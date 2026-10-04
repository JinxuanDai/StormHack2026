"""Movement floor boundary and enlarged sprite attachment positions."""

import unittest

from lab_panic.main import GameState, WALKABLE_TOP, display_position
from lab_panic.ui import theme
from lab_panic.ui.renderer import held_item_position, player_visual_rect


class PlayerPlacementTests(unittest.TestCase):
    def test_player_cannot_walk_into_rear_wall(self):
        game = GameState(high_score_path=None)
        game.start()
        player = game.players[0]
        player.update(x=640, y=WALKABLE_TOP + 22)
        before = player["y"]
        game.move(0, 0, -1, 0.05)
        self.assertEqual(player["y"], before)
        self.assertGreaterEqual(display_position(640, game.player_rect(player).top)[1], theme.FLOOR_TOP)
        game.move(0, 0, 1, 0.05)
        self.assertGreater(player["y"], before)
        self.assertEqual(game.player_rect(player).size, (36, 44))

    def test_hand_anchor_tracks_sprite_and_movement(self):
        for x, y in ((300, 400), (640, 350)):
            rect = player_visual_rect(x, y)
            hand = held_item_position(x, y)
            self.assertEqual(rect.size, (80, 128))
            self.assertEqual(rect.midbottom, (x, y + 22))
            self.assertTrue(rect.collidepoint(hand))
            moved = held_item_position(x + 11, y + 17)
            self.assertEqual(moved, (hand[0] + 11, hand[1] + 17))
