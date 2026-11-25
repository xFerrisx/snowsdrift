"""Infinitely streamed ice track.

The path is a ribbon swept along a path defined by two smooth noise fields:
one bends the path, one lifts it. Both are pure functions of the station
index, so the path is endless without ever storing it.

Stations are grown outward from whichever part of the window already exists -
forwards, backwards, or both - so the ice is always there whether you are
riding on or have spun round and headed back the way you came. Memory stays
flat because only a bounded window around the player exists: new stations are
generated at both ends and old ones are dropped at both ends (see
``TrackStream.prune``). Everything else about the track is re-derived from the
index, so a pruned stretch comes back identical if you ride into it again.
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
        self.start_i = int(start_i)
        self.stations = {}
        self._fill(self.start_i, 0.0, 0.0, 0.0)
        self.head_i = self.start_i
        self.tail_i = self.start_i
        self.ensure(
            self.start_i - config.GEN_BEHIND,
            self.start_i + config.GEN_AHEAD,
        )

    # -- generation ------------------------------------------------------
    def _curvature(self, i):
        # Wavelengths of ~88 m and ~32 m. Short ripples here read as a
        # wobbling, glitchy road, so the shortest octave stays long.
        n1 = vnoise(i / 22.0, self.seed + 1) * 2.0 - 1.0
        n2 = vnoise(i / 8.0, self.seed + 2) * 2.0 - 1.0
        # 0.016 1/m is roughly a 60 m radius hairpin - tight but drivable.
        return 0.0125 * n1 + 0.0035 * n2

    def _height(self, i):
        # 120 m and 44 m swells, about 4 degrees at their steepest. The old
        # 20 m octave made the sled porpoise hard enough to feel broken.
        return 2.2 * (vnoise(i / 30.0, self.seed + 3) * 2.0 - 1.0) \
            + 0.75 * (vnoise(i / 11.0, self.seed + 4) * 2.0 - 1.0)

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

    def _fill(self, i, x, z, heading):
        st = Station()
        st.i = i
        st.s = (i - self.start_i) * config.STATION_STEP
        st.x = x
        st.y = self._height(i)
        st.z = z
        hx = math.sin(heading)
        hz = math.cos(heading)
        st.fx = hx
        st.fz = hz
        st.rx = hz
        st.rz = -hx
        st.w = 6.2 + 2.0 * vnoise(i * 0.06 + 31.7, self.seed + 5)

        # Smooth drifts of shade rather than a fresh random tint every 4 m -
        # per-station jitter shimmered as the strips scrolled past.
        tint = (vnoise(i * 0.12, self.seed + 7) * 2.0 - 1.0) * config.ICE_SPREAD
        st.ice = (
            int(config.ICE[0] + tint),
            int(config.ICE[1] + tint * 0.8),
            int(config.ICE[2] + tint * 0.6),
        )
        shade = 0.5 + 0.5 * vnoise(i * 0.15, self.seed + 9)
        st.bank = tuple(
            int(config.BANK_SHADE[k] + (config.BANK[k] - config.BANK_SHADE[k]) * shade)
            for k in range(3)
        )
        st.trees = self._trees(i, st.w)
        self.stations[i] = st
        return st

    def _extend_up(self):
        """Add the station after ``head_i``, continuing the sweep forwards."""
        step = config.STATION_STEP
        below = self.stations[self.head_i]
        i = self.head_i + 1
        heading = math.atan2(below.fx, below.fz) + self._curvature(i) * step
        self._fill(
            i,
            below.x + math.sin(heading) * step,
            below.z + math.cos(heading) * step,
            heading,
        )
        self.head_i = i

    def _extend_down(self):
        """Add the station before ``tail_i``, running the sweep backwards.

        This is the exact inverse of ``_extend_up``: the step into station
        ``i + 1`` used the heading at ``i + 1``, so unwinding it reproduces
        the same path to within rounding.
        """
        step = config.STATION_STEP
        above = self.stations[self.tail_i]
        i = self.tail_i - 1
        heading = math.atan2(above.fx, above.fz) - self._curvature(above.i) * step
        self._fill(i, above.x - above.fx * step, above.z - above.fz * step, heading)
        self.tail_i = i

    def ensure(self, lo_i, hi_i):
        """Generate stations until the stream covers [lo_i, hi_i]."""
        guard = 0
        while self.head_i < hi_i and guard < 20000:
            self._extend_up()
            guard += 1
        while self.tail_i > lo_i and guard < 40000:
            self._extend_down()
            guard += 1

    def prune(self, lo_i, hi_i):
        """Drop every station outside [lo_i, hi_i] (flat memory)."""
        stations = self.stations
        drop = [k for k in stations if k < lo_i or k > hi_i]
        if not drop:
            return
        for k in drop:
            del stations[k]
        if not stations:
            return
        if self.tail_i <= lo_i:
            self.tail_i = min(stations)
        if self.head_i >= hi_i:
            self.head_i = max(stations)

    # -- queries ---------------------------------------------------------
    def get(self, i):
        return self.stations.get(i)

    def locate(self, x, z, hint_i):
        """Nearest station to (x, z) near ``hint_i``, plus lateral offset and s."""
        best_i = None
        best_d2 = None
        for i in range(hint_i - 6, hint_i + 7):
            st = self.stations.get(i)
            if st is None:
                continue
            dx = x - st.x
            dz = z - st.z
            d2 = dx * dx + dz * dz
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_i = i
        if best_i is None:
            if not self.stations:
                raise RuntimeError("track window is empty")
            best_i = min(self.stations, key=lambda k: abs(k - hint_i))
        st = self.stations[best_i]
        dx = x - st.x
        dz = z - st.z
        lateral = dx * st.rx + dz * st.rz
        along = st.s + dx * st.fx + dz * st.fz
        return st, lateral, along

    def height_at(self, along):
        """Smooth surface height at a distance along the track.

        The ice is drawn as straight strips between stations, so blending the
        two ends puts the sled exactly on the surface instead of snapping it
        up and down by up to half a station every 4 m.
        """
        fi = along / config.STATION_STEP + self.start_i
        i0 = math.floor(fi)
        a = self.stations.get(i0)
        b = self.stations.get(i0 + 1)
        if a is not None and b is not None:
            return a.y + (b.y - a.y) * (fi - i0)
        st = a if a is not None else b
        if st is None:
            st = self.stations.get(int(round(fi)))
        if st is None and self.stations:
            st = self.stations[min(self.stations, key=lambda k: abs(k - fi))]
        return st.y if st is not None else 0.0

    def slope_at_along(self, along, span=7.0):
        """Surface gradient along the track, measured over a wide baseline."""
        return (self.height_at(along + span) - self.height_at(along - span)) / (2.0 * span)
