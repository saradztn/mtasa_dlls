# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# bake.py - flatten a Mesh and bake vertex colours (day + night) for outdoor models: hemispheric ambient, weak sun term,
#           per-asset AO hook (foliage crowns), low-height contact darkening, emissive (lamp glass, kiosk window).
# NOTE: the night set is deliberately dark - white night colours would render full-bright at night.
# -----------------------------------------------------------------------------
import numpy as np

DAY = dict(amb=(0.80, 0.80, 0.82), sun=(0.40, 0.38, 0.32), sun_dir=(0.45, -0.55, 0.70), glow=0.25)
NIGHT = dict(amb=(0.17, 0.21, 0.32), sun=(0.12, 0.15, 0.24), sun_dir=(-0.35, 0.45, 0.82), glow=1.0)


def flatten(M):
    pos, nrm, uv, tris, tmat, emis = [], [], [], [], [], []
    off = 0
    for p, n, u, t, mt, e in M.chunks:
        pos.append(p)
        nrm.append(n)
        uv.append(u)
        tris.append(t + off)
        tmat.append(np.full(len(t), mt, np.int32))
        emis.append(np.full(len(p), e))
        off += len(p)
    return (np.concatenate(pos), np.concatenate(nrm), np.concatenate(uv), np.concatenate(tris).astype(np.int32),
            np.concatenate(tmat), np.concatenate(emis))


def bake(pos, nrm, emis, cfg, ao=None, glow=None, extra=None):
    hemi = 0.76 + 0.24 * (nrm[:, 2] * 0.5 + 0.5)
    col = np.array(cfg['amb']) * hemi[:, None]
    sd = np.array(cfg['sun_dir'])
    sd = sd / np.linalg.norm(sd)
    col = col + np.clip(nrm @ sd, 0, 1)[:, None] * np.array(cfg['sun'])
    col *= np.clip(0.86 + 0.14 * (pos[:, 2] + 0.05) / 0.6, 0.86, 1.0)[:, None]
    if ao is not None:
        col *= np.clip(ao(pos, nrm), 0, 1.2)[:, None]
    if extra is not None:
        col = col + extra
    col = np.clip(col, 0, 1)
    e = emis * (cfg['glow'] if glow is None else glow)
    return np.clip(col * (1 - e[:, None]) + e[:, None], 0, 1)
