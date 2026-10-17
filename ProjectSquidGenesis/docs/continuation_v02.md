# Continuation v0.2 — 2026-10-17

## Runtime safeguards actually implemented
- Server stores a matching `PSG/0.2.0` readiness report per sender. Loading not complete / incorrect protocol → entry refused.
- Each `/psg enter|tug|glass` issues a distinct server request token, bound to that player and latest request. Client verifies its object instances/model list still exist before acknowledging.
- Server validates the sender, event source, exact token, readiness, five-second TTL, alive/on-foot status **again** before moving the player. Forged/stale/cancelled/expired requests never move players in the mock tests.
- Position/interior/dimension/rotation are captured immediately before the first committed move. Load failure reports and `/psg leave` restore them. Resource stop also restores active saved sessions.
- The pending request table holds at most one entry per player. Expiry is checked on acknowledgement, not a repeating timer. A timed-out request does not freeze/move the player and is replaced by the next command. Unsigned tick-wrap differences are handled.
- Panel snapshot requests require ready state. Trusted server panel-state exports remain unchanged.
- Failed quality TXD loads do not alter the selected quality. If native import fails during a switch, the previous dictionary is reapplied and the shader set is retained.

These guards address normal asset loading and accidental stale asynchronous requests. They do not certify engine collision readiness, and client readiness is not an anti-cheat attestation. No actual MTA runtime execution occurred.

## New authored geometry / material
- Slatted elevated maintenance galleries at 12 m, with side rails and supporting brackets.
- Repeated deep-shaft crossbraces on three vertical levels and visible maintenance ladders (no climbing mechanic).
- Floor seam strips, small bolt details, front hazard edge and dedicated capstan/collar at each actual rope endpoint.
- Recessed facade glass strips, mullion frames and corrected alternating facade accent colors. The prior parity-based pattern accidentally selected only one color because fin positions advance in even increments.
- Physically separate drain-grate bars and a four-row wayfinding atlas for both arenas and the entry.
- Blender UV display now flips the D3D/RenderWare V-down coordinates to Blender V-up, which is important for readable text.

## Verified here
- Rebuilt DFF/COL/TXD and regenerated `meta.xml`.
- Lua 5.1 syntax, expanded mock server handshake tests and client load/failure/quality tests.
- Offline route samples still pass; this is not capsule physics validation.
- Reopened both Blender projects; checked relative image paths and skinned reference structure.
- Reimported all 20 FBX clips and the combined action file again; animation tests still pass.
- Regenerated and inspected actual Blender exterior and tug views; glass view regenerated too. No claim of engine visual equivalence.

## Remaining gates
Shader compilation, real streaming/alpha sorting/physics, multiplayer integration, animator polish/retarget, reference fidelity and target hardware profiling remain as documented in `limitations.md`. The overall acceptance status remains PARTIAL.
