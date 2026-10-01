#!/usr/bin/env python3
"""Convert validated original GTA SA nodes*.dat files into streamed MTA chunks.

The canonical source is a legally extracted ``nodes0.dat`` ... ``nodes63.dat``
set from a GTA San Andreas installation.  Rockstar game assets are deliberately
not redistributed by this resource.

The parser follows the documented native layout exactly:
header -> 28-byte path nodes -> 14-byte navi nodes -> 4-byte links -> filler
-> navi links -> link lengths -> intersection flags -> trailing 192 bytes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import struct
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

FORMAT = "npc_ai.gta_sa_ped_graph.v1"
AREA_COUNT = 64
AREAS_PER_AXIS = 8
AREA_SIZE = 750
WORLD_MIN = -3000
HEADER = struct.Struct("<IIIII")
PATH_NODE = struct.Struct("<II3hhHHHBBI")
NAVI_NODE = struct.Struct("<2hHH2bI")
LINK = struct.Struct("<HH")
FILLER_SIZE = 768
TRAILING_SIZE = 192
NODE_FILE_PATTERN = re.compile(r"^nodes(\d+)\.dat$", re.IGNORECASE)


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    area: int | None = None
    node: int | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.area is not None:
            result["area"] = self.area
        if self.node is not None:
            result["node"] = self.node
        return result


@dataclass
class ValidationReport:
    max_stored_issues: int = 1000
    issues: list[Issue] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    def add(
        self,
        severity: str,
        code: str,
        message: str,
        area: int | None = None,
        node: int | None = None,
    ) -> None:
        self.counts[severity] += 1
        self.counts[f"{severity}:{code}"] += 1
        if len(self.issues) < self.max_stored_issues:
            self.issues.append(Issue(severity, code, message, area, node))

    @property
    def has_errors(self) -> bool:
        return self.counts["error"] > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "errors": self.counts["error"],
                "warnings": self.counts["warning"],
                "info": self.counts["info"],
                "storedIssues": len(self.issues),
                "issuesTruncated": max(0, sum(self.counts[s] for s in ("error", "warning", "info")) - len(self.issues)),
            },
            "issueCounts": dict(sorted(self.counts.items())),
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass
class ParsedArea:
    area: int
    source_path: Path
    source_sha256: str
    source_size: int
    header: dict[str, int]
    ped: list[list[Any]]
    vehicle: list[list[Any]]
    navi: list[list[Any]]
    all_nodes: list[dict[str, Any]]
    bounds: list[int]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def area_bounds(area: int) -> list[int]:
    column = area % AREAS_PER_AXIS
    row = area // AREAS_PER_AXIS
    minimum_x = WORLD_MIN + column * AREA_SIZE
    minimum_y = WORLD_MIN + row * AREA_SIZE
    return [minimum_x, minimum_y, minimum_x + AREA_SIZE, minimum_y + AREA_SIZE]


def required_size(num_nodes: int, num_navi: int, num_links: int) -> int:
    return (
        HEADER.size
        + num_nodes * PATH_NODE.size
        + num_navi * NAVI_NODE.size
        + num_links * LINK.size
        + FILLER_SIZE
        + num_links * 2  # navi-link table
        + num_links  # link lengths
        + num_links  # intersection flags
        + TRAILING_SIZE
    )


def parse_area_file(path: Path, area: int, report: ValidationReport, coordinate_limit: float) -> ParsedArea:
    data = path.read_bytes()
    if len(data) < HEADER.size:
        raise ValueError(f"{path.name}: file is shorter than the 20-byte header")

    num_nodes, num_vehicle, num_ped, num_navi, num_links = HEADER.unpack_from(data, 0)
    expected_size = required_size(num_nodes, num_navi, num_links)
    if len(data) < expected_size:
        raise ValueError(
            f"{path.name}: truncated ({len(data)} bytes; native layout requires at least {expected_size})"
        )
    if num_vehicle + num_ped != num_nodes:
        report.add(
            "error",
            "header_count_mismatch",
            f"header total={num_nodes}, vehicle+ped={num_vehicle + num_ped}",
            area,
        )
    if num_vehicle > num_nodes or num_ped > num_nodes:
        report.add("error", "header_count_invalid", "vehicle/ped count exceeds total", area)

    nodes_offset = HEADER.size
    navi_offset = nodes_offset + num_nodes * PATH_NODE.size
    links_offset = navi_offset + num_navi * NAVI_NODE.size
    filler_offset = links_offset + num_links * LINK.size
    navi_links_offset = filler_offset + FILLER_SIZE
    link_lengths_offset = navi_links_offset + num_links * 2
    intersections_offset = link_lengths_offset + num_links

    raw_links = [LINK.unpack_from(data, links_offset + index * LINK.size) for index in range(num_links)]
    raw_navi_links = [struct.unpack_from("<H", data, navi_links_offset + index * 2)[0] for index in range(num_links)]
    raw_lengths = list(data[link_lengths_offset : link_lengths_offset + num_links])
    raw_intersections = list(data[intersections_offset : intersections_offset + num_links])

    ped: list[list[Any]] = []
    vehicle: list[list[Any]] = []
    all_nodes: list[dict[str, Any]] = []
    seen_node_ids: set[int] = set()
    seen_coordinates: dict[tuple[float, float, float, str], int] = {}

    for index in range(num_nodes):
        offset = nodes_offset + index * PATH_NODE.size
        (
            memory_address,
            unused,
            raw_x,
            raw_y,
            raw_z,
            heuristic_cost,
            link_offset,
            node_area,
            node_id,
            width,
            flood_fill,
            flags,
        ) = PATH_NODE.unpack_from(data, offset)
        node_type = "vehicle" if index < num_vehicle else "ped"
        x, y, z = raw_x / 8.0, raw_y / 8.0, raw_z / 8.0
        link_count = flags & 0x0F

        if node_area != area:
            report.add(
                "error",
                "area_mismatch",
                f"node declares area {node_area}, expected {area}",
                area,
                node_id,
            )
        if node_id in seen_node_ids:
            report.add("error", "duplicate_node_id", f"duplicate node ID {node_id}", area, node_id)
        seen_node_ids.add(node_id)
        if not all(math.isfinite(value) and abs(value) <= coordinate_limit for value in (x, y, z)):
            report.add("error", "invalid_coordinate", f"({x}, {y}, {z})", area, node_id)
        if link_offset + link_count > num_links:
            report.add(
                "error",
                "broken_link_range",
                f"offset {link_offset} + count {link_count} exceeds {num_links}",
                area,
                node_id,
            )

        coordinate_key = (x, y, z, node_type)
        if coordinate_key in seen_coordinates:
            report.add(
                "warning",
                "duplicate_coordinate",
                f"duplicates node {seen_coordinates[coordinate_key]} at ({x}, {y}, {z})",
                area,
                node_id,
            )
        else:
            seen_coordinates[coordinate_key] = node_id

        links: list[list[int]] = []
        for link_index in range(link_offset, min(link_offset + link_count, num_links)):
            target_area, target_node = raw_links[link_index]
            links.append(
                [
                    target_area,
                    target_node,
                    raw_lengths[link_index],
                    raw_intersections[link_index],
                    raw_navi_links[link_index],
                ]
            )
            if target_area == node_area and target_node == node_id:
                report.add("warning", "self_link", "node links to itself", area, node_id)

        # Compact positional record consumed by navigation/nodes.lua. The raw
        # UINT32 fields and explicit grouping-derived node type are retained.
        output_node: list[Any] = [
            node_id,
            x,
            y,
            z,
            width,
            flags,
            flood_fill,
            heuristic_cost,
            link_offset,
            links,
            memory_address,
            unused,
            node_type,
        ]
        (vehicle if node_type == "vehicle" else ped).append(output_node)
        all_nodes.append(
            {
                "area": node_area,
                "node_id": node_id,
                "type": node_type,
                "x": x,
                "y": y,
                "z": z,
                "links": links,
            }
        )

    navi: list[list[Any]] = []
    for index in range(num_navi):
        offset = navi_offset + index * NAVI_NODE.size
        raw_x, raw_y, target_area, target_node, direction_x, direction_y, flags = NAVI_NODE.unpack_from(data, offset)
        navi.append([
            index,
            raw_x / 8.0,
            raw_y / 8.0,
            target_area,
            target_node,
            direction_x,
            direction_y,
            flags,
        ])

    return ParsedArea(
        area=area,
        source_path=path,
        source_sha256=sha256_bytes(data),
        source_size=len(data),
        header={
            "numNodes": num_nodes,
            "numVehicleNodes": num_vehicle,
            "numPedNodes": num_ped,
            "numNaviNodes": num_navi,
            "numLinks": num_links,
        },
        ped=ped,
        vehicle=vehicle,
        navi=navi,
        all_nodes=all_nodes,
        bounds=area_bounds(area),
    )


def discover_node_files(input_path: Path, report: ValidationReport, allow_partial: bool) -> dict[int, Path]:
    if input_path.is_file():
        candidates = [input_path]
    elif input_path.is_dir():
        candidates = list(input_path.iterdir())
    else:
        raise ValueError(f"input does not exist: {input_path}")

    found: dict[int, Path] = {}
    for candidate in candidates:
        match = NODE_FILE_PATTERN.match(candidate.name)
        if not match or not candidate.is_file():
            continue
        area = int(match.group(1))
        if area < 0 or area >= AREA_COUNT:
            report.add("error", "area_out_of_range", f"{candidate.name} has area {area}")
            continue
        if area in found:
            report.add("error", "duplicate_area_file", f"both {found[area].name} and {candidate.name}", area)
            continue
        found[area] = candidate

    if not found:
        raise ValueError("no nodes<N>.dat files found")
    if not allow_partial:
        missing = [str(area) for area in range(AREA_COUNT) if area not in found]
        if missing:
            report.add("error", "missing_areas", "missing areas: " + ", ".join(missing))
    return found


def validate_cross_area_links(
    parsed_areas: Iterable[ParsedArea],
    report: ValidationReport,
    max_link_distance: float,
    allow_partial: bool,
) -> None:
    by_key: dict[tuple[int, int], dict[str, Any]] = {}
    areas = list(parsed_areas)
    supplied_areas = {parsed.area for parsed in areas}
    for parsed in areas:
        for node in parsed.all_nodes:
            key = (node["area"], node["node_id"])
            if key in by_key:
                report.add("error", "duplicate_global_node", f"duplicate global key {key}", parsed.area, node["node_id"])
            by_key[key] = node

    for parsed in areas:
        for node in parsed.all_nodes:
            for target_area, target_node, stored_length, _intersection, _navi_link in node["links"]:
                target = by_key.get((target_area, target_node))
                if target is None:
                    severity = "warning" if allow_partial and target_area not in supplied_areas else "error"
                    code = "link_target_outside_partial_corpus" if severity == "warning" else "missing_link_target"
                    report.add(
                        severity,
                        code,
                        f"link target ({target_area}, {target_node}) does not exist in supplied corpus",
                        parsed.area,
                        node["node_id"],
                    )
                    continue
                distance = math.dist((node["x"], node["y"], node["z"]), (target["x"], target["y"], target["z"]))
                if distance > max_link_distance:
                    report.add(
                        "warning",
                        "impossible_link_distance",
                        f"link to ({target_area}, {target_node}) is {distance:.2f} units (stored {stored_length})",
                        parsed.area,
                        node["node_id"],
                    )
                if node["type"] == "ped" and target["type"] != "ped":
                    report.add(
                        "warning",
                        "ped_link_to_nonped",
                        f"ped node links to {target['type']} target ({target_area}, {target_node})",
                        parsed.area,
                        node["node_id"],
                    )


def atomic_json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def update_meta(meta_path: Path, chunk_paths: list[Path]) -> None:
    begin = "<!-- NPC_AI_NODE_FILES_BEGIN -->"
    end = "<!-- NPC_AI_NODE_FILES_END -->"
    text = meta_path.read_text(encoding="utf-8")
    start_index = text.find(begin)
    end_index = text.find(end)
    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise ValueError(f"{meta_path}: conversion markers were not found")

    entries: list[str] = []
    for chunk_path in sorted(chunk_paths):
        relative = chunk_path.relative_to(meta_path.parent).as_posix()
        entries.append(f'    <file src="{relative}" download="false" />')
    replacement = begin + "\n"
    if entries:
        replacement += "\n".join(entries) + "\n"
    replacement += "    " + end
    text = text[:start_index] + replacement + text[end_index + len(end) :]
    meta_path.write_text(text, encoding="utf-8")


def audit_json_dataset(path: Path) -> int:
    """Audit a third-party JSON export without pretending it is canonical data."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"[ERROR] Cannot read JSON: {error}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("[ERROR] Root is not a JSON object", file=sys.stderr)
        return 2

    required = {"x", "y", "z", "links", "area", "nodeId", "type", "flags", "width"}
    observed: set[str] = set()
    link_count = 0
    empty_links = 0
    malformed_links = 0
    coordinates: list[tuple[float, float, float]] = []
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        observed.update(value.keys())
        links = value.get("links")
        if isinstance(links, list):
            link_count += len(links)
            empty_links += int(not links)
            malformed_links += sum(not isinstance(link, (str, int, dict, list)) for link in links)
        if all(isinstance(value.get(axis), (int, float)) for axis in ("x", "y", "z")):
            coordinates.append((float(value["x"]), float(value["y"]), float(value["z"])))

    missing = sorted(required - observed)
    out_of_raw_range = sum(any(abs(component) > 4096 for component in coordinate) for coordinate in coordinates)
    print(f"[INFO] JSON nodes: {len(data)}")
    print(f"[INFO] Fields: {', '.join(sorted(observed)) or '(none)'}")
    print(f"[INFO] Links: {link_count}; empty-link nodes: {empty_links}; malformed links: {malformed_links}")
    print(f"[INFO] Coordinates outside signed-int16/8 range: {out_of_raw_range}")
    if missing:
        print("[ERROR] Dataset cannot identify a validated GTA SA ped graph; missing fields: " + ", ".join(missing))
        print("[ERROR] Use --input with original nodes0.dat ... nodes63.dat instead.")
        return 1
    print("[INFO] Dataset has the minimum metadata fields; it still must be cross-validated against DAT files.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    resource_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="directory containing extracted nodes0.dat ... nodes63.dat")
    parser.add_argument(
        "--output",
        type=Path,
        default=resource_root / "data" / "gta_nodes",
        help="output directory for manifest.json and area_<N>.json chunks",
    )
    parser.add_argument("--update-meta", type=Path, help="meta.xml to update with download=false chunk entries")
    parser.add_argument("--allow-partial", action="store_true", help="allow a subset of the 64 original areas")
    parser.add_argument("--ped-only", action="store_true", help="omit vehicle/navi records from generated chunks")
    parser.add_argument("--allow-errors", action="store_true", help="write chunks even if validation found errors (not recommended)")
    parser.add_argument("--coordinate-limit", type=float, default=4096.0)
    parser.add_argument("--max-link-distance", type=float, default=2000.0)
    parser.add_argument("--source-label", default="Original GTA San Andreas nodes*.dat")
    parser.add_argument("--audit-json", type=Path, help="audit a third-party JSON export and exit")
    return parser


def run_conversion(args: argparse.Namespace) -> int:
    report = ValidationReport()
    try:
        files = discover_node_files(args.input, report, args.allow_partial)
    except ValueError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2

    runtime_resource_root = (args.update_meta.parent if args.update_meta else Path(__file__).resolve().parents[1]).resolve()
    try:
        args.output.resolve().relative_to(runtime_resource_root)
    except ValueError:
        print(
            "[ERROR] --output must be inside the resource root so generated manifest file paths are MTA-relative.",
            file=sys.stderr,
        )
        return 2

    parsed_areas: list[ParsedArea] = []
    for area, path in sorted(files.items()):
        try:
            parsed_areas.append(parse_area_file(path, area, report, args.coordinate_limit))
        except (OSError, ValueError, struct.error) as error:
            report.add("error", "parse_failure", str(error), area)

    validate_cross_area_links(parsed_areas, report, args.max_link_distance, args.allow_partial)
    args.output.mkdir(parents=True, exist_ok=True)
    report_payload = report.as_dict()
    atomic_json_write(args.output / "validation_report.json", report_payload)

    summary = report_payload["summary"]
    print(f"[INFO] Parsed {len(parsed_areas)}/{len(files)} area files")
    print(f"[INFO] Validation: {summary['errors']} error(s), {summary['warnings']} warning(s)")
    if report.has_errors and not args.allow_errors:
        print("[ERROR] Conversion stopped. Inspect validation_report.json; use --allow-errors only for investigation.", file=sys.stderr)
        return 1

    chunk_paths: list[Path] = []
    manifest_areas: dict[str, Any] = {}
    totals = {"pedNodes": 0, "vehicleNodes": 0, "naviNodes": 0, "links": 0}
    source_files: list[dict[str, Any]] = []

    for parsed in parsed_areas:
        vehicle = [] if args.ped_only else parsed.vehicle
        navi = [] if args.ped_only else parsed.navi
        chunk = {
            "format": FORMAT,
            "area": parsed.area,
            "bounds": parsed.bounds,
            "header": parsed.header,
            "ped": parsed.ped,
            "vehicle": vehicle,
            "navi": navi,
        }
        chunk_path = args.output / f"area_{parsed.area}.json"
        atomic_json_write(chunk_path, chunk)
        chunk_paths.append(chunk_path)
        manifest_areas[str(parsed.area)] = {
            "file": chunk_path.resolve().relative_to(runtime_resource_root).as_posix(),
            "bounds": parsed.bounds,
            "pedNodes": len(parsed.ped),
            "vehicleNodes": len(parsed.vehicle),
            "naviNodes": len(parsed.navi),
            "links": parsed.header["numLinks"],
        }
        totals["pedNodes"] += len(parsed.ped)
        totals["vehicleNodes"] += len(parsed.vehicle)
        totals["naviNodes"] += len(parsed.navi)
        totals["links"] += parsed.header["numLinks"]
        source_files.append({
            "area": parsed.area,
            "name": parsed.source_path.name,
            "bytes": parsed.source_size,
            "sha256": parsed.source_sha256,
        })

    manifest = {
        "format": FORMAT,
        "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "label": args.source_label,
            "files": source_files,
            "pedOnly": bool(args.ped_only),
        },
        "areas": manifest_areas,
        "totals": totals,
    }
    atomic_json_write(args.output / "manifest.json", manifest)

    if args.update_meta:
        try:
            update_meta(args.update_meta, chunk_paths)
        except (OSError, ValueError) as error:
            print(f"[ERROR] Chunks were written, but meta.xml was not updated: {error}", file=sys.stderr)
            return 2

    print(f"[INFO] Wrote {len(chunk_paths)} streamed chunks to {args.output}")
    print(f"[INFO] Ped graph: {totals['pedNodes']} nodes, {totals['links']} preserved links")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.audit_json:
        return audit_json_dataset(args.audit_json)
    if args.input is None:
        parser.error("--input is required unless --audit-json is used")
    return run_conversion(args)


if __name__ == "__main__":
    raise SystemExit(main())
