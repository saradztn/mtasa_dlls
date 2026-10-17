-- One persistent rope object; changing model never allocates an object/texture/shader.
-- Camera distance is measured to the whole sagging rope, not only its midpoint.
function PSG.updateLOD()
    if not PSG.ready or not isElement(PSG.rope) then return end
    if getElementDimension(localPlayer)~=PSG_CONFIG.dimension then return end
    local x,y,z=getCameraMatrix();local o=PSG_CONFIG.origin
    x=x-o[1];y=y-o[2];z=z-o[3]
    local along=math.max(-20,math.min(20,x))
    local height=math.abs(along)<14 and (1.05-.16*math.cos(math.pi*along/28)^2) or 1.05
    local distance2=(x-along)^2+y*y+(z-height)^2
    local q=PSG_CONFIG.ropeLOD[PSG.quality];local target=PSG.ropeTier
    if PSG.quality=='LOW' then target='low'
    elseif target=='high' and distance2>q.leave*q.leave then target='low'
    elseif target=='low' and distance2<q.enter*q.enter then target='high' end
    if target~=PSG.ropeTier then
        local id=PSG.modelByName[target=='low' and 'rope_low' or 'rope']
        if setElementModel(PSG.rope,id) then
            PSG.ropeTier=target;setElementCollisionsEnabled(PSG.rope,false)
        else outputDebugString('[PSG] Rope LOD model switch failed; retaining current model',1) end
    end
end
