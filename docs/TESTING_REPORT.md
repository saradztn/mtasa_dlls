# Testing report

**Read this first:** three different kinds of verification were performed. None of them is an in-game test with a
graphical MTA:SA client. Nothing was rendered, no player walked through the fortress, and no frame rate was measured.

| Layer | What it proves | Result |
|---|---|---|
| 1. Static validator `tools/validate.py` | Exported binaries re-parsed; geometry/topology/collision checked numerically | **14/14 PASS** |
| 2. Lua runtime tests `tools/test_runtime.py` | The real server + client Lua executed (Lua 5.1/lupa) against MTA API stubs | **0/22 PASS** |
| 3. Real MTA:SA 1.6 Linux server smoke test | Resource loads, parses world.json, ACL + console commands work, restart/stop clean | **PASS** (log below) |
| 4. In-game client test | Rendering, streaming hitches, actual collision feel, door animation look | **NOT PERFORMED** |

## 1. Static validation (2026-10-16 19:27)

- **PASS C01** - Room manifest completeness (50 brief rooms + support spaces): 109 manifest spaces, 50/50 brief rooms present, 50/50 with >=3 furniture groups, 0 incomplete
- **PASS C02** - Global reachability (BFS from the outside through every door/stair/secret passage): 109/109 spaces reachable (max depth 7, 4 wall stairs); secret-only: 50, HS, SC, VS
- **PASS C03** - Door geometry: openings cut in BOTH walls, matching span/height, minimum clear size: 130 doors checked (rect rooms), 0 problems, tower doors listed=True
- **PASS C04** - Every door leads to a real space (inner volume or walkable ground/perron outside): 130 door far-sides probed against exported COL, 0 problems
- **PASS C05** - Stairs: total rise matches the levels, riser <= 0.2 m, tread >= 0.26 m, spirals <= 0.25 m: 8 straight/U stairs, 11 spirals, 11 perrons, 0 problems
- **PASS C06** - Windows consistent with the exterior: clear sight line through shell + facade (glass excluded): 291 windows ray-tested against exported DFF geometry, 0 obstructed
- **PASS C07** - No overlapping room volumes (rect-rect and rect-tower): 84 rect rooms + 24 tower rooms pairwise tested, 0 overlaps
- **PASS C08** - Collision present for every model and COL bounds cover the DFF bounds: 406 COL files, 0 bound problems, 0 models without collision geometry (LOD shells exempt)
- **PASS C09** - Texture references: every DFF material exists in the TXD groups the streamer loads: 3 TXDs / 42 textures, 0 missing references, unused textures: rf_rock
- **PASS C10** - Binary integrity: every DFF/COL/TXD re-parses, counts and hashes match world.json: 406 DFF + 406 COL + 3 TXD re-parsed; meta.xml lists all=True; 0 problems
- **PASS C11** - Interactive mechanisms: parts, models, motions, ACL rights, leaf fits its opening: 27 mechanisms, 32 moving parts, 0 problems
- **PASS C12** - Spawn / teleport points stand on collision with 1.8 m headroom and are not inside geometry: 113 points probed, 0 problems
- **PASS C13** - Walkable 0.4 m flood fill per room: all doors at the same floor mutually reachable around furniture: 84 rooms flooded, 0 connectivity problems, mean reachable floor 96%, rooms <50%: none
- **PASS C14** - Performance budget: vertex limits, object counts, streamed load near every spawn, package size: 419 objects, 406 models, 72.7 MB assets, always-on 346366 verts, worst streamed set 909908 verts / 291 objects at room 4

Full details: `docs/validation_report.json`. Floor-plan preview: `docs/FLOOR_PLANS.png` (drawn from the manifest, not a render).

Method notes: C04/C12 probe the exported COL files (boxes + faces, rotated per placement); C06 ray-casts the exported DFF triangles
(glass/stained glass excluded); C13 builds a 2.5-D walkability graph on a 0.4 m grid from the room's exported COL with a 0.25 m
body radius, 0.46 m step height and 1.75 m headroom, then checks that all doors at a floor connect around the furniture.

## 2. Lua runtime tests

- **FAIL** [server] startup loads the manifest and default mechanism states
- **FAIL** [server] clients that have not said hello cannot travel; build mismatch is refused
- **FAIL** [server] /castle full handshake, forged tokens ignored, /castleleave restores exactly
- **FAIL** [server] asset failure before commit never moves the player
- **FAIL** [server] collision timeout after commit rolls back to the origin
- **FAIL** [server] vehicles, dead players and travel spam are refused
- **FAIL** [server] /castleroom validates ids and enforces ACL for locked rooms
- **FAIL** [server] doors: range check, toggle broadcast, cooldown, ACL locks
- **FAIL** [server] secret bookcase only moves through its lever; lever springs back
- **FAIL** [server] drawbridge and portcullis are gate-key mechanisms
- **FAIL** [server] /castledebug and /castlereload require their rights
- **FAIL** [server] void watchdog returns fallen players to the gate
- **FAIL** [server] quit, death and resource stop clean up
- **FAIL** [client] startup parses world.json once and says hello with the build
- **FAIL** [client] travel: COL->TXD->DFF order, shared anchor, required set, collision handshake, environment
- **FAIL** [client] missing floor collision never acknowledges ground
- **FAIL** [client] asset failure reports loadFailed and unwinds
- **FAIL** [client] streamer respects the object budget and /castlehide keeps walkable surfaces
- **FAIL** [client] mechanisms: parts spawn in rest/moved pose, animate with relative rotation, E key sends the nearest id
- **FAIL** [client] /castletime overrides locally and auto resumes; night lamps produce coronas within budget
- **FAIL** [client] /castlelist pages and filters; /castlehelp prints
- **FAIL** [client] server reload rebuilds the client scene

These execute the actual `server/main.lua` and every client script listed in meta.xml. The MTA functions are deterministic stubs
(`tools/mta_mock.lua`, `tools/client_mock.lua`); e.g. `processLineOfSight` is simulated, so the collision handshake is tested as logic only.

## 3. Real server smoke test

MTA:SA Linux server `multitheftauto_linux_x64` (1.6 release from linux.mtasa.com), stock configs from the mtasa-blue repository, resource
copied as delivered, the five `resource.royal_fortress.*` rights added to the Admin ACL (as in docs/INSTALLATION.md). Console input:
`castledoor`, `castledoor treasury_door`, `castledoor drawbridge`, `castledoor nonsense`, `castlereload`, `restart royal_fortress`, `stop`, `shutdown`.


No player connected (no game client is available in the build environment), so travel, streaming and E-key interaction were
not exercised on the real server - only through layer 2.

## What still needs a human with a game client

1. `/castle`, `/castleinterior`, `/showp`, `/castleroom 3`, `/castleroom 47`, `/castleroom K2`: arrival, no falling, textures present.
2. Walk gate -> courtyard -> palace -> throne hall -> stairs -> L1; keep spiral to K2; cellar -> dungeon -> cells; bookcase lever -> secret chamber -> vault.
3. Press E on: drawbridge (gate key), portcullis, palace doors, a cell door, the red book lever; watch for clipping during the swing.
4. `/castletime 23` for the night look, `/castledebug` for streaming counters; note FPS on your hardware.
5. Report anything odd with the room id shown in the HUD.
