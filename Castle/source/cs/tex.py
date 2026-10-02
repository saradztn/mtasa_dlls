# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# tex.py - procedural textures for the gothic castle.  Every generator returns the FINAL diffuse
# (sRGB float HxWx3, or HxWx4 for alpha textures).  Relief/AO are baked into the colour with a
# directional height shading because San Andreas has no normal-map support.
# Tiling textures are periodic (wrapped cellular / FFT noise).
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib.noise import fnoise, bnoise, worley, smooth, scratches

MAT_NAMES = ['cs_stone', 'cs_stone_in', 'cs_trim', 'cs_flag', 'cs_tile', 'cs_slate', 'cs_wood', 'cs_door', 'cs_iron',
             'cs_rug', 'cs_web', 'cs_orb', 'cs_glass', 'cs_flame', 'cs_books', 'cs_banner', 'cs_gold', 'cs_carved']
M = {n: i for i, n in enumerate(MAT_NAMES)}
ALPHA = {M['cs_web'], M['cs_orb'], M['cs_flame']}


def shade(alb, height, strength=1.0, light=(-0.6, -0.8)):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    s = 1.0 + strength * (gx * light[0] + gy * light[1])
    return alb * np.clip(s, 0.45, 1.6)[..., None]


def tint(rgb, h, w):
    return np.broadcast_to(np.array(rgb, np.float32), (h, w, 3)).copy()


# ------------------------------------------------------------------------------------------------
def ashlar(size, rows, seed, base, bright=(0.8, 1.2), wid=(1.5, 2.6), mortar=5, bevel=10, moss=0.0, stain=0.5,
           cracks=14, warm=0.0, grain=0.08):
    r = np.random.default_rng(seed)
    h = w = size
    rh = r.uniform(0.75, 1.3, rows)
    rh = rh / rh.sum() * h
    ed = np.round(np.concatenate([[0], np.cumsum(rh)])).astype(int)
    ed[-1] = h
    bid = np.zeros((h, w), np.int32)
    dxl = np.zeros((h, w), np.float32)
    dxr = np.zeros((h, w), np.float32)
    dyt = np.zeros((h, w), np.float32)
    dyb = np.zeros((h, w), np.float32)
    X = np.arange(w)
    cnt = 0
    for i in range(rows):
        y0, y1 = ed[i], ed[i + 1]
        nb = max(2, int(round(w / ((y1 - y0) * r.uniform(*wid)))))
        xs = np.sort(r.uniform(0, w, nb))
        j = np.searchsorted(xs, X, 'right') - 1
        left = np.where(j >= 0, xs[np.maximum(j, 0)], xs[-1] - w)
        right = np.where(j + 1 < nb, xs[np.minimum(j + 1, nb - 1)], xs[0] + w)
        ids = cnt + (j % nb)
        cnt += nb
        bid[y0:y1] = ids[None, :]
        dxl[y0:y1] = (X - left)[None, :]
        dxr[y0:y1] = (right - X)[None, :]
        yy = np.arange(y0, y1)
        dyt[y0:y1] = (yy - y0)[:, None]
        dyb[y0:y1] = (y1 - 1 - yy)[:, None]
    wn = bnoise(h, w, 4.0, 4.0, seed + 1) * 1.1
    e = np.minimum(np.minimum(dxl, dxr), np.minimum(dyt, dyb)) + wn
    bval = r.uniform(*bright, cnt).astype(np.float32)
    btint = r.normal(0, 1, (cnt, 3)).astype(np.float32) * np.array([0.007, 0.006, 0.009], np.float32)
    bv = bval[bid]
    gr = fnoise(h, w, 1.3, seed + 2) * grain + bnoise(h, w, 0.8, 0.8, seed + 3) * grain * 0.6
    big = fnoise(h, w, 2.6, seed + 4)
    alb = np.array(base, np.float32)[None, None, :] * (bv * (1 + gr) * (1 + 0.12 * big))[..., None] + btint[bid]
    alb[..., 0] += warm * big * 0.03
    # vertical weathering streaks / stains
    st = bnoise(h, w, 4.0, 60.0, seed + 5)
    alb *= (1 - stain * 0.22 * smooth(0.3, 1.8, st))[..., None]
    if moss > 0:
        mm = smooth(1.0, 2.2, bnoise(h, w, 6.0, 40.0, seed + 6) + 0.5 * fnoise(h, w, 2.0, seed + 7))
        alb = alb * (1 - mm[..., None] * moss) + mm[..., None] * moss * np.array([0.10, 0.17, 0.07], np.float32) * (0.7 + 0.3 * gr[..., None] * 5)
    mort = smooth(mortar * 0.5, mortar, e)
    hgt = smooth(0, bevel, e) * mort
    hgt += 0.20 * gr + 0.10 * fnoise(h, w, 1.6, seed + 8)
    alb = alb * (0.28 + 0.72 * mort)[..., None]
    if cracks:
        sc = scratches(h, w, cracks, 40, 160, seed + 9, spread=1.2, ss=2, width=1.2)
        hgt -= 0.35 * sc
        alb *= (1 - 0.55 * sc)[..., None]
    alb = shade(alb, hgt * 3.0, 1.0)
    return np.clip(alb, 0, 1)


def gen_stone():
    return ashlar(1024, 8, 11, (0.30, 0.31, 0.34), moss=0.35, stain=0.9, cracks=18)


def gen_stone_in():
    a = ashlar(1024, 8, 21, (0.22, 0.215, 0.23), moss=0.18, stain=1.0, cracks=22, warm=1.0)
    return a * np.array([1.02, 0.97, 0.93])


def gen_trim():
    return ashlar(512, 5, 31, (0.40, 0.40, 0.42), bright=(0.9, 1.1), wid=(2.0, 3.0), mortar=4, bevel=7, moss=0.1, stain=0.5, cracks=6, grain=0.06)


def gen_flag():
    return ashlar(1024, 4, 41, (0.26, 0.25, 0.25), bright=(0.75, 1.15), wid=(0.9, 1.4), mortar=7, bevel=12, moss=0.0, stain=0.3, cracks=24, warm=1.0)


def gen_tile():
    h = w = 512
    n = 8
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    cx, cy = X * n // w, Y * n // h
    chk = (cx + cy) % 2
    fx = (X * n % w) / (w / n)
    fy = (Y * n % h) / (h / n)
    e = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) * (w / n)
    vein = np.abs(np.sin((X * 0.015 + Y * 0.01 + fnoise(h, w, 2.4, 51) * 2.5) * 6.0))
    vein = smooth(0.85, 1.0, vein)
    dark = np.array([0.045, 0.045, 0.055], np.float32)
    red = np.array([0.30, 0.045, 0.05], np.float32)
    alb = np.where(chk[..., None] == 1, red, dark) * (1 + 0.18 * fnoise(h, w, 2.0, 52))[..., None]
    alb = alb + (vein * 0.22)[..., None] * np.array([0.8, 0.75, 0.7], np.float32)
    grout = smooth(1.0, 3.5, e)
    alb = alb * (0.35 + 0.65 * grout)[..., None]
    gl = 0.5 * (smooth(0.0, 40.0, X * 0.0 + fnoise(h, w, 2.8, 53) * 60 + 30))
    alb = alb * (0.9 + 0.2 * gl[..., None])
    return np.clip(alb, 0, 1)


def gen_slate():
    h = w = 1024
    rows = 16
    rh = h / rows
    r = np.random.default_rng(61)
    Y, X = np.mgrid[0:h, 0:w]
    row = (Y // rh).astype(int)
    fy = (Y % rh) / rh
    nper = 12
    sw = w / nper
    xoff = np.where(row % 2 == 0, 0.0, sw / 2)
    col = ((X + xoff) // sw).astype(int) % nper
    fx = ((X + xoff) % sw) / sw
    ids = r.random((rows, nper))
    iv = ids[row % rows, col]
    base = np.array([0.15, 0.17, 0.21], np.float32)
    alb = base[None, None] * (0.7 + 0.7 * iv)[..., None]
    alb *= (1 + 0.20 * fnoise(h, w, 1.6, 62))[..., None]
    # each slate: dark overlap shadow near the top (covered by row above), light lower edge
    sh = 0.55 + 0.45 * smooth(0.0, 0.5, fy) + 0.25 * smooth(0.9, 1.0, fy)
    edge = smooth(0.0, 0.04, np.minimum(fx, 1 - fx))
    alb = alb * sh[..., None] * (0.35 + 0.65 * edge)[..., None]
    mm = smooth(1.2, 2.4, bnoise(h, w, 8, 8, 63) + 0.5 * fnoise(h, w, 2.0, 64))
    alb = alb * (1 - 0.8 * mm[..., None]) + 0.8 * mm[..., None] * np.array([0.07, 0.12, 0.05], np.float32)
    hgt = sh + 0.1 * fnoise(h, w, 1.4, 65)
    alb = shade(alb, hgt * 1.5, 0.8)
    return np.clip(alb, 0, 1)


def gen_wood():
    h = w = 512
    Y, X = np.mgrid[0:h, 0:w]
    npl = 4
    pid = X * npl // w
    fx = (X * npl % w) / (w / npl)
    r = np.random.default_rng(71)
    pv = r.uniform(0.75, 1.25, npl)[pid]
    po = r.uniform(0, 50, npl)[pid]
    grain = np.sin((fx * 40 + fnoise(h, w, 2.4, 72) * 3.0 + po) * 1.0 + bnoise(h, w, 1.5, 80, 73) * 2.0)
    fib = bnoise(h, w, 1.2, 70, 74)
    base = np.array([0.34, 0.20, 0.105], np.float32)
    alb = base[None, None] * (pv * (1 + 0.20 * fib + 0.10 * grain))[..., None]
    gap = smooth(0.0, 0.02, np.minimum(fx, 1 - fx))
    alb *= (0.4 + 0.6 * gap)[..., None]
    hgt = 0.4 * fib + 0.2 * grain + gap
    alb = shade(alb, hgt * 2.0, 0.8)
    return np.clip(alb, 0, 1)


def gen_door():
    h = w = 512
    Y, X = np.mgrid[0:h, 0:w]
    npl = 7
    pid = X * npl // w
    fx = (X * npl % w) / (w / npl)
    r = np.random.default_rng(81)
    pv = r.uniform(0.75, 1.2, npl)[pid]
    fib = bnoise(h, w, 1.2, 80, 82)
    grain = np.sin((fx * 30 + fnoise(h, w, 2.4, 83) * 3 + r.uniform(0, 30, npl)[pid]) + bnoise(h, w, 1.5, 70, 84) * 2)
    alb = np.array([0.30, 0.17, 0.09], np.float32)[None, None] * (pv * (1 + 0.2 * fib + 0.1 * grain))[..., None]
    gap = smooth(0.0, 0.03, np.minimum(fx, 1 - fx))
    alb *= (0.35 + 0.65 * gap)[..., None]
    hgt = 0.4 * fib + gap
    yn = Y / h
    band = np.zeros((h, w), np.float32)
    for c, hw in ((0.14, 0.045), (0.50, 0.04), (0.86, 0.045)):
        band = np.maximum(band, smooth(c - hw - 0.008, c - hw, yn) * (1 - smooth(c + hw, c + hw + 0.008, yn)))
    # hinge strap pointed tail from the left edge
    band *= 1.0
    iron = np.array([0.055, 0.055, 0.06], np.float32)[None, None] * (1 + 0.5 * fnoise(h, w, 1.4, 85))[..., None]
    alb = alb * (1 - band[..., None]) + iron * band[..., None]
    hgt = hgt + 0.6 * band
    # rivets
    for c in (0.14, 0.50, 0.86):
        for k in range(8):
            cx, cy = (k + 0.5) / 8 * w, c * h
            d = np.hypot(X - cx, Y - cy)
            rv = smooth(6.5, 3.0, d)
            alb = alb * (1 - rv[..., None]) + np.array([0.20, 0.19, 0.18], np.float32) * rv[..., None]
            hgt = hgt + 0.7 * rv
    alb = shade(alb, hgt * 2.0, 0.9)
    return np.clip(alb, 0, 1)


def gen_iron():
    h = w = 256
    a = 0.07 + 0.03 * fnoise(h, w, 1.6, 91)
    rust = smooth(1.3, 2.4, bnoise(h, w, 3, 3, 92))
    alb = np.stack([a, a, a * 1.05], -1) * 1.0
    alb = alb * (1 - rust[..., None]) + rust[..., None] * np.array([0.22, 0.10, 0.05], np.float32)
    alb = shade(alb, fnoise(h, w, 1.2, 93) * 0.3, 0.6)
    return np.clip(alb, 0, 1)


def gen_rug():
    h, w = 1024, 512
    Y, X = np.mgrid[0:h, 0:w]
    u = X / w
    v = Y / h
    red = np.array([0.34, 0.035, 0.045], np.float32)
    deep = np.array([0.17, 0.02, 0.035], np.float32)
    gold = np.array([0.62, 0.45, 0.14], np.float32)
    navy = np.array([0.04, 0.05, 0.12], np.float32)
    d_edge = np.minimum(u, 1 - u)
    alb = np.broadcast_to(red, (h, w, 3)).copy()
    # outer border bands
    alb = np.where((d_edge < 0.075)[..., None], deep, alb)
    alb = np.where(((d_edge > 0.012) & (d_edge < 0.022))[..., None], gold, alb)
    alb = np.where(((d_edge > 0.060) & (d_edge < 0.068))[..., None], gold, alb)
    # zig-zag pattern in the border
    zig = (np.abs(((v * 24) % 1.0) - 0.5) * 2)
    alb = np.where(((d_edge > 0.027) & (d_edge < 0.055) & (np.abs(d_edge - 0.041) < 0.014 * (1 - zig + 0.2)))[..., None], gold, alb)
    # central repeating medallions (period 1/2 along v)
    cu, cv = u - 0.5, ((v * 2) % 1.0) - 0.5
    dist = np.sqrt((cu * 1.0) ** 2 + (cv * 0.5) ** 2)
    diam = np.abs(cu) * 1.6 + np.abs(cv) * 0.8
    ring = (diam < 0.36) & (diam > 0.32)
    alb = np.where(ring[..., None], gold, alb)
    alb = np.where(((diam < 0.26) & (diam > 0.22))[..., None], navy, alb)
    alb = np.where((diam < 0.12)[..., None], gold, alb)
    alb = np.where((diam < 0.06)[..., None], deep, alb)
    # tiny dots on the field
    dots = (((u * 12) % 1 - 0.5) ** 2 + ((v * 24) % 1 - 0.5) ** 2) < 0.012
    alb = np.where((dots & (d_edge > 0.09) & (diam > 0.38))[..., None], deep * 1.6, alb)
    # woven fabric texture
    thr = np.sin(X * np.pi * 2 / 3.0) * np.sin(Y * np.pi * 2 / 3.0)
    pile = fnoise(h, w, 1.0, 101) * 0.10 + bnoise(h, w, 0.7, 0.7, 102) * 0.08
    wear = smooth(0.8, 2.0, fnoise(h, w, 2.8, 103))
    alb = alb * (1 + pile + 0.05 * thr)[..., None]
    alb = alb * (1 - 0.35 * wear[..., None]) + 0.35 * wear[..., None] * np.array([0.12, 0.10, 0.09], np.float32) * 0.4
    # fringe: no (UV maps the rug body only)
    return np.clip(alb, 0, 1)


def _web_img(kind, size, seed):
    S = 4
    n = size * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    wcol = (236, 236, 232)
    if kind == 'corner':
        nsp = 9
        angs = np.linspace(0, np.pi / 2, nsp) + r.normal(0, 0.035, nsp)
        angs[0], angs[-1] = 0.0, np.pi / 2
        Rmax = n * 1.05
        for a in angs:
            d.line([(0, 0), (np.cos(a) * Rmax, np.sin(a) * Rmax)], fill=wcol + (205,), width=int(1.3 * S))
        rad = 0.0
        while rad < Rmax * 0.97:
            rad += r.uniform(0.045, 0.085) * n
            for i in range(nsp - 1):
                if r.random() < 0.10:
                    continue
                a0, a1 = angs[i], angs[i + 1]
                p0 = np.array([np.cos(a0), np.sin(a0)]) * rad
                p1 = np.array([np.cos(a1), np.sin(a1)]) * rad
                m = (p0 + p1) / 2 * (0.93 + r.uniform(-0.02, 0.02))
                pts = []
                for t in np.linspace(0, 1, 9):
                    q = (1 - t) ** 2 * p0 + 2 * t * (1 - t) * m + t ** 2 * p1
                    pts.append(tuple(q))
                d.line(pts, fill=wcol + (170,), width=int(0.9 * S))
    else:
        c = n / 2
        nsp = 22
        angs = np.sort(r.uniform(0, 2 * np.pi, nsp))
        angs = np.linspace(0, 2 * np.pi, nsp, endpoint=False) + r.normal(0, 0.07, nsp)
        for a in angs:
            d.line([(c, c), (c + np.cos(a) * n * 0.5, c + np.sin(a) * n * 0.5)], fill=wcol + (200,), width=int(1.2 * S))
        rad = n * 0.03
        ang_off = 0.0
        while rad < n * 0.48:
            rad += n * 0.011
            ang_off += 0.19
            for i in range(nsp):
                a0, a1 = angs[i], angs[(i + 1) % nsp] + (2 * np.pi if i == nsp - 1 else 0)
                p0 = np.array([c + np.cos(a0) * rad, c + np.sin(a0) * rad])
                p1 = np.array([c + np.cos(a1) * rad, c + np.sin(a1) * rad])
                if r.random() < 0.03:
                    continue
                m = (p0 + p1) / 2 - (np.array([np.cos((a0 + a1) / 2), np.sin((a0 + a1) / 2)]) * rad * 0.012)
                pts = [tuple((1 - t) ** 2 * p0 + 2 * t * (1 - t) * m + t ** 2 * p1) for t in np.linspace(0, 1, 5)]
                d.line(pts, fill=wcol + (165,), width=int(0.8 * S))
        # missing wedge + dust clumps
        d.ellipse([c - n * 0.02, c - n * 0.02, c + n * 0.02, c + n * 0.02], fill=wcol + (230,))
    im = im.resize((size, size), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    Y, X = np.mgrid[0:size, 0:size] / size
    if kind == 'corner':
        a[..., 3] *= smooth(1.0, 0.82, X + Y)           # fade out towards the far edge of the triangle
    else:
        a[..., 3] *= smooth(0.5, 0.40, np.hypot(X - 0.5, Y - 0.5))
    a[..., 3] *= 0.9
    a[..., :3] = np.array([0.93, 0.93, 0.90], np.float32)      # constant colour: no dark fringes after DXT/mip filtering
    return a


def gen_web():
    return _web_img('corner', 512, 111)


def gen_orb():
    return _web_img('orb', 512, 112)


def gen_glass():
    h = w = 256
    F1, F2, ID = worley(h, w, 6, 6, 121)
    cols = np.array([[1.0, 0.55, 0.12], [1.0, 0.72, 0.20], [0.95, 0.38, 0.08], [1.0, 0.82, 0.38], [0.85, 0.28, 0.06]], np.float32)
    ci = (ID * 5).astype(int) % 5
    alb = cols[ci] * (0.85 + 0.15 * fnoise(h, w, 2.0, 122))[..., None]
    lead = smooth(0.0, 0.07, F2 - F1)
    alb = alb * (0.08 + 0.92 * lead)[..., None]
    # glow towards the cell centres
    alb = alb * (0.75 + 0.25 * smooth(0.5, 0.0, F1))[..., None]
    return np.clip(alb, 0, 1)


def gen_flame():
    h = w = 128
    Y, X = np.mgrid[0:h, 0:w]
    x = (X + 0.5) / w * 2 - 1
    y = 1 - (Y + 0.5) / h            # 0 bottom .. 1 top
    wid = 0.55 * np.sin(np.pi * np.clip(y * 0.92, 0, 1)) ** 0.8 * (1 - 0.55 * y)
    dist = np.abs(x) / np.maximum(wid, 1e-3)
    a = np.clip(1 - dist ** 2, 0, 1) * smooth(1.0, 0.85, y) * smooth(0.0, 0.05, y)
    glow = np.exp(-((x ** 2) * 3.0 + ((y - 0.30) ** 2) * 4.0)) * 0.55
    alpha = np.clip(a + glow * 0.8, 0, 1)
    core = np.clip(1 - dist ** 2 * 1.4, 0, 1) * smooth(0.0, 0.5, y) * (1 - smooth(0.5, 0.95, y))
    rgb = np.stack([np.ones_like(y), 0.45 + 0.50 * core, 0.08 + 0.55 * core ** 2], -1)
    return np.concatenate([rgb, alpha[..., None]], -1).astype(np.float32)


def gen_books():
    h = w = 512
    r = np.random.default_rng(131)
    img = np.zeros((h, w, 3), np.float32)
    hgt = np.zeros((h, w), np.float32)
    wood = np.array([0.14, 0.08, 0.045], np.float32)
    nsh = 4
    sh_h = h // nsh
    img[:] = wood
    palette = [(0.35, 0.05, 0.06), (0.08, 0.16, 0.10), (0.10, 0.10, 0.25), (0.30, 0.20, 0.08), (0.20, 0.08, 0.10), (0.06, 0.06, 0.06),
               (0.38, 0.30, 0.16), (0.18, 0.12, 0.07), (0.25, 0.05, 0.12)]
    for s in range(nsh):
        y_bot = (s + 1) * sh_h - 14
        x = 3
        while x < w - 6:
            bw = int(r.uniform(9, 24))
            bh = int(sh_h * r.uniform(0.62, 0.92))
            if x + bw > w - 3:
                bw = w - 3 - x
            col = np.array(palette[r.integers(len(palette))], np.float32) * r.uniform(0.75, 1.2)
            y0 = y_bot - bh
            img[y0:y_bot, x:x + bw] = col
            hgt[y0:y_bot, x:x + bw] = 0.6
            hgt[y0:y_bot, x:x + 2] = 0.2
            hgt[y0:y_bot, x + bw - 2:x + bw] = 0.2
            # gold bands on spine
            if r.random() < 0.6:
                for yy in (y0 + 6, y_bot - 8):
                    img[yy:yy + 3, x + 1:x + bw - 1] = np.array([0.55, 0.42, 0.14], np.float32)
            if r.random() < 0.35 and bw > 12:
                img[y0 + bh // 3: y0 + bh // 3 + 14, x + 3:x + bw - 3] = np.array([0.5, 0.4, 0.2], np.float32) * 0.8
            x += bw + int(r.uniform(0, 2))
            if r.random() < 0.05:
                x += int(r.uniform(14, 30))
    # shelf boards
    for s in range(nsh + 1):
        y = min(h - 1, s * sh_h)
        img[max(0, y - 2):y + 14] = wood * 1.2
    dust = fnoise(h, w, 1.5, 132)
    img = img * (1 + 0.10 * dust[..., None])
    img = shade(img, hgt * 3.0, 0.9)
    # gloom between books
    return np.clip(img, 0, 1)


def gen_banner():
    h, w = 512, 256
    Y, X = np.mgrid[0:h, 0:w]
    u, v = X / w, Y / h
    red = np.array([0.30, 0.03, 0.05], np.float32)
    gold = np.array([0.66, 0.48, 0.14], np.float32)
    alb = np.broadcast_to(red, (h, w, 3)).copy()
    alb *= (1 + 0.10 * fnoise(h, w, 1.2, 141))[..., None]
    wv = np.sin(X * np.pi * 2 / 3.0) * np.sin(Y * np.pi * 2 / 3.0) * 0.05
    alb *= (1 + wv)[..., None]
    border = (np.minimum(u, 1 - u) < 0.06) | (v < 0.035)
    inner = (np.abs(np.minimum(u, 1 - u) - 0.085) < 0.008) & (v > 0.05)
    alb = np.where((border | inner)[..., None], gold, alb)
    # pointed-arch emblem
    cu, cv = (u - 0.5), v
    arch = np.maximum(np.abs(cu) * 2.0 - 0.0, 0) ** 2 * 0.0
    pt = (np.abs(cu) * 3.2 + (0.55 - cv)) < 0.62
    pt = (np.abs(cu) < 0.20) & (cv > 0.22) & (cv < 0.55) | ((np.abs(cu) * 2.4 + (cv - 0.12) * 1.0) < 0.5) & (cv < 0.24) & (cv > 0.10)
    ring = (np.hypot(cu * 1.0, (cv - 0.40) * 0.5) < 0.19) & (np.hypot(cu * 1.0, (cv - 0.40) * 0.5) > 0.165)
    alb = np.where(ring[..., None], gold, alb)
    spire = ((np.abs(cu) < (0.62 - cv) * 0.22) & (cv > 0.13) & (cv < 0.62)) | ((np.abs(cu) < 0.045) & (cv > 0.30) & (cv < 0.78))
    alb = np.where(spire[..., None], gold, alb)
    tassel = (v > 0.93) & (((X // 8) % 2) == 0)
    alb = np.where(tassel[..., None], gold * 0.9, alb)
    alb *= (1 - 0.35 * smooth(0.8, 2.0, fnoise(h, w, 2.6, 142)))[..., None]
    return np.clip(alb, 0, 1)


def gen_gold():
    h = w = 128
    a = 0.55 + 0.12 * fnoise(h, w, 1.5, 151)
    alb = np.stack([a * 1.0, a * 0.74, a * 0.25], -1)
    return np.clip(shade(alb, fnoise(h, w, 1.2, 152) * 0.3, 0.5), 0, 1)


def gen_carved():
    """gothic tracery panel, 512 x 1024 (3 m x 6 m) lit amber like the facade in the reference picture"""
    h, w = 1024, 512
    S = 2
    im = Image.new('L', (w * S, h * S), 70)
    d = ImageDraw.Draw(im)

    def arch(cx, base_y, half, rise, val, width):
        pts = []
        for t in np.linspace(0, 1, 40):
            # pointed arch
            x = cx - half + 2 * half * t
            if t <= 0.5:
                yy = base_y - np.sqrt(max((2 * half) ** 2 - (x - (cx - half + 2 * half)) ** 2, 0)) + 0
            else:
                yy = base_y - np.sqrt(max((2 * half) ** 2 - (x - (cx - half)) ** 2, 0))
            pts.append((x * S, yy * S))
        d.line(pts, fill=val, width=width * S)

    # frame
    d.rectangle([14 * S, 14 * S, (w - 14) * S, (h - 14) * S], outline=235, width=10 * S)
    d.rectangle([34 * S, 34 * S, (w - 34) * S, (h - 34) * S], outline=140, width=6 * S)
    for k, cx in enumerate((w * 0.30, w * 0.70)):
        top_base = 560
        d.rectangle([(cx - 70) * S, top_base * S, (cx + 70) * S, (h - 70) * S], fill=30, outline=225, width=7 * S)
        arch(cx, top_base, 70, 120, 225, 7)
        d.polygon([((cx - 70) * S, top_base * S)] + [((cx - 70 + 140 * t) * S, (top_base - np.sqrt(max(140 ** 2 - (((cx - 70 + 140 * t) - (cx + 70)) if t <= 0.5 else ((cx - 70 + 140 * t) - (cx - 70))) ** 2, 0))) * S) for t in np.linspace(0, 1, 30)] + [((cx + 70) * S, top_base * S)], fill=30)
        d.line([(cx * S, (top_base - 118) * S), (cx * S, (h - 70) * S)], fill=215, width=5 * S)
        for yy in range(640, h - 80, 90):
            d.line([((cx - 70) * S, yy * S), ((cx + 70) * S, yy * S)], fill=190, width=4 * S)
    # rose window
    cx, cy, R = w / 2, 270, 150
    for rr, wd in ((R, 10), (R - 22, 5), (R * 0.45, 6)):
        d.ellipse([(cx - rr) * S, (cy - rr) * S, (cx + rr) * S, (cy + rr) * S], outline=235, width=wd * S)
    for k in range(12):
        a = k * np.pi / 6
        d.line([(cx * S, cy * S), ((cx + np.cos(a) * (R - 6)) * S, (cy + np.sin(a) * (R - 6)) * S)], fill=210, width=5 * S)
        for t in (0.72,):
            px, py = cx + np.cos(a) * R * t, cy + np.sin(a) * R * t
            d.ellipse([(px - 17) * S, (py - 17) * S, (px + 17) * S, (py + 17) * S], outline=215, width=4 * S)
    im = im.resize((w, h), Image.LANCZOS)
    hgt = np.asarray(im, np.float32) / 255.0
    hgt = np.asarray(Image.fromarray((hgt * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0
    stone = 0.55 + 0.45 * fnoise(h, w, 1.6, 161) * 0.3
    t = np.clip(hgt, 0, 1)
    dark = np.array([0.10, 0.06, 0.035], np.float32)
    mid = np.array([0.55, 0.32, 0.10], np.float32)
    hi = np.array([1.0, 0.72, 0.28], np.float32)
    a = np.where(t[..., None] < 0.5, dark + (mid - dark) * (t[..., None] / 0.5), mid + (hi - mid) * ((t[..., None] - 0.5) / 0.5))
    a = a * (0.85 + 0.15 * stone[..., None] + 0.12 * fnoise(h, w, 1.2, 162)[..., None])
    gx = np.roll(hgt, -2, 1) - np.roll(hgt, 2, 1)
    gy = np.roll(hgt, -2, 0) - np.roll(hgt, 2, 0)
    a = a * np.clip(1 + 4.0 * (gx * -0.6 + gy * -0.8), 0.5, 1.5)[..., None]
    return np.clip(a, 0, 1)


GEN = {'cs_stone': gen_stone, 'cs_stone_in': gen_stone_in, 'cs_trim': gen_trim, 'cs_flag': gen_flag, 'cs_tile': gen_tile,
       'cs_slate': gen_slate, 'cs_wood': gen_wood, 'cs_door': gen_door, 'cs_iron': gen_iron, 'cs_rug': gen_rug,
       'cs_web': gen_web, 'cs_orb': gen_orb, 'cs_glass': gen_glass, 'cs_flame': gen_flame, 'cs_books': gen_books,
       'cs_banner': gen_banner, 'cs_gold': gen_gold, 'cs_carved': gen_carved}


def generate_all():
    out = {}
    for n in MAT_NAMES:
        a = GEN[n]()
        a = np.clip(a, 0, 1)
        out[n] = (a * 255 + 0.5).astype(np.uint8)
    return out
