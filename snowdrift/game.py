"""The game: input, physics stepping, scene assembly and the HUD."""

import math
import random

import pygame

from . import config
from .hud import HUD
from .particles import Spray
from .renderer import NEAR, Renderer
from .sled import Sled
from .track import TrackStream
from .util import clamp, hash01, lerp_color, rss_mb

BANK_RISE = 1.55
BANK_WIDTH = 3.4

# Local-space sled mesh: (vertices, colour). +z forward, +y up, origin on the
# snow between the skis. Only faces a chase camera can see are included.
_BODY = (206, 74, 52)
_BODY_DARK = (168, 54, 40)
_SEAT = (40, 46, 60)
_GLASS = (172, 208, 226)
_METAL = (74, 82, 92)
_RIDER = (48, 60, 92)
_HELMET = (236, 240, 246)


def _box(x0, x1, y0, y1, z0, z1, top, side, back=None):
    quads = [
        ((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)),   # top
        ((x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (x0, y0, z0)),   # left
        ((x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0)),   # right
    ]
    colors = [top, side, side]
    if back is not None:
        quads.append(((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)))
        colors.append(back)
    return list(zip(quads, colors))


def _build_mesh():
    parts = []
    parts += _box(-0.34, 0.34, 0.26, 0.66, -1.20, 0.55, _BODY, _BODY_DARK, _SEAT)
    # nose wedge
    parts.append((((-0.32, 0.66, 0.55), (0.32, 0.66, 0.55), (0.22, 0.30, 1.45), (-0.22, 0.30, 1.45)), _BODY))
    parts.append((((-0.32, 0.26, 0.55), (-0.22, 0.30, 1.45), (0.22, 0.30, 1.45), (0.32, 0.26, 0.55)), _BODY_DARK))
    # seat
    parts += _box(-0.22, 0.22, 0.66, 0.86, -1.00, 0.18, _SEAT, _SEAT)
    # windshield
    parts.append((((-0.26, 0.66, 0.52), (0.26, 0.66, 0.52), (0.17, 1.04, 0.26), (-0.17, 1.04, 0.26)), _GLASS))
    # skis and struts
    for side in (-1.0, 1.0):
        x = side * 0.46
        parts += _box(x - 0.06, x + 0.06, 0.0, 0.10, 0.35, 1.55, _METAL, _METAL)
        parts.append((((x - 0.06, 0.0, 1.55), (x + 0.06, 0.0, 1.55), (x + 0.02, 0.20, 1.82), (x - 0.02, 0.20, 1.82)), _METAL))
        parts.append((((x - 0.03, 0.10, 0.95), (x + 0.03, 0.10, 0.95), (x + 0.03, 0.30, 0.85), (x - 0.03, 0.30, 0.85)), _BODY_DARK))
    # handlebar
    parts.append((((-0.40, 1.00, 0.44), (0.40, 1.00, 0.44), (0.40, 1.00, 0.52), (-0.40, 1.00, 0.52)), _METAL))
    # rider
    parts += _box(-0.19, 0.19, 0.86, 1.38, -0.42, 0.06, _RIDER, _RIDER)
    parts += _box(-0.14, 0.14, 1.38, 1.66, -0.30, 0.02, _HELMET, _HELMET, _HELMET)
    return parts


SLED_MESH = _build_mesh()


class Game:
    def __init__(self, surface, seed=None, stats=False):
        self.surface = surface
        self.w, self.h = surface.get_size()
        self.renderer = Renderer(surface)
        self.hud = HUD(self.w, self.h)
        self.stats = stats
        self.state = "title"
        self.fps = 60.0
        self.mem = 0.0
        self._mem_timer = 0.0
        self.seed = random.randrange(1, 1 << 30) if seed is None else int(seed)
        self.reset(self.seed)

    # -- lifecycle -------------------------------------------------------
    def reset(self, seed):
        self.seed = seed
        self.track = TrackStream(seed)
        self.sled = Sled(self.track)
        self.spray = Spray()
        self.cam_pos = [self.sled.x, self.sled.y + 4.4, self.sled.z - 9.6]
        self.cam_look = [self.sled.x, self.sled.y + 1.5, self.sled.z + 7.0]
        self.shake = 0.0
        self.last_bumps = 0
        self._bump_cool = 0.0
        self._render_dir = 1

    def handle_event(self, event):
        """Returns False when the window should close."""
        if event.type != pygame.KEYDOWN:
            return True
        key = event.key
        if key == pygame.K_ESCAPE:
            if self.state == "play":
                self.state = "paused"
                return True
            return False
        if key == pygame.K_p:
            if self.state == "play":
                self.state = "paused"
            elif self.state == "paused":
                self.state = "play"
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.state == "title":
                self.reset(random.randrange(1, 1 << 30))
                self.state = "play"
            elif self.state == "paused":
                self.state = "play"
        elif key == pygame.K_r and self.state in ("play", "paused"):
            self.reset(random.randrange(1, 1 << 30))
            self.state = "play"
        return True

    # -- simulation ------------------------------------------------------
    def update(self, dt):
        if dt <= 0.0:
            dt = 1e-4
        self.fps = self.fps * 0.92 + (1.0 / dt) * 0.08
        self._mem_timer -= dt
        if self._mem_timer <= 0.0:
            self.mem = rss_mb()
            self._mem_timer = 1.0

        if self.state == "play":
            keys = pygame.key.get_pressed()
            throttle = 1.0 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0.0
            brake = 1.0 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0.0
            steer = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                steer -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                steer += 1.0
            self._step_physics(dt, throttle, brake, steer)
            self._update_spray(dt, throttle)
        self._update_camera(dt)

    def _step_physics(self, dt, throttle, brake, steer):
        steps = max(1, min(6, int(dt * 120.0) + 1))
        sub = dt / steps
        for _ in range(steps):
            self.sled.update(sub, throttle, brake, steer, self.track)

        # The road is grown both ways from the player, so spinning round and
        # riding back never runs off the end of the generated ice.
        cur = self.sled.station_i
        self.track.ensure(cur - config.GEN_BEHIND, cur + config.GEN_AHEAD)
        self.track.prune(cur - config.GEN_BEHIND, cur + config.GEN_AHEAD)

        self._bump_cool = max(0.0, self._bump_cool - dt)
        if self.sled.bumps != self.last_bumps:
            self.last_bumps = self.sled.bumps
            if self._bump_cool <= 0.0:
                self.shake = min(0.9, self.shake + 0.32)
                self._bump_cool = 0.16

    def _update_spray(self, dt, throttle):
        sled = self.sled
        self.spray.update(dt)
        slip = abs(sled.drift)
        if (slip > 10.0 and sled.speed > 4.0) or (throttle > 0.0 and sled.speed > 10.0):
            intensity = clamp(slip / 45.0 + sled.speed / config.MAX_SPEED * 0.55, 0.0, 1.0)
            count = int(1 + 5 * intensity)
            fx = math.sin(sled.psi)
            fz = math.cos(sled.psi)
            self.spray.emit_burst(
                sled.x - fx * 1.25, sled.y + 0.1, sled.z - fz * 1.25,
                -fx, -fz, count, 0.6 + intensity,
            )

    # -- camera ----------------------------------------------------------
    def _update_camera(self, dt):
        sled = self.sled
        fx = math.sin(sled.psi)
        fz = math.cos(sled.psi)
        speed = sled.speed
        if speed > 2.0:
            vx = sled.vx / speed
            vz = sled.vz / speed
            blend = clamp(speed / 16.0, 0.0, 1.0) * 0.6
            bx = fx * (1.0 - blend) + vx * blend
            bz = fz * (1.0 - blend) + vz * blend
            n = math.hypot(bx, bz)
            if n > 1e-3:
                bx /= n
                bz /= n
            else:
                bx, bz = fx, fz
        else:
            bx, bz = fx, fz

        dist = 8.4 + 0.032 * speed
        height = 3.7 + 0.012 * speed
        target = (sled.x - bx * dist, sled.y + height, sled.z - bz * dist)
        look = (sled.x + fx * 6.0, sled.y + 1.5, sled.z + fz * 6.0)

        k1 = 1.0 - math.exp(-7.5 * dt)
        k2 = 1.0 - math.exp(-10.0 * dt)
        for i in range(3):
            self.cam_pos[i] += (target[i] - self.cam_pos[i]) * k1
            self.cam_look[i] += (look[i] - self.cam_look[i]) * k2

        self.shake = max(0.0, self.shake - dt * 3.2)
        sh = self.shake * 0.30
        px = self.cam_pos[0] + random.uniform(-sh, sh)
        py = self.cam_pos[1] + random.uniform(-sh, sh)
        pz = self.cam_pos[2] + random.uniform(-sh, sh)

        ox = self.cam_look[0] - px
        oy = self.cam_look[1] - py
        oz = self.cam_look[2] - pz
        horiz = math.hypot(ox, oz)
        yaw = math.atan2(ox, oz)
        pitch = math.atan2(oy, max(horiz, 1e-4))
        self.renderer.cam.set((px, py, pz), yaw, clamp(pitch, -1.2, 0.7))

    # -- drawing ---------------------------------------------------------
    def draw(self):
        r = self.renderer
        if r.surface is not self.surface:
            r = Renderer(self.surface)
            self.renderer = r
        r.w, r.h = self.surface.get_size()
        r.draw_sky()
        self._draw_track(r)
        self._draw_sled(r)
        r.flush()
        self._draw_spray(r)
        self._draw_hud()

    def _view_dir(self, cur):
        """+1 if the camera looks along increasing stations, -1 if back.

        With a dead zone, so a sideways drift does not flip the whole track
        between frames and make it pop.
        """
        st = self.track.get(cur)
        if st is not None:
            cam = self.renderer.cam
            dot = cam.fx * st.fx + cam.fz * st.fz
            if dot > 0.2:
                self._render_dir = 1
            elif dot < -0.2:
                self._render_dir = -1
        return self._render_dir

    def _station_indices(self, cur):
        """Stations to draw, walking out in whichever way the camera faces.

        LOD steps get coarser with distance in that direction, so the far view
        is as long behind the sled as it is in front of it.
        """
        d = self._view_dir(cur)
        offs = []
        off = -4
        while off <= config.RENDER_NEAR:
            offs.append(off)
            off += 1
        while off <= config.RENDER_MID:
            offs.append(off)
            off += 2
        while off <= config.RENDER_FAR:
            offs.append(off)
            off += 4
        offs.append(config.RENDER_FAR)
        return [cur + d * o for o in offs]

    def _draw_track(self, r):
        track = self.track
        cur = self.sled.station_i
        stations = []
        for i in self._station_indices(cur):
            st = track.get(i)
            if st is not None:
                stations.append(st)

        add = r.add
        for a, b in zip(stations, stations[1:]):
            alx = a.x - a.rx * a.w
            alz = a.z - a.rz * a.w
            arx = a.x + a.rx * a.w
            arz = a.z + a.rz * a.w
            blx = b.x - b.rx * b.w
            blz = b.z - b.rz * b.w
            brx = b.x + b.rx * b.w
            brz = b.z + b.rz * b.w

            add(((alx, a.y, alz), (arx, a.y, arz), (brx, b.y, brz), (blx, b.y, blz)), a.ice)

            if a.i % 6 == 0:
                dx = a.rx * 0.30
                dz = a.rz * 0.30
                cax = a.x + (b.x - a.x) * 0.25
                caz = a.z + (b.z - a.z) * 0.25
                cbx = a.x + (b.x - a.x) * 0.7
                cbz = a.z + (b.z - a.z) * 0.7
                ay = a.y + 0.03
                by = b.y + 0.03
                add(
                    ((cax - dx, ay, caz - dz), (cax + dx, ay, caz + dz),
                     (cbx + dx, by, cbz + dz), (cbx - dx, by, cbz - dz)),
                    config.DASH,
                )

            if a.i % 7 == 0:
                l0 = (hash01(a.i, 41, track.seed) * 2.0 - 1.0) * a.w * 0.75
                l1 = l0 + (hash01(a.i, 43, track.seed) - 0.5) * a.w * 0.5
                gy = a.y + 0.02
                f = 0.18
                p0 = (a.x + a.rx * l0, gy, a.z + a.rz * l0)
                p1 = (a.x + a.rx * l1, gy, a.z + a.rz * l1)
                add(
                    (p0, p1,
                     (p1[0] + a.fx * f, gy, p1[2] + a.fz * f),
                     (p0[0] + a.fx * f, gy, p0[2] + a.fz * f)),
                    (134, 160, 180),
                )

            aoff = a.w + BANK_WIDTH
            boff = b.w + BANK_WIDTH
            aox = a.x - a.rx * aoff
            aoz = a.z - a.rz * aoff
            box = b.x - b.rx * boff
            boz = b.z - b.rz * boff
            add(
                ((alx, a.y + 0.05, alz), (aox, a.y + BANK_RISE, aoz),
                 (box, b.y + BANK_RISE, boz), (blx, b.y + 0.05, blz)),
                a.bank,
            )

            aox = a.x + a.rx * aoff
            aoz = a.z + a.rz * aoff
            box = b.x + b.rx * boff
            boz = b.z + b.rz * boff
            add(
                ((arx, a.y + 0.05, arz), (aox, a.y + BANK_RISE, aoz),
                 (box, b.y + BANK_RISE, boz), (brx, b.y + 0.05, brz)),
                a.bank,
            )

        for st in stations:
            if not st.trees or abs(st.i - cur) > 80:
                continue
            for off, size, kind in st.trees:
                self._add_tree(r, st.x + st.rx * off, st.y, st.z + st.rz * off, size, kind)

    def _add_tree(self, r, x, y, z, size, kind):
        cam = r.cam
        rx = cam.rx
        rz = cam.rz
        depth = cam.depth((x, y, z))
        if depth < NEAR or depth > config.FOG_END:
            return
        if kind == 0:
            h = 5.8 * size
            wd = 1.85 * size
            r.add(
                ((x - rx * 0.16, y, z - rz * 0.16), (x + rx * 0.16, y, z + rz * 0.16),
                 (x + rx * 0.12, y + h * 0.30, z + rz * 0.12), (x - rx * 0.12, y + h * 0.30, z - rz * 0.12)),
                (62, 48, 42), depth,
            )
            r.add(
                ((x - rx * wd, y + h * 0.22, z - rz * wd), (x + rx * wd, y + h * 0.22, z + rz * wd),
                 (x, y + h * 0.78, z)),
                config.TREE_DARK, depth,
            )
            r.add(
                ((x - rx * wd * 0.55, y + h * 0.52, z - rz * wd * 0.55),
                 (x + rx * wd * 0.55, y + h * 0.52, z + rz * wd * 0.55),
                 (x, y + h, z)),
                config.TREE_LIGHT, depth,
            )
        else:
            h = 1.6 * size
            wd = 1.5 * size
            r.add(
                ((x - rx * wd, y, z - rz * wd), (x + rx * wd, y, z + rz * wd),
                 (x + rx * wd * 0.55, y + h, z + rz * wd * 0.55),
                 (x - rx * wd * 0.55, y + h, z - rz * wd * 0.55)),
                config.ROCK, depth,
            )
            r.add(
                ((x - rx * wd * 0.55, y + h, z - rz * wd * 0.55),
                 (x + rx * wd * 0.55, y + h, z + rz * wd * 0.55),
                 (x, y + h * 1.12, z)),
                (232, 240, 247), depth,
            )

    def _draw_sled(self, r):
        s = self.sled
        cp = math.cos(s.pitch)
        sp = math.sin(s.pitch)
        cr = math.cos(s.roll)
        sr = math.sin(s.roll)
        cy = math.cos(s.psi)
        sy = math.sin(s.psi)
        base_depth = r.cam.depth((s.x, s.y, s.z))
        # A soft contact shadow keeps the sled planted on the ice.
        shadow = []
        for lx, lz in ((-0.85, -2.0), (0.85, -2.0), (1.15, 0.1),
                       (0.70, 1.9), (-0.70, 1.9), (-1.15, 0.1)):
            shadow.append((s.x + lx * cy + lz * sy, s.y + 0.03, s.z - lx * sy + lz * cy))
        r.add(tuple(shadow), (128, 154, 176), base_depth + 0.5)

        for verts, color in SLED_MESH:
            out = []
            for x, y, z in verts:
                x1 = x * cr - y * sr
                y1 = x * sr + y * cr
                y2 = y1 * cp - z * sp
                z2 = y1 * sp + z * cp
                wx = x1 * cy + z2 * sy
                wz = -x1 * sy + z2 * cy
                out.append((s.x + wx, s.y + y2, s.z + wz))
            r.add(out, color, base_depth)

    def _draw_spray(self, r):
        cam = r.cam
        surface = r.surface
        focal = cam.focal
        hw = self.w * 0.5
        hh = self.h * 0.5
        spray = self.spray
        circle = pygame.draw.circle
        for i in range(spray.count):
            if spray.life[i] <= 0.0:
                continue
            dx = spray.px[i] - cam.x
            dy = spray.py[i] - cam.y
            dz = spray.pz[i] - cam.z
            z = dx * cam.fx + dy * cam.fy + dz * cam.fz
            if z < 0.5 or z > 80.0:
                continue
            cx = dx * cam.rx + dz * cam.rz
            cy = dx * cam.ux + dy * cam.uy + dz * cam.uz
            radius = focal * spray.size[i] / z
            if radius < 0.7:
                continue
            if radius > 26.0:
                radius = 26.0
            x = hw + cx * focal / z
            y = hh - cy * focal / z
            col = lerp_color((252, 253, 255), config.FOG_COLOR, min(1.0, z / 70.0) * 0.8)
            circle(surface, col, (int(x), int(y)), int(radius))

    def _draw_hud(self):
        hud = self.hud
        surf = self.surface
        stats_text = None
        if self.stats:
            stats_text = [
                f"fps {self.fps:5.1f}   polys {self.renderer.poly_count:4d}",
                f"rss {self.mem:6.1f} MB   stations {len(self.track.stations)}",
                f"seed {self.seed}",
            ]
        if self.state == "title":
            hud.draw_title(surf)
        else:
            hud.draw_play(
                surf,
                self.sled.score,
                self.sled.speed * 3.6,
                self.sled.drift,
                stats_text,
            )
            if self.state == "paused":
                hud.draw_pause(surf)
