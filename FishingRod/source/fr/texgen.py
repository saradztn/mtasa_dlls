# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# texgen.py - procedural PBR texture synthesis for the fishing rod.
#
# Each generator returns a Tex with:  albedo (sRGB 0..1) / height / rough / metal / ao
# which are then baked into the three maps that ship with the asset:
#   * diffuse  -> TXD (DXT1)     albedo with baked cavity/AO, micro-scratches, weave shading
#   * normal   -> DDS (DXT5nm)   X in alpha, Y in green (tangent space, +Y = image up)
#   * orm      -> DDS (DXT1)     R = AO / cavity, G = roughness, B = metallic
# All patterns are periodic (FFT / wrapped cellular noise) so they tile without seams.
# -----------------------------------------------------------------------------
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_M = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'


class Tex:
    def __init__(self, albedo, height, rough, metal, ao):
        self.albedo = np.clip(albedo, 0, 1).astype(np.float32)
        self.height = height.astype(np.float32)
        self.rough = np.clip(rough, 0.04, 1).astype(np.float32)
        self.metal = np.clip(metal, 0, 1).astype(np.float32)
        self.ao = np.clip(ao, 0, 1).astype(np.float32)


# ---------------------------------------------------------------------------
# noise toolbox (all tileable)
# ---------------------------------------------------------------------------
def _norm(a):
    a = a - a.mean()
    return a / (a.std() + 1e-9)


def fnoise(h, w, beta, seed):
    """1/f^beta noise, std = 1"""
    r = np.random.default_rng(seed)
    F = np.fft.rfft2(r.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    F = F / (f * max(h, w)) ** (beta / 2.0)
    F[0, 0] = 0
    return _norm(np.fft.irfft2(F, s=(h, w)))


def bnoise(h, w, sx, sy, seed):
    """band-limited (gaussian) noise with correlation lengths sx, sy in pixels, std = 1"""
    r = np.random.default_rng(seed)
    F = np.fft.rfft2(r.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * 2 * np.pi
    fx = np.fft.rfftfreq(w)[None, :] * 2 * np.pi
    F = F * np.exp(-0.5 * ((fx * sx) ** 2 + (fy * sy) ** 2))
    F[0, 0] = 0
    return _norm(np.fft.irfft2(F, s=(h, w)))


def white(h, w, seed):
    return np.random.default_rng(seed).standard_normal((h, w))


def worley(h, w, nx, ny, seed):
    """tileable cellular noise -> (F1, F2, id) with distances in cell units"""
    r = np.random.default_rng(seed)
    pts = r.random((ny, nx, 2))
    ids = r.random((ny, nx))
    X = (np.arange(w) + 0.5)[None, :] / w * nx
    Y = (np.arange(h) + 0.5)[:, None] / h * ny
    cx = np.floor(X).astype(int)
    cy = np.floor(Y).astype(int)
    F1 = np.full((h, w), 9.0)
    F2 = np.full((h, w), 9.0)
    ID = np.zeros((h, w))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ccx = cx + dx
            ccy = cy + dy
            px = ccx + pts[ccy % ny, ccx % nx, 0]
            py = ccy + pts[ccy % ny, ccx % nx, 1]
            d = np.sqrt((X - px) ** 2 + (Y - py) ** 2)
            upd = d < F1
            F2 = np.where(upd, F1, np.minimum(F2, d))
            ID = np.where(upd, ids[ccy % ny, ccx % nx], ID)
            F1 = np.where(upd, d, F1)
    return F1, F2, ID


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def scratches(h, w, n, lmin, lmax, seed, angle=None, spread=0.3, ss=2, width=1.0):
    """random thin scratches, wrapped; returns 0..1 mask"""
    r = np.random.default_rng(seed)
    im = Image.new('L', (w * ss, h * ss), 0)
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y = r.random() * w, r.random() * h
        ang = r.random() * np.pi if angle is None else angle + r.normal(0, spread)
        L = r.uniform(lmin, lmax)
        dx, dy = np.cos(ang) * L, np.sin(ang) * L
        val = int(r.uniform(60, 255))
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d.line([((x + ox) * ss, (y + oy) * ss), ((x + ox + dx) * ss, (y + oy + dy) * ss)], fill=val, width=max(1, int(width * ss)))
    im = im.resize((w, h), Image.BOX)
    return np.asarray(im, np.float32) / 255.0


def normal_from_height(hgt, strength):
    gx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5
    gy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 0.5      # d/drow (down)
    nx = -gx * strength
    ny = gy * strength                                          # +Y = image up  (== -d/dy_up... see render.c)
    nz = np.ones_like(nx)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / l, ny / l, nz / l


# ---------------------------------------------------------------------------
# bake: Tex -> (diffuse uint8 RGB, normal uint8 RGBA (DXT5nm), orm uint8 RGB)
# ---------------------------------------------------------------------------
def bake(t, nstrength):
    ao = t.ao
    diff = t.albedo * (0.80 + 0.20 * ao[..., None])
    # Game-diffuse lift: authored albedos for black materials (carbon, rubber, plastic) are physically
    # dark (<=12/255), which turns pure black under San Andreas' simple vertex lighting and hides all
    # micro-detail.  Real black rubber/carbon has ~0.04-0.05 linear albedo (~56 sRGB); lift towards it.
    diff = 0.045 + 0.955 * np.power(np.clip(diff, 0, 1), 0.72)
    diffuse = (np.clip(diff, 0, 1) * 255 + 0.5).astype(np.uint8)
    nx, ny, nz = normal_from_height(t.height, nstrength)
    n = np.zeros(t.height.shape + (4,), np.uint8)
    n[..., 0] = 0
    n[..., 1] = ((ny * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)
    n[..., 2] = 0
    n[..., 3] = ((nx * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)
    orm = np.stack([ao, t.rough, t.metal], -1)
    orm = (np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8)
    return diffuse, n, orm


def rgb(r, g, b, h, w):
    return np.stack([np.full((h, w), r), np.full((h, w), g), np.full((h, w), b)], -1).astype(np.float32)


# ---------------------------------------------------------------------------
# carbon fibre 2x2 twill
# ---------------------------------------------------------------------------
def carbon_twill(w, h, cx, cy, seed, base=0.085, gloss=0.17):
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    n1 = fnoise(h, w, 3.2, seed) * 0.040
    n2 = fnoise(h, w, 3.2, seed + 1) * 0.040
    gx = X / w * cx + n1
    gy = Y / h * cy + n2
    i = np.floor(gx).astype(int)
    j = np.floor(gy).astype(int)
    fx = gx - i
    fy = gy - j
    sv = (gy - i) % 4.0
    wv = smooth(0.0, 0.30, sv) - smooth(1.70, 2.0, sv)
    arch_v = np.sin(np.pi * np.clip(fx, 0, 1)) ** 0.55
    arch_h = np.sin(np.pi * np.clip(fy, 0, 1)) ** 0.55
    hh = wv * (0.55 + 0.45 * arch_v) + (1 - wv) * (0.55 + 0.45 * arch_h)
    rnd = np.random.default_rng(seed + 7)
    tv = 1 + 0.09 * (rnd.random(cx) - 0.5) * 2
    th = 1 + 0.09 * (rnd.random(cy + 1) - 0.5) * 2
    nf = bnoise(h, w, 0.8, 0.8, seed + 2)
    fib_v = 0.88 + 0.12 * np.sin(2 * np.pi * (fx * 8 + 0.08 * nf))
    fib_h = 0.88 + 0.12 * np.sin(2 * np.pi * (fy * 8 + 0.08 * nf))
    br_v = 1.0 * tv[i % cx] * fib_v * (0.55 + 0.45 * arch_v)
    br_h = 0.55 * th[j % cy] * fib_h * (0.55 + 0.45 * arch_h)
    br = wv * br_v + (1 - wv) * br_h
    aoc = 1.0 - 0.38 * 4 * wv * (1 - wv)
    aoc *= 0.80 + 0.20 * hh
    # clear-coat micro defects
    peel = fnoise(h, w, 2.4, seed + 3)
    sc = scratches(h, w, int(w * h / 3500), 8, 40, seed + 4)
    sc2 = scratches(h, w, int(w * h / 12000), 20, 90, seed + 5, width=1.0)
    scr = np.clip(sc * 0.5 + sc2, 0, 1)
    alb_v = base * br * (1 + 0.1 * peel * 0.2)
    alb = np.stack([alb_v * 0.96, alb_v * 0.98, alb_v * 1.06], -1) + scr[..., None] * 0.060
    height = hh * 0.55 + peel * 0.035 - scr * 0.10
    rough = gloss + 0.06 * (1 - hh) + 0.05 * peel * 0.2 + scr * 0.28
    return Tex(alb, height, rough, np.zeros((h, w)), aoc)


# ---------------------------------------------------------------------------
# text helper (decals)
# ---------------------------------------------------------------------------
def text_mask(text, font_path, px, tracking=0.0):
    f = ImageFont.truetype(font_path, px)
    # measure with tracking
    widths = [f.getlength(c) for c in text]
    W = int(sum(widths) + tracking * px * (len(text) - 1)) + 8
    bbox = f.getbbox('H')
    asc = f.getmetrics()[0]
    H = asc + f.getmetrics()[1] + 8
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    x = 4.0
    for c, cw in zip(text, widths):
        d.text((x, 4), c, font=f, fill=255)
        x += cw + tracking * px
    # tight crop
    arr = np.asarray(im)
    ys, xs = np.nonzero(arr > 8)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def place_text_rotated(mask_img, length_px, height_px, rot):
    """resize a horizontal text mask to (length along v, height along u), rotate 90deg"""
    m = mask_img.resize((int(length_px), int(height_px)), Image.LANCZOS)
    m = m.rotate(rot, expand=True)
    return np.asarray(m, np.float32) / 255.0


def paste_mask(canvas, m, x, y):
    """additive paste into float canvas (no wrap in the label)"""
    h, w = m.shape
    H, W = canvas.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    sub = m[y0 - y:y1 - y, x0 - x:x1 - x]
    canvas[y0:y1, x0:x1] = np.maximum(canvas[y0:y1, x0:x1], sub)


# ---------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------
def gen_carbon(seed=11):
    return carbon_twill(1024, 1024, 24, 24, seed)


def gen_label(seed=21):
    w, h = 512, 2048
    t = carbon_twill(w, h, 24, 204, seed, base=0.085)
    # physical scale: u: circumference ~ 40 mm over 512 px ; v: 0.337 m over 2048 px
    mm_u = 40.8 / w
    mm_v = 337.0 / h
    gold = np.zeros((h, w), np.float32)
    white_ = np.zeros((h, w), np.float32)
    red = np.zeros((h, w), np.float32)
    # full-circumference gold stripes near the handle and at the end of the label zone
    def stripe(y_mm, th_mm, arr, val=1.0):
        a = int((y_mm) / mm_v)
        b = max(a + 1, int((y_mm + th_mm) / mm_v))
        arr[a:b, :] = val
    for y0 in (6.0, 10.5):
        stripe(y0, 1.6 if y0 < 8 else 0.7, gold)
    stripe(10.5 + 3.0, 0.5, white_)
    for y0 in (325.0, 329.5):
        stripe(y0, 1.6 if y0 < 327 else 0.7, gold)
    # --- text on +X side (u = 0.75): reads handle -> tip
    m = text_mask('TIDEWATER', FONT_B, 220, 0.10)
    A = place_text_rotated(m, 62.0 / mm_v, 5.4 / mm_u, -90)
    paste_mask(gold, A, int(0.75 * w - A.shape[1] / 2), int(24.0 / mm_v))
    m = text_mask('PRO SERIES', FONT_B, 200, 0.18)
    A = place_text_rotated(m, 44.0 / mm_v, 3.6 / mm_u, -90)
    paste_mask(white_, A, int(0.75 * w - A.shape[1] / 2), int(92.0 / mm_v))
    m = text_mask("7'0\"  2PC  MED  FAST", FONT_R, 150, 0.12)
    A = place_text_rotated(m, 62.0 / mm_v, 2.5 / mm_u, -90)
    paste_mask(white_, A, int(0.75 * w - A.shape[1] / 2), int(150.0 / mm_v))
    m = text_mask('TW-702MF', FONT_M, 170, 0.0)
    A = place_text_rotated(m, 34.0 / mm_v, 2.5 / mm_u, -90)
    paste_mask(red, A, int(0.75 * w - A.shape[1] / 2), int(222.0 / mm_v))
    # --- text on -X side (u = 0.25): rotated the other way so it reads right when seen from -X
    m = text_mask('LINE 8-14 LB   LURE 1/8-5/8 OZ', FONT_R, 150, 0.10)
    A = place_text_rotated(m, 118.0 / mm_v, 2.5 / mm_u, 90)
    paste_mask(white_, A, int(0.25 * w - A.shape[1] / 2), int(60.0 / mm_v))
    m = text_mask('HIGH MODULUS CARBON', FONT_B, 150, 0.14)
    A = place_text_rotated(m, 82.0 / mm_v, 2.8 / mm_u, 90)
    paste_mask(gold, A, int(0.25 * w - A.shape[1] / 2), int(190.0 / mm_v))
    # a stylised fish mark
    fish = Image.new('L', (400, 180), 0)
    d = ImageDraw.Draw(fish)
    d.ellipse([20, 40, 300, 140], fill=255)
    d.polygon([(280, 90), (390, 20), (360, 90), (390, 160)], fill=255)
    d.ellipse([70, 75, 92, 97], fill=0)
    A = place_text_rotated(fish, 16.0 / mm_v, 7.0 / mm_u, -90)
    paste_mask(gold, A, int(0.75 * w - A.shape[1] / 2), int(250.0 / mm_v))
    # soften (decals are printed under clear coat)
    def soft(a):
        return np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    gold, white_, red = soft(gold), soft(white_), soft(red)
    alb = t.albedo.copy()
    for mk, col in ((gold, (0.62, 0.45, 0.16)), (white_, (0.72, 0.72, 0.70)), (red, (0.60, 0.05, 0.05))):
        alb = alb * (1 - mk[..., None]) + np.array(col, np.float32) * mk[..., None] * (0.85 + 0.15 * t.ao[..., None])
    allm = np.clip(gold + white_ + red, 0, 1)
    height = t.height + allm * 0.12
    rough = t.rough * (1 - allm) + 0.30 * allm
    return Tex(alb, height, rough, np.zeros((h, w)) + 0.0, t.ao)


def gen_eva(seed=31):
    h = w = 1024
    F1, F2, ID = worley(h, w, 150, 150, seed)
    pores = smooth(0.0, 0.42, F1)                      # 0 at cell centre
    edge = smooth(0.0, 0.18, F2 - F1)                  # 0 on cell boundaries
    big = fnoise(h, w, 2.2, seed + 1)
    fine = bnoise(h, w, 0.9, 0.9, seed + 2)
    mid = fnoise(h, w, 1.4, seed + 3)
    speck = (white(h, w, seed + 4) > 2.8).astype(np.float32)
    speck = np.asarray(Image.fromarray((speck * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 * 3
    cellv = (ID - 0.5)
    tone = 0.105 * (1 + 0.16 * big + 0.10 * fine + 0.16 * cellv)
    tone = tone * (0.80 + 0.20 * edge) + speck * 0.07
    alb = np.stack([tone * 1.0, tone * 1.0, tone * 1.04], -1)
    height = -0.55 * (1 - pores) + 0.30 * edge + 0.10 * mid + 0.05 * fine
    ao = 0.60 + 0.40 * pores * (0.5 + 0.5 * edge)
    rough = 0.80 + 0.04 * fine + 0.06 * big - 0.06 * speck
    return Tex(alb, height, rough, np.zeros((h, w)), ao)


def gen_cork(seed=41):
    """natural cork: fine multi-scale granules, dark lenticels/specks, glue seams between 4 stacked discs"""
    h = w = 1024
    F1, F2, ID = worley(h, w, 80, 80, seed)
    G1, G2, IDg = worley(h, w, 190, 190, seed + 9)
    edge = smooth(0.0, 0.16, F2 - F1)
    edgeg = smooth(0.0, 0.20, G2 - G1)
    big = fnoise(h, w, 2.4, seed + 1)
    mid = fnoise(h, w, 1.5, seed + 2)
    fine = bnoise(h, w, 0.9, 0.9, seed + 3)
    rnd = np.random.default_rng(seed + 4)
    dtone = 1 + 0.12 * (rnd.random(4) - 0.5) * 2
    dhue = (rnd.random(4) - 0.5) * 0.06
    Y = (np.arange(h) + 0.5) / h
    disc = np.minimum((Y * 4).astype(int), 3)
    dt = dtone[disc][:, None] * np.ones((1, w))
    dh = dhue[disc][:, None] * np.ones((1, w))
    yf = (Y * 4) % 1.0
    seam = (1 - smooth(0.0, 0.016, np.minimum(yf, 1 - yf)))[:, None] * np.ones((1, w))
    g = 0.55 * (ID - 0.5) + 0.45 * (IDg - 0.5)
    base = np.stack([0.60 + 0.20 * g + dh, 0.43 + 0.15 * g + dh * 0.7, 0.26 + 0.10 * g], -1)
    base = base * (dt[..., None] * (1 + 0.16 * big[..., None] + 0.08 * mid[..., None]))
    spk = (white(h, w, seed + 6) > 2.55).astype(np.float32)
    spk = np.asarray(Image.fromarray((spk * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9)), np.float32) / 255 * 3.2
    lent = (smooth(0.12, 0.0, G1) * (IDg > 0.62)).astype(np.float32)                 # dark pits
    resin = np.clip((fnoise(h, w, 1.1, seed + 7) - 1.7) * 1.3, 0, 1)
    light = (white(h, w, seed + 8) > 3.0).astype(np.float32)
    light = np.asarray(Image.fromarray((light * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 * 2.5
    alb = base * (0.90 + 0.10 * edge[..., None]) * (0.92 + 0.08 * edgeg[..., None])
    alb = alb * (1 - 0.55 * np.clip(spk, 0, 1)[..., None]) * (1 - 0.60 * lent[..., None]) * (1 - 0.35 * resin[..., None])
    alb = alb + light[..., None] * 0.05
    alb = alb * (1 - 0.50 * seam[..., None])
    height = 0.30 * edge + 0.25 * edgeg + 0.12 * mid + 0.06 * fine - 0.9 * lent - 0.4 * np.clip(spk, 0, 1) - 0.9 * seam
    ao = 0.72 + 0.28 * edge * (0.6 + 0.4 * edgeg) - 0.35 * lent - 0.3 * seam
    rough = 0.74 + 0.06 * fine - 0.05 * edge + 0.05 * big
    return Tex(alb, height, rough, np.zeros((h, w)), ao)


def gen_rubber(seed=51):
    h = w = 512
    # hexagonal dimple lattice (period integer => tileable)
    nx, ny = 32, 28
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    gx = X / w * nx
    gy = Y / h * ny * (np.sqrt(3) / 2) * 2 / np.sqrt(3) * (np.sqrt(3) / 2)
    gy = Y / h * (ny / 2)
    # two interleaved rectangular lattices make a hex lattice
    def dimple(ox, oy):
        fx = ((X / w * nx + ox) % 1.0) - 0.5
        fy = (((Y / h * (ny // 2) * 1.0) + oy) % 1.0) - 0.5
        d = np.sqrt((fx) ** 2 + (fy * 1.0) ** 2)
        return d
    d = np.minimum(dimple(0.0, 0.0), dimple(0.5, 0.5))
    dim = 1 - smooth(0.12, 0.34, d)
    grain = bnoise(h, w, 0.8, 0.8, seed)
    big = fnoise(h, w, 2.0, seed + 1)
    dust = smooth(2.3, 3.4, bnoise(h, w, 0.7, 0.7, seed + 5))            # sparse pale dust / filler specks
    scuff = scratches(h, w, 26, 20, 90, seed + 6, spread=1.0, width=1.2)  # hand-wear scuffs
    t = 0.040 * (1 + 0.20 * big + 0.10 * grain) * (1 - 0.50 * dim) * (1 + 1.1 * dust + 0.9 * scuff)
    alb = np.stack([t, t, t * 1.03], -1)
    height = -dim * 0.9 + 0.05 * grain
    ao = 1 - 0.45 * dim
    rough = 0.88 + 0.05 * big - 0.10 * (1 - dim) * 0
    return Tex(alb, height, rough, np.zeros((h, w)), ao)


def _brushed(h, w, seed, sx=60.0, sy=0.9):
    return bnoise(h, w, sx, sy, seed)


def gen_alu_dark(seed=61):
    h = w = 1024
    br = _brushed(h, w, seed, 70, 0.8)
    br2 = _brushed(h, w, seed + 1, 18, 0.7)
    big = fnoise(h, w, 2.4, seed + 2)
    pit = (white(h, w, seed + 3) > 3.4).astype(np.float32)
    pit = np.asarray(Image.fromarray((pit * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255 * 3
    sc = scratches(h, w, 900, 20, 140, seed + 4, angle=0.0, spread=0.35)
    sc2 = scratches(h, w, 90, 120, 300, seed + 5, angle=0.0, spread=0.08)
    scr = np.clip(sc * 0.6 + sc2 * 0.8, 0, 1)
    t = 0.150 * (1 + 0.10 * br + 0.06 * br2 + 0.04 * big)
    alb = np.stack([t * 0.98, t * 0.99, t * 1.05], -1) + pit[..., None] * 0.10 + scr[..., None] * 0.14
    height = 0.12 * br + 0.07 * br2 - 0.30 * scr - 0.25 * pit
    ao = 0.92 + 0.08 * br * 0.3 - 0.2 * pit
    rough = 0.34 + 0.07 * br2 + 0.05 * big * 0.5 + 0.30 * scr + 0.1 * pit
    return Tex(alb, height, rough, 1.0 - 0.15 * pit, ao)


def gen_alu_gold(seed=71):
    h = w = 1024
    br = _brushed(h, w, seed, 90, 0.7)
    rings = np.sin(2 * np.pi * (np.arange(h)[:, None] / h * 180 + 0.25 * fnoise(h, w, 2.0, seed + 1)))   # turning marks
    big = fnoise(h, w, 2.4, seed + 2)
    sc = scratches(h, w, 800, 20, 160, seed + 3, angle=0.0, spread=0.3)
    pit = (white(h, w, seed + 4) > 3.5).astype(np.float32)
    pit = np.asarray(Image.fromarray((pit * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255 * 3
    k = 1 + 0.08 * br + 0.04 * rings + 0.05 * big
    alb = np.stack([0.60 * k, 0.43 * k * (1 + 0.02 * big), 0.145 * k], -1) + sc[..., None] * np.array([0.10, 0.08, 0.04]) - pit[..., None] * 0.1
    height = 0.10 * br + 0.10 * rings - 0.25 * sc
    ao = 0.95 + 0.05 * rings
    rough = 0.30 + 0.06 * br + 0.03 * rings + 0.25 * sc
    return Tex(alb, height, rough, np.ones((h, w)) * 0.95, ao)


def gen_paint(seed=81):
    h = w = 512
    peel = fnoise(h, w, 2.2, seed)
    big = fnoise(h, w, 2.6, seed + 1)
    flake_pos = (white(h, w, seed + 2) > 2.6).astype(np.float32)
    flake = np.asarray(Image.fromarray((flake_pos * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255 * 2.5
    fr = np.random.default_rng(seed + 3).random((h, w))
    t = 0.032 * (1 + 0.06 * big)
    alb = np.stack([t * 1.0, t * 1.04, t * 1.14], -1) + flake[..., None] * (0.05 + 0.08 * fr[..., None]) * np.array([0.9, 1.0, 1.2])
    height = 0.10 * peel + 0.02 * big
    ao = np.ones((h, w))
    rough = 0.24 + 0.03 * peel + 0.10 * flake
    return Tex(alb, height, rough, 0.55 + 0.35 * flake, ao)


def gen_chrome(seed=91):
    h = w = 512
    br = _brushed(h, w, seed, 120, 0.6)
    big = fnoise(h, w, 2.2, seed + 1)
    sc = scratches(h, w, 220, 20, 120, seed + 2, angle=None)
    sc2 = scratches(h, w, 220, 30, 220, seed + 3, angle=0.0, spread=0.12)
    scr = np.clip(sc * 0.5 + sc2 * 0.6, 0, 1)
    t = 0.80 * (1 + 0.025 * br + 0.02 * big)
    alb = np.stack([t * 0.98, t * 0.99, t * 1.01], -1) - scr[..., None] * 0.05
    height = 0.04 * br - 0.20 * scr
    rough = 0.10 + 0.03 * br + 0.18 * scr + 0.02 * big
    return Tex(alb, height, rough, np.ones((h, w)), 0.97 + 0.03 * br)


def gen_ceramic(seed=101):
    h = w = 256
    F1, F2, ID = worley(h, w, 64, 64, seed)
    grain = smooth(0.0, 0.9, F1)
    big = fnoise(h, w, 2.0, seed + 1)
    sp = (white(h, w, seed + 2) > 2.9).astype(np.float32)
    t = 0.085 * (1 + 0.20 * (ID - 0.5) + 0.10 * big) + sp * 0.07
    alb = np.stack([t * 0.96, t * 1.03, t * 1.22], -1)
    height = 0.05 * grain + 0.02 * big
    return Tex(alb, height, 0.08 + 0.04 * (ID - 0.5) + 0.05 * grain, np.zeros((h, w)), 0.9 + 0.1 * (1 - grain) * 0 + 0.1 * grain)


def gen_thread(seed=111):
    h = w = 512
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    pitch = 6.0
    s = (Y % pitch) / pitch
    cylinder = np.sin(np.pi * s) ** 0.7
    twist = np.sin(2 * np.pi * (X / w * 22 + Y / pitch * 0.12 + 0.2 * fnoise(h, w, 1.6, seed)))
    fibre = np.sin(2 * np.pi * (X / w * 64 + 0.15 * s))
    fl = fnoise(h, w, 2.0, seed + 1)
    # per-thread brightness
    tid = (Y // pitch).astype(int)
    rnd = np.random.default_rng(seed + 2).random(h // 6 + 2)
    tb = (1 + 0.08 * (rnd[tid] - 0.5) * 2)
    shade = (0.45 + 0.55 * cylinder) * tb * (1 + 0.06 * twist + 0.02 * fibre)
    top = Y < h / 2
    # top half: deep red thread under epoxy; bottom half: gold metallic thread
    red = np.stack([0.40 * shade, 0.020 * shade, 0.028 * shade], -1)
    gold = np.stack([0.66 * shade, 0.46 * shade, 0.12 * shade], -1)
    alb = np.where(top[..., None], red, gold)
    # epoxy: slightly darker glassy film with soft lensing
    height = cylinder * 0.5 + 0.05 * twist + 0.03 * fl
    ao = 0.5 + 0.5 * cylinder
    rough = np.where(top, 0.12, 0.22) + 0.04 * (1 - cylinder)
    metal = np.where(top, 0.0, 0.55)
    return Tex(alb, height, rough, metal, ao)


def gen_plastic(seed=121):
    h = w = 512
    g = bnoise(h, w, 0.9, 0.9, seed)
    big = fnoise(h, w, 2.2, seed + 1)
    F1, F2, ID = worley(h, w, 90, 90, seed + 2)
    scuff = scratches(h, w, 70, 25, 140, seed + 6, spread=1.0, width=1.1)
    dust = smooth(2.4, 3.5, bnoise(h, w, 0.7, 0.7, seed + 7))
    t = 0.034 * (1 + 0.24 * big + 0.12 * g) * (1 + 1.4 * scuff + 0.9 * dust)
    alb = np.stack([t, t, t * 1.04], -1)
    height = 0.25 * smooth(0, 0.8, F1) + 0.10 * g - 0.15 * scuff
    return Tex(alb, height, 0.52 + 0.08 * g + 0.05 * big, np.zeros((h, w)), 0.9 + 0.1 * smooth(0, 0.8, F1))


def _superellipse_mask(w, h, a, b, p):
    X = (np.arange(w) + 0.5) / w * 2 - 1
    Y = (np.arange(h) + 0.5) / h * 2 - 1
    XX, YY = np.meshgrid(X, Y)
    return (np.abs(XX / a) ** p + np.abs(YY / b) ** p)


def gen_plate(seed=131):
    """reel side plate: black anodised, laser-etched gold lettering + fish logo.
    Texture is mapped to the plate bounding box (92.6 x 53.5 mm), drawn with the real aspect and
    resampled to 1024x1024."""
    cw, ch = 2048, 1440            # canvas ~ 0.0371 mm/px both axes
    mmpx = 76.0 / cw
    eng = Image.new('L', (cw, ch), 0)
    d = ImageDraw.Draw(eng)
    sup = 1.0
    # border line following the plate shape (superellipse, p=2.6 like the housing)
    th = np.linspace(0, 2 * np.pi, 400)
    p = 2.6
    c, s = np.cos(th), np.sin(th)
    bx = np.sign(c) * np.abs(c) ** (2 / p)
    by = np.sign(s) * np.abs(s) ** (2 / p)
    for k, (sc_, wd) in enumerate(((0.935, 6), (0.905, 3))):
        pts = [(cw / 2 + x * cw / 2 * sc_, ch / 2 + y * ch / 2 * sc_) for x, y in zip(bx, by)]
        d.line(pts + [pts[0]], fill=255, width=wd, joint='curve')
    # lettering
    def put(text, font, px, cy, tracking=0.0, fill=255):
        m = text_mask(text, font, px, tracking)
        eng.paste(fill, (int(cw / 2 - m.size[0] / 2), int(cy - m.size[1] / 2)), m)
    put('TIDEWATER', FONT_B, 215, 400, 0.12)
    d.line([(cw / 2 - 560, 545), (cw / 2 + 560, 545)], fill=255, width=5)
    put('ELITE  SERIES', FONT_R, 100, 640, 0.35)
    # fish + waves
    fish = Image.new('L', (520, 240), 0)
    fd = ImageDraw.Draw(fish)
    fd.ellipse([20, 50, 380, 190], fill=255)
    fd.polygon([(350, 120), (500, 20), (470, 120), (500, 220)], fill=255)
    fd.ellipse([85, 95, 118, 128], fill=0)
    fd.arc([160, 60, 260, 180], 100, 260, fill=0, width=7)
    eng.paste(255, (int(cw / 2 - 260), 760), fish)
    for k in range(3):
        y0 = 1040 + 36 * k
        pts = [(cw / 2 - 300 + x, y0 + 14 * np.sin(x / 60.0 * np.pi + k)) for x in range(0, 601, 6)]
        d.line(pts, fill=255, width=6)
    put('3000', FONT_B, 190, 1165, 0.2)
    put('5.2:1  \u00b7  7+1 BB', FONT_R, 62, 1262, 0.2)
    eng = eng.resize((1024, 1024), Image.LANCZOS)
    e = np.asarray(eng.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255.0
    h = w = 1024
    br = bnoise(h, w, 55, 0.8, seed)
    br2 = bnoise(h, w, 14, 0.7, seed + 1)
    big = fnoise(h, w, 2.4, seed + 2)
    pit = (white(h, w, seed + 3) > 3.5).astype(np.float32)
    pit = np.asarray(Image.fromarray((pit * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255 * 3
    sc = scratches(h, w, 700, 20, 130, seed + 4, angle=0.0, spread=0.35)
    t = 0.040 * (1 + 0.14 * br + 0.07 * br2 + 0.05 * big)
    alb = np.stack([t * 0.98, t * 0.99, t * 1.08], -1) + sc[..., None] * 0.10 + pit[..., None] * 0.08
    gold = np.array([0.68, 0.50, 0.17], np.float32) * (1 + 0.10 * br[..., None] + 0.05 * br2[..., None])
    alb = alb * (1 - e[..., None]) + gold * e[..., None]
    height = 0.10 * br + 0.05 * br2 - 0.25 * sc - 0.9 * e
    rough = 0.34 + 0.07 * br2 + 0.28 * sc + 0.14 * e
    return Tex(alb, height, rough, np.ones((h, w)) * 0.95, 0.95 - 0.3 * e)


def gen_line_wound(seed=141):
    h = w = 512
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    pitch = 8.0
    out = None
    heights = []
    for k, sgn in enumerate((+1, -1)):
        ph = Y / pitch + sgn * 3.0 * X / w + 0.04 * fnoise(h, w, 2.4, seed + k)
        sv = ph % 1.0
        cyl = np.sin(np.pi * sv) ** 0.75
        heights.append(cyl)
    layer = np.maximum(heights[0], heights[1]) * 0.6 + 0.4 * np.minimum(heights[0], heights[1])
    # alternate dominance bands (cross-wind pattern)
    blend = 0.5 + 0.5 * np.sin(2 * np.pi * (X / w * 6 + Y / h * 2))
    hh = heights[0] * blend + heights[1] * (1 - blend)
    hh = 0.65 * hh + 0.35 * layer
    n = fnoise(h, w, 2.0, seed + 5)
    col = np.array([0.60, 0.67, 0.44], np.float32)
    shade = 0.35 + 0.65 * hh
    alb = col[None, None, :] * shade[..., None] * (1 + 0.05 * n[..., None])
    return Tex(alb, hh * 0.7, 0.42 + 0.1 * (1 - hh), np.zeros((h, w)), 0.4 + 0.6 * hh)


def gen_line(seed=151):
    h = w = 64
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    twist = np.sin(2 * np.pi * (X / w * 2 + Y / h * 3))
    n = fnoise(h, w, 2.0, seed)
    col = np.array([0.62, 0.69, 0.50], np.float32)
    alb = col[None, None, :] * (0.92 + 0.06 * twist + 0.03 * n)[..., None]
    return Tex(alb, 0.1 * twist, np.full((h, w), 0.2), np.zeros((h, w)), np.ones((h, w)))


def gen_env():
    """matcap-style studio reflection map used by the MatFX env-map (256x256 RGB)."""
    n = 256
    u = (np.arange(n) + 0.5) / n * 2 - 1
    X, Y = np.meshgrid(u, -u)
    r2 = np.clip(X * X + Y * Y, 0, 1)
    Z = np.sqrt(1 - r2)
    N = np.stack([X, Y, Z], -1)
    def dirv(v):
        v = np.array(v, np.float64)
        return v / np.linalg.norm(v)
    # view space: +Z towards the viewer, +Y up
    base = 0.14 + 0.55 * smooth(-0.4, 1.0, N[..., 1]) + 0.1 * smooth(0.0, 1.0, N[..., 2])
    img = np.stack([base * 0.96, base * 0.98, base * 1.02], -1)
    for v, wd, amp, col in ((dirv((-0.55, 0.60, 0.55)), 0.10, 4.0, (1.0, 0.97, 0.92)),
                            (dirv((0.80, 0.25, 0.45)), 0.06, 2.4, (0.85, 0.92, 1.0)),
                            (dirv((0.1, -0.7, 0.5)), 0.12, 0.9, (1.0, 0.95, 0.9)),
                            (dirv((-0.1, 0.95, 0.2)), 0.07, 2.0, (1.0, 1.0, 1.0))):
        dd = (N * v).sum(-1)
        m = smooth(1 - wd, 1.0, dd)
        img += m[..., None] * amp * np.array(col)
    img = img / (1 + img * 0.4)
    img = np.clip(img, 0, 1) ** (1 / 1.0)
    return (img * 255 + 0.5).astype(np.uint8)


GENERATORS = {
    'carbon': (gen_carbon, 7.0), 'label': (gen_label, 7.0), 'eva': (gen_eva, 7.0), 'cork': (gen_cork, 7.0),
    'rubber': (gen_rubber, 5.0), 'alu_dark': (gen_alu_dark, 5.0), 'alu_gold': (gen_alu_gold, 4.0),
    'paint': (gen_paint, 5.0), 'chrome': (gen_chrome, 4.0), 'ceramic': (gen_ceramic, 4.0),
    'thread': (gen_thread, 5.0), 'plastic': (gen_plastic, 5.0), 'plate': (gen_plate, 6.0),
    'linewound': (gen_line_wound, 5.0), 'line': (gen_line, 2.0),
}
