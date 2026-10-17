#!/usr/bin/env python3
"""Static checks on actual exported RenderWare files and Lua syntax; not an in-game test."""
from pathlib import Path
import sys,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
if len(sys.argv)<2:raise SystemExit('usage: validate.py RESOURCE_DIR')
R=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT/'vendor/DragonFF'))
from gtaLib import dff as gdff,col as gcol,txd as gtxd
from luaparser import ast as lua_ast
errors=[];checks=[]
def check(ok,label,detail=''):
 checks.append((bool(ok),label,detail))
 if not ok:errors.append(label+(': '+detail if detail else ''))

world_path=R/'data/world.json'
try:W=json.loads(world_path.read_text(encoding='utf8'))
except Exception as e:raise SystemExit('Could not read generated world manifest: '+str(e))
check(len(W.get('models',{}))>0,'model manifest not empty')
model_names=set(W['models']);texture_sets={}
for n,rec in W['models'].items():
 for key in ('dff','col'):
  if not (R/rec[key]).is_file():errors.append(f'{n}: missing {key} {rec[key]}')
 try:
  d=gdff.dff();d.load_file(str(R/rec['dff']));g=d.clumps[0].geometry_list[0]
  check(len(g.vertices)>0 and len(g.triangles)>0,n+' DFF parse')
  tex=set()
  for m in g.materials:
   for t in m.textures:tex.add(t.name.lower())
  texture_sets[n]=tex
 except Exception as e:errors.append(f'{n}: DFF parse: {e}')
 try:
  c=gcol.coll();c.load_file(str(R/rec['col']));cm=c.models[0]
  check(len(cm.boxes)+len(cm.mesh_faces)>0,n+' collision parse/nonempty')
 except Exception as e:errors.append(f'{n}: COL parse: {e}')
for group,path in [('main','textures/squid_arena.txd')]:
 try:
  t=gtxd.txd();t.load_file(str(R/path));texture_sets[group]={x.name.lower() for x in t.native_textures}
  check(len(texture_sets[group])>=8,'TXD texture dictionary parses')
 except Exception as e:errors.append('TXD parse: '+str(e))
all_txd=texture_sets.get('main',set())
for n,refs in texture_sets.items():
 if n!='main':
  missing=refs-all_txd
  if missing:errors.append(n+': missing textures '+','.join(sorted(missing)))
for i,p in enumerate(W.get('placements',[])):
 if p.get('model') not in model_names:errors.append(f'placement {i} references absent model {p.get("model")}')
 if p.get('arena') not in W.get('arenas',{}):errors.append(f'placement {i} references absent arena')
check(len(W['placements'])>100,'substantial placed geometry',str(len(W['placements'])))
try:
 meta=ET.parse(R/'meta.xml').getroot()
 for f in meta.findall('file'):
  if not (R/f.attrib['src']).is_file():errors.append('meta missing '+f.attrib['src'])
 for s in meta.findall('script'):
  if not (R/s.attrib['src']).is_file():errors.append('meta missing script '+s.attrib['src'])
 check(meta.tag=='meta','resource meta.xml valid XML')
except Exception as e:errors.append('meta.xml parse: '+str(e))
for p in (R/'client').glob('*.lua'):
 try:lua_ast.parse(p.read_text(encoding='utf8'));check(True,'Lua syntax '+p.name)
 except Exception as e:errors.append(p.name+' Lua parse: '+str(e))
for p in list((R/'server').glob('*.lua'))+list((R/'shared').glob('*.lua')):
 try:lua_ast.parse(p.read_text(encoding='utf8'));check(True,'Lua syntax '+p.relative_to(R).as_posix())
 except Exception as e:errors.append(p.name+' Lua parse: '+str(e))
print('Static asset validation:',len(W['models']),'models,',len(W['placements']),'placements,',len(W['arenas']),'arenas')
print('PASS:',sum(1 for a,_,_ in checks if a),'FAILED:',len(errors))
for e in errors:print('FAIL:',e)
print('NOTE: static validation cannot prove shader compilation, MTA resource loading, game collision, or in-game visuals.')
sys.exit(bool(errors))
