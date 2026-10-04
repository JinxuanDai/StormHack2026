"""Standalone presentation demo: python -m lab_panic.ui.demo.

1: main menu; 2: gameplay; 3: success; 4: failure; Escape: quit.
Menu: Up/Down and Enter, or click HOST/JOIN/QUIT. HOST and JOIN both open
identical mock gameplay; neither starts networking. Players, timer (3:00),
processing bar and completion check are static visual examples.
Use --smoke-test to render all four screens headlessly and exit.
"""

import argparse
import os

import pygame

from . import theme
from .renderer import Renderer
from .views import PatientView, PlayerView, RoundView, SampleView, StationView


MOCK_ROUND = RoundView(
    time_remaining=180,
    patients=(
        PatientView("P-001", ("CBC", "Blood Smear")),
        PatientView("P-002", ("Coagulation",)),
        PatientView("P-003", ("CBC", "Coagulation")),
        PatientView("P-004", ("CBC", "Blood Smear", "Coagulation")),
    ),
    stations=(
        StationView("extraction", "extraction", ("Sample Extraction",), 184, 150, width=190),
        StationView("cbc", "cbc", ("CBC",), 586, 150, width=190, is_processing=True, processing_progress=0.58),
        StationView("trash", "trash", ("Trash",), 36, 304, width=134),
        StationView("submit", "submit", ("Submit",), 790, 304, width=134),
        StationView("package", "package", ("Package",), 385, 304, width=190),
        StationView("smear", "microscope", ("Blood Smear", "+ Microscope"), 184, 458, width=190),
        StationView("coagulation", "coagulation", ("Coagulation Test",), 586, 458, width=190, is_complete=True),
    ),
    players=(PlayerView("one", 318, 354, "sample-one"), PlayerView("two", 655, 399)),
    samples=(SampleView("sample-two", 451, 374),),
)

SCREENS = ("menu", "gameplay", "success", "failure")
SCREEN_KEYS = {pygame.K_1: "menu", pygame.K_2: "gameplay", pygame.K_3: "success", pygame.K_4: "failure"}


def draw_screen(renderer: Renderer, surface, screen: str, selected: int = 0) -> None:
    if screen == "menu":
        renderer.draw_menu(surface, selected)
    elif screen == "gameplay":
        renderer.draw_gameplay(surface, MOCK_ROUND)
    else:
        renderer.draw_result(surface, success=screen == "success")
    # Demo-only inspection controls; not part of the gameplay HUD.
    hint = "1 Menu   2 Gameplay   3 Success   4 Failure   Esc Quit"
    if screen == "menu":
        hint += "   |   Up/Down + Enter or click"
    theme.text(surface, renderer.fonts.small, hint, (theme.WIDTH // 2, theme.HEIGHT - 15), theme.MUTED, center=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke-test", action="store_true", help="render all four mock screens headlessly, then exit")
    args = parser.parse_args()
    if args.smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    try:
        surface = pygame.display.set_mode((theme.WIDTH, theme.HEIGHT))
        pygame.display.set_caption("Lab Panic | UI demo")
        renderer = Renderer()
        clock = pygame.time.Clock()
        screen, selected, frames = "menu", 0, 0
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in SCREEN_KEYS:
                        screen = SCREEN_KEYS[event.key]
                    elif screen == "menu":
                        if event.key in (pygame.K_UP, pygame.K_DOWN):
                            selected = (selected + (1 if event.key == pygame.K_DOWN else -1)) % 3
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if selected == 2:
                                running = False
                            else:
                                screen = "gameplay"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and screen == "menu":
                    for index, rect in enumerate(renderer.menu_buttons()):
                        if rect.collidepoint(event.pos):
                            selected = index
                            if index == 2:
                                running = False
                            else:
                                screen = "gameplay"
                            break
            if not running:
                break
            if args.smoke_test:
                screen = SCREENS[frames]
            draw_screen(renderer, surface, screen, selected)
            pygame.display.flip()
            frames += 1
            if args.smoke_test and frames == len(SCREENS):
                running = False
            clock.tick(theme.FPS)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
