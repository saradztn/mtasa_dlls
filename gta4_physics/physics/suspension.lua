GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Suspension = {}
local wheelNames = { "FL", "FR", "RL", "RR" }

function G4.Suspension.newState()
    return { compression = { FL = 0, FR = 0, RL = 0, RR = 0 }, velocity = { FL = 0, FR = 0, RL = 0, RR = 0 } }
end

function G4.Suspension.update(spec, state, loads, contacts, dt, profile)
    local susp = spec.suspension
    local wheelCount = spec.class == "motorcycle" and 2 or 4
    local massPerWheel = math.max(10, spec.mass / wheelCount)
    local result = { wheels = {}, pitchMoment = 0, rollMoment = 0, verticalForce = 0 }
    local forceScale = M.clamp(profile and profile.suspension or 1, 0.6, 1.5)
    for _, name in ipairs(wheelNames) do
        local contact = contacts[name] ~= false
        local targetLoad = math.max(0, loads[name] or 0)
        if spec.class == "motorcycle" and (name == "FR" or name == "RR") then contact, targetLoad = false, 0 end
        local spring = math.max(1000, susp.force or 25000) * forceScale
        local travel = math.max(0.03, (susp.upper or 0.18) - (susp.lower or -0.15))
        local current = state.suspension.compression[name] or travel * 0.44
        local velocity = state.suspension.velocity[name] or 0
        local target = contact and M.clamp(targetLoad / spring + (susp.raise or 0), 0.015, travel) or 0
        local damping = velocity < 0 and (susp.compression or 2500) or (susp.rebound or 3500)
        local acceleration = (targetLoad - spring * current - damping * velocity) / massPerWheel
        if not contact then acceleration = (-spring * current - damping * velocity) / massPerWheel end
        velocity = M.clamp(velocity + acceleration * dt, -3.5, 3.5)
        current = M.clamp(current + velocity * dt, 0, travel)
        state.suspension.compression[name] = current
        state.suspension.velocity[name] = velocity
        local normalized = M.clamp(current / travel, 0, 1)
        local cornerForce = contact and math.max(0, spring * current + damping * velocity) or 0
        result.wheels[name] = {
            compression = current, compression01 = normalized, compressionVelocity = velocity,
            rebound = velocity < -0.01, compressionState = velocity > 0.01,
            bottoming = normalized > 0.94, extension = normalized < 0.08,
            springForce = cornerForce, contact = contact
        }
        local front = name == "FL" or name == "FR"
        local left = name == "FL" or name == "RL"
        local longitudinalArm = front and (spec.dimensions.wheelbase * 0.5) or (-spec.dimensions.wheelbase * 0.5)
        local lateralArm = spec.class == "motorcycle" and 0 or (left and (-spec.dimensions.trackWidth * 0.5) or (spec.dimensions.trackWidth * 0.5))
        result.pitchMoment = result.pitchMoment + cornerForce * longitudinalArm
        result.rollMoment = result.rollMoment + cornerForce * lateralArm
        result.verticalForce = result.verticalForce + cornerForce
    end
    if spec.class ~= "motorcycle" then
        local antiRoll = math.max(0, susp.antiRoll or 0) * forceScale
        local function applyAntiRoll(leftName, rightName, front)
            local leftWheel, rightWheel = result.wheels[leftName], result.wheels[rightName]
            if not leftWheel or not rightWheel or not leftWheel.contact or not rightWheel.contact then return end
            local difference = leftWheel.compression - rightWheel.compression
            local transfer = M.clamp(antiRoll * difference * 0.5, -math.min(rightWheel.springForce, spec.mass * 9.81 * 0.20), math.min(leftWheel.springForce, spec.mass * 9.81 * 0.20))
            local oldLeft, oldRight = leftWheel.springForce, rightWheel.springForce
            leftWheel.springForce = math.max(0, oldLeft + transfer)
            rightWheel.springForce = math.max(0, oldRight - transfer)
            local leftDelta, rightDelta = leftWheel.springForce - oldLeft, rightWheel.springForce - oldRight
            result.verticalForce = result.verticalForce + leftDelta + rightDelta
            local y = (front and 1 or -1) * spec.dimensions.wheelbase * 0.5
            result.pitchMoment = result.pitchMoment + (leftDelta + rightDelta) * y
            result.rollMoment = result.rollMoment + leftDelta * (-spec.dimensions.trackWidth * 0.5) + rightDelta * (spec.dimensions.trackWidth * 0.5)
        end
        applyAntiRoll("FL", "FR", true)
        applyAntiRoll("RL", "RR", false)
    end
    return result
end
