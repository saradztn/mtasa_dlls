-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- zombies_client.lua - client side of the infected (server side: zombies.lua)
--   * forwards every hit the local player lands on a zombie (weapon, body part, damage) so the server can stagger / alert / head-shot it
--   * red damage flash when a zombie hurts the local player
--   * /zombiedebug : state label and type above every zombie in sight (idle, wander, search, chase, attack) - for further development
-- ---------------------------------------------------------------------------------------------
addEvent("zombie:hurt", true)

local flash = { a = 0 }
local lastHit = 0
local debugOn = false

addEventHandler("onClientPedDamage", root, function(attacker, weapon, bodypart, loss)
    if attacker ~= localPlayer then return end
    if not getElementData(source, "af:zombie") then return end
    local now = getTickCount()
    if now - lastHit < 60 then return end          -- one report per shot is enough
    lastHit = now
    triggerServerEvent("zombie:hit", resourceRoot, source, tonumber(weapon) or 0, tonumber(bodypart) or 3, tonumber(loss) or 0)
end)

addEventHandler("zombie:hurt", resourceRoot, function(dmg)
    flash.a = math.min(150, flash.a + 45 + (tonumber(dmg) or 5) * 4)
end)

addEventHandler("onClientRender", root, function()
    if flash.a > 1 then
        local sw, sh = guiGetScreenSize()
        local a = math.floor(flash.a)
        dxDrawRectangle(0, 0, sw, sh, tocolor(140, 0, 0, a))
        flash.a = flash.a * 0.90
    end
    if debugOn then
        local cx, cy, cz = getCameraMatrix()
        for _, p in ipairs(getElementsByType("ped", root, true)) do
            local t = getElementData(p, "af:zombie")
            if t then
                local x, y, z = getElementPosition(p)
                local d = getDistanceBetweenPoints3D(cx, cy, cz, x, y, z)
                if d < 60 then
                    local sx, sy = getScreenFromWorldPosition(x, y, z + 1.1)
                    if sx then
                        local st = getElementData(p, "af:zs") or "?"
                        dxDrawText(t .. " [" .. st .. "]  hp " .. math.floor(getElementHealth(p)), sx - 80, sy - 10, sx + 80, sy + 10, tocolor(255, 220, 160, 230), 1, "default-bold", "center", "center")
                    end
                end
            end
        end
    end
end)

addCommandHandler("zombiedebug", function()
    debugOn = not debugOn
    outputChatBox("#c8b090[Ashfall zombies] #ffffffdebug labels: " .. (debugOn and "ON" or "OFF"), 255, 255, 255, true)
end)
