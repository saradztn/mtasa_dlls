# RoyalKingdom - a huge royal castle and capital for MTA:SA 1.6+  (independent project)

Created by Arena.ai Agent Mode. This folder is a **stand-alone project**: nothing in `Ashfall/`, `Castle/`, `Park/`, `FishingRod/` or `source.zip` is modified, and the new build system, outputs and resource will live only here.
(The session is tied to one git branch, so independence is by folder; the other projects are untouched.)

## 1. What `source.zip` (NightCity) taught me - the pipeline I will reuse (not copy-merge)
Read from the code itself (`build.py`, `nc/*`, `lib/*`, `validate.py`, `mta_lua_test_nc.py`):

| Stage | How the project does it | What I do in RoyalKingdom |
|---|---|---|
| Plan | `nc/plan.py` builds a deterministic registry of models (deduplicated by specification) + a list of placements (`x, y, z, rz, tag`) | a plan of the castle: keep / palace / wings / towers / walls / gates / bridges / courtyards / gardens / town + terrain, every part a modular model |
| Geometry | `nc/mb.py` Mesh builder with architectural primitives, `nc/bld*.py` building generators, `nc/ground.py` terrain tiles | same idea: modular kit (wall segments, towers, spires, arches, stairs, balconies, rooms) + terrain tiles with cliffs / waterfalls |
| Lighting | `nc/bake.py` bakes vertex colours (night/day prelit) from lights + AO | baked day and night prelight (torches, lanterns, windows) |
| Export | `lib/rwdff.py` DFF writer, `lib/colfile.py` COL3 writer, `lib/dxt.py` DXT1/DXT5 encoder + mip chain, `lib/rwtxd.py` TXD writer | the same binary writers; DFF + COL per module, TXD per category |
| Textures | `nc/texgen.py` procedural PBR -> `dxt.compress_chain` -> `rwtxd.build_txd` | **textures are AI generated images** (`textures_ai/`), converted (seamless fix, resize, DXT1/DXT5, mips) into the TXDs |
| Resource | `build.py` writes `models.lua`, `layout.lua`, `meta.xml`; client script creates the objects in batches, `engineRequestModel` / `engineReplaceModel`; server script commands | same architecture; commands `/showkingdom`, `/hidekingdom`, enterable interiors |
| QC | `validate.py` (binary readers re-parse DFF/TXD/COL), `mta_lua_test_nc.py` + `mta_stub_nc.lua` (runs the real Lua on a stubbed MTA API), `mta_lua_static.py` (checks every MTA function name against `tools/mta_*_funcs.txt`) | the same three checks |

## 2. Reference (the image you gave me)
Cream limestone palace with a tall central keep, many blue slate spires with gold finials, curtain walls with towers, a stone arch bridge over a river, terraced royal gardens with a fountain, statues, blue-and-gold lion banners, dark green conifers, rocky cliffs with waterfalls, snow mountains, warm lantern light at dusk, a grand interior hall (arched windows, red carpet, chandeliers, marble floor, blue banners).

## 3. Texture plan - AI generated, in batches of 10 (`textures_ai/`)
Rules for every image: seamless / tileable where it is a surface, flat even light (no baked shadows), no text. Batch status:

### Batch 1 - DONE (10)
`stone_ashlar_cream`, `stone_ashlar_aged`, `stone_mossy`, `stone_wet`, `roof_slate_blue`, `cobble_plaza`, `marble_white_veined`, `wood_planks_dark`, `gold_ornate`, `rock_cliff_granite`

### Batch 2 - nature and ground (10)
`rock_mountain_snow`, `snow_clean`, `grass_lush`, `grass_dry_meadow`, `dirt_path`, `forest_floor_leaves`, `gravel_royal_path`, `riverbed_pebbles`, `bark_pine`, `roof_terracotta`

### Batch 3 - exterior architecture (10)
`plaster_cream_town`, `brick_red_town`, `timber_frame_plaster`, `roof_wood_shingle`, `stone_carved_gothic_tracery`, `stone_balustrade`, `copper_verdigris`, `iron_wrought_dark`, `bronze_aged`, `stone_column_fluted`

### Batch 4 - interiors (10)
`marble_checker_floor`, `carpet_red_royal`, `damask_wall_blue_gold`, `wood_panel_oak_carved`, `ceiling_plaster_gilded`, `door_oak_iron`, `stained_glass_window`, `tapestry_royal`, `velvet_curtain_red`, `parquet_floor`

### Batch 5 - heraldry and details (10)
`banner_blue_gold_lion`, `banner_crimson_gold_crown`, `pennant_gold_blue`, `window_gothic_lit_night`, `lantern_glass_warm`, `fresco_ceiling_painting`, `statue_marble_surface`, `fountain_stone_basin`, `torch_wood_wrap`, `chain_iron`

### Batch 6 - vegetation, water and decals (10)
`conifer_foliage_branch`, `deciduous_leaf_cluster`, `ivy_leaves`, `flowers_garden`, `hedge_boxwood`, `waterfall_foam_mist`, `crack_decal`, `moss_decal`, `water_stain_decal`, `rose_bush`
(vegetation / decals are generated on a plain uniform background and keyed to alpha in the conversion step)

## 4. Next stages (start only when you order it)
1. texture conversion (seamless blend, 512 / 1024 px, DXT1 / DXT5, mips) -> TXDs
2. plan + modular kit + terrain + interiors -> DFF / COL / LOD
3. Lua resource, validation, tests, GitHub push
