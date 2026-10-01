GTA4Physics = GTA4Physics or {}
local G4 = GTA4Physics
G4.Performance = {
    lastLodTick = 0, lastRemoteTick = 0,
    lodByVehicle = setmetatable({}, { __mode = "k" }),
    remoteByVehicle = setmetatable({}, { __mode = "k" }),
    counts = { FULL = 0, NEAR = 0, FAR = 0, INACTIVE = 0 },
    lastStepMs = 0, averageStepMs = 0, updates = 0, remoteUpdates = 0
}
local P = G4.Performance

function P.updateLods(force)
    local now = getTickCount()
    if not force and now - P.lastLodTick < G4.Config.lodUpdateMs then return end
    P.lastLodTick = now
    P.counts = { FULL = 0, NEAR = 0, FAR = 0, INACTIVE = 0 }
    if not isElement(localPlayer) then return end
    local px, py, pz = getElementPosition(localPlayer)
    local dimension, interior = getElementDimension(localPlayer), getElementInterior(localPlayer)
    local vehicles = getElementsByType("vehicle", root, true)
    for _, vehicle in ipairs(vehicles) do
        local lod = "INACTIVE"
        if isElement(vehicle) and getElementDimension(vehicle) == dimension and getElementInterior(vehicle) == interior then
            local x, y, z = getElementPosition(vehicle)
            local dx, dy, dz = x - px, y - py, z - pz
            local distance = math.sqrt(dx * dx + dy * dy + dz * dz)
            if G4.State.enabled and G4.VehicleManager and vehicle == G4.VehicleManager.activeVehicle and getVehicleController(vehicle) == localPlayer then
                lod = "FULL"
            elseif distance <= G4.Config.nearRange then
                lod = "NEAR"
            elseif distance <= G4.Config.farRange then
                lod = "FAR"
            end
        end
        P.lodByVehicle[vehicle] = lod
        P.counts[lod] = (P.counts[lod] or 0) + 1
    end
end

function P.getLod(vehicle)
    return P.lodByVehicle[vehicle] or "INACTIVE"
end

local function blendTable(current, target, alpha)
    current = current or {}
    for _, key in ipairs({ "speedMps", "rpm", "throttle", "brake", "steering", "yawRate", "pitch", "roll", "longitudinalG", "lateralG" }) do
        local value = target[key]
        if G4.isFinite(value) then
            current[key] = G4.isFinite(current[key]) and (current[key] + (value - current[key]) * alpha) or value
        end
    end
    current.gear, current.profile = target.gear, target.profile
    current.serverVelocity = target.serverVelocity and G4.copyTable(target.serverVelocity) or current.serverVelocity
    current.position = target.position and G4.copyTable(target.position) or current.position
    current.receivedTick, current.sourceTick = getTickCount(), target.receivedTick
    current.wheels = current.wheels or {}
    for _, name in ipairs({ "FL", "FR", "RL", "RR" }) do
        local targetWheel = target.wheels and target.wheels[name]
        if targetWheel then
            local wheel = current.wheels[name] or {}
            for _, key in ipairs({ "longitudinalSlip", "lateralSlip", "combinedSlip", "load" }) do
                local value = targetWheel[key]
                if G4.isFinite(value) then
                    wheel[key] = G4.isFinite(wheel[key]) and (wheel[key] + (value - wheel[key]) * alpha) or value
                end
            end
            current.wheels[name] = wheel
        end
    end
    return current
end

-- Remote vehicles are not simulated on this client: MTA's network owner runs the solver.
-- NEAR/FAR LODs smoothly filter validated telemetry at different rates and never write position.
function P.processRemoteLods(force)
    local now = getTickCount()
    if not force and now - P.lastRemoteTick < 100 then return end
    local dt = math.max(0.001, (now - (P.lastRemoteTick > 0 and P.lastRemoteTick or now - 100)) / 1000)
    P.lastRemoteTick = now
    P.remoteUpdates = P.remoteUpdates + 1
    for vehicle, lod in pairs(P.lodByVehicle) do
        if lod == "NEAR" or lod == "FAR" then
            local packet = G4.Sync and G4.Sync.getRemoteState and G4.Sync.getRemoteState(vehicle)
            if packet then
                local response = lod == "NEAR" and 8.0 or 2.0
                local alpha = 1 - math.exp(-response * dt)
                P.remoteByVehicle[vehicle] = blendTable(P.remoteByVehicle[vehicle], packet, alpha)
                P.remoteByVehicle[vehicle].lod = lod
            end
        else
            P.remoteByVehicle[vehicle] = nil
        end
    end
end

function P.getRemoteTelemetry(vehicle)
    local data = P.remoteByVehicle[vehicle]
    if not data then return nil end
    if getTickCount() - (data.receivedTick or 0) > G4.Config.network.stateExpiryMs then
        P.remoteByVehicle[vehicle] = nil
        return nil
    end
    return G4.copyTable(data)
end

function P.recordStep(milliseconds)
    milliseconds = math.max(0, tonumber(milliseconds) or 0)
    P.lastStepMs = milliseconds
    P.updates = P.updates + 1
    P.averageStepMs = P.averageStepMs + (milliseconds - P.averageStepMs) * math.min(0.08, 1 / math.max(1, P.updates))
end

function P.getStats()
    return {
        lods = G4.copyTable(P.counts), averageStepMs = P.averageStepMs,
        lastStepMs = P.lastStepMs, physicsUpdates = P.updates, remoteUpdates = P.remoteUpdates,
        activeLod = G4.VehicleManager and G4.VehicleManager.activeVehicle and P.getLod(G4.VehicleManager.activeVehicle) or "INACTIVE"
    }
end
