# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# kit.py - asset registry, mesh/collision composition helpers (place a sub-model with position + yaw), oriented
#          collision slabs and foliage (card crown) helpers shared by assets_small.py / assets_big.py.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit, TAU
from . import gx
from .tex import IDX

REG = {}


class Asset:
    def __init__(self, name, cat, M, C, ao=None, dist=150.0, day_glow=0.25, alpha_sort=False, note=''):
        self.name, self.cat, self.M, self.C = name, cat, M, C
        self.ao, self.dist, self.day_glow, self.note = ao, dist, day_glow, note


def asset(name, cat, dist=150.0, day_glow=0.25):
    """decorator: fn() -> (M, C) or (M, C, ao)"""
    def deco(fn):
        def run():
            r = fn()
            ao = r[2] if len(r) > 2 else None
            return Asset(name, cat, r[0], r[1], ao, dist, day_glow)
        REG[name] = run
        return run
    return deco


def m(name):
    return IDX['pk_' + name]


def rotz(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def place(M, sub, pos=(0, 0, 0), rz=0.0, scale=1.0):
    """copy every chunk of the mesh `sub` into M, rotated about z by rz degrees (CCW from above) and moved to pos"""
    R = rotz(rz)
    for p, n, u, t, mt, e in sub.chunks:
        M.chunks.append(((p * scale) @ R.T + np.asarray(pos, float), n @ R.T, u, t, mt, e))


def place_col(C, sub, pos=(0, 0, 0), rz=0.0):
    R = rotz(rz)
    pos = np.asarray(pos, float)
    for lo, hi in sub.boxes:
        lo, hi = np.array(lo), np.array(hi)
        if abs(rz) % 90 < 1e-6:
            a, b = lo @ R.T + pos, hi @ R.T + pos
            C.box(np.minimum(a, b), np.maximum(a, b))
        else:
            cs = [np.array([x, y, z]) @ R.T + pos for z in (lo[2], hi[2]) for x, y in ((lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1]))]
            C.prisms.append(np.array(cs))
    for cc in sub.prisms:
        C.prisms.append(np.asarray(cc) @ R.T + pos)


def col_bar(C, p0, p1, w, h):
    """oriented collision slab between two points (w wide horizontally, h thick); corner order: bottom face, top face"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = unit(p1 - p0)
    r = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(r) < 1e-6:
        r = np.array([1.0, 0, 0])
    r = unit(r)
    u = unit(np.cross(r, d))
    if u[2] < 0:
        u = -u
    cs = []
    for s in (-1, 1):
        for q in (p0, p1):
            pass
    bot = [p0 - r * w / 2 - u * h / 2, p1 - r * w / 2 - u * h / 2, p1 + r * w / 2 - u * h / 2, p0 + r * w / 2 - u * h / 2]
    top = [b + u * h for b in bot]
    C.prisms.append(np.array(bot + top))


def bbox(M):
    P = np.concatenate([c[0] for c in M.chunks])
    return P.min(0), P.max(0)


# ---------------------------------------------------------------------------------------------
# foliage
# ---------------------------------------------------------------------------------------------
def crown(M, c, radii, n, size, mat, rng, shell=0.45, zmin=-0.35, uvq=None, tilt=0.55, size_var=(0.8, 1.25), flat=0.0):
    """n leaf cards inside an ellipsoid (centre c, radii (rx, ry, rz)).  uvq: list of uv rects to choose from."""
    c = np.asarray(c, float)
    radii = np.asarray(radii, float)
    up = np.array([0, 0, 1.0])
    done = 0
    while done < n:
        d = rng.normal(size=3)
        d = unit(d)
        if d[2] < zmin:
            continue
        f = 1.0 - shell * rng.random() ** 1.6
        p = c + d * radii * f
        nrm = unit(d + up * 0.30 + rng.normal(size=3) * tilt * 0.5)
        if flat:
            nrm = unit(nrm * [1, 1, 1 + flat])
        a = unit(np.cross(nrm, up))
        if np.linalg.norm(np.cross(nrm, up)) < 1e-3:
            a = np.array([1.0, 0, 0])
        b = np.cross(a, nrm)
        roll = rng.uniform(0, TAU)
        a2 = a * np.cos(roll) + b * np.sin(roll)
        b2 = -a * np.sin(roll) + b * np.cos(roll)
        s = size * rng.uniform(*size_var) / 2
        uvr = (0, 0, 1, 1) if uvq is None else uvq[rng.integers(len(uvq))]
        if rng.random() < 0.5:
            uvr = (uvr[2], uvr[1], uvr[0], uvr[3])
        gx.card(M, p, a2 * s, b2 * s, mat, unit(d + up * 0.25), uvr)
        done += 1


def ao_crown(c, radii, base=0.58, trunk_dark=0.70):
    """vertex colour multiplier: inner foliage darker, trunk under the crown darker"""
    c = np.asarray(c, float)
    radii = np.asarray(radii, float)

    def f(P, N):
        q = (P - c) / radii
        r = np.clip(np.linalg.norm(q, axis=1), 0, 1.15)
        k = base + (1 - base) * np.clip(r, 0, 1) ** 1.3
        k = k * (0.92 + 0.12 * np.clip(q[:, 2] * 0.5 + 0.5, 0, 1))
        low = np.clip((c[2] - P[:, 2]) / max(c[2], 1e-3), 0, 1)           # low trunk: slightly darker
        return k * (1 - 0.15 * low * (r > 1.0))
    return f


def bush_ao(c, R):
    c = np.asarray(c, float)

    def f(P, N):
        r = np.clip(np.linalg.norm((P - c) / R, axis=1), 0, 1.1)
        h = np.clip(P[:, 2] / (R[2] * 1.2), 0, 1)
        return (0.55 + 0.45 * np.clip(r, 0, 1) ** 1.2) * (0.70 + 0.30 * h ** 0.6)
    return f


def bin_mesh(M, keyfn):
    """split a Mesh by triangle centroid: keyfn(cx, cy) -> bin key.  Returns {key: Mesh} (vertex data copied per bin)"""
    out = {}
    for p, n, u, t, mt, e in M.chunks:
        cen = p[t].mean(1)
        keys = [keyfn(c[0], c[1]) for c in cen]
        for key in set(keys):
            sel = np.array([i for i, k in enumerate(keys) if k == key])
            tt = t[sel]
            used, inv = np.unique(tt.reshape(-1), return_inverse=True)
            out.setdefault(key, Mesh()).add(p[used], n[used], u[used], inv.reshape(-1, 3), mt, e)
    return out
