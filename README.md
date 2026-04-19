# 📚 Teacher Task Reminder Bot

A Telegram bot for teachers who receive task messages throughout the day and need automatic reminders. Forward any message to the bot — it extracts the task and deadline using Gemini AI, then reminds you at the right time.

---

## How It Works

1. Your mom receives a task message on WhatsApp from school
2. She **forwards it to this Telegram bot** (takes 2 seconds)
3. Groq AI reads the message and automatically categorizes the scheduling logic
4. The bot **automatically reminds her** at the right time:
   - **"Tomorrow"** → Gentle reminder at 4:00 PM next day, final reminder at 7:00 PM
   - **"Evening"** → Gentle reminder at 5:00 PM today, final reminder at 7:00 PM
   - **Exact Deadline** → Reminder sent **1 hour before** the exact deadline
   - **No deadline** → Collected into a **daily digest at 7:00 PM IST**

She never needs to remember anything. Just forward and forget.

---

## Example

**She forwards this message:**
> "Make a list of these students and send it to the principal by 6 PM" _(with an image attached)_

**Bot confirms:**
> ✅ Got it! Task saved.
> 📌 Summary: Prepare a list of students and send to the principal.
> ⏰ Deadline: 6:00 PM today — I'll remind you at 5:00 PM.

**At 5:00 PM, bot sends:**
> ⏰ REMINDER — Task Due in 1 Hour!
> 📌 Prepare a list of students and send to the principal.
> 🕐 Due: 6:00 PM today
> _(original image re-sent below)_

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| Bot Interface | python-telegram-bot v20 | Free |
| AI Parsing | Groq API (Llama 3.3) | Free Developer Tier |
| Database | SQLite | Free |
| Scheduler | APScheduler | Free |
| Hosting | Render.com (Background Worker) | Free |
| Language | Python 3.11 | Free |

**Total estimated cost: ₹0/month**

---

## Project Structure

```
teacher-reminder-bot/
├── bot.py                  # Entry point — starts bot + scheduler
├── handlers.py             # Handles incoming Telegram messages
├── groq_parser.py          # Groq AI — extracts task + deadline from text
├── db.py                   # SQLite database models + helper functions
├── scheduler.py            # APScheduler — deadline checker + 7 PM digest
├── reminders.py            # Composes and sends reminder messages
├── config.py               # Central config (timezone, reminder times, etc.)
├── requirements.txt        # Python dependencies
├── render.yaml             # Render.com deployment config
├── .env.example            # Template for environment variables
└── .gitignore              # Excludes .env and db file from git
```

---

## Full Setup Guide

### Step 1 — Create the Telegram Bot (2 minutes)

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Enter a name: e.g. `Mom Task Reminder`
4. Enter a username ending in `bot`: e.g. `mom_task_reminder_bot`
5. BotFather replies with a token like:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxx
   ```
6. **Copy and save this token** — you'll need it in Step 4

---

### Step 2 — Get Groq API Key (Free)

1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Sign in or create a developer account
3. Click **"Create API Key"**
4. Copy the key — it looks like: `gsk_XXXXXXXXXXXXXXXXXXXXXXXX`
5. **Free tier limits:** Extremely high limits designed for developers

> No credit card required. The free tier is largely sufficient for personal bot usage.

---

### Step 3 — Set Up Project Locally

```bash
# 1. Clone or create the project folder
mkdir teacher-reminder-bot
cd teacher-reminder-bot

# 2. Create a Python virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file from the template
cp .env.example .env
```

Now open `.env` and fill in your values (see Step 4).

---

### Step 4 — Configure Environment Variables

Your `.env` file should look like this:

```env
# From BotFather (Step 1)
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxx

# From Groq Console (Step 2)
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXXXXXX

# Your mom's Telegram chat ID — see Step 5 to get this
ALLOWED_CHAT_ID=987654321
```

> ⚠️ Never commit `.env` to GitHub. It's listed in `.gitignore` by default.

---

### Step 5 — Find Your Telegram Chat ID

The bot only responds to one specific person (your mom) for security. You need her chat ID.

```bash
# Run the bot locally
python bot.py
```

Then open Telegram, search for your bot by username, and send `/start`. The bot will print your chat ID in the terminal:

```
[INFO] New /start from chat_id: 987654321
```

Copy that number and paste it as `ALLOWED_CHAT_ID` in your `.env`.

---

### Step 6 — Test Locally

```bash
python bot.py
```

You should see:
```
[INFO] Bot started. Polling for messages...
[INFO] Scheduler started (Asia/Kolkata timezone)
```

Send a test message to the bot on Telegram:
```
Prepare PTM schedule and send it to the principal by 6pm today
```

Expected reply:
```
✅ Got it! Task saved.
📌 Prepare PTM schedule and send to the principal.
⏰ Deadline detected: 6:00 PM today — I'll remind you at 5:00 PM.
```

---

### Step 7 — Deploy to Render.com

#### 7a — Push code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/teacher-reminder-bot.git
git push -u origin main
```

> Make sure `.env` is in `.gitignore` — never push your secrets to GitHub.

#### 7b — Create Render Background Worker

1. Go to [render.com](https://render.com) and sign up with GitHub
2. Click **New +** → **Background Worker**
   - (Do NOT choose "Web Service" — this bot doesn't serve HTTP traffic)
3. Connect your GitHub repo
4. Set the following:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. Go to the **Environment** tab and add these variables:
   ```
   TELEGRAM_BOT_TOKEN = your_token_here
   GROQ_API_KEY       = your_groq_key_here
   ALLOWED_CHAT_ID    = your_chat_id_here
   ```
6. Click **Create Background Worker**

Render builds and deploys in ~2 minutes. Check the **Logs** tab — you should see:
```
[INFO] Bot started. Polling for messages...
```

> ⚠️ **Render Free Tier Note:** Background workers on the free tier can spin down after inactivity. If this becomes an issue, upgrade to Render's $7/month plan or switch to [Railway.app](https://railway.app) which has a more generous always-on free tier.

---

## File-by-File Code Guide

This section describes exactly what each file should contain so you know what to code.

### `config.py`
Central configuration. Import this everywhere instead of hardcoding values.

```python
import os
from zoneinfo import ZoneInfo

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
ALLOWED_CHAT_ID    = int(os.getenv("ALLOWED_CHAT_ID"))

TIMEZONE                       = ZoneInfo("Asia/Kolkata")
DAILY_DIGEST_HOUR              = 19       # 7:00 PM IST
DAILY_DIGEST_MINUTE            = 0
DEADLINE_REMINDER_MINUTES_BEFORE = 60    # Remind 1 hour before deadline
DEADLINE_CHECK_INTERVAL_SECONDS  = 60    # Check for upcoming deadlines every minute
```

---

### `db.py`
SQLite database using the built-in `sqlite3` module. Creates one table: `tasks`.

**Table schema:**

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `chat_id` | TEXT | Telegram chat ID to send reminder to |
| `original_text` | TEXT | Raw forwarded message text |
| `task_summary` | TEXT | AI-generated short summary |
| `schedule_type` | TEXT | `'tomorrow'`, `'evening'`, `'exact'`, or `'none'` |
| `target_iso` | TEXT | ISO datetime reference if `'exact'` |
| `file_id` | TEXT | Telegram file_id if image/doc was attached |
| `file_type` | TEXT | `'photo'`, `'document'`, or NULL |
| `gentle_reminded` | BOOLEAN | Has the 4 PM / 5 PM gentle reminder been sent? (default 0) |
| `final_reminded` | BOOLEAN | Has the 7 PM / exact-time reminder been sent? (default 0) |
| `created_at` | TEXT | ISO datetime string of when task was saved |

**Functions to implement:**
- `init_db()` — creates the table if it doesn't exist. Called on bot startup.
- `save_task(...)` — inserts a new row with the parsed schedule logic.
- `get_pending_tasks()` — returns all tasks where `final_reminded=0`.
- `update_reminder_status(task_id, reminder_type)` — marks `gentle_reminded=1` or `final_reminded=1`.

---

### `groq_parser.py`
Calls the Groq API to parse a forwarded message into structured task data.

**Install:** `groq` (already in requirements.txt)

**Logic:**
1. Initialize the Groq client
2. Build a prompt with the current IST date/time + the forwarded message text
3. Instruct Groq to return **only** a JSON object — no extra text
4. Parse the JSON response
5. Return a dict with keys: `task_summary`, `schedule_type`, `target_iso`

**Prompt template to use:**

```
You are a task extraction assistant for a school teacher in India.
Today's date is {date} and current time is {time} IST.

Read the message below and extract the task.
Return ONLY a valid JSON object with these exact keys:
  - "task_summary": A short 1-2 sentence summary of what needs to be done.
  - "schedule_type": Must be exactly one of: "tomorrow", "evening", "exact", "none".
       - "tomorrow": if it says "tomorrow" or "next day".
       - "evening": if it says "by evening", "tonight", or "today" without specific time.
       - "exact": if a specific time is mentioned (e.g. "by 3:00 PM").
       - "none": if no time context is provided at all.
  - "target_iso": If schedule_type is "exact", provide the concrete deadline as "YYYY-MM-DDTHH:MM:SS" in IST. Otherwise, return null.

Message:
{message_text}
```

**Important:** Enable JSON output mode in your Groq completion call by passing `response_format={"type": "json_object"}`.

---

### `handlers.py`
Called every time a message is received. This is the core handler.

**Function: `handle_message(update, context)`**

Step-by-step logic:
1. **Security check:** If `update.effective_chat.id != ALLOWED_CHAT_ID`, ignore silently
2. **Extract text:** Use `update.message.text` or `update.message.caption` (captions are text on photos/docs)
3. **Extract file:**
   - If `update.message.photo` → `file_id = update.message.photo[-1].file_id`, `file_type = 'photo'`
   - If `update.message.document` → `file_id = update.message.document.file_id`, `file_type = 'document'`
   - Otherwise → `file_id = None`, `file_type = None`
4. **Handle missing text:** If no text and no caption, reply asking what the task is, then return
5. **Call Groq:** `result = parse_task(message_text)` from `groq_parser.py`
6. **Save to DB:** Call `save_task(...)` with all extracted data including `schedule_type`
7. **Confirm to user:** Send a friendly confirmation message:
   - "exact": "✅ Got it! I'll remind you 1 hour before."
   - "tomorrow": "✅ Got it! I'll gently remind you at 4 PM tomorrow, and a final reminder at 7 PM."
   - "evening": "✅ Got it! I'll gently remind you at 5 PM today, and a final reminder at 7 PM."
   - "none": "✅ Got it! I'll include this in your 7 PM summary."

---

### `reminders.py`
Composes and sends the actual reminder messages via Telegram.

**Function: `send_deadline_reminder(bot, task)`**
- Sends a text message: "⏰ REMINDER — Task Due in 1 Hour!\n\n📌 {task_summary}\n🕐 Due: {deadline}"
- If `task['file_id']` is not None:
  - If `file_type == 'photo'` → call `bot.send_photo(chat_id, file_id)`
  - If `file_type == 'document'` → call `bot.send_document(chat_id, file_id)`

**Function: `send_daily_digest(bot, chat_id, tasks)`**
- If `tasks` is empty → do nothing (don't send an empty message)
- Otherwise build message:
  ```
  📋 YOUR TASKS FOR TODAY

  1. {task_summary_1}
  2. {task_summary_2}
  ...

  Have a good evening! 🌙
  ```
- Send the message to `chat_id`
- Mark all tasks as reminded in DB

---

### `scheduler.py`
Sets up two background jobs using APScheduler.

**Job 1 — Main Watcher (Runs every 60 seconds)**
- Checks `get_pending_tasks()` and triggers warnings based on `schedule_type` and current IST time:
  - **exact**: Send final reminder if time is <= 1 hr away. Mark `final_reminded=1`.
  - **tomorrow**: 
    - Send gentle reminder if time >= 16:00 next day & `gentle_reminded=0`. Mark `gentle_reminded=1`.
    - Send final reminder if time >= 19:00 next day & `final_reminded=0`. Mark `final_reminded=1`.
  - **evening**:
    - Send gentle reminder if time >= 17:00 today & `gentle_reminded=0`. Mark `gentle_reminded=1`.
    - Send final reminder if time >= 19:00 today & `final_reminded=0`. Mark `final_reminded=1`.

**Job 2 — Daily Digest (Runs at 19:00 IST)**
- Aggregates tasks with `schedule_type='none'` created today.
- Summarizes and sends in a single message.
- Marks them as `final_reminded=1`.

**Important:** Use `BackgroundScheduler` with `timezone=ZoneInfo("Asia/Kolkata")` so all cron times are in IST automatically.

---

### `bot.py`
The main entry point. Keep it clean and simple.

```python
# Pseudocode structure
def main():
    load_dotenv()
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # Start scheduler
    start_scheduler(app.bot)

    # Start polling
    app.run_polling()
```

**Bot commands to implement:**

| Command | Behaviour |
|---|---|
| `/start` | Welcome message + prints chat_id for setup |
| `/tasks` | Lists all pending (unreminded) tasks with deadlines |
| `/clear` | Marks all tasks as done. Useful at end of day |
| `/help` | Short usage instructions |

---

### `requirements.txt`

```
python-telegram-bot==20.7
groq==0.8.0
APScheduler==3.10.4
python-dotenv==1.0.1
```

---

### `render.yaml`

```yaml
services:
  - type: worker
    name: teacher-reminder-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python bot.py
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: ALLOWED_CHAT_ID
        sync: false
```

---

### `.gitignore`

```
.env
*.db
__pycache__/
venv/
*.pyc
```

---

## Edge Cases Handled

| Situation | How it's handled |
|---|---|
| Image with no caption/text | Bot replies asking what the task is |
| "Evening" tasks | Extracted as schedule_type="evening", sends reminders at 5PM and 7PM |
| "Tomorrow" tasks | Extracted as schedule_type="tomorrow", sends reminders at 4PM and 7PM next day |
| Multiple tasks in one message | Saved as one task; AI summarises all of it |
| PDF document forwarded | Stored as `file_type='document'`, re-sent on reminder |
| No tasks today | Daily digest is not sent (no empty message) |
| Bot restarts mid-day | APScheduler re-checks DB on startup, fires any missed reminders immediately |
| Someone else messages the bot | Silently ignored (ALLOWED_CHAT_ID check) |

---

## System Flow Diagram

```
[WhatsApp message received]
         |
         | (mom manually forwards to Telegram bot)
         v
[Telegram Bot — handlers.py]
    |             |
    |             v
    |      [Extract file_id if photo/doc]
    |
    v
[groq_parser.py]
    — sends text + current IST time to Groq API
    — returns: task_summary, schedule_type, target_iso
         |
         v
[db.py — save_task()]
    — stores everything in SQLite
         |
         v
[Confirmation message sent back to mom]


[APScheduler — runs in background]
         |
         |--- Every 60 seconds (Main Watcher):
         |       Checks pending tasks based on type (exact, evening, tomorrow)
         |       → sends 4PM/5PM gentle or 1Hr final reminders
         |       → updates gentle_reminded / final_reminded
         |
         |--- Daily at 7:00 PM IST (Digest):
                 → aggregates 'none' tasks
                 → send_daily_digest()
                 → updates final_reminded
```

---

## Common Issues & Fixes

**Bot not responding?**
- Check Render logs for errors
- Verify `TELEGRAM_BOT_TOKEN` is correct in environment variables
- Make sure you sent `/start` to the bot first

**Groq not parsing correctly?**
- Check `GROQ_API_KEY` is valid at [console.groq.com](https://console.groq.com)
- Print the raw Groq response in `groq_parser.py` to debug
- Ensure you passed `response_format={"type": "json_object"}`

**Reminders not firing?**
- Confirm `ALLOWED_CHAT_ID` matches what the bot printed during `/start`
- Check the scheduler is starting (look for `[INFO] Scheduler started` in logs)
- Verify timezone — all deadlines are stored as UTC internally, displayed as IST

**Render free tier spinning down?**
- Upgrade to Render's $7/month plan, or
- Switch to [Railway.app](https://railway.app) free tier (more reliable for background workers)

---

## Security Notes

- The bot only accepts messages from `ALLOWED_CHAT_ID` — all others are silently ignored
- API keys are stored as environment variables, never in code
- The `.env` file is excluded from git via `.gitignore`
- SQLite database file (`.db`) is also excluded from git

---

## Cost Summary

| Service | Free Tier Limit | Expected Usage | Cost |
|---|---|---|---|
| Telegram Bot API | Unlimited | ~20 messages/day | ₹0 |
| Groq API | Developer free tier | ~20 requests/day | ₹0 |
| Render.com | Background worker free tier | Always on | ₹0 |
| SQLite | No limits | Tiny (KB of data) | ₹0 |
| **Total** | | | **₹0/month** |

---

*Built with ❤️ — Telegram + Groq API + Python + Render.com | IST Timezone*