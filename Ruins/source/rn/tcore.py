# Created by: Arena.ai Agent Mode (AI) - Ruins MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# tcore.py - shared helpers of the procedural texture generators: periodic noise, relief shading baked into the colour
#            (San Andreas has no normal maps), weathering (grime in crevices, rain streaks, rust bleed, moss, dust),
#            alpha packing with colour bleeding (no dark / white fringes with DXT5 + mip-mapping).
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib.noise import fnoise, bnoise, worley, smooth, scratches, FONT_B, FONT_R, FONT_M

TAU = np.pi * 2
F32 = np.float32


def col(rgb):
    return np.array(rgb, F32)


def lerp(a, b, t):
    return a + (b - a) * np.asarray(t, F32)[..., None]


def mix(c, rgb, t):
    """blend colour image c towards a constant colour with mask t"""
    return c + (col(rgb) - c) * np.asarray(t, F32)[..., None]


def n1(h, w, beta, seed):
    return fnoise(h, w, beta, seed).astype(F32)


def nb(h, w, sx, sy, seed):
    return bnoise(h, w, sx, sy, seed).astype(F32)


def shade(alb, height, strength=1.0, light=(-0.6, -0.8)):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    s = 1.0 + strength * (gx * light[0] + gy * light[1])
    return alb * np.clip(s, 0.4, 1.7)[..., None]


def gblur(a, sigma):
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    if a.ndim == 3:
        return np.stack([np.fft.irfft2(np.fft.rfft2(a[..., i]) * k, s=(h, w)) for i in range(a.shape[2])], -1).astype(F32)
    return np.fft.irfft2(np.fft.rfft2(a) * k, s=(h, w)).astype(F32)


def weather(c, hgt, seed, grime=0.5, streak=0.5, moss=0.0, rust=0.0, dust=0.25, streak_len=70):
    """standard aging pass.  c: HxWx3, hgt: relief (high = proud).  All periodic."""
    h, w = hgt.shape
    cav = smooth(0.15, -0.9, (hgt - gblur(hgt, 6)) / (hgt.std() + 1e-6))      # crevices
    c = c * (1 - grime * 0.55 * cav)[..., None]
    if streak > 0:
        st = smooth(0.4, 2.4, nb(h, w, 1.8, streak_len, seed + 1) + 0.35 * nb(h, w, 6, streak_len * 1.6, seed + 2))
        c = c * (1 - streak * 0.42 * st)[..., None]
        wet = smooth(1.2, 2.8, nb(h, w, 2.5, streak_len * 2, seed + 3))
        c = c * (1 - streak * 0.18 * wet)[..., None]
    if rust > 0:
        rs = smooth(0.9, 2.3, nb(h, w, 2.2, streak_len * 0.8, seed + 4) + 0.5 * nb(h, w, 9, 9, seed + 5))
        rc = lerp(col((0.30, 0.13, 0.05)), col((0.55, 0.27, 0.09)), np.clip(0.5 + 0.5 * n1(h, w, 1.4, seed + 6), 0, 1))
        c = lerp(c, rc, rs * rust)
    if moss > 0:
        m = smooth(0.7, 2.0, nb(h, w, 7, 7, seed + 7) + 0.7 * nb(h, w, 2, 2, seed + 8)) * (0.35 + 0.65 * cav)
        mc = lerp(col((0.10, 0.17, 0.05)), col((0.22, 0.32, 0.09)), np.clip(0.5 + 0.5 * n1(h, w, 1.2, seed + 9), 0, 1))
        c = lerp(c, mc, m * moss)
    if dust > 0:
        d = np.clip(0.5 + 0.5 * nb(h, w, 14, 14, seed + 10), 0, 1)
        c = mix(c, (0.50, 0.47, 0.42), dust * 0.30 * d)
    return c


def speckle(h, w, seed, amount=0.06, scale=0.7):
    return (nb(h, w, scale, scale, seed) * amount).astype(F32)


def bleed(rgb, a):
    img = (np.clip(rgb, 0, 1) * a[..., None]).astype(F32)
    out = rgb.copy()
    known = a > 0.5
    cur_i, cur_a = img, a
    for r in (2, 6, 14, 30):
        bi = gblur(cur_i, r)
        ba = np.clip(gblur(cur_a, r), 0, 1)
        est = bi / np.maximum(ba[..., None], 1e-4)
        use = (~known) & (ba > 0.02)
        out = np.where(use[..., None], est, out)
        known = known | use
    return np.where(known[..., None], out, rgb.mean((0, 1)))


def pack(rgb, a):
    return np.concatenate([np.clip(bleed(rgb, a), 0, 1), np.clip(a, 0, 1)[..., None]], -1).astype(F32)


def img_to_np(im):
    return np.asarray(im, F32) / 255.0


def draw_cracks(h, w, seed, n=12, length=(0.2, 0.6), width=1.4, branch=0.5, ss=2):
    """random wandering crack polylines (wrapped, with branches) -> 0..1 mask"""
    r = np.random.default_rng(seed)
    im = Image.new('L', (w * ss, h * ss), 0)
    d = ImageDraw.Draw(im)

    def walk(x, y, ang, L, wd, depth):
        pts = [(x, y)]
        steps = max(4, int(L / 6))
        for _ in range(steps):
            ang += r.normal(0, 0.35)
            x += np.cos(ang) * L / steps
            y += np.sin(ang) * L / steps
            pts.append((x, y))
            if depth < 2 and r.random() < branch / steps * 3:
                walk(x, y, ang + r.choice([-1, 1]) * r.uniform(0.5, 1.2), L * r.uniform(0.2, 0.5), wd * 0.6, depth + 1)
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d.line([((px + ox) * ss, (py + oy) * ss) for px, py in pts], fill=255, width=max(1, int(wd * ss)), joint='curve')
    for _ in range(n):
        walk(r.random() * w, r.random() * h, r.random() * TAU, r.uniform(*length) * max(h, w), width * r.uniform(0.7, 1.5), 0)
    im = im.resize((w, h), Image.BOX)
    return np.asarray(im, F32) / 255.0
