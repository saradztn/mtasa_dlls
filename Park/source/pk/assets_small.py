# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# assets_small.py - small park props (bench, table, bin, lamp, board, planter, fence, rocks, cone, crate, cabinet,
#                   hydrant, bike rack, manhole, duck ...).  Ground = z 0, every model is one atomic.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit, TAU
from . import gx
from .kit import asset, m, place, place_col, col_bar, REG


# ------------------------------------------------------------------------------------------ bench
def bench_geo(M, C, L=1.8):
    W, WD, IR = m('wood'), m('wooddark'), m('iron')
    hx = L / 2
    # seat slats
    for k, y in enumerate((-0.17, 0.0, 0.17)):
        M.box((-hx, y - 0.07, 0.44), (hx, y + 0.07, 0.48), W, tile=1.0)
    # back slats (leaning back)
    for k, z in enumerate((0.60, 0.74, 0.88)):
        y = -0.30 - (z - 0.5) * 0.18
        M.box((-hx, y - 0.02, z - 0.06), (hx, y + 0.02, z + 0.06), W, tile=1.0)
    # cast iron side frames (two per end)
    for sx in (-1, 1):
        x = sx * (hx - 0.12)
        gx.bar(M, (x, 0.22, 0.0), (x, 0.22, 0.43), 0.05, IR, h=0.07, tile=0.5)           # front leg
        gx.bar(M, (x, -0.26, 0.0), (x, -0.27, 0.43), 0.05, IR, h=0.07, tile=0.5)         # rear leg
        gx.bar(M, (x, -0.27, 0.43), (x, -0.40, 0.95), 0.05, IR, h=0.07, tile=0.5)        # back support
        gx.bar(M, (x, 0.22, 0.43), (x, -0.30, 0.43), 0.045, IR, h=0.04, tile=0.5)        # seat rail
        gx.bar(M, (x, 0.20, 0.44), (x, 0.22, 0.64), 0.04, IR, h=0.05, tile=0.5)          # armrest post
        gx.bar(M, (x, 0.24, 0.64), (x, -0.30, 0.64), 0.05, IR, h=0.045, tile=0.5)        # armrest
        gx.sphere(M, (x, 0.24, 0.655), 0.035, IR, 8, 5)
        gx.bar(M, (x, -0.26, 0.12), (x, 0.22, 0.12), 0.03, IR, h=0.03, tile=0.5)         # lower stretcher
        for px in (-1, 1):
            gx.bar(M, (x + px * 0.02, 0.22, -0.005), (x + px * 0.02, 0.22, 0.01), 0.07, IR, h=0.09, tile=0.5)
    C.box((-hx, -0.34, 0.0), (hx, 0.27, 0.50))
    C.box((-hx, -0.44, 0.45), (hx, -0.22, 0.97))


@asset('pk_bench', 'props')
def bench():
    M, C = Mesh(), Col()
    bench_geo(M, C)
    return M, C


# --------------------------------------------------------------------------------------- picnic table
@asset('pk_picnic', 'props')
def picnic():
    M, C = Mesh(), Col()
    W, WD = m('wood_light'), m('wood')
    L = 1.9
    for y in (-0.30, -0.10, 0.10, 0.30):
        M.box((-L / 2, y - 0.045, 0.72), (L / 2, y + 0.045, 0.76), W, tile=1.0)
    for sy in (-1, 1):
        for y in (0.0,):
            M.box((-L / 2, sy * 0.78 - 0.13, 0.42), (L / 2, sy * 0.78 + 0.13, 0.46), W, tile=1.0)
    for sx in (-1, 1):
        x = sx * 0.62
        # A-frame legs
        for sy in (-1, 1):
            gx.bar(M, (x, sy * 0.88, 0.0), (x, sy * 0.10, 0.70), 0.07, WD, h=0.05, tile=1.0)
        gx.bar(M, (x, -0.88, 0.40), (x, 0.88, 0.40), 0.07, WD, h=0.04, tile=1.0)
        gx.bar(M, (x, -0.30, 0.70), (x, 0.30, 0.70), 0.07, WD, h=0.05, tile=1.0)
    C.box((-L / 2, -0.38, 0.0), (L / 2, 0.38, 0.77))
    for sy in (-1, 1):
        C.box((-L / 2, sy * 0.78 - 0.14, 0.0), (L / 2, sy * 0.78 + 0.14, 0.47))
    return M, C


# --------------------------------------------------------------------------------------------- bin
@asset('pk_bin', 'props')
def trash_bin():
    M, C = Mesh(), Col()
    W, IR, WD = m('wood'), m('iron'), m('wooddark')
    n = 12
    M.prism((0, 0), 0.27, 0.05, 0.80, n, W, tile=0.6, cap_top=False)
    gx.lathe(M, (0, 0), [(0.0, 0.0), (0.30, 0.0), (0.30, 0.07), (0.275, 0.09)], 24, IR, tile=0.6)
    for z in (0.14, 0.43, 0.70):
        gx.lathe(M, (0, 0), [(0.272, z - 0.025), (0.292, z - 0.02), (0.292, z + 0.02), (0.272, z + 0.025)], 24, IR, tile=0.4)
    gx.lathe(M, (0, 0), [(0.30, 0.79), (0.30, 0.84), (0.255, 0.86), (0.21, 0.84), (0.20, 0.72), (0.0, 0.70)], 24, IR, tile=0.6)
    gx.lathe(M, (0, 0), [(0.0, 0.72), (0.0, 0.90), (0.03, 0.92), (0.07, 0.90)], 12, IR, tile=0.3)
    C.box((-0.30, -0.30, 0.0), (0.30, 0.30, 0.86))
    return M, C


# ------------------------------------------------------------------------------------------- lamp posts
def lantern(M, z0, IR, emis=0.9):
    """lantern with emissive glass, iron cage, roof and finial; centred on x=y=0, base at z0"""
    G = m('lamp')
    gx.lathe(M, (0, 0), [(0.0, z0), (0.12, z0), (0.19, z0 + 0.07), (0.215, z0 + 0.11), (0.215, z0 + 0.13)], 16, IR, tile=0.5)
    # glass: 8 sided tapered shaft
    gx.lathe(M, (0, 0), [(0.19, z0 + 0.13), (0.215, z0 + 0.42), (0.235, z0 + 0.62)], 8, G, tile=0.6, emis=0.85, theta0=np.pi / 8)
    for k in range(8):
        a = TAU * k / 8 + np.pi / 8 - np.pi / 8
        pa = np.array([np.cos(a), np.sin(a)])
        gx.bar(M, (pa[0] * 0.19, pa[1] * 0.19, z0 + 0.13), (pa[0] * 0.238, pa[1] * 0.238, z0 + 0.62), 0.022, IR, h=0.022, tile=0.5)
    gx.lathe(M, (0, 0), [(0.255, z0 + 0.60), (0.255, z0 + 0.64), (0.0, z0 + 0.64)], 16, IR, tile=0.5)
    gx.lathe(M, (0, 0), [(0.0, z0 + 0.64), (0.30, z0 + 0.64), (0.29, z0 + 0.68), (0.08, z0 + 0.92), (0.0, z0 + 0.94)], 16, IR, tile=0.6)
    gx.sphere(M, (0, 0, z0 + 0.98), 0.045, IR, 8, 5)
    gx.cyl(M, (0, 0, z0 + 0.98), (0, 0, z0 + 1.14), 0.014, 0.003, 6, IR, tile=0.3, caps=False)


@asset('pk_lamp', 'props', dist=220)
def lamp():
    M, C = Mesh(), Col()
    IR = m('iron')
    prof = [(0.0, -0.05), (0.24, -0.05), (0.24, 0.04), (0.20, 0.08), (0.20, 0.16), (0.15, 0.22), (0.13, 0.34), (0.09, 0.48), (0.09, 0.62),
            (0.065, 0.70), (0.052, 0.82), (0.045, 1.0), (0.045, 3.00), (0.058, 3.05), (0.058, 3.12), (0.11, 3.16), (0.11, 3.22), (0.075, 3.26), (0.0, 3.28)]
    gx.lathe(M, (0, 0), prof, 16, IR, tile=0.6)
    for z in (1.0, 2.0):
        gx.lathe(M, (0, 0), [(0.045, z - 0.04), (0.07, z - 0.025), (0.07, z + 0.025), (0.045, z + 0.04)], 16, IR, tile=0.4)
    # cross arm with two scrolls under the lantern (decorative)
    for s in (-1, 1):
        pts = [(s * 0.02, 0, 2.85), (s * 0.20, 0, 2.78), (s * 0.30, 0, 2.62), (s * 0.24, 0, 2.52), (s * 0.15, 0, 2.58)]
        gx.tube(M, pts, [0.016] * 5, 6, IR, tile=0.4, cap_end=True)
    lantern(M, 3.28, IR)
    C.box((-0.20, -0.20, 0.0), (0.20, 0.20, 0.5))
    C.box((-0.08, -0.08, 0.5), (0.08, 0.08, 3.1))
    return M, C


@asset('pk_bollard', 'props')
def bollard():
    M, C = Mesh(), Col()
    IR, G = m('iron'), m('lamp')
    gx.lathe(M, (0, 0), [(0.0, -0.03), (0.14, -0.03), (0.14, 0.05), (0.11, 0.10), (0.10, 0.60), (0.12, 0.64), (0.12, 0.68), (0.10, 0.70)], 16, IR, tile=0.5)
    gx.lathe(M, (0, 0), [(0.10, 0.70), (0.10, 0.92)], 8, G, tile=0.5, emis=0.85, theta0=np.pi / 8)
    gx.lathe(M, (0, 0), [(0.0, 0.92), (0.125, 0.92), (0.125, 0.95), (0.06, 1.02), (0.0, 1.04)], 16, IR, tile=0.5)
    C.box((-0.13, -0.13, 0.0), (0.13, 0.13, 1.0))
    return M, C


# -------------------------------------------------------------------------------------------- info board
@asset('pk_board', 'props')
def board():
    M, C = Mesh(), Col()
    WD, W, IR, SG = m('wooddark'), m('wood'), m('iron'), m('sign_info')
    for sx in (-1, 1):
        M.box((sx * 0.62 - 0.05, -0.05, 0.0), (sx * 0.62 + 0.05, 0.05, 1.75), WD, tile=0.8)
    # frame + panel
    x0, x1, z0, z1 = -0.56, 0.56, 0.65, 1.55
    M.box((x0 - 0.05, -0.04, z0 - 0.05), (x1 + 0.05, 0.04, z1 + 0.05), W, tile=0.8, skip=('+y',))
    M.poly([(x0, 0.041, z0), (x1, 0.041, z0), (x1, 0.041, z1), (x0, 0.041, z1)], SG, hint=(0, 1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    # little gable roof
    M.poly([(-0.78, -0.16, 1.80), (0.78, -0.16, 1.80), (0.78, 0.0, 2.02), (-0.78, 0.0, 2.02)], m('shingle'), hint=(0, -0.5, 1), tile=0.8)
    M.poly([(-0.78, 0.16, 1.80), (-0.78, 0.0, 2.02), (0.78, 0.0, 2.02), (0.78, 0.16, 1.80)], m('shingle'), hint=(0, 0.5, 1), tile=0.8)
    for sy in (-1, 1):
        M.poly([(-0.78, sy * 0.16, 1.80), (0.78, sy * 0.16, 1.80), (0.78, sy * 0.16, 1.72), (-0.78, sy * 0.16, 1.72)], WD, hint=(0, sy, 0), tile=0.6)
    for sx in (-1, 1):
        M.poly([(sx * 0.78, -0.16, 1.80), (sx * 0.78, 0.16, 1.80), (sx * 0.78, 0.0, 2.02)], WD, hint=(sx, 0, 0), tile=0.6)
    C.box((-0.72, -0.12, 0.0), (0.72, 0.12, 1.85))
    return M, C


# ----------------------------------------------------------------------------------------------- planter
def planter_geo(M, C, q):
    W, WD, IR, D = m('wood'), m('wooddark'), m('iron'), m('dirt')
    M.box((-0.65, -0.26, 0.04), (0.65, 0.26, 0.46), W, tile=0.8)
    for x in (-0.60, 0.60):
        M.box((x - 0.04, -0.285, 0.0), (x + 0.04, 0.285, 0.47), WD, tile=0.5)
    M.box((-0.67, -0.29, 0.44), (0.67, 0.29, 0.48), WD, tile=0.5)
    M.poly([(-0.60, -0.22, 0.455), (0.60, -0.22, 0.455), (0.60, 0.22, 0.455), (-0.60, 0.22, 0.455)], D, hint=(0, 0, 1), tile=0.5)
    M.poly([(-0.60, -0.22, 0.455), (-0.60, 0.22, 0.455), (0.60, 0.22, 0.455), (0.60, -0.22, 0.455)], D, hint=(0, 0, 1), tile=0.5)
    rng = np.random.default_rng(40 + q)
    FL = m('flowers')
    uvq = [(0, 0, .5, .5), (.5, 0, 1, .5), (0, .5, .5, 1), (.5, .5, 1, 1)]
    for i in range(16):
        x = -0.55 + 1.1 * (i + rng.uniform(-0.2, 0.2)) / 15
        y = rng.uniform(-0.12, 0.12)
        sz = rng.uniform(0.50, 0.70)
        ang = rng.uniform(0, np.pi)
        a = np.array([np.cos(ang), np.sin(ang) * 0.5, 0.0])
        a = unit(a) * sz / 2
        q_ = uvq[q % 4] if rng.random() < 0.8 else uvq[rng.integers(4)]
        tilt = rng.uniform(-0.3, 0.3)
        b = np.array([0, tilt * 0.4, 1.0]) * sz / 2
        gx.card(M, (x, y, 0.46 + sz * 0.42), a, b, FL, (0, 0, 1) if True else None, q_)
    C.box((-0.67, -0.29, 0.0), (0.67, 0.29, 0.50))


@asset('pk_planter', 'props')
def planter():
    M, C = Mesh(), Col()
    planter_geo(M, C, 0)
    return M, C


@asset('pk_planter2', 'props')
def planter2():
    M, C = Mesh(), Col()
    planter_geo(M, C, 2)
    return M, C


# ----------------------------------------------------------------------------------------------- fences
@asset('pk_fence', 'struct', dist=200)
def fence():
    """wrought iron fence panel 2.5 m long (x -1.25..1.25), 1.5 m high"""
    M, C = Mesh(), Col()
    IR = m('iron')
    L, H = 2.5, 1.5
    hx = L / 2
    gx.bar(M, (-hx, 0, 0.18), (hx, 0, 0.18), 0.05, IR, h=0.05, tile=0.5)
    gx.bar(M, (-hx, 0, 0.42), (hx, 0, 0.42), 0.03, IR, h=0.03, tile=0.5)
    gx.bar(M, (-hx, 0, H - 0.12), (hx, 0, H - 0.12), 0.05, IR, h=0.05, tile=0.5)
    gx.bar(M, (-hx, 0, H - 0.42), (hx, 0, H - 0.42), 0.03, IR, h=0.03, tile=0.5)
    n = 16
    for i in range(n + 1):
        x = -hx + 0.07 + (L - 0.14) * i / n
        gx.bar(M, (x, 0, 0.0), (x, 0, H - 0.1), 0.026, IR, h=0.026, tile=0.5, caps=False)
        # spear head
        gx.cone_pt(M, (x, 0, H - 0.1), 0.026, 0.115, IR) if hasattr(gx, 'cone_pt') else None
        M.poly([(x - 0.032, -0.012, H - 0.12), (x + 0.032, -0.012, H - 0.12), (x, 0, H + 0.02)], IR, hint=(0, -1, 0.3), tile=0.3)
        M.poly([(x + 0.032, 0.012, H - 0.12), (x - 0.032, 0.012, H - 0.12), (x, 0, H + 0.02)], IR, hint=(0, 1, 0.3), tile=0.3)
        M.poly([(x - 0.032, 0.012, H - 0.12), (x - 0.032, -0.012, H - 0.12), (x, 0, H + 0.02)], IR, hint=(-1, 0, 0.3), tile=0.3)
        M.poly([(x + 0.032, -0.012, H - 0.12), (x + 0.032, 0.012, H - 0.12), (x, 0, H + 0.02)], IR, hint=(1, 0, 0.3), tile=0.3)
        if i % 2 == 0 and 0 < i < n:
            gx.sphere(M, (x, 0, H - 0.27), 0.03, IR, 6, 3)
    # decorative rings between the rails
    for i in range(0, n, 4):
        x = -hx + 0.07 + (L - 0.14) * (i + 2) / n
        pts = [(x + 0.12 * np.cos(a), 0, 0.30 + 0.12 * np.sin(a)) for a in np.linspace(0, TAU, 13)]
        gx.tube(M, pts[::2] + [pts[0]], [0.012] * 8, 4, IR, tile=0.4, cap_end=False)
    C.box((-hx, -0.04, 0.0), (hx, 0.04, H))
    return M, C


@asset('pk_post', 'struct', dist=220)
def post():
    """stone fence post with cap and ball (every ~10 m along the iron fence)"""
    M, C = Mesh(), Col()
    S, GR = m('stone'), m('granite')
    M.box((-0.30, -0.30, -0.05), (0.30, 0.30, 0.32), S, tile=0.8)
    M.box((-0.24, -0.24, 0.32), (0.24, 0.24, 1.60), S, tile=0.8)
    M.box((-0.30, -0.30, 1.60), (0.30, 0.30, 1.72), GR, tile=0.8)
    M.cone((0, 0), 0.30, 1.72, 1.90, 4, GR, tile=0.8, theta0=np.pi / 4, r_top=0.12)
    gx.sphere(M, (0, 0, 2.02), 0.14, GR, 12, 7)
    C.box((-0.30, -0.30, 0.0), (0.30, 0.30, 2.1))
    return M, C


@asset('pk_picket', 'props')
def picket():
    """low wooden picket fence 2 m long (x -1..1), 0.85 high"""
    M, C = Mesh(), Col()
    W, WD = m('wood_light'), m('wood')
    gx.bar(M, (-1.0, 0.04, 0.22), (1.0, 0.04, 0.22), 0.07, WD, h=0.04, tile=0.6)
    gx.bar(M, (-1.0, 0.04, 0.60), (1.0, 0.04, 0.60), 0.07, WD, h=0.04, tile=0.6)
    for i in range(10):
        x = -0.90 + 0.2 * i
        M.box((x - 0.04, -0.02, 0.0), (x + 0.04, 0.02, 0.78), W, tile=0.6, skip=('+z',))
        M.poly([(x - 0.04, -0.02, 0.78), (x + 0.04, -0.02, 0.78), (x, -0.02, 0.86)], W, hint=(0, -1, 0), tile=0.6)
        M.poly([(x + 0.04, 0.02, 0.78), (x - 0.04, 0.02, 0.78), (x, 0.02, 0.86)], W, hint=(0, 1, 0), tile=0.6)
        M.poly([(x - 0.04, 0.02, 0.78), (x - 0.04, -0.02, 0.78), (x, -0.02, 0.86), (x, 0.02, 0.86)], W, hint=(-1, 0, 0.8), tile=0.6)
        M.poly([(x + 0.04, -0.02, 0.78), (x + 0.04, 0.02, 0.78), (x, 0.02, 0.86), (x, -0.02, 0.86)], W, hint=(1, 0, 0.8), tile=0.6)
    for sx in (-1, 1):
        M.box((sx * 0.98 - 0.05, -0.05, 0.0), (sx * 0.98 + 0.05, 0.08, 0.92), WD, tile=0.6)
    C.box((-1.0, -0.06, 0.0), (1.0, 0.09, 0.86))
    return M, C


# ------------------------------------------------------------------------------------------------- rocks
def rock_asset(seed, size, boxes):
    M, C = Mesh(), Col()
    gx.rock(M, (0, 0, size[2] * 0.62), size, m('granite'), seed, n=16, flat=0.75, tile=1.4)
    from .kit import bbox
    lo, hi = bbox(M)
    C.box((lo[0] * 0.8, lo[1] * 0.8, 0.0), (hi[0] * 0.8, hi[1] * 0.8, hi[2] * 0.82))
    return M, C


@asset('pk_rock1', 'props')
def rock1():
    return rock_asset(11, (0.55, 0.45, 0.42), [((-0.40, -0.32, 0.0), (0.40, 0.32, 0.38))])


@asset('pk_rock2', 'props')
def rock2():
    return rock_asset(23, (0.95, 0.75, 0.62), [((-0.70, -0.52, 0.0), (0.70, 0.52, 0.55))])


@asset('pk_rock3', 'props')
def rock3():
    return rock_asset(37, (1.55, 1.10, 0.95), [((-1.1, -0.75, 0.0), (1.1, 0.75, 0.85))])


# --------------------------------------------------------------------------------------------- misc props
@asset('pk_cone', 'props', dist=100)
def cone():
    M, C = Mesh(), Col()
    CN = m('cone')
    M.box((-0.20, -0.20, 0.0), (0.20, 0.20, 0.035), m('metal'), tile=0.5)
    gx.lathe(M, (0, 0), [(0.125, 0.035), (0.085, 0.40), (0.05, 0.62), (0.035, 0.70)], 20, CN, tile=0.72)
    M.cone((0, 0), 0.035, 0.70, 0.71, 20, CN, tile=0.72)
    C.box((-0.2, -0.2, 0.0), (0.2, 0.2, 0.72))
    return M, C


@asset('pk_crate', 'props', dist=100)
def crate():
    M, C = Mesh(), Col()
    W, WD = m('crate'), m('wooddark')
    M.box((-0.40, -0.40, 0.0), (0.40, 0.40, 0.80), W, tile=0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            M.box((sx * 0.40 - 0.04 if sx < 0 else 0.36, sy * 0.40 - 0.04 if sy < 0 else 0.36, -0.005),
                  (sx * 0.40 + 0.04 if sx > 0 else -0.36, sy * 0.40 + 0.04 if sy > 0 else -0.36, 0.805), WD, tile=0.5) if False else None
    for z in (0.04, 0.76):
        M.box((-0.42, -0.42, z - 0.04), (0.42, 0.42, z + 0.04), WD, tile=0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            M.box((sx * 0.38 - 0.045, sy * 0.38 - 0.045, 0.0), (sx * 0.38 + 0.045, sy * 0.38 + 0.045, 0.82), WD, tile=0.8)
    C.box((-0.42, -0.42, 0.0), (0.42, 0.42, 0.82))
    return M, C


@asset('pk_cabinet', 'props', dist=120)
def cabinet():
    M, C = Mesh(), Col()
    GN, MT, YL = m('paint_green'), m('metal'), m('paint_yellow')
    M.box((-0.45, -0.22, 0.0), (0.45, 0.22, 0.10), m('stone'), tile=0.8)
    M.box((-0.42, -0.20, 0.10), (0.42, 0.20, 1.20), GN, tile=0.8)
    M.box((-0.45, -0.23, 1.20), (0.45, 0.23, 1.26), GN, tile=0.8)
    for sx in (-1, 1):
        x = sx * 0.21
        gx.bar(M, (x, -0.212, 0.22), (x, -0.212, 1.08), 0.38, GN, h=0.012, tile=0.8)
        for k in range(10):
            z = 0.30 + 0.07 * k
            gx.bar(M, (x - 0.12, -0.225, z), (x + 0.12, -0.225, z), 0.012, MT, h=0.012, tile=0.4)
        gx.bar(M, (x - sx * 0.14, -0.222, 0.65), (x - sx * 0.14, -0.222, 0.80), 0.02, MT, h=0.02, tile=0.4)
    M.poly([(-0.10, -0.2125, 1.12), (0.10, -0.2125, 1.12), (0.10, -0.2125, 1.18), (-0.10, -0.2125, 1.18)], YL, hint=(0, -1, 0), tile=0.2)
    C.box((-0.45, -0.23, 0.0), (0.45, 0.23, 1.26))
    return M, C


@asset('pk_hydrant', 'props', dist=100)
def hydrant():
    M, C = Mesh(), Col()
    R, IR, MT = m('paint_red'), m('iron'), m('metal')
    gx.lathe(M, (0, 0), [(0.0, -0.02), (0.16, -0.02), (0.16, 0.05), (0.12, 0.09), (0.11, 0.55), (0.14, 0.58), (0.14, 0.62), (0.11, 0.65), (0.11, 0.70),
                         (0.13, 0.74), (0.12, 0.80), (0.07, 0.85), (0.0, 0.87)], 18, R, tile=0.6)
    gx.cyl(M, (-0.20, 0, 0.45), (0.20, 0, 0.45), 0.055, 0.055, 12, R, tile=0.5)
    for s in (-1, 1):
        gx.cyl(M, (s * 0.20, 0, 0.45), (s * 0.235, 0, 0.45), 0.065, 0.065, 12, MT, tile=0.3)
    gx.cyl(M, (0, -0.10, 0.50), (0, -0.20, 0.50), 0.07, 0.07, 12, R, tile=0.5)
    gx.cyl(M, (0, -0.20, 0.50), (0, -0.235, 0.50), 0.08, 0.08, 12, MT, tile=0.3)
    gx.cyl(M, (0, 0, 0.87), (0, 0, 0.92), 0.04, 0.04, 8, MT, tile=0.3)
    C.box((-0.25, -0.2, 0.0), (0.25, 0.2, 0.92))
    return M, C


@asset('pk_bikerack', 'props', dist=100)
def bikerack():
    M, C = Mesh(), Col()
    MT = m('metal')
    for i in range(4):
        x = -0.75 + 0.5 * i
        arc = [(x, 0.30 * np.cos(a_), 0.42 + 0.30 * np.sin(a_)) for a_ in np.linspace(0, np.pi, 11)]
        pts = [(x, 0.30, -0.02)] + arc + [(x, -0.30, -0.02)]
        gx.tube(M, pts, [0.022] * len(pts), 8, MT, tile=0.5, cap_end=True, cap_start=True)
    gx.bar(M, (-0.75, -0.30, 0.02), (0.75, -0.30, 0.02), 0.04, MT, h=0.03, tile=0.5)
    gx.bar(M, (-0.75, 0.30, 0.02), (0.75, 0.30, 0.02), 0.04, MT, h=0.03, tile=0.5)
    C.box((-0.80, -0.34, 0.0), (0.80, 0.34, 0.74))
    return M, C


@asset('pk_manhole', 'props', dist=90)
def manhole():
    M, C = Mesh(), Col()
    gx.disc(M, (0, 0), 0.40, 0.012, m('manhole'), n=32, tile=0.8, uvoff=(0.5, 0.5))
    C.box((-0.01, -0.01, 0.0), (0.01, 0.01, 0.012))
    return M, C


@asset('pk_stump', 'props', dist=110)
def stump():
    M, C = Mesh(), Col()
    BK = m('bark')
    gx.lathe(M, (0, 0), [(0.0, -0.05), (0.42, -0.05), (0.40, 0.08), (0.30, 0.22), (0.28, 0.40), (0.30, 0.46)], 18, BK, tile=0.9)
    gx.disc(M, (0, 0), 0.30, 0.46, m('wood_light'), n=18, tile=0.6, uvoff=(0.5, 0.5))
    C.box((-0.3, -0.3, 0.0), (0.3, 0.3, 0.47))
    return M, C


@asset('pk_log', 'props', dist=120)
def log():
    M, C = Mesh(), Col()
    BK = m('bark')
    pts = [(-1.5 + 0.375 * i, 0.06 * np.sin(i * 0.9), 0.0 + 0.24 + 0.02 * np.sin(i)) for i in range(9)]
    gx.tube(M, pts, [0.26 - 0.015 * i / 8 * 8 * 0.4 for i in range(9)], 12, BK, tile=1.0, cap_end=True, cap_start=True)
    gx.tube(M, [(0.1, 0.2, 0.38), (0.35, 0.45, 0.62), (0.45, 0.60, 0.80)], [0.07, 0.05, 0.03], 8, BK, tile=0.6)
    C.box((-1.5, -0.25, 0.0), (1.5, 0.25, 0.50))
    return M, C


@asset('pk_sandbox', 'props', dist=140)
def sandbox():
    M, C = Mesh(), Col()
    W, WD, SD = m('wood'), m('wooddark'), m('sand')
    S = 1.6
    M.poly([(-S, -S, 0.12), (S, -S, 0.12), (S, S, 0.12), (-S, S, 0.12)], SD, hint=(0, 0, 1), tile=1.2)
    for sx, sy, ex, ey in ((-S - 0.07, -S - 0.07, S + 0.07, -S + 0.07), (-S - 0.07, S - 0.07, S + 0.07, S + 0.07), (-S - 0.07, -S + 0.07, -S + 0.07, S - 0.07), (S - 0.07, -S + 0.07, S + 0.07, S - 0.07)):
        M.box((sx, sy, 0.0), (ex, ey, 0.30), W, tile=0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            M.box((sx * (S + 0.07) - 0.07, sy * (S + 0.07) - 0.07, 0.0), (sx * (S + 0.07) + 0.07, sy * (S + 0.07) + 0.07, 0.34), WD, tile=0.8)
    # toy bucket + sand mound
    gx.lathe(M, (0.7, 0.5), [(0.0, 0.12), (0.09, 0.12), (0.12, 0.30), (0.125, 0.31), (0.11, 0.31)], 14, m('paint_red'), tile=0.5)
    gx.lathe(M, (-0.5, -0.4), [(0.0, 0.12), (0.5, 0.12), (0.30, 0.20), (0.10, 0.30), (0.0, 0.31)], 18, SD, tile=1.0)
    for sx, sy, ex, ey in ((-S - 0.07, -S - 0.07, S + 0.07, -S + 0.07), (-S - 0.07, S - 0.07, S + 0.07, S + 0.07), (-S - 0.07, -S + 0.07, -S + 0.07, S - 0.07), (S - 0.07, -S + 0.07, S + 0.07, S - 0.07)):
        C.box((sx, sy, 0.0), (ex, ey, 0.34))
    return M, C


@asset('pk_duck', 'props', dist=120)
def duck():
    """mallard, swimming pose; origin on the water line"""
    M, C = Mesh(), Col()
    gx.sphere(M, (0, 0, 0.07), 0.13, m('duck'), 14, 8, sq=(1.0, 1.55, 0.78))
    gx.sphere(M, (0, 0.20, 0.17), 0.065, m('paint_green'), 10, 6, sq=(0.9, 1.0, 1.0))
    gx.cyl(M, (0, 0.17, 0.11), (0, 0.19, 0.17), 0.045, 0.04, 8, m('paint_green'), tile=0.3, caps=False)
    gx.bar(M, (0, 0.255, 0.165), (0, 0.31, 0.155), 0.04, m('paint_yellow'), h=0.016, tile=0.2)
    for s in (-1, 1):
        gx.sphere(M, (s * 0.045, 0.225, 0.195), 0.012, m('iron'), 6, 4)
    M.poly([(-0.07, -0.19, 0.09), (0.07, -0.19, 0.09), (0.0, -0.30, 0.15)], m('duck'), hint=(0, 0, 1), tile=0.3, double=True)
    C.box((-0.1, -0.2, 0.0), (0.1, 0.3, 0.2))
    return M, C
