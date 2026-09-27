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

- `publicdata.py` (currency/crypto/holidays/country over free no-key APIs)
  — endpoint knowledge from bertrandmbanwi/Jarvis
  `jarvis/tools/public_data.py` (**MIT**); rewritten synchronously on 47's
  `request_with_retry`.
- `planner.py` multi-step runner (sequence-marker heuristics before any LLM
  call, steps through the normal command router) — heuristic idea from
  bertrandmbanwi/Jarvis `jarvis/agent/planner.py` (**MIT**); 47's runner and
  heuristics are its own code (no Claude/agents stack ported).
- Pending-confirmation TTL (60s expiry) — the server-granted-confirmation
  principle from bertrandmbanwi/Jarvis `jarvis/core/confirmation.py`
  (**MIT**); implemented on 47's per-context pending store.
- `tests/test_golden.py` deterministic eval harness — the golden-cases idea
  from bertrandmbanwi/Jarvis `evals/golden_cases.yml` (**MIT**).

## Adapted patterns (reimplemented, no code copied)

- `safety.yaml` extensible confirm policy — the `confirm_before` idea from
  JARVIS-6's `config.yaml` safety section (psycoks/Jarvis, no license file —
  idea only, 47's parser/loader written from scratch).
- Audit-trail idea (`audit.py`, local `audit_47.jsonl`) — inspired by
  `core/audit.py` in psycoks/Jarvis (JARVIS-6).
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
