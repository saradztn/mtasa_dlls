"""Measure actual source AND reimported FBX against authored kinematic contracts.
Sole/palm points are anatomical proxies, not imported display bone tails (FBX may infer their length).
"""
from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Vector
from animation_profiles import profile
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'source_assets/animations/manifest.json').read_text())
contracts=json.loads((ROOT/'source_assets/animations/contact_contracts.json').read_text())
deform=[b['name'] for b in json.loads((ROOT/'source_assets/animations/rig.json').read_text()) if b['deform']]
boundaries={}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def marker(rig,name):
    m=contracts['markers'][name];return rig.matrix_world@(rig.pose.bones[m['bone']].matrix@Vector(m['local']))
def measure(rig,clip,mode):
    name=clip['name'];c=contracts['clips'][name];start,end=clip['frames'];samples=[];ankle_error=wrist_error=root_error=0
    for frame in range(start,end+1):
        t=(frame-start)/(end-start);bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();p=profile(name,t)
        if frame in (start,end):
            boundaries[(mode,name,'start' if frame==start else 'end')]=[v for bone in deform for row in (rig.matrix_world@rig.pose.bones[bone].matrix) for v in row]
        sample={'t':t,'markers':{k:list(marker(rig,k)) for k in contracts['markers']}}
        root_error=max(root_error,((rig.matrix_world@rig.pose.bones['root'].head)-Vector(p['root'])).length)
        for i,side in enumerate(['L','R']):
            ankle_error=max(ankle_error,((rig.matrix_world@rig.pose.bones['foot_'+side].head)-Vector(p['feet'][i])).length)
            wrist_error=max(wrist_error,((rig.matrix_world@rig.pose.bones['hand_'+side].head)-Vector(p['hands'][i])).length)
        samples.append(sample)
    drift=height=grip_error=0;contact_samples=grip_samples=0
    for side,windows in c['planted_windows_normalized'].items():
        for a,b in windows:
            window=[s for s in samples if a-1e-8<=s['t']<=b+1e-8];assert window,(name,side,a,b)
            for mark in ['heel_sole_'+side,'toe_sole_'+side]:
                points=[Vector(s['markers'][mark])+Vector(c['virtual_actor_translation_per_cycle'])*s['t'] for s in window]
                drift=max(drift,max((p-points[0]).length for p in points));height=max(height,max(abs(p.z) for p in points));contact_samples+=len(points)
    for a,b in c['grip_windows_normalized']:
        for s in samples:
            if a-1e-8<=s['t']<=b+1e-8:
                for side in ['L','R']:
                    p=Vector(s['markers']['palm_'+side]);grip_error=max(grip_error,math.hypot(p.x,p.z-1.05));grip_samples+=1
    limits={'max_ankle_target_error_m':(ankle_error,c['target_tolerance_m']),'max_wrist_target_error_m':(wrist_error,c['target_tolerance_m']),'max_root_translation_error_m':(root_error,.0001),'max_planted_sole_proxy_drift_m':(drift if contact_samples else None,c['contact_tolerance_m']),'max_planted_sole_proxy_height_error_m':(height if contact_samples else None,c['contact_tolerance_m']),'max_grip_centre_line_error_m':(grip_error if grip_samples else None,c['contact_tolerance_m'])}
    failures=[k for k,(v,tol) in limits.items() if v is not None and v>tol]
    return {'name':name,'mode':mode,'status':'FAIL' if failures else 'PASS',**{k:v[0] for k,v in limits.items()},'planted_proxy_samples':contact_samples,'grip_proxy_samples':grip_samples,'failures':failures}
results=[];source=ROOT/'source_assets/animations/GenesisAnimations.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));rig=bpy.data.objects['GenesisHumanoid']
for clip in manifest:
    rig.animation_data.action=bpy.data.actions[clip['name']];results.append(measure(rig,clip,'source'))
for clip in manifest:
    bpy.ops.wm.read_factory_settings(use_empty=True);path=ROOT/f'exports/animations_fbx/{clip["name"]}.fbx';bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True,anim_offset=0)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');result=measure(rig,clip,'fbx_reimport');result['fbx_sha256']=digest(path);results.append(result)
pairs=[('TW_GrabRope','TW_Ready'),('TW_Ready','TW_PullLoop'),('TW_PullLoop','TW_StrongPull'),('TW_StrongPull','TW_Ready'),('TW_Stumble','TW_Recovery'),('TW_Recovery','TW_PullLoop'),('TW_Ready','TW_Release'),('TW_Ready','TW_Victory'),('GB_TestPanel','GB_IdleBalance'),('GB_Hesitate','GB_IdleBalance')]
transitions=[]
for mode in ['source','fbx_reimport']:
    for a,b in pairs:
        error=max(abs(v-w) for v,w in zip(boundaries[(mode,a,'end')],boundaries[(mode,b,'start')]))
        transitions.append({'from':a,'to':b,'mode':mode,'max_deform_matrix_difference':error,'status':'PASS' if error<.0001 else 'FAIL'})
report={'status':'FAIL' if any(r['status']=='FAIL' for r in results+transitions) else 'PASS','transitions':transitions,'tool':bpy.app.version_string,'scope':'2mm proxy kinematic tests only: NOT biological realism, skinned-foot collision, fingertip grip, GTA compatibility or in-game validation','source_sha256':digest(source),'contract_sha256':digest(ROOT/'source_assets/animations/contact_contracts.json'),'profile_sha256':digest(ROOT/'tools/animation_profiles.py'),'results':results}
(ROOT/'tests/animation_contact_results.json').write_text(json.dumps(report,indent=2))
for r in results:
    print(r['mode'],r['name'],r['status'],{k:(round(v,6) if v is not None else None) for k,v in r.items() if k.startswith('max_')},r['failures'])
assert report['status']=='PASS','Animation contacts failed; inspect tests/animation_contact_results.json'
