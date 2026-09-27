"""
Real command-prompt access for 47 — this is what lets it run anything you'd
type into a terminal yourself, including as admin/root.

Design, explained once so it's clear what's a real limit vs. a deliberate
choice:

- 47 is voice-activated and its speech recognizer is transcribing
  continuously in the background, not just after the wake word — that's
  how the wake-word check works at all. Free recognizers do occasionally
  mishear background noise/TV/other conversation as words. Giving *that*
  channel an unconfirmed direct line to something like "format C:" is how
  people lose a drive to a misheard sentence, not to anything you asked
  for. So: every normal command — including admin-elevated ones — runs
  immediately with zero friction, exactly as asked. The ONE exception is a
  command that matches an unmistakably destructive pattern (mass delete,
  disk format/partition, raw disk writes, shutdown/reboot), which requires
  one extra spoken or typed word — "confirm" — before it runs. That's a
  single word, not a form.

- Elevation ("as admin"/"as administrator") is real: on Windows it triggers
  an actual UAC prompt; on macOS/Linux it shells out to `sudo`. Both of
  those are the *operating system's own* elevation gate, not something 47
  adds on top — no local app can hand out admin rights without going
  through it, and this project isn't going to help disable that gate
  itself (that's a real, hard line, not a style choice).

HONESTY ABOUT WHAT THE CONFIRMATION GATE IS AND ISN'T:
The destructive-command regex below is a *speed bump for an accidental
misfire* — a mis-transcribed word, a fat-fingered typo, an ambiguous phrase.
It is NOT a security boundary. It's a fixed set of patterns; anyone who
actually wants to do something destructive on purpose can trivially phrase
around it (a different flag, a one-liner in another language, an alias, a
script file). Real access control lives one layer up, in main.py: whether
an unauthenticated stranger can reach this module's `run()` at all in the
first place. See main.py's dashboard-auth comments for that half of it.
"""

import ctypes
import os
import platform
import re
import shlex
import subprocess
import tempfile
import threading

# Patterns worth a single spoken "confirm" before running: irreversible data
# loss, disk-level operations, and system power state. Deliberately narrow —
# this is not a general permission system, just a seatbelt for the handful
# of commands where "typed/heard wrong" and "oops" are the same event.
# Widened beyond the original list to also catch the most common one-line
# rephrasings of the same operations (Python's shutil.rmtree, PowerShell's
# Remove-Item -Recurse -Force, a classic bash fork bomb) — still just a
# speed bump, not a claim of completeness (see module docstring above).
_DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b", r"\brm\s+-r\s+--force\b", r"\bdel\s+/s\b", r"\brmdir\s+/s\b",
    r"\bdiskpart\b", r"\bmkfs\.", r"\bformat\s+[a-z]:", r"\bdd\s+if=",
    r"\bshutdown\b", r"\breboot\b", r"\bhalt\b", r">\s*/dev/sd[a-z]",
    r"\breg\s+delete\b", r"\bnet\s+user\b.*\bdelete\b", r"\bdel\s+/f\s+/s\s+/q\b",
    r"shutil\.rmtree", r"remove-item\b.*-recurse", r":\(\)\s*\{\s*:\s*\|\s*:\s*&?\s*\}\s*;",
    r"\bchmod\s+-r\s+777\s+/", r"\bformat-volume\b",
]
_DESTRUCTIVE_RE = re.compile("|".join(_DESTRUCTIVE_PATTERNS), re.IGNORECASE)

# Extensible safety policy (safety.yaml, JARVIS-6 `confirm_before` idea):
# extra regexes requiring "confirm", so new risky patterns can be added
# without code changes. Parsed minimally (no PyYAML dep) and cached.
_SAFETY_PATH = os.environ.get("47_SAFETY_YAML") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "safety.yaml")
_extra_patterns = []
_extra_mtime = 0.0


def _load_extra_patterns(path: str = None):
    global _extra_patterns, _extra_mtime
    target = path or _SAFETY_PATH
    try:
        mtime = os.path.getmtime(target)
    except OSError:
        return _extra_patterns
    if target == _SAFETY_PATH and mtime == _extra_mtime:
        return _extra_patterns
    patterns = []
    try:
        with open(target, "r", encoding="utf-8") as f:
            in_list = False
            for line in f:
                stripped = line.strip()
                if stripped.startswith("confirm_before:"):
                    in_list = True
                    continue
                if in_list:
                    if stripped.startswith("- "):
                        pat = stripped[2:].strip().strip("\"'")
                        if pat:
                            patterns.append(pat)
                    elif stripped and not stripped.startswith("#"):
                        in_list = False
        compiled = [p for p in patterns if p]
        # Validate all compile; a bad line must not kill the shell module.
        for p in compiled:
            re.compile(p)
    except (OSError, re.error):
        return _extra_patterns
    if target == _SAFETY_PATH:
        _extra_patterns = compiled
        _extra_mtime = mtime
        return _extra_patterns
    return compiled


def needs_confirmation(command: str, safety_path: str = None) -> bool:
    if _DESTRUCTIVE_RE.search(command):
        return True
    extra = _load_extra_patterns(safety_path)
    return any(re.search(p, command, re.IGNORECASE) for p in extra)

# BUGFIX: the old module kept exactly one pending confirmation in a single
# global dict. That's fine for the voice loop (there's only ever one "47" to
# talk to), but the typed dashboard box can have several browser tabs open
# at once (several socket sessions), and a destructive command staged by
# tab A used to get silently overwritten — or confirmed! — by tab B typing
# anything. Pending state is now keyed per *context* (the voice loop uses
# the fixed key "voice"; each dashboard socket connection uses its own
# session id), so one context's staged command can't leak into another's.
_pending = {}
_lock = threading.Lock()


# Confirmations expire after 60s so a hours-later accidental "confirm"
# can't fire a stale destructive command (and the confirm reply restates
# the command — server-side grant, never model-supplied).
_PENDING_TTL_S = 60


def stage_for_confirmation(context_id: str, command: str, elevate: bool):
    import time as _t
    with _lock:
        _pending[context_id] = (command, elevate, _t.time())


def has_pending(context_id: str) -> bool:
    import time as _t
    with _lock:
        item = _pending.get(context_id)
        if not item:
            return False
        if _t.time() - item[2] > _PENDING_TTL_S:
            _pending.pop(context_id, None)
            return False
        return True


def pop_pending(context_id: str):
    with _lock:
        item = _pending.pop(context_id, (None, False, 0.0))
    return item[0], item[1]


def run(command: str, elevate: bool = False, timeout: int = 60) -> str:
    """Runs `command` in the real OS shell (cmd.exe / sh) and returns
    combined stdout+stderr, truncated for speech/dashboard display."""
    try:
        import audit as _audit
        _audit.record("shell.run", command=command[:300], elevate=elevate)
    except Exception:
        pass
    system = platform.system()
    try:
        if elevate:
            if system == "Windows":
                return _run_elevated_windows(command, timeout)
            else:
                result = subprocess.run(
                    ["sudo"] + shlex.split(command),
                    capture_output=True, text=True, timeout=timeout,
                )
                output = (result.stdout or "") + (result.stderr or "")
                return (output.strip() or "(ran with no output)")[:1500]
        else:
            if system == "Windows":
                result = subprocess.run(
                    ["cmd.exe", "/c", command],
                    capture_output=True, text=True, timeout=timeout,
                )
            else:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=timeout,
                )
            output = (result.stdout or "") + (result.stderr or "")
            return (output.strip() or "(ran with no output)")[:1500]
    except subprocess.TimeoutExpired:
        return f"That command timed out after {timeout} seconds."
    except Exception as e:
        return f"Couldn't run that: {e}"


def _run_elevated_windows(command: str, timeout: int) -> str:
    """Runs an elevated command on Windows and actually captures its output.

    FIX for "elevated commands open a black window we can't see into": the
    old code used ShellExecuteW('runas', 'cmd.exe', '/k command', ...),
    which opens a *separate* interactive window with no pipe back to this
    process — there is no way to read stdout/stderr across that boundary,
    full stop, so this couldn't previously tell you whether the command
    even succeeded.

    The fix: elevate a short-lived PowerShell whose only job is to run the
    real command with output redirected into a temp file, `Wait` for it
    from *this* (non-elevated) process via `Start-Process -Wait`, then read
    the temp file back once it exits. This does mean a second UAC prompt
    is what you're approving (for the launcher, not the command itself) —
    that's the OS's elevation gate again, not something to route around.
    """
    fd, outfile = tempfile.mkstemp(suffix=".47out.txt")
    os.close(fd)
    try:
        ps_inner = f'cmd /c "{command}" > "{outfile}" 2>&1'
        ps_inner_escaped = ps_inner.replace('"', '\\"')
        launcher = (
            f"Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden "
            f"-ArgumentList '-NoProfile','-Command','{ps_inner_escaped}'"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", launcher],
            capture_output=True, text=True, timeout=timeout,
        )
        try:
            with open(outfile, "r", errors="replace") as f:
                output = f.read().strip()
        except OSError:
            output = ""
        if not output and result.returncode != 0:
            return ("Ran elevated, but couldn't capture output (the UAC "
                    "prompt may have been declined). Exit indicator: "
                    f"{(result.stderr or result.stdout or '').strip()[:300]}")
        return output[:1500] or "(ran elevated with no output)"
    except subprocess.TimeoutExpired:
        return f"That elevated command timed out after {timeout} seconds."
    except Exception as e:
        return f"Couldn't run that elevated: {e}"
    finally:
        try:
            os.remove(outfile)
        except OSError:
            pass
