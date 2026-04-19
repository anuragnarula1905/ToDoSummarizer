import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_CHAT_ID
from db import save_task, get_all_pending_tasks_display, mark_all_as_done
from groq_parser import parse_task

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _is_authorized(update: Update) -> bool:
    """Returns True only if the message is from the allowed chat ID."""
    return update.effective_chat.id == ALLOWED_CHAT_ID


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"[Handler] /start from chat_id: {chat_id}")
    await update.message.reply_text(
        f"👋 Hello! I'm your Teacher Task Reminder Bot.\n\n"
        f"🔑 Your Chat ID is: `{chat_id}`\n\n"
        f"Just forward any task message to me and I'll remind you at the right time!\n\n"
        f"Commands:\n"
        f"  /tasks — View pending tasks\n"
        f"  /clear — Mark all tasks as done\n"
        f"  /help  — Show usage guide",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "📖 *How to use this bot:*\n\n"
        "1️⃣ Forward any task message to me (text, photo, or document).\n"
        "2️⃣ I'll read it and schedule reminders automatically:\n\n"
        "   🌅 *\"Tomorrow\"* → Gentle at 4 PM, Final at 7 PM next day\n"
        "   🌤️ *\"By evening\"* → Gentle at 5 PM, Final at 7 PM today\n"
        "   ⏰ *Specific time* → Reminder 1 hour before\n"
        "   📋 *No deadline* → Included in 7 PM daily digest\n\n"
        "3️⃣ Sit back and relax! ✅",
        parse_mode="Markdown"
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return

    tasks = get_all_pending_tasks_display(str(ALLOWED_CHAT_ID))
    if not tasks:
        await update.message.reply_text("✅ You have no pending tasks! Enjoy your day 🎉")
        return

    lines = []
    for i, task in enumerate(tasks, 1):
        stype = task["schedule_type"]
        badges = {
            "tomorrow": "🌅 Tomorrow",
            "evening":  "🌤️ This Evening",
            "exact":    "⏰ Exact Deadline",
            "none":     "📋 No Deadline",
        }
        badge = badges.get(stype, stype)
        lines.append(f"{i}. [{badge}] {task['task_summary']}")

    await update.message.reply_text(
        f"📌 *Pending Tasks ({len(tasks)}):*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    mark_all_as_done(str(ALLOWED_CHAT_ID))
    await update.message.reply_text("🗑️ All tasks marked as done! Fresh start. ✅")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Core message handler — processes all forwarded/typed messages."""
    if not _is_authorized(update):
        logger.debug(f"[Handler] Ignoring unauthorized chat_id: {update.effective_chat.id}")
        return

    msg = update.message

    # ── Extract text ──────────────────────────────────────────────────────────
    message_text = msg.text or msg.caption

    # ── Extract file ──────────────────────────────────────────────────────────
    file_id   = None
    file_type = None

    if msg.photo:
        file_id   = msg.photo[-1].file_id   # largest resolution
        file_type = "photo"
    elif msg.document:
        file_id   = msg.document.file_id
        file_type = "document"

    # ── Guard: need text to parse ─────────────────────────────────────────────
    if not message_text:
        await msg.reply_text(
            "🤔 I received a file but couldn't find any task description.\n"
            "Please add a caption or send the text along with the file!"
        )
        return

    # ── Typing indicator ──────────────────────────────────────────────────────
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # ── Call Groq ─────────────────────────────────────────────────────────────
    result = parse_task(message_text)
    task_summary  = result["task_summary"]
    schedule_type = result["schedule_type"]
    target_iso    = result.get("target_iso")

    # ── Save to DB ────────────────────────────────────────────────────────────
    save_task(
        chat_id       = str(update.effective_chat.id),
        original_text = message_text,
        task_summary  = task_summary,
        schedule_type = schedule_type,
        target_iso    = target_iso,
        file_id       = file_id,
        file_type     = file_type,
    )

    # ── Build confirmation message ────────────────────────────────────────────
    if schedule_type == "exact" and target_iso:
        try:
            dt = datetime.fromisoformat(target_iso).astimezone(IST)
            deadline_str = dt.strftime("%I:%M %p, %d %b")
            confirm = (
                f"✅ Got it! Task saved.\n\n"
                f"📌 {task_summary}\n"
                f"⏰ Deadline: {deadline_str} — I'll remind you 1 hour before."
            )
        except Exception:
            confirm = (
                f"✅ Got it! Task saved.\n\n"
                f"📌 {task_summary}\n"
                f"⏰ I'll remind you 1 hour before the deadline."
            )
    elif schedule_type == "tomorrow":
        confirm = (
            f"✅ Got it! Task saved.\n\n"
            f"📌 {task_summary}\n"
            f"🌅 I'll gently remind you at 4 PM tomorrow,\n"
            f"   and send a final reminder at 7 PM."
        )
    elif schedule_type == "evening":
        confirm = (
            f"✅ Got it! Task saved.\n\n"
            f"📌 {task_summary}\n"
            f"🌤️ I'll gently remind you at 5 PM today,\n"
            f"   and send a final reminder at 7 PM."
        )
    else:  # none
        confirm = (
            f"✅ Got it! Task saved.\n\n"
            f"📌 {task_summary}\n"
            f"📋 No deadline detected — I'll include this in your 7 PM digest."
        )

    await msg.reply_text(confirm)
