# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# assets_plants.py - trees (oak x2, birch, palm, maple), bushes, hedge, flower beds, grass tufts, reeds and lily pads.
#                    Foliage = crowns of alpha leaf cards over a real trunk/branch skeleton, baked with crown AO.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit, TAU
from . import gx
from .kit import asset, m, crown, ao_crown, bush_ao, bbox

UP = np.array([0, 0, 1.0])


def trunk_path(h, bend, rng, n=9, lean=(0.0, 0.0)):
    pts = []
    ph = rng.uniform(0, TAU)
    for i in range(n):
        t = i / (n - 1)
        pts.append((bend * np.sin(t * 2.6 + ph) * t + lean[0] * t * t, bend * 0.8 * np.cos(t * 2.1 + ph) * t + lean[1] * t * t, -0.15 + (h + 0.15) * t))
    return pts


def tree_geo(seed, h, crown_c, crown_r, ncards, size, leaf, bark, trunk_r, nbranch, bend=0.25, shell=0.45, uvq=None, spread=1.0):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    pts = trunk_path(h, bend, rng)
    radii = [trunk_r * 1.55, trunk_r * 1.20, trunk_r * 1.0, trunk_r * 0.92, trunk_r * 0.84, trunk_r * 0.76, trunk_r * 0.68, trunk_r * 0.58, trunk_r * 0.5]
    gx.tube(M, pts, radii, 12, bark, tile=1.0, cap_end=True, uv_scale=1.0)
    # root flare lumps
    for k in range(5):
        a = TAU * k / 5 + rng.uniform(-0.3, 0.3)
        d = np.array([np.cos(a), np.sin(a), 0])
        gx.tube(M, [(d[0] * trunk_r * 0.7, d[1] * trunk_r * 0.7, 0.35), (d[0] * trunk_r * 1.5, d[1] * trunk_r * 1.5, 0.05), (d[0] * trunk_r * 2.2, d[1] * trunk_r * 2.2, -0.12)],
                [trunk_r * 0.40, trunk_r * 0.30, trunk_r * 0.2], 7, bark, tile=1.0, cap_end=False)
    # main branches into the crown
    top = np.array(pts[-1])
    cc = np.asarray(crown_c, float)
    for k in range(nbranch):
        a = TAU * (k + rng.uniform(-0.15, 0.15)) / nbranch
        zf = rng.uniform(0.55, 0.92)
        i0 = int(zf * (len(pts) - 1))
        p0 = np.array(pts[i0])
        d = np.array([np.cos(a), np.sin(a), 0])
        end = cc + d * np.array(crown_r) * rng.uniform(0.40, 0.65) * spread + np.array([0, 0, rng.uniform(-0.4, 0.6)])
        mid = (p0 + end) / 2 + np.array([d[0] * 0.15, d[1] * 0.15, -0.15])
        br = trunk_r * rng.uniform(0.34, 0.44)
        gx.tube(M, [p0, mid, end], [br, br * 0.70, br * 0.34], 8, bark, tile=1.0, cap_end=True)
        # twigs
        for j in range(2):
            q = mid + d * 0.1
            e2 = end + np.array([rng.normal(0, 0.5), rng.normal(0, 0.5), rng.uniform(0.2, 0.8)])
            gx.tube(M, [q, (q + e2) / 2 + np.array([0, 0, 0.1]), e2], [br * 0.35, br * 0.2, br * 0.08], 5, bark, tile=1.0, cap_end=True)
    crown(M, cc, crown_r, ncards, size, leaf, rng, shell=shell, uvq=uvq)
    # low inner fill cards so the crown does not look hollow from below
    crown(M, cc + np.array([0, 0, -crown_r[2] * 0.15]), np.array(crown_r) * 0.72, ncards // 4, size * 1.1, leaf, rng, shell=0.2, uvq=uvq)
    C.box((-trunk_r * 0.85, -trunk_r * 0.85, 0.0), (trunk_r * 0.85, trunk_r * 0.85, 3.0))
    ao = ao_crown(cc, crown_r)
    return M, C, ao


@asset('pk_oak1', 'flora', dist=260)
def oak1():
    return tree_geo(101, 3.6, (0.2, 0.0, 6.1), (3.4, 3.4, 2.7), 190, 2.3, m('leaf_oak'), m('bark'), 0.30, 6)


@asset('pk_oak2', 'flora', dist=260)
def oak2():
    return tree_geo(202, 3.0, (-0.3, 0.2, 5.6), (4.1, 3.7, 2.4), 200, 2.3, m('leaf_oak'), m('bark'), 0.34, 7, bend=0.35, spread=1.15)


@asset('pk_maple', 'flora', dist=220)
def maple():
    return tree_geo(303, 2.4, (0, 0, 4.4), (2.2, 2.2, 2.0), 110, 1.7, m('leaf_oak'), m('bark'), 0.18, 5, bend=0.2)


@asset('pk_birch', 'flora', dist=240)
def birch():
    M, C, ao = tree_geo(404, 5.2, (0.1, 0.1, 6.6), (2.1, 2.1, 3.0), 150, 1.5, m('leaf_birch'), m('birchbark'), 0.14, 5, bend=0.45, shell=0.5, spread=0.8)
    return M, C, ao


@asset('pk_palm', 'flora', dist=240)
def palm():
    rng = np.random.default_rng(505)
    M, C = Mesh(), Col()
    BK, FR = m('bark'), m('frond')
    H = 6.8
    pts = [(0.9 * (i / 9) ** 2 * 1.4, 0.25 * np.sin(i * 0.7), -0.15 + (H + 0.15) * i / 9) for i in range(10)]
    radii = [0.34, 0.30, 0.27, 0.25, 0.23, 0.22, 0.21, 0.20, 0.20, 0.23]
    gx.tube(M, pts, radii, 12, BK, tile=1.0, uv_scale=1.0, cap_end=True)
    top = np.array(pts[-1])
    for k in range(5):
        a = TAU * k / 5
        gx.tube(M, [(0.5 * np.cos(a), 0.5 * np.sin(a), 0.4), (0.35 * np.cos(a), 0.35 * np.sin(a), 0.1), (0.62 * np.cos(a), 0.62 * np.sin(a), -0.12)], [0.16, 0.14, 0.1], 7, BK, tile=1.0, cap_end=False)
    # fronds: curved strips drooping outwards
    nf = 17
    for k in range(nf):
        a = TAU * k / nf + rng.uniform(-0.15, 0.15)
        d = np.array([np.cos(a), np.sin(a), 0.0])
        side = np.array([-d[1], d[0], 0.0])
        L = rng.uniform(3.0, 3.8)
        rise = rng.uniform(0.9, 1.6) if k % 2 else rng.uniform(0.2, 0.8)
        m_ = 8
        P, N, UV, T = [], [], [], []
        for i in range(m_ + 1):
            t = i / m_
            c = top + d * L * t + UP * (rise * np.sin(t * np.pi * 0.55) * 1.3 - 2.0 * (t ** 2) * (0.9 + 0.4 * rng.random())) + UP * 0.25
            hw = 1.05 * np.sin(np.pi * (0.12 + 0.88 * t) ) ** 0.8 * (1.0 - 0.15 * t)
            tw = side * hw
            P += [c - tw, c + tw]
            N += [unit(UP + d * 0.35)] * 2
            UV += [(t, 1.0), (t, 0.0)]
        for i in range(m_):
            a0 = 2 * i
            T += [[a0, a0 + 2, a0 + 3], [a0, a0 + 3, a0 + 1]]
        geo = np.cross(np.array(P[2]) - np.array(P[0]), np.array(P[3]) - np.array(P[0]))
        T = T if np.dot(geo, UP) > 0 else [t[::-1] for t in T]
        M.add(P, N, UV, T, FR)
        M.add(P, N, UV, [t[::-1] for t in T], FR)
    for k in range(5):
        a = TAU * k / 5 + 0.4
        gx.sphere(M, top + np.array([0.28 * np.cos(a), 0.28 * np.sin(a), -0.25]), 0.12, BK, 8, 5)
    C.box((-0.22, -0.22, 0.0), (0.22, 0.22, 3.0))
    c = top + np.array([0, 0, 0.5])
    return M, C, ao_crown(c, np.array([3.4, 3.4, 2.5]), base=0.70)


# ---------------------------------------------------------------------------------------------- bushes
def bush_geo(seed, R, n, size, col_mat=None):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    c = np.array([0, 0, R[2] * 0.55])
    gx.sphere(M, c, 0.55, m('wooddark'), 8, 5, sq=(R[0] * 0.5 / 0.55, R[1] * 0.5 / 0.55, R[2] * 0.42 / 0.55))
    crown(M, c, R, n, size, m('leaf_oak'), rng, shell=0.55, zmin=-0.25)
    C.box((-R[0] * 0.55, -R[1] * 0.55, 0.0), (R[0] * 0.55, R[1] * 0.55, R[2] * 1.1))
    return M, C, bush_ao(c, np.array(R))


@asset('pk_bush1', 'flora', dist=140)
def bush1():
    return bush_geo(11, (0.95, 0.95, 0.80), 110, 1.05)


@asset('pk_bush2', 'flora', dist=140)
def bush2():
    return bush_geo(22, (1.35, 0.85, 0.65), 120, 1.0)


@asset('pk_bush3', 'flora', dist=140)
def bush3():
    return bush_geo(33, (0.75, 0.75, 1.15), 100, 1.0)


@asset('pk_hedge', 'flora', dist=160)
def hedge():
    """box hedge 2.5 m long, 0.8 wide, 1.0 high (x -1.25..1.25)"""
    rng = np.random.default_rng(77)
    M, C = Mesh(), Col()
    M.box((-1.18, -0.28, 0.0), (1.18, 0.28, 0.86), m('wooddark'), tile=0.8)
    LF = m('leaf_oak')
    cards = []
    for i in range(230):
        face = rng.integers(0, 6)
        if face < 3:            # top
            p = np.array([rng.uniform(-1.2, 1.2), rng.uniform(-0.35, 0.35), 0.95 + rng.uniform(-0.05, 0.08)])
            n = unit(np.array([rng.normal(0, 0.4), rng.normal(0, 0.4), 1.0]))
        elif face < 5:          # long sides
            sy = -1 if face == 3 else 1
            p = np.array([rng.uniform(-1.2, 1.2), sy * (0.38 + rng.uniform(-0.04, 0.06)), rng.uniform(0.15, 0.95)])
            n = unit(np.array([rng.normal(0, 0.4), sy, 0.3 + rng.normal(0, 0.2)]))
        else:
            sx = rng.choice([-1, 1])
            p = np.array([sx * 1.26, rng.uniform(-0.3, 0.3), rng.uniform(0.15, 0.95)])
            n = unit(np.array([sx, rng.normal(0, 0.4), 0.3]))
        a = unit(np.cross(n, UP)) if abs(n[2]) < 0.95 else np.array([1.0, 0, 0])
        b = np.cross(a, n)
        ro = rng.uniform(0, TAU)
        a2, b2 = a * np.cos(ro) + b * np.sin(ro), -a * np.sin(ro) + b * np.cos(ro)
        s = rng.uniform(0.8, 1.15) / 2
        uvr = (0, 0, 1, 1) if rng.random() < 0.5 else (1, 0, 0, 1)
        gx.card(M, p, a2 * s, b2 * s, LF, unit(n + UP * 0.3), uvr)
    C.box((-1.25, -0.34, 0.0), (1.25, 0.34, 1.0))

    def ao(P, N):
        return 0.62 + 0.38 * np.clip(P[:, 2] / 1.0, 0, 1) ** 0.7 * (0.8 + 0.2 * np.clip(np.abs(P[:, 1]) / 0.4, 0, 1))
    return M, C, ao


# ------------------------------------------------------------------------------------------- flower beds
def bed_geo(seed, rx, ry, qs, n):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    M.prism((0, 0), 1.0, -0.05, 0.14, 22, m('dirt'), tile=1.4, ex=rx, ey=ry, smooth=True, cap_top=True)
    uvq = [(0, 0, .5, .5), (.5, 0, 1, .5), (0, .5, .5, 1), (.5, .5, 1, 1)]
    FL = m('flowers')
    for i in range(n):
        while True:
            x, y = rng.uniform(-1, 1, 2)
            if x * x + y * y <= 0.92:
                break
        px, py = x * rx * 0.92, y * ry * 0.92
        sz = rng.uniform(0.55, 0.85) * (1.0 - 0.3 * np.hypot(x, y))
        an = rng.uniform(0, np.pi)
        a = np.array([np.cos(an), np.sin(an), 0]) * sz / 2
        b = np.array([0, 0, 1.0]) * sz / 2
        q = uvq[qs[int((x * 0.7 + y * 0.7 + 2) * len(qs) / 4) % len(qs)] if rng.random() < 0.85 else qs[rng.integers(len(qs))]]
        gx.card(M, (px, py, 0.12 + sz * 0.42), a, b, FL, (px * 0.3, py * 0.3, 1.0), q if rng.random() < 0.5 else (q[2], q[1], q[0], q[3]))
    for i in range(int(n * 0.5)):          # leaning cards fill the gaps on top
        x, y = rng.uniform(-1, 1, 2)
        if x * x + y * y > 0.85:
            continue
        px, py = x * rx * 0.9, y * ry * 0.9
        nn = unit(np.array([x * 0.5, y * 0.5, 1.0]))
        a = unit(np.cross(nn, UP)) * 0.3
        b = np.cross(a, nn) * 1.0
        gx.card(M, (px, py, 0.38), a, unit(b) * 0.3, FL, nn, uvq[qs[rng.integers(len(qs))]])
    C.box((-rx * 0.7, -ry * 0.7, 0.0), (rx * 0.7, ry * 0.7, 0.16))
    return M, C, (lambda P, N: 0.70 + 0.30 * np.clip(P[:, 2] / 0.5, 0, 1))


@asset('pk_bed1', 'flora', dist=130)
def bed1():
    return bed_geo(1, 1.3, 0.9, [0, 1], 24)


@asset('pk_bed2', 'flora', dist=130)
def bed2():
    return bed_geo(2, 1.5, 1.0, [2, 3], 28)


@asset('pk_bed3', 'flora', dist=130)
def bed3():
    return bed_geo(3, 1.6, 1.1, [0, 1, 2, 3], 32)


# ------------------------------------------------------------------------------------------ grass, reeds
def tuft_geo(seed, mat, w, h, n=3, ncl=1):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    for k in range(n):
        a = np.pi * k / n + rng.uniform(-0.2, 0.2)
        ah = np.array([np.cos(a), np.sin(a), 0]) * w / 2
        gx.card(M, (0, 0, h / 2 - 0.02), ah, UP * h / 2, mat, unit(np.array([-np.sin(a), np.cos(a), 0.8])), (0, 0, 1, 1))
    C.box((-0.02, -0.02, 0.0), (0.02, 0.02, 0.04))
    return M, C, (lambda P, N: 0.62 + 0.38 * np.clip(P[:, 2] / h, 0, 1))


@asset('pk_tuft', 'flora', dist=90)
def tuft():
    return tuft_geo(5, m('grassblade'), 1.2, 0.95, 4)


@asset('pk_reeds', 'flora', dist=150)
def reeds():
    rng = np.random.default_rng(9)
    M, C = Mesh(), Col()
    for k in range(5):
        a = np.pi * k / 5 + rng.uniform(-0.2, 0.2)
        off = np.array([rng.normal(0, 0.25), rng.normal(0, 0.25), 0.0])
        s = rng.uniform(0.85, 1.15)
        ah = np.array([np.cos(a), np.sin(a), 0]) * 0.6 * s
        gx.card(M, off + UP * 0.9 * s - UP * 0.1, ah, UP * 1.0 * s, m('reed'), unit(np.array([-np.sin(a), np.cos(a), 0.8])), (0, 0, 1, 1) if k % 2 else (1, 0, 0, 1))
    C.box((-0.02, -0.02, 0.0), (0.02, 0.02, 0.04))
    return M, C, (lambda P, N: 0.60 + 0.40 * np.clip(P[:, 2] / 1.7, 0, 1))


@asset('pk_lilies', 'flora', dist=170)
def lilies():
    """lily pad cluster lying on the water (origin on the water surface)"""
    rng = np.random.default_rng(13)
    M, C = Mesh(), Col()
    LY = m('lily')
    for k in range(4):
        c = np.array([rng.uniform(-1.6, 1.6), rng.uniform(-1.2, 1.2), 0.015 + 0.004 * k])
        an = rng.uniform(0, TAU)
        a = np.array([np.cos(an), np.sin(an), 0]) * 1.0
        b = np.array([-np.sin(an), np.cos(an), 0]) * 1.0
        gx.card(M, c, a, b, LY, UP, (0, 0, 1, 1), double=True)
    C.box((-0.02, -0.02, -0.03), (0.02, 0.02, 0.0))
    return M, C
