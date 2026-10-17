"""Execute real server scripts with multiple-handler mocks and two-player contention.
Not a running MTA server, physics test or network-security certification.
"""
from pathlib import Path
import json,hashlib
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
vm=LuaRuntime(unpack_returned_tuples=True)
vm.execute('''
root={kind='root'};resourceRoot={kind='resource'};handlers={};commands={};sent={};timers={};players={};tick=10000
function isElement(e)return type(e)=='table' and e.kind~=nil and not e.deleted end
function getElementType(e)return e.kind end
function addEvent()end
function addEventHandler(name,attached,fn)handlers[name]=handlers[name] or {};table.insert(handlers[name],fn)end
function addCommandHandler(name,fn)commands[name]=fn end
function emit(name,element,sender,...)source=element;client=sender;for _,fn in ipairs(handlers[name] or {})do fn(...)end end
function getTickCount()return tick end
function triggerClientEvent(target,name,element,...)table.insert(sent,{target=target,name=name,args={...}})end
function getElementsByType(kind)return players end
function outputChatBox()end
function isPedDead(p)return p.dead end
function isPedInVehicle(p)return p.vehicle end
function getElementPosition(p)return p.x,p.y,p.z end
function setElementPosition(p,x,y,z)p.x=x;p.y=y;p.z=z end
function getElementRotation(p)return 0,0,p.rz end
function setElementRotation(p,x,y,z)p.rz=z end
function getElementDimension(p)return p.dimension end
function setElementDimension(p,d)p.dimension=d end
function getElementInterior(p)return p.interior end
function setElementInterior(p,d)p.interior=d end
function hasObjectPermissionTo(p)return p.admin==true end
function setTimer(fn)local t={fn=fn};timers[t]=true;return t end
function isTimer(t)return timers[t]==true end
function killTimer(t)timers[t]=nil end
function lastEvent(p,name)for i=#sent,1,-1 do local e=sent[i];if e.target==p and e.name==name then return e end end end
function player(x)local p={kind='player',x=x,y=20,z=30,dimension=4,interior=2,rz=75};table.insert(players,p);return p end
function maintenance()tick=tick+501;for t in pairs(timers)do t.fn()end end
function interact(p,action,id,delay)tick=tick+(delay or 401);emit('psg:interaction',resourceRoot,p,PSG_CONFIG.protocol,action,id)end
function at(p,id)local a;for _,z in ipairs(PSG_CONFIG.interactionZones)do if z.id==id then a=z.position end end;assert(a);p.x=PSG_CONFIG.origin[1]+a[1];p.y=PSG_CONFIG.origin[2]+a[2];p.z=PSG_CONFIG.origin[3]+a[3]end
function enter(p)emit('psg:loadStatus',resourceRoot,p,PSG_CONFIG.protocol,true);commands.psg(p,'psg','enter');local e=lastEvent(p,'psg:prepare');assert(e);emit('psg:prepared',resourceRoot,p,e.args[2])end
function reason(p)return lastEvent(p,'psg:interactionReply').args[2]end
''')
for path in ['shared/config.lua','server/main.lua','server/arena_state.lua','server/interactions.lua']:vm.execute((ROOT/path).read_text(),name=path)
vm.execute('''
p=player(10);q=player(11);r=player(12)
-- Matching dimension and client-ready alone cannot substitute for a managed session.
emit('psg:loadStatus',resourceRoot,r,PSG_CONFIG.protocol,true);r.dimension=2601;r.interior=0;at(r,'TW_left_1')
interact(r,'use','TW_left_1');assert(reason(r)=='session_required' and not getSlotOccupant('TW_left_1'))
enter(p);enter(q);at(p,'TW_left_1');at(q,'TW_left_1')
local n=#sent;emit('psg:interaction',resourceRoot,p,'wrong','use','TW_left_1');assert(#sent==n)
emit('psg:interaction',p,p,PSG_CONFIG.protocol,'use','TW_left_1');assert(#sent==n)
interact(p,'use',{});assert(reason(p)=='invalid_zone' and not getSlotOccupant('TW_left_1'))
interact(p,'use','unknown');assert(reason(p)=='invalid_zone' and not getSlotOccupant('TW_left_1'))
interact(p,'setPanelState','GB_01_L');assert(reason(p)=='invalid_action' and getPanelState('GB_01_L')=='intact')
interact(p,'use','TW_left_1');assert(getSlotOccupant('TW_left_1')==p and getInteractionState(p).zone=='TW_left_1')
local state=getInteractionState(p);state.zone='tampered';assert(getInteractionState(p).zone=='TW_left_1')
interact(q,'use','TW_left_1');assert(reason(q)=='occupied' and not getInteractionState(q))
interact(q,'release','TW_left_1');assert(getSlotOccupant('TW_left_1')==p,'cannot release another owner')
-- Bad destinations cannot silently fall back to nearest or drop an existing reservation.
interact(p,'use','invalid');assert(getSlotOccupant('TW_left_1')==p)
interact(p,'use','TW_right_1');assert(reason(p)=='too_far' and getSlotOccupant('TW_left_1')==p)
local n=#sent;interact(p,'release',nil,0);assert(#sent==n and getSlotOccupant('TW_left_1')==p,'rate limit')
p.x=p.x+2;maintenance();assert(not getSlotOccupant('TW_left_1') and not getInteractionState(p))
-- Cooldown remains valid across the signed 32-bit tick transition.
at(p,'TW_left_1');tick=2147483600;interact(p,'use','TW_left_1',0);assert(getSlotOccupant('TW_left_1')==p)
tick=-2147483295;interact(p,'release',nil,0);assert(not getSlotOccupant('TW_left_1'))
interact(p,'use','TW_left_1',1);assert(not getSlotOccupant('TW_left_1'),'wrap cooldown')
interact(q,'use','TW_left_1');assert(getSlotOccupant('TW_left_1')==q)
q.vehicle=true;maintenance();assert(not getInteractionState(q));q.vehicle=false
-- Both clients may acknowledge bridge entry; it is not an exclusive seat/round.
at(p,'GB_START');at(q,'GB_START');interact(p,'use','GB_START');interact(q,'use','GB_START')
assert(getInteractionState(p).kind=='bridge_entry' and getInteractionState(q).kind=='bridge_entry')
-- Panel query picks canonical nearby panel, does not trust a requested panel ID or mutate it.
p.x=PSG_CONFIG.origin[1]+45.1;p.y=PSG_CONFIG.origin[2]-18.4;p.z=PSG_CONFIG.origin[3]+1
assert(setPanelState('GB_01_L','marked'));interact(p,'inspect_panel','GB_18_R')
local info=lastEvent(p,'psg:interactionReply');assert(info.args[2]=='panel_info' and info.args[3].id=='GB_01_L' and info.args[3].state=='marked')
assert(getPanelState('GB_18_R')=='intact')
at(p,'EXIT');interact(p,'inspect_panel');assert(reason(p)=='no_nearby_panel')
-- Non-finite positions, bad heights, different interior and excessive horizontal distance fail.
at(p,'TW_left_1');p.z=p.z+10;interact(p,'use','TW_left_1');assert(reason(p)=='too_far')
at(p,'TW_left_1');p.x=0/0;interact(p,'use','TW_left_1');assert(reason(p)=='too_far')
at(p,'TW_left_1');p.interior=1;interact(p,'use','TW_left_1');assert(reason(p)=='session_required');p.interior=0
at(p,'TW_left_1');tick=tick+401;commands.psg_use(p,'psg_use');assert(getSlotOccupant('TW_left_1')==p)
-- Invalid destination occupancy preserves an old claim when both are in approach range.
at(q,'TW_left_2');interact(q,'use','TW_left_2');assert(getSlotOccupant('TW_left_2')==q)
p.x=PSG_CONFIG.origin[1]-18.1;tick=tick+401;commands.psg_use(p,'psg_use','TW_left_2')
assert(reason(p)=='occupied' and getSlotOccupant('TW_left_1')==p)
emit('psg:loadStatus',resourceRoot,p,PSG_CONFIG.protocol,false);assert(not getInteractionState(p) and p.dimension==4 and p.x==10)
-- Reentry and exit-zone use restore original session coordinates and release the station.
enter(p);at(p,'TW_right_1');interact(p,'use','TW_right_1');assert(getSlotOccupant('TW_right_1')==p)
at(p,'EXIT');interact(p,'use','EXIT');assert(p.dimension==4 and p.interior==2 and p.x==10 and not getSlotOccupant('TW_right_1'))
-- Death and quit run all relevant handlers, not only the last registered callback.
emit('onPlayerWasted',q,nil);assert(q.dimension==4 and q.x==11 and not getInteractionState(q))
enter(q);at(q,'TW_right_2');interact(q,'use','TW_right_2');emit('onPlayerQuit',q,nil);q.deleted=true;assert(not getSlotOccupant('TW_right_2'))
enter(p);at(p,'TW_left_3');interact(p,'use','TW_left_3');emit('onResourceStop',resourceRoot,nil)
assert(p.dimension==4 and p.x==10 and not getInteractionState(p) and next(timers)==nil)
''')
result={'status':'PASS','script_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['shared/config.lua','server/main.lua','server/arena_state.lua','server/interactions.lua']},'scope':'Actual Lua 5.1 scripts against mocked APIs; NOT real MTA physics, networking, UI or anti-cheat validation','tests':['managed-session/ready/dimension/interior/on-foot eligibility','protocol and event-source rejection','invalid/remote/NaN/height checks with canonical positions','two-player exclusive slot contention and own-only release','unknown destination does not select nearest or drop an old claim','copy-only state query prevents external table mutation','request rate limit including signed tick transition and release-on-drift/vehicle','nonexclusive bridge entry acknowledgement','nearby panel readback ignores arbitrary requested IDs; no client mutation','load-loss/exit/death/quit/stop cleanup restores session and releases slots','multiple event handlers retained in mocks; timer removed on stop']}
(ROOT/'tests/interaction_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
