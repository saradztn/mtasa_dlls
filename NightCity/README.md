# NightCity - an empty, rain-soaked futuristic megacity at midnight (MTA:SA resource)

A finished **Multi Theft Auto: San Andreas** map: a 1200 x 1380 m cyberpunk-style city at midnight in the rain - skyscrapers, wide avenues,
alleys, commercial and industrial districts, a river with five bridges, two elevated expressways, sky bridges and a 450 m road tunnel -
**with no people, no vehicles (not even flying ones), no bikes and no animals**.  Roads, pavements and plazas are clean and exposed, so the
city also works as a reference layout for an open-world map.

The only thing you need is the folder **`resource/NightCity/`** (45 MB).  Everything under `source/` is the generator that produced it and
can be deleted if you only want the map.

```
NightCity/
  resource/NightCity/      <- THE MAP. Copy this folder into  <server>/mods/deathmatch/resources/  and start it.
    meta.xml  client.lua  server.lua  tour.lua  wet.fx  post.fx
    models.lua  layout.lua  sprites.lua           (generated data: models, 398 placements, water, points, tunnel, tour, 3936 billboards)
    files/    203 x .dff + .col, 3 x .txd (95 textures), glow/steam sprites, 7 audio loops
  source/                  generator + validators (optional): build.py, nc/, lib/, validate.py, mta_lua_test_nc.py ...
```

## Install and use

1. Copy `resource/NightCity` into the server's `resources` folder, then `start NightCity` (MTA client **1.6.0-9.22676 or newer**, a DirectX 9 GPU
   with shader model 3 for the wet-ground shader; the rest runs without it).
2. In game type **`/ncshow`**.  The city is created high above the map (z = 900 m, so nothing of the vanilla world can touch it) and you are
   put at the spawn point.  `/ncshow here` builds it on the ground where you stand, `/ncshow x y z` at a position of your choice.
3. Walk around.  Everything has collision (streets, pavements, plazas, bridges, expressways, building bases, the tunnel).

| command | where | what it does |
|---|---|---|
| `/ncshow [here \| x y z]`, `/nchide` | server | show / remove the city (removing sends players in the sky to a safe place) |
| `/ncz <m>` | server | trim the height of the whole city by up to 8 m per call |
| `/ncempty on \| off \| now` | server | optional guard: removes vehicles and peds other resources spawn inside the city volume |
| `/nctour` | client | scripted camera flight: aerial, river, bridge deck, avenue, plaza, arcology, expressway, market, industrial, **through the tunnel** (Space stops it) |
| `/ncfree` | client | free camera (W A S D, mouse, Space up, C down, Shift fast, Ctrl slow) |
| `/ncview <point>` | client | teleport: spawn, plaza, avenue, market, quay, bridge, expressway, industrial, tunnel_in, tunnel_mid, tunnel_out |
| `/ncfx [0\|1\|2]` | client | 0 plain, 1 cinematic grade, 2 grade + wet reflective ground (default) |
| `/ncexposure <0.3-4>` | client | brightness of the grade (1 = as designed) - use it if your setup shows the city too dark / bright |
| `/ncrain <0-1>`, `/nctime <h>`, `/ncinfo` | client | rain / wetness, clock (the city is lit for midnight), status line |

## What is in the city

* **Plan**: 12 x 12 blocks on a non-uniform grid (avenues 36 m, streets 22 m, lanes 14 m), districts with their own look: glass **core**,
  the 397 m **arcology** (hero building) with its plaza gate, **entertainment** (neon, screens), parking **garages**, a dense **market** with 8 m
  alleys, **residential** slabs and mega-blocks, **waterfront**, and **industrial** zones (warehouses, factories, tank farm, container yards).
* **77 building models** in 14 archetypes (setback / cylindrical / twin towers, mid-rises, tenements with fire escapes, slabs, mega-blocks ...),
  lit from inside, with neon signs, digital billboards, LED strips, roof machinery, antennas, beacons.  Street lamps, signals, kiosks,
  benches, planters, steam vents, manholes, cables and utility poles fill the streets.
* **Infrastructure**: a river through the middle (12 water quads, quays with bollards and rails), **5 bridges** (4 girder + 1 cable-stayed hero
  bridge), **two elevated expressways** that cross at two levels, **3 glass sky bridges**, distant skyline strips on all four sides.
* **Road tunnel** (cut-and-cover underpass, 450 m): along the S street on x = 304 north of the river.  Open cuts with retaining walls,
  rails, sign gantry and portal header, then a 14 m x 4.8 m tiled box tube 6.5 m below the street: LED luminaires, jet fans, cable trays, SOS
  niches, lane-control signals, amber delineators.  It runs under two avenues, the lower expressway deck and a street.  Portals in city
  coordinates: y = 27 (south) and y = 477 (north).  The tunnel deliberately does not go under the river: San Andreas treats everything below a
  water polygon as water, so a tube below the river could put the player into swimming / underwater state.
* **Night, rain and atmosphere** (all inside the San Andreas engine): baked night vertex lighting, 3936 glow / steam billboards, fixed
  clock 00:30, rain storm weather, fog and a purple city-glow sky, lightning flashes with thunder, rain / wind / city hum / steam / neon buzz /
  tunnel drone audio, `wet.fx` (darker asphalt, puddles with rain rings, screen-space reflection of the lit city) and `post.fx` (bloom, grade,
  vignette, grain).  Vanilla birds and ambient sounds are switched off while the city is shown.
* **Empty by construction**: there is not a single person, car, bike, flying vehicle or animal model; `validate.py` checks all model, material
  and texture names against a word list.

## Honest limits - please read

* **Not tested inside a real MTA client.**  No MTA client was available while building this.  The Lua runs against a strict model of the MTA
  API (unknown functions, wrong argument types, wrong event names, wrong command argument lists, leaks and ordering errors all raise); the
  data files were parsed by the reference RenderWare loader (aap/librw) and by our own readers; the shaders were type-checked with the Slang
  compiler front-end.  What cannot be proven that way: real GPU shader compilation, real streaming / LOD behaviour, frame rate, exact brightness.
  If something misbehaves: `/ncfx 0` switches the shaders off, `/ncexposure` fixes brightness, `debugscript 3` shows the resource's messages.
* **The engine is San Andreas**: no real-time global illumination, volumetric light or dynamic shadows.  Lighting is baked into vertex colours
  (the engine's prelit pipeline); reflections are an approximation (screen-space, wet ground only); glow and steam are billboards.
* **Textures are 1K at most (DXT1)**, 95 procedural PBR-derived materials (17 MB).  4K / 8K textures are not practical in San Andreas
  (streaming memory, download size) and are not provided.
* Object count 398 (MTA streams about 600 ordinary objects at once), 516 k vertices in 203 models, draw distance up to 560 m (extended LOD) with
  fog hiding the rest.

## Rebuild and verify (optional)

```
cd source
python3 build.py                  # ~45 s, deterministic: rebuilds resource/NightCity byte for byte   (needs numpy, scipy, pillow)
python3 validate.py               # 161 structural checks on the finished files (no rendering of any kind)
python3 validate.py --lua --librw # ... plus the headless Lua session test and the reference RenderWare loader on every DFF
python3 mta_lua_test_nc.py        # 139 checks: show / draw frames / commands / tour / free cam / hide / re-show / stop + failure injection
python3 mta_lua_static.py         # every global in the Lua files exists in Lua 5.1 or in the real MTA client / server API
```
Optional extras: `pip install slangpy lupa luaparser` (shader type check, Lua runtime, Lua parser), `tools/build_librw_check.sh` (needs cmake, g++).

`layout.lua` is the machine-readable placement list (model, x, y, z, rotation, tag, in a city frame with z = street level), `models.lua`
the model table; both are generated.
