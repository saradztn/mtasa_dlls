"""Round towers (24-gon, apothem-exact door edges), spiral stairs, wall towers, keep roof,
escape tunnel. All rooms built here are registered in POLY_ROOMS for the manifest."""
from __future__ import annotations
import math
import numpy as np
from fortlib import Mesh, Collision
import layout as L
from rooms import TEXSCALE, oriented_quad, to_local, rect_minus, railing, floor_rect, rect_floor_round_hole

N = 24
POLY_ROOMS = []   # manifest records for non-rectangular rooms
SPIRALS = []


def pol(c, apo, k, frac):
    """Point on the polygon with apothem `apo`; edge k (normal angle 15k deg), frac -1..1 along the edge."""
    a = math.radians(15 * k); half = apo * math.tan(math.radians(7.5))
    nx, ny = math.cos(a), math.sin(a); tx, ty = -ny, nx
    return (c[0] + nx * apo + tx * half * frac, c[1] + ny * apo + ty * half * frac)


def edge_quad(m, col, c, k, apo, z0, z1, tex, inside, origin, s_rng=(-1, 1), colsurf='stone'):
    a = pol(c, apo, k, s_rng[0]); b = pol(c, apo, k, s_rng[1])
    pts = [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
    nrm = np.array((math.cos(math.radians(15 * k)), math.sin(math.radians(15 * k)), 0.)) * (-1 if inside else 1)
    half = apo * math.tan(math.radians(7.5)); ksc = TEXSCALE.get(tex, 2.0)
    s0 = (k * 2 * half + half * (s_rng[0] + 1)); s1 = (k * 2 * half + half * (s_rng[1] + 1))
    uvs = [(s0 / ksc, z0 / ksc), (s1 / ksc, z0 / ksc), (s1 / ksc, z1 / ksc), (s0 / ksc, z1 / ksc)]
    oriented_quad(m, [to_local(p, origin) for p in pts], nrm, tex, uvs)
    if col is not None:
        q = [to_local(p, origin) for p in pts]; col.quad(q[0], q[1], q[2], q[3], colsurf)


def poly_wall(m, col, c, apo_in, apo_out, z0, z1, tex_in, tex_out, origin, openings, do_in=True, do_out=True, out_skip=()):
    """Tower wall ring. openings: {edge k: [(w, za, zb, kind)]}; out_skip: edges with no outer face (links)."""
    for k in range(N):
        ops = openings.get(k % N, [])
        for side, apo, tex in (('in', apo_in, tex_in), ('out', apo_out, tex_out)):
            if (side == 'in' and not do_in) or (side == 'out' and (not do_out or k in out_skip)): continue
            half = apo * math.tan(math.radians(7.5))
            holes = [(-w / 2 / half, w / 2 / half, za, zb) for (w, za, zb, kind) in ops]
            for (f0, f1, w0, w1) in rect_minus(-1, 1, z0, z1, holes):
                edge_quad(m, col, c, k, apo, w0, w1, tex, side == 'in', origin, (f0, f1))
        a = math.radians(15 * k); nx, ny = math.cos(a), math.sin(a); tx, ty = -ny, nx
        for (w, za, zb, kind) in ops:
            # reveals through the full thickness (both halves belong to this tower)
            for sgn in (-1, 1):
                s = sgn * w / 2
                p0 = (c[0] + nx * apo_in + tx * s, c[1] + ny * apo_in + ty * s); p1 = (c[0] + nx * apo_out + tx * s, c[1] + ny * apo_out + ty * s)
                pts = [(p0[0], p0[1], za), (p1[0], p1[1], za), (p1[0], p1[1], zb), (p0[0], p0[1], zb)]
                oriented_quad(m, [to_local(p, origin) for p in pts], np.array((-tx * sgn, -ty * sgn, 0.)), 'rf_stone', [(0, 0), (.6, 0), (.6, (zb - za) / 3), (0, (zb - za) / 3)])
            for zz, nz in ((zb, -1.), (za, 1.)):
                if nz > 0 and kind == 'door': continue
                q = [(c[0] + nx * apo_in - tx * w / 2, c[1] + ny * apo_in - ty * w / 2, zz), (c[0] + nx * apo_in + tx * w / 2, c[1] + ny * apo_in + ty * w / 2, zz),
                     (c[0] + nx * apo_out + tx * w / 2, c[1] + ny * apo_out + ty * w / 2, zz), (c[0] + nx * apo_out - tx * w / 2, c[1] + ny * apo_out - ty * w / 2, zz)]
                oriented_quad(m, [to_local(p, origin) for p in q], np.array((0, 0, nz)), 'rf_stone', [(0, 0), (1, 0), (1, .5), (0, .5)])
            if kind == 'door':
                q = [(c[0] + nx * apo_in - tx * w / 2, c[1] + ny * apo_in - ty * w / 2, za), (c[0] + nx * apo_in + tx * w / 2, c[1] + ny * apo_in + ty * w / 2, za),
                     (c[0] + nx * apo_out + tx * w / 2, c[1] + ny * apo_out + ty * w / 2, za), (c[0] + nx * apo_out - tx * w / 2, c[1] + ny * apo_out - ty * w / 2, za)]
                oriented_quad(m, [to_local(p, origin) for p in q], np.array((0, 0, 1.)), 'rf_stone', [(0, 0), (1, 0), (1, .5), (0, .5)])
                if col is not None:
                    ql = [to_local(p, origin) for p in q]; col.quad(ql[0], ql[1], ql[2], ql[3], 'stone')
            if kind == 'window' and do_out:
                q = [(c[0] + nx * (apo_in + apo_out) / 2 + tx * s, c[1] + ny * (apo_in + apo_out) / 2 + ty * s, z) for s, z in ((-w / 2, za), (w / 2, za), (w / 2, zb), (-w / 2, zb))]
                m.poly([to_local(p, origin) for p in q], 'rf_glass', [(0, 0), (w / 1.6, 0), (w / 1.6, (zb - za) / 1.6), (0, (zb - za) / 1.6)], two_sided=True)


def disc(m, col, c, apo, z, tex, origin, up=True, hole=0.0, surf='stone'):
    """24-gon floor/ceiling at z; optional round hole of radius `hole` (24-gon)."""
    rr = apo / math.cos(math.radians(7.5)); ksc = TEXSCALE.get(tex, 2.0)
    for k in range(N):
        a0 = math.radians(15 * k - 7.5); a1 = math.radians(15 * k + 7.5)
        o0 = (c[0] + rr * math.cos(a0), c[1] + rr * math.sin(a0)); o1 = (c[0] + rr * math.cos(a1), c[1] + rr * math.sin(a1))
        if hole > 0:
            hr = hole / math.cos(math.radians(7.5))
            i0 = (c[0] + hr * math.cos(a0), c[1] + hr * math.sin(a0)); i1 = (c[0] + hr * math.cos(a1), c[1] + hr * math.sin(a1))
            pts = [(i0[0], i0[1], z), (o0[0], o0[1], z), (o1[0], o1[1], z), (i1[0], i1[1], z)]
        else:
            pts = [(c[0], c[1], z), (o0[0], o0[1], z), (o1[0], o1[1], z), (c[0] + 1e-3 * math.cos(a1), c[1] + 1e-3 * math.sin(a1), z)]
        uvs = [(p[0] / ksc, p[1] / ksc) for p in pts]
        oriented_quad(m, [to_local(p, origin) for p in pts], np.array((0, 0, 1. if up else -1.)), tex, uvs)
        if col is not None:
            q = [to_local(p, origin) for p in pts]; col.quad(q[0], q[1], q[2], q[3], surf)


def spiral(m, col, c, z0, z1, a_start, origin, turns=None, r_in=.6, r_out=3.0, tex='rf_stone', steps_per_turn=28, rail=True):
    rise = z1 - z0; turns = turns or (1.25 if rise > 6 else 1.0)
    n = int(round(steps_per_turn * turns)); da = 2 * math.pi * turns / n; dz = rise / n
    a0 = math.radians(a_start)
    for k in range(n):
        aa = a0 + da * k; ab = aa + da; zt = z0 + dz * (k + 1); zb = zt - .24 - dz
        p = lambda r_, a_, z_: to_local((c[0] + r_ * math.cos(a_), c[1] + r_ * math.sin(a_), z_), origin)
        top = [p(r_in, aa, zt), p(r_out, aa, zt), p(r_out, ab, zt), p(r_in, ab, zt)]
        oriented_quad(m, top, np.array((0, 0, 1.)), tex, [(0, 0), (1.2, 0), (1.2, .5), (0, .5)])
        bot = [p(r_in, aa, zb), p(r_out, aa, zb), p(r_out, ab, zb + dz), p(r_in, ab, zb + dz)]
        oriented_quad(m, bot, np.array((0, 0, -1.)), tex, [(0, 0), (1.2, 0), (1.2, .5), (0, .5)])
        outer = [p(r_out, aa, zb), p(r_out, ab, zb + dz), p(r_out, ab, zt), p(r_out, aa, zt)]
        oriented_quad(m, outer, np.array((math.cos(aa + da / 2), math.sin(aa + da / 2), 0)), tex, [(0, 0), (.5, 0), (.5, .2), (0, .2)])
        riser = [p(r_in, aa, zb), p(r_out, aa, zb), p(r_out, aa, zt), p(r_in, aa, zt)]
        oriented_quad(m, riser, np.array((math.sin(aa), -math.cos(aa), 0)), tex, [(0, 0), (1.2, 0), (1.2, .2), (0, .2)])
        # smooth helicoid ramp for collision (centre of each riser)
        za = z0 + dz * (k + .5); zb2 = z0 + dz * (k + 1.5) if k < n - 1 else z1
        col.quad(p(r_in, aa, za), p(r_out, aa, za), p(r_out, ab, zb2), p(r_in, ab, zb2), 'stone')
        if rail and k < n - 5 and k % 2 == 0:
            m.cyl(p(r_out - .08, aa, zt), .03, .95, 'rf_iron', 4, caps=False)
    if rail:
        pts = []
        for k in range(0, n - 4):
            aa = a0 + da * k; pts.append(to_local((c[0] + (r_out - .08) * math.cos(aa), c[1] + (r_out - .08) * math.sin(aa), z0 + dz * (k + 1) + .95), origin))
        for q0, q1 in zip(pts[:-1], pts[1:]):
            m.poly([q0, q1, (q1[0], q1[1], q1[2] + .05), (q0[0], q0[1], q0[2] + .05)], 'rf_iron', two_sided=True)
    m.cyl(to_local((c[0], c[1], z0), origin), r_in, rise, 'rf_stone', 10, caps=False)
    col.box(to_local((c[0] - r_in * .9, c[1] - r_in * .9, z0), origin), to_local((c[0] + r_in * .9, c[1] + r_in * .9, z1), origin), 'stone')
    a_end = (a_start + 360 * turns) % 360
    SPIRALS.append({'center': [c[0], c[1]], 'from_z': z0, 'to_z': z1, 'turns': turns, 'steps': n, 'step_rise': round(dz, 3),
                    'start_deg': a_start % 360, 'arrive_deg': a_end, 'r': [r_in, r_out]})
    return a_end


def hole_railing(m, col, c, hole, z, gap_deg, origin, h=1.0):
    """Railing around a 24-gon stair hole with an opening (60 deg) at the arrival angle."""
    hr = hole / math.cos(math.radians(7.5)) + .05
    for k in range(N):
        a0 = 15 * k - 7.5; a1 = a0 + 15; mid = (a0 + a1) / 2
        if abs((mid - gap_deg + 180) % 360 - 180) < 32: continue
        p0 = (c[0] + hr * math.cos(math.radians(a0)), c[1] + hr * math.sin(math.radians(a0)))
        p1 = (c[0] + hr * math.cos(math.radians(a1)), c[1] + hr * math.sin(math.radians(a1)))
        q = [to_local((p0[0], p0[1], z), origin), to_local((p1[0], p1[1], z), origin), to_local((p1[0], p1[1], z + h), origin), to_local((p0[0], p0[1], z + h), origin)]
        m.box(to_local((p0[0] - .05, p0[1] - .05, z), origin), to_local((p0[0] + .05, p0[1] + .05, z + h), origin), 'rf_wood', 1)
        m.poly([q[3], q[2], (q[2][0], q[2][1], q[2][2] - .08), (q[3][0], q[3][1], q[3][2] - .08)], 'rf_wood', two_sided=True)
        m.poly([q[0], q[1], (q[1][0], q[1][1], q[1][2] + .1), (q[0][0], q[0][1], q[0][2] + .1)], 'rf_wood', two_sided=True)
        col.quad(q[0], q[1], q[2], q[3], 'wood')


def palace_tower(key):
    """Returns ({room_id: (mesh, col, origin)}, exterior (mesh, col, origin))."""
    T = L.TOWERS[key]; c = T['c']; kd = int(round(T['door'] / 15)) % N
    apo_c, t = L.TOWER_APO, 1.2; ai, ao = apo_c - t / 2, apo_c + t / 2
    levels = L.TOWER_LEVELS; rooms = {}
    a_start = (T['door'] + 180) % 360
    win_edges = [(kd + j) % N for j in (6, 9, 12, 15, 18)]
    balcony = key == 'NW'; bal_edge = 12  # faces west (180 deg)
    ext_open = {}
    arrive = a_start
    for li, (z, h) in enumerate(levels):
        rid = T['rooms'][li]; origin = (c[0], c[1], z); m = Mesh(); col = Collision(); top = z + h - L.SLAB
        ops = {kd: [(1.6, z, z + 3.0, 'door')]} if li < 2 else {}
        wz = (z + 1.4, z + 1.4 + (2.6 if h > 6 else 2.2))
        for k in win_edges:
            if balcony and li == 2 and k == bal_edge:
                ops.setdefault(k, []).append((1.6, z, z + 3.0, 'door')); continue
            ops.setdefault(k, []).append((1.1, wz[0], wz[1], 'window'))
        for k, lst in ops.items(): ext_open.setdefault(k, []).extend(lst)
        wall_tex = 'rf_stone'
        poly_wall(m, col, c, ai, ao, z, top, wall_tex, None, origin, ops, do_out=False)
        floor_tex = 'rf_woodlight' if li else 'rf_cobble'
        disc(m, col, c, ai + .02, z, floor_tex, origin, hole=0 if li == 0 else 3.15)
        if li < len(levels) - 1:
            disc(m, None, c, ai + .02, top, 'rf_plaster', origin, up=False, hole=3.15)
            arrive_next = spiral(m, col, c, z, levels[li + 1][0], arrive, origin)
        else:
            disc(m, None, c, ai + .02, top, 'rf_ceiling', origin, up=False)
            col_top = Collision(); disc(Mesh(), col, c, ai, top, 'rf_plaster', origin, up=False)
            arrive_next = arrive
        if li > 0:
            hole_railing(m, col, c, 3.15, z, arrive, origin)
        rooms[rid] = (m, col, origin, {'arrive_deg': arrive})
        arrive = arrive_next
        POLY_ROOMS.append({'id': rid, 'name': L.TOWER_NAMES[rid], 'block': 'tower', 'tower': key, 'shape': 'poly24', 'center': list(c),
                           'apothem_inner': ai, 'z0': z, 'h': h, 'level': 'T%d' % li, 'stairs': 'spiral',
                           'door_edges': sorted(k for k, lst in ops.items() for o in lst if o[3] == 'door')})
    # exterior shell: plinth to top, links cover the door edge for L0+L1
    z_bot = L.G - 1.5; z_top = levels[-1][0] + levels[-1][1]
    m = Mesh(); col = Collision(); origin = (c[0], c[1], L.G)
    # outer wall in vertical bands so link openings skip only the covered band
    for k in range(N):
        bands = [(z_bot, z_top)]
        if k == kd: bands = [(levels[2][0], z_top)]
        for (b0, b1) in bands:
            ops = {k: [o for o in ext_open.get(k, []) if o[1] >= b0 - 1e-6 and o[2] <= b1 + 1e-6]}
            poly_wall_one(m, col, c, ai, ao, b0, b1, origin, k, ops[k])
    # machicolation corbel ring + cone roof + finial
    m.cyl(to_local((c[0], c[1], z_top - .6), origin), ao + .5, .6, 'rf_stonedark', N, caps=False)
    m.cyl(to_local((c[0], c[1], z_top - 1.4), origin), ao, .8, 'rf_stonedark', N, caps=False, r2=ao + .5)
    m.cyl(to_local((c[0], c[1], z_top), origin), ao + .9, 12.5, 'rf_slate', N, caps=False, r2=0.0, uvscale=3.0)
    m.cyl(to_local((c[0], c[1], z_top - .02), origin), ao + .9, .01, 'rf_slate', N, caps=True, r2=ao + .9)
    m.sphere(to_local((c[0], c[1], z_top + 12.6), origin), .35, 'rf_gold', 8, 4)
    m.cyl(to_local((c[0], c[1], z_top + 12.4), origin), .06, 2.2, 'rf_iron', 4)
    if balcony:
        zb = levels[2][0]
        for k in range(6, 19):
            a0 = math.radians(15 * k - 7.5); a1 = math.radians(15 * k + 7.5); r0 = ao / math.cos(math.radians(7.5)) - .05; r1 = r0 + 2.4
            q = [(c[0] + r0 * math.cos(a0), c[1] + r0 * math.sin(a0), zb), (c[0] + r1 * math.cos(a0), c[1] + r1 * math.sin(a0), zb),
                 (c[0] + r1 * math.cos(a1), c[1] + r1 * math.sin(a1), zb), (c[0] + r0 * math.cos(a1), c[1] + r0 * math.sin(a1), zb)]
            ql = [to_local(p, origin) for p in q]
            oriented_quad(m, ql, np.array((0, 0, 1.)), 'rf_stone', [(p[0] / 3, p[1] / 3) for p in q]); col.quad(*ql, 'stone')
            qb = [(p[0], p[1], p[2] - .45) for p in ql]
            oriented_quad(m, qb, np.array((0, 0, -1.)), 'rf_stone', [(0, 0), (1, 0), (1, 1), (0, 1)])
            o = [ql[1], ql[2], (ql[2][0], ql[2][1], ql[2][2] + 1.05), (ql[1][0], ql[1][1], ql[1][2] + 1.05)]
            m.poly(o, 'rf_stone', two_sided=True); col.quad(*o, 'stone')
            m.poly([ql[1], ql[2], qb[2], qb[1]], 'rf_stone', two_sided=True)
    return rooms, (m, col, origin)


def poly_wall_one(m, col, c, ai, ao, z0, z1, origin, k, ops):
    half = ao * math.tan(math.radians(7.5))
    holes = [(-w / 2 / half, w / 2 / half, za, zb) for (w, za, zb, kind) in ops]
    for (f0, f1, w0, w1) in rect_minus(-1, 1, z0, z1, holes):
        edge_quad(m, col, c, k, ao, w0, w1, 'rf_stone', False, origin, (f0, f1))
    a = math.radians(15 * k); nx, ny = math.cos(a), math.sin(a); tx, ty = -ny, nx
    am = (ai + ao) / 2
    for (w, za, zb, kind) in ops:
        if kind == 'window':
            q = [(c[0] + nx * am + tx * s, c[1] + ny * am + ty * s, z) for s, z in ((-w / 2, za), (w / 2, za), (w / 2, zb), (-w / 2, zb))]
            m.poly([to_local(p, origin) for p in q], 'rf_glass', [(0, 0), (w / 1.6, 0), (w / 1.6, (zb - za) / 1.6), (0, (zb - za) / 1.6)], two_sided=True)
            col.quad(*[to_local(p, origin) for p in q], 'glass')
            # outer surround
            for sgn in (-1, 1):
                p0 = (c[0] + nx * (ao + .06) + tx * sgn * (w / 2 + .1), c[1] + ny * (ao + .06) + ty * sgn * (w / 2 + .1))
                m.box(to_local((p0[0] - .1, p0[1] - .1, za - .1), origin), to_local((p0[0] + .1, p0[1] + .1, zb + .15), origin), 'rf_stonedark', 2)
        for sgn in (-1, 1):
            s = sgn * w / 2
            p0 = (c[0] + nx * am + tx * s, c[1] + ny * am + ty * s); p1 = (c[0] + nx * ao + tx * s, c[1] + ny * ao + ty * s)
            pts = [(p0[0], p0[1], za), (p1[0], p1[1], za), (p1[0], p1[1], zb), (p0[0], p0[1], zb)]
            oriented_quad(m, [to_local(p, origin) for p in pts], np.array((-tx * sgn, -ty * sgn, 0.)), 'rf_stone', [(0, 0), (.3, 0), (.3, 1), (0, 1)])
        for zz, nz in ((zb, -1.), (za, 1.)):
            q = [(c[0] + nx * am - tx * w / 2, c[1] + ny * am - ty * w / 2, zz), (c[0] + nx * am + tx * w / 2, c[1] + ny * am + ty * w / 2, zz),
                 (c[0] + nx * ao + tx * w / 2, c[1] + ny * ao + ty * w / 2, zz), (c[0] + nx * ao - tx * w / 2, c[1] + ny * ao - ty * w / 2, zz)]
            oriented_quad(m, [to_local(p, origin) for p in q], np.array((0, 0, nz)), 'rf_stone', [(0, 0), (1, 0), (1, .3), (0, .3)])


def wall_tower(variant):
    """Generic wall tower model in local frame (+x = outward radial). Walk room G+10..G+16."""
    c = (0.0, 0.0); ai, ao = 7.8, 9.0; zw = L.WALK_Z; zt = zw + 6.0; origin = (0, 0, 0)
    m = Mesh(); col = Collision()
    door_k = [7, 17]                    # +-105 deg: wall walks
    ops = {k: [(1.6, zw, zw + 2.8, 'door')] for k in door_k}
    for k in (0, 3, 21, 12):
        ops.setdefault(k, []).append((0.5, zw + 1.2, zw + 3.2, 'window'))
    # body (solid) from below ground to walk level: outer faces only
    for k in range(N):
        poly_wall_one(m, col, c, ai, ao, L.G - 1.5, zw, origin, k, [])
        poly_wall_one(m, col, c, ai, ao, zw, zt, origin, k, ops.get(k, []))
    poly_wall(m, col, c, ai, ao, zw, zt - L.SLAB, 'rf_stone', None, origin, ops, do_out=False)
    disc(m, col, c, ai + .02, zw, 'rf_woodlight', origin, surf='wood')
    disc(m, None, c, ai + .02, zt - L.SLAB, 'rf_wood', origin, up=False)
    disc(Mesh(), col, c, ai, zt - L.SLAB, 'rf_wood', origin)
    m.cyl((0, 0, zt - .7), ao + .55, .7, 'rf_stonedark', N, caps=False)
    m.cyl((0, 0, zt - 1.5), ao, .8, 'rf_stonedark', N, caps=False, r2=ao + .55)
    m.cyl((0, 0, zt), ao + 1.0, 13.0, 'rf_slate', N, caps=False, r2=0.0, uvscale=3.0)
    m.cyl((0, 0, zt - .02), ao + 1.0, .01, 'rf_slate', N, caps=True, r2=ao + 1.0)
    m.sphere((0, 0, zt + 13.1), .4, 'rf_gold', 8, 4); m.cyl((0, 0, zt + 12.8), .06, 2.4, 'rf_iron', 4)
    return m, col


def keep_extras():
    """Keep roof (walkable), parapet, corner bartizans and stair turret. Spiral helpers for K0-K2."""
    x0, y0, x1, y1 = [r for r in L.ROOMS if r['id'] == 'K0'][0]['rect']
    c = ((x0 + x1) / 2, (y0 + y1) / 2); zr = L.L0 + 21.0; origin = (c[0], c[1], zr)
    m = Mesh(); col = Collision(); t = 2.0
    ox0, oy0, ox1, oy1 = x0 - t / 2, y0 - t / 2, x1 + t / 2, y1 + t / 2
    rect_floor_round_hole(m, col, (ox0 + .6, oy0 + .6, ox1 - .6, oy1 - .6), c, 3.2, zr, 'rf_cobble', origin)
    # parapet ring with merlons
    for (a, b, cc, d) in [(ox0, oy0, ox1, oy0 + .6), (ox0, oy1 - .6, ox1, oy1), (ox0, oy0 + .6, ox0 + .6, oy1 - .6), (ox1 - .6, oy0 + .6, ox1, oy1 - .6)]:
        m.box(to_local((a, b, zr), origin), to_local((cc, d, zr + 1.1), origin), 'rf_stonedark', 4); col.box(to_local((a, b, zr), origin), to_local((cc, d, zr + 1.1), origin))
    for x in np.arange(ox0 + .4, ox1 - .4, 1.8):
        for (yy0, yy1) in ((oy0, oy0 + .6), (oy1 - .6, oy1)):
            m.box(to_local((x, yy0, zr + 1.1), origin), to_local((x + 1.0, yy1, zr + 2.0), origin), 'rf_stonedark', 4); col.box(to_local((x, yy0, zr + 1.1), origin), to_local((x + 1.0, yy1, zr + 2.0), origin))
    for y in np.arange(oy0 + 2.2, oy1 - 2.2, 1.8):
        for (xx0, xx1) in ((ox0, ox0 + .6), (ox1 - .6, ox1)):
            m.box(to_local((xx0, y, zr + 1.1), origin), to_local((xx1, y + 1.0, zr + 2.0), origin), 'rf_stonedark', 4); col.box(to_local((xx0, y, zr + 1.1), origin), to_local((xx1, y + 1.0, zr + 2.0), origin))
    # corner bartizans
    for (bx, by) in ((ox0, oy0), (ox1, oy0), (ox0, oy1), (ox1, oy1)):
        m.cyl(to_local((bx, by, zr - 3.0), origin), 1.2, 1.5, 'rf_stonedark', 12, caps=False, r2=1.8)
        m.cyl(to_local((bx, by, zr - 1.5), origin), 1.8, 4.5, 'rf_stonedark', 12, caps=False)
        m.cyl(to_local((bx, by, zr + 3.0), origin), 2.1, 4.5, 'rf_slate', 12, caps=False, r2=0)
        m.cyl(to_local((bx, by, zr + 2.98), origin), 2.1, .01, 'rf_slate', 12, caps=True, r2=2.1)
    # stair turret around the roof hole: round wall r 3.45..3.95, door toward the arrival direction
    arrive = SPIRALS_KEEP_ARRIVE[0] if SPIRALS_KEEP_ARRIVE else 0.0
    kd = int(round(arrive / 15)) % N
    ops = {kd: [(1.5, zr, zr + 2.6, 'door')]}
    poly_wall(m, col, c, 3.45, 3.95, zr, zr + 3.6, 'rf_stone', 'rf_stonedark', origin, ops)
    disc(m, None, c, 3.47, zr + 3.6, 'rf_wood', origin, up=False)
    m.cyl(to_local((c[0], c[1], zr + 3.6), origin), 4.4, 4.2, 'rf_slate', N, caps=False, r2=0)
    m.cyl(to_local((c[0], c[1], zr + 3.58), origin), 4.4, .01, 'rf_slate', N, caps=True, r2=4.4)
    # flag pole with royal banner
    m.cyl(to_local((c[0] + 9, c[1] + 7, zr), origin), .08, 9.0, 'rf_iron', 6)
    fp = [to_local(p, origin) for p in [(c[0] + 9, c[1] + 7, zr + 6.0), (c[0] + 12.4, c[1] + 7, zr + 6.0), (c[0] + 12.4, c[1] + 7, zr + 8.8), (c[0] + 9, c[1] + 7, zr + 8.8)]]
    m.poly(fp, 'rf_banner', [(0, 0), (1, 0), (1, 1), (0, 1)], two_sided=True)
    return m, col, origin


SPIRALS_KEEP_ARRIVE = []


def keep_spiral_parts():
    """Per keep room: helix + railing pieces (merged into the room shells by build.py)."""
    x0, y0, x1, y1 = [r for r in L.ROOMS if r['id'] == 'K0'][0]['rect']
    c = ((x0 + x1) / 2, (y0 + y1) / 2); out = {}; a = 270.0
    for rid, z in (('K0', L.L0), ('K1', L.L0 + 7), ('K2', L.L0 + 14)):
        m = Mesh(); col = Collision(); origin = (c[0], c[1], z)
        if rid != 'K0':
            hole_railing(m, col, c, 3.2, z, a, origin)
        a_next = spiral(m, col, c, z, z + 7.0, a, origin, turns=1.25)
        out[rid] = (m, col, origin, a)
        a = a_next
    SPIRALS_KEEP_ARRIVE[:] = [a]
    return out


def tunnel():
    """Escape tunnel from the Main Dungeon (L-2) to the north moat water gate."""
    x0, x1 = -2.0, 2.0; ys = L.PALACE_DY + 2.0; ye = L.APO_REV
    zf0 = L.L0 - 10.0; zf1 = L.W + 1.5
    def zf(y):
        if y <= 40 + L.PALACE_DY: return zf0
        if y >= ye - 8: return zf1
        return zf0 + (zf1 - zf0) * (y - 40 - L.PALACE_DY) / (ye - 8 - 40 - L.PALACE_DY)
    origin = (0.0, (ys + ye) / 2, zf1); m = Mesh(); col = Collision()
    ys_ = list(np.arange(ys, ye, 4.0)) + [ye]
    H = 3.0; arch = 0.9
    for ya, yb in zip(ys_[:-1], ys_[1:]):
        za, zb = zf(ya), zf(yb)
        fl = [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)]
        oriented_quad(m, [to_local(p, origin) for p in fl], np.array((0, 0, 1.)), 'rf_dungeon', [(p[0] / 3.5, p[1] / 3.5) for p in fl])
        col.quad(*[to_local(p, origin) for p in fl], 'stone')
        for xw, nx in ((x0, 1.), (x1, -1.)):
            w = [(xw, ya, za), (xw, yb, zb), (xw, yb, zb + H), (xw, ya, za + H)]
            oriented_quad(m, [to_local(p, origin) for p in w], np.array((nx, 0, 0.)), 'rf_dungeon', [(p[1] / 3.5, (p[2] - za) / 3.5) for p in w])
            col.quad(*[to_local(p, origin) for p in w], 'stone')
        # barrel vault (6 facets)
        for j in range(6):
            t0 = math.pi * j / 6; t1 = math.pi * (j + 1) / 6
            def V(t, y, z):
                return (2.0 * math.cos(t), y, z + H + arch * math.sin(t) * 1.0)
            q = [V(t0, ya, za), V(t0, yb, zb), V(t1, yb, zb), V(t1, ya, za)]
            oriented_quad(m, [to_local(p, origin) for p in q], np.array((-math.cos((t0 + t1) / 2), 0, -math.sin((t0 + t1) / 2))), 'rf_dungeon', [(j / 2, ya / 3.5), (j / 2, yb / 3.5), ((j + 1) / 2, yb / 3.5), ((j + 1) / 2, ya / 3.5)])
        col.quad(*[to_local(p, origin) for p in [(x0, ya, za + H + arch), (x1, ya, za + H + arch), (x1, yb, zb + H + arch), (x0, yb, zb + H + arch)]], 'stone')
    POLY_ROOMS.append({'id': 'TN', 'name': 'Escape Tunnel', 'block': 'palace', 'shape': 'tunnel', 'rect': [x0, ys, x1, ye], 'z0': zf0, 'z_end': zf1, 'h': H + arch,
                       'level': 'L-2', 'category': 'secret', 'polyline': [[0, ys, zf0], [0, 40 + L.PALACE_DY, zf0], [0, ye - 8, zf1], [0, ye, zf1]]})
    return m, col, origin, zf
