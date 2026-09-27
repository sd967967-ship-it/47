"""
47 proactive watch — the "robot inside the computer" layer.

Small interface, deep-enough implementation (codebase-design: one module,
one seam):
  - get_world_headlines(limit) -> list[str]   (Hacker News, free, no key)
  - new_headlines() -> list[str]              (unseen since last check)
  - agenda_text() -> str                      (today + tomorrow from tasks)
  - startup_briefing() -> str                 (one spoken summary on boot)

Everything stays local except the keyless headline fetch. Seen-story state
lives in watch_state.json next to this file — never uploaded.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from net_utils import request_with_retry

STATE_PATH = Path(__file__).parent / "watch_state.json"
_WORLD_TTL_S = 3600

_cache = {"at": 0.0, "headlines": []}


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"seen": [], "last_brief": 0.0}


def _save_state(state: dict):
    try:
        STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def get_world_headlines(limit: int = 5) -> list:
    """Top Hacker News titles, cached 60 min. Free, no API key."""
    now = time.time()
    if _cache["headlines"] and now - _cache["at"] < _WORLD_TTL_S:
        return _cache["headlines"][:limit]
    try:
        ids = request_with_retry(
            "GET", "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=15,
        ).json()[: max(1, min(limit, 10)) * 2]
        titles = []
        for story_id in ids:
            if len(titles) >= limit:
                break
            try:
                item = request_with_retry(
                    "GET", f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10,
                ).json()
                title = (item or {}).get("title", "").strip()
                if title:
                    titles.append(title)
            except Exception:
                continue
        if titles:
            _cache.update(at=now, headlines=titles)
            return titles[:limit]
    except Exception:
        pass
    return list(_cache["headlines"][:limit])


def new_headlines(limit: int = 3) -> list:
    """Headlines not seen in previous checks (marks them seen)."""
    state = _load_state()
    seen = set(state.get("seen", []))
    fresh = [h for h in get_world_headlines(limit * 2) if h not in seen][:limit]
    if fresh:
        state["seen"] = sorted(seen | set(fresh))[-60:]
        _save_state(state)
    return fresh


def agenda_text() -> str:
    """Today's + tomorrow's due tasks, from the local task store."""
    import memory
    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_tomorrow = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                    + timedelta(days=2)).timestamp()
    rows = memory.tasks_due_between(start_today, end_tomorrow)
    if not rows:
        return "Nothing scheduled for today or tomorrow."
    lines = []
    for _id, desc, due_at in rows:
        day = "today" if due_at < start_today + 86400 else "tomorrow"
        when = datetime.fromtimestamp(due_at).strftime("%H:%M")
        lines.append(f"- {desc} ({day} {when})")
    return "Coming up:\n" + "\n".join(lines)


def startup_briefing() -> str:
    """One short spoken summary for boot: time, tasks, top story."""
    import memory
    now = datetime.now().strftime("%H:%M")
    try:
        open_tasks = len(memory.list_open_tasks())
    except Exception:
        open_tasks = 0
    heads = get_world_headlines(limit=1)
    parts = [f"It's {now}. You have {open_tasks} open task{'s' if open_tasks != 1 else ''}."]
    if heads:
        parts.append(f"Top story right now: {heads[0]}.")
    parts.append("I'm watching your system and the headlines — I'll speak up if anything needs you.")
    return " ".join(parts)


def is_daytime() -> bool:
    return 8 <= datetime.now().hour < 22
