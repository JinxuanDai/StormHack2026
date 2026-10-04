"""The ground footprint stays on the rendered floor without losing stations."""

import unittest
from unittest.mock import patch

import pygame

from lab_panic import layout
from lab_panic.main import GameState, PLAYER_SPEED, ZONES, display_position, display_zone
from lab_panic.ui import theme
from lab_panic.ui.assets import AssetStore
from lab_panic.ui.display import logical_position, viewport_for
from lab_panic.ui.renderer import Renderer


class TopWallTests(unittest.TestCase):
    def game_at_wall(self, player_id):
        game = GameState(high_score_path=None)
        game.start()
        player = game.players[player_id]
        player.update(x=640.0, y=float(layout.WORLD_FLOOR_TOP + 22))
        return game, player

    def assert_on_floor(self, game, player):
        footprint = game.player_rect(player)
        self.assertEqual(footprint.size, (36, 44))
        self.assertGreaterEqual(footprint.top, layout.WORLD_FLOOR_TOP)
        self.assertGreaterEqual(display_zone(footprint).top, layout.FLOOR_TOP)

    def test_both_players_stop_after_repeated_upward_movement(self):
        for player_id in (0, 1):
            for dt in (1 / 60, 0.05):
                with self.subTest(player=player_id, dt=dt):
                    game, player = self.game_at_wall(player_id)
                    player["y"] += 50
                    start_y = player["y"]
                    for _ in range(120):
                        game.move(player_id, 0, -1, dt)
                        self.assert_on_floor(game, player)
                    self.assertLess(player["y"], start_y)
                    stopped_y = player["y"]
                    game.move(player_id, 0, -1, dt)
                    self.assertEqual(player["y"], stopped_y)

    def test_both_upward_diagonals_slide_along_wall(self):
        for player_id in (0, 1):
            for dx in (-1, 1):
                with self.subTest(player=player_id, dx=dx):
                    game, player = self.game_at_wall(player_id)
                    start_x, start_y = player["x"], player["y"]
                    for _ in range(30):
                        game.move(player_id, dx, -1, 0.05)
                        self.assert_on_floor(game, player)
                    self.assertGreater((player["x"] - start_x) * dx, 0)
                    self.assertEqual(player["y"], start_y)

    def test_horizontal_movement_and_retreat_remain_possible(self):
        for player_id in (0, 1):
            for dx in (-1, 1):
                with self.subTest(player=player_id, dx=dx):
                    game, player = self.game_at_wall(player_id)
                    start_x, start_y = player["x"], player["y"]
                    game.move(player_id, dx, 0, 0.05)
                    self.assertGreater((player["x"] - start_x) * dx, 0)
                    self.assertEqual(player["y"], start_y)
                    game.move(player_id, 0, 1, 0.05)
                    self.assertGreater(player["y"], start_y)
                    self.assert_on_floor(game, player)

    def test_collision_boundary_matches_rendered_floor_edge(self):
        renderer = Renderer.__new__(Renderer)
        renderer.assets = AssetStore()
        surface = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        with patch("lab_panic.ui.renderer.pygame.draw.line", wraps=pygame.draw.line) as line:
            renderer._room(surface)
        start, end = line.call_args.args[2:4]
        self.assertEqual(start[1], end[1])
        self.assertEqual(start[1], display_position(0, layout.WORLD_FLOOR_TOP)[1])
        self.assertEqual(start[1], layout.FLOOR_TOP)

    def test_boundary_alignment_survives_window_and_fullscreen_scaling(self):
        game, player = self.game_at_wall(0)
        footprint_y = display_zone(game.player_rect(player)).top
        for size in ((960, 640), (1920, 1080), (2560, 1440), (1280, 1024), (800, 1200)):
            with self.subTest(size=size):
                viewport = viewport_for(size)
                floor_y = viewport.y + round(layout.FLOOR_TOP * viewport.height / theme.HEIGHT)
                player_y = viewport.y + round(footprint_y * viewport.height / theme.HEIGHT)
                self.assertEqual(player_y, floor_y)
                mapped = logical_position((viewport.centerx, player_y), viewport)
                self.assertLessEqual(abs(mapped[1] - layout.FLOOR_TOP), 1)

    def move_to(self, game, player_id, x, y):
        player = game.players[player_id]
        for axis, target in (("x", x), ("y", y)):
            for _ in range(200):
                delta = target - player[axis]
                if abs(delta) < 0.001:
                    break
                direction = 1 if delta > 0 else -1
                before = player[axis]
                game.move(player_id, direction if axis == "x" else 0,
                          direction if axis == "y" else 0,
                          min(0.05, abs(delta) / PLAYER_SPEED))
                self.assertNotEqual(player[axis], before, "Approach path was blocked")
                self.assert_on_floor(game, player)
            self.assertAlmostEqual(player[axis], target)

    def test_both_players_can_walk_to_and_use_all_top_stations(self):
        for player_id in (0, 1):
            for station in ("sample_0", "sample_1", "CBC"):
                with self.subTest(player=player_id, station=station):
                    game = GameState(high_score_path=None)
                    game.start()
                    player = game.players[player_id]
                    # From the real spawn, go through the central aisle and
                    # approach the rear workstations from the walkable floor.
                    self.move_to(game, player_id, 640, 300)
                    self.move_to(game, player_id, ZONES[station].centerx,
                                 layout.WORLD_FLOOR_TOP + 22)
                    self.assertTrue(game.near(player, ZONES[station]))
                    if station == "CBC":
                        player["item"] = {"kind": "sample", "patient": game.patient}
                    game.interact(player_id)
                    if station == "CBC":
                        self.assertIsNone(player["item"])
                        self.assertEqual(game.stations[station]["phase"], "processing")
                    else:
                        patient = game.patient_slots[int(station[-1])]["patient"]
                        self.assertEqual(player["item"], {"kind": "sample", "patient": patient})
