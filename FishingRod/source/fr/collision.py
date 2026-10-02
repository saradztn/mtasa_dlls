# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# collision.py - simplified collision proxy for the fishing rod (COL3).
#   * handle + reel seat : chain of overlapping spheres following the real radius profile
#   * rod blank          : 20 short AABBs that follow the bend (min. half-thickness 5 mm)
#   * reel               : housing box, rotor/spool box, stem box, crank arm box, knob box
# Spheres/boxes use float coordinates (a mesh would be quantised to 1/128 m = 7.8 mm,
# which is far too coarse for a 12 mm blank), so the proxy is exact where it matters.
# -----------------------------------------------------------------------------
import numpy as np
from . import model as md

SURF = 0   # default surface material


def handle_radius(y):
    ys = [-0.300, -0.290, -0.225, -0.112, -0.0785, -0.044, 0.056, 0.062, 0.075, 0.145, 0.162, 0.173]
    rs = [0.0125, 0.0148, 0.0160, 0.0160, 0.0150, 0.0178, 0.0182, 0.0155, 0.0152, 0.0120, 0.0128, 0.0100]
    return float(np.interp(y, ys, rs))


def build_shapes():
    spheres = []
    y = md.BUTT_Y + 0.0125
    while y < 0.172:
        r = handle_radius(y)
        spheres.append((0.0, y, 0.0, r, SURF))
        y += max(0.012, r * 0.9)
    boxes = []
    O = md.REEL_O
    # blank: 20 AABBs along the curve
    ys = np.linspace(0.165, md.TIP_Y + 0.004, 21)
    for a, b in zip(ys[:-1], ys[1:]):
        pts = np.array([md.rod_path(v) for v in np.linspace(a, b, 6)])
        r = max(md.blank_r(a) + 0.0025, 0.005)
        lo = np.array([-r, a, pts[:, 2].min() - r])
        hi = np.array([r, b, pts[:, 2].max() + r])
        boxes.append((tuple(lo), tuple(hi), SURF))
    # reel housing / foot / rotor / crank
    boxes.append(((-0.0225, O[1] - 0.0640, O[2] - 0.0345), (0.0225, O[1] + 0.0310, O[2] + 0.0345), SURF))
    boxes.append(((-0.0345, O[1] + 0.0310, O[2] - 0.0360), (0.0345, O[1] + 0.1040, O[2] + 0.0420), SURF))   # rotor, spool, bail
    boxes.append(((-0.0090, -0.0225, O[2] + 0.0300), (0.0090, 0.0075, -0.0170), SURF))                      # stem + foot
    boxes.append(((-0.0335, O[1] - 0.0420, O[2] - 0.0720), (-0.0245, O[1] - 0.0100, O[2] + 0.0125), SURF))     # crank arm
    boxes.append(((-0.0640, O[1] - 0.0480, O[2] - 0.0720), (-0.0300, O[1] - 0.0235, O[2] - 0.0525), SURF))     # power knob
    return spheres, boxes
