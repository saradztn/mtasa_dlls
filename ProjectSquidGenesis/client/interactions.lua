-- Lightweight optional HUD/debug lines. No markers, textures or models allocated here.
local known,slots={},{ }
for _,zone in ipairs(PSG_CONFIG.interactionZones) do known[zone.id]=zone end
local reasons={reserved='Tug slot reserved (no animation/round started).',bridge_ready='Bridge entry acknowledged (no round started).',occupied='That slot is occupied.',too_far='Move closer to the station.',invalid_zone='No interaction station in range.',session_required='Enter through /psg first.',released='Reservation released.',moved_away='Reservation released: moved away.',session_ended='Arena session ended.',session_invalid='Arena session is no longer valid.',left_arena='Returned to the saved position.',no_nearby_panel='No glass panel in inspection range.',invalid_position='Invalid player position.',invalid_action='Unknown interaction action.',already_reserved='This is already your reservation.'}
local debug=false
local function inside()return PSG.ready and getElementDimension(localPlayer)==PSG_CONFIG.dimension and getElementInterior(localPlayer)==0 end
function PSG.updateInteractions()
    PSG.nearbyZone=nil;PSG.interactionHint=nil
    if not inside() or isPedDead(localPlayer) or isPedInVehicle(localPlayer) then return end
    local x,y,z=getElementPosition(localPlayer);local o=PSG_CONFIG.origin;local best,distance
    for _,zone in ipairs(PSG_CONFIG.interactionZones) do
        local d=(x-o[1]-zone.position[1])^2+(y-o[2]-zone.position[2])^2
        if d<=zone.radius^2 and math.abs(z-o[3]-zone.position[3])<=zone.verticalTolerance and (not distance or d<distance) then best=zone;distance=d end
    end
    if best then
        PSG.nearbyZone=best.id
        local yours=PSG.interactionState and PSG.interactionState.zone==best.id
        local key=PSG_CONFIG.interactionKey
        PSG.interactionHint=(type(key)=='string' and '['..string.upper(key)..'] ' or '[/psg_use] ')..best.label..(yours and ' / YOUR RESERVATION' or slots[best.id] and ' / OCCUPIED' or '')
    end
end
function PSG.useNearestInteraction()
    if not inside() or not PSG.nearbyZone or isChatBoxInputActive() or isConsoleActive() or isMainMenuActive() or isCursorShowing() then return end
    triggerServerEvent('psg:interaction',resourceRoot,PSG_CONFIG.protocol,'use',PSG.nearbyZone)
end
function PSG.startInteractions()
    local key=PSG_CONFIG.interactionKey
    if type(key)=='string' and not bindKey(key,'down',PSG.useNearestInteraction) then outputDebugString('[PSG] Interaction key binding failed; use /psg_use instead',1) end
end
function PSG.stopInteractions()
    if type(PSG_CONFIG.interactionKey)=='string' then unbindKey(PSG_CONFIG.interactionKey,'down',PSG.useNearestInteraction) end
    debug=false;slots={};PSG.nearbyZone=nil;PSG.interactionHint=nil;PSG.interactionState=nil
end
addEvent('psg:slots',true)
addEventHandler('psg:slots',resourceRoot,function(snapshot)
    if source~=resourceRoot or type(snapshot)~='table' then return end
    for id,value in pairs(snapshot) do if known[id] and known[id].kind=='tug_slot' and type(value)=='boolean' then slots[id]=value end end
    PSG.updateInteractions()
end)
addEvent('psg:interactionReply',true)
addEventHandler('psg:interactionReply',resourceRoot,function(ok,reason,data)
    if source~=resourceRoot or type(ok)~='boolean' or type(reason)~='string' then return end
    if ok and reason=='panel_info' and type(data)=='table' and type(data.id)=='string' and type(data.state)=='string' then
        outputChatBox('[PSG] '..data.id:sub(1,32)..' / '..data.state:sub(1,16)..' / row '..tostring(data.row):sub(1,4)..' '..tostring(data.side):sub(1,8)..' / '..tostring(data.material):sub(1,32));return
    end
    if ok and data==false then PSG.interactionState=nil
    elseif ok and type(data)=='table' and known[data.zone] then PSG.interactionState={zone=data.zone,kind=known[data.zone].kind} end
    if reasons[reason] then outputChatBox('[PSG] '..reasons[reason]) end
end)
addCommandHandler('psg_debug',function()debug=not debug;outputChatBox('[PSG] Station guides: '..tostring(debug)..' (local diagnostic only)')end)
addEventHandler('onClientRender',root,function()
    if not inside() then return end
    local w,h=guiGetScreenSize()
    if PSG.interactionHint then dxDrawText(PSG.interactionHint,0,h-85,w,h-40,tocolor(210,235,245),1.1,'default-bold','center','center') end
    if not debug then return end
    local o=PSG_CONFIG.origin
    for index,route in ipairs(PSG_CONFIG.inspectionRoutes) do
        local color=index==1 and tocolor(30,190,220) or index==2 and tocolor(210,40,120) or tocolor(225,170,80)
        for i=1,#route.points-1 do
            local a,b=route.points[i],route.points[i+1]
            dxDrawLine3D(o[1]+a[1],o[2]+a[2],o[3]+a[3],o[1]+b[1],o[2]+b[2],o[3]+b[3],color,2)
        end
    end
    for _,zone in ipairs(PSG_CONFIG.interactionZones) do
        local x,y,z=o[1]+zone.position[1],o[2]+zone.position[2],o[3]+.06
        local radius=zone.radius;local color=slots[zone.id] and tocolor(245,160,60) or tocolor(30,200,220)
        dxDrawLine3D(x-radius,y-radius,z,x+radius,y-radius,z,color,2)
        dxDrawLine3D(x+radius,y-radius,z,x+radius,y+radius,z,color,2)
        dxDrawLine3D(x+radius,y+radius,z,x-radius,y+radius,z,color,2)
        dxDrawLine3D(x-radius,y+radius,z,x-radius,y-radius,z,color,2)
        if zone.heading then
            local angle=math.rad(zone.heading);dxDrawLine3D(x,y,z,x-math.sin(angle)*.6,y+math.cos(angle)*.6,z,color,2)
        end
    end
end)
