function PSG.createWorld()
    local tier=PSG_CONFIG.quality[PSG.quality].tier
    local txd=PSG.keep(engineLoadTXD('textures/'..tier..'/genesis.txd'))
    if not txd then error('[PSG] TXD load failed') end
    PSG.txd=txd;PSG.txds={[tier]=txd};PSG.modelByName={}
    for _,a in ipairs(PSG_CONFIG.assets) do
        local id=engineRequestModel('object',1337)
        if not id then error('[PSG] No free model ID for '..a.name) end
        table.insert(PSG.ids,id)
        local col=PSG.keep(engineLoadCOL('collisions/'..a.name..'.col'))
        local dff=PSG.keep(engineLoadDFF('models/'..a.name..'.dff'))
        if not col or not dff or not engineImportTXD(txd,id) or not engineReplaceCOL(col,id) or not engineReplaceModel(dff,id,a.role=='panel_template') then error('[PSG] Model load/replace failed: '..a.name) end
        PSG.modelByName[a.name]=id
        engineSetModelLODDistance(id,170)
    end
    local function place(name,p)
        local o=PSG_CONFIG.origin
        local ob=createObject(PSG.modelByName[name],o[1]+p[1],o[2]+p[2],o[3]+p[3])
        if not ob then error('[PSG] Object creation failed: '..name) end
        setElementDimension(ob,PSG_CONFIG.dimension);setElementInterior(ob,0);setElementDoubleSided(ob,false)
        table.insert(PSG.objects,ob);return ob
    end
    for _,p in ipairs(PSG_CONFIG.placements) do
        local ob=place(p.asset,p.position)
        if p.asset=='rope' then PSG.rope=ob;PSG.ropeTier='high';setElementCollisionsEnabled(ob,false) end
    end
    for _,p in ipairs(PSG_CONFIG.panels) do PSG.panelObjects[p.id]=place('glass_panel',p.position) end
end
function PSG.destroyWorld()
    PSG.clearMaterials()
    if PSG.resetLighting then PSG.resetLighting() end
    PSG.rope=nil;PSG.ropeTier=nil
    for _,ob in ipairs(PSG.objects) do if isElement(ob) then destroyElement(ob) end end;PSG.objects={};PSG.panelObjects={}
    for _,id in ipairs(PSG.ids) do engineRestoreModel(id);engineRestoreCOL(id);engineFreeModel(id) end;PSG.ids={}
    for _,e in ipairs(PSG.resources) do if isElement(e) then destroyElement(e) end end;PSG.resources={}
end
addEvent('psg:panels',true)
addEventHandler('psg:panels',resourceRoot,function(states)
    if source~=resourceRoot or type(states)~='table' then return end
    for id,state in pairs(states) do
        local ob=PSG.panelObjects[id]
        if isElement(ob) and (state=='intact' or state=='marked' or state=='broken') then setElementAlpha(ob,state=='broken' and 0 or state=='marked' and 180 or 255);setElementCollisionsEnabled(ob,state~='broken') end
    end
end)
