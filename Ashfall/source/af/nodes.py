# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# nodes.py - walk-node graph of District Zero for the zombie AI (zombies.lua).
#   * a fine (0.5 m) occupancy raster is built from the city plan (roads, sidewalks, crosswalks, lots, park, paths), the lake,
#     the REAL collision shapes (boxes / prisms of every placed model, rotated into the city frame) and the building footprints
#   * a node sits on every 4 m grid point whose fine cell is free; nodes are linked to their 8 neighbours when the straight
#     segment between them is free all the way (no corner cutting); only the largest connected component is kept
#   * output: resource/Ashfall/zombie_nodes.lua  (AF_NODES, AF_FOOTPRINTS - local city frame, same as layout.lua)
# -----------------------------------------------------------------------------
import numpy as np
from . import city as CT

FINE = 0.5
CELL = 4.0
HALF = 170
WALKABLE = (CT.ROAD_NS, CT.ROAD_EW, CT.INTER, CT.CROSS_NS, CT.CROSS_EW, CT.WALK, CT.LOT, CT.PARKG, CT.PATH)
KIND = {CT.ROAD_NS: 1, CT.ROAD_EW: 1, CT.INTER: 1, CT.CROSS_NS: 1, CT.CROSS_EW: 1, CT.WALK: 2, CT.PARKG: 3, CT.PATH: 3, CT.LOT: 4}
SKIP = ('wires', 'weeds', 'grass', 'ivy', 'lamp_glow')


def _hull(pts):
    pts = sorted(set(map(tuple, np.round(pts, 4))))
    if len(pts) < 3:
        return pts
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def shapes_of(C):
    """2D convex polygons (model space) of a model's collision that a pedestrian cannot walk through"""
    out = []
    for lo, hi in C.boxes:
        if hi[2] < 0.45 or lo[2] > 1.8:
            continue
        out.append(np.array([(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])], float))
    for cc in C.prisms:
        cc = np.asarray(cc, float)
        if cc[:, 2].max() < 0.45 or cc[:, 2].min() > 1.8:
            continue
        out.append(np.array(_hull(cc[:, :2])))
    return out


def build(L, models, pad=0.7):
    n = int(2 * HALF / FINE)
    fx = -HALF + (np.arange(n) + 0.5) * FINE
    FX, FY = np.meshgrid(fx, fx)                      # [iy, ix]
    cls = CT.classify(FX, FY)[0]
    free = np.isin(cls, WALKABLE)
    # lake (+ margin) and the fountain basin
    q = np.sqrt(((FX - CT.LAKE_C[0]) / CT.LAKE_R[0]) ** 2 + ((FY - CT.LAKE_C[1]) / CT.LAKE_R[1]) ** 2)
    free &= q > 1.0
    shapes = {}
    for mo in models:
        if mo.get('C') is None or any(s in mo['name'] for s in SKIP):
            continue
        sh = shapes_of(mo['C'])
        if sh:
            shapes[mo['name']] = sh
    for o in L.obj:
        sh = shapes.get(o['m'])
        if not sh:
            continue
        c, s = np.cos(np.radians(o['rz'])), np.sin(np.radians(o['rz']))
        for poly in sh:
            P = np.stack([o['x'] + c * poly[:, 0] - s * poly[:, 1], o['y'] + s * poly[:, 0] + c * poly[:, 1]], 1)
            x0, x1 = P[:, 0].min() - pad, P[:, 0].max() + pad
            y0, y1 = P[:, 1].min() - pad, P[:, 1].max() + pad
            i0, i1 = max(int((x0 + HALF) / FINE), 0), min(int((x1 + HALF) / FINE) + 1, n)
            j0, j1 = max(int((y0 + HALF) / FINE), 0), min(int((y1 + HALF) / FINE) + 1, n)
            if i0 >= i1 or j0 >= j1:
                continue
            gx, gy = FX[j0:j1, i0:i1], FY[j0:j1, i0:i1]
            inside = np.ones(gx.shape, bool)
            m = len(P)
            area = sum(P[i, 0] * P[(i + 1) % m, 1] - P[(i + 1) % m, 0] * P[i, 1] for i in range(m))
            sgn = 1.0 if area >= 0 else -1.0
            for i in range(m):
                a, b = P[i], P[(i + 1) % m]
                e = b - a
                ln = np.hypot(*e) + 1e-9
                d = sgn * (e[0] * (gy - a[1]) - e[1] * (gx - a[0])) / ln          # signed distance to the edge line (inside > 0)
                inside &= d > -pad
            free[j0:j1, i0:i1] &= ~inside
    for (x0, y0, x1, y1) in L.fp:
        i0, i1 = int((x0 - 1.2 + HALF) / FINE), int((x1 + 1.2 + HALF) / FINE) + 1
        j0, j1 = int((y0 - 1.2 + HALF) / FINE), int((y1 + 1.2 + HALF) / FINE) + 1
        free[max(j0, 0):max(j1, 0), max(i0, 0):max(i1, 0)] = False
    # nodes
    k = int(round(CELL / FINE))
    ng = int(2 * HALF / CELL)
    gi = (np.arange(ng) * k + k // 2)
    ok = free[np.ix_(gi, gi)]                           # [jy, ix]
    idx = -np.ones((ng, ng), int)

    def seg_free(a, b):
        (ja, ia), (jb, ib) = a, b
        steps = int(max(abs(ia - ib), abs(ja - jb)) * k * 2) + 1
        t = np.linspace(0, 1, steps)
        jj = np.round((ja * k + k // 2) + t * (jb - ja) * k).astype(int)
        ii = np.round((ia * k + k // 2) + t * (ib - ia) * k).astype(int)
        return bool(free[jj, ii].all())

    # connectivity
    links = {}
    cells = [(j, i) for j in range(ng) for i in range(ng) if ok[j, i]]
    for (j, i) in cells:
        nb = []
        for dj, di in ((0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < ng and 0 <= ii < ng and ok[jj, ii]:
                if dj and di and not (ok[j, ii] and ok[jj, i]):
                    continue
                if seg_free((j, i), (jj, ii)):
                    nb.append((jj, ii))
        links[(j, i)] = nb
    # largest component
    seen, best = set(), []
    for c0 in cells:
        if c0 in seen:
            continue
        comp, st = [], [c0]
        seen.add(c0)
        while st:
            c = st.pop()
            comp.append(c)
            for d in links[c]:
                if d not in seen:
                    seen.add(d)
                    st.append(d)
        if len(comp) > len(best):
            best = comp
    keep = sorted(best)
    for t, c in enumerate(keep):
        idx[c] = t + 1
    xs = -HALF + (np.array([c[1] for c in keep]) + 0.5) * CELL
    ys = -HALF + (np.array([c[0] for c in keep]) + 0.5) * CELL
    zs = CT.surface_z(xs, ys)
    kinds = [KIND[int(cls[c[0] * k + k // 2, c[1] * k + k // 2])] for c in keep]
    nodes = []
    for t, c in enumerate(keep):
        nodes.append((float(xs[t]), float(ys[t]), float(zs[t]), kinds[t], [int(idx[d]) for d in links[c] if idx[d] > 0]))
    return nodes, free


def to_lua(nodes, fps):
    hdr = '-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource\n-- GENERATED by source/build.py (af/nodes.py) - do not edit by hand\n'
    out = [hdr + '-- zombie walk nodes, city frame (layout.lua).  node = { x, y, z, kind, { linked node indices } }   kind 1 road, 2 sidewalk, 3 park / path, 4 lot',
           'AF_NODE_CELL = %.1f' % CELL, 'AF_NODES = {']
    for x, y, z, k, nb in nodes:
        out.append('    { %.1f, %.1f, %.2f, %d, { %s } },' % (x, y, z, k, ','.join(map(str, nb))))
    out.append('}')
    out.append('-- building footprints { x0, y0, x1, y1 }: zombies cannot see through them')
    out.append('AF_FOOTPRINTS = {')
    for f in fps:
        out.append('    { %.1f, %.1f, %.1f, %.1f },' % tuple(f))
    out.append('}')
    return '\n'.join(out) + '\n'
