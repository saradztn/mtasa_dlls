-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: CLIENT DEBUG VISUALIZATION
-- ============================================================================

NPCDebug = NPCDebug or {
    enabled = Config.debug,
    showNodes = false,
    showPaths = true,
    showRays = false,
    showLabels = true,
    showCollision = false,
    showState = true,
    showProfiler = Config.debugDraw.showProfiler,
}

local function drawPoint(x, y, z, size, color)
    dxDrawLine3D(x - size, y, z, x + size, y, z, color, Config.debugDraw.lineWidth)
    dxDrawLine3D(x, y - size, z, x, y + size, z, color, Config.debugDraw.lineWidth)
end

local function drawTextAt(x, y, z, text, color)
    local screenX, screenY = getScreenFromWorldPosition(x, y, z)
    if screenX then
        dxDrawText(text, screenX, screenY, screenX, screenY, color, 1, "default-bold", "center", "bottom", false, false, false)
    end
end

function NPCDebug.getNearestAgent()
    local nearest
    local bestDistance = math.huge
    if not isElement(localPlayer) then
        return nil
    end
    local playerX, playerY, playerZ = getElementPosition(localPlayer)
    for _, agent in pairs(NPCAI.agents) do
        if isElement(agent.ped) and NPCUtil.sameWorld(agent.ped, localPlayer) then
            local x, y, z = getElementPosition(agent.ped)
            local distance = NPCUtil.distance3D(playerX, playerY, playerZ, x, y, z)
            if distance < bestDistance then
                bestDistance = distance
                nearest = agent
            end
        end
    end
    return nearest
end

local function drawPath(agent)
    if not agent.path or not agent.path.nodes then
        return
    end

    local previous
    for index = math.max(1, agent.path.index - 1), #agent.path.nodes do
        local node = NPCNodes.getNode(agent.path.nodes[index])
        if node then
            if previous then
                dxDrawLine3D(previous.x, previous.y, previous.z + 0.15, node.x, node.y, node.z + 0.15, tocolor(42, 209, 255, 220), Config.debugDraw.lineWidth)
            end
            drawPoint(node.x, node.y, node.z + 0.15, 0.13, tocolor(42, 209, 255, 230))
            previous = node
        end
    end
end

local function drawAvoidance(agent)
    local avoidance = agent.avoidance
    if not avoidance or not avoidance.rays then
        return
    end

    for index = 1, #avoidance.rays do
        local ray = avoidance.rays[index]
        local color = ray.hit and tocolor(255, 89, 89, 220) or tocolor(112, 255, 147, 150)
        local endX = ray.hit and ray.hitX or ray.endX
        local endY = ray.hit and ray.hitY or ray.endY
        local endZ = ray.hit and ray.hitZ or ray.endZ
        dxDrawLine3D(ray.startX, ray.startY, ray.startZ, endX, endY, endZ, color, 1)
    end
end

local function drawNearbyNodes(agent)
    local x, y, z = getElementPosition(agent.ped)
    NPCSpatial.eachNodeInRadius(x, y, 13, function(node)
        drawPoint(node.x, node.y, node.z + 0.08, Config.debugDraw.nodeRadius, tocolor(255, 204, 74, 160))
    end, 100)
end

local function drawAgent(agent)
    if not isElement(agent.ped) or not NPCUtil.sameWorld(agent.ped, localPlayer) then
        return
    end

    local x, y, z = getElementPosition(agent.ped)
    local playerX, playerY, playerZ = getElementPosition(localPlayer)
    if NPCUtil.distance3D(x, y, z, playerX, playerY, playerZ) > Config.debugDraw.maxDistance then
        return
    end

    if NPCDebug.showPaths then
        drawPath(agent)
    end
    if NPCDebug.showRays then
        drawAvoidance(agent)
    end
    if NPCDebug.showCollision and agent.avoidance and agent.avoidance.closestHit then
        local hit = agent.avoidance.closestHit
        if hit.hitX then
            drawPoint(hit.hitX, hit.hitY, hit.hitZ + 0.05, 0.22, tocolor(255, 72, 72, 230))
        end
    end
    if NPCDebug.showNodes then
        drawNearbyNodes(agent)
    end

    local color = agent.state == NPCAI.states.STUCK and tocolor(255, 79, 79, 240) or tocolor(255, 255, 255, 220)
    drawPoint(x, y, z + 0.16, 0.28, color)

    if agent.destination then
        dxDrawLine3D(x, y, z + 0.25, agent.destination.x, agent.destination.y, agent.destination.z + 0.25, tocolor(255, 196, 78, 100), 1)
        drawPoint(agent.destination.x, agent.destination.y, agent.destination.z + 0.15, 0.24, tocolor(255, 196, 78, 210))
    end

    if NPCDebug.showLabels or NPCDebug.showState then
        local current = agent.currentNode and tostring(agent.currentNode) or "-"
        local goal = agent.goalNode and tostring(agent.goalNode) or "-"
        local pathLength = agent.path and #agent.path.nodes or 0
        local text = string.format(
            "NPC %s\n%s [%s]\nnode %s -> %s | path %d\nspeed %.2f | %s",
            tostring(getElementData(agent.ped, "npc_ai:id") or "?"),
            agent.state,
            agent.lod or "-",
            current,
            goal,
            pathLength,
            agent.currentSpeed or 0,
            isElementSyncer(agent.ped) and "LOCAL SYNCER" or "remote"
        )
        drawTextAt(x, y, z + 1.25, text, color)
    end
end

local function profilerLine(label, key)
    local elapsed, count = NPCProfiler.getLast(key)
    return string.format("%s: %.2f ms (%d samples)", label, elapsed, count)
end

function NPCDebug.drawProfiler()
    if not NPCDebug.showProfiler then
        return
    end

    local snapshot = NPCProfiler.getSnapshot()
    if not snapshot.elapsedMs then
        return
    end

    local text = table.concat({
        "NPC AI PROFILER",
        "Window: " .. tostring(snapshot.elapsedMs) .. " ms | NPCs: " .. tostring(#NPCAI.agentList),
        profilerLine("Pathfinding", "pathfinding"),
        profilerLine("Steering/NPC", "npc_update"),
        profilerLine("Avoidance", "avoidance"),
        profilerLine("Navigation", "navigation"),
        profilerLine("Node load", "node_load"),
        profilerLine("Smoothing", "smoothing"),
    }, "\n")
    dxDrawText(text, 18, 190, 450, 450, tocolor(235, 245, 255, 235), 1, "default-bold", "left", "top", false, false, false)
end

function NPCDebug.toggle(option)
    if not option or option == "all" then
        NPCDebug.enabled = not NPCDebug.enabled
    elseif option == "on" then
        NPCDebug.enabled = true
    elseif option == "off" then
        NPCDebug.enabled = false
    elseif option == "nodes" then
        NPCDebug.enabled = true
        NPCDebug.showNodes = not NPCDebug.showNodes
    elseif option == "paths" or option == "path" then
        NPCDebug.enabled = true
        NPCDebug.showPaths = not NPCDebug.showPaths
    elseif option == "rays" then
        NPCDebug.enabled = true
        NPCDebug.showRays = not NPCDebug.showRays
    elseif option == "labels" then
        NPCDebug.enabled = true
        NPCDebug.showLabels = not NPCDebug.showLabels
    elseif option == "collision" then
        NPCDebug.enabled = true
        NPCDebug.showCollision = not NPCDebug.showCollision
    elseif option == "state" then
        NPCDebug.enabled = true
        NPCDebug.showState = not NPCDebug.showState
    elseif option == "profiler" then
        NPCDebug.enabled = true
        NPCDebug.showProfiler = not NPCDebug.showProfiler
    else
        outputChatBox("[NPC-AI] /npcdebug [on|off|nodes|paths|rays|collision|labels|state|profiler]", 255, 210, 100)
        return
    end
    outputChatBox("[NPC-AI] Debug " .. tostring(option or "all") .. " toggled", 100, 230, 255)
end

addEvent(NPCProtocol.toggleDebug, true)
addEventHandler(NPCProtocol.toggleDebug, root, function(option)
    if source == resourceRoot then
        NPCDebug.toggle(option)
    end
end)

addCommandHandler("npcdebug", function(_, option)
    NPCDebug.toggle(option)
end)

addCommandHandler("npcnodes", function()
    NPCDebug.toggle("nodes")
end)

addCommandHandler("npcpath", function()
    NPCDebug.toggle("paths")
end)

addEventHandler("onClientRender", root, function()
    if not NPCDebug.enabled or not isElement(localPlayer) then
        return
    end
    for _, agent in pairs(NPCAI.agents) do
        drawAgent(agent)
    end
    NPCDebug.drawProfiler()
end)
