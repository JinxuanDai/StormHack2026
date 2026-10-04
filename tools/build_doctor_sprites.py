"""Convert the two approved doctor design sheets into game sprite sheets.

Run from the repository root with the project's installed Python environment:

    .venv/bin/python tools/build_doctor_sprites.py

Each design contains a 3 x 4 grid: three walk frames for the front, left,
right and back directions. The converter isolates every transparent frame,
normalizes all frames with one scale per character, and writes 40 x 64 cells.
"""

from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
CHARACTER_ROOT = ROOT / "assets" / "sprites" / "characters"
DESIGN_ROOT = CHARACTER_ROOT / "design"
FRAME_COLUMNS = 3
FRAME_ROWS = 4
CELL_SIZE = (40, 64)
SHEET_SIZE = (CELL_SIZE[0] * FRAME_COLUMNS, CELL_SIZE[1] * FRAME_ROWS)
ALPHA_THRESHOLD = 48


def source_cell(sheet: pygame.Surface, column: int, row: int) -> pygame.Rect:
    """Split uneven generated-image dimensions without losing edge pixels."""
    left = round(column * sheet.get_width() / FRAME_COLUMNS)
    right = round((column + 1) * sheet.get_width() / FRAME_COLUMNS)
    top = round(row * sheet.get_height() / FRAME_ROWS)
    bottom = round((row + 1) * sheet.get_height() / FRAME_ROWS)
    return pygame.Rect(left, top, right - left, bottom - top)


def opaque_bounds(surface: pygame.Surface) -> pygame.Rect:
    """Return bounds of visible design pixels, ignoring faint transparent noise."""
    left = surface.get_width()
    top = surface.get_height()
    right = -1
    bottom = -1
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            if surface.get_at((x, y)).a >= ALPHA_THRESHOLD:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < left or bottom < top:
        raise ValueError("A doctor design frame is empty")
    return pygame.Rect(left, top, right - left + 1, bottom - top + 1)


def harden_alpha(surface: pygame.Surface) -> None:
    """Keep the generated pixel edges crisp after reducing to game size."""
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            color = surface.get_at((x, y))
            if color.a < 96:
                surface.set_at((x, y), (0, 0, 0, 0))
            else:
                color.a = 255
                surface.set_at((x, y), color)


def convert_design(path: Path) -> pygame.Surface:
    design = pygame.image.load(str(path))
    frames: list[tuple[pygame.Surface, pygame.Rect]] = []
    for row in range(FRAME_ROWS):
        for column in range(FRAME_COLUMNS):
            cell = design.subsurface(source_cell(design, column, row)).copy()
            bounds = opaque_bounds(cell)
            frames.append((cell, bounds))

    max_width = max(bounds.width for _, bounds in frames)
    max_height = max(bounds.height for _, bounds in frames)
    scale = min((CELL_SIZE[0] - 2) / max_width, (CELL_SIZE[1] - 1) / max_height)
    output = pygame.Surface(SHEET_SIZE, pygame.SRCALPHA)

    for index, (cell, bounds) in enumerate(frames):
        frame = cell.subsurface(bounds).copy()
        scaled_size = (
            max(1, round(bounds.width * scale)),
            max(1, round(bounds.height * scale)),
        )
        frame = pygame.transform.scale(frame, scaled_size)
        harden_alpha(frame)
        destination = frame.get_rect(
            midbottom=(
                (index % FRAME_COLUMNS) * CELL_SIZE[0] + CELL_SIZE[0] // 2,
                (index // FRAME_COLUMNS + 1) * CELL_SIZE[1],
            )
        )
        output.blit(frame, destination)
    return output


def main() -> None:
    pygame.init()
    CHARACTER_ROOT.mkdir(parents=True, exist_ok=True)
    pygame.image.save(
        convert_design(DESIGN_ROOT / "doctor_female_design.png"),
        CHARACTER_ROOT / "doctor_female.png",
    )
    pygame.image.save(
        convert_design(DESIGN_ROOT / "doctor_male_design.png"),
        CHARACTER_ROOT / "doctor_male.png",
    )
    pygame.quit()


if __name__ == "__main__":
    main()
