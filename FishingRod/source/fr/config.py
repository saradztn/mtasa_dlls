# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# Export orientation.  The model is authored with +Y towards the tip; ROT_Z_DEG is baked into the exported
# DFF vertices/normals/frames and into the COL (GTA convention: positive = counter-clockwise seen from above,
# +90 turns +Y (tip) into -X).  Baking is required because GTA replaces the frame of a held weapon.
import numpy as np

ROT_Z_DEG = 90.0


def rot_z(deg=None):
    a = np.radians(ROT_Z_DEG if deg is None else deg)
    c, s = round(float(np.cos(a)), 12), round(float(np.sin(a)), 12)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)
