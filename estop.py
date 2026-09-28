"""
47 emergency stop — one action halts everything pending.

STOP blocks: shell runs, desktop control, browser automation, TTS queue,
focus timers, proactive loop iterations, and any new handle_command tool
work. It never deletes files, cancels sent messages, or corrupts state —
only future/pending activity stops. Resume is explicit and, when a lock
is configured, requires an unlock first.
"""
import threading
import time

_lock = threading.Lock()
_stopped = False
_stopped_at = 0.0
_last_stop = None


def stop(source: str, detail: str = "") -> dict:
    """Engage the stop. Returns the audit record. Idempotent."""
    global _stopped, _stopped_at, _last_stop
    cancelled = []
    try:
        import tts_jarvis
        tts_jarvis.clear_queue()
        cancelled.append("speech queue")
    except Exception:
        pass
    try:
        import focus as _focus
        live = _focus.status()
        _focus.reset()
        if live:
            cancelled.append(f"{len(live)} focus session(s)")
    except Exception:
        pass
    with _lock:
        _stopped = True
        _stopped_at = time.time()
        _last_stop = {"ts": _stopped_at, "source": source[:40],
                      "detail": detail[:200], "cancelled": cancelled}
        record = dict(_last_stop)
    try:
        import audit as _audit
        _audit.record("estop", **record)
    except Exception:
        pass
    return record


def resume() -> bool:
    """Release the stop. Returns False when nothing was stopped."""
    global _stopped
    with _lock:
        was = _stopped
        _stopped = False
    if was:
        try:
            import audit as _audit
            _audit.record("estop.resume", ts=time.time())
        except Exception:
            pass
    return was


def is_stopped() -> bool:
    with _lock:
        return _stopped


def status() -> dict:
    with _lock:
        return {"stopped": _stopped, "stopped_at": _stopped_at,
                "last": _last_stop}


def reset_state():
    """Test seam."""
    global _stopped, _stopped_at, _last_stop
    with _lock:
        _stopped = False
        _stopped_at = 0.0
        _last_stop = None
