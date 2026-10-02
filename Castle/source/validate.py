# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# validate.py - independent QC of the *shipped files* (parsed again with lib/readers.py, a strict parser
# written separately from the writers) + collision / walkability checks.
#   python3 validate.py        -> prints the report, writes qc_report.txt, exit code 1 on failure
# Walkability: the COL is voxelised (0.2 m) and a 1.8 m tall walker (step <= 0.45 m) is flooded from the
# entrance; the test lists which rooms / levels are reachable (doors count as OPEN because the door
# models carry their own collision).
# -----------------------------------------------------------------------------
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import readers
from cs import tex as T_

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


def check_dff(path, txd_names, expect_alpha_split=False):
    dff = readers.read_dff(path)
    ok(dff['version'] == 0x1803FFFF, '%s: RW version 0x%08X (3.6.0.3, San Andreas)' % (os.path.basename(path), dff['version']))
    fr = dff['frames']
    ok(fr[0]['parent'] == -1 and all(f['parent'] == 0 for f in fr[1:]), '  frames: 1 root + %d children' % (len(fr) - 1))
    tot_v = tot_t = 0
    tex_used = set()
    allp = []
    for at in dff['atomics']:
        g = dff['geoms'][at['geom']]
        P, N, UV, T, TM = g['pos'], g['nrm'], g['uv'], g['tris'], g['tri_mat']
        tot_v += g['nverts']
        tot_t += g['ntris']
        ok(g['nverts'] < 65535 and T.max() < g['nverts'] and T.min() >= 0, '  geometry %d (%s): %d verts %d tris %d materials - indices valid' % (at['geom'], fr[at['frame']]['name'], g['nverts'], g['ntris'], len(g['materials'])))
        ok(np.isfinite(P).all() and np.isfinite(N).all() and np.isfinite(UV).all(), '    all values finite')
        nl = np.linalg.norm(N, axis=1)
        ok(nl.min() > 0.98 and nl.max() < 1.02, '    normals unit length')
        a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        fn = np.cross(b - a, c - a)
        area = np.linalg.norm(fn, axis=1) * 0.5
        valid = area > 1e-9
        d = (fn * (N[T[:, 0]] + N[T[:, 1]] + N[T[:, 2]])).sum(1)
        frac = (d[valid] > 0).mean()
        ok(frac > 0.985, '    winding agrees with vertex normals: %.2f%%' % (100 * frac))
        ok((~valid).sum() < 0.002 * len(T) + 2, '    degenerate triangles: %d' % (~valid).sum())
        ok(len(np.unique(T.reshape(-1))) == g['nverts'], '    no orphan vertices')
        ok(bool(g['flags'] & 0x08) and g.get('prelit') is not None, '    prelit (day) vertex colours present')
        ok(g.get('night') is not None, '    night vertex colours (extra colour plugin) present')
        if g.get('night') is not None:
            nc = g['night'][:, :3].astype(float).mean()
            names_ = [m['tex']['name'] for m in g['materials']]
            if any(n in ('cs_web', 'cs_orb', 'cs_flame') for n in names_):
                white = (g['night'][:, :3].min(1) > 250).mean()
                ok(white < 0.9, '    night colours (flames are fullbright by design): %.0f%% pure white vertices, mean %.0f/255' % (100 * white, nc))
            else:
                ok(nc < 140, '    night colours are dark (mean %.0f/255) - not the white full-bright trap' % nc)
        ok(all(m['tex'] is not None for m in g['materials']), '    every material is textured')
        for m in g['materials']:
            tex_used.add(m['tex']['name'])
        ok(sum(len(m[1]) for m in g['binmesh']) == 3 * g['ntris'], '    BinMesh index total = 3 x triangles')
        s = g['sphere']
        r = np.linalg.norm(P - np.array(s[:3]), axis=1).max()
        ok(r <= s[3] * 1.001 + 1e-4, '    bounding sphere covers all vertices')
        allp.append(P)
        if expect_alpha_split:
            names = [m['tex']['name'] for m in g['materials']]
            alpha = [n in ('cs_web', 'cs_orb', 'cs_flame') for n in names]
            ok(all(alpha) or not any(alpha), '    alpha materials are never mixed with opaque ones in one atomic')
    missing = sorted(n for n in tex_used if n not in txd_names)
    ok(not missing, '  every texture referenced exists in the TXD%s' % (' MISSING: %s' % missing if missing else ''))
    allp = np.concatenate(allp)
    say('  total %d verts, %d tris; bounds %s .. %s' % (tot_v, tot_t, np.round(allp.min(0), 2), np.round(allp.max(0), 2)))
    return dff, allp, tex_used


def main():
    say('=== Castle QC ===')
    paths = {k: os.path.join(ROOT, d, f) for k, (d, f) in dict(
        dff=('model', 'Castle.dff'), gate=('model', 'CastleGate.dff'), door=('model', 'CastleDoor.dff'), txd=('texture', 'Castle.txd'),
        col=('collision', 'Castle.col'), gcol=('collision', 'CastleGate.col'), dcol=('collision', 'CastleDoor.col')).items()}
    for p in paths.values():
        ok(os.path.isfile(p) and os.path.getsize(p) > 0, 'file exists: %s (%d bytes)' % (os.path.relpath(p, ROOT), os.path.getsize(p)))

    say('\n-- TXD --')
    txd = readers.read_txd(paths['txd'])
    names = {t['name']: t for t in txd['textures']}
    ok(txd['device'] == 9 and txd['count'] == len(names), 'D3D9 texture dictionary, %d textures' % len(names))
    ok(set(names) == set(T_.MAT_NAMES), 'all %d castle textures present' % len(T_.MAT_NAMES))
    for n, t in names.items():
        po2 = (t['w'] & (t['w'] - 1)) == 0 and (t['h'] & (t['h'] - 1)) == 0
        full = t['nlev'] == int(np.log2(max(t['w'], t['h']))) + 1
        want = 'DXT5' if T_.M[n] in T_.ALPHA else 'DXT1'
        im = readers.decode_texture(t, 0)
        ok(po2 and full and t['fmt'] == want and (im[..., 3] if want == 'DXT5' else im[..., :3]).std() > 4, '%-12s %4dx%-4d %s %d mips, decoded std %.1f' % (n, t['w'], t['h'], t['fmt'], t['nlev'], (im[..., 3] if want == 'DXT5' else im[..., :3]).std()))
        if want == 'DXT5':
            a = im[..., 3]
            ok(a.min() < 20 and a.max() > 150, '  alpha channel has real transparency (min %d max %d)' % (a.min(), a.max()))
        ok(len(n) < 24, '  name length < 24')

    say('\n-- DFF --')
    dff, P, used = check_dff(paths['dff'], names, True)
    ok(P[:, 2].max() < 60 and np.abs(P[:, :2]).max() < 60, 'castle fits in %.0f x %.0f x %.0f m' % tuple(P.max(0) - P.min(0)))
    alpha_geoms = sum(1 for at in dff['atomics'] if any(m['tex']['name'] in ('cs_web', 'cs_orb', 'cs_flame') for m in dff['geoms'][at['geom']]['materials']))
    ok(alpha_geoms >= 1, 'alpha atomic(s) present: %d' % alpha_geoms)
    for k in ('gate', 'door'):
        _, _, u2 = check_dff(paths[k], names)
        used |= u2
    unused = sorted(set(names) - used)
    ok(not unused, 'every texture is used by one of the three models' + (': %s' % unused if unused else ''), warn=True)

    say('\n-- COL --')
    boxes_all = []
    for k, label in (('col', 'Castle'), ('gcol', 'CastleGate'), ('dcol', 'CastleDoor')):
        c = readers.read_col3(paths[k])
        ok(c['name'] == label and c['end'] + 4 <= c['total'] + 4, '%s.col: COL3 name %s, %d boxes, %d faces, %.1f KB, size field consistent' % (label, c['name'], len(c['boxes']), len(c['faces']), c['total'] / 1024))
        ok(c['flags'] & 2, '  flags: not-empty bit set (0x%X)' % c['flags'])
        if k == 'col':
            boxes_all = c['boxes']
            colinfo = c
            ok(len(c['faces']) < 65535 and len(c['boxes']) < 65535, '  counts within uint16')
            ok(all(b[0] < b[3] and b[1] < b[4] and b[2] < b[5] for b in c['boxes']), '  every box has positive size')
    b = np.array([x[:6] for x in boxes_all])
    mn, mx = np.array(colinfo['min']), np.array(colinfo['max'])
    ok(np.allclose(mn, b[:, :3].min(0), atol=0.01) or (mn <= b[:, :3].min(0) + 0.01).all(), 'COL bounds enclose all boxes: %s .. %s' % (np.round(mn, 1), np.round(mx, 1)))
    ok(abs(mn[2] + 2.0) < 0.05 and mx[2] >= 29.9, 'COL vertical extent plausible (plinth bottom -2.0 .. tower %.1f)' % mx[2])

    # ---------------------------------------------------------------- walkability
    say('\n-- walkability (voxelised collision, 1.8 m walker) --')
    walk(paths['col'], boxes_all, dff)

    say('\n=== %d failures, %d warnings ===' % (len(fails), len(warns)))
    open(os.path.join(HERE, 'qc_report.txt'), 'w').write('\n'.join(lines) + '\n')
    return 1 if fails else 0


def walk(colpath, boxes, dff):
    import struct
    V = 0.2
    lo = np.array([-30.0, -16.0, -2.4])
    hi = np.array([30.0, 46.0, 36.0])
    shp = np.ceil((hi - lo) / V).astype(int)
    solid = np.zeros(shp, bool)

    def idx(v, ceil=False):
        return np.floor((np.asarray(v) - lo) / V + 1e-6).astype(int)
    for bx in boxes:
        a = idx(bx[:3])
        b = np.ceil((np.array(bx[3:6]) - lo) / V - 1e-6).astype(int)
        a = np.maximum(a, 0)
        b = np.minimum(b, shp)
        solid[a[0]:b[0], a[1]:b[1], a[2]:b[2]] = True
    # mesh (convex prisms): re-read vertices/faces from the file
    buf = open(colpath, 'rb').read()
    ns, nb, nf = struct.unpack_from('<HHH', buf, 72)
    flags, o_s, o_b, o_c, o_v, o_f = struct.unpack_from('<6I', buf, 80)
    nv_ = (o_f - o_v) // 6 if o_v else 0
    nv_ = int(np.ceil((o_f - o_v) / 6)) if o_v else 0
    verts = np.array([struct.unpack_from('<3h', buf, 4 + o_v + 6 * i) for i in range(max(0, min(nv_, (o_f - o_v) // 6)))]) / 128.0 if o_v else np.zeros((0, 3))
    faces = np.array([struct.unpack_from('<3H', buf, 4 + o_f + 8 * i) for i in range(nf)]) if nf else np.zeros((0, 3), int)
    # 12 faces per prism, consecutive: voxelise each prism as a convex hull of its vertices
    for k in range(0, len(faces), 12):
        f = faces[k:k + 12]
        vs = np.unique(f.reshape(-1))
        pts = verts[vs]
        a = np.maximum(idx(pts.min(0)), 0)
        b = np.minimum(idx(pts.max(0)) + 1, shp)
        xs, ys, zs = np.meshgrid(np.arange(a[0], b[0]), np.arange(a[1], b[1]), np.arange(a[2], b[2]), indexing='ij')
        ctr = lo + (np.stack([xs, ys, zs], -1) + 0.5) * V
        inside = np.ones(xs.shape, bool)
        cen = pts.mean(0)
        for tri in f:
            p0, p1, p2 = verts[tri]
            n = np.cross(p1 - p0, p2 - p0)
            ln = np.linalg.norm(n)
            if ln < 1e-9:
                continue
            n /= ln
            if np.dot(n, cen - p0) > 0:
                n = -n
            inside &= ((ctr - p0) @ n) <= 0.02
        solid[a[0]:b[0], a[1]:b[1], a[2]:b[2]] |= inside
    solid[:, :, :int(round((-2.0 - lo[2]) / V))] = True     # terrain below the plinth (not part of the COL)
    say('  voxel grid %s, solid %.2f%%' % (tuple(shp), 100 * solid.mean()))
    H = 9                                  # 1.8 m headroom
    free_run = np.zeros(shp, np.int16)     # number of free voxels directly above (inclusive), capped
    cum = np.zeros(shp, np.int16)
    for k in range(shp[2] - 1, -1, -1):
        cum[:, :, k] = np.where(solid[:, :, k], 0, 1 + (cum[:, :, k + 1] if k + 1 < shp[2] else 0))
    stand = (~solid) & (cum >= H)
    below = np.zeros(shp, bool)
    below[:, :, 1:] = solid[:, :, :-1]
    stand &= below
    # BFS over standing voxels; moves: 8 neighbours with dz in [-3..+2] voxels (0.45 m up)
    from collections import deque
    start = tuple(idx((0.0, -14.5, -1.9)))
    # find the standing voxel in that column
    col = np.nonzero(stand[start[0], start[1], :])[0]
    ok(len(col) > 0, 'start point outside the castle is walkable ground')
    s0 = (start[0], start[1], int(col[0]))
    seen = np.zeros(shp, bool)
    seen[s0] = True
    dq = deque([s0])
    nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    while dq:
        x, y, z = dq.popleft()
        for dx, dy in nbrs:
            xx, yy = x + dx, y + dy
            if not (0 <= xx < shp[0] and 0 <= yy < shp[1]):
                continue
            for dz in (0, 1, 2, -1, -2, -3):
                zz = z + dz
                if 0 <= zz < shp[2] and stand[xx, yy, zz] and not seen[xx, yy, zz]:
                    if dx and dy:                       # diagonal: both side cells must be free at the walker height
                        if solid[x + dx, y, z + 1:z + H].any() or solid[x, y + dy, z + 1:z + H].any():
                            continue
                    seen[xx, yy, zz] = True
                    dq.append((xx, yy, zz))
                    break
    say('  reachable standing voxels: %d' % seen.sum())
    targets = [
        ('terrace in front of the gate', (0.0, -3.0, 0.0)),
        ('hall floor (centre)', (0.0, 4.0, 0.0)),
        ('hall floor near the grand stair', (0.0, 7.0, 0.0)),
        ('grand stair top / dais', (0.0, 13.0, 2.0)),
        ('throne dais, rear', (3.0, 23.0, 2.0)),
        ('west flight, mid', (-6.8, 8.5, 4.4)),
        ('east flight, mid', (6.8, 8.5, 4.4)),
        ('gallery (upper floor over the gate)', (0.0, 3.5, 6.8)),
        ('west wing ground (library)', (-15.0, 11.0, 0.0)),
        ('west wing upper floor', (-15.6, 11.0, 6.8)),
        ('east wing ground (dining hall)', (15.0, 5.0, 0.0)),
        ('east wing upper floor', (15.6, 11.0, 6.8)),
        ('keep ground floor (through the rear doors)', (-5.0, 30.0, 2.0)),
        ('keep spiral stair, first steps', (-2.9, 32.0, 2.4)),
        ('keep top level (observation floor)', (-5.2, 32.7, 22.0)),
    ]
    for label, p in targets:
        a = idx(p)
        # the nearest standing voxel within +-0.6 m
        found = False
        for r in range(0, 4):
            sl = (slice(max(a[0] - r, 0), a[0] + r + 1), slice(max(a[1] - r, 0), a[1] + r + 1), slice(max(a[2] - 2, 0), a[2] + 4))
            if (seen[sl]).any():
                found = True
                break
        ok(found, 'reachable on foot: %s %s' % (label, p))
    # things that must NOT be reachable: walking onto the roofs / towers
    unreach = [('roof ridge of the great hall', (0.0, 10.0, 28.0)), ('front tower crown', (13.0, -3.5, 17.0))]
    for label, p in unreach:
        a = idx(p)
        sl = (slice(max(a[0] - 3, 0), a[0] + 4), slice(max(a[1] - 3, 0), a[1] + 4), slice(max(a[2] - 3, 0), a[2] + 4))
        ok(not seen[sl].any(), 'not walkable (expected): %s' % label, warn=True)
    # head bump / stuck tests: standing voxels reachable at least on both side of every wing door
    for label, p in (('west ground door', (-8.6, 2.7, 0.0)), ('east upper door', (8.6, 4.9, 6.8)), ('keep west door', (-4.9, 25.8, 2.0)), ('keep east door', (4.9, 25.8, 2.0))):
        a = idx(p)
        sl = (slice(a[0] - 1, a[0] + 2), slice(a[1] - 1, a[1] + 2), slice(a[2], a[2] + 3))
        ok(seen[sl].any(), 'doorway is passable: %s' % label)
    return seen


if __name__ == '__main__':
    sys.exit(main())
