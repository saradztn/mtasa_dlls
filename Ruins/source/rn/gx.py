# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# gx.py - extra geometry primitives for the park: lathe (revolved profiles), tapered cylinders along any axis,
#         bent branches/trunks, leaf cards, crowns of cards, displaced rocks, ribbons along a polyline.
#         All primitives write into a mb.Mesh (flat or smooth normals are explicit).
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, unit, TAU


def _orient(P, T, N):
    """flip triangle winding where the geometric normal disagrees with the vertex normal"""
    P = np.asarray(P)
    N = np.asarray(N)
    out = []
    for t in T:
        nf = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
        s = N[t[0]] + N[t[1]] + N[t[2]]
        out.append(t if np.dot(nf, s) >= 0 else t[::-1])
    return out


def lathe(M, c, prof, n, mat, tile=1.0, emis=0.0, sharp=50.0, theta0=0.0, ex=1.0, ey=1.0, vscale=1.0):
    """surface of revolution around the vertical axis through c. prof = [(r, z), ...] ordered bottom -> top along the
    outside surface (the outward normal is the profile tangent rotated by -90 deg).  Corners sharper than `sharp`
    degrees get hard edges."""
    prof = [tuple(p) for p in prof]
    segs = []
    for i in range(len(prof) - 1):
        (r0, z0), (r1, z1) = prof[i], prof[i + 1]
        dr, dz = r1 - r0, z1 - z0
        L = np.hypot(dr, dz)
        if L < 1e-9:
            continue
        segs.append(((r0, z0), (r1, z1), np.array([dz / L, -dr / L])))      # (nr, nz)
    th = theta0 + np.arange(n + 1) * TAU / n
    cx, cy = c
    cs, sn = np.cos(th), np.sin(th)
    vacc = 0.0
    for i, (a, b, nn) in enumerate(segs):
        def vnorm(j, other):
            if other is None:
                return nn
            ang = np.degrees(np.arccos(np.clip(np.dot(nn, other), -1, 1)))
            if ang > sharp:
                return nn
            v = nn + other
            return v / max(np.linalg.norm(v), 1e-9)
        n0 = vnorm(i, segs[i - 1][2] if i > 0 else None)
        n1 = vnorm(i, segs[i + 1][2] if i + 1 < len(segs) else None)
        L = np.hypot(b[0] - a[0], b[1] - a[1])
        P, N, UV, T = [], [], [], []
        for k in range(n + 1):
            for (r, z), nv, vv in ((a, n0, vacc), (b, n1, vacc + L)):
                P.append([cx + r * ex * cs[k], cy + r * ey * sn[k], z])
                N.append(unit([nv[0] * cs[k] / ex, nv[0] * sn[k] / ey, nv[1]]))
                UV.append([k / n * TAU * max(a[0], b[0], 0.05) / tile, -(vv) * vscale / tile])
        for k in range(n):
            i0 = 2 * k
            T += [[i0, i0 + 1, i0 + 3], [i0, i0 + 3, i0 + 2]]
        M.add(P, N, UV, _orient(P, T, N), mat, emis)
        vacc += L


def frame(d):
    d = unit(d)
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.97 else np.array([1.0, 0, 0])
    r = unit(np.cross(d, up))
    u = np.cross(r, d)
    return r, u, d


def tube(M, pts, radii, n, mat, tile=1.0, cap_end=True, cap_start=False, emis=0.0, uv_scale=1.0):
    """smooth tapered tube along a polyline"""
    pts = [np.asarray(p, float) for p in pts]
    rings, nrm, v = [], [], [0.0]
    for i in range(1, len(pts)):
        v.append(v[-1] + np.linalg.norm(pts[i] - pts[i - 1]))
    prev_u = None
    for i, p in enumerate(pts):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = unit(pts[i + 1] - p) + unit(p - pts[i - 1])
        r_, u_, d_ = frame(d)
        if prev_u is not None:                     # parallel transport to avoid twisting
            u_ = unit(prev_u - d_ * np.dot(prev_u, d_))
            r_ = np.cross(d_, u_)
            r_ = unit(r_)
        prev_u = u_
        ring, nn = [], []
        for k in range(n):
            a = TAU * k / n
            dirv = r_ * np.cos(a) + u_ * np.sin(a)
            ring.append(p + dirv * radii[i])
            nn.append(dirv)
        rings.append(ring)
        nrm.append(nn)
    P, N, UV, T = [], [], [], []
    for i, (ring, nn) in enumerate(zip(rings, nrm)):
        for k in range(n + 1):
            kk = k % n
            P.append(ring[kk])
            N.append(nn[kk])
            UV.append([k / n * TAU * radii[i] * uv_scale / tile * 1.0, v[i] / tile])
    for i in range(len(pts) - 1):
        for k in range(n):
            a = i * (n + 1) + k
            b = a + n + 1
            T += [[a, a + 1, b + 1], [a, b + 1, b]]
    M.add(P, N, UV, _orient(P, T, N), mat, emis)
    if cap_end:
        d = unit(pts[-1] - pts[-2])
        ring = rings[-1]
        M.poly(ring, mat, hint=d, tile=tile)
    if cap_start:
        d = unit(pts[0] - pts[1])
        M.poly(rings[0], mat, hint=d, tile=tile)


def cyl(M, p0, p1, r0, r1, n, mat, tile=1.0, caps=True, emis=0.0):
    tube(M, [p0, p1], [r0, r1], n, mat, tile=tile, cap_end=caps, cap_start=caps, emis=emis)


def card(M, c, a, b, mat, nrm, uvr=(0, 0, 1, 1), emis=0.0, double=True):
    """quad centred at c spanned by half-vectors a (u direction) and b (v direction, 'up' of the texture).
    nrm: the shading normal used on both faces (foliage lighting)."""
    c, a, b = np.asarray(c, float), np.asarray(a, float), np.asarray(b, float)
    P = [c - a - b, c + a - b, c + a + b, c - a + b]
    u0, v0, u1, v1 = uvr
    UV = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
    n = unit(nrm)
    geo = np.cross(P[1] - P[0], P[2] - P[0])
    T = [[0, 1, 2], [0, 2, 3]]
    if np.dot(geo, n) < 0:
        T = [t[::-1] for t in T]
    M.add(P, [n] * 4, UV, T, mat, emis)
    if double:
        M.add(P, [n] * 4, UV, [t[::-1] for t in T], mat, emis)


def rock(M, c, size, mat, seed, n=14, flat=0.62, tile=1.2):
    """displaced ellipsoid with smooth normals computed from the displaced surface"""
    r = np.random.default_rng(seed)
    nu, nv = n, n // 2 + 1
    ph = np.linspace(-np.pi / 2 * 0.92, np.pi / 2, nv)
    th = np.arange(nu) * TAU / nu
    # low-frequency displacement from random harmonics
    harm = [(r.integers(1, 4), r.integers(1, 4), r.uniform(0, TAU), r.uniform(0.05, 0.18)) for _ in range(5)]
    G = np.zeros((nv, nu, 3))
    for j, p in enumerate(ph):
        for i, t in enumerate(th):
            d = np.array([np.cos(p) * np.cos(t), np.cos(p) * np.sin(t), np.sin(p) * flat])
            k = 1.0 + sum(a * np.sin(f1 * t + f2 * p * 2 + ph0) for f1, f2, ph0, a in harm) + r.normal(0, 0.018)
            G[j, i] = d * k * np.array(size)
    Pn = G + np.asarray(c, float)
    P, UV, T = [], [], []
    for j in range(nv):
        for i in range(nu + 1):
            P.append(Pn[j, i % nu])
            UV.append([P[-1][0] / tile, P[-1][1] / tile + P[-1][2] / tile * 0.5])
    for j in range(nv - 1):
        for i in range(nu):
            a = j * (nu + 1) + i
            b = a + nu + 1
            T += [[a, a + 1, b + 1], [a, b + 1, b]]
    P = np.array(P)
    nrm = np.zeros_like(P)
    for t in T:
        fn = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
        for q in t:
            nrm[q] += fn
    nrm = unit(nrm)
    # seam: average normals of duplicated column
    for j in range(nv):
        a, b = j * (nu + 1), j * (nu + 1) + nu
        s = unit(nrm[a] + nrm[b])
        nrm[a] = nrm[b] = s
    out = np.asarray(P) - np.asarray(c, float)
    T = _orient(P, T, np.where((out * nrm).sum(1, keepdims=True) >= 0, nrm, -nrm))
    M.add(P, nrm, UV, T, mat)
    # bottom cap
    ring = [Pn[0, i] for i in range(nu)]
    M.poly(ring[::-1], mat, hint=(0, 0, -1), tile=tile)


def ribbon(M, pts, width, zfn, mat, tile=2.0, zoff=0.04, step=1.5, edge_mat=None, edge_w=0.0, edge_h=0.06, closed=False):
    """flat strip along a 2D polyline following zfn(x, y) (+zoff); an optional raised curb strip on both sides.
    Returns the sampled centre line."""
    pts = [np.asarray(p, float) for p in pts]
    S = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.linalg.norm(b - a)
        k = max(1, int(np.ceil(L / step)))
        for i in range(1, k + 1):
            S.append(a + (b - a) * i / k)
    S = np.array(S)
    d = np.gradient(S, axis=0)
    d = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    nl = np.stack([-d[:, 1], d[:, 0]], 1)
    acc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(S, axis=0), axis=1))])
    hw = width / 2.0
    wfn = width if callable(width) else None
    P, N, UV, T = [], [], [], []
    for i, (s, n_) in enumerate(zip(S, nl)):
        for side in (-1, 1):
            q = s + n_ * hw * side
            P.append([q[0], q[1], zfn(q[0], q[1]) + zoff])
            N.append([0, 0, 1])
            UV.append([acc[i] / tile, (side * hw + hw) / tile])
    for i in range(len(S) - 1):
        a = 2 * i
        T += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
    M.add(P, N, UV, _orient(P, T, N), mat)
    if edge_mat is not None and edge_w > 0:
        for side in (-1, 1):
            P, N, UV, T = [], [], [], []
            for i, (s, n_) in enumerate(zip(S, nl)):
                q0 = s + n_ * (hw - (edge_w if side < 0 else 0)) * 1.0 * 1.0
                # inner / outer edge of the curb strip
                qi = s + n_ * side * (hw - edge_w)
                qo = s + n_ * side * hw
                zi, zo = zfn(qi[0], qi[1]) + zoff, zfn(qo[0], qo[1]) + zoff
                P += [[qi[0], qi[1], zi + edge_h], [qo[0], qo[1], zo + edge_h], [qo[0], qo[1], zo - 0.02], [qi[0], qi[1], zi]]
                N += [[0, 0, 1], [0, 0, 1], [side * n_[0], side * n_[1], 0.0], [-side * n_[0], -side * n_[1], 0.0]]
                UV += [[acc[i] / tile, 0], [acc[i] / tile, edge_w / tile], [acc[i] / tile, edge_w / tile + 0.1], [acc[i] / tile, 0]]
            for i in range(len(S) - 1):
                a = 4 * i
                b = a + 4
                T += [[a, b, b + 1], [a, b + 1, a + 1]]           # top
                T += [[a + 1, b + 1, b + 2], [a + 1, b + 2, a + 2]]   # outer wall
            Nn = np.array(N)
            M.add(P, N, UV, _orient(P, T, N), edge_mat)
    return S


def disc(M, c, r, z, mat, n=48, tile=2.0, nz=1.0, zfn=None, ring_r0=0.0, uvoff=(0.0, 0.0)):
    """horizontal disc / annulus (flat) at height z"""
    cx, cy = c
    th = np.arange(n + 1) * TAU / n
    P, N, UV, T = [], [], [], []
    for k in range(n + 1):
        for rr in (ring_r0, r):
            x, y = cx + rr * np.cos(th[k]), cy + rr * np.sin(th[k])
            P.append([x, y, z if zfn is None else zfn(x, y) + z])
            N.append([0, 0, nz])
            UV.append([(x - cx) / tile + uvoff[0], (y - cy) / tile + uvoff[1]])
    for k in range(n):
        a = 2 * k
        T += [[a, a + 2, a + 3], [a, a + 3, a + 1]] if nz > 0 else [[a, a + 3, a + 2], [a, a + 1, a + 3]]
    M.add(P, N, UV, _orient(P, T, N), mat)


# ---- copied from the castle pipeline (bar / sphere primitives)
def bar(M, p0, p1, w, mat, h=None, tile=1.0, caps=True, emis=0.0):
    """rectangular bar between two points (w wide, h tall; default square)"""
    h = w if h is None else h
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = unit(p1 - p0)
    up = np.array([0, 0, 1.0])
    if abs(d[2]) > 0.98:
        up = np.array([1.0, 0, 0])
    right = unit(np.cross(d, up))
    upv = np.cross(right, d)
    c = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ring0 = [p0 + right * a * w / 2 + upv * b * h / 2 for a, b in c]
    ring1 = [p1 + right * a * w / 2 + upv * b * h / 2 for a, b in c]
    L = np.linalg.norm(p1 - p0)
    mid = (p0 + p1) / 2
    for i in range(4):
        j = (i + 1) % 4
        pts = [ring0[i], ring0[j], ring1[j], ring1[i]]
        cen = (ring0[i] + ring0[j]) / 2 - p0
        M.poly(pts, mat, hint=cen - d * np.dot(cen, d), uv=[(0, 0), (w / tile, 0), (w / tile, L / tile), (0, L / tile)], emis=emis)
    if caps:
        M.poly(ring0[::-1], mat, hint=-d, tile=tile, emis=emis)
        M.poly(ring1, mat, hint=d, tile=tile, emis=emis)




def sphere(M, c, r, mat, nu=10, nv=6, emis=0.0, sq=(1, 1, 1)):
    P, N, UV, T = [], [], [], []
    for j in range(nv + 1):
        ph = np.pi * j / nv - np.pi / 2
        for i in range(nu + 1):
            th = TAU * i / nu
            n = np.array([np.cos(ph) * np.cos(th), np.cos(ph) * np.sin(th), np.sin(ph)])
            P.append(np.array(c) + n * r * np.array(sq))
            N.append(unit(n / np.array(sq)))
            UV.append([i / nu, j / nv])
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            b = a + nu + 1
            for tri in ([a, a + 1, b + 1], [a, b + 1, b]):
                nf = np.cross(np.array(P[tri[1]]) - np.array(P[tri[0]]), np.array(P[tri[2]]) - np.array(P[tri[0]]))
                T.append(tri if np.dot(nf, N[tri[0]]) >= 0 else tri[::-1])
    M.add(P, N, UV, T, mat, emis)


# --------------------------------------------------------------------------------------------
# light and fire
# --------------------------------------------------------------------------------------------
