# 47 — MVP scope

## In v1 (shipped)
Chat (voice+typed), tasks/reminders/alarms, approved-folder files + study
assistant, media (YouTube/Google/photos), system insight + wifi scan, free
public data (weather/currency/crypto/holidays/country), proactive briefings,
always-3D dashboard with `.glb` library, command palette + catalog, lock
screen, emergency stop, guided memory erase, permission/health views, audit
trail, exact React frontend + single-file fallback.

## Deferred (with reasons)
- TripoSR image-to-3D: ~1GB weights, disk too full; hook documented in
  `assets/models/SOURCE.md`. Needs free space first.
- openWakeWord engine: native audio/ML dep; `WAKE_WORD` hook ready.
- Calendar sync: needs OAuth account flow; tasks cover scheduling for now.
- Email sending: stub only; irreversible external action, stays gated.
- Streaming replies: provider supports SSE; dashboard streaming not wired.
- Multi-user/hosted mode: single-operator product by design.

## MVP exit criteria
Suite green, no secrets in repo, every visible control live or labeled,
degraded mode verified (no key → local features work).
