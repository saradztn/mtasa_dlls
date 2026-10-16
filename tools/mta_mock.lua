-- Test-only deterministic MTA API stub. This never creates a game world or renders.
root={_element=true,kind="root"};resourceRoot={_element=true,kind="resource"}
local elements,handlers,commands,timers={},{},{},{}
local clock=10000
__events={};__messages={};__debug={};__registeredEvents={}
function isElement(e)return type(e)=="table" and e._element==true and not e.destroyed end
function getElementType(e)return isElement(e) and e.kind or false end
function _element(kind,x,y,z,dim,int)
 local e={_element=true,kind=kind,x=x or 0,y=y or 0,z=z or 0,dim=dim or 0,int=int or 0,rx=0,ry=0,rz=0,frozen=false,data={},occupants={},health=kind=="vehicle" and 1000 or 100,vt="Automobile",vx=0,vy=0,vz=0}
 elements[#elements+1]=e;return e
end
function _player(...)return _element("player",...)end
function _vehicle(...)return _element("vehicle",...)end
function getElementsByType(kind) local a={};for _,e in ipairs(elements) do if isElement(e) and e.kind==kind then a[#a+1]=e end end;return a end
function getElementPosition(e)if e.vehicle then return getElementPosition(e.vehicle) end;return e.x,e.y,e.z end
function setElementPosition(e,x,y,z)e.x=x;e.y=y;e.z=z;return true end
function getElementRotation(e)return e.rx,e.ry,e.rz end
function setElementRotation(e,x,y,z)e.rx=x;e.ry=y;e.rz=z;return true end
function getElementVelocity(e)return e.vx,e.vy,e.vz end
function setElementVelocity(e,x,y,z)e.vx=x;e.vy=y;e.vz=z;return true end
function getElementDimension(e)return e.dim end
function setElementDimension(e,v)e.dim=v;return true end
function getElementInterior(e)return e.int end
function setElementInterior(e,v)e.int=v;return true end
function isElementFrozen(e)return e.frozen end
function setElementFrozen(e,v)e.frozen=v;return true end
function getElementHealth(e)return e.health end
function isPedDead(e)return e.dead==true end
function getVehicleType(e)return e.vt end
function getVehicleTowedByVehicle(v)return v.trailer or false end
function getVehicleTowingVehicle(v)return v.towing or false end
function detachTrailerFromVehicle(v,t)v.trailer=nil;if t then t.towing=nil end;return true end
function getVehicleOccupants(e)return e.occupants end
function getVehicleOccupant(e,seat)return e.occupants[seat or 0] or false end
function getPedOccupiedVehicle(e)return e.vehicle or false end
function getPedOccupiedVehicleSeat(e)return e.seat or false end
function warpPedIntoVehicle(p,v,seat)
 if p.vehicle then removePedFromVehicle(p) end
 seat=seat or 0;p.vehicle=v;p.seat=seat;v.occupants[seat]=p;p.dim=v.dim;p.int=v.int;return true
end
function removePedFromVehicle(p)
 if not p.vehicle then return false end
 local v=p.vehicle;p.x=v.x;p.y=v.y;p.z=v.z;v.occupants[p.seat]=nil;p.vehicle=nil;p.seat=nil;return true
end
function setElementData(e,k,v)e.data[k]=v;return true end
function getElementData(e,k)return e.data[k] or false end
function removeElementData(e,k)e.data[k]=nil;return true end
function createVehicle(model,x,y,z,rx,ry,rz)local v=_vehicle(x,y,z);v.model=model;v.rx=rx or 0;v.ry=ry or 0;v.rz=rz or 0;return v end
function setVehicleColor()return true end
function outputChatBox(text,p)table.insert(__messages,{text=text,player=p});return true end
function outputDebugString(text,level)__debug[#__debug+1]={text=text,level=level};return true end
function outputServerLog(text)__debug[#__debug+1]={text=text,level=3};return true end
function triggerClientEvent(p,event,source,...)
 __events[#__events+1]={player=p,name=event,source=source,args={...}};return isElement(p)
end
function triggerServerEvent()return true end
function setCameraTarget(p,t)p.camera=t;return true end
function fadeCamera(p,value)p.fade=value;return true end
function getTickCount()return clock end
function addEvent(name,remote)if __registeredEvents[name]~=nil then return false end;__registeredEvents[name]=remote==true;return true end
function _isEventRegistered(name)return __registeredEvents[name]~=nil end
function addEventHandler(name,target,fn)
 handlers[name]=handlers[name] or {};table.insert(handlers[name],{target=target,fn=fn});return true
end
function _emit(name,element,...)
 local oldSource,oldClient=source,client;source=element;client=nil
 for _,h in ipairs(handlers[name] or {}) do if h.target==root or h.target==element then h.fn(...) end end
 source=oldSource;client=oldClient
end
function _event(name,player,...)
 local os,oc=source,client;source=resourceRoot;client=player
 for _,h in ipairs(handlers[name] or {}) do if h.target==root or h.target==resourceRoot then h.fn(...) end end
 source=os;client=oc
end
function addCommandHandler(name,fn,restricted)commands[name]=fn;return true end
function _command(name,p,...)assert(commands[name],"missing command "..name);commands[name](p,name,...)end
function _clientCommand(name,...)assert(commands[name],"missing client command "..name);commands[name](name,...)end
function hasObjectPermissionTo(p,right,default)assert(default==false,'explicit default required');return p.admin==true or (p.rights~=nil and p.rights[right]==true) end
function setTimer(fn,delay,times,...)
 local t={fn=fn,due=clock+delay,delay=delay,times=times,args={...},active=true}
 timers[#timers+1]=t;return t
end
function isTimer(t)return type(t)=="table" and t.active==true end
function killTimer(t)t.active=false;return true end
function _advance(ms)
 local finish=clock+ms;local rounds=0
 while true do
  local nextTimer=false
  for _,t in ipairs(timers) do if t.active and t.due<=finish and (not nextTimer or t.due<nextTimer.due) then nextTimer=t end end
  if not nextTimer then break end
  rounds=rounds+1;assert(rounds<10000,"timer loop")
  local t=nextTimer;clock=t.due
  if t.times==1 then t.active=false else if t.times>1 then t.times=t.times-1 end;t.due=t.due+t.delay end
  t.fn(unpack(t.args))
 end
 clock=finish
end
function destroyElement(e)
 if not isElement(e) then return false end
 if e.kind=="player" and e.vehicle then removePedFromVehicle(e) end
 if e.kind=="vehicle" then local pp={};for _,p in pairs(e.occupants) do pp[#pp+1]=p end;for _,p in ipairs(pp) do removePedFromVehicle(p) end end
 _emit("onElementDestroy",e);e.destroyed=true;return true
end
function fileOpen(path)local raw=__readFile(path);if not raw then return false end;return {data=raw,pos=1}end
function fileGetSize(f)return #f.data end
function fileRead(f,n)local s=f.data:sub(f.pos,f.pos+n-1);f.pos=f.pos+n;return s end
function fileClose()return true end
function fileExists(path)return __readFile(path)~=nil end
function fromJSON(s)return __fromJSON(s)end
function _assertOrigin(p,x,y,z,dim,int)
 local a,b,c=getElementPosition(p)
 assert(math.abs(a-x)<.001 and math.abs(b-y)<.001 and math.abs(c-z)<.001,"position was not restored")
 assert(p.dim==dim and p.int==int,"dimension/interior was not restored")
end
function _prepare(p)
 local t=RFServer.pending[p];assert(t and not t.committed,"no prepare transaction")
 _event("rf:prepared",p,t.token);return t
end
function _ready(p)local t=RFServer.pending[p];assert(t and t.committed,"no collision transaction");_event("rf:groundReady",p,t.token);return t end
function _lastEvent(name,p)
 for i=#__events,1,-1 do if __events[i].name==name and (not p or __events[i].player==p) then return __events[i] end end
 return false
end
