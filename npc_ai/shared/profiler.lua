-- ============================================================================
-- GTA SA REAL NODE NPC AI
-- Author: AI Agent
-- Module: RUNTIME PROFILER
-- ============================================================================

NPCProfiler = NPCProfiler or {
    current = {},
    counts = {},
    last = {},
    windowStartedAt = 0,
    windowMs = 1000,
}

function NPCProfiler.configure(windowMs)
    NPCProfiler.windowMs = windowMs or NPCProfiler.windowMs
    NPCProfiler.windowStartedAt = NPCUtil.now()
end

function NPCProfiler.begin(name)
    return {
        name = name,
        startedAt = NPCUtil.now(),
    }
end

function NPCProfiler.finish(token)
    if not token then
        return 0
    end

    local elapsed = math.max(0, NPCUtil.now() - token.startedAt)
    NPCProfiler.current[token.name] = (NPCProfiler.current[token.name] or 0) + elapsed
    NPCProfiler.counts[token.name] = (NPCProfiler.counts[token.name] or 0) + 1
    return elapsed
end

function NPCProfiler.add(name, elapsedMs)
    if type(elapsedMs) ~= "number" then
        return
    end
    NPCProfiler.current[name] = (NPCProfiler.current[name] or 0) + math.max(0, elapsedMs)
    NPCProfiler.counts[name] = (NPCProfiler.counts[name] or 0) + 1
end

function NPCProfiler.rollWindow(now)
    now = now or NPCUtil.now()
    if NPCProfiler.windowStartedAt == 0 then
        NPCProfiler.windowStartedAt = now
        return false
    end

    local elapsed = now - NPCProfiler.windowStartedAt
    if elapsed < NPCProfiler.windowMs then
        return false
    end

    NPCProfiler.last = {
        elapsedMs = elapsed,
        timings = NPCProfiler.current,
        counts = NPCProfiler.counts,
    }
    NPCProfiler.current = {}
    NPCProfiler.counts = {}
    NPCProfiler.windowStartedAt = now
    return true
end

function NPCProfiler.getLast(name)
    local timing = NPCProfiler.last.timings and NPCProfiler.last.timings[name] or 0
    local count = NPCProfiler.last.counts and NPCProfiler.last.counts[name] or 0
    return timing or 0, count or 0, NPCProfiler.last.elapsedMs or 0
end

function NPCProfiler.getSnapshot()
    return NPCProfiler.last
end
