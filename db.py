import os
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Opens a new connection to the PostgreSQL database."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """Creates the tasks table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id              SERIAL PRIMARY KEY,
                    chat_id         TEXT NOT NULL,
                    original_text   TEXT NOT NULL,
                    task_summary    TEXT NOT NULL,
                    schedule_type   TEXT NOT NULL CHECK(schedule_type IN ('tomorrow', 'evening', 'exact', 'none')),
                    target_iso      TEXT,
                    file_id         TEXT,
                    file_type       TEXT CHECK(file_type IN ('photo', 'document') OR file_type IS NULL),
                    gentle_reminded BOOLEAN NOT NULL DEFAULT FALSE,
                    final_reminded  BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TEXT NOT NULL
                )
            """)
        conn.commit()
    logger.info("[DB] PostgreSQL database initialized.")


def save_task(chat_id, original_text, task_summary, schedule_type, target_iso=None, file_id=None, file_type=None):
    """Inserts a new task row into the database."""
    created_at = datetime.now(IST).isoformat()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tasks
                    (chat_id, original_text, task_summary, schedule_type, target_iso, file_id, file_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (str(chat_id), original_text, task_summary, schedule_type, target_iso, file_id, file_type, created_at))
            task_id = cur.fetchone()[0]
        conn.commit()
    logger.info(f"[DB] Task saved — id={task_id}, type={schedule_type}")
    return task_id


def get_pending_tasks():
    """Returns all tasks that haven't had their final reminder sent yet."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM tasks WHERE final_reminded = FALSE")
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_todays_none_tasks(chat_id):
    """Returns all 'none' schedule_type tasks created today that haven't been finally reminded."""
    today_ist = datetime.now(IST).date().isoformat()
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM tasks
                WHERE schedule_type = 'none'
                  AND chat_id = %s
                  AND final_reminded = FALSE
                  AND created_at::date = %s::date
            """, (str(chat_id), today_ist))
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def update_reminder_status(task_id, reminder_type):
    """
    Updates gentle_reminded or final_reminded for a task.
    reminder_type: 'gentle' or 'final'
    """
    column = "gentle_reminded" if reminder_type == "gentle" else "final_reminded"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE tasks SET {column} = TRUE WHERE id = %s", (task_id,))
        conn.commit()
    logger.info(f"[DB] Task id={task_id} marked {reminder_type}_reminded=TRUE")


def get_all_pending_tasks_display(chat_id):
    """Returns all tasks not yet finally reminded (for /tasks command display)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM tasks
                WHERE chat_id = %s AND final_reminded = FALSE
                ORDER BY created_at ASC
            """, (str(chat_id),))
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def mark_all_as_done(chat_id):
    """Marks all tasks as finally reminded (/clear command)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks SET gentle_reminded = TRUE, final_reminded = TRUE
                WHERE chat_id = %s AND final_reminded = FALSE
            """, (str(chat_id),))
        conn.commit()
    logger.info(f"[DB] All tasks cleared for chat_id={chat_id}")
