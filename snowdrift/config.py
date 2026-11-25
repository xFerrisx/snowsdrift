"""Tunable constants. Looks live in themes.py; this file is feel and budget."""

# --- window / rendering ---------------------------------------------------
WIDTH = 1280
HEIGHT = 720
FPS = 60
FOV_DEG = 60.0             # vertical field of view

# Fog blends every polygon toward the theme's fog colour. Geometry past
# FOG_END is not drawn at all, which is what keeps the scene bounded.
FOG_START = 60.0
FOG_END = 470.0

# --- track streaming ------------------------------------------------------
STATION_STEP = 4.0         # metres between track samples
GEN_AHEAD = 160            # stations generated in front of the player
GEN_BEHIND = 160           # ...and behind, so turning round never shows a void
RENDER_NEAR = 56           # stations drawn at full resolution (~224 m)
RENDER_MID = 92            # then every second station
RENDER_FAR = 118           # then every fourth station (~472 m)

# --- driving model --------------------------------------------------------
MAX_SPEED = 88.0           # m/s soft cap; settles around 300 km/h
ENGINE = 32.0              # m/s^2 of thrust at a standstill
BRAKE = 34.0
REVERSE_MAX = 9.0
COAST_DRAG = 0.55          # 1/s, applied to forward speed with no throttle
AIR_DRAG = 0.00018         # quadratic drag coefficient
GRIP_BASE = 1.85           # lateral grip on ice (1/s of lateral damping)
GRIP_THROTTLE_LOSS = 0.95  # full throttle -> power slide
STEER_RATE = 2.1           # rad/s at low speed
WALL_BOUNCE = 0.32
WALL_SPEED_LOSS = 0.84
