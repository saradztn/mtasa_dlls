-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: INCREMENTAL A* PATHFINDER
-- ============================================================================

NPCPathfinder = NPCPathfinder or {
    queue = {},
    activeByAgent = {},
    nextRequestId = 1,
}

local function heapPush(heap, entry)
    heap[#heap + 1] = entry
    local index = #heap
    while index > 1 do
        local parent = math.floor(index / 2)
        if heap[parent].priority <= entry.priority then
            break
        end
        heap[index] = heap[parent]
        index = parent
    end
    heap[index] = entry
end

local function heapPop(heap)
    local size = #heap
    if size == 0 then
        return nil
    end

    local result = heap[1]
    local last = heap[size]
    heap[size] = nil
    size = size - 1
    if size == 0 then
        return result
    end

    local index = 1
    while true do
        local left = index * 2
        if left > size then
            break
        end
        local right = left + 1
        local child = left
        if right <= size and heap[right].priority < heap[left].priority then
            child = right
        end
        if heap[child].priority >= last.priority then
            break
        end
        heap[index] = heap[child]
        index = child
    end
    heap[index] = last
    return result
end

local function enqueue(request)
    if request.cancelled or request.finished or request.enqueued or request.waiting then
        return
    end
    request.enqueued = true
    NPCPathfinder.queue[#NPCPathfinder.queue + 1] = request
end

local function detach(request)
    if request.agent and NPCPathfinder.activeByAgent[request.agent] == request then
        NPCPathfinder.activeByAgent[request.agent] = nil
    end
end

local function invokeCallback(request, success, path, information)
    if request.finished then
        return
    end
    request.finished = true
    detach(request)
    request.callback(success, path, information)
end

local function fail(request, reason)
    invokeCallback(request, false, nil, {
        reason = reason,
        iterations = request.iterations,
    })
end

local function reconstructPath(request)
    local path = {}
    local current = request.goalId
    local seen = {}

    while current do
        if seen[current] then
            return nil, "parent chain loop"
        end
        seen[current] = true
        path[#path + 1] = current
        if current == request.startId then
            break
        end
        current = request.parent[current]
        if #path > Config.pathfinding.maxPathNodes then
            return nil, "path exceeds maximum node count"
        end
    end

    if path[#path] ~= request.startId then
        return nil, "goal has no path to start"
    end

    local reversed = {}
    for index = #path, 1, -1 do
        reversed[#reversed + 1] = path[index]
    end
    return reversed
end

local function finishSuccess(request, rawPath, fromCache)
    if not fromCache then
        NPCPathCache.put(request.startId, request.goalId, rawPath)
    end
    local smoothed = NPCGraph.smoothPath(rawPath, request.agent and request.agent.ped or nil)
    invokeCallback(request, true, smoothed, {
        rawPath = rawPath,
        cached = fromCache == true,
        iterations = request.iterations or 0,
    })
end

local function waitForArea(request, area)
    if request.waiting or request.cancelled or request.finished then
        return
    end

    request.waiting = true
    NPCNodes.requestArea(area, function(success, reason)
        if request.cancelled or request.finished then
            return
        end
        request.waiting = false
        if success then
            enqueue(request)
        else
            request.unavailableAreas[area] = true
            NPCAILog.debug("PATH", "Area " .. tostring(area) .. " unavailable: " .. tostring(reason))
            enqueue(request)
        end
    end)
end

local function initialise(request)
    local start = NPCGraph.getNode(request.startId)
    local goal = NPCGraph.getNode(request.goalId)
    if not start or not goal then
        local areas = {}
        if not start then
            areas[#areas + 1] = math.floor(request.startId / 65536)
        end
        if not goal then
            areas[#areas + 1] = math.floor(request.goalId / 65536)
        end
        request.waiting = true
        NPCNodes.ensureAreas(areas, function(success, reason)
            if request.cancelled or request.finished then
                return
            end
            request.waiting = false
            if not success then
                fail(request, "required node area could not load: " .. tostring(reason))
                return
            end
            enqueue(request)
        end)
        return false
    end

    request.openSet = {}
    request.closedSet = {}
    request.gScore = { [request.startId] = 0 }
    request.fScore = { [request.startId] = NPCGraph.estimateCost(request.startId, request.goalId) * Config.pathfinding.heuristicWeight }
    request.parent = {}
    heapPush(request.openSet, {
        id = request.startId,
        priority = request.fScore[request.startId],
    })
    request.initialised = true
    return true
end

local function advance(request, budget)
    local operations = 0

    if not request.initialised then
        if not initialise(request) then
            return operations, "waiting"
        end
    end

    while operations < budget do
        local openEntry = heapPop(request.openSet)
        if not openEntry then
            fail(request, "open set exhausted")
            return operations, "finished"
        end

        local currentId = openEntry.id
        if not request.closedSet[currentId] and openEntry.priority <= (request.fScore[currentId] or math.huge) then
            operations = operations + 1
            request.iterations = request.iterations + 1
            if request.iterations > Config.pathfinding.maxIterations then
                fail(request, "max A* iterations reached")
                return operations, "finished"
            end

            if currentId == request.goalId then
                local rawPath, errorMessage = reconstructPath(request)
                if not rawPath then
                    fail(request, errorMessage)
                else
                    finishSuccess(request, rawPath, false)
                end
                return operations, "finished"
            end

            local currentNode = NPCGraph.getNode(currentId)
            if not currentNode then
                local area = math.floor(currentId / 65536)
                if not request.unavailableAreas[area] and not NPCNodes.isAreaLoaded(area) then
                    heapPush(request.openSet, openEntry)
                    waitForArea(request, area)
                    return operations, "waiting"
                end
                -- The area is present but this ID is not a pedestrian node
                -- (or the export is malformed), so discard this stale entry.
                request.closedSet[currentId] = true
            else
                local links = currentNode.links
                local needsArea
                for linkIndex = 1, #links do
                    local link = links[linkIndex]
                    if not NPCGraph.getNode(link.id)
                        and not NPCNodes.isAreaLoaded(link.area)
                        and not request.unavailableAreas[link.area]
                        and NPCNodes.hasAreaInManifest(link.area) then
                        needsArea = link.area
                        break
                    end
                end

                -- Do not mark this node closed before all potentially-ped
                -- neighbours in a streamed area can be inspected.
                if needsArea then
                    heapPush(request.openSet, openEntry)
                    waitForArea(request, needsArea)
                    return operations, "waiting"
                end

                request.closedSet[currentId] = true
                local currentCost = request.gScore[currentId] or math.huge
                for linkIndex = 1, #links do
                    local link = links[linkIndex]
                    local neighbour = NPCGraph.getNode(link.id)
                    if neighbour and neighbour.type == "ped" and not request.closedSet[neighbour.id] then
                        local tentativeCost = currentCost + NPCGraph.linkCost(currentNode, link, neighbour, request.options)
                        local previousCost = request.gScore[neighbour.id]
                        if not previousCost or tentativeCost < previousCost then
                            request.parent[neighbour.id] = currentId
                            request.gScore[neighbour.id] = tentativeCost
                            local heuristic = NPCGraph.estimateCost(neighbour.id, request.goalId) * Config.pathfinding.heuristicWeight
                            local score = tentativeCost + heuristic
                            request.fScore[neighbour.id] = score
                            heapPush(request.openSet, { id = neighbour.id, priority = score })
                        end
                    end
                end
            end
        end
    end

    return operations, "running"
end

function NPCPathfinder.cancel(agent)
    local request = NPCPathfinder.activeByAgent[agent]
    if not request then
        return false
    end
    request.cancelled = true
    detach(request)
    return true
end

function NPCPathfinder.request(agent, startId, goalId, callback, options)
    callback = callback or function() end
    options = options or {}
    NPCPathfinder.cancel(agent)

    if startId == goalId then
        callback(true, { startId }, { rawPath = { startId }, cached = false, iterations = 0 })
        return nil
    end

    local request = {
        id = NPCPathfinder.nextRequestId,
        agent = agent,
        startId = startId,
        goalId = goalId,
        callback = callback,
        options = options,
        unavailableAreas = {},
        iterations = 0,
        waiting = false,
        enqueued = false,
        cancelled = false,
        finished = false,
        initialised = false,
    }
    NPCPathfinder.nextRequestId = NPCPathfinder.nextRequestId + 1
    NPCPathfinder.activeByAgent[agent] = request

    -- Recovery routes carry temporary node penalties, so they must not reuse
    -- an ordinary cache entry that would undo the alternate-route attempt.
    local cached = not options.penaltyNodes and NPCPathCache.get(startId, goalId) or nil
    if cached then
        request.waiting = true
        NPCNodes.ensurePathAreas(cached, function(success, reason)
            if request.cancelled or request.finished then
                return
            end
            request.waiting = false
            if not success then
                fail(request, "cached path area could not load: " .. tostring(reason))
                return
            end
            finishSuccess(request, cached, true)
        end)
    else
        enqueue(request)
    end
    return request
end

function NPCPathfinder.tick()
    local timer = NPCProfiler.begin("pathfinding")
    local budget = Config.pathfinding.operationsPerTick
    local safety = #NPCPathfinder.queue * 2 + 1

    while budget > 0 and #NPCPathfinder.queue > 0 and safety > 0 do
        safety = safety - 1
        local request = table.remove(NPCPathfinder.queue, 1)
        request.enqueued = false
        if not request.cancelled and not request.finished and not request.waiting then
            local perRequestBudget = math.min(budget, Config.pathfinding.operationsPerRequest)
            local used, status = advance(request, perRequestBudget)
            budget = budget - math.max(used, 1)
            if status == "running" and not request.cancelled and not request.finished then
                enqueue(request)
            end
        end
    end

    NPCProfiler.finish(timer)
end

addEventHandler("onClientPreRender", root, function()
    NPCPathfinder.tick()
end)
