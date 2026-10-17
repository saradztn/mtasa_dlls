"""Real low-poly facade details. Metres, closed surfaces, no modifier-only bevels."""
import math

def chamfered_column(mesh,lo,hi,bevel,texture):
    x0,y0,z0=lo;x1,y1,z1=hi
    if not all(math.isfinite(v) for v in (*lo,*hi,bevel)) or not 0<bevel<min(x1-x0,y1-y0)/2 or z1<=z0:
        raise ValueError('Invalid chamfered extrusion dimensions')
    b=bevel
    ring=[(x0+b,y0),(x1-b,y0),(x1,y0+b),(x1,y1-b),(x1-b,y1),(x0+b,y1),(x0,y1-b),(x0,y0+b)]
    perimeter=0
    for i,a in enumerate(ring):
        q=ring[(i+1)%8];length=math.dist(a,q)
        mesh.quad((*a,z0),(*q,z0),(*q,z1),(*a,z1),texture,[(perimeter/2,z0/2),((perimeter+length)/2,z0/2),((perimeter+length)/2,z1/2),(perimeter/2,z1/2)])
        perimeter+=length
    mesh.poly([(*p,z0) for p in reversed(ring)],texture)
    mesh.poly([(*p,z1) for p in ring],texture)

def louver_blade(mesh,x0,x1,y,z,texture):
    """Closed four-sided sloping blade, 35 cm deep and 4 cm thick."""
    ring=[(y,z),(y+.35,z-.14),(y+.35,z-.10),(y,z+.04)]
    for i,a in enumerate(ring):
        b=ring[(i+1)%4]
        mesh.quad((x0,*a),(x0,*b),(x1,*b),(x1,*a),texture)
    mesh.poly([(x0,*p) for p in reversed(ring)],texture)
    mesh.poly([(x1,*p) for p in ring],texture)
