# Part C Phase 2 preview

Run from the repository's installed Python environment:

```sh
python -m lab_panic.ui.demo
python -m lab_panic.ui.demo --smoke-test
python -m lab_panic.main --smoke-test
```

The window is fixed at 960 × 640. Controls:

- `1`: main menu
- `2`: mock gameplay
- `3`: success
- `4`: failure
- `Escape` or window close: quit
- Menu: `Up` / `Down` selects; `Enter` (including keypad Enter) activates.
  Left-click also activates a button. HOST and JOIN both open the same mock
  scene; QUIT exits. There is no network connection or player movement.

The timer stays at 3:00. Players, carried sample, processing progress and the
completion checkmark are fixed examples. The footer is a demo inspection aid.
The seven station positions follow the agreed layout; their names do not
introduce or change any processing rules.

## Modules and integration

- `theme.py`: colors, licensed pixel font, clipped panels, fixed dimensions and text helper.
- `assets.py`: asset root, centralized `SPRITES` crop registry and `AssetStore`.
- `views.py`: frozen presentation snapshots; these are not gameplay models.
- `renderer.py`: `Renderer.draw_gameplay(surface, snapshot)`, menu and results.
- `hud.py`: timer, patient cards, progress bar, checkmark and messages.
- `demo.py`: mock snapshot, inspection controls and standalone event loop.

A/B should adapt authoritative state into the immutable view values, map world
positions to display coordinates, and supply remaining time, progress and
completion explicitly. C's renderer never advances timers, changes ownership,
checks test requirements, or decides round outcomes. A selects the menu/result
screen and connects real host/join actions in the application's own event loop.
Initialize Pygame before creating a renderer and reuse it between frames.

## Runtime sprite crops

All crop rectangles are defined in `assets.py`, in source pixels `(x, y, width,
height)`. Six original sheets are used: `1.png`, `3.png`, `4.png`, `5.png`,
`6.png`, and `7.png`. No original laboratory images are modified or copied.

| Named crop | Sheet | Source rectangle | Display role |
| --- | --- | --- | --- |
| `sample_bench` | `3.png` | `(144, 160, 96, 80)` | Reflective drawer bench used beneath extraction items |
| `sample_rack` | `3.png` | `(576, 672, 48, 50)` | Wooden rack with red sample tubes |
| `blood_smear_slide` | `6.png` | `(435, 110, 43, 21)` | Tightly cropped blood-bearing slide layered onto the smear bench |
| `cbc_machine` | `7.png` | `(485, 674, 86, 93)` | Mobile analyzer cart shown in the layout |
| `lab_printer` | `4.png` | `(297, 399, 71, 81)` | Rear-wall printer beside the CBC analyzer |
| `microscope` | `4.png` | `(576, 577, 96, 95)` | Microscope on a bench |
| `coagulation_machine` | `4.png` | `(401, 578, 63, 94)` | Open-lid round laboratory machine |
| `package_table` | `3.png` | `(672, 0, 96, 48)` | Wide workbench from the supplied layout |
| `trash_bin` | `5.png` | `(677, 328, 39, 55)` | Yellow biohazard bin |
| `submit_terminal` | `4.png` | `(180, 389, 108, 115)` | Computer workstation with chair |
| `sample_tube` | `6.png` | `(542, 3, 21, 93)` | Red-filled tube, carried or on bench |
| `floor_tile` | `1.png` | `(0, 0, 48, 48)` | Repeated neutral laboratory tile |
| `trash_blue` … `trash_biohazard` | `5.png` | six bottom-row 48 × 80 crops | Recycling/biohazard cluster |
| `package_box` | `6.png` | `(336, 724, 48, 44)` | Small box on each package table |

Crop boundaries were visually inspected. The CBC and Coagulation assignments
are fictional visual stand-ins: the round machine resembles a centrifuge, not
an identified coagulation analyzer. No medical equipment identification is
claimed. Bench-mounted props remain part of their single source crops.

The loader uses `convert_alpha()` when a display is available, preserves aspect
ratio, scales with nearest-neighbor sampling, and caches sheets and output
surfaces. Missing/corrupt sheets, unknown names, invalid crop bounds and empty
crops fall back to Phase 1 shapes. Samples and floor have their own fallbacks.
Treat cached surfaces as read-only. Packaging may supply an explicit asset root
to `AssetStore`. Keep station type mapping in `STATION_SPRITES`; rendering does
not require changes to A/B's state models.

Both players remain Phase 1 circle placeholders. Station label plates, borders,
shadows, HUD, menus and results use Pygame primitives plus the bundled Press
Start 2P font. Its SIL OFL license and upstream changelog live in
`assets/fonts/`. Four mock cards and all seven areas fit the fixed 960 × 640
scene. Sample carrying and machine states are static examples, with no movement
or rules.

The team still needs to document original laboratory asset sources/licenses;
no metadata has been invented. There are no new Python dependencies.
The visual demo has no audio playback; standalone audio assets and previews
are described below.

## Audio Phase 1: standalone presentation architecture

The audio architecture is now integrated into `main.py` on both host and client.
Confirmed snapshots trigger pickup, machine, processing and package cues.
Dual-patient reports are tracked by patient ID; confirmed per-player discard
counters trigger trash cues. Result presentation triggers one result cue per
session. Disconnect and shutdown stop processing loops. Background music runs
independently on the dedicated music channel. No timing or result rules change.
Phase 1 introduced the standalone architecture;
Phase 2 adds ten temporary generated WAVs and a listening preview, described below.
Neither phase adds dependencies.

The flow is one-way:

```text
confirmed authoritative snapshot -> AudioObserver -> AudioEvent values -> AudioManager
existing presentation result ----------------------> present_result()
```

`audio_observer.py` has no Pygame, gameplay or networking imports. It copies
primitive fields into frozen values instead of retaining snapshot references.
`audio.py` initializes the mixer if necessary, caches existing files and consumes
events on the application's main thread. Missing/corrupt files, unavailable
hardware, mixer failures and channel exhaustion silently skip playback. Normal
use does not print. Playback never calls back into gameplay.

### Public API

`AudioManager(root=AUDIO_ROOT, *, enabled=True, files=None)` preloads optional
sounds. The default root is the checkout's `assets/audio/`; `files` can override
named cue filenames, for example `{"pickup": "pickup.ogg"}`. Default filenames
are `<cue>.wav` for the ten cues below. Phase 2 supplies those placeholder files.
`CUE_VOLUMES` applies centralized per-cue gain once when each sound is loaded.

- `available`: whether the manager can currently use the mixer.
- `loaded_cues`: tuple of successfully loaded cue names.
- `preload()`: returns loaded names; caches existing sounds and can explicitly
  retry missing files after assets are added.
- `play(cue)`: plays a one-shot, returning whether playback started. Unknown cues
  and `processing_loop` return false; loops use `start_processing()`.
- `start_processing(station_id)`: starts at most one loop per station; returns
  true for an existing loop or successful start, false when unavailable.
- `stop_processing(station_id)` / `stop_all_loops()`: stop owned loop channels.
- `handle(events)`: consumes observer events in order.
- `close()`: stops loops, releases cached sounds and disables the manager. It
  does not quit the shared mixer; final application shutdown remains with A.

`AudioObserver()` exposes:

- `observe(state, *, session_id=None) -> tuple[AudioEvent, ...]`: consumes the
  current authoritative snapshot schema. Use a stable session ID on every call
  if supplying one; a changed ID establishes a new silent baseline.
- `present_result("success" | "failure") -> tuple[AudioEvent, ...]`: consumes
  the result already selected by presentation. It never reads scores or
  calculates victory. The first valid call stops loops and emits its result;
  repeated/contradictory calls are silent. Unknown values are ignored.
- `disconnect() -> tuple[AudioEvent, ...]`: stops loops and forgets the snapshot
  baseline, preserving the result latch across reconnection.
- `reset() -> tuple[AudioEvent, ...]`: stops loops and clears the baseline,
  session ID and result latch for a new game.

Forward the returned events from **all** these methods to `AudioManager.handle()`.
`AudioEvent` is frozen, with `action` (`play`, `start_loop`, `stop_loop`, or
`stop_all_loops`), optional `cue`, and optional `station_id`. These are audio
instructions, not gameplay commands.

### Cues and confirmed transitions

| Cue | Trigger |
| --- | --- |
| `pickup` | Empty hand becomes a held item, except a matched machine collection. |
| `machine_insert` | Station changes from `idle` to `processing`. |
| `processing_start` | The same confirmed `idle` to `processing` transition. |
| `processing_loop` | A `start_loop` event on that transition, keyed by station. |
| `processing_complete` | `processing` to `output` for the same station patient; stop its loop first. |
| `machine_remove` | `output` to `idle` plus an empty-handed player acquiring a report matching the station's test and prior patient. Replaces generic pickup for that acquisition. |
| `package_insert` | `package_reports` gains tests for the same patient. Multiple additions in one snapshot produce one cue. |
| `trash` | Host-confirmed `discard_counts` increases; never inferred from item disappearance. |
| `round_success` | Explicit `present_result("success")`, once per session. |
| `round_failure` | Explicit `present_result("failure")`, once per session. |

Both insertion and processing-start one-shots are exposed because insertion
currently starts processing immediately. Their final sound mix can be chosen
when assets are added. No generic `drop` cue exists: gameplay has no general
drop action. Item disappearance alone is silent; it cannot distinguish trash,
insertion, submission or a reset. Messages, button presses, scores and remaining
time are not used as an audio contract. Audio does not classify invalid items.

### Baselines, duplicate suppression and loops

The first snapshot is silent, even if it already contains processing machines,
held items or reports. Identical snapshots, changed elapsed times, movement and
message updates do not retrigger cues. A patient change establishes a new
baseline and stops all requested loops without generating reset-related cues.
It does not rearm a round result. A changed session ID, explicit `reset()`, or
observed transition back out of a finished/started round establishes a new
baseline and rearms the result latch.

Waiting, disconnection and finished snapshots produce no new interaction cues.
Loops stop on any observed exit from processing, station removal, patient/session
reset, disconnect, round end, explicit result presentation or manager close.
The observer tracks requested loops; the manager independently prevents duplicate
channels per station. It uses free channels without stealing active ones. Missing
sounds or busy channels do not create retries on every frame.

For a strict silent baseline, a machine already processing when first observed
or reconnected does not start a loop retroactively. Its later observed completion
can still produce a completion cue. Snapshots can skip intermediate states and
there are no unique item IDs or event sequence IDs. Consequently some interactions
can be missed, and exact causal attribution is not guaranteed. Reliable delivery
of every interaction, including trash, needs host-authored events from A/B later.

### Integration pattern used by A

In `main.py`, import the two classes:

```python
from .ui.audio import AudioManager
from .ui.audio_observer import AudioObserver
```

Create one manager and observer in each of `run_host()` and `run_client()` after
Pygame initialization, outside the frame loop:

```python
audio = AudioManager()
audio_observer = AudioObserver()
```

Host: immediately after `state = game.snapshot(network.connected)`, feed that
confirmed state. Client: feed only a real `network.state()` while the transport
is connected, never the synthetic connecting-screen state:

```python
audio.handle(audio_observer.observe(state))
```

For results, expose the existing presentation choice once rather than adding a
victory predicate to audio. In the application `Renderer.draw()` adapter, set
`result = None` at entry, and reuse its existing finished-branch decision:

```python
success = state["completed"] >= 3  # Existing presentation rule, kept here.
self.ui.draw_result(self.screen, success=success)
result = "success" if success else "failure"
```

Return `result` at the **end** of `draw()`, after all existing text/overlays, and
update its return annotation to `str | None`. The caller then uses:

```python
result = renderer.draw(state, local_player)  # Preserve the client's status argument.
if result is not None:
    audio.handle(audio_observer.present_result(result))
```

On the client, only feed result cues while connected. When transport disconnects,
call the following even if the last snapshot still has `connected=True`:

```python
audio.handle(audio_observer.disconnect())
```

The host's `connected=False` snapshot also stops loops automatically. In each
run function's `finally`, call `audio.close()` before the existing shutdown.
For a new session, create fresh objects or forward `audio_observer.reset()`.
Rendering itself remains free of playback calls. Later, a confirmed trash event
can call `audio.play("trash")`; client feedback must wait for host confirmation.

### Standalone verification

Run from the installed environment; `-B` avoids updating repository bytecode:

```sh
python -B -m lab_panic.ui.audio_check
python -B -m lab_panic.main --smoke-test
python -B -m unittest discover -s tests -v
```

`audio_check.py` uses synthetic snapshots, WAV inspection and a mocked mixer.
It checks copied state, unchanged input, transitions, duplicate suppression,
resets, external results, independent loops, missing assets, mixer failures,
gain configuration and preview key routing. It imports no `main.py` or
gameplay/networking code, creates no assets and needs no device.
These checks do not verify audible playback or two-computer networking.

## Audio Phase 2: temporary SFX and listening preview

Run the standalone window:

```sh
python -m lab_panic.ui.audio_demo
```

| Key | Cue | Default gain |
| --- | --- | --- |
| 1 | `pickup` | 0.55 |
| 2 | `machine_insert` | 0.55 |
| 3 | `machine_remove` | 0.55 |
| 4 | `processing_start` | 0.50 |
| 5 | `processing_loop` (toggle ON/OFF) | 0.18 |
| 6 | `processing_complete` | 0.62 |
| 7 | `package_insert` | 0.55 |
| 8 | `trash` | 0.50 |
| 9 | `round_success` | 0.65 |
| 0 | `round_failure` | 0.60 |
| Escape | Quit and stop audio | — |

The window shows each cue's loaded/missing status, mixer availability, gain,
last action and processing-loop ON/OFF state. Keyboard repeat is disabled so
holding 5 does not repeatedly toggle. Missing sounds or unavailable hardware
leave the window usable. No gameplay state or networking is used; the demo
directly auditions the manager, including the otherwise hook-only trash cue.

All WAVs are locally synthesized, mono 16-bit PCM at 44.1 kHz. The hum is quieter
both in the file and in its mixer gain. See `assets/audio/README.md` for provenance,
durations, replacement instructions and the standard-library regeneration command.
Replace files one-for-one and restart the demo to reload. These are development
placeholders for listening review, not final production sound design.

The standalone preview remains available for auditioning individual cues.
The main host/client loops now also play cues from confirmed gameplay state.
