--[[
  NextGenPoliceDepartment - shader manager.

  * One shader instance per (texture, interior|exterior) pair, created lazily the first time a model that
    uses the texture is shown, never per frame.  Instances share DDS map textures through a cache.
  * Applied with engineApplyShaderToWorldTexture(shader, textureName, element) on OUR objects only, so
    no GTA world surface is touched.
  * Failure policy: if dxCreateShader fails or only the fixed-function "fallback" technique validates,
    that .fx file is marked failed for the session (no retry loop) and its surfaces render with the plain
    prelit TXD look.  Missing DDS maps do the same for that texture.
  * Environment values (wetness, rain, sun, sky) are pushed at most 4x per second and only when changed.
]]

NGPD.shaders = { instances = {}, list = {}, texCache = {}, failedFile = {}, enabled = false, profile = nil, stats = { created = 0, failed = 0, applied = 0 } }
local S = NGPD.shaders
local ENV_KEYS = { "gWetness", "gRain", "gDayFactor", "gSunDir", "gSunColor", "gSkyColor", "gIndoorEnv" }

local function tex(path)
    if not path then return nil end
    local t = S.texCache[path]
    if t == nil then
        t = dxCreateTexture(path, "dxt5", true, "wrap") or false
        if not t then outputDebugString("[NGPD] dxCreateTexture failed: " .. path, 2) end
        S.texCache[path] = t
    end
    return t or nil
end

local function getShader(texName, interior)
    local key = texName .. (interior and "#i" or "#e")
    local inst = S.instances[key]
    if inst ~= nil then return inst or nil end
    local m = NGPD_MATERIALS.textures[texName]
    local p = S.profile
    if not m or not p then S.instances[key] = false return nil end
    if S.failedFile[m.shader] then S.instances[key] = false return nil end
    local maps = m.maps[p.maps] or m.maps.medium
    local nTex, sTex = maps and tex(maps.normal), maps and tex(maps.surface)
    if not (nTex and sTex) then S.instances[key] = false; S.stats.failed = S.stats.failed + 1 return nil end
    -- maxDistance 0 (no limit): MTA's maxDistance is evaluated per OBJECT and our chunks are 20-90 m wide, so a
    -- limit made whole wings flip between shaded and plain at once ("popping", runs #4/#5).  The quality
    -- distance is now a per-pixel fade inside the shader (gFadeStart..gFadeEnd -> exactly the plain look).
    local sh, technique = dxCreateShader("shaders/" .. m.shader .. ".fx", 0, 0, false, "object")
    if not sh then
        S.failedFile[m.shader] = true
        S.instances[key] = false
        S.stats.failed = S.stats.failed + 1
        outputDebugString("[NGPD] dxCreateShader failed for " .. m.shader .. ".fx - using plain textures", 2)
        return nil
    end
    if technique == "fallback" then
        -- no programmable technique validated on this GPU: keep the cheaper plain path
        destroyElement(sh)
        S.failedFile[m.shader] = true
        S.instances[key] = false
        outputDebugString("[NGPD] " .. m.shader .. ".fx: only the fixed-function fallback validated - shader disabled", 2)
        return nil
    end
    dxSetShaderValue(sh, "sNormalTex", nTex)
    dxSetShaderValue(sh, "sSurfaceTex", sTex)
    dxSetShaderValue(sh, "gWetFactor", m.wetFactor)
    dxSetShaderValue(sh, "gPorosity", m.porosity)
    dxSetShaderValue(sh, "gPuddles", m.puddles)
    dxSetShaderValue(sh, "gSpec", m.spec)
    dxSetShaderValue(sh, "gMetallic", m.metallic)
    dxSetShaderValue(sh, "gEmissive", m.emissive)
    dxSetShaderValue(sh, "gNormalScale", m.normalScale * (p.normalScale or 1))
    dxSetShaderValue(sh, "gReflectScale", p.reflectScale or 1)
    dxSetShaderValue(sh, "gInterior", interior and 1 or 0)
    local fadeEnd = p.shaderDistance or 60
    dxSetShaderValue(sh, "gFadeStart", fadeEnd * 0.55)
    dxSetShaderValue(sh, "gFadeEnd", fadeEnd)
    local rec = { shader = sh, technique = technique, interior = interior, texture = texName, last = {} }
    S.instances[key] = rec
    S.list[#S.list + 1] = rec
    S.stats.created = S.stats.created + 1
    S.pushEnv(rec, true)
    return rec
end

function S.applyToElement(element, modelName, interior)
    if not S.enabled then return end
    local texs = NGPD_MATERIALS.modelTextures[modelName]
    if not texs then return end
    for _, t in ipairs(texs) do
        local rec = getShader(t, interior)
        if rec and engineApplyShaderToWorldTexture(rec.shader, t, element) then
            S.stats.applied = S.stats.applied + 1
        end
    end
end

------------------------------------------------------------------ environment
local env = {}

local function smooth(e0, e1, x) local t = NGPD.clamp((x - e0) / (e1 - e0), 0, 1) return t * t * (3 - 2 * t) end

function S.computeEnv()
    local h, m = getTime()
    local t = h + m / 60
    -- sun path: rises in the east (+X) at 06:00, south (-Y) at noon, sets west at 18:00
    local day = math.sin((t - 6) / 12 * math.pi)
    local az = (t - 6) / 12 * math.pi
    local elev = math.max(day, 0.05) * math.rad(70)
    env.gSunDir = { math.cos(az) * math.cos(elev), -math.sin(az) * math.cos(elev) * 0.6, math.sin(elev) }
    env.gDayFactor = smooth(0.0, 0.2, day)
    local sr, sg, sb = getSunColor()
    if sr then env.gSunColor = { sr / 255, sg / 255, sb / 255 } else env.gSunColor = { 1, 0.95, 0.88 } end
    local r1, g1, b1, r2, g2, b2 = getSkyGradient()
    if r1 then
        env.gSkyColor = { (r1 + r2) / 510, (g1 + g2) / 510, (b1 + b2) / 510 }
    else
        env.gSkyColor = { 0.55, 0.62, 0.72 }
    end
    env.gIndoorEnv = { 0.80, 0.80, 0.82 }
    env.gWetness = (NGPD.wet and S.profile and S.profile.wetness) and NGPD.wet.value or 0
    env.gRain = math.min(1, (getRainLevel() or 0) / 0.6)
end

local function differs(a, b)
    if type(a) == "table" then
        if type(b) ~= "table" then return true end
        for i = 1, #a do if math.abs(a[i] - b[i]) > 0.004 then return true end end
        return false
    end
    return b == nil or math.abs(a - b) > 0.002
end

function S.pushEnv(rec, force)
    for _, k in ipairs(ENV_KEYS) do
        local v = env[k]
        if v ~= nil and (force or differs(v, rec.last[k])) then
            if type(v) == "table" then dxSetShaderValue(rec.shader, k, v[1], v[2], v[3]) else dxSetShaderValue(rec.shader, k, v) end
            rec.last[k] = type(v) == "table" and { v[1], v[2], v[3] } or v
        end
    end
end

local function tick()
    if not S.enabled then return end
    S.computeEnv()
    for _, rec in ipairs(S.list) do
        if isElement(rec.shader) then S.pushEnv(rec, false) end
    end
end

------------------------------------------------------------------ lifecycle
function S.enable(profile)
    S.disable()
    S.profile = profile
    S.enabled = true
    S.computeEnv()
    S.timer = setTimer(tick, NGPD_CONFIG.wet.updateMs, 0)
end

function S.disable()
    if isTimer(S.timer) then killTimer(S.timer) end
    S.timer = nil
    for _, rec in ipairs(S.list) do
        if isElement(rec.shader) then destroyElement(rec.shader) end   -- also removes its world-texture applications
    end
    for _, t in pairs(S.texCache) do if t and isElement(t) then destroyElement(t) end end
    S.instances, S.list, S.texCache = {}, {}, {}
    S.enabled = false
    S.stats = { created = 0, failed = 0, applied = 0 }
    -- failedFile intentionally survives quality switches: a failing .fx is not retried this session
end

addCommandHandler("ngpd_shaders", function()
    local tech = {}
    for _, rec in ipairs(S.list) do tech[rec.technique or "?"] = (tech[rec.technique or "?"] or 0) + 1 end
    local parts = {}
    for k, v in pairs(tech) do parts[#parts + 1] = k .. "=" .. v end
    local failed = {}
    for k in pairs(S.failedFile) do failed[#failed + 1] = k end
    outputChatBox(string.format("[NGPD] shaders %s | instances %d | applications %d | techniques: %s | failed files: %s | maps %d",
        S.enabled and "ON" or "OFF", #S.list, S.stats.applied, table.concat(parts, ", "), #failed > 0 and table.concat(failed, ",") or "none",
        (function() local n = 0 for _, t in pairs(S.texCache) do if t then n = n + 1 end end return n end)()), 150, 200, 255)
end)

addEventHandler("onClientResourceStop", resourceRoot, function() S.disable() end)
