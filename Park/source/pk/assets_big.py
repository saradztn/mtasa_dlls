# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# assets_big.py - park structures: fountain, gazebo, kiosk, playground (tower+slide, swings, merry-go-round),
#                 arched wooden bridge, entrance gate (pillar, arch with sign, animated leaf).
#                 Ground = z 0, one atomic per model, hand built collision.
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit, TAU
from . import gx
from .kit import asset, m, place, place_col, col_bar, bbox
from .assets_small import bench_geo, lantern

UP = np.array([0, 0, 1.0])


def ring_col(C, r, thick, z0, z1, n=16):
    for k in range(n):
        a0, a1 = TAU * k / n, TAU * (k + 1) / n
        C.strip((r * np.cos(a0), r * np.sin(a0)), (r * np.cos(a1), r * np.sin(a1)), thick, z0, z1)


# ---------------------------------------------------------------------------------------------- fountain
@asset('pk_fountain', 'struct', dist=250, day_glow=0.0)
def fountain():
    M, C = Mesh(), Col()
    S, GR, WT, SP = m('stone'), m('granite'), m('water'), m('spray')
    n = 40
    # basin: outer wall, coping, inner wall, floor
    gx.lathe(M, (0, 0), [(0.0, -0.1), (4.75, -0.1), (4.75, 0.45), (4.82, 0.50), (4.82, 0.62), (4.55, 0.66), (4.2, 0.66), (4.12, 0.58), (4.12, 0.40)], n, S, tile=1.2)
    gx.lathe(M, (0, 0), [(4.12, 0.40), (4.0, 0.34), (0.0, 0.34)], n, GR, tile=1.5)
    gx.lathe(M, (0, 0), [(4.82, 0.50), (4.82, 0.62)], n, GR, tile=1.0)
    # water surface of the basin (alpha)
    gx.disc(M, (0, 0), 4.05, 0.50, WT, n=n, tile=3.0)
    # pedestal and bowls
    gx.lathe(M, (0, 0), [(0.0, 0.34), (1.15, 0.34), (1.15, 0.55), (0.95, 0.62), (0.75, 0.95), (0.55, 1.15), (0.45, 1.30), (0.45, 1.50)], 24, S, tile=1.0)
    gx.lathe(M, (0, 0), [(0.45, 1.46), (0.9, 1.50), (1.8, 1.62), (2.35, 1.82), (2.45, 1.95), (2.38, 1.97), (2.25, 1.88), (1.7, 1.78), (0.0, 1.72)], 32, GR, tile=1.2)
    gx.lathe(M, (0, 0), [(0.0, 1.72), (0.0, 1.76)], 6, GR, tile=1.0)
    gx.disc(M, (0, 0), 2.18, 1.86, WT, n=32, tile=2.0)
    gx.lathe(M, (0, 0), [(0.0, 1.70), (0.40, 1.74), (0.40, 2.30), (0.30, 2.50), (0.26, 2.70)], 20, S, tile=1.0)
    gx.lathe(M, (0, 0), [(0.26, 2.66), (0.55, 2.72), (1.05, 2.86), (1.35, 3.04), (1.40, 3.12), (1.33, 3.14), (1.2, 3.04), (0.9, 2.94), (0.0, 2.88)], 28, GR, tile=1.0)
    gx.disc(M, (0, 0), 1.18, 3.02, WT, n=28, tile=1.5)
    gx.lathe(M, (0, 0), [(0.0, 2.88), (0.22, 2.95), (0.18, 3.35), (0.12, 3.55), (0.12, 3.75), (0.16, 3.82), (0.12, 3.9), (0.0, 4.15)], 14, S, tile=0.8)
    # water curtains (alpha, vertical streak texture)
    gx.lathe(M, (0, 0), [(1.35, 2.98), (1.55, 2.55), (1.62, 1.95)], 40, SP, tile=1.0, vscale=0.8)
    gx.lathe(M, (0, 0), [(2.42, 1.90), (2.62, 1.2), (2.70, 0.52)], 48, SP, tile=1.4, vscale=0.8)
    for k in range(2):      # rising jet (two crossed cards) and a ring of small arcs
        a = k * np.pi / 2
        d = np.array([np.cos(a), np.sin(a), 0.0])
        gx.card(M, (0, 0, 4.6), d * 0.38, UP * 0.65, SP, d, (0.2, 0.0, 0.8, 1.0))
    for k in range(10):
        a = TAU * k / 10
        d = np.array([np.cos(a), np.sin(a), 0.0])
        pts = [d * 0.2 + UP * 3.3, d * 0.9 + UP * 3.6, d * 1.5 + UP * 3.2, d * 1.9 + UP * 2.4]
    # collision
    ring_col(C, 4.45, 0.7, 0.0, 0.66, 20)
    for k in range(6):
        a = np.pi * k / 6
        d = np.array([np.cos(a), np.sin(a)]) * 4.1
        C.strip(-d, d, 2.4, 0.0, 0.36)
    C.box((-1.05, -1.05, 0.0), (1.05, 1.05, 1.0))
    ring_col(C, 1.9, 1.5, 1.0, 1.9, 8)
    C.box((-0.45, -0.45, 1.0), (0.45, 0.45, 3.2))
    return M, C, (lambda P, N: np.where(P[:, 2] > 0.45, 1.0, 0.82))


# -------------------------------------------------------------------------------------------------- gazebo
@asset('pk_gazebo', 'struct', dist=260, day_glow=0.0)
def gazebo():
    """hexagonal gazebo, entrance on the -y side, floor 0.30 above the ground"""
    M, C = Mesh(), Col()
    W, WL, WD, IR, SH, S = m('wood'), m('wood_light'), m('wooddark'), m('iron'), m('shingle'), m('stone')
    PAINT = m('plaster')
    R, ZF, ZP, ZR = 2.55, 0.32, 2.85, 2.95
    th = np.arange(6) * TAU / 6
    V = [np.array([R * np.cos(a), R * np.sin(a)]) for a in th]
    # floor: stone skirt + wooden deck
    M.prism((0, 0), 3.05, -0.1, ZF, 6, S, tile=1.2, cap_top=False, ex=1, ey=1)
    for k in range(6):
        a = np.array([3.05 * np.cos(th[k]), 3.05 * np.sin(th[k])])
        b = np.array([3.05 * np.cos(th[(k + 1) % 6]), 3.05 * np.sin(th[(k + 1) % 6])])
        M.poly([(0, 0, ZF), (b[0], b[1], ZF), (a[0], a[1], ZF)], WL, hint=(0, 0, 1), uv=[(0, 0), (b[0] / 1.2, b[1] / 1.2), (a[0] / 1.2, a[1] / 1.2)])
    # steps at the -y side (between vertices 4 and 5 -> angles 240, 300)
    for i in range(2):
        z = ZF - 0.16 * i - 0.16
        M.box((-1.2, -3.05 - 0.42 * (i + 1), -0.1), (1.2, -3.0 - 0.42 * i, z + 0.16), S, tile=0.8)
        C.box((-1.2, -3.05 - 0.42 * (i + 1), 0.0), (1.2, -2.6, z + 0.16))
    # posts, beams, rails
    for k in range(6):
        p = V[k]
        M.box((p[0] - 0.09, p[1] - 0.09, ZF), (p[0] + 0.09, p[1] + 0.09, ZP), PAINT, tile=0.6)
        M.box((p[0] - 0.13, p[1] - 0.13, ZF), (p[0] + 0.13, p[1] + 0.13, ZF + 0.18), WD, tile=0.6)
        C.box((p[0] - 0.1, p[1] - 0.1, 0.0), (p[0] + 0.1, p[1] + 0.1, ZP))
    for k in range(6):
        a, b = V[k], V[(k + 1) % 6]
        mid = (a + b) / 2
        entr = (k == 4)
        gx.bar(M, (a[0], a[1], ZP - 0.10), (b[0], b[1], ZP - 0.10), 0.20, WD, h=0.22, tile=0.8)
        gx.bar(M, (a[0], a[1], ZP - 0.34), (b[0], b[1], ZP - 0.34), 0.05, WD, h=0.14, tile=0.8)
        # diagonal brackets at both post tops
        for s_, pa in ((1, a), (-1, b)):
            d = unit(np.append((b - a) * s_, 0))
            gx.bar(M, (pa[0], pa[1], ZP - 0.65), (pa[0] + d[0] * 0.55, pa[1] + d[1] * 0.55, ZP - 0.15), 0.05, WD, h=0.08, tile=0.8)
        if entr:
            continue
        gx.bar(M, (a[0], a[1], ZF + 1.0), (b[0], b[1], ZF + 1.0), 0.09, WL, h=0.06, tile=0.8)
        gx.bar(M, (a[0], a[1], ZF + 0.12), (b[0], b[1], ZF + 0.12), 0.07, WD, h=0.05, tile=0.8)
        L = np.linalg.norm(b - a)
        nb = int(L / 0.20)
        for j in range(1, nb):
            q = a + (b - a) * j / nb
            gx.bar(M, (q[0], q[1], ZF + 0.14), (q[0], q[1], ZF + 1.0), 0.035, WL, tile=0.8, caps=False)
        C.strip(a, b, 0.14, 0.0, ZF + 1.05)
    # benches inside the rails
    for k in range(6):
        if k in (4,):
            continue
        a, b = V[k], V[(k + 1) % 6]
        mid = (a + b) / 2
        ang = np.degrees(np.arctan2(mid[1], mid[0])) + 90
        inner = mid * (1 - 0.34 / np.linalg.norm(mid))
        sub, subc = Mesh(), Col()
        bench_geo(sub, subc, L=1.8)
        place(M, sub, (inner[0], inner[1], ZF), ang + 180)
        place_col(C, subc, (inner[0], inner[1], ZF), ang + 180)
    C.prisms.append(np.array([(-2.6, -2.2, 0.0), (2.6, -2.2, 0.0), (2.6, 2.2, 0.0), (-2.6, 2.2, 0.0), (-2.6, -2.2, ZF), (2.6, -2.2, ZF), (2.6, 2.2, ZF), (-2.6, 2.2, ZF)]))
    C.box((-1.3, -2.6, 0.0), (1.3, -2.1, ZF))
    for k in range(3):
        a = k * np.pi / 3
        d = np.array([np.cos(a), np.sin(a)]) * 3.0
        C.strip(-d, d, 1.7, 0.0, ZF)
    # roof: hexagonal hip roof with fascia, underside, finial
    RR, RZ = 3.55, 4.9
    for k in range(6):
        a = np.array([RR * np.cos(th[k]), RR * np.sin(th[k]), ZR])
        b = np.array([RR * np.cos(th[(k + 1) % 6]), RR * np.sin(th[(k + 1) % 6]), ZR])
        ap = np.array([0, 0, RZ])
        mid = (a + b) / 2
        # two rows of shingle courses via uv scale; slight curve: a lower kink
        k1 = 0.55
        a1, b1 = a * k1 + ap * (1 - k1) + UP * 0.0, b * k1 + ap * (1 - k1)
        a1[2] = ZR + (RZ - ZR) * 0.50
        b1[2] = a1[2]
        L = np.linalg.norm(b - a)
        slant = np.linalg.norm(ap - mid)
        M.poly([a, b, b1, a1], SH, hint=(mid[0], mid[1], 1.2), uv=[(0, 0), (L / 0.9, 0), (L * k1 / 0.9, -slant * 0.5 / 0.9), (L * k1 / 0.9, -slant * 0.5 / 0.9)][:0] or [(0, 0), (L / 0.9, 0), (L * 0.7 / 0.9, -1.2), (L * 0.3 / 0.9, -1.2)])
        M.poly([a1, b1, ap], SH, hint=(mid[0], mid[1], 1.5), uv=[(0, 0), (L * k1 / 0.9, 0), (L * k1 / 1.8, -1.6)])
        # underside ceiling
        M.poly([(a[0], a[1], ZR - 0.02), (0, 0, RZ - 0.35), (b[0], b[1], ZR - 0.02)], WL, hint=(0, 0, -1), tile=1.0)
        # fascia board
        M.poly([(a[0], a[1], ZR - 0.14), (b[0], b[1], ZR - 0.14), (b[0], b[1], ZR), (a[0], a[1], ZR)], WD, hint=(mid[0], mid[1], 0), tile=0.8)
        # hip ribs
        gx.bar(M, (a[0], a[1], ZR + 0.02), (a1[0], a1[1], a1[2]), 0.08, WD, h=0.05, tile=0.8)
        gx.bar(M, (a1[0], a1[1], a1[2]), (0, 0, RZ), 0.07, WD, h=0.05, tile=0.8)
    gx.lathe(M, (0, 0), [(0.0, RZ - 0.05), (0.16, RZ - 0.05), (0.14, RZ + 0.10), (0.06, RZ + 0.25), (0.08, RZ + 0.32), (0.05, RZ + 0.48), (0.0, RZ + 0.75)], 12, IR, tile=0.5)
    gx.sphere(M, (0, 0, RZ + 0.30), 0.11, IR, 8, 5)
    # hanging lantern
    gx.cyl(M, (0, 0, RZ - 0.4), (0, 0, ZP - 0.6), 0.012, 0.012, 5, IR, tile=0.3, caps=False)
    lantern_sub = Mesh()
    lantern(lantern_sub, 0.0, IR)
    place(M, lantern_sub, (0, 0, ZP - 1.35), 0, 0.55)

    def ao(P, N):
        return np.where(P[:, 2] > ZR - 0.3, 0.92, 1.0) * (0.86 + 0.14 * np.clip(P[:, 2] / 1.0, 0, 1))
    return M, C, ao


# ---------------------------------------------------------------------------------------------------- kiosk
@asset('pk_kiosk', 'struct', dist=240, day_glow=0.0)
def kiosk():
    """snack kiosk 3.6 x 2.6 m, serving window and striped awning at the -y side"""
    M, C = Mesh(), Col()
    PL, S, WD, WL, SH, AW, GL = m('plaster'), m('stone'), m('wooddark'), m('wood_light'), m('shingle'), m('awning'), m('glass')
    hx, hy, t = 1.8, 1.3, 0.16
    zp, zt = 0.25, 2.75
    M.box((-hx - 0.1, -hy - 0.1, -0.1), (hx + 0.1, hy + 0.1, zp), S, tile=0.8)
    C.box((-hx - 0.1, -hy - 0.1, 0.0), (hx + 0.1, hy + 0.1, zp))
    # walls
    M.box((-hx, hy - t, zp), (hx, hy, zt), PL, tile=1.2, skip=('-z',))
    M.box((-hx, -hy, zp), (-hx + t, hy, zt), PL, tile=1.2, skip=('-z',))
    M.box((hx - t, -hy, zp), (hx, hy, zt), PL, tile=1.2, skip=('-z',))
    wx = 1.15
    M.box((-hx, -hy, zp), (-wx, -hy + t, zt), PL, tile=1.2, skip=('-z',))
    M.box((wx, -hy, zp), (hx, -hy + t, zt), PL, tile=1.2, skip=('-z',))
    M.box((-wx, -hy, zp), (wx, -hy + t, 1.0), PL, tile=1.2, skip=('-z',))
    M.box((-wx, -hy, 2.0), (wx, -hy + t, zt), PL, tile=1.2, skip=('-z',))
    # window reveal frames
    gx.bar(M, (-wx, -hy - 0.02, 1.0), (wx, -hy - 0.02, 1.0), 0.20, WD, h=0.05, tile=0.8)
    for sx in (-1, 1):
        gx.bar(M, (sx * wx, -hy - 0.02, 1.0), (sx * wx, -hy - 0.02, 2.0), 0.08, WD, h=0.05, tile=0.8)
    # counter
    M.box((-wx - 0.05, -hy - 0.40, 0.96), (wx + 0.05, -hy + 0.02, 1.02), WL, tile=0.8)
    M.box((-wx - 0.02, -hy - 0.38, 0.30), (wx + 0.02, -hy - 0.02, 0.96), WD, tile=0.8)
    # floor / ceiling / inner shelves
    M.poly([(-hx + t, -hy + t, zp + 0.02), (hx - t, -hy + t, zp + 0.02), (hx - t, hy - t, zp + 0.02), (-hx + t, hy - t, zp + 0.02)], WL, hint=(0, 0, 1), tile=1.0)
    M.poly([(-hx + t, -hy + t, zt - 0.02), (-hx + t, hy - t, zt - 0.02), (hx - t, hy - t, zt - 0.02), (hx - t, -hy + t, zt - 0.02)], WL, hint=(0, 0, -1), tile=1.0)
    rng = np.random.default_rng(5)
    bottle = [m('paint_red'), m('paint_yellow'), m('paint_blue'), m('paint_green')]
    for z in (1.15, 1.55):
        M.box((-hx + t, hy - t - 0.3, z), (hx - t, hy - t, z + 0.04), WL, tile=0.8)
        x = -hx + t + 0.15
        while x < hx - t - 0.1:
            hgt = rng.uniform(0.15, 0.28)
            gx.cyl(M, (x, hy - t - 0.14, z + 0.04), (x, hy - t - 0.14, z + 0.04 + hgt), 0.04, 0.04, 8, bottle[rng.integers(4)], tile=0.3)
            x += rng.uniform(0.10, 0.2)
    # side windows (glass, lit at night)
    for sx in (-1, 1):
        x = sx * (hx + 0.004)
        M.poly([(x, -0.4, 1.2), (x, 0.4, 1.2), (x, 0.4, 2.1), (x, -0.4, 2.1)][::sx], GL, hint=(sx, 0, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)], emis=0.6)
        for q in (-0.45, 0.45):
            gx.bar(M, (x + sx * 0.02, q, 1.15), (x + sx * 0.02, q, 2.15), 0.06, WD, h=0.04, tile=0.8)
        gx.bar(M, (x + sx * 0.02, -0.45, 1.15), (x + sx * 0.02, 0.45, 1.15), 0.06, WD, h=0.05, tile=0.8)
        gx.bar(M, (x + sx * 0.02, -0.45, 2.15), (x + sx * 0.02, 0.45, 2.15), 0.06, WD, h=0.05, tile=0.8)
    # hip roof
    ex, ey, rt = hx + 0.55, hy + 0.55, 3.55
    tx, ty = 0.9, 0.35
    top = [(-tx, -ty, rt), (tx, -ty, rt), (tx, ty, rt), (-tx, ty, rt)]
    eave = [(-ex, -ey, zt), (ex, -ey, zt), (ex, ey, zt), (-ex, ey, zt)]
    M.poly([eave[0], eave[1], top[1], top[0]], SH, hint=(0, -1, 1), uv=[(0, 0), (ex * 2 / 0.9, 0), (tx * 2 / 0.9, -1.4), (0, -1.4)] if False else None, tile=0.9)
    M.poly([eave[2], eave[3], top[3], top[2]], SH, hint=(0, 1, 1), tile=0.9)
    M.poly([eave[1], eave[2], top[2], top[1]], SH, hint=(1, 0, 1), tile=0.9)
    M.poly([eave[3], eave[0], top[0], top[3]], SH, hint=(-1, 0, 1), tile=0.9)
    M.poly(top, SH, hint=(0, 0, 1), tile=0.9)
    for i in range(4):
        a, b = eave[i], eave[(i + 1) % 4]
        mid = np.array([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0])
        M.poly([(a[0], a[1], zt - 0.16), (b[0], b[1], zt - 0.16), (b[0], b[1], zt), (a[0], a[1], zt)], WD, hint=(mid[0], mid[1], 0), tile=0.8)
        gx.bar(M, eave[i], top[i], 0.09, WD, h=0.05, tile=0.8)
    M.poly([(-ex, -ey, zt - 0.02), (-ex, ey, zt - 0.02), (ex, ey, zt - 0.02), (ex, -ey, zt - 0.02)], WL, hint=(0, 0, -1), tile=1.0)
    # vent cupola
    M.box((-0.25, -0.2, rt), (0.25, 0.2, rt + 0.28), WD, tile=0.6)
    M.poly([(-0.32, -0.27, rt + 0.28), (0.32, -0.27, rt + 0.28), (0.1, -0.05, rt + 0.45), (-0.1, -0.05, rt + 0.45)], SH, hint=(0, -1, 1), tile=0.5)
    M.poly([(0.32, 0.27, rt + 0.28), (-0.32, 0.27, rt + 0.28), (-0.1, 0.05, rt + 0.45), (0.1, 0.05, rt + 0.45)], SH, hint=(0, 1, 1), tile=0.5)
    # sign board on the lintel + striped awning
    M.poly([(-1.05, -hy - 0.015, 2.12), (1.05, -hy - 0.015, 2.12), (1.05, -hy - 0.015, 2.62), (-1.05, -hy - 0.015, 2.62)], m('sign_kiosk'), hint=(0, -1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    gx.bar(M, (-1.08, -hy - 0.02, 2.65), (1.08, -hy - 0.02, 2.65), 0.06, WD, h=0.04, tile=0.6)
    gx.bar(M, (-1.08, -hy - 0.02, 2.09), (1.08, -hy - 0.02, 2.09), 0.06, WD, h=0.04, tile=0.6)
    ax = 1.55
    a0, a1 = (-ax, -hy - 0.04, 2.04), (-ax, -hy - 1.0, 1.72)
    M.poly([(-ax, -hy - 0.04, 2.04), (ax, -hy - 0.04, 2.04), (ax, -hy - 1.0, 1.72), (-ax, -hy - 1.0, 1.72)], AW, hint=(0, -0.4, 1), uv=[(0, 0), (2 * ax / 1.6, 0), (2 * ax / 1.6, 0.9), (0, 0.9)])
    M.poly([(-ax, -hy - 1.0, 1.72), (ax, -hy - 1.0, 1.72), (ax, -hy - 1.0, 1.52), (-ax, -hy - 1.0, 1.52)], AW, hint=(0, -1, -0.2), uv=[(0, 0.9), (2 * ax / 1.6, 0.9), (2 * ax / 1.6, 1.0), (0, 1.0)])
    for sx in (-1, 1):
        M.poly([(sx * ax, -hy - 0.04, 2.04), (sx * ax, -hy - 1.0, 1.72), (sx * ax, -hy - 1.0, 1.52)], AW, hint=(sx, 0, 0), uv=[(0, 0), (0, 0.9), (0, 1.0)])
    # collision: walls, counter, roof slab kept out so players never bump on the awning
    C.box((-hx, hy - t, 0.0), (hx, hy, zt))
    C.box((-hx, -hy, 0.0), (-hx + t, hy, zt))
    C.box((hx - t, -hy, 0.0), (hx, hy, zt))
    C.box((-hx, -hy, 0.0), (-wx, -hy + t, zt))
    C.box((wx, -hy, 0.0), (hx, -hy + t, zt))
    C.box((-wx, -hy - 0.4, 0.0), (wx, -hy + t, 1.02))
    C.box((-wx, -hy, 2.0), (wx, -hy + t, zt))
    C.box((-hx, -hy, zp), (hx, hy, zp + 0.05))

    def ao(P, N):
        return np.where(P[:, 2] > 2.7, 1.0, 0.84 + 0.16 * np.clip((P[:, 2] - 0.1) / 1.2, 0, 1))
    return M, C, ao


# ----------------------------------------------------------------------------------------------- playground
@asset('pk_slide', 'struct', dist=220, day_glow=0.0)
def slide():
    """play tower 1.7 m platform with roof, ladder (-x side) and slide towards +y"""
    M, C = Mesh(), Col()
    RD, YL, BL, WL, WD, MT, GN = m('paint_red'), m('paint_yellow'), m('paint_blue'), m('wood_light'), m('wooddark'), m('metal'), m('paint_green')
    H, hs = 1.55, 0.85
    # deck
    M.box((-hs, -hs, H - 0.10), (hs, hs, H), WL, tile=0.8)
    M.box((-hs - 0.04, -hs - 0.04, H - 0.16), (hs + 0.04, hs + 0.04, H - 0.10), WD, tile=0.8, skip=('-z',))
    C.box((-hs, -hs, H - 0.16), (hs, hs, H))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = (sx * (hs - 0.05), sy * (hs - 0.05))
            M.box((p[0] - 0.07, p[1] - 0.07, 0.0), (p[0] + 0.07, p[1] + 0.07, 2.95), RD, tile=0.6)
            C.box((p[0] - 0.07, p[1] - 0.07, 0.0), (p[0] + 0.07, p[1] + 0.07, H))
    # railings: -y, +x and the sides next to the openings; opening at +y (slide) and -x (ladder)
    def rail(a, b, z0=H, h=0.80):
        gx.bar(M, (a[0], a[1], z0 + h), (b[0], b[1], z0 + h), 0.07, YL, h=0.05, tile=0.6)
        gx.bar(M, (a[0], a[1], z0 + 0.12), (b[0], b[1], z0 + 0.12), 0.05, YL, h=0.04, tile=0.6)
        L = np.linalg.norm(np.array(b) - np.array(a))
        k = max(2, int(L / 0.14))
        for j in range(1, k):
            q = np.array(a) + (np.array(b) - np.array(a)) * j / k
            gx.bar(M, (q[0], q[1], z0 + 0.12), (q[0], q[1], z0 + h), 0.03, YL, tile=0.6, caps=False)
        C.strip(a, b, 0.08, z0, z0 + h + 0.05)
    c = hs - 0.05
    rail((-c, -c), (c, -c))
    rail((c, -c), (c, c))
    rail((-c, -c), (-c, -0.30))
    rail((-c, 0.30), (-c, c))
    rail((-c, c), (-0.30, c))
    rail((0.30, c), (c, c))
    # roof: blue pyramid with trim
    M.cone((0, 0), 1.45, 2.95, 3.85, 4, BL, tile=0.8, theta0=np.pi / 4)
    for i in range(4):
        a = np.pi / 4 + i * np.pi / 2
        gx.bar(M, (1.45 * np.cos(a), 1.45 * np.sin(a), 2.97), (0, 0, 3.85), 0.07, YL, h=0.05, tile=0.6)
    M.poly([(1.45 * np.cos(np.pi / 4 + i * np.pi / 2), 1.45 * np.sin(np.pi / 4 + i * np.pi / 2), 2.93) for i in range(4)][::-1], WD, hint=(0, 0, -1), tile=1.0)
    gx.sphere(M, (0, 0, 3.92), 0.10, RD, 8, 5)
    # ladder on -x side (leaning)
    for sy in (-1, 1):
        gx.bar(M, (-hs - 0.6, sy * 0.28, 0.0), (-hs - 0.04, sy * 0.28, H), 0.06, MT, h=0.04, tile=0.6)
    for k in range(1, 6):
        t_ = k / 6
        x = -hs - 0.6 + 0.56 * t_
        gx.bar(M, (x, -0.28, H * t_), (x, 0.28, H * t_), 0.05, YL, h=0.05, tile=0.5)
    col_bar(C, (-hs - 0.6, 0, 0.05), (-hs - 0.04, 0, H), 0.6, 0.06)
    # slide: curved chute from (y=hs, z=H) to (y=hs+3.2, z=0.14)
    pts = []
    for i in range(15):
        t_ = i / 14
        y = hs + 3.3 * t_
        z = H * (1 - t_) ** 1.55 + 0.14 + 0.0
        pts.append((0.0, y, z))
    for i in range(14):
        a, b = np.array(pts[i]), np.array(pts[i + 1])
        gx.bar(M, a - UP * 0.02, b - UP * 0.02, 0.62, BL, h=0.045, tile=0.7)
        for sx in (-1, 1):
            gx.bar(M, a + np.array([sx * 0.31, 0, 0.07]), b + np.array([sx * 0.31, 0, 0.07]), 0.045, YL, h=0.17, tile=0.6)
        col_bar(C, a, b, 0.66, 0.1)
    for sx in (-1, 1):
        for i in (3, 7, 11):
            q = np.array(pts[i])
            gx.bar(M, q + np.array([sx * 0.28, 0, -0.03]), (sx * 0.30, q[1], 0.0), 0.04, MT, tile=0.5)
    gx.bar(M, (-0.32, hs - 0.02, H + 0.45), (-0.32, hs - 0.02, H), 0.04, YL, tile=0.5)
    # slide hand bars
    for sx in (-1, 1):
        gx.bar(M, (sx * 0.34, hs + 0.05, H + 0.05), (sx * 0.34, hs + 0.05, H + 0.70), 0.04, MT, tile=0.5)
    gx.bar(M, (-0.34, hs + 0.05, H + 0.70), (0.34, hs + 0.05, H + 0.70), 0.04, MT, tile=0.5)
    return M, C, (lambda P, N: np.clip(0.80 + 0.20 * P[:, 2] / 1.5, 0, 1))


@asset('pk_swingset', 'struct', dist=220, day_glow=0.0)
def swingset():
    """A-frame swing set (top bar at z=2.45 along x, width 4.2); the two seats are separate animated objects"""
    M, C = Mesh(), Col()
    MT, RD = m('metal'), m('paint_red')
    H = 2.45
    for sx in (-1, 1):
        x = sx * 2.0
        for sy in (-1, 1):
            gx.tube(M, [(x, sy * 1.0, -0.05), (x, 0, H)], [0.055, 0.05], 8, RD, tile=0.5, cap_end=True, cap_start=True)
            gx.lathe(M, (x, sy * 1.0), [(0.0, -0.05), (0.13, -0.05), (0.13, 0.04), (0.06, 0.06)], 8, MT, tile=0.4)
        gx.lathe(M, (x, 0.0), [(0.0, H - 0.1), (0.075, H - 0.1), (0.075, H + 0.08), (0.0, H + 0.08)], 8, MT, tile=0.4)
    gx.tube(M, [(-2.15, 0, H), (2.15, 0, H)], [0.055, 0.055], 10, RD, tile=0.5, cap_end=True, cap_start=True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            col_bar(C, (sx * 2.0 - 0.05 * 0, sy * 1.0, 0.0), (sx * 2.0, 0.0, H), 0.12, 0.12)
    C.box((-2.1, -0.06, H - 0.07), (2.1, 0.06, H + 0.07))
    return M, C, (lambda P, N: np.clip(0.80 + 0.20 * P[:, 2] / 1.5, 0, 1))


@asset('pk_swing', 'struct', dist=150, day_glow=0.0)
def swing():
    """one swing: origin at the pivot (top bar), seat 2.05 m below; swings about the x axis"""
    M, C = Mesh(), Col()
    MT, WD, BK, RB = m('metal'), m('wood'), m('wooddark'), m('rubber_blue')
    D = 2.05
    for sx in (-1, 1):
        x = sx * 0.24
        pts = [(x, 0, -0.06 - 0.1 * k) for k in range(0, int(D * 10) - 3)]
        gx.tube(M, [(x, 0, -0.06), (x, 0, -D + 0.06)], [0.012, 0.012], 5, MT, tile=0.2, cap_end=True)
        for k in range(0, 19):
            z = -0.14 - 0.1 * k
            gx.sphere(M, (x, 0, z), 0.017, MT, 5, 3)
        gx.sphere(M, (x, 0, -0.04), 0.03, MT, 6, 4)
    gx.bar(M, (-0.30, 0, -D), (0.30, 0, -D), 0.20, RB, h=0.045, tile=0.5)
    gx.bar(M, (-0.28, 0, -D - 0.015), (0.28, 0, -D - 0.015), 0.22, BK, h=0.02, tile=0.5)
    C.box((-0.001, -0.001, -D), (0.001, 0.001, -D + 0.002))
    return M, C


@asset('pk_merry', 'struct', dist=180, day_glow=0.0)
def merry():
    """merry-go-round, 2.4 m wide platform with four painted pairs of sectors; spins about its origin"""
    M, C = Mesh(), Col()
    mats = [m('paint_red'), m('paint_yellow'), m('paint_blue'), m('paint_green')]
    MT = m('metal')
    n = 8
    R, Z = 1.2, 0.46
    gx.cyl(M, (0, 0, 0.0), (0, 0, Z), 0.12, 0.10, 10, MT, tile=0.5)
    for k in range(n):
        a0, a1 = TAU * k / n, TAU * (k + 1) / n
        p0, p1 = (R * np.cos(a0), R * np.sin(a0)), (R * np.cos(a1), R * np.sin(a1))
        M.poly([(0, 0, Z), (p0[0], p0[1], Z), (p1[0], p1[1], Z)][::1], mats[k % 4], hint=(0, 0, 1), uv=[(0.5, 0.5), (0.5 + 0.5 * np.cos(a0), 0.5 + 0.5 * np.sin(a0)), (0.5 + 0.5 * np.cos(a1), 0.5 + 0.5 * np.sin(a1))])
        M.poly([(p0[0], p0[1], Z), (p0[0] * 1.0, p0[1] * 1.0, Z - 0.08), (p1[0], p1[1], Z - 0.08), (p1[0], p1[1], Z)], MT, hint=(p0[0] + p1[0], p0[1] + p1[1], 0), tile=0.5)
        M.poly([(0, 0, Z - 0.08), (p1[0], p1[1], Z - 0.08), (p0[0], p0[1], Z - 0.08)], MT, hint=(0, 0, -1), tile=1.0)
    for k in range(4):
        a = TAU * k / 4 + np.pi / 4
        c, s = np.cos(a), np.sin(a)
        pts = [(0.0, 0.0, Z + 0.02), (0.0, 0.0, Z + 0.55)] + [(0.75 * (1 - np.cos(t_)) * c * 0.5 + 0, 0, 0) for t_ in []]
        gx.tube(M, [(0.35 * c, 0.35 * s, Z), (0.35 * c, 0.35 * s, Z + 0.75), (0.15 * c, 0.15 * s, Z + 0.95), (0.0, 0.0, Z + 0.98)], [0.025] * 4, 8, MT, tile=0.4, cap_end=True)
    gx.tube(M, [(0, 0, Z), (0, 0, Z + 0.98)], [0.04, 0.04], 10, MT, tile=0.4, cap_end=True)
    gx.sphere(M, (0, 0, Z + 1.0), 0.07, mats[0], 8, 5)
    ring_col(C, 1.1, 0.6, 0.0, Z, 8)
    C.box((-0.7, -0.7, 0.0), (0.7, 0.7, Z))
    return M, C, (lambda P, N: np.clip(0.78 + 0.22 * P[:, 2] / 0.5, 0, 1))


# ------------------------------------------------------------------------------------------------- bridge
@asset('pk_bridge', 'struct', dist=250, day_glow=0.0)
def bridge():
    """arched wooden footbridge along the y axis: 14 m long (y -7..7), 2.6 m wide, rise 1.15 m, ends at z=0"""
    M, C = Mesh(), Col()
    WL, WD, W, S, GR, IR = m('wood_light'), m('wooddark'), m('wood'), m('stone'), m('granite'), m('iron')
    Lh, Wd, RISE = 7.0, 2.6, 1.15
    hw = Wd / 2

    def zf(y):
        return RISE * (1 - (y / Lh) ** 2)

    ns = 28
    ys = np.linspace(-Lh, Lh, ns + 1)
    # deck planks (across), slightly gapped
    for i in range(ns):
        y0, y1 = ys[i], ys[i + 1]
        z0, z1 = zf(y0), zf(y1)
        for k in range(2):
            ya = y0 + (y1 - y0) * k / 2 + 0.01
            yb = y0 + (y1 - y0) * (k + 1) / 2 - 0.01
            za, zb = zf(ya), zf(yb)
            P = [(-hw, ya, za), (hw, ya, za), (hw, yb, zb), (-hw, yb, zb)]
            M.poly(P, WL, hint=(0, 0, 1), uv=[(0, 0), (hw * 2 / 2.0, 0), (hw * 2 / 2.0, 0.22), (0, 0.22)])
            # thickness front
            M.poly([(-hw, ya, za - 0.07), (hw, ya, za - 0.07), (hw, ya, za), (-hw, ya, za)], WD, hint=(0, -1, 0), tile=0.6)
        col_bar(C, (0, y0, z0 - 0.04), (0, y1, z1 - 0.04), Wd, 0.14)
    # side stringers (curved beams below deck) and fascia
    for sx in (-1, 1):
        for i in range(ns):
            a, b = np.array([sx * (hw - 0.05), ys[i], zf(ys[i]) - 0.24]), np.array([sx * (hw - 0.05), ys[i + 1], zf(ys[i + 1]) - 0.24])
            gx.bar(M, a, b, 0.20, WD, h=0.30, tile=0.8)
    # three cross beams under the deck
    for y in (-4.5, -1.5, 1.5, 4.5):
        gx.bar(M, (-hw, y, zf(y) - 0.12), (hw, y, zf(y) - 0.12), 0.16, WD, h=0.16, tile=0.8)
    # railings
    pts_rail = {}
    for sx in (-1, 1):
        x = sx * (hw - 0.10)
        post_y = np.linspace(-Lh + 0.2, Lh - 0.2, 15)
        for y in post_y:
            gx.bar(M, (x, y, zf(y)), (x, y, zf(y) + 1.05), 0.12, W, tile=0.8)
            M.box((x - 0.075, y - 0.075, zf(y) + 1.05), (x + 0.075, y + 0.075, zf(y) + 1.09), WL, tile=0.6)
        top = [(x, y, zf(y) + 1.00) for y in np.linspace(-Lh + 0.2, Lh - 0.2, 29)]
        mid = [(x, y, zf(y) + 0.52) for y in np.linspace(-Lh + 0.2, Lh - 0.2, 29)]
        for a, b in zip(top[:-1], top[1:]):
            gx.bar(M, a, b, 0.12, WL, h=0.07, tile=0.8)
        for a, b in zip(mid[:-1], mid[1:]):
            gx.bar(M, a, b, 0.07, W, h=0.05, tile=0.8)
        for y in np.linspace(-Lh + 0.5, Lh - 0.5, 28):
            gx.bar(M, (x, y, zf(y) + 0.08), (x, y, zf(y) + 1.0), 0.04, W, tile=0.6, caps=False)
        for i in range(0, 28, 1):
            ya, yb = -Lh + 0.2 + (2 * Lh - 0.4) * i / 28, -Lh + 0.2 + (2 * Lh - 0.4) * (i + 1) / 28
            col_bar(C, (x, ya, zf(ya) + 0.55), (x, yb, zf(yb) + 0.55), 0.14, 1.0)
    # stone abutments at both ends
    for sy in (-1, 1):
        M.box((-hw - 0.45, sy * (Lh + 0.35) - 0.55 + (0 if sy > 0 else 0), -0.8), (hw + 0.45, sy * (Lh + 0.35) + 0.55, 0.0), S, tile=0.9)
        C.box((-hw - 0.45, sy * (Lh + 0.35) - 0.55, -0.8), (hw + 0.45, sy * (Lh + 0.35) + 0.55, 0.0))
        for sx in (-1, 1):
            M.box((sx * (hw + 0.10) - 0.3, sy * (Lh - 0.2) - 0.3, -0.8), (sx * (hw + 0.10) + 0.3, sy * (Lh - 0.2) + 0.3, 0.45), S, tile=0.8)
            M.box((sx * (hw + 0.10) - 0.35, sy * (Lh - 0.2) - 0.35, 0.45), (sx * (hw + 0.10) + 0.35, sy * (Lh - 0.2) + 0.35, 0.55), GR, tile=0.8)
    return M, C, (lambda P, N: np.clip(0.80 + 0.20 * (P[:, 2] + 0.5) / 1.2, 0, 1))


# --------------------------------------------------------------------------------------------------- gate
@asset('pk_gatepost', 'struct', dist=300, day_glow=0.0)
def gatepost():
    """stone entrance pillar with lantern, plaque lamp and cap (origin = centre of the pillar)"""
    M, C = Mesh(), Col()
    S, GR, IR = m('stone'), m('granite'), m('iron')
    M.box((-0.58, -0.58, -0.1), (0.58, 0.58, 0.45), S, tile=0.9)
    M.box((-0.64, -0.64, 0.45), (0.64, 0.64, 0.58), GR, tile=0.9)
    M.box((-0.42, -0.42, 0.58), (0.42, 0.42, 3.05), S, tile=0.9)
    for ax in (0, 1):
        for s in (-1, 1):
            q = 0.425 * s
    M.box((-0.52, -0.52, 3.05), (0.52, 0.52, 3.20), GR, tile=0.9)
    M.box((-0.58, -0.58, 3.20), (0.58, 0.58, 3.30), GR, tile=0.9)
    M.cone((0, 0), 0.72, 3.30, 3.78, 4, GR, tile=0.9, theta0=np.pi / 4, r_top=0.30)
    M.box((-0.30, -0.30, 3.78), (0.30, 0.30, 3.86), GR, tile=0.9)
    from .kit import place
    L = Mesh()
    lantern(L, 0.0, IR)
    place(M, L, (0, 0, 3.86), 0, 0.95)
    # carved ring bands
    for z in (1.0, 2.7):
        M.box((-0.455, -0.455, z - 0.05), (0.455, 0.455, z + 0.05), GR, tile=0.9)
    C.box((-0.62, -0.62, 0.0), (0.62, 0.62, 3.9))
    return M, C, (lambda P, N: np.clip(0.78 + 0.22 * np.clip(P[:, 2] / 1.0, 0, 1), 0, 1))


@asset('pk_gatearch', 'struct', dist=300, day_glow=0.0)
def gatearch():
    """wrought-iron arch over the entrance with the 'CENTRAL PARK' sign (spans x -3.5..3.5, springs at z=3.1)"""
    M, C = Mesh(), Col()
    IR, SG, WD = m('iron'), m('sign_park'), m('wooddark')
    X = 3.1
    ts = np.linspace(-1, 1, 31)
    def zt(x):
        return 3.05 + 1.35 * np.sqrt(np.maximum(1 - (x / X) ** 2, 0)) ** 0.8
    top = [(X * t, 0, zt(X * t)) for t in ts]
    low = [(X * t, 0, zt(X * t) - 0.34) for t in ts]
    gx.tube(M, top, [0.035] * len(top), 8, IR, tile=0.5, cap_end=True, cap_start=True)
    gx.tube(M, low, [0.028] * len(low), 8, IR, tile=0.5, cap_end=True, cap_start=True)
    for i in range(3, len(ts) - 3):
        x = X * ts[i]
        if i % 2:
            gx.bar(M, (x, 0, zt(x) - 0.33), (x, 0, zt(x) - 0.02), 0.02, IR, h=0.02, tile=0.4, caps=False)
    # scrolls beneath the arch at both ends
    for s in (-1, 1):
        pts = [(s * (X - 0.05 - 0.50 * (1 - np.cos(a)) * 0.0 - 0.28 * np.sin(a)), 0, 3.05 - 0.45 + 0.45 * (1 - np.cos(a)) * 0.0 - 0.0 + 0.0 * a) for a in np.linspace(0, 3.4, 18)]
        pts = [(s * (X - 0.1 - 0.42 * (1 - np.cos(a))), 0, 3.0 - 0.16 * a - 0.12 * np.sin(a * 2)) for a in np.linspace(0, 2.7, 18)]
        gx.tube(M, pts, [0.018] * len(pts), 6, IR, tile=0.4, cap_end=True)
    # sign: hung between the rails
    M.poly([(-1.55, -0.03, 3.38), (1.55, -0.03, 3.38), (1.55, -0.03, 4.17), (-1.55, -0.03, 4.17)], SG, hint=(0, -1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    M.poly([(1.55, 0.03, 3.38), (-1.55, 0.03, 3.38), (-1.55, 0.03, 4.17), (1.55, 0.03, 4.17)], SG, hint=(0, 1, 0), uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
    for (a, b, c, d) in ((-1.58, -0.03, 3.355, 3.38), (-1.58, -0.03, 4.17, 4.195)):
        M.box((a, b, c), (1.58, 0.03, d), IR, tile=0.5)
    for sx in (-1, 1):
        M.box((sx * 1.58 - 0.012, -0.03, 3.355), (sx * 1.58 + 0.012, 0.03, 4.195), IR, tile=0.5)
        for xx in (sx * 1.2,):
            gx.bar(M, (xx, 0, 4.195), (xx, 0, zt(xx) - 0.34), 0.02, IR, h=0.02, tile=0.4)
    # finial
    gx.sphere(M, (0, 0, zt(0) + 0.07), 0.07, IR, 8, 5)
    M.cone((0, 0), 0.05, zt(0) + 0.10, zt(0) + 0.45, 6, IR, tile=0.3)
    for s in (-1, 1):
        gx.sphere(M, (s * X, 0, 3.05), 0.06, IR, 8, 5)
    C.box((-0.001, -0.001, 3.0), (0.001, 0.001, 3.002))
    return M, C, (lambda P, N: np.ones(len(P)))


@asset('pk_gateleaf', 'struct', dist=300, day_glow=0.0)
def gateleaf():
    """one wrought-iron gate leaf, hinge at the origin, extends along +x (2.95 m); rises towards the free end"""
    M, C = Mesh(), Col()
    IR, GD = m('iron'), m('metal')
    Wd = 2.95
    def top(x):
        return 1.85 + 0.30 * (x / Wd) ** 2
    gx.bar(M, (0.02, 0, 0.16), (Wd, 0, 0.16), 0.05, IR, h=0.10, tile=0.5)
    gx.bar(M, (0.02, 0, 0.55), (Wd, 0, 0.55), 0.035, IR, h=0.04, tile=0.5)
    xs = np.linspace(0.03, Wd, 23)
    for a, b in zip(xs[:-1], xs[1:]):
        gx.bar(M, (a, 0, top(a) - 0.18), (b, 0, top(b) - 0.18), 0.05, IR, h=0.06, tile=0.5)
        gx.bar(M, (a, 0, top(a) - 0.55), (b, 0, top(b) - 0.55), 0.03, IR, h=0.035, tile=0.5)
    n = 19
    for i in range(n + 1):
        x = 0.05 + (Wd - 0.08) * i / n
        z1 = top(x)
        big = i in (0, n)
        w = 0.05 if big else 0.026
        gx.bar(M, (x, 0, 0.0), (x, 0, z1 - 0.10), w, IR, h=w, tile=0.5, caps=False)
        M.poly([(x - 0.032, -0.012, z1 - 0.12), (x + 0.032, -0.012, z1 - 0.12), (x, 0, z1 + 0.10)], IR, hint=(0, -1, 0.3), tile=0.3)
        M.poly([(x + 0.032, 0.012, z1 - 0.12), (x - 0.032, 0.012, z1 - 0.12), (x, 0, z1 + 0.10)], IR, hint=(0, 1, 0.3), tile=0.3)
        M.poly([(x - 0.032, 0.012, z1 - 0.12), (x - 0.032, -0.012, z1 - 0.12), (x, 0, z1 + 0.10)], IR, hint=(-1, 0, 0.3), tile=0.3)
        M.poly([(x + 0.032, -0.012, z1 - 0.12), (x + 0.032, 0.012, z1 - 0.12), (x, 0, z1 + 0.10)], IR, hint=(1, 0, 0.3), tile=0.3)
        if i % 2 == 1 and 0 < i < n:
            pts = [(x + 0.14 * np.cos(a), 0, 1.20 + 0.14 * np.sin(a)) for a in np.linspace(0, TAU, 9)]
            gx.tube(M, pts, [0.011] * 9, 4, IR, tile=0.3, cap_end=False)
    # hinge knuckles and centre rosette
    for z in (0.35, 1.5):
        gx.cyl(M, (0.0, 0, z - 0.09), (0.0, 0, z + 0.09), 0.045, 0.045, 8, GD, tile=0.3)
    gx.sphere(M, (Wd - 0.05, 0.0, 1.05), 0.05, GD, 8, 5)
    C.box((0.0, -0.05, 0.0), (Wd, 0.05, 2.0))
    return M, C
