"""
47 permission registry — what 47 may touch, at which level, and why.

Levels: 0 read-only local · 1 one-time confirm · 2 preview confirm ·
3 final confirm, never unattended. Status strings are computed live;
nothing here grants anything — enforcement lives in actions/shell/main.
"""


def _approved_folders():
    try:
        import actions
        return [str(p) for p in actions._approved_roots()]
    except Exception:
        return []


def _key_state(name: str) -> str:
    try:
        import vault
        return "set" if vault.get(name) else "missing"
    except Exception:
        return "unknown"


def registry():
    import lock as _lock
    folders = _approved_folders()
    return [
        {"id": "microphone", "title": "Microphone", "level": "user gesture",
         "scope": "Browser tab only, while the Mic button is live",
         "status": "browser-managed", "last": "see browser site settings",
         "reason": "Voice typing; push-to-talk, never background recording."},
        {"id": "speaker", "title": "Speaker / voice", "level": 0,
         "scope": "This laptop's speakers",
         "status": "on", "last": "each reply",
         "reason": "Spoken answers; queued, interruptible by stopping 47."},
        {"id": "files", "title": "Files & folders", "level": "0 read / 2 write",
         "scope": "; ".join(folders) or "none",
         "status": "scoped", "last": "each file command",
         "reason": "Find/read approved files; writes and cloud sends need confirm."},
        {"id": "shell", "title": "Terminal commands", "level": "2-3",
         "scope": "Any command you utter; destructive + safety.yaml need confirm",
         "status": "gated", "last": "each run (audit log)",
         "reason": "Real shell access; blocked while stopped."},
        {"id": "browser", "title": "Browser & sites", "level": "1 open / 2 act",
         "scope": "Opens sites you name; automation is visible + confirmed",
         "status": "gated", "last": "each action (audit log)",
         "reason": "No logins, paywalls, or CAPTCHAs ever bypassed."},
        {"id": "tasks", "title": "Tasks & reminders", "level": 1,
         "scope": "Local task store",
         "status": "on", "last": "each reminder",
         "reason": "Spoken alerts for due items; nothing leaves the laptop."},
        {"id": "memory", "title": "Long-term memory", "level": "1 save / 3 erase-all",
         "scope": "Local SQLite facts + history",
         "status": "on", "last": "each remember/forget",
         "reason": "Only what you approve; erase-all needs confirm" +
                   (" + unlock" if _lock.is_configured() else "") + "."},
        {"id": "mcp", "title": "MCP servers", "level": "2",
         "scope": "Approved stdio servers only",
         "status": "gated", "last": "each tool call (audit log)",
         "reason": "Model plans, 47 executes; outputs treated as untrusted."},
        {"id": "camera", "title": "Camera", "level": "2 per use",
         "scope": "Single snapshot only when you ask",
         "status": "off unless asked", "last": "never continuous",
         "reason": "One photo per request, then discarded."},
        {"id": "lock", "title": "Agent lock", "level": "3 areas",
         "scope": "Guards erase-all, exports, settings, resume",
         "status": "set" if _lock.is_configured() else "not set",
         "last": "each unlock attempt (rate-limited)",
         "reason": "PIN-gated sensitive areas; hash-only storage."},
        {"id": "keys", "title": "API keys", "level": "server-side",
         "scope": "XAI_API_KEY: " + _key_state("XAI_API_KEY")
                  + " · GROQ_API_KEY: " + _key_state("GROQ_API_KEY"),
         "status": "server-side only", "last": "never logged",
         "reason": "Env/keyring/.47_env only; redacted everywhere else."},
    ]
