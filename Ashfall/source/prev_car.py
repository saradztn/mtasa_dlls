# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
import sys
sys.path.insert(0, '.')
import numpy as np
from af import pv, cars, assets_props
from af.kit import REG
from af.mb import Mesh
name = sys.argv[1] if len(sys.argv) > 1 else 'af_car_sedan_a'
a = REG[name]()
g = Mesh()
from af import tex
g.poly([(-12, -12, 0), (12, -12, 0), (12, 12, 0), (-12, 12, 0)], tex.IDX['af_asphalt'], hint=(0, 0, 1), tile=4.0)
for k, (e, t) in enumerate([((5.5, -3.5, 1.6), (0, 0, 0.8)), ((-2.5, 5.0, 1.3), (0, 0, 0.8)), ((3.2, 0.2, 1.0), (0, 0, 0.7))]):
    im = pv.render(pv.merge([g, a.M]), e, t, fov=50, W=960, H=600, ss=2)
    im.save('_work/car_%d.png' % k)
