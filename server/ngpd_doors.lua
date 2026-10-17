--[[
  NextGenPoliceDepartment - server authoritative door system.

  Every door from NGPD_DATA.doors gets
    * one server object per leaf (placeholder model 1337; element data "ngpd.model" tells clients which
      locally allocated custom model to show - engineRequestModel IDs differ per client),
    * one custom element "ngpd_door" (id "ngpd_door_<id>") carrying the synced state for UI:
        ngpd.state  = "closed" | "opening" | "open" | "closing"
        ngpd.locked = boolean
  Leaves are animated with moveObject (synced/interpolated by MTA for every client).

  Request flow (client presses E -> "ngpd:doorRequest"):
    validated here: real client == source player, door exists, alive, same int/dim, distance to door
    centre, vehicle rules, per-player cooldown, per-door cooldown, not mid-transition, lock, access group.
  The client-side prompt is cosmetic only; nothing on the client can open a door by itself.
]]

local CFG = NGPD_CONFIG.doors
local doors = {}            -- id -> runtime record
local playerCooldown = {}   -- player -> tick

local function now() return getTickCount() end

------------------------------------------------------------------ geometry
local function leafClosedPose(leaf)
    local x, y, z = NGPD.toWorld(leaf.x, leaf.y, leaf.z)
    return x, y, z, 0, 0, NGPD.toWorldRot(leaf.rz)
end

-- target pose of a leaf in the open state (absolute)
local function leafOpenPose(leaf)
    local x, y, z, rx, ry, rz = leafClosedPose(leaf)
    local o = leaf.open
    if o.type == "rot" then
        rz = rz + (o.drz or 90)
    elseif o.type == "move" then
        local a = math.rad(NGPD.origin.rz)
        local c, s = math.cos(a), math.sin(a)
        local dx, dy = o.dx or 0, o.dy or 0
        x, y, z = x + dx * c - dy * s, y + dx * s + dy * c, z + (o.dz or 0)
    elseif o.type == "tilt" then
        rx = rx + (o.drx or 88)
        z = z + (o.dz or 0)
    elseif o.type == "pivot" then
        ry = ry + (o.dry or -85)
    end
    return x, y, z, rx, ry, rz
end

local function durationFor(door)
    if door.kind == "gate" or door.kind == "rollup" then return CFG.gateOpenMs end
    if door.kind == "barrier" then return 2200 end
    return CFG.defaultOpenMs
end

------------------------------------------------------------------ state
local function setState(rec, state)
    rec.state = state
    if isElement(rec.element) then setElementData(rec.element, "ngpd.state", state) end
end

local function killTimer_(t) if t and isTimer(t) then killTimer(t) end end

local function animate(rec, toOpen)
    local ms = durationFor(rec.def)
    for i, obj in ipairs(rec.objects) do
        if isElement(obj) then
            local leaf = rec.def.leaves[i]
            local cx, cy, cz, crx, cry, crz = leafClosedPose(leaf)
            local ox, oy, oz, orx, ory, orz = leafOpenPose(leaf)
            -- moveObject rotation arguments are RELATIVE offsets
            if toOpen then
                setElementPosition(obj, cx, cy, cz)
                setElementRotation(obj, crx, cry, crz)
                moveObject(obj, ms, ox, oy, oz, orx - crx, ory - cry, orz - crz, CFG.easing)
            else
                setElementPosition(obj, ox, oy, oz)
                setElementRotation(obj, orx, ory, orz)
                moveObject(obj, ms, cx, cy, cz, crx - orx, cry - ory, crz - orz, CFG.easing)
            end
        end
    end
    return ms
end

local function snap(rec, open)
    for i, obj in ipairs(rec.objects) do
        if isElement(obj) then
            stopObject(obj)
            local x, y, z, rx, ry, rz
            if open then x, y, z, rx, ry, rz = leafOpenPose(rec.def.leaves[i]) else x, y, z, rx, ry, rz = leafClosedPose(rec.def.leaves[i]) end
            setElementPosition(obj, x, y, z)
            setElementRotation(obj, rx, ry, rz)
        end
    end
end

local closeDoor

local function openDoor(rec, byPlayer)
    if rec.state ~= "closed" then return false, "busy" end
    killTimer_(rec.autoTimer)
    setState(rec, "opening")
    local ms = animate(rec, true)
    rec.transTimer = setTimer(function()
        rec.transTimer = nil
        snap(rec, true)
        setState(rec, "open")
        rec.readyAt = now() + CFG.doorCooldownMs
        local ac = CFG.autoCloseMs[rec.def.kind]
        if ac and ac > 0 then
            rec.autoTimer = setTimer(function() rec.autoTimer = nil; closeDoor(rec) end, ac, 1)
        end
    end, ms + 50, 1)
    rec.lastBy = byPlayer and getPlayerName(byPlayer) or "system"
    return true
end

closeDoor = function(rec, byPlayer)
    if rec.state ~= "open" then return false, "busy" end
    killTimer_(rec.autoTimer)
    rec.autoTimer = nil
    setState(rec, "closing")
    local ms = animate(rec, false)
    rec.transTimer = setTimer(function()
        rec.transTimer = nil
        snap(rec, false)
        setState(rec, "closed")
        rec.readyAt = now() + CFG.doorCooldownMs
    end, ms + 50, 1)
    rec.lastBy = byPlayer and getPlayerName(byPlayer) or "system"
    return true
end

local function setLocked(rec, locked)
    rec.locked = locked and true or false
    if isElement(rec.element) then setElementData(rec.element, "ngpd.locked", rec.locked) end
end

------------------------------------------------------------------ build / teardown
local function destroyDoors()
    for _, rec in pairs(doors) do
        killTimer_(rec.transTimer)
        killTimer_(rec.autoTimer)
        for _, obj in ipairs(rec.objects) do if isElement(obj) then destroyElement(obj) end end
        if isElement(rec.element) then destroyElement(rec.element) end
    end
    doors = {}
end

function NGPD.buildDoors()
    destroyDoors()
    for _, d in ipairs(NGPD_DATA.doors) do
        local rec = { def = d, objects = {}, state = "closed", locked = false, readyAt = 0 }
        rec.element = createElement("ngpd_door", "ngpd_door_" .. d.id)
        setElementData(rec.element, "ngpd.id", d.id)
        setElementData(rec.element, "ngpd.state", "closed")
        setElementData(rec.element, "ngpd.locked", false)
        for i, leaf in ipairs(d.leaves) do
            local x, y, z, rx, ry, rz = leafClosedPose(leaf)
            local obj = createObject(1337, x, y, z, rx, ry, rz)
            if obj then
                setElementInterior(obj, NGPD_CONFIG.interior)
                setElementDimension(obj, NGPD_CONFIG.dimension)
                setElementFrozen(obj, true)
                setElementData(obj, "ngpd.model", leaf.model)
                setElementData(obj, "ngpd.door", d.id)
                setElementParent(obj, rec.element)
                rec.objects[i] = obj
            else
                outputDebugString("[NGPD] createObject failed for door " .. d.id, 1)
            end
        end
        -- detention cells / security doors start locked? No: closed & unlocked; staff lock them explicitly.
        doors[d.id] = rec
    end
end

-- relocation: rebuild with the new transform but keep lock flags
function NGPD.rebuildDoors()
    local locks = {}
    for id, rec in pairs(doors) do locks[id] = rec.locked end
    NGPD.buildDoors()
    for id, l in pairs(locks) do if doors[id] then setLocked(doors[id], l) end end
end

function NGPD.doorStats()
    local s = { open = 0, moving = 0, locked = 0 }
    for _, rec in pairs(doors) do
        if rec.state == "open" then s.open = s.open + 1 elseif rec.state ~= "closed" then s.moving = s.moving + 1 end
        if rec.locked then s.locked = s.locked + 1 end
    end
    return s
end

------------------------------------------------------------------ request validation
local DENY = {
    far = "You are too far from the door.",
    cooldown = "Wait a moment.",
    busy = "The door is moving.",
    locked = "The door is locked.",
    access = "Access denied: %s clearance required.",
    vehicle = "Get out of the vehicle first.",
    dead = "",
}

local function validate(player, rec)
    if isPedDead(player) then return false, "dead" end
    local t = now()
    if (playerCooldown[player] or 0) > t then return false, "cooldown" end
    if rec.state == "opening" or rec.state == "closing" or rec.readyAt > t then return false, "busy" end
    if getElementInterior(player) ~= NGPD_CONFIG.interior or getElementDimension(player) ~= NGPD_CONFIG.dimension then return false, "far" end
    local px, py, pz = getElementPosition(player)
    local cx, cy, cz = NGPD.doorCentre(rec.def)
    local radius = CFG.interactRadius + (rec.def.w or 1) * 0.5
    if isPedInVehicle(player) then
        if not CFG.vehicleKinds[rec.def.kind] then return false, "vehicle" end
        radius = CFG.vehicleRadius + (rec.def.w or 1) * 0.5
    end
    if NGPD.dist3(px, py, pz, cx, cy, cz) > radius then return false, "far" end
    if rec.locked then return false, "locked" end
    if not NGPD.hasAccess(player, rec.def.access) then return false, "access" end
    return true
end

addEvent("ngpd:doorRequest", true)
addEventHandler("ngpd:doorRequest", resourceRoot, function(doorId)
    local player = client
    if not player or type(doorId) ~= "string" then return end
    local rec = doors[doorId]
    if not rec then return end
    local ok, why = validate(player, rec)
    playerCooldown[player] = now() + CFG.cooldownMs
    if not ok then
        local msg = DENY[why] or why
        if why == "access" then msg = string.format(msg, rec.def.access) end
        if msg ~= "" then NGPD.notify(player, msg, "error") end
        return
    end
    if rec.state == "closed" then openDoor(rec, player) else closeDoor(rec, player) end
end)

addEventHandler("onPlayerQuit", root, function() playerCooldown[source] = nil end)

------------------------------------------------------------------ admin / staff commands
local function staff(player, group)
    return (not isElement(player)) or getElementType(player) == "console" or NGPD.hasAccess(player, group)
end

local function nearestDoor(player, maxDist)
    local px, py, pz = getElementPosition(player)
    local best, bd = nil, maxDist or 6
    for _, rec in pairs(doors) do
        local cx, cy, cz = NGPD.doorCentre(rec.def)
        local dd = NGPD.dist3(px, py, pz, cx, cy, cz)
        if dd < bd then best, bd = rec, dd end
    end
    return best
end

local function resolve(player, id)
    if id and doors[id] then return doors[id] end
    if isElement(player) and getElementType(player) == "player" then return nearestDoor(player, 6) end
    return nil
end

-- /ngpd_lock [doorId]   /ngpd_unlock [doorId]  - nearest door when no id is given
local function lockCmd(lock)
    return function(player, _, id)
        local rec = resolve(player, id)
        if not rec then return NGPD.notify(player, "No door found (stand near one or give an id).", "error") end
        local need = (rec.def.access == "public") and "police" or rec.def.access
        if not staff(player, need) then return NGPD.notify(player, "Access denied.", "error") end
        if lock and rec.state ~= "closed" then
            -- close first, lock once closed
            if rec.state == "open" then closeDoor(rec, player) end
            setTimer(function() if rec.state == "closed" then setLocked(rec, true) end end, durationFor(rec.def) + 200, 1)
            return NGPD.notify(player, "Door " .. rec.def.id .. " closing and locking.", "ok")
        end
        setLocked(rec, lock)
        NGPD.notify(player, "Door " .. rec.def.id .. (lock and " locked." or " unlocked."), "ok")
    end
end
addCommandHandler("ngpd_lock", lockCmd(true))
addCommandHandler("ngpd_unlock", lockCmd(false))

-- /ngpd_door <id> open|close  (admin, ignores distance but not transition state)
addCommandHandler("ngpd_door", function(player, _, id, action)
    if not staff(player, NGPD_CONFIG.adminGroup) then return NGPD.notify(player, "Access denied.", "error") end
    local rec = doors[id or ""]
    if not rec then return NGPD.notify(player, "Usage: /ngpd_door <doorId> open|close", "error") end
    local ok, why
    if action == "open" then ok, why = openDoor(rec, player) else ok, why = closeDoor(rec, player) end
    NGPD.notify(player, ok and ("Door " .. id .. " " .. (action == "open" and "opening" or "closing")) or ("Door is " .. rec.state), ok and "ok" or "error")
end)

-- /ngpd_lockdown [on|off]  detention wing: close + lock (or unlock) every detention door
addCommandHandler("ngpd_lockdown", function(player, _, mode)
    if not staff(player, "detention") then return NGPD.notify(player, "Access denied.", "error") end
    local on = mode ~= "off"
    local n = 0
    for _, rec in pairs(doors) do
        if rec.def.access == "detention" then
            n = n + 1
            if on then
                if rec.state == "open" then closeDoor(rec, player) end
                local r = rec
                setTimer(function() if r.state == "closed" then setLocked(r, true) end end, durationFor(r.def) + 300, 1)
            else
                setLocked(rec, false)
            end
        end
    end
    local msg = string.format("Detention lockdown %s (%d doors).", on and "ON" or "OFF", n)
    for _, p in ipairs(getElementsByType("player")) do
        if NGPD.hasAccess(p, "detention") then NGPD.notify(p, msg, "warn") end
    end
    if not isElement(player) then outputServerLog("[NGPD] " .. msg) end
end)

-- /ngpd_doors : list doors within 15 m with state
addCommandHandler("ngpd_doors", function(player)
    if not isElement(player) or getElementType(player) ~= "player" then
        for id, rec in pairs(doors) do outputServerLog(string.format("[NGPD] %s %s %s %s", id, rec.def.kind, rec.state, rec.locked and "LOCKED" or "")) end
        return
    end
    local px, py, pz = getElementPosition(player)
    for id, rec in pairs(doors) do
        local cx, cy, cz = NGPD.doorCentre(rec.def)
        local dd = NGPD.dist3(px, py, pz, cx, cy, cz)
        if dd < 15 then
            outputChatBox(string.format("[NGPD] %s (%s, %s) %s%s - %.1fm", id, rec.def.kind, rec.def.access, rec.state, rec.locked and " LOCKED" or "", dd), player, 150, 200, 255)
        end
    end
end)

------------------------------------------------------------------ cleanup
addEventHandler("onResourceStop", resourceRoot, function()
    destroyDoors()
    playerCooldown = {}
end)

-- exported for other resources (e.g. a jail script): exports.NextGenPoliceDepartment:ngpdSetDoorLocked("door_12", true)
function ngpdSetDoorLocked(id, locked)
    local rec = doors[id]
    if not rec then return false end
    if locked and rec.state ~= "closed" then return false end
    setLocked(rec, locked)
    return true
end

function ngpdGetDoorState(id)
    local rec = doors[id]
    if not rec then return false end
    return rec.state, rec.locked
end

function ngpdOpenDoor(id)
    local rec = doors[id]
    return rec and openDoor(rec, nil) or false
end

function ngpdCloseDoor(id)
    local rec = doors[id]
    return rec and closeDoor(rec, nil) or false
end
