# Third-party sources used by 47

47's core is original code. The items below are adapted or vendored from the
repos the owner listed, with licenses respected. Nothing here phones home —
all of it runs locally.

## Vendored files (copied with headers intact)

- `prompts/research.yaml`, `prompts/fix.yaml` — from
  bertrandmbanwi/Jarvis `templates/prompts/` (**MIT licensed**), used by
  `prompts.py` to structure 47's `research <topic>` answers and bug-fix
  writeups.

## Adapted patterns (reimplemented, no code copied)

- Audit-trail idea (`audit.py`, local `audit_47.jsonl`) — inspired by
  `core/audit.py` in psycoks/Jarvis (JARVIS-6). That repo ships **no license
  file**, so its code was NOT copied; 47's module is written from scratch.
- Destructive/privileged tool flags (confirm gates in `shell.py`,
  `desktop.py`) — same inspiration source as above, reimplemented.
- `duckduckgo-search` (DDGS) for real web results in `actions.web_search` —
  same library JARVIS-6's registry uses; used as a pip dependency.
- Playwright persistent-profile browser (`browser.py`) and PyAutoGUI desktop
  control (`desktop.py`) — standard usage of those PyPI packages, same
  approach as the listed Jarvis repos.
- Local Whisper STT option (`VOICE_RECOGNIZER=whisper`) — same
  faster-whisper library JARVIS-6 uses.
- `WAKE_WORD` env hook — same idea as openWakeWord-based assistants; the
  openWakeWord engine itself is NOT bundled (needs onnxruntime + audio
  setup), see README for the optional path.

## Not imported (checked, skipped deliberately)

- `kymaman/jarvis` — does not exist on GitHub (404).
- `isair/jarvis` (13MB desktop app), `PersonalJarvis/PersonalJarvis`
  (4,000+ commits), `microsoft/playwright` (whole framework) — far too large
  to merge; relevant ideas already covered above.
- `dscripka/openWakeWord` engine — heavy native dep; documented as optional.
