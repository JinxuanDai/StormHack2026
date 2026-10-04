"""Standalone SFX preview: python -m lab_panic.ui.audio_demo.

Keys 1 through 0 audition cues; 5 toggles the processing loop; Escape quits.
No gameplay state, observer, networking, or main.py is invoked by this demo.
"""

import pygame

from . import theme
from .audio import AudioManager, CUE_VOLUMES


BINDINGS = (
    (pygame.K_1, "1", "pickup"),
    (pygame.K_2, "2", "machine_insert"),
    (pygame.K_3, "3", "machine_remove"),
    (pygame.K_4, "4", "processing_start"),
    (pygame.K_5, "5", "processing_loop"),
    (pygame.K_6, "6", "processing_complete"),
    (pygame.K_7, "7", "package_insert"),
    (pygame.K_8, "8", "trash"),
    (pygame.K_9, "9", "round_success"),
    (pygame.K_0, "0", "round_failure"),
)
KEY_CUES = {key: cue for key, _, cue in BINDINGS}
STATION_ID = "preview"
WINDOW_SIZE = (740, 650)


class SoundPreview:
    """Small keyboard controller shared by the window and standalone checks."""

    def __init__(self, audio: AudioManager) -> None:
        self.audio = audio
        self.loop_on = False
        self.last_action = "Press a number key to preview a sound."

    def press(self, key: int) -> bool:
        """Return whether a mapped cue played/toggled; failed playback stays OFF."""
        cue = KEY_CUES.get(key)
        if cue is None:
            return False
        if cue == "processing_loop":
            if self.loop_on:
                self.audio.stop_processing(STATION_ID)
                self.loop_on = False
                self.last_action = "processing_loop: OFF"
                return True
            self.loop_on = self.audio.start_processing(STATION_ID)
            self.last_action = "processing_loop: ON" if self.loop_on else "processing_loop: unavailable"
            return self.loop_on
        played = self.audio.play(cue)
        self.last_action = f"{cue}: playing" if played else f"{cue}: unavailable or all channels busy"
        return played

    def draw(self, screen: pygame.Surface, fonts: theme.Fonts) -> None:
        screen.fill(theme.BACKGROUND)
        theme.text(screen, fonts.heading, "LAB PANIC / SOUND PREVIEW", (28, 24), theme.TEAL)
        theme.text(screen, fonts.small, "Temporary development SFX  |  Escape: quit", (28, 58), theme.MUTED)
        status = f"Mixer ready  /  {len(self.audio.loaded_cues)} of {len(BINDINGS)} cues loaded"
        if not self.audio.available:
            status = "Audio unavailable: mixer/device could not initialize."
        theme.text(screen, fonts.small, status, (28, 86), theme.MUTED)
        theme.text(screen, fonts.small, "KEY", (38, 122), theme.MUTED)
        theme.text(screen, fonts.small, "CUE", (106, 122), theme.MUTED)
        theme.text(screen, fonts.small, "GAIN", (486, 122), theme.MUTED)
        theme.text(screen, fonts.small, "FILE", (584, 122), theme.MUTED)
        for index, (_, label, cue) in enumerate(BINDINGS):
            y = 150 + index * 38
            rect = pygame.Rect(28, y - 4, 684, 32)
            active = cue == "processing_loop" and self.loop_on
            pygame.draw.rect(screen, theme.TEAL_LIGHT if active else theme.PANEL, rect, border_radius=4)
            theme.text(screen, fonts.body, label, (40, y))
            theme.text(screen, fonts.body, cue, (106, y))
            theme.text(screen, fonts.small, f"{CUE_VOLUMES[cue]:.0%}", (486, y + 2), theme.MUTED)
            loaded = cue in self.audio.loaded_cues
            theme.text(screen, fonts.small, "LOADED" if loaded else "MISSING", (584, y + 2),
                       theme.GREEN if loaded else theme.RED)
        theme.text(screen, fonts.heading, f"Processing loop: {'ON' if self.loop_on else 'OFF'}  (5 toggles)",
                   (28, 546), theme.TEAL if self.loop_on else theme.MUTED)
        theme.text(screen, fonts.small, self.last_action, (28, 582))
        theme.text(screen, fonts.small, "Standalone preview only. Live game audio is not connected.",
                   (28, 618), theme.MUTED)


def main() -> None:
    # Initialize video/fonts independently so a missing audio device cannot
    # prevent the preview window from showing its unavailable status.
    pygame.display.init()
    pygame.font.init()
    audio = AudioManager()
    try:
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("Lab Panic | Sound Preview")
        pygame.key.set_repeat()  # Holding 5 must not rapidly toggle the loop.
        fonts = theme.Fonts()
        preview = SoundPreview(audio)
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN:
                    preview.press(event.key)
            if running:
                preview.draw(screen, fonts)
                pygame.display.flip()
                clock.tick(60)
    finally:
        audio.close()
        pygame.quit()


if __name__ == "__main__":
    main()
