# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# preview_park.py - game-like preview renders of the whole park: python3 preview_park.py <day|night> <view,view,...> [outdir]
import sys, os, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pk import tex, layout, scene, assets_small, assets_plants, assets_big
from lib import render2

VIEWS = {
    'aerial': dict(eye=(-95, -62, 85), target=(0, 42, 0), fov=52),
    'aerial_ne': dict(eye=(100, 150, 70), target=(-5, 40, 0), fov=55),
    'gate': dict(eye=(0, -34, 3.2), target=(0, 6, 3.4), fov=62),
    'gate_close': dict(eye=(5, -9, 1.8), target=(-1, 2, 2.6), fov=70),
    'fountain': dict(eye=(-14, 14, 4.0), target=(0, 40, 2.0), fov=70),
    'fountain_hi': dict(eye=(-22, 18, 14), target=(0, 40, 1.0), fov=60),
    'pond': dict(eye=(12, 28, 3.0), target=(36, 42, 0.5), fov=70),
    'bridge': dict(eye=(36, 24, 3.2), target=(36, 42, 1.0), fov=62),
    'playground': dict(eye=(28, 53, 4.0), target=(40, 70, 1.5), fov=75),
    'gazebo': dict(eye=(-20, 36, 2.6), target=(-38, 40, 2.4), fov=70),
    'kiosk': dict(eye=(1.5, 52, 2.2), target=(-8, 60, 1.5), fov=72),
    'walk': dict(eye=(0, 8, 1.7), target=(0, 40, 2.0), fov=75),
}

if __name__ == '__main__':
    mode = sys.argv[1]
    which = sys.argv[2].split(',')
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, '_work')
    W, H, ss = int(os.environ.get('W', 1280)), int(os.environ.get('H', 720)), int(os.environ.get('SS', 1))
    L = layout.build_layout()
    imgs = tex.generate_all()
    textures = [imgs[n] for n in tex.NAMES]
    t = time.time()
    pos, uv, col, tris, tm = scene.full_scene(L, mode, len(textures))
    print('scene', len(pos), 'verts', len(tris), 'tris  %.1fs' % (time.time() - t))
    bg = (0.55, 0.68, 0.88) if mode == 'day' else (0.02, 0.03, 0.07)
    os.makedirs(out, exist_ok=True)
    for w in which:
        v = VIEWS[w]
        t = time.time()
        im = render2.render(pos, uv, col, tris, tm, textures, sorted(tex.ALPHA), v['eye'], v['target'], fov=v['fov'], W=W, H=H, ss=ss, bg=bg)
        p = os.path.join(out, 'park_%s_%s.png' % (w, mode))
        im.save(p)
        print(p, '%.1fs' % (time.time() - t))
