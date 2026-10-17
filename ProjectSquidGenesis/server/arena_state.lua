local states={};for _,p in ipairs(PSG_CONFIG.panels) do states[p.id]='intact' end
function getPanelState(id)
    if type(id)~='string' then return false end
    return states[id] or false
end
function setPanelState(id,state)
    if type(id)~='string' or type(state)~='string' then return false end
    if not states[id] or (state~='intact' and state~='marked' and state~='broken') then return false end
    states[id]=state;triggerClientEvent(root,'psg:panels',resourceRoot,{[id]=state});return true
end
-- No remotely-triggerable mutation event. Trusted server exports / ACL command only.
addCommandHandler('psg_panel',function(player,_,id,state)
    if isElement(player) and not hasObjectPermissionTo(player,'command.psg_panel',false) then return end
    if not setPanelState(id,state) and isElement(player) then outputChatBox('/psg_panel GB_01_L intact|marked|broken',player) end
end)
local last={}
addEvent('psg:snapshot',true)
addEventHandler('psg:snapshot',resourceRoot,function()
    if not client or source~=resourceRoot or not PSG_isClientReady(client) then return end
    local now=getTickCount();if last[client] and (now-last[client])%4294967296<2000 then return end
    last[client]=now;triggerClientEvent(client,'psg:panels',resourceRoot,states)
end)
addEventHandler('onPlayerQuit',root,function()last[source]=nil end)
