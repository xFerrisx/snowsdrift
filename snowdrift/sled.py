"""Arcade drift physics for the snowmobile.

The model is deliberately simple: forward/lateral velocity in the sled's own
frame, a low lateral grip that bleeds the sideways slip away slowly (that is
the drift), driven by engine force and a little air drag. Steering rotates the
heading but never rotates the velocity vector, so the nose leads into the
slide and you steer out of it the way you do on real ice.
"""

import math

from . import config
from .util import clamp, short_angle


class Sled:
    def __init__(self, track, index=0):
        st = track.get(index)
        self.x = st.x
        self.y = st.y + 0.02
        self.z = st.z
        self.psi = math.atan2(st.fx, st.fz)
        self.vx = 0.0
        self.vz = 0.0
        self.speed = 0.0
        self.drift = 0.0          # degrees of slip between nose and travel
        self.roll = 0.0
        self.pitch = 0.0
        self.station_i = index
        self.score = 0.0          # metres ridden forward = points
        self.bumps = 0

    def update(self, dt, throttle, brake, steer, track):
        fx = math.sin(self.psi)
        fz = math.cos(self.psi)
        rx = fz
        rz = -fx

        vf = self.vx * fx + self.vz * fz
        vr = self.vx * rx + self.vz * rz

        # --- engine / brake ------------------------------------------------
        if brake > 0.0:
            if vf > 0.6:
                vf -= config.BRAKE * dt
            elif vf > -config.REVERSE_MAX:
                vf -= config.ENGINE * 0.45 * dt
        elif throttle > 0.0:
            vf += throttle * config.ENGINE * max(0.0, 1.0 - max(vf, 0.0) / config.MAX_SPEED) * dt
        else:
            vf -= vf * config.COAST_DRAG * dt
        vf -= config.AIR_DRAG * vf * abs(vf) * dt

        # --- ice grip ------------------------------------------------------
        # Hard on the throttle = less grip = the slide holds. Easing off
        # straightens the sled up again.
        grip = config.GRIP_BASE - config.GRIP_THROTTLE_LOSS * throttle * clamp(
            abs(vf) / 10.0, 0.0, 1.0
        )
        if brake > 0.0:
            grip += 0.8
        # Past ~35 degrees of slip the edge bites and the slide washes off,
        # which keeps a big handful of throttle from turning into a spin.
        slip = abs(math.atan2(vr, max(abs(vf), 0.5)))
        if slip > 0.72:
            grip += 5.5 * (slip - 0.72)
        vr *= math.exp(-max(0.15, grip) * dt)

        # --- steering ------------------------------------------------------
        speed_f = clamp(abs(vf) / 6.0, 0.0, 1.0)
        turn = (
            steer
            * config.STEER_RATE
            * speed_f
            * (1.0 - 0.40 * clamp(abs(vf) / config.MAX_SPEED, 0.0, 1.0))
        )
        if abs(vr) > 4.0:
            turn *= 1.22                  # counter-steer helps when sideways
        if vf < -0.5:
            turn = -turn                  # reversing inverts the bars
        self.psi += turn * dt

        # Off the bars the sled straightens itself out of the slide instead of
        # spinning: feeding a little counter-steer is what makes it drivable.
        if abs(steer) < 0.35 and abs(vr) > 1.0:
            travel = math.atan2(self.vx, self.vz)
            self.psi += short_angle(self.psi, travel) * min(1.0, 1.8 * dt)

        # Velocity keeps its world direction; only its components changed.
        self.vx = fx * vf + rx * vr
        self.vz = fz * vf + rz * vr
        self.x += self.vx * dt
        self.z += self.vz * dt

        # --- stay on the ice ----------------------------------------------
        st, lateral, along = track.locate(self.x, self.z, self.station_i)
        self.station_i = st.i
        limit = st.w - 0.45
        if abs(lateral) > limit:
            side = 1.0 if lateral > 0.0 else -1.0
            over = abs(lateral) - limit
            self.x -= st.rx * side * over
            self.z -= st.rz * side * over
            wf = self.vx * st.fx + self.vz * st.fz
            wr = self.vx * st.rx + self.vz * st.rz
            if wr * side > 0.4:           # actually driving into the bank
                self.bumps += 1
                wf *= config.WALL_SPEED_LOSS
            wr = -wr * config.WALL_BOUNCE
            self.vx = st.fx * wf + st.rx * wr
            self.vz = st.fz * wf + st.rz * wr
            lateral = side * limit

        # Blend the two stations the sled sits between: the ice is drawn as
        # straight strips, so this keeps the sled planted on the surface
        # instead of popping up a step at every station boundary.
        self.y = track.height_at(along) + 0.02
        self.speed = math.hypot(self.vx, self.vz)
        # Slip is measured between the nose and the direction of travel - the
        # angle you actually see when the sled comes sideways.
        nfx = math.sin(self.psi)
        nfz = math.cos(self.psi)
        vf_local = self.vx * nfx + self.vz * nfz
        vr_local = self.vx * nfz - self.vz * nfx
        self.drift = math.degrees(math.atan2(vr_local, max(abs(vf_local), 0.4)))

        # --- lean / pitch ---------------------------------------------------
        target_roll = clamp(-vf * turn * 0.011, -0.30, 0.30) - self.drift * 0.0022
        self.roll += (clamp(target_roll, -0.36, 0.36) - self.roll) * (1.0 - math.exp(-9.0 * dt))
        slope = track.slope_at_along(along)
        target_pitch = clamp(-math.atan(slope) * 0.9, -0.22, 0.22)
        self.pitch += (target_pitch - self.pitch) * (1.0 - math.exp(-6.0 * dt))

        if along > self.score:
            self.score = along
