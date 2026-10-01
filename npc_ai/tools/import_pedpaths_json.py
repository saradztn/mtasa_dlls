#!/usr/bin/env python3
"""Build runnable NPC-AI chunks from a verified pedestrian-node JSON export.

This importer is intentionally limited to data that contains *only real GTA SA
pedestrian nodes* with stable global IDs encoded as ``area * 65536 + nodeId``.
It is used for the bundled ready-to-run graph when native nodes*.dat files are
not redistributed.  ``convert_nodes.py`` remains the canonical full-fidelity
converter for a user's original DAT corpus.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from convert_nodes import AREA_COUNT, AREA_SIZE, AREAS_PER_AXIS, FORMAT, WORLD_MIN, atomic_json_write, update_meta

UPSTREAM_URL = "https://github.com/ryrntjy9bp-lab/pedestrians-build"
UPSTREAM_COMMIT = "83594e793b148d035974aa8bd3078fddad1f2fc3"
EXPECTED_SOURCE_SHA256 = "f8eee454f8bbab5b85cbd9fade1c7c9174ee5aecbff9356dbf69b982962c15a3"
EXPECTED_PED_COUNT = 37650


def area_bounds(area: int) -> list[int]:
    column = area % AREAS_PER_AXIS
    row = area // AREAS_PER_AXIS
    minimum_x = WORLD_MIN + column * AREA_SIZE
    minimum_y = WORLD_MIN + row * AREA_SIZE
    return [minimum_x, minimum_y, minimum_x + AREA_SIZE, minimum_y + AREA_SIZE]


def fail(message: str) -> None:
    raise ValueError(message)


def finite_number(value: Any, field: str, index: int) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f"node[{index}] has invalid {field}")
    return float(value)


def parse_nodes(payload: Any) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(payload, list):
        fail("pedpaths JSON root must be an array")

    errors: list[dict[str, Any]] = []
    parsed: list[dict[str, Any]] = []
    by_id: dict[int, dict[str, Any]] = {}
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            errors.append({"code": "invalid_record", "index": index})
            continue
        global_id = raw.get("id")
        area = raw.get("area")
        if not isinstance(global_id, int) or not isinstance(area, int):
            errors.append({"code": "invalid_id_or_area", "index": index})
            continue
        if area < 0 or area >= AREA_COUNT:
            errors.append({"code": "area_out_of_range", "index": index, "area": area})
            continue
        if global_id < 0 or global_id >= AREA_COUNT * 65536:
            errors.append({"code": "global_id_out_of_range", "index": index, "id": global_id})
            continue
        if global_id // 65536 != area:
            errors.append({"code": "global_id_area_mismatch", "index": index, "id": global_id, "area": area})
            continue
        if global_id in by_id:
            errors.append({"code": "duplicate_global_id", "index": index, "id": global_id})
            continue
        try:
            x = finite_number(raw.get("x"), "x", index)
            y = finite_number(raw.get("y"), "y", index)
            z = finite_number(raw.get("z"), "z", index)
        except ValueError as error:
            errors.append({"code": "invalid_coordinate", "index": index, "message": str(error)})
            continue
        links = raw.get("links")
        if not isinstance(links, list) or len(links) > 15 or any(not isinstance(link, int) for link in links):
            errors.append({"code": "invalid_links", "index": index, "id": global_id})
            continue

        node = {
            "id": global_id,
            "area": area,
            "nodeId": global_id % 65536,
            "x": x,
            "y": y,
            "z": z,
            "links": links,
        }
        parsed.append(node)
        by_id[global_id] = node

    if errors:
        preview = json.dumps(errors[:8], ensure_ascii=False)
        fail(f"pedpaths validation failed with {len(errors)} issue(s): {preview}")

    topology_issues: list[dict[str, Any]] = []
    for node in parsed:
        for target_id in node["links"]:
            target = by_id.get(target_id)
            if target is None:
                topology_issues.append({"code": "missing_link_target", "id": node["id"], "target": target_id})
            elif target_id == node["id"]:
                topology_issues.append({"code": "self_link", "id": node["id"]})
            elif node["id"] not in target["links"]:
                topology_issues.append({"code": "non_reciprocal_link", "id": node["id"], "target": target_id})
    if topology_issues:
        preview = json.dumps(topology_issues[:8], ensure_ascii=False)
        fail(f"pedpaths topology validation failed with {len(topology_issues)} issue(s): {preview}")
    return parsed, by_id, topology_issues


def build_chunks(nodes: list[dict[str, Any]], by_id: dict[int, dict[str, Any]], output: Path) -> tuple[list[Path], dict[str, Any], dict[str, int]]:
    by_area: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_area[node["area"]].append(node)

    chunks: list[Path] = []
    manifest_areas: dict[str, Any] = {}
    total_links = 0
    for area in range(AREA_COUNT):
        area_nodes = sorted(by_area.get(area, []), key=lambda node: node["nodeId"])
        records: list[list[Any]] = []
        link_offset = 0
        for node in area_nodes:
            links: list[list[int]] = []
            for target_id in node["links"]:
                target = by_id[target_id]
                # The pedpaths source does not retain native byte link lengths,
                # navi links, or intersection flags. Runtime uses Euclidean cost.
                links.append([target["area"], target["nodeId"], 0, 0, 0])
            records.append([
                node["nodeId"],
                node["x"],
                node["y"],
                node["z"],
                0,                 # native path width unavailable in ped-only source
                len(links),        # preserves the low-nibble link-count contract
                0,                 # flood fill unavailable
                0,                 # heuristic cost unavailable
                link_offset,
                links,
                0,                 # raw memory address unavailable
                0,                 # raw unused UINT32 unavailable
                "ped",
            ])
            link_offset += len(links)
        total_links += link_offset
        chunk = {
            "format": FORMAT,
            "area": area,
            "bounds": area_bounds(area),
            "header": {
                "numNodes": len(records),
                "numVehicleNodes": 0,
                "numPedNodes": len(records),
                "numNaviNodes": 0,
                "numLinks": link_offset,
                "source": "verified_pedpaths_json",
            },
            "ped": records,
            "vehicle": [],
            "navi": [],
        }
        chunk_path = output / f"area_{area}.json"
        atomic_json_write(chunk_path, chunk)
        chunks.append(chunk_path)
        manifest_areas[str(area)] = {
            "file": f"data/gta_nodes/{chunk_path.name}",
            "bounds": area_bounds(area),
            "pedNodes": len(records),
            "vehicleNodes": 0,
            "naviNodes": 0,
            "links": link_offset,
        }

    totals = {
        "pedNodes": len(nodes),
        "vehicleNodes": 0,
        "naviNodes": 0,
        "links": total_links,
    }
    return chunks, manifest_areas, totals


def main(argv: list[str] | None = None) -> int:
    resource_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="verified pedpaths.json input")
    parser.add_argument("--output", type=Path, default=resource_root / "data" / "gta_nodes")
    parser.add_argument("--update-meta", type=Path, default=resource_root / "meta.xml")
    parser.add_argument("--allow-unexpected-count", action="store_true")
    parser.add_argument("--allow-unexpected-sha256", action="store_true", help="allow a source other than the audited pinned input")
    parser.add_argument("--upstream-url", default=UPSTREAM_URL)
    parser.add_argument("--upstream-commit", default=UPSTREAM_COMMIT)
    args = parser.parse_args(argv)

    try:
        runtime_resource_root = args.update_meta.parent.resolve()
        try:
            args.output.resolve().relative_to(runtime_resource_root)
        except ValueError:
            fail("--output must be inside the resource root so meta.xml can reference its chunks")

        raw_bytes = args.input.read_bytes()
        source_hash = hashlib.sha256(raw_bytes).hexdigest()
        if not args.allow_unexpected_sha256 and source_hash != EXPECTED_SOURCE_SHA256:
            fail(
                "input SHA-256 does not match the audited pinned pedpaths.json; "
                "use --allow-unexpected-sha256 only after independently reviewing the source"
            )
        payload = json.loads(raw_bytes.decode("utf-8"))
        nodes, by_id, _ = parse_nodes(payload)
        if not args.allow_unexpected_count and len(nodes) != EXPECTED_PED_COUNT:
            fail(f"expected {EXPECTED_PED_COUNT} pedestrian nodes, got {len(nodes)}")
        args.output.mkdir(parents=True, exist_ok=True)
        chunks, areas, totals = build_chunks(nodes, by_id, args.output)
        manifest = {
            "format": FORMAT,
            "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "source": {
                "kind": "pedestrian-only GTA SA node export",
                "label": "ryrntjy9bp-lab/pedestrians-build pedpaths.json",
                "url": args.upstream_url,
                "commit": args.upstream_commit,
                "sha256": source_hash,
                "license": "MIT; see data/gta_nodes/THIRD_PARTY_NOTICES.md",
                "nativeMetadata": "Ped-only export: coordinates and topology are available; vehicle/navi/raw DAT flags are not.",
                "fieldHandling": "The runtime flag low nibble is reconstructed from verified link count; native flag bits and link metadata are unavailable.",
            },
            "areas": areas,
            "totals": totals,
        }
        atomic_json_write(args.output / "manifest.json", manifest)
        report = {
            "summary": {
                "errors": 0,
                "warnings": 0,
                "pedNodes": len(nodes),
                "areas": len(areas),
                "links": totals["links"],
                "degreeHistogram": dict(sorted(Counter(len(node["links"]) for node in nodes).items())),
            },
            "checks": [
                "global ID area encoding validated",
                "coordinates finite",
                "all link targets exist",
                "no self-links",
                "all links reciprocal",
            ],
        }
        atomic_json_write(args.output / "validation_report.json", report)
        update_meta(args.update_meta, chunks)
        print(f"[INFO] Wrote ready graph: {totals['pedNodes']} ped nodes, {totals['links']} links, {len(chunks)} chunks")
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
