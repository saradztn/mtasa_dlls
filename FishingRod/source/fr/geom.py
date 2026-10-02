# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# geom.py - procedural mesh primitives (skin/lathe, sweeps, tori, sector solids)
#
# Conventions
#   * Right handed, Z up, Y forward (GTA / MTA world).  1 unit = 1 metre.
#   * Every surface is built as a (rows x cols) grid.  Triangle winding is
#     auto-oriented against an analytic outward reference so that CCW (seen
#     from outside) == front face.  Normals are accumulated per grid vertex so
#     hard edges are made explicitly by duplicating a profile row.
# -----------------------------------------------------------------------------
import numpy as np

TAU = np.pi * 2.0


def norm(v, axis=-1, eps=1e-12):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, eps)


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


# ----------------------------------------------------------------------------
# Part container
# ----------------------------------------------------------------------------
class Part:
    """A chunk of triangles sharing one material."""

    def __init__(self, name, mat, pos, nrm, uv, tris):
        self.name = name
        self.mat = mat
        self.pos = np.asarray(pos, np.float64).reshape(-1, 3)
        self.nrm = np.asarray(nrm, np.float64).reshape(-1, 3)
        self.uv = np.asarray(uv, np.float64).reshape(-1, 2)
        self.tris = np.asarray(tris, np.int64).reshape(-1, 3)

    def transformed(self, M=None, t=None):
        pos = self.pos.copy()
        nrm = self.nrm.copy()
        if M is not None:
            pos = pos @ M.T
            nrm = norm(nrm @ M.T)
        if t is not None:
            pos = pos + np.asarray(t)
        return Part(self.name, self.mat, pos, nrm, self.uv.copy(), self.tris.copy())


# ----------------------------------------------------------------------------
# Grid -> Part
# ----------------------------------------------------------------------------
def grid_part(name, mat, P, UV, ref, closed_u=False, closed_v=False, keep=None):
    """Convert a vertex grid to a Part.

    P   : (nv, nu, 3) positions   (rows = v/profile direction, cols = u/around)
    UV  : (nv, nu, 2)
    ref : (nv, nu, 3) outward reference normal (analytic, may be approximate)
    closed_u / closed_v : last col/row duplicates first (seam) -> normals merged
    keep: optional (nv-1, nu-1) bool mask of quads to keep
    """
    P = np.asarray(P, np.float64)
    nv, nu, _ = P.shape
    ref = np.asarray(ref, np.float64)
    idx = np.arange(nv * nu).reshape(nv, nu)
    a = idx[:-1, :-1]
    b = idx[:-1, 1:]
    c = idx[1:, 1:]
    d = idx[1:, :-1]
    # two triangles per quad
    t1 = np.stack([a, b, c], -1).reshape(-1, 3)
    t2 = np.stack([a, c, d], -1).reshape(-1, 3)
    tris = np.concatenate([t1, t2], 0)
    if keep is not None:
        k = np.asarray(keep).reshape(-1)
        tris = np.concatenate([t1[k], t2[k]], 0)

    Pf = P.reshape(-1, 3)
    fn = np.cross(Pf[tris[:, 1]] - Pf[tris[:, 0]], Pf[tris[:, 2]] - Pf[tris[:, 0]])
    area2 = np.linalg.norm(fn, axis=1)
    good = area2 > 1e-13
    # orientation vs analytic reference
    reff = ref.reshape(-1, 3)
    rf = reff[tris[:, 0]] + reff[tris[:, 1]] + reff[tris[:, 2]]
    score = np.sum(np.einsum('ij,ij->i', fn[good], rf[good]))
    if score < 0:
        tris = tris[:, ::-1].copy()
        fn = -fn
    vn = np.zeros_like(Pf)
    for k in range(3):
        np.add.at(vn, tris[good][:, k], fn[good])
    vn = vn.reshape(nv, nu, 3)
    if closed_u:
        s = vn[:, 0] + vn[:, -1]
        vn[:, 0] = s
        vn[:, -1] = s
    if closed_v:
        s = vn[0] + vn[-1]
        vn[0] = s
        vn[-1] = s
    ln = np.linalg.norm(vn, axis=-1, keepdims=True)
    bad = ln[..., 0] < 1e-10
    vn = vn / np.maximum(ln, 1e-12)
    if bad.any():
        vn[bad] = norm(ref)[bad]
    tris = tris[good]
    return _compact(Part(name, mat, Pf, vn.reshape(-1, 3), np.asarray(UV, np.float64).reshape(-1, 2), tris))


def _compact(part):
    used = np.unique(part.tris)
    remap = -np.ones(len(part.pos), np.int64)
    remap[used] = np.arange(len(used))
    return Part(part.name, part.mat, part.pos[used], part.nrm[used], part.uv[used], remap[part.tris])


# ----------------------------------------------------------------------------
# Frames
# ----------------------------------------------------------------------------
class AxisFrame:
    """Straight axis: origin + a*axis, with e1,e2 spanning the section plane."""

    def __init__(self, origin, axis, e1=None):
        self.o = np.asarray(origin, np.float64)
        self.t = unit(axis)
        if e1 is None:
            e1 = np.array([1.0, 0, 0]) if abs(self.t[0]) < 0.9 else np.array([0, 1.0, 0])
        e1 = np.asarray(e1, np.float64)
        e1 = unit(e1 - self.t * np.dot(e1, self.t))
        self.e1 = e1
        self.e2 = np.cross(e1, self.t)  # e1 x t  (for t=+Y,e1=+X -> e2=+Z)

    def at(self, a):
        a = np.asarray(a, np.float64)
        C = self.o[None, :] + a[:, None] * self.t[None, :]
        n = len(a)
        return C, np.tile(self.t, (n, 1)), np.tile(self.e1, (n, 1)), np.tile(self.e2, (n, 1))


class PathFrame:
    """Axis defined by a function y -> point (x,y,z) (rod blank bend).
    e1 stays +X, e2 is the 'up' vector perpendicular to the tangent."""

    def __init__(self, fn, up_hint=(0, 0, 1.0)):
        self.fn = fn
        self.up = np.asarray(up_hint, np.float64)

    def at(self, a):
        a = np.asarray(a, np.float64)
        C = np.array([self.fn(x) for x in a])
        h = 1e-4
        T = np.array([self.fn(x + h) - self.fn(x - h) for x in a])
        T = norm(T)
        e1 = np.tile(np.array([1.0, 0, 0]), (len(a), 1))
        e2 = norm(np.cross(e1, T))          # e1 x T  -> 'up' (+Z) for a rod along +Y
        return C, T, e1, e2


def circle_outline(n, theta0=0.0, ex=1.0, ey=1.0):
    th = theta0 + TAU * np.arange(n + 1) / n
    return np.stack([np.cos(th) * ex, np.sin(th) * ey], -1)


def superellipse_outline(n, a, b, p=2.0, theta0=0.0):
    th = theta0 + TAU * np.arange(n + 1) / n
    c, s = np.cos(th), np.sin(th)
    x = a * np.sign(c) * np.abs(c) ** (2.0 / p)
    y = b * np.sign(s) * np.abs(s) ** (2.0 / p)
    return np.stack([x, y], -1)


def hull_outline(c0, r0, c1, r1, n=24):
    """Convex hull of two circles (arm outline), centred on the centroid."""
    c0 = np.asarray(c0, float)
    c1 = np.asarray(c1, float)
    d = c1 - c0
    L = np.linalg.norm(d)
    ang = np.arctan2(d[1], d[0])
    k = np.arccos(np.clip((r0 - r1) / L, -1, 1))  # tangent half angle
    pts = []
    for th in np.linspace(ang + k, ang + TAU - k, n):          # around circle 0 (back side)
        pts.append(c0 + r0 * np.array([np.cos(th), np.sin(th)]))
    for th in np.linspace(ang - k, ang + k, n):                # around circle 1 (front side)
        pts.append(c1 + r1 * np.array([np.cos(th), np.sin(th)]))
    pts = np.array(pts)
    pts = np.vstack([pts, pts[:1]])
    return pts


# ----------------------------------------------------------------------------
# Profile helpers
# ----------------------------------------------------------------------------
def fillet_profile(pts, radii, n=5):
    """Round the corners of a polyline in (a,s) space.
    pts: list of (a,s); radii: per-point fillet radius (0 = keep sharp).
    Returns list of (a,s)."""
    pts = [np.asarray(p, float) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        r = radii[i]
        if r <= 0:
            out.append(p1)
            continue
        d0 = p0 - p1
        d1 = p2 - p1
        l0, l1 = np.linalg.norm(d0), np.linalg.norm(d1)
        u0, u1 = d0 / l0, d1 / l1
        cosang = np.clip(np.dot(u0, u1), -1, 1)
        ang = np.arccos(cosang)
        if ang < 1e-3 or abs(ang - np.pi) < 1e-3:
            out.append(p1)
            continue
        t = r / np.tan(ang / 2)
        t = min(t, 0.48 * l0, 0.48 * l1)
        r_eff = t * np.tan(ang / 2)
        a0 = p1 + u0 * t
        a1 = p1 + u1 * t
        bis = unit(u0 + u1)
        cen = p1 + bis * (r_eff / np.sin(ang / 2))
        v0 = a0 - cen
        v1 = a1 - cen
        th0 = np.arctan2(v0[1], v0[0])
        th1 = np.arctan2(v1[1], v1[0])
        dth = (th1 - th0 + np.pi) % TAU - np.pi
        for k in range(n + 1):
            th = th0 + dth * k / n
            out.append(cen + r_eff * np.array([np.cos(th), np.sin(th)]))
    out.append(pts[-1])
    return out


def profile_with_v(prof, v_per_m, v0=0.0):
    """Add arclength-based v coordinate. prof: list of (a,s). returns rows (a,s,v)."""
    prof = np.asarray(prof, float)
    d = np.linalg.norm(np.diff(prof, axis=0), axis=1)
    v = v0 + np.concatenate([[0], np.cumsum(d)]) * v_per_m
    return np.column_stack([prof, v])


def dedupe_corner(prof, i):
    """duplicate row i (hard edge)."""
    prof = list(prof)
    prof.insert(i, prof[i])
    return prof


# ----------------------------------------------------------------------------
# skin  (generalised lathe)
# ----------------------------------------------------------------------------
def _row_refs(rows_as, T, E1, E2, outline):
    """analytic outward reference normals for rows/cols"""
    a = rows_as[:, 0]
    s = rows_as[:, 1]
    n = len(a)
    na = np.zeros(n)
    ns = np.zeros(n)
    seg_a = np.diff(a)
    seg_s = np.diff(s)
    seg_l = np.hypot(seg_a, seg_s)
    # outward normal for travel direction (da,ds): (axial=-ds, radial=da)
    sn_ax = np.where(seg_l > 1e-12, -seg_s / np.maximum(seg_l, 1e-12), 0)
    sn_rd = np.where(seg_l > 1e-12, seg_a / np.maximum(seg_l, 1e-12), 0)
    for i in range(n):
        ax = 0.0
        rd = 0.0
        if i > 0 and seg_l[i - 1] > 1e-12:
            ax += sn_ax[i - 1]
            rd += sn_rd[i - 1]
        if i < n - 1 and seg_l[i] > 1e-12:
            ax += sn_ax[i]
            rd += sn_rd[i]
        l = np.hypot(ax, rd)
        if l < 1e-12:
            ax, rd = 0, 1
            l = 1
        na[i] = ax / l
        ns[i] = rd / l
    rad = norm(outline[:, 0:1][None] * E1[:, None, :] + outline[:, 1:2][None] * E2[:, None, :])
    ref = na[:, None, None] * T[:, None, :] + ns[:, None, None] * rad
    return ref


def skin(name, mat, frame, rows, outline, u_rep=1.0, u0=0.0, uv_fn=None,
         keep=None, closed=True, arc_u=True, v_scale=1.0, mod=None, flip=False):
    """Generalised lathe / loft.

    frame   : AxisFrame / PathFrame
    rows    : array (n,3) of (a, s, v)  a=axial coordinate, s=scale of outline, v=texture v
    outline : (m+1,2) unit outline (first==last when closed)
    mod     : optional fn(a_row, col_frac)->radial multiplier (n,m+1) for knurls etc.
    """
    rows = np.asarray(rows, np.float64)
    a = rows[:, 0]
    C, T, E1, E2 = frame.at(a)
    outline = np.asarray(outline, np.float64)
    s = rows[:, 1][:, None]
    if mod is not None:
        frac = np.cumsum(np.r_[0, np.linalg.norm(np.diff(outline, axis=0), axis=1)])
        frac = frac / frac[-1]
        mm = mod(a[:, None], frac[None, :])
        s = s * mm
    else:
        s = np.repeat(s, len(outline), axis=1)
    P = (C[:, None, :] + s[..., None] * (outline[None, :, 0:1] * E1[:, None, :]
                                         + outline[None, :, 1:2] * E2[:, None, :]))
    nv, nu = P.shape[:2]
    # uv
    if arc_u:
        seg = np.linalg.norm(np.diff(outline, axis=0), axis=1)
        fr = np.r_[0, np.cumsum(seg)]
        fr = fr / fr[-1]
    else:
        fr = np.linspace(0, 1, nu)
    U = u0 + u_rep * fr
    UV = np.empty((nv, nu, 2))
    UV[..., 0] = U[None, :]
    UV[..., 1] = rows[:, 2][:, None] * v_scale
    ref = _row_refs(rows, T, E1, E2, outline)
    if flip:
        ref = -ref
    if uv_fn is not None:
        UV = uv_fn(P)
    return grid_part(name, mat, P, UV, ref, closed_u=closed, keep=keep)


# ----------------------------------------------------------------------------
# tube sweep along a polyline
# ----------------------------------------------------------------------------
def _rmf(path):
    """rotation minimising frames (double reflection)."""
    n = len(path)
    T = np.zeros((n, 3))
    T[1:-1] = path[2:] - path[:-2]
    T[0] = path[1] - path[0]
    T[-1] = path[-1] - path[-2]
    T = norm(T)
    R = np.zeros((n, 3))
    t0 = T[0]
    ref = np.array([0, 0, 1.0]) if abs(t0[2]) < 0.9 else np.array([1.0, 0, 0])
    R[0] = unit(ref - t0 * np.dot(ref, t0))
    for i in range(n - 1):
        v1 = path[i + 1] - path[i]
        c1 = np.dot(v1, v1)
        if c1 < 1e-18:
            R[i + 1] = R[i]
            continue
        rL = R[i] - (2 / c1) * np.dot(v1, R[i]) * v1
        tL = T[i] - (2 / c1) * np.dot(v1, T[i]) * v1
        v2 = T[i + 1] - tL
        c2 = np.dot(v2, v2)
        if c2 < 1e-18:
            R[i + 1] = rL
        else:
            R[i + 1] = rL - (2 / c2) * np.dot(v2, rL) * v2
    S = np.cross(T, R)
    return T, R, S


def tube(name, mat, path, radius, nseg=12, cap0=True, cap1=True, ncap=4,
         u_rep=1.0, v_per_m=1.0, v0=0.0, elliptic=None, theta0=0.0, sections=None):
    """Sweep a (possibly elliptical) circle along `path`.
    radius   : scalar or (n,) array
    elliptic : optional (kr, ks): scale of section along R / S frame vectors
    """
    path = np.asarray(path, np.float64)
    n = len(path)
    rad = np.broadcast_to(np.asarray(radius, np.float64), (n,)).copy()
    T, R, S = _rmf(path)
    kr, ks = (1.0, 1.0) if elliptic is None else elliptic
    seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    rows_pos = []
    rows_sc = []
    rows_T = []
    rows_R = []
    rows_S = []
    rows_v = []

    def add(p, sc, i, v):
        rows_pos.append(p)
        rows_sc.append(sc)
        rows_T.append(T[i])
        rows_R.append(R[i])
        rows_S.append(S[i])
        rows_v.append(v)

    if cap0:
        r_e = rad[0]
        for k in range(ncap, -1, -1):
            ph = (np.pi / 2) * k / ncap
            add(path[0] - T[0] * r_e * np.sin(ph) * ks * 0 - T[0] * r_e * np.sin(ph), r_e * np.cos(ph), 0, v0 - r_e * np.sin(ph) * v_per_m)
    for i in range(n):
        add(path[i], rad[i], i, v0 + seglen[i] * v_per_m)
    if cap1:
        r_e = rad[-1]
        for k in range(1, ncap + 1):
            ph = (np.pi / 2) * k / ncap
            add(path[-1] + T[-1] * r_e * np.sin(ph), r_e * np.cos(ph), n - 1, v0 + seglen[-1] * v_per_m + r_e * np.sin(ph) * v_per_m)
    pos = np.array(rows_pos)
    sc = np.array(rows_sc)[:, None]
    Rr = np.array(rows_R)
    Ss = np.array(rows_S)
    Tt = np.array(rows_T)
    th = theta0 + TAU * np.arange(nseg + 1) / nseg
    cs = np.cos(th)[None, :, None]
    sn = np.sin(th)[None, :, None]
    radial = cs * Rr[:, None, :] * kr + sn * Ss[:, None, :] * ks
    P = pos[:, None, :] + sc[..., None] * radial
    nv = len(pos)
    UV = np.empty((nv, nseg + 1, 2))
    UV[..., 0] = u_rep * np.arange(nseg + 1)[None, :] / nseg
    UV[..., 1] = np.array(rows_v)[:, None]
    ref = norm(radial)
    return grid_part(name, mat, P, UV, ref, closed_u=True)


# ----------------------------------------------------------------------------
# torus (elliptic section)
# ----------------------------------------------------------------------------
def torus(name, mat, center, axis, R, r_ax, r_rad, nu=32, nv=12, u_rep=1.0, v_rep=1.0, theta0=0.0, e1=None):
    fr = AxisFrame(center, axis, e1)
    th = theta0 + TAU * np.arange(nu + 1) / nu          # around the ring
    ph = TAU * np.arange(nv + 1) / nv                   # around the tube
    ct, st = np.cos(th)[:, None], np.sin(th)[:, None]
    radial_dir = ct[..., None] * fr.e1 + st[..., None] * fr.e2      # (nu+1,1,3)
    cph, sph = np.cos(ph)[None, :], np.sin(ph)[None, :]
    P = (np.asarray(center) + (R + r_rad * cph)[..., None] * radial_dir + (r_ax * sph)[..., None] * fr.t)
    ref = norm((cph[..., None] * radial_dir + sph[..., None] * fr.t))
    UV = np.empty((nu + 1, nv + 1, 2))
    UV[..., 0] = v_rep * np.arange(nv + 1)[None, :] / nv
    UV[..., 1] = u_rep * np.arange(nu + 1)[:, None] / nu
    return grid_part(name, mat, P, UV, ref, closed_u=True, closed_v=True)


# ----------------------------------------------------------------------------
# sector solid (rotor arms etc.)
# ----------------------------------------------------------------------------
def sector_solid(name, mat, frame, a0, a1, r_in, r_out, th_c, th_hw, na=14, nt=14, uv_scale=(1.0, 1.0),
                 uv_fn=None, ncorner=3):
    """Closed solid: part of a hollow cylinder.  r_in(a), r_out(a), th_hw(a) callables.
    angle measured in the frame's (e1,e2) plane."""
    A = np.linspace(a0, a1, na)
    C, T, E1, E2 = frame.at(A)
    hw = np.array([th_hw(x) for x in A])
    ro = np.array([r_out(x) for x in A])
    ri = np.array([r_in(x) for x in A])
    f = np.linspace(-1, 1, nt)
    TH = th_c + hw[:, None] * f[None, :]
    def pts(R, TH_):
        d = np.cos(TH_)[..., None] * E1[:, None, :] + np.sin(TH_)[..., None] * E2[:, None, :]
        return C[:, None, :] + R[:, None, None] * d, d
    Po, do = pts(ro, TH)
    Pi, di = pts(ri, TH)
    parts = []
    def UVg(P, ua, ub):
        U = np.broadcast_to(np.linspace(0, 1, P.shape[1])[None, :] * uv_scale[0] + ua, P.shape[:2])
        V = np.broadcast_to(np.linspace(0, 1, P.shape[0])[:, None] * uv_scale[1] + ub, P.shape[:2])
        return np.stack([U, V], -1)
    parts.append(grid_part(name + '_o', mat, Po, UVg(Po, 0, 0), do))
    parts.append(grid_part(name + '_i', mat, Pi, UVg(Pi, 0, 0), -di))
    # end walls at a0 and a1  (rim)
    for k, sgn in ((0, -1.0), (na - 1, 1.0)):
        Pw = np.stack([Pi[k], Po[k]], 0)
        refw = np.tile(T[k] * sgn, (2, nt, 1))
        parts.append(grid_part(name + '_w%d' % k, mat, Pw, UVg(Pw, 0, 0), refw))
    # side walls
    for j, sgn in ((0, -1.0), (nt - 1, 1.0)):
        Ps = np.stack([Pi[:, j], Po[:, j]], 1)
        tang = np.zeros_like(Ps)
        dth = np.stack([-np.sin(TH[:, j])[:, None] * E1 + np.cos(TH[:, j])[:, None] * E2] * 2, 1)
        parts.append(grid_part(name + '_s%d' % j, mat, Ps, UVg(Ps, 0, 0), dth * sgn))
    return parts


# ----------------------------------------------------------------------------
# misc helpers
# ----------------------------------------------------------------------------
def rbox(name, mat, center, size, axes=None, bevel=0.0006, p=6.0, n=24):
    """rounded box: superellipse loft with filleted end caps (smooth normals, soft corners).
    axes: 3x3 matrix whose columns are the local x,y,z directions in world space."""
    sx, sy, sz = size
    ax = np.eye(3) if axes is None else np.asarray(axes, float)
    fr = AxisFrame(center, ax[:, 2], ax[:, 0])
    out = superellipse_outline(n, sx / 2, sy / 2, p)
    h = sz / 2
    b = min(bevel, h * 0.9, min(sx, sy) * 0.45)
    k = 4
    top = []
    for i in range(k + 1):
        ph = (np.pi / 2) * i / k
        top.append((h - b + b * np.sin(ph), 1.0 - (b / (min(sx, sy) / 2)) * (1 - np.cos(ph))))
    bot = [(-a, s) for a, s in top[::-1]]
    prof = [(-h, 0.0)] + bot + top + [(h, 0.0)]
    rows = np.array([(a, s, 0.0) for a, s in prof])
    return skin(name, mat, fr, rows, out, u_rep=1.0)


def merge_parts(parts):
    """merge parts of the same material"""
    by = {}
    for p in parts:
        by.setdefault(p.mat, []).append(p)
    out = []
    for m, ps in sorted(by.items()):
        pos = np.concatenate([p.pos for p in ps])
        nrm = np.concatenate([p.nrm for p in ps])
        uv = np.concatenate([p.uv for p in ps])
        off = 0
        tr = []
        for p in ps:
            tr.append(p.tris + off)
            off += len(p.pos)
        out.append(Part('mat%d' % m, m, pos, nrm, uv, np.concatenate(tr)))
    return out


# ----------------------------------------------------------------------------
# profile builders
# ----------------------------------------------------------------------------
def groove_profile(base_fn, a0, a1, n=12, grooves=(), extra=()):
    """Sample r(a)=base_fn(a) minus smooth grooves [(centre, half_width, depth)].
    Dense samples inside the grooves, coarse elsewhere. Returns list of (a, s)."""
    a = list(np.linspace(a0, a1, n))
    for ac, w, d in grooves:
        a += list(np.linspace(ac - w, ac + w, 5))
    a += list(extra)
    a = np.unique(np.round(np.clip(a, a0, a1), 7))
    out = []
    for x in a:
        r = base_fn(x)
        for ac, w, d in grooves:
            if abs(x - ac) < w:
                r -= d * 0.5 * (1 + np.cos(np.pi * (x - ac) / w))
        out.append((x, r))
    return out


def slab_rows(half, bevel_s, bevel_a, k=3):
    """Rows for a plate of thickness 2*half centred on a=0 with rounded rim.
    s runs 0..1 (outline scale); returns (a, s, 0) rows (outer surface travels a-,rim,a+)."""
    bevel_a = min(bevel_a, half * 0.95)
    rows = [(-half, 0.0), (-half, 0.5 * (1 - bevel_s)), (-half, 1 - bevel_s)]
    for i in range(1, k + 1):
        ph = (np.pi / 2) * i / k
        rows.append((-half + bevel_a * (1 - np.cos(ph)), 1 - bevel_s + bevel_s * np.sin(ph)))
    for i in range(k - 1, -1, -1):
        ph = (np.pi / 2) * i / k
        rows.append((half - bevel_a * (1 - np.cos(ph)), 1 - bevel_s + bevel_s * np.sin(ph)))
    rows += [(half, 1 - bevel_s), (half, 0.5 * (1 - bevel_s)), (half, 0.0)]
    # drop the duplicated rim point
    out = [rows[0]]
    for r in rows[1:]:
        if abs(r[0] - out[-1][0]) > 1e-12 or abs(r[1] - out[-1][1]) > 1e-12:
            out.append(r)
    return np.array([(a, s, 0.0) for a, s in out])
