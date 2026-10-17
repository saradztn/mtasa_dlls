"""Room furnishing: placement engine (door clearances, openings, stair zones, occupancy)
+ one recipe per room. Output per room: merged furniture Mesh/Collision in the room's
local frame (same origin as the shell), baked-light sources, flame coronas, interactive
object placements and a placement log for the manifest."""
from __future__ import annotations
import math
import numpy as np
from fortlib import Mesh, Collision
import layout as L
import rooms as R
import props as P

Y = L.PALACE_DY
EDGE_ROT = {'S': 0.0, 'N': 180.0, 'W': -90.0, 'E': 90.0}   # rotation that makes local +y face into the room


def _rot(x, y, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c


def prop_bounds(p):
    pts = []
    if p.m.v:
        mn, mx = p.m.bounds(); pts += [mn.tolist(), mx.tolist()]
    for lo, hi, _ in p.c.boxes: pts += [lo, hi]
    a = np.asarray(pts, float); return a.min(axis=0), a.max(axis=0)


def col_rotated(c, offset, deg):
    """Collision rotated by any angle: 90-degree multiples keep boxes, others become triangles."""
    if abs(deg / 90.0 - round(deg / 90.0)) < 1e-6:
        return c.transformed(offset, deg)
    out = Collision()
    def T(p):
        x, y = _rot(p[0], p[1], deg); return (x + offset[0], y + offset[1], p[2] + offset[2])
    for lo, hi, s in c.boxes:
        x0, y0, z0 = lo; x1, y1, z1 = hi
        v = [T((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        for a, b, cc, d in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
            out.quad(v[a], v[b], v[cc], v[d], s)
    out.verts += [T(p) for p in c.verts]
    base = len(out.verts) - len(c.verts); out.faces += [(a + base, b + base, cc + base, s) for a, b, cc, s in c.faces]
    return out


class Furnisher:
    def __init__(self, r, origin):
        self.r = r; self.origin = origin; self.m = Mesh(); self.c = Collision()
        self.lights = []; self.flames = []; self.interactive = []; self.log = []
        self.z0 = r['z0']; self.top = r['z0'] + r['h'] - L.SLAB
        self.inner = R.inner_rect(r) if r.get('shape', 'rect') == 'rect' else None
        self.occ = {}          # layer -> list of (x0,y0,x1,y1)
        self.blocked = {}      # layer -> list of rects that floor props may not touch
        self.block_all = False
        if self.inner is not None: self._door_clearances()

    # ------------------------------------------------------------------ geometry queries
    def edge_info(self, e):
        ix0, iy0, ix1, iy1 = self.inner
        return {'S': ('y', iy0, ix0, ix1, 1), 'N': ('y', iy1, ix0, ix1, -1), 'W': ('x', ix0, iy0, iy1, 1), 'E': ('x', ix1, iy0, iy1, -1)}[e]

    def openings(self, e):
        return R.OPENINGS.get((self.r['id'], e), [])

    def _door_clearances(self, depth=1.6):
        for e in R.EDGES:
            if R.open_edge(self.r, e):
                ax, c, a, b, sg = self.edge_info(e)
                self._add_block(0.0, ax, c, a, b, sg, depth + .4); continue
            for o in self.openings(e):
                if o['kind'] in ('extwindow', 'window'): continue
                layer = round(o['z0'] - self.z0, 1)
                if layer < .6: layer = 0.0
                ax, c, _, _, sg = self.edge_info(e)
                self._add_block(layer, ax, c, o['s0'] - .35, o['s1'] + .35, sg, depth)

    def _add_block(self, layer, ax, c, s0, s1, sg, depth):
        c2 = c + sg * depth
        rect = (s0, min(c, c2), s1, max(c, c2)) if ax == 'y' else (min(c, c2), s0, max(c, c2), s1)
        self.blocked.setdefault(layer, []).append(rect)

    def block(self, rect, layer=0.0):
        self.blocked.setdefault(layer, []).append(tuple(rect))

    def block_circle(self, c, rad, layer=0.0):
        self.block((c[0] - rad, c[1] - rad, c[0] + rad, c[1] + rad), layer)

    @staticmethod
    def _hit(a, b, m=0.0):
        return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m

    # ------------------------------------------------------------------ placement
    def put(self, p, x, y, rot=0.0, z=0.0, layer=None, overlay=False, force=False, name='', solid=True):
        """Place prop p at world (x, y), floor-relative height z. Returns True on success."""
        mn, mx = prop_bounds(p)
        cs = [_rot(cx, cy, rot) for cx in (mn[0], mx[0]) for cy in (mn[1], mx[1])]
        fp = (x + min(c[0] for c in cs), y + min(c[1] for c in cs), x + max(c[0] for c in cs), y + max(c[1] for c in cs))
        layer = round(z, 1) if layer is None else layer
        if not force:
            if self.inner is not None:
                ix0, iy0, ix1, iy1 = self.inner
                if fp[0] < ix0 - .02 or fp[1] < iy0 - .02 or fp[2] > ix1 + .02 or fp[3] > iy1 + .02: return False
            if not overlay:
                if self.block_all and layer == 0.0: return False
                if any(self._hit(fp, b) for b in self.blocked.get(layer, [])): return False
                if any(self._hit(fp, b, -.02) for b in self.occ.get(layer, [])): return False
        if not overlay and solid: self.occ.setdefault(layer, []).append(fp)
        ox, oy, oz = self.origin; off = (x - ox, y - oy, self.z0 + z - oz)
        self.m.merge(p.m, off, rot)
        if not p.c.empty(): self.c.merge(col_rotated(p.c, off, rot))
        for Lt in p.lights:
            lx, ly = _rot(Lt['pos'][0], Lt['pos'][1], rot)
            self.lights.append(dict(Lt, pos=[lx + off[0], ly + off[1], Lt['pos'][2] + off[2]]))
        for f in p.flames:
            fx, fy = _rot(f['pos'][0], f['pos'][1], rot)
            self.flames.append(dict(f, pos=[fx + x, fy + y, f['pos'][2] + self.z0 + z]))
        self.log.append({'prop': name, 'pos': [round(x, 2), round(y, 2), round(self.z0 + z, 2)], 'rot': rot})
        return True

    def wall(self, e, p, s, z=0.0, off=0.0, name='', zlo=None, zhi=None, overlay=False, layer=None):
        """Prop against inner face of edge e at abscissa s; checks openings on that wall."""
        ax, c, a, b, sg = self.edge_info(e)
        mn, mx = prop_bounds(p)
        za = self.z0 + z + (mn[2] if zlo is None else zlo); zb = self.z0 + z + (mx[2] if zhi is None else zhi)
        if s + mn[0] < a + .05 or s + mx[0] > b - .05: return False
        for o in self.openings(e):
            if o['s0'] - .25 < s + mx[0] and s + mn[0] < o['s1'] + .25 and o['z0'] - .1 < zb and za < o['z1'] + .1:
                return False
        d = c + sg * (off - mn[1])    # back of the prop touches the wall face
        x, y = (s, d) if ax == 'y' else (d, s)
        return self.put(p, x, y, EDGE_ROT[e], z, overlay=overlay, name=name, layer=layer)

    def wall_run(self, e, factory, spacing, z=0.0, margin=1.0, name='', overlay=False, layer=None, limit=99):
        ax, c, a, b, sg = self.edge_info(e); n = 0
        s = a + margin
        while s < b - margin + 1e-6 and n < limit:
            if self.wall(e, factory(), s, z, name=name, overlay=overlay, layer=layer): n += 1
            s += spacing
        return n

    def walls_run(self, edges, factory, spacing, **kw):
        return sum(self.wall_run(e, factory, spacing, **kw) for e in edges)

    def centre(self):
        ix0, iy0, ix1, iy1 = self.inner; return (ix0 + ix1) / 2, (iy0 + iy1) / 2

    def size(self):
        ix0, iy0, ix1, iy1 = self.inner; return ix1 - ix0, iy1 - iy0

    def long_axis(self):
        w, d = self.size(); return 'x' if w >= d else 'y'

    def hang(self, p, x, y, name='chandelier', drop_room=None):
        return self.put(p, x, y, 0, self.top - self.z0, overlay=True, force=True, name=name)

    def sconces(self, z=2.4, spacing=4.5, edges=R.EDGES, layer_name='sconce', limit=99):
        return self.walls_run(edges, P.sconce, spacing, z=z, margin=1.2, overlay=True, name=layer_name, limit=limit)

    def lumens(self):
        return sum(l.get('power', 1) * l['radius'] ** 2 for l in self.lights)

    def ensure_light(self, per_m2=4.0, z=2.4):
        if self.inner is None: return
        w, d = self.size()
        if self.lumens() < per_m2 * w * d:
            self.sconces(z=z, spacing=3.6)


# ====================================================================== recipe helpers
def grid_pts(F, nx, ny, mx=2.0, my=2.0, rect=None):
    ix0, iy0, ix1, iy1 = rect or F.inner
    xs = [ix0 + mx + (ix1 - ix0 - 2 * mx) * (i + .5) / nx for i in range(nx)]
    ys = [iy0 + my + (iy1 - iy0 - 2 * my) * (j + .5) / ny for j in range(ny)]
    return [(x, y) for x in xs for y in ys]


def chandeliers(F, nx=None, ny=None, drop=1.8, r=1.1, gold=True):
    w, d = F.size(); nx = nx or max(1, round(w / 9)); ny = ny or max(1, round(d / 9))
    for (x, y) in grid_pts(F, nx, ny, 0, 0):
        F.hang(P.chandelier(r, 8, min(drop, F.r['h'] - 4.4), gold), x, y)


def dining(F, cx, cy, length, axis='x', cloth='rf_fabricred', chairs=True, tw=1.2):
    if axis == 'x':
        F.put(P.table(length, tw, .78, 'rf_wood', cloth), cx, cy, 0, name='table')
        if chairs:
            for k in range(int(length // .9)):
                x = cx - length / 2 + .45 + k * .9
                F.put(P.chair(), x, cy - tw / 2 - .4, 0, name='chair'); F.put(P.chair(), x, cy + tw / 2 + .4, 180, name='chair')
    else:
        F.put(P.table(length, tw, .78, 'rf_wood', cloth), cx, cy, 90, name='table')
        if chairs:
            for k in range(int(length // .9)):
                y = cy - length / 2 + .45 + k * .9
                F.put(P.chair(), cx - tw / 2 - .4, y, -90, name='chair'); F.put(P.chair(), cx + tw / 2 + .4, y, 90, name='chair')
    for k in (-1, 1):
        o = k * length * .3
        F.put(P.candelabra(.5), cx + (o if axis == 'x' else 0), cy + (0 if axis == 'x' else o), 0, .78, overlay=True, force=True, name='candles')


def paintings(F, edges=R.EDGES, spacing=3.4, z=1.7, texs=('rf_paint1', 'rf_paint2', 'rf_paint3')):
    k = [0]
    def fac():
        k[0] += 1; return P.painting(1.3, 1.0, texs[k[0] % len(texs)])
    return F.walls_run(edges, fac, spacing, z=z, margin=1.6, overlay=True, name='painting')


def banners(F, edges, spacing=4.0, z=None, h=3.2):
    z = z if z is not None else max(1.6, F.r['h'] - L.SLAB - h - .6)
    return F.walls_run(edges, lambda: P.wall_hanging(1.4, h), spacing, z=z, margin=1.5, overlay=True, name='banner')


def shelves(F, edges, kind='books', spacing=2.2, layer=None, z=0.0, h=3.0):
    fac = (lambda: P.bookshelf(2.0, h)) if kind == 'books' else (lambda: P.shelf_items(2.0, 2.2, kind))
    return F.walls_run(edges, fac, spacing, z=z, margin=1.1, name='shelf_' + kind, layer=layer)


def rug_centre(F, tex='rf_carpetred', inset=2.5, minw=2.0):
    w, d = F.size(); cx, cy = F.centre()
    if w - 2 * inset > minw and d - 2 * inset > minw:
        F.put(P.rug(w - 2 * inset, d - 2 * inset, tex), cx, cy, 0, overlay=True, force=True, name='rug')


def sitting_group(F, cx, cy, rot=0):
    F.put(P.table(1.2, .8, .5, 'rf_wood'), cx, cy, rot, name='low table')
    for dx, dy, rr in ((0, -1.2, 0), (0, 1.2, 180), (-1.3, 0, -90), (1.3, 0, 90)):
        x, y = _rot(dx, dy, rot); F.put(P.chair(high=True), cx + x, cy + y, rr + rot, name='armchair')


def corridor(F, statues=True, art=True, bench=True):
    al = F.long_axis(); edges = ('W', 'E') if al == 'y' else ('S', 'N')
    if F.r['wall'] not in ('rf_dungeon',):
        if art: paintings(F, edges, 5.0)
    F.sconces(z=2.5, spacing=6.0, edges=edges if max(F.size()) > 7 else R.EDGES)
    if statues:
        F.walls_run(edges, lambda: P.statue('rf_whitemarble', .9, .8), 9.0, margin=4.0, name='statue')
    if bench:
        F.walls_run(edges, lambda: P.bench(1.8, 'rf_wood', 'rf_fabricred'), 9.0, margin=8.5, name='bench')
    w, d = F.size(); cx, cy = F.centre()
    if min(w, d) >= 3.0:
        F.put(P.rug(1.6, max(w, d) - 2.0, 'rf_carpetred') if al == 'y' else P.rug(1.6, w - 2.0, 'rf_carpetred'), cx, cy, 0 if al == 'y' else 90, overlay=True, force=True, name='runner')


def dais(w, d, steps=3, step_h=.18, tex='rf_marble'):
    p = P.Prop()
    for k in range(steps):
        inset = k * .45; z1 = (k + 1) * step_h
        p.m.box((-w / 2 + inset, -d / 2 + inset, k * step_h), (w / 2 - inset, d / 2 - inset, z1), tex, 3, faces='xXyYZ')
        p.c.box((-w / 2 + inset, -d / 2 + inset, 0), (w / 2 - inset, d / 2 - inset, z1), 'marble')
    return p, steps * step_h


def stair_lights(F):
    rec = next((s for s in R.STAIRS if s['room'] == F.r['id'] and s['type'] in ('U', 'I')), None)
    sp = F.r['special']; F.block_all = True
    if rec is None: return
    land = rec['landing']; ez = rec['entry_zone']; rise = rec['to_z'] - rec['from_z']
    land_edge = 'W' if min(land) <= F.inner[0] + .1 else 'E'
    ent_edge = 'E' if land_edge == 'W' else 'W'
    cy = F.centre()[1]; w, d = F.size()
    if sp['stair'] == 'U':
        for s in (cy - d / 4, cy + d / 4): F.wall(land_edge, P.sconce(), s, rise / 2 + 2.4, overlay=True, name='sconce')
        F.wall(ent_edge, P.sconce(), cy, 2.6, overlay=True, name='sconce')
        F.wall(ent_edge, P.sconce(), cy, rise + 2.5, overlay=True, name='sconce')
        if F.r['h'] > 10: F.wall(land_edge, P.wall_hanging(1.6, 3.4), cy, rise / 2 + 3.0, overlay=True, name='banner')
        if F.r['h'] >= 12: F.hang(P.chandelier(1.3, 8, 1.6), (F.inner[0] + F.inner[2]) / 2, cy)
    else:
        for s in (cy - d / 4, cy + d / 4):
            F.wall(land_edge, P.sconce(), s, 2.4, overlay=True, name='sconce')
            F.wall(ent_edge, P.sconce(), s, rise + 2.4, overlay=True, name='sconce')
    # both long walls get sconces above the flights' highest point near the landing
    for e in ('S', 'N'):
        x = (min(land) + max(land)) / 2
        F.wall(e, P.sconce(), x, (rise / 2 if sp['stair'] == 'U' else 0) + 2.4, overlay=True, name='sconce')


# ====================================================================== recipes (per room id)
RECIPES = {}
def recipe(*ids):
    def deco(fn):
        for i in ids: RECIPES[str(i)] = fn
        return fn
    return deco


@recipe(1)
def r_vestibule(F):
    cx, cy = F.centre(); w, d = F.size()
    F.put(P.rug(4.0, d - .6, 'rf_carpetred'), cx, cy, 0, overlay=True, force=True, name='runner')
    for sx in (-1, 1):
        for dy in (-2.2, 2.2):
            F.put(P.column(.45, F.r['h'] - L.SLAB, 'rf_whitemarble'), cx + sx * 4.2, cy + dy, name='column')
        F.put(P.statue('rf_whitemarble', 1.0, 1.0), cx + sx * 7.8, cy + 3.0, 90 * -sx, name='statue')
        F.put(P.brazier(), cx + sx * 6.0, cy + 2.8, name='brazier')
    banners(F, ('S', 'N'), 4.0, z=2.2, h=3.4)
    F.hang(P.chandelier(1.4, 10, 1.8), cx, cy)


@recipe('SW', 'SE', 'HS', 'SS', 'DS', 'VS', 'BH')
def r_stair(F):
    stair_lights(F)


@recipe(2)
def r_reception_hall(F):
    cx, cy = F.centre(); w, d = F.size()
    F.put(P.rug(5.0, d - 1.0, 'rf_carpetblue'), cx, cy, 0, overlay=True, force=True, name='runner')
    for sx in (-1, 1):
        for xx in (6.0, 11.0):
            F.put(P.column(.5, F.r['h'] - L.SLAB, 'rf_marble'), cx + sx * xx, cy, name='column')
        F.wall('S', P.bench(2.4, 'rf_wood', 'rf_fabricblue'), cx + sx * 9.0, name='bench')
        F.wall('N', P.statue('rf_whitemarble'), cx + sx * 9.0, name='statue')
    paintings(F, ('S', 'N'), 4.0, z=2.0); banners(F, ('W', 'E'), 4.0)
    chandeliers(F, 3, 1, 2.0, 1.3)
    F.ensure_light()


@recipe(3)
def r_throne(F):
    cx, cy = F.centre(); w, d = F.size(); ix0, iy0, ix1, iy1 = F.inner
    p, hz = dais(12.0, 6.5, 3)
    dy = iy1 - 1.8 - 3.25
    F.put(p, cx, dy, 0, name='throne dais')
    F.put(P.throne(), cx, dy + .6, 180, z=hz, layer=round(hz, 1), name='THRONE')
    F.put(P.rug(10.0, 5.5, 'rf_carpetred'), cx, dy, 0, z=hz, overlay=True, force=True, name='dais carpet')
    for sx in (-1, 1):
        F.put(P.chair(high=True), cx + sx * 2.2, dy + .6, 180, z=hz, layer=round(hz, 1), name='consort chair')
        F.put(P.candelabra(1.9), cx + sx * 4.6, dy + 1.8, z=hz, layer=round(hz, 1), name='candelabra')
        F.put(P.statue('rf_gold', 1.1, 1.2), cx + sx * 7.5, dy + 2.0, 180, name='gilded statue')
    # nave carpet from the south doors to the dais
    F.put(P.rug(4.6, dy - 3.25 - iy0 - .2, 'rf_carpetred'), cx, (iy0 + dy - 3.25) / 2, 0, overlay=True, force=True, name='nave carpet')
    # two colonnades with braziers and banners between them
    for sx in (-1, 1):
        for k in range(7):
            y = iy0 + 5.0 + k * 6.5
            if y > dy - 4.5: break
            F.put(P.column(.6, F.r['h'] - L.SLAB, 'rf_marble'), cx + sx * 6.5, y, name='colonnade')
            if k % 2 == 1: F.put(P.brazier(), cx + sx * 4.2, y, name='brazier')
            else: F.put(P.armor_stand(), cx + sx * 9.5, y, 90 * -sx, name='armour')
    banners(F, ('W', 'E'), 6.5, z=6.8, h=4.0)
    F.wall('N', P.wall_hanging(4.0, 6.0), cx, 3.4, overlay=True, name='royal banner') or F.wall('N', P.wall_hanging(4.0, 6.0), cx - 4.0, 3.4, overlay=True)
    for y in np.arange(iy0 + 6.0, iy1 - 3.0, 9.0):
        F.hang(P.chandelier(1.8, 12, 2.6), cx, y)
    F.ensure_light(3.0, 3.2)


@recipe('CW', 'CE', 'KW', 'KE', 'CW1', 'CE1', 'KW1', 'KE1')
def r_gallery(F):
    corridor(F, statues=F.r['id'] in ('CW', 'CE'), bench=F.r['id'] not in ('KW1', 'KE1'))
    if F.r['h'] >= 7: chandeliers(F, 1, None, 1.6, .9)


@recipe(4)
def r_audience(F):
    cx, cy = F.centre(); w, d = F.size(); ix0, iy0, ix1, iy1 = F.inner
    p, hz = dais(5.0, 3.0, 2)
    F.wall('W', p, cy, name='dais'); F.put(P.throne(), ix0 + 1.6, cy, -90, z=hz, layer=round(hz, 1), name='audience throne')
    F.put(P.rug(9.0, 6.0, 'rf_carpetred'), cx + 1.0, cy, 0, overlay=True, force=True, name='rug')
    for k in range(4):
        F.put(P.bench(3.0, 'rf_wood', 'rf_fabricred'), cx + 1.0 + (k - 1.5) * 2.0, cy - 3.6, 0, name='petitioner bench')
    banners(F, ('S', 'N'), 4.0); F.wall('W', P.wall_hanging(2.4, 4.0), cy, 2.4, overlay=True, name='banner')
    F.walls_run(('E',), P.candelabra, 4.0, margin=2.0, name='candelabra')
    chandeliers(F, 2, 1)


@recipe(5)
def r_council(F):
    cx, cy = F.centre()
    F.put(P.rug(12, 9, 'rf_carpetblue'), cx, cy, 0, overlay=True, force=True, name='rug')
    dining(F, cx, cy, 8.0, 'x', 'rf_fabricblue', tw=1.6)
    F.put(P.chair(high=True), cx - 4.8, cy, -90, name="king's chair")
    shelves(F, ('W',), 'ledgers'); paintings(F, ('S', 'N'), 4.0)
    F.put(P.globe(), cx + 5.5, cy + 3.5, name='globe')
    chandeliers(F, 2, 1)


@recipe(9)
def r_history(F):
    cx, cy = F.centre(); w, d = F.size()
    for (x, y) in grid_pts(F, 3, 2, 3.0, 3.5):
        F.put(P.display_case(1.2, .8, 1.0, ['rf_gold', 'rf_bronze', 'rf_copper'][int(x * 7) % 3]), x, y, name='display case')
    paintings(F, R.EDGES, 3.2, z=1.9)
    F.walls_run(('W',), P.armor_stand, 3.0, margin=2.0, name='armour')
    F.put(P.rug(w - 3, 2.0, 'rf_carpetred'), cx, cy, 0, overlay=True, force=True, name='runner')
    chandeliers(F, 1, 2)


@recipe(7)
def r_ballroom(F):
    cx, cy = F.centre(); w, d = F.size(); ix0, iy0, ix1, iy1 = F.inner
    F.put(P.rug(w - 6, d - 8, 'rf_carpetblue'), cx, cy, 0, overlay=True, force=True, name='dance floor carpet')
    F.put(P.instrument_set(), ix0 + 1.6, iy1 - 2.0, 0, name='musicians')
    for e in ('W',):
        F.wall_run(e, lambda: P.bench(2.0, 'rf_wood', 'rf_fabricred'), 4.0, margin=3.0, name='bench')
    F.walls_run(('S', 'N'), P.candelabra, 3.0, margin=2.0, name='candelabra')
    paintings(F, ('E',), 4.0, z=2.2); banners(F, ('W',), 5.0)
    chandeliers(F, 1, 3, 2.0, 1.6)


@recipe(10)
def r_reception_room(F):
    cx, cy = F.centre()
    rug_centre(F, 'rf_carpetred', 2.4); sitting_group(F, cx, cy)
    F.walls_run(('W',), lambda: P.fireplace(2.4), 8, margin=3.0, name='fireplace', limit=1)
    paintings(F); F.walls_run(('S',), lambda: P.wardrobe(1.4, 2.2), 6, margin=2.0, name='cabinet', limit=2)
    chandeliers(F, 1, 1)
    F.ensure_light()


@recipe(25)
def r_scribe(F):
    cx, cy = F.centre()
    for (x, y) in grid_pts(F, 3, 2, 2.0, 1.8):
        F.put(P.desk(1.4), x, y, 0, name='scribe desk'); F.put(P.chair(), x, y - .75, 0, name='stool')
    shelves(F, ('W', 'N'), 'scrolls')
    F.put(P.lectern(), cx, F.inner[3] - 3.4, 180, name='lectern')
    F.ensure_light(5.0)


@recipe(23)
def r_map(F):
    cx, cy = F.centre()
    F.put(P.map_table(4.4, 2.6), cx, cy, 0, name='map table')
    for dx in (-1.5, 0, 1.5):
        F.put(P.chair(), cx + dx, cy - 1.8, 0, name='chair'); F.put(P.chair(), cx + dx, cy + 1.8, 180, name='chair')
    F.put(P.globe(), cx + 4.0, cy + 2.4, name='globe'); F.put(P.telescope(), cx - 4.0, cy + 2.4, name='telescope')
    shelves(F, ('W',), 'scrolls'); F.walls_run(('S', 'N'), lambda: P.painting(1.8, 1.3, 'rf_map'), 4.0, z=1.6, margin=1.6, overlay=True, name='wall map')
    F.ensure_light(5.0)


@recipe(26)
def r_treasury(F):
    cx, cy = F.centre(); w, d = F.size()
    F.put(P.crown_display(), cx, cy, name='crown jewels')
    for (x, y) in grid_pts(F, 4, 2, 1.6, 1.2):
        if abs(x - cx) < 2 and abs(y - cy) < 2: continue
        F.put(P.gold_pile(.7), x, y, name='gold')
    F.walls_run(('W', 'S', 'N'), lambda: P.chest(1.1, True), 1.8, margin=1.0, name='treasure chest')
    F.walls_run(('W',), P.candelabra, 3.0, margin=1.5, name='candelabra', overlay=True)
    F.sconces(z=2.4, spacing=3.5)


@recipe(21)
def r_library(F):
    ix0, iy0, ix1, iy1 = F.inner; z0 = F.r['z0']; zg = 7.0
    # gallery stair (south wall) and gallery columns are obstacles
    F.block((ix1 - 3.9 - 40 * .295 - .2, iy0, ix1 - 3.9 + .2, iy0 + 1.9))
    for y in np.arange(iy0 + 4, iy1 - 2.3, 6.0):
        F.block((ix0 + 2.4 - .3, y - .3, ix0 + 2.4 + .3, y + .3)); F.block((ix1 - 3.9 - .3, y - .3, ix1 - 3.9 + .3, y + .3))
    for x in np.arange(ix0 + 2.4, ix1 - 3.8, 5.0): F.block((x - .3, iy1 - 2.4 - .3, x + .3, iy1 - 2.4 + .3))
    shelves(F, ('W', 'N', 'E'), 'books', 2.15, h=3.2)
    shelves(F, ('W', 'N', 'E'), 'books', 2.15, layer=zg, z=zg, h=3.0)
    # free-standing double-sided stacks in the open nave
    for y in np.arange(iy0 + 6.0, iy1 - 4.5, 4.0):
        F.put(P.bookshelf(4.0, 2.6, .5), (ix0 + ix1) / 2 + 1.0, y, 0, name='stack') and F.put(P.bookshelf(4.0, 2.6, .5), (ix0 + ix1) / 2 + 1.0, y + .5, 180, name='stack', force=True)
    cx = (ix0 + 2.8 + ix1 - 4.3) / 2
    F.put(P.table(3.0, 1.2, .78, 'rf_wood'), cx - 1.0, iy0 + 3.6, 90, name='reading table')
    F.put(P.lectern(), cx + 1.5, iy0 + 3.0, 0, name='lectern')
    for k in range(3): F.put(P.candelabra(.5), cx - 1.0, iy0 + 2.6 + k, z=.78, overlay=True, force=True, name='candles')
    F.put(P.globe(), ix0 + 3.6, iy0 + 2.4, name='globe')
    chandeliers(F, 1, 3, 2.2, 1.2)
    F.sconces(z=2.6 + zg, spacing=5.0)
    # secret door: book lever on the shelf nearest the bookcase (door 21-HS at x = -46 on the south wall)
    F.interactive.append({'id': 'book_lever', 'model': 'it_booklever', 'pos': [-48.4, iy0 + .32, z0 + 1.45], 'rot': 0.0})


@recipe(27)
def r_artifacts(F):
    for (x, y) in grid_pts(F, 3, 3, 2.4, 2.4):
        F.put(P.display_case(1.0, .8, 1.0, 'rf_bronze'), x, y, name='artifact case')
    F.walls_run(('S', 'E'), P.armor_stand, 2.6, margin=1.6, name='armour')
    F.walls_run(('N',), lambda: P.weapon_rack(2.0), 3.0, margin=1.6, name='weapon display')
    paintings(F, ('W',), 3.6); chandeliers(F, 1, 1); F.ensure_light()


@recipe(8, 'EG')
def r_portraits(F):
    cx, cy = F.centre(); w, d = F.size()
    paintings(F, R.EDGES, 2.6, z=1.6); paintings(F, R.EDGES, 2.6, z=3.2 if F.r['h'] > 6 else 1.6)
    for k in range(int(d // 8)):
        F.put(P.bench(2.4, 'rf_wood', 'rf_fabricred'), cx, F.inner[1] + 4 + k * 8, 90, name='bench')
    F.put(P.rug(3.0, d - 3.0, 'rf_carpetred'), cx, cy, 0, overlay=True, force=True, name='runner')
    chandeliers(F, 1, None, 1.6); F.ensure_light()


@recipe(6)
def r_banquet(F):
    cx, cy = F.centre(); w, d = F.size(); ix0, iy0, ix1, iy1 = F.inner
    dining(F, cx - 2.5, cy - 1.0, d - 9.0, 'y', 'rf_fabricred')
    dining(F, cx + 3.0, cy - 1.0, d - 9.0, 'y', 'rf_fabricred')
    F.put(P.table(6.0, 1.2, .9, 'rf_wood', 'rf_fabricblue'), cx, iy1 - 2.4, 0, name='high table')
    for dx in (-2, -1, 0, 1, 2): F.put(P.chair(high=dx == 0), cx + dx * 1.1, iy1 - 1.5, 180, name='chair')
    F.walls_run(('E',), lambda: P.fireplace(3.0), 20, margin=10.0, name='fireplace', limit=1)
    banners(F, ('W', 'E'), 5.0, z=3.0); chandeliers(F, 1, 3, 1.8, 1.4)
    F.walls_run(('S',), P.barrel, 1.2, margin=1.0, name='wine barrel', limit=4)


@recipe('SH')
def r_service_hall(F):
    F.walls_run(('W', 'N'), P.crate, 1.4, margin=1.2, name='crate', limit=4)
    F.walls_run(('E',), P.barrel, 1.2, margin=1.2, name='barrel', limit=3)
    F.walls_run(('S',), lambda: P.bench(2.0), 5, margin=5.0, name='bench', limit=1)
    F.sconces(spacing=4.0)


@recipe(46)
def r_laundry(F):
    cx, cy = F.centre()
    for dx in (-4.5, 0, 4.5): F.put(P.bathtub(), cx + dx, cy, 90, name='wash tub')
    F.walls_run(('E', 'W'), lambda: P.shelf_items(2.0, 2.2, 'linen'), 2.4, margin=1.2, name='linen shelf')
    F.walls_run(('N',), lambda: P.table(2.4, .9, .9, 'rf_woodlight'), 3.5, margin=1.5, name='ironing table')
    F.walls_run(('N', 'S'), P.sack, 1.0, margin=1.2, name='sack', limit=4)
    F.put(P.cauldron(), cx, cy + 3.0, name='boiler'); F.ensure_light(5.0)


@recipe(44)
def r_servants_dining(F):
    cx, cy = F.centre()
    dining(F, cx, cy - 1.8, 9.0, 'x', None); dining(F, cx, cy + 2.4, 9.0, 'x', None)
    F.walls_run(('E',), lambda: P.shelf_items(2.0, 2.2, 'food'), 2.4, margin=1.4, name='dresser')
    F.walls_run(('W',), lambda: P.hearth(2.6), 20, margin=7.0, name='hearth', limit=1)
    F.ensure_light(5.0)


@recipe(42)
def r_prep(F):
    cx, cy = F.centre()
    for dy in (-2.0, 2.0): F.put(P.table(6.0, 1.2, .9, 'rf_woodlight'), cx, cy + dy, 0, name='prep table')
    F.walls_run(('W', 'E', 'N'), lambda: P.shelf_items(2.0, 2.2, 'food'), 2.4, margin=1.2, name='food shelf')
    F.walls_run(('S',), P.barrel, 1.1, margin=1.0, name='barrel', limit=5)
    F.walls_run(('S',), P.sack, 1.0, margin=8.0, name='sack', limit=4)
    F.ensure_light(6.0)


@recipe(41)
def r_kitchen(F):
    cx, cy = F.centre(); ix0, iy0, ix1, iy1 = F.inner
    F.wall('E', P.hearth(4.0), cy - 4.0, name='great hearth') or F.wall('E', P.hearth(4.0), cy + 4.0, name='great hearth')
    F.wall('N', P.oven(), cx - 4.0, name='bread oven'); F.wall('N', P.oven(), cx + 4.0, name='bread oven')
    for y in (cy - 4.0, cy + 2.0): F.put(P.table(7.0, 1.4, .9, 'rf_woodlight'), cx - 1.0, y, 0, name='kitchen table')
    F.put(P.cauldron(), cx - 1.0, cy - 1.0, name='stockpot')
    F.walls_run(('W',), lambda: P.shelf_items(2.0, 2.2, 'jars'), 2.4, margin=1.2, name='spice shelf')
    F.walls_run(('S',), P.barrel, 1.1, margin=1.4, name='barrel', limit=6)
    F.ensure_light(6.0)


@recipe(20)
def r_guard_ante(F):
    cx, cy = F.centre()
    F.walls_run(('W', 'E'), P.armor_stand, 2.4, margin=1.6, name='armour')
    F.walls_run(('S',), lambda: P.weapon_rack(2.4), 3.6, margin=2.0, name='weapon rack')
    F.put(P.table(2.4, 1.0, .78), cx, cy - 1.0, 0, name='guard table')
    for dx in (-.8, .8): F.put(P.chair(), cx + dx, cy - 1.9, 0, name='stool')
    banners(F, ('W', 'E'), 4.0, h=2.6); F.ensure_light(5.0)


@recipe(24)
def r_war_room(F):
    cx, cy = F.centre(); w, d = F.size()
    F.put(P.map_table(6.0, 3.2), cx, cy - .5, 0, name='campaign map table')
    for dx in (-2.4, -1.2, 0, 1.2, 2.4):
        F.put(P.chair(), cx + dx, cy - 2.6, 0, name='chair'); F.put(P.chair(), cx + dx, cy + 1.6, 180, name='chair')
    F.put(P.chair(high=True), cx - 3.7, cy - .5, -90, name="marshal's chair")
    F.put(P.globe(), cx + 6.5, cy + 3.5, name='globe')
    F.walls_run(('W', 'E'), lambda: P.painting(2.0, 1.4, 'rf_map'), 4.0, z=1.5, margin=1.5, overlay=True, name='wall map')
    F.walls_run(('S',), P.armor_stand, 3.0, margin=3.5, name='armour', limit=4)
    banners(F, ('W', 'E'), 3.4, h=2.4); chandeliers(F, 2, 1, 1.3)
    F.walls_run(('N',), P.candelabra, 2.6, margin=1.6, name='candelabra')


@recipe(11)
def r_royal_bed(F):
    ix0, iy0, ix1, iy1 = F.inner; cx, cy = F.centre()
    F.wall('W', P.bed(2.6, 2.8, 'rf_fabricred'), cy, name='royal canopy bed')
    F.put(P.rug(6.0, 7.0, 'rf_carpetred'), ix0 + 3.6, cy, 0, overlay=True, force=True, name='rug')
    for s in (cy - 2.4, cy + 2.4): F.wall('W', P.chest(.6, False), s, name='bedside')
    for s in (cy - 2.4, cy + 2.4): F.put(P.candelabra(1.4), ix0 + .5, s + (.9 if s > cy else -.9), name='candelabra')
    F.walls_run(('E',), lambda: P.fireplace(2.2), 9, margin=7.0, name='fireplace', limit=1)
    sitting_group(F, ix1 - 4.0, iy1 - 3.0)
    F.walls_run(('S',), lambda: P.wardrobe(1.8, 2.5), 3.0, margin=2.0, name='wardrobe', limit=2)
    F.put(P.chest(1.3, False), ix0 + 3.6 + 1.6, cy, 90, name='blanket chest')
    paintings(F, ('N', 'S'), 4.0, z=1.8); chandeliers(F, 1, 1, 1.2)


@recipe(12)
def r_dressing(F):
    F.walls_run(('W', 'E', 'N'), lambda: P.wardrobe(1.6, 2.4), 2.0, margin=1.1, name='wardrobe')
    cx, cy = F.centre(); F.put(P.table(1.4, .7, .8), cx, cy, 0, name='vanity'); F.put(P.chair(), cx, cy - .7, 0, name='stool')
    F.put(P.rug(5, 3, 'rf_carpetblue'), cx, cy, 0, overlay=True, force=True, name='rug'); F.ensure_light(5.0)


@recipe(14)
def r_bath(F):
    cx, cy = F.centre()
    p, hz = dais(4.0, 4.0, 2, tex='rf_whitemarble'); F.put(p, cx, cy, name='bath dais')
    F.put(P.bathtub(), cx, cy, 90, z=hz, layer=round(hz, 1), name='copper bath')
    F.walls_run(('W', 'E'), lambda: P.shelf_items(2.0, 2.2, 'bottles'), 3.0, margin=1.2, name='oils shelf')
    for dx in (-2.6, 2.6): F.put(P.candelabra(1.5), cx + dx, cy + 2.6, name='candelabra')
    F.walls_run(('S', 'N'), lambda: P.statue('rf_whitemarble', .8, .9), 6, margin=2.0, name='statue', limit=2)
    F.ensure_light(5.0)


@recipe(13)
def r_sitting(F):
    cx, cy = F.centre(); rug_centre(F, 'rf_carpetblue', 2.0)
    sitting_group(F, cx, cy + 1.0)
    F.walls_run(('W',), lambda: P.fireplace(2.4), 9, margin=5.0, name='fireplace', limit=1)
    F.walls_run(('S',), lambda: P.bookshelf(2.0, 2.6), 2.2, margin=1.2, name='bookcase', limit=4)
    F.put(P.instrument_set(), F.inner[2] - 2.6, F.inner[3] - 1.4, 0, name='harp & drum')
    paintings(F, ('N',), 3.0); chandeliers(F, 1, 1, 1.2)


@recipe(15)
def r_study(F):
    cx, cy = F.centre()
    F.put(P.desk(2.0), cx, cy, 180, name="king's desk"); F.put(P.chair(high=True), cx, cy + .8, 180, name='chair')
    for dx in (-.7, .7): F.put(P.chair(), cx + dx, cy - 1.0, 0, name='visitor chair')
    shelves(F, ('W', 'S', 'N'), 'books', 2.15, h=3.0)
    F.put(P.globe(), cx + 3.0, cy - 2.4, name='globe'); F.put(P.rug(5, 4, 'rf_carpetred'), cx, cy, 0, overlay=True, force=True, name='rug')
    F.put(P.candelabra(.5), cx - .6, cy, z=.78, overlay=True, force=True, name='candles'); F.ensure_light(5.0)


@recipe(18, 'GS', 17, 19)
def r_suite(F):
    ix0, iy0, ix1, iy1 = F.inner; cx, cy = F.centre(); rid = F.r['id']
    fab = {'18': 'rf_fabricblue', 'GS': 'rf_fabricred', '17': 'rf_fabricblue', '19': 'rf_fabricred'}[rid]
    big = rid in ('18', 'GS')
    placed = False
    for e in ('W', 'E', 'N', 'S'):
        ax, c, a, b, sg = F.edge_info(e)
        if F.wall(e, P.bed(2.2 if big else 1.8, 2.5, fab, canopy=big), (a + b) / 2, name='bed'): placed = True; break
    if rid == '19':
        F.walls_run(('N',), lambda: P.bed(1.2, 2.1, fab, canopy=False), 2.6, margin=2.0, name='child bed', limit=2)
    F.walls_run(('S', 'N'), lambda: P.wardrobe(1.6, 2.3), 4.0, margin=1.5, name='wardrobe', limit=2)
    sitting_group(F, ix1 - 3.0, iy0 + 3.0) if big else F.put(P.table(1.2, .8, .78), cx + 2, cy - 2, name='table')
    F.walls_run(('E', 'W'), lambda: P.fireplace(2.0), 9, margin=4.0, name='fireplace', limit=1)
    rug_centre(F, 'rf_carpetblue' if 'blue' in fab else 'rf_carpetred', 2.8)
    paintings(F, ('S', 'N'), 4.0); F.ensure_light(5.0)


@recipe(22)
def r_archive(F):
    w, d = F.size(); cx, cy = F.centre()
    shelves(F, R.EDGES, 'scrolls', 2.2)
    for x in np.arange(F.inner[0] + 4.0, F.inner[2] - 3.0, 3.2):
        F.put(P.shelf_items(6.0, 2.2, 'ledgers'), x, cy, 90, name='archive stack')
    F.put(P.lectern(), cx, F.inner[1] + 2.0, 0, name='lectern')
    F.sconces(z=2.3, spacing=4.0)


@recipe(29)
def r_scholar(F):
    cx, cy = F.centre()
    F.put(P.desk(1.8), cx, cy, 0, name='writing desk'); F.put(P.chair(), cx, cy - .8, 0, name='chair')
    shelves(F, ('W', 'E', 'S'), 'books', 2.15, h=3.0)
    F.put(P.telescope(), cx + 3.0, cy + 2.4, name='telescope'); F.put(P.globe(), cx - 3.0, cy + 2.4, name='globe')
    F.put(P.lectern(), cx + 3.4, cy - 2.0, 0, name='lectern'); F.ensure_light(5.0)


@recipe(30, 'K1')
def r_alchemy(F):
    cx, cy = F.centre(); w, d = F.size()
    F.walls_run(('W', 'E', 'N'), lambda: P.shelf_items(2.0, 2.2, 'bottles'), 2.3, margin=1.2, name='reagent shelf')
    dx, dy = (7.0, 5.5) if F.r['id'] == 'K1' else (4.0, 3.0)
    for (x, y) in ((cx - dx, cy - dy), (cx + dx, cy - dy), (cx - dx, cy + dy), (cx + dx, cy + dy)):
        F.put(P.flask_table(2.4), x, y, 0, name='flask bench')
    F.put(P.cauldron(True), cx, cy if F.r['id'] == '30' else cy - 6.0, name='bubbling cauldron')
    F.walls_run(('S',), P.brazier, 3.0, margin=2.0, name='athanor', limit=2)
    F.walls_run(('S',), P.lectern, 3.0, margin=5.0, name='grimoire', limit=1)
    F.walls_run(('S', 'N'), P.barrel, 1.2, margin=4.0, name='barrel', limit=3)
    F.ensure_light(5.0)


@recipe('ST')
def r_steward(F):
    cx, cy = F.centre()
    F.put(P.desk(1.8), cx, cy, 0, name='steward desk'); F.put(P.chair(), cx, cy - .8, 0, name='chair')
    shelves(F, ('W', 'N'), 'ledgers'); F.walls_run(('S',), P.chest, 1.6, margin=2, name='coffer', limit=3)
    F.put(P.table(2.4, 1.0, .78), cx + 4.0, cy + 3.0, 0, name='table'); F.ensure_light(5.0)


@recipe('WS')
def r_linen(F):
    shelves(F, R.EDGES, 'linen', 2.2)
    cx, cy = F.centre()
    for dx in (-3, 3): F.put(P.shelf_items(6.0, 2.2, 'linen'), cx + dx, cy, 90, name='linen rack')
    F.sconces(z=2.3, spacing=4.5)


@recipe('MR')
def r_minstrels(F):
    cx, cy = F.centre(); F.put(P.instrument_set(), cx - 1.0, cy, 0, name='instruments')
    for dx in (-2, 0, 2): F.put(P.chair(), cx + dx - 1.0, cy - 2.0, 0, name='chair')
    F.walls_run(('W', 'E'), lambda: P.bench(2.0, 'rf_wood', 'rf_fabricblue'), 4.0, margin=2.0, name='bench', limit=4)
    F.walls_run(('S',), lambda: P.shelf_items(2.0, 2.2, 'scrolls'), 2.4, margin=1.4, name='music scores', limit=3)
    rug_centre(F, 'rf_carpetred', 2.5); paintings(F, ('N',), 3.0); F.ensure_light(5.0)


@recipe('LC', 'SC', 'KP')
def r_plain_corridor(F):
    dark = F.r['wall'] == 'rf_dungeon'
    corridor(F, statues=False, art=not dark, bench=False)
    if dark:
        F.walls_run(('S', 'N') if F.long_axis() == 'x' else ('W', 'E'), lambda: P.chains(), 7.0, z=2.2, margin=3.0, overlay=True, name='chains')


@recipe('WC')
def r_wine(F):
    ix0, iy0, ix1, iy1 = F.inner
    for x in np.arange(ix0 + 1.0, ix1 - .5, .9):
        F.put(P.barrel(.42, 1.0), x, iy1 - .5, name='wine barrel'); F.put(P.barrel(.42, 1.0), x, iy0 + .5, name='wine barrel')
    for y in np.arange(iy0 + 3.0, iy1 - 2.5, 3.0):
        F.put(P.shelf_items(6.0, 2.0, 'bottles'), (ix0 + ix1) / 2, y, 0, name='bottle rack')
    F.put(P.table(1.6, .8, .9), ix1 - 2.0, (iy0 + iy1) / 2, 90, name='tasting table')
    F.sconces(z=2.3, spacing=4.5)


@recipe(43)
def r_pantry(F):
    shelves(F, ('W', 'E', 'N'), 'food', 2.2)
    cx, cy = F.centre()
    for (x, y) in grid_pts(F, 3, 2, 3.0, 3.0): F.put(P.sack(), x, y, name='sack') and F.put(P.barrel(.4, .9), x + .8, y, name='barrel')
    F.walls_run(('S',), P.crate, 1.2, margin=1.4, name='crate', limit=6)
    F.sconces(z=2.3, spacing=4.5)


@recipe(45)
def r_servants(F):
    ix0, iy0, ix1, iy1 = F.inner
    for e in ('W', 'E'): F.wall_run(e, P.bunk, 1.6, margin=1.2, name='bunk')
    F.walls_run(('S', 'N'), P.chest, 1.8, margin=1.4, name='footlocker', limit=6)
    cx, cy = F.centre(); F.put(P.table(3.0, 1.0, .78, 'rf_woodlight'), cx, cy, 90, name='table')
    for dy in (-1, 0, 1): F.put(P.chair(), cx - .9, cy + dy, -90, name='stool')
    F.sconces(z=2.3, spacing=4.0)


@recipe(47)
def r_dungeon(F):
    cx, cy = F.centre(); ix0, iy0, ix1, iy1 = F.inner
    F.walls_run(('W', 'E'), lambda: P.chains(), 2.6, z=2.4, margin=1.2, overlay=True, name='wall shackles')
    F.put(P.pillory(), cx - 5.0, cy + 2.0, 0, name='pillory'); F.put(P.pillory(), cx + 4.0, cy + 2.5, 90, name='pillory')
    F.put(P.table(2.0, 1.0, .8, 'rf_wood'), cx + 5.0, cy - 3.0, 0, name="jailer's table")
    F.put(P.chair(), cx + 5.0, cy - 3.8, 0, name='stool')
    F.walls_run(('S',), P.barrel, 1.2, margin=1.0, name='water barrel', limit=3)
    F.walls_run(('E',), lambda: P.weapon_rack(1.6), 3.0, margin=1.5, name='halberds', limit=2)
    F.walls_run(('W', 'E', 'S', 'N'), P.brazier, 7.0, margin=3.5, name='brazier', limit=4)
    F.sconces(z=2.3, spacing=5.0)


@recipe(48)
def r_cells(F):
    """Six 4.4 m deep cells along the south wall behind iron bars; sliding cell doors."""
    ix0, iy0, ix1, iy1 = F.inner; z0 = F.r['z0']; hh = F.r['h'] - L.SLAB
    depth = 4.4; yb = iy0 + depth; n = 6; cw = (ix1 - ix0) / n; dw = 1.2
    F.block((ix0, iy0, ix1, yb + .1))
    for k in range(n):
        xa = ix0 + k * cw; xb = xa + cw; xd = xa + cw / 2      # door centre
        # bars left and right of the door opening
        for (a, b) in ((xa, xd - dw / 2), (xd + dw / 2, xb)):
            if b - a > .1: F.put(P.cell_bars(b - a, hh), (a + b) / 2, yb, 0, force=True, overlay=True, name='cell bars')
        F.put(P.cell_bars(dw + .02, hh - 2.5), xd, yb, 0, z=2.5, force=True, overlay=True, name='bars over door')
        if k > 0:   # stone partition between cells
            p = P.Prop(); p.box((-.2, -depth / 2, 0), (.2, depth / 2, hh), 'rf_dungeon', uv=3.5, surf='stone')
            F.put(p, xa, iy0 + depth / 2, 0, force=True, overlay=True, name='cell partition')
        F.put(P.cot(), xa + .7, iy0 + 1.4, 0, force=True, overlay=True, name='cot')
        F.put(P.chains(), xb - .5, iy0 + .05, 0, z=2.2, force=True, overlay=True, name='shackle')
        F.put(P.sack(), xb - .6, iy0 + 2.4, force=True, overlay=True, name='straw')
        # sliding door: closed = covering the opening, opens by sliding +x (behind the bars)
        F.interactive.append({'id': 'cell_%d' % (k + 1), 'model': 'it_celldoor', 'pos': [xd - dw / 2 + .03, yb + .09, z0], 'rot': 0.0,
                              'slide': [dw * .95, 0, 0]})
    F.walls_run(('N',), P.brazier, 6.0, margin=3.0, name='brazier', limit=3)
    F.walls_run(('W', 'E'), P.sconce, 3.0, z=2.3, margin=yb - iy0 + .8, overlay=True, name='sconce')
    F.wall_run('N', lambda: P.bench(2.0), 3.0, margin=2.0, name='guard bench', limit=1)


@recipe(49)
def r_interrogation(F):
    cx, cy = F.centre()
    F.put(P.table(2.2, 1.0, .8), cx, cy, 0, name='interrogation table')
    F.put(P.chair(high=True), cx, cy - .9, 0, name='prisoner chair'); F.put(P.chair(), cx, cy + .9, 180, name='chair')
    F.put(P.brazier(), cx + 3.0, cy + 2.5, name='brazier'); F.put(P.pillory(), cx - 3.5, cy + 3.0, 0, name='stocks')
    F.walls_run(('W', 'N'), lambda: P.chains(), 2.2, z=2.4, margin=1.2, overlay=True, name='shackles')
    F.walls_run(('S',), lambda: P.weapon_rack(1.6), 3, margin=2, name='tool rack', limit=1)
    F.put(P.candelabra(.5), cx + .6, cy, z=.8, overlay=True, force=True, name='candle')
    F.sconces(z=2.3, spacing=5.0)


@recipe(50)
def r_vault(F):
    cx, cy = F.centre()
    F.put(P.crown_display(), cx, cy, name='vault crown')
    for (x, y) in grid_pts(F, 3, 3, 2.0, 2.0):
        if abs(x - cx) < 1.5 and abs(y - cy) < 1.5: continue
        F.put(P.gold_pile(.8), x, y, name='gold hoard')
    F.walls_run(R.EDGES, lambda: P.chest(1.1, True), 1.7, margin=1.0, name='treasure chest')
    F.walls_run(R.EDGES, P.candelabra, 5.0, margin=2.5, name='candelabra', overlay=True)
    F.sconces(z=2.3, spacing=4.0)


@recipe('K0')
def r_keep_hall(F):
    cx, cy = F.centre(); F.block_circle((cx, cy), 4.0)
    F.walls_run(('W', 'E'), P.armor_stand, 2.6, margin=1.6, name='armour')
    F.walls_run(('S', 'N'), lambda: P.weapon_rack(2.0), 3.6, margin=1.6, name='weapon rack', limit=4)
    for dx in (-8.5, 8.5): F.put(P.table(3.0, 1.0, .8), cx + dx, cy - 6.0, 90, name='guard table')
    banners(F, ('W', 'E'), 5.0, h=3.0); F.walls_run(R.EDGES, P.brazier, 9.0, margin=4.0, name='brazier', limit=4)
    F.ensure_light(4.0)


@recipe('K2')
def r_keep_lookout(F):
    cx, cy = F.centre(); F.block_circle((cx, cy), 4.0)
    F.put(P.telescope(True), cx - 8.0, cy + 7.0, 0, name='great telescope')
    F.put(P.map_table(3.0, 2.0), cx + 7.0, cy - 6.0, 0, name='signal table')
    F.walls_run(('W', 'E'), lambda: P.weapon_rack(1.8), 4.0, margin=2.0, name='crossbow rack', limit=4)
    F.walls_run(('S', 'N'), P.barrel, 1.0, margin=2.0, name='barrel', limit=6)
    banners(F, ('S',), 4.0, h=3.0); F.ensure_light(4.0)


@recipe('LNW0', 'LNW1', 'LSW0', 'LSW1', 'LNE0', 'LNE1', 'LSE0', 'LSE1')
def r_link(F):
    F.block_all = True
    for e in ('S', 'N'): F.wall(e, P.sconce(), F.centre()[0], 2.4, overlay=True, name='sconce')


@recipe(31)
def r_barracks(F):
    for e in ('W', 'N'): F.wall_run(e, P.bunk, 1.5, margin=1.0, name='bunk')
    F.walls_run(('E', 'S'), P.chest, 1.6, margin=1.2, name='footlocker', limit=6)
    cx, cy = F.centre(); F.put(P.table(4.0, 1.2, .78, 'rf_woodlight'), cx + 2.0, cy - 1.0, 0, name='mess table')
    for dx in (-1.2, 0, 1.2):
        F.put(P.bench(1.0), cx + 2.0 + dx, cy - 2.0, 0, name='stool')
    F.walls_run(('E',), lambda: P.weapon_rack(1.6), 3, margin=2.0, name='rack', limit=1); F.ensure_light(5.0)


@recipe(38, 40)
def r_storage(F):
    F.walls_run(R.EDGES, P.crate, 1.1, margin=1.0, name='crate')
    cx, cy = F.centre()
    for (x, y) in grid_pts(F, 2, 3, 1.8, 2.2):
        F.put(P.barrel(), x, y, name='barrel') and F.put(P.sack(), x + .9, y, name='sack')
    F.ensure_light(5.0)


@recipe(37)
def r_training(F):
    cx, cy = F.centre(); w, d = F.size()
    for k, dx in enumerate((-5, -2, 1, 4)): F.put(P.dummy(), cx + dx, cy + 4.0, 0, name='training dummy')
    F.walls_run(('E',), P.target, 3.0, margin=2.0, name='archery target', limit=4)
    F.walls_run(('W', 'S'), lambda: P.weapon_rack(2.0), 3.0, margin=2.0, name='weapon rack', limit=5)
    F.walls_run(('N',), lambda: P.bench(3.0), 4.0, margin=2.0, name='bench', limit=3)
    F.put(P.rug(6.0, 6.0, 'rf_carpetred'), cx - 2.0, cy - 2.5, 0, overlay=True, force=True, name='sparring mat')
    chandeliers(F, 2, 2, 1.6, 1.0, gold=False); F.ensure_light(4.0, 3.0)


@recipe(32)
def r_officers(F):
    F.walls_run(('W',), lambda: P.bed(1.4, 2.2, 'rf_fabricblue', canopy=False), 3.0, margin=1.6, name='officer bed', limit=3)
    F.walls_run(('N', 'S'), lambda: P.wardrobe(1.2, 2.2), 3.0, margin=2.0, name='locker', limit=4)
    cx, cy = F.centre(); F.put(P.desk(1.4), cx + 1.5, cy, 90, name='desk'); F.put(P.chair(), cx + 2.3, cy, 90, name='chair')
    F.ensure_light(5.0)


@recipe(35)
def r_command(F):
    cx, cy = F.centre()
    F.put(P.map_table(4.0, 2.4), cx, cy, 0, name='command table')
    for dx in (-1.3, 0, 1.3):
        F.put(P.chair(), cx + dx, cy - 1.7, 0, name='chair'); F.put(P.chair(), cx + dx, cy + 1.7, 180, name='chair')
    F.walls_run(('S', 'W'), lambda: P.painting(1.8, 1.3, 'rf_map'), 3.5, z=1.5, margin=1.4, overlay=True, name='wall map')
    banners(F, ('S',), 3.5, h=2.2); F.ensure_light(5.0)


@recipe(33, 34)
def r_armory(F):
    F.walls_run(R.EDGES, lambda: P.weapon_rack(1.8), 2.2, margin=1.1, name='weapon rack')
    cx, cy = F.centre()
    F.put(P.armor_stand(), cx - 1.0, cy, 0, name='armour'); F.put(P.armor_stand(), cx + 1.0, cy, 0, name='armour')
    F.walls_run(('W', 'E'), lambda: P.shield(.45), 1.6, z=2.0 if F.r['h'] < 5 else 2.6, margin=1.0, overlay=True, name='shield')
    F.ensure_light(5.0)


@recipe(39)
def r_gatehouse(F):
    cx, cy = F.centre()
    F.put(P.winch(), cx, cy + 1.6, 0, name='portcullis winch')
    # timber casing over the portcullis slot (the raised grille rises into it)
    cas = P.Prop(); cas.box((-2.9, -.45, 0), (2.9, .45, 2.3), 'rf_wood', uv=2.0)
    cas.m.box((-3.0, -.5, 2.3), (3.0, .5, 2.45), 'rf_iron', 1)
    F.put(cas, 0.0, -L.APO_WALL - 4.55, 0, force=True, name='portcullis casing')
    F.walls_run(('S',), P.barrel, 1.1, margin=2.5, name='pitch barrel', limit=4)
    F.walls_run(('N',), lambda: P.weapon_rack(1.8), 2.4, margin=3.0, name='crossbows', limit=3)
    F.walls_run(('S', 'N'), P.crate, 1.2, margin=7.0, name='crate', limit=4)
    F.ensure_light(5.0)


@recipe('CH')
def r_chapel(F):
    ix0, iy0, ix1, iy1 = F.inner; cx, cy = F.centre()
    F.wall('E', P.altar(), cy, name='altar')
    p, hz = dais(4.0, 7.0, 2, tex='rf_whitemarble'); F.put(p, ix1 - 2.0 - .4, cy, 90, overlay=True, force=True, name='sanctuary step')
    for x in np.arange(ix0 + 4.5, ix1 - 6.0, 1.6):
        for sy in (-1, 1): F.put(P.pew(4.6), x, cy + sy * 3.6, -90, name='pew')
    F.put(P.rug(ix1 - ix0 - 4.0, 2.4, 'rf_carpetred'), cx - 1.0, cy, 0, overlay=True, force=True, name='aisle')
    for sx in (-1, 1): F.put(P.candelabra(1.9), ix1 - 3.0, cy + sx * 2.6, name='candelabra')
    F.put(P.lectern(), ix1 - 5.0, cy - 2.2, 90, name='pulpit')
    F.walls_run(('S', 'N'), lambda: P.statue('rf_whitemarble', 1.0, .8), 6.0, margin=3.0, name='saint statue', limit=4)
    chandeliers(F, 3, 1, 2.6, 1.4); F.ensure_light(3.0, 2.6)


# ---------------------------------------------------------------- non-rect rooms (towers, wall towers, tunnel)
def ring_place(F, c, p, ang, rad, name, rot_extra=0.0):
    x = c[0] + rad * math.cos(math.radians(ang)); y = c[1] + rad * math.sin(math.radians(ang))
    return F.put(p, x, y, ang + 90 + rot_extra, force=True, name=name)


TOWER_RECIPES = {
    'TNW0': [('bookshelf', 1.0), ('bookshelf', 1.0), ('lectern', .9)],
    'TNW1': [('bench', 1.0), ('painting', 0)],
    '16': [('sitting', 1.0), ('candelabra', 1.0)],
    'TSW0': [('armor_stand', 1.0), ('bench', 1.0)], 'TSW1': [('weapon_rack', 1.0)], 'TSW2': [('telescope', 1.0), ('barrel', 1.0), ('weapon_rack', 1.0)],
    'TNE0': [('barrel', 1.0), ('barrel', 1.0), ('crate', 1.0), ('sack', 1.0), ('shelf_food', 1.0)],
    'TNE1': [('bench', 1.0), ('crate', 1.0)],
    '28': [('telescope_big', 1.0), ('globe', 1.0), ('desk', 1.0), ('map_table', 1.0)],
    'TSE0': [('armor_stand', 1.0), ('chest', 1.0)], 'TSE1': [('bench', 1.0)], 'TSE2': [('bell', 1.0)],
}
FACT = {'bookshelf': lambda: P.bookshelf(2.0, 3.0), 'lectern': P.lectern, 'bench': lambda: P.bench(1.8, 'rf_wood', 'rf_fabricred'),
        'painting': lambda: P.painting(1.2, 1.0, 'rf_paint2'), 'candelabra': P.candelabra, 'armor_stand': P.armor_stand,
        'weapon_rack': lambda: P.weapon_rack(1.6), 'telescope': P.telescope, 'telescope_big': lambda: P.telescope(True),
        'barrel': P.barrel, 'crate': P.crate, 'sack': P.sack, 'shelf_food': lambda: P.shelf_items(1.8, 2.2, 'food'),
        'globe': P.globe, 'desk': lambda: P.desk(1.4), 'map_table': lambda: P.map_table(2.4, 1.4), 'chest': P.chest}


def furnish_tower_room(rec, origin, arrive_deg):
    """Ring of wall-backed props between the door/arrival sector; sconces in between."""
    F = Furnisher(dict(id=rec['id'], z0=rec['z0'], h=rec['h'], special={}, shape='poly24'), origin)
    c = rec['center']; ai = rec['apothem_inner']
    door_angles = [15 * k for k in rec['door_edges']]
    t = L.TOWERS[rec['tower']]; kd = int(round(t['door'] / 15)) % 24
    win_angles = [15 * ((kd + j) % 24) for j in (6, 9, 12, 15, 18)]
    def free(a, half=22):
        bad = door_angles + [arrive_deg] + win_angles
        return all(abs((a - b + 180) % 360 - 180) > half for b in bad)
    slots = [a for a in range(0, 360, 30) if free(a, 26)]
    items = TOWER_RECIPES.get(rec['id'], [])
    if rec['id'] == 'TSE2':   # bell chamber: bell hangs over the stair well? no - it sits on the floor ring opposite the door
        a = (t['door'] + 180) % 360
        ring_place(F, c, P.bell(.9), a, ai - 1.4, 'great bell', 0)
        items = []
    used = set()
    for name, _ in items:
        for a in slots:
            if a in used: continue
            if name == 'sitting':
                ring_place(F, c, P.chair(high=True), a, ai - .9, 'armchair'); ring_place(F, c, P.table(.8, .8, .5), a, ai - 2.0, 'side table')
            elif name == 'painting':
                F.put(FACT[name](), c[0] + (ai - .1) * math.cos(math.radians(a)), c[1] + (ai - .1) * math.sin(math.radians(a)), a + 90, z=1.6, force=True, overlay=True, name='painting')
            else:
                p = FACT[name](); mn, mx = prop_bounds(p)
                hw = max(abs(mn[0]), abs(mx[0]))
                ring_place(F, c, p, a, ai - .1 + mn[1] - max(0.0, hw - .9) * .27, name)
            used.add(a); break
    # sconces on solid edges (odd 15-degree edges between slots), never next to each other
    used_s = set()
    for a in range(15, 360, 30):
        if not free(a, 14) or a in used_s: continue
        used_s.add((a + 30) % 360); used_s.add((a + 330) % 360)
        F.put(P.sconce(), c[0] + ai * math.cos(math.radians(a)) * .995, c[1] + ai * math.sin(math.radians(a)) * .995, a + 90, z=2.4, force=True, overlay=True, name='sconce')
    if F.lumens() < 80:
        F.lights.append({'pos': [c[0] - origin[0], c[1] - origin[1], rec['z0'] + 3.0 - origin[2]], 'color': [.9, .7, .45], 'radius': 9.0, 'power': .8})
    return F


def furnish_wall_tower(is_watch):
    """Walk-level guard post furniture for the shared wall-tower model (local frame, +x radial)."""
    r = dict(id='36' if is_watch else 'WT', z0=L.WALK_Z, h=6.0, special={}, shape='poly24')
    F = Furnisher(r, (0, 0, 0)); ai = 7.8
    F.put(P.table(1.6, .9, .8), -3.4, 0, 90, force=True, name='guard table')
    F.put(P.chair(), -2.6, 0, 90, force=True, name='stool')
    F.put(P.brazier(), 0, 0, force=True, name='brazier')
    for a in (60, -60): ring_place(F, (0, 0), P.weapon_rack(1.4), a, ai - .3, 'rack')
    for a in (150, -150): ring_place(F, (0, 0), P.barrel(), a, ai - .6, 'barrel')
    if is_watch:
        ring_place(F, (0, 0), P.telescope(), 30, ai - 1.2, 'telescope'); ring_place(F, (0, 0), P.map_table(1.8, 1.2), 180, ai - 1.4, 'signal map')
    return F


def furnish_tunnel(rec, origin):
    F = Furnisher(dict(id='TN', z0=origin[2], h=3.9, special={}, shape='tunnel'), origin)
    x0, ys, x1, ye = rec['rect']
    n = int((ye - ys) / 8)
    for k in range(1, n):
        y = ys + k * 8.0; t = (y - ys) / (ye - ys)
        z = rec['z0'] if y < 40 + Y else rec['z0'] + (rec['z_end'] - rec['z0']) * (y - (40 + Y)) / (ye - (40 + Y))
        side = -1 if k % 2 else 1
        F.put(P.sconce(), x0 + .02 if side < 0 else x1 - .02, y, -90 if side < 0 else 90, z=z - origin[2] + 2.0, force=True, overlay=True, name='torch')
    return F


def furnish_room(r, origin):
    F = Furnisher(r, origin)
    fn = RECIPES.get(r['id'])
    if fn is None:
        raise KeyError('no furnishing recipe for room ' + r['id'])
    if 'spiral' in r['special']:
        F.block_circle(((r['rect'][0] + r['rect'][2]) / 2, (r['rect'][1] + r['rect'][3]) / 2), 4.0)
    fn(F)
    if 'stair' in r['special'] and r['h'] >= 10:
        F.hang(P.chandelier(1.0, 6, 1.6, gold=False), (F.inner[0] + F.inner[2]) / 2, (F.inner[1] + F.inner[3]) / 2, name='iron chandelier')
    elif 'stair' not in r['special'] and not r['id'].startswith('L'):
        F.ensure_light(3.0, min(2.6, r['h'] - 1.2))
    return F
