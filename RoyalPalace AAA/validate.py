"""PROJECT ROYAL FORTRESS - automated static validator (14 checks + floor-plan preview).
Reads the EXPORTED artefacts (assets/*.dff|col|txd, client/data/world.json, docs/rooms.json, meta.xml)
and re-parses every binary with the DragonFF gtaLib readers. Layout modules are only used for
room rectangles / wall thickness. This is static analysis - it is NOT an in-game test."""
from __future__ import annotations
import json, math, sys, hashlib, time
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'vendor' / 'DragonFF'))
from gtaLib import col as gcol, dff as gdff, txd as gtxd
import layout as L, rooms as R

W = json.loads((ROOT / 'client' / 'data' / 'world.json').read_text())
RM = json.loads((ROOT / 'docs' / 'rooms.json').read_text())
ROOMS = {r['id']: r for r in RM['rooms']}
RESULTS = []; DETAILS = {}
CELL = 0.4; STEP = 0.46; HEAD = 1.75; PED_R = 0.25


def check(cid, title):
    def deco(fn):
        def run():
            t = time.time()
            try:
                ok, info, det = fn()
            except Exception as ex:  # a crash is a failure, never a pass
                import traceback; ok, info, det = False, 'EXCEPTION %r' % ex, traceback.format_exc()
            RESULTS.append({'id': cid, 'title': title, 'status': 'PASS' if ok else 'FAIL', 'summary': info, 'seconds': round(time.time() - t, 2)})
            DETAILS[cid] = det
            print('%s %-4s %s - %s' % ('PASS' if ok else 'FAIL', cid, title, info))
        return run
    return deco


# ------------------------------------------------------------------ COL cache / world queries
_COL = {}


def colmodel(name):
    if name not in _COL:
        c = gcol.coll(); c.load_file(str(ROOT / W['models'][name]['col']))
        m = c.models[0]
        boxes = np.array([[*b.min, *b.max] for b in m.boxes], float).reshape(-1, 6)
        verts = np.array([[v.x, v.y, v.z] if hasattr(v, 'x') else list(v) for v in m.mesh_verts], float).reshape(-1, 3)
        faces = np.array([[f.a, f.b, f.c] for f in m.mesh_faces], int).reshape(-1, 3)
        _COL[name] = (m, boxes, verts, faces)
    return _COL[name]


def to_local(o, x, y, z):
    a = math.radians(-o['rot'][2]); dx, dy = x - o['pos'][0], y - o['pos'][1]
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a), z - o['pos'][2]


def world_aabb(o):
    lo, hi = W['models'][o['model']]['col_bounds']; a = math.radians(o['rot'][2]); c, s = math.cos(a), math.sin(a)
    xs, ys = [], []
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]): xs.append(o['pos'][0] + x * c - y * s); ys.append(o['pos'][1] + x * s + y * c)
    return min(xs), min(ys), lo[2] + o['pos'][2], max(xs), max(ys), hi[2] + o['pos'][2]


SOLID_OBJ = [o for o in W['objects'] if W['models'][o['model']]['class'] != 'lod']
AABB = {id(o): world_aabb(o) for o in SOLID_OBJ}


def objects_at(x, y):
    return [o for o in SOLID_OBJ if AABB[id(o)][0] - .1 <= x <= AABB[id(o)][3] + .1 and AABB[id(o)][1] - .1 <= y <= AABB[id(o)][4] + .1]


def tri_z_at(v, f, lx, ly):
    """z of mesh faces crossing the vertical line (lx,ly) - vectorised barycentric test."""
    if not len(f): return np.zeros(0)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(d) > 1e-9; d = np.where(ok, d, 1)
    w1 = ((b[:, 1] - c[:, 1]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (ly - c[:, 1])) / d
    w2 = ((c[:, 1] - a[:, 1]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (ly - c[:, 1])) / d
    w3 = 1 - w1 - w2; inside = ok & (w1 >= -1e-4) & (w2 >= -1e-4) & (w3 >= -1e-4)
    return (w1 * a[:, 2] + w2 * b[:, 2] + w3 * c[:, 2])[inside]


def surface_below(x, y, z, up=.4, down=1.2):
    """Highest collision surface in [z-down, z+up] under (x,y) over all placed COL (boxes + faces)."""
    best = None
    for o in objects_at(x, y):
        lx, ly, lz = to_local(o, x, y, z); _, bx, v, f = colmodel(o['model'])
        if len(bx):
            m = (bx[:, 0] <= lx) & (lx <= bx[:, 3]) & (bx[:, 1] <= ly) & (ly <= bx[:, 4]) & (bx[:, 5] <= lz + up) & (bx[:, 5] >= lz - down)
            if m.any(): t = bx[m, 5].max() + o['pos'][2]; best = t if best is None else max(best, t)
        zz = tri_z_at(v, f, lx, ly); zz = zz[(zz <= lz + up) & (zz >= lz - down)]
        if len(zz): t = zz.max() + o['pos'][2]; best = t if best is None else max(best, t)
    return best


def solid_at(x, y, z0, z1, r=0.2):
    """Any COL box intersecting the column (x+-r, y+-r, z0..z1)?"""
    for o in objects_at(x, y):
        lx, ly, lz = to_local(o, x, y, 0); _, bx, _, _ = colmodel(o['model'])
        if not len(bx): continue
        lz0, lz1 = z0 - o['pos'][2], z1 - o['pos'][2]
        m = (bx[:, 0] < lx + r) & (bx[:, 3] > lx - r) & (bx[:, 1] < ly + r) & (bx[:, 4] > ly - r) & (bx[:, 2] < lz1) & (bx[:, 5] > lz0)
        if m.any(): return o['model']
    return None


# ------------------------------------------------------------------ checks
@check('C01', 'Room manifest completeness (50 brief rooms + support spaces)')
def c01():
    need = ('id', 'name', 'level', 'z0', 'h', 'connections', 'models', 'collision', 'light_sources', 'spawn', 'furniture')
    bad = []
    for r in RM['rooms']:
        miss = [k for k in need if k not in r or r[k] in (None, '')]
        if r.get('shape') == 'rect' and 'rect' not in r: miss.append('rect')
        if r.get('shape') == 'poly24' and 'center' not in r: miss.append('center')
        if not r.get('models'): miss.append('models(empty)')
        if not r.get('connections'): miss.append('connections(empty)')
        if miss: bad.append((r['id'], miss))
    numbered = [str(i) for i in range(1, 51)]
    absent = [i for i in numbered if i not in ROOMS]
    named = sum(1 for i in numbered if i in ROOMS)
    furnished = sum(1 for i in numbered if i in ROOMS and len(ROOMS[i]['furniture']) >= (3 if ROOMS[i].get('block') not in ('wall_tower',) else 0))
    return (not bad and not absent), '%d manifest spaces, %d/50 brief rooms present, %d/50 with >=3 furniture groups, %d incomplete' % (len(RM['rooms']), named, furnished, len(bad)), {'incomplete': bad, 'absent': absent}


def graph():
    g = defaultdict(set)
    for d in RM['doors']:
        if d['kind'] == 'window': continue
        g[d['a']].add(d['b']); g[d['b']].add(d['a'])
    # wall-walk network: 12 wall towers sit on the curtain-wall walk; walk <-> ground via the 4 stair segments,
    # walk <-> gatehouse room 39 through its side doors (declared in DOORS as b='WALK' if present)
    nstair = sum(1 for o in W['objects'] if o['model'] == 'wall_stair')
    for a, b in RM.get('spiral_links', []): g[a].add(b); g[b].add(a)
    for wt in L.WALL_TOWERS: g[wt['id']].add('WALK'); g['WALK'].add(wt['id'])
    if nstair >= 1: g['WALK'].add('EXT'); g['EXT'].add('WALK')
    return g, nstair


@check('C02', 'Global reachability (BFS from the outside through every door/stair/secret passage)')
def c02():
    g, nstair = graph(); seen = {'EXT'}; q = deque(['EXT']); depth = {'EXT': 0}
    while q:
        u = q.popleft()
        for v in g[u]:
            if v not in seen: seen.add(v); depth[v] = depth[u] + 1; q.append(v)
    unreachable = [r for r in ROOMS if r not in seen]
    # secret-only rooms: reachable only if secret doors are opened
    g2 = defaultdict(set)
    for d in RM['doors']:
        if d['kind'] in ('window', 'secret'): continue
        g2[d['a']].add(d['b']); g2[d['b']].add(d['a'])
    for a, b in RM.get('spiral_links', []): g2[a].add(b); g2[b].add(a)
    for k, v in g.items():
        if k == 'WALK' or 'WALK' in v:
            for x in v: g2[k].add(x)
    s2 = {'EXT'}; q = deque(['EXT'])
    while q:
        u = q.popleft()
        for v in g2[u]:
            if v not in s2: s2.add(v); q.append(v)
    secret_only = sorted(r for r in ROOMS if r in seen and r not in s2)
    return not unreachable, '%d/%d spaces reachable (max depth %d, %d wall stairs); secret-only: %s' % (
        len([r for r in ROOMS if r in seen]), len(ROOMS), max(depth.values()), nstair, ', '.join(secret_only) or 'none'), {'unreachable': unreachable, 'depth': depth, 'secret_only': secret_only}


def door_openings(d, r):
    """(edge, opening) of door d in rect room r; tower doors are matched by value (towers.py copies the record)."""
    e = R.door_edge(d, r)
    edges = [e] if e else ['S', 'N', 'W', 'E']
    for e2 in edges:
        for o in R.OPENINGS.get((r['id'], e2), []):
            if o['door'] is d or o['door'] == d: return e2, o
    if e is None and d['at'] is not None:      # tower doors: opening matched by centre and width on the rect side
        for e2 in edges:
            for o in R.OPENINGS.get((r['id'], e2), []):
                if o['kind'] == d['kind'] and abs((o['s0'] + o['s1']) / 2 - d['at']) < .05 and abs((o['s1'] - o['s0']) - d['w']) < .05: return e2, o
    return None, None


@check('C03', 'Door geometry: openings cut in BOTH walls, matching span/height, minimum clear size')
def c03():
    bad = []; n = 0
    for d in L.DOORS:
        if d['kind'] == 'window': continue
        sides = [x for x in (d['a'], d['b']) if x in R.ROOM]
        spans = []
        for rid in sides:
            r = R.ROOM[rid]; e, o = door_openings(d, r)
            if o is None: bad.append((d['a'], d['b'], rid, 'opening missing')); continue
            spans.append((o['s0'], o['s1'], o['z0'], o['z1']))
        if len(spans) == 2 and not np.allclose(spans[0], spans[1], atol=.03): bad.append((d['a'], d['b'], 'span mismatch', spans))
        if spans:
            s0, s1, z0, z1 = spans[0]
            minw = .75 if d['kind'] == 'secret' else .9
            if s1 - s0 < minw - 1e-6 or z1 - z0 < 2.1 - 1e-6: bad.append((d['a'], d['b'], 'too small', round(s1 - s0, 2), round(z1 - z0, 2)))
        n += 1
    # polygon/tower doors are cut by towers.py; check the room manifest lists them
    poly_ok = all(ROOMS[p]['connections'] for p in ROOMS if ROOMS[p].get('shape') == 'poly24' and not p.startswith('WT') and p != '36')
    return not bad and poly_ok, '%d doors checked (rect rooms), %d problems, tower doors listed=%s' % (n, len(bad), poly_ok), bad


@check('C04', 'Every door leads to a real space (inner volume or walkable ground/perron outside)')
def c04():
    bad = []; n = 0
    for d in L.DOORS:
        if d['kind'] == 'window': continue
        for rid, other in ((d['a'], d['b']), (d['b'], d['a'])):
            if rid not in R.ROOM: continue
            r = R.ROOM[rid]; e, o = door_openings(d, r)
            if o is None: continue
            ax, c, _, _, sg = R.edge_line(r, e); n_in = R.inward(r, e)
            sm = (o['s0'] + o['s1']) / 2
            base = (sm, c) if ax == 'y' else (c, sm)
            t = R.thickness(r, e) / 2 + .45
            px, py = base[0] - n_in[0] * t, base[1] - n_in[1] * t     # point beyond the door (other side)
            z = o['z0'] + .1
            s = surface_below(px, py, z, up=.55, down=.6)
            n += 1
            if s is None:
                bad.append((rid, other, e, [round(px, 2), round(py, 2), round(z, 2)], 'no walkable surface beyond the door'))
            elif solid_at(px, py, s + .5, s + 1.8, r=.15):
                bad.append((rid, other, e, [round(px, 2), round(py, 2)], 'blocked by ' + str(solid_at(px, py, s + .5, s + 1.8, r=.15))))
            break
    return not bad, '%d door far-sides probed against exported COL, %d problems' % (n, len(bad)), bad


@check('C05', 'Stairs: total rise matches the levels, riser <= 0.2 m, tread >= 0.26 m, spirals <= 0.25 m')
def c05():
    bad = []
    for s in RM['stairs']:
        rise = s['to_z'] - s['from_z']
        if abs(s['risers'] * s['riser_h'] - rise) > .02: bad.append((s['room'], 'rise mismatch', s['risers'], s['riser_h'], rise))
        if s['riser_h'] > .2 + 1e-6: bad.append((s['room'], 'riser too high', s['riser_h']))
        if s['tread'] < .26 - 1e-6: bad.append((s['room'], 'tread too short', s['tread']))
        r = ROOMS[s['room']]
        if abs(r['z0'] - s['from_z']) > .01: bad.append((s['room'], 'stair does not start on the room floor'))
        # arrival on a real floor: probe the exported COL at the top of the stair
        rec = R.ROOM[s['room']]; ix0, iy0, ix1, iy1 = R.inner_rect(rec); found = 0
        for x in np.linspace(ix0 + .3, ix1 - .3, 12):
            for y in np.linspace(iy0 + .3, iy1 - .3, 8):
                t = surface_below(x, y, s['to_z'] + .05, up=.1, down=.1)
                if t is not None and abs(t - s['to_z']) < .06: found += 1
        if found < 3: bad.append((s['room'], 'no landing surface at the upper level', found))
    for sp in RM['spirals']:
        if sp['step_rise'] > .25: bad.append(('spiral', sp['center'], sp['step_rise']))
        if abs(sp['steps'] * sp['step_rise'] - (sp['to_z'] - sp['from_z'])) > .05: bad.append(('spiral rise', sp['center']))
    for p in RM['perrons']:
        if p['rise'] / p['risers'] > .2: bad.append(('perron', p))
    return not bad, '%d straight/U stairs, %d spirals, %d perrons, %d problems' % (len(RM['stairs']), len(RM['spirals']), len(RM['perrons']), len(bad)), bad


_DFF = {}


def dffmesh(name):
    if name not in _DFF:
        d = gdff.dff(); d.load_file(str(ROOT / W['models'][name]['dff'])); g = d.clumps[0].geometry_list[0]
        v = np.array([[p.x, p.y, p.z] for p in g.vertices]); f = np.array([[t.a, t.b, t.c, t.material] for t in g.triangles]).reshape(-1, 4)
        names = [m.textures[0].name if m.textures else '' for m in g.materials]
        _DFF[name] = (v, f, names)
    return _DFF[name]


def seg_hits(o, p0, p1, skip=('rf_glass', 'rf_stained')):
    v, f, names = dffmesh(o['model'])
    a = np.array(to_local(o, *p0)); b = np.array(to_local(o, *p1)); d = b - a
    keep = np.array([names[m] not in skip for m in f[:, 3]], bool)
    F = f[keep]
    if not len(F): return 0
    v0, v1, v2 = v[F[:, 0]], v[F[:, 1]], v[F[:, 2]]
    e1, e2 = v1 - v0, v2 - v0; h = np.cross(d, e2); det = (e1 * h).sum(1); ok = np.abs(det) > 1e-9; inv = 1 / np.where(ok, det, 1)
    s = a - v0; u = (s * h).sum(1) * inv; q = np.cross(s, e1); vv = (d * q).sum(1) * inv; t = (e2 * q).sum(1) * inv
    return int((ok & (u >= 0) & (vv >= 0) & (u + vv <= 1) & (t > 0) & (t < 1)).sum())


@check('C06', 'Windows consistent with the exterior: clear sight line through shell + facade (glass excluded)')
def c06():
    bad = []; n = 0
    for w in RM['windows']:
        r = R.ROOM[w['room']]; nin = R.inward(r, w['edge']); t = R.thickness(r, w['edge']) / 2
        zc = (w['z'][0] + w['z'][1]) / 2; cx, cy = w['center']
        p0 = (cx + nin[0] * (t + .25), cy + nin[1] * (t + .25), zc); p1 = (cx - nin[0] * (t + .6), cy - nin[1] * (t + .6), zc)
        hits = 0
        for o in objects_at(cx, cy):
            if W['models'][o['model']]['class'] in ('furn', 'tree', 'terrain'): continue
            hits += seg_hits(o, p0, p1)
        n += 1
        if hits: bad.append((w['room'], w['edge'], w['center'], hits))
    return not bad, '%d windows ray-tested against exported DFF geometry, %d obstructed' % (n, len(bad)), bad


@check('C07', 'No overlapping room volumes (rect-rect and rect-tower)')
def c07():
    bad = []; rr = list(L.ROOMS)
    for i, a in enumerate(rr):
        ax0, ay0, ax1, ay1 = R.inner_rect(a)
        for b in rr[i + 1:]:
            bx0, by0, bx1, by1 = R.inner_rect(b)
            ox = min(ax1, bx1) - max(ax0, bx0); oy = min(ay1, by1) - max(ay0, by0)
            oz = min(a['z0'] + a['h'], b['z0'] + b['h']) - max(a['z0'], b['z0'])
            if ox > .05 and oy > .05 and oz > .05: bad.append((a['id'], b['id'], round(ox, 2), round(oy, 2), round(oz, 2)))
    polys = [r for r in RM['rooms'] if r.get('shape') == 'poly24']
    for p in polys:
        ap = p.get('apothem_inner', 7.8); cx, cy = p['center']; z0 = p['z0']; z1 = z0 + p.get('h', 6)
        for a in rr:
            ax0, ay0, ax1, ay1 = R.inner_rect(a)
            dx = max(ax0 - cx, 0, cx - ax1); dy = max(ay0 - cy, 0, cy - ay1)
            if math.hypot(dx, dy) < ap - .3 and min(z1, a['z0'] + a['h']) - max(z0, a['z0']) > .05: bad.append((p['id'], a['id']))
    return not bad, '%d rect rooms + %d tower rooms pairwise tested, %d overlaps' % (len(rr), len(polys), len(bad)), bad


@check('C08', 'Collision present for every model and COL bounds cover the DFF bounds')
def c08():
    bad = []; empty = []
    for name, m in W['models'].items():
        c, bx, v, f = colmodel(name)
        lo = np.array(c.bounds.min); hi = np.array(c.bounds.max)
        vlo, vhi = np.array(m['bounds'][0]), np.array(m['bounds'][1])
        if (lo > vlo + .05).any() or (hi < vhi - .05).any(): bad.append((name, lo.tolist(), hi.tolist(), vlo.tolist(), vhi.tolist()))
        if not len(bx) and not len(f) and m['class'] != 'lod': empty.append(name)
    return not bad and not empty, '%d COL files, %d bound problems, %d models without collision geometry (LOD shells exempt)' % (len(W['models']), len(bad), len(empty)), {'bounds': bad, 'empty': empty}


@check('C09', 'Texture references: every DFF material exists in the TXD groups the streamer loads')
def c09():
    tex = {}
    for g, info in W['txds'].items():
        t = gtxd.txd(); t.load_file(str(ROOT / info['path'])); tex[g] = {x.name.lower() for x in t.native_textures}
    bad = []; used = set()
    for name, m in W['models'].items():
        _, f, names = dffmesh(name)
        avail = set().union(*[tex[g] for g in m['txds']])
        for nm in set(names):
            used.add(nm.lower())
            if nm.lower() not in avail: bad.append((name, nm))
    unused = sorted(set().union(*tex.values()) - used)
    return not bad, '%d TXDs / %d textures, %d missing references, unused textures: %s' % (len(tex), sum(len(v) for v in tex.values()), len(bad), ', '.join(unused) or 'none'), bad


@check('C10', 'Binary integrity: every DFF/COL/TXD re-parses, counts and hashes match world.json')
def c10():
    bad = []
    for name, m in W['models'].items():
        v, f, _ = dffmesh(name)
        if len(v) != m['vertices'] or len(f) != m['triangles']: bad.append((name, 'count mismatch'))
        if len(v) >= 65535: bad.append((name, 'too many vertices'))
        c, bx, cv, cf = colmodel(name)
        if c.version != 3 or len(bx) != m['col_boxes'] or len(cf) != m['col_faces']: bad.append((name, 'col mismatch'))
        if (ROOT / m['dff']).read_bytes()[:4] != b'\x10\x00\x00\x00': bad.append((name, 'not a RW clump'))
        if (ROOT / m['col']).read_bytes()[:4] != b'COL3': bad.append((name, 'not COL3'))
    for g, info in W['txds'].items():
        if hashlib.sha256((ROOT / info['path']).read_bytes()).hexdigest() != info['sha256']: bad.append((g, 'sha mismatch'))
    meta = (ROOT / 'meta.xml').read_text() if (ROOT / 'meta.xml').exists() else ''
    missing_meta = [p for p in [m['dff'] for m in W['models'].values()] + [m['col'] for m in W['models'].values()] + [i['path'] for i in W['txds'].values()] if p not in meta]
    if missing_meta: bad.append(('meta.xml', '%d files not listed' % len(missing_meta)))
    return not bad, '%d DFF + %d COL + %d TXD re-parsed; meta.xml lists all=%s; %d problems' % (len(W['models']), len(W['models']), len(W['txds']), not missing_meta, len(bad)), bad


@check('C11', 'Interactive mechanisms: parts, models, motions, ACL rights, leaf fits its opening')
def c11():
    bad = []
    rights = {'gate', 'vault', 'archive', None}
    for iid, meta in L.INTERACTIVE.items():
        rec = W['interactive'].get(iid)
        if not rec or not rec['parts']: bad.append((iid, 'no parts')); continue
        if meta['acl'] not in rights: bad.append((iid, 'unknown acl', meta['acl']))
        for p in rec['parts']:
            if p['model'] not in W['models']: bad.append((iid, 'model missing', p['model']))
            mv = p['open']; mag = sum(abs(x) for x in mv.get('move', [0, 0, 0])) + sum(abs(x) for x in mv.get('rot', [0, 0, 0]))
            if mag < 1e-6: bad.append((iid, 'no motion'))
        if meta.get('needs') and meta['needs'] not in W['interactive']: bad.append((iid, 'needs unknown', meta['needs']))
    # leaf width vs opening width
    for d in L.DOORS:
        if d['kind'] not in ('interactive',) or not d['iid']: continue
        rec = W['interactive'][d['iid']]; tot = 0
        for p in rec['parts']:
            b = W['models'][p['model']]['bounds']; tot += b[1][0] - b[0][0]
        if d['iid'] == 'vault_door': continue
        if abs(tot - d['w']) > .12: bad.append((d['iid'], 'leaf width %.2f vs opening %.2f' % (tot, d['w'])))
    lua = ''.join(p.read_text() for p in (ROOT / 'server').glob('*.lua')) if (ROOT / 'server').exists() else ''
    if 'hasObjectPermissionTo' not in lua: bad.append(('server', 'no ACL check found in server Lua'))
    return not bad, '%d mechanisms, %d moving parts, %d problems' % (len(W['interactive']), sum(len(v['parts']) for v in W['interactive'].values()), len(bad)), bad


@check('C12', 'Spawn / teleport points stand on collision with 1.8 m headroom and are not inside geometry')
def c12():
    bad = []; pts = [('room ' + rid, r['spawn']) for rid, r in W['rooms'].items() if r.get('spawn')]
    pts += [('teleport ' + k, v['pos']) for k, v in W['teleports'].items()]
    for name, p in pts:
        s = surface_below(p[0], p[1], p[2] + .05, up=.35, down=.6)
        if s is None: bad.append((name, p, 'no floor')); continue
        hit = solid_at(p[0], p[1], s + .45, s + 1.8, r=.2)
        if hit: bad.append((name, p, 'inside ' + hit))
    return not bad, '%d points probed, %d problems' % (len(pts), len(bad)), bad


def room_flood(r):
    """2.5-D walkability on a 0.4 m grid using the exported COL of the room's own models."""
    rec = R.ROOM[r['id']]; ix0, iy0, ix1, iy1 = R.inner_rect(rec)
    nx = int((ix1 - ix0) / CELL); ny = int((iy1 - iy0) / CELL)
    xs = ix0 + (np.arange(nx) + .5) * (ix1 - ix0) / nx; ys = iy0 + (np.arange(ny) + .5) * (iy1 - iy0) / ny
    surf = defaultdict(list); block = defaultdict(list)
    zlo, zhi = rec['z0'] - .6, rec['z0'] + rec['h'] + .2
    for mname in r['models']:
        o = next(o for o in W['objects'] if o['model'] == mname)
        _, bx, v, f = colmodel(mname); ox, oy, oz = o['pos']
        for b in bx:
            x0, y0, z0, x1, y1, z1 = b[0] + ox, b[1] + oy, b[2] + oz, b[3] + ox, b[4] + oy, b[5] + oz
            if z1 < zlo or z0 > zhi: continue
            i0, i1 = np.searchsorted(xs, x0 - PED_R), np.searchsorted(xs, x1 + PED_R)
            j0, j1 = np.searchsorted(ys, y0 - PED_R), np.searchsorted(ys, y1 + PED_R)
            for i in range(i0, i1):
                inx = x0 <= xs[i] <= x1
                for j in range(j0, j1):
                    block[(i, j)].append((z0, z1))
                    if inx and y0 <= ys[j] <= y1: surf[(i, j)].append(z1)
        if len(f):
            a, b2, c = v[f[:, 0]] + o['pos'], v[f[:, 1]] + o['pos'], v[f[:, 2]] + o['pos']
            nz = np.abs(np.cross(b2 - a, c - a)[:, 2]) / (np.linalg.norm(np.cross(b2 - a, c - a), axis=1) + 1e-9)
            for k in np.nonzero(nz > .7)[0]:
                tri = np.array([a[k], b2[k], c[k]])
                if tri[:, 2].max() < zlo or tri[:, 2].min() > zhi: continue
                i0, i1 = np.searchsorted(xs, tri[:, 0].min()), np.searchsorted(xs, tri[:, 0].max())
                j0, j1 = np.searchsorted(ys, tri[:, 1].min()), np.searchsorted(ys, tri[:, 1].max())
                for i in range(i0, i1):
                    for j in range(j0, j1):
                        zz = tri_z_at(tri, np.array([[0, 1, 2]]), xs[i], ys[j])
                        if len(zz): surf[(i, j)].append(float(zz[0]))
    nodes = {}
    for key, ss in surf.items():
        for s in sorted(set(round(x, 2) for x in ss)):
            if s < zlo or s > zhi - 1.0: continue
            if any(z0 < s + HEAD and z1 > s + STEP for z0, z1 in block[key]): continue
            nodes.setdefault(key, []).append(s)
    return xs, ys, nodes


def flood(nodes, start):
    seen = {start}; q = deque([start])
    while q:
        (i, j, s) = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (i + di, j + dj)
            for s2 in nodes.get(k, []):
                if abs(s2 - s) <= STEP and (k[0], k[1], s2) not in seen: seen.add((k[0], k[1], s2)); q.append((k[0], k[1], s2))
    return seen


@check('C13', 'Walkable 0.4 m flood fill per room: all doors at the same floor mutually reachable around furniture')
def c13():
    bad = []; stats = {}
    for r in L.ROOMS:
        rr = ROOMS[r['id']]; xs, ys, nodes = room_flood(rr)
        doors = []
        for (rid, e), lst in R.OPENINGS.items():
            if rid != r['id']: continue
            for o in lst:
                if o['kind'] in ('window', 'extwindow'): continue
                ax, c, _, _, sg = R.edge_line(r, e); n_in = R.inward(r, e); sm = (o['s0'] + o['s1']) / 2
                bx, by = (sm, c) if ax == 'y' else (c, sm)
                t = R.thickness(r, e) / 2 + .45; px, py = bx + n_in[0] * t, by + n_in[1] * t
                i = int(np.clip(np.searchsorted(xs, px) - (1 if np.searchsorted(xs, px) == len(xs) else 0), 0, len(xs) - 1))
                j = int(np.clip(np.searchsorted(ys, py) - (1 if np.searchsorted(ys, py) == len(ys) else 0), 0, len(ys) - 1))
                cand = []
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        for s in nodes.get((i + di, j + dj), []):
                            if abs(s - o['z0']) <= .3: cand.append((i + di, j + dj, s))
                doors.append((e, round(sm, 2), o['z0'], cand))
        nofloor = [(d[0], d[1], d[2]) for d in doors if not d[3]]
        if nofloor: bad.append((r['id'], 'door without walkable floor inside', nofloor))
        doors = [d for d in doors if d[3]]
        if not doors:      # spiral-only rooms (keep K1/K2): flood from the spiral arrival / spawn point
            sp = W['rooms'][r['id']]['spawn']
            i = int(np.argmin(np.abs(xs - sp[0]))); j = int(np.argmin(np.abs(ys - sp[1])))
            st = [(i + di, j + dj, s) for di in (-1, 0, 1) for dj in (-1, 0, 1) for s in nodes.get((i + di, j + dj), []) if abs(s - sp[2]) < .3]
            if not st: bad.append((r['id'], 'spawn not walkable')); continue
            doors = [('spawn', 0, sp[2], st)]
        reach = flood(nodes, doors[0][3][0]); total = sum(len(v) for v in nodes.values())
        for d in doors[1:]:
            if not any(c in reach for c in d[3]):
                if 'spiral' in r.get('special', {}) and abs(d[2] - doors[0][2]) > .5: continue   # via the spiral (C05)
                bad.append((r['id'], 'door unreachable', (doors[0][0], doors[0][1], doors[0][2]), (d[0], d[1], d[2])))
        stats[r['id']] = round(len(reach) / max(1, total), 3)
    low = {k: v for k, v in stats.items() if v < .5}
    return not bad, '%d rooms flooded, %d connectivity problems, mean reachable floor %.0f%%, rooms <50%%: %s' % (
        len(stats), len(bad), 100 * np.mean(list(stats.values())), ', '.join('%s=%.0f%%' % (k, 100 * v) for k, v in low.items()) or 'none'), {'bad': bad, 'reachable_fraction': stats}


@check('C14', 'Performance budget: vertex limits, object counts, streamed load near every spawn, package size')
def c14():
    bad = []
    if len(W['objects']) > 700: bad.append(('objects', len(W['objects'])))
    worst = (0, None, 0)
    for rid, r in W['rooms'].items():
        p = r.get('spawn')
        if not p: continue
        vs = 0; n = 0
        for o in W['objects']:
            cls = W['classes'][o['class']]
            if cls.get('mandatory'): continue
            a = AABB.get(id(o)) or world_aabb(o)
            dx = max(a[0] - p[0], 0, p[0] - a[3]); dy = max(a[1] - p[1], 0, p[1] - a[4])
            if math.hypot(dx, dy) < cls['radius']: vs += W['models'][o['model']]['vertices']; n += 1
        if vs > worst[0]: worst = (vs, rid, n)
    if worst[0] > 1_400_000: bad.append(('streamed vertices', worst))
    size = sum(f.stat().st_size for f in (ROOT / 'assets').rglob('*') if f.is_file())
    if size > 100 * 2 ** 20: bad.append(('asset size MB', size / 2 ** 20))
    over = [n for n, m in W['models'].items() if m['vertices'] > 60000]
    if over: bad.append(('near 65535 vertex limit', over))
    mand = sum(W['models'][o['model']]['vertices'] for o in W['objects'] if W['classes'][o['class']].get('mandatory'))
    return not bad, '%d objects, %d models, %.1f MB assets, always-on %d verts, worst streamed set %d verts / %d objects at room %s' % (
        len(W['objects']), len(W['models']), size / 2 ** 20, mand, worst[0], worst[2], worst[1]), bad


# ------------------------------------------------------------------ floor plan preview
def floorplan(path):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(HERE / 'vendor' / 'DejaVuSans-Bold.ttf'), 11); big = ImageFont.truetype(str(HERE / 'vendor' / 'DejaVuSans-Bold.ttf'), 20)
    G0, L0_ = L.G - .1, L.L0 + .1
    palace = (-80, -20, 80, 100)
    levels = [('L-2  dungeon / prison / secret vault', lambda r: abs(r['z0'] - L.L0 + 10) < .1, None),
              ('L-1  cellars, kitchens service, hidden stair', lambda r: abs(r['z0'] - L.L0 + 5) < .1, None),
              ('Ground / L0  whole ward (barracks, chapel, towers)', lambda r: G0 <= r['z0'] <= L0_, (-185, -185, 185, 185)),
              ('L0 state floor - palace & keep detail', lambda r: G0 <= r['z0'] <= L0_, palace),
              ('L1 private floor - palace & keep detail', lambda r: L0_ < r['z0'] < L.L0 + 7.2 and r.get('block') != 'barracks', palace),
              ('Upper: barracks L1, keep K1/K2, gatehouse, wall towers', lambda r: r['z0'] > L0_ and (r.get('block') in ('barracks', 'gatehouse', 'wall_tower', 'keep') or r['z0'] > L.L0 + 7.2 or r['id'].startswith('WT') or r['id'] == '36'), (-185, -185, 185, 185))]
    PW, PH = 900, 900
    img = Image.new('RGB', (PW * 3 + 40, PH * 2 + 110), (246, 241, 230)); dr = ImageDraw.Draw(img)
    dr.text((16, 10), 'ROYAL FORTRESS - generated floor plans (from docs/rooms.json; validator preview, not a render)', fill=(40, 30, 20), font=big)
    col = {'royal': (196, 160, 90), 'private': (170, 130, 160), 'admin': (110, 150, 180), 'military': (170, 90, 80), 'service': (140, 140, 110),
           'circulation': (205, 200, 190), 'extra': (160, 175, 140), 'underground': (120, 110, 110)}
    def bbox_of(pred):
        xs, ys = [], []
        for r in RM['rooms']:
            if not pred(r): continue
            if r.get('rect'): xs += [r['rect'][0], r['rect'][2]]; ys += [r['rect'][1], r['rect'][3]]
            elif 'center' in r: xs += [r['center'][0] - 9, r['center'][0] + 9]; ys += [r['center'][1] - 9, r['center'][1] + 9]
        return (min(xs) - 8, min(ys) - 8, max(xs) + 8, max(ys) + 8)
    for li, (title, pred, view) in enumerate(levels):
        pox = 10 + (li % 3) * (PW + 10); poy = 50 + (li // 3) * (PH + 20); ox = oy = 0
        panel = Image.new('RGB', (PW + 1, PH + 1), (246, 241, 230)); dr = ImageDraw.Draw(panel)
        vx0, vy0, vx1, vy1 = view or bbox_of(pred)
        S = min((PW - 20) / (vx1 - vx0), (PH - 50) / (vy1 - vy0))
        def T_(x, y, S=S, vx0=vx0, vy1=vy1, ox=ox, oy=oy): return ox + 10 + (x - vx0) * S, oy + 40 + (vy1 - y) * S
        dr.rectangle([ox, oy, ox + PW, oy + PH], outline=(120, 110, 90))
        dr.text((ox + 8, oy + 6), title + '   (scale: %.1f px/m)' % S, fill=(30, 30, 30), font=big)
        R_ = L.APO_WALL / math.cos(math.radians(15))
        pts = [T_(R_ * math.cos(math.radians(-75 + 30 * k)), R_ * math.sin(math.radians(-75 + 30 * k))) for k in range(12)]
        dr.polygon(pts, outline=(150, 140, 120))
        small = S < 4
        for r in RM['rooms']:
            if not pred(r): continue
            c = col.get(r.get('category'), (180, 180, 180))
            if r.get('shape') in ('rect', 'tunnel') and r.get('rect'):
                x0, y0, x1, y1 = r['rect']; a = T_(x0, y1); b = T_(x1, y0)
                dr.rectangle([a, b], fill=c, outline=(40, 35, 30), width=2)
                lab = r['id'] if small or (b[0] - a[0]) < 70 else '%s %s' % (r['id'], r['name'][:int((b[0] - a[0]) / 7)])
                dr.text((a[0] + 3, a[1] + 2), lab, fill=(20, 20, 20), font=font)
            elif 'center' in r:
                cx, cy = r['center']; rad = r.get('apothem_inner', 7.8) + .8; a = T_(cx - rad, cy + rad); b = T_(cx + rad, cy - rad)
                dr.ellipse([a, b], fill=c, outline=(40, 35, 30), width=2); dr.text((a[0] + 6, a[1] + 8), r['id'], fill=(20, 20, 20), font=font)
        for w in RM['windows']:
            r = ROOMS[w['room']]
            if pred(r):
                x, y = T_(*w['center']); dr.rectangle([x - 2, y - 2, x + 2, y + 2], fill=(70, 140, 220))
        for d in L.DOORS:
            if d['kind'] == 'window': continue
            for rid in (d['a'], d['b']):
                if rid in R.ROOM and pred(ROOMS[rid]):
                    r = R.ROOM[rid]; e, o0 = door_openings(d, r)
                    for o in ([o0] if o0 else []):
                        ax, c, _, _, _ = R.edge_line(r, e)
                        p0 = (o['s0'], c) if ax == 'y' else (c, o['s0']); p1 = (o['s1'], c) if ax == 'y' else (c, o['s1'])
                        clr = {'secret': (150, 0, 150), 'interactive': (200, 40, 30)}.get(d['kind'], (250, 250, 250))
                        dr.line([T_(*p0), T_(*p1)], fill=clr, width=5)
                    break
        for s in RM['stairs']:
            r = ROOMS[s['room']]
            if pred(r):
                x0, y0, x1, y1 = r['rect']
                for k in range(10):
                    xx = x0 + (x1 - x0) * (k + .5) / 10; dr.line([T_(xx, y0 + .6), T_(xx, y1 - .6)], fill=(90, 80, 70), width=1)
        for sp in RM['spirals']:
            if any(pred(r) and abs(r['z0'] - sp['from_z']) < .1 for r in RM['rooms'] if (r.get('rect') and r['rect'][0] <= sp['center'][0] <= r['rect'][2] and r['rect'][1] <= sp['center'][1] <= r['rect'][3]) or ('center' in r and math.hypot(r['center'][0] - sp['center'][0], r['center'][1] - sp['center'][1]) < 1)):
                a = T_(sp['center'][0] - 3, sp['center'][1] + 3); b = T_(sp['center'][0] + 3, sp['center'][1] - 3); dr.ellipse([a, b], outline=(60, 50, 40), width=2)
        dr.rectangle([0, 0, PW, PH], outline=(120, 110, 90)); img.paste(panel, (pox, poy))
    dr = ImageDraw.Draw(img)
    ly = PH * 2 + 80; x = 16
    for k, c in col.items():
        dr.rectangle([x, ly, x + 16, ly + 16], fill=c); dr.text((x + 20, ly + 1), k, fill=(20, 20, 20), font=font); x += 120
    for k, c in (('door', (250, 250, 250)), ('interactive door', (200, 40, 30)), ('secret passage', (150, 0, 150)), ('window', (70, 140, 220))):
        dr.rectangle([x, ly + 4, x + 22, ly + 10], fill=c, outline=(0, 0, 0)); dr.text((x + 26, ly + 1), k, fill=(20, 20, 20), font=font); x += 150
    img.save(path)


def main():
    R.compute_openings()
    t = time.time()
    for fn in (c01, c02, c03, c04, c05, c06, c07, c08, c09, c10, c11, c12, c13, c14): fn()
    floorplan(ROOT / 'docs' / 'FLOOR_PLANS.png')
    passed = sum(r['status'] == 'PASS' for r in RESULTS)
    rep = {'tool': 'tools/validate.py', 'type': 'STATIC ANALYSIS (not an in-game test)', 'date': time.strftime('%Y-%m-%d %H:%M'),
           'passed': passed, 'total': len(RESULTS), 'results': RESULTS, 'details': DETAILS, 'seconds': round(time.time() - t, 1)}
    (ROOT / 'docs' / 'validation_report.json').write_text(json.dumps(rep, indent=1, default=str))
    print('%d/%d checks passed (%.1fs)' % (passed, len(RESULTS), time.time() - t))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
