"""Standalone checks: python -m lab_panic.ui.audio_check.

Uses synthetic snapshots, WAV inspection and a mocked mixer; no main.py import,
audio device, generated test files or shared test infrastructure are needed.
"""

from copy import deepcopy
from pathlib import Path
import struct
import unittest
from unittest.mock import Mock, patch
import wave

import pygame

from .audio import AUDIO_ROOT, AudioManager, CUE_FILES, CUE_VOLUMES
from .audio_demo import BINDINGS, SoundPreview, STATION_ID
from .audio_observer import AudioEvent, AudioObserver


def snapshot() -> dict:
    return {
        "patient": 1, "started": True, "finished": False, "connected": True,
        "players": [{"item": None}, {"item": None}],
        "stations": {key: {"phase": "idle", "patient": 0, "elapsed": 0.0}
                     for key in ("CBC", "COAG", "SMEAR")},
        "package_reports": [], "completed": 0, "remaining": 180,
    }


def item(kind: str, test: str | None = None, patient: int = 1) -> dict:
    value = {"kind": kind, "patient": patient}
    if test is not None:
        value["test"] = test
    return value


class ObserverChecks(unittest.TestCase):
    def setUp(self):
        self.observer = AudioObserver()
        self.state = snapshot()

    def observe(self):
        original = deepcopy(self.state)
        events = self.observer.observe(self.state)
        self.assertEqual(self.state, original, "Audio mutated its input")
        return events

    def start_machine(self, station="CBC"):
        self.state["stations"][station].update(phase="processing", patient=1)
        return self.observe()

    def test_first_and_repeated_snapshots_are_silent(self):
        self.state["players"][0]["item"] = item("sample")
        self.state["stations"]["CBC"].update(phase="processing", patient=1)
        self.state["package_reports"].append("COAG")
        self.assertEqual(self.observe(), ())
        self.assertEqual(self.observe(), ())
        self.state["stations"]["CBC"]["elapsed"] = 1.0
        self.state["players"][0]["message"] = "Started CBC"
        self.assertEqual(self.observe(), ())

    def test_pickup_then_insertion_start_and_single_loop(self):
        self.observe()
        self.state["players"][0]["item"] = item("sample")
        self.assertEqual(self.observe(), (AudioEvent("play", "pickup"),))
        self.state["players"][0]["item"] = None
        self.assertEqual(self.start_machine(), (
            AudioEvent("play", "machine_insert", "CBC"),
            AudioEvent("play", "processing_start", "CBC"),
            AudioEvent("start_loop", "processing_loop", "CBC")))
        self.assertEqual(self.observe(), ())
        self.state["stations"]["CBC"]["elapsed"] = 1.0
        self.assertEqual(self.observe(), ())

    def test_completion_stops_loop_before_cue_then_collection(self):
        self.observe()
        self.start_machine()
        self.state["stations"]["CBC"]["phase"] = "output"
        self.assertEqual(self.observe(), (
            AudioEvent("stop_loop", station_id="CBC"),
            AudioEvent("play", "processing_complete", "CBC")))
        self.assertEqual(self.observe(), ())
        self.state["stations"]["CBC"].update(phase="idle", patient=0)
        self.state["players"][1]["item"] = item("report", "CBC")
        self.assertEqual(self.observe(), (AudioEvent("play", "machine_remove", "CBC"),))
        self.assertEqual(self.observe(), ())

    def test_removal_requires_matching_report_and_patient(self):
        for report in (item("report", "COAG"), item("report", "CBC", patient=99), item("sample")):
            with self.subTest(report=report):
                observer = AudioObserver()
                state = snapshot()
                state["stations"]["CBC"].update(phase="output", patient=1)
                observer.observe(state)
                state["stations"]["CBC"].update(phase="idle", patient=0)
                state["players"][0]["item"] = report
                self.assertEqual(observer.observe(state), (AudioEvent("play", "pickup"),))

    def test_output_cleared_without_acquisition_is_silent(self):
        self.state["stations"]["CBC"].update(phase="output", patient=1)
        self.observe()
        self.state["stations"]["CBC"].update(phase="idle", patient=0)
        self.assertEqual(self.observe(), ())

    def test_package_additions_are_copied_and_coalesced(self):
        self.state["players"][0]["item"] = item("report", "CBC")
        self.observe()
        self.state["package_reports"].extend(["CBC", "SMEAR"])
        self.state["players"][0]["item"] = None
        self.assertEqual(self.observe(), (AudioEvent("play", "package_insert", "package"),))
        self.assertEqual(self.observe(), ())
        self.state["players"][0]["item"] = item("package")
        self.assertEqual(self.observe(), (AudioEvent("play", "pickup"),))

    def test_patient_reset_suppresses_all_reset_cues_and_stops_loops(self):
        self.observe()
        self.start_machine()
        self.state["patient"] = 2
        self.state["players"][0]["item"] = item("sample", patient=2)
        self.state["package_reports"].append("SMEAR")
        self.state["stations"]["CBC"].update(phase="idle", patient=0)
        self.assertEqual(self.observe(), (AudioEvent("stop_all_loops"),))
        self.assertEqual(self.observe(), ())

    def test_held_items_are_copied_not_retained(self):
        held = item("sample")
        self.state["players"][0]["item"] = held
        self.observe()
        # Mutating the caller's object cannot rewrite the observer's baseline.
        held.update(kind="report", test="CBC")
        self.assertEqual(self.observe(), ())  # held -> held is not an acquisition.
        self.state["players"][0]["item"] = None
        self.assertEqual(self.observe(), ())
        held["kind"] = "package"
        self.state["players"][0]["item"] = held
        self.assertEqual(self.observe(), (AudioEvent("play", "pickup"),))

    def test_disappearance_messages_and_scores_do_not_invent_cues(self):
        self.state["players"][0]["item"] = item("sample")
        self.observe()
        self.state["players"][0].update(item=None, message="Item discarded")
        self.state["completed"] = 100
        self.state["remaining"] = 0
        self.assertEqual(self.observe(), ())
        self.state["players"][0]["message"] = "REJECTED: duplicate report"
        self.assertEqual(self.observe(), ())

    def test_loops_are_independent_and_stop_on_station_exit(self):
        self.observe()
        self.start_machine("CBC")
        self.start_machine("COAG")
        self.state["stations"]["CBC"]["phase"] = "idle"
        self.assertEqual(self.observe(), (AudioEvent("stop_loop", station_id="CBC"),))
        del self.state["stations"]["COAG"]
        self.assertEqual(self.observe(), (AudioEvent("stop_loop", station_id="COAG"),))

    def test_round_end_stops_loops_without_selecting_result(self):
        self.observe()
        self.start_machine()
        self.state["finished"] = True
        self.state["stations"]["CBC"]["phase"] = "output"
        self.assertEqual(self.observe(), (AudioEvent("stop_all_loops"),))
        self.assertEqual(self.observe(), ())

    def test_each_result_once_per_session_even_if_contradicted(self):
        for result, opposite in (("success", "failure"), ("failure", "success")):
            with self.subTest(result=result):
                observer = AudioObserver()
                self.assertEqual(observer.present_result(result), (AudioEvent("play", f"round_{result}"),))
                self.assertEqual(observer.present_result(result), ())
                self.assertEqual(observer.present_result(opposite), ())
                observer.disconnect()
                self.assertEqual(observer.present_result(result), ())
                observer.reset()
                self.assertEqual(observer.present_result(opposite), (AudioEvent("play", f"round_{opposite}"),))

    def test_result_stops_loops_and_suppresses_further_processing(self):
        self.observe()
        self.start_machine()
        self.assertEqual(self.observer.present_result("success"), (
            AudioEvent("stop_all_loops"), AudioEvent("play", "round_success")))
        self.assertEqual(self.start_machine("COAG"), ())

    def test_unknown_result_does_not_consume_latch(self):
        self.assertEqual(self.observer.present_result("unknown"), ())
        self.assertEqual(self.observer.present_result("failure"), (AudioEvent("play", "round_failure"),))

    def test_patient_change_does_not_reset_result_latch(self):
        self.observe()
        self.observer.present_result("success")
        self.state["patient"] = 2
        self.observe()
        self.assertEqual(self.observer.present_result("success"), ())

    def test_session_change_is_baseline_and_rearms_result(self):
        self.observer.observe(self.state, session_id="first")
        self.state["stations"]["CBC"].update(phase="processing", patient=1)
        self.observer.observe(self.state, session_id="first")
        self.assertEqual(self.observer.observe(self.state, session_id="second"), (AudioEvent("stop_all_loops"),))
        self.assertEqual(self.observer.present_result("success"), (AudioEvent("play", "round_success"),))
        self.assertEqual(self.observer.observe(self.state, session_id="third"), ())
        self.assertEqual(self.observer.present_result("failure"), (AudioEvent("play", "round_failure"),))

    def test_explicit_and_snapshot_disconnect_baseline_on_reconnect(self):
        self.observe()
        self.start_machine()
        self.assertEqual(self.observer.disconnect(), (AudioEvent("stop_all_loops"),))
        self.assertEqual(self.observer.disconnect(), ())
        self.state["stations"]["CBC"]["phase"] = "output"
        self.assertEqual(self.observe(), ())
        self.start_machine("COAG")
        self.state["connected"] = False
        self.assertEqual(self.observe(), (AudioEvent("stop_all_loops"),))
        self.state["connected"] = True
        self.state["players"][0]["item"] = item("sample")
        self.assertEqual(self.observe(), ())

    def test_waiting_and_new_round_are_silent_baselines(self):
        self.state["started"] = False
        self.observe()
        self.state["started"] = True
        self.assertEqual(self.observe(), ())
        self.state["finished"] = True
        self.observe()
        self.observer.present_result("success")
        self.state["finished"] = False
        self.assertEqual(self.observe(), ())
        self.assertEqual(self.observer.present_result("failure"), (AudioEvent("play", "round_failure"),))


class ManagerChecks(unittest.TestCase):
    def setUp(self):
        self.mixer = self.enterContext(patch("lab_panic.ui.audio.pygame.mixer"))
        self.mixer.get_init.return_value = (44100, -16, 2)
        self.is_file = self.enterContext(patch.object(Path, "is_file", return_value=True))

    def test_missing_files_and_unknown_cues_are_silent(self):
        self.is_file.return_value = False
        manager = AudioManager()
        self.assertEqual(manager.loaded_cues, ())
        self.assertFalse(manager.play("pickup"))
        self.assertFalse(manager.play("drop"))
        self.assertFalse(manager.start_processing("CBC"))
        self.mixer.Sound.assert_not_called()

    def test_disabled_audio_never_initializes_or_loads(self):
        manager = AudioManager(enabled=False)
        self.assertFalse(manager.available)
        self.mixer.init.assert_not_called()
        self.mixer.Sound.assert_not_called()

    def test_mixer_initialization_failure_is_safe(self):
        self.mixer.get_init.return_value = None
        self.mixer.init.side_effect = pygame.error("No audio device")
        manager = AudioManager()
        self.assertFalse(manager.available)
        self.assertFalse(manager.play("pickup"))
        self.assertFalse(manager.start_processing("CBC"))
        manager.close()

    def test_mixer_is_initialized_only_when_needed(self):
        self.mixer.get_init.side_effect = [None, (44100, -16, 2)]
        AudioManager()
        self.mixer.init.assert_called_once_with()

    def test_preload_caches_sounds_and_accepts_filename_overrides(self):
        manager = AudioManager(files={"pickup": "pickup.ogg"})
        self.assertEqual(set(manager.loaded_cues), set(CUE_FILES))
        self.assertEqual(self.mixer.Sound.call_count, len(CUE_FILES))
        self.mixer.Sound.assert_any_call(str(manager.root / "pickup.ogg"))
        manager.preload()
        self.assertEqual(self.mixer.Sound.call_count, len(CUE_FILES))
        self.mixer.init.assert_not_called()

    def test_bad_files_do_not_prevent_other_cues_loading(self):
        self.mixer.Sound.side_effect = [pygame.error("Bad sound")] + [Mock() for _ in range(len(CUE_FILES) - 1)]
        manager = AudioManager()
        self.assertNotIn("pickup", manager.loaded_cues)
        self.assertIn("round_success", manager.loaded_cues)

    def test_per_cue_volume_is_applied_once_and_loop_is_quieter(self):
        sounds = {cue: Mock() for cue in CUE_FILES}
        self.mixer.Sound.side_effect = list(sounds.values())
        manager = AudioManager()
        manager.preload()
        for cue, sound in sounds.items():
            sound.set_volume.assert_called_once_with(CUE_VOLUMES[cue])
        for cue in ("processing_complete", "round_success", "round_failure"):
            self.assertLess(CUE_VOLUMES["processing_loop"], CUE_VOLUMES[cue])

    def test_volume_backend_failure_skips_sound_safely(self):
        self.mixer.Sound.return_value.set_volume.side_effect = pygame.error("Device lost")
        manager = AudioManager()
        self.assertEqual(manager.loaded_cues, ())
        self.assertFalse(manager.play("pickup"))

    def test_one_loop_per_station_and_no_shared_mixer_shutdown(self):
        first, second = Mock(), Mock()
        self.mixer.find_channel.side_effect = [first, second]
        manager = AudioManager()
        self.assertTrue(manager.start_processing("CBC"))
        self.assertTrue(manager.start_processing("CBC"))
        self.assertTrue(manager.start_processing("COAG"))
        self.assertEqual(self.mixer.find_channel.call_count, 2)
        first.play.assert_called_once_with(self.mixer.Sound.return_value, loops=-1)
        manager.stop_processing("CBC")
        first.stop.assert_called_once_with()
        second.stop.assert_not_called()
        manager.close()
        manager.close()
        second.stop.assert_called_once_with()
        self.mixer.quit.assert_not_called()
        self.assertFalse(manager.play("pickup"))

    def test_channels_are_not_stolen_when_busy(self):
        self.mixer.find_channel.return_value = None
        manager = AudioManager()
        self.assertFalse(manager.play("pickup"))
        self.assertFalse(manager.start_processing("CBC"))
        self.mixer.find_channel.assert_called_with()

    def test_playback_and_stop_failures_are_safe(self):
        manager = AudioManager()
        channel = self.mixer.find_channel.return_value
        self.assertTrue(manager.start_processing("CBC"))
        channel.stop.side_effect = pygame.error("Mixer stopped")
        manager.stop_all_loops()
        channel.play.side_effect = pygame.error("Device lost")
        self.assertFalse(manager.play("pickup"))
        self.assertFalse(manager.start_processing("CBC"))
        self.mixer.get_init.return_value = None
        self.assertFalse(manager.play("pickup"))
        manager.close()

    def test_observer_events_drive_manager_without_assets(self):
        self.is_file.return_value = False
        manager, observer, state = AudioManager(), AudioObserver(), snapshot()
        manager.handle(observer.observe(state))
        state["stations"]["CBC"].update(phase="processing", patient=1)
        manager.handle(observer.observe(state))
        state["stations"]["CBC"]["phase"] = "output"
        manager.handle(observer.observe(state))
        manager.handle(observer.present_result("failure"))
        manager.handle(observer.disconnect())
        manager.close()
        self.mixer.find_channel.assert_not_called()

    def test_event_dispatch_plays_cues_and_stops_the_matching_loop(self):
        insert, start, loop, complete, result = (Mock() for _ in range(5))
        self.mixer.find_channel.side_effect = [insert, start, loop, complete, result]
        manager, observer, state = AudioManager(), AudioObserver(), snapshot()
        manager.handle(observer.observe(state))
        state["stations"]["CBC"].update(phase="processing", patient=1)
        manager.handle(observer.observe(state))
        manager.handle(observer.observe(state))
        self.assertEqual(self.mixer.find_channel.call_count, 3)
        insert.play.assert_called_once_with(self.mixer.Sound.return_value)
        start.play.assert_called_once_with(self.mixer.Sound.return_value)
        loop.play.assert_called_once_with(self.mixer.Sound.return_value, loops=-1)
        state["stations"]["CBC"]["phase"] = "output"
        manager.handle(observer.observe(state))
        loop.stop.assert_called_once_with()
        complete.play.assert_called_once_with(self.mixer.Sound.return_value)
        manager.handle(observer.present_result("success"))
        manager.handle(observer.present_result("success"))
        result.play.assert_called_once_with(self.mixer.Sound.return_value)
        self.assertEqual(self.mixer.find_channel.call_count, 5)
        manager.close()


class AssetChecks(unittest.TestCase):
    def test_all_wavs_are_valid_mono_pcm_with_headroom(self):
        for cue, filename in CUE_FILES.items():
            with self.subTest(cue=cue), wave.open(str(AUDIO_ROOT / filename), "rb") as source:
                self.assertEqual((source.getnchannels(), source.getsampwidth(), source.getframerate()), (1, 2, 44100))
                self.assertEqual(source.getcomptype(), "NONE")
                count = source.getnframes()
                samples = struct.unpack(f"<{count}h", source.readframes(count))
                peak = max(abs(value) for value in samples)
                self.assertGreater(peak, 1000)
                self.assertLess(peak, 20000)
                duration = count / source.getframerate()
                if cue == "processing_loop":
                    self.assertTrue(0.6 <= duration <= 1.2)
                    self.assertLess(peak, 9000)
                    seam = abs(samples[-1] - samples[0])
                    largest_step = max(abs(b - a) for a, b in zip(samples, samples[1:]))
                    self.assertLessEqual(seam, largest_step + 1)
                elif cue.startswith("round_"):
                    self.assertTrue(0.8 <= duration <= 1.5)
                else:
                    self.assertTrue(0 < duration < 0.5)
                if cue != "processing_loop":
                    self.assertEqual((samples[0], samples[-1]), (0, 0))


class PreviewChecks(unittest.TestCase):
    def test_keys_route_to_all_ten_cues(self):
        audio = Mock()
        audio.play.return_value = audio.start_processing.return_value = True
        preview = SoundPreview(audio)
        expected = ("pickup", "machine_insert", "machine_remove", "processing_start",
                    "processing_loop", "processing_complete", "package_insert", "trash",
                    "round_success", "round_failure")
        self.assertEqual(tuple(cue for _, _, cue in BINDINGS), expected)
        for key, label, cue in BINDINGS:
            self.assertEqual(pygame.key.name(key), label)
            self.assertTrue(preview.press(key))
            if cue == "processing_loop":
                audio.start_processing.assert_called_once_with(STATION_ID)
            else:
                audio.play.assert_called_with(cue)
        self.assertTrue(preview.loop_on)
        self.assertTrue(preview.press(pygame.K_5))
        self.assertFalse(preview.loop_on)
        audio.stop_processing.assert_called_once_with(STATION_ID)

    def test_missing_loop_stays_off_and_unmapped_key_is_ignored(self):
        audio = Mock()
        audio.start_processing.return_value = False
        preview = SoundPreview(audio)
        self.assertFalse(preview.press(pygame.K_5))
        self.assertFalse(preview.loop_on)
        self.assertIn("unavailable", preview.last_action)
        self.assertFalse(preview.press(pygame.K_a))
        audio.play.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
