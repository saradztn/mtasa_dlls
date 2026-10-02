# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# bld.py - procedural abandoned buildings.
#   * facade builder: every bay of every floor is an individually modelled opening (intact glass / broken glass /
#     open dark hole) with reveals, mullions, sill + head bands and piers; no alpha anywhere in the main model.
#   * corner collapse: a box cut (x >= cx0, y >= cy0, z >= cz0) removes facade cells with a ragged edge and exposes slab
#     edges, columns, rebar and a rubble-covered terrace.
#   * a companion "veg" mesh (alpha) with ivy, weeds and shrubs is returned separately.
#   * everything is built in local metres: footprint [0,W]x[0,D], origin at the south-west ground corner.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit
from . import gx
from .tex import IDX

TAU = 2 * np.pi


def MT(n):
    return IDX['af_' + n]


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


FACES = [  # origin(x,y), u dir, outward normal
    ((0, 0), (1, 0), (0, -1)),     # south
    (('W', 0), (0, 1), (1, 0)),    # east
    (('W', 'D'), (-1, 0), (0, 1)),  # north
    ((0, 'D'), (0, -1), (-1, 0)),  # west
]


class Building:
    def __init__(self, spec):
        s = dict(floors=8, fh=3.5, gh=4.4, bw=3.6, pw=0.55, sill=0.95, wh=1.55, wall='concrete', wall2=None,
                 ground='plain', dmg=0.5, cut=None, balcony=0.0, seed=1, tile=2.4, door=True, roof='flat',
                 cornice=True, ivy=6, weeds=1.0, tank=True, mullion=True, plinth='concrete', shell='concrete')
        s.update(spec)
        self.s = s
        self.W, self.D = s['W'], s['D']
        self.r = np.random.default_rng(s['seed'])
        n = s['floors']
        self.Z = [0.0] + [s['gh'] + s['fh'] * i for i in range(n)]
        self.H = self.Z[-1]
        self.M = Mesh()
        self.V = Mesh()
        self.C = Col()
        self.rub = []   # rubble boxes (collision)

    # ------------------------------------------------------------------ face frame helpers
    def frame(self, fi):
        o, u, n = FACES[fi]
        o = (self.W if o[0] == 'W' else o[0], self.D if o[1] == 'D' else o[1])
        L = self.W if fi in (0, 2) else self.D
        return np.array(o, float), np.array(u, float), np.array(n, float), L

    def P(self, fi, s, z, depth=0.0):
        o, u, n, L = self.frame(fi)
        p = o + u * s - n * depth
        return np.array([p[0], p[1], z])

    def nb(self, fi):
        return int(round(self.frame(fi)[3] / self.s['bw']))

    def bwf(self, fi):
        return self.frame(fi)[3] / self.nb(fi)

    # ------------------------------------------------------------------ cut test
    def in_cut(self, fi, s, z, bay):
        c = self.s['cut']
        if not c:
            return False
        p = self.P(fi, s, z, 0.0)
        if p[0] < c['x0'] - 0.01 or p[1] < c['y0'] - 0.01:
            return False
        jag = self.jag.get((fi, bay), 0.0)
        return z >= c['z0'] + jag

    # ------------------------------------------------------------------ planar quad on a face
    def fquad(self, M, fi, mat, s0, s1, z0, z1, d0, d1=None, tile=None, flip=False, uvmul=1.0):
        """vertical rectangle on face fi at depth d0 (and d1 for a sloped one)."""
        o, u, n, L = self.frame(fi)
        d1 = d0 if d1 is None else d1
        tile = tile or self.s['tile']
        pts = [self.P(fi, s0, z0, d0), self.P(fi, s1, z0, d0), self.P(fi, s1, z1, d1), self.P(fi, s0, z1, d1)]
        uv = [(s0 / tile * uvmul, -z0 / tile * uvmul), (s1 / tile * uvmul, -z0 / tile * uvmul),
              (s1 / tile * uvmul, -z1 / tile * uvmul), (s0 / tile * uvmul, -z1 / tile * uvmul)]
        hint = np.array([n[0], n[1], 0.0]) * (-1 if flip else 1)
        M.poly(pts, mat, hint=hint, uv=uv)

    def reveal(self, M, fi, mat, s0, s1, z0, z1, depth):
        """four quads of a window reveal from depth 0..depth"""
        o, u, n, L = self.frame(fi)
        t = 1.0
        for (a0, a1, b0, b1, hint) in ((s0, s0, z0, z1, u), (s1, s1, z0, z1, -u)):
            pts = [self.P(fi, a0, b0, 0), self.P(fi, a0, b0, depth), self.P(fi, a0, b1, depth), self.P(fi, a0, b1, 0)]
            M.poly(pts, mat, hint=np.array([hint[0], hint[1], 0.0]), tile=t)
        for zz, hz in ((z0, 1.0), (z1, -1.0)):
            pts = [self.P(fi, s0, zz, 0), self.P(fi, s1, zz, 0), self.P(fi, s1, zz, depth), self.P(fi, s0, zz, depth)]
            M.poly(pts, mat, hint=np.array([0, 0, hz]), tile=t)

    # ------------------------------------------------------------------ main
    def build(self):
        s = self.s
        r = self.r
        W, D = self.W, self.D
        self.jag = {}
        if s['cut']:
            for fi in (1, 2):
                for j in range(self.nb(fi)):
                    k = r.choice([0, 0, 1, 1, 2])
                    self.jag[(fi, j)] = k * s['fh']
        for fi in range(4):
            self.facade(fi)
        self.roof_and_top()
        if s['cut']:
            self.cut_interior()
        self.base_details()
        self.vegetation()
        self.collision()
        return self.M, self.V, self.C

    # ------------------------------------------------------------------ facade
    def facade(self, fi):
        s, r, M = self.s, self.r, self.M
        o, u, n, L = self.frame(fi)
        nb = self.nb(fi)
        bw = self.bwf(fi)
        pw = s['pw'] * (bw / s['bw'])
        nfl = len(self.Z) - 1
        wallm = MT(s['wall'])
        wall2 = MT(s['wall2']) if s['wall2'] else wallm
        # damage field: blobs on this face
        blobs = [(r.uniform(0, L), r.uniform(0, self.H), r.uniform(4, 11), r.uniform(0.35, 0.9)) for _ in range(4)]
        shop = s['ground'] == 'shop'
        door_bay = int(r.integers(1, max(2, nb - 1))) if (fi == 0 and s['door']) else -1
        states = {}
        for f in range(nfl):
            for j in range(nb):
                cs, cz = (j + 0.5) * bw, (self.Z[f] + self.Z[f + 1]) / 2
                v = r.uniform(0, 0.6)
                for bs, bz, br, bst in blobs:
                    v += bst * np.exp(-((cs - bs) ** 2 + (cz - bz) ** 2) / (2 * br * br * 0.5))
                v += 0.25 * (cz / self.H) + (0.35 if (f == 0 and shop) else 0.0)
                th_o = 1.1 - s['dmg']
                th_b = 0.78 - 0.8 * s['dmg']
                states[(f, j)] = 'open' if v > th_o else ('broken' if v > th_b else 'ok')
        # --- bands (sill / head) and windows per cell
        for f in range(nfl):
            z_lo, z_hi = self.Z[f], self.Z[f + 1]
            storefront = shop and f == 0
            sill = 0.5 if storefront else s['sill']
            wh = (z_hi - z_lo - sill - 0.95) if storefront else s['wh']
            for j in range(nb):
                cs = (j + 0.5) * bw
                cz = (z_lo + z_hi) / 2
                if self.in_cut(fi, cs, cz, j):
                    continue
                s0, s1 = j * bw + pw, (j + 1) * bw - pw
                if storefront:
                    s0, s1 = j * bw + pw * 0.8, (j + 1) * bw - pw * 0.8
                zs0, zs1 = z_lo + sill, z_lo + sill + wh
                isdoor = (j == door_bay and f == 0)
                if isdoor:
                    zs0 = z_lo
                    zs1 = z_lo + 2.6
                    s0, s1 = j * bw + bw * 0.22, (j + 1) * bw - bw * 0.22
                # sill & head bands (full bay width) and pier slabs
                self.fquad(M, fi, wallm, j * bw, (j + 1) * bw, z_lo, zs0, 0.0) if zs0 - z_lo > 1e-3 else None
                self.fquad(M, fi, wallm, j * bw, (j + 1) * bw, zs1, z_hi, 0.0)
                self.fquad(M, fi, wallm if not storefront else wall2, j * bw, s0, zs0, zs1, 0.0)
                self.fquad(M, fi, wallm if not storefront else wall2, s1, (j + 1) * bw, zs0, zs1, 0.0)
                st = states[(f, j)]
                if isdoor:
                    st = 'open'
                self.window(fi, f, j, s0, s1, zs0, zs1, st, storefront)
                # balcony
                if s['balcony'] > 0 and f >= 1 and not storefront and r.random() < s['balcony'] and fi in (0, 1, 2, 3):
                    self.balcony(fi, s0, s1, z_lo)

    def window(self, fi, f, j, s0, s1, z0, z1, st, storefront):
        s, r, M = self.s, self.r, self.M
        wallm = MT(s['wall'])
        depth = 0.32
        deep = 1.1 if st != 'ok' else depth
        self.reveal(M, fi, wallm, s0, s1, z0, z1, deep)
        o, u, n, L = self.frame(fi)
        inter = MT('interior')
        if st != 'ok':
            self.fquad(M, fi, inter, s0, s1, z0, z1, deep, tile=1.0)
        gd = depth - 0.12
        if st == 'ok':
            self.fquad(M, fi, MT('glass'), s0, s1, z0, z1, gd, tile=max(s1 - s0, z1 - z0), uvmul=1.0)
        elif st == 'broken':
            h = z1 - z0
            if r.random() < 0.5:
                zz1 = z0 + h * r.uniform(0.25, 0.7)
                zz0 = z0
            else:
                zz0 = z0 + h * r.uniform(0.35, 0.8)
                zz1 = z1
            ss0, ss1 = (s0, s1) if r.random() < 0.6 else ((s0, s0 + (s1 - s0) * r.uniform(0.4, 0.7)) if r.random() < 0.5 else (s1 - (s1 - s0) * r.uniform(0.4, 0.7), s1))
            self.fquad(M, fi, MT('glass_broken'), ss0, ss1, zz0, zz1, gd, tile=max(s1 - s0, z1 - z0))
        # frame: vertical + horizontal bars
        if s['mullion'] and not (st == 'open' and r.random() < 0.6):
            fm = MT('frame')
            bw_ = 0.07
            cd = gd - 0.04
            if st != 'open' or r.random() < 0.5:
                cs = (s0 + s1) / 2
                self.fquad(M, fi, fm, cs - bw_, cs + bw_, z0, z1, cd, tile=1.0)
            if not storefront:
                zc = z0 + (z1 - z0) * 0.62
                self.fquad(M, fi, fm, s0, s1, zc - bw_, zc + bw_, cd, tile=1.0)
            self.fquad(M, fi, fm, s0, s0 + 0.09, z0, z1, cd - 0.01, tile=1.0)
            self.fquad(M, fi, fm, s1 - 0.09, s1, z0, z1, cd - 0.01, tile=1.0)
            self.fquad(M, fi, fm, s0, s1, z1 - 0.09, z1, cd - 0.01, tile=1.0)
            self.fquad(M, fi, fm, s0, s1, z0, z0 + 0.09, cd - 0.01, tile=1.0)

    def balcony(self, fi, s0, s1, zf):
        s, r, M = self.s, self.r, self.M
        o, u, n, L = self.frame(fi)
        ext = r.uniform(1.0, 1.5)
        a, b = s0 - 0.25, s1 + 0.25
        if (self.s['cut'] and self.in_cut(fi, (a + b) / 2, zf + 1, int(((a + b) / 2) / self.bwf(fi)))):
            return
        c = [self.P(fi, a, zf, 0), self.P(fi, b, zf, 0), self.P(fi, b, zf, -ext), self.P(fi, a, zf, -ext)]
        lo = np.min(c, 0) + [0, 0, -0.16]
        hi = np.max(c, 0)
        M.box(lo, hi, MT('concrete'), tile=2.0)
        # corrugated sheet railing with rust, partly missing
        if r.random() < 0.8:
            zr0, zr1 = zf, zf + 1.05 - (0.4 if r.random() < 0.3 else 0)
            q = [self.P(fi, a, zr0, -ext + 0.04), self.P(fi, b, zr0, -ext + 0.04), self.P(fi, b, zr1, -ext + 0.04), self.P(fi, a, zr1, -ext + 0.04)]
            M.poly(q, MT('corrugated'), hint=np.array([n[0], n[1], 0.0]), uv=[(0, 1), (1.2, 1), (1.2, 0), (0, 0)])
            for sd in (a, b):
                q = [self.P(fi, sd, zr0, 0), self.P(fi, sd, zr0, -ext + 0.04), self.P(fi, sd, zr1, -ext + 0.04), self.P(fi, sd, zr1, 0)]
                M.poly(q, MT('corrugated'), hint=np.array([u[0], u[1], 0.0]) * (1 if sd == b else -1), tile=1.5)

    # ------------------------------------------------------------------ roof, parapet, rooftop clutter
    def roof_and_top(self):
        s, r, M = self.s, self.r, self.M
        W, D, H = self.W, self.D, self.H
        c = s['cut']
        roofm, conc = MT('roofing'), MT('concrete')
        if c:
            parts = [((0, 0), (c['x0'], D)), ((c['x0'], 0), (W, c['y0']))]
        else:
            parts = [((0, 0), (W, D))]
        for lo, hi in parts:
            M.box((lo[0], lo[1], H - 0.3), (hi[0], hi[1], H), roofm, tile=3.0, mats={'-z': conc, '+x': conc, '-x': conc, '+y': conc, '-y': conc})
        # parapet + cornice along faces (skip cut)
        for fi in range(4):
            o, u, n, L = self.frame(fi)
            ranges = [(0, L)]
            if c:
                if fi == 1:
                    ranges = [(0, c['y0'])]
                elif fi == 2:
                    ranges = [(W - c['x0'], W)]
                elif fi == 0:
                    ranges = [(0, L)]
            for a, b in ranges:
                if s['cornice']:
                    # drop the front face (visible) onto the facade with mild overhang
                    M.box(np.minimum(self.P(fi, a, H - 0.5, -0.28), self.P(fi, b, H - 0.05, 0.35)),
                          np.maximum(self.P(fi, a, H - 0.5, -0.28), self.P(fi, b, H - 0.05, 0.35)), conc, tile=2.0)
                    # parapet
                    pt = 0.3
                    ptop = H + (0.8 if r.random() < 0.9 else 0.5)
                    M.box(np.minimum(self.P(fi, a, H, 0.0), self.P(fi, b, ptop, pt)),
                          np.maximum(self.P(fi, a, H, 0.0), self.P(fi, b, ptop, pt)), conc, tile=2.0)
        # rooftop clutter
        n_units = int(r.integers(3, 6))
        for _ in range(n_units):
            w, d, h = r.uniform(1.2, 3.2), r.uniform(1.2, 3.0), r.uniform(0.9, 2.2)
            w, d = min(w, W * 0.3), min(d, D * 0.3)
            x, y = r.uniform(1, max(1.5, W - 1 - w)), r.uniform(1, max(1.5, D - 1 - d))
            if c and x + w > c['x0'] - 0.5 and y + d > c['y0'] - 0.5:
                continue
            M.box((x, y, H), (x + w, y + d, H + h), MT('steel'), tile=1.5)
            M.box((x - 0.05, y - 0.05, H + h), (x + w + 0.05, y + d + 0.05, H + h + 0.12), MT('rust'), tile=1.5)
        if s['tank']:
            x, y = r.uniform(3, W - 3), r.uniform(3, D - 3)
            if not (c and x > c['x0'] - 2.5 and y > c['y0'] - 2.5):
                for dx, dy in ((-0.9, -0.9), (0.9, -0.9), (0.9, 0.9), (-0.9, 0.9)):
                    gx.bar(M, (x + dx, y + dy, H), (x + dx, y + dy, H + 2.2), 0.12, MT('rust'))
                M.prism((x, y), 1.3, H + 2.2, H + 4.2, 14, MT('corrugated'), tile=2.0, cap_top=True)
                M.cone((x, y), 1.35, H + 4.2, H + 4.9, 14, MT('rust'), tile=2.0)
        # antenna masts
        for _ in range(int(r.integers(1, 3))):
            x, y = r.uniform(2, W - 2), r.uniform(2, D - 2)
            if c and x > c['x0'] - 1 and y > c['y0'] - 1:
                continue
            hh = r.uniform(5, 11)
            gx.bar(M, (x, y, H), (x + r.uniform(-0.3, 0.3), y + r.uniform(-0.3, 0.3), H + hh), 0.1, MT('steel'))
            gx.bar(M, (x, y, H + hh * 0.7), (x + 1.2, y, H + hh * 0.7 + 0.1), 0.05, MT('steel'))

    # ------------------------------------------------------------------ exposed interior of the collapse
    def cut_interior(self):
        s, r, M = self.s, self.r, self.M
        c = s['cut']
        W, D, H = self.W, self.D, self.H
        inter, conc, rust = MT('interior'), MT('concrete'), MT('rust')
        cx0, cy0, cz0 = c['x0'], c['y0'], c['z0']
        # dark inner walls
        M.poly([(cx0, cy0, cz0), (cx0, D, cz0), (cx0, D, H), (cx0, cy0, H)], inter, hint=(1, 0, 0), tile=1.0)
        M.poly([(cx0, cy0, cz0), (W, cy0, cz0), (W, cy0, H), (cx0, cy0, H)], inter, hint=(0, 1, 0), tile=1.0)
        # terrace slab (broken top floor of the surviving lower part)
        M.box((cx0, cy0, cz0 - 0.4), (W, D, cz0), conc, tile=2.5)
        # slab edges hanging out of the standing structure
        for f, z in enumerate(self.Z):
            if z <= cz0 + 0.1 or z >= H - 0.1:
                continue
            for axis in (0, 1):
                L = (D - cy0) if axis == 0 else (W - cx0)
                k = int(max(2, L // 3))
                for i in range(k):
                    if r.random() < 0.28 + 0.08 * (f / len(self.Z)):
                        continue
                    ov = r.uniform(0.4, 3.2)
                    a0, a1 = cy0 + i * L / k, cy0 + (i + 1) * L / k if axis == 0 else cx0 + (i + 1) * L / k
                    if axis == 0:
                        a0 = cy0 + i * L / k
                        M.box((cx0, a0, z - 0.3), (cx0 + ov, a1 - 0.05, z), conc, tile=2.0)
                        for _ in range(int(r.integers(1, 3))):
                            yy = r.uniform(a0 + 0.2, a1 - 0.2)
                            gx.bar(M, (cx0 + ov - 0.1, yy, z - 0.15), (cx0 + ov + r.uniform(0.3, 0.9), yy, z - 0.15 - r.uniform(0.1, 0.8)), 0.04, rust)
                    else:
                        a0 = cx0 + i * L / k
                        M.box((a0, cy0, z - 0.3), (a1 - 0.05, cy0 + ov, z), conc, tile=2.0)
                        for _ in range(int(r.integers(1, 3))):
                            xx = r.uniform(a0 + 0.2, a1 - 0.2)
                            gx.bar(M, (xx, cy0 + ov - 0.1, z - 0.15), (xx, cy0 + ov + r.uniform(0.3, 0.9), z - 0.15 - r.uniform(0.1, 0.8)), 0.04, rust)
        # columns along the cut planes
        cb = self.s['bw']
        for axis in (0, 1):
            L = (D - cy0) if axis == 0 else (W - cx0)
            for i in range(int(L // cb) + 1):
                pos = (cy0 if axis == 0 else cx0) + i * cb
                top = H - r.uniform(0, 2 * s['fh']) * (1 if r.random() < 0.6 else 0)
                if pos > (D if axis == 0 else W) - 0.3:
                    continue
                if axis == 0:
                    M.box((cx0 - 0.2, pos, cz0), (cx0 + 0.45, pos + 0.5, top), conc, tile=2.0)
                    gx.bar(M, (cx0 + 0.1, pos + 0.2, top), (cx0 + 0.15, pos + 0.25, top + r.uniform(0.3, 1.2)), 0.04, rust)
                else:
                    M.box((pos, cy0 - 0.2, cz0), (pos + 0.5, cy0 + 0.45, top), conc, tile=2.0)
                    gx.bar(M, (pos + 0.2, cy0 + 0.1, top), (pos + 0.25, cy0 + 0.15, top + r.uniform(0.3, 1.2)), 0.04, rust)
        # rubble heaps on terrace + at the foot
        for _ in range(int(r.integers(10, 16))):
            x = r.uniform(cx0 + 1, W - 1)
            y = r.uniform(cy0 + 1, D - 1)
            sz = r.uniform(0.5, 1.6)
            gx.rock(M, (x, y, cz0 + sz * 0.15), (sz * 1.3, sz, sz * 0.8), conc, int(r.integers(1, 10 ** 6)), n=10)
        for _ in range(int(r.integers(14, 22))):
            ang = r.uniform(0, TAU)
            # fallen debris outside the walls, below the cut
            side = r.integers(0, 2)
            if side == 0:
                x, y = W + r.uniform(0.5, 6.0), r.uniform(cy0 - 4, D + 2)
            else:
                x, y = r.uniform(cx0 - 4, W + 2), D + r.uniform(0.5, 6.0)
            sz = r.uniform(0.35, 1.5)
            gx.rock(M, (x, y, sz * 0.1), (sz * 1.4, sz, sz * 0.8), conc, int(r.integers(1, 10 ** 6)), n=10)
            self.rub.append(((x - sz, y - sz, 0), (x + sz, y + sz, sz * 0.8)))
        # slanted fallen slabs
        for _ in range(int(r.integers(2, 4))):
            side = r.integers(0, 2)
            if side == 0:
                x, y = W + r.uniform(1.5, 5), r.uniform(cy0, D)
            else:
                x, y = r.uniform(cx0, W), D + r.uniform(1.5, 5)
            ln = r.uniform(2.5, 4.5)
            dirv = unit(np.array([r.normal(), r.normal(), 0.0]))
            p0 = np.array([x, y, 0.2])
            p1 = p0 + dirv * ln + np.array([0, 0, r.uniform(0.6, 1.6)])
            gx.bar(M, p0, p1, ln * 0.7, conc, h=0.28, tile=2.0)

    # ------------------------------------------------------------------ plinth, stoop, debris, doors
    def base_details(self):
        s, r, M = self.s, self.r, self.M
        W, D = self.W, self.D
        conc = MT(s['plinth'])
        for fi in range(4):
            o, u, n, L = self.frame(fi)
            a = self.P(fi, 0, 0, -0.14)
            b = self.P(fi, L, 0.55, 0.0)
            M.box(np.minimum(a, b), np.maximum(a, b), conc, tile=2.0)
        # scattered debris, broken glass litter (small chunks), fallen bricks
        for _ in range(int(r.integers(16, 26))):
            fi = int(r.integers(0, 4))
            o, u, n, L = self.frame(fi)
            p = self.P(fi, r.uniform(1, L - 1), 0, -r.uniform(0.5, 2.8))
            sz = r.uniform(0.14, 0.5)
            gx.rock(M, (p[0], p[1], sz * 0.12), (sz * 1.3, sz, sz * 0.7), MT(s['wall'] if r.random() < 0.5 else 'concrete'), int(r.integers(1, 10 ** 6)), n=8)

    # ------------------------------------------------------------------ vegetation (alpha companion)
    def vegetation(self):
        s, r, V = self.s, self.r, self.V
        ivy, weeds, dead, leaf = MT('ivy'), MT('weeds'), MT('dead_grass'), MT('leaf')
        up = np.array([0, 0, 1.0])
        for fi in range(4):
            o, u, n, L = self.frame(fi)
            nrm = np.array([n[0] * 0.4, n[1] * 0.4, 0.9])
            for k in range(int(s['ivy'] * L / 30 + r.integers(0, 3))):
                s0 = r.uniform(1, L - 1)
                top = r.uniform(2.5, max(2.6, min(self.H * 0.75, 3.5 + r.integers(1, 5) * s['fh'])))
                z = 0.8
                while z < top:
                    w = r.uniform(1.0, 1.7)
                    sj = s0 + r.normal(0, 0.6)
                    cpos = self.P(fi, np.clip(sj, 0.5, L - 0.5), z, -0.06)
                    if s['cut'] and self.in_cut(fi, sj, z, int(sj / self.bwf(fi))):
                        break
                    gx.card(V, cpos, np.array([u[0], u[1], 0]) * w / 2, up * w / 2, ivy, nrm, double=False)
                    z += w * 0.8
        # weeds around the base
        for fi in range(4):
            o, u, n, L = self.frame(fi)
            cnt = int(L / 2.8 * s['weeds'])
            for i in range(cnt):
                p = self.P(fi, r.uniform(0.3, L - 0.3), 0, -r.uniform(0.15, 1.1))
                hgt = r.uniform(0.6, 1.5)
                w = hgt * r.uniform(0.9, 1.3)
                ang = r.uniform(0, np.pi)
                a = np.array([np.cos(ang), np.sin(ang), 0]) * w / 2
                mat = weeds if r.random() < 0.6 else dead
                gx.card(V, p + up * hgt / 2 * 0.98, a, up * hgt / 2, mat, up, double=True)
                a2 = np.array([-np.sin(ang), np.cos(ang), 0]) * w / 2
                gx.card(V, p + up * hgt / 2 * 0.98, a2, up * hgt / 2, mat, up, double=True)
        # terrace / roof shrubs
        c = s['cut']
        if c:
            for _ in range(int(r.integers(8, 14))):
                p = np.array([r.uniform(c['x0'] + 0.5, self.W - 0.5), r.uniform(c['y0'] + 0.5, self.D - 0.5), c['z0']])
                hgt = r.uniform(0.8, 2.2)
                for ang in (0.0, np.pi / 2):
                    a = np.array([np.cos(ang), np.sin(ang), 0]) * hgt * 0.6
                    gx.card(V, p + up * hgt / 2, a, up * hgt / 2, weeds if r.random() < 0.6 else leaf, up)

    # ------------------------------------------------------------------ collision
    def collision(self):
        C, s = self.C, self.s
        W, D, H = self.W, self.D, self.H
        c = s['cut']
        if c:
            C.box((0, 0, 0), (W, D, c['z0']))
            C.box((0, 0, c['z0']), (c['x0'], D, H + 0.8))
            C.box((c['x0'], 0, c['z0']), (W, c['y0'], H + 0.8))
        else:
            C.box((0, 0, 0), (W, D, H + 0.8))
        for lo, hi in self.rub:
            C.box(lo, hi)
