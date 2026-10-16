-- Royal Fortress server (remake)
local ROOT_RES = "client/data/world.json"
local f = fileOpen(ROOT_RES)
local raw = fileRead(f, fileGetSize(f)); fileClose(f)
local W = fromJSON(raw)

RFServer = {}
RFServer.world = W
RFServer.interactive = W.interactive
for _, meta in pairs(RFServer.interactive) do
    for _, part in ipairs(meta.parts or {}) do
        part.center = part.pos
    end
end
RFServer.rooms = W.rooms
RFServer.teleports = W.teleports
RFServer.states = {}
RFServer.pending = {}
RFServer.ready = {}
RFServer.sessions = {}
RFServer.origins = {}
RFServer.lastTravel = {}
RFServer.movingUntil = {}
RFServer.tokenCounter = 0

-- default states
for id, meta in pairs(RFServer.interactive) do
    if id == "drawbridge" then
        RFServer.states[id] = false
    else
        RFServer.states[id] = (meta.default == "open")
    end
end

local function statesList()
    local out = {}
    for id, v in pairs(RFServer.states) do
        out[#out+1] = {id, v}
    end
    return out
end

local function newToken()
    RFServer.tokenCounter = RFServer.tokenCounter + 1
    return "tok" .. RFServer.tokenCounter
end

local function nearPart(p, id)
    local rec = W.interactive[id]
    if not rec then return false end
    for _, part in ipairs(rec.parts) do
        local dx = p.x - part.pos[1]
        local dy = p.y - part.pos[2]
        local dz = p.z - part.pos[3]
        if (dx*dx + dy*dy + dz*dz) <= 36 then return true end
    end
    return false
end

local function restoreOrigin(p)
    local t = RFServer.pending[p]
    local o = RFServer.origins[p]
    if (not o) and t and t.origin then o = t.origin end
    if o then
        setElementPosition(p, o.x, o.y, o.z)
        setElementDimension(p, o.dim)
        setElementInterior(p, o.int)
        p.frozen = false
    end
    RFServer.pending[p] = nil
    RFServer.sessions[p] = nil
end

local function startTravel(p, targetKey, roomID)
    if not RFServer.ready[p] then return end
    if p.dead then return end
    if p.vehicle then return end
    if RFServer.pending[p] then return end
    local now = getTickCount()
    if RFServer.lastTravel[p] and (now - RFServer.lastTravel[p]) < RFConfig.travelCooldown then return end

    local target
    if roomID then
        local r = RFServer.rooms[roomID]
        if not r or not r.spawn then return end
        if r.acl then
            local right = "resource.royal_fortress." .. r.acl
            if not hasObjectPermissionTo(p, right, false) then return end
        end
        target = { pos = r.spawn, label = r.name }
    else
        target = RFServer.teleports[targetKey]
        if not target then return end
    end

    RFServer.lastTravel[p] = now
    RFServer.origins[p] = { x = p.x, y = p.y, z = p.z, dim = p.dim, int = p.int }
    local token = newToken()
    RFServer.pending[p] = { token = token, target = target, origin = RFServer.origins[p], committed = false, time = now }
    triggerClientEvent(p, "rf:prepare", resourceRoot, token, target.pos)
end

-- hello
addEvent("rf:hello", true)
addEventHandler("rf:hello", resourceRoot, function(build)
    local p = client
    if build == RFConfig.build then
        RFServer.ready[p] = true
        triggerClientEvent(p, "rf:states", resourceRoot, statesList())
    end
end)

-- prepared
addEvent("rf:prepared", true)
addEventHandler("rf:prepared", resourceRoot, function(token)
    local p = client
    local t = RFServer.pending[p]
    if not t or t.token ~= token then return end
    if t.committed then return end
    t.committed = true
    p.frozen = true
    local pos = t.target.pos
    setElementPosition(p, pos[1], pos[2], pos[3] + 1.0)
    setElementDimension(p, 779)
    setElementInterior(p, 0)
    triggerClientEvent(p, "rf:committed", resourceRoot, token, pos) -- optional
end)

-- groundReady
addEvent("rf:groundReady", true)
addEventHandler("rf:groundReady", resourceRoot, function(token)
    local p = client
    local t = RFServer.pending[p]
    if not t or t.token ~= token then return end
    if not t.committed then return end
    p.frozen = false
    RFServer.sessions[p] = true
    RFServer.pending[p] = nil
end)

-- loadFailed
addEvent("rf:loadFailed", true)
addEventHandler("rf:loadFailed", resourceRoot, function(token, reason)
    local p = client
    local t = RFServer.pending[p]
    if not t or t.token ~= token then return end
    if t.committed then return end
    restoreOrigin(p)
    triggerClientEvent(p, "rf:rollback", resourceRoot, token, reason or "")
end)

-- interact
addEvent("rf:interact", true)
addEventHandler("rf:interact", resourceRoot, function(id)
    local p = client
    if not RFServer.sessions[p] then return end
    if type(id) ~= "string" or #id > 64 then return end
    local meta = RFServer.interactive[id]
    if not meta then return end
    if not meta.operable then return end
    if not nearPart(p, id) then return end
    local now = getTickCount()
    if RFServer.movingUntil[id] and now < RFServer.movingUntil[id] then return end

    -- ACL
    if meta.acl then
        local right = "resource.royal_fortress." .. meta.acl
        if not hasObjectPermissionTo(p, right, false) then
            -- locked: no change
            return
        end
    end

    if id == "book_lever" then
        RFServer.states["library_bookcase"] = true
        RFServer.states["book_lever"] = true
        RFServer.movingUntil["book_lever"] = now + RFConfig.animTime
        triggerClientEvent(root, "rf:state", resourceRoot, "library_bookcase", true, true)
        triggerClientEvent(root, "rf:state", resourceRoot, "book_lever", true, true)
        setTimer(function()
            RFServer.states["book_lever"] = false
            triggerClientEvent(root, "rf:state", resourceRoot, "book_lever", false, true)
        end, RFConfig.animTime, 1)
        return
    end

    -- toggle
    local newval = not RFServer.states[id]
    -- special gate mechanisms require rights already checked above
    RFServer.states[id] = newval
    RFServer.movingUntil[id] = now + RFConfig.animTime
    triggerClientEvent(root, "rf:state", resourceRoot, id, newval, true)
end)

-- commands
addCommandHandler("castle", function(p) startTravel(p, "gate") end)
addCommandHandler("castleinterior", function(p) startTravel(p, "interior") end)
addCommandHandler("showp", function(p) startTravel(p, "showp") end)
addCommandHandler("castleroom", function(p, cmd, rid)
    if not rid then return end
    local key = rid
    if not RFServer.rooms[key] and RFServer.rooms[string.upper(rid)] then key = string.upper(rid) end
    startTravel(p, nil, key)
end)
addCommandHandler("castleleave", function(p)
    if not RFServer.sessions[p] then return end
    restoreOrigin(p)
    triggerClientEvent(p, "rf:leave", resourceRoot)
end)
addCommandHandler("castledoor", function(p, cmd, id)
    if not id or not RFServer.interactive[id] then return end
    local newval = not RFServer.states[id]
    RFServer.states[id] = newval
    RFServer.movingUntil[id] = getTickCount() + RFConfig.animTime
    triggerClientEvent(root, "rf:state", resourceRoot, id, newval, true)
end)
addCommandHandler("castledebug", function(p)
    if not p.admin then return end
    triggerClientEvent(p, "rf:debug", resourceRoot, true)
end)
addCommandHandler("castlereload", function(p)
    if not p.admin then return end
    -- reset states
    for id, meta in pairs(RFServer.interactive) do
        if id == "drawbridge" then RFServer.states[id] = false
        else RFServer.states[id] = (meta.default == "open") end
    end
    triggerClientEvent(root, "rf:reload", resourceRoot, statesList())
end)

-- void watchdog
setTimer(function()
    for p, _ in pairs(RFServer.sessions) do
        if isElement(p) then
            local z = p.z
            if z < 2480 or z > 2600 then
                if not RFServer.pending[p] then
                    RFServer.lastTravel[p] = nil
                    startTravel(p, "gate")
                end
            end
        end
    end
end, 2000, 0)

-- cleanup
addEventHandler("onPlayerWasted", root, function()
    local p = source
    restoreOrigin(p)
end)
addEventHandler("onPlayerQuit", root, function()
    local p = source
    RFServer.pending[p] = nil
    RFServer.ready[p] = nil
    RFServer.sessions[p] = nil
    RFServer.origins[p] = nil
end)
addEventHandler("onResourceStop", root, function()
    for p, _ in pairs(RFServer.sessions) do
        restoreOrigin(p)
    end
end)

-- transaction timeout
setTimer(function()
    local now = getTickCount()
    for p, t in pairs(RFServer.pending) do
        if t.committed and (now - t.time) >= RFConfig.transactionTimeout then
            restoreOrigin(p)
            triggerClientEvent(p, "rf:rollback", resourceRoot, t.token, "timeout")
        end
    end
end, 1000, 0)
