"""Read-only timer, patient cards, progress and presentation messages."""

import math

import pygame

from . import theme
from .views import RoundView


def draw_progress(surface, rect: pygame.Rect, progress: float) -> None:
    fraction = max(0.0, min(1.0, progress)) if math.isfinite(progress) else 0.0
    pygame.draw.rect(surface, theme.DARK_INK, rect.inflate(4, 4))
    pygame.draw.rect(surface, theme.TEAL_LIGHT, rect)
    if fraction > 0:
        fill = rect.copy()
        fill.width = max(1, round(rect.width * fraction))
        pygame.draw.rect(surface, theme.GREEN, fill)


def draw_checkmark(surface, center: tuple[int, int]) -> None:
    x, y = center
    rect = pygame.Rect(0, 0, 24, 24)
    rect.center = center
    theme.cut_panel(surface, rect, theme.GREEN, theme.INK, cut=4, shadow=False)
    pygame.draw.lines(surface, theme.INK, False, [(x - 6, y), (x - 1, y + 5), (x + 7, y - 5)], 3)


def draw_hud(surface, fonts: theme.Fonts, snapshot: RoundView) -> None:
    pygame.draw.rect(surface, theme.BACKGROUND, (0, 0, theme.WIDTH, theme.HUD_HEIGHT))
    pygame.draw.rect(surface, (99, 163, 168), (0, theme.HUD_HEIGHT - 5, theme.WIDTH, 5))

    seconds = max(0, int(snapshot.time_remaining))
    timer_rect = pygame.Rect(14, 12, 122, 94)
    theme.cut_panel(surface, timer_rect, theme.PANEL, theme.BORDER, cut=9)
    theme.text(surface, fonts.small, "SHIFT TIME", (timer_rect.centerx, timer_rect.top + 19), theme.MUTED, center=True)
    theme.text(
        surface,
        fonts.timer,
        f"{seconds // 60}:{seconds % 60:02d}",
        (timer_rect.centerx, timer_rect.centery + 14),
        theme.INK,
        center=True,
    )

    for index, patient in enumerate(snapshot.patients[:2]):
        rect = pygame.Rect(148 + index * 240, 12, 226, 94)
        theme.cut_panel(surface, rect, theme.PANEL, theme.BORDER, cut=9)
        theme.text(surface, fonts.heading, patient.patient_id, (rect.x + 12, rect.y + 13), theme.INK)
        patient_seconds = max(0, math.ceil(patient.time_remaining))
        timer_color = theme.RED if patient_seconds <= 10 else theme.YELLOW
        theme.text(surface, fonts.heading, f"{patient_seconds}s", (rect.right - 28, rect.y + 19), timer_color, center=True)
        pygame.draw.line(surface, theme.PANEL_LIGHT, (rect.x + 10, rect.y + 36), (rect.right - 10, rect.y + 36), 2)
        for row, task in enumerate(patient.tasks):
            completed = task in patient.completed_tasks
            task_rect = theme.text(
                surface,
                fonts.small,
                task.upper(),
                (rect.x + 12, rect.y + 44 + row * 14),
                theme.MUTED if not completed else theme.GREEN,
            )
            if completed:
                pygame.draw.line(
                    surface,
                    theme.GREEN,
                    (task_rect.left - 2, task_rect.centery),
                    (task_rect.right + 2, task_rect.centery),
                    2,
                )

    score_rect = pygame.Rect(628, 12, 318, 94)
    theme.cut_panel(surface, score_rect, theme.PANEL, theme.BORDER, cut=9)
    theme.text(surface, fonts.small, "TEAM SCORE", (score_rect.x + 16, score_rect.y + 17), theme.MUTED)
    theme.text(surface, fonts.heading, str(snapshot.score), (score_rect.x + 16, score_rect.y + 43), theme.INK)
    pygame.draw.line(surface, theme.PANEL_LIGHT, (score_rect.centerx, score_rect.y + 12), (score_rect.centerx, score_rect.bottom - 12), 2)
    theme.text(surface, fonts.small, "LAB BEST", (score_rect.centerx + 18, score_rect.y + 17), theme.MUTED)
    theme.text(surface, fonts.heading, str(snapshot.high_score), (score_rect.centerx + 18, score_rect.y + 43), theme.YELLOW)


def draw_message(surface, fonts: theme.Fonts, message: str, color=theme.INK) -> None:
    theme.text(surface, fonts.title, message, (theme.WIDTH // 2, theme.HEIGHT // 2), color, center=True)
