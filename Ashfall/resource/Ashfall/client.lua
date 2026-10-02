-- Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA resource
-- ---------------------------------------------------------------------------------------------
-- client.lua - Ashfall, District Zero: a 340 m abandoned post-apocalyptic city with a ruined
--   central park (lake, dry fountain, paths, dense trees), abandoned cars, overgrown streets.
--   * every model is allocated with engineRequestModel("object") - no vanilla model is replaced
--   * ~2300 objects + 16 ground tiles are created in small batches when the server says "city:show"
--   * the lake gets swim-able createWater, the sky is fixed to a dull overcast afternoon, fog hides the edges
--   * procedural ambience: wind, distant rumble, crows / birds by day, crickets at night, creaking metal
--   * optional leaf-sway shader: /citywind (default OFF); cinematic grade (post.fx): /cityfx (default ON)
-- City frame (layout.lua): origin = centre of the central park, x east, y north, z = road level.
-- The server sends the world anchor with city:show (default: 900 m above the map; /showcity here = on the ground where you stand);
-- /cityz <m> trims the height.
-- ---------------------------------------------------------------------------------------------
local CFG = {
    PARENTS = { 1215, false },      -- parent model ids tried by engineRequestModel (false = MTA default)
    BATCH = 90,                     -- objects created per step
    BATCH_MS = 40,
    ANCHOR = { x = 0.0, y = 0.0, z = 900.0 },   -- fallback only: the server sends the real anchor with city:show
    SOUND = true,
    WIND_TEX = { "af_leaf", "af_leaf_dead", "af_weeds", "af_dead_grass", "af_ivy", "af_wire" },
    BIRD_EVERY = { 4000, 10000 },
}

local S = {
    loaded = false, loading = false, ids = {}, txd = {}, dffs = {}, cols = {},
    shown = false, zoff = 0, objs = {}, tiles = {}, water = {}, sounds = {},
    trees = {}, wind = nil, timers = {}, anchor = nil,
}
addEvent("city:show", true)
addEvent("city:hide", true)

-- ---------------------------------------------------------------------------------------------
local function toWorld(px, py, pz)
    local A = S.anchor or CFG.ANCHOR
    return A.x + px, A.y + py, A.z + S.zoff + pz
end

local function track(t) S.timers[#S.timers + 1] = t return t end
local function dbg(msg) outputDebugString("[Ashfall] " .. msg, 3) end
local function say(msg, r, g, b) outputChatBox("#c8b090[Ashfall] #ffffff" .. msg, r or 255, g or 255, b or 255, true) end
local function hourNow() local h, m = getTime() return h + m / 60 end
local function isNight() local h = hourNow() return h >= 20.0 or h < 5.5 end
local function isDay() local h = hourNow() return h >= 6.0 and h < 19.5 end
local function rnd(a, b) return a + (b - a) * math.random() end

local function cityDist()
    local px, py, pz = getElementPosition(localPlayer)
    local cx, cy = toWorld(0, 0, 0)
    return math.sqrt((px - cx) ^ 2 + (py - cy) ^ 2)
end

-- ---------------------------------------------------------------------------------------------
-- models
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
    local def = AF_MODELS[i]
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
    local i, n, failed = 0, #AF_MODELS, 0
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
    for _, id in pairs(S.ids) do engineFreeModel(id) end
    for _, e in pairs(S.dffs) do if isElement(e) then destroyElement(e) end end
    for _, e in pairs(S.cols) do if isElement(e) then destroyElement(e) end end
    for _, e in pairs(S.txd) do if isElement(e) then destroyElement(e) end end
    S.ids, S.dffs, S.cols, S.txd, S.loaded = {}, {}, {}, {}, false
end

-- ---------------------------------------------------------------------------------------------
-- ambience
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

local amb = {}

local function startAmbience()
    amb.wind = snd2("wind_loop", true, 0)
    amb.rumble = snd2("rumble_loop", true, 0)
    amb.crickets = {}
    for _, p in ipairs({ { -48, 20 }, { 48, 14 }, { -30, 48 }, { 20, 44 } }) do
        local s = snd3("crickets_loop", p[1], p[2], 0.5, true, 0, 4, 34)
        if s then amb.crickets[#amb.crickets + 1] = s end
    end
    track(setTimer(function()
        local d = cityDist()
        local inside = math.max(0, math.min(1, (240 - d) / 90))
        if amb.wind and isElement(amb.wind) then setSoundVolume(amb.wind, 0.34 * inside) end
        if amb.rumble and isElement(amb.rumble) then setSoundVolume(amb.rumble, 0.30 * inside) end
        local cv = isNight() and 0.5 or 0.0
        for _, s in ipairs(amb.crickets or {}) do if isElement(s) then setSoundVolume(s, cv * inside) end end
    end, 2000, 0))
    local function birdTick()
        if S.shown and CFG.SOUND and cityDist() < 120 and #S.trees > 0 then
            if isDay() then
                local px, py = getElementPosition(localPlayer)
                for _ = 1, 8 do
                    local t = S.trees[math.random(#S.trees)]
                    local wx, wy = toWorld(t[1], t[2], 0)
                    if (wx - px) ^ 2 + (wy - py) ^ 2 < 60 ^ 2 then
                        if math.random() < 0.35 then snd3("crow", t[1], t[2], t[3] + rnd(4, 8), false, rnd(0.4, 0.7), 6, 55)
                        else snd3("bird" .. math.random(4), t[1], t[2], t[3] + rnd(5, 9), false, rnd(0.45, 0.8), 6, 52) end
                        break
                    end
                end
            elseif math.random() < 0.4 then
                snd3("creak", rnd(-90, 90), rnd(-90, 90), rnd(6, 18), false, rnd(0.3, 0.55), 8, 70)
            end
        end
        if S.shown then track(setTimer(birdTick, math.random(CFG.BIRD_EVERY[1], CFG.BIRD_EVERY[2]), 1)) end
    end
    track(setTimer(birdTick, 2000, 1))
end

local function stopAmbience()
    for _, t in ipairs(S.timers) do if isTimer(t) then killTimer(t) end end     -- ambience timers must not outlive the city
    S.timers = {}
    for _, s in pairs(amb) do
        if type(s) == "table" then for _, e in ipairs(s) do if isElement(e) then destroyElement(e) end end
        elseif isElement(s) then destroyElement(s) end
    end
    amb = {}
    for _, s in ipairs(S.sounds) do if isElement(s) then destroyElement(s) end end
    S.sounds = {}
end

-- ---------------------------------------------------------------------------------------------
-- water (GTA water polygons need even integer coordinates)
-- ---------------------------------------------------------------------------------------------
local function createLake()
    local L = AF_LAKE
    local wz = (S.anchor or CFG.ANCHOR).z + S.zoff + L.z
    local step = 4
    local x0 = math.floor((L.cx - L.rx) / step) * step
    local x1 = math.ceil((L.cx + L.rx) / step) * step
    local y0 = math.floor((L.cy - L.ry) / step) * step
    local y1 = math.ceil((L.cy + L.ry) / step) * step
    local made = 0
    for gy = y0, y1 - step, step do
        for gx = x0, x1 - step, step do
            local mx, my = gx + step / 2 - L.cx, gy + step / 2 - L.cy
            if (mx * mx) / (L.rx * L.rx) + (my * my) / (L.ry * L.ry) < 0.92 then
                local a, b = toWorld(gx, gy, 0)
                local c, d = toWorld(gx + step, gy + step, 0)
                local w = createWater(a, b, wz, c, b, wz, a, d, wz, c, d, wz)
                if w then S.water[#S.water + 1] = { e = w, x = a, y = b, z = wz } made = made + 1 end
            end
        end
    end
    if made == 0 then dbg("createWater failed") end
    pcall(setWaterColor, 52, 74, 62, 210)
    return made
end

-- ---------------------------------------------------------------------------------------------
-- build / clear
-- ---------------------------------------------------------------------------------------------
local function spawnOne(o)
    local id = S.ids[o[1]]
    if not id then return nil end
    local x, y, z = toWorld(o[2], o[3], o[4])
    local ob = createObject(id, x, y, z, 0, 0, o[5])
    if ob and o[6] == "border" then          -- invisible border wall at the foot of the mountains: collision only
        setElementAlpha(ob, 0)
        return ob
    end
    if ob and setElementDoubleSided then setElementDoubleSided(ob, AF_MODELS[o[1]].alpha and true or false) end
    return ob
end

local function build(done)
    local i, n = 0, #AF_OBJECTS
    local function step()
        local stop = math.min(i + CFG.BATCH, n)
        while i < stop do
            i = i + 1
            S.objs[i] = spawnOne(AF_OBJECTS[i])
        end
        if i < n then
            setTimer(step, CFG.BATCH_MS, 1)
        else
            done()
        end
    end
    step()
end

local function buildGround()
    for i, def in ipairs(AF_MODELS) do
        if def.ox then
            local id = S.ids[i]
            if id then
                local x, y, z = toWorld(def.ox, def.oy, 0)
                local ob = createObject(id, x, y, z, 0, 0, 0)
                if ob then S.tiles[i] = { e = ob, def = def } end
            end
        end
    end
end

-- the sky is frozen at a pale overcast late afternoon: the game clock is stopped (a long minute) and a timer re-enforces it,
-- so the city never turns into a dark-blue night after a few real minutes.  Weather 15 = cloudy countryside (no heat haze).
local ATMO = { time = { 15, 30 }, weather = 15, fog = 470, far = 900, saved = nil, timer = nil }

local function enforceTime()
    pcall(setTime, ATMO.time[1], ATMO.time[2])
    pcall(setWeather, ATMO.weather)
    pcall(setHeatHaze, 0)
end

local function applyAtmosphere()
    if not ATMO.saved then
        local okw, w = pcall(getWeather)
        ATMO.saved = { weather = okw and tonumber(w) or 0 }
    end
    pcall(setSunSize, 0)
    pcall(setCloudsEnabled, false)
    pcall(setMinuteDuration, 2147483647)
    enforceTime()
    pcall(setFogDistance, ATMO.fog)
    pcall(setFarClipDistance, ATMO.far)
    pcall(setRainLevel, 0)
    pcall(setSkyGradient, 104, 116, 130, 170, 172, 170)
    if not (ATMO.timer and isTimer(ATMO.timer)) then
        ATMO.timer = setTimer(function() if S.shown then enforceTime() end end, 1000, 0)
    end
end

local function restoreAtmosphere()
    if ATMO.timer and isTimer(ATMO.timer) then killTimer(ATMO.timer) end
    ATMO.timer = nil
    pcall(setMinuteDuration, 1000)
    pcall(resetHeatHaze)
    pcall(resetFarClipDistance)
    if ATMO.saved then pcall(setWeather, ATMO.saved.weather) end
    ATMO.saved = nil
end

-- ---------------------------------------------------------------------------------------------
-- cinematic post-processing (post.fx) - /cityfx toggles it, it starts with the city
-- ---------------------------------------------------------------------------------------------
local FX = { shader = nil, src = nil, w = 0, h = 0 }

local function fxRender()
    if not FX.shader or not isElement(FX.shader) then return end
    dxUpdateScreenSource(FX.src)
    dxSetShaderValue(FX.shader, "ScreenTexture", FX.src)
    dxSetShaderValue(FX.shader, "gTime", (getTickCount() % 100000) / 1000)
    dxDrawImage(0, 0, FX.w, FX.h, FX.shader)
end

local function fxStop()
    if FX.shader then
        removeEventHandler("onClientHUDRender", root, fxRender)
        if isElement(FX.shader) then destroyElement(FX.shader) end
        if FX.src and isElement(FX.src) then destroyElement(FX.src) end
    end
    FX.shader, FX.src = nil, nil
end

local function fxStart()
    if FX.shader then return true end
    local sw, sh = guiGetScreenSize()
    local shader = dxCreateShader("post.fx")
    if not shader then return false end
    local src = dxCreateScreenSource(sw, sh)
    if not src then destroyElement(shader) return false end
    FX.shader, FX.src, FX.w, FX.h = shader, src, sw, sh
    dxSetShaderValue(shader, "gPix", 1 / sw, 1 / sh)
    addEventHandler("onClientHUDRender", root, fxRender)
    return true
end

addCommandHandler("cityfx", function()
    if FX.shader then fxStop() say("cinematic grade: OFF")
    elseif fxStart() then say("cinematic grade: ON  (/cityfx again to switch off)")
    else say("this graphics setup could not compile the grade shader.", 255, 150, 120) end
end)

local clearCity

local function thaw()
    setElementFrozen(localPlayer, false)
end

local function showCity(zoff, ax, ay, az)
    if S.shown then clearCity() end
    S.zoff = zoff or 0
    if ax and ay and az then S.anchor = { x = ax, y = ay, z = az } end
    local near = cityDist() < 400
    if near then setElementFrozen(localPlayer, true) end       -- hold the player in the air until the ground collision exists
    loadModels(function(ok)
        if not ok then
            if near then thaw() end
            say("the city could not be loaded (see debugscript 3).", 255, 150, 120)
            return
        end
        S.shown = true
        buildGround()
        build(function()
            if near then setTimer(thaw, 1500, 1) end
            createLake()
            S.trees = {}
            for _, o in ipairs(AF_OBJECTS) do
                if o[6] == "tree" then S.trees[#S.trees + 1] = { o[2], o[3], o[4] } end
            end
            applyAtmosphere()
            fxStart()
            -- the server (zombies.lua) spawns the infected once the ground collision exists
            track(setTimer(function() if S.shown then triggerServerEvent("city:ready", resourceRoot) end end, 2500, 1))
            startAmbience()
            say("District Zero is in front of you - " .. #S.objs .. " objects.  /hidecity removes it, /cityz <m> trims the height, /citywind toggles leaf sway.")
        end)
    end)
end

function clearCity()
    for _, e in pairs(S.objs) do if e and isElement(e) then destroyElement(e) end end
    for _, t in pairs(S.tiles) do if t and isElement(t.e) then destroyElement(t.e) end end
    for _, w in pairs(S.water) do if w and isElement(w.e) then destroyElement(w.e) end end
    S.objs, S.tiles, S.water, S.trees = {}, {}, {}, {}
    stopAmbience()
    fxStop()
    pcall(resetSkyGradient)
    pcall(resetFogDistance)
    restoreAtmosphere()
    pcall(resetSunSize)
    pcall(setCloudsEnabled, true)
    if S.wind then
        for _, n in ipairs(CFG.WIND_TEX) do engineRemoveShaderFromWorldTexture(S.wind, n) end
        destroyElement(S.wind)
        S.wind = nil
    end
    S.shown = false
end

addEventHandler("city:show", resourceRoot, function(zoff, ax, ay, az) showCity(zoff, ax, ay, az) end)
addEventHandler("city:hide", resourceRoot, function() clearCity() say("District Zero removed.") end)

-- reposition everything after /cityz
addEvent("city:zoff", true)
addEventHandler("city:zoff", resourceRoot, function(dz)
    if not S.shown then S.zoff = S.zoff + dz return end
    S.zoff = S.zoff + dz
    for k, e in pairs(S.objs) do
        if e and isElement(e) then
            local o = AF_OBJECTS[k]
            local x, y, z = toWorld(o[2], o[3], o[4])
            setElementPosition(e, x, y, z)
        end
    end
    for _, t in pairs(S.tiles) do
        if t and isElement(t.e) then
            local x, y, z = toWorld(t.def.ox, t.def.oy, 0)
            setElementPosition(t.e, x, y, z)
        end
    end
    for _, w in pairs(S.water) do
        if w and isElement(w.e) then
            w.z = w.z + dz
            setElementPosition(w.e, w.x, w.y, w.z)
        end
    end
end)

-- safety net for the sky city: anyone who somehow steps off the edge is brought back to the park entrance
setTimer(function()
    if not S.shown or not S.anchor or S.anchor.z < 300 then return end
    local px, py, pz = getElementPosition(localPlayer)
    local cx, cy, cz = toWorld(0, 0, 0)
    local dx, dy = math.abs(px - cx), math.abs(py - cy)
    -- fell off the wasteland (or walked off its far rim): back to the park entrance
    if (pz < cz - 40 and dx < 700 and dy < 700) or ((dx > 500 or dy > 500) and dx < 700 and dy < 700 and pz < cz + 30) then
        local P = AF_POINTS.spawn
        local x, y, z = toWorld(P[1], P[2], P[3] + 1.0)
        setElementPosition(localPlayer, x, y, z)
        setElementVelocity(localPlayer, 0, 0, 0)
    end
end, 1000, 0)

-- ---------------------------------------------------------------------------------------------
-- wind shader toggle
-- ---------------------------------------------------------------------------------------------
addCommandHandler("citywind", function()
    if S.wind then
        for _, n in ipairs(CFG.WIND_TEX) do engineRemoveShaderFromWorldTexture(S.wind, n) end
        destroyElement(S.wind)
        S.wind = nil
        say("wind sway: OFF")
        return
    end
    local sh = dxCreateShader("wind.fx")
    if not sh then say("this graphics setup could not compile the wind shader.", 255, 150, 120) return end
    for _, n in ipairs(CFG.WIND_TEX) do engineApplyShaderToWorldTexture(sh, n) end
    S.wind = sh
    say("wind sway: ON  (/citywind again to switch off)")
end)

-- ---------------------------------------------------------------------------------------------
addEventHandler("onClientResourceStart", resourceRoot, function()
    triggerServerEvent("city:request", resourceRoot)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    clearCity()
    freeModels()
    for _, t in ipairs(S.timers) do if isTimer(t) then killTimer(t) end end
end)
