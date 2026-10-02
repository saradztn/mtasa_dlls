# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# tex.py - procedural textures of the post-apocalyptic city.  Every generator returns FINAL diffuse (float HxWx3, or
# HxWx4 for alpha textures): San Andreas has no normal maps, so relief / AO / grime are baked into the colour.
# Tiling textures are periodic.  Weathering recipe shared by all surfaces: multi-scale mottling, vertical rain streaks,
# crack networks (warped Worley edges), moss / weeds in the damp places, rust bloom on metal, dust drifts.
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from lib.noise import fnoise, bnoise, worley, smooth, scratches, white, FONT_B, FONT_R
from .ctex import shade
from .tex_base import col, gblur, pack, _planks, _cluster, _blade_img, _leaf_poly, TAU

NAMES = [
    # ground
    'af_asphalt', 'af_road', 'af_crosswalk', 'af_sidewalk', 'af_curb', 'af_gravel', 'af_dirt', 'af_grass', 'af_moss',
    # structure
    'af_concrete', 'af_panel', 'af_brick', 'af_plaster_a', 'af_plaster_b', 'af_plaster_c', 'af_glass', 'af_glass_broken',
    'af_frame', 'af_interior', 'af_rust', 'af_steel', 'af_roofing', 'af_corrugated', 'af_wood', 'af_bark',
    # props / vehicles
    'af_car_red', 'af_car_blue', 'af_car_white', 'af_car_green', 'af_car_yellow', 'af_car_grey', 'af_tire',
    'af_sign_street', 'af_sign_stop', 'af_billboard', 'af_container', 'af_barrier',
    # alpha
    'af_weeds', 'af_dead_grass', 'af_ivy', 'af_leaf', 'af_leaf_dead', 'af_wire',
]
IDX = {n: i for i, n in enumerate(NAMES)}
ALPHA = {IDX[n] for n in ('af_weeds', 'af_dead_grass', 'af_ivy', 'af_leaf', 'af_leaf_dead', 'af_wire')}
CATEGORY = {}
for _n in NAMES[:9]:
    CATEGORY[_n] = 'ground'
for _n in NAMES[9:25]:
    CATEGORY[_n] = 'struct'
for _n in NAMES[25:37]:
    CATEGORY[_n] = 'props'
for _n in NAMES[37:]:
    CATEGORY[_n] = 'flora'


# ------------------------------------------------------------------------------------------------ helpers
def lerp(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2:
        t = t[..., None]
    return a + (b - a) * t


def tile(rgb, h, w):
    return np.broadcast_to(np.array(rgb, np.float32), (h, w, 3)).copy()


def warp(a, amp, seed, sc=14):
    """periodic displacement of a 2-d (or 3-d) array by smooth noise (keeps tiling)"""
    h, w = a.shape[:2]
    dx = np.rint(bnoise(h, w, sc, sc, seed) * amp).astype(int)
    dy = np.rint(bnoise(h, w, sc, sc, seed + 1) * amp).astype(int)
    Y, X = np.mgrid[0:h, 0:w]
    return a[(Y + dy) % h, (X + dx) % w]


def cracks(h, w, cells, seed, width=0.05, amp=7):
    F1, F2, _ = worley(h, w, cells, cells, seed)
    m = 1 - smooth(0.0, width, (F2 - F1))
    return np.clip(warp(m.astype(np.float32), amp, seed + 7), 0, 1)


def rain(h, w, seed, strength=0.3, sx=3.0, sy=90.0):
    """vertical rain-streak darkening 0..1"""
    s = bnoise(h, w, sx, sy, seed) + 0.5 * bnoise(h, w, sx * 2.2, sy * 0.5, seed + 1)
    return smooth(0.2, 2.2, s) * strength


def patches(h, w, seed, size, lo=0.8, hi=1.6):
    return smooth(lo, hi, bnoise(h, w, size, size, seed) + 0.4 * fnoise(h, w, 2.0, seed + 1))


def speckle(h, w, seed, sigma=0.7):
    s = gblur(white(h, w, seed).astype(np.float32), sigma)
    return (s - s.mean()) / (s.std() + 1e-9)


def moss_over(c, mask, seed, strength=0.8):
    h, w = mask.shape
    m = np.clip(mask, 0, 1) * (0.55 + 0.45 * smooth(-0.5, 1.2, bnoise(h, w, 1.6, 1.6, seed)))
    mc = lerp(tile((0.07, 0.14, 0.04), h, w), tile((0.20, 0.30, 0.08), h, w), smooth(-1, 1.5, bnoise(h, w, 4, 4, seed + 2)))
    return lerp(c, mc, m * strength)


def finish(c, hgt, k=1.4):
    return np.clip(shade(c, hgt * 2.0, k), 0, 1)


# ------------------------------------------------------------------------------------------------ ground
def _asphalt(seed, h=512, w=512, tone=0.205):
    n1 = fnoise(h, w, 1.4, seed)
    sp = speckle(h, w, seed + 1, 0.8)
    c = tile((tone, tone * 0.98, tone * 0.95), h, w) * (1 + 0.13 * n1 + 0.20 * sp)[..., None]
    stones = smooth(2.3, 3.2, speckle(h, w, seed + 2, 0.6))
    c = lerp(c, tile((0.46, 0.44, 0.40), h, w), stones * 0.55)
    c *= (1 + 0.20 * (patches(h, w, seed + 3, 40, 0.9, 1.5) - 0.5))[..., None]            # re-surfaced patches
    c = lerp(c, c * 0.45, patches(h, w, seed + 4, 22, 1.3, 2.0)[..., None][..., 0] * 0.55)        # oil
    dust = patches(h, w, seed + 5, 34, 1.2, 2.1)
    c = lerp(c, tile((0.40, 0.36, 0.29), h, w), dust * 0.40)                                  # sand / dust drifts
    cm = np.clip(cracks(h, w, 5, seed + 6, 0.035) + 0.7 * cracks(h, w, 13, seed + 8, 0.03), 0, 1)
    edge = gblur(cm, 1.6)
    c *= (1 - 0.88 * cm)[..., None]
    c = lerp(c, c * 1.35, np.clip(edge - cm, 0, 1)[..., None] * 0.6)                          # lighter crumbled lips
    weeds = smooth(0.12, 0.45, gblur(cm, 2.4)) * smooth(-0.2, 0.9, bnoise(h, w, 3, 3, seed + 9))
    c = lerp(c, lerp(tile((0.10, 0.20, 0.05), h, w), tile((0.36, 0.42, 0.12), h, w), smooth(-1, 1, bnoise(h, w, 1.3, 1.3, seed + 10))), weeds[..., None] * 0.85)
    hgt = -cm * 0.8 + 0.12 * sp + 0.2 * n1
    return finish(c, hgt, 1.1), cm


def gen_asphalt():
    return _asphalt(1001)[0]


def gen_road():
    """full road cross section: u across 12 m, v along 12 m.  4 lanes: double yellow centre, dashed white, solid edges"""
    h = w = 512
    c, cm = _asphalt(1101, tone=0.19)
    X = (np.arange(w)[None, :] + 0.5) / w * 12.0 - 6.0              # metres from the centre line
    Y = (np.arange(h)[:, None] + 0.5) / h * 12.0
    line = np.zeros((h, w), np.float32)
    yellow = np.zeros((h, w), np.float32)
    for xs in (-0.14, 0.14):
        yellow = np.maximum(yellow, (np.abs(X - xs) < 0.055).astype(np.float32) * np.ones((h, 1), np.float32))
    for xs in (-3.0, 3.0):
        dash = ((Y % 12.0) < 4.0).astype(np.float32)
        line = np.maximum(line, (np.abs(X - xs) < 0.07).astype(np.float32) * dash)
    for xs in (-5.62, 5.62):
        line = np.maximum(line, (np.abs(X - xs) < 0.08).astype(np.float32) * np.ones((h, 1), np.float32))
    wear = smooth(-0.8, 1.0, bnoise(h, w, 6, 6, 1111) + 0.5 * fnoise(h, w, 1.2, 1112) + 0.6 * speckle(h, w, 1113, 1.0))
    wear *= (1 - 0.8 * cm)
    edge = gblur(line, 0.7)
    edgey = gblur(yellow, 0.7)
    c = lerp(c, tile((0.62, 0.62, 0.58), h, w), np.clip(edge * wear * 0.78, 0, 1)[..., None])
    c = lerp(c, tile((0.66, 0.50, 0.10), h, w), np.clip(edgey * wear * 0.82, 0, 1)[..., None])
    tyre = smooth(0.2, 1.0, bnoise(h, w, 40, 400, 1115))                               # dark tyre lanes
    tyre_m = (np.exp(-((np.abs(X) - 1.6) ** 2) / 0.5) + np.exp(-((np.abs(X) - 4.4) ** 2) / 0.5))
    c *= (1 - 0.18 * tyre * tyre_m)[..., None]
    return np.clip(c, 0, 1)


def gen_crosswalk():
    h = w = 512
    c, cm = _asphalt(1201, tone=0.19)
    X = (np.arange(w)[None, :] + 0.5) / w * 4.0                     # 4 m wide tile, stripes 0.5 m wide every 1 m
    stripe = ((X % 1.0) < 0.5).astype(np.float32) * np.ones((h, 1), np.float32)
    wear = smooth(-0.9, 0.9, bnoise(h, w, 8, 8, 1211) + 0.5 * fnoise(h, w, 1.2, 1212) + 0.5 * speckle(h, w, 1213, 1.0)) * (1 - 0.8 * cm)
    c = lerp(c, tile((0.64, 0.64, 0.60), h, w), np.clip(gblur(stripe, 0.8) * wear * 0.8, 0, 1)[..., None])
    return np.clip(c, 0, 1)


def gen_sidewalk():
    h = w = 512
    n1 = fnoise(h, w, 1.5, 1301)
    sp = speckle(h, w, 1302, 0.9)
    Y, X = np.mgrid[0:h, 0:w]
    sl = 256
    cx, cy = X % sl, Y % sl
    sid = (X // sl) + 2 * (Y // sl)
    r = np.random.default_rng(1303)
    bv = r.uniform(0.86, 1.12, 8)[sid]
    c = tile((0.50, 0.485, 0.45), h, w) * (bv * (1 + 0.10 * n1 + 0.10 * sp))[..., None]
    e = np.minimum(np.minimum(cx, sl - 1 - cx), np.minimum(cy, sl - 1 - cy)).astype(np.float32) + bnoise(h, w, 3, 3, 1304) * 1.2
    joint = smooth(1.0, 5.0, e)
    c *= (0.35 + 0.65 * joint)[..., None]
    cm = np.clip(cracks(h, w, 3, 1305, 0.04) + 0.6 * cracks(h, w, 8, 1306, 0.03), 0, 1)
    c *= (1 - 0.8 * cm)[..., None]
    c *= (1 - 0.18 * patches(h, w, 1307, 30, 0.9, 1.8))[..., None]                       # stains
    damp = np.clip(gblur(cm, 3.0) * 2.4 + (1 - joint) * 0.9, 0, 1) * smooth(-0.6, 0.8, bnoise(h, w, 4, 4, 1308))
    c = moss_over(c, damp, 1309, 0.9)
    weeds = smooth(0.3, 0.7, gblur(cm + (1 - joint), 2.0)) * smooth(0.3, 1.1, bnoise(h, w, 3, 3, 1310))
    c = lerp(c, lerp(tile((0.12, 0.22, 0.05), h, w), tile((0.34, 0.40, 0.11), h, w), smooth(-1, 1, bnoise(h, w, 1.2, 1.2, 1311))), weeds[..., None] * 0.8)
    return finish(c, joint * 1.0 - cm * 0.8 + 0.1 * sp, 1.0)


def gen_curb():
    h = w = 256
    n1 = fnoise(h, w, 1.5, 1401)
    c = tile((0.52, 0.51, 0.48), h, w) * (1 + 0.10 * n1 + 0.14 * speckle(h, w, 1402))[..., None]
    c *= (1 - 0.25 * patches(h, w, 1403, 20, 0.8, 1.6))[..., None]
    cm = cracks(h, w, 3, 1404, 0.04)
    c *= (1 - 0.75 * cm)[..., None]
    c = moss_over(c, smooth(0.3, 1.2, bnoise(h, w, 8, 8, 1405)) * 0.5, 1406, 0.7)
    return finish(c, -cm + 0.15 * n1, 1.0)


def gen_gravel():
    h = w = 512
    F1, F2, ID = worley(h, w, 40, 40, 1501)
    ID = ID.astype(np.float32)
    r = np.random.default_rng(1502)
    base = r.uniform(0.25, 0.62, 2000).astype(np.float32)
    tn = r.normal(0, 0.008, (2000, 3)).astype(np.float32)
    k = (ID * 1999).astype(int)
    c = tile((1, 1, 1), h, w) * base[k][..., None] * np.array([1.0, 0.97, 0.92], np.float32) + tn[k]
    gap = smooth(0.0, 0.35, F2 - F1)
    c *= (0.25 + 0.75 * gap)[..., None]
    c *= (1 - 0.3 * patches(h, w, 1503, 25, 0.8, 1.6))[..., None]
    c = lerp(c, tile((0.40, 0.36, 0.29), h, w), patches(h, w, 1504, 18, 1.0, 1.9)[..., None][..., 0] * 0.35)
    return finish(c, gap * 1.5 + F1 * -1.2, 1.0)


def gen_dirt():
    h = w = 512
    n1 = fnoise(h, w, 1.8, 1601)
    c = tile((0.27, 0.20, 0.13), h, w) * (1 + 0.20 * n1 + 0.2 * speckle(h, w, 1602, 1.0))[..., None]
    c = lerp(c, tile((0.38, 0.30, 0.20), h, w), patches(h, w, 1603, 30, 0.9, 1.8)[..., None][..., 0] * 0.5)
    pud = patches(h, w, 1604, 40, 1.4, 2.0)
    c = lerp(c, tile((0.10, 0.08, 0.06), h, w), pud[..., None] * 0.6)
    cm = cracks(h, w, 7, 1605, 0.05) * patches(h, w, 1606, 60, 0.4, 1.0)
    c *= (1 - 0.6 * cm)[..., None]
    stones = smooth(2.4, 3.2, speckle(h, w, 1607, 0.7))
    c = lerp(c, tile((0.5, 0.47, 0.42), h, w), stones * 0.6)
    c = moss_over(c, patches(h, w, 1608, 20, 1.4, 2.0) * 0.5, 1609, 0.6)
    return finish(c, n1 * 0.5 - cm, 1.0)


def gen_grass():
    h = w = 512
    s = 1701
    n1, n2 = fnoise(h, w, 1.1, s), bnoise(h, w, 0.9, 3.2, s + 1)
    n3, n4 = bnoise(h, w, 38, 38, s + 2), bnoise(h, w, 9, 9, s + 3)
    t = np.clip(0.5 + 0.22 * n3 + 0.16 * n4 + 0.10 * n1, 0, 1)
    dark, mid, light = col((0.06, 0.13, 0.03)), col((0.17, 0.29, 0.07)), col((0.38, 0.46, 0.14))
    c = np.where((t < 0.5)[..., None], lerp(dark, mid, smooth(0.1, 0.5, t)), lerp(mid, light, smooth(0.5, 0.95, t)))
    c = c * (0.55 + 0.7 * (0.5 + 0.5 * n2))[..., None]
    dry = smooth(0.9, 1.9, bnoise(h, w, 16, 16, s + 4) + 0.5 * fnoise(h, w, 1.5, s + 5))           # dead straw areas
    straw = lerp(tile((0.36, 0.30, 0.15), h, w), tile((0.55, 0.48, 0.26), h, w), smooth(-1, 1, n2))
    c = lerp(c, straw, dry[..., None] * 0.65)
    sc = scratches(h, w, 220, 6, 18, s + 6, angle=-1.35, spread=0.35, width=1.0)
    c = lerp(c, tile((0.55, 0.50, 0.30), h, w), sc[..., None] * 0.30)
    bare = smooth(1.6, 2.4, bnoise(h, w, 20, 20, s + 7))
    c = lerp(c, tile((0.24, 0.18, 0.11), h, w), bare[..., None] * 0.6)
    return finish(c, n2 * 0.4 + 0.2 * n4, 0.8)


def gen_moss():
    h = w = 256
    n = fnoise(h, w, 1.3, 1801)
    c = lerp(tile((0.05, 0.11, 0.03), h, w), tile((0.24, 0.36, 0.10), h, w), smooth(-1.2, 1.4, n + 0.5 * bnoise(h, w, 1.5, 1.5, 1802)))
    c *= (0.7 + 0.5 * speckle(h, w, 1803, 0.7) * 0.4 + 0.3)[..., None]
    return finish(c, speckle(h, w, 1803, 0.9) * 0.4, 1.0)


# ------------------------------------------------------------------------------------------------ structure
def _concrete_base(h, w, seed, tone=(0.47, 0.465, 0.44)):
    n1 = fnoise(h, w, 1.6, seed)
    c = tile(tone, h, w) * (1 + 0.11 * n1 + 0.12 * speckle(h, w, seed + 1, 0.9) + 0.06 * bnoise(h, w, 20, 20, seed + 2))[..., None]
    pores = smooth(2.2, 3.2, speckle(h, w, seed + 3, 0.6))
    c *= (1 - 0.35 * pores)[..., None]
    return c, n1


def gen_concrete():
    h = w = 512
    c, n1 = _concrete_base(h, w, 2001)
    Y, X = np.mgrid[0:h, 0:w]
    seam = np.minimum(np.abs(((Y - 2) % 256) - 0), np.abs((X % 256))).astype(np.float32)
    seam = smooth(0, 3.5, np.minimum(Y % 256, X % 256).astype(np.float32))
    c *= (0.45 + 0.55 * seam)[..., None]
    for ty in (64, 192):                                             # form-tie holes
        for tx in (64, 192):
            for ox in (0, 256):
                for oy in (0, 256):
                    d = np.hypot(X - (tx + ox), Y - (ty + oy))
                    c *= (1 - 0.55 * np.exp(-(d / 3.0) ** 2))[..., None]
    st = rain(h, w, 2005, 0.45)
    c *= (1 - st)[..., None]
    rs = rain(h, w, 2007, 1.0, 2.0, 60) * smooth(0.5, 1.0, bnoise(h, w, 25, 25, 2009) + 0.8)    # rust streaks from rebar
    c = lerp(c, tile((0.33, 0.17, 0.08), h, w), rs[..., None] * 0.55)
    cm = np.clip(cracks(h, w, 4, 2011, 0.03) * patches(h, w, 2012, 60, 0.0, 0.9), 0, 1)
    c *= (1 - 0.8 * cm)[..., None]
    c = moss_over(c, smooth(0.5, 1.5, rain(h, w, 2013, 1.5, 3, 70)) * 0.5, 2014, 0.7)
    return finish(c, n1 * 0.4 - cm + seam * 0.8, 1.0)


def gen_panel():
    h = w = 512
    c, n1 = _concrete_base(h, w, 2101, (0.38, 0.385, 0.38))
    Y, X = np.mgrid[0:h, 0:w]
    rib = 0.5 + 0.5 * np.sin(Y / h * TAU * 16)
    c *= (0.86 + 0.14 * rib)[..., None]
    seam = smooth(0, 3.0, np.minimum(X % 256, Y % 512).astype(np.float32))
    c *= (0.4 + 0.6 * seam)[..., None]
    c *= (1 - rain(h, w, 2103, 0.55))[..., None]
    c = lerp(c, tile((0.30, 0.18, 0.10), h, w), (rain(h, w, 2105, 1.0, 2, 70) * smooth(0.6, 1.0, bnoise(h, w, 30, 30, 2106) + 0.7))[..., None] * 0.5)
    c *= (1 - 0.2 * patches(h, w, 2107, 24, 0.9, 1.7))[..., None]
    return finish(c, rib * 0.3 + seam * 0.5, 1.0)


def gen_brick():
    h = w = 512
    r = np.random.default_rng(2201)
    rows, per = 24, 8
    bh = h // rows
    bw = w // per
    Y, X = np.mgrid[0:h, 0:w]
    ry = Y // bh
    off = (ry % 2) * (bw // 2)
    xx = (X + off) % w
    bx = xx // bw
    cx = xx % bw
    cy = Y % bh
    bid = (ry * per + bx) % 600
    bval = r.uniform(0.62, 1.22, 600).astype(np.float32)
    btint = r.normal(0, 1, (600, 3)).astype(np.float32) * np.array([0.04, 0.025, 0.02], np.float32)
    base = np.array([0.46, 0.20, 0.13], np.float32)
    c = base[None, None] * (bval[bid] * (1 + 0.20 * fnoise(h, w, 1.4, 2202) + 0.18 * speckle(h, w, 2203, 0.9)))[..., None] + btint[bid]
    dark = (r.random(600) < 0.12).astype(np.float32)[bid]                    # over-burnt dark bricks
    c = lerp(c, tile((0.20, 0.10, 0.08), h, w), dark[..., None][..., 0] * 0.6)
    e = np.minimum(np.minimum(cx, bw - 1 - cx), np.minimum(cy, bh - 1 - cy)).astype(np.float32) + bnoise(h, w, 2.5, 2.5, 2204) * 0.7
    mort = smooth(0.8, 2.6, e)
    c = lerp(tile((0.50, 0.48, 0.43), h, w) * (1 + 0.15 * speckle(h, w, 2205, 0.8))[..., None], c, mort[..., None])
    spall = (r.random(600) < 0.05).astype(np.float32)[bid] * smooth(2, 6, e)
    c = lerp(c, tile((0.16, 0.10, 0.08), h, w), spall[..., None] * 0.7)
    eff = smooth(1.0, 2.0, bnoise(h, w, 8, 22, 2206) + 0.4 * fnoise(h, w, 1.5, 2207)) * mort    # white salt
    c = lerp(c, tile((0.62, 0.60, 0.55), h, w), eff[..., None] * 0.35)
    c *= (1 - rain(h, w, 2208, 0.55))[..., None]
    c *= (1 - 0.35 * patches(h, w, 2209, 28, 1.1, 1.9))[..., None]                           # soot
    c = moss_over(c, smooth(0.8, 1.8, rain(h, w, 2210, 1.6, 3, 60)) * 0.45, 2211, 0.7)
    cm = np.clip(cracks(h, w, 3, 2212, 0.025) * patches(h, w, 2213, 60, 0.2, 1.0), 0, 1)
    c *= (1 - 0.7 * cm)[..., None]
    return finish(c, mort * 1.5 - spall * 1.5 - cm, 1.1)


def _plaster(seed, paint, under, h=512, w=512, peel=0.30):
    n1 = fnoise(h, w, 1.7, seed)
    c = tile(paint, h, w) * (1 + 0.07 * n1 + 0.05 * speckle(h, w, seed + 1, 0.9))[..., None]
    c *= (1 - rain(h, w, seed + 2, 0.5))[..., None]
    mask = smooth(0.9 - peel * 0.8, 1.35 - peel * 0.8, bnoise(h, w, 18, 18, seed + 3) + 0.6 * bnoise(h, w, 6, 6, seed + 4) + 0.2 * rain(h, w, seed + 5, 2.0))
    ud = tile(under, h, w) * (1 + 0.15 * speckle(h, w, seed + 6, 0.9) + 0.1 * fnoise(h, w, 1.5, seed + 7))[..., None]
    edge = np.clip(gblur(mask, 1.4) - mask, 0, 1)
    c = lerp(c, ud, mask[..., None])
    c = lerp(c, c * 1.3 + 0.05, np.clip(edge * 3, 0, 1)[..., None] * 0.7)                    # lifted paint lip
    c *= (1 - 0.5 * np.clip(gblur(np.roll(np.roll(mask, 2, 0), 2, 1), 1.2) - mask, 0, 1))[..., None]
    cm = np.clip(cracks(h, w, 4, seed + 8, 0.025) * patches(h, w, seed + 9, 50, 0.2, 1.0), 0, 1)
    c *= (1 - 0.7 * cm)[..., None]
    c *= (1 - 0.3 * patches(h, w, seed + 10, 26, 1.1, 1.9))[..., None]
    c = moss_over(c, smooth(0.8, 1.8, rain(h, w, seed + 11, 1.6, 3, 70)) * 0.5, seed + 12, 0.65)
    return finish(c, -mask * 1.0 - cm + n1 * 0.2, 1.2)


def gen_plaster_a():
    return _plaster(2301, (0.74, 0.69, 0.55), (0.40, 0.38, 0.35))


def gen_plaster_b():
    return _plaster(2401, (0.40, 0.55, 0.50), (0.40, 0.30, 0.22))


def gen_plaster_c():
    return _plaster(2501, (0.55, 0.30, 0.20), (0.45, 0.43, 0.40), peel=0.25)


def gen_glass():
    h = w = 256
    Y = np.broadcast_to(np.arange(h)[:, None] / h, (h, w))
    X = np.broadcast_to(np.arange(w)[None, :] / w, (h, w))
    top, bot = tile((0.30, 0.36, 0.38), h, w), tile((0.06, 0.08, 0.09), h, w)
    c = lerp(top, bot, np.clip(Y * 1.2, 0, 1))
    diag = smooth(0.0, 0.04, np.abs((X + Y * 0.8) % 0.55 - 0.27) - 0.10)
    c = c * (0.85 + 0.15 * diag)[..., None] + 0.05 * (1 - diag)[..., None]
    dirt = smooth(0.3, 1.8, bnoise(h, w, 20, 20, 2601) + 0.7 * rain(h, w, 2602, 2.0, 3, 50))
    c = lerp(c, tile((0.25, 0.22, 0.17), h, w), dirt[..., None] * 0.55)
    return np.clip(c, 0, 1)


def gen_glass_broken():
    h = w = 256
    c = gen_glass() * 0.8
    im = Image.new('L', (w * 2, h * 2), 0)
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(2701)
    for _ in range(3):                                                # spider web cracks
        cx, cy = r.uniform(0.2, 0.8) * w * 2, r.uniform(0.2, 0.8) * h * 2
        nr = r.integers(7, 12)
        angs = np.sort(r.uniform(0, TAU, nr))
        for a in angs:
            L = r.uniform(0.25, 0.7) * w * 2
            pts = [(cx, cy)]
            for k in range(1, 6):
                aa = a + r.normal(0, 0.06)
                pts.append((cx + np.cos(aa) * L * k / 5, cy + np.sin(aa) * L * k / 5))
            d.line(pts, fill=255, width=2)
        for rr in (0.05, 0.1, 0.18, 0.3):
            pts = [(cx + np.cos(a) * rr * w * 2 * r.uniform(0.85, 1.15), cy + np.sin(a) * rr * w * 2 * r.uniform(0.85, 1.15)) for a in angs]
            d.line(pts + [pts[0]], fill=200, width=1)
    m = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    c = lerp(c, tile((0.78, 0.82, 0.84), h, w), np.clip(m * 1.4, 0, 1)[..., None] * 0.75)
    hole = smooth(1.1, 1.5, bnoise(h, w, 22, 22, 2703))                  # missing shards show the dark room
    c = lerp(c, tile((0.015, 0.015, 0.018), h, w), hole[..., None] * 0.95)
    return np.clip(c, 0, 1)


def gen_frame():
    h = w = 128
    n = fnoise(h, w, 1.5, 2801)
    c = tile((0.62, 0.62, 0.58), h, w) * (1 + 0.1 * n + 0.12 * speckle(h, w, 2802))[..., None]
    c *= (1 - 0.35 * patches(h, w, 2803, 14, 0.7, 1.4))[..., None]
    rust = smooth(0.5, 1.4, bnoise(h, w, 6, 6, 2804) + 0.5 * speckle(h, w, 2805, 1.2))
    c = lerp(c, tile((0.38, 0.20, 0.09), h, w), rust[..., None] * 0.7)
    return finish(c, n * 0.3, 0.8)


def gen_interior():
    h = w = 128
    n = fnoise(h, w, 1.5, 2901)
    c = tile((0.050, 0.047, 0.045), h, w) * (1 + 0.5 * n)[..., None]
    Y = np.broadcast_to(np.arange(h)[:, None] / h, (h, w))
    c *= (1.0 + 0.8 * smooth(0.55, 1.0, Y))[..., None]
    return np.clip(c, 0, 1)


def gen_rust():
    h = w = 512
    n1, n2 = fnoise(h, w, 1.6, 3001), fnoise(h, w, 1.1, 3002)
    base = lerp(tile((0.30, 0.15, 0.07), h, w), tile((0.55, 0.28, 0.10), h, w), smooth(-1.3, 1.3, n1))
    pits = smooth(1.8, 2.8, speckle(h, w, 3003, 0.8))
    c = base * (1 + 0.25 * n2 + 0.2 * speckle(h, w, 3004, 0.8))[..., None]
    c = lerp(c, tile((0.12, 0.07, 0.04), h, w), pits[..., None] * 0.7)
    flake = smooth(1.1, 1.6, bnoise(h, w, 14, 14, 3005))                     # remains of paint
    c = lerp(c, tile((0.30, 0.34, 0.30), h, w) * (1 + 0.2 * n2)[..., None], flake[..., None] * 0.65)
    c *= (1 - rain(h, w, 3006, 0.35, 2, 70))[..., None]
    return finish(c, n1 * 0.6 + pits * -1.0, 1.2)


def gen_steel():
    h = w = 256
    n = fnoise(h, w, 1.5, 3101)
    c = tile((0.22, 0.23, 0.24), h, w) * (1 + 0.15 * n + 0.15 * speckle(h, w, 3102, 0.8))[..., None]
    sc = scratches(h, w, 90, 20, 90, 3103, spread=0.5)
    c = lerp(c, tile((0.45, 0.46, 0.46), h, w), sc[..., None] * 0.4)
    rust = smooth(1.0, 1.8, bnoise(h, w, 9, 9, 3104) + 0.4 * rain(h, w, 3105, 2, 3, 60))
    c = lerp(c, tile((0.34, 0.18, 0.08), h, w) * (1 + 0.3 * n)[..., None], rust[..., None] * 0.65)
    return finish(c, n * 0.3 - sc * 0.3, 0.8)


def gen_roofing():
    h = w = 512
    n = fnoise(h, w, 1.5, 3201)
    c = tile((0.13, 0.125, 0.12), h, w) * (1 + 0.3 * n + 0.4 * speckle(h, w, 3202, 0.9))[..., None]
    Y, X = np.mgrid[0:h, 0:w]
    seam = smooth(0, 2.5, (X % 128).astype(np.float32))
    c *= (0.6 + 0.4 * seam)[..., None]
    pud = patches(h, w, 3203, 40, 1.2, 1.9)
    c = lerp(c, tile((0.20, 0.19, 0.17), h, w), pud[..., None] * 0.45)              # ponding stains
    c = moss_over(c, patches(h, w, 3204, 24, 1.3, 2.0) * 0.8, 3205, 0.85)
    blis = smooth(2.0, 3.0, speckle(h, w, 3206, 1.6))
    c = lerp(c, c * 1.8 + 0.03, blis[..., None] * 0.5)
    return finish(c, seam * 0.4 + n * 0.3, 1.0)


def gen_corrugated():
    h = w = 512
    Y, X = np.mgrid[0:h, 0:w]
    rid = 0.5 + 0.5 * np.sin(X / w * TAU * 16)
    n = fnoise(h, w, 1.5, 3301)
    base = lerp(tile((0.40, 0.42, 0.40), h, w), tile((0.28, 0.30, 0.30), h, w), smooth(-1, 1, n))
    c = base * (0.72 + 0.4 * rid)[..., None] * (1 + 0.1 * speckle(h, w, 3302, 0.8))[..., None]
    rust = smooth(0.3, 1.5, rain(h, w, 3303, 2.0, 2.5, 90) + 0.6 * bnoise(h, w, 20, 20, 3304) * 0.5 + 0.5 * speckle(h, w, 3305, 1.5) * 0.3)
    c = lerp(c, lerp(tile((0.33, 0.16, 0.07), h, w), tile((0.55, 0.30, 0.11), h, w), smooth(-1, 1, n))[...], rust[..., None] * 0.75)
    c *= (1 - 0.3 * patches(h, w, 3306, 26, 1.0, 1.8))[..., None]
    return finish(c, rid * 1.5, 0.9)


def gen_wood():
    c = _planks(3401, (0.30, 0.25, 0.19), 5, 1.0, 512, 512, True, 0.6)
    h, w = c.shape[:2]
    c = c * (0.7 + 0.3 * smooth(-1, 1, fnoise(h, w, 1.8, 3402)))[..., None]
    grey = smooth(0.2, 1.2, bnoise(h, w, 12, 40, 3403))                     # sun-bleached silver grey
    c = lerp(c, tile((0.42, 0.40, 0.36), h, w) * (0.8 + 0.4 * speckle(h, w, 3404, 0.8) * 0.3)[..., None], grey[..., None] * 0.5)
    c = moss_over(c, patches(h, w, 3405, 22, 1.2, 2.0) * 0.6, 3406, 0.6)
    return np.clip(c, 0, 1)


def gen_bark():
    h = w = 256
    n = bnoise(h, w, 2.0, 40, 3501)
    f = fnoise(h, w, 1.6, 3502)
    ridge = 1 - np.abs(np.sin(np.arange(w)[None, :] / w * TAU * 7 + 2.2 * f + 1.4 * n))
    c = col((0.17, 0.14, 0.11))[None, None] * (0.5 + 0.6 * ridge + 0.12 * f)[..., None]
    c = moss_over(c, smooth(0.0, 1.4, bnoise(h, w, 10, 24, 3503)) * 0.7, 3504, 0.9)
    return finish(c, ridge * 1.5, 0.8)


# ------------------------------------------------------------------------------------------------ vehicles / props
def _car_paint(base, seed, rusty=0.18):
    h = w = 256
    n = fnoise(h, w, 1.6, seed)
    c = tile(base, h, w) * (1 + 0.06 * n)[..., None]
    fade = smooth(-0.3, 1.2, bnoise(h, w, 30, 30, seed + 1))
    gray = (c * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    c = lerp(c, np.broadcast_to(gray, c.shape) * 1.15 + 0.08, fade * 0.55)            # sun-faded, chalky paint
    sc = scratches(h, w, 70, 10, 60, seed + 2, spread=0.9)
    c = lerp(c, tile((0.40, 0.38, 0.35), h, w), sc[..., None] * 0.5)
    rm = smooth(1.15 - 0.5 * rusty, 2.0 - 0.5 * rusty, bnoise(h, w, 9, 9, seed + 3) + 0.55 * speckle(h, w, seed + 4, 1.4) + 0.4 * rain(h, w, seed + 5, 2, 4, 40))
    c = lerp(c, lerp(tile((0.30, 0.14, 0.06), h, w), tile((0.56, 0.30, 0.11), h, w), smooth(-1, 1, fnoise(h, w, 1.3, seed + 6))), rm[..., None] * 0.8)
    dust = smooth(0.3, 1.6, bnoise(h, w, 18, 18, seed + 7) + 0.5 * fnoise(h, w, 2, seed + 8))
    c = lerp(c, tile((0.46, 0.41, 0.31), h, w), dust[..., None] * 0.4)
    c = moss_over(c, patches(h, w, seed + 9, 14, 1.4, 2.1) * 0.7, seed + 10, 0.8)
    return finish(c, n * 0.2 - rm * 0.5, 0.7)


def gen_car_red():
    return _car_paint((0.45, 0.07, 0.06), 3601)


def gen_car_blue():
    return _car_paint((0.10, 0.20, 0.42), 3701)


def gen_car_white():
    return _car_paint((0.72, 0.72, 0.68), 3801)


def gen_car_green():
    return _car_paint((0.10, 0.28, 0.16), 3901)


def gen_car_yellow():
    return _car_paint((0.72, 0.56, 0.08), 4001)


def gen_car_grey():
    return _car_paint((0.28, 0.29, 0.30), 4101)


def gen_tire():
    h = w = 128
    n = fnoise(h, w, 1.5, 4201)
    c = tile((0.07, 0.07, 0.07), h, w) * (1 + 0.5 * n + 0.4 * speckle(h, w, 4202))[..., None]
    X = np.arange(w)[None, :]
    groove = 0.5 + 0.5 * np.sin(X / w * TAU * 6)
    c *= (0.6 + 0.4 * groove)[..., None]
    c = lerp(c, tile((0.30, 0.27, 0.22), h, w), patches(h, w, 4203, 10, 0.8, 1.6)[..., None][..., 0] * 0.4)
    return np.clip(c, 0, 1)


def _text(im, xy, s, size, fill, bold=True, anchor='mm'):
    f = ImageFont.truetype(FONT_B if bold else FONT_R, size)
    ImageDraw.Draw(im).text(xy, s, font=f, fill=fill, anchor=anchor)


def _sign_weather(c, seed):
    h, w = c.shape[:2]
    c = c * (1 - rain(h, w, seed, 0.5, 4, 40))[..., None]
    rust = smooth(0.8, 1.6, bnoise(h, w, 6, 6, seed + 1) + 0.6 * speckle(h, w, seed + 2, 1.2))
    edge = np.ones((h, w), np.float32)
    edge[6:-6, 6:-6] = 0
    rust = np.clip(rust * 0.7 + gblur(edge, 4) * 0.8, 0, 1) * smooth(0.2, 1.0, bnoise(h, w, 10, 10, seed + 3) + 0.6)
    c = lerp(c, tile((0.38, 0.20, 0.09), h, w), rust[..., None] * 0.8)
    c = lerp(c, c * 0.5 + 0.15, smooth(1.5, 2.3, speckle(h, w, seed + 4, 1.5))[..., None] * 0.5)
    return np.clip(c, 0, 1)


def gen_sign_street():
    im = Image.new('RGB', (512, 128), (16, 84, 52))
    d = ImageDraw.Draw(im)
    d.rectangle([5, 5, 506, 122], outline=(230, 230, 220), width=4)
    _text(im, (256, 58), 'ASHFALL AVE', 62, (232, 232, 222))
    _text(im, (256, 104), '100 BLOCK', 22, (232, 232, 222), bold=False)
    c = np.asarray(im, np.float32) / 255.0
    return _sign_weather(c, 4301)


def gen_sign_stop():
    S = 512
    im = Image.new('RGB', (S, S), (30, 30, 30))
    d = ImageDraw.Draw(im)
    pts = [(S / 2 + S * 0.5 * np.cos(np.radians(22.5 + 45 * k)), S / 2 + S * 0.5 * np.sin(np.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon(pts, fill=(196, 26, 26))
    pts2 = [(S / 2 + S * 0.46 * np.cos(np.radians(22.5 + 45 * k)), S / 2 + S * 0.46 * np.sin(np.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon(pts2, outline=(240, 240, 235), width=8)
    _text(im, (S / 2, S / 2), 'STOP', 150, (240, 240, 235))
    c = np.asarray(im, np.float32) / 255.0
    c = _sign_weather(c, 4401)
    c = lerp(c, tile((0.52, 0.44, 0.38), S, S), smooth(1.0, 2.0, bnoise(S, S, 20, 20, 4405))[..., None] * 0.4)
    return c


def gen_billboard():
    W, H = 1024, 512
    im = Image.new('RGB', (W, H), (200, 190, 160))
    d = ImageDraw.Draw(im)
    for k in range(H):
        t = k / H
        d.line([(0, k), (W, k)], fill=(int(220 - 90 * t), int(150 - 50 * t), int(60 + 70 * t)))
    d.ellipse([W * 0.62, H * 0.12, W * 0.62 + 260, H * 0.12 + 260], fill=(250, 220, 120))
    d.polygon([(0, H), (0, H * 0.7), (150, H * 0.55), (300, H * 0.72), (520, H * 0.5), (760, H * 0.74), (W, H * 0.6), (W, H)], fill=(40, 52, 70))
    _text(im, (W * 0.3, H * 0.28), 'ASHFALL', 130, (255, 250, 235))
    _text(im, (W * 0.3, H * 0.46), 'A NEW DAY. A NEW START.', 38, (255, 245, 225), bold=False)
    c = np.asarray(im, np.float32) / 255.0
    h, w = H, W
    peel = smooth(1.0, 1.4, bnoise(h, w, 30, 18, 4501) + 0.5 * bnoise(h, w, 9, 9, 4502))
    c = lerp(c, tile((0.62, 0.58, 0.50), h, w) * (1 + 0.1 * fnoise(h, w, 1.5, 4503))[..., None], peel[..., None] * 0.9)   # torn paper
    c = lerp(c, c * 0.4 + np.array([0.32, 0.30, 0.27], np.float32) * 0.5, 0.35 * smooth(0.3, 1.5, fnoise(h, w, 2.0, 4504))[..., None])
    c *= (1 - rain(h, w, 4505, 0.6, 5, 120))[..., None]
    return np.clip(c, 0, 1)


def gen_container():
    h = w = 512
    Y, X = np.mgrid[0:h, 0:w]
    rid = 0.5 + 0.5 * np.sin(X / w * TAU * 12)
    n = fnoise(h, w, 1.5, 4601)
    base = tile((0.17, 0.26, 0.34), h, w)
    c = base * (0.7 + 0.45 * rid)[..., None] * (1 + 0.12 * n)[..., None]
    rust = smooth(0.3, 1.5, rain(h, w, 4602, 2.0, 2.5, 90) + 0.5 * speckle(h, w, 4603, 1.4) * 0.3 + 0.4 * bnoise(h, w, 18, 18, 4604) * 0.5)
    c = lerp(c, lerp(tile((0.30, 0.15, 0.07), h, w), tile((0.55, 0.30, 0.11), h, w), smooth(-1, 1, n)), rust[..., None] * 0.8)
    return finish(c, rid * 1.5, 0.9)


def gen_barrier():
    h = w = 256
    c, n1 = _concrete_base(h, w, 4701, (0.50, 0.49, 0.46))
    st = (np.arange(h)[:, None] // 64) % 2
    stripe = (smooth(0, 3, (np.arange(w)[None, :] % 128).astype(np.float32)) * 0 + ((np.arange(w)[None, :] + np.arange(h)[:, None]) // 48 % 2)).astype(np.float32)
    mask = smooth(0.0, 1.0, bnoise(h, w, 12, 12, 4702)) * 0.0
    band = ((np.arange(h)[:, None] > 90) & (np.arange(h)[:, None] < 150)).astype(np.float32)
    c = lerp(c, tile((0.62, 0.17, 0.13), h, w) * (1 + 0.1 * n1)[..., None], (band * stripe * 0.85)[..., None])
    c *= (1 - rain(h, w, 4703, 0.4))[..., None]
    c = lerp(c, c * 0.5 + 0.12, patches(h, w, 4704, 12, 1.0, 1.8)[..., None] * 0.5)
    cm = cracks(h, w, 3, 4705, 0.04)
    c *= (1 - 0.7 * cm)[..., None]
    return finish(c, n1 * 0.4 - cm, 1.0)


# ------------------------------------------------------------------------------------------------ foliage (alpha)
def gen_weeds():
    return _blade_img(256, 256, 4801, 52, ((0.12, 0.22, 0.05), (0.50, 0.55, 0.16)), 0.30, 1.0, 0.055, 0.35)


def gen_dead_grass():
    return _blade_img(256, 384, 4811, 46, ((0.28, 0.22, 0.10), (0.66, 0.58, 0.32)), 0.45, 1.0, 0.040, 0.45)


def gen_leaf():
    return _cluster(512, 4821, 170, 70, 38, ((0.04, 0.12, 0.03), (0.24, 0.40, 0.09)), serr=0.5, tip=0.35)


def gen_leaf_dead():
    return _cluster(512, 4831, 70, 62, 32, ((0.20, 0.13, 0.06), (0.52, 0.38, 0.15)), twig=(0.16, 0.12, 0.09), serr=0.5, tip=0.35, rise=0.9)


def gen_ivy():
    S, ss = 512, 2
    SS = S * ss
    r = np.random.default_rng(4841)
    rgb = Image.new('RGB', (SS, SS), (0, 0, 0))
    al = Image.new('L', (SS, SS), 0)
    dr, da = ImageDraw.Draw(rgb), ImageDraw.Draw(al)
    stems = []
    for k in range(9):
        x, y = SS * r.uniform(0.15, 0.85), SS
        a = -np.pi / 2 + r.normal(0, 0.15)
        pts = [(x, y)]
        for i in range(24):
            a += r.normal(0, 0.18)
            a = np.clip(a, -np.pi / 2 - 0.9, -np.pi / 2 + 0.9)
            pts.append((pts[-1][0] + np.cos(a) * SS * 0.04, pts[-1][1] + np.sin(a) * SS * 0.04))
        stems.append(pts)
        dr.line(pts, fill=(52, 38, 24), width=int(SS / 160))
        da.line(pts, fill=255, width=int(SS / 160))
    items = []
    for st in stems:
        for i in range(2, len(st)):
            if r.random() < 0.75:
                items.append((st[i][0] + r.normal(0, 8), st[i][1] + r.normal(0, 8), r.uniform(0, TAU), r.random()))
    items.sort(key=lambda t: t[3])
    for x, y, a, z in items:
        L = SS * r.uniform(0.045, 0.075)
        base = np.array((0.04, 0.14, 0.03)) * (1 - z) + np.array((0.20, 0.38, 0.09)) * z
        cc = tuple(int(255 * v) for v in np.clip(base * (0.8 + 0.4 * r.random()), 0, 1))
        pts = []
        for t in np.linspace(0, TAU, 14, endpoint=False):                 # heart-ish ivy leaf
            rr = L * (0.55 + 0.45 * np.cos(t)) if np.cos(t) > -0.2 else L * 0.55
            pts.append((x + np.cos(t + a) * rr * 0.9, y + np.sin(t + a) * rr * 0.9))
        dr.polygon(pts, fill=cc)
        da.polygon(pts, fill=255)
        dr.line([(x, y), (x + np.cos(a) * L * 0.9, y + np.sin(a) * L * 0.9)], fill=tuple(int(v * 0.7) for v in cc), width=2)
    rgbi = np.asarray(rgb.resize((S, S), Image.LANCZOS), np.float32) / 255.0
    a = np.asarray(al.resize((S, S), Image.LANCZOS), np.float32) / 255.0
    rgbi = np.where(a[..., None] > 0.02, np.clip(rgbi / np.maximum(a[..., None], 0.02), 0, 1), rgbi)
    return pack(rgbi, np.clip((a - 0.1) * 1.3, 0, 1))


def gen_wire():
    """thin dark cable on a transparent card (used for sagging power lines drawn as flat ribbons)"""
    h, w = 64, 64
    a = np.zeros((h, w), np.float32)
    a[26:38, :] = 1.0
    a = gblur(a, 1.2)
    c = np.broadcast_to(np.array([0.05, 0.05, 0.05], np.float32), (h, w, 3)).copy()
    return pack(c, np.clip(a * 1.6, 0, 1))


GEN = {n: globals()['gen_' + n[3:]] for n in NAMES}


def generate_all():
    out = {}
    for n in NAMES:
        a = np.clip(GEN[n](), 0, 1)
        out[n] = (a * 255 + 0.5).astype(np.uint8)
    return out
