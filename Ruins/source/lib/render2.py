# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# render2.py - ctypes front-end of render2.c (game-like preview: texture * baked vertex colour)
import ctypes
import os
import subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MAXLEV = 12
TI = 1 + 3 * MAXLEV


def _lib():
    so = os.path.join(HERE, 'librender2.so')
    src = os.path.join(HERE, 'render2.c')
    if not os.path.exists(so) or os.path.getmtime(so) < os.path.getmtime(src):
        subprocess.check_call(['gcc', '-O3', '-shared', '-fPIC', src, '-o', so, '-lm'])
    return ctypes.CDLL(so)


def _mips(img):
    out = [img]
    im = Image.fromarray(img, 'RGBA')
    w, h = im.size
    while (w > 1 or h > 1) and len(out) < MAXLEV:
        w, h = max(1, w // 2), max(1, h // 2)
        im = im.resize((w, h), Image.BOX)
        out.append(np.asarray(im))
    return out


def render(pos, uv, vcol, tris, tmat, textures, alpha_mats, eye, target, up=(0, 0, 1), fov=40.0, W=1600, H=900, ss=2, cuts=(),
           bg=(0.02, 0.025, 0.05), gamma=1.0, tonemap=True):
    """textures: list (per material) of uint8 HxWx3|4 arrays"""
    lib = _lib()
    nmat = len(textures)
    info = np.zeros((nmat, TI), np.int32)
    chunks = []
    off = 0
    for m, img in enumerate(textures):
        if img.shape[2] == 3:
            img = np.concatenate([img, np.full(img.shape[:2] + (1,), 255, np.uint8)], 2)
        lv = _mips(np.ascontiguousarray(img))
        info[m, 0] = len(lv)
        for i, l in enumerate(lv):
            info[m, 1 + 3 * i], info[m, 2 + 3 * i], info[m, 3 + 3 * i] = l.shape[1], l.shape[0], off
            chunks.append(l.reshape(-1))
            off += l.size
    data = np.ascontiguousarray(np.concatenate(chunks), np.uint8)
    am = np.zeros(nmat, np.int32)
    for a in alpha_mats:
        am[a] = 1
    P = ctypes.POINTER
    f32, i32, u8 = P(ctypes.c_float), P(ctypes.c_int), P(ctypes.c_uint8)
    lib.render2.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, f32, f32, f32, ctypes.c_int, i32, i32, ctypes.c_int, i32, u8, i32, f32,
                            ctypes.c_float, f32, ctypes.c_int, f32, f32]
    w, h = W * ss, H * ss
    out = np.zeros((h, w, 3), np.float32)
    pos = np.ascontiguousarray(pos, np.float32)
    uv = np.ascontiguousarray(uv, np.float32)
    vcol = np.ascontiguousarray(vcol, np.float32)
    tris = np.ascontiguousarray(tris, np.int32)
    tmat = np.ascontiguousarray(tmat, np.int32)
    cam = np.array([*eye, *target, *up, fov], np.float32)
    cu = np.ascontiguousarray(np.array(cuts, np.float32).reshape(-1, 4))
    bgc = np.array(bg, np.float32)
    lib.render2(w, h, len(pos), pos.ctypes.data_as(f32), uv.ctypes.data_as(f32), vcol.ctypes.data_as(f32), len(tris), tris.ctypes.data_as(i32),
                tmat.ctypes.data_as(i32), nmat, info.ctypes.data_as(i32), data.ctypes.data_as(u8), am.ctypes.data_as(i32), cam.ctypes.data_as(f32),
                gamma, out.ctypes.data_as(f32), len(cu), cu.ctypes.data_as(f32), bgc.ctypes.data_as(f32))
    out = out.reshape(H, ss, W, ss, 3).mean(axis=(1, 3))
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
