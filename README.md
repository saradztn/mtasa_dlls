# NextGenPoliceDepartment — Photorealistic Golden-Hour, Wet-PBR & 4K Spatial Upscaling Edition (MTA:SA 1.6 / DirectX 9)

> **العربية**: للاطلاع على الدليل الكامل باللغة العربية (التثبيت، أوامر التحكم، الإعدادات، متطلبات التشغيل، وحل المشكلات)، راجع ملف **[`README_AR.md`](README_AR.md)** أو القسم العربي أدناه.

## 1. Overview & Visual Upgrade Summary

`NextGenPoliceDepartment` is a complete, server-authoritative, multi-floor Police Headquarters resource for **Multi Theft Auto: San Andreas (MTA:SA 1.6+)** upgraded into a photorealistic **Golden-Hour & Wet-Surface PBR environment** with a dedicated **Two-Pass AMD FSR 1.0 (EASU + RCAS) 4K Spatial Upscaling pipeline** tuned for the **AMD Radeon RX 580 2048SP, Ryzen 5 3600X, 16 GB RAM** hardware target.

### Key Engineering & Visual Upgrades
1. **Golden-Hour Atmospheric Lighting & Solar System (`shaders/ngpd_common.fxh`, `client/ngpd_weather.lua`, `client/ngpd_lighting.lua`)**:
   - Physically inspired Rayleigh/Mie atmospheric sunset sky model with a controlled solar disc, horizon aureole, illuminated sunset clouds, directional shadow contrast, contact ambient occlusion, and **ACES Filmic tone mapping**.
   - Includes 9 client-side weather presets (`goldenhour`, `sunset`, `postrain`, `sunny`, `cloudy`, `night`, `lightrain`, `heavyrain`, `fog`) and direct time-of-day locking (`/ngpd_time HH:MM`).
2. **Ultra-Realistic Wet Surfaces, Puddles & Reflections (`shaders/asphalt.fx`, `shaders/concrete.fx`, `shaders/wet.fx`, `shaders/glass.fx`)**:
   - Replaced synthetic noise textures with crushed-stone bitumen asphalt, micro-crack networks, tire-wear lanes, oil patina, architectural precast concrete, and granite plaza pavers.
   - Non-repeating world-space standing puddles with 4-cell expanding rain ripples + wind-driven capillary waves, porous moisture darkening, and high-contrast Fresnel reflections of the golden-hour sky, solar path, and building glazing.
3. **Real-World PBR Material & Texture Replacement (`tools/rebuild_textures.py`, `textures/`)**:
   - **60 native textures** per tier across `ngpd_world_high.txd` (`1024 px`), `ngpd_world_med.txd` (`512 px`), and `ngpd_world_low.txd` (`256 px`) with full mipmap chains (`FILTER_MIPLINEAR = 0x6`) and `8x` anisotropic filtering.
   - **136 DXT5 DDS maps** (`*_n.dds` in DXT5nm format + `*_s.dds` packing Roughness, AO, Puddle/Emissive mask, and Metallic).
   - Preserves 100% of UV-dependent signage, police badges, floor emblems, and CCTV/computer screens while upgrading their physical material relief.
4. **Rebuilt 3D Botanical Vegetation (`source/vegetation/tree_generator.py`, `tools/rebuild_models.py`, `shaders/foliage.fx`)**:
   - Replaced all **41 primitive exterior trees** (previously 14-triangle concrete-textured cylinders + 18-triangle flat diamond cards) with root-flared, organically curved S-spline trunks and multi-level boughs mapped to `ngpd_bark` + layered 3D cambered botanical leaf crowns mapped to `ngpd_foliage`.
   - Replaced all **30 indoor planter clusters** across `ngpd_f*a.dff` with multi-frond botanical rosettes.
   - Added vertex wind sway, leaf flutter, two-sided shading, and golden-hour backlit chlorophyll subsurface scattering (`shaders/foliage.fx`).
5. **AMD FSR 1.0 Style 4K Spatial Upscaler (`shaders/upscale_easu.fx`, `shaders/upscale_rcas.fx`, `client/ngpd_upscaler.lua`, `source/dx9_upscaler_dll/`)**:
   - Two-pass spatial reconstruction (`12-tap EASU` + `5-tap ringing-free RCAS`) targeting up to **3840×2160 (4K UHD)** in DirectX 9 without requiring motion vectors, inaccessible depth buffers, or unsafe anti-cheat DLL injection.
   - Standalone C++17 shared library (`source/dx9_upscaler_dll/`) also included for offline verification and CLI benchmarking.

---

## 2. Repository Structure

| Path | Description |
|---|---|
| `meta.xml` | Ready-to-run MTA:SA 1.6 resource manifest (`15` Lua scripts, `282` asset files, `4` server exports). |
| `shared/`, `server/`, `client/` | Complete Lua 5.1 resource scripts (config, materials, doors, elevators, models, shaders, weather, wetness, quality presets, and 4K upscaler). |
| `shaders/` | 10 DirectX 9 HLSL shaders (`asphalt.fx`, `concrete.fx`, `floor.fx`, `foliage.fx`, `glass.fx`, `material_base.fx`, `metal.fx`, `wet.fx`, `upscale_easu.fx`, `upscale_rcas.fx`) + `ngpd_common.fxh`. |
| `models/` & `collisions/` | 66 RenderWare `0x36003` `.dff` models and 66 `COL3` `.col` collision files with rebuilt 3D botanical vegetation and golden-hour prelighting. |
| `textures/` | `ngpd_world_{high,med,low}.txd` (`180` mipmapped textures) + `136` DXT5nm normal (`*_n.dds`) and PBR surface (`*_s.dds`) maps. |
| `source/` | `source/vegetation/tree_generator.py` (3D botanical tree generator) and `source/dx9_upscaler_dll/` (C++17 EASU+RCAS 4K upscaler library & CLI test). |
| `assets/` | PBR source textures (`assets/source_textures/`), texture before/after sheet (`assets/textures_preview/before_after_textures.png`), and 3D scene/tree/upscaler renders (`assets/renders/`). |
| `tools/` | `rebuild_textures.py`, `rebuild_models.py`, `render_previews.py`, `package_release.py`, and `vendor/DragonFF/gtaLib`. |
| `tests/` | `tests/run_all_tests.py` and `tests/test_report.json` (`8 PASSED, 0 FAILED`). |
| `docs/` | `ASSET_AND_LICENSE_MANIFEST.md`, `TEST_AND_VERIFICATION_REPORT.md`, and `RELEASE_MANIFEST.json`. |
| `backup/` | Intact original source files (`backup/original_source/`), original unmodified models (`backup/original_models/`), and `backup/BACKUP_MANIFEST.json` (+ full original archive in `build/backup/NextGenPoliceDepartment_original.zip`). |
| `dist/` | Packaged ready-to-install `dist/NextGenPoliceDepartment.zip` (`41.6 MB`). |
| `setup_and_build.bat` | Automated Windows dependency checker, asset builder, validator, packager, and MTA resource installer. |

---

## 3. Windows Build & Installation Instructions

### Automated Build & Packaging (`setup_and_build.bat`)
```bat
:: Validate assets, run all tests, and package dist\NextGenPoliceDepartment.zip
setup_and_build.bat

:: Automatically copy dist\NextGenPoliceDepartment.zip into your MTA:SA server resources folder
setup_and_build.bat --install

:: Rebuild all PBR TXD/DDS textures and 3D models from source before packaging
setup_and_build.bat --rebuild --install
```

### Manual Installation in MTA:SA 1.6 Server
1. Copy `dist/NextGenPoliceDepartment.zip` into `<MTA San Andreas 1.6>\server\mods\deathmatch\resources\`.
2. In the MTA Server console, run:
   ```text
   refresh
   start NextGenPoliceDepartment
   ```

---

## 4. In-Game Commands & Quality / Upscaler Controls

- **Quality Presets**: `/ngpd_quality <performance | balanced | high | ultra | upscaling_4k | low | medium>`
- **Weather & Golden-Hour Presets**: `/ngpd_weather <goldenhour | sunset | postrain | sunny | cloudy | night | lightrain | heavyrain | fog | off>`
- **Time-of-Day Lock**: `/ngpd_time <HH:MM | off>` (e.g. `/ngpd_time 18:50`)
- **Wetness & Puddles**: `/ngpd_wet <0..100 | auto>`
- **Fine Visual Controls**: `/ngpd_set <wetness | reflections | bloom | sun | shadows | puddles | wind | vegetation> <0..200>` (or `/ngpd_set reset`)
- **4K Spatial Upscaler (`EASU + RCAS`)**:
  - `/ngpd_upscale <on | off | performance | balanced | quality | ultra_quality | native | hud | aspect>`
  - `/ngpd_scale <50..100>` (Internal rendering scale percentage)
  - `/ngpd_sharpen <0..100>` (RCAS contrast-adaptive sharpening strength)
- **Gameplay & Navigation**:
  - Press **`E`** near any of the 128 doors/gates or 3-floor elevator call buttons.
  - `/ngpd_tp` (teleport to main entrance), `/ngpd_relocate`, `/ngpd_setorigin x y z rz`, `/ngpd_resetorigin`, `/ngpd_doors`, `/ngpd_lock [doorId]`, `/ngpd_shaders`.

---

## 5. الملخص باللغة العربية (Arabic Quick Reference)

<div dir="rtl">

- **التثبيت السريع على Windows**: شغّل الملف `setup_and_build.bat --install` أو انسخ الملف الجاهز `dist/NextGenPoliceDepartment.zip` إلى مجلد `server\mods\deathmatch\resources\` ثم نفّذ الأمر `start NextGenPoliceDepartment` في خادم MTA:SA.
- **تفعيل مظهر الساعة الذهبية والأرضية المبللة (المطابق للصورة المرجعية)**:
  - اكتب في المحادثة: `/ngpd_quality ultra` (أو `/ngpd_quality upscaling_4k` لشاشات 4K على بطاقة RX 580 2048SP).
  - اكتب: `/ngpd_weather goldenhour`
- **للدليل العربي التفصيلي الكامل**: راجع ملف **[`README_AR.md`](README_AR.md)**.

</div>
