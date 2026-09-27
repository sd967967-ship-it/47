"""
47 task planner — multi-step requests run as ordered steps.

Heuristic idea from bertrandmbanwi/Jarvis jarvis/agent/planner.py (MIT):
check complexity markers BEFORE any LLM call so simple requests never pay
for planning. 47's version is its own code: split on sequence markers and
run each step through the normal command router in order (each step keeps
its own confirm gates, memory logging, and dashboard output).
"""
import re

MAX_STEPS = 4

_SEQUENCE_SPLIT = re.compile(
    r"\s*(?:and then|after that|followed by|finally|then|next|;)\s*",
    re.IGNORECASE,
)

_SEQUENCE_HINTS = re.compile(
    r"\b(then|after that|followed by|finally|first\b.*\bthen|step \d|and then)\b",
    re.IGNORECASE,
)

_ACTION_VERBS = (
    "search", "find", "research", "open", "browse", "send", "email",
    "create", "write", "read", "summarize", "run", "execute", "remind",
    "convert", "fetch", "weather",
)


def split_steps(text: str) -> list:
    """Split a compound request on sequence markers. Returns 1+ steps."""
    parts = [p.strip(" ,.") for p in _SEQUENCE_SPLIT.split(text)]
    return [p for p in parts if p][:MAX_STEPS]


def needs_plan(text: str) -> bool:
    """True when the request looks multi-step: a sequence marker plus 2+
    distinct action verbs (or 3+ split parts). Cheap — no LLM call."""
    parts = split_steps(text)
    if len(parts) < 2:
        return False
    if not _SEQUENCE_HINTS.search(text):
        return False
    lowered = text.lower()
    verbs = sum(1 for v in _ACTION_VERBS if v in lowered)
    return verbs >= 2 or len(parts) >= 3
