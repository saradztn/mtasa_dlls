# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# layout.py - places every model of District Zero (city frame: origin = centre of the central park, x east, y north).
#   * 8 building lots (two rows of facades facing the two long streets, a 20 m overgrown courtyard in the middle)
#   * abandoned traffic on the roadways, lamps / signals / signs / hydrants / benches along the sidewalks
#   * barricades, rubble, containers, billboards, power poles + wires
#   * the central park: lake with pier, fountain plaza, paths with benches and lamps, gazebo, playground, obelisk,
#     dense trees, bushes, tall grass
# All randomness is seeded (deterministic output).  Result: Layout(obj=[{m,x,y,z,rz,tag}], lamps, points)
# -----------------------------------------------------------------------------
import numpy as np
from . import city as CT
from . import assets_bld as AB

LOT_Z = 0.10
ST = CT.STREETS


class Layout:
    def __init__(self):
        self.obj = []
        self.lamps = []
        self.points = {}
        self.fp = []          # building footprints (x0, y0, x1, y1)
        self.solid = []       # circles (x, y, r) of big things trees must avoid

    def add(self, m, x, y, z=None, rz=0.0, tag=None):
        if z is None:
            z = float(CT.surface_z(x, y)[0])
        self.obj.append(dict(m=m if m.startswith('af_') else 'af_' + m, x=float(x), y=float(y), z=float(z), rz=float(rz) % 360.0, tag=tag))


def _cls(x, y):
    return int(CT.classify(np.array([[x]]), np.array([[y]]))[0][0, 0])


def _in_rect(x, y, r, m=0.0):
    return r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m


# ------------------------------------------------------------------------------------------------ buildings
LOTS = {}
for _i, (_a, _b) in enumerate(CT.BLOCKS):
    for _j, (_c, _d) in enumerate(CT.BLOCKS):
        if (_i, _j) != (1, 1):
            LOTS[(_i, _j)] = (_a, _c, _b, _d)       # x0, y0, x1, y1

POOL_TALL = ['tower_a', 'tower_b', 'hotel', 'apt_a', 'office_low']
POOL_MID = ['apt_a', 'apt_b', 'apt_c', 'office_low', 'hotel']
POOL_LOW = ['shop_a', 'shop_b', 'apt_c', 'kiosk']
SIZES = {'tower_a': (26, 24), 'tower_b': (22, 30), 'apt_a': (40, 18), 'apt_b': (32, 20), 'apt_c': (28, 18), 'shop_a': (36, 14),
         'shop_b': (28, 14), 'hotel': (30, 22), 'kiosk': (9, 6), 'office_low': (34, 20)}
# (lot) -> two rows [(side, [names])]  side: S N W E = the street the facades look at
PLAN = {
    (0, 0): [('S', ['tower_a', 'shop_a']), ('N', ['apt_b', 'shop_b'])],
    (1, 0): [('S', ['apt_c', 'hotel', 'shop_b']), ('N', ['office_low', 'shop_a', 'kiosk'])],
    (2, 0): [('S', ['shop_a', 'tower_b']), ('N', ['apt_a', 'apt_c'])],
    (0, 1): [('W', ['hotel', 'apt_b', 'shop_b', 'kiosk']), ('E', ['apt_a', 'tower_a', 'shop_b'])],
    (2, 1): [('W', ['apt_c', 'office_low', 'shop_a']), ('E', ['tower_b', 'apt_b', 'kiosk', 'shop_b'])],
    (0, 2): [('S', ['apt_a', 'kiosk', 'shop_b']), ('N', ['hotel', 'shop_a'])],
    (1, 2): [('S', ['shop_a', 'apt_b', 'tower_a']), ('N', ['apt_c', 'apt_a', 'kiosk'])],
    (2, 2): [('S', ['office_low', 'apt_c', 'kiosk']), ('N', ['tower_a', 'shop_b'])],
}


def place_buildings(L, rng):
    for lot, rows in PLAN.items():
        x0, y0, x1, y1 = LOTS[lot]
        for side, names in rows:
            span = (x1 - x0) if side in 'SN' else (y1 - y0)
            tot = sum(SIZES[n][0] for n in names)
            gap = (span - 4.0 - tot) / max(1, len(names))
            gap = float(np.clip(gap, 1.5, 6.0))
            cur = 2.0 + rng.uniform(0, max(0.0, span - 4.0 - tot - gap * (len(names) - 1)) * 0.5)
            for n in names:
                W, D = SIZES[n]
                inset = 2.5 + rng.uniform(0, 1.5)
                along = cur + W / 2
                cur += W + gap
                if side == 'S':
                    cx, cy, rz = x0 + along, y0 + inset + D / 2, 0.0
                elif side == 'N':
                    cx, cy, rz = x0 + along, y1 - inset - D / 2, 180.0
                elif side == 'W':
                    cx, cy, rz = x0 + inset + D / 2, y0 + along, 270.0
                else:
                    cx, cy, rz = x1 - inset - D / 2, y0 + along, 90.0
                if along + W / 2 > span - 0.5:
                    continue
                c, s = np.cos(np.radians(rz)), np.sin(np.radians(rz))
                ox = cx - (c * W / 2 - s * D / 2)
                oy = cy - (s * W / 2 + c * D / 2)
                hx, hy = (W / 2, D / 2) if rz in (0.0, 180.0) else (D / 2, W / 2)
                fp = (cx - hx, cy - hy, cx + hx, cy + hy)
                L.fp.append(fp)
                L.solid.append((cx, cy, max(hx, hy) * 1.3))
                L.add('af_' + n, ox, oy, LOT_Z - 0.02, rz, 'bld')
                L.add('af_' + n + '_v', ox, oy, LOT_Z - 0.02, rz, 'veg')


def free_of_buildings(L, x, y, m=2.0):
    return not any(_in_rect(x, y, f, m) for f in L.fp)


# ------------------------------------------------------------------------------------------------ roads
def road_segments():
    """(axis, centre, a, b): the straight roadway pieces between intersections"""
    segs = []
    for c in ST:
        for k in range(3):
            a, b = ST[k] + 10.0, ST[k + 1] - 10.0
            segs.append(('ns', c, a, b))
            segs.append(('ew', c, a, b))
    return segs


CAR_W = [('car_sedan_a', 3), ('car_sedan_b', 3), ('car_sedan_c', 2), ('car_hatch_a', 3), ('car_hatch_b', 2), ('car_suv_a', 2), ('car_suv_b', 2),
         ('car_van_a', 1.5), ('car_van_b', 1.5), ('car_pickup_a', 2), ('car_pickup_b', 1.5), ('car_taxi', 1.5), ('car_bus', 0.5), ('car_lorry', 0.6)]
CAR_LEN = {'car_bus': 11.4, 'car_lorry': 7.6}


def place_cars(L, rng):
    names = [n for n, w in CAR_W]
    prob = np.array([w for n, w in CAR_W], float)
    prob /= prob.sum()
    placed = []

    def ok(x, y, r):
        return all((x - px) ** 2 + (y - py) ** 2 > (r + pr) ** 2 for px, py, pr in placed)
    n_target = 0
    for axis, c, a, b in road_segments():
        length = b - a
        n = int(length / 11.5)
        for _ in range(n * 3):
            if n_target >= n * 1:
                pass
            t = rng.uniform(a + 2, b - 2)
            kind = rng.random()
            if kind < 0.45:
                off = rng.choice([-1, 1]) * 4.55
                yaw = rng.choice([0, 180]) + rng.normal(0, 2.5)
            elif kind < 0.85:
                lane = rng.choice([-1, 1])
                off = lane * rng.uniform(2.6, 3.4)
                yaw = (0 if lane > 0 else 180) + rng.normal(0, 4.0)
            else:
                off = rng.uniform(-3.5, 3.5)
                yaw = rng.choice([0, 180]) + rng.uniform(-28, 28)
            name = str(rng.choice(names, p=prob))
            if axis == 'ns':
                x, y, rz = c + off, t, yaw
            else:
                x, y, rz = t, c + off, yaw + 90
            r = max(2.6, CAR_LEN.get(name, 4.9) / 2 + 0.3)
            if not ok(x, y, r) or abs(CT.road_dz(np.array([x]), np.array([y]))[0]) > 0.12:
                continue
            placed.append((x, y, r))
            z = float(CT.surface_z(x, y)[0])
            L.add(name, x, y, z - 0.02, rz, 'car')
            n_target += 1
            if sum(1 for p in placed if abs((p[1] if axis == 'ns' else p[0]) - t) < length) > n * 0.8 and rng.random() < 0.0:
                break
    # pile-ups inside a few intersections
    for (ix, iy) in ((-70, -70), (70, 70), (-160, 70), (70, -160), (-70, 160), (160, -70)):
        for k in range(3):
            x, y = ix + rng.uniform(-6, 6), iy + rng.uniform(-6, 6)
            nm = str(rng.choice(names[:12]))
            if ok(x, y, 2.8):
                placed.append((x, y, 2.8))
                L.add(nm, x, y, float(CT.surface_z(x, y)[0]) - 0.02, rng.uniform(0, 360), 'car')
    return placed


def sidewalk_props(L, rng):
    def crossing(t):          # near an intersection?
        return min(abs(t - s) for s in ST) < 12.5
    lamp_pos = []
    for c in ST:
        for side in (-1, 1):
            t = -160.0 + 14.0 + rng.uniform(0, 8)
            while t < 150:
                if not crossing(t):
                    for axis in ('ns', 'ew'):
                        off = side * 8.2
                        r = rng.random()
                        nm = 'lamp_a' if r < 0.62 else ('lamp_b' if r < 0.74 else ('lamp_d' if r < 0.86 else 'lamp_c'))
                        if axis == 'ns':
                            x, y = c + off, t
                            rz = 180.0 if side > 0 else 0.0
                        else:
                            x, y = t, c + off
                            rz = 270.0 if side > 0 else 90.0
                        if nm == 'lamp_c':
                            rz = rng.uniform(0, 360)
                        if abs(x) <= CT.HALF - 2 and abs(y) <= CT.HALF - 2:
                            L.add(nm, x, y, None, rz, 'lamp')
                            lamp_pos.append((x, y, 8.0))
                t += 29.0 + rng.uniform(-4, 4)
    L.lamps = [p for p in lamp_pos if rng.random() < 0.25]
    # intersections: signals, stop signs, street signs, hydrants
    for sx in ST:
        for sy in ST:
            for (qx, qy) in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                x, y = sx + qx * 8.8, sy + qy * 8.8
                if abs(x) > CT.HALF - 2 or abs(y) > CT.HALF - 2:
                    continue
                if qx * qy > 0:
                    L.add('tlight_a' if rng.random() < 0.6 else 'tlight_b', x, y, None, 180.0 if qy > 0 else 0.0, 'sig')
                else:
                    L.add('sign_stop' if rng.random() < 0.7 else 'sign_stop_b', x, y, None, rng.choice([0, 90, 180, 270]), 'sign')
                    if rng.random() < 0.5:
                        L.add('sign_street', x + qx * 0.9, y, None, rng.choice([0, 90]), 'sign')
    # mid block furniture
    for axis, c, a, b in road_segments():
        for side in (-1, 1):
            n = int((b - a) / 22)
            for _ in range(n):
                t = rng.uniform(a + 4, b - 4)
                off = side * rng.uniform(8.9, 9.5)
                x, y = (c + off, t) if axis == 'ns' else (t, c + off)
                if abs(x) > CT.HALF - 3 or abs(y) > CT.HALF - 3 or _cls(x, y) != CT.WALK:
                    continue
                facing = (180.0 if side > 0 else 0.0) if axis == 'ns' else (270.0 if side > 0 else 90.0)
                r = rng.random()
                if r < 0.20:
                    L.add('hydrant', x, y, None, rng.uniform(0, 360), 'prop')
                elif r < 0.38:
                    L.add('trashcan', x, y, None, rng.uniform(0, 360), 'prop')
                elif r < 0.52:
                    L.add('bench_s', x, y, None, facing + 90, 'prop')
                elif r < 0.64:
                    L.add('dumpster', x, y, None, facing + 90 + rng.choice([0, 180]), 'prop')
                elif r < 0.72:
                    L.add('barrel', x, y, None, rng.uniform(0, 360), 'prop')
                elif r < 0.80:
                    L.add('crates', x, y, None, rng.uniform(0, 360), 'prop')
                elif r < 0.85:
                    L.add('busstop', x, y, None, facing + 90 + 90, 'prop')
                else:
                    L.add('sapling', x, y, None, rng.uniform(0, 360), 'veg')
    # power poles + wires along two streets
    for c in (-160.0, 70.0):
        for k in range(0, 10):
            y = -150.0 + k * 30.0
            if abs(y - 70.0) < 12 or abs(y + 70.0) < 12 or abs(y - 160.0) < 12 or abs(y + 160.0) < 12:
                continue
            L.add('pole_a' if k % 2 else 'pole_b', c + 9.5, y, None, 0.0, 'pole')


def blockades(L, rng):
    """military / civilian cordons across a few roadways"""
    for (c, t, ax) in ((-70.0, -112.0, 'ns'), (70.0, 112.0, 'ns'), (-112.0, 160.0, 'ew'), (112.0, -160.0, 'ew')):
        for k in range(-5, 6):
            off = k * 1.15
            if abs(off) > 5.8:
                continue
            nm = 'jersey_a' if rng.random() < 0.8 else 'barricade'
            if ax == 'ns':
                L.add(nm, c + off * 1.0, t + rng.normal(0, 0.25), None, 90.0 + rng.normal(0, 5), 'block')
            else:
                L.add(nm, t + rng.normal(0, 0.25), c + off, None, rng.normal(0, 5), 'block')
        for k in range(3):
            if ax == 'ns':
                L.add('barrel', c + rng.uniform(-5, 5), t + rng.uniform(-4, 4) - 3, None, 0, 'prop')
            else:
                L.add('crates', t + rng.uniform(-4, 4) - 3, c + rng.uniform(-5, 5), None, rng.uniform(0, 360), 'prop')
    # rubble on the roadway
    for (x, y, nm) in ((-70, -22, 'rubble_b'), (70, 41, 'rubble_a'), (22, -160, 'rubble_b'), (-160, 75, 'rubble_c'), (-70, 128, 'rubble_b'),
                       (48, 70, 'rubble_a'), (-100, -70, 'rubble_c'), (70, -110, 'rubble_a'), (160, 20, 'rubble_c'), (-31, 70, 'rubble_a')):
        L.add(nm, x, y, float(CT.surface_z(x, y)[0]) - 0.1, rng.uniform(0, 360), 'rubble')


# ------------------------------------------------------------------------------------------------ lots
def lot_yards(L, rng):
    for lot, (x0, y0, x1, y1) in LOTS.items():
        # courtyard objects
        for _ in range(60):
            x, y = rng.uniform(x0 + 3, x1 - 3), rng.uniform(y0 + 3, y1 - 3)
            if not free_of_buildings(L, x, y, 1.0):
                continue
            r = rng.random()
            if r < 0.14:
                L.add('rubble_' + rng.choice(['a', 'b', 'c']), x, y, None, rng.uniform(0, 360), 'rubble')
            elif r < 0.22:
                L.add('dumpster', x, y, None, rng.uniform(0, 360), 'prop')
            elif r < 0.30:
                L.add('container', x, y, None, rng.choice([0, 90]) + rng.normal(0, 4), 'prop')
            elif r < 0.34:
                L.add('container_stack', x, y, None, rng.choice([0, 90]), 'prop')
            elif r < 0.48:
                L.add(rng.choice(['car_sedan_a', 'car_van_a', 'car_pickup_a', 'car_suv_b', 'car_hatch_a']), x, y, None, rng.uniform(0, 360), 'car')
            elif r < 0.62:
                L.add(rng.choice(['tree_dead_a', 'tree_dead_b', 'tree_c', 'tree_a']), x, y, None, rng.uniform(0, 360), 'tree')
                L.solid.append((x, y, 3.0))
            elif r < 0.74:
                L.add(rng.choice(['bush_a', 'bush_b', 'bush_dead']), x, y, None, rng.uniform(0, 360), 'veg')
            elif r < 0.80:
                L.add('barrel', x, y, None, rng.uniform(0, 360), 'prop')
            elif r < 0.84:
                L.add('crates', x, y, None, rng.uniform(0, 360), 'prop')
            else:
                L.add(rng.choice(['weeds_b', 'grass_tall', 'ivy_mound', 'weeds_a']), x, y, None, rng.uniform(0, 360), 'veg')
        # alleys between buildings + weed fringe
        for _ in range(55):
            x, y = rng.uniform(x0 + 1, x1 - 1), rng.uniform(y0 + 1, y1 - 1)
            if free_of_buildings(L, x, y, 0.8):
                L.add(rng.choice(['weeds_a', 'weeds_b', 'grass_tall', 'bush_a']), x, y, None, rng.uniform(0, 360), 'veg')
    # billboards + a gas canopy
    L.add('billboard', -60.0, -146.0, None, 0.0, 'prop')
    L.add('billboard', 146.0, 60.0, None, 90.0, 'prop')
    L.add('gas_canopy', 112.0, -128.0, None, 0.0, 'prop')


def street_vegetation(L, rng):
    """weeds, saplings and grass tufts pushing through cracks (road edges, sidewalks, intersections)"""
    for axis, c, a, b in road_segments():
        for _ in range(int((b - a) * 0.22)):
            t = rng.uniform(a, b)
            edge = rng.random() < 0.8
            off = rng.choice([-1, 1]) * rng.uniform(5.6, 6.3) if edge else rng.uniform(-5, 5)
            x, y = (c + off, t) if axis == 'ns' else (t, c + off)
            if abs(x) > CT.HALF - 2 or abs(y) > CT.HALF - 2:
                continue
            L.add('weeds_a' if (not edge or rng.random() < 0.7) else 'weeds_b', x, y, float(CT.surface_z(x, y)[0]) - 0.03, rng.uniform(0, 360), 'veg')
        for _ in range(int((b - a) / 16)):
            t = rng.uniform(a, b)
            off = rng.choice([-1, 1]) * rng.uniform(7.0, 9.7)
            x, y = (c + off, t) if axis == 'ns' else (t, c + off)
            if abs(x) > CT.HALF - 3 or abs(y) > CT.HALF - 3:
                continue
            L.add(rng.choice(['sapling', 'bush_a', 'ivy_mound']), x, y, None, rng.uniform(0, 360), 'veg')


# ------------------------------------------------------------------------------------------------ park
def place_park(L, rng):
    cx, cy = CT.LAKE_C
    fx, fy = CT.FOUNTAIN
    L.add('fountain', fx, fy, None, 0.0, 'park')
    L.add('gazebo', 40.0, 32.0, None, 20.0, 'park')
    L.add('playground', -30.0, -38.0, None, 90.0, 'park')
    L.add('pier', cx, cy - 22.5, -1.0, 0.0, 'park')
    L.add('obelisk', CT.OBELISK_PLAZA[0], CT.OBELISK_PLAZA[1], None, 0.0, 'park')
    L.add('billboard', -58.0, 0.0, None, 270.0, 'prop') if False else None
    L.points.update(spawn=(0.0, -62.0, 1.0), plaza=(fx, fy + 12.0, 1.0), lake=(cx, cy - 18.0, 1.0), pier=(cx, cy - 22.5, 1.0), gazebo=(40.0, 25.0, 1.0),
                    street=(-70.0, -140.0, 1.0), tower=(-120.0, -100.0, 1.0))
    # ring path: benches facing the lake + lamps
    ring = CT._ring(0.95, 72)
    for i in range(3, 72, 6):
        x, y = ring[i]
        ang = np.arctan2(y - cy, x - cx)
        bx, by = x + np.cos(ang) * 2.5, y + np.sin(ang) * 2.5
        L.add('bench_p', bx, by, None, np.degrees(ang) - 90 + 180 + rng.normal(0, 8), 'park')
    for i in range(0, 72, 9):
        x, y = ring[i]
        ang = np.arctan2(y - cy, x - cx)
        L.add('lamp_a' if rng.random() < 0.6 else 'lamp_b', x - np.cos(ang) * 2.4, y - np.sin(ang) * 2.4, None, np.degrees(ang) + (0 if rng.random() < 0.5 else 0), 'lamp')
    for (x, y) in ((6.0, -52.0), (-6.0, -52.0), (-12.0, -34.0), (-8.0, 55.0), (-8.0, 40.0), (-52.0, 10.0), (50.0, 10.0)):
        L.add('bench_p', x, y, None, rng.choice([0, 90, 180, 270]) + rng.normal(0, 6), 'park')
    # trees: dense belt along the park edge, scattered elsewhere; none on paths / lake / plaza
    pts = []
    tries = 0
    while len(pts) < 150 and tries < 4000:
        tries += 1
        x, y = rng.uniform(-57, 57), rng.uniform(-57, 57)
        q = np.hypot((x - cx) / CT.LAKE_R[0], (y - cy) / CT.LAKE_R[1])
        if q < 0.82 or _cls(x, y) != CT.PARKG:
            continue
        if np.hypot(x - fx, y - fy) < 14 or np.hypot(x - 40, y - 32) < 8 or np.hypot(x + 30, y + 38) < 10:
            continue
        edge = 60 - max(abs(x), abs(y))
        if rng.random() > (0.95 if edge < 12 else 0.55):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < 6.0 ** 2 for px, py in pts):
            continue
        pts.append((x, y))
        r = rng.random()
        nm = 'tree_big' if (r < 0.10 and edge > 10) else ('tree_a' if r < 0.34 else ('tree_b' if r < 0.58 else ('tree_c' if r < 0.74 else ('tree_dead_a' if r < 0.84 else ('tree_dead_b' if r < 0.93 else 'sapling')))))
        L.add(nm, x, y, None, rng.uniform(0, 360), 'tree')
    # understory: bushes, tall grass, weeds, ivy mounds
    n = 0
    tries = 0
    while n < 330 and tries < 8000:
        tries += 1
        x, y = rng.uniform(-59, 59), rng.uniform(-59, 59)
        q = np.hypot((x - cx) / CT.LAKE_R[0], (y - cy) / CT.LAKE_R[1])
        k = _cls(x, y)
        if k not in (CT.PARKG, CT.PATH) or q < 0.70:
            continue
        if k == CT.PATH and rng.random() > 0.25:
            continue
        if np.hypot(x - fx, y - fy) < 8:
            continue
        r = rng.random()
        if q < 1.0 and r < 0.35:
            nm = 'grass_tall'              # reeds at the shore
        elif r < 0.30:
            nm = rng.choice(['bush_a', 'bush_b', 'bush_dead'])
        elif r < 0.65:
            nm = rng.choice(['grass_tall', 'weeds_b', 'weeds_a'])
        elif r < 0.75:
            nm = 'ivy_mound'
        else:
            nm = rng.choice(['weeds_a', 'weeds_b'])
        L.add(nm, x, y, None, rng.uniform(0, 360), 'veg')
        n += 1
    # park litter: fallen lamp, rubble on the plaza, a wrecked car on the path, a tent camp
    L.add('car_van_b', 0.0, -57.0, None, 82.0, 'car')
    L.add('rubble_c', 6.0, -33.0, None, 40.0, 'rubble')
    L.add('barrel', 3.0, -30.0, None, 0.0, 'prop')
    L.add('crates', -34.0, -33.0, None, 25.0, 'prop')
    L.add('container', 46.0, -46.0, None, 70.0, 'prop')


def build_layout():
    rng = np.random.default_rng(20261002)
    L = Layout()
    place_buildings(L, rng)
    place_cars(L, rng)
    sidewalk_props(L, rng)
    blockades(L, rng)
    lot_yards(L, rng)
    street_vegetation(L, rng)
    place_park(L, rng)
    # wires between pole pairs on the pole streets
    for c in (-160.0, 70.0):
        for k in range(0, 9):
            y = -150.0 + k * 30.0
            y2 = y + 30.0
            if any(abs(yy - s) < 12 for yy in (y, y2) for s in ST):
                continue
            L.add('wires30_b' if k % 4 == 1 else 'wires30', c + 9.5, y, 9.2, 90.0, 'wire')
    return L
