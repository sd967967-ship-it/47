"""
47 secrets vault — server-side only, never leaves this machine.

Lookup order for a secret name (e.g. "XAI_API_KEY"):
  1. Environment variable (highest priority — good for sessions).
  2. OS keyring via the optional `keyring` package (Windows Credential
     Locker / macOS Keychain / Linux Secret Service), service "47".
  3. `.47_env` file next to this module (KEY=VALUE lines), created with
     owner-only permissions where the platform supports it.

Rule (spec): secrets must never appear in frontend bundles, browser
storage, source code, screenshots, logs, error messages, commits, or docs.
Use redact() before logging anything that might contain a key.
"""
import os
import re
from pathlib import Path

_ENV_PATH = Path(__file__).parent / ".47_env"

_KEY_LIKE = re.compile(r"\b((?:gsk|xai|sk-ant|sk)-[A-Za-z0-9_\-]{8,})\b")


def get(name: str) -> str:
    """Return the secret value or '' when absent. Never raises."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        import keyring
        value = keyring.get_password("47", name) or ""
        if value:
            return value.strip()
    except Exception:
        pass
    try:
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == name:
                return val.strip().strip("\"'")
    except OSError:
        pass
    return ""


def set_file(name: str, value: str):
    """Persist a secret to .47_env (owner-only file). For local desktop use."""
    lines = []
    try:
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        pass
    lines = [ln for ln in lines if ln.partition("=")[0].strip() != name]
    lines.append(f"{name}={value}")
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(_ENV_PATH, 0o600)
    except OSError:
        pass


def redact(text: str) -> str:
    """Replace key-like strings with <REDACTED>. Apply before any logging."""
    if not text:
        return text
    return _KEY_LIKE.sub("<REDACTED>", text)
