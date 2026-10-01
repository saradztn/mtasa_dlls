-- Assertions and driving scenario for the offline runtime smoke test.
-- Runs after every client script has loaded and the MTA stubs are in place.

local G4 = GTA4Physics
assert(type(G4) == "table", "GTA4Physics global was not created")
__G4_failures = __G4_failures or {}
local failures = __G4_failures

local function check(condition, message)
    if not condition then failures[#failures + 1] = message end
end
local function finite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
__G4_check = check
__G4_finite = finite

local vehicle = __G4_test_vehicle
local originalMass = __G4_original_handling.mass

-- 1. Startup path
check(G4.VehicleDatabase.count() >= 100, "expected at least 100 estimated model entries, got " .. G4.VehicleDatabase.count())
check(G4.VehicleDatabase.get(560) ~= nil, "model 560 (Sultan) missing from the database")
check(G4.VehicleDatabase.get(560).estimated == true, "database entries must be flagged estimated")
check(G4.Surfaces.resolve(1, 0).name ~= nil, "surface resolution returned no name")
check(G4.Surfaces.resolve(nil, 0).name == "asphalt", "nil material should fall back to asphalt")

triggerEvent("onClientResourceStart", resourceRoot, resourceRoot)

-- 2. Entering the vehicle activates FULL LOD and a blended native base
source = vehicle
triggerEvent("onClientVehicleEnter", vehicle, localPlayer, 0)
local state = G4.VehicleManager.states[vehicle]
check(state ~= nil, "no simulation state after entering a supported vehicle")
check(G4.VehicleManager.activeVehicle == vehicle, "active vehicle was not registered")
check(G4.State.enabled == true, "emulator should start enabled")
check(type(vehicle.handling.mass) == "number", "native handling mass missing")
check(math.abs(vehicle.handling.mass - originalMass) > 1, "native handling base was not blended")
check(G4.Performance.getLod(vehicle) == "FULL", "driver vehicle should be FULL LOD")

-- 3. Drive for 12 seconds: throttle, then steering, then braking
local frames = 12 * 60
local speedLog, loadLog, slipLog, gearLog, rpmLog, rollLog, yawLog = {}, {}, {}, {}, {}, {}, {}
local lateralGLog, longitudinalGLog, compressionLog = {}, {}, {}
local accelFrontShare, brakingFrontShare = nil, nil
local accelPitch, brakingPitch = nil, nil
for frame = 1, frames do
    if frame <= 5 * 60 then
        __G4_input.throttle, __G4_input.brake, __G4_input.steer = 1, 0, 0
    elseif frame <= 8 * 60 then
        __G4_input.throttle, __G4_input.brake, __G4_input.steer = 0.7, 0, 0.6
    else
        __G4_input.throttle, __G4_input.brake, __G4_input.steer = 0, 1, 0
    end
    __G4_frame(16.666)
    if state and state.longitudinalG ~= nil then
        local totalLoad = 0
        local totalSlip = 0
        for _, name in ipairs({ "FL", "FR", "RL", "RR" }) do
            local wheel = state.tireWheels and state.tireWheels[name]
            if wheel then
                totalLoad = totalLoad + (wheel.wheelLoad or 0)
                totalSlip = totalSlip + math.abs(wheel.combinedSlip or 0)
                check(finite(wheel.wheelLoad), "non-finite wheel load for " .. name)
                check(finite(wheel.combinedSlip), "non-finite combined slip for " .. name)
                check(finite(wheel.wheelSpeed), "non-finite wheel speed for " .. name)
                check((wheel.wheelLoad or 0) >= 0, "negative wheel load for " .. name)
            end
        end
        speedLog[#speedLog + 1] = state.speedMps or 0
        loadLog[#loadLog + 1] = totalLoad
        slipLog[#slipLog + 1] = totalSlip
        gearLog[#gearLog + 1] = state.gear or 0
        rpmLog[#rpmLog + 1] = state.rpm or 0
        rollLog[#rollLog + 1] = state.roll or 0
        yawLog[#yawLog + 1] = state.yawRate or 0
        lateralGLog[#lateralGLog + 1] = state.lateralG or 0
        longitudinalGLog[#longitudinalGLog + 1] = state.longitudinalG or 0
        if state.suspensionWheels and state.suspensionWheels.FL then
            compressionLog[#compressionLog + 1] = state.suspensionWheels.FL.compression01 or 0
        end
        local frontLoad = (state.loads.FL or 0) + (state.loads.FR or 0)
        local share = totalLoad > 0 and frontLoad / totalLoad or nil
        if share then
            local accelerating = frame <= 5 * 60 and (state.speedMps or 0) > 5
            local braking = frame > 8 * 60 and (state.speedMps or 0) > 5
            local pitch = state.pitch or 0
            if accelerating then
                accelFrontShare = math.min(accelFrontShare or share, share)
                accelPitch = math.max(accelPitch or pitch, pitch)
            end
            if braking then
                brakingFrontShare = math.max(brakingFrontShare or share, share)
                brakingPitch = math.min(brakingPitch or pitch, pitch)
            end
        end
        check(finite(state.rpm) and state.rpm > 0, "engine RPM is not positive")
        check(finite(state.longitudinalG) and finite(state.lateralG), "non-finite g values")
        check(state.surfaceName ~= nil, "surface name missing")
        check(finite(state.yawRate), "non-finite yaw rate")
    end
end

-- Coast phase: with no throttle or brake the tires must stop being saturated.
__G4_input.throttle, __G4_input.brake, __G4_input.steer = 0, 0, 0
local coastSlip = {}
for _ = 1, 2 * 60 do
    __G4_frame(16.666)
    if state and state.tireWheels then
        coastSlip[#coastSlip + 1] = (state.tireWheels.FL.combinedSlip or 0) + (state.tireWheels.RL.combinedSlip or 0)
    end
end

local function maximum(list)
    local best = 0
    for _, value in ipairs(list) do best = math.max(best, math.abs(value)) end
    return best
end
local function average(list)
    if #list == 0 then return 0 end
    local sum = 0
    for _, value in ipairs(list) do sum = sum + value end
    return sum / #list
end

__G4_report = {
    frames = frames,
    maxSpeed = maximum(speedLog),
    averageLoad = average(loadLog),
    maxSlip = maximum(slipLog),
    maxGear = maximum(gearLog),
    maxRPM = maximum(rpmLog),
    maxRoll = maximum(rollLog),
    maxYawRate = maximum(yawLog),
    maxLateralG = maximum(lateralGLog),
    maxLongitudinalG = maximum(longitudinalGLog),
    maxCompression = maximum(compressionLog),
    surface = state and state.surfaceName,
    tiresTurned = state and state.tireWheels and state.tireWheels.FL ~= nil,
    accelFrontShare = accelFrontShare or -1,
    brakingFrontShare = brakingFrontShare or -1,
    coastSlip = maximum(coastSlip),
    coastSpeed = state and state.speedMps or -1,
    coastFlLongSlip = state and state.tireWheels.FL.longitudinalSlip or -1,
    coastFlLatSlip = state and state.tireWheels.FL.lateralSlip or -1,
    coastFlForce = state and state.tireWheels.FL.fx or -1,
    coastFlWheelSpeed = state and state.tireWheels.FL.wheelSpeed or -1,
    coastYawRate = state and state.yawRate or -1,
    accelPitchDeg = accelPitch or -999,
    brakingPitchDeg = brakingPitch or -999,
    maxBodyRollDeg = maximum(rollLog)
}

check(__G4_report.maxSpeed > 8, string.format("vehicle did not accelerate (max %.2f m/s)", __G4_report.maxSpeed))
check(__G4_report.maxGear >= 2, string.format("automatic transmission never upshifted (max gear %d)", __G4_report.maxGear))
check(__G4_report.maxRPM > 900, string.format("engine never exceeded idle (max %.0f rpm)", __G4_report.maxRPM))
check(__G4_report.maxSlip < 40, string.format("combined slip grew unrealistically (max %.2f)", __G4_report.maxSlip))
check(type(accelFrontShare) == "number" and type(brakingFrontShare) == "number", "front-axle load share was never recorded")
if type(accelFrontShare) == "number" and type(brakingFrontShare) == "number" then
    check(brakingFrontShare > accelFrontShare + 0.01, string.format(
        "braking weight transfer not visible (front share %.3f under power vs %.3f braking)", accelFrontShare, brakingFrontShare))
end
check(__G4_report.coastSlip < 1.2, string.format(
    "tire slip stayed saturated while coasting (front+rear combined slip %.2f)", __G4_report.coastSlip))
check(type(accelPitch) == "number" and type(brakingPitch) == "number", "body pitch was never recorded")
if type(accelPitch) == "number" and type(brakingPitch) == "number" then
    check(brakingPitch < accelPitch - 0.05, string.format(
        "brake dive / acceleration squat not visible (nose-up %.3f deg under power vs %.3f deg braking)", accelPitch, brakingPitch))
end
check(__G4_report.maxBodyRollDeg > 0.15 and __G4_report.maxBodyRollDeg < 12, string.format(
    "cornering roll is outside a believable range (%.3f deg)", __G4_report.maxBodyRollDeg))
check(state ~= nil, "state disappeared during the run")
if state then
    local totalLoad = 0
    for _, name in ipairs({ "FL", "FR", "RL", "RR" }) do
        totalLoad = totalLoad + (state.loads[name] or 0)
    end
    local expected = state.spec.mass * 9.81
    check(math.abs(totalLoad - expected) / expected < 0.25,
        string.format("total wheel load %.0f N is not within 25%% of mass*g %.0f N", totalLoad, expected))
    check(state.suspensionWheels ~= nil and state.suspensionWheels.FL ~= nil, "suspension state missing")
    if state.suspensionWheels and state.suspensionWheels.FL then
        check(finite(state.suspensionWheels.FL.compression), "non-finite suspension compression")
        check(state.suspensionWheels.FL.compression >= 0, "negative suspension compression")
    end
    check(state.outputs and state.outputs.wheelForces ~= nil, "force outputs missing")
end

-- 4. Profiles, reset, telemetry, calibration and debug overlay
check(G4.VehicleManager.setProfile("sport") == true, "profile switch failed")
check(G4.VehicleManager.setProfile("nonsense") == false, "invalid profile was accepted")
check(G4.VehicleManager.resetCurrent() == true, "reset failed")
check(G4.Telemetry.start() == true, "telemetry start failed")
__G4_frame(20)
__G4_frame(20)
check(G4.Telemetry.getSampleCount() >= 1, "telemetry recorded no samples")
G4.Telemetry.stop()

check(G4.Calibration.setReference(560, "0-60", 6.5) == true, "calibration reference rejected")
G4.Calibration.start(560)
G4.Calibration.runtime.zeroTo60 = 7.0
G4.Calibration.results[560] = { zeroTo60 = 7.0, topSpeed = 60, corneringG = 0.9 }
local report = G4.Calibration.compare(560)
check(type(report) == "table", "calibration compare returned no report")
check(G4.Calibration.getCoefficient(560, "engine") ~= 1, "calibration coefficient was not produced")

G4.State.debug, G4.State.debugFull = true, true
G4.Visualizer.render()
G4.State.debug, G4.State.debugFull = false, false

-- 5. Disabling restores the captured native handling and releases state
G4.VehicleManager.setEnabled(false)
check(math.abs(vehicle.handling.mass - originalMass) < 0.001, "native handling mass was not restored on disable")
G4.VehicleManager.setEnabled(true)

-- 6. Resource stop must restore handling and clear state
source = vehicle
triggerEvent("onClientVehicleExit", vehicle, localPlayer, 0)
triggerEvent("onClientResourceStop", resourceRoot, resourceRoot)
check(math.abs(vehicle.handling.mass - originalMass) < 0.001, "native handling mass was not restored on stop")
check(G4.VehicleManager.activeVehicle == nil, "active vehicle survived resource stop")
check(G4.VehicleManager.states[vehicle] == nil, "simulation state survived resource stop")

-- 7. Logs must exist and no numeric field may be nil/NaN
check(#__G4_log > 0, "resource produced no debug/chat output")
for index, line in ipairs(__G4_log) do
    check(type(line) == "string", "log entry " .. index .. " is not a string")
end
