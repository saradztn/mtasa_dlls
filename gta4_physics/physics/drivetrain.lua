GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Drivetrain = {}

local function torqueCurve(engine, rpm)
    local idle, peak, redline = engine.idleRPM or 800, engine.peakRPM or 4200, engine.redlineRPM or 6500
    local shape = engine.torqueCurve or {}
    local normalized = M.clamp((rpm - idle) / math.max(1, redline - idle), 0, 1)
    local peakAt = M.clamp((peak - idle) / math.max(1, redline - idle), 0.15, 0.90)
    if normalized <= peakAt then
        return (shape.riseBase or 0.58) + (shape.riseGain or 0.42) * math.sin((normalized / peakAt) * math.pi * 0.5)
    end
    local fall = (normalized - peakAt) / math.max(0.01, 1 - peakAt)
    return M.clamp(1.0 - (shape.fallLinear or 0.32) * fall - (shape.fallQuadratic or 0.10) * fall * fall,
        shape.minimum or 0.52, 1.0)
end

function G4.Drivetrain.compute(spec, state, controls, transmission, speedMps, profile)
    local engine, drive = spec.engine, spec.drivetrain
    local throttle = M.clamp(controls.throttle or 0, 0, 1)
    local rpm = state.rpm or engine.idleRPM or 800
    local calibrationEngine = G4.Calibration and G4.Calibration.getCoefficient and G4.Calibration.getCoefficient(spec.model, "engine") or 1
    local engineTorque = (engine.peakTorqueNm or 200) * torqueCurve(engine, rpm) * throttle * ((profile and profile.engine) or 1) * calibrationEngine
    local totalWheelTorque = engineTorque * (transmission.ratio or 0) * (drive.finalDrive or 3.5) * (drive.efficiency or 0.86)
    totalWheelTorque = totalWheelTorque * (transmission.shiftFactor or 1)
    local radius = math.max(0.08, spec.dimensions.wheelRadius or 0.32)
    local totalForce = M.clamp(totalWheelTorque / radius, -math.max(250, drive.driveForce or 250), math.max(250, drive.driveForce or 250))
    local wheelTorque = { FL = 0, FR = 0, RL = 0, RR = 0 }
    local frontShare = drive.type == "FWD" and 1 or (drive.type == "AWD" and M.clamp(drive.frontShare or 0.5, 0.2, 0.8) or 0)
    if spec.class == "motorcycle" then
        if drive.type == "FWD" then wheelTorque.FL = totalForce * radius else wheelTorque.RL = totalForce * radius end
    else
        wheelTorque.FL, wheelTorque.FR = totalForce * frontShare * radius * 0.5, totalForce * frontShare * radius * 0.5
        wheelTorque.RL, wheelTorque.RR = totalForce * (1 - frontShare) * radius * 0.5, totalForce * (1 - frontShare) * radius * 0.5
    end
    local engineBrake = 0
    if throttle < 0.04 and math.abs(speedMps or 0) > 1.5 and (transmission.ratio or 0) ~= 0 then
        engineBrake = math.min(engine.engineBrakeNm or 30, math.abs(speedMps) * (engine.engineBrakeNm or 30) * 0.12) * M.sign(speedMps)
    end
    state.engineTorque, state.engineTorqueCurve, state.engineBrakeNm = engineTorque, torqueCurve(engine, rpm), engineBrake
    return { wheelTorques = wheelTorque, engineTorque = engineTorque, engineBrakeNm = engineBrake, totalForce = totalForce }
end
