"""
47 local audit trail — append-only JSONL of tool/shell/desktop actions.

Stays on this machine (audit_47.jsonl next to this file), never uploaded.
Inspired by the audit pattern in psycoks/Jarvis (JARVIS-6) core/audit.py —
reimplemented here from scratch for 47 (no upstream code copied, since that
repo ships no license file). Prompt-template idea (prompts/*.yaml) comes
from bertrandmbanwi/Jarvis, which is MIT licensed — see prompts/ headers.
"""
import json
import threading
import time
from pathlib import Path

AUDIT_PATH = Path(__file__).parent / "audit_47.jsonl"
_lock = threading.Lock()


def record(event: str, **fields):
    """Append one audit entry. Never raises — auditing must not break actions."""
    try:
        entry = {"ts": time.time(), "event": event, **fields}
        with _lock:
            with open(AUDIT_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def read(limit: int = 100):
    """Return the last `limit` entries (for 'show audit log' review)."""
    try:
        with _lock:
            with open(AUDIT_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-max(1, min(limit, 2000)):]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
