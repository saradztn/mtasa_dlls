"""Numerical geometry contracts; not an artistic/reference-match acceptance test."""
from pathlib import Path
import json,hashlib,math
import numpy as np
from geometry import Mesh
from architectural_details import chamfered_column,louver_blade
ROOT=Path(__file__).resolve().parents[1]
def volume_and_edges(m):
    edges={};volume=0
    for f in m.f:
        a,b,c=[np.array(m.v[i]) for i in f[:3]]
        assert np.isfinite([a,b,c]).all() and np.linalg.norm(np.cross(b-a,c-a))>1e-9
        volume+=np.dot(a,np.cross(b,c))/6
        for i,j in [(0,1),(1,2),(2,0)]:
            p,q=[tuple(m.v[f[k]]) for k in (i,j)];key=tuple(sorted((p,q)))
            edges.setdefault(key,[]).append(1 if p<q else -1)
    assert all(len(v)==2 and sum(v)==0 for v in edges.values()),'Nonmanifold/open or reversed edge'
    assert len(m.uv)==len(m.v) and np.isfinite(m.uv).all()
    return volume
samples=0
for x in [-29,0,57.7]:
    for width,depth,height,bevel in [(1,2,26,.12),(.8,1,4,.08),(18,1.4,5,.16),(92.4,.4,.85,.07)]:
        m=Mesh();chamfered_column(m,(x,-39.35,4),(x+width,-39.35+depth,4+height),bevel,'psg_concrete')
        expected=(width*depth-2*bevel**2)*height
        assert math.isclose(volume_and_edges(m),expected,rel_tol=1e-8,abs_tol=1e-7)
        assert len(m.f)==28
        samples+=1
    m=Mesh();louver_blade(m,x,x+1.4,-26.43,18.13,'psg_steel')
    assert math.isclose(volume_and_edges(m),1.4*.35*.04,rel_tol=1e-7,abs_tol=1e-8)
    samples+=1
for b in [0,-1,.5,float('nan')]:
    try:chamfered_column(Mesh(),(0,0,0),(1,1,1),b,'psg_concrete')
    except ValueError:pass
    else:raise AssertionError('Invalid bevel accepted')
details=json.loads((ROOT/'source_assets/facade_details.json').read_text())
assert details['chamfered_extrusions']==41
assert details['louver_modules']>=10 and details['louver_blades']==10*details['louver_modules']
assert details['rainwater_stacks']==4
layout=json.loads((ROOT/'source_assets/layout.json').read_text())
assert len(layout['assets'])==11 and len(layout['placements'])==9 and len(layout['panels'])==36
result={'status':'PASS','scope':'Closed oriented helper meshes and authored inventory only; no MTA rendering/physics or reference-match signoff','geometry_samples':samples,'tests':['positive analytic volume and closed consistently oriented edges on chamfer extrusions','closed sloped blades have positive thickness and finite UVs','invalid/NaN bevel dimensions rejected','detail inventory present; original 11 model assets and 36 panels preserved'],'details':details,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/architectural_details.py','tools/build_geometry.py','source_assets/facade_details.json','source_assets/layout.json','models/entry_exterior.dff','collisions/entry_exterior.col']}}
(ROOT/'tests/architecture_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
