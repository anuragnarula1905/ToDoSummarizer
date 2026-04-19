import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

client = Groq(api_key=GROQ_API_KEY)

PROMPT_TEMPLATE = """You are a task extraction assistant for a school teacher in India.
Today's date is {date} and the current time is {time} IST.

Read the message below and extract the task.
Return ONLY a valid JSON object with these exact keys — no explanation, no markdown fences:

  - "task_summary": A short 1-2 sentence summary of what needs to be done.
  - "schedule_type": Must be exactly one of: "tomorrow", "evening", "exact", "none".
       - "tomorrow": if the message says "tomorrow", "next day", or similar next-day phrasing.
       - "evening": if it says "by evening", "tonight", "end of day", or just "today" without a specific time.
       - "exact": if a specific time or date is mentioned (e.g. "by 3:00 PM", "by 5 PM", "by Friday").
       - "none": if there is absolutely no time context mentioned.
  - "target_iso": Only used when schedule_type is "exact".
       Provide the deadline as "YYYY-MM-DDTHH:MM:SS" in IST based on the current date.
       If schedule_type is NOT "exact", return null.

Message:
{message_text}"""


def parse_task(message_text: str) -> dict:
    """
    Calls the Groq API to extract structured task data from a free-text message.
    Returns a dict with keys: task_summary, schedule_type, target_iso
    Falls back gracefully on any error.
    """
    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%A, %d %B %Y")   # e.g. "Saturday, 19 April 2026"
    time_str = now_ist.strftime("%I:%M %p")         # e.g. "01:11 PM"

    prompt = PROMPT_TEMPLATE.format(
        date=date_str,
        time=time_str,
        message_text=message_text.strip()
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,    # low temperature = more consistent structured output
            max_tokens=256,
        )

        raw = response.choices[0].message.content.strip()
        logger.info(f"[Groq] Raw response: {raw}")

        data = json.loads(raw)

        # Validate and sanitize the returned data
        schedule_type = data.get("schedule_type", "none")
        if schedule_type not in ("tomorrow", "evening", "exact", "none"):
            logger.warning(f"[Groq] Unexpected schedule_type '{schedule_type}', defaulting to 'none'")
            schedule_type = "none"

        target_iso = data.get("target_iso") if schedule_type == "exact" else None

        return {
            "task_summary":  data.get("task_summary", message_text[:200]),
            "schedule_type": schedule_type,
            "target_iso":    target_iso,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Groq] JSON parse error: {e}")
    except Exception as e:
        logger.error(f"[Groq] API error: {e}")

    # Graceful fallback — treat as no-deadline task
    return {
        "task_summary":  message_text[:200],
        "schedule_type": "none",
        "target_iso":    None,
    }
