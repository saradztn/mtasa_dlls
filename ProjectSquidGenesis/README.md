# ProjectSquidGenesis — editable environment & animation build 0.6

**الحالة: تنفيذ جزئي حقيقي، وليس إعلان اكتمال AAA أو نجاح التشغيل داخل MTA.**

مشروع مستقل عن المورد الموجود في جذر المستودع، مخصص لشد الحبل والجسر الزجاجي فقط. يحتوي مصادر Blender وأصول تشغيل أصلية وخامات إجرائية وحركات FBX فعلية. القيود والاختبارات مفصولة بوضوح في `docs/limitations.md` و`docs/test_report.md`.

## Contents
- Tug hall with opposing supported decks, 48 m shaft and independent three-strand braided rope.
- Adjacent bridge hall, 18 pairs / 36 independently identified glass panels, support frame and landing decks.
- Shared entry corridor, simplified industrial facade, forecourt, fence and open gate.
- 11 genuine DFF/COL3 pairs (including the rope LOD alternative); three mipmapped D3D9 TXDs; 16 material families, normal and packed surface maps.
- 6 material Effects variants sharing real HLSL, wetness transitions, source-position lighting, LOW/MEDIUM/HIGH.
- `GenesisEnvironment.blend`, `GenesisAnimations.blend`, clean custom rig, 20 separate animated FBX files plus a combined file.
- Offline parsers, Lua 5.1 tests, mock runtime/authority tests and FBX reimport validation.

## Build
Python 3.11 recommended. Use a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/build.py --package
# Optional actual Blender/Cycles inspection renders, not MTA screenshots:
.venv/bin/python tools/render_inspection.py
```

On Windows use `.venv\Scripts\python.exe` / `pip.exe`. Normal Blender 4.2 LTS may run the Blender scripts with `blender -b --python tools/build_blender.py`; install NumPy/Pillow/SciPy/lupa for the non-Blender tooling separately. Linux bpy needs the usual X11/OpenGL loader libraries even when rendering headlessly. See environment audit for the sandbox-specific workaround, which is not shipped.

`tools/build.py --skip-blender` regenerates materials/game assets and runs offline tests **without regenerating or validating FBX**. `--environment-only` rebuilds the editable environment and validates its vertex/triangle/UV/material correspondence, while retaining unchanged animation/FBX evidence only if its hashes still match. Use `--environment-only --render --package` for architecture-only changes. It cannot be combined with `--skip-blender`. Full builds regenerate FBX, reimport every clip, test matrices, loop endpoints and scale, then execute resource tests. A failed stage exits nonzero. `--package` creates ignored `dist/ProjectSquidGenesis.zip` with resource, sources, tools, documentation and licenses; no venv/cache files included.

### Individual stages
```sh
python tools/material_generator.py --all
python tools/build_geometry.py
python tools/build_runtime.py
python tools/build_blender.py
# Motion-only rebuild, without rebuilding environment geometry:
python tools/build_animations.py
python tools/validate_fbx.py
python tools/validate_animation_contacts.py
python tools/validate.py
python tools/test_client.py
python tools/test_lighting.py
python tools/test_interactions.py
python tools/test_architecture.py
```

Material edits do not require rebuilding meshes:
```sh
python tools/material_generator.py --name concrete --color 72 79 86 --roughness 0.87 \
  --detail 1 --scale 1 --contrast 1 --wetness 0.65 --normal 1 \
  --resolution 1024 --seed 42 --output source_assets/materials
```
This produces images, not new TXDs automatically. To change the installed library, edit the corresponding palette/default in `material_generator.py`, run `--all`, and restart/reload the resource. Surface RGBA = roughness, AO, wet mask, metallic; normal = conventional tangent RGB. Only maps used by the shader are generated. Base RGBA carries glass alpha. Wayfinding uses a four-row atlas; mesh UVs are stored in RenderWare/D3D V-down convention and the Blender builder explicitly flips V for inspection. Source resolution 1024 for important surfaces, 256 for small/emissive families; tiered runtime maps 256/512/1024 max. No 4K assets.

## Install and test in MTA 1.6+
1. Copy **this entire `ProjectSquidGenesis` directory**, not the parent repository, into `server/mods/deathmatch/resources/[maps]/`.
2. Run `refresh`, then `start ProjectSquidGenesis` in server console. Other resources named in the parent repository are not dependencies.
3. Enable client `debugscript 3`. Read every shader/model error. On graphics failure, TXD/prelight is a limited fallback, **not** successful shader validation.
4. On foot and alive: `/psg enter`, `/psg tug`, `/psg glass`, `/psg leave`. Leave restores original position, rotation, dimension and interior. Entry is refused until the client reports a complete load and acknowledges the latest server-issued request within five seconds. A load-loss report restores the saved origin; no player movement occurs before acknowledgement. This is a loading safeguard, not an anti-cheat proof or a GTA collision-streaming test. Runtime remains untested here.
5. `/psg_quality LOW|MEDIUM|HIGH`; `/psg_wet dry|slightly|wet|heavy|drying`. Material wetness transitions are visual and client-local.
6. `/psg_status` reports readiness, material fallback counts and the active rope tier (not FPS). Admin panel test: `/psg_panel GB_01_L broken` then `intact` or `marked`. Requires ACL right `command.psg_panel` for players. Server console can issue it. Other trusted server resources may call `exports.ProjectSquidGenesis:setPanelState("GB_01_L", "broken")`. No client mutation event is registered.
7. Approach a station and press **E** (or `/psg_use [stationID]`) to reserve a tug slot, acknowledge bridge entry or use the exit. `/psg_release` releases your own reservation; `/psg_panelinfo` inspects the canonical nearest glass panel without changing it. `/psg_debug` enables local station/route guides, off by default. These are readiness tools, **not** completed game rounds. See `docs/continuation_v05.md`.
8. Test restart/stop, player reconnect, two-player state synchronization, door routes and glass collision toggles before any real gameplay integration.

Origin `(5000,5000,100)`, dimension `2601`, interior 0. Configure by editing `source_assets/layout.json` for positions/metadata or `tools/build_geometry.py` for geometry and rebuilding. `shared/config.lua` and `meta.xml` are generated. Do not simultaneously use the same dimension for another resource. Physical shaders apply only to this resource's objects.

## Edit sources
- Open `source_assets/blender/GenesisEnvironment.blend`: textures use relative paths; keep the source_assets directory structure.
- Open `source_assets/animations/GenesisAnimations.blend`: the custom rig now has 18 deform bones plus eight endpoint/pole controls. Choose a named Action on `GenesisHumanoid`; switch to pose mode to inspect controls. Source IK controls are retained; exported FBX contains sampled deform bones.
- `source_assets/blender/mesh_sources.json.gz` preserves runtime geometry/UV/material authoring output. `build_geometry.py` is authoritative for DFF/COL; arbitrary Blender mesh changes do **not** flow back into runtime exports automatically. An artist export/round-trip integration is still needed for hand-edited mesh production.
- Animation export FPS=30, source metres/Z-up/+Y forward, FBX `-Z` forward / `Y` up. Read `docs/animation_manifest.md` and `docs/retargeting.md` before IFP conversion. No direct GTA rig compatibility claim.

## v0.2 continuation
Added server-gated two-stage entry readiness, failure rollback and stale-request tests; transactional quality dictionary loading; raised slatted maintenance galleries and shaft crossbracing; platform seams and rope-end clamps; facade glazing, paired accent colors, readable wayfinding atlas and real drain grate bars. Maintenance ladders are visual equipment only, not a GTA climbing feature. See `docs/continuation_v02.md`.

## v0.3 continuation
Added a 1,920-triangle distant rope model versus the 17,280-triangle near cable; one persistent object switches by hysteresis distance and quality. Local-light slots now fade to zero before changing fixtures, without interpolating source positions. Material parameter/binding failures are checked, partial resources cleaned, and failed quality rollback disables entry. See `docs/continuation_v03.md` and `tests/lighting_results.json`.

## v0.4 continuation
Corrected rig-world root translation and inherited foot rotation, added calibrated elbow/knee poles, brought targets into reachable limb ranges, and authored explicit stance/grip contracts. `validate_animation_contacts.py` checks 20 source actions and 20 reimported FBX files with 2 mm proxy-contact tolerances; ten supported transition pairs are also checked in both representations. These are not skinned sole/finger, biomechanical or GTA playback tests.

`GB_CautiousWalk` is in-place and requires **+0.88 m/cycle (3 seconds)** of actor travel in source +Y for ground-relative stance contact. The saved source contract and retargeting notes explain this requirement. `tools/build_animations.py` can regenerate animations alone. Optional actual source-action GIFs:
```sh
python tools/render_animation_previews.py
# Full build, scene renders, source-action GIFs, verification and ZIP:
python tools/build.py --render --animation-previews --package
```
Rope holding regions are now flat over both decks, with sag only in the free span. Six source-rig anchors in `grip_alignment.json` align the palm-centre proxies to the rope; they are **not** proven GTA ped placements. See `docs/continuation_v04.md`.

## v0.5 continuation
Eight canonical proximity stations (six exclusive tug slots, nonexclusive bridge entry and exit) now have server-managed reservation/readiness logic. Requests validate session, source/protocol, player state, dimension/interior, finite canonical distance and cooldown. Movement/vehicle/load-loss/death/quit/stop release reservations. No player snapping, freezing, forces, scoring, elimination or animation playback is implemented.

The client adds an optional proximity hint and configurable interaction key (`interactionKey` in `tools/build_runtime.py`; set false to use commands only). Debug station and three tour-route guides allocate no world elements or textures. Routes and zones share `source_assets/interactions.json` and generated config; nominal source collision checks are not MTA physics tests. Trusted server exports now include `getPanelState(id)`, `getInteractionState(player)` and `getSlotOccupant(id)` in addition to `setPanelState`.

## v0.6 continuation
Refined the existing exterior only: 41 genuine chamfered extrusions (fins/coping/crowns/gate pillars/fascia), 13 framed service louvers with 130 closed sloping blades, canopy soffit ribs, horizontal reveals and four decorative rainwater stacks. No extra game, room or city was added. The two arena shells, rope, bridge panels, light table and placement transforms are unchanged. Runtime geometry totals 72,816 unique triangles (including the mutually exclusive rope alternative), versus 68,520 in v0.5; no FPS inference is made.

`tools/architectural_details.py` is editable mesh authoring, not a render-only bevel modifier. Geometry tests check closed edge orientation, analytic positive volume, UV finiteness and invalid dimensions. Environment source QA now compares all authored vertices, triangles, material indices and UVs to the Blender meshes. Four actual Blender inspection views include `docs/inspection/exterior_detail.png`. These are not MTA screenshots. See `docs/continuation_v06.md`.

The close facade view `exterior_detail.png` uses a neutral area-light inspection fill to expose geometry; that fill is not saved in the source environment or implemented as MTA lighting. The three wider night views use the scene fixtures without this additional fill.

## Evidence / limitations
`tests/*_results.json` hold actual automated outputs. `docs/inspection/*.png` are rendered from the saved 3D scene, not generative images or MTA output. They are diagnostic only. The delivered geometry/materials and motion studies need further artistic refinement and target-client validation to meet the full requested standard. No FPS, ray tracing, perfect reference-match or complete multiplayer claims.

## Licensing
New project scripts and authored procedural assets: GPL-3.0-or-later, see `LICENSE`. Vendored DragonFF retains its GPL license and revision notice. Geometry helper is adapted from the existing repository exporter (original attribution retained), not a reused environment. User-supplied reference board is included for design review only; no ownership/license of that reference is asserted. No GTA character, external texture pack or IFP animation is bundled.

