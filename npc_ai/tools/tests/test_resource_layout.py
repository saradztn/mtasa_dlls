#!/usr/bin/env python3
"""Static resource contract checks that do not require an MTA server."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RESOURCE_ROOT = Path(__file__).resolve().parents[2]
HEADER = "-- ============================================================================\n-- GTA SA REAL NODE NPC AI\n-- Author: AI Agent\n"
EXPECTED_PED_NODES = 37650
EXPECTED_LINKS = 80686
AREA_COUNT = 64


class ResourceLayoutTests(unittest.TestCase):
    def meta_root(self) -> ET.Element:
        return ET.parse(RESOURCE_ROOT / "meta.xml").getroot()

    def test_meta_references_exist_and_are_ordered(self) -> None:
        root = self.meta_root()
        scripts = root.findall("script")
        self.assertGreaterEqual(len(scripts), 20)
        for script in scripts:
            path = RESOURCE_ROOT / script.attrib["src"]
            self.assertTrue(path.is_file(), f"missing script: {path}")
        for file_entry in root.findall("file"):
            path = RESOURCE_ROOT / file_entry.attrib["src"]
            self.assertTrue(path.is_file(), f"missing static resource file: {path}")

    def test_foundation_scripts_are_explicit_and_precede_modules_on_both_sides(self) -> None:
        root = self.meta_root()
        scripts = root.findall("script")
        self.assertFalse(any(script.attrib.get("type") == "shared" for script in scripts))
        foundations = [
            "config/config.lua",
            "shared/util.lua",
            "shared/logger.lua",
            "shared/profiler.lua",
            "shared/protocol.lua",
        ]
        server = [script.attrib["src"] for script in scripts if script.attrib.get("type") == "server"]
        client = [script.attrib["src"] for script in scripts if script.attrib.get("type") == "client"]
        self.assertEqual(server[: len(foundations)], foundations)
        self.assertEqual(client[: len(foundations)], foundations)
        self.assertIn("client/npc.lua", client)
        self.assertIn("client/debug.lua", client)
        self.assertLess(client.index("shared/protocol.lua"), client.index("client/npc.lua"))
        self.assertLess(client.index("config/config.lua"), client.index("client/debug.lua"))

    def test_every_lua_module_has_required_header(self) -> None:
        modules = list(RESOURCE_ROOT.rglob("*.lua"))
        self.assertGreaterEqual(len(modules), 19)
        for module in modules:
            self.assertTrue(module.read_text(encoding="utf-8").startswith(HEADER), module)

    def test_no_position_teleport_api_is_used(self) -> None:
        for module in RESOURCE_ROOT.rglob("*.lua"):
            source = module.read_text(encoding="utf-8")
            # Comments can document the prohibition; executable invocation may not exist.
            executable_lines = "\n".join(
                line for line in source.splitlines() if not line.lstrip().startswith("--")
            )
            self.assertIsNone(re.search(r"\bsetElementPosition\s*\(", executable_lines), module)

    def test_bundled_graph_is_complete_and_references_all_area_files(self) -> None:
        root = self.meta_root()
        graph_directory = RESOURCE_ROOT / "data" / "gta_nodes"
        manifest_path = graph_directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["format"], "npc_ai.gta_sa_ped_graph.v1")
        self.assertEqual(manifest["totals"]["pedNodes"], EXPECTED_PED_NODES)
        self.assertEqual(manifest["totals"]["links"], EXPECTED_LINKS)
        self.assertEqual(len(manifest["areas"]), AREA_COUNT)
        source = manifest["source"]
        self.assertEqual(source["commit"], "83594e793b148d035974aa8bd3078fddad1f2fc3")
        self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("Ped-only export", source["nativeMetadata"])

        entries = {entry.attrib["src"]: entry for entry in root.findall("file")}
        for area in range(AREA_COUNT):
            info = manifest["areas"][str(area)]
            self.assertEqual(info["file"], f"data/gta_nodes/area_{area}.json")
            self.assertTrue((RESOURCE_ROOT / info["file"]).is_file())
            self.assertIn(info["file"], entries)
            self.assertEqual(entries[info["file"]].attrib.get("download"), "false")

    def test_bundled_graph_topology_is_finite_and_reciprocal(self) -> None:
        graph_directory = RESOURCE_ROOT / "data" / "gta_nodes"
        manifest = json.loads((graph_directory / "manifest.json").read_text(encoding="utf-8"))
        nodes: dict[int, tuple[int, list[list[int]]]] = {}
        links = 0

        for area in range(AREA_COUNT):
            chunk = json.loads((graph_directory / f"area_{area}.json").read_text(encoding="utf-8"))
            self.assertEqual(chunk["area"], area)
            self.assertEqual(chunk["format"], manifest["format"])
            self.assertEqual(chunk["header"]["numPedNodes"], len(chunk["ped"]))
            self.assertEqual(chunk["header"]["numLinks"], sum(len(record[9]) for record in chunk["ped"]))
            self.assertEqual(manifest["areas"][str(area)]["pedNodes"], len(chunk["ped"]))
            self.assertEqual(manifest["areas"][str(area)]["links"], chunk["header"]["numLinks"])
            for record in chunk["ped"]:
                local_id, x, y, z, _width, flags, _flood, _heuristic, _offset, raw_links = record[:10]
                self.assertIsInstance(local_id, int)
                self.assertGreaterEqual(local_id, 0)
                self.assertLess(local_id, 65536)
                self.assertTrue(all(math.isfinite(value) for value in (x, y, z)))
                self.assertEqual(flags & 0x0F, len(raw_links))
                global_id = area * 65536 + local_id
                self.assertNotIn(global_id, nodes)
                nodes[global_id] = (area, raw_links)
                links += len(raw_links)

        self.assertEqual(len(nodes), EXPECTED_PED_NODES)
        self.assertEqual(links, EXPECTED_LINKS)
        for global_id, (_area, raw_links) in nodes.items():
            for raw_link in raw_links:
                target_id = raw_link[0] * 65536 + raw_link[1]
                self.assertNotEqual(target_id, global_id)
                self.assertIn(target_id, nodes)
                target_links = nodes[target_id][1]
                self.assertTrue(
                    any(link[0] * 65536 + link[1] == global_id for link in target_links),
                    f"missing reciprocal link {global_id} -> {target_id}",
                )

    def test_manifest_records_the_exact_imported_input_hash(self) -> None:
        """Guard the provenance field shape; raw upstream data itself is not vendored."""
        manifest = json.loads((RESOURCE_ROOT / "data" / "gta_nodes" / "manifest.json").read_text(encoding="utf-8"))
        source_hash = manifest["source"]["sha256"]
        self.assertEqual(len(bytes.fromhex(source_hash)), hashlib.sha256().digest_size)


if __name__ == "__main__":
    unittest.main(verbosity=2)
