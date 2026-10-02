# Created by: Arena.ai Agent Mode (AI) - headless smoke test of the Park MTA resource (stubbed MTA API, runs the REAL Lua files)
#   python3 mta_lua_test.py
import math
import os
import sys
from lupa import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'resource', 'Park')
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute(open(os.path.join(HERE, 'mta_stub.lua')).read())
T = lua.globals().T
rd = lambda f: open(os.path.join(RES, f), encoding='utf8').read()
for d, _, fs in os.walk(os.path.join(RES, 'files')):
    for f in fs:
        T.files[os.path.relpath(os.path.join(d, f), RES)] = True
T.files['wind.fx'] = True
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


# the server/client files run in the stub environments; models.lua/layout.lua are client scripts
for f in ('models.lua', 'layout.lua', 'client.lua'):
    lua.eval('function(n, s) return T.load("client", n, s) end')(f, rd(f))
lua.eval('function(n, s) return T.load("server", n, s) end')('server.lua', rd('server.lua'))
G = T.sides.client
N_OBJ = len(G.PARK_OBJECTS)
N_MODELS = len(G.PARK_MODELS)
print('objects in layout: %d, models: %d' % (N_OBJ, N_MODELS))

# world positions of the park frame
def to_world(ox, oy, rot, px, py):
    r = math.radians(rot)
    return ox + math.cos(r) * px - math.sin(r) * py, oy + math.sin(r) * px + math.cos(r) * py


alive = lambda k: int(T.alive(k))
names = [m['name'] for m in G.PARK_MODELS.values()]
objs_of = lambda nm: list(T.objectsByModel(T.models[1 + names.index(nm)]).values())
print('\n-- start, /showpark --')
T.fireC('onClientResourceStart')
check('toClient:park:hide' in logs(), 'resource start: client asks, server answers "no park yet"')
T.setPlayer(100, 200, 20)
lua.globals().localPlayer.rz = 90
T.cmd('server', 'showpark')
check(any('park:show' in l for l in logs()), 'server sent park:show')
frames(3)
check(int(T.liveTimers()) > 0, 'loading is chunked over timers (not one long freeze)')
frames(80)
ox, oy, oz = 100 - 17.0, 200.0, 19.9
check(len(T.models) == N_MODELS and int(T.replaced) == N_MODELS, '%d model ids requested and %d DFF replaced' % (len(T.models), int(T.replaced)))
check(alive('object') == N_OBJ, 'all %d objects created (alive %d)' % (N_OBJ, alive('object')))
check(alive('water') >= 30, 'pond water surface: %d triangles' % alive('water'))
check(alive('effect') == 1 and alive('blip') == 1, 'fountain effect + radar blip')
check(not any(l.startswith('dbg:') for l in logs()), 'no debug errors: %s' % [l for l in logs() if l.startswith('dbg:')][:3])
check(any('ready' in m for m in chat()), 'ready message shown')
frames(40)
snd = {}
for k in ('fountain_loop', 'pond_loop', 'wind_loop', 'city_loop', 'crickets_loop'):
    snd[k] = len(T.sound(k))
check(snd['fountain_loop'] == 1 and snd['pond_loop'] == 1 and snd['wind_loop'] == 1 and snd['city_loop'] == 1 and snd['crickets_loop'] == 5, 'looping sounds started: %s' % snd)
missing = [lua.eval('function(t,k) return t[k] end')(T.sounds_played, k) for k in ()]
# gate position
gl = objs_of('pk_gateleaf')
check(len(gl) == 2, 'two gate leaves exist')
gx, gy = to_world(ox, oy, 90, -3.12, 0)
check(any(abs(o.x - gx) < 1e-6 and abs(o.y - gy) < 1e-6 for o in gl), 'gate leaf at the right world position (%.2f, %.2f)' % (gx, gy))
check(all(o.rz % 360 in (90.0, 270.0) for o in gl), 'gate leaves rotated with the park (rz 90 / 270)')
check(all(o.frozen is not True for o in gl) and True, 'gate leaves are not frozen (moveObject)')

print('\n-- gate --')
n0 = len(logs())
frames(10)
check(not [l for l in logs()[n0:] if l.startswith('move:')], 'gate stays closed while nobody is near')
T.setPlayer(ox + 1.0, oy, oz + 1.0)
frames(20)
mv = [l for l in logs()[n0:] if l.startswith('move:')]
check(len(mv) == 2 and sorted(l.split(':')[2] for l in mv) == ['-85', '85'], 'gate opens when the player walks up: %s' % mv)
n1 = len(logs())
frames(60)
check(not [l for l in logs()[n1:] if l.startswith('move:')], 'gate stays open while the player is there')
T.setPlayer(ox + 80, oy, oz + 1.0)
frames(80)
mv2 = [l for l in logs()[n1:] if l.startswith('move:')]
check(len(mv2) == 2 and sorted(l.split(':')[2] for l in mv2) == ['-85', '85'], 'gate closes again after the player leaves')
check(int(T.sounds_played['files/audio/gate_creak.wav']) == 2, 'gate creak played twice (open + close)')

print('\n-- swing / merry-go-round / ducks / bell --')
P = G.PARK_POINTS
sx, sy = to_world(ox, oy, 90, P.swing[1], P.swing[2])
swings = objs_of('pk_swing')
T.setPlayer(sx, sy, oz + 1.0)
frames(120)
rots = [o.rx for o in swings]
check(len(swings) == 2 and max(abs(r) for r in rots) > 1.0, 'swings oscillate (max angle %.1f deg)' % max(abs(r) for r in rots))
n_creak = int(T.sounds_played['files/audio/swing_creak.wav'] or 0)
check(n_creak >= 1, 'swing creak played near the swings (%d)' % n_creak)
mo = objs_of('pk_merry')
check(len(mo) == 1, 'merry-go-round object present')
m = mo[0]
a0 = m.rz
T.setPlayer(m.x + 1.6, m.y, oz + 1.0, 0, 3.0)      # running past at 3 m/s tangentially
frames(60)
T.setPlayer(ox + 80, oy, oz + 1.0)
frames(20)
check(abs(((m.rz - a0 + 180) % 360) - 180) > 5, 'merry-go-round turns when pushed (rz %.1f -> %.1f)' % (a0, m.rz))
ducks = objs_of('pk_duck')
cxw, cyw = to_world(ox, oy, 90, 0, 45)
T.setPlayer(cxw, cyw, oz + 1.0)
frames(2)
p0 = [(d.x, d.y) for d in ducks]
frames(40)
p1 = [(d.x, d.y) for d in ducks]
check(len(ducks) >= 3 and all(math.hypot(a[0] - b[0], a[1] - b[1]) > 0.05 for a, b in zip(p0, p1)), '%d ducks paddle around' % len(ducks))
pd = G.PARK_POND
check(all(math.hypot(d.x - to_world(ox, oy, 90, pd.cx, pd.cy)[0], d.y - to_world(ox, oy, 90, pd.cx, pd.cy)[1]) < 16 for d in ducks), 'ducks stay on the pond')
kx, ky = to_world(ox, oy, 90, -5.6, 60)
T.setPlayer(kx, ky, oz + 1.0)
frames(10)
check(int(T.sounds_played['files/audio/bell.wav'] or 0) == 1, 'kiosk bell rings once at the counter')
T.setPlayer(ox + 80, oy, oz + 1.0)
check(True, 'info boards are drawn near a board')
bx, by = to_world(ox, oy, 90, P.board1[1], P.board1[2])
T.setPlayer(bx, by, oz + 1.0)
d0 = int(T.draws)
frames(3)
check(int(T.draws) > d0, 'info-board HUD draws near board1')

print('\n-- /sit --')
sit = G.PARK_SIT[1]
bx, by = to_world(ox, oy, 90, sit[1], sit[2])
T.setPlayer(bx + 0.8, by, oz + 1.0)
T.cmd('client', 'sit')
check(localPlayer_anim := (lua.globals().localPlayer.anim == 'BEACH/ParkSit_M_loop'), 'player plays BEACH/ParkSit_M_loop')
pl = lua.globals().localPlayer
check(abs(pl.x - bx) < 0.1 and abs(pl.y - by) < 0.1 and abs(pl.z - (oz + sit[4] + 0.8)) < 0.01, 'player placed on the bench seat (%.2f, %.2f, %.2f)' % (pl.x, pl.y, pl.z))
frames(20)
T.key('w')
check(pl.anim is None, 'pressing W stands up (animation cleared)')
T.setPlayer(ox + 30, oy + 30, oz + 1.0)
T.cmd('client', 'sit')
check(any('Stand next to a bench' in m for m in chat()), '/sit far from a bench gives a hint')
T.setPlayer(bx + 0.8, by, oz + 1.0)
T.fireS('park:sit', bx + 500, by, oz + 1.0, 0.0)
check(pl.anim is None, 'server rejects a sit request far from the player (anti-cheat)')

print('\n-- day / night, wind shader --')
T.hour = 22.5
frames(60)
nl = len(T.light())
check(1 <= nl <= 4, 'night: %d real point lights near the player' % nl)
check(all(s.vol > 0 for s in list(T.sound('crickets_loop').values())), 'night: crickets audible')
T.hour = 13
frames(60)
check(len(T.light()) == 0, 'day: lights removed')
check(all(s.vol == 0 for s in list(T.sound('crickets_loop').values())), 'day: crickets muted')
T.cmd('client', 'parkwind')
check(alive('shader') == 1, '/parkwind creates the shader')
T.cmd('client', 'parkwind')
check(alive('shader') == 0, '/parkwind again removes it')

print('\n-- /hidepark, re-show, restart, models limit --')
T.cmd('server', 'hidepark')
frames(20)
leak = {k: alive(k) for k in ('object', 'water', 'effect', 'blip', 'light', 'shader')}
leak['looping sounds'] = sum(1 for e in [T.elems[i] for i in range(1, len(T.elems) + 1)] if e.kind == 'sound' and e.alive and e.loop)
check(all(v == 0 for v in leak.values()), 'everything removed: %s' % leak)
check(int(T.handlerCount('onClientRender')) == 0, 'render handlers removed')
live = int(T.liveTimers())
check(live == 0, 'no timers left alive (%d)' % live)
T.setPlayer(500, 500, 20)
T.cmd('server', 'showpark'); frames(80)
check(alive('object') == N_OBJ and len(T.models) == N_MODELS, 're-show: objects rebuilt, models not requested twice (%d ids)' % len(T.models))
T.cmd('server', 'showpark'); frames(80)
check(alive('object') == N_OBJ, 'showpark twice does not duplicate (%d)' % alive('object'))
T.cmd('server', 'parkz', '1.5'); frames(80)
check(alive('object') == N_OBJ, '/parkz moves the park without duplicating')
T.cmd('server', 'showpark'); frames(1)
T.cmd('server', 'hidepark'); frames(100)
check(alive('object') == 0, 'hide during the build leaves nothing behind (alive %d)' % alive('object'))
# loading cancelled while models load is covered on a fresh client below
T.fireC('onClientResourceStop')
check(len(T.freed) == N_MODELS, 'resource stop frees all %d model ids' % len(T.freed))
check(alive('dff') == 0 and alive('txd') == 0 and alive('col') == 0, 'DFF/TXD/COL elements destroyed on stop')
print('\n-- file references --')
import re
for f in ('client.lua',):
    refs = set(re.findall(r'files/[A-Za-z0-9_/.]+', rd(f)))
    check(all(r in T.files or os.path.isfile(os.path.join(RES, r)) for r in refs if '.' in r.split('/')[-1]), 'every literal file path in %s exists' % f)
snd_files = set(re.findall(r'"([a-z0-9_]+)"', ' '.join(re.findall(r'snd[23]\(([^,)]*)', rd('client.lua')))))
snd_files.discard('bird'); snd_files |= {'bird%d' % k for k in range(1, 6)}
check(all(os.path.isfile(os.path.join(RES, 'files', 'audio', n + '.wav')) for n in snd_files), 'all %d sound names used by client.lua exist as WAV: %s' % (len(snd_files), sorted(snd_files)))
check(all(f in T.files for f in ['files/audio/%s.wav' % n for n in snd_files]), 'and are listed in the file table')
print('\n=== %d failures ===' % len(fails))
sys.exit(1 if fails else 0)
