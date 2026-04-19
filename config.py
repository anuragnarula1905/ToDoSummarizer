import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
ALLOWED_CHAT_ID    = int(os.getenv("ALLOWED_CHAT_ID", "0"))

TIMEZONE = ZoneInfo("Asia/Kolkata")

# Daily digest time (no-deadline tasks)
DAILY_DIGEST_HOUR   = 19   # 7:00 PM IST
DAILY_DIGEST_MINUTE = 0

# "Evening" tasks: gentle at 5 PM, final at 7 PM
EVENING_GENTLE_HOUR = 17   # 5:00 PM IST
EVENING_FINAL_HOUR  = 19   # 7:00 PM IST

# "Tomorrow" tasks: gentle at 4 PM next day, final at 7 PM next day
TOMORROW_GENTLE_HOUR = 16  # 4:00 PM IST
TOMORROW_FINAL_HOUR  = 19  # 7:00 PM IST

# "Exact" deadline tasks: remind 1 hour before
EXACT_REMINDER_MINUTES_BEFORE = 60

# Scheduler check interval
DEADLINE_CHECK_INTERVAL_SECONDS = 60

# Groq model
GROQ_MODEL = "llama-3.3-70b-versatile"
