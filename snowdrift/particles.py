"""Fixed-size snow spray pool.

Two hundred particles are allocated once at start-up and recycled through a
ring index, so the spray can never grow the process.
"""

import random


class Spray:
    def __init__(self, count=200):
        self.count = count
        self.px = [0.0] * count
        self.py = [0.0] * count
        self.pz = [0.0] * count
        self.vx = [0.0] * count
        self.vy = [0.0] * count
        self.vz = [0.0] * count
        self.life = [0.0] * count
        self.size = [0.0] * count
        self.head = 0

    def emit(self, x, y, z, vx, vy, vz, size, life):
        i = self.head
        self.head = (i + 1) % self.count
        self.px[i] = x
        self.py[i] = y
        self.pz[i] = z
        self.vx[i] = vx
        self.vy[i] = vy
        self.vz[i] = vz
        self.size[i] = size
        self.life[i] = life

    def update(self, dt):
        drag = 1.0 - min(0.5, 2.4 * dt)
        for i in range(self.count):
            if self.life[i] <= 0.0:
                continue
            self.life[i] -= dt
            self.vy[i] -= 7.5 * dt
            self.vx[i] *= drag
            self.vz[i] *= drag
            self.px[i] += self.vx[i] * dt
            self.py[i] += self.vy[i] * dt
            self.pz[i] += self.vz[i] * dt
            self.size[i] *= 1.0 + 1.4 * dt

    def emit_burst(self, x, y, z, back_x, back_z, count, power):
        """Kick snow off the track. ``back_*`` is the backwards heading."""
        for _ in range(count):
            side = random.uniform(-1.0, 1.0)
            forward = random.uniform(0.4, 2.2) * power
            spread = random.uniform(0.8, 2.6) * power
            self.emit(
                x + random.uniform(-0.3, 0.3),
                y + random.uniform(0.0, 0.35),
                z + random.uniform(-0.3, 0.3),
                back_x * forward + back_z * side * spread,
                random.uniform(0.6, 2.6) * power,
                back_z * forward - back_x * side * spread,
                random.uniform(0.03, 0.075),
                random.uniform(0.3, 0.7),
            )
