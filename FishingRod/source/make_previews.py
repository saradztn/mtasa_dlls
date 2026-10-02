# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# make_previews.py - renders ../preview/*.png from the SHIPPED files only:
#   geometry  <- model/FishingRod.dff   (parsed by fr/readers.py)
#   diffuse   <- texture/FishingRod.txd (DXT1 decoded, level 0)
#   normal/ORM<- texture/maps/*.dds     (DXT5nm / DXT1 decoded)
# using the software PBR rasteriser (fr/render.c).  These are NOT in-game screenshots:
# SA's own lighting / MatFX look different.  Usage: python3 make_previews.py [front|side|detail|all]
# -----------------------------------------------------------------------------
import os
import struct
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fr import readers, dxt
from fr.materials import MATS
from fr.render import Scene, render

ROOT = os.path.abspath(os.path.join(HERE, '..'))
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
NOTE = 'Software PBR render of the shipped DFF + TXD + normal/ORM DDS (not an in-game screenshot)'


def read_dds(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'DDS '
    h, w = struct.unpack_from('<II', b, 12)
    cc = b[84:88].decode()
    n = dxt.level_size(w, h, cc)
    return dxt.decode(b[128:128 + n], w, h, cc)


def load_scene():
    dff = readers.read_dff(os.path.join(ROOT, 'model', 'FishingRod.dff'))
    txd = readers.read_txd(os.path.join(ROOT, 'texture', 'FishingRod.txd'))
    tex = {t['name']: t for t in txd['textures']}
    idx = {m['tex']: i for i, m in enumerate(MATS)}
    pos, nrm, uv, tri, tm = [], [], [], [], []
    off = 0
    for at in dff['atomics']:
        g = dff['geoms'][at['geom']]
        fp = dff['frames'][at['frame']]['pos']
        pos.append(g['pos'] + fp)
        nrm.append(g['nrm'])
        uv.append(g['uv'])
        tri.append(g['tris'] + off)
        tm.append(np.array([idx[g['materials'][k]['tex']['name']] for k in range(len(g['materials']))])[g['tri_mat']])
        off += g['nverts']
    S = Scene(np.concatenate(pos), np.concatenate(nrm), np.concatenate(uv), np.concatenate(tri), np.concatenate(tm), len(MATS))
    for i, m in enumerate(MATS):
        S.set_tex(i, 0, readers.decode_texture(tex[m['tex']], 0))
        S.set_tex(i, 1, read_dds(os.path.join(ROOT, 'texture', 'maps', m['tex'] + '_n.dds')))
        S.set_tex(i, 2, read_dds(os.path.join(ROOT, 'texture', 'maps', m['tex'] + '_orm.dds')))
        S.param[i, 3] = m['rough']
        S.param[i, 4] = m['metal']
    return S


def caption(im, title, sub=None):
    d = ImageDraw.Draw(im, 'RGBA')
    f1 = ImageFont.truetype(FB, max(18, im.width // 55))
    f2 = ImageFont.truetype(FR, max(12, im.width // 110))
    d.rectangle([0, im.height - f1.size * 2.6, im.width, im.height], fill=(0, 0, 0, 150))
    d.text((24, im.height - f1.size * 2.4), title, font=f1, fill=(255, 255, 255, 255))
    d.text((24, im.height - f2.size * 1.9), sub or NOTE, font=f2, fill=(205, 205, 205, 255))
    return im


def view_front(S):
    # hero 3/4 view from the tip end: perspective, handle + reel in front, blank receding
    im = render(S, (0.95, 2.75, 0.5), (0.0, 0.72, -0.17), fov=24, W=2000, H=1250, ss=2)
    return caption(im, 'Tidewater Pro Series TW-702MF - 7\'0" spinning rod  |  front 3/4 view')


def view_side(S):
    im = render(S, (1.35, 0.67, 0.0), (0.0, 0.67, -0.06), fov=36, W=2400, H=900, ss=2)
    return caption(im, 'Side profile, full length 1.95 m  |  origin = reel-seat centre, +Y towards tip, Z up')


def view_detail(S):
    W, H = 1300, 900
    panels = [
        ('Reel - drive side, crank + power knob', (0.30, 0.06, -0.05), (0.0, 0.0, -0.075), 28),
        ('Reel - rotor, bail, spool, drag knob', (-0.20, 0.31, -0.14), (0.0, 0.03, -0.075), 30),
        ('Reel seat, hoods, knurled lock nut, cork grip', (0.20, 0.0, 0.10), (0.0, -0.03, -0.03), 34),
        ('Guides + tip-top (ceramic inserts, wraps)', (0.12, 1.40, 0.07), (0.0, 1.50, -0.05), 26),
    ]
    out = Image.new('RGB', (W * 2, H * 2))
    for i, (t, eye, tgt, fov) in enumerate(panels):
        im = render(S, eye, tgt, fov=fov, W=W, H=H, ss=2)
        d = ImageDraw.Draw(im, 'RGBA')
        f = ImageFont.truetype(FB, 30)
        d.rectangle([0, 0, W, 52], fill=(0, 0, 0, 140))
        d.text((18, 8), t, font=f, fill=(255, 255, 255, 255))
        out.paste(im, ((i % 2) * W, (i // 2) * H))
    return caption(out, 'Detail views: reel, seat, guides and tip')


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    S = load_scene()
    os.makedirs(os.path.join(ROOT, 'preview'), exist_ok=True)
    for name, fn in (('front', view_front), ('side', view_side), ('detail', view_detail)):
        if which in ('all', name):
            im = fn(S)
            im.save(os.path.join(ROOT, 'preview', 'preview_%s.png' % name))
            print('wrote preview_%s.png %s' % (name, im.size))
