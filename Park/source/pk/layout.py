# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# layout.py - the park plan.  Park frame: x -60..60, y 0..90, origin at the centre of the entrance gate, +y into the park,
#             z = 0 on the podium (the surrounding terrain is 0.9 m lower: the park sits on a gentle embankment).
#   * height field h(x, y) (embankment, entrance ramp, pond bowl)
#   * ground tiles (12) with grass / dirt / pond bed, paths (paving, cobbles, curbs), plazas, playground rubber
#   * every placed object (model name, position, yaw) - trees, bushes, flower beds, benches, lamps, fence ...
# Everything is deterministic (seeded) so the build is reproducible.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, unit, TAU
from . import gx
from .kit import m, bin_mesh

PX, PY0, PY1 = 60.0, 0.0, 90.0
POND_C, POND_R = (36.0, 40.0), (17.0, 7.0)
POND_DEPTH, WATER_Z = 1.6, -0.30
OUT_Z = -0.90
TILE_X = [-66.0, -33.0, 0.0, 33.0, 66.0]
TILE_Y = [-18.0, 24.0, 66.0, 96.0]


def pond_r(x, y):
    return np.sqrt(((x - POND_C[0]) / POND_R[0]) ** 2 + ((y - POND_C[1]) / POND_R[1]) ** 2)


def hfield(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    dx = np.maximum(np.abs(x) - PX, 0)
    dy = np.maximum(np.maximum(PY0 - y, y - PY1), 0)
    d = np.hypot(dx, dy)
    he = OUT_Z * np.clip(d / 2.7, 0, 1)
    hr = OUT_Z * np.clip(-y / 14.0, 0, 1) + OUT_Z * np.clip((np.abs(x) - 5.0) / 2.7, 0, 1)
    h = np.where(y < 0, np.maximum(he, hr), he)
    s = np.clip((1 - pond_r(x, y)) / 0.45, 0, 1)
    return h - POND_DEPTH * s * s * (3 - 2 * s)


def axis(lo, hi, bps, zones):
    vals = list(bps)
    cands = list(np.arange(lo, hi + 1e-6, 2.5))
    for a, b, st in zones:
        cands += list(np.arange(a, b + 1e-6, st))
    for c in sorted(cands):
        if lo - 1e-6 <= c <= hi + 1e-6 and min(abs(c - v) for v in vals) > 0.38:
            vals.append(float(c))
    return np.array(sorted(set(round(v, 4) for v in vals)))


XS = axis(-66, 66, TILE_X + [-60, 60, -62.7, 62.7, -5, 5, -7.7, 7.7], [(-63.5, -58.5, 0.9), (58.5, 63.5, 0.9), (17, 55, 0.75), (-6, 6, 1.5)])
YS = axis(-18, 96, TILE_Y + [0, 90, 92.7, -14, -2.7, 2.7], [(-3, 3, 0.9), (88.5, 94, 0.9), (31, 49, 0.75)])


def ground_tile(ix, iy):
    """grass/dirt/pond-bed surface of one tile as a Mesh (park coordinates)"""
    xs = XS[(XS >= TILE_X[ix] - 1e-6) & (XS <= TILE_X[ix + 1] + 1e-6)]
    ys = YS[(YS >= TILE_Y[iy] - 1e-6) & (YS <= TILE_Y[iy + 1] + 1e-6)]
    X, Y = np.meshgrid(xs, ys)
    Z = hfield(X, Y)
    e = 0.3
    nx = -(hfield(X + e, Y) - hfield(X - e, Y)) / (2 * e)
    ny = -(hfield(X, Y + e) - hfield(X, Y - e)) / (2 * e)
    N = np.stack([nx, ny, np.ones_like(nx)], -1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    P = np.stack([X, Y, Z], -1).reshape(-1, 3)
    N = N.reshape(-1, 3)
    UV = np.stack([X.reshape(-1) / 4.0, Y.reshape(-1) / 4.0], -1)
    ny_, nx_ = len(ys), len(xs)
    T = {}
    pb, dirt, gr = m('pondbed'), m('dirt'), m('grass')
    for j in range(ny_ - 1):
        for i in range(nx_ - 1):
            a = j * nx_ + i
            for t in ([a, a + 1, a + nx_ + 1], [a, a + nx_ + 1, a + nx_]):
                cx, cy = P[t][:, 0].mean(), P[t][:, 1].mean()
                r = float(pond_r(cx, cy))
                mt = pb if r < 0.80 else (dirt if r < 0.93 else gr)
                T.setdefault(mt, []).append(t)
    M = Mesh()
    for mt, tr in T.items():
        M.add(P, N, UV, tr, mt)
    return M, (P, N, np.array(sum(T.values(), [])))


# ---------------------------------------------------------------------------------------------------- paths
PATHS = []      # (name, pts, width, mat_key, z offset, curb)
PLAZAS = []     # (x0, y0, x1, y1, mat, zoff, curb)
DISCS = []      # (cx, cy, r, mat, zoff)
RING_C = (0.0, 40.0)
GAZEBO_C = (-38.0, 40.0)
PLAY = (24.0, 58.0, 52.0, 80.0)


def setup_paths():
    PATHS.clear(); PLAZAS.clear(); DISCS.clear()
    PATHS.append(('entrance', [(0, -14), (0, 0.5)], 8.0, 'paving', 0.045, True))
    PATHS.append(('main_s', [(0, 0), (0, 29)], 5.0, 'paving', 0.045, False))
    PATHS.append(('main_n', [(0, 51), (0, 86)], 5.0, 'paving', 0.045, False))
    ring = [(RING_C[0] + 10.7 * np.cos(a), RING_C[1] + 10.7 * np.sin(a)) for a in np.linspace(0, TAU, 49)]
    PATHS.append(('ring', ring, 4.6, 'paving', 0.045, True))
    DISCS.append((RING_C[0], RING_C[1], 8.4, 'cobble', 0.040))
    PATHS.append(('west', [(-12.5, 40), (-34, 40)], 3.0, 'paving', 0.041, False))
    DISCS.append((GAZEBO_C[0], GAZEBO_C[1], 5.2, 'cobble', 0.040))
    PATHS.append(('east', [(0, 24), (36, 24), (36, 33.3)], 3.0, 'paving', 0.042, False))
    PATHS.append(('east2', [(36, 46.7), (36, 58)], 3.0, 'paving', 0.042, False))
    PATHS.append(('nw', [(0, 66), (-34, 66), (-34, 40)], 3.0, 'paving', 0.041, False))
    PATHS.append(('perim', [(2.5, 6), (55, 6), (55, 86), (-55, 86), (-55, 6), (-2.5, 6)], 2.4, 'paving', 0.038, False))
    PLAZAS.append((-10.0, 55.0, -2.5, 65.0, 'paving', 0.043, True))
    PLAZAS.append((PLAY[0], PLAY[1], PLAY[2], PLAY[3], 'rubber_blue', 0.035, True))


setup_paths()


def dist_polyline(x, y, pts):
    best = 1e9
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a, float), np.array(b, float)
        d = b - a
        L2 = d @ d
        t = np.clip(((x - a[0]) * d[0] + (y - a[1]) * d[1]) / max(L2, 1e-9), 0, 1)
        best = min(best, float(np.hypot(x - (a[0] + d[0] * t), y - (a[1] + d[1] * t))))
    return best


def path_clearance(x, y):
    """distance from (x, y) to the nearest path/plaza edge (negative = on a path)"""
    best = 1e9
    for name, pts, w, mat, zo, curb in PATHS:
        best = min(best, dist_polyline(x, y, pts) - w / 2)
    for cx, cy, r, mat, zo in DISCS:
        best = min(best, float(np.hypot(x - cx, y - cy)) - r)
    for x0, y0, x1, y1, mat, zo, curb in PLAZAS:
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        inside = (x0 <= x <= x1) and (y0 <= y <= y1)
        d = -min(x - x0, x1 - x, y - y0, y1 - y) if inside else float(np.hypot(dx, dy))
        best = min(best, d)
    return best


def surf_z(x, y):
    """height an object placed at (x, y) should stand on (ground or raised path)"""
    z = float(hfield(x, y))
    if path_clearance(x, y) < -0.05 and z > -0.2:
        z += 0.045
    return z


def build_paths(Mp):
    """paths, plazas, curbs into mesh Mp (park coordinates)"""
    zf = lambda x, y: float(hfield(x, y))
    for name, pts, w, mat, zo, curb in PATHS:
        closed = name == 'ring'
        gx.ribbon(Mp, pts, w, zf, m(mat), tile=2.0 if mat == 'paving' else 1.6, zoff=zo, step=1.2 if closed else 2.0,
                  edge_mat=m('curb') if curb else None, edge_w=0.28 if curb else 0.0, edge_h=0.07)
        if not closed:
            for p in pts[1:-1]:
                gx.disc(Mp, p, w / 2, zo, m(mat), n=20, tile=2.0, zfn=lambda x, y: float(hfield(x, y)))
    for cx, cy, r, mat, zo in DISCS:
        gx.disc(Mp, (cx, cy), r, zo, m(mat), n=64, tile=2.0, zfn=lambda x, y: float(hfield(x, y)))
    for x0, y0, x1, y1, mat, zo, curb in PLAZAS:
        P = [(x0, y0, zo), (x1, y0, zo), (x1, y1, zo), (x0, y1, zo)]
        # split into 2 m cells so the polygon follows nothing but is well sampled for baking
        xs = np.arange(x0, x1 + 1e-6, 2.0)
        ys = np.arange(y0, y1 + 1e-6, 2.0)
        if xs[-1] < x1 - 1e-6:
            xs = np.append(xs, x1)
        if ys[-1] < y1 - 1e-6:
            ys = np.append(ys, y1)
        for a, b in zip(xs[:-1], xs[1:]):
            for c, d in zip(ys[:-1], ys[1:]):
                Mp.poly([(a, c, zo), (b, c, zo), (b, d, zo), (a, d, zo)], m(mat), hint=(0, 0, 1), tile=2.0 if mat == 'paving' else 3.0)
        if mat == 'rubber_blue':          # orange hopscotch-like accents
            for cx, cy, rx, ry in ((32.0, 70.0, 3.2, 2.6), (44.0, 63.0, 3.6, 2.2), (46.0, 76.0, 2.4, 2.4)):
                th = np.linspace(0, TAU, 29)
                ring = [(cx + rx * np.cos(a), cy + ry * np.sin(a), zo + 0.004) for a in th[:-1]]
                Mp.poly(ring, m('rubber_orange'), hint=(0, 0, 1), tile=2.0)
        if curb:
            ch = 0.10
            for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                if mat == 'rubber_blue' and a == (x0, y0) and b == (x1, y0):
                    # entrance gap on the south side (x 34..38)
                    for (u0, u1) in ((x0, 34.0), (38.0, x1)):
                        Mp.box((u0, y0 - 0.12, zo - 0.02), (u1, y0 + 0.12, zo + ch), m('curb'), tile=1.0)
                    continue
                a_, b_ = np.array(a), np.array(b)
                lo = np.minimum(a_, b_) - 0.12
                hi = np.maximum(a_, b_) + 0.12
                Mp.box((lo[0], lo[1], zo - 0.02), (hi[0], hi[1], zo + ch), m('curb'), tile=1.0)


# ---------------------------------------------------------------------------------------------------- instances
def face(fx, fy):
    return float(np.degrees(np.arctan2(-fx, fy)))


class Layout:
    def __init__(self):
        self.obj = []             # dict(m, x, y, z, rz, tag)
        self.circles = []         # exclusion circles (x, y, r)
        self.rects = []
        self.lamps = []           # (x, y, zlight)
        self.sit = []             # benches (x, y, rz)
        self.rng = np.random.default_rng(2026)
        self.trees = []

    def add(self, model, x, y, rz=0.0, z=None, tag=None, dz=0.0):
        zz = surf_z(x, y) if z is None else z
        self.obj.append(dict(m=model, x=round(float(x), 3), y=round(float(y), 3), z=round(float(zz + dz), 3), rz=round(float(rz) % 360, 2), tag=tag))

    def free(self, x, y, r, tree=False):
        for cx, cy, cr in self.circles:
            if np.hypot(x - cx, y - cy) < cr + r:
                return False
        for x0, y0, x1, y1 in self.rects:
            if x0 - r < x < x1 + r and y0 - r < y < y1 + r:
                return False
        if pond_r(x, y) < 1.12 + r / 8:
            return False
        if path_clearance(x, y) < r:
            return False
        if not (-PX + 2.5 < x < PX - 2.5 and 3.0 < y < PY1 - 2.5):
            return False
        return True


def build_layout():
    L = Layout()
    rng = L.rng
    # ------------------------------------------------------------------ entrance gate + fence
    for s in (-1, 1):
        L.add('pk_gatepost', s * 3.55, 0.0, 0.0, z=0.0)
    L.add('pk_gatearch', 0.0, 0.0, 0.0, z=0.0)
    L.add('pk_gateleaf', -3.12, 0.0, 0.0, z=0.0, tag='gateL')
    L.add('pk_gateleaf', 3.12, 0.0, 180.0, z=0.0, tag='gateR')
    # south fence (both sides of the gate), east/west/north fences; posts every 4 panels and at corners
    k = 0
    for s in (-1, 1):
        for k in range(22):
            x = s * (4.1 + 1.25 + 2.5 * k)
            L.add('pk_fence', x, 0.0, 0.0, z=0.0)
            if k % 4 == 0 and k > 0:
                L.add('pk_post', s * (4.1 + 2.5 * k), 0.0, 0.0, z=0.0)
        L.add('pk_post', s * 59.7, 0.0, 0.0, z=0.0)
        for k in range(36):
            L.add('pk_fence', s * PX, 1.25 + 2.5 * k, 90.0, z=0.0)
            if k % 4 == 0 and k > 0:
                L.add('pk_post', s * PX, 2.5 * k, 0.0, z=0.0)
        L.add('pk_post', s * PX, 90.0, 0.0, z=0.0)
    for k in range(48):
        x = -PX + 1.25 + 2.5 * k
        L.add('pk_fence', x, PY1, 0.0, z=0.0)
        if k % 4 == 0 and 0 < k:
            L.add('pk_post', -PX + 2.5 * k, PY1, 0.0, z=0.0)
    # bollards along the entrance ramp, planters / beds / boards flanking the gate
    for y in (-3.0, -7.5, -12.0):
        for s in (-1, 1):
            L.add('pk_bollard', s * 4.55, y, 0.0, dz=0.0)
    for s in (-1, 1):
        L.add('pk_planter', s * 7.4, 2.4, 0.0, z=0.0)
        L.add('pk_planter2', s * 9.2, 2.4, 0.0, z=0.0)
        L.add('pk_bed1' if s < 0 else 'pk_bed2', s * 8.5, 5.0 if False else 4.6, 0.0)
        L.add('pk_hydrant', s * 5.6, 1.6, 0.0, z=0.0)
        L.add('pk_lamp', s * 5.2, -1.2, 0.0, z=surf_z(s * 5.2, -1.2) - 0.0)
        L.lamps.append((s * 5.2, -1.2, 3.4))
    L.add('pk_board', -6.6, 4.2, 180.0)
    L.add('pk_board', 6.6, 4.2, 180.0)
    for s in (-1, 1):
        L.circles += [(s * 8.5, 4.6, 1.8)]
        L.circles += [(s * 5.6, 3.0, 1.4), (s * 7.4, 3.0, 1.4)]
    L.circles.append((0, 3.0, 4.0))
    # hedge rows inside the fence next to the gate
    for s in (-1, 1):
        for k in range(8):
            L.add('pk_hedge', s * (7.0 + 2.5 * k + 1.25 + 4.0), 1.6, 0.0, z=0.0)
    # ------------------------------------------------------------------ fountain plaza
    cx, cy = RING_C
    L.add('pk_fountain', cx, cy, 0.0, z=0.0)
    L.circles.append((cx, cy, 14.5))
    for k in range(8):
        a = np.radians(k * 45 + 22.5)
        p = (cx + 13.9 * np.cos(a), cy + 13.9 * np.sin(a))
        if not (abs(np.degrees(a) % 90 - 0) < 1):
            L.add('pk_bench', p[0], p[1], np.degrees(a) + 90)
            L.sit.append((p[0], p[1], np.degrees(a) + 90))
        q = (cx + 15.0 * np.cos(a + 0.34), cy + 15.0 * np.sin(a + 0.34))
        L.add('pk_bin', q[0], q[1], 0.0)
    for k in range(8):
        a = np.radians(k * 45)
        p = (cx + 13.6 * np.cos(a), cy + 13.6 * np.sin(a))
        if abs(np.degrees(a) - 90) < 1 or abs(np.degrees(a) - 270) < 1 or abs(np.degrees(a) - 180) < 1:   # 180 = mouth of the west path
            continue
        L.add('pk_lamp', p[0], p[1], 0.0)
        L.lamps.append((p[0], p[1], 3.5))
    for k in range(8):
        a = np.radians(k * 45 + 22.5)
        p = (cx + 17.2 * np.cos(a), cy + 17.2 * np.sin(a))
        L.add(['pk_bed1', 'pk_bed2', 'pk_bed3'][k % 3], p[0], p[1], np.degrees(a))
    L.add('pk_board', 14.6, 33.0, 220.0)
    # ------------------------------------------------------------------ gazebo + west branch
    gx_, gy_ = GAZEBO_C
    L.add('pk_gazebo', gx_, gy_, 90.0, z=0.0)
    L.circles.append((gx_, gy_, 7.0))
    for sy in (-1, 1):
        L.add('pk_planter', gx_ + 5.6, gy_ + sy * 2.6, 90.0, dz=0.0)
    L.add('pk_lamp', -22.0, 42.1, 0.0)
    L.lamps.append((-22.0, 42.1, 3.5))
    L.add('pk_lamp', -22.0, 37.9, 0.0)
    L.lamps.append((-22.0, 37.9, 3.5))
    # ------------------------------------------------------------------ kiosk + plaza
    L.add('pk_kiosk', -8.0, 60.0, 90.0, z=surf_z(-8.0, 60.0))
    L.circles.append((-7.5, 60.0, 4.0))
    L.add('pk_bin', -3.4, 56.0, 0.0)
    L.add('pk_bin', -3.4, 64.0, 0.0)
    L.add('pk_picnic', -5.2, 55.9, 0.0)
    L.add('pk_picnic', -5.2, 64.2, 0.0)
    L.add('pk_lamp', -3.0, 58.0, 0.0)
    L.lamps.append((-3.0, 58.0, 3.5))
    L.add('pk_bench', 3.5, 60.0, 270.0)
    L.sit.append((3.5, 60.0, 270.0))
    # ------------------------------------------------------------------ bridge + pond
    px_, py_ = POND_C
    L.add('pk_bridge', px_, py_, 0.0, z=0.0)
    for k in range(34):
        a = TAU * k / 34
        r = 1.04 + rng.uniform(-0.03, 0.05)
        x, y = px_ + POND_R[0] * r * np.cos(a), py_ + POND_R[1] * r * np.sin(a)
        if abs(x - px_) < 3.0 and True:
            continue
        L.add(['pk_rock1', 'pk_rock2', 'pk_rock3', 'pk_rock1', 'pk_rock2'][k % 5], x, y, rng.uniform(0, 360))
    for k in range(40):
        a = TAU * k / 40 + rng.uniform(-0.05, 0.05)
        r = rng.uniform(0.86, 0.97)
        x, y = px_ + POND_R[0] * r * np.cos(a), py_ + POND_R[1] * r * np.sin(a)
        if abs(x - px_) < 3.2:
            continue
        L.add('pk_reeds', x, y, rng.uniform(0, 360))
    for (dx_, dy_) in ((-9.0, 1.5), (7.0, -1.8), (-2.0, 3.6), (11.5, 2.2)):
        L.add('pk_lilies', px_ + dx_, py_ + dy_, rng.uniform(0, 360), z=WATER_Z)
    for i, (dx_, dy_) in enumerate(((-6.0, -2.0), (6.5, 2.0), (-12.0, 0.5))):
        L.add('pk_duck', px_ + dx_, py_ + dy_, rng.uniform(0, 360), z=WATER_Z, tag='duck')
    L.add('pk_log', 15.5, 44.5, 20.0)
    L.add('pk_stump', 14.6, 37.2, 0.0)
    L.add('pk_bench', 20.6, 30.4, 180.0)       # bench looking at the pond (north)
    L.sit.append((20.6, 30.4, 180.0))
    L.add('pk_bench', 51.6, 30.6, 180.0)
    L.sit.append((51.6, 30.6, 180.0))
    L.add('pk_bench', 26.0, 49.7, 0.0)
    L.sit.append((26.0, 49.7, 0.0))
    L.add('pk_lamp', 31.0, 26.0, 0.0)
    L.lamps.append((31.0, 26.0, 3.5))
    L.add('pk_lamp', 41.0, 50.6, 0.0)
    L.lamps.append((41.0, 50.6, 3.5))
    L.add('pk_lamp', 31.5, 51.5, 0.0)
    L.lamps.append((31.5, 51.5, 3.5))
    L.circles.append((px_, 31.0, 3.0))
    # ------------------------------------------------------------------ playground
    x0, y0, x1, y1 = PLAY
    L.rects.append((x0 - 2.5, y0 - 2.5, x1 + 2.5, y1 + 2.5))
    L.add('pk_slide', 40.0, 62.0, 0.0, dz=0.0)
    L.add('pk_swingset', 46.0, 72.0, 0.0, dz=0.0)
    L.add('pk_swing', 45.2, 72.0, 0.0, z=surf_z(46, 72) + 2.45, tag='swing')
    L.add('pk_swing', 46.8, 72.0, 0.0, z=surf_z(46, 72) + 2.45, tag='swing')
    L.add('pk_merry', 31.0, 66.0, 0.0, tag='merry')
    L.add('pk_sandbox', 31.5, 75.0, 0.0)
    L.add('pk_bench', 27.5, 59.5, 0.0)
    L.add('pk_bench', 49.5, 59.5, 0.0)
    L.sit += [(27.5, 59.5, 0.0), (49.5, 59.5, 0.0)]
    L.add('pk_bin', 24.9, 60.5, 0.0)
    L.add('pk_lamp', 34.0, 57.0, 0.0)
    L.add('pk_lamp', 38.0, 79.2, 0.0)
    L.lamps += [(34.0, 57.0, 3.5), (38.0, 79.2, 3.5)]
    # picket fence around the playground (opening on the south side x 34..38)
    for k in range(14):
        L.add('pk_picket', x0 + 1.0 + 2.0 * k, y1 + 0.5, 0.0, z=0.0 + surf_z(x0 + 1 + 2 * k, y1 + 0.5) * 0)
    for k in range(11):
        L.add('pk_picket', x1 + 0.5, y0 + 1.0 + 2.0 * k, 90.0, z=surf_z(x1 + 0.5, y0 + 1 + 2 * k))
        L.add('pk_picket', x0 - 0.5, y0 + 1.0 + 2.0 * k, 90.0, z=surf_z(x0 - 0.5, y0 + 1 + 2 * k))
    for k in range(5):
        L.add('pk_picket', x0 + 1.0 + 2.0 * k, y0 - 0.5, 0.0, z=surf_z(x0 + 1 + 2 * k, y0 - 0.5))
    for k in range(7):
        L.add('pk_picket', 39.0 + 2.0 * k, y0 - 0.5, 0.0, z=surf_z(39 + 2 * k, y0 - 0.5))
    # ------------------------------------------------------------------ lamps and benches along paths
    def along(pts, step, off, model='pk_lamp', side_alt=True, start=0.0):
        pts = [np.array(p, float) for p in pts]
        acc = start
        out = []
        for a, b in zip(pts[:-1], pts[1:]):
            d = b - a
            Lh = np.linalg.norm(d)
            u = d / Lh
            n = np.array([-u[1], u[0]])
            t = acc % step if False else acc
            s = (step - (acc % step)) % step if acc else 0.0
            while s <= Lh:
                out.append((a + u * s, n, u))
                s += step
            acc += Lh
        return out
    i = 0
    for pts, step, off in (([(0, 6), (0, 26)], 13.0, 3.1), ([(0, 54), (0, 84)], 13.0, 3.1), ([(0, 24), (36, 24)], 17.0, 2.3), ([(36, 47), (36, 58)], 11.0, 2.3),
                           ([(0, 66), (-34, 66), (-34, 44)], 17.0, 2.3), ([(2.5, 6), (55, 6), (55, 86), (-55, 86), (-55, 6), (-2.5, 6)], 19.0, 2.0)):
        for p, n, u in along(pts, step, off):
            side = 1 if (i % 2 == 0) else -1
            i += 1
            q = p + n * off * side
            if not (-PX + 1.5 < q[0] < PX - 1.5 and 2.0 < q[1] < PY1 - 1.0):
                continue
            if any(np.hypot(q[0] - lx, q[1] - ly) < 6 for lx, ly, _ in L.lamps):
                continue
            if pond_r(q[0], q[1]) < 1.2 or np.hypot(q[0] - cx, q[1] - cy) < 14.8 or path_clearance(q[0], q[1]) < 0.3:
                continue
            L.add('pk_lamp', q[0], q[1], 0.0)
            L.lamps.append((q[0], q[1], 3.5))
            if i % 3 == 0:
                q2 = p - n * (off + 0.8) * side
                if -PX + 3 < q2[0] < PX - 3 and 3 < q2[1] < PY1 - 3 and np.hypot(q2[0] - cx, q2[1] - cy) > 15.5 and pond_r(q2[0], q2[1]) > 1.25:
                    f = n * side
                    L.add('pk_bench', q2[0], q2[1], face(-f[0] * -1, -f[1] * -1) if False else face(f[0], f[1]))
                    L.sit.append((q2[0], q2[1], face(f[0], f[1])))
                    L.add('pk_bin', q2[0] + u[0] * 1.6, q2[1] + u[1] * 1.6, 0.0)
    # ------------------------------------------------------------------ props: manholes, cones, cabinet, crates...
    for (x, y, rz) in ((0.0, 14.0, 0.0), (0.0, 70.0, 0.0), (-20.0, 24.0, 0.0), (55.0, 40.0, 0.0), (-55.0, 60.0, 0.0), (0.0, -9.0, 0.0)):
        L.add('pk_manhole', x, y, rz)
    for (x, y) in ((54.0, 38.6), (54.0, 41.4), (53.0, 37.5)):
        L.add('pk_cone', x, y, 0.0)
    L.add('pk_cabinet', -57.6, 30.0, 90.0, z=0.0)
    L.add('pk_crate', -57.4, 33.0, 12.0, z=0.0)
    L.add('pk_crate', -57.5, 34.0 + 0.0, 40.0, z=0.8)
    L.add('pk_crate', -57.4, 35.1, 80.0, z=0.0)
    L.add('pk_hydrant', -2.0, 83.0, 0.0)
    L.add('pk_bikerack', 12.0, 8.5, 0.0)
    L.add('pk_bikerack', -14.0, 8.5, 0.0)
    L.add('pk_bikerack', -6.5, 67.5, 0.0)
    for (x, y) in ((54.8, 16.0), (-54.8, 74.0)):
        L.add('pk_picnic', x - (1.5 if x > 0 else -1.5), y, 90.0)
    # picnic lawn (south-east) and south-west flowers
    for (x, y, rz) in ((28.0, 12.0, 0.0), (36.0, 14.5, 90.0), (44.0, 11.0, 20.0), (-28.0, 12.0, 0.0), (-40.0, 15.0, 70.0)):
        L.add('pk_picnic', x, y, rz)
        L.circles.append((x, y, 2.4))
        L.add('pk_bin', x + 2.8, y - 1.0, 0.0)
        L.circles.append((x + 2.8, y - 1.0, 0.8))
    for (x, y, mm) in ((-20.0, 12.0, 'pk_bed3'), (-14.0, 30.0, 'pk_bed1'), (14.0, 14.0, 'pk_bed2'), (-47.0, 45.0, 'pk_bed2'), (-46.0, 70.0, 'pk_bed3'), (46.0, 31.0, 'pk_bed1'), (14.0, 70.0, 'pk_bed3'), (12.0, 56.0, 'pk_bed1')):
        if L.free(x, y, 1.6):
            L.add(mm, x, y, rng.uniform(0, 360))
            L.circles.append((x, y, 2.0))
    # ------------------------------------------------------------------ trees, bushes, tufts (rejection sampled)
    tree_types = [('pk_oak1', 5.0, 4.1), ('pk_oak2', 5.2, 4.4), ('pk_birch', 3.2, 2.6), ('pk_maple', 3.2, 2.6), ('pk_palm', 3.0, 3.6), ('pk_oak1', 5.0, 4.1)]
    weights = [2, 2, 4, 2, 1, 1]
    wsum = sum(weights)
    placed = 0
    attempts = 0
    while placed < 74 and attempts < 6000:
        attempts += 1
        x = rng.uniform(-PX + 4, PX - 4)
        y = rng.uniform(5, PY1 - 3)
        # more trees towards the borders and the north / west
        edge = min(PX - abs(x), y, PY1 - y)
        if rng.random() > 0.35 + 0.65 * np.exp(-edge / 20.0):
            continue
        t = rng.random() * wsum
        k = 0
        while t > weights[k]:
            t -= weights[k]
            k += 1
        name, rr, cr = tree_types[k]
        if name == 'pk_palm' and not (pond_r(x, y) < 1.9 or y < 22):
            continue
        if not L.free(x, y, 1.6 + 0.0):
            continue
        if any(np.hypot(x - tx, y - ty) < 5.4 for tx, ty, _ in L.trees):
            continue
        if any(np.hypot(x - lx, y - ly) < 2.2 for lx, ly, _ in L.lamps):
            continue
        L.add(name, x, y, rng.uniform(0, 360), dz=0.0)
        L.trees.append((x, y, cr))
        placed += 1
    # bushes
    placed = 0
    attempts = 0
    while placed < 95 and attempts < 8000:
        attempts += 1
        x = rng.uniform(-PX + 3, PX - 3)
        y = rng.uniform(4, PY1 - 2)
        edge = min(PX - abs(x), y, PY1 - y)
        near_tree = min([np.hypot(x - tx, y - ty) for tx, ty, _ in L.trees] + [99])
        if not (edge < 9 or near_tree < 5.0) and rng.random() > 0.25:
            continue
        if not L.free(x, y, 1.1):
            continue
        if any(np.hypot(x - bx['x'], y - bx['y']) < 2.4 for bx in L.obj if bx['m'].startswith('pk_bush')):
            continue
        if near_tree < 1.7:
            continue
        L.add(['pk_bush1', 'pk_bush2', 'pk_bush3'][rng.integers(3)], x, y, rng.uniform(0, 360))
        placed += 1
    # grass tufts and a few more small stones
    placed = 0
    attempts = 0
    while placed < 150 and attempts < 6000:
        attempts += 1
        x = rng.uniform(-PX + 2, PX - 2)
        y = rng.uniform(3, PY1 - 1)
        if not L.free(x, y, 0.9):
            continue
        L.add('pk_tuft', x, y, rng.uniform(0, 360))
        placed += 1
    for k in range(10):
        x, y = rng.uniform(-PX + 5, PX - 5), rng.uniform(8, PY1 - 5)
        if L.free(x, y, 1.8):
            L.add(['pk_rock1', 'pk_rock2'][k % 2], x, y, rng.uniform(0, 360))
    for k in range(3):
        x, y = rng.uniform(-PX + 6, -PX + 18), rng.uniform(8, PY1 - 8)
        if L.free(x, y, 1.0):
            L.add('pk_stump', x, y, 0.0)
    return L


def tree_shadow_fn(trees):
    T = np.array([(tx, ty, cr) for tx, ty, cr in trees], float) if trees else np.zeros((0, 3))

    def f(P, N, strength=0.40):
        k = np.ones(len(P))
        for tx, ty, cr in T:
            d = np.hypot(P[:, 0] - tx, P[:, 1] - ty) / (cr * 1.15)
            k *= 1 - strength * np.clip(1 - d, 0, 1) ** 0.8 * (P[:, 2] < 0.3)
        return k
    return f


def lamp_pool(P, lamps, rad=7.5, col=(1.0, 0.72, 0.38), k=0.62):
    out = np.zeros((len(P), 3))
    for lx, ly, lz in lamps:
        d = np.sqrt((P[:, 0] - lx) ** 2 + (P[:, 1] - ly) ** 2 + (P[:, 2] - 0.0 - 0.0) ** 2)
        d3 = np.sqrt((P[:, 0] - lx) ** 2 + (P[:, 1] - ly) ** 2 + (np.maximum(lz - P[:, 2], 0.3)) ** 2)
        att = np.clip(1 - np.hypot(P[:, 0] - lx, P[:, 1] - ly) / rad, 0, 1) ** 1.7
        out += (att * k)[:, None] * np.array(col)
    return out
