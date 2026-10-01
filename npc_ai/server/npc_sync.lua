-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: PED OWNERSHIP AND SYNCHRONIZATION
-- ============================================================================

local function findBestOwner(record)
    if not isElement(record.ped) then
        return nil
    end

    local pedX, pedY, pedZ = getElementPosition(record.ped)
    local pedInterior = getElementInterior(record.ped)
    local pedDimension = getElementDimension(record.ped)
    local bestPlayer
    local bestDistance = Config.networking.ownerDistance

    for _, player in ipairs(getElementsByType("player")) do
        if getElementInterior(player) == pedInterior and getElementDimension(player) == pedDimension then
            local playerX, playerY, playerZ = getElementPosition(player)
            local distance = NPCUtil.distance3D(pedX, pedY, pedZ, playerX, playerY, playerZ)
            if distance <= bestDistance then
                bestDistance = distance
                bestPlayer = player
            end
        end
    end
    return bestPlayer
end

local function setOwner(record, owner)
    if not isElement(record.ped) then
        return
    end

    local actual = getElementSyncer(record.ped)
    if record.owner == owner and actual == owner then
        return
    end

    local success = setElementSyncer(record.ped, owner or false, Config.networking.persistSyncer)
    if not success then
        NPCAILog.warning("SYNC", "Could not assign syncer for NPC " .. tostring(record.id))
        return
    end

    record.owner = owner
    if owner then
        NPCAILog.debug("SYNC", "NPC " .. record.id .. " owner assigned")
        NPCManager.publishTask(record, owner)
    else
        NPCAILog.debug("SYNC", "NPC " .. record.id .. " has no nearby owner")
    end
end

local function refreshOwners()
    for _, record in pairs(NPCManager.recordsByPed) do
        if isElement(record.ped) then
            setOwner(record, findBestOwner(record))
        end
    end
end

addEventHandler("onResourceStart", resourceRoot, function()
    setTimer(refreshOwners, Config.networking.ownerUpdateMs, 0)
    refreshOwners()
end)

addEventHandler("onPlayerQuit", root, function()
    for _, record in pairs(NPCManager.recordsByPed) do
        if record.owner == source then
            record.owner = nil
            if isElement(record.ped) then
                setElementSyncer(record.ped, false, Config.networking.persistSyncer)
            end
        end
    end
end)

addEventHandler("onElementDestroy", root, function()
    local record = NPCManager.recordsByPed[source]
    if record then
        NPCManager.recordsByPed[source] = nil
        NPCManager.recordsById[record.id] = nil
        NPCAILog.warning("SYNC", "Managed NPC " .. record.id .. " was destroyed externally")
    end
end)
