# Lab Panic

Lab Panic is a two-player LAN hospital hematology game built with Python and
Pygame. Players cooperate to collect patient blood samples, run the requested
tests, package the correct reports, and submit as many complete patient orders
as possible during a three-minute shift.

> The laboratory workflow is fictional and simplified for gameplay. It is not
> clinical guidance.

## Current demo

- Two-player host/client play over the same Wi-Fi or LAN
- Arrow keys to move and Space to interact on both computers
- Two concurrent patients with independent sample and package tables
- Each patient has a 45-second deadline and one to three randomized tests
- CBC: 2 seconds, white report
- Blood smear + microscope: 3 seconds, purple report
- Coagulation: 4 seconds, yellow report
- Visible workstation progress bars
- Each package table accepts only its matching patient's requested reports
- Trash discards unwanted samples, reports, or packages
- Three-minute shift with cumulative score and a host-local high score
- Laboratory sprite sheets from `assets/sprites/laboratory/`

## Requirements

- Python 3.12 or 3.13 (Python 3.14 is not supported yet)
- Both computers connected to the same local network
- TCP port `50505` allowed through the firewall

## Fast start — Windows

1. Install [Python 3.12](https://www.python.org/downloads/) and enable
   **Add Python to PATH** during installation.
2. Clone or download this repository.
3. Double-click `Start Lab Panic.bat`.

The first launch creates `.venv` and installs Pygame automatically. Later
launches reuse the same environment.

## Fast start — macOS

1. Install Python 3.12 or 3.13.
2. Clone or download this repository.
3. Right-click `Start Lab Panic.command`, choose **Open**, then confirm. Later
   launches can be opened normally by double-clicking it.

If macOS says the file is not executable, run once from Terminal:

```bash
chmod +x "Start Lab Panic.command"
./Start\ Lab\ Panic.command
```

## Play over LAN

1. On computer 1, start the game and select **HOST GAME**.
2. The host screen displays its local IP address, for example `192.168.1.23`.
3. On computer 2, start the game, enter that IP, then select **JOIN GAME**.
4. Allow Python network access if Windows or macOS asks.
5. Both players use the arrow keys to move and Space to interact. Escape quits.

The timer begins when player 2 connects. The host is authoritative for player
positions, samples, workstation timers, reports, packages, and scoring.

Two patient slots stay active throughout the shift. They begin as Patient #1
and #2. Completing or timing out one slot replaces only that patient with the
next ID; the other patient's timer and work remain unchanged. Samples, reports
and packages keep an immutable patient ID from pickup through submission.

Each patient has 45 seconds. Correct submission awards 100 points within 10
seconds, 80 within 20, 60 within 30, 40 within 40, and 20 before the deadline.
A timeout removes that order and deducts 40 points. The final score is the
three-minute total. The host saves its best score in the ignored local file
`.lab_panic_high_score.json`; clients see the host's score, but separate host
computers do not share a leaderboard.

## Terminal setup

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m lab_panic.main
```

### macOS/Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m lab_panic.main
```

Direct command-line hosting and joining are also supported:

```bash
python -m lab_panic.main
python -m lab_panic.main --host
python -m lab_panic.main --join 192.168.1.23
```

Running without options opens the original `HOST` / `JOIN` / `QUIT` menu.

## Verification

```bash
python -m lab_panic.main --smoke-test
```

The main entry point uses the shared UI renderer with live host snapshots,
including processing progress, report collection, packaging and results.
The standalone `python -m lab_panic.ui.demo` remains a static UI preview.

The smoke test loads the repository assets and renders the menu, waiting screen,
live machine and carried-item states, and both results headlessly, then exits.
LAN transport has been tested locally on loopback; the team should
also test between two physical computers before release.

## Team workflow

Read `AGENTS.md` before coding or prompting Codex. Work on a feature branch,
commit and push it, then open a pull request into `main`. Do not force-push
`main`, commit `.venv`, or overwrite another teammate's changes.

| Owner | Directory | Responsibility |
| --- | --- | --- |
| A | `src/lab_panic/networking/`, `main.py` | LAN, players, integration |
| B | `src/lab_panic/gameplay/` | Samples, stations, timers |
| C | `src/lab_panic/ui/`, `assets/` | Rendering, HUD, sprites, sound |

## Assets and Unity archive

Laboratory sprite sheets are stored in `assets/sprites/laboratory/`. Record the
source, author, license, and modifications in `assets/README.md` before public
distribution.

The `unity-prototype` tag preserves the final tracked Unity project. Ignored
`_unity_backup/` retains local Unity files and caches.
