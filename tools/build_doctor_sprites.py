"""Build the two Lab Panic doctor sheets from the credited free sprite bases.

Run from the repository root with the project's installed Python environment:

    .venv/bin/python tools/build_doctor_sprites.py

The source sheets use 20 x 32 cells arranged as three animation frames by four
directions.  Pixel operations are intentionally deterministic so the generated
game assets keep the original walk cycles exactly.
"""

from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
CHARACTER_ROOT = ROOT / "assets" / "sprites" / "characters"
SOURCE_ROOT = CHARACTER_ROOT / "source"
CELL_WIDTH = 20
CELL_HEIGHT = 32

TRANSPARENT = (255, 255, 255, 0)
COAT_LIGHT = (246, 245, 238, 255)
COAT_MID = (211, 213, 213, 255)
COAT_DARK = (145, 151, 154, 255)
SHIRT_LIGHT = (75, 91, 171, 255)
SHIRT_DARK = (36, 46, 114, 255)


def recolor_torso(
    sheet: pygame.Surface,
    palette: dict[tuple[int, int, int, int], tuple[int, int, int, int]],
) -> None:
    """Recolor clothing while leaving faces, hair, legs and shoes untouched."""
    for y in range(sheet.get_height()):
        local_y = y % CELL_HEIGHT
        if not 13 <= local_y <= 24:
            continue
        for x in range(sheet.get_width()):
            color = tuple(sheet.get_at((x, y)))
            replacement = palette.get(color)
            if replacement is not None:
                sheet.set_at((x, y), replacement)


def add_blue_shirt(sheet: pygame.Surface) -> None:
    """Expose a narrow blue shirt between the front edges of the white coat."""
    coat_colors = {COAT_LIGHT, COAT_MID, COAT_DARK}
    for row in range(3):  # Front, left and right views; the back stays white.
        for column in range(3):
            cell_x = column * CELL_WIDTH
            cell_y = row * CELL_HEIGHT
            if row == 0:
                xs = range(9, 12)
            elif row == 1:
                xs = range(8, 10)
            else:
                xs = range(10, 12)
            for local_y in range(16, 22):
                for local_x in xs:
                    point = (cell_x + local_x, cell_y + local_y)
                    if tuple(sheet.get_at(point)) in coat_colors:
                        color = SHIRT_LIGHT if local_y < 19 else SHIRT_DARK
                        sheet.set_at(point, color)


def build_female() -> pygame.Surface:
    sheet = pygame.image.load(str(SOURCE_ROOT / "female_base.png"))
    recolor_torso(
        sheet,
        {
            (204, 45, 69, 255): COAT_LIGHT,
            (135, 23, 47, 255): COAT_MID,
            (77, 14, 34, 255): COAT_DARK,
        },
    )
    add_blue_shirt(sheet)
    return sheet


def build_male() -> pygame.Surface:
    sheet = pygame.image.load(str(SOURCE_ROOT / "male_base.png"))
    recolor_torso(
        sheet,
        {
            (255, 255, 255, 255): COAT_LIGHT,
            (201, 201, 201, 255): COAT_MID,
            (152, 152, 152, 255): COAT_MID,
            (98, 98, 98, 255): COAT_DARK,
        },
    )
    # This base already contains the same blue family used by the supplied
    # doctor reference, so retaining it keeps the inner shirt naturally shaded.
    return sheet


def main() -> None:
    pygame.init()
    CHARACTER_ROOT.mkdir(parents=True, exist_ok=True)
    pygame.image.save(build_female(), CHARACTER_ROOT / "doctor_female.png")
    pygame.image.save(build_male(), CHARACTER_ROOT / "doctor_male.png")
    pygame.quit()


if __name__ == "__main__":
    main()
