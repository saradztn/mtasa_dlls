"""Run with Python bpy 4.2 LTS. Creates editable scene + IK animation source and FBX exports."""
from pathlib import Path
import bpy, json, gzip, math, hashlib, argparse
parser=argparse.ArgumentParser();parser.add_argument("--environment-only",action="store_true");args,_=parser.parse_known_args()
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
layout=json.loads((ROOT/'source_assets/layout.json').read_text());sources=json.loads(gzip.open(ROOT/'source_assets/blender/mesh_sources.json.gz','rt').read())
materials={}
for name in json.loads((ROOT/'source_assets/materials/settings.json').read_text()):
    mat=bpy.data.materials.new('psg_'+name);mat.use_nodes=True;nodes=mat.node_tree.nodes;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.65
    for kind in ('base','normal','surface'):
        im=bpy.data.images.load(str(ROOT/f'source_assets/materials/{name}_{kind}.png'));tex=nodes.new('ShaderNodeTexImage');tex.image=im
        if kind=='base':
            mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            if name=='glass':
                bs.inputs['Transmission Weight'].default_value=.65;bs.inputs['Roughness'].default_value=.13
            if name in ('cyan','pink','amber'):
                mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=3
        elif kind=='normal':
            im.colorspace_settings.name='Non-Color';nm=nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:
            im.colorspace_settings.name='Non-Color';sep=nodes.new('ShaderNodeSeparateColor');mat.node_tree.links.new(tex.outputs['Color'],sep.inputs['Color']);mat.node_tree.links.new(sep.outputs['Red'],bs.inputs['Roughness']);mat.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Metallic'])
    materials['psg_'+name]=mat
objects={}
for name,data in sources.items():
    me=bpy.data.meshes.new(name);me.from_pydata(data['v'],[],[f[:3] for f in data['f']]);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for tex in data['textures']:me.materials.append(materials[tex])
    uv=me.uv_layers.new()
    for poly,f in zip(me.polygons,data['f']):
        poly.material_index=f[3]
        for li in poly.loop_indices:u,v=data['uv'][me.loops[li].vertex_index];uv.data[li].uv=(u,1-v)
    if name=='rope_low':
        ob.hide_render=True;ob.hide_viewport=True;ob['usage']='Runtime distant / LOW cable alternative; not placed simultaneously'
    objects[name]=ob
for panel in layout['panels']:
    ob=bpy.data.objects.new(panel['id'],objects['glass_panel'].data);bpy.context.collection.objects.link(ob);ob.location=panel['position'];ob['panel_id']=panel['id']
bpy.data.objects.remove(objects['glass_panel'],do_unlink=True)
for l in layout['lights']:
    ld=bpy.data.lights.new('Fixture','POINT');ld.color=l['color'];ld.energy=6500 if l['position'][2]>19 else 1800;ld.shadow_soft_size=.6;ob=bpy.data.objects.new('Fixture light',ld);bpy.context.collection.objects.link(ob);ob.location=l['position']
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.world.color=(.025,.035,.055)
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=960;scene.render.resolution_y=640;scene.render.resolution_percentage=100
camd=bpy.data.cameras.new('Inspection');cam=bpy.data.objects.new('Inspection',camd);bpy.context.collection.objects.link(cam);cam.location=(-22,-21,9);cam.rotation_euler=(Vector((8,1,-6))-cam.location).to_track_quat('-Z','Y').to_euler();camd.lens=24;scene.camera=cam
for im in bpy.data.images:
    if im.filepath:im.filepath='//../materials/'+Path(im.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source_assets/blender/GenesisEnvironment.blend'))
# Animation authoring can also be rebuilt independently.
import runpy
if not args.environment_only:runpy.run_path(str(ROOT/'tools/build_animations.py'),run_name='__main__')
