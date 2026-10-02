# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# model.py - the fishing rod itself (7'0" medium-fast spinning rod + 3000 reel)
#
# Coordinate system (GTA/MTA): +X right, +Y forward (rod tip), +Z up. 1 unit = 1 m.
# ORIGIN = centre of the reel seat on the rod axis (where the hand holds a rod).
# The rod lies along +Y, guides + reel hang on the underside (-Z), the reel
# handle is on the left (-X).  Total length 2.13 m (7 ft).
#
# Frames / atomics exported to the DFF:
#   FishingRod (root dummy)
#     fr_rod         rod blank, handle, reel seat, guides, tip-top, wraps
#     fr_reel_body   reel housing, plates, foot/stem, crank, knob, switches
#     fr_reel_rotor  rotor, spool, drag knob, bail wire, roller (pivot = spool axis)
#     fr_line        monofilament  spool -> roller -> guides -> tip-top
# -----------------------------------------------------------------------------
import numpy as np
from .geom import *
from .materials import M

# ---------------------------------------------------------------------------
# global dimensions (metres)
# ---------------------------------------------------------------------------
BUTT_Y = -0.300
TIP_Y = 1.645            # blank end  (total length = 1.945 + ... see README: 2.13 incl. reel overhang? no)
BLANK_Y0 = 0.170         # blank starts inside the handle
BLANK_R0 = 0.0071        # blank radius at BLANK_Y0 (14.2 mm)
BLANK_RT = 0.0010        # blank radius at the tip
SAG = 0.075              # relaxed bend of the tip (towards the guides)
BEND_Y0 = 0.183
FERRULE = (0.860, 0.940)
LABEL_END = 0.520

REEL_O = np.array([0.0, 0.0, -0.0865])      # spool axis origin (rotor pivot)
LINE_R = 0.0005
TAU = np.pi * 2


def rod_path(y):
    t = np.clip((y - BEND_Y0) / (TIP_Y - BEND_Y0), 0.0, 1.0)
    return np.array([0.0, y, -SAG * t ** 2.2])


def blank_r(y):
    t = np.clip((y - BLANK_Y0) / (TIP_Y - BLANK_Y0), 0.0, 1.0)
    return BLANK_RT + (BLANK_R0 - BLANK_RT) * (1 - t) ** 1.30


def rod_frame_at(y):
    """centre, tangent, up at blank position y"""
    h = 1e-4
    C = rod_path(y)
    T = rod_path(y + h) - rod_path(y - h)
    T = T / np.linalg.norm(T)
    up = np.cross(np.array([1.0, 0, 0]), T)
    up = up / np.linalg.norm(up)
    return C, T, up


ROD = AxisFrame((0, 0, 0), (0, 1, 0), (1, 0, 0))           # e1=+X e2=+Z
BLANK = PathFrame(rod_path)
TH0 = np.pi / 2                                            # seam on top (+Z)


def cyl_outline(n):
    return circle_outline(n, TH0)


def lathe(name, mat, origin, axis, e1, prof, nu=48, tile=(0.03, 0.03), v0=0.0, mod=None, flip=False,
          caps=True, u_rep=None, theta0=TH0, outline=None, u0=0.0):
    prof = [tuple(p) for p in prof]
    if caps and prof[0][1] > 1e-9:
        prof.insert(0, (prof[0][0], 0.0))
    if caps and prof[-1][1] > 1e-9:
        prof.append((prof[-1][0], 0.0))
    rows = profile_with_v(prof, 1.0 / tile[1], v0)
    smax = max(p[1] for p in prof)
    ur = u_rep if u_rep is not None else max(1, int(round(TAU * smax / tile[0])))
    fr = AxisFrame(origin, axis, e1)
    out = circle_outline(nu, theta0) if outline is None else outline
    return skin(name, mat, fr, rows, out, u_rep=ur, mod=mod, flip=flip, u0=u0)


def rod_lathe(name, mat, prof, nu=48, tile=(0.03, 0.03), **kw):
    return lathe(name, mat, (0, 0, 0), (0, 1, 0), (1, 0, 0), prof, nu=nu, tile=tile, **kw)


def knurl(n_flutes, depth, a0, a1, ramp=0.0008):
    """radius multiplier producing straight flutes between a0..a1"""
    def f(a, frac):
        w = np.clip(np.minimum(a - a0, a1 - a) / ramp, 0, 1)
        flute = 0.5 - 0.5 * np.cos(frac * TAU * n_flutes)
        return 1.0 - depth * w * flute ** 0.7
    return f


def lobes(n, depth):
    def f(a, frac):
        return 1.0 - depth * (0.5 - 0.5 * np.cos(frac * TAU * n))
    return f


def star_outline(nu, nlobes, depth):
    th = np.arange(nu + 1) * TAU / nu
    r = 1.0 - depth * (0.5 - 0.5 * np.cos(nlobes * th))
    return np.stack([np.cos(th) * r, np.sin(th) * r], -1)


# ---------------------------------------------------------------------------
# ROD: handle, seat
# ---------------------------------------------------------------------------
def build_handle():
    P = []
    # --- rubber butt pad (domed, soft rim)
    prof = fillet_profile([(BUTT_Y, 0.0), (BUTT_Y, 0.0141), (BUTT_Y + 0.0100, 0.0143)], [0, 0.0030, 0], 5)
    # make the dome: lift the centre by 1.6mm
    prof = [(a - 0.0016 * max(0.0, 1 - (s / 0.0120) ** 2), s) for a, s in prof]
    P.append(rod_lathe('butt_pad', M('rubber'), prof, nu=48, tile=(0.020, 0.020), caps=True))

    # --- rear grip, EVA with four soft ring grooves
    a0, a1 = BUTT_Y + 0.0100, -0.2250
    base = lambda a: 0.01425 + (0.0151 - 0.01425) * (a - a0) / (a1 - a0) + 0.0003 * np.sin(np.pi * (a - a0) / (a1 - a0))
    grooves = [(-0.2755, 0.0022, 0.00035), (-0.2625, 0.0022, 0.00035), (-0.2495, 0.0022, 0.00035), (-0.2365, 0.0022, 0.00035)]
    prof = groove_profile(base, a0, a1, 8, grooves)
    P.append(rod_lathe('eva_rear', M('eva'), prof, nu=44, tile=(0.032, 0.032)))

    # --- anodised accent ring
    pr = fillet_profile([(-0.2250, 0.0140), (-0.2250, 0.0153), (-0.2205, 0.0153), (-0.2205, 0.0140)], [0, 0.0004, 0.0004, 0], 3)
    P.append(rod_lathe('ring_a', M('alu_gold'), pr, nu=44, tile=(0.03, 0.03)))

    # --- cork centre section (swelling), separate material
    base = lambda a: 0.01520 + 0.00055 * np.sin(np.pi * (a + 0.2205) / 0.1085) - 0.0002 * (a + 0.2205) / 0.1085
    prof = [(a, base(a)) for a in np.linspace(-0.2205, -0.1120, 13)]
    P.append(rod_lathe('cork_rear', M('cork'), prof, nu=48, tile=(0.030, 0.034)))
    pr = fillet_profile([(-0.1120, 0.0140), (-0.1120, 0.0150), (-0.1085, 0.0150), (-0.1085, 0.0140)], [0, 0.0004, 0.0004, 0], 3)
    P.append(rod_lathe('ring_b', M('alu_gold'), pr, nu=44, tile=(0.03, 0.03)))
    # --- EVA leading into the reel seat
    a0, a1 = -0.1085, -0.0785
    base = lambda a: 0.0147 - 0.0009 * (a - a0) / (a1 - a0)
    prof = groove_profile(base, a0, a1, 6, [(-0.0930, 0.0020, 0.0003)])
    P.append(rod_lathe('eva_mid', M('eva'), prof, nu=44, tile=(0.032, 0.032)))

    # --- reel seat -------------------------------------------------------
    # fixed (rear) hood, dark anodised, with two fine grooves
    pts = [(-0.0785, 0.0), (-0.0785, 0.0140), (-0.0775, 0.0152), (-0.0735, 0.0163), (-0.0600, 0.0170),
           (-0.0500, 0.0168), (-0.0455, 0.0162), (-0.0440, 0.0156)]
    prof = []
    for a, s in pts:
        prof.append((a, s))
    prof = groove_profile(lambda a: np.interp(a, [p[0] for p in pts], [p[1] for p in pts]), -0.0785, -0.0440, 10,
                          [(-0.0650, 0.0018, 0.00025), (-0.0585, 0.0018, 0.00025)])
    P.append(rod_lathe('seat_hood_rear', M('alu_dark'), prof, nu=48, tile=(0.030, 0.030)))
    pr = fillet_profile([(-0.0420, 0.0150), (-0.0420, 0.0166), (-0.0392, 0.0166), (-0.0392, 0.0150)], [0, 0.0004, 0.0004, 0], 3)
    pr = [(-0.0440, 0.0156)] + pr
    P.append(rod_lathe('seat_ring_gold', M('alu_gold'), [(-0.0440, 0.0157), (-0.0430, 0.0166)] + fillet_profile(
        [(-0.0430, 0.0166), (-0.0405, 0.0167), (-0.0392, 0.0157)], [0, 0.0006, 0], 3)[1:], nu=48, tile=(0.03, 0.03)))
    # exposed seat tube (machined, threaded look comes from normal map)
    prof = [(a, 0.0155) for a in np.linspace(-0.0395, 0.0235, 3)]
    P.append(rod_lathe('seat_tube', M('alu_dark'), prof, nu=48, tile=(0.030, 0.024), u_rep=2))
    # sliding hood
    pts = [(0.0225, 0.0156), (0.0225, 0.0162), (0.0345, 0.0166), (0.0355, 0.0160)]
    pr = fillet_profile([(0.0225, 0.0150), (0.0225, 0.0163), (0.0350, 0.0163), (0.0360, 0.0150)], [0, 0.0006, 0.0006, 0], 3)
    P.append(rod_lathe('seat_hood_slide', M('alu_dark'), pr, nu=48, tile=(0.03, 0.03)))
    # knurled lock nut (24 real flutes)
    a0, a1 = 0.0360, 0.0565
    base = lambda a: 0.0172
    prof = fillet_profile([(a0, 0.0150), (a0, 0.0166), (a0 + 0.0010, 0.0174), (a1 - 0.0010, 0.0174), (a1, 0.0166), (a1, 0.0150)],
                          [0, 0.0006, 0.0003, 0.0003, 0.0006, 0], 3)
    prof = [(a, s) for a, s in prof]
    # densify for knurl ramps
    P.append(rod_lathe('seat_locknut', M('alu_dark'), prof, nu=72, tile=(0.030, 0.030), mod=knurl(18, 0.040, a0 + 0.0006, a1 - 0.0006, 0.0006)))
    # tail ring (gold)
    pr = fillet_profile([(0.0565, 0.0150), (0.0565, 0.0158), (0.0615, 0.0156), (0.0620, 0.0150)], [0, 0.0005, 0.0005, 0], 3)
    P.append(rod_lathe('seat_tail', M('alu_gold'), pr, nu=44, tile=(0.03, 0.03)))

    # --- fore grip -------------------------------------------------------
    a0, a1 = 0.0620, 0.0750
    P.append(rod_lathe('eva_fore0', M('eva'), [(a, 0.01475 - 0.0003 * (a - a0) / (a1 - a0)) for a in np.linspace(a0, a1, 4)],
                       nu=44, tile=(0.032, 0.032)))
    a0, a1 = 0.0750, 0.1450
    base = lambda a: 0.01445 - 0.0026 * ((a - a0) / (a1 - a0)) ** 0.9 + 0.00035 * np.sin(np.pi * (a - a0) / (a1 - a0))
    P.append(rod_lathe('cork_fore', M('cork'), [(a, base(a)) for a in np.linspace(a0, a1, 12)], nu=48, tile=(0.030, 0.034)))
    a0, a1 = 0.1450, 0.1620
    P.append(rod_lathe('eva_fore1', M('eva'), [(a, 0.0120 - 0.0007 * (a - a0) / (a1 - a0)) for a in np.linspace(a0, a1, 4)],
                       nu=48, tile=(0.032, 0.032)))
    # winding check (gold anodised, flared) + trim thread wrap
    pr = fillet_profile([(0.1620, 0.0100), (0.1620, 0.0125), (0.1640, 0.0124), (0.1735, 0.0092), (0.1735, 0.0080)],
                        [0, 0.0006, 0.0004, 0.0004, 0], 4)
    P.append(rod_lathe('winding_check', M('alu_gold'), pr, nu=48, tile=(0.03, 0.03)))
    # decorative trim wrap (gold thread, epoxied) between check and blank
    a0, a1 = 0.1735, 0.1850
    rows = []
    for a in np.linspace(a0, a1, 10):
        t = (a - a0) / (a1 - a0)
        r = blank_r(a) + 0.0003 + (0.0085 - blank_r(a) - 0.0003) * (1 - smoothstep(t)) ** 1.0
        rows.append((a, r))
    P.append(thread_wrap('trim_wrap', rows, gold=True))
    return P


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def thread_wrap(name, rows_ar, gold=False, nu=14, v0=None):
    """thread wrap: rows_ar list of (y, r) around the (bent) blank"""
    rows_ar = list(rows_ar)
    # closing end rows tucked into the blank
    y0, y1 = rows_ar[0][0], rows_ar[-1][0]
    rows = []
    arc = 0.0
    last = None
    for y, r in rows_ar:
        if last is not None:
            arc += np.hypot(y - last[0], r - last[1])
        last = (y, r)
        rows.append((y, r, arc))
    rows = np.array(rows)
    pitch_v = 39.0                       # v per metre  (6 px of 512 per 0.3 mm thread)
    base = 0.52 if gold else 0.02
    rows[:, 2] = base + rows[:, 2] * pitch_v
    return skin(name, M('thread'), BLANK, rows, cyl_outline(nu), u_rep=1.0)


def build_blank():
    P = []
    # label zone (non-tiled UV 512x2048) -----------------------------------
    ys = np.linspace(BEND_Y0, LABEL_END, 16)
    rows = np.array([(y, blank_r(y), (y - BEND_Y0) / (LABEL_END - BEND_Y0)) for y in ys])
    rows[0, 1] = blank_r(ys[0])
    P.append(skin('blank_label', M('label'), BLANK, rows, cyl_outline(28), u_rep=1.0))
    # tiled carbon (twill) zone: v = integral dy/(2 pi r)  => square weave cells all the way
    ys = np.concatenate([np.linspace(LABEL_END, 0.84, 14), np.linspace(0.84, 0.96, 6)[1:], np.linspace(0.96, 1.60, 34)[1:],
                         np.linspace(1.60, TIP_Y - 0.0005, 8)[1:]])
    rr = np.array([blank_r(y) for y in ys])
    dv = np.diff(ys) / (TAU * 0.5 * (rr[1:] + rr[:-1]))
    v = np.r_[0, np.cumsum(dv)]
    rows = np.column_stack([ys, rr, v])
    P.append(skin('blank_tiled', M('carbon'), BLANK, rows, cyl_outline(28), u_rep=1.0))
    # ferrule sleeve (female ferrule, slightly thicker, gloss) --------------
    f0, f1 = FERRULE
    ys = np.linspace(f0, f1, 14)
    prof = []
    for y in ys:
        t = (y - f0) / (f1 - f0)
        step = 0.0006 * smoothstep(t / 0.12) * (1 - 0.0) * smoothstep((1 - t) / 0.12) + 0.00012
        prof.append((y, blank_r(y) + step))
    rr = np.array([p[1] for p in prof])
    dv = np.diff(ys) / (TAU * 0.5 * (rr[1:] + rr[:-1]))
    v = 90.0 + np.r_[0, np.cumsum(dv)]
    rows = np.column_stack([ys, rr, v])
    P.append(skin('ferrule', M('carbon'), BLANK, rows, cyl_outline(28), u_rep=1.0))
    # gold trim wraps at both ends of the ferrule
    for yc in (f0 + 0.0030, f1 - 0.0030):
        rows_ar = []
        for y in np.linspace(yc - 0.0024, yc + 0.0024, 7):
            t = abs((y - yc) / 0.0024)
            rows_ar.append((y, blank_r(y) + 0.00075 - 0.0004 * smoothstep(t) ** 2 + 0.00012))
        P.append(thread_wrap('ferrule_trim', rows_ar, gold=True))
    return P


# ---------------------------------------------------------------------------
# GUIDES
# ---------------------------------------------------------------------------
GUIDES = [  # y, ring ID (mm), centre depth below blank axis (m), half foot spread (m)
    (0.400, 20.0, 0.0345, 0.0165),
    (0.575, 16.0, 0.0285, 0.0145),
    (0.745, 13.0, 0.0235, 0.0130),
    (0.995, 11.0, 0.0195, 0.0115),
    (1.165, 9.0, 0.0165, 0.0105),
    (1.305, 8.0, 0.0145, 0.0095),
    (1.425, 7.0, 0.0128, 0.0085),
    (1.515, 6.0, 0.0112, 0.0078),
    (1.585, 5.0, 0.0100, 0.0070),
]
TIPTOP_ID = 3.6e-3


def guide_ring_center(g):
    y, idmm, h, f = g
    C, T, up = rod_frame_at(y)
    return C - up * h, T, up


def bezier(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def build_guide(g, idx):
    y, idmm, h, f = g
    ID = idmm * 1e-3
    C, T, up = rod_frame_at(y)
    center = C - up * h
    P = []
    t_ins = 0.0021 if idmm > 8 else 0.0017
    nuk = 32 if idmm >= 13 else (24 if idmm >= 8 else 20)
    # ceramic insert (SiC) + stainless frame ring
    P.append(torus('g%d_insert' % idx, M('ceramic'), center, T, ID / 2 + t_ins / 2, 0.0012 + 0.00004 * idmm, t_ins / 2,
                   nu=nuk, nv=8, u_rep=4, v_rep=1, theta0=0.0, e1=up))
    Ro = ID / 2 + t_ins + 0.0006
    P.append(torus('g%d_ring' % idx, M('chrome'), center, T, Ro, 0.0011 + 0.00003 * idmm, 0.00068, nu=nuk, nv=6, u_rep=6, v_rep=1,
                   e1=up))
    # frame legs (double foot)
    top = center + up * (Ro - 0.0003)
    for sgn in (-1, 1):
        yf = y + sgn * (f + 0.0035)
        Cf, Tf, upf = rod_frame_at(yf)
        foot0 = Cf - upf * (blank_r(yf) + 0.00050)
        yf2 = y + sgn * (f - 0.0010)
        Cf2, Tf2, upf2 = rod_frame_at(yf2)
        foot1 = Cf2 - upf2 * (blank_r(yf2) + 0.00060)
        p0 = foot1
        p3 = top + T * sgn * 0.0006
        p1 = p0 - T * sgn * 0.45 * f                 # leaves the foot along the blank
        p2 = p3 + (foot1 - p3) * 0.55                # arrives at the ring from the foot side
        path_curve = bezier(p0, p1, p2, p3, 12)
        flat = [foot0 + (foot1 - foot0) * k for k in (0.0, 0.5)]
        path = np.vstack([flat[0], flat[1], path_curve])
        # remove duplicate points
        keep = [0]
        for i in range(1, len(path)):
            if np.linalg.norm(path[i] - path[keep[-1]]) > 2e-4:
                keep.append(i)
        path = path[keep]
        rad = np.linspace(0.00085, 0.00072, len(path))
        P.append(tube('g%d_leg%d' % (idx, sgn), M('chrome'), path, rad, nseg=6, cap0=True, cap1=False, ncap=2,
                      u_rep=1, v_per_m=40.0, elliptic=(1.0, 1.0)))
        # thread wrap covering the foot
        rows_ar = []
        yc = y + sgn * (f - 0.0003)
        hw = 0.0052
        for yy in np.linspace(yc - hw, yc + hw, 7):
            tt = abs((yy - yc) / hw)
            r = blank_r(yy) + 0.00020 + (0.00115 - 0.00020) * (1 - smoothstep((tt - 0.55) / 0.45))
            rows_ar.append((yy, r))
        P.append(thread_wrap('g%d_wrap%d' % (idx, sgn), rows_ar, gold=False))
    return P


def build_tiptop():
    P = []
    y0, y1 = TIP_Y - 0.0125, TIP_Y + 0.0020
    ys = np.linspace(y0, y1, 8)
    rows = []
    for y in ys:
        rows.append((y, blank_r(min(y, TIP_Y)) + 0.00085))
    path = np.array([rod_path(min(y, TIP_Y)) + (np.array([0, y - min(y, TIP_Y), 0])) for y in ys])
    rows_ar = [(y, blank_r(min(y, TIP_Y)) + 0.00085) for y in ys]
    # tube along the blank axis, rounded end
    P.append(tube('tip_tube', M('chrome'), path, np.array([r for _, r in rows_ar]), nseg=12, cap0=False, cap1=True, ncap=3,
                  u_rep=1, v_per_m=40))
    C, T, up = rod_frame_at(TIP_Y)
    ring_c = C + T * 0.0034 - up * 0.0050
    ID = TIPTOP_ID
    P.append(torus('tt_insert', M('ceramic'), ring_c, T, ID / 2 + 0.0008, 0.0011, 0.0008, nu=24, nv=8, theta0=0, e1=up))
    Ro = ID / 2 + 0.0016 + 0.0004
    P.append(torus('tt_ring', M('chrome'), ring_c, T, Ro, 0.0009, 0.00055, nu=24, nv=8, e1=up))
    # bridge from tube to ring
    p0 = C + T * (0.0004) - up * 0.0012
    p3 = ring_c + up * (Ro - 0.0002)
    path = bezier(p0, p0 + T * 0.0012, p3 - T * 0.0012 + up * 0.0008, p3, 8)
    P.append(tube('tt_bridge', M('chrome'), path, 0.00060, nseg=8, cap0=False, cap1=False, ncap=1, u_rep=1, v_per_m=40))
    return P, ring_c


def tip_ring_center():
    C, T, up = rod_frame_at(TIP_Y)
    return C + T * 0.0034 - up * 0.0050


# ---------------------------------------------------------------------------
# REEL (3000 size spinning reel)
# ---------------------------------------------------------------------------
HOUSING_W = 0.0225            # half width (x)
HOUSING_Y = -0.0165           # outline centre y (relative to reel origin)
HOUSING_A, HOUSING_B = 0.0475, 0.0345   # y/z semi axes
HANDLE_AX = (-0.022, 0.002)   # (y,z) of crank shaft relative to REEL_O
FOOT_Y = (-0.0345, 0.0215)

def yz_frame(x0, sign=-1.0):
    """frame whose axis runs along sign*X; outline (x,y) = world (Y,Z)."""
    return AxisFrame((x0, 0, 0), (sign, 0, 0), (0, 1, 0))


def planar_plate_uv(side, y0, y1, z0, z1):
    def f(P):
        u = (P[..., 1] - y0) / (y1 - y0)
        v = (z1 - P[..., 2]) / (z1 - z0)
        if side < 0:
            u = 1 - u
        return np.stack([u, v], -1)
    return f


def build_reel_body():
    O = REEL_O
    P = []
    # --- housing (painted metal) : superellipse loft with bevelled flat sides
    out = superellipse_outline(72, HOUSING_A, HOUSING_B, 2.6)
    # flatten the lower rear a little so the body reads as a "teardrop"
    out[:, 1] = np.where(out[:, 1] < 0, out[:, 1] * 0.94, out[:, 1])
    fr = AxisFrame((0.0, O[1] + HOUSING_Y, O[2]), (-1, 0, 0), (0, 1, 0))
    rows = slab_rows(HOUSING_W, 0.20, 0.0075, 5)
    rows[:, 1] = rows[:, 1]                       # s relative to outline
    # scale the rows to be unit outline fractions
    P.append(skin('housing', M('paint'), fr, rows, out / 1.0, u_rep=3, v_scale=1.0))
    # --- side plates (raised 0.35mm, text/engraving texture)
    plate_s = 0.80
    y_c = O[1] + HOUSING_Y
    y0, y1 = y_c - HOUSING_A * plate_s, y_c + HOUSING_A * plate_s
    z0, z1 = O[2] - HOUSING_B * plate_s * 0.94, O[2] + HOUSING_B * plate_s
    for side in (+1, -1):
        sign = -1.0 if side < 0 else 1.0
        # frame axis along side*X ... outward travel
        frp = AxisFrame((0.0, y_c, O[2]), (side * 1.0, 0, 0), (0, 1, 0))
        base = HOUSING_W - 0.0004
        rows = np.array([(base + 0.0000, plate_s * 1.0, 0), (base + 0.00045, plate_s * 0.995, 0), (base + 0.00060, plate_s * 0.975, 0),
                         (base + 0.00060, plate_s * 0.6, 0), (base + 0.00060, 0.0, 0)])
        # rows go rim->centre with a increasing outward: orientation resolved automatically
        # the outline of the plate is the housing outline mirrored for side==-1 (e2 = +Z for both)
        outl = out.copy()
        if side > 0:
            outl[:, 0] = outl[:, 0]  # e1 = +Y, e2 = side*... resolved by frame
        P.append(skin('plate%+d' % side, M('plate'), frp, rows, outl, uv_fn=planar_plate_uv(side, y0, y1, z0, z1)))
    # --- bearing collar at the front of the housing (where the rotor meets it)
    pr = fillet_profile([(0.0255, 0.0), (0.0255, 0.0200), (0.0345, 0.0200), (0.0345, 0.0)], [0, 0.0006, 0.0006, 0], 3)
    P.append(lathe('collar', M('alu_dark'), O, (0, 1, 0), (1, 0, 0), pr, nu=48, tile=(0.03, 0.03)))

    # --- reel foot (curved shell around the seat tube) + stem
    P += sector_solid('foot', M('alu_dark'), ROD, FOOT_Y[0], FOOT_Y[1],
                      lambda a: 0.0157, lambda a: 0.0187, 1.5 * np.pi,
                      lambda a: 0.95 - 0.35 * smoothstep((abs(a - 0.5 * (FOOT_Y[0] + FOOT_Y[1])) - 0.020) / 0.008),
                      na=12, nt=16, uv_scale=(1.2, 1.9))
    stem_top = -0.0180
    stem_bot = O[2] + HOUSING_B * 0.78
    P.append(rbox('stem', M('alu_dark'), (0.0, -0.0075, 0.5 * (stem_top + stem_bot)),
                  (0.0175, 0.0300, stem_top - stem_bot), bevel=0.0040, p=3.2, n=32))
    # stem collar bolt (chrome allen-style) on both sides
    for sx in (-1, 1):
        P.append(lathe('stem_bolt', M('chrome'), (sx * 0.0087, -0.0075, -0.0340), (sx, 0, 0), (0, 1, 0),
                       [(0.0, 0.0), (0.0, 0.0030), (0.0006, 0.0034), (0.0014, 0.0034), (0.0017, 0.0028), (0.0017, 0.0)],
                       nu=24, tile=(0.01, 0.01), outline=star_outline(24, 6, 0.18)))

    # --- crank assembly on the -X side ---------------------------------------
    hy, hz = O[1] + HANDLE_AX[0], O[2] + HANDLE_AX[1]
    # boss behind the arm
    P.append(lathe('crank_boss', M('alu_dark'), (-HOUSING_W, hy, hz), (-1, 0, 0), (0, 1, 0),
                   [(0.0, 0.0), (0.0, 0.0112), (0.0020, 0.0112), (0.0030, 0.0100), (0.0030, 0.0)], nu=48, tile=(0.03, 0.03)))
    # crank arm : hull of two circles, tapered, flat with bevel
    knob = np.array([hy - 0.0125, hz - 0.0620])
    outl = hull_outline((0.0, 0.0), 0.0098, (knob[0] - hy, knob[1] - hz), 0.0070, 28)
    cen = outl[:-1].mean(axis=0)
    # centre at the centroid so the 's' scaling is a uniform inset
    fr = AxisFrame((-HOUSING_W - 0.0030 - 0.0018, hy + cen[0], hz + cen[1]), (-1, 0, 0), (0, 1, 0))
    rows = slab_rows(0.0018, 0.10, 0.0010, 3)
    P.append(skin('crank_arm', M('alu_dark'), fr, rows, outl - cen, u_rep=3))
    # hub cap (6-lobe torx style)
    P.append(lathe('crank_cap', M('chrome'), (-HOUSING_W - 0.0030 - 0.0036, hy, hz), (-1, 0, 0), (0, 1, 0),
                   [(0.0, 0.0), (0.0, 0.0072), (0.0009, 0.0074), (0.0030, 0.0070), (0.0036, 0.0052), (0.0036, 0.0)],
                   nu=48, tile=(0.02, 0.02), outline=star_outline(48, 6, 0.10)))
    # arm pivot / knob mounting
    kx0 = -HOUSING_W - 0.0030 - 0.0036       # outer face of the arm
    kprof = [(0.0, 0.0), (0.0, 0.0068), (0.0010, 0.0068), (0.0010, 0.0046), (0.0030, 0.0046), (0.0030, 0.0050)]
    P.append(lathe('knob_washer', M('chrome'), (kx0 + 0.0036, knob[0], knob[1]), (-1, 0, 0), (0, 1, 0), kprof, nu=32, tile=(0.02, 0.02)))
    # power knob (soft rubber), long barrel with rounded ends
    a0 = 0.0030
    pk = [(a0, 0.0050), (a0, 0.0075)]
    kb = fillet_profile([(a0, 0.0050), (a0 + 0.0003, 0.0072), (a0 + 0.0040, 0.0090), (a0 + 0.0150, 0.0098), (a0 + 0.0250, 0.0090),
                         (a0 + 0.0285, 0.0075), (a0 + 0.0295, 0.0045)], [0, 0.0012, 0.0, 0.0, 0.0, 0.0030, 0], 4)
    P.append(lathe('knob', M('rubber'), (kx0 + 0.0036, knob[0], knob[1]), (-1, 0, 0), (0, 1, 0), kb, nu=40, tile=(0.020, 0.020)))
    # knob end cap with torx screw
    ec = a0 + 0.0295
    P.append(lathe('knob_cap', M('alu_gold'), (kx0 + 0.0036, knob[0], knob[1]), (-1, 0, 0), (0, 1, 0),
                   fillet_profile([(ec - 0.0012, 0.0052), (ec - 0.0012, 0.0062), (ec + 0.0010, 0.0058), (ec + 0.0013, 0.0)], [0, 0.0004, 0.0003, 0], 3),
                   nu=36, tile=(0.02, 0.02)))
    # --- torx screws on both plates
    for side in (+1, -1):
        for k, ang in enumerate([35, 150, 215, 325, 270]):
            th = np.deg2rad(ang)
            r_sc = 0.80 * 0.915 if k == 4 else 0.915 * 0.97
            py = y_c + np.cos(th) * HOUSING_A * 0.885 * (0.62 if k == 4 else 1.0) * r_sc / 0.915
            pz = O[2] + np.sin(th) * HOUSING_B * 0.885 * (0.62 if k == 4 else 1.0) * r_sc / 0.915 * (0.94 if th > np.pi else 1.0)
            if k == 4:
                py, pz = y_c + 0.0, O[2] - HOUSING_B * 0.60
            P.append(lathe('screw', M('chrome'), (side * (HOUSING_W + 0.00060), py, pz), (side, 0, 0), (0, 1, 0),
                           [(0.0, 0.0), (0.0, 0.0021), (0.0003, 0.0023), (0.0010, 0.0020), (0.0011, 0.0)],
                           nu=18, tile=(0.01, 0.01), outline=star_outline(18, 6, 0.28)))
    # --- anti-reverse switch (plastic) at the rear-bottom
    P.append(rbox('ar_switch', M('plastic'), (0.0050, O[1] - 0.0655, O[2] - 0.0165), (0.0135, 0.0075, 0.0060), bevel=0.0016, p=4, n=24))
    P.append(rbox('ar_switch_base', M('alu_dark'), (0.0, O[1] - 0.0640, O[2] - 0.0165), (0.0290, 0.0030, 0.0095), bevel=0.0010, p=4, n=24))
    return P


def build_reel_rotor():
    O = REEL_O
    P = []
    ax = (0, 1, 0)
    e1 = (1, 0, 0)
    fr = AxisFrame(O, ax, e1)         # theta from +X towards +Z (e2 = e1 x t = +Z)
    # --- rotor back wall + hub
    pr = fillet_profile([(0.0300, 0.0), (0.0300, 0.0330), (0.0312, 0.0345), (0.0372, 0.0345), (0.0372, 0.0100), (0.0400, 0.0100), (0.0400, 0.0)],
                        [0, 0.0010, 0.0005, 0, 0.0003, 0, 0], 3)
    P.append(lathe('rotor_wall', M('alu_dark'), O, ax, e1, pr, nu=56, tile=(0.03, 0.03), theta0=0.0))
    # --- rotor arms (top/bottom) : two real sector solids with tapering width
    for k, thc in enumerate((0.5 * np.pi, 1.5 * np.pi)):
        P += sector_solid('rotor_arm%d' % k, M('alu_dark'), fr, 0.0340, 0.0905,
                          lambda a: 0.0318, lambda a: 0.0346 + 0.0004 * (a - 0.034) / 0.0565, thc,
                          lambda a: 0.66 - 0.30 * smoothstep((a - 0.040) / 0.050), na=16, nt=18, uv_scale=(1.4, 2.0))
        # bail mount block on the arm tip
        sgn = 1 if k == 0 else -1
        P.append(rbox('bail_mount%d' % k, M('chrome'), (0.0, O[1] + 0.0895, O[2] + sgn * 0.0352), (0.0105, 0.0075, 0.0052),
                      bevel=0.0015, p=4, n=24))
    # --- spool ------------------------------------------------------------
    # rear skirt + flange (gold anodised, turned)
    pr = fillet_profile([(0.0400, 0.0), (0.0400, 0.0262), (0.0415, 0.0270), (0.0462, 0.0270), (0.0462, 0.0285), (0.0505, 0.0285), (0.0505, 0.0250)],
                        [0, 0.0008, 0.0003, 0, 0.0005, 0.0004, 0], 3)
    P.append(lathe('spool_rear', M('alu_gold'), O, ax, e1, pr, nu=72, tile=(0.030, 0.030)))
    # wound line (separate material with winding texture)
    pr = [(0.0502, 0.0256), (0.0506, 0.0261), (0.0522, 0.0262), (0.0814, 0.0262), (0.0830, 0.0261), (0.0834, 0.0256)]
    P.append(lathe('spool_line', M('linewound'), O, ax, e1, pr, nu=72, tile=(0.022, 0.022), caps=False, u_rep=8))
    # front lip + dished face
    pr = fillet_profile([(0.0832, 0.0250), (0.0832, 0.0290), (0.0852, 0.0299), (0.0872, 0.0296), (0.0906, 0.0150), (0.0906, 0.0)],
                        [0, 0.0006, 0.0010, 0.0004, 0.0005, 0], 4)
    P.append(lathe('spool_lip', M('alu_gold'), O, ax, e1, pr, nu=72, tile=(0.030, 0.030)))
    # drag knob : knurled body + gold cap
    a0, a1 = 0.0906, 0.1040
    pr = fillet_profile([(a0, 0.0100), (a0, 0.0140), (a0 + 0.0014, 0.0146), (a1 - 0.0010, 0.0146), (a1, 0.0136), (a1, 0.0098)],
                        [0, 0.0006, 0.0003, 0.0003, 0.0007, 0], 3)
    P.append(lathe('drag_knob', M('alu_dark'), O, ax, e1, pr, nu=96, tile=(0.03, 0.03),
                   mod=knurl(24, 0.050, a0 + 0.0011, a1 - 0.0010, 0.0006)))
    pr = fillet_profile([(a1 - 0.0004, 0.0), (a1 - 0.0004, 0.0100), (a1 + 0.0005, 0.0098), (a1 + 0.0014, 0.0075), (a1 + 0.0018, 0.0)],
                        [0, 0.0003, 0.0003, 0.0003, 0], 3)
    P.append(lathe('drag_cap', M('alu_gold'), O, ax, e1, pr, nu=48, tile=(0.02, 0.02)))
    # --- bail wire : superellipse arc in the YZ plane (top mount -> over the spool -> bottom mount)
    ph = np.linspace(0, np.pi, 40)
    zr = 0.0352 - 0.0
    yr = 0.0215
    c, s = np.cos(ph), np.sin(ph)
    wy = O[1] + 0.0895 + yr * np.abs(s) ** (2 / 2.5)
    wz = O[2] + zr * np.sign(c) * np.abs(c) ** (2 / 2.5)
    wire = np.stack([np.zeros_like(wy), wy, wz], -1)
    P.append(tube('bail_wire', M('chrome'), wire, 0.00175, nseg=14, cap0=True, cap1=True, ncap=3, u_rep=1, v_per_m=40))
    # --- line roller assembly (top mount)
    ry, rz = O[1] + 0.0895, O[2] + 0.0352 + 0.0050
    P.append(rbox('roller_bracket', M('chrome'), (0.0, ry - 0.0002, O[2] + 0.0352 + 0.0020), (0.0100, 0.0070, 0.0040), bevel=0.0012, p=4, n=24))
    for sx in (-1, 1):
        P.append(rbox('roller_ear', M('chrome'), (sx * 0.00485, ry, rz - 0.0005), (0.0016, 0.0060, 0.0100), bevel=0.0006, p=4, n=20))
    P.append(lathe('roller', M('alu_gold'), (-0.0043, ry, rz), (1, 0, 0), (0, 1, 0),
                   fillet_profile([(0.0, 0.0), (0.0, 0.0036), (0.0006, 0.0036), (0.0008, 0.0030), (0.0078, 0.0030), (0.0080, 0.0036), (0.0086, 0.0036), (0.0086, 0.0)],
                                  [0, 0.0004, 0, 0, 0, 0, 0.0004, 0], 2), nu=32, tile=(0.02, 0.02)))
    P.append(lathe('roller_axle', M('chrome'), (-0.0056, ry, rz), (1, 0, 0), (0, 1, 0),
                   [(0.0, 0.0), (0.0, 0.0008), (0.0112, 0.0008), (0.0112, 0.0)], nu=12, tile=(0.01, 0.01)))
    # --- line clip on the spool lip (plastic)
    P.append(rbox('line_clip', M('plastic'), (0.0, O[1] + 0.0860, O[2] - 0.0300), (0.0105, 0.0050, 0.0042), bevel=0.0012, p=4, n=24))
    return P


def line_points():
    O = REEL_O
    pts = [np.array([0.0, O[1] + 0.0700, O[2] + 0.0262 + LINE_R]),
           np.array([0.0, O[1] + 0.0850, O[2] + 0.0262 + LINE_R + 0.0033]),
           np.array([0.0, O[1] + 0.0872, O[2] + 0.0296 + LINE_R + 0.0004]),
           np.array([0.0, O[1] + 0.0895, O[2] + 0.0352 + 0.0050 + 0.0030 + LINE_R])]
    for g in GUIDES:
        c, T, up = guide_ring_center(g)
        pts.append(c)
    pts.append(tip_ring_center())
    return np.array(pts)


def build_line():
    pts = line_points()
    return [tube('line', M('line'), pts, LINE_R, nseg=5, cap0=True, cap1=True, ncap=1, u_rep=1, v_per_m=50.0)]


# ---------------------------------------------------------------------------
def build_all():
    rod = []
    rod += build_handle()
    rod += build_blank()
    for i, g in enumerate(GUIDES):
        rod += build_guide(g, i)
    tt, _ = build_tiptop()
    rod += tt
    body = build_reel_body()
    rotor = build_reel_rotor()
    line = build_line()
    return {'fr_rod': rod, 'fr_reel_body': body, 'fr_reel_rotor': rotor, 'fr_line': line}
