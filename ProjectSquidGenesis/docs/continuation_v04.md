# Continuation v0.4 — measured animation-contact pass

## Issues actually found, not just assumed
Historical source measurements are recorded in `tests/animation_baseline_v03.json`, bound to the previous source file hash. Several nominal stance clips had centimetre-scale ankle-target misses; inherited foot rotation caused roughly 0.148 m of toe-bone motion in the pull loop and 0.211 m in strong pull. Those legacy toe-bone measurements are not directly the same metric as the new sole proxies; they explain why stable ankle targets alone were insufficient.

The root bone's local axes were not the scene axes: assigning a nominal world Z offset directly to `pose_bone.location.z` moved the body along another scene axis. Some poses also requested targets outside limb reach. The earlier import/loop tests had not checked those issues.

## Fixes authored
- Motion is now defined in explicit metre-space profiles in `tools/animation_profiles.py`. Root input passes through the inverse root rest basis; actual root world displacement is tested.
- Two-bone arm/leg IK uses four explicit pole controls with measured bone-roll calibration. Foot/hand world orientation is constrained before FBX bake, so the feet no longer inherit shin twist.
- Stance height, pull travel, probe distance and victory reach are within the rig's limb ranges. Both grip proxies lie on one +Y source rope centre line at X=0, Z=1.05.
- Step/probe/recovery trajectories lift the moving foot. The panel test has a declared forward contact interval. Jump has preparation, flight and planted landing phases. Intentional slips and falls are not mislabeled planted contact.
- Cautious walk has an explicit +0.88 m/three-second actor-drive contract. Swing endpoint velocities match the in-place stance trajectory. This external drive must be applied by the consumer; it is not secretly baked as locomotion into the in-place root.
- All 20 individual FBX files and the 20-action combined file were regenerated. No IFP was created.

## Stronger tests
`validate_animation_contacts.py` samples actual evaluated source bones and actual reimported FBX bones every frame. It compares wrist/ankle targets and world-root motion; computes heel/toe **sole proxy** drift and plane error only in declared planted windows; and measures palm-centre distance to the source rope line only in declared grip windows. Non-applicable contact metrics are null, not fictional zero-error tests.

Contact tolerance is 2 mm. Numerical tests are constrained by the source rig and proxy definitions; they do not sample skinned foot geometry, finger surfaces, environmental collisions, force balance or biological realism.

Ten explicitly supported transition pairs are compared on full deform-bone matrices in each representation (20 comparisons). This does not claim all possible state transitions are seamless; resistance/idle and locomotion transitions still need deliberate blending/retarget handling.

During the new checks, the first probe trajectory missed its target by 2.5 mm and failed the test. Its reach was reduced; the tolerance was not relaxed. Initial FBX comparisons also exposed Blender importer's default +1-frame animation offset. Imports now explicitly use `anim_offset=0`, and exact frame 1..N spans are checked. The file timing itself was not corrupt.

No-leaf-bone FBX can produce different terminal bone display lengths in an importer. QA uses anatomical local marker vectors stored in `contact_contracts.json`, transformed by the imported bone matrices, instead of treating an arbitrary display tail as the real toe/palm.

## Environment contact references
The rope remains 40 m long, but is now horizontal over the holding regions of both decks and uses cosine-squared sag in the suspended free span. Both high and low models and runtime LOD distance logic use the same authored profile. Six standing anchors avoid the rope-end pedestals and place both source-rig palm-centre proxies on the straight rope. The custom source root at floor Z=0 and the approximate MTA ped spawn Z=1 are stored separately. Actual GTA retarget offsets are not known or proven.

## Inspection evidence
`render_animation_previews.py` renders the genuine skinned reference rig for pull, strong pull, cautious walk and jump. Optional GIFs carry source/file hashes and diagnostic labels. The walk preview applies the declared actor drive. These are a segmented reference mannequin, not a finished character, MTA footage, mocap or animator sign-off.

## Reference skin regression found in visual review
The first driven-walk preview exposed a separate reference-mesh binding problem: the rigid mesh segments were not parented to the armature object. Their bones were correct, but moving the whole actor could detach/deform displayed segments. They are now parented to the rig with a preserved rest transform. `validate_reference_skin.py` samples 2,040 segment poses across all 20 clips, both with and without actor translation/rotation, and checks evaluated mesh centroids against anatomical bone centres. Corrected previews were regenerated. This test still does not validate a continuous weighted character skin or a GTA target.

GIFs may merge identical neighbouring render samples during encoding (for example at a symmetric strong-pull midpoint). Metadata distinguishes rendered samples from decoded GIF frames and records exact encoded frame durations. `validate_animation_previews.py` checks dimensions, decoded frame counts, duration, source/file hashes and successful decoding. The small GIFs are down-palette diagnostic views, not final quality renders.

## Remaining acceptance
Artistic timing/weight polish, actual hand/finger and skinned sole contact, exact GTA skeleton mapping, IFP conversion/playback, MTA shader/streaming/physics tests, reference fidelity and hardware profiling remain outstanding. Overall project status is still PARTIAL.
