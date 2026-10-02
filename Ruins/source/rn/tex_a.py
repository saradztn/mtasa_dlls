# Created by: Arena.ai Agent Mode (AI) - Ruins MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# tex_a.py - ground and building materials: asphalt, road markings, sidewalks, curbs, dirt, gravel, leaf litter, bricks,
#            concrete, stucco, curtain wall, windows, doors, boards, corrugated metal, roofs, interior surfaces.
# Every generator returns final diffuse: float HxWx3 (opaque) or HxWx4 (alpha).  Aged: cracks, stains, rust, moss.
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .tcore import *


# ----------------------------------------------------------------------------------------------- street
def _asphalt_base(h, w, s, tone=0.16, crack_n=9, alligator=True):
    agg = nb(h, w, 0.8, 0.8, s)
    mott = n1(h, w, 1.6, s + 1)
    base = tone + 0.028 * mott + 0.040 * agg
    c = base[..., None] * col((1.0, 0.99, 0.965))
    stones = smooth(1.5, 2.7, nb(h, w, 0.7, 0.7, s + 2))
    c = c + stones[..., None] * col((0.10, 0.10, 0.095))
    c = c * (1 - 0.30 * smooth(1.3, 2.6, nb(h, w, 38, 38, s + 3)))[..., None]            # oil / water stains
    c = c * (1 - 0.22 * smooth(1.0, 2.2, nb(h, w, 5, 420, s + 4)))[..., None]            # tyre tracks (along v)
    c = c * (1 + 0.20 * smooth(1.2, 2.5, nb(h, w, 60, 60, s + 11)))[..., None]            # bleached / sun faded areas
    hgt = agg * 0.25 + stones * 0.4
    big = draw_cracks(h, w, s + 5, n=crack_n, length=(0.25, 0.8), width=h / 340, branch=0.8)
    big = np.maximum(big, 0.0)
    cr = gblur(big, 0.8)
    cr = np.clip(cr * 1.8, 0, 1)
    al = np.zeros((h, w), F32)
    if alligator:
        F1, F2, _ = worley(h, w, h // 64, h // 64, s + 6)
        edge = F2 - F1
        area = smooth(0.7, 1.9, nb(h, w, 70, 70, s + 7) + 0.6 * nb(h, w, 22, 22, s + 12))
        al = (smooth(0.09, 0.0, edge) * area).astype(F32)
    crack = np.clip(cr + al * 0.9, 0, 1)
    c = c * (1 - 0.88 * crack)[..., None]
    hgt = hgt - crack * 1.1
    # weeds / moss growing in the big cracks
    near = np.clip(gblur(big, 2.6) * 6, 0, 1)
    weeds = smooth(0.4, 1.4, nb(h, w, 1.4, 1.4, s + 8) + 0.5 * nb(h, w, 4, 4, s + 9)) * near
    wc = lerp(col((0.10, 0.20, 0.05)), col((0.30, 0.38, 0.10)), np.clip(0.5 + 0.5 * n1(h, w, 1.3, s + 10), 0, 1))
    c = lerp(c, wc, weeds * 0.85)
    hgt = hgt + weeds * 0.5
    return c, hgt, crack


def gen_asphalt():
    h = w = 1024
    c, hgt, _ = _asphalt_base(h, w, 1000)
    return np.clip(shade(c, hgt * 3, 0.6) * 1.0, 0, 1)


def _lane_strip(seed, kind):
    """asphalt strip with marking; u across the road (0..1), v along (periodic)"""
    h = w = 512
    c, hgt, crack = _asphalt_base(h, w, seed, crack_n=5)
    paint = np.zeros((h, w), F32)
    X = np.arange(w)[None, :].repeat(h, 0)
    Y = np.arange(h)[:, None].repeat(w, 1)
    if kind == 'yellow2':
        for cx in (w // 2 - 16, w // 2 + 16):
            paint = np.maximum(paint, (np.abs(X - cx) < 5).astype(F32))
        pc = col((0.62, 0.50, 0.12))
    elif kind == 'white_dash':
        paint = ((np.abs(X - w // 2) < 6) & ((Y % 256) < 140)).astype(F32)
        pc = col((0.66, 0.65, 0.60))
    else:      # white edge line, near the left side
        paint = (np.abs(X - 56) < 6).astype(F32)
        pc = col((0.66, 0.65, 0.60))
    wear = smooth(0.2, 1.6, nb(h, w, 8, 8, seed + 20) + 0.8 * nb(h, w, 2, 2, seed + 21) + 0.3)
    paint = paint * wear * (1 - crack * 0.9)
    paint = gblur(paint, 0.7)
    c = lerp(c, pc * (0.8 + 0.25 * nb(h, w, 1, 1, seed + 22))[..., None], np.clip(paint, 0, 1) * 0.92)
    return np.clip(shade(c, hgt * 3, 0.6), 0, 1)


def gen_road_yellow():
    return _lane_strip(1100, 'yellow2')


def gen_road_dash():
    return _lane_strip(1200, 'white_dash')


def gen_road_edge():
    return _lane_strip(1300, 'edge')


def gen_crosswalk():
    h = w = 512
    c, hgt, crack = _asphalt_base(h, w, 1400, crack_n=5)
    Y = np.arange(h)[:, None].repeat(w, 1)
    stripe = ((Y % 128) < 72).astype(F32)
    wear = smooth(0.0, 1.5, nb(h, w, 6, 6, 1401) + 0.9 * nb(h, w, 1.5, 1.5, 1402) + 0.4)
    paint = gblur(stripe * wear * (1 - crack * 0.9), 0.8)
    c = lerp(c, col((0.68, 0.67, 0.62)) * (0.8 + 0.25 * nb(h, w, 1, 1, 1403))[..., None], np.clip(paint, 0, 1) * 0.95)
    return np.clip(shade(c, hgt * 3, 0.6), 0, 1)


def gen_sidewalk():
    h = w = 1024
    s = 1500
    r = np.random.default_rng(s)
    n = 4
    sl = h // n
    Y, X = np.mgrid[0:h, 0:w]
    sid = (X // sl) + (Y // sl) * n
    tone = r.uniform(0.80, 1.12, n * n)[sid]
    warm = r.normal(0, 0.012, (n * n, 3)).astype(F32)[sid]
    ex = np.minimum(X % sl, sl - 1 - X % sl)
    ey = np.minimum(Y % sl, sl - 1 - Y % sl)
    e = np.minimum(ex, ey).astype(F32) + nb(h, w, 4, 4, s + 1) * 1.6
    joint = smooth(1.0, 5.0, e)
    gr = n1(h, w, 1.2, s + 2) * 0.05 + nb(h, w, 0.8, 0.8, s + 3) * 0.05
    c = col((0.50, 0.49, 0.46))[None, None] * (tone * (1 + gr) * (1 + 0.14 * n1(h, w, 2.6, s + 4)))[..., None] + warm
    c = c * (1 - 0.22 * smooth(0.5, 2.2, nb(h, w, 30, 30, s + 5)))[..., None]            # stains
    cr = np.clip(gblur(draw_cracks(h, w, s + 6, n=14, length=(0.1, 0.45), width=2.2, branch=0.9), 0.7) * 1.8, 0, 1)
    c = c * (1 - 0.8 * cr)[..., None]
    cr_near = np.clip(gblur(cr, 3) * 5, 0, 1)
    wd = smooth(0.2, 1.3, nb(h, w, 1.5, 1.5, s + 7) + 0.6 * nb(h, w, 5, 5, s + 8))
    wc = lerp(col((0.10, 0.22, 0.05)), col((0.32, 0.40, 0.11)), np.clip(0.5 + 0.5 * n1(h, w, 1.3, s + 9), 0, 1))
    c = lerp(c, col((0.13, 0.12, 0.09)), (1 - joint) * 0.9)
    gm = np.maximum((1 - joint) * smooth(0.3, 1.6, nb(h, w, 3, 3, s + 10)), cr_near * wd) * 0.85
    c = lerp(c, wc, gm)
    hgt = joint * 1.5 + gr * 3 - cr * 1.2
    c = shade(c, hgt * 2.0, 0.8)
    c = mix(c, (0.20, 0.30, 0.10), 0.30 * smooth(1.4, 2.6, nb(h, w, 12, 12, s + 11)))        # moss patches
    return np.clip(c, 0, 1)


def gen_curb():
    h = w = 256
    s = 1600
    g = n1(h, w, 1.3, s) * 0.06 + nb(h, w, 0.8, 0.8, s + 1) * 0.05
    c = col((0.50, 0.49, 0.46))[None, None] * (1 + g)[..., None]
    band = smooth(70, 90, np.arange(h)[:, None].repeat(w, 1).astype(F32)) * smooth(190, 170, np.arange(h)[:, None].repeat(w, 1).astype(F32))
    fade = smooth(0.0, 1.4, nb(h, w, 6, 6, s + 2) + 0.8 * nb(h, w, 1.4, 1.4, s + 3) + 0.2)
    c = lerp(c, col((0.62, 0.50, 0.12)), band * fade * 0.6)
    c = weather(c, g * 6, s + 4, grime=0.8, streak=0.2, moss=0.3, dust=0.5)
    return np.clip(c, 0, 1)


def gen_dirt():
    h = w = 512
    s = 1700
    n = n1(h, w, 1.5, s)
    c = lerp(col((0.14, 0.10, 0.065)), col((0.30, 0.23, 0.15)), np.clip(0.5 + 0.35 * n + 0.3 * nb(h, w, 0.8, 0.8, s + 1), 0, 1))
    pebbles = smooth(1.7, 2.6, nb(h, w, 1.0, 1.0, s + 2))
    c = lerp(c, col((0.40, 0.37, 0.32)), pebbles * 0.6)
    c = mix(c, (0.10, 0.17, 0.05), 0.55 * smooth(0.9, 2.0, nb(h, w, 9, 9, s + 3)))
    hgt = n * 0.5 + pebbles
    return np.clip(shade(c, hgt * 2, 0.7), 0, 1)


def gen_gravel():
    h = w = 512
    s = 1800
    F1, F2, ID = worley(h, w, 38, 38, s)
    stone = smooth(0.62, 0.15, F1)
    tone = 0.25 + 0.5 * ID
    c = col((0.42, 0.40, 0.37))[None, None] * tone[..., None] * (0.7 + 0.4 * stone)[..., None]
    c = c * (0.25 + 0.75 * smooth(0.05, 0.4, F2 - F1))[..., None]
    c = mix(c, (0.15, 0.12, 0.09), 0.5 * smooth(0.5, 1.7, nb(h, w, 12, 12, s + 1)))
    c = mix(c, (0.12, 0.2, 0.05), 0.4 * smooth(1.2, 2.4, nb(h, w, 5, 5, s + 2)))
    return np.clip(shade(c, stone * 1.5, 0.6), 0, 1)


def gen_leaflitter():
    h = w = 512
    s = 1900
    base = lerp(col((0.10, 0.07, 0.04)), col((0.30, 0.20, 0.09)), np.clip(0.5 + 0.4 * n1(h, w, 1.4, s), 0, 1))
    im = Image.new('RGB', (w * 2, h * 2), (22, 16, 9))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(s)
    palette = [(120, 74, 28), (150, 98, 34), (92, 60, 24), (130, 112, 44), (74, 80, 28), (104, 46, 20), (60, 44, 20)]
    for _ in range(900):
        x, y = r.random() * w * 2, r.random() * h * 2
        L = r.uniform(10, 26)
        a = r.random() * TAU
        pts = [(x + np.cos(a) * L * np.cos(t) - np.sin(a) * L * 0.35 * np.sin(t), y + np.sin(a) * L * np.cos(t) + np.cos(a) * L * 0.35 * np.sin(t)) for t in np.linspace(0, TAU, 9)]
        cc = palette[r.integers(len(palette))]
        cc = tuple(int(v * r.uniform(0.7, 1.15)) for v in cc)
        for ox in (-w * 2, 0, w * 2):
            for oy in (-h * 2, 0, h * 2):
                d.polygon([(px + ox, py + oy) for px, py in pts], fill=cc)
    c = img_to_np(im.resize((w, h), Image.LANCZOS))
    c = mix(c, (0.10, 0.18, 0.05), 0.5 * smooth(1.0, 2.2, nb(h, w, 8, 8, s + 1)))
    c = c * (0.85 + 0.3 * n1(h, w, 1.5, s + 2))[..., None]
    return np.clip(c, 0, 1)


def gen_moss():
    h = w = 512
    s = 2000
    n = n1(h, w, 1.1, s)
    tuft = smooth(0.0, 1.5, nb(h, w, 1.2, 1.2, s + 1) + 0.5)
    c = lerp(col((0.06, 0.12, 0.03)), col((0.26, 0.38, 0.09)), np.clip(0.45 + 0.4 * n + 0.3 * tuft, 0, 1))
    c = mix(c, (0.35, 0.33, 0.28), 0.35 * smooth(1.3, 2.5, nb(h, w, 10, 10, s + 2)))
    return np.clip(shade(c, tuft * 2 + n * 0.5, 0.8), 0, 1)


def gen_grass():
    h = w = 512
    s = 2100
    n2 = bnoise(h, w, 0.9, 3.4, s + 1).astype(F32)
    n3, n4 = nb(h, w, 40, 40, s + 2), nb(h, w, 9, 9, s + 3)
    t = np.clip(0.5 + 0.22 * n3 + 0.17 * n4 + 0.1 * n1(h, w, 1.1, s), 0, 1)
    dark, mid, light = col((0.07, 0.15, 0.035)), col((0.19, 0.31, 0.08)), col((0.38, 0.45, 0.14))
    c = np.where((t < 0.5)[..., None], lerp(dark, mid, smooth(0.1, 0.5, t)), lerp(mid, light, smooth(0.5, 0.95, t)))
    c = c * (0.58 + 0.62 * (0.5 + 0.5 * n2))[..., None]
    dry = smooth(1.2, 2.2, nb(h, w, 16, 16, s + 4) + 0.5 * n1(h, w, 1.5, s + 5))          # dead straw patches (overgrown + neglected)
    c = lerp(c, col((0.46, 0.40, 0.19)) * (0.7 + 0.3 * (0.5 + 0.5 * n2))[..., None], dry * 0.65)
    c = mix(c, (0.22, 0.17, 0.09), 0.6 * smooth(1.9, 2.8, nb(h, w, 14, 14, s + 6)))        # bare soil
    return np.clip(c, 0, 1)


def gen_parkpath():
    """old cracked pavers with weeds"""
    h = w = 512
    s = 2200
    r = np.random.default_rng(s)
    rows, sw = 8, 128
    Y, X = np.mgrid[0:h, 0:w]
    ry = Y // (h // rows)
    off = (ry % 2) * (sw // 2)
    cx = (X + off) % sw
    cy = Y % (h // rows)
    sid = (((X + off) // sw) % (w // sw) + ry * 10) % 200
    bv = r.uniform(0.75, 1.15, 200)[sid]
    e = np.minimum(np.minimum(cx, sw - 1 - cx), np.minimum(cy, h // rows - 1 - cy)).astype(F32) + nb(h, w, 3, 3, s + 1) * 1.1
    joint = smooth(1.0, 3.8, e)
    c = col((0.52, 0.47, 0.41))[None, None] * (bv * (1 + 0.07 * n1(h, w, 1.5, s + 2)))[..., None]
    c = lerp(c, col((0.13, 0.12, 0.09)), (1 - joint) * 0.9)
    cr = np.clip(gblur(draw_cracks(h, w, s + 3, n=8, length=(0.1, 0.4), width=1.8, branch=0.9), 0.6) * 1.8, 0, 1)
    c = c * (1 - 0.8 * cr)[..., None]
    gm = np.maximum((1 - joint) * smooth(0.0, 1.2, nb(h, w, 3, 3, s + 4)), np.clip(gblur(cr, 3) * 5, 0, 1) * smooth(0.2, 1.2, nb(h, w, 2, 2, s + 5)))
    c = lerp(c, lerp(col((0.10, 0.20, 0.05)), col((0.30, 0.38, 0.10)), np.clip(0.5 + 0.5 * n1(h, w, 1.3, s + 6), 0, 1)), gm * 0.9)
    leaves = smooth(1.8, 2.8, nb(h, w, 2, 2, s + 7))
    c = lerp(c, col((0.30, 0.20, 0.08)), leaves * 0.55)
    c = c * (1 - 0.25 * smooth(0.6, 2.0, nb(h, w, 30, 30, s + 8)))[..., None]
    return np.clip(shade(c, joint * 1.4 - cr, 0.8), 0, 1)


def gen_water():
    h = w = 512
    s = 2300
    n = n1(h, w, 2.0, s)
    rip = 1 - np.abs(np.sin((nb(h, w, 14, 14, s + 1) * 2.0 + np.arange(w)[None, :] / w * TAU * 3)))
    sky = np.clip(0.5 + 0.5 * nb(h, w, 40, 40, s + 2), 0, 1)
    c = lerp(col((0.05, 0.10, 0.06)), col((0.13, 0.22, 0.17)), sky * 0.7)
    c = c + (rip ** 8 * 0.14)[..., None] * col((0.6, 0.7, 0.62))
    alg = smooth(0.6, 1.8, nb(h, w, 12, 12, s + 3) + 0.5 * nb(h, w, 3, 3, s + 4))
    c = lerp(c, col((0.14, 0.26, 0.07)), alg * 0.75)                                     # algae scum
    c = mix(c, (0.32, 0.30, 0.18), 0.35 * smooth(1.4, 2.4, nb(h, w, 5, 5, s + 5)))      # pollen / debris film
    a = np.clip(0.80 + 0.10 * n - 0.0 * alg + 0.1 * rip ** 10, 0.62, 0.95)
    return np.concatenate([np.clip(c, 0, 1), a[..., None]], -1).astype(F32)


# --------------------------------------------------------------------------------------------- facades
def _brick(seed, tone_a, tone_b, rows=32, cols=11, mortar=(0.50, 0.47, 0.42), plaster=None, soot=0.6):
    h = w = 1024
    r = np.random.default_rng(seed)
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    v = Y / h * rows
    ri = np.floor(v).astype(int)
    u = X / w * cols + (ri % 2) * 0.5
    bi = np.floor(u).astype(int) % cols
    fx, fy = u - np.floor(u), v - ri
    bw, bh = w / cols, h / rows
    ed = np.minimum(np.minimum(fx * bw, (1 - fx) * bw), np.minimum(fy * bh, (1 - fy) * bh)) + nb(h, w, 2.5, 2.5, seed + 1) * 1.2
    brick = smooth(1.5, 4.5, ed)
    ids = (ri * 31 + bi * 7) % 997
    tv = r.uniform(0, 1, 997)[ids]
    cc = lerp(col(tone_a), col(tone_b), tv)
    cc = cc * (1 + 0.16 * nb(h, w, 1.0, 1.0, seed + 2) + 0.12 * n1(h, w, 1.6, seed + 3))[..., None]
    flame = smooth(0.2, 1.6, nb(h, w, 14, 14, seed + 4))                       # darker burnt bricks
    cc = cc * (1 - 0.35 * flame * (tv > 0.7))[..., None]
    c = lerp(col(mortar) * (0.7 + 0.5 * nb(h, w, 0.8, 0.8, seed + 5))[..., None], cc, brick)
    hgt = brick * 1.2 + nb(h, w, 1.2, 1.2, seed + 6) * 0.2
    if plaster is not None:
        pm = smooth(0.15, 0.9, nb(h, w, 40, 40, seed + 7) + 0.5 * nb(h, w, 14, 14, seed + 8) - 0.45)
        pm = pm * smooth(0.0, 0.6, nb(h, w, 3, 3, seed + 9) + 1.0)
        pc = col(plaster)[None, None] * (1 + 0.1 * nb(h, w, 0.9, 0.9, seed + 10) + 0.08 * n1(h, w, 1.8, seed + 11))[..., None]
        c = lerp(c, pc, pm)
        hgt = hgt * (1 - pm) + pm * 1.9
        edge = smooth(0.0, 0.3, pm) * (1 - smooth(0.5, 1.0, pm))
        c = c * (1 - 0.35 * edge)[..., None]
    c = weather(c, hgt, seed + 20, grime=0.6, streak=soot, moss=0.12, rust=0.0, dust=0.3, streak_len=110)
    return np.clip(shade(c, hgt * 1.6, 0.9), 0, 1)


def gen_brick_red():
    return _brick(3000, (0.46, 0.17, 0.11), (0.60, 0.27, 0.17), plaster=(0.55, 0.50, 0.42))


def gen_brick_brown():
    return _brick(3100, (0.40, 0.28, 0.17), (0.55, 0.40, 0.25), rows=28, cols=10, mortar=(0.55, 0.52, 0.46), plaster=None, soot=0.8)


def gen_concrete():
    h = w = 1024
    s = 3200
    n = n1(h, w, 1.7, s)
    pores = smooth(1.6, 2.8, nb(h, w, 0.8, 0.8, s + 1))
    c = col((0.42, 0.42, 0.40))[None, None] * (1 + 0.13 * n + 0.06 * nb(h, w, 1.0, 1.0, s + 2))[..., None]
    Y, X = np.mgrid[0:h, 0:w]
    seam = np.zeros((h, w), F32)
    for k in (0, 512):
        seam = np.maximum(seam, smooth(7, 2, np.abs(((X - k + 512) % 1024) - 512).astype(F32)))
        seam = np.maximum(seam, smooth(7, 2, np.abs(((Y - k + 512) % 1024) - 512).astype(F32)))
    boards = 0.5 + 0.5 * np.sin(Y / h * TAU * 24 + nb(h, w, 20, 3, s + 3) * 2)           # horizontal shuttering lines
    c = c * (1 - 0.07 * boards)[..., None]
    c = c * (1 - 0.65 * seam)[..., None]
    c = c * (1 - 0.35 * pores)[..., None]
    # spalling with exposed rebar
    sp = smooth(1.5, 2.1, nb(h, w, 20, 20, s + 4) + 0.5 * nb(h, w, 6, 6, s + 5))
    c = lerp(c, col((0.23, 0.21, 0.19)), sp * 0.9)
    bars = (np.abs(((X + nb(h, w, 30, 30, s + 6) * 8) % 96) - 48) < 2.2).astype(F32) * sp
    c = lerp(c, col((0.40, 0.17, 0.07)), gblur(bars, 0.8) * 0.9)
    hgt = n * 0.4 - seam * 2 - pores * 0.5 - sp * 1.5
    c = weather(c, hgt, s + 7, grime=0.7, streak=0.9, moss=0.15, rust=0.55, dust=0.3, streak_len=140)
    return np.clip(shade(c, hgt, 0.8), 0, 1)


def gen_stucco():
    h = w = 512
    s = 3300
    base = lerp(col((0.62, 0.56, 0.42)), col((0.70, 0.64, 0.50)), np.clip(0.5 + 0.5 * n1(h, w, 1.6, s), 0, 1))
    grain = nb(h, w, 0.8, 0.8, s + 1) * 0.06
    peel = smooth(0.1, 0.8, nb(h, w, 26, 26, s + 2) + 0.6 * nb(h, w, 8, 8, s + 3) - 0.35)
    under = lerp(col((0.40, 0.38, 0.35)), col((0.50, 0.30, 0.20)), smooth(0.8, 1.6, nb(h, w, 10, 10, s + 4)))
    c = lerp(base * (1 + grain)[..., None], under * (1 + 3 * grain)[..., None], peel)
    ed = smooth(0.0, 0.25, peel) * (1 - smooth(0.4, 0.9, peel))
    c = c * (1 - 0.3 * ed)[..., None]
    cr = np.clip(gblur(draw_cracks(h, w, s + 5, n=6, length=(0.15, 0.5), width=1.2, branch=0.8), 0.6) * 1.6, 0, 1)
    c = c * (1 - 0.7 * cr)[..., None]
    c = weather(c, grain * 8 - peel * 1.5 - cr, s + 6, grime=0.6, streak=0.9, moss=0.18, rust=0.0, dust=0.3, streak_len=90)
    return np.clip(c, 0, 1)


def gen_glasswall():
    h = w = 512
    s = 3400
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    cell = 128
    pi = (X // cell).astype(int) + 4 * (Y // cell).astype(int)
    r = np.random.default_rng(s)
    missing = r.random(16) < 0.18
    cracked = r.random(16) < 0.30
    ex = np.minimum(X % cell, cell - 1 - X % cell)
    ey = np.minimum(Y % cell, cell - 1 - Y % cell)
    e = np.minimum(ex, ey)
    frame = smooth(7, 3, e)
    sky = np.clip(0.55 + 0.35 * (1 - Y / h) + 0.2 * nb(h, w, 40, 40, s + 1), 0, 1)
    gl = lerp(col((0.10, 0.17, 0.19)), col((0.38, 0.50, 0.52)), sky * 0.8)
    streak = smooth(0.5, 2.0, nb(h, w, 2, 80, s + 2))
    gl = gl * (1 - 0.35 * streak)[..., None]
    gl = mix(gl, (0.30, 0.28, 0.22), 0.4 * smooth(0.8, 2.2, nb(h, w, 18, 18, s + 3)))   # grime
    dark = col((0.015, 0.02, 0.022))[None, None] * (1 + 4 * nb(h, w, 1, 1, s + 4))[..., None]
    miss = missing[pi]
    gl = np.where(miss[..., None], dark + 0.0 * gl, gl)
    # spider cracks
    cr = np.zeros((h, w), F32)
    for i in range(16):
        if cracked[i] and not missing[i]:
            ox, oy = (i % 4) * cell, (i // 4) * cell
            im = Image.new('L', (cell, cell), 0)
            d = ImageDraw.Draw(im)
            cx, cy = r.uniform(30, 98), r.uniform(30, 98)
            for k in range(9):
                a = r.uniform(0, TAU)
                pts = [(cx, cy)]
                L = r.uniform(30, 90)
                for t in range(1, 6):
                    a += r.normal(0, 0.25)
                    pts.append((cx + np.cos(a) * L * t / 5, cy + np.sin(a) * L * t / 5))
                d.line(pts, fill=255, width=1)
            cr[oy:oy + cell, ox:ox + cell] = np.asarray(im, F32) / 255
    gl = lerp(gl, col((0.75, 0.80, 0.80)), gblur(cr, 0.6) * 0.8)
    al = col((0.36, 0.38, 0.38))[None, None] * (1 + 0.25 * nb(h, w, 1, 40, s + 5))[..., None]
    c = lerp(gl, al * 1.0, frame)
    c = mix(c, (0.13, 0.20, 0.07), 0.5 * smooth(1.3, 2.4, nb(h, w, 10, 10, s + 6)) * (e < 10))
    return np.clip(shade(c, frame * 2, 0.6), 0, 1)


def _wood_boards(h, w, seed, base, n=6, wear=0.6, vert=False):
    s = seed
    if vert:
        P = np.arange(w)[None, :].repeat(h, 0).astype(F32)
        L = np.arange(h)[:, None].repeat(w, 1).astype(F32)
        size = w
    else:
        P = np.arange(h)[:, None].repeat(w, 1).astype(F32)
        L = np.arange(w)[None, :].repeat(h, 0).astype(F32)
        size = h
    bw = size / n
    bi = np.floor(P / bw).astype(int)
    r = np.random.default_rng(s)
    tv = r.uniform(0.7, 1.15, n + 1)[bi % n]
    fy = (P % bw) / bw
    gap = smooth(0.04, 0.0, fy) + smooth(0.96, 1.0, fy)
    grain = 0.5 + 0.5 * np.sin((P * 0.9 + nb(h, w, 40, 2, s + 1) * 14 * (1 if not vert else 1)) * 0.5 + nb(h, w, 2, 30, s + 2) * 4)
    c = col(base)[None, None] * (tv * (0.78 + 0.3 * grain) * (1 + 0.1 * n1(h, w, 1.4, s + 3)))[..., None]
    gray = smooth(0.2, 1.4, nb(h, w, 18, 18, s + 4)) * wear
    c = lerp(c, col((0.38, 0.35, 0.31)) * (0.7 + 0.3 * grain)[..., None], gray * 0.7)         # weathered grey wood
    c = lerp(c, col((0.02, 0.015, 0.01)), np.clip(gap, 0, 1) * 0.9)
    return c, grain * 0.6 - gap


def gen_boards():
    h = w = 512
    c, hg = _wood_boards(h, w, 3500, (0.36, 0.26, 0.15), n=5, wear=0.8)
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    for ny in (60, 440):                                         # rusty nails
        for nx in (24, 488):
            rr = np.hypot(X - nx, Y - ny)
            c = lerp(c, col((0.30, 0.14, 0.06)), smooth(5, 2.5, rr) * 0.9)
    c = weather(c, hg, 3501, grime=0.5, streak=0.6, moss=0.1, rust=0.0, dust=0.3)
    return np.clip(shade(c, hg, 0.8), 0, 1)


def gen_wood_dark():
    h = w = 512
    c, hg = _wood_boards(h, w, 3600, (0.20, 0.13, 0.08), n=4, wear=0.5, vert=True)
    c = weather(c, hg, 3601, grime=0.5, streak=0.5, moss=0.2, dust=0.3)
    return np.clip(shade(c, hg, 0.8), 0, 1)


def gen_metal_rust():
    """corrugated steel sheet"""
    h = w = 512
    s = 3700
    X = np.arange(w)[None, :].repeat(h, 0).astype(F32)
    wave = np.sin(X / w * TAU * 8)
    paint = np.clip(0.5 + 0.5 * nb(h, w, 12, 12, s), 0, 1)
    c = lerp(col((0.30, 0.34, 0.33)), col((0.46, 0.50, 0.50)), np.clip(0.5 + 0.5 * n1(h, w, 1.6, s + 1), 0, 1))
    rs = smooth(0.2, 1.5, nb(h, w, 14, 14, s + 2) + 0.6 * nb(h, w, 3, 3, s + 3) + 0.2 * (wave < -0.5))
    rc = lerp(col((0.28, 0.11, 0.04)), col((0.58, 0.30, 0.10)), np.clip(0.5 + 0.5 * n1(h, w, 1.2, s + 4), 0, 1))
    c = lerp(c, rc, rs * 0.92)
    c = c * (0.72 + 0.3 * (0.5 + 0.5 * wave))[..., None]
    c = weather(c, wave * 0.8, s + 5, grime=0.6, streak=0.9, moss=0.0, rust=0.2, dust=0.2, streak_len=120)
    return np.clip(c, 0, 1)


def gen_door():
    h = w = 512
    s = 3800
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    c = lerp(col((0.14, 0.24, 0.20)), col((0.22, 0.34, 0.28)), np.clip(0.5 + 0.5 * n1(h, w, 1.5, s), 0, 1))     # peeling green steel
    panel = smooth(8, 2, np.minimum(np.minimum(X - 64, 448 - X), np.minimum(Y - 48, 464 - Y)).astype(F32))
    hg = -panel * 1.5
    rs = smooth(0.3, 1.6, nb(h, w, 10, 10, s + 1) + 0.7 * nb(h, w, 2.5, 2.5, s + 2))
    rc = lerp(col((0.30, 0.12, 0.05)), col((0.55, 0.27, 0.09)), np.clip(0.5 + 0.5 * n1(h, w, 1.2, s + 3), 0, 1))
    c = lerp(c, rc, rs * 0.85)
    hnd = smooth(16, 8, np.hypot(X - 420, Y - 260))
    c = lerp(c, col((0.12, 0.12, 0.12)), hnd * 0.9)
    c = weather(c, hg, s + 4, grime=0.7, streak=0.9, rust=0.3, dust=0.2)
    return np.clip(shade(c, hg, 0.9), 0, 1)


def gen_roof():
    h = w = 512
    s = 3900
    c = lerp(col((0.10, 0.10, 0.10)), col((0.20, 0.20, 0.19)), np.clip(0.5 + 0.5 * n1(h, w, 1.6, s), 0, 1))
    gr = nb(h, w, 0.8, 0.8, s + 1)
    c = c * (1 + 0.35 * gr)[..., None]
    pud = smooth(1.2, 2.2, nb(h, w, 22, 22, s + 2))
    c = lerp(c, col((0.05, 0.07, 0.07)), pud * 0.8)
    c = mix(c, (0.15, 0.27, 0.07), 0.8 * smooth(0.9, 2.0, nb(h, w, 9, 9, s + 3) + 0.5 * nb(h, w, 2, 2, s + 4)))   # moss/weeds on the roof
    cr = np.clip(gblur(draw_cracks(h, w, s + 5, n=6, length=(0.1, 0.4), width=1.5), 0.6) * 1.7, 0, 1)
    c = c * (1 - 0.7 * cr)[..., None]
    return np.clip(shade(c, gr, 0.5), 0, 1)


# ---------------------------------------------------------------------------------------------- windows
def _window_alpha(seed, broken):
    """window sash with remnants of dirty glass.  alpha: 0 = missing pane."""
    h = w = 512
    r = np.random.default_rng(seed)
    im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = 2
    fw = 18 * S                                    # frame width
    # frame (flaking white paint over grey steel / wood)
    frame = Image.new('L', (w * S, h * S), 0)
    fd = ImageDraw.Draw(frame)
    fd.rectangle([0, 0, w * S - 1, fw], fill=255)
    fd.rectangle([0, h * S - fw - 1, w * S - 1, h * S - 1], fill=255)
    fd.rectangle([0, 0, fw, h * S - 1], fill=255)
    fd.rectangle([w * S - fw - 1, 0, w * S - 1, h * S - 1], fill=255)
    fd.rectangle([w * S // 2 - fw // 2, 0, w * S // 2 + fw // 2, h * S - 1], fill=255)
    fd.rectangle([0, h * S // 2 - fw // 2, w * S - 1, h * S // 2 + fw // 2], fill=255)
    fr = np.asarray(frame.resize((w, h), Image.LANCZOS), F32) / 255
    # glass panes: 4 panes
    glass = np.zeros((h, w), F32)
    panes = [(0, 0), (1, 0), (0, 1), (1, 1)]
    ga = np.zeros((h, w), F32)
    for (px, py) in panes:
        x0, y0 = px * w // 2 + 9, py * h // 2 + 9
        x1, y1 = (px + 1) * w // 2 - 9, (py + 1) * h // 2 - 9
        state = r.random()
        if broken:
            gone = state < 0.55
        else:
            gone = state < 0.12
        if not gone:
            ga[y0:y1, x0:x1] = 1.0
        else:                                      # shards left on the edge
            sh = Image.new('L', (w * S, h * S), 0)
            sd = ImageDraw.Draw(sh)
            for k in range(r.integers(2, 5)):
                side = r.integers(4)
                L = r.uniform(30, 80) * S
                if side == 0:
                    bx, by = r.uniform(x0, x1) * S, y0 * S
                    pts = [(bx, by), (bx + r.uniform(20, 50) * S, by), (bx + r.uniform(0, 30) * S, by + L)]
                elif side == 1:
                    bx, by = r.uniform(x0, x1) * S, y1 * S
                    pts = [(bx, by), (bx + r.uniform(20, 50) * S, by), (bx + r.uniform(0, 30) * S, by - L)]
                elif side == 2:
                    bx, by = x0 * S, r.uniform(y0, y1) * S
                    pts = [(bx, by), (bx, by + r.uniform(20, 50) * S), (bx + L, by + r.uniform(0, 30) * S)]
                else:
                    bx, by = x1 * S, r.uniform(y0, y1) * S
                    pts = [(bx, by), (bx, by + r.uniform(20, 50) * S), (bx - L, by + r.uniform(0, 30) * S)]
                sd.polygon(pts, fill=255)
            ga = np.maximum(ga, np.asarray(sh.resize((w, h), Image.LANCZOS), F32) / 255)
    # crack lines in intact panes
    cr = np.clip(gblur(draw_cracks(h, w, seed + 1, n=3, length=(0.1, 0.3), width=1.0), 0.5) * 1.6, 0, 1)
    dirt = smooth(0.4, 2.0, nb(h, w, 14, 14, seed + 2) + 0.6 * nb(h, w, 3, 40, seed + 3))
    gcol = lerp(col((0.16, 0.22, 0.23)), col((0.40, 0.45, 0.42)), np.clip(0.5 + 0.5 * nb(h, w, 30, 30, seed + 4), 0, 1))
    gcol = mix(gcol, (0.28, 0.26, 0.20), 0.55 * dirt)
    gcol = lerp(gcol, col((0.8, 0.85, 0.85)), cr * 0.9)
    galpha = ga * np.clip(0.38 + 0.38 * dirt + 0.4 * cr, 0, 0.88)
    # frame colour
    flake = smooth(0.3, 1.4, nb(h, w, 6, 6, seed + 5) + 0.6 * nb(h, w, 1.5, 1.5, seed + 6))
    fc = lerp(col((0.62, 0.62, 0.58)), col((0.22, 0.20, 0.17)), flake)
    fc = mix(fc, (0.42, 0.18, 0.07), 0.5 * smooth(0.9, 2.0, nb(h, w, 4, 4, seed + 7)))
    fc = fc * (1 - 0.35 * smooth(0.5, 2.2, nb(h, w, 2, 50, seed + 8)))[..., None]
    fc = shade(fc, fr * 2 + flake, 0.6)
    a = np.maximum(fr, galpha)
    c = lerp(gcol, fc, np.clip(fr / np.maximum(a, 1e-3), 0, 1))
    return pack(np.clip(c, 0, 1), a)


def gen_window_a():
    return _window_alpha(4000, False)


def gen_window_b():
    return _window_alpha(4100, True)


def gen_interior_dark():
    """what you see through a window of an abandoned room: dark wall, ceiling line, hint of debris"""
    h = w = 256
    s = 4200
    Y = np.arange(h)[:, None].repeat(w, 1).astype(F32)
    c = lerp(col((0.035, 0.036, 0.035)), col((0.11, 0.105, 0.095)), np.clip(0.35 + 0.5 * n1(h, w, 1.8, s), 0, 1))
    c = c * (0.5 + 0.8 * smooth(0, h, Y) ** 1.5)[..., None]
    c = mix(c, (0.20, 0.22, 0.20), 0.25 * smooth(1.4, 2.4, nb(h, w, 14, 14, s + 1)) * (Y > h * 0.6))
    return np.clip(c, 0, 1)


# --------------------------------------------------------------------------------------------- interior
def gen_floor_tile():
    h = w = 512
    s = 4300
    r = np.random.default_rng(s)
    n = 8
    sl = h // n
    Y, X = np.mgrid[0:h, 0:w]
    ti = (X // sl) + n * (Y // sl)
    chk = ((X // sl + Y // sl) % 2).astype(F32)
    e = np.minimum(np.minimum(X % sl, sl - 1 - X % sl), np.minimum(Y % sl, sl - 1 - Y % sl)).astype(F32)
    j = smooth(0.8, 3.0, e)
    base = lerp(col((0.30, 0.29, 0.25)), col((0.52, 0.50, 0.44)), chk) * r.uniform(0.85, 1.1, n * n)[ti][..., None]
    c = lerp(col((0.10, 0.09, 0.07)), base, j)
    c = mix(c, (0.18, 0.15, 0.10), 0.7 * smooth(0.5, 2.0, nb(h, w, 22, 22, s + 1)))                 # mud / water stains
    cr = np.clip(gblur(draw_cracks(h, w, s + 2, n=5, length=(0.1, 0.35), width=1.4), 0.6) * 1.7, 0, 1)
    c = c * (1 - 0.75 * cr)[..., None]
    c = mix(c, (0.12, 0.2, 0.06), 0.5 * smooth(1.5, 2.5, nb(h, w, 6, 6, s + 3)))
    return np.clip(shade(c, j * 1.2 - cr, 0.7), 0, 1)


def gen_floor_wood():
    h = w = 512
    c, hg = _wood_boards(h, w, 4400, (0.30, 0.20, 0.11), n=8, wear=0.9)
    c = mix(c, (0.08, 0.06, 0.04), 0.7 * smooth(0.6, 2.0, nb(h, w, 22, 22, 4401)))
    c = mix(c, (0.12, 0.2, 0.06), 0.4 * smooth(1.5, 2.5, nb(h, w, 8, 8, 4402)))
    return np.clip(shade(c, hg, 0.8), 0, 1)


def gen_wallpaper():
    h = w = 512
    s = 4500
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    base = col((0.48, 0.42, 0.30))
    stripes = 0.5 + 0.5 * np.sin(X / w * TAU * 16)
    pat = smooth(0.62, 0.7, 0.5 + 0.5 * np.sin(X / w * TAU * 8) * np.sin(Y / h * TAU * 8))
    c = base[None, None] * (0.85 + 0.14 * stripes + 0.10 * pat)[..., None]
    peel = smooth(0.2, 0.9, nb(h, w, 30, 40, s) + 0.5 * nb(h, w, 8, 8, s + 1) - 0.2)
    c = lerp(c, col((0.40, 0.38, 0.34)) * (1 + 0.2 * nb(h, w, 1, 1, s + 2))[..., None], peel)
    c = mix(c, (0.12, 0.10, 0.07), 0.8 * smooth(1.0, 2.2, nb(h, w, 5, 90, s + 3)))                   # water damage streaks
    c = mix(c, (0.12, 0.2, 0.07), 0.5 * smooth(1.6, 2.6, nb(h, w, 10, 10, s + 4)))                    # mould
    return np.clip(shade(c, -peel * 1.5, 0.8), 0, 1)


def gen_ceiling():
    h = w = 512
    s = 4600
    Y, X = np.mgrid[0:h, 0:w].astype(F32)
    t = np.minimum(np.minimum(X % 128, 127 - X % 128), np.minimum(Y % 128, 127 - Y % 128))
    j = smooth(1.0, 4.0, t)
    c = col((0.50, 0.49, 0.45))[None, None] * (1 + 0.15 * n1(h, w, 1.5, s) + 0.1 * nb(h, w, 0.8, 0.8, s + 1))[..., None]
    c = lerp(col((0.12, 0.11, 0.10)), c, j)
    c = mix(c, (0.16, 0.12, 0.07), 0.9 * smooth(0.8, 2.0, nb(h, w, 26, 26, s + 2)))
    c = mix(c, (0.10, 0.15, 0.07), 0.5 * smooth(1.3, 2.4, nb(h, w, 9, 9, s + 3)))
    return np.clip(shade(c, j, 0.6), 0, 1)


GEN = dict(
    ru_asphalt=gen_asphalt, ru_road_yellow=gen_road_yellow, ru_road_dash=gen_road_dash, ru_road_edge=gen_road_edge,
    ru_crosswalk=gen_crosswalk, ru_sidewalk=gen_sidewalk, ru_curb=gen_curb, ru_dirt=gen_dirt, ru_gravel=gen_gravel,
    ru_leaflitter=gen_leaflitter, ru_moss=gen_moss, ru_grass=gen_grass, ru_parkpath=gen_parkpath, ru_water=gen_water,
    ru_brick_red=gen_brick_red, ru_brick_brown=gen_brick_brown, ru_concrete=gen_concrete, ru_stucco=gen_stucco,
    ru_glasswall=gen_glasswall, ru_boards=gen_boards, ru_wood_dark=gen_wood_dark, ru_metal_rust=gen_metal_rust,
    ru_door=gen_door, ru_roof=gen_roof, ru_window_a=gen_window_a, ru_window_b=gen_window_b, ru_interior_dark=gen_interior_dark,
    ru_floor_tile=gen_floor_tile, ru_floor_wood=gen_floor_wood, ru_wallpaper=gen_wallpaper, ru_ceiling=gen_ceiling,
)
ALPHA_NAMES = {'ru_window_a', 'ru_window_b', 'ru_water'}
