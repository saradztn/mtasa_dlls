-- Server-authoritative reservations / proximity readiness. NOT a round controller.
local zones,owners,activity,last={},{},{},{}
local closing=false
for _,zone in ipairs(PSG_CONFIG.interactionZones) do zones[zone.id]=zone end
local function finite(n)return type(n)=='number' and n==n and n>-math.huge and n<math.huge end
local function eligible(p)
    return isElement(p) and getElementType(p)=='player' and PSG_isClientReady(p) and PSG_hasArenaSession(p)
        and getElementDimension(p)==PSG_CONFIG.dimension and getElementInterior(p)==0
        and not isPedDead(p) and not isPedInVehicle(p)
end
local function near(p,zone,radius)
    local x,y,z=getElementPosition(p)
    if not finite(x) or not finite(y) or not finite(z) then return false end
    local o=PSG_CONFIG.origin;local target=zone.position
    return (x-o[1]-target[1])^2+(y-o[2]-target[2])^2<=radius*radius
        and math.abs(z-o[3]-target[3])<=zone.verticalTolerance
end
local function snapshot()
    local result={}
    for id,zone in pairs(zones) do if zone.kind=='tug_slot' then result[id]=isElement(owners[id]) end end
    return result
end
local function broadcast()
    if closing then return end
    local slots=snapshot()
    for _,p in ipairs(getElementsByType('player')) do
        if eligible(p) then triggerClientEvent(p,'psg:slots',resourceRoot,slots) end
    end
end
local function reply(p,ok,reason,data)
    if not closing and isElement(p) then triggerClientEvent(p,'psg:interactionReply',resourceRoot,ok,reason,data) end
end
function getInteractionState(p)
    local a=activity[p]
    if not a then return false end
    return {zone=a.zone,kind=a.kind} -- Never expose the mutable internal table.
end
function getSlotOccupant(id)
    if type(id)~='string' or not zones[id] or zones[id].kind~='tug_slot' then return false end
    return isElement(owners[id]) and owners[id] or false
end
function PSG_syncInteractions(p)
    if eligible(p) then triggerClientEvent(p,'psg:slots',resourceRoot,snapshot());reply(p,true,'synced',getInteractionState(p)) end
end
function PSG_releaseInteraction(p,reason)
    local a=activity[p];if not a then return false end
    activity[p]=nil
    if owners[a.zone]==p then owners[a.zone]=nil end
    reply(p,true,reason or 'released',false);broadcast();return true
end
local function nearestZone(p)
    local best,distance
    local x,y=getElementPosition(p);local o=PSG_CONFIG.origin
    if not finite(x) or not finite(y) then return nil end
    for _,zone in ipairs(PSG_CONFIG.interactionZones) do
        local d=(x-o[1]-zone.position[1])^2+(y-o[2]-zone.position[2])^2
        if near(p,zone,zone.radius) and (not distance or d<distance) then best=zone;distance=d end
    end
    return best
end
local function inspectPanel(p)
    local x,y,z=getElementPosition(p);local o=PSG_CONFIG.origin
    if not finite(x) or not finite(y) or not finite(z) then return reply(p,false,'invalid_position') end
    local best,distance
    for _,panel in ipairs(PSG_CONFIG.panels) do
        local a=panel.position;local d=(x-o[1]-a[1])^2+(y-o[2]-a[2])^2
        if d<=2.5^2 and math.abs(z-o[3]-a[3]-1)<=1.5 and (not distance or d<distance) then best=panel;distance=d end
    end
    if not best then return reply(p,false,'no_nearby_panel') end
    reply(p,true,'panel_info',{id=best.id,row=best.row,side=best.side,material=best.material,state=getPanelState(best.id)})
end
local function request(p,action,id)
    if not isElement(p) or getElementType(p)~='player' then return end
    local now=getTickCount()
    if last[p] and (now-last[p])%4294967296<PSG_CONFIG.interactionRequestInterval then return end
    last[p]=now
    if not eligible(p) then PSG_releaseInteraction(p,'session_invalid');return reply(p,false,'session_required') end
    if action=='release' then
        if not PSG_releaseInteraction(p,'released') then reply(p,true,'released',false) end
        return
    end
    if action=='inspect_panel' then return inspectPanel(p) end
    if action~='use' then return reply(p,false,'invalid_action') end
    if id~=nil and (type(id)~='string' or #id>64) then return reply(p,false,'invalid_zone') end
    local zone
    if id then zone=zones[id] else zone=nearestZone(p) end
    if not zone then return reply(p,false,'invalid_zone') end
    if not near(p,zone,zone.radius) then return reply(p,false,'too_far') end
    if zone.kind=='exit' then PSG_leaveArena(p);return reply(p,true,'left_arena',false) end
    if zone.kind=='tug_slot' and isElement(owners[zone.id]) and owners[zone.id]~=p then return reply(p,false,'occupied') end
    local old=activity[p]
    if old and old.zone==zone.id then return reply(p,true,'already_reserved',getInteractionState(p)) end
    -- Validate destination before releasing an old reservation; no yielding between claims.
    if old and owners[old.zone]==p then owners[old.zone]=nil end
    activity[p]={zone=zone.id,kind=zone.kind}
    if zone.kind=='tug_slot' then owners[zone.id]=p end
    reply(p,true,zone.kind=='tug_slot' and 'reserved' or 'bridge_ready',getInteractionState(p));broadcast()
end
addEvent('psg:interaction',true)
addEventHandler('psg:interaction',resourceRoot,function(protocol,action,id)
    if not client or source~=resourceRoot or protocol~=PSG_CONFIG.protocol or type(action)~='string' then return end
    request(client,action,id)
end)
addCommandHandler('psg_use',function(p,_,id)if isElement(p) then request(p,'use',id) end end)
addCommandHandler('psg_release',function(p)if isElement(p) then request(p,'release') end end)
addCommandHandler('psg_panelinfo',function(p)if isElement(p) then request(p,'inspect_panel') end end)
local maintenance=setTimer(function()
    for p,a in pairs(activity) do
        local zone=zones[a.zone]
        if not eligible(p) or not zone or not near(p,zone,zone.exitRadius) then PSG_releaseInteraction(p,'moved_away') end
    end
end,500,0)
addEventHandler('onPlayerQuit',root,function()PSG_releaseInteraction(source,'disconnected');last[source]=nil end)
addEventHandler('onPlayerWasted',root,function()PSG_releaseInteraction(source,'died')end)
addEventHandler('onResourceStop',resourceRoot,function()
    closing=true
    if isTimer(maintenance) then killTimer(maintenance) end
    activity={};owners={};last={}
end)
