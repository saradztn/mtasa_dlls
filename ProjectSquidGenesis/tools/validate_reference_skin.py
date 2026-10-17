"""Detect detached/exploded rigid reference segments under actor transforms.
Not a final weighted skin quality or target GTA character validation.
"""
from pathlib import Path
import bpy,json,math,hashlib
from mathutils import Vector,Euler
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'source_assets/animations/GenesisAnimations.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['GenesisHumanoid']
manifest=json.loads((ROOT/'source_assets/animations/manifest.json').read_text());worst=0;count=0
for clip in manifest:
    rig.animation_data.action=bpy.data.actions[clip['name']]
    for t in [0,.5,1]:
        bpy.context.scene.frame_set(round(1+t*(clip['frames'][1]-1)))
        for transform in [False,True]:
            rig.location=(.25,.44,.1) if transform else (0,0,0);rig.rotation_euler=(0,0,.3) if transform else (0,0,0)
            bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
            for ob in bpy.context.scene.objects:
                if ob.type!='MESH':continue
                assert ob.parent==rig and ob.modifiers['Skin'].object==rig
                bone_name=ob.vertex_groups[0].name;bone=rig.pose.bones[bone_name]
                evaluated=ob.evaluated_get(graph);mesh=evaluated.to_mesh()
                actual=evaluated.matrix_world@(sum((v.co for v in mesh.vertices),Vector())/len(mesh.vertices))
                evaluated.to_mesh_clear();expected=rig.matrix_world@((bone.head+bone.tail)/2)
                error=(actual-expected).length;worst=max(worst,error);count+=1
assert worst<.0001,worst
result={'status':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'segment_pose_samples':count,'max_segment_centroid_error_m':worst,'tolerance_m':.0001,'scope':'Rigid segmented reference mesh follows source bones under actor translation/rotation; not continuous skin, anatomical realism, foot surface collision or GTA skin validation'}
(ROOT/'tests/reference_skin_results.json').write_text(json.dumps(result,indent=2));print(result)
