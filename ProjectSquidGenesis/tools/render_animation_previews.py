"""Render real source actions on the skinned reference mannequin, not generated imagery.
Optional diagnostics only; GIFs do not certify animator quality or GTA playback.
"""
from pathlib import Path
import bpy,json,hashlib,tempfile,math,argparse
from mathutils import Vector
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--clip',choices=['TW_PullLoop','TW_StrongPull','GB_CautiousWalk','GB_Jump']);p.add_argument('--single-frame',action='store_true');args=p.parse_args()
source=ROOT/'source_assets/animations/GenesisAnimations.blend';bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;rig=bpy.data.objects['GenesisHumanoid']
manifest={c['name']:c for c in json.loads((ROOT/'source_assets/animations/manifest.json').read_text())};contracts=json.loads((ROOT/'source_assets/animations/contact_contracts.json').read_text())
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.6;return m
body=mat('Reference mannequin',(.28,.34,.4));floor=mat('Contact plane',(.075,.085,.10));grid=mat('Half-metre grid',(.15,.17,.2));rope_mat=mat('Guide rope',(.27,.16,.065))
for ob in list(scene.objects):
    if ob.type=='MESH':ob.data.materials.clear();ob.data.materials.append(body)
bpy.ops.mesh.primitive_plane_add(size=10);plane=bpy.context.object;plane.name='QA ground';plane.data.materials.append(floor)
for x in range(-6,7):
    for axis in [0,1]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x*.5 if axis==0 else 0,0 if axis==0 else x*.5,.001));ob=bpy.context.object;ob.scale=(.003,3,.001) if axis==0 else (3,.003,.001);ob.data.materials.append(grid)
curve=bpy.data.curves.new('QA rope guide','CURVE');curve.dimensions='3D';curve.bevel_depth=.066;curve.bevel_resolution=2;curve.use_fill_caps=True;spline=curve.splines.new('POLY');spline.points.add(1);spline.points[0].co=(0,-.4,1.05,1);spline.points[1].co=(0,1.2,1.05,1)
rope=bpy.data.objects.new('QA rope guide',curve);scene.collection.objects.link(rope);curve.materials.append(rope_mat)
camd=bpy.data.cameras.new('QA camera');cam=bpy.data.objects.new('QA camera',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.lens=48
for name,pos,power,color in [('Key',(2,1,4),400,(1,.9,.8)),('Fill',(-2,1,3),200,(.5,.8,1)),('Rim',(0,-3,3),250,(.8,.3,.6))]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=3;ld.color=color;ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.085,.12,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4;scene.cycles.use_denoising=True;scene.render.resolution_x=480;scene.render.resolution_y=360;scene.render.resolution_percentage=100
out=ROOT/'docs/animation_previews';out.mkdir(exist_ok=True);records=[]
for name in ([args.clip] if args.clip else ['TW_PullLoop','TW_StrongPull','GB_CautiousWalk','GB_Jump']):
    c=manifest[name];rig.animation_data.action=bpy.data.actions[name];rope.hide_render=not name.startswith('TW')
    n=1 if args.single_frame else round(c['seconds']*6);frames=[];sample_times=[]
    with tempfile.TemporaryDirectory(prefix='genesis-animation-') as temp:
        for i in range(n):
            t=.5 if args.single_frame else i/n if c['loop'] else i/(n-1)
            frame=1+t*(c['frames'][1]-1);scene.frame_set(int(frame),subframe=frame-int(frame))
            travel=Vector(contracts['clips'][name]['virtual_actor_translation_per_cycle'])*t
            rig.location=travel;cam.location=Vector((3.3,2.8,2.2))+travel;cam.rotation_euler=(Vector((0,.1,.9))+travel-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
            scene.render.filepath=str(Path(temp)/'frame.png');bpy.ops.render.render(write_still=True)
            image=Image.open(scene.render.filepath).convert('RGB');draw=ImageDraw.Draw(image);draw.rectangle((0,0,480,43),fill=(10,15,22));font=ImageFont.load_default(size=12)
            draw.text((12,6),name+' / SOURCE RIG / Blender inspection',fill=(190,220,240),font=font)
            label='virtual actor drive: +0.88 m/cycle' if name=='GB_CautiousWalk' else 'proxy contact study / no GTA playback validation'
            draw.text((12,25),label,fill=(190,190,195),font=font);frames.append(image.quantize(colors=64));sample_times.append(t)
    path=out/(name+('.png' if args.single_frame else '.gif'))
    durations=[(round((i+1)*c['seconds']*100/n)-round(i*c['seconds']*100/n))*10 for i in range(n)]
    if args.single_frame:frames[0].save(path)
    else:frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2)
    encoded=Image.open(path);encoded_durations=[]
    for frame_index in range(getattr(encoded,'n_frames',1)):
        encoded.seek(frame_index);encoded_durations.append(encoded.info.get('duration',0))
    records.append({'name':name,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'frames':getattr(encoded,'n_frames',1),'rendered_samples':n,'playback_duration_ms':sum(encoded_durations),'frame_durations_ms':encoded_durations,'render_sample_durations_ms':durations,'normalized_sample_times':sample_times,'dimensions':[480,360],'palette_limit':64})
    encoded.close()
if not args.single_frame:
    (ROOT/'tests/animation_preview_results.json').write_text(json.dumps({'status':'PASS','scope':'Actual source-rig render output only; does not prove target-rig compatibility, biomechanics, skinned sole collision or finger grasp','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'previews':records},indent=2))
print('Rendered',len(records),'actual source-motion previews')
