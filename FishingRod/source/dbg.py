# Created by: Arena.ai Agent Mode (AI) - debug helper
import sys, numpy as np
from fr.model import *
from fr.geom import merge_parts
from fr.materials import MATS
from fr.render import Scene, render
def scene():
    n=build_all()
    pos=[];nrm=[];uv=[];tr=[];tm=[];off=0
    for k,v in n.items():
        for p in v:
            pos.append(p.pos);nrm.append(p.nrm);uv.append(p.uv);tr.append(p.tris+off);tm.append(np.full(len(p.tris),p.mat));off+=len(p.pos)
    S=Scene(np.concatenate(pos),np.concatenate(nrm),np.concatenate(uv),np.concatenate(tr),np.concatenate(tm),len(MATS))
    for i,m in enumerate(MATS):
        S.param[i,:3]=m['rgb'];S.param[i,3]=m['rough'];S.param[i,4]=m['metal']
    return S
if __name__=='__main__':
    S=scene()
    which=sys.argv[1]
    if which=='side':
        render(S,(1.6,0.9,0.1)[::1] if False else (3.0,0.7,0.0),(0,0.7,-0.1),fov=30,W=1800,H=700,ss=1,ortho=False).save('_work/side.png')
    if which=='reel':
        render(S,(0.28,0.06,-0.04),(0,0.0,-0.07),fov=30,W=1400,H=1000,ss=1).save('_work/reel.png')
    if which=='reel2':
        render(S,(-0.2,0.3,-0.15),(0,0.03,-0.07),fov=30,W=1400,H=1000,ss=1).save('_work/reel2.png')
    if which=='tip':
        render(S,(0.15,1.5,0.0),(0,1.6,-0.07),fov=30,W=1400,H=1000,ss=1).save('_work/tip.png')
