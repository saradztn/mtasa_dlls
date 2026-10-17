#!/usr/bin/env python3
"""
NextGenPoliceDepartment - 3D Model, Vegetation & Prelight Upgrader (tools/rebuild_models.py)

Upgrades the 65 RenderWare DFF models and 65 COL3 collision files:
  1. Replaces all 41 primitive exterior trees (14-tri concrete cylinders + 18-tri flat card canopies)
     with curved, root-flared, multi-branching botanical 3D trees (`ngpd_bark` trunks/boughs in
     `ngpd_site_{00,01,10,20}.dff` + layered cambered `ngpd_foliage` crowns in `ngpd_site_{00a,01a,10a,20a}.dff`).
  2. Replaces all 27 primitive 12-tri indoor plant cards in `ngpd_f*a.dff` with multi-frond botanical rosettes.
  3. Upgrades exterior vertex prelighting (`prelit_colors`) with golden-hour directional warmth,
     sky hemisphere fill, and ground-contact ambient occlusion.
  4. Recomputes DFF bounding spheres and COL3 bounding volumes so GTA:SA frustum culling never clips canopies.
"""
from __future__ import annotations
import json
import math
import re
import shutil
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "vendor" / "DragonFF"))
sys.path.insert(0, str(ROOT / "source" / "vegetation"))
from gtaLib import col as gcol, dff as gdff
from tree_generator import generate_indoor_planter_plant, generate_tree

RW_VERSION = 0x36003
ORIG_RES = Path("/tmp/original_resource")
if not ORIG_RES.exists():
    ORIG_RES = ROOT / "backup" / "original_resource"

OUT_MODELS = ROOT / "models"
OUT_COLS = ROOT / "collisions"


def parse_model_positions(data_lua_path: Path) -> dict[str, np.ndarray]:
    txt = data_lua_path.read_text()
    pos_map = {}
    for m in re.finditer(
        r'name\s*=\s*"([^"]+)",\s*dff\s*=\s*"([^"]+)",\s*col\s*=\s*"([^"]+)",\s*alpha\s*=\s*(true|false),\s*pos\s*=\s*\{([^\}]+)\}',
        txt,
    ):
        name, _, _, _, pos_s = m.groups()
        pos_map[name] = np.array([float(x) for x in pos_s.split(",")], dtype=np.float64)
    return pos_map


def compact_geometry(
    verts: list[tuple[float, float, float]],
    norms: list[tuple[float, float, float]],
    uvs: list[tuple[float, float]],
    colors: list[tuple[int, int, int, int]],
    tris: list[tuple[int, int, int, int]],
    mat_names: list[str],
) -> gdff.Geometry:
    """Compact unreferenced vertices and materials and construct a valid RenderWare DFF Geometry."""
    used_verts = sorted({v for a, b, c, _ in tris for v in (a, b, c)})
    v_remap = {old: new for new, old in enumerate(used_verts)}
    new_verts = [verts[i] for i in used_verts]
    new_norms = [norms[i] for i in used_verts]
    new_uvs = [uvs[i] for i in used_verts]
    new_colors = [colors[i] for i in used_verts]

    used_mats = sorted({m for _, _, _, m in tris})
    m_remap = {old: new for new, old in enumerate(used_mats)}
    new_mat_names = [mat_names[m] for m in used_mats]
    new_tris = [(v_remap[a], v_remap[b], v_remap[c], m_remap[m]) for a, b, c, m in tris if a != b and b != c and a != c]

    assert 0 < len(new_verts) < 65535, f"Vertex count out of DFF 16-bit range: {len(new_verts)}"
    assert 0 < len(new_tris) < 65535, f"Triangle count out of DFF 16-bit range: {len(new_tris)}"

    g = gdff.Geometry()
    g.export_flags["light"] = False
    g.vertices = [gdff.Vector(*p) for p in new_verts]
    g.normals = [gdff.Vector(*n) for n in new_norms]
    g.uv_layers = [[gdff.TexCoords(*uv) for uv in new_uvs]]
    g.prelit_colors = [gdff.RGBA(*c) for c in new_colors]
    # Note: DragonFF Triangle constructor order is (b, a, material, c) where a=t.a, b=t.b, c=t.c
    g.triangles = [gdff.Triangle(b, a, m, c) for a, b, c, m in new_tris]

    vv = np.asarray(new_verts, dtype=np.float64)
    lo = vv.min(axis=0)
    hi = vv.max(axis=0)
    center = (lo + hi) * 0.5
    radius = float(np.linalg.norm(vv - center, axis=1).max()) + 0.05
    g.bounding_sphere = gdff.Sphere(float(center[0]), float(center[1]), float(center[2]), radius)
    g.surface_properties = gdff.GeomSurfPro(0.65, 0.0, 0.70)

    for tname in new_mat_names:
        mat = gdff.Material()
        mat.color = gdff.RGBA(255, 255, 255, 255)
        mat.surface_properties = gdff.GeomSurfPro(0.65, 0.0, 0.70)
        tex = gdff.Texture()
        tex.name = tname
        tex.filters = 6
        tex.uv_addressing = 0x11
        mat.textures = [tex]
        g.materials.append(mat)

    return g


def extract_geometry_arrays(g: gdff.Geometry):
    verts = [(float(v.x), float(v.y), float(v.z)) for v in g.vertices]
    norms = [(float(n.x), float(n.y), float(n.z)) for n in g.normals]
    uvs = [(float(u.u), float(u.v)) for u in g.uv_layers[0]]
    colors = [(int(c.r), int(c.g), int(c.b), int(c.a)) for c in g.prelit_colors]
    tris = [(int(t.a), int(t.b), int(t.c), int(t.material)) for t in g.triangles]
    mat_names = [m.textures[0].name for m in g.materials]
    return verts, norms, uvs, colors, tris, mat_names


def enhance_exterior_prelight(
    verts: list[tuple[float, float, float]],
    norms: list[tuple[float, float, float]],
    colors: list[tuple[int, int, int, int]],
    world_offset: np.ndarray,
    is_interior: bool,
) -> list[tuple[int, int, int, int]]:
    """
    Enhance vertex prelight on exterior meshes with:
      - Golden-hour directional warmth on sun-facing surfaces
      - Cool sky-hemisphere fill on upward/shadowed faces
      - Ground-contact ambient occlusion near Z=0 on vertical walls
    """
    if is_interior or not verts:
        return colors
    vv = np.asarray(verts, dtype=np.float64) + world_offset[None, :]
    nn = np.asarray(norms, dtype=np.float64)
    cc = np.asarray(colors, dtype=np.float64)

    sun_dir = np.array([0.48, -0.64, 0.60], dtype=np.float64)
    sun_dir /= np.linalg.norm(sun_dir)
    ndl = np.clip(nn @ sun_dir, 0.0, 1.0)
    sky_up = np.clip(nn[:, 2] * 0.5 + 0.5, 0.0, 1.0)

    # Subtle contact AO where vertical surfaces meet the ground plane (z in 0..0.85m)
    vert_wall = np.abs(nn[:, 2]) < 0.35
    ground_prox = np.clip(1.0 - np.abs(vv[:, 2]) / 0.85, 0.0, 1.0)
    contact_ao = np.where(vert_wall, 1.0 - 0.14 * (ground_prox ** 1.5), 1.0)

    # Golden-hour directional tint + sky balance (subtle so dynamic shader still controls time of day)
    r_gain = (0.94 + 0.14 * ndl + 0.02 * sky_up) * contact_ao
    g_gain = (0.94 + 0.09 * ndl + 0.03 * sky_up) * contact_ao
    b_gain = (0.93 + 0.03 * ndl + 0.06 * sky_up) * contact_ao

    out_r = np.clip(cc[:, 0] * r_gain, 24.0, 255.0).astype(int)
    out_g = np.clip(cc[:, 1] * g_gain, 24.0, 255.0).astype(int)
    out_b = np.clip(cc[:, 2] * b_gain, 24.0, 255.0).astype(int)
    out_a = cc[:, 3].astype(int)
    return [(int(r), int(g), int(b), int(a)) for r, g, b, a in zip(out_r, out_g, out_b, out_a)]


def update_col_bounds(col_path: Path, dff_geom: gdff.Geometry) -> None:
    """Ensure the COL3 bounding box/sphere covers the visual DFF geometry bounds."""
    c_doc = gcol.coll()
    c_doc.load_file(str(col_path))
    m = c_doc.models[0]
    vv = np.array([(v.x, v.y, v.z) for v in dff_geom.vertices], dtype=np.float64)
    lo = np.minimum(np.array(m.bounds.min, dtype=np.float64), vv.min(axis=0))
    hi = np.maximum(np.array(m.bounds.max, dtype=np.float64), vv.max(axis=0))
    center = (lo + hi) * 0.5
    radius = float(np.linalg.norm(hi - center)) + 0.10
    m.bounds = gcol.TBounds(tuple(float(x) for x in lo), tuple(float(x) for x in hi), tuple(float(x) for x in center), radius)
    gcol.Sections.init_sections(3)
    c_doc.write_file(str(col_path))


def rebuild_all_models() -> dict:
    OUT_MODELS.mkdir(parents=True, exist_ok=True)
    OUT_COLS.mkdir(parents=True, exist_ok=True)

    pos_map = parse_model_positions(ORIG_RES / "shared" / "ngpd_data.lua")
    data_txt = (ORIG_RES / "shared" / "ngpd_data.lua").read_text()
    interior_map = {}
    for m in re.finditer(r'name\s*=\s*"([^"]+)".*?interior\s*=\s*(true|false)', data_txt, re.S):
        interior_map[m.group(1)] = m.group(2) == "true"

    # First copy all original DFF and COL files to output folders
    for p in sorted((ORIG_RES / "models").glob("*.dff")):
        shutil.copy2(p, OUT_MODELS / p.name)
    for p in sorted((ORIG_RES / "collisions").glob("*.col")):
        shutil.copy2(p, OUT_COLS / p.name)

    site_pairs = [
        ("ngpd_site_00", "ngpd_site_00a"),
        ("ngpd_site_01", "ngpd_site_01a"),
        ("ngpd_site_10", "ngpd_site_10a"),
        ("ngpd_site_20", "ngpd_site_20a"),
    ]

    tree_stats = {"exterior_trees_rebuilt": 0, "indoor_planters_rebuilt": 0, "site_pairs": {}}

    # 1. Rebuild all 41 exterior trees across the 4 site chunks
    for pair_idx, (base_name, alpha_name) in enumerate(site_pairs):
        d_base = gdff.dff()
        d_base.load_file(str(ORIG_RES / "models" / f"{base_name}.dff"))
        g_base = d_base.clumps[0].geometry_list[0]
        bv, bn, buv, bc, bt, bmats = extract_geometry_arrays(g_base)
        b_pos = pos_map[base_name]

        d_alpha = gdff.dff()
        d_alpha.load_file(str(ORIG_RES / "models" / f"{alpha_name}.dff"))
        g_alpha = d_alpha.clumps[0].geometry_list[0]
        av, an, auv, ac, at, amats = extract_geometry_arrays(g_alpha)
        a_pos = pos_map[alpha_name]

        # Identify tree trunks in base_name (ngpd_conc_weathered with world zmax > 0.50)
        b_world = np.asarray(bv, dtype=np.float64) + b_pos[None, :]
        cw_idx = bmats.index("ngpd_conc_weathered") if "ngpd_conc_weathered" in bmats else -1
        ml_idx = bmats.index("ngpd_mulch") if "ngpd_mulch" in bmats else -1

        trunk_tri_indices = []
        keep_bt = []
        for ti, (a, b, c, m) in enumerate(bt):
            zmax = max(b_world[a, 2], b_world[b, 2], b_world[c, 2])
            if m == cw_idx and zmax > 0.50:
                trunk_tri_indices.append(ti)
            elif m == ml_idx and zmax > 0.50:
                # Old mulch-textured crown branches in ngpd_site_10
                continue
            else:
                keep_bt.append((a, b, c, m))

        # Cluster trunk_tri_indices in world XY to get exact root centers (cx, cy, z_base, height)
        t_centers = np.array([(b_world[bt[i][0]] + b_world[bt[i][1]] + b_world[bt[i][2]]) / 3.0 for i in trunk_tri_indices])
        used = np.zeros(len(trunk_tri_indices), dtype=bool)
        trees_to_build = []
        for i in range(len(trunk_tri_indices)):
            if used[i]:
                continue
            dist = np.linalg.norm(t_centers[:, :2] - t_centers[i, :2], axis=1)
            mask = dist < 2.2
            used[mask] = True
            c_tris = [bt[trunk_tri_indices[j]] for j in np.where(mask)[0]]
            c_v = b_world[[v for a, b, c, _ in c_tris for v in (a, b, c)]]
            cx = float(np.median(c_v[:, 0]))
            cy = float(np.median(c_v[:, 1]))
            z_base = float(c_v[:, 2].min())
            z_top = float(c_v[:, 2].max())
            is_plaza = len(c_tris) > 30
            trees_to_build.append((cx, cy, z_base, z_top, "plaza" if is_plaza else "street"))

        # Remove old ngpd_foliage triangles from alpha_name while keeping fence/glass
        fol_idx = amats.index("ngpd_foliage")
        keep_at = [(a, b, c, m) for (a, b, c, m) in at if m != fol_idx]

        if "ngpd_bark" not in bmats:
            bmats.append("ngpd_bark")
        bark_mat_id = bmats.index("ngpd_bark")

        # Generate new 3D botanical trees and append to base (bark) and alpha (foliage)
        for t_idx, (cx, cy, z_base, z_top, style) in enumerate(trees_to_build):
            seed = 10000 + pair_idx * 500 + t_idx * 17
            if style == "plaza":
                tot_h = max(7.2, (z_top - z_base) * 1.08)
                c_rad = 3.1
            else:
                tot_h = 6.2
                c_rad = 2.35
            tree_data = generate_tree(cx, cy, z_base, total_height=tot_h, crown_radius=c_rad, seed=seed, style=style)

            # Append bark in base local coordinates (world - b_pos)
            b_ofs = len(bv)
            for vx, vy, vz in tree_data["bark"]["verts"]:
                bv.append((vx - float(b_pos[0]), vy - float(b_pos[1]), vz - float(b_pos[2])))
            bn.extend(tree_data["bark"]["norms"])
            buv.extend(tree_data["bark"]["uvs"])
            bc.extend(tree_data["bark"]["colors"])
            for ta, tb_, tc in tree_data["bark"]["tris"]:
                keep_bt.append((ta + b_ofs, tb_ + b_ofs, tc + b_ofs, bark_mat_id))

            # Append foliage in alpha local coordinates (world - a_pos)
            a_ofs = len(av)
            for vx, vy, vz in tree_data["foliage"]["verts"]:
                av.append((vx - float(a_pos[0]), vy - float(a_pos[1]), vz - float(a_pos[2])))
            an.extend(tree_data["foliage"]["norms"])
            auv.extend(tree_data["foliage"]["uvs"])
            ac.extend(tree_data["foliage"]["colors"])
            for ta, tb_, tc in tree_data["foliage"]["tris"]:
                keep_at.append((ta + a_ofs, tb_ + a_ofs, tc + a_ofs, fol_idx))

        bc = enhance_exterior_prelight(bv, bn, bc, b_pos, is_interior=False)
        new_g_base = compact_geometry(bv, bn, buv, bc, keep_bt, bmats)
        d_base.clumps[0].geometry_list[0] = new_g_base
        d_base.write_file(str(OUT_MODELS / f"{base_name}.dff"), RW_VERSION)
        update_col_bounds(OUT_COLS / f"{base_name}.col", new_g_base)

        new_g_alpha = compact_geometry(av, an, auv, ac, keep_at, amats)
        d_alpha.clumps[0].geometry_list[0] = new_g_alpha
        d_alpha.write_file(str(OUT_MODELS / f"{alpha_name}.dff"), RW_VERSION)
        update_col_bounds(OUT_COLS / f"{alpha_name}.col", new_g_alpha)

        tree_stats["exterior_trees_rebuilt"] += len(trees_to_build)
        tree_stats["site_pairs"][base_name] = {
            "trees": len(trees_to_build),
            "base_verts": len(new_g_base.vertices),
            "base_tris": len(new_g_base.triangles),
            "alpha_verts": len(new_g_alpha.vertices),
            "alpha_tris": len(new_g_alpha.triangles),
        }

    # 2. Rebuild indoor planter vegetation in all 8 interior alpha models (ngpd_f*a.dff)
    indoor_alpha_models = [
        "ngpd_f0ca", "ngpd_f0wa", "ngpd_f1ca", "ngpd_f1ea",
        "ngpd_f1wa", "ngpd_f2ca", "ngpd_f2ea", "ngpd_f2wa",
    ]
    for m_idx, mname in enumerate(indoor_alpha_models):
        d_in = gdff.dff()
        d_in.load_file(str(ORIG_RES / "models" / f"{mname}.dff"))
        g_in = d_in.clumps[0].geometry_list[0]
        iv, inorm, iuv, ic, it, imats = extract_geometry_arrays(g_in)
        if "ngpd_foliage" not in imats:
            continue
        f_idx = imats.index("ngpd_foliage")
        f_tris = [(a, b, c) for a, b, c, m in it if m == f_idx]
        keep_it = [(a, b, c, m) for a, b, c, m in it if m != f_idx]
        iv_arr = np.asarray(iv, dtype=np.float64)
        f_centers = np.array([(iv_arr[a] + iv_arr[b] + iv_arr[c]) / 3.0 for a, b, c in f_tris])
        used = np.zeros(len(f_tris), dtype=bool)
        for i in range(len(f_tris)):
            if used[i]:
                continue
            mask = np.linalg.norm(f_centers[:, :2] - f_centers[i, :2], axis=1) < 1.8
            used[mask] = True
            c_v = iv_arr[[v for j in np.where(mask)[0] for v in f_tris[j]]]
            cx = float(c_v[:, 0].mean())
            cy = float(c_v[:, 1].mean())
            z0 = float(c_v[:, 2].min())
            h_pl = float(max(1.2, c_v[:, 2].max() - z0))
            plant = generate_indoor_planter_plant(cx, cy, z0, height=h_pl, radius=0.48, seed=7000 + m_idx * 100 + i)
            ofs = len(iv)
            iv.extend(plant["verts"])
            inorm.extend(plant["norms"])
            iuv.extend(plant["uvs"])
            ic.extend(plant["colors"])
            for ta, tb_, tc in plant["tris"]:
                keep_it.append((ta + ofs, tb_ + ofs, tc + ofs, f_idx))
            tree_stats["indoor_planters_rebuilt"] += 1

        new_g_in = compact_geometry(iv, inorm, iuv, ic, keep_it, imats)
        d_in.clumps[0].geometry_list[0] = new_g_in
        d_in.write_file(str(OUT_MODELS / f"{mname}.dff"), RW_VERSION)
        update_col_bounds(OUT_COLS / f"{mname}.col", new_g_in)

    # 3. Enhance exterior prelight on remaining exterior models (ngpd_canopy, ngpd_crown, ngpd_roofx, ngpd_site_11, ngpd_site_21)
    for ext_name in ["ngpd_canopy", "ngpd_crown", "ngpd_roofx", "ngpd_site_11", "ngpd_site_21"]:
        d_ext = gdff.dff()
        d_ext.load_file(str(OUT_MODELS / f"{ext_name}.dff"))
        g_ext = d_ext.clumps[0].geometry_list[0]
        ev, en, euv, ec, et, emats = extract_geometry_arrays(g_ext)
        ec = enhance_exterior_prelight(ev, en, ec, pos_map.get(ext_name, np.zeros(3)), is_interior=False)
        d_ext.clumps[0].geometry_list[0] = compact_geometry(ev, en, euv, ec, et, emats)
        d_ext.write_file(str(OUT_MODELS / f"{ext_name}.dff"), RW_VERSION)

    # 4. Collect final per-model texture list for shared/ngpd_materials.lua
    model_textures = {}
    for p in sorted(OUT_MODELS.glob("*.dff")):
        d = gdff.dff()
        d.load_file(str(p))
        g = d.clumps[0].geometry_list[0]
        model_textures[p.stem] = sorted({m.textures[0].name for m in g.materials if m.textures})

    tree_stats["model_textures_count"] = len(model_textures)
    (ROOT / "assets" / "MODEL_BUILD_MANIFEST.json").write_text(json.dumps({"stats": tree_stats, "modelTextures": model_textures}, indent=2))
    return tree_stats


if __name__ == "__main__":
    stats = rebuild_all_models()
    print(json.dumps(stats, indent=2))
