# Continuation v0.3 — performance & graphics failure handling

## Cable LOD
The near cable remains three genuinely helical swept strands (17,280 triangles). The distant cable is a 12-sided lobed sweep with 80 segments, the same 40 m extent and 0.16 m centre sag (1,920 triangles). Fine helicity at a distance is approximated by the rope material. This is an **88.9% reduction in cable model triangles**, not a measured frame-rate or overall-scene improvement.

Only one rope object is placed. Both models are loaded once; the object changes its model in the existing 250 ms update timer. No new object, shader, TXD or texture is allocated during LOD updates. LOW always chooses the simpler cable in the arena. MEDIUM switches to high within 14 m and low beyond 20 m; HIGH uses 24/32 m. The intervening band retains the current tier. Distance is measured to the sagging cable segment rather than its midpoint. This is a close geometric approximation, not an exact minimizer of distance to the curved surface.

The new `rope_low` source object is deliberately hidden in Blender render/viewport and has no runtime placement. Unhide it and hide `rope` to inspect it. Runtime model-switch failure logs an error and retains the tracked tier. Both tiers are non-colliding; no rope physics is simulated. The abrupt silhouette/UV LOD change itself is not cross-faded and needs target-client visual review.

## Stable local-light slots
At most four shader slots still approximate local illumination. Already-selected fixtures get a 20% squared-distance ranking preference to reduce boundary churn. Slots retain their source identity if still selected. Replaced slots first fade to zero over approximately 0.6 seconds, then change to the new **exact fixture position**, then fade back in. No light is moved through imaginary positions between fixtures. Missing/disabled slots explicitly receive zero color. This prevents a hard intensity/source jump in the tested logic but may produce temporary dimming. Ranking remains camera-based, unshadowed and spatially approximate; it does not solve wall bleed or reflect scene geometry.

Lua tests check hysteresis, bounded weights, exact source positions, zero-intensity source changes, unique slot source IDs, disabled colors, LOW light budget and cleanup. These tests do not render the shader.

## Graphics error paths
Each material checks shader creation, normal/surface allocation, required parameter bindings and application to its objects. If any stage fails, partial shader/map elements are destroyed and a `fallback` status/reason is recorded. A created shader is no longer sufficient to be reported active. Runtime `/psg_status` prints readiness, quality, object/model counts, active/fallback material counts and rope tier. It reports no invented performance data.

Quality native-dictionary import failures reapply the old dictionary to every model ID. If rollback itself fails, the client disables entry and reports asset loss so the server restores an existing session. Geometry is retained until resource cleanup; native bindings may be inconsistent and a restart is required. Mock tests exercise both successful rollback and rollback failure.

## Acceptance boundary
All source/game assets are rebuilt and parser-checked; editable projects and FBX are reopened. Windows MTA compilation, engine texture/model switching, light appearance, collision streaming, multiplayer traversal, GPU memory and FPS are still **not tested here**. See the current test report rather than treating these offline improvements as final acceptance.
