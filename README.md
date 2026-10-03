# Lab Panic

2D cooperative hospital biochemistry laboratory game using Python and Pygame.

## Current status
Local scaffold: window, WASD movement, placeholder workstation layout.
LAN, sample interactions, processing, countdown and win/loss rules are not implemented.
Target: receive -> centrifuge -> add reagent -> analyze -> submit report.
Report submission succeeds; unfinished samples fail when the round ends.
The experiment process is fictional and simplified.

## Windows setup
Team baseline: **Python 3.12**. Python 3.13 is also permitted; avoid 3.14 with
this pinned Pygame release. Install 3.12 if `py -3.12` is unavailable.

```powershell
git clone https://github.com/JinxuanDai/StormHack2026.git
cd StormHack2026
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m lab_panic.main
```

Activation is optional. This existing checkout already has a Python 3.12 .venv.
WASD moves; Escape or closing the window exits.

## Smoke check
```powershell
.\.venv\Scripts\python.exe -m lab_panic.main --smoke-test
```
Renders three frames headlessly then exits. This does not verify visible graphics or LAN.

## Team workflow
Read AGENTS.md before coding or prompting Codex.

| Owner | Directory | Responsibility |
| --- | --- | --- |
| A | src/lab_panic/networking/, main.py | LAN, players, integration |
| B | src/lab_panic/gameplay/ | Samples, stations, timers |
| C | src/lab_panic/ui/, assets/ | Rendering, HUD, sprites, sound |

```powershell
git switch main
git pull --ff-only
git switch -c feature/sample-flow
# Make and verify a small change.
git add .
git commit -m "Add sample processing states"
git push -u origin feature/sample-flow
```
Open a PR into main. A reviews and integrates every 2-3 hours.
Commit local work before switching branches or pulling. Coordinate dependency/main.py edits.
First milestone: two computers join, move and consistently pick up the same sample.
Host/Join commands will be documented once implemented.

## Unity archive
Tag `unity-prototype` preserves the final tracked Unity project.
Ignored `_unity_backup/` retains local Unity files and caches.
Inspect the archive in a separate checkout:

```powershell
git clone --branch unity-prototype https://github.com/JinxuanDai/StormHack2026.git ../LabPanic-UnityArchive
```
