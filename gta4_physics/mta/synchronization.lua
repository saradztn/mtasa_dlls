GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
G4.Sync = {
    sequence = 0,
    lastSendTick = 0,
    clientStarted = false,
    serverStarted = false,
    remoteStates = setmetatable({}, { __mode = "k" }),
    authority = setmetatable({}, { __mode = "k" }),
    serverRate = setmetatable({}, { __mode = "k" }),
    serverSequence = setmetatable({}, { __mode = "k" })
}
local S = G4.Sync

local function finite(value)
    return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge
end
local function clamp(value, low, high)
    if not finite(value) then return low end
    return math.max(low, math.min(high, value))
end

function S.sanitizeClientPacket(packet)
    if type(packet) ~= "table" then return nil end
    local clean = {
        sequence = math.floor(clamp(packet.sequence, 0, 2147483647)),
        speedMps = clamp(packet.speedMps, 0, G4.Config.network.maxReportedSpeed),
        rpm = clamp(packet.rpm, 0, G4.Config.network.maxReportedRPM),
        gear = math.floor(clamp(packet.gear, -1, 10)),
        throttle = clamp(packet.throttle, 0, 1),
        brake = clamp(packet.brake, 0, 1),
        steering = clamp(packet.steering, -1, 1),
        yawRate = clamp(packet.yawRate, -8, 8),
        pitch = clamp(packet.pitch, -90, 90),
        roll = clamp(packet.roll, -90, 90),
        longitudinalG = clamp(packet.longitudinalG, -8, 8),
        lateralG = clamp(packet.lateralG, -8, 8),
        profile = ({ gta4 = true, comfort = true, sport = true, drift = true })[tostring(packet.profile or "")] and tostring(packet.profile) or "gta4",
        wheels = {}
    }
    for _, name in ipairs({ "FL", "FR", "RL", "RR" }) do
        local wheel = type(packet.wheels) == "table" and packet.wheels[name] or nil
        clean.wheels[name] = {
            longitudinalSlip = clamp(wheel and wheel.longitudinalSlip, -G4.Config.network.maxReportedSlip, G4.Config.network.maxReportedSlip),
            lateralSlip = clamp(wheel and wheel.lateralSlip, -G4.Config.network.maxReportedSlip, G4.Config.network.maxReportedSlip),
            combinedSlip = clamp(wheel and wheel.combinedSlip, 0, G4.Config.network.maxReportedSlip),
            load = clamp(wheel and wheel.load, 0, 120000)
        }
    end
    return clean
end

function S.clientTick(vehicle, state)
    if not G4.Config.network.enabled or not isElement(vehicle) then return end
    local now = getTickCount()
    if now - S.lastSendTick < G4.Config.syncIntervalMs then return end
    S.lastSendTick = now
    S.sequence = (S.sequence + 1) % 2147483647
    local packet = S.sanitizeClientPacket({
        sequence = S.sequence, speedMps = state.speedMps, rpm = state.rpm, gear = state.gear,
        throttle = state.throttle, brake = state.brake, steering = state.steering,
        yawRate = state.yawRate, pitch = state.pitch, roll = state.roll,
        longitudinalG = state.longitudinalG, lateralG = state.lateralG, profile = state.profile,
        wheels = {
            FL = { longitudinalSlip = state.tireWheels.FL.longitudinalSlip, lateralSlip = state.tireWheels.FL.lateralSlip, combinedSlip = state.tireWheels.FL.combinedSlip, load = state.tireWheels.FL.wheelLoad },
            FR = { longitudinalSlip = state.tireWheels.FR.longitudinalSlip, lateralSlip = state.tireWheels.FR.lateralSlip, combinedSlip = state.tireWheels.FR.combinedSlip, load = state.tireWheels.FR.wheelLoad },
            RL = { longitudinalSlip = state.tireWheels.RL.longitudinalSlip, lateralSlip = state.tireWheels.RL.lateralSlip, combinedSlip = state.tireWheels.RL.combinedSlip, load = state.tireWheels.RL.wheelLoad },
            RR = { longitudinalSlip = state.tireWheels.RR.longitudinalSlip, lateralSlip = state.tireWheels.RR.lateralSlip, combinedSlip = state.tireWheels.RR.combinedSlip, load = state.tireWheels.RR.wheelLoad }
        }
    })
    triggerServerEvent(G4.Config.eventNames.state, resourceRoot, vehicle, packet)
end

local function acceptClientState(vehicle, packet, isAck)
    if not isElement(vehicle) or getElementType(vehicle) ~= "vehicle" then return end
    local clean = S.sanitizeClientPacket(packet)
    if not clean then return end
    clean.receivedTick = getTickCount()
    if isAck and G4.VehicleManager and vehicle == G4.VehicleManager.activeVehicle then
        clean.serverVelocity = packet.serverVelocity
        clean.position = packet.position
        if type(clean.serverVelocity) == "table" and finite(clean.serverVelocity.x) and finite(clean.serverVelocity.y) and finite(clean.serverVelocity.z) then
            S.authority[vehicle] = clean
        end
    else
        if type(packet.serverVelocity) == "table" and finite(packet.serverVelocity.x) and finite(packet.serverVelocity.y) and finite(packet.serverVelocity.z) then
            clean.serverVelocity = { x = packet.serverVelocity.x, y = packet.serverVelocity.y, z = packet.serverVelocity.z }
        end
        if type(packet.position) == "table" and finite(packet.position.x) and finite(packet.position.y) and finite(packet.position.z) then
            clean.position = { x = packet.position.x, y = packet.position.y, z = packet.position.z }
        end
        S.remoteStates[vehicle] = clean
    end
end

function S.startClient()
    if S.clientStarted or not localPlayer then return false end
    S.clientStarted = true
    addEvent(G4.Config.eventNames.state, true)
    addEvent(G4.Config.eventNames.ack, true)
    S.clientStateHandler = function(vehicle, packet) acceptClientState(vehicle, packet, false) end
    S.clientAckHandler = function(vehicle, packet) acceptClientState(vehicle, packet, true) end
    addEventHandler(G4.Config.eventNames.state, resourceRoot, S.clientStateHandler)
    addEventHandler(G4.Config.eventNames.ack, resourceRoot, S.clientAckHandler)
    return true
end

function S.stopClient()
    if not S.clientStarted then return end
    if S.clientStateHandler then removeEventHandler(G4.Config.eventNames.state, resourceRoot, S.clientStateHandler) end
    if S.clientAckHandler then removeEventHandler(G4.Config.eventNames.ack, resourceRoot, S.clientAckHandler) end
    S.clientStateHandler, S.clientAckHandler = nil, nil
    S.clientStarted = false
    S.remoteStates = setmetatable({}, { __mode = "k" })
    S.authority = setmetatable({}, { __mode = "k" })
end

function S.getRemoteState(vehicle)
    local data = S.remoteStates[vehicle]
    if not data then return nil end
    if getTickCount() - (data.receivedTick or 0) > G4.Config.network.stateExpiryMs then
        S.remoteStates[vehicle] = nil
        return nil
    end
    return data
end

function S.getVelocityCorrection(vehicle, currentVelocity, dt)
    local target = S.authority[vehicle]
    if not target or not target.serverVelocity then return { x = 0, y = 0, z = 0 } end
    if getTickCount() - (target.receivedTick or 0) > 700 then return { x = 0, y = 0, z = 0 } end
    local blend = 1 - math.exp(-G4.Config.velocityCorrectionRate * math.max(0, dt or 0))
    local difference = {
        x = (target.serverVelocity.x - currentVelocity.x) * blend,
        y = (target.serverVelocity.y - currentVelocity.y) * blend,
        z = (target.serverVelocity.z - currentVelocity.z) * blend
    }
    local length = math.sqrt(difference.x ^ 2 + difference.y ^ 2 + difference.z ^ 2)
    local maximum = G4.Config.network.maxCorrectionMps * math.max(0, dt or 0)
    if length > maximum and length > 0 then
        local scale = maximum / length
        difference.x, difference.y, difference.z = difference.x * scale, difference.y * scale, difference.z * scale
    end
    return difference
end

function S.startServer()
    if S.serverStarted then return false end
    S.serverStarted = true
    addEvent(G4.Config.eventNames.state, true)
    S.serverStateHandler = function(vehicle, packet)
        local player = client
        if source ~= resourceRoot or not isElement(player) or getElementType(player) ~= "player" then return end
        if not isElement(vehicle) or getElementType(vehicle) ~= "vehicle" then return end
        if getPedOccupiedVehicle(player) ~= vehicle or getVehicleController(vehicle) ~= player then return end
        local ok, seat = pcall(getPedOccupiedVehicleSeat, player)
        if not ok or seat ~= 0 then return end

        local now = getTickCount()
        if now - (S.serverRate[player] or 0) < G4.Config.syncRateLimitMs then return end
        local clean = S.sanitizeClientPacket(packet)
        if not clean then return end
        local previousSequence = S.serverSequence[player]
        if previousSequence ~= nil then
            local sequenceDelta = (clean.sequence - previousSequence) % 2147483647
            if sequenceDelta == 0 or sequenceDelta >= 1073741824 then return end
        end
        S.serverRate[player], S.serverSequence[player] = now, clean.sequence

        local vx, vy, vz = getElementVelocity(vehicle)
        local px, py, pz = getElementPosition(vehicle)
        if not (finite(vx) and finite(vy) and finite(vz) and finite(px) and finite(py) and finite(pz)) then return end
        local serverState = {
            sequence = clean.sequence, speedMps = math.min(G4.Config.network.maxReportedSpeed, math.sqrt(vx * vx + vy * vy + vz * vz) * 50),
            rpm = clean.rpm, gear = clean.gear, throttle = clean.throttle, brake = clean.brake, steering = clean.steering,
            yawRate = clean.yawRate, pitch = clean.pitch, roll = clean.roll,
            longitudinalG = clean.longitudinalG, lateralG = clean.lateralG, profile = clean.profile,
            wheels = clean.wheels, serverVelocity = { x = vx * 50, y = vy * 50, z = vz * 50 },
            position = { x = px, y = py, z = pz }, receivedTick = now
        }
        triggerClientEvent(player, G4.Config.eventNames.ack, resourceRoot, vehicle, serverState)

        local dimension, interior = getElementDimension(vehicle), getElementInterior(vehicle)
        local rangeSquared = G4.Config.syncRange * G4.Config.syncRange
        for _, recipient in ipairs(getElementsByType("player")) do
            if recipient ~= player and getElementDimension(recipient) == dimension and getElementInterior(recipient) == interior then
                local rx, ry, rz = getElementPosition(recipient)
                local dx, dy, dz = rx - px, ry - py, rz - pz
                if dx * dx + dy * dy + dz * dz <= rangeSquared then
                    triggerClientEvent(recipient, G4.Config.eventNames.state, resourceRoot, vehicle, serverState)
                end
            end
        end
    end
    addEventHandler(G4.Config.eventNames.state, resourceRoot, S.serverStateHandler)
    S.serverQuitHandler = function() S.serverRate[source], S.serverSequence[source] = nil, nil end
    addEventHandler("onPlayerQuit", root, S.serverQuitHandler)
    return true
end

function S.stopServer()
    if not S.serverStarted then return end
    if S.serverStateHandler then removeEventHandler(G4.Config.eventNames.state, resourceRoot, S.serverStateHandler) end
    if S.serverQuitHandler then removeEventHandler("onPlayerQuit", root, S.serverQuitHandler) end
    S.serverStateHandler, S.serverQuitHandler = nil, nil
    S.serverStarted = false
    S.serverRate, S.serverSequence = setmetatable({}, { __mode = "k" }), setmetatable({}, { __mode = "k" })
end
