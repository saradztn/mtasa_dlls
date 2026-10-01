#!/usr/bin/env python3
"""Regression tests for the ready-to-run pedpaths bundle importer."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIRECTORY))
TOOL_PATH = TOOLS_DIRECTORY / "import_pedpaths_json.py"
SPEC = importlib.util.spec_from_file_location("import_pedpaths_json", TOOL_PATH)
assert SPEC and SPEC.loader
importer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = importer
SPEC.loader.exec_module(importer)


class PedpathsImporterTests(unittest.TestCase):
    def write_meta(self, path: Path) -> None:
        path.write_text(
            "<meta>\n<!-- NPC_AI_NODE_FILES_BEGIN -->\n<!-- NPC_AI_NODE_FILES_END -->\n</meta>\n",
            encoding="utf-8",
        )

    def test_builds_all_64_areas_and_preserves_ped_topology(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "pedpaths.json"
            output = root / "resource" / "data" / "gta_nodes"
            meta = root / "resource" / "meta.xml"
            meta.parent.mkdir(parents=True)
            self.write_meta(meta)
            source.write_text(
                json.dumps([
                    {"id": 65537, "area": 1, "x": -2200.0, "y": -2200.0, "z": 10.0, "links": [65538]},
                    {"id": 65538, "area": 1, "x": -2195.0, "y": -2200.0, "z": 10.0, "links": [65537]},
                ]),
                encoding="utf-8",
            )

            result = importer.main([
                "--input", str(source),
                "--output", str(output),
                "--update-meta", str(meta),
                "--allow-unexpected-count",
                "--allow-unexpected-sha256",
            ])
            self.assertEqual(result, 0)

            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["areas"]), 64)
            self.assertEqual(manifest["totals"], {"pedNodes": 2, "vehicleNodes": 0, "naviNodes": 0, "links": 2})
            self.assertEqual(len(list(output.glob("area_*.json"))), 64)
            area_one = json.loads((output / "area_1.json").read_text(encoding="utf-8"))
            self.assertEqual(area_one["header"]["numPedNodes"], 2)
            self.assertEqual(area_one["ped"][0][0], 1)
            self.assertEqual(area_one["ped"][0][9][0][:2], [1, 2])
            empty_area = json.loads((output / "area_0.json").read_text(encoding="utf-8"))
            self.assertEqual(empty_area["ped"], [])
            self.assertIn('src="data/gta_nodes/area_63.json" download="false"', meta.read_text(encoding="utf-8"))

    def test_rejects_a_missing_or_nonreciprocal_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "bad.json"
            source.write_text(
                json.dumps([
                    {"id": 65537, "area": 1, "x": 1, "y": 2, "z": 3, "links": [65538]},
                    {"id": 65538, "area": 1, "x": 2, "y": 2, "z": 3, "links": []},
                ]),
                encoding="utf-8",
            )
            self.assertEqual(
                importer.main([
                    "--input", str(source),
                    "--allow-unexpected-count",
                    "--allow-unexpected-sha256",
                ]),
                1,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
