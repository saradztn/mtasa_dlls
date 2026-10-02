# Created by: Arena.ai Agent Mode (AI) - headless smoke test of the Ashfall MTA resource (stubbed MTA API, runs the REAL Lua files)
#   python3 mta_lua_test_af.py
import math
import os
import sys
from lupa import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'resource', 'Ashfall')
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute(open(os.path.join(HERE, 'mta_stub.lua')).read())
T = lua.globals().T
rd = lambda f: open(os.path.join(RES, f), encoding='utf8').read()
for d, _, fs in os.walk(os.path.join(RES, 'files')):
    for f in fs:
        T.files[os.path.relpath(os.path.join(d, f), RES)] = True
T.files['wind.fx'] = True
T.files['post.fx'] = True
fails = []


def check(c, msg):
    print('  [%s] %s' % ('PASS' if c else 'FAIL', msg))
    if not c:
        fails.append(msg)


def logs():
    return [T.log[i] for i in range(1, len(T.log) + 1)]


def chat():
    return [T.chat[i] for i in range(1, len(T.chat) + 1)]


def frames(n, ms=50):
    for _ in range(n):
        T.frame(ms)


def alive(k):
    return int(T.alive(k))


for f in ('models.lua', 'layout.lua', 'client.lua'):
    lua.eval('function(n, s) return T.load("client", n, s) end')(f, rd(f))
lua.eval('function(n, s) return T.load("server", n, s) end')('layout.lua', rd('layout.lua'))
lua.eval('function(n, s) return T.load("server", n, s) end')('server.lua', rd('server.lua'))
G = T.sides.client
localPlayer_x = lambda: lua.eval('localPlayer.x')
localPlayer_y = lambda: lua.eval('localPlayer.y')
localPlayer_z = lambda: lua.eval('localPlayer.z')
N_LAYOUT = len(G.AF_OBJECTS)
N_TILES = sum(1 for m in G.AF_MODELS.values() if m['ox'] is not None)
N_MODELS = len(G.AF_MODELS)
print('objects in layout: %d + %d ground tiles, models: %d' % (N_LAYOUT, N_TILES, N_MODELS))

print('\n-- start, /showcity --')
T.fireC('onClientResourceStart')
check('toClient:city:hide' in logs(), 'resource start: client asks, server answers "no city yet"')
T.setPlayer(2000, -1700, 15)
T.cmd('server', 'showcity')
check(abs(float(localPlayer_z()) - 902.0) < 0.01 and abs(float(localPlayer_y()) + 62.0) < 0.01, 'default /showcity teleports the player to the sky city spawn (0,-62,902)')
check(bool(lua.eval('localPlayer.frozen')), 'client freezes the player while the ground is being built')
check(any('city:show' in l for l in logs()), 'server sent city:show')
frames(3)
check(int(T.liveTimers()) > 0, 'loading is chunked over timers (not one long freeze)')
frames(160)
check(not bool(lua.eval('localPlayer.frozen')), 'player is released after the ground exists')
check(len(T.models) == N_MODELS and int(T.replaced) == N_MODELS, '%d model ids requested and %d DFF replaced' % (len(T.models), int(T.replaced)))
check(alive('object') == N_LAYOUT + N_TILES, 'all %d objects created (%d layout + %d tiles; alive %d)' % (N_LAYOUT + N_TILES, N_LAYOUT, N_TILES, alive('object')))
used = set(int(o[1]) for o in G.AF_OBJECTS.values()) | set(i for i, m in G.AF_MODELS.items() if m['ox'] is not None)
check(len(used) == N_MODELS, 'every one of the %d models is instantiated at least once (unused: %s)' % (N_MODELS, sorted(set(range(1, N_MODELS + 1)) - used)))

# water
rects = [list(e.args.values()) for e in [T.elems[i] for i in range(1, len(T.elems) + 1)] if e.kind == 'water' and e.alive]
good = all(len(a) == 12 and all(float(v).is_integer() for v in a[:2] + a[3:5] + a[6:8] + a[9:11]) and all(int(v) % 2 == 0 for v in a[:2] + a[3:5] + a[6:8] + a[9:11]) for a in rects)
check(len(rects) >= 50 and good, 'lake: %d water rectangles, all x/y even integers (%s)' % (len(rects), 'ok' if good else 'BAD'))
L = G.AF_LAKE
AX, AY, AZ = 0.0, 0.0, 900.0
miss = tested = 0
for iu in range(-86, 87, 4):
    for iv in range(-86, 87, 4):
        u, v = iu / 100.0, iv / 100.0
        if u * u + v * v > 0.80 ** 2:
            continue
        x, y = AX + L.cx + u * L.rx, AY + L.cy + v * L.ry
        tested += 1
        if not any(a[0] <= x <= a[3] and a[1] <= y <= a[7] for a in rects):
            miss += 1
check(miss == 0, 'lake water covers the bowl (%d sample points, %d uncovered)' % (tested, miss))
wl = rects[0][2]
check(abs(wl - (AZ + L.z)) < 1e-6, 'water level %.2f = anchor z + lake z %.2f' % (wl, L.z))

check(not any(l.startswith('dbg:') for l in logs()), 'no debug errors: %s' % [l for l in logs() if l.startswith('dbg:')][:3])
check(any('District Zero is in front of you' in m for m in chat()), 'ready message shown: %s' % [m for m in chat() if 'District' in m][:1])
frames(20)
snd = {k: int(lua.eval('function(t,k) return t[k] or 0 end')(T.sounds_played, 'files/audio/' + k + '.wav')) for k in ('wind_loop', 'rumble_loop', 'crickets_loop')}
check(snd['wind_loop'] == 1 and snd['rumble_loop'] == 1 and snd['crickets_loop'] == 4, 'looping sounds started: %s' % snd)

print('\n-- /cityz --')
objs = [T.elems[i] for i in range(1, len(T.elems) + 1) if T.elems[i].kind == 'object' and T.elems[i].alive]
z0 = objs[0].z
T.cmd('server', 'cityz', '0.5')
frames(4)
objs = [T.elems[i] for i in range(1, len(T.elems) + 1) if T.elems[i].kind == 'object' and T.elems[i].alive]
check(abs(objs[0].z - (z0 + 0.5)) < 1e-6, 'cityz +0.5 moves objects (%.2f -> %.2f)' % (z0, objs[0].z))
T.cmd('server', 'cityz', '-0.5')
frames(4)

print('\n-- /citywind --')
check(alive('shader') == 1 and alive('screensource') == 1, 'cinematic grade started with the city (shader + screen source)')
T.advance(100)
T.fireC('onClientHUDRender')
check(int(T.screenUpdates or 0) >= 1, 'grade renders: screen source updated in onClientHUDRender')
T.cmd('client', 'citywind')
check(alive('shader') == 2, 'wind shader ON creates a shader element')
T.cmd('client', 'citywind')
check(alive('shader') == 1, 'wind shader OFF destroys it')
T.cmd('client', 'cityfx')
check(alive('shader') == 0 and alive('screensource') == 0, '/cityfx OFF destroys shader and screen source')
T.cmd('client', 'cityfx')
check(alive('shader') == 1 and alive('screensource') == 1, '/cityfx ON again')

print('\n-- /hidecity --')
T.setPlayer(10, -60, 903)
T.cmd('server', 'hidecity')
check(abs(float(localPlayer_x()) - 2495.0) < 0.01, 'hidecity sends players standing on the sky city to a safe place')
frames(2)
loops = [T.elems[i] for i in range(1, len(T.elems) + 1) if T.elems[i].kind == 'sound' and T.elems[i].alive and str(T.elems[i].file or '').find('_loop') >= 0]
check(alive('shader') == 0 and alive('screensource') == 0, 'hidecity stops the grade')
check(alive('object') == 0 and alive('water') == 0 and len(loops) == 0, 'hidecity removes objects (%d), water (%d), loop sounds (%d)' % (alive('object'), alive('water'), len(loops)))

print('\n-- /showcity here (on the ground) + fall guard --')
T.setPlayer(500, 600, 21)
T.cmd('server', 'showcity', 'here')
frames(160)
check(abs(float(localPlayer_x()) - 500) < 0.01 and abs(float(localPlayer_z()) - 21) < 0.01, 'showcity here keeps the player where he stands')
z1 = [T.elems[i] for i in range(1, len(T.elems) + 1) if T.elems[i].kind == 'object' and T.elems[i].alive][0].z
check(abs(z1 - ((21 - 1.0) + float(G.AF_OBJECTS[1][4]))) < 0.5, 'ground anchor z follows the player (%.2f)' % z1)
T.cmd('server', 'hidecity')
frames(4)
T.setPlayer(0, 0, 0)
T.cmd('server', 'showcity')
frames(160)
T.setPlayer(20, 20, 850)
frames(30)
T.advance(1500)
check(float(localPlayer_z()) > 890, 'fall guard returns a player who fell off the sky city (z %.1f)' % float(localPlayer_z()))

print('\n-- resource stop --')
T.cmd('server', 'showcity')
frames(140)
n_obj = alive('object')
T.fireC('onClientResourceStop')
check(alive('object') == 0, 'stop: objects destroyed (%d before)' % n_obj)
check(len(T.freed) == N_MODELS, 'stop: all %d model ids freed (%d)' % (N_MODELS, len(T.freed)))

print('\n%d checks failed' % len(fails))
sys.exit(1 if fails else 0)
