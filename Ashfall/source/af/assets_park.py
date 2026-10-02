# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# assets_park.py - landmarks of the ruined central park: dry broken fountain, rusted playground, gazebo ruin, wooden pier
#   with a collapsed end, memorial obelisk, park benches.  (The lake water itself is a native MTA water polygon.)
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, unit, TAU
from . import gx
from .kit import asset, m
from .assets_props import _ao, rnd

UP = np.array([0, 0, 1.0])


@asset('af_fountain', 'props', 400)
def fountain():
    M, C = Mesh(), Col()
    conc, moss, rust = m('concrete'), m('moss'), m('rust')
    r = rnd(7)
    # outer basin: ring wall + dry floor with a broken sector
    R0, R1, H = 6.4, 5.6, 0.95
    n = 28
    for i in range(n):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        if 9 <= i <= 11:                                  # collapsed section of the rim
            hh = 0.25 + 0.1 * (i - 9)
        else:
            hh = H - (0.18 if r.random() < 0.15 else 0.0)
        p = lambda rad, a, z: (np.cos(a) * rad, np.sin(a) * rad, z)
        M.poly([p(R0, a0, 0), p(R0, a1, 0), p(R0, a1, hh), p(R0, a0, hh)], conc, hint=(np.cos((a0 + a1) / 2), np.sin((a0 + a1) / 2), 0), tile=2.0)
        M.poly([p(R1, a0, 0.25), p(R1, a1, 0.25), p(R1, a1, hh), p(R1, a0, hh)], moss, hint=(-np.cos((a0 + a1) / 2), -np.sin((a0 + a1) / 2), 0), tile=2.0)
        M.poly([p(R1, a0, hh), p(R1, a1, hh), p(R0, a1, hh), p(R0, a0, hh)], conc, hint=(0, 0, 1), tile=2.0)
    M.prism((0, 0), R1, 0.0, 0.25, 28, moss, tile=3.0, cap_top=True)
    # fallen rim pieces
    for a in (9.4, 10.2, 11.0):
        ang = TAU * a / n
        gx.rock(M, (np.cos(ang) * (R0 + 0.8), np.sin(ang) * (R0 + 0.8), 0.2), (0.9, 0.5, 0.35), conc, int(a * 10), n=9)
    # pedestal, mid basin, column
    M.prism((0, 0), 1.6, 0.25, 1.4, 20, conc, tile=2.0, cap_top=True)
    M.prism((0, 0), 3.0, 1.4, 1.75, 24, conc, tile=2.0, cap_top=True)
    M.prism((0, 0), 2.7, 1.75, 2.0, 24, moss, tile=2.0, cap_top=True)
    M.prism((0, 0), 0.55, 2.0, 3.4, 12, conc, tile=1.5, cap_top=True)
    # upper basin is cracked: half of it
    for i in range(10):
        a0, a1 = np.pi * i / 10 + 0.4, np.pi * (i + 1) / 10 + 0.4
        p = lambda rad, a, z: (np.cos(a) * rad, np.sin(a) * rad, z)
        M.poly([p(1.5, a0, 3.4), p(1.5, a1, 3.4), p(1.5, a1, 3.85), p(1.5, a0, 3.85)], conc, hint=(np.cos((a0 + a1) / 2), np.sin((a0 + a1) / 2), 0), tile=1.5)
        M.poly([p(1.5, a0, 3.85), p(1.5, a1, 3.85), p(1.1, a1, 3.85), p(1.1, a0, 3.85)], conc, hint=(0, 0, 1), tile=1.5)
    gx.tube(M, [(0.0, 0.0, 3.4), (0.15, 0.1, 4.4), (0.5, 0.2, 5.2)], [0.26, 0.2, 0.12], 8, rust, tile=1.0, cap_end=True)
    # broken statue plinth top pieces on the ground
    gx.rock(M, (2.3, -1.9, 0.5), (0.7, 0.55, 0.5), conc, 71, n=9)
    gx.rock(M, (-2.8, 1.4, 0.45), (0.8, 0.6, 0.4), conc, 72, n=9)
    # moss + weeds are placed by the layout; collision
    C.box((-1.7, -1.7, 0), (1.7, 1.7, 2.0))
    C.box((-0.6, -0.6, 2.0), (0.6, 0.6, 3.4))
    for i in range(n):
        if 9 <= i <= 11:
            continue
        a = TAU * (i + 0.5) / n
        c = np.array([np.cos(a), np.sin(a)]) * (R0 + R1) / 2
        t = np.array([-np.sin(a), np.cos(a)]) * 1.0
        C.strip(c - t, c + t, R0 - R1, 0.0, H)
    return M, C, _ao


@asset('af_gazebo', 'props', 300)
def gazebo():
    M, C = Mesh(), Col()
    r = rnd(8)
    conc, wood, rust, steel = m('concrete'), m('wood'), m('rust'), m('steel')
    R = 4.0
    M.prism((0, 0), R + 0.5, 0.0, 0.45, 8, conc, tile=2.0, cap_top=True)
    posts = []
    for i in range(8):
        a = TAU * i / 8 + TAU / 16
        x, y = np.cos(a) * R, np.sin(a) * R
        top = 3.4 if i not in (2, 3) else (1.9 if i == 2 else 1.1)      # two posts broken off
        gx.bar(M, (x, y, 0.45), (x + (0.4 if i == 3 else 0), y, top), 0.28, wood, tile=1.0)
        posts.append((x, y, top))
        C.box((x - 0.15, y - 0.15, 0.0), (x + 0.15, y + 0.15, top))
    # roof ring beams and rafters (some missing)
    for i in range(8):
        j = (i + 1) % 8
        if posts[i][2] > 3 and posts[j][2] > 3:
            gx.bar(M, (posts[i][0], posts[i][1], 3.3), (posts[j][0], posts[j][1], 3.3), 0.2, wood, h=0.3)
    for i in range(8):
        if r.random() < 0.25 or posts[i][2] < 3:
            continue
        gx.bar(M, (posts[i][0], posts[i][1], 3.4), (0, 0, 5.2), 0.14, wood)
    # remaining roof panels (rusty steel) on 3 sectors
    for i in (4, 5, 6, 0):
        a0, a1 = TAU * i / 8 + TAU / 16, TAU * (i + 1) / 8 + TAU / 16
        M.poly([(np.cos(a0) * (R + 0.6), np.sin(a0) * (R + 0.6), 3.0), (np.cos(a1) * (R + 0.6), np.sin(a1) * (R + 0.6), 3.0), (0, 0, 5.3)], rust, hint=(np.cos((a0 + a1) / 2), np.sin((a0 + a1) / 2), 1.0), tile=2.0, double=True)
    # fallen roof pieces + railing remnants
    for k in range(5):
        a = r.uniform(0, TAU)
        gx.bar(M, (np.cos(a) * 1.5, np.sin(a) * 1.5, 0.5), (np.cos(a) * 3.5, np.sin(a) * 3.5, 0.9), 0.5, rust, h=0.08)
    gx.rock(M, (0.8, -0.6, 0.55), (0.9, 0.7, 0.4), wood, 81, n=9)
    # bench ring remains
    for k in range(3):
        a = TAU * k / 3 + 1.0
        M.box((np.cos(a) * 3.2 - 0.9, np.sin(a) * 3.2 - 0.2, 0.45), (np.cos(a) * 3.2 + 0.9, np.sin(a) * 3.2 + 0.2, 0.9), wood, tile=1.0) if False else None
    C.box((-R - 0.5, -R - 0.5, 0.0), (R + 0.5, R + 0.5, 0.45))
    return M, C, _ao


@asset('af_playground', 'props', 260)
def playground():
    M, C = Mesh(), Col()
    r = rnd(9)
    rust, steel, wood = m('rust'), m('steel'), m('wood')
    # swing set with two swings (one hanging by a single chain)
    for sx in (-2.0, 2.0):
        gx.bar(M, (sx, -0.9, 0), (sx, 0.0, 2.6), 0.09, rust)
        gx.bar(M, (sx, 0.9, 0), (sx, 0.0, 2.6), 0.09, rust)
    gx.bar(M, (-2.1, 0, 2.62), (2.1, 0, 2.62), 0.1, rust)
    for sx, broken in ((-0.8, False), (0.8, True)):
        gx.bar(M, (sx - 0.3, 0, 2.55), (sx - 0.3, 0, 0.55), 0.015, steel)
        if not broken:
            gx.bar(M, (sx + 0.3, 0, 2.55), (sx + 0.3, 0, 0.55), 0.015, steel)
            M.box((sx - 0.32, -0.12, 0.5), (sx + 0.32, 0.12, 0.55), wood, tile=0.5)
        else:
            gx.bar(M, (sx - 0.3, 0, 0.55), (sx + 0.1, 0.0, 0.1), 0.2, wood, h=0.04)
            M.box((sx + 0.1, -0.12, 0.0), (sx + 0.7, 0.12, 0.06), wood, tile=0.5)
    # slide on a platform
    ox = 5.5
    for sx in (-0.6, 0.6):
        for sy in (-0.6, 0.6):
            gx.bar(M, (ox + sx, sy, 0), (ox + sx, sy, 1.9), 0.08, rust)
    M.box((ox - 0.75, -0.75, 1.9), (ox + 0.75, 0.75, 1.96), wood, tile=1.0)
    q = [(ox - 0.4, 0.75, 1.88), (ox + 0.4, 0.75, 1.88), (ox + 0.4, 3.6, 0.3), (ox - 0.4, 3.6, 0.3)]
    M.poly(q, m('steel'), hint=(0, 0, 1), tile=1.0, double=True)
    for sx in (-0.4, 0.4):
        gx.bar(M, (ox + sx, 0.75, 1.88), (ox + sx, 3.6, 0.3), 0.04, rust, h=0.25)
    # merry-go-round (tilted, rusty)
    mx, my = -4.5, 4.0
    M.prism((mx, my), 1.3, 0.35, 0.42, 14, m('steel'), tile=1.0, cap_top=True)
    for k in range(6):
        a = TAU * k / 6
        gx.bar(M, (mx, my, 0.45), (mx + np.cos(a) * 1.25, my + np.sin(a) * 1.25, 0.9), 0.04, rust)
    gx.bar(M, (mx, my, 0.0), (mx, my, 0.4), 0.15, rust)
    # seesaw
    gx.bar(M, (-3.0, -3.5, 0.65), (-1.0, -3.5, 0.15), 0.18, wood, h=0.06)
    gx.bar(M, (-2.0, -3.5, 0.0), (-2.0, -3.5, 0.45), 0.12, rust)
    # monkey bars frame
    for sx in (-1.5, 1.5):
        gx.bar(M, (3 + sx, -4.0, 0), (3 + sx, -4.0, 2.0), 0.07, rust)
    for sx in (-1.5, 1.5):
        gx.bar(M, (3 + sx, -4.0, 2.0), (3 + sx, -5.4, 2.0), 0.06, rust)
    for k in range(6):
        gx.bar(M, (1.5, -4.0 - k * 0.27, 2.0), (4.5, -4.0 - k * 0.27, 2.0), 0.03, rust) if False else None
    C.box((-2.2, -1.0, 0), (2.2, 1.0, 2.7))
    C.box((ox - 0.8, -0.8, 0), (ox + 0.8, 0.8, 2.0))
    C.box((mx - 1.3, my - 1.3, 0), (mx + 1.3, my + 1.3, 0.45))
    return M, C, _ao


@asset('af_pier', 'props', 300)
def pier():
    M, C = Mesh(), Col()
    wood, wd = m('wood'), m('bark')
    L, W = 15.0, 2.2
    for i in range(0, int(L / 1.5)):
        y = i * 1.5
        for sx in (-W / 2 + 0.2, W / 2 - 0.2):
            gx.bar(M, (sx, y, -2.5), (sx, y, 0.35), 0.22, wd) if i < 8 else None
    # deck boards; the last stretch sags and breaks
    n = int(L / 0.28)
    r = rnd(10)
    for k in range(n):
        y = k * 0.28
        if y > 11.5 and r.random() < 0.55:
            continue
        z = 0.35 - max(0, (y - 9.0)) * 0.12
        tilt = r.uniform(-0.04, 0.04) if y > 9 else 0
        M.box((-W / 2, y, z), (W / 2, y + 0.25, z + 0.06 + tilt), wood, tile=1.0)
    for sx in (-W / 2 + 0.1, W / 2 - 0.1):
        gx.bar(M, (sx, 0, 0.28), (sx, 11.0, 0.0), 0.12, wd, h=0.14)
    C.box((-W / 2, 0, 0.2), (W / 2, 9.0, 0.45))
    return M, C, _ao


@asset('af_obelisk', 'props', 300)
def obelisk():
    M, C = Mesh(), Col()
    conc = m('concrete')
    M.box((-1.8, -1.8, 0), (1.8, 1.8, 0.4), conc, tile=2.0)
    M.box((-1.4, -1.4, 0.4), (1.4, 1.4, 0.9), conc, tile=2.0)
    M.box((-0.8, -0.8, 0.9), (0.8, 0.8, 4.3), m('plaster_a'), tile=1.5)
    M.cone((0, 0), 0.8, 4.3, 5.6, 4, m('plaster_a'), tile=1.5, theta0=TAU / 8)
    gx.rock(M, (2.6, 1.2, 0.35), (0.9, 0.6, 0.35), conc, 91, n=9)
    C.box((-1.8, -1.8, 0), (1.8, 1.8, 0.9))
    C.box((-0.8, -0.8, 0.9), (0.8, 0.8, 5.2))
    return M, C, _ao


@asset('af_bench_p', 'props', 120)
def bench_p():
    M, C = Mesh(), Col()
    r = rnd(12)
    for sx in (-0.85, 0.85):
        M.box((sx - 0.05, -0.25, 0.0), (sx + 0.05, 0.25, 0.46), m('rust'), tile=0.6)
        M.box((sx - 0.05, 0.2, 0.46), (sx + 0.05, 0.27, 0.95), m('rust'), tile=0.6)
    for k in range(4):
        if r.random() < 0.15:
            continue
        M.box((-1.0, -0.24 + k * 0.12, 0.46), (1.0, -0.14 + k * 0.12, 0.5), m('wood'), tile=1.0)
    for k in range(3):
        if r.random() < 0.3:
            continue
        M.box((-1.0, 0.22, 0.55 + k * 0.14), (1.0, 0.26, 0.65 + k * 0.14), m('wood'), tile=1.0)
    C.box((-1.0, -0.26, 0), (1.0, 0.27, 0.95))
    return M, C, _ao
