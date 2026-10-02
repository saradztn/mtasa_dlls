# Created by: Arena.ai Agent Mode (AI) - headless smoke test of the Castle MTA resource (stubbed MTA API, runs the real Lua files)
import math, os, sys
from lupa import LuaRuntime
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resource', 'Castle')
lua = LuaRuntime(unpack_returned_tuples=True)
log, objs, timers, cmds, handlers = [], {}, [], {}, {}
state = dict(t=0, nid=0)

player = dict(pos=[100.0, 200.0, 20.0], rz=90.0, dead=False)
g = lua.globals()
def create(model, x, y, z, rx, ry, rz):
    state['nid'] += 1; o = lua.table(id=state['nid']); objs[state['nid']] = dict(model=model, pos=[x, y, z], rot=[rx, ry, rz], dim=0, int=0, alive=True); return o
def getobj(o): return objs[o['id']]
def isElement(e): return e is not None and hasattr(e, '__getitem__') and not isinstance(e, str) and 'id' in e and objs.get(e['id'], {}).get('alive', False) or (e is not None and e == 'PLAYER')
def destroy(e): objs[e['id']]['alive'] = False; return True
def move(o, t, x, y, z, rx, ry, rz, ease=None):
    d = getobj(o); log.append(('move', d['model'], round(rz, 1))); d['rot'][2] += rz; return True
def setTimer(fn, ms, n):
    timers.append(dict(fn=fn, ms=ms, n=n, next=state['t'] + ms, alive=True)); return lua.table(tid=len(timers) - 1)
def killTimer(t): timers[t['tid']]['alive'] = False; return True
def isTimer(t): return t is not None and timers[t['tid']]['alive']
def step(ms):
    end = state['t'] + ms
    while True:
        due = [t for t in timers if t['alive'] and t['next'] <= end]
        if not due: break
        t = min(due, key=lambda x: x['next']); state['t'] = t['next']; t['fn']()
        if t['n'] == 1: t['alive'] = False
        else: t['next'] += t['ms']
    state['t'] = end
msgs = []
api = dict(
    createObject=create, destroyElement=destroy, isElement=isElement, moveObject=move, setTimer=setTimer, killTimer=killTimer, isTimer=isTimer,
    getElementPosition=lambda e: tuple(player['pos']) if e == 'PLAYER' else tuple(getobj(e)['pos']),
    getElementRotation=lambda e: (0, 0, player['rz']) if e == 'PLAYER' else tuple(getobj(e)['rot']),
    getElementDimension=lambda e: 0, getElementInterior=lambda e: 0, setElementDimension=lambda e, d: True, setElementInterior=lambda e, d: True,
    setObjectBreakable=lambda e, b: True, isPedInVehicle=lambda p: False, isPedDead=lambda p: player['dead'],
    getElementsByType=lambda t: lua.table('PLAYER'), outputChatBox=lambda *a: msgs.append(a[0]),
    addCommandHandler=lambda n, f: cmds.__setitem__(n, f), addEventHandler=lambda *a: handlers.__setitem__(a[0], a[2]),
    resourceRoot='ROOT', getAccountName=lambda a: 'x', getPlayerAccount=lambda p: 'x', isObjectInACLGroup=lambda *a: True, aclGetGroup=lambda n: 'g')
for k, v in api.items(): g[k] = v
g.string = lua.eval('string')
for f in ('ids.lua', 'doors_data.lua', 'server.lua'):
    lua.execute(open(os.path.join(RES, f), encoding='utf8').read())
assert 'showx' in cmds and 'hidex' in cmds
cmds['showx']('PLAYER')
assert any('castle stands' in m for m in msgs), msgs
alive = [o for o in objs.values() if o['alive']]
print('objects after /showx:', len(alive), [o['model'] for o in alive])
assert len(alive) == 12 and [o['model'] for o in alive[:4]] == [12853, 12859, 12860, 12861]
# player faces rz=90 (west): forward = (-1,0); origin should be 16 m west of the player
print('castle origin', alive[0]['pos'], 'yaw', alive[0]['rot'][2])
assert abs(alive[0]['pos'][0] - 84.0) < 1e-6 and abs(alive[0]['pos'][1] - 200.0) < 1e-6
# gate centre in world: local (0,0.6) -> rotate 90 -> (-0.6, 0)
step(1000); assert not log, 'doors must stay closed when the player is far from them'
player['pos'] = [84.0 + 0.6, 200.0 - 0.0, 20.5]            # a bit outside the gate, local y = -0.6
step(2000)
print('on approach:', log)
assert sum(1 for l in log if l[1] == 12854) == 2, 'both gate leaves must open'
player['pos'] = [500, 500, 20]; n = len(log); step(3000)
print('after leaving:', log[n:]); assert sum(1 for l in log[n:] if l[1] == 12854) == 2, 'gate must close again'
player['dead'] = True; player['pos'] = [84.0, 200.0, 20.5]; n = len(log); step(2000); assert len(log) == n, 'dead players do not trigger doors'
cmds['hidex']('PLAYER')
assert not [o for o in objs.values() if o['alive']], 'hidex must remove everything'
cmds['showx']('PLAYER'); cmds['showx']('PLAYER')
assert len([o for o in objs.values() if o['alive']]) == 12, 'showx twice must not duplicate'
print('SERVER LUA OK')
# client script: syntax + simulated start with stubs
lua2 = LuaRuntime(unpack_returned_tuples=True); calls = []
g2 = lua2.globals(); g2.resourceRoot = 'ROOT'; hs = {}
for n in ('engineLoadTXD', 'engineLoadDFF', 'engineLoadCOL'):
    g2[n] = (lambda n: lambda f: (calls.append((n, f)), lua2.table(name=f))[1])(n)
for n in ('engineReplaceCOL', 'engineImportTXD', 'engineReplaceModel', 'removeWorldModel', 'engineSetModelLODDistance', 'engineRestoreModel',
          'engineResetModelLODDistance', 'restoreWorldModel'):
    g2[n] = (lambda n: lambda *a: (calls.append((n,) + tuple(a[1:] if n.startswith('engineRe') or n == 'engineImportTXD' else a)), True)[1])(n)
g2.outputChatBox = lambda *a: calls.append(('chat', a[0])); g2.outputDebugString = lambda *a: calls.append(('dbg', a[0]))
lua2.execute(open(os.path.join(RES, 'ids.lua'), encoding='utf8').read())
g2.addEventHandler = lambda e, r, f: hs.__setitem__(e, f); g2.isElement = lambda e: True; g2.destroyElement = lambda e: True
lua2.execute(open(os.path.join(RES, 'client.lua'), encoding='utf8').read())
hs['onClientResourceStart'](); hs['onClientResourceStop']()
names = [c[0] for c in calls]
print('client calls:', {n: names.count(n) for n in sorted(set(names))})
assert 'dbg' not in names and names.count('engineReplaceModel') == 6 and names.count('engineReplaceCOL') == 6 and names.count('removeWorldModel') == 6
assert names.count('restoreWorldModel') == 6
for f in ('files/Castle.dff', 'files/CastleGate.dff', 'files/CastleDoor.dff', 'files/Castle.txd', 'files/Castle.col', 'files/CastleGate.col', 'files/CastleDoor.col'):
    assert os.path.getsize(os.path.join(RES, f)) > 0
import re
meta = open(os.path.join(RES, 'meta.xml')).read()
for src in re.findall(r'src="([^"]+)"', meta): assert os.path.isfile(os.path.join(RES, src)), src
print('CLIENT LUA OK, meta.xml files all exist')
