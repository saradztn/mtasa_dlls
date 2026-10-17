from pathlib import Path
import bpy,json,hashlib,argparse
parser=argparse.ArgumentParser();parser.add_argument("--view",choices=["tug","glass","exterior","exterior_detail"]);args=parser.parse_args()
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source_assets/blender/GenesisEnvironment.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.resolution_x=900;s.render.resolution_y=600;s.render.resolution_percentage=100
s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.035,.06,.1,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
out=ROOT/'docs/inspection';out.mkdir(exist_ok=True)
source=ROOT/'source_assets/blender/GenesisEnvironment.blend'
material_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'source_assets/materials').iterdir()) if p.suffix in ('.png','.json')}
if args.view:
    old=json.loads((ROOT/'tests/inspection_results.json').read_text())
    assert old['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest() and old['material_sha256']==material_hashes,'Partial render requires unchanged scene/material inputs; render all views first'
    assert all(hashlib.sha256((ROOT/i['path']).read_bytes()).hexdigest()==i['sha256'] for i in old['images']),'Partial render requires intact previous views'
for name,pos,target,lens in [('tug',(-24,-19,7),(8,2,-8),23),('glass',(43,-22,5),(46,25,-4),23),('exterior',(90,-110,45),(10,-4,10),32),('exterior_detail',(9,-57,16),(5,-26,18),40)]:
    if args.view and args.view!=name:continue
    if name=='exterior_detail':
        ld=bpy.data.lights.new('Diagnostic neutral fill','AREA');ld.energy=12000;ld.shape='DISK';ld.size=12
        fill=bpy.data.objects.new('Diagnostic neutral fill',ld);bpy.context.collection.objects.link(fill);fill.location=(7,-39,24);fill.rotation_euler=(Vector((5,-26,16))-fill.location).to_track_quat('-Z','Y').to_euler()
    s.camera.location=pos;s.camera.rotation_euler=(Vector(target)-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=lens;s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)

source=ROOT/'source_assets/blender/GenesisEnvironment.blend'
report={'status':'PASS','tool':'Blender '+bpy.app.version_string+' / CPU Cycles 16 samples','scope':'Inspection renders only, NOT MTA screenshots or a reference-match acceptance test. exterior_detail uses a neutral AREA inspection fill, not part of runtime lighting.','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'material_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'source_assets/materials').iterdir()) if p.suffix in ('.png','.json')},'images':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'dimensions':[900,600],'neutral_inspection_fill':p.stem=='exterior_detail'} for p in sorted(out.glob('*.png'))]}
(ROOT/'tests/inspection_results.json').write_text(json.dumps(report,indent=2))
