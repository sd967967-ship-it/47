"""
47 focus timer — Pomodoro-style sessions with a spoken finish.

Deep module, tiny interface: start/stop/status. The completion callback
(speak + dashboard push) is injected, so tests pass a recorder instead of
audio. Sessions live in-process; stopping the app ends them (stated
honestly in help text, not presented as durable).
"""
import threading
import time

_sessions = {}
_lock = threading.Lock()
_next_id = 1


def start_focus(minutes: float, label: str, on_done) -> int:
    """Start a focus session; on_done(session) fires after `minutes`."""
    global _next_id
    minutes = max(0.05, min(240, float(minutes)))
    with _lock:
        sid = _next_id
        _next_id += 1
        session = {"id": sid, "label": label or "focus",
                   "minutes": minutes, "ends_at": time.time() + minutes * 60,
                   "done": False}
        timer = threading.Timer(minutes * 60, _finish, args=(sid,))
        timer.daemon = True
        session["timer"] = timer
        session["on_done"] = on_done
        _sessions[sid] = session
        timer.start()
    return sid


def _finish(sid: int):
    with _lock:
        session = _sessions.get(sid)
        if not session or session["done"]:
            return
        session["done"] = True
    try:
        session["on_done"]({k: v for k, v in session.items() if k != "on_done"})
    except Exception:
        pass


def stop_focus(sid: int = None) -> bool:
    """Stop one (or the latest) session. Returns True if one was live."""
    with _lock:
        if sid is None:
            live = [s for s in _sessions.values() if not s["done"]]
            if not live:
                return False
            session = max(live, key=lambda s: s["id"])
        else:
            session = _sessions.get(sid)
            if not session or session["done"]:
                return False
        session["done"] = True
        try:
            session["timer"].cancel()
        except Exception:
            pass
        return True


def status():
    with _lock:
        return [{k: v for k, v in s.items() if k not in ("on_done", "timer")}
                for s in _sessions.values() if not s["done"]]


def reset():
    """Test seam."""
    global _next_id
    with _lock:
        for s in _sessions.values():
            try:
                s["timer"].cancel()
            except Exception:
                pass
        _sessions.clear()
        _next_id = 1
