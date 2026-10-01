# GTA SA Real Node NPC AI for MTA:SA

`npc_ai` is an MTA:SA resource for pedestrian NPCs that uses the **authored GTA San Andreas path-node graph** (`nodes0.dat` … `nodes63.dat`) as its global navigation layer. It combines incremental A*, spatial lookup, streamed node chunks, native ped controls, local steering, wall/vehicle/ped avoidance, stuck/loop recovery, LOD scheduling, and syncer ownership.

> **Scope honesty:** this is an independent AI layer built on Rockstar's authored navigation data. It is not, and does not claim to be, a byte-for-byte recreation of Rockstar's internal AI.

## Research and data decision

The implementation was designed only after checking these sources:

- [GTAMods: Paths (GTA SA)](https://gtamods.com/wiki/Paths_(GTA_SA)) — the canonical binary layout used by the converter.
- [Leuansin/GTA-SA-Nodes-Json](https://github.com/Leuansin/GTA-SA-Nodes-Json) — audited as a useful lead, **not accepted as production ped data**.
- [MadGamerHD/GTA-SA-Path-Nodes-Editor](https://github.com/MadGamerHD/GTA-SA-Path-Nodes-Editor) — inspected for field coverage and compared against the binary specification.
- MTA documentation for [`createPed`](https://wiki.multitheftauto.com/wiki/CreatePed), [`setElementSyncer`](https://wiki.multitheftauto.com/wiki/SetElementSyncer), [`isElementSyncer`](https://wiki.multitheftauto.com/wiki/IsElementSyncer), [`processLineOfSight`](https://wiki.multitheftauto.com/wiki/ProcessLineOfSight), and [`downloadFile`](https://wiki.multitheftauto.com/wiki/DownloadFile).

### Why the external JSON is not used as the canonical input

The audited current JSON has only `x`, `y`, `z`, and `links`; it has no node type, area/node IDs, flags, width, flood-fill, link length, intersection data, or navi-link fields. Those omissions make it impossible to safely separate pedestrian nodes from vehicle nodes or preserve the native graph metadata.

Its bundled converter also does not match the documented native layout: it reads a two-byte link pool immediately after the header and treats header offset 12 (navi count) as link count. In the real format, nodes and 14-byte navi nodes come first, links are four-byte `(areaId,nodeId)` records, and link count is at header offset 16. Use the included audit command to reproduce the schema check:

```bash
python3 tools/convert_nodes.py --audit-json /path/to/nodes.json
```

This resource therefore treats **legally extracted original `.dat` files** as the source of truth. No GTA game data is redistributed in this repository.

## Native graph model

Each of the 64 areas is a 750×750 unit square, row-major from `(-3000, -3000)`. The converter parses:

- 20-byte header: total, vehicle, pedestrian, navi, and link counts;
- 28-byte path nodes, with position (`INT16 / 8`), width, flood fill, flags, area, node ID, link offset, and the two raw `UINT32` fields;
- 14-byte navi nodes and their direction/flags;
- four-byte area/node links, navi links, byte lengths, and intersection flags.

The generated chunk keeps pedestrian and vehicle records separate. Runtime A* traverses only `ped` records; vehicle/navi records are retained in each chunk unless `--ped-only` is intentionally requested. Path nodes are grouped by the header (`vehicle` first, then `ped`), **not** by inventing a type from an unrelated byte.

## Architecture

```text
npc_ai/
├── client/
│   ├── npc.lua          State machine, LOD scheduler, repath/stuck/loop logic
│   ├── movement.lua     Native ped control + interpolated facing
│   ├── steering.lua     Waypoint following and steering intent
│   ├── avoidance.lua    Five rays + local ped/vehicle separation
│   ├── animation.lua    Native locomotion animation-rate synchronization
│   └── debug.lua        3D graph/path/ray/state/profiler display
├── server/
│   ├── npc_manager.lua  Spawn/public API/admin commands
│   ├── npc_tasks.lua    Authoritative tasks and validated client events
│   └── npc_sync.lua     Nearest-player ownership / MTA syncer assignment
├── navigation/
│   ├── nodes.lua        Chunk streaming, nearest-node cache, node loader
│   ├── spatial.lua      Spatial-hash nearest and random-node lookup
│   ├── graph.lua        Ped graph and safe line-of-sight smoothing
│   ├── pathfinder.lua   Incremental non-recursive A* queue
│   └── cache.lua        Expiring start-node/goal-node path cache
├── shared/               Utilities, logger, profiler, network protocol
├── config/config.lua     All resource tuning
├── data/gta_nodes/       Generated manifest and streamed chunks
└── tools/convert_nodes.py
```

## Install

### 1. Put the resource in the MTA server

Copy this entire `npc_ai` directory to:

```text
<MTA server>/mods/deathmatch/resources/npc_ai/
```

MTA 1.6 is required because the ownership design uses `setElementSyncer` / `isElementSyncer` and dynamic file download.

### 2. Extract the original node files

From a legally owned GTA San Andreas installation, extract the original files from `gta3.img`:

```text
nodes0.dat
nodes1.dat
...
nodes63.dat
```

Put the extracted files into a local directory, for example `/srv/gta-sa-paths`. Do not replace this resource's scripts with game files, and do not commit the extracted game assets.

### 3. Convert and validate offline

Run this from the resource root:

```bash
cd <MTA server>/mods/deathmatch/resources/npc_ai
python3 tools/convert_nodes.py \
  --input /srv/gta-sa-paths \
  --output data/gta_nodes \
  --update-meta meta.xml
```

The command validates all 64 files before writing chunks. It rejects duplicate IDs, broken link ranges/targets, bad header counts, self-links, invalid coordinates, and suspiciously long links (as warnings). It writes:

```text
data/gta_nodes/manifest.json
data/gta_nodes/area_0.json ... area_63.json
data/gta_nodes/validation_report.json
```

It also inserts `download="false"` file entries in `meta.xml`. Chunks are then fetched only when a client needs their areas via `downloadFile`; they are not all parsed at resource start.

Use `--ped-only` only when you explicitly want to discard vehicle/navi records from the runtime export. The default preserves them.

### 4. Start

In the MTA server console:

```text
refresh
start npc_ai
```

If startup logs `No converted node areas found`, conversion has not completed or the generated `meta.xml` was not deployed.

## Public API

### Server-local handle API

```lua
local npc, err = NPC.create(7, 1482.0, -1742.0, 13.5)
if not npc then
    outputDebugString(err, 1)
    return
end

npc:startWander(300)
npc:setDestination(1367.0, -1280.0, 13.5)
npc:setSpeed(1.0)
npc:setAvoidanceEnabled(true)
npc:pause()
npc:resume()

outputDebugString(npc:getState())
local path = npc:getCurrentPath()
local currentNode = npc:getCurrentNode()
npc:stop()
npc:destroy()
```

Supported state values are `IDLE`, `WANDER`, `WALK_TO_NODE`, `FOLLOW_PATH`, `AVOID_OBSTACLE`, `WAIT`, `STUCK`, `REPATH`, `FLEE`, `CHASE`, `GO_TO_LOCATION`, and `RETURN`.

### Exported API for another resource

```lua
local ped = exports.npc_ai:createNPC(7, 1482.0, -1742.0, 13.5, {
    speed = 1.0,
    avoidance = true,
    walkingStyle = 128,
})

exports.npc_ai:startNPCWander(ped, 300)
exports.npc_ai:setNPCDestination(ped, 1367.0, -1280.0, 13.5)
exports.npc_ai:pauseNPC(ped)
exports.npc_ai:resumeNPC(ped)
exports.npc_ai:setNPCAvoidanceEnabled(ped, true)
```

Exports also include `destroyNPC`, `stopNPC`, `setNPCSpeed`, `setNPCBehavior`, `getNPCState`, `getNPCCurrentPath`, and `getNPCCurrentNode`.

`setNPCBehavior(ped, "return")`, `"chase"`, and `"flee"` are available server-side; CHASE/FLEE require `options.target` when set through the local `NPC` API.

## Commands

Commands that create/change NPC tasks are ACL-gated through `Config.security.commandACLRight` (default: `function.kickPlayer`). Configure a dedicated ACL right for production if preferred.

```text
/npcspawn [model] [count]       Spawn one or more managed NPCs near you
/npcwander [radius] [npcId]     Start graph-based wandering
/npcgoto <x> <y> <z> [npcId]    Set a node-projected graph destination
/npcstop [npcId]                Stop the selected NPC
/npctest [count]                Spawn a controlled wander stress test
/npcdebug [on|off|nodes|paths|rays|collision|labels|state|profiler]
/npcpath                        Toggle path rendering
/npcnodes                       Toggle nearby node rendering
```

`/npcdebug` is client-local and safe for normal players; it displays only streamed data.

## Runtime behavior

1. The server creates a synced ped and owns the authoritative task.
2. `npc_sync.lua` assigns the nearest same-world player within 90 units as MTA ped syncer.
3. That owner client dynamically downloads nearby node chunks and finds nearest **ped** nodes through the spatial hash; it never scans the full map.
4. Incremental A* is queued under a per-frame operation budget. Missing areas are downloaded and the request resumes; 50 agents do not all run A* in one frame.
5. Raw A* output is cached by `(startNode, goalNode)` and only smoothed when local collision data is known. A visibility shortcut is discarded if it risks crossing a wall.
6. The syncer holds native `forwards`/turn/walk controls. Position is never moved by `setElementPosition` or frame-by-frame teleportation.
7. Five bounded LOS rays and local ped/vehicle separation produce steering force, deceleration, local avoidance, and delayed repath for sustained blockers.
8. Position history detects stalls; recovery tries local side steps, alternate direction, a fresh nearest graph anchor, repath, then bounded wait/retry. It does not teleport a stuck ped.
9. Repeated node visits invalidate the route to prevent `A → B → C → A` loops.

## Performance tuning

All values are in `config/config.lua`.

- **LOD:** 20 Hz within 50m, 10 Hz within 150m, ~3 Hz within 300m, then sleep.
- **Avoidance:** rays run at 8 Hz / 4 Hz / ~1.7 Hz by LOD, not every render frame.
- **A*:** `operationsPerTick`, `operationsPerRequest`, `maxIterations`, and a FIFO scheduler cap route work.
- **Streaming:** only loaded areas are spatially indexed; old chunks are unloaded after inactivity under a memory cap.
- **Cache:** exact start/goal routes expire after `cacheTtlMs` and are bounded by `cacheMaxEntries`.

Use `/npctest 10`, `/npctest 25`, `/npctest 50`, then increase cautiously. Results depend on CPU, player placement, streamed collision, node density, and other resources; this project intentionally does not promise invented FPS/CPU numbers.

The debug profiler reports measured accumulated timing windows for Navigation, A*, Smoothing, Avoidance, Node Load, and NPC update work. It does not display hard-coded benchmark values.

## Debugging and troubleshooting

- **NPC does not move:** confirm it has a nearby player syncer, real node chunks exist in `meta.xml`, and the player is in the same dimension/interior.
- **`no start/goal ped node`:** inspect `validation_report.json`, node conversion paths, and the spawned position. The graph intentionally refuses vehicle-only nodes.
- **No direct wall shortcut:** expected. Smoothing is deliberately bounded and collision-checked near the local player.
- **Far-away paths pause:** expected. `processLineOfSight` only has reliable collision data around the local player, and chunks stream on demand.
- **MTA control replication:** MTA documents that client control states on non-local peds have synchronization limitations. This resource selects one actual ped syncer, validates owner events server-side, and lets only that client drive a ped. It does not falsely claim perfect native GTA network AI.
- **Commands denied:** grant the configured ACL right or change `Config.security.commandACLRight`.

## Offline tests

The tests generate synthetic binary fixtures only; they do not contain or require GTA assets:

```bash
cd npc_ai
python3 -m unittest discover -s tools/tests -v
```

They cover the documented section order, ped/vehicle separation, meta-file generation, broken-link rejection, and third-party JSON schema rejection.

## Security

NPC creation, destruction, task changes, client ownership, wander nominations, status reports, coordinate bounds, and event frequency are validated server-side. A client may nominate a wander node only while it is the server-selected MTA syncer, only for its wandering NPC, and only within the configured radius. No client event can create arbitrary NPCs.
