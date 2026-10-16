"""Rectilinear room engine: walls/openings/facades/stairs derived from layout.py.
One wall = one centre-line; each side owns its half (inner face -> centre-line), so
neighbouring rooms never generate coplanar or overlapping surfaces."""
from __future__ import annotations
import math
import numpy as np
from fortlib import Mesh, Collision
import layout as L

TEXSCALE = {'rf_stone': 4.0, 'rf_stonedark': 4.0, 'rf_slate': 3.0, 'rf_cobble': 3.0, 'rf_plaster': 3.0, 'rf_ceiling': 4.0,
            'rf_marble': 4.0, 'rf_dungeon': 3.5, 'rf_rock': 6.0, 'rf_iron': 2.0, 'rf_wood': 2.5, 'rf_woodlight': 2.5,
            'rf_grass': 8.0, 'rf_dirt': 8.0, 'rf_gravel': 4.0, 'rf_carpetblue': 3.0, 'rf_carpetred': 2.0, 'rf_gold': 1.0,
            'rf_whitemarble': 2.0, 'rf_books': 2.4, 'rf_glass': 1.6, 'rf_stained': 1.6, 'rf_hedge': 3.0}
SURF_OF = {'rf_marble': 'marble', 'rf_woodlight': 'wood', 'rf_wood': 'wood', 'rf_cobble': 'paving', 'rf_dungeon': 'stone',
           'rf_stone': 'stone', 'rf_carpetblue': 'carpet', 'rf_carpetred': 'carpet'}
WIN = {  # style: (width, sill, height, spacing)
    'palace7': (1.8, 1.5, 3.8, 4.6), 'palace5': (1.6, 1.1, 2.9, 4.2), 'keep': (1.2, 1.6, 2.6, 6.0),
    'small': (1.2, 1.3, 1.8, 4.0), 'slit': (0.5, 1.0, 2.0, 3.0), 'chapel': (2.0, 2.6, 6.0, 5.0)}
AMBIENT = {'warm': (.40, .34, .26), 'work': (.44, .41, .35), 'dim': (.24, .21, .17), 'cellar': (.21, .18, .14),
           'dungeon': (.15, .14, .13), 'vault': (.22, .19, .12), 'alchemy': (.19, .25, .20), 'chapel': (.33, .30, .29)}

ROOM = {r['id']: r for r in L.ROOMS}
EDGES = ('S', 'N', 'W', 'E')
EPS = 1e-6


def uvs_for(tex, s0, s1, z0, z1):
    k = TEXSCALE.get(tex, 2.0)
    return [(s0 / k, z0 / k), (s1 / k, z0 / k), (s1 / k, z1 / k), (s0 / k, z1 / k)]


def edge_line(r, e):
    x0, y0, x1, y1 = r['rect']
    return {'S': ('y', y0, x0, x1, 1), 'N': ('y', y1, x0, x1, -1), 'W': ('x', x0, y0, y1, 1), 'E': ('x', x1, y0, y1, -1)}[e]


def P(r, e, s, z, off):
    """World point on edge e at abscissa s, height z, offset off (positive = into room)."""
    ax, c, _, _, sg = edge_line(r, e)
    return (s, c + sg * off, z) if ax == 'y' else (c + sg * off, s, z)


def inward(r, e):
    ax, c, _, _, sg = edge_line(r, e)
    return np.array((0, sg, 0.)) if ax == 'y' else np.array((sg, 0, 0.))


def zr(r):
    return r['z0'], r['z0'] + r['h']


def neighbours(r, e, block=None):
    """Rooms touching edge e from outside with positive plan overlap: (room, s0, s1, z0, z1)."""
    ax, c, a, b, sg = edge_line(r, e); out = []
    for q in L.ROOMS:
        if q is r or q.get('shape') != 'rect': continue
        if block and q['block'] != block: continue
        qx0, qy0, qx1, qy1 = q['rect']
        if ax == 'y':
            touch = abs((qy1 if sg > 0 else qy0) - c) < 1e-6 if True else False
            touch = (abs(qy1 - c) < EPS and sg > 0) or (abs(qy0 - c) < EPS and sg < 0)
            lo, hi = max(a, qx0), min(b, qx1)
        else:
            touch = (abs(qx1 - c) < EPS and sg > 0) or (abs(qx0 - c) < EPS and sg < 0)
            lo, hi = max(a, qy0), min(b, qy1)
        if touch and hi - lo > 1e-3:
            out.append((q, lo, hi, q['z0'], q['z0'] + q['h']))
    return out


def opposite(e):
    return {'S': 'N', 'N': 'S', 'W': 'E', 'E': 'W'}[e]


def on_block_boundary(r, e):
    ax, c, a, b, sg = edge_line(r, e)
    for s in np.linspace(a + .05, b - .05, 9):
        x, y, _ = P(r, e, s, 0, -.05)
        for q in L.ROOMS:
            if q['block'] == r['block'] and q.get('shape') == 'rect':
                qx0, qy0, qx1, qy1 = q['rect']
                if qx0 < x < qx1 and qy0 < y < qy1:
                    return False
    return True


_TCACHE = {}
def own_t(r, e):
    return L.BLOCKS[r['block']]['t'] if on_block_boundary(r, e) else L.INT_T


def thickness(r, e):
    key = (r['id'], e)
    if key not in _TCACHE:
        t = own_t(r, e)
        for q, *_ in neighbours(r, e):
            t = max(t, own_t(q, opposite(e)))
        _TCACHE[key] = t
    return _TCACHE[key]


def adjacent_edges(e):
    return {'S': ('W', 'E'), 'N': ('W', 'E'), 'W': ('S', 'N'), 'E': ('S', 'N')}[e]


def open_edge(r, e):
    return e in r['special'].get('open_edges', ())


# -------------------------------------------------------------------- openings
def door_edge(d, r):
    """Edge of room r that door d lies on (line shared with the other room / exterior side)."""
    other = d['b'] if d['a'] == r['id'] else d['a']
    if other == 'EXT':
        return d['side']
    q = ROOM.get(other)
    if q is None:  # non-rectangular neighbour (tower via open link edge, tunnel)
        return d.get('side')
    for e in EDGES:
        for n, *_ in neighbours(r, e):
            if n is q:
                return e
    raise ValueError('door %s-%s: rooms do not touch' % (d['a'], d['b']))


def door_z(d, r, other):
    if d['z'] is not None:
        return d['z'] + d.get('sill', 0)
    zz = r['z0'] if other is None else max(r['z0'], other['z0'])
    return zz + d.get('sill', 0)


OPENINGS = {}   # (room id, edge) -> list of dict(s0,s1,z0,z1,kind,door)
WINDOWS = []    # exterior windows (manifest)


def compute_openings():
    OPENINGS.clear(); WINDOWS.clear()
    for d in L.DOORS:
        for rid in (d['a'], d['b']):
            r = ROOM.get(rid)
            if r is None: continue
            e = door_edge(d, r)
            if e is None: continue
            other = ROOM.get(d['b'] if rid == d['a'] else d['a'])
            ax, c, a, b, sg = edge_line(r, e)
            at = d['at'] if d['at'] is not None else (a + b) / 2
            z0 = door_z(d, r, other)
            OPENINGS.setdefault((rid, e), []).append(dict(s0=at - d['w'] / 2, s1=at + d['w'] / 2, z0=z0, z1=z0 + d['h'],
                                                       kind=d['kind'], door=d, ext=(other is None and (d['b'] == 'EXT' or d['a'] == 'EXT'))))
    for r in L.ROOMS:
        if r.get('shape') != 'rect' or not r['windows']: continue
        style = L.BLOCKS[r['block']]['win']
        if style == 'none': continue
        if style == 'palace': style = 'palace7' if r['h'] >= 6.5 else 'palace5'
        w, sill, wh, sp = WIN[style]
        rows = [(sill, wh)]
        if r['h'] >= 10:
            if r['kind'] == 'stair' or r['special'].get('hero'): rows = [(r['h'] - 5.4, 4.0)]
            elif r['block'] == 'palace': rows = [(1.6, 3.6), (r['h'] - 4.8, 3.4)]
            elif r['block'] == 'chapel': rows = [(2.6, 6.0)]
            else: rows = [(1.4, 2.2), (r['h'] - 4.0, 2.2)]
        for e in EDGES:
            if open_edge(r, e): continue
            for (s0, s1, z0, z1) in exterior_pieces(r, e):
                for sill_, wh_ in rows:
                    za = r['z0'] + sill_; zb = za + wh_
                    if za < z0 - 1e-6 or zb > z1 + 1e-6 or za < L.BLOCKS[r['block']]['ground'] + .4: continue
                    length = s1 - s0 - 2.4
                    if length < w: continue
                    n = int(length // sp) + 1
                    span = (n - 1) * sp; start = (s0 + s1) / 2 - span / 2
                    for k in range(n):
                        sc = start + k * sp; a_, b_ = sc - w / 2, sc + w / 2
                        clash = any(o['s0'] - .9 < b_ and a_ < o['s1'] + .9 and o['z0'] < zb and za < o['z1'] for o in OPENINGS.get((r['id'], e), []))
                        if clash: continue
                        o = dict(s0=a_, s1=b_, z0=za, z1=zb, kind='extwindow', door=None, ext=True)
                        OPENINGS.setdefault((r['id'], e), []).append(o)
                        x, y, _ = P(r, e, sc, za, 0)
                        WINDOWS.append({'room': r['id'], 'edge': e, 'center': [round(x, 3), round(y, 3)], 'z': [round(za, 3), round(zb, 3)], 'width': w})


def exterior_pieces(r, e):
    """(s0,s1,z0,z1) regions of edge e not covered by any neighbouring room (any block)."""
    if open_edge(r, e): return []
    ax, c, a, b, sg = edge_line(r, e); z0, z1 = zr(r)
    ground = L.BLOCKS[r['block']]['ground']
    cover = [(lo, hi, nz0, nz1) for q, lo, hi, nz0, nz1 in neighbours(r, e)]
    ss = sorted({a, b} | {v for cv in cover for v in cv[:2] if a < v < b})
    zs = sorted({z0, z1} | {v for cv in cover for v in cv[2:] if z0 < v < z1})
    out = []
    for i in range(len(ss) - 1):
        for j in range(len(zs) - 1):
            sm = (ss[i] + ss[i + 1]) / 2; zm = (zs[j] + zs[j + 1]) / 2
            if any(lo < sm < hi and nz0 < zm < nz1 for lo, hi, nz0, nz1 in cover): continue
            out.append([ss[i], ss[i + 1], zs[j], zs[j + 1]])
    # Extend the lowest above-ground piece down to the plinth level (below terrain).
    plinth = L.BLOCKS[r['block']].get('plinth', 1.5)
    out = [p for p in out if p[3] > ground - plinth + 1e-6]
    for p in out:
        if p[2] <= ground + 2.0: p[2] = ground - plinth
    # merge vertical runs with identical s-range
    out.sort(key=lambda p: (p[0], p[1], p[2])); merged = []
    for p in out:
        if merged and abs(merged[-1][0] - p[0]) < EPS and abs(merged[-1][1] - p[1]) < EPS and abs(merged[-1][3] - p[2]) < 1e-6:
            merged[-1][3] = p[3]
        else: merged.append(list(p))
    return [tuple(p) for p in merged]


# -------------------------------------------------------------------- surfaces
def rect_minus(s0, s1, z0, z1, holes):
    """Decompose rectangle minus holes into sub-rectangles (grid method, rows merged)."""
    hs = [(max(s0, h[0]), min(s1, h[1]), max(z0, h[2]), min(z1, h[3])) for h in holes]
    hs = [h for h in hs if h[1] - h[0] > 1e-4 and h[3] - h[2] > 1e-4]
    ss = sorted({s0, s1} | {v for h in hs for v in h[:2]}); zs = sorted({z0, z1} | {v for h in hs for v in h[2:]})
    out = []
    for j in range(len(zs) - 1):
        run = None
        for i in range(len(ss) - 1):
            sm = (ss[i] + ss[i + 1]) / 2; zm = (zs[j] + zs[j + 1]) / 2
            solid = not any(h[0] < sm < h[1] and h[2] < zm < h[3] for h in hs)
            if solid:
                run = [ss[i], ss[i + 1]] if run is None else [run[0], ss[i + 1]]
            elif run is not None:
                out.append((run[0], run[1], zs[j], zs[j + 1])); run = None
        if run is not None: out.append((run[0], run[1], zs[j], zs[j + 1]))
    return out


def oriented_quad(m, pts, normal, tex, uvs, step=None):
    p = np.asarray(pts, float); n = np.cross(p[1] - p[0], p[3] - p[0])
    if np.dot(n, normal) < 0:
        pts = [pts[1], pts[0], pts[3], pts[2]]; uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
    if step:
        o = np.asarray(pts[0], float); du = np.asarray(pts[1], float) - o; dv = np.asarray(pts[3], float) - o
        k = TEXSCALE.get(tex, 2.0)
        m.grid_quad(o, du, dv, tex, step=step, uvscale=(k, k), uv0=uvs[0])
    else:
        m.quad(*pts, tex, uvs)


def to_local(p, origin):
    return (p[0] - origin[0], p[1] - origin[1], p[2] - origin[2])


def ebox(r, e, s0, s1, z0, z1, off0, off1, origin):
    """Axis-aligned box from edge coordinates -> local lo/hi."""
    a = P(r, e, s0, z0, off0); b = P(r, e, s1, z1, off1)
    lo = [min(a[i], b[i]) - origin[i] for i in range(3)]; hi = [max(a[i], b[i]) - origin[i] for i in range(3)]
    return lo, hi


def wall_side(m, col, r, e, origin, tex, side='in', z0=None, z1=None, s_ext=(0, 0), pieces=None, frame_tex='rf_stone'):
    """Generate one side of edge e: inner (room) side or outer (facade) side."""
    t = thickness(r, e); ax, c, a, b, sg = edge_line(r, e)
    nrm = inward(r, e) if side == 'in' else -inward(r, e)
    face_off = t / 2 if side == 'in' else -t / 2
    ops = OPENINGS.get((r['id'], e), [])
    if side == 'in':
        ta, tb = (thickness(r, x) for x in adjacent_edges(e))
        # adjacent edge order relative to s: for S/N edges s=x so W first; for W/E s=y so S first
        s_lo = a + ta / 2; s_hi = b - tb / 2
        regions = [(s_lo, s_hi, z0, z1)]
    else:
        regions = pieces
    for (rs0, rs1, rz0, rz1) in regions:
        holes = [(o['s0'], o['s1'], o['z0'], o['z1']) for o in ops]
        for (q0, q1, w0, w1) in rect_minus(rs0, rs1, rz0, rz1, holes):
            pts = [P(r, e, q0, w0, face_off), P(r, e, q1, w0, face_off), P(r, e, q1, w1, face_off), P(r, e, q0, w1, face_off)]
            oriented_quad(m, [to_local(p, origin) for p in pts], nrm, tex, uvs_for(tex, q0, q1, w0, w1), step=2.0 if side == 'in' else None)
            lo, hi = ebox(r, e, q0, q1, w0, w1, 0.0, face_off, origin)
            col.box(lo, hi, 'stone')
    # reveals for openings inside regions
    for o in ops:
        inside = any(o['s0'] >= rs0 - 1e-6 and o['s1'] <= rs1 + 1e-6 and o['z0'] >= rz0 - 1e-6 and o['z1'] <= rz1 + 1e-6 for rs0, rs1, rz0, rz1 in regions)
        if not inside: continue
        if o['kind'] == 'secret' and side == 'in' and r['id'] == '21':
            pass
        o0, o1 = (0.0, face_off) if face_off > 0 else (face_off, 0.0)
        rtex = frame_tex
        for s_, nn in ((o['s0'], 1), (o['s1'], -1)):
            sv = np.array((1, 0, 0.)) if ax == 'y' else np.array((0, 1, 0.))
            pts = [P(r, e, s_, o['z0'], o0), P(r, e, s_, o['z0'], o1), P(r, e, s_, o['z1'], o1), P(r, e, s_, o['z1'], o0)]
            oriented_quad(m, [to_local(p, origin) for p in pts], sv * nn, rtex, uvs_for(rtex, o0, o1, o['z0'], o['z1']))
        pts = [P(r, e, o['s0'], o['z1'], o0), P(r, e, o['s1'], o['z1'], o0), P(r, e, o['s1'], o['z1'], o1), P(r, e, o['s0'], o['z1'], o1)]
        oriented_quad(m, [to_local(p, origin) for p in pts], np.array((0, 0, -1.)), rtex, uvs_for(rtex, o['s0'], o['s1'], o0, o1))
        floor_z = r['z0']
        if side == 'out' and o['kind'] in ('arch', 'interactive') and o['z0'] <= floor_z + 0.05:
            pts = [P(r, e, o['s0'], o['z0'], o0), P(r, e, o['s1'], o['z0'], o0), P(r, e, o['s1'], o['z0'], o1), P(r, e, o['s0'], o['z0'], o1)]
            oriented_quad(m, [to_local(p, origin) for p in pts], np.array((0, 0, 1.)), r['floor'], uvs_for(r['floor'], o['s0'], o['s1'], o0, o1))
            lo, hi = ebox(r, e, o['s0'], o['s1'], o['z0'] - .3, o['z0'], o0, o1, origin); col.box(lo, hi, 'stone')
        if o['z0'] > floor_z + 0.05 or o['kind'] in ('extwindow', 'window'):
            pts = [P(r, e, o['s0'], o['z0'], o0), P(r, e, o['s1'], o['z0'], o0), P(r, e, o['s1'], o['z0'], o1), P(r, e, o['s0'], o['z0'], o1)]
            oriented_quad(m, [to_local(p, origin) for p in pts], np.array((0, 0, 1.)), rtex, uvs_for(rtex, o['s0'], o['s1'], o0, o1))
        # Frames (proud 6-8 cm => never coplanar)
        fo = face_off + (0.07 if face_off > 0 else -0.07)
        fa, fb = (face_off, fo) if face_off > 0 else (fo, face_off)
        if o['kind'] in ('arch', 'interactive', 'secret') and not (o['kind'] == 'secret' and r['id'] == '21'):
            ftex = 'rf_stone' if r['wall'] in ('rf_stone', 'rf_dungeon', 'rf_stonedark') or side == 'out' else 'rf_wood'
            for (q0, q1) in ((o['s0'] - .28, o['s0']), (o['s1'], o['s1'] + .28)):
                lo, hi = ebox(r, e, q0, q1, o['z0'], o['z1'] + .3, fa, fb, origin); m.box(lo, hi, ftex, TEXSCALE.get(ftex, 2))
            lo, hi = ebox(r, e, o['s0'] - .34, o['s1'] + .34, o['z1'], o['z1'] + .34, fa, fb, origin); m.box(lo, hi, ftex, TEXSCALE.get(ftex, 2))
        if o['kind'] == 'extwindow':
            ftex = 'rf_stone' if side == 'out' else 'rf_wood'
            for (q0, q1) in ((o['s0'] - .18, o['s0']), (o['s1'], o['s1'] + .18)):
                lo, hi = ebox(r, e, q0, q1, o['z0'] - .12, o['z1'] + .18, fa, fb, origin); m.box(lo, hi, ftex, 2)
            sill_o = fo + (0.16 if face_off > 0 else -0.16)
            lo, hi = ebox(r, e, o['s0'] - .3, o['s1'] + .3, o['z0'] - .16, o['z0'] - .02, *(sorted((face_off, sill_o)) if True else ()), origin); m.box(lo, hi, ftex, 2)
            if side == 'out':
                # pointed hood mould: a shallow gable prism above the window
                hw = (o['s1'] - o['s0']) / 2 + .25; sc = (o['s0'] + o['s1']) / 2; zt = o['z1'] + .18
                for off in (fa, fb):
                    pass
                tri_pts = [P(r, e, sc - hw, zt, fb), P(r, e, sc + hw, zt, fb), P(r, e, sc, zt + hw * .75, fb)]
                pl = [to_local(p, origin) for p in tri_pts]
                pp = np.asarray(pl); n_ = np.cross(pp[1] - pp[0], pp[2] - pp[0])
                if np.dot(n_, nrm) < 0: pl = [pl[1], pl[0], pl[2]]
                m.poly(pl, 'rf_stone', [(0, 0), (1, 0), (.5, .6)])
                # glass pane (two-sided) exactly on the centre-line
                gp = [P(r, e, o['s0'], o['z0'], 0), P(r, e, o['s1'], o['z0'], 0), P(r, e, o['s1'], o['z1'], 0), P(r, e, o['s0'], o['z1'], 0)]
                tex = 'rf_stained' if r['block'] == 'chapel' else 'rf_glass'
                m.poly([to_local(p, origin) for p in gp], tex, uvs_for(tex, o['s0'], o['s1'], o['z0'], o['z1']), two_sided=True)
                lo, hi = ebox(r, e, o['s0'], o['s1'], o['z0'], o['z1'], -0.03, 0.03, origin); col.box(lo, hi, 'glass')
        if o['kind'] == 'window' and side == 'in':
            # interior arcade/balcony: stone balustrade at the sill on the room side
            lo, hi = ebox(r, e, o['s0'], o['s1'], o['z0'], o['z0'] + .95, face_off * .15, face_off, origin)
            m.box(lo, hi, 'rf_stone', 2.0); col.box(lo, hi, 'stone')


def floor_rect(m, col, rect, z, origin, tex, holes=(), up=True, surf='stone', thick=0.3, step=2.0):
    x0, y0, x1, y1 = rect
    for (a, b, c, d) in rect_minus(x0, x1, y0, y1, [(h[0], h[2], h[1], h[3]) for h in holes]):
        k = TEXSCALE.get(tex, 2.0)
        pts = [(a, c, z), (b, c, z), (b, d, z), (a, d, z)]
        oriented_quad(m, [to_local(p, origin) for p in pts], np.array((0, 0, 1. if up else -1.)), tex,
                      [(a / k, c / k), (b / k, c / k), (b / k, d / k), (a / k, d / k)], step=step)
        if col is not None:
            zz = (z - thick, z) if up else (z, z + thick)
            col.box((a - origin[0], c - origin[1], zz[0] - origin[2]), (b - origin[0], d - origin[1], zz[1] - origin[2]), surf)


def rect_floor_round_hole(m, col, rect, c, hole, z, tex, origin, up=True, surf='stone'):
    """Rectangle floor with a 24-gon hole (keep spiral)."""
    hr = hole / math.cos(math.radians(7.5)); sq = hr + .05
    floor_rect(m, col, rect, z, origin, tex, holes=[(c[0] - sq, c[1] - sq, c[0] + sq, c[1] + sq)], up=up, surf=surf)
    ksc = TEXSCALE.get(tex, 2.0)
    for k in range(24):
        a0 = math.radians(15 * k - 7.5); a1 = math.radians(15 * k + 7.5)
        def sqpt(a):
            dx, dy = math.cos(a), math.sin(a); t = sq / max(abs(dx), abs(dy)); return (c[0] + dx * t, c[1] + dy * t)
        i0 = (c[0] + hr * math.cos(a0), c[1] + hr * math.sin(a0)); i1 = (c[0] + hr * math.cos(a1), c[1] + hr * math.sin(a1))
        o0 = sqpt(a0); o1 = sqpt(a1)
        # square corners: split when the segment crosses a corner angle
        corners = [math.radians(45 + 90 * j) for j in range(4)]
        mid = [cc for cc in corners if (a0 < cc < a1) or (a0 < cc + 2 * math.pi < a1)]
        outer = [o0] + [sqpt(mm) for mm in mid] + [o1]
        pts = [(i0[0], i0[1], z)] + [(p[0], p[1], z) for p in outer] + [(i1[0], i1[1], z)]
        loc = [to_local(p, origin) for p in pts]
        pp = np.asarray(loc); n_ = np.cross(pp[1] - pp[0], pp[2] - pp[0])
        if (n_[2] > 0) != up: loc = loc[::-1]
        m.poly(loc, tex, [(p[0] / ksc, p[1] / ksc) for p in (loc if True else pts)])
        if col is not None:
            for j in range(1, len(loc) - 1): col.tri(loc[0], loc[j], loc[j + 1], surf)



def stair_flight(m, col, origin, xa, xb, y0, y1, za, zb, tex, axis='x', side_tex='rf_stone', solid_to=None, open_sides=''):
    """Straight solid flight rising from (xa, za) to (xb, zb) along `axis`; xa/xb may be in any order.
    Mesh: steps (tread + riser + side faces). COL: one inclined ramp + side boxes."""
    n = max(2, int(round(abs(zb - za) / 0.175)))
    rise = (zb - za) / n; run = (xb - xa) / n
    base = solid_to if solid_to is not None else min(za, zb)
    def pt(u, v, z):
        return to_local((u, v, z) if axis == 'x' else (v, u, z), origin)
    for k in range(n):
        u0 = xa + run * k; u1 = u0 + run; ztop = za + rise * (k + 1)
        ulo, uhi = min(u0, u1), max(u0, u1)
        lo = pt(ulo, y0, base); hi = pt(uhi, y1, ztop)
        lo2 = [min(lo[i], hi[i]) for i in range(3)]; hi2 = [max(lo[i], hi[i]) for i in range(3)]
        faces = 'Z'
        # riser faces the low end; sides only toward open space (y0/y1 handled by caller walls)
        if axis == 'x': faces += ('x' if run > 0 else 'X') + open_sides
        else: faces += ('y' if run > 0 else 'Y') + open_sides
        m.box(lo2, hi2, side_tex, TEXSCALE.get(side_tex, 2), faces=faces.replace('Z', ''))
        m.box([lo2[0], lo2[1], hi2[2] - .02], hi2, tex, TEXSCALE.get(tex, 2), faces='Z')
    # COL ramp across the nosings (surface stays within 9 cm of each tread)
    a0 = pt(xa, y0, za + rise * 0.5); a1 = pt(xa, y1, za + rise * 0.5); b1 = pt(xb, y1, zb); b0 = pt(xb, y0, zb)
    col.quad(a0, b0, b1, a1, 'stone')
    lo = pt(min(xa, xb), y0, base); hi = pt(max(xa, xb), y1, min(za, zb) + .15)
    col.box([min(lo[i], hi[i]) for i in range(3)], [max(lo[i], hi[i]) for i in range(3)], 'stone')
    return n


def railing(m, col, origin, p0, p1, z, h=1.0, tex='rf_wood'):
    """Balustrade along an axis-aligned segment p0-p1 at floor z."""
    x0, y0 = p0; x1, y1 = p1; L_ = math.hypot(x1 - x0, y1 - y0)
    if L_ < .1: return
    dx, dy = (x1 - x0) / L_, (y1 - y0) / L_
    n = max(2, int(L_ / .45))
    for k in range(n + 1):
        x = x0 + dx * L_ * k / n; y = y0 + dy * L_ * k / n
        m.box(to_local((x - .04, y - .04, z), origin), to_local((x + .04, y + .04, z + h - .08), origin), tex, 1, faces='xXyY')
    lo = (min(x0, x1) - .07 * abs(dy) - .04 * abs(dx), min(y0, y1) - .07 * abs(dx) - .04 * abs(dy), z + h - .08)
    hi = (max(x0, x1) + .07 * abs(dy) + .04 * abs(dx), max(y0, y1) + .07 * abs(dx) + .04 * abs(dy), z + h)
    m.box(to_local(lo, origin), to_local(hi, origin), tex, 2)
    col.box(to_local((lo[0], lo[1], z), origin), to_local(hi, origin), 'wood')


def inner_rect(r):
    x0, y0, x1, y1 = r['rect']
    return (x0 + thickness(r, 'W') / 2, y0 + thickness(r, 'S') / 2, x1 - thickness(r, 'E') / 2, y1 - thickness(r, 'N') / 2)


STAIRS = []   # manifest records


def build_stair(m, col, r, origin):
    sp = r['special']; ix0, iy0, ix1, iy1 = inner_rect(r); z0 = r['z0']; rise = sp['rise']
    ftex = r['floor']; stex = 'rf_stone' if r['floor'] != 'rf_dungeon' else 'rf_dungeon'
    rec = {'room': r['id'], 'type': sp['stair'], 'from_z': z0, 'to_z': z0 + rise}
    if sp['stair'] == 'U':
        ez = 3.3; gap = .4; fl = round(rise / 2 / .175) * .30
        ym = (iy0 + iy1) / 2
        if sp['entry'] == 'E':
            ze0, ze1 = ix1 - ez, ix1; fs = ze0; fe = ze0 - fl; land = (ix0, fe)
        else:
            ze0, ze1 = ix0, ix0 + ez; fs = ze1; fe = ze1 + fl; land = (fe, ix1)
        assert (land[1] - land[0]) >= 1.6, (r['id'], land)
        # entry floor and full floor under everything at z0 (stairs are solid on top of it)
        floor_rect(m, col, (ix0 - .01, iy0 - .01, ix1 + .01, iy1 + .01), z0, origin, ftex)
        # flight 1 (south half) up to landing, landing block, flight 2 back up to the arrival strip
        n1 = stair_flight(m, col, origin, fs, fe, iy0, ym - gap / 2, z0, z0 + rise / 2, ftex, 'x', stex, solid_to=z0)
        lo = (min(land), iy0, z0); hi = (max(land), iy1, z0 + rise / 2)
        m.box(to_local((lo[0], lo[1], hi[2] - .02), origin), to_local(hi, origin), ftex, 3, faces='Z')
        col.box(to_local(lo, origin), to_local(hi, origin), 'stone')
        n2 = stair_flight(m, col, origin, fe, fs, ym + gap / 2, iy1, z0 + rise / 2, z0 + rise, ftex, 'x', stex, solid_to=z0)
        # central spine wall between flights
        sx0, sx1 = min(fs, fe), max(fs, fe)
        lo = (sx0, ym - gap / 2, z0); hi = (sx1, ym + gap / 2, z0 + rise + 1.0)
        m.box(to_local(lo, origin), to_local(hi, origin), 'rf_stone', 4); col.box(to_local(lo, origin), to_local(hi, origin), 'stone')
        # arrival strip slab over the entry zone
        zt = z0 + rise
        floor_rect(m, col, (ze0, iy0, ze1, iy1), zt, origin, ftex, thick=.4)
        floor_rect(m, None, (ze0, iy0, ze1, iy1), zt - .4, origin, 'rf_plaster', up=False)
        edge_x = ze0 if sp['entry'] == 'E' else ze1
        m.box(to_local((edge_x - .2, iy0, zt - .4), origin), to_local((edge_x + .2, iy1, zt), origin), 'rf_stone', 2, faces='xXz')
        railing(m, col, origin, (edge_x, iy0 + .1), (edge_x, ym - gap / 2), zt, 1.05, 'rf_wood')
        rec.update(entry_zone=[ze0, ze1], landing=list(land), flights=[n1, n2], risers=n1 + n2, riser_h=rise / (n1 + n2), tread=.30)
    else:  # 'I' straight flight: top entry zone at one end on the upper floor
        ez = 3.1; n = int(round(rise / .175)); fl = n * .30; zt = z0 + rise
        if sp['top'] == 'E':
            ze0, ze1 = ix1 - ez, ix1; fs = ze0; fe = ze0 - fl; land = (ix0, fe)
        else:
            ze0, ze1 = ix0, ix0 + ez; fs = ze1; fe = ze1 + fl; land = (fe, ix1)
        assert land[1] - land[0] >= 2.0, (r['id'], land)
        floor_rect(m, col, (min(land) - .01, iy0 - .01, max(land) + .01, iy1 + .01), z0, origin, ftex)
        nn = stair_flight(m, col, origin, fe, fs, iy0, iy1, z0, zt, ftex, 'x', stex, solid_to=z0)
        floor_rect(m, col, (ze0 - .01, iy0, ze1 + .01, iy1), zt, origin, ftex, thick=rise)
        rec.update(entry_zone=[ze0, ze1], landing=list(land), flights=[nn], risers=nn, riser_h=rise / nn, tread=.30)
    STAIRS.append(rec)


def library_gallery(m, col, r, origin):
    ix0, iy0, ix1, iy1 = inner_rect(r); zg = r['z0'] + 7.0
    strips = [(ix0, iy0, ix0 + 2.4, iy1), (ix0 + 2.4, iy1 - 2.4, ix1 - 3.9, iy1), (ix1 - 3.9, iy0, ix1, iy1)]
    for s in strips:
        floor_rect(m, col, s, zg, origin, r['floor'], thick=.4)
        floor_rect(m, None, s, zg - .4, origin, 'rf_wood', up=False)
    # slab edges + railings
    railing(m, col, origin, (ix0 + 2.4, iy0 + .1), (ix0 + 2.4, iy1 - 2.4), zg, 1.0)
    railing(m, col, origin, (ix0 + 2.4, iy1 - 2.4), (ix1 - 3.9, iy1 - 2.4), zg, 1.0)
    railing(m, col, origin, (ix1 - 3.9, iy0 + 1.8), (ix1 - 3.9, iy1 - 2.4), zg, 1.0)
    for (a, b, c, d) in strips:
        m.box(to_local((a, b, zg - .45), origin), to_local((c, d, zg - .4), origin), 'rf_wood', 2, faces='xXyY')
    # oak columns under the gallery corners and every ~6 m
    cols = [(ix0 + 2.4, y) for y in np.arange(iy0 + 4, iy1 - 2.3, 6.0)] + [(ix1 - 3.9, y) for y in np.arange(iy0 + 4, iy1 - 2.3, 6.0)] + \
           [(x, iy1 - 2.4) for x in np.arange(ix0 + 2.4, ix1 - 3.8, 5.0)]
    for (x, y) in cols:
        m.cyl(to_local((x, y, r['z0']), origin), .22, 6.6, 'rf_wood', 8, caps=False)
        col.box(to_local((x - .22, y - .22, r['z0']), origin), to_local((x + .22, y + .22, zg - .4), origin), 'wood')
    # internal stair along the south wall to the east gallery
    n = stair_flight(m, col, origin, ix1 - 3.9 - 40 * .295, ix1 - 3.9, iy0, iy0 + 1.6, r['z0'], zg, 'rf_woodlight', 'x', 'rf_wood', solid_to=r['z0'], open_sides='Y')
    STAIRS.append({'room': r['id'], 'type': 'gallery', 'from_z': r['z0'], 'to_z': zg, 'risers': n, 'riser_h': 7.0 / n, 'tread': .295})
    return strips


def room_shell(r, lights):
    """Shell DFF+COL for one rectangular room. Origin = (centre x, centre y, z0)."""
    x0, y0, x1, y1 = r['rect']; origin = ((x0 + x1) / 2, (y0 + y1) / 2, r['z0'])
    m = Mesh(); col = Collision(); top = r['z0'] + r['h'] - L.SLAB
    for e in EDGES:
        if open_edge(r, e): continue
        wall_side(m, col, r, e, origin, r['wall'], 'in', r['z0'], top, frame_tex='rf_stone' if r['wall'] != 'rf_dungeon' else 'rf_dungeon')
    sp = r['special']
    if 'stair' in sp:
        build_stair(m, col, r, origin)
    else:
        if 'spiral' in sp and r['id'] != 'K0':
            rect_floor_round_hole(m, col, r['rect'], origin[:2], 3.2, r['z0'], r['floor'], origin, surf=SURF_OF.get(r['floor'], 'stone'))
        else:
            floor_rect(m, col, r['rect'], r['z0'], origin, r['floor'], surf=SURF_OF.get(r['floor'], 'stone'))
    ceil_holes = 'spiral' in sp
    if ceil_holes:
        rect_floor_round_hole(m, None, r['rect'], origin[:2], 3.2, top, r['ceil'], origin, up=False)
    else:
        floor_rect(m, None, r['rect'], top, origin, r['ceil'], up=False)
    if not ceil_holes:
        col.box((x0 - origin[0], y0 - origin[1], top - origin[2]), (x1 - origin[0], y1 - origin[1], top + .1 - origin[2]), 'stone')
    if sp.get('gallery'):
        library_gallery(m, col, r, origin)
    return m, col, origin


def facade_pieces_for_block(block):
    out = []
    for r in L.ROOMS:
        if r.get('shape') != 'rect' or r['block'] != block: continue
        for e in EDGES:
            ps = exterior_pieces(r, e)
            if ps: out.append((r, e, ps))
    return out


def facade(block, origin, filt=None):
    """Exterior faces of all rooms of a block (outer half-walls, windows, glass)."""
    m = Mesh(); col = Collision(); tex = L.BLOCKS[block]['facade']
    for r, e, ps in facade_pieces_for_block(block):
        if filt and not filt(r, e): continue
        t = thickness(r, e); ax, c, a, b, sg = edge_line(r, e)
        # extend pieces at convex block corners by t_adj/2 so faces meet at the outer corner
        ext = []
        for (s0, s1, z0, z1) in ps:
            e_lo, e_hi = adjacent_edges(e)
            if abs(s0 - a) < 1e-6 and exterior_pieces(r, e_lo): s0 -= thickness(r, e_lo) / 2
            if abs(s1 - b) < 1e-6 and exterior_pieces(r, e_hi): s1 += thickness(r, e_hi) / 2
            ext.append((s0, s1, z0, z1))
        wall_side(m, col, r, e, origin, tex, 'out', pieces=ext)
    return m, col
