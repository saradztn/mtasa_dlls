# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# scene.py - colour baking for ground tiles (large scale dry / green / mud / dirty-asphalt tint on top of the usual
#            hemispheric bake) and full-city preview scene assembly.
import numpy as np
from . import bake, city as CT, tex
from .tex import IDX


def _fld(seed, x, y, f):
    return CT._field(seed, x * f, y * f)


def vertex_mats(M):
    out = []
    for p, n, u, t, m, e in M.chunks:
        out.append(np.full(len(p), m, np.int32))
    return np.concatenate(out)


def ground_tint(pos, vm):
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    tint = np.ones((len(pos), 3))
    big = _fld(8001, x, y, 0.6)
    small = _fld(8002, x, y, 3.0)
    for name, base in (('grass', None),):
        m = vm == IDX['af_grass']
        dry = np.clip(big * 0.8 + 0.4, 0, 1)[m]
        tint[m] = (np.array([0.70, 0.74, 0.46]) * (1 - dry[:, None]) + np.array([1.05, 0.88, 0.58]) * dry[:, None]) * (0.85 + 0.2 * small[m, None])
        mud = np.clip((-0.6 - z[m]) / 0.8, 0, 1)
        tint[m] = tint[m] * (1 - mud[:, None]) + np.array([0.42, 0.34, 0.26]) * mud[:, None]
    # wasteland outside the district: smooth patches of bare earth / dry straw / fresh green instead of a flat carpet
    out = np.maximum(np.abs(x), np.abs(y)) > 170.0
    m = (vm == IDX['af_grass']) & out
    if m.any():
        pa, pb = _fld(8003, x[m], y[m], 0.35), _fld(8004, x[m], y[m], 1.4)
        earth = np.clip((pa - 0.05) * 3.0, 0, 1)[:, None]
        straw = np.clip((pb + 0.1) * 2.0, 0, 1)[:, None]
        g = np.array([0.95, 1.05, 0.62]) * (1 - straw) + np.array([1.45, 1.1, 0.72]) * straw
        tint[m] = (g * (1 - earth) + np.array([1.7, 1.0, 0.85]) * earth) * (0.95 + 0.25 * small[m, None])
    # the mountain rim: bare grey-brown rock above ~10 m
    if m.any():
        alt = np.clip((z[m] - 9.0) / 24.0, 0, 1)[:, None]
        tint[m] = tint[m] * (1 - alt) + np.array([1.45, 1.25, 1.35]) * (0.85 + 0.3 * small[m, None]) * alt
    for nm in ('road', 'asphalt', 'crosswalk'):
        m = vm == IDX['af_' + nm]
        tint[m] = (0.82 + 0.22 * big[m, None]) * np.array([1.0, 1.0, 1.02])
    m = vm == IDX['af_sidewalk']
    tint[m] = (0.88 + 0.2 * big[m, None]) * np.array([1.0, 0.98, 0.94])
    return tint


def bake_ground(M, cfg, ao=None):
    pos, nrm, uv, tris, tmat, emis = bake.flatten(M)
    vm = vertex_mats(M)
    col = bake.bake(pos, nrm, emis, cfg, ao=ao)
    col = np.clip(col * ground_tint(pos, vm), 0, 1)
    return pos, nrm, uv, tris, tmat, col
