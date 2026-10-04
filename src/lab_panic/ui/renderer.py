"""Pure presentation of supplied snapshots. No simulation or transport imports."""

import pygame

from . import hud, theme
from .assets import AssetStore, STATION_SPRITES
from .views import RoundView, StationView


class Renderer:
    def __init__(self, assets: AssetStore | None = None) -> None:
        self.assets = assets if assets is not None else AssetStore()
        self.fonts = theme.Fonts()
        self._player_positions: dict[str, tuple[int, int]] = {}
        self._player_facing: dict[str, str] = {}
        self._player_motion_until: dict[str, int] = {}

    def draw_gameplay(self, surface: pygame.Surface, snapshot: RoundView) -> None:
        surface.fill(theme.BACKGROUND)
        self._room(surface)
        station_boxes = [(station, self._station(surface, station))
                         for station in snapshot.stations]
        for sample in snapshot.samples:
            self._sample(surface, sample.x, sample.y)
        for index, player in enumerate(snapshot.players):
            self._player(surface, player, index)
            if player.held_item is not None:
                self._sample(surface, player.x + 22, player.y + 5)
        # Labels float above characters; they never participate in collision.
        for station, sprite_box in station_boxes:
            self._station_label(surface, station, sprite_box)
        hud.draw_hud(surface, self.fonts, snapshot)

    def _player(self, surface: pygame.Surface, player, index: int) -> None:
        previous = self._player_positions.get(player.player_id, (player.x, player.y))
        dx = player.x - previous[0]
        dy = player.y - previous[1]
        facing = self._player_facing.get(player.player_id, "down")
        if dx or dy:
            if abs(dx) > abs(dy):
                facing = "right" if dx > 0 else "left"
            else:
                facing = "down" if dy > 0 else "up"
            self._player_motion_until[player.player_id] = pygame.time.get_ticks() + 120
        now = pygame.time.get_ticks()
        moving = now < self._player_motion_until.get(player.player_id, 0)
        frame = (now // 140) % 3 if moving else 1
        sprite = self.assets.character_frame(index, facing, frame)
        sprite_rect = sprite.get_rect(midbottom=(player.x, player.y + 22))
        surface.blit(sprite, sprite_rect)
        self._player_positions[player.player_id] = (player.x, player.y)
        self._player_facing[player.player_id] = facing

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

    def _station(self, surface, station: StationView) -> pygame.Rect:
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

        if station.is_complete:
            hud.draw_checkmark(surface, (sprite_box.right - 5, sprite_box.top + 8))
        elif station.is_processing:
            progress = pygame.Rect(rect.centerx - 48, sprite_box.bottom + 2, 96, 8)
            hud.draw_progress(surface, progress, station.processing_progress)
        return sprite_box

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
        # These stable rectangles are both the keyboard layout and mouse
        # hitboxes. The selected button grows around its center when drawn.
        return tuple(
            pygame.Rect((theme.WIDTH - 214) // 2, 306 + index * 57, 214, 42)
            for index in range(3)
        )

    def _menu_background(self, surface: pygame.Surface) -> None:
        """Build the approved pixel-lab menu without touching game state."""
        wall_bottom = 238
        surface.fill((174, 216, 218))
        pygame.draw.rect(surface, (188, 222, 222), (0, 0, theme.WIDTH, wall_bottom))

        floor = pygame.Rect(0, wall_bottom, theme.WIDTH, theme.HEIGHT - wall_bottom)
        tile = self.assets.sprite("floor_tile", theme.FLOOR_TILE_SIZE)
        old_clip = surface.get_clip()
        surface.set_clip(old_clip.clip(floor))
        for y in range(floor.top, floor.bottom, tile.get_height()):
            for x in range(floor.left, floor.right, tile.get_width()):
                surface.blit(tile, (x, y))
        surface.set_clip(old_clip)
        pygame.draw.rect(surface, (91, 160, 166), (0, wall_bottom - 7, theme.WIDTH, 7))
        pygame.draw.line(surface, (52, 112, 123), (0, wall_bottom), (theme.WIDTH, wall_bottom), 3)

        # Matching compact windows frame the title at the same height.
        for window in (pygame.Rect(94, 36, 112, 64), pygame.Rect(754, 36, 112, 64)):
            pygame.draw.rect(surface, (120, 174, 181), window.inflate(8, 8))
            pygame.draw.rect(surface, (65, 92, 108), window.inflate(4, 4))
            pygame.draw.rect(surface, (151, 204, 218), window)
            pygame.draw.polygon(
                surface,
                (207, 235, 239),
                [(window.left + 8, window.top), (window.left + 28, window.top),
                 (window.left + 8, window.top + 28)],
            )
            pygame.draw.line(surface, (118, 171, 190), window.midtop, window.midbottom, 2)

        # Reuse gameplay's laboratory sprites so the menu matches the room.
        machines = (
            ("sample_bench", (18, 145, 126, 96)),
            ("cbc_machine", (150, 142, 92, 99)),
            ("lab_printer", (247, 139, 89, 102)),
            ("microscope", (624, 143, 100, 98)),
            ("coagulation_machine", (732, 139, 78, 102)),
            ("submit_terminal", (816, 132, 126, 109)),
        )
        for name, rect in machines:
            surface.blit(self.assets.sprite(name, rect[2:]), rect[:2])

        # Foreground corners frame the composition without blocking controls.
        bench = self.assets.sprite("sample_bench", (180, 142))
        surface.blit(bench, (-44, 530))
        surface.blit(pygame.transform.flip(bench, True, False), (824, 530))

    def _menu_doctor(self, surface: pygame.Surface, player_index: int, center_x: int) -> None:
        sprite = self.assets.character_frame(player_index, "down", 1, (92, 148))
        rect = sprite.get_rect(midbottom=(center_x, 493))
        # This muted grounding shadow is intentionally not a selection halo.
        pygame.draw.ellipse(surface, (123, 159, 166), (rect.centerx - 35, 484, 70, 10))
        surface.blit(sprite, rect)

    def draw_menu(self, surface, selected: int = 0) -> None:
        self._menu_background(surface)

        # Raise the title; lower the doctors and three-button group together.
        title_panel = pygame.Rect(278, 14, 404, 72)
        theme.cut_panel(surface, title_panel, theme.PANEL, theme.BORDER, cut=12)
        theme.text(surface, self.fonts.title, "LAB PANIC", title_panel.center, theme.INK, center=True)

        self._menu_doctor(surface, 0, 226)
        self._menu_doctor(surface, 1, theme.WIDTH - 226)
        for index, (label, rect) in enumerate(zip(("HOST", "JOIN", "QUIT"), self.menu_buttons())):
            active = index == selected
            draw_rect = rect.inflate(16, 8) if active else rect
            theme.cut_panel(
                surface,
                draw_rect,
                theme.TEAL if active else theme.PANEL,
                theme.INK if active else theme.BORDER,
                cut=8,
            )
            theme.text(surface, self.fonts.heading, label, draw_rect.center, theme.INK, center=True)

    def draw_result(self, surface, *, success: bool) -> None:
        surface.fill(theme.BACKGROUND)
        panel = pygame.Rect(190, 242, 580, 156)
        theme.cut_panel(surface, panel, theme.PANEL, theme.GREEN if success else theme.RED, cut=14)
        hud.draw_message(surface, self.fonts, "LAB COMPLETE" if success else "LAB FAILED", theme.INK)
