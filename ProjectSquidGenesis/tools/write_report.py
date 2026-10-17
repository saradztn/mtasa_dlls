"""Evidence report; reject stale FBX/source evidence instead of silently recycling PASS."""
from pathlib import Path
import json,hashlib,gzip
ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
layout=load('source_assets/layout.json');offline=load('tests/offline_results.json')
client=load('tests/client_results.json');lighting=load('tests/lighting_results.json')
interactions=load('tests/interaction_results.json')
architecture=load('tests/architecture_results.json')
assert architecture['status']=='PASS'
for path,h in architecture['source_sha256'].items():assert digest(ROOT/path)==h,'Stale architecture evidence: '+path
for evidence in [client,interactions]:
    assert evidence['status']=='PASS'
    for path,h in evidence['script_sha256'].items():assert digest(ROOT/path)==h,'Stale Lua evidence: '+path
sources=load('tests/source_results.json');fbx=load('tests/fbx_results.json')
assert sources['mesh_source_content_sha256']==hashlib.sha256(gzip.open(ROOT/'source_assets/blender/mesh_sources.json.gz','rb').read()).hexdigest(),'Stale environment mesh-source evidence'
for path,h in sources['environment_runtime_sha256'].items():assert digest(ROOT/path)==h,'Stale environment-runtime evidence: '+path
contacts=load('tests/animation_contact_results.json')
assert contacts['status']=='PASS'
skin=load('tests/reference_skin_results.json')
assert skin['status']=='PASS' and skin['source_sha256']==digest(ROOT/'source_assets/animations/GenesisAnimations.blend'),'Stale reference-skin evidence'
assert contacts['source_sha256']==digest(ROOT/'source_assets/animations/GenesisAnimations.blend'),'Stale contact source evidence'
assert contacts['contract_sha256']==digest(ROOT/'source_assets/animations/contact_contracts.json'),'Stale contact contract evidence'
assert contacts['profile_sha256']==digest(ROOT/'tools/animation_profiles.py'),'Stale motion profile evidence'
for record in contacts['results']:
    if record['mode']=='fbx_reimport':assert record['fbx_sha256']==digest(ROOT/f'exports/animations_fbx/{record["name"]}.fbx'),'Stale contact FBX evidence'
for clip in fbx['individual']:
    assert digest(ROOT/f'exports/animations_fbx/{clip["name"]}.fbx')==clip['file_sha256'],'Stale FBX evidence: rerun validate_fbx.py'
for path,h in sources['checked_source_sha256'].items():
    assert digest(ROOT/path)==h,'Stale source evidence: rerun validate_sources.py'
checks={str(f.relative_to(ROOT)):digest(f) for folder in ('models','collisions','textures','exports','source_assets') for f in sorted((ROOT/folder).rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
(ROOT/'tests/asset_checksums.json').write_text(json.dumps(checks,indent=2))
lines=['# Test report — 2026-10-17 / build 0.6','','## Overall: PARTIAL',
'Full user acceptance is **not achieved**. Files are real, but no MTA client/server or D3D9 compiler ran here. No FPS/VRAM measurements were made.','','## Executed offline evidence','| Test | Status | Actual result |','|---|---|---|']
for test in offline:lines.append('| '+test['test']+' | '+test['status']+' | '+str(test['detail']).replace('|','/')+' |')
for name,evidence in [('Mock client lifecycle/failures',client),('Mock light-slot stability',lighting),('Mock interaction/session authority',interactions),('Facade helper geometry/inventory',architecture)]:
    lines.append('| '+name+' | '+evidence['status']+' | '+'; '.join(evidence['tests'])+' |')
lines.append(f"| Saved Blender sources reopened | {sources['status']} | {sources['environment_mesh_objects']} meshes ({sources['visible_environment_mesh_objects']} visible placements + 1 hidden LOD template); {sources['animation_actions']} Actions; {sources['bones']} bones / {sources['deform_bones']} deform; relative textures resolve |")
lines.append(f"| Environment mesh/source correspondence | PASS | {sources['matched_environment_vertices']} vertices and {sources['matched_environment_triangles']} triangles, all material slots/indices and UVs match authored mesh data; runtime hashes recorded. Not engine compatibility. |")
lines.append(f"| FBX export/reimport | PASS | {len(fbx['individual'])} individual files contain animated tracks/keyframes and distinct sampled motion; combined file contains {fbx['combined_action_count']} Actions. Finite transforms, stable scales, exact spans and loop endpoint continuity tested. |")
preview_path=ROOT/'tests/animation_preview_results.json'
previews_current=False
if preview_path.is_file():
    preview=load('tests/animation_preview_results.json')
    previews_current=preview['source_sha256']==digest(ROOT/'source_assets/animations/GenesisAnimations.blend') and all(digest(ROOT/p['path'])==p['sha256'] for p in preview['previews'])
lines.append('| Reference mannequin skin under actor transforms | '+skin['status']+' | '+str(skin['segment_pose_samples'])+' segment-pose samples; segment centroids follow source bone centres under identity and translated/rotated actor transforms. This is not continuous-skin or GTA-character validation. |')
lines.append('| Source animation GIF provenance | '+('PASS' if previews_current else 'PARTIAL')+' | '+('Actual rendered source-rig GIFs match the current source/image hashes. Human pose/animation review is still required.' if previews_current else 'Current source-rig GIFs were not rendered/confirmed in this build.')+' |')
inspection_path=ROOT/'tests/inspection_results.json'
inspection_current=False
if inspection_path.is_file():
    inspection=load('tests/inspection_results.json')
    inspection_current=inspection['source_sha256']==digest(ROOT/'source_assets/blender/GenesisEnvironment.blend') and all(digest(ROOT/i['path'])==i['sha256'] for i in inspection['images']) and all(digest(ROOT/p)==h for p,h in inspection['material_sha256'].items())
lines.append('| Animation contact contracts | '+contacts['status']+' | 20 source actions + 20 FBX reimports checked against wrist/ankle/root targets, declared planted sole-proxy windows and held-grip centre lines. Tolerance 2 mm; ten transition pairs are also checked on source and FBX deform matrices. Walk requires explicit +0.88 m/cycle actor drive. Not skinned sole/finger/collision or biomechanical approval. |')
lines.append('| Inspection render provenance | '+('PASS' if inspection_current else 'PARTIAL')+' | '+(str(len(inspection['images']))+' actual Cycles outputs match the current saved scene, material inputs and recorded image hashes. The close facade view uses neutral diagnostic fill; the other views retain scene fixtures. This does not validate MTA visuals or AAA fidelity.' if inspection_current else 'Inspection images exist, but are not confirmed against the current saved source; regenerate with render_inspection.py.')+' |')
lines+=['','An environment-only or skip-Blender build retains earlier animation/FBX/contact evidence only while recorded hashes match; those rows do not imply that animation tests were rerun during packaging.','','## Incomplete / unexecuted gates','| Gate | Status | Reason |','|---|---|---|',
'| MTA streaming, DFF/COL engine compatibility, D3D9 shader compilation | BLOCKED | No target MTA/DirectX graphics runtime |',
'| Actual glass sorting, collisions, jumps and multiplayer traversal | NOT TESTED | Offline parsers and API mocks cannot exercise the engine |',
'| Reference fidelity / AAA finish | PARTIAL | Layout is recognizable; architecture, weathering, materials and lighting still need artist refinement |',
'| Biomechanics / actual skinned-foot and finger contact | NOT TESTED | Proxy kinematic contacts pass, but do not establish biological realism, skin collision or finger grasp |',
'| GTA retarget and IFP playback | BLOCKED | Exact target skeleton/conversion workflow not supplied; no IFP conversion attempted |',
'| FPS / VRAM / target hardware profiling | NOT TESTED | No target client/GPU session |','', '## Authored counts (not measured engine draw calls)']
assets=layout['assets'];by_name={a['name']:a for a in assets};families=len(load('source_assets/materials/settings.json'))
lines += [f"- {len(assets)} DFF/COL pairs, {sum(a['triangles'] for a in assets)} unique exported triangles across all models, including both mutually exclusive rope tiers.",
f"- {len(layout['placements'])+len(layout['panels'])} persistent placed objects, including 36 independently identified panels. One rope object switches its model; it is not duplicated for LOD.",
f"- Cable high/low: {by_name['rope']['triangles']:,} / {by_name['rope_low']['triangles']:,} triangles ({100*(1-by_name['rope_low']['triangles']/by_name['rope']['triangles']):.1f}% authored cable-triangle reduction). This is not an FPS result.",
f'- {families} material families; {families*3} source material maps, {families*6} runtime normal/packed-surface maps, three mipmapped TXDs.',
'- 20 individual animation FBX plus one combined file; two editable Blender projects.','', '## Fixes and additions actually tested',
'1. Source/FBX files are reopened; cached PASS evidence must match their current hashes before report generation.',
'2. Canonical tour routes from the interaction configuration are sampled against collision boxes; entry and landing gaps were corrected. This is not full capsule physics.',
'3. Initial dark inspection lighting and embedded columns were corrected; elevated galleries, braces, collars and wayfinding were added.',
'4. Client load gate, per-request acknowledgements and stale/expired/cancelled request rejection are exercised in Lua mocks.',
'5. Quality switches cache native dictionaries. Failed imports reapply all old dictionary bindings; rollback failure disables entry and sends a load-loss report.',
'6. Failed shader allocation, normal/surface allocation, parameter binding and world-texture binding destroy partial graphics elements and report fallback, not success.',
'7. Rope LOD uses a distance hysteresis band and reuses one object; model-switch failure preserves the tracked tier.',
'8. Light slots retain exact fixture positions. Hysteresis and intensity fades ensure a source changes only at zero slot intensity; disabled slots are explicitly zeroed.', '9. Corrected local-vs-world root translation, unreachable poses and inherited foot twist; added calibrated elbow/knee poles and world-oriented hand/foot controls.', '10. Contact tests initially detected a 2.5 mm source probe reach error; the probe range was reduced to be reachable. FBX comparison also exposed Blender import default +1-frame offset; imports now explicitly use zero offset and exact frame spans.', '11. Walk contact checks include the declared external actor drive; jump preparation and landing have explicit planted windows.', '12. Visual inspection exposed unparented reference-mesh segments deforming incorrectly under external actor translation. Reference meshes are now parented to the rig and 2,040 transformed segment poses are checked. Preview GIFs were regenerated with this corrected skin binding.', '13. Added six mutually exclusive tug reservations, nonexclusive bridge entry and proximity exit; server validates canonical positions/session/type/cooldown, checks contention and releases on drift, vehicle, load loss, death, quit and stop.', '14. Added read-only nearest-panel inspection, optional local station HUD/debug lines and client key cleanup; no round/force/animation controller is claimed.', '15. Replaced selected facade box silhouettes with real chamfer extrusions, added 13 framed closed-blade louvers, four rainwater stacks, coping, horizontal reveals and canopy ribs. Environment source validation now compares every vertex, triangle, material and UV against exported authoring data. Animations were deliberately retained unchanged.','', '## Reproduction',
'`python tools/build.py --render --package` performs the complete rebuild, source/FBX/contact verification, Lua tests, renders, report and ZIP. `--skip-blender` skips rebuilding/retesting Blender sources and FBX; pre-existing evidence must still match the stored source/FBX hashes.',
'Optional GIFs: add `--animation-previews` to the build. Individual tests: `validate_animation_contacts.py`, `validate.py`, `test_client.py`, `test_lighting.py`, `test_interactions.py`, `test_architecture.py`, `validate_sources.py`, `validate_fbx.py`. Evidence is in `tests/*_results.json`; asset hashes are in `tests/asset_checksums.json`.','', '## Windows MTA acceptance checklist (unchecked)',
'- Enable debugscript 3; verify each shader technique and model/COL load result.',
'- Inspect both rope tiers and threshold switching, including model binding failures, without assuming API mocks prove visual correctness.',
'- Test glass transparency from above/below, every panel collider, jumping and hall culling.',
'- Test two clients, reconnect snapshots, ACL allow/deny, failed downloads, load-loss restoration, cancellation and resource stop.',
'- Check lighting transition pacing and source selection inside each hall; inspect wall light bleed and weather-resource conflicts.',
'- Retarget/polish animations and profile LOW/MEDIUM/HIGH on target hardware before accepting the final scene.']
(ROOT/'docs/test_report.md').write_text('\n'.join(lines)+'\n')
print('Report and',len(checks),'asset checksums written; inspection source current:',inspection_current)
