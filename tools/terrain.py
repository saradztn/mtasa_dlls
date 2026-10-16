"""Landscape: plateau (inside the moat revetment), moat bed, outer heightfield with hills,
river, coast; road network with grade-limited profiles and switchbacks; masonry revetment
and counterscarp; river bridges; trees and road lamps. Tiles are 120 m squares."""
from __future__ import annotations
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, box as sbox, Point, LineString
from fortlib import Mesh, Collision
import layout as L
import props as P

TILE = 120.0; EXT = 480.0; CELL = 4.0
G, W = L.G, L.W
MOAT_BED = W - 3.0
NGON = 12


def gon(apo, n=NGON, rot=0.0):
    """Regular polygon with edge normals at multiples of 360/n (+rot), apothem `apo`."""
    R_ = apo / math.cos(math.pi / n)
    return Polygon([(R_ * math.cos(math.radians(rot + 180 / n + 360 * k / n)), R_ * math.sin(math.radians(rot + 180 / n + 360 * k / n))) for k in range(n)])


def pa(x, y):
    """12-gon 'apothem distance' (edge normals at multiples of 30 deg)."""
    return max(x * math.cos(math.radians(30 * k)) + y * math.sin(math.radians(30 * k)) for k in range(12))


PALACE_RECT = (-64.0, -16.0, 64.0, 64.0)
PLATEAU = gon(L.APO_REV).difference(sbox(*PALACE_RECT))
MOAT = gon(L.APO_MOAT_OUT).difference(gon(L.APO_REV))
OUTER = sbox(-EXT, -EXT, EXT, EXT).difference(gon(L.APO_MOAT_OUT))
REGIONS = (('plateau', PLATEAU), ('moat', MOAT), ('outer', OUTER))
for _nm, _pg in REGIONS: shapely.prepare(_pg)

# ------------------------------------------------------------------ natural terrain
HILLS = [((-318.0, -238.0), 95.0, G + 22.0 - (W + 6.0)), ((310.0, 300.0), 80.0, 16.0), ((-360.0, 230.0), 90.0, 12.0),
         ((180.0, -380.0), 70.0, 9.0), ((-160.0, 360.0), 60.0, 7.0), ((390.0, -120.0), 60.0, 8.0)]
BELVEDERE = (-318.0, -238.0)
RIVER = [(520.0, 430.0), (380.0, 330.0), (290.0, 200.0), (262.0, 60.0), (268.0, -90.0), (300.0, -220.0), (380.0, -330.0), (520.0, -440.0)]
RIVER_LINE = LineString(RIVER)
RIVER_HW = 9.0; RIVER_BANK = 22.0


def _noise(x, y):
    return (math.sin(x * .021 + 1.3) * math.cos(y * .017 - .7) * 1.6 + math.sin(x * .053 + y * .041) * .7 + math.cos(x * .011 - y * .013) * 1.2)


def smoothstep(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)


def h_natural(x, y):
    d = pa(x, y) - L.APO_MOAT_OUT
    low = W + 6.0 + _noise(x, y)
    h = G - .5 + (low - (G - .5)) * smoothstep((d - 18.0) / 150.0)
    for (cx, cy), rad, amp in HILLS:
        r2 = ((x - cx) ** 2 + (y - cy) ** 2) / rad ** 2
        h += amp * math.exp(-r2 * 1.6) if r2 < 9 else 0.0
    # coast: drop under the sea plane towards the map edge
    edge = max(abs(x), abs(y))
    h += (W - 6.0 - h) * smoothstep((edge - 420.0) / 55.0)
    return h


def river_dist(x, y):
    return RIVER_LINE.distance(Point(x, y))


def h_river(x, y, h):
    dr = river_dist(x, y)
    if dr >= RIVER_BANK: return h
    bed = W - 2.6
    if dr <= RIVER_HW: return bed
    t = smoothstep((dr - RIVER_HW) / (RIVER_BANK - RIVER_HW))
    return bed + (min(h, W + 7.0) - bed) * t if t < 1 else h


# ------------------------------------------------------------------ roads
def arc_pts(c, r0, r1, a0, a1, step=6.0):
    n = max(2, int(abs(a1 - a0) * math.pi / 180 * max(r0, r1) / step))
    return [(c[0] + (r0 + (r1 - r0) * k / n) * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             c[1] + (r0 + (r1 - r0) * k / n) * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def _belvedere_path():
    c = BELVEDERE; pts = [(-170.0, -300.0), (-215.0, -296.0)]
    legs = [(118, 96, -10, -75), (96, 74, -75, 10), (74, 52, 10, -75), (52, 30, -75, 0), (30, 16, 0, -40)]
    for (r0, r1, a0, a1) in legs:
        pts += arc_pts(c, r0, r1, a0, a1)
    return pts


ROADS = {  # id: (points, width, texture, fixed start z, lamps)
    'main':      ([(0.0, -197.0), (0.0, -232.0), (0.0, -262.0), (4.0, -290.0), (0.0, -310.0)], 9.0, 'rf_cobble', G, True),
    'east':      ([(0.0, -310.0), (60.0, -322.0), (150.0, -318.0), (240.0, -272.0), (300.0, -250.0), (380.0, -246.0), (412.0, -247.0)], 8.0, 'rf_cobble', None, True),
    'west':      ([(0.0, -310.0), (-60.0, -312.0), (-120.0, -306.0), (-170.0, -300.0)], 7.0, 'rf_cobble', None, True),
    'belvedere': (_belvedere_path(), 6.0, 'rf_gravel', None, True),
    'service':   ([(197.0, 0.0), (225.0, 2.0), (262.0, 0.0), (300.0, -4.0), (380.0, 10.0), (412.0, 12.0)], 7.0, 'rf_cobble', G, True),
    'ring':      ([(212.0, -4.0), (214.0, -60.0), (196.0, -130.0), (150.0, -196.0), (80.0, -232.0), (30.0, -244.0), (5.0, -247.0)], 6.0, 'rf_gravel', None, False),
    'north':     ([(0.0, 214.0), (-60.0, 236.0), (-140.0, 250.0), (-230.0, 236.0), (-330.0, 236.0), (-412.0, 240.0)], 6.0, 'rf_gravel', None, False),
}
CHECKPOINTS = [('main', (0.0, -268.0)), ('service', (226.0, 2.0)), ('east', (404.0, -247.0)), ('service', (404.0, 11.5)), ('north', (-404.0, 240.0))]


def resample(pts, step=2.0):
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; L_ = math.hypot(dx, dy); n = max(1, int(L_ / step))
        out += [(a[0] + dx * k / n, a[1] + dy * k / n) for k in range(1, n + 1)]
    return out


ROAD_DATA = {}


def build_road_profiles(max_grade=.085):
    for rid, (pts, w, tex, z0, lamps) in ROADS.items():
        s = resample(pts, 2.0); n = len(s)
        zn = np.array([h_river(x, y, h_natural(x, y)) for x, y in s])
        dr = np.array([river_dist(x, y) for x, y in s])
        bridge = dr < RIVER_HW + 7.0
        zs = zn.copy()
        # across the river use the bank heights (deck spans the channel)
        if bridge.any():
            idx = np.where(bridge)[0]
            for grp in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
                a, b = max(0, grp[0] - 1), min(n - 1, grp[-1] + 1)
                za = max(zn[a], W + 4.0); zb = max(zn[b], W + 4.0)
                zs[grp] = np.linspace(za, zb, len(grp) + 2)[1:-1]
        k = 15; pad = np.pad(zs, k, mode='edge'); zs = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), 'valid')
        if z0 is not None: zs[0] = z0
        for rid2, data in ROAD_DATA.items():      # junctions: start at the parent road's height
            d = [math.hypot(s[0][0] - x, s[0][1] - y) for x, y in data['pts']]
            j = int(np.argmin(d))
            if d[j] < 6.0 and z0 is None: zs[0] = data['z'][j]
        g = max_grade * 2.0
        for i in range(1, n): zs[i] = min(max(zs[i], zs[i - 1] - g), zs[i - 1] + g)
        if z0 is None:
            for i in range(n - 2, -1, -1): zs[i] = min(max(zs[i], zs[i + 1] - g), zs[i + 1] + g)
            zs[0] = zs[0]
        zs = np.maximum(zs, np.where(bridge, W + 4.0, W + 1.0))
        ROAD_DATA[rid] = {'pts': s, 'z': zs.tolist(), 'w': w, 'tex': tex, 'bridge': bridge.tolist(), 'lamps': lamps}
    return ROAD_DATA


def road_influence(x, y):
    """(road z, weight) of the closest road whose corridor covers (x,y) - used to flatten terrain."""
    best = None
    for rid, d in ROAD_DATA.items():
        pts = d['_np'] if '_np' in d else d.setdefault('_np', np.asarray(d['pts']))
        dd = np.hypot(pts[:, 0] - x, pts[:, 1] - y); i = int(np.argmin(dd)); dist = dd[i]
        hw = d['w'] / 2
        if dist < hw + 9.0 and not d['bridge'][i]:
            wgt = 1.0 if dist < hw + 1.8 else 1.0 - smoothstep((dist - hw - 1.8) / 7.2)
            if best is None or wgt > best[1]: best = (d['z'][i] - .14, wgt)
    return best


def h_final(x, y):
    h = h_river(x, y, h_natural(x, y))
    ri = road_influence(x, y)
    if ri is not None:
        h = h + (ri[0] - h) * ri[1]
    for (bx, by), rad, zt in FLATS:
        dd = math.hypot(x - bx, y - by)
        if dd < rad + 8: h = h + (zt - h) * (1.0 if dd < rad else 1 - smoothstep((dd - rad) / 8))
    return h


FLATS = [(BELVEDERE, 15.0, None)]   # filled after road profiles (summit plaza = road end height)


# ------------------------------------------------------------------ terrain tiles
def _tex_for(region, x, y, z):
    if region == 'plateau': return 'rf_grass'
    if region == 'moat': return 'rf_dirt'
    if river_dist(x, y) < RIVER_BANK - 4: return 'rf_sand' if z < W + 1.5 else 'rf_dirt'
    if z < W + 1.0: return 'rf_sand'
    return 'rf_grass'


HCACHE = {}
def H(x, y):
    k = (round(x, 3), round(y, 3))
    v = HCACHE.get(k)
    if v is None: v = HCACHE[k] = h_final(x, y)
    return v


def region_z(region, x, y):
    return G if region == 'plateau' else MOAT_BED if region == 'moat' else H(x, y)


def terrain_tile(ix, iy):
    x0 = -EXT + ix * TILE; y0 = -EXT + iy * TILE; origin = (x0 + TILE / 2, y0 + TILE / 2, L.BASE + 10.0)
    m = Mesh(); col = Collision(); n = int(TILE / CELL)
    tile_box = sbox(x0, y0, x0 + TILE, y0 + TILE)
    active = [(nm, poly) for nm, poly in REGIONS if poly.intersects(tile_box)]
    def emit(tri, region):
        pts = [(x, y, region_z(region, x, y)) for x, y in tri]
        a, b, c = [np.array(p) for p in pts]
        if np.cross(b - a, c - a)[2] < 0: pts = [pts[0], pts[2], pts[1]]
        cx = sum(p[0] for p in pts) / 3; cy = sum(p[1] for p in pts) / 3; cz = sum(p[2] for p in pts) / 3
        tex = _tex_for(region, cx, cy, cz); k = 8.0 if tex in ('rf_grass', 'rf_dirt') else 4.0
        loc = [(p[0] - origin[0], p[1] - origin[1], p[2] - origin[2]) for p in pts]
        m.poly(loc, tex, [(p[0] / k, p[1] / k) for p in pts])
        col.tri(*loc, 'grass' if tex == 'rf_grass' else 'dirt' if tex == 'rf_dirt' else 'sand')
    for i in range(n):
        for j in range(n):
            cx0 = x0 + i * CELL; cy0 = y0 + j * CELL
            cell = sbox(cx0, cy0, cx0 + CELL, cy0 + CELL)
            for nm, poly in active:
                if poly.contains(cell):
                    q = [(cx0, cy0), (cx0 + CELL, cy0), (cx0 + CELL, cy0 + CELL), (cx0, cy0 + CELL)]
                    # split along the diagonal that follows the terrain better
                    z = [region_z(nm, *p) for p in q]
                    if abs(z[0] - z[2]) <= abs(z[1] - z[3]): emit((q[0], q[1], q[2]), nm); emit((q[0], q[2], q[3]), nm)
                    else: emit((q[0], q[1], q[3]), nm); emit((q[1], q[2], q[3]), nm)
                    break
                if poly.intersects(cell):
                    part = poly.intersection(cell)
                    if part.area < 1e-4: continue
                    tris = shapely.constrained_delaunay_triangles(part)
                    for t in getattr(tris, 'geoms', [tris]):
                        if t.area < 1e-5: continue
                        emit(list(t.exterior.coords)[:3], nm)
    return m, col, origin


# ------------------------------------------------------------------ masonry: revetment / counterscarp
def ring_wall(apo, z0, z1, outward, tex='rf_stonedark', holes=(), coping=None, gaps=()):
    """Vertical 12-gon masonry face at apothem apo (outward=True: faces away from the centre).
    holes: (edge_k, s0, s1, za, zb) openings in the face; coping: (zc0, zc1) parapet block on the
    land side of the face; gaps: (edge_k, s0, s1) breaks in the coping (bridges, stairs)."""
    from rooms import rect_minus, oriented_quad
    m = Mesh(); col = Collision(); origin = (0.0, 0.0, L.BASE + 10.0); half = apo * math.tan(math.pi / 12)
    sgn = 1 if outward else -1
    for k in range(12):
        a = math.radians(30 * k); nx, ny = math.cos(a), math.sin(a); tx, ty = -ny, nx
        def Pt(ap, s, z):
            return (nx * ap + tx * s - origin[0], ny * ap + ty * s - origin[1], z - origin[2])
        hl = [(s0, s1, za, zb) for (kk, s0, s1, za, zb) in holes if kk == k]
        for (s0, s1, za, zb) in rect_minus(-half, half, z0, z1, hl):
            pts = [Pt(apo, s0, za), Pt(apo, s1, za), Pt(apo, s1, zb), Pt(apo, s0, zb)]
            oriented_quad(m, pts, np.array((nx * sgn, ny * sgn, 0.)), tex, [(s0 / 4, za / 4), (s1 / 4, za / 4), (s1 / 4, zb / 4), (s0 / 4, zb / 4)])
            col.quad(*pts, 'stone')
        for (s0, s1, za, zb) in hl:   # reveal (jambs/lintel) 1.5 m deep into the masonry
            d = -sgn * 1.5
            for (p0, p1, nrm) in (((s0, za), (s0, zb), (1, 0)), ((s1, zb), (s1, za), (-1, 0))):
                q = [Pt(apo, p0[0], p0[1]), Pt(apo, p1[0], p1[1]), Pt(apo + d, p1[0], p1[1]), Pt(apo + d, p0[0], p0[1])]
                oriented_quad(m, q, np.array((tx * nrm[0], ty * nrm[0], 0.)), tex, [(0, 0), (0, 1), (.4, 1), (.4, 0)])
            q = [Pt(apo, s0, zb), Pt(apo, s1, zb), Pt(apo + d, s1, zb), Pt(apo + d, s0, zb)]
            oriented_quad(m, q, np.array((0, 0, -1.)), tex, [(0, 0), (1, 0), (1, .4), (0, .4)])
        if coping:
            zc0, zc1 = coping; a0, a1 = (apo - .7, apo) if outward else (apo, apo + .7)
            cuts = sorted((s0, s1) for (kk, s0, s1) in gaps if kk == k)
            segs = []; cur = -half * 1.2
            for (g0, g1) in cuts: segs.append((cur, g0)); cur = g1
            segs.append((cur, half * 1.2))
            for (sa, sb) in segs:
                quad = []
                for ap in (a0, a1):
                    lim = half * ap / apo
                    quad.append((max(sa, -lim), min(sb, lim), ap))
                if quad[0][1] - quad[0][0] < .05: continue
                c4 = [Pt(a0, quad[0][0], 0)[:2], Pt(a0, quad[0][1], 0)[:2], Pt(a1, quad[1][1], 0)[:2], Pt(a1, quad[1][0], 0)[:2]]
                zz0, zz1 = zc0 - origin[2], zc1 - origin[2]
                m.poly([(x, y, zz1) for x, y in c4], 'rf_stone', [(x / 4, y / 4) for x, y in c4])
                for i in range(4):
                    (xa, ya), (xb, yb) = c4[i], c4[(i + 1) % 4]
                    if (i == 1 and quad[0][1] >= half * a0 / apo - 1e-6) or (i == 3 and quad[0][0] <= -half * a0 / apo + 1e-6): continue
                    m.poly([(xa, ya, zz0), (xb, yb, zz0), (xb, yb, zz1), (xa, ya, zz1)], 'rf_stone', [(0, 0), (1, 0), (1, .25), (0, .25)])
                    col.quad((xa, ya, zz0), (xb, yb, zz0), (xb, yb, zz1), (xa, ya, zz1), 'stone')
                col.tri((*c4[0], zz1), (*c4[1], zz1), (*c4[2], zz1)); col.tri((*c4[0], zz1), (*c4[2], zz1), (*c4[3], zz1))
    return m, col, origin


def water_stair():
    """North escape route: jetty from the tunnel portal + stone stair up the counterscarp."""
    from rooms import stair_flight, floor_rect
    zj = L.W + 1.5; y0 = L.APO_REV; yc = L.APO_MOAT_OUT
    z_top = H(30.0, yc + 1.0)
    origin = (12.0, (y0 + yc) / 2, zj)
    m = Mesh(); col = Collision()
    # timber jetty on stone piles
    m.box((-2.0 - origin[0], y0 - origin[1], -.3), (2.0 - origin[0], yc - 3.5 - origin[1], 0), 'rf_wood', 2.5)
    col.box((-2.0 - origin[0], y0 - origin[1], -.3), (2.0 - origin[0], yc - 3.5 - origin[1], 0), 'wood')
    for yy in np.arange(y0 + 2, yc - 3.5, 3.0):
        for xx in (-1.7, 1.7): m.cyl((xx - origin[0], yy - origin[1], MOAT_BED - zj), .18, zj - MOAT_BED - .3, 'rf_wood', 6, caps=False)
    # landing + flight (+x) rising along the counterscarp face
    m.box((-2.0 - origin[0], yc - 3.5 - origin[1], MOAT_BED - zj), (4.0 - origin[0], yc - origin[1], 0), 'rf_stone', 4, faces='xXyZ')
    col.box((-2.0 - origin[0], yc - 3.5 - origin[1], MOAT_BED - zj), (4.0 - origin[0], yc - origin[1], 0), 'stone')
    n = stair_flight(m, col, origin, 4.0, 4.0 + round((z_top - zj) / .175) * .30, yc - 3.5, yc, zj, z_top, 'rf_stone', 'x', 'rf_stonedark', solid_to=MOAT_BED, open_sides='y')
    x_end = 4.0 + n * .30
    m.box((x_end - origin[0], yc - 3.5 - origin[1], MOAT_BED - zj), (x_end + 3.0 - origin[0], yc - origin[1], z_top - zj), 'rf_stone', 4, faces='xXyZ')
    col.box((x_end - origin[0], yc - 3.5 - origin[1], MOAT_BED - zj), (x_end + 3.0 - origin[0], yc - origin[1], z_top - zj), 'stone')
    from rooms import railing
    railing(m, col, origin, (4.0, yc - 3.4), (x_end, yc - 3.4), zj, 1.0, 'rf_iron')
    return m, col, origin, (x_end - .2, x_end + 3.2), z_top


# ------------------------------------------------------------------ roads, lamps, bridges, trees
def road_mesh_pieces():
    """Return list of (world_mid_xy, Mesh-in-world-coords-chunk, Collision) per 40 m chunk."""
    pieces = []; lamps = []
    for rid, d in ROAD_DATA.items():
        pts = d['pts']; zs = d['z']; hw = d['w'] / 2; br = d['bridge']; tex = d['tex']
        n = len(pts); chunk = 20
        for c0 in range(0, n - 1, chunk):
            m = Mesh(); col = Collision(); mids = []
            for i in range(c0, min(n - 1, c0 + chunk)):
                if br[i] or br[i + 1]: continue
                (xa, ya), (xb, yb) = pts[i], pts[i + 1]; za, zb = zs[i], zs[i + 1]
                def nrm(k):
                    k0, k1 = max(0, k - 1), min(n - 1, k + 1)
                    dx, dy = pts[k1][0] - pts[k0][0], pts[k1][1] - pts[k0][1]; l = math.hypot(dx, dy) or 1
                    return -dy / l, dx / l
                na, nb = nrm(i), nrm(i + 1)
                A0 = (xa - na[0] * hw, ya - na[1] * hw, za); A1 = (xa + na[0] * hw, ya + na[1] * hw, za)
                B0 = (xb - nb[0] * hw, yb - nb[1] * hw, zb); B1 = (xb + nb[0] * hw, yb + nb[1] * hw, zb)
                s0 = i * 2.0; s1 = s0 + 2.0; k = 3.0 if tex == 'rf_cobble' else 4.0
                m.poly([A0, B0, B1, A1][::-1] if False else [A0, A1, B1, B0][::-1], tex, [(0, s0 / k), (d['w'] / k, s0 / k), (d['w'] / k, s1 / k), (0, s1 / k)][::-1])
                col.quad(A0, B0, B1, A1, 'paving' if tex == 'rf_cobble' else 'gravel')
                # kerb skirts (hide terrain seams)
                for (P0, P1, sg) in ((A0, B0, -1), (A1, B1, 1)):
                    dn = (na if sg < 0 else na)
                    q = [P0, P1, (P1[0], P1[1], P1[2] - .45), (P0[0], P0[1], P0[2] - .45)]
                    m.poly(q if sg > 0 else q[::-1], 'rf_stonedark', [(0, 0), (1, 0), (1, .2), (0, .2)], two_sided=False)
                mids.append((xa, ya))
                if d['lamps'] and i % 15 == 0 and i > 2:
                    side = 1 if (i // 15) % 2 else -1
                    lx, ly = xa + na[0] * (hw + .9) * side, ya + na[1] * (hw + .9) * side
                    lamps.append((lx, ly, za))
            if mids: pieces.append((mids[len(mids) // 2], m, col))
    return pieces, lamps


def bridge_spans():
    out = []
    for rid, d in ROAD_DATA.items():
        br = np.array(d['bridge']); idx = np.where(br)[0]
        if not len(idx): continue
        for grp in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            a, b = max(0, grp[0] - 1), min(len(br) - 1, grp[-1] + 1)
            out.append({'road': rid, 'a': d['pts'][a], 'b': d['pts'][b], 'za': d['z'][a], 'zb': d['z'][b], 'w': d['w']})
    return out


def stone_bridge(a, b, za, zb, w, piers=True, deck_tex='rf_cobble'):
    """Arched stone bridge in a local frame (origin = midpoint, local +y = a->b)."""
    dx, dy = b[0] - a[0], b[1] - a[1]; Ln = math.hypot(dx, dy); ang = math.degrees(math.atan2(dy, dx)) - 90
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (za + zb) / 2)
    m = Mesh(); col = Collision(); hw = w / 2 + .6; hl = Ln / 2 + 1.0
    zA = za - mid[2]; zB = zb - mid[2]
    # deck (sloped quad) + parapets
    deck = [(-w / 2, -hl, zA), (w / 2, -hl, zA), (w / 2, hl, zB), (-w / 2, hl, zB)]
    m.poly(deck, deck_tex, [(0, 0), (w / 3, 0), (w / 3, 2 * hl / 3), (0, 2 * hl / 3)]); col.quad(*deck, 'paving')
    for sx in (-1, 1):
        x0, x1 = (sx * w / 2, sx * hw) if sx > 0 else (sx * hw, sx * w / 2)
        for (za_, zb_, top) in ((zA - 1.6, zB - 1.6, False), ):
            pass
        # parapet wall
        q = lambda x, y, z: (x, y, z)
        for face_x, nx in ((x0, -1), (x1, 1)):
            pts = [(face_x, -hl, zA - 1.4), (face_x, hl, zB - 1.4), (face_x, hl, zB + 1.0), (face_x, -hl, zA + 1.0)]
            if nx > 0: pts = [pts[1], pts[0], pts[3], pts[2]]
            m.poly(pts, 'rf_stone', [(0, 0), (2 * hl / 4, 0), (2 * hl / 4, .6), (0, .6)])
        m.poly([(x0, -hl, zA + 1.0), (x1, -hl, zA + 1.0), (x1, hl, zB + 1.0), (x0, hl, zB + 1.0)], 'rf_stonedark', [(0, 0), (.2, 0), (.2, 2 * hl / 4), (0, 2 * hl / 4)])
        col.box((x0, -hl, min(zA, zB) - 1.4), (x1, hl, max(zA, zB) + 1.0), 'stone')
    # arch soffit + spandrel band under the deck
    zmin = W - 3.0 - mid[2]
    nb = max(1, int(Ln // 14) + 1); span = 2 * hl / nb
    for k in range(nb):
        y0 = -hl + k * span; y1 = y0 + span; yc = (y0 + y1) / 2; r = span / 2 - .9
        zc = zA + (zB - zA) * (yc + hl) / (2 * hl) - 1.6
        segs = 8
        for j in range(segs):
            t0 = math.pi * j / segs; t1 = math.pi * (j + 1) / segs
            p0 = (yc - r * math.cos(t0), zc - r * .8 + r * .8 * math.sin(t0) - .2); p1 = (yc - r * math.cos(t1), zc - r * .8 + r * .8 * math.sin(t1) - .2)
            m.poly([(-hw, p1[0], p1[1]), (hw, p1[0], p1[1]), (hw, p0[0], p0[1]), (-hw, p0[0], p0[1])], 'rf_stone', [(0, 0), (w / 4, 0), (w / 4, .5), (0, .5)], two_sided=True)
        if piers and k > 0:
            m.box((-hw - .3, y0 - .9, zmin), (hw + .3, y0 + .9, zc - .2), 'rf_stone', 4)
            col.box((-hw - .3, y0 - .9, zmin), (hw + .3, y0 + .9, zc - .2), 'stone')
            m.cyl((0, y0 - .9, zmin), 0.0, 0.0, 'rf_stone', 3) if False else None
    for sx in (-1, 1):
        x = sx * hw
        pts = [(x, -hl, zA - 1.6), (x, hl, zB - 1.6), (x, hl, zB - 1.4), (x, -hl, zA - 1.4)]
        if sx > 0: pts = [pts[1], pts[0], pts[3], pts[2]]
        m.poly(pts, 'rf_stonedark', [(0, 0), (1, 0), (1, .1), (0, .1)])
    return m, col, mid, ang


def tree(kind='oak', s=1.0):
    p = P.Prop()
    if kind == 'oak':
        p.m.cyl((0, 0, 0), .35 * s, 4.0 * s, 'rf_bark', 7, r2=.25 * s)
        cards = [(0, 0, 3.0 * s, 4.2 * s, 5.2 * s)] + [(1.4 * s * math.cos(a), 1.4 * s * math.sin(a), 3.6 * s, 3.0 * s, 3.6 * s) for a in (0.4, 2.5, 4.4)]
    elif kind == 'pine':
        p.m.cyl((0, 0, 0), .28 * s, 7.5 * s, 'rf_bark', 6, r2=.12 * s)
        cards = [(0, 0, 1.6 * s + k * 1.7 * s, (3.4 - k * .75) * s, 2.6 * s) for k in range(4)]
    else:   # cypress (garden)
        p.m.cyl((0, 0, 0), .18 * s, 1.0 * s, 'rf_bark', 5)
        cards = [(0, 0, .8 * s, 1.6 * s, 6.5 * s)]
    for (cx, cy, z, wd, ht) in cards:
        for a in (0, 60, 120):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            q = [(cx - ca * wd / 2, cy - sa * wd / 2, z), (cx + ca * wd / 2, cy + sa * wd / 2, z), (cx + ca * wd / 2, cy + sa * wd / 2, z + ht), (cx - ca * wd / 2, cy - sa * wd / 2, z + ht)]
            p.m.poly(q, 'rf_leaf', [(0, 0), (1, 0), (1, 1), (0, 1)], two_sided=True)
    r = .4 * s; p.c.box((-r, -r, 0), (r, r, 3.0 * s), 'wood')
    return p


def scatter_trees(seed=4242, n_try=5200):
    rng = np.random.default_rng(seed); out = []
    for _ in range(n_try):
        x, y = rng.uniform(-440, 440, 2)
        d = pa(x, y)
        if d < L.APO_MOAT_OUT + 14: continue
        z = H(x, y)
        if z < W + 1.5: continue
        if river_dist(x, y) < RIVER_BANK + 3: continue
        ri = road_influence(x, y)
        if ri is not None and ri[1] > 0.02: continue
        if math.hypot(x - BELVEDERE[0], y - BELVEDERE[1]) < 26: continue
        if any(math.hypot(x - cx, y - cy) < 14 for _, (cx, cy) in CHECKPOINTS): continue
        dens = .35 + .65 * smoothstep((d - 230) / 120)
        if rng.random() > dens * .55: continue
        # slope check
        if abs(H(x + 2, y) - H(x - 2, y)) > 2.4 or abs(H(x, y + 2) - H(x, y - 2)) > 2.4: continue
        if any((x - a) ** 2 + (y - b) ** 2 < 49 for a, b, _, _, _ in out[-60:]): continue
        kind = 'pine' if z > W + 12 or rng.random() < .35 else 'oak'
        out.append((x, y, z, kind, float(rng.uniform(.8, 1.25))))
    return out


def finalize():
    """Compute road profiles and the summit plaza; must run before H()/tiles."""
    build_road_profiles()
    bz = ROAD_DATA['belvedere']['z'][-1] + .14
    FLATS[:] = [(BELVEDERE, 15.0, bz)]
    HCACHE.clear()
    return bz


def heightfield(step=4.0):
    xs = np.arange(-EXT, EXT + .01, step)
    grid = []
    for y in xs:
        row = []
        for x in xs:
            if PLATEAU.contains(Point(x, y)) or sbox(*PALACE_RECT).contains(Point(x, y)): row.append(G)
            elif MOAT.contains(Point(x, y)): row.append(MOAT_BED)
            else: row.append(H(x, y))
        grid.append([round(v, 2) for v in row])
    return {'origin': [-EXT, -EXT], 'step': step, 'n': len(xs), 'z': grid, 'note': 'rows = y ascending, palace footprint reported at plateau level G'}
