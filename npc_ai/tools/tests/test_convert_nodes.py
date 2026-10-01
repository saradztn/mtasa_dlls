#!/usr/bin/env python3
"""Game-free regression tests for the native GTA SA nodes*.dat converter."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parents[1] / "convert_nodes.py"
SPEC = importlib.util.spec_from_file_location("convert_nodes", TOOL_PATH)
assert SPEC and SPEC.loader
converter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = converter
SPEC.loader.exec_module(converter)


def write_area(path: Path, area: int, nodes=None, vehicle_count: int = 0, navi=None, links=None) -> None:
    """Write a minimal valid native-layout fixture; never uses game assets."""
    nodes = nodes or []
    navi = navi or []
    links = links or []
    ped_count = len(nodes) - vehicle_count
    payload = bytearray(converter.HEADER.pack(len(nodes), vehicle_count, ped_count, len(navi), len(links)))

    for index, node in enumerate(nodes):
        node_id = node["id"]
        x, y, z = (int(round(node[axis] * 8)) for axis in ("x", "y", "z"))
        flags = (node.get("flags", 0) & ~0x0F) | node.get("count", 0)
        payload.extend(
            converter.PATH_NODE.pack(
                node.get("memory", 0),
                node.get("unused", 0),
                x,
                y,
                z,
                node.get("heuristic", 0x7FFE),
                node.get("link_offset", 0),
                area,
                node_id,
                node.get("width", 0),
                node.get("flood", 1),
                flags,
            )
        )

    for nav in navi:
        payload.extend(
            converter.NAVI_NODE.pack(
                int(nav["x"] * 8),
                int(nav["y"] * 8),
                nav.get("area", area),
                nav.get("node", 0),
                nav.get("dir_x", 0),
                nav.get("dir_y", 0),
                nav.get("flags", 0),
            )
        )

    for target_area, target_node, _length, _intersection, _navi_link in links:
        payload.extend(converter.LINK.pack(target_area, target_node))
    payload.extend(b"\xff\xff\x00\x00" * 192)
    for _target_area, _target_node, _length, _intersection, navi_link in links:
        payload.extend(int(navi_link).to_bytes(2, "little"))
    payload.extend(bytes(link[2] for link in links))
    payload.extend(bytes(link[3] for link in links))
    payload.extend(b"\x00" * converter.TRAILING_SIZE)
    path.write_bytes(payload)


def write_full_fixture(directory: Path, broken_link: bool = False) -> None:
    for area in range(64):
        write_area(directory / f"nodes{area}.dat", area)

    links = [
        (0, 2, 4, 0, 0),
        (0, 1 if not broken_link else 999, 4, 0, 0),
    ]
    nodes = [
        {"id": 0, "x": -2990.0, "y": -2990.0, "z": 12.0, "count": 0},
        {"id": 1, "x": -2988.0, "y": -2990.0, "z": 12.0, "link_offset": 0, "count": 1, "width": 8},
        {"id": 2, "x": -2984.0, "y": -2990.0, "z": 12.0, "link_offset": 1, "count": 1, "width": 8},
    ]
    navi = [{"x": -2986.0, "y": -2990.0, "area": 0, "node": 0, "dir_x": 100, "dir_y": 0, "flags": 7}]
    write_area(directory / "nodes0.dat", 0, nodes, vehicle_count=1, navi=navi, links=links)


class ConverterTests(unittest.TestCase):
    def test_converts_correct_native_sections_and_updates_meta(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "resource" / "data" / "gta_nodes"
            meta = root / "resource" / "meta.xml"
            source.mkdir(parents=True)
            meta.parent.mkdir(parents=True)
            meta.write_text(
                "<meta>\n<!-- NPC_AI_NODE_FILES_BEGIN -->\n<!-- NPC_AI_NODE_FILES_END -->\n</meta>\n",
                encoding="utf-8",
            )
            write_full_fixture(source)

            args = converter.build_arg_parser().parse_args([
                "--input", str(source),
                "--output", str(output),
                "--update-meta", str(meta),
            ])
            self.assertEqual(converter.run_conversion(args), 0)

            chunk = json.loads((output / "area_0.json").read_text(encoding="utf-8"))
            self.assertEqual(chunk["format"], converter.FORMAT)
            self.assertEqual(chunk["header"]["numPedNodes"], 2)
            self.assertEqual(len(chunk["ped"]), 2)
            self.assertEqual(len(chunk["vehicle"]), 1)
            self.assertEqual(len(chunk["navi"]), 1)
            self.assertEqual(chunk["ped"][0][0], 1)
            self.assertEqual(chunk["ped"][0][9][0][:3], [0, 2, 4])
            self.assertIn('src="data/gta_nodes/area_0.json" download="false"', meta.read_text(encoding="utf-8"))

    def test_broken_link_stops_production_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "resource" / "data" / "gta_nodes"
            meta = root / "resource" / "meta.xml"
            source.mkdir()
            meta.parent.mkdir(parents=True)
            meta.write_text("<meta>\n<!-- NPC_AI_NODE_FILES_BEGIN -->\n<!-- NPC_AI_NODE_FILES_END -->\n</meta>\n", encoding="utf-8")
            write_full_fixture(source, broken_link=True)
            args = converter.build_arg_parser().parse_args([
                "--input", str(source),
                "--output", str(output),
                "--update-meta", str(meta),
            ])
            self.assertEqual(converter.run_conversion(args), 1)
            report = json.loads((output / "validation_report.json").read_text(encoding="utf-8"))
            self.assertGreater(report["summary"]["errors"], 0)
            self.assertTrue(any(issue["code"] == "missing_link_target" for issue in report["issues"]))

    def test_incomplete_third_party_json_is_rejected_as_ped_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nodes.json"
            path.write_text(json.dumps({"0_0": {"x": 1, "y": 2, "z": 3, "links": []}}), encoding="utf-8")
            self.assertEqual(converter.audit_json_dataset(path), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
