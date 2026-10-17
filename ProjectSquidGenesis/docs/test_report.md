# Test report — 2026-10-17 / build 0.6

## Overall: PARTIAL
Full user acceptance is **not achieved**. Files are real, but no MTA client/server or D3D9 compiler ran here. No FPS/VRAM measurements were made.

## Executed offline evidence
| Test | Status | Actual result |
|---|---|---|
| XML and resource dependency closure | PASS | 139 |
| DFF and COL parser roundtrip, UVs, finite unit normals | PASS | {'models': 11, 'unique_triangles': 72816} |
| Rope LOD geometry and matching centreline | PASS | {'near_triangles': 17280, 'distant_triangles': 1920, 'triangle_reduction_percent': 88.88888888888889, 'same_authored_length_and_sag': True, 'scope': 'Authored geometry count, not measured FPS'} |
| Native TXD mip chains and map dimensions | PASS | {'checked_map_images': 96, 'dictionaries': 3} |
| Lua 5.1 syntax | PASS | All Lua scripts compiled with Lua 5.1 (not MTA execution) |
| Entry-to-platform collision corridor samples | PASS | {'floor_samples': 1752, 'note': 'Axis-aligned source collision boxes only. Full MTA capsule/streaming NOT TESTED.'} |
| Tug source-rig anchor alignment | PASS | Six source-rig anchors put both palm-centre proxies on the straight platform rope; GTA ped offsets/mesh contact NOT TESTED |
| Interaction station schema and nominal floor footprints | PASS | {'zones': 8, 'canonical_centre_footprint_samples': 72, 'scope': 'Source collision boxes around canonical centres, not full approach radius or MTA capsule physics'} |
| Server authority logic (mock APIs) | PASS | Mocked ready gate, protocol/source rejection, request-token acknowledgement, stale/expired/cancelled requests, vehicle race, load-loss rollback, restoration, ACL panel states and throttled snapshot |
| Mock client lifecycle/failures | PASS | 45 objects / 11 allocated IDs / 16 shader instances; panel collision state update; quality cycling has stable live-resource count after cache warmup; stop leaves zero tracked elements/models/timers; shader allocation failure falls back to geometry; COL failure rolls back loaded elements and model IDs; client acknowledges only matching protocol with live world; lost world sends not-ready; no teleport acknowledgement; failed tier load retains old quality; quality command is disabled after failed startup; rope LOD hysteresis retains object identity and live resource count; rope LOD model-switch failure retains old tier; native tier import failure rolls back every ID; rollback failure disables entry and reports load loss; texture/parameter/binding failures destroy partial material resources; nearby interaction uses canonical ID and suppresses key while chatting; slot/reply HUD state validation and zero element allocations in draw path; interaction key unbound and local state cleared on stop; disabled/failed key binding keeps manual-command fallback and cleanup; non-resource reply/slot source rejected; console/menu/cursor suppress use |
| Mock light-slot stability | PASS | stable source identity under rank-boundary hysteresis; all source-position changes occur at zero slot intensity; fixture positions remain exact, not interpolated through space; slot colors equal source color times bounded fade weight; no duplicate selected source IDs; inactive colors reset to zero; LOW settles to its configured light budget; outside-dimension early return and explicit reset |
| Mock interaction/session authority | PASS | managed-session/ready/dimension/interior/on-foot eligibility; protocol and event-source rejection; invalid/remote/NaN/height checks with canonical positions; two-player exclusive slot contention and own-only release; unknown destination does not select nearest or drop an old claim; copy-only state query prevents external table mutation; request rate limit including signed tick transition and release-on-drift/vehicle; nonexclusive bridge entry acknowledgement; nearby panel readback ignores arbitrary requested IDs; no client mutation; load-loss/exit/death/quit/stop cleanup restores session and releases slots; multiple event handlers retained in mocks; timer removed on stop |
| Facade helper geometry/inventory | PASS | positive analytic volume and closed consistently oriented edges on chamfer extrusions; closed sloped blades have positive thickness and finite UVs; invalid/NaN bevel dimensions rejected; detail inventory present; original 11 model assets and 36 panels preserved |
| Saved Blender sources reopened | PASS | 46 meshes (45 visible placements + 1 hidden LOD template); 20 Actions; 26 bones / 18 deform; relative textures resolve |
| Environment mesh/source correspondence | PASS | 142888 vertices and 72816 triangles, all material slots/indices and UVs match authored mesh data; runtime hashes recorded. Not engine compatibility. |
| FBX export/reimport | PASS | 20 individual files contain animated tracks/keyframes and distinct sampled motion; combined file contains 20 Actions. Finite transforms, stable scales, exact spans and loop endpoint continuity tested. |
| Reference mannequin skin under actor transforms | PASS | 2040 segment-pose samples; segment centroids follow source bone centres under identity and translated/rotated actor transforms. This is not continuous-skin or GTA-character validation. |
| Source animation GIF provenance | PASS | Actual rendered source-rig GIFs match the current source/image hashes. Human pose/animation review is still required. |
| Animation contact contracts | PASS | 20 source actions + 20 FBX reimports checked against wrist/ankle/root targets, declared planted sole-proxy windows and held-grip centre lines. Tolerance 2 mm; ten transition pairs are also checked on source and FBX deform matrices. Walk requires explicit +0.88 m/cycle actor drive. Not skinned sole/finger/collision or biomechanical approval. |
| Inspection render provenance | PASS | 4 actual Cycles outputs match the current saved scene, material inputs and recorded image hashes. The close facade view uses neutral diagnostic fill; the other views retain scene fixtures. This does not validate MTA visuals or AAA fidelity. |

An environment-only or skip-Blender build retains earlier animation/FBX/contact evidence only while recorded hashes match; those rows do not imply that animation tests were rerun during packaging.

## Incomplete / unexecuted gates
| Gate | Status | Reason |
|---|---|---|
| MTA streaming, DFF/COL engine compatibility, D3D9 shader compilation | BLOCKED | No target MTA/DirectX graphics runtime |
| Actual glass sorting, collisions, jumps and multiplayer traversal | NOT TESTED | Offline parsers and API mocks cannot exercise the engine |
| Reference fidelity / AAA finish | PARTIAL | Layout is recognizable; architecture, weathering, materials and lighting still need artist refinement |
| Biomechanics / actual skinned-foot and finger contact | NOT TESTED | Proxy kinematic contacts pass, but do not establish biological realism, skin collision or finger grasp |
| GTA retarget and IFP playback | BLOCKED | Exact target skeleton/conversion workflow not supplied; no IFP conversion attempted |
| FPS / VRAM / target hardware profiling | NOT TESTED | No target client/GPU session |

## Authored counts (not measured engine draw calls)
- 11 DFF/COL pairs, 72816 unique exported triangles across all models, including both mutually exclusive rope tiers.
- 45 persistent placed objects, including 36 independently identified panels. One rope object switches its model; it is not duplicated for LOD.
- Cable high/low: 17,280 / 1,920 triangles (88.9% authored cable-triangle reduction). This is not an FPS result.
- 16 material families; 48 source material maps, 96 runtime normal/packed-surface maps, three mipmapped TXDs.
- 20 individual animation FBX plus one combined file; two editable Blender projects.

## Fixes and additions actually tested
1. Source/FBX files are reopened; cached PASS evidence must match their current hashes before report generation.
2. Canonical tour routes from the interaction configuration are sampled against collision boxes; entry and landing gaps were corrected. This is not full capsule physics.
3. Initial dark inspection lighting and embedded columns were corrected; elevated galleries, braces, collars and wayfinding were added.
4. Client load gate, per-request acknowledgements and stale/expired/cancelled request rejection are exercised in Lua mocks.
5. Quality switches cache native dictionaries. Failed imports reapply all old dictionary bindings; rollback failure disables entry and sends a load-loss report.
6. Failed shader allocation, normal/surface allocation, parameter binding and world-texture binding destroy partial graphics elements and report fallback, not success.
7. Rope LOD uses a distance hysteresis band and reuses one object; model-switch failure preserves the tracked tier.
8. Light slots retain exact fixture positions. Hysteresis and intensity fades ensure a source changes only at zero slot intensity; disabled slots are explicitly zeroed.
9. Corrected local-vs-world root translation, unreachable poses and inherited foot twist; added calibrated elbow/knee poles and world-oriented hand/foot controls.
10. Contact tests initially detected a 2.5 mm source probe reach error; the probe range was reduced to be reachable. FBX comparison also exposed Blender import default +1-frame offset; imports now explicitly use zero offset and exact frame spans.
11. Walk contact checks include the declared external actor drive; jump preparation and landing have explicit planted windows.
12. Visual inspection exposed unparented reference-mesh segments deforming incorrectly under external actor translation. Reference meshes are now parented to the rig and 2,040 transformed segment poses are checked. Preview GIFs were regenerated with this corrected skin binding.
13. Added six mutually exclusive tug reservations, nonexclusive bridge entry and proximity exit; server validates canonical positions/session/type/cooldown, checks contention and releases on drift, vehicle, load loss, death, quit and stop.
14. Added read-only nearest-panel inspection, optional local station HUD/debug lines and client key cleanup; no round/force/animation controller is claimed.
15. Replaced selected facade box silhouettes with real chamfer extrusions, added 13 framed closed-blade louvers, four rainwater stacks, coping, horizontal reveals and canopy ribs. Environment source validation now compares every vertex, triangle, material and UV against exported authoring data. Animations were deliberately retained unchanged.

## Reproduction
`python tools/build.py --render --package` performs the complete rebuild, source/FBX/contact verification, Lua tests, renders, report and ZIP. `--skip-blender` skips rebuilding/retesting Blender sources and FBX; pre-existing evidence must still match the stored source/FBX hashes.
Optional GIFs: add `--animation-previews` to the build. Individual tests: `validate_animation_contacts.py`, `validate.py`, `test_client.py`, `test_lighting.py`, `test_interactions.py`, `test_architecture.py`, `validate_sources.py`, `validate_fbx.py`. Evidence is in `tests/*_results.json`; asset hashes are in `tests/asset_checksums.json`.

## Windows MTA acceptance checklist (unchecked)
- Enable debugscript 3; verify each shader technique and model/COL load result.
- Inspect both rope tiers and threshold switching, including model binding failures, without assuming API mocks prove visual correctness.
- Test glass transparency from above/below, every panel collider, jumping and hall culling.
- Test two clients, reconnect snapshots, ACL allow/deny, failed downloads, load-loss restoration, cancellation and resource stop.
- Check lighting transition pacing and source selection inside each hall; inspect wall light bleed and weather-resource conflicts.
- Retarget/polish animations and profile LOW/MEDIUM/HIGH on target hardware before accepting the final scene.
