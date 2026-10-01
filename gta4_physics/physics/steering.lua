GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Steering = {}

function G4.Steering.update(spec, state, raw, speedMps, dt, profile)
    raw = raw or {}
    local steeringRate = raw.steer or 0
    state.steerInput = M.approach(state.steerInput or 0, steeringRate, spec.steering.inputRate or 9.0, dt)
    local maxSpeed = math.max(8, spec.drivetrain.maxSpeed or 50)
    local normalizedSpeed = M.clamp((speedMps or 0) / maxSpeed, 0, 1.4)
    local sensitivity = spec.steering.speedSensitivity or 0.8
    local curve = spec.steering.speedCurve or 1.25
    local speedFactor = M.clamp(1 / (1 + sensitivity * normalizedSpeed * normalizedSpeed * curve), 0.34, 1)
    local lock = math.rad(spec.steering.lock or 32) * speedFactor * ((profile and profile.steering) or 1)
    local targetAngle = state.steerInput * lock
    local yawRate = state.yawRate or 0
    local counterLimit = spec.steering.maxCounterSteer or 0.18
    local counter = M.clamp(-yawRate * (spec.steering.counterSteer or 0.15) * M.clamp(normalizedSpeed, 0, 1), -counterLimit, counterLimit)
    if math.abs(state.steerInput or 0) < 0.035 and math.abs(yawRate) > 0.35 then targetAngle = targetAngle + counter end
    local response = math.abs(steeringRate) > 0.02 and 8.0 or (spec.steering.returnRate or 4.0)
    state.steerAngle = M.approach(state.steerAngle or 0, targetAngle, response, dt)
    local throttleTarget = raw.throttle or 0
    local stoppedReverse = raw.reverse and (speedMps or 0) < 1.0
    if stoppedReverse then throttleTarget = math.max(throttleTarget, raw.reverseThrottle or 0) end
    state.throttle = M.approach(state.throttle or 0, M.clamp(throttleTarget, 0, 1), spec.engine.throttleResponse or 4, dt)
    local brakeTarget = stoppedReverse and 0 or M.clamp(raw.brake or 0, 0, 1)
    if raw.reverse and (speedMps or 0) >= 1.0 then brakeTarget = 1 end
    state.brake = M.approach(state.brake or 0, brakeTarget, 12, dt)
    state.handbrake = raw.handbrake and true or false
    state.reverseRequested = stoppedReverse and true or false
    return { steer = state.steerInput, steerAngle = state.steerAngle, throttle = state.throttle,
        brake = state.brake, handbrake = state.handbrake, reverse = state.reverseRequested }
end
