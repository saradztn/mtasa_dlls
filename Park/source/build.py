# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# build.py - one command build of the complete park:     python3 build.py
#   writes ../model/*.dff (one atomic per model)  ../texture/{ground,flora,struct,props}.txd  ../collision/*.col
#          ../audio/*.wav  and the ready to use MTA resource ../resource/Park/ (files/, models.lua, layout.lua, meta.xml)
# Then run validate.py, mta_lua_test.py and preview_park.py.
# -----------------------------------------------------------------------------
import json, os, shutil, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pk import tex, bake, layout as LY, scene, audio, assets_small, assets_plants, assets_big
from pk.kit import REG, bbox
from pk.mb import Mesh, Col
from lib import dxt, rwdff, rwtxd, colfile

OUT = os.path.abspath(os.path.join(HERE, '..'))
SURF = dict(grass=10, dirt=26, pondbed=38)          # COL surface ids of the ground triangles (footsteps / friction)


def weld(pos, nrm, uv, dcol, ncol, tris):
    key = np.concatenate([np.round(pos * 1000).astype(np.int64), np.round(nrm * 60).astype(np.int64), np.round(uv * 4000).astype(np.int64),
                          dcol.astype(np.int64), ncol.astype(np.int64)], axis=1)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    return pos[first], nrm[first], uv[first], dcol[first], ncol[first], inv[tris]


def mat_chunk(name):
    return dict(tex=name, env=0, color=(255, 255, 255, 255), surface=(1.0, 0.0, 1.0))


def build_geometry(pos, nrm, uv, tris, tmat, day, night):
    """-> geometry dict + used material list (one atomic per model)"""
    area = np.linalg.norm(np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]]), axis=1)
    keep = area > 1e-9
    tris, tmat = tris[keep], tmat[keep]
    used_v, inv = np.unique(tris.reshape(-1), return_inverse=True)
    t2 = inv.reshape(-1, 3)
    c = lambda a: np.concatenate([(a[used_v] * 255 + 0.5).astype(np.uint8), np.full((len(used_v), 1), 255, np.uint8)], 1)
    p, n, u, d, nc, t3 = weld(pos[used_v], nrm[used_v], uv[used_v], c(day), c(night), t2)
    mats = sorted(set(tmat.tolist()))
    remap = {mm: i for i, mm in enumerate(mats)}
    tm = np.array([remap[mm] for mm in tmat], np.int64)
    # sort triangles by material (stable) so every material owns one contiguous run
    order = np.argsort(tm, kind='stable')
    assert len(p) < 65000, len(p)
    return dict(pos=p, nrm=n, uv=u, tris=t3[order], tri_mat=tm[order], prelit=d, night=nc, dyn_light=False), mats


def build_col(C, name, model_id, bounds, faces_mesh=None):
    """boxes + oriented prisms (+ optional triangle mesh) -> COL3 bytes; bounds = (lo, hi) of the visual mesh (culling)"""
    verts, faces, vmap = [], [], {}

    def vid(p):
        k = tuple(int(round(c * 128)) for c in p)
        if k not in vmap:
            vmap[k] = len(verts)
            verts.append(np.array(k) / 128.0)
        return vmap[k]
    for cc in C.prisms:
        cc = np.asarray(cc, float)
        b, t = cc[:4], cc[4:]
        area = sum(b[i][0] * b[(i + 1) % 4][1] - b[(i + 1) % 4][0] * b[i][1] for i in range(4))
        if area < 0:
            b, t = b[::-1], t[::-1]
        ib = [vid(p) for p in b]
        it = [vid(p) for p in t]
        faces += [(ib[0], ib[2], ib[1], 0), (ib[0], ib[3], ib[2], 0), (it[0], it[1], it[2], 0), (it[0], it[2], it[3], 0)]
        for i in range(4):
            j = (i + 1) % 4
            faces += [(ib[i], ib[j], it[j], 0), (ib[i], it[j], it[i], 0)]
    if faces_mesh is not None:
        P, F, S = faces_mesh
        base = {}
        for a, b_, c_, s in zip(F[:, 0], F[:, 1], F[:, 2], S):
            ids = [vid(P[q]) for q in (a, b_, c_)]
            if len(set(ids)) == 3:
                faces.append((ids[0], ids[1], ids[2], int(s)))
    boxes = [(lo, hi, 0) for lo, hi in C.boxes]
    assert len(verts) < 32767 and len(faces) < 65535, (name, len(verts), len(faces))
    V = np.array(verts) if verts else None
    if V is not None:
        assert np.abs(V).max() < 255.9, (name, 'collision vertex outside int16/128 range')
    if not boxes and not faces:                          # non solid model: 2 cm stub cube hidden at the origin
        boxes = [((-0.01, -0.01, -0.02), (0.01, 0.01, 0.0), 0)]
    col = colfile.build_col3(name, model_id, [], boxes, V.tolist() if V is not None else None, faces if faces else None, bounds=bounds)
    return col, len(boxes), len(faces), len(verts)


def main():
    t0 = time.time()
    for d in ('model', 'texture', 'collision', 'preview', 'audio'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
        if d in ('model', 'collision', 'texture'):
            for f in os.listdir(os.path.join(OUT, d)):
                os.remove(os.path.join(OUT, d, f))
    print('[1/7] layout ...')
    L = LY.build_layout()
    print('   %d placed objects, %d lamps, %d sit points, %d trees' % (len(L.obj), len(L.lamps), len(L.sit), len(L.trees)))
    print('[2/7] models (geometry + baked day/night colours) ...')
    models = []          # dict(name, cat, geom, mats, col, alpha, dist, stats)
    for name, fn in REG.items():
        a = fn()
        pos, nrm, uv, tris, tmat, emis = bake.flatten(a.M)
        day = bake.bake(pos, nrm, emis, bake.DAY, a.ao, glow=a.day_glow)
        night = bake.bake(pos, nrm, emis, bake.NIGHT, a.ao, glow=1.0)
        g, mats = build_geometry(pos, nrm, uv, tris, tmat, day, night)
        lo, hi = bbox(a.M)
        models.append(dict(name=name, cat=a.cat, geom=g, mats=mats, C=a.C, bounds=(lo.tolist(), hi.tolist()), dist=a.dist, alpha=any(mm in tex.ALPHA for mm in mats), faces=None))
    print('[3/7] ground tiles ...')
    tiles, hf = scene.ground_meshes()
    for (ix, iy), M in sorted(tiles.items()):
        name = 'pk_ground_%d_%d' % (ix, iy)
        cx, cy = (LY.TILE_X[ix] + LY.TILE_X[ix + 1]) / 2, (LY.TILE_Y[iy] + LY.TILE_Y[iy + 1]) / 2
        pos, nrm, uv, tris, tmat, col_d = scene.bake_ground(M, L, bake.DAY, False)
        _, _, _, _, _, col_n = scene.bake_ground(M, L, bake.NIGHT, True)
        org = np.array([cx, cy, 0.0])
        g, mats = build_geometry(pos - org, nrm, uv, tris, tmat, col_d, col_n)
        P, N, F = hf[(ix, iy)]
        # collision mesh = the height field only (paths are 4 cm decals); material per triangle from the visual chunk
        surf = []
        for t in F:
            r = float(LY.pond_r(P[t][:, 0].mean(), P[t][:, 1].mean()))
            surf.append(SURF['pondbed'] if r < 0.80 else (SURF['dirt'] if r < 0.93 else SURF['grass']))
        lo, hi = (pos - org).min(0), (pos - org).max(0)
        models.append(dict(name=name, cat='ground', geom=g, mats=mats, C=Col(), bounds=(lo.tolist(), hi.tolist()), dist=400.0, alpha=False,
                           faces=(P - org, F, surf), origin=(float(cx), float(cy), 0.0)))
    # model ids are assigned by the client at run time (engineRequestModel) -> the COL header id is only informative
    print('[4/7] textures ...')
    imgs = tex.generate_all()
    cats = {}
    for mo in models:
        cats.setdefault(mo['cat'], set()).update(tex.NAMES[mm] for mm in mo['mats'])
    txd_info = {}
    for cat, names in sorted(cats.items()):
        lst = []
        for n in tex.NAMES:
            if n not in names:
                continue
            im = imgs[n]
            h, w = im.shape[:2]
            fmt = 'DXT5' if tex.IDX[n] in tex.ALPHA else 'DXT1'
            chain = dxt.compress_chain(im, fmt)
            lst.append(dict(name=n, w=w, h=h, fmt=fmt, chain=chain, alpha=(fmt == 'DXT5')))
        b = rwtxd.build_txd(lst)
        open(os.path.join(OUT, 'texture', cat + '.txd'), 'wb').write(b)
        txd_info[cat] = dict(bytes=len(b), textures=[(t['name'], t['w'], t['h'], t['fmt']) for t in lst])
        print('   %-7s %2d textures  %.2f MB' % (cat, len(lst), len(b) / 1048576))
    print('[5/7] DFF + COL ...')
    report = []
    for i, mo in enumerate(models):
        g, mats = mo['geom'], mo['mats']
        frames = [dict(name=mo['name'], pos=(0, 0, 0), parent=-1), dict(name=mo['name'] + '_a', pos=(0, 0, 0), parent=0)]
        dff = rwdff.build_clump(frames, [g], [(1, 0, False)], [[mat_chunk(tex.NAMES[mm]) for mm in mats]])
        open(os.path.join(OUT, 'model', mo['name'] + '.dff'), 'wb').write(dff)
        col, nb, nf, nv = build_col(mo['C'], mo['name'], 1337, mo['bounds'], mo['faces'])
        open(os.path.join(OUT, 'collision', mo['name'] + '.col'), 'wb').write(col)
        mo.update(dff_bytes=len(dff), col_bytes=len(col))
        report.append(dict(name=mo['name'], cat=mo['cat'], verts=int(len(g['pos'])), tris=int(len(g['tris'])), materials=[tex.NAMES[mm] for mm in mats], alpha=mo['alpha'],
                           col_boxes=nb, col_faces=nf, dff=len(dff), col=len(col)))
    print('   %d models  DFF %.2f MB  COL %.2f MB' % (len(models), sum(m_['dff_bytes'] for m_ in models) / 1048576, sum(m_['col_bytes'] for m_ in models) / 1048576))
    print('[6/7] audio ...')
    wavs = audio.make_all(os.path.join(OUT, 'audio'))
    print('   ', ', '.join(wavs))
    print('[7/7] resource ...')
    res = os.path.join(OUT, 'resource', 'Park')
    if os.path.isdir(os.path.join(res, 'files')):
        shutil.rmtree(os.path.join(res, 'files'))
    os.makedirs(os.path.join(res, 'files'), exist_ok=True)
    os.makedirs(os.path.join(res, 'files', 'audio'), exist_ok=True)
    files = []
    for mo in models:
        for sub, ext in (('model', 'dff'), ('collision', 'col')):
            fn = '%s.%s' % (mo['name'], ext)
            shutil.copyfile(os.path.join(OUT, sub, fn), os.path.join(res, 'files', fn))
            files.append(fn)
    for cat in sorted(cats):
        fn = cat + '.txd'
        shutil.copyfile(os.path.join(OUT, 'texture', fn), os.path.join(res, 'files', fn))
        files.append(fn)
    for w in wavs:
        shutil.copyfile(os.path.join(OUT, 'audio', w), os.path.join(res, 'files', 'audio', w))
        files.append('audio/' + w)
    names = [mo['name'] for mo in models]
    idx = {n: i + 1 for i, n in enumerate(names)}
    hdr = '-- Created by: Arena.ai Agent Mode (AI) - Park MTA:SA resource\n-- GENERATED by source/build.py - do not edit by hand\n'
    ml = [hdr + 'PARK_MODELS = {', '    -- name, txd (category), alpha (foliage / water: engineReplaceModel alphaTransparency), draw distance (m), tile origin (ground tiles only)']
    for mo in models:
        org = ', ox = %.1f, oy = %.1f' % (mo['origin'][0], mo['origin'][1]) if 'origin' in mo else ''
        ml.append('    { name = "%s", txd = "%s", alpha = %s, dist = %.0f%s },' % (mo['name'], mo['cat'], 'true' if mo['alpha'] else 'false', mo['dist'], org))
    ml.append('}')
    open(os.path.join(res, 'models.lua'), 'w').write('\n'.join(ml) + '\n')
    ll = [hdr + '-- park frame: x -60..60, y 0..90, origin = centre of the gate, z = 0 podium top.  obj = { model index, x, y, z, rz [, tag] }', 'PARK_OBJECTS = {']
    for o in L.obj:
        tag = ', "%s"' % o['tag'] if o['tag'] else ''
        ll.append('    { %d, %.3f, %.3f, %.3f, %.1f%s },' % (idx[o['m']], o['x'], o['y'], o['z'], o['rz'], tag))
    ll.append('}')
    ll.append('PARK_SIT = {')
    for x, y, rz in L.sit:
        ll.append('    { %.2f, %.2f, %.1f, %.2f },' % (x, y, rz, LY.surf_z(x, y)))
    ll.append('}')
    ll.append('PARK_LAMPS = {')
    for x, y, z in L.lamps:
        ll.append('    { %.2f, %.2f, %.2f },' % (x, y, LY.surf_z(x, y) + 3.5))
    ll.append('}')
    th = np.linspace(0, 2 * np.pi, 33)[:-1]
    ll.append('-- pond: ellipse polygon of the water surface (x, y), water level z')
    ll.append('PARK_POND = { cx = %.2f, cy = %.2f, rx = %.2f, ry = %.2f, z = %.2f, k = 0.90 }' % (LY.POND_C[0], LY.POND_C[1], LY.POND_R[0], LY.POND_R[1], LY.WATER_Z))
    ll.append('PARK_POINTS = {')
    ll.append('    gate = { 0, 0, 0 }, fountain = { %.1f, %.1f, 3.6 }, pond = { %.1f, %.1f, -0.2 }, gazebo = { %.1f, %.1f, 1.5 }, kiosk = { -8.0, 60.0, 1.5 },' % (*LY.RING_C, *LY.POND_C, *LY.GAZEBO_C))
    ll.append('    swing = { 46.0, 72.0, 1.0 }, merry = { 31.0, 66.0, 0.5 }, board1 = { -6.6, 4.2, 1.3 }, board2 = { 6.6, 4.2, 1.3 }, board3 = { 14.6, 33.0, 1.3 },')
    ll.append('}')
    ll.append('PARK_TREES = {')
    for x, y, cr in L.trees:
        ll.append('    { %.1f, %.1f, %.1f },' % (x, y, LY.surf_z(x, y)))
    ll.append('}')
    open(os.path.join(res, 'layout.lua'), 'w').write('\n'.join(ll) + '\n')
    mx = ['<!-- Created by: Arena.ai Agent Mode (AI) - Park MTA:SA resource -->', '<meta>',
          '    <info author="Arena.ai Agent Mode" name="Park" version="1.0.0" type="script"',
          '          description="Central Park: realistic park with entrance gate, fountain, pond, bridge, gazebo, kiosk, playground, trees and sounds. Commands: /showpark /hidepark /parkz /sit /parkwind" />',
          '    <min_mta_version client="1.5.8-9.20716" server="1.5.8-9.20716" />', '',
          '    <script src="models.lua" type="client" />', '    <script src="layout.lua" type="client" />', '    <script src="client.lua" type="client" />',
          '    <script src="server.lua" type="server" />', '', '    <file src="wind.fx" />']
    mx += ['    <file src="files/%s" />' % f for f in files] + ['</meta>']
    open(os.path.join(res, 'meta.xml'), 'w').write('\n'.join(mx) + '\n')
    json.dump(dict(models=report, txd=txd_info, objects=len(L.obj), seconds=round(time.time() - t0, 1)), open(os.path.join(HERE, 'build_report.json'), 'w'), indent=1)
    json.dump(dict(files=files, models=names), open(os.path.join(HERE, '_work', 'files.json'), 'w'))
    print('done in %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
