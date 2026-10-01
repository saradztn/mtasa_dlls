GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Braking = {}
local wheelNames = { "FL", "FR", "RL", "RR" }

function G4.Braking.compute(spec, state, controls, loads, speedMps, dt, profile)
    local brake = spec.brakes
    local calibrationBrake = G4.Calibration and G4.Calibration.getCoefficient and G4.Calibration.getCoefficient(spec.model, "brake") or 1
    local force = math.max(0, brake.force or 0) * M.clamp(profile and profile.brake or 1, 0.6, 1.4) * calibrationBrake
    local command = M.clamp(controls.brake or 0, 0, 1)
    local frontBias = M.clamp(brake.bias or 0.63, 0.50, 0.76)
    local wheelRadius = math.max(0.08, spec.dimensions.wheelRadius or 0.32)
    local torques = { FL = 0, FR = 0, RL = 0, RR = 0 }
    state.abs = state.abs or { FL = 1, FR = 1, RL = 1, RR = 1 }
    for _, name in ipairs(wheelNames) do
        local front = name == "FL" or name == "FR"
        local activeWheel = spec.class ~= "motorcycle" or name == "FL" or name == "RL"
        if activeWheel then
            local axleShare = front and frontBias or (1 - frontBias)
            local wheelsPerAxle = spec.class == "motorcycle" and 1 or 2
            local pressure = state.abs[name] or 1
            local wheel = state.wheels and state.wheels[name] or {}
            local slip = wheel.longitudinalSlip or 0
            local activationSpeed = brake.absActivationSpeed or 2.0
            local minimumPressure = brake.absMinPressure or 0.22
            if command > 0.02 and math.abs(speedMps or 0) > activationSpeed and slip < -(brake.absSlip or 0.18) then
                pressure = math.max(minimumPressure, pressure - (brake.absRelease or 8) * dt)
            else
                pressure = math.min(1, pressure + (brake.absRecover or 2.5) * dt)
            end
            state.abs[name] = pressure
            local perWheelForce = force * axleShare / wheelsPerAxle * command * pressure
            if state.handbrake and not front then perWheelForce = perWheelForce + force * 0.34 / wheelsPerAxle end
            perWheelForce = math.min(perWheelForce, math.max(0, loads[name] or 0) * 1.35)
            torques[name] = perWheelForce * wheelRadius
        else
            state.abs[name] = 1
        end
    end
    state.absActive = false
    for _, name in ipairs(wheelNames) do if (state.abs[name] or 1) < 0.98 then state.absActive = true end end
    return { wheelTorques = torques, command = command, absActive = state.absActive }
end
