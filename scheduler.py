import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Bot

from config import (
    ALLOWED_CHAT_ID, TIMEZONE,
    DAILY_DIGEST_HOUR, DAILY_DIGEST_MINUTE,
    EVENING_GENTLE_HOUR, EVENING_FINAL_HOUR,
    TOMORROW_GENTLE_HOUR, TOMORROW_FINAL_HOUR,
    EXACT_REMINDER_MINUTES_BEFORE,
    DEADLINE_CHECK_INTERVAL_SECONDS,
)
from db import get_pending_tasks, get_todays_none_tasks
from reminders import (
    send_gentle_reminder,
    send_final_reminder,
    send_exact_deadline_reminder,
    send_daily_digest,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _run_async(coro):
    """Helper to run async reminder functions from a sync APScheduler job."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def check_reminders(bot: Bot):
    """
    Main watcher — runs every 60 seconds.
    Checks all pending tasks and fires reminders based on schedule_type and IST time.
    """
    now = datetime.now(IST)
    today = now.date()

    tasks = get_pending_tasks()
    logger.debug(f"[Scheduler] Watcher tick — {len(tasks)} pending task(s)")

    for task in tasks:
        stype = task["schedule_type"]
        tid   = task["id"]

        # ── Exact deadline: remind 1 hour before ─────────────────────────────
        if stype == "exact":
            if not task.get("target_iso"):
                continue
            try:
                deadline = datetime.fromisoformat(task["target_iso"]).astimezone(IST)
            except Exception:
                continue

            time_left = (deadline - now).total_seconds() / 60  # minutes
            if 0 < time_left <= EXACT_REMINDER_MINUTES_BEFORE and not task["final_reminded"]:
                logger.info(f"[Scheduler] Firing exact reminder for task {tid}")
                _run_async(send_exact_deadline_reminder(bot, task))

        # ── Evening tasks: gentle at 5 PM, final at 7 PM ─────────────────────
        elif stype == "evening":
            created_date = datetime.fromisoformat(task["created_at"]).astimezone(IST).date()
            if created_date != today:
                continue  # task is from a previous day, skip

            if now.hour >= EVENING_GENTLE_HOUR and not task["gentle_reminded"]:
                logger.info(f"[Scheduler] Firing evening gentle reminder for task {tid}")
                _run_async(send_gentle_reminder(bot, task))

            if now.hour >= EVENING_FINAL_HOUR and not task["final_reminded"]:
                logger.info(f"[Scheduler] Firing evening final reminder for task {tid}")
                _run_async(send_final_reminder(bot, task))

        # ── Tomorrow tasks: gentle at 4 PM next day, final at 7 PM next day ──
        elif stype == "tomorrow":
            created_date = datetime.fromisoformat(task["created_at"]).astimezone(IST).date()
            target_date  = created_date + timedelta(days=1)

            if today != target_date:
                continue  # not the right day yet

            if now.hour >= TOMORROW_GENTLE_HOUR and not task["gentle_reminded"]:
                logger.info(f"[Scheduler] Firing tomorrow gentle reminder for task {tid}")
                _run_async(send_gentle_reminder(bot, task))

            if now.hour >= TOMORROW_FINAL_HOUR and not task["final_reminded"]:
                logger.info(f"[Scheduler] Firing tomorrow final reminder for task {tid}")
                _run_async(send_final_reminder(bot, task))


def send_nightly_digest(bot: Bot):
    """
    Daily digest — runs at 7:00 PM IST.
    Aggregates all 'none' tasks for today and sends a single summary message.
    """
    logger.info("[Scheduler] Running nightly digest")
    tasks = get_todays_none_tasks(str(ALLOWED_CHAT_ID))
    _run_async(send_daily_digest(bot, str(ALLOWED_CHAT_ID), tasks))


def start_scheduler(bot: Bot) -> BackgroundScheduler:
    """
    Initializes and starts the APScheduler with two jobs:
      1. Watcher — runs every 60 seconds
      2. Nightly digest — runs at 7:00 PM IST
    """
    scheduler = BackgroundScheduler(timezone=IST)

    # Job 1 — Main watcher
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(seconds=DEADLINE_CHECK_INTERVAL_SECONDS),
        args=[bot],
        id="watcher",
        name="Main Watcher",
        replace_existing=True,
        misfire_grace_time=30,
    )

    # Job 2 — 7 PM digest
    scheduler.add_job(
        send_nightly_digest,
        trigger=CronTrigger(hour=DAILY_DIGEST_HOUR, minute=DAILY_DIGEST_MINUTE, timezone=IST),
        args=[bot],
        id="nightly_digest",
        name="Nightly Digest",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] Started — Watcher every 60s, Digest at 7:00 PM IST")
    return scheduler
