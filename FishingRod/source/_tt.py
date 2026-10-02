import time, numpy as np, pickle
from PIL import Image
from fr import texgen
from fr.materials import MATS
out={}
for m in MATS:
    k=m['key']; g,ns=texgen.GENERATORS[k]
    t=time.time(); tx=g(); d,n,o=texgen.bake(tx,ns)
    assert d.shape[:2]==(m['size'][1],m['size'][0]),(k,d.shape,m['size'])
    out[k]=(d,n,o)
    Image.fromarray(d).save('_work/d_%s.png'%k); 
    Image.fromarray(n[...,[3,1,2]]).save('_work/n_%s.png'%k)
    print(k,d.shape,round(time.time()-t,1))
