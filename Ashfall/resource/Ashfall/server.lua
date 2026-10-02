-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- server.lua - /showcity drops the whole district high above the map (or /showcity here on the ground where you stand) and
--              teleports you to the south entrance of the park; /hidecity removes it; /cityz <m> trims the height.
--              The city itself (objects, models, water, sounds) is created client side, see client.lua.
-- ---------------------------------------------------------------------------------------------
local CFG = {
    ADMIN_ONLY = false,
    SKY = { x = 0.0, y = 0.0, z = 900.0 },        -- default anchor: high above the map, so no vanilla terrain, tree or building can touch the city
    SAFE = { 2495.0, -1688.0, 14.0 },             -- where players are sent when the sky city is removed (Grove Street)
}
local city = nil        -- { zoff, ax, ay, az }   world position of the city origin

addEvent("city:request", true)

local function allowed(player)
    if not CFG.ADMIN_ONLY then return true end
    local acc = getPlayerAccount(player)
    if not acc or isGuestAccount(acc) then return false end
    return isObjectInACLGroup("user." .. getAccountName(acc), aclGetGroup("Admin")) and true or false
end

local function sendState(target)
    if target == root and AF_ZOMBIES_CITY then AF_ZOMBIES_CITY(city, city ~= nil and city.fresh) end
    if city then city.fresh = nil end
    if city then
        triggerClientEvent(target, "city:show", resourceRoot, city.zoff, city.ax, city.ay, city.az)
    else
        triggerClientEvent(target, "city:hide", resourceRoot)
    end
end

-- /showcity            city high above the map (default, always works, nothing can poke through it)
-- /showcity here       city on the ground exactly where you stand (use it on flat ground; the park is 62 m in front of you)
-- /showcity x y z      city origin at the given world position
addCommandHandler("showcity", function(player, _, a1, a2, a3)
    if not allowed(player) then outputChatBox("Ashfall: you are not allowed to use this command.", player, 255, 80, 80) return end
    local P = AF_POINTS.spawn
    local ax, ay, az
    local tele = true
    if a1 == "here" then
        local px, py, pz = getElementPosition(player)
        ax, ay, az = px - P[1], py - P[2], pz - 1.0
        tele = false
    elseif tonumber(a1) and tonumber(a2) and tonumber(a3) then
        ax, ay, az = tonumber(a1), tonumber(a2), tonumber(a3)
    else
        ax, ay, az = CFG.SKY.x, CFG.SKY.y, CFG.SKY.z
    end
    city = { zoff = 0, ax = ax, ay = ay, az = az, fresh = true }
    if tele then      -- drop the player at the park's south entrance (spawn point of layout.lua); the client freezes him until the ground exists
        setElementPosition(player, ax + P[1], ay + P[2], az + P[3] + 1.0)
        setElementRotation(player, 0, 0, 0)
    end
    sendState(root)
    outputChatBox("Welcome to District Zero - the abandoned city.  (/hidecity removes it, /cityz <m> adjusts the height, /citywind leaf sway)", player, 200, 176, 144)
end)

addCommandHandler("hidecity", function(player)
    if not allowed(player) then outputChatBox("Ashfall: you are not allowed to use this command.", player, 255, 80, 80) return end
    if city and city.az > 300 then    -- sky city: nobody may fall 900 m when the ground disappears
        for _, p in ipairs(getElementsByType("player")) do
            local x, y, z = getElementPosition(p)
            if z > 300 and math.abs(x - city.ax) < 400 and math.abs(y - city.ay) < 400 then
                setElementPosition(p, CFG.SAFE[1], CFG.SAFE[2], CFG.SAFE[3])
            end
        end
    end
    city = nil
    sendState(root)
    outputChatBox("District Zero removed.", player, 230, 200, 120)
end)

addCommandHandler("cityz", function(player, _, dz)
    if not allowed(player) then return end
    dz = tonumber(dz)
    if not city or not dz then outputChatBox("Usage: /cityz <metres, e.g. 0.5 or -0.3>  (the city must be shown)", player, 230, 200, 120) return end
    dz = math.max(-8, math.min(8, dz))
    city.zoff = city.zoff + dz
    if AF_ZOMBIES_CITY then AF_ZOMBIES_CITY(city) end
    triggerClientEvent(root, "city:zoff", resourceRoot, dz)
end)

addEventHandler("city:request", resourceRoot, function()
    if client then sendState(client) end
end)
