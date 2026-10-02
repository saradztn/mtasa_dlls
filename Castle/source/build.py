# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# build.py - one command build of the complete castle asset:
#     python3 build.py
# writes   ../model/Castle.dff  CastleGate.dff  CastleDoor.dff
#          ../texture/Castle.txd (shared by the three models)
#          ../collision/Castle.col  CastleGate.col  CastleDoor.col
#          ../source/mta_resource/files/*  (copies, ready to zip)  +  build_report.json
# Then run validate.py and make_previews.py.
# -----------------------------------------------------------------------------
import json
import os
import shutil
import sys
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cs import castle, tex, light, parts
from cs.mb import Mesh, Col
from lib import dxt, rwdff, rwtxd, colfile

OUT = os.path.abspath(os.path.join(HERE, '..'))
MAX_TRIS = 19000                      # per atomic (unwelded 3 verts per tri) -> always < 65535 vertices
ID_CASTLE, ID_GATE, ID_DOOR = 12853, 12854, 12855


def weld(pos, nrm, uv, dcol, ncol, tris):
    key = np.concatenate([np.round(pos * 1000).astype(np.int64), np.round(nrm * 60).astype(np.int64), np.round(uv * 4000).astype(np.int64),
                          dcol.astype(np.int64), ncol.astype(np.int64)], axis=1)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    return pos[first], nrm[first], uv[first], dcol[first], ncol[first], inv[tris]


def make_geoms(pos, nrm, uv, tris, tmat, dcol, ncol, alpha_mats):
    """split into opaque spatial chunks + one alpha atomic list; returns list of (geometry dict, used materials, is_alpha)"""
    area = np.linalg.norm(np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]]), axis=1)
    keep = area > 1e-9                                  # drop zero-area triangles (sphere poles ...)
    tris, tmat = tris[keep], tmat[keep]
    cen = pos[tris].mean(1)
    is_a = np.isin(tmat, list(alpha_mats))
    out = []
    for group, flag in ((~is_a, False), (is_a, True)):
        idx = np.nonzero(group)[0]
        if len(idx) == 0:
            continue
        c = cen[idx]
        key = (np.floor(c[:, 2] / 14.0).astype(int) * 1000 + np.floor((c[:, 1] + 20) / 16.0).astype(int) * 40 + np.floor((c[:, 0] + 40) / 16.0).astype(int))
        idx = idx[np.argsort(key, kind='stable')]
        for s0 in range(0, len(idx), MAX_TRIS):
            sel = idx[s0:s0 + MAX_TRIS]
            t = tris[sel]
            used_v, inv = np.unique(t.reshape(-1), return_inverse=True)
            t2 = inv.reshape(-1, 3)
            p, n, u, d, nc, t3 = weld(pos[used_v], nrm[used_v], uv[used_v], dcol[used_v], ncol[used_v], t2)
            mats = sorted(set(tmat[sel].tolist()))
            remap = {m: i for i, m in enumerate(mats)}
            tm = np.array([remap[m] for m in tmat[sel]], np.int64)
            assert len(p) < 65535, len(p)
            g = dict(pos=p, nrm=n, uv=u, tris=t3, tri_mat=tm, prelit=d, night=nc, dyn_light=False)
            out.append((g, mats, flag))
    return out


def mat_chunk(name):
    return dict(tex=name, env=0, color=(255, 255, 255, 255), surface=(1.0, 0.0, 1.0))


def build_col(C, name, model_id):
    verts, faces, vmap = [], [], {}

    def vid(p):
        k = tuple(int(round(c * 128)) for c in p)
        if k not in vmap:
            vmap[k] = len(verts)
            verts.append(np.array(k) / 128.0)
        return vmap[k]
    # corner order of Col.strip prisms: bottom 4 (CCW from above) then top 4 (same order)
    for cc in C.prisms:
        cc = np.asarray(cc, float)
        b, t = cc[:4], cc[4:]
        # make bottom CCW seen from above
        area = sum(b[i][0] * b[(i + 1) % 4][1] - b[(i + 1) % 4][0] * b[i][1] for i in range(4))
        if area < 0:
            b, t = b[::-1], t[::-1]
        ib = [vid(p) for p in b]
        it = [vid(p) for p in t]
        faces += [(ib[0], ib[2], ib[1]), (ib[0], ib[3], ib[2]), (it[0], it[1], it[2]), (it[0], it[2], it[3])]
        for i in range(4):
            j = (i + 1) % 4
            faces += [(ib[i], ib[j], it[j]), (ib[i], it[j], it[i])]
    boxes = [(lo, hi, 0) for lo, hi in C.boxes]
    assert len(verts) < 32767 and len(faces) < 65535
    V = np.array(verts) if verts else None
    if V is not None:
        assert np.abs(V).max() < 255.9, 'collision mesh vertex outside int16/128 range'
    col = colfile.build_col3(name, model_id, [], boxes, V.tolist() if V is not None else None, [(a, b, c, 0) for a, b, c in faces] if verts else None)
    return col, len(boxes), len(faces), len(verts)


# ---------------------------------------------------------------------------------------------
def door_meshes():
    """gate leaf (arched top, 2.0 wide) and door leaf (1.7 x 2.2); hinge at the local origin, leaf along +x"""
    res = {}
    for kind in ('gate', 'door'):
        M, C = Mesh(), Col()
        P = parts
        if kind == 'door':
            w, hgt, th = 1.7, 2.2, 0.07
            M.poly([(0.02, th, 0.0), (w, th, 0.0), (w, th, hgt), (0.02, th, hgt)], P.DR, hint=(0, 1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
            M.poly([(0.02, -th, 0.0), (w, -th, 0.0), (w, -th, hgt), (0.02, -th, hgt)], P.DR, hint=(0, -1, 0), uv=[(1, 1), (0, 1), (0, 0), (1, 0)])
            M.box((0.02, -th, 0), (w, th, hgt), P.WD, tile=1.0, skip=('+y', '-y'))
            for sy in (-1, 1):
                P.sphere(M, (w - 0.14, sy * (th + 0.03), 1.05), 0.045, P.GD, 8, 5)
                P.bar(M, (w - 0.14, sy * (th + 0.01), 1.05), (w - 0.14, sy * (th + 0.01), 0.97), 0.03, P.IR, tile=0.3)
            # lintel pointed hood top
            C.box((0.0, -th, 0.0), (w, th, hgt))
        else:
            w, th = 2.0, 0.11
            xs = np.linspace(0.02, w - 0.02, 14)
            top = 2.6 + np.sqrt(np.maximum(16.0 - (xs - 4.0) ** 2, 0.0)) - 0.05
            pts_f = [(xs[0], th, 0.0), (xs[-1], th, 0.0)] + [(x, th, z) for x, z in zip(xs[::-1], top[::-1])]
            uvf = [(p[0] / w, -p[2] / 2.2) for p in pts_f]
            M.poly(pts_f, P.DR, hint=(0, 1, 0), uv=uvf)
            pts_b = [(x, -th, z) for x, _, z in pts_f]
            M.poly(pts_b, P.DR, hint=(0, -1, 0), uv=[(1 - u, v) for u, v in uvf])
            # thin edge faces following the outline
            for i in range(len(pts_f)):
                a, b = pts_f[i], pts_f[(i + 1) % len(pts_f)]
                mid = np.array([(a[0] + b[0]) / 2, 0, (a[2] + b[2]) / 2])
                M.poly([(a[0], -th, a[2]), (b[0], -th, b[2]), (b[0], th, b[2]), (a[0], th, a[2])], P.WD, hint=(mid[0] - w / 2, 0, mid[2] - 2.5), tile=1.0)
            # iron straps with studs on both faces, ring handles
            for sy in (-1, 1):
                for zc in (0.45, 1.5, 2.6, 3.7, 4.7):
                    zt = min(zc + 0.09, 2.6 + np.sqrt(max(16.0 - (w - 4.0) ** 2, 0)) - 0.2)
                    P.bar(M, (0.02, sy * (th + 0.015), zc), (min(w - 0.02, 1.98), sy * (th + 0.015), zc), 0.16, P.IR, h=0.04, tile=0.5) if zc < 4.2 else None
                    for xk in np.arange(0.2, w - 0.1, 0.35):
                        if zc < 4.2:
                            P.sphere(M, (xk, sy * (th + 0.04), zc), 0.032, P.IR, 6, 4)
                P.sphere(M, (w - 0.28, sy * (th + 0.05), 1.3), 0.07, P.IR, 8, 5)
                P.sphere(M, (w - 0.28, sy * (th + 0.05), 1.3), 0.07, P.IR, 8, 5)
            C.box((0.0, -th, 0.0), (w, th, 2.6))
            C.box((0.55, -th, 2.6), (w, th, 4.4))
            C.box((1.15, -th, 4.4), (w, th, 6.0))
        res[kind] = (M, C)
    return res


def dff_from_meshes(M, frames_name, dcol, ncol):
    pos, nrm, uv, tris, tmat, emis = light.flatten(M)
    d = np.tile(np.array(dcol, np.uint8), (len(pos), 1))
    n = np.tile(np.array(ncol, np.uint8), (len(pos), 1))
    emis_b = emis > 0.5
    d[emis_b] = 255
    n[emis_b] = 255
    geoms = make_geoms(pos, nrm, uv, tris, tmat, d, n, tex.ALPHA)
    frames = [dict(name=frames_name, pos=(0, 0, 0), parent=-1)]
    atomics, mats_per, gl = [], [], []
    for i, (g, mats, fl) in enumerate(geoms):
        frames.append(dict(name='%s_%02d' % (frames_name, i), pos=(0, 0, 0), parent=0))
        atomics.append((i + 1, i, False))
        mats_per.append([mat_chunk(tex.MAT_NAMES[m]) for m in mats])
        gl.append(g)
    return rwdff.build_clump(frames, gl, atomics, mats_per), geoms


def main():
    t0 = time.time()
    for d in ('model', 'texture', 'collision', 'preview'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    print('[1/6] geometry ...')
    S = castle.Scene()
    castle.build_all(S)
    pos, nrm, uv, tris, tmat, emis = light.flatten(S.M)
    print('   %d verts (unwelded)  %d tris  %d lights  %d rooms  %d collision boxes  %d prisms' % (len(pos), len(tris), len(S.L), len(S.rooms), len(S.C.boxes), len(S.C.prisms)))
    print('[2/6] baking vertex colours (day + night) ...')
    day = light.bake(pos, nrm, emis, None, S.rooms, S.L, light.DAY)
    night = light.bake(pos, nrm, emis, None, S.rooms, S.L, light.NIGHT)
    dcol = np.concatenate([(day * 255 + 0.5).astype(np.uint8), np.full((len(pos), 1), 255, np.uint8)], 1)
    ncol = np.concatenate([(night * 255 + 0.5).astype(np.uint8), np.full((len(pos), 1), 255, np.uint8)], 1)
    print('[3/6] textures ...')
    imgs = tex.generate_all()
    txd_tex, rep_tex = [], []
    for i, n in enumerate(tex.MAT_NAMES):
        im = imgs[n]
        h, w = im.shape[:2]
        fmt = 'DXT5' if i in tex.ALPHA else 'DXT1'
        chain = dxt.compress_chain(im, fmt)
        txd_tex.append(dict(name=n, w=w, h=h, fmt=fmt, chain=chain, alpha=(fmt == 'DXT5')))
        rep_tex.append(dict(name=n, size=[w, h], fmt=fmt, mips=len(chain), bytes=sum(len(c[2]) for c in chain)))
        print('   %-12s %4dx%-4d %s' % (n, w, h, fmt))
    txd = rwtxd.build_txd(txd_tex)
    open(os.path.join(OUT, 'texture', 'Castle.txd'), 'wb').write(txd)
    print('[4/6] DFF ...')
    geoms = make_geoms(pos, nrm, uv, tris, tmat, dcol, ncol, tex.ALPHA)
    frames = [dict(name='Castle', pos=(0, 0, 0), parent=-1)]
    atomics, mats_per, gl = [], [], []
    for i, (g, mats, fl) in enumerate(geoms):
        frames.append(dict(name='cs_%s_%02d' % ('alpha' if fl else 'solid', i), pos=(0, 0, 0), parent=0))
        atomics.append((i + 1, i, False))
        mats_per.append([mat_chunk(tex.MAT_NAMES[m]) for m in mats])
        gl.append(g)
        print('   atomic %-2d %-6s verts %6d tris %6d materials %d' % (i, 'alpha' if fl else 'solid', len(g['pos']), len(g['tris']), len(mats)))
    dff = rwdff.build_clump(frames, gl, atomics, mats_per)
    open(os.path.join(OUT, 'model', 'Castle.dff'), 'wb').write(dff)
    doors = door_meshes()
    rep_doors = {}
    for kind, name, mid in (('gate', 'CastleGate', ID_GATE), ('door', 'CastleDoor', ID_DOOR)):
        M, C = doors[kind]
        b, geo = dff_from_meshes(M, name, (165, 150, 140, 255), (62, 52, 50, 255))
        open(os.path.join(OUT, 'model', name + '.dff'), 'wb').write(b)
        c, nb, nf, nv = build_col(C, name, mid)
        open(os.path.join(OUT, 'collision', name + '.col'), 'wb').write(c)
        rep_doors[name] = dict(dff=len(b), col=len(c), verts=sum(len(g[0]['pos']) for g in geo))
    print('[5/6] COL ...')
    col, nb, nf, nv = build_col(S.C, 'Castle', ID_CASTLE)
    open(os.path.join(OUT, 'collision', 'Castle.col'), 'wb').write(col)
    print('   boxes %d  mesh faces %d  mesh verts %d  %.1f KB' % (nb, nf, nv, len(col) / 1024))
    # door table for the Lua resource
    meta = dict(doors=S.doors, ids=dict(castle=ID_CASTLE, gate=ID_GATE, door=ID_DOOR))
    json.dump(meta, open(os.path.join(HERE, '_work', 'doors.json'), 'w'), indent=1)
    res = os.path.join(OUT, 'resource', 'Castle')
    os.makedirs(os.path.join(res, 'files'), exist_ok=True)
    lua = ['-- Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA resource', '-- GENERATED by source/build.py from cs/interiors.py (doors) - do not edit by hand',
           '-- fields: model (gate|door), hinge = castle-space position of the leaf pivot, rz = closed angle, open_rz = open angle (degrees)', 'CASTLE_DOORS = {']
    for d in S.doors:
        lua.append('    { name = "%s", model = "%s", hinge = { %.3f, %.3f, %.3f }, rz = %.1f, open_rz = %.1f },' % (d['name'], d['model'], *d['hinge'], d['rz'], d['open_rz']))
    lua.append('}')
    open(os.path.join(res, 'doors_data.lua'), 'w').write('\n'.join(lua) + '\n')
    for src, dst in (('model/Castle.dff', 'Castle.dff'), ('model/CastleGate.dff', 'CastleGate.dff'), ('model/CastleDoor.dff', 'CastleDoor.dff'),
                     ('texture/Castle.txd', 'Castle.txd'), ('collision/Castle.col', 'Castle.col'), ('collision/CastleGate.col', 'CastleGate.col'),
                     ('collision/CastleDoor.col', 'CastleDoor.col')):
        shutil.copyfile(os.path.join(OUT, src), os.path.join(res, 'files', dst))
    rep = dict(dff_bytes=len(dff), txd_bytes=len(txd), col_bytes=len(col), textures=rep_tex, doors=rep_doors,
               geometries=[dict(verts=int(len(g[0]['pos'])), tris=int(len(g[0]['tris'])), alpha=bool(g[2])) for g in geoms],
               collision=dict(boxes=nb, faces=nf, verts=nv), lights=len(S.L), build_seconds=round(time.time() - t0, 1))
    json.dump(rep, open(os.path.join(HERE, 'build_report.json'), 'w'), indent=1)
    print('[6/6] done in %.1fs  DFF %.2f MB  TXD %.2f MB  COL %.1f KB' % (time.time() - t0, len(dff) / 1048576, len(txd) / 1048576, len(col) / 1024))


if __name__ == '__main__':
    main()
