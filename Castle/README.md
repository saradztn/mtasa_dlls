<!-- Created by: Arena.ai Agent Mode (AI) -->
# Castle — enterable gothic castle for MTA:SA

A complete gothic castle (stone plinth with grand stairs and parapet, great hall with gallery and twin grand
staircases, library wing, dining wing, keep with a spiral staircase, towers, spires, stained glass, rugs, banners,
chandeliers, torches, fireplaces, bookshelves, armour, cobwebs …) built procedurally in Python and exported as
real GTA SA RenderWare files.

| File | Content |
|---|---|
| `model/Castle.dff`, `CastlePart2.dff`, `CastlePart3.dff`, `CastleFx.dff` | the castle in 4 parts (3 solid + 1 transparent for cobwebs / flames / orbs), **one atomic per DFF**, together 122 k vertices / 86 k triangles, baked day + night vertex colours |
| `model/CastleGate.dff`, `model/CastleDoor.dff` | the arched gate leaf (2.0 m) and the interior door leaf (1.7 m × 2.2 m) |
| `texture/Castle.txd` | 18 textures, shared by the three models (DXT1; DXT5 only for web / orb / flame) |
| `collision/Castle.col`, `CastleGate.col`, `CastleDoor.col` | COL3: 2 449 boxes + a 1 968-face mesh for the castle (walls, floors, every stair step, towers). `CastlePart2/3/Fx.col` are stubs with the castle bounds (so GTA does not cull those parts) |
| `resource/Castle/` | ready-to-use MTA resource (copy the folder into `resources/`, `start Castle`) |
| `preview/*.jpg` | software renders (day and night) of the exterior and every room |
| `source/` | the generator (`build.py`), QC (`validate.py`), previews (`preview.py`), librw check, Lua smoke test |

## Use in MTA:SA
1. Copy `resource/Castle` to the server's `resources/` and run `start Castle`.
2. Stand on flat ground and type **`/showx`**: the castle appears 16 m in front of you, facing you; the entrance gate is
   at the bottom of the plinth stairs. Walk up — the gate (and every interior door) opens by itself when you are near and
   closes behind you. **`/hidex`** removes it.

### Replaced objects (important)
GTA SA / MTA show only **one atomic per object model**, therefore the castle is split into 4 models that the server
places at the same origin. Each original below has exactly one instance on the map; they are hidden while the resource
runs and come back when it stops.

| ID | Original | Becomes |
|---|---|---|
| 12853 `sw_gas01` | Dillimore petrol station | castle part 1 (+ the full collision) |
| 12859 `sw_cont03` | loading-bay container | castle part 2 |
| 12860 `sw_cont04` | loading-bay container | castle part 3 |
| 12861 `sw_cont05` | loading-bay container | castle part 4 (cobwebs, flames, orbs; alpha) |
| 12854 `sw_gas01int` | petrol station interior | gate leaf |
| 12855 `sw_copshop` | Dillimore police station | door leaf |

Vanilla LOD objects of them may still be seen from far away. To use other IDs edit `ID_PARTS` / `ID_GATE` / `ID_DOOR` in
`source/build.py` and rebuild (it regenerates `ids.lua`, `meta.xml` and the COL headers). Settings (distance,
admin-only, door speed/reach) are in the `CFG` table at the top of `server.lua`.

## Rebuild / check
```
cd source
python3 build.py          # writes model/ texture/ collision/ and resource/Castle (files, ids.lua, doors_data.lua, meta.xml)
python3 validate.py       # DFF / TXD / COL structure + voxel walkability test (every room reachable on foot)
python3 mta_lua_test.py   # runs server.lua + client.lua against a stubbed MTA API (needs `pip install lupa`)
python3 preview.py day|night front,hall,...
sh tools/build_librw_check.sh && /tmp/librw_check ../model/Castle.dff ../texture/Castle.txd   # reference loader
```

## What was verified (and what was not)
* DFF / TXD / COL parsed by my own readers **and** by the reference RenderWare implementation (aap/librw): `source/librw_report.txt`.
* `validate.py`: 0 failures — all rooms, both floors of the wings, gallery, throne dais, keep spiral up to the observation
  floor, and all doorways are reachable by a 1.8 m walker over the collision geometry alone.
* The Lua resource was executed against stubbed MTA functions (commands, door open/close, hide/show, client load/restore).
* **Not tested inside the real game** (no MTA client in the build environment). Please send a screenshot / `debugscript 3`
  output if anything looks wrong.
* Place the castle on reasonably flat ground; the castle floor sits 1.5 m above the ground and the plinth is sunk 0.5 m into it, so uneven terrain may poke through or leave gaps.
