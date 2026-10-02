<!-- Created by: Arena.ai Agent Mode (AI) -->
# Castle — enterable gothic castle for MTA:SA

A complete gothic castle (stone plinth with grand stairs and parapet, great hall with gallery and twin grand
staircases, library wing, dining wing, keep with a spiral staircase, towers, spires, stained glass, rugs, banners,
chandeliers, torches, fireplaces, bookshelves, armour, cobwebs …) built procedurally in Python and exported as
real GTA SA RenderWare files.

| File | Content |
|---|---|
| `model/Castle.dff` | castle, 6 atomics (≤65535 vertices each), 122 k vertices / 86 k triangles, baked day + night vertex colours |
| `model/CastleGate.dff`, `model/CastleDoor.dff` | the arched gate leaf (2.0 m) and the interior door leaf (1.7 m × 2.2 m) |
| `texture/Castle.txd` | 18 textures, shared by the three models (DXT1; DXT5 only for web / orb / flame) |
| `collision/Castle.col`, `CastleGate.col`, `CastleDoor.col` | COL3: 2 449 boxes + a 1 968-face mesh for the castle (walls, floors, every stair step, towers) |
| `resource/Castle/` | ready-to-use MTA resource (copy the folder into `resources/`, `start Castle`) |
| `preview/*.jpg` | software renders (day and night) of the exterior and every room |
| `source/` | the generator (`build.py`), QC (`validate.py`), previews (`preview.py`), librw check, Lua smoke test |

## Use in MTA:SA
1. Copy `resource/Castle` to the server's `resources/` and run `start Castle`.
2. Stand on flat ground and type **`/showx`**: the castle appears 16 m in front of you, facing you; the entrance gate is
   at the bottom of the plinth stairs. Walk up — the gate (and every interior door) opens by itself when you are near and
   closes behind you. **`/hidex`** removes it.

### Replaced objects (important)
| ID | Original (all in Dillimore, one instance each) | Becomes |
|---|---|---|
| 12853 `sw_gas01` | petrol station | the castle |
| 12854 `sw_gas01int` | petrol station interior | gate leaf |
| 12855 `sw_copshop` | Dillimore police station | door leaf |

While the resource runs the three original Dillimore buildings are hidden (`removeWorldModel`), they come back when the
resource stops. Vanilla LOD objects of them may still be seen from far away. To use other IDs change `IDS` in `client.lua`,
`CFG` in `server.lua` and `ID_*` in `source/build.py`, then rebuild.
Settings (distance, admin-only, door speed/reach) are in the `CFG` table at the top of `server.lua`.

## Rebuild / check
```
cd source
python3 build.py          # writes model/ texture/ collision/ and resource/Castle/files + doors_data.lua
python3 validate.py       # DFF / TXD / COL structure + voxel walkability test (every room reachable on foot)
python3 mta_lua_test.py   # runs server.lua + client.lua against a stubbed MTA API (needs `pip install lupa`)
python3 preview.py day|night front,hall,...
sh tools/build_librw_check.sh && /tmp/librw_check model/Castle.dff texture/Castle.txd   # reference loader
```

## What was verified (and what was not)
* DFF / TXD / COL parsed by my own readers **and** by the reference RenderWare implementation (aap/librw): `source/librw_report.txt`.
* `validate.py`: 0 failures — all rooms, both floors of the wings, gallery, throne dais, keep spiral up to the observation
  floor, and all doorways are reachable by a 1.8 m walker over the collision geometry alone.
* The Lua resource was executed against stubbed MTA functions (commands, door open/close, hide/show, client load/restore).
* **Not tested inside the real game** (no MTA client in the build environment). Please send a screenshot / `debugscript 3`
  output if anything looks wrong.
* Place the castle on reasonably flat ground; the castle floor sits 1.5 m above the ground and the plinth is sunk 0.5 m into it, so uneven terrain may poke through or leave gaps.
