GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Transmission = {}

local function shiftTo(state, target, delay)
    if state.gear == target then return end
    state.gear = target
    state.shiftTimer = delay
    state.lastShiftDuration = delay
    state.lastShiftTick = getTickCount and getTickCount() or 0
end

function G4.Transmission.update(spec, state, controls, speedMps, dt)
    local drive = spec.drivetrain
    local count = math.max(1, tonumber(drive.gears) or #(drive.gearRatios or {}))
    local ratios = drive.gearRatios or { 3.0, 1.8, 1.2, 0.9 }
    local calibrationShift = G4.Calibration and G4.Calibration.getCoefficient and G4.Calibration.getCoefficient(spec.model, "shift") or 1
    local shiftDelay = (drive.shiftDelay or 0.22) * calibrationShift
    local gear = tonumber(state.gear) or 1
    if controls.reverse then
        if math.abs(speedMps or 0) < 1.15 and state.gear ~= -1 then shiftTo(state, -1, 0.14 * calibrationShift) end
    elseif gear < 0 then
        shiftTo(state, 1, 0.16 * calibrationShift)
    elseif gear == 0 then
        shiftTo(state, 1, 0.12 * calibrationShift)
    end

    state.shiftTimer = math.max(0, (state.shiftTimer or 0) - (dt or 0))
    local ratio = 0
    local shiftFactor = state.shiftTimer > 0 and 0.42 or 1
    if state.gear == -1 then
        ratio = -(drive.reverseRatio or 3.05)
    elseif state.gear > 0 then
        state.gear = math.min(count, state.gear)
        ratio = tonumber(ratios[state.gear]) or tonumber(ratios[#ratios]) or 1

        local rpm = state.rpm or spec.engine.idleRPM
        local upshift = spec.engine.upshiftRPM or (spec.engine.redlineRPM * 0.91)
        local downshift = spec.engine.downshiftRPM or (spec.engine.peakRPM * 0.54)
        if state.shiftTimer <= 0 and controls.throttle > 0.18 and state.gear < count and rpm > upshift then
            shiftTo(state, state.gear + 1, shiftDelay)
        elseif state.shiftTimer <= 0 and state.gear > 1 and (rpm < downshift or (speedMps or 0) < 2.2) then
            shiftTo(state, state.gear - 1, shiftDelay)
        end
        if state.gear > 0 then ratio = tonumber(ratios[state.gear]) or ratio end
    end

    local wheelRadius = math.max(0.08, spec.dimensions.wheelRadius or 0.32)
    local coupledRPM = math.abs(speedMps or 0) / wheelRadius * math.abs(ratio * (drive.finalDrive or 3.5)) * 60 / (2 * math.pi)
    local idle = spec.engine.idleRPM or 800
    local throttle = M.clamp(controls.throttle or 0, 0, 1)
    local freeRevRPM = idle + throttle * ((spec.engine.peakRPM or 4500) - idle) * 0.54
    local targetRPM = math.max(idle, coupledRPM, freeRevRPM)
    targetRPM = math.min(spec.engine.redlineRPM or 6500, targetRPM)
    local inertia = math.max(0.05, (spec.engine.inertia or 0.25) + math.max(0, drive.driveInertia or 0) * 0.035)
    local response = M.clamp(1 / inertia, 1.2, 7.5)
    state.rpm = M.approach(state.rpm or idle, targetRPM, response, dt or 0)
    state.gearRatio = ratio
    state.shiftFactor = shiftFactor
    return { gear = state.gear, ratio = ratio, finalDrive = drive.finalDrive or 3.5, shiftFactor = shiftFactor, rpm = state.rpm }
end
