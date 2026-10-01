-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: SPATIAL HASH
-- ============================================================================

NPCSpatial = NPCSpatial or {
    cells = {},
    nodeCells = {},
}

local function cellCoordinates(x, y)
    local size = Config.nodes.spatialCellSize
    return math.floor(x / size), math.floor(y / size)
end

local function cellKey(cx, cy)
    return tostring(cx) .. ":" .. tostring(cy)
end

function NPCSpatial.clear()
    NPCSpatial.cells = {}
    NPCSpatial.nodeCells = {}
end

function NPCSpatial.insert(node)
    if not node or not node.id then
        return false
    end

    local cx, cy = cellCoordinates(node.x, node.y)
    local key = cellKey(cx, cy)
    local cell = NPCSpatial.cells[key]
    if not cell then
        cell = {}
        NPCSpatial.cells[key] = cell
    end

    cell[node.id] = true
    NPCSpatial.nodeCells[node.id] = key
    return true
end

function NPCSpatial.remove(nodeId)
    local key = NPCSpatial.nodeCells[nodeId]
    if not key then
        return false
    end

    local cell = NPCSpatial.cells[key]
    if cell then
        cell[nodeId] = nil
        if next(cell) == nil then
            NPCSpatial.cells[key] = nil
        end
    end
    NPCSpatial.nodeCells[nodeId] = nil
    return true
end

function NPCSpatial.findNearest(x, y, z, maximumDistance, maximumRings)
    local timer = NPCProfiler.begin("navigation")
    maximumDistance = maximumDistance or math.huge
    maximumRings = maximumRings or Config.nodes.nearestSearchCellRings

    local baseX, baseY = cellCoordinates(x, y)
    local maximumDistanceSquared = maximumDistance * maximumDistance
    local bestNode
    local bestDistanceSquared = maximumDistanceSquared

    for ring = 0, maximumRings do
        for cx = baseX - ring, baseX + ring do
            for cy = baseY - ring, baseY + ring do
                if ring == 0 or math.abs(cx - baseX) == ring or math.abs(cy - baseY) == ring then
                    local cell = NPCSpatial.cells[cellKey(cx, cy)]
                    if cell then
                        for nodeId in pairs(cell) do
                            local node = NPCNodes.getNode(nodeId)
                            if node then
                                local distanceSquared = NPCUtil.distanceSquared(x, y, z, node.x, node.y, node.z)
                                if distanceSquared < bestDistanceSquared then
                                    bestDistanceSquared = distanceSquared
                                    bestNode = node
                                end
                            end
                        end
                    end
                end
            end
        end

        -- A point in later rings cannot beat the current candidate if its
        -- minimum horizontal cell distance is already greater than it.
        if bestNode and ring > 0 then
            local lowerBound = (ring - 1) * Config.nodes.spatialCellSize
            if lowerBound * lowerBound > bestDistanceSquared then
                break
            end
        end
    end

    NPCProfiler.finish(timer)
    if not bestNode then
        return nil, nil
    end
    return bestNode, math.sqrt(bestDistanceSquared)
end

function NPCSpatial.randomPedNodeInRadius(x, y, z, radius)
    local minimumCellX, minimumCellY = cellCoordinates(x - radius, y - radius)
    local maximumCellX, maximumCellY = cellCoordinates(x + radius, y + radius)
    local radiusSquared = radius * radius
    local selected
    local seen = 0

    for cx = minimumCellX, maximumCellX do
        for cy = minimumCellY, maximumCellY do
            local cell = NPCSpatial.cells[cellKey(cx, cy)]
            if cell then
                for nodeId in pairs(cell) do
                    local node = NPCNodes.getNode(nodeId)
                    if node then
                        local horizontalDistanceSquared = NPCUtil.distanceSquared(x, y, 0, node.x, node.y, 0)
                        local verticalDistance = math.abs((z or node.z) - node.z)
                        if horizontalDistanceSquared <= radiusSquared and verticalDistance <= 12 then
                            seen = seen + 1
                            -- Reservoir sampling avoids allocating a candidate list.
                            if math.random(seen) == 1 then
                                selected = node
                            end
                        end
                    end
                end
            end
        end
    end

    return selected
end

function NPCSpatial.eachNodeInRadius(x, y, radius, callback, limit)
    local minimumCellX, minimumCellY = cellCoordinates(x - radius, y - radius)
    local maximumCellX, maximumCellY = cellCoordinates(x + radius, y + radius)
    local radiusSquared = radius * radius
    local emitted = 0

    for cx = minimumCellX, maximumCellX do
        for cy = minimumCellY, maximumCellY do
            local cell = NPCSpatial.cells[cellKey(cx, cy)]
            if cell then
                for nodeId in pairs(cell) do
                    local node = NPCNodes.getNode(nodeId)
                    if node and NPCUtil.distanceSquared(x, y, 0, node.x, node.y, 0) <= radiusSquared then
                        callback(node)
                        emitted = emitted + 1
                        if limit and emitted >= limit then
                            return emitted
                        end
                    end
                end
            end
        end
    end

    return emitted
end
