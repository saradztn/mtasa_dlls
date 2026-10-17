-- Acknowledgements protect normal loading/restart failures, not a malicious client's renderer.
local saved,ready,pending={},{},{}
local serial=0
local places={enter={0,-44,1},tug={-22,-3,1},glass={46,-23,1}}
local function restore(p)
    pending[p]=nil
    if PSG_releaseInteraction then PSG_releaseInteraction(p,'session_ended') end
    local s=saved[p];if not s or not isElement(p) then return end
    setElementInterior(p,s.interior);setElementDimension(p,s.dimension)
    setElementPosition(p,s.x,s.y,s.z);setElementRotation(p,0,0,s.rz);saved[p]=nil
end
addEvent('psg:loadStatus',true)
addEventHandler('psg:loadStatus',resourceRoot,function(protocol,loaded)
    if not client or source~=resourceRoot or type(loaded)~='boolean' then return end
    if protocol~=PSG_CONFIG.protocol or not loaded then
        ready[client]=nil;restore(client);return
    end
    ready[client]=true
end)
function PSG_isClientReady(p)return ready[p]==true end
function PSG_hasArenaSession(p)return saved[p]~=nil end
function PSG_leaveArena(p)restore(p)end
addCommandHandler('psg',function(p,_,place)
    if not isElement(p) or getElementType(p)~='player' then return end
    if place=='leave' then restore(p);return end
    if not places[place] or isPedDead(p) or isPedInVehicle(p) then
        outputChatBox('/psg enter|tug|glass|leave (on foot, alive)',p);return
    end
    if not ready[p] then outputChatBox('[PSG] Assets not ready. Entry refused; check client debugscript 3.',p);return end
    serial=serial+1
    local token=tostring(getTickCount())..':'..tostring(serial)
    pending[p]={place=place,token=token,started=getTickCount()}
    -- No movement, state change or freeze until the exact request is acknowledged.
    triggerClientEvent(p,'psg:prepare',resourceRoot,PSG_CONFIG.protocol,token)
end)
addEvent('psg:prepared',true)
addEventHandler('psg:prepared',resourceRoot,function(token)
    if not client or source~=resourceRoot or type(token)~='string' then return end
    local p=client;local request=pending[p]
    if not ready[p] or not request or token~=request.token then return end
    pending[p]=nil
    if (getTickCount()-request.started)%4294967296>5000 or isPedDead(p) or isPedInVehicle(p) then return end
    if not saved[p] then
        local x,y,z=getElementPosition(p);local _,_,rz=getElementRotation(p)
        saved[p]={x=x,y=y,z=z,rz=rz,dimension=getElementDimension(p),interior=getElementInterior(p)}
    end
    local o=PSG_CONFIG.origin;local a=places[request.place]
    setElementInterior(p,0);setElementDimension(p,PSG_CONFIG.dimension)
    setElementPosition(p,o[1]+a[1],o[2]+a[2],o[3]+a[3])
    if PSG_syncInteractions then PSG_syncInteractions(p) end
end)
addEventHandler('onPlayerQuit',root,function()saved[source]=nil;ready[source]=nil;pending[source]=nil end)
addEventHandler('onPlayerWasted',root,function()restore(source)end)
addEventHandler('onResourceStop',resourceRoot,function()
    for p in pairs(saved) do restore(p) end
    saved={};ready={};pending={}
end)
