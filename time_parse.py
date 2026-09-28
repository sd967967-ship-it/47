"""Tiny relative-time parser: 'in 10 minutes', 'in 2 hours', 'in 1 day' -> unix timestamp.
No dependencies. Returns None if it can't parse a due time (task is still saved,
just without a scheduled reminder).
"""

import re
import time

_UNIT_SECONDS = {
    "second": 1, "seconds": 1, "sec": 1, "secs": 1,
    "minute": 60, "minutes": 60, "min": 60, "mins": 60,
    "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
    "day": 86400, "days": 86400,
}

# BUGFIX: alternation is tried left-to-right and regex doesn't backtrack to a
# *longer* match once a shorter one succeeds, so "seconds|second" (etc.) must
# list the longer form first — otherwise "10 minutes" matches only "minute"
# and leaves a stray trailing "s" in the remaining text.
_UNIT_PATTERN = (r"seconds|second|secs|sec|minutes|minute|mins|min|"
                  r"hours|hour|hrs|hr|days|day")

_PATTERN = re.compile(rf"in\s+(\d+)\s*({_UNIT_PATTERN})", re.IGNORECASE)

# BUGFIX (main.py handle_command): "remind me in 10 minutes to call the bank"
# needs the leading "remind me [in ...] [to]" stripped before this module ever
# sees it, or the stored task description ends up as the whole raw sentence.
_REMIND_PREFIX = re.compile(
    rf"^\s*(?:remind me|wake me(?: up)?|set an alarm(?: for me)?)\s*"
    rf"(in\s+\d+\s*(?:{_UNIT_PATTERN}))?\s*(to)?\s*", re.IGNORECASE,
)

# Clock times: "at 15:26", "at 3pm", "at 3:05 pm", "at 7".
_AT_PATTERN = re.compile(
    r"\bat\s+(\d{1,2})(?::|\s)?(\d{2})?\s*(am|pm)?\b", re.IGNORECASE)


def strip_reminder_prefix(text: str) -> str:
    """Strip a leading 'remind me [in N units] [to]' so the remaining text is
    just the task description (the 'in N units' part, if present, is put
    back at the end so parse_due() below can still find it)."""
    match = _REMIND_PREFIX.match(text)
    if not match:
        return text.strip()
    due_phrase = (match.group(1) or "").strip()
    rest = text[match.end():].strip(" .,")
    return f"{rest} {due_phrase}".strip() if due_phrase else rest


def parse_due(text: str):
    match = _PATTERN.search(text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        return time.time() + amount * _UNIT_SECONDS[unit]
    return _parse_at_time(text)


def _parse_at_time(text: str):
    """'at 15:26' / 'at 3pm' / 'at 7' -> next occurrence (today, or
    tomorrow if that time already passed). Returns None on no match."""
    import datetime as _dt
    match = _AT_PATTERN.search(text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = (match.group(3) or "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    now = _dt.datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target.timestamp() <= now.timestamp():
        target += _dt.timedelta(days=1)
    return target.timestamp()


def strip_due_phrase(text: str) -> str:
    """Remove the 'in N units' / 'at HH:MM' phrase from a task description."""
    text = _PATTERN.sub("", text)
    return _AT_PATTERN.sub("", text).strip(" .,")
