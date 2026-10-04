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
            pygame.draw.circle(surface, theme.DARK_INK, (player.x, player.y), 23)
            pygame.draw.circle(surface, color, (player.x, player.y), 20)
            pygame.draw.rect(surface, theme.INK, (player.x - 10, player.y - 8, 6, 6))
            pygame.draw.rect(surface, theme.INK, (player.x + 4, player.y - 8, 6, 6))
            if player.held_item is not None:
                self._sample(surface, player.x + 22, player.y + 5)
        hud.draw_hud(surface, self.fonts, snapshot)

    def _room(self, surface) -> None:
        # Match the reference viewpoint: a quiet rear wall beneath the HUD,
        # followed by one continuous tiled floor and a narrow baseboard.
        room = pygame.Rect(theme.ROOM)
        floor_top = room.top + 108
        pygame.draw.rect(surface, theme.WALL, room)
        floor = pygame.Rect(room.left, floor_top, room.width, room.bottom - floor_top)
        tile = self.assets.sprite("floor_tile", theme.FLOOR_TILE_SIZE)
        previous_clip = surface.get_clip()
        surface.set_clip(previous_clip.clip(floor))
        for y in range(floor.top, floor.bottom, tile.get_height()):
            for x in range(floor.left, floor.right, tile.get_width()):
                surface.blit(tile, (x, y))
        surface.set_clip(previous_clip)
        pygame.draw.rect(surface, (91, 160, 166), (room.left, floor_top - 8, room.width, 8))
        pygame.draw.line(surface, (52, 112, 123), (room.left, floor_top), (room.right, floor_top), 3)
        pygame.draw.rect(surface, theme.BORDER, room, 2)

    def _station(self, surface, station: StationView) -> None:
        rect = pygame.Rect(station.x, station.y, station.width, station.height)
        visual_sizes = {
            "extraction": (120, 100),
            "cbc": (178, 112),
            "package": (136, 74),
            "microscope": (164, 112),
            "coagulation": (164, 112),
            "submit": (126, 132),
            "trash": (42, 140),
        }
        bottom_offsets = {
            "extraction": 10,
            # Keep the composite machine, table and label below the HUD.
            "cbc": 38,
            "package": 4,
            "microscope": 20,
            "coagulation": 20,
            "submit": 15,
            "trash": 10,
        }
        sprite_box = pygame.Rect((0, 0), visual_sizes.get(station.station_type, rect.size))
        sprite_box.midbottom = (rect.centerx, rect.bottom + bottom_offsets.get(station.station_type, 0))
        visual_offsets = {
            "sample_0": (10, 12),
            "sample_1": (32, 12),
            "package_0": (-15, 0),
            "package_1": (15, 0),
            "trash": (-14, 0),
            "CBC": (-42, -2),
        }
        sprite_box.move_ip(visual_offsets.get(station.station_id, (0, 0)))

        if station.station_type == "trash":
            self._trash_cluster(surface, sprite_box)
        elif station.station_type == "extraction":
            self._sample_bench(surface, sprite_box)
        elif station.station_type == "cbc":
            self._cbc_pair(surface, sprite_box)
        elif station.station_type == "coagulation":
            # Use the same workstation and scale as microscopy, then cover the
            # microscope itself with the round coagulation/centrifuge device.
            bench = self.assets.sprite("microscope", sprite_box.size)
            surface.blit(bench, sprite_box)
            machine = self.assets.sprite("coagulation_machine", (62, 92))
            surface.blit(machine, machine.get_rect(midbottom=(sprite_box.centerx, sprite_box.top + 80)))
        else:
            sprite_name = STATION_SPRITES.get(station.station_type, station.station_type)
            surface.blit(self.assets.sprite(sprite_name, sprite_box.size), sprite_box)
            if station.station_type == "package":
                package = self.assets.sprite("package_box", (34, 30))
                surface.blit(package, package.get_rect(midtop=(sprite_box.centerx, sprite_box.top + 5)))
            elif station.station_type == "microscope":
                slide = self.assets.sprite("blood_smear_slide", (18, 9))
                surface.blit(slide, slide.get_rect(center=(sprite_box.left + 46, sprite_box.top + 56)))

        self._station_label(surface, station, rect, sprite_box)
        if station.is_complete:
            hud.draw_checkmark(surface, (sprite_box.right - 5, sprite_box.top + 8))
        elif station.is_processing:
            progress = pygame.Rect(rect.centerx - 48, sprite_box.bottom + 2, 96, 8)
            hud.draw_progress(surface, progress, station.processing_progress)

    def _sample_bench(self, surface: pygame.Surface, sprite_box: pygame.Rect) -> None:
        """Assemble the reference extraction bench from its separate sprites."""
        surface.blit(self.assets.sprite("sample_bench", sprite_box.size), sprite_box)
        tabletop_y = sprite_box.top + 35
        rack = self.assets.sprite("sample_rack", (38, 40))
        surface.blit(rack, rack.get_rect(midbottom=(sprite_box.left + 29, tabletop_y + 5)))
        tube = self.assets.sprite("sample_tube", (7, 25))
        tube_left = pygame.transform.rotate(tube, 72)
        tube_right = pygame.transform.rotate(tube, 82)
        surface.blit(tube_left, tube_left.get_rect(center=(sprite_box.right - 36, tabletop_y - 2)))
        surface.blit(tube_right, tube_right.get_rect(center=(sprite_box.right - 22, tabletop_y + 5)))

    def _cbc_pair(self, surface: pygame.Surface, sprite_box: pygame.Rect) -> None:
        """Draw the two rear-wall analyzers side by side as in the reference."""
        baseline = sprite_box.bottom
        printer = self.assets.sprite("lab_printer", (86, 98))
        cart = self.assets.sprite("cbc_machine", (80, 88))
        surface.blit(printer, printer.get_rect(bottomleft=(sprite_box.left + 4, baseline)))
        surface.blit(cart, cart.get_rect(bottomright=(sprite_box.right - 2, baseline)))

    def _station_label(
        self,
        surface: pygame.Surface,
        station: StationView,
        logical_rect: pygame.Rect,
        sprite_box: pygame.Rect,
    ) -> None:
        lines = tuple(label.upper() for label in station.label)
        widths = [self.fonts.small.size(line)[0] for line in lines]
        width = min(158, max(72, max(widths, default=60) + 18))
        height = 15 + max(0, len(lines) - 1) * 13
        label_rect = pygame.Rect(0, 0, width, height)
        if station.station_id in ("sample_0", "sample_1", "CBC"):
            label_gap = 2
        elif station.station_id == "COAG":
            label_gap = 20
        else:
            label_gap = 8
        label_rect.midbottom = (sprite_box.centerx, sprite_box.top - label_gap)
        theme.cut_panel(surface, label_rect, theme.PANEL, theme.BORDER, cut=4, shadow=False)
        for row, label in enumerate(lines):
            theme.text(
                surface,
                self.fonts.small,
                label,
                (label_rect.centerx, label_rect.top + 8 + row * 13),
                theme.INK,
                center=True,
            )

    def _trash_cluster(self, surface: pygame.Surface, sprite_box: pygame.Rect) -> None:
        names = ("trash_yellow", "trash_biohazard", "trash_dark", "trash_red", "trash_green", "trash_blue")
        bin_size = (26, 43)
        for index, name in enumerate(names):
            image = self.assets.sprite(name, bin_size)
            position = (
                sprite_box.centerx - bin_size[0] // 2,
                sprite_box.top + index * 20,
            )
            surface.blit(image, position)

    def _sample(self, surface, x: int, y: int) -> None:
        image = self.assets.sprite("sample_tube", theme.SAMPLE_SIZE)
        surface.blit(image, image.get_rect(center=(x, y)))

    @staticmethod
    def menu_buttons() -> tuple[pygame.Rect, ...]:
        return tuple(pygame.Rect((theme.WIDTH - 280) // 2, 270 + index * 68, 280, 52) for index in range(3))

    def draw_menu(self, surface, selected: int = 0) -> None:
        surface.fill(theme.BACKGROUND)
        title_panel = pygame.Rect(272, 146, 416, 82)
        theme.cut_panel(surface, title_panel, theme.PANEL, theme.BORDER, cut=12)
        theme.text(surface, self.fonts.title, "LAB PANIC", title_panel.center, theme.INK, center=True)
        for index, (label, rect) in enumerate(zip(("HOST", "JOIN", "QUIT"), self.menu_buttons())):
            active = index == selected
            theme.cut_panel(
                surface,
                rect,
                theme.TEAL if active else theme.PANEL,
                theme.INK if active else theme.BORDER,
                cut=8,
            )
            theme.text(surface, self.fonts.heading, label, rect.center, theme.INK, center=True)

    def draw_result(self, surface, *, success: bool) -> None:
        surface.fill(theme.BACKGROUND)
        panel = pygame.Rect(190, 242, 580, 156)
        theme.cut_panel(surface, panel, theme.PANEL, theme.GREEN if success else theme.RED, cut=14)
        hud.draw_message(surface, self.fonts, "LAB COMPLETE" if success else "LAB FAILED", theme.INK)
