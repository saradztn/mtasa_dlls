# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# castle.py - architectural shell of the gothic castle: plinth, terrace, entrance stairs, great hall,
#             gallery + flights, wings, towers, keep with spiral stair, roofs, windows.
# Coordinate system (metres): origin at the centre of the entrance floor; front facade at y = 0,
# the castle extends towards +y; floor z = 0, ground z = -2.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, Opening, wall, stairs, arch_fn, unit, TAU
from .tex import M as MI
from . import parts as P
from .parts import ST, SI, TR, FL, TL, SL, WD, DR, IR, RG, WB, OB, GL, FM, BK, BN, GD, CV

HALL_H = 13.0
SLAB0, SLAB1 = 6.4, 6.8          # upper floor slab
DAIS_Z = 2.0


class Scene:
    def __init__(self):
        self.M = Mesh()
        self.C = Col()
        self.L = []
        self.rooms = {}          # name -> (lo, hi)
        self.doors = []          # dict(model, hinge, rz, swing)
        self.web_pts = []        # candidate corners for cobwebs (filled by build functions)
        self.rng = np.random.default_rng(2026)
        self.meta = {}
        self.windows = []        # (centre xyz, normal xy, apex z) of interior-facing window arches
        self.ceil = {}           # room -> ceiling z

    def lift(self, dz):
        return _Lift(self, dz)


class _Lift:
    """context manager: everything added inside the block (mesh, collision, lights) is raised by dz"""
    def __init__(self, S, dz):
        self.S, self.dz = S, dz

    def __enter__(self):
        S = self.S
        self.i = (len(S.M.chunks), len(S.C.boxes), len(S.C.prisms), len(S.L))
        return self

    def __exit__(self, *a):
        S, dz = self.S, self.dz
        for k in range(self.i[0], len(S.M.chunks)):
            S.M.chunks[k][0][:, 2] += dz
        for k in range(self.i[1], len(S.C.boxes)):
            lo, hi = S.C.boxes[k]
            S.C.boxes[k] = ((lo[0], lo[1], lo[2] + dz), (hi[0], hi[1], hi[2] + dz))
        for k in range(self.i[2], len(S.C.prisms)):
            S.C.prisms[k][:, 2] += dz
        for k in range(self.i[3], len(S.L)):
            S.L[k]['pos'][2] += dz


# ---------------------------------------------------------------------------------------------
def op(s0, s1, zb, zs, k=1.0, glass=True, trim=True, door=False, mull=True, sill=True):
    return dict(s0=s0, s1=s1, zb=zb, zs=zs, k=k, glass=glass, trim=trim, door=door, mull=mull, sill=sill)


def build_wall(S, mat_a, mat_b, a, b, t, bands, ext_side=None, tile=3.0, mat_rev=None, collide=True):
    """wall made of stacked bands [(z0, z1, [ops])].  ext_side = +1/-1: the face that gets window trims / sills
    (+1 = left of a->b = face A).  Windows get glass at the centre plane."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = unit(b - a)
    nl = np.array([-d[1], d[0]])
    L = float(np.linalg.norm(b - a))
    n = len(bands)
    for i, (z0, z1, ops) in enumerate(bands):
        O = [Opening(o['s0'], o['s1'], o['zb'], o['zs'], 'arch', o['k']) for o in ops]
        wall(S.M, S.C, mat_a, mat_b, a, b, z0, z1, t, O, tile=tile, mat_top=ST,
             mat_rev=TR if mat_rev is None else mat_rev, top_cap=(i == n - 1), caps=(True, True), collide=collide)
        for o, OO in zip(ops, O):
            wm = (a + d * (o['s0'] + o['s1']) / 2)
            if o['glass']:
                S.windows.append((np.array([wm[0] + nl[0] * (t / 2 + 0.04), wm[1] + nl[1] * (t / 2 + 0.04), OO.apex]), nl.copy(), OO.zb, o['s1'] - o['s0']))
            if o['glass']:
                ss = OO.samples()
                pts = [a + d * s for s in ss]
                poly = [(a[0] + d[0] * OO.s0, a[1] + d[1] * OO.s0, OO.zb), (a[0] + d[0] * OO.s1, a[1] + d[1] * OO.s1, OO.zb)]
                for s in ss[::-1]:
                    if s <= OO.s0 + 1e-9 or s >= OO.s1 - 1e-9:
                        poly.append((a[0] + d[0] * s, a[1] + d[1] * s, OO.top(s)))
                        continue
                    poly.append((a[0] + d[0] * s, a[1] + d[1] * s, OO.top(s)))
                # remove duplicated points
                clean = []
                for p in poly:
                    if not clean or np.linalg.norm(np.array(p) - np.array(clean[-1])) > 1e-6:
                        clean.append(p)
                S.M.poly(clean, GL, hint=(nl[0], nl[1], 0), tile=2.4, emis=0.92, double=True)
                if o['mull']:
                    mx, my = wm
                    apex = OO.apex
                    P.bar(S.M, (mx, my, OO.zb), (mx, my, apex - 0.02), 0.07, IR, tile=0.3)
                    for f in (0.34, 0.67):
                        zz = OO.zb + (OO.zt - OO.zb) * f
                        P.bar(S.M, (a[0] + d[0] * (o['s0']), a[1] + d[1] * o['s0'], zz), (a[0] + d[0] * o['s1'], a[1] + d[1] * o['s1'], zz), 0.05, IR, tile=0.3)
                    # outer iron frame
                    for sgn, s_e in ((0, o['s0']), (1, o['s1'])):
                        P.bar(S.M, (a[0] + d[0] * s_e, a[1] + d[1] * s_e, OO.zb), (a[0] + d[0] * s_e, a[1] + d[1] * s_e, OO.zt), 0.06, IR, tile=0.3)
            if ext_side is not None and o['trim']:
                P.arch_trim(S.M, a, b, t, ext_side, o['s0'], o['s1'], o['zt'] if 'zt' in o else o['zs'], o['k'], width=0.22, depth=0.14, jamb=o['zs'] - o['zb'])
                if o['sill'] and not o['door']:
                    sp = a + d * o['s0'] + nl * ext_side * (t / 2 + 0.09)
                    sq = a + d * o['s1'] + nl * ext_side * (t / 2 + 0.09)
                    lo = np.minimum(sp, sq) - np.abs(d) * 0.12 - np.abs(nl) * 0.09
                    hi = np.maximum(sp, sq) + np.abs(d) * 0.12 + np.abs(nl) * 0.09
                    S.M.box((lo[0], lo[1], o['zb'] - 0.16), (hi[0], hi[1], o['zb']), TR, tile=1.0)


def crenel(S, a, b, z, th=0.5, hp=1.0, hm=0.55, pitch=1.7, solid_z=None):
    """parapet (hp high) with merlons (hm high) along a->b, outer face on the right of a->b"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = unit(b - a)
    L = float(np.linalg.norm(b - a))
    nl = np.array([-d[1], d[0]])
    def blk(s0, s1, z0, z1):
        p0 = a + d * s0 + nl * th / 2
        p1 = a + d * s1 - nl * th / 2
        lo = np.minimum(p0, p1)
        hi = np.maximum(p0, p1)
        S.M.box((lo[0], lo[1], z0), (hi[0], hi[1], z1), ST, tile=2.0, mats={'+z': TR})
    blk(0, L, z, z + hp)
    k = int(L / pitch)
    for i in range(k):
        s0 = (i + 0.25) * L / k
        s1 = (i + 0.75) * L / k
        blk(s0, s1, z + hp, z + hp + hm)
    p0 = a + nl * th / 2
    p1 = b - nl * th / 2
    lo, hi = np.minimum(p0, p1), np.maximum(p0, p1)
    S.C.box((lo[0], lo[1], z), (hi[0], hi[1], z + hp + hm * 0.7))


# ---------------------------------------------------------------------------------------------
def foundation(S):
    M, C = S.M, S.C
    X, Y0, Y1 = 26.0, -8.5, 43.0
    M.box((-X, Y0, -2.0), (X, Y1, 0.0), ST, tile=3.0, mats={'+z': FL}, skip=('-z',))
    C.box((-X, Y0, -2.0), (X, Y1, 0.0))
    # entrance steps (10 x 0.2 rise / 0.4 run) with cheek walls
    stairs(M, C, TR, -4.0, 4.0, -12.5, -2.0, +1, 10, 0.2, 0.4, mat_side=ST, tile=2.0, z_floor=-2.0, tread_mat=FL)
    for sx in (-1, 1):
        x0, x1 = (4.0, 4.8) if sx > 0 else (-4.8, -4.0)
        # cheek wall following the flight: a stepped stone block that rises with the steps
        for i in range(10):
            ya, yb = -12.5 + 0.4 * i, -12.1 + 0.4 * i
            zt = -2.0 + 0.2 * (i + 1) + 0.9
            M.box((x0, ya, -2.0), (x1, yb, zt), ST, tile=2.0, mats={'+z': TR}, skip=('-z',))
            C.box((x0, ya, -2.0), (x1, yb, zt))
    # parapet around the plinth: front (with the stair gap), sides and back
    crenel(S, (-X, Y0 + 0.25), (-4.8, Y0 + 0.25), 0.0)
    crenel(S, (4.8, Y0 + 0.25), (X, Y0 + 0.25), 0.0)
    crenel(S, (X - 0.25, Y0), (X - 0.25, Y1), 0.0)
    crenel(S, (X, Y1 - 0.25), (-X, Y1 - 0.25), 0.0)
    crenel(S, (-X + 0.25, Y1), (-X + 0.25, Y0), 0.0)
    S.meta['plinth'] = (X, Y0, Y1)


def hall(S):
    M, C = S.M, S.C
    H = HALL_H
    # ---- walls ------------------------------------------------------------------------
    # front wall (a->b towards +x): left = +y = interior
    gate = op(7.2, 11.2, 0.0, 2.6, 1.0, glass=False, trim=False, door=True)
    lancets = [op(9.2 + c - 0.7, 9.2 + c + 0.7, 8.0, 10.4, 1.2) for c in (-6.4, -2.8, 2.8, 6.4)]
    build_wall(S, SI, ST, (-9.2, 0.6), (9.2, 0.6), 1.2, [(0, SLAB0, [gate]), (SLAB0, H, lancets)], ext_side=-1)
    # triple moulding around the gate (like the reference picture)
    # back wall: a=(9.2,25.8) -> b=(-9.2,25.8); left = -y = hall interior ; right = keep interior
    d1 = op(3.4, 5.2, DAIS_Z, DAIS_Z + 2.2, 1.0, glass=False, trim=False, door=True)
    d2 = op(13.2, 15.0, DAIS_Z, DAIS_Z + 2.2, 1.0, glass=False, trim=False, door=True)
    build_wall(S, SI, SI, (9.2, 25.8), (-9.2, 25.8), 1.2, [(0, H, [d1, d2])])
    # west wall: a=(-8.6,25.2) -> b=(-8.6,1.2) ; left = +x (hall) ; right = wing interior
    gw = op(21.6, 23.4, 0.0, 2.2, 1.0, glass=False, trim=False, door=True)
    uw = op(19.4, 21.2, SLAB1, SLAB1 + 2.2, 1.0, glass=False, trim=False, door=True)
    build_wall(S, SI, SI, (-8.6, 25.2), (-8.6, 1.2), 1.2, [(0, SLAB0, [gw]), (SLAB0, H, [uw])])
    ge = op(0.6, 2.4, 0.0, 2.2, 1.0, glass=False, trim=False, door=True)
    ue = op(2.8, 4.6, SLAB1, SLAB1 + 2.2, 1.0, glass=False, trim=False, door=True)
    build_wall(S, SI, SI, (8.6, 1.2), (8.6, 25.2), 1.2, [(0, SLAB0, [ge]), (SLAB0, H, [ue])])
    # ---- floor / ceiling ---------------------------------------------------------------
    M.poly([(-8, 1.2, 0.02), (8, 1.2, 0.02), (8, 12.0, 0.02), (-8, 12.0, 0.02)], TL, hint=(0, 0, 1), tile=6.0)
    # dais
    M.box((-8, 12.0, 0.0), (8, 25.2, DAIS_Z), SI, tile=3.0, mats={'+z': TL, '-y': TR}, skip=('-z', '-x', '+x', '+y'))
    C.box((-8, 12.0, 0.0), (8, 25.2, DAIS_Z))
    # coffered timber ceiling with beams
    M.poly([(-8, 1.2, 12.6), (-8, 25.2, 12.6), (8, 25.2, 12.6), (8, 1.2, 12.6)], WD, hint=(0, 0, -1), tile=2.0)
    for y in (2.2, 6.2, 10.2, 14.2, 18.2, 22.2, 24.6):
        M.box((-8, y - 0.25, 12.05), (8, y + 0.25, 12.6), WD, tile=1.0, skip=('+z',))
    for x in (-4.0, 0.0, 4.0):
        M.box((x - 0.18, 1.2, 12.3), (x + 0.18, 25.2, 12.6), WD, tile=1.0, skip=('+z',))
    # ---- central grand staircase, gallery, flights ------------------------------------------
    stairs(M, C, TR, -2.4, 2.4, 8.0, 0.0, +1, 10, 0.2, 0.4, mat_side=ST, tile=2.0, z_floor=0.0, tread_mat=TR)
    # carpet on the grand stairs follows each step
    for i in range(10):
        ya, yb, zt = 8.0 + 0.4 * i, 8.4 + 0.4 * i, 0.2 * (i + 1)
        M.poly([(-1.3, ya, zt + 0.015), (1.3, ya, zt + 0.015), (1.3, yb, zt + 0.015), (-1.3, yb, zt + 0.015)], RG, hint=(0, 0, 1),
               uv=[(0.0, 0.0 + i * 0.4 / 5.2), (1, 0.0 + i * 0.4 / 5.2), (1, (i + 1) * 0.4 / 5.2), (0, (i + 1) * 0.4 / 5.2)])
        M.poly([(-1.3, ya, zt - 0.2 + 0.0), (1.3, ya, zt - 0.2), (1.3, ya, zt + 0.015), (-1.3, ya, zt + 0.015)], RG, hint=(0, -1, 0),
               uv=[(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
    for sx in (-1, 1):
        x0, x1 = (5.6, 8.0) if sx > 0 else (-8.0, -5.6)
        stairs(M, C, TR, x0, x1, 12.0, DAIS_Z, -1, 24, 0.2, 0.25, mat_side=ST, tile=2.0, z_floor=0.0, tread_mat=TR)
    # gallery slab
    M.box((-8, 1.2, SLAB0), (8, 6.0, SLAB1), WD, tile=2.0, mats={'+z': WD, '+y': TR}, skip=('-x', '+x', '-y'))
    C.box((-8, 1.2, SLAB0), (8, 6.0, SLAB1))
    M.box((-8, 5.2, 5.6), (8, 6.0, SLAB0), TR, tile=1.5, skip=('+z', '-x', '+x', '-y'))
    for sx in (-1, 1):
        P.column(M, C, (sx * 3.0, 5.6), 0.34, 0.0, 5.6, TR)
    # balustrade along the gallery front + along the flights
    def balustrade(p0, p1, z0, z1, n):
        p0, p1 = np.array(p0, float), np.array(p1, float)
        for i in range(n + 1):
            t = i / n
            p = p0 + (p1 - p0) * t
            zz = z0 + (z1 - z0) * t
            M.prism((p[0], p[1]), 0.07, zz, zz + 0.9, 6, TR, tile=0.5, cap_top=True, smooth=True)
        P.bar(M, (p0[0], p0[1], z0 + 0.95), (p1[0], p1[1], z1 + 0.95), 0.12, TR, tile=0.6)
    balustrade((-5.6, 5.85), (5.6, 5.85), SLAB1, SLAB1, 22)
    C.box((-5.6, 5.78, SLAB1), (5.6, 5.92, SLAB1 + 1.0))
    for sx in (-1, 1):
        xi = 5.6 * sx + (0.12 if sx < 0 else -0.12) * 0
        balustrade((sx * 5.65, 6.0), (sx * 5.65, 12.0), SLAB1, DAIS_Z + 0.2, 24)
    # pilasters + rib capitals along the side walls (above the landing) and along the dais
    for sx in (-1, 1):
        for y in (13.6, 17.4, 21.2):
            xw = 8.0 * sx
            M.box((min(xw, xw - sx * 0.45), y - 0.28, 0), (max(xw, xw - sx * 0.45), y + 0.28, 12.0), TR, tile=1.5, skip=('-z',))
            M.box((min(xw, xw - sx * 0.6), y - 0.38, 11.0), (max(xw, xw - sx * 0.6), y + 0.38, 12.1), TR, tile=1.5, skip=('-z',))
            C.box((min(xw, xw - sx * 0.45), y - 0.28, DAIS_Z), (max(xw, xw - sx * 0.45), y + 0.28, 12.0))
    # two tall carved panels above the keep doors, flanking the throne
    M.poly([(-6.4, 25.17, 6.4), (-3.4, 25.17, 6.4), (-3.4, 25.17, 12.4), (-6.4, 25.17, 12.4)], CV, hint=(0, -1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)], emis=0.30)
    M.poly([(3.4, 25.17, 6.4), (6.4, 25.17, 6.4), (6.4, 25.17, 12.4), (3.4, 25.17, 12.4)], CV, hint=(0, -1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)], emis=0.30)
    S.rooms['hall'] = ((-8, 1.2, 0), (8, 25.2, 13.0))
    S.ceil['hall'] = 12.6
    S.meta['hall_beams'] = [2.2, 6.2, 10.2, 14.2, 18.2, 22.2]


def wings(S):
    M, C = S.M, S.C
    H = HALL_H
    for sx, nm in ((-1, 'wing_w'), (1, 'wing_e')):
        # wall ordering mirrors by sign so that face A (left) is always the interior
        if sx < 0:
            front = ((-22, 0.5), (-9.2, 0.5))
            outer = ((-21.5, 22.0), (-21.5, 1.0))
            back = ((-9.2, 22.5), (-22, 22.5))
        else:
            front = ((9.2, 0.5), (22, 0.5))
            outer = ((21.5, 1.0), (21.5, 22.0))
            back = ((22, 22.5), (9.2, 22.5))
        # front wall: s measured along a->b
        def fx(x):
            return (x - front[0][0]) if sx > 0 else (x - front[0][0])
        g = []
        wx = sx * 19.8
        g_low = [op(abs(wx - front[0][0]) - 0.6, abs(wx - front[0][0]) + 0.6, 1.2, 3.8, 1.2)]
        g_up = [op(abs(wx - front[0][0]) - 0.6, abs(wx - front[0][0]) + 0.6, 7.8, 10.2, 1.2)]
        build_wall(S, SI, ST, front[0], front[1], 1.0, [(0, SLAB0, g_low), (SLAB0, H, g_up)], ext_side=-1)
        # outer wall: windows staggered (ground: y=5,10,15,19.5 ; upper: 7.5,12.5,17)
        def so(y):
            return abs(y - outer[0][1])
        low = [op(so(y) - 0.6, so(y) + 0.6, 1.2, 3.8, 1.2) for y in (5.0, 10.0, 15.0, 19.5)]
        upp = [op(so(y) - 0.6, so(y) + 0.6, 7.8, 10.2, 1.2) for y in (3.0, 7.5, 12.5, 17.0, 20.0)]
        build_wall(S, SI, ST, outer[0], outer[1], 1.0, [(0, SLAB0, low), (SLAB0, H, upp)], ext_side=-1)
        # back wall: windows at two x positions
        def sb(x):
            return abs(x - back[0][0])
        bl = [op(sb(sx * c) - 0.6, sb(sx * c) + 0.6, 1.2, 3.8, 1.2) for c in (12.5, 18.5)]
        bu = [op(sb(sx * c) - 0.6, sb(sx * c) + 0.6, 7.8, 10.2, 1.2) for c in (12.5, 18.5)]
        build_wall(S, SI, ST, back[0], back[1], 1.0, [(0, SLAB0, bl), (SLAB0, H, bu)], ext_side=-1)
        x0, x1 = (-21.0, -9.2) if sx < 0 else (9.2, 21.0)
        # floors / slab / ceiling
        mat_floor = FL if sx < 0 else TL
        M.poly([(x0, 1.0, 0.02), (x1, 1.0, 0.02), (x1, 22.0, 0.02), (x0, 22.0, 0.02)], mat_floor, hint=(0, 0, 1), tile=(4.0 if sx < 0 else 6.0))
        M.box((x0, 1.0, SLAB0), (x1, 22.0, SLAB1), WD, tile=2.0, skip=('-x', '+x', '-y', '+y'), mats={'+z': WD})
        C.box((x0, 1.0, SLAB0), (x1, 22.0, SLAB1))
        M.poly([(x0, 1.0, 12.6), (x0, 22.0, 12.6), (x1, 22.0, 12.6), (x1, 1.0, 12.6)], WD, hint=(0, 0, -1), tile=2.0)
        M.poly([(x0, 1.0, SLAB0), (x0, 22.0, SLAB0), (x1, 22.0, SLAB0), (x1, 1.0, SLAB0)], WD, hint=(0, 0, -1), tile=2.0)
        for y in (3.0, 7.0, 11.0, 15.0, 19.0):
            M.box((x0, y - 0.22, 12.1), (x1, y + 0.22, 12.6), WD, tile=1.0, skip=('+z',))
            M.box((x0, y - 0.22, SLAB0 - 0.45), (x1, y + 0.22, SLAB0), WD, tile=1.0, skip=('+z',))
        S.rooms[nm + '_g'] = ((x0, 1.0, 0.0), (x1, 22.0, SLAB0))
        S.rooms[nm + '_u'] = ((x0, 1.0, SLAB1), (x1, 22.0, H))
        S.ceil[nm + '_g'] = SLAB0 - 0.02
        S.ceil[nm + '_u'] = 12.6
        # buttresses on the outer wall
        xo = 22.0 * sx
        for y in (7.5, 12.5, 17.5):
            lo, hi = sorted([xo, xo + sx * 0.9])
            M.box((lo, y - 0.45, -0.0), (hi, y + 0.45, 8.0), ST, tile=2.0, mats={'+z': TR})
            lo2, hi2 = sorted([xo, xo + sx * 0.55])
            M.box((lo2, y - 0.35, 8.0), (hi2, y + 0.35, 11.5), ST, tile=2.0, mats={'+z': TR})
            C.box((min(xo, xo + sx * 0.9), y - 0.45, 0.0), (max(xo, xo + sx * 0.9), y + 0.45, 8.0))
        # chimney on the outer roof slope
        cx = sx * 20.0
        M.box((cx - 0.7, 18.0, 13.0), (cx + 0.7, 19.4, 21.0), ST, tile=2.0, mats={'+z': TR})
        M.box((cx - 0.9, 17.8, 21.0), (cx + 0.9, 19.6, 21.5), TR, tile=2.0)
        for dx in (-0.45, 0.45):
            M.box((cx + dx - 0.25, 18.2, 21.5), (cx + dx + 0.25, 19.2, 22.6), ST, tile=1.0)


def roofs(S):
    M, C = S.M, S.C

    def gable_roof(xa, xb, ya, yb, ze, zr, ridge_x):
        """roof with ridge parallel to y at x = ridge_x, eaves at z = ze (x = xa and x = xb)."""
        for x_e, sgn in ((xa, -1), (xb, +1)):
            run = abs(ridge_x - x_e)
            slant = np.hypot(run, zr - ze)
            L = yb - ya
            pts = [(x_e, ya, ze), (x_e, yb, ze), (ridge_x, yb, zr), (ridge_x, ya, zr)]
            uv = [(0, 0), (L / 3.0, 0), (L / 3.0, -slant / 3.0), (0, -slant / 3.0)]
            M.poly(pts, SL, uv=uv, hint=((x_e - ridge_x), 0, run))
            # eave thickness
            M.poly([(x_e, ya, ze - 0.35), (x_e, yb, ze - 0.35), (x_e, yb, ze), (x_e, ya, ze)], TR, hint=(x_e - ridge_x, 0, 0), tile=1.5)
        # ridge cap
        P.bar(M, (ridge_x, ya, zr + 0.05), (ridge_x, yb, zr + 0.05), 0.35, TR, tile=1.0)
        # gable ends (solid stone triangles)
        for y, ny, mat in ((ya, -1, ST), (yb, +1, SI)):
            M.poly([(xa, y, ze), (xb, y, ze), (ridge_x, y, zr)], ST, hint=(0, ny, 0), tile=3.0)
    # hall: ridge z=28 ; eaves at z=13 x = +-9.2
    gable_roof(-9.2, 9.2, 0.0, 26.4, HALL_H, 28.0, 0.0)
    # wings: ridge parallel to y
    gable_roof(-22.0, -9.2, 0.0, 23.0, HALL_H, 24.0, -15.6)
    gable_roof(9.2, 22.0, 0.0, 23.0, HALL_H, 24.0, 15.6)
    # cornice (string course) along the front facade and rose window on the hall gable
    M.box((-22.0, -0.30, 12.7), (22.0, 0.0, 13.05), TR, tile=1.5)
    M.box((-22.0, -0.20, SLAB0 - 0.1), (-9.2, 0.0, SLAB0 + 0.15), TR, tile=1.5)
    M.box((9.2, -0.20, SLAB0 - 0.1), (22.0, 0.0, SLAB0 + 0.15), TR, tile=1.5)
    # rose window
    cx, cz, R = 0.0, 19.2, 2.7
    n = 32
    ring = [(cx + R * np.cos(i * TAU / n), -0.03, cz + R * np.sin(i * TAU / n)) for i in range(n)]
    M.poly(ring, GL, hint=(0, -1, 0), tile=2.4, emis=0.95)
    for i in range(n):
        a_, b_ = ring[i], ring[(i + 1) % n]
        P.bar(M, (a_[0], -0.05, a_[2]), (b_[0], -0.05, b_[2]), 0.14, TR, h=0.22, tile=1.0)
        a2 = (cx + (R + 0.3) * np.cos(i * TAU / n), -0.12, cz + (R + 0.3) * np.sin(i * TAU / n))
        b2 = (cx + (R + 0.3) * np.cos((i + 1) * TAU / n), -0.12, cz + (R + 0.3) * np.sin((i + 1) * TAU / n))
        P.bar(M, a2, b2, 0.22, TR, h=0.28, tile=1.0)
        ai = (cx + R * 0.45 * np.cos(i * TAU / n), -0.06, cz + R * 0.45 * np.sin(i * TAU / n))
        bi = (cx + R * 0.45 * np.cos((i + 1) * TAU / n), -0.06, cz + R * 0.45 * np.sin((i + 1) * TAU / n))
        P.bar(M, ai, bi, 0.08, TR, h=0.12, tile=1.0)
    for k in range(12):
        a = k * TAU / 12
        P.bar(M, (cx, -0.06, cz), (cx + (R) * np.cos(a), -0.06, cz + R * np.sin(a)), 0.08, TR, h=0.12, tile=1.0)
        # petals
        px, pz = cx + R * 0.72 * np.cos(a + TAU / 24), cz + R * 0.72 * np.sin(a + TAU / 24)
    # lancet slits in the wing gables
    # gable finials
    P.finial(M, (0.0, 0.3), 27.8, 4.0, 0.28)
    P.finial(M, (-15.6, 0.3), 23.8, 3.2, 0.24)
    P.finial(M, (15.6, 0.3), 23.8, 3.2, 0.24)
    P.finial(M, (0.0, 26.1), 27.8, 3.0, 0.24)


# ---------------------------------------------------------------------------------------------
def round_tower(S, c, R, z_top, z_cone, n=12, slits=(3.5, 8.0, 12.5), crown=True, name=None, door=None):
    """decorative solid round tower (exterior only): shaft with plinth, string courses, glowing slits, corbelled crown, cone roof."""
    M, C = S.M, S.C
    cx, cy = c
    th = np.arange(n + 1) * TAU / n + TAU / (2 * n)
    # shaft
    M.prism((cx, cy), R, 0.0, z_top, n, ST, tile=3.0, theta0=TAU / (2 * n), cap_top=False)
    # base plinth + courses
    M.prism((cx, cy), R + 0.3, 0.0, 1.1, n, TR, tile=2.0, theta0=TAU / (2 * n), cap_top=False)
    M.cone((cx, cy), R + 0.3, 1.1, 1.5, n, TR, tile=2.0, theta0=TAU / (2 * n), r_top=R)
    zc = z_top * 0.55
    M.prism((cx, cy), R + 0.12, zc, zc + 0.25, n, TR, tile=2.0, theta0=TAU / (2 * n), cap_top=False)
    # crown: corbels + machicolation ring + eaves
    M.cone((cx, cy), R + 0.9, z_top - 0.9, z_top, n, TR, tile=2.0, theta0=TAU / (2 * n), r_top=R)
    M.prism((cx, cy), R + 0.9, z_top, z_top + 0.55, n, ST, tile=2.0, theta0=TAU / (2 * n), cap_top=False)
    M.cone((cx, cy), R + 0.9, z_top + 0.55, z_top + 0.62, n, TR, tile=2.0, theta0=TAU / (2 * n), r_top=R + 0.2)
    # cone roof (slate)
    M.cone((cx, cy), R + 0.75, z_top + 0.55, z_cone, n, SL, tile=3.0, theta0=TAU / (2 * n), smooth=False)
    P.finial(M, (cx, cy), z_cone - 0.1, 3.0, 0.24)
    # glowing slits: 4 per level facing the 4 diagonal directions of the polygon
    for zs in slits:
        for k in range(n):
            if k % 3 != 1 and (name is None):
                continue
            if k % 3 != 1:
                continue
            ang = th[k] - TAU / (2 * n) + TAU / (2 * n)
            mid = (th[k] + th[k + 1]) / 2 - TAU / (2 * n) + TAU / (2 * n)
            nrm = np.array([np.cos(mid), np.sin(mid)])
            tg = np.array([-nrm[1], nrm[0]])
            rr = R * np.cos(TAU / (2 * n)) + 0.03
            base = np.array([cx, cy]) + nrm * rr
            w = 0.45
            pts = [(*(base - tg * w / 2), zs), (*(base + tg * w / 2), zs), (*(base + tg * w / 2), zs + 1.5), (*base, zs + 2.1), (*(base - tg * w / 2), zs + 1.5)]
            M.poly(pts, GL, hint=(nrm[0], nrm[1], 0), tile=2.0, emis=0.9)
            # stone frame
            fpts = [(*(base - tg * (w / 2 + 0.14)), zs - 0.1), (*(base + tg * (w / 2 + 0.14)), zs - 0.1), (*(base + tg * (w / 2 + 0.14)), zs + 1.55), (*base, zs + 2.28),
                    (*(base - tg * (w / 2 + 0.14)), zs + 1.55)]
            M.poly(fpts, TR, hint=(nrm[0], nrm[1], 0), tile=1.0, uvoff=(0, 0))
    # collision: thick ring of strips (solid shaft)
    ring = [(cx + R * np.cos(a), cy + R * np.sin(a)) for a in th]
    for i in range(n):
        C.strip(np.array(ring[i]), np.array(ring[i + 1]), R * 0.9, 0.0, z_top)
    return


def towers(S):
    # front gate towers on the terrace, rear towers behind the wings, wing corner turrets
    for sx in (-1, 1):
        round_tower(S, (sx * 13.0, -3.5), 3.5, 17.0, 28.0)
        round_tower(S, (sx * 13.0, 26.5), 3.5, 19.0, 31.0, slits=(4.0, 9.0, 14.0))
        round_tower(S, (sx * 23.5, -1.6), 2.4, 15.0, 23.0, slits=(3.5, 8.5), n=10)
        round_tower(S, (sx * 23.5, 24.6), 2.4, 16.0, 24.5, slits=(3.5, 8.5), n=10)


# ---------------------------------------------------------------------------------------------
def keep(S):
    M, C = S.M, S.C
    H = 30.0
    cy0, cy1 = 26.4, 39.6 + 0.6
    # south wall = hall back wall (already built).  side walls and back wall:
    # west: a=(-6.6,40.2)->b=(-6.6,26.4): left=+x interior ; east: a=(6.6,26.4)->(6.6,40.2) ; back: a=(7.2,39.6)->(-7.2,39.6)
    def win_row(c_list, w=1.2):
        return c_list
    def ops_for(z0, z1, zb, zs, centres, a_s):
        return [op(a_s(c) - 0.6, a_s(c) + 0.6, zb, zs, 1.2) for c in centres]
    bands_def = [(0.0, 11.0, 4.5, 7.5), (11.0, 22.0, 13.5, 17.0), (22.0, 30.0, 24.0, 26.5)]
    for name, a, b, tt, cen, sfun in (
            ('w', (-6.6, 40.2), (-6.6, 26.4), 1.2, (29.7, 33.3, 36.9), lambda y: 40.2 - y),
            ('e', (6.6, 26.4), (6.6, 40.2), 1.2, (29.7, 33.3, 36.9), lambda y: y - 26.4),
            ('b', (7.2, 39.6), (-7.2, 39.6), 1.2, (-3.6, 0.0, 3.6), lambda x: 7.2 - x)):
        bands = [(z0, z1, [op(sfun(c) - 0.6, sfun(c) + 0.6, zb, zs, 1.2) for c in cen]) for z0, z1, zb, zs in bands_def]
        build_wall(S, SI, ST, a, b, tt, bands, ext_side=-1)
    # south wall of the keep above the hall (hall back wall is only 13 m high)
    build_wall(S, ST, SI, (7.2, 25.8), (-7.2, 25.8), 1.2, [(13.0, 22.0, []), (22.0, 30.0, [op(7.2 - 4.8 - 0.6, 7.2 - 4.8 + 0.6, 24.0, 26.5, 1.2), op(7.2 + 4.8 - 0.6, 7.2 + 4.8 + 0.6, 24.0, 26.5, 1.2)])], ext_side=None, collide=False)
    # floor + ceiling + top gallery slab
    M.box((-6.0, 26.4, 0.0), (6.0, 39.0, DAIS_Z), FL, tile=4.0, skip=('-z', '-x', '+x', '-y', '+y'))
    C.box((-6.0, 26.4, 0.0), (6.0, 39.0, DAIS_Z))
    cyc = 32.7
    for (lo, hi) in (((-6.0, 26.4), (6.0, 28.2)), ((-6.0, 37.2), (6.0, 39.0)), ((-6.0, 28.2), (-4.5, 37.2)), ((4.5, 28.2), (6.0, 37.2))):
        M.box((lo[0], lo[1], 21.55), (hi[0], hi[1], 22.0), WD, tile=2.0, skip=())
        C.box((lo[0], lo[1], 21.55), (hi[0], hi[1], 22.0))
    # balustrade around the stair well at the top
    for (p0, p1) in (((-4.5, 28.2), (4.5, 28.2)), ((-4.5, 37.2), (4.5, 37.2)), ((4.5, 28.2), (4.5, 37.2))):
        p0, p1 = np.array(p0), np.array(p1)
        k = int(np.linalg.norm(p1 - p0) / 0.5)
        for i in range(k + 1):
            p = p0 + (p1 - p0) * i / k
            M.prism((p[0], p[1]), 0.06, 22.0, 22.9, 6, TR, tile=0.5, smooth=True)
        P.bar(M, (p0[0], p0[1], 22.95), (p1[0], p1[1], 22.95), 0.1, TR, tile=0.6)
        lo = np.minimum(p0, p1) - 0.06
        hi = np.maximum(p0, p1) + 0.06
        C.box((lo[0], lo[1], 22.0), (hi[0], hi[1], 23.0))
    M.poly([(-6, 26.4, 29.4), (-6, 39, 29.4), (6, 39, 29.4), (6, 26.4, 29.4)], WD, hint=(0, 0, -1), tile=2.0)
    for x in (-4.0, 0.0, 4.0):
        M.box((x - 0.2, 26.4, 29.0), (x + 0.2, 39.0, 29.4), WD, tile=1.0, skip=('+z',))
    # spiral staircase around a central column
    col_r, r_in, r_out = 0.9, 0.9, 4.4
    M.prism((0, cyc), col_r, 2.0, 22.0, 16, TR, tile=2.0, smooth=True, cap_top=False)
    C.box((-0.65, cyc - 0.65, 2.0), (0.65, cyc + 0.65, 22.0))
    n_steps = 100
    dth = np.radians(14.4)
    th0 = np.radians(187.2)
    for i in range(n_steps):
        a0 = th0 + i * dth
        a1 = a0 + dth
        zt = 2.0 + 0.2 * (i + 1)
        zb = zt - 0.38
        p = lambda a, r: (0.0 + r * np.cos(a), cyc + r * np.sin(a))
        i0, i1, o0, o1 = p(a0, r_in), p(a1, r_in), p(a0, r_out), p(a1, r_out)
        top = [(*i0, zt), (*o0, zt), (*o1, zt), (*i1, zt)]
        M.poly(top, TR, hint=(0, 0, 1), tile=1.2)
        # riser (faces the lower step i.e. direction of decreasing angle)
        rd = np.array([np.sin(a0), -np.cos(a0), 0.0])
        M.poly([(*i0, zb), (*o0, zb), (*o0, zt), (*i0, zt)], TR, hint=-rd * -1 * -1, tile=1.2)
        # outer face
        mid = (a0 + a1) / 2
        M.poly([(*o0, zb), (*o1, zb), (*o1, zt), (*o0, zt)], ST, hint=(np.cos(mid), np.sin(mid), 0), tile=1.2)
        # underside
        M.poly([(*i0, zb), (*o0, zb), (*o1, zb), (*i1, zb)], WD, hint=(0, 0, -1), tile=1.2)
        corners = [i0, o0, o1, i1]
        cc = [[x, y, zb - 0.1] for x, y in corners] + [[x, y, zt] for x, y in corners]
        C.prisms.append(np.array(cc))
    # spire: 4 sided pyramid + corner pinnacles
    S_cx = 0.0
    M.cone((S_cx, cyc + 0.45), 10.6, 30.0, 49.0, 4, SL, tile=3.0, theta0=np.pi / 4)
    P.finial(M, (S_cx, cyc + 0.45), 48.9, 5.0, 0.34)
    M.box((-7.5, 26.4 - 0.2 + 0.0, 29.6), (7.5, 40.4, 30.0), TR, tile=1.5)
    for sx in (-1, 1):
        for yy in (26.7, 40.0):
            x, y = sx * 7.2, yy
            M.prism((x, y), 0.95, 29.6, 33.5, 8, ST, tile=2.0, cap_top=False, theta0=np.pi / 8)
            M.cone((x, y), 1.2, 33.5, 39.0, 8, SL, tile=2.0, theta0=np.pi / 8)
            P.finial(M, (x, y), 38.9, 2.0, 0.16)
    S.rooms['keep'] = ((-6.0, 26.4, 0.0), (6.0, 39.0, 30.0))
    S.ceil['keep'] = 29.4
    S.meta['keep_center'] = (0.0, cyc)


def build_shell(S):
    foundation(S)
    hall(S)
    wings(S)
    roofs(S)
    towers(S)
    keep(S)


def build_all(S):
    build_shell(S)
    from . import interiors
    interiors.furnish(S)
