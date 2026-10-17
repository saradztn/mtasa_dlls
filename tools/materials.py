"""Material library -> genuine mipmapped D3D9 TXDs (DXT1/DXT5 via Pillow, written by
DragonFF gtaLib). 9 sources are actual image-generation outputs (development/ai_textures);
the rest are deterministic procedural or AI-derived textures. No scene rendering."""
from __future__ import annotations
import hashlib, io, json, math
from collections import namedtuple
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
from fortlib import RW_VERSION
from gtaLib import txd

ROOT = Path(__file__).resolve().parent.parent
AI = {'rf_stone': 'castle_stone', 'rf_slate': 'roof_slate', 'rf_marble': 'marble_floor', 'rf_wood': 'dark_wood',
      'rf_cobble': 'cobble_paving', 'rf_dungeon': 'dungeon_stone', 'rf_banner': 'royal_banner',
      'rf_iron': 'forged_iron', 'rf_grass': 'meadow_grass'}
GROUPS = {
    'rf_struct': ['rf_stone', 'rf_stonedark', 'rf_slate', 'rf_cobble', 'rf_plaster', 'rf_ceiling', 'rf_marble',
                  'rf_dungeon', 'rf_rock', 'rf_iron', 'rf_wood', 'rf_woodlight', 'rf_glass', 'rf_stained', 'rf_gold'],
    'rf_deco': ['rf_carpetblue', 'rf_carpetred', 'rf_banner', 'rf_fabricred', 'rf_fabricblue', 'rf_books', 'rf_paint1',
                'rf_paint2', 'rf_paint3', 'rf_map', 'rf_fire', 'rf_candle', 'rf_lamp', 'rf_parchment', 'rf_bronze',
                'rf_whitemarble', 'rf_copper', 'rf_hay', 'rf_waterfx'],
    'rf_nature': ['rf_grass', 'rf_dirt', 'rf_gravel', 'rf_sand', 'rf_hedge', 'rf_leaf', 'rf_bark', 'rf_flowers'],
}
ALPHA = {'rf_glass', 'rf_fire', 'rf_leaf', 'rf_waterfx'}
TEX_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}
RNG = np.random.default_rng(77901)


def seamless(im, size=1024):
    a = np.asarray(im.convert('RGB').resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32)
    dx = (a[:, -1] - a[:, 0]).copy(); dy = (a[-1, :] - a[0, :]).copy()
    x = np.linspace(-.5, .5, size)[None, :, None]; y = np.linspace(-.5, .5, size)[:, None, None]
    a -= dx[:, None, :] * x; a -= dy[None, :, :] * y
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')


def noise(n, sigma, seed=None):
    r = np.random.default_rng(seed) if seed is not None else RNG
    a = gaussian_filter(r.normal(size=(n, n)), sigma, mode='wrap'); return a / max(1e-6, a.std())


def from_array(a, alpha=None):
    a = np.clip(a, 0, 255).astype(np.uint8)
    im = Image.fromarray(a, 'RGB').convert('RGBA')
    if alpha is not None: im.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8)))
    return im


def tint(im, k, size=None):
    a = np.asarray(im.convert('RGB'), float) * np.asarray(k, float)
    out = from_array(a)
    return out.resize((size, size), Image.Resampling.LANCZOS) if size else out


def solid_noise(color, n=512, amp=10, sigma=2.0, fine=3, seed=None):
    nz = noise(n, sigma, seed)[:, :, None]
    return from_array(np.asarray(color, float)[None, None, :] + nz * amp + RNG.normal(0, fine, (n, n, 1)))


def lattice(n, cell, width, value_line, value_fill):
    yy, xx = np.mgrid[0:n, 0:n]
    u = ((xx + yy) % cell); v = ((xx - yy) % cell)
    line = (u < width) | (v < width)
    return np.where(line, value_line, value_fill)


def procedural(img):
    T = {}
    T['rf_stonedark'] = tint(img['rf_stone'], (.70, .70, .74))
    T['rf_woodlight'] = tint(img['rf_wood'], (1.55, 1.35, 1.12), 512)
    T['rf_rock'] = tint(img['rf_dungeon'], (1.45, 1.33, 1.15), 512)
    T['rf_bark'] = tint(img['rf_wood'], (.85, .86, .80), 512)
    T['rf_hedge'] = tint(img['rf_grass'], (.55, .78, .52), 512)
    n = 512
    pl = noise(n, 18)[:, :, None] * 5 + noise(n, 1.5)[:, :, None] * 3
    T['rf_plaster'] = from_array(np.array([214, 202, 178])[None, None, :] + pl)
    # Coffered ceiling: plaster panels framed by darker carved wood mouldings.
    c = np.array([226, 214, 190], float)[None, None, :] + pl
    yy, xx = np.mgrid[0:n, 0:n]; d = np.minimum(np.minimum(xx % 256, 256 - xx % 256), np.minimum(yy % 256, 256 - yy % 256))
    frame = (d < 22)[:, :, None]; inner = ((d >= 22) & (d < 30))[:, :, None]
    c = np.where(frame, np.array([92, 62, 38])[None, None, :] + pl * 1.5, c)
    c = np.where(inner, np.array([176, 140, 74])[None, None, :] + pl, c)
    T['rf_ceiling'] = from_array(c)
    g = 256; gn = noise(g, 3)[:, :, None]; gn2 = noise(g, .8)[:, :, None]
    T['rf_gold'] = from_array(np.array([196, 152, 58])[None, None, :] + gn * 22 + gn2 * 10)
    T['rf_copper'] = from_array(np.array([170, 96, 58])[None, None, :] + gn * 18 + gn2 * 8)
    T['rf_bronze'] = from_array(np.array([92, 98, 70])[None, None, :] + gn * 14 + noise(g, 6)[:, :, None] * 12)
    # Leaded window glass: diamond lattice, translucent blue-grey panes (DXT5 alpha).
    lat = lattice(g, 64, 4, 1.0, 0.0)
    rgb = np.where(lat[:, :, None] > .5, np.array([40, 40, 44]), np.array([118, 146, 168]) + gn * 8)
    T['rf_glass'] = from_array(rgb, np.where(lat > .5, 255, 150))
    # Stained glass: saturated panes in lead lattice (opaque, reads bright with baked light).
    cells = ((xx[:g, :g] + yy[:g, :g]) // 64) * 7 + ((xx[:g, :g] - yy[:g, :g]) // 64) * 3
    pal = np.array([[160, 30, 40], [30, 60, 160], [200, 160, 40], [40, 120, 60], [120, 40, 140], [200, 90, 30]])
    rgb = pal[np.mod(cells, len(pal))] + gn * 12
    rgb = np.where(lat[:, :, None] > .5, np.array([30, 28, 26]), rgb)
    T['rf_stained'] = from_array(rgb)
    # Carpets.
    cb = np.array([22, 38, 104], float)[None, None, :] + noise(n, 1)[:, :, None] * 6 + noise(n, 20)[:, :, None] * 5
    im = from_array(cb); d_ = ImageDraw.Draw(im)
    for j in range(4):
        for i in range(4):
            cx = i * 128 + (64 if j % 2 else 0); cy = j * 128 + 64
            for ox in (-512, 0, 512):
                pts = []
                for k in range(16):
                    r = 26 if k % 2 == 0 else 10; a = math.pi * k / 8
                    pts.append((cx + ox + r * math.cos(a), cy + r * math.sin(a)))
                d_.polygon(pts, fill=(205, 165, 70, 255))
    for k in range(0, 512, 128):
        d_.line((k, 0, k + 512, 512), fill=(150, 120, 60, 255), width=2); d_.line((k - 512, 0, k, 512), fill=(150, 120, 60, 255), width=2)
        d_.line((k, 512, k + 512, 0), fill=(150, 120, 60, 255), width=2); d_.line((k - 512, 512, k, 0), fill=(150, 120, 60, 255), width=2)
    T['rf_carpetblue'] = im.filter(ImageFilter.GaussianBlur(.6))
    cr = np.array([118, 20, 26], float)[None, None, :] + noise(n, 1)[:, :, None] * 6 + noise(n, 20)[:, :, None] * 5
    im = from_array(cr); d_ = ImageDraw.Draw(im)
    for j in range(8):
        for i in range(8):
            cx = i * 64 + 32; cy = j * 64 + 32
            d_.polygon([(cx, cy - 14), (cx + 14, cy), (cx, cy + 14), (cx - 14, cy)], outline=(210, 170, 80, 255), width=3)
            d_.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(30, 50, 110, 255))
    T['rf_carpetred'] = im.filter(ImageFilter.GaussianBlur(.6))
    weave = (np.sin(xx * .9) * np.sin(yy * .9))[:, :, None] * 6
    T['rf_fabricred'] = from_array(np.array([132, 24, 30])[None, None, :] + weave + noise(n, 8)[:, :, None] * 8)
    T['rf_fabricblue'] = from_array(np.array([30, 48, 120])[None, None, :] + weave + noise(n, 8)[:, :, None] * 8)
    # Book spines: 4 shelves, wooden shelf boards.
    im = Image.new('RGBA', (512, 512), (60, 38, 22, 255)); d_ = ImageDraw.Draw(im); r = np.random.default_rng(5)
    cols = [(110, 28, 26), (30, 52, 96), (36, 78, 46), (118, 84, 40), (70, 30, 70), (140, 120, 90), (40, 32, 28)]
    for s in range(4):
        y0 = s * 128; x = 0
        d_.rectangle((0, y0 + 116, 512, y0 + 128), fill=(84, 56, 32, 255))
        while x < 512:
            w = int(r.integers(10, 26)); h = int(r.integers(76, 112)); cc = cols[int(r.integers(len(cols)))]
            v = int(r.integers(-15, 15)); cc = tuple(max(0, min(255, q + v)) for q in cc)
            d_.rectangle((x, y0 + 116 - h, min(511, x + w - 2), y0 + 116), fill=cc + (255,))
            for b in (18, h - 22):
                d_.line((x + 1, y0 + 116 - b, x + w - 3, y0 + 116 - b), fill=(200, 165, 80, 255), width=2)
            x += w
    T['rf_books'] = im
    # Paintings (original procedural art).
    def landscape(seed, sea=False):
        r = np.random.default_rng(seed); s = 256; im = Image.new('RGB', (s, s)); d = ImageDraw.Draw(im)
        for y in range(s):
            t = y / s; d.line((0, y, s, y), fill=(int(90 + 120 * t), int(120 + 80 * t), int(170 + 40 * t)))
        for k, colr in enumerate([(70, 90, 70), (52, 74, 48), (40, 58, 36)]):
            pts = [(0, s)] + [(x, int(s * (.45 + .12 * k) + 18 * math.sin(x * .03 + seed + k) + r.normal(0, 3))) for x in range(0, s + 8, 8)] + [(s, s)]
            d.polygon(pts, fill=colr)
        if sea:
            d.rectangle((0, int(s * .62), s, s), fill=(40, 70, 110))
            for k in range(30):
                x = int(r.integers(0, s)); y = int(r.integers(int(s * .64), s)); d.line((x, y, x + 12, y), fill=(160, 180, 200))
            d.polygon([(120, 150), (160, 150), (150, 162), (128, 162)], fill=(70, 40, 20)); d.polygon([(140, 100), (140, 150), (165, 148)], fill=(230, 225, 210))
        else:
            for x0 in (150, 172, 196):
                d.rectangle((x0, 92, x0 + 14, 140), fill=(80, 76, 70)); d.polygon([(x0 - 3, 92), (x0 + 17, 92), (x0 + 7, 70)], fill=(52, 60, 84))
            d.rectangle((150, 116, 210, 140), fill=(86, 80, 72))
        return im.filter(ImageFilter.GaussianBlur(1.1))
    def portrait():
        s = 256; im = Image.new('RGB', (s, s), (34, 26, 20)); d = ImageDraw.Draw(im)
        for y in range(s): d.line((0, y, s, y), fill=(40 + y // 16, 30 + y // 20, 22))
        d.ellipse((60, 150, 196, 300), fill=(26, 34, 80)); d.ellipse((98, 60, 158, 136), fill=(214, 176, 140))
        d.polygon([(96, 70), (128, 36), (160, 70)], fill=(200, 160, 50)); d.rectangle((118, 136, 138, 156), fill=(200, 160, 128))
        d.line((70, 200, 186, 200), fill=(200, 160, 60), width=4)
        return im.filter(ImageFilter.GaussianBlur(1.2))
    T['rf_paint1'] = landscape(3).convert('RGBA'); T['rf_paint2'] = portrait().convert('RGBA'); T['rf_paint3'] = landscape(9, True).convert('RGBA')
    # Parchment and a kingdom map.
    pa = np.array([214, 190, 140], float)[None, None, :] + noise(n, 30)[:, :, None] * 10 + noise(n, 2)[:, :, None] * 4
    T['rf_parchment'] = from_array(pa)
    h = noise(n, 26, 11); land = h > .15
    m = np.where(land[:, :, None], pa * np.array([.95, .93, .82]), pa * np.array([.70, .78, .86]))
    edge = land ^ np.roll(land, 1, 0) | land ^ np.roll(land, 1, 1)
    m[edge] = (70, 50, 30)
    m[(yy % 64 == 0) | (xx % 64 == 0)] *= .85
    im = from_array(m); d_ = ImageDraw.Draw(im)
    d_.ellipse((400, 400, 480, 480), outline=(90, 50, 30, 255), width=3); d_.line((440, 395, 440, 485), fill=(90, 50, 30, 255), width=2); d_.line((395, 440, 485, 440), fill=(90, 50, 30, 255), width=2)
    for k in range(9):
        x = int(RNG.integers(40, 470)); y = int(RNG.integers(40, 470))
        if land[y, x]: d_.rectangle((x - 5, y - 5, x + 5, y + 5), fill=(120, 30, 30, 255))
    T['rf_map'] = im
    # Flame (alpha), candle wax, lantern glow.
    fy, fx = np.mgrid[0:256, 0:128]; u = (fx - 64) / 64.0; v = 1 - fy / 256.0
    shape = np.clip(1 - (u / (0.15 + 0.85 * np.sqrt(np.clip(1 - v, 0, 1)) * (1 - v) * 1.6 + 1e-3)) ** 2, 0, 1) * np.clip(v * 4, 0, 1)
    flick = gaussian_filter(np.random.default_rng(2).normal(size=(256, 128)), 6) * 2
    a = np.clip(shape + flick * shape * .3, 0, 1)
    rgb = np.dstack([255 * np.ones_like(a), 120 + 130 * a, 30 + 120 * a ** 3])
    T['rf_fire'] = from_array(rgb, a * 255)
    T['rf_candle'] = solid_noise((236, 226, 200), 64, 4, 3, 1)
    T['rf_lamp'] = solid_noise((255, 214, 140), 64, 4, 3, 1)
    wm = np.array([232, 230, 224], float)[None, None, :] + noise(n, 1.0)[:, :, None] * 3
    veins = np.abs(np.sin((xx * .012 + yy * .02) * 6 + noise(n, 22, 4) * 2.8))
    wm -= (veins < .06)[:, :, None] * 46 + (veins < .12)[:, :, None] * 12
    T['rf_whitemarble'] = from_array(wm)
    hy = Image.new('RGBA', (256, 256), (190, 160, 80, 255)); d_ = ImageDraw.Draw(hy); r = np.random.default_rng(8)
    for k in range(900):
        x = int(r.integers(0, 256)); y = int(r.integers(0, 256)); L = int(r.integers(8, 30)); a_ = r.uniform(-.6, .6)
        cc = int(r.integers(-40, 30)); d_.line((x, y, x + L * math.cos(a_), y + L * math.sin(a_)), fill=(200 + cc // 2, 168 + cc // 2, 80 + cc // 3, 255), width=2)
    T['rf_hay'] = hy
    wn = noise(256, 4)[:, :, None]
    T['rf_waterfx'] = from_array(np.array([60, 110, 120])[None, None, :] + wn * 14, 190 + noise(256, 4) * 10)
    T['rf_dirt'] = solid_noise((112, 92, 66), 512, 12, 6.0, 5)
    gv = np.array([128, 124, 114], float)[None, None, :] + noise(n, 1.4)[:, :, None] * 16 + noise(n, 14)[:, :, None] * 6
    T['rf_gravel'] = from_array(gv)
    T['rf_sand'] = solid_noise((196, 178, 136), 256, 8, 5.0, 4)
    leaf = Image.new('RGBA', (512, 512), (48, 78, 36, 0)); d_ = ImageDraw.Draw(leaf); r = np.random.default_rng(31)
    for k in range(420):
        x = int(r.integers(10, 502)); y = int(r.integers(10, 502)); w = int(r.integers(5, 13)); hh = int(r.integers(10, 26)); v_ = int(r.integers(-14, 16))
        d_.ellipse((x - w, y - hh, x + w, y + hh), fill=(50 + v_, 84 + v_, 38 + v_, 255))
    T['rf_leaf'] = leaf
    fl = np.asarray(tint(img['rf_grass'], (.9, 1, .9), 256), float)[:, :, :3]; im = from_array(fl); d_ = ImageDraw.Draw(im); r = np.random.default_rng(12)
    for k in range(260):
        x = int(r.integers(0, 256)); y = int(r.integers(0, 256)); cc = [(220, 60, 70), (240, 210, 70), (230, 230, 240), (150, 80, 200)][k % 4]
        d_.ellipse((x - 2, y - 2, x + 2, y + 2), fill=cc + (255,))
    T['rf_flowers'] = im
    return T


def dds_pixels(image, fmt):
    b = io.BytesIO(); image.save(b, format='DDS', pixel_format=fmt); data = b.getvalue()
    assert data[:4] == b'DDS ' and data[84:88] == fmt.encode('ascii'); return data[128:]


def mips(image):
    yield image
    while image.width > 1 or image.height > 1:
        image = image.resize((max(1, image.width // 2), max(1, image.height // 2)), Image.Resampling.LANCZOS); yield image


def native(name, image, alpha):
    t = txd.TextureNative(); t.platform_id = 9; t.filter_mode = 6; t.uv_addressing = 0x11
    t.name = name; t.mask = ''; t.width = image.width; t.height = image.height
    t.depth = 32 if alpha else 16; t.raster_type = 4
    t.raster_format_flags = (0x0500 if alpha else 0x0200) | 0x8000
    t.d3d_format = txd.D3DFormat.D3D_DXT5 if alpha else txd.D3DFormat.D3D_DXT1
    P = namedtuple('PlatformProperties', 'alpha cube_texture auto_mipmaps compressed')
    t.platform_properties = P(alpha, False, False, True)
    t.pixels = [dds_pixels(lv, 'DXT5' if alpha else 'DXT1') for lv in mips(image)]
    t.num_levels = len(t.pixels); return t


def build():
    src = ROOT / 'development' / 'ai_textures'; out = ROOT / 'assets' / 'txd'; out.mkdir(parents=True, exist_ok=True)
    img = {}; manifest = []
    for name, stem in AI.items():
        p = src / (stem + '.jpg'); raw = Image.open(p)
        img[name] = seamless(raw) if name != 'rf_banner' else raw.convert('RGBA').resize((512, 512), Image.Resampling.LANCZOS)
        manifest.append({'texture': name, 'provenance': 'actual image-generation tool output (this project)', 'source': p.relative_to(ROOT).as_posix(),
                         'source_resolution': list(raw.size), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                         'processing': 'periodic edge correction' if name != 'rf_banner' else 'downscaled decal (not tiled)'})
    T = procedural(img); img.update(T)
    derived = {'rf_stonedark': 'rf_stone', 'rf_woodlight': 'rf_wood', 'rf_rock': 'rf_dungeon', 'rf_bark': 'rf_wood', 'rf_hedge': 'rf_grass', 'rf_flowers': 'rf_grass'}
    for name in T:
        manifest.append({'texture': name, 'provenance': ('AI-source derivative of ' + derived[name]) if name in derived else 'original deterministic procedural texture (materials.py)', 'resolution': list(T[name].size)})
    info = {}
    for group, names in GROUPS.items():
        d = txd.txd(); d.device_id = txd.DeviceType.DEVICE_D3D9
        d.native_textures = [native(n_, img[n_], n_ in ALPHA) for n_ in names]
        path = out / (group + '.txd'); d.write_file(str(path), RW_VERSION)
        info[group] = {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                       'textures': [{'name': t.name, 'size': [t.width, t.height], 'mips': t.num_levels, 'alpha': t.name in ALPHA} for t in d.native_textures]}
    note = {'ai_sources_generated': 9, 'ai_generation_note': 'a 10th AI texture (royal carpet) failed/was refused by the image tool limit; rf_carpetblue/rf_carpetred are procedural',
            'materials': manifest, 'groups': info}
    (ROOT / 'development' / 'TEXTURE_MANIFEST.json').write_text(json.dumps(note, indent=1))
    return info


if __name__ == '__main__':
    for g, i in build().items():
        print(g, i['bytes'], [t['name'] for t in i['textures']])
