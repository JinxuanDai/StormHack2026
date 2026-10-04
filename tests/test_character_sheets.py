"""Guard row isolation and consistent facing across the actual walk frames."""

import unittest

import pygame

from lab_panic.ui.assets import AssetStore, CHARACTER_ROOT, FEMALE_SKIN_BASE
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

    def test_menu_uses_the_approved_front_portraits(self):
        expected_sources = ((232, 380), (211, 400))
        store = AssetStore()
        for player_index, expected_size in enumerate(expected_sources):
            filename = "menu_doctor_female.png" if player_index == 0 else "menu_doctor_male.png"
            source = pygame.image.load(str(CHARACTER_ROOT / filename))
            portrait = store.menu_character(player_index)
            with self.subTest(character=filename):
                self.assertEqual(source.get_size(), expected_size)
                self.assertLessEqual(portrait.get_width(), 110)
                self.assertEqual(portrait.get_height(), 170)

    def test_female_gameplay_and_menu_skin_is_warm_without_tinting_coat(self):
        store = AssetStore()
        gameplay = store.character_frame(0, "down", 1, (40, 64))
        menu = store.menu_character(0)

        self.assertIn(FEMALE_SKIN_BASE, {
            tuple(gameplay.get_at((x, y)))[:3]
            for y in range(gameplay.get_height())
            for x in range(gameplay.get_width())
        })
        for image in (gameplay, menu):
            coat_pixels = 0
            warm_skin = []
            for y in range(image.get_height()):
                for x in range(image.get_width()):
                    color = image.get_at((x, y))
                    if color.a and abs(color.r - color.g) <= 8 and abs(color.g - color.b) <= 8:
                        coat_pixels += color.r > 200
                    if (color.a and color.r > 170 and color.r > color.g + 20
                            and color.g > color.b + 10):
                        warm_skin.append((color.r, color.g, color.b))
            self.assertGreater(coat_pixels, 10)
            self.assertGreater(len(warm_skin), 10)
            self.assertLess(sum(color[1] for color in warm_skin) / len(warm_skin), 200)
