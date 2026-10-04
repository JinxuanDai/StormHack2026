"""Central sprite-sheet crops and cached loading with placeholder fallback.

Original sheets are read-only. Register verified pixel rectangles in SPRITES,
e.g. SpriteRegion("1.png", (x, y, width, height)). No crops are verified yet.
An explicit root can be supplied when A packages assets outside this checkout.
"""

from dataclasses import dataclass
from pathlib import Path

import pygame

from . import theme

LABORATORY_ROOT = Path(__file__).resolve().parents[3] / "assets" / "sprites" / "laboratory"


@dataclass(frozen=True)
class SpriteRegion:
    sheet: str
    rect: tuple[int, int, int, int]


SPRITES: dict[str, SpriteRegion] = {}


class AssetStore:
    def __init__(self, root: Path = LABORATORY_ROOT) -> None:
        self.root = Path(root)
        self._sheets: dict[str, pygame.Surface | None] = {}
        self._sprites: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}

    def sprite(self, name: str, size: tuple[int, int]) -> pygame.Surface:
        """Return a cached crop or a clean placeholder for missing/invalid art.

        Returned surfaces are shared and should be treated as read-only.
        Call after initializing Pygame; no display conversion is required.
        """
        key = (name, size)
        if key not in self._sprites:
            region = SPRITES.get(name)
            result = None
            if region is not None:
                if region.sheet not in self._sheets:
                    try:
                        self._sheets[region.sheet] = pygame.image.load(str(self.root / region.sheet))
                    except (OSError, pygame.error):
                        self._sheets[region.sheet] = None
                sheet = self._sheets[region.sheet]
                rect = pygame.Rect(region.rect)
                if sheet is not None and rect.width > 0 and rect.height > 0 and sheet.get_rect().contains(rect):
                    result = pygame.transform.scale(sheet.subsurface(rect), size)
            self._sprites[key] = result if result is not None else self._placeholder(size)
        return self._sprites[key]

    @staticmethod
    def _placeholder(size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        box = surface.get_rect().inflate(-4, -4)
        pygame.draw.rect(surface, theme.TEAL_LIGHT, box, border_radius=8)
        pygame.draw.rect(surface, theme.TEAL, box, width=2, border_radius=8)
        display = pygame.Rect(box.x + 10, box.y + 9, max(4, box.width - 20), max(4, box.height // 3))
        pygame.draw.rect(surface, theme.TEAL, display, border_radius=3)
        pygame.draw.circle(surface, theme.TEAL, (box.right - 13, box.bottom - 12), 3)
        return surface
