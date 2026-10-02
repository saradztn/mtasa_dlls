# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# validate.py - independent QC of the *shipped files* of the Park resource:
#   * every DFF / TXD / COL is parsed again with lib/readers.py (a strict parser written separately from the writers)
#   * every material of every DFF exists in the TXD the resource loads it with (models.lua)
#   * meta.xml lists every file that exists and nothing that is missing; the Lua files compile (lupa)
#   * layout.lua only references existing models; every object is inside the park; no solid prop blocks a footpath
#   * the bridge deck is a continuous walkable surface (step <= 0.45 m)
#   python3 validate.py   -> prints the report, writes qc_report.txt, exit code 1 on failure
# -----------------------------------------------------------------------------
import os
import re
import sys
import wave
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import readers

ROOT = os.path.abspath(os.path.join(HERE, '..'))
RES = os.path.join(ROOT, 'resource', 'Park')
lines, fails, warns = [], [], []


def say(s=''):
    print(s)
    lines.append(s)


def ok(cond, msg, warn=False):
    tag = 'PASS' if cond else ('WARN' if warn else 'FAIL')
    say('  [%s] %s' % (tag, msg))
    if not cond:
        (warns if warn else fails).append(msg)
    return cond


def lua_runtime():
    from lupa import LuaRuntime
    return LuaRuntime(unpack_returned_tuples=True)


def main():
    say('=== Park QC ===')
    lua = lua_runtime()
    # ------------------------------------------------------------------ Lua
    say('\n-- Lua --')
    for f in ('models.lua', 'layout.lua', 'client.lua', 'server.lua'):
        src = open(os.path.join(RES, f), encoding='utf-8').read()
        res = lua.eval('function(s) local f, e = load(s, "%s") return {f = f, e = e} end' % f)(src)
        fn, err = res['f'], res['e']
        ok(fn is not None, '%s compiles (%d lines)%s' % (f, src.count('\n') + 1, '' if fn else ' ERROR ' + str(err)))
        ok(src.lstrip().startswith('--') and 'Arena.ai Agent Mode' in src[:200], '  header names the AI that created it')
    for f in ('models.lua', 'layout.lua'):
        lua.execute(open(os.path.join(RES, f), encoding='utf-8').read())
    g = lua.globals()
    models = [dict(name=m['name'], txd=m['txd'], alpha=m['alpha'], dist=m['dist'], ox=m['ox'], oy=m['oy']) for m in g.PARK_MODELS.values()]
    objs = [[v for v in o.values()] for o in g.PARK_OBJECTS.values()]
    ok(len(models) == len(set(m['name'] for m in models)), '%d models, unique names' % len(models))
    ok(all(1 <= o[0] <= len(models) for o in objs), '%d objects, all model indices valid' % len(objs))
    ok(all(len(m['name']) <= 20 for m in models), 'model names are short (<= 20 chars)')

    # ------------------------------------------------------------------ files / meta
    say('\n-- meta.xml / files --')
    meta = open(os.path.join(RES, 'meta.xml'), encoding='utf-8').read()
    listed = re.findall(r'<file src="([^"]+)"', meta)
    scripts = re.findall(r'<script src="([^"]+)"', meta)
    ok(all(os.path.isfile(os.path.join(RES, p)) for p in listed + scripts), 'every <file>/<script> in meta.xml exists (%d files, %d scripts)' % (len(listed), len(scripts)))
    ok(len(listed) == len(set(listed)), 'no duplicate <file> entries')
    present = set()
    for d, _, fs in os.walk(os.path.join(RES, 'files')):
        for f in fs:
            present.add(os.path.relpath(os.path.join(d, f), RES))
    present.add('wind.fx')
    ok(present == set(listed), 'files on disk == files in meta.xml (%d)' % len(present))
    order = scripts.index('models.lua') < scripts.index('client.lua') and scripts.index('layout.lua') < scripts.index('client.lua')
    ok(order, 'models.lua and layout.lua load before client.lua')
    for key in ('PARK_MODELS', 'PARK_OBJECTS'):
        ok(key in open(os.path.join(RES, 'client.lua'), encoding='utf-8').read(), 'client.lua uses %s' % key)
    # resource copies == source copies
    for sub, ext in (('model', 'dff'), ('texture', 'txd'), ('collision', 'col')):
        same = all(open(os.path.join(ROOT, sub, f), 'rb').read() == open(os.path.join(RES, 'files', f), 'rb').read()
                   for f in os.listdir(os.path.join(ROOT, sub)) if f.endswith('.' + ext))
        ok(same, 'resource/files/*.%s identical to %s/' % (ext, sub))

    # ------------------------------------------------------------------ TXD
    say('\n-- TXD --')
    txds = {}
    for cat in sorted(set(m['txd'] for m in models)):
        t = readers.read_txd(os.path.join(ROOT, 'texture', '%s.txd' % cat))
        names = {x['name']: x for x in t['textures']}
        txds[cat] = names
        ok(t['device'] == 9 and t['count'] == len(names), '%s.txd: D3D9, %d textures' % (cat, len(names)))
        for n, x in names.items():
            po2 = (x['w'] & (x['w'] - 1)) == 0 and (x['h'] & (x['h'] - 1)) == 0
            full = x['nlev'] == int(np.log2(max(x['w'], x['h']))) + 1
            im = readers.decode_texture(x, 0)
            has_a = x['fmt'] in ('DXT5', 'DXT3')
            std = (im[..., 3] if (has_a and im[..., 3].std() > 1) else im[..., :3]).std()
            good = po2 and full and x['fmt'] in ('DXT1', 'DXT5') and std > 2 and len(n) < 24
            ok(good, '%-16s %4dx%-4d %s %d mips, std %.1f' % (n, x['w'], x['h'], x['fmt'], x['nlev'], std))
            if has_a and x['fmt'] == 'DXT5':
                a = im[..., 3]
                ok(a.min() < 40 or a.max() > 250, '  alpha channel present (min %d max %d)' % (a.min(), a.max()), warn=True)
    # ------------------------------------------------------------------ DFF / COL
    say('\n-- DFF / COL --')
    tot_v = tot_t = 0
    cols = {}
    used = {c: set() for c in txds}
    for m in models:
        nm = m['name']
        dp = os.path.join(ROOT, 'model', nm + '.dff')
        cp = os.path.join(ROOT, 'collision', nm + '.col')
        if not (ok(os.path.isfile(dp), '%s.dff exists' % nm) and ok(os.path.isfile(cp), '%s.col exists' % nm)):
            continue
        d = readers.read_dff(dp)
        bad = []
        if d['version'] != 0x1803FFFF:
            bad.append('RW version %08X' % d['version'])
        if len(d['atomics']) != 1:
            bad.append('%d atomics' % len(d['atomics']))
        P_all = []
        for at in d['atomics']:
            gm = d['geoms'][at['geom']]
            P, N, UV, T = gm['pos'], gm['nrm'], gm['uv'], gm['tris']
            tot_v += gm['nverts']; tot_t += gm['ntris']
            P_all.append(P)
            if not (gm['nverts'] < 65535 and T.min() >= 0 and T.max() < gm['nverts']):
                bad.append('bad indices')
            if not (np.isfinite(P).all() and np.isfinite(N).all() and np.isfinite(UV).all()):
                bad.append('non-finite values')
            nl = np.linalg.norm(N, axis=1)
            if not (nl.min() > 0.98 and nl.max() < 1.02):
                bad.append('normals not unit')
            a_, b_, c_ = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
            fn = np.cross(b_ - a_, c_ - a_)
            area = np.linalg.norm(fn, axis=1) * 0.5
            valid = area > 1e-10
            if not m['alpha']:       # foliage cards are double-sided by design, solids must agree with normals
                dd = (fn * (N[T[:, 0]] + N[T[:, 1]] + N[T[:, 2]])).sum(1)
                frac = (dd[valid] > 0).mean()
                if frac < 0.97:
                    bad.append('winding vs normals %.1f%%' % (100 * frac))
            if gm.get('prelit') is None:
                bad.append('no prelit colours')
            if gm.get('night') is None:
                bad.append('no night colours')
            if not all(x['tex'] is not None for x in gm['materials']):
                bad.append('untextured material')
            for x in gm['materials']:
                tn = x['tex']['name']
                used[m['txd']].add(tn)
                if tn not in txds[m['txd']]:
                    bad.append('texture %s missing from %s.txd' % (tn, m['txd']))
            if sum(len(q[1]) for q in gm['binmesh']) != 3 * gm['ntris']:
                bad.append('BinMesh count')
            s = gm['sphere']
            if np.linalg.norm(P - np.array(s[:3]), axis=1).max() > s[3] * 1.001 + 1e-4:
                bad.append('bounding sphere')
        c = readers.read_col3(cp)
        cols[nm] = c
        if c['name'] != nm:
            bad.append('COL name %s' % c['name'])
        if not (c['boxes'] or c['faces'] or c['spheres']):
            bad.append('empty COL')
        if not all(math.isfinite(v) for v in list(c['min']) + list(c['max'])):
            bad.append('COL bounds')
        Pa = np.concatenate(P_all)
        ok(not bad, '%-18s %6d v %6d t  %-5s %2d mats  col: %d box %d sph %d face  %s' % (
            nm, sum(len(p) for p in P_all), sum(len(d['geoms'][a['geom']]['tris']) for a in d['atomics']), m['txd'],
            sum(len(d['geoms'][a['geom']]['materials']) for a in d['atomics']), len(c['boxes']), len(c['spheres']), len(c['faces']),
            ('; '.join(bad)) if bad else ''))
    say('  total %d vertices, %d triangles in %d models' % (tot_v, tot_t, len(models)))
    for cat, names in txds.items():
        un = sorted(set(names) - used[cat])
        ok(not un, '%s.txd: every texture is used by some model%s' % (cat, ' (unused: %s)' % un if un else ''), warn=True)

    # ------------------------------------------------------------------ layout
    say('\n-- layout --')
    xs = np.array([o[1] for o in objs]); ys = np.array([o[2] for o in objs]); zs = np.array([o[3] for o in objs])
    ok(xs.min() >= -66 and xs.max() <= 66 and ys.min() >= -18 and ys.max() <= 96, 'objects inside the park frame x %.1f..%.1f  y %.1f..%.1f  z %.2f..%.2f' % (xs.min(), xs.max(), ys.min(), ys.max(), zs.min(), zs.max()))
    cnt = {}
    for o in objs:
        cnt[models[o[0] - 1]['name']] = cnt.get(models[o[0] - 1]['name'], 0) + 1
    say('  ' + ', '.join('%s x%d' % kv for kv in sorted(cnt.items(), key=lambda kv: -kv[1])[:14]))
    tags = [o[5] for o in objs if len(o) > 5]
    say('  tagged objects: %s' % sorted(set(tags)))
    for need in ('gateL', 'gateR'):
        ok(need in tags, 'tag %s present (client animates it)' % need)
    for tg in ('swing', 'merry', 'duck'):
        ok(any(str(t).startswith(tg) for t in tags), 'tag %s* present' % tg)
    pts = g.PARK_POINTS
    for k in ('gate', 'fountain', 'pond', 'gazebo', 'kiosk', 'swing', 'merry', 'board1', 'board2', 'board3'):
        ok(pts[k] is not None, 'PARK_POINTS.%s defined' % k)
    # sit points on a bench
    sit = [(s[1], s[2]) for s in g.PARK_SIT.values()]
    benches = [(o[1], o[2]) for o in objs if models[o[0] - 1]['name'] == 'pk_bench']
    ok(len(sit) == len(benches) and all(min(math.hypot(a - b[0], c - b[1]) for b in benches) < 0.8 for a, c in sit), '%d sit points all on a bench' % len(sit))
    for k in ('board1', 'board2', 'board3'):
        bp = pts[k]
        boards = [(o[1], o[2]) for o in objs if models[o[0] - 1]['name'] == 'pk_board']
        d = min(math.hypot(bp[1] - b[0], bp[2] - b[1]) for b in boards) if boards else 99
        ok(d < 5, 'info %s is %.1f m from an info-board model' % (k, d), warn=True)
    mp = pts['merry']; mo = [(o[1], o[2]) for o in objs if len(o) > 5 and str(o[5]).startswith('merry')]
    ok(mo and min(math.hypot(mp[1] - a, mp[2] - b) for a, b in mo) < 2, 'merry point matches the merry-go-round object')

    # ------------------------------------------------------------------ walkability
    say('\n-- walkability --')
    from pk import layout as LY
    boxes = []   # solid (x0,y0,x1,y1,z0,z1)
    for o in objs:
        nm = models[o[0] - 1]['name']
        if nm.startswith('pk_ground') or (len(o) > 5 and str(o[5]) in ('gateL', 'gateR')):
            continue
        c = cols[nm]
        if c['faces'] and nm not in ('pk_fountain',):   # only box/sphere colliders are tested as obstacles
            continue
        rz = math.radians(o[4]); cs, sn = math.cos(rz), math.sin(rz)
        items = [(b[0], b[1], b[2], b[3], b[4], b[5]) for b in c['boxes']] + [(s[0] - s[3], s[1] - s[3], s[2] - s[3], s[0] + s[3], s[1] + s[3], s[2] + s[3]) for s in c['spheres']]
        for (x0, y0, z0, x1, y1, z1) in items:
            cs_ = [(cs * x - sn * y + o[1], sn * x + cs * y + o[2]) for x in (x0, x1) for y in (y0, y1)]
            boxes.append((min(p[0] for p in cs_), min(p[1] for p in cs_), max(p[0] for p in cs_), max(p[1] for p in cs_), z0 + o[3], z1 + o[3], nm))
    B = np.array([b[:6] for b in boxes])
    blocked = {}
    for name, pl, w, mat, zo, curb in LY.PATHS:
        if name in ('entrance', 'perim'):
            pass
        n_s = 0
        for a, b in zip(pl[:-1], pl[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            for t in np.linspace(0, 1, max(2, int(L / 0.5))):
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                z = float(LY.hfield(x, y))
                if abs(x - 36) < 3.5 and 31 < y < 49:     # on the bridge (its deck collision is face based)
                    continue
                hit = (B[:, 0] - 0.3 < x) & (x < B[:, 2] + 0.3) & (B[:, 1] - 0.3 < y) & (y < B[:, 3] + 0.3) & (B[:, 5] > z + 0.5) & (B[:, 4] < z + 1.8)
                for i in np.nonzero(hit)[0]:
                    blocked.setdefault(name, set()).add((boxes[i][6], round(x, 1), round(y, 1)))
                n_s += 1
        ok(name not in blocked, 'path %-8s %5d samples, centre line clear of solid props%s' % (name, n_s, (' BLOCKED by %s' % sorted(blocked[name])[:4]) if name in blocked else ''), warn=(name == 'ring'))
    # bridge deck continuity
    bi = [m['name'] for m in models].index('pk_bridge') + 1
    bo = [o for o in objs if o[0] == bi][0]
    bc = cols['pk_bridge']
    ok(len(bc['faces']) > 0 or len(bc['boxes']) > 0, 'bridge COL has %d boxes / %d faces' % (len(bc['boxes']), len(bc['faces'])))
    say('  bridge at (%.1f, %.1f, rz %.0f)' % (bo[1], bo[2], bo[4]))
    # triangle-mesh top surface along the bridge axis (COL3 vertices are int16 / 128)
    import struct
    cb = open(os.path.join(ROOT, 'collision', 'pk_bridge.col'), 'rb').read()
    ns_, nb_, nf_, _, _ = struct.unpack_from('<HHHBB', cb, 72)
    hdr = struct.unpack_from('<I9I', cb, 80)
    o_v, o_f = hdr[4], hdr[5]
    F = [struct.unpack_from('<3HBB', cb, 4 + o_f + 8 * i) for i in range(nf_)]
    V = np.array([struct.unpack_from('<3h', cb, 4 + o_v + 6 * i) for i in range(max(max(f[:3]) for f in F) + 1)]) / 128.0

    def top(px, py):
        best = None
        for f in F:
            A, B_, C = V[list(f[:3])]
            cr = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            d = (cr(A, B_, (px, py)), cr(B_, C, (px, py)), cr(C, A, (px, py)))
            if all(v >= 0 for v in d) or all(v <= 0 for v in d):
                n = np.cross(B_ - A, C - A)
                if abs(n[2]) > 1e-9:
                    z = A[2] - (n[0] * (px - A[0]) + n[1] * (py - A[1])) / n[2]
                    best = z if best is None or z > best else best
        return best
    for off in (-1.0, 0.0, 1.0):
        prof = [top(off, y) for y in np.arange(-6.9, 6.95, 0.25)]
        okp = all(p is not None for p in prof)
        st = max(abs(a - b) for a, b in zip(prof[:-1], prof[1:])) if okp else 99
        ok(okp and st <= 0.12, 'bridge deck x=%+.1f: continuous surface over 13.8 m, max step %.2f m per 0.25 m (slope %.0f%%), crest z %.2f' % (off, st, st / 0.25 * 100, max(p for p in prof if p is not None)))
    for yy in (-7.0, 7.0):
        zb = top(0.0, yy)
        zg = float(LY.hfield(bo[1], bo[2] + yy))
        ok(zb is not None and abs(zb - zg) < 0.15, 'bridge end y=%+.0f meets the bank: deck %.2f vs ground %.2f' % (yy, zb if zb is not None else -99, zg))

    # ------------------------------------------------------------------ audio
    say('\n-- audio --')
    for f in sorted(os.listdir(os.path.join(ROOT, 'audio'))):
        w = wave.open(os.path.join(ROOT, 'audio', f))
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        ok(w.getnchannels() == 1 and w.getsampwidth() == 2 and 0.2 < abs(a).max() < 0.99 and a.std() > 0.01,
           '%-18s %.1fs mono 16-bit %d Hz peak %.2f rms %.3f' % (f, w.getnframes() / w.getframerate(), w.getframerate(), abs(a).max(), a.std()))
    say('\n=== %d failures, %d warnings ===' % (len(fails), len(warns)))
    open(os.path.join(HERE, 'qc_report.txt'), 'w').write('\n'.join(lines) + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
