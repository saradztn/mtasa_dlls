--[[
  NextGenPoliceDepartment - Golden-Hour Atmospheric Weather & Time-of-Day System (Client)

  /ngpd_weather <goldenhour|sunset|postrain|sunny|cloudy|night|lightrain|heavyrain|fog|off|list>
  /ngpd_time <HH:MM|off>
  Presets only change THIS player's view (client-side sky gradient, sun disc size/color, weather,
  time, rain, fog, and wetness) and smoothly restore on "off" or resource stop.
]]

NGPD.weather = { active = nil, saved = nil, customSun = nil }
local WX = NGPD.weather

-- SA weather IDs + physically tuned Golden-Hour sky gradients & solar parameters
WX.presets = {
    goldenhour = {
        label = "Golden-Hour Wet Sunset (Reference Visual Target)",
        weather = 17, hour = 18, minute = 50, rain = 0.0, wetness = 0.78,
        skyTop = { 62, 86, 134 }, skyBot = { 244, 152, 78 },
        sunCore = { 255, 224, 156 }, sunCorona = { 255, 146, 64 }, sunSize = 4.5,
        sunDir = { 0.46, -0.64, 0.61 }, sunColor = { 1.00, 0.78, 0.48 }, skyColor = { 0.54, 0.60, 0.74 },
        fog = 95, farClip = 650, wind = { 0.35, 0.20, 0.0 },
    },
    sunset = {
        label = "Sunset",
        weather = 17, hour = 19, minute = 40, rain = 0.0, wetness = 0.65,
        skyTop = { 54, 74, 122 }, skyBot = { 238, 136, 68 },
        sunCore = { 255, 212, 142 }, sunCorona = { 248, 128, 54 }, sunSize = 4.2,
        sunDir = { 0.52, -0.68, 0.51 }, sunColor = { 1.00, 0.74, 0.44 }, skyColor = { 0.50, 0.56, 0.70 },
        fog = 85, farClip = 600, wind = { 0.30, 0.15, 0.0 },
    },
    postrain = {
        label = "Post-Rain Golden Reflection",
        weather = 15, hour = 17, minute = 30, rain = 0.0, wetness = 0.92,
        skyTop = { 70, 94, 138 }, skyBot = { 232, 158, 92 },
        sunCore = { 255, 228, 168 }, sunCorona = { 245, 162, 82 }, sunSize = 3.8,
        sunDir = { 0.42, -0.62, 0.66 }, sunColor = { 1.00, 0.82, 0.56 }, skyColor = { 0.54, 0.62, 0.75 },
        fog = 80, farClip = 550, wind = { 0.40, 0.25, 0.0 },
    },
    sunny = {
        label = "Sunny",
        weather = 18, hour = 12, minute = 0,
        skyTop = { 48, 108, 196 }, skyBot = { 165, 206, 245 },
        sunCore = { 255, 250, 232 }, sunCorona = { 255, 236, 195 }, sunSize = 2.5,
        sunDir = { 0.25, -0.45, 0.86 }, sunColor = { 1.00, 0.96, 0.90 }, skyColor = { 0.58, 0.68, 0.82 },
    },
    cloudy = {
        label = "Cloudy",
        weather = 15, hour = 13, minute = 30,
        skyTop = { 112, 126, 146 }, skyBot = { 168, 178, 192 },
        sunCore = { 225, 222, 212 }, sunCorona = { 196, 198, 202 }, sunSize = 1.8,
        sunDir = { 0.30, -0.50, 0.81 }, sunColor = { 0.88, 0.88, 0.86 }, skyColor = { 0.62, 0.66, 0.72 },
    },
    night = {
        label = "Night",
        weather = 18, hour = 23, minute = 30,
        skyTop = { 10, 16, 30 }, skyBot = { 26, 36, 58 },
        sunCore = { 160, 180, 220 }, sunCorona = { 90, 110, 150 }, sunSize = 1.2,
        sunDir = { -0.20, 0.40, 0.89 }, sunColor = { 0.24, 0.30, 0.44 }, skyColor = { 0.14, 0.18, 0.28 },
    },
    lightrain = {
        label = "Light Rain",
        weather = 16, hour = 14, minute = 0, rain = 0.25, wetness = 0.75,
        skyTop = { 76, 88, 108 }, skyBot = { 126, 138, 154 },
        sunDir = { 0.34, -0.52, 0.78 }, sunColor = { 0.72, 0.76, 0.82 }, skyColor = { 0.44, 0.50, 0.58 },
        wind = { 0.65, 0.45, 0.0 },
    },
    heavyrain = {
        label = "Heavy Rain",
        weather = 8, hour = 16, minute = 0, rain = 1.0, wetness = 1.0,
        skyTop = { 48, 56, 72 }, skyBot = { 88, 98, 114 },
        sunDir = { 0.38, -0.58, 0.72 }, sunColor = { 0.55, 0.60, 0.68 }, skyColor = { 0.34, 0.40, 0.48 },
        wind = { 1.15, 0.85, 0.0 },
    },
    fog = {
        label = "Fog",
        weather = 9, hour = 7, minute = 0, fog = 30, farClip = 220, wetness = 0.55,
        skyTop = { 142, 152, 164 }, skyBot = { 188, 192, 198 },
        sunDir = { 0.55, -0.60, 0.58 }, sunColor = { 0.86, 0.82, 0.76 }, skyColor = { 0.66, 0.70, 0.74 },
    },
}
WX.order = { "goldenhour", "sunset", "postrain", "sunny", "cloudy", "night", "lightrain", "heavyrain", "fog" }

local function save()
    if WX.saved then return end
    local h, m = getTime()
    WX.saved = { weather = getWeather(), hour = h, minute = m, minuteDuration = getMinuteDuration() }
end

local function applyAtmosphere(p)
    if p.skyTop and p.skyBot and setSkyGradient then
        setSkyGradient(p.skyTop[1], p.skyTop[2], p.skyTop[3], p.skyBot[1], p.skyBot[2], p.skyBot[3])
    elseif resetSkyGradient then
        resetSkyGradient()
    end
    if p.sunCore and p.sunCorona and setSunColor then
        setSunColor(p.sunCore[1], p.sunCore[2], p.sunCore[3], p.sunCorona[1], p.sunCorona[2], p.sunCorona[3])
    elseif resetSunColor then
        resetSunColor()
    end
    if p.sunSize and setSunSize then
        setSunSize(p.sunSize)
    elseif resetSunSize then
        resetSunSize()
    end
    if p.wind and setWindVelocity then
        setWindVelocity(p.wind[1], p.wind[2], p.wind[3])
    elseif resetWindVelocity then
        resetWindVelocity()
    end
    WX.customSun = {
        sunDir = p.sunDir,
        sunColor = p.sunColor,
        skyColor = p.skyColor,
    }
end

local function assertPreset()
    local p = WX.presets[WX.active or ""]
    if not p then return end
    if getWeather() ~= p.weather then setWeather(p.weather) end
    local h, m = getTime()
    if h ~= p.hour or math.abs(m - p.minute) > 2 then setTime(p.hour, p.minute) end
    if p.rain ~= nil then setRainLevel(p.rain) end
end

function WX.apply(name)
    local p = WX.presets[name]
    if not p then return false end
    save()
    WX.active = name
    setMinuteDuration(3600000)
    setWeather(p.weather)
    setTime(p.hour, p.minute)
    if p.rain ~= nil then setRainLevel(p.rain) else resetRainLevel() end
    if p.fog then setFogDistance(p.fog) else resetFogDistance() end
    if p.farClip then setFarClipDistance(p.farClip) else resetFarClipDistance() end
    applyAtmosphere(p)
    if p.wetness and NGPD.wet then NGPD.wet.force(p.wetness) end
    if p.rain and p.rain > 0.5 and NGPD.wet and NGPD.wet.value < 0.3 then NGPD.wet.force(0.3) end
    if not isTimer(WX.timer) then WX.timer = setTimer(assertPreset, 5000, 0) end
    if NGPD.shaders and NGPD.shaders.refreshNow then NGPD.shaders.refreshNow() end
    return true
end

function WX.restore()
    if isTimer(WX.timer) then killTimer(WX.timer) end
    WX.timer = nil
    WX.active = nil
    WX.customSun = nil
    resetRainLevel()
    resetFogDistance()
    resetFarClipDistance()
    if resetSkyGradient then resetSkyGradient() end
    if resetSunColor then resetSunColor() end
    if resetSunSize then resetSunSize() end
    if resetWindVelocity then resetWindVelocity() end
    local s = WX.saved
    if s then
        setWeather(s.weather)
        setMinuteDuration(s.minuteDuration)
        setTime(s.hour, s.minute)
    end
    WX.saved = nil
    if NGPD.shaders and NGPD.shaders.refreshNow then NGPD.shaders.refreshNow() end
end

addCommandHandler(NGPD_CONFIG.presetCommand, function(_, name)
    name = name and name:lower() or "list"
    if name == "off" or name == "reset" then
        WX.restore()
        return outputChatBox("[NGPD] Weather/time restored.", 150, 200, 255)
    end
    if WX.apply(name) then
        return outputChatBox("[NGPD] Personal preset: " .. WX.presets[name].label .. " (only you see this; /" .. NGPD_CONFIG.presetCommand .. " off to restore)", 150, 200, 255)
    end
    local names = {}
    for _, k in ipairs(WX.order) do names[#names + 1] = k end
    outputChatBox("[NGPD] presets: " .. table.concat(names, ", ") .. ", off" .. (WX.active and ("  (active: " .. WX.active .. ")") or ""), 150, 200, 255)
end)

addCommandHandler("ngpd_time", function(_, arg)
    if not arg or arg == "off" or arg == "reset" then
        WX.restore()
        return outputChatBox("[NGPD] Time-of-day lock cleared.", 150, 200, 255)
    end
    local h, m = arg:match("^(%d+):(%d+)$")
    h, m = tonumber(h or arg), tonumber(m or 0)
    if not h or h < 0 or h > 23 then
        return outputChatBox("[NGPD] Usage: /ngpd_time <0..23[:MM]|off>", 150, 200, 255)
    end
    save()
    setMinuteDuration(3600000)
    setTime(h, math.max(0, math.min(59, m)))
    if NGPD.shaders and NGPD.shaders.refreshNow then NGPD.shaders.refreshNow() end
    outputChatBox(string.format("[NGPD] Time locked to %02d:%02d.", h, m), 150, 200, 255)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    if WX.active or WX.saved then WX.restore() end
end)
