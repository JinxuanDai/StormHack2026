"""Shared presentation constants; coordinates are in fixed-window pixels."""

import pygame

WIDTH, HEIGHT = 1120, 800
FPS = 60
BACKGROUND = (231, 239, 239)
PANEL = (250, 252, 250)
INK = (30, 60, 68)
MUTED = (90, 114, 120)
TEAL = (33, 123, 126)
TEAL_LIGHT = (211, 234, 231)
BORDER = (187, 207, 208)
FLOOR = (223, 233, 232)
GRID = (212, 225, 225)
SHADOW = (197, 214, 213)
GREEN = (45, 145, 94)
RED = (182, 70, 70)
PLAYER_COLORS = ((230, 137, 99), (103, 133, 207))
FONT_SMALL, FONT_BODY, FONT_HEADING, FONT_TITLE = 20, 24, 30, 76
ROOM = (24, 164, 1072, 584)


class Fonts:
    """Create once after pygame.font.init(); no external font dependency."""

    def __init__(self) -> None:
        self.small = pygame.font.Font(None, FONT_SMALL)
        self.body = pygame.font.Font(None, FONT_BODY)
        self.heading = pygame.font.Font(None, FONT_HEADING)
        self.title = pygame.font.Font(None, FONT_TITLE)


def text(surface, font, value, position, color=INK, *, center=False):
    image = font.render(value, True, color)
    rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
    surface.blit(image, rect)
    return rect
