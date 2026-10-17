--[[
  NextGenPoliceDepartment - wet surface state machine (client).

  wetness (0..1) follows the game's current rain (getRainLevel):
    rises  at  riseRate * (0.3 + 0.7 * rainStrength)  per second while it rains
    dries  at  dryRate (day) / dryRateNight per second when it does not rain
  States: Dry, Rain Starting, Light Rain, Heavy Rain, Wet After Rain, Drying.
  Per-material response (wet_factor / porosity / puddles) is applied in the shaders; interior shader
  instances ignore wetness.  The Post-Rain weather preset may force a starting wetness.
  The visual result is an approximation: darkening + lower roughness + puddle masks + env colour gloss.
]]

NGPD.wet = { value = 0, state = "Dry", lastRainTick = 0, forced = nil }
local W = NGPD.wet
local C = NGPD_CONFIG.wet

function W.force(v)
    W.value = NGPD.clamp(v, 0, 1)
    W.lastRainTick = getTickCount()
end

local function isNight()
    local h = getTime()
    return h >= 20 or h < 6
end

local function update()
    local dt = C.updateMs / 1000
    local rain = getRainLevel() or 0
    local t = getTickCount()
    if rain > 0.001 then
        local strength = NGPD.clamp(rain / C.heavyRain, 0, 1)
        W.value = math.min(1, W.value + C.riseRate * (0.3 + 0.7 * strength) * dt)
        W.lastRainTick = t
        if W.value < 0.2 then
            W.state = "Rain Starting"
        elseif rain >= C.heavyRain then
            W.state = "Heavy Rain"
        else
            W.state = "Light Rain"
        end
    else
        local rate = isNight() and C.dryRateNight or C.dryRate
        W.value = math.max(0, W.value - rate * dt)
        if W.value <= 0.01 then
            W.state = "Dry"
        elseif W.value > 0.6 and t - W.lastRainTick < 120000 then
            W.state = "Wet After Rain"
        else
            W.state = "Drying"
        end
    end
end

addEventHandler("onClientResourceStart", resourceRoot, function()
    -- start from the current weather instead of a fake default: raining now = already fairly wet
    if (getRainLevel() or 0) > C.lightRain then W.value = 0.6 end
    W.timer = setTimer(update, C.updateMs, 0)
end)

addEventHandler("onClientResourceStop", resourceRoot, function()
    if isTimer(W.timer) then killTimer(W.timer) end
end)

addCommandHandler("ngpd_wet", function(_, v)
    if v and tonumber(v) then
        -- local visual test only (nothing is sent to the server)
        W.force(tonumber(v))
    end
    outputChatBox(string.format("[NGPD] wetness %.2f  state: %s  rain level %.2f", W.value, W.state, getRainLevel() or 0), 150, 200, 255)
end)
