"""Infinitely streamed ice track.

The track is a ribbon swept along a path defined by two smooth noise fields:
one bends the path, one lifts it. Both are pure functions of the station
index, so the path is endless without ever storing it.

Memory stays flat because only a window of stations around the player exists:
new ones are generated in front, old ones are dropped behind (see
``TrackStream.prune``). Nothing else about the track is remembered.
"""

import math

from . import config
from .util import hash01, vnoise


class Station:
    """One cross-section of the track, 4 m from its neighbours."""

    __slots__ = (
        "i", "s", "x", "y", "z", "fx", "fz", "rx", "rz", "w",
        "ice", "bank", "trees",
    )


class TrackStream:
    def __init__(self, seed=1, start_i=0):
        self.seed = int(seed)
        self.stations = {}
        self.head_i = start_i - 40        # a little track behind the start line
        self._x = 0.0
        self._z = 0.0
        self._heading = 0.0
        self.start_i = start_i
        self.ensure(start_i + config.GEN_AHEAD)

    # -- generation ------------------------------------------------------
    def _curvature(self, i):
        n1 = vnoise(i / 9.0, self.seed + 1) * 2.0 - 1.0
        n2 = vnoise(i / 3.5, self.seed + 2) * 2.0 - 1.0
        # 0.017 1/m is roughly a 60 m radius hairpin - tight but drivable.
        return 0.0125 * n1 + 0.0045 * n2

    def _height(self, i):
        return 3.0 * (vnoise(i / 14.0, self.seed + 3) * 2.0 - 1.0) \
            + 1.0 * (vnoise(i / 5.0, self.seed + 4) * 2.0 - 1.0)

    def _trees(self, i, half_width):
        trees = []
        for slot in range(2):
            if hash01(i, slot, self.seed + 11) > 0.38:
                continue
            side = -1.0 if hash01(i, slot, 17) < 0.5 else 1.0
            off = half_width + 5.5 + 26.0 * hash01(i, slot, 23) ** 1.3
            size = 0.75 + 0.85 * hash01(i, slot, 29)
            kind = 0 if hash01(i, slot, 31) < 0.78 else 1
            trees.append((side * off, size, kind))
        return tuple(trees)

    def _make(self, i):
        step = config.STATION_STEP
        self._heading += self._curvature(i) * step
        hx = math.sin(self._heading)
        hz = math.cos(self._heading)
        self._x += hx * step
        self._z += hz * step

        st = Station()
        st.i = i
        st.s = (i - self.start_i) * step
        st.x = self._x
        st.y = self._height(i)
        st.z = self._z
        st.fx = hx
        st.fz = hz
        st.rx = hz
        st.rz = -hx
        st.w = 6.2 + 2.0 * vnoise(i * 0.06 + 31.7, self.seed + 5)

        tint = (hash01(i, 3, self.seed + 7) * 2.0 - 1.0) * config.ICE_SPREAD
        st.ice = (
            int(config.ICE[0] + tint),
            int(config.ICE[1] + tint * 0.8),
            int(config.ICE[2] + tint * 0.6),
        )
        shade = 0.5 + 0.5 * hash01(i, 5, self.seed + 9)
        st.bank = tuple(
            int(config.BANK_SHADE[k] + (config.BANK[k] - config.BANK_SHADE[k]) * shade)
            for k in range(3)
        )
        st.trees = self._trees(i, st.w)
        self.stations[i] = st
        return st

    def ensure(self, upto_i):
        """Generate stations until ``upto_i`` exists."""
        while self.head_i < upto_i:
            self.head_i += 1
            self._make(self.head_i)

    def prune(self, keep_from_i):
        """Drop every station older than ``keep_from_i`` (flat memory)."""
        for i in [k for k in self.stations if k < keep_from_i]:
            del self.stations[i]

    # -- queries ---------------------------------------------------------
    def get(self, i):
        return self.stations.get(i)

    def locate(self, x, z, hint_i):
        """Nearest station to (x, z) near ``hint_i``, plus lateral offset and s."""
        best_i = hint_i
        best_d2 = None
        for i in range(hint_i - 5, hint_i + 9):
            st = self.stations.get(i)
            if st is None:
                continue
            dx = x - st.x
            dz = z - st.z
            d2 = dx * dx + dz * dz
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_i = i
        st = self.stations.get(best_i)
        if st is None:
            st = self.stations[min(self.stations)]
        dx = x - st.x
        dz = z - st.z
        lateral = dx * st.rx + dz * st.rz
        along = st.s + dx * st.fx + dz * st.fz
        return st, lateral, along

    def slope_at(self, i):
        a = self.stations.get(i - 1)
        b = self.stations.get(i + 1)
        if a is None or b is None:
            return 0.0
        return (b.y - a.y) / (2.0 * config.STATION_STEP)
