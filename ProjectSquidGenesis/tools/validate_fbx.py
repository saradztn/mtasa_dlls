from pathlib import Path
import bpy,json,hashlib,math
ROOT=Path(__file__).resolve().parents[1];manifest=json.loads((ROOT/'source_assets/animations/manifest.json').read_text());results=[]
for clip in manifest:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path=ROOT/f'exports/animations_fbx/{clip["name"]}.fbx';bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True,anim_offset=0)
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1
    rig=rigs[0];action=rig.animation_data.action;assert action and len(action.fcurves)>20
    start,end=map(round,action.frame_range);assert [start,end]==clip['frames'],(clip['name'],start,end)
    samples=[];max_scale_error=0
    for frame in range(start,end+1):
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        vals=[]
        for b in rig.pose.bones:
            if b.name not in ('root','pelvis','spine','chest','neck','head') and not any(x in b.name for x in ('upperarm','forearm','thigh','shin','foot','hand')):continue
            vals.extend(v for row in b.matrix for v in row)
            max_scale_error=max(max_scale_error,max(abs(x-1) for x in b.scale))
        assert all(math.isfinite(v) for v in vals);samples.append(vals)
    movement=max(abs(a-b) for sample in samples for a,b in zip(samples[0],sample));assert movement>.0001,(clip['name'],'static')
    loop_error=max(abs(a-b) for a,b in zip(samples[0],samples[-1]));assert not clip['loop'] or loop_error<.0001,(clip['name'],loop_error)
    assert max_scale_error<.001,(clip['name'],max_scale_error)
    results.append({'name':clip['name'],'status':'PASS','imported_frame_range':[start,end],'curves':len(action.fcurves),'keyframes':sum(len(fc.keyframe_points) for fc in action.fcurves),'sampled_matrix_motion':movement,'loop_matrix_error':loop_error if clip['loop'] else None,'scale_error':max_scale_error,'motion_hash':hashlib.sha256(json.dumps(samples).encode()).hexdigest(),'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(ROOT/'exports/animations_fbx/Genesis_All.fbx'),anim_offset=0)
assert len(bpy.data.actions)==20,len(bpy.data.actions)
assert len({r['motion_hash'] for r in results})==20
(ROOT/'tests/fbx_results.json').write_text(json.dumps({'tool':bpy.app.version_string,'individual':results,'combined_action_count':len(bpy.data.actions),'note':'Numerical/import tests only; biomechanical and in-game quality NOT TESTED'},indent=2))
print('PASS: 20 imported animated FBX, distinct samples; loops continuous; combined has 20 actions')
