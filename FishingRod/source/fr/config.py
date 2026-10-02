# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# Export orientation, baked into the exported DFF vertices/normals/frames and into the COL.
# (Baking is required because GTA replaces the frame of a held weapon with the hand bone's.)
#
# Authoring pose: +X right, +Y tip, +Z up (reel hangs on -Z).
# Step 1  ROT_Z_DEG = 90  (requested: rotation Z 90; GTA convention, counter-clockwise from above).
# Step 2  HAND_FIT: measured from an in-game screenshot of the step-1 export held as weapon 10 / model 321:
#         the rod stood vertically (tip up) with the reel behind the player.  The hand frame therefore maps
#         model (x, y, z) -> game (-up, -right, +forward).  HAND_FIT turns the rod so that, in the hand, the tip
#         points forward and 45 degrees up and the reel hangs underneath, like a rod held while fishing.
import numpy as np

ROT_Z_DEG = 90.0
_s = np.sqrt(0.5)
HAND_FIT = np.array([[_s, 0, -_s], [0, -1, 0], [-_s, 0, -_s]], np.float64)


def rot_z(deg=ROT_Z_DEG):
    a = np.radians(deg)
    c, s = round(float(np.cos(a)), 12), round(float(np.sin(a)), 12)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)


def export_rot():
    """authoring vector -> exported (model-space) vector"""
    return HAND_FIT @ rot_z()
