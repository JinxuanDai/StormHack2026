"""Pure presentation of supplied snapshots. No simulation or transport imports."""

import pygame

from . import hud, theme
from .assets import AssetStore
from .views import RoundView, StationView


class Renderer:
    def __init__(self, assets: AssetStore | None = None) -> None:
        self.assets = assets if assets is not None else AssetStore()
        self.fonts = theme.Fonts()

    def draw_gameplay(self, surface: pygame.Surface, snapshot: RoundView) -> None:
        surface.fill(theme.BACKGROUND)
        self._room(surface)
        for station in snapshot.stations:
            self._station(surface, station)
        for sample in snapshot.samples:
            self._sample(surface, sample.x, sample.y)
        for index, player in enumerate(snapshot.players):
            color = theme.PLAYER_COLORS[index % len(theme.PLAYER_COLORS)]
            pygame.draw.ellipse(surface, theme.SHADOW, (player.x - 22, player.y + 14, 44, 16))
            pygame.draw.circle(surface, theme.INK, (player.x, player.y), 23)
            pygame.draw.circle(surface, color, (player.x, player.y), 20)
            pygame.draw.circle(surface, theme.PANEL, (player.x - 6, player.y - 6), 5)
            if player.held_item is not None:
                self._sample(surface, player.x + 22, player.y + 5)
        hud.draw_hud(surface, self.fonts, snapshot)

    def _room(self, surface) -> None:
        room = pygame.Rect(theme.ROOM)
        pygame.draw.rect(surface, theme.BORDER, room, border_radius=12)
        floor = room.inflate(-20, -20)
        pygame.draw.rect(surface, theme.FLOOR, floor, border_radius=5)
        for x in range(floor.left + 40, floor.right, 40):
            pygame.draw.line(surface, theme.GRID, (x, floor.top), (x, floor.bottom))
        for y in range(floor.top + 40, floor.bottom, 40):
            pygame.draw.line(surface, theme.GRID, (floor.left, y), (floor.right, y))

    def _station(self, surface, station: StationView) -> None:
        rect = pygame.Rect(station.x, station.y, station.width, 128)
        pygame.draw.rect(surface, theme.SHADOW, rect.move(0, 5), border_radius=10)
        pygame.draw.rect(surface, theme.PANEL, rect, border_radius=10)
        pygame.draw.rect(surface, theme.BORDER, rect, width=1, border_radius=10)
        for row, label in enumerate(station.label):
            theme.text(surface, self.fonts.body, label, (rect.centerx, rect.top + 20 + row * 22), center=True)
        icon_y = rect.bottom - 67
        surface.blit(self.assets.sprite(station.station_type, (58, 48)), (rect.centerx - 29, icon_y))
        if station.is_complete:
            hud.draw_checkmark(surface, (rect.right - 23, rect.bottom - 35))
        elif station.is_processing:
            hud.draw_progress(surface, pygame.Rect(rect.x + 16, rect.bottom - 12, rect.width - 32, 6), station.processing_progress)

    @staticmethod
    def _sample(surface, x: int, y: int) -> None:
        pygame.draw.rect(surface, theme.INK, (x - 6, y - 13, 12, 27), border_radius=4)
        pygame.draw.rect(surface, theme.PANEL, (x - 4, y - 10, 8, 20), border_radius=3)
        pygame.draw.rect(surface, theme.RED, (x - 3, y, 6, 9), border_radius=2)
        pygame.draw.rect(surface, theme.TEAL, (x - 7, y - 15, 14, 6), border_radius=2)

    @staticmethod
    def menu_buttons() -> tuple[pygame.Rect, ...]:
        return tuple(pygame.Rect(420, 345 + index * 76, 280, 56) for index in range(3))

    def draw_menu(self, surface, selected: int = 0) -> None:
        surface.fill(theme.BACKGROUND)
        theme.text(surface, self.fonts.title, "LAB PANIC", (theme.WIDTH // 2, 245), theme.TEAL, center=True)
        for index, (label, rect) in enumerate(zip(("HOST", "JOIN", "QUIT"), self.menu_buttons())):
            active = index == selected
            pygame.draw.rect(surface, theme.TEAL if active else theme.PANEL, rect, border_radius=8)
            pygame.draw.rect(surface, theme.TEAL if active else theme.BORDER, rect, width=2, border_radius=8)
            theme.text(surface, self.fonts.heading, label, rect.center, theme.PANEL if active else theme.INK, center=True)

    def draw_result(self, surface, *, success: bool) -> None:
        surface.fill(theme.BACKGROUND)
        hud.draw_message(surface, self.fonts, "LAB COMPLETE" if success else "LAB FAILED", theme.GREEN if success else theme.RED)
