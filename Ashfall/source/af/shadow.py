# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# shadow.py - baked sun shadows + horizon ambient occlusion for the ground of the whole district.
#   The placed city (layout) is rasterised into a 1 m height field (solid buildings / cars / containers) and a canopy
#   field (trees, bushes: base, top, density per metre).  For every cell:
#     * sun transmittance: the ray towards the sun is marched through both fields (solids block, canopies absorb with
#       Beer-Lambert) -> long building shadows and dappled tree shade, exactly in the direction the day bake uses;
#     * sky visibility: horizon based AO over 8 directions -> dark street canyons, contact darkening at walls, under trees.
#   shade_fn() returns the per-vertex multiplier used by bake.bake(ao=...) for the ground tiles.
# -----------------------------------------------------------------------------
import numpy as np
from . import city as CT
from .tex_base import gblur

N = 340
X0 = -170.0
SOLID = ('af_tower', 'af_apt', 'af_shop', 'af_hotel', 'af_kiosk', 'af_office', 'af_car_', 'af_container', 'af_dumpster',
         'af_busstop', 'af_jersey', 'af_rubble', 'af_gas_canopy', 'af_fountain', 'af_gazebo', 'af_playground', 'af_obelisk')
TREES = {'af_tree_a': 0.15, 'af_tree_b': 0.15, 'af_tree_c': 0.15, 'af_tree_big': 0.17, 'af_tree_dead_a': 0.05, 'af_tree_dead_b': 0.05,
         'af_sapling': 0.15, 'af_bush_a': 0.25, 'af_bush_b': 0.25, 'af_bush_dead': 0.12}


def _rect_cells(ox, oy, rz, lo, hi, pad=0.0):
    """cell indices + mask of the oriented rectangle (lo, hi in model space) placed at (ox, oy) rotated rz degrees"""
    c, s = np.cos(np.radians(rz)), np.sin(np.radians(rz))
    cs = [(ox + c * x - s * y, oy + s * x + c * y) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])]
    x0 = int(np.floor(min(p[0] for p in cs) - X0 - 1)); x1 = int(np.ceil(max(p[0] for p in cs) - X0 + 1))
    y0 = int(np.floor(min(p[1] for p in cs) - X0 - 1)); y1 = int(np.ceil(max(p[1] for p in cs) - X0 + 1))
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, N), min(y1, N)
    if x0 >= x1 or y0 >= y1:
        return None
    gx, gy = np.meshgrid(X0 + np.arange(x0, x1) + 0.5, X0 + np.arange(y0, y1) + 0.5)
    dx, dy = gx - ox, gy - oy
    u = c * dx + s * dy
    v = -s * dx + c * dy
    m = (u >= lo[0] - pad) & (u <= hi[0] + pad) & (v >= lo[1] - pad) & (v <= hi[1] + pad)
    return (slice(y0, y1), slice(x0, x1)), m, u, v


def build(objs, bounds, sun=(0.45, -0.55, 0.70)):
    H = np.zeros((N, N), np.float32)                 # solid top
    Cb = np.full((N, N), 1e3, np.float32)            # canopy base / top / density per metre
    Ct = np.zeros((N, N), np.float32)
    Cd = np.zeros((N, N), np.float32)
    for o in objs:
        name = o['m']
        if name not in bounds:
            continue
        lo, hi = np.array(bounds[name][0], float), np.array(bounds[name][1], float)
        if name.endswith('_v'):
            continue
        if name in TREES:
            dens = TREES[name]
            rad = 0.5 * max(hi[0] - lo[0], hi[1] - lo[1]) * 0.85
            cx, cy = o['x'] + 0.5 * (lo[0] + hi[0]), o['y'] + 0.5 * (lo[1] + hi[1])
            base = o['z'] + (lo[2] + 0.38 * (hi[2] - lo[2]) if 'bush' not in name else lo[2])
            top = o['z'] + hi[2]
            r = _rect_cells(cx, cy, 0, (-rad, -rad), (rad, rad))
            if r is None:
                continue
            sl, m, u, v = r
            m = (u * u + v * v) <= rad * rad
            fall = np.clip(1.15 - np.sqrt(u * u + v * v) / rad, 0, 1)        # thinner at the rim
            Cb[sl] = np.where(m, np.minimum(Cb[sl], base), Cb[sl])
            Ct[sl] = np.where(m, np.maximum(Ct[sl], top), Ct[sl])
            Cd[sl] = np.where(m, np.maximum(Cd[sl], dens * np.sqrt(fall)), Cd[sl])
        elif name.startswith(SOLID):
            r = _rect_cells(o['x'], o['y'], o['rz'], lo[:2], hi[:2])
            if r is None:
                continue
            sl, m, u, v = r
            H[sl] = np.where(m, np.maximum(H[sl], o['z'] + hi[2]), H[sl])
    # ------------------------------------------------ sun transmittance
    s = np.array(sun, float)
    hd = s[:2] / np.hypot(*s[:2])
    slope = s[2] / np.hypot(*s[:2])
    gy, gx = np.mgrid[0:N, 0:N].astype(np.float32)
    T = np.ones((N, N), np.float32)
    step = 1.0
    for k in range(1, 96):
        sx = np.clip(np.rint(gx + hd[0] * k * step).astype(int), 0, N - 1)
        sy = np.clip(np.rint(gy + hd[1] * k * step).astype(int), 0, N - 1)
        zr = k * step * slope + 0.3
        T = np.where(H[sy, sx] > zr, 0.0, T)
        inside = (Cb[sy, sx] < zr) & (Ct[sy, sx] > zr)
        T = T * np.exp(-np.where(inside, Cd[sy, sx], 0.0) * step / max(slope, 0.5))
    T = gblur(T, 0.9)
    # ------------------------------------------------ horizon AO
    Heff = np.maximum(H, np.where(Cd > 0.05, Ct * np.clip(Cd * 1.4, 0, 1), 0)).astype(np.float32)
    occ = np.zeros((N, N), np.float32)
    for a in range(10):
        ang = a * 2 * np.pi / 10
        d = (np.cos(ang), np.sin(ang))
        best = np.zeros((N, N), np.float32)
        for k in (1, 2, 3, 4, 6, 8, 11, 15, 20, 27):
            sx = np.clip(np.rint(gx + d[0] * k).astype(int), 0, N - 1)
            sy = np.clip(np.rint(gy + d[1] * k).astype(int), 0, N - 1)
            best = np.maximum(best, np.maximum(Heff[sy, sx] - 0.4, 0) / np.sqrt((Heff[sy, sx] - 0.4).clip(0) ** 2 + (k * step) ** 2 + 1e-6))
        occ += best
    occ /= 10
    ao = np.clip(1 - 0.60 * occ, 0.50, 1.0)
    ao = gblur(ao, 0.8)
    return dict(T=T, AO=ao, H=H)


def sample(F, x, y):
    """bilinear sample of a cell field at world positions"""
    fx = np.clip((np.asarray(x) - X0) - 0.5, 0, N - 1.001)
    fy = np.clip((np.asarray(y) - X0) - 0.5, 0, N - 1.001)
    ix, iy = fx.astype(int), fy.astype(int)
    tx, ty = fx - ix, fy - iy
    return (F[iy, ix] * (1 - tx) * (1 - ty) + F[iy, ix + 1] * tx * (1 - ty) + F[iy + 1, ix] * (1 - tx) * ty + F[iy + 1, ix + 1] * tx * ty)


def shade_fn(fields, sunfrac=0.42, ao_strength=1.0):
    """multiplier callable for bake.bake(ao=...)  (sunfrac: share of the sun term in the day colour; 0.1 for night)"""
    def f(pos, nrm):
        t = sample(fields['T'], pos[:, 0], pos[:, 1])
        a = sample(fields['AO'], pos[:, 0], pos[:, 1])
        a = 1 - (1 - a) * ao_strength
        up = np.clip(nrm[:, 2], 0, 1)
        sunk = 1 - sunfrac * (1 - t) * (0.35 + 0.65 * up)
        return a * sunk
    return f
