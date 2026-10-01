"""
Static validation for the gta4_physics MTA:SA resource.

Checks performed:
  * Lua syntax of every .lua file (uses the luaparse CLI when available)
  * meta.xml well-formedness and referenced script/file existence
  * script load order vs. cross-file GTA4Physics references
  * flags TODO/FIXME/placeholder markers

This is a static check only. It cannot validate MTA runtime behaviour.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESOURCE = ROOT
while RESOURCE != RESOURCE.parent and not (RESOURCE / "meta.xml").is_file():
    RESOURCE = RESOURCE.parent
if not (RESOURCE / "meta.xml").is_file():
    raise SystemExit("Could not locate the gta4_physics meta.xml")
FAILURES: list[str] = []
SKIP_DIRS = {"node_modules", ".git"}


def fail(message: str) -> None:
    FAILURES.append(message)
    print(f"FAIL: {message}")


def resource_files(pattern: str):
    for path in sorted(RESOURCE.rglob(pattern)):
        if any(part in SKIP_DIRS for part in path.relative_to(RESOURCE).parts):
            continue
        yield path


def syntax_check() -> None:
    lua_files = list(resource_files("*.lua"))
    print(f"Lua files found: {len(lua_files)}")
    npx = shutil.which("npx")
    if npx:
        result = subprocess.run(
            [npx, "--yes", "luaparse", "--quiet", *[str(p) for p in lua_files]],
            capture_output=True, text=True, check=False, cwd=str(RESOURCE),
        )
        if result.returncode != 0:
            fail(f"luaparse reported syntax errors:\n{result.stdout}\n{result.stderr}")
        else:
            print("Lua syntax: OK (luaparse)")
    else:
        print("WARNING: npx/luaparse not available; skipped syntax parsing")


def meta_check() -> list[tuple[str, str]]:
    meta = RESOURCE / "meta.xml"
    try:
        root = ET.parse(meta).getroot()
    except ET.ParseError as exc:  # pragma: no cover
        fail(f"meta.xml is not well-formed XML: {exc}")
        return []
    print("meta.xml: well-formed")
    ordered: list[tuple[str, str]] = []
    for script in root.findall("script"):
        src, kind = script.get("src"), script.get("type", "server")
        if not (RESOURCE / src).is_file():
            fail(f"meta.xml references a missing script: {src}")
        ordered.append((src, kind))
    for node in root.findall("file"):
        if not (RESOURCE / node.get("src", "")).is_file():
            fail(f"meta.xml references a missing file: {node.get('src')}")
    for node in root.findall("export"):
        if not node.get("function"):
            fail("meta.xml contains an <export> without a function name")
    print(f"meta.xml scripts: {len(ordered)}")
    return ordered


ASSIGN = re.compile(r"^\s*(?:function\s+)?(GTA4Physics|G4)\.([A-Za-z0-9_]+)\s*=", re.M)
ASSIGN_ALIAS = re.compile(r"^\s*local\s+([A-Za-z0-9_]+)\s*=\s*(?:GTA4Physics|G4)\.([A-Za-z0-9_]+)\s*$", re.M)
ASSIGN_NS_FUNC = re.compile(r"^\s*function\s+(GTA4Physics|G4)\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", re.M)
MULTI_ASSIGN = re.compile(r"^\s*([A-Za-z0-9_.\s,]+?)\s*=[^=]")
TOKEN = re.compile(r"([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)")
USE_NS = re.compile(r"\b([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\b")


def _constructor_keys(text: str, start: int, prefix: str, members: set[tuple[str, str]]) -> None:
    depth = 0
    word = ""
    for index in range(start, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            outer_depth = depth
            depth -= 1
            if outer_depth == 1:
                match = re.match(r"\s*([A-Za-z0-9_]+)\s*=", word)
                if match:
                    members.add((prefix, match.group(1)))
            if depth <= 0:
                return
        elif character in "\n," and depth == 1:
            match = re.match(r"\s*([A-Za-z0-9_]+)\s*=", word)
            if match:
                members.add((prefix, match.group(1)))
            word = ""
        else:
            word += character


def defined_symbols() -> tuple[set[str], set[tuple[str, str]]]:
    modules: set[str] = set()
    members: set[tuple[str, str]] = set()
    for path in resource_files("*.lua"):
        text = path.read_text(encoding="utf-8")
        for _, name in ASSIGN.findall(text):
            modules.add(name)
        for _, module, member in ASSIGN_NS_FUNC.findall(text):
            members.add((module, member))
        aliases = {alias: module for alias, module in ASSIGN_ALIAS.findall(text)}
        if aliases:
            for alias, module in aliases.items():
                pattern = re.compile(r"^\s*function\s+" + re.escape(alias) + r"\.([A-Za-z0-9_]+)", re.M)
                for member in pattern.findall(text):
                    members.add((module, member))
        for line in text.splitlines():
            left_side = MULTI_ASSIGN.match(line)
            if not left_side:
                continue
            for prefix, member in TOKEN.findall(left_side.group(1)):
                module = aliases.get(prefix, prefix)
                if module == "Math":
                    continue
                members.add((module, member))
        for match in re.finditer(r"(?:GTA4Physics|G4)\.([A-Za-z0-9_]+)\s*=\s*\{", text):
            _constructor_keys(text, match.end() - 1, match.group(1), members)
        for alias, module in aliases.items():
            if module == "Math":
                continue
            for match in re.finditer(re.escape(alias) + r"\s*=\s*\{", text):
                _constructor_keys(text, match.end() - 1, module, members)
    return modules, members


def reference_check(order: list[tuple[str, str]]) -> None:
    modules, members = defined_symbols()
    allowed_prefixes = {
        "Config", "State", "Math", "VehicleClasses", "VehicleDatabase", "Surfaces",
        "PhysicsCore", "Suspension", "TireModel", "WeightTransfer", "Steering",
        "Transmission", "Drivetrain", "Braking", "AirDynamics", "Collision", "Adapter",
        "Sync", "Performance", "Telemetry", "Calibration", "Visualizer", "Debug",
        "Commands", "VehicleManager", "copyTable", "isFinite", "safeNumber", "log",
        "notify", "VERSION",
    }
    problems = 0
    for path in resource_files("*.lua"):
        text = path.read_text(encoding="utf-8")
        aliases = {alias: module for alias, module in ASSIGN_ALIAS.findall(text)}
        for prefix, member in USE_NS.findall(text):
            module = aliases.get(prefix, prefix)
            if module not in allowed_prefixes:
                continue
            if module in {"Config", "State", "Math", "VehicleClasses", "VehicleDatabase"}:
                continue
            if (module, member) not in members:
                problems += 1
                fail(f"{path.relative_to(RESOURCE)} references undefined {module}.{member}")
    if problems == 0:
        print(f"Cross-file namespace references: OK ({len(members)} members registered)")

    seen_shared = False
    seen_client = False
    for src, kind in order:
        if kind in {"shared", "client"} and not seen_shared:
            seen_shared = True
        if kind == "client":
            seen_client = True
    if not seen_shared or not seen_client:
        fail("meta.xml must include shared configuration and client scripts")



MARKERS = re.compile(r"\b(TODO|FIXME|XXX|placeholder|pseudocode|implement later)\b", re.I)


def marker_check() -> None:
    found = 0
    # Documentation legitimately mentions these words, so only code/manifest files
    # are scanned for unfinished markers.
    for path in resource_files("*"):
        if path.suffix not in {".lua", ".xml"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MARKERS.search(line):
                found += 1
                fail(f"unfinished marker at {path.relative_to(RESOURCE)}:{number}: {line.strip()}")
    if found == 0:
        print("Placeholder/TODO markers: none")


def main() -> int:
    print(f"Resource: {RESOURCE}")
    syntax_check()
    order = meta_check()
    reference_check(order)
    marker_check()
    if FAILURES:
        print(f"\n{len(FAILURES)} issue(s) found")
        return 1
    print("\nAll static checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
