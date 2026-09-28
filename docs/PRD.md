# 47 — Product Requirements (PRD)

## Vision
A calm, voice-first personal companion for one owner's laptop and daily
life: tasks, files, study, media, system insight, and proactive briefings —
secure by default, useful without nagging.

## Users
Single operator (this machine only). No multi-user, no hosted service.

## Functional requirements
1. Voice + typed chat with a cloud brain; graceful degraded mode offline.
2. Tasks/reminders/alarms with spoken alerts; events with calendar dates.
3. Approved-folder files: find/read/list/preview/summarize/quiz, filename index.
4. Media: YouTube play, Google search, enquiry photos with captions.
5. System: vitals HUD, apps/windows/processes/drives, wifi scan, lock PC.
6. Free public data: weather, currency, crypto, holidays, country facts.
7. Proactive: boot briefing, world headlines, danger alerts (cooldowns).
8. 3D visuals for every reply + CC0 `.glb` library with free orbit controls.
9. Memory: opt-in facts, full inspect/export/delete, guided erase flows.
10. Lock screen (hash-only PIN), emergency stop, audit trail, permissions view.

## Non-functional requirements
- Idle-light: no local inference, 5s ambient polls, paused hidden-tab render.
- Replies in ~1–2s for chat; answers in short human paragraphs.
- 127.0.0.1 only, token-gated; secrets never in code/logs/repo.
- Full unittest suite green before every push (`python -m unittest discover -s tests`).

## Acceptance criteria (per feature)
Implemented + unit-tested + verified live (curl/log evidence) + documented
in `help_catalog.py`. No mock presented as live, ever.

## Out of scope (refused by design)
Email sending, password/cookie access, silent installs/deletes, paywall or
CAPTCHA bypass, self-retraining, background recording, remote backdoors,
privilege escalation, model-generated shell execution.
