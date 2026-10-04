"""Resolution changes preserve canvas coordinates and reject black-bar clicks."""

import unittest

import pygame

from lab_panic.main import ZONES, display_zone
from lab_panic.ui import theme
from lab_panic.ui.display import logical_position, viewport_for


class DisplayTests(unittest.TestCase):
    def test_widescreen_and_portrait_preserve_aspect_ratio(self):
        for size in ((1920, 1080), (2560, 1440), (1280, 1024), (800, 1200)):
            viewport = viewport_for(size)
            self.assertTrue(pygame.Rect((0, 0), size).contains(viewport))
            self.assertAlmostEqual(viewport.width / viewport.height,
                                   theme.WIDTH / theme.HEIGHT, places=2)
            center = logical_position(viewport.center, viewport)
            self.assertLessEqual(abs(center[0] - 480), 1)
            self.assertLessEqual(abs(center[1] - 320), 1)

    def test_menu_click_and_collision_coordinates_scale_together(self):
        viewport = viewport_for((1920, 1080))
        for zone in ZONES.values():
            logical = display_zone(zone).center
            physical = (viewport.x + round(logical[0] * viewport.width / theme.WIDTH),
                        viewport.y + round(logical[1] * viewport.height / theme.HEIGHT))
            mapped = logical_position(physical, viewport)
            self.assertLessEqual(abs(mapped[0] - logical[0]), 1)
            self.assertLessEqual(abs(mapped[1] - logical[1]), 1)
        self.assertEqual(logical_position((0, 0), viewport), (-1, -1))

    def test_window_mode_is_identity(self):
        viewport = viewport_for((960, 640))
        self.assertEqual(logical_position((480, 300), viewport), (480, 300))
