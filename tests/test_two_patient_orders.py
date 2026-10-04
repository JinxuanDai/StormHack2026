"""Independent patient slots, scoring, expiry and high-score coverage."""

import json
import tempfile
import unittest
from pathlib import Path

from lab_panic.main import GameState, PATIENT_SECONDS, ZONES


class TwoPatientOrderTests(unittest.TestCase):
    def make_game(self) -> GameState:
        game = GameState(high_score_path=None)
        game.start()
        game.patient_slots[0]["tasks"] = ["CBC", "COAG"]
        game.patient_slots[1]["tasks"] = ["SMEAR"]
        return game

    def test_each_sample_table_is_bound_to_its_patient(self):
        game = self.make_game()
        self.assertEqual([patient["patient"] for patient in game.patient_slots], [1, 2])
        for slot_index, expected_patient in enumerate((1, 2)):
            player = game.players[slot_index]
            player.update(x=ZONES[f"sample_{slot_index}"].centerx,
                          y=ZONES[f"sample_{slot_index}"].bottom + 30,
                          item=None)
            game.interact(slot_index)
            self.assertEqual(player["item"], {"kind": "sample", "patient": expected_patient})

    def test_wrong_package_rejects_report_without_changing_identity(self):
        game = self.make_game()
        player = game.players[0]
        report = {"kind": "report", "patient": 1, "test": "CBC"}
        player.update(x=ZONES["package_1"].centerx,
                      y=ZONES["package_1"].bottom + 30, item=report)
        game.interact(0)
        self.assertIs(player["item"], report)
        self.assertEqual(game.patient_slots[1]["package_reports"], [])
        self.assertIn("Package #2", player["message"])

        player.update(x=ZONES["package_0"].centerx,
                      y=ZONES["package_0"].bottom + 30)
        game.interact(0)
        self.assertIsNone(player["item"])
        self.assertEqual(game.patient_slots[0]["package_reports"], ["CBC"])

    def test_finishing_one_patient_replaces_only_that_slot_and_scores(self):
        game = self.make_game()
        game.patient_slots[0]["remaining"] = PATIENT_SECONDS - 9.0
        game.players[0]["item"] = {"kind": "package", "patient": 1}
        game.players[0].update(x=ZONES["submit"].left - 30,
                               y=ZONES["submit"].centery)
        game.interact(0)
        self.assertEqual(game.score, 100)
        self.assertEqual(game.completed, 1)
        self.assertEqual([patient["patient"] for patient in game.patient_slots], [3, 2])

    def test_timeout_penalizes_and_replaces_only_expired_patient(self):
        game = self.make_game()
        game.patient_slots[0]["remaining"] = 0.01
        game.patient_slots[1]["remaining"] = 20.0
        game.update(0.02)
        self.assertEqual(game.score, -40)
        self.assertEqual([patient["patient"] for patient in game.patient_slots], [3, 2])
        self.assertAlmostEqual(game.patient_slots[1]["remaining"], 19.98)

    def test_score_tiers(self):
        expected = ((5, 100), (10, 100), (15, 80), (25, 60), (35, 40), (44, 20))
        for elapsed, points in expected:
            with self.subTest(elapsed=elapsed):
                self.assertEqual(GameState.completion_score(PATIENT_SECONDS - elapsed), points)

    def test_host_high_score_persists_locally(self):
        with tempfile.TemporaryDirectory() as directory:
            score_path = Path(directory) / "score.json"
            game = GameState(high_score_path=score_path)
            game.start()
            game.score = 180
            game.remaining = 0.01
            game.update(0.02)
            self.assertEqual(json.loads(score_path.read_text())["high_score"], 180)
            self.assertEqual(GameState(high_score_path=score_path).high_score, 180)


if __name__ == "__main__":
    unittest.main()
