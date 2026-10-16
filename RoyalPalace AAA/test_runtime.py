#!/usr/bin/env python3
"""Execute the ACTUAL Royal Fortress Lua (server + client) under Lua 5.1 against deterministic MTA API stubs.
These are unit/integration tests of script logic. They are NOT in-game tests: nothing is rendered and no
MTA client is involved. Results are written to docs/runtime_tests.json."""
import json, sys, traceback, time, xml.etree.ElementTree as ET
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT = Path(__file__).resolve().parent.parent


def base():
    lua = LuaRuntime(unpack_returned_tuples=True)
    def table(v):
        if isinstance(v, dict): return lua.table_from({k: table(x) for k, x in v.items()})
        if isinstance(v, list): return lua.table_from([table(x) for x in v])
        return v
    lua.globals()['__readFile'] = lambda p: (ROOT / p).read_bytes() if (ROOT / p).is_file() else None
    lua.globals()['__fromJSON'] = lambda raw: table(json.loads(raw))
    lua.execute((ROOT / 'tools/mta_mock.lua').read_text(), name='mta_mock')
    return lua


def server():
    lua = base()
    lua.execute('function getElementType(e)return isElement(e) and e.kind or false end')
    for p in ('shared/config.lua', 'server/main.lua'): lua.execute((ROOT / p).read_text(), name=p)
    lua.execute('''function _ready_player(...)local p=_player(...);_event("rf:hello",p,RFConfig.build);return p end
function _partNear(id,n)local part=RFServer.interactive[id].parts[n or 1];return part.center[1],part.center[2],part.center[3]-0.5 end''')
    return lua


def client():
    lua = base()
    lua.execute((ROOT / 'tools/client_mock.lua').read_text(), name='client_mock')
    lua.execute('localPlayer=_player(0,0,10,0,0)')
    meta = ET.parse(ROOT / 'meta.xml').getroot()
    for s in meta.findall('script'):
        if s.get('type') in ('shared', 'client'): lua.execute((ROOT / s.get('src')).read_text(), name=s.get('src'))
    lua.execute('_emit("onClientResourceStart",resourceRoot);assert(RFClient.ready)')
    return lua


SERVER = {
'startup loads the manifest and default mechanism states': r'''
local n=0;for _ in pairs(RFServer.interactive) do n=n+1 end;assert(n==27,"mechanisms "..n)
local r=0;for _ in pairs(RFServer.rooms) do r=r+1 end;assert(r==109,"rooms "..r)
assert(RFServer.states.drawbridge==false,"drawbridge rests lowered (open)")
assert(RFServer.states.main_portcullis==true,"portcullis default open = lifted")
assert(RFServer.states.treasury_door==false and RFServer.states.cell_2==true and RFServer.states.cell_1==false)
''',
'clients that have not said hello cannot travel; build mismatch is refused': r'''
local p=_player(100,200,10,0,0);_command("castle",p);assert(not RFServer.pending[p] and not _lastEvent("rf:prepare",p))
_event("rf:hello",p,"0.0.1");assert(not RFServer.ready[p])
_event("rf:hello",p,RFConfig.build);assert(RFServer.ready[p] and _lastEvent("rf:states",p))
_command("castle",p);assert(RFServer.pending[p] and _lastEvent("rf:prepare",p))
''',
'/castle full handshake, forged tokens ignored, /castleleave restores exactly': r'''
local p=_ready_player(120,-240,21,4,2);p.rz=73
_command("castle",p);local t=RFServer.pending[p];assert(t and not p.frozen and p.dim==4,"no movement before preparation")
_event("rf:prepared",p,"forged");assert(not t.committed)
_prepare(p);local g=RFServer.teleports.gate
assert(p.dim==779 and p.int==0 and p.frozen and math.abs(p.x-g.pos[1])<1e-6 and math.abs(p.z-(g.pos[3]+1.0))<1e-6)
_event("rf:groundReady",p,"forged");assert(RFServer.pending[p]==t)
_ready(p);assert(not p.frozen and not RFServer.pending[p] and RFServer.sessions[p])
_command("castleleave",p);_assertOrigin(p,120,-240,21,4,2);assert(p.rz==73 and not RFServer.sessions[p] and _lastEvent("rf:leave",p))
''',
'asset failure before commit never moves the player': r'''
local p=_ready_player(-80,30,12,9,3);_command("showp",p);local t=RFServer.pending[p]
_event("rf:loadFailed",p,t.token,"missing COL");_assertOrigin(p,-80,30,12,9,3);assert(not p.frozen and not RFServer.pending[p] and not RFServer.sessions[p])
assert(_lastEvent("rf:rollback",p))
''',
'collision timeout after commit rolls back to the origin': r'''
local p=_ready_player(20,40,18,3,0);_command("castleinterior",p);_prepare(p);assert(p.dim==779)
_advance(RFConfig.transactionTimeout+10);_assertOrigin(p,20,40,18,3,0);assert(not p.frozen and not RFServer.sessions[p])
''',
'vehicles, dead players and travel spam are refused': r'''
local p=_ready_player(0,0,5,0,0);local v=_vehicle(0,0,5,0,0);warpPedIntoVehicle(p,v,0)
_command("castle",p);assert(not RFServer.pending[p]);removePedFromVehicle(p)
p.dead=true;_command("castle",p);assert(not RFServer.pending[p]);p.dead=false
_command("castle",p);_prepare(p);_ready(p);_command("castleinterior",p);assert(not RFServer.pending[p],"cooldown")
_advance(RFConfig.travelCooldown+1);_command("castleinterior",p);assert(RFServer.pending[p])
''',
'/castleroom validates ids and enforces ACL for locked rooms': r'''
local p=_ready_player(0,0,5,0,0)
_command("castleroom",p);assert(not RFServer.pending[p])
_command("castleroom",p,"999");assert(not RFServer.pending[p])
_command("castleroom",p,"26");assert(not RFServer.pending[p],"treasury needs the vault key")
p.rights={["resource.royal_fortress.vault"]=true};_command("castleroom",p,"26");assert(RFServer.pending[p])
local q=_ready_player(0,0,5,0,0);_command("castleroom",q,"k1");local t=RFServer.pending[q];assert(t and t.target.pos[3]==RFServer.rooms.K1.spawn[3])
''',
'doors: range check, toggle broadcast, cooldown, ACL locks': r'''
local p=_ready_player(0,0,5,0,0);_command("castleinterior",p);_prepare(p);_ready(p)
local far=RFServer.states.throne_doors;p.x,p.y,p.z=0,0,2517.5;_event("rf:interact",p,"throne_doors");assert(RFServer.states.throne_doors==far,"far player must not operate")
p.x,p.y,p.z=_partNear("throne_doors");_advance(1000);_event("rf:interact",p,"throne_doors");assert(RFServer.states.throne_doors~=far)
local e=_lastEvent("rf:state");assert(e and e.player==root and e.args[1]=="throne_doors")
_advance(1000);local s=RFServer.states.throne_doors;_event("rf:interact",p,"throne_doors");assert(RFServer.states.throne_doors==s,"still moving")
p.x,p.y,p.z=_partNear("treasury_door");_advance(2000);_event("rf:interact",p,"treasury_door");assert(RFServer.states.treasury_door==false,"locked without key")
p.rights={["resource.royal_fortress.vault"]=true};_advance(2000);_event("rf:interact",p,"treasury_door");assert(RFServer.states.treasury_door==true)
_event("rf:interact",p,string.rep("x",80));_event("rf:interact",p,42)
''',
'secret bookcase only moves through its lever; lever springs back': r'''
local p=_ready_player(0,0,5,0,0);_command("castleinterior",p);_prepare(p);_ready(p)
p.x,p.y,p.z=_partNear("library_bookcase");_event("rf:interact",p,"library_bookcase");assert(RFServer.states.library_bookcase==false)
p.x,p.y,p.z=_partNear("book_lever");_advance(1000);_event("rf:interact",p,"book_lever")
assert(RFServer.states.library_bookcase==true and RFServer.states.book_lever==true)
_advance(RFConfig.animTime+500);assert(RFServer.states.book_lever==false and RFServer.states.library_bookcase==true)
''',
'drawbridge and portcullis are gate-key mechanisms': r'''
local p=_ready_player(0,0,5,0,0);_command("castle",p);_prepare(p);_ready(p)
p.x,p.y,p.z=_partNear("drawbridge");_event("rf:interact",p,"drawbridge");assert(RFServer.states.drawbridge==false)
p.rights={["resource.royal_fortress.gate"]=true};_advance(1000);_event("rf:interact",p,"drawbridge");assert(RFServer.states.drawbridge==true,"raised")
_command("castledoor",p,"main_portcullis");assert(RFServer.states.main_portcullis==false,"lowered via admin command")
''',
'/castledebug and /castlereload require their rights': r'''
local p=_ready_player(0,0,5,0,0);_command("castledebug",p);assert(not _lastEvent("rf:debug",p))
_command("castlereload",p);assert(not _lastEvent("rf:reload"))
local a=_ready_player(0,0,5,0,0);a.admin=true;_command("castledebug",a);local e=_lastEvent("rf:debug",a);assert(e and e.args[1]==true)
RFServer.states.treasury_door=true;_command("castlereload",a);assert(_lastEvent("rf:reload") and RFServer.states.treasury_door==false)
''',
'void watchdog returns fallen players to the gate': r'''
local p=_ready_player(0,0,5,0,0);_command("castleinterior",p);_prepare(p);_ready(p)
p.z=2400;_advance(2100);local t=RFServer.pending[p];assert(t and t.target==RFServer.teleports.gate)
''',
'quit, death and resource stop clean up': r'''
local p=_ready_player(5,6,7,1,0);_command("castle",p);_prepare(p);_emit("onPlayerWasted",p);_assertOrigin(p,5,6,7,1,0)
local q=_ready_player(8,9,10,2,0);_advance(5000);_command("castle",q);_prepare(q);_ready(q)
_emit("onResourceStop",resourceRoot);_assertOrigin(q,8,9,10,2,0)
local r=_ready_player(1,1,1,0,0);_advance(5000);_command("castle",r);_emit("onPlayerQuit",r);assert(not RFServer.pending[r] and not RFServer.ready[r])
''',
}

CLIENT = {
'startup parses world.json once and says hello with the build': r'''
assert(RFScene.data and #RFScene.data.objects==419);assert(#__serverEvents==1 and __serverEvents[1].name=="rf:hello" and __serverEvents[1].args[1]==RFConfig.build)
''',
'travel: COL->TXD->DFF order, shared anchor, required set, collision handshake, environment': r'''
local g=RFScene.data.teleports.gate.pos;__floorZ=g[3]
_emit("rf:prepare",resourceRoot,"tok1",g);_advance(15000)
local prep=false;for _,e in ipairs(__serverEvents) do if e.name=="rf:prepared" then prep=true end end;assert(prep,"prepared not sent")
local first={};for i,n in ipairs(__assetCalls) do if not first[n] then first[n]=i end end
assert(first.COL<first.TXD and first.TXD<first.importTXD and first.importTXD<first.DFF,"load order")
local imports=0;for _,n in ipairs(__assetCalls) do if n=="importTXD" then imports=imports+1 end end;assert(imports<=3,"each TXD imported once")
local n=0;for _ in pairs(RFScene.objects) do n=n+1 end;assert(n>=64,"terrain + structures resident: "..n)
setElementDimension(localPlayer,779);setElementPosition(localPlayer,g[1],g[2],g[3]+1)
_emit("rf:committed",resourceRoot,"tok1",g);_advance(300)
local ready=false;for _,e in ipairs(__serverEvents) do if e.name=="rf:groundReady" then ready=true end end;assert(ready,"groundReady")
assert(RFClient.active and isElement(RFClient.water) and RFClient.water.dim==779 and getWeather()==1 and getFarClipDistance()==1500)
_emit("rf:finished",resourceRoot,"tok1");assert(not RFClient.pending)
_emit("rf:leave",resourceRoot);assert(not RFClient.active and getWeather()==3 and getFarClipDistance()==900 and not isElement(RFClient.water))
assert(not next(RFModels.loaded) and not next(__ids),"all models freed")
''',
'missing floor collision never acknowledges ground': r'''
local g=RFScene.data.teleports.interior.pos;__noFloor=true
_emit("rf:prepare",resourceRoot,"tok2",g);_advance(15000);setElementDimension(localPlayer,779);setElementPosition(localPlayer,g[1],g[2],g[3]+1)
_emit("rf:committed",resourceRoot,"tok2",g);_advance(2000)
for _,e in ipairs(__serverEvents) do assert(e.name~="rf:groundReady") end;__noFloor=false
''',
'asset failure reports loadFailed and unwinds': r'''
__fail="DFF";_emit("rf:prepare",resourceRoot,"tok3",RFScene.data.teleports.gate.pos);_advance(5000)
local f=false;for _,e in ipairs(__serverEvents) do if e.name=="rf:loadFailed" then f=true end end;assert(f);__fail=false
_emit("rf:rollback",resourceRoot,"tok3","x");assert(not RFClient.pending and not next(RFModels.loaded))
''',
'streamer respects the object budget and /castlehide keeps walkable surfaces': r'''
local p=RFScene.data.rooms["3"].spawn
_emit("rf:prepare",resourceRoot,"tok4",p);_advance(20000);setElementDimension(localPlayer,779);setElementPosition(localPlayer,p[1],p[2],p[3]+1)
_emit("rf:committed",resourceRoot,"tok4",p);_advance(300);_emit("rf:finished",resourceRoot,"tok4");_advance(30000)
local n,furn,rooms=0,0,0
for id,r in pairs(RFScene.objects) do n=n+1;local c=RFScene.data.objects[r.index].class;if c=="furn" then furn=furn+1 elseif c=="room" then rooms=rooms+1 end end
assert(n<=RFConfig.streaming.maxObjects and furn>0 and rooms>0,"n="..n)
_clientCommand("castlehide");_advance(2000)
local f2,r2=0,0;for id,r in pairs(RFScene.objects) do local c=RFScene.data.objects[r.index].class;if c=="furn" or c=="tree" then f2=f2+1 elseif c=="room" then r2=r2+1 end end
assert(f2==0 and r2==rooms,"hidden furniture, rooms kept");_clientCommand("castlehide")
''',
'mechanisms: parts spawn in rest/moved pose, animate with relative rotation, E key sends the nearest id': r'''
local p=RFScene.data.rooms["3"].spawn
_emit("rf:prepare",resourceRoot,"tok5",p);_advance(20000);setElementDimension(localPlayer,779);setElementPosition(localPlayer,p[1],p[2],p[3]+1)
_emit("rf:committed",resourceRoot,"tok5",p);_advance(300);_emit("rf:finished",resourceRoot,"tok5")
_emit("rf:states",resourceRoot,{{"throne_doors",false},{"main_portcullis",true}});_advance(1000)
local rec=RFScene.data.interactive.throne_doors;local part=rec.parts[1];local key="throne_doors#1"
assert(RFMech.parts[key],"door leaf streamed near the throne hall")
local e=RFMech.parts[key].element;assert(math.abs(e.rz-part.rot[3])<1e-6)
_emit("rf:state",resourceRoot,"throne_doors",true,true);local mv=__moves[#__moves-1]
assert(mv and math.abs(mv.rz-part.open.rot[3])<1e-6 and mv.t==RFConfig.animTime,"relative swing")
local c=part.pos;setElementPosition(localPlayer,c[1],c[2]-1.2,c[3]+1);_advance(400);assert(RFMech.prompt and RFMech.prompt.id=="throne_doors","prompt")
__keys.e();local last=__serverEvents[#__serverEvents];assert(last.name=="rf:interact" and last.args[1]=="throne_doors")
''',
'/castletime overrides locally and auto resumes; night lamps produce coronas within budget': r'''
local p=RFScene.data.teleports.gate.pos
_emit("rf:prepare",resourceRoot,"tok6",p);_advance(15000);setElementDimension(localPlayer,779);setElementPosition(localPlayer,p[1],p[2],p[3]+1)
_emit("rf:committed",resourceRoot,"tok6",p);_advance(300)
_clientCommand("castletime","23");local h=getTime();assert(h==23 and getMinuteDuration()==60000000)
_advance(700);assert(#RFLights.coronas<=RFConfig.lights.maxCoronas)
_clientCommand("castletime","auto");assert(getMinuteDuration()==1000 and not RFClient.timeOverride)
_clientCommand("castletime","99")
''',
'/castlelist pages and filters; /castlehelp prints': r'''
local before=#__messages;_clientCommand("castlelist");assert(#__messages-before==13,"header + 12")
before=#__messages;_clientCommand("castlelist","military");assert(#__messages-before>3)
before=#__messages;_clientCommand("castlehelp");assert(#__messages-before==3)
''',
'server reload rebuilds the client scene': r'''
_emit("rf:reload",resourceRoot,{{"treasury_door",true}});assert(RFScene.data and RFMech.states.treasury_door==true)
''',
}


def run(kind, tests, make):
    out = []
    for name, code in tests.items():
        t = time.time()
        try:
            lua = make(); lua.execute(code, name=name); ok, err = True, ''
        except Exception as ex:
            ok, err = False, ''.join(traceback.format_exception_only(type(ex), ex)).strip()
        out.append({'suite': kind, 'test': name, 'status': 'PASS' if ok else 'FAIL', 'error': err, 'seconds': round(time.time() - t, 2)})
        print(('PASS' if ok else 'FAIL'), kind, '-', name, ('' if ok else '\n    ' + err[:600]))
    return out


if __name__ == '__main__':
    res = run('server', SERVER, server) + run('client', CLIENT, client)
    passed = sum(r['status'] == 'PASS' for r in res)
    (ROOT / 'docs' / 'runtime_tests.json').write_text(json.dumps({'type': 'Lua 5.1 (lupa) execution of the real resource scripts against MTA API stubs - NOT an in-game test',
                                                                  'passed': passed, 'total': len(res), 'results': res}, indent=1))
    print('%d/%d runtime tests passed' % (passed, len(res)))
    sys.exit(0 if passed == len(res) else 1)
