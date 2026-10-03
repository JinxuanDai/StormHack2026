# Lab Panic collaboration

Python 3.12, Pygame 2.6.1, 2D hospital laboratory, two-player LAN target.
Current scaffold is local only. Do not claim networking works without two-computer verification.

## Ownership
- A: networking/, player interactions, main.py, integration, packaging.
- B: gameplay/, sample states, workstations, processing timers.
- C: ui/, assets/, rendering, HUD, audio.
- Coordinate edits to main.py, dependencies and shared interfaces.
- Do not delegate to agents unless a human explicitly requests it.

## Shared design
Received -> Centrifuged -> ReagentAdded -> Analyzed -> ReportSubmitted.
Only report submission succeeds. At the round deadline unfinished samples fail.
Use simplified fictional processes, not clinical advice.
Host owns sample IDs, item ownership, stations, timers and results.
Gameplay must be independent of rendering and transport. UI reads authoritative state.
Network I/O must not block Pygame's event loop.

## Git and validation
Use small feature branches and PRs into main; A integrates every 2-3 hours.
Commit local work before updating. Never overwrite teammate changes or force-push main.
Do not commit .venv, caches, secrets, or _unity_backup. Preserve unity-prototype tag.
After rendering changes run `python -m lab_panic.main --smoke-test`.
Networking changes require testing on two computers.
