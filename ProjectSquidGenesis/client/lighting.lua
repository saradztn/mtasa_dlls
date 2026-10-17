-- Stable source identities + hysteresis; fade out before moving a slot to a new fixture.
-- No interpolated light positions through walls and no new graphics resources per update.
function PSG.resetLighting()PSG.lightSlots={} end
function PSG.updateLighting(dt)
    if getElementDimension(localPlayer)~=PSG_CONFIG.dimension then return end
    dt=math.max(0,math.min(dt or .25,.5))
    local step=dt/.6
    local x,y,z=getCameraMatrix();local origin=PSG_CONFIG.origin;local sorted={}
    local slots=PSG.lightSlots or {};PSG.lightSlots=slots
    local active={}
    for i=1,4 do
        slots[i]=slots[i] or {weight=0}
        if slots[i].index then active[slots[i].index]=true end
    end
    for id,l in ipairs(PSG_CONFIG.lights) do
        local p=l.position;local d=(p[1]+origin[1]-x)^2+(p[2]+origin[2]-y)^2+(p[3]+origin[3]-z)^2
        table.insert(sorted,{id=id,score=d*(active[id] and .8 or 1)})
    end
    table.sort(sorted,function(a,b)if a.score==b.score then return a.id<b.id end;return a.score<b.score end)
    local wanted,order,claimed={},{},{}
    for i=1,math.min(PSG_CONFIG.quality[PSG.quality].lightCount,#sorted) do
        wanted[sorted[i].id]=true;order[i]=sorted[i].id
    end
    for i=1,4 do
        local slot=slots[i];slot.next=nil
        if slot.index and wanted[slot.index] then slot.next=slot.index;claimed[slot.index]=true end
    end
    for i=1,4 do
        local slot=slots[i]
        if not slot.next then
            for _,id in ipairs(order) do if not claimed[id] then slot.next=id;claimed[id]=true;break end end
        end
        if slot.index~=slot.next then
            slot.weight=math.max(0,slot.weight-step)
            if slot.weight==0 then slot.index=slot.next end
        elseif slot.index then slot.weight=math.min(1,slot.weight+step)
        else slot.weight=0 end
    end
    for _,shader in ipairs(PSG.shaders) do
        for i=1,4 do
            local slot=slots[i];local l=slot.index and PSG_CONFIG.lights[slot.index]
            local p=l and l.position or {0,0,0};local c=l and l.color or {0,0,0}
            dxSetShaderValue(shader,'gLight'..(i-1),origin[1]+p[1],origin[2]+p[2],origin[3]+p[3])
            dxSetShaderValue(shader,'gColor'..(i-1),c[1]*slot.weight,c[2]*slot.weight,c[3]*slot.weight)
        end
        dxSetShaderValue(shader,'gWetness',PSG.wetness or .65)
    end
end
-- Scoped local atmosphere: no global server weather changes.
local atmosphere
function PSG.updateAtmosphere()
    local inside=getElementDimension(localPlayer)==PSG_CONFIG.dimension
    if inside and not atmosphere then
        local h,m=getTime()
        atmosphere={h=h,m=m,weather=getWeather(),minute=getMinuteDuration(),far=getFarClipDistance(),fog=getFogDistance()}
        setTime(0,30);setMinuteDuration(600000);setWeather(7);setFarClipDistance(180);setFogDistance(145)
    elseif not inside then PSG.restoreAtmosphere() end
end
function PSG.restoreAtmosphere()
    if atmosphere then
        setTime(atmosphere.h,atmosphere.m);setMinuteDuration(atmosphere.minute);setWeather(atmosphere.weather);setFarClipDistance(atmosphere.far);setFogDistance(atmosphere.fog);atmosphere=nil
    end
end
