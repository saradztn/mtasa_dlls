-- Created by: Arena.ai Agent Mode (AI) - Park MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- client.lua - Central Park.  Everything is CLIENT side:
--   * models are allocated with engineRequestModel("object", parent) (no vanilla model is replaced), looked up by NAME
--   * ~830 client objects are created in small batches when the server says "park:show"
--   * pond water (createWater) with a swimmable bowl, fountain effect, automatic entrance gate, animated swings /
--     merry-go-round / ducks, /sit on benches, info boards, radar blip, night lamp lights
--   * procedural sounds (files/audio/*.wav) played with playSound3D: fountain, pond, wind, city, crickets, birds, frogs ...
--   * optional wind-sway shader: /parkwind (default OFF)
-- Park frame: x -60..60, y 0..90, origin = centre of the gate, +y into the park, z = 0 podium top (layout.lua).
-- ---------------------------------------------------------------------------------------------
local CFG = {
    PARENTS = { 1215, false },     -- parent model ids tried for engineRequestModel (false = MTA default parent)
    BATCH = 70,                    -- objects created per step
    BATCH_MS = 40,
    GATE_REACH = 9.0,              -- m: the gate opens when somebody is this close to its centre
    GATE_OPEN = 85,                -- degrees
    GATE_MS = 1400,
    SOUND = true,
    BIRD_EVERY = { 3500, 9000 },
    LIGHTS = 4,
}

local S = {
    loaded = false, loading = false, ids = {}, txd = {}, dffs = {}, cols = {},
    shown = false, ox = 0, oy = 0, oz = 0, rot = 0,
    objs = {}, timers = {}, sounds = {}, extras = {},
    swings = {}, ducks = {}, merry = nil, gate = nil, sitting = false, wind = nil, lights = {},
    pending = nil,
}
addEvent("park:show", true)
addEvent("park:hide", true)

-- ---------------------------------------------------------------------------------------------
-- helpers
-- ---------------------------------------------------------------------------------------------
local function toWorld(px, py, pz)
    local r = math.rad(S.rot)
    local c, s = math.cos(r), math.sin(r)
    return S.ox + c * px - s * py, S.oy + s * px + c * py, S.oz + pz
end

local function track(t)
    S.timers[#S.timers + 1] = t
    return t
end

local function dbg(msg)
    outputDebugString("[Park] " .. msg, 3)
end

local function say(msg, r, g, b)
    outputChatBox("#78e678[Park] #ffffff" .. msg, r or 255, g or 255, b or 255, true)
end

local function hourNow()
    local h, m = getTime()
    return h + m / 60
end

local function isNight()
    local h = hourNow()
    return h >= 20.0 or h < 5.5
end

local function isDay()
    local h = hourNow()
    return h >= 6.0 and h < 19.5
end

local function parkDist()
    local px, py = getElementPosition(localPlayer)
    local cx, cy = toWorld(0, 45, 0)
    return math.sqrt((px - cx) ^ 2 + (py - cy) ^ 2)
end

-- ---------------------------------------------------------------------------------------------
-- models: engineRequestModel + TXD / COL / DFF
-- ---------------------------------------------------------------------------------------------
local function requestId()
    for _, parent in ipairs(CFG.PARENTS) do
        local id
        if parent then id = engineRequestModel("object", parent) else id = engineRequestModel("object") end
        if id then return id end
    end
    return false
end

local function loadOne(i)
    local def = PARK_MODELS[i]
    local id = requestId()
    if not id then dbg("engineRequestModel failed for " .. def.name) return false end
    S.ids[i] = id
    local txd = S.txd[def.txd]
    if not txd then
        txd = engineLoadTXD("files/" .. def.txd .. ".txd")
        if not txd then dbg("cannot load TXD " .. def.txd) engineFreeModel(id) S.ids[i] = nil return false end
        S.txd[def.txd] = txd
    end
    local col = engineLoadCOL("files/" .. def.name .. ".col")
    local dff = engineLoadDFF("files/" .. def.name .. ".dff")
    if not col or not dff then
        dbg("cannot load " .. def.name)
        engineFreeModel(id) S.ids[i] = nil
        return false
    end
    engineImportTXD(txd, id)
    engineReplaceCOL(col, id)
    engineReplaceModel(dff, id, def.alpha and true or false)
    engineSetModelLODDistance(id, def.dist or 150)
    S.cols[i], S.dffs[i] = col, dff
    return true
end

local function loadModels(done)
    if S.loaded then done(true) return end
    if S.loading then return end
    S.loading = true
    local i, n, failed = 0, #PARK_MODELS, 0
    local function step()
        local stop = math.min(i + 8, n)
        while i < stop do
            i = i + 1
            if not loadOne(i) then failed = failed + 1 end
        end
        if i < n then
            setTimer(step, 30, 1)
        else
            S.loading = false
            S.loaded = failed < n
            if failed > 0 then say(failed .. " of " .. n .. " models could not be loaded (see debugscript 3).", 255, 150, 120) end
            done(S.loaded)
        end
    end
    step()
end

local function freeModels()
    for i, id in pairs(S.ids) do engineFreeModel(id) end
    for _, e in pairs(S.dffs) do if isElement(e) then destroyElement(e) end end
    for _, e in pairs(S.cols) do if isElement(e) then destroyElement(e) end end
    for _, e in pairs(S.txd) do if isElement(e) then destroyElement(e) end end
    S.ids, S.dffs, S.cols, S.txd, S.loaded = {}, {}, {}, {}, false
end

-- ---------------------------------------------------------------------------------------------
-- sounds
-- ---------------------------------------------------------------------------------------------
local function snd3(file, px, py, pz, loop, vol, minD, maxD)
    if not CFG.SOUND then return nil end
    local x, y, z = toWorld(px, py, pz)
    local s = playSound3D("files/audio/" .. file .. ".wav", x, y, z, loop and true or false)
    if s then
        setSoundVolume(s, vol or 1)
        setSoundMinDistance(s, minD or 5)
        setSoundMaxDistance(s, maxD or 40)
        if loop then S.sounds[#S.sounds + 1] = s end
    end
    return s
end

local function snd2(file, loop, vol)
    if not CFG.SOUND then return nil end
    local s = playSound("files/audio/" .. file .. ".wav", loop and true or false)
    if s then
        setSoundVolume(s, vol or 1)
        if loop then S.sounds[#S.sounds + 1] = s end
    end
    return s
end

local function rnd(a, b)
    return a + (b - a) * math.random()
end

local ambience = {}

local function startAmbience()
    local P = PARK_POINTS
    ambience.fountain = snd3("fountain_loop", P.fountain[1], P.fountain[2], 1.5, true, 1.0, 7, 48)
    ambience.pond = snd3("pond_loop", P.pond[1], P.pond[2], P.pond[3], true, 0.8, 8, 42)
    ambience.wind = snd2("wind_loop", true, 0)
    ambience.city = snd2("city_loop", true, 0)
    ambience.crickets = {}
    for _, p in ipairs({ { -48, 20 }, { 48, 14 }, { -30, 80 }, { 20, 74 }, { 20, 38 } }) do
        local s = snd3("crickets_loop", p[1], p[2], 0.5, true, 0, 4, 34)
        if s then ambience.crickets[#ambience.crickets + 1] = s end
    end
    track(setTimer(function()
        local d = parkDist()
        local inside = math.max(0, math.min(1, (95 - d) / 45))
        if ambience.wind and isElement(ambience.wind) then setSoundVolume(ambience.wind, 0.30 * inside) end
        if ambience.city and isElement(ambience.city) then setSoundVolume(ambience.city, 0.22 * inside) end
        local cv = isNight() and 0.55 or 0.0
        for _, s in ipairs(ambience.crickets) do if isElement(s) then setSoundVolume(s, cv) end end
    end, 2000, 0))
    -- birds (daytime) and frogs (night), random timers
    local function birdTick()
        if S.shown and CFG.SOUND then
            local d = parkDist()
            if d < 80 then
                if isDay() and #PARK_TREES > 0 then
                    local px, py = getElementPosition(localPlayer)
                    local best, tries = nil, 0
                    while tries < 8 do
                        tries = tries + 1
                        local t = PARK_TREES[math.random(#PARK_TREES)]
                        local wx, wy = toWorld(t[1], t[2], 0)
                        if (wx - px) ^ 2 + (wy - py) ^ 2 < 55 ^ 2 then best = t break end
                    end
                    if best then snd3("bird" .. math.random(5), best[1], best[2], best[3] + rnd(5.5, 8.5), false, rnd(0.55, 0.9), 6, 52) end
                elseif isNight() then
                    local P_ = PARK_POINTS.pond
                    snd3("frog", P_[1] + rnd(-12, 12), P_[2] + rnd(-5, 5), 0, false, rnd(0.5, 0.8), 4, 32)
                end
            end
        end
        if S.shown then track(setTimer(birdTick, math.random(CFG.BIRD_EVERY[1], CFG.BIRD_EVERY[2]), 1)) end
    end
    track(setTimer(birdTick, 1500, 1))
end

-- ---------------------------------------------------------------------------------------------
-- animation: gate, swings, merry-go-round, ducks
-- ---------------------------------------------------------------------------------------------
local function gateTick()
    local g = S.gate
    if not g or g.busy or not isElement(g.L) then return end
    local gx, gy, gz = toWorld(0, 0, 0)
    local near = false
    for _, p in ipairs(getElementsByType("player", root, true)) do
        local x, y, z = getElementPosition(p)
        if (x - gx) ^ 2 + (y - gy) ^ 2 < CFG.GATE_REACH ^ 2 and math.abs(z - gz) < 8 then near = true break end
    end
    if near ~= g.open then
        g.busy = true
        g.open = near
        local d = near and CFG.GATE_OPEN or -CFG.GATE_OPEN
        local x, y, z = getElementPosition(g.L)
        moveObject(g.L, CFG.GATE_MS, x, y, z, 0, 0, d, "InOutQuad")
        x, y, z = getElementPosition(g.R)
        moveObject(g.R, CFG.GATE_MS, x, y, z, 0, 0, -d, "InOutQuad")
        snd3("gate_creak", 0, 0, 1.5, false, 0.85, 8, 45)
        track(setTimer(function() if S.gate then S.gate.busy = false end end, CFG.GATE_MS + 80, 1))
    end
end

local lastTick = getTickCount()
local swingSnd, merrySnd, bellAt, duckAt = -1e9, -1e9, -1e9, -1e9

local function onRender()
    if not S.shown then return end
    local now = getTickCount()
    local dt = math.min((now - lastTick) / 1000, 0.1)
    lastTick = now
    local t = now / 1000
    local px, py, pz = getElementPosition(localPlayer)
    local d = parkDist()
    if d > 110 then return end
    -- swings: pendulum about the top bar, bigger when somebody is near
    for _, sw in ipairs(S.swings) do
        if isElement(sw.obj) then
            local near = (px - sw.wx) ^ 2 + (py - sw.wy) ^ 2 < 36
            sw.amp = sw.amp + ((near and 0.42 or 0.07) - sw.amp) * math.min(dt * 0.6, 1)
            local a = math.deg(sw.amp * math.sin(t * 2.15 + sw.ph))
            setElementRotation(sw.obj, a, 0, S.rot)
            if near and now - swingSnd > 3200 and math.abs(a) > 8 then
                swingSnd = now
                snd3("swing_creak", PARK_POINTS.swing[1], PARK_POINTS.swing[2], 1.5, false, 0.35, 3, 22)
            end
        end
    end
    -- merry-go-round: pushed by the player running next to it, slows down by itself
    local m = S.merry
    if m and isElement(m.obj) then
        local dx, dy = px - m.wx, py - m.wy
        local r = math.sqrt(dx * dx + dy * dy)
        if r > 0.8 and r < 2.6 and math.abs(pz - m.wz) < 2.2 then
            local vx, vy = getElementVelocity(localPlayer)
            local tang = (-dy * vx + dx * vy) / r
            m.w = m.w + tang * 6.0 * dt
        end
        m.w = m.w * (1 - 0.30 * dt)
        if m.w > 3.2 then m.w = 3.2 elseif m.w < -3.2 then m.w = -3.2 end
        m.ang = (m.ang + m.w * dt * 57.2958) % 360
        setElementRotation(m.obj, 0, 0, S.rot + m.ang)
        if math.abs(m.w) > 0.9 and now - merrySnd > 1800 and r < 30 then
            merrySnd = now
            local s = snd3("swing_creak", PARK_POINTS.merry[1], PARK_POINTS.merry[2], 0.6, false, 0.3, 3, 20)
            if s then setSoundSpeed(s, 0.7) end
        end
    end
    -- ducks paddle in ellipses over the pond (they pass under the bridge)
    local cx, cy, wz = PARK_POND.cx, PARK_POND.cy, PARK_POND.z
    for _, du in ipairs(S.ducks) do
        if isElement(du.obj) then
            local th = du.ph + t * du.sp
            local x = cx + du.a * math.cos(th)
            local y = cy + du.b * math.sin(th)
            local hx, hy = -du.a * math.sin(th) * du.sp, du.b * math.cos(th) * du.sp
            local rzl = math.deg(math.atan2(-hx, hy))
            local wx, wy, wzz = toWorld(x, y, wz + 0.01 * math.sin(t * 2 + du.ph))
            setElementPosition(du.obj, wx, wy, wzz)
            setElementRotation(du.obj, 0, 0, rzl + S.rot)
            if d < 45 and now - duckAt > 9000 and math.random() < 0.004 then
                duckAt = now
                snd3("duck", x, y, wz + 0.2, false, 0.7, 3, 30)
            end
        end
    end
    -- kiosk bell when walking up to the counter
    local kx, ky = toWorld(-5.6, 60, 0)
    if (px - kx) ^ 2 + (py - ky) ^ 2 < 7 and now - bellAt > 45000 then
        bellAt = now
        snd3("bell", -5.6, 60, 1.4, false, 0.8, 4, 28)
    end
end

-- ---------------------------------------------------------------------------------------------
-- info boards (text appears when standing in front of one)
-- ---------------------------------------------------------------------------------------------
local BOARD_TEXT = {
    "CENTRAL PARK",
    "Open every day 06:00 - 22:00",
    "",
    "Fountain  -  centre of the park",
    "Pond & bridge  -  east, ducks and lilies (swimming allowed)",
    "Playground  -  north-east: slide, swings, merry-go-round",
    "Kiosk  -  north-west, snacks and drinks",
    "Gazebo  -  west, a quiet place to sit  (/sit on any bench)",
}

local function boardHud()
    if not S.shown then return end
    local px, py, pz = getElementPosition(localPlayer)
    local near = false
    for _, key in ipairs({ "board1", "board2", "board3" }) do
        local p = PARK_POINTS[key]
        local x, y = toWorld(p[1], p[2], 0)
        if (px - x) ^ 2 + (py - y) ^ 2 < 9 then near = true break end
    end
    if not near then return end
    local sw, sh = guiGetScreenSize()
    local w, h = 560, 30 + #BOARD_TEXT * 22
    local x0, y0 = (sw - w) / 2, sh - h - 90
    dxDrawRectangle(x0, y0, w, h, tocolor(14, 40, 26, 215))
    dxDrawRectangle(x0, y0, w, 3, tocolor(230, 200, 90, 255))
    for i, line in ipairs(BOARD_TEXT) do
        local color = i == 1 and tocolor(240, 205, 100, 255) or tocolor(235, 240, 225, 255)
        dxDrawText(line, x0 + 16, y0 + 12 + (i - 1) * 22, x0 + w - 16, y0 + 34 + (i - 1) * 22, color, i == 1 and 1.25 or 1.0, "default-bold")
    end
end

-- ---------------------------------------------------------------------------------------------
-- /sit
-- ---------------------------------------------------------------------------------------------
local function standUp()
    if S.sitting then
        S.sitting = false
        triggerServerEvent("park:stand", resourceRoot)
        for _, k in ipairs({ "w", "a", "s", "d", "space" }) do unbindKey(k, "down", standUp) end
    end
end

local function sitCmd()
    if S.sitting then standUp() return end
    if not S.shown then return end
    if isPedInVehicle(localPlayer) then return end
    local px, py, pz = getElementPosition(localPlayer)
    local best, bd = nil, 2.3 ^ 2
    for _, b in ipairs(PARK_SIT) do
        local x, y = toWorld(b[1], b[2], 0)
        local d2 = (px - x) ^ 2 + (py - y) ^ 2
        if d2 < bd then best, bd = b, d2 end
    end
    if not best then say("Stand next to a bench and type /sit.", 255, 220, 140) return end
    local x, y, z = toWorld(best[1], best[2], best[4])
    -- the bench seat is 0.46 m high, a sitting ped's root is about 0.35 m above the seat
    local rz = best[3] + S.rot
    local r = math.rad(rz)
    local sx, sy = x + math.sin(r) * 0.05, y - math.cos(r) * 0.05
    triggerServerEvent("park:sit", resourceRoot, sx, sy, z + 0.80, rz)
    S.sitting = true
    setTimer(function()
        for _, k in ipairs({ "w", "a", "s", "d", "space" }) do bindKey(k, "down", standUp) end
    end, 600, 1)
end
addCommandHandler("sit", sitCmd)

-- ---------------------------------------------------------------------------------------------
-- night lights near the player (a few real point lights, recycled)
-- ---------------------------------------------------------------------------------------------
local function lightTick()
    if not S.shown or not createLight then return end
    if not isNight() then
        for i, l in ipairs(S.lights) do if isElement(l) then destroyElement(l) end S.lights[i] = nil end
        return
    end
    local px, py, pz = getElementPosition(localPlayer)
    local list = {}
    for _, L in ipairs(PARK_LAMPS) do
        local x, y, z = toWorld(L[1], L[2], L[3])
        local d2 = (px - x) ^ 2 + (py - y) ^ 2 + (pz - z) ^ 2
        if d2 < 55 ^ 2 then list[#list + 1] = { d2 = d2, x = x, y = y, z = z } end
    end
    table.sort(list, function(a, b) return a.d2 < b.d2 end)
    for i = 1, CFG.LIGHTS do
        local e = list[i]
        local l = S.lights[i]
        if e then
            if not (l and isElement(l)) then
                l = createLight(0, e.x, e.y, e.z - 0.3, 11, 255, 190, 110)
                S.lights[i] = l
            end
            if l then setElementPosition(l, e.x, e.y, e.z - 0.3) end
        elseif l and isElement(l) then
            destroyElement(l)
            S.lights[i] = nil
        end
    end
end

-- ---------------------------------------------------------------------------------------------
-- building / removing the park
-- ---------------------------------------------------------------------------------------------
local function clearPark()
    for _, t in ipairs(S.timers) do if isTimer(t) then killTimer(t) end end
    S.timers = {}
    for _, o in ipairs(S.objs) do if isElement(o) then destroyElement(o) end end
    S.objs = {}
    for _, s in ipairs(S.sounds) do if isElement(s) then destroySound(s) end end
    S.sounds = {}
    for _, e in ipairs(S.extras) do if isElement(e) then destroyElement(e) end end
    S.extras = {}
    for i, l in ipairs(S.lights) do if isElement(l) then destroyElement(l) end S.lights[i] = nil end
    removeEventHandler("onClientRender", root, onRender)
    removeEventHandler("onClientRender", root, boardHud)
    S.swings, S.ducks, S.merry, S.gate = {}, {}, nil, nil
    ambience = {}
    if S.sitting then standUp() end
    S.shown = false
end

local function createWaterSurface()
    local P = PARK_POND
    local pts = {}
    local n = 32
    for k = 0, n - 1 do
        local a = 2 * math.pi * k / n
        pts[k] = { P.cx + P.rx * P.k * math.cos(a), P.cy + P.ry * P.k * math.sin(a) }
    end
    pts[n] = pts[0]
    local ok = 0
    for k = 0, n - 1 do
        local x1, y1, z1 = toWorld(P.cx, P.cy, P.z)
        local x2, y2, z2 = toWorld(pts[k][1], pts[k][2], P.z)
        local x3, y3, z3 = toWorld(pts[k + 1][1], pts[k + 1][2], P.z)
        local w = createWater(x1, y1, z1, x2, y2, z2, x3, y3, z3)
        if w then S.extras[#S.extras + 1] = w ok = ok + 1 end
    end
    if ok == 0 then dbg("createWater failed") end
end

local function createFountainFx()
    local P = PARK_POINTS.fountain
    local x, y, z = toWorld(P[1], P[2], 4.2)
    local ok, fx = pcall(createEffect, "water_fountain", x, y, z, -90, 0, 0, 120)
    if ok and fx then S.extras[#S.extras + 1] = fx
    else dbg("water_fountain effect not available") end
end

local function build()
    local n, i = #PARK_OBJECTS, 0
    local r = S.rot
    local function step()
        if not S.shown then return end
        local stop = math.min(i + CFG.BATCH, n)
        while i < stop do
            i = i + 1
            local o = PARK_OBJECTS[i]
            local mid = S.ids[o[1]]
            if mid then
                local x, y, z = toWorld(o[2], o[3], o[4])
                local rz = o[5] + r
                local obj = createObject(mid, x, y, z, 0, 0, rz)
                if obj then
                    setObjectBreakable(obj, false)
                    local tag = o[6]
                    if tag ~= "gateL" and tag ~= "gateR" then setElementFrozen(obj, true) end   -- the gate leaves are moved with moveObject
                    S.objs[#S.objs + 1] = obj
                    if tag == "gateL" then S.gate = S.gate or { open = false, busy = false } S.gate.L = obj
                    elseif tag == "gateR" then S.gate = S.gate or { open = false, busy = false } S.gate.R = obj
                    elseif tag == "swing" then S.swings[#S.swings + 1] = { obj = obj, ph = #S.swings * 1.9, amp = 0.07, wx = x, wy = y }
                    elseif tag == "merry" then S.merry = { obj = obj, ang = 0, w = 0, wx = x, wy = y, wz = z }
                    elseif tag == "duck" then
                        local k = #S.ducks
                        S.ducks[#S.ducks + 1] = { obj = obj, ph = k * 2.1, sp = (0.10 + 0.03 * k) * (k % 2 == 0 and 1 or -1), a = 9.0 + 1.2 * k, b = 3.0 + 0.5 * k }
                    end
                end
            end
        end
        if i < n then
            track(setTimer(step, CFG.BATCH_MS, 1))
        else
            createWaterSurface()
            createFountainFx()
            local bx, by, bz = toWorld(0, 45, 0)
            local blip = createBlip(bx, by, bz, 0, 2, 40, 170, 60, 255, 0, 700)
            if blip then S.extras[#S.extras + 1] = blip end
            addEventHandler("onClientRender", root, onRender)
            addEventHandler("onClientRender", root, boardHud)
            track(setTimer(gateTick, 300, 0))
            track(setTimer(lightTick, 800, 0))
            startAmbience()
            say("Central Park is ready - " .. #S.objs .. " objects.  Commands: /sit  /parkwind  /hidepark (server)")
        end
    end
    S.shown = true
    step()
end

local function showPark(ox, oy, oz, rot)
    if S.pending then S.ox, S.oy, S.oz, S.rot = ox, oy, oz, rot S.pending = true return end      -- models still loading: use the newest position
    if S.shown then clearPark() end
    S.ox, S.oy, S.oz, S.rot = ox, oy, oz, rot
    say("building the park ...")
    S.pending = true
    loadModels(function(ok)
        local cancelled = S.pending == "cancel"
        S.pending = nil
        if cancelled then return end                      -- /hidepark arrived while the models were loading
        if not ok then say("could not load the park models: you need MTA 1.5.8-9.20716 or newer (engineRequestModel).", 255, 120, 120) return end
        build()
    end)
end

addEventHandler("park:show", resourceRoot, function(ox, oy, oz, rot)
    showPark(ox, oy, oz, rot)
end)

addEventHandler("park:hide", resourceRoot, function()
    if S.pending then S.pending = "cancel" end
    if S.shown then clearPark() end
end)

-- ---------------------------------------------------------------------------------------------
-- wind shader toggle
-- ---------------------------------------------------------------------------------------------
local WIND_TEX = { "pk_leaf_oak", "pk_leaf_birch", "pk_frond", "pk_flowers", "pk_grassblade", "pk_reed", "pk_lily" }

addCommandHandler("parkwind", function()
    if S.wind then
        for _, n in ipairs(WIND_TEX) do engineRemoveShaderFromWorldTexture(S.wind, n) end
        destroyElement(S.wind)
        S.wind = nil
        say("wind sway: OFF")
        return
    end
    local sh = dxCreateShader("wind.fx")
    if not sh then say("this graphics setup could not compile the wind shader.", 255, 150, 120) return end
    for _, n in ipairs(WIND_TEX) do engineApplyShaderToWorldTexture(sh, n) end
    S.wind = sh
    say("wind sway: ON  (/parkwind again to switch off)")
end)

addCommandHandler("parkinfo", function()
    say(string.format("models loaded: %s, objects: %d, sounds: %d", tostring(S.loaded), #S.objs, #S.sounds))
end)

-- ---------------------------------------------------------------------------------------------
-- start / stop
-- ---------------------------------------------------------------------------------------------
addEventHandler("onClientResourceStart", resourceRoot, function()
    math.randomseed(getTickCount())
    triggerServerEvent("park:request", resourceRoot)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    if S.wind and isElement(S.wind) then destroyElement(S.wind) end
    clearPark()
    freeModels()
end)
