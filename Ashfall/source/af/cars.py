# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# cars.py - lofted abandoned vehicles.  A car body is a closed ring cross-section swept along its length (front = +y,
#   origin = middle of the wheelbase on the ground).  Ring segments carry the material (paint / glass / pillars), wheels
#   are lathed tyres with rim discs, details (bumpers, lights, mirrors, door seams, plates) are small boxes.
#   Damage: flat tyres (body sags), broken glass, rust is part of the paint textures.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit
from .tex import IDX
from .kit import asset, rotz, place_col
from . import gx

TAU = 2 * np.pi


def MT(n):
    return IDX['af_' + n]


def revolve(M, c, axis, prof, n, mat, tile=1.0, flip=False):
    """revolve profile [(r, t)...] (t along axis) around the line through c with direction axis"""
    ax = unit(np.asarray(axis, float))
    ref = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
    e1 = unit(np.cross(ax, ref))
    e2 = np.cross(ax, e1)
    c = np.asarray(c, float)
    prof = np.asarray(prof, float)
    nv = len(prof)
    P, N, UV, T = [], [], [], []
    for j, (r, t) in enumerate(prof):
        for i in range(n + 1):
            a = TAU * i / n
            d = np.cos(a) * e1 + np.sin(a) * e2
            P.append(c + ax * t + d * r)
            UV.append((i / n * TAU * max(r, 0.05) / tile, t / tile))
    # normals from the grid
    P = np.array(P).reshape(nv, n + 1, 3)
    Nn = np.zeros_like(P)
    for j in range(nv):
        for i in range(n + 1):
            du = P[j, (i + 1) % n] - P[j, (i - 1) % n]
            dv = P[min(j + 1, nv - 1), i] - P[max(j - 1, 0), i]
            Nn[j, i] = np.cross(du, dv)
    L = np.linalg.norm(Nn, axis=-1, keepdims=True)
    Nn = np.where(L > 1e-12, Nn / np.maximum(L, 1e-12), ax)
    # outward = away from the axis
    for j in range(nv):
        for i in range(n + 1):
            rad = P[j, i] - c - ax * np.dot(P[j, i] - c, ax)
            if np.dot(Nn[j, i], rad) < 0 and np.linalg.norm(rad) > 1e-6:
                Nn[j, i] = -Nn[j, i]
    for j in range(nv - 1):
        for i in range(n):
            a = j * (n + 1) + i
            b = a + n + 1
            T += [[a, b, a + 1], [a + 1, b, b + 1]]
    flat = P.reshape(-1, 3)
    nrm = Nn.reshape(-1, 3)
    uv = np.array(UV)
    # make winding agree with the normals
    T = np.array(T)
    for k, t in enumerate(T):
        g = np.cross(flat[t[1]] - flat[t[0]], flat[t[2]] - flat[t[0]])
        if np.dot(g, nrm[t].sum(0)) < 0:
            T[k] = t[::-1]
    M.add(flat, nrm, uv, T, mat)


def wheel(M, c, r, width, side, flat=False, rim_mat=None, rust=False):
    c = np.asarray(c, float)
    rr = r * (0.80 if flat else 1.0)
    cz = c.copy()
    if flat:
        cz[2] = rr
    w = width * (1.12 if flat else 1.0)
    prof = [(r * 0.58, -w / 2), (rr * 0.78, -w / 2), (rr * 0.97, -w * 0.43), (rr, -w * 0.22), (rr, w * 0.22), (rr * 0.97, w * 0.43), (rr * 0.78, w / 2), (r * 0.58, w / 2)]
    revolve(M, cz, (1, 0, 0), prof, 18, MT('tire'), tile=0.8)
    # rim disc facing outwards + hub
    x = side * (w / 2 - 0.02)
    rm = MT('rust') if rust else MT('steel')
    pts = [(x, cz[1] + np.cos(a) * r * 0.60, cz[2] + np.sin(a) * r * 0.60) for a in np.linspace(0, TAU, 16, endpoint=False)]
    # u,v of the rim texture: radial planar
    uvs = [((p[1] - cz[1]) / (r * 1.2) + 0.5, (p[2] - cz[2]) / (r * 1.2) + 0.5) for p in pts]
    M.poly(pts, rm, hint=(side, 0, 0), uv=uvs)
    hub = [(x + side * 0.01, cz[1] + np.cos(a) * r * 0.2, cz[2] + np.sin(a) * r * 0.2) for a in np.linspace(0, TAU, 8, endpoint=False)]
    M.poly(hub, MT('tire'), hint=(side, 0, 0), tile=0.5)


class CarSpec:
    def __init__(self, **k):
        self.__dict__.update(k)


SPECS = {
    # belt / top: lists of (s fraction of L from rear, z) ; w = body width ; zb = ground clearance
    'sedan': CarSpec(L=4.65, W=1.82, wb=2.7, track=1.55, tr=0.33, zb=0.22, wf=0.95,
                     belt=[(0, 0.80), (0.12, 0.92), (0.30, 0.94), (0.55, 0.92), (0.72, 0.95), (0.90, 0.80), (1.0, 0.58)],
                     top=[(0, 0.80), (0.14, 0.94), (0.28, 1.34), (0.38, 1.44), (0.60, 1.44), (0.70, 1.20), (0.74, 0.95), (1.0, 0.58)]),
    'hatch': CarSpec(L=3.95, W=1.74, wb=2.5, track=1.5, tr=0.31, zb=0.2, wf=0.95,
                     belt=[(0, 0.95), (0.15, 0.96), (0.55, 0.92), (0.72, 0.93), (0.90, 0.80), (1.0, 0.58)],
                     top=[(0, 1.00), (0.06, 1.20), (0.16, 1.44), (0.55, 1.46), (0.72, 1.22), (0.78, 0.93), (1.0, 0.58)]),
    'suv': CarSpec(L=4.75, W=1.92, wb=2.8, track=1.62, tr=0.38, zb=0.30, wf=0.97,
                   belt=[(0, 1.08), (0.15, 1.12), (0.60, 1.10), (0.76, 1.12), (0.92, 1.00), (1.0, 0.76)],
                   top=[(0, 1.78), (0.06, 1.84), (0.55, 1.86), (0.66, 1.80), (0.72, 1.12), (1.0, 0.76)]),
    'van': CarSpec(L=5.05, W=1.95, wb=3.1, track=1.65, tr=0.35, zb=0.28, wf=0.98,
                   belt=[(0, 1.00), (0.2, 1.02), (0.76, 1.05), (0.90, 1.0), (1.0, 0.70)],
                   top=[(0, 2.26), (0.04, 2.30), (0.70, 2.30), (0.78, 2.20), (0.86, 1.28), (1.0, 0.70)]),
    'pickup': CarSpec(L=5.3, W=1.92, wb=3.2, track=1.62, tr=0.38, zb=0.30, wf=0.97,
                      belt=[(0, 1.02), (0.45, 1.02), (0.48, 1.12), (0.64, 1.14), (0.74, 1.12), (0.88, 1.04), (1.0, 0.78)],
                      top=[(0, 1.02), (0.45, 1.02), (0.50, 1.40), (0.54, 1.82), (0.64, 1.86), (0.70, 1.50), (0.74, 1.12), (1.0, 0.78)]),
    'bus': CarSpec(L=11.2, W=2.55, wb=5.6, track=2.1, tr=0.5, zb=0.32, wf=1.0,
                   belt=[(0, 1.00), (0.5, 1.02), (0.98, 0.98), (1.0, 0.8)],
                   top=[(0, 3.15), (0.03, 3.28), (0.96, 3.28), (0.99, 3.0), (1.0, 2.0)]),
    'lorry': CarSpec(L=7.4, W=2.45, wb=4.2, track=2.0, tr=0.5, zb=0.45, wf=1.0,
                     belt=[(0, 1.2), (0.62, 1.2), (0.66, 1.38), (0.88, 1.42), (1.0, 0.95)],
                     top=[(0, 3.1), (0.62, 3.1), (0.66, 2.4), (0.72, 2.9), (0.86, 2.9), (0.92, 1.42), (1.0, 0.95)]),
}


def _interp(pts, s):
    xs = np.array([p[0] for p in pts])
    zs = np.array([p[1] for p in pts])
    return float(np.interp(s, xs, zs))


def build_car(kind, paint, seed=1, flat=(0, 0, 0, 0), glass_dmg=0.5, rust=False, extra=None):
    sp = SPECS[kind]
    r = np.random.default_rng(seed)
    M = Mesh()
    body = Mesh()
    L, W = sp.L, sp.W
    ns = max(26, int(L * 7))
    ss = np.linspace(0, 1, ns) ** 1.0
    # more stations near the ends
    ss = 0.5 - 0.5 * np.cos(ss * np.pi)
    ss = 0.5 * ss + 0.5 * np.linspace(0, 1, ns)
    paint_m, glass_m, glassb_m = MT(paint), MT('glass'), MT('glass_broken')
    black, steel = MT('tire'), MT('steel')
    # per-station ring
    rings, zones = [], []
    for s in ss:
        zb = sp.zb + (0.06 if s < 0.04 or s > 0.96 else 0.0)
        belt = _interp(sp.belt, s)
        top = _interp(sp.top, s)
        # body width tapers at the ends
        w = W * (1.0 - 0.18 * (1 - min(s / 0.08, 1)) ** 2 - 0.30 * (1 - min((1 - s) / 0.10, 1)) ** 2) * (sp.wf if sp.wf < 1 else 1)
        cab = top - belt
        wc = w * 0.46 * (0.96 if cab > 0.25 else 1.0)
        wr = w * (0.40 if kind in ('sedan', 'hatch') else 0.45) if cab > 0.25 else w * 0.38
        hh = max(cab, 0.03)
        # half profile (y, z)
        half = [(0.0, zb), (w * 0.44, zb), (w * 0.5, zb + 0.12), (w * 0.5, belt - 0.06), (w * 0.49, belt),
                (wc, belt + 0.02), (wc * 0.90, belt + hh * 0.85) if cab > 0.25 else (wc * 0.9, belt + 0.03),
                (wr, top), (0.0, top + (0.03 if cab <= 0.25 else 0.0))]
        pts = half + [(-y, z) for y, z in half[-2:0:-1]]
        rings.append(np.array(pts))
        zones.append(cab > 0.25)
    nr = len(rings[0])
    # world positions: x = ring y, y = s*L - L/2 ... place wheelbase centre at origin: rear axle at y=-wb/2
    ycenter = L * 0.5 - (L - sp.wb) / 2 * 0 - 0
    ofs = -L * 0.5 + (L - sp.wb) / 2 - (L - sp.wb) / 2     # = -L/2 ; recentre on wheelbase below
    sh = -(L - sp.wb) / 2 - sp.wb / 2 + (L - sp.wb) / 2 * 0
    shift = -((L - sp.wb) / 2 + sp.wb / 2)
    G = np.zeros((ns, nr, 3))
    for i, s in enumerate(ss):
        G[i, :, 0] = rings[i][:, 0]
        G[i, :, 1] = s * L + shift
        G[i, :, 2] = rings[i][:, 1]
    # smooth normals on the grid
    Nn = np.zeros_like(G)
    for i in range(ns):
        for j in range(nr):
            du = G[i, (j + 1) % nr] - G[i, (j - 1) % nr]
            dv = G[min(i + 1, ns - 1), j] - G[max(i - 1, 0), j]
            n = np.cross(dv, du)
            ln = np.linalg.norm(n)
            Nn[i, j] = n / ln if ln > 1e-12 else (0, 0, 1)
    # make sure normals point outwards
    for i in range(ns):
        cen = G[i].mean(0)
        for j in range(nr):
            if np.dot(Nn[i, j], G[i, j] - cen) < 0:
                Nn[i, j] = -Nn[i, j]
    # materials per cell: segments (ring edges) index j -> j+1.  edges: 0 bottom, 1 rocker, 2 lower side, 3 belt, 4 base glass lower,
    #  5 glass upper, 6 roof edge, 7 roof ... mirrored
    glass_state = {}
    for i in range(ns - 1):
        s = (ss[i] + ss[i + 1]) / 2
        for j in range(nr):
            glass = zones[i] and zones[i + 1] and (j in (5, 6, nr - 5 + 0, nr - 6 + 0) or j in (4, nr - 4))
            # side glass has pillars: B pillar etc. along s
            side = j in (4, 5, 6, nr - 4, nr - 5, nr - 6) if False else False
            mat = paint_m
            if zones[i] and zones[i + 1] and j in (5, 6, nr - 6 + 0, nr - 7 + 0):
                # side window: pillars at fixed fractions
                cabs = [k for k, z in enumerate(zones) if z]
                s0, s1 = ss[cabs[0]], ss[cabs[-1]]
                u = (s - s0) / max(s1 - s0, 1e-6)
                pill = any(abs(u - p) < 0.035 for p in ((0.0, 0.5, 1.0) if kind not in ('van', 'bus', 'lorry') else (0.0, 1.0)))
                if kind in ('sedan', 'hatch', 'suv', 'pickup') and (u < 0.05 or u > 0.95):
                    pill = True
                mat = paint_m if pill else glass_m
            elif zones[i] != zones[i + 1] or (not zones[i] and (j in (5, 6) and False)):
                mat = glass_m if (j in (5, 6, nr - 6, nr - 7)) else paint_m
            # windshield / rear window: sloped cabin transition cells (zones differ across the edge) -> glass on the upper segments
            if zones[i] != zones[i + 1] and j in (5, 6, 7, nr - 6, nr - 7, nr - 8, 7):
                mat = glass_m
            if mat == glass_m:
                key = (i // 2, j // 2)
                if key not in glass_state:
                    glass_state[key] = glassb_m if r.random() < glass_dmg else glass_m
                mat = glass_state[key]
            # underside
            if j in (0, nr - 1):
                mat = black
            self_uv = []
            q = [G[i, j], G[i, (j + 1) % nr], G[i + 1, (j + 1) % nr], G[i + 1, j]]
            qn = [Nn[i, j], Nn[i, (j + 1) % nr], Nn[i + 1, (j + 1) % nr], Nn[i + 1, j]]
            if mat in (glass_m, glassb_m):
                uv = [(0, 0), (0.3, 0), (0.3, 0.3), (0, 0.3)] if False else [(j * 0.25, i * 0.25), ((j + 1) * 0.25, i * 0.25), ((j + 1) * 0.25, (i + 1) * 0.25), (j * 0.25, (i + 1) * 0.25)]
            else:
                uv = [(G[i, j][0] / 2.5 + G[i, j][2] / 2.5, G[i, j][1] / 2.5), (G[i, (j + 1) % nr][0] / 2.5 + G[i, (j + 1) % nr][2] / 2.5, G[i, (j + 1) % nr][1] / 2.5),
                      (G[i + 1, (j + 1) % nr][0] / 2.5 + G[i + 1, (j + 1) % nr][2] / 2.5, G[i + 1, (j + 1) % nr][1] / 2.5), (G[i + 1, j][0] / 2.5 + G[i + 1, j][2] / 2.5, G[i + 1, j][1] / 2.5)]
            geo = np.cross(q[1] - q[0], q[2] - q[0])
            T = [[0, 1, 2], [0, 2, 3]]
            if np.dot(geo, sum(qn)) < 0:
                T = [t[::-1] for t in T]
            if np.linalg.norm(geo) < 1e-10:
                T = [[0, 1, 2], [0, 2, 3]] if np.dot(np.cross(q[2] - q[0], q[3] - q[0]), sum(qn)) >= 0 else [[2, 1, 0], [3, 2, 0]]
            body.add(q, qn, uv, T, mat)
    # end caps
    for end, nd in ((0, (0, -1, 0)), (ns - 1, (0, 1, 0))):
        pts = [G[end, j] for j in range(nr)]
        body.poly(pts, paint_m, hint=nd, tile=2.5)
    # ---------- details
    yb, yf = G[0, 0, 1], G[-1, 0, 1]
    # bumpers
    for (yy, d) in ((yb, -1), (yf, 1)):
        zb0 = sp.zb - 0.02
        body.box((-W * 0.46, yy - (0.02 if d < 0 else 0.0) - (0.0 if d > 0 else 0.0) + (0.0 if d > 0 else -0.16), zb0 + 0.02), (W * 0.46, yy + (0.16 if d > 0 else 0.02), zb0 + 0.30), steel, tile=1.0) if False else None
        y0, y1 = (yy - 0.18, yy + 0.03) if d < 0 else (yy - 0.03, yy + 0.18)
        body.box((-W * 0.45, y0 * 0.0 + (yy - 0.10 if d < 0 else yy - 0.02), sp.zb + 0.06), (W * 0.45, (yy + 0.02 if d < 0 else yy + 0.10), sp.zb + 0.26), steel, tile=1.0)
    # headlights / tail lights (dim, broken)
    zl = _interp(sp.belt, 1.0) + 0.2 if kind not in ('bus',) else 0.9
    for sx in (-1, 1):
        body.box((sx * W * 0.30 - 0.14, yf - 0.03, sp.zb + 0.38), (sx * W * 0.30 + 0.14, yf + 0.04, sp.zb + 0.55), glassb_m, tile=0.4)
        body.box((sx * W * 0.34 - 0.12, yb - 0.04, sp.zb + 0.50), (sx * W * 0.34 + 0.12, yb + 0.03, sp.zb + 0.68), MT('rust'), tile=0.4)
    # grille
    body.box((-W * 0.18, yf - 0.02, sp.zb + 0.34), (W * 0.18, yf + 0.04, sp.zb + 0.5), black, tile=0.4)
    # door seams (black thin quads on both sides) + handles
    s0 = shift + L * 0.30
    for sx in (-1, 1):
        for yy in (shift + L * (0.34 if kind != 'bus' else 0.3), shift + L * (0.52 if kind != 'bus' else 0.66)):
            x = sx * (W * 0.5 + 0.003)
            body.box((x - 0.002, yy, sp.zb + 0.2), (x + 0.002, yy + 0.014, _interp(sp.belt, 0.5) - 0.02), black, tile=0.5)
        yh = shift + L * 0.37
        body.box((sx * (W * 0.5) , yh, _interp(sp.belt, 0.5) - 0.08), (sx * (W * 0.5 + 0.04), yh + 0.14, _interp(sp.belt, 0.5) - 0.05), steel, tile=0.3)
        # mirrors
        zm = _interp(sp.belt, 0.58) + 0.12
        body.box((sx * W * 0.5, shift + L * 0.60, zm), (sx * (W * 0.5 + 0.17), shift + L * 0.60 + 0.12, zm + 0.12), paint_m, tile=0.5)
    # plates
    body.box((-0.26, yb - 0.045, sp.zb + 0.35), (0.26, yb + 0.0, sp.zb + 0.46), MT('steel'), tile=0.5)
    body.box((-0.26, yf, sp.zb + 0.12), (0.26, yf + 0.04, sp.zb + 0.23), MT('steel'), tile=0.5)
    # bed (pickup), roof sign (taxi), roof rack
    if kind == 'pickup':
        bz = _interp(sp.belt, 0.2)
        bx0, bx1 = shift + L * 0.0, shift + L * 0.44
        body.box((-W * 0.5 + 0.0, bx0, bz - 0.12), (-W * 0.5 + 0.1, bx1, bz + 0.38), paint_m, tile=1.5)
        body.box((W * 0.5 - 0.1, bx0, bz - 0.12), (W * 0.5, bx1, bz + 0.38), paint_m, tile=1.5)
        body.box((-W * 0.5, bx0, bz - 0.12), (W * 0.5, bx0 + 0.1, bz + 0.38), paint_m, tile=1.5)
        body.box((-W * 0.5 + 0.1, bx0 + 0.1, bz - 0.15), (W * 0.5 - 0.1, bx1, bz + 0.0), MT('rust'), tile=1.0)
    if paint == 'car_yellow' and kind == 'sedan':
        top = _interp(sp.top, 0.5)
        body.box((-0.35, shift + L * 0.46, top), (0.35, shift + L * 0.46 + 0.2, top + 0.2), MT('car_white'), tile=0.5)
    # ---------- wheels
    axles = [(-sp.wb / 2, 0), (sp.wb / 2, 1)] if kind not in ('bus', 'lorry') else [(-sp.wb / 2 - (0.0 if kind == 'bus' else 0.0), 0), (sp.wb / 2, 1)]
    wc = []
    fi = 0
    wheels = Mesh()
    sag = []
    for ay, _ in axles:
        for sx in (-1, 1):
            f = bool(flat[fi]) if fi < len(flat) else False
            fi += 1
            wheel(wheels, (sx * sp.track / 2, ay, sp.tr), sp.tr, 0.22 if kind not in ('bus', 'lorry') else 0.30, sx, flat=f, rust=rust)
            wc.append((sx * sp.track / 2, ay, f))
            # wheel arch
            ar = sp.tr + 0.07
            pts = []
            for a in np.linspace(0, np.pi, 11):
                zz = sp.tr + np.sin(a) * ar
                yy = ay + np.cos(a) * ar
                pts.append((sx * (W * 0.5 + 0.006), yy, max(zz, sp.zb + 0.12)))
            wheels.poly(pts, black, hint=(sx, 0, 0), tile=0.5)
    # body sag from flat tyres: rotate body slightly
    dz = np.array([0.09 if f else 0.0 for (_, _, f) in wc])
    if dz.any():
        # fit plane z = a*x + b*y + c to the sag at wheel positions, apply to body as a small rotation
        A = np.array([[x, y, 1] for x, y, _ in wc])
        coef = np.linalg.lstsq(A, -dz, rcond=None)[0]
        for k, (p, n, u, t, m_, e) in enumerate(body.chunks):
            p2 = p.copy()
            p2[:, 2] += (p[:, 0] * coef[0] + p[:, 1] * coef[1] + coef[2]) * np.clip(p[:, 2] / 0.5, 0.2, 1.0)
            body.chunks[k] = (p2, n, u, t, m_, e)
    M.chunks += body.chunks + wheels.chunks
    # collision: lower body + cabin
    C = Col()
    zt = max(p[1] for p in sp.top)
    cab = [s for s in np.linspace(0, 1, 50) if _interp(sp.top, s) - _interp(sp.belt, s) > 0.25]
    C.box((-W * 0.5, shift + 0.05, sp.zb), (W * 0.5, shift + L - 0.05, max(_interp(sp.belt, 0.5), 0.9)))
    if cab:
        C.box((-W * 0.44, shift + L * cab[0], sp.zb), (W * 0.44, shift + L * cab[-1], zt))
    return M, C


def ao_car(pos, nrm):
    z = pos[:, 2]
    up = np.clip(nrm[:, 2], 0, 1)
    return (0.55 + 0.45 * np.clip(z / 0.9, 0, 1) ** 0.8) * (0.9 + 0.1 * up)


# name: (kind, paint, seed, flat, glass_dmg, rust)
CARS = {
    'car_sedan_a': ('sedan', 'car_red', 3, (0, 0, 1, 0), 0.6, False),
    'car_sedan_b': ('sedan', 'car_white', 4, (0, 0, 0, 0), 0.4, False),
    'car_sedan_c': ('sedan', 'car_grey', 5, (1, 1, 0, 1), 0.8, True),
    'car_hatch_a': ('hatch', 'car_blue', 6, (0, 1, 0, 0), 0.5, False),
    'car_hatch_b': ('hatch', 'car_green', 7, (0, 0, 0, 0), 0.7, True),
    'car_suv_a': ('suv', 'car_grey', 8, (0, 0, 0, 1), 0.5, False),
    'car_suv_b': ('suv', 'car_white', 9, (1, 0, 0, 0), 0.6, False),
    'car_van_a': ('van', 'car_white', 10, (0, 0, 1, 1), 0.5, True),
    'car_van_b': ('van', 'car_blue', 11, (0, 0, 0, 0), 0.7, False),
    'car_pickup_a': ('pickup', 'car_green', 12, (1, 0, 0, 0), 0.6, True),
    'car_pickup_b': ('pickup', 'car_red', 13, (0, 0, 0, 0), 0.5, False),
    'car_taxi': ('sedan', 'car_yellow', 14, (0, 1, 0, 0), 0.6, False),
    'car_bus': ('bus', 'car_yellow', 15, (1, 1, 0, 0), 0.7, True),
    'car_lorry': ('lorry', 'container', 16, (0, 0, 0, 0), 0.5, True),
}
for _n, (_k, _p, _s, _f, _g, _r) in CARS.items():
    def _mk(n=_n, k=_k, p=_p, s=_s, f=_f, g=_g, r=_r):
        def run():
            M, C = build_car(k, p, s, f, g, r)
            return M, C, ao_car
        asset('af_' + n, 'props', dist=260.0, day_glow=0.0)(run)
    _mk()
