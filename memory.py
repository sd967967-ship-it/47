"""
Persistent memory for 47.
Stores full conversation history + explicitly remembered facts in a local
SQLite file (memory_47.db) — free, no external service, survives restarts.
"""

import re
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "memory_47.db"

# FIX: facts used to be dumped into every prompt with no cap. A long-lived
# install eventually turns this into hundreds of facts on every single
# turn — bloats context, slows every reply, and costs more per call the
# longer you use it. Capped to the N most recently touched (inserted OR
# re-affirmed) facts. This is a size limit, not "relevance filtering" in
# any smart sense — a real relevance filter would need embeddings/search,
# out of scope for the free/local stack this project promises — but it
# stops unbounded growth, which was the actual reported problem.
MAX_FACTS_IN_CONTEXT = 40


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            ts REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            key TEXT PRIMARY KEY,
            value TEXT,
            ts REAL
        )
    """)
    return conn


def log_turn(role: str, content: str):
    conn = _connect()
    conn.execute("INSERT INTO conversation (role, content, ts) VALUES (?, ?, ?)",
                 (role, content, time.time()))
    conn.commit()
    conn.close()


def recent_history(limit: int = 10):
    """Return the last `limit` turns as a list of (role, content), oldest first."""
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return list(reversed(rows))


# BUGFIX: the old key derivation was `fact.split(" is ")[0]` or, failing
# that, the first 30 raw characters of the sentence — case-sensitive,
# punctuation-sensitive, and with no normalization at all. That meant
# "remember that My Flight is at 6pm" and a later "remember that my flight
# is at 7pm" produced two different keys ("My Flight" vs "my flight") and
# just piled up as separate facts instead of the second one correcting the
# first. normalize_key() collapses whitespace/case/punctuation and strips a
# few leading filler words so restating the same fact actually overwrites
# it (the ON CONFLICT below then does real dedup instead of accumulation).
_LEADING_FILLER_RE = re.compile(r"^(my|the|a|an)\s+", re.IGNORECASE)


def normalize_key(raw_key: str) -> str:
    key = raw_key.strip().strip(".,!?").lower()
    key = _LEADING_FILLER_RE.sub("", key)
    key = re.sub(r"\s+", " ", key)
    return key[:60] or raw_key[:60]


def derive_key_and_value(fact_sentence: str):
    """Given the text after 'remember that ', split it into a normalized
    key (for dedup/lookup) and the full original sentence (for display and
    for the LLM context, so nothing is lost even though the key is lossy)."""
    if " is " in fact_sentence:
        raw_key = fact_sentence.split(" is ", 1)[0]
    elif " are " in fact_sentence:
        raw_key = fact_sentence.split(" are ", 1)[0]
    else:
        raw_key = fact_sentence[:40]
    return normalize_key(raw_key), fact_sentence.strip()


def remember_fact(key: str, value: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO facts (key, value, ts) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, ts=excluded.ts",
        (key, value, time.time()),
    )
    conn.commit()
    conn.close()


def get_fact(key: str):
    conn = _connect()
    row = conn.execute("SELECT value FROM facts WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None


def all_facts():
    conn = _connect()
    rows = conn.execute("SELECT key, value FROM facts").fetchall()
    conn.close()
    return dict(rows)


def facts_as_context() -> str:
    """Render remembered facts as a short context block for the LLM prompt.
    Capped at MAX_FACTS_IN_CONTEXT, most-recently-touched first, so a
    long-lived install doesn't silently balloon every prompt's size/cost."""
    conn = _connect()
    rows = conn.execute(
        "SELECT key, value FROM facts ORDER BY ts DESC LIMIT ?", (MAX_FACTS_IN_CONTEXT,)
    ).fetchall()
    conn.close()
    if not rows:
        return ""
    lines = [f"- {k}: {v}" for k, v in rows]
    return "Known facts about the user:\n" + "\n".join(lines)


def fact_count() -> int:
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    conn.close()
    return n


def forget_fact(key: str) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM facts WHERE key = ?", (key,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ---------- Tasks ----------
def _ensure_tasks_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            due_at REAL,
            status TEXT DEFAULT 'open',
            reminded INTEGER DEFAULT 0,
            source TEXT,
            ts REAL
        )
    """)


def add_task(description: str, due_at: float = None, source: str = "explicit") -> int:
    conn = _connect()
    _ensure_tasks_table(conn)
    cur = conn.execute(
        "INSERT INTO tasks (description, due_at, status, source, ts) VALUES (?, ?, 'open', ?, ?)",
        (description, due_at, source, time.time()),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def list_open_tasks():
    conn = _connect()
    _ensure_tasks_table(conn)
    rows = conn.execute(
        "SELECT id, description, due_at FROM tasks WHERE status = 'open' ORDER BY ts DESC"
    ).fetchall()
    conn.close()
    return rows  # [(id, description, due_at), ...]


def due_unreminded_tasks(now_ts: float):
    conn = _connect()
    _ensure_tasks_table(conn)
    rows = conn.execute(
        "SELECT id, description FROM tasks WHERE status='open' AND reminded=0 "
        "AND due_at IS NOT NULL AND due_at <= ?", (now_ts,)
    ).fetchall()
    conn.close()
    return rows


def tasks_due_between(start_ts: float, end_ts: float):
    """Open tasks due in [start_ts, end_ts), oldest-due first. Powers the
    tomorrow-agenda and proactive briefing without exposing full history."""
    conn = _connect()
    _ensure_tasks_table(conn)
    rows = conn.execute(
        "SELECT id, description, due_at FROM tasks WHERE status='open' "
        "AND due_at IS NOT NULL AND due_at >= ? AND due_at < ? ORDER BY due_at",
        (start_ts, end_ts),
    ).fetchall()
    conn.close()
    return rows


def mark_reminded(task_id: int):
    conn = _connect()
    conn.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def _like_escape(fragment: str) -> str:
    return fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def complete_task_matching(text_fragment: str) -> str:
    """Marks the most recent open task whose description contains text_fragment as done."""
    conn = _connect()
    _ensure_tasks_table(conn)
    row = conn.execute(
        "SELECT id, description FROM tasks WHERE status='open' AND description LIKE ? ESCAPE '\\' "
        "ORDER BY ts DESC LIMIT 1", (f"%{_like_escape(text_fragment)}%",)
    ).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute("UPDATE tasks SET status='done' WHERE id = ?", (row[0],))
    conn.commit()
    conn.close()
    return row[1]


# FEATURE (fix for "noisy passive detection, no easy way to review/delete
# except touching the sqlite file directly"): a voice/typed-reachable way
# to remove a task without needing a DB browser.
def delete_task_matching(text_fragment: str) -> str:
    """Deletes (not just completes) the most recent task — open or done —
    whose description contains text_fragment. Returns the deleted
    description, or None if nothing matched."""
    conn = _connect()
    _ensure_tasks_table(conn)
    row = conn.execute(
        "SELECT id, description FROM tasks WHERE description LIKE ? ESCAPE '\\' "
        "ORDER BY ts DESC LIMIT 1", (f"%{_like_escape(text_fragment)}%",)
    ).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute("DELETE FROM tasks WHERE id = ?", (row[0],))
    conn.commit()
    conn.close()
    return row[1]


def clear_auto_detected_tasks() -> int:
    """Bulk-removes every still-open task that came from passive detection
    (not something the user explicitly asked to be reminded of). Returns
    how many were removed, so the noisy 'I need to...' auto-logging has a
    one-shot undo instead of only manual per-task cleanup."""
    conn = _connect()
    _ensure_tasks_table(conn)
    cur = conn.execute(
        "DELETE FROM tasks WHERE source = 'auto_detected' AND status = 'open'"
    )
    conn.commit()
    removed = cur.rowcount
    conn.close()
    return removed


def tasks_as_context() -> str:
    tasks = list_open_tasks()
    if not tasks:
        return ""
    lines = []
    for _id, desc, due_at in tasks:
        due_str = f" (due {time.strftime('%Y-%m-%d %H:%M', time.localtime(due_at))})" if due_at else ""
        lines.append(f"- {desc}{due_str}")
    return ("The user's open tasks (mention relevant ones naturally, and suggest "
            "faster/smarter ways to get them done when it fits the conversation):\n"
            + "\n".join(lines))
