--[[
  NextGenPoliceDepartment - exterior night lighting (client).

  Building/site surfaces get their lighting from the baked prelight (day + night vertex colours,
  including canopy downlights, sign floods and street lamps - see tools/asset_builder/lighting.py).
  At runtime this module only adds:
    * corona markers at the brightest exterior fixtures (count limited by the quality profile),
      visible between 19:30 and 06:30;
    * a few createLight point lights under the canopy / at the garage door.  MTA's createLight lights
      peds and vehicles, NOT buildings, so it is used only to light players walking in.
  Interior rooms are lit entirely by their baked per-room light zones (office / detention / lab ...).
]]

NGPD.lighting = { markers = {}, lights = {}, visible = nil }
local LT = NGPD.lighting

local function isNight()
    local h, m = getTime()
    local t = h + m / 60
    return t >= 19.5 or t < 6.5
end

function LT.clear()
    if isTimer(LT.timer) then killTimer(LT.timer) end
    LT.timer = nil
    for _, m in ipairs(LT.markers) do if isElement(m.el) then destroyElement(m.el) end end
    for _, l in ipairs(LT.lights) do if isElement(l) then destroyElement(l) end end
    LT.markers, LT.lights, LT.visible = {}, {}, nil
end

local function refresh()
    local night = isNight()
    if night == LT.visible then return end
    LT.visible = night
    for _, m in ipairs(LT.markers) do
        if isElement(m.el) then setMarkerColor(m.el, m.r, m.g, m.b, night and m.a or 0) end
    end
    for _, l in ipairs(LT.lights) do
        if isElement(l) then setLightColor(l, night and 255 or 0, night and 240 or 0, night and 220 or 0) end
    end
end

function LT.build(profile)
    LT.clear()
    local n = profile.lampCoronas or 0
    local list = {}
    for _, l in ipairs(NGPD_DATA.lights or {}) do list[#list + 1] = l end
    -- most important first: brightest, then closest to the main entrance axis
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
            LT.markers[#LT.markers + 1] = { el = el, r = l.r, g = l.g, b = l.b, a = 110 }
        end
    end
    if n > 0 then
        -- ped/vehicle-only point lights at the public entrance and the garage apron
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
