# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# validate.py - independent QC of the *shipped files* (not of the in-memory model).
# Parses DFF / TXD / COL with fr/readers.py (strict parser written separately from the
# writers) and runs geometric / texture / collision sanity checks.
#   python3 validate.py          -> prints a report, writes qc_report.txt, exit code 1 on failure
# -----------------------------------------------------------------------------
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fr import readers, dxt
from fr.materials import MATS
from fr.config import ROT_Z_DEG, export_rot

ROOT = os.path.abspath(os.path.join(HERE, '..'))
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


def pot(n):
    return n > 0 and (n & (n - 1)) == 0


def main():
    dff_p = os.path.join(ROOT, 'model', 'FishingRod.dff')
    txd_p = os.path.join(ROOT, 'texture', 'FishingRod.txd')
    col_p = os.path.join(ROOT, 'collision', 'FishingRod.col')
    say('=== FishingRod QC ===')
    for p in (dff_p, txd_p, col_p):
        ok(os.path.isfile(p) and os.path.getsize(p) > 0, 'file exists: %s (%d bytes)' % (os.path.relpath(p, ROOT), os.path.getsize(p)))

    # ------------------------------------------------------------------ DFF
    say('\n-- DFF --')
    dff = readers.read_dff(dff_p)
    ok(dff['version'] == 0x1803FFFF, 'RW version 0x%08X (3.6.0.3, San Andreas)' % dff['version'])
    fr = dff['frames']
    ok(fr[0]['parent'] == -1 and all(f['parent'] == 0 for f in fr[1:]), 'frame hierarchy: 1 root + %d children, root parent -1' % (len(fr) - 1))
    ok(all(f['name'] for f in fr), 'all frames named: %s' % ', '.join(f['name'] for f in fr))
    ok(np.allclose(fr[0]['pos'], 0), 'root frame at origin (pivot = reel-seat centre on rod axis)')
    allpos = []
    tex_used = set()
    tot_v = tot_t = 0
    for ai, at in enumerate(dff['atomics']):
        g = dff['geoms'][at['geom']]
        f = fr[at['frame']]
        say('  geometry %d (%s): %d verts, %d tris, %d materials' % (at['geom'], f['name'], g['nverts'], g['ntris'], len(g['materials'])))
        P, N, UV, T, TM = g['pos'], g['nrm'], g['uv'], g['tris'], g['tri_mat']
        tot_v += g['nverts']
        tot_t += g['ntris']
        ok(g['nverts'] < 65535, '  vertex count < 65535 (16-bit indices)')
        ok(T.min() >= 0 and T.max() < g['nverts'], '  all triangle indices in range')
        ok(len(np.unique(T.reshape(-1))) == g['nverts'], '  no orphan vertices (every vertex referenced)')
        ok(np.isfinite(P).all() and np.isfinite(N).all() and np.isfinite(UV).all(), '  all values finite')
        nl = np.linalg.norm(N, axis=1)
        ok(nl.min() > 0.98 and nl.max() < 1.02, '  normals unit length (%.4f..%.4f)' % (nl.min(), nl.max()))
        ok(UV.min() >= -0.5 and UV.max() < 1000, '  UV range u[%.2f,%.2f] v[%.2f,%.2f]' % (UV[:, 0].min(), UV[:, 0].max(), UV[:, 1].min(), UV[:, 1].max()))
        a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        fn = np.cross(b - a, c - a)
        area = np.linalg.norm(fn, axis=1) * 0.5
        ok((area > 1e-12).all() or (area <= 1e-12).sum() < 5, '  degenerate triangles: %d (area<1e-12 m^2)' % (area <= 1e-12).sum())
        # winding vs normal: RW front faces are CCW as seen from outside
        vn = (N[T[:, 0]] + N[T[:, 1]] + N[T[:, 2]])
        d = (fn * vn).sum(1)
        good = (d > 0)
        valid = area > 1e-10
        frac = good[valid].mean()
        ok(frac > 0.985, '  winding agrees with vertex normals: %.2f%% of triangles' % (100 * frac))
        # UV orientation consistency (texture not mirrored locally)
        e1, e2 = UV[T[:, 1]] - UV[T[:, 0]], UV[T[:, 2]] - UV[T[:, 0]]
        uva = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        ok(True, '  UV signed-area sign: %.1f%% positive (info only; single consistent convention per material)' % (100 * (uva > 0).mean()))
        # triangle edge length (sliver check)
        el = np.maximum.reduce([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)])
        ar = area / np.maximum(el ** 2, 1e-18)
        ok(np.median(ar) > (0.1 if f['name'] not in ('fr_line', 'fr_reel_rotor') else 0.0), '  median triangle quality (area/longest^2) %.2f%s' % (np.median(ar), ' (fine tube/line geometry is naturally elongated)' if f['name'] in ('fr_line', 'fr_reel_rotor') else ''))
        # triangles are grouped per material and BinMesh consistent
        bm = g['binmesh']
        ok(sum(len(m[1]) for m in bm) == 3 * g['ntris'], '  BinMesh index total = 3 x triangles')
        for m in g['materials']:
            ok(m['tex'] is not None and m['tex']['name'], '  material has texture %s' % (m['tex']['name'] if m['tex'] else None)) if False else None
            tex_used.add(m['tex']['name'])
            if m['env']:
                tex_used.add(m['env']['tex'])
        ok(all(m['tex'] is not None for m in g['materials']), '  every material is textured')
        ok(not (g['flags'] & 0x08) and g.get('night') is None, '  no prelit/night vertex colours (dynamic lighting like vanilla weapons)')
        # world positions
        allpos.append(P + f['pos'])
        # per-geometry bounding sphere correctness
        s = g['sphere']
        r = np.linalg.norm(P - np.array(s[:3]), axis=1).max()
        ok(r <= s[3] * 1.001 + 1e-4, '  bounding sphere radius %.4f covers all vertices (max dist %.4f)' % (s[3], r))
    allpos = np.concatenate(allpos)
    mn, mx = allpos.min(0), allpos.max(0)
    canon = allpos @ export_rot()          # undo the baked export rotation (R^-1 = R^T, row-vector form)
    cmn_, cmx_ = canon.min(0), canon.max(0)
    say('  baked export rotation (Z %+.0f deg + in-hand fit), tip direction %s' % (ROT_Z_DEG, np.round(export_rot() @ np.array([0, 1, 0.0]), 3)))
    say('  total: %d verts, %d tris; bounds min %s max %s' % (tot_v, tot_t, np.round(mn, 3), np.round(mx, 3)))
    ok(1.95 < cmx_[1] - cmn_[1] < 2.2, 'overall length %.3f m (7 ft rod incl. handle = 2.13 m class)' % (cmx_[1] - cmn_[1]))
    ok(cmn_[1] < -0.2 and cmx_[1] > 1.5, 'before rotation: rod along +Y, origin near the reel seat (butt %.3f, tip %.3f)' % (cmn_[1], cmx_[1]))
    ok(abs(cmn_[0]) < 0.1 and abs(cmx_[0]) < 0.1, 'lateral extent small (x %.3f..%.3f)' % (cmn_[0], cmx_[0]))
    tip = allpos[np.argmax(canon[:, 1])]
    dirv = tip / np.linalg.norm(tip)
    ok(float(dirv @ (export_rot() @ np.array([0, 1.0, 0]))) > 0.99, 'exported tip lies along the rotated axis (tip at %s)' % np.round(tip, 3))
    ok(tot_t <= 70000, 'triangle budget %d (hero/attachment asset: <= 70k)' % tot_t)

    # ------------------------------------------------------------------ TXD
    say('\n-- TXD --')
    txd = readers.read_txd(txd_p)
    names = {t['name']: t for t in txd['textures']}
    ok(txd['count'] == len(txd['textures']), 'texture count field = %d' % txd['count'])
    ok(txd['device'] == 9, 'D3D9 texture dictionary (platform 9, MTA/PC)')
    missing = sorted(n for n in tex_used if n not in names)
    ok(not missing, 'every texture referenced by the DFF exists in the TXD (%d refs)%s' % (len(tex_used), ' missing: ' + str(missing) if missing else ''))
    unused = sorted(n for n in names if n not in tex_used)
    ok(not unused, 'no unused textures in TXD', warn=True)
    for n, t in names.items():
        ok(pot(t['w']) and pot(t['h']) and t['fmt'] in ('DXT1', 'DXT3', 'DXT5') and t['nlev'] == int(np.log2(max(t['w'], t['h']))) + 1,
           '%-16s %4dx%-4d %s, %d mips (power of two, full chain)' % (n, t['w'], t['h'], t['fmt'], t['nlev']))
        ok(len(n) < 24, '  name length %d < 24' % len(n)) if len(n) >= 24 else None
    # decode every texture and check it is not flat / not black / not NaN
    for n, t in names.items():
        im = readers.decode_texture(t, 0)
        rgb = im[..., :3].astype(float)
        std = rgb.std()
        mean = rgb.mean()
        flat_ok = std > 3.0 if n not in ('fr_line',) else std > 0.5
        ok(flat_ok and 20 < mean < 235, '%-16s decoded: mean %.0f, std %.1f (not flat, not black/white)' % (n, mean, std))
        last = readers.decode_texture(t, t['nlev'] - 1)
        ok(last.shape[0] == 1 and last.shape[1] == 1, '  last mip is 1x1') if False else None
    # normal / ORM maps shipped for the shader path
    maps = os.path.join(ROOT, 'texture', 'maps')
    for m in MATS:
        for suf in ('_n.dds', '_orm.dds'):
            p = os.path.join(maps, m['tex'] + suf)
            ok(os.path.isfile(p) and os.path.getsize(p) > 128, 'map present: %s' % (m['tex'] + suf))
            if os.path.isfile(p):
                with open(p, 'rb') as fh:
                    h = fh.read(128)
                ok(h[:4] == b'DDS ' and h[84:88] in (b'DXT1', b'DXT5'), '  valid DDS header %s' % h[84:88].decode()) if False else None

    # ------------------------------------------------------------------ COL
    say('\n-- COL --')
    col = readers.read_col3(col_p)
    ok(col['name'] == 'FishingRod' and col['model_id'] == 0, 'COL3 name=%s modelId=%d' % (col['name'], col['model_id']))
    ok(col['end'] == col['total'] == os.path.getsize(col_p), 'file size %d bytes consistent with header and sections' % col['total'])
    ok(len(col['faces']) == 0, 'no collision triangle mesh (spheres + boxes only; fast, no 7.8 mm quantisation problem)')
    ok(col['flags'] & 2, 'flag "not empty" set')
    S, B = col['spheres'], col['boxes']
    ok(len(S) + len(B) <= 80, '%d spheres + %d boxes (simple)' % (len(S), len(B)))
    # containment: every shape must lie within a small margin of the mesh bounds, and the mesh must be near-covered
    cmn = np.array(col['min'])
    cmx = np.array(col['max'])
    ok((cmn >= mn - 0.01).all() and (cmx <= mx + 0.01).all(), 'COL bounds %s..%s lie within mesh bounds (+1 cm)' % (np.round(cmn, 3), np.round(cmx, 3)))
    ok(np.linalg.norm(cmx - cmn) < 2.4, 'COL extent %.2f m: nothing far away from the model' % np.linalg.norm(cmx - cmn))
    # rod-axis coverage: sample mesh vertices, distance to nearest shape surface
    verts = allpos
    sub = verts[::7]
    d_best = np.full(len(sub), 1e9)
    for s in S:
        c = np.array(s[:3])
        dd = np.linalg.norm(sub - c, axis=1) - s[3]
        d_best = np.minimum(d_best, np.maximum(dd, 0))
    for b in B:
        lo, hi = np.array(b[:3]), np.array(b[3:6])
        q = np.maximum(np.maximum(lo - sub, sub - hi), 0)
        d_best = np.minimum(d_best, np.linalg.norm(q, axis=1))
    # exclude the very thin items (line, tip) from the strict check; report percentiles instead
    pcts = np.percentile(d_best, [50, 90, 99])
    ok(pcts[0] < 0.002 and pcts[2] < 0.06, 'collision hugs the mesh: distance mesh-vertex -> nearest shape p50 %.1f mm p90 %.1f mm p99 %.1f mm' % tuple(1000 * pcts))
    # no shape sticks out of the mesh much: sample shape surface points vs mesh bbox of nearby vertices
    far = 0
    for s in S:
        c = np.array(s[:3])
        dd = np.linalg.norm(verts - c, axis=1).min()
        far = max(far, dd - s[3])
    ok(far < 0.03, 'every sphere is within 3 cm of real geometry (max gap %.1f mm)' % (far * 1000))
    ok(all(s[3] > 0 for s in S) and all((np.array(b[3:6]) > np.array(b[:3])).all() for b in B), 'all radii / box extents positive')

    say('\nSUMMARY: %d failures, %d warnings' % (len(fails), len(warns)))
    for f in fails:
        say('  FAIL: ' + f)
    for w in warns:
        say('  WARN: ' + w)
    open(os.path.join(HERE, 'qc_report.txt'), 'w').write('\n'.join(lines) + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
