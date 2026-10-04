"""Workstation overhead space is walkable without changing interaction reach."""

import unittest
from unittest.mock import patch

import pygame

from lab_panic.main import GameState, MOVEMENT_ZONES, ZONES, round_view
from lab_panic.ui.renderer import Renderer


class MovementZoneTests(unittest.TestCase):
    def test_player_can_move_through_package_overhead_but_not_table_base(self):
        game = GameState(high_score_path=None)
        game.start()
        zone = ZONES["package_0"]
        player = game.players[0]
        # Move down into the old rectangle's top, above the floor footprint.
        player.update(x=zone.centerx, y=zone.top - 23)
        before = player["y"]
        game.move(0, 0, 1, 0.05)
        self.assertGreater(player["y"], before)
        self.assertTrue(game.near(player, zone))
        footprint = MOVEMENT_ZONES["package_0"]
        player["y"] = footprint.top - 26
        before = player["y"]
        game.move(0, 0, 1, 0.05)
        self.assertEqual(player["y"], before)
        self.assertEqual(game.player_rect(player).size, (36, 44))

    def test_submit_still_uses_original_interaction_zone(self):
        game = GameState(high_score_path=None)
        game.start()
        patient = game.patient_slots[0]
        player = game.players[0]
        player.update(x=ZONES["submit"].left - 30, y=ZONES["submit"].top,
                      item={"kind": "package", "patient": patient["patient"]})
        game.interact(0)
        self.assertEqual(game.completed, 1)

    def test_labels_are_drawn_after_all_players(self):
        # A call-order check needs no fonts, assets or real display.
        renderer = Renderer.__new__(Renderer)
        renderer.fonts = None
        order = []
        view = round_view(GameState(high_score_path=None).snapshot(True))
        with patch.object(Renderer, "_room"), patch.object(Renderer, "_station", return_value=pygame.Rect(0, 0, 1, 1)), \
             patch.object(Renderer, "_player", side_effect=lambda *args: order.append("player")), \
             patch.object(Renderer, "_station_label", side_effect=lambda *args: order.append("label")), \
             patch("lab_panic.ui.renderer.hud.draw_hud"):
            renderer.draw_gameplay(pygame.Surface((960, 640)), view)
        self.assertEqual(order[:2], ["player", "player"])
        self.assertTrue(all(value == "label" for value in order[2:]))
