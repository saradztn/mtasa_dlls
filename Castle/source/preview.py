# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# preview.py - build the scene in memory and render game-like previews (texture * baked vertex colours)
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cs import castle, tex, light
from lib import render2


def get_scene():
    S = castle.Scene()
    castle.build_all(S) if hasattr(castle, 'build_all') else castle.build_shell(S)
    return S


def prep(S, textures=None):
    pos, nrm, uv, tris, tmat, emis = light.flatten(S.M)
    textures = textures or [tex.GEN[n]() for n in tex.MAT_NAMES]
    textures = [(np.clip(t, 0, 1) * 255 + 0.5).astype(np.uint8) for t in textures]
    return pos, nrm, uv, tris, tmat, emis, textures


def subdivide(pos, uv, col, tris, tmat, nrm=None, maxedge=5.0):
    """preview only: split long triangles so the simple renderer's near-plane handling does not drop big floors"""
    pos, uv, col = [pos], [uv], [col]
    P = np.concatenate(pos); U = np.concatenate(uv); Cc = np.concatenate(col)
    T = tris.copy(); TM = tmat.copy()
    for _ in range(4):
        e = np.stack([np.linalg.norm(P[T[:, 1]] - P[T[:, 0]], axis=1), np.linalg.norm(P[T[:, 2]] - P[T[:, 1]], axis=1), np.linalg.norm(P[T[:, 0]] - P[T[:, 2]], axis=1)], 1).max(1)
        big = e > maxedge
        if not big.any():
            break
        tb = T[big]
        mid = []
        newv = []
        base = len(P)
        a, b, c = tb[:, 0], tb[:, 1], tb[:, 2]
        Pm = [(P[a] + P[b]) / 2, (P[b] + P[c]) / 2, (P[c] + P[a]) / 2]
        Um = [(U[a] + U[b]) / 2, (U[b] + U[c]) / 2, (U[c] + U[a]) / 2]
        Cm = [(Cc[a] + Cc[b]) / 2, (Cc[b] + Cc[c]) / 2, (Cc[c] + Cc[a]) / 2]
        n = len(tb)
        ab = base + np.arange(n); bc = base + n + np.arange(n); ca = base + 2 * n + np.arange(n)
        P = np.concatenate([P] + Pm); U = np.concatenate([U] + Um); Cc = np.concatenate([Cc] + Cm)
        new = np.concatenate([np.stack([a, ab, ca], 1), np.stack([ab, b, bc], 1), np.stack([ca, bc, c], 1), np.stack([ab, bc, ca], 1)])
        newm = np.tile(TM[big], 4)
        T = np.concatenate([T[~big], new]); TM = np.concatenate([TM[~big], newm])
    return P, U, Cc, T, TM


def add_doors(S, pos, nrm, uv, tris, tmat, emis, textures, open_=False):
    import build
    D = build.door_meshes()
    P_, N_, U_, T_, M_, E_ = [pos], [nrm], [uv], [tris], [tmat], [emis]
    off = len(pos)
    for d in S.doors:
        M = D[d['model']][0]
        p, n, u, t, m, e = light.flatten(M)
        a = np.radians(d['open_rz'] if open_ else d['rz'])
        R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        P_.append(p @ R.T + np.array(d['hinge'])); N_.append(n @ R.T); U_.append(u); T_.append(t + off); M_.append(m); E_.append(e)
        off += len(p)
    return [np.concatenate(x) for x in (P_, N_, U_, T_, M_, E_)]


def shots(S, which, out_dir, mode='day', W=1600, H=900, ss=2, textures=None):
    pos, nrm, uv, tris, tmat, emis, textures = prep(S, textures)
    cfg = light.DAY if mode == 'day' else light.NIGHT
    col = light.bake(pos, nrm, emis, None, S.rooms, S.L, cfg)
    n0 = len(pos)
    pos, nrm, uv, tris, tmat, emis = add_doors(S, pos, nrm, uv, tris, tmat, emis, textures, open_=bool(int(os.environ.get('OPEN', '0'))))
    dcol = (0.62, 0.58, 0.55) if mode == 'day' else (0.30, 0.26, 0.24)
    col = np.concatenate([col, np.tile(dcol, (len(pos) - n0, 1))])
    pos, uv, col, tris, tmat = subdivide(pos, uv, col, tris, tmat)
    alpha = sorted(tex.ALPHA)
    tm = np.repeat(tmat, 1)
    tri_mat = tmat
    bg = (0.55, 0.65, 0.80) if mode == 'day' else (0.02, 0.03, 0.07)
    views = {
        'front': dict(eye=(0, -60, 18), target=(0, 10, 15), fov=52),
        'front_close': dict(eye=(6, -24, 6), target=(0, 0, 8), fov=60),
        'aerial': dict(eye=(-48, -45, 48), target=(0, 15, 14), fov=50),
        'back': dict(eye=(30, 80, 30), target=(0, 20, 14), fov=55),
        'hall': dict(eye=(0, 2.0, 1.7), target=(0, 18, 4.5), fov=75, cuts=[(0, 0, 1, 12.5)]),
        'hall_back': dict(eye=(0, 24.6, 4.0), target=(0, 3, 6.5), fov=75),
        'lib': dict(eye=(-10.0, 2.2, 1.8), target=(-18, 14, 1.8), fov=80),
        'lib_up': dict(eye=(-10.0, 2.5, 8.6), target=(-18, 14, 8.0), fov=80),
        'dine': dict(eye=(10.0, 2.2, 1.8), target=(17, 14, 1.5), fov=80),
        'dine_fire': dict(eye=(15.6, 3.0, 1.8), target=(15.6, 21, 1.6), fov=75),
        'gallery': dict(eye=(0, 2.4, 8.4), target=(0, 20, 6.0), fov=80),
        'keep_in': dict(eye=(-5.0, 27.0, 3.4), target=(0, 33, 8.0), fov=85),
        'keep_top': dict(eye=(-4.8, 33, 21.0), target=(2, 33, 26.0), fov=85),
        'gate_open': dict(eye=(0, -9, 1.8), target=(0, 6, 3.5), fov=70),
        'section': dict(eye=(0, -45, 15), target=(0, 12, 10), fov=60, cuts=[(0, -1, 0, -0.5 - 8.0 * 0 + 0.0), ]),
    }
    os.makedirs(out_dir, exist_ok=True)
    for w in which:
        v = views[w]
        t = time.time()
        im = render2.render(pos, uv, col, tris, tri_mat, textures, alpha, v['eye'], v['target'], fov=v['fov'], W=W, H=H, ss=ss,
                            cuts=v.get('cuts', ()), bg=bg)
        p = os.path.join(out_dir, '%s_%s.png' % (w, mode))
        im.save(p)
        print(p, '%.1fs' % (time.time() - t))


if __name__ == '__main__':
    S = get_scene()
    mode = sys.argv[1]
    which = sys.argv[2].split(',')
    shots(S, which, os.path.join(HERE, '_work'), mode, W=int(os.environ.get('W', 1280)), H=int(os.environ.get('H', 720)), ss=int(os.environ.get('SS', 1)))
