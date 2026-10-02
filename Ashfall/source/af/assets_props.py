# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# assets_props.py - street props of the dead city: lamps, traffic lights, signs, hydrants, dumpsters, barriers,
#   containers, bus shelter, power poles + sagging wires, billboards, rubble, barrels, crates, gas station parts.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit, TAU
from . import gx
from .kit import asset, m, col_bar, ao_crown
from .pv import ao_default

UP = np.array([0, 0, 1.0])


def _ao(P, N):
    return 0.66 + 0.34 * np.clip(P[:, 2] / 3.0, 0, 1)


def rnd(seed):
    return np.random.default_rng(seed)


def pole(M, p0, p1, r0, r1, mat, n=10):
    gx.tube(M, [p0, (np.array(p0) + np.array(p1)) / 2, p1], [r0, (r0 + r1) / 2, r1], n, mat, tile=1.5, cap_end=True)


def bent_pole(M, base, pts_up, r0, r1, mat, n=10):
    pts = [base] + list(pts_up)
    rr = np.linspace(r0, r1, len(pts))
    gx.tube(M, pts, list(rr), n, mat, tile=1.5, cap_end=True)


# ---------------------------------------------------------------------------------------------- lamps
def lamp_geo(seed, lean=0.0, bend=0.0, fallen=False, h=7.5):
    r = rnd(seed)
    M, C = Mesh(), Col()
    steel, rust = m('steel'), m('rust')
    M.prism((0, 0), 0.26, 0.0, 0.55, 10, m('concrete'), tile=1.0)
    n = 9
    if fallen:
        ang = r.uniform(0, TAU)
        d = np.array([np.cos(ang), np.sin(ang), 0])
        pts = [np.array([0, 0, 0.5])] + [d * (h * t) + np.array([0, 0, 0.5 + 0.18 * (1 - t) ** 2 * 3 + 0.2 * t]) for t in np.linspace(0.05, 1, n)]
        gx.tube(M, pts, list(np.linspace(0.12, 0.06, len(pts))), 9, steel, tile=1.5, cap_end=True)
        end = pts[-1]
        gx.bar(M, end, end + d * 1.6, 0.07, steel)
        gx.bar(M, end + d * 1.6, end + d * 1.9 + np.array([0, 0, -0.1]), 0.35, m('glass_broken'), h=0.18)
        C.strip(pts[0][:2], pts[-1][:2], 0.3, 0.2, 0.7) if False else col_bar(C, pts[1], end, 0.28, 0.28)
        return M, C, _ao
    pts = []
    for i in range(n + 1):
        t = i / n
        bx = lean * t * t * 1.2 + bend * max(0, t - 0.55) ** 1.5 * 4
        pts.append(np.array([bx, 0.0, 0.5 + (h - 0.5) * t - (abs(bend) * 0.6 * max(0, t - 0.55) ** 1.5 * 4)]))
    gx.tube(M, pts, list(np.linspace(0.14, 0.065, len(pts))), 10, steel, tile=1.5, cap_end=True)
    top = pts[-1]
    # curved arm
    arm = [top, top + np.array([0.3, 0, 0.35]), top + np.array([1.2, 0, 0.55]), top + np.array([2.1, 0, 0.42])]
    gx.tube(M, arm, [0.06, 0.055, 0.05, 0.045], 8, steel, tile=1.5, cap_end=True)
    head = arm[-1]
    gx.bar(M, head - np.array([0.1, 0, 0]), head + np.array([0.9, 0, 0.0]), 0.28, rust, h=0.12)
    gx.bar(M, head + np.array([0.0, 0, -0.07]), head + np.array([0.85, 0, -0.07]), 0.24, m('glass_broken'), h=0.03)
    M.box((-0.22, -0.02, 1.3), (0.22, 0.02, 1.9), rust, tile=1.0) if False else None
    C.box((-0.2, -0.2, 0), (0.2, 0.2, 3.5))
    return M, C, _ao


asset('af_lamp_a', 'props', 190)(lambda: lamp_geo(1))
asset('af_lamp_b', 'props', 190)(lambda: lamp_geo(2, lean=0.9, bend=0.8))
asset('af_lamp_c', 'props', 190)(lambda: lamp_geo(3, fallen=True))
asset('af_lamp_d', 'props', 190)(lambda: lamp_geo(4, lean=-0.4, h=9.0))


# ---------------------------------------------------------------------------------------------- traffic lights
def tlight_geo(seed, lean=0.0, drop=False):
    r = rnd(seed)
    M, C = Mesh(), Col()
    steel, rust = m('steel'), m('rust')
    pts = [np.array([lean * t * t, 0, 6.0 * t]) for t in np.linspace(0, 1, 7)]
    gx.tube(M, pts, list(np.linspace(0.13, 0.08, 7)), 10, steel, tile=1.5, cap_end=True)
    top = pts[-1]
    arm_end = top + np.array([0, 5.2, 0.0])
    gx.tube(M, [top + np.array([0, 0, -0.2]), top + np.array([0, 2.5, 0.35]), arm_end + np.array([0, 0, 0.25]) - np.array([0, 0, 0.05 if not drop else 0.9])], [0.07, 0.06, 0.05], 8, steel, tile=1.5, cap_end=True)
    for k, y in enumerate((2.0, 4.3, 5.1)):
        head = top + np.array([0, y, 0.30 - (0.0 if not drop else 0.18 * k)])
        M.box((head[0] - 0.17, head[1] - 0.17, head[2] - 1.05), (head[0] + 0.17, head[1] + 0.17, head[2] - 0.0), steel if k != 1 else rust, tile=1.0)
        for j in range(3):
            zz = head[2] - 0.18 - j * 0.32
            M.box((head[0] - 0.14, head[1] + 0.17, zz - 0.11), (head[0] + 0.14, head[1] + 0.20, zz + 0.11), m('glass_broken') if (j + k) % 2 else m('interior'), tile=0.3)
    C.box((-0.18, -0.18, 0), (0.18, 0.18, 3.0))
    return M, C, _ao


asset('af_tlight_a', 'props', 190)(lambda: tlight_geo(1))
asset('af_tlight_b', 'props', 190)(lambda: tlight_geo(2, lean=0.7, drop=True))


# ---------------------------------------------------------------------------------------------- signs
def sign_geo(kind, seed, tilt=0.0):
    r = rnd(seed)
    M, C = Mesh(), Col()
    steel = m('steel')
    pts = [np.array([tilt * t * t * 0.3, 0, 2.9 * t]) for t in np.linspace(0, 1, 5)]
    gx.tube(M, pts, [0.045] * 5, 8, steel, tile=1.0, cap_end=True)
    top = pts[-1]
    if kind == 'stop':
        # octagon plate, 0.75 wide
        rr = 0.40
        ring = [(top[0] + np.cos(a + TAU / 16) * rr, top[1] + 0.06, top[2] + 0.1 + np.sin(a + TAU / 16) * rr) for a in np.linspace(0, TAU, 8, endpoint=False)]
        uvs = [(0.5 + np.cos(a + TAU / 16) * 0.5 / np.cos(TAU / 16) * 0.97, 0.5 - np.sin(a + TAU / 16) * 0.5 / np.cos(TAU / 16) * 0.97) for a in np.linspace(0, TAU, 8, endpoint=False)]
        # texture is 512 x 128 for stop? use the whole square image
        M.poly(ring, m('sign_stop'), hint=(0, 1, 0), uv=uvs)
        M.poly([(p[0], p[1] - 0.012, p[2]) for p in ring], m('rust'), hint=(0, -1, 0), tile=0.5)
    else:
        w, h = 0.95, 0.3
        for i, y0 in enumerate((0.0,)):
            q = [(top[0] - w / 2, top[1] + 0.06, top[2] - h / 2 + 0.05), (top[0] + w / 2, top[1] + 0.06, top[2] - h / 2 + 0.05),
                 (top[0] + w / 2, top[1] + 0.06, top[2] + h / 2 + 0.05), (top[0] - w / 2, top[1] + 0.06, top[2] + h / 2 + 0.05)]
            M.poly(q, m('sign_street'), hint=(0, 1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
            M.poly([(p[0], p[1] - 0.012, p[2]) for p in q], m('rust'), hint=(0, -1, 0), tile=0.5)
    C.box((-0.1, -0.1, 0), (0.1, 0.1, 2.5))
    return M, C, _ao


asset('af_sign_stop', 'props', 150)(lambda: sign_geo('stop', 1, 0.0))
asset('af_sign_stop_b', 'props', 150)(lambda: sign_geo('stop', 2, 1.4))
asset('af_sign_street', 'props', 150)(lambda: sign_geo('street', 3, 0.0))


# ---------------------------------------------------------------------------------------------- street furniture
@asset('af_hydrant', 'props', 110)
def hydrant():
    M, C = Mesh(), Col()
    red = m('car_red')
    M.prism((0, 0), 0.17, 0.0, 0.6, 12, red, tile=0.6)
    M.prism((0, 0), 0.20, 0.6, 0.72, 12, red, tile=0.6)
    M.prism((0, 0), 0.12, 0.72, 0.82, 10, m('rust'), tile=0.6, cap_top=True)
    gx.bar(M, (-0.30, 0, 0.45), (0.30, 0, 0.45), 0.13, red)
    C.box((-0.22, -0.22, 0), (0.22, 0.22, 0.8))
    return M, C, _ao


@asset('af_dumpster', 'props', 130)
def dumpster():
    M, C = Mesh(), Col()
    g = m('car_green')
    M.box((-1.1, -0.6, 0.18), (1.1, 0.6, 1.25), g, tile=1.5)
    M.box((-1.1, -0.65, 1.25), (1.1, 0.65, 1.32), m('rust'), tile=1.5)
    # lid half open
    gx.bar(M, (-1.1, 0.65, 1.32), (-1.1, 0.0, 1.98), 0.0 + 1.0, m('rust'), h=0.05, caps=False) if False else None
    M.quad((-1.1, 0.65, 1.32), (1.1, 0.65, 1.32), (1.1, 0.35, 1.95), (-1.1, 0.35, 1.95), m('car_green'), hint=(0, 0, 1), tile=1.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            M.prism((sx * 0.9, sy * 0.45), 0.08, 0.0, 0.18, 8, m('tire'), tile=0.3)
    # garbage spilling
    r = rnd(5)
    for _ in range(7):
        gx.rock(M, (r.uniform(-0.9, 0.9), r.uniform(-0.4, 0.4), 1.28), (0.28, 0.24, 0.16), m(['concrete', 'rust', 'brick'][int(r.integers(0, 3))]), int(r.integers(1, 99999)), n=8)
    C.box((-1.12, -0.65, 0.0), (1.12, 0.65, 1.35))
    return M, C, _ao


@asset('af_barrel', 'props', 100)
def barrel():
    M, C = Mesh(), Col()
    M.prism((0, 0), 0.30, 0.0, 0.88, 14, m('rust'), tile=0.8, cap_top=True)
    for z in (0.2, 0.45, 0.7):
        M.prism((0, 0), 0.31, z, z + 0.04, 14, m('steel'), tile=0.5)
    C.box((-0.28, -0.28, 0), (0.28, 0.28, 0.88))
    return M, C, _ao


@asset('af_crates', 'props', 100)
def crates():
    M, C = Mesh(), Col()
    r = rnd(3)
    for (x, y, z, s, rz) in ((0, 0, 0, 0.9, 0), (1.0, 0.05, 0, 0.8, 8), (0.45, 0.1, 0.9, 0.75, -12), (-0.95, 0.2, 0, 0.7, 20)):
        c, sn = np.cos(np.radians(rz)), np.sin(np.radians(rz))
        pts = [(x + (a * c - b * sn) * s / 2, y + (a * sn + b * c) * s / 2) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for k in range(4):
            pass
        M.box((x - s / 2, y - s / 2, z), (x + s / 2, y + s / 2, z + s), m('wood'), tile=0.9)
        gx.bar(M, (x - s / 2 - 0.01, y - s / 2 - 0.01, z + s * 0.5), (x + s / 2 + 0.01, y - s / 2 - 0.01, z + s * 0.5), 0.06, m('wooddark') if False else m('wood'), h=0.08)
    C.box((-1.35, -0.45, 0), (1.45, 0.55, 1.0))
    return M, C, _ao


@asset('af_jersey_a', 'props', 150)
def jersey_a():
    M, C = Mesh(), Col()
    prof = [(-0.30, 0.0), (0.30, 0.0), (0.30, 0.06), (0.17, 0.30), (0.12, 0.8), (-0.12, 0.8), (-0.17, 0.30), (-0.30, 0.06)]
    # extrude along y (3.0 m)
    L = 3.0
    ring0 = [(x, -L / 2, z) for x, z in prof]
    ring1 = [(x, L / 2, z) for x, z in prof]
    k = len(prof)
    for i in range(k):
        j = (i + 1) % k
        cen = (prof[j][1] - prof[i][1], 0, -(prof[j][0] - prof[i][0]))      # outward normal of the profile edge
        M.poly([ring0[i], ring0[j], ring1[j], ring1[i]], m('barrier'), hint=(cen[0] * 1.0, 0, cen[2]), uv=[(0, 0), (0, 1), (1, 1), (1, 0)] if False else None, tile=1.5)
    for i in range(k):                     # end caps: the profile is concave -> triangle fan around an interior point
        j = (i + 1) % k
        for ring, h in ((ring0, (0, -1, 0)), (ring1, (0, 1, 0))):
            M.poly([(0.0, ring[0][1], 0.4), ring[i], ring[j]], m('barrier'), hint=h, tile=1.5)
    C.box((-0.30, -1.5, 0), (0.30, 1.5, 0.8))
    return M, C, _ao


@asset('af_barricade', 'props', 120)
def barricade():
    M, C = Mesh(), Col()
    for sx in (-1, 1):
        gx.bar(M, (sx * 0.9, -0.35, 0.0), (sx * 0.9, 0.0, 0.95), 0.07, m('steel'))
        gx.bar(M, (sx * 0.9, 0.35, 0.0), (sx * 0.9, 0.0, 0.95), 0.07, m('steel'))
    for z in (0.55, 0.85):
        M.box((-1.1, -0.03, z), (1.1, 0.03, z + 0.2), m('barrier'), tile=1.0)
    C.box((-1.1, -0.35, 0), (1.1, 0.35, 1.05))
    return M, C, _ao


@asset('af_container', 'props', 300)
def container():
    M, C = Mesh(), Col()
    L, W, H = 6.06, 2.44, 2.6
    M.box((-W / 2, -L / 2, 0.0), (W / 2, L / 2, H), m('container'), tile=3.0)
    # ribs on the doors end
    for y in (-L / 2 - 0.02, L / 2 + 0.0):
        for i in range(-3, 4):
            M.box((i * 0.3 - 0.02, y, 0.15), (i * 0.3 + 0.02, y + 0.03, H - 0.15), m('steel'), tile=0.5)
    # rusty feet
    for sx in (-1, 1):
        M.box((sx * W / 2 - 0.08, -L / 2, -0.0), (sx * W / 2 + 0.08, L / 2, 0.14), m('rust'), tile=1.0) if False else None
    C.box((-W / 2, -L / 2, 0), (W / 2, L / 2, H))
    return M, C, _ao


@asset('af_container_stack', 'props', 300)
def container_stack():
    M, C = Mesh(), Col()
    L, W, H = 6.06, 2.44, 2.6
    for (x, y, z, rz, mt) in ((0, 0, 0, 0, 'container'), (0, 0, H, 4, 'container'), (W + 0.3, 0.3, 0, -3, 'container')):
        c, s_ = np.cos(np.radians(rz)), np.sin(np.radians(rz))
        pts = [(x + a * c - b * s_, y + a * s_ + b * c) for a, b in ((-W / 2, -L / 2), (W / 2, -L / 2), (W / 2, L / 2), (-W / 2, L / 2))]
        sub = Mesh()
        sub.box((-W / 2, -L / 2, 0), (W / 2, L / 2, H), m(mt), tile=3.0)
        for p_, n_, u_, t_, mm, e_ in sub.chunks:
            R = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
            M.chunks.append((p_ @ R.T + np.array([x, y, z]), n_ @ R.T, u_, t_, mm, e_))
        C.box((x - W / 2, y - L / 2, z), (x + W / 2, y + L / 2, z + H))
    return M, C, _ao


@asset('af_busstop', 'props', 160)
def busstop():
    M, C = Mesh(), Col()
    steel, glass = m('steel'), m('glass_broken')
    for sx in (-1.6, 1.6):
        for sy in (-0.7, 0.7):
            gx.bar(M, (sx, sy, 0), (sx, sy, 2.5), 0.08, steel)
    M.box((-1.8, -0.9, 2.5), (1.8, 0.9, 2.58), m('rust'), tile=1.5)
    M.box((-1.6, 0.66, 0.35), (1.6, 0.7, 2.4), m('interior'), tile=1.0)
    M.box((-1.6, 0.62, 0.35), (-0.4, 0.66, 2.4), glass, tile=1.2)
    M.box((-1.3, 0.2, 0.4), (1.3, 0.6, 0.48), m('wood'), tile=1.0)
    C.box((-1.7, -0.8, 0), (1.7, 0.8, 2.6))
    return M, C, _ao


@asset('af_bench_s', 'props', 100)
def bench_s():
    M, C = Mesh(), Col()
    for sx in (-0.8, 0.8):
        M.box((sx - 0.04, -0.2, 0.0), (sx + 0.04, 0.2, 0.45), m('steel'), tile=0.6)
    for z in (0.45, 0.5):
        pass
    M.box((-1.0, -0.22, 0.45), (1.0, 0.22, 0.5), m('wood'), tile=1.0)
    M.box((-1.0, 0.18, 0.5), (1.0, 0.23, 0.95), m('wood'), tile=1.0)
    C.box((-1.0, -0.25, 0), (1.0, 0.25, 0.95))
    return M, C, _ao


@asset('af_trashcan', 'props', 90)
def trashcan():
    M, C = Mesh(), Col()
    M.prism((0, 0), 0.25, 0.0, 0.8, 12, m('steel'), tile=0.8, cap_top=True)
    M.prism((0, 0), 0.27, 0.78, 0.82, 12, m('rust'), tile=0.6)
    C.box((-0.25, -0.25, 0), (0.25, 0.25, 0.82))
    return M, C, _ao


# ---------------------------------------------------------------------------------------------- power poles
def power_pole(seed, lean=0.0):
    r = rnd(seed)
    M, C = Mesh(), Col()
    wood = m('wood')
    pts = [np.array([lean * t * t * 1.5, 0, 10.0 * t - 0.2]) for t in np.linspace(0, 1, 6)]
    gx.tube(M, pts, list(np.linspace(0.20, 0.13, 6)), 10, wood, tile=1.0, cap_end=True)
    top = pts[-1]
    z = top[2] - 0.9
    c = np.array([pts[4][0] + (top[0] - pts[4][0]) * 0.0, 0, z])
    for zz, ln in ((z, 1.2), (z - 1.5, 0.9)):
        cx = top[0] * (zz + 0.2) / 10.0 ** 1.0 * 0.0 + np.interp(zz, [p[2] for p in pts], [p[0] for p in pts])
        gx.bar(M, (cx - ln, 0, zz), (cx + ln, 0, zz), 0.10, wood, h=0.14)
        for sx in (-ln * 0.85, 0, ln * 0.85):
            gx.cyl(M, (cx + sx, 0, zz + 0.07), (cx + sx, 0, zz + 0.3), 0.05, 0.035, 8, m('concrete'), tile=0.4)
    # transformer
    M.prism((0.0, 0.32), 0.26, 6.2 - 0.6, 6.2 + 0.2, 10, m('steel'), tile=1.0)
    C.box((-0.22, -0.22, 0), (0.22, 0.22, 3.0))
    return M, C, _ao


asset('af_pole_a', 'props', 220)(lambda: power_pole(1))
asset('af_pole_b', 'props', 220)(lambda: power_pole(2, lean=0.9))


def wires_geo(span, sag, nlines=3, seed=1, droop_end=0.0, y=0.0):
    """alpha strip cables from (0,0) to (span,0) (local +x), 3 cables, catenary sag; double sided ribbons"""
    M, C = Mesh(), Col()
    wire = m('wire')
    for k, (oy, oz) in enumerate(((-0.9, 9.2), (0.0, 9.2), (0.9, 9.2))[:nlines]):
        z0 = oz - (0 if k != 2 else 1.5)
        n = 14
        P, UV, T = [], [], []
        for i in range(n + 1):
            t = i / n
            x = span * t
            zz = z0 - 4 * sag * t * (1 - t) * (-1) * -1 - droop_end * t ** 4
            zz = z0 - sag * 4 * t * (1 - t) - droop_end * t ** 6
            # two crossed ribbons (flat + vertical) so it reads from every angle
            P += [(x, oy - 0.06, zz), (x, oy + 0.06, zz)]
            UV += [(t * span / 3, 0.0), (t * span / 3, 1.0)]
        for i in range(n):
            a = 2 * i
            T += [[a, a + 1, a + 3], [a, a + 3, a + 2]]
        N = [(0, 0, 1)] * len(P)
        M.add(P, N, UV, T, wire)
        M.add(P, N, UV, [t[::-1] for t in T], wire)
        P2 = [(p[0], p[1] + (0.06 if j % 2 == 0 else -0.06), p[2] + (-0.06 if j % 2 == 0 else 0.06)) for j, p in enumerate(P)]
        P2 = [(p[0], P[j][1] * 0 + oy, p[2] + (-0.06 if j % 2 == 0 else 0.06)) for j, p in enumerate(P)]
        M.add(P2, N, UV, T, wire)
        M.add(P2, N, UV, [t[::-1] for t in T], wire)
    return M, C, None


asset('af_wires30', 'flora', 260)(lambda: wires_geo(30.0, 0.9))
asset('af_wires30_b', 'flora', 260)(lambda: wires_geo(30.0, 2.6, droop_end=5.0))


# ---------------------------------------------------------------------------------------------- billboard
@asset('af_billboard', 'props', 420)
def billboard():
    M, C = Mesh(), Col()
    steel, rust = m('steel'), m('rust')
    W, H, z0 = 12.0, 3.9, 6.0
    for sx in (-4.0, 4.0):
        gx.bar(M, (sx, 0, 0), (sx, 0, z0 + H - 0.2), 0.45, steel)
        gx.bar(M, (sx, 0.2, 0.1), (sx, 0.8, 0.1), 0.6, m('concrete'), h=0.2) if False else None
    M.box((-W / 2 - 0.15, 0.2, z0 - 0.15), (W / 2 + 0.15, 0.55, z0 + H + 0.15), rust, tile=2.0, skip=('+y',))
    # board (front, +y) split in two so one half hangs torn
    q = [(-W / 2, 0.56, z0), (W / 2, 0.56, z0), (W / 2, 0.56, z0 + H), (-W / 2, 0.56, z0 + H)]
    M.poly(q, m('billboard'), hint=(0, 1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    M.box((-W / 2 - 0.2, 0.2, z0 - 0.7), (W / 2 + 0.2, 0.9, z0 - 0.55), steel, tile=2.0)      # catwalk
    C.box((-4.3, -0.3, 0), (4.3, 0.3, z0 + H)) if False else None
    for sx in (-4.0, 4.0):
        C.box((sx - 0.25, -0.25, 0), (sx + 0.25, 0.25, z0 + H))
    C.box((-W / 2, 0.2, z0), (W / 2, 0.6, z0 + H))
    return M, C, _ao


# ---------------------------------------------------------------------------------------------- rubble
def rubble_geo(seed, R, n, h):
    r = rnd(seed)
    M, C = Mesh(), Col()
    mats = [m('concrete'), m('concrete'), m('brick'), m('plaster_a'), m('concrete')]
    for k in range(n):
        rad = r.uniform(0, R) ** 0.8
        a = r.uniform(0, TAU)
        sz = r.uniform(0.35, 1.2) * (1.2 - 0.6 * rad / R)
        z = max(0.0, (1 - rad / R) * h * r.uniform(0.3, 1.0)) * 0.6
        gx.rock(M, (np.cos(a) * rad, np.sin(a) * rad, z + sz * 0.1), (sz * 1.3, sz, sz * 0.75), mats[int(r.integers(0, len(mats)))], int(r.integers(1, 10 ** 6)), n=10)
    # slabs and rebar
    for k in range(3):
        a = r.uniform(0, TAU)
        d = np.array([np.cos(a), np.sin(a), 0])
        p0 = d * r.uniform(0.2, R * 0.6) + np.array([0, 0, 0.35])
        p1 = p0 + d * r.uniform(1.8, 3.2) + np.array([0, 0, r.uniform(0.5, 1.4)])
        gx.bar(M, p0, p1, 1.4, m('concrete'), h=0.22, tile=1.5)
        for q in range(3):
            o = np.array([-d[1], d[0], 0]) * r.uniform(-0.5, 0.5)
            gx.bar(M, p1 + o, p1 + o + d * 0.6 + np.array([0, 0, r.uniform(0.2, 0.7)]), 0.035, m('rust'))
    C.box((-R * 0.6, -R * 0.6, 0), (R * 0.6, R * 0.6, h * 0.55))
    return M, C, _ao


asset('af_rubble_a', 'props', 230)(lambda: rubble_geo(1, 3.6, 22, 2.4))
asset('af_rubble_b', 'props', 230)(lambda: rubble_geo(2, 5.0, 36, 3.2))
asset('af_rubble_c', 'props', 230)(lambda: rubble_geo(3, 2.4, 12, 1.4))


# ---------------------------------------------------------------------------------------------- gas station
@asset('af_gas_canopy', 'props', 360)
def gas_canopy():
    M, C = Mesh(), Col()
    W, D, H = 14.0, 9.0, 5.2
    for sx in (-W / 2 + 1.5, W / 2 - 1.5):
        for sy in (-D / 2 + 1.5, D / 2 - 1.5):
            M.box((sx - 0.25, sy - 0.25, 0), (sx + 0.25, sy + 0.25, H), m('plaster_c'), tile=2.0)
    M.box((-W / 2, -D / 2, H), (W / 2, D / 2, H + 0.5), m('plaster_c'), tile=2.0, mats={'+z': m('roofing')})
    M.box((-W / 2 + 0.2, -D / 2 + 0.2, H + 0.5), (W / 2 - 0.2, -D / 2 + 0.4, H + 0.9), m('rust'), tile=2.0)
    for sx in (-3.5, 3.5):                                     # pump islands
        M.box((sx - 0.4, -1.8, 0), (sx + 0.4, 1.8, 0.2), m('concrete'), tile=1.0)
        for sy in (-1.0, 1.0):
            M.box((sx - 0.3, sy - 0.2, 0.2), (sx + 0.3, sy + 0.2, 1.45), m('car_red'), tile=0.8)
            M.box((sx - 0.25, sy - 0.21, 0.95), (sx + 0.25, sy - 0.2, 1.3), m('glass_broken'), tile=0.5)
    for sx in (-W / 2 + 1.5, W / 2 - 1.5):
        for sy in (-D / 2 + 1.5, D / 2 - 1.5):
            C.box((sx - 0.3, sy - 0.3, 0), (sx + 0.3, sy + 0.3, H))
    for sx in (-3.5, 3.5):
        C.box((sx - 0.4, -1.8, 0), (sx + 0.4, 1.8, 1.45))
    return M, C, _ao


@asset('af_border', 'props', 700)
def border():
    """invisible border wall segment (the client sets its alpha to 0): a tiny visual stub + a 100 x 1.5 x 175 m collision slab"""
    M, C = Mesh(), Col()
    M.box((-0.05, -0.05, 0.0), (0.05, 0.05, 0.1), m('steel'), tile=1.0)
    C.box((-50.0, -0.75, -5.0), (50.0, 0.75, 170.0))
    return M, C, _ao
