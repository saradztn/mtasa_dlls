--[[
  NextGenPoliceDepartment - personal weather / time presets (client-local).

  /ngpd_weather <preset|off|list>
  Presets only change THIS player's view (client-side setWeather/setTime/setRainLevel/fog), nothing is
  sent to the server and no other player is affected.  The previous values are saved when a preset is
  first applied and restored on "off" and when the resource stops.  No preset is active by default -
  in particular rain is never forced unless the player picks a rain preset.
  While a preset is active it is re-asserted every 5 s so the server's weather/time sync does not
  silently replace it; the minute duration is raised so the chosen time stays put.
]]

NGPD.weather = { active = nil, saved = nil }
local WX = NGPD.weather

-- SA weather IDs: 15 cloudy countryside, 16 rainy countryside, 17/18 (extra) sunny desert, 9 foggy SF, 8 LS storm
WX.presets = {
    sunny     = { label = "Sunny",       weather = 18, hour = 12, minute = 0 },
    cloudy    = { label = "Cloudy",      weather = 15, hour = 13, minute = 30 },
    sunset    = { label = "Sunset",      weather = 17, hour = 19, minute = 40 },
    night     = { label = "Night",       weather = 18, hour = 23, minute = 30 },
    lightrain = { label = "Light Rain",  weather = 16, hour = 14, minute = 0, rain = 0.25 },
    heavyrain = { label = "Heavy Rain",  weather = 8,  hour = 16, minute = 0, rain = 1.0 },
    postrain  = { label = "Post-Rain",   weather = 15, hour = 17, minute = 30, rain = 0.0, wetness = 0.9 },
    fog       = { label = "Fog",         weather = 9,  hour = 7,  minute = 0, fog = 30, farClip = 220 },
}
WX.order = { "sunny", "cloudy", "sunset", "night", "lightrain", "heavyrain", "postrain", "fog" }

local function save()
    if WX.saved then return end
    local h, m = getTime()
    WX.saved = { weather = getWeather(), hour = h, minute = m, minuteDuration = getMinuteDuration() }
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
    setMinuteDuration(3600000)     -- 1 game minute per real hour: time effectively frozen
    setWeather(p.weather)
    setTime(p.hour, p.minute)
    if p.rain ~= nil then setRainLevel(p.rain) else resetRainLevel() end
    if p.fog then setFogDistance(p.fog) else resetFogDistance() end
    if p.farClip then setFarClipDistance(p.farClip) else resetFarClipDistance() end
    if p.wetness and NGPD.wet then NGPD.wet.force(p.wetness) end
    if p.rain and p.rain > 0.5 and NGPD.wet and NGPD.wet.value < 0.3 then NGPD.wet.force(0.3) end
    if not isTimer(WX.timer) then WX.timer = setTimer(assertPreset, 5000, 0) end
    return true
end

function WX.restore()
    if isTimer(WX.timer) then killTimer(WX.timer) end
    WX.timer = nil
    WX.active = nil
    resetRainLevel()
    resetFogDistance()
    resetFarClipDistance()
    local s = WX.saved
    if s then
        setWeather(s.weather)
        setMinuteDuration(s.minuteDuration)
        setTime(s.hour, s.minute)
    end
    WX.saved = nil
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

addEventHandler("onClientResourceStop", resourceRoot, function()
    if WX.active or WX.saved then WX.restore() end
end)
