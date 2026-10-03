"""Runnable layout scaffold; networking and experiments are not implemented."""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab Panic scaffold")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if args.smoke_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    import pygame

    pygame.init()
    try:
        screen = pygame.display.set_mode((960, 640))
        pygame.display.set_caption("Lab Panic")
        clock = pygame.time.Clock()
        font = pygame.font.Font(None, 28)
        title = pygame.font.Font(None, 64)
        position = pygame.Vector2(480, 470)
        running = True
        frames = 0
        while running:
            dt = min(clock.tick(60) / 1000, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
            keys = pygame.key.get_pressed()
            direction = pygame.Vector2(int(keys[pygame.K_d]) - int(keys[pygame.K_a]), int(keys[pygame.K_s]) - int(keys[pygame.K_w]))
            if direction.length_squared():
                position += direction.normalize() * 220 * dt
            position.x = max(25, min(935, position.x))
            position.y = max(390, min(615, position.y))
            screen.fill((232, 242, 242))
            screen.blit(title.render("Lab Panic", True, (27, 86, 91)), (40, 30))
            screen.blit(font.render("WASD: move | Esc: exit", True, (45, 75, 80)), (40, 100))
            for index, label in enumerate(("Receive", "Centrifuge", "Reagent", "Analyze", "Report")):
                x = 30 + index * 186
                pygame.draw.rect(screen, (99, 180, 178), (x, 220, 156, 100), border_radius=12)
                screen.blit(font.render(label, True, (15, 45, 50)), (x + 10, 256))
            pygame.draw.circle(screen, (232, 119, 107), (round(position.x), round(position.y)), 20)
            screen.blit(font.render("Layout preview: LAN and processing are not implemented yet.", True, (45, 75, 80)), (40, 350))
            pygame.display.flip()
            frames += 1
            if args.smoke_test and frames >= 3:
                running = False
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
