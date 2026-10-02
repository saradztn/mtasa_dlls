# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# assets_flora.py - overgrown vegetation: big street trees breaking through the asphalt, dead trees, saplings, bushes,
#   weed / tall-grass patches.  Foliage = crowns of alpha leaf-cluster cards over a real trunk + branch skeleton.
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



def dead_tree(seed, h, spread, nb, leafmat=None):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    bark = m('bark')
    pts = trunk_path(h, 0.35, rng)
    tr = 0.28
    gx.tube(M, pts, [tr * 1.5, tr * 1.1, tr, tr * 0.9, tr * 0.8, tr * 0.7, tr * 0.6, tr * 0.5, tr * 0.35], 12, bark, tile=1.0, cap_end=True)
    for k in range(5):
        a = TAU * k / 5 + rng.uniform(-0.3, 0.3)
        d = np.array([np.cos(a), np.sin(a), 0])
        gx.tube(M, [(d[0] * tr * 0.7, d[1] * tr * 0.7, 0.35), (d[0] * tr * 1.5, d[1] * tr * 1.5, 0.05), (d[0] * tr * 2.1, d[1] * tr * 2.1, -0.12)], [tr * 0.4, tr * 0.3, tr * 0.2], 7, bark, tile=1.0, cap_end=False)
    ends = []
    for k in range(nb):
        a = TAU * k / nb + rng.uniform(-0.3, 0.3)
        zf = rng.uniform(0.45, 0.97)
        p0 = np.array(pts[int(zf * (len(pts) - 1))])
        d = np.array([np.cos(a), np.sin(a), 0])
        L = rng.uniform(1.6, 3.2) * spread * (1.3 - zf * 0.6)
        end = p0 + d * L + UP * rng.uniform(0.2, 1.6)
        mid = (p0 + end) / 2 + UP * rng.uniform(0.0, 0.5)
        br = tr * rng.uniform(0.3, 0.45)
        gx.tube(M, [p0, mid, end], [br, br * 0.6, br * 0.2], 7, bark, tile=1.0, cap_end=True)
        ends.append(end)
        for j in range(2):
            q = (mid + end) / 2
            e2 = q + d * rng.uniform(0.6, 1.4) + np.array([rng.normal(0, 0.6), rng.normal(0, 0.6), rng.uniform(0.2, 1.0)])
            gx.tube(M, [q, (q + e2) / 2 + UP * 0.1, e2], [br * 0.4, br * 0.2, br * 0.07], 5, bark, tile=1.0, cap_end=True)
            ends.append(e2)
    if leafmat is not None:
        for e in ends[::2]:
            for _ in range(2):
                rr = np.random.default_rng(int(rng.integers(1, 10 ** 6)))
                gx.card(M, e + rr.normal(0, 0.3, 3) * [1, 1, 0.5], unit(np.array([rr.normal(), rr.normal(), 0])) * 0.55, UP * 0.5, leafmat, UP)
    C.box((-tr * 0.85, -tr * 0.85, 0.0), (tr * 0.85, tr * 0.85, 3.0))
    return M, C, ao_crown(np.array([0, 0, h]), (3.5, 3.5, 4.0), base=0.75)


def patch(seed, n, R, hmin, hmax, mats):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    for _ in range(n):
        rad = R * np.sqrt(rng.random())
        a = rng.uniform(0, TAU)
        p = np.array([np.cos(a) * rad, np.sin(a) * rad, 0.0])
        h = rng.uniform(hmin, hmax)
        w = h * rng.uniform(0.8, 1.3)
        ang = rng.uniform(0, np.pi)
        for dd in (0, np.pi / 2):
            ax = np.array([np.cos(ang + dd), np.sin(ang + dd), 0]) * w / 2
            gx.card(M, p + UP * h * 0.49, ax, UP * h / 2, mats[int(rng.integers(0, len(mats)))] if dd == 0 else mats[int(rng.integers(0, len(mats)))], UP)
    return M, C, lambda P, N: 0.62 + 0.38 * np.clip(P[:, 2] / max(hmax, 0.1), 0, 1)


@asset('af_tree_a', 'flora', dist=300)
def tree_a():
    return tree_geo(101, 3.4, (0.2, 0.0, 6.4), (3.8, 3.8, 3.0), 210, 2.6, m('leaf'), m('bark'), 0.32, 6, bend=0.3)


@asset('af_tree_b', 'flora', dist=300)
def tree_b():
    return tree_geo(202, 2.8, (-0.3, 0.2, 5.8), (4.4, 4.0, 2.7), 220, 2.6, m('leaf'), m('bark'), 0.36, 7, bend=0.4, spread=1.15)


@asset('af_tree_big', 'flora', dist=380)
def tree_big():
    return tree_geo(303, 6.5, (0.4, 0.3, 11.0), (6.2, 6.2, 5.0), 330, 3.2, m('leaf'), m('bark'), 0.55, 8, bend=0.5, spread=1.2)


@asset('af_tree_c', 'flora', dist=280)
def tree_c():
    return tree_geo(404, 4.2, (0.0, 0.0, 7.0), (2.8, 2.8, 3.6), 150, 2.2, m('leaf'), m('bark'), 0.24, 5, bend=0.35, shell=0.5, spread=0.85)


@asset('af_tree_dead_a', 'flora', dist=260)
def tree_dead_a():
    return dead_tree(505, 6.0, 1.0, 7, m('leaf_dead'))


@asset('af_tree_dead_b', 'flora', dist=260)
def tree_dead_b():
    return dead_tree(606, 4.6, 1.2, 6, m('leaf_dead'))


@asset('af_sapling', 'flora', dist=170)
def sapling():
    return tree_geo(707, 2.2, (0, 0, 3.4), (1.5, 1.5, 1.5), 55, 1.4, m('leaf'), m('bark'), 0.075, 4, bend=0.25)


def bush_geo(seed, R, n, size, leaf):
    rng = np.random.default_rng(seed)
    M, C = Mesh(), Col()
    c = np.array([0, 0, R[2] * 0.55])
    gx.sphere(M, c, 0.55, m('bark'), 8, 5, sq=(R[0] * 0.5 / 0.55, R[1] * 0.5 / 0.55, R[2] * 0.42 / 0.55))
    crown(M, c, R, n, size, leaf, rng, shell=0.55, zmin=-0.25)
    C.box((-R[0] * 0.55, -R[1] * 0.55, 0.0), (R[0] * 0.55, R[1] * 0.55, R[2] * 1.1))
    return M, C, bush_ao(c, np.array(R))


asset('af_bush_a', 'flora', dist=150)(lambda: bush_geo(11, (1.5, 1.5, 1.2), 40, 1.2, m('leaf')))
asset('af_bush_b', 'flora', dist=150)(lambda: bush_geo(12, (2.2, 1.8, 1.5), 60, 1.3, m('leaf')))
asset('af_bush_dead', 'flora', dist=150)(lambda: bush_geo(13, (1.6, 1.4, 1.1), 40, 1.1, m('leaf_dead')))
asset('af_weeds_a', 'flora', dist=130)(lambda: patch(21, 16, 1.3, 0.7, 1.3, [m('weeds'), m('dead_grass')]))
asset('af_weeds_b', 'flora', dist=130)(lambda: patch(22, 26, 2.4, 0.9, 1.7, [m('weeds'), m('dead_grass'), m('weeds')]))
asset('af_grass_tall', 'flora', dist=140)(lambda: patch(23, 22, 1.8, 1.3, 2.1, [m('dead_grass'), m('weeds')]))
asset('af_ivy_mound', 'flora', dist=140)(lambda: patch(24, 14, 1.4, 0.8, 1.6, [m('ivy'), m('leaf')]))
