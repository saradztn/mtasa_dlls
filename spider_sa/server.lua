--[[
    spider_sa / server.lua

    The model replacement itself is client side, so the server only coordinates:
      * /spiderall          place a spider for every player, at the position the
                            executing player is looking at
      * /spiderall remove   remove it again for every player
      * joining players     get the current state re-sent when their client
                            resource starts (see spiderSa:requestState)
]]

local C = SpiderConfig or {}
local SPREAD = (C.spawnRange or 6.0)

local placement = nil              -- { x = , y = , z = , rot = , by = playerName }

local function atan2(y, x)
    if math.atan2 then return math.atan2(y, x) end
    return math.atan(y, x)                                  -- Lua 5.3+ style
end

local function forwardVector(element)
    -- exact forward direction from the element matrix (row 2 = forward)
    local matrix = getElementMatrix(element, false)
    if matrix and matrix[2] then
        local fx, fy, fz = matrix[2][1], matrix[2][2], matrix[2][3]
        local len = math.sqrt(fx * fx + fy * fy + fz * fz)
        if len > 0.0001 then
            return fx / len, fy / len, fz / len
        end
    end
    -- fallback: GTA z-rotation convention (0 = north, clockwise)
    local _, _, rot = getElementRotation(element)
    local rad = math.rad(rot)
    return math.sin(-rad), math.cos(-rad), 0
end

local function computePlacement(player)
    local px, py, pz = getElementPosition(player)
    local fx, fy = forwardVector(player)
    local x, y = px + fx * SPREAD, py + fy * SPREAD
    local groundZ = getGroundPosition(x, y, pz + 2.0)
    local z = groundZ or pz
    -- face the player: the model looks along +Y, z-rotation grows clockwise
    local rot = -math.deg(atan2(px - x, py - y))
    return { x = x, y = y, z = z, rot = rot, by = getPlayerName(player) }
end

addCommandHandler("spiderall", function(player, _, sub)
    sub = string.lower(tostring(sub or ""))

    if sub == "remove" or sub == "clear" then
        placement = nil
        triggerClientEvent("spiderSa:remove", resourceRoot, root)
        outputChatBox("[spider] removed the spider for every player", 255, 205, 130)
        return
    end

    if sub == "info" then
        if placement then
            outputChatBox(string.format("[spider] placed by %s at %.1f %.1f %.1f",
                placement.by, placement.x, placement.y, placement.z), 255, 205, 130)
        else
            outputChatBox("[spider] no global spider is placed", 255, 205, 130)
        end
        return
    end

    if sub ~= "" and sub ~= "spawn" then
        outputChatBox("[spider] usage: /spiderall [spawn|remove|info]", 255, 205, 130)
        return
    end

    if not player then return end
    placement = computePlacement(player)
    triggerClientEvent("spiderSa:spawn", resourceRoot, root,
        placement.x, placement.y, placement.z, placement.rot)
    outputChatBox(string.format("[spider] placed for every player at %.1f %.1f %.1f",
        placement.x, placement.y, placement.z), 255, 205, 130)
end)

addEvent("spiderSa:requestState", true)
addEventHandler("spiderSa:requestState", root, function()
    local player = client
    if player and placement and isElement(player) then
        triggerClientEvent("spiderSa:spawn", player, placement.x, placement.y, placement.z, placement.rot)
    end
end)

addEventHandler("onPlayerJoin", root, function()
    -- the client resource starts right after the join and asks for the state
    -- itself, this is only a safety net for clients that miss that handshake
    if not placement then return end
    local player = source
    setTimer(function()
        if isElement(player) then
            triggerClientEvent("spiderSa:spawn", player,
                placement.x, placement.y, placement.z, placement.rot)
        end
    end, 3000, 1)
end)
