GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.PhysicsCore = {}
local Core = G4.PhysicsCore
local GRAVITY = 9.81

function Core.newState(spec, profileName)
    return {
        spec = spec, model = spec.model, profile = profileName or G4.State.profile,
        gear = 1, rpm = spec.engine.idleRPM, shiftTimer = 0, shiftFactor = 1,
        throttle = 0, brake = 0, steerInput = 0, steerAngle = 0, yawRate = 0,
        longitudinalAcceleration = 0, lateralAcceleration = 0,
        suspension = G4.Suspension.newState(), wheels = G4.TireModel.newWheels(spec, 0),
        abs = { FL = 1, FR = 1, RL = 1, RR = 1 },
        contacts = { FL = true, FR = true, RL = true, RR = true },
        surface = G4.Surfaces.resolve(nil, 0), surfaceTick = 0,
        accumulator = 0, networkTimer = 0, lastTelemetryTick = 0,
        collisionTimeLeft = 0, collisionYawDamping = 1,
        lod = "FULL", lastVelocity = { x = 0, y = 0, z = 0 },
        outputs = {}
    }
end

local function summarizeWheels(wheels, loads)
    local result = {}
    for _, name in ipairs({ "FL", "FR", "RL", "RR" }) do
        local wheel = wheels[name] or {}
        result[name] = {
            wheelSpeed = wheel.wheelSpeed or 0,
            wheelSlip = wheel.longitudinalSlip or 0,
            longitudinalSlip = wheel.longitudinalSlip or 0,
            lateralSlip = wheel.lateralSlip or 0,
            combinedSlip = wheel.combinedSlip or 0,
            normalForce = loads[name] or 0,
            wheelLoad = loads[name] or 0,
            fx = wheel.fx or 0, fy = wheel.fy or 0,
            contact = wheel.contact ~= false
        }
    end
    return result
end

local function tireYawMoment(spec, wheels)
    local positions = {
        FL = { x = -spec.dimensions.trackWidth * 0.5, y = spec.dimensions.wheelbase * 0.5 },
        FR = { x = spec.dimensions.trackWidth * 0.5, y = spec.dimensions.wheelbase * 0.5 },
        RL = { x = -spec.dimensions.trackWidth * 0.5, y = -spec.dimensions.wheelbase * 0.5 },
        RR = { x = spec.dimensions.trackWidth * 0.5, y = -spec.dimensions.wheelbase * 0.5 }
    }
    if spec.class == "motorcycle" then positions.FL.x, positions.RL.x = 0, 0 end
    local moment = 0
    for name, point in pairs(positions) do
        local wheel = wheels[name]
        if wheel then moment = moment + point.x * (wheel.fy or 0) - point.y * (wheel.fx or 0) end
    end
    return moment
end

local function suspensionMomentError(spec, suspension, loads)
    local expectedPitch, expectedRoll = 0, 0
    for _, name in ipairs({ "FL", "FR", "RL", "RR" }) do
        local front = name == "FL" or name == "FR"
        local left = name == "FL" or name == "RL"
        local x = spec.class == "motorcycle" and 0 or (left and -spec.dimensions.trackWidth * 0.5 or spec.dimensions.trackWidth * 0.5)
        local y = front and spec.dimensions.wheelbase * 0.5 or -spec.dimensions.wheelbase * 0.5
        local load = loads[name] or 0
        expectedPitch = expectedPitch + load * y
        expectedRoll = expectedRoll - load * x
    end
    -- Correction moments push the modelled body toward the load distribution:
    -- error = desired (from wheel loads) - actual (from spring/damper forces).
    local rollError = expectedRoll - suspension.rollMoment
    local pitchError = expectedPitch - suspension.pitchMoment
    return rollError, pitchError
end

-- Body attitude is handled as a bounded secondary motion: loads and forces decide
-- a target roll/pitch angle for the given lateral/longitudinal g, the modelled
-- body lags toward it, and the vehicle's angular velocity is nudged just enough
-- to track that rate. Terrain tilt and the native solver are never overridden,
-- and the target angle is bounded, so the motion always settles.
local function applyAngularMoment(vehicle, state, sample, lateralForce, forwardForce, yawMoment, suspensionRollMoment, suspensionPitchMoment, dt, profile)
    if not sample.canSimulate or not sample.basis then return end
    local spec = state.spec
    local mass, track, wheelbase = spec.mass, spec.dimensions.trackWidth, spec.dimensions.wheelbase
    local body = spec.bodyDynamics or {}
    local damping = state.collisionTimeLeft > 0 and state.collisionYawDamping or 1
    -- customAngularBlend (config.lua, default 0.10) scales how much of the
    -- reference body attitude this layer contributes; 1.0 gives it full
    -- authority over the reference angle.
    local authority = M.clamp((G4.Config.customAngularBlend or 0.1) * 3.5, 0.12, 1.0) * ((profile and profile.force) or 1) / damping

    local lateralG = lateralForce / math.max(1, mass * GRAVITY)
    local longitudinalG = forwardForce / math.max(1, mass * GRAVITY)
    local rollPerG = math.rad(body.maxRollDeg or 4.4)
    local pitchPerG = math.rad(body.maxPitchDeg or 2.2)
    local loadRoll = M.clamp((suspensionRollMoment or 0) / math.max(1, mass * GRAVITY * track), -1, 1) * 0.5
    local loadPitch = M.clamp((suspensionPitchMoment or 0) / math.max(1, mass * GRAVITY * wheelbase), -1, 1) * 0.5
    local rollTarget = M.clamp((lateralG + loadRoll) * rollPerG, -rollPerG * 1.6, rollPerG * 1.6) * authority
    local pitchTarget = M.clamp((longitudinalG + loadPitch) * pitchPerG, -pitchPerG * 1.6, pitchPerG * 1.6) * authority

    state.bodyRoll, state.bodyPitch = state.bodyRoll or 0, state.bodyPitch or 0
    local previousRoll, previousPitch = state.bodyRoll, state.bodyPitch
    state.bodyRoll = M.approach(state.bodyRoll, rollTarget, body.rollRate or 6.4, dt)
    state.bodyPitch = M.approach(state.bodyPitch, pitchTarget, body.pitchRate or 6.0, dt)
    local desiredRollRate = (state.bodyRoll - previousRoll) / dt
    local desiredPitchRate = (state.bodyPitch - previousPitch) / dt

    local currentWorld = sample.angularVelocity
    local localOmega = M.toLocal(sample.basis, currentWorld)
    local maxRate = math.min(G4.Config.maxAngularCorrection, G4.Config.suspension.maxBodyRate or 0.55)
    local rollDelta = M.clamp(desiredRollRate - localOmega.forward, -maxRate, maxRate) * dt
    local pitchDelta = M.clamp(desiredPitchRate - localOmega.right, -maxRate, maxRate) * dt
    local yawGain = (body.yawGain or 0.05) * authority
    local yawInertia = math.max(50, mass * (wheelbase * wheelbase + track * track) / 12)
    local yawDelta = M.clamp(yawGain * (yawMoment / yawInertia) * dt, -maxRate * dt, maxRate * dt)
    -- Local pitch is about vehicle-right (X); roll is about vehicle-forward (Y).
    local worldDelta = M.toWorld(sample.basis, pitchDelta, rollDelta, yawDelta)
    G4.Adapter.setAngularVelocityRad(vehicle, M.add(currentWorld, worldDelta))
end

function Core.step(vehicle, state, dt)
    if not isElement(vehicle) or not state or not state.spec then return false end
    dt = M.clamp(dt or 0, 1 / 240, 1 / 20)
    local sample = G4.Adapter.sample(vehicle)
    if not sample then return false end
    local spec = state.spec
    local profile = G4.Config.profiles[state.profile] or G4.Config.profiles.gta4
    local speedMps = sample.speed
    local raw = G4.Adapter.readControls(localPlayer)
    local controls = G4.Steering.update(spec, state, raw, speedMps, dt, profile)
    local transmission = G4.Transmission.update(spec, state, controls, sample.localVelocity.forward, dt)
    local drive = G4.Drivetrain.compute(spec, state, controls, transmission, sample.localVelocity.forward, profile)

    local now = getTickCount()
    if now - (state.surfaceTick or 0) >= G4.Config.surfaceSampleMs then
        state.surface = G4.Adapter.sampleSurface(vehicle, now) or state.surface
        state.surfaceTick = now
    end
    state.contacts = G4.Adapter.getWheelContacts(vehicle, spec.class)
    local preliminaryAir = G4.AirDynamics.compute(spec, sample.velocity, profile)
    local loads = G4.WeightTransfer.compute(spec, state.longitudinalAcceleration, state.lateralAcceleration,
        preliminaryAir.downforce - preliminaryAir.lift, state.contacts)
    local suspension = G4.Suspension.update(spec, state, loads.wheels, state.contacts, dt, profile)
    local brakes = G4.Braking.compute(spec, state, controls, loads.wheels, sample.localVelocity.forward, dt, profile)

    if math.abs(drive.engineBrakeNm or 0) > 0 and transmission.ratio ~= 0 then
        local engineBrakeWheel = math.min(950, math.abs(drive.engineBrakeNm * transmission.ratio * transmission.finalDrive))
        if spec.class == "motorcycle" then
            -- The motorcycle model uses FL for the front and RL for the rear wheel.
            brakes.wheelTorques.RL = brakes.wheelTorques.RL + engineBrakeWheel
        elseif spec.drivetrain.type == "FWD" then
            brakes.wheelTorques.FL = brakes.wheelTorques.FL + engineBrakeWheel * 0.5
            brakes.wheelTorques.FR = brakes.wheelTorques.FR + engineBrakeWheel * 0.5
        else
            brakes.wheelTorques.RL = brakes.wheelTorques.RL + engineBrakeWheel * 0.5
            brakes.wheelTorques.RR = brakes.wheelTorques.RR + engineBrakeWheel * 0.5
        end
    end

    local tires = G4.TireModel.compute(spec, state, sample.localVelocity, state.yawRate,
        controls.steerAngle, loads.wheels, state.contacts, drive.wheelTorques, brakes.wheelTorques,
        state.surface, dt, profile)
    local aero = G4.AirDynamics.compute(spec, sample.velocity, profile)
    local rolling = (state.surface and state.surface.rollingResistance or 0.012) * spec.mass * GRAVITY
    local forwardForce = tires.totalForwardForce + M.dot(sample.basis.forward, aero.force)
    forwardForce = forwardForce - M.sign(sample.localVelocity.forward) * rolling
    local rightForce = tires.totalRightForce + M.dot(sample.basis.right, aero.force)
    local upForce = M.dot(sample.basis.up, aero.force) + (aero.lift or 0) - (aero.downforce or 0)

    local accelerationForward = forwardForce / math.max(1, spec.mass)
    local accelerationRight = rightForce / math.max(1, spec.mass)
    local suspensionRollMoment, suspensionPitchMoment = suspensionMomentError(spec, suspension, loads.wheels)
    local suspensionResidual = (suspension.verticalForce - loads.totalNormal) / math.max(1, spec.mass)
    local accelerationUp = upForce / math.max(1, spec.mass) + suspensionResidual * (G4.Config.suspension.verticalCorrection or 0)
    state.longitudinalAcceleration = M.clamp(accelerationForward, -25, 18)
    state.lateralAcceleration = M.clamp(accelerationRight, -18, 18)

    local maxDelta = G4.Config.maxCustomAcceleration * dt * G4.Config.customForceBlend * (profile.force or 1)
    local correction = M.toWorld(sample.basis, accelerationRight * dt * G4.Config.customForceBlend * profile.force,
        accelerationForward * dt * G4.Config.customForceBlend * profile.force,
        accelerationUp * dt * G4.Config.customForceBlend * profile.force)
    correction = M.limitVector(correction, maxDelta)
    if G4.Sync and G4.Sync.getVelocityCorrection then
        correction = M.add(correction, G4.Sync.getVelocityCorrection(vehicle, sample.velocity, dt))
    end
    if sample.canSimulate and G4.State.enabled then
        local desired = M.add(sample.velocity, correction)
        -- Do not hard-clamp velocity: native handling and aero provide a soft top-speed limit.
        if M.length(correction) > 0.0008 then G4.Adapter.setVelocityMps(vehicle, desired) end
        applyAngularMoment(vehicle, state, sample, rightForce, forwardForce,
            tireYawMoment(spec, tires.wheels), suspensionRollMoment, suspensionPitchMoment, dt, profile)
    end

    state.speedMps = speedMps
    state.speedKmh = speedMps * 3.6
    state.gear = transmission.gear
    state.rpm = transmission.rpm
    state.gearRatio = transmission.ratio
    state.shiftFactor = transmission.shiftFactor
    state.throttle = controls.throttle
    state.brake = controls.brake
    state.steering = controls.steer
    state.steerAngle = controls.steerAngle
    state.yawRate = M.dot(sample.angularVelocity, sample.basis.up)
    state.pitch = sample.rotation.pitch
    state.roll = sample.rotation.roll
    state.yaw = sample.rotation.yaw
    state.longitudinalG = state.longitudinalAcceleration / GRAVITY
    state.lateralG = state.lateralAcceleration / GRAVITY
    state.loads = loads.wheels
    state.tireWheels = summarizeWheels(tires.wheels, loads.wheels)
    state.suspensionWheels = suspension.wheels
    state.surfaceName = state.surface and state.surface.name or "asphalt"
    state.absActive = brakes.absActive
    state.engineTorque = drive.engineTorque
    state.aero = aero
    state.contacts = state.contacts
    state.lastVelocity = sample.velocity
    state.collisionTimeLeft = math.max(0, (state.collisionTimeLeft or 0) - dt)

    if G4.Calibration then G4.Calibration.update(state, dt) end
    if G4.Telemetry then G4.Telemetry.update(state, dt) end
    if G4.Sync and G4.Sync.clientTick then G4.Sync.clientTick(vehicle, state, dt) end
    state.outputs = {
        rightForce = rightForce, forwardForce = forwardForce, upForce = upForce,
        accelerationRight = accelerationRight, accelerationForward = accelerationForward,
        wheelForces = tires.wheels, suspension = suspension
    }
    return true
end
