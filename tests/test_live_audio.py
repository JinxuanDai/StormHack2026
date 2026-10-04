"""Audio follows confirmed dual-patient gameplay, including remote trash."""

import unittest

from lab_panic.main import GameState, TEST_SECONDS, ZONES
from lab_panic.ui.audio_observer import AudioObserver


class LiveAudioTests(unittest.TestCase):
    def setUp(self):
        self.game = GameState(high_score_path=None)
        self.game.start()
        self.observer = AudioObserver()
        self.observe()

    def observe(self):
        return self.observer.observe(self.game.snapshot(True))

    def cues(self):
        return [event.cue for event in self.observe() if event.action == "play"]

    def test_second_patient_machine_and_package_flow(self):
        patient = self.game.patient_slots[1]
        patient["tasks"] = ["CBC"]
        player = self.game.players[1]
        player.update(x=ZONES["sample_1"].centerx, y=ZONES["sample_1"].bottom + 20)
        self.game.interact(1)
        self.assertEqual(self.cues(), ["pickup"])
        player.update(x=ZONES["CBC"].centerx, y=ZONES["CBC"].bottom + 20)
        self.game.interact(1)
        events = self.observe()
        self.assertEqual([e.cue for e in events if e.action == "play"], ["machine_insert", "processing_start"])
        self.assertTrue(any(e.action == "start_loop" for e in events))
        self.game.update(TEST_SECONDS["CBC"])
        self.assertEqual(self.cues(), ["processing_complete"])
        self.game.interact(1)
        self.assertEqual(self.cues(), ["machine_remove"])
        self.game._interact_package(1, 1)
        self.assertEqual(self.cues(), ["package_insert"])
        self.assertEqual(self.cues(), [])

    def test_patient_one_replacement_preserves_patient_two_loop(self):
        self.game.stations["CBC"].update(phase="processing", patient=self.game.patient_slots[1]["patient"])
        self.observe()
        self.game._replace_patient(0, "expired")
        self.assertEqual(self.observe(), ())
        self.game.update(TEST_SECONDS["CBC"])
        self.assertEqual(self.cues(), ["processing_complete"])

    def test_confirmed_trash_is_once_and_empty_hands_are_silent(self):
        player = self.game.players[1]
        player.update(x=ZONES["trash"].centerx, y=ZONES["trash"].bottom + 20,
                      item={"kind": "sample", "patient": self.game.patient})
        self.observe()
        self.game.interact(1)
        self.assertEqual(self.cues(), ["trash"])
        self.assertEqual(self.cues(), [])
        self.game.interact(1)
        self.assertEqual(self.cues(), [])

    def test_disconnect_and_result_stop_loops_without_repeating(self):
        self.game.stations["CBC"].update(phase="processing", patient=self.game.patient)
        self.observe()
        self.assertTrue(any(e.action == "stop_all_loops" for e in self.observer.disconnect()))
        self.observe()
        self.assertEqual([e.cue for e in self.observer.present_result("success")], ["round_success"])
        self.assertEqual(self.observer.present_result("success"), ())
