"""Exterior architecture: curtain wall (12 segments, wall walks, access stairs), gatehouse with
passage/portcullis slot, service gate, roofs (palace hipped, gables, flat), eave bands, exterior
perrons for every raised exterior door, courtyards, royal garden, ward outbuildings,
checkpoints, Belvedere pavilion, LOD shells. Every function returns Part records."""
from __future__ import annotations
import math
import numpy as np
from fortlib import Mesh, Collision
import layout as L
import rooms as R
import props as P
import terrain as T
from rooms import to_local, stair_flight, railing, floor_rect, oriented_quad

G = L.G; WZ = L.WALK_Z; Y = L.PALACE_DY
SEG_HALF = L.R_TOWER * math.sin(math.radians(15))          # 42.70: vertex-to-midpoint along an edge
WALL_END = SEG_HALF - 8.4
WT = 4.4                                                    # curtain wall thickness


class Part:
    def __init__(self, name, m, col, origin, rot=0.0, cls='building', alpha=False, lights=None, flames=None, lod=None, room=None):
        self.name = name; self.m = m; self.col = col; self.origin = tuple(float(v) for v in origin); self.rot = float(rot)
        self.cls = cls; self.alpha = alpha; self.lights = lights or []; self.flames = flames or []; self.lod = lod; self.room = room


def rebase(m, col, dz):
    """Shift a mesh/collision built in absolute z by dz (keeps COL coordinates in range)."""
    m.v = [(x, y, z + dz) for (x, y, z) in m.v]
    col.boxes = [([lo[0], lo[1], lo[2] + dz], [hi[0], hi[1], hi[2] + dz], s) for lo, hi, s in col.boxes]
    col.verts = [(x, y, z + dz) for (x, y, z) in col.verts]
    return m, col


def merlons(m, col, x0, x1, y0, y1, z, along='y', h=1.0, w=1.0, gap=1.0, tex='rf_stonedark', origin=(0, 0, 0)):
    a0, a1 = (y0, y1) if along == 'y' else (x0, x1)
    s = a0 + gap / 2
    while s + w <= a1 - gap / 2 + 1e-6:
        lo, hi = ((x0, s, z), (x1, s + w, z + h)) if along == 'y' else ((s, y0, z), (s + w, y1, z + h))
        m.box(to_local(lo, origin), to_local(hi, origin), tex, 4); col.box(to_local(lo, origin), to_local(hi, origin))
        s += w + gap


# ====================================================================== curtain wall
def wall_segment(variant='plain', y_cut=None):
    """Local frame: +x = outward normal, y along the edge, origin = edge midpoint at z=0 (world z)."""
    m = Mesh(); col = Collision(); o = (0, 0, 0); hx = WT / 2; ya, yb = -WALL_END, WALL_END
    pieces = [(ya, yb)] if not y_cut else [(ya, -y_cut), (y_cut, yb)]
    for (a, b) in pieces:
        # body faces (outer, inner), walk surface
        for x, nx in ((hx, 1.), (-hx, -1.)):
            q = [(x, a, G - 1.5), (x, b, G - 1.5), (x, b, WZ), (x, a, WZ)]
            oriented_quad(m, q, np.array((nx, 0, 0.)), 'rf_stone', [(p[1] / 4, p[2] / 4) for p in q])
        floor_rect(m, None, (-hx + .4, a, hx - .6, b), WZ, o, 'rf_cobble')
        col.box((-hx, a, G - 1.5), (hx, b, WZ), 'stone')
        # outer parapet + merlons, inner low wall
        m.box((hx - .6, a, WZ), (hx, b, WZ + 1.2), 'rf_stone', 4, faces='xXZ'); col.box((hx - .6, a, WZ), (hx, b, WZ + 1.2))
        merlons(m, col, hx - .6, hx, a, b, WZ + 1.2, 'y', 1.1, 1.2, 1.0)
        if variant == 'stair':
            for (c0, c1) in ((a, -7.9), (-4.9, b)):
                c0, c1 = max(a, c0), min(b, c1)
                if c1 - c0 > .1:
                    m.box((-hx, c0, WZ), (-hx + .4, c1, WZ + 1.0), 'rf_stone', 4, faces='xXZ'); col.box((-hx, c0, WZ), (-hx + .4, c1, WZ + 1.0))
        else:
            m.box((-hx, a, WZ), (-hx + .4, b, WZ + 1.0), 'rf_stone', 4, faces='xXZ'); col.box((-hx, a, WZ), (-hx + .4, b, WZ + 1.0))
        # string course on the outer face
        m.box((hx, a, WZ - .6), (hx + .25, b, WZ - .3), 'rf_stonedark', 2, faces='XzZ')
    if variant == 'stair':   # flight along the inner face, top landing joins the walk
        n = stair_flight(m, col, o, -25.0, -7.9, -hx - 3.0, -hx, G, WZ, 'rf_stone', 'y', 'rf_stone', solid_to=G - .5, open_sides='x')
        m.box((-hx - 3.0, -7.9, G - .5), (-hx, -4.9, WZ), 'rf_stone', 4, faces='xyYZ'); col.box((-hx - 3.0, -7.9, G - .5), (-hx, -4.9, WZ))
        railing(m, col, o, (-hx - 2.95, -25.0), (-hx - 2.95, -4.95), G, 1.0, 'rf_iron')
        for yy in (-25.0 + 6, -25.0 + 12):
            pass
        railing(m, col, o, (-hx - 3.0, -4.95), (-hx, -4.95), WZ, 1.0, 'rf_iron')
    return m, col


def curtain_wall_parts():
    parts = []
    shared = {'plain': rebase(*wall_segment('plain'), -G), 'stair': rebase(*wall_segment('stair'), -G)}
    for k in range(12):
        nrm = -60 + 30 * k; a = math.radians(nrm); c = (L.APO_WALL * math.cos(a), L.APO_WALL * math.sin(a))
        if k in (2, 11): continue          # service gate (0 deg) and main gate (270 deg) are one-off models
        var = 'stair' if k in (0, 5, 8, 10) else 'plain'
        m, col = shared[var]
        parts.append(Part('wall_' + var, m, col, (c[0], c[1], G), nrm, 'landmark'))
    return parts


def gate_segment(kind):
    """kind 'main' (south, normal 270) or 'service' (east, normal 0). Built in the segment's local frame."""
    m = Mesh(); col = Collision(); o = (0, 0, 0); hx = WT / 2
    if kind == 'main':
        gw = 9.0     # gatehouse half-width along the wall (room 39 spans x -9..9)
        mm, cc = wall_segment('plain', y_cut=gw); m.merge(mm); col.merge(cc)
        # gatehouse lower block (outer face projects 6.75 m, inner 4.15 m from the wall centre-line)
        xo, xi = 6.75, -4.15; pw = 2.6; ph = 7.0
        for (y0, y1) in ((-gw - .75, -pw), (pw, gw + .75)):
            m.box((xi, y0, G - 1.5), (xo, y1, WZ - .35), 'rf_stonedark', 4, faces='xX' + ('y' if y0 < 0 else '') + ('Y' if y1 > 0 else ''))
            col.box((xi, y0, G - 1.5), (xo, y1, WZ - .35))
        m.box((xi, -pw, G + ph), (xo, pw, WZ - .35), 'rf_stonedark', 4, faces='xX'); col.box((xi, -pw, G + ph), (xo, pw, WZ - .35))
        # passage reveals, vault, floor
        for yy, ny in ((-pw, 1.), (pw, -1.)):
            q = [(xi, yy, G), (xo, yy, G), (xo, yy, G + ph), (xi, yy, G + ph)]
            oriented_quad(m, q, np.array((0, ny, 0.)), 'rf_stone', [(p[0] / 4, p[2] / 4) for p in q])
        floor_rect(m, col, (xi, -pw, xo, pw), G + ph, o, 'rf_stone', up=False)
        floor_rect(m, col, (xi, -pw, xo, pw), G + .05, o, 'rf_cobble', surf='paving')
        # portcullis groove (outer third) and murder-hole slot frame
        for yy in (-pw, pw - .25):
            m.box((xo - 2.4, yy, G), (xo - 2.0, yy + .25, G + ph), 'rf_iron', 1, faces='xX')
        # arch voussoirs on both faces
        for xf, nx in ((xo, 1), (xi, -1)):
            for j in range(9):
                t0 = math.pi * j / 9; t1 = math.pi * (j + 1) / 9
                p0 = (pw * math.cos(t0), G + ph - .9 + .9 * math.sin(t0)); p1 = (pw * math.cos(t1), G + ph - .9 + .9 * math.sin(t1))
                q = [(xf, p0[0], p0[1]), (xf, p1[0], p1[1]), (xf, p1[0], G + ph + .6), (xf, p0[0], G + ph + .6)]
                m.poly(q if nx > 0 else q[::-1], 'rf_stone', [(0, 0), (.3, 0), (.3, .3), (0, .3)], two_sided=True)
        # flanking drum towers (solid, conical slate caps) and gatehouse roof parapet
        for sy in (-1, 1):
            cy = sy * (gw + 2.6); cx = 4.2
            m.cyl((cx, cy, G - 1.5), 4.0, WZ + 9.0 - (G - 1.5), 'rf_stonedark', 16, caps=False)
            m.cyl((cx, cy, WZ + 9.0), 4.4, .6, 'rf_stone', 16, caps=True)
            m.cyl((cx, cy, WZ + 9.6), 4.4, 7.0, 'rf_slate', 16, caps=False, r2=0.0)
            m.sphere((cx, cy, WZ + 16.7), .3, 'rf_gold', 6, 4)
            for k in range(8):
                aa = math.radians(22.5 + 45 * k)
                m.box((cx + 3.6 * math.cos(aa) - .2, cy + 3.6 * math.sin(aa) - .5, WZ + 3.0), (cx + 3.6 * math.cos(aa) + .2, cy + 3.6 * math.sin(aa) + .5, WZ + 4.6), 'rf_glass', 1, faces='xXyY') if k % 2 else None
            col.box((cx - 3.6, cy - 3.6, G - 1.5), (cx + 3.6, cy + 3.6, WZ + 9.6))
        # flat crenellated roof above room 39 (room top = WZ + 5)
        zr = WZ + 5.0; x0, x1, y0, y1 = xi - .2, xo + .2, -gw - .95, gw + .95
        floor_rect(m, col, (x0, y0, x1, y1), zr + .3, o, 'rf_slate')
        for (a0, a1, b0, b1) in ((x0, x1, y0, y0 + .6), (x0, x1, y1 - .6, y1), (x0, x0 + .6, y0, y1), (x1 - .6, x1, y0, y1)):
            m.box((a0, b0, zr - .4), (a1, b1, zr + 1.2), 'rf_stonedark', 4); col.box((a0, b0, zr - .4), (a1, b1, zr + 1.2))
        merlons(m, col, x1 - .6, x1, y0, y1, zr + 1.2, 'y', 1.0, 1.0, 1.0)
        merlons(m, col, x0, x0 + .6, y0, y1, zr + 1.2, 'y', 1.0, 1.0, 1.0)
        # royal banners on the outer face
        for sy in (-1, 1):
            q = [(xo + .05, sy * 5.6 - .9, G + 8.0), (xo + .05, sy * 5.6 + .9, G + 8.0), (xo + .05, sy * 5.6 + .9, G + 13.0), (xo + .05, sy * 5.6 - .9, G + 13.0)]
            m.poly([q[2], q[3], q[0], q[1]], 'rf_banner', [(1, 0), (0, 0), (0, 1), (1, 1)][::-1])
        m.box((xo, -3.4, G + ph + .6), (xo + .3, 3.4, G + ph + 1.3), 'rf_stone', 2)
    else:
        gw = 3.0; mm, cc = wall_segment('plain', y_cut=gw); m.merge(mm); col.merge(cc)
        ph = 5.5
        m.box((-hx, -gw, G + ph), (hx, gw, WZ), 'rf_stone', 4, faces='xXz'); col.box((-hx, -gw, G + ph), (hx, gw, WZ))
        floor_rect(m, None, (-hx + .4, -gw, hx - .6, gw), WZ, o, 'rf_cobble')
        m.box((hx - .6, -gw, WZ), (hx, gw, WZ + 1.2), 'rf_stone', 4, faces='Z'); col.box((hx - .6, -gw, WZ), (hx, gw, WZ + 1.2))
        m.box((-hx, -gw, WZ), (-hx + .4, gw, WZ + 1.0), 'rf_stone', 4, faces='Z'); col.box((-hx, -gw, WZ), (-hx + .4, gw, WZ + 1.0))
        merlons(m, col, hx - .6, hx, -gw, gw, WZ + 1.2, 'y', 1.1, 1.2, 1.0)
        for yy, ny in ((-gw, 1.), (gw, -1.)):
            q = [(-hx, yy, G), (hx, yy, G), (hx, yy, G + ph), (-hx, yy, G + ph)]
            oriented_quad(m, q, np.array((0, ny, 0.)), 'rf_stone', [(p[0] / 4, p[2] / 4) for p in q])
        floor_rect(m, col, (-hx, -gw, hx, gw), G + .05, o, 'rf_cobble', surf='paving')
        for sy in (-1, 1):     # buttress-pilasters framing the gate
            m.box((hx, sy * gw - (1.4 if sy < 0 else 0), G - 1.5), (hx + 1.0, sy * gw + (0 if sy < 0 else 1.4), WZ - .6), 'rf_stonedark', 4)
            col.box((hx, sy * gw - (1.4 if sy < 0 else 0), G - 1.5), (hx + 1.0, sy * gw + (0 if sy < 0 else 1.4), WZ - .6))
    return m, col


def gate_parts():
    out = []
    for kind, nrm in (('main', 270.0), ('service', 0.0)):
        m, col = rebase(*gate_segment(kind), -G); a = math.radians(nrm)
        out.append(Part('gate_' + kind, m, col, (L.APO_WALL * math.cos(a), L.APO_WALL * math.sin(a), G), nrm, 'landmark'))
    return out


def wall_towers_parts(furn_fn):
    out = []
    for wt in L.WALL_TOWERS:
        is_watch = wt['id'] == '36'
        out.append(('wall_tower_watch' if is_watch else 'wall_tower', wt, is_watch))
    return out


# ====================================================================== roofs and eave bands
def hipped(m, col, x0, y0, x1, y1, z, h, tex='rf_slate', o=(0, 0, 0)):
    w, d = x1 - x0, y1 - y0
    if d >= w:
        i = w / 2; r0 = (x0 + i, y0 + i, z + h); r1 = (x0 + i, y1 - i, z + h)
        faces = [[(x0, y0, z), (x1, y0, z), r0], [(x1, y0, z), (x1, y1, z), r1, r0], [(x1, y1, z), (x0, y1, z), r1], [(x0, y1, z), (x0, y0, z), r0, r1]]
        ridge = (r0, r1)
    else:
        i = d / 2; r0 = (x0 + i, y0 + i, z + h); r1 = (x1 - i, y0 + i, z + h)
        faces = [[(x0, y0, z), (x1, y0, z), r1, r0], [(x1, y0, z), (x1, y1, z), r1], [(x1, y1, z), (x0, y1, z), r0, r1], [(x0, y1, z), (x0, y0, z), r0]]
        ridge = (r0, r1)
    for f in faces:
        loc = [to_local(p, o) for p in f]
        a = np.array(f[1]) - np.array(f[0]); a /= np.linalg.norm(a); nz = np.array((0, 0, 1.))
        b = np.cross(nz, a)
        uv = [((np.dot(np.array(p), a)) / 3.0, (np.dot(np.array(p)[:2], b[:2]) + (p[2] - z) * 1.2) / 3.0) for p in f]
        m.poly(loc, tex, uv)
        col.tri(loc[0], loc[1], loc[2], 'stone')
        if len(loc) == 4: col.tri(loc[0], loc[2], loc[3], 'stone')
    # soffit underneath the overhang
    m.poly([to_local(p, o) for p in [(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)]], 'rf_wood', [(0, 0), (0, d / 3), (w / 3, d / 3), (w / 3, 0)])
    return ridge


def gable(m, col, x0, y0, x1, y1, z, h, axis='x', tex='rf_slate', wall_tex='rf_stone', o=(0, 0, 0), ov=.6):
    """Ridge along `axis`; gable end walls flush with the building, roof overhang ov."""
    if axis == 'x':
        ym = (y0 + y1) / 2
        for (ya, yb) in ((y0 - ov, ym), (y1 + ov, ym)):
            za = z - ov * h / ((y1 - y0) / 2)
            f = [(x0 - ov, ya, za), (x1 + ov, ya, za), (x1 + ov, yb, z + h), (x0 - ov, yb, z + h)]
            if ya > ym: f = [f[1], f[0], f[3], f[2]]
            m.poly([to_local(p, o) for p in f], tex, [(p[0] / 3, (abs(p[1] - ym)) / 3) for p in f], two_sided=True)
            col.quad(*[to_local(p, o) for p in f], 'stone')
        for xx, s in ((x0, -1), (x1, 1)):
            t = [(xx, y0, z), (xx, y1, z), (xx, ym, z + h)]
            if s < 0: t = [t[1], t[0], t[2]]
            m.poly([to_local(p, o) for p in t], wall_tex, [(p[1] / 4, (p[2] - z) / 4) for p in t]); col.tri(*[to_local(p, o) for p in t])
    else:
        xm = (x0 + x1) / 2
        for (xa, xb) in ((x0 - ov, xm), (x1 + ov, xm)):
            za = z - ov * h / ((x1 - x0) / 2)
            f = [(xa, y1 + ov, za), (xa, y0 - ov, za), (xb, y0 - ov, z + h), (xb, y1 + ov, z + h)]
            if xa > xm: f = [f[1], f[0], f[3], f[2]]
            m.poly([to_local(p, o) for p in f], tex, [(p[1] / 3, abs(p[0] - xm) / 3) for p in f], two_sided=True)
            col.quad(*[to_local(p, o) for p in f], 'stone')
        for yy, s in ((y0, -1), (y1, 1)):
            t = [(x1, yy, z), (x0, yy, z), (xm, yy, z + h)]
            if s < 0: t = [t[1], t[0], t[2]]
            m.poly([to_local(p, o) for p in t], wall_tex, [(p[0] / 4, (p[2] - z) / 4) for p in t]); col.tri(*[to_local(p, o) for p in t])


def band(m, col, x0, y0, x1, y1, za, zb, tex, o, proj=.0):
    """Closed exterior band (frieze) around a rectangle - covers wall-height mismatches."""
    for (a, b, nrm) in (((x0, y0), (x1, y0), (0, -1)), ((x1, y0), (x1, y1), (1, 0)), ((x1, y1), (x0, y1), (0, 1)), ((x0, y1), (x0, y0), (-1, 0))):
        q = [(a[0] + nrm[0] * proj, a[1] + nrm[1] * proj, za), (b[0] + nrm[0] * proj, b[1] + nrm[1] * proj, za),
             (b[0] + nrm[0] * proj, b[1] + nrm[1] * proj, zb), (a[0] + nrm[0] * proj, a[1] + nrm[1] * proj, zb)]
        oriented_quad(m, [to_local(p, o) for p in q], np.array((nrm[0], nrm[1], 0.)), tex, [(0, za / 4), (math.dist(a, b) / 4, za / 4), (math.dist(a, b) / 4, zb / 4), (0, zb / 4)])
    if proj > 0:
        floor_rect(m, None, (x0 - proj, y0 - proj, x1 + proj, y1 + proj), zb, o, tex)
        floor_rect(m, None, (x0 - proj, y0 - proj, x1 + proj, y1 + proj), za, o, tex, up=False)


def chimney(m, col, x, y, z0, z1, o):
    m.box(to_local((x - .7, y - .5, z0), o), to_local((x + .7, y + .5, z1), o), 'rf_stone', 3, faces='xXyY')
    m.box(to_local((x - .85, y - .65, z1), o), to_local((x + .85, y + .65, z1 + .35), o), 'rf_stonedark', 2)
    for dx in (-.35, .35): m.cyl(to_local((x + dx, y, z1 + .35), o), .18, .6, 'rf_copper', 6)
    col.box(to_local((x - .7, y - .5, z0), o), to_local((x + .7, y + .5, z1), o))


def roof_parts():
    parts = []
    t = 1.2; ov = .7; zE = L.L0 + 12.5
    # ---- palace: west wing, central block, east wing; cornice; chimneys; ridge finials
    o = (0.0, 24.0, zE); m = Mesh(); col = Collision()
    x0, y0, x1, y1 = -64 - t / 2, -16 - t / 2, 64 + t / 2, 64 + t / 2
    band(m, col, x0, y0, x1, y1, zE - .5, zE + .05, 'rf_stonedark', o, proj=.45)
    floor_rect(m, col, (x0, y0, x1, y1), zE + .05, o, 'rf_slate')
    rr = []
    rr.append(hipped(m, col, x0 - ov, y0 - ov, -21.5, y1 + ov, zE + .05, 9.0, o=o))
    rr.append(hipped(m, col, -22.5, y0 - ov, 22.5, y1 + ov, zE + .05, 12.0, o=o))
    rr.append(hipped(m, col, 21.5, y0 - ov, x1 + ov, y1 + ov, zE + .05, 9.0, o=o))
    for (a, b) in rr:
        for p in (a, b):
            m.cyl(to_local(p, o), .18, 1.4, 'rf_iron', 6, r2=.05); m.sphere(to_local((p[0], p[1], p[2] + 1.5), o), .25, 'rf_gold', 6, 4)
        n = int(math.dist(a, b) / 3)
        for k in range(n + 1):    # ridge cresting
            pt = [a[i] + (b[i] - a[i]) * k / max(1, n) for i in range(3)]
            m.box(to_local((pt[0] - .08, pt[1] - .08, pt[2]), o), to_local((pt[0] + .08, pt[1] + .08, pt[2] + .5), o), 'rf_iron', 1, faces='xXyY')
    for (cx, cy, top) in ((-52, -6, 7.8), (-52, 46, 7.8), (52, -6, 7.8), (52, 46, 7.8), (-30, 20, 8.6), (30, 20, 8.6), (-12, 52, 10.5), (12, 52, 10.5)):
        chimney(m, col, cx, cy, zE, zE + top, o)
    parts.append(Part('roof_palace', m, col, o, 0, 'landmark'))
    # ---- link roofs, keep passage roof
    m = Mesh(); col = Collision(); o = (0.0, 0.0, zE)
    for key, tw in L.TOWERS.items():
        cx, cy = tw['c']; sgn = 1 if cx > 0 else -1
        xa, xb = (64.6, 66.8) if sgn > 0 else (-66.8, -64.6)
        floor_rect(m, col, (xa, cy - 1.8 - .6, xb, cy + 1.8 + .6), zE + .3, o, 'rf_stone')
        band(m, col, xa, cy - 2.4, xb, cy + 2.4, zE - .3, zE + .3, 'rf_stonedark', o)
        merlons(m, col, xa, xb, cy - 2.4, cy - 1.9, zE + .3, 'x', .9, .8, .6, origin=o); merlons(m, col, xa, xb, cy + 1.9, cy + 2.4, zE + .3, 'x', .9, .8, .6, origin=o)
    zk = L.L0 + 5.0
    floor_rect(m, col, (-3.6, 64.6, 3.6, 69.0), zk + .3, o, 'rf_stone')
    band(m, col, -3.6, 64.6, 3.6, 69.0, zk - .3, zk + .3, 'rf_stonedark', o)
    merlons(m, col, -3.6, -3.1, 64.6, 69.0, zk + .3, 'y', .9, .8, .6, origin=o); merlons(m, col, 3.1, 3.6, 64.6, 69.0, zk + .3, 'y', .9, .8, .6, origin=o)
    parts.append(Part('roof_links', m, col, o, 0, 'building'))
    # ---- barracks (gable along x, H 6) with frieze band covering the upper-floor height mismatch
    bx0, by0, bx1, by1 = L.BX - 24 - .45, L.BY - 12 - .45, L.BX + 24 + .45, L.BY + 12 + .45
    zb = L.BG + 10.0; o = (L.BX, L.BY, zb); m = Mesh(); col = Collision()
    band(m, col, bx0, by0, bx1, by1, L.BG + 9.55, zb + .05, 'rf_stonedark', o, proj=.0)
    floor_rect(m, col, (bx0, by0, bx1, by1), zb + .05, o, 'rf_stonedark')
    gable(m, col, bx0, by0, bx1, by1, zb + .05, 6.0, 'x', wall_tex='rf_stonedark', o=o)
    chimney(m, col, L.BX - 14, L.BY + 4, zb, zb + 5.6, o); chimney(m, col, L.BX + 2, L.BY - 4, zb, zb + 5.6, o)
    parts.append(Part('roof_barracks', m, col, o, 0, 'building'))
    # ---- chapel gable + west bell turret with spire
    cx0, cy0, cx1, cy1 = L.CX - 16 - .5, L.CY - 8 - .5, L.CX + 16 + .5, L.CY + 8 + .5
    zc = G + .6 + 11.0; o = (L.CX, L.CY, zc); m = Mesh(); col = Collision()
    band(m, col, cx0, cy0, cx1, cy1, zc - .4, zc + .05, 'rf_stonedark', o, proj=.3)
    floor_rect(m, col, (cx0, cy0, cx1, cy1), zc + .05, o, 'rf_stone')
    gable(m, col, cx0, cy0, cx1, cy1, zc + .05, 7.5, 'x', o=o)
    bt = (cx0 + 3.0, L.CY)
    m.box(to_local((bt[0] - 2, bt[1] - 2, zc + 3.0), o), to_local((bt[0] + 2, bt[1] + 2, zc + 9.0), o), 'rf_stone', 4, faces='xXyY')
    col.box(to_local((bt[0] - 2, bt[1] - 2, zc + 3.0), o), to_local((bt[0] + 2, bt[1] + 2, zc + 9.0), o))
    for (dx, dy) in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        pass
    m.box(to_local((bt[0] - 2.2, bt[1] - 2.2, zc + 9.0), o), to_local((bt[0] + 2.2, bt[1] + 2.2, zc + 9.4), o), 'rf_stonedark', 2)
    for (px, py) in ((-1.8, -1.8), (1.8, -1.8), (-1.8, 1.8), (1.8, 1.8)):
        m.box(to_local((bt[0] + px - .3, bt[1] + py - .3, zc + 9.4), o), to_local((bt[0] + px + .3, bt[1] + py + .3, zc + 12.4), o), 'rf_stone', 2)
    m.cyl(to_local((bt[0], bt[1], zc + 10.6), o), .75, 1.2, 'rf_bronze', 12, r2=.4)   # bell
    m.box(to_local((bt[0] - 2.3, bt[1] - 2.3, zc + 12.4), o), to_local((bt[0] + 2.3, bt[1] + 2.3, zc + 12.8), o), 'rf_stonedark', 2)
    m.cyl(to_local((bt[0], bt[1], zc + 12.8), o), 2.6, 9.0, 'rf_slate', 8, caps=False, r2=0.0)
    m.box(to_local((bt[0] - .06, bt[1] - .06, zc + 21.8), o), to_local((bt[0] + .06, bt[1] + .06, zc + 24.0), o), 'rf_gold', 1)
    m.box(to_local((bt[0] - .06, bt[1] - .6, zc + 23.0), o), to_local((bt[0] + .06, bt[1] + .6, zc + 23.15), o), 'rf_gold', 1)
    parts.append(Part('roof_chapel', m, col, o, 0, 'landmark', flames=[]))
    return parts


# ====================================================================== perrons (steps to raised exterior doors)
def perrons():
    m = Mesh(); col = Collision(); o = (0.0, 0.0, G); recs = []
    for (rid, e), lst in R.OPENINGS.items():
        r = R.ROOM.get(rid)
        if r is None: continue
        ground = L.BLOCKS[r['block']]['ground']
        for op in lst:
            if not op.get('ext') or op['kind'] in ('extwindow', 'window'): continue
            if r['block'] == 'gatehouse': continue
            rise = op['z0'] - ground
            if rise < .05: continue
            t = R.thickness(r, e); ax, c, a, b, sg = R.edge_line(r, e); face = c - sg * t / 2
            n = max(1, int(round(rise / .17))); run = .32 * n
            wide = 12.0 if rid == '1' else op['s1'] - op['s0'] + 1.6
            sc = (op['s0'] + op['s1']) / 2; s0, s1 = sc - wide / 2, sc + wide / 2
            land = 1.6
            for k in range(n + 1):
                d0 = face - sg * (0 if k == 0 else land + (k - 1) * .32); d1 = face - sg * (land + k * .32)
                if k == n: break
                ztop = op['z0'] - k * rise / n
                lo_d, hi_d = min(face, d1), max(face, d1)
                lo = (s0, lo_d, ground - .3) if ax == 'y' else (lo_d, s0, ground - .3)
                hi = (s1, hi_d, ztop) if ax == 'y' else (hi_d, s1, ztop)
                if k == 0:
                    lo = (s0 - .3, lo_d, ground - .3) if ax == 'y' else (lo_d, s0 - .3, ground - .3)
                    hi = (s1 + .3, hi_d, ztop) if ax == 'y' else (hi_d, s1 + .3, ztop)
                m.box(to_local(lo, o), to_local(hi, o), 'rf_stone' if k else 'rf_marble' if rid == '1' else 'rf_stone', 3, faces='xXyYZ')
                col.box(to_local(lo, o), to_local(hi, o), 'stone')
            if rid == '1':
                for sx in (-1, 1):
                    x = sc + sx * (wide / 2 + .3)
                    m.box(to_local((x - .35, face - sg * (land + run), ground), o), to_local((x + .35, face, op['z0'] + .9), o), 'rf_whitemarble', 2)
                    col.box(to_local((x - .35, min(face, face - sg * (land + run)), ground), o), to_local((x + .35, max(face, face - sg * (land + run)), op['z0'] + .9), o))
            recs.append({'room': rid, 'edge': e, 'risers': n, 'rise': round(rise, 3), 'width': wide})
    return Part('perrons', m, col, o, 0, 'building'), recs


# ====================================================================== courtyards, garden, ward
def paved(m, col, x0, y0, x1, y1, tex='rf_cobble', z=G, h=.08, o=(0, 0, G), kerb='rf_stonedark'):
    m.box(to_local((x0, y0, z - .2), o), to_local((x1, y1, z + h), o), kerb, 2, faces='xXyY')
    floor_rect(m, None, (x0, y0, x1, y1), z + h, o, tex, step=8.0)
    col.box(to_local((x0, y0, z - .2), o), to_local((x1, y1, z + h), o), 'paving' if tex == 'rf_cobble' else 'gravel')


def fountain(r=4.0, tiers=2):
    p = P.Prop()
    p.m.cyl((0, 0, 0), r, .7, 'rf_stone', 20, caps=False); p.m.cyl((0, 0, .7), r + .25, .12, 'rf_stonedark', 20, caps=False, r2=r + .25)
    p.m.cyl((0, 0, .82), r + .25, .001, 'rf_stonedark', 20, caps=False, r2=r - .25)
    p.m.cyl((0, 0, .55), r - .25, .001, 'rf_waterfx', 20, caps=True)
    p.m.cyl((0, 0, .1), r - .25, .6, 'rf_stone', 20, caps=False, inside=True)
    for k in range(tiers):
        rr = r * (.45 - .17 * k); z = 1.4 + k * 1.3
        p.m.cyl((0, 0, .55), .35 - .08 * k, z - .5, 'rf_whitemarble', 10, caps=False)
        p.m.cyl((0, 0, z - .2), rr * .4, .25, 'rf_whitemarble', 14, caps=False, r2=rr)
        p.m.cyl((0, 0, z + .05), rr, .001, 'rf_waterfx', 14, caps=True)
    p.m.sphere((0, 0, 1.4 + tiers * 1.3), .3, 'rf_gold', 8, 5)
    for k in range(20):
        a0 = 2 * math.pi * k / 20; a1 = 2 * math.pi * (k + 1) / 20
        for z0, z1 in ((0, .82),):
            pass
    for k in range(16):
        a = 2 * math.pi * k / 16
        p.c.box((r * math.cos(a) - .45, r * math.sin(a) - .45, 0), (r * math.cos(a) + .45, r * math.sin(a) + .45, .82), 'stone')
    p.c.box((-.6, -.6, 0), (.6, .6, 2.6), 'stone')
    return p


def hedge_box(x0, y0, x1, y1, h=1.1):
    p = P.Prop(); p.box((x0, y0, 0), (x1, y1, h), 'rf_hedge', uv=3.0, faces='xXyYZ', surf='grass'); return p


def outbuilding(w, d, h, roof_h, name, wall='rf_stone', door_side='S', windows=True):
    """Closed (non-enterable) ward building in a local frame centred on its footprint."""
    m = Mesh(); col = Collision(); o = (0, 0, 0)
    x0, y0, x1, y1 = -w / 2, -d / 2, w / 2, d / 2
    m.box((x0, y0, -1.0), (x1, y1, h), wall, 4, faces='xXyY'); col.box((x0, y0, -1.0), (x1, y1, h))
    m.box((x0 - .15, y0 - .15, -1.0), (x1 + .15, y1 + .15, .6), 'rf_stonedark', 3, faces='xXyY')
    gable(m, col, x0, y0, x1, y1, h, roof_h, 'x' if w >= d else 'y', wall_tex=wall, o=o)
    # door (static leaves) + windows on the long sides
    ds = {'S': (0, y0, (0, -1)), 'N': (0, y1, (0, 1))}[door_side]
    dw = min(3.4, w * .3)
    m.box((-dw / 2 - .25, ds[1] - .06 if door_side == 'S' else ds[1] - .04, 0), (dw / 2 + .25, ds[1] + (.04 if door_side == 'S' else .06), 3.4), 'rf_stone', 2, faces='yY')
    yd = ds[1] - .08 if door_side == 'S' else ds[1] + .08
    m.poly([(-dw / 2, yd, 0), (dw / 2, yd, 0), (dw / 2, yd, 3.0), (-dw / 2, yd, 3.0)], 'rf_wood', [(0, 0), (1, 0), (1, 1.5), (0, 1.5)], two_sided=True)
    if windows:
        for yy, sg in ((y0, -1), (y1, 1)):
            for xx in np.arange(x0 + 2.5, x1 - 2.0, 3.5):
                if abs(xx) < dw / 2 + 1.0 and ((door_side == 'S' and sg < 0) or (door_side == 'N' and sg > 0)): continue
                q = [(xx - .6, yy + sg * .03, 1.6), (xx + .6, yy + sg * .03, 1.6), (xx + .6, yy + sg * .03, 3.0), (xx - .6, yy + sg * .03, 3.0)]
                m.poly(q if sg < 0 else [q[1], q[0], q[3], q[2]], 'rf_glass', [(0, 0), (1, 0), (1, 1), (0, 1)])
                m.box((xx - .75, yy + (sg * .0 if sg > 0 else -.12), 1.45), (xx + .75, yy + (.12 if sg > 0 else 0), 1.6), 'rf_stonedark', 1, faces='xXyYZ')
    return m, col


WARD = [  # name, centre, w, d, wall h, roof h, wall tex, door side, rot
    ('Royal Stables', (-132.0, 22.0), 36.0, 12.0, 5.0, 4.5, 'rf_stone', 'S'),
    ('Tack & Hay Barn', (-104.0, 40.0), 14.0, 10.0, 6.0, 4.0, 'rf_woodlight', 'S'),
    ('Smithy & Workshops', (122.0, -46.0), 26.0, 10.0, 5.0, 4.0, 'rf_stone', 'N'),
    ('Granary', (120.0, 46.0), 22.0, 12.0, 7.0, 5.0, 'rf_stonedark', 'S'),
    ('Bakehouse & Outer Kitchen', (100.0, -12.0), 16.0, 10.0, 5.0, 3.5, 'rf_plaster', 'S'),
    ('Guard Post West', (-60.0, -142.0), 8.0, 6.0, 4.0, 3.0, 'rf_stonedark', 'N'),
    ('Guard Post East', (60.0, -142.0), 8.0, 6.0, 4.0, 3.0, 'rf_stonedark', 'N'),
    ('Carpenter Workshop', (138.0, -16.0), 12.0, 10.0, 5.0, 3.5, 'rf_woodlight', 'S'),
]


def ward_parts():
    parts = []
    for (name, c, w, d, h, rh, wall, ds) in WARD:
        m, col = outbuilding(w, d, h, rh, name, wall, ds)
        parts.append(Part('ward_' + name.split()[0].lower() + '_' + name.split()[-1].lower(), m, col, (c[0], c[1], G), 0, 'building'))
    return parts


def courtyard_parts():
    """Ceremonial avenue + parade square + palace forecourt fountains; military yard; service yard;
    royal garden parterres, fountain, cypresses and statues around the keep."""
    out = []
    # --- ceremonial courtyard (south)
    m = Mesh(); col = Collision(); o = (0.0, -90.0, G); lights = []; flames = []
    paved(m, col, -5.5, -152.0, 5.5, -60.0, o=o)
    paved(m, col, -46.0, -60.0, 46.0, -19.4, o=o)
    paved(m, col, -4.5, -172.0, 4.5, -166.2, o=o)
    paved(m, col, -4.5, -155.2, 4.5, -152.0, o=o)
    for sx in (-1, 1):
        f = fountain(5.0, 2); m.merge(f.m, to_local((sx * 26.0, -40.0, G + .08), o)); col.merge(f.c.transformed(to_local((sx * 26.0, -40.0, G + .08), o)))
        for y in np.arange(-146.0, -62.0, 12.0):
            lp = P.lantern_post(3.8); m.merge(lp.m, to_local((sx * 7.0, y, G), o)); col.merge(lp.c.transformed(to_local((sx * 7.0, y, G), o)))
            flames += [dict(fl, pos=[fl['pos'][0] + sx * 7.0, fl['pos'][1] + y, fl['pos'][2] + G]) for fl in lp.flames]
            if int(abs(y)) % 24 == 2:
                st = P.statue('rf_whitemarble', 1.0, 1.2); m.merge(st.m, to_local((sx * 10.5, y + 6, G), o), 90 * -sx); col.merge(st.c.transformed(to_local((sx * 10.5, y + 6, G), o), 90 * -sx))
        for y in (-58.0, -21.0):
            st = P.statue('rf_bronze', 1.3, 1.6); m.merge(st.m, to_local((sx * 44.0, y, G + .08), o)); col.merge(st.c.transformed(to_local((sx * 44.0, y, G + .08), o)))
    out.append(Part('court_ceremonial', m, col, o, 0, 'building', flames=flames))
    # --- military courtyard (west): training yard, well, archery butts, pillory
    m = Mesh(); col = Collision(); o = (-118.0, -80.0, G)
    paved(m, col, -150.0, -112.0, -86.0, -58.0, 'rf_dirt', h=.05, o=o)
    paved(m, col, -136.5, -58.0, -87.5, -52.6, 'rf_cobble', o=o)
    for (x, y, rot, fn) in ((-140, -70, 0, P.dummy), (-134, -70, 0, P.dummy), (-128, -70, 0, P.dummy), (-100, -106, 180, P.target), (-108, -106, 180, P.target),
                            (-116, -106, 180, P.target), (-95, -66, 90, lambda: P.weapon_rack(2.4)), (-145, -95, 0, P.pillory), (-120, -88, 0, P.brazier)):
        p = fn(); m.merge(p.m, to_local((x, y, G + .05), o), rot); col.merge(p.c.transformed(to_local((x, y, G + .05), o), rot))
    well = P.Prop(); well.m.cyl((0, 0, 0), 1.4, 1.0, 'rf_stone', 14, caps=False); well.m.cyl((0, 0, .3), 1.15, .7, 'rf_stone', 14, caps=False, inside=True)
    well.m.cyl((0, 0, .5), 1.15, .001, 'rf_waterfx', 14); well.m.box((-1.5, -.1, 1.0), (-1.3, .1, 2.8), 'rf_wood', 1); well.m.box((1.3, -.1, 1.0), (1.5, .1, 2.8), 'rf_wood', 1)
    well.m.box((-1.5, -.12, 2.6), (1.5, .12, 2.8), 'rf_wood', 1); well.c.box((-1.4, -1.4, 0), (1.4, 1.4, 1.0))
    m.merge(well.m, to_local((-118, -96, G + .05), o)); col.merge(well.c.transformed(to_local((-118, -96, G + .05), o)))
    out.append(Part('court_military', m, col, o, 0, 'building'))
    # --- service yard (east, inside the service gate)
    m = Mesh(); col = Collision(); o = (125.0, 0.0, G)
    paved(m, col, 90.0, -36.0, 156.0, 32.0, 'rf_cobble', o=o)
    for (x, y, fn, rot) in ((146, 22, P.crate, 0), (148, 20, P.crate, 0), (146, -26, P.barrel, 0), (148, -27, P.barrel, 0), (144, -28, P.barrel, 0), (110, 26, P.sack, 0), (111, 27, P.sack, 0), (132, -30, P.barrel, 0)):
        p = fn(); m.merge(p.m, to_local((x, y, G + .08), o), rot); col.merge(p.c.transformed(to_local((x, y, G + .08), o), rot))
    out.append(Part('court_service', m, col, o, 0, 'building'))
    # --- royal garden (north, around the keep): gravel paths, parterre hedges, fountain, cypresses, statues, lamps
    m = Mesh(); col = Collision(); o = (0.0, 120.0, G); flames = []
    alpha = Mesh(); acol = Collision()
    paved(m, col, -3.0, 95.6, 3.0, 146.0, 'rf_gravel', h=.05, o=o)
    paved(m, col, -70.0, 116.0, 70.0, 121.0, 'rf_gravel', h=.05, o=o)
    paved(m, col, -10.0, 108.5, 10.0, 128.5, 'rf_gravel', h=.06, o=o)
    f = fountain(6.0, 3); m.merge(f.m, to_local((0, 118.5, G + .06), o)); col.merge(f.c.transformed(to_local((0, 118.5, G + .06), o)))
    for sx in (-1, 1):
        for (xa, xb) in ((14, 30), (34, 50), (54, 66)):
            for (ya, yb) in ((100, 114), (123, 140)):
                X0, X1 = sorted((sx * xa, sx * xb))
                for (a0, a1, b0, b1) in ((X0, X1, ya, ya + .8), (X0, X1, yb - .8, yb), (X0, X0 + .8, ya + .8, yb - .8), (X1 - .8, X1, ya + .8, yb - .8)):
                    hb = hedge_box(a0, b0, a1, b1); m.merge(hb.m, to_local((0, 0, G), o)); col.merge(hb.c.transformed(to_local((0, 0, G), o)))
                fl = P.Prop(); fl.m.box((X0 + .8, ya + .8, 0), (X1 - .8, yb - .8, .25), 'rf_flowers', 2.0, faces='xXyYZ')
                m.merge(fl.m, to_local((0, 0, G), o))
                ct = T.tree('cypress', 1.0)
                for (cx, cy) in ((X0, ya - 1.6), (X1, ya - 1.6), (X0, yb + 1.6), (X1, yb + 1.6)):
                    if abs(cy - 118.5) < 4: continue
                    alpha.merge(ct.m, to_local((cx, cy, G), o)); acol.merge(ct.c.transformed(to_local((cx, cy, G), o)))
        for y in (104.0, 134.0):
            st = P.statue('rf_whitemarble', .95, 1.0); m.merge(st.m, to_local((sx * 6.5, y, G), o), -90 * sx); col.merge(st.c.transformed(to_local((sx * 6.5, y, G), o), -90 * sx))
        for x in (20.0, 40.0, 60.0):
            lp = P.lantern_post(3.2); m.merge(lp.m, to_local((sx * x, 114.5, G), o)); col.merge(lp.c.transformed(to_local((sx * x, 114.5, G), o)))
            flames += [dict(fl, pos=[fl['pos'][0] + sx * x, fl['pos'][1] + 114.5, fl['pos'][2] + G]) for fl in lp.flames]
    out.append(Part('garden_royal', m, col, o, 0, 'building', flames=flames))
    out.append(Part('garden_cypress', alpha, acol, o, 0, 'tree', alpha=True))
    return out


def checkpoint_parts():
    out = []
    for road, (x, y) in T.CHECKPOINTS:
        d = T.ROAD_DATA[road]; pts = np.asarray(d['pts']); i = int(np.argmin(np.hypot(pts[:, 0] - x, pts[:, 1] - y)))
        i0, i1 = max(0, i - 2), min(len(pts) - 1, i + 2)
        ang = math.degrees(math.atan2(pts[i1][1] - pts[i0][1], pts[i1][0] - pts[i0][0]))
        z = d['z'][i]; hw = d['w'] / 2
        m = Mesh(); col = Collision(); o = (0, 0, 0); flames = []
        gm, gc = outbuilding(4.0, 4.0, 3.0, 2.2, 'guardhouse', 'rf_stonedark', 'N', windows=False)
        m.merge(gm, (0, hw + 3.6, 0)); col.merge(gc.transformed((0, hw + 3.6, 0)))
        for sy in (-1, 1):
            m.box((-.3, sy * (hw + .6) - .3, 0), (.3, sy * (hw + .6) + .3, 1.3), 'rf_stone', 2); col.box((-.3, sy * (hw + .6) - .3, 0), (.3, sy * (hw + .6) + .3, 1.3))
        for k in range(int(2 * hw / .5)):
            m.box((-.06, -hw + k * .5, 1.0), (.06, -hw + k * .5 + .5, 1.15), 'rf_fabricred' if k % 2 else 'rf_candle', 1)
        b = P.brazier(); m.merge(b.m, (2.0, hw + 1.6, 0)); col.merge(b.c.transformed((2.0, hw + 1.6, 0)))
        flames += [dict(f, pos=[f['pos'][0] + 2.0, f['pos'][1] + hw + 1.6, f['pos'][2]]) for f in b.flames]
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        wf = [dict(f, pos=[x + f['pos'][0] * ca - f['pos'][1] * sa, y + f['pos'][0] * sa + f['pos'][1] * ca, z + f['pos'][2]]) for f in flames]
        out.append(Part('checkpoint', m, col, (x, y, z), ang, 'building', flames=wf))
    return out


def belvedere_part(bz):
    m = Mesh(); col = Collision(); o = (0, 0, 0)
    paved(m, col, -13, -13, 13, 13, 'rf_cobble', z=0.0, h=.12, o=(0, 0, 0))
    m.cyl((0, 0, .12), 7.0, .6, 'rf_whitemarble', 24, caps=True); col.box((-6.6, -6.6, 0), (6.6, 6.6, .72))
    for k in range(10):
        a = 2 * math.pi * k / 10; x, y = 5.6 * math.cos(a), 5.6 * math.sin(a)
        m.cyl((x, y, .72), .32, 4.6, 'rf_whitemarble', 10, caps=False); col.box((x - .32, y - .32, .72), (x + .32, y + .32, 5.3))
    m.cyl((0, 0, 5.3), 6.4, .6, 'rf_whitemarble', 24, caps=True)
    m.sphere((0, 0, 5.9), 6.0, 'rf_bronze', 20, 6, sz=.55)
    m.sphere((0, 0, 9.4), .4, 'rf_gold', 8, 5)
    for sx, sy, ex, ey in ((-12.9, -12.9, 12.9, -12.9), (12.9, -12.9, 12.9, 12.9), (12.9, 12.9, -12.9, 12.9), (-12.9, 12.9, -12.9, -2.5)):
        railing(m, col, (0, 0, 0), (sx, sy), (ex, ey), .12, 1.05, 'rf_whitemarble')
    for (x, y) in ((-10, -10), (10, -10), (10, 10), (-10, 10)):
        b = P.bench(2.4, 'rf_whitemarble'); m.merge(b.m, (x, y, .12), 45 if x * y > 0 else -45)
    lp = P.lantern_post(3.4); flames = []
    for (x, y) in ((-12.0, -4.0), (-12.0, 4.0)):
        m.merge(lp.m, (x, y, .12)); col.merge(lp.c.transformed((x, y, .12)))
        flames += [dict(f, pos=[f['pos'][0] + x + T.BELVEDERE[0], f['pos'][1] + y + T.BELVEDERE[1], f['pos'][2] + bz + .12]) for f in lp.flames]
    return Part('belvedere', m, col, (T.BELVEDERE[0], T.BELVEDERE[1], bz), 0, 'landmark', flames=flames)


# ====================================================================== LOD shells (far distance)
def lod_palace():
    m = Mesh(); o = (0.0, 24.0, L.L0)
    m.box(to_local((-64.6, -16.6, G - 1.5), o), to_local((64.6, 64.6, L.L0 + 12.5), o), 'rf_stone', 6, faces='xXyY')
    for (x0, x1, h) in ((-65.3, -21.5, 9.0), (-22.5, 22.5, 12.0), (21.5, 65.3, 9.0)):
        hipped(m, Collision(), x0, -17.3, x1, 65.3, L.L0 + 12.55, h, o=o)
    for key, t in L.TOWERS.items():
        cx, cy = t['c']; m.cyl(to_local((cx, cy, G - 1.5), o), 8.0, L.L0 + 18.5 - G + 1.5, 'rf_stone', 10, caps=False)
        m.cyl(to_local((cx, cy, L.L0 + 18.5), o), 8.6, 12.5, 'rf_slate', 10, caps=False, r2=0)
    m.box(to_local((-15, 69, G - 1.5), o), to_local((15, 95, L.L0 + 21), o), 'rf_stonedark', 6, faces='xXyYZ')
    m.cyl(to_local((0, 82, L.L0 + 21), o), 4.4, 7.8, 'rf_slate', 8, caps=False, r2=0)
    return m, o


def lod_wall():
    m = Mesh(); o = (0, 0, 0)   # absolute z; rebased by the caller
    for k in range(12):
        a = math.radians(-60 + 30 * k); nx, ny = math.cos(a), math.sin(a); tx, ty = -ny, nx
        c = (L.APO_WALL * nx, L.APO_WALL * ny)
        for xo, sg in ((WT / 2, 1), (-WT / 2, -1)):
            q = [(c[0] + nx * xo - tx * SEG_HALF, c[1] + ny * xo - ty * SEG_HALF, G - 1.5), (c[0] + nx * xo + tx * SEG_HALF, c[1] + ny * xo + ty * SEG_HALF, G - 1.5),
                 (c[0] + nx * xo + tx * SEG_HALF, c[1] + ny * xo + ty * SEG_HALF, WZ + 1.8), (c[0] + nx * xo - tx * SEG_HALF, c[1] + ny * xo - ty * SEG_HALF, WZ + 1.8)]
            oriented_quad(m, q, np.array((nx * sg, ny * sg, 0.)), 'rf_stone', [(0, 0), (SEG_HALF / 3, 0), (SEG_HALF / 3, 4), (0, 4)])
    for wt in L.WALL_TOWERS:
        cx, cy = wt['c']; m.cyl((cx, cy, G - 1.5), 9.0, WZ + 6 - G + 1.5, 'rf_stonedark', 10, caps=False); m.cyl((cx, cy, WZ + 6), 9.6, 13, 'rf_slate', 10, caps=False, r2=0)
    return m, o
