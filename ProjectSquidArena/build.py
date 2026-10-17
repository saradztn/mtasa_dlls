#!/usr/bin/env python3
"""One-command Windows/Linux build: procedural geometry -> DFF/COL/TXD -> MTA resource."""
from pathlib import Path
import subprocess,sys,shutil,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from config import ARENAS,AI,DEFAULTS,MODEL_BASE

def lua(v):
 if isinstance(v,dict):return '{'+','.join('['+json.dumps(str(k))+']='+lua(x) for k,x in v.items())+'}'
 if isinstance(v,(list,tuple)):return '{'+','.join(lua(x) for x in v)+'}'
 if isinstance(v,str):return json.dumps(v,ensure_ascii=True)
 if isinstance(v,bool):return 'true' if v else 'false'
 return repr(v)
def write_lua_config():
 arenas={}
 for key,a in ARENAS.items():
  entry=a['entry'];ai=a['ai'];o=a['origin']
  r={'dimension':a['dimension'],'origin':{'x':o[0],'y':o[1],'z':o[2]},'entry':{'x':entry[0],'y':entry[1],'z':entry[2]},'ai':{'x':ai[0],'y':ai[1],'z':ai[2]},'deckZ':a.get('deck_z',0)}
  for pykey,luakey in [('first_panel_y','firstPanelY'),('step','step'),('steps','steps')]:
   if pykey in a:r[luakey]=a[pykey]
  arenas[key]=r
 cfg={'modelBase':MODEL_BASE,'arenas':arenas,'ai':{'tugTeamSize':AI['tug_team_size'],'tugPressurePerSecond':AI['tug_pressure_per_second'],'bridgeSkill':AI['bridge_skill']},'defaults':DEFAULTS}
 (ROOT/'resource/shared/config.lua').write_text('SQUID_CONFIG='+lua(cfg)+chr(10),encoding='utf8')

def main():
 if sys.version_info<(3,9):raise SystemExit('Python 3.9 or newer is required')
 v=ROOT/'.venv';py=v/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
 if not py.exists():subprocess.check_call([sys.executable,'-m','venv',str(v)])
 pip=v/('Scripts/pip.exe' if sys.platform=='win32' else 'bin/pip')
 subprocess.check_call([str(pip),'install','-r',str(ROOT/'requirements.txt')])
 for sub in ('resource/models','resource/collisions','resource/textures','resource/data','resource/shaders','tools/material_generator/generated','output'):(ROOT/sub).mkdir(parents=True,exist_ok=True)
 subprocess.check_call([str(py),str(ROOT/'generator/materials.py')],cwd=ROOT)
 subprocess.check_call([str(py),str(ROOT/'generator/build_assets.py')],cwd=ROOT)
 write_lua_config()
 world=json.loads((ROOT/'resource/data/world.json').read_text(encoding='utf8'))
 stage=ROOT/'output/.ProjectSquidArena-staging';dest=ROOT/'output/ProjectSquidArena'
 if stage.exists():shutil.rmtree(stage)
 shutil.copytree(ROOT/'resource',stage)
 files=[]
 for p in sorted(stage.rglob('*')):
  if p.is_file() and p.name!='meta.xml':files.append(p.relative_to(stage).as_posix())
 meta=ET.Element('meta')
 ET.SubElement(meta,'info',{'name':'ProjectSquidArena','author':'Arena project','version':'1.0.0','type':'script','description':'Tug-of-war and AI glass bridge arenas'})
 ET.SubElement(meta,'min_mta_version',{'client':'1.6.0-9.22676','server':'1.6.0'})
 for path,typ in [('shared/config.lua','shared'),('server/main.lua','server'),('server/gameplay.lua','server'),('client/main.lua','client')]:
  if not (stage/path).exists():raise FileNotFoundError(stage/path)
  ET.SubElement(meta,'script',{'src':path,'type':typ,'cache':'true'})
 for path in files:ET.SubElement(meta,'file',{'src':path,'download':'true'})
 ET.indent(meta,space='  ');ET.ElementTree(meta).write(stage/'meta.xml',encoding='utf-8',xml_declaration=True)
 ET.parse(stage/'meta.xml')
 subprocess.check_call([str(py),str(ROOT/'tests/validate.py'),str(stage)],cwd=ROOT)
 for el in meta.findall('file'):
  if not (stage/el.attrib['src']).is_file():raise FileNotFoundError(el.attrib['src'])
 if dest.exists():shutil.rmtree(dest)
 stage.rename(dest)
 report={'status':'built','resource':str(dest),'models':len(world['models']),'placed_objects':len(world['placements']),'vertices':world['stats']['vertices'],'triangles':world['stats']['triangles'],'mta_runtime_tested':False,'reason':'MTA client/server and DirectX runtime are not installed in build environment.'}
 (ROOT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print('BUILD SUCCESS:',json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
