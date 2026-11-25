"""Heads-up display and menus, drawn with the default pygame fonts."""

import pygame


class HUD:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.big = self._font(78, True)
        self.mid = self._font(34, True)
        self.small = self._font(20)
        self.tiny = self._font(16)

    @staticmethod
    def _font(size, bold=False):
        try:
            return pygame.font.SysFont("Segoe UI", size, bold=bold)
        except Exception:
            return pygame.font.Font(None, size)

    def _text(self, surf, font, text, color, pos, anchor="topleft", shadow=True):
        img = font.render(text, True, color)
        rect = img.get_rect(**{anchor: pos})
        if shadow:
            shade = font.render(text, True, (28, 44, 62))
            surf.blit(shade, rect.move(2, 2))
        surf.blit(img, rect)
        return rect

    def draw_play(self, surf, score, speed_kmh, drift_deg, stats_text=None):
        self._text(
            surf, self.big, f"{int(score):,} m", (255, 255, 255), (self.w // 2, 18), "midtop"
        )
        self._text(
            surf, self.tiny, "METRES RIDDEN", (226, 236, 246), (self.w // 2, 100), "midtop"
        )
        self._text(
            surf, self.mid, f"{speed_kmh:3.0f} km/h", (255, 255, 255), (26, self.h - 62)
        )
        if abs(drift_deg) > 12.0:
            colour = (255, 226, 140) if abs(drift_deg) < 40.0 else (255, 170, 120)
            self._text(
                surf, self.mid, f"DRIFT {abs(drift_deg):2.0f}\u00b0", colour,
                (self.w // 2, self.h - 62), "midtop",
            )
        if stats_text:
            for i, line in enumerate(stats_text):
                self._text(surf, self.tiny, line, (238, 246, 252), (18, 14 + i * 20), shadow=False)

    def _overlay(self, surf, alpha=170):
        shade = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        shade.fill((8, 18, 32, alpha))
        surf.blit(shade, (0, 0))

    def draw_title(self, surf):
        self._overlay(surf, 120)
        cx = self.w // 2
        self._text(surf, self.big, "SNOWDRIFT", (255, 255, 255), (cx, self.h // 5), "midtop")
        self._text(
            surf, self.mid, "endless ice  \u2022  third person  \u2022  drift for distance",
            (214, 232, 246), (cx, self.h // 5 + 92), "midtop",
        )
        controls = [
            ("W  /  \u2191", "throttle"),
            ("S  /  \u2193", "brake & reverse"),
            ("A  D", "steer"),
            ("P", "pause"),
            ("ESC", "quit"),
        ]
        y = self.h // 2 + 36
        col = cx - 96
        for key, action in controls:
            self._text(surf, self.small, key, (255, 240, 190), (col, y), "topright")
            self._text(surf, self.small, action, (232, 242, 250), (col + 22, y))
            y += 30
        self._text(
            surf, self.mid, "PRESS SPACE TO RIDE", (255, 240, 190),
            (cx, self.h - 96), "midtop",
        )

    def draw_pause(self, surf):
        self._overlay(surf, 140)
        self._text(surf, self.big, "PAUSED", (255, 255, 255), (self.w // 2, self.h // 2 - 80), "midtop")
        self._text(
            surf, self.small, "P resume    R restart    ESC quit",
            (226, 236, 246), (self.w // 2, self.h // 2 + 12), "midtop",
        )
