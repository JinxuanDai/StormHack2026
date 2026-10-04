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
BLUSH = (224, 145, 164)

# One shared, deliberately small palette keeps both doctors visually related
# and prevents thousands of near-identical resampling colors from appearing at
# the eyes, hairline, coat edges and shoes. Transparent pixels are preserved
# separately and are not part of this palette.
CLEAN_PALETTE = (
    (38, 27, 24),    # outline, eyes and eyebrows
    (58, 35, 29),    # deepest hair / shoe shade
    (80, 50, 37),    # dark brown
    (108, 68, 49),   # middle brown
    (142, 94, 67),   # brown highlight
    (224, 174, 150), # skin shadow
    (246, 211, 193), # skin
    BLUSH,            # restrained cheek color
    (252, 252, 249), # lab coat
    (207, 211, 211), # lab coat shadow
    (64, 79, 145),   # dark blue shirt
    (79, 98, 188),   # blue shirt
    (39, 40, 47),    # dark trousers
    (60, 64, 74),    # trouser highlight
    (102, 66, 49),   # shoes
    (167, 111, 80),  # shoe highlight
)


def source_rows(sheet: pygame.Surface) -> list[tuple[int, int]]:
    """Find character bands separated by transparent gutters, not equal rows."""
    bands = []
    start = None
    for y in range(sheet.get_height()):
        occupied = sum(sheet.get_at((x, y)).a >= ALPHA_THRESHOLD
                       for x in range(sheet.get_width())) > max(20, sheet.get_width() // 50)
        if occupied and start is None:
            start = y
        elif not occupied and start is not None:
            bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, sheet.get_height()))
    if len(bands) != FRAME_ROWS:
        raise ValueError(f"Expected four isolated character rows, found {len(bands)}")
    return bands


def source_cell(sheet: pygame.Surface, column: int, row: int,
                rows: list[tuple[int, int]]) -> pygame.Rect:
    """Use the measured vertical band and evenly spaced source columns."""
    left = round(column * sheet.get_width() / FRAME_COLUMNS)
    right = round((column + 1) * sheet.get_width() / FRAME_COLUMNS)
    top, bottom = rows[row]
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


def clean_palette(surface: pygame.Surface) -> None:
    """Map every visible pixel to one crisp, shared character color."""
    cache: dict[tuple[int, int, int], tuple[int, int, int, int]] = {}
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            color = surface.get_at((x, y))
            if not color.a:
                continue
            source = (color.r, color.g, color.b)
            replacement = cache.get(source)
            if replacement is None:
                # Reserve pink for pixels that are already visibly pink. This
                # prevents warm shoe and skin highlights from becoming blush.
                is_pink = (
                    source[0] > 150
                    and source[0] - source[1] > 25
                    and source[2] >= source[1] * 0.9
                )
                if is_pink:
                    nearest = BLUSH
                else:
                    # Green carries the most perceived brightness, blue the least.
                    nearest = min(
                        (target for target in CLEAN_PALETTE if target != BLUSH),
                        key=lambda target: (
                            3 * (source[0] - target[0]) ** 2
                            + 4 * (source[1] - target[1]) ** 2
                            + 2 * (source[2] - target[2]) ** 2
                        ),
                    )
                replacement = (*nearest, 255)
                cache[source] = replacement
            surface.set_at((x, y), replacement)


def convert_design(path: Path) -> pygame.Surface:
    design = pygame.image.load(str(path))
    rows = source_rows(design)
    frames: list[tuple[pygame.Surface, pygame.Rect]] = []
    for row in range(FRAME_ROWS):
        for column in range(FRAME_COLUMNS):
            cell = design.subsurface(source_cell(design, column, row, rows)).copy()
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
        clean_palette(frame)
        # These two approved male poses face opposite to their assigned row.
        # Correct the source poses once so every walk cycle keeps its facing.
        if path.name == "doctor_male_design.png" and index in (5, 6):
            frame = pygame.transform.flip(frame, True, False)
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
