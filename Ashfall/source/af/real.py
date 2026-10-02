# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# real.py - the "realism pass" of the textures.
#   * photo(): turns a clean procedural albedo into something that reads as a photographed, weathered surface:
#     desaturation (real-world albedo is dull), tonal compression, band-limited sensor/micro grain, unsharp micro contrast,
#     slow large-scale tonal drift so a tile never looks like a repeating swatch.
#   * up2(): wrap-around 2x upsample (the grain is added AFTER it, at the final resolution -> genuinely finer detail).
#   * grass_card / leaf_card / ivy_card: foliage cards drawn blade by blade / leaf by leaf with per-element shading
#     (dark root, lit tip, translucent yellowing, midrib, edge darkening, depth ordering) instead of flat vector shapes.
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw
from lib.noise import fnoise, bnoise, white
from .tex_base import gblur, pack

TAU = 2 * np.pi
LUMA = np.array([0.299, 0.587, 0.114], np.float32)

# name -> (saturation, gain, contrast, grain, sharpen, drift)
GRADE = {
    'af_asphalt': (0.80, 0.95, 1.10, 0.20, 0.55, 0.10), 'af_road': (0.80, 0.95, 1.10, 0.20, 0.55, 0.10),
    'af_crosswalk': (0.75, 0.95, 1.08, 0.20, 0.50, 0.08), 'af_sidewalk': (0.72, 0.96, 1.08, 0.18, 0.55, 0.10),
    'af_curb': (0.72, 0.96, 1.06, 0.16, 0.5, 0.08), 'af_gravel': (0.70, 0.95, 1.08, 0.14, 0.5, 0.06),
    'af_dirt': (0.70, 0.92, 1.06, 0.20, 0.5, 0.12), 'af_grass': (0.58, 0.88, 1.08, 0.24, 0.6, 0.14),
    'af_moss': (0.62, 0.90, 1.05, 0.18, 0.5, 0.10),
    'af_concrete': (0.70, 0.96, 1.08, 0.18, 0.55, 0.10), 'af_panel': (0.70, 0.96, 1.08, 0.16, 0.5, 0.08),
    'af_brick': (0.62, 0.90, 1.10, 0.18, 0.55, 0.10), 'af_plaster_a': (0.52, 0.94, 1.06, 0.18, 0.5, 0.10),
    'af_plaster_b': (0.50, 0.90, 1.06, 0.18, 0.5, 0.10), 'af_plaster_c': (0.50, 0.92, 1.06, 0.18, 0.5, 0.10),
    'af_glass': (0.70, 1.0, 1.0, 0.05, 0.3, 0.0), 'af_glass_broken': (0.70, 1.0, 1.0, 0.05, 0.3, 0.0),
    'af_frame': (0.70, 0.95, 1.05, 0.12, 0.4, 0.05), 'af_interior': (0.8, 1.0, 1.0, 0.0, 0.0, 0.0),
    'af_rust': (0.50, 0.86, 1.10, 0.20, 0.55, 0.10), 'af_steel': (0.70, 0.92, 1.08, 0.14, 0.5, 0.06),
    'af_roofing': (0.70, 0.95, 1.06, 0.16, 0.5, 0.08), 'af_corrugated': (0.52, 0.90, 1.08, 0.16, 0.5, 0.08),
    'af_wood': (0.70, 0.92, 1.08, 0.16, 0.5, 0.08), 'af_bark': (0.70, 0.90, 1.10, 0.20, 0.6, 0.08),
    'af_car_red': (0.62, 0.86, 1.06, 0.06, 0.2, 0.10), 'af_car_blue': (0.58, 0.86, 1.08, 0.06, 0.2, 0.10),
    'af_car_white': (0.70, 0.92, 1.08, 0.06, 0.2, 0.10), 'af_car_green': (0.58, 0.86, 1.08, 0.06, 0.2, 0.10),
    'af_car_yellow': (0.58, 0.88, 1.08, 0.06, 0.2, 0.10), 'af_car_grey': (0.75, 0.92, 1.08, 0.06, 0.2, 0.08),
    'af_tire': (0.8, 1.0, 1.0, 0.1, 0.3, 0.0),
    'af_sign_street': (0.72, 0.88, 1.06, 0.12, 0.4, 0.05), 'af_sign_stop': (0.70, 0.86, 1.06, 0.12, 0.4, 0.05),
    'af_billboard': (0.68, 0.88, 1.06, 0.10, 0.4, 0.05), 'af_container': (0.62, 0.86, 1.08, 0.16, 0.5, 0.08),
    'af_barrier': (0.70, 0.94, 1.06, 0.14, 0.5, 0.06),
}
UP2 = {'af_asphalt', 'af_road', 'af_crosswalk', 'af_sidewalk', 'af_concrete', 'af_panel', 'af_brick', 'af_plaster_a',
       'af_plaster_b', 'af_plaster_c', 'af_grass', 'af_dirt', 'af_car_red', 'af_car_blue', 'af_car_white', 'af_car_green',
       'af_car_yellow', 'af_car_grey', 'af_rust', 'af_container'}


def up2(a):
    """2x upsample of a periodic image (wrap padding so the seam stays invisible)"""
    h, w = a.shape[:2]
    pad = 8
    p = np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='wrap')
    im = Image.fromarray((np.clip(p, 0, 1) * 255 + 0.5).astype(np.uint8)).resize(((w + 2 * pad) * 2, (h + 2 * pad) * 2), Image.BICUBIC)
    o = np.asarray(im, np.float32) / 255.0
    return o[pad * 2:pad * 2 + h * 2, pad * 2:pad * 2 + w * 2]


def _band(h, w, seed, s0, s1):
    """periodic band-pass noise (unit std)"""
    n = white(h, w, seed).astype(np.float32)
    b = gblur(n, s0) - gblur(n, s1)
    return b / (b.std() + 1e-9)


def photo(c, name):
    sat, gain, con, grain, sharp, drift = GRADE.get(name, (0.8, 0.95, 1.05, 0.12, 0.4, 0.05))
    c = np.asarray(c, np.float32)
    h, w = c.shape[:2]
    seed = (sum(map(ord, name)) * 7919) % 100000
    lum = (c * LUMA).sum(-1, keepdims=True)
    c = lum + (c - lum) * sat
    m = c.mean()
    c = (m + (c - m) * con) * gain
    if sharp > 0:                                           # micro contrast (unsharp mask, periodic)
        bl = np.stack([gblur(c[..., k], 1.4) for k in range(3)], -1)
        c = c + sharp * (c - bl)
    if grain > 0:
        l = np.clip((c * LUMA).sum(-1), 0, 1)
        g = 0.65 * _band(h, w, seed + 1, 0.55, 1.6) + 0.35 * _band(h, w, seed + 2, 1.5, 4.0)
        c = c * (1 + grain * 0.55 * g * (0.35 + 0.9 * l))[..., None]
    if drift > 0:                                           # slow tonal / tint drift: breaks the swatch look
        d = bnoise(h, w, 3, 3, seed + 3) * 0.6 + bnoise(h, w, 7, 7, seed + 4) * 0.4
        t = np.stack([1 + drift * d, 1 + drift * 0.6 * d, 1 + drift * 0.3 * d], -1)
        c = c * t
    return np.clip(c, 0, 1).astype(np.float32)


def finish(name, arr):
    """generator output -> final texture (float32 HxWx3 / HxWx4)"""
    a = np.asarray(arr, np.float32)
    rgb, al = a[..., :3], (a[..., 3] if a.shape[2] == 4 else None)
    if name in UP2:
        rgb = up2(rgb)
    rgb = photo(rgb, name)
    return rgb if al is None else np.concatenate([rgb, al[..., None]], -1)


# ------------------------------------------------------------------------------------------------ foliage cards
def _unpremul(img, al, size_w, size_h):
    rgb = np.asarray(img.resize((size_w, size_h), Image.LANCZOS), np.float32) / 255.0
    a = np.asarray(al.resize((size_w, size_h), Image.LANCZOS), np.float32) / 255.0
    rgb = np.where(a[..., None] > 0.02, np.clip(rgb / np.maximum(a[..., None], 0.02), 0, 1), rgb)
    return rgb, a


def _c8(v):
    return tuple(int(255 * x) for x in np.clip(v, 0, 1))


def grass_card(size_w, size_h, seed, n, pal, dead=0.0, hmin=0.35, hmax=1.0, spread=0.20, wmax=0.030, heads=0, ss=3):
    """pal = (root colour, mid colour, tip colour); blades are shaded along their length and across their width"""
    W, H = size_w * ss, size_h * ss
    r = np.random.default_rng(seed)
    img = Image.new('RGB', (W, H), (0, 0, 0))
    al = Image.new('L', (W, H), 0)
    d, da = ImageDraw.Draw(img), ImageDraw.Draw(al)
    root, mid, tip = (np.array(p) for p in pal)
    straw = [np.array((0.20, 0.15, 0.07)), np.array((0.38, 0.31, 0.15)), np.array((0.62, 0.55, 0.34))]
    blades = []
    for i in range(n):
        blades.append(dict(x0=W * (0.5 + r.normal(0, spread)), hh=H * r.uniform(hmin, hmax) ** 0.9, ww=W * wmax * r.uniform(0.45, 1.0),
                           lean=r.normal(0, 0.28) * W * 0.30, curl=r.normal(0, 0.5), z=r.random(), dead=r.random() < dead, hue=r.normal(0, 0.06)))
    blades.sort(key=lambda b: b['z'])                       # far (dark) first
    for b in blades:
        k = 14
        cols = straw if b['dead'] else (root, mid, tip)
        ptsl, ptsr, ctr = [], [], []
        for j in range(k + 1):
            t = j / k
            x = b['x0'] + b['lean'] * t * t + b['curl'] * W * 0.02 * np.sin(t * 3.1)
            y = H - b['hh'] * t
            wd = b['ww'] * (1 - t) ** 0.85 * (0.75 + 0.25 * (1 - t)) + 0.4
            ptsl.append((x - wd, y)); ptsr.append((x + wd, y)); ctr.append((x, y))
        depth = 0.50 + 0.50 * b['z']
        for j in range(k):
            t = (j + 0.5) / k
            col = (cols[0] * (1 - min(t * 2, 1)) + cols[1] * min(t * 2, 1)) if t < 0.5 else (cols[1] * (1 - (t - 0.5) * 2) + cols[2] * (t - 0.5) * 2)
            col = col * depth * (1 + np.array([b['hue'] * 1.2, b['hue'], -b['hue'] * 0.5]))
            lt = np.clip(col * 1.22 + 0.012, 0, 1)             # sunlit half
            dk = np.clip(col * 0.72, 0, 1)                     # shaded half
            a, bq = j, j + 1
            d.polygon([ptsl[a], ctr[a], ctr[bq], ptsl[bq]], fill=_c8(dk))
            d.polygon([ctr[a], ptsr[a], ptsr[bq], ctr[bq]], fill=_c8(lt))
            da.polygon([ptsl[a], ptsr[a], ptsr[bq], ptsl[bq]], fill=255)
    for hx in range(heads):                                # seed heads on the dry stalks
        x = W * (0.25 + 0.5 * r.random()); y0 = H * r.uniform(0.05, 0.3)
        d.line([(x, H), (x + r.normal(0, W * 0.02), y0 + H * 0.05)], fill=_c8(straw[1] * 0.9), width=max(2, int(W / 160)))
        da.line([(x, H), (x + r.normal(0, W * 0.02), y0 + H * 0.05)], fill=255, width=max(2, int(W / 160)))
        for q in range(14):
            yy = y0 + q * H * 0.012
            d.line([(x, yy), (x + r.normal(0, W * 0.025), yy - H * 0.02)], fill=_c8(straw[2] * 0.85), width=max(1, int(W / 300)))
            da.line([(x, yy), (x + r.normal(0, W * 0.025), yy - H * 0.02)], fill=255, width=max(1, int(W / 300)))
    rgb, a = _unpremul(img, al, size_w, size_h)
    return pack(rgb, np.clip((a - 0.08) * 1.25, 0, 1))


def _leaf_pts(cx, cy, L, Wd, ang, tip, n=12, skew=0.0):
    top, bot = [], []
    for k in range(n + 1):
        t = k / n
        env = np.sin(np.pi * t ** (0.8 + skew)) ** 0.85 * (1 - tip * t)
        top.append((t * L, Wd * 0.5 * env)); bot.append((t * L, -Wd * 0.5 * env))
    ca, sa = np.cos(ang), np.sin(ang)
    tr = lambda p: (cx + p[0] * ca - p[1] * sa, cy + p[0] * sa + p[1] * ca)
    return [tr(p) for p in top], [tr(p) for p in bot]


def leaf_card(size, seed, nleaf, L, Wd, pal, twig=(0.16, 0.12, 0.08), tip=0.30, rise=0.85, nstem=8, ss=3, hue=0.10, autumn=0.0):
    """leaf cluster on twigs; pal = (dark, light); every leaf has a lit half, a shaded half, a midrib, a darker rim and a
    depth factor (inner leaves darker -> the crown gets volume)"""
    S = size * ss
    r = np.random.default_rng(seed)
    img = Image.new('RGB', (S, S), (0, 0, 0))
    al = Image.new('L', (S, S), 0)
    d, da = ImageDraw.Draw(img), ImageDraw.Draw(al)
    stems = []
    for k in range(nstem):
        a0 = -np.pi / 2 + r.normal(0, 0.55)
        x0, y0 = S * (0.5 + r.normal(0, 0.05)), S * 0.94
        ln = S * r.uniform(0.35, rise)
        pts = [(x0, y0)]
        for i in range(1, 10):
            a0 += r.normal(0, 0.12)
            pts.append((pts[-1][0] + np.cos(a0) * ln / 9, pts[-1][1] + np.sin(a0) * ln / 9))
        stems.append(pts)
        d.line(pts, fill=_c8(np.array(twig)), width=max(2, int(S / 170)))
        da.line(pts, fill=255, width=max(2, int(S / 170)))
    items = []
    for i in range(nleaf):
        st = stems[r.integers(0, len(stems))]
        p = st[r.integers(2, len(st))]
        items.append((p[0] + r.normal(0, S * 0.07), p[1] + r.normal(0, S * 0.07), r.uniform(0, TAU), r.random() ** 0.8))
    items.sort(key=lambda t: t[3])
    dark, light = np.array(pal[0]), np.array(pal[1])
    for x, y, ang, z in items:
        base = dark * (1 - z) + light * z
        shift = r.normal(0, hue)                           # per-leaf yellow <-> blue-green drift
        base = base * (1 + np.array([shift * 1.3, shift * 0.6, -shift * 1.2]))
        if autumn and r.random() < autumn:
            base = np.array((0.42, 0.26, 0.08)) * (0.5 + 0.5 * z)
        base = base * (0.40 + 0.60 * z) * r.uniform(0.9, 1.1)
        l = L * ss * r.uniform(0.75, 1.2)
        w = Wd * ss * r.uniform(0.8, 1.2)
        top, bot = _leaf_pts(x, y, l, w, ang, tip, skew=r.uniform(-0.1, 0.25))
        rim = _c8(base * 0.55)
        d.polygon(top + bot[::-1], fill=rim)
        t2, b2 = _leaf_pts(x + np.cos(ang) * l * 0.02, y + np.sin(ang) * l * 0.02, l * 0.94, w * 0.80, ang, tip)
        d.polygon(t2 + [(x, y)], fill=_c8(np.clip(base * 1.18, 0, 1)))
        d.polygon(b2 + [(x, y)], fill=_c8(base * 0.82))
        x1, y1 = x + l * 0.90 * np.cos(ang), y + l * 0.90 * np.sin(ang)
        d.line([(x, y), (x1, y1)], fill=_c8(np.clip(base * 1.5 + 0.03, 0, 1)), width=max(1, int(l / 34)))
        da.polygon(top + bot[::-1], fill=255)
    rgb, a = _unpremul(img, al, size, size)
    return pack(rgb, np.clip((a - 0.12) * 1.3, 0, 1))
