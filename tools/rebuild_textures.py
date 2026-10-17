#!/usr/bin/env python3
"""
NextGenPoliceDepartment - Photorealistic Material & Texture Pipeline (tools/rebuild_textures.py)

Rebuilds:
  * textures/ngpd_world_high.txd (60 D3D9 native mipmapped textures: DXT1 / DXT3 / DXT5)
  * textures/ngpd_world_med.txd  (60 D3D9 native mipmapped textures, 512px max)
  * textures/ngpd_world_low.txd  (60 D3D9 native mipmapped textures, 256px max)
  * textures/<category>/<name>_n.dds (DXT5nm swizzled normal maps: R=255, G=Ny, B=0, A=Nx)
  * textures/<category>/<name>_s.dds (DXT5 PBR surface maps: R=Roughness, G=AO, B=Mask, A=Metallic)
  * textures/<category>/med/<name>_{n,s}.dds (512px medium-tier maps for 1024px high-tier textures)
  * assets/textures_preview/before_after_comparison.png (visual QA sheet)
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import struct
import sys
from collections import namedtuple
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy.ndimage import gaussian_filter, sobel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "vendor" / "DragonFF"))
from gtaLib import txd

RW_VERSION = 0x36003
ORIG_RES = Path("/tmp/original_resource")
if not ORIG_RES.exists():
    ORIG_RES = ROOT / "backup" / "original_resource"

SRC_TEX_DIR = ROOT / "assets" / "source_textures"
OUT_TEX_DIR = ROOT / "textures"
PREVIEW_DIR = ROOT / "assets" / "textures_preview"


def make_seamless(im: Image.Image, size: int | tuple[int, int] = 1024) -> np.ndarray:
    """Convert an image into a seamlessly tiling float32 RGB array of shape (H, W, 3)."""
    if isinstance(size, int):
        w = h = size
    else:
        w, h = size
    arr = np.asarray(im.convert("RGB").resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32)
    # Remove low-frequency illumination gradient so tiling has zero brightness seams
    low_freq = gaussian_filter(arr, sigma=(h // 6, w // 6, 0), mode="wrap")
    mean_col = arr.mean(axis=(0, 1), keepdims=True)
    arr = arr - low_freq + mean_col
    # Cosine cross-blend across periodic boundaries
    u = np.linspace(0.0, 1.0, w, endpoint=False, dtype=np.float32)[None, :, None]
    v = np.linspace(0.0, 1.0, h, endpoint=False, dtype=np.float32)[:, None, None]
    wx = 0.5 - 0.5 * np.cos(2.0 * math.pi * u)
    wy = 0.5 - 0.5 * np.cos(2.0 * math.pi * v)
    shifted = np.roll(np.roll(arr, h // 2, axis=0), w // 2, axis=1)
    blend = wx * wy
    out = arr * blend + shifted * (1.0 - blend)
    return np.clip(out, 0.0, 255.0)


def fbm_noise(h: int, w: int, octaves=(2.0, 6.0, 18.0, 48.0), weights=(0.15, 0.25, 0.35, 0.25), seed=42) -> np.ndarray:
    """Zero-mean unit-std multi-octave periodic fractal noise."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    for sig, wt in zip(octaves, weights):
        raw = rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)
        flt = gaussian_filter(raw, sigma=sig, mode="wrap")
        flt /= max(1e-6, float(flt.std()))
        acc += flt * wt
    acc /= max(1e-6, float(acc.std()))
    return acc


def crack_network(h: int, w: int, seed=101, density=2) -> np.ndarray:
    """Generate realistic branching hairline crack depth field in [0, 1] (1 = deep crack)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    for k in range(density):
        f1 = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=28.0 + k * 14.0, mode="wrap")
        f2 = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=6.0 + k * 3.0, mode="wrap")
        f = f1 * 0.8 + f2 * 0.2
        f /= max(1e-6, float(f.std()))
        ridge = np.exp(-((np.abs(f) * 28.0) ** 1.6))
        mask = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=45.0, mode="wrap")
        mask = np.clip(mask / max(1e-6, float(mask.std())) + 0.2, 0.0, 1.0)
        acc = np.maximum(acc, ridge * mask)
    return np.clip(acc, 0.0, 1.0)


def puddle_mask_field(h: int, w: int, seed=202, coverage=0.52) -> np.ndarray:
    """Organic multi-scale puddle basin mask in [0, 1] with natural depth gradients."""
    rng = np.random.default_rng(seed)
    macro = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=max(16.0, h / 11.0), mode="wrap")
    meso = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=max(6.0, h / 32.0), mode="wrap")
    micro = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), sigma=max(2.0, h / 96.0), mode="wrap")
    field = macro * 0.62 + meso * 0.28 + micro * 0.10
    field = (field - field.min()) / max(1e-6, float(field.max() - field.min()))
    # Shape so that puddle basins have smooth meniscus edges and flat deep centers
    thresh = 1.0 - coverage
    puddle = np.clip((field - thresh) / max(0.15, 1.0 - thresh), 0.0, 1.0)
    puddle = puddle * puddle * (3.0 - 2.0 * puddle)
    return np.clip(field * 0.35 + puddle * 0.65, 0.0, 1.0)


def height_to_dxt5nm(height: np.ndarray, strength: float = 3.2) -> Image.Image:
    """Convert a heightfield (H, W) in [0, 1] to a DXT5nm swizzled normal map (R=255, G=Ny, B=0, A=Nx)."""
    h_f = height.astype(np.float32)
    dx = sobel(h_f, axis=1, mode="wrap") * (strength / 8.0)
    dy = sobel(h_f, axis=0, mode="wrap") * (strength / 8.0)
    nx = -dx
    ny = -dy
    nz = np.ones_like(nx)
    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    nx *= inv_len
    ny *= inv_len
    g_chan = np.clip((ny * 0.5 + 0.5) * 255.0, 0.0, 255.0).astype(np.uint8)
    a_chan = np.clip((nx * 0.5 + 0.5) * 255.0, 0.0, 255.0).astype(np.uint8)
    r_chan = np.full_like(g_chan, 255, dtype=np.uint8)
    b_chan = np.zeros_like(g_chan, dtype=np.uint8)
    return Image.fromarray(np.dstack([r_chan, g_chan, b_chan, a_chan]), mode="RGBA")


def pack_surface_map(rough: np.ndarray, ao: np.ndarray, mask: np.ndarray, metal: np.ndarray) -> Image.Image:
    """Pack R=Roughness, G=AO, B=Mask (puddle/emissive), A=Metallic into an RGBA Image."""
    r = np.clip(rough * 255.0, 0.0, 255.0).astype(np.uint8)
    g = np.clip(ao * 255.0, 0.0, 255.0).astype(np.uint8)
    b = np.clip(mask * 255.0, 0.0, 255.0).astype(np.uint8)
    a = np.clip(metal * 255.0, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(np.dstack([r, g, b, a]), mode="RGBA")


def dds_pixels(image: Image.Image, fmt: str) -> bytes:
    b = io.BytesIO()
    image.save(b, format="DDS", pixel_format=fmt)
    data = b.getvalue()
    assert data[:4] == b"DDS " and data[84:88] == fmt.encode("ascii")
    return data[128:]


def mip_chain_dds(image: Image.Image) -> list[Image.Image]:
    """Generate mip chain stopping at min(w, h) == 4 (exact DXT block boundary)."""
    chain = [image]
    cur = image
    while cur.width > 4 and cur.height > 4:
        cur = cur.resize((max(4, cur.width // 2), max(4, cur.height // 2)), Image.Resampling.LANCZOS)
        chain.append(cur)
    return chain


def write_mipmapped_dds(image: Image.Image, path: Path, fmt: str = "DXT5") -> None:
    """Write a complete D3D9 mipmapped DDS file matching the exact NGPD binary layout."""
    chain = mip_chain_dds(image)
    w, h = image.width, image.height
    block_bytes = 8 if fmt == "DXT1" else 16
    pitch = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block_bytes
    flags = 0x000A1007  # DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE
    caps = 0x00401008   # DDSCAPS_COMPLEX | DDSCAPS_MIPMAP | DDSCAPS_TEXTURE
    hdr = struct.pack(
        "<4s7I44s2I4s5I5I",
        b"DDS ", 124, flags, h, w, pitch, 0, len(chain),
        b"\x00" * 44,
        32, 4, fmt.encode("ascii"), 0, 0, 0, 0, 0,
        caps, 0, 0, 0, 0,
    )
    payload = b"".join(dds_pixels(lv, fmt) for lv in chain)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(hdr + payload)


def make_native_txd_entry(name: str, image: Image.Image, alpha_fmt: str | None = None) -> txd.TextureNative:
    """Create a RenderWare D3D9 TextureNative entry with full mipmaps and anisotropic-ready filtering."""
    has_alpha = alpha_fmt is not None
    fmt_str = alpha_fmt if has_alpha else "DXT1"
    t = txd.TextureNative()
    t.platform_id = 9
    t.filter_mode = 6  # FILTER_MIPLINEAR (supports anisotropic filtering in D3D9 sampler)
    t.uv_addressing = 0x11
    t.name = name
    t.mask = ""
    t.width = image.width
    t.height = image.height
    t.depth = 32 if has_alpha else 16
    t.raster_type = 4
    if fmt_str == "DXT3":
        t.raster_format_flags = 0x0300 | 0x8000
        t.d3d_format = txd.D3DFormat.D3D_DXT3
    elif fmt_str == "DXT5":
        t.raster_format_flags = 0x0500 | 0x8000
        t.d3d_format = txd.D3DFormat.D3D_DXT5
    else:
        t.raster_format_flags = 0x0200 | 0x8000
        t.d3d_format = txd.D3DFormat.D3D_DXT1
    P = namedtuple("PlatformProperties", "alpha cube_texture auto_mipmaps compressed")
    t.platform_properties = P(has_alpha, False, False, True)
    chain = mip_chain_dds(image)
    t.pixels = [dds_pixels(lv, fmt_str) for lv in chain]
    t.num_levels = len(t.pixels)
    return t


def load_original_txd_images() -> dict[str, Image.Image]:
    """Load the original high-tier TXD images so we preserve exact decals/text layouts."""
    orig_txd_path = ORIG_RES / "textures" / "ngpd_world_high.txd"
    t = txd.txd()
    t.load_file(str(orig_txd_path))
    out = {}
    for nt in t.native_textures:
        w, h = nt.width, nt.height
        fourcc = nt.d3d_format.to_bytes(4, "little")
        flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000
        pitch = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * (8 if fourcc == b"DXT1" else 16)
        hdr = struct.pack(
            "<4s7I44s8I20s",
            b"DDS ", 124, flags, h, w, pitch, 0, 1, b"\x00" * 44,
            32, 0x4, int.from_bytes(fourcc, "little"), 0, 0, 0, 0, 0,
            struct.pack("<5I", 0x1000, 0, 0, 0, 0),
        )
        out[nt.name] = Image.open(io.BytesIO(hdr + nt.pixels[0])).convert("RGBA")
    return out


def generate_botanical_foliage(size: int = 1024) -> tuple[Image.Image, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate a high-definition 1024x1024 botanical tree branch & leaf cluster texture with:
      - Curved woody branch stems and secondary twigs
      - Layered ovate/lanceolate leaves with serrated margins, midribs, and lateral veins
      - Natural chlorophyll variation (deep forest green, olive, sunlit golden-green tips)
      - Mipmap-safe alpha coverage and matching leaf relief height + roughness + AO
    """
    rng = np.random.default_rng(20261017)
    im = Image.new("RGBA", (size, size), (38, 66, 28, 0))
    height_im = Image.new("L", (size, size), 128)
    draw = ImageDraw.Draw(im)
    hdraw = ImageDraw.Draw(height_im)

    # 1. Draw organic woody twigs radiating through the cluster so branches connect naturally
    for b in range(18):
        x0 = rng.uniform(0.08, 0.92) * size
        y0 = rng.uniform(0.08, 0.92) * size
        ang = rng.uniform(0, 2 * math.pi)
        length = rng.uniform(0.18, 0.34) * size
        pts = []
        for s in range(8):
            t = s / 7.0
            ang += rng.uniform(-0.22, 0.22)
            px = (x0 + math.cos(ang) * length * t) % size
            py = (y0 + math.sin(ang) * length * t) % size
            pts.append((px, py))
        for s in range(len(pts) - 1):
            p1, p2 = pts[s], pts[s + 1]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < size * 0.4:
                w = max(2, int((1.0 - s / 8.0) * (size / 140)))
                draw.line([p1, p2], fill=(68, 52, 36, 235), width=w)
                hdraw.line([p1, p2], fill=195, width=w)

    # 2. Draw 3 layers of botanical leaves (back shadow layer, mid canopy layer, sunlit top layer)
    palettes = [
        # Back layer (cooler, deeper emerald-olive)
        [(28, 54, 22), (34, 62, 26), (31, 58, 24), (40, 68, 28)],
        # Mid layer (rich chlorophyll greens)
        [(44, 78, 30), (52, 88, 34), (48, 84, 32), (60, 94, 36), (38, 72, 28)],
        # Top sunlit layer (warm golden-hour kissed leaf tips)
        [(68, 108, 38), (78, 118, 42), (88, 126, 44), (62, 100, 36)],
    ]
    counts = [240, 320, 220]
    for layer_idx, (pal, count) in enumerate(zip(palettes, counts)):
        for _ in range(count):
            cx = rng.uniform(0.03, 0.97) * size
            cy = rng.uniform(0.03, 0.97) * size
            ang = rng.uniform(0.0, 2.0 * math.pi)
            leaf_len = rng.uniform(0.042, 0.088) * size * (1.0 - 0.08 * layer_idx)
            leaf_wid = leaf_len * rng.uniform(0.42, 0.62)
            base_col = pal[int(rng.integers(len(pal)))]
            jitter = rng.integers(-8, 9, size=3)
            r = int(np.clip(base_col[0] + jitter[0], 18, 145))
            g = int(np.clip(base_col[1] + jitter[1], 36, 175))
            b = int(np.clip(base_col[2] + jitter[2], 14, 95))

            ca, sa = math.cos(ang), math.sin(ang)
            # Construct natural ovate/acuminate leaf silhouette with 16 perimeter points
            poly = []
            n_pts = 16
            for k in range(n_pts):
                theta = 2.0 * math.pi * k / n_pts
                # u along leaf axis (-1 base .. +1 pointed tip), v across width
                u = math.cos(theta)
                # Tapered tip and rounded base profile + subtle serration
                taper = (1.0 - 0.35 * u) * math.sin(theta)
                serr = 1.0 + 0.06 * math.sin(theta * 7.0)
                lx = u * (leaf_len * 0.5)
                ly = taper * serr * (leaf_wid * 0.5)
                wx = cx + lx * ca - ly * sa
                wy = cy + lx * sa + ly * ca
                poly.append((wx, wy))

            draw.polygon(poly, fill=(r, g, b, 252), outline=(max(12, r - 14), max(24, g - 16), max(10, b - 10), 255))
            h_val = int(115 + layer_idx * 45 + rng.integers(-12, 12))
            hdraw.polygon(poly, fill=h_val)

            # Central midrib vein
            p_base = (cx - 0.42 * leaf_len * ca, cy - 0.42 * leaf_len * sa)
            p_tip = (cx + 0.44 * leaf_len * ca, cy + 0.44 * leaf_len * sa)
            vein_col = (min(255, r + 18), min(255, g + 22), min(255, b + 10), 255)
            draw.line([p_base, p_tip], fill=vein_col, width=max(1, size // 512))
            hdraw.line([p_base, p_tip], fill=min(255, h_val + 28), width=max(1, size // 512))

    arr = np.asarray(im, dtype=np.float32)
    # Bleed RGB colors into transparent background pixels so mipmapping never produces dark fringes!
    alpha = arr[:, :, 3] / 255.0
    rgb = arr[:, :, :3].copy()
    mask_opaque = alpha > 0.25
    mean_leaf = rgb[mask_opaque].mean(axis=0) if mask_opaque.any() else np.array([48.0, 86.0, 34.0])
    blurred_rgb = gaussian_filter(rgb, sigma=(6.0, 6.0, 0.0), mode="wrap")
    blurred_a = gaussian_filter(alpha, sigma=6.0, mode="wrap")[:, :, None]
    fill_rgb = np.where(blurred_a > 0.02, blurred_rgb / np.maximum(blurred_a, 0.02), mean_leaf[None, None, :])
    rgb_clean = np.where(alpha[:, :, None] > 0.15, rgb, fill_rgb)
    # Add fine cellular micro-variation across leaves
    cell_noise = fbm_noise(size, size, octaves=(1.5, 4.0, 12.0), weights=(0.5, 0.3, 0.2), seed=888)
    rgb_clean = np.clip(rgb_clean + cell_noise[:, :, None] * 6.5, 0.0, 255.0)
    out_im = Image.fromarray(
        np.dstack([rgb_clean.astype(np.uint8), np.clip(arr[:, :, 3], 0, 255).astype(np.uint8)]),
        mode="RGBA",
    )
    h_arr = np.asarray(height_im, dtype=np.float32) / 255.0
    h_arr = np.clip(h_arr + cell_noise * 0.08, 0.0, 1.0)
    rough = np.clip(0.42 - 0.12 * (h_arr - 0.5) + cell_noise * 0.05, 0.22, 0.68)
    ao = np.clip(0.55 + 0.45 * h_arr, 0.35, 1.0)
    return out_im, h_arr, rough, ao


def build_all_textures() -> dict:
    """Synthesize all 60 TXD materials + 144 DDS normal/surface maps from photographic AI sources & PBR laws."""
    orig_imgs = load_original_txd_images()
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TEX_DIR.mkdir(parents=True, exist_ok=True)

    # Load and make seamless our 10 photographic 2K AI source masters
    src = {}
    for key, fname in [
        ("asph_road", "asphalt_road_source.jpg"),
        ("asph_parking", "asphalt_parking_source.jpg"),
        ("conc_facade", "concrete_facade_source.jpg"),
        ("sidewalk", "sidewalk_paving_source.jpg"),
        ("plaza_stone", "plaza_stone_source.jpg"),
        ("bark", "tree_bark_source.jpg"),
        ("lobby", "polished_lobby_source.jpg"),
        ("grass", "grass_ground_source.jpg"),
        ("metal_panel", "metal_panel_source.jpg"),
        ("wood_desk", "wood_desk_source.jpg"),
    ]:
        p = SRC_TEX_DIR / fname
        src[key] = make_seamless(Image.open(p), 1024)

    high_albedo: dict[str, Image.Image] = {}
    alpha_format: dict[str, str | None] = {}
    dds_records: list[dict] = []

    def register_material(
        name: str,
        category: str,
        albedo_rgba: Image.Image,
        height: np.ndarray,
        rough: np.ndarray,
        ao: np.ndarray,
        mask: np.ndarray,
        metal: np.ndarray,
        normal_strength: float = 3.2,
        alpha_fmt: str | None = None,
        has_med_dds: bool = False,
        in_txd: bool = True,
    ):
        if in_txd:
            high_albedo[name] = albedo_rgba
            alpha_format[name] = alpha_fmt
        nm_im = height_to_dxt5nm(height, strength=normal_strength)
        sf_im = pack_surface_map(rough, ao, mask, metal)
        n_path = OUT_TEX_DIR / category / f"{name}_n.dds"
        s_path = OUT_TEX_DIR / category / f"{name}_s.dds"
        write_mipmapped_dds(nm_im, n_path, "DXT5")
        write_mipmapped_dds(sf_im, s_path, "DXT5")
        rec = {
            "name": name,
            "category": category,
            "size": [albedo_rgba.width, albedo_rgba.height],
            "normal_dds": n_path.relative_to(ROOT).as_posix(),
            "surface_dds": s_path.relative_to(ROOT).as_posix(),
        }
        if has_med_dds:
            mw = max(64, nm_im.width // 2)
            mh = max(64, nm_im.height // 2)
            mn_path = OUT_TEX_DIR / category / "med" / f"{name}_n.dds"
            ms_path = OUT_TEX_DIR / category / "med" / f"{name}_s.dds"
            write_mipmapped_dds(nm_im.resize((mw, mh), Image.Resampling.LANCZOS), mn_path, "DXT5")
            write_mipmapped_dds(sf_im.resize((mw, mh), Image.Resampling.LANCZOS), ms_path, "DXT5")
            rec["med_normal_dds"] = mn_path.relative_to(ROOT).as_posix()
            rec["med_surface_dds"] = ms_path.relative_to(ROOT).as_posix()
        dds_records.append(rec)

    # ------------------------------------------------------------------ 1. ASPHALT & GROUND
    # 1a. ngpd_asph_road (1024x1024)
    ar = src["asph_road"].copy()
    cracks_r = crack_network(1024, 1024, seed=11, density=3)
    micro_r = fbm_noise(1024, 1024, octaves=(1.2, 3.0, 8.0, 24.0), weights=(0.45, 0.25, 0.15, 0.15), seed=12)
    # Subtle wheel-rut wear bands along V
    yy, xx = np.mgrid[0:1024, 0:1024]
    rut = 0.5 * (np.exp(-(((xx - 290) / 85.0) ** 2)) + np.exp(-(((xx - 734) / 85.0) ** 2))).astype(np.float32)
    ar = ar * (0.82 + 0.08 * rut[:, :, None]) + micro_r[:, :, None] * 6.5 - cracks_r[:, :, None] * 28.0
    ar_im = Image.fromarray(np.dstack([np.clip(ar, 18, 235).astype(np.uint8), np.full((1024, 1024), 255, np.uint8)]), "RGBA")
    lum_r = ar.mean(axis=2) / 255.0
    h_road = np.clip(lum_r * 0.65 + (micro_r * 0.12 + 0.5) * 0.35 - cracks_r * 0.55 - rut * 0.08, 0.0, 1.0)
    puddle_r = np.clip(puddle_mask_field(1024, 1024, seed=101, coverage=0.58) + rut * 0.22 + cracks_r * 0.25, 0.0, 1.0)
    rough_r = np.clip(0.76 - rut * 0.16 - lum_r * 0.14 + micro_r * 0.06, 0.28, 0.92)
    ao_r = np.clip(0.86 + (lum_r - 0.25) * 0.45 - cracks_r * 0.52, 0.22, 1.0)
    register_material("ngpd_asph_road", "asphalt", ar_im, h_road, rough_r, ao_r, puddle_r, np.zeros_like(h_road), normal_strength=4.2, has_med_dds=True)

    # 1b. ngpd_asph_parking (1024x1024)
    ap = src["asph_parking"].copy()
    cracks_p = crack_network(1024, 1024, seed=21, density=2)
    micro_p = fbm_noise(1024, 1024, octaves=(1.2, 3.5, 12.0, 36.0), weights=(0.4, 0.3, 0.15, 0.15), seed=22)
    oil = np.clip(fbm_noise(1024, 1024, octaves=(18.0, 42.0), weights=(0.5, 0.5), seed=23) - 0.65, 0.0, 1.0)
    ap = ap * (0.86 - 0.22 * oil[:, :, None]) + micro_p[:, :, None] * 6.0 - cracks_p[:, :, None] * 24.0
    ap_im = Image.fromarray(np.dstack([np.clip(ap, 20, 235).astype(np.uint8), np.full((1024, 1024), 255, np.uint8)]), "RGBA")
    lum_p = ap.mean(axis=2) / 255.0
    h_park = np.clip(lum_p * 0.65 + (micro_p * 0.12 + 0.5) * 0.35 - cracks_p * 0.50, 0.0, 1.0)
    puddle_p = np.clip(puddle_mask_field(1024, 1024, seed=202, coverage=0.52) + oil * 0.20 + cracks_p * 0.20, 0.0, 1.0)
    rough_p = np.clip(0.74 - oil * 0.28 - lum_p * 0.12 + micro_p * 0.06, 0.24, 0.90)
    ao_p = np.clip(0.88 + (lum_p - 0.25) * 0.42 - cracks_p * 0.48, 0.25, 1.0)
    register_material("ngpd_asph_parking", "asphalt", ap_im, h_park, rough_p, ao_p, puddle_p, np.zeros_like(h_park), normal_strength=4.0, has_med_dds=True)

    # 1c. ngpd_ground_slab (512x512)
    gs_base = Image.fromarray(src["sidewalk"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS)
    gs = np.asarray(gs_base, dtype=np.float32) * 0.96 + fbm_noise(512, 512, seed=31)[:, :, None] * 5.5
    gs_im = Image.fromarray(np.dstack([np.clip(gs, 30, 240).astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_gs = np.clip(gs.mean(axis=2) / 255.0, 0.0, 1.0)
    puddle_gs = puddle_mask_field(512, 512, seed=303, coverage=0.42)
    register_material("ngpd_ground_slab", "asphalt", gs_im, h_gs, np.clip(0.68 - 0.15 * h_gs, 0.35, 0.85), np.clip(0.75 + 0.25 * h_gs, 0.4, 1.0), puddle_gs, np.zeros_like(h_gs), normal_strength=3.2)

    # ------------------------------------------------------------------ 2. CONCRETE & MASONRY
    cf = src["conc_facade"].copy()
    cf_micro = fbm_noise(1024, 1024, octaves=(1.5, 5.0, 18.0), weights=(0.45, 0.35, 0.20), seed=41)
    cf = np.clip(cf + cf_micro[:, :, None] * 5.0, 25, 245)
    cf_im = Image.fromarray(np.dstack([cf.astype(np.uint8), np.full((1024, 1024), 255, np.uint8)]), "RGBA")
    h_cf = np.clip(cf.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_conc_facade", "concrete", cf_im, h_cf, np.clip(0.72 - 0.18 * h_cf, 0.38, 0.88), np.clip(0.68 + 0.32 * h_cf, 0.30, 1.0), puddle_mask_field(1024, 1024, seed=404, coverage=0.35), np.zeros_like(h_cf), normal_strength=3.5, has_med_dds=True)

    cf_512 = np.asarray(Image.fromarray(cf.astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)

    def build_concrete_variant(name: str, scale_rgb: tuple[float, float, float], bias: float, seed: int, size: int = 512, rough_base: float = 0.68, puddle_cov: float = 0.30, n_str: float = 2.8):
        if size == 512:
            base = cf_512.copy()
        else:
            base = np.asarray(Image.fromarray(cf.astype(np.uint8)).resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32)
        nz = fbm_noise(size, size, octaves=(1.5, 4.5, 14.0), weights=(0.4, 0.35, 0.25), seed=seed)
        crk = crack_network(size, size, seed=seed + 100, density=1)
        rgb = base * np.array(scale_rgb, dtype=np.float32)[None, None, :] + bias + nz[:, :, None] * 6.5 - crk[:, :, None] * 14.0
        rgb = np.clip(rgb, 18.0, 246.0)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), np.full((size, size), 255, np.uint8)]), "RGBA")
        h = np.clip(rgb.mean(axis=2) / 255.0 - crk * 0.35, 0.0, 1.0)
        r = np.clip(rough_base - (h - 0.5) * 0.18 + nz * 0.04, 0.18, 0.92)
        ao = np.clip(0.74 + 0.26 * h - crk * 0.35, 0.32, 1.0)
        pud = puddle_mask_field(size, size, seed=seed + 200, coverage=puddle_cov)
        register_material(name, "concrete", im, h, r, ao, pud, np.zeros_like(h), normal_strength=n_str)

    # Architectural dark slate-blue concrete accent (std boosted from 0.98 to ~12!)
    build_concrete_variant("ngpd_conc_accent", (0.34, 0.39, 0.46), 4.0, seed=51, rough_base=0.58, puddle_cov=0.25, n_str=2.6)
    build_concrete_variant("ngpd_conc_detention", (1.02, 1.04, 1.03), 14.0, seed=52, rough_base=0.52, puddle_cov=0.20, n_str=2.5)
    build_concrete_variant("ngpd_conc_industrial", (0.82, 0.83, 0.82), 2.0, seed=53, rough_base=0.74, puddle_cov=0.38, n_str=3.4)
    build_concrete_variant("ngpd_conc_interior", (1.06, 1.05, 1.03), 32.0, seed=54, rough_base=0.56, puddle_cov=0.15, n_str=2.2)
    build_concrete_variant("ngpd_conc_smooth", (1.04, 1.03, 1.00), 18.0, seed=55, rough_base=0.54, puddle_cov=0.32, n_str=2.4)
    build_concrete_variant("ngpd_conc_weathered", (0.78, 0.76, 0.72), -4.0, seed=56, rough_base=0.78, puddle_cov=0.45, n_str=3.8)
    build_concrete_variant("ngpd_floor_detention", (0.84, 0.87, 0.89), 6.0, seed=57, rough_base=0.36, puddle_cov=0.25, n_str=2.0)
    build_concrete_variant("ngpd_floor_industrial", (0.68, 0.70, 0.73), 2.0, seed=58, rough_base=0.40, puddle_cov=0.35, n_str=2.4)
    build_concrete_variant("ngpd_floor_polished", (0.91, 0.90, 0.88), 8.0, seed=59, rough_base=0.24, puddle_cov=0.20, n_str=1.8)
    build_concrete_variant("ngpd_painted_white", (1.05, 1.05, 1.04), 48.0, seed=60, size=256, rough_base=0.48, puddle_cov=0.15, n_str=1.8)

    # ------------------------------------------------------------------ 3. STONE PAVING & LOBBY FLOORS
    # 3a. ngpd_floor_lobby (1024x1024)
    lob = src["lobby"].copy()
    lob_nz = fbm_noise(1024, 1024, octaves=(1.5, 6.0, 20.0), weights=(0.35, 0.35, 0.30), seed=61)
    lob = np.clip(lob + lob_nz[:, :, None] * 4.0, 40, 248)
    lob_im = Image.fromarray(np.dstack([lob.astype(np.uint8), np.full((1024, 1024), 255, np.uint8)]), "RGBA")
    h_lob = np.clip(lob.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_floor_lobby", "stone", lob_im, h_lob, np.clip(0.22 - 0.08 * (h_lob - 0.5), 0.12, 0.42), np.clip(0.82 + 0.18 * h_lob, 0.45, 1.0), puddle_mask_field(1024, 1024, seed=601, coverage=0.25), np.zeros_like(h_lob), normal_strength=2.2, has_med_dds=True)

    # 3b. ngpd_floor_corridor (512x512)
    cor = np.asarray(Image.fromarray(lob.astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32) * np.array([0.86, 0.88, 0.91])[None, None, :]
    cor = np.clip(cor + fbm_noise(512, 512, seed=62)[:, :, None] * 4.5, 35, 242)
    cor_im = Image.fromarray(np.dstack([cor.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_cor = np.clip(cor.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_floor_corridor", "stone", cor_im, h_cor, np.clip(0.28 - 0.08 * (h_cor - 0.5), 0.16, 0.48), np.clip(0.80 + 0.20 * h_cor, 0.45, 1.0), puddle_mask_field(512, 512, seed=602, coverage=0.20), np.zeros_like(h_cor), normal_strength=2.2)

    # 3c. ngpd_plaza_stone (512x512 in TXD & DDS for full compatibility, derived from 2K plaza_stone_source)
    plz = np.asarray(Image.fromarray(src["plaza_stone"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)
    plz = np.clip(plz + fbm_noise(512, 512, seed=63)[:, :, None] * 4.5, 30, 245)
    plz_im = Image.fromarray(np.dstack([plz.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_plz = np.clip(plz.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_plaza_stone", "stone", plz_im, h_plz, np.clip(0.46 - 0.16 * (h_plz - 0.5), 0.22, 0.72), np.clip(0.72 + 0.28 * h_plz, 0.35, 1.0), puddle_mask_field(512, 512, seed=603, coverage=0.45), np.zeros_like(h_plz), normal_strength=3.4)

    # 3d. ngpd_sidewalk (512x512 in TXD & DDS, derived from 2K sidewalk_paving_source)
    sw = np.asarray(Image.fromarray(src["sidewalk"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)
    sw = np.clip(sw + fbm_noise(512, 512, seed=64)[:, :, None] * 5.0, 28, 242)
    sw_im = Image.fromarray(np.dstack([sw.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_sw = np.clip(sw.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_sidewalk", "stone", sw_im, h_sw, np.clip(0.58 - 0.16 * (h_sw - 0.5), 0.28, 0.82), np.clip(0.70 + 0.30 * h_sw, 0.32, 1.0), puddle_mask_field(512, 512, seed=604, coverage=0.44), np.zeros_like(h_sw), normal_strength=3.6)

    # ------------------------------------------------------------------ 4. WOOD, BARK & MULCH
    # 4a. ngpd_bark (NEW 512x512 realistic tree bark for rebuilt trees!)
    brk = np.asarray(Image.fromarray(src["bark"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)
    brk_im = Image.fromarray(np.dstack([np.clip(brk, 12, 235).astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_brk = np.clip(brk.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_bark", "wood", brk_im, h_brk, np.clip(0.84 - 0.14 * h_brk, 0.58, 0.95), np.clip(0.45 + 0.55 * h_brk, 0.20, 1.0), np.zeros_like(h_brk), np.zeros_like(h_brk), normal_strength=4.8)

    # 4b. ngpd_mulch (512x512 organic bark chips & rich soil)
    mlc = brk * np.array([0.62, 0.46, 0.33])[None, None, :] + fbm_noise(512, 512, octaves=(1.5, 4.0, 10.0), weights=(0.5, 0.3, 0.2), seed=71)[:, :, None] * 14.0
    mlc = np.clip(mlc, 16, 185)
    mlc_im = Image.fromarray(np.dstack([mlc.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_mlc = np.clip(mlc.mean(axis=2) / 185.0, 0.0, 1.0)
    register_material("ngpd_mulch", "wood", mlc_im, h_mlc, np.clip(0.86 - 0.12 * h_mlc, 0.62, 0.96), np.clip(0.50 + 0.50 * h_mlc, 0.25, 1.0), puddle_mask_field(512, 512, seed=701, coverage=0.25), np.zeros_like(h_mlc), normal_strength=4.2)

    # 4c. ngpd_wood_desk (512x512 walnut wood grain)
    wd = np.asarray(Image.fromarray(src["wood_desk"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)
    wd = np.clip(wd * np.array([0.88, 0.72, 0.56])[None, None, :], 18, 225)
    wd_im = Image.fromarray(np.dstack([wd.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_wd = np.clip(wd.mean(axis=2) / 225.0, 0.0, 1.0)
    register_material("ngpd_wood_desk", "wood", wd_im, h_wd, np.clip(0.34 - 0.08 * h_wd, 0.20, 0.48), np.clip(0.82 + 0.18 * h_wd, 0.55, 1.0), np.zeros_like(h_wd), np.zeros_like(h_wd), normal_strength=2.0)

    # 4d. ngpd_wood_light (512x512 warm ash/maple wood grain)
    wl = np.asarray(Image.fromarray(src["wood_desk"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)
    wl = np.clip(wl * np.array([1.28, 1.12, 0.86])[None, None, :] + 24.0, 45, 242)
    wl_im = Image.fromarray(np.dstack([wl.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_wl = np.clip(wl.mean(axis=2) / 242.0, 0.0, 1.0)
    register_material("ngpd_wood_light", "wood", wl_im, h_wl, np.clip(0.40 - 0.08 * h_wl, 0.25, 0.55), np.clip(0.84 + 0.16 * h_wl, 0.60, 1.0), np.zeros_like(h_wl), np.zeros_like(h_wl), normal_strength=2.0)

    # 4e. ngpd_bookshelf (512x512 preserve shelf layout + wood grain relief)
    bs_orig = np.asarray(orig_imgs["ngpd_bookshelf"], dtype=np.float32)
    bs_nz = fbm_noise(512, 512, octaves=(1.5, 4.0), weights=(0.6, 0.4), seed=72)
    bs_rgb = np.clip(bs_orig[:, :, :3] + bs_nz[:, :, None] * 5.0, 12, 245)
    bs_im = Image.fromarray(np.dstack([bs_rgb.astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_bs = np.clip(bs_rgb.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_bookshelf", "wood", bs_im, h_bs, np.full((512, 512), 0.55, np.float32), np.clip(0.65 + 0.35 * h_bs, 0.35, 1.0), np.zeros_like(h_bs), np.zeros_like(h_bs), normal_strength=2.6)

    # 4f. ngpd_cardboard (256x256 kraft corrugated fiber texture)
    cb_orig = np.asarray(orig_imgs["ngpd_cardboard"], dtype=np.float32)
    cb_nz = fbm_noise(256, 256, octaves=(1.2, 3.5, 10.0), weights=(0.5, 0.3, 0.2), seed=73)
    cb_rgb = np.clip(cb_orig[:, :, :3] + cb_nz[:, :, None] * 7.5, 35, 235)
    cb_im = Image.fromarray(np.dstack([cb_rgb.astype(np.uint8), np.full((256, 256), 255, np.uint8)]), "RGBA")
    h_cb = np.clip(cb_rgb.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_cardboard", "wood", cb_im, h_cb, np.full((256, 256), 0.78, np.float32), np.clip(0.75 + 0.25 * h_cb, 0.45, 1.0), np.zeros_like(h_cb), np.zeros_like(h_cb), normal_strength=2.2)

    # ------------------------------------------------------------------ 5. VEGETATION, GRASS & FABRICS
    # 5a. ngpd_foliage (512x512 in TXD & DDS for full compatibility, rendered at 1024 master then downsampled with Lanczos)
    fol_1024, h_fol_1024, r_fol_1024, ao_fol_1024 = generate_botanical_foliage(1024)
    fol_512 = fol_1024.resize((512, 512), Image.Resampling.LANCZOS)
    h_fol = np.asarray(Image.fromarray((h_fol_1024 * 255).astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), np.float32) / 255.0
    r_fol = np.asarray(Image.fromarray((r_fol_1024 * 255).astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), np.float32) / 255.0
    ao_fol = np.asarray(Image.fromarray((ao_fol_1024 * 255).astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), np.float32) / 255.0
    register_material("ngpd_foliage", "fabric", fol_512, h_fol, r_fol, ao_fol, np.zeros_like(h_fol), np.zeros_like(h_fol), normal_strength=3.0, alpha_fmt="DXT3")

    # 5b. ngpd_grass (512x512 lush urban lawn grass)
    grs = np.asarray(Image.fromarray(src["grass"].astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)
    grs_im = Image.fromarray(np.dstack([np.clip(grs, 14, 225).astype(np.uint8), np.full((512, 512), 255, np.uint8)]), "RGBA")
    h_grs = np.clip(grs.mean(axis=2) / 225.0, 0.0, 1.0)
    register_material("ngpd_grass", "fabric", grs_im, h_grs, np.clip(0.76 - 0.14 * h_grs, 0.45, 0.90), np.clip(0.58 + 0.42 * h_grs, 0.28, 1.0), puddle_mask_field(512, 512, seed=801, coverage=0.30), np.zeros_like(h_grs), normal_strength=3.6)

    # 5c. Fabrics, Carpet, Ceiling, Leather, Plastic, Rubber, Roof Membrane
    def build_fabric_or_polymer(name: str, base_rgb: tuple[float, float, float], size: int, amp: float,rough_val: float, seed: int, grid_step: int = 0, weave_amp: float = 0.0, puddle_cov: float = 0.0):
        yy, xx = np.mgrid[0:size, 0:size]
        nz = fbm_noise(size, size, octaves=(1.2, 3.5, 11.0), weights=(0.5, 0.3, 0.2), seed=seed)
        wv = (np.sin(xx * 1.1) * np.cos(yy * 1.1)).astype(np.float32) * weave_amp if weave_amp > 0 else np.zeros((size, size), np.float32)
        joint = np.zeros((size, size), np.float32)
        if grid_step > 0:
            d = np.minimum(np.minimum(xx % grid_step, grid_step - xx % grid_step), np.minimum(yy % grid_step, grid_step - yy % grid_step))
            joint = np.clip(1.0 - d / 3.0, 0.0, 1.0).astype(np.float32)
        rgb = np.array(base_rgb, np.float32)[None, None, :] + nz[:, :, None] * amp + wv[:, :, None] - joint[:, :, None] * 26.0
        rgb = np.clip(rgb, 10.0, 248.0)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), np.full((size, size), 255, np.uint8)]), "RGBA")
        h = np.clip(0.5 + (nz * 0.18) + (wv * 0.04) - joint * 0.35, 0.0, 1.0)
        r = np.clip(rough_val + nz * 0.04, 0.15, 0.95)
        ao = np.clip(0.86 + nz * 0.08 - joint * 0.35, 0.35, 1.0)
        pud = puddle_mask_field(size, size, seed=seed + 300, coverage=puddle_cov) if puddle_cov > 0 else np.zeros_like(h)
        register_material(name, "fabric", im, h, r, ao, pud, np.zeros_like(h), normal_strength=2.5)

    build_fabric_or_polymer("ngpd_ceiling_tile", (222, 223, 221), 512, amp=7.5, rough_val=0.84, seed=81, grid_step=128)
    build_fabric_or_polymer("ngpd_fabric_seat", (38, 54, 86), 512, amp=6.5, rough_val=0.82, seed=82, weave_amp=4.5)
    build_fabric_or_polymer("ngpd_floor_office", (64, 70, 82), 512, amp=8.0, rough_val=0.78, seed=83, grid_step=128, weave_amp=3.5)
    build_fabric_or_polymer("ngpd_leather", (34, 32, 36), 256, amp=5.5, rough_val=0.42, seed=84)
    build_fabric_or_polymer("ngpd_mattress", (62, 74, 88), 256, amp=6.0, rough_val=0.74, seed=85, weave_amp=3.0)
    build_fabric_or_polymer("ngpd_plastic", (196, 198, 201), 256, amp=6.0, rough_val=0.38, seed=86)
    build_fabric_or_polymer("ngpd_plastic_dark", (34, 36, 40), 256, amp=5.0, rough_val=0.36, seed=87)
    build_fabric_or_polymer("ngpd_roof_membrane", (172, 175, 178), 512, amp=11.0, rough_val=0.66, seed=88, grid_step=256, puddle_cov=0.52)
    build_fabric_or_polymer("ngpd_rubber", (26, 26, 28), 256, amp=4.8, rough_val=0.72, seed=89)

    # ------------------------------------------------------------------ 6. ARCHITECTURAL GLASS
    def build_glass_material(name: str, base_rgb: tuple[float, float, float], alpha_val: int, size: int, seed: int):
        yy, xx = np.mgrid[0:size, 0:size]
        nz = fbm_noise(size, size, octaves=(4.0, 14.0), weights=(0.6, 0.4), seed=seed)
        edge = np.minimum(np.minimum(xx, size - 1 - xx), np.minimum(yy, size - 1 - yy)).astype(np.float32)
        bevel = np.clip(1.0 - edge / 10.0, 0.0, 1.0)
        rgb = np.array(base_rgb, np.float32)[None, None, :] + nz[:, :, None] * 4.5 - bevel[:, :, None] * 14.0
        rgb = np.clip(rgb, 15.0, 245.0)
        a_arr = np.clip(alpha_val + bevel * 38.0 + nz * 4.0, 60.0, 245.0).astype(np.uint8)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), a_arr]), "RGBA")
        h = np.clip(0.5 - bevel * 0.25 + nz * 0.04, 0.0, 1.0)
        r = np.clip(0.06 + bevel * 0.12, 0.03, 0.25)
        ao = np.clip(0.95 - bevel * 0.25, 0.60, 1.0)
        register_material(name, "glass", im, h, r, ao, np.zeros_like(h), np.zeros_like(h), normal_strength=1.4, alpha_fmt="DXT3")

    build_glass_material("ngpd_glass_facade", (48, 68, 86), 148, 256, seed=91)
    build_glass_material("ngpd_glass_interior", (192, 208, 214), 118, 256, seed=92)

    # ------------------------------------------------------------------ 7. METALS & CLADDING
    mp = src["metal_panel"].copy()
    mp_nz = fbm_noise(1024, 1024, octaves=(1.5, 6.0, 22.0), weights=(0.35, 0.35, 0.30), seed=101)
    mp = np.clip(mp * np.array([0.85, 0.90, 0.98])[None, None, :] + mp_nz[:, :, None] * 4.5, 18, 230)
    mp_im = Image.fromarray(np.dstack([mp.astype(np.uint8), np.full((1024, 1024), 255, np.uint8)]), "RGBA")
    h_mp = np.clip(mp.mean(axis=2) / 255.0, 0.0, 1.0)
    register_material("ngpd_metal_panel", "metal", mp_im, h_mp, np.clip(0.32 - 0.08 * h_mp, 0.16, 0.52), np.clip(0.78 + 0.22 * h_mp, 0.40, 1.0), np.zeros_like(h_mp), np.full_like(h_mp, 0.65), normal_strength=2.8, has_med_dds=True)

    mp_512 = np.asarray(Image.fromarray(mp.astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS), dtype=np.float32)

    def build_metal_variant(name: str, base_rgb: tuple[float, float, float], size: int, rough_val: float, metal_val: float, seed: int, brush_amp: float = 5.5):
        yy, xx = np.mgrid[0:size, 0:size]
        nz = fbm_noise(size, size, octaves=(1.0, 4.0, 16.0), weights=(0.45, 0.35, 0.20), seed=seed)
        # Anisotropic horizontal brushed metal micro-grooves
        brush = gaussian_filter(np.random.default_rng(seed + 50).normal(size=(size, size)).astype(np.float32), sigma=(0.7, 9.0), mode="wrap")
        brush /= max(1e-6, float(brush.std()))
        rgb = np.array(base_rgb, np.float32)[None, None, :] + nz[:, :, None] * 5.0 + brush[:, :, None] * brush_amp
        rgb = np.clip(rgb, 14.0, 245.0)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), np.full((size, size), 255, np.uint8)]), "RGBA")
        h = np.clip(0.5 + brush * 0.15 + nz * 0.10, 0.0, 1.0)
        r = np.clip(rough_val + nz * 0.04 - brush * 0.03, 0.12, 0.78)
        ao = np.clip(0.88 + 0.12 * h, 0.55, 1.0)
        m = np.full_like(h, metal_val)
        register_material(name, "metal", im, h, r, ao, np.zeros_like(h), m, normal_strength=2.4)

    build_metal_variant("ngpd_metal_alu", (176, 180, 185), 512, rough_val=0.26, metal_val=0.92, seed=111, brush_amp=7.0)
    build_metal_variant("ngpd_metal_bars", (92, 104, 116), 256, rough_val=0.36, metal_val=0.78, seed=112, brush_amp=5.5)
    build_metal_variant("ngpd_metal_blue", (36, 62, 106), 512, rough_val=0.34, metal_val=0.35, seed=113, brush_amp=4.8)
    build_metal_variant("ngpd_metal_frame", (32, 34, 39), 256, rough_val=0.32, metal_val=0.68, seed=114, brush_amp=5.0)
    build_metal_variant("ngpd_metal_hardware", (62, 64, 68), 256, rough_val=0.28, metal_val=0.95, seed=115, brush_amp=6.0)
    build_metal_variant("ngpd_metal_matte", (70, 73, 78), 512, rough_val=0.46, metal_val=0.65, seed=116, brush_amp=5.2)
    build_metal_variant("ngpd_metal_painted", (149, 156, 162), 512, rough_val=0.38, metal_val=0.25, seed=117, brush_amp=4.5)

    # Preserve structured UV metal textures (drain_grate, fence, locker, server_rack) with enhanced normal/surface maps
    for mname, r_val, met_val, p_val, a_fmt in [
        ("ngpd_drain_grate", 0.38, 0.88, 0.85, None),
        ("ngpd_fence", 0.42, 0.75, 0.0, "DXT3"),
        ("ngpd_locker", 0.36, 0.45, 0.0, None),
        ("ngpd_server_rack", 0.34, 0.55, 0.65, None),
    ]:
        orig_im = orig_imgs[mname]
        w, h_sz = orig_im.size
        arr = np.asarray(orig_im, dtype=np.float32)
        nz = fbm_noise(h_sz, w, octaves=(1.2, 4.0), weights=(0.6, 0.4), seed=120 + len(mname))
        rgb = np.clip(arr[:, :, :3] + nz[:, :, None] * 5.5, 8.0, 248.0)
        a_ch = arr[:, :, 3].astype(np.uint8) if a_fmt else np.full((h_sz, w), 255, np.uint8)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), a_ch]), "RGBA")
        h_map = np.clip(rgb.mean(axis=2) / 255.0, 0.0, 1.0)
        r_map = np.clip(r_val + (0.5 - h_map) * 0.15, 0.18, 0.82)
        ao_map = np.clip(0.45 + 0.55 * h_map, 0.20, 1.0)
        mask_map = np.full_like(h_map, p_val)
        met_map = np.full_like(h_map, met_val)
        register_material(mname, "metal", im, h_map, r_map, ao_map, mask_map, met_map, normal_strength=3.2, alpha_fmt=a_fmt)

    # ------------------------------------------------------------------ 8. DECALS, ROAD PAINT & EMISSIVE DISPLAYS
    # Road markings (paint_white, paint_yellow, paint_blue): weathered thermoplastic road paint with glass-bead micro-grain
    for pname, base_col, seed in [
        ("ngpd_paint_white", (222, 221, 215), 131),
        ("ngpd_paint_yellow", (218, 172, 44), 132),
        ("ngpd_paint_blue", (44, 92, 188), 133),
    ]:
        nz = fbm_noise(256, 256, octaves=(1.0, 3.0, 10.0), weights=(0.5, 0.3, 0.2), seed=seed)
        wear = np.clip(fbm_noise(256, 256, octaves=(8.0, 20.0), weights=(0.6, 0.4), seed=seed + 20) - 0.55, 0.0, 1.0)
        rgb = np.array(base_col, np.float32)[None, None, :] * (1.0 - 0.28 * wear[:, :, None]) + nz[:, :, None] * 9.0
        rgb = np.clip(rgb, 24.0, 248.0)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), np.full((256, 256), 255, np.uint8)]), "RGBA")
        h_map = np.clip(0.65 - wear * 0.35 + nz * 0.10, 0.0, 1.0)
        r_map = np.clip(0.42 + wear * 0.28, 0.25, 0.80)
        ao_map = np.clip(0.82 - wear * 0.22, 0.45, 1.0)
        pud_map = puddle_mask_field(256, 256, seed=seed + 50, coverage=0.40)
        register_material(pname, "decals", im, h_map, r_map, ao_map, pud_map, np.zeros_like(h_map), normal_strength=2.8)

    # Preserve & sharpen structured decals / screens / light panels
    for dname, r_val, met_val, em_mask_scale, has_med in [
        ("ngpd_badge", 0.26, 0.65, 0.0, False),
        ("ngpd_floor_emblem", 0.20, 0.25, 0.0, False),
        ("ngpd_light_panel", 0.18, 0.0, 1.0, False),
        ("ngpd_light_warm", 0.18, 0.0, 1.0, False),
        ("ngpd_screen_cctv", 0.15, 0.0, 0.92, False),
        ("ngpd_screen_pc", 0.15, 0.0, 0.90, False),
        ("ngpd_sign_atlas", 0.30, 0.15, 0.45, False),
        ("ngpd_sign_police", 0.25, 0.35, 0.85, True),
    ]:
        orig_im = orig_imgs[dname]
        w, h_sz = orig_im.size
        arr = np.asarray(orig_im, dtype=np.float32)
        nz = fbm_noise(h_sz, w, octaves=(1.5, 5.0), weights=(0.6, 0.4), seed=140 + len(dname))
        rgb = np.clip(arr[:, :, :3] + nz[:, :, None] * 3.2, 4.0, 252.0)
        im = Image.fromarray(np.dstack([rgb.astype(np.uint8), np.full((h_sz, w), 255, np.uint8)]), "RGBA")
        lum = rgb.mean(axis=2) / 255.0
        h_map = np.clip(lum * 0.85 + nz * 0.05, 0.0, 1.0)
        r_map = np.clip(r_val + (1.0 - lum) * 0.12, 0.10, 0.65)
        ao_map = np.clip(0.75 + 0.25 * lum, 0.45, 1.0)
        mask_map = np.clip(lum * em_mask_scale, 0.0, 1.0) if em_mask_scale > 0 else np.zeros_like(lum)
        met_map = np.clip(lum * met_val, 0.0, 1.0)
        register_material(dname, "decals", im, h_map, r_map, ao_map, mask_map, met_map, normal_strength=2.2, has_med_dds=has_med)

    # Extra DDS-only decals referenced in meta.xml (ngpd_board_case, ngpd_floor_accent)
    for xname, xsz in [("ngpd_board_case", 512), ("ngpd_floor_accent", 256)]:
        nz = fbm_noise(xsz, xsz, seed=160 + xsz)
        h_map = np.clip(0.5 + nz * 0.15, 0.0, 1.0)
        r_map = np.full((xsz, xsz), 0.35, np.float32)
        ao_map = np.full((xsz, xsz), 0.90, np.float32)
        im_dummy = Image.new("RGBA", (xsz, xsz), (128, 128, 128, 255))
        register_material(xname, "decals", im_dummy, h_map, r_map, ao_map, np.zeros_like(h_map), np.zeros_like(h_map), normal_strength=1.8, in_txd=False)

    # ------------------------------------------------------------------ 9. WRITE TXD ARCHIVES (HIGH / MED / LOW)
    sorted_names = sorted(high_albedo.keys())
    txd_summary = {}
    for tier, scale_div, max_dim in [("high", 1, 1024), ("med", 2, 512), ("low", 4, 256)]:
        t_doc = txd.txd()
        t_doc.device_id = txd.DeviceType.DEVICE_D3D9
        natives = []
        for tname in sorted_names:
            im = high_albedo[tname]
            if tier == "high":
                tw, th = im.width, im.height
            elif tier == "med":
                tw = min(max_dim, im.width)
                th = min(max_dim, im.height)
                if im.width == 1024 and im.height == 256:
                    tw, th = 512, 128
            else:
                tw = min(max_dim, max(128, im.width // 2))
                th = min(max_dim, max(128, im.height // 2))
                if im.width >= 256 and im.height >= 256:
                    tw, th = 256, 256
                elif im.width == 1024 and im.height == 256:
                    tw, th = 256, 64
            tim = im if (im.width == tw and im.height == th) else im.resize((tw, th), Image.Resampling.LANCZOS)
            natives.append(make_native_txd_entry(tname, tim, alpha_format[tname]))
        t_doc.native_textures = natives
        out_p = OUT_TEX_DIR / f"ngpd_world_{tier}.txd"
        t_doc.write_file(str(out_p), RW_VERSION)
        txd_summary[tier] = {
            "path": out_p.relative_to(ROOT).as_posix(),
            "bytes": out_p.stat().st_size,
            "texture_count": len(natives),
        }

    # ------------------------------------------------------------------ 10. VISUAL BEFORE / AFTER COMPARISON SHEET
    pairs = [
        ("ngpd_asph_parking", "Asphalt Parking"),
        ("ngpd_asph_road", "Asphalt Road"),
        ("ngpd_foliage", "Botanical Foliage"),
        ("ngpd_conc_facade", "Concrete Facade"),
        ("ngpd_sidewalk", "Urban Sidewalk"),
        ("ngpd_plaza_stone", "Plaza Granite"),
    ]
    cell_w, cell_h = 256, 256
    sheet = Image.new("RGB", (cell_w * len(pairs), cell_h * 2 + 48), (18, 22, 28))
    sdraw = ImageDraw.Draw(sheet)
    for idx, (tname, label) in enumerate(pairs):
        ox = idx * cell_w
        before_im = orig_imgs[tname].convert("RGB").resize((cell_w - 8, cell_h - 8), Image.Resampling.LANCZOS)
        after_im = high_albedo[tname].convert("RGB").resize((cell_w - 8, cell_h - 8), Image.Resampling.LANCZOS)
        sheet.paste(before_im, (ox + 4, 24))
        sheet.paste(after_im, (ox + 4, cell_h + 44))
        sdraw.text((ox + 8, 6), f"BEFORE: {label}", fill=(255, 140, 120))
        sdraw.text((ox + 8, cell_h + 26), f"AFTER:  {label}", fill=(140, 255, 160))
    comp_path = PREVIEW_DIR / "before_after_textures.png"
    sheet.save(comp_path)

    manifest = {
        "txd_archives": txd_summary,
        "total_materials_in_txd": len(sorted_names),
        "total_dds_pairs": len(dds_records),
        "comparison_sheet": comp_path.relative_to(ROOT).as_posix(),
    }
    (ROOT / "assets" / "TEXTURE_BUILD_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    info = build_all_textures()
    print(json.dumps(info, indent=2))

