# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# mb.py - mesh builder + architectural primitives (walls with arched openings, boxes, prisms,
#         cones, stairs ...) + collision collector.
#
# Conventions: right handed, X right, Y forward, Z up, 1 unit = 1 m.
# Triangles are stored CCW when seen from OUTSIDE (the DFF writer converts to RW order).
# Every face is flat shaded (vertices are not shared between faces) so that hard stone edges are
# crisp; smooth round shapes pass explicit normals.
# -----------------------------------------------------------------------------
import numpy as np

TAU = np.pi * 2


def v3(*a):
    return np.array(a, dtype=np.float64)


def unit(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


class Mesh:
    """Collection of surface chunks. chunk = (pos, nrm, uv, tris, mat, emis)"""

    def __init__(self):
        self.chunks = []

    # ------------------------------------------------------------------ raw
    def add(self, pos, nrm, uv, tris, mat, emis=0.0):
        pos = np.asarray(pos, np.float64).reshape(-1, 3)
        nrm = np.asarray(nrm, np.float64).reshape(-1, 3)
        uv = np.asarray(uv, np.float64).reshape(-1, 2)
        tris = np.asarray(tris, np.int64).reshape(-1, 3)
        self.chunks.append((pos, nrm, uv, tris, int(mat), float(emis)))

    # ------------------------------------------------------------------ planar uv
    @staticmethod
    def planar_uv(P, n, tile, off=(0.0, 0.0)):
        ax = int(np.argmax(np.abs(n)))
        if ax == 2:
            a, b = P[:, 0], P[:, 1] * (1 if n[2] > 0 else -1)
        elif ax == 0:
            a, b = P[:, 1] * (1 if n[0] > 0 else -1), -P[:, 2]
        else:
            a, b = P[:, 0] * (-1 if n[1] > 0 else 1), -P[:, 2]
        return np.stack([a / tile + off[0], b / tile + off[1]], -1)

    # ------------------------------------------------------------------ polygons
    def poly(self, pts, mat, hint=None, uv=None, tile=3.0, emis=0.0, uvoff=(0, 0), double=False):
        """convex planar polygon (fan). pts ordered CCW seen from outside (flipped automatically to match
        `hint`, a direction that should point to the viewer side)."""
        P = np.asarray(pts, np.float64)
        k = len(P)
        n = np.zeros(3)
        for i in range(1, k - 1):
            n += np.cross(P[i] - P[0], P[i + 1] - P[0])
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            return
        n /= ln
        order = np.arange(k)
        if hint is not None and np.dot(n, hint) < 0:
            order = order[::-1]
            n = -n
        P = P[order]
        UV = None if uv is None else np.asarray(uv, np.float64)[order]
        if UV is None:
            UV = self.planar_uv(P, n, tile, uvoff)
        tr = [[0, i, i + 1] for i in range(1, k - 1)]
        self.add(P, np.tile(n, (k, 1)), UV, tr, mat, emis)
        if double:
            self.add(P[::-1], np.tile(-n, (k, 1)), UV[::-1], [[0, i, i + 1] for i in range(1, k - 1)], mat, emis)

    def quad(self, p0, p1, p2, p3, mat, **kw):
        self.poly([p0, p1, p2, p3], mat, **kw)

    # ------------------------------------------------------------------ solids
    def box(self, lo, hi, mat, tile=3.0, skip=(), emis=0.0, mats=None, uvoff=(0, 0)):
        """axis aligned box; skip: names of faces to omit among '+x','-x','+y','-y','+z','-z'"""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        faces = {
            '+x': ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
            '-x': ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], (-1, 0, 0)),
            '+y': ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], (0, 1, 0)),
            '-y': ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
            '+z': ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
            '-z': ([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], (0, 0, -1)),
        }
        for k, (pts, n) in faces.items():
            if k in skip:
                continue
            m = mat if mats is None else mats.get(k, mat)
            self.poly(pts, m, hint=np.array(n, float), tile=tile, emis=emis, uvoff=uvoff)

    def prism(self, center, radius, z0, z1, n, mat, tile=3.0, theta0=0.0, cap_top=True, cap_bot=False, smooth=False,
              emis=0.0, ex=1.0, ey=1.0):
        """vertical n-gon prism (flat or smooth shaded), u = arc length / tile"""
        th = theta0 + np.arange(n + 1) * TAU / n
        cx, cy = center
        ring = np.stack([cx + radius * ex * np.cos(th), cy + radius * ey * np.sin(th)], -1)
        for i in range(n):
            a, b = ring[i], ring[i + 1]
            ln = np.linalg.norm(b - a)
            u0 = i * ln / tile
            u1 = (i + 1) * ln / tile
            P = [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
            UV = [(u0, -z0 / tile), (u1, -z0 / tile), (u1, -z1 / tile), (u0, -z1 / tile)]
            mid = (a + b) / 2 - np.array([cx, cy])
            hint = np.array([mid[0], mid[1], 0.0])
            if smooth:
                na = np.array([np.cos(th[i]), np.sin(th[i]), 0.0])
                nb = np.array([np.cos(th[i + 1]), np.sin(th[i + 1]), 0.0])
                Pn = np.array(P)
                self.add(Pn, [na, nb, nb, na], UV, [[0, 1, 2], [0, 2, 3]], mat, emis)
            else:
                self.poly(P, mat, hint=hint, uv=UV, emis=emis)
        if cap_top:
            self.poly([(r[0], r[1], z1) for r in ring[:-1]], mat, hint=(0, 0, 1), tile=tile, emis=emis)
        if cap_bot:
            self.poly([(r[0], r[1], z0) for r in ring[:-1]], mat, hint=(0, 0, -1), tile=tile, emis=emis)

    def cone(self, center, radius, z0, z1, n, mat, tile=3.0, theta0=0.0, smooth=False, emis=0.0, r_top=0.0, slope_tile=None):
        """roof cone (or frustum if r_top>0); u = angle fraction * circumference/tile, v = slant/tile"""
        cx, cy = center
        th = theta0 + np.arange(n + 1) * TAU / n
        slant = np.hypot(radius - r_top, z1 - z0)
        circ = TAU * radius
        for i in range(n):
            a = np.array([cx + radius * np.cos(th[i]), cy + radius * np.sin(th[i]), z0])
            b = np.array([cx + radius * np.cos(th[i + 1]), cy + radius * np.sin(th[i + 1]), z0])
            if r_top > 0:
                c = np.array([cx + r_top * np.cos(th[i + 1]), cy + r_top * np.sin(th[i + 1]), z1])
                d = np.array([cx + r_top * np.cos(th[i]), cy + r_top * np.sin(th[i]), z1])
                P = [a, b, c, d]
                UV = [(i * circ / n / tile, 0), ((i + 1) * circ / n / tile, 0), ((i + 1) * circ / n / tile * r_top / radius, -slant / tile),
                      (i * circ / n / tile * r_top / radius, -slant / tile)]
            else:
                P = [a, b, np.array([cx, cy, z1])]
                UV = [(i * circ / n / tile, 0), ((i + 1) * circ / n / tile, 0), ((i + 0.5) * circ / n / tile, -slant / tile)]
            mid = (a + b) / 2 - np.array([cx, cy, 0])
            slope = (radius - r_top) / max(z1 - z0, 1e-6)
            hint = np.array([mid[0], mid[1], 0.0])
            hint = hint / max(np.linalg.norm(hint), 1e-9)
            hint = np.array([hint[0], hint[1], slope])
            if smooth:
                nn = [unit([np.cos(th[i]), np.sin(th[i]), slope]), unit([np.cos(th[i + 1]), np.sin(th[i + 1]), slope])]
                nrm = [nn[0], nn[1]] + ([nn[1], nn[0]] if r_top > 0 else [unit([np.cos((th[i] + th[i + 1]) / 2), np.sin((th[i] + th[i + 1]) / 2), slope])])
                Pn = np.array(P)
                # orient
                nf = np.cross(Pn[1] - Pn[0], Pn[2] - Pn[0])
                tr = [[0, 1, 2], [0, 2, 3]] if r_top > 0 else [[0, 1, 2]]
                if np.dot(nf, hint) < 0:
                    tr = [t[::-1] for t in tr]
                self.add(Pn, nrm, UV, tr, mat, emis)
            else:
                self.poly(P, mat, hint=hint, uv=UV, emis=emis)


# ---------------------------------------------------------------------------------------------
# collision collector
# ---------------------------------------------------------------------------------------------
class Col:
    def __init__(self):
        self.boxes = []       # (lo, hi)
        self.prisms = []      # list of 8x3 corner arrays (non axis aligned convex boxes)

    def box(self, lo, hi):
        a, b = np.asarray(lo, float), np.asarray(hi, float)
        lo, hi = np.minimum(a, b), np.maximum(a, b)
        if (hi - lo).min() < 1e-4:
            return
        self.boxes.append((tuple(map(float, lo)), tuple(map(float, hi))))

    def strip(self, a, b, t, z0, z1):
        """vertical slab following the segment a-b (2D) with thickness t between z0 and z1"""
        if z1 - z0 < 1e-4:
            return
        a = np.asarray(a, float)
        b = np.asarray(b, float)
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-6:
            return
        d /= L
        nl = np.array([-d[1], d[0]])
        if abs(d[0]) > 0.99999 or abs(d[1]) > 0.99999:
            lo = np.minimum(a, b) - np.abs(nl) * t / 2
            hi = np.maximum(a, b) + np.abs(nl) * t / 2
            self.box((lo[0], lo[1], z0), (hi[0], hi[1], z1))
        else:
            c = []
            for z in (z0, z1):
                for p in (a - nl * t / 2, b - nl * t / 2, b + nl * t / 2, a + nl * t / 2):
                    c.append((p[0], p[1], z))
            self.prisms.append(np.array(c))


# ---------------------------------------------------------------------------------------------
# arched openings and walls
# ---------------------------------------------------------------------------------------------
def arch_fn(s0, s1, zs, k=1.0):
    """pointed (two-centre) arch above springline zs spanning [s0,s1]; k = radius / span (1 = equilateral)"""
    w = s1 - s0
    r = k * w
    xc = (s0 + s1) / 2

    def f(s):
        s = np.asarray(s, float)
        left = zs + np.sqrt(np.maximum(r * r - (s - (s0 + r)) ** 2, 0.0))
        right = zs + np.sqrt(np.maximum(r * r - (s - (s1 - r)) ** 2, 0.0))
        return np.where(s <= xc, left, right)
    return f, float(f(xc))


class Opening:
    def __init__(self, s0, s1, zb, ztop, kind='rect', k=1.0, n=8):
        """kind 'rect': flat top at ztop.  kind 'arch': straight jambs up to ztop (= springline) then pointed arch."""
        self.s0, self.s1, self.zb, self.zt, self.kind, self.k, self.n = s0, s1, zb, ztop, kind, k, n
        if kind == 'arch':
            self.fn, self.apex = arch_fn(s0, s1, ztop, k)
        else:
            self.fn, self.apex = (lambda s: np.full_like(np.asarray(s, float), ztop)), ztop

    def top(self, s):
        return float(self.fn(s))

    def samples(self):
        if self.kind != 'arch':
            return [self.s0, self.s1]
        xc = (self.s0 + self.s1) / 2
        # denser near the springing where curvature is largest in z
        t = np.linspace(0, 1, self.n + 1)
        left = self.s0 + (xc - self.s0) * np.sin(t * np.pi / 2)
        right = xc + (self.s1 - xc) * (1 - np.cos(t * np.pi / 2))
        return list(left) + list(right[1:])


def wall(M, C, mat_a, mat_b, a, b, z0, z1, t, openings=(), tile=3.0, caps=(True, True), mat_top=None, mat_rev=None,
         collide=True, emis=0.0, uoff=0.0, top_cap=True):
    """Vertical wall along centre line a->b (thickness t). Face A faces the LEFT of a->b, face B the right.
    mat_rev: material of the reveals/soffits (default mat_a)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = b - a
    L = float(np.linalg.norm(d))
    d /= L
    nl = np.array([-d[1], d[0]])
    mat_rev = mat_a if mat_rev is None else mat_rev
    mat_top = mat_a if mat_top is None else mat_top
    ops = sorted(openings, key=lambda o: o.s0)

    def P(s, z, side):
        q = a + d * s + nl * side * t / 2
        return (q[0], q[1], z)

    def U(s, z):
        base = a + d * s
        return (np.dot(base, d) / tile + uoff, -z / tile)

    def face(s_list, zlow, zhigh, mat_for_side):
        # polygon between z-profiles: zlow/zhigh are lists aligned with s_list
        for side, mat in ((+1, mat_a), (-1, mat_b)):
            pts = [P(s, zl, side) for s, zl in zip(s_list, zlow)] + [P(s, zh, side) for s, zh in zip(s_list[::-1], zhigh[::-1])]
            uvs = [U(s, zl) for s, zl in zip(s_list, zlow)] + [U(s, zh) for s, zh in zip(s_list[::-1], zhigh[::-1])]
            hint = np.array([nl[0], nl[1], 0.0]) * side
            M.poly(pts, mat, hint=hint, uv=uvs, emis=emis if side > 0 else 0.0)

    bps = [0.0, L]
    for o in ops:
        bps += o.samples()
    bps = sorted(set(round(x, 6) for x in bps))
    for sa, sb in zip(bps[:-1], bps[1:]):
        if sb - sa < 1e-6:
            continue
        mid = (sa + sb) / 2
        o = next((o for o in ops if o.s0 - 1e-9 <= mid <= o.s1 + 1e-9), None)
        if o is None:
            face([sa, sb], [z0, z0], [z1, z1], None)
            if collide:
                C.strip(a + d * sa, a + d * sb, t, z0, z1)
            continue
        ta, tb = o.top(sa), o.top(sb)
        if o.zb > z0 + 1e-6:
            face([sa, sb], [z0, z0], [o.zb, o.zb], None)
            M.quad(P(sa, o.zb, +1), P(sb, o.zb, +1), P(sb, o.zb, -1), P(sa, o.zb, -1), mat_rev, hint=(0, 0, 1), tile=tile)
            if collide:
                C.strip(a + d * sa, a + d * sb, t, z0, o.zb)
        if min(ta, tb) < z1 - 1e-6:
            face([sa, sb], [ta, tb], [z1, z1], None)
            M.quad(P(sa, ta, +1), P(sb, tb, +1), P(sb, tb, -1), P(sa, ta, -1), mat_rev, hint=(0, 0, -1), tile=tile)
            if collide:
                C.strip(a + d * sa, a + d * sb, t, max(ta, tb), z1)
    for o in ops:
        for s, sign in ((o.s0, +1), (o.s1, -1)):
            zt = o.top(s)
            hint = np.array([d[0], d[1], 0.0]) * sign
            M.quad(P(s, o.zb, +1), P(s, o.zb, -1), P(s, zt, -1), P(s, zt, +1), mat_rev, hint=hint, tile=tile)
    if top_cap:
        M.quad(P(0, z1, +1), P(L, z1, +1), P(L, z1, -1), P(0, z1, -1), mat_top, hint=(0, 0, 1), tile=tile)
    if caps[0]:
        M.quad(P(0, z0, -1), P(0, z0, +1), P(0, z1, +1), P(0, z1, -1), mat_rev, hint=(-d[0], -d[1], 0), tile=tile)
    if caps[1]:
        M.quad(P(L, z0, +1), P(L, z0, -1), P(L, z1, -1), P(L, z1, +1), mat_rev, hint=(d[0], d[1], 0), tile=tile)


def stairs(M, C, mat, x0, x1, y_start, z_start, direction, n, rise, run, mat_side=None, tile=2.0, full_solid=True,
           z_floor=0.0, tread_mat=None):
    """straight flight along +y (direction=+1) or -y (-1) between x0..x1; step i has top z_start+rise*(i+1),
    y span [y_start+direction*run*i, y_start+direction*run*(i+1)].  Solid down to z_floor."""
    mat_side = mat if mat_side is None else mat_side
    tread_mat = mat if tread_mat is None else tread_mat
    for i in range(n):
        ya = y_start + direction * run * i
        yb = y_start + direction * run * (i + 1)
        lo_y, hi_y = min(ya, yb), max(ya, yb)
        ztop = z_start + rise * (i + 1)
        zbot = z_floor if full_solid else ztop - 0.25
        # riser faces toward the downhill (start) side, tread on top, sides
        M.box((x0, lo_y, zbot), (x1, hi_y, ztop), mat, tile=tile, mats={'+z': tread_mat, '+x': mat_side, '-x': mat_side},
              skip=('-z', '+y' if direction > 0 else '-y'))
        C.box((x0, lo_y, zbot), (x1, hi_y, ztop))
