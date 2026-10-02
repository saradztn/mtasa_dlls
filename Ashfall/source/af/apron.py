# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# apron.py - the wasteland around District Zero.  Without it the 340 m district floats like a diorama with a visible
# edge; with it the streets run out into overgrown, rolling ground that rises into hills and a dead forest, and the
# distance fades into fog.
#   * 8 model tiles (340 m, 4 m cells) around the district, +-510 m in total; heights start at the district's outer level
#     and grow into low hills; triangle-mesh collision (the same mesh); materials grass / dirt / gravel chosen by noise
#   * place_wasteland(): trees, dead trees, saplings, bushes, weeds, tall grass, rubble and a few wrecks / barricades
# -----------------------------------------------------------------------------
import numpy as np
from . import city as CT
from .mb import Mesh
from .tex import IDX

TILE = 340.0
CELL = 4.0
HALF = 170.0
EXT = 510.0


def _sm(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def edge_dist(x, y):
    """distance outside the district square (0 on / inside it)"""
    return np.maximum(np.maximum(np.abs(x), np.abs(y)) - HALF, 0.0)


def height(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = edge_dist(x, y)
    und = 0.9 * CT._field(9101, x * 0.9, y * 0.9) + 0.35 * CT._field(9102, x * 2.6, y * 2.6)
    hills = 6.0 * _sm(40.0, 420.0, d) * (0.55 + 0.9 * CT._field(9103, x * 0.35, y * 0.35)) + 2.5 * _sm(120.0, 500.0, d) * CT._field(9104, x * 0.8, y * 0.8)
    return CT.Z_OUT + _sm(0.0, 38.0, d) * (und + 0.4) + np.maximum(hills, 0.0) * _sm(10.0, 80.0, d)


def cell_material(x, y):
    """0 grass (the dirt / dry-grass variation is a smooth vertex tint, see scene.ground_tint), 2 gravel strip at the district edge"""
    d = edge_dist(x, y)
    m = np.zeros(np.shape(x), np.int8)
    m[d < 8] = 2
    return m


def build_tiles():
    tiles = {}
    n = int(round(TILE / CELL))
    for ty in range(-1, 2):
        for tx in range(-1, 2):
            if tx == 0 and ty == 0:
                continue
            cx, cy = tx * TILE, ty * TILE
            gx = cx - TILE / 2 + CELL * np.arange(n + 1)
            gy = cy - TILE / 2 + CELL * np.arange(n + 1)
            GX, GY = np.meshgrid(gx, gy)                       # [iy, ix]
            Z = height(GX, GY)
            gyv, gxv = np.gradient(Z, CELL)
            NR = np.stack([-gxv, -gyv, np.ones_like(Z)], -1)
            NR /= np.linalg.norm(NR, axis=-1, keepdims=True)
            cm = cell_material(0.5 * (GX[:-1, :-1] + GX[1:, 1:]), 0.5 * (GY[:-1, :-1] + GY[1:, 1:]))
            org = np.array([cx, cy, 0.0])
            # collision: shared vertex grid, tile-local coordinates are produced by build.py (it subtracts org)
            Pc = np.stack([GX, GY, Z], -1).reshape(-1, 3)
            ii, jj = np.meshgrid(np.arange(n), np.arange(n))
            a = (jj * (n + 1) + ii).ravel()
            Fc = np.concatenate([np.stack([a, a + 1, a + n + 2], 1), np.stack([a, a + n + 2, a + n + 1], 1)])
            Sc = np.full(len(Fc), 10, np.int64)
            M = Mesh()
            for mi, mname in enumerate(('grass', 'dirt', 'gravel')):
                sel = np.argwhere(cm == mi)               # [j, i]
                if len(sel) == 0:
                    continue
                j, i = sel[:, 0], sel[:, 1]
                P = np.zeros((len(sel), 4, 3))
                NN = np.zeros((len(sel), 4, 3))
                for k, (di, dj) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
                    P[:, k] = np.stack([GX[j + dj, i + di], GY[j + dj, i + di], Z[j + dj, i + di]], -1)
                    NN[:, k] = NR[j + dj, i + di]
                UV = P[..., :2] / 5.0
                base = (np.arange(len(sel)) * 4)[:, None]
                T = np.concatenate([base + [0, 1, 2], base + [0, 2, 3]])
                M.add(P.reshape(-1, 3), NN.reshape(-1, 3), UV.reshape(-1, 2), T, IDX['af_' + mname])
            tiles[(20 + tx, 20 + ty)] = dict(M=M, faces=(Pc, Fc, Sc), org=tuple(org))
    return tiles


# ------------------------------------------------------------------------------------------------ props
def place_wasteland(L, rng):
    kinds = [('tree_a', 3), ('tree_b', 3), ('tree_c', 3), ('tree_big', 2), ('tree_dead_a', 2), ('tree_dead_b', 2), ('sapling', 2)]
    names = [k for k, w in kinds]
    pw = np.array([w for k, w in kinds], float)
    pw /= pw.sum()
    taken = {}

    def free(x, y, r):
        gx, gy = int(x // 8), int(y // 8)
        for ax in (-1, 0, 1):
            for ay in (-1, 0, 1):
                for (px, py, pr) in taken.get((gx + ax, gy + ay), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < (pr + r) ** 2:
                        return False
        taken.setdefault((gx, gy), []).append((x, y, r))
        return True

    n_tree = 0
    for _ in range(30000):
        x, y = rng.uniform(-EXT + 6, EXT - 6, 2)
        d = float(edge_dist(x, y))
        if d < 7.0:
            continue
        clump = CT._field(9301, x * 0.9, y * 0.9) + 0.6 * CT._field(9302, x * 0.2, y * 0.2)
        p = (0.18 + 0.82 * _sm(8.0, 160.0, d)) * np.clip(0.40 + clump, 0.04, 1.0)
        if rng.random() > p * 0.95:
            continue
        nm = names[rng.choice(len(names), p=pw)]
        r = 4.5 if nm == 'tree_big' else (3.2 if nm.startswith('tree') else 1.6)
        if not free(x, y, r):
            continue
        L.add(nm, x, y, float(height(x, y)), rng.uniform(0, 360), 'wild')
        n_tree += 1
        if n_tree >= 900:
            break
    # understorey: bushes, weeds, tall grass, dry scrub
    n_low = 0
    for _ in range(9000):
        x, y = rng.uniform(-EXT + 4, EXT - 4, 2)
        d = float(edge_dist(x, y))
        if d < 3.0:
            continue
        nm = ['weeds_a', 'weeds_b', 'grass_tall', 'bush_a', 'bush_b', 'bush_dead', 'weeds_a', 'grass_tall'][rng.integers(0, 8)]
        if not free(x, y, 0.9):
            continue
        L.add(nm, x, y, float(height(x, y)), rng.uniform(0, 360), 'wild')
        n_low += 1
        if n_low >= 1700:
            break
    # debris along the district edge: rubble heaps, barricades, a few wrecks
    for _ in range(46):
        side = int(rng.integers(0, 4))
        t = rng.uniform(-HALF, HALF)
        off = rng.uniform(6, 60)
        x, y = [(t, -HALF - off), (t, HALF + off), (-HALF - off, t), (HALF + off, t)][side]
        if not free(x, y, 3.0):
            continue
        nm = ['rubble_a', 'rubble_b', 'rubble_c', 'rubble_a', 'container', 'jersey_a', 'barricade', 'car_sedan_c', 'car_van_b', 'car_pickup_a'][int(rng.integers(0, 10))]
        L.add(nm, x, y, float(height(x, y)), rng.uniform(0, 360), 'wild')
