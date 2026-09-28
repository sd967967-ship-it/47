# 47 — High-Level Design (HLD)

## 1. Components
| Component | Role | Tech |
|---|---|---|
| Exact React frontend | Main UI (chat, tasks, memory, activity, permissions, health, lock, e-stop) | React + TanStack Start, node :4173, SSR |
| Classic dashboard | Fallback single-file UI | `templates/dashboard.html`, Three.js r128 |
| Flask core (`main.py`) | Routing, approvals, pages, APIs, proxy | Flask + Flask-SocketIO :5000 |
| Brain seam (`providers/`) | One active LLM: Groq live, Grok one-key swap | `providers/__init__.py` key-presence pick |
| Local modules | Memory, files, shell, desktop, browser, TTS, watch, planner… | 27 stdlib-first Python modules |
| Stores | Facts/history/tasks, audit log, secrets, lock, index | SQLite + JSONL + 0600 files (gitignored) |

## 2. Trust boundaries
1. **Browser → Flask**: dashboard token (`?token=`, constant-time compare);
   localhost-only bind; CORS locked; all `/api/*` gated.
2. **Model → 47**: model text never executes; tools run only through 47's
   registry with confirm gates; tool/web/file output is untrusted data.
3. **Secrets**: env → OS keyring → `.47_env`; redacted in every log path.
4. **Files**: approved folders only; writes + cloud sends need per-item OK.

## 3. Network map
- `127.0.0.1:5000` Flask (UI, API, socket, proxy).
- `127.0.0.1:4173` node SSR (exact frontend origin server).
- Outbound only: `api.groq.com` (brain), keyless public APIs
  (weather/currency/crypto/holidays/countries/news), CDN (three.js/fonts).
- No inbound except localhost; no LAN exposure by default.

## 4. Data stores
- `memory_47.db`: `facts(key,value,ts)`, `conversation(role,content,ts)`,
  `tasks(id,description,due_at,status,reminded,source,ts)`.
- `audit_47.jsonl`: append-only tool/approval/feedback/e-stop events.
- `watch_state.json`: seen headlines. `.47_file_index.json`: filename map.

## 5. Failure modes
No brain key → degraded chat, local features live. Node down → 502 with
plain message (`/classic` fallback). Rate limit → friendly message.
Locked → PIN gate. Stopped → tool refusal until resume (+ unlock).
