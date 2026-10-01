GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
local M = G4.Math
G4.Adapter = { handlingSnapshots = setmetatable({}, { __mode = "k" }) }
local A = G4.Adapter
local VELOCITY_TICKS_PER_SECOND = 50 -- MTA velocity is GTA units per 1/50 s; one GTA unit is one metre.

local handlingProperties = {
    "mass", "turnMass", "dragCoeff", "centerOfMass", "tractionMultiplier", "tractionLoss", "tractionBias",
    "numberOfGears", "maxVelocity", "engineAcceleration", "engineInertia", "driveType",
    "brakeDeceleration", "brakeBias", "steeringLock", "suspensionForceLevel",
    "suspensionDamping", "suspensionHighSpeedDamping", "suspensionUpperLimit", "suspensionLowerLimit",
    "suspensionFrontRearBias", "suspensionAntiDiveMultiplier"
}

local function vectorFromRow(row, fallback)
    if type(row) ~= "table" then return fallback end
    local x = tonumber(row[1] or row.x)
    local y = tonumber(row[2] or row.y)
    local z = tonumber(row[3] or row.z)
    if not x or not y or not z then return fallback end
    return M.normalize({ x = x, y = y, z = z }, fallback)
end

local function callRotation(vehicle)
    local ok, rx, ry, rz = pcall(getElementRotation, vehicle, "ZYX")
    if not ok or not G4.isFinite(rx) then rx, ry, rz = getElementRotation(vehicle) end
    return tonumber(rx) or 0, tonumber(ry) or 0, tonumber(rz) or 0
end

function A.getVelocityMps(vehicle)
    if not isElement(vehicle) then return { x = 0, y = 0, z = 0 } end
    local ok, x, y, z = pcall(getElementVelocity, vehicle)
    if not ok or not G4.isFinite(x) then return { x = 0, y = 0, z = 0 } end
    return { x = x * VELOCITY_TICKS_PER_SECOND, y = y * VELOCITY_TICKS_PER_SECOND, z = z * VELOCITY_TICKS_PER_SECOND }
end

function A.getBasis(vehicle)
    local matrix
    local ok, result = pcall(getElementMatrix, vehicle, false)
    if ok then matrix = result end
    if type(matrix) == "table" then
        local right = vectorFromRow(matrix[1], nil)
        local forward = vectorFromRow(matrix[2], nil)
        local up = vectorFromRow(matrix[3], nil)
        local position = matrix[4]
        if right and forward and up and type(position) == "table" then
            return {
                right = right, forward = forward, up = up,
                position = { x = tonumber(position[1] or position.x) or 0, y = tonumber(position[2] or position.y) or 0, z = tonumber(position[3] or position.z) or 0 }
            }
        end
    end
    local x, y, z = getElementPosition(vehicle)
    local _, _, rz = callRotation(vehicle)
    local yaw = math.rad(rz)
    return {
        right = { x = math.cos(yaw), y = math.sin(yaw), z = 0 },
        forward = { x = -math.sin(yaw), y = math.cos(yaw), z = 0 },
        up = { x = 0, y = 0, z = 1 },
        position = { x = x or 0, y = y or 0, z = z or 0 }
    }
end

function A.getAngularVelocity(vehicle)
    if not isElement(vehicle) or type(getElementAngularVelocity) ~= "function" then
        return { x = 0, y = 0, z = 0 }
    end
    local ok, x, y, z = pcall(getElementAngularVelocity, vehicle)
    if not ok or not G4.isFinite(x) then return { x = 0, y = 0, z = 0 } end
    return { x = x * VELOCITY_TICKS_PER_SECOND, y = y * VELOCITY_TICKS_PER_SECOND, z = z * VELOCITY_TICKS_PER_SECOND }
end

function A.sample(vehicle)
    if not isElement(vehicle) or getElementType(vehicle) ~= "vehicle" then return nil end
    local basis = A.getBasis(vehicle)
    local velocity = A.getVelocityMps(vehicle)
    local rx, ry, rz = callRotation(vehicle)
    local angular = A.getAngularVelocity(vehicle)
    local controller = getVehicleController(vehicle)
    local syncer = controller == localPlayer
    if type(isElementSyncer) == "function" then
        local ok, value = pcall(isElementSyncer, vehicle)
        if ok then syncer = value == true end
    end
    local localVelocity = M.toLocal(basis, velocity)
    return {
        basis = basis, velocity = velocity, localVelocity = localVelocity,
        angularVelocity = angular, rotation = { roll = rx, pitch = ry, yaw = rz },
        controller = controller, canSimulate = controller == localPlayer and syncer,
        speed = M.length(velocity)
    }
end

local function analog(ped, control)
    if type(getPedAnalogControlState) == "function" then
        local ok, value = pcall(getPedAnalogControlState, ped, control, true)
        if ok and G4.isFinite(value) then return M.clamp(value, 0, 1) end
    end
    if type(getPedControlState) == "function" and getPedControlState(ped, control) then return 1 end
    return 0
end

function A.readControls(ped)
    if not isElement(ped) then return { throttle = 0, brake = 0, steer = 0, handbrake = false } end
    local left = analog(ped, "vehicle_left")
    local right = analog(ped, "vehicle_right")
    return {
        throttle = analog(ped, "accelerate"),
        brake = analog(ped, "brake_reverse"),
        steer = M.clamp(right - left, -1, 1),
        handbrake = getPedControlState(ped, "handbrake") == true,
        reverse = getPedControlState(ped, "brake_reverse") == true,
        reverseThrottle = analog(ped, "brake_reverse")
    }
end

function A.getWheelContacts(vehicle, className)
    local contacts = { FL = true, FR = true, RL = true, RR = true }
    if className == "motorcycle" then contacts.FR, contacts.RR = false, false end
    if type(isVehicleWheelOnGround) == "function" then
        -- IDs documented by MTA: 0 front-left, 1 rear-left, 2 front-right, 3 rear-right.
        local wheelIds = { FL = 0, RL = 1, FR = 2, RR = 3 }
        for name, wheelId in pairs(wheelIds) do
            if className ~= "motorcycle" or name == "FL" or name == "RL" then
                local ok, value = pcall(isVehicleWheelOnGround, vehicle, wheelId)
                if ok and type(value) == "boolean" then contacts[name] = value end
            end
        end
    elseif type(isVehicleOnGround) == "function" then
        local ok, grounded = pcall(isVehicleOnGround, vehicle)
        if ok and not grounded then
            contacts.FL, contacts.FR, contacts.RL, contacts.RR = false, false, false, false
        end
    end
    return contacts
end

function A.sampleSurface(vehicle, now)
    local x, y, z = getElementPosition(vehicle)
    if not x or not y or not z or type(processLineOfSight) ~= "function" then
        return G4.Surfaces.resolve(nil, 0)
    end
    local material
    local groundZ = type(getGroundPosition) == "function" and getGroundPosition(x, y, z + 3) or nil
    if groundZ and groundZ > 0 and math.abs(z - groundZ) < 8 then
        local ok, hit, hitX, hitY, hitZ, hitElement, normalX, normalY, normalZ, materialId = pcall(processLineOfSight,
            x, y, z + 1.5, x, y, groundZ - 0.02, true, false, false, true, false, false, false, false, vehicle)
        if ok and hit then material = tonumber(materialId) end
    end
    local rain = 0
    if type(getRainLevel) == "function" then
        local ok, value = pcall(getRainLevel)
        if ok then rain = tonumber(value) or 0 end
    end
    return G4.Surfaces.resolve(material, rain)
end

local function snapshotHandling(vehicle)
    local ok, current = pcall(getVehicleHandling, vehicle)
    if not ok or type(current) ~= "table" then return nil end
    local snapshot = {}
    for _, property in ipairs(handlingProperties) do
        if current[property] ~= nil then snapshot[property] = G4.copyTable(current[property]) end
    end
    return snapshot
end

local function mixNumber(current, target, blend)
    if not G4.isFinite(current) or not G4.isFinite(target) then return target end
    return current + (target - current) * blend
end

function A.applyNativeBase(vehicle, spec, profileName)
    if not isElement(vehicle) or not spec then return false end
    local snapshot = A.handlingSnapshots[vehicle]
    if not snapshot then
        snapshot = snapshotHandling(vehicle)
        if not snapshot then return false end
        A.handlingSnapshots[vehicle] = snapshot
    end
    local current = getVehicleHandling(vehicle)
    if type(current) ~= "table" then return false end
    local profile = G4.Config.profiles[profileName or G4.State.profile] or G4.Config.profiles.gta4
    local hcfg = G4.Config.handling
    local speedCoefficient = G4.Calibration and G4.Calibration.getCoefficient and G4.Calibration.getCoefficient(spec.model, "speed") or 1
    local blendMass = M.clamp(hcfg.massBlend or 0.7, 0, 1)
    local blendOther = M.clamp(hcfg.otherNumericBlend or 0.45, 0, 1)
    local drive = spec.drivetrain
    local values = {
        mass = mixNumber(current.mass, spec.mass, blendMass),
        turnMass = mixNumber(current.turnMass, spec.mass * (spec.dimensions.wheelbase ^ 2 + spec.dimensions.trackWidth ^ 2) / 12, blendMass),
        dragCoeff = mixNumber(current.dragCoeff, spec.drag, blendOther),
        centerOfMass = {
            mixNumber(current.centerOfMass and current.centerOfMass[1] or 0, spec.centerOfMass[1] or spec.centerOfMass.x or 0, blendOther),
            mixNumber(current.centerOfMass and current.centerOfMass[2] or 0, spec.centerOfMass[2] or spec.centerOfMass.y or 0, blendOther),
            mixNumber(current.centerOfMass and current.centerOfMass[3] or 0, spec.centerOfMass[3] or spec.centerOfMass.z or 0, blendOther)
        },
        tractionMultiplier = mixNumber(current.tractionMultiplier, (spec.traction.max or 1) * hcfg.nativeGripScale, blendOther),
        tractionLoss = mixNumber(current.tractionLoss, (spec.traction.min or 0.5) * hcfg.nativeGripScale, blendOther),
        tractionBias = spec.traction.bias,
        numberOfGears = M.clamp(math.floor(drive.gears or 5), 1, 5),
        maxVelocity = mixNumber(current.maxVelocity, drive.maxSpeed * speedCoefficient * 3.6, blendOther),
        engineAcceleration = mixNumber(current.engineAcceleration, M.clamp(drive.driveForce / math.max(1, spec.mass) * 4.1 * hcfg.nativeEngineScale, 2, 38), blendOther),
        engineInertia = mixNumber(current.engineInertia, M.clamp(2 + (spec.engine.inertia or 0.25) * 12, 2, 15), blendOther),
        driveType = string.lower(drive.type or "rwd"),
        brakeDeceleration = mixNumber(current.brakeDeceleration, M.clamp(spec.brakes.force / math.max(1, spec.mass) * hcfg.nativeBrakeScale, 3, 22), blendOther),
        brakeBias = spec.brakes.bias,
        steeringLock = mixNumber(current.steeringLock, spec.steering.lock, blendOther),
        suspensionForceLevel = mixNumber(current.suspensionForceLevel, M.clamp(spec.suspension.force / math.max(1, spec.mass * 9.81), 0.48, 2.1), blendOther),
        suspensionDamping = mixNumber(current.suspensionDamping, M.clamp(spec.suspension.compression / math.max(1, spec.mass * 20), 0.05, 0.48), blendOther),
        suspensionHighSpeedDamping = mixNumber(current.suspensionHighSpeedDamping, 0.12, blendOther),
        suspensionUpperLimit = mixNumber(current.suspensionUpperLimit, spec.suspension.upper, blendOther),
        suspensionLowerLimit = mixNumber(current.suspensionLowerLimit, spec.suspension.lower, blendOther),
        suspensionFrontRearBias = spec.suspension.bias,
        suspensionAntiDiveMultiplier = mixNumber(current.suspensionAntiDiveMultiplier, 0.18, blendOther)
    }
    for property, value in pairs(values) do
        if snapshot[property] ~= nil then
            pcall(setVehicleHandling, vehicle, property, value)
        end
    end
    if type(G4.log) == "function" then G4.log(string.format("Applied estimated base for %s (%d), profile %s.", spec.name, spec.model, profile.label)) end
    return true
end

function A.restoreNative(vehicle)
    if not isElement(vehicle) then return false end
    local snapshot = A.handlingSnapshots[vehicle]
    if not snapshot then return true end
    for property, value in pairs(snapshot) do
        pcall(setVehicleHandling, vehicle, property, G4.copyTable(value))
    end
    A.handlingSnapshots[vehicle] = nil
    return true
end

function A.setVelocityMps(vehicle, velocity)
    if not isElement(vehicle) or not velocity then return false end
    if not (G4.isFinite(velocity.x) and G4.isFinite(velocity.y) and G4.isFinite(velocity.z)) then return false end
    return setElementVelocity(vehicle, velocity.x / VELOCITY_TICKS_PER_SECOND,
        velocity.y / VELOCITY_TICKS_PER_SECOND, velocity.z / VELOCITY_TICKS_PER_SECOND)
end

function A.setAngularVelocityRad(vehicle, angular)
    if not isElement(vehicle) or type(setElementAngularVelocity) ~= "function" then return false end
    if not (G4.isFinite(angular.x) and G4.isFinite(angular.y) and G4.isFinite(angular.z)) then return false end
    return setElementAngularVelocity(vehicle, angular.x / VELOCITY_TICKS_PER_SECOND,
        angular.y / VELOCITY_TICKS_PER_SECOND, angular.z / VELOCITY_TICKS_PER_SECOND)
end

function A.getNativeSnapshot(vehicle)
    if not isElement(vehicle) then return nil end
    return G4.copyTable(A.handlingSnapshots[vehicle] or {})
end
