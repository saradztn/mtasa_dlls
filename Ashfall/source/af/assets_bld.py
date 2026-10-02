# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# assets_bld.py - the building models (facade builder specs).  Every building also gets a companion alpha model
#   "<name>_v" with ivy, weeds and shrubs (same origin) so the opaque model never needs alpha sorting.
import numpy as np
from .kit import asset
from .bld import Building
from .pv import ao_default

# name: (spec, cat)   footprint W x D, origin = SW corner
SPECS = {
    'tower_a': dict(W=26, D=24, floors=10, wall='panel', seed=11, dmg=0.55, ground='shop', cut=dict(x0=12, y0=10, k=6)),
    'tower_b': dict(W=22, D=30, floors=12, wall='concrete', seed=23, dmg=0.50, bw=3.2, pw=0.38, wh=1.9, sill=0.85, ground='shop', cut=dict(x0=8, y0=14, k=8)),
    'apt_a': dict(W=40, D=18, floors=6, wall='brick', seed=31, dmg=0.45, balcony=0.45, gh=3.8, fh=3.1, bw=4.0, pw=0.8, sill=0.9, wh=1.5, cut=dict(x0=26, y0=6, k=3)),
    'apt_b': dict(W=32, D=20, floors=5, wall='plaster_a', seed=41, dmg=0.50, balcony=0.55, gh=3.6, fh=3.1, bw=4.0, pw=0.8, wh=1.5, cut=None),
    'apt_c': dict(W=28, D=18, floors=4, wall='plaster_b', seed=47, dmg=0.60, balcony=0.35, gh=3.4, fh=3.1, bw=3.5, pw=0.75, wh=1.5, cut=dict(x0=14, y0=4, k=2)),
    'shop_a': dict(W=36, D=14, floors=3, wall='plaster_c', seed=53, dmg=0.50, ground='shop', gh=4.4, fh=3.5, bw=4.5, pw=0.7, wh=1.7, cut=None, tank=False),
    'shop_b': dict(W=28, D=14, floors=2, wall='brick', seed=59, dmg=0.60, ground='shop', gh=4.2, fh=3.4, bw=4.0, pw=0.8, wh=1.6, cut=dict(x0=14, y0=0, k=1), tank=False),
    'hotel': dict(W=30, D=22, floors=8, wall='plaster_a', seed=67, dmg=0.45, balcony=0.30, gh=4.6, fh=3.2, bw=3.75, pw=0.7, wh=1.6, ground='shop', cut=dict(x0=15, y0=11, k=6)),
    'kiosk': dict(W=9, D=6, floors=1, wall='plaster_c', seed=77, dmg=0.7, ground='shop', gh=3.3, bw=3.0, pw=0.4, wh=1.8, cut=None, tank=False, ivy=10, cornice=False),
    'office_low': dict(W=34, D=20, floors=4, wall='panel', seed=71, dmg=0.55, bw=3.4, pw=0.45, wh=1.8, ground='shop', cut=None),
}


def make(name):
    spec = dict(SPECS[name])
    c = spec.get('cut')
    if c:
        b0 = Building(dict(spec, cut=None))     # just for floor heights
        spec['cut'] = dict(x0=c['x0'], y0=c['y0'], z0=b0.Z[min(c['k'], len(b0.Z) - 2)])
    b = Building(spec)
    M, V, C = b.build()
    return M, V, C


for _n in SPECS:
    def _mk(n=_n):
        def run_main():
            M, V, C = make(n)
            return M, C, ao_default
        def run_veg():
            M, V, C = make(n)
            from .mb import Col
            return V, Col(), ao_default
        asset('af_' + n, 'struct', dist=650.0, day_glow=0.0)(run_main)
        asset('af_' + n + '_v', 'flora', dist=220.0, day_glow=0.0)(run_veg)
    _mk()
