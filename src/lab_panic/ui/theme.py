"""Shared presentation constants; coordinates are in fixed-window pixels."""

import pygame

WIDTH, HEIGHT = 960, 640
FPS = 60
BACKGROUND = (230, 233, 236)
PANEL = (248, 249, 250)
INK = (30, 60, 68)
MUTED = (90, 114, 120)
TEAL = (33, 123, 126)
TEAL_LIGHT = (211, 234, 231)
BORDER = (164, 175, 188)
FLOOR = (219, 224, 231)
GRID = (197, 205, 216)
SHADOW = (181, 191, 205)
GREEN = (45, 145, 94)
RED = (182, 70, 70)
PLAYER_COLORS = ((230, 137, 99), (103, 133, 207))
FONT_SMALL, FONT_BODY, FONT_HEADING, FONT_TITLE = 20, 24, 28, 68
FONT_TIMER = 60
HUD_HEIGHT = 120
ROOM = (16, 132, 928, 476)
STATION_HEIGHT = 140
STATION_SPRITE_SIZE = (112, 84)
SAMPLE_SIZE = (12, 34)
FLOOR_TILE_SIZE = (48, 48)


class Fonts:
    """Create once after pygame.font.init(); no external font dependency."""

    def __init__(self) -> None:
        self.small = pygame.font.Font(None, FONT_SMALL)
        self.body = pygame.font.Font(None, FONT_BODY)
        self.heading = pygame.font.Font(None, FONT_HEADING)
        self.title = pygame.font.Font(None, FONT_TITLE)
        self.timer = pygame.font.Font(None, FONT_TIMER)


def text(surface, font, value, position, color=INK, *, center=False):
    image = font.render(value, True, color)
    rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
    surface.blit(image, rect)
    return rect
