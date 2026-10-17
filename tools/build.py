"""PROJECT ROYAL FORTRESS - full asset build.
Order: openings -> room shells (+keep spirals) -> furnishing -> towers -> keep roof -> tunnel ->
exterior (walls, gates, roofs, perrons, courts, ward, checkpoints, belvedere) -> landscape
(terrain tiles, flora, roads+lamps, bridges, masonry, water stair) -> interactive parts -> LOD.
Writes assets/dff, assets/col, client/data/world.json, docs/rooms.json, development/heightfield.json."""
from __future__ import annotations
import json, math, sys, time, hashlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'vendor' / 'DragonFF'))
from fortlib import Mesh, Collision, bake, export_dff, export_col
import layout as L, rooms as R, towers as TW, props as P, furnish as FU, terrain as T, exterior as E
from materials import TEX_GROUP

ROOT = HERE.parent
OUT_DFF = ROOT / 'assets' / 'dff'; OUT_COL = ROOT / 'assets' / 'col'
SUN = {'dir': (-.4, -.5, -.75), 'color': (.60, .56, .48), 'sky': (.12, .14, .17)}
EXT_AMB = (.40, .40, .43)
CLASSES = {   # streaming: draw distance (engineSetModelLODDistance), stream-in radius, importance
    'terrain':  {'draw': 1200, 'radius': 2000, 'importance': 9.0, 'mandatory': True},
    'landmark': {'draw': 650, 'radius': 760, 'importance': 4.0},
    'lod':      {'draw': 1500, 'radius': 2000, 'importance': 3.0, 'mandatory': True},
    'building': {'draw': 300, 'radius': 420, 'importance': 2.5},
    'road':     {'draw': 400, 'radius': 480, 'importance': 2.2},
    'room':     {'draw': 150, 'radius': 170, 'importance': 2.0},
    'furn':     {'draw': 80, 'radius': 95, 'importance': 1.2},
    'tree':     {'draw': 250, 'radius': 300, 'importance': 1.0},
    'door':     {'draw': 120, 'radius': 140, 'importance': 1.6},
}
MODELS = {}; OBJECTS = []; FLAMES = []; INTERACTIVE = {}; ROOMREC = {}; STATS = {'vertices': 0, 'triangles': 0}


def rot_dir(d, deg):
    a = math.radians(-deg); c, s = math.cos(a), math.sin(a)
    return (d[0] * c - d[1] * s, d[0] * s + d[1] * c, d[2])


def add_model(name, m, col, cls, alpha=False, lod_of=None):
    assert name not in MODELS, name
    if not m.v: return None
    if not col.boxes and not col.faces:
        lo = np.min(np.asarray(m.v), axis=0); col.box((lo[0], lo[1], lo[2] - .06), (lo[0] + .1, lo[1] + .1, lo[2] - .01), 'stone')
    info = export_dff(m, OUT_DFF / (name + '.dff'), name)
    ci = export_col(col, OUT_COL / (name + '.col'), name, (np.array(info['bounds'][0]), np.array(info['bounds'][1])))
    groups = sorted({TEX_GROUP[t] for t in info['textures']})
    alpha = alpha or any(t in ('rf_glass', 'rf_fire', 'rf_leaf', 'rf_waterfx') for t in info['textures'])
    MODELS[name] = {'dff': 'assets/dff/%s.dff' % name, 'col': 'assets/col/%s.col' % name, 'txds': groups, 'alpha': alpha,
                    'class': cls, 'draw': CLASSES[cls]['draw'], 'vertices': info['vertices'], 'triangles': info['triangles'],
                    'bounds': info['bounds'], 'col_boxes': ci['boxes'], 'col_faces': ci['faces'], 'col_bounds': ci['bounds'],
                    'textures': info['textures']}
    STATS['vertices'] += info['vertices']; STATS['triangles'] += info['triangles']
    return name


def place(model, pos, rz=0.0, cls=None, room=None, lod=None, iid=None):
    if model is None: return
    OBJECTS.append({'model': model, 'pos': [round(float(v), 4) for v in pos], 'rot': [0.0, 0.0, round(float(rz), 4)],
                    'class': cls or MODELS[model]['class'], 'room': room, 'lod': lod, 'interactive': iid})


def part(p, sun=True):
    lights = list(p.lights)
    bake(p.m, EXT_AMB, lights, {**SUN, 'dir': rot_dir(SUN['dir'], p.rot)} if sun else None)
    return p


def window_lights(rid, origin):
    out = []
    for w in R.WINDOWS:
        if w['room'] != rid: continue
        r = R.ROOM[rid]; n = R.inward(r, w['edge'])
        p = (w['center'][0] + n[0] * 1.6 - origin[0], w['center'][1] + n[1] * 1.6 - origin[1], (w['z'][0] + w['z'][1]) / 2 - origin[2])
        out.append({'pos': list(p), 'color': [.50, .55, .62], 'radius': 8.5 + w['width'], 'power': .85})
    return out


def free_spot(F, r):
    """Walkable spawn point near the room centre (not inside furniture / stair zones)."""
    if r.get('special', {}).get('stair'):
        rec = next((s for s in R.STAIRS if s['room'] == r['id'] and s['type'] in ('U', 'I')), None)
        ix0, iy0, ix1, iy1 = R.inner_rect(r)
        if rec:
            if rec['type'] == 'U': x = sum(rec['entry_zone']) / 2; return [x, (iy0 + iy1) / 2, r['z0']]
            return [sum(rec['landing']) / 2, (iy0 + iy1) / 2, r['z0']]
    ix0, iy0, ix1, iy1 = F.inner; cx, cy = (ix0 + ix1) / 2, (iy0 + iy1) / 2
    occ = F.occ.get(0.0, []) + [b for b in F.blocked.get(0.0, []) if (b[2] - b[0]) * (b[3] - b[1]) > 30]
    if 'spiral' in r.get('special', {}): occ = occ + [(cx - 4.2, cy - 4.2, cx + 4.2, cy + 4.2)]
    best = None
    for x in np.arange(ix0 + .8, ix1 - .7, .5):
        for y in np.arange(iy0 + .8, iy1 - .7, .5):
            fp = (x - .45, y - .45, x + .45, y + .45)
            if any(F._hit(fp, b) for b in occ): continue
            d = (x - cx) ** 2 + (y - cy) ** 2
            if best is None or d < best[0]: best = (d, [round(float(x), 2), round(float(y), 2), r['z0']])
    return best[1] if best else [cx, cy, r['z0']]


def build_rooms():
    keep_sp = TW.keep_spiral_parts()
    for r in L.ROOMS:
        m, col, origin = R.room_shell(r, [])
        if r['id'] in keep_sp:
            sm, sc, so, _ = keep_sp[r['id']]; assert np.allclose(so, origin), (so, origin)
            m.merge(sm); col.merge(sc)
        F = FU.furnish_room(r, origin)
        lights = F.lights + window_lights(r['id'], origin)
        amb = R.AMBIENT[r['light']]
        bake(m, amb, lights); bake(F.m, amb, lights)
        rid = r['id']
        place(add_model('rm_' + rid.lower(), m, col, 'room'), origin, room=rid)
        if F.m.v:
            place(add_model('fu_' + rid.lower(), F.m, F.c, 'furn'), origin, room=rid)
        FLAMES.extend(dict(f, room=rid) for f in F.flames)
        for it in F.interactive: add_interactive_part(it['id'], it['model'], it['pos'], it['rot'], it)
        ROOMREC[rid] = {'furniture': F.log, 'lights': len(lights), 'spawn': free_spot(F, r), 'origin': list(origin)}


def build_towers():
    for key in L.TOWERS:
        rooms, (em, ec, eo) = TW.palace_tower(key)
        for rid, (m, col, origin, meta) in rooms.items():
            rec = next(p for p in TW.POLY_ROOMS if p['id'] == rid)
            F = FU.furnish_tower_room(rec, origin, meta['arrive_deg'])
            bake(m, R.AMBIENT['warm'], F.lights); bake(F.m, R.AMBIENT['warm'], F.lights)
            place(add_model('rm_' + rid.lower(), m, col, 'room'), origin, room=rid)
            place(add_model('fu_' + rid.lower(), F.m, F.c, 'furn'), origin, room=rid)
            FLAMES.extend(dict(f, room=rid) for f in F.flames)
            c = rec['center']; dk = rec['door_edges'][0] if rec['door_edges'] else 0
            spawn = None
            for rad in (5.0, 4.2, 3.4, 5.6):
                for da in range(0, 360, 15):
                    a = math.radians(15 * dk + da); x, y = c[0] + rad * math.cos(a), c[1] + rad * math.sin(a)
                    fp = (x - .5, y - .5, x + .5, y + .5)
                    if not any(F._hit(fp, bb) for bb in F.occ.get(0.0, []) + F.blocked.get(0.0, [])):
                        spawn = [round(x, 2), round(y, 2), rec['z0']]; break
                if spawn: break
            ROOMREC[rid] = {'furniture': F.log, 'lights': len(F.lights), 'origin': list(origin), 'spawn': spawn}
        bake(em, EXT_AMB, [], SUN)
        place(add_model('tw_' + key.lower() + '_ext', em, ec, 'landmark'), eo)
    # keep roof
    m, col, o = TW.keep_extras(); bake(m, EXT_AMB, [], SUN); place(add_model('keep_roof', m, col, 'landmark'), o)
    # escape tunnel
    m, col, o, zf = TW.tunnel(); rec = next(p for p in TW.POLY_ROOMS if p['id'] == 'TN')
    F = FU.furnish_tunnel(rec, o)
    bake(m, R.AMBIENT['dungeon'], F.lights); bake(F.m, R.AMBIENT['dungeon'], F.lights)
    place(add_model('rm_tn', m, col, 'room'), o, room='TN'); place(add_model('fu_tn', F.m, F.c, 'furn'), o, room='TN')
    FLAMES.extend(dict(f, room='TN') for f in F.flames)
    ROOMREC['TN'] = {'furniture': F.log, 'lights': len(F.lights), 'origin': list(o), 'spawn': [0.0, L.PALACE_DY + 6.0, rec['z0']]}
    # wall towers (shared model, rebased to G) + guard-post furniture
    for var in ('std', 'watch'):
        m, col = TW.wall_tower(var); E.rebase(m, col, -L.G)
        F = FU.furnish_wall_tower(var == 'watch'); E.rebase(F.m, F.c, -L.G)
        for lt in F.lights: lt['pos'][2] -= L.G
        bake(m, R.AMBIENT['work'], F.lights + [{'pos': [0, 0, L.WALK_Z - L.G + 3.0], 'color': [.5, .5, .55], 'radius': 9, 'power': .6}])
        bake(F.m, R.AMBIENT['work'], F.lights)
        add_model('wtower_' + var, m, col, 'landmark'); add_model('wtfurn_' + var, F.m, F.c, 'furn')
        if var == 'watch': WT_FLAMES['watch'] = F.flames
        else: WT_FLAMES['std'] = F.flames
    for wt in L.WALL_TOWERS:
        var = 'watch' if wt['id'] == '36' else 'std'; pos = (wt['c'][0], wt['c'][1], L.G)
        place('wtower_' + var, pos, wt['angle'], room=wt['id']); place('wtfurn_' + var, pos, wt['angle'], room=wt['id'])
        ca, sa = math.cos(math.radians(wt['angle'])), math.sin(math.radians(wt['angle']))
        for f in WT_FLAMES[var]:
            x, y, z = f['pos']
            FLAMES.append(dict(f, pos=[pos[0] + x * ca - y * sa, pos[1] + x * sa + y * ca, z], room=wt['id']))
        ROOMREC[wt['id']] = {'furniture': [], 'lights': 3, 'origin': list(pos), 'spawn': [pos[0] - 4.5 * ca, pos[1] - 4.5 * sa, L.WALK_Z]}
WT_FLAMES = {}


def build_facades():
    for block in L.BLOCKS:
        rs = [r for r in L.ROOMS if r['block'] == block]
        x0 = min(r['rect'][0] for r in rs); x1 = max(r['rect'][2] for r in rs); y0 = min(r['rect'][1] for r in rs); y1 = max(r['rect'][3] for r in rs)
        o = ((x0 + x1) / 2, (y0 + y1) / 2, L.BLOCKS[block]['ground'])
        m, col = R.facade(block, o)
        if not m.v: continue
        bake(m, EXT_AMB, [], SUN)
        place(add_model('fa_' + block, m, col, 'landmark' if block in ('palace', 'keep', 'chapel', 'gatehouse') else 'building'), o)


def build_exterior():
    seen = {}
    for p in E.curtain_wall_parts() + E.gate_parts():
        if p.name not in seen:
            part(p); seen[p.name] = add_model(p.name, p.m, p.col, p.cls)
        place(seen[p.name], p.origin, p.rot)
    for p in E.roof_parts() + E.ward_parts() + E.courtyard_parts() + [E.perrons()[0]]:
        part(p); place(add_model(p.name, p.m, p.col, p.cls, p.alpha), p.origin, p.rot); FLAMES.extend(p.flames)
    cps = E.checkpoint_parts()
    if cps:
        part(cps[0]); add_model('checkpoint', cps[0].m, cps[0].col, 'building')
        for p in cps: place('checkpoint', p.origin, p.rot); FLAMES.extend(p.flames)
    bz = T.ROAD_DATA['belvedere']['z'][-1] + .14
    p = E.belvedere_part(bz); part(p); place(add_model('belvedere', p.m, p.col, 'landmark'), p.origin); FLAMES.extend(p.flames)
    # LOD shells (no collision geometry, bounds only; they replace the detailed exterior far away)
    lm, lo = E.lod_palace(); bake(lm, EXT_AMB, [], SUN); add_model('lod_palace', lm, Collision(), 'lod'); place('lod_palace', lo, cls='lod')
    wm, _ = E.rebase(E.lod_wall()[0], Collision(), -L.G); bake(wm, EXT_AMB, [], SUN); add_model('lod_wall', wm, Collision(), 'lod'); place('lod_wall', (0, 0, L.G), cls='lod')


def build_landscape():
    tiles = int(2 * T.EXT / T.TILE)
    trees = T.scatter_trees(); TREES_BY = {}
    for (x, y, z, kind, s) in trees:
        TREES_BY.setdefault((int((x + T.EXT) // T.TILE), int((y + T.EXT) // T.TILE)), []).append((x, y, z, kind, s))
    road_pieces, lamps = T.road_mesh_pieces(); ROAD_BY = {}
    for (mid, m, col) in road_pieces:
        ROAD_BY.setdefault((int((mid[0] + T.EXT) // T.TILE), int((mid[1] + T.EXT) // T.TILE)), []).append((m, col))
    LAMP_BY = {}
    for (x, y, z) in lamps:
        LAMP_BY.setdefault((int((x + T.EXT) // T.TILE), int((y + T.EXT) // T.TILE)), []).append((x, y, H_ground(x, y)))
    proto = {k: T.tree(k, 1.0) for k in ('oak', 'pine')}
    lamp = P.lantern_post(4.0)
    for ix in range(tiles):
        for iy in range(tiles):
            m, col, o = T.terrain_tile(ix, iy)
            if not m.v: continue
            bake(m, EXT_AMB, [], SUN)
            place(add_model('ter_%d_%d' % (ix, iy), m, col, 'terrain'), o)
            tr = TREES_BY.get((ix, iy), [])
            if tr:
                fm = Mesh(); fc = Collision()
                for (x, y, z, kind, s) in tr:
                    fm.merge(proto[kind].m, (x - o[0], y - o[1], z - .2 - o[2]), (x * 37.0) % 360, s)
                    r = .4 * s; fc.box((x - o[0] - r, y - o[1] - r, z - o[2] - .2), (x - o[0] + r, y - o[1] + r, z - o[2] + 3.0 * s), 'wood')
                bake(fm, (.45, .47, .42), [], SUN)
                place(add_model('flora_%d_%d' % (ix, iy), fm, fc, 'tree', alpha=True), o)
            rp = ROAD_BY.get((ix, iy), []); lp = LAMP_BY.get((ix, iy), [])
            if rp or lp:
                rm = Mesh(); rc = Collision()
                for (pm, pc) in rp:
                    rm.merge(pm, (-o[0], -o[1], -o[2]))
                    sh = pc.transformed((-o[0], -o[1], -o[2])); rc.merge(sh)
                for (x, y, z) in lp:
                    rm.merge(lamp.m, (x - o[0], y - o[1], z - o[2])); rc.merge(lamp.c.transformed((x - o[0], y - o[1], z - o[2])))
                    FLAMES.extend(dict(f, pos=[f['pos'][0] + x, f['pos'][1] + y, f['pos'][2] + z]) for f in lamp.flames)
                bake(rm, EXT_AMB, [], SUN)
                place(add_model('road_%d_%d' % (ix, iy), rm, rc, 'road'), o)
    # river bridges, moat bridges, masonry rings, water stair
    for i, b in enumerate(T.bridge_spans()):
        m, col, mid, ang = T.stone_bridge(b['a'], b['b'], b['za'], b['zb'], b['w']); bake(m, EXT_AMB, [], {**SUN, 'dir': rot_dir(SUN['dir'], ang)})
        place(add_model('bridge_%s_%d' % (b['road'], i), m, col, 'landmark'), mid, ang)
    for name, a, b in (('bridge_gate', (0.0, -183.0), (0.0, -195.5)), ('bridge_service', (173.0, 0.0), (195.5, 0.0))):
        m, col, mid, ang = T.stone_bridge(a, b, L.G, L.G, 5.4 if name == 'bridge_gate' else 6.0)
        bake(m, EXT_AMB, [], {**SUN, 'dir': rot_dir(SUN['dir'], ang)}); place(add_model(name, m, col, 'landmark'), mid, ang)
    wm, wc, wo, (sx0, sx1), ztop = T.water_stair()
    m, col, o = T.ring_wall(L.APO_REV, T.MOAT_BED - .5, L.G, True, holes=[(3, -2.0, 2.0, L.W + 1.5, L.W + 1.5 + 3.9)],
                            coping=(L.G - .1, L.G + .9), gaps=[(9, -3.0, 3.0), (0, -3.6, 3.6)])
    bake(m, EXT_AMB, [], SUN); place(add_model('masonry_revetment', m, col, 'landmark'), o)
    m, col, o = T.ring_wall(L.APO_MOAT_OUT, T.MOAT_BED - .5, L.G, False, coping=(L.G - .7, L.G + .55),
                            gaps=[(9, -3.4, 3.4), (0, -3.6, 3.6), (3, -sx1, -sx0)])
    bake(m, EXT_AMB, [], SUN); place(add_model('masonry_counterscarp', m, col, 'landmark'), o)
    bake(wm, EXT_AMB, [], SUN); place(add_model('water_stair', wm, wc, 'building'), wo)
    return len(trees), len(lamps)


def road_z(x, y):
    best = None
    for rd in T.ROAD_DATA.values():
        for p, z in zip(rd['pts'], rd['z']):
            d = math.hypot(p[0] - x, p[1] - y)
            if best is None or d < best[0]: best = (d, z)
    return round(max(best[1], T.H(x, y)) + .02, 3)


def spiral_links():
    out = []
    allr = [(r['id'], r) for r in L.ROOMS] + [(p['id'], p) for p in TW.POLY_ROOMS]
    for sp in TW.SPIRALS:
        cx, cy = sp['center']; ends = []
        for z in (sp['from_z'], sp['to_z']):
            for rid, r in allr:
                if abs(r['z0'] - z) > .05: continue
                if 'rect' in r:
                    x0, y0, x1, y1 = r['rect']
                    if x0 <= cx <= x1 and y0 <= cy <= y1: ends.append(rid); break
                elif 'center' in r and math.hypot(r['center'][0] - cx, r['center'][1] - cy) < 1.0: ends.append(rid); break
        if len(ends) == 2: out.append(tuple(ends))
    return out


def H_ground(x, y):
    return T.H(x, y)


# ====================================================================== interactive parts
LEAF_STYLE = {'palace_doors': 'grand', 'throne_doors': 'grand', 'chapel_doors': 'grand', 'treasury_door': 'iron', 'interrogation_door': 'iron',
              'armory_door': 'iron', 'dungeon_gate': 'bars', 'tunnel_gate': 'bars'}
LEAF_MODELS = {}


def leaf_model(w, h, style):
    key = 'it_leaf_%s_%d_%d' % (style, round(w * 100), round(h * 100))
    if key not in LEAF_MODELS:
        p = P.door_leaf(w, h, style); bake(p.m, (.55, .52, .48), [], None)
        LEAF_MODELS[key] = add_model(key, p.m, p.c, 'door')
    return LEAF_MODELS[key]


def add_interactive_part(iid, model, pos, rot, extra=None, motion=None):
    meta = L.INTERACTIVE[iid]
    rec = INTERACTIVE.setdefault(iid, {'name': meta['name'], 'kind': meta['kind'], 'acl': meta['acl'], 'default': meta['default'],
                                       'needs': meta.get('needs'), 'moved_is_open': iid != 'drawbridge',
                                       'operable': meta['kind'] != 'slide' or not meta.get('needs'), 'parts': []})
    if model not in MODELS:
        if model == 'it_celldoor': p = P.cell_door(1.14, 2.5)
        elif model == 'it_booklever': p = P.book_lever()
        else: raise KeyError(model)
        bake(p.m, (.5, .48, .45), [], None); add_model(model, p.m, p.c, 'door')
    mv = motion or {}
    if extra and 'slide' in extra: mv = {'move': extra['slide'], 'rot': [0, 0, 0]}
    if meta['kind'] == 'lever' and not mv: mv = {'move': [0, 0, 0], 'rot': [0, -25, 0]}
    rec['parts'].append({'model': model, 'pos': [round(float(v), 4) for v in pos], 'rot': [0.0, 0.0, float(rot)], 'open': mv})


def build_interactive():
    for d in L.DOORS:
        if d['kind'] not in ('interactive', 'secret') or not d['iid']: continue
        iid = d['iid']; ra = R.ROOM.get(d['a']); rb = R.ROOM.get(d['b'])
        r = ra if ra is not None else rb
        e = R.door_edge(d, r)
        op = next(o for o in R.OPENINGS[(r['id'], e)] if o['door'] is d)
        ax, c, _, _, sg = R.edge_line(r, e)
        into = rb if (rb is not None and d['b'] != 'EXT') else r
        inw = R.inward(r, e) * (1 if into is r else -1)       # world vector pointing into the 'into' room
        s0, s1, z0, z1 = op['s0'], op['s1'], op['z0'], op['z1']; w = s1 - s0; h = z1 - z0
        kind = L.INTERACTIVE[iid]['kind']
        if ax == 'y': base_rot = 0.0; P0 = lambda s, off=0.0: (s, c + off, z0)
        else: base_rot = 90.0; P0 = lambda s, off=0.0: (c + off, s, z0)
        # sign of a CCW rotation for a leaf spanning +s: +s rotated +90 equals the edge 'left' normal
        left = np.array((0, 1, 0)) if ax == 'y' else np.array((-1, 0, 0))
        ccw_into = 1 if np.dot(left, inw) > 0 else -1
        if kind == 'slide' and iid == 'library_bookcase':
            p = P.bookcase_door(w, h - .02); bake(p.m, (.45, .4, .32), [], None)
            mdl = add_model('it_bookcase', p.m, p.c, 'door')
            sc = (s0 + s1) / 2; dvec = [-2.0, 0, 0] if ax == 'y' else [0, -2.0, 0]
            add_interactive_part(iid, mdl, P0(sc), base_rot, motion={'move': dvec, 'rot': [0, 0, 0]})
            continue
        if kind == 'vault':
            p = P.vault_door(1.6); bake(p.m, (.5, .48, .45), [], None)
            mdl = add_model('it_vaultdoor', p.m, p.c, 'door')
            off = -(R.thickness(r, e) / 2 + .27) * (1 if into is r else -1)  # mounted on the outer (approach) face
            face_dir = -inw
            rot = base_rot + (0 if np.dot(face_dir, left) < 0 else 180)
            hinge_s = s0 - .6 if rot == base_rot else s1 + .6
            pos = P0(hinge_s, off * sg if ax == 'y' else off * sg)
            pos = (pos[0], pos[1], z0 - .1)
            add_interactive_part(iid, mdl, pos, rot, motion={'move': [0, 0, 0], 'rot': [0, 0, -95 if rot == base_rot else 95]})
            continue
        style = LEAF_STYLE.get(iid, 'oak')
        if kind == 'swing2':
            mdl = leaf_model(w / 2, h - .02, style)
            add_interactive_part(iid, mdl, P0(s0), base_rot, motion={'move': [0, 0, 0], 'rot': [0, 0, 95 * ccw_into]})
            add_interactive_part(iid, mdl, P0(s1), base_rot + 180, motion={'move': [0, 0, 0], 'rot': [0, 0, -95 * ccw_into]})
        else:
            mdl = leaf_model(w, h - .02, style)
            add_interactive_part(iid, mdl, P0(s0), base_rot, motion={'move': [0, 0, 0], 'rot': [0, 0, 95 * ccw_into]})
    G = L.G; AW = L.APO_WALL
    # gatehouse: portcullis (lift 4.6), inner doors (swing2), drawbridge (raise rx -80), service gate leaves, dock gate
    p = P.portcullis(5.2, 7.0); bake(p.m, (.5, .5, .5), [], SUN); add_model('it_portcullis', p.m, p.c, 'door')
    add_interactive_part('main_portcullis', 'it_portcullis', (0.0, -AW - 4.55, G), 0.0, motion={'move': [0, 0, 4.6], 'rot': [0, 0, 0]})
    gl = leaf_model(2.6, 6.8, 'gate')
    add_interactive_part('gate_doors', gl, (-2.6, -AW + 3.95, G), 0.0, motion={'move': [0, 0, 0], 'rot': [0, 0, 95]})
    add_interactive_part('gate_doors', gl, (2.6, -AW + 3.95, G), 180.0, motion={'move': [0, 0, 0], 'rot': [0, 0, -95]})
    p = P.drawbridge(5.0, 10.0); p.m.v = [(-x, -y, z) for (x, y, z) in p.m.v]; p.c = p.c.transformed((0, 0, 0), 180)
    bake(p.m, EXT_AMB, [], SUN); add_model('it_drawbridge', p.m, p.c, 'door')
    add_interactive_part('drawbridge', 'it_drawbridge', (0.0, -L.APO_REV, G), 0.0, motion={'move': [0, 0, 0], 'rot': [-80, 0, 0]})
    sl = leaf_model(3.0, 5.4, 'gate')
    add_interactive_part('service_gate', sl, (AW - 1.9, -3.0, G), 90.0, motion={'move': [0, 0, 0], 'rot': [0, 0, 95]})
    add_interactive_part('service_gate', sl, (AW - 1.9, 3.0, G), 270.0, motion={'move': [0, 0, 0], 'rot': [0, 0, -95]})
    p = P.portcullis(4.0, 3.9); bake(p.m, (.4, .4, .4), [], None); add_model('it_watergate', p.m, p.c, 'door')
    add_interactive_part('dock_gate', 'it_watergate', (0.0, L.APO_REV - .5, L.W + 1.5), 0.0, motion={'move': [0, 0, 3.6], 'rot': [0, 0, 0]})
    # book lever beside the secret bookcase (room 21, south wall, east of the opening)
    ix0, iy0, ix1, iy1 = R.inner_rect(R.ROOM['21'])
    add_interactive_part('book_lever', 'it_booklever', (ix1 - .55, iy0 + .16, R.ROOM['21']['z0'] + 1.45), 0.0)
    INTERACTIVE['book_lever']['parts'][:] = INTERACTIVE['book_lever']['parts'][-1:]
    missing = set(L.INTERACTIVE) - set(INTERACTIVE)
    assert not missing, missing


def main():
    t0 = time.time()
    for d in (OUT_DFF, OUT_COL):
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob('*'): f.unlink()
    R.compute_openings(); T.finalize()
    build_rooms(); print('rooms', len(MODELS), round(time.time() - t0, 1))
    build_towers(); print('towers', len(MODELS), round(time.time() - t0, 1))
    build_facades(); build_exterior(); print('exterior', len(MODELS), round(time.time() - t0, 1))
    ntrees, nlamps = build_landscape(); print('landscape', len(MODELS), round(time.time() - t0, 1))
    build_interactive(); print('interactive', len(MODELS), round(time.time() - t0, 1))
    write_manifests(ntrees, nlamps)
    print('DONE models=%d objects=%d flames=%d verts=%d %.1fs' % (len(MODELS), len(OBJECTS), len(FLAMES), STATS['vertices'], time.time() - t0))


def write_manifests(ntrees, nlamps):
    txds = {g: {'path': 'assets/txd/%s.txd' % g} for g in ('rf_struct', 'rf_deco', 'rf_nature')}
    for g, v in txds.items():
        v['sha256'] = hashlib.sha256((ROOT / v['path']).read_bytes()).hexdigest()
    rooms_brief = {}
    # rooms behind ACL-locked doors: /castleroom must not bypass the lock
    def bfs(allowed):
        g = {}
        for d in L.DOORS:
            if d['kind'] == 'window': continue
            acl = L.INTERACTIVE[d['iid']]['acl'] if d['iid'] else None
            if acl and acl not in allowed: continue
            g.setdefault(d['a'], set()).add(d['b']); g.setdefault(d['b'], set()).add(d['a'])
        for a, b2 in spiral_links(): g.setdefault(a, set()).add(b2); g.setdefault(b2, set()).add(a)
        seen = {'EXT'}; st = ['EXT']
        while st:
            u = st.pop()
            for v in g.get(u, ()):
                if v not in seen: seen.add(v); st.append(v)
        return seen
    free = bfs(set()); ROOM_ACL = {}
    for right in ('gate', 'archive', 'vault'):
        for rid in bfs({right}) - free: ROOM_ACL.setdefault(rid, right)
    allrooms = [dict(r) for r in L.ROOMS] + [dict(p) for p in TW.POLY_ROOMS]
    for wt in L.WALL_TOWERS:
        allrooms.append({'id': wt['id'], 'name': wt['name'], 'block': 'wall_tower', 'shape': 'poly24', 'center': list(wt['c']), 'z0': L.WALK_Z, 'h': 6.0, 'level': 'W', 'category': 'military' if wt['id'] == '36' else 'extra'})
    for r in allrooms:
        rec = ROOMREC.get(r['id'], {})
        geo = {'rect': list(r['rect'])} if 'rect' in r else ({'center': list(r['center']), 'radius': r.get('apothem_inner', 7.8)} if 'center' in r else {})
        rooms_brief[r['id']] = {'name': r.get('name') or L.TOWER_NAMES.get(r['id'], r['id']), 'level': r.get('level', ''), 'spawn': rec.get('spawn'),
                                'category': r.get('category', ''), 'z0': r['z0'], 'h': r.get('h', 6.0), 'acl': ROOM_ACL.get(r['id']), **geo}
    world = {
        'format': 'royal_fortress/world@1', 'dimension': L.DIM, 'base_z': L.BASE, 'ground_z': L.G, 'water': [{'x0': -1400, 'y0': -1400, 'x1': 1400, 'y1': 1400, 'z': L.W}],
        'classes': CLASSES, 'txds': txds, 'models': MODELS, 'objects': OBJECTS, 'interactive': INTERACTIVE,
        'teleports': {k: {'label': v[0], 'pos': [v[1], v[2], v[3] if v[3] is not None else road_z(v[1], v[2])], 'rot': v[4]} for k, v in L.PUBLIC_TELEPORTS.items()},
        'spawn_z_offset': 1.0,
        'rooms': rooms_brief, 'flames': [{k: (round(x, 3) if isinstance(x, float) else x) for k, x in f.items()} for f in FLAMES],
        'stats': {**STATS, 'models': len(MODELS), 'objects': len(OBJECTS), 'trees': ntrees, 'road_lamps': nlamps},
    }
    world['teleports']['showp']['pos'][2] = round(T.ROAD_DATA['belvedere']['z'][-1] + .14 + .72, 3)   # pavilion platform top
    cd = ROOT / 'client' / 'data'; cd.mkdir(parents=True, exist_ok=True)
    (cd / 'world.json').write_text(json.dumps(world, separators=(',', ':')))
    # full room manifest
    doors = []
    for i, d in enumerate(L.DOORS):
        doors.append({'index': i, 'a': d['a'], 'b': d['b'], 'at': d['at'], 'width': d['w'], 'height': d['h'], 'kind': d['kind'], 'interactive': d['iid'], 'z': d['z'], 'side': d['side'], 'sill': d['sill']})
    conn = {}
    for d in L.DOORS:
        if d['kind'] == 'window': continue
        conn.setdefault(d['a'], set()).add(d['b']); conn.setdefault(d['b'], set()).add(d['a'])
    links = spiral_links()
    for a, b2 in links: conn.setdefault(a, set()).add(b2); conn.setdefault(b2, set()).add(a)
    for wt in L.WALL_TOWERS: conn.setdefault(wt['id'], set()).add('WALK')
    rooms_full = []
    for r in allrooms:
        rec = ROOMREC.get(r['id'], {})
        out = {k: v for k, v in r.items() if k not in ('special',)}
        out['special'] = {k: v for k, v in r.get('special', {}).items()}
        out['connections'] = sorted(conn.get(r['id'], set()))
        out['openings'] = [{'edge': e, **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items() if k in ('s0', 's1', 'z0', 'z1', 'kind', 'ext')}} for (rid, e), lst in R.OPENINGS.items() if rid == r['id'] for o in lst]
        out['windows'] = [w for w in R.WINDOWS if w['room'] == r['id']]
        out['stairs'] = [s for s in R.STAIRS if s['room'] == r['id']]
        out['furniture'] = rec.get('furniture', []); out['light_sources'] = rec.get('lights', 0); out['spawn'] = rec.get('spawn')
        out['models'] = sorted({o['model'] for o in OBJECTS if o['room'] == r['id']})
        out['collision'] = {m: {'boxes': MODELS[m]['col_boxes'], 'faces': MODELS[m]['col_faces'], 'bounds': MODELS[m]['col_bounds']} for m in out['models']}
        rooms_full.append(out)
    dd = ROOT / 'docs'; dd.mkdir(parents=True, exist_ok=True)
    (dd / 'rooms.json').write_text(json.dumps({'format': 'royal_fortress/rooms@1', 'rooms': rooms_full, 'doors': doors, 'spirals': TW.SPIRALS,
                                               'stairs': R.STAIRS, 'windows': R.WINDOWS, 'perrons': E.perrons()[1], 'spiral_links': links}, indent=1, default=list))
    (ROOT / 'development' / 'heightfield.json').write_text(json.dumps(T.heightfield(8.0), separators=(',', ':')))


if __name__ == '__main__':
    main()
