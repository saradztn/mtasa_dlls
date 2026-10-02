# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# city.py - the plan of District Zero (city frame: origin = centre of the central park, +x east, +y north, metres)
#   3x3 blocks [70,120,70] m separated by 20 m streets (4 m sidewalk + 12 m roadway + 4 m sidewalk), 340 m square.
#   Vectorised cell classification + height fields used by ground.py and by the layout.
# -----------------------------------------------------------------------------
import numpy as np
from lib import noise as nz

HALF = 170
STREETS = [-160.0, -70.0, 70.0, 160.0]        # street centre lines (both axes)
BLOCKS = [(-150.0, -80.0), (-60.0, 60.0), (80.0, 150.0)]   # block extents along one axis
ROAD_HW, WALK_HW = 6.0, 10.0
Z_WALK = 0.15
Z_OUT = -0.25                                 # outside the map (flush with the real terrain)
PARK = (-60.0, 60.0)

# class ids
OUT, ROAD_NS, ROAD_EW, INTER, CROSS_NS, CROSS_EW, WALK, LOT, PARKG = range(9)
NAMES = ['out', 'road_ns', 'road_ew', 'inter', 'cross_ns', 'cross_ew', 'walk', 'lot', 'park']

LAKE_C = (-8.0, 10.0)
LAKE_R = (27.0, 20.0)
LAKE_Z = -1.5            # water level (local)


def _near(v, centres):
    """distance to nearest street centre + its index"""
    c = np.array(centres)
    d = v[..., None] - c
    k = np.abs(d).argmin(-1)
    return np.take_along_axis(d, k[..., None], -1)[..., 0], k


def classify(x, y):
    """x, y arrays of cell centres -> class array and (dx, dy) offsets to the nearest NS / EW street centre"""
    dx, kx = _near(x, STREETS)
    dy, ky = _near(y, STREETS)
    inx = np.abs(dx) <= WALK_HW
    iny = np.abs(dy) <= WALK_HW
    c = np.full(x.shape, LOT, np.int8)
    ax, ay = np.abs(dx), np.abs(dy)
    # NS street only
    m = inx & ~iny
    c[m & (ax <= ROAD_HW)] = ROAD_NS
    c[m & (ax > ROAD_HW)] = WALK
    m = iny & ~inx
    c[m & (ay <= ROAD_HW)] = ROAD_EW
    c[m & (ay > ROAD_HW)] = WALK
    m = inx & iny
    c[m & (ax > ROAD_HW) & (ay > ROAD_HW)] = WALK
    c[m & (ax <= ROAD_HW) & (ay <= ROAD_HW)] = INTER
    c[m & (ax <= ROAD_HW) & (ay > ROAD_HW)] = CROSS_NS     # crosswalk across the N-S roadway
    c[m & (ay <= ROAD_HW) & (ax > ROAD_HW)] = CROSS_EW
    park = (np.abs(x) < PARK[1]) & (np.abs(y) < PARK[1])
    c[park & (c == LOT)] = PARKG
    c[(np.abs(x) > HALF) | (np.abs(y) > HALF)] = OUT
    return c, dx, dy, kx, ky


# ----------------------------------------------------------------------------------- height fields
_SINKS = [(-70.0, -22.0, 4.5, 0.9), (70.0, 41.0, 3.8, 0.7), (-31.0, 160.0 - 160.0 + 70.0, 3.0, 0.5), (22.0, -160.0, 4.0, 0.8),
          (160.0, 20.0, 3.5, 0.6), (-160.0, 75.0, 3.2, 0.7), (-70.0, 128.0, 4.2, 0.9), (48.0, 70.0, 3.0, 0.6), (-100.0, -70.0, 3.0, 0.6),
          (70.0, -110.0, 3.4, 0.7)]


def road_dz(x, y):
    """sinkholes / heaved asphalt on roadway cells (negative = subsidence)"""
    z = np.zeros_like(x, dtype=float)
    for cx, cy, r, d in _SINKS:
        z -= d * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * (r * 0.55) ** 2))
    # soft long-wave undulation + heave ridges
    z += 0.12 * np.sin(x * 0.11 + 1.3) * np.cos(y * 0.09) * _smooth(-0.1, 0.4, np.sin(x * 0.043 + y * 0.037))
    return np.sign(z) * np.maximum(np.abs(z) - 0.03, 0.0)       # exactly flat where the road is undisturbed


def _smooth(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _field(seed, sx, sy):
    """cheap smooth value noise on arbitrary coordinate arrays (sum of sines, deterministic)"""
    r = np.random.default_rng(seed)
    z = np.zeros_like(sx, dtype=float)
    for _ in range(6):
        a, b = r.uniform(0.02, 0.12), r.uniform(0.02, 0.12)
        z += np.sin(sx * a * np.cos(b * 40) + sy * a * np.sin(b * 40) + r.uniform(0, 6.28)) * r.uniform(0.3, 1.0)
    return z / 3.0


_MOUNDS = [(-120.0, -110.0, 7.0, 0.7), (112.0, -118.0, 6.0, 0.6), (-118.0, 112.0, 8.0, 0.8), (118.0, 112.0, 7.0, 0.7),
           (-112.0, 8.0, 6.0, 0.5), (116.0, -6.0, 7.0, 0.6), (-4.0, -112.0, 6.0, 0.6), (8.0, 118.0, 6.0, 0.5)]


def lot_height(x, y):
    """lots are flat (merged into big rectangles) except for a few overgrown mounds of fallen debris"""
    z = np.zeros_like(x, dtype=float)
    for cx, cy, r, a in _MOUNDS:
        z += a * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * (r * 0.5) ** 2))
    return 0.10 + np.maximum(z - 0.03, 0.0)


def park_height(x, y):
    """rolling park terrain with the lake bowl; blends to the sidewalk level at the park edge"""
    h = 0.55 * _field(7101, x, y) + 0.25 * _field(7102, x * 2.1, y * 1.9)
    # knolls
    for cx, cy, r, a in ((40, 32, 16, 1.6), (-40, -34, 18, 1.8), (30, -40, 12, 1.0), (-46, 38, 10, 1.1)):
        h += a * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * (r * 0.6) ** 2))
    # lake bowl
    q = np.sqrt(((x - LAKE_C[0]) / LAKE_R[0]) ** 2 + ((y - LAKE_C[1]) / LAKE_R[1]) ** 2)
    bowl = _smooth(1.15, 0.45, q)
    h = h * (1 - bowl) + (LAKE_Z - 1.3 + 1.2 * _smooth(0.0, 0.45, q)) * bowl
    # edge blend
    e = np.minimum(PARK[1] - np.abs(x), PARK[1] - np.abs(y))
    w = _smooth(0.0, 7.0, e)
    return Z_WALK * (1 - w) + h * w


def corner_heights(cls, x, y):
    """height of every vertex position (x, y) for a given class code (array-wise)"""
    if cls in (ROAD_NS, ROAD_EW, INTER, CROSS_NS, CROSS_EW):
        return road_dz(x, y)
    if cls == WALK:
        return np.full_like(x, Z_WALK, dtype=float)
    if cls == PARKG:
        return park_height(x, y)
    if cls == LOT:
        return lot_height(x, y)
    return np.full_like(x, Z_OUT, dtype=float)


def surface_z(x, y):
    """walking surface height at arbitrary points (used by the layout)"""
    x = np.atleast_1d(np.asarray(x, float))
    y = np.atleast_1d(np.asarray(y, float))
    c, *_ = classify(np.floor(x) + 0.5, np.floor(y) + 0.5)
    out = np.empty_like(x)
    for k in np.unique(c):
        m = c == k
        out[m] = corner_heights(int(k), x[m], y[m])
    return out
