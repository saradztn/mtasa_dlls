# GTA SA Real Node NPC AI for MTA:SA

`npc_ai` is an MTA:SA resource for pedestrian NPCs. It uses a **real GTA San
Andreas pedestrian navigation graph** as its global route layer, not generated
grids or random XYZ movement. It combines streamed graph chunks, spatial
nearest-node lookup, cached incremental A*, native ped controls, local
steering, wall/vehicle/ped avoidance, stuck/loop recovery, LOD scheduling, and
syncer ownership.

> **Scope honesty:** this is an independent AI layer built on real GTA SA
> pedestrian-graph topology. It is not, and does not claim to be, a byte-for-byte
> recreation of Rockstar's internal AI.

## Ready-to-run bundled graph

**No GTA files, converter run, or separate download is required.** Copy this
entire directory to your MTA resources folder and run `start npc_ai`. The
resource includes 64 on-demand area chunks and a manifest containing **37,650
real pedestrian nodes and 80,686 validated directed links**. Empty areas are
included explicitly, so they are not mistaken for missing downloads.

The bundle is imported from the MIT-licensed pedestrian-only `pedpaths.json`
export in [`ryrntjy9bp-lab/pedestrians-build`](https://github.com/ryrntjy9bp-lab/pedestrians-build),
pinned to commit `83594e793b148d035974aa8bd3078fddad1f2fc3`. Before bundling,
the importer verified unique IDs, GTA's `area * 65536 + localNodeId` encoding,
finite coordinates, existing targets, no self-links, and reciprocal topology.
The input SHA-256, full source notice, verification summary, and metadata
limits live in [`data/gta_nodes/`](data/gta_nodes/README.md).

### Metadata limitation, stated precisely

This ready graph preserves the real pedestrian coordinates, global/local IDs,
area mapping, and links available from that source. It is **not represented as
a full raw `nodes*.dat` export**: the source does not provide native path
widths, raw flags, link-length bytes, intersection flags, navi links, vehicle
nodes, or navi nodes. Where a native edge length is absent, runtime A* uses its
geometric cost. It never claims unavailable metadata is original.

The included `tools/convert_nodes.py` remains the full-fidelity optional
converter for a server operator who has legally extracted original GTA SA
`nodes0.dat` through `nodes63.dat` and needs those native fields. Running it
will replace the bundled chunks; it is not a prerequisite for normal use.

## Research references

The implementation and optional native converter were designed after checking:

- [GTAMods: Paths (GTA SA)](https://gtamods.com/wiki/Paths_(GTA_SA)) — native
  binary layout used by `convert_nodes.py`.
- [`ryrntjy9bp-lab/pedestrians-build`](https://github.com/ryrntjy9bp-lab/pedestrians-build)
  — the pinned, MIT-licensed source of the bundled pedestrian-only topology.
- [MTA `createPed`](https://wiki.multitheftauto.com/wiki/CreatePed),
  [`setElementSyncer`](https://wiki.multitheftauto.com/wiki/SetElementSyncer),
  [`isElementSyncer`](https://wiki.multitheftauto.com/wiki/IsElementSyncer),
  [`processLineOfSight`](https://wiki.multitheftauto.com/wiki/ProcessLineOfSight),
  and [`downloadFile`](https://wiki.multitheftauto.com/wiki/DownloadFile).

## Native graph model (optional converter)

For a legal, locally extracted native corpus, the optional converter parses all
64 GTA SA 750×750-unit areas, row-major from `(-3000, -3000)`, following the
native layout:

- 20-byte header: total, vehicle, pedestrian, navi, and link counts;
- 28-byte path nodes, including position, width, flood fill, flags, area/node
  ID, link offset, and raw `UINT32` fields;
- 14-byte navi nodes and their direction/flags;
- four-byte area/node links, navi links, byte lengths, and intersection flags.

Its native chunks retain pedestrian and vehicle records separately. Runtime A*
traverses only `ped` records; vehicle/navi records are retained unless
`--ped-only` is explicitly requested. Path nodes are grouped by the native
header (vehicle first, then pedestrian), never inferred from an unrelated byte.

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
├── data/gta_nodes/       Bundled manifest, 64 streamed chunks, provenance
└── tools/
    ├── convert_nodes.py       Optional full native DAT converter
    └── import_pedpaths_json.py Reproducible bundled-graph importer
```

## Install — two commands, no conversion

1. Copy the entire `npc_ai` folder to:

   ```text
   <MTA server>/mods/deathmatch/resources/npc_ai/
   ```

2. In the MTA server console run:

   ```text
   refresh
   start npc_ai
   ```

MTA 1.6 is required because ownership uses `setElementSyncer` /
`isElementSyncer` and streamed chunks use `downloadFile`. At successful client
startup, the log reports `Manifest loaded (64 streamed areas)`. There should be
no `No converted node areas found` warning.

### Optional: replace the bundled graph with your legal native DAT conversion

This is **not needed for normal installation**. It is only for operators who
want to replace the included ped-only bundle with a full native conversion:

```bash
cd <MTA server>/mods/deathmatch/resources/npc_ai
python3 tools/convert_nodes.py \
  --input /srv/gta-sa-paths \
  --output data/gta_nodes \
  --update-meta meta.xml
```

The converter validates all 64 source files before writing chunks. It rejects
duplicate IDs, broken link ranges/targets, bad header counts, self-links, and
invalid coordinates; it then updates the dynamic `<file>` block in `meta.xml`.
Do not commit or redistribute legally extracted GTA binary files.

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

- **NPC does not move:** confirm it has a nearby player syncer, the 64 bundled chunk entries remain in `meta.xml`, and the player is in the same dimension/interior.
- **`Config` or `NPCProtocol` is nil on the client:** deploy this revision's `meta.xml` together with the scripts and restart the resource. Its foundation files are explicitly loaded as ordered client scripts before `client/npc.lua` and `client/debug.lua`; do not mix it with an older meta file.
- **`No graph area entries found`:** reinstall the complete `data/gta_nodes` directory and retain all 64 `<file>` entries from `meta.xml`; conversion is optional, not required.
- **`no start/goal ped node`:** inspect `data/gta_nodes/validation_report.json` and the spawned position. The bundled graph is ped-only; it intentionally does not route over vehicle nodes.
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

They cover the documented native section order, ped/vehicle separation, meta-file generation, broken-link rejection, third-party JSON schema rejection, bundled graph topology, and explicit client/server foundation ordering.

## Security

NPC creation, destruction, task changes, client ownership, wander nominations, status reports, coordinate bounds, and event frequency are validated server-side. A client may nominate a wander node only while it is the server-selected MTA syncer, only for its wandering NPC, and only within the configured radius. No client event can create arbitrary NPCs.
