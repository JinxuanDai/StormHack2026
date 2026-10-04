"""Scale one logical canvas and map pointer input through the same viewport."""

import pygame

from . import theme


def viewport_for(size: tuple[int, int]) -> pygame.Rect:
    width, height = size
    scale = min(width / theme.WIDTH, height / theme.HEIGHT)
    rect = pygame.Rect(0, 0, max(1, round(theme.WIDTH * scale)),
                       max(1, round(theme.HEIGHT * scale)))
    rect.center = (width // 2, height // 2)
    return rect


def logical_position(position: tuple[int, int], viewport: pygame.Rect) -> tuple[int, int]:
    if not viewport.collidepoint(position):
        return (-1, -1)
    return (int((position[0] - viewport.x) * theme.WIDTH / viewport.width),
            int((position[1] - viewport.y) * theme.HEIGHT / viewport.height))


class GameDisplay:
    def __init__(self, *, fullscreen: bool = False) -> None:
        self.canvas = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        self.fullscreen = fullscreen
        self._set_mode()

    def _set_mode(self) -> None:
        self.window = pygame.display.set_mode(
            (0, 0) if self.fullscreen else (theme.WIDTH, theme.HEIGHT),
            pygame.FULLSCREEN if self.fullscreen else 0)
        self.viewport = viewport_for(self.window.get_size())

    def events(self) -> list[pygame.event.Event]:
        result = []
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and (
                event.key == pygame.K_F11 or
                (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)
            ):
                self.fullscreen = not self.fullscreen
                self._set_mode()
                continue
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                values = dict(event.dict)
                values["pos"] = logical_position(event.pos, self.viewport)
                event = pygame.event.Event(event.type, values)
            result.append(event)
        return result

    def present(self) -> None:
        self.window.fill((0, 0, 0))
        image = pygame.transform.scale(self.canvas, self.viewport.size)
        self.window.blit(image, self.viewport)
        pygame.display.flip()
