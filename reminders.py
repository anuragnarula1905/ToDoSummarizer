import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Bot

from db import update_reminder_status
from config import ALLOWED_CHAT_ID

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# ─────────────────────────────────────────────────────────────────────────────
# Gentle Reminder (4PM tomorrow / 5PM today)
# ─────────────────────────────────────────────────────────────────────────────

async def send_gentle_reminder(bot: Bot, task: dict):
    """Sends the soft, heads-up reminder for tomorrow/evening tasks."""
    chat_id = task["chat_id"]
    summary = task["task_summary"]
    stype   = task["schedule_type"]

    if stype == "tomorrow":
        label = "🌅 Heads-up! You have a task due this evening."
        hint  = "Final reminder coming at 7 PM."
    else:  # evening
        label = "🌤️ Gentle Reminder — Task due this evening!"
        hint  = "Final reminder coming at 7 PM."

    text = (
        f"{label}\n\n"
        f"📌 {summary}\n\n"
        f"💡 {hint}"
    )

    await bot.send_message(chat_id=chat_id, text=text)

    # Re-send the original file if any
    await _send_file(bot, task)

    update_reminder_status(task["id"], "gentle")
    logger.info(f"[Reminder] Gentle sent for task id={task['id']}")


# ─────────────────────────────────────────────────────────────────────────────
# Final / Exact Deadline Reminder (7PM / 1hr before exact deadline)
# ─────────────────────────────────────────────────────────────────────────────

async def send_final_reminder(bot: Bot, task: dict):
    """Sends the urgent final reminder for tomorrow/evening tasks."""
    chat_id = task["chat_id"]
    summary = task["task_summary"]

    text = (
        f"🔔 FINAL REMINDER — Please take action now!\n\n"
        f"📌 {summary}\n\n"
        f"✅ Mark done with /clear once finished."
    )

    await bot.send_message(chat_id=chat_id, text=text)
    await _send_file(bot, task)

    update_reminder_status(task["id"], "final")
    logger.info(f"[Reminder] Final sent for task id={task['id']}")


async def send_exact_deadline_reminder(bot: Bot, task: dict):
    """Sends the 1-hour-before reminder for exact deadline tasks."""
    chat_id = task["chat_id"]
    summary = task["task_summary"]

    # Parse the target_iso to show a human-readable time
    if task.get("target_iso"):
        try:
            deadline_dt = datetime.fromisoformat(task["target_iso"]).astimezone(IST)
            due_str = deadline_dt.strftime("%I:%M %p, %d %b")
        except Exception:
            due_str = task["target_iso"]
    else:
        due_str = "soon"

    text = (
        f"⏰ REMINDER — Task Due in 1 Hour!\n\n"
        f"📌 {summary}\n"
        f"🕐 Due: {due_str}\n\n"
        f"✅ Mark done with /clear once finished."
    )

    await bot.send_message(chat_id=chat_id, text=text)
    await _send_file(bot, task)

    update_reminder_status(task["id"], "final")
    logger.info(f"[Reminder] Exact deadline reminder sent for task id={task['id']}")


# ─────────────────────────────────────────────────────────────────────────────
# Daily Digest (7 PM — 'none' type tasks)
# ─────────────────────────────────────────────────────────────────────────────

async def send_daily_digest(bot: Bot, chat_id: str, tasks: list):
    """Sends the nightly digest of all no-deadline tasks."""
    if not tasks:
        logger.info("[Digest] No tasks to digest tonight.")
        return

    lines = "\n".join(
        f"{i + 1}. {t['task_summary']}" for i, t in enumerate(tasks)
    )

    text = (
        f"📋 YOUR TASK DIGEST FOR TODAY\n\n"
        f"{lines}\n\n"
        f"Have a good evening! 🌙\n"
        f"Use /clear to mark all as done."
    )

    await bot.send_message(chat_id=chat_id, text=text)

    for task in tasks:
        update_reminder_status(task["id"], "final")

    logger.info(f"[Digest] Sent {len(tasks)} tasks to chat_id={chat_id}")


# ─────────────────────────────────────────────────────────────────────────────
# Helper — Re-send original file if attached
# ─────────────────────────────────────────────────────────────────────────────

async def _send_file(bot: Bot, task: dict):
    """Re-sends the attached photo or document if any."""
    file_id   = task.get("file_id")
    file_type = task.get("file_type")
    chat_id   = task["chat_id"]

    if not file_id:
        return

    try:
        if file_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=file_id, caption="📎 Original attachment")
        elif file_type == "document":
            await bot.send_document(chat_id=chat_id, document=file_id, caption="📎 Original attachment")
    except Exception as e:
        logger.warning(f"[Reminder] Could not re-send file for task {task['id']}: {e}")
