from pathlib import Path
import json,hashlib
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
vm=LuaRuntime(unpack_returned_tuples=True)
vm.execute('''
root={};resourceRoot={};source=resourceRoot;localPlayer={dimension=0};handlers={};commands={};live={};models={};timers={};serial=0;logs={};sent={};keys={};chat=false;draws=0;importCalls=0;camera={4978,4997,105}
function make(kind) serial=serial+1;local e={id=serial,kind=kind};live[e]=true;return e end
function isElement(e)return live[e]==true end
function destroyElement(e)assert(live[e]);live[e]=nil end
function addEvent()end
function addEventHandler(n,r,f)local old=handlers[n];if old then handlers[n]=function(...)old(...);f(...)end else handlers[n]=f end end
function addCommandHandler(n,f)commands[n]=f end
function outputDebugString(s)table.insert(logs,s)end
function outputChatBox()end
function engineRequestModel()serial=serial+1;models[serial]=true;return serial end
function engineFreeModel(n)assert(models[n]);models[n]=nil end
function engineRestoreModel()end
function engineRestoreCOL()end
function engineLoadTXD()if failTXD then return false end;return make('txd')end
function engineLoadCOL()if failCOL then return false end;return make('col')end
function engineLoadDFF()return make('dff')end
function engineImportTXD()importCalls=importCalls+1;if failImport and (failImport=='all' or importCalls==failImport) then return false end;return true end
function engineReplaceCOL()return true end
function engineReplaceModel()return true end
function engineSetModelLODDistance()end
function setElementModel(e,id)if failModel then return false end;e.model=id;return true end
function createObject(id,x,y,z)local e=make('object');e.x=x;e.y=y;e.z=z;return e end
function setElementDimension(e,d)e.dimension=d end
function setElementInterior()end
function setElementDoubleSided()end
function setElementCollisionsEnabled(e,v)e.collision=v end
function setElementAlpha(e,a)e.alpha=a end
function getElementDimension(e)return e.dimension end
function getElementInterior(e)return e.interior or 0 end
function getElementPosition(e)return e.x or 0,e.y or 0,e.z or 0 end
function isPedDead(e)return e.dead end
function isPedInVehicle(e)return e.vehicle end
function bindKey(key,state,fn)if failKey then return false end;assert(not keys[key]);keys[key]=fn;return true end
function unbindKey(key,state,fn)if keys[key]==fn then keys[key]=nil end;return true end
function isChatBoxInputActive()return chat end
function isConsoleActive()return console end
function isMainMenuActive()return menu end
function isCursorShowing()return cursor end
function guiGetScreenSize()return 640,480 end
function tocolor()return 0 end
function dxDrawText()draws=draws+1 end
function dxDrawLine3D()draws=draws+1 end
function dxCreateShader()if failShader then return false end;return make('shader'),'genesis' end
function dxCreateTexture()if failTexture then return false end;return make('texture')end
function dxSetShaderValue()return not failParameter end
function engineApplyShaderToWorldTexture()return not failBinding end
function engineRemoveShaderFromWorldTexture()return true end
function getCameraMatrix()return unpack(camera)end
function triggerServerEvent(...)table.insert(sent,{...})end
function setTimer(f)local t={f=f};timers[t]=true;return t end
function isTimer(t)return timers[t]==true end
function killTimer(t)timers[t]=nil end
function getTime()return 12,25 end
function getWeather()return 0 end
function getMinuteDuration()return 1000 end
function getFarClipDistance()return 1000 end
function getFogDistance()return 500 end
function setTime()end
function setMinuteDuration()end
function setWeather()end
function setFarClipDistance()end
function setFogDistance()end
function count(t)local n=0;for _ in pairs(t)do n=n+1 end;return n end
''')
for p in ('shared/config.lua','client/materials.lua','client/lighting.lua','client/wet_surface.lua','client/arenas.lua','client/lod.lua','client/interactions.lua','client/main.lua'):vm.execute((ROOT/p).read_text())
vm.execute('''
handlers.onClientResourceStart();assert(PSG.ready and #PSG.objects==45 and #PSG.ids==11 and #PSG.shaders==16)
local n=#sent;handlers['psg:prepare']('bad','request');assert(#sent==n)
handlers['psg:prepare'](PSG_CONFIG.protocol,'request');assert(sent[#sent][1]=='psg:prepared' and sent[#sent][3]=='request')
local quality=PSG.quality;failTXD=true;commands.psg_quality('psg_quality','LOW');assert(PSG.quality==quality);failTXD=false
localPlayer.dimension=2601;for t in pairs(timers)do t.f()end
assert(keys.e==PSG.useNearestInteraction)
localPlayer.x=PSG_CONFIG.origin[1]-18.9;localPlayer.y=PSG_CONFIG.origin[2];localPlayer.z=PSG_CONFIG.origin[3]+1
PSG.updateInteractions();assert(PSG.nearbyZone=='TW_left_1')
local sentBefore=#sent;chat=true;keys.e();assert(#sent==sentBefore);chat=false
console=true;keys.e();console=false;menu=true;keys.e();menu=false;cursor=true;keys.e();cursor=false;assert(#sent==sentBefore)
keys.e();assert(sent[#sent][1]=='psg:interaction' and sent[#sent][4]=='use' and sent[#sent][5]=='TW_left_1')
source={};handlers['psg:slots']({TW_left_1=true});handlers['psg:interactionReply'](true,'reserved',{zone='TW_left_1'});assert(not PSG.interactionState and not PSG.interactionHint:find('OCCUPIED'));source=resourceRoot
handlers['psg:slots']({TW_left_1=true,invalid=true});assert(PSG.interactionHint:find('OCCUPIED'))
handlers['psg:interactionReply'](true,'reserved',{zone='TW_left_1',kind='forged'});assert(PSG.interactionState.kind=='tug_slot')
handlers['psg:interactionReply'](true,'released',false);assert(not PSG.interactionState)
local countBefore=count(live);handlers.onClientRender();commands.psg_debug();handlers.onClientRender();assert(draws>0 and count(live)==countBefore,'HUD allocated elements')
localPlayer.dimension=0;PSG.updateInteractions();assert(not PSG.nearbyZone);localPlayer.dimension=2601

-- Object identity and allocations remain stable across rope tier changes.
local rope=PSG.rope;local ropeResources=count(live)
camera={5000,5000,101};PSG.updateLOD();assert(PSG.ropeTier=='high')
camera={5000,5033,101};PSG.updateLOD();assert(PSG.ropeTier=='low' and PSG.rope==rope and not rope.collision)
camera={5000,5028,101};PSG.updateLOD();assert(PSG.ropeTier=='low','hysteresis band')
camera={5000,5020,101};PSG.updateLOD();assert(PSG.ropeTier=='high' and count(live)==ropeResources)
failModel=true;camera={5000,5060,101};PSG.updateLOD();assert(PSG.ropeTier=='high');failModel=false
-- Moving along the cable endpoint does not select LOD using midpoint distance.
camera={5021,5000,101};PSG.updateLOD();assert(PSG.ropeTier=='high')
-- Failed import into one ID must reimport the old dictionary into every ID.
local oldQuality=PSG.quality;importCalls=0;failImport=3;commands.psg_quality('psg_quality','MEDIUM');assert(PSG.quality==oldQuality and PSG.ready and importCalls==3+#PSG.ids);failImport=nil

handlers['psg:panels']({GB_01_L='broken'});assert(PSG.panelObjects.GB_01_L.alpha==0 and not PSG.panelObjects.GB_01_L.collision)
handlers['psg:panels']({GB_01_L='intact'});assert(PSG.panelObjects.GB_01_L.collision)
commands.psg_quality('psg_quality','LOW');commands.psg_quality('psg_quality','MEDIUM');commands.psg_quality('psg_quality','HIGH')
local before=count(live);for i=1,8 do commands.psg_quality('psg_quality','LOW');commands.psg_quality('psg_quality','HIGH') end;assert(count(live)==before,'tier switching leaks')
-- Shader parameter, texture allocation and binding failures must be reported as fallback.
for _,failure in ipairs({'texture','parameter','binding'}) do
    failTexture=failure=='texture';failParameter=failure=='parameter';failBinding=failure=='binding'
    PSG.loadMaterials();assert(#PSG.shaders==0)
    for _,status in pairs(PSG.materialStatus) do assert(status.state=='fallback') end
end
failTexture=false;failParameter=false;failBinding=false;PSG.loadMaterials();assert(#PSG.shaders==16)
importCalls=0;failImport='all';commands.psg_quality('psg_quality','LOW');assert(not PSG.ready and sent[#sent][1]=='psg:loadStatus' and sent[#sent][4]==false);failImport=nil
handlers.onClientResourceStop();assert(count(live)==0 and count(models)==0 and count(timers)==0 and #PSG.lightSlots==0 and next(keys)==nil)
failShader=true;handlers.onClientResourceStart();assert(#PSG.shaders==0 and #PSG.objects==45);handlers.onClientResourceStop();assert(count(live)==0)
failShader=false;handlers.onClientResourceStart();destroyElement(PSG.objects[1]);handlers['psg:prepare'](PSG_CONFIG.protocol,'broken-world');assert(not PSG.ready and sent[#sent][1]=='psg:loadStatus' and sent[#sent][4]==false);handlers.onClientResourceStop()
failCOL=true;handlers.onClientResourceStart();assert(not PSG.ready and count(live)==0 and count(models)==0 and count(timers)==0)
local n=#sent;commands.psg_quality('psg_quality','HIGH');assert(#sent==n and count(live)==0)
failCOL=false;PSG_CONFIG.interactionKey=false;handlers.onClientResourceStart();assert(PSG.ready and next(keys)==nil);handlers.onClientResourceStop()
PSG_CONFIG.interactionKey='e';failKey=true;handlers.onClientResourceStart();assert(PSG.ready and next(keys)==nil);handlers.onClientResourceStop();assert(count(live)==0 and count(models)==0 and next(timers)==nil);failKey=false

''')
result={'status':'PASS','tool':'Lua 5.1 via lupa','tests':['45 objects / 11 allocated IDs / 16 shader instances','panel collision state update','quality cycling has stable live-resource count after cache warmup','stop leaves zero tracked elements/models/timers','shader allocation failure falls back to geometry','COL failure rolls back loaded elements and model IDs','client acknowledges only matching protocol with live world','lost world sends not-ready; no teleport acknowledgement','failed tier load retains old quality','quality command is disabled after failed startup','rope LOD hysteresis retains object identity and live resource count','rope LOD model-switch failure retains old tier','native tier import failure rolls back every ID','rollback failure disables entry and reports load loss','texture/parameter/binding failures destroy partial material resources','nearby interaction uses canonical ID and suppresses key while chatting','slot/reply HUD state validation and zero element allocations in draw path','interaction key unbound and local state cleared on stop','disabled/failed key binding keeps manual-command fallback and cleanup','non-resource reply/slot source rejected; console/menu/cursor suppress use'],'script_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['shared/config.lua','client/materials.lua','client/lighting.lua','client/wet_surface.lua','client/arenas.lua','client/lod.lua','client/interactions.lua','client/main.lua']},'scope':'Mock API tests. Does NOT compile shader, render pixels, test GTA streaming or prove MTA compatibility.'}
(ROOT/'tests/client_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
