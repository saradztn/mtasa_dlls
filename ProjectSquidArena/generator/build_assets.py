"""Procedural, modular RenderWare arena kit. Coordinates are metres, z-up, local to each arena."""
from pathlib import Path
import sys, math, json, random
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'lib')); sys.path.insert(0,str(ROOT/'vendor/DragonFF'))
from mesh_export import Mesh, Collision, export_dff, export_col

MODELS={}; PLACEMENTS=[]
def model(name,build,collision=True):
    m=Mesh(); c=Collision(); build(m,c)
    if not m.v: raise ValueError('empty model '+name)
    out=ROOT/'resource'; dff=out/'models'/(name+'.dff'); col=out/'collisions'/(name+'.col')
    info=export_dff(m,dff,name)
    if not c.boxes and not c.faces and collision:
        lo=np.min(np.asarray(m.v),axis=0);hi=np.max(np.asarray(m.v),axis=0);c.box(lo,hi,'metal')
    ci=export_col(c,col,name, (np.asarray(info['bounds'][0]),np.asarray(info['bounds'][1])))
    MODELS[name]={'dff':f'models/{name}.dff','col':f'collisions/{name}.col','textures':info['textures'],'vertices':info['vertices'],'triangles':info['triangles'],'bounds':info['bounds'],'collision_boxes':ci['boxes'],'collision_faces':ci['faces']}
    return name

def add(name,arena,x,y,z,rz=0,group='structure',extra=None):
    PLACEMENTS.append({'model':name,'arena':arena,'pos':[round(x,3),round(y,3),round(z,3)],'rot':[0,0,rz],'group':group,**(extra or {})})
def box_builder(lo,hi,tex,uv=2,top=None):
    def f(m,c):m.box(lo,hi,tex,uvscale=uv,tex_top=top);c.box(lo,hi,'metal')
    return f

# The kit relies on physically modelled bevels/ribs; custom texture names are separately authored.
model('deck_tile',lambda m,c:(m.box((-2,-2,-.32),(2,2,.02),'sq_floor',uvscale=1.7),m.box((-2,-2,-.43),(2,2,-.30),'sq_steel',uvscale=1.3),c.box((-2,-2,-.43),(2,2,.02),'metal')))
model('beam_x',lambda m,c:(m.box((-4,-.32,-.38),(4,.32,.38),'sq_steel',uvscale=2),m.box((-4,-.46,.22),(4,.46,.38),'sq_steel2',uvscale=2),m.box((-4,-.46,-.38),(4,.46,-.22),'sq_steel2',uvscale=2),c.box((-4,-.46,-.38),(4,.46,.38),'metal')))
model('beam_y',lambda m,c:(m.box((-.32,-4,-.38),(.32,4,.38),'sq_steel',uvscale=2),m.box((-.46,-4,.22),(.46,4,.38),'sq_steel2',uvscale=2),m.box((-.46,-4,-.38),(.46,4,-.22),'sq_steel2',uvscale=2),c.box((-.46,-4,-.38),(.46,4,.38),'metal')))
model('column',lambda m,c:(m.box((-.55,-.55,-12),(.55,.55,0),'sq_steel',uvscale=2),m.box((-.85,-.85,-.45),(.85,.85,.1),'sq_steel2'),m.box((-.72,-.72,-11.7),(.72,.72,-11.35),'sq_steel2'),m.box((-.7,-.7,-1.0),(.7,.7,-.65),'sq_steel2'),c.box((-.85,-.85,-12),(.85,.85,.1),'metal')))
model('truss',lambda m,c:(m.box((-5,-.22,2.35),(5,.22,2.75),'sq_steel2'),m.box((-5,-.22,-2.75),(5,.22,-2.35),'sq_steel2'),m.box((-5,-.22,-2.4),(-4.65,.22,2.4),'sq_steel'),m.box((4.65,-.22,-2.4),(5,.22,2.4),'sq_steel'),*[m.box((x,-.16,-2.35),(x+.22,.16,2.35),'sq_steel',uvscale=2) for x in (-4.5,-3,-1.5,0,1.5,3,4.5)],c.box((-5,-.25,-2.8),(5,.25,2.8),'metal')))
model('rail_x',lambda m,c:(m.box((-2,-.13,0),(2,.13,.16),'sq_steel2'),m.box((-2,-.11,1.15),(2,.11,1.28),'sq_steel'),*[m.box((x-.07,-.11,.12),(x+.07,.11,1.17),'sq_steel2') for x in (-1.85,0,1.85)],c.box((-2,-.13,0),(2,.13,1.28),'metal')))
model('wall_panel',lambda m,c:(m.box((-4,-.16,0),(4,.16,12),'sq_concrete',uvscale=3),*[m.box((x,-.23,.08),(x+.20,.23,11.92),'sq_steel2') for x in (-3.8,3.6)],*[m.box((-3.75,-.2,z),(3.75,.2,z+.16),'sq_steel') for z in (3.9,7.9)],c.box((-4,-.16,0),(4,.16,12),'concrete')))
model('banner',lambda m,c:(m.box((-.65,-.08,0),(.65,.08,3.6),'sq_banner'),m.box((-.82,-.1,3.55),(.82,.1,3.72),'sq_steel2'),m.box((-.05,-.15,3.72),(.05,.15,4.2),'sq_steel'),c.box((-.65,-.08,0),(.65,.08,3.6),'metal')))
model('lamp_cyan',lambda m,c:(m.box((-1.8,-.035,-.04),(1.8,.035,.04),'sq_cyan'),m.box((-1.82,-.08,-.12),(1.82,.08,-.06),'sq_steel'),c.box((-1.82,-.08,-.12),(1.82,.08,.04),'metal')))
model('lamp_magenta',lambda m,c:(m.box((-1.8,-.035,-.04),(1.8,.035,.04),'sq_magenta'),m.box((-1.82,-.08,-.12),(1.82,.08,-.06),'sq_steel'),c.box((-1.82,-.08,-.12),(1.82,.08,.04),'metal')))
model('glass_panel',lambda m,c:(m.box((-.76,-.89,-.12),(.76,.89,-.025),'sq_glass',uvscale=.9),m.box((-.8,-.93,-.2),(.8,-.82,-.08),'sq_steel2'),m.box((-.8,.82,-.2),(.8,.93,-.08),'sq_steel2'),m.box((-.8,-.82,-.2),(-.68,.82,-.08),'sq_steel2'),m.box((.68,-.82,-.2),(.8,.82,-.08),'sq_steel2'),c.box((-.76,-.89,-.12),(.76,.89,-.025),'glass')))
model('bridge_rib',lambda m,c:(m.box((-.18,-1.5,-.48),(.18,1.5,-.12),'sq_steel2'),m.box((-.25,-1.45,-.57),(.25,1.45,-.47),'sq_steel'),c.box((-.25,-1.5,-.57),(.25,1.5,-.12),'metal')))
model('stair_step',lambda m,c:(m.box((-1.5,-.7,-.35),(1.5,.7,.02),'sq_floor'),m.box((-1.5,-.7,-.43),(1.5,.7,-.34),'sq_steel'),c.box((-1.5,-.7,-.43),(1.5,.7,.02),'metal')))
model('safety_mark',lambda m,c:(m.box((-1.5,-.07,-.015),(1.5,.07,.005),'sq_warning'),c.box((-1.5,-.07,-.015),(1.5,.07,.005),'metal')))
def rope_mesh(m,c):
    # Three counter-twisted fibre bundles around a core; faceted 3D tube, not a texture-only rope.
    m.box((-9,-.075,-.075),(9,.075,.075),'sq_rope',uvscale=1.0)
    # Three helices are swept over the long X axis and form the visible braided silhouette.
    for strand in range(3):
      base=len(m.v);N=150;S=7;turns=20;rad=.11;sr=.035
      rings=[]
      for i in range(N+1):
        t=i/N;x=-9+18*t; a=2*math.pi*turns*t+strand*2*math.pi/3
        cy=rad*math.cos(a);cz=rad*math.sin(a)
        row=[]
        for j in range(S):
          b=2*math.pi*j/S
          # section oriented in the yz plane around the helix centre
          row.append(m.vert((x,cy+sr*math.cos(b),cz+sr*math.sin(b)),(i/N*7,j/S),(168,145,112,255)))
        rings.append(row)
      mat=m.mat('sq_rope')
      for i in range(N):
        for j in range(S):m.tri(rings[i][j],rings[i][(j+1)%S],rings[i+1][(j+1)%S],mat);m.tri(rings[i][j],rings[i+1][(j+1)%S],rings[i+1][j],mat)
    c.box((-9,-.16,-.16),(9,.16,.16),'wood')
model('rope',lambda m,c:rope_mesh(m,c))
model('anchor',lambda m,c:(m.box((-.45,-.45,-1.2),(.45,.45,1.4),'sq_steel2'),m.box((-.85,-.85,-1.35),(.85,.85,-1.0),'sq_steel'),m.box((-.7,-.7,1.15),(.7,.7,1.48),'sq_steel2'),c.box((-.85,-.85,-1.35),(.85,.85,1.48),'metal')))
model('chamber_pillar',lambda m,c:(m.box((-.45,-.45,-35),(.45,.45,0),'sq_steel'),*[m.box((-.68,-.68,z),(.68,.68,z+.22),'sq_steel2') for z in (-34,-24,-14,-4)],c.box((-.68,-.68,-35),(.68,.68,0),'metal')))
model('duct',lambda m,c:(m.box((-2,-.18,-.18),(2,.18,.18),'sq_steel2'),m.box((-1.8,-.24,.2),(1.8,.24,.3),'sq_cyan'),c.box((-2,-.24,-.2),(2,.24,.3),'metal')))
model('safety_panel',lambda m,c:(m.box((-1.9,-.08,0),(1.9,.08,3.8),'sq_concrete'),m.box((-1.75,-.12,.25),(1.75,.12,.5),'sq_warning'),m.box((-1.75,-.12,3.2),(1.75,.12,3.45),'sq_warning'),c.box((-1.9,-.08,0),(1.9,.08,3.8),'metal')))

# Tug arena: split decks over a bottomless sightline; full steel space frame and suspended perimeter.
for side,sgn in [('home',-1),('ai',1)]:
  for ix in range(6):
    for iy in range(7): add('deck_tile','tug',sgn*(12+ix*4),-12+iy*4,0,group='floor')
  for x in ((-33,-21,-9) if sgn<0 else (9,21,33)):
    for y in (-16,16): add('beam_x','tug',x,y,-.8,90)
  for y in (-14,14):
    for x in range(-34,35,4):
      if (sgn<0 and x<-9) or (sgn>0 and x>9): add('rail_x','tug',x,y,.05,0,group='rail')
  for x in (-35,35): add('rail_x','tug',x,0,.05,90,group='rail')
# tall pylons, perimeter and roof trusses
for x in (-42,-21,0,21,42):
  for y in (-24,24):
    add('column','tug',x,y,0,group='structure');add('column','tug',x,y,24,group='structure')
  add('truss','tug',x,0,23,0,group='structure')
for y in (-24,-12,0,12,24): add('beam_x','tug',0,y,27,0,group='structure')
for y in (-24,24):
  for z in (0,12,24):
    for x in range(-40,41,8):add('wall_panel','tug',x,y,z,0,group='structure')
for x in (-42,42):
  for z in (0,12,24):
    for y in range(-24,25,8):add('wall_panel','tug',x,y,z,90,group='structure')
for y in (-20,-10,0,10,20):
  add('lamp_cyan','tug',-41,y,15,0,group='lighting');add('lamp_magenta','tug',41,y,15,0,group='lighting')
for x in (-9,9): add('anchor','tug',x,0,2,group='gameplay')
add('rope','tug',0,0,1.35,group='gameplay')
for x in (-36,-24,-12,12,24,36):
  for y in (-24,24): add('chamber_pillar','tug',x,y,0,group='structure')
for x in range(-36,37,12): add('banner','tug',x,-25,9,0,group='decor')

# Glass bridge chamber: two 18-step glass lanes, exposed deep structural shaft, start/end platforms.
for x in range(-14,15,4):
  for y in (-40,-36,36,40):add('deck_tile','bridge',x,y,0,group='floor')
for x in (-18,18):
  for y in range(-48,49,4): add('deck_tile','bridge',x,y,-1,group='floor')
for lane_x in (-1.25,1.25):
  for i in range(18):
    y=-32+i*3.8
    add('glass_panel','bridge',lane_x,y,0,group='gameplay',extra={'panel':i,'lane':-1 if lane_x<0 else 1})
    add('bridge_rib','bridge',lane_x,y,-.04,0,group='structure')
    # restrained lane-edge markers: alternating chroma guide lights, no color-on-everything effect.
    add('lamp_cyan' if i%3 else 'lamp_magenta','bridge',lane_x,y-.9,.12,0,group='lighting')
for i in range(19):
  y=-34+i*3.8
  for x in (-2.7,2.7):
    add('beam_y','bridge',x,y,-.7,0,group='structure')
for x in (-4.5,4.5):
  for y in (-38,-20,0,20,38):
    add('chamber_pillar','bridge',x,y,10,group='structure');add('chamber_pillar','bridge',x,y,45,group='structure')
for y in (-50,50):
  for z in (-30,-18,-6,6,18,30):
    for x in range(-16,17,8): add('wall_panel','bridge',x,y,z,0,group='structure')
for x in (-20,20):
  for z in (-30,-18,-6,6,18,30):
    for y in range(-48,49,8): add('wall_panel','bridge',x,y,z,90,group='structure')
for z in (-30,-20,-10,0,10,20,30):
  for y in (-40,-20,0,20,40): add('beam_x','bridge',0,y,z,group='structure')
for y in (-42,42):
  for x in (-18,-9,0,9,18): add('truss','bridge',x,y,24,0,group='structure')
for y in (-46,-36,36,46):
  for z in (0,8,16,24,32):add('lamp_cyan' if y in (-46,46) else 'lamp_magenta','bridge',0,y,z,0,group='lighting')
for i in range(8): add('safety_mark','bridge',-12+i*3.4,-41,0,0,group='decor')
for y in (-30,-15,0,15,30): add('banner','bridge',-19,y,22,90,group='decor')

# ensure every placement references a valid generated model and the local coordinate budget is sane
for p in PLACEMENTS:
  if p['model'] not in MODELS: raise AssertionError(p)
  if max(abs(v) for v in p['pos'])>180: raise ValueError('placement outside intended arena bounds: '+str(p))

(ROOT/'resource'/'data').mkdir(parents=True,exist_ok=True)
manifest={'schema':'project_squid_arena/1','coordinate_system':'meters; z-up; origin offset added from shared config','model_base':15000,'arenas':{},'models':MODELS,'placements':PLACEMENTS,'stats':{'models':len(MODELS),'instances':len(PLACEMENTS),'vertices':sum(m['vertices'] for m in MODELS.values()),'triangles':sum(m['triangles'] for m in MODELS.values())}}
from config import ARENAS
manifest['arenas']=ARENAS
(ROOT/'resource'/'data'/'world.json').write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
print('Generated',manifest['stats'])
