"""Regression coverage for sample insertion and pending CBC reports."""

import unittest

from lab_panic.main import GameState, TEST_SECONDS, ZONES


class StationInteractionTests(unittest.TestCase):
    def test_both_players_can_insert_sample_into_idle_cbc(self):
        for player_id in (0, 1):
            with self.subTest(player_id=player_id):
                game = GameState()
                game.start()
                player = game.players[player_id]
                player.update(x=ZONES["CBC"].centerx, y=ZONES["CBC"].bottom + 30,
                              item={"kind": "sample", "patient": game.patient})
                game.interact(player_id)
                self.assertIsNone(player["item"])
                self.assertEqual(game.stations["CBC"]["phase"], "processing")
                self.assertEqual(game.stations["CBC"]["patient"], game.patient)

    def test_pending_report_is_preserved_and_can_be_collected(self):
        game = GameState()
        game.start()
        player = game.players[0]
        player.update(x=ZONES["CBC"].centerx, y=ZONES["CBC"].bottom + 30,
                      item={"kind": "sample", "patient": game.patient})
        game.interact(0)
        game.update(TEST_SECONDS["CBC"])
        sample = {"kind": "sample", "patient": game.patient}
        player["item"] = sample
        game.interact(0)
        self.assertEqual(game.stations["CBC"]["phase"], "output")
        self.assertEqual(player["item"], sample)
        self.assertIn("Report ready", player["message"])
        player["item"] = None
        game.interact(0)
        self.assertEqual(player["item"], {"kind": "report", "patient": game.patient, "test": "CBC"})
        self.assertEqual(game.stations["CBC"]["phase"], "idle")
        player["item"] = sample
        game.interact(0)
        self.assertEqual(game.stations["CBC"]["phase"], "processing")


if __name__ == "__main__":
    unittest.main()
