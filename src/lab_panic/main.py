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

from .ui import theme
from .ui.renderer import Renderer as UIRenderer
from .ui.views import PatientView, PlayerView, RoundView, StationView


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
                self.say(player_id, "Report ready: empty hands and collect it first", 3.0)
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


def display_position(x: float, y: float) -> tuple[int, int]:
    """Map authoritative world coordinates into the UI room interior."""
    return (round(24 + x * 912 / WIDTH),
            round(140 + (y - HUD_HEIGHT) * 460 / (HEIGHT - HUD_HEIGHT)))


def display_zone(rect: pygame.Rect) -> pygame.Rect:
    left, top = display_position(rect.left, rect.top)
    right, bottom = display_position(rect.right, rect.bottom)
    return pygame.Rect(left, top, right - left, bottom - top)


def round_view(state: dict[str, Any]) -> RoundView:
    """Adapt a host snapshot without changing simulation or wire format."""
    types = {"sample": "extraction", "CBC": "cbc", "SMEAR": "microscope",
             "COAG": "coagulation", "trash": "trash", "submit": "submit", "package": "package"}
    labels = {"sample": ("Sample Extraction",), "CBC": ("CBC",),
              "SMEAR": ("Blood Smear", "Microscope"), "COAG": ("Coagulation",),
              "trash": ("Trash",), "submit": ("Submit",), "package": ("Package",)}
    stations = []
    for key, zone in ZONES.items():
        rect = display_zone(zone)
        machine = state["stations"].get(key, {})
        phase = machine.get("phase", "idle")
        stations.append(StationView(
            key, types[key], labels[key], rect.x, rect.y, width=rect.width,
            height=rect.height, is_processing=phase == "processing",
            processing_progress=machine.get("elapsed", 0) / TEST_SECONDS[key] if key in TEST_SECONDS else 0,
            is_complete=phase == "output" or (key == "package" and state["package_ready"])))
    players = tuple(PlayerView(str(index), *display_position(player["x"], player["y"]),
                               "sample" if player["item"] and player["item"]["kind"] == "sample" else None)
                    for index, player in enumerate(state["players"]))
    tasks = tuple("Blood Smear" if test == "SMEAR" else TEST_LABEL[test] for test in state["tasks"])
    return RoundView(state["remaining"], (PatientView(f"P-{state['patient']:03d}", tasks),),
                     tuple(stations), players, ())


class Renderer:
    """Application presentation adapter; simulation stays in world coordinates."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.ui = UIRenderer()

    def text(self, value: str, pos: tuple[int, int], color=theme.INK, *, center=False) -> None:
        theme.text(self.screen, self.ui.fonts.small, value, pos, color, center=center)

    def draw(self, state: dict[str, Any], local_player: int, status: str = "") -> None:
        if state["finished"]:
            self.ui.draw_result(self.screen, success=state["completed"] >= 3)
            self.text(f"Patients completed: {state['completed']} / 3", (480, 390), center=True)
            self.text("Esc: quit", (480, 425), center=True)
        else:
            self.ui.draw_gameplay(self.screen, round_view(state))
            self.text(f"Completed: {state['completed']} / 3", (365, 24))
            self.text(f"Reports packed: {len(state['package_reports'])} / {len(state['tasks'])}", (365, 50))
            self.text("Packed: " + (", ".join(state["package_reports"]) or "none"), (365, 76))
            for index, player in enumerate(state["players"]):
                x, y = display_position(player["x"], player["y"])
                self.text(f"P{index + 1}" + (" (YOU)" if index == local_player else ""), (x, y + 28), center=True)
                item = player["item"]
                if item:
                    label = item.get("test", item["kind"]).upper() + f" #{item['patient']}"
                    self.text(label, (x, y - 40), center=True)
                    if item["kind"] != "sample":
                        color = TEST_COLOR[item["test"]] if item["kind"] == "report" else ORANGE
                        rect = pygame.Rect(x + 16, y - 12, 26, 20)
                        pygame.draw.rect(self.screen, color, rect, border_radius=3)
                        pygame.draw.rect(self.screen, theme.INK, rect, 1, border_radius=3)
            message = state["players"][local_player]["message"]
            self.text(status or message or "Arrow keys: move   Space: interact   Esc: quit", (480, 624), theme.RED if status or message else theme.MUTED, center=True)
            if not state.get("connected", False):
                shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                shade.fill((230, 233, 236, 225))
                self.screen.blit(shade, (0, 0))
                theme.text(self.screen, self.ui.fonts.heading, "WAITING FOR PLAYER 2", (480, 290), center=True)
                self.text(f"Host IP: {local_ip()}   Port: {PORT}", (480, 335), center=True)
                self.text("Esc: quit", (480, 375), center=True)
        if state["finished"] and status:
            self.text(status, (480, 624), theme.RED, center=True)


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


def main_menu(screen: pygame.Surface) -> tuple[str, str] | None:
    renderer = UIRenderer()
    ip_box = pygame.Rect(340, 510, 280, 42)
    ip_text = "127.0.0.1"
    selected, active = 0, False
    clock = pygame.time.Clock()
    host_ip = local_ip()
    while True:
        clock.tick(FPS)
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
                    elif event.unicode and event.unicode in "0123456789.":
                        ip_text += event.unicode
                else:
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        selected = (selected + (1 if event.key == pygame.K_DOWN else -1)) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if selected == 2:
                            return None
                        if selected == 0 or ip_text:
                            return ("host", "") if selected == 0 else ("join", ip_text)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                active = ip_box.collidepoint(event.pos)
                for index, rect in enumerate(renderer.menu_buttons()):
                    if rect.collidepoint(event.pos):
                        selected = index
                        if index == 2:
                            return None
                        if index == 0 or ip_text:
                            return ("host", "") if index == 0 else ("join", ip_text)
        renderer.draw_menu(screen, selected)
        pygame.draw.rect(screen, theme.PANEL, ip_box, border_radius=6)
        pygame.draw.rect(screen, theme.TEAL if active else theme.BORDER, ip_box, 2, border_radius=6)
        theme.text(screen, renderer.fonts.small, ip_text or "Host IP address", (ip_box.x + 12, ip_box.y + 12))
        theme.text(screen, renderer.fonts.small, "Join: click above to enter the host IP", (480, 575), center=True)
        theme.text(screen, renderer.fonts.small, f"Your IP: {host_ip}   Port: {PORT}", (480, 606), center=True)
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
        screen.blit(headline, headline.get_rect(center=(theme.WIDTH // 2, theme.HEIGHT // 2 - 45)))
        screen.blit(detail, detail.get_rect(center=(theme.WIDTH // 2, theme.HEIGHT // 2)))
        screen.blit(prompt, prompt.get_rect(center=(theme.WIDTH // 2, theme.HEIGHT // 2 + 45)))
        pygame.display.flip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--host", action="store_true", help="host a LAN game")
    mode.add_argument("--join", metavar="IP", help="join a host by local IP")
    mode.add_argument("--smoke-test", action="store_true", help="render menu, live states and results headlessly and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_caption("Lab Panic")
    screen = pygame.display.set_mode((theme.WIDTH, theme.HEIGHT))
    try:
        if args.smoke_test:
            renderer = Renderer(screen)
            game = GameState()
            game.start()
            renderer.ui.draw_menu(screen)
            renderer.draw(game.snapshot(False), 0)
            game.stations["CBC"].update(phase="processing", elapsed=1.0)
            game.stations["COAG"].update(phase="output", patient=game.patient)
            game.players[0]["item"] = {"kind": "report", "test": "CBC", "patient": game.patient}
            game.players[1]["item"] = {"kind": "sample", "patient": game.patient}
            game.package_ready = True
            renderer.draw(game.snapshot(True), 0)
            for completed in (0, 3):
                game.finished = True
                game.completed = completed
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
