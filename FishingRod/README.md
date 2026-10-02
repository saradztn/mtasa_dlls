<!-- Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline -->
# FishingRod – "Tidewater Pro Series TW-702MF" 7'0" spinning rod for MTA:SA / GTA:SA

Procedurally modelled, textured and exported by a fully reproducible Python pipeline (no DCC tool, no placeholder meshes).

## Files (ready for direct use)
| File | Content |
|---|---|
| `model/FishingRod.dff` | RW 3.6.0.3 (0x1803FFFF) clump, 5 frames, 4 atomics, 41 081 verts / **67 908 tris**, normals, 1 UV set, prelit + night colours, MatFX env-map on metals |
| `texture/FishingRod.txd` | D3D9 TXD, 15 diffuse textures (DXT1, full mip chain, power-of-two, 64²…1024², label 512×2048) + `fr_env` env map |
| `collision/FishingRod.col` | COL3 `FishingRod`, model id 0 (MTA reassigns it on `engineReplaceCOL`): 33 spheres + 25 boxes, 1.4 KB, no triangle mesh |
| `texture/maps/*_n.dds`, `*_orm.dds` | Normal maps (DXT5nm, x in alpha) and ORM maps (R = AO, G = roughness, B = metallic; DXT1) for the optional shader |
| `preview/preview_{front,side,detail}.png` | Software PBR renders **of the shipped files** (not in-game screenshots) |
| `source/` | Complete pipeline, QC and an MTA test resource |

SA's material model has no normal/roughness/metal channels, so: diffuse (with baked AO and a game-lift for black materials) + env-map MatFX live in the TXD; the full PBR set is delivered as DDS maps and consumed by the optional `source/mta_test/shader.fx`.

## Orientation / pivot
Units = metres, **+Y = towards the tip**, +X right, **+Z up**. Origin = centre of the reel seat on the rod axis (the natural hand-hold point). Length 1.95 m (butt y = −0.302, tip y = +1.649), reel hangs below the blank (z −0.0865) like a real spinning rod.
Frames: `FishingRod` (root) → `fr_rod`, `fr_reel_body`, `fr_reel_rotor` (pivot on the spool axis, ready for animation), `fr_line`.

## Contents
Tapered, slightly bent carbon blank (7.1 → 1.0 mm radius, twill weave, printed label zone, ferrule); handle with rubber butt pad, EVA, cork and gold rings; reel seat with fixed and sliding hoods and knurled lock nut; spinning reel with housing and laser-etched plates, 10 Torx screws, crank arm + knob, rotor, bail wire, line roller and clip, spool with gold flanges and wound line, drag knob, anti-reverse switch, stem and foot; 9 graduated guides (ceramic insert, chrome ring, two bent legs, thread wraps) and tip-top; 1 mm line from spool over the roller through every guide to the tip.
Materials (each its own texture + roughness/metal/AO/normal): carbon, labelled carbon, EVA, cork, rubber, dark anodised aluminium, gold aluminium, paint, chrome, ceramic, thread, plastic, reel plate, wound line, line.

## Rebuild and QC
```
pip install numpy pillow scipy
cd source
python3 build_all.py          # geometry + textures -> DFF / TXD / COL / maps   (~20 s)
python3 validate.py           # independent re-parse + checks  -> qc_report.txt
tools/build_librw_check.sh && /tmp/librw_check ../model/FishingRod.dff ../texture/FishingRod.txd
python3 make_previews.py      # preview PNGs from the shipped files
```
QC results: `source/qc_report.txt` (0 failures) and `source/librw_report.txt` (the reference RenderWare loader `aap/librw` parses the DFF and TXD and resolves every texture from the TXD: ALL CHECKS PASSED). Checks cover chunk sizes, index ranges, orphan vertices, unit normals, winding vs. normals (99.4–100 %), degenerate faces, BinMesh totals, bounding spheres, texture references ⊆ TXD, texture sanity, COL header/size and COL ↔ mesh containment.

## ⚠ What has NOT been verified
**No MTA:SA / GTA:SA client was available in the build environment, so there was no real in-game import test.** The files were validated by two independent parsers (own strict reader + librw), not by the game. Treat the first load in MTA as the final test:
1. `python3 source/mta_test/install_test_resource.py <mta>/server/mods/deathmatch/resources`
2. `/start FishingRod_test` replaces **model ID 321** (weapon id 10 slot model) with the rod; `/fishrod` spawns an object with ID 321, `/fishshader` toggles the optional shader (untested).
The debug console prints which step failed. Known risks: the COL3 and the RW MatFX / extra-vertex-colour chunks are hand-written to the documented layouts; the DFF is 68 k tris, which is fine for a single hero object but heavy if many are streamed at once (rod blank, guides and reel are separate materials; drop `fr_line` or the guides if you need an LOD).
