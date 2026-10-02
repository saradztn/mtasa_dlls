# Created by: Arena.ai Agent Mode (AI) - Castle MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# parts.py - props and architectural details: bars, rings, candles, flames, torches, chandeliers,
#            cobwebs, spiders, tables, chairs, bookshelves, throne, bed, lanterns, columns,
#            arch trims, finials, roofs.
# Every function adds geometry to the Mesh `M`, collision to `C` (if the object is solid) and
# registers lights in `L` (list of dict(pos, col, rad, k)).
# -----------------------------------------------------------------------------
import numpy as np
from .mb import Mesh, Col, v3, unit, TAU, arch_fn
from .tex import M as MI

ST, SI, TR, FL, TL, SL, WD, DR, IR, RG, WB, OB, GL, FM, BK, BN, GD, CV = [MI[n] for n in
    ['cs_stone', 'cs_stone_in', 'cs_trim', 'cs_flag', 'cs_tile', 'cs_slate', 'cs_wood', 'cs_door', 'cs_iron', 'cs_rug',
     'cs_web', 'cs_orb', 'cs_glass', 'cs_flame', 'cs_books', 'cs_banner', 'cs_gold', 'cs_carved']]

WARM = (1.0, 0.58, 0.24)


def rot2(p, ang):
    c, s = np.cos(ang), np.sin(ang)
    return np.array([c * p[0] - s * p[1], s * p[0] + c * p[1]])


# --------------------------------------------------------------------------------------------
def bar(M, p0, p1, w, mat, h=None, tile=1.0, caps=True, emis=0.0):
    """rectangular bar between two points (w wide, h tall; default square)"""
    h = w if h is None else h
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = unit(p1 - p0)
    up = np.array([0, 0, 1.0])
    if abs(d[2]) > 0.98:
        up = np.array([1.0, 0, 0])
    right = unit(np.cross(d, up))
    upv = np.cross(right, d)
    c = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ring0 = [p0 + right * a * w / 2 + upv * b * h / 2 for a, b in c]
    ring1 = [p1 + right * a * w / 2 + upv * b * h / 2 for a, b in c]
    L = np.linalg.norm(p1 - p0)
    mid = (p0 + p1) / 2
    for i in range(4):
        j = (i + 1) % 4
        pts = [ring0[i], ring0[j], ring1[j], ring1[i]]
        cen = (ring0[i] + ring0[j]) / 2 - p0
        M.poly(pts, mat, hint=cen - d * np.dot(cen, d), uv=[(0, 0), (w / tile, 0), (w / tile, L / tile), (0, L / tile)], emis=emis)
    if caps:
        M.poly(ring0[::-1], mat, hint=-d, tile=tile, emis=emis)
        M.poly(ring1, mat, hint=d, tile=tile, emis=emis)


def ring_h(M, center, R, r, mat, nu=24, nv=6, emis=0.0, tile=1.0):
    """horizontal torus-like ring (smooth), centre-line radius R, tube radius r"""
    cx, cy, cz = center
    P, N, UV, T = [], [], [], []
    for i in range(nu + 1):
        u = i * TAU / nu
        for j in range(nv + 1):
            v = j * TAU / nv
            n = np.array([np.cos(v) * np.cos(u), np.cos(v) * np.sin(u), np.sin(v)])
            P.append([cx + (R + r * np.cos(v)) * np.cos(u), cy + (R + r * np.cos(v)) * np.sin(u), cz + r * np.sin(v)])
            N.append(n)
            UV.append([u / TAU * TAU * R / tile, v / TAU * TAU * r / tile])
    P, N = np.array(P), np.array(N)
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            b = a + nv + 1
            for tri in ([a, b, b + 1], [a, b + 1, a + 1]):
                nf = np.cross(P[tri[1]] - P[tri[0]], P[tri[2]] - P[tri[0]])
                T.append(tri if np.dot(nf, N[tri[0]]) >= 0 else tri[::-1])
    M.add(P, N, UV, T, mat, emis)


def sphere(M, c, r, mat, nu=10, nv=6, emis=0.0, sq=(1, 1, 1)):
    P, N, UV, T = [], [], [], []
    for j in range(nv + 1):
        ph = np.pi * j / nv - np.pi / 2
        for i in range(nu + 1):
            th = TAU * i / nu
            n = np.array([np.cos(ph) * np.cos(th), np.cos(ph) * np.sin(th), np.sin(ph)])
            P.append(np.array(c) + n * r * np.array(sq))
            N.append(unit(n / np.array(sq)))
            UV.append([i / nu, j / nv])
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            b = a + nu + 1
            for tri in ([a, a + 1, b + 1], [a, b + 1, b]):
                nf = np.cross(np.array(P[tri[1]]) - np.array(P[tri[0]]), np.array(P[tri[2]]) - np.array(P[tri[0]]))
                T.append(tri if np.dot(nf, N[tri[0]]) >= 0 else tri[::-1])
    M.add(P, N, UV, T, mat, emis)


# --------------------------------------------------------------------------------------------
# light and fire
# --------------------------------------------------------------------------------------------
def add_light(L, pos, col=WARM, rad=7.0, k=1.0):
    L.append(dict(pos=np.array(pos, float), col=np.array(col, float), rad=float(rad), k=float(k)))


def flame(M, p, h=0.22, w=0.12, rot=0.0):
    """two crossed, double sided flame cards (alpha, fullbright)"""
    p = np.asarray(p, float)
    for ang in (rot, rot + np.pi / 2):
        d = np.array([np.cos(ang), np.sin(ang), 0.0]) * w / 2
        pts = [p - d, p + d, p + d + [0, 0, h], p - d + [0, 0, h]]
        M.poly(pts, FM, hint=np.cross(d, [0, 0, 1]), uv=[(0, 1), (1, 1), (1, 0), (0, 0)], emis=1.0, double=True)


def candle(M, p, h=0.18, r=0.022, with_flame=True):
    x, y, z = p
    M.prism((x, y), r, z, z + h, 6, TR, tile=0.3, cap_top=True)
    if with_flame:
        flame(M, (x, y, z + h), 0.11, 0.06)


def torch(M, L, pos, outward, z=3.2):
    """wall torch: iron bracket + cup + flame; `pos` = (x,y) on the wall surface, outward = unit 2D normal into the room"""
    x, y = pos
    o = np.array(outward, float)
    base = np.array([x, y, z])
    tip = base + np.array([o[0], o[1], 0.0]) * 0.34 + [0, 0, 0.28]
    bar(M, base, base + [o[0] * 0.30, o[1] * 0.30, 0.0], 0.05, IR, tile=0.3)
    bar(M, base + [o[0] * 0.30, o[1] * 0.30, 0.0], tip + [0, 0, -0.18], 0.05, IR, tile=0.3)
    M.prism((tip[0], tip[1]), 0.07, tip[2] - 0.20, tip[2] - 0.02, 8, IR, tile=0.3, smooth=True, cap_top=False)
    ring_h(M, (tip[0], tip[1], tip[2] - 0.02), 0.07, 0.012, IR, nu=10, nv=4)
    flame(M, (tip[0], tip[1], tip[2] - 0.02), 0.34, 0.20)
    add_light(L, tip + [0, 0, 0.1] + np.array([o[0], o[1], 0]) * 0.3, WARM, 6.5, 1.0)


def chandelier(M, L, C, c, R=1.1, nc=8):
    """iron ring chandelier hanging from a chain; c = ring centre"""
    cx, cy, cz = c
    ring_h(M, (cx, cy, cz), R, 0.04, IR, nu=28, nv=6)
    ring_h(M, (cx, cy, cz - 0.30), R * 0.55, 0.03, IR, nu=20, nv=5)
    for k in range(4):
        a = k * np.pi / 2 + np.pi / 4
        bar(M, (cx, cy, cz + 1.2), (cx + np.cos(a) * R, cy + np.sin(a) * R, cz), 0.03, IR, tile=0.3, caps=False)
        bar(M, (cx, cy, cz - 0.30), (cx + np.cos(a) * R * 0.55, cy + np.sin(a) * R * 0.55, cz - 0.30), 0.03, IR, tile=0.3)
    for z in np.arange(cz + 1.2, cz + 3.4, 0.22):                   # chain links (alternating orientation)
        bar(M, (cx, cy, z), (cx, cy, z + 0.17), 0.045, IR, tile=0.3, caps=False)
    sphere(M, (cx, cy, cz - 0.55), 0.10, IR, 8, 5, sq=(1, 1, 1.5))
    for k in range(nc):
        a = k * TAU / nc
        px, py = cx + np.cos(a) * R, cy + np.sin(a) * R
        M.prism((px, py), 0.05, cz, cz + 0.05, 8, GD, tile=0.3, smooth=True)
        candle(M, (px, py, cz + 0.05), 0.2)
    add_light(L, (cx, cy, cz + 0.4), WARM, 11.0, 1.3)


# --------------------------------------------------------------------------------------------
# cobwebs and spiders
# --------------------------------------------------------------------------------------------
def web_corner(M, p, d1, d2, size, size2=None):
    """triangular web stretched in the corner p between directions d1 and d2 (double sided)"""
    p = np.asarray(p, float)
    d1, d2 = unit(d1), unit(d2)
    s2 = size if size2 is None else size2
    pts = [p, p + d1 * size, p + d2 * s2]
    M.poly(pts, WB, hint=np.cross(d1, d2), uv=[(0, 0), (1, 0), (0, 1)], emis=0.0, double=True)


def web_orb(M, c, normal, size, up=(0, 0, 1)):
    c = np.asarray(c, float)
    n = unit(normal)
    r = unit(np.cross(up, n))
    u = np.cross(n, r)
    h = size / 2
    pts = [c - r * h - u * h, c + r * h - u * h, c + r * h + u * h, c - r * h + u * h]
    M.poly(pts, OB, hint=n, uv=[(0, 1), (1, 1), (1, 0), (0, 0)], double=True)


def spider(M, p, scale=1.0, thread_to=None, rot=0.0):
    """small spider (body + 8 legs) hanging at p; optional thread up to z=thread_to"""
    p = np.asarray(p, float)
    s = scale
    sphere(M, p + [0, 0, 0], 0.045 * s, IR, 8, 5, sq=(1, 1.3, 0.8))
    sphere(M, p + [0, 0.07 * s, 0.005 * s], 0.028 * s, IR, 6, 4)
    for k in range(4):
        for side in (-1, 1):
            a = (k - 1.5) * 0.45 + 1.5707 * 0 + rot
            base = p + [side * 0.03 * s, (k - 1.5) * 0.02 * s, 0]
            knee = base + [side * 0.12 * s, (k - 1.5) * 0.08 * s, 0.08 * s]
            foot = knee + [side * 0.10 * s, (k - 1.5) * 0.05 * s, -0.16 * s]
            bar(M, base, knee, 0.008 * s, IR, tile=0.1)
            bar(M, knee, foot, 0.006 * s, IR, tile=0.1)
    if thread_to is not None:
        pts = [p + [-0.004, 0, 0], p + [0.004, 0, 0], np.array([p[0] + 0.004, p[1], thread_to]), np.array([p[0] - 0.004, p[1], thread_to])]
        M.poly(pts, WB, hint=(0, 1, 0), uv=[(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01)], double=True)


# --------------------------------------------------------------------------------------------
# furniture
# --------------------------------------------------------------------------------------------
def table(M, C, c, size, h=0.78, mat=WD, rot90=False):
    cx, cy = c
    sx, sy = size
    if rot90:
        sx, sy = sy, sx
    M.box((cx - sx / 2, cy - sy / 2, h - 0.07), (cx + sx / 2, cy + sy / 2, h), mat, tile=1.0)
    for dx in (-1, 1):
        for dy in (-1, 1):
            lx, ly = cx + dx * (sx / 2 - 0.12), cy + dy * (sy / 2 - 0.12)
            M.box((lx - 0.07, ly - 0.07, 0), (lx + 0.07, ly + 0.07, h - 0.07), mat, tile=1.0, skip=('-z',))
    M.box((cx - sx / 2 + 0.12, cy - 0.04, 0.25), (cx + sx / 2 - 0.12, cy + 0.04, 0.33), mat, tile=1.0) if sx > sy else \
        M.box((cx - 0.04, cy - sy / 2 + 0.12, 0.25), (cx + 0.04, cy + sy / 2 - 0.12, 0.33), mat, tile=1.0)
    C.box((cx - sx / 2, cy - sy / 2, 0), (cx + sx / 2, cy + sy / 2, h))


def chair(M, C, c, facing, h=0.46, back=1.05, mat=WD, solid=True):
    """facing = 2D unit vector towards which the sitter looks"""
    cx, cy = c
    f = np.array(facing, float)
    r = np.array([-f[1], f[0]])

    def P(a, b):
        return np.array([cx, cy]) + f * a + r * b

    def blk(a0, a1, b0, b1, z0, z1):
        pts = [P(a0, b0), P(a1, b0), P(a1, b1), P(a0, b1)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        M.box((min(xs), min(ys), z0), (max(xs), max(ys), z1), mat, tile=1.0)
    # (chairs are rotated by multiples of 90 degrees in this scene, so AABBs are exact)
    blk(-0.22, 0.22, -0.22, 0.22, h - 0.05, h)
    blk(-0.22, -0.18, -0.22, 0.22, h, back)
    for a in (-0.20, 0.20):
        for b in (-0.20, 0.20):
            blk(a - 0.02, a + 0.02, b - 0.02, b + 0.02, 0, h - 0.05)
    if solid:
        pts = [P(-0.22, -0.22), P(0.22, 0.22)]
        C.box((min(pts[0][0], pts[1][0]), min(pts[0][1], pts[1][1]), 0), (max(pts[0][0], pts[1][0]), max(pts[0][1], pts[1][1]), h))


def bookshelf(M, C, lo, hi, front):
    """lo/hi: AABB. front: axis string '+x','-x','+y','-y' of the face carrying the books"""
    M.box(lo, hi, WD, tile=1.0, skip=(front,))
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    e = 0.012
    if front == '+x':
        pts = [(x1 + e, y0, z0), (x1 + e, y1, z0), (x1 + e, y1, z1), (x1 + e, y0, z1)]
        L = y1 - y0
    elif front == '-x':
        pts = [(x0 - e, y1, z0), (x0 - e, y0, z0), (x0 - e, y0, z1), (x0 - e, y1, z1)]
        L = y1 - y0
    elif front == '+y':
        pts = [(x1, y1 + e, z0), (x0, y1 + e, z0), (x0, y1 + e, z1), (x1, y1 + e, z1)]
        L = x1 - x0
    else:
        pts = [(x0, y0 - e, z0), (x1, y0 - e, z0), (x1, y0 - e, z1), (x0, y0 - e, z1)]
        L = x1 - x0
    nrm = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0)}[front]
    H = z1 - z0
    M.poly(pts, BK, hint=nrm, uv=[(0, 1), (L / 1.2, 1), (L / 1.2, 1 - H / 1.2), (0, 1 - H / 1.2)])
    C.box(lo, hi)


def throne(M, C, c):
    cx, cy = c
    M.box((cx - 0.55, cy - 0.5, 0.0), (cx + 0.55, cy + 0.45, 0.55), WD, tile=1.0)
    M.box((cx - 0.55, cy + 0.34, 0.55), (cx + 0.55, cy + 0.50, 2.7), WD, tile=1.0)
    for sx in (-1, 1):                                                    # arms
        M.box((cx + sx * 0.55 - (0.0 if sx > 0 else 0.12), cy - 0.45, 0.55), (cx + sx * 0.55 + (0.12 if sx > 0 else 0.0), cy + 0.40, 0.95), WD, tile=1.0)
        M.box((cx + sx * 0.60 - 0.05, cy - 0.45, 0.95), (cx + sx * 0.60 + 0.05, cy - 0.35, 1.0), GD, tile=0.3)
    # pointed crown
    pts = [(cx - 0.55, cy + 0.50, 2.7), (cx + 0.55, cy + 0.50, 2.7), (cx, cy + 0.50, 3.5)]
    M.poly(pts, WD, hint=(0, 1, 0), tile=1.0)
    M.poly([(cx - 0.55, cy + 0.34, 2.7), (cx, cy + 0.34, 3.5), (cx + 0.55, cy + 0.34, 2.7)], WD, hint=(0, -1, 0), tile=1.0)
    for sx in (-1, 1):
        M.poly([(cx + sx * 0.55, cy + 0.34, 2.7), (cx + sx * 0.55, cy + 0.50, 2.7), (cx, cy + 0.50, 3.5), (cx, cy + 0.34, 3.5)], WD,
               hint=(sx * 0.8, 0, 0.6), tile=1.0)
    for sx in (-1, 1):
        M.cone((cx + sx * 0.55, cy + 0.42), 0.07, 2.7, 3.15, 6, GD, tile=0.3, smooth=True)
    M.box((cx - 0.40, cy - 0.44, 0.55), (cx + 0.40, cy + 0.34, 0.62), RG, tile=1.0)       # cushion (rug texture = red velvet)
    C.box((cx - 0.60, cy - 0.5, 0), (cx + 0.60, cy + 0.52, 1.0))
    C.box((cx - 0.55, cy + 0.34, 1.0), (cx + 0.55, cy + 0.52, 2.7))


def bed(M, C, c, length=2.2, width=1.5):
    cx, cy = c
    M.box((cx - width / 2, cy - length / 2, 0.25), (cx + width / 2, cy + length / 2, 0.55), WD, tile=1.0)
    M.box((cx - width / 2 + 0.05, cy - length / 2 + 0.05, 0.55), (cx + width / 2 - 0.05, cy + length / 2 - 0.05, 0.72), RG, tile=1.2)
    M.box((cx - width / 2 + 0.2, cy + length / 2 - 0.50, 0.72), (cx + width / 2 - 0.2, cy + length / 2 - 0.10, 0.82), BN, tile=0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = cx + sx * (width / 2 - 0.05), cy + sy * (length / 2 - 0.05)
            M.box((px - 0.05, py - 0.05, 0), (px + 0.05, py + 0.05, 2.2 if sy > 0 else 1.0), WD, tile=1.0)
    M.box((cx - width / 2, cy + length / 2 - 0.04, 0.5), (cx + width / 2, cy + length / 2, 1.5), WD, tile=1.0)
    M.box((cx - width / 2 - 0.02, cy - length / 2, 2.15), (cx + width / 2 + 0.02, cy + length / 2, 2.2), WD, tile=1.0)
    C.box((cx - width / 2, cy - length / 2, 0), (cx + width / 2, cy + length / 2, 0.8))


def chest(M, C, c, size=(1.1, 0.55, 0.55)):
    cx, cy = c
    sx, sy, sz = size
    M.box((cx - sx / 2, cy - sy / 2, 0), (cx + sx / 2, cy + sy / 2, sz), WD, tile=1.0)
    for k in (-0.3, 0.3):
        M.box((cx + k * sx - 0.03, cy - sy / 2 - 0.01, 0), (cx + k * sx + 0.03, cy + sy / 2 + 0.01, sz + 0.005), IR, tile=0.3)
    M.box((cx - 0.04, cy - sy / 2 - 0.02, sz * 0.55), (cx + 0.04, cy - sy / 2, sz * 0.8), GD, tile=0.3)
    C.box((cx - sx / 2, cy - sy / 2, 0), (cx + sx / 2, cy + sy / 2, sz))


def rug(M, x0, y0, x1, y1, z, mat=RG):
    """rug lying on the floor, long axis along y (u across the width, motif period = 2 x width)"""
    w = x1 - x0
    L = y1 - y0
    M.poly([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], mat, hint=(0, 0, 1),
           uv=[(0, 0), (1, 0), (1, L / (2 * w)), (0, L / (2 * w))])


def banner(M, pos, normal, w=1.2, h=2.4, z0=5.0):
    """hanging banner on a wall at pos (x,y), normal = unit 2D vector pointing into the room"""
    x, y = pos
    n = np.array([normal[0], normal[1], 0.0])
    t = np.array([-n[1], n[0], 0.0])
    c = np.array([x, y, 0.0]) + n * 0.04
    pts = [c + t * w / 2 + [0, 0, z0], c - t * w / 2 + [0, 0, z0], c - t * w / 2 + [0, 0, z0 + h], c + t * w / 2 + [0, 0, z0 + h]]
    M.poly(pts, BN, hint=n, uv=[(1, 1), (0, 1), (0, 0), (1, 0)])
    bar(M, c - t * (w / 2 + 0.06) + [0, 0, z0 + h + 0.02], c + t * (w / 2 + 0.06) + [0, 0, z0 + h + 0.02], 0.05, IR, tile=0.3)


def lantern(M, L, base, h=1.7):
    """exterior lantern post with glowing orange cage like in the reference picture"""
    x, y, z = base
    M.prism((x, y), 0.07, z, z + h, 8, IR, tile=0.5, smooth=True)
    M.prism((x, y), 0.14, z, z + 0.14, 8, IR, tile=0.5)
    bar(M, (x, y, z + h), (x, y, z + h + 0.06), 0.30, IR, tile=0.5)
    M.box((x - 0.14, y - 0.14, z + h + 0.06), (x + 0.14, y + 0.14, z + h + 0.46), GL, tile=0.4, emis=1.0, skip=('-z',))
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar(M, (x + sx * 0.145, y + sy * 0.145, z + h + 0.06), (x + sx * 0.145, y + sy * 0.145, z + h + 0.46), 0.03, IR, tile=0.3)
    M.cone((x, y), 0.26, z + h + 0.46, z + h + 0.68, 4, IR, tile=0.5, theta0=np.pi / 4)
    flame(M, (x, y, z + h + 0.10), 0.30, 0.20)
    add_light(L, (x, y, z + h + 0.3), (1.0, 0.50, 0.15), 9.0, 1.2)


def column(M, C, c, r, z0, z1, mat=TR, collide=True, cap=True):
    x, y = c
    M.prism((x, y), r * 1.35, z0, z0 + 0.18, 8, mat, tile=1.5, cap_top=False)
    M.prism((x, y), r * 1.15, z0 + 0.18, z0 + 0.34, 8, mat, tile=1.5, cap_top=True)
    M.prism((x, y), r, z0 + 0.34, z1 - 0.34, 8, mat, tile=1.5, cap_top=False, theta0=np.pi / 8)
    if cap:
        M.prism((x, y), r * 1.15, z1 - 0.34, z1 - 0.18, 8, mat, tile=1.5, cap_top=False)
        M.cone((x, y), r * 1.55, z1 - 0.18, z1, 8, mat, tile=1.5, r_top=r * 1.3)
        M.prism((x, y), r * 1.6, z1 - 0.10, z1, 4, mat, tile=1.5, cap_top=True, theta0=np.pi / 4, ex=1.0, ey=1.0)
    if collide:
        C.box((x - r * 1.0, y - r * 1.0, z0), (x + r * 1.0, y + r * 1.0, z1))


def arch_trim(M, a, b, t, side, s0, s1, zs, k, width=0.3, depth=0.18, mat=TR, nseg=10, jamb=2.0):
    """stone hood moulding on the face (side=+1 left of a->b, -1 right) of a wall (centre line a->b, thickness t)
    around a pointed arch opening [s0,s1] with springline zs (curve ratio k)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = unit(b - a)
    nl = np.array([-d[1], d[0]])
    n2 = nl * side
    fn, apex = arch_fn(s0, s1, zs, k)
    xc = (s0 + s1) / 2
    ss = np.concatenate([np.linspace(s0, xc, nseg + 1), np.linspace(xc, s1, nseg + 1)[1:]])
    zz = fn(ss)
    dz = np.gradient(zz, ss)
    nn = np.stack([-dz, np.ones_like(dz)], -1)
    nn = nn / np.linalg.norm(nn, axis=-1, keepdims=True)
    # normal of the curve in (s,z) plane pointing away from the opening: (-dz/ds, 1)
    inner = np.stack([ss, zz], -1)
    outer = inner + nn * width

    def W(s, z, o):
        q = a + d * s + nl * side * t / 2 + n2 * o
        return np.array([q[0], q[1], z])
    hint = np.array([n2[0], n2[1], 0.0])
    for i in range(len(ss) - 1):
        pi_, pj = inner[i], inner[i + 1]
        qi, qj = outer[i], outer[i + 1]
        M.poly([W(pi_[0], pi_[1], depth), W(pj[0], pj[1], depth), W(qj[0], qj[1], depth), W(qi[0], qi[1], depth)], mat,
               hint=hint, tile=1.0)
        mid = (qi + qj) / 2 - (pi_ + pj) / 2
        sh = np.array([d[0] * mid[0], d[1] * mid[0], mid[1]])
        M.poly([W(qi[0], qi[1], 0.0), W(qj[0], qj[1], 0.0), W(qj[0], qj[1], depth), W(qi[0], qi[1], depth)], mat, hint=sh, tile=1.0)
    for s_edge, sg in ((s0, -1), (s1, 1)):
        zl = zs - jamb
        M.poly([W(s_edge, zl, depth), W(s_edge, zs, depth), W(s_edge + sg * width, zs, depth), W(s_edge + sg * width, zl, depth)], mat, hint=hint, tile=1.0)
        M.poly([W(s_edge + sg * width, zl, 0), W(s_edge + sg * width, zs, 0), W(s_edge + sg * width, zs, depth), W(s_edge + sg * width, zl, depth)], mat,
               hint=np.array([d[0] * sg, d[1] * sg, 0.0]), tile=1.0)


def finial(M, c, z, h=1.8, r=0.2):
    x, y = c
    M.prism((x, y), r, z, z + 0.25, 8, IR, tile=0.5, smooth=True)
    sphere(M, (x, y, z + 0.35), r * 0.9, IR, 8, 5)
    M.cone((x, y), r * 0.55, z + 0.3, z + h, 8, IR, tile=0.5, smooth=True)
