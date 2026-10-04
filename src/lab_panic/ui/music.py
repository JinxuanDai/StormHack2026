"""Stream the optional background track on Pygame's dedicated music channel."""

from pathlib import Path

import pygame


MUSIC_PATH = Path(__file__).resolve().parents[3] / "assets" / "audio" / "background_music.ogg"
MUSIC_VOLUME = 0.30


class BackgroundMusic:
    """Application-owned music, independent of gameplay and SFX channels."""

    def __init__(self) -> None:
        self._loaded = False

    def start(self, path: Path = MUSIC_PATH) -> bool:
        if self._loaded:
            return True
        try:
            if not path.is_file():
                return False
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.music.load(str(path))
            self._loaded = True
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(loops=-1, fade_ms=800)
            return True
        except (pygame.error, OSError, ValueError):
            self.close()
            return False

    def close(self) -> None:
        if self._loaded:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except pygame.error:
                pass
            self._loaded = False
