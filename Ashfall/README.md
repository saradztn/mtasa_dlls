# Ashfall - District Zero (MTA:SA resource)

<!-- Created by: Arena.ai Agent Mode (AI) -->
An abandoned post-apocalyptic district (340 x 340 m): 41 ruined buildings, 322 rusted cars, cracked streets with
sinkholes, props, overgrown vegetation and a ruined central park (lake, dry fountain, paths, gazebo, playground,
pier, dense trees). Everything is procedural (Python): textures, models, collision, baked lighting, audio.

## Install / use
1. Copy `resource/Ashfall` into the server's `resources` folder, then `start Ashfall`.
2. In game:
   - `/showcity` - the district appears 900 m above the map (nothing of the vanilla world can poke through it) and you
     are placed at the park's south entrance; you are held in place until the ground collision exists.
   - `/showcity here` - the district is built on the ground exactly where you stand (use flat ground; the park is 62 m ahead).
   - `/showcity x y z` - city origin at a world position.
   - `/hidecity`, `/cityz <m>` (trim the height), `/citywind` (optional leaf-sway shader),
     `/cityfx` (cinematic grade, ON by default: sharpen, bloom, desaturation, split tint, vignette, film grain).
   Models are allocated with `engineRequestModel` - no vanilla model is replaced.

## Contents
| folder | what |
|---|---|
| `model/`, `collision/`, `texture/` | 99 DFF + COL, 4 TXD (ground, flora, struct, props) |
| `audio/` | wind, rumble, crickets, creaks, birds, crow (synthesised) |
| `resource/Ashfall/` | meta.xml, models.lua, layout.lua (2257 objects), client.lua, server.lua, wind.fx, files/ |
| `preview/` | software renders of the finished layout (day and night) |
| `source/` | `build.py` (full rebuild, ~25 s), `validate.py` (QC of the shipped files), `mta_lua_test_af.py` (runs the real Lua with a stubbed MTA API), `prev_layout.py` (renders) |

## Rebuild / QC
```
cd source
python3 build.py && python3 validate.py && python3 mta_lua_test_af.py
W=1280 H=720 python3 prev_layout.py day aerial,street,park ../preview
```
Needs numpy, pillow, lupa.

## Realism pass
- Textures: photo grade (desaturated albedo, micro grain, unsharp contrast, tonal drift), 1024 px ground / facades, 512 px cars.
- Foliage cards drawn blade by blade / leaf by leaf with shading (see `source/af/real.py`).
- Baked sun shadows + horizon AO on the whole ground (`source/af/shadow.py`, 3 m ground resolution).
- Dirty uniform window glass, finer car paint, muted rust.
- `post.fx`: screen grade (needs a GPU with ps_2_0, i.e. any). `previews/*_graded.png` are a numpy approximation of it.

## Status
Phase 1 (one district) is complete and passes the offline QC. It has not yet been run inside a real MTA client:
please report anything odd (heights, missing objects, performance) after `restart Ashfall` + `/showcity`.

## Realism pass 3 (atmosphere + wasteland)
* **Frozen sky**: the game clock is stopped (`setMinuteDuration`) and re-enforced every second at 15:30; weather 15 (cloudy countryside, no heat haze), fog 380 m, far clip 800 m. `/hidecity` restores clock, weather, haze, fog and far clip.
* **Wasteland apron** (`source/af/apron.py`): 8 extra ground tiles (+-510 m) with rolling hills, collision, smooth earth / straw / green tinting, a gravel strip at the district edge, ~900 trees, ~1700 bushes / weeds / grass tufts, rubble, barricades and wrecks around the district. The district no longer floats over a void.
* Sky-mode guard now also brings back anyone who walks off the 510 m wasteland rim.
* The park is unchanged.

## Zombies (infected)
Server side `zombies.lua` + `zombie_nodes.lua`, client side `zombies_client.lua`. They appear when the city is shown (after a client reports `city:ready`) and are removed with `/hidecity`.

* **Skins (existing GTA:SA peds only, no custom models)**: 48 walker, 78 shambler, 79 runner, 80 brute. Everything per type (skin, hp, walking style, speed, damage, reach, sight, hearing, reaction time) is in `AF_ZTYPES` at the top of `zombies.lua`, so a skin can be swapped later with one number.
* **Nodes**: `source/af/nodes.py` (run by `build.py`) builds a 4 m walk-node graph (4322 nodes, 21078 links) from the city plan, the lake, the real collision shapes of every placed model and the building footprints. A* path finding runs on it (`AF_FindPath`).
* **AI**: idle -> wander (random destinations 25-90 m away) -> search (sound / last known position) -> chase -> attack. Sight = distance + view cone + 2D line of sight against the footprints; hearing = running / sprinting / gun shots (weapon dependent radius); reaction delay; horde alert; give up after ~6.5 s without contact; stuck detection (jump / side step / re-plan); fall guard.
* **Combat**: melee animation + damage (armour absorbs 60 % first, cars take damage), player hits are forwarded by the client (`zombie:hit`): stagger, aggro, head shot kills (brute loses extra hp instead), corpse removed after 20 s, respawn after 30 s out of sight (>= 40 m from every player).
* **Commands**: `/zombies [on|off|clear|status|count <n>|spawn <type|skin>]`, `/zombiedebug` (state labels above the zombies).
* **Events for development**: `zombie:spawned`, `zombie:killed`, `zombie:attack` (server).
* **Test**: `python3 source/mta_lua_test_zombies.py` runs the real Lua files against a stubbed server API with a simple movement simulation (spawn, patrol, sight, chase, attack, armour, path around a building, head shot, respawn, commands, hide).

## Border (mountains) and zombie hunting
* The wasteland rim (apron) is now a mountain range (70-120 m, `af/apron.py`). At its foot, 497 m from the city centre, a square ring of **invisible collision walls** (model `af_border`, 40 segments of 100 m x 1.5 m x 175 m, created by the clients with alpha 0) stops everyone.
* `boundary.lua` (server) is the same border on the server: a player who was inside and is found outside (square limit, more than 230 m above or 60 m below the city) is put back on his last good position, vehicle included; players teleported in from outside are not touched.
* Zombies hunt: every player within `AF_ZCFG.HUNT_RADIUS` (80 m) is felt through walls and chased along the node graph; beyond that they use sight and hearing. `ZONE` = 505 m, so they follow players over the wasteland up to the border. `/zombies` commands unchanged.
