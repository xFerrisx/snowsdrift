"""Heads-up display and menus, drawn with the default pygame fonts."""

import pygame

from . import themes


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

    def draw_title(self, surf, theme, active):
        self._overlay(surf, 128)
        cx = self.w // 2
        self._text(surf, self.big, "SNOWDRIFT", (255, 255, 255), (cx, self.h // 5 - 30), "midtop")
        self._text(surf, self.mid, theme.name, theme.accent, (cx, self.h // 5 + 58), "midtop")
        self._text(
            surf, self.small, theme.blurb, (226, 236, 246),
            (cx, self.h // 5 + 104), "midtop",
        )

        y = self.h // 5 + 150
        spacing = 196
        count = len(themes.THEMES)
        x0 = cx - (count - 1) * spacing // 2
        for i, item in enumerate(themes.THEMES):
            col = theme.accent if i == active else (172, 188, 202)
            self._text(surf, self.small, f"{i + 1}  {item.name}", col, (x0 + i * spacing, y), "midtop")
        self._text(
            surf, self.tiny, "1 2 3  or  LEFT / RIGHT  to change the run",
            (226, 236, 246), (cx, y + 28), "midtop",
        )

        controls = [
            ("W  /  \u2191", "throttle"),
            ("S  /  \u2193", "brake & reverse"),
            ("A  D", "steer"),
            ("P", "pause"),
            ("ESC", "quit"),
        ]
        col = cx - 96
        y = self.h // 2 + 96
        for key, action in controls:
            self._text(surf, self.small, key, theme.accent, (col, y), "topright")
            self._text(surf, self.small, action, (232, 242, 250), (col + 22, y))
            y += 28
        self._text(
            surf, self.mid, "PRESS SPACE TO RIDE", theme.accent,
            (cx, self.h - 84), "midtop",
        )

    def draw_pause(self, surf, theme, active):
        self._overlay(surf, 150)
        cx = self.w // 2
        top = self.h // 2 - 150
        self._text(surf, self.big, "PAUSED", (255, 255, 255), (cx, top), "midtop")
        self._text(surf, self.mid, theme.name, theme.accent, (cx, top + 92), "midtop")
        self._text(surf, self.small, theme.blurb, (226, 236, 246), (cx, top + 136), "midtop")

        y = top + 188
        spacing = 196
        count = len(themes.THEMES)
        x0 = cx - (count - 1) * spacing // 2
        for i, item in enumerate(themes.THEMES):
            col = theme.accent if i == active else (172, 188, 202)
            self._text(surf, self.small, f"{i + 1}  {item.name}", col, (x0 + i * spacing, y), "midtop")
        self._text(
            surf, self.tiny,
            "1 2 3  or  LEFT / RIGHT  to switch the run  \u2022  your distance is kept",
            (226, 236, 246), (cx, y + 28), "midtop",
        )
        self._text(
            surf, self.small, "P resume    R restart    ESC quit",
            (226, 236, 246), (cx, y + 72), "midtop",
        )
