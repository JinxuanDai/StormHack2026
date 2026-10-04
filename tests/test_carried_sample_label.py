"""Carried sample text follows actual sprites without moving unrelated text."""

import copy
import unittest
from unittest.mock import patch

import pygame

from lab_panic.main import CARRIED_SAMPLE_LABEL_GAP, GameState, Renderer, display_position
from lab_panic.ui import theme


class CarriedSampleLabelTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.surface = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        self.renderer = Renderer(self.surface)
        self.game = GameState(high_score_path=None)

    def draw(self, *, local_player=0):
        state = self.game.snapshot(True)
        original = copy.deepcopy(state)
        records = []
        text = theme.text

        def record(surface, font, value, position, color=theme.INK, *, center=False):
            rect = text(surface, font, value, position, color, center=center)
            records.append((value, rect.copy(), color))
            return rect

        with patch("lab_panic.ui.theme.text", side_effect=record):
            self.renderer.draw(state, local_player)
        self.assertEqual(state, original)
        return records

    @staticmethod
    def is_sample_label(record):
        value, _, color = record
        # Station plates use the light ink; the carried overlay uses dark ink.
        return value.startswith("SAMPLE #") and color == theme.DARK_INK

    def give_samples(self):
        for player_id, player in enumerate(self.game.players):
            player["item"] = {"kind": "sample", "patient": player_id + 1}

    def test_labels_clear_both_sprites_in_every_direction_and_frame(self):
        self.give_samples()
        for direction in ("down", "left", "right", "up"):
            for frame in range(3):
                with self.subTest(direction=direction, frame=frame):
                    for player_id in (0, 1):
                        self.renderer.ui._player_facing[str(player_id)] = direction
                        self.renderer.ui._player_motion_until[str(player_id)] = 10000
                    with patch("lab_panic.ui.renderer.pygame.time.get_ticks", return_value=frame * 140):
                        labels = [r for r in self.draw(local_player=frame % 2) if self.is_sample_label(r)]
                    self.assertEqual(len(labels), 2)
                    for player_id, (value, label, _) in enumerate(labels):
                        player = self.game.players[player_id]
                        x, y = display_position(player["x"], player["y"])
                        sprite = self.renderer.ui.assets.character_frame(player_id, direction, frame)
                        bounds = self.renderer.ui.player_sprite_bounds(str(player_id))
                        self.assertEqual(bounds, sprite.get_rect(midbottom=(x, y + 22)))
                        self.assertEqual(value, f"SAMPLE #{player_id + 1}")
                        self.assertEqual(label.centerx, bounds.centerx)
                        self.assertEqual(bounds.top - label.bottom, CARRIED_SAMPLE_LABEL_GAP)
                        self.assertFalse(label.colliderect(bounds))

    def test_labels_follow_each_players_movement(self):
        self.give_samples()
        before = {value: rect for value, rect, color in self.draw()
                  if self.is_sample_label((value, rect, color))}
        positions = [display_position(p["x"], p["y"]) for p in self.game.players]
        for player, dx, dy in ((self.game.players[0], 40, -30),
                               (self.game.players[1], -50, 25)):
            player["x"] += dx
            player["y"] += dy
        after = {value: rect for value, rect, color in self.draw()
                 if self.is_sample_label((value, rect, color))}
        for player_id, player in enumerate(self.game.players):
            x, y = display_position(player["x"], player["y"])
            old_x, old_y = positions[player_id]
            label = f"SAMPLE #{player_id + 1}"
            self.assertEqual(after[label], before[label].move(x - old_x, y - old_y))

    def test_empty_hands_have_no_carried_sample_label(self):
        self.give_samples()
        self.draw()
        for player in self.game.players:
            player["item"] = None
        self.assertFalse(any(self.is_sample_label(record) for record in self.draw()))

    def test_station_hud_and_player_id_text_is_unchanged_when_carrying(self):
        before = self.draw()
        self.give_samples()
        after = [record for record in self.draw() if not self.is_sample_label(record)]
        self.assertEqual(after, before)

    def test_label_uses_actual_frame_size_instead_of_fixed_height(self):
        self.give_samples()
        # A different supplied frame size must still use the rect actually
        # blitted, rather than repeating the default character dimensions.
        frame = pygame.Surface((60, 150), pygame.SRCALPHA)
        with patch.object(self.renderer.ui.assets, "character_frame", return_value=frame):
            labels = [r for r in self.draw() if self.is_sample_label(r)]
        for player_id, (_, label, _) in enumerate(labels):
            bounds = self.renderer.ui.player_sprite_bounds(str(player_id))
            self.assertEqual(bounds.size, frame.get_size())
            self.assertEqual(bounds.top - label.bottom, CARRIED_SAMPLE_LABEL_GAP)
            self.assertFalse(label.colliderect(bounds))

    def test_report_and_package_label_positions_are_preserved(self):
        self.game.players[0]["item"] = {"kind": "report", "test": "CBC", "patient": 1}
        self.game.players[1]["item"] = {"kind": "package", "patient": 2}
        labels = {value: rect for value, rect, color in self.draw() if color == theme.DARK_INK}
        for player_id, value in ((0, "CBC #1"), (1, "PACKAGE #2")):
            player = self.game.players[player_id]
            x, y = display_position(player["x"], player["y"])
            self.assertEqual(labels[value].center, (x, y - 54))
