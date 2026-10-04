"""Verify authoritative state is adapted without changing gameplay data."""

import copy
import unittest

from lab_panic.main import GameState, TEST_SECONDS, ZONES, display_zone, round_view
from lab_panic.ui import theme


class UIIntegrationTests(unittest.TestCase):
    def test_live_machine_states_and_items_preserve_snapshot(self):
        game = GameState()
        game.stations["CBC"].update(phase="processing", elapsed=TEST_SECONDS["CBC"] / 2)
        game.stations["SMEAR"].update(phase="output")
        game.package_ready = True
        game.players[0]["item"] = {"kind": "sample", "patient": game.patient}
        game.players[1]["item"] = {"kind": "report", "test": "CBC", "patient": game.patient}
        state = game.snapshot(True)
        original = copy.deepcopy(state)
        view = round_view(state)
        stations = {station.station_id: station for station in view.stations}
        self.assertTrue(stations["CBC"].is_processing)
        self.assertEqual(stations["CBC"].processing_progress, 0.5)
        self.assertTrue(stations["SMEAR"].is_complete)
        self.assertTrue(stations["package"].is_complete)
        self.assertIsNotNone(view.players[0].held_item)
        self.assertIsNone(view.players[1].held_item)
        self.assertEqual(state, original)

    def test_station_bounds_match_mapped_collision_zones_inside_room(self):
        view = round_view(GameState().snapshot(True))
        import pygame
        room = pygame.Rect(theme.ROOM)
        for station in view.stations:
            rect = pygame.Rect(station.x, station.y, station.width, station.height)
            self.assertEqual(rect, display_zone(ZONES[station.station_id]))
            self.assertTrue(room.contains(rect))
