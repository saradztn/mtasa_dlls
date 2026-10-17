"""Metre-space centreline; flat over playable decks, C1-continuous sag in the free span."""
import math
EXTENT=20.0
GAP_HALF=14.0
HEIGHT=1.05
SAG=.16
def height(x):
    return HEIGHT-SAG*math.cos(math.pi*x/(2*GAP_HALF))**2 if abs(x)<GAP_HALF else HEIGHT
