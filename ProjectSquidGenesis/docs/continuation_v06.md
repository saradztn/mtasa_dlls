# Continuation v0.6 — facade geometry refinement

## Scope and actual edits
Only the existing entry/exterior asset changed. The two hall shells, platforms, rope tiers, glass-panel template, frame and all 36 addressed panel placements remain unchanged, along with the origin, dimension, light table and object placements. A comparison with the delivered v0.5 ZIP is recorded in `tests/architecture_baseline_v05.json`.

- 41 real eight-sided chamfer extrusions replace selected rectangular fins, crowns, coping, gate pillars and canopy fascia. The small beveled edges are baked into exported triangles, not Blender-only modifiers.
- 13 framed/backed service ventilation modules contain 130 closed sloping blades. Each blade has actual depth and thickness, rather than a flat ventilation decal.
- Horizontal reveal strips and coping caps add depth to the existing stepped silhouette; canopy soffit ribs break up the underside of the existing entrance roof.
- Four decorative vertical rainwater stacks have collars, brackets and angled upper connections. No fluid/plumbing simulation or accessible equipment gameplay is implemented.
- Recessed glass panes are restricted to the actual hall envelopes; previously unsupported panes beyond the hall edges are omitted.
- No extra rooms, games, city, animation conversion or multiplayer round rules were added.

`source_assets/facade_details.json` records the authored inventory. Detailed helper code is in `tools/architectural_details.py`, integrated into `tools/build_geometry.py`. Collision uses conservative box envelopes for the structural extrusions. Small blades, trim and pipes are visual-only; they are not player climbing or collision equipment.

## Geometry and resource budget
The number of DFF/COL pairs remains 11; placed world objects remain 45, including independent panels. Unique triangles including both mutually exclusive rope alternatives changed from **68,520 to 72,816** (+4,296, about 6.27%). This is a file/geometry count, not an FPS, streaming or GPU-memory measurement. Material families and shader instances were not expanded.

The scene still has coarse chunks and is not a hand-finished final AAA environment. New facade details alone do not resolve all remaining architecture/reference-matching acceptance gates.

## Build and validation
```sh
python tools/build.py --environment-only --render --package
```
This regenerates geometry, material/runtime files and the editable environment, checks source correspondence, runs offline/client/server/architecture tests, renders current inspection views and packages. It does **not** rebuild animations or rerun FBX import/contact checks. Existing animation/FBX/contact/GIF evidence is retained only while its recorded source/contract/profile/file hashes match. To rebuild everything, omit `--environment-only` and regenerate animation previews if their source changes.

`tools/test_architecture.py` validates 15 numerical helper specimens at different translated positions. Checks include manifold edges with consistent winding, analytic positive volume, nonzero thickness, finite UVs and rejection of invalid/NaN bevel dimensions. The 41/13/130/4 inventory is checked against authored metadata; this is not artistic acceptance.

`tools/validate_sources.py` now compares every authored environment mesh vertex, triangle, material slot/index and flipped-V UV against the saved Blender scene. Logical decompressed mesh-source content and runtime DFF/COL hashes bind that evidence to the current files. This is stronger than checking only object counts, but still does not prove MTA rendering/physics.

## Visual inspection evidence
Four actual CPU Cycles views are generated from the saved environment:
- `docs/inspection/tug.png`
- `docs/inspection/glass.png`
- `docs/inspection/exterior.png`
- `docs/inspection/exterior_detail.png`

Inspection provenance now includes material-input hashes as well as the Blender-source and rendered-image hashes. These are genuine Blender renders, not generated reference-matching images or MTA captures. Shader and light behavior will differ in MTA.

## Status
Offline construction/parse/source/helper tests: **PASS** when recorded in the current report. MTA shader compilation, in-engine appearance/collision, real multiplayer behavior, final reference matching, artistic animation approval and hardware profiling remain **NOT TESTED / BLOCKED / PARTIAL**, as itemized in `limitations.md`. Overall acceptance remains **PARTIAL**.

The close facade view `exterior_detail.png` uses a neutral area-light inspection fill to expose geometry; that fill is not saved in the source environment or implemented as MTA lighting. The three wider night views use the scene fixtures without this additional fill.
