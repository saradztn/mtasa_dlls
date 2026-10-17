# Custom-rig → GTA conversion notes (no IFP exported)

This project supplies a **custom**, 26-bone humanoid (18 deform + 4 IK endpoint controls + 4 pole controls). It is not an imported GTA skeleton, and it does not carry verified GTA bone IDs. Use `source_assets/animations/rig.json` as the authoritative hierarchy/rest-coordinate definition. `GenesisAnimations.blend` contains 20 editable named Actions plus the segmented skinned reference mannequin. Skin is for preview, not a finished game character.

## Space and export
- Blender: metres, Z up, +Y facing. Rest height ≈1.83 m; arms slope downward, not a GTA T-pose.
- Scene 30 FPS; each action samples every frame. Frame 1 through N inclusive; duration=(N−1)/30.
- FBX binary 7400: `axis_forward=-Z`, `axis_up=Y`, `apply_unit_scale=True`, leaf bones off, only selected armature, deform-only, no simplification, animation bake on.
- Individual FBX: active action only, no NLA/all-actions bake. Combined FBX: all named actions. No mesh in FBX; source blend retains preview mesh.
- Four unparented endpoint controls `handIK_L/R`, `footIK_L/R` and four calibrated `elbowPole_L/R`, `kneePole_L/R` controls constrain the two-bone chains. World-space foot/hand orientation constraints are baked. Exported animation is evaluated/baked onto deform bones. Do not retarget the source control bones as GTA bones.

## Semantic mapping — NOT verified target names or IDs
| Source | Target role |
|---|---|
| root | chosen locomotion root / actor motion reference |
| pelvis | pelvis/hips |
| spine | lower spine |
| chest | upper spine |
| neck | neck |
| head | head |
| upperarm_L / R | left/right upper arm |
| forearm_L / R | left/right forearm |
| hand_L / R | left/right hand |
| thigh_L / R | left/right thigh |
| shin_L / R | left/right calf |
| foot_L / R | left/right foot |

GTA target rigs may have clavicles, toes, fingers, twist bones and different axis rolls. This source does not. Set unmapped target bones to a suitable rest pose; do not guess numeric bone IDs. Obtain the exact target rig from the user's licensed conversion pipeline. Source L is negative X while facing +Y: verify target handedness explicitly rather than swapping based on a name alone.

## Suggested external workflow
1. Open the source blend, select a named Action, check it on the reference rig.
2. Import the exact target skeleton; compare units, rest positions, local axes and bone rolls. Preserve the target hierarchy/IDs.
3. Add target-to-source constraints/retarget mappings by the semantic table, accounting for rest-pose differences. Handle missing clavicles and hands with explicit offsets; no finger grip is authored.
4. Bake **target** transforms at 30 FPS, remove constraints, inspect actual hand positions and planted feet frame-by-frame. Never copy source local Euler channels blindly.
5. Choose whether to retain or extract root translation for short-step/jump/fall/stumble clips. The cautious walk is in-place and requires locomotion synchronization.
6. Export/convert using the user's own IFP tool. This project neither converts nor validates IFP.

## Rope alignment
Environment rope runs along local X, with flat holding regions X=-20..-14 and 14..20 at Y=0, Z=1.05. The suspended free span sags smoothly to Z=.89 at the middle; a cosine-squared profile is C1-continuous at both platform edges.

Held source wrist targets are X=0, Y=.28/.42, Z=1.06. Source palm-centre proxy offsets put both centres at X=0, Y=.33/.47, Z=1.05. These are centre-line proxies, **not** skin/finger surface contacts. The hands do not have articulated fingers.

`source_assets/animations/grip_alignment.json` supplies six authored source-rig anchors. Left-team roots X=-18.9,-17.3,-15.7 rotate 270 degrees around Z (+Y facing becomes +X); right-team counterparts rotate 90 degrees. Both palm proxies map to the straight platform rope within the authored span. These reference positions avoid the dedicated rope-end pedestal and stay on the deck. Unused former capstan bases that occupied a standing slot were removed.

Each anchor distinguishes `source_rig_root` at Z=0 from an approximate MTA `mta_spawn_reference` at Z=1. **Do not equate the custom source root with the GTA ped's collision/model origin.** Target rig offsets, actor facing, animation import axes, skinned hands and all in-game alignment still require conversion/playback verification. No runtime animation attachment/IFP playback is implemented.

## In-place walk drive
`GB_CautiousWalk` requires +0.88 m of actor travel per three-second cycle in source +Y (~0.2933 m/s). Source-root bone animation stays in-place; declared stance-foot trajectories counteract this separate drive. Contact tests explicitly apply it rather than falsely asserting that an undriven in-place walk has stationary feet. If the converter extracts root motion or rescales units, preserve this relationship deliberately. Jump preparation/landing use separate planted windows; intentional slip/fall phases are not stance contacts.

## Import timing and anatomical markers
Validation imports FBX with `anim_offset=0` to preserve source frame 1..N. Blender's default +1-frame offset is an importer option, not a damaged file. Set the equivalent option in your converter.

No leaf bones are exported. Importers can infer different terminal display-tail lengths; a display tail is not a reliable toe/palm location. `contact_contracts.json` defines anatomical local marker vectors. Evaluate them with the imported bone transforms, not arbitrary displayed bone lengths. This does not prove how an independently skinned GTA character's soles/fingers move.

## QA boundary
FBX reimport validates nonempty tracks, exact frame spans, finite evaluated transforms, distinct sampled motion, stable bone scales and matching endpoints of designated loops. Additional source/FBX contract tests enforce 2 mm proxy sole planting, IK target reach and held-grip line alignment within declared windows, and verify ten supported transition pairs. That still does **not** prove biomechanical realism, actual skinned-foot/finger contact, GTA compatibility or final visual acceptance. Unsupported transitions need blending/retarget work.
