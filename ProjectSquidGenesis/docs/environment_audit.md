# Environment audit — 2026-10-17

- Working repository: `saradztn/mtasa_dlls`, session branch `arena/949fde0a-mtasa-dlls`.
- Existing repository is a different MTA resource. Its scripts, models and textures are not incorporated into Genesis. No existing tracked files changed.
- New assets live under `ProjectSquidGenesis/`. Export kernel is adapted from repository `tools/fortlib.py`; DragonFF gtaLib is copied with original GPL license and revision `4c332f96bcd7f251e943f90559ba8e572e3d1a3b`. All scene geometry, textures and animation authoring are new procedural work.
- Linux, Python 3.11, Git and authenticated gh available. No Blender executable, MTA client/server, Windows DirectX 9 compiler, GTA skeleton or IFP tool initially available.
- Installed a private venv `/home/user/squid-venv`, with `bpy 4.2.23 LTS` from PyPI. Python bpy exposes the genuine Blender exporter/importer. FBX 7400 exports and Blender sources generated successfully.
- Missing graphical loader libraries prevented initial bpy import. Apt repository access was unavailable. For this sandbox only, X11/OpenGL support libraries were retrieved through GitHub's contents API from `hanpfei/chromium-net`'s Debian amd64 sysroot, and libSM/libICE/libxkbcommon from `eXtern-OS/eXternOS-Base`. These external system binaries are NOT included in the project or required on a normal Blender workstation. `LD_LIBRARY_PATH=/home/user/blender-libs` was used for sandbox bpy processes. No custom rendering DLL is injected into MTA.
- Main MTA source examined via GitHub API: `multitheftauto/mtasa-blue`, commit `e42616dd91b9444c98a570f1f838c45da147e643`, `Client/mods/deathmatch/logic/luadefs/CLuaDrawingDefs.cpp`, in particular DxCreateShader and DxSetShaderValue. This confirms shader filepath/macros, priority, maxdistance, layered and object type arguments. It does NOT certify the shader compiles.
- Engine target: MTA 1.6.0, RenderWare SA version 0x36003, COL3 and native D3D9 mipmapped DXT5 TXD. Custom object IDs requested at runtime; no stock model IDs permanently overwritten.
- Shader target: Effects vs_3_0/ps_3_0 using MTA WORLD/WORLDVIEWPROJECTION/CAMERAPOSITION semantics and stage-0 texture annotation. No unsupported secondary-camera renderer, depth-buffer capture, SSR or ray tracing is claimed. These semantics/profile need actual Windows MTA compilation verification.
- Only the four-view reference board was attached. Rainy-car lighting image missing; no external substitute used.

## Reproducible dependencies
Use Blender 4.2 LTS's Python (includes bpy), or Python 3.11 + PyPI bpy. Standard Linux system requirements include libXrender, libXxf86vm, libXfixes, libXi, libxkbcommon, libSM, libICE, libGL and their dependencies. Prefer OS packages, not the sandbox workaround. Exact installed Python versions are recorded in `tests/build_environment.txt`.

## Blocking gates
Actual MTA graphics compilation, glass sorting, streaming, capsule collisions, multiplayer traversal and performance profiling cannot run here. A target skeleton is needed for proven GTA retargeting; the supplied custom rig is not asserted to be GTA/IFP-compatible out of the box.

## v0.3 update
Rope-only model LOD, stable fading light slots and additional failure checks were authored and tested under the same offline environment. No newly available MTA/DirectX runtime is implied. The material/LOD API tests remain mocks.

## v0.5 update
Eight proximity stations, server reservations, read-only nearest-panel queries and local HUD/debug route lines were added. Expanded multi-handler Lua mocks exercise two-player contention and lifecycle cleanup; no MTA client/server or DirectX environment became available. Environment meshes, textures and animation source/FBX were not artistically changed in this step.

## v0.6 update
Architecture-only bpy build mode preserves the previously validated animation source/FBX. Environment mesh correspondence and closed facade-helper geometry tests were added; actual current-source Cycles views were regenerated. MTA/DirectX remain unavailable; no new engine-compatibility or performance result is claimed.
