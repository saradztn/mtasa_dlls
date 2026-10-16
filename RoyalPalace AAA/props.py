"""Parametric furniture / decoration library. Each prop is built at the origin facing +y
(front) and returns a Prop with mesh, collision boxes, baked-light sources and flame
coronas. Original geometry - no external assets."""
from __future__ import annotations
import math
import numpy as np
from fortlib import Mesh, Collision


class Prop:
    def __init__(self):
        self.m = Mesh(); self.c = Collision(); self.lights = []; self.flames = []

    def box(self, lo, hi, tex, col=True, uv=1.0, faces='xXyYzZ', surf='wood'):
        self.m.box(lo, hi, tex, uv, faces=faces)
        if col: self.c.box(lo, hi, surf)

    def flame(self, p, size=.25, color=(255, 170, 90), light=True, power=1.0, radius=7.0):
        x, y, z = p
        self.m.poly([(x - size * .3, y, z), (x + size * .3, y, z), (x + size * .3, y, z + size), (x - size * .3, y, z + size)], 'rf_fire', [(0, 1), (1, 1), (1, 0), (0, 0)], two_sided=True)
        self.m.poly([(x, y - size * .3, z), (x, y + size * .3, z), (x, y + size * .3, z + size), (x, y - size * .3, z + size)], 'rf_fire', [(0, 1), (1, 1), (1, 0), (0, 0)], two_sided=True)
        self.flames.append({'pos': [x, y, z + size * .5], 'size': size, 'color': list(color)})
        if light: self.lights.append({'pos': [x, y, z + size * .6], 'color': [c / 255 * .9 for c in color], 'radius': radius, 'power': power})


def table(w=2.0, d=1.0, h=.78, tex='rf_wood', cloth=None):
    p = Prop(); t = .08
    p.box((-w / 2, -d / 2, h - t), (w / 2, d / 2, h), tex, col=False, uv=2.5)
    if cloth:
        p.m.box((-w / 2 - .03, -d / 2 - .03, h - .3), (w / 2 + .03, d / 2 + .03, h + .005), cloth, 2.0, faces='xXyYZ')
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((sx * (w / 2 - .12) - .05, sy * (d / 2 - .12) - .05, 0), (sx * (w / 2 - .12) + .05, sy * (d / 2 - .12) + .05, h - t), tex, col=False, faces='xXyY')
    p.c.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), 'wood')
    return p


def chair(tex='rf_wood', fabric='rf_fabricred', high=False):
    p = Prop(); s = .46; h = .46
    p.box((-.24, -.24, h - .06), (.24, .24, h), tex, col=False)
    p.m.box((-.22, -.22, h), (.22, .22, h + .05), fabric, 1, faces='xXyYZ')
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.m.box((sx * .2 - .025, sy * .2 - .025, 0), (sx * .2 + .025, sy * .2 + .025, h - .06), tex, 1, faces='xXyY')
    bh = 1.5 if high else 1.05
    p.m.box((-.24, -.26, h), (.24, -.2, bh), tex, 1)
    p.m.box((-.2, -.2, h + .25), (.2, -.19, bh - .08), fabric, 1, faces='Y')
    p.c.box((-.25, -.27, 0), (.25, .25, h + .05), 'wood')
    return p


def bench(w=2.0, tex='rf_wood', cushion=None):
    p = Prop()
    p.box((-w / 2, -.22, .42), (w / 2, .22, .48), tex, col=False)
    if cushion: p.m.box((-w / 2 + .05, -.2, .48), (w / 2 - .05, .2, .54), cushion, 1, faces='xXyYZ')
    for sx in (-1, 1): p.m.box((sx * (w / 2 - .15) - .05, -.18, 0), (sx * (w / 2 - .15) + .05, .18, .42), tex, 1, faces='xXyY')
    p.c.box((-w / 2, -.22, 0), (w / 2, .22, .5), 'wood')
    return p


def throne():
    p = Prop()
    p.box((-.8, -.6, 0), (.8, .5, .55), 'rf_gold', col=False)
    p.m.box((-.6, -.4, .55), (.6, .45, .68), 'rf_fabricblue', 1, faces='xXyYZ')
    p.m.box((-.8, -.75, .55), (.8, -.5, 2.6), 'rf_gold', 1)
    p.m.box((-.55, -.5, .9), (.55, -.49, 2.3), 'rf_fabricblue', 1, faces='Y')
    for sx in (-1, 1):
        p.m.box((sx * .8 - .14, -.5, .55), (sx * .8 + .02 * sx, .5, 1.05), 'rf_gold', 1)
        p.m.sphere((sx * .72, .45, 1.12), .1, 'rf_gold', 6, 4)
    p.m.cyl((0, -.62, 2.6), .25, .55, 'rf_gold', 6, r2=0.0)
    p.m.sphere((0, -.62, 3.2), .1, 'rf_gold', 6, 4)
    p.c.box((-.95, -.8, 0), (.95, .55, 1.0), 'metal'); p.c.box((-.8, -.78, 1.0), (.8, -.5, 2.6), 'metal')
    return p


def bed(w=2.0, l=2.3, fabric='rf_fabricred', canopy=True):
    p = Prop()
    p.box((-w / 2, -l / 2, .18), (w / 2, l / 2, .5), 'rf_wood', col=False)
    p.m.box((-w / 2 + .05, -l / 2 + .05, .5), (w / 2 - .05, l / 2 - .05, .72), 'rf_candle', 1, faces='xXyYZ')
    p.m.box((-w / 2 + .03, -l / 2 + .5, .72), (w / 2 - .03, l / 2 - .03, .78), fabric, 1.5, faces='xXyYZ')
    for sx in (-.3, .3): p.m.box((sx * w - .3, -l / 2 + .1, .72), (sx * w + .3, -l / 2 + .45, .9), 'rf_candle', 1)
    p.m.box((-w / 2, -l / 2 - .1, 0), (w / 2, -l / 2, 1.5), 'rf_wood', 2)
    if canopy:
        for sx in (-1, 1):
            for sy in (-1, 1):
                p.m.box((sx * w / 2 - .06, sy * l / 2 - .06, 0), (sx * w / 2 + .06, sy * l / 2 + .06, 2.6), 'rf_wood', 1, faces='xXyY')
        p.m.box((-w / 2 - .1, -l / 2 - .1, 2.6), (w / 2 + .1, l / 2 + .1, 2.8), fabric, 2)
        for sx in (-1, 1):
            p.m.poly([(sx * w / 2, -l / 2, .6), (sx * w / 2, -l / 2 + .7, .6), (sx * w / 2, -l / 2 + .7, 2.6), (sx * w / 2, -l / 2, 2.6)], fabric, two_sided=True)
            p.m.poly([(sx * w / 2, l / 2 - .7, .6), (sx * w / 2, l / 2, .6), (sx * w / 2, l / 2, 2.6), (sx * w / 2, l / 2 - .7, 2.6)], fabric, two_sided=True)
    p.c.box((-w / 2 - .06, -l / 2 - .1, 0), (w / 2 + .06, l / 2 + .06, .8), 'wood')
    return p


def wardrobe(w=1.6, h=2.4, d=.65, tex='rf_wood'):
    p = Prop()
    p.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), tex, uv=2.0)
    p.m.box((-w / 2 - .04, -d / 2 - .04, h), (w / 2 + .04, d / 2 + .04, h + .12), tex, 1)
    p.m.box((-.02, d / 2, .2), (.02, d / 2 + .01, h - .2), 'rf_iron', 1, faces='Y')
    for sx in (-1, 1): p.m.sphere((sx * .1, d / 2 + .03, h * .5), .035, 'rf_gold', 5, 3)
    return p


def chest(w=1.1, gold=False, tex='rf_wood'):
    p = Prop(); d = .6; h = .6
    p.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), tex, uv=1.5)
    for sx in (-1, 0, 1): p.m.box((sx * (w / 2 - .1) - .04, -d / 2 - .01, 0), (sx * (w / 2 - .1) + .04, d / 2 + .01, h + .01), 'rf_iron', 1, faces='xXyYZ')
    if gold:
        p.m.cyl((0, 0, h), w * .32, .25, 'rf_gold', 8, r2=.05)
    return p


def bookshelf(w=2.0, h=3.0, d=.45):
    p = Prop()
    p.m.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), 'rf_wood', 2, faces='xXyZz')
    p.m.box((-w / 2 + .06, d / 2 - .02, .08), (w / 2 - .06, d / 2 + .005, h - .08), 'rf_books', 1, faces='Y')
    m = p.m; k = len(m.uv) - 4
    m.uv[k:k + 4] = [(0, 0), (w / 2.4, 0), (w / 2.4, (h - .16) / 2.4), (0, (h - .16) / 2.4)]
    p.m.box((-w / 2 - .03, -d / 2, h), (w / 2 + .03, d / 2 + .05, h + .1), 'rf_wood', 1)
    p.c.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), 'wood')
    return p


def desk(w=1.6):
    p = table(w, .8, .78, 'rf_wood')
    p.m.box((-w / 2 + .05, -.35, .2), (-w / 2 + .45, .35, .7), 'rf_wood', 1)
    p.m.box((-.25, -.1, .78), (.15, .2, .8), 'rf_parchment', 1, faces='Z')
    p.m.cyl((.35, .1, .78), .04, .1, 'rf_iron', 6)
    p.m.box((.5, -.2, .78), (.75, .1, .86), 'rf_fabricred', 1)
    return p


def display_case(w=1.2, d=.7, h=1.0, item='rf_gold'):
    p = Prop()
    p.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), 'rf_wood', uv=1.5)
    p.m.box((-w / 2 + .02, -d / 2 + .02, h), (w / 2 - .02, d / 2 - .02, h + .6), 'rf_glass', 1.6, faces='xXyYZ')
    p.m.sphere((0, 0, h + .15), .13, item, 8, 5)
    p.m.box((-.25, -.12, h), (.25, .12, h + .05), 'rf_fabricred', 1)
    p.c.box((-w / 2, -d / 2, h), (w / 2, d / 2, h + .6), 'glass')
    return p


def chandelier(r=1.2, n=8, drop=2.0, gold=True):
    """Hanging ring chandelier; origin = ceiling attachment point (z=0), hangs down."""
    p = Prop(); tex = 'rf_gold' if gold else 'rf_iron'
    p.m.cyl((0, 0, -drop), .03, drop, 'rf_iron', 4, caps=False)
    for k in range(16):
        a0 = 2 * math.pi * k / 16; a1 = 2 * math.pi * (k + 1) / 16
        p.m.box((r * math.cos(a0) - .04, r * math.sin(a0) - .04, -drop - .06), (r * math.cos(a0) + .04, r * math.sin(a0) + .04, -drop + .02), tex, 1)
    for k in range(4):
        a = math.pi * k / 2
        p.m.poly([(0, 0, -drop + .6), (r * math.cos(a), r * math.sin(a), -drop), (r * math.cos(a), r * math.sin(a), -drop + .04)], tex, two_sided=True)
    p.m.sphere((0, 0, -drop - .15), .18, tex, 8, 4)
    for k in range(n):
        a = 2 * math.pi * k / n; x, y = r * math.cos(a), r * math.sin(a)
        p.m.cyl((x, y, -drop + .02), .035, .22, 'rf_candle', 5)
        p.flame((x, y, -drop + .24), .12, light=(k % 2 == 0), power=.75, radius=9.0)
    return p


def candelabra(h=1.6):
    p = Prop()
    p.m.cyl((0, 0, 0), .22, .08, 'rf_gold', 8, r2=.12); p.m.cyl((0, 0, .08), .04, h - .1, 'rf_gold', 6, caps=False)
    for dx in (-.25, 0, .25):
        p.m.box((dx - .03, -.03, h - .05), (dx + .03, .03, h), 'rf_gold', 1)
        p.m.cyl((dx, 0, h), .025, .18, 'rf_candle', 5); p.flame((dx, 0, h + .18), .1, light=dx == 0, power=.6, radius=6)
    p.c.box((-.2, -.2, 0), (.2, .2, h), 'metal')
    return p


def sconce(torch=True):
    """Wall torch; origin on the wall face, sticking out along +y."""
    p = Prop()
    p.m.box((-.08, 0, -.15), (.08, .05, .15), 'rf_iron', 1)
    p.m.poly([(0, .03, -.05), (0, .32, .15), (0, .32, .2), (0, .03, .0)], 'rf_iron', two_sided=True)
    p.m.cyl((0, .32, .1), .07, .2, 'rf_iron' if torch else 'rf_gold', 6, r2=.1)
    p.flame((0, .32, .3), .32, power=1.0, radius=8.5)
    return p


def fireplace(w=2.4, h=2.0):
    p = Prop(); d = .8
    p.box((-w / 2 - .4, -d / 2, 0), (-w / 2, d / 2, h), 'rf_stone', uv=3, surf='stone'); p.box((w / 2, -d / 2, 0), (w / 2 + .4, d / 2, h), 'rf_stone', uv=3, surf='stone')
    p.box((-w / 2 - .5, -d / 2, h), (w / 2 + .5, d / 2 + .15, h + .45), 'rf_stone', uv=3, surf='stone')
    p.m.box((-w / 2 - .6, -d / 2, h + .45), (w / 2 + .6, d / 2 + .25, h + .55), 'rf_stonedark', 2)
    p.m.box((-w / 2 + .01, -d / 2, 0), (w / 2 - .01, -d / 2 + .1, h), 'rf_dungeon', 2, faces='Y')
    p.m.box((-w / 2 + .01, -d / 2, .0), (w / 2 - .01, d / 2, .12), 'rf_stonedark', 2, faces='Z')
    for k in range(3): p.m.cyl((-.5 + k * .5, .0, .12), .09, .9, 'rf_bark', 6, caps=True)
    p.flame((-.25, .05, .2), .9, power=1.5, radius=10); p.flame((.3, -.05, .2), .7, light=False)
    p.c.box((-w / 2, -d / 2, 0), (w / 2, d / 2, .3), 'stone')
    return p


def rug(w, l, tex='rf_carpetred'):
    p = Prop()
    p.m.box((-w / 2, -l / 2, .0), (w / 2, l / 2, .025), tex, 3.0 if tex == 'rf_carpetblue' else 2.0, faces='xXyYZ')
    p.m.box((-w / 2 - .12, -l / 2 - .12, .0), (w / 2 + .12, l / 2 + .12, .018), 'rf_gold', 1, faces='xXyYZ')
    return p


def wall_hanging(w=1.6, h=3.2, tex='rf_banner'):
    """Banner on the wall (origin at wall, +y out), bottom at z=0."""
    p = Prop()
    p.m.poly([(-w / 2, .04, 0), (w / 2, .04, 0), (w / 2, .04, h), (-w / 2, .04, h)], tex, [(0, 0), (1, 0), (1, 1), (0, 1)])
    p.m.cyl((-w / 2 - .1, .07, h + .05), .03, .01, 'rf_gold', 4)
    p.m.box((-w / 2 - .12, .02, h), (w / 2 + .12, .09, h + .06), 'rf_gold', 1)
    return p


def painting(w=1.4, h=1.1, tex='rf_paint1'):
    p = Prop()
    p.m.box((-w / 2 - .1, 0, -.1), (w / 2 + .1, .06, h + .1), 'rf_gold', 1)
    p.m.poly([(-w / 2, .065, 0), (w / 2, .065, 0), (w / 2, .065, h), (-w / 2, .065, h)], tex, [(0, 0), (1, 0), (1, 1), (0, 1)])
    return p


def statue(tex='rf_whitemarble', scale=1.0, pedestal=1.0):
    """Stylised knight statue on a pedestal (original low-poly sculpture)."""
    p = Prop(); s = scale; z = pedestal
    p.box((-.55, -.55, 0), (.55, .55, z), 'rf_stone', uv=2, surf='stone')
    p.m.box((-.62, -.62, z - .08), (.62, .62, z), 'rf_stonedark', 1)
    for sx in (-1, 1): p.m.cyl((sx * .14 * s, 0, z), .1 * s, .85 * s, tex, 7, r2=.12 * s)
    p.m.cyl((0, 0, z + .85 * s), .26 * s, .75 * s, tex, 8, r2=.3 * s)
    p.m.sphere((0, 0, z + 1.75 * s), .15 * s, tex, 8, 5)
    p.m.cyl((0, 0, z + 1.6 * s), .2 * s, .15 * s, tex, 8, r2=.12 * s)
    for sx in (-1, 1): p.m.cyl((sx * .34 * s, .05, z + .95 * s), .07 * s, .6 * s, tex, 6, r2=.08 * s)
    p.m.box((.38 * s, .12, z + .1), (.42 * s, .16, z + 1.25 * s), tex, 1)
    p.m.box((.28 * s, .1, z + 1.0 * s), (.52 * s, .18, z + 1.05 * s), tex, 1)
    p.m.box((-.5 * s, .1, z + .6 * s), (-.3 * s, .14, z + 1.2 * s), tex, 1)
    p.c.box((-.55, -.55, z), (.55, .55, z + 1.9 * s), 'stone')
    return p


def column(r=.4, h=6.0, tex='rf_stone'):
    p = Prop()
    p.m.box((-r - .15, -r - .15, 0), (r + .15, r + .15, .35), 'rf_stonedark', 2)
    p.m.cyl((0, 0, .35), r, h - .75, tex, 12, caps=False, uvscale=4)
    p.m.cyl((0, 0, h - .4), r, .25, 'rf_stonedark', 12, caps=False, r2=r + .2)
    p.m.box((-r - .25, -r - .25, h - .15), (r + .25, r + .25, h), 'rf_stonedark', 2)
    p.c.box((-r, -r, 0), (r, r, h), 'stone')
    return p


def armor_stand():
    p = Prop()
    p.m.box((-.3, -.3, 0), (.3, .3, .08), 'rf_wood', 1)
    for sx in (-1, 1): p.m.cyl((sx * .12, 0, .08), .08, .82, 'rf_iron', 6, r2=.1)
    p.m.cyl((0, 0, .9), .25, .65, 'rf_iron', 8, r2=.3); p.m.sphere((0, 0, 1.75), .15, 'rf_iron', 8, 5)
    p.m.cyl((0, 0, 1.58), .12, .1, 'rf_iron', 6)
    for sx in (-1, 1): p.m.sphere((sx * .3, 0, 1.45), .12, 'rf_iron', 6, 4); p.m.cyl((sx * .33, .05, .95), .06, .5, 'rf_iron', 6)
    p.m.box((-.25, .25, .7), (.25, .3, 1.35), 'rf_banner', 1)
    p.c.box((-.32, -.3, 0), (.32, .32, 1.9), 'metal')
    return p


def weapon_rack(w=1.8):
    p = Prop()
    p.box((-w / 2, -.2, 0), (w / 2, .2, .12), 'rf_wood', col=False)
    p.m.box((-w / 2, -.05, 1.3), (w / 2, .05, 1.4), 'rf_wood', 1)
    for sx in (-1, 1): p.m.box((sx * w / 2 - .05, -.05, 0), (sx * w / 2 + .05, .05, 1.5), 'rf_wood', 1)
    n = int(w / .3)
    for k in range(n):
        x = -w / 2 + .15 + k * (w - .3) / max(1, n - 1)
        if k % 2 == 0:
            p.m.cyl((x, 0, .12), .025, 2.1, 'rf_wood', 4, caps=False); p.m.cyl((x, 0, 2.2), .05, .25, 'rf_iron', 4, r2=0)
        else:
            p.m.box((x - .03, -.01, .12), (x + .03, .01, 1.15), 'rf_iron', 1); p.m.box((x - .12, -.02, 1.15), (x + .12, .02, 1.2), 'rf_gold', 1)
    p.c.box((-w / 2, -.2, 0), (w / 2, .2, 2.0), 'wood')
    return p


def shield(r=.45, tex='rf_banner'):
    p = Prop()
    pts = [(r * math.cos(a), .05, r * math.sin(a) * 1.2) for a in [math.pi * k / 8 for k in range(17)]]
    p.m.poly([(0, .06, -r * 1.3)] + [(-r, .06, 0), (-r, .06, r), (r, .06, r), (r, .06, 0)], tex, [(.5, 0), (0, .45), (0, 1), (1, 1), (1, .45)])
    return p


def barrel(r=.42, h=1.0):
    p = Prop()
    p.m.cyl((0, 0, 0), r * .85, h / 2, 'rf_wood', 10, caps=True, r2=r)
    p.m.cyl((0, 0, h / 2), r, h / 2, 'rf_wood', 10, caps=True, r2=r * .85)
    for z in (.12, h - .15): p.m.cyl((0, 0, z), r * .92, .05, 'rf_iron', 10, caps=False)
    p.c.box((-r, -r, 0), (r, r, h), 'wood')
    return p


def crate(s=.9, tex='rf_woodlight'):
    p = Prop(); p.box((-s / 2, -s / 2, 0), (s / 2, s / 2, s), tex, uv=1.2)
    p.m.box((-s / 2 - .02, -s / 2 - .02, s * .45), (s / 2 + .02, s / 2 + .02, s * .55), 'rf_wood', 1, faces='xXyY')
    return p


def sack():
    p = Prop(); p.m.sphere((0, 0, .3), .32, 'rf_parchment', 7, 5, sz=1.1); p.c.box((-.3, -.3, 0), (.3, .3, .6), 'wood'); return p


def hearth(w=3.0):
    p = fireplace(w, 2.2)
    p.m.cyl((0, .0, 1.4), .45, .5, 'rf_iron', 10, r2=.38)
    p.m.box((-w / 2 + .1, -.05, 2.0), (w / 2 - .1, .05, 2.06), 'rf_iron', 1)
    return p


def oven():
    p = Prop()
    p.box((-1.2, -.9, 0), (1.2, .9, 1.0), 'rf_stone', uv=3, surf='stone')
    p.m.cyl((0, 0, 1.0), 1.1, 1.0, 'rf_stone', 12, r2=.5); p.m.box((-.35, .7, .9), (.35, .95, 1.5), 'rf_dungeon', 1)
    p.flame((0, .9, .95), .35, power=1.2, radius=7)
    p.c.box((-1.2, -.9, 1.0), (1.2, .9, 2.0), 'stone')
    return p


def cauldron(glow=False):
    p = Prop()
    p.m.cyl((0, 0, .15), .45, .55, 'rf_iron', 12, caps=True, r2=.55)
    p.m.cyl((0, 0, .7), .5, .02, 'rf_waterfx' if glow else 'rf_dungeon', 12, caps=True)
    for k in range(3):
        a = 2 * math.pi * k / 3; p.m.cyl((.4 * math.cos(a), .4 * math.sin(a), 0), .04, .2, 'rf_iron', 4)
    p.flame((0, 0, -.02), .4, color=(120, 255, 140) if glow else (255, 160, 80), power=1.0, radius=6)
    p.c.box((-.55, -.55, 0), (.55, .55, .75), 'metal')
    return p


def shelf_items(w=2.0, h=2.2, kind='jars'):
    p = Prop(); d = .45
    p.m.box((-w / 2, -d / 2, 0), (-w / 2 + .05, d / 2, h), 'rf_wood', 1); p.m.box((w / 2 - .05, -d / 2, 0), (w / 2, d / 2, h), 'rf_wood', 1)
    for k in range(4):
        z = .1 + k * (h - .2) / 3
        p.m.box((-w / 2, -d / 2, z), (w / 2, d / 2, z + .04), 'rf_wood', 1)
        if k == 3: continue
        for j in range(int(w / .3)):
            x = -w / 2 + .2 + j * .3
            if kind == 'jars': p.m.cyl((x, 0, z + .04), .08, .22, ['rf_copper', 'rf_candle', 'rf_glass'][j % 3], 6)
            elif kind == 'bottles': p.m.cyl((x, 0, z + .04), .05, .28, ['rf_glass', 'rf_waterfx', 'rf_copper'][j % 3], 6, r2=.02)
            elif kind == 'food': p.m.cyl((x, 0, z + .04), .14, .12, 'rf_candle', 8) if j % 2 else p.m.sphere((x, 0, z + .15), .12, 'rf_copper', 6, 4, sz=1.4)
            elif kind == 'linen': p.m.box((x - .13, -.18, z + .04), (x + .13, .18, z + .2), ['rf_candle', 'rf_fabricblue', 'rf_fabricred'][j % 3], 1)
            elif kind == 'scrolls': p.m.cyl((x, -.15, z + .1), .05, .01, 'rf_parchment', 6) or p.m.box((x - .06, -.18, z + .04), (x + .06, .18, z + .16), 'rf_parchment', 1)
            elif kind == 'ledgers': p.m.box((x - .1, -.15, z + .04), (x + .05, .15, z + .3), ['rf_fabricred', 'rf_wood', 'rf_fabricblue'][j % 3], 1)
    p.c.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), 'wood')
    return p


def bunk():
    p = Prop()
    for z in (.3, 1.5):
        p.m.box((-.5, -1.0, z), (.5, 1.0, z + .2), 'rf_woodlight', 1); p.m.box((-.45, -.95, z + .2), (.45, .95, z + .32), 'rf_fabricblue', 1, faces='xXyYZ')
    for sx in (-1, 1):
        for sy in (-1, 1): p.m.box((sx * .5 - .05, sy * 1.0 - .05, 0), (sx * .5 + .05, sy * 1.0 + .05, 2.1), 'rf_wood', 1, faces='xXyY')
    p.c.box((-.55, -1.05, 0), (.55, 1.05, 2.1), 'wood')
    return p


def map_table(w=4.0, d=2.4):
    p = table(w, d, .9, 'rf_wood')
    p.m.box((-w / 2 + .1, -d / 2 + .1, .9), (w / 2 - .1, d / 2 - .1, .915), 'rf_map', 1, faces='Z')
    k = len(p.m.uv) - 4; p.m.uv[k:k + 4] = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for j in range(9):
        x = -w / 2 + .4 + (j * 1.37) % (w - .8); y = -d / 2 + .3 + (j * .71) % (d - .6)
        p.m.cyl((x, y, .915), .06, .16, 'rf_banner' if j % 2 else 'rf_fabricred', 5, r2=.02)
    return p


def globe():
    p = Prop(); p.m.cyl((0, 0, 0), .25, .7, 'rf_wood', 6, r2=.05); p.m.sphere((0, 0, 1.05), .32, 'rf_map', 10, 6)
    p.m.cyl((0, 0, .7), .03, .7, 'rf_gold', 4, caps=False); p.c.box((-.32, -.32, 0), (.32, .32, 1.4), 'wood'); return p


def telescope(big=False):
    p = Prop(); s = 2.0 if big else 1.0
    for k in range(3):
        a = 2 * math.pi * k / 3; p.m.poly([(0, 0, 1.3 * s), (.5 * s * math.cos(a), .5 * s * math.sin(a), 0), (.5 * s * math.cos(a) + .04, .5 * s * math.sin(a), 0)], 'rf_wood', two_sided=True)
    p.m.cyl((0, 0, 1.3 * s), .1 * s, .05, 'rf_gold', 6)
    from fortlib import Mesh as _M
    tube = _M(); tube.cyl((0, 0, -.9 * s), .09 * s, 1.9 * s, 'rf_copper', 8, r2=.13 * s)
    ang = math.radians(55); c_, s_ = math.cos(ang), math.sin(ang)
    tube.v = [(x, y * c_ + z * s_, -y * s_ + z * c_ + 1.35 * s) for (x, y, z) in tube.v]
    p.m.merge(tube)
    p.c.box((-.5 * s, -.5 * s, 0), (.5 * s, .5 * s, 1.4 * s), 'metal')
    return p


def flask_table(w=2.4):
    p = table(w, 1.0, .9, 'rf_wood')
    for j in range(7):
        x = -w / 2 + .25 + j * (w - .5) / 6
        tex = ['rf_waterfx', 'rf_glass', 'rf_copper'][j % 3]
        p.m.sphere((x, (j % 2) * .25 - .1, 1.02), .09 + .03 * (j % 2), tex, 7, 5); p.m.cyl((x, (j % 2) * .25 - .1, 1.08), .025, .14, 'rf_glass', 5)
    p.m.box((.2, .15, .9), (.6, .45, .95), 'rf_parchment', 1)
    p.flame((-w / 2 + .3, .3, .92), .1, color=(140, 255, 160), power=.6, radius=4)
    return p


def bathtub():
    p = Prop()
    p.m.cyl((0, 0, 0), .8, .7, 'rf_copper', 14, caps=False, r2=.9)
    p.m.cyl((0, 0, .5), .85, .01, 'rf_waterfx', 14, caps=True)
    for i, v in enumerate(p.m.v):
        p.m.v[i] = (v[0] * .65, v[1] * 1.4, v[2])
    p.c.box((-.6, -1.26, 0), (.6, 1.26, .7), 'metal')
    return p


def pew(w=3.0):
    p = bench(w, 'rf_wood'); p.m.box((-w / 2, -.25, .48), (w / 2, -.19, 1.0), 'rf_wood', 1)
    p.m.box((-w / 2, .5, .0), (w / 2, .56, .9), 'rf_wood', 1); p.c.box((-w / 2, .5, 0), (w / 2, .56, .9), 'wood')
    return p


def altar():
    p = Prop()
    p.box((-1.4, -.6, 0), (1.4, .6, 1.05), 'rf_whitemarble', uv=2, surf='marble')
    p.m.box((-1.42, -.62, .7), (1.42, .62, 1.06), 'rf_fabricblue', 1, faces='yYZ' if False else 'y')
    p.m.box((-.04, -.04, 1.05), (.04, .04, 1.8), 'rf_gold', 1); p.m.box((-.3, -.04, 1.5), (.3, .04, 1.58), 'rf_gold', 1)
    for dx in (-1.0, 1.0):
        p.m.cyl((dx, 0, 1.05), .05, .35, 'rf_candle', 6); p.flame((dx, 0, 1.4), .12, power=.6, radius=6)
    return p


def bell(r=1.1):
    p = Prop()
    p.m.box((-1.6, -.15, 3.0), (1.6, .15, 3.25), 'rf_wood', 1)
    for sx in (-1, 1): p.m.box((sx * 1.6 - .15, -.15, 0), (sx * 1.6 + .15, .15, 3.25), 'rf_wood', 1)
    p.m.cyl((0, 0, 1.2), r, .3, 'rf_bronze', 14, caps=False, r2=r * .8)
    p.m.cyl((0, 0, 1.5), r * .8, 1.2, 'rf_bronze', 14, caps=True, r2=r * .45)
    p.c.box((-1.75, -.3, 0), (1.75, .3, 3.25), 'wood'); p.c.box((-r, -r, 1.2), (r, r, 2.7), 'metal')
    return p


def brazier():
    p = Prop()
    for k in range(3):
        a = 2 * math.pi * k / 3; p.m.poly([(0, 0, .9), (.35 * math.cos(a), .35 * math.sin(a), 0), (.35 * math.cos(a) + .05, .35 * math.sin(a), 0)], 'rf_iron', two_sided=True)
    p.m.cyl((0, 0, .8), .25, .25, 'rf_iron', 10, r2=.4); p.flame((0, 0, 1.0), .6, power=1.3, radius=9)
    p.c.box((-.4, -.4, 0), (.4, .4, 1.05), 'metal')
    return p


def pillory():
    p = Prop()
    p.box((-.1, -.1, 0), (.1, .1, 1.7), 'rf_wood', uv=1); p.m.box((-.9, -.12, 1.3), (.9, .12, 1.55), 'rf_wood', 1)
    p.c.box((-.9, -.12, 1.3), (.9, .12, 1.55), 'wood'); return p


def cot():
    p = Prop(); p.box((-.45, -1.0, 0), (.45, 1.0, .4), 'rf_wood', uv=1); p.m.box((-.4, -.95, .4), (.4, .95, .48), 'rf_hay', 1, faces='xXyYZ'); return p


def dummy():
    p = Prop(); p.m.cyl((0, 0, 0), .05, 1.2, 'rf_wood', 5); p.m.cyl((0, 0, 1.0), .25, .7, 'rf_hay', 8, r2=.22)
    p.m.sphere((0, 0, 1.9), .16, 'rf_hay', 7, 4); p.m.box((-.55, -.04, 1.45), (.55, .04, 1.53), 'rf_wood', 1)
    p.c.box((-.25, -.25, 0), (.25, .25, 2.0), 'wood'); return p


def target():
    p = Prop(); p.m.box((-.05, .1, 0), (.05, .2, 1.6), 'rf_wood', 1)
    disc = Mesh(); disc.cyl((0, 0, -.12), .7, .24, 'rf_hay', 14, caps=True)
    disc.v = [(x, -z, y + 1.0) for (x, y, z) in disc.v]; p.m.merge(disc)
    p.c.box((-.7, -.15, .3), (.7, .2, 1.7), 'wood'); return p


def winch():
    p = Prop()
    p.m.cyl((-1.2, 0, 1.0), .5, 2.4, 'rf_wood', 10, caps=True)
    for i in range(len(p.m.v)):
        x, y, z = p.m.v[i]; p.m.v[i] = (z - 2.2, -y, x + 2.2)
    for sx in (-1.3, 1.3): p.m.box((sx - .12, -.4, 0), (sx + .12, .4, 1.6), 'rf_wood', 1)
    p.m.cyl((0, 0, 1.0), .05, 3.5, 'rf_iron', 4, caps=False)
    p.c.box((-1.45, -.5, 0), (1.45, .5, 1.6), 'wood'); return p


def lantern_post(h=3.6):
    p = Prop()
    p.m.box((-.25, -.25, 0), (.25, .25, .4), 'rf_stonedark', 1); p.m.cyl((0, 0, .4), .07, h - .4, 'rf_iron', 6, caps=False)
    p.m.box((-.2, -.2, h), (.2, .2, h + .45), 'rf_lamp', 1); p.m.cyl((0, 0, h + .45), .3, .3, 'rf_iron', 4, r2=0)
    p.m.box((-.23, -.23, h - .03), (.23, .23, h), 'rf_iron', 1)
    p.flames.append({'pos': [0, 0, h + .22], 'size': .35, 'color': [255, 196, 120], 'lamp': True})
    p.c.box((-.25, -.25, 0), (.25, .25, h), 'metal'); return p


def instrument_set():
    p = Prop()
    p.m.cyl((0, 0, 0), .35, .6, 'rf_wood', 10); p.m.cyl((0, 0, .6), .36, .02, 'rf_parchment', 10)
    p.m.sphere((1.0, 0, .55), .25, 'rf_wood', 8, 5, sz=.4); p.m.box((1.0, .2, .5), (1.05, .9, .58), 'rf_wood', 1)
    for dx in (-.8, 1.8):
        p.m.cyl((dx, -.5, 0), .03, 1.1, 'rf_iron', 4); p.m.box((dx - .25, -.52, 1.1), (dx + .25, -.48, 1.4), 'rf_parchment', 1)
    p.c.box((-.4, -.6, 0), (2.0, .6, 1.2), 'wood'); return p


def gold_pile(r=.9):
    p = Prop(); p.m.cyl((0, 0, 0), r, r * .6, 'rf_gold', 12, caps=False, r2=.05)
    for k in range(5):
        a = k * 1.3; p.m.cyl((r * .9 * math.cos(a), r * .9 * math.sin(a), 0), .25, .06, 'rf_gold', 8)
    p.c.box((-r * .7, -r * .7, 0), (r * .7, r * .7, r * .5), 'metal'); return p


def crown_display():
    p = display_case(1.0, 1.0, 1.1, 'rf_gold')
    p.m.cyl((0, 0, 1.15), .16, .12, 'rf_gold', 10, caps=False)
    for k in range(6):
        a = 2 * math.pi * k / 6; p.m.cyl((.16 * math.cos(a), .16 * math.sin(a), 1.27), .03, .08, 'rf_gold', 4, r2=0)
    return p


def lectern():
    p = Prop(); p.m.cyl((0, 0, 0), .25, .1, 'rf_wood', 8); p.m.box((-.06, -.06, .1), (.06, .06, 1.0), 'rf_wood', 1)
    p.m.poly([(-.35, -.2, 1.0), (.35, -.2, 1.0), (.35, .15, 1.25), (-.35, .15, 1.25)], 'rf_wood', two_sided=True)
    p.m.poly([(-.3, -.17, 1.02), (.3, -.17, 1.02), (.3, .12, 1.25), (-.3, .12, 1.25)], 'rf_parchment')
    p.c.box((-.35, -.25, 0), (.35, .2, 1.25), 'wood'); return p


def cell_bars(length, height, axis='x'):
    """Iron bar partition along x (centre line y=0), 0.05 bars every 0.18 m."""
    p = Prop(); n = int(length / .18)
    for k in range(n + 1):
        x = -length / 2 + k * length / n
        p.m.box((x - .025, -.025, 0), (x + .025, .025, height), 'rf_iron', 1, faces='xXyY')
    for z in (.05, height * .5, height - .08):
        p.m.box((-length / 2, -.04, z), (length / 2, .04, z + .08), 'rf_iron', 1)
    p.c.box((-length / 2, -.06, 0), (length / 2, .06, height), 'metal')
    return p


def chains():
    p = Prop()
    for k in range(10): p.m.cyl((0, .05, -k * .12), .04, .08, 'rf_iron', 6, caps=False)
    p.m.cyl((0, .05, -1.3), .1, .05, 'rf_iron', 8, caps=False)
    return p


def mill_wheel(r=4.0, w=1.6):
    """Water wheel centred at origin, axis along x (rotated client-side)."""
    p = Prop(); m = Mesh(); p.c.box((-w / 2, -r, -r), (w / 2, r, r), 'wood')
    for side in (-w / 2, w / 2):
        for k in range(16):
            a0 = 2 * math.pi * k / 16; a1 = 2 * math.pi * (k + 1) / 16
            for rr in (r, r - .25):
                pass
            q = [(side, r * math.cos(a0), r * math.sin(a0)), (side, r * math.cos(a1), r * math.sin(a1)), (side, (r - .3) * math.cos(a1), (r - .3) * math.sin(a1)), (side, (r - .3) * math.cos(a0), (r - .3) * math.sin(a0))]
            m.poly(q, 'rf_wood', two_sided=True)
        for k in range(8):
            a = math.pi * k / 4; m.poly([(side, 0, 0), (side, r * math.cos(a), r * math.sin(a)), (side, r * math.cos(a + .08), r * math.sin(a + .08))], 'rf_wood', two_sided=True)
    for k in range(16):
        a = 2 * math.pi * k / 16
        m.poly([(-w / 2, r * math.cos(a), r * math.sin(a)), (w / 2, r * math.cos(a), r * math.sin(a)), (w / 2, (r + .5) * math.cos(a), (r + .5) * math.sin(a)), (-w / 2, (r + .5) * math.cos(a), (r + .5) * math.sin(a))], 'rf_wood', two_sided=True)
    hub = Mesh(); hub.cyl((0, 0, -w / 2 - .3), .35, w + .6, 'rf_iron', 8)
    hub.v = [(z, -y, x) for (x, y, z) in hub.v]; m.merge(hub)
    p.m = m
    return p


# ====================================================================== interactive (moving) parts
# Pivot conventions (used by the client animator):
#   swing leaves: hinge line at local x=0, leaf spans +x (0..w), y = 0 is the leaf centre plane
#   slide parts:  origin at the closed position's bottom-centre, motion vector given in world.json
#   lift (portcullis): bottom-centre, rises +z;  bridge: hinge along local x at y=0, deck spans +y
def door_leaf(w, h, style='oak'):
    p = Prop(); t = .12
    if style == 'bars':
        n = max(3, int(w / .16))
        for k in range(n + 1):
            x = .03 + k * (w - .06) / n; p.m.box((x - .025, -.025, 0), (x + .025, .025, h), 'rf_iron', 1, faces='xXyY')
        for z in (.05, h / 2, h - .1): p.m.box((0, -.04, z), (w, .04, z + .08), 'rf_iron', 1)
        p.c.box((0, -.05, 0), (w, .05, h), 'metal'); return p
    tex = {'oak': 'rf_wood', 'iron': 'rf_iron', 'grand': 'rf_wood', 'gate': 'rf_wood'}[style]
    p.box((0.01, -t / 2, 0), (w - .01, t / 2, h), tex, uv=2.0, surf='metal' if style == 'iron' else 'wood')
    band = 'rf_gold' if style == 'grand' else 'rf_iron'
    for z in (h * .18, h * .5, h * .82):
        p.m.box((.02, -t / 2 - .02, z - .05), (w * .85, t / 2 + .02, z + .05), band, 1, faces='yYzZ')
    if style in ('grand', 'gate'):
        for zz in (h * .3, h * .7):
            p.m.box((w * .15, -t / 2 - .03, zz - .5), (w * .85, -t / 2 - .01, zz + .5), 'rf_wood', 1.5, faces='y')
            p.m.box((w * .15, t / 2 + .01, zz - .5), (w * .85, t / 2 + .03, zz + .5), 'rf_wood', 1.5, faces='Y')
    for sy in (-1, 1):
        p.m.cyl((w - .18, sy * (t / 2 + .06), h * .45), .08, .02, band, 8, caps=False)
        p.m.box((w - .2, sy * (t / 2) - .03 if sy > 0 else -t / 2 - .06, h * .45 - .04), (w - .16, sy * (t / 2) + .06 if sy > 0 else -t / 2 + .03, h * .45 + .04), band, 1)
    return p


def bookcase_door(w, h):
    p = bookshelf(w, h, .4)
    p.m.box((-w / 2, -.25, 0), (w / 2, -.2, h), 'rf_wood', 2, faces='y')
    return p


def cell_door(w=1.2, h=2.5):
    p = door_leaf(w, h, 'bars')
    p.m.box((w * .8, -.08, h * .45), (w * .9, .08, h * .55), 'rf_iron', 1)
    return p


def portcullis(w, h):
    p = Prop(); n = int(w / .35)
    for k in range(n + 1):
        x = -w / 2 + k * w / n; p.m.box((x - .06, -.06, 0), (x + .06, .06, h), 'rf_iron', 1)
        p.m.cyl((x, 0, -.3), .06, .3, 'rf_iron', 4, r2=0.0, caps=False)
    for z in np.arange(.4, h, .45): p.m.box((-w / 2, -.07, z), (w / 2, .07, z + .1), 'rf_iron', 1)
    p.c.box((-w / 2, -.1, 0), (w / 2, .1, h), 'metal'); return p


def drawbridge(w, l):
    p = Prop()
    p.box((-w / 2, 0, -.45), (w / 2, l, 0), 'rf_wood', uv=2.5, surf='wood')
    for x in (-w / 2 + .25, w / 2 - .25):
        p.m.box((x - .2, 0, -.6), (x + .2, l, -.45), 'rf_iron', 2, faces='xXzY')
    for y in np.arange(1.0, l, 2.0): p.m.box((-w / 2, y - .08, .0), (w / 2, y + .08, .02), 'rf_iron', 1, faces='Z')
    for sx in (-1, 1): p.m.cyl((sx * (w / 2 - .1), l - .2, 0), .12, .25, 'rf_iron', 6)
    return p


def vault_door(r=1.35):
    """Round vault door; hinge at local x=0, disc centred at x=r."""
    p = Prop()
    disc = Mesh(); disc.cyl((0, 0, -.25), r, .5, 'rf_iron', 20, caps=True)
    disc.v = [(x + r, -z, y + r) for (x, y, z) in disc.v]; p.m.merge(disc)
    wheel = Mesh(); wheel.cyl((0, 0, .25), .45, .08, 'rf_gold', 12, caps=True)
    wheel.v = [(x + r, -z, y + r) for (x, y, z) in wheel.v]; p.m.merge(wheel)
    for k in range(6):
        a = math.pi * k / 3
        p.m.box((r + .45 * math.cos(a) - .04, -.42, r + .45 * math.sin(a) - .04), (r + .45 * math.cos(a) + .04, -.32, r + .45 * math.sin(a) + .04), 'rf_gold', 1)
    for k in range(10):
        a = 2 * math.pi * k / 10
        p.m.cyl((r + (r - .15) * math.cos(a), -.28, r + (r - .15) * math.sin(a)), .06, .03, 'rf_gold', 6)
    p.c.box((0, -.25, 0), (2 * r, .25, 2 * r), 'metal'); return p


def book_lever():
    p = Prop(); p.box((-.05, -.14, 0), (.05, .14, .32), 'rf_fabricred', uv=1, surf='wood')
    p.m.box((-.055, -.145, .25), (.055, .145, .27), 'rf_gold', 1, faces='xXyY'); return p
