# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# prev_city.py - whole-city preview renders: python3 prev_city.py <day|night> <view,...> [outdir]
import sys, os, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from af import ground, scene, tex, bake, pv
from lib import render2

VIEWS = {
    'aerial': dict(eye=(-230, -240, 190), target=(0, 0, 0), fov=55),
    'aerial_s': dict(eye=(0, -260, 120), target=(0, -40, 5), fov=60),
    'street': dict(eye=(-70, -150, 1.8), target=(-70, -60, 3), fov=75),
    'inter': dict(eye=(-100, -70, 3.0), target=(-60, -70, 1.0), fov=75),
    'park': dict(eye=(-60, -40, 6), target=(0, 10, -1), fov=75),
}
if __name__ == '__main__':
    mode = sys.argv[1]
    which = sys.argv[2].split(',')
    out = sys.argv[3] if len(sys.argv) > 3 else '_work'
    W, H, ss = int(os.environ.get('W', 1280)), int(os.environ.get('H', 720)), int(os.environ.get('SS', 1))
    cfg = bake.DAY if mode == 'day' else bake.NIGHT
    t = time.time()
    tiles = ground.build_tiles(maxrun=2)
    parts = []
    for k, v in sorted(tiles.items()):
        parts.append(scene.bake_ground(v['M'], cfg))
    off = 0
    P, UV, C, T, TM = [], [], [], [], []
    for pos, nrm, uv, tris, tmat, col in parts:
        P.append(pos); UV.append(uv); C.append(col); T.append(tris + off); TM.append(tmat); off += len(pos)
    pos, uv, col, tris, tm = [np.concatenate(a) for a in (P, UV, C, T, TM)]
    print('scene', len(pos), 'verts', len(tris), 'tris  %.1fs' % (time.time() - t))
    textures = pv.textures()
    bg = (0.52, 0.56, 0.60) if mode == 'day' else (0.02, 0.03, 0.07)
    os.makedirs(out, exist_ok=True)
    for w in which:
        v = VIEWS[w]
        t = time.time()
        im = render2.render(pos, uv, col, tris, tm, textures, sorted(tex.ALPHA), v['eye'], v['target'], fov=v['fov'], W=W, H=H, ss=ss, bg=bg)
        p = os.path.join(out, 'city_%s_%s.png' % (w, mode))
        im.save(p)
        print(p, '%.1fs' % (time.time() - t))
