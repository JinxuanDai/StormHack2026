"""Guard row isolation and consistent facing across the actual walk frames."""

import unittest

import pygame

from lab_panic.ui.assets import AssetStore, CHARACTER_ROOT, MALE_MENU_SKIN_BASE
from tools.build_doctor_sprites import (
    CLEAN_PALETTE,
    LAB_COAT,
    LAB_COAT_SHADOW,
    source_rows,
)


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

    def test_female_face_has_no_lab_coat_white_blocks(self):
        sheet = pygame.image.load(str(CHARACTER_ROOT / "doctor_female.png"))
        coat_colors = {LAB_COAT, LAB_COAT_SHADOW}
        for row in range(3):
            for column in range(3):
                frame = sheet.subsurface((column * 40, row * 64, 40, 64))
                face_colors = {
                    tuple(frame.get_at((x, y)))[:3]
                    for y in range(36)
                    for x in range(40)
                }
                with self.subTest(row=row, column=column):
                    self.assertTrue(face_colors.isdisjoint(coat_colors))

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

    def test_female_skin_matches_male_without_tinting_coat(self):
        store = AssetStore()
        female_gameplay = store.character_frame(0, "down", 1, (40, 64))
        male_gameplay = store.character_frame(1, "down", 1, (40, 64))
        menu = store.menu_character(0)

        def skin_palette(image):
            return {
                tuple(image.get_at((x, y)))[:3]
                for y in range(image.get_height())
                for x in range(image.get_width())
                if (image.get_at((x, y)).a
                    and image.get_at((x, y)).r > 190
                    and image.get_at((x, y)).r > image.get_at((x, y)).g + 8
                    and image.get_at((x, y)).g > image.get_at((x, y)).b + 5)
            }

        self.assertEqual(skin_palette(female_gameplay), skin_palette(male_gameplay))
        self.assertIn(MALE_MENU_SKIN_BASE, skin_palette(menu))
        for image in (female_gameplay, menu):
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
