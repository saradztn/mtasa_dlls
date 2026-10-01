# Bundled pedestrian navigation graph

This directory is **ready to run**. It contains all 64 streamed `area_<N>.json`
files, including six valid empty areas, so `start npc_ai` does not require a GTA
installation, extraction step, or converter run.

## Provenance and validation

The bundled graph was imported from the pedestrian-only `pedpaths.json` export
from [`ryrntjy9bp-lab/pedestrians-build`](https://github.com/ryrntjy9bp-lab/pedestrians-build),
commit `83594e793b148d035974aa8bd3078fddad1f2fc3` (MIT; full notice in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)). The exact upstream input
SHA-256, source URL, totals, and limitations are recorded in `manifest.json`.

Before bundling, the importer verifies the pinned source SHA-256, all 37,650
IDs are unique and obey GTA SA's `area * 65536 + localNodeId` convention, all
coordinates are finite, and every one of the 80,686 directed links has an
existing, non-self, reciprocal target. The compact `validation_report.json`
records those checks.

This is a **pedestrian-only topology bundle**. The upstream export retains real
pedestrian coordinates, area identity, node IDs, and links, but it does not
provide native `nodes*.dat` path width, raw flags, link length bytes,
intersection flags, navi links, vehicle nodes, or navi nodes. For compatibility
with the runtime record layout, the low flag nibble is reconstructed from the
verified outgoing-link count; no original high flag bits are claimed. The
runtime uses Euclidean edge costs where native link lengths are unavailable. It
does not pretend these unavailable values came from a raw DAT export.

## Optional full native conversion

`../../tools/convert_nodes.py` remains available for deployments that legally
extract original GTA San Andreas `nodes0.dat` through `nodes63.dat` and need
full native path/vehicle/navi metadata. That optional workflow overwrites these
chunks and rewrites the marked `meta.xml` file block. It is not needed for the
bundled resource to work.

Do not place invented grids or hand-authored replacement nodes here.
