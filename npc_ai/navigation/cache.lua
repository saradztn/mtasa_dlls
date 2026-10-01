-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: PATH CACHE
-- ============================================================================

NPCPathCache = NPCPathCache or {
    entries = {},
    size = 0,
}

local function makeKey(startId, goalId)
    return tostring(startId) .. ":" .. tostring(goalId)
end

local function clonePath(path)
    return NPCUtil.copyArray(path)
end

function NPCPathCache.get(startId, goalId)
    local key = makeKey(startId, goalId)
    local entry = NPCPathCache.entries[key]
    if not entry then
        return nil
    end

    local now = NPCUtil.now()
    if entry.expiresAt <= now then
        NPCPathCache.entries[key] = nil
        NPCPathCache.size = math.max(0, NPCPathCache.size - 1)
        return nil
    end

    entry.lastUsedAt = now
    return clonePath(entry.path)
end

function NPCPathCache.put(startId, goalId, path)
    if type(path) ~= "table" or #path == 0 then
        return false
    end

    local key = makeKey(startId, goalId)
    local now = NPCUtil.now()
    if not NPCPathCache.entries[key] then
        NPCPathCache.size = NPCPathCache.size + 1
    end

    NPCPathCache.entries[key] = {
        path = clonePath(path),
        createdAt = now,
        lastUsedAt = now,
        expiresAt = now + Config.pathfinding.cacheTtlMs,
    }

    NPCPathCache.prune()
    return true
end

function NPCPathCache.prune()
    local now = NPCUtil.now()
    for key, entry in pairs(NPCPathCache.entries) do
        if entry.expiresAt <= now then
            NPCPathCache.entries[key] = nil
            NPCPathCache.size = math.max(0, NPCPathCache.size - 1)
        end
    end

    while NPCPathCache.size > Config.pathfinding.cacheMaxEntries do
        local oldestKey
        local oldestTime = math.huge
        for key, entry in pairs(NPCPathCache.entries) do
            if entry.lastUsedAt < oldestTime then
                oldestTime = entry.lastUsedAt
                oldestKey = key
            end
        end

        if not oldestKey then
            break
        end
        NPCPathCache.entries[oldestKey] = nil
        NPCPathCache.size = NPCPathCache.size - 1
    end
end

function NPCPathCache.clear()
    NPCPathCache.entries = {}
    NPCPathCache.size = 0
end
