"""Editable source rig, stable IK orientation/planes and actual deform-only FBX exports."""
from pathlib import Path
import bpy,json,math,sys
from mathutils import Vector,Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from animation_profiles import NAMES,LOOPS,duration,profile,contract
ROOT=Path(__file__).resolve().parents[1]
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
for collection in (bpy.data.meshes,bpy.data.materials,bpy.data.images,bpy.data.lights,bpy.data.cameras,bpy.data.armatures,bpy.data.actions):
    for block in list(collection):
        if block.users==0:collection.remove(block)
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0;scene.render.fps=30;scene.render.fps_base=1.0
bpy.context.preferences.filepaths.save_version=0
arm=bpy.data.armatures.new('GenesisHumanoid');rig=bpy.data.objects.new('GenesisHumanoid',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bones={}
def bone(name,h,t,parent=None,deform=True):
    b=arm.edit_bones.new(name);b.head=h;b.tail=t;b.use_deform=deform
    if parent:b.parent=bones[parent]
    bones[name]=b
bone('root',(0,0,0),(0,0,.15));bone('pelvis',(0,0,.92),(0,0,1.08),'root');bone('spine',(0,0,1.08),(0,0,1.31),'pelvis');bone('chest',(0,0,1.31),(0,0,1.5),'spine');bone('neck',(0,0,1.5),(0,0,1.6),'chest');bone('head',(0,0,1.6),(0,0,1.83),'neck')
for side,s in [('L',-1),('R',1)]:
    bone('upperarm_'+side,(s*.19,0,1.48),(s*.39,.03,1.22),'chest');bone('forearm_'+side,(s*.39,.03,1.22),(s*.43,.13,1.0),'upperarm_'+side);bone('hand_'+side,(s*.43,.13,1),(s*.43,.23,.98),'forearm_'+side)
    bone('thigh_'+side,(s*.115,0,.95),(s*.115,.06,.52),'pelvis');bone('shin_'+side,(s*.115,.06,.52),(s*.115,0,.10),'thigh_'+side);bone('foot_'+side,(s*.115,0,.10),(s*.115,.23,.07),'shin_'+side)
    bone('handIK_'+side,(s*.43,.13,1),(s*.43,.23,.98),deform=False);bone('footIK_'+side,(s*.115,0,.10),(s*.115,.23,.07),deform=False)
    bone('elbowPole_'+side,(s*.6,-.3,1.2),(s*.6,-.3,1.3),deform=False)
    bone('kneePole_'+side,(s*.16,.8,.5),(s*.16,.8,.6),deform=False)
bpy.ops.object.mode_set(mode='POSE');ik_constraints={}
for side in ['L','R']:
    for limb,target,pole in [('forearm','handIK','elbowPole'),('shin','footIK','kneePole')]:
        con=rig.pose.bones[limb+'_'+side].constraints.new('IK');con.target=rig;con.subtarget=target+'_'+side;con.chain_count=2;con.use_stretch=False;con.iterations=500
        con.pole_target=rig;con.pole_subtarget=pole+'_'+side;ik_constraints[limb+'_'+side]=con
    for end,target in [('hand','handIK'),('foot','footIK')]:
        con=rig.pose.bones[end+'_'+side].constraints.new('COPY_ROTATION');con.target=rig;con.subtarget=target+'_'+side;con.owner_space='WORLD';con.target_space='WORLD';con.mix_mode='REPLACE'
    for name in ['upperarm','forearm','thigh','shin']:rig.pose.bones[name+'_'+side].ik_stretch=0
bpy.ops.object.mode_set(mode='OBJECT')
def move(name,point,frame=None):
    pb=rig.pose.bones[name];rest=arm.bones[name]
    pb.location=rest.matrix_local.to_3x3().inverted()@(Vector(point)-rest.head_local)
    if frame is not None:pb.keyframe_insert('location',frame=frame)
def apply_pose(p,frame=None):
    pb=rig.pose.bones['root'];pb.location=arm.bones['root'].matrix_local.to_3x3().inverted()@Vector(p['root'])
    if frame is not None:pb.keyframe_insert('location',frame=frame)
    for name in ['spine','chest']:
        pb=rig.pose.bones[name];pb.rotation_mode='XYZ';pb.rotation_euler=(-p['lean']*.5,0,p['root'][0]*.12)
        if frame is not None:pb.keyframe_insert('rotation_euler',frame=frame)
    for i,side in enumerate(['L','R']):
        move('handIK_'+side,p['hands'][i],frame);move('footIK_'+side,p['feet'][i],frame)
        for pole in ['elbowPole','kneePole']:move(pole+'_'+side,arm.bones[pole+'_'+side].head_local+Vector(p['root']),frame)
        for target,angle in [('handIK',p['hand_pitch'][i]),('footIK',0)]:
            pb=rig.pose.bones[target+'_'+side];rest=arm.bones[pb.name].matrix_local.to_quaternion();pb.rotation_mode='QUATERNION'
            pb.rotation_quaternion=rest.inverted()@Quaternion((1,0,0),angle)@rest
            if frame is not None:pb.keyframe_insert('rotation_quaternion',frame=frame)
# Calibrate source bone roll once, in a reachable stance, toward each authored pole.
apply_pose(profile('TW_Ready',0));calibration={}
for name,con in ik_constraints.items():
    best=None
    for angle in [0,math.pi/2,-math.pi/2,math.pi]:
        con.pole_angle=angle;bpy.context.view_layer.update()
        joint=rig.pose.bones[name];upper=joint.parent;target=rig.pose.bones[con.subtarget].head
        axis=(target-upper.head).normalized();bend=joint.head-upper.head;bend-=axis*bend.dot(axis)
        toward=rig.pose.bones[con.pole_subtarget].head-upper.head;toward-=axis*toward.dot(axis)
        score=bend.normalized().dot(toward.normalized())
        if best is None or score>best[0]:best=(score,angle)
    con.pole_angle=best[1];calibration[name]={'angle_rad':best[1],'pole_alignment_cosine':best[0]}
bpy.context.view_layer.update()
for b in arm.bones:
    if not b.use_deform or b.name=='root':continue
    mid=(b.head_local+b.tail_local)/2;length=b.length
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,location=mid);ob=bpy.context.object;ob.name='Reference_'+b.name;ob.scale=(.10 if b.name in ['chest','pelvis','head'] else .055,.075,length*.54);ob.rotation_euler=(b.tail_local-b.head_local).to_track_quat('Z','Y').to_euler();bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    vg=ob.vertex_groups.new(name=b.name);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE');mod=ob.modifiers.new('Skin','ARMATURE');mod.object=rig;ob.parent=rig;ob.matrix_parent_inverse=rig.matrix_world.inverted()
bpy.context.view_layer.objects.active=rig
manifest=[];contracts={name:contract(name) for name in NAMES}
for name in NAMES:
    end=round(duration(name)*30)+1;act=bpy.data.actions.new(name);act.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=act
    for frame in range(1,end+1):apply_pose(profile(name,(frame-1)/(end-1)),frame)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:kp.interpolation='LINEAR'
    scene.frame_start=1;scene.frame_end=end;scene.frame_set(1);bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT/f'exports/animations_fbx/{name}.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',apply_unit_scale=True)
    manifest.append({'name':name,'frames':[1,end],'fps':30,'seconds':duration(name),'loop':name in LOOPS,'source':'procedural IK with contact contracts; animator/GTA review outstanding','root_motion':name in ['TW_Stumble','TW_Recovery','TW_Fall','GB_ShortStep','GB_Jump','GB_Fall','GB_Slip'],'recommended_actor_translation_per_cycle':contracts[name]['virtual_actor_translation_per_cycle']})
rig.animation_data.action=bpy.data.actions['TW_PullLoop'];scene.frame_start=1;scene.frame_end=61;scene.frame_set(1)
rig['forward']='+Y';rig['up']='+Z';rig['unit']='metre';rig['note']='Custom rig; no GTA/IFP compatibility claim';rig['pole_calibration']=json.dumps(calibration)
root=ROOT/'source_assets/animations'
(root/'rig.json').write_text(json.dumps([{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local),'deform':b.use_deform} for b in arm.bones],indent=2))
markers={}
for side in ['L','R']:
    foot=arm.bones['foot_'+side];rot=foot.matrix_local.to_3x3()
    markers['heel_sole_'+side]={'bone':foot.name,'local':list(rot.inverted()@Vector((0,0,-.10))),'purpose':'proxy sole; not skinned-mesh collision'}
    markers['toe_sole_'+side]={'bone':foot.name,'local':list(rot.inverted()@Vector((0,.23,-.10))),'purpose':'proxy sole; not skinned-mesh collision'}
    hand=arm.bones['hand_'+side];markers['palm_'+side]={'bone':hand.name,'local':[0,hand.length*.5,0],'purpose':'grip centre proxy; no fingers'}
(root/'contact_contracts.json').write_text(json.dumps({'version':'0.4','space':'metres / rig world +Y forward +Z up','scope':'proxy kinematic constraints, not biological/mesh/collision approval','markers':markers,'clips':contracts},indent=2))
(root/'export_settings.json').write_text(json.dumps({'fps':30,'axis_forward':'-Z','axis_up':'Y','deform_only':True,'leaf_bones':False,'bake_step':1,'simplify':0,'root_translation_input':'world converted through inverse root rest basis','pole_calibration':calibration},indent=2))
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(root/'GenesisAnimations.blend'))
bpy.ops.export_scene.fbx(filepath=str(ROOT/'exports/animations_fbx/Genesis_All.fbx'),use_selection=True,object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y')
print('Exported 20 contact-authored clips and combined FBX; pole calibration:',calibration)

import runpy
runpy.run_path(str(ROOT/'tools/write_animation_manifest.py'),run_name='__main__')
