# 47 — voice-first personal AI companion

Talk or type. 47 handles tasks, files, study, media, system insight, and
proactive briefings on your Windows laptop — through an exact React
frontend, with a single-file fallback. One active cloud brain (Groq live,
Grok one-key swap); everything else runs locally.

## 60-second start
```
pip install -r requirements.txt
python -m unittest discover -s tests   # must be fully green
python main.py                          # prints token URL, opens browser
```
No key yet? 47 runs degraded: chat says so, files/tasks/system/3D all work.
Add a brain key when ready:
```
$env:GROQ_API_KEY="gsk-..."     # free tier, works today
# or: $env:XAI_API_KEY="xai-..."  # Grok, preferred when present
```
Keys stay in env / OS keyring / `.47_env` (gitignored) — never in code.

## What it does
See the `?` palette in the app, say `help`, or read
[`docs/BROWSE.md`](docs/BROWSE.md) (capabilities + trigger words).

## Docs
`docs/BROWSE.md` (start here) · `ARCHITECTURE.md` · `PRD.md` · `MVP.md` ·
`WORKFLOW.md` · `HLD.md` · `LLD.md` · `AGENTS.md` (repo root, working rules).

## Safety in one paragraph
Localhost + token gate; approved folders only; destructive, cloud-send,
and erase actions need explicit `confirm`; PIN lock; emergency stop;
append-only audit log. Details in `docs/HLD.md` and the Permission Center
in the app.
