GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics

function gta4PhysicsSetEnabled(enabled)
    return G4.VehicleManager.setEnabled(enabled == true)
end

function gta4PhysicsGetTelemetry()
    local vehicle = G4.VehicleManager and G4.VehicleManager.activeVehicle
    local state = vehicle and G4.VehicleManager.states[vehicle]
    if not state then return nil end
    return G4.copyTable({
        model = state.model, profile = state.profile, speedMps = state.speedMps, speedKmh = state.speedKmh,
        rpm = state.rpm, gear = state.gear, throttle = state.throttle, brake = state.brake,
        steering = state.steering, yawRate = state.yawRate, pitch = state.pitch, roll = state.roll,
        longitudinalG = state.longitudinalG, lateralG = state.lateralG, loads = state.loads,
        wheels = state.tireWheels, surface = state.surfaceName, estimated = state.spec.estimated
    })
end

local function onStart()
    if G4.State.resourceStarted then return end
    G4.State.resourceStarted = true
    G4.Calibration.load()
    G4.Performance.updateLods(true)
    G4.VehicleManager.start()
    G4.Debug.start()
    G4.Commands.start()
    G4.log(string.format("Client started. %d per-model estimates loaded; all database entries are marked estimated.", G4.VehicleDatabase.count()))
    G4.notify("GTA IV-style behavior emulator ready. Use /gta4help; drive the vehicle as its driver to activate FULL LOD.")
end

local function onStop()
    if not G4.State.resourceStarted then return end
    G4.Commands.stop()
    G4.Debug.stop()
    G4.VehicleManager.stop()
    G4.Telemetry.stop()
    G4.Calibration.save()
    G4.State.resourceStarted = false
end

addEventHandler("onClientResourceStart", resourceRoot, onStart)
addEventHandler("onClientResourceStop", resourceRoot, onStop)
