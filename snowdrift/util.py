"""Small helpers: deterministic noise, colour mixing, process memory."""

import math
import sys

MASK64 = (1 << 64) - 1


def hash01(*keys):
    """Deterministic float in [0, 1) from a tuple of integers.

    Used instead of random.Random so that any piece of the track can be
    re-derived from its station index alone - no history, no storage.
    """
    h = 0x9E3779B97F4A7C15
    for k in keys:
        k = int(k) & MASK64
        h = (h ^ ((k * 0xC2B2AE3D27D4EB4F) & MASK64)) & MASK64
        h = ((h ^ (h >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        h = ((h ^ (h >> 27)) * 0x94D049BB133111EB) & MASK64
        h ^= h >> 31
    return (h & 0xFFFFFF) / float(0x1000000)


def vnoise(x, seed=0):
    """Smooth 1D value noise in [0, 1]."""
    i = math.floor(x)
    f = x - i
    f = f * f * (3.0 - 2.0 * f)
    a = hash01(i, seed)
    b = hash01(i + 1, seed)
    return a + (b - a) * f


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def short_angle(a, b):
    """Signed shortest rotation from angle a to angle b."""
    return (b - a + math.pi) % (2.0 * math.pi) - math.pi


def rss_mb():
    """Resident set size of this process in megabytes (0.0 if unavailable)."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            handle = kernel32.GetCurrentProcess()
            if psapi.GetProcessMemoryInfo(
                wintypes.HANDLE(handle), ctypes.byref(counters), counters.cb
            ):
                return counters.WorkingSetSize / (1024.0 * 1024.0)
            return 0.0
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return usage / (1024.0 if sys.platform == "darwin" else 1024.0 * 1024.0)
    except Exception:
        return 0.0
