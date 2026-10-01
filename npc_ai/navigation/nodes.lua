-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: GTA SA NODE STREAMING AND LOADING
-- ============================================================================

NPCNodes = NPCNodes or {
    manifest = nil,
    loadedAreas = {},
    pedNodes = {},
    nearestCache = {},
    pendingByPath = {},
    loadedAreaCount = 0,
    lastGarbageCollectionAt = 0,
}

local function readFileText(path)
    local handle = fileOpen(path)
    if not handle then
        return nil, "fileOpen failed"
    end

    local size = fileGetSize(handle)
    local content = fileRead(handle, size)
    fileClose(handle)
    if not content then
        return nil, "fileRead failed"
    end
    return content
end

local function finishPending(path, success, reason)
    local pending = NPCNodes.pendingByPath[path]
    NPCNodes.pendingByPath[path] = nil
    if not pending then
        return
    end

    for index = 1, #pending.callbacks do
        local callback = pending.callbacks[index]
        callback(success, reason)
    end
end

local function getAreaManifest(area)
    if not NPCNodes.manifest or type(NPCNodes.manifest.areas) ~= "table" then
        return nil
    end
    return NPCNodes.manifest.areas[tostring(area)] or NPCNodes.manifest.areas[area]
end

local function areaCoordinates(area)
    local axis = Config.nodes.areasPerAxis
    return area % axis, math.floor(area / axis)
end

function NPCNodes.getAreaAtPosition(x, y)
    local column = math.floor((x - Config.nodes.worldMin) / Config.nodes.areaSize)
    local row = math.floor((y - Config.nodes.worldMin) / Config.nodes.areaSize)
    if column < 0 or row < 0 or column >= Config.nodes.areasPerAxis or row >= Config.nodes.areasPerAxis then
        return nil
    end
    return row * Config.nodes.areasPerAxis + column
end

function NPCNodes.getNode(nodeId)
    local node = NPCNodes.pedNodes[nodeId]
    if node then
        local area = NPCNodes.loadedAreas[node.area]
        if area then
            area.lastUsedAt = NPCUtil.now()
        end
    end
    return node
end

function NPCNodes.getArea(area)
    return NPCNodes.loadedAreas[area]
end

function NPCNodes.getVehicleNodes(area)
    local areaRecord = NPCNodes.loadedAreas[area]
    return areaRecord and areaRecord.vehicleNodes or nil
end

function NPCNodes.isAreaLoaded(area)
    return NPCNodes.loadedAreas[area] ~= nil
end

function NPCNodes.hasAreaInManifest(area)
    return getAreaManifest(area) ~= nil
end

function NPCNodes.loadManifest()
    local text, errorMessage = readFileText(Config.nodes.manifestPath)
    if not text then
        NPCAILog.error("NODES", "Cannot read manifest: " .. tostring(errorMessage))
        return false
    end

    local manifest = fromJSON(text)
    if type(manifest) ~= "table" or manifest.format ~= "npc_ai.gta_sa_ped_graph.v1" then
        NPCAILog.error("NODES", "Invalid or unsupported node manifest")
        return false
    end

    NPCNodes.manifest = manifest
    local areaCount = NPCUtil.tableCount(manifest.areas or {})
    if areaCount == 0 then
        NPCAILog.warning("NODES", "No converted node areas found; run tools/convert_nodes.py first")
    else
        NPCAILog.info("NODES", "Manifest loaded (" .. areaCount .. " streamed areas)")
    end
    return true
end

local function ingestArea(data, expectedArea)
    if type(data) ~= "table" or data.format ~= "npc_ai.gta_sa_ped_graph.v1" then
        return false, "invalid chunk format"
    end
    if data.area ~= expectedArea then
        return false, "area id mismatch"
    end
    if NPCNodes.loadedAreas[expectedArea] then
        return true
    end

    local timer = NPCProfiler.begin("node_load")
    local areaRecord = {
        id = expectedArea,
        bounds = data.bounds,
        header = data.header,
        vehicleNodes = data.vehicle or {},
        naviNodes = data.navi or {},
        pedNodeIds = {},
        loadedAt = NPCUtil.now(),
        lastUsedAt = NPCUtil.now(),
    }

    local pedRecords = data.ped or {}
    for index = 1, #pedRecords do
        local raw = pedRecords[index]
        local nodeId = raw[1]
        local x, y, z = raw[2], raw[3], raw[4]
        if NPCUtil.isFinite(nodeId) and NPCUtil.isFinite(x) and NPCUtil.isFinite(y) and NPCUtil.isFinite(z) then
            local globalId = NPCUtil.makeNodeId(expectedArea, nodeId)
            if not NPCNodes.pedNodes[globalId] then
                local node = {
                    id = globalId,
                    nodeId = nodeId,
                    area = expectedArea,
                    x = x,
                    y = y,
                    z = z,
                    width = raw[5] or 0,
                    flags = raw[6] or 0,
                    floodFill = raw[7] or 0,
                    heuristicCost = raw[8] or 0,
                    linkOffset = raw[9] or 0,
                    memoryAddress = raw[11] or 0,
                    unused = raw[12] or 0,
                    sourceType = raw[13] or "ped",
                    type = "ped",
                    links = {},
                }

                local rawLinks = raw[10] or {}
                for linkIndex = 1, #rawLinks do
                    local rawLink = rawLinks[linkIndex]
                    local targetArea = rawLink[1]
                    local targetNodeId = rawLink[2]
                    if NPCUtil.isFinite(targetArea) and NPCUtil.isFinite(targetNodeId) then
                        node.links[#node.links + 1] = {
                            id = NPCUtil.makeNodeId(targetArea, targetNodeId),
                            area = targetArea,
                            nodeId = targetNodeId,
                            length = rawLink[3] or 0,
                            intersectionFlags = rawLink[4] or 0,
                            naviLink = rawLink[5] or 0,
                            direction = "outbound",
                        }
                    end
                end

                NPCNodes.pedNodes[globalId] = node
                areaRecord.pedNodeIds[#areaRecord.pedNodeIds + 1] = globalId
                NPCSpatial.insert(node)
            end
        else
            NPCAILog.warning("NODES", "Ignored invalid ped node in area " .. tostring(expectedArea))
        end
    end

    NPCNodes.loadedAreas[expectedArea] = areaRecord
    NPCNodes.loadedAreaCount = NPCNodes.loadedAreaCount + 1
    NPCProfiler.finish(timer)
    NPCAILog.debug("NODES", "Loaded area " .. expectedArea .. " (" .. #areaRecord.pedNodeIds .. " ped nodes)")
    return true
end

local function parseDownloadedArea(area, path)
    local text, errorMessage = readFileText(path)
    if not text then
        return false, errorMessage
    end

    local decoded = fromJSON(text)
    return ingestArea(decoded, area)
end

function NPCNodes.requestArea(area, callback)
    callback = callback or function() end
    if NPCNodes.loadedAreas[area] then
        NPCNodes.loadedAreas[area].lastUsedAt = NPCUtil.now()
        callback(true)
        return true
    end

    local metadata = getAreaManifest(area)
    if not metadata or type(metadata.file) ~= "string" then
        callback(false, "area is absent from the manifest")
        return false
    end

    local path = metadata.file
    local pending = NPCNodes.pendingByPath[path]
    if pending then
        pending.callbacks[#pending.callbacks + 1] = callback
        return true
    end

    pending = {
        area = area,
        callbacks = { callback },
    }
    NPCNodes.pendingByPath[path] = pending

    -- Node chunks are declared download="false" by the converter.  The MTA
    -- download event is the only authority that a chunk is ready to fileOpen.
    if not downloadFile(path) then
        NPCNodes.pendingByPath[path] = nil
        callback(false, "downloadFile was rejected (missing meta.xml file entry?)")
        return false
    end
    return true
end

function NPCNodes.ensureAreas(areas, callback)
    local uniqueAreas = {}
    local visited = {}
    for index = 1, #areas do
        local area = areas[index]
        if area ~= nil and not visited[area] then
            visited[area] = true
            uniqueAreas[#uniqueAreas + 1] = area
        end
    end

    local remaining = #uniqueAreas
    local failedReason
    if remaining == 0 then
        callback(true)
        return
    end

    for index = 1, #uniqueAreas do
        local area = uniqueAreas[index]
        NPCNodes.requestArea(area, function(success, reason)
            if not success and not failedReason then
                failedReason = reason or "unknown area load failure"
            end
            remaining = remaining - 1
            if remaining == 0 then
                callback(not failedReason, failedReason)
            end
        end)
    end
end

function NPCNodes.ensureAreasNear(x, y, radiusInAreas, callback)
    local center = NPCNodes.getAreaAtPosition(x, y)
    if center == nil then
        callback(false, "position is outside GTA SA node grid")
        return
    end

    local centerColumn, centerRow = areaCoordinates(center)
    local areas = {}
    for row = centerRow - radiusInAreas, centerRow + radiusInAreas do
        for column = centerColumn - radiusInAreas, centerColumn + radiusInAreas do
            if column >= 0 and row >= 0 and column < Config.nodes.areasPerAxis and row < Config.nodes.areasPerAxis then
                areas[#areas + 1] = row * Config.nodes.areasPerAxis + column
            end
        end
    end
    NPCNodes.ensureAreas(areas, callback)
end

function NPCNodes.getNearestPedNode(x, y, z, maximumDistance)
    if not NPCUtil.isFinite(x) or not NPCUtil.isFinite(y) or not NPCUtil.isFinite(z) then
        return nil, "invalid position"
    end

    local cacheSize = Config.nodes.nearestCacheCellSize
    local cacheKey = math.floor(x / cacheSize) .. ":" .. math.floor(y / cacheSize) .. ":" .. math.floor(z / cacheSize)
    local cached = NPCNodes.nearestCache[cacheKey]
    if cached then
        local cachedNode = NPCNodes.getNode(cached.nodeId)
        if cachedNode and NPCUtil.distance3D(x, y, z, cached.x, cached.y, cached.z) <= Config.nodes.nearestCacheDistance then
            local distance = NPCUtil.distance3D(x, y, z, cachedNode.x, cachedNode.y, cachedNode.z)
            if not maximumDistance or distance <= maximumDistance then
                return cachedNode, distance
            end
        end
    end

    local node, distance = NPCSpatial.findNearest(x, y, z, maximumDistance)
    if node then
        NPCNodes.nearestCache[cacheKey] = {
            nodeId = node.id,
            x = x,
            y = y,
            z = z,
        }
        return node, distance
    end
    return nil, "no loaded ped node near position"
end

-- Asynchronous nearest lookup for streamed chunks.  The public synchronous
-- getNearestPedNode function remains available for already-loaded areas.
function NPCNodes.findNearestPedNode(x, y, z, callback, maximumDistance)
    local node, distance = NPCNodes.getNearestPedNode(x, y, z, maximumDistance)
    if node then
        callback(node, distance)
        return
    end

    NPCNodes.ensureAreasNear(x, y, Config.nodes.preloadAreaRadius, function(success, reason)
        if not success then
            callback(nil, reason)
            return
        end
        local foundNode, foundDistance = NPCNodes.getNearestPedNode(x, y, z, maximumDistance)
        callback(foundNode, foundDistance or "no ped node in loaded neighbourhood")
    end)
end

function NPCNodes.ensurePathAreas(path, callback)
    local areas = {}
    local seen = {}
    for index = 1, #path do
        local area = math.floor(path[index] / 65536)
        if not seen[area] then
            seen[area] = true
            areas[#areas + 1] = area
        end
    end
    NPCNodes.ensureAreas(areas, callback)
end

function NPCNodes.unloadArea(area)
    local areaRecord = NPCNodes.loadedAreas[area]
    if not areaRecord then
        return false
    end

    for index = 1, #areaRecord.pedNodeIds do
        local nodeId = areaRecord.pedNodeIds[index]
        NPCSpatial.remove(nodeId)
        NPCNodes.pedNodes[nodeId] = nil
    end

    NPCNodes.loadedAreas[area] = nil
    NPCNodes.loadedAreaCount = math.max(0, NPCNodes.loadedAreaCount - 1)
    return true
end

function NPCNodes.collectGarbage(anchorElements)
    local now = NPCUtil.now()
    if now - NPCNodes.lastGarbageCollectionAt < Config.performance.areaGcTickMs then
        return
    end
    NPCNodes.lastGarbageCollectionAt = now

    if NPCNodes.loadedAreaCount <= Config.nodes.maxLoadedAreas then
        return
    end

    local candidates = {}
    for area, record in pairs(NPCNodes.loadedAreas) do
        local shouldKeep = false
        if anchorElements then
            for index = 1, #anchorElements do
                local element = anchorElements[index]
                if isElement(element) then
                    local x, y = getElementPosition(element)
                    local elementArea = NPCNodes.getAreaAtPosition(x, y)
                    if elementArea == area then
                        shouldKeep = true
                        break
                    end
                end
            end
        end

        if not shouldKeep and now - record.lastUsedAt > Config.nodes.unloadAfterMs then
            candidates[#candidates + 1] = { area = area, lastUsedAt = record.lastUsedAt }
        end
    end

    table.sort(candidates, function(first, second)
        return first.lastUsedAt < second.lastUsedAt
    end)

    for index = 1, #candidates do
        if NPCNodes.loadedAreaCount <= Config.nodes.maxLoadedAreas then
            break
        end
        NPCNodes.unloadArea(candidates[index].area)
    end
end

-- Required public API. It never scans the full map: only currently indexed
-- streamed chunks are searched. Use NPCNodes.findNearestPedNode for loading.
function getNearestPedNode(x, y, z)
    return NPCNodes.getNearestPedNode(x, y, z)
end

addEventHandler("onClientFileDownloadComplete", root, function(fileName, success, requestResource)
    if source ~= resourceRoot then
        return
    end

    local pending = NPCNodes.pendingByPath[fileName]
    if not pending then
        return
    end

    if not success then
        finishPending(fileName, false, "MTA failed to download node chunk")
        return
    end

    local loaded, reason = parseDownloadedArea(pending.area, fileName)
    finishPending(fileName, loaded, reason)
end)

addEventHandler("onClientResourceStart", resourceRoot, function()
    NPCNodes.loadManifest()
end)
