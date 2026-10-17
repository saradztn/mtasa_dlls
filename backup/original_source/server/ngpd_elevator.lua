--[[
  NextGenPoliceDepartment - elevator.
  The lift car is modelled in every floor's chunk; travelling between floors is a validated teleport
  (the server checks that the player stands in a lift car and that the target floor exists).
]]

local lastUse = {}

local function stopAt(floor)
    for _, e in ipairs(NGPD_DATA.elevators) do
        if e.floor == floor then return e end
    end
end

local function nearestStop(player)
    local px, py, pz = getElementPosition(player)
    for _, e in ipairs(NGPD_DATA.elevators) do
        local x, y, z = NGPD.toWorld(e.x, e.y, e.z + 1.0)
        if NGPD.dist3(px, py, pz, x, y, z) <= NGPD_CONFIG.elevatorRadius + 0.6 then return e end
    end
end

addEvent("ngpd:elevator", true)
addEventHandler("ngpd:elevator", resourceRoot, function(targetFloor)
    local player = client
    if not player or type(targetFloor) ~= "number" then return end
    if isPedDead(player) or isPedInVehicle(player) then return end
    if getElementInterior(player) ~= NGPD_CONFIG.interior or getElementDimension(player) ~= NGPD_CONFIG.dimension then return end
    local t = getTickCount()
    if (lastUse[player] or 0) > t then return NGPD.notify(player, "The elevator is moving.", "error") end
    local from = nearestStop(player)
    if not from then return end
    local to = stopAt(math.floor(targetFloor))
    if not to or to.floor == from.floor then return end
    -- upper floors of the admin wing are staff only; ground floor always allowed
    if to.floor >= 2 and not NGPD.hasAccess(player, "police") then
        return NGPD.notify(player, "Floor " .. to.floor .. " requires police access (key card).", "error")
    end
    lastUse[player] = t + NGPD_CONFIG.elevatorCooldownMs
    local px, py, pz = getElementPosition(player)
    local lx, ly, lz = NGPD.toLocal(px, py, pz)
    -- keep the offset inside the car, change only the floor height
    local dx, dy = NGPD.clamp(lx - from.x, -0.8, 0.8), NGPD.clamp(ly - from.y, -0.8, 0.8)
    local x, y, z = NGPD.toWorld(to.x + dx, to.y + dy, to.z + 1.0)
    triggerClientEvent(player, "ngpd:elevatorFx", resourceRoot, to.floor)
    setTimer(function()
        if isElement(player) and not isPedDead(player) then
            setElementPosition(player, x, y, z)
        end
    end, 900, 1)
end)

addEventHandler("onPlayerQuit", root, function() lastUse[source] = nil end)
addEventHandler("onResourceStop", resourceRoot, function() lastUse = {} end)
