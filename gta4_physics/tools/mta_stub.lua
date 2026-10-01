-- Minimal MTA:SA client API stubs for the offline runtime smoke test.
-- Only the functions used by the resource are implemented, and the "native"
-- solver here is a crude stand-in used purely to make the vehicle move.

local log = {}
__G4_log = log

local function record(kind, text)
    log[#log + 1] = kind .. ": " .. tostring(text)
end

clock = 0
function getTickCount() return clock end

root = { __element = true, __type = "root" }
resourceRoot = { __element = true, __type = "resource" }

local player = {
    __element = true, __type = "player",
    position = { x = 1, y = 1, z = 5 }, rotation = { 0, 0, 0 },
    velocity = { x = 0, y = 0, z = 0 }, angular = { x = 0, y = 0, z = 0 }
}
localPlayer = player

local originalHandling = {
    mass = 1400, turnMass = 1800, dragCoeff = 1.5, centerOfMass = { 0, 0.05, -0.1 },
    percentSubmerged = 85, tractionMultiplier = 1.1, tractionLoss = 1.0, tractionBias = 0.5,
    numberOfGears = 5, maxVelocity = 180, engineAcceleration = 10, engineInertia = 5,
    driveType = "rwd", engineType = "petrol", brakeDeceleration = 11, brakeBias = 0.6,
    ABS = false, steeringLock = 35, suspensionForceLevel = 1.7, suspensionDamping = 0.12,
    suspensionHighSpeedDamping = 0, suspensionUpperLimit = 0.16, suspensionLowerLimit = -0.16,
    suspensionFrontRearBias = 0.5, suspensionAntiDiveMultiplier = 0.17, seatOffsetDistance = 0,
    collisionDamageMultiplier = 1, modelFlags = 0, handlingFlags = 0, headLight = "small",
    tailLight = "small", animGroup = 0
}
local function copyTable(source)
    local result = {}
    for key, value in pairs(source) do
        result[key] = type(value) == "table" and copyTable(value) or value
    end
    return result
end

local vehicle = {
    __element = true, __type = "vehicle", model = 560,
    velocity = { x = 0, y = 0, z = 0 }, position = { x = 0, y = 0, z = 5 },
    rotation = { 0, 0, 0 }, angular = { x = 0, y = 0, z = 0 },
    handling = copyTable(originalHandling), wheelContacts = { true, true, true, true }
}
__G4_test_vehicle = vehicle
__G4_original_handling = originalHandling

-- Test inputs (overwritten by the smoke test).
__G4_input = { throttle = 0, brake = 0, steer = 0, handbrake = false, reverse = false }

function isElement(element) return type(element) == "table" and element.__element == true end
function getElementType(element)
    if type(element) == "table" then return element.__type end
    return false
end
function getElementModel(element) return element and element.model or 0 end
function getElementPosition(element) return element.position.x, element.position.y, element.position.z end
function setElementPosition(element, x, y, z) element.position = { x = x, y = y, z = z } return true end
function getElementRotation(element, order)
    return element.rotation[1], element.rotation[2], element.rotation[3]
end
function getElementVelocity(element)
    return element.velocity.x / 50, element.velocity.y / 50, element.velocity.z / 50
end
function setElementVelocity(element, x, y, z)
    if type(x) ~= "number" or type(y) ~= "number" or type(z) ~= "number" then
        error("setElementVelocity received non-numbers")
    end
    element.velocity = { x = x * 50, y = y * 50, z = z * 50 }
    return true
end
function getElementAngularVelocity(element) return element.angular.x / 50, element.angular.y / 50, element.angular.z / 50 end
function setElementAngularVelocity(element, x, y, z) element.angular = { x = x * 50, y = y * 50, z = z * 50 } return true end
function getElementMatrix(element, legacy)
    local yaw = math.rad(element.rotation[3])
    local right = { math.cos(yaw), math.sin(yaw), 0 }
    local forward = { -math.sin(yaw), math.cos(yaw), 0 }
    local up = { 0, 0, 1 }
    return { right, forward, up, { element.position.x, element.position.y, element.position.z } }
end
function getElementDimension() return 0 end
function getElementInterior() return 0 end
function getElementsByType(elementType) if elementType == "vehicle" then return { vehicle } end if elementType == "player" then return { player } end return {} end
function isElementSyncer() return true end
function getVehicleController() return player end
function getPedOccupiedVehicle() return vehicle end
function getPedOccupiedVehicleSeat() return 0 end
function getVehicleType() return "Automobile" end
function isVehicleOnGround() return true end
function isVehicleWheelOnGround(element, wheel)
    local index = type(wheel) == "number" and (wheel + 1) or 1
    return element.wheelContacts[index] == true
end
function getVehicleHandling(element) return element.handling end
function setVehicleHandling(element, property, value)
    if type(property) ~= "string" then error("setVehicleHandling requires a property string") end
    element.handling[property] = value
    return true
end
function getVehicleWheelFrictionState() return 0 end
function getPedAnalogControlState(element, control)
    if control == "accelerate" then return __G4_input.throttle end
    if control == "brake_reverse" then return __G4_input.brake end
    if control == "vehicle_left" then return __G4_input.steer < 0 and -__G4_input.steer or 0 end
    if control == "vehicle_right" then return __G4_input.steer > 0 and __G4_input.steer or 0 end
    return 0
end
function getPedControlState(element, control)
    if control == "handbrake" then return __G4_input.handbrake == true end
    if control == "brake_reverse" then return __G4_input.reverse == true end
    return false
end
function getGroundPosition(x, y, z) return 0 end
function processLineOfSight()
    return true, 0, 0, -0.01, nil, 0, 0, 1, 1, 1
end
function engineGetSurfaceProperties(surfaceID, property)
    if property == "adhesiongroup" then return "road" end
    if property == "tyregrip" or property == "wetgrip" then return 128 end
    if property == "wheeleffect" then return "disabled" end
    return false
end
function getRainLevel() return 0 end
function outputDebugString(message) record("debug", message) end
function outputChatBox(message) record("chat", message) end
function triggerServerEvent(name) record("serverEvent", name) end
function triggerClientEvent() return true end
function dxDrawText() end
function dxDrawRectangle() end
function dxDrawLine3D() end
function getScreenFromWorldPosition() return nil, nil end
function tocolor(r, g, b, a) return 0 end
function toJSON(value) return "{}" end
function fromJSON(value) return {} end
function fileCreate(path) return { path = path } end
function fileWrite(handle, data) handle.data = (handle.data or "") .. data return true end
function fileClose() return true end
function fileExists() return false end
function fileOpen() return nil end
function fileRead() return nil end
function fileGetSize() return 0 end

-- Crude stand-in for the native MTA solver: keep the car on the ground and move
-- it forward so the emulator sees speed, slip and load changes.
function __G4_nativeTick(dt)
    local yaw = math.rad(vehicle.rotation[3])
    local forward = { x = -math.sin(yaw), y = math.cos(yaw) }
    local handling = vehicle.handling
    local throttle = __G4_input.throttle or 0
    local speed = math.sqrt(vehicle.velocity.x ^ 2 + vehicle.velocity.y ^ 2)
    local accel = (handling.engineAcceleration or 8) * 0.55 * throttle
    local maxSpeed = (handling.maxVelocity or 180) / 3.6
    if speed < maxSpeed then
        vehicle.velocity.x = vehicle.velocity.x + forward.x * accel * dt
        vehicle.velocity.y = vehicle.velocity.y + forward.y * accel * dt
    end
    if __G4_input.brake and __G4_input.brake > 0 and speed > 0.5 then
        local decel = (handling.brakeDeceleration or 8) * __G4_input.brake * dt
        local scale = math.max(0, speed - decel) / speed
        vehicle.velocity.x, vehicle.velocity.y = vehicle.velocity.x * scale, vehicle.velocity.y * scale
    end
    -- Integrate the angular velocity the emulator writes, using the documented
    -- "ZYX" basis so body roll/pitch/yaw can be measured by the smoke test.
    local rx, ry, rz = math.rad(vehicle.rotation[1]), math.rad(vehicle.rotation[2]), math.rad(vehicle.rotation[3])
    local right = {
        math.cos(rz) * math.cos(ry) - math.sin(rz) * math.sin(rx) * math.sin(ry),
        math.cos(ry) * math.sin(rz) + math.cos(rz) * math.sin(rx) * math.sin(ry),
        -math.cos(rx) * math.sin(ry)
    }
    local forward = { -math.cos(rx) * math.sin(rz), math.cos(rz) * math.cos(rx), math.sin(rx) }
    local up = {
        math.cos(rz) * math.sin(ry) + math.cos(ry) * math.sin(rz) * math.sin(rx),
        math.sin(rz) * math.sin(ry) - math.cos(rz) * math.cos(ry) * math.sin(rx),
        math.cos(rx) * math.cos(ry)
    }
    local function dot(a, b) return a[1] * b[1] + a[2] * b[2] + a[3] * b[3] end
    local localRight = dot(right, { vehicle.angular.x, vehicle.angular.y, vehicle.angular.z })
    local localForward = dot(forward, { vehicle.angular.x, vehicle.angular.y, vehicle.angular.z })
    local localUp = dot(up, { vehicle.angular.x, vehicle.angular.y, vehicle.angular.z })
    vehicle.rotation[1] = vehicle.rotation[1] + math.deg(localForward) * dt
    vehicle.rotation[2] = vehicle.rotation[2] + math.deg(localRight) * dt
    vehicle.rotation[3] = vehicle.rotation[3] + math.deg(localUp) * dt

    local drag = (handling.dragCoeff or 1.5) * 0.02
    vehicle.velocity.x = vehicle.velocity.x - vehicle.velocity.x * drag * dt
    vehicle.velocity.y = vehicle.velocity.y - vehicle.velocity.y * drag * dt
    vehicle.velocity.z = 0
    vehicle.position.x = vehicle.position.x + vehicle.velocity.x * dt
    vehicle.position.y = vehicle.position.y + vehicle.velocity.y * dt
    vehicle.position.z = 5
    local steer = __G4_input.steer or 0
    if math.abs(steer) > 0 then
        local factor = math.min(1, speed / 12) * 0.6
        local yawDelta = math.rad(steer * factor * dt * 60)
        vehicle.rotation[3] = vehicle.rotation[3] + steer * factor * dt * 60
        -- A real tyre would mostly carry its velocity into the new heading; rotate
        -- the velocity vector by most of the yaw change so the stand-in solver is
        -- not permanently sideways.
        local cosDelta, sinDelta = math.cos(yawDelta), math.sin(yawDelta)
        local vx, vy = vehicle.velocity.x * 0.99, vehicle.velocity.y * 0.99
        vehicle.velocity.x = vx * cosDelta + vy * sinDelta
        vehicle.velocity.y = -vx * sinDelta + vy * cosDelta
    end
end

function __G4_frame(timeSlice)
    clock = clock + timeSlice
    __G4_nativeTick(timeSlice / 1000)
    triggerEvent("onClientPreRender", root, timeSlice)
end
