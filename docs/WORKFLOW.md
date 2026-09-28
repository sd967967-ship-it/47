# 47 — Runtime workflows

## 1. Voice/text command
Mic/typed → `handle_command(text, context_id)` → e-stop gate → pending
gate (`confirm` runs staged; anything else cancels) → passive task scan →
3D push → planner split (sequence words) → branch match (files/media/docs/
wifi/tasks/…) → else `ask_brain` → styled reply → dashboard push + queued
TTS. Voice loop needs `hi 47`; typed input is always addressed.

## 2. Approval flow
Stage (`shell.stage_for_confirmation`, per-context, 60s TTL) → dashboard
approval card + spoken ask → `confirm` executes (shell/doc/erase/memory) →
audit entry. Deny/anything-else cancels. E-stop blocks all execution.

## 3. Planner flow
`planner.needs_plan` (sequence markers + 2 verbs, no LLM) → split (max 4)
→ each step re-enters router → pause if a step stages a confirm.

## 4. Emergency stop flow
`Kill Agent 47` (voice/text/button/shortcut/API) → `estop.stop`: clear TTS
queue, cancel focus, flag set, audit entry, STOPPED banner → resume needs
`resume 47` (+ unlock when a lock is set).

## 5. Erase flow
`forget X` → candidate shown → confirm deletes one. `erase memory` →
staged `ERASE:ALL` → confirm (+ unlock gate) → wipes facts + history
(tasks/reminders kept) → audit metadata only.

## 6. Lock/unlock flow
No `.47_lock` → setup PIN screen → PBKDF2 hash stored. Locked → full-app
PIN gate (socket `unlock_attempt`, never logged). 5 fails → 5-min lockout.
Unlock = 15-min session. Guards erase-all, exports, resume.

## 7. Proactive loop (30 min, daytime speech only)
New headlines → briefing push + optional speak. Ambient (5s): vitals push +
CPU/battery/disk/RAM alerts (30-min cooldown). Reminders (15s): due spoken.
Startup: one full briefing after 25s.
