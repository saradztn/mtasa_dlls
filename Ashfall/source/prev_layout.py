# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# prev_layout.py - preview of the complete placed city: python3 prev_layout.py <day|night> <view,...> [outdir]
import sys, os, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from af import ground, scene, tex, bake, pv, layout, assets_bld, cars, assets_props, assets_flora, assets_park
from af.kit import REG
from af.mb import Mesh
from lib import render2

VIEWS = {
    'aerial': dict(eye=(-230, -240, 190), target=(0, 0, 0), fov=55),
    'aerial2': dict(eye=(240, 230, 150), target=(0, 0, 0), fov=55),
    'street': dict(eye=(-70, -150, 1.9), target=(-70, -60, 6), fov=75),
    'street2': dict(eye=(-100, 20, 1.9), target=(-70, -20, 5), fov=75),
    'cross': dict(eye=(-50, -62, 1.8), target=(-70, -70, 4), fov=80),
    'park': dict(eye=(-8, -62, 4), target=(0, -30, 1), fov=75),
    'lake': dict(eye=(-50, -14, 3), target=(-8, 10, -1), fov=75),
    'plaza': dict(eye=(14, -62, 3), target=(0, -42, 2), fov=75),
    'lot': dict(eye=(-115, -125, 3), target=(-115, -95, 6), fov=75),
}
if __name__ == '__main__':
    mode = sys.argv[1]
    which = sys.argv[2].split(',')
    out = sys.argv[3] if len(sys.argv) > 3 else '_work'
    W, H, ss = int(os.environ.get('W', 1280)), int(os.environ.get('H', 720)), int(os.environ.get('SS', 1))
    cfg = bake.DAY if mode == 'day' else bake.NIGHT
    t = time.time()
    L = layout.build_layout()
    tiles = ground.build_tiles(maxrun=3)
    P, UV, C, T, TM = [], [], [], [], []
    cache, bounds = {}, {}
    off = 0
    def add(pos, uv, col, tris, tmat):
        global off
        P.append(pos); UV.append(uv); C.append(col); T.append(tris + off); TM.append(tmat); off += len(pos)
    for o in L.obj:
        if o['m'] not in cache:
            a = REG[o['m']]()
            pos, nrm, uv, tris, tmat, emis = bake.flatten(a.M)
            col = bake.bake(pos, nrm, emis, cfg, a.ao, glow=a.day_glow)
            cache[o['m']] = (pos, nrm, uv, tris, tmat, col)
            bounds[o['m']] = (pos.min(0).tolist(), pos.max(0).tolist())
        pos, nrm, uv, tris, tmat, col = cache[o['m']]
        c, s = np.cos(np.radians(o['rz'])), np.sin(np.radians(o['rz']))
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        add(pos @ R.T + np.array([o['x'], o['y'], o['z']]), uv, col, tris, tmat)
    from af import shadow
    t1 = time.time()
    F = shadow.build(L.obj, bounds)
    print('shadow field %.1fs  sun-lit %.0f%%  mean AO %.2f' % (time.time() - t1, 100 * (F['T'] > 0.9).mean(), F['AO'].mean()), flush=True)
    sh = shadow.shade_fn(F, 0.50 if mode == 'day' else 0.10)
    for k, v in sorted(tiles.items()):
        pos, nrm, uv, tris, tmat, col = scene.bake_ground(v['M'], cfg, ao=sh)
        add(pos, uv, col, tris, tmat)
    pos, uv, col, tris, tmat = (np.concatenate(a) for a in (P, UV, C, T, TM))
    print('scene', len(pos), 'verts', len(tris), 'tris', '%.1fs' % (time.time() - t), flush=True)
    bg = (0.52, 0.56, 0.60) if mode == 'day' else (0.02, 0.03, 0.07)
    for v in which:
        d = VIEWS[v]
        im = render2.render(pos, uv, col, tris, tmat, pv.textures(), sorted(tex.ALPHA), d['eye'], d['target'], fov=d['fov'], W=W, H=H, ss=ss, bg=bg)
        im.save('%s/lay_%s_%s.png' % (out, v, mode))
        if os.environ.get('GRADE', '1') == '1' and mode == 'day':
            pv.grade(im).save('%s/lay_%s_%s_graded.png' % (out, v, mode))
        print(v, '%.1fs' % (time.time() - t), flush=True)
