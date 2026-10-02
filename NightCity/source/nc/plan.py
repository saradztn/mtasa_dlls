# Created by: Arena.ai Agent Mode (AI) - NightCity MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# plan.py - the city plan: non-uniform street grid with T-junctions, dead-ends,
#           a roundabout, a diagonal boulevard, offset blocks and curves.
#           Districts, block recipes, expressways, river + bridges, sky bridges,
#           distant skyline.  Produces the model registry and the list of placements.
# City frame: origin = centre of the city, x east, y north, z = street level (0).
# Everything is deterministic.
# -----------------------------------------------------------------------------
import numpy as np
from .ground import SW, CARR, SIDE, CURB, QUAY, RIVER_Z, BED_Z, cell_dims
from . import ground, bld, infra, tunnel as TUN
from .bldkit import POD_H

# -----------------------------------------------------------------------------
# grid -- expanded to 14 x 14 blocks.  Street class letters:
#   A avenue 36 m, S street 22 m, N lane 14 m, '.' = no street (T-junction / dead-end gap)
# Edge vectors are 15-long (blocks 14 => 15 street lines).  A '.' edge means that
# road segment does not exist, producing a T-junction, dead end, or offset grid.
# -----------------------------------------------------------------------------
XB = [56, 64, 80, 56, 88, 88, 128, 88, 72, 80, 64, 56, 72, 56]                                # 14 block widths  (W -> E)
XC = ['S','N','N','A','N','A','S','A','A','S','S','N','A','S','S']                           # 15 vertical street lines (x=const)
YB = [88, 88, 104, 72, 88, 130, 72, 72, 128, 88, 72, 88, 96, 72]                             # 14 block depths (S -> N), j=5 is the river
YC = ['S','S','A','S','S','S','S','A','A','S','A','S','S','S','S']                           # 15 horizontal street lines (y=const)

RIVER_J = 5
HERO = (7, 8)

# district letters, rows j = 13 (north) ... 0 (south) (printed top = north).
# Codes:
#   C core glass     K arcology hero       P plaza gate
#   E entertainment  G neon / garage hub   B old brick quarter
#   M market / dens  R residential mega    Q residential quiet
#   W waterfront     H hospital / campus   U university / civic
#   D docks / port   I general industrial  T tank farm
#   F factory        Y container yard      O stadium / oval (park plaza)
#   ~ river
DISTRICTS = [
    "RRRRRCCCCEEEEQQ",   # 13
    "RRRRCCCEEEEBQQQ",   # 12
    "RRMMCCCCEEEBBUQ",   # 11
    "MMMMCCKCEEEBBUU",   # 10
    "MMMMCCCPCEEEEBB",   # 9
    "RMMHWWWWWWWWBII",   # 8
    "~~~~~~~~~~~~~~~",   # 7  river
    "IIWWWWWBWWWWDII",   # 6
    "IIIIIBBIIIIDDII",   # 5
    "ITTFFIIBBYYFDDI",   # 4
    "ITTFFIIBBYYFDDI",   # 3
    "IIFIIIIIIIFFIII",   # 2
    "IIIIIBIIIIIIIII",   # 1
    "IIIIIIIIIIIIIII",   # 0
]
DIST = {j: DISTRICTS[13 - j] for j in range(14)}

EXPRESS_EW = dict(line=8, level=12.0)      # E-W expressway, lower deck (runs above y-line 8)
EXPRESS_NS = dict(line=7, level=22.0)      # N-S expressway, upper deck
BRIDGE_LINES = {1: 'N', 4: 'A', 6: 'A', 8: 'S', 10: 'A', 12: 'N'}  # x lines that cross the river
HERO_BRIDGE_LINE = 6

# road tunnel (N-S under x-line 9, north of the river): extends through the larger grid
TUNNEL = dict(line=9, row_in=8, g=0.10, L_open=64.0, PT=1.2, flat_L=64.0, flat_n=5, variants=(0, 1, 2, 1, 0), start=20.0)

STYLE = {
    'C': 'core', 'K': 'core', 'P': 'core',
    'E': 'ent', 'G': 'ent',
    'M': 'market', 'B': 'market',
    'R': 'res', 'Q': 'res', 'U': 'res', 'H': 'res',
    'W': 'ent',
    'I': 'ind', 'T': 'ind', 'F': 'ind', 'Y': 'ind', 'D': 'ind',
    'O': 'ent',
    '~': 'ent',
}
PAD = {
    'C': 'nc_plaza', 'K': 'nc_plaza', 'P': 'nc_plaza',
    'E': 'nc_sidewalk', 'G': 'nc_sidewalk',
    'M': 'nc_sidewalk', 'B': 'nc_sidewalk',
    'R': 'nc_sidewalk', 'Q': 'nc_sidewalk', 'U': 'nc_sidewalk', 'H': 'nc_sidewalk',
    'W': 'nc_sidewalk',
    'I': 'nc_concrete', 'T': 'nc_concrete', 'F': 'nc_concrete', 'Y': 'nc_concrete', 'D': 'nc_concrete',
    'O': 'nc_plaza',
}

GLASSES = ['nc_glass_a', 'nc_glass_b', 'nc_glass_c', 'nc_glass_d', 'nc_glass_e', 'nc_glass_f', 'nc_glass_g', 'nc_glass_h']
LEDS = ['nc_strip_cyan', 'nc_strip_white', 'nc_light_magenta', 'nc_strip_cyan', 'nc_light_amber', 'nc_strip_white']

# Streets that do NOT continue through their cell (i.e. are closed on one side), producing
# T-junctions, dead ends, or curves.  Keyed by (i,j,'n'|'s'|'e'|'w') -> True (blocked).
# Adding a closure on a side shortens that street to end at the intersection rather than
# continuing into the cell.  The closure is mirrored into the neighbour cell's ground mesh
# automatically because neighbour cells share street mid-lines.
CLOSED = set()


class Plan:
    def __init__(self):
        self.models = {}
        self.keys = {}
        self.placements = []
        self.water = []
        self.points = {}
        self.tour = []
        self.counts = {'g': 0, 'b': 0, 'i': 0, 's': 0}

    def model(self, cat, builder, args, hint=''):
        key = (builder, tuple(sorted((k, v if not isinstance(v, (list, tuple)) else tuple(v)) for k, v in args.items())))
        if key in self.keys:
            return self.keys[key]
        self.counts[cat] += 1
        name = 'nc_%s%03d' % (cat, self.counts[cat])
        self.models[name] = dict(cat=cat, builder=builder, args=dict(args), hint=hint)
        self.keys[key] = name
        return name

    def place(self, name, x, y, z, rz, tag):
        self.placements.append(dict(model=name, x=float(x), y=float(y), z=float(z), rz=float(rz), tag=tag))


def tunnel_geom(X, Y):
    T = TUNNEL
    g, Lo, PT = T['g'], T['L_open'], T['PT']
    Lt = Lo + PT
    fl, fn = T['flat_L'], T['flat_n']
    x = X[T['line']]
    y_in = Y[T['row_in']] + T['start']
    z_floor = -g * Lt
    parts = [dict(builder='tunnel_open', args=dict(L=Lo, pt=PT, g=g), y=y_in + Lt / 2, z=-g * Lt / 2, rz=0.0)]
    y = y_in + Lt
    y_a = y
    for k in range(fn):
        parts.append(dict(builder='tunnel_tube', args=dict(L=fl, dz=0.0, variant=T['variants'][k % len(T['variants'])]), y=y + fl / 2, z=z_floor, rz=0.0))
        y += fl
    y_b = y
    parts.append(dict(builder='tunnel_open', args=dict(L=Lo, pt=PT, g=g), y=y_b + Lt / 2, z=-g * Lt / 2, rz=180.0))
    y_out = y_b + Lt
    prof = [(y_in, 0.0), (y_a, z_floor), (y_b, z_floor), (y_out, 0.0)]
    return dict(x=x, y_in=y_in, y_out=y_out, y_cov0=y_a, y_cov1=y_b, y_a=y_a, y_b=y_b, z_floor=z_floor, parts=parts, prof=prof,
                holes=[(y_in, y_in + Lo), (y_b + PT, y_out)])


def tunnel_z(tg, y):
    ys = [p[0] for p in tg['prof']]
    zs = [p[1] for p in tg['prof']]
    return float(np.interp(y, ys, zs))


def tunnel_tour(tg):
    x = tg['x']

    def at(ye, yt, sec, h=1.7, ht=1.2):
        return (x, ye, tunnel_z(tg, ye) + h, x, yt, tunnel_z(tg, yt) + ht, sec)
    yi, yo, ya, yb = tg['y_in'], tg['y_out'], tg['y_a'], tg['y_b']
    return [
        (x, yi - 70.0, 7.0, x, yi + 40.0, tunnel_z(tg, yi + 40.0) + 0.5, 5.0),
        at(yi + 25.0, yi + 125.0, 5.0),
        at(ya + 10.0, ya + 130.0, 8.0),
        at(ya + 150.0, ya + 280.0, 8.0),
        at(ya + 300.0, ya + 400.0, 6.0),
        at(yb - 40.0, yb + 60.0, 5.0),
        at(yb + 20.0, yo, 5.0),
        (x, yo + 8.0, 1.9, x, yo + 110.0, 2.6, 6.0),
    ]


def grid_lines():
    W = [XB[i] + SW[XC[i]] / 2 + SW[XC[i + 1]] / 2 for i in range(14)]
    D = [YB[j] + SW[YC[j]] / 2 + SW[YC[j + 1]] / 2 for j in range(14)]
    X = [0.0]
    for w in W:
        X.append(X[-1] + w)
    Y = [0.0]
    for d in D:
        Y.append(Y[-1] + d)
    cx = (X[0] + X[-1]) / 2
    cy = (Y[0] + Y[-1]) / 2
    X = [x - cx for x in X]
    Y = [y - cy for y in Y]
    return X, Y, W, D


# -----------------------------------------------------------------------------
# palettes -- bigger, more varied building sets per district
# -----------------------------------------------------------------------------
def _palettes():
    rng = np.random.default_rng(2077)
    towers = []
    sizes = [(36, 36), (40, 36), (44, 38), (48, 40), (40, 44), (36, 44), (44, 44), (32, 32), (52, 44), (28, 40)]
    floors = [30, 36, 42, 48, 54, 60, 68, 76, 86, 96, 104, 112]
    for k in range(48):
        w, d = sizes[k % len(sizes)]
        f = floors[(k * 3 + int(rng.integers(0, 4))) % len(floors)]
        r = rng.random()
        mat = GLASSES[(k * 5 + int(rng.integers(0, 8))) % 8]
        led = LEDS[int(rng.integers(len(LEDS)))]
        if r < 0.50:
            towers.append(('tower_setback', dict(w=w, d=d, floors=f, mat=mat, seed=int(rng.integers(1, 9999)),
                                                 crown_style=str(rng.choice(['spire', 'ring', 'prongs', 'flat', 'dish', 'ring'])),
                                                 steps=int(rng.integers(1, 4)), scale_top=float(round(rng.uniform(0.5, 0.82), 2)),
                                                 pod=int(rng.integers(1, 3)), fin=int(rng.random() < 0.4),
                                                 signs=int(rng.integers(2, 5)), led=led, octo=bool(rng.random() < 0.22))))
        elif r < 0.82:
            towers.append(('tower_cyl', dict(r=float(rng.choice([12, 13, 14, 15, 16, 17])), floors=f, mat=mat,
                                              seed=int(rng.integers(1, 9999)), ring_every=int(rng.choice([5, 6, 8, 10])),
                                              led=led, crown_style=str(rng.choice(['ring', 'spire', 'flat'])))))
        else:
            towers.append(('tower_twin', dict(w=24, d=28, floors=min(f, 68), gap=float(rng.choice([14, 16, 20, 22])),
                                              mat=mat, seed=int(rng.integers(1, 9999)), led=led)))
    mids = []
    for k in range(30):
        w, d = [(36, 36), (40, 36), (32, 40), (44, 32), (36, 28), (30, 30), (42, 34)][k % 7]
        mids.append(('midrise', dict(w=w, d=d, floors=int(rng.integers(8, 22)), mat=GLASSES[(k * 3 + 1) % 8],
                                     seed=int(rng.integers(1, 9999)), signs=int(rng.integers(2, 5)),
                                     led=LEDS[int(rng.integers(len(LEDS)))])))
    tens = []
    for k in range(24):
        w, d = [(22, 20), (26, 22), (26, 24), (24, 22), (26, 26), (20, 20), (28, 22)][k % 7]
        tens.append(('tenement', dict(w=w, d=d, floors=int(rng.integers(5, 14)),
                                      mat=['nc_wall_tenement_a', 'nc_wall_tenement_b', 'nc_wall_brutal', 'nc_wall_brick'][k % 4],
                                      seed=int(rng.integers(1, 9999)), escapes=int(rng.integers(1, 3)))))
    slabs = []
    for k in range(14):
        w, d = [(64, 18), (56, 18), (48, 16), (60, 20), (72, 20), (52, 16)][k % 6]
        slabs.append(('slab', dict(w=w, d=d, floors=int(rng.integers(12, 28)),
                                   mat=['nc_glass_b', 'nc_glass_g', 'nc_wall_brutal', 'nc_glass_h', 'nc_wall_brick'][k % 5],
                                   seed=int(rng.integers(1, 9999)))))
    megas = [('megablock', dict(w=w, d=d, floors=int(f), seed=int(rng.integers(1, 9999))))
             for (w, d, f) in ((48, 48, 30), (48, 44, 36), (52, 48, 32), (40, 40, 34), (56, 52, 28), (44, 56, 26))]
    warehouses = [('warehouse', dict(w=w, d=d, h=float(h), seed=int(rng.integers(1, 9999))))
                  for (w, d, h) in ((56, 36, 11), (60, 40, 12), (52, 34, 10), (64, 38, 13), (48, 32, 10), (72, 44, 14), (56, 48, 12))]
    return dict(towers=towers, mids=mids, tens=tens, slabs=slabs, megas=megas, warehouses=warehouses)


PAL = None


def pal():
    global PAL
    if PAL is None:
        PAL = _palettes()
    return PAL


def _footprint(arch, a):
    if arch == 'tower_setback':
        return a['w'] + 6, a['d'] + 6
    if arch == 'tower_cyl':
        return 2 * (a['r'] + 3.5), 2 * (a['r'] + 3.5)
    if arch == 'tower_twin':
        return 2 * a['w'] + a['gap'] + 6, a['d'] + 6
    if arch == 'arcology':
        return a['w'] + 8, a['w'] + 8
    if arch == 'plaza_gate':
        return a['w'], 9.0
    if arch == 'hospital':
        return a['w'] + 2, a['d'] + 2
    return a['w'], a['d']


def pick(items, bw, bd, target, rng, key=lambda it: it[1].get('floors', 0), margin=2.0, avoid=()):
    fit = [it for it in items if _footprint(it[0], it[1])[0] <= bw - margin and _footprint(it[0], it[1])[1] <= bd - margin]
    if not fit:
        fit = sorted(items, key=lambda it: _footprint(it[0], it[1])[0] * _footprint(it[0], it[1])[1])[:3]
    fit = [it for it in fit if (it[0], it[1].get('seed')) not in avoid] or fit
    fit.sort(key=lambda it: abs(key(it) - target))
    return fit[int(rng.integers(0, min(3, len(fit))))]


# -----------------------------------------------------------------------------
# T-junction / dead-end layout: which edges of which cells are "closed" so the
# street doesn't continue, producing non-axis-straight roads.
# -----------------------------------------------------------------------------
def _build_closures():
    cl = set()
    def close(i, j, side):
        cl.add((i, j, side))
        # mirror closure on the neighbour cell (the shared street edge).
        # 'n' edge of (i,j) is the south edge ('s') of (i,j+1), etc.
        nb = {'n': (i, j + 1, 's'), 's': (i, j - 1, 'n'), 'e': (i + 1, j, 'w'), 'w': (i - 1, j, 'e')}[side]
        cl.add(nb)

    # Residential / industrial cul-de-sacs and T-junctions (hand-placed to break the grid).
    # Format: (i, j, side_to_close)  -- the named side of the cell has no through road.
    closes = [
        # upper-left residential
        (0, 12, 'w'), (0, 13, 'w'),
        (1, 13, 'n'),
        (3, 12, 'e'),
        (2, 11, 'n'), (3, 11, 'n'),
        # quiet quarter top-right
        (12, 12, 'n'), (13, 12, 'n'), (13, 11, 'n'),
        (13, 10, 'e'),
        (11, 12, 'e'),
        # waterfront T-junctions (promenade)
        (2, 6, 's'), (3, 6, 's'),
        (9, 6, 's'), (10, 6, 's'),
        (5, 8, 'n'), (6, 8, 'n'),
        # industrial dead-ends / yards
        (0, 1, 's'), (0, 0, 's'), (0, 0, 'w'),
        (13, 0, 'e'), (13, 1, 'e'),
        (12, 2, 'e'),
        (5, 1, 'e'),
        (1, 3, 'w'), (0, 4, 'w'),
        # brick quarter narrow
        (11, 9, 'e'), (11, 10, 'e'),
        (12, 9, 'n'),
        # entertainment variety
        (10, 11, 'e'),
        (9, 12, 'n'),
        # campus (U) interior closes
        (12, 11, 's'),
        # extra variety: curve-like offsets
        (2, 2, 'w'),
        (7, 0, 's'),
        (6, 13, 'n'),
        (4, 12, 'n'),
        (8, 13, 'n'),
    ]
    for c in closes:
        close(*c)
    return cl


# -----------------------------------------------------------------------------
# build
# -----------------------------------------------------------------------------
def build_plan():
    global CLOSED
    CLOSED = _build_closures()
    plan = Plan()
    X, Y, W, D = grid_lines()
    rng = np.random.default_rng(31337)
    P_ = pal()
    recent = []
    cx0 = X[HERO[0]] + W[HERO[0]] / 2
    cy0 = Y[HERO[1]] + D[HERO[1]] / 2
    plan.extent = (X[0], Y[0], X[-1], Y[-1])
    tg = tunnel_geom(X, Y)
    plan.tunnel = tg
    for (hy0, hy1) in tg['holes']:
        jj = [j for j in range(14) if Y[j] < hy0 and hy1 < Y[j + 1]]
        assert len(jj) == 1, (hy0, hy1)
        j = jj[0]
        lo = Y[j] + CARR[YC[j]] / 2 + 4.0 + 1.0
        hi = Y[j + 1] - CARR[YC[j + 1]] / 2 - 4.0 - 1.0
        assert lo <= hy0 and hy1 <= hi, ('tunnel cut leaves its street', hy0, hy1, lo, hi)
    skyblocks = {}
    for j in range(14):
        for i in range(14):
            ch = DIST[j][i]
            cls = (XC[i], XC[i + 1], YC[j], YC[j + 1])
            bw, bd = XB[i], YB[j]
            cxm = X[i] + W[i] / 2
            cym = Y[j] + D[j] / 2
            style = STYLE[ch]
            bcx = cxm + (SW[cls[0]] / 2 - SW[cls[1]] / 2) / 2
            bcy = cym + (SW[cls[2]] / 2 - SW[cls[3]] / 2) / 2
            alley = None
            if ch == 'M':
                alley = ('x', 0.0, 8.0)
            elif ch == 'B':
                alley = ('y', float(rng.uniform(-bd * 0.1, bd * 0.1)), 6.0)
            spec = dict(bw=bw, bd=bd, cls=cls, style=style, pad=PAD.get(ch, 'nc_sidewalk'), alley=alley,
                        river=(ch == '~'), seed=1000 + 13 * bw + bd + 7 * (i + j * 17))
            # pass closures to the ground builder so roads terminate
            closes = tuple(s for s in ('n', 's', 'e', 'w') if (i, j, s) in CLOSED)
            if closes:
                spec['closes'] = closes
            if spec['river'] and ch != 'O':
                spec['seed'] = 3000 + bw
                gp = []
                if i in BRIDGE_LINES:
                    gp.append((-W[i] / 2, -W[i] / 2 + SW[XC[i]] / 2))
                if (i + 1) in BRIDGE_LINES:
                    gp.append((W[i] / 2 - SW[XC[i + 1]] / 2, W[i] / 2))
                spec['gaps'] = tuple((float(a), float(b)) for a, b in gp)
            if ch == 'O':
                # the roundabout island replaces water in that one river cell; mark it as non-river for ground, but still draw a short water segment
                spec['river'] = False
                spec['roundabout'] = True
            holes = []
            for (hy0, hy1) in tg['holes']:
                if Y[j] < hy0 and hy1 < Y[j + 1]:
                    if i + 1 == TUNNEL['line']:
                        holes.append(('e', round(hy0 - cym, 3), round(hy1 - cym, 3)))
                    if i == TUNNEL['line']:
                        holes.append(('w', round(hy0 - cym, 3), round(hy1 - cym, 3)))
            if holes:
                spec['holes'] = tuple(holes)
            gname = plan.model('g', 'cell', spec, hint='%s %dx%d' % (ch, bw, bd))
            plan.place(gname, cxm, cym, 0.0, 0.0, 'ground')
            if ch == '~':
                yw0 = cym + (-D[j] / 2 + CARR[cls[2]] / 2 + SIDE[cls[2]] + QUAY)
                yw1 = cym + (D[j] / 2 - CARR[cls[3]] / 2 - SIDE[cls[3]] - QUAY)
                plan.water.append((int(round(X[i] / 2.0)) * 2, int(np.floor(yw0 / 2) * 2), int(round(X[i + 1] / 2.0)) * 2, int(np.ceil(yw1 / 2) * 2), RIVER_Z))
                continue
            dist_c = np.hypot(bcx - cx0, bcy - cy0)
            rr = np.random.default_rng(int(rng.integers(1, 10**9)))
            blds = []
            if ch in 'CKP':
                if ch == 'K':
                    blds.append(('arcology', dict(w=118, floors=78, seed=77), 0.0, 0.0, 0.0))
                elif ch == 'P':
                    blds.append(('plaza_gate', dict(w=64, h=80.0, seed=5), 0.0, 0.0, 90.0))
                else:
                    target = 104 - dist_c / 13.0 + float(rr.uniform(-10, 10))
                    arch, a = pick(P_['towers'], bw, bd, target, rr, avoid=recent[-8:])
                    recent.append((arch, a.get('seed')))
                    fw, fd = _footprint(arch, a)
                    rz = 0.0 if (fw <= bw - 2 and fd <= bd - 2) else 90.0
                    blds.append((arch, a, 0.0, 0.0, rz))
            elif ch == 'E':
                r = rr.random()
                if r < 0.30:
                    arch, a = pick(P_['towers'], bw, bd, 44 + float(rr.uniform(-6, 18)), rr, avoid=recent[-8:])
                    recent.append((arch, a.get('seed')))
                    blds.append((arch, a, 0.0, 0.0, 0.0 if _footprint(arch, a)[0] <= bw - 2 and _footprint(arch, a)[1] <= bd - 2 else 90.0))
                elif r < 0.74:
                    arch, a = pick(P_['mids'], bw - 4, bd - 4, 14 + float(rr.uniform(-4, 6)), rr, avoid=recent[-4:])
                    recent.append((arch, a.get('seed')))
                    blds.append((arch, a, 0.0, 0.0, float(rr.choice([0, 90]))))
                else:
                    g = ('garage', dict(w=float(rr.choice([48, 52, 56, 60])), d=float(rr.choice([32, 36, 40])), levels=int(rr.integers(5, 10)), seed=int(rr.integers(1, 99))))
                    blds.append((g[0], g[1], 0.0, 0.0, float(rr.choice([0, 90]))))
            elif ch == 'G':
                blds.append(('garage', dict(w=56.0, d=40.0, levels=9, seed=3), 0.0, -bd * 0.2, 0.0))
                arch, a = pick(P_['mids'], bw - 4, bd * 0.4, 12, rr)
                blds.append((arch, a, 0.0, bd * 0.25, 0.0))
            elif ch == 'W':
                if rr.random() < 0.55:
                    arch, a = pick(P_['mids'], bw - 4, bd - 4, 10 + float(rr.uniform(-2, 8)), rr, avoid=recent[-4:])
                    recent.append((arch, a.get('seed')))
                    blds.append((arch, a, 0.0, 0.0, 0.0))
                else:
                    arch, a = pick(P_['slabs'], bw - 4, bd - 4, 18, rr)
                    blds.append((arch, a, 0.0, 0.0, 0.0 if bw >= bd else 90.0))
            elif ch == 'M':
                ds = (bd - 8.0) / 2.0
                for row in (-1, 1):
                    for col in (-1, 1):
                        arch, a = pick(P_['tens'], bw / 2 - 1, ds - 1.5, int(rr.integers(6, 14)), rr)
                        blds.append((arch, a, col * bw / 4.0, row * (4.0 + ds / 2.0), float(rr.choice([0, 90, 180, 270]))))
            elif ch == 'B':
                # old brick quarter: smaller, denser tenements of varied heights and rotations, with an alley
                nrows, ncols = 2, 2
                if bw > 72: ncols = 3
                if bd > 78: nrows = 3
                cw = (bw - 8.0) / ncols
                chh = (bd - 8.0) / nrows
                for rr_ in range(nrows):
                    for cc_ in range(ncols):
                        if rr.random() < 0.10:
                            continue      # leave a small gap / yard
                        arch, a = pick(P_['tens'], cw - 2, chh - 2, int(rr.integers(4, 12)), rr)
                        blds.append((arch, a,
                                     -bw / 2 + 4 + cw * (cc_ + 0.5),
                                     -bd / 2 + 4 + chh * (rr_ + 0.5),
                                     float(rr.choice([0, 90, 180, 270]))))
            elif ch == 'R':
                if rr.random() < 0.45:
                    arch, a = pick(P_['megas'], bw - 4, bd - 4, 32, rr, key=lambda it: it[1]['floors'])
                    blds.append((arch, a, 0.0, 0.0, 0.0))
                else:
                    arch, a = pick(P_['slabs'], bw - 6, bd * 0.45, 20, rr)
                    blds.append((arch, a, 0.0, -bd * 0.22, 0.0))
                    arch2, a2 = pick(P_['slabs'], bw - 6, bd * 0.45, 16, rr)
                    blds.append((arch2, a2, 0.0, bd * 0.24, 180.0))
            elif ch == 'Q':
                # quiet residential: two shorter slabs with a green gap
                arch, a = pick(P_['slabs'], bw - 8, bd * 0.36, int(rr.integers(8, 16)), rr)
                blds.append((arch, a, float(rr.uniform(-6, 6)), -bd * 0.28, float(rr.choice([0, 90]))))
                arch2, a2 = pick(P_['slabs'], bw - 8, bd * 0.36, int(rr.integers(8, 16)), rr)
                blds.append((arch2, a2, float(rr.uniform(-6, 6)), bd * 0.28, float(rr.choice([0, 90]))))
            elif ch == 'U':
                # civic/university: one midrise institutional block plus a smaller wing
                arch, a = pick(P_['mids'], bw - 8, bd * 0.5, 10, rr, avoid=recent[-4:])
                recent.append((arch, a.get('seed')))
                blds.append((arch, a, 0.0, -bd * 0.18, 0.0))
                arch2, a2 = pick(P_['mids'], bw * 0.55, bd * 0.32, 6, rr)
                blds.append((arch2, a2, bw * 0.05, bd * 0.28, float(rr.choice([0, 90]))))
            elif ch == 'H':
                # hospital: cross-shaped midrise (use a large midrise)
                arch, a = pick(P_['mids'], bw - 12, bd * 0.45, 12, rr)
                blds.append((arch, a, 0.0, -bd * 0.1, 0.0))
                arch2, a2 = pick(P_['mids'], bw * 0.3, bd - 10, 8, rr)
                blds.append((arch2, a2, 0.0, bd * 0.2, 90.0))
            elif ch == 'I':
                if rr.random() < 0.65:
                    arch, a = pick(P_['warehouses'], bw - 4, bd - 4, 11, rr, key=lambda it: it[1]['h'])
                    blds.append((arch, a, 0.0, -bd * 0.18 if bd > 70 else 0.0, 0.0))
                    if bd >= 84:
                        arch, a = pick(P_['warehouses'], bw - 4, bd * 0.4, 10, rr, key=lambda it: it[1]['h'])
                        blds.append((arch, a, 0.0, bd * 0.27, 0.0))
                else:
                    blds.append(('container_yard', dict(w=float(min(bw - 4, 80)), d=float(min(bd - 4, 60)), seed=int(rr.integers(1, 99))), 0.0, 0.0, 0.0))
            elif ch == 'T':
                blds.append(('tank_farm', dict(w=float(bw - 6), d=float(min(bd - 6, 70)), seed=int(rr.integers(1, 99))), 0.0, 0.0, 0.0))
            elif ch == 'F':
                blds.append(('factory', dict(w=float(bw - 4), d=float(min(bd - 4, 70)), seed=int(rr.integers(1, 99))), 0.0, 0.0, 0.0))
            elif ch == 'Y':
                blds.append(('container_yard', dict(w=float(bw - 4), d=float(min(bd - 4, 64)), seed=int(rr.integers(1, 99))), 0.0, 0.0, 0.0))
            elif ch == 'D':
                # docks: mix of warehouses with cranes simulated by taller stacks
                arch, a = pick(P_['warehouses'], bw - 4, bd * 0.45, 12, rr, key=lambda it: it[1]['h'])
                blds.append((arch, a, 0.0, -bd * 0.22, 0.0))
                blds.append(('container_yard', dict(w=float(min(bw - 6, 76)), d=float(min(bd * 0.40, 52)), seed=int(rr.integers(1, 99))), 0.0, bd * 0.25, 0.0))
            elif ch == 'O':
                # roundabout island: small circular plaza with a central monument (use a midrise scaled down as landmark)
                arch, a = ('tower_cyl', dict(r=8.0, floors=14, mat='nc_glass_c', seed=9001, ring_every=5, led='nc_light_magenta', crown_style='spire', pod=0))
                blds.append((arch, a, 0.0, 0.0, 0.0))
            for arch, a, dx, dy, rz in blds:
                bname = plan.model('b', arch, a, hint=arch)
                plan.place(bname, bcx + dx, bcy + dy, CURB, rz, 'bld')
                fw, fd = _footprint(arch, a)
                if rz % 180 == 90:
                    fw, fd = fd, fw
                skyblocks.setdefault((i, j), []).append((bcx + dx, bcy + dy, fw / 2, fd / 2, arch, a))
    # expressways -- over the extended grid
    ew, ns = EXPRESS_EW, EXPRESS_NS
    for i in range(14):
        L = int(round(W[i]))
        pier = True
        if i == RIVER_J:
            pier = False
        m = plan.model('i', 'expressway', dict(L=L, level=ew['level'], seed=i % 3, pier=pier, river=(i == RIVER_J)), hint='ew')
        plan.place(m, X[i] + W[i] / 2, Y[ew['line']], 0.0, 0.0, 'infra')
    for j in range(14):
        L = int(round(D[j]))
        if j == RIVER_J:
            m = plan.model('i', 'expressway', dict(L=L, level=ns['level'], seed=j % 3, pier=False, river=True), hint='ns-river')
        else:
            m = plan.model('i', 'expressway', dict(L=L, level=ns['level'], seed=j % 3, pier=True), hint='ns')
        plan.place(m, X[ns['line']], Y[j] + D[j] / 2, 0.0, 90.0, 'infra')
    # bridges
    j = RIVER_J
    span = int(round(D[j]))
    water_span = int(round(D[j] - (CARR[YC[j]] / 2 + SIDE[YC[j]] + QUAY) - (CARR[YC[j + 1]] / 2 + SIDE[YC[j + 1]] + QUAY)))
    for line, cls in BRIDGE_LINES.items():
        if line == HERO_BRIDGE_LINE:
            m = plan.model('i', 'bridge_cable', dict(span=span, water=water_span, cls='A', seed=3), hint='hero bridge')
        else:
            m = plan.model('i', 'bridge_girder', dict(span=span, water=water_span, cls=cls, seed=line), hint='bridge %s' % cls)
        plan.place(m, X[line], (Y[j] + Y[j + 1]) / 2, 0.0, 0.0, 'bridge')
    # tunnel
    for pt_ in tg['parts']:
        m = plan.model('i', pt_['builder'], pt_['args'], hint='tunnel')
        plan.place(m, tg['x'], pt_['y'], pt_['z'], pt_['rz'], 'tunnel')
    # sky bridges
    sky = []
    for (i, j), lst in skyblocks.items():
        if (i + 1, j) in skyblocks and DIST[j][i] in 'CE' and DIST[j][i + 1] in 'CE':
            for (x0, y0, hw0, hd0, a0, s0) in lst:
                for (x1, y1, hw1, hd1, a1, s1) in skyblocks[(i + 1, j)]:
                    f0, f1 = s0.get('floors', 0), s1.get('floors', 0)
                    if a0.startswith('tower') and a1.startswith('tower') and min(f0, f1) >= 40 and abs(y0 - y1) < 8:
                        gap = (x1 - hw1) - (x0 + hw0)
                        if 8 < gap < 64:
                            sky.append(((x0 + hw0 - 1.0 + x1 - hw1 + 1.0) / 2, (y0 + y1) / 2, gap + 2.0, min(f0, f1)))
    sky.sort(key=lambda s: -s[3])
    used = 0
    for (sx, sy, L, f) in sky[:6]:
        z = 40.0 + 3.8 * int(f * 0.35)
        m = plan.model('i', 'skybridge', dict(length=int(round(L)), seed=used), hint='skybridge')
        plan.place(m, sx, sy, z, 0.0, 'sky')
        used += 1
    # distant skyline strips
    x0, y0, x1, y1 = plan.extent
    lw = x1 - x0 + 600
    lh = y1 - y0 + 600
    sk = [
        ('N', 0, (x0 + x1) / 2, y1 + 180.0, 0.0, lw, 11), ('N', 1, (x0 + x1) / 2, y1 + 380.0, 0.0, lw, 12),
        ('S', 2, (x0 + x1) / 2, y0 - 180.0, 180.0, lw, 13), ('S', 3, (x0 + x1) / 2, y0 - 380.0, 180.0, lw, 14),
    ]
    ry0 = Y[RIVER_J]
    ry1 = Y[RIVER_J + 1]
    for (side, k, cx, cy, rz, L, sd) in sk:
        m = plan.model('s', 'skyline_strip', dict(L=int(L), seed=sd, rows=2), hint='skyline')
        plan.place(m, cx, cy, 0.0, rz, 'skyline')
    for (rz, xs, tagn) in ((-90.0, x1 + 180.0, 'E'), (90.0, x0 - 180.0, 'W')):
        for (a, b, sd) in ((y0 - 120, ry0 - 20, 21), (ry1 + 20, y1 + 120, 22)):
            m = plan.model('s', 'skyline_strip', dict(L=int(b - a), seed=sd + (0 if tagn == 'E' else 5), rows=2), hint='skyline')
            plan.place(m, xs, (a + b) / 2, 0.0, rz, 'skyline')
    # named points
    plan.points = dict(
        spawn=(cx0 - 0.0, cy0 - D[HERO[1]] / 2 + 12.0, CURB + 1.0),
        plaza=(cx0 - 94.0, cy0, CURB + 1.0),
        avenue=(X[5], cy0 - 220.0, 1.0),
        market=(X[2] + 4.0, Y[9] + 40.0, 1.0),
        quay=(cx0, Y[RIVER_J] + CARR[YC[RIVER_J]] / 2 + SIDE[YC[RIVER_J]] + 4.0, CURB + 1.0),
        bridge=(X[HERO_BRIDGE_LINE], (Y[RIVER_J] + Y[RIVER_J + 1]) / 2, CURB + 1.0),
        expressway=(X[3], Y[ew['line']], ew['level'] + 1.0),
        industrial=(X[9] + 60, Y[2] + 80, 1.0),
        docks=(X[11] + 40, Y[4] + 60, 1.0),
        brick=(X[11] - 30, Y[9] + 40, 1.0),
        campus=(X[12] - 30, Y[11] + 20, 1.0),
        roundabout=(X[7], (Y[RIVER_J] + Y[RIVER_J + 1]) / 2, CURB + 1.0),
        tunnel_in=(tg['x'], tg['y_in'] - 14.0, 1.0),
        tunnel_out=(tg['x'], tg['y_out'] + 14.0, 1.0),
        tunnel_mid=(tg['x'], (tg['y_a'] + tg['y_b']) / 2, tg['z_floor'] + 1.0),
    )
    yr = (Y[RIVER_J] + Y[RIVER_J + 1]) / 2
    hb = X[HERO_BRIDGE_LINE]
    plan.tour = [
        (X[11], Y[2] - 80.0, 340.0, cx0, cy0, 100.0, 14.0),
        (hb + 140.0, yr - 250.0, 80.0, hb, yr, 50.0, 12.0),
        (hb, yr - 70.0, 7.0, hb, yr + 360.0, 40.0, 14.0),
        (X[5], Y[8] + 20.0, 3.5, X[5], Y[11], 60.0, 12.0),
        (cx0 - 140.0, cy0 - 120.0, 3.0, cx0, cy0, 150.0, 12.0),
        (cx0 + 70.0, cy0 - 30.0, 40.0, cx0, cy0, 140.0, 10.0),
        (X[3], Y[ew['line']], ew['level'] + 3.0, X[10], Y[ew['line']], ew['level'] + 9.0, 14.0),
        (X[2] + 3.0, Y[9] + 6.0, 3.0, X[2] + 3.0, Y[9] + 240.0, 14.0, 14.0),
        (X[10] + 50.0, Y[9] + 30.0, 11.0, X[10] + 50.0, Y[10] + 140.0, 40.0, 10.0),
        (X[11] + 60.0, Y[4] + 20.0, 18.0, X[11] + 60.0, Y[5] - 40, 40.0, 10.0),
        (X[9] + 50.0, Y[2] + 30.0, 11.0, X[9] + 50.0, Y[3] + 160.0, 46.0, 12.0),
    ] + tunnel_tour(tg) + [
        (X[3], Y[4] - 100.0, 160.0, cx0, cy0, 40.0, 10.0),
    ]
    plan.grid = dict(X=X, Y=Y, W=W, D=D)
    plan.hero = (cx0, cy0)
    return plan
