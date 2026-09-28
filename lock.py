"""
47 lock screen — PIN-gated access to 47 itself and sensitive actions.

- First run: NO lock file exists -> setup mode. The user chooses a PIN in
  the dashboard setup flow (their requested initial PIN is entered there,
  never written into source, logs, tests, or docs).
- Stored: salt + PBKDF2-HMAC-SHA256 (200k rounds) JSON in .47_lock
  (owner-only file, gitignored). No plaintext anywhere.
- Unlock sessions live in memory only (15 min), never on disk.
- 5 wrong tries -> 5-minute lockout. No hint that reveals the PIN.
"""
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

LOCK_PATH = Path(__file__).parent / ".47_lock"
_ROUNDS = 200_000
_SESSION_TTL_S = 900
_MAX_FAILS = 5
_LOCKOUT_S = 300

_unlocked_until = 0.0
_fails = []
_lockout_until = 0.0


def is_configured() -> bool:
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        return bool(data.get("salt") and data.get("hash"))
    except (OSError, ValueError):
        return False


def _write(salt_hex: str, hash_hex: str):
    LOCK_PATH.write_text(json.dumps({"salt": salt_hex, "hash": hash_hex}),
                         encoding="utf-8")
    try:
        os.chmod(LOCK_PATH, 0o600)
    except OSError:
        pass


def set_pin(pin: str):
    """Create or change the PIN. Raises ValueError on weak input."""
    pin = (pin or "").strip()
    if not (pin.isdigit() and 4 <= len(pin) <= 12):
        raise ValueError("PIN must be 4-12 digits.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, _ROUNDS)
    _write(salt.hex(), digest.hex())


def _check_locked_out() -> float:
    """Remaining lockout seconds (0 when clear)."""
    global _fails, _lockout_until
    now = time.time()
    if now < _lockout_until:
        return _lockout_until - now
    _fails = [t for t in _fails if now - t < _LOCKOUT_S]
    return 0.0


def verify(pin: str):
    """Returns (ok, message). Rate-limited. Never logs the PIN."""
    global _fails, _lockout_until, _unlocked_until
    if not is_configured():
        return False, "No lock is set up yet."
    wait = _check_locked_out()
    if wait > 0:
        return False, f"Too many tries — locked for {int(wait)}s."
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        expect = bytes.fromhex(data["hash"])
        got = hashlib.pbkdf2_hmac("sha256", (pin or "").encode(),
                                  bytes.fromhex(data["salt"]), _ROUNDS)
        if hmac.compare_digest(expect, got):
            _fails = []
            _unlocked_until = time.time() + _SESSION_TTL_S
            return True, "Unlocked."
    except (OSError, ValueError, KeyError):
        pass
    _fails.append(time.time())
    if len(_fails) >= _MAX_FAILS:
        _lockout_until = time.time() + _LOCKOUT_S
        return False, "Too many tries — locked for 300s."
    left = _MAX_FAILS - len(_fails)
    return False, f"Wrong PIN. {left} tries left."


def is_unlocked() -> bool:
    return time.time() < _unlocked_until


def lock_now():
    global _unlocked_until
    _unlocked_until = 0.0


def reset_state():
    """Test seam: in-memory session/lockout only (never touches the file)."""
    global _unlocked_until, _fails, _lockout_until
    _unlocked_until = 0.0
    _fails = []
    _lockout_until = 0.0
