-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- boundary.lua (server) - the invisible border of District Zero.
--   The 340 m district is surrounded by a wasteland whose rim is a mountain range (ground tiles of apron.py).  At the foot of the
--   mountains, 497 m from the city centre, a square ring of invisible collision walls (model af_border, created by the clients,
--   alpha 0) stops everybody.  This script is the server side of the same border:
--     * a player who was inside and is found outside (square limit, too high, or fallen through) is put back on his last good position
--       (vehicle included, velocity cleared) - nobody can get past the mountains by jetpack, vehicle jump or lag
--     * players who are teleported in from outside are never touched (the border only works on those who were inside)
-- ---------------------------------------------------------------------------------------------
AF_BCFG = {
    LIMIT = 497.0,        -- half size of the square (m) measured from the city centre
    MAX_UP = 230.0,       -- metres above the city level (the mountains reach ~120 m, the wall 170 m)
    MAX_DOWN = 60.0,      -- metres below the city level (fell through the world)
    TICK = 350,
    JUMP = 400.0,         -- a step longer than this is a teleport, not a walk: leave the player alone
}

local B = nil             -- { x, y, z } city origin (z includes /cityz)
local last = {}           -- player -> { x, y, z }
local warned = {}

function AF_BOUNDARY_CITY(city)
    if not city then
        B = nil
        last, warned = {}, {}
        return
    end
    B = { x = city.ax, y = city.ay, z = city.az + city.zoff }
end

local function inside(x, y, z)
    return math.abs(x - B.x) < AF_BCFG.LIMIT and math.abs(y - B.y) < AF_BCFG.LIMIT and z < B.z + AF_BCFG.MAX_UP and z > B.z - AF_BCFG.MAX_DOWN
end

setTimer(function()
    if not B then return end
    for _, p in ipairs(getElementsByType("player")) do
        if isElement(p) and not isPedDead(p) and getElementDimension(p) == 0 then
            local x, y, z = getElementPosition(p)
            if inside(x, y, z) then
                last[p] = { x = x, y = y, z = z }
            else
                local l = last[p]
                if l then
                    local d = math.sqrt((x - l.x) ^ 2 + (y - l.y) ^ 2 + (z - l.z) ^ 2)
                    if d < AF_BCFG.JUMP then
                        local veh = getPedOccupiedVehicle(p)
                        local target = veh or p
                        setElementPosition(target, l.x, l.y, l.z + 0.3)
                        setElementVelocity(target, 0, 0, 0)
                        local now = getTickCount()
                        if not warned[p] or now - warned[p] > 6000 then
                            warned[p] = now
                            outputChatBox("#c8b090[Ashfall] #ffffffThe mountains block the way - there is nothing beyond them.", p, 255, 255, 255, true)
                        end
                    else
                        last[p] = nil          -- teleported away (admin, /hidecity, ...): free again
                    end
                end
            end
        end
    end
end, AF_BCFG.TICK, 0)

addEventHandler("onPlayerQuit", root, function() last[source] = nil warned[source] = nil end)
