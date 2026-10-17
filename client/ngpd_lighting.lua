--[[
  NextGenPoliceDepartment - Exterior Golden-Hour & Night Lighting (Client)

  * Corona markers at exterior fixtures (count scaled by quality profile), active from dusk/golden-hour
    through dawn (18:15 to 06:45).
  * Dynamic point lights under the entrance canopy and garage apron.
  * Computes screen-space solar disc position along gSunDir for atmospheric Mie glare.
]]

NGPD.lighting = { markers = {}, lights = {}, visible = nil }
local LT = NGPD.lighting

local function isDuskOrNight()
    local h, m = getTime()
    local t = h + m / 60
    return t >= 18.25 or t < 6.75
end

function LT.getSunScreenPos()
    if not getCameraMatrix or not getScreenFromWorldPosition or not guiGetScreenSize then
        return 0.5, 0.25, 0.0
    end
    local cx, cy, cz, lx, ly, lz = getCameraMatrix()
    if not cx then return 0.5, 0.25, 0.0 end
    local sunDir = (NGPD.shaders and NGPD.shaders.env and NGPD.shaders.env.gSunDir) or { 0.46, -0.64, 0.61 }
    local sx_w = cx + sunDir[1] * 800.0
    local sy_w = cy + sunDir[2] * 800.0
    local sz_w = cz + sunDir[3] * 800.0
    local scrX, scrY = getScreenFromWorldPosition(sx_w, sy_w, sz_w, 0.25, true)
    if not scrX or not scrY then return 0.5, 0.25, 0.0 end
    local sw, sh = guiGetScreenSize()
    local u = NGPD.clamp(scrX / math.max(1, sw), 0, 1)
    local v = NGPD.clamp(scrY / math.max(1, sh), 0, 1)
    local vx, vy, vz = lx - cx, ly - cy, lz - cz
    local vlen = math.sqrt(vx * vx + vy * vy + vz * vz) + 1e-6
    local align = math.max(0, (vx * sunDir[1] + vy * sunDir[2] + vz * sunDir[3]) / vlen)
    local dayFactor = (NGPD.shaders and NGPD.shaders.env and NGPD.shaders.env.gDayFactor) or 1.0
    local weight = math.pow(align, 2.0) * dayFactor
    return u, v, weight
end

function LT.clear()
    if isTimer(LT.timer) then killTimer(LT.timer) end
    LT.timer = nil
    for _, m in ipairs(LT.markers) do if isElement(m.el) then destroyElement(m.el) end end
    for _, l in ipairs(LT.lights) do if isElement(l) then destroyElement(l) end end
    LT.markers, LT.lights, LT.visible = {}, {}, nil
end

local function refresh()
    local active = isDuskOrNight()
    if active == LT.visible then return end
    LT.visible = active
    for _, m in ipairs(LT.markers) do
        if isElement(m.el) then setMarkerColor(m.el, m.r, m.g, m.b, active and m.a or 0) end
    end
    for _, l in ipairs(LT.lights) do
        if isElement(l) then setLightColor(l, active and 255 or 0, active and 232 or 0, active and 196 or 0) end
    end
end

function LT.build(profile)
    LT.clear()
    local n = profile.lampCoronas or 0
    local list = {}
    for _, l in ipairs(NGPD_DATA.lights or {}) do list[#list + 1] = l end
    table.sort(list, function(a, b)
        if a.intensity ~= b.intensity then return a.intensity > b.intensity end
        return (a.x * a.x + (a.y + 20) ^ 2) < (b.x * b.x + (b.y + 20) ^ 2)
    end)
    local int, dim = NGPD.models.int or 0, NGPD.models.dim or 0
    for i = 1, math.min(n, #list) do
        local l = list[i]
        local x, y, z = NGPD.toWorld(l.x, l.y, l.z)
        local size = 0.35 + 0.35 * l.intensity
        local el = createMarker(x, y, z, "corona", size, l.r, l.g, l.b, 0)
        if el then
            setElementInterior(el, int)
            setElementDimension(el, dim)
            LT.markers[#LT.markers + 1] = { el = el, r = l.r, g = l.g, b = l.b, a = 115 }
        end
    end
    if n > 0 then
        for _, p in ipairs({ { 0, -18.5, 3.0, 9 }, { -6, -18.5, 3.0, 7 }, { 6, -18.5, 3.0, 7 }, { 45, 11, 4.0, 8 } }) do
            local x, y, z = NGPD.toWorld(p[1], p[2], p[3])
            local l = createLight(0, x, y, z, p[4], 0, 0, 0)
            if l then
                setElementInterior(l, int)
                setElementDimension(l, dim)
                LT.lights[#LT.lights + 1] = l
            end
        end
    end
    refresh()
    LT.timer = setTimer(refresh, 5000, 0)
end

addEventHandler("onClientResourceStop", resourceRoot, function() LT.clear() end)
