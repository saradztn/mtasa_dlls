-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: SERVER NPC MANAGER AND PUBLIC API
-- ============================================================================

NPCManager = NPCManager or {
    recordsByPed = {},
    recordsById = {},
    nextId = 1,
    lastNPCByPlayer = {},
}

local function validCoordinate(value)
    return NPCUtil.isFinite(value) and math.abs(value) <= Config.security.worldCoordinateLimit
end

local function resolvePed(value)
    if type(value) == "table" and value.ped then
        value = value.ped
    end
    return value
end

function NPCManager.getRecord(value)
    return NPCManager.recordsByPed[resolvePed(value)]
end

function NPCManager.getRecordById(id)
    return NPCManager.recordsById[tonumber(id)]
end

function NPCManager.count()
    return NPCUtil.tableCount(NPCManager.recordsByPed)
end

function NPCManager.serialiseTask(record)
    local task = NPCUtil.copyTable(record.task)
    -- Elements are valid event values in MTA; only CHASE/FLEE use target and
    -- the server validates it when a task is created.
    return task
end

function NPCManager.publishTask(record, target)
    if not record or not isElement(record.ped) then
        return false
    end
    triggerClientEvent(target or root, NPCProtocol.task, resourceRoot, record.ped, NPCManager.serialiseTask(record))
    return true
end

function NPCManager.setTask(record, task)
    if not record or not isElement(record.ped) or type(task) ~= "table" then
        return false, "invalid NPC task"
    end

    task.revision = (record.task and record.task.revision or 0) + 1
    task.speed = NPCUtil.clamp(tonumber(task.speed) or record.speed or Config.movement.defaultSpeed, 0.2, Config.movement.runSpeed)
    if task.avoidance == nil then
        task.avoidance = record.avoidanceEnabled ~= false
    end

    record.task = task
    record.speed = task.speed
    record.avoidanceEnabled = task.avoidance
    local taskStates = {
        idle = "IDLE",
        wander = "WANDER",
        go = "GO_TO_LOCATION",
        chase = "CHASE",
        flee = "FLEE",
        ["return"] = "RETURN",
    }
    record.state = task.paused and "WAIT" or (taskStates[task.kind] or "IDLE")
    setElementData(record.ped, "npc_ai:state", record.state)
    setElementData(record.ped, "npc_ai:taskRevision", task.revision)
    NPCManager.publishTask(record)
    return true
end

function NPCManager.create(model, x, y, z, options)
    options = options or {}
    model = tonumber(model)
    x, y, z = tonumber(x), tonumber(y), tonumber(z)
    if not model or model % 1 ~= 0 or model < 0 or model > 312 then
        return false, "invalid GTA SA ped model"
    end
    if not validCoordinate(x) or not validCoordinate(y) or not validCoordinate(z) then
        return false, "invalid spawn position"
    end
    if NPCManager.count() >= Config.maxNPCs then
        return false, "maxNPCs limit reached"
    end

    local rotation = tonumber(options.rotation) or 0
    local ped = createPed(model, x, y, z, rotation, true)
    if not ped then
        return false, "createPed failed"
    end

    if options.interior ~= nil then
        setElementInterior(ped, tonumber(options.interior) or 0)
    end
    if options.dimension ~= nil then
        setElementDimension(ped, tonumber(options.dimension) or 0)
    end
    if options.walkingStyle then
        setPedWalkingStyle(ped, tonumber(options.walkingStyle) or 0)
    end

    local id = NPCManager.nextId
    NPCManager.nextId = id + 1
    local record = {
        id = id,
        ped = ped,
        model = model,
        createdAt = NPCUtil.now(),
        home = { x = x, y = y, z = z },
        state = "IDLE",
        speed = NPCUtil.clamp(tonumber(options.speed) or Config.movement.defaultSpeed, 0.2, Config.movement.runSpeed),
        avoidanceEnabled = options.avoidance ~= false,
        task = {
            kind = "idle",
            revision = 0,
            speed = NPCUtil.clamp(tonumber(options.speed) or Config.movement.defaultSpeed, 0.2, Config.movement.runSpeed),
            avoidance = options.avoidance ~= false,
        },
        owner = nil,
        lastClientEventAt = {},
        reportedPath = {},
        reportedState = "IDLE",
    }

    NPCManager.recordsByPed[ped] = record
    NPCManager.recordsById[id] = record
    setElementData(ped, "npc_ai:managed", true)
    setElementData(ped, "npc_ai:id", id)
    setElementData(ped, "npc_ai:state", "IDLE")
    setElementData(ped, "npc_ai:taskRevision", 0)

    NPCAILog.info("NPC", "Created NPC " .. id .. " (model " .. model .. ")")
    return ped
end

function NPCManager.destroy(value)
    local ped = resolvePed(value)
    local record = NPCManager.recordsByPed[ped]
    if not record then
        return false, "unknown NPC"
    end

    NPCManager.recordsByPed[ped] = nil
    NPCManager.recordsById[record.id] = nil
    if isElement(ped) then
        destroyElement(ped)
    end
    NPCAILog.info("NPC", "Destroyed NPC " .. record.id)
    return true
end

function NPCManager.setDestination(value, x, y, z, options)
    local record = NPCManager.getRecord(value)
    x, y, z = tonumber(x), tonumber(y), tonumber(z)
    options = options or {}
    if not record then
        return false, "unknown NPC"
    end
    if not validCoordinate(x) or not validCoordinate(y) or not validCoordinate(z) then
        return false, "invalid destination"
    end

    return NPCManager.setTask(record, {
        kind = "go",
        destination = { x = x, y = y, z = z },
        speed = options.speed or record.speed,
        avoidance = options.avoidance ~= false and record.avoidanceEnabled,
        paused = false,
    })
end

function NPCManager.startWander(value, radius, options)
    local record = NPCManager.getRecord(value)
    options = options or {}
    if not record then
        return false, "unknown NPC"
    end

    radius = NPCUtil.clamp(tonumber(radius) or Config.wandering.defaultRadius, Config.wandering.minRadius, Config.wandering.maxRadius)
    return NPCManager.setTask(record, {
        kind = "wander",
        radius = radius,
        speed = options.speed or record.speed,
        avoidance = options.avoidance ~= false and record.avoidanceEnabled,
        paused = false,
    })
end

function NPCManager.stop(value)
    local record = NPCManager.getRecord(value)
    if not record then
        return false, "unknown NPC"
    end
    return NPCManager.setTask(record, {
        kind = "idle",
        speed = record.speed,
        avoidance = record.avoidanceEnabled,
        paused = false,
    })
end

function NPCManager.pause(value)
    local record = NPCManager.getRecord(value)
    if not record then
        return false, "unknown NPC"
    end
    local task = NPCUtil.copyTable(record.task)
    task.paused = true
    return NPCManager.setTask(record, task)
end

function NPCManager.resume(value)
    local record = NPCManager.getRecord(value)
    if not record then
        return false, "unknown NPC"
    end
    local task = NPCUtil.copyTable(record.task)
    task.paused = false
    return NPCManager.setTask(record, task)
end

function NPCManager.setSpeed(value, speed)
    local record = NPCManager.getRecord(value)
    speed = tonumber(speed)
    if not record or not speed then
        return false, "invalid NPC or speed"
    end
    local task = NPCUtil.copyTable(record.task)
    task.speed = NPCUtil.clamp(speed, 0.2, Config.movement.runSpeed)
    return NPCManager.setTask(record, task)
end

function NPCManager.setAvoidance(value, enabled)
    local record = NPCManager.getRecord(value)
    if not record then
        return false, "unknown NPC"
    end
    local task = NPCUtil.copyTable(record.task)
    task.avoidance = enabled == true
    return NPCManager.setTask(record, task)
end

function NPCManager.setBehavior(value, behavior, options)
    local record = NPCManager.getRecord(value)
    behavior = tostring(behavior or ""):lower()
    options = options or {}
    if not record then
        return false, "unknown NPC"
    end

    if behavior == "wander" then
        return NPCManager.startWander(record.ped, options.radius, options)
    elseif behavior == "idle" or behavior == "stop" then
        return NPCManager.stop(record.ped)
    elseif behavior == "return" then
        return NPCManager.setTask(record, {
            kind = "return",
            home = NPCUtil.copyTable(record.home),
            speed = options.speed or record.speed,
            avoidance = options.avoidance ~= false and record.avoidanceEnabled,
            paused = false,
        })
    elseif behavior == "chase" or behavior == "flee" then
        local target = options.target
        if not isElement(target) then
            return false, "chase/flee requires options.target element"
        end
        return NPCManager.setTask(record, {
            kind = behavior,
            target = target,
            fleeDistance = options.fleeDistance,
            speed = options.speed or record.speed,
            avoidance = options.avoidance ~= false and record.avoidanceEnabled,
            paused = false,
        })
    elseif behavior == "go" and options.x and options.y and options.z then
        return NPCManager.setDestination(record.ped, options.x, options.y, options.z, options)
    end
    return false, "unsupported behavior"
end

function NPCManager.getState(value)
    local record = NPCManager.getRecord(value)
    return record and record.state or false
end

function NPCManager.getCurrentPath(value)
    local record = NPCManager.getRecord(value)
    if not record then
        return false
    end
    return NPCUtil.copyArray(record.reportedPath or {})
end

function NPCManager.getCurrentNode(value)
    local record = NPCManager.getRecord(value)
    return record and record.currentNode or false
end

-- Lua-facing handle API requested by the resource contract. It is useful inside
-- this resource; other resources should call the exported functions below.
local NPCHandle = {}
NPCHandle.__index = NPCHandle

function NPCHandle:setDestination(x, y, z, options)
    return NPCManager.setDestination(self.ped, x, y, z, options)
end
function NPCHandle:startWander(radius, options)
    return NPCManager.startWander(self.ped, radius, options)
end
function NPCHandle:stop()
    return NPCManager.stop(self.ped)
end
function NPCHandle:pause()
    return NPCManager.pause(self.ped)
end
function NPCHandle:resume()
    return NPCManager.resume(self.ped)
end
function NPCHandle:setSpeed(speed)
    return NPCManager.setSpeed(self.ped, speed)
end
function NPCHandle:setBehavior(behavior, options)
    return NPCManager.setBehavior(self.ped, behavior, options)
end
function NPCHandle:setAvoidanceEnabled(enabled)
    return NPCManager.setAvoidance(self.ped, enabled)
end
function NPCHandle:destroy()
    return NPCManager.destroy(self.ped)
end
function NPCHandle:getState()
    return NPCManager.getState(self.ped)
end
function NPCHandle:getCurrentPath()
    return NPCManager.getCurrentPath(self.ped)
end
function NPCHandle:getCurrentNode()
    return NPCManager.getCurrentNode(self.ped)
end
function NPCHandle:getPed()
    return self.ped
end

NPC = NPC or {}
function NPC.wrap(ped)
    if not NPCManager.getRecord(ped) then
        return false
    end
    return setmetatable({ ped = ped }, NPCHandle)
end
function NPC.create(model, x, y, z, options)
    local ped, errorMessage = NPCManager.create(model, x, y, z, options)
    if not ped then
        return false, errorMessage
    end
    return NPC.wrap(ped)
end

-- Exported MTA API -----------------------------------------------------------
function createNPC(model, x, y, z, options)
    return NPCManager.create(model, x, y, z, options)
end
function destroyNPC(ped)
    return NPCManager.destroy(ped)
end
function setNPCDestination(ped, x, y, z, options)
    return NPCManager.setDestination(ped, x, y, z, options)
end
function startNPCWander(ped, radius, options)
    return NPCManager.startWander(ped, radius, options)
end
function stopNPC(ped)
    return NPCManager.stop(ped)
end
function pauseNPC(ped)
    return NPCManager.pause(ped)
end
function resumeNPC(ped)
    return NPCManager.resume(ped)
end
function setNPCSpeed(ped, speed)
    return NPCManager.setSpeed(ped, speed)
end
function setNPCBehavior(ped, behavior, options)
    return NPCManager.setBehavior(ped, behavior, options)
end
function setNPCAvoidanceEnabled(ped, enabled)
    return NPCManager.setAvoidance(ped, enabled)
end
function getNPCState(ped)
    return NPCManager.getState(ped)
end
function getNPCCurrentPath(ped)
    return NPCManager.getCurrentPath(ped)
end
function getNPCCurrentNode(ped)
    return NPCManager.getCurrentNode(ped)
end

local function commandAllowed(player)
    if not player or not isElement(player) then
        return true
    end
    return hasObjectPermissionTo(player, Config.security.commandACLRight, false)
end

local function commandRecord(player, id)
    if id then
        return NPCManager.getRecordById(id)
    end
    return NPCManager.getRecord(NPCManager.lastNPCByPlayer[player])
end

local function commandReply(player, message, red, green, blue)
    outputChatBox("[NPC-AI] " .. message, player, red or 120, green or 225, blue or 255)
end

addCommandHandler("npcspawn", function(player, _, model, amount)
    if not commandAllowed(player) then
        commandReply(player, "You do not have permission.", 255, 90, 90)
        return
    end
    if not isElement(player) then
        return
    end

    amount = NPCUtil.clamp(math.floor(tonumber(amount) or 1), 1, Config.security.maxSpawnPerCommand)
    model = tonumber(model) or 7
    local x, y, z = getElementPosition(player)
    local created = 0
    for index = 1, amount do
        local angle = math.rad((index - 1) * 37)
        local ped = NPCManager.create(model, x + math.cos(angle) * (2 + index * 0.2), y + math.sin(angle) * (2 + index * 0.2), z)
        if ped then
            created = created + 1
            NPCManager.lastNPCByPlayer[player] = ped
        end
    end
    commandReply(player, "Spawned " .. created .. " managed NPC(s).")
end)

addCommandHandler("npcwander", function(player, _, radius, id)
    if not commandAllowed(player) then
        return
    end
    local record = commandRecord(player, id)
    if not record then
        commandReply(player, "No managed NPC selected.", 255, 90, 90)
        return
    end
    local success, errorMessage = NPCManager.startWander(record.ped, radius)
    commandReply(player, success and ("NPC " .. record.id .. " is wandering.") or tostring(errorMessage), success and 120 or 255, success and 225 or 90, success and 255 or 90)
end)

addCommandHandler("npcgoto", function(player, _, x, y, z, id)
    if not commandAllowed(player) then
        return
    end
    local record = commandRecord(player, id)
    if not record then
        commandReply(player, "No managed NPC selected.", 255, 90, 90)
        return
    end
    local success, errorMessage = NPCManager.setDestination(record.ped, x, y, z)
    commandReply(player, success and ("NPC " .. record.id .. " received destination.") or tostring(errorMessage), success and 120 or 255, success and 225 or 90, success and 255 or 90)
end)

addCommandHandler("npcstop", function(player, _, id)
    if not commandAllowed(player) then
        return
    end
    local record = commandRecord(player, id)
    if not record then
        commandReply(player, "No managed NPC selected.", 255, 90, 90)
        return
    end
    NPCManager.stop(record.ped)
    commandReply(player, "NPC " .. record.id .. " stopped.")
end)

addCommandHandler("npctest", function(player, _, amount)
    if not commandAllowed(player) or not isElement(player) then
        return
    end
    amount = NPCUtil.clamp(math.floor(tonumber(amount) or 10), 1, Config.security.maxSpawnPerCommand)
    local x, y, z = getElementPosition(player)
    local created = 0
    for index = 1, amount do
        local angle = math.rad(index * 137.5)
        local radius = 3 + math.floor(index / 4) * 2
        local ped = NPCManager.create(7 + (index % 8), x + math.cos(angle) * radius, y + math.sin(angle) * radius, z)
        if ped then
            NPCManager.startWander(ped, Config.wandering.defaultRadius)
            NPCManager.lastNPCByPlayer[player] = ped
            created = created + 1
        end
    end
    commandReply(player, "Test spawned " .. created .. " wandering NPC(s).")
end)

addEventHandler("onPlayerQuit", root, function()
    NPCManager.lastNPCByPlayer[source] = nil
end)

addEventHandler("onResourceStop", resourceRoot, function()
    local toDestroy = {}
    for ped in pairs(NPCManager.recordsByPed) do
        toDestroy[#toDestroy + 1] = ped
    end
    for index = 1, #toDestroy do
        NPCManager.destroy(toDestroy[index])
    end
end)
