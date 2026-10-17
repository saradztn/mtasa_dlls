# Continuation v0.5 — interaction readiness, not complete games

## Implemented stations
`source_assets/interactions.json` and generated `shared/config.lua` define eight canonical zones:

| IDs | Purpose | Exclusivity |
|---|---|---|
| `TW_left_1` .. `TW_left_3` | Left tug stance reservations | One player per slot |
| `TW_right_1` .. `TW_right_3` | Right tug stance reservations | One player per slot |
| `GB_START` | Acknowledge arrival at bridge start | Multiple players |
| `EXIT` | Return to the saved pre-entry position/interior/dimension/heading | Not a seat |

A reservation does **not** move, rotate, snap, freeze or animate the player. The source-rig stance coordinates and approximate GTA ped positions remain references, not validated animation attachments. Holding a slot cannot be described as starting a tug round. Bridge readiness does not implement safe panels, turns, elimination or progression.

## Player tools
1. Enter using `/psg enter` after assets load. `/psg tug` and `/psg glass` remain exploration teleports with load acknowledgement.
2. `/psg_debug` toggles local floor guides: eight station outlines, source-facing arrows on tug slots and three canonical routes from the forecourt to the two tug approaches and bridge start. They are off by default and are immediate-mode diagnostic lines, not new world objects or a visual substitute for architecture.
3. In a station's approach radius, the HUD shows the action. Press **E** or run `/psg_use` to choose the server's nearest station. `/psg_use TW_left_1` requests that explicit canonical ID, still subject to server distance checks.
4. `/psg_release` releases your own reservation. Moving beyond the station's exit radius also releases it during the 500 ms maintenance check. Leave, load loss, invalid session, entering a vehicle, death, quit and resource stop clean up reservations.
5. `/psg_panelinfo` queries the canonical nearest panel within 2.5 horizontal metres and the configured vertical range. It reports its stable ID and current state without changing it. An arbitrary client-supplied panel ID does not override this selection.
6. `/psg_status` now also prints the local nearest station and acknowledged reservation.

The binding is configurable through `interactionKey` in `tools/build_runtime.py`. Set it to false to use commands only if another resource owns E. Chat input, console, main menu and a visible cursor suppress the interaction key. No game controls are disabled.

## Authority and state
`server/interactions.lua` requires a saved arena session, matching protocol/event source, ready client, correct dimension/interior, alive/on-foot state and finite position. It looks up positions/radii from server config rather than client coordinates, applies a 400 ms per-player request interval, and rejects unknown zones instead of silently selecting another one.

Destination validation happens before an old claim is replaced. A busy/invalid/far destination leaves the existing claim intact. Claims execute without yielding. A second player cannot acquire an occupied tug slot or release its owner by naming that slot. Bridge entry is deliberately nonexclusive. Slot snapshots contain occupancy booleans, not player identifiers, and are sent to eligible arena clients. A player may briefly see a stale occupied slot until maintenance or the next snapshot; no real networking timing was measured.

The client HUD is advisory. It is not authority, and a malicious client may falsify UI/readiness or cheat its own replicated movement. This resource is **not** an anti-cheat system. Native physics/streaming and real networking remain untested.

## Trusted server exports
- `setPanelState(id, "intact"|"marked"|"broken")` — existing trusted server mutation; remote clients have no panel-state mutation event.
- `getPanelState(id)` — state string or false. Does not return a mutable state table.
- `getInteractionState(player)` — a fresh `{zone=..., kind=...}` table or false.
- `getSlotOccupant(id)` — owner player element or false for canonical tug slots.

These readbacks are hooks for a future round/animation system, not a claim that one is implemented.

## Tests executed here
- Lua 5.1 execution of the actual main/state/interaction server scripts with multiple event handlers retained, rather than mocks accidentally replacing earlier handlers.
- Two-player contention, own-only release, copy-only state queries, stale/invalid destinations, finite/NaN/height/dimension/interior checks, protocol/source checks and cooldown.
- Automatic cleanup for movement, vehicle, load loss, proximity exit, death, quit and stop; maintenance timer removed on stop.
- Read-only nearest-panel lookup ignores arbitrary supplied IDs and does not mutate panel safety/state.
- Client canonical nearest-station selection, suppressed key while chatting, UI state validation, no world-element allocations in the draw path, and key cleanup.
- Eight nominal station footprints are sampled at 72 points against authored collision boxes. Three shared canonical tour routes are sampled at 1,752 points. These are not full approach-circle or player-capsule tests.
- Evidence: `tests/interaction_results.json`, `tests/client_results.json`, `tests/offline_results.json`. Client/server script hashes prevent silently reusing stale logic-test PASS results in the generated report.

## Still outstanding
No real MTA run, rendered HUD screenshot, engine physics test, genuine multiplayer/network run, shader compilation or performance measurement occurred. The previously generated 3D and motion inspection images remain Blender-only evidence. Full visual/reference fidelity and GTA retargeting remain PARTIAL as documented.
