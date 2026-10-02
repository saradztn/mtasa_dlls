# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# render.py - ctypes front-end for render.c (preview / QA renderer, not a game asset)
import ctypes
import os
import subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MAXLEV = 12
TI = 1 + 3 * MAXLEV


def _lib():
    so = os.path.join(HERE, 'librender.so')
    src = os.path.join(HERE, 'render.c')
    if not os.path.exists(so) or os.path.getmtime(so) < os.path.getmtime(src):
        subprocess.check_call(['gcc', '-O3', '-fopenmp', '-shared', '-fPIC', src, '-o', so, '-lm'])
    return ctypes.CDLL(so)


def _mips(img):
    """img uint8 HxWx3 -> list of mip levels"""
    out = [img]
    im = Image.fromarray(img)
    w, h = im.size
    while w > 1 or h > 1:
        w, h = max(1, w // 2), max(1, h // 2)
        out.append(np.asarray(im.resize((w, h), Image.BOX)))
        im = Image.fromarray(out[-1])
        if len(out) >= MAXLEV:
            break
    return out


class Scene:
    def __init__(self, pos, nrm, uv, tris, tmat, nmat):
        self.pos = np.ascontiguousarray(pos, np.float32)
        self.nrm = np.ascontiguousarray(nrm, np.float32)
        self.uv = np.ascontiguousarray(uv, np.float32)
        self.tris = np.ascontiguousarray(tris, np.int32)
        self.tmat = np.ascontiguousarray(tmat, np.int32)
        self.nmat = nmat
        self.tex = {}          # (mat, kind) -> uint8 HxWx3   kind: 0 albedo 1 normal 2 orm
        self.param = np.zeros((nmat, 8), np.float32)
        self.param[:, 0:3] = 0.5
        self.param[:, 3] = 0.5

    def set_tex(self, mat, kind, img):
        self.tex[(mat, kind)] = np.ascontiguousarray(img[..., :3], np.uint8)

    def pack(self):
        info = np.zeros((self.nmat * 3, TI), np.int32)
        chunks = []
        off = 0
        for m in range(self.nmat):
            for k in range(3):
                img = self.tex.get((m, k))
                if img is None:
                    continue
                lv = _mips(img)
                info[m * 3 + k, 0] = len(lv)
                for i, l in enumerate(lv):
                    info[m * 3 + k, 1 + 3 * i] = l.shape[1]
                    info[m * 3 + k, 2 + 3 * i] = l.shape[0]
                    info[m * 3 + k, 3 + 3 * i] = off
                    chunks.append(l.reshape(-1))
                    off += l.size
        data = np.concatenate(chunks) if chunks else np.zeros(3, np.uint8)
        return np.ascontiguousarray(info), np.ascontiguousarray(data, np.uint8)


def render(scene, eye, target, up=(0, 0, 1), fov=25.0, W=1600, H=600, ss=2,
           ortho=False, orthoh=1.0, gamma=2.2, exposure=1.0):
    lib = _lib()
    info, data = scene.pack()
    cam = np.array([*eye, *target, *up, fov, 1.0 if ortho else 0.0, orthoh], np.float32)
    opts = np.array([gamma, exposure], np.float32)
    w, h = W * ss, H * ss
    out = np.zeros((h, w, 3), np.float32)
    P = ctypes.POINTER
    f32 = P(ctypes.c_float)
    i32 = P(ctypes.c_int)
    u8 = P(ctypes.c_uint8)
    lib.render.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, f32, f32, f32, ctypes.c_int, i32, i32,
                           ctypes.c_int, i32, u8, f32, f32, f32, f32]
    lib.render(w, h, len(scene.pos),
               scene.pos.ctypes.data_as(f32), scene.nrm.ctypes.data_as(f32), scene.uv.ctypes.data_as(f32),
               len(scene.tris), scene.tris.ctypes.data_as(i32), scene.tmat.ctypes.data_as(i32),
               scene.nmat, info.ctypes.data_as(i32), data.ctypes.data_as(u8),
               np.ascontiguousarray(scene.param).ctypes.data_as(f32),
               cam.ctypes.data_as(f32), opts.ctypes.data_as(f32), out.ctypes.data_as(f32))
    out = out.reshape(H, ss, W, ss, 3).mean(axis=(1, 3))
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
