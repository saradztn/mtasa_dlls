#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_txd.py - builds Dragon_2.5.txd (RenderWare Texture Dictionary, GTA:SA / MTA:SA
layout) for the Spider "Dragon 2.5" DFF, using only the images shipped in
Spider_sa.zip plus procedurally reconstructed artwork for the two texture slots
that have no matching image in the bundle (spider_eye, spider_teeth).

Requires: Python 3.8+ and Pillow  (pip install pillow)

Usage:
    python3 build_txd.py --source ../../Spider_sa.zip --out ../assets/Dragon_2.5.txd
    python3 build_txd.py --preview ../docs/texture_preview.png
    python3 build_txd.py --flip-rows           # only if the game shows them upside down

File layout written (identical chunk order to a shipping Rockstar GTA:SA txd):
    TextureDictionary (0x16)
        Struct (0x01)  -> uint16 textureCount, uint16 unknown(2)
        TextureNative (0x15) * textureCount
            Struct (0x01) -> 88 byte D3D9 header + mip level data
            Extension (0x03, empty)
        Extension (0x03, empty)

Header values: platform 9 (D3D9), filter word 0x001106 (FILTER_LINEAR_MIP_LINEAR,
WRAP/WRAP), rasterFormat 0x0500 (FORMAT_8888) or 0x0600 (FORMAT_888), d3dFormat
"A8R8G8B8" / "X8R8G8B8", depth 32, numLevels 1, rasterType 4, flag bit0 = alpha,
flag bit2 = auto mipmaps.  Texels are BGRA, first row first.
"""

import argparse
import io
import math
import os
import random
import struct
import sys
import zipfile

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
except ImportError:
    sys.stderr.write("Pillow is required:  pip install pillow\n")
    raise

# --------------------------------------------------------------------------
# RenderWare constants
# --------------------------------------------------------------------------
RW_VERSION = 0x1803FFFF          # RenderWare 3.6.0.3 (GTA:SA PC)
CHUNK_STRUCT = 0x01
CHUNK_EXTENSION = 0x03
CHUNK_TEXNATIVE = 0x15
CHUNK_TEXDICT = 0x16

PLATFORM_D3D9 = 9
FILTER_LINEAR_MIP_LINEAR = 0x06
ADDRESS_WRAP = 0x01

FORMAT_8888 = 0x0500             # RGBA, alpha used          -> D3DFMT_A8R8G8B8
FORMAT_888 = 0x0600              # RGB, alpha forced opaque  -> D3DFMT_X8R8G8B8
D3DFMT_A8R8G8B8 = 21             # the 4 byte format field holds the numeric
D3DFMT_X8R8G8B8 = 22             # D3DFORMAT value for uncompressed textures
                                 # (a FourCC such as "DXT1" only for compressed ones)

FLAG_ALPHA = 0x01
FLAG_AUTO_MIPMAPS = 0x04
RASTER_TYPE_STANDARD = 4


def make_filter_word(filter_mode=FILTER_LINEAR_MIP_LINEAR, u=ADDRESS_WRAP, v=ADDRESS_WRAP):
    return (filter_mode & 0xFF) | ((u & 0xF) << 8) | ((v & 0xF) << 12)


# --------------------------------------------------------------------------
# RenderWare binary writing
# --------------------------------------------------------------------------
def section(section_id, payload, version=RW_VERSION):
    return struct.pack("<III", section_id, len(payload), version) + payload


def texture_native(name, width, height, bgra, has_alpha, auto_mipmaps=True):
    """One TextureNative (0x15) section holding a single uncompressed level."""
    if len(bgra) != width * height * 4:
        raise ValueError("texel buffer size mismatch for %r" % name)
    name_bytes = name.encode("latin-1")
    if len(name_bytes) > 31:
        raise ValueError("texture name too long: %r" % name)

    header = bytearray()
    header += struct.pack("<I", PLATFORM_D3D9)
    header += struct.pack("<I", make_filter_word())
    header += name_bytes.ljust(32, b"\x00")
    header += b"".ljust(32, b"\x00")                       # alpha / mask texture name
    header += struct.pack("<I", FORMAT_8888 if has_alpha else FORMAT_888)
    header += struct.pack("<I", D3DFMT_A8R8G8B8 if has_alpha else D3DFMT_X8R8G8B8)
    header += struct.pack("<HH", width, height)
    flags = (FLAG_ALPHA if has_alpha else 0) | (FLAG_AUTO_MIPMAPS if auto_mipmaps else 0)
    header += struct.pack("<4B", 32, 1, RASTER_TYPE_STANDARD, flags)
    if len(header) != 88:
        raise AssertionError("D3D9 raster header must be 88 bytes, got %d" % len(header))

    payload = bytes(header) + struct.pack("<I", len(bgra)) + bgra
    return section(CHUNK_TEXNATIVE,
                   section(CHUNK_STRUCT, payload) + section(CHUNK_EXTENSION, b""))


def texture_dictionary(texture_sections):
    body = section(CHUNK_STRUCT, struct.pack("<HH", len(texture_sections), 2))
    body += b"".join(texture_sections)
    body += section(CHUNK_EXTENSION, b"")
    return section(CHUNK_TEXDICT, body)


# --------------------------------------------------------------------------
# Image helpers
# --------------------------------------------------------------------------
def to_bgra(img, flip_rows=False):
    """RGBA PIL image -> BGRA bytes. First row of the file = top row of the image."""
    img = img.convert("RGBA")
    if flip_rows:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    raw = img.tobytes()                                    # R,G,B,A order
    out = bytearray(len(raw))
    out[0::4] = raw[2::4]                                  # B
    out[1::4] = raw[1::4]                                  # G
    out[2::4] = raw[0::4]                                  # R
    out[3::4] = raw[3::4]                                  # A
    return bytes(out)


def resize_rgba_premultiplied(img, size):
    """Alpha-correct resize: no dark or white halos around soft edges."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    am = Image.merge("RGB", (a, a, a))

    def premultiply(ch):
        return ImageChops.multiply(ch.convert("RGB"), am).split()[0]

    pm = Image.merge("RGBA", (premultiply(r), premultiply(g), premultiply(b), a))
    pm = pm.resize(size, Image.LANCZOS)
    pr, pg, pb, pa = pm.split()
    al = list(pa.getdata())

    def unpremultiply(ch):
        out = [min(255, int(round(v * 255.0 / alpha))) if alpha else 0
               for v, alpha in zip(ch.getdata(), al)]
        res = Image.new("L", ch.size)
        res.putdata(out)
        return res

    return Image.merge("RGBA", (unpremultiply(pr), unpremultiply(pg), unpremultiply(pb), pa))


def smooth_noise(size, cells, seed):
    """Cheap tileable low-frequency noise in [0,255]."""
    rnd = random.Random(seed)
    small = Image.new("L", (cells, cells))
    small.putdata([rnd.randrange(256) for _ in range(cells * cells)])
    return small.resize(size, Image.BICUBIC)


def average_color(img, fraction=1.0, brightest=False):
    px = list(img.convert("RGB").getdata())
    px.sort(key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2], reverse=brightest)
    take = max(1, int(len(px) * fraction))
    sel = px[:take]
    return tuple(int(round(sum(c[i] for c in sel) / len(sel))) for i in range(3))


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def scale_color(c, k, lo=0, hi=255):
    return tuple(max(lo, min(hi, int(round(v * k)))) for v in c)


def checker(size, a=(58, 60, 66), b=(76, 78, 84), step=16):
    img = Image.new("RGB", size, a)
    d = ImageDraw.Draw(img)
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if ((x // step) + (y // step)) % 2:
                d.rectangle([x, y, x + step - 1, y + step - 1], fill=b)
    return img


# --------------------------------------------------------------------------
# Source assets
# --------------------------------------------------------------------------
class Sources(object):
    """Reads assets from the zip, or from an already extracted folder."""

    def __init__(self, source):
        self.source = source
        self.zip = None
        self.dir = None
        if os.path.isdir(source):
            self.dir = source
        elif zipfile.is_zipfile(source):
            self.zip = zipfile.ZipFile(source)
        else:
            raise SystemExit("source not found (zip or folder): %s" % source)

    def read(self, name):
        if self.zip is not None:
            with self.zip.open(name) as fh:
                return fh.read()
        with open(os.path.join(self.dir, name), "rb") as fh:
            return fh.read()

    def image(self, name):
        return Image.open(io.BytesIO(self.read(name)))


# --------------------------------------------------------------------------
# Texture generators.  Each returns (RGBA image, has_alpha)
# --------------------------------------------------------------------------
def gen_box(size, palette, seed=11):
    """'box' material - a quad whose 4 UVs are all (0,0): one quiet neutral texel
    field so it reads as a plain dark block surface whichever texel is used."""
    w, h = size
    base = mix(palette["mid"], palette["dark"], 0.55)
    gray = sum(base) // 3
    base = mix(base, (gray, gray, gray), 0.45)
    noise = smooth_noise((w, h), 4, seed)
    img = Image.new("RGB", (w, h))
    img.putdata([scale_color(base, 1.0 + (v - 128) / 900.0) for v in noise.getdata()])
    return img.convert("RGBA"), False


def gen_eye(size, palette, seed=23):
    """'spider_eye' - the DFF samples this texture about once every 4 mm across
    the eye spheroids, so the tile is deliberately a low contrast dark organic
    surface: at play distance it averages to the dark brown of the rest of the
    spider, up close it shows a fine lens facet pattern with two wet highlights.
    Built seamless so the very high repeat rate produces no visible seam grid."""
    w, h = size
    ss = 4
    W, H = w * ss, h * ss
    dark = palette["darkest"]
    base_color = mix(palette["dark"], dark, 0.55)
    glint = mix(palette["bright"], (255, 246, 230), 0.40)

    n1 = smooth_noise((W, H), 4, seed)
    n2 = smooth_noise((W, H), 13, seed + 1)
    img = Image.new("RGB", (W, H))
    img.putdata([scale_color(base_color, max(0.60, min(1.22,
                    0.94 + (a - 128) / 255.0 * 0.30 + (b - 128) / 255.0 * 0.16)))
                 for a, b in zip(n1.getdata(), n2.getdata())])

    # fine lens facets: a wrapped grid of small rounded cells with slight shading
    facets = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(facets)
    rnd = random.Random(seed + 5)
    step = max(6, W // 14)
    for gy in range(-1, H // step + 2):
        for gx in range(-1, W // step + 2):
            cx = gx * step + (step // 2 if gy % 2 else 0)
            cy = gy * step
            r = int(step * (0.34 + rnd.random() * 0.06))
            k = 0.82 + rnd.random() * 0.36
            col = scale_color(base_color, k)
            fd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (110,))
    wrapped = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            wrapped.alpha_composite(facets, (dx * W, dy * H))
    img = Image.alpha_composite(img.convert("RGBA"), wrapped).convert("RGB")

    # two soft wet highlights, wrapped so they survive the tiling
    domes = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(domes)
    for (ox, oy, rr) in ((0.30, 0.34, 0.20), (0.72, 0.66, 0.15)):
        cx, cy, r = int(ox * W), int(oy * H), int(rr * W)
        for step_i in range(30, 0, -1):
            t = step_i / 30.0                       # 1 at the outer edge, ->0 in the centre
            rad = max(1, int(r * t))
            dd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                       fill=mix(glint, dark, min(1.0, t * 1.25)) + (int(150 * (1 - t) ** 0.8),))
    wrapped = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            wrapped.alpha_composite(domes, (dx * W, dy * H))
    out = Image.alpha_composite(img.convert("RGBA"), wrapped)
    return out.resize((w, h), Image.LANCZOS), False


def gen_teeth(size, palette, seed=37):
    """'spider_teeth' - ivory fangs on a dark gum background.

    The mouth ring only samples the middle 30% window of this texture
    (U and V both 0.35 .. 0.65), so the fangs are laid out as a dense,
    interlocking field that covers the whole tile - no matter which part of the
    tile is addressed, fangs are visible.  Alpha = fang silhouette; the
    background stays dark gum so it still reads if alpha is disabled."""
    w, h = size
    ss = 8
    W, H = w * ss, h * ss
    gum = mix(palette["dark"], palette["mid"], 0.30)
    gum_dark = mix(palette["darkest"], gum, 0.40)
    ivory = mix(palette["bright"], (255, 250, 238), 0.55)
    ivory_root = mix(ivory, palette["mid"], 0.45)

    canvas = Image.new("RGBA", (W, H), gum + (255,))
    mask = Image.new("L", (W, H), 0)
    dcol = ImageDraw.Draw(canvas)
    dmask = ImageDraw.Draw(mask)

    def fang(cx, base_y, width, length, up):
        """One tapered fang, drawn with horizontal and vertical wrapping."""
        for kx in (-1, 0, 1):
            for ky in (-1, 0, 1):
                x = cx + kx * W
                base = base_y + ky * H
                tip = base - length if up else base + length
                quad = [(x - width // 2, base), (x + width // 2, base),
                        (x + width // 6, tip), (x - width // 6, tip)]
                dcol.polygon(quad, fill=ivory + (255,))
                dmask.polygon(quad, fill=255)
                # root shading + a lit edge
                dcol.polygon([(x - width // 2, base), (x - width // 8, base),
                              (x - width // 8, tip), (x - width // 6, tip)],
                             fill=ivory_root + (255,))
                dcol.line([(x - width // 2, base), (x - width // 6, tip)],
                          fill=mix(ivory_root, gum_dark, 0.45) + (255,), width=2)
                dcol.line([(x + width // 2 - 2, base), (x + width // 6, tip)],
                          fill=mix(ivory, (255, 255, 255), 0.35) + (200,), width=2)

    # fang bases sit on the tile edges and the tips overlap across the middle, so
    # the tile is a dense interlocking fang field with no empty band anywhere -
    # important because the mouth ring only addresses the central UV window.
    cols = 7
    col_w = W / float(cols)
    fang_w = int(col_w * 0.82)
    length = int(H * 0.62)
    for i in range(cols):
        cx = int((i + 0.5) * col_w)
        fang(cx, 0, fang_w, length, up=False)                     # hangs from the top edge
        fang(cx + int(col_w * 0.5), H, fang_w, length, up=True)   # rises from the bottom edge

    # soft tone variation on the gum background
    n = smooth_noise((W, H), 5, seed)
    shade = Image.new("RGBA", (W, H), gum_dark + (255,))
    canvas = Image.composite(shade, canvas, n.point(lambda v: 255 if v < 112 else 0))

    out = canvas.resize((w, h), Image.LANCZOS)
    out.putalpha(mask.resize((w, h), Image.LANCZOS))
    return out, True


def gen_sh3(img, size):
    """'i_sh3' - hair strand strip built from the pale spike in SH3.png.

    The DFF repeats this texture roughly nine times across every hair card, so a
    single centred spike would stamp out an obvious mechanical row.  The source
    spike is cropped to its alpha bounds and stamped three times at different
    heights and widths, all wrapped, making one seamless strand pattern that
    reads as fur at any repeat count."""
    w, h = size
    src = img.convert("RGBA")
    bbox = src.split()[3].point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        src = src.crop(bbox)

    ss = 4
    W, H = w * ss, h * ss
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # (centre x, height fraction, width fraction of tile) - several strands of
    # different sizes so the pattern still reads as fur after many repeats
    strands = ((0.08, 0.72, 0.20), (0.22, 0.94, 0.24), (0.36, 0.60, 0.18),
               (0.50, 0.84, 0.22), (0.63, 0.68, 0.19), (0.78, 1.00, 0.25),
               (0.92, 0.56, 0.17))
    for (cx, hf, wf) in strands:
        tw = max(4, int(wf * W))
        th = max(4, int(hf * H))
        spike = src.resize((tw, th), Image.LANCZOS)
        for kx in (-1, 0, 1):
            canvas.alpha_composite(spike, (int(cx * W) - tw // 2 + kx * W, H - th))
    return resize_rgba_premultiplied(canvas, (w, h)), True


def gen_leg(img, size, detail_img=None, detail_strength=0.25):
    """'i' - the furry leg texture resized to power-of-two.  The shipped image
    already tiles (edge delta < 5/255), so no seam surgery is needed.  The
    optional hair normal map is baked in as subtle strand relief, because
    RenderWare / GTA:SA has no normal map slot to use it directly."""
    w, h = size
    base = img.convert("RGB").resize((w, h), Image.LANCZOS)
    if detail_img is None or detail_strength <= 0:
        return base.convert("RGBA"), False

    nrm = detail_img.convert("RGB").resize((w, h), Image.LANCZOS)
    nrm = nrm.filter(ImageFilter.GaussianBlur(0.6))
    lx, ly, lz = 0.35, 0.45, 0.82                          # tangent space light
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln

    shades = []
    for (r, g, b) in nrm.getdata():
        nx, ny, nz = (r / 255.0) * 2 - 1, (g / 255.0) * 2 - 1, (b / 255.0) * 2 - 1
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        shades.append(max(0.0, (nx / nl) * lx + (ny / nl) * ly + (nz / nl) * lz))
    mean = sum(shades) / len(shades)

    res = Image.new("RGB", (w, h))
    res.putdata([scale_color(px, max(0.72, min(1.28,
                    1.0 + detail_strength * (s - mean) * 1.6)))
                 for px, s in zip(base.getdata(), shades)])
    return res.convert("RGBA"), False


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
TEXTURE_ORDER = ["box", "spider_eye", "i_sh3", "spider_teeth", "i"]   # DFF material order


def build_palette(sources):
    leg = sources.image("Spinnen_Bein_tex.jpg").convert("RGB")
    return {
        "leg": leg,
        "leg_alt": sources.image("Spinnen_Bein_tex_2.jpg").convert("RGB"),
        "sh3": sources.image("SH3.png"),
        "nrm": sources.image("haar_detail_NRM.jpg"),
        "darkest": average_color(leg, 0.10, brightest=False),
        "dark": average_color(leg, 0.30, brightest=False),
        "mid": average_color(leg, 1.0),
        "bright": average_color(leg, 0.05, brightest=True),
    }


def make_textures(sources, palette, detail_strength=0.25, seed=2026):
    return {
        "box": gen_box((64, 64), palette, seed + 1),
        "spider_eye": gen_eye((64, 64), palette, seed + 2),
        "i_sh3": gen_sh3(palette["sh3"], (128, 128)),
        "spider_teeth": gen_teeth((64, 64), palette, seed + 3),
        "i": gen_leg(palette["leg"], (128, 256), palette["nrm"], detail_strength),
    }


def preview_sheet(textures, path, scale=2):
    cell_w = max(img.width for img, _ in textures.values()) * scale
    cell_h = max(img.height for img, _ in textures.values()) * scale
    sheet = checker((cell_w * len(textures), cell_h))
    for i, name in enumerate(TEXTURE_ORDER):
        img, has_alpha = textures[name]
        big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        sheet.paste(big, (i * cell_w + (cell_w - big.width) // 2,
                          (cell_h - big.height) // 2), big if has_alpha else None)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sheet.save(path)
    return sheet.size


def build(args):
    sources = Sources(args.source)
    palette = build_palette(sources)
    textures = make_textures(sources, palette, args.detail, args.seed)

    sections, report = [], []
    for name in TEXTURE_ORDER:
        img, has_alpha = textures[name]
        data = to_bgra(img, flip_rows=args.flip_rows)
        sections.append(texture_native(name, img.width, img.height, data, has_alpha))
        report.append((name, "%dx%d" % (img.width, img.height),
                       "A8R8G8B8" if has_alpha else "X8R8G8B8", has_alpha, len(data)))

    blob = texture_dictionary(sections)
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(blob)
    if args.preview:
        preview_sheet(textures, args.preview)

    print("wrote %s (%d bytes, %d textures)" % (out_path, len(blob), len(sections)))
    if args.preview:
        print("preview: %s" % os.path.abspath(args.preview))
    print("palette sampled from the provided images:")
    print("   darkest=%s dark=%s mid=%s bright=%s"
          % (palette["darkest"], palette["dark"], palette["mid"], palette["bright"]))
    for (name, size, fmt, alpha, nbytes) in report:
        print("   %-14s %-9s %-9s alpha=%-5s %d texel bytes" % (name, size, fmt, alpha, nbytes))
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Build Dragon_2.5.txd from the Spider_sa assets")
    ap.add_argument("--source", default=os.path.normpath(os.path.join(here, "..", "..", "Spider_sa.zip")),
                    help="Spider_sa.zip or a folder with the extracted images")
    ap.add_argument("--out", default=os.path.normpath(os.path.join(here, "..", "assets", "Dragon_2.5.txd")))
    ap.add_argument("--preview", default=os.path.normpath(os.path.join(here, "..", "docs", "texture_preview.png")),
                    help="preview PNG ('' to skip)")
    ap.add_argument("--detail", type=float, default=0.25,
                    help="strength of the hair normal map detail baked into 'i' (0..1)")
    ap.add_argument("--seed", type=int, default=2026, help="art RNG seed")
    ap.add_argument("--flip-rows", action="store_true",
                    help="store texels bottom-up (only if the game shows them upside down)")
    args = ap.parse_args(argv)
    if args.preview == "":
        args.preview = None
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
