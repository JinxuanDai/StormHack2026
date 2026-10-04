"""Pure presentation of supplied snapshots. No simulation or transport imports."""

import pygame

from . import hud, theme
from .assets import AssetStore, STATION_SPRITES
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
        pygame.draw.rect(surface, theme.BORDER, room, border_radius=8)
        floor = room.inflate(-16, -16)
        tile = self.assets.sprite("floor_tile", theme.FLOOR_TILE_SIZE)
        previous_clip = surface.get_clip()
        surface.set_clip(previous_clip.clip(floor))
        for y in range(floor.top, floor.bottom, tile.get_height()):
            for x in range(floor.left, floor.right, tile.get_width()):
                surface.blit(tile, (x, y))
        surface.set_clip(previous_clip)

    def _station(self, surface, station: StationView) -> None:
        rect = pygame.Rect(station.x, station.y, station.width, station.height)
        label_rect = pygame.Rect(rect.x, rect.y, rect.width, 24 if len(station.label) == 1 else 44)
        pygame.draw.rect(surface, theme.PANEL, label_rect, border_radius=5)
        for row, label in enumerate(station.label):
            theme.text(surface, self.fonts.body, label, (rect.centerx, rect.top + 12 + row * 20), center=True)
        sprite_box = pygame.Rect(0, 0, min(112, rect.width - 12), min(84, max(16, rect.height - label_rect.height - 12)))
        sprite_box.midbottom = (rect.centerx, rect.bottom - 10)
        pygame.draw.ellipse(surface, theme.SHADOW, (rect.centerx - 46, rect.bottom - 22, 92, 16))
        sprite_name = STATION_SPRITES.get(station.station_type, station.station_type)
        surface.blit(self.assets.sprite(sprite_name, sprite_box.size), sprite_box)
        if station.is_complete:
            hud.draw_checkmark(surface, (rect.centerx + 58, rect.bottom - 24))
        elif station.is_processing:
            hud.draw_progress(surface, pygame.Rect(rect.centerx - 44, rect.bottom - 6, 88, 6), station.processing_progress)

    def _sample(self, surface, x: int, y: int) -> None:
        image = self.assets.sprite("sample_tube", theme.SAMPLE_SIZE)
        surface.blit(image, image.get_rect(center=(x, y)))

    @staticmethod
    def menu_buttons() -> tuple[pygame.Rect, ...]:
        return tuple(pygame.Rect((theme.WIDTH - 280) // 2, 270 + index * 68, 280, 52) for index in range(3))

    def draw_menu(self, surface, selected: int = 0) -> None:
        surface.fill(theme.BACKGROUND)
        theme.text(surface, self.fonts.title, "LAB PANIC", (theme.WIDTH // 2, 190), theme.TEAL, center=True)
        for index, (label, rect) in enumerate(zip(("HOST", "JOIN", "QUIT"), self.menu_buttons())):
            active = index == selected
            pygame.draw.rect(surface, theme.TEAL if active else theme.PANEL, rect, border_radius=8)
            pygame.draw.rect(surface, theme.TEAL if active else theme.BORDER, rect, width=2, border_radius=8)
            theme.text(surface, self.fonts.heading, label, rect.center, theme.PANEL if active else theme.INK, center=True)

    def draw_result(self, surface, *, success: bool) -> None:
        surface.fill(theme.BACKGROUND)
        hud.draw_message(surface, self.fonts, "LAB COMPLETE" if success else "LAB FAILED", theme.GREEN if success else theme.RED)
