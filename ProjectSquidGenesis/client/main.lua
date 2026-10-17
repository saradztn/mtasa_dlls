local timers={}
local function worldIntact()
    if #PSG.objects~=#PSG_CONFIG.placements+#PSG_CONFIG.panels or #PSG.ids~=#PSG_CONFIG.assets then return false end
    for _,ob in ipairs(PSG.objects) do if not isElement(ob) then return false end end
    return true
end
addEvent('psg:prepare',true)
addEventHandler('psg:prepare',resourceRoot,function(protocol,token)
    if source~=resourceRoot or protocol~=PSG_CONFIG.protocol or type(token)~='string' then return end
    if not PSG.ready or not worldIntact() then
        PSG.ready=false
        triggerServerEvent('psg:loadStatus',resourceRoot,PSG_CONFIG.protocol,false)
        return
    end
    triggerServerEvent('psg:prepared',resourceRoot,token)
end)
addEventHandler('onClientResourceStart',resourceRoot,function()
    PSG.ready=false
    triggerServerEvent('psg:loadStatus',resourceRoot,PSG_CONFIG.protocol,false)
    local ok,err=pcall(function()PSG.createWorld();PSG.loadMaterials()end)
    if not ok or not worldIntact() then
        outputDebugString('[PSG] Startup failed: '..tostring(err),1);PSG.destroyWorld();return
    end
    PSG.ready=true
    PSG.startInteractions()
    timers[1]=setTimer(function()PSG.updateWetness();PSG.updateAtmosphere();PSG.updateLighting();PSG.updateLOD();PSG.updateInteractions()end,250,0)
    triggerServerEvent('psg:loadStatus',resourceRoot,PSG_CONFIG.protocol,true)
    triggerServerEvent('psg:snapshot',resourceRoot)
    outputChatBox('[PSG] Assets loaded: /psg enter | tug | glass | leave. Build 0.5: not gameplay-complete.')
end)
addCommandHandler('psg_quality',function(_,quality)
    if not PSG.ready then outputChatBox('[PSG] Assets not ready.');return end
    quality=string.upper(quality or '')
    if not PSG_CONFIG.quality[quality] then outputChatBox('/psg_quality LOW|MEDIUM|HIGH');return end
    if quality==PSG.quality then return end
    local tier=PSG_CONFIG.quality[quality].tier
    local txd=PSG.txds[tier] or PSG.keep(engineLoadTXD('textures/'..tier..'/genesis.txd'))
    if not txd then outputDebugString('[PSG] Tier TXD load failed; keeping previous quality',1);return end
    PSG.txds[tier]=txd
    for _,id in ipairs(PSG.ids) do
        if not engineImportTXD(txd,id) then
            local old=PSG.txds[PSG_CONFIG.quality[PSG.quality].tier]
            local restored=true
            for _,restoreId in ipairs(PSG.ids) do if not engineImportTXD(old,restoreId) then restored=false end end
            if restored then outputDebugString('[PSG] Tier import failed; previous dictionary restored',1)
            else
                PSG.ready=false;triggerServerEvent('psg:loadStatus',resourceRoot,PSG_CONFIG.protocol,false)
                outputDebugString('[PSG] FATAL: dictionary import AND rollback failed. Entry disabled; restart resource.',1)
            end
            return
        end
    end
    PSG.quality=quality
    PSG.loadMaterials();PSG.updateLighting(0);PSG.updateLOD()
end)
addEventHandler('onClientResourceStop',resourceRoot,function()
    PSG.ready=false
    triggerServerEvent('psg:loadStatus',resourceRoot,PSG_CONFIG.protocol,false)
    for _,t in ipairs(timers) do if isTimer(t) then killTimer(t) end end
    timers={};PSG.stopInteractions();PSG.restoreAtmosphere();PSG.destroyWorld()
end)

addCommandHandler('psg_status',function()
    local active,fallback=0,0
    for _,status in pairs(PSG.materialStatus or {}) do if status.state=='active' then active=active+1 else fallback=fallback+1 end end
    outputChatBox('[PSG] ready='..tostring(PSG.ready)..' quality='..PSG.quality..' objects='..#PSG.objects..' models='..#PSG.ids)
    outputChatBox('[PSG] materials active='..active..' fallback='..fallback..' rope='..tostring(PSG.ropeTier)..'; no FPS measurement available.')
    outputChatBox('[PSG] nearby='..tostring(PSG.nearbyZone)..' reservation='..tostring(PSG.interactionState and PSG.interactionState.zone))
end)
