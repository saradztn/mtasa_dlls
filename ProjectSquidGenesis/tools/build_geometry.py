"""Metre-space architecture, modular trusses, fasteners, fixtures and braided rope.
All game geometry is authored here; no models from the existing resource are used.
"""
from pathlib import Path
import json,math,gzip
import numpy as np
from rope_profile import height as rope_height
from architectural_details import chamfered_column,louver_blade
from geometry import Mesh,Collision,export_dff,export_col,bake
ROOT=Path(__file__).resolve().parents[1]
assets=[]; sources={};lights=[];placements=[]
facade_details={"chamfered_extrusions":0,"louver_modules":0,"louver_blades":0,"rainwater_stacks":0,"scope":"Authored facade detail, simplified box collision; not visual acceptance or plumbing simulation"}
def chamfer(m,c,lo,hi,b=.1,tex="concrete",solid=True):
    chamfered_column(m,lo,hi,b,"psg_"+tex)
    if solid:c.box(lo,hi,"concrete" if tex=="concrete" else "metal")
    facade_details["chamfered_extrusions"]+=1
def asset(name):return Mesh(),Collision()
def box(m,c,lo,hi,tex='steel',solid=True):
    m.box(lo,hi,'psg_'+tex,uvscale=.6 if tex=='rope' else 2)
    if solid:c.box(lo,hi,'glass' if tex=='glass' else 'metal' if tex in ('steel','floor','frame') else 'concrete')
def beam(m,a,b,width=.15,tex='steel'):
    a=np.array(a,float);b=np.array(b,float);v=b-a;v/=np.linalg.norm(v);u=np.cross(v,[0,0,1] if abs(v[2])<.9 else [0,1,0]);u/=np.linalg.norm(u);w=np.cross(v,u);ring=[u+w,-u+w,-u-w,u-w];p=[a+r*width/2 for r in ring];q=[b+r*width/2 for r in ring]
    for i in range(4):m.quad(p[i],p[(i+1)%4],q[(i+1)%4],q[i],'psg_'+tex)
    m.poly(p[::-1],'psg_'+tex);m.poly(q,'psg_'+tex)
def rail(m,c,a,b,z=0):
    beam(m,(a[0],a[1],z+1.05),(b[0],b[1],z+1.05),.065,'frame');beam(m,(a[0],a[1],z+.5),(b[0],b[1],z+.5),.04)
    for t in np.linspace(0,1,max(2,int(math.dist(a,b)/2)+1)):
        x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t;box(m,c,(x-.035,y-.035,z),(x+.035,y+.035,z+1.1),'frame')
def fixture(m,c,x,y,z,color='cyan',vertical=True):
    size=(.18,.15,3) if vertical else (1.8,.3,.12)
    box(m,c,(x-.1,y-.1,z-.12),(x+size[0]+.1,y+size[1]+.1,z+size[2]+.12),'steel',False)
    box(m,c,(x,y,z),(x+size[0],y+size[1],z+size[2]),color,False)
    lights.append({'position':[x+size[0]/2,y+.3 if vertical else y+.15,z+size[2]/2 if vertical else z-.3],'color':{'cyan':[.07,.7,.85],'pink':[.85,.04,.32],'amber':[.85,.55,.22]}[color],'radius':12})
def save(name,m,c,at=(0,0,0),role='structure'):
    local_lights=[{'pos':l['position'],'color':l['color'],'radius':24,'power':1.3} for l in lights]
    # Subtle constant prelight; actual local sources handled by runtime shader.
    for i,v in enumerate(m.v):
        n=.5+.14*max(0,min(1,(v[2]+48)/72));m.c[i]=(int(n*220),int(n*235),int(n*255),255)
    bake(m,(.65,.72,.82),local_lights,clamp=(70,255))
    stats=export_dff(m,ROOT/f'models/{name}.dff',name)
    cs=export_col(c,ROOT/f'collisions/{name}.col',name,stats['bounds'])
    sources[name]={'v':m.v,'uv':m.uv,'f':m.f,'textures':m.textures,'colors':m.c}
    assets.append({'name':name,'role':role,'position':list(at),**stats,'collision':cs})
    placements.append({'asset':name,'position':list(at)})
# Two halls: structural bays, deep shaft, working perimeter and overhead grid.
for hall,x0,x1,y0,y1 in [('tug',-28,28,-25,25),('bridge',34,58,-25,45)]:
    m,c=asset(hall)
    box(m,c,(x0-1,y0-1,-49),(x1+1,y1+1,-48),'industrial')
    for x in (x0,x1):
        box(m,c,(x-.6,y0,-48),(x+.6,y1,24),'concrete')
        box(m,c,(x-1 if x==x1 else x,y0,-.5),(x if x==x1 else x+1,y1,0),'floor')
        for y in np.arange(y0+2,y1,7):
            # Exposed inner I-section column and bolted plates
            sx=x+(.95 if x==x0 else -.95)
            box(m,c,(sx-.35,y-.3,-48),(sx+.35,y+.3,23),'steel',False)
            for z in (-36,-24,-12,0,12,22):
                box(m,c,(sx-.5,y-.5,z),(sx+.5,y+.5,z+.12),'frame',False)
                for dx in (-.38,.38):m.cyl((sx+dx,y-.38,z+.12),.06,.06,'psg_bolt',sides=6)
            fixture(m,c,x+(.7 if x==x0 else -.9),y,8,'pink' if int(y)%2 else 'cyan')
            fixture(m,c,x+(.7 if x==x0 else -.9),y,-32,'cyan')
    # Perimeter handrails and horizontal panel seams expose depth.
    for x in (x0+1.6,x1-1.6):
        intervals=[(y0+3,-8),(8,y1-3)] if hall=='tug' else [(y0+3,y1-3)]
        for ya,yb in intervals:rail(m,c,(x,ya),(x,yb))
    for z in (-40,-32,-24,-16,-8,6,14):
        for x in (x0+.65,x1-.65):beam(m,(x,y0,z),(x,y1,z),.08,'frame')
    # End walls have real walk-through door openings at deck level.
    for y in (y0,y1):
        box(m,c,(x0,y-.5,-48),(x1,y+.5,-.5),'concrete')
        box(m,c,(x0,y-.5,4),(x1,y+.5,24),'concrete')
        openings=[(-23,-18),(18,23)] if hall=='tug' else [(43,49)]
        cursor=x0
        for a,b in openings:
            box(m,c,(cursor,y-.5,-.5),(a,y+.5,4),'concrete');cursor=b
        box(m,c,(cursor,y-.5,-.5),(x1,y+.5,4),'concrete')
        box(m,c,(x0,y if y==y0 else y-3,-.5),(x1,y+3 if y==y0 else y,0),'floor')
    for y in np.arange(y0+2,y1,7):
        beam(m,(x0,y,22),(x1,y,22),.35)
        for x in np.arange(x0,x1-3,4):
            beam(m,(x,y,20),(x+4,y,22),.15);beam(m,(x,y,22),(x+4,y,20),.15)
        fixture(m,c,(x0+x1)/2,y,21,'cyan',False)
    # Raised maintenance galleries: real slatted geometry and simplified solid collision.
    for edge in (-1,1):
        wall=x0 if edge<0 else x1
        xa,xb=(wall+.75,wall+3.1) if edge<0 else (wall-3.1,wall-.75)
        for yy in np.arange(y0+1,y1-1,.32):
            box(m,c,(xa,yy,11.82),(xb,min(yy+.15,y1-1),12),'floor',False)
        c.box((xa,y0+1,11.8),(xb,y1-1,12),'metal')
        for xx in (xa,xb):beam(m,(xx,y0+1,11.65),(xx,y1-1,11.65),.22)
        rail(m,c,((xb if edge<0 else xa),y0+1),((xb if edge<0 else xa),y1-1),12)
        for yy in np.arange(y0+2,y1-1,7):
            beam(m,(wall,yy,8.8),((xb if edge<0 else xa),yy,11.65),.18)
            # Multi-level wall crossbraces occupy the shaft edge, not the player route.
            for za in (-40,-24,-8):
                xx=wall+(.8 if edge<0 else -.8)
                beam(m,(xx,yy,za),(xx,min(yy+6,y1-1),za+7),.11)
                beam(m,(xx,yy,za+7),(xx,min(yy+6,y1-1),za),.11)
        # Maintenance ladder is visual equipment, not a GTA climbing mechanic.
        lx=wall+(1.5 if edge<0 else -1.5);ly=y1-6
        for yy in (ly-.35,ly+.35):beam(m,(lx,yy,.1),(lx,yy,13),.055,'frame')
        for zz in np.arange(.3,12.7,.3):beam(m,(lx,ly-.35,zz),(lx,ly+.35,zz),.035,'frame')
    # Roof is separate, permitting inspection
    save(hall+'_shell',m,c)
    m,c=asset('roof');box(m,c,(x0,y0,24),(x1,y1,24.5),'industrial');save(hall+'_roof',m,c)
# Opposing platforms: supported truss decks, anchors, hazard edge, service access.
for side in (-1,1):
    m,c=asset('deck');a,b=(-28,-14) if side<0 else (14,28)
    box(m,c,(a,-8,-.65),(b,8,0),'floor')
    for y in (-8,8):
        box(m,c,(a,y-.12,-.1),(b,y+.12,.025),'warning')
        for x in np.arange(a,b,3):
            beam(m,(x,y,-.7),(x+3,y,-4),.22);beam(m,(x,y,-4),(x+3,y,-.7),.22)
        beam(m,(a,y,-4),(b,y,-4),.3)
    for y in (-6,0,6):
        beam(m,((a+b)/2,y,-3),(side*27,y,-18),.55)
    # Access side connects deck to perimeter.
    for y in (-25,8):box(m,c,(a if side<0 else b-3,y,-.5),(a+3 if side<0 else b,y+17,0),'floor')
    leading=b if side<0 else a
    box(m,c,(leading-.12,-8,-.22),(leading+.12,8,.015),'warning')
    for xx in np.arange(a+.7,b-.3,1.8):
        box(m,c,(xx,-7.7,.005),(xx+.035,7.7,.02),'frame',False)
        for yy in (-7.6,7.6):m.cyl((xx,yy,.02),.045,.025,'psg_bolt',sides=6)
    # Dedicated rope-end pedestal and collar are centred on the actual endpoint.
    anchor=side*20
    box(m,c,(anchor-.5,-.45,0),(anchor+.5,.45,.15),'frame')
    m.cyl((anchor,0,.15),.22,.87,'psg_steel',sides=16)
    for k in range(12):
        t=k*math.tau/12;u=(k+1)*math.tau/12
        m.quad((anchor-.07,.09*math.cos(t),1.05+.09*math.sin(t)),(anchor-.07,.09*math.cos(u),1.05+.09*math.sin(u)),(anchor+.07,.09*math.cos(u),1.05+.09*math.sin(u)),(anchor+.07,.09*math.cos(t),1.05+.09*math.sin(t)),'psg_frame')
    for x in (a+2,b-2):
        beam(m,(x,-7,0),(x,-7,5),.1);fixture(m,c,x,-7,5,'amber',False)
    save('tug_deck_'+('left' if side<0 else 'right'),m,c)
# Braided rope: three helical strands, each swept using six-sided cross sections.
m,c=asset('rope');length=40;steps=480
for strand in range(3):
    rings=[]
    for i in range(steps+1):
        t=i/steps;x=-20+length*t;angle=t*math.pi*2*65+strand*math.pi*2/3
        center=np.array([x,.038*math.cos(angle),rope_height(x)+.038*math.sin(angle)])
        rings.append([center+np.array([0,.028*math.cos(k*math.tau/6),.028*math.sin(k*math.tau/6)]) for k in range(6)])
    for i in range(steps):
        for k in range(6):m.quad(rings[i][k],rings[i][(k+1)%6],rings[i+1][(k+1)%6],rings[i+1][k],'psg_rope',[(i/8,k/6),(i/8,(k+1)/6),((i+1)/8,(k+1)/6),((i+1)/8,k/6)])
save('rope',m,c,role='rope')
# Distant/LOW cable: the same sag and envelope, with a lobed cross-section.
# Fine helical fibre detail stays in the authored rope texture, not separate strands.
m,c=asset('rope_low');steps=80;sides=12
for i in range(steps):
    def ring(j,k):
        t=j/steps;angle=k*math.tau/sides;r=.058+.008*math.cos(3*angle)
        return (-20+40*t,r*math.cos(angle),rope_height(-20+40*t)+r*math.sin(angle))
    for k in range(sides):
        m.quad(ring(i,k),ring(i,k+1),ring(i+1,k+1),ring(i+1,k),'psg_rope',
               [(i/steps*40/.6,k/sides),(i/steps*40/.6,(k+1)/sides),((i+1)/steps*40/.6,(k+1)/sides),((i+1)/steps*40/.6,k/sides)])
save('rope_low',m,c,role='lod_template');placements.pop()

# Glass frames with underside diagonal bracing, side runners and bolted corners.
m,c=asset('bridge_frame')
for x in (44.2,46,47.8):box(m,c,(x-.08,-22,-.4),(x+.08,39,.02),'frame')
for row in range(19):
    y=-20+row*3.2;box(m,c,(44.1,y-.08,-.28),(47.9,y+.08,.04),'frame')
    if row<18:
        for x in (44.2,47.8):
            beam(m,(x,y,-.4),(x,y+3.2,-1.5),.12);beam(m,(x,y,-1.5),(x,y+3.2,-.4),.12)
            for yy in (y+.15,y+3.05):m.cyl((x,yy,.04),.055,.045,'psg_bolt',sides=6)
        if row%3==0:fixture(m,c,44.05,y,-.3,'cyan' if row%2==0 else 'pink',False)
for y,end in [(-25,-19.88),(37.48,45)]:box(m,c,(41,y,-.6),(51,end,0),'floor')
save('bridge_frame',m,c)
m,c=asset('panel');box(m,c,(-.77,-1.48,-.16),(.77,1.48,-.025),'glass');save('glass_panel',m,c,role='panel_template');placements.pop()
panels=[]
for row in range(18):
    for side,x in [('L',45.1),('R',46.9)]:panels.append({'id':f'GB_{row+1:02}_{side}','row':row+1,'side':side,'position':[x,-18.4+row*3.2,0],'material':'glass','state':'intact','appearanceMutable':True,'collisionMutable':True})
# Entry corridor: continuous T-path to both tug platforms and bridge, no extra rooms.
m,c=asset('entry')
box(m,c,(-30,-39,-.6),(62,-22,0),'concrete')
box(m,c,(-30,-39,0),(-27,-26,7),'concrete');box(m,c,(59,-39,0),(62,-26,7),'concrete')
# Low entry canopy and stepped facade crown, kept above clear door routes.
box(m,c,(-30,-39,6.8),(62,-26,7.3),'industrial')
for xa,xb,z in [(-28,-10,29),(-10,10,32),(10,28,28),(34,58,30)]:
    chamfer(m,c,(xa,-27,24.5),(xb,-25.6,z),.16)
    chamfer(m,c,(xa-.15,-27.25,z),(xb+.15,-25.45,z+.18),.12,tex='frame',solid=False)
    for xx in np.arange(xa+1,xb,4):
        box(m,c,(xx,-27.1,25),(xx+.18,-27,z-.5),'cyan',False)
# Exterior forecourt, drains, gate pillars, tiered facade fins.
box(m,c,(-40,-58,-.6),(70,-39,0),'asphalt')
for index,x in enumerate(np.arange(-29,61,6)):
    top=28+(int(x)%3)*2
    chamfer(m,c,(x,-29,4),(x+1,-27,top),.12)
    chamfer(m,c,(x-.12,-29.16,top),(x+1.12,-26.88,top+.18),.1,tex='frame',solid=False)
    fixture(m,c,x+.3,-29.6,9,'pink' if index%3==1 else 'cyan')
    # Glazing stays inside the two actual hall envelopes, not unsupported beyond them.
    if any(a<=x+2 and x+3.5<=b for a,b in [(-28,28),(34,58)]):
        for zz in (10,14,18,22):
            box(m,c,(x+2,-25.72,zz),(x+3.5,-25.6,zz+3.5),'glass',False)
            for xx in (x+1.9,x+3.5):box(m,c,(xx,-25.8,zz-.1),(xx+.1,-25.55,zz+3.6),'frame',False)
    # Recessed service louvers, backed and framed, with genuinely sloped closed blades.
    if any(a<=x+3.8 and x+5.2<=b for a,b in [(-28,28),(34,58)]):
        xa,xb=x+3.8,x+5.2
        box(m,c,(xa-.08,-26.0,17.85),(xb+.08,-25.75,20.6),'rubber',False)
        for xx in (xa-.08,xb):box(m,c,(xx,-26.42,17.85),(xx+.08,-25.72,20.6),'frame',False)
        for zz in (17.85,20.52):box(m,c,(xa,-26.42,zz),(xb,-25.72,zz+.08),'frame',False)
        for n in range(10):louver_blade(m,xa,xb,-26.43,18.13+n*.24,'psg_steel')
        facade_details['louver_modules']+=1;facade_details['louver_blades']+=10
# Horizontal reveals and coping articulate the existing stepped silhouette.
for xa,xb in [(-28,28),(34,58)]:
    for zz in (9.7,13.7,17.7,21.7):
        box(m,c,(xa,-26.65,zz),(xb,-26.3,zz+.12),'frame',False)
# Ribbed canopy soffit and a chamfered front fascia remain above head/door clearance.
chamfer(m,c,(-30.2,-39.35,6.65),(62.2,-38.95,7.5),.07,tex='frame',solid=False)
for xx in range(-28,61,4):beam(m,(xx,-38.7,6.62),(xx,-27,6.62),.12,'frame')
for xx in (-28.3,27.7,34.7,57.7):
    m.cyl((xx,-29.3,7.4),.095,20.4,'psg_steel',sides=12)
    for zz in (8,14,20,27):
        m.cyl((xx,-29.3,zz),.135,.08,'psg_frame',sides=12)
        beam(m,(xx,-29.3,zz+.04),(xx,-28.8,zz+.04),.07,'frame')
    beam(m,(xx,-29.3,27.8),(xx,-26.7,28.4),.18,'steel')
    facade_details['rainwater_stacks']+=1
for x in (-5,7):chamfer(m,c,(x,-49,0),(x+.8,-48,4),.08)
for x0,x1 in [(-40,-5),(8,70)]:
    for x in np.arange(x0,x1,.65):box(m,c,(x,-49,0),(x+.045,-48.95,2.5),'steel')
    beam(m,(x0,-49,2.4),(x1,-49,2.4),.07)
for x in range(-34,65,4):
    box(m,c,(x,-42,.005),(x+2,-41.7,.015),'rubber',False)
    for xx in np.arange(x,x+2,.13):box(m,c,(xx,-42,.02),(xx+.045,-41.7,.035),'frame',False)
# Readable wayfinding atlas, faced south, outside the clear door apertures.
for x,row in [(-21,0),(21,0),(46,1),(0,2)]:
    yy=-25.9 if row<2 else -39.15;zz=4.5 if row<2 else 5.2;w=4.8;h=1.2
    box(m,c,(x-w/2-.1,yy,zz-.1),(x+w/2+.1,yy+.14,zz+h+.1),'steel',False)
    m.quad((x-w/2,yy-.01,zz),(x+w/2,yy-.01,zz),(x+w/2,yy-.01,zz+h),(x-w/2,yy-.01,zz+h),'psg_signage',[(0,(row+1)/4),(1,(row+1)/4),(1,row/4),(0,row/4)])
    for side in (-1,1):box(m,c,(x+side*2.45-.06,yy-.06,zz),(x+side*2.45+.06,yy+.12,zz+h),'amber',False)

for x in (-21,21,46):fixture(m,c,x,-32,4,'amber',False)
save('entry_exterior',m,c)
(ROOT/'source_assets/facade_details.json').write_text(json.dumps(facade_details,indent=2))
(ROOT/'source_assets/layout.json').write_text(json.dumps({'origin':[5000,5000,100],'dimension':2601,'assets':assets,'placements':placements,'panels':panels,'lights':lights},indent=2))
with gzip.open(ROOT/'source_assets/blender/mesh_sources.json.gz','wt') as f:json.dump(sources,f)
print('Built',len(assets),'models,',len(panels),'panels;',sum(a['triangles'] for a in assets),'unique triangles')
