GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.TireModel = {}
local wheelNames = { "FL", "FR", "RL", "RR" }

local function magicFormula(slip, stiffness, shape, curvature)
    local bx = stiffness * slip
    return math.sin(shape * math.atan(bx - curvature * (bx - math.atan(bx))))
end

function G4.TireModel.newWheels(spec, speedMps)
    local omega = (speedMps or 0) / math.max(0.08, spec.dimensions.wheelRadius or 0.32)
    local state = {}
    for _, name in ipairs(wheelNames) do
        state[name] = { wheelSpeed = omega, longitudinalSlip = 0, lateralSlip = 0, combinedSlip = 0, normalForce = 0, fx = 0, fy = 0 }
    end
    return state
end

function G4.TireModel.compute(spec, state, basisVelocity, yawRate, steerAngle, loads, contacts, driveTorques, brakeTorques, surface, dt, profile)
    local traction = spec.traction
    local radius = math.max(0.08, spec.dimensions.wheelRadius or 0.32)
    local wheelInertia = math.max(0.08, (spec.dimensions.wheelInertia or 1.2) + math.max(0, spec.drivetrain.driveInertia or 0) * 0.18)
    local positions = {
        FL = { x = -spec.dimensions.trackWidth * 0.5, y = spec.dimensions.wheelbase * 0.50 },
        FR = { x =  spec.dimensions.trackWidth * 0.5, y = spec.dimensions.wheelbase * 0.50 },
        RL = { x = -spec.dimensions.trackWidth * 0.5, y = -spec.dimensions.wheelbase * 0.50 },
        RR = { x =  spec.dimensions.trackWidth * 0.5, y = -spec.dimensions.wheelbase * 0.50 }
    }
    if spec.class == "motorcycle" then positions.FL.x, positions.RL.x = 0, 0 end
    local out = { wheels = {}, totalRightForce = 0, totalForwardForce = 0, totalNormalForce = 0 }
    local wheelState = state.wheels or G4.TireModel.newWheels(spec, basisVelocity.forward)
    local calibrationTire = G4.Calibration and G4.Calibration.getCoefficient and G4.Calibration.getCoefficient(spec.model, "tire") or 1
    local gripProfile = M.clamp((profile and profile.tire or 1) * calibrationTire, 0.65, 1.35)
    local surfaceGrip = M.clamp((surface and surface.traction) or 1, 0.25, 1.4)

    for _, name in ipairs(wheelNames) do
        local p, wheel = positions[name], wheelState[name] or {}
        local contact = contacts[name] ~= false
        local load = math.max(0, loads[name] or 0)
        if spec.class == "motorcycle" and (name == "FR" or name == "RR") then contact, load = false, 0 end
        local localLong = basisVelocity.forward + (yawRate or 0) * p.x
        local localLat = basisVelocity.right - (yawRate or 0) * p.y
        local angle = (name == "FL" or name == "FR") and (steerAngle or 0) or 0
        local c, s = math.cos(angle), math.sin(angle)
        local wheelLong = localLong * c + localLat * s
        local wheelLat = -localLong * s + localLat * c
        local omega = wheel.wheelSpeed or (basisVelocity.forward / radius)
        local slipLong = M.clamp((omega * radius - wheelLong) / math.max(math.abs(wheelLong), 2.8), -3.0, 3.0)
        local slipLat = M.clamp(M.atan2(wheelLat, math.abs(wheelLong) + 1.2), -1.35, 1.35)
        local wheelCount = spec.class == "motorcycle" and 2 or 4
        local nominalLoad = math.max(20, spec.mass * 9.81 / wheelCount)
        local loadFactor = M.clamp((math.max(load, 1) / nominalLoad) ^ (-(traction.loadSensitivity or 0.12)), 0.68, 1.25)
        local mu = M.clamp((traction.max or 1.0) * loadFactor * surfaceGrip * gripProfile,
            traction.min or 0.4, (traction.max or 1.0) * 1.25)
        local peak = contact and load * mu or 0
        local frontWheel = name == "FL" or name == "FR"
        local axleShare = frontWheel and (traction.bias or 0.5) or (1 - (traction.bias or 0.5))
        local lateralBias = M.clamp(axleShare * 2, 0.55, 1.45)
        local curve = traction.magicFormula or {}
        local targetFx = peak * magicFormula(slipLong, traction.stiffnessLong or 8.5,
            curve.longitudinalShape or 1.55, curve.longitudinalCurvature or 0.88) * (traction.longitudinal or 1)
        local targetFy = -peak * magicFormula(slipLat, traction.stiffnessLat or 7.0,
            curve.lateralShape or 1.38, curve.lateralCurvature or 0.88) * (traction.lateral or 1) * lateralBias
        local longLimit, latLimit = math.max(1, peak * (traction.longitudinal or 1)), math.max(1, peak * (traction.lateral or 1) * lateralBias)
        local targetCombined = math.sqrt((targetFx / longLimit) ^ 2 + (targetFy / latLimit) ^ 2)
        if targetCombined > 1 then targetFx, targetFy = targetFx / targetCombined, targetFy / targetCombined end
        local relaxation = M.clamp(traction.springDelta or 0.17, 0.03, 0.50)
        local forceAlpha = 1 - math.exp(-M.clamp(16 / (1 + relaxation * 3), 5, 18) * dt)
        local fx, fy, combined = 0, 0, 0
        if contact then
            fx = (wheel.longitudinalForce or 0) + (targetFx - (wheel.longitudinalForce or 0)) * forceAlpha
            fy = (wheel.lateralForce or 0) + (targetFy - (wheel.lateralForce or 0)) * forceAlpha
            combined = math.sqrt((fx / longLimit) ^ 2 + (fy / latLimit) ^ 2)
            if combined > 1 then fx, fy = fx / combined, fy / combined end
        end
        -- Wheel-frame forces rotate back to vehicle axes (right, forward).
        local vehicleRight, vehicleForward = fx * s + fy * c, fx * c - fy * s

        local driveTorque = (driveTorques and driveTorques[name]) or 0
        local brakeTorque = (brakeTorques and brakeTorques[name]) or 0
        local brakeSign = M.sign(omega)
        if brakeSign == 0 then brakeSign = M.sign(driveTorque) end
        local netTorque = driveTorque - brakeSign * brakeTorque - fx * radius
        omega = M.clamp(omega + (netTorque / wheelInertia) * dt, -380, 380)
        wheel.wheelSpeed, wheel.longitudinalSlip, wheel.lateralSlip = omega, slipLong, slipLat
        wheel.longitudinalForce, wheel.lateralForce = fx, fy
        wheel.combinedSlip, wheel.normalForce, wheel.wheelLoad = M.clamp(combined, 0, 3), load, load
        wheel.fx, wheel.fy, wheel.contact = vehicleRight, vehicleForward, contact
        out.wheels[name] = wheel
        out.totalRightForce = out.totalRightForce + vehicleRight
        out.totalForwardForce = out.totalForwardForce + vehicleForward
        out.totalNormalForce = out.totalNormalForce + load
    end
    state.wheels = out.wheels
    return out
end
