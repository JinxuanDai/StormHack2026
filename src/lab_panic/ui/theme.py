"""Pixel-laboratory presentation constants for the fixed game window."""

from pathlib import Path

import pygame

WIDTH, HEIGHT = 960, 640
FPS = 60
BACKGROUND = (172, 211, 212)
WALL = (184, 216, 216)
PANEL = (49, 73, 86)
PANEL_LIGHT = (68, 97, 109)
INK = (247, 250, 247)
DARK_INK = (39, 54, 65)
MUTED = (197, 220, 220)
TEAL = (66, 153, 157)
TEAL_LIGHT = (130, 193, 194)
BORDER = (120, 174, 181)
FLOOR = (215, 223, 235)
GRID = (175, 188, 207)
SHADOW = (79, 105, 113)
GREEN = (78, 183, 122)
RED = (231, 102, 88)
YELLOW = (240, 194, 77)
PLAYER_COLORS = ((230, 137, 99), (103, 133, 207))
FONT_SMALL, FONT_BODY, FONT_HEADING, FONT_TITLE = 9, 10, 13, 30
FONT_TIMER = 24
HUD_HEIGHT = 120
ROOM = (16, 132, 928, 476)
FLOOR_TOP = ROOM[1] + 108
STATION_HEIGHT = 140
STATION_SPRITE_SIZE = (112, 84)
SAMPLE_SIZE = (12, 34)
FLOOR_TILE_SIZE = (96, 96)
FONT_PATH = Path(__file__).resolve().parents[3] / "assets" / "fonts" / "PressStart2P-Regular.ttf"


class Fonts:
    """Create the licensed pixel font once, with a safe Pygame fallback."""

    def __init__(self) -> None:
        font_path = str(FONT_PATH) if FONT_PATH.is_file() else None
        self.small = pygame.font.Font(font_path, FONT_SMALL)
        self.body = pygame.font.Font(font_path, FONT_BODY)
        self.heading = pygame.font.Font(font_path, FONT_HEADING)
        self.title = pygame.font.Font(font_path, FONT_TITLE)
        self.timer = pygame.font.Font(font_path, FONT_TIMER)


def text(surface, font, value, position, color=INK, *, center=False):
    image = font.render(value, False, color)
    rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
    surface.blit(image, rect)
    return rect


def cut_panel(surface, rect: pygame.Rect, fill=PANEL, border=BORDER, *, cut=7, shadow=False) -> None:
    """Draw a crisp clipped-corner panel matching the laboratory pixel art."""
    rect = pygame.Rect(rect)

    def points(target: pygame.Rect) -> list[tuple[int, int]]:
        return [
            (target.left + cut, target.top),
            (target.right - cut, target.top),
            (target.right, target.top + cut),
            (target.right, target.bottom - cut),
            (target.right - cut, target.bottom),
            (target.left + cut, target.bottom),
            (target.left, target.bottom - cut),
            (target.left, target.top + cut),
        ]

    if shadow:
        shadow_rect = rect.move(3, 4)
        pygame.draw.polygon(surface, (67, 101, 108), points(shadow_rect))
    pygame.draw.polygon(surface, fill, points(rect))
    pygame.draw.lines(surface, border, True, points(rect), 2)
