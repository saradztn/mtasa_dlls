-- ============================================================================
-- MTA:SA Z1000-INSPIRED SYNTHETIC INLINE-FOUR AUDIO
-- Author: AI Agent (Arena.ai)
-- Module: Client-side 3D Layered Audio Engine
-- ============================================================================

local LOOP_DEFINITIONS = {
    { key = "idle", position = "engine", anchorGroup = "base" },
    { key = "low", position = "engine", anchorGroup = "base" },
    { key = "mid", position = "engine", anchorGroup = "base" },
    { key = "high", position = "engine", anchorGroup = "base" },
    { key = "redline", position = "engine", anchorGroup = "base" },
    { key = "accel", position = "engine", anchorGroup = "overlay" },
    { key = "lightAccel", position = "engine", anchorGroup = "overlay" },
    { key = "hardAccel", position = "engine", anchorGroup = "overlay" },
    { key = "decel", position = "rear", anchorGroup = "overlay" },
    { key = "engineBrake", position = "rear", anchorGroup = "overlay" },
    { key = "throttleRelease", position = "rear", anchorGroup = "overlay" },
    { key = "coast", position = "engine", anchorGroup = "overlay" },
    { key = "limiter", position = "rear", anchorGroup = "overlay" },
    { key = "intake", position = "front", anchorGroup = "overlay" },
    { key = "exhaust", position = "rear", anchorGroup = "overlay" }
}

local BASE_LAYER_KEYS = { "idle", "low", "mid", "high", "redline" }
local REQUIRED_SAMPLE_KEYS = {
    "idle", "low", "mid", "high", "redline",
    "accel", "decel", "engineBrake", "limiter"
}

local tracks = {}
local failedPoolRetry = {}
local sampleAvailable = {}
local oneTimeWarnings = {}
local audioReady = false
local localAudioMessage = ""
local runtimeDebug = Config.Debug == true
local debugHandlerAttached = false
local scanTimer = nil
local updateTimer = nil
local lastUpdateTick = nil
local testRig = {
    enabled = false,
    retiring = false,
    rpm = Config.Test.StartRPM,
    throttle = Config.Test.Throttle,
    sounds = {},
    currentVolumes = {},
    currentSpeeds = {},
    lastAppliedVolumes = {}
}

local function clamp(value, minimum, maximum)
    if value < minimum then
        return minimum
    end
    if value > maximum then
        return maximum
    end
    return value
end

local function safeNumber(value, fallback)
    if type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge then
        return value
    end
    return fallback
end

local function smoothstep(edge0, edge1, value)
    if edge0 == edge1 then
        return value >= edge1 and 1 or 0
    end
    local t = clamp((value - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)
end

local function approach(current, target, deltaSeconds, timeConstant)
    if timeConstant <= 0 then
        return target
    end
    local alpha = 1 - math.exp(-deltaSeconds / timeConstant)
    return current + (target - current) * alpha
end

local function warnOnce(key, message)
    if oneTimeWarnings[key] then
        return
    end
    oneTimeWarnings[key] = true
    outputDebugString("[Z1000 Audio] " .. message, 2)
end

local function chatMessage(message)
    outputChatBox("[Z1000] " .. message, 220, 231, 240)
end

local function isElementVehicle(vehicle)
    return isElement(vehicle) and getElementType(vehicle) == "vehicle"
end

local function isTargetVehicle(vehicle)
    if not isElementVehicle(vehicle) then
        return false
    end

    local model = getElementModel(vehicle)
    if Config.TargetModels[model] == true then
        return true
    end

    local targetData = Config.TargetElementData
    if targetData and targetData.Enabled and type(targetData.Key) == "string" then
        return getElementData(vehicle, targetData.Key) == targetData.Value
    end
    return false
end

local function getVehicleVelocity(vehicle)
    local vx, vy, vz = getElementVelocity(vehicle)
    if type(vx) ~= "number" or type(vy) ~= "number" or type(vz) ~= "number" then
        return 0, 0, 0
    end
    return vx, vy, vz
end

local function speedKmhFromVelocity(vx, vy, vz)
    -- MTA velocity is GTA units per 1/50 second; 1 GTA unit is approximately 1 m.
    return math.sqrt(vx * vx + vy * vy + vz * vz) * 180
end

local function readLocalAnalogControl(controlName)
    local value = 0
    if type(getPedAnalogControlState) == "function" then
        local ok, result = pcall(getPedAnalogControlState, localPlayer, controlName, true)
        if ok and type(result) == "number" then
            value = result
        end
    end

    if value <= 0.001 and type(getPedControlState) == "function" then
        local ok, pressed = pcall(getPedControlState, localPlayer, controlName)
        if ok and pressed then
            value = 1
        end
    end
    return clamp(safeNumber(value, 0), 0, 1)
end

local function getListenerInfo()
    local x, y, z = getCameraMatrix()
    if type(x) ~= "number" or type(y) ~= "number" or type(z) ~= "number" then
        x, y, z = getElementPosition(localPlayer)
    end

    local listenerEntity = getPedOccupiedVehicle(localPlayer) or localPlayer
    local vx, vy, vz = getVehicleVelocity(listenerEntity)
    return {
        x = x,
        y = y,
        z = z,
        vx = vx,
        vy = vy,
        vz = vz,
        dimension = getElementDimension(localPlayer),
        interior = getElementInterior(localPlayer)
    }
end

local function localOffsetToWorld(matrix, offset)
    local ox = safeNumber(offset and offset[1], 0)
    local oy = safeNumber(offset and offset[2], 0)
    local oz = safeNumber(offset and offset[3], 0)

    local right = matrix[1]
    local forward = matrix[2]
    local up = matrix[3]
    local position = matrix[4]
    return
        ox * right[1] + oy * forward[1] + oz * up[1] + position[1],
        ox * right[2] + oy * forward[2] + oz * up[2] + position[2],
        ox * right[3] + oy * forward[3] + oz * up[3] + position[3]
end

local function getVehiclePose(vehicle)
    local matrix = getElementMatrix(vehicle, false)
    if type(matrix) ~= "table" or type(matrix[2]) ~= "table" or type(matrix[4]) ~= "table" then
        local x, y, z = getElementPosition(vehicle)
        local rx, ry, rz = getElementRotation(vehicle)
        local yaw = math.rad(safeNumber(rz, 0))
        local forwardX = -math.sin(yaw)
        local forwardY = math.cos(yaw)
        return {
            engine = { x, y, z + 0.25 },
            front = { x + forwardX * 0.55, y + forwardY * 0.55, z + 0.28 },
            rear = { x - forwardX * 1.0, y - forwardY * 1.0, z + 0.22 },
            center = { x, y, z },
            forwardX = forwardX,
            forwardY = forwardY,
            forwardZ = 0
        }
    end

    local engineX, engineY, engineZ = localOffsetToWorld(matrix, Config.SourceOffsets.Engine)
    local frontX, frontY, frontZ = localOffsetToWorld(matrix, Config.SourceOffsets.Front)
    local rearX, rearY, rearZ = localOffsetToWorld(matrix, Config.SourceOffsets.Rear)
    return {
        engine = { engineX, engineY, engineZ },
        front = { frontX, frontY, frontZ },
        rear = { rearX, rearY, rearZ },
        center = { matrix[4][1], matrix[4][2], matrix[4][3] },
        forwardX = matrix[2][1],
        forwardY = matrix[2][2],
        forwardZ = matrix[2][3]
    }
end

local function sourcePositionFor(definition, pose)
    return pose[definition.position] or pose.engine
end

local function configure3DSound(sound, position, dimension, interior)
    if not isElement(sound) then
        return false
    end
    setSoundVolume(sound, 0)
    setElementPosition(sound, position[1], position[2], position[3])
    setElementDimension(sound, dimension)
    setElementInterior(sound, interior)
    setSoundMinDistance(sound, math.floor(Config.MinSoundDistance))
    setSoundMaxDistance(sound, math.floor(Config.MaxAudibleDistance))
    return true
end

local function stopAndDestroySound(sound)
    if isElement(sound) then
        stopSound(sound)
        if isElement(sound) then
            destroyElement(sound)
        end
    end
end

local function getSampleAnchor(key, anchorGroup)
    local rpmConfig = Config.RPM
    if anchorGroup == "base" then
        return safeNumber(rpmConfig.LayerAnchors[key], rpmConfig.Idle)
    end
    return safeNumber(rpmConfig.OverlayAnchors[key], rpmConfig.Idle)
end

local function validateAudioFiles()
    sampleAvailable = {}
    if not Config.AudioReady then
        return false, "Config.AudioReady is false; custom engine playback is disabled."
    end

    local missingRequired = {}
    for _, key in ipairs(BASE_LAYER_KEYS) do
        if not Config.LayerEnabled[key] then
            missingRequired[#missingRequired + 1] = key .. " (base loop disabled)"
        end
    end
    for _, key in ipairs(REQUIRED_SAMPLE_KEYS) do
        local path = Config.Samples[key]
        if type(path) == "string" and fileExists(path) then
            sampleAvailable[key] = true
        else
            sampleAvailable[key] = false
            missingRequired[#missingRequired + 1] = key
        end
    end

    if #missingRequired > 0 then
        return false, "Missing required processed samples: " .. table.concat(missingRequired, ", ")
    end

    for _, definition in ipairs(LOOP_DEFINITIONS) do
        local key = definition.key
        if Config.LayerEnabled[key] and sampleAvailable[key] == nil then
            local path = Config.Samples[key]
            sampleAvailable[key] = type(path) == "string" and fileExists(path)
            if not sampleAvailable[key] then
                warnOnce("missing-layer-" .. key, "Layer '" .. key .. "' is enabled but its sample file is missing; that layer is disabled.")
            end
        end
    end

    local optionalKeys = { "shift", "helmet" }
    for _, key in ipairs(optionalKeys) do
        local path = Config.Samples[key]
        sampleAvailable[key] = type(path) == "string" and fileExists(path)
        if not sampleAvailable[key] and ((key == "shift" and Config.ShiftTransientEnabled) or (key == "helmet" and Config.Interior.Enabled)) then
            warnOnce("missing-optional-" .. key, "Optional sample '" .. key .. "' is enabled but its file is missing.")
        end
    end

    return true
end

local function getEnabledLoopDefinitions()
    local enabled = {}
    for _, definition in ipairs(LOOP_DEFINITIONS) do
        if Config.LayerEnabled[definition.key] and sampleAvailable[definition.key] then
            enabled[#enabled + 1] = definition
        end
    end
    return enabled
end

local function getBaseWeights(rpm)
    local anchors = Config.RPM.LayerAnchors
    local keys = BASE_LAYER_KEYS
    local weights = { idle = 0, low = 0, mid = 0, high = 0, redline = 0 }

    if rpm <= anchors[keys[1]] then
        weights[keys[1]] = 1
        return weights
    end

    local lastKey = keys[#keys]
    if rpm >= anchors[lastKey] then
        weights[lastKey] = 1
        return weights
    end

    for index = 1, #keys - 1 do
        local lowerKey = keys[index]
        local upperKey = keys[index + 1]
        local lowerAnchor = anchors[lowerKey]
        local upperAnchor = anchors[upperKey]
        if rpm >= lowerAnchor and rpm <= upperAnchor then
            local blend = smoothstep(lowerAnchor, upperAnchor, rpm)
            -- Equal-power crossfade avoids a level hole between adjacent RPM layers.
            weights[lowerKey] = math.cos(blend * math.pi * 0.5)
            weights[upperKey] = math.sin(blend * math.pi * 0.5)
            return weights
        end
    end

    weights.idle = 1
    return weights
end

local function calculateLayerTargets(context)
    local targets = {}
    local weights = getBaseWeights(context.rpm)
    local throttle = clamp(context.throttle, 0, 1)
    local acceleration = clamp(context.positiveAccel, 0, 1)
    local deceleration = clamp(context.deceleration, 0, 1)
    local brake = clamp(context.brake, 0, 1)
    local speed = math.max(0, context.speedKmh)
    local noThrottle = 1 - smoothstep(0.025, 0.16, throttle)
    local speedFactor = smoothstep(Config.Estimator.EngineBrakeMinSpeedKmh,
        Config.Estimator.EngineBrakeMinSpeedKmh + 18, speed)
    local brakeIntensity = math.max(deceleration, brake)
    local shiftGain = 1 - Config.RPM.ShiftDip * clamp(context.shiftEnvelope or 0, 0, 1)
    local engineGain = context.engineOn and 1 or 0

    for _, key in ipairs(BASE_LAYER_KEYS) do
        targets[key] = weights[key] * shiftGain * engineGain
    end

    targets.accel = smoothstep(0.06, 0.68, throttle) * (0.48 + 0.52 * acceleration) * engineGain
    targets.lightAccel = smoothstep(0.04, 0.16, throttle)
        * (1 - smoothstep(0.34, 0.58, throttle)) * (0.35 + 0.65 * acceleration) * engineGain
    targets.hardAccel = smoothstep(0.54, 0.88, throttle)
        * (0.50 + 0.50 * acceleration) * engineGain

    targets.decel = math.max(brake, deceleration) * (1 - throttle * 0.70) * engineGain
    local gearFactor = context.gear and context.gear > 1 and 1 or 0.48
    targets.engineBrake = noThrottle * speedFactor * gearFactor
        * (0.22 + 0.78 * smoothstep(0.04, 0.55, brakeIntensity)) * engineGain
    targets.throttleRelease = clamp(context.throttleRelease or 0, 0, 1)
        * (0.55 + 0.45 * speedFactor) * engineGain
    targets.coast = noThrottle * speedFactor
        * (1 - smoothstep(0.06, 0.55, brakeIntensity)) * 0.72 * engineGain

    local rpm = context.rpm
    local limiter = smoothstep(Config.RPM.LimiterStart, Config.RPM.Maximum, rpm)
    targets.limiter = limiter * (throttle ^ 1.25) * engineGain
    targets.intake = throttle * (0.22 + 0.78 * clamp(context.frontFactor or 0.5, 0, 1)) * engineGain
    targets.exhaust = (0.22 + 0.50 * throttle + 0.28 * acceleration)
        * (0.22 + 0.78 * clamp(context.rearFactor or 0.5, 0, 1)) * engineGain

    for key, value in pairs(targets) do
        targets[key] = clamp(value, 0, 1)
    end
    return targets
end

local function getDopplerFactor(vehicleVelocity, listener, position)
    if not Config.Pitch.DopplerEnabled then
        return 1
    end

    local dx = position[1] - listener.x
    local dy = position[2] - listener.y
    local dz = position[3] - listener.z
    local distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    if distance < 0.5 then
        return 1
    end

    local directionX, directionY, directionZ = dx / distance, dy / distance, dz / distance
    local relativeX = (vehicleVelocity[1] - listener.vx) * 50
    local relativeY = (vehicleVelocity[2] - listener.vy) * 50
    local relativeZ = (vehicleVelocity[3] - listener.vz) * 50
    local radialSpeed = relativeX * directionX + relativeY * directionY + relativeZ * directionZ
    local speedOfSound = math.max(1, Config.Pitch.SpeedOfSoundMetresPerSecond)
    local factor = speedOfSound / math.max(speedOfSound * 0.5, speedOfSound + radialSpeed)
    local variation = Config.Pitch.DopplerMaxPercent
    return clamp(factor, 1 - variation, 1 + variation)
end

local function getPitchRate(rpm, anchor, dopplerFactor)
    if not Config.Pitch.Enabled then
        return clamp(dopplerFactor or 1, 0.90, 1.10)
    end
    local safeAnchor = math.max(1, anchor)
    local ratio = clamp(rpm / safeAnchor, 0.55, 1.55)
    local rate = ratio ^ Config.Pitch.Curve
    rate = clamp(rate, Config.Pitch.Min, Config.Pitch.Max)
    return clamp(rate * (dopplerFactor or 1), Config.Pitch.Min, Config.Pitch.Max)
end

local function getLayerState(context)
    if not context.engineOn then
        return "Engine off"
    end
    if context.rpm >= Config.RPM.LimiterStart and context.throttle > 0.60 then
        return "Rev limiter"
    end
    if context.rpm >= Config.RPM.Redline then
        return "Redline"
    end
    if (context.shiftEnvelope or 0) > 0.32 then
        return "Gear shift"
    end
    if (context.throttleRelease or 0) > 0.36 then
        return "Throttle release"
    end
    if context.throttle < 0.09 and context.speedKmh > Config.Estimator.EngineBrakeMinSpeedKmh
        and context.deceleration > 0.12 then
        return "Engine braking"
    end
    if context.throttle >= 0.58 and context.positiveAccel > 0.24 then
        return "Hard acceleration"
    end
    if context.throttle >= 0.10 and (context.positiveAccel > 0.04 or context.throttle > 0.38) then
        return "Light acceleration"
    end
    if context.throttle < 0.09 and context.speedKmh > 12 then
        return "Coasting"
    end
    if context.rpm >= Config.RPM.LayerAnchors.high then
        return "High RPM"
    end
    if context.rpm >= Config.RPM.LayerAnchors.mid then
        return "Mid RPM"
    end
    if context.rpm >= Config.RPM.LayerAnchors.low then
        return "Low RPM"
    end
    return "Idle"
end

local function speedAtGearTop(maxVelocity, gear, gearCount)
    if gear >= gearCount then
        return maxVelocity
    end
    local ratio = gear / gearCount
    return maxVelocity * (ratio ^ Config.RPM.GearSpeedExponent)
end

local function estimateInitialGear(speedKmh, maxVelocity, gearCount)
    local gear = 1
    while gear < gearCount and speedKmh > speedAtGearTop(maxVelocity, gear, gearCount) do
        gear = gear + 1
    end
    return gear
end

local function getVehicleHandlingValues(vehicle)
    local handling = getVehicleHandling(vehicle)
    if type(handling) ~= "table" then
        handling = {}
    end

    local maxVelocity = safeNumber(handling.maxVelocity, 210)
    maxVelocity = clamp(maxVelocity, 80, 500)
    local gearCount = math.floor(safeNumber(handling.numberOfGears, Config.RPM.DefaultGears) + 0.5)
    local gearOverride = math.floor(safeNumber(Config.RPM.GearCountOverride, 0))
    if gearOverride >= 1 then
        gearCount = gearOverride
    end
    gearCount = math.floor(clamp(gearCount, 1, 8))
    local engineAcceleration = safeNumber(handling.engineAcceleration, 10)
    return {
        maxVelocity = maxVelocity,
        gearCount = gearCount,
        engineAcceleration = engineAcceleration
    }
end

local function destroyTrack(track)
    if not track then
        return
    end

    for _, sound in pairs(track.sounds) do
        stopAndDestroySound(sound)
    end
    track.sounds = {}

    stopAndDestroySound(track.helmetSound)
    track.helmetSound = nil

    for _, transient in ipairs(track.transients) do
        stopAndDestroySound(transient.sound)
    end
    track.transients = {}

    if track.vehicle and tracks[track.vehicle] == track then
        tracks[track.vehicle] = nil
    end
end

local function beginTrackFade(track)
    if track and not track.retiring then
        track.retiring = true
        track.retireStarted = getTickCount()
    end
end

local function createLoopForTrack(track, definition, pose)
    local key = definition.key
    local path = Config.Samples[key]
    if not sampleAvailable[key] or type(path) ~= "string" then
        return false
    end

    local position = sourcePositionFor(definition, pose)
    local sound = playSound3D(path, position[1], position[2], position[3], true, false)
    if not isElement(sound) then
        warnOnce("create-loop-" .. key, "MTA could not open loop '" .. path .. "' (" .. key .. "). Check WAV format and meta.xml.")
        return false
    end

    configure3DSound(sound, position, getElementDimension(track.vehicle), getElementInterior(track.vehicle))
    track.sounds[key] = sound
    track.currentVolumes[key] = 0
    track.currentSpeeds[key] = 1
    track.positions[key] = { position[1], position[2], position[3] }
    return true
end

local function createTrack(vehicle, listener)
    if not isElementVehicle(vehicle) then
        return nil
    end

    local vx, vy, vz = getVehicleVelocity(vehicle)
    local speed = speedKmhFromVelocity(vx, vy, vz)
    local pose = getVehiclePose(vehicle)
    local handling = getVehicleHandlingValues(vehicle)
    local now = getTickCount()
    local track = {
        vehicle = vehicle,
        sounds = {},
        currentVolumes = {},
        currentSpeeds = {},
        lastAppliedVolumes = {},
        positions = {},
        transients = {},
        handling = handling,
        vx = vx,
        vy = vy,
        vz = vz,
        speedKmh = speed,
        previousSpeedKmh = speed,
        previousRawThrottle = 0,
        throttle = 0,
        acceleration = 0,
        rpm = Config.RPM.Idle,
        gear = estimateInitialGear(speed, handling.maxVelocity, handling.gearCount),
        lastShiftTick = now - Config.RPM.ShiftCooldownMs,
        shiftEnvelope = 0,
        throttleReleaseEnvelope = 0,
        master = 0,
        retiring = false,
        lastContext = nil,
        lastDistance = 0,
        dimension = getElementDimension(vehicle),
        interior = getElementInterior(vehicle),
        lastPose = pose
    }

    local baseLoopsReady = true
    for _, definition in ipairs(getEnabledLoopDefinitions()) do
        local created = createLoopForTrack(track, definition, pose)
        if definition.anchorGroup == "base" and not created then
            baseLoopsReady = false
        end
    end

    if not baseLoopsReady then
        for _, sound in pairs(track.sounds) do
            stopAndDestroySound(sound)
        end
        warnOnce("incomplete-base-pool", "At least one base RPM loop failed to load; custom pool was rejected so it cannot overlap the native engine sound.")
        return nil
    end

    tracks[vehicle] = track
    return track
end

local function updateVehicleGear(track, speedKmh, now)
    local gear = track.gear
    local count = track.handling.gearCount
    local shifted = false

    if now - track.lastShiftTick >= Config.RPM.ShiftCooldownMs then
        if gear < count then
            local upshiftSpeed = speedAtGearTop(track.handling.maxVelocity, gear, count)
                * Config.RPM.UpshiftHysteresis
            if speedKmh >= upshiftSpeed then
                gear = gear + 1
                shifted = true
            end
        end

        if not shifted and gear > 1 then
            local downshiftSpeed = speedAtGearTop(track.handling.maxVelocity, gear - 1, count)
                * Config.RPM.DownshiftHysteresis
            if speedKmh <= downshiftSpeed then
                gear = gear - 1
                shifted = true
            end
        end
    end

    if shifted then
        track.gear = gear
        track.lastShiftTick = now
        track.shiftEnvelope = 1
        return true
    end
    return false
end

local function triggerShiftTransient(track, pose, listener, vehicleVelocity, now)
    if not Config.ShiftTransientEnabled or not sampleAvailable.shift then
        return
    end
    if now - (track.lastShiftSoundTick or 0) < 260 then
        return
    end
    if #track.transients >= 1 then
        return
    end

    local path = Config.Samples.shift
    if type(path) ~= "string" then
        return
    end
    local position = pose.rear
    local sound = playSound3D(path, position[1], position[2], position[3], false, false)
    if not isElement(sound) then
        warnOnce("create-shift", "MTA could not open the optional shift transient sample.")
        return
    end

    configure3DSound(sound, position, getElementDimension(track.vehicle), getElementInterior(track.vehicle))
    local doppler = getDopplerFactor(vehicleVelocity, listener, position)
    setSoundSpeed(sound, getPitchRate(track.rpm, getSampleAnchor("high", "base"), doppler))
    setSoundVolume(sound, Config.Volume.Master * Config.Volume.shift * 0.72)
    track.transients[#track.transients + 1] = {
        sound = sound,
        expires = now + 1200,
        baseVolume = Config.Volume.Master * Config.Volume.shift * 0.72
    }
    track.lastShiftSoundTick = now
end

local function updateTrackDynamics(track, deltaSeconds, now, listener, pose)
    local vehicle = track.vehicle
    local vx, vy, vz = getVehicleVelocity(vehicle)
    local speedKmh = speedKmhFromVelocity(vx, vy, vz)
    local rawAcceleration = (speedKmh - track.previousSpeedKmh) / math.max(deltaSeconds, 0.01)
    rawAcceleration = clamp(rawAcceleration, -90, 90)
    track.acceleration = approach(track.acceleration or 0, rawAcceleration, deltaSeconds,
        Config.Estimator.AccelerationSmoothingSeconds)
    local acceleration = track.acceleration

    local positiveAccel = 0
    local deceleration = 0
    local localDriver = getVehicleOccupant(vehicle, 0) == localPlayer
    local rawThrottle
    local rawBrake

    if localDriver then
        rawThrottle = readLocalAnalogControl("accelerate")
        rawBrake = readLocalAnalogControl("brake_reverse")
    else
        local fullAcceleration = Config.Estimator.RemoteFullAccelerationKmhPerSecond
        if track.handling.engineAcceleration > 0 then
            fullAcceleration = clamp(fullAcceleration * (track.handling.engineAcceleration / 10), 16, 55)
        end
        positiveAccel = clamp((acceleration - Config.Estimator.RemoteThrottleNoiseFloorKmhPerSecond)
            / fullAcceleration, 0, 1)
        deceleration = clamp((-acceleration - Config.Estimator.RemoteThrottleNoiseFloorKmhPerSecond)
            / math.max(12, fullAcceleration), 0, 1)
        rawThrottle = positiveAccel
        rawBrake = deceleration
    end

    if localDriver then
        local fullAcceleration = Config.Estimator.RemoteFullAccelerationKmhPerSecond
        positiveAccel = clamp((acceleration - Config.Estimator.RemoteThrottleNoiseFloorKmhPerSecond)
            / fullAcceleration, 0, 1)
        deceleration = clamp((-acceleration - Config.Estimator.RemoteThrottleNoiseFloorKmhPerSecond)
            / math.max(12, fullAcceleration), 0, 1)
    end

    local throttleTau = rawThrottle > track.throttle
        and Config.Estimator.ThrottleRiseSeconds or Config.Estimator.ThrottleFallSeconds
    track.throttle = approach(track.throttle, rawThrottle, deltaSeconds, throttleTau)
    track.throttle = clamp(track.throttle, 0, 1)

    if track.previousRawThrottle - rawThrottle >= Config.Estimator.ThrottleReleaseThreshold then
        track.throttleReleaseEnvelope = 1
    else
        track.throttleReleaseEnvelope = track.throttleReleaseEnvelope
            * math.exp(-deltaSeconds / math.max(0.05, Config.Estimator.ThrottleReleaseDecaySeconds))
    end
    track.previousRawThrottle = rawThrottle

    local gearChanged = updateVehicleGear(track, speedKmh, now)
    if gearChanged then
        triggerShiftTransient(track, pose, listener, { vx, vy, vz }, now)
    end
    track.shiftEnvelope = track.shiftEnvelope
        * math.exp(-deltaSeconds / math.max(0.05, Config.RPM.ShiftDipSeconds))

    local gearTopSpeed = speedAtGearTop(track.handling.maxVelocity, track.gear, track.handling.gearCount)
    local roadRatio = clamp(speedKmh / math.max(1, gearTopSpeed), 0, 1.12)
    local range = math.max(1, Config.RPM.Redline - Config.RPM.Idle)
    local roadRPM = range * (roadRatio ^ 0.94)
    local launchFactor = clamp(1 - speedKmh / math.max(1, Config.Estimator.LaunchSpeedKmh), 0, 1)
    local launchRPM = range * track.throttle * Config.Estimator.LaunchRevRange * launchFactor
    local throttleLoadRPM = range * track.throttle * Config.Estimator.ThrottleLoadRange
    local accelerationLoadRPM = range * positiveAccel * Config.Estimator.AccelerationLoadRange
    local rpmTarget = Config.RPM.Idle + roadRPM + launchRPM + throttleLoadRPM + accelerationLoadRPM
    rpmTarget = clamp(rpmTarget, Config.RPM.Idle, Config.RPM.Maximum)

    local engineOn = not Config.RespectVehicleEngineState or getVehicleEngineState(vehicle) == true
    if not engineOn then
        rpmTarget = 0
    end
    local rpmTau = rpmTarget > track.rpm
        and Config.Estimator.RPMRiseSeconds or Config.Estimator.RPMFallSeconds
    track.rpm = approach(track.rpm, rpmTarget, deltaSeconds, rpmTau)
    if engineOn then
        track.rpm = clamp(track.rpm, Config.RPM.Idle, Config.RPM.Maximum)
    else
        track.rpm = math.max(0, track.rpm)
    end

    local dx = listener.x - pose.center[1]
    local dy = listener.y - pose.center[2]
    local dz = listener.z - pose.center[3]
    local distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    local directionLength = math.max(distance, 0.001)
    local cameraDot = (dx * pose.forwardX + dy * pose.forwardY + dz * pose.forwardZ) / directionLength
    local frontFactor = 0.25 + 0.75 * smoothstep(-0.10, 0.72, cameraDot)
    local rearFactor = 0.25 + 0.75 * smoothstep(-0.10, 0.72, -cameraDot)

    local context = {
        rpm = track.rpm,
        speedKmh = speedKmh,
        throttle = track.throttle,
        rawThrottle = rawThrottle,
        positiveAccel = positiveAccel,
        deceleration = deceleration,
        brake = rawBrake,
        gear = track.gear,
        engineOn = engineOn,
        shiftEnvelope = track.shiftEnvelope,
        throttleRelease = track.throttleReleaseEnvelope,
        frontFactor = frontFactor,
        rearFactor = rearFactor
    }

    track.vx, track.vy, track.vz = vx, vy, vz
    track.speedKmh = speedKmh
    track.previousSpeedKmh = speedKmh
    track.lastContext = context
    track.lastPose = pose
    track.lastDistance = distance
    return context, { vx, vy, vz }, distance
end

local function updateTrackSoundPositions(track, pose)
    local dimension = getElementDimension(track.vehicle)
    local interior = getElementInterior(track.vehicle)
    if dimension ~= track.dimension or interior ~= track.interior then
        for _, sound in pairs(track.sounds) do
            if isElement(sound) then
                setElementDimension(sound, dimension)
                setElementInterior(sound, interior)
            end
        end
        track.dimension = dimension
        track.interior = interior
    end

    for _, definition in ipairs(LOOP_DEFINITIONS) do
        local sound = track.sounds[definition.key]
        if isElement(sound) then
            local position = sourcePositionFor(definition, pose)
            local previous = track.positions[definition.key]
            if not previous
                or (position[1] - previous[1]) ^ 2 + (position[2] - previous[2]) ^ 2
                    + (position[3] - previous[3]) ^ 2 > 0.0025 then
                setElementPosition(sound, position[1], position[2], position[3])
                track.positions[definition.key] = { position[1], position[2], position[3] }
            end
        end
    end
end

local function updateTransientSounds(track, now, fade)
    for index = #track.transients, 1, -1 do
        local transient = track.transients[index]
        if not isElement(transient.sound) or now >= transient.expires then
            stopAndDestroySound(transient.sound)
            table.remove(track.transients, index)
        else
            setSoundVolume(transient.sound, transient.baseVolume * fade)
        end
    end
end

local function updateHelmetSound(track, context, deltaSeconds, fade, now)
    local shouldPlay = Config.Interior.Enabled and sampleAvailable.helmet
        and isElementVehicle(track.vehicle)
        and getVehicleOccupant(track.vehicle, 0) == localPlayer
        and context.engineOn and not track.retiring

    if shouldPlay and not isElement(track.helmetSound) then
        local path = Config.Samples.helmet
        local sound = playSound(path, true, false)
        if isElement(sound) then
            setSoundVolume(sound, 0)
            track.helmetSound = sound
            track.helmetVolume = 0
            track.helmetSpeed = 1
        else
            warnOnce("create-helmet", "MTA could not open the optional 2D helmet sample.")
        end
    end

    if isElement(track.helmetSound) then
        local target = 0
        if shouldPlay then
            target = Config.Volume.Master * Config.Interior.Volume * Config.Volume.helmet
                * (0.55 + 0.25 * context.throttle + 0.20 * smoothstep(900, 7000, context.rpm))
        end
        track.helmetVolume = approach(track.helmetVolume or 0, target, deltaSeconds,
            target > (track.helmetVolume or 0) and Config.LayerAttackSeconds or Config.LayerReleaseSeconds)
        track.helmetVolume = clamp(track.helmetVolume, 0, 1)
        setSoundVolume(track.helmetSound, track.helmetVolume * fade)

        local pitch = getPitchRate(context.rpm, getSampleAnchor("helmet", "overlay"), 1)
        if math.abs(pitch - (track.helmetSpeed or 1)) > 0.012 then
            setSoundSpeed(track.helmetSound, pitch)
            track.helmetSpeed = pitch
        end

        if not shouldPlay and track.helmetVolume < 0.008 then
            stopAndDestroySound(track.helmetSound)
            track.helmetSound = nil
            track.helmetVolume = 0
        end
    end
end

local function updateTrackMix(track, context, pose, vehicleVelocity, listener, deltaSeconds, now)
    local fadeTarget = track.retiring and 0 or 1
    local fadeTime = track.retiring and Config.TrackFadeOutSeconds or Config.TrackFadeInSeconds
    track.master = approach(track.master, fadeTarget, deltaSeconds, math.max(0.03, fadeTime))
    track.master = clamp(track.master, 0, 1)

    local targets = calculateLayerTargets(context)
    local localDriver = isElementVehicle(track.vehicle) and getVehicleOccupant(track.vehicle, 0) == localPlayer
    local useHelmet = Config.Interior.Enabled and sampleAvailable.helmet and localDriver and context.engineOn
    local exteriorDuck = useHelmet and Config.Interior.ExteriorDuck or 1

    for _, definition in ipairs(LOOP_DEFINITIONS) do
        local key = definition.key
        local sound = track.sounds[key]
        if isElement(sound) then
            local target = 0
            if not track.retiring and context.engineOn then
                target = Config.Volume.Master * safeNumber(Config.Volume[key], 0.30)
                    * (targets[key] or 0) * exteriorDuck
            end
            local current = track.currentVolumes[key] or 0
            local tau = target > current and Config.LayerAttackSeconds or Config.LayerReleaseSeconds
            current = clamp(approach(current, target, deltaSeconds, math.max(0.02, tau)), 0, 1)
            local appliedVolume = clamp(current * track.master, 0, 1)
            if math.abs(appliedVolume - (track.lastAppliedVolumes[key] or -1)) > 0.006 then
                setSoundVolume(sound, appliedVolume)
                track.lastAppliedVolumes[key] = appliedVolume
            end
            track.currentVolumes[key] = current

            local anchor = getSampleAnchor(key, definition.anchorGroup)
            local position = sourcePositionFor(definition, pose)
            local doppler = getDopplerFactor(vehicleVelocity, listener, position)
            local pitch = getPitchRate(context.rpm, anchor, doppler)
            if math.abs(pitch - (track.currentSpeeds[key] or 1)) > 0.012 then
                setSoundSpeed(sound, pitch)
                track.currentSpeeds[key] = pitch
            end
        end
    end

    updateHelmetSound(track, context, deltaSeconds, track.master, now)
    updateTransientSounds(track, now, track.master)
    track.currentLayer = getLayerState(context)
end

local function updateWorldTrack(track, deltaSeconds, now, listener)
    if not track.retiring and not isElementVehicle(track.vehicle) then
        beginTrackFade(track)
    end

    if not track.retiring and isElementVehicle(track.vehicle) then
        local pose = getVehiclePose(track.vehicle)
        local context, velocity = updateTrackDynamics(track, deltaSeconds, now, listener, pose)
        updateTrackSoundPositions(track, pose)
        updateTrackMix(track, context, pose, velocity, listener, deltaSeconds, now)
    else
        local context = track.lastContext or {
            rpm = track.rpm or 0,
            speedKmh = track.speedKmh or 0,
            throttle = 0,
            positiveAccel = 0,
            deceleration = 0,
            brake = 0,
            gear = track.gear or 1,
            engineOn = false,
            shiftEnvelope = 0,
            throttleRelease = 0,
            frontFactor = 0.5,
            rearFactor = 0.5
        }
        context = {
            rpm = context.rpm,
            speedKmh = context.speedKmh,
            throttle = context.throttle,
            positiveAccel = context.positiveAccel,
            deceleration = context.deceleration,
            brake = context.brake,
            gear = context.gear,
            engineOn = false,
            shiftEnvelope = context.shiftEnvelope,
            throttleRelease = context.throttleRelease,
            frontFactor = context.frontFactor,
            rearFactor = context.rearFactor
        }
        local pose = track.lastPose or { engine = { 0, 0, 0 }, front = { 0, 0, 0 }, rear = { 0, 0, 0 } }
        updateTrackMix(track, context, pose, { track.vx or 0, track.vy or 0, track.vz or 0 }, listener, deltaSeconds, now)
    end

    if track.retiring and track.master < 0.012 then
        destroyTrack(track)
    end
end

local function createTestRigSounds()
    if not audioReady then
        return false
    end
    for _, definition in ipairs(getEnabledLoopDefinitions()) do
        local key = definition.key
        if not isElement(testRig.sounds[key]) then
            local path = Config.Samples[key]
            local sound = playSound(path, true, false)
            if isElement(sound) then
                setSoundVolume(sound, 0)
                testRig.sounds[key] = sound
                testRig.currentVolumes[key] = 0
                testRig.currentSpeeds[key] = 1
            else
                warnOnce("test-create-" .. key, "MTA could not open test sample '" .. tostring(path) .. "'.")
            end
        end
    end
    return true
end

local function stopTestRigNow()
    for _, sound in pairs(testRig.sounds) do
        stopAndDestroySound(sound)
    end
    testRig.sounds = {}
    testRig.currentVolumes = {}
    testRig.currentSpeeds = {}
    testRig.lastAppliedVolumes = {}
    testRig.enabled = false
    testRig.retiring = false
end

local function updateTestRig(deltaSeconds)
    if not testRig.enabled and not testRig.retiring then
        return
    end

    local throttle = testRig.enabled and testRig.throttle or 0
    local rpm = testRig.rpm
    local context = {
        rpm = rpm,
        speedKmh = testRig.enabled and 36 or 0,
        throttle = throttle,
        positiveAccel = testRig.enabled and clamp((throttle - 0.08) / 0.86, 0, 1) or 0,
        deceleration = 0,
        brake = 0,
        gear = Config.Test.Gear,
        engineOn = testRig.enabled,
        shiftEnvelope = 0,
        throttleRelease = 0,
        frontFactor = 0.5,
        rearFactor = 0.5
    }
    local targets = calculateLayerTargets(context)

    for _, definition in ipairs(getEnabledLoopDefinitions()) do
        local key = definition.key
        local sound = testRig.sounds[key]
        if isElement(sound) then
            local target = testRig.enabled
                and Config.Volume.Master * safeNumber(Config.Volume[key], 0.30) * (targets[key] or 0)
                or 0
            local current = testRig.currentVolumes[key] or 0
            local tau = target > current and Config.LayerAttackSeconds or Config.LayerReleaseSeconds
            current = approach(current, target, deltaSeconds, tau)
            testRig.currentVolumes[key] = current
            if math.abs(current - (testRig.lastAppliedVolumes[key] or -1)) > 0.006 then
                setSoundVolume(sound, current)
                testRig.lastAppliedVolumes[key] = current
            end

            local pitch = getPitchRate(rpm, getSampleAnchor(key, definition.anchorGroup), 1)
            if math.abs(pitch - (testRig.currentSpeeds[key] or 1)) > 0.012 then
                setSoundSpeed(sound, pitch)
                testRig.currentSpeeds[key] = pitch
            end
        end
    end

    if testRig.retiring then
        local peak = 0
        for _, value in pairs(testRig.currentVolumes) do
            peak = math.max(peak, value)
        end
        if peak < 0.008 then
            stopTestRigNow()
        end
    end
end

local function countTracks()
    local count = 0
    for _ in pairs(tracks) do
        count = count + 1
    end
    return count
end

local function scanVehicles()
    if not audioReady or not isElement(localPlayer) then
        return
    end

    local listener = getListenerInfo()
    local scanRadius = Config.MaxAudibleDistance + Config.DistanceHysteresis
    local scanRadiusSquared = scanRadius * scanRadius
    local candidates = {}
    local vehicles = getElementsByType("vehicle", root, true)

    for _, vehicle in ipairs(vehicles) do
        if isTargetVehicle(vehicle)
            and getElementDimension(vehicle) == listener.dimension
            and getElementInterior(vehicle) == listener.interior then
            local x, y, z = getElementPosition(vehicle)
            local dx, dy, dz = x - listener.x, y - listener.y, z - listener.z
            local distanceSquared = dx * dx + dy * dy + dz * dz
            if distanceSquared <= scanRadiusSquared then
                candidates[#candidates + 1] = {
                    vehicle = vehicle,
                    distanceSquared = distanceSquared
                }
            end
        end
    end

    table.sort(candidates, function(a, b)
        return a.distanceSquared < b.distanceSquared
    end)

    local maximum = math.max(1, math.floor(safeNumber(Config.MaxTrackedVehicles, 3)))
    local wanted = {}
    local wantedCount = math.min(#candidates, maximum)
    for index = 1, wantedCount do
        wanted[candidates[index].vehicle] = candidates[index].distanceSquared
    end

    for vehicle, track in pairs(tracks) do
        if wanted[vehicle] then
            track.retiring = false
            track.lastDistance = math.sqrt(wanted[vehicle])
        else
            beginTrackFade(track)
        end
    end

    local currentCount = countTracks()
    local now = getTickCount()
    for index = 1, wantedCount do
        local vehicle = candidates[index].vehicle
        local retryAt = failedPoolRetry[vehicle]
        if retryAt and now >= retryAt then
            failedPoolRetry[vehicle] = nil
            retryAt = nil
        end
        if not tracks[vehicle] and not retryAt and currentCount < maximum then
            local track = createTrack(vehicle, listener)
            if track then
                track.lastDistance = math.sqrt(candidates[index].distanceSquared)
                currentCount = currentCount + 1
            else
                failedPoolRetry[vehicle] = now + 5000
            end
        end
    end
end

local function updateAllSounds()
    local now = getTickCount()
    local deltaSeconds = 0.05
    if lastUpdateTick then
        deltaSeconds = clamp((now - lastUpdateTick) / 1000, 0.01, 0.12)
    end
    lastUpdateTick = now

    updateTestRig(deltaSeconds)
    if not audioReady then
        return
    end

    local listener = getListenerInfo()
    for _, track in pairs(tracks) do
        updateWorldTrack(track, deltaSeconds, now, listener)
    end
end

local function onClientWorldSound(group, index)
    if not audioReady or not Config.SuppressStockSound then
        return
    end
    if not Config.NativeEngineGroups[group] then
        return
    end

    local emitter = source
    if not isElementVehicle(emitter) or not isTargetVehicle(emitter) then
        return
    end

    local track = tracks[emitter]
    if not track then
        return
    end
    for _, key in ipairs(BASE_LAYER_KEYS) do
        if not isElement(track.sounds[key]) then
            return
        end
    end

    if Config.DebugWorldSounds then
        warnOnce("world-sound-" .. tostring(group) .. "-" .. tostring(index),
            "Filtered target-bike native sound group " .. tostring(group) .. ", index " .. tostring(index) .. ".")
    end
    cancelEvent()
end

local function getDebugTrack()
    local occupied = getPedOccupiedVehicle(localPlayer)
    if occupied and tracks[occupied] then
        return tracks[occupied]
    end

    local nearest = nil
    local nearestDistance = math.huge
    for _, track in pairs(tracks) do
        if not track.retiring and track.lastDistance < nearestDistance then
            nearest = track
            nearestDistance = track.lastDistance
        end
    end
    return nearest
end

local function drawDebugOverlay()
    local screenWidth, screenHeight = guiGetScreenSize()
    local x = screenWidth - 355
    local y = 120
    local width = 340
    local height = 172
    dxDrawRectangle(x, y, width, height, tocolor(10, 15, 20, 205), false)

    local track = getDebugTrack()
    local lines = {
        "Z1000 AUDIO DEBUG  |  " .. (audioReady and "AUDIO READY" or "AUDIO NOT READY"),
        "Active tracks: " .. tostring(countTracks()) .. "/" .. tostring(Config.MaxTrackedVehicles),
        "Test rig: " .. (testRig.enabled and "ON" or (testRig.retiring and "FADING" or "OFF"))
    }

    if track and track.lastContext then
        local context = track.lastContext
        lines[#lines + 1] = string.format("RPM: %d  |  speed: %.1f km/h", math.floor(context.rpm + 0.5), context.speedKmh)
        lines[#lines + 1] = string.format("Throttle: %.2f  |  gear: %d", context.throttle, context.gear)
        lines[#lines + 1] = "Layer/state: " .. tostring(track.currentLayer or getLayerState(context))
        lines[#lines + 1] = string.format("Distance: %.1f m  |  vehicle model: %d", track.lastDistance, getElementModel(track.vehicle))
    else
        lines[#lines + 1] = "No tracked target vehicle in range."
        if testRig.enabled then
            lines[#lines + 1] = string.format("Test RPM: %d  |  throttle: %.2f", testRig.rpm, testRig.throttle)
        end
    end

    dxDrawText(table.concat(lines, "\n"), x + 10, y + 9, x + width - 10, y + height - 8,
        tocolor(238, 244, 250, 255), 1, "default-bold", "left", "top", false, false, false, true)
end

local function setDebugEnabled(enabled)
    runtimeDebug = enabled == true
    if runtimeDebug and not debugHandlerAttached then
        debugHandlerAttached = addEventHandler("onClientRender", root, drawDebugOverlay)
    elseif not runtimeDebug and debugHandlerAttached then
        removeEventHandler("onClientRender", root, drawDebugOverlay)
        debugHandlerAttached = false
    end
end

local function commandDebug()
    setDebugEnabled(not runtimeDebug)
    chatMessage("Debug overlay " .. (runtimeDebug and "enabled." or "disabled."))
end

local function commandTestSound()
    if not audioReady then
        chatMessage("Custom audio is disabled or incomplete. Check the WAV set and Config.AudioReady in config.lua; see README.txt.")
        return
    end

    if testRig.enabled then
        testRig.enabled = false
        testRig.retiring = true
        chatMessage("Test mix is fading out.")
    else
        testRig.enabled = true
        testRig.retiring = false
        testRig.rpm = clamp(Config.Test.StartRPM, Config.RPM.Idle, Config.RPM.Maximum)
        testRig.throttle = clamp(Config.Test.Throttle, 0, 1)
        createTestRigSounds()
        chatMessage("2D test mix started. Use /z1000rpm <rpm> [throttle] or /z1000stop.")
    end
end

local function commandTestRPM(_, rpmArgument, throttleArgument)
    if not audioReady then
        chatMessage("Custom audio is disabled or incomplete. Check the WAV set and Config.AudioReady in config.lua.")
        return
    end

    local rpm = tonumber(rpmArgument)
    if not rpm then
        chatMessage("Usage: /z1000rpm <rpm> [throttle 0-1]")
        return
    end

    testRig.rpm = clamp(rpm, Config.RPM.Idle, Config.RPM.Maximum)
    if throttleArgument ~= nil then
        local throttle = tonumber(throttleArgument)
        if not throttle then
            chatMessage("Throttle must be a number between 0 and 1.")
            return
        end
        testRig.throttle = clamp(throttle, 0, 1)
    elseif testRig.rpm >= Config.RPM.LimiterStart then
        testRig.throttle = 1
    else
        testRig.throttle = clamp(Config.Test.Throttle, 0, 1)
    end

    testRig.enabled = true
    testRig.retiring = false
    createTestRigSounds()
    chatMessage(string.format("Test mix: %d RPM, throttle %.2f (2D local preview).", math.floor(testRig.rpm + 0.5), testRig.throttle))
end

local function commandStopTest()
    if not testRig.enabled and not testRig.retiring then
        chatMessage("No test mix is active.")
        return
    end
    testRig.enabled = false
    testRig.retiring = true
    chatMessage("Test mix is fading out; world vehicle audio is unchanged.")
end

local function onResourceStart()
    audioReady, localAudioMessage = validateAudioFiles()
    if not audioReady then
        outputDebugString("[Z1000 Audio] " .. localAudioMessage, 2)
        if Config.AudioReady then
            outputDebugString("[Z1000 Audio] Native vehicle sounds were left untouched because the custom mix is incomplete.", 2)
        end
    else
        outputDebugString("[Z1000 Audio] Layered audio ready; enabled loops: " .. tostring(#getEnabledLoopDefinitions()) .. ".", 1)
        if Config.SuppressStockSound then
            addEventHandler("onClientWorldSound", root, onClientWorldSound)
        end
        addEventHandler("onClientElementDestroy", root, function()
            local destroyed = source
            failedPoolRetry[destroyed] = nil
            local track = tracks[destroyed]
            if track then
                beginTrackFade(track)
            end
        end)
        addEventHandler("onClientPlayerVehicleEnter", localPlayer, scanVehicles)
        addEventHandler("onClientPlayerVehicleExit", localPlayer, scanVehicles)
        scanVehicles()
        scanTimer = setTimer(scanVehicles, math.max(150, Config.ScanInterval), 0)
    end

    if audioReady then
        updateTimer = setTimer(updateAllSounds, math.max(25, Config.UpdateInterval), 0)
    end
    if runtimeDebug then
        setDebugEnabled(true)
    end
end

local function onResourceStop()
    if scanTimer and isTimer(scanTimer) then
        killTimer(scanTimer)
    end
    if updateTimer and isTimer(updateTimer) then
        killTimer(updateTimer)
    end

    for _, track in pairs(tracks) do
        destroyTrack(track)
    end
    tracks = {}
    failedPoolRetry = {}
    stopTestRigNow()

    if debugHandlerAttached then
        removeEventHandler("onClientRender", root, drawDebugOverlay)
        debugHandlerAttached = false
    end
end

addCommandHandler("z1000debug", commandDebug)
addCommandHandler("z1000sound", commandTestSound)
addCommandHandler("z1000rpm", commandTestRPM)
addCommandHandler("z1000stop", commandStopTest)

addEventHandler("onClientResourceStart", resourceRoot, onResourceStart)
addEventHandler("onClientResourceStop", resourceRoot, onResourceStop)
