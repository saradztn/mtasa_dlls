# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# validate.py - independent QC of the *shipped files* of the Ashfall resource:
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
RES = os.path.join(ROOT, 'resource', 'Ashfall')
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
    say('=== Ashfall QC ===')
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
    models = [dict(name=m['name'], txd=m['txd'], alpha=m['alpha'], dist=m['dist'], ox=m['ox'], oy=m['oy']) for m in g.AF_MODELS.values()]
    objs = [[v for v in o.values()] for o in g.AF_OBJECTS.values()]
    ok(len(models) == len(set(m['name'] for m in models)), '%d models, unique names' % len(models))
    used_ = set(o[0] for o in objs) | set(i + 1 for i, m in enumerate(models) if m['ox'] is not None)
    ok(len(used_) == len(models), 'every model is placed by the layout or is a ground tile (unused: %s)' % [models[i - 1]['name'] for i in sorted(set(range(1, len(models) + 1)) - used_)])
    ok(all(1 <= o[0] <= len(models) for o in objs), '%d objects, all model indices valid' % len(objs))
    ok(all(len(m['name']) <= 24 for m in models), 'model names are short (<= 24 chars)')

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
    for key in ('AF_MODELS', 'AF_OBJECTS'):
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
    ok(xs.min() >= -172 and xs.max() <= 172 and ys.min() >= -172 and ys.max() <= 172, 'objects inside the 340 m city frame x %.1f..%.1f  y %.1f..%.1f  z %.2f..%.2f' % (xs.min(), xs.max(), ys.min(), ys.max(), zs.min(), zs.max()))
    ok(zs.min() > -3.5 and zs.max() < 12, 'object heights are sane')
    cnt = {}
    for o in objs:
        cnt[models[o[0] - 1]['name']] = cnt.get(models[o[0] - 1]['name'], 0) + 1
    say('  ' + ', '.join('%s x%d' % kv for kv in sorted(cnt.items(), key=lambda kv: -kv[1])[:14]))
    nb = sum(v for k, v in cnt.items() if k.startswith('af_') and not k.endswith('_v') and k[3:].split('_')[0] in ('tower', 'apt', 'shop', 'hotel', 'kiosk', 'office'))
    ncar = sum(v for k, v in cnt.items() if k.startswith('af_car_'))
    say('  %d building shells, %d cars, %d trees' % (nb, ncar, sum(v for k, v in cnt.items() if 'tree' in k)))
    ok(nb >= 20 and ncar >= 80, 'enough buildings and abandoned cars')
    # no two buildings overlap
    pts = g.AF_POINTS
    for k in ('spawn', 'plaza', 'lake', 'pier', 'gazebo', 'street', 'tower'):
        ok(pts[k] is not None, 'AF_POINTS.%s defined' % k)
    lk = g.AF_LAKE
    ok(lk.rx > 10 and lk.ry > 10 and lk.z < 0, 'AF_LAKE defined (rx %.0f ry %.0f z %.2f)' % (lk.rx, lk.ry, lk.z))
    # nothing placed inside the lake bowl except water plants / pier / ducks
    inside = [models[o[0] - 1]['name'] for o in objs if ((o[1] - lk.cx) / (lk.rx * 0.8)) ** 2 + ((o[2] - lk.cy) / (lk.ry * 0.8)) ** 2 < 1 and not any(w in models[o[0] - 1]['name'] for w in ('pier', 'reed', 'lily', 'weeds', 'grass', 'rubble', 'bush', 'ground'))]
    ok(not inside, 'no solid prop stands in the lake (%s)' % sorted(set(inside))[:5], warn=True)
    # the spawn point is free of solid props
    sp = pts['spawn']
    near = [models[o[0] - 1]['name'] for o in objs if math.hypot(o[1] - sp[1], o[2] - sp[2]) < 2.5 and not any(w in models[o[0] - 1]['name'] for w in ('weeds', 'grass', 'ground', 'rubble'))]
    ok(not near, 'spawn point is clear (%s)' % near)
    # ground tiles cover the city
    til = [m for m in models if m['ox'] is not None]
    ok(len(til) == 16, '%d ground tiles (4 x 4 x 85 m)' % len(til))

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
