"""Snowdrift - infinite third-person snowmobile drifting on an ice track.

Run with:  python main.py
"""

import argparse
import random
import sys

import pygame

from snowdrift.game import Game


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Snowdrift - endless drifting")
    parser.add_argument("--size", default="1280x720", help="window size, e.g. 1280x720")
    parser.add_argument("--seed", type=int, default=None, help="track seed")
    parser.add_argument("--stats", action="store_true", help="show fps / polygons / RAM")
    parser.add_argument("--fullscreen", action="store_true", help="start fullscreen")
    parser.add_argument(
        "--theme", default="snow",
        help="snow (ice/snowmobile, default), city (asphalt/buildings) or dirt (bicycle/bamboo)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        width, height = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        raise SystemExit("--size must look like 1280x720")

    pygame.init()
    pygame.display.set_caption("Snowdrift")
    flags = pygame.FULLSCREEN if args.fullscreen else 0
    surface = pygame.display.set_mode((width, height), flags)
    clock = pygame.time.Clock()

    seed = args.seed if args.seed is not None else random.randrange(1, 1 << 30)
    game = Game(surface, seed=seed, stats=args.stats, theme=args.theme)

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif not game.handle_event(event):
                running = False
        if not running:
            break
        game.update(dt)
        game.draw()
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
