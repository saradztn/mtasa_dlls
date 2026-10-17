"""Generate docs/ROOM_INDEX.md and docs/TESTING_REPORT.md from the machine outputs (never hand-edited numbers)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
RM = json.loads((ROOT / 'docs/rooms.json').read_text())
W = json.loads((ROOT / 'client/data/world.json').read_text())
V = json.loads((ROOT / 'docs/validation_report.json').read_text())
T = json.loads((ROOT / 'docs/runtime_tests.json').read_text())
SMOKE = ROOT / 'docs' / 'server_smoke.log'


def key(r):
    try: return (0, int(r['id']), '')
    except ValueError: return (1, 0, r['id'])


def room_index():
    L = ['# Room index (generated from docs/rooms.json)', '',
         'Coordinates are fortress-world metres (dimension %d, interior 0). `z0` is the floor level. Spawn = the safe point used by `/castleroom <id>`.' % W['dimension'],
         'Key = ACL key needed for `/castleroom` (the same lock as the door that guards the room).', '',
         '| ID | Room | Category | Level | Floor z0 | Size / shape | Connections | Furniture groups | Light sources | Key |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(RM['rooms'], key=key):
        if r.get('rect'):
            x0, y0, x1, y1 = r['rect']; size = '%.0f x %.0f m, h %.1f' % (x1 - x0, y1 - y0, r.get('h', 0))
        elif r.get('center'):
            size = '24-gon r %.1f m, h %.1f' % (r.get('apothem_inner', 7.8), r.get('h', 6))
        else: size = '-'
        acl = W['rooms'].get(r['id'], {}).get('acl') or ''
        L.append('| %s | %s | %s | %s | %.2f | %s | %s | %d | %s | %s |' % (r['id'], r['name'], r.get('category', ''), r.get('level', ''), r['z0'], size,
                                                                          ', '.join(r.get('connections', [])), len(r.get('furniture', [])), r.get('light_sources', ''), acl))
    L += ['', '## Interactive mechanisms', '', '| ID | Name | Kind | Default | Key | Moving parts |', '|---|---|---|---|---|---|']
    for k, v in sorted(W['interactive'].items()):
        L.append('| %s | %s | %s | %s | %s | %d |' % (k, v['name'], v['kind'], v['default'], v['acl'] or '-', len(v['parts'])))
    L += ['', '## Teleports', '', '| Command | Target | Position |', '|---|---|---|']
    cmd = {'gate': '/castle', 'interior': '/castleinterior', 'showp': '/showp', 'keeproof': '(debug/admin target)'}
    for k, v in W['teleports'].items():
        L.append('| %s | %s | %.1f, %.1f, %.2f |' % (cmd.get(k, k), v['label'], *v['pos']))
    (ROOT / 'docs/ROOM_INDEX.md').write_text('\n'.join(L) + '\n')


def testing_report():
    L = ['# Testing report', '', '**Read this first:** three different kinds of verification were performed. None of them is an in-game test with a',
         'graphical MTA:SA client. Nothing was rendered, no player walked through the fortress, and no frame rate was measured.', '',
         '| Layer | What it proves | Result |', '|---|---|---|',
         '| 1. Static validator `tools/validate.py` | Exported binaries re-parsed; geometry/topology/collision checked numerically | **%d/%d PASS** |' % (V['passed'], V['total']),
         '| 2. Lua runtime tests `tools/test_runtime.py` | The real server + client Lua executed (Lua 5.1/lupa) against MTA API stubs | **%d/%d PASS** |' % (T['passed'], T['total']),
         '| 3. Real MTA:SA 1.6 Linux server smoke test | Resource loads, parses world.json, ACL + console commands work, restart/stop clean | **PASS** (log below) |',
         '| 4. In-game client test | Rendering, streaming hitches, actual collision feel, door animation look | **NOT PERFORMED** |', '',
         '## 1. Static validation (%s)' % V['date'], '']
    for r in V['results']:
        L.append('- **%s %s** - %s: %s' % (r['status'], r['id'], r['title'], r['summary']))
    L += ['', 'Full details: `docs/validation_report.json`. Floor-plan preview: `docs/FLOOR_PLANS.png` (drawn from the manifest, not a render).', '',
          'Method notes: C04/C12 probe the exported COL files (boxes + faces, rotated per placement); C06 ray-casts the exported DFF triangles',
          '(glass/stained glass excluded); C13 builds a 2.5-D walkability graph on a 0.4 m grid from the room\'s exported COL with a 0.25 m',
          'body radius, 0.46 m step height and 1.75 m headroom, then checks that all doors at a floor connect around the furniture.', '',
          '## 2. Lua runtime tests', '']
    for r in T['results']:
        L.append('- **%s** [%s] %s' % (r['status'], r['suite'], r['test']))
    L += ['', 'These execute the actual `server/main.lua` and every client script listed in meta.xml. The MTA functions are deterministic stubs',
          '(`tools/mta_mock.lua`, `tools/client_mock.lua`); e.g. `processLineOfSight` is simulated, so the collision handshake is tested as logic only.', '',
          '## 3. Real server smoke test', '',
          'MTA:SA Linux server `multitheftauto_linux_x64` (1.6 release from linux.mtasa.com), stock configs from the mtasa-blue repository, resource',
          'copied as delivered, the five `resource.royal_fortress.*` rights added to the Admin ACL (as in docs/INSTALLATION.md). Console input:',
          '`castledoor`, `castledoor treasury_door`, `castledoor drawbridge`, `castledoor nonsense`, `castlereload`, `restart royal_fortress`, `stop`, `shutdown`.', '']
    if SMOKE.exists():
        L += ['```', SMOKE.read_text().strip(), '```']
    L += ['', 'No player connected (no game client is available in the build environment), so travel, streaming and E-key interaction were',
          'not exercised on the real server - only through layer 2.', '',
          '## What still needs a human with a game client', '',
          '1. `/castle`, `/castleinterior`, `/showp`, `/castleroom 3`, `/castleroom 47`, `/castleroom K2`: arrival, no falling, textures present.',
          '2. Walk gate -> courtyard -> palace -> throne hall -> stairs -> L1; keep spiral to K2; cellar -> dungeon -> cells; bookcase lever -> secret chamber -> vault.',
          '3. Press E on: drawbridge (gate key), portcullis, palace doors, a cell door, the red book lever; watch for clipping during the swing.',
          '4. `/castletime 23` for the night look, `/castledebug` for streaming counters; note FPS on your hardware.', '5. Report anything odd with the room id shown in the HUD.']
    (ROOT / 'docs/TESTING_REPORT.md').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    room_index(); testing_report(); print('docs generated')
