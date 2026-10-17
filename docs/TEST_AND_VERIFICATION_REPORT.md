# Engineering Test & Verification Report (`NextGenPoliceDepartment`)

All automated checks are executed by `python3 tests/run_all_tests.py` (machine-readable output saved to `tests/test_report.json`).

## Summary
- **PASSED**: `8` suites
- **FAILED**: `0` suites
- **BLOCKED**: `0` suites
- **NOT TESTED**: `1` item (Live interactive Windows MTA:SA 1.6 client+server session on physical RX 580 2048SP hardware)

---

## Detailed Results

| Category | Test Suite | Status | Verified Details |
|---|---|---|---|
| **1. Manifest** | `meta.xml` & Asset Existence | **PASSED** | All `15` Lua scripts (`shared`, `server`, `client`), `282` asset files (`66` DFFs, `66` COLs, `3` TXDs, `136` DDS maps, `11` HLSL `.fx`/`.fxh` files), and `4` server exports exist on disk and are non-empty. |
| **2. Lua Syntax** | LuaJIT 2.1 / Lua 5.1 Bytecode Compilation | **PASSED** | All `15` Lua scripts (`shared/ngpd_config.lua`, `shared/ngpd_util.lua`, `shared/ngpd_data.lua`, `shared/ngpd_materials.lua`, `server/ngpd_main.lua`, `server/ngpd_doors.lua`, `server/ngpd_elevator.lua`, `client/ngpd_quality.lua`, `client/ngpd_wet.lua`, `client/ngpd_weather.lua`, `client/ngpd_shaders.lua`, `client/ngpd_lighting.lua`, `client/ngpd_models.lua`, `client/ngpd_doors.lua`, `client/ngpd_upscaler.lua`) compile with zero syntax errors. |
| **3. Server Runtime** | Server-Authoritative Doors, Exports, Elevator & ACL | **PASSED** | Executed under `lupa.luajit21` with deterministic MTA server stubs: verified world origin (`177.0, 2514.5, 16.2`), `128` doors (`ngpdGetDoorState`, `ngpdOpenDoor`, `ngpdCloseDoor`, `ngpdSetDoorLocked` lock-when-closed safety), elevator floor transitions, frozen police vehicles, and `/ngpd_tp` & `/ngpd_status`. |
| **4. Client Runtime** | Models, Shaders, Golden-Hour Weather, Wetness & 4K Upscaler | **PASSED** | Executed under `lupa.luajit21` with deterministic MTA client stubs: verified `53` static objects + `13` door leaf models, `60` PBR material shader bindings (including `ngpd_bark` & `ngpd_foliage`), all `9` weather presets (`goldenhour`, `sunset`, `postrain`, `sunny`, `cloudy`, `night`, `lightrain`, `heavyrain`, `fog`), `/ngpd_time`, `/ngpd_set`, all `5` quality tiers (`performance`, `balanced`, `high`, `ultra`, `upscaling_4k`), 2-pass EASU+RCAS 4K upscaler (`performance` 50%, `balanced` 59%, `quality` 67%, `ultra_quality` 77%, `native` 100%), `onClientRestore` device-reset recovery, VRAM exhaustion fallback, and zero-leak `onClientResourceStop`. |
| **5. 3D Models** | RenderWare DFF (`66`) & COL3 (`66`) Binary & Vegetation Integrity | **PASSED** | All `66` `.dff` files verified at RenderWare version `0x36003` (`286,012` total vertices, `177,400` total triangles; every mesh within 16-bit `< 65,535` limits), with `41` exterior trees rebuilt with `ngpd_bark` + `ngpd_foliage` and `30` indoor planter clusters rebuilt. All `66` `.col` (`COL3`) files verified with non-degenerate bounding spheres covering visual geometry. |
| **6. Textures** | TXD Archives (`3 × 60`) & DXT5nm/Surface DDS (`136`) | **PASSED** | `ngpd_world_{low,med,high}.txd` each contain `60` mipmapped DXT1/DXT3 textures (`180` total) with `platform_id = 9` and `filter_mode = 0x6` (`FILTER_MIPLINEAR`). All `136` `.dds` files verified with `DXT5` FourCC, mipmap flags `0x000A1007`, and complete mip chains down to `4×4`. |
| **7. Shaders** | DirectX 9 HLSL Static Analysis & Technique Verification | **PASSED** | All `10` `.fx` shaders (`asphalt.fx`, `concrete.fx`, `floor.fx`, `foliage.fx`, `glass.fx`, `material_base.fx`, `metal.fx`, `wet.fx`, `upscale_easu.fx`, `upscale_rcas.fx`) and `ngpd_common.fxh` verified for balanced syntax, `vs_3_0/ps_3_0` high techniques, `vs_2_0/ps_2_0` low techniques, and fixed-function `fallback` techniques. |
| **8. Upscaler C++** | Standalone C++17 DirectX 9 EASU+RCAS 4K Upscaler Library | **PASSED** | Compiled `source/dx9_upscaler_dll/libngpd_dx9_upscaler.so` and executed `test_upscaler_cli`: verified all `5` presets at `3840×2160` (`50%` = `1920×1080` [-75.0% pixels], `59%` = `2266×1274` [-65.2% pixels], `67%` = `2572×1446` [-55.2% pixels], `77%` = `2956×1662` [-40.8% pixels], `100%` = `3840×2160`), `21:9` aspect-ratio preservation (`3440×1440` -> `2560×1440` viewport), device-lost/reset state machine, and RGBA8 two-pass EASU+RCAS reconstruction. |
| **9. Live In-Game Runtime** | Interactive Windows MTA:SA 1.6 Client + Server Session on Physical AMD Radeon RX 580 2048SP | **NOT TESTED** | The build and verification environment is a Linux container without a Windows DirectX 9 display server or MTA:SA 1.6 executable. In-game visual behavior is verified offline via software 3D DFF/TXD rasterization (`assets/renders/*.png`), C++ EASU+RCAS image processing, and Lua 5.1 runtime simulation. |
