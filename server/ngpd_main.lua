--[[
  NextGenPoliceDepartment - server core
    * world origin (persisted in resource settings, broadcast to clients)
    * access-group checks (ACL group / team / element data) used by doors, elevators and commands
    * decorative police vehicles (frozen, locked, damage proof)
    * admin commands: /ngpd_status /ngpd_relocate /ngpd_setorigin /ngpd_resetorigin /ngpd_tp
]]

local RES_NAME = getResourceName(getThisResource())
NGPD.server = { vehicles = {}, readyClients = {} }

------------------------------------------------------------------ settings
local function loadOrigin()
    local s = get("origin")                         -- "x,y,z,rz" in meta.xml <settings> / settings.xml
    if type(s) == "string" and s ~= "" then
        local x, y, z, rz = s:match("^%s*([%-%d%.]+)%s*,%s*([%-%d%.]+)%s*,%s*([%-%d%.]+)%s*,?%s*([%-%d%.]*)%s*$")
        if x then
            NGPD.setOrigin(tonumber(x), tonumber(y), tonumber(z), tonumber(rz) or 0)
            return true
        end
        outputDebugString("[NGPD] invalid 'origin' setting '" .. s .. "', using default", 2)
    end
    local o = NGPD_CONFIG.origin
    NGPD.setOrigin(o.x, o.y, o.z, o.rz)
    return false
end

local function saveOrigin()
    local o = NGPD.origin
    local ok = set("origin", string.format("%.3f,%.3f,%.3f,%.2f", o.x, o.y, o.z, o.rz))
    if not ok then
        outputDebugString("[NGPD] could not persist origin (resource needs settings write access); it will reset on restart", 2)
    end
    return ok
end

------------------------------------------------------------------ access
local function inAclGroup(player, groupName)
    local account = getPlayerAccount(player)
    if not account or isGuestAccount(account) then return false end
    local group = aclGetGroup(groupName)
    if not group then return false end
    return isObjectInACLGroup("user." .. getAccountName(account), group)
end

-- returns true when the player satisfies the named access group
function NGPD.hasAccess(player, groupName)
    if not isElement(player) then return false end
    local name = NGPD_CONFIG.accessAliases[groupName] or groupName
    local rule = NGPD_CONFIG.access[name]
    if not rule then return false end
    if rule.open then return true end
    if name ~= NGPD_CONFIG.adminGroup and NGPD.hasAccess(player, NGPD_CONFIG.adminGroup) then return true end
    for _, g in ipairs(rule.acl or {}) do
        if inAclGroup(player, g) then return true end
    end
    local team = getPlayerTeam(player)
    if team then
        local tn = getTeamName(team)
        for _, t in ipairs(rule.teams or {}) do
            if tn == t then return true end
        end
    end
    for _, key in ipairs(rule.data or {}) do
        if getElementData(player, key) then return true end
    end
    return false
end

local function isAdmin(player)
    return player == nil or getElementType(player) == "console" or NGPD.hasAccess(player, NGPD_CONFIG.adminGroup)
end

function NGPD.notify(player, msg, kind)
    if isElement(player) and getElementType(player) == "player" then
        if NGPD.server.readyClients[player] then
            triggerClientEvent(player, "ngpd:notice", resourceRoot, msg, kind or "info")
        else
            -- client scripts not running yet (still downloading / failed): plain chat, no client event
            local c = kind == "error" and { 255, 110, 110 } or kind == "ok" and { 130, 255, 160 } or { 220, 230, 255 }
            outputChatBox("[NGPD] " .. msg, player, c[1], c[2], c[3])
        end
    else
        outputServerLog("[NGPD] " .. msg)
    end
end

------------------------------------------------------------------ decorative vehicles
local function destroyVehicles()
    for _, v in ipairs(NGPD.server.vehicles) do
        if isElement(v) then destroyElement(v) end
    end
    NGPD.server.vehicles = {}
end

local function spawnVehicles()
    destroyVehicles()
    if not NGPD_CONFIG.spawnVehicles then return end
    local list = {}
    for _, v in ipairs(NGPD_DATA.vehicles) do list[#list + 1] = { v.model, v.x, v.y, v.z, v.rz } end
    for _, a in ipairs(NGPD_DATA.anchors.garage_cars or {}) do list[#list + 1] = { 596, a[1], a[2], a[3], a[4] } end
    for i, a in ipairs(NGPD_DATA.anchors.yard_cars or {}) do list[#list + 1] = { (i == 2) and 427 or 599, a[1], a[2], a[3], a[4] } end
    for i, v in ipairs(list) do
        local x, y, z = NGPD.toWorld(v[2], v[3], v[4])
        local veh = createVehicle(v[1], x, y, z + 1.0, 0, 0, NGPD.toWorldRot(v[5]), string.format("NGPD%03d", i))
        if veh then
            setElementInterior(veh, NGPD_CONFIG.interior)
            setElementDimension(veh, NGPD_CONFIG.dimension)
            setVehicleLocked(veh, true)
            setVehicleDamageProof(veh, true)
            setVehicleEngineState(veh, false)
            setVehicleOverrideLights(veh, 1)
            setElementData(veh, "ngpd.decorative", true)
            -- let the car settle onto the parking surface, then freeze it
            setTimer(function() if isElement(veh) then setElementFrozen(veh, true) end end, 3000, 1)
            NGPD.server.vehicles[#NGPD.server.vehicles + 1] = veh
        else
            outputDebugString("[NGPD] createVehicle failed for model " .. tostring(v[1]), 2)
        end
    end
end

-- nobody may drive the decorative cars (they are locked; this also covers admins warping in)
addEventHandler("onVehicleStartEnter", root, function(player, seat)
    if getElementData(source, "ngpd.decorative") and seat == 0 then cancelEvent() end
end)

------------------------------------------------------------------ client handshake
local function sendInit(player)
    local o = NGPD.origin
    triggerClientEvent(player, "ngpd:init", resourceRoot, o.x, o.y, o.z, o.rz, NGPD_CONFIG.interior, NGPD_CONFIG.dimension)
end

addEvent("ngpd:ready", true)
addEventHandler("ngpd:ready", resourceRoot, function()
    if not client then return end
    NGPD.server.readyClients[client] = true
    sendInit(client)
end)

addEventHandler("onPlayerQuit", root, function()
    NGPD.server.readyClients[source] = nil
end)

local function broadcastOrigin()
    for player in pairs(NGPD.server.readyClients) do
        if isElement(player) then sendInit(player) end
    end
end

------------------------------------------------------------------ relocation
function NGPD.applyOrigin(x, y, z, rz, persist)
    NGPD.setOrigin(x, y, z, rz)
    if persist then saveOrigin() end
    if NGPD.rebuildDoors then NGPD.rebuildDoors() end
    spawnVehicles()
    broadcastOrigin()
    local o = NGPD.origin
    outputServerLog(string.format("[NGPD] origin set to %.2f, %.2f, %.2f rz %.1f", o.x, o.y, o.z, o.rz))
end

addCommandHandler("ngpd_relocate", function(player)
    if not isAdmin(player) then return NGPD.notify(player, "Access denied.", "error") end
    if not isElement(player) or getElementType(player) ~= "player" then return outputServerLog("[NGPD] use /ngpd_setorigin from console") end
    local x, y, z = getElementPosition(player)
    local _, _, prz = getElementRotation(player)
    -- the player stands where the main entrance will be; ground level ~1 m below the ped origin
    NGPD.applyOrigin(x, y, z - 1.0, math.floor(prz / 90 + 0.5) * 90 % 360, true)
    NGPD.notify(player, "Police HQ moved to your position (entrance faces your back).", "ok")
end)

addCommandHandler("ngpd_setorigin", function(player, _, x, y, z, rz)
    if not isAdmin(player) then return NGPD.notify(player, "Access denied.", "error") end
    x, y, z, rz = tonumber(x), tonumber(y), tonumber(z), tonumber(rz) or 0
    if not (x and y and z) then return NGPD.notify(player, "Usage: /ngpd_setorigin x y z [rz]", "error") end
    NGPD.applyOrigin(x, y, z, rz, true)
    NGPD.notify(player, "Origin updated.", "ok")
end)

addCommandHandler("ngpd_resetorigin", function(player)
    if not isAdmin(player) then return NGPD.notify(player, "Access denied.", "error") end
    local o = NGPD_CONFIG.origin
    NGPD.applyOrigin(o.x, o.y, o.z, o.rz, true)
    NGPD.notify(player, "Origin reset to the default (Verdant Meadows).", "ok")
end)

addCommandHandler("ngpd_tp", function(player)
    if not isElement(player) or getElementType(player) ~= "player" then return end
    if not NGPD.hasAccess(player, NGPD_CONFIG.teleportAccess) then return NGPD.notify(player, "Access denied.", "error") end
    local a = NGPD_DATA.anchors.lobby_spawn
    local x, y, z = NGPD.toWorld(a[1], a[2], a[3] + 1.0)
    if isPedInVehicle(player) then removePedFromVehicle(player) end
    setElementInterior(player, NGPD_CONFIG.interior)
    setElementDimension(player, NGPD_CONFIG.dimension)
    setElementPosition(player, x, y, z)
    setElementRotation(player, 0, 0, NGPD.toWorldRot(180))
end)

addCommandHandler("ngpd_status", function(player)
    local o = NGPD.origin
    local doors = NGPD.doorStats and NGPD.doorStats() or {}
    local lines = {
        string.format("NGPD %s | origin %.1f %.1f %.1f rz %.0f | int %d dim %d", RES_NAME, o.x, o.y, o.z, o.rz, NGPD_CONFIG.interior, NGPD_CONFIG.dimension),
        string.format("models %d + %d leaves | doors %d (open %d, moving %d, locked %d) | vehicles %d | clients ready %d",
            #NGPD_DATA.models, #NGPD_DATA.leaves, #NGPD_DATA.doors, doors.open or 0, doors.moving or 0, doors.locked or 0,
            #NGPD.server.vehicles, (function() local n = 0 for _ in pairs(NGPD.server.readyClients) do n = n + 1 end return n end)()),
    }
    for _, l in ipairs(lines) do
        if isElement(player) and getElementType(player) == "player" then outputChatBox("[NGPD] " .. l, player, 120, 180, 255) else outputServerLog("[NGPD] " .. l) end
    end
end)

------------------------------------------------------------------ lifecycle
addEventHandler("onResourceStart", resourceRoot, function()
    local persisted = loadOrigin()
    if NGPD.buildDoors then NGPD.buildDoors() end
    spawnVehicles()
    local o = NGPD.origin
    outputServerLog(string.format("[NGPD] started: %d models, %d doors, origin %.1f %.1f %.1f rz %.0f (%s)",
        #NGPD_DATA.models, #NGPD_DATA.doors, o.x, o.y, o.z, o.rz, persisted and "from settings" or "default"))
end)

addEventHandler("onResourceStop", resourceRoot, function()
    -- elements created by this resource are destroyed by MTA; timers/tables are cleared explicitly
    destroyVehicles()
    NGPD.server.readyClients = {}
end)
