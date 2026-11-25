"""Third-person camera and a painter's-algorithm 3D renderer.

No OpenGL, no numpy: every polygon is transformed in Python, clipped against
the near plane, projected, fogged toward the horizon colour, sorted
back-to-front and filled with ``pygame.draw.polygon``. Only a few hundred
quads are on screen at once, so this stays comfortably interactive.
"""

import math

import pygame

from . import config
from .util import clamp, lerp_color, vnoise

NEAR = 0.45
CLAMP_PX = 12000


class Camera:
    __slots__ = (
        "w", "h", "focal", "x", "y", "z", "yaw", "pitch",
        "fx", "fy", "fz", "rx", "rz", "ux", "uy", "uz",
    )

    def __init__(self, w, h, fov_deg=None):
        self.w = w
        self.h = h
        fov = config.FOV_DEG if fov_deg is None else fov_deg
        self.focal = (h * 0.5) / math.tan(math.radians(fov) * 0.5)
        self.set((0.0, 4.0, -10.0), 0.0, -0.12)

    def set(self, pos, yaw, pitch):
        self.x, self.y, self.z = pos
        self.yaw = yaw
        self.pitch = pitch
        cp = math.cos(pitch)
        sp = math.sin(pitch)
        sy = math.sin(yaw)
        cy = math.cos(yaw)
        self.fx = sy * cp
        self.fy = sp
        self.fz = cy * cp
        self.rx = cy
        self.rz = -sy
        self.ux = -sp * sy
        self.uy = cp
        self.uz = -sp * cy

    def depth(self, p):
        return (p[0] - self.x) * self.fx + (p[1] - self.y) * self.fy + (p[2] - self.z) * self.fz

    def project(self, p):
        dx = p[0] - self.x
        dy = p[1] - self.y
        dz = p[2] - self.z
        cz = dx * self.fx + dy * self.fy + dz * self.fz
        if cz < NEAR:
            return None
        cx = dx * self.rx + dz * self.rz
        cy = dx * self.ux + dy * self.uy + dz * self.uz
        s = self.focal / cz
        return (self.w * 0.5 + cx * s, self.h * 0.5 - cy * s, cz)


def _clip_near(poly):
    """Sutherland-Hodgman clip of a camera-space polygon against z = NEAR."""
    out = []
    n = len(poly)
    for i in range(n):
        ax, ay, az = poly[i]
        bx, by, bz = poly[(i + 1) % n]
        a_in = az >= NEAR
        b_in = bz >= NEAR
        if a_in:
            out.append((ax, ay, az))
        if a_in != b_in:
            t = (NEAR - az) / (bz - az)
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t, NEAR))
    return out


class Renderer:
    def __init__(self, surface):
        self.surface = surface
        self.w, self.h = surface.get_size()
        self.cam = Camera(self.w, self.h)
        self.queue = []
        self.poly_count = 0

    # -- geometry --------------------------------------------------------
    def add(self, verts, color, depth=None):
        cam = self.cam
        cx0, cy0, cz0 = cam.x, cam.y, cam.z
        fx, fy, fz = cam.fx, cam.fy, cam.fz
        rx, rz = cam.rx, cam.rz
        ux, uy, uz = cam.ux, cam.uy, cam.uz

        view = []
        any_front = False
        any_behind = False
        for vx, vy, vz in verts:
            dx = vx - cx0
            dy = vy - cy0
            dz = vz - cz0
            z = dx * fx + dy * fy + dz * fz
            if z >= NEAR:
                any_front = True
            else:
                any_behind = True
            view.append((dx * rx + dz * rz, dx * ux + dy * uy + dz * uz, z))
        if not any_front:
            return

        if depth is None:
            depth = 0.0
            for _, _, z in view:
                depth += z
            depth /= len(view)
        if depth > config.FOG_END:
            return

        poly = _clip_near(view) if any_behind else view
        if len(poly) < 3:
            return

        focal = cam.focal
        hw = self.w * 0.5
        hh = self.h * 0.5
        pts = []
        minx = miny = 1e9
        maxx = maxy = -1e9
        for px, py, pz in poly:
            s = focal / pz
            x = hw + px * s
            y = hh - py * s
            if x < -CLAMP_PX:
                x = -CLAMP_PX
            elif x > CLAMP_PX:
                x = CLAMP_PX
            if y < -CLAMP_PX:
                y = -CLAMP_PX
            elif y > CLAMP_PX:
                y = CLAMP_PX
            pts.append((int(x), int(y)))
            if x < minx:
                minx = x
            if x > maxx:
                maxx = x
            if y < miny:
                miny = y
            if y > maxy:
                maxy = y
        if maxx < 0 or minx > self.w or maxy < 0 or miny > self.h:
            return

        if depth > config.FOG_START:
            t = clamp((depth - config.FOG_START) / (config.FOG_END - config.FOG_START), 0.0, 1.0)
            fog = t * t * 0.55 + t * 0.45      # denser near the draw limit
            color = lerp_color(color, config.FOG_COLOR, fog)
        self.queue.append((depth, pts, color))

    def flush(self):
        surface = self.surface
        polygon = pygame.draw.polygon
        self.queue.sort(key=_sort_key, reverse=True)
        for _, pts, color in self.queue:
            polygon(surface, color, pts)
        # Cumulative within one frame: the scene is flushed more than once so
        # the ice can go down before anything standing on it.
        self.poly_count += len(self.queue)
        self.queue.clear()

    # -- backdrop --------------------------------------------------------
    def draw_sky(self):
        surface = self.surface
        w = self.w
        h = self.h
        horizon = h * 0.5 + self.cam.focal * math.tan(self.cam.pitch)
        if horizon > h + 4:
            horizon = h + 4
        if horizon < -4:
            horizon = -4

        bands = 26
        if horizon > 0:
            for i in range(bands):
                y0 = horizon * i / bands
                y1 = horizon * (i + 1) / bands
                t = i / (bands - 1.0)
                col = lerp_color(config.SKY_TOP, config.SKY_HORIZON, t * t * 0.75 + t * 0.25)
                pygame.draw.rect(surface, col, (0, int(y0), w, int(y1 - y0) + 2))

        self._draw_mountains(horizon)

        if horizon < h:
            span = h - horizon
            for i in range(bands):
                y0 = horizon + span * i / bands
                y1 = horizon + span * (i + 1) / bands
                t = i / (bands - 1.0)
                col = lerp_color(config.SNOW_FAR, config.SNOW_NEAR, t * t)
                pygame.draw.rect(surface, col, (0, int(y0), w, int(y1 - y0) + 2))

    def _draw_mountains(self, horizon):
        cam = self.cam
        w = self.w
        focal = cam.focal
        yaw = cam.yaw
        steps = 42
        for layer in (0, 1):
            col = (186, 202, 219) if layer == 0 else (197, 211, 226)
            amp = 118.0 if layer == 0 else 72.0
            seed_a = 91 + layer * 13
            seed_b = 37 + layer * 5
            pts = [(0, int(horizon) + 2)]
            for k in range(steps + 1):
                x = w * k / steps
                az = yaw + math.atan2(x - w * 0.5, focal)
                ca = math.cos(az)
                sa = math.sin(az)
                n = 0.58 * vnoise(ca * 3.1 + sa * 1.7 + 40.0 + layer * 7.0, seed_a) \
                    + 0.42 * vnoise(sa * 7.3 - ca * 4.1 + 12.0 + layer * 3.0, seed_b)
                hgt = amp * (0.22 + 0.78 * n) * (1.0 if layer == 0 else 0.82)
                pts.append((int(x), int(horizon - hgt)))
            pts.append((w, int(horizon) + 2))
            pygame.draw.polygon(self.surface, col, pts)


def _sort_key(item):
    return item[0]
