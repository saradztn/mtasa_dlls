# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# scene.py - turns the layout into ground tile meshes (baked, per tile) and, for previews, a full flattened scene.
# -----------------------------------------------------------------------------
import numpy as np
from . import layout as LY, bake
from .kit import REG, bin_mesh, rotz
from .mb import Mesh


def tile_key(cx, cy):
    ix = int(np.clip(np.searchsorted(LY.TILE_X, cx, side='right') - 1, 0, len(LY.TILE_X) - 2))
    iy = int(np.clip(np.searchsorted(LY.TILE_Y, cy, side='right') - 1, 0, len(LY.TILE_Y) - 2))
    return ix, iy


def ground_meshes():
    """{(ix, iy): Mesh in park coordinates (surface + paths)} and {(ix,iy): (P, N, F)} height field mesh for collision"""
    tiles, hf = {}, {}
    for iy in range(3):
        for ix in range(4):
            M, h = LY.ground_tile(ix, iy)
            tiles[(ix, iy)] = M
            hf[(ix, iy)] = h
    Mp = Mesh()
    LY.build_paths(Mp)
    for key, sub in bin_mesh(Mp, tile_key).items():
        tiles[key].chunks += sub.chunks
    return tiles, hf


def bake_ground(M, L, cfg, night):
    pos, nrm, uv, tris, tmat, emis = bake.flatten(M)
    shadow = LY.tree_shadow_fn(L.trees)
    ao = (lambda P, N: shadow(P, N, 0.15)) if night else (lambda P, N: shadow(P, N, 0.42))
    extra = LY.lamp_pool(pos, L.lamps) if night else None
    col = bake.bake(pos, nrm, emis, cfg, ao=ao, extra=extra)
    return pos, nrm, uv, tris, tmat, col


def full_scene(L, mode, textures_n, only=None, skip=()):
    """flattened scene (park coordinates) for preview renders"""
    cfg = bake.DAY if mode == 'day' else bake.NIGHT
    P, U, T, TM, C = [], [], [], [], []
    off = 0

    def push(pos, uv, tris, tmat, col):
        nonlocal off
        P.append(pos); U.append(uv); T.append(tris + off); TM.append(tmat); C.append(col); off += len(pos)
    tiles, _ = ground_meshes()
    for key, M in tiles.items():
        pos, nrm, uv, tris, tmat, col = bake_ground(M, L, cfg, mode != 'day')
        push(pos, uv, tris, tmat, col)
    cache = {}
    for o in L.obj:
        if only and o['m'] not in only or o['m'] in skip:
            continue
        if o['m'] not in cache:
            a = REG[o['m']]()
            pos, nrm, uv, tris, tmat, emis = bake.flatten(a.M)
            cache[o['m']] = (pos, nrm, uv, tris, tmat, bake.bake(pos, nrm, emis, cfg, a.ao, glow=cfg['glow'] if mode != 'day' else a.day_glow))
        pos, nrm, uv, tris, tmat, col = cache[o['m']]
        R = rotz(o['rz'])
        push(pos @ R.T + np.array([o['x'], o['y'], o['z']]), uv, tris, tmat, col)
    return (np.concatenate(P), np.concatenate(U), np.concatenate(C), np.concatenate(T), np.concatenate(TM))
