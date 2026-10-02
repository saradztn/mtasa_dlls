# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# interiors.py - furnishing and decoration of every room: rugs, thrones, tables, chairs, shelves, beds,
#                fireplace, braziers, armour stands, banners, torches, chandeliers, lanterns, gate
#                mouldings, cobwebs and spiders, door definitions.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import unit, TAU, Opening
from . import parts as P
from .parts import ST, SI, TR, FL, TL, SL, WD, DR, IR, RG, WB, OB, GL, FM, BK, BN, GD, CV
from .castle import DAIS_Z, SLAB0, SLAB1, HALL_H, op

WARM = P.WARM


def brazier(S, c, z=0.0):
    M, C = S.M, S.C
    x, y = c
    with S.lift(z):
        for k in range(3):
            a = k * TAU / 3 + 0.3
            P.bar(M, (x + np.cos(a) * 0.38, y + np.sin(a) * 0.38, 0.0), (x + np.cos(a) * 0.12, y + np.sin(a) * 0.12, 0.85), 0.05, IR, tile=0.3)
        M.cone((x, y), 0.45, 0.80, 1.05, 12, IR, tile=0.5, smooth=True, r_top=0.52)
        M.prism((x, y), 0.50, 1.02, 1.07, 12, IR, tile=0.5, cap_top=True)
        P.ring_h(M, (x, y, 1.05), 0.52, 0.025, GD, nu=16, nv=5)
        for dx, dy in ((0, 0), (0.15, 0.1), (-0.15, 0.05), (0.05, -0.15)):
            P.flame(M, (x + dx, y + dy, 1.06), 0.55, 0.32, rot=dx * 4)
        P.add_light(S.L, (x, y, 1.9), WARM, 9.0, 1.2)
        C.box((x - 0.5, y - 0.5, 0), (x + 0.5, y + 0.5, 1.1))


def armor(S, c, facing, z=0.0):
    """knight in plate armour on a stone plinth holding a halberd"""
    M, C = S.M, S.C
    x, y = c
    fx, fy = facing
    with S.lift(z):
        M.box((x - 0.5, y - 0.5, 0), (x + 0.5, y + 0.5, 0.35), TR, tile=1.0)
        for sx in (-0.13, 0.13):
            M.prism((x + sx, y), 0.085, 0.35, 1.15, 8, IR, tile=0.5, smooth=True, theta0=0.4)
            M.box((x + sx - 0.11, y - 0.14, 0.35), (x + sx + 0.11, y + 0.18, 0.43), IR, tile=0.5)
        M.box((x - 0.27, y - 0.15, 1.15), (x + 0.27, y + 0.15, 1.30), IR, tile=0.5)
        M.prism((x, y), 0.30, 1.30, 1.85, 8, IR, tile=0.6, smooth=True, theta0=0.4, ex=1.0, ey=0.62)
        P.sphere(M, (x - 0.34, y, 1.78), 0.12, IR, 8, 5)
        P.sphere(M, (x + 0.34, y, 1.78), 0.12, IR, 8, 5)
        for sx in (-0.38, 0.38):
            P.bar(M, (x + sx, y, 1.72), (x + sx * 1.05, y + fy * 0.22 + 0.0, 1.30), 0.10, IR, tile=0.5)
        P.sphere(M, (x, y, 2.02), 0.17, IR, 10, 6, sq=(1, 1, 1.15))
        P.bar(M, (x + 0.52, y, 0.35), (x + 0.52, y, 2.7), 0.04, WD, tile=0.5)
        M.cone((x + 0.52, y), 0.06, 2.7, 2.95, 4, IR, tile=0.3, theta0=np.pi / 4)
        P.bar(M, (x + 0.52, y - 0.12, 2.30), (x + 0.52, y + 0.12, 2.5), 0.03, IR, tile=0.3)
        P.bar(M, (x + 0.52, y, 2.35), (x + 0.52 + 0.30, y, 2.42), 0.03, IR, tile=0.3, h=0.18)
        C.box((x - 0.5, y - 0.5, 0), (x + 0.6, y + 0.5, 2.1))


def fireplace(S, cx, y_wall, z=0.0, width=3.0, depth=0.9, faceDir=-1):
    """stone fireplace against a wall at y = y_wall facing -y (faceDir=-1)"""
    M, C = S.M, S.C
    y0, y1 = y_wall - depth, y_wall
    x0, x1 = cx - width / 2, cx + width / 2
    with S.lift(z):
        M.box((x0, y0, 0), (x0 + 0.55, y1, 3.0), TR, tile=1.5)
        M.box((x1 - 0.55, y0, 0), (x1, y1, 3.0), TR, tile=1.5)
        M.box((x0, y0, 2.1), (x1, y1, 3.0), TR, tile=1.5)
        M.box((x0 - 0.15, y0 - 0.2, 3.0), (x1 + 0.15, y1, 3.25), TR, tile=1.5)
        # sooty back + hearth
        M.poly([(x0 + 0.55, y1 - 0.04, 0.0), (x1 - 0.55, y1 - 0.04, 0.0), (x1 - 0.55, y1 - 0.04, 2.1), (x0 + 0.55, y1 - 0.04, 2.1)], IR, hint=(0, -1, 0), tile=1.0)
        M.poly([(x0 + 0.55, y0, 0.04), (x1 - 0.55, y0, 0.04), (x1 - 0.55, y1, 0.04), (x0 + 0.55, y1, 0.04)], IR, hint=(0, 0, 1), tile=1.0)
        # chimney breast up to the ceiling
        M.box((x0 + 0.3, y1 - 0.6, 3.25), (x1 - 0.3, y1, 5.8), ST, tile=2.0)
        for k in range(3):
            xx = cx - 0.55 + k * 0.55
            P.bar(M, (xx - 0.28, y0 + 0.5, 0.18), (xx + 0.28, y0 + 0.5, 0.18), 0.09, WD, tile=0.5)
        for dx in (-0.5, -0.15, 0.2, 0.55):
            P.flame(M, (cx + dx, y0 + 0.5, 0.2), 0.62, 0.40, rot=dx * 3)
        P.add_light(S.L, (cx, y0 - 0.3, 1.2), (1.0, 0.50, 0.18), 10.0, 1.5)
        C.box((x0, y0 - 0.2, 0), (x1, y1, 3.25))


def gate_mouldings(S):
    M = S.M
    a, b, t = (-9.2, 0.6), (9.2, 0.6), 1.2
    off = 0.0
    r = 4.0
    for w, dp in ((0.26, 0.12), (0.24, 0.22), (0.22, 0.32)):
        s0, s1 = 7.2 - off, 11.2 + off
        kk = (1.0 * 4.0 + off) / (4.0 + 2 * off)
        P.arch_trim(M, a, b, t, -1, s0, s1, 2.6, kk, width=w, depth=dp, jamb=2.6)
        off += w
    # bold jamb piers beside the gate
    for sx in (-1, 1):
        x = sx * (2.0 + off + 0.1)
        M.box((min(x, x + sx * 0.5), -0.34, 0), (max(x, x + sx * 0.5), 0.0, 5.4), TR, tile=1.5)
        M.cone((x + sx * 0.25, -0.17), 0.36, 5.4, 5.8, 4, TR, tile=1.0, theta0=np.pi / 4, r_top=0.12)
    # facade carved panels, banners, torches
    for sx in (-1, 1):
        cx = sx * 5.7
        M.poly([(cx - 1.5, -0.04, 0.8), (cx + 1.5, -0.04, 0.8), (cx + 1.5, -0.04, 6.8), (cx - 1.5, -0.04, 6.8)], CV, hint=(0, -1, 0),
               uv=[(0, 1), (1, 1), (1, 0), (0, 0)] if sx > 0 else [(1, 1), (0, 1), (0, 0), (1, 0)], emis=0.30)
        P.torch(M, S.L, (sx * 3.4, -0.02), (0, -1), z=3.6)
        P.banner(M, (sx * 3.4, -0.02), (0, -1), 0.9, 2.4, 0.9)


def exterior_lights(S):
    M = S.M
    for sx in (-1, 1):
        P.lantern(M, S.L, (sx * 4.4, -8.9, -0.9), 1.5)
        P.lantern(M, S.L, (sx * 4.4, -12.3, -2.0 + 0.2 + 0.9), 1.5)
        P.lantern(M, S.L, (sx * 8.0, -7.6, 0.0), 1.8)
        P.lantern(M, S.L, (sx * 19.5, -7.6, 0.0), 1.8)
        P.lantern(M, S.L, (sx * 24.5, 20.0, 0.0), 1.8)
        P.lantern(M, S.L, (sx * 24.5, 5.0, 0.0), 1.8)
        P.lantern(M, S.L, (sx * 12.0, 41.0, 0.0), 1.8)
        P.lantern(M, S.L, (sx * 2.7, -1.2, 0.0), 1.6)


# ---------------------------------------------------------------------------------------------
def hall_props(S):
    M, C = S.M, S.C
    # rugs
    P.rug(M, -1.5, 0.30, 1.5, 7.9, 0.035)
    P.rug(M, -1.5, 12.2, 1.5, 22.8, DAIS_Z + 0.015)
    P.rug(M, -1.3, 1.5, 1.3, 5.5, SLAB1 + 0.015)
    P.rug(M, -6.9, 14.0, -4.5, 18.5, DAIS_Z + 0.015)
    P.rug(M, 4.5, 14.0, 6.9, 18.5, DAIS_Z + 0.015)
    # throne with canopy banners
    with S.lift(DAIS_Z):
        P.throne(M, C, (0.0, 24.1))
    for sx in (-1, 1):
        P.banner(M, (sx * 1.9, 25.17), (0, -1), 1.3, 3.4, DAIS_Z + 2.0)
        with S.lift(DAIS_Z):
            P.torch(M, S.L, (sx * 3.0, 25.17), (0, -1), z=2.6)
    # torches + banners between the pilasters, torches above the flights
    for sx in (-1, 1):
        nx = -sx
        for y in (15.5, 19.3, 23.1):
            with S.lift(DAIS_Z):
                P.torch(M, S.L, (sx * 8.0, y), (nx, 0), z=1.4)
            P.banner(M, (sx * 8.0, y), (nx, 0), 1.2, 2.6, DAIS_Z + 3.2)
        for y in (8.8, 11.4):
            P.torch(M, S.L, (sx * 8.0, y), (nx, 0), z=7.6)
        P.torch(M, S.L, (sx * 7.4, 1.2), (0, 1), z=3.4)
        P.torch(M, S.L, (sx * 3.4, 1.2), (0, 1), z=3.4)
    # chandeliers
    for (y, z) in ((10.0, 9.0), (16.0, 9.2), (21.5, 9.2)):
        P.chandelier(M, S.L, C, (0.0, y, z), 1.2, 10)
    P.chandelier(M, S.L, C, (0.0, 3.4, 10.3), 1.0, 8)
    # braziers, armour
    brazier(S, (-4.6, 10.2))
    brazier(S, (4.6, 10.2))
    for sx in (-1, 1):
        armor(S, (sx * 5.3, 2.5), (0, 1))
        armor(S, (sx * 7.0, 13.2), (0, -1), z=DAIS_Z)
        armor(S, (sx * 7.0, 24.4), (0, -1), z=DAIS_Z)
    # long benches / tables on the dais sides


def wing_props(S):
    M, C = S.M, S.C
    # ----------------------------------------------------------------- west ground: library
    shelves = []
    for (x0, x1) in ((-20.9, -19.3), (-17.9, -15.6), (-15.6, -13.3), (-11.8, -9.45)):
        shelves.append(((x0, 21.45, 0), (x1, 22.0, 3.5), '-y'))
    for (y0, y1) in ((1.3, 4.35), (5.8, 9.2), (10.8, 14.2), (15.8, 18.7), (20.3, 21.4)):
        shelves.append(((-21.0, y0, 0), (-20.45, y1, 3.5), '+x'))
    for (x0, x1) in ((-18.9, -16.4), (-16.4, -13.9), (-13.9, -11.4), (-11.4, -9.6)):
        shelves.append(((x0, 1.0, 0), (x1, 1.55, 3.5), '+y'))
    for (y0, y1) in ((4.3, 7.2), (7.2, 10.1), (10.1, 13.0), (13.0, 15.9), (15.9, 18.8), (18.8, 21.4)):
        shelves.append(((-9.75, y0, 0), (-9.2, y1, 3.5), '-x'))
    for lo, hi, f in shelves:
        P.bookshelf(M, C, lo, hi, f)
        # carved crown on top
        M.box((lo[0] - (0.04 if f in ('-y', '+y') else 0), lo[1] - (0.04 if f in ('-x', '+x') else 0), 3.5),
              (hi[0] + (0.04 if f in ('-y', '+y') else 0), hi[1] + (0.04 if f in ('-x', '+x') else 0), 3.62), WD, tile=1.0)
    # free standing double sided shelves + reading tables
    for y0, y1 in ((6.5, 8.9), (13.5, 15.9)):
        P.bookshelf(M, C, (-14.9, y0, 0), (-14.4, y1, 3.0), '+x')
    P.rug(M, -19.4, 8.8, -15.8, 13.8, 0.035)
    P.table(M, C, (-17.6, 11.3), (1.3, 3.0))
    for y in (10.2, 11.3, 12.4):
        P.chair(M, C, (-18.6, y), (1, 0))
        P.chair(M, C, (-16.6, y), (-1, 0))
    P.chair(M, C, (-17.6, 13.1), (0, -1))
    P.chair(M, C, (-17.6, 9.5), (0, 1))
    P.rug(M, -13.0, 16.0, -10.8, 21.0, 0.035)
    P.table(M, C, (-12.0, 18.5), (1.2, 1.2))
    P.chair(M, C, (-12.0, 17.5), (0, 1))
    P.chair(M, C, (-12.9, 18.5), (1, 0))
    P.chair(M, C, (-11.1, 18.5), (-1, 0))
    brazier(S, (-20.0, 2.6))
    for (x, y, z) in ((-15.6, 5.0, 3.9), (-15.6, 11.5, 3.9), (-15.6, 18.0, 3.9)):
        _short_chandelier(S, (x, y, z), 0.9, 8)
    # ----------------------------------------------------------------- west upper: bedroom / study
    zu = SLAB1
    with S.lift(zu):
        P.bed(M, C, (-19.4, 17.0))
        P.chest(M, C, (-19.4, 13.9), (0.55, 1.1, 0.6))
        P.chest(M, C, (-11.2, 20.7))
        P.table(M, C, (-12.5, 5.4), (1.0, 2.2), mat=WD)
        P.chair(M, C, (-13.5, 5.4), (1, 0))
        P.bookshelf(M, C, (-21.0, 1.4, 0), (-20.5, 4.6, 3.2), '+x')
    P.rug(M, -17.2, 4.0, -13.6, 11.0, zu + 0.015)
    P.rug(M, -17.2, 11.5, -13.6, 17.5, zu + 0.015)
    armor(S, (-20.2, 20.6), (1, -1), z=zu)
    for y in (6.0, 12.0, 17.0):
        P.torch(M, S.L, (-9.2, y), (-1, 0), z=zu + 1.8)
    P.banner(M, (-9.2, 9.0), (-1, 0), 1.2, 2.6, zu + 2.4)
    P.banner(M, (-9.2, 14.5), (-1, 0), 1.2, 2.6, zu + 2.4)
    for y in (6.0, 15.0):
        P.chandelier(M, S.L, C, (-15.6, y, 10.2), 1.0, 8)
    # ----------------------------------------------------------------- east ground: dining hall
    P.rug(M, 12.3, 4.5, 18.9, 20.0, 0.035)
    P.table(M, C, (15.6, 12.2), (1.7, 9.0))
    for y in np.arange(8.6, 16.0, 1.5):
        P.chair(M, C, (14.3, y), (1, 0))
        P.chair(M, C, (16.9, y), (-1, 0))
    P.chair(M, C, (15.6, 17.4), (0, -1))
    P.chair(M, C, (15.6, 7.0), (0, 1))
    for y in np.arange(9.0, 15.5, 1.5):
        for x in (15.1, 16.1):
            M.prism((x, y), 0.11, 0.78, 0.84, 8, GD, tile=0.5, smooth=True)           # plates
        P.candle(M, (15.6, y + 0.4, 0.78), 0.25)
    fireplace(S, 15.6, 22.0, faceDir=-1)
    for y in (7.0, 12.0, 17.0):
        P.torch(M, S.L, (9.2, y), (1, 0), z=3.8)
    for (x, y, z) in ((15.6, 8.5, 3.9), (15.6, 12.0, 3.9), (15.6, 16.0, 3.9)):
        _short_chandelier(S, (x, y, z), 1.0, 10)
    for sy in (3.0, 20.5):
        M.box((20.4, sy - 0.8, 0), (21.0, sy + 0.8, 0.95), WD, tile=1.0)
        C.box((20.4, sy - 0.8, 0), (21.0, sy + 0.8, 0.95))
    armor(S, (10.1, 20.6), (0, -1))
    armor(S, (20.3, 1.9), (-1, 1))
    # ----------------------------------------------------------------- east upper: armoury / great chamber
    with S.lift(zu):
        P.bed(M, C, (19.4, 17.0))
        P.chest(M, C, (19.4, 13.9), (0.55, 1.1, 0.6))
        P.chest(M, C, (11.2, 20.7))
        P.table(M, C, (12.5, 5.4), (1.0, 2.2), mat=WD)
        P.chair(M, C, (13.5, 5.4), (-1, 0))
        P.bookshelf(M, C, (20.5, 1.4, 0), (21.0, 4.6, 3.2), '-x')
    P.rug(M, 13.6, 4.0, 17.2, 11.0, zu + 0.015)
    P.rug(M, 13.6, 11.5, 17.2, 17.5, zu + 0.015)
    armor(S, (20.2, 20.6), (-1, -1), z=zu)
    for y in (6.0, 12.0, 17.0):
        P.torch(M, S.L, (9.2, y), (1, 0), z=zu + 1.8)
    P.banner(M, (9.2, 9.0), (1, 0), 1.2, 2.6, zu + 2.4)
    P.banner(M, (9.2, 14.5), (1, 0), 1.2, 2.6, zu + 2.4)
    for y in (6.0, 15.0):
        P.chandelier(M, S.L, C, (15.6, y, 10.2), 1.0, 8)


def _short_chandelier(S, c, R, nc):
    """chandelier for the 6.4 m high ground floor rooms: a short chain up to the beam"""
    M, C = S.M, S.C
    cx, cy, cz = c
    P.ring_h(M, (cx, cy, cz), R, 0.04, IR, nu=28, nv=6)
    P.ring_h(M, (cx, cy, cz - 0.28), R * 0.55, 0.03, IR, nu=20, nv=5)
    for k in range(4):
        a = k * np.pi / 2 + np.pi / 4
        P.bar(M, (cx, cy, cz + 0.9), (cx + np.cos(a) * R, cy + np.sin(a) * R, cz), 0.03, IR, tile=0.3, caps=False)
        P.bar(M, (cx, cy, cz - 0.28), (cx + np.cos(a) * R * 0.55, cy + np.sin(a) * R * 0.55, cz - 0.28), 0.03, IR, tile=0.3)
    for z in np.arange(cz + 0.9, SLAB0 - 0.45, 0.21):
        P.bar(M, (cx, cy, z), (cx, cy, min(z + 0.16, SLAB0 - 0.45)), 0.045, IR, tile=0.3, caps=False)
    P.sphere(M, (cx, cy, cz - 0.5), 0.09, IR, 8, 5, sq=(1, 1, 1.4))
    for k in range(nc):
        a = k * TAU / nc
        px, py = cx + np.cos(a) * R, cy + np.sin(a) * R
        M.prism((px, py), 0.05, cz, cz + 0.05, 8, GD, tile=0.3, smooth=True)
        P.candle(M, (px, py, cz + 0.05), 0.2)
    P.add_light(S.L, (cx, cy, cz + 0.4), WARM, 10.0, 1.2)


def keep_props(S):
    M, C = S.M, S.C
    cyc = S.meta['keep_center'][1]
    # wall torches up the well (placed on the side/back walls)
    for z, y in ((4.4, 28.5), (8.0, 38.4), (11.6, 28.5), (15.2, 38.4), (18.8, 28.5), (24.8, 38.4), (24.8, 28.0)):
        for sx in (-1, 1):
            P.torch(M, S.L, (sx * 6.0, y), (-sx, 0), z=z)
    for x in (-3.0, 3.0):
        P.torch(M, S.L, (x, 38.98), (0, -1), z=5.5)
        P.torch(M, S.L, (x, 38.98), (0, -1), z=13.0)
        P.torch(M, S.L, (x, 38.98), (0, -1), z=19.5)
    for x in (-3.0, 3.0):
        P.torch(M, S.L, (x, 26.45), (0, 1), z=5.2)
    # observation level: chandelier, rug, banners
    P.chandelier(M, S.L, C, (0.0, cyc, 26.2), 1.3, 10)
    P.rug(M, -5.6, 26.9, -4.6, 38.5, 22.02)
    P.rug(M, 4.6, 26.9, 5.6, 38.5, 22.02)
    for y in (30.5, 35.0):
        P.banner(M, (-5.98, y), (1, 0), 1.3, 3.0, 4.6)
        P.banner(M, (5.98, y), (-1, 0), 1.3, 3.0, 4.6)
    # chest + torch brackets by the entrance
    with S.lift(DAIS_Z):
        P.chest(M, C, (-5.0, 38.2), (1.2, 0.6, 0.6))
        P.chest(M, C, (5.0, 38.2), (1.2, 0.6, 0.6))


# ---------------------------------------------------------------------------------------------
def webs(S):
    """cobwebs ("بيوت العنكبوت"): ceiling corners, wall corners, beam junctions, window orbs, spiders on threads"""
    M = S.M
    rng = S.rng
    interior = {
        'hall': ((-8.0, 1.2), (8.0, 25.2)),
        'wing_w_g': ((-21.0, 1.0), (-9.2, 22.0)), 'wing_w_u': ((-21.0, 1.0), (-9.2, 22.0)),
        'wing_e_g': ((9.2, 1.0), (21.0, 22.0)), 'wing_e_u': ((9.2, 1.0), (21.0, 22.0)),
        'keep': ((-6.0, 26.4), (6.0, 39.0)),
    }
    for name, ((x0, y0), (x1, y1)) in interior.items():
        zc = S.ceil[name]
        for cx_, sx in ((x0, 1), (x1, -1)):
            for cy_, sy in ((y0, 1), (y1, -1)):
                p = np.array([cx_ + sx * 0.03, cy_ + sy * 0.03, zc - 0.03])
                L1 = rng.uniform(1.2, 2.2)
                L2 = rng.uniform(1.2, 2.2)
                P.web_corner(M, p, (sx, 0, 0), (0, sy, 0), L1, L2)
                # vertical wall webs
                P.web_corner(M, p, (sx, 0, 0), (0, 0, -1), rng.uniform(1.0, 1.8), rng.uniform(1.2, 2.4))
                P.web_corner(M, p, (0, sy, 0), (0, 0, -1), rng.uniform(1.0, 1.8), rng.uniform(1.2, 2.4))
                if rng.random() < 0.6:
                    P.spider(M, p + np.array([sx * 0.9, sy * 0.9, -rng.uniform(0.6, 1.4)]), 1.0, thread_to=zc - 0.03)
        # floor corners (dusty low webs)
        zf = 0.03 if name != 'wing_w_u' and name != 'wing_e_u' else SLAB1 + 0.03
        if name == 'keep':
            zf = DAIS_Z + 0.03
        for cx_, sx in ((x0, 1), (x1, -1)):
            for cy_, sy in ((y0, 1), (y1, -1)):
                if rng.random() < 0.55:
                    p = np.array([cx_ + sx * 0.03, cy_ + sy * 0.03, zf + 0.0])
                    P.web_corner(M, p + [0, 0, 0.9], (sx, 0, 0), (0, 0, -1), 1.0, 0.9)
                    P.web_corner(M, p + [0, 0, 0.9], (0, sy, 0), (0, 0, -1), 1.0, 0.9)
    # beams in the hall (webs between beam and wall)
    for y in S.meta['hall_beams']:
        for sx in (-1, 1):
            if rng.random() < 0.8:
                p = np.array([sx * 7.97, y + rng.choice([-0.26, 0.26]), 12.05])
                P.web_corner(M, p, (0, 1 if rng.random() < 0.5 else -1, 0), (0, 0, -1), rng.uniform(1.0, 1.8), rng.uniform(0.9, 1.7))
    # window orbs (interior side)
    for (apex_pt, nl, zb, w) in S.windows:
        from .light import room_index
        r, _ = room_index(apex_pt[None, :], S.rooms, 0.3)
        if r[0] < 0 or rng.random() < 0.35:
            continue
        c = apex_pt + np.array([nl[0] * 0.02, nl[1] * 0.02, -0.55])
        P.web_orb(M, c, (nl[0], nl[1], 0), rng.uniform(1.0, 1.5))
        if rng.random() < 0.5:
            P.spider(M, c + np.array([nl[0] * 0.02, nl[1] * 0.02, -0.1]), 1.1)
    # hall features: between gallery columns and beam, throne canopy, chandeliers
    P.web_orb(M, (1.6, 5.53, 4.7), (0, 1, 0), 1.8)
    P.web_orb(M, (-1.6, 5.53, 4.6), (0, 1, 0), 1.7)
    P.web_corner(M, (3.34, 5.6, 5.55), (-1, 0, 0), (0, 0, -1), 1.6, 1.2)
    P.web_corner(M, (-3.34, 5.6, 5.55), (1, 0, 0), (0, 0, -1), 1.6, 1.2)
    P.web_orb(M, (0.0, 24.6, 9.0), (0, -1, 0), 2.2)
    P.web_orb(M, (-4.4, 25.15, 8.0), (0, -1, 0), 1.6)
    P.web_orb(M, (4.4, 25.15, 8.2), (0, -1, 0), 1.6)
    for y in (13.0, 19.0, 24.0):
        for sx in (-1, 1):
            P.web_corner(M, (sx * 7.97, y, 12.57), (0, 1, 0), (-sx, 0, 0), 1.6, 1.8)
    for (x, y, z) in ((0.0, 10.0, 11.4), (0.0, 16.0, 11.6), (0.0, 21.5, 11.6)):
        P.spider(M, (x + 0.8, y + 0.4, z - 0.6), 1.3, thread_to=12.05)
    # tower stair: webs hanging in the well
    cyc = S.meta['keep_center'][1]
    for z in (6.0, 12.0, 18.0, 25.0):
        P.web_orb(M, (-5.95, cyc + rng.uniform(-3, 3), z + 1.2), (1, 0, 0), 2.0)
        P.web_orb(M, (5.95, cyc + rng.uniform(-3, 3), z + 1.2), (-1, 0, 0), 2.0)
    for z, sy in ((8.0, 1), (14.5, 1), (21.0, 1)):
        P.spider(M, (5.0, 36.5, z), 1.4, thread_to=z + 1.8)
    # spiders in the wings
    for (x, y, z) in ((-19.0, 4.0, 4.6), (-11.0, 19.0, 4.8), (-15.0, 12.0, 5.0), (-19.0, 4.0, 11.0), (-12.0, 18.0, 11.2),
                      (19.0, 4.0, 4.6), (11.0, 19.0, 4.8), (15.0, 14.0, 5.0), (19.0, 4.0, 11.0), (12.0, 18.0, 11.2)):
        P.spider(M, (x, y, z), 1.3, thread_to=(5.95 if z < 8 else 12.05))


# ---------------------------------------------------------------------------------------------
def doors(S):
    """door objects: (model, hinge xyz, closed rz, open rz)"""
    D = S.doors
    D.append(dict(name='gate_l', model='gate', hinge=(-2.0, 0.6, 0.0), rz=0.0, open_rz=95.0))
    D.append(dict(name='gate_r', model='gate', hinge=(2.0, 0.6, 0.0), rz=180.0, open_rz=180.0 - 95.0))
    D.append(dict(name='w_ground', model='door', hinge=(-8.6, 1.9, 0.0), rz=90.0, open_rz=90.0 + 95.0))
    D.append(dict(name='w_upper', model='door', hinge=(-8.6, 4.1, SLAB1), rz=90.0, open_rz=90.0 + 95.0))
    D.append(dict(name='e_ground', model='door', hinge=(8.6, 1.9, 0.0), rz=90.0, open_rz=90.0 - 95.0))
    D.append(dict(name='e_upper', model='door', hinge=(8.6, 4.1, SLAB1), rz=90.0, open_rz=90.0 - 95.0))
    D.append(dict(name='keep_w', model='door', hinge=(-5.7, 25.8, DAIS_Z), rz=0.0, open_rz=95.0))
    D.append(dict(name='keep_e', model='door', hinge=(5.7, 25.8, DAIS_Z), rz=180.0, open_rz=180.0 - 95.0))


def furnish(S):
    gate_mouldings(S)
    exterior_lights(S)
    hall_props(S)
    wing_props(S)
    keep_props(S)
    webs(S)
    doors(S)
