# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# build_all.py - one command build of the complete asset:
#     python3 build_all.py
# writes   ../model/FishingRod.dff   ../texture/FishingRod.txd   ../texture/maps/*.dds
#          ../collision/FishingRod.col   (+ build_report.json)
# orientation: fr/config.py ROT_Z_DEG (default 90) is baked in.
# then run  validate.py  and  make_previews.py
# -----------------------------------------------------------------------------
import json
import os
import sys
import time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fr import model as md
from fr import texgen, dxt, rwdff, rwtxd, colfile, collision
from fr.geom import merge_parts
from fr.materials import MATS, ENV_TEX, ENV_SIZE
from fr.config import ROT_Z_DEG, rot_z

OUT = os.path.abspath(os.path.join(HERE, '..'))
NODE_ORDER = ['fr_rod', 'fr_reel_body', 'fr_reel_rotor', 'fr_line']


def geometry_from_parts(parts, offset=(0, 0, 0)):
    parts = merge_parts(parts)
    pos, nrm, uv, tr, tm = [], [], [], [], []
    off = 0
    used = sorted(set(p.mat for p in parts))
    remap = {m: i for i, m in enumerate(used)}
    for p in parts:
        pos.append(p.pos - np.asarray(offset))
        nrm.append(p.nrm)
        uv.append(p.uv)
        tr.append(p.tris + off)
        tm.append(np.full(len(p.tris), remap[p.mat]))
        off += len(p.pos)
    R = rot_z()
    pos = np.concatenate(pos) @ R.T
    n = len(pos)
    white = np.full((n, 4), 255, np.uint8)
    return dict(pos=pos, nrm=np.concatenate(nrm) @ R.T, uv=np.concatenate(uv), tris=np.concatenate(tr), tri_mat=np.concatenate(tm),
                prelit=white, night=white.copy()), used


def main():
    t0 = time.time()
    for d in ('model', 'texture', 'texture/maps', 'collision'):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    print('[1/5] geometry ...')
    nodes = md.build_all()
    geoms, mats_per, used_per = [], [], []
    for k in NODE_ORDER:
        off = tuple(md.REEL_O) if k == 'fr_reel_rotor' else (0, 0, 0)
        g, used = geometry_from_parts(nodes[k], off)
        geoms.append(g)
        used_per.append(used)
        mats = []
        for mi in used:
            m = MATS[mi]
            mats.append(dict(tex=m['tex'], env=m['env'], env_tex=ENV_TEX, color=(255, 255, 255, 255), surface=(1.0, 0.0, 1.0)))
        mats_per.append(mats)
        print('   %-14s verts %6d tris %6d materials %d' % (k, len(g['pos']), len(g['tris']), len(used)))

    print('[2/5] textures (procedural PBR) ...')
    txd_tex, report_tex = [], []
    for mi, m in enumerate(MATS):
        gen, ns = texgen.GENERATORS[m['key']]
        tx = gen()
        diff, nrm, orm = texgen.bake(tx, ns)
        w, h = m['size']
        assert diff.shape[:2] == (h, w), (m['key'], diff.shape)
        chain = dxt.compress_chain(diff, 'DXT1')
        txd_tex.append(dict(name=m['tex'], w=w, h=h, fmt='DXT1', chain=chain, alpha=False))
        dxt.write_dds(os.path.join(OUT, 'texture', 'maps', m['tex'] + '_n.dds'), nrm, 'DXT5')
        dxt.write_dds(os.path.join(OUT, 'texture', 'maps', m['tex'] + '_orm.dds'), orm, 'DXT1')
        report_tex.append(dict(name=m['tex'], size=[w, h], fmt='DXT1', mips=len(chain), bytes=sum(len(c[2]) for c in chain)))
        print('   %-16s %4dx%-4d DXT1 + normal(DXT5nm) + ORM(DXT1)' % (m['tex'], w, h))
    env = texgen.gen_env()
    chain = dxt.compress_chain(env, 'DXT1')
    txd_tex.append(dict(name=ENV_TEX, w=ENV_SIZE[0], h=ENV_SIZE[1], fmt='DXT1', chain=chain, alpha=False))
    report_tex.append(dict(name=ENV_TEX, size=list(ENV_SIZE), fmt='DXT1', mips=len(chain), bytes=sum(len(c[2]) for c in chain)))
    Image.fromarray(env).save(os.path.join(HERE, '_work', 'env.png')) if os.path.isdir(os.path.join(HERE, '_work')) else None
    txd = rwtxd.build_txd(txd_tex)
    open(os.path.join(OUT, 'texture', 'FishingRod.txd'), 'wb').write(txd)

    print('[3/5] DFF ...')
    frames = [dict(name='FishingRod', pos=(0, 0, 0), parent=-1),
              dict(name='fr_rod', pos=(0, 0, 0), parent=0),
              dict(name='fr_reel_body', pos=(0, 0, 0), parent=0),
              dict(name='fr_reel_rotor', pos=tuple(float(x) for x in rot_z() @ np.asarray(md.REEL_O, float)), parent=0),
              dict(name='fr_line', pos=(0, 0, 0), parent=0)]
    atomics = []
    for i, k in enumerate(NODE_ORDER):
        fx = any(MATS[mi]['env'] > 0 for mi in used_per[i])
        atomics.append((i + 1, i, fx))
    dff = rwdff.build_clump(frames, geoms, atomics, mats_per)
    open(os.path.join(OUT, 'model', 'FishingRod.dff'), 'wb').write(dff)

    print('[4/5] COL ...')
    sph, box = collision.build_shapes()
    R = rot_z()
    sph = [tuple(R @ np.array(s_[:3])) + tuple(s_[3:]) for s_ in sph]
    nb = []
    for lo, hi, m in box:
        c = np.array([R @ np.array(lo), R @ np.array(hi)])
        nb.append((tuple(c.min(0)), tuple(c.max(0)), m))   # 90-degree multiples keep boxes axis-aligned
    box = nb
    col = colfile.build_col3('FishingRod', 0, sph, box)
    open(os.path.join(OUT, 'collision', 'FishingRod.col'), 'wb').write(col)

    rep = dict(dff_bytes=len(dff), txd_bytes=len(txd), col_bytes=len(col), textures=report_tex,
               geometries={k: dict(verts=int(len(g['pos'])), tris=int(len(g['tris']))) for k, g in zip(NODE_ORDER, geoms)},
               collision=dict(spheres=len(sph), boxes=len(box)), build_seconds=round(time.time() - t0, 1))
    json.dump(rep, open(os.path.join(HERE, 'build_report.json'), 'w'), indent=1)
    print('[5/5] done in %.1fs  DFF %.1f KB  TXD %.2f MB  COL %.1f KB' % (time.time() - t0, len(dff) / 1024, len(txd) / 1048576, len(col) / 1024))


if __name__ == '__main__':
    main()
