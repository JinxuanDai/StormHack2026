# Part C Phase 1 preview

Run from the repository's installed Python environment:

```sh
python -m lab_panic.ui.demo
python -m lab_panic.ui.demo --smoke-test
python -m lab_panic.main --smoke-test
```

The window is fixed at 1120 × 800. Controls:

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

- `theme.py`: colors, font sizes, fixed display dimensions and text helper.
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

No real sprite crops are registered yet. Room, station icons, players and sample
vials are geometric placeholders. Original laboratory PNGs remain untouched.
Add verified `SpriteRegion` entries centrally in `assets.py`; `AssetStore.sprite`
loads/crops/scales in memory and caches results. Missing files, unregistered
names and invalid crop bounds fall back to placeholders. Treat cached surfaces
as read-only. Packaging may supply an explicit asset root to `AssetStore`.
The team still needs to document original asset sources/licenses; no metadata
has been invented. There are no new dependencies, audio assets or playback.
