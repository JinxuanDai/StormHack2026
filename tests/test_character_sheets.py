"""Guard row isolation and consistent facing across the actual walk frames."""

import unittest

import pygame

from lab_panic.ui.assets import CHARACTER_ROOT
from tools.build_doctor_sprites import CLEAN_PALETTE, source_rows


class CharacterSheetTests(unittest.TestCase):
    def test_source_rows_use_transparent_gutters(self):
        expected = {
            "male": [(33, 428), (447, 843), (871, 1271), (1298, 1706)],
            "female": [(44, 369), (395, 728), (756, 1088), (1111, 1488)],
        }
        for name, bands in expected.items():
            sheet = pygame.image.load(str(CHARACTER_ROOT / "design" / f"doctor_{name}_design.png"))
            self.assertEqual(source_rows(sheet), bands)

    def test_side_walk_frames_keep_face_on_correct_side(self):
        for name in ("male", "female"):
            sheet = pygame.image.load(str(CHARACTER_ROOT / f"doctor_{name}.png"))
            for row in (1, 2):
                for column in range(3):
                    frame = sheet.subsurface((column * 40, row * 64, 40, 64))
                    face_x = []
                    for y in range(32):
                        for x in range(40):
                            color = frame.get_at((x, y))
                            if (color.a and color.r > 170 and color.g > 110
                                    and color.b < 200 and color.r > color.g * 1.08):
                                face_x.append(x)
                    self.assertTrue(face_x)
                    center = sum(face_x) / len(face_x)
                    with self.subTest(character=name, row=row, column=column):
                        self.assertLess(center, 20) if row == 1 else self.assertGreater(center, 20)

    def test_runtime_sheets_use_only_the_clean_shared_palette(self):
        allowed = set(CLEAN_PALETTE)
        for name in ("male", "female"):
            sheet = pygame.image.load(str(CHARACTER_ROOT / f"doctor_{name}.png"))
            visible_colors = set()
            alpha_values = set()
            for y in range(sheet.get_height()):
                for x in range(sheet.get_width()):
                    color = sheet.get_at((x, y))
                    alpha_values.add(color.a)
                    if color.a:
                        visible_colors.add((color.r, color.g, color.b))
            with self.subTest(character=name):
                self.assertLessEqual(visible_colors, allowed)
                self.assertEqual(alpha_values, {0, 255})
