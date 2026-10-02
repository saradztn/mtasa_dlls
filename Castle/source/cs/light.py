# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# light.py - flattens a Mesh and bakes vertex colours (day + night) from room ambients, sun/moon
#            and the registered point lights (torches, chandeliers, lanterns, fire).
# Lights only affect vertices of their own room (interior lights never leak outdoors and vice versa).
# Emissive vertices (glass, flames, lantern cages) are fullbright in both sets.
# NOTE: the night set is deliberately DARK - white night colours would render full-bright (white) at night.
# -----------------------------------------------------------------------------
import numpy as np

DAY = dict(ext_amb=(0.80, 0.80, 0.82), int_amb=(0.46, 0.45, 0.47), sun=(0.40, 0.38, 0.32), sun_dir=(0.45, -0.55, 0.70), light_k=0.55, glass=0.80)
NIGHT = dict(ext_amb=(0.17, 0.21, 0.32), int_amb=(0.21, 0.20, 0.24), sun=(0.12, 0.15, 0.24), sun_dir=(-0.35, 0.45, 0.82), light_k=1.0, glass=1.0)


def flatten(M):
    pos, nrm, uv, tris, tmat, emis = [], [], [], [], [], []
    off = 0
    for p, n, u, t, m, e in M.chunks:
        pos.append(p)
        nrm.append(n)
        uv.append(u)
        tris.append(t + off)
        tmat.append(np.full(len(t), m, np.int32))
        emis.append(np.full(len(p), e))
        off += len(p)
    return (np.concatenate(pos), np.concatenate(nrm), np.concatenate(uv), np.concatenate(tris).astype(np.int32),
            np.concatenate(tmat), np.concatenate(emis))


def room_index(pts, rooms, margin=0.12):
    """index of the smallest room containing each point (-1 = exterior)"""
    names = list(rooms)
    vol = [np.prod(np.array(rooms[n][1]) - np.array(rooms[n][0])) for n in names]
    order = np.argsort(vol)
    idx = np.full(len(pts), -1, np.int32)
    for k in order[::-1]:
        lo = np.array(rooms[names[k]][0]) - margin
        hi = np.array(rooms[names[k]][1]) + margin
        inside = np.all((pts >= lo) & (pts <= hi), axis=1)
        idx[inside] = k
    return idx, names


def bake(pos, nrm, emis, mat_alpha, rooms, lights, cfg, tint_by_z=True):
    ridx, names = room_index(pos, rooms)
    n = len(pos)
    col = np.zeros((n, 3))
    ext = ridx < 0
    hemi = 0.78 + 0.22 * (nrm[:, 2] * 0.5 + 0.5)
    amb = np.where(ext[:, None], np.array(cfg['ext_amb']), np.array(cfg['int_amb'])) * hemi[:, None]
    col += amb
    sd = np.array(cfg['sun_dir'])
    sd = sd / np.linalg.norm(sd)
    lam = np.clip(nrm @ sd, 0, 1)
    col += np.where(ext[:, None], lam[:, None] * np.array(cfg['sun']), 0.0)
    # slightly darker near the ground line of the exterior (poor man's AO)
    if tint_by_z:
        ao = np.clip(0.80 + 0.20 * (pos[:, 2] + 2.0) / 3.5, 0.8, 1.0)
        col *= np.where(ext, ao, 1.0)[:, None]
    # interior ambient occlusion: corners near floor / ceiling slightly darker
    for L in lights:
        lr, _ = room_index(L['pos'][None, :], rooms, 0.05)
        lr = int(lr[0])
        same = ridx == lr
        if not same.any():
            continue
        d = pos[same] - L['pos']
        dist = np.linalg.norm(d, axis=1)
        wrap = np.clip(np.einsum('ij,ij->i', nrm[same], -d / np.maximum(dist[:, None], 1e-6)) * 0.75 + 0.25, 0, 1)
        att = np.clip(1 - dist / L['rad'], 0, 1) ** 1.6
        col[same] += (att * wrap * L['k'] * cfg['light_k'])[:, None] * L['col']
    col = np.clip(col, 0, 1)
    e = emis.copy()
    if cfg is DAY:
        e = e * cfg['glass']
    col = col * (1 - e[:, None]) + e[:, None]
    return np.clip(col, 0, 1)
