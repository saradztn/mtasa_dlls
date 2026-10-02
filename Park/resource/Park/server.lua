-- Created by: Arena.ai Agent Mode (AI) - Park MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- server.lua - /showpark builds the park in front of the player (for everybody), /hidepark removes it,
--              /parkz <metres> raises / lowers it.  The park state is kept here: players that join later
--              (or restart their client scripts) ask for it with "park:request" and get the current state.
--              Also: /sit support (sync of the sitting animation).
-- The park itself (objects, models, sounds, water ...) is created CLIENT side, see client.lua.
-- ---------------------------------------------------------------------------------------------
local CFG = {
    FORWARD = 17.0,        -- m: distance from the player to the gate centre (the park extends away from the player)
    Z_BELOW = 0.1,         -- gate/podium level = player's root z - 1.0 (ground) + 0.9 (podium height) = z - 0.1
    ADMIN_ONLY = false,    -- true: only members of the Admin ACL group may use /showpark /hidepark /parkz
    SIT_REACH = 4.0,       -- m: max distance between the player and the bench point sent by the client
}
local park = nil           -- { x, y, z, rz }

addEvent("park:request", true)
addEvent("park:sit", true)
addEvent("park:stand", true)

local function allowed(player)
    if not CFG.ADMIN_ONLY then return true end
    local acc = getPlayerAccount(player)
    if not acc or isGuestAccount(acc) then return false end
    return isObjectInACLGroup("user." .. getAccountName(acc), aclGetGroup("Admin")) and true or false
end

local function sendState(target)
    if park then
        triggerClientEvent(target, "park:show", resourceRoot, park.x, park.y, park.z, park.rz)
    else
        triggerClientEvent(target, "park:hide", resourceRoot)
    end
end

addCommandHandler("showpark", function(player)
    if not allowed(player) then outputChatBox("Park: you are not allowed to use this command.", player, 255, 80, 80) return end
    local x, y, z = getElementPosition(player)
    local _, _, rz = getElementRotation(player)
    local r = math.rad(rz)
    -- forward vector of a ped with rotation rz is (-sin rz, cos rz)
    park = { x = x - math.sin(r) * CFG.FORWARD, y = y + math.cos(r) * CFG.FORWARD, z = z - CFG.Z_BELOW, rz = rz }
    sendState(root)
    outputChatBox("Central Park is opening in front of you ... (/hidepark removes it, /parkz <m> adjusts the height, /sit on a bench)", player, 120, 230, 120)
end)

addCommandHandler("hidepark", function(player)
    if not allowed(player) then outputChatBox("Park: you are not allowed to use this command.", player, 255, 80, 80) return end
    park = nil
    sendState(root)
    outputChatBox("Central Park removed.", player, 230, 200, 120)
end)

addCommandHandler("parkz", function(player, _, dz)
    if not allowed(player) then return end
    dz = tonumber(dz)
    if not park or not dz then outputChatBox("Usage: /parkz <metres, e.g. 0.5 or -0.3>  (the park must be shown)", player, 230, 200, 120) return end
    park.z = park.z + math.max(-5, math.min(5, dz))
    sendState(root)
end)

addEventHandler("park:request", resourceRoot, function()
    if client then sendState(client) end
end)

-- /sit: the client sends the bench seat position; the server validates the distance and plays the animation (synced to everybody)
addEventHandler("park:sit", resourceRoot, function(x, y, z, rot)
    local player = client
    if not player or type(x) ~= "number" or type(y) ~= "number" or type(z) ~= "number" or type(rot) ~= "number" then return end
    local px, py, pz = getElementPosition(player)
    if isPedInVehicle(player) or isPedDead(player) then return end
    if getDistanceBetweenPoints3D(px, py, pz, x, y, z) > CFG.SIT_REACH then return end
    setElementPosition(player, x, y, z)
    setPedRotation(player, rot)
    setPedAnimation(player, "BEACH", "ParkSit_M_loop", -1, true, false, false, false)
end)

addEventHandler("park:stand", resourceRoot, function()
    local player = client
    if player then setPedAnimation(player) end
end)

