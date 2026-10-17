#!/usr/bin/env python3
"""
NextGenPoliceDepartment - Reusable Botanical 3D Vegetation Generator (source/vegetation/tree_generator.py)

Generates natural, non-repetitive 3D trees and indoor architectural plants with:
  * Root-flared, organically curved S-spline trunks (`ngpd_bark`)
  * Irregular primary boughs and secondary forks with realistic radius tapering
  * Multi-layered dome/frond botanical leaf clusters (`ngpd_foliage`)
  * Baked 3D canopy ambient occlusion, trunk contact shadows, and golden-hour self-shadowing
"""
from __future__ import annotations
import math
import numpy as np


def _orthonormal_frame(tangent: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = tangent / max(1e-8, float(np.linalg.norm(tangent)))
    up = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    if abs(float(np.dot(t, up))) > 0.92:
        up = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    b1 = np.cross(t, up)
    b1 /= max(1e-8, float(np.linalg.norm(b1)))
    b2 = np.cross(t, b1)
    b2 /= max(1e-8, float(np.linalg.norm(b2)))
    return b1, b2


def _add_tube_Along_spline(
    pts: list[np.ndarray],
    radii: list[float],
    sides: int,
    root_flute: float,
    v_start: float,
    v_scale: float,
    ao_bottom: float,
    ao_top: float,
    sun_dir: np.ndarray,
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[tuple[float, float]], list[tuple[int, int, int, int]], list[tuple[int, int, int]]]:
    """Build a smooth tubular branch mesh along 3D spline points `pts` with per-ring `radii`."""
    verts = []
    norms = []
    uvs = []
    colors = []
    tris = []

    n_rings = len(pts)
    cum_len = 0.0
    ring_offsets = []

    for r_idx in range(n_rings):
        p = pts[r_idx]
        if r_idx > 0:
            cum_len += float(np.linalg.norm(p - pts[r_idx - 1]))
        if r_idx == 0:
            tang = pts[1] - pts[0]
        elif r_idx == n_rings - 1:
            tang = pts[-1] - pts[-2]
        else:
            tang = pts[r_idx + 1] - pts[r_idx - 1]
        b1, b2 = _orthonormal_frame(tang)
        t_frac = r_idx / max(1, n_rings - 1)
        ao = ao_bottom + (ao_top - ao_bottom) * (t_frac ** 0.7)
        rad = radii[r_idx]
        flute_amp = root_flute * max(0.0, 1.0 - t_frac * 4.5)

        base_idx = len(verts)
        ring_offsets.append(base_idx)
        for s in range(sides + 1):
            u = s / sides
            ang = 2.0 * math.pi * u
            flute = 1.0 + flute_amp * math.cos(5.0 * ang + 0.7)
            local_r = rad * flute
            normal = math.cos(ang) * b1 + math.sin(ang) * b2
            normal /= max(1e-8, float(np.linalg.norm(normal)))
            pos = p + normal * local_r
            verts.append((float(pos[0]), float(pos[1]), float(pos[2])))
            norms.append((float(normal[0]), float(normal[1]), float(normal[2])))
            uvs.append((float(u * 1.5), float(v_start + cum_len * v_scale)))

            # Golden-hour directional shading + AO in vertex color
            ndl = max(0.0, float(np.dot(normal, sun_dir)))
            lit = ao * (0.68 + 0.32 * ndl)
            cr = int(np.clip(lit * 248.0, 42, 255))
            cg = int(np.clip(lit * 238.0, 40, 250))
            cb = int(np.clip(lit * 222.0, 38, 240))
            colors.append((cr, cg, cb, 255))

    for r_idx in range(n_rings - 1):
        r0 = ring_offsets[r_idx]
        r1 = ring_offsets[r_idx + 1]
        for s in range(sides):
            a = r0 + s
            b = r0 + s + 1
            c = r1 + s + 1
            d = r1 + s
            tris.append((a, b, c))
            tris.append((a, c, d))

    return verts, norms, uvs, colors, tris


def generate_tree(
    cx: float,
    cy: float,
    z_base: float,
    total_height: float = 6.2,
    crown_radius: float = 2.4,
    seed: int = 1001,
    style: str = "street",
) -> dict:
    """
    Generate a complete 3D botanical tree at `(cx, cy, z_base)` with separate:
      - `bark`: {verts, norms, uvs, colors, tris} for `ngpd_bark` (opaque trunk, root flare & boughs)
      - `foliage`: {verts, norms, uvs, colors, tris} for `ngpd_foliage` (alpha-tested/blended layered crown)
    """
    rng = np.random.default_rng(seed)
    sun_dir = np.array([0.48, -0.64, 0.60], dtype=np.float64)
    sun_dir /= np.linalg.norm(sun_dir)

    # Natural per-tree variation in height, width, lean, and crown asymmetry
    h_var = total_height * float(rng.uniform(0.92, 1.12))
    r_var = crown_radius * float(rng.uniform(0.90, 1.14))
    trunk_h = h_var * (0.46 if style == "street" else 0.52)
    base_r = (0.21 if style == "street" else 0.30) * float(rng.uniform(0.90, 1.12))

    lean_x = float(rng.uniform(-0.22, 0.22))
    lean_y = float(rng.uniform(-0.22, 0.22))
    curve_phase = float(rng.uniform(0.0, 2.0 * math.pi))

    # 1. Main curved trunk spline (7 rings)
    trunk_pts = []
    trunk_radii = []
    n_trunk = 7
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        sx = cx + lean_x * t + 0.11 * math.sin(t * math.pi * 1.4 + curve_phase) * t
        sy = cy + lean_y * t + 0.11 * math.cos(t * math.pi * 1.3 + curve_phase) * t
        sz = z_base + trunk_h * t
        trunk_pts.append(np.array([sx, sy, sz], dtype=np.float64))
        # Root flare at t=0, smooth taper upward
        flare = 1.32 if i == 0 else (1.10 if i == 1 else 1.0)
        rad = base_r * flare * ((1.0 - 0.52 * t) ** 0.85)
        trunk_radii.append(rad)

    bark_v, bark_n, bark_uv, bark_c, bark_t = _add_tube_Along_spline(
        trunk_pts,
        trunk_radii,
        sides=8,
        root_flute=0.22,
        v_start=0.0,
        v_scale=0.65,
        ao_bottom=0.52,  # Ground contact shadow at trunk base
        ao_top=0.88,
        sun_dir=sun_dir,
    )

    def append_bark(v_add, n_add, uv_add, c_add, t_add):
        ofs = len(bark_v)
        bark_v.extend(v_add)
        bark_n.extend(n_add)
        bark_uv.extend(uv_add)
        bark_c.extend(c_add)
        bark_t.extend((a + ofs, b + ofs, c + ofs) for a, b, c in t_add)

    # 2. Primary boughs (5 main limbs) + secondary forks
    n_boughs = 5 if style == "street" else 6
    fork_origin = trunk_pts[-1]
    fork_r = trunk_radii[-1] * 0.82
    bough_tips = []

    base_az = float(rng.uniform(0.0, 2.0 * math.pi))
    for b_idx in range(n_boughs):
        az = base_az + (2.0 * math.pi * b_idx / n_boughs) + float(rng.uniform(-0.24, 0.24))
        elev = float(rng.uniform(0.42, 0.78))
        b_len = r_var * float(rng.uniform(0.72, 1.02))
        start_z_frac = float(rng.uniform(0.78, 1.0))
        p0 = trunk_pts[-2] * (1.0 - start_z_frac) + fork_origin * start_z_frac

        b_pts = []
        b_rads = []
        for k in range(5):
            kt = k / 4.0
            # Outward reach with slight upward phototropic curve at the end
            reach = b_len * (kt ** 0.92)
            lift = b_len * math.sin(elev) * kt + 0.14 * (kt * kt) - 0.08 * math.sin(kt * math.pi)
            swirl = 0.12 * math.sin(kt * math.pi + b_idx)
            bx = p0[0] + reach * math.cos(az + swirl) * math.cos(elev)
            by = p0[1] + reach * math.sin(az + swirl) * math.cos(elev)
            bz = p0[2] + lift
            b_pts.append(np.array([bx, by, bz], dtype=np.float64))
            b_rads.append(max(0.025, fork_r * ((1.0 - 0.78 * kt) ** 0.9)))

        bv, bn, buv, bc, bt = _add_tube_Along_spline(
            b_pts, b_rads, sides=6, root_flute=0.0, v_start=1.2, v_scale=0.8, ao_bottom=0.72, ao_top=0.92, sun_dir=sun_dir
        )
        append_bark(bv, bn, buv, bc, bt)
        bough_tips.append((b_pts[-1], az, elev, b_len * 0.52))
        bough_tips.append((b_pts[2], az + 0.45, elev + 0.22, b_len * 0.44))

        # Secondary sub-branch fork from midpoint of each primary bough
        for sub_sign in (-1.0, 1.0):
            s_az = az + sub_sign * float(rng.uniform(0.42, 0.72))
            s_elev = elev + float(rng.uniform(0.08, 0.35))
            s_len = b_len * float(rng.uniform(0.45, 0.64))
            sp0 = b_pts[2]
            s_pts = [
                sp0,
                sp0 + np.array([math.cos(s_az) * s_len * 0.5, math.sin(s_az) * s_len * 0.5, math.sin(s_elev) * s_len * 0.45]),
                sp0 + np.array([math.cos(s_az) * s_len, math.sin(s_az) * s_len, math.sin(s_elev) * s_len * 0.85]),
            ]
            s_rads = [b_rads[2] * 0.75, b_rads[2] * 0.42, 0.02]
            sv, sn, suv, sc, st = _add_tube_Along_spline(
                s_pts, s_rads, sides=5, root_flute=0.0, v_start=2.0, v_scale=0.9, ao_bottom=0.76, ao_top=0.95, sun_dir=sun_dir
            )
            append_bark(sv, sn, suv, sc, st)
            bough_tips.append((s_pts[-1], s_az, s_elev, b_len * 0.48))

    # Add central ascending leader branch from fork_origin up to crown apex so no foliage ever floats
    apex_center = fork_origin + np.array([lean_x * 0.35, lean_y * 0.35, (h_var - trunk_h) * 0.68], dtype=np.float64)
    leader_mid = (fork_origin + apex_center) * 0.5 + np.array([0.06, -0.05, 0.0], dtype=np.float64)
    lv, ln, luv, lc, lt = _add_tube_Along_spline(
        [fork_origin, leader_mid, apex_center],
        [fork_r * 0.78, fork_r * 0.45, 0.025],
        sides=5, root_flute=0.0, v_start=1.5, v_scale=0.85, ao_bottom=0.75, ao_top=0.95, sun_dir=sun_dir
    )
    append_bark(lv, ln, luv, lc, lt)
    bough_tips.append((leader_mid, base_az + 0.5, 0.85, r_var * 0.56))
    bough_tips.append((apex_center, base_az + 1.2, 1.05, r_var * 0.54))

    # 3. Layered Botanical Foliage Canopy around each bough tip and sub-dome
    fol_v = []
    fol_n = []
    fol_uv = []
    fol_c = []
    fol_t = []

    crown_center = fork_origin + np.array([0.0, 0.0, (h_var - trunk_h) * 0.48], dtype=np.float64)

    def add_curved_leaf_cluster(center: np.ndarray, radius: float, yaw: float, pitch: float, roll: float):
        """
        Add a 3D cambered (curved) botanical frond quad (4 triangles in a 2x1 tent/arch, double-sided = 8 tris)
        whose normals point outward from the tree crown for smooth spherical/organic shading!
        """
        cy_a, sy_a = math.cos(yaw), math.sin(yaw)
        cp_a, sp_a = math.cos(pitch), math.sin(pitch)
        cr_a, sr_a = math.cos(roll), math.sin(roll)

        # Rotation matrix Rz(yaw) * Ry(pitch) * Rx(roll)
        rx = np.array([cy_a * cp_a, sy_a * cp_a, -sp_a], dtype=np.float64)
        ry = np.array([cy_a * sp_a * sr_a - sy_a * cr_a, sy_a * sp_a * sr_a + cy_a * cr_a, cp_a * sr_a], dtype=np.float64)
        rz = np.array([cy_a * sp_a * cr_a + sy_a * sr_a, sy_a * sp_a * cr_a - cy_a * sr_a, cp_a * cr_a], dtype=np.float64)

        w = radius * 1.15
        h = radius * 0.95
        arch = radius * 0.26  # 3D camber so cards are curved domes, never flat planes!

        local_pts = [
            (-w, -h * 0.85, -arch * 0.5, 0.04, 0.96),
            (0.0, -h, arch * 0.6, 0.50, 0.96),
            (w, -h * 0.85, -arch * 0.5, 0.96, 0.96),
            (-w, h * 0.85, -arch * 0.3, 0.04, 0.04),
            (0.0, h, arch * 0.8, 0.50, 0.04),
            (w, h * 0.85, -arch * 0.3, 0.96, 0.04),
        ]

        for side in (1.0, -1.0):
            base = len(fol_v)
            for lx, ly, lz, u, v in local_pts:
                p = center + rx * lx + ry * ly + rz * lz
                # Outward foliage normal blended between card normal and spherical crown normal
                crown_vec = p - crown_center
                c_dist = float(np.linalg.norm(crown_vec)) + 1e-6
                n_sphere = crown_vec / c_dist
                n_card = rz * side
                n_blend = n_sphere * 0.68 + n_card * 0.32
                n_blend /= max(1e-8, float(np.linalg.norm(n_blend)))

                # Canopy AO: deeper inside/lower = darker, outer/upper sunlit crown = brighter & warmer
                rel_z = np.clip((p[2] - (z_base + trunk_h * 0.55)) / max(1.0, h_var * 0.65), 0.0, 1.0)
                radial = np.clip(c_dist / max(0.8, r_var * 1.05), 0.0, 1.0)
                ao = 0.50 + 0.28 * rel_z + 0.22 * radial
                ndl = max(0.0, float(np.dot(n_sphere, sun_dir)))
                sun_boost = 0.72 + 0.36 * ndl

                r_col = int(np.clip(ao * sun_boost * 246.0, 48, 255))
                g_col = int(np.clip(ao * sun_boost * 242.0, 52, 255))
                b_col = int(np.clip(ao * (0.68 + 0.24 * ndl) * 218.0, 44, 240))

                fol_v.append((float(p[0]), float(p[1]), float(p[2])))
                fol_n.append((float(n_blend[0]), float(n_blend[1]), float(n_blend[2])))
                fol_uv.append((float(u), float(v)))
                fol_c.append((r_col, g_col, b_col, 255))

            if side > 0:
                fol_t.extend([
                    (base + 0, base + 1, base + 4),
                    (base + 0, base + 4, base + 3),
                    (base + 1, base + 2, base + 5),
                    (base + 1, base + 5, base + 4),
                ])
            else:
                fol_t.extend([
                    (base + 0, base + 4, base + 1),
                    (base + 0, base + 3, base + 4),
                    (base + 1, base + 5, base + 2),
                    (base + 1, base + 4, base + 5),
                ])

    # Place layered curved frond clusters at every bough tip (steeply cambered crossed 3D domes)
    for tip_pos, az, elev, cl_rad in bough_tips:
        for k in range(2):
            yaw = az + k * 1.45 + float(rng.uniform(-0.28, 0.28))
            pitch = (0.92 if k == 0 else -0.78) + float(rng.uniform(-0.22, 0.22))
            roll = (0.45 if k == 0 else -0.52) + float(rng.uniform(-0.20, 0.20))
            jit = rng.uniform(-0.16, 0.16, size=3)
            add_curved_leaf_cluster(tip_pos + jit, cl_rad * float(rng.uniform(0.92, 1.15)), yaw, pitch, roll)

    return {
        "bark": {"verts": bark_v, "norms": bark_n, "uvs": bark_uv, "colors": bark_c, "tris": bark_t},
        "foliage": {"verts": fol_v, "norms": fol_n, "uvs": fol_uv, "colors": fol_c, "tris": fol_t},
    }


def generate_indoor_planter_plant(cx: float, cy: float, z_base: float, height: float = 1.45, radius: float = 0.52, seed: int = 5001) -> dict:
    """Generate a lush multi-stem architectural indoor plant (Ficus / Dracaena rosette) for `ngpd_f*a`."""
    rng = np.random.default_rng(seed)
    fol_v, fol_n, fol_uv, fol_c, fol_t = [], [], [], [], []
    n_fronds = 7
    for k in range(n_fronds):
        az = (2.0 * math.pi * k / n_fronds) + float(rng.uniform(-0.2, 0.2))
        tier = k % 2
        w = radius * (0.88 if tier == 0 else 0.72)
        h = height * (0.85 if tier == 0 else 0.96)
        z0 = z_base + (0.04 if tier == 0 else 0.18)
        ca, sa = math.cos(az), math.sin(az)
        nx, ny = -sa, ca
        pts = [
            (cx - w * ca, cy - w * sa, z0, 0.08, 0.95),
            (cx + w * ca, cy + w * sa, z0, 0.92, 0.95),
            (cx + w * 1.12 * ca + nx * 0.12, cy + w * 1.12 * sa + ny * 0.12, z0 + h, 0.92, 0.05),
            (cx - w * 1.12 * ca + nx * 0.12, cy - w * 1.12 * sa + ny * 0.12, z0 + h, 0.08, 0.05),
        ]
        for side in (1.0, -1.0):
            base = len(fol_v)
            for idx_p, (px, py, pz, u, v) in enumerate(pts):
                top_f = 1.0 if idx_p >= 2 else 0.68
                col = (int(215 * top_f), int(230 * top_f), int(210 * top_f), 255)
                fol_v.append((float(px), float(py), float(pz)))
                fol_n.append((float(nx * side * 0.6), float(ny * side * 0.6), 0.8))
                fol_uv.append((float(u), float(v)))
                fol_c.append(col)
            if side > 0:
                fol_t.extend([(base, base + 1, base + 2), (base, base + 2, base + 3)])
            else:
                fol_t.extend([(base, base + 2, base + 1), (base, base + 3, base + 2)])
    return {"verts": fol_v, "norms": fol_n, "uvs": fol_uv, "colors": fol_c, "tris": fol_t}
