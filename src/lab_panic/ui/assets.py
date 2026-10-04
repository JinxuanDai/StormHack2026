"""Named runtime crops from the untouched laboratory sheets.

Rectangles are (x, y, width, height) in source pixels. Machine names describe
fictional display roles, not verified clinical equipment. Packaging may supply
an explicit asset root instead of the default checkout path.
"""

from dataclasses import dataclass
from pathlib import Path

import pygame

from . import theme

LABORATORY_ROOT = Path(__file__).resolve().parents[3] / "assets" / "sprites" / "laboratory"
CHARACTER_ROOT = Path(__file__).resolve().parents[3] / "assets" / "sprites" / "characters"
CHARACTER_FILES = ("doctor_female.png", "doctor_male.png")
CHARACTER_CELL = (20, 32)
CHARACTER_ROWS = {"down": 0, "left": 1, "right": 2, "up": 3}


@dataclass(frozen=True)
class SpriteRegion:
    sheet: str
    rect: tuple[int, int, int, int]


# All source coordinates live here. No PNGs are modified or exported.
SPRITES: dict[str, SpriteRegion] = {
    "sample_bench": SpriteRegion("3.png", (144, 160, 96, 80)),
    "sample_rack": SpriteRegion("3.png", (576, 672, 48, 50)),
    "blood_smear_slide": SpriteRegion("6.png", (435, 110, 43, 21)),
    "cbc_machine": SpriteRegion("7.png", (485, 674, 86, 93)),
    "lab_printer": SpriteRegion("4.png", (297, 399, 71, 81)),
    "microscope": SpriteRegion("4.png", (576, 577, 96, 95)),
    "coagulation_machine": SpriteRegion("4.png", (401, 578, 63, 94)),
    "package_table": SpriteRegion("3.png", (672, 0, 96, 48)),
    "trash_bin": SpriteRegion("5.png", (677, 328, 39, 55)),
    "submit_terminal": SpriteRegion("4.png", (180, 389, 108, 115)),
    "sample_tube": SpriteRegion("6.png", (542, 3, 21, 93)),
    "floor_tile": SpriteRegion("1.png", (0, 0, 48, 48)),
    "trash_blue": SpriteRegion("5.png", (480, 688, 48, 80)),
    "trash_green": SpriteRegion("5.png", (528, 688, 48, 80)),
    "trash_red": SpriteRegion("5.png", (576, 688, 48, 80)),
    "trash_dark": SpriteRegion("5.png", (624, 688, 48, 80)),
    "trash_yellow": SpriteRegion("5.png", (672, 688, 48, 80)),
    "trash_biohazard": SpriteRegion("5.png", (720, 688, 48, 80)),
    "package_box": SpriteRegion("6.png", (336, 724, 48, 44)),
}

# Preserve the Phase 1 snapshot station types without involving gameplay models.
STATION_SPRITES = {
    "extraction": "sample_bench",
    "cbc": "cbc_machine",
    "microscope": "microscope",
    "coagulation": "coagulation_machine",
    "package": "package_table",
    "trash": "trash_bin",
    "submit": "submit_terminal",
}


class AssetStore:
    def __init__(
        self,
        root: Path = LABORATORY_ROOT,
        character_root: Path = CHARACTER_ROOT,
    ) -> None:
        self.root = Path(root)
        self.character_root = Path(character_root)
        self._sheets: dict[str, pygame.Surface | None] = {}
        self._sprites: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}
        self._character_sheets: dict[str, pygame.Surface | None] = {}
        self._character_frames: dict[
            tuple[int, str, int, tuple[int, int]], pygame.Surface
        ] = {}

    def character_frame(
        self,
        player_index: int,
        direction: str,
        frame: int,
        size: tuple[int, int] = (40, 64),
    ) -> pygame.Surface:
        """Return one four-direction doctor frame at a crisp integer scale."""
        direction = direction if direction in CHARACTER_ROWS else "down"
        frame = max(0, min(2, int(frame)))
        key = (player_index % len(CHARACTER_FILES), direction, frame, size)
        if key not in self._character_frames:
            filename = CHARACTER_FILES[key[0]]
            sheet = self._character_sheet(filename)
            if sheet is None:
                result = self._player_placeholder(size, player_index)
            else:
                source = pygame.Rect(
                    frame * CHARACTER_CELL[0],
                    CHARACTER_ROWS[direction] * CHARACTER_CELL[1],
                    *CHARACTER_CELL,
                )
                result = pygame.transform.scale(sheet.subsurface(source), size)
            self._character_frames[key] = result
        return self._character_frames[key]

    def sprite(self, name: str, size: tuple[int, int]) -> pygame.Surface:
        """Return an aspect-preserving crop centered in size, or a placeholder.

        Nearest-neighbor scaling preserves the pack's pixel style. Cached
        surfaces are shared: callers must treat them as read-only. Initialize
        Pygame first; a display enables convert_alpha() when loading sheets.
        """
        key = (name, size)
        if key not in self._sprites:
            image = self._crop(name)
            if image is None:
                result = self._placeholder(size, name)
            else:
                factor = min(size[0] / image.get_width(), size[1] / image.get_height())
                scaled = pygame.transform.scale(image, (
                    max(1, round(image.get_width() * factor)),
                    max(1, round(image.get_height() * factor)),
                ))
                result = pygame.Surface(size, pygame.SRCALPHA)
                result.blit(scaled, scaled.get_rect(center=result.get_rect().center))
            self._sprites[key] = result
        return self._sprites[key]

    def _crop(self, name: str) -> pygame.Surface | None:
        region = SPRITES.get(name)
        if region is None:
            return None
        if region.sheet not in self._sheets:
            try:
                sheet = pygame.image.load(str(self.root / region.sheet))
                if pygame.display.get_surface() is not None:
                    sheet = sheet.convert_alpha()
                self._sheets[region.sheet] = sheet
            except (OSError, pygame.error):
                self._sheets[region.sheet] = None
        sheet = self._sheets[region.sheet]
        if sheet is None:
            return None
        try:
            rect = pygame.Rect(region.rect)
            if rect.width <= 0 or rect.height <= 0 or not sheet.get_rect().contains(rect):
                return None
            image = sheet.subsurface(rect)
            return image if image.get_bounding_rect().width else None
        except (TypeError, ValueError, pygame.error):
            return None

    def _character_sheet(self, filename: str) -> pygame.Surface | None:
        if filename not in self._character_sheets:
            try:
                sheet = pygame.image.load(str(self.character_root / filename))
                if pygame.display.get_surface() is not None:
                    sheet = sheet.convert_alpha()
                expected = (64, 128)
                self._character_sheets[filename] = sheet if sheet.get_size() == expected else None
            except (OSError, pygame.error):
                self._character_sheets[filename] = None
        return self._character_sheets[filename]

    @staticmethod
    def _player_placeholder(size: tuple[int, int], player_index: int) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        color = theme.PLAYER_COLORS[player_index % len(theme.PLAYER_COLORS)]
        center = (size[0] // 2, size[1] // 2)
        radius = max(4, min(size) // 3)
        pygame.draw.circle(surface, theme.DARK_INK, center, radius + 2)
        pygame.draw.circle(surface, color, center, radius)
        return surface

    @staticmethod
    def _placeholder(size: tuple[int, int], name: str = "") -> pygame.Surface:
        # Keep the Phase 1 fallbacks recognizable, including sample and floor.
        if name == "floor_tile":
            surface = pygame.Surface(size, pygame.SRCALPHA)
            surface.fill(theme.FLOOR)
            pygame.draw.rect(surface, theme.GRID, surface.get_rect(), width=1)
            return surface
        if name == "sample_tube":
            surface = pygame.Surface((14, 30), pygame.SRCALPHA)
            pygame.draw.rect(surface, theme.INK, (1, 2, 12, 27), border_radius=4)
            pygame.draw.rect(surface, theme.PANEL, (3, 5, 8, 20), border_radius=3)
            pygame.draw.rect(surface, theme.RED, (4, 15, 6, 9), border_radius=2)
            pygame.draw.rect(surface, theme.TEAL, (0, 0, 14, 6), border_radius=2)
            return pygame.transform.scale(surface, size)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        box = surface.get_rect().inflate(-4, -4)
        pygame.draw.rect(surface, theme.TEAL_LIGHT, box, border_radius=8)
        pygame.draw.rect(surface, theme.TEAL, box, width=2, border_radius=8)
        display = pygame.Rect(box.x + 10, box.y + 9, max(4, box.width - 20), max(4, box.height // 3))
        pygame.draw.rect(surface, theme.TEAL, display, border_radius=3)
        pygame.draw.circle(surface, theme.TEAL, (box.right - 13, box.bottom - 12), 3)
        return surface
