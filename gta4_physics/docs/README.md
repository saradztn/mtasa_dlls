# GTA IV-style vehicle physics emulator for MTA:SA

**Resource name:** `gta4_physics`  
**Version:** 0.1.0  
**Minimum MTA:SA:** 1.6.0 r22864 on both client and server  
**Scope:** a public-API-only, editable *style emulation* layered over the MTA vehicle solver. It is not an exact GTA IV/RAGE port, and it does not use or require `handling.dat`.

Every vehicle value supplied here is a documented or explicitly **estimated** starting value. GTA IV model-specific internal handling values are not exposed by MTA and are not represented as recovered facts. The resource makes no claim of 100% GTA IV fidelity.

## Resource layout

```text
gta4_physics/
  meta.xml            client/server script manifest (min MTA 1.6.0 r22864)
  config.lua          every tuning knob, profile multipliers and profile list
  client.lua          client startup/shutdown and the two exported functions
  server.lua          server startup/shutdown for validation + telemetry relay
  data/               editable estimates: class baselines, per-model rows, surfaces
  physics/            forces, weight transfer, suspension, tire model, steering,
                      transmission, drivetrain, braking, aero, collision, core loop
  mta/                adapter (state/controls/handling), manager (LOD + events),
                      synchronization (server validation, smooth correction)
  systems/            performance/LOD budgets, telemetry recorder, calibration
  debug/              overlay, 3D wheel-force visualiser, command handlers
  docs/README.md      this document
  tools/              development-only offline checks (not used by the game)
```

## Install

1. Copy this entire `gta4_physics/` directory into the server's `resources/` directory (or an installed resource package).
2. From the server console, run `refresh`, then `start gta4_physics`.
3. Join with a supported vehicle as its driver. The resource applies a blended native-handling base and activates the custom FULL LOD only for the local driver/syncer.
4. Use `/gta4help` in-game. To remove the emulator, run `stop gta4_physics`; the client restores the handling values it captured on entry/resource start.

There are no external executables, DLL injection, memory access, shaders, replacement game files, or cloud services. Only documented MTA Lua APIs are used. The resource needs the listed minimum build because its client code uses angular-velocity APIs added in r22864; wheel-contact and material-property queries have older introduction builds.

## What it does

- Expands 137 model-specific starting estimates across compact, sedan, coupe, sports, super, muscle, SUV, off-road, van, truck, bus and motorcycle classes. Entries carry `estimated = true`; each model has its own expanded editable record and model-specific modifiers.
- Keeps vehicle parameters in `data/vehicle_classes.lua` and `data/gta4_vehicle_database.lua`, rather than embedding handling values in `physics/physics_core.lua`. Edit a class baseline for a broad change, or edit that model's row in the database catalog for an individual change. All rows are estimates and should be treated as tuning seeds.
- Reads driver controls and MTA vehicle state, then advances a bounded fixed-step model. The native MTA solver remains active; a bounded correction is applied to velocity and angular velocity only while the local player controls/syncs the vehicle.
- Models per-wheel longitudinal/lateral slip, combined-slip force limits, load-sensitive grip, front/rear drive share, dynamic four-corner loads, spring/damper travel, steering response, automatic gearing, torque/RPM, engine braking, brake bias and ABS-style pressure release.
- Samples a local surface material sparsely, reads documented surface grip properties when available, and blends road grip with the MTA rain level. The surface ray can miss unloaded world areas, in which case the asphalt fallback is used.
- Estimates aerodynamic drag/lift/downforce, rolling resistance and mass-aware impact severity. The native collision solver still owns the actual collision response; no second unbounded collision impulse is applied.
- Sends compact state reports to the server for occupancy/rate/range checks and a velocity acknowledgement. Local prediction reconciles velocity gradually; it never corrects position with a teleport. Other clients receive filtered telemetry, not a second vehicle solver.

## Architecture

```text
MTA controls + vehicle state + native wheel contacts
                       |
             mta/vehicle_adapter.lua
                       |
        fixed-step mta/vehicle_manager.lua
                       |
                  physics_core
      +----------------+-------------------+
      |                |                   |
  drivetrain       weight transfer     surfaces/aero
  transmission     suspension          brakes/ABS
  steering         tire model          collision estimate
      +----------------+-------------------+
                       |
       bounded velocity/angular correction
            (local controller/syncer only)
                       |
        server validation + smooth velocity ack
          /                         \
  NEAR/FAR telemetry filter       CSV/JSON + calibration
                       |
                 debug overlay
```

### Physics LOD

| LOD | Work performed |
| --- | --- |
| **FULL** | One supported vehicle driven and synced by the local player: fixed-step custom estimates, wheel/tire/brake model, sparse surface sampling and bounded correction. |
| **NEAR** | No competing force solver. Validated remote telemetry is filtered more quickly; MTA remains responsible for the remote vehicle's actual physics and interpolation. |
| **FAR** | No force solver. Available remote telemetry is filtered more slowly; ordinary MTA streaming and vehicle synchronization continue. |
| **INACTIVE** | No custom vehicle work. |

The client classifies streamed vehicles every 450 ms. Remote telemetry is filtered on a 100 ms budget. This is deliberately not a claim that the client can take over the server's or another player's wheel physics.

## Commands

| Command | Action |
| --- | --- |
| `/gta4help` | Show the command summary. |
| `/gta4physics` | Report active vehicle/profile/LOD status. |
| `/gta4physics on` / `off` / `toggle` | Enable, disable, or toggle custom corrections. `off` restores the captured native handling. |
| `/gta4debug on` / `off` / `full` | Toggle the telemetry overlay; `full` also draws estimated wheel-force vectors and contact points. |
| `/gta4reset` | Reset internal wheel, shift, ABS and prediction state without moving the vehicle. |
| `/gta4profile gta4` / `comfort` / `sport` / `drift` | Select a profile multiplier set in `config.lua`; it does not alter the source database. |
| `/gta4reload` | Recreate current-model simulation state and reapply current database/calibration coefficients. |
| `/gta4telemetry start` / `stop` | Start or stop the local ring-buffer recorder. Starting clears the current buffer. |
| `/gta4telemetry csv` / `json` | Export the current buffer as CSV or JSON to the MTA private resource-file area (`@gta4physics_telemetry.csv` / `.json`). |
| `/gta4telemetry clear` | Clear samples and event marks. |
| `/gta4calibrate start` / `stop` | Start or stop a model-specific calibration run; the run records telemetry and keeps calibration separate from the database. |
| `/gta4calibrate ref <metric> <value>` | Store a future reference value for the current supported model. |
| `/gta4calibrate compare` | Compare the latest run with stored references, report errors and update bounded calibration multipliers. |
| `/gta4calibrate clear` | Clear calibration data for the current model only. |

`/gta4physics` defaults to a status report. Supported `/gta4calibrate ref` metrics and units are:

- `0-60`, `0-100`: seconds, measured from the first sample above 1 m/s to threshold crossing (start a run from rest).
- `topSpeed`: metres per second.
- `brakingDistance`: metres, accumulated while braking above 4 m/s.
- `corneringG`: absolute peak lateral g.
- `yawRate`: radians per second; `rollRate`: degrees per second.
- `shiftTime`: seconds, the configured emulated shift interval observed during the run.

The comparison reports `(measured - reference) / reference` as percent error. Acceleration, top-speed, brake-distance, grip and shift-time multipliers are clamped to 0.78–1.28. Yaw and roll errors are reported but do not silently rewrite the database or another system. Reference figures must come from the user/test dataset; none are fabricated here.

## Calibration workflow

1. Choose a supported model and gather independent reference measurements on a repeatable test surface. Store each available metric with `/gta4calibrate ref <metric> <value>`.
2. Reset the vehicle to a comparable starting state and run `/gta4calibrate start`.
3. From rest, record acceleration; then brake from a known speed, hold a repeatable corner, and allow several automatic shifts. Avoid collisions and traffic for clean runs.
4. Run `/gta4calibrate stop`, then `/gta4calibrate compare`.
5. Repeat under the same conditions. The resulting multipliers are stored in a client-private `@gta4physics_calibration.json` file. They do **not** mutate `data/gta4_vehicle_database.lua`; clear them with `/gta4calibrate clear` if a run is invalid.

This workflow is a comparison aid, not a claim of exact system identification. Results vary with frame timing, terrain, rain, native MTA handling, upgrades, damage and network ownership.

## Telemetry and API exports

The CSV/JSON recorder includes time, speed, RPM, gear, driver inputs, yaw/pitch/roll, longitudinal/lateral g, surface name, four estimated wheel slips and four estimated wheel loads. Collision marks are included in JSON. The ring buffer is capped by `maxTelemetrySamples` in `config.lua`.

Client exports:

- `gta4PhysicsSetEnabled(boolean)`
- `gta4PhysicsGetTelemetry()` — returns a copy of the active vehicle's latest estimated state, or `nil` when no supported driver vehicle is active.

## Performance notes

- Custom simulation uses a 1/60 s step, caps frame delta at 50 ms and runs at most three substeps per render callback.
- Only the local driver's FULL-LOD vehicle receives force calculations and state corrections. Other vehicles are not run through a per-frame custom tire solver.
- Wheel-contact queries occur in FULL LOD; the material raycast is cached and normally runs no more often than once per 220 ms. Remote-state processing runs on a 100 ms budget.
- The debug HUD is cheap when disabled; FULL debug mode adds 3D lines and screen projections and should be used for short diagnosis, not benchmark runs.
- `config.lua` exposes the fixed-step, blend, LOD, telemetry, surface and synchronization budgets.

## Limits and honest feature breakdown

| Category | What this resource can honestly claim |
| --- | --- |
| **NATIVE MTA** | Vehicle transforms and native solver; native collision response; local driver controls; current handling table and documented handling setter; velocity/angular-velocity accessors; boolean wheel-contact checks; sparse line-of-sight material IDs; rain level; MTA multiplayer vehicle ownership/replication. |
| **EMULATED** | Model-driven engine torque/RPM and inertia, automatic gear/reverse/shift delay, wheel-speed state, slip curves and combined tire-force limits, estimated load-sensitive grip, four-corner weight transfer, spring/damper travel, speed-sensitive steering/countersteer, brake bias, wheel-lock/ABS-style modulation, rolling resistance, surface grip/wetness and aerodynamic forces. |
| **APPROXIMATED** | Per-model starting parameters; body pitch/roll/yaw moments; tire loads/slip/ground response; impact severity from mass and collision-event data; remote telemetry smoothing; calibration against user-provided measurements. The native solver remains in the loop. |
| **NOT ACCESSIBLE** | RAGE/GTA IV's private handling database or exact `handling.dat` values; true GTA IV engine/differential/traction-control internals; MTA-exposed per-wheel angular velocity, normal force, contact patch, suspension travel or slip ratio; direct server-authoritative custom tire simulation for every remote vehicle. |

MTA exposes wheel-on-ground booleans, not per-wheel normal force or contact-patch state. The tire model's wheel speeds, loads and slip are therefore internal estimates. The collision event is pre-reaction; impact mass/severity is retained for damping/telemetry while native collision response remains authoritative, avoiding a duplicate impulse. Client-side blended handling is local to the MTA client; exact cross-client parity depends on the server's normal vehicle sync and the active syncer. The server checks event source, driver seat, sequence, rate and numeric bounds but is **not** an anti-cheat or a custom authoritative physics server.

## Offline verification tools

`tools/` contains development-only checks. Nothing in `tools/` is referenced by `meta.xml` and the directory can be deleted before deployment.

```bash
python3 gta4_physics/tools/validate.py     # static checks
cd gta4_physics/tools && npm install       # fengari, used only for the runtime check
node smoke_test.js                         # offline runtime scenario
```

`validate.py` parses every Lua file, verifies `meta.xml` well-formedness and that every referenced script exists, resolves cross-file `GTA4Physics.*` references (including local aliases such as `local A = G4.Adapter`) and rejects TODO/placeholder markers.

`mta_stub.lua` + `smoke_assert.lua` + `smoke_test.js` load the real client scripts inside a Lua 5.3 interpreter with stubbed MTA functions, then drive a Sultan-class vehicle through a 12-second scenario (full throttle, then cornering, then braking, then coasting) with a deliberately crude stand-in for the native solver. The latest run reports:

| Measurement | Result |
| --- | --- |
| Frames / steps executed without a Lua error | 720 / 720 |
| Peak speed reached | ~36.6 m/s (≈132 km/h) |
| Highest gear reached | 3 of 6 |
| Peak engine speed | ~6 480 RPM (below the 7 100 RPM redline) |
| Peak lateral g | ~1.26 |
| Peak longitudinal g | ~0.74 |
| Front-axle load share under power → under braking | 0.437 → 0.563 (braking weight transfer) |
| Body pitch under power → under braking | +0.26° → +0.08° (squat then dive) |
| Peak body roll this layer contributes | ~1.1° |
| Front+rear combined slip when coasting | ~0.45 (tires relax, no permanent saturation) |
| Wheel-load / slip / RPM / g values | all finite, wheel loads non-negative |
| Handling capture and restore | mass restored exactly on disable and on stop |

These numbers prove the Lua executes, the model stays bounded and the expected qualitative behaviours appear. They are **not** MTA measurements and do not validate RAGE-like fidelity, the MTA solver's interaction, GPU cost or multiplayer behaviour — only a real client/server test can do that.

## Honest runtime status

A real MTA client/server test is still required to verify handling magnitudes, angular-correction feel, control behaviour, material sampling and multiplayer ownership under your server's resources and upgrades. This repository cannot simulate the MTA game runtime; do not treat a clean static or stub check as proof of in-game parity or performance.
