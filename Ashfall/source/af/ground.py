# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# ground.py - the terrain of the district as 4x4 model tiles (85 m).  A 1 m cell grid is classified (road / sidewalk /
#   crosswalk / lot / park ...) by city.py; every cell has its own corner heights (flat classes are merged into long
#   rectangles), vertical skirts (curbs, retaining edges) are emitted wherever neighbouring cells do not meet, and the
#   collision is the very same triangle mesh with a surface id per triangle.
# -----------------------------------------------------------------------------
import numpy as np
from . import city as CT
from .mb import Mesh
from .tex import IDX

N = 340
X0 = -170.0
TILE = 85.0
SURF = {CT.ROAD_NS: 1, CT.ROAD_EW: 1, CT.INTER: 1, CT.CROSS_NS: 1, CT.CROSS_EW: 1, CT.WALK: 4, CT.LOT: 10, CT.PARKG: 10, CT.OUT: 4}
SURF_SKIRT = 4


def _grids():
    cx = X0 + np.arange(N) + 0.5
    X, Y = np.meshgrid(cx, cx)                       # [iy, ix]
    cls, dx, dy, kx, ky = CT.classify(X, Y)
    vx = X0 + np.arange(N + 1)
    VX, VY = np.meshgrid(vx, vx)
    z = [np.empty((N, N)) for _ in range(4)]        # z00 z10 z01 z11 (corner order: (0,0) (1,0) (0,1) (1,1))
    nrm = [np.empty((N, N, 3)) for _ in range(4)]
    for k in np.unique(cls):
        Hk = CT.corner_heights(int(k), VX, VY)
        gy, gx_ = np.gradient(Hk, 1.0)
        nk = np.stack([-gx_, -gy, np.ones_like(Hk)], -1)
        nk /= np.linalg.norm(nk, axis=-1, keepdims=True)
        m = cls == k
        for ci, (ox, oy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
            zz = Hk[oy:oy + N, ox:ox + N]
            z[ci][m] = zz[m]
            nn = nk[oy:oy + N, ox:ox + N]
            nrm[ci][m] = nn[m]
    return cls, kx, ky, z, nrm


def _uv(k, x, y, kx, ky):
    """uv of world point(s) for class k"""
    if k == CT.ROAD_NS:
        return (x - CT.STREETS[kx]) / 12.0 + 0.5, y / 12.0
    if k == CT.ROAD_EW:
        return (y - CT.STREETS[ky]) / 12.0 + 0.5, x / 12.0
    if k == CT.INTER:
        return x / 6.0, y / 6.0
    if k == CT.CROSS_NS:
        return x / 4.0, y / 4.0
    if k == CT.CROSS_EW:
        return y / 4.0, x / 4.0
    if k == CT.WALK:
        return x / 3.0, y / 3.0
    return x / 5.0, y / 5.0


def _mat(k):
    return {CT.ROAD_NS: 'road', CT.ROAD_EW: 'road', CT.INTER: 'asphalt', CT.CROSS_NS: 'crosswalk', CT.CROSS_EW: 'crosswalk',
            CT.WALK: 'sidewalk', CT.LOT: 'grass', CT.PARKG: 'grass', CT.OUT: 'concrete'}[k]


def build_tiles(maxrun=10 ** 6):
    cls, kx, ky, z, nrm = _grids()
    pad = np.pad(cls, 1, constant_values=CT.OUT)
    # per cell height of the neighbours' shared edges, evaluated from the neighbour's own arrays
    tiles = {}
    nt = int(round(N / TILE))
    for ty in range(nt):
        for tx in range(nt):
            i0, i1 = int(tx * TILE), int((tx + 1) * TILE)
            j0, j1 = int(ty * TILE), int((ty + 1) * TILE)
            vis = {}       # mat name -> (P, NRM, UV, T)
            P_col, F_col, S_col = [], [], []

            def emit(mat, pts, nr, uvs):
                d = vis.setdefault(mat, ([], [], [], []))
                base = sum(len(a) for a in d[0])
                d[0].append(np.array(pts, float))
                d[1].append(np.array(nr, float))
                d[2].append(np.array(uvs, float))
                # diagonal choice: split along the shorter height difference
                zz = [p[2] for p in pts]
                if abs(zz[0] - zz[2]) <= abs(zz[1] - zz[3]):
                    d[3].append(np.array([[0, 1, 2], [0, 2, 3]]) + base)
                else:
                    d[3].append(np.array([[0, 1, 3], [1, 2, 3]]) + base)

            def collide(pts, surf):
                b = len(P_col)
                P_col.extend(pts)
                zz = [p[2] for p in pts]
                if abs(zz[0] - zz[2]) <= abs(zz[1] - zz[3]):
                    F_col.extend([[b, b + 1, b + 2], [b, b + 2, b + 3]])
                else:
                    F_col.extend([[b, b + 1, b + 3], [b + 1, b + 2, b + 3]])
                S_col.extend([surf, surf])

            for j in range(j0, j1):
                i = i0
                while i < i1:
                    k = int(cls[j, i])
                    if k == CT.OUT:
                        i += 1
                        continue
                    flat = (z[0][j, i] == z[1][j, i] == z[2][j, i] == z[3][j, i])
                    # merge run along x
                    e = i + 1
                    if flat:
                        while e < i1 and e - i < maxrun and cls[j, e] == k and z[0][j, e] == z[0][j, i] and z[1][j, e] == z[0][j, i] == z[2][j, e] == z[3][j, e] \
                                and kx[j, e] == kx[j, i] and ky[j, e] == ky[j, i]:
                            e += 1
                    xa, xb = X0 + i, X0 + e
                    ya, yb = X0 + j, X0 + j + 1
                    za = [z[0][j, i], z[1][j, e - 1], z[3][j, e - 1], z[2][j, i]]
                    pts = [(xa, ya, za[0]), (xb, ya, za[1]), (xb, yb, za[2]), (xa, yb, za[3])]
                    nr = [nrm[0][j, i], nrm[1][j, e - 1], nrm[3][j, e - 1], nrm[2][j, i]]
                    uu = [_uv(k, p[0], p[1], kx[j, i], ky[j, i]) for p in pts]
                    emit(_mat(k), pts, nr, uu)
                    collide(pts, SURF[k])
                    i = e
            # skirts: compare each cell with its east and north neighbour (and the tile's west / south neighbour once)
            def skirt(a0, a1, b0, b1, p0, p1, nvec, mat):
                """shared edge p0->p1 (xy); heights (a0,a1) on the cell side, (b0,b1) on the neighbour side"""
                lo0, hi0 = min(a0, b0), max(a0, b0)
                lo1, hi1 = min(a1, b1), max(a1, b1)
                if max(hi0 - lo0, hi1 - lo1) < 0.012:
                    return
                pts = [(p0[0], p0[1], lo0), (p1[0], p1[1], lo1), (p1[0], p1[1], hi1), (p0[0], p0[1], hi0)]
                L = np.hypot(p1[0] - p0[0], p1[1] - p0[1])
                tt = (p0[0] + p0[1]) * (1 if abs(p1[0] - p0[0]) > 0 else 1)
                uu = [(p0[0] / 2 + p0[1] / 2, -lo0 / 0.5), (p1[0] / 2 + p1[1] / 2, -lo1 / 0.5), (p1[0] / 2 + p1[1] / 2, -hi1 / 0.5), (p0[0] / 2 + p0[1] / 2, -hi0 / 0.5)]
                # orient the quad so the visible side faces the lower cell
                n3 = np.array([nvec[0], nvec[1], 0.0])
                geo = np.cross(np.array(pts[1]) - np.array(pts[0]), np.array(pts[2]) - np.array(pts[0]))
                order = [0, 1, 2, 3] if np.dot(geo, n3) > 0 else [0, 3, 2, 1]
                pts2 = [pts[q] for q in order]
                uu2 = [uu[q] for q in order]
                emit(mat, pts2, [n3] * 4, uu2)
                collide(pts2, SURF_SKIRT)
            for j in range(j0, j1):
                for i in range(i0, i1):
                    k = int(cls[j, i])
                    ke = int(pad[j + 1, i + 2])
                    kn = int(pad[j + 2, i + 1])
                    x1, y1 = X0 + i + 1, X0 + j + 1
                    if k != CT.OUT or ke != CT.OUT:
                        # east edge: cell (i,j) right edge vs neighbour (i+1,j) left edge
                        if i + 1 < N:
                            b0, b1 = z[0][j, i + 1], z[2][j, i + 1]
                        else:
                            b0 = b1 = CT.Z_OUT
                        a0, a1 = (z[1][j, i], z[3][j, i]) if k != CT.OUT else (CT.Z_OUT, CT.Z_OUT)
                        if k == CT.OUT:
                            a0, a1 = CT.Z_OUT, CT.Z_OUT
                        if ke == CT.OUT:
                            b0 = b1 = CT.Z_OUT
                        # direction of the visible face = towards the lower side
                        low_is_cell = (a0 + a1) < (b0 + b1)
                        nvec = (1, 0) if not low_is_cell else (-1, 0)
                        nvec = (-nvec[0], -nvec[1]) if False else nvec
                        mat = 'curb' if ((k == CT.WALK) != (ke == CT.WALK) and k != CT.OUT and ke != CT.OUT) else ('concrete' if CT.OUT in (k, ke) else 'dirt')
                        # visible normal must point to the lower side: neighbour is east, so lower neighbour => +x
                        nvec = (1, 0) if (b0 + b1) < (a0 + a1) else (-1, 0)
                        skirt(a0, a1, b0, b1, (x1, y1 - 1), (x1, y1), nvec, mat)
                    if k != CT.OUT or kn != CT.OUT:
                        if j + 1 < N:
                            b0, b1 = z[0][j + 1, i], z[1][j + 1, i]
                        else:
                            b0 = b1 = CT.Z_OUT
                        a0, a1 = (z[2][j, i], z[3][j, i]) if k != CT.OUT else (CT.Z_OUT, CT.Z_OUT)
                        if kn == CT.OUT:
                            b0 = b1 = CT.Z_OUT
                        mat = 'curb' if ((k == CT.WALK) != (kn == CT.WALK) and k != CT.OUT and kn != CT.OUT) else ('concrete' if CT.OUT in (k, kn) else 'dirt')
                        nvec = (0, 1) if (b0 + b1) < (a0 + a1) else (0, -1)
                        skirt(a0, a1, b0, b1, (x1 - 1, y1), (x1, y1), nvec, mat)
            # west edge of the tile at the map border (cells with i0 == 0) and south edge
            if tx == 0:
                for j in range(j0, j1):
                    k = int(cls[j, 0])
                    if k != CT.OUT:
                        skirt(z[0][j, 0], z[2][j, 0], CT.Z_OUT, CT.Z_OUT, (X0, X0 + j), (X0, X0 + j + 1), (-1, 0), 'concrete')
            if ty == 0:
                for i in range(i0, i1):
                    k = int(cls[0, i])
                    if k != CT.OUT:
                        skirt(z[0][0, i], z[1][0, i], CT.Z_OUT, CT.Z_OUT, (X0 + i, X0), (X0 + i + 1, X0), (0, -1), 'concrete')
            M = Mesh()
            for mat, (pp, nn, uu, tt) in vis.items():
                M.add(np.concatenate(pp), np.concatenate(nn), np.concatenate(uu), np.concatenate(tt), IDX['af_' + mat])
            tiles[(tx, ty)] = dict(M=M, faces=(np.array(P_col, float), np.array(F_col, np.int64), np.array(S_col, np.int64)),
                                   org=(X0 + (tx + 0.5) * TILE, X0 + (ty + 0.5) * TILE, 0.0))
    return tiles
