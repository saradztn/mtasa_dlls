-- Royal Fortress server (remake) - MTA:SA compatible
local ROOT_RES = "client/data/world.json"
local f = fileOpen(ROOT_RES)
local raw = fileRead(f, fileGetSize(f)); fileClose(f)
local W = fromJSON(raw)

RFServer = {}
RFServer.world = W
RFServer.interactive = W.interactive
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

for _, meta in pairs(RFServer.interactive) do
    for _, part in ipairs(meta.parts or {}) do
        part.center = part.pos
    end
end

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

local function getPos(p)
    local x, y, z = getElementPosition(p)
    return x, y, z
end

local function nearPart(p, id)
    local rec = W.interactive[id]
    if not rec then return false end
    local px, py, pz = getPos(p)
    for _, part in ipairs(rec.parts) do
        local dx = px - part.pos[1]
        local dy = py - part.pos[2]
        local dz = pz - part.pos[3]
        if (dx*dx + dy*dy + dz*dz) <= 36 then return true end
    end
    return false
end

local function restoreOrigin(p)
    local o = RFServer.origins[p]
    local t = RFServer.pending[p]
    if (not o) and t and t.origin then o = t.origin end
    if o then
        setElementPosition(p, o.x, o.y, o.z)
        setElementDimension(p, o.dim)
        setElementInterior(p, o.int)
        setElementFrozen(p, false)
    end
    RFServer.pending[p] = nil
    RFServer.sessions[p] = nil
end

local function startTravel(p, targetKey, roomID)
    if not RFServer.ready[p] then return end
    if isPedDead(p) then return end
    if getPedOccupiedVehicle(p) then return end
    if RFServer.pending[p] then return end
    local now = getTickCount()
    if RFServer.lastTravel[p] and (now - RFServer.lastTravel[p]) < RFConfig.travelCooldown then return end

    local target
    if roomID then
        local r = RFServer.rooms[roomID]
        if not r or not r.spawn then
            -- try uppercase
            r = RFServer.rooms[string.upper(roomID)]
            if not r or not r.spawn then return end
        end
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
    local x, y, z = getPos(p)
    local origin = { x = x, y = y, z = z, dim = getElementDimension(p), int = getElementInterior(p) }
    RFServer.origins[p] = origin
    local token = newToken()
    RFServer.pending[p] = { token = token, target = target, origin = origin, committed = false, time = now }
    triggerClientEvent(p, "rf:prepare", resourceRoot, token, target.pos)
end

addEvent("rf:hello", true)
addEventHandler("rf:hello", resourceRoot, function(build)
    local p = client
    if build == RFConfig.build then
        RFServer.ready[p] = true
        triggerClientEvent(p, "rf:states", resourceRoot, statesList())
    end
end)

addEvent("rf:prepared", true)
addEventHandler("rf:prepared", resourceRoot, function(token)
    local p = client
    local t = RFServer.pending[p]
    if not t or t.token ~= token then return end
    if t.committed then return end
    t.committed = true
    setElementFrozen(p, true)
    local pos = t.target.pos
    setElementPosition(p, pos[1], pos[2], pos[3] + 1.0)
    setElementDimension(p, 779)
    setElementInterior(p, 0)
end)

addEvent("rf:groundReady", true)
addEventHandler("rf:groundReady", resourceRoot, function(token)
    local p = client
    local t = RFServer.pending[p]
    if not t or t.token ~= token then return end
    if not t.committed then return end
    setElementFrozen(p, false)
    RFServer.sessions[p] = true
    RFServer.pending[p] = nil
end)

addEvent("rf:loadFailed", true)
addEventHandler("rf:loadFailed", resourceRoot, function(token, reason)
    local p = client
    local t = RFServer.pending[p]
    if not t or t.token ~= token then return end
    if t.committed then return end
    restoreOrigin(p)
    triggerClientEvent(p, "rf:rollback", resourceRoot, token, reason or "")
end)

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

    if meta.acl then
        local right = "resource.royal_fortress." .. meta.acl
        if not hasObjectPermissionTo(p, right, false) then
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

    local newval = not RFServer.states[id]
    RFServer.states[id] = newval
    RFServer.movingUntil[id] = now + RFConfig.animTime
    triggerClientEvent(root, "rf:state", resourceRoot, id, newval, true)
end)

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
    if not hasObjectPermissionTo(p, "resource.royal_fortress.admin", false) then return end
    triggerClientEvent(p, "rf:debug", resourceRoot, true)
end)
addCommandHandler("castlereload", function(p)
    if not hasObjectPermissionTo(p, "resource.royal_fortress.admin", false) then return end
    for id, meta in pairs(RFServer.interactive) do
        if id == "drawbridge" then RFServer.states[id] = false
        else RFServer.states[id] = (meta.default == "open") end
    end
    triggerClientEvent(root, "rf:reload", resourceRoot, statesList())
end)

setTimer(function()
    for p, _ in pairs(RFServer.sessions) do
        if isElement(p) then
            local x, y, z = getElementPosition(p)
            if z < 2480 or z > 2600 then
                if not RFServer.pending[p] then
                    RFServer.lastTravel[p] = nil
                    startTravel(p, "gate")
                end
            end
        end
    end
end, 2000, 0)

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

setTimer(function()
    local now = getTickCount()
    for p, t in pairs(RFServer.pending) do
        if t.committed and (now - t.time) >= RFConfig.transactionTimeout then
            restoreOrigin(p)
            triggerClientEvent(p, "rf:rollback", resourceRoot, t.token, "timeout")
        end
    end
end, 1000, 0)
