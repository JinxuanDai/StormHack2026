"""Read-only timer, patient cards, progress and presentation messages."""

import math

import pygame

from . import theme
from .views import RoundView


def draw_progress(surface, rect: pygame.Rect, progress: float) -> None:
    fraction = max(0.0, min(1.0, progress)) if math.isfinite(progress) else 0.0
    pygame.draw.rect(surface, theme.TEAL_LIGHT, rect, border_radius=4)
    if fraction > 0:
        fill = rect.copy()
        fill.width = max(1, round(rect.width * fraction))
        pygame.draw.rect(surface, theme.TEAL, fill, border_radius=4)


def draw_checkmark(surface, center: tuple[int, int]) -> None:
    x, y = center
    pygame.draw.circle(surface, theme.GREEN, center, 13)
    pygame.draw.lines(surface, theme.PANEL, False, [(x - 6, y), (x - 1, y + 5), (x + 7, y - 5)], 3)


def draw_hud(surface, fonts: theme.Fonts, snapshot: RoundView) -> None:
    pygame.draw.rect(surface, theme.PANEL, (0, 0, theme.WIDTH, theme.HUD_HEIGHT))
    seconds = max(0, int(snapshot.time_remaining))
    theme.text(surface, fonts.small, "TIME", (20, 29), theme.MUTED)
    theme.text(surface, fonts.timer, f"{seconds // 60}:{seconds % 60:02d}", (16, 52), theme.TEAL)
    for index, patient in enumerate(snapshot.patients[:2]):
        rect = pygame.Rect(150 + index * 200, 12, 190, 96)
        pygame.draw.rect(surface, theme.BACKGROUND, rect, border_radius=10)
        pygame.draw.rect(surface, theme.BORDER, rect, width=1, border_radius=10)
        theme.text(surface, fonts.heading, patient.patient_id, (rect.x + 14, rect.y + 10))
        patient_seconds = max(0, math.ceil(patient.time_remaining))
        timer_color = theme.RED if patient_seconds <= 10 else theme.TEAL
        theme.text(surface, fonts.heading, f"{patient_seconds}s", (rect.right - 48, rect.y + 10), timer_color)
        for row, task in enumerate(patient.tasks):
            theme.text(surface, fonts.small, task, (rect.x + 14, rect.y + 36 + row * 18), theme.MUTED)
    theme.text(surface, fonts.small, "SCORE", (760, 27), theme.MUTED)
    theme.text(surface, fonts.heading, str(snapshot.score), (760, 49), theme.TEAL)
    theme.text(surface, fonts.small, f"BEST {snapshot.high_score}", (760, 78), theme.MUTED)


def draw_message(surface, fonts: theme.Fonts, message: str, color=theme.INK) -> None:
    theme.text(surface, fonts.title, message, (theme.WIDTH // 2, theme.HEIGHT // 2), color, center=True)
