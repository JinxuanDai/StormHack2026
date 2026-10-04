"""Character facing ignores display-coordinate and network rounding noise."""

import unittest
from unittest.mock import patch

import pygame

from lab_panic.ui.renderer import Renderer
from lab_panic.ui.views import PlayerView


class PlayerFacingStabilityTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.surface = pygame.Surface((960, 640))
        self.renderer = Renderer()

    def draw_male(self, x: int, y: int, ticks: int) -> None:
        with patch("lab_panic.ui.renderer.pygame.time.get_ticks", return_value=ticks):
            self.renderer._player(self.surface, PlayerView("1", x, y), 1)

    def test_one_pixel_horizontal_jitter_does_not_change_facing_or_start_walk(self):
        self.draw_male(300, 300, 100)
        self.draw_male(301, 300, 110)
        self.draw_male(300, 300, 120)

        self.assertEqual(self.renderer._player_facing["1"], "down")
        self.assertEqual(self.renderer._player_motion_until.get("1", 0), 0)

    def test_real_horizontal_movement_still_changes_facing(self):
        self.draw_male(300, 300, 100)
        self.draw_male(303, 300, 110)

        self.assertEqual(self.renderer._player_facing["1"], "right")
        self.assertEqual(self.renderer._player_motion_until["1"], 230)


if __name__ == "__main__":
    unittest.main()
