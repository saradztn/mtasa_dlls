# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# tex.py - procedural textures of the park.  Every generator returns FINAL diffuse (float HxWx3, or HxWx4 for
# alpha textures).  Relief / AO are baked into the colour (San Andreas has no normal maps).  Tiling textures are
# periodic.  Foliage cards are drawn with PIL at 2x supersampling (leaf shapes with veins) and RGB is "bled" into
# the transparent area so that DXT5 / mip-mapping never produces dark or white fringes.
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from lib.noise import fnoise, bnoise, worley, smooth, scratches, FONT_B, FONT_R
from .ctex import ashlar, shade

TAU = np.pi * 2

NAMES = ['pk_grass', 'pk_paving', 'pk_cobble', 'pk_curb', 'pk_dirt', 'pk_pondbed', 'pk_stone', 'pk_granite', 'pk_wood',
         'pk_wooddark', 'pk_shingle', 'pk_iron', 'pk_bark', 'pk_leaf_oak', 'pk_leaf_birch', 'pk_frond', 'pk_flowers',
         'pk_grassblade', 'pk_reed', 'pk_lily', 'pk_water', 'pk_rubber_blue', 'pk_rubber_orange', 'pk_paint_red',
         'pk_paint_yellow', 'pk_paint_blue', 'pk_paint_green', 'pk_awning', 'pk_plaster', 'pk_glass', 'pk_sign_info',
         'pk_sign_kiosk', 'pk_sign_park', 'pk_manhole', 'pk_cone', 'pk_spray', 'pk_metal', 'pk_crate', 'pk_wood_light', 'pk_lamp',
         'pk_birchbark', 'pk_sand', 'pk_duck']
IDX = {n: i for i, n in enumerate(NAMES)}
ALPHA = {IDX[n] for n in ('pk_leaf_oak', 'pk_leaf_birch', 'pk_frond', 'pk_flowers', 'pk_grassblade', 'pk_reed', 'pk_lily', 'pk_water', 'pk_spray')}


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def col(rgb):
    return np.array(rgb, np.float32)


def gblur(a, sigma):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(a) * k, s=(h, w)).astype(np.float32)


def bleed(rgb, a):
    """fill RGB of transparent texels with the colour of nearby opaque ones"""
    h, w = a.shape
    img = (np.clip(rgb, 0, 1) * a[..., None]).astype(np.float32)
    acc, wsum = img.copy(), a.copy()
    cur_i, cur_a = img, a
    out = rgb.copy()
    known = a > 0.5
    for r in (2, 6, 14, 30):
        bi = np.stack([gblur(cur_i[..., c], r) for c in range(3)], -1)
        ba = np.clip(gblur(cur_a, r), 0, 1)
        est = bi / np.maximum(ba[..., None], 1e-4)
        use = (~known) & (ba > 0.02)
        out = np.where(use[..., None], est, out)
        known = known | use
    out = np.where(known[..., None], out, rgb.mean((0, 1)))
    return out


def pack(rgb, a):
    return np.concatenate([np.clip(bleed(rgb, a), 0, 1), np.clip(a, 0, 1)[..., None]], -1).astype(np.float32)


# ------------------------------------------------------------------------------------------------ ground
def gen_grass():
    h = w = 512
    s = 301
    n1, n2 = fnoise(h, w, 1.1, s), bnoise(h, w, 0.9, 3.2, s + 1)
    n3, n4 = bnoise(h, w, 38, 38, s + 2), bnoise(h, w, 9, 9, s + 3)
    t = np.clip(0.5 + 0.20 * n3 + 0.16 * n4 + 0.10 * n1, 0, 1)
    dark, mid, light = col((0.075, 0.17, 0.040)), col((0.19, 0.36, 0.085)), col((0.40, 0.54, 0.16))
    c = np.where((t < 0.5)[..., None], lerp(dark, mid, smooth(0.1, 0.5, t)), lerp(mid, light, smooth(0.5, 0.95, t)))
    blades = 0.5 + 0.5 * n2
    c = c * (0.62 + 0.62 * blades)[..., None]
    dry = smooth(1.7, 2.6, bnoise(h, w, 14, 14, s + 4) + 0.5 * fnoise(h, w, 1.5, s + 5))
    c = lerp(c, col((0.50, 0.46, 0.20)) * (0.8 + 0.3 * blades)[..., None], dry * 0.55)
    clover = smooth(1.9, 2.6, bnoise(h, w, 3.0, 3.0, s + 6))
    c = lerp(c, col((0.10, 0.30, 0.07)), clover * 0.5)
    r = np.random.default_rng(s)
    for k in range(70):                       # tiny white / yellow flowers (daisies, dandelions)
        x, y = r.integers(0, w), r.integers(0, h)
        rr = r.integers(1, 3)
        cc = col((0.95, 0.93, 0.80)) if r.random() < 0.6 else col((0.95, 0.80, 0.15))
        for dx in range(-rr, rr + 1):
            for dy in range(-rr, rr + 1):
                if dx * dx + dy * dy <= rr * rr:
                    c[(y + dy) % h, (x + dx) % w] = cc
    return np.clip(c, 0, 1)


def gen_paving():
    h = w = 512
    r = np.random.default_rng(311)
    rows, sw = 8, 128
    Y, X = np.mgrid[0:h, 0:w]
    ry = Y // (h // rows)
    off = (ry % 2) * (sw // 2)
    cx = (X + off) % sw
    cy = Y % (h // rows)
    sid = ((X + off) // sw) % (w // sw) + ry * 10
    bv = r.uniform(0.82, 1.14, 200)[sid % 200]
    tn = r.normal(0, 0.012, (200, 3)).astype(np.float32)[sid % 200]
    e = np.minimum(np.minimum(cx, sw - 1 - cx), np.minimum(cy, h // rows - 1 - cy)).astype(np.float32)
    e = e + bnoise(h, w, 3, 3, 312) * 0.8
    joint = smooth(1.2, 3.4, e)
    gr = fnoise(h, w, 1.3, 313) * 0.07 + bnoise(h, w, 0.7, 0.7, 314) * 0.05
    base = col((0.60, 0.56, 0.50))
    c = base[None, None] * (bv * (1 + gr) * (1 + 0.10 * fnoise(h, w, 2.4, 315)))[..., None] + tn
    stain = smooth(0.4, 2.0, bnoise(h, w, 28, 28, 316))
    c *= (1 - 0.16 * stain)[..., None]
    moss = smooth(1.0, 1.9, bnoise(h, w, 2.2, 2.2, 317)) * (1 - joint)
    jc = col((0.20, 0.19, 0.15))
    c = lerp(c, jc, (1 - joint) * 0.9)
    c = lerp(c, col((0.14, 0.24, 0.07)), moss * 0.5)
    hgt = joint * 1.2 + gr * 2
    c = shade(c, hgt * 2.0, 0.8)
    return np.clip(c, 0, 1)


def gen_cobble():
    h = w = 512
    F1, F2, ID = worley(h, w, 13, 13, 321)
    e = (F2 - F1)
    bv = 0.78 + 0.45 * ID
    tint = np.stack([ID * 0.06 - 0.03, ID * 0.02, -ID * 0.05 + 0.02], -1)
    c = col((0.55, 0.52, 0.48))[None, None] * bv[..., None] + tint * 0.5
    c *= (1 + fnoise(h, w, 1.2, 322) * 0.08)[..., None]
    dome = smooth(0.0, 0.5, e)
    c *= (0.45 + 0.65 * dome)[..., None]
    c = lerp(c, col((0.15, 0.14, 0.11)), (1 - smooth(0.02, 0.10, e)) * 0.8)
    c = shade(c, dome * 2.5 + F1 * -0.8, 0.9)
    return np.clip(c, 0, 1)


def gen_curb():
    h = w = 256
    g = fnoise(h, w, 1.3, 331) * 0.07 + bnoise(h, w, 0.8, 0.8, 332) * 0.05
    c = col((0.66, 0.65, 0.62))[None, None] * (1 + g + 0.1 * fnoise(h, w, 2.5, 333))[..., None]
    c *= (1 - 0.18 * smooth(0.5, 2.0, bnoise(h, w, 20, 20, 334)))[..., None]
    # expansion joint every half texture
    X = np.arange(w)[None, :]
    jt = np.exp(-((X - 0.5) ** 2) / 1.5) + np.exp(-((X - w // 2) ** 2) / 1.5)
    c *= (1 - 0.5 * jt)[..., None]
    return np.clip(c, 0, 1)


def gen_dirt():
    h = w = 256
    n = fnoise(h, w, 1.5, 341)
    c = col((0.30, 0.22, 0.14))[None, None] * (1 + 0.22 * n + 0.1 * bnoise(h, w, 6, 6, 342))[..., None]
    peb = smooth(1.8, 2.5, bnoise(h, w, 1.6, 1.6, 343))
    c = lerp(c, col((0.5, 0.46, 0.4)), peb * 0.55)
    return np.clip(shade(c, n * 0.4, 0.5), 0, 1)


def gen_pondbed():
    h = w = 256
    n = fnoise(h, w, 1.5, 351)
    c = col((0.13, 0.12, 0.085))[None, None] * (1 + 0.3 * n)[..., None]
    alg = smooth(0.8, 2.0, bnoise(h, w, 10, 10, 352))
    c = lerp(c, col((0.05, 0.16, 0.06)), alg * 0.7)
    peb = smooth(1.7, 2.4, bnoise(h, w, 2.0, 2.0, 353))
    c = lerp(c, col((0.30, 0.28, 0.24)), peb * 0.6)
    return np.clip(c, 0, 1)


def gen_stone():
    return ashlar(512, 6, 361, (0.64, 0.57, 0.45), bright=(0.85, 1.12), wid=(1.8, 3.0), mortar=5, bevel=8, moss=0.22, stain=0.8, cracks=8, warm=1.0)


def gen_granite():
    h = w = 512
    n = fnoise(h, w, 1.8, 371)
    spk = bnoise(h, w, 0.8, 0.8, 372)
    c = col((0.38, 0.37, 0.35))[None, None] * (1 + 0.20 * n + 0.18 * spk)[..., None]
    lich = smooth(1.3, 2.2, bnoise(h, w, 9, 9, 373) + 0.3 * fnoise(h, w, 1.6, 374))
    c = lerp(c, col((0.50, 0.55, 0.30)), lich * 0.55)
    moss = smooth(1.6, 2.4, bnoise(h, w, 16, 16, 375))
    c = lerp(c, col((0.10, 0.22, 0.07)), moss * 0.6)
    sc = scratches(h, w, 30, 20, 90, 376, spread=1.2)
    c *= (1 - 0.3 * sc)[..., None]
    return np.clip(shade(c, n * 1.4 + spk * 0.4, 0.8), 0, 1)


def _planks(seed, base, n_planks=4, grain=1.0, w=512, h=512, vert=True, wear=0.5):
    Y, X = np.mgrid[0:h, 0:w]
    if not vert:
        X, Y = Y, X
    pid = X * n_planks // w
    fx = (X * n_planks % w) / w
    r = np.random.default_rng(seed)
    pv = r.uniform(0.75, 1.2, n_planks)[pid]
    po = r.uniform(0, 60, n_planks)[pid]
    gn = fnoise(512, 512, 2.4, seed + 1)
    fib = bnoise(512, 512, 1.2, 70, seed + 2)
    if not vert:
        gn, fib = gn.T, fib.T
    gr = np.sin(fx * 36 + gn * 3.0 + po + fib * 2.0)
    c = col(base)[None, None] * (pv * (1 + 0.20 * fib + 0.10 * gr * grain))[..., None]
    knots = np.zeros((h, w), np.float32)
    for _ in range(3):
        kx, ky = r.uniform(0, w), r.uniform(0, h)
        knots += np.exp(-(((X - kx) ** 2) / 60.0 + ((Y - ky) ** 2) / 260.0))
    c *= (1 - 0.5 * np.clip(knots, 0, 1))[..., None]
    gap = smooth(0.0, 0.025, np.minimum(fx, 1 - fx))
    c *= (0.30 + 0.70 * gap)[..., None]
    wearm = smooth(0.4, 1.6, bnoise(512, 512, 12, 12, seed + 3))
    c = lerp(c, c * 1.35 + 0.03, wearm * wear * 0.4)
    return np.clip(shade(c, (0.5 * fib + 0.25 * gr + gap) * 2.0, 0.8), 0, 1)


def gen_wood():
    return _planks(381, (0.45, 0.28, 0.14), 4, 1.0)


def gen_wooddark():
    return _planks(391, (0.26, 0.15, 0.08), 3, 1.1)


def gen_wood_light():
    return _planks(395, (0.62, 0.44, 0.26), 4, 0.9)


def gen_crate():
    c = _planks(397, (0.55, 0.40, 0.23), 4, 1.0)
    h, w = c.shape[:2]
    c = c.copy()
    for t in (0, 1):                               # darker frame boards (border) for the crate look
        c[:20] *= 0.72
        c[-20:] *= 0.72
        c[:, :20] *= 0.72
        c[:, -20:] *= 0.72
    return c


def gen_shingle():
    h = w = 512
    rows = 10
    rh = h // rows
    Y, X = np.mgrid[0:h, 0:w]
    ry = Y // rh
    sw = 64
    off = (ry % 2) * (sw // 2)
    cx = (X + off) % sw
    cy = Y % rh
    sid = (((X + off) // sw) % 8) + ry * 8
    r = np.random.default_rng(401)
    bv = r.uniform(0.7, 1.2, 100)[sid % 100]
    c = col((0.23, 0.21, 0.20))[None, None] * (bv * (1 + 0.15 * fnoise(h, w, 1.5, 402)))[..., None]
    c[..., 2] *= 1 + r.normal(0, 0.03, 100)[sid % 100]
    shadow = smooth(0, rh * 0.45, cy.astype(np.float32))              # darker at the top (under the overlapping row)
    jt = smooth(0.8, 3.0, np.minimum(cx, sw - 1 - cx).astype(np.float32))
    c *= (0.55 + 0.45 * shadow)[..., None] * (0.55 + 0.45 * jt)[..., None]
    moss = smooth(1.5, 2.4, bnoise(h, w, 12, 12, 403))
    c = lerp(c, col((0.14, 0.22, 0.09)), moss * 0.35)
    return np.clip(shade(c, shadow * 1.6 + jt * 0.4, 0.7), 0, 1)


def gen_iron():
    h = w = 256
    a = 0.055 + 0.025 * fnoise(h, w, 1.6, 411)
    rust = smooth(1.5, 2.6, bnoise(h, w, 3, 3, 412))
    c = np.stack([a, a * 1.02, a * 1.08], -1)
    c = lerp(c, col((0.20, 0.09, 0.045)), rust * 0.55)
    sheen = smooth(0.5, 1.5, bnoise(h, w, 30, 3, 413))
    c = c * (1 + 0.5 * sheen[..., None])
    return np.clip(shade(c, fnoise(h, w, 1.2, 414) * 0.3, 0.6), 0, 1)


def gen_metal():
    h = w = 256
    n = bnoise(h, w, 40, 1.2, 421)
    c = col((0.52, 0.54, 0.56))[None, None] * (1 + 0.14 * n + 0.05 * fnoise(h, w, 1.4, 422))[..., None]
    c *= (1 - 0.22 * smooth(1.3, 2.4, bnoise(h, w, 6, 6, 423)))[..., None]
    return np.clip(c, 0, 1)


def gen_bark():
    h = w = 256
    n = bnoise(h, w, 2.0, 40, 431)
    f = fnoise(h, w, 1.6, 432)
    ridge = 1 - np.abs(np.sin(np.arange(w)[None, :] / w * TAU * 7 + 2.2 * f + 1.4 * n))
    c = col((0.19, 0.145, 0.105))[None, None] * (0.55 + 0.55 * ridge + 0.12 * f)[..., None]
    lich = smooth(1.5, 2.4, bnoise(h, w, 10, 10, 433))
    c = lerp(c, col((0.45, 0.50, 0.38)), lich * 0.30)
    return np.clip(shade(c, ridge * 2.0, 0.8), 0, 1)


# ------------------------------------------------------------------------------------------------ foliage (alpha)
def _leaf_poly(cx, cy, L, Wd, ang, n=14, tip=0.25, serr=0.0):
    pts = []
    for s in (1, -1):
        rng = range(n + 1) if s == 1 else range(n, -1, -1)
        for k in rng:
            t = k / n
            hw = Wd * 0.5 * (np.sin(np.pi * t ** 0.85) ** 0.9) * (1 - tip * t)
            hw *= 1 + serr * (1 if k % 2 else -1) * 0.4
            x, y = t * L, s * hw
            pts.append((cx + x * np.cos(ang) - y * np.sin(ang), cy + x * np.sin(ang) + y * np.cos(ang)))
    return pts


def _draw_leaf(d, cx, cy, L, Wd, ang, color, vein, tip=0.25, serr=0.0):
    d.polygon(_leaf_poly(cx, cy, L, Wd, ang, tip=tip, serr=serr), fill=color)
    x1, y1 = cx + L * 0.92 * np.cos(ang), cy + L * 0.92 * np.sin(ang)
    d.line([(cx, cy), (x1, y1)], fill=vein, width=max(1, int(L / 28)))
    for t in (0.3, 0.5, 0.7):
        for s in (1, -1):
            a2 = ang + s * 0.8
            x0, y0 = cx + L * t * np.cos(ang), cy + L * t * np.sin(ang)
            d.line([(x0, y0), (x0 + Wd * 0.4 * np.cos(a2), y0 + Wd * 0.4 * np.sin(a2))], fill=vein, width=1)


def _cluster(size, seed, nleaf, L, Wd, cols, twig=(0.20, 0.14, 0.08), serr=0.0, tip=0.25, spread=0.46, base_y=0.93, rise=0.82, birch=False):
    ss = 2
    S = size * ss
    r = np.random.default_rng(seed)
    rgb = Image.new('RGB', (S, S), (0, 0, 0))
    al = Image.new('L', (S, S), 0)
    dr, da = ImageDraw.Draw(rgb), ImageDraw.Draw(al)
    # twigs
    stems = []
    for k in range(7):
        a0 = -np.pi / 2 + r.normal(0, 0.55)
        x0, y0 = S * (0.5 + r.normal(0, 0.05)), S * base_y
        ln = S * r.uniform(0.35, rise)
        pts = [(x0, y0)]
        for i in range(1, 9):
            a0 += r.normal(0, 0.12)
            pts.append((pts[-1][0] + np.cos(a0) * ln / 8, pts[-1][1] + np.sin(a0) * ln / 8))
        stems.append(pts)
        tw = tuple(int(255 * c) for c in twig)
        dr.line(pts, fill=tw, width=max(2, int(S / 150)))
        da.line(pts, fill=255, width=max(2, int(S / 150)))
    # leaves drawn from the back (dark) to the front (light)
    items = []
    for i in range(nleaf):
        st = stems[r.integers(0, len(stems))]
        p = st[r.integers(2, len(st))]
        ang = r.uniform(0, TAU)
        items.append((p[0] + r.normal(0, S * 0.06), p[1] + r.normal(0, S * 0.06), ang, r.random()))
    items.sort(key=lambda t: t[3])
    for x, y, ang, z in items:
        base = np.array(cols[0]) * (1 - z) + np.array(cols[1]) * z
        base = base * (0.88 + 0.24 * r.random())
        base = np.clip(base, 0, 1)
        colr = tuple(int(255 * c) for c in base)
        vein = tuple(int(255 * c * 0.75) for c in base)
        l = L * ss * r.uniform(0.8, 1.2)
        _draw_leaf(dr, x, y, l, Wd * ss * r.uniform(0.85, 1.15), ang, colr, vein, tip=tip, serr=serr)
        _draw_leaf(da, x, y, l, Wd * ss * 1.0, ang, 255, 255, tip=tip, serr=serr) if False else da.polygon(_leaf_poly(x, y, l, Wd * ss, ang, tip=tip, serr=serr), fill=255)
    rgb = rgb.resize((size, size), Image.LANCZOS)
    al = al.resize((size, size), Image.LANCZOS)
    a = np.asarray(al, np.float32) / 255.0
    c = np.asarray(rgb, np.float32) / 255.0
    c = c / np.maximum(a[..., None], 1e-3) * np.minimum(a[..., None] * 1.0, 1.0) if False else c
    # un-premultiply (PIL resize of black background darkens the edges)
    c = np.where(a[..., None] > 0.02, np.clip(c / np.maximum(a[..., None], 0.02), 0, 1), c)
    a = np.clip((a - 0.12) * 1.25, 0, 1)
    return pack(c, a)


def gen_leaf_oak():
    return _cluster(512, 501, 150, 74, 40, ((0.05, 0.14, 0.03), (0.30, 0.50, 0.10)), serr=0.5, tip=0.35)


def gen_leaf_birch():
    return _cluster(512, 511, 210, 46, 30, ((0.12, 0.26, 0.05), (0.52, 0.66, 0.16)), twig=(0.75, 0.72, 0.65), tip=0.55, serr=0.9)


def gen_frond():
    """palm frond: rachis along the x axis, dense lancet leaflets (filled polygons) angled towards the tip"""
    size = 512
    ss = 2
    S = size * ss
    img = Image.new('RGB', (S, S), (0, 0, 0))
    al = Image.new('L', (S, S), 0)
    d, da = ImageDraw.Draw(img), ImageDraw.Draw(al)
    r = np.random.default_rng(521)
    y0 = S / 2
    n = 70
    for i in range(n):
        t = i / (n - 1)
        x = S * (0.02 + 0.94 * t)
        L = S * 0.50 * np.sin(np.pi * (0.06 + 0.92 * t) ** 0.85) * (1 - 0.1 * t) + S * 0.012
        for s in (1, -1):
            sweep = 0.55 + 0.25 * t                      # leaflets lean towards the tip
            tip = np.array((x + np.sin(sweep) * L * 0.62, y0 + s * np.cos(sweep) * L))
            base = np.array((x, y0))
            mid = (base + tip) / 2 + np.array((0.0, s * L * 0.02))
            nrm = np.array((-(tip - base)[1], (tip - base)[0]))
            nrm = nrm / np.linalg.norm(nrm) * (S / 105) * (1 - 0.30 * t)
            col = np.clip(np.array((0.10, 0.36, 0.08)) * (0.75 + 0.5 * t) * (0.88 + 0.24 * r.random()), 0, 1)
            c = tuple(int(255 * v) for v in col)
            pts = [tuple(base), tuple(mid + nrm), tuple(tip), tuple(mid - nrm)]
            d.polygon(pts, fill=c)
            da.polygon(pts, fill=255)
            d.line([tuple(base), tuple(tip)], fill=tuple(int(v * 1.5) for v in c), width=2)
    d.line([(S * 0.0, y0), (S * 0.99, y0)], fill=(70, 95, 35), width=int(S / 70))
    da.line([(S * 0.0, y0), (S * 0.99, y0)], fill=255, width=int(S / 70))
    rgb = np.asarray(img.resize((size, size), Image.LANCZOS), np.float32) / 255.0
    a = np.asarray(al.resize((size, size), Image.LANCZOS), np.float32) / 255.0
    rgb = np.where(a[..., None] > 0.02, np.clip(rgb / np.maximum(a[..., None], 0.02), 0, 1), rgb)
    return pack(rgb, np.clip((a - 0.1) * 1.3, 0, 1))


def _blade_img(size_w, size_h, seed, n, cols, hmin=0.45, hmax=0.98, wmax=0.045, bend=0.25, heads=0):
    ss = 2
    W, H = size_w * ss, size_h * ss
    r = np.random.default_rng(seed)
    img = Image.new('RGB', (W, H), (0, 0, 0))
    al = Image.new('L', (W, H), 0)
    d, da = ImageDraw.Draw(img), ImageDraw.Draw(al)
    order = sorted(range(n), key=lambda i: r.random())
    for i in order:
        x0 = W * (0.5 + r.normal(0, 0.12))
        hh = H * r.uniform(hmin, hmax)
        ww = W * r.uniform(0.4, 1.0) * wmax
        lean = r.normal(0, bend) * W * 0.35
        pts_l, pts_r = [], []
        for k in range(12):
            t = k / 11
            x = x0 + lean * t * t
            y = H - hh * t
            wd = ww * (1 - t) ** 0.8 * (1 if t > 0 else 1)
            pts_l.append((x - wd, y))
            pts_r.append((x + wd, y))
        poly = pts_l + pts_r[::-1]
        z = r.random()
        base = np.array(cols[0]) * (1 - z) + np.array(cols[1]) * z
        c = tuple(int(255 * v) for v in np.clip(base * (0.85 + 0.3 * r.random()), 0, 1))
        d.polygon(poly, fill=c)
        da.polygon(poly, fill=255)
        d.line([(x0, H), (x0 + lean, H - hh)], fill=tuple(int(v * 0.8) for v in c), width=1)
    for hx in range(heads):                        # cattail heads
        x = W * (0.3 + 0.4 * (hx + 0.5) / max(heads, 1))
        y = H * r.uniform(0.04, 0.2)
        d.line([(x, H), (x, y + H * 0.1)], fill=(60, 110, 40), width=int(W / 70))
        da.line([(x, H), (x, y + H * 0.1)], fill=255, width=int(W / 70))
        d.rounded_rectangle([x - W * 0.028, y, x + W * 0.028, y + H * 0.13], radius=int(W * 0.026), fill=(88, 50, 28))
        da.rounded_rectangle([x - W * 0.028, y, x + W * 0.028, y + H * 0.13], radius=int(W * 0.026), fill=255)
    rgb = np.asarray(img.resize((size_w, size_h), Image.LANCZOS), np.float32) / 255.0
    a = np.asarray(al.resize((size_w, size_h), Image.LANCZOS), np.float32) / 255.0
    rgb = np.where(a[..., None] > 0.02, np.clip(rgb / np.maximum(a[..., None], 0.02), 0, 1), rgb)
    return pack(rgb, np.clip((a - 0.1) * 1.3, 0, 1))


def gen_grassblade():
    return _blade_img(256, 256, 531, 44, ((0.10, 0.27, 0.05), (0.45, 0.62, 0.17)), 0.35, 0.98, 0.05, 0.3)


def gen_reed():
    return _blade_img(256, 512, 541, 18, ((0.08, 0.30, 0.07), (0.38, 0.58, 0.15)), 0.55, 1.0, 0.035, 0.18, heads=3)


def gen_flowers():
    size = 512
    ss = 2
    S = size * ss
    q = S // 2
    img = Image.new('RGB', (S, S), (0, 0, 0))
    al = Image.new('L', (S, S), 0)
    d, da = ImageDraw.Draw(img), ImageDraw.Draw(al)
    r = np.random.default_rng(551)
    schemes = [((0.85, 0.10, 0.12), (0.98, 0.35, 0.30)), ((0.98, 0.88, 0.15), (1.0, 0.98, 0.55)), ((0.88, 0.38, 0.62), (0.98, 0.72, 0.85)),
               ((0.55, 0.30, 0.85), (0.92, 0.88, 0.98))]
    for qi, (c0, c1) in enumerate(schemes):
        ox, oy = (qi % 2) * q, (qi // 2) * q
        # leafy mound
        for k in range(90):
            x = ox + q * (0.5 + r.normal(0, 0.20))
            y = oy + q * (0.95 - abs(r.normal(0, 0.28)) * 0.9)
            if not (ox + 6 < x < ox + q - 6 and oy + 6 < y < oy + q - 4):
                continue
            ang = r.uniform(-np.pi, 0) if r.random() < 0.8 else r.uniform(0, np.pi)
            g = np.array((0.09, 0.26, 0.06)) * (0.8 + 0.7 * r.random())
            _draw_leaf(d, x, y, q * 0.15, q * 0.07, ang, tuple(int(255 * v) for v in g), tuple(int(200 * v) for v in g), tip=0.3)
            da.polygon(_leaf_poly(x, y, q * 0.15, q * 0.07, ang, tip=0.3), fill=255)
        # blossoms on stems
        for k in range(46):
            x = ox + q * (0.5 + r.normal(0, 0.2))
            y = oy + q * (0.12 + r.random() * 0.62)
            if not (ox + 14 < x < ox + q - 14 and oy + 10 < y < oy + q - 40):
                continue
            rad = q * r.uniform(0.032, 0.058)
            d.line([(x, y), (x + r.normal(0, 4), min(oy + q - 2, y + q * 0.30))], fill=(40, 100, 30), width=2)
            da.line([(x, y), (x + r.normal(0, 4), min(oy + q - 2, y + q * 0.30))], fill=255, width=2)
            z = r.random()
            cc = np.array(c0) * (1 - z) + np.array(c1) * z
            for p in range(6):
                a = p * TAU / 6 + r.uniform(0, 1)
                px, py = x + np.cos(a) * rad * 0.85, y + np.sin(a) * rad * 0.85
                d.ellipse([px - rad * 0.62, py - rad * 0.62, px + rad * 0.62, py + rad * 0.62], fill=tuple(int(255 * v) for v in np.clip(cc * (0.8 + 0.3 * r.random()), 0, 1)))
                da.ellipse([px - rad * 0.62, py - rad * 0.62, px + rad * 0.62, py + rad * 0.62], fill=255)
            d.ellipse([x - rad * 0.35, y - rad * 0.35, x + rad * 0.35, y + rad * 0.35], fill=(235, 190, 40) if qi != 1 else (190, 100, 20))
    rgb = np.asarray(img.resize((size, size), Image.LANCZOS), np.float32) / 255.0
    a = np.asarray(al.resize((size, size), Image.LANCZOS), np.float32) / 255.0
    rgb = np.where(a[..., None] > 0.02, np.clip(rgb / np.maximum(a[..., None], 0.02), 0, 1), rgb)
    return pack(rgb, np.clip((a - 0.1) * 1.3, 0, 1))


def gen_lily():
    size = 512
    ss = 2
    S = size * ss
    img = Image.new('RGB', (S, S), (0, 0, 0))
    al = Image.new('L', (S, S), 0)
    d, da = ImageDraw.Draw(img), ImageDraw.Draw(al)
    r = np.random.default_rng(561)
    spots = [(0.25, 0.27, 0.19), (0.72, 0.22, 0.15), (0.50, 0.58, 0.20), (0.20, 0.76, 0.13), (0.82, 0.74, 0.17), (0.60, 0.92, 0.07), (0.92, 0.45, 0.08)]
    for (cx, cy, rr) in spots:
        cx, cy, rr = cx * S, cy * S, rr * S
        notch = r.uniform(0, TAU)
        pts = [(cx, cy)]
        for k in range(0, 41):
            a = notch + 0.22 + (TAU - 0.44) * k / 40
            pts.append((cx + np.cos(a) * rr, cy + np.sin(a) * rr * 0.92))
        g = np.array((0.08, 0.30, 0.10)) * (0.85 + 0.35 * r.random())
        d.polygon(pts, fill=tuple(int(255 * v) for v in g))
        da.polygon(pts, fill=255)
        for k in range(14):
            a = notch + 0.3 + (TAU - 0.6) * k / 13
            d.line([(cx, cy), (cx + np.cos(a) * rr * 0.92, cy + np.sin(a) * rr * 0.85)], fill=tuple(int(255 * v * 0.7) for v in g), width=2)
        d.ellipse([cx - rr * 0.5, cy - rr * 0.5, cx + rr * 0.1, cy + rr * 0.1], fill=tuple(int(255 * min(1, v * 1.25)) for v in g))
    for (cx, cy, rr) in ((0.36, 0.44, 0.06), (0.74, 0.60, 0.05)):             # lotus flowers
        cx, cy, rr = cx * S, cy * S, rr * S
        for ring, (n, col_, sc) in enumerate(((8, (0.95, 0.55, 0.72), 1.0), (6, (0.99, 0.78, 0.88), 0.72), (5, (1.0, 0.92, 0.55), 0.38))):
            for p in range(n):
                a = p * TAU / n + ring * 0.3
                pts = _leaf_poly(cx, cy, rr * sc * 1.9, rr * sc * 0.95, a, n=10, tip=0.5)
                d.polygon(pts, fill=tuple(int(255 * v) for v in col_))
                da.polygon(pts, fill=255)
    rgb = np.asarray(img.resize((size, size), Image.LANCZOS), np.float32) / 255.0
    a = np.asarray(al.resize((size, size), Image.LANCZOS), np.float32) / 255.0
    rgb = np.where(a[..., None] > 0.02, np.clip(rgb / np.maximum(a[..., None], 0.02), 0, 1), rgb)
    return pack(rgb, np.clip((a - 0.1) * 1.3, 0, 1))


def gen_water():
    h = w = 512
    n = fnoise(h, w, 2.0, 571)
    rip = 1 - np.abs(np.sin((bnoise(h, w, 14, 14, 572) * 2.2 + np.arange(w)[None, :] / w * TAU * 3)))
    sky = np.clip(0.5 + 0.5 * bnoise(h, w, 40, 40, 573), 0, 1)
    c = lerp(col((0.035, 0.13, 0.13)), col((0.10, 0.30, 0.34)), sky * 0.7)
    c = c + (rip ** 8 * 0.20)[..., None] * col((0.7, 0.85, 0.95))
    alg = smooth(1.2, 2.4, bnoise(h, w, 16, 16, 574))
    c = lerp(c, col((0.07, 0.22, 0.08)), alg * 0.5)
    a = np.clip(0.72 + 0.12 * n - 0.1 * alg + 0.15 * rip ** 10, 0.5, 0.9)
    return np.concatenate([np.clip(c, 0, 1), a[..., None]], -1).astype(np.float32)


def gen_rubber(base, seed):
    h = w = 256
    sp = bnoise(h, w, 0.7, 0.7, seed)
    c = col(base)[None, None] * (1 + 0.14 * sp + 0.08 * fnoise(h, w, 1.5, seed + 1))[..., None]
    gr = smooth(1.6, 2.4, bnoise(h, w, 1.0, 1.0, seed + 2))
    c = lerp(c, c * 1.25, gr * 0.5)
    c *= (1 - 0.15 * smooth(0.8, 2.0, bnoise(h, w, 24, 24, seed + 3)))[..., None]
    return np.clip(c, 0, 1)


def gen_rubber_blue():
    return gen_rubber((0.15, 0.29, 0.44), 581)


def gen_rubber_orange():
    return gen_rubber((0.82, 0.38, 0.12), 585)


def gen_paint(base, seed):
    h = w = 128
    n = fnoise(h, w, 1.5, seed)
    c = col(base)[None, None] * (1 + 0.07 * n)[..., None]
    chip = smooth(1.9, 2.7, bnoise(h, w, 2.5, 2.5, seed + 1))
    c = lerp(c, col((0.55, 0.55, 0.55)), chip * 0.5)
    c *= (1 - 0.15 * smooth(0.8, 2.0, bnoise(h, w, 12, 12, seed + 2)))[..., None]
    return np.clip(c, 0, 1)


def gen_paint_red():
    return gen_paint((0.72, 0.07, 0.06), 591)


def gen_paint_yellow():
    return gen_paint((0.93, 0.74, 0.08), 592)


def gen_paint_blue():
    return gen_paint((0.07, 0.25, 0.70), 593)


def gen_paint_green():
    return gen_paint((0.08, 0.30, 0.17), 594)


def gen_awning():
    h = w = 256
    X = np.arange(w)[None, :].repeat(h, 0)
    stripe = ((X * 8) // w) % 2
    c = np.where(stripe[..., None] == 1, col((0.80, 0.07, 0.08)), col((0.95, 0.94, 0.90)))
    weave = 0.5 + 0.5 * np.sin(np.arange(h)[:, None] * 2.2) * np.sin(np.arange(w)[None, :] * 2.2)
    c = c * (0.90 + 0.10 * weave)[..., None] * (1 + 0.05 * fnoise(h, w, 1.5, 601))[..., None]
    c *= (1 - 0.25 * smooth(0.0, 12, np.abs(np.arange(h)[:, None] - h).astype(np.float32)))[..., None] if False else 1
    return np.clip(c, 0, 1)


def gen_plaster():
    h = w = 256
    n = fnoise(h, w, 1.6, 611)
    c = col((0.88, 0.82, 0.68))[None, None] * (1 + 0.06 * n + 0.03 * bnoise(h, w, 0.8, 0.8, 612))[..., None]
    Y = np.arange(h)[:, None] / h
    c *= (1 - 0.35 * smooth(0.82, 1.0, Y))[..., None]                     # dirt at the foot of the wall
    c *= (1 - 0.15 * smooth(1.0, 2.2, bnoise(h, w, 4, 40, 613)))[..., None]
    return np.clip(c, 0, 1)


def gen_glass():
    h = w = 128
    Y = np.arange(h)[:, None] / h
    X = np.arange(w)[None, :] / w
    c = lerp(np.broadcast_to(col((0.45, 0.62, 0.70)), (h, w, 3)).copy(), np.broadcast_to(col((0.12, 0.20, 0.26)), (h, w, 3)).copy(), np.clip(Y, 0, 1)[..., 0] if False else np.broadcast_to(Y, (h, w)))
    streak = smooth(0.0, 0.05, np.abs((X + Y * 0.6) % 0.5 - 0.25) - 0.18)
    c = c * (1 - 0.3 * (1 - np.broadcast_to(streak, (h, w))))[..., None] + 0.12 * np.broadcast_to(1 - streak, (h, w))[..., None]
    return np.clip(c, 0, 1)


def _text_img(w, h, bg, draw_fn):
    im = Image.new('RGB', (w, h), bg)
    draw_fn(ImageDraw.Draw(im), w, h)
    return np.asarray(im, np.float32) / 255.0


def gen_sign_info():
    def fn(d, w, h):
        d.rectangle([0, 0, w, h], fill=(36, 74, 52))
        d.rectangle([10, 10, w - 10, h - 10], outline=(236, 228, 200), width=5)
        d.rectangle([22, 22, w - 22, 86], fill=(236, 228, 200))
        d.text((w // 2, 54), 'PARK MAP', font=ImageFont.truetype(FONT_B, 44), fill=(36, 74, 52), anchor='mm')
        # miniature map: grass, paths, pond, fountain
        mx0, my0, mx1, my1 = 40, 106, w - 40, h - 118
        d.rectangle([mx0, my0, mx1, my1], fill=(120, 168, 86), outline=(236, 228, 200), width=3)
        cx = (mx0 + mx1) // 2
        d.line([(cx, my1), (cx, my0 + 20)], fill=(222, 210, 180), width=14)
        d.line([(cx, my0 + 150), (mx1 - 70, my0 + 150)], fill=(222, 210, 180), width=9)
        d.line([(mx0 + 40, my0 + 90), (cx, my0 + 90)], fill=(222, 210, 180), width=9)
        d.ellipse([cx - 28, my0 + 62, cx + 28, my0 + 118], fill=(222, 210, 180))
        d.ellipse([cx - 16, my0 + 74, cx + 16, my0 + 106], fill=(80, 150, 200))
        d.ellipse([mx1 - 150, my0 + 70, mx1 - 30, my0 + 130], fill=(70, 140, 190))
        d.rectangle([mx0 + 20, my0 + 70, mx0 + 52, my0 + 102], fill=(110, 80, 50))
        d.rectangle([mx1 - 110, my0 + 20, mx1 - 30, my0 + 56], fill=(220, 120, 40))
        d.rectangle([cx - 70, my0 + 40, cx - 44, my0 + 56], fill=(200, 60, 60))
        f = ImageFont.truetype(FONT_R, 20)
        for i, (txt, c) in enumerate((('Fountain', (80, 150, 200)), ('Pond & Bridge', (70, 140, 190)), ('Gazebo', (110, 80, 50)), ('Playground', (220, 120, 40)), ('Kiosk', (200, 60, 60)))):
            yy = my1 + 20 + i * 15 if False else h - 108 + (i % 3) * 30
            xx = 36 + (i // 3) * 250
            d.rectangle([xx, yy, xx + 18, yy + 18], fill=c)
            d.text((xx + 28, yy + 9), txt, font=f, fill=(236, 228, 200), anchor='lm')
        d.text((w // 2, h - 22), 'Open 06:00 - 22:00', font=ImageFont.truetype(FONT_R, 18), fill=(236, 228, 200), anchor='mm')
    return _text_img(512, 512, (36, 74, 52), fn)


def gen_sign_kiosk():
    def fn(d, w, h):
        d.rectangle([0, 0, w, h], fill=(36, 30, 28))
        d.rounded_rectangle([6, 6, w - 6, h - 6], radius=10, outline=(240, 190, 60), width=5)
        d.text((w // 2, h // 2 - 6), 'KIOSK', font=ImageFont.truetype(FONT_B, 54), fill=(250, 210, 80), anchor='mm')
        d.text((w // 2, h - 22), 'coffee  *  ice cream  *  snacks', font=ImageFont.truetype(FONT_R, 17), fill=(235, 225, 200), anchor='mm')
    return _text_img(512, 128, (36, 30, 28), fn)


def gen_sign_park():
    def fn(d, w, h):
        d.rectangle([0, 0, w, h], fill=(26, 52, 40))
        d.rectangle([8, 8, w - 8, h - 8], outline=(222, 190, 100), width=4)
        d.text((w // 2, h // 2 - 8), 'CENTRAL PARK', font=ImageFont.truetype(FONT_B, 40), fill=(232, 200, 110), anchor='mm')
        d.text((w // 2, h - 24), 'WELCOME', font=ImageFont.truetype(FONT_R, 18), fill=(232, 224, 200), anchor='mm')
    return _text_img(512, 128, (26, 52, 40), fn)


def gen_manhole():
    h = w = 128
    Y, X = np.mgrid[0:h, 0:w]
    d = np.hypot(X - w / 2, Y - h / 2) / (w / 2)
    c = np.full((h, w, 3), 0.075, np.float32)
    ring = smooth(0.80, 0.84, d) * (1 - smooth(0.93, 0.96, d))
    grid = (np.abs(np.sin(X * 0.5)) * np.abs(np.sin(Y * 0.5)) > 0.3) & (d < 0.78)
    c = c * (1 + 0.8 * grid[..., None]) * (1 + 0.5 * ring[..., None])
    c = lerp(c, col((0.3, 0.17, 0.10)), smooth(0.9, 1.0, d) * 0.5)
    c += 0.04 * fnoise(h, w, 1.5, 621)[..., None]
    return np.clip(c, 0, 1)


def gen_cone():
    h = w = 128
    Y = np.arange(h)[:, None].repeat(w, 1) / h
    c = np.broadcast_to(col((0.95, 0.38, 0.05)), (h, w, 3)).copy()
    band = ((Y > 0.36) & (Y < 0.52)) | ((Y > 0.66) & (Y < 0.78))
    c[band] = col((0.94, 0.94, 0.92))
    c *= (1 + 0.06 * fnoise(h, w, 1.5, 631))[..., None]
    return np.clip(c, 0, 1)


def gen_spray():
    h, w = 256, 128
    X = np.arange(w)[None, :]
    Y = np.arange(h)[:, None]
    n = bnoise(h, w, 1.2, 14, 641)
    n2 = bnoise(h, w, 0.8, 6, 642)
    mask = np.clip(0.5 + 0.55 * n + 0.3 * n2, 0, 1) ** 1.5
    prof = np.exp(-((X - w / 2) / (w * 0.36)) ** 2)
    a = mask * prof * smooth(0, 30, Y.astype(np.float32)) * smooth(0, 30, (h - Y).astype(np.float32)) * 0.85
    rgb = np.broadcast_to(col((0.92, 0.97, 1.0)), (h, w, 3)) * (0.85 + 0.15 * n2[..., None])
    return np.concatenate([np.clip(rgb, 0, 1), np.clip(a, 0, 1)[..., None]], -1).astype(np.float32)


def gen_lamp():
    h = w = 64
    n = fnoise(h, w, 1.5, 651)
    Y = np.arange(h)[:, None] / h
    c = col((1.0, 0.93, 0.74))[None, None] * (0.86 + 0.08 * n[..., None] + 0.06 * np.sin(Y * 9)[..., None])
    return np.clip(np.broadcast_to(c, (h, w, 3)), 0, 1)


def gen_birchbark():
    h = w = 256
    n = bnoise(h, w, 1.5, 30, 661)
    base = col((0.86, 0.84, 0.78))[None, None] * (1 + 0.06 * fnoise(h, w, 1.5, 662))[..., None]
    marks = smooth(1.3, 2.0, bnoise(h, w, 28, 2.0, 663) + 0.4 * n)
    lines = smooth(1.6, 2.4, bnoise(h, w, 22, 1.6, 664))
    c = lerp(base, col((0.07, 0.065, 0.06)), np.maximum(marks * 0.75, lines * 0.9))
    return np.clip(shade(c, n * 0.5, 0.5), 0, 1)


def gen_sand():
    h = w = 256
    n = fnoise(h, w, 1.4, 671)
    c = col((0.78, 0.68, 0.48))[None, None] * (1 + 0.10 * n + 0.08 * bnoise(h, w, 0.7, 0.7, 672))[..., None]
    c *= (1 - 0.12 * smooth(0.5, 2.0, bnoise(h, w, 14, 14, 673)))[..., None]
    return np.clip(c, 0, 1)


def gen_duck():
    h = w = 64
    Y = np.arange(h)[:, None].repeat(w, 1) / h
    belly = col((0.92, 0.90, 0.84))
    back = col((0.40, 0.31, 0.22))
    c = np.where((Y < 0.34)[..., None], belly, back) * (1 + 0.10 * fnoise(h, w, 1.2, 681))[..., None]
    return np.clip(c, 0, 1)


GEN = {n: globals()['gen_' + n[3:]] for n in NAMES if 'gen_' + n[3:] in globals()}


def generate_all():
    out = {}
    for n in NAMES:
        a = np.clip(GEN[n](), 0, 1)
        out[n] = (a * 255 + 0.5).astype(np.uint8)
    return out
