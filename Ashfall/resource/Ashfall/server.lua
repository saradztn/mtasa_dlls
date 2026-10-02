-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- server.lua - /showcity drops the whole district on its fixed world anchor and teleports you to the
--              south entrance of the park; /hidecity removes it; /cityz <m> trims the height.
--              The city itself (objects, models, water, sounds) is created client side, see client.lua.
-- ---------------------------------------------------------------------------------------------
local CFG = {
    ADMIN_ONLY = false,
}
local city = nil        -- { zoff }

addEvent("city:request", true)

local function allowed(player)
    if not CFG.ADMIN_ONLY then return true end
    local acc = getPlayerAccount(player)
    if not acc or isGuestAccount(acc) then return false end
    return isObjectInACLGroup("user." .. getAccountName(acc), aclGetGroup("Admin")) and true or false
end

local function sendState(target)
    if city then
        triggerClientEvent(target, "city:show", resourceRoot, city.zoff)
    else
        triggerClientEvent(target, "city:hide", resourceRoot)
    end
end

addCommandHandler("showcity", function(player)
    if not allowed(player) then outputChatBox("Ashfall: you are not allowed to use this command.", player, 255, 80, 80) return end
    city = { zoff = 0 }
    -- drop the player at the park's south entrance (spawn point of layout.lua: 0, -62)
    local P = AF_POINTS.spawn
    setElementPosition(player, -1900.0 + P[1], -2400.0 + P[2], 1.5 + P[3] + 1.0)
    setElementRotation(player, 0, 0, 0)
    sendState(root)
    outputChatBox("Welcome to District Zero - the abandoned city.  (/hidecity removes it, /cityz <m> adjusts the height, /citywind leaf sway)", player, 200, 176, 144)
end)

addCommandHandler("hidecity", function(player)
    if not allowed(player) then outputChatBox("Ashfall: you are not allowed to use this command.", player, 255, 80, 80) return end
    city = nil
    sendState(root)
    outputChatBox("District Zero removed.", player, 230, 200, 120)
end)

addCommandHandler("cityz", function(player, _, dz)
    if not allowed(player) then return end
    dz = tonumber(dz)
    if not city or not dz then outputChatBox("Usage: /cityz <metres, e.g. 0.5 or -0.3>  (the city must be shown)", player, 230, 200, 120) return end
    city.zoff = city.zoff + math.max(-8, math.min(8, dz))
    triggerClientEvent(root, "city:zoff", resourceRoot, dz)
end)

addEventHandler("city:request", resourceRoot, function()
    if client then sendState(client) end
end)
