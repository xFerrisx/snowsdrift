"""Tunable constants. Everything that shapes the look and the handling lives here."""

# --- window / rendering ---------------------------------------------------
WIDTH = 1280
HEIGHT = 720
FPS = 60
FOV_DEG = 60.0             # vertical field of view

# Fog blends every polygon toward FOG_COLOR. Geometry past FOG_END is not drawn
# at all, which is what keeps the scene bounded no matter how far you ride.
FOG_START = 60.0
FOG_END = 470.0
FOG_COLOR = (203, 216, 229)

SKY_TOP = (74, 116, 168)
SKY_HORIZON = (203, 216, 229)
SNOW_FAR = (206, 219, 232)
SNOW_NEAR = (232, 237, 244)

ICE = (150, 178, 198)
ICE_SPREAD = 5             # per-station brightness jitter
BANK = (241, 247, 252)
BANK_SHADE = (222, 232, 242)
DASH = (126, 156, 178)
TREE_DARK = (43, 70, 62)
TREE_LIGHT = (236, 243, 249)
ROCK = (152, 173, 190)

# --- track streaming ------------------------------------------------------
STATION_STEP = 4.0         # metres between track samples
GEN_AHEAD = 160            # stations generated in front of the player
KEEP_BEHIND = 26           # stations kept behind the player, then discarded
RENDER_NEAR = 56           # stations drawn at full resolution (~224 m)
RENDER_MID = 92            # then every second station
RENDER_FAR = 118           # then every fourth station (~472 m)

# --- driving model --------------------------------------------------------
MAX_SPEED = 44.0           # m/s (~158 km/h) soft cap
ENGINE = 16.0              # m/s^2 of thrust at a standstill
BRAKE = 24.0
REVERSE_MAX = 9.0
COAST_DRAG = 0.55          # 1/s, applied to forward speed with no throttle
AIR_DRAG = 0.0016          # quadratic drag coefficient
GRIP_BASE = 1.85           # lateral grip on ice (1/s of lateral damping)
GRIP_THROTTLE_LOSS = 0.95  # full throttle -> power slide
STEER_RATE = 1.6           # rad/s at low speed
WALL_BOUNCE = 0.32
WALL_SPEED_LOSS = 0.84
