--[[
  NextGenPoliceDepartment - interaction UI (doors, elevator, notices, room label).
  Purely cosmetic: it shows prompts and forwards requests; the server validates every request
  (distance, permissions, lock, cooldowns) and owns all door state.
]]

local sx, sy = guiGetScreenSize()
local UI = { door = nil, lift = nil, notices = {}, room = nil, lastReq = 0 }
local KIND_LABEL = { exit = "Emergency Exit", security = "Security Door", cell = "Cell Door", swing = "Door",
                     slide_glass = "Main Entrance", rollup = "Garage Door", gate = "Gate", barrier = "Barrier" }
local FLOOR_NAME = { [0] = "Ground", [1] = "First", [2] = "Second" }

local roomLabel = {}
for _, r in ipairs(NGPD_DATA.rooms) do roomLabel[r.id] = r.label end

local function doorTitle(d)
    local other
    for _, rid in ipairs(d.rooms or {}) do
        if rid ~= "__outside__" and not rid:find("corridor") then other = roomLabel[rid] or rid end
    end
    return (KIND_LABEL[d.kind] or "Door") .. (other and (" - " .. other) or "")
end

local function uiBlocked()
    return isChatBoxInputActive() or isConsoleActive() or isMainMenuActive() or isCursorShowing()
end

------------------------------------------------------------------ scanning (5 Hz)
local function scan()
    if not NGPD.models.loaded then UI.door, UI.lift = nil, nil return end
    local px, py, pz = getElementPosition(localPlayer)
    local inVeh = isPedInVehicle(localPlayer)
    local CFG = NGPD_CONFIG.doors
    local best, bd = nil, math.huge
    for _, d in ipairs(NGPD_DATA.doors) do
        if not inVeh or CFG.vehicleKinds[d.kind] then
            local cx, cy, cz = NGPD.doorCentre(d)
            local r = (inVeh and CFG.vehicleRadius or CFG.interactRadius) + (d.w or 1) * 0.5 - 0.2
            local dd = NGPD.dist3(px, py, pz, cx, cy, cz)
            if dd < r and dd < bd then best, bd = d, dd end
        end
    end
    UI.door = best
    local lift
    if not inVeh then
        for _, e in ipairs(NGPD_DATA.elevators) do
            local x, y, z = NGPD.toWorld(e.x, e.y, e.z + 1.0)
            if NGPD.dist3(px, py, pz, x, y, z) <= NGPD_CONFIG.elevatorRadius then lift = e end
        end
    end
    if lift ~= UI.lift then
        UI.lift = lift
        for i = 1, #NGPD_DATA.elevators do
            if lift then bindKey(tostring(i), "down", UI.liftKey) else unbindKey(tostring(i), "down", UI.liftKey) end
        end
    end
    local lx, ly, lz = NGPD.toLocal(px, py, pz)
    UI.room = NGPD.isInsideBuilding(lx, ly, lz) and NGPD.roomAt(lx, ly, lz) or nil
end

function UI.liftKey(key)
    if not UI.lift or uiBlocked() then return end
    local floor = tonumber(key) - 1
    if floor == UI.lift.floor then return end
    triggerServerEvent("ngpd:elevator", resourceRoot, floor)
end

local function useKey()
    if not UI.door or uiBlocked() then return end
    local t = getTickCount()
    if t - UI.lastReq < 400 then return end      -- local spam guard; the server has the real cooldown
    UI.lastReq = t
    triggerServerEvent("ngpd:doorRequest", resourceRoot, UI.door.id)
end

------------------------------------------------------------------ drawing
local function shadowText(text, x, y, w, h, color, scale, font, ax)
    dxDrawText(text, x + 1, y + 1, x + w + 1, y + h + 1, tocolor(0, 0, 0, 200), scale, font, ax or "center", "center")
    dxDrawText(text, x, y, x + w, y + h, color, scale, font, ax or "center", "center")
end

local function render()
    local y0 = sy * 0.72
    if UI.door then
        local el = getElementByID("ngpd_door_" .. UI.door.id)
        local state = el and getElementData(el, "ngpd.state") or "closed"
        local locked = el and getElementData(el, "ngpd.locked")
        local action
        if locked then action = "LOCKED"
        elseif state == "opening" or state == "closing" then action = state:upper() .. "..."
        else action = "[E] " .. (state == "open" and "Close" or "Open") end
        local col = locked and tocolor(255, 90, 90) or tocolor(255, 255, 255)
        dxDrawRectangle(sx * 0.5 - 190, y0 - 6, 380, 52, tocolor(8, 14, 28, 170))
        dxDrawRectangle(sx * 0.5 - 190, y0 - 6, 4, 52, tocolor(40, 110, 255, 230))
        shadowText(doorTitle(UI.door), sx * 0.5 - 180, y0 - 4, 360, 22, tocolor(160, 200, 255), 1.0, "default-bold")
        local access = UI.door.access ~= "public" and ("  (" .. UI.door.access .. ")") or ""
        shadowText(action .. access, sx * 0.5 - 180, y0 + 18, 360, 24, col, 1.15, "default-bold")
        y0 = y0 + 60
    end
    if UI.lift then
        local parts = {}
        for i, e in ipairs(NGPD_DATA.elevators) do
            parts[#parts + 1] = (e.floor == UI.lift.floor) and ("[" .. i .. "] " .. (FLOOR_NAME[e.floor] or e.floor) .. " (here)") or ("[" .. i .. "] " .. (FLOOR_NAME[e.floor] or e.floor))
        end
        dxDrawRectangle(sx * 0.5 - 220, y0 - 6, 440, 34, tocolor(8, 14, 28, 170))
        shadowText("ELEVATOR   " .. table.concat(parts, "   "), sx * 0.5 - 210, y0 - 6, 420, 34, tocolor(255, 255, 255), 1.0, "default-bold")
    end
    if UI.room then
        shadowText(UI.room.label, sx - 330, sy * 0.30, 310, 20, tocolor(200, 220, 255, 220), 1.0, "default-bold", "right")
    end
    local t = getTickCount()
    local ny = sy * 0.25
    for i = #UI.notices, 1, -1 do
        local n = UI.notices[i]
        if t > n.untilTick then table.remove(UI.notices, i) end
    end
    for _, n in ipairs(UI.notices) do
        local c = n.kind == "error" and tocolor(255, 110, 110) or n.kind == "ok" and tocolor(130, 255, 160) or n.kind == "warn" and tocolor(255, 210, 90) or tocolor(220, 230, 255)
        shadowText(n.text, 0, ny, sx, 24, c, 1.1, "default-bold")
        ny = ny + 26
    end
end

------------------------------------------------------------------ events
addEvent("ngpd:notice", true)
addEventHandler("ngpd:notice", resourceRoot, function(text, kind)
    table.insert(UI.notices, { text = tostring(text), kind = kind, untilTick = getTickCount() + 3500 })
    while #UI.notices > 4 do table.remove(UI.notices, 1) end
end)

addEvent("ngpd:elevatorFx", true)
addEventHandler("ngpd:elevatorFx", resourceRoot, function(floor)
    fadeCamera(false, 0.5, 0, 0, 0)
    playSoundFrontEnd(41)
    setTimer(function() fadeCamera(true, 0.6) end, 1300, 1)
    table.insert(UI.notices, { text = "Elevator: " .. (FLOOR_NAME[floor] or tostring(floor)) .. " floor", kind = "info", untilTick = getTickCount() + 2500 })
end)

addEventHandler("onClientResourceStart", resourceRoot, function()
    UI.timer = setTimer(scan, 200, 0)
    bindKey("e", "down", useKey)
    addEventHandler("onClientRender", root, render)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    if isTimer(UI.timer) then killTimer(UI.timer) end
    unbindKey("e", "down", useKey)
    for i = 1, #NGPD_DATA.elevators do unbindKey(tostring(i), "down", UI.liftKey) end
    removeEventHandler("onClientRender", root, render)
    fadeCamera(true, 0)
end)
