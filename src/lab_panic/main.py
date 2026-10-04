"""Hematology Lab Rush: a two-player Pygame LAN prototype."""

from __future__ import annotations

import argparse
import json
import math
import os
import queue
import random
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pygame


WIDTH, HEIGHT = 1280, 720
HUD_HEIGHT = 128
FPS = 60
PORT = 50505
GAME_SECONDS = 180.0
PLAYER_SPEED = 250.0
INTERACT_DISTANCE = 54
SNAPSHOT_RATE = 1.0 / 30.0

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = REPO_ROOT / "assets"

BG = (225, 233, 232)
FLOOR_A = (205, 218, 216)
FLOOR_B = (194, 210, 208)
NAVY = (27, 45, 60)
WHITE = (250, 251, 249)
BLACK = (23, 29, 33)
RED = (203, 70, 68)
GREEN = (64, 155, 104)
BLUE = (50, 128, 190)
ORANGE = (225, 137, 60)
YELLOW = (236, 198, 67)
PURPLE = (143, 92, 181)
GRAY = (104, 117, 123)

TESTS = ("CBC", "COAG", "SMEAR")
TEST_LABEL = {"CBC": "CBC", "COAG": "Coagulation", "SMEAR": "Blood Smear + Microscope"}
TEST_SECONDS = {"CBC": 2.0, "COAG": 4.0, "SMEAR": 3.0}
TEST_COLOR = {"CBC": WHITE, "COAG": YELLOW, "SMEAR": PURPLE}

ZONES = {
    "sample": pygame.Rect(94, 158, 238, 92),
    "CBC": pygame.Rect(948, 158, 238, 92),
    "trash": pygame.Rect(28, 348, 130, 142),
    "submit": pygame.Rect(1122, 348, 130, 142),
    "package": pygame.Rect(470, 322, 340, 126),
    "SMEAR": pygame.Rect(102, 574, 268, 104),
    "COAG": pygame.Rect(910, 574, 268, 104),
}


def send_json(sock: socket.socket, payload: dict[str, Any]) -> None:
    sock.sendall((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def local_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return str(probe.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        probe.close()


class HostNetwork:
    def __init__(self, port: int = PORT) -> None:
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", port))
        self.server.listen(1)
        self.server.settimeout(0.5)
        self.client: socket.socket | None = None
        self.client_lock = threading.Lock()
        self.connected = False
        self.running = True
        self.remote_input = {"x": 0, "y": 0}
        self.actions: queue.SimpleQueue[int] = queue.SimpleQueue()
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()

    def _accept_loop(self) -> None:
        while self.running:
            try:
                client, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with self.client_lock:
                if self.client is not None:
                    client.close()
                    continue
                self.client = client
                self.connected = True
            client.settimeout(0.5)
            try:
                self._read_client(client)
            finally:
                with self.client_lock:
                    if self.client is client:
                        self.client = None
                        self.connected = False
                        self.remote_input = {"x": 0, "y": 0}
                try:
                    client.close()
                except OSError:
                    pass

    def _read_client(self, client: socket.socket) -> None:
        buffer = ""
        while self.running:
            try:
                chunk = client.recv(8192)
            except socket.timeout:
                continue
            except OSError:
                return
            if not chunk:
                return
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("type") == "input":
                    self.remote_input = {
                        "x": max(-1, min(1, int(message.get("x", 0)))),
                        "y": max(-1, min(1, int(message.get("y", 0)))),
                    }
                    if message.get("action"):
                        self.actions.put(1)

    def pop_actions(self) -> int:
        count = 0
        while True:
            try:
                self.actions.get_nowait()
                count += 1
            except queue.Empty:
                return count

    def broadcast(self, state: dict[str, Any]) -> None:
        with self.client_lock:
            client = self.client
        if client is None:
            return
        try:
            send_json(client, {"type": "state", "state": state})
        except OSError:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def close(self) -> None:
        self.running = False
        try:
            self.server.close()
        except OSError:
            pass
        with self.client_lock:
            if self.client:
                try:
                    self.client.close()
                except OSError:
                    pass


class ClientNetwork:
    def __init__(self, host: str, port: int = PORT) -> None:
        self.sock = socket.create_connection((host, port), timeout=6)
        self.sock.settimeout(0.5)
        self.running = True
        self.connected = True
        self.latest_state: dict[str, Any] | None = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _read_loop(self) -> None:
        buffer = ""
        while self.running:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("type") == "state":
                    with self.lock:
                        self.latest_state = message["state"]
        self.connected = False

    def state(self) -> dict[str, Any] | None:
        with self.lock:
            return self.latest_state

    def send_input(self, x: int, y: int, action: bool) -> None:
        if not self.connected:
            return
        try:
            send_json(self.sock, {"type": "input", "x": x, "y": y, "action": action})
        except OSError:
            self.connected = False

    def close(self) -> None:
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass


class GameState:
    def __init__(self) -> None:
        self.players = [
            {"x": 420.0, "y": 500.0, "item": None, "message": "", "message_until": 0.0},
            {"x": 826.0, "y": 500.0, "item": None, "message": "", "message_until": 0.0},
        ]
        self.patient = 1
        self.tasks: list[str] = []
        self.completed = 0
        self.package_reports: list[str] = []
        self.package_ready = False
        self.stations = {test: self._idle_station() for test in TESTS}
        self.remaining = GAME_SECONDS
        self.started = False
        self.finished = False
        self.new_patient()

    @staticmethod
    def _idle_station() -> dict[str, Any]:
        return {"phase": "idle", "elapsed": 0.0, "patient": 0}

    def new_patient(self) -> None:
        count = random.randint(1, 3)
        self.tasks = random.sample(list(TESTS), count)
        self.tasks.sort(key=TESTS.index)
        self.package_reports = []
        self.package_ready = False
        self.stations = {test: self._idle_station() for test in TESTS}
        for player in self.players:
            player["item"] = None

    def start(self) -> None:
        self.started = True

    def say(self, player_id: int, text: str, seconds: float = 2.2) -> None:
        player = self.players[player_id]
        player["message"] = text
        player["message_until"] = time.monotonic() + seconds

    @staticmethod
    def player_rect(player: dict[str, Any]) -> pygame.Rect:
        return pygame.Rect(round(player["x"] - 18), round(player["y"] - 22), 36, 44)

    def _solids(self) -> list[pygame.Rect]:
        return [rect.inflate(6, 6) for rect in ZONES.values()]

    def move(self, player_id: int, dx: int, dy: int, dt: float) -> None:
        if self.finished or not self.started:
            return
        player = self.players[player_id]
        length = math.hypot(dx, dy)
        if length:
            dx /= length
            dy /= length
        for axis, amount in (("x", dx * PLAYER_SPEED * dt), ("y", dy * PLAYER_SPEED * dt)):
            old = player[axis]
            player[axis] += amount
            rect = self.player_rect(player)
            if rect.left < 8 or rect.right > WIDTH - 8 or rect.top < HUD_HEIGHT + 8 or rect.bottom > HEIGHT - 8:
                player[axis] = old
                continue
            if any(rect.colliderect(solid) for solid in self._solids()):
                player[axis] = old

    @staticmethod
    def near(player: dict[str, Any], zone: pygame.Rect) -> bool:
        px, py = player["x"], player["y"]
        nearest_x = max(zone.left, min(px, zone.right))
        nearest_y = max(zone.top, min(py, zone.bottom))
        return math.hypot(px - nearest_x, py - nearest_y) <= INTERACT_DISTANCE

    def interact(self, player_id: int) -> None:
        if self.finished or not self.started:
            return
        player = self.players[player_id]
        item = player["item"]

        if self.near(player, ZONES["trash"]):
            if item:
                player["item"] = None
                self.say(player_id, "Item discarded")
            else:
                self.say(player_id, "Nothing to discard")
            return

        if self.near(player, ZONES["submit"]):
            if item and item["kind"] == "package" and item["patient"] == self.patient:
                player["item"] = None
                self.completed += 1
                self.patient += 1
                self.new_patient()
                self.say(player_id, "Correct package submitted!", 2.6)
                return
            self.say(player_id, "Bring the completed package")
            return

        if self.near(player, ZONES["sample"]):
            if item is None:
                player["item"] = {"kind": "sample", "patient": self.patient}
                self.say(player_id, f"Picked up Sample #{self.patient}")
            else:
                self.say(player_id, "Hands are full")
            return

        if self.near(player, ZONES["package"]):
            self._interact_package(player_id)
            return

        for test in TESTS:
            if self.near(player, ZONES[test]):
                self._interact_station(player_id, test)
                return

        self.say(player_id, "Move closer to a station")

    def _interact_station(self, player_id: int, test: str) -> None:
        player = self.players[player_id]
        item = player["item"]
        station = self.stations[test]
        if station["phase"] == "output":
            if item is not None:
                self.say(player_id, "Hands are full")
                return
            player["item"] = {"kind": "report", "patient": station["patient"], "test": test}
            self.stations[test] = self._idle_station()
            self.say(player_id, f"Picked up {TEST_LABEL[test]} report")
            return
        if station["phase"] == "processing":
            self.say(player_id, f"{TEST_LABEL[test]} is processing")
            return
        if not item or item["kind"] != "sample":
            self.say(player_id, "This station needs a blood sample")
            return
        if item["patient"] != self.patient:
            self.say(player_id, "That sample is from an old patient")
            return
        player["item"] = None
        station.update(phase="processing", elapsed=0.0, patient=self.patient)
        self.say(player_id, f"Started {TEST_LABEL[test]}")

    def _interact_package(self, player_id: int) -> None:
        player = self.players[player_id]
        item = player["item"]
        if self.package_ready:
            if item is None:
                player["item"] = {"kind": "package", "patient": self.patient}
                self.package_ready = False
                self.say(player_id, "Package collected — submit it!")
            else:
                self.say(player_id, "Hands are full")
            return
        if not item or item["kind"] != "report":
            self.say(player_id, "Bring a required report")
            return
        if item["patient"] != self.patient:
            self.say(player_id, "REJECTED: wrong patient")
            return
        test = item["test"]
        if test not in self.tasks:
            self.say(player_id, "REJECTED: report not ordered — use trash", 3.0)
            return
        if test in self.package_reports:
            self.say(player_id, "REJECTED: duplicate report — use trash", 3.0)
            return
        self.package_reports.append(test)
        player["item"] = None
        if all(required in self.package_reports for required in self.tasks):
            self.package_ready = True
            self.say(player_id, "All reports packed!")
        else:
            self.say(player_id, "Report added to package")

    def update(self, dt: float) -> None:
        if not self.started or self.finished:
            return
        self.remaining = max(0.0, self.remaining - dt)
        if self.remaining <= 0:
            self.finished = True
        for test, station in self.stations.items():
            if station["phase"] != "processing":
                continue
            station["elapsed"] += dt
            if station["elapsed"] >= TEST_SECONDS[test]:
                station["elapsed"] = TEST_SECONDS[test]
                station["phase"] = "output"

    def snapshot(self, connected: bool) -> dict[str, Any]:
        now = time.monotonic()
        players = []
        for player in self.players:
            copy = dict(player)
            if copy["message_until"] < now:
                copy["message"] = ""
            players.append(copy)
        return {
            "players": players,
            "patient": self.patient,
            "tasks": self.tasks,
            "completed": self.completed,
            "package_reports": self.package_reports,
            "package_ready": self.package_ready,
            "stations": self.stations,
            "remaining": self.remaining,
            "started": self.started,
            "finished": self.finished,
            "connected": connected,
        }


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 24)
        self.small = pygame.font.SysFont("arial", 18)
        self.tiny = pygame.font.SysFont("arial", 15)
        self.big = pygame.font.SysFont("arial", 52, bold=True)
        self.title = pygame.font.SysFont("arial", 30, bold=True)
        self.player_images = [self._load_player(1), self._load_player(2)]
        self.lab_sprites = self._load_lab_sprites()

    @staticmethod
    def _load_player(number: int) -> pygame.Surface | None:
        path = ASSET_DIR / f"player{number}.png"
        if not path.exists():
            return None
        try:
            return pygame.transform.smoothscale(pygame.image.load(path).convert_alpha(), (54, 68))
        except pygame.error:
            return None

    @staticmethod
    def _load_lab_sprites() -> dict[str, pygame.Surface]:
        """Crop useful sprites from the repository's laboratory sprite sheets."""
        sprite_dir = ASSET_DIR / "sprites" / "laboratory"
        try:
            sheets = {
                name: pygame.image.load(sprite_dir / f"{name}.png").convert_alpha()
                for name in ("1", "5", "6", "7")
            }
        except (FileNotFoundError, pygame.error):
            return {}

        def crop(sheet: str, rect: tuple[int, int, int, int], size: tuple[int, int]) -> pygame.Surface:
            source = sheets[sheet].subsurface(pygame.Rect(rect)).copy()
            return pygame.transform.smoothscale(source, size)

        return {
            "floor": crop("1", (0, 0, 48, 48), (52, 52)),
            "sample": crop("6", (0, 0, 132, 88), (96, 64)),
            "CBC": crop("7", (194, 0, 91, 94), (64, 66)),
            "SMEAR": crop("7", (0, 0, 102, 96), (72, 68)),
            "COAG": crop("7", (0, 194, 106, 94), (76, 66)),
            "trash": crop("6", (576, 385, 130, 96), (94, 70)),
            "package": crop("6", (575, 0, 193, 96), (104, 52)),
        }

    def sprite(self, name: str, center: tuple[int, int]) -> None:
        surface = self.lab_sprites.get(name)
        if surface:
            self.screen.blit(surface, surface.get_rect(center=center))

    def text(self, text: str, pos: tuple[int, int], color: tuple[int, int, int] = BLACK,
             font: pygame.font.Font | None = None, center: bool = False) -> pygame.Rect:
        surface = (font or self.font).render(text, True, color)
        rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        self.screen.blit(surface, rect)
        return rect

    def draw(self, state: dict[str, Any], local_player: int, status: str = "") -> None:
        self.screen.fill(BG)
        self._draw_floor()
        self._draw_hud(state)
        self._draw_zones(state)
        self._draw_players(state, local_player)
        if status:
            self.text(status, (WIDTH // 2, HEIGHT - 18), RED, self.small, center=True)
        if not state.get("connected", False):
            self._overlay("WAITING FOR PLAYER 2", f"Host IP: {local_ip()}   Port: {PORT}")
        elif state.get("finished"):
            result = "LAB SHIFT COMPLETE"
            subtitle = f"Patients completed: {state['completed']} — " + ("VICTORY!" if state["completed"] >= 3 else "Try again")
            self._overlay(result, subtitle)

    def _draw_floor(self) -> None:
        tile = 52
        for y in range(HUD_HEIGHT, HEIGHT, tile):
            for x in range(0, WIDTH, tile):
                if "floor" in self.lab_sprites:
                    self.screen.blit(self.lab_sprites["floor"], (x, y))
                    if (x // tile + y // tile) % 2:
                        shade = pygame.Surface((tile, tile), pygame.SRCALPHA)
                        shade.fill((20, 45, 55, 12))
                        self.screen.blit(shade, (x, y))
                else:
                    color = FLOOR_A if (x // tile + y // tile) % 2 == 0 else FLOOR_B
                    pygame.draw.rect(self.screen, color, (x, y, tile - 1, tile - 1))

    def _draw_hud(self, state: dict[str, Any]) -> None:
        pygame.draw.rect(self.screen, NAVY, (0, 0, WIDTH, HUD_HEIGHT))
        seconds = max(0, math.ceil(state["remaining"]))
        self.text(f"{seconds // 60}:{seconds % 60:02d}", (25, 22), WHITE, self.big)
        self.text(f"PATIENT #{state['patient']}", (245, 18), WHITE, self.title)
        self.text("ORDER", (245, 59), (162, 184, 194), self.tiny)
        x = 245
        for test in TESTS:
            required = test in state["tasks"]
            color = TEST_COLOR[test] if required else (73, 91, 103)
            rect = pygame.Rect(x, 82, 186 if test != "SMEAR" else 250, 32)
            pygame.draw.rect(self.screen, color, rect, border_radius=7)
            pygame.draw.rect(self.screen, WHITE if required else GRAY, rect, 2, border_radius=7)
            self.text(TEST_LABEL[test] if required else "—", rect.center, BLACK if required else (143, 155, 161), self.tiny, True)
            x = rect.right + 12
        self.text(f"Completed: {state['completed']} / 3+", (1050, 27), WHITE, self.font)
        victory = state["completed"] >= 3
        self.text("Victory reached — keep going!" if victory else "Goal: 3 patients", (1050, 65), GREEN if victory else (182, 201, 210), self.small)

    def _zone(self, rect: pygame.Rect, title: str, color: tuple[int, int, int]) -> None:
        pygame.draw.rect(self.screen, (244, 246, 244), rect, border_radius=12)
        pygame.draw.rect(self.screen, color, rect, 5, border_radius=12)
        self.text(title, (rect.centerx, rect.top + 22), BLACK, self.small, True)

    def _draw_zones(self, state: dict[str, Any]) -> None:
        self._zone(ZONES["sample"], "BLOOD SAMPLE PICKUP", RED)
        if "sample" in self.lab_sprites:
            self.sprite("sample", (ZONES["sample"].centerx, ZONES["sample"].centery + 14))
        else:
            for x in (142, 206, 270):
                pygame.draw.rect(self.screen, RED, (x, 205, 18, 31), border_radius=5)
                pygame.draw.rect(self.screen, WHITE, (x + 3, 209, 12, 10), border_radius=2)

        self._draw_station("CBC", state)
        self._draw_station("COAG", state)
        self._draw_station("SMEAR", state)

        self._zone(ZONES["trash"], "TRASH", GRAY)
        self.sprite("trash", (ZONES["trash"].centerx, ZONES["trash"].centery + 18))
        self.text("Discard", (ZONES["trash"].centerx, ZONES["trash"].bottom - 15), GRAY, self.tiny, True)
        self._zone(ZONES["submit"], "SUBMIT", GREEN)
        self.text("Package", (ZONES["submit"].centerx, ZONES["submit"].centery + 20), GREEN, self.tiny, True)

        rect = ZONES["package"]
        self._zone(rect, "PACKAGE TABLE", ORANGE)
        reports = state["package_reports"]
        required = state["tasks"]
        self.text(f"Reports: {len(reports)} / {len(required)}", (rect.centerx, rect.top + 55), BLACK, self.small, True)
        if state["package_ready"]:
            self.sprite("package", (rect.centerx, rect.bottom - 29))
            self.text("READY", (rect.centerx, rect.bottom - 13), BLACK, self.tiny, True)
        else:
            start_x = rect.centerx - (len(required) * 23)
            for index, test in enumerate(required):
                color = TEST_COLOR[test] if test in reports else (130, 139, 143)
                pygame.draw.circle(self.screen, color, (start_x + index * 46 + 22, rect.bottom - 27), 11)

    def _draw_station(self, test: str, state: dict[str, Any]) -> None:
        rect = ZONES[test]
        color = TEST_COLOR[test]
        border = color if test != "CBC" else BLUE
        self._zone(rect, TEST_LABEL[test].upper(), border)
        station = state["stations"][test]
        phase = station["phase"]
        if phase == "idle":
            self.sprite(test, (rect.centerx, rect.centery + 12))
            label = f"SPACE: insert sample ({TEST_SECONDS[test]:g}s)"
            self.text(label, (rect.centerx, rect.bottom - 10), GRAY, self.tiny, True)
        elif phase == "processing":
            progress = min(1.0, station["elapsed"] / TEST_SECONDS[test])
            bar = pygame.Rect(rect.left + 24, rect.bottom - 34, rect.width - 48, 15)
            pygame.draw.rect(self.screen, (172, 180, 181), bar, border_radius=7)
            fill = bar.copy()
            fill.width = round(bar.width * progress)
            pygame.draw.rect(self.screen, BLUE, fill, border_radius=7)
            self.text(f"Processing {progress * 100:.0f}%", (rect.centerx, rect.centery + 6), BLACK, self.tiny, True)
        else:
            report_color = TEST_COLOR[test]
            report = pygame.Rect(rect.centerx - 32, rect.centery - 5, 64, 40)
            pygame.draw.rect(self.screen, report_color, report, border_radius=4)
            pygame.draw.rect(self.screen, BLACK, report, 2, border_radius=4)
            self.text(f"#{station['patient']}", report.center, BLACK, self.tiny, True)

    def _draw_players(self, state: dict[str, Any], local_player: int) -> None:
        for index, player in enumerate(state["players"]):
            x, y = round(player["x"]), round(player["y"])
            image = self.player_images[index]
            if image:
                self.screen.blit(image, image.get_rect(center=(x, y)))
            else:
                color = BLUE if index == 0 else RED
                pygame.draw.circle(self.screen, (37, 44, 49), (x + 3, y + 16), 20)
                pygame.draw.circle(self.screen, color, (x, y - 7), 23)
                pygame.draw.circle(self.screen, (247, 211, 177), (x, y - 15), 13)
            label = f"P{index + 1}" + (" (YOU)" if index == local_player else "")
            self.text(label, (x, y + 37), NAVY, self.tiny, True)
            if player["item"]:
                item = player["item"]
                if item["kind"] == "sample":
                    item_label, item_color = f"Sample #{item['patient']}", RED
                elif item["kind"] == "report":
                    item_label, item_color = f"{item['test']} #{item['patient']}", TEST_COLOR[item["test"]]
                else:
                    item_label, item_color = f"Package #{item['patient']}", ORANGE
                bubble = self.small.render(item_label, True, BLACK)
                bubble_rect = bubble.get_rect(center=(x, y - 52)).inflate(14, 7)
                pygame.draw.rect(self.screen, item_color, bubble_rect, border_radius=7)
                pygame.draw.rect(self.screen, BLACK, bubble_rect, 2, border_radius=7)
                self.screen.blit(bubble, bubble.get_rect(center=bubble_rect.center))
            if player["message"]:
                self.text(player["message"], (x, y + 57), RED, self.tiny, True)

    def _overlay(self, heading: str, subtitle: str) -> None:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((10, 18, 25, 175))
        self.screen.blit(shade, (0, 0))
        box = pygame.Rect(WIDTH // 2 - 310, HEIGHT // 2 - 92, 620, 184)
        pygame.draw.rect(self.screen, WHITE, box, border_radius=16)
        pygame.draw.rect(self.screen, BLUE, box, 5, border_radius=16)
        self.text(heading, (WIDTH // 2, HEIGHT // 2 - 34), NAVY, self.title, True)
        self.text(subtitle, (WIDTH // 2, HEIGHT // 2 + 20), BLACK, self.font, True)
        self.text("Arrow keys: move    Space: interact    Esc: quit", (WIDTH // 2, HEIGHT // 2 + 59), GRAY, self.small, True)


def directional_input() -> tuple[int, int]:
    keys = pygame.key.get_pressed()
    x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
    y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])
    return x, y


def run_host(screen: pygame.Surface) -> None:
    try:
        network = HostNetwork()
    except OSError as exc:
        error_screen(screen, f"Could not host on port {PORT}: {exc}")
        return
    renderer = Renderer(screen)
    clock = pygame.time.Clock()
    game = GameState()
    running = True
    previous_space = False
    broadcast_timer = 0.0
    try:
        while running:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            if network.connected and not game.started:
                game.start()
            x, y = directional_input()
            space = pygame.key.get_pressed()[pygame.K_SPACE]
            action = space and not previous_space
            previous_space = space
            game.move(0, x, y, dt)
            remote = network.remote_input
            game.move(1, remote["x"], remote["y"], dt)
            if action:
                game.interact(0)
            for _ in range(network.pop_actions()):
                game.interact(1)
            game.update(dt)
            state = game.snapshot(network.connected)
            broadcast_timer += dt
            if broadcast_timer >= SNAPSHOT_RATE:
                network.broadcast(state)
                broadcast_timer = 0.0
            renderer.draw(state, 0)
            pygame.display.flip()
    finally:
        network.close()


def run_client(screen: pygame.Surface, host: str) -> None:
    try:
        network = ClientNetwork(host)
    except OSError as exc:
        error_screen(screen, f"Could not connect to {host}:{PORT}: {exc}")
        return
    renderer = Renderer(screen)
    clock = pygame.time.Clock()
    running = True
    previous_space = False
    last_send = 0.0
    try:
        while running:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            x, y = directional_input()
            space = pygame.key.get_pressed()[pygame.K_SPACE]
            action = space and not previous_space
            previous_space = space
            now = time.monotonic()
            if action or now - last_send >= SNAPSHOT_RATE:
                network.send_input(x, y, action)
                last_send = now
            state = network.state()
            if state:
                renderer.draw(state, 1, "" if network.connected else "Connection lost")
            else:
                waiting_state = GameState().snapshot(True)
                renderer.draw(waiting_state, 1, f"Connecting to {host}...")
            pygame.display.flip()
    finally:
        network.close()


def button(screen: pygame.Surface, rect: pygame.Rect, label: str, font: pygame.font.Font,
           mouse: tuple[int, int]) -> None:
    hovered = rect.collidepoint(mouse)
    pygame.draw.rect(screen, (66, 150, 205) if hovered else BLUE, rect, border_radius=10)
    pygame.draw.rect(screen, WHITE, rect, 2, border_radius=10)
    text = font.render(label, True, WHITE)
    screen.blit(text, text.get_rect(center=rect.center))


def main_menu(screen: pygame.Surface) -> tuple[str, str] | None:
    title = pygame.font.SysFont("arial", 54, bold=True)
    font = pygame.font.SysFont("arial", 25, bold=True)
    small = pygame.font.SysFont("arial", 19)
    host_button = pygame.Rect(WIDTH // 2 - 245, 350, 220, 62)
    join_button = pygame.Rect(WIDTH // 2 + 25, 350, 220, 62)
    ip_box = pygame.Rect(WIDTH // 2 - 245, 270, 490, 52)
    ip_text = "127.0.0.1"
    active = False
    clock = pygame.time.Clock()
    while True:
        clock.tick(FPS)
        mouse = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if active:
                    if event.key == pygame.K_BACKSPACE:
                        ip_text = ip_text[:-1]
                    elif event.key == pygame.K_RETURN and ip_text:
                        return "join", ip_text
                    elif event.unicode in "0123456789.":
                        ip_text += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                active = ip_box.collidepoint(event.pos)
                if host_button.collidepoint(event.pos):
                    return "host", ""
                if join_button.collidepoint(event.pos) and ip_text:
                    return "join", ip_text
        screen.fill((20, 39, 53))
        screen.blit(title.render("HEMATOLOGY LAB RUSH", True, WHITE), title.render("HEMATOLOGY LAB RUSH", True, WHITE).get_rect(center=(WIDTH // 2, 122)))
        subtitle = small.render("Two-player LAN demo", True, (170, 198, 213))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 178)))
        pygame.draw.rect(screen, WHITE, ip_box, border_radius=8)
        pygame.draw.rect(screen, BLUE if active else GRAY, ip_box, 3, border_radius=8)
        ip_surface = font.render(ip_text or "Host IP address", True, BLACK if ip_text else GRAY)
        screen.blit(ip_surface, (ip_box.left + 14, ip_box.centery - ip_surface.get_height() // 2))
        button(screen, host_button, "HOST GAME", font, mouse)
        button(screen, join_button, "JOIN GAME", font, mouse)
        info = small.render(f"Host will listen on port {PORT}. Your local IP: {local_ip()}", True, (170, 198, 213))
        screen.blit(info, info.get_rect(center=(WIDTH // 2, 465)))
        controls = small.render("Arrow keys to move  |  Space to interact", True, (170, 198, 213))
        screen.blit(controls, controls.get_rect(center=(WIDTH // 2, 510)))
        pygame.display.flip()


def error_screen(screen: pygame.Surface, message: str) -> None:
    font = pygame.font.SysFont("arial", 23)
    small = pygame.font.SysFont("arial", 18)
    clock = pygame.time.Clock()
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                return
        screen.fill(NAVY)
        headline = font.render("NETWORK ERROR", True, RED)
        detail = small.render(message[:110], True, WHITE)
        prompt = small.render("Press any key to return", True, (174, 194, 204))
        screen.blit(headline, headline.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 45)))
        screen.blit(detail, detail.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))
        pygame.display.flip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--host", action="store_true", help="host a LAN game")
    mode.add_argument("--join", metavar="IP", help="join a host by local IP")
    mode.add_argument("--smoke-test", action="store_true", help="render three frames headlessly and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_caption("Hematology Lab Rush")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    try:
        if args.smoke_test:
            renderer = Renderer(screen)
            game = GameState()
            game.start()
            for _ in range(3):
                renderer.draw(game.snapshot(True), 0)
                pygame.display.flip()
        elif args.host:
            run_host(screen)
        elif args.join:
            run_client(screen, args.join)
        else:
            choice = main_menu(screen)
            if choice:
                mode, host = choice
                run_host(screen) if mode == "host" else run_client(screen, host)
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
