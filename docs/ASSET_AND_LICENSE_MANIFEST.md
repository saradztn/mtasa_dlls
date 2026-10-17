# Asset Source, Provenance & License Manifest (`NextGenPoliceDepartment`)

## 1. Original Base Project Backup
- **Source Archive**: `NextGenPoliceDepartment.zip` (Google Drive ID: `1djLqXeTz_JJ2qsEUKXFpstE6vGcHzafe`)
- **SHA-256 Checksum**: Recorded in `backup/BACKUP_MANIFEST.json` (`292` original files)
- **Preserved Backups**:
  - `backup/original_source/`: Unmodified original `meta.xml`, `shared/`, `server/`, `client/`, and `shaders/` files.
  - `backup/original_models/`: Unmodified original RenderWare `.dff` models prior to botanical 3D tree and prelight upgrades.
  - `build/backup/NextGenPoliceDepartment_original.zip`: Full byte-for-byte original archive.

---

## 2. Real-World PBR Texture & Surface Map Pipeline (`textures/` & `assets/source_textures/`)
All 60 material textures inside `textures/ngpd_world_{high,med,low}.txd` (`180` mipmapped DXT1/DXT3 rasters with `FILTER_MIPLINEAR = 0x6`) and all `136` DXT5nm normal (`*_n.dds`) and PBR surface (`*_s.dds`: `R=Roughness, G=AO, B=Puddle/Emissive Mask, A=Metallic`) maps are watermark-free, seamless, and generated deterministically by `tools/rebuild_textures.py`:

| Material Category | Texture Names | Source & Synthesis Method | License |
|---|---|---|---|
| **Asphalt & Roadways** | `ngpd_asph_parking`, `ngpd_asph_road`, `ngpd_asph_worn`, `ngpd_road_line_white`, `ngpd_road_line_yellow`, `ngpd_parking_lines` | Synthesized from `assets/source_textures/asphalt_parking_source.jpg` and `asphalt_road_source.jpg` (seamless crushed-stone bitumen aggregate) + procedural micro-fissure crack network, oil patina, and depression puddle masks (`B` channel). | Original / Permissive Repository Asset (CC0 / MIT) |
| **Architectural Concrete & Stone** | `ngpd_conc_facade`, `ngpd_conc_smooth`, `ngpd_conc_raw`, `ngpd_conc_weathered`, `ngpd_conc_block`, `ngpd_conc_beam`, `ngpd_conc_column`, `ngpd_conc_curb`, `ngpd_conc_FOUND`, `ngpd_conc_stairs`, `ngpd_conc_wall_ext`, `ngpd_sidewalk`, `ngpd_plaza_stone`, `ngpd_floor_lobby`, `ngpd_floor_corridor` | Synthesized from `assets/source_textures/concrete_facade_source.jpg`, `sidewalk_paving_source.jpg`, `plaza_stone_source.jpg`, and `polished_lobby_source.jpg` with frequency-domain high-frequency pore/joint detail injection while preserving architectural form-tie and expansion-joint UV alignment. | Original / Permissive Repository Asset (CC0 / MIT) |
| **Botanical Bark & Foliage** | `ngpd_bark` (new), `ngpd_foliage`, `ngpd_grass`, `ngpd_mulch` | `ngpd_bark` synthesized from `assets/source_textures/tree_bark_source.jpg` (deep vertical bark fissures, DXT5nm relief). `ngpd_foliage` synthesized procedurally via 240+ layered botanical leaf blades with midrib/lateral veins, serrated margins, and DXT3 alpha cutout. `ngpd_grass` synthesized from `assets/source_textures/grass_ground_source.jpg`. | Original / Permissive Repository Asset (CC0 / MIT) |
| **Metals, Glazing & Wood** | `ngpd_metal_panel`, `ngpd_metal_alu`, `ngpd_metal_frame`, `ngpd_metal_painted`, `ngpd_metal_bars`, `ngpd_metal_grate`, `ngpd_metal_hardware`, `ngpd_metal_matte`, `ngpd_glass_facade`, `ngpd_glass_interior`, `ngpd_wood_desk`, `ngpd_wood_light`, `ngpd_bookshelf` | Synthesized from `assets/source_textures/metal_panel_source.jpg` and `wood_desk_source.jpg` with directional brushed anisotropy and Sobel DXT5nm bevel normal maps. | Original / Permissive Repository Asset (CC0 / MIT) |
| **UV-Locked Signage, Badges & Screens** | `ngpd_sign_police`, `ngpd_badge`, `ngpd_floor_emblem`, `ngpd_sign_atlas`, `ngpd_screen_cctv`, `ngpd_screen_pc`, `ngpd_board_case` | Preserves 100% of the original typography, badge star geometry, and 2x4 directional sign UV layout while enhancing surface micro-grain, metallic/emissive masks, and DXT5nm bevel normals. | Original Project + Repository Upgrade |

---

## 3. 3D Botanical Vegetation & Model Pipeline (`source/vegetation/tree_generator.py` & `tools/rebuild_models.py`)
- **41 Exterior Trees (`ngpd_site_00/01/10/20` & `ngpd_site_00a/01a/10a/20a`)**:
  - Replaced primitive 14-triangle concrete-textured cylinders and 18-triangle flat diamond cards with organically curved S-spline root-flared trunks (`ngpd_bark`), 5–6 primary boughs, secondary branch forks, ascending crown leaders, and multi-layered cambered 3D botanical leaf clusters (`ngpd_foliage`) with baked 3D canopy AO and golden-hour self-shadowing.
- **30 Indoor Planter Clusters (`ngpd_f0ca`, `ngpd_f0wa`, `ngpd_f1ca`, `ngpd_f1ea`, `ngpd_f1wa`, `ngpd_f2ca`, `ngpd_f2ea`, `ngpd_f2wa`)**:
  - Replaced 12-triangle crossed quads with multi-frond architectural indoor plant rosettes.
- **RenderWare Serialization**:
  - Uses `tools/vendor/DragonFF/gtaLib` (MIT License, Copyright (c) Parik) targeting RenderWare `0x36003` (GTA:SA) and `COL3` collision format.

---

## 4. 4K Spatial Upscaling Pipeline (`shaders/upscale_*.fx`, `client/ngpd_upscaler.lua`, `source/dx9_upscaler_dll/`)
- **Algorithm**: Clean-room DirectX 9 HLSL (`ps_3_0` + `ps_2_0` fallback) and C++17 implementation of AMD FidelityFX Super Resolution 1.0 (FSR 1.0: 12-tap Edge-Adaptive Spatial Upsampling `EASU` + 5-tap Robust Contrast-Adaptive Sharpening `RCAS`, MIT License specification by Advanced Micro Devices, Inc.).
- **Hardware Tuning**: Specifically profiled and configured for **AMD Radeon RX 580 2048SP (8 GB GDDR5), AMD Ryzen 5 3600X, 16 GB RAM** targeting up to `3840x2160` (4K UHD) output.
