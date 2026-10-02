# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# showcase.py - QA renders: python3 showcase.py <names|all|group> [mode] [out.png]   (grid of assets on grass)
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pk import tex, bake, kit
from pk.kit import REG, place
from pk.mb import Mesh
from lib import render2


def load_all():
    from pk import assets_small
    try:
        from pk import assets_plants
    except ImportError:
        pass
    try:
        from pk import assets_big
    except ImportError:
        pass


def render_assets(names, mode='day', out='_work/show.png', cols=6, gap=6.0, eye_k=1.0, view=None, W=1600, H=900, extra=()):
    load_all()
    imgs = tex.generate_all()
    textures = [imgs[n] for n in tex.NAMES]
    cfg = bake.DAY if mode == 'day' else bake.NIGHT
    P, N, U, T, TM, C = [], [], [], [], [], []
    off = 0
    items = []
    for i, nm in enumerate(names):
        a = REG[nm]()
        x, y = (i % cols) * gap, -(i // cols) * gap
        pos, nrm, uv, tris, tmat, emis = bake.flatten(a.M)
        col = bake.bake(pos, nrm, emis, cfg, a.ao, glow=cfg['glow'] if mode != 'day' else a.day_glow)
        pos = pos + np.array([x, y, 0.0])
        P.append(pos); N.append(nrm); U.append(uv); T.append(tris + off); TM.append(tmat); C.append(col); off += len(pos)
    rows = (len(names) + cols - 1) // cols
    x0, x1, y0, y1 = -gap, cols * gap, -rows * gap, gap
    g = np.array([[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]], float)
    P.append(g); N.append(np.tile([0, 0, 1.0], (4, 1))); U.append(g[:, :2] / 3.0); T.append(np.array([[0, 1, 2], [0, 2, 3]]) + off)
    TM.append(np.full(2, tex.IDX['pk_grass'], np.int32)); C.append(np.tile((0.62, 0.62, 0.62) if mode == 'day' else (0.12, 0.14, 0.2), (4, 1)))
    pos = np.concatenate(P); uv = np.concatenate(U); col = np.concatenate(C); tris = np.concatenate(T); tm = np.concatenate(TM)
    cx, cy = (cols - 1) * gap / 2, -(rows - 1) * gap / 2
    eye = view['eye'] if view else (cx, cy - gap * 1.5 - (cols * gap) * 0.55 * eye_k, 3.0 + rows * 2.2)
    tgt = view['target'] if view else (cx, cy, 1.0)
    bg = (0.55, 0.68, 0.85) if mode == 'day' else (0.02, 0.03, 0.07)
    im = render2.render(pos, uv, col, tris, tm, textures, sorted(tex.ALPHA), eye, tgt, fov=(view or {}).get('fov', 42), W=W, H=H, ss=1, bg=bg)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    im.save(out)
    print(out)


if __name__ == '__main__':
    load_all()
    names = sys.argv[1].split(',') if sys.argv[1] != 'all' else list(REG)
    mode = sys.argv[2] if len(sys.argv) > 2 else 'day'
    out = sys.argv[3] if len(sys.argv) > 3 else '_work/show.png'
    cols = int(os.environ.get('COLS', 6)); gap = float(os.environ.get('GAP', 3.0))
    render_assets(names, mode, out, cols=cols, gap=gap, eye_k=float(os.environ.get('EK', 1.0)))
