-- Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
-- Automatically gives every player weapon 10 (uses model 321 = the FishingRod) and selects it:
-- on resource start, on join and on every spawn.  No commands needed.
local WEAPON = 10

local function giveRod(player)
    if isElement(player) and not isPedDead(player) then
        giveWeapon(player, WEAPON, 1, true)
    end
end

addEventHandler("onResourceStart", resourceRoot, function()
    for _, p in ipairs(getElementsByType("player")) do giveRod(p) end
end)
addEventHandler("onPlayerSpawn", root, function() giveRod(source) end)
addEventHandler("onPlayerJoin", root, function() setTimer(giveRod, 2000, 1, source) end)
