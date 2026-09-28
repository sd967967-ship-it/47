# 47 — Architecture

## 1. What 47 is
Voice-first personal AI companion (Windows laptop, Python 3.12). One active
cloud brain behind a provider seam, local-first everything else: memory,
files, tasks, 3D visuals, dashboard, audit. No local model inference.

## 2. Runtime layout

```
Browser (exact React app :4173, proxied)   user voice / mic
        │ token-gated Flask :5000 (main.py)          │
        ├─ SocketIO: user_text_command / unlock_attempt / set_pin / lock_now
        ├─ REST: /api/* (tasks, memory, audit, chat, health, …)
        ├─ Brain: providers/{groq.py (live), grok.py (ready)} — ONE active
        ├─ Local modules: memory, actions, shell, docs, desktop, browser,
        │   ambient, watch, planner, publicdata, media, wifi, focus,
        │   visual3d, models3d, prompts, persona, readability, tts_jarvis,
        │   vision, mcp_client, net_utils, vault, lock, estop, permissions,
        │   audit, home, time_parse, help_catalog
        └─ Stores (gitignored): memory_47.db (SQLite), audit_47.jsonl,
            watch_state.json, .47_dashboard_token, .47_env, .47_lock,
            .47_file_index.json
```

## 3. Request path (chat/voice command)
1. Mic/typed text → `handle_command(text, context_id)` (`main.py`).
2. E-stop gate → pending-confirm gate → passive task scan → 3D push.
3. Planner: sequence words split work into ordered steps (same router).
4. Command branches (files, media, docs, wifi, tasks, …) or `ask_brain`.
5. `ask_brain`: context (facts+tasks, capped) + history (20, truncated) →
   active provider → optional MCP tool plan (max 2, executed locally) →
   `readability.style_reply` → log → push text + speak (queued TTS).

## 4. Trust boundaries
- Browser → Flask: dashboard token (`?token=`, compared with
  `secrets.compare_digest`), localhost-only bind, CORS locked to the app.
- Model → 47: model text is NEVER executed; tools run only via 47's
  registry with confirm gates; tool/web/file content is untrusted input.
- Secrets: env → OS keyring → `.47_env`; redacted in logs (`vault.redact`).
- Files: approved folders only (`47_APPROVED_FOLDERS`, default
  Documents/Desktop/Downloads/Pictures); writes and cloud sends need
  per-item confirmation.

## 5. Concurrency model
Flask-SocketIO threads: voice loop, ambient (5s vitals), proactive
(30 min briefings), window tracking, task reminders (15s), TTS worker.
Supervisor restarts crashed threads with backoff. TTS is queued and
non-blocking; speech is sentence-chunked.

## 6. Frontends
- `/` → exact React build (node :4173) via token-gated reverse proxy;
  static assets public (fingerprinted, no data).
- `/classic` → single-file fallback dashboard (same protocol).
- React app calls `/api/*` with the page token; chat via `/api/chat`.

## 7. Failure modes
No brain key → "temporarily unavailable", local features live. Node down →
502 with plain message. Rate limit → friendly message. Locked → PIN gate.
Stopped → tool refusal until resume (+ unlock when configured).
