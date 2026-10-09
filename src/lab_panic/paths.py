"""Locations for bundled resources and persistent player data."""

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
RESOURCE_ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parents[2]
ASSET_ROOT = RESOURCE_ROOT / "assets"


def high_score_path() -> Path:
    if not FROZEN:
        return RESOURCE_ROOT / ".lab_panic_high_score.json"
    folder = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Lab Panic"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / ".lab_panic_high_score.json"
