<!-- Created by: Arena.ai Agent Mode (AI) - Park MTA:SA project -->
# Central Park (MTA:SA resource)

A complete, walkable park that is built in front of you with **`/showpark`**: entrance gate with stone pillars and an
automatic gate, paved paths, fountain, pond with real swimmable water and a walkable wooden bridge, gazebo, kiosk,
playground (slide tower, swings, merry-go-round), benches you can `/sit` on, lamps, info boards, trees / bushes / flowers /
reeds / lily pads, ducks, birds, and ~15 procedurally synthesised sounds.

Everything is **client side** and **does not replace any GTA model**: the models are allocated with
`engineRequestModel("object")` and looked up by name (model ids differ per client).

## Install / use
1. Copy `resource/Park` into your server's `resources/` folder, `refresh`, `start Park`.
2. In game: `/showpark` (stand where you want the gate; the park grows 17 m in front of you, facing away from you).
   `/hidepark` removes it, `/parkz <m>` raises/lowers it (e.g. on slopes). Late joiners get the current state automatically.
3. `/sit` next to a bench (any movement key stands up), `/parkwind` toggles the wind-sway shader (default off),
   `/parkinfo` prints status. Needs MTA 1.5.8-9.20716 or newer (`engineRequestModel`).

Set `ADMIN_ONLY = true` at the top of `server.lua` to restrict the commands to the Admin ACL group.

## What is inside
| Folder | Content |
|---|---|
| `model/` `texture/` `collision/` | 62 DFF + 62 COL (50 props / plants / structures and 12 ground tiles), 4 TXD (`flora` `ground` `props` `struct`, DXT1/DXT5 with mipmaps) |
| `audio/` | 15 WAV (mono 16-bit 22.05 kHz): birds x5, fountain, pond, wind, distant city, crickets, frog, duck, swing creak, gate creak, kiosk bell |
| `resource/Park/` | `meta.xml`, `server.lua`, `client.lua`, `wind.fx`, generated `models.lua` / `layout.lua`, `files/` |
| `preview/` | software renders of the park (day / night) and spectrograms of the sounds |
| `source/` | the whole generator (Python + numpy): `build.py` rebuilds everything, `validate.py`, `mta_lua_test.py`, `audio_qc.py`, `preview_park.py`, `tools/` |

Numbers: 821 objects, 39 lamps, 19 benches, 74 trees, DFF 3.4 MB (59k vertices / 57k triangles), TXD 6.6 MB, COL 0.4 MB, audio 2.5 MB.

## How the models are made (no shortcuts)
Every model is built from real geometry (lathes, tubes, swept profiles, leaf cards, beveled boxes), UV-mapped with tiling
textures generated procedurally (bark, leaves, bricks, paving, cobble, grass, wood, iron, rubber ...), baked vertex lighting
(day + night colour sets), explicit hand-built COL (boxes / spheres / triangle meshes; the bridge deck is a triangle mesh,
the ground tiles carry the pond bowl so you can swim) and written as RenderWare 3.6.0.3 (San Andreas) DFF / D3D9 TXD / COL3.

## Quality checks (run them: `cd source && python3 build.py && python3 validate.py && python3 mta_lua_test.py`)
* `validate.py` - independent parser re-reads every shipped file: valid indices, finite values, unit normals, winding, BinMesh,
  every material exists in its TXD, DXT format / mip chain, COL header / bounds, meta.xml == files on disk, Lua compiles,
  layout only uses existing models, no solid prop blocks a footpath, the bridge deck is a continuous surface (slope 33 %, ends meet the banks).
  Result: **0 failures** (`source/qc_report.txt`).
* `mta_lua_test.py` - runs the *real* `client.lua` / `server.lua` on a stubbed MTA API (lupa): chunked loading, all 821 objects,
  water, effect, gate opens / closes, swings / merry-go-round / ducks move, bell, info board HUD, `/sit` + stand-up + server distance check,
  day/night lights, wind shader toggle, `/hidepark` leaves nothing (objects, sounds, timers, handlers), re-show without duplication,
  hide during loading, model ids freed on stop. Result: **0 failures**.
* `source/librw_report.txt` - all 62 DFF + TXD pairs load in **aap/librw**, the reference RenderWare implementation: 62 / 62 pass.
* `audio_qc.py` - peaks, RMS, loop seams (all loops click-free).

## Water (important)
`createWater` rounds every x/y to an **even integer** and GTA only renders **axis-aligned** water polygons. The first version used a
fan of arbitrary triangles; after the rounding they became degenerate and crashed `gta_sa.exe` (integer divide by zero in the water
renderer, `0xC0000094`). The pond is now covered with axis-aligned rectangles on the 2 m world grid (SW, SE, NW, NE order), valid for any
rotation of the park; `mta_lua_test.py` checks even coordinates, rectangle shape, and full coverage of the bowl for 5 rotations.

## Not verified in the real game (be honest)
This was built in a sandbox without GTA/MTA. Please test and report: the `water_fountain` particle effect (guarded with `pcall`),
`createLight` night lights, the parent model `1215` used for `engineRequestModel`, the sit height on benches (adjust `+ 0.80` in
`client.lua`), and the wind shader `wind.fx` (cannot be compiled here; if your GPU refuses it `/parkwind` prints a message and nothing else breaks).
Debug output: `debugscript 3`.
