-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: PEDESTRIAN GRAPH
-- ============================================================================

NPCGraph = NPCGraph or {}

function NPCGraph.getNode(nodeId)
    return NPCNodes.getNode(nodeId)
end

function NPCGraph.getLinks(nodeId)
    local node = NPCNodes.getNode(nodeId)
    return node and node.links or nil
end

function NPCGraph.estimateCost(fromNodeId, toNodeId)
    local first = NPCNodes.getNode(fromNodeId)
    local second = NPCNodes.getNode(toNodeId)
    if not first or not second then
        return math.huge
    end
    return NPCUtil.distance3D(first.x, first.y, first.z, second.x, second.y, second.z)
end

function NPCGraph.linkCost(fromNode, link, toNode, options)
    local geometricDistance = NPCUtil.distance3D(fromNode.x, fromNode.y, fromNode.z, toNode.x, toNode.y, toNode.z)
    local recordedLength = tonumber(link.length) or 0

    -- The original byte length is retained in the data.  Route cost is never
    -- allowed below the Euclidean distance, which keeps the Euclidean A*
    -- heuristic admissible even when an original byte length was rounded down.
    local cost = math.max(recordedLength, geometricDistance)
    if cost <= 0 then
        return math.huge
    end

    if options and options.penaltyNodes and options.penaltyNodes[toNode.id] then
        cost = cost + options.penaltyNodes[toNode.id]
    end
    return cost
end

function NPCGraph.isPedLink(link)
    if not link then
        return false
    end
    local target = NPCNodes.getNode(link.id)
    return target ~= nil and target.type == "ped"
end

local function isCloseEnoughToPlayer(first, second)
    if not isElement(localPlayer) then
        return false
    end
    local playerX, playerY, playerZ = getElementPosition(localPlayer)
    local midpointX = (first.x + second.x) * 0.5
    local midpointY = (first.y + second.y) * 0.5
    local midpointZ = (first.z + second.z) * 0.5
    return NPCUtil.distance3D(playerX, playerY, playerZ, midpointX, midpointY, midpointZ)
        <= Config.pathfinding.smoothing.maxDistanceFromPlayer
end

-- LOS is a local validation layer, not a replacement for the authored graph.
-- MTA only guarantees world collision around the local player's draw distance,
-- so a segment outside that range is deliberately never smoothed away.
function NPCGraph.canWalkDirect(first, second, ignoredElement)
    if not first or not second then
        return false
    end

    local horizontalDistance = NPCUtil.distance2D(first.x, first.y, second.x, second.y)
    if horizontalDistance > Config.pathfinding.smoothing.maxSegmentDistance then
        return false
    end
    if math.abs(first.z - second.z) > Config.pathfinding.smoothing.maxVerticalDelta then
        return false
    end
    if not isCloseEnoughToPlayer(first, second) then
        return false
    end

    return isLineOfSightClear(
        first.x, first.y, first.z + 0.65,
        second.x, second.y, second.z + 0.65,
        true,  -- buildings
        false, -- dynamic vehicles are handled by local avoidance
        false, -- players
        true,  -- map objects
        false, -- dummies
        false, -- see-through collision
        false, -- camera objects
        false, -- shoot-through collision
        ignoredElement
    )
end

function NPCGraph.smoothPath(path, ignoredElement)
    if not Config.pathfinding.smoothing.enabled or #path <= 2 then
        return NPCUtil.copyArray(path)
    end

    local timer = NPCProfiler.begin("smoothing")
    local smoothed = { path[1] }
    local anchor = 1
    local checks = 0
    local maximumChecks = Config.pathfinding.smoothing.maxVisibilityChecks

    while anchor < #path do
        local selected = anchor + 1
        local first = NPCNodes.getNode(path[anchor])
        if not first then
            -- Preserve the remaining recorded route rather than taking an
            -- unvalidated shortcut after a streamed area was released.
            for index = anchor + 1, #path do
                smoothed[#smoothed + 1] = path[index]
            end
            break
        end

        for candidate = #path, anchor + 2, -1 do
            if checks >= maximumChecks then
                break
            end
            local second = NPCNodes.getNode(path[candidate])
            checks = checks + 1
            if second and NPCGraph.canWalkDirect(first, second, ignoredElement) then
                selected = candidate
                break
            end
        end

        smoothed[#smoothed + 1] = path[selected]
        anchor = selected
    end

    NPCProfiler.finish(timer)
    return smoothed
end

function NPCGraph.canUseFinalApproach(fromNode, destination, ignoredElement)
    if not destination or not fromNode then
        return false
    end
    if not Config.movement.finalApproachLineOfSight then
        return false
    end

    local distance = NPCUtil.distance3D(fromNode.x, fromNode.y, fromNode.z, destination.x, destination.y, destination.z)
    if distance > Config.movement.finalApproachDistance then
        return false
    end

    return NPCGraph.canWalkDirect(fromNode, destination, ignoredElement)
end
