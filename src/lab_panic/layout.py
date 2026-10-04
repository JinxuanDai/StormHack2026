"""Shared room geometry and world-to-canvas mapping; no UI dependencies."""

import math


WORLD_SIZE = (1280, 720)
WORLD_HUD_HEIGHT = 128
ROOM = (16, 132, 928, 476)
ROOM_INSET = 8
ROOM_INTERIOR = (ROOM[0] + ROOM_INSET, ROOM[1] + ROOM_INSET,
                 ROOM[2] - 2 * ROOM_INSET, ROOM[3] - 2 * ROOM_INSET)
FLOOR_TOP = ROOM[1] + 108

# Round toward the floor so an integer collision rectangle cannot enter the
# wall. This is the inverse of display_position's vertical mapping.
WORLD_FLOOR_TOP = math.ceil(
    WORLD_HUD_HEIGHT
    + (FLOOR_TOP - ROOM_INTERIOR[1]) * (WORLD_SIZE[1] - WORLD_HUD_HEIGHT)
    / ROOM_INTERIOR[3]
)


def display_position(x: float, y: float) -> tuple[int, int]:
    """Map authoritative world coordinates into the logical room interior."""
    left, top, width, height = ROOM_INTERIOR
    return (round(left + x * width / WORLD_SIZE[0]),
            round(top + (y - WORLD_HUD_HEIGHT) * height
                  / (WORLD_SIZE[1] - WORLD_HUD_HEIGHT)))
