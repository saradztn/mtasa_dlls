-- ---------------------------------------------------------------------------------------------
-- atmo.lua - AAA environment system for NightCity: time-of-day + weather presets, smoothly
--   interpolated. Drives GTA weather/clouds, sky gradient, sun/moon colour & size, fog,
--   far clip, wind, rain, the low-cost post grade and the wet-asphalt shader. Pure client side.
-- Public API:
--   NC_ATMO.setWeather("sunny"|"partly"|"cloudy"|"overcast"|"foggy"|"mist"|"drizzle"|"rain"|"storm"|"afterrain"|"clearnight")
--   NC_ATMO.setRainOverride(value)    -- optional manual rain level 0..1; nil releases the override
--   NC_ATMO.setTime(hour, minute)     -- or NC_ATMO.setPreset(name); manually set time stops the cycle
--   NC_ATMO.setCycle(on, speed)       -- seconds per in-game hour (default 60; full day in 24 minutes)
--   NC_ATMO.getState() -> table; NC_ATMO.tick(now) is called each frame while the city is shown
-- Exposed to the shaders: gWet/gSheen/gSunAlt on wet.fx and gGain/gTint on post.fx.
-- ---------------------------------------------------------------------------------------------
local TAU = math.pi * 2
local function lerp(a, b, t)
    a = tonumber(a) or 0
    b = tonumber(b) or 0
    t = tonumber(t) or 0
    return a + (b - a) * t
end
local function clamp(v, lo, hi) if v < lo then return lo elseif v > hi then return hi end return v end
local function smooth(t) t = clamp(t, 0, 1) return t * t * (3 - 2 * t) end
local function lerpC(A, B, t)
    A = A or {0,0,0}; B = B or {0,0,0}
    return { lerp(A[1] or 0, B[1] or 0, t), lerp(A[2] or 0, B[2] or 0, t), lerp(A[3] or 0, B[3] or 0, t) }
end
local function cMul(c, k) return { (c[1] or 0) * k, (c[2] or 0) * k, (c[3] or 0) * k } end
local function cToK(c) return math.max(0,math.min(255,(c[1] or 0) * 255)), math.max(0,math.min(255,(c[2] or 0) * 255)), math.max(0,math.min(255,(c[3] or 0) * 255)) end

-- colours are linear-ish 0..1 triplets; they will be multiplied by the post-fx grade.
-- times are decimal hours 0..24.
local SUN_CURVE = {
    -- h,  sunTop skyTop skyBot fogCol                 sunCol                sunSize moonCol               moonSz  ambTint              far   fogDensity  cloudBright  starsB
    { 0.0, 0.00, {.015,.020,.045}, {.040,.045,.080}, {.055,.060,.095}, {.95,.70,.50}, 0.0, {.85,.90,1.0}, 0.0, {.50,.54,.70}, 1400, 0.85, 0.0, 1.0 }, -- midnight
    { 4.0, 0.00, {.060,.065,.110}, {.160,.130,.160}, {.190,.150,.180}, {1.0,.65,.45}, 0.0, {.85,.90,1.0}, 0.4, {.55,.50,.65}, 1500, 0.70, 0.0, 0.6 }, -- deep night
    { 5.2, 0.00, {.220,.160,.240}, {.550,.290,.250}, {.600,.320,.280}, {1.0,.55,.30}, 0.0, {.85,.90,1.0}, 0.0, {.70,.55,.60}, 1800, 0.55, 0.0, 0.0 }, -- pre-dawn
    { 6.0, 0.05, {.480,.340,.340}, {.900,.520,.320}, {.850,.500,.360}, {1.0,.60,.30}, 0.0, {.85,.90,1.0}, 0.0, {.95,.75,.65}, 2400, 0.35, 0.2, 0.0 }, -- dawn
    { 6.8, 0.25, {.650,.520,.520}, {1.00,.680,.440}, {.950,.700,.550}, {1.0,.78,.50}, 1.2, {.00,.00,.00}, 0.0, {1.1, .95,.80}, 3200, 0.20, 0.6, 0.0 }, -- sunrise
    { 8.0, 0.65, {.470,.630,.900}, {.700,.780,.950}, {.720,.780,.900}, {1.0,.92,.75}, 2.2, {.00,.00,.00}, 0.0, {1.05,1.00,.95}, 4000, 0.12, 0.9, 0.0 }, -- morning
    { 11.0, 1.00, {.340,.560,.920}, {.650,.760,.970}, {.700,.790,.930}, {1.0,.98,.92}, 2.6, {.00,.00,.00}, 0.0, {1.00,1.00,1.00}, 4400, 0.08, 1.0, 0.0 }, -- late morning
    { 13.0, 1.00, {.300,.530,.940}, {.620,.740,.980}, {.670,.770,.950}, {1.0,1.00,.96}, 2.7, {.00,.00,.00}, 0.0, {1.00,1.02,1.03}, 4600, 0.07, 1.0, 0.0 }, -- noon
    { 16.0, 0.70, {.330,.540,.910}, {.660,.720,.900}, {.710,.740,.860}, {1.0,.95,.82}, 2.2, {.00,.00,.00}, 0.0, {1.02,1.00,.96}, 4000, 0.10, 0.95,0.0 }, -- afternoon
    { 17.5, 0.35, {.460,.440,.700}, {.920,.620,.420}, {.870,.650,.500}, {1.0,.72,.40}, 1.4, {.00,.00,.00}, 0.0, {1.10,.92,.75}, 3200, 0.18, 0.7,  0.0 }, -- golden
    { 18.5, 0.10, {.420,.280,.400}, {.880,.420,.260}, {.780,.420,.320}, {1.0,.55,.28}, 0.5, {.70,.75,.90}, 0.0, {1.00,.70,.55}, 2200, 0.30, 0.3, 0.0 }, -- sunset
    { 19.5, 0.00, {.200,.150,.260}, {.520,.270,.290}, {.450,.290,.320}, {1.0,.45,.25}, 0.0, {.85,.90,1.0}, 0.2, {.75,.60,.65}, 1800, 0.50, 0.0, 0.0 }, -- dusk
    { 21.0, 0.00, {.050,.070,.160}, {.130,.130,.220}, {.120,.140,.220}, {.95,.65,.40}, 0.0, {.85,.90,1.0}, 0.6, {.55,.58,.72}, 1500, 0.70, 0.0, 0.3 }, -- early night
    { 23.0, 0.00, {.020,.028,.060}, {.060,.060,.110}, {.065,.070,.120}, {.95,.70,.50}, 0.0, {.85,.90,1.0}, 0.0, {.50,.54,.70}, 1300, 0.85, 0.0, 1.0 }, -- late night
    { 24.0, 0.00, {.015,.020,.045}, {.040,.045,.080}, {.055,.060,.095}, {.95,.70,.50}, 0.0, {.85,.90,1.0}, 0.0, {.50,.54,.70}, 1400, 0.85, 0.0, 1.0 },
}

-- weather multipliers applied on top of the time curve.  Each entry is tuned to look right at noon;
-- at night the system softens everything (less cloud contrast, no sun glare, etc.).
-- keys: sky/fog tint, fog strength, far distance, native-cloud toggle, rain amount,
--       wet-road target, wind, heat haze and a subtle wet-road sheen.
local W = {
    sunny =     { sky = {1.00,1.00,1.00}, fog = {1.00,1.00,1.00}, fogA = 0.0, far = 1.00, clouds = true,  rain = 0.00, wet = 0.00, wind = {0.2,0.1}, hz = 0, haz = {0,0,0},       sheen = 0.0, stars = 1.0 },
    partly =    { sky = {0.98,0.99,1.02}, fog = {0.98,0.99,1.02}, fogA = 0.10, far = 0.92, clouds = true,  rain = 0.00, wet = 0.00, wind = {0.6,0.2}, hz = 0, haz = {0,0,0},       sheen = 0.1, stars = 0.6 },
    cloudy =    { sky = {0.90,0.92,0.98}, fog = {0.92,0.93,0.98}, fogA = 0.30, far = 0.70, clouds = true,  rain = 0.00, wet = 0.00, wind = {1.2,0.4}, hz = 0, haz = {.03,.03,.04},  sheen = 0.25,stars = 0.0 },
    overcast =  { sky = {0.82,0.85,0.92}, fog = {0.85,0.87,0.92}, fogA = 0.45, far = 0.55, clouds = true,  rain = 0.00, wet = 0.05, wind = {1.8,0.5}, hz = 0, haz = {.05,.05,.06},  sheen = 0.30,stars = 0.0 },
    foggy =     { sky = {0.95,0.95,0.95}, fog = {0.97,0.97,0.97}, fogA = 0.75, far = 0.22, clouds = false, rain = 0.00, wet = 0.10, wind = {0.2,0.1}, hz = 0, haz = {.12,.12,.12},  sheen = 0.20,stars = 0.0 },
    mist =      { sky = {0.98,0.97,0.96}, fog = {0.98,0.97,0.96}, fogA = 0.55, far = 0.40, clouds = false, rain = 0.00, wet = 0.08, wind = {0.1,0.0}, hz = 0, haz = {.08,.08,.07},  sheen = 0.15,stars = 0.0 },
    drizzle =   { sky = {0.85,0.88,0.94}, fog = {0.87,0.89,0.94}, fogA = 0.45, far = 0.55, clouds = true,  rain = 0.25, wet = 0.45, wind = {1.4,0.4}, hz = 0, haz = {.04,.04,.05},  sheen = 0.40,stars = 0.0 },
    rain =      { sky = {0.78,0.81,0.88}, fog = {0.80,0.83,0.88}, fogA = 0.55, far = 0.45, clouds = true,  rain = 0.50, wet = 0.75, wind = {2.2,0.6}, hz = 0, haz = {.05,.05,.06},  sheen = 0.55,stars = 0.0 },
    storm =     { sky = {0.65,0.68,0.78}, fog = {0.70,0.73,0.80}, fogA = 0.65, far = 0.35, clouds = true,  rain = 0.85, wet = 0.90, wind = {3.5,1.0}, hz = 0, haz = {.07,.07,.08},  sheen = 0.65,stars = 0.0 },
    afterrain = { sky = {0.92,0.94,1.00}, fog = {0.90,0.92,0.98}, fogA = 0.30, far = 0.80, clouds = true,  rain = 0.00, wet = 0.45, wind = {0.6,0.2}, hz = 0, haz = {.03,.03,.04},  sheen = 0.55,stars = 0.2 },
    clearnight ={ sky = {1.00,1.00,1.00}, fog = {1.00,1.00,1.00}, fogA = 0.10, far = 1.00, clouds = false, rain = 0.00, wet = 0.00, wind = {0.2,0.1}, hz = 0, haz = {0,0,0},       sheen = 0.0, stars = 1.0 },
}

-- Native GTA:SA weather IDs provide the real cloud/timecyc layer underneath our custom sky.
-- setWeatherBlended keeps transitions smooth; atmo.lua still controls the exact sky, fog and rain.
local NATIVE_WEATHER = {
    sunny = 0, partly = 1, cloudy = 4, overcast = 7, foggy = 9, mist = 9,
    drizzle = 8, rain = 8, storm = 16, afterrain = 4, clearnight = 1,
}

local M = {
    weather = "sunny",
    timeH = 12.0,                 -- decimal hours 0..24
    cycle = true,
    cycleSpeed = 60.0,            -- real seconds per in-game hour; a full day takes 24 minutes
    lerped = nil,                 -- current interpolated state
    lightning = 0,                -- >0 means flash is active (seconds remaining)
    rainOverride = nil,           -- optional /ncrain override, nil means follow the weather preset
    nativeWeather = nil,
    stars = 0,
}

local function setNativeWeather(id)
    id = tonumber(id)
    if not id or id == M.nativeWeather then return end
    local ok, result = false, false
    if type(setWeatherBlended) == "function" then
        ok, result = pcall(setWeatherBlended, id)
    end
    if not ok or result == false then
        if type(setWeather) == "function" then ok, result = pcall(setWeather, id) end
    end
    if ok and result ~= false then M.nativeWeather = id end
end



function M.getState()
    local h = (M.timeH or 12) % 24
    if h < 0 then h = h + 24 end
    local a, b, t = SUN_CURVE[1], SUN_CURVE[#SUN_CURVE], 0
    for k = 1, #SUN_CURVE - 1 do
        if SUN_CURVE[k + 1][1] >= h - 1e-6 then
            a, b = SUN_CURVE[k], SUN_CURVE[k + 1]
            local denom = (b[1] - a[1])
            t = denom > 1e-6 and smooth((h - a[1]) / denom) or 0
            break
        end
    end
    local st = {
        sunAlt    = lerp(a[2], b[2], t),
        skyTop    = lerpC(a[3], b[3], t),
        skyBot    = lerpC(a[4], b[4], t),
        fogCol    = lerpC(a[5], b[5], t),
        sunCol    = lerpC(a[6], b[6], t),
        sunSz     = lerp(a[7], b[7], t),
        moonCol   = lerpC(a[8], b[8], t),
        moonSz    = lerp(a[9], b[9], t),
        amb       = lerpC(a[10], b[10], t),
        far       = lerp(a[11], b[11], t),
        fogD      = lerp(a[12], b[12], t),
        cloudBr   = lerp(a[13], b[13], t),
        stars     = lerp(a[14], b[14], t),
    }
    local w = W[M.weather] or W.sunny
    -- weather multipliers.  At night, cloud brightness fades to sky darkness, fog tints shift, rain stays.
    local night = 1 - st.sunAlt
    st.skyTop = { st.skyTop[1] * w.sky[1], st.skyTop[2] * w.sky[2], st.skyTop[3] * w.sky[3] }
    st.skyBot = { st.skyBot[1] * w.sky[1], st.skyBot[2] * w.sky[2], st.skyBot[3] * w.sky[3] }
    st.fogCol = lerpC(st.fogCol, { 0.18, 0.20, 0.25 }, night * 0.5)
    st.fogCol = { st.fogCol[1] * w.fog[1], st.fogCol[2] * w.fog[2], st.fogCol[3] * w.fog[3] }
    st.fogD   = clamp(st.fogD + w.fogA * (0.4 + 0.6 * st.sunAlt), 0.05, 0.95)
    st.far    = st.far * w.far
    st.rain   = w.rain * (0.8 + 0.2 * st.sunAlt)
    st.wet    = w.wet
    st.wind   = { w.wind[1], w.wind[2] }
    st.sheen  = w.sheen * (0.6 + 0.4 * st.sunAlt)
    if M.rainOverride ~= nil then
        -- Manual rain controls the visible rain and road film even when the chosen preset is dry.
        st.rain = clamp(M.rainOverride, 0, 1)
        st.wet = st.rain * 0.95
        st.sheen = st.rain * 0.60
    end
    st.haz    = w.haz
    st.clouds = w.clouds
    st.cloudBr = st.cloudBr * w.sky[1] * (0.3 + 0.7 * st.sunAlt)
    st.stars  = st.stars * w.stars
    st.hz     = w.hz
    st.weather = M.weather
    st.timeH  = M.timeH
    return st
end

local function smoothStep()
    if not M.lerped then M.lerped = M.getState() return end
    local target = M.getState()
    local cur = M.lerped
    local k = 0.12                                 -- ~300 ms to 90%, feels natural
    for _, key in ipairs({"sunAlt", "sunSz", "moonSz", "far", "fogD", "cloudBr", "stars", "rain", "wet", "sheen", "hz"}) do
        cur[key] = lerp(cur[key], target[key], k)
    end
    for _, key in ipairs({"skyTop", "skyBot", "fogCol", "sunCol", "moonCol", "amb", "wind", "haz"}) do
        cur[key] = lerpC(cur[key], target[key], k)
    end
    cur.clouds = target.clouds
    cur.weather = target.weather
    cur.timeH = target.timeH
    if M.lightning > 0 then
        M.lightning = M.lightning - 0.016          -- advances each frame tick
    end
end

function M.setWeather(name)
    name = string.lower(tostring(name or ""))
    if not W[name] then return false end
    M.weather = name
    M.rainOverride = nil
    setNativeWeather(NATIVE_WEATHER[name])
    return true
end

function M.setRainOverride(value)
    if value == nil then
        M.rainOverride = nil
    else
        M.rainOverride = clamp(tonumber(value) or 0, 0, 1)
    end
    -- A manual shower gets a cloudy native backdrop; returning to 0 restores the selected preset.
    local native = (M.rainOverride and M.rainOverride > 0.001) and 4 or NATIVE_WEATHER[M.weather]
    setNativeWeather(native)
    return true
end

local TIME_PRESETS = {
    dawn = 6.0, sunrise = 6.7, morning = 8.5, noon = 13.0, afternoon = 16.0,
    golden = 17.3, sunset = 18.5, dusk = 19.5, night = 22.0, midnight = 0.5,
    clear = 12.0,
}

function M.setTime(h, m)
    if type(h) == "string" then
        h = TIME_PRESETS[string.lower(h)]
        if not h then return false end
    end
    M.timeH = (tonumber(h) or 12) + (tonumber(m) or 0) / 60
    M.timeH = M.timeH % 24
    M.cycle = false
    return true
end

function M.setPreset(name)
    if type(name) ~= "string" then return false end
    return M.setTime(name)
end

function M.setCycle(on, speed)
    M.cycle = on and true or false
    local secondsPerHour = tonumber(speed)
    if secondsPerHour then M.cycleSpeed = clamp(secondsPerHour, 5, 3600) end
end

local weatherNames = {}
for k in pairs(W) do weatherNames[#weatherNames + 1] = k end
table.sort(weatherNames)
M.weatherNames = weatherNames

-- hooks that client.lua installs after loading this file
_G.NC_ATMO_WET    = nil       -- wet shader handle (set by client.lua)
_G.NC_ATMO_POST   = nil       -- post shader handle
_G.NC_ATMO_SFX    = nil       -- function(name, loop, vol) -> sound  (short sfx player)

local function _wet()  return _G.NC_ATMO_WET  end
local function _post() return _G.NC_ATMO_POST end
local function _sfx(n, l, v) if _G.NC_ATMO_SFX then _G.NC_ATMO_SFX(n, l, v) end end

local function apply(st)
    -- Sun: MTA's setTime drives the vanilla sun direction; we push hour/minute and then override sun colour.
    local h = math.floor(st.timeH) % 24
    local m = math.floor((st.timeH - math.floor(st.timeH)) * 60) % 60
    pcall(setTime, h, m)
    -- Sky gradient (zenith / horizon): GTA expects bytes 0..255.
    local zr, zg, zb = cToK(st.skyTop)
    local hr, hg, hb = cToK(st.skyBot)
    if M.lightning > 0 then
        local f = M.lightning
        zr, zg, zb = math.min(255, zr + 180 * f), math.min(255, zg + 185 * f), math.min(255, zb + 200 * f)
        hr, hg, hb = math.min(255, hr + 200 * f), math.min(255, hg + 200 * f), math.min(255, hb + 210 * f)
    end
    pcall(setSkyGradient, zr, zg, zb, hr, hg, hb)
    -- Sun / moon
    local sr, sg, sb = cToK(st.sunCol)
    local mr, mg, mb = cToK(st.moonCol)
    pcall(setSunColor, sr, sg, sb, mr, mg, mb)
    pcall(setSunSize, st.sunSz)
    -- tunnel check BEFORE fog/far
    local inTunnel = false
    if NC and NC.inTunnel then
        local px, py, pz = getElementPosition(localPlayer)
        inTunnel = NC.inTunnel(px, py, pz)
    end
    -- Fog: keep a reasonable near start so the world never draws holes; far clip never under 1800 m.
    local farClip = math.max(1800, st.far)
    local fogStart = farClip * math.max(0.15, 1.0 - 0.6 * st.fogD)
    pcall(setFogDistance, fogStart)
    pcall(setFarClipDistance, farClip)
    pcall(resetWindVelocity)
    pcall(setWindVelocity, st.wind[1], st.wind[2], 0)
    pcall(setCloudsEnabled, st.clouds)
    -- Rain: natural levels, never over 0.6 even in storms
    local rainAmt = inTunnel and 0 or math.min(0.6, st.rain)
    pcall(resetRainLevel)
    pcall(setRainLevel, rainAmt)
    if st.weather == "foggy" or st.weather == "mist" then
        pcall(setHeatHaze, 1)
    else
        pcall(resetHeatHaze)
    end
    -- Tell the shaders.
    local ws = _wet()
    if ws and isElement(ws) then
        dxSetShaderValue(ws, "gWet", st.wet * (inTunnel and 0.3 or 1.0))
        dxSetShaderValue(ws, "gSheen", st.sheen)
        dxSetShaderValue(ws, "gSunAlt", st.sunAlt)
    end
    local ps = _post()
    if ps and isElement(ps) then
        local exposure = tonumber(_G.NC_ATMO_EXPOSURE) or 1.0
        dxSetShaderValue(ps, "gGain", exposure / (0.75 + 0.25 * st.sunAlt))
        dxSetShaderValue(ps, "gTint", st.amb[1], st.amb[2], st.amb[3])
    end
end

-- tick: advances auto cycle + lightning, smoothes, pushes to GTA
local lastTick = 0
function M.tick(now)
    local dt = math.min(0.1, (now - lastTick) / 1000)
    if lastTick == 0 then dt = 0 end
    lastTick = now
    if M.cycle then
        M.timeH = (M.timeH + dt / M.cycleSpeed) % 24
    end
    if (M.weather == "rain" or M.weather == "storm" or M.weather == "drizzle") then
        if math.random() < (M.weather == "storm" and 0.0008 or (M.weather == "rain" and 0.0002 or 0.00005)) then
            M.lightning = 1.0
            _sfx("thunder", false, 0.4)
        end
    end
    smoothStep()
    apply(M.lerped)
end

-- helpers
function M.weatherList() return weatherNames end

_G.NC_ATMO = M
