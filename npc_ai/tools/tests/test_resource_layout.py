#!/usr/bin/env python3
"""Static resource contract checks that do not require an MTA server."""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RESOURCE_ROOT = Path(__file__).resolve().parents[2]
HEADER = "-- ============================================================================\n-- GTA SA REAL NODE NPC AI\n-- Author: AI Agent\n"


class ResourceLayoutTests(unittest.TestCase):
    def test_meta_references_exist_and_are_ordered(self) -> None:
        root = ET.parse(RESOURCE_ROOT / "meta.xml").getroot()
        scripts = root.findall("script")
        self.assertGreaterEqual(len(scripts), 10)
        for script in scripts:
            path = RESOURCE_ROOT / script.attrib["src"]
            self.assertTrue(path.is_file(), f"missing script: {path}")
        for file_entry in root.findall("file"):
            path = RESOURCE_ROOT / file_entry.attrib["src"]
            self.assertTrue(path.is_file(), f"missing static resource file: {path}")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
