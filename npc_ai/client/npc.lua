-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: CLIENT NPC STATE MACHINE AND SCHEDULER
-- ============================================================================

NPCAI = NPCAI or {
    agents = {},
    agentList = {},
    roundRobinIndex = 1,
    states = {
        IDLE = "IDLE",
        WANDER = "WANDER",
        WALK_TO_NODE = "WALK_TO_NODE",
        FOLLOW_PATH = "FOLLOW_PATH",
        AVOID_OBSTACLE = "AVOID_OBSTACLE",
        WAIT = "WAIT",
        STUCK = "STUCK",
        REPATH = "REPATH",
        FLEE = "FLEE",
        CHASE = "CHASE",
        GO_TO_LOCATION = "GO_TO_LOCATION",
        RETURN = "RETURN",
    },
}

local function isManagedPed(ped)
    return isElement(ped)
        and getElementType(ped) == "ped"
        and getElementData(ped, "npc_ai:managed") == true
end

local function taskDestination(task)
    if type(task) ~= "table" then
        return nil
    end
    local source = type(task.destination) == "table" and task.destination or task
    local x, y, z = source.x, source.y, source.z
    if not NPCUtil.isFinite(x) or not NPCUtil.isFinite(y) or not NPCUtil.isFinite(z) then
        return nil
    end
    return { x = x, y = y, z = z }
end

local function validTask(task)
    return type(task) == "table" and type(task.kind) == "string" and type(task.revision) == "number"
end

function NPCAI.ensureAgent(ped)
    if not isManagedPed(ped) then
        return nil
    end

    local existing = NPCAI.agents[ped]
    if existing then
        return existing
    end

    local agent = {
        ped = ped,
        state = NPCAI.states.IDLE,
        task = { kind = "idle", revision = 0 },
        taskRevision = 0,
        destination = nil,
        path = nil,
        pathPending = false,
        pathToken = 0,
        currentNode = nil,
        goalNode = nil,
        currentSpeed = 0,
        speed = Config.movement.defaultSpeed,
        avoidanceEnabled = true,
        avoidance = nil,
        controls = {},
        nextUpdateAt = 0,
        nextAvoidanceAt = 0,
        nextReportAt = 0,
        nextPathAttemptAt = 0,
        lastRepathAt = 0,
        retries = 0,
        completedRevision = nil,
        visitHistory = {},
        stuckSamples = {},
        stuckCount = 0,
        waitingForWander = false,
        lod = "sleep",
    }
    NPCAvoidance.clear(agent)
    NPCAI.agents[ped] = agent
    NPCAI.agentList[#NPCAI.agentList + 1] = agent
    return agent
end

function NPCAI.removeAgent(ped)
    local agent = NPCAI.agents[ped]
    if not agent then
        return
    end

    NPCPathfinder.cancel(agent)
    NPCMovement.release(agent)
    NPCAI.agents[ped] = nil
    for index = #NPCAI.agentList, 1, -1 do
        if NPCAI.agentList[index] == agent then
            table.remove(NPCAI.agentList, index)
            break
        end
    end
end

function NPCAI.getAgent(ped)
    return NPCAI.agents[ped]
end

function NPCAI.isAuthority(agent)
    return agent and isElement(agent.ped)
        and isElementStreamedIn(agent.ped)
        and isElementSyncer(agent.ped)
end

function NPCAI.getLOD(agent)
    if not isElement(agent.ped) or not isElement(localPlayer) or not NPCUtil.sameWorld(agent.ped, localPlayer) then
        return "sleep", Config.performance.sleepingTickMs
    end

    local pedX, pedY, pedZ = getElementPosition(agent.ped)
    local playerX, playerY, playerZ = getElementPosition(localPlayer)
    local distance = NPCUtil.distance3D(pedX, pedY, pedZ, playerX, playerY, playerZ)
    if distance <= Config.performance.nearDistance then
        return "near", Config.performance.nearTickMs
    elseif distance <= Config.performance.mediumDistance then
        return "medium", Config.performance.mediumTickMs
    elseif distance <= Config.performance.farDistance then
        return "far", Config.performance.farTickMs
    end
    return "sleep", Config.performance.sleepingTickMs
end

function NPCAI.setState(agent, state)
    if agent.state == state then
        return
    end
    agent.state = state
    NPCAILog.debug("STATE", "NPC " .. tostring(getElementData(agent.ped, "npc_ai:id") or "?") .. " -> " .. state)
end

local function resetPath(agent)
    agent.pathToken = agent.pathToken + 1
    NPCPathfinder.cancel(agent)
    agent.path = nil
    agent.pathPending = false
    agent.goalNode = nil
end

function NPCAI.applyTask(ped, task)
    if not validTask(task) then
        return false
    end

    local agent = NPCAI.ensureAgent(ped)
    if not agent then
        return false
    end

    if task.revision < agent.taskRevision then
        return false
    end
    if task.revision == agent.taskRevision and agent.task.kind == task.kind then
        return true
    end

    resetPath(agent)
    agent.task = task
    agent.taskRevision = task.revision
    agent.destination = taskDestination(task)
    agent.speed = tonumber(task.speed) or Config.movement.defaultSpeed
    agent.speed = NPCUtil.clamp(agent.speed, 0.2, Config.movement.runSpeed)
    agent.avoidanceEnabled = task.avoidance ~= false
    agent.completedRevision = nil
    agent.retries = 0
    agent.waitingForWander = false
    agent.recovery = nil
    agent.visitHistory = {}
    agent.stuckSamples = {}

    if task.paused then
        NPCAI.setState(agent, NPCAI.states.WAIT)
    elseif task.kind == "wander" then
        NPCAI.setState(agent, NPCAI.states.WANDER)
    elseif task.kind == "chase" then
        NPCAI.setState(agent, NPCAI.states.CHASE)
    elseif task.kind == "flee" then
        NPCAI.setState(agent, NPCAI.states.FLEE)
    elseif task.kind == "return" then
        NPCAI.setState(agent, NPCAI.states.RETURN)
    elseif task.kind == "go" then
        NPCAI.setState(agent, NPCAI.states.GO_TO_LOCATION)
    else
        NPCAI.setState(agent, NPCAI.states.IDLE)
    end
    return true
end

local function setDynamicDestination(agent, now)
    local task = agent.task
    if task.kind == "return" then
        agent.destination = taskDestination(task.home) or taskDestination(task)
        return agent.destination ~= nil
    end

    local target = task.target
    if (task.kind ~= "chase" and task.kind ~= "flee") or not isElement(target) or not NPCUtil.sameWorld(agent.ped, target) then
        return agent.destination ~= nil
    end

    local pedX, pedY, pedZ = getElementPosition(agent.ped)
    local targetX, targetY, targetZ = getElementPosition(target)
    if task.kind == "chase" then
        local changed = not agent.destination
            or NPCUtil.distance3D(agent.destination.x, agent.destination.y, agent.destination.z, targetX, targetY, targetZ) > 7
        if changed then
            agent.destination = { x = targetX, y = targetY, z = targetZ }
            agent.completedRevision = nil
            if now - agent.lastRepathAt >= Config.pathfinding.repathCooldownMs then
                NPCAI.requestRepath(agent, "chase target moved", true)
            end
        end
    else
        local awayX, awayY, distance = NPCUtil.normalize2D(pedX - targetX, pedY - targetY)
        if distance < 0.1 then
            awayX, awayY = NPCUtil.vectorFromRotation(math.random(0, 359))
        end
        local fleeDistance = NPCUtil.clamp(tonumber(task.fleeDistance) or 70, 25, 160)
        local goalX = NPCUtil.clamp(pedX + awayX * fleeDistance, -Config.security.worldCoordinateLimit, Config.security.worldCoordinateLimit)
        local goalY = NPCUtil.clamp(pedY + awayY * fleeDistance, -Config.security.worldCoordinateLimit, Config.security.worldCoordinateLimit)
        local changed = not agent.destination
            or NPCUtil.distance3D(agent.destination.x, agent.destination.y, agent.destination.z, goalX, goalY, pedZ) > 12
        agent.destination = { x = goalX, y = goalY, z = pedZ }
        agent.completedRevision = nil
        if changed and now - agent.lastRepathAt >= Config.pathfinding.repathCooldownMs then
            NPCAI.requestRepath(agent, "flee target changed", true)
        end
    end
    return agent.destination ~= nil
end

function NPCAI.requestPath(agent, reason)
    local now = NPCUtil.now()
    if agent.pathPending or now < agent.nextPathAttemptAt or not agent.destination then
        return false
    end

    agent.pathPending = true
    agent.pathToken = agent.pathToken + 1
    local token = agent.pathToken
    local revision = agent.taskRevision
    local pedX, pedY, pedZ = getElementPosition(agent.ped)
    NPCAI.setState(agent, NPCAI.states.REPATH)

    NPCAILog.debug("PATH", "NPC requested path: " .. tostring(reason or "task"))
    NPCNodes.findNearestPedNode(pedX, pedY, pedZ, function(startNode, startResult)
        if not NPCAI.agents[agent.ped] or token ~= agent.pathToken or revision ~= agent.taskRevision then
            return
        end
        if not startNode then
            agent.pathPending = false
            NPCAI.onPathFailed(agent, "no start ped node: " .. tostring(startResult))
            return
        end

        NPCNodes.findNearestPedNode(agent.destination.x, agent.destination.y, agent.destination.z, function(goalNode, goalResult)
            if not NPCAI.agents[agent.ped] or token ~= agent.pathToken or revision ~= agent.taskRevision then
                return
            end
            if not goalNode then
                agent.pathPending = false
                NPCAI.onPathFailed(agent, "no goal ped node: " .. tostring(goalResult))
                return
            end

            agent.currentNode = startNode.id
            agent.goalNode = goalNode.id
            NPCPathfinder.request(agent, startNode.id, goalNode.id, function(success, path, info)
                if not NPCAI.agents[agent.ped] or token ~= agent.pathToken or revision ~= agent.taskRevision then
                    return
                end
                agent.pathPending = false
                if not success then
                    NPCAI.onPathFailed(agent, info and info.reason or "A* failed")
                    return
                end

                agent.path = {
                    nodes = path,
                    index = 1,
                    rawNodes = info.rawPath,
                    createdAt = NPCUtil.now(),
                }
                agent.retries = 0
                agent.stuckCount = 0
                agent.nextPathAttemptAt = 0
                NPCAI.setState(agent, NPCAI.states.FOLLOW_PATH)
                NPCAILog.debug("PATH", "Path found: " .. tostring(#path) .. " nodes")
            end, {
                penaltyNodes = agent.repathPenaltyNodes,
            })
        end)
    end)
    return true
end

function NPCAI.requestRepath(agent, reason, force)
    local now = NPCUtil.now()
    local cooldown = reason == "obstacle" and Config.pathfinding.blockedRepathCooldownMs or Config.pathfinding.repathCooldownMs
    if not force and now - agent.lastRepathAt < cooldown then
        return false
    end

    agent.lastRepathAt = now
    agent.repathPenaltyNodes = {}
    for index = 1, #agent.visitHistory do
        agent.repathPenaltyNodes[agent.visitHistory[index]] = 18
    end
    resetPath(agent)
    agent.nextPathAttemptAt = now
    NPCAI.setState(agent, NPCAI.states.REPATH)
    NPCAILog.debug("REPATH", "Recalculating: " .. tostring(reason or "unknown"))
    return true
end

function NPCAI.onPathFailed(agent, reason)
    agent.retries = agent.retries + 1
    agent.nextPathAttemptAt = NPCUtil.now() + Config.pathfinding.retryDelayMs
    NPCAILog.warning("PATH", "NPC path failed (" .. tostring(reason) .. "), retry " .. agent.retries)

    if agent.retries <= Config.pathfinding.maxRetries then
        NPCAI.setState(agent, NPCAI.states.REPATH)
        return
    end

    if agent.task.kind == "wander" then
        agent.destination = nil
        agent.waitingForWander = false
        agent.retries = 0
        agent.waitUntil = NPCUtil.now() + Config.stuck.waitAfterFailureMs
        NPCAI.setState(agent, NPCAI.states.WAIT)
    else
        agent.waitUntil = NPCUtil.now() + Config.stuck.waitAfterFailureMs
        NPCAI.setState(agent, NPCAI.states.WAIT)
    end
end

function NPCAI.onNodeReached(agent, node)
    local history = agent.visitHistory
    history[#history + 1] = node.id
    while #history > Config.stuck.loopHistorySize do
        table.remove(history, 1)
    end

    local visits = 0
    for index = 1, #history do
        if history[index] == node.id then
            visits = visits + 1
        end
    end
    if visits >= Config.stuck.loopVisitsBeforeRepath and agent.path and agent.path.index < #agent.path.nodes then
        NPCAILog.warning("LOOP", "Repeated node " .. tostring(node.id) .. "; invalidating current path")
        NPCAI.requestRepath(agent, "loop", true)
    end
end

function NPCAI.onPathReached(agent)
    resetPath(agent)
    agent.currentSpeed = 0
    agent.stuckSamples = {}

    if agent.task.kind == "wander" then
        agent.destination = nil
        agent.waitingForWander = false
        agent.waitUntil = NPCUtil.now() + math.random(Config.wandering.idleMinMs, Config.wandering.idleMaxMs)
        NPCAI.setState(agent, NPCAI.states.WAIT)
    elseif agent.task.kind == "chase" or agent.task.kind == "flee" then
        agent.nextPathAttemptAt = NPCUtil.now() + Config.pathfinding.repathCooldownMs
        NPCAI.setState(agent, agent.task.kind == "chase" and NPCAI.states.CHASE or NPCAI.states.FLEE)
    else
        agent.completedRevision = agent.taskRevision
        NPCAI.setState(agent, NPCAI.states.IDLE)
    end
end

local function chooseWanderDestination(agent)
    if agent.waitingForWander then
        return
    end

    agent.waitingForWander = true
    local pedX, pedY, pedZ = getElementPosition(agent.ped)
    local requestedRadius = tonumber(agent.task.radius) or Config.wandering.defaultRadius
    local radius = NPCUtil.clamp(requestedRadius, Config.wandering.minRadius, Config.wandering.maxRadius)
    local areaRadius = math.max(Config.nodes.preloadAreaRadius, math.ceil(radius / Config.nodes.areaSize))

    NPCNodes.ensureAreasNear(pedX, pedY, areaRadius, function(success, reason)
        if not NPCAI.agents[agent.ped] or not agent.waitingForWander then
            return
        end
        if not success then
            agent.waitingForWander = false
            NPCAI.onPathFailed(agent, "wander nodes unavailable: " .. tostring(reason))
            return
        end

        local candidate = NPCSpatial.randomPedNodeInRadius(pedX, pedY, pedZ, radius)
        if not candidate then
            agent.waitingForWander = false
            NPCAI.onPathFailed(agent, "no valid loaded wander node")
            return
        end

        -- The server remains authoritative for the task. It validates that the
        -- current MTA syncer may nominate a bounded wander destination.
        triggerServerEvent(
            NPCProtocol.chooseWanderDestination,
            resourceRoot,
            agent.ped,
            candidate.x,
            candidate.y,
            candidate.z
        )
    end)
end

local function updateStuckDetection(agent, intent, now)
    if not intent or agent.state == NPCAI.states.WAIT or agent.state == NPCAI.states.IDLE then
        agent.stuckSamples = {}
        return
    end
    if agent.currentSpeed < 0.12 then
        return
    end

    local samples = agent.stuckSamples
    local latest = samples[#samples]
    if latest and now - latest.at < Config.stuck.sampleIntervalMs then
        return
    end

    local x, y, z = getElementPosition(agent.ped)
    samples[#samples + 1] = { x = x, y = y, z = z, at = now }
    while #samples > 1 and now - samples[1].at > Config.stuck.windowMs do
        table.remove(samples, 1)
    end

    if #samples >= 2 and now - samples[1].at >= Config.stuck.windowMs then
        local first = samples[1]
        local moved = NPCUtil.distance3D(first.x, first.y, first.z, x, y, z)
        if moved < Config.stuck.minimumMovement then
            NPCAI.beginRecovery(agent, intent, now)
            agent.stuckSamples = {}
        else
            agent.stuckCount = 0
        end
    end
end

function NPCAI.beginRecovery(agent, intent, now)
    if agent.recovery then
        return
    end

    agent.stuckCount = agent.stuckCount + 1
    NPCAI.setState(agent, NPCAI.states.STUCK)
    if agent.stuckCount > Config.stuck.maxRecoveries then
        NPCAILog.warning("STUCK", "NPC exhausted recovery attempts; waiting before fallback")
        resetPath(agent)
        agent.waitUntil = now + Config.stuck.waitAfterFailureMs
        agent.recovery = nil
        if agent.task.kind == "wander" then
            agent.destination = nil
        end
        NPCAI.setState(agent, NPCAI.states.WAIT)
        return
    end

    local side = ((getElementData(agent.ped, "npc_ai:id") or 0) + agent.stuckCount) % 2 == 0 and 1 or -1
    local sideX = -intent.directionY * side
    local sideY = intent.directionX * side
    local x, y, z = getElementPosition(agent.ped)
    agent.recovery = {
        stage = 1,
        side = side,
        target = { x = x + sideX * 1.35, y = y + sideY * 1.35, z = z },
        untilAt = now + Config.stuck.localRecoveryMs,
    }
    NPCAILog.warning("STUCK", "NPC local recovery stage " .. agent.stuckCount)
end

local function advanceRecovery(agent, now)
    local recovery = agent.recovery
    if not recovery or now < recovery.untilAt then
        return false
    end

    local x, y, z = getElementPosition(agent.ped)
    if recovery.stage == 1 then
        local forwardX, forwardY = NPCUtil.vectorFromRotation(select(3, getElementRotation(agent.ped)))
        local sideX = -forwardY * -recovery.side
        local sideY = forwardX * -recovery.side
        recovery.stage = 2
        recovery.target = { x = x + sideX * 1.65, y = y + sideY * 1.65, z = z }
        recovery.untilAt = now + Config.stuck.alternateRecoveryMs
        return true
    end

    agent.recovery = nil
    -- Fallback selects a fresh, valid graph anchor. It does not move/teleport
    -- the ped; native collision and controls remain responsible for position.
    NPCNodes.findNearestPedNode(x, y, z, function(node)
        if NPCAI.agents[agent.ped] and node then
            agent.currentNode = node.id
            NPCAI.requestRepath(agent, "stuck recovery", true)
        end
    end)
    return true
end

local function reportAgent(agent, now)
    if now < agent.nextReportAt or not NPCAI.isAuthority(agent) then
        return
    end
    agent.nextReportAt = now + Config.networking.reportIntervalMs
    local pathForReport = {}
    if agent.path and agent.path.nodes then
        for index = 1, math.min(#agent.path.nodes, 256) do
            pathForReport[index] = agent.path.nodes[index]
        end
    end
    triggerServerEvent(NPCProtocol.report, resourceRoot, agent.ped, {
        state = agent.state,
        currentNode = agent.currentNode,
        goalNode = agent.goalNode,
        speed = agent.currentSpeed or 0,
        pathLength = agent.path and #agent.path.nodes or 0,
        path = pathForReport,
        repaths = agent.stuckCount,
    })
end

local function updateAgent(agent, now)
    if not isElement(agent.ped) then
        NPCAI.removeAgent(agent.ped)
        return
    end

    local lod, interval = NPCAI.getLOD(agent)
    agent.lod = lod
    agent.nextUpdateAt = now + interval

    if not NPCAI.isAuthority(agent) then
        NPCMovement.release(agent)
        return
    end

    local task = agent.task
    if task.paused or lod == "sleep" then
        NPCAI.setState(agent, NPCAI.states.WAIT)
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    if agent.state == NPCAI.states.WAIT then
        if agent.waitUntil and now < agent.waitUntil then
            NPCMovement.release(agent)
            reportAgent(agent, now)
            return
        end
        agent.waitUntil = nil
        if task.kind == "wander" then
            NPCAI.setState(agent, NPCAI.states.WANDER)
        elseif agent.completedRevision == task.revision then
            NPCAI.setState(agent, NPCAI.states.IDLE)
            NPCMovement.release(agent)
            reportAgent(agent, now)
            return
        end
    end

    if task.kind == "idle" or (agent.completedRevision == task.revision and task.kind ~= "chase" and task.kind ~= "flee") then
        NPCAI.setState(agent, NPCAI.states.IDLE)
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    if task.kind == "wander" and not agent.destination then
        NPCAI.setState(agent, NPCAI.states.WANDER)
        NPCMovement.release(agent)
        chooseWanderDestination(agent)
        reportAgent(agent, now)
        return
    end

    if not setDynamicDestination(agent, now) then
        NPCAI.onPathFailed(agent, "task has no valid destination")
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    if not agent.path and not agent.pathPending then
        NPCAI.requestPath(agent, "path absent")
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    if agent.pathPending then
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    advanceRecovery(agent, now)
    local preliminaryIntent, steeringReason = NPCSteering.compute(agent, interval / 1000)
    if not preliminaryIntent then
        if steeringReason == "path complete" then
            NPCAI.onPathReached(agent)
        else
            NPCAI.requestRepath(agent, steeringReason or "steering failed", true)
        end
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    if now >= agent.nextAvoidanceAt then
        NPCAvoidance.update(agent, preliminaryIntent.heading)
        agent.nextAvoidanceAt = now + NPCAvoidance.getIntervalForLOD(lod)
    end

    local intent, finalReason = NPCSteering.compute(agent, interval / 1000)
    if not intent then
        if finalReason == "path complete" then
            NPCAI.onPathReached(agent)
        else
            NPCAI.requestRepath(agent, finalReason or "steering failed", true)
        end
        NPCMovement.release(agent)
        reportAgent(agent, now)
        return
    end

    if agent.avoidance and agent.avoidance.blocked then
        NPCAI.setState(agent, NPCAI.states.AVOID_OBSTACLE)
        if agent.blockedSince and now - agent.blockedSince >= Config.avoidance.majorObstaclePersistMs then
            NPCAI.requestRepath(agent, "obstacle", false)
        end
    elseif agent.recovery then
        NPCAI.setState(agent, NPCAI.states.STUCK)
    else
        NPCAI.setState(agent, NPCAI.states.FOLLOW_PATH)
    end

    NPCMovement.apply(agent, intent, interval / 1000)
    updateStuckDetection(agent, intent, now)
    reportAgent(agent, now)
end

function NPCAI.tick(now)
    local timer = NPCProfiler.begin("npc_update")
    local count = #NPCAI.agentList
    local processed = 0
    local scanned = 0
    local maximum = Config.performance.maxAgentsPerFrame

    while count > 0 and scanned < count and processed < maximum do
        if NPCAI.roundRobinIndex > #NPCAI.agentList then
            NPCAI.roundRobinIndex = 1
        end
        local agent = NPCAI.agentList[NPCAI.roundRobinIndex]
        NPCAI.roundRobinIndex = NPCAI.roundRobinIndex + 1
        scanned = scanned + 1
        if agent and now >= agent.nextUpdateAt then
            updateAgent(agent, now)
            processed = processed + 1
        end
        count = #NPCAI.agentList
    end

    local anchors = { localPlayer }
    for index = 1, #NPCAI.agentList do
        local agent = NPCAI.agentList[index]
        if agent and NPCAI.isAuthority(agent) then
            anchors[#anchors + 1] = agent.ped
        end
    end
    NPCNodes.collectGarbage(anchors)
    NPCProfiler.finish(timer)
    NPCProfiler.rollWindow(now)
end

addEvent(NPCProtocol.task, true)
addEventHandler(NPCProtocol.task, root, function(ped, task)
    if source ~= resourceRoot or not isManagedPed(ped) then
        return
    end
    NPCAI.applyTask(ped, task)
end)

addEvent(NPCProtocol.taskSnapshot, true)
addEventHandler(NPCProtocol.taskSnapshot, root, function(snapshot)
    if source ~= resourceRoot or type(snapshot) ~= "table" then
        return
    end
    for index = 1, #snapshot do
        local entry = snapshot[index]
        if type(entry) == "table" then
            NPCAI.applyTask(entry.ped, entry.task)
        end
    end
end)

addEventHandler("onClientElementStreamIn", root, function()
    if isManagedPed(source) then
        NPCAI.ensureAgent(source)
        triggerServerEvent(NPCProtocol.requestTask, resourceRoot, source)
    end
end)

addEventHandler("onClientElementStreamOut", root, function()
    local agent = NPCAI.getAgent(source)
    if agent then
        NPCMovement.release(agent)
    end
end)

addEventHandler("onClientElementDestroy", root, function()
    if NPCAI.getAgent(source) then
        NPCAI.removeAgent(source)
    end
end)

addEventHandler("onClientPreRender", root, function()
    NPCAI.tick(NPCUtil.now())
end)

addEventHandler("onClientResourceStart", resourceRoot, function()
    NPCProfiler.configure(Config.performance.profilerWindowMs)
    local peds = getElementsByType("ped", root, true)
    for index = 1, #peds do
        if isManagedPed(peds[index]) then
            NPCAI.ensureAgent(peds[index])
        end
    end
    triggerServerEvent(NPCProtocol.requestTasks, resourceRoot)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    for _, agent in pairs(NPCAI.agents) do
        NPCMovement.release(agent)
    end
end)
