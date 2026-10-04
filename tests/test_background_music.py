"""Music lifecycle and optional-audio failure handling."""

import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from lab_panic.ui.music import BackgroundMusic, MUSIC_VOLUME


class BackgroundMusicTests(unittest.TestCase):
    @patch("lab_panic.ui.music.pygame.mixer")
    @patch.object(Path, "is_file", return_value=True)
    def test_loop_starts_once_and_releases_track(self, exists, mixer):
        mixer.get_init.return_value = (44100, -16, 2)
        music = BackgroundMusic()
        self.assertTrue(music.start())
        self.assertTrue(music.start())
        mixer.music.load.assert_called_once()
        mixer.music.set_volume.assert_called_once_with(MUSIC_VOLUME)
        mixer.music.play.assert_called_once_with(loops=-1, fade_ms=800)
        music.close()
        music.close()
        mixer.music.stop.assert_called_once()
        mixer.music.unload.assert_called_once()

    @patch("lab_panic.ui.music.pygame.mixer")
    @patch.object(Path, "is_file", return_value=False)
    def test_missing_track_never_initializes_audio(self, exists, mixer):
        self.assertFalse(BackgroundMusic().start())
        mixer.init.assert_not_called()
        mixer.music.load.assert_not_called()

    @patch("lab_panic.ui.music.pygame.mixer")
    @patch.object(Path, "is_file", return_value=True)
    def test_audio_device_failure_stays_optional(self, exists, mixer):
        mixer.get_init.return_value = None
        mixer.init.side_effect = pygame.error("No audio device")
        self.assertFalse(BackgroundMusic().start())
        mixer.music.play.assert_not_called()
