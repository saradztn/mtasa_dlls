# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
import sys, time
import numpy as np
sys.path.insert(0, '.')
from af import bld, pv, tex
from af.mb import Mesh
spec = dict(W=26, D=24, floors=10, wall='panel', seed=7, dmg=0.55, balcony=0.0, ground='shop',
            cut=dict(x0=12, y0=10, z0=4.4 + 3.5 * 4))
t = time.time()
b = bld.Building(spec)
M, V, C = b.build()
print('build %.1fs' % (time.time() - t), sum(len(c[0]) for c in M.chunks), 'verts', sum(len(c[0]) for c in V.chunks), 'veg verts')
g = Mesh()
x = 60
g.poly([(-x, -x, 0), (x + 40, -x, 0), (x + 40, x + 40, 0), (-x, x + 40, 0)], tex.IDX['af_asphalt'], hint=(0, 0, 1), tile=6.0)
views = dict(a=((-30, -34, 9), (14, 10, 18), 62), b=((50, -10, 8), (14, 14, 16), 60), c=((46, 48, 14), (14, 12, 16), 62), d=((-8, -12, 2.0), (13, 0, 6), 70))
sel = sys.argv[1].split(',') if len(sys.argv) > 1 else ['a']
for k in sel:
    e, tg, fv = views[k]
    im = pv.render(pv.merge([g, M, V]), e, tg, fov=fv, W=960, H=640, ss=1)
    im.save('_work/bld_%s.png' % k)
print('ok')
