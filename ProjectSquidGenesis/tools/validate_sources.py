from pathlib import Path
import bpy,json,hashlib,gzip,math
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source_assets/blender/GenesisEnvironment.blend'))
layout=json.loads((ROOT/'source_assets/layout.json').read_text())
assert sum(o.type=='MESH' for o in bpy.context.scene.objects)==len(layout['assets'])-1+len(layout['panels'])
assert bpy.data.objects['rope_low'].hide_render and bpy.data.objects['rope_low'].hide_viewport
mesh_bytes=gzip.open(ROOT/'source_assets/blender/mesh_sources.json.gz','rb').read()
mesh_sources=json.loads(mesh_bytes);matched_vertices=0;matched_triangles=0
for name,data in mesh_sources.items():
    ob=bpy.data.objects[layout['panels'][0]['id'] if name=='glass_panel' else name];me=ob.data
    assert len(me.vertices)==len(data['v']) and len(me.polygons)==len(data['f']),name
    for vert,expected in zip(me.vertices,data['v']):assert math.dist(vert.co,expected)<.00001,(name,'vertex')
    assert [mat.name for mat in me.materials]==data['textures'],name
    for poly,face in zip(me.polygons,data['f']):
        assert tuple(poly.vertices)==tuple(face[:3]) and poly.material_index==face[3],(name,'face')
        for li in poly.loop_indices:
            u,v=data['uv'][me.loops[li].vertex_index]
            assert math.dist(me.uv_layers.active.data[li].uv,(u,1-v))<.00002,(name,'UV')
    matched_vertices+=len(me.vertices);matched_triangles+=len(me.polygons)

assert sum(o.type=='MESH' and not o.hide_render for o in bpy.context.scene.objects)==len(layout['placements'])+len(layout['panels'])
for image in bpy.data.images:
    if image.source=='FILE':assert Path(bpy.path.abspath(image.filepath)).is_file(),image.filepath
assert all(o.data.uv_layers for o in bpy.context.scene.objects if o.type=='MESH')
environment_meshes=sum(o.type=='MESH' for o in bpy.context.scene.objects)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source_assets/animations/GenesisAnimations.blend'))
rig=bpy.data.objects['GenesisHumanoid'];assert rig.type=='ARMATURE';assert len(bpy.data.actions)==20
assert sum(o.type=='MESH' for o in bpy.context.scene.objects)==17
assert all(o.parent==rig and o.modifiers.get('Skin') and len(o.vertex_groups)==1 for o in bpy.context.scene.objects if o.type=='MESH')
results={'status':'PASS','blender':bpy.app.version_string,'environment_mesh_objects':environment_meshes,'animation_actions':len(bpy.data.actions),'bones':len(rig.data.bones),'deform_bones':sum(b.use_deform for b in rig.data.bones),'skinned_reference_segments':17,'relative_textures_resolve':True,'matched_environment_vertices':matched_vertices,'matched_environment_triangles':matched_triangles,'mesh_source_content_sha256':hashlib.sha256(mesh_bytes).hexdigest(),'environment_runtime_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['models','collisions'] for p in sorted((ROOT/d).glob('*')) if p.is_file()},'visible_environment_mesh_objects':len(layout['placements'])+len(layout['panels']),'hidden_lod_templates':1,'checked_source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'source_assets/blender/GenesisEnvironment.blend',ROOT/'source_assets/animations/GenesisAnimations.blend']},'scope':'Source structure only, not art quality'}
(ROOT/'tests/source_results.json').write_text(json.dumps(results,indent=2));print(results)
