"""Optional Pygame playback for presentation cues; missing audio stays silent.

Audio Phase 2 supplies replaceable procedural WAV placeholders. Trash still
needs an explicit confirmed-action hook from A; there is no generic drop cue.
"""

from collections.abc import Iterable, Mapping
from pathlib import Path

import pygame

from .audio_observer import AudioEvent


AUDIO_ROOT = Path(__file__).resolve().parents[3] / "assets" / "audio"
CUE_FILES = {cue: f"{cue}.wav" for cue in (
    "pickup", "machine_insert", "machine_remove", "processing_start",
    "processing_loop", "processing_complete", "package_insert", "trash",
    "round_success", "round_failure",
)}
# Mixer gains, applied once to each cached sound. The loop is intentionally quiet.
CUE_VOLUMES = {
    "pickup": 0.55,
    "machine_insert": 0.55,
    "machine_remove": 0.55,
    "processing_start": 0.50,
    "processing_loop": 0.18,
    "processing_complete": 0.62,
    "package_insert": 0.55,
    "trash": 0.50,
    "round_success": 0.65,
    "round_failure": 0.60,
}
_AUDIO_ERRORS = (pygame.error, OSError, ValueError)


class AudioManager:
    """Preload optional sounds and reuse one processing channel per station.

    Call from the application thread. No printing, networking or gameplay
    callbacks occur. This manager never quits the shared Pygame mixer.
    """

    def __init__(
        self, root: Path | str = AUDIO_ROOT, *, enabled: bool = True,
        files: Mapping[str, str] | None = None,
    ) -> None:
        self.root = Path(root)
        self._files = dict(CUE_FILES)
        if files:
            self._files.update((cue, filename) for cue, filename in files.items() if cue in CUE_FILES)
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._loops: dict[str, pygame.mixer.Channel] = {}
        self._enabled = enabled
        if enabled:
            try:
                if pygame.mixer.get_init() is None:
                    pygame.mixer.init()
            except _AUDIO_ERRORS:
                self._enabled = False
        self.preload()

    @property
    def available(self) -> bool:
        """Whether this manager can currently use the mixer."""
        try:
            return self._enabled and pygame.mixer.get_init() is not None
        except _AUDIO_ERRORS:
            return False

    @property
    def loaded_cues(self) -> tuple[str, ...]:
        return tuple(sorted(self._sounds))

    def preload(self) -> tuple[str, ...]:
        """Cache existing files once; an explicit repeat can load newly added files."""
        if self.available:
            for cue, filename in self._files.items():
                if cue in self._sounds:
                    continue
                try:
                    path = self.root / filename
                    if path.is_file():
                        sound = pygame.mixer.Sound(str(path))
                        sound.set_volume(CUE_VOLUMES[cue])
                        self._sounds[cue] = sound
                except _AUDIO_ERRORS:
                    continue
        return self.loaded_cues

    def play(self, cue: str) -> bool:
        """Try one one-shot. Return False for unavailable cues/channels/audio."""
        if not self.available or cue == "processing_loop":
            return False
        sound = self._sounds.get(cue)
        if sound is None:
            return False
        try:
            channel = pygame.mixer.find_channel()  # Never steal an active loop.
            if channel is None:
                return False
            channel.play(sound)
            return True
        except _AUDIO_ERRORS:
            return False

    def start_processing(self, station_id: str) -> bool:
        """Start at most one loop per station; a repeated request is a no-op."""
        if not self.available:
            return False
        if station_id in self._loops:
            return True
        sound = self._sounds.get("processing_loop")
        if sound is None:
            return False
        try:
            channel = pygame.mixer.find_channel()
            if channel is None:
                return False
            channel.play(sound, loops=-1)
            self._loops[station_id] = channel
            return True
        except _AUDIO_ERRORS:
            return False

    def stop_processing(self, station_id: str) -> None:
        channel = self._loops.pop(station_id, None)
        if channel is not None:
            try:
                channel.stop()
            except _AUDIO_ERRORS:
                pass

    def stop_all_loops(self) -> None:
        for station_id in tuple(self._loops):
            self.stop_processing(station_id)

    def handle(self, events: Iterable[AudioEvent]) -> None:
        """Consume observer events in order; backend failures stay local here."""
        for event in events:
            if event.action == "play" and event.cue is not None:
                self.play(event.cue)
            elif event.action == "start_loop" and event.station_id is not None:
                self.start_processing(event.station_id)
            elif event.action == "stop_loop" and event.station_id is not None:
                self.stop_processing(event.station_id)
            elif event.action == "stop_all_loops":
                self.stop_all_loops()

    def close(self) -> None:
        """Stop owned loops and disable playback; leave the shared mixer alone."""
        self.stop_all_loops()
        self._sounds.clear()
        self._enabled = False
