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

Both players now use separate 20 × 32, four-direction doctor sprite sheets.
The renderer infers facing and walk animation from successive immutable display
positions, so gameplay and network payloads do not need animation fields.
Sprites render at 40 × 64 with nearest-neighbor scaling and keep the existing
collision coordinates unchanged. Missing character files fall back to the
Phase 1 circle art. Source, license and modifications are recorded beside the
character assets and in `assets/README.md`.

Station label plates, borders, HUD, menus and results use Pygame primitives plus
the bundled Press Start 2P font. Its SIL OFL license and upstream changelog live
in `assets/fonts/`. Four mock cards and all seven areas fit the fixed 960 × 640
scene. Sample carrying and machine states are static examples, with no movement
or rules.

The team still needs to document original laboratory asset sources/licenses;
no metadata has been invented. There are no new Python dependencies, audio
assets or playback.
