-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: LOGGER
-- ============================================================================

NPCAILog = NPCAILog or {
    lastMessageAt = {},
}

local function write(level, channel, message)
    if not Config.logging.enabled then
        return
    end

    local prefix = string.format("[NPC-AI][%s][%s] ", level, channel or "CORE")
    local debugLevel = 3
    if level == "WARNING" then
        debugLevel = 2
    elseif level == "ERROR" then
        debugLevel = 1
    end

    outputDebugString(prefix .. tostring(message), debugLevel)
end

function NPCAILog.info(channel, message)
    write("INFO", channel, message)
end

function NPCAILog.warning(channel, message)
    write("WARNING", channel, message)
end

function NPCAILog.error(channel, message)
    write("ERROR", channel, message)
end

function NPCAILog.debug(channel, message)
    if Config.logging.debug then
        write("DEBUG", channel, message)
    end
end

function NPCAILog.rateLimited(key, level, channel, message, intervalMs)
    local now = NPCUtil.now()
    local previous = NPCAILog.lastMessageAt[key] or 0
    intervalMs = intervalMs or Config.logging.rateLimitMs
    if now - previous < intervalMs then
        return false
    end

    NPCAILog.lastMessageAt[key] = now
    if level == "ERROR" then
        NPCAILog.error(channel, message)
    elseif level == "WARNING" then
        NPCAILog.warning(channel, message)
    elseif level == "DEBUG" then
        NPCAILog.debug(channel, message)
    else
        NPCAILog.info(channel, message)
    end
    return true
end
