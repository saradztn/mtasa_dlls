# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# pv.py - quick preview helpers: bake a list of (Mesh, transform) and render with lib.render2
import numpy as np
from . import tex, bake
from .mb import Mesh
from lib import render2

_imgs = None


def textures():
    global _imgs
    if _imgs is None:
        d = tex.generate_all()
        _imgs = [d[n] for n in tex.NAMES]
    return _imgs


def ao_default(pos, nrm):
    z = pos[:, 2]
    return 0.64 + 0.36 * np.clip(z / 7.0, 0, 1)


def place(M, pos, rz=0.0, mirror=False):
    """copy of mesh M moved/rotated (rz deg, CCW)"""
    out = Mesh()
    c, s = np.cos(np.radians(rz)), np.sin(np.radians(rz))
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    for p, n, u, t, m, e in M.chunks:
        p2 = p @ R.T + np.asarray(pos)
        n2 = n @ R.T
        out.chunks.append((p2, n2, u, t, m, e))
    return out


def merge(meshes):
    out = Mesh()
    for m in meshes:
        out.chunks += m.chunks
    return out


def render(M, eye, target, fov=60, W=1280, H=720, ss=1, mode='day', ao=ao_default, bg=None):
    pos, nrm, uv, tris, tm, em = bake.flatten(M)
    cfg = bake.DAY if mode == 'day' else bake.NIGHT
    col = bake.bake(pos, nrm, em, cfg, ao=ao)
    bg = bg or ((0.52, 0.56, 0.60) if mode == 'day' else (0.02, 0.03, 0.07))
    return render2.render(pos, uv, col, tris, tm, textures(), sorted(tex.ALPHA), eye, target, fov=fov, W=W, H=H, ss=ss, bg=bg)


def grade(im):
    """numpy twin of resource/Ashfall/post.fx (sharpen, bloom, desaturation, contrast, split tint, vignette, grain) for the previews"""
    from PIL import Image
    from .tex_base import gblur
    a = np.asarray(im, np.float32)[..., :3] / 255.0
    n = np.stack([gblur(a[..., k], 1.2) for k in range(3)], -1)
    w = np.stack([gblur(a[..., k], 7.0) for k in range(3)], -1)
    c = a + (a - n) * 0.55
    c = c + np.maximum(w - 0.55, 0) * 0.55
    l = (c * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    c = l + (c - l) * 0.82
    c = (c - 0.5) * 1.10 + 0.5
    t = np.clip(l * 1.7, 0, 1)
    c = c * ((1 - t) * np.array([0.90, 0.98, 1.05]) + t * np.array([1.05, 1.0, 0.93])) * 1.16
    h, wd = c.shape[:2]
    yy, xx = np.mgrid[0:h, 0:wd]
    d2 = ((xx / wd - 0.5) ** 2 + (yy / h - 0.5) ** 2)[..., None]
    c = c * np.clip(1 - d2 * 1.15, 0, 1)
    c = c + (np.random.default_rng(1).random((h, wd, 1)) - 0.5) * 0.028
    return Image.fromarray((np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8))
