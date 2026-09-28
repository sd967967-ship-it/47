# 47 — Low-Level Design (LLD)

## 1. Entry points
- `python main.py` → prints token URL, opens browser, serves :5000.
- `python -m unittest discover -s tests` → full suite (must be green).

## 2. HTTP routes (`main.py`)
| Route | Auth | Purpose |
|---|---|---|
| `GET /` | token | Exact React app (node proxy) |
| `GET /today /tasks /calendar /notes /projects /focus /memory /activity /settings` | token | Same proxy |
| `GET /assets/*` | public | Fingerprinted build assets |
| `GET /classic` | token | Fallback single-file dashboard |
| `GET /models/<name>` | token | `.glb` allowlist (`models3d`) |
| `GET /api/commands` | token | `help_catalog.GROUPS` |
| `GET /api/tasks` · `POST /api/tasks/complete` | token | List / complete by id |
| `GET /api/memory` · `DELETE /api/memory/<key>` | token | Facts (+unlock-gated erase-all via chat) |
| `GET /api/audit` | token | Last 50 audit entries |
| `POST /api/feedback` | token | `{rating: helpful\|not-helpful, excerpt}` |
| `POST /api/chat` | token | `{text}` → full pipeline → `{reply}` |
| `GET /api/status /permissions /health` | token | Brain, folders, perms, health (no secrets) |
| `GET /api/lock/status` · `POST /api/lock/setup /unlock` | token | PIN setup/verify (never logged) |
| `POST /api/estop` | token | `{action: stop\|resume}` |
| `GET/POST/DELETE /api/focus` | token | Focus timer status/start/stop |

Socket events: `connect/disconnect` (token), `user_text_command`,
`unlock_attempt`, `set_pin`, `lock_now`. Outgoing: `data_47`
(`text|bars|network|object3d|model3d|vitals|window|briefing|approval|estop`).

## 3. Key module interfaces
- `providers/__init__.get_active_provider()` → `(module, name)|None`.
  Provider seam: `send_message`, `request_tool_plan`, `health_check`.
- `vault.get/set_file/redact`; `lock.set_pin/verify/is_unlocked`;
  `estop.stop/resume/is_stopped`; `shell.run/stage/needs_confirmation`
  (60s TTL pending); `memory.*` (facts/tasks/history/erase/stats);
  `actions._safe_resolve` (approved-root jail); `docs.extract_text`;
  `planner.needs_plan/split_steps`; `time_parse.parse_due`;
  `tts_jarvis.speak` (queued) + `clean_for_speech`; `watch.*` (headlines,
  agenda); `permissions.registry()`; `help_catalog.GROUPS/as_text`.

## 4. Environment (see `.env.example`, placeholders only)
`XAI_API_KEY`, `GROQ_API_KEY`, `GROQ_MODEL`, `DASHBOARD_TOKEN/HOST/PORT`,
`47_APPROVED_FOLDERS`, `47_SAFETY_YAML`, `47_NOTES_DIR`, `47_PROACTIVE`,
`WAKE_WORD`, `VOICE_RECOGNIZER`, `JARVIS_VOICE`, `HA_URL/HA_TOKEN`.

## 5. Tests → modules (`tests/`)
`test_ask_brain` (provider selection), `test_lock_estop`, `test_safety`,
`test_shell`, `test_memory`, `test_time_parse`, `test_planner`,
`test_visual3d`, `test_dashboard` (template guards), `test_help`,
`test_audit_prompts`, `test_watch`, `test_publicdata`, `test_images`,
`test_media`, `test_docs`, `test_tts_clean`, `test_readability`,
`test_models_persona`, `test_golden`, `test_actions`, `test_net_utils`.
