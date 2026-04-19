import logging
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from db import init_db
from handlers import (
    start_command,
    help_command,
    tasks_command,
    clear_command,
    handle_message,
)
from scheduler import start_scheduler

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    logger.info("[Bot] Initializing database...")
    init_db()

    logger.info("[Bot] Building Telegram application...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Register command handlers ─────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("clear", clear_command))

    # ── Register message handler (text, photos, documents, forwards) ──────────
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL,
        handle_message
    ))

    # ── Start background scheduler ────────────────────────────────────────────
    logger.info("[Bot] Starting scheduler...")
    start_scheduler(app.bot)

    # ── Start polling ─────────────────────────────────────────────────────────
    logger.info("[Bot] Bot running — polling for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
