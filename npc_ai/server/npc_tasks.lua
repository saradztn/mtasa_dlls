-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: SERVER TASK AUTHORITY AND EVENT VALIDATION
-- ============================================================================

local allowedReportedStates = {
    IDLE = true,
    WANDER = true,
    WALK_TO_NODE = true,
    FOLLOW_PATH = true,
    AVOID_OBSTACLE = true,
    WAIT = true,
    STUCK = true,
    REPATH = true,
    FLEE = true,
    CHASE = true,
    GO_TO_LOCATION = true,
    RETURN = true,
}

local snapshotRequestedAt = {}

local function rateLimited(record, player, key, interval)
    record.lastClientEventAt = record.lastClientEventAt or {}
    local byPlayer = record.lastClientEventAt[player] or {}
    record.lastClientEventAt[player] = byPlayer
    local now = NPCUtil.now()
    local previous = byPlayer[key] or 0
    if now - previous < interval then
        return true
    end
    byPlayer[key] = now
    return false
end

local function validClientEvent(record, requireOwner)
    if source ~= resourceRoot or not client or not record or not isElement(record.ped) then
        return false
    end
    if requireOwner then
        if record.owner ~= client or getElementSyncer(record.ped) ~= client then
            NPCAILog.rateLimited("ownership:" .. tostring(record.id), "WARNING", "SECURITY", "Rejected non-owner NPC event for " .. record.id)
            return false
        end
    end
    return true
end

local function validNodeId(value)
    return type(value) == "number" and value % 1 == 0 and value >= 0 and value < 64 * 65536
end

addEvent(NPCProtocol.requestTasks, true)
addEventHandler(NPCProtocol.requestTasks, resourceRoot, function()
    if source ~= resourceRoot or not client then
        return
    end

    local now = NPCUtil.now()
    if now - (snapshotRequestedAt[client] or 0) < Config.networking.clientEventMinIntervalMs then
        return
    end
    snapshotRequestedAt[client] = now

    local snapshot = {}
    for _, record in pairs(NPCManager.recordsByPed) do
        if #snapshot >= Config.networking.snapshotMaxNPCs then
            break
        end
        if isElement(record.ped) then
            snapshot[#snapshot + 1] = {
                ped = record.ped,
                task = NPCManager.serialiseTask(record),
            }
        end
    end
    triggerClientEvent(client, NPCProtocol.taskSnapshot, resourceRoot, snapshot)
end)

addEvent(NPCProtocol.requestTask, true)
addEventHandler(NPCProtocol.requestTask, resourceRoot, function(ped)
    local record = NPCManager.getRecord(ped)
    if not validClientEvent(record, false) then
        return
    end
    if rateLimited(record, client, "requestTask", Config.networking.clientEventMinIntervalMs) then
        return
    end
    NPCManager.publishTask(record, client)
end)

addEvent(NPCProtocol.chooseWanderDestination, true)
addEventHandler(NPCProtocol.chooseWanderDestination, resourceRoot, function(ped, x, y, z)
    local record = NPCManager.getRecord(ped)
    if not validClientEvent(record, true) then
        return
    end
    if rateLimited(record, client, "wander", Config.networking.clientEventMinIntervalMs) then
        return
    end
    if record.task.kind ~= "wander" or record.task.paused then
        return
    end

    x, y, z = tonumber(x), tonumber(y), tonumber(z)
    if not NPCUtil.isFinite(x) or not NPCUtil.isFinite(y) or not NPCUtil.isFinite(z)
        or math.abs(x) > Config.security.worldCoordinateLimit
        or math.abs(y) > Config.security.worldCoordinateLimit
        or math.abs(z) > Config.security.worldCoordinateLimit then
        NPCAILog.warning("SECURITY", "Rejected invalid wander coordinates for NPC " .. record.id)
        return
    end

    local pedX, pedY, pedZ = getElementPosition(record.ped)
    local radius = NPCUtil.clamp(tonumber(record.task.radius) or Config.wandering.defaultRadius, Config.wandering.minRadius, Config.wandering.maxRadius)
    local distance = NPCUtil.distance3D(pedX, pedY, pedZ, x, y, z)
    if distance > math.min(radius + 20, Config.security.maxWanderDestinationDistance) then
        NPCAILog.warning("SECURITY", "Rejected out-of-range wander destination for NPC " .. record.id)
        return
    end

    NPCManager.setTask(record, {
        kind = "wander",
        radius = radius,
        destination = { x = x, y = y, z = z },
        speed = record.speed,
        avoidance = record.avoidanceEnabled,
        paused = false,
    })
end)

addEvent(NPCProtocol.report, true)
addEventHandler(NPCProtocol.report, resourceRoot, function(ped, report)
    local record = NPCManager.getRecord(ped)
    if not validClientEvent(record, true) or type(report) ~= "table" then
        return
    end
    if rateLimited(record, client, "report", math.max(250, Config.networking.reportIntervalMs - 100)) then
        return
    end

    if allowedReportedStates[report.state] then
        record.reportedState = report.state
        record.state = report.state
        setElementData(record.ped, "npc_ai:state", report.state)
    end
    if validNodeId(report.currentNode) then
        record.currentNode = report.currentNode
    end
    if validNodeId(report.goalNode) then
        record.goalNode = report.goalNode
    end
    if NPCUtil.isFinite(report.speed) then
        record.reportedSpeed = NPCUtil.clamp(report.speed, 0, Config.movement.runSpeed)
    end

    local reportedPath = report.path
    if type(reportedPath) == "table" then
        local cleaned = {}
        local maximum = math.min(#reportedPath, 256)
        for index = 1, maximum do
            if validNodeId(reportedPath[index]) then
                cleaned[#cleaned + 1] = reportedPath[index]
            else
                cleaned = {}
                break
            end
        end
        record.reportedPath = cleaned
    end
end)

addEventHandler("onPlayerQuit", root, function()
    snapshotRequestedAt[source] = nil
end)
