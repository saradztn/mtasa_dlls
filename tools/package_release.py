#!/usr/bin/env python3
"""
NextGenPoliceDepartment - MTA:SA Resource Packager (tools/package_release.py)

Packages the validated MTA:SA 1.6 resource (`meta.xml`, `shared/`, `server/`, `client/`,
`shaders/`, `models/`, `collisions/`, `textures/`) into `dist/NextGenPoliceDepartment.zip`
and writes `docs/RELEASE_MANIFEST.json`.
"""
from __future__ import annotations
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def package_resource() -> dict:
    dist_dir = ROOT / "dist"
    docs_dir = ROOT / "docs"
    dist_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    meta_path = ROOT / "meta.xml"
    root_el = ET.parse(meta_path).getroot()
    scripts = [s.get("src") for s in root_el.findall("script")]
    files = [f.get("src") for f in root_el.findall("file")]

    all_entries = ["meta.xml"] + scripts + files
    seen = set()
    ordered = []
    for rel in all_entries:
        if rel not in seen:
            seen.add(rel)
            ordered.append(rel)

    zip_path = dist_dir / "NextGenPoliceDepartment.zip"
    uncompressed_bytes = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel in ordered:
            p = ROOT / rel
            assert p.is_file() and p.stat().st_size > 0, f"Missing or empty resource file: {rel}"
            uncompressed_bytes += p.stat().st_size
            zf.write(p, arcname=rel)

    zip_bytes = zip_path.stat().st_size
    zip_sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    manifest = {
        "resource_name": "NextGenPoliceDepartment",
        "mta_version_min": {"client": "1.6.0", "server": "1.5.9"},
        "package_path": "dist/NextGenPoliceDepartment.zip",
        "compressed_bytes": zip_bytes,
        "uncompressed_bytes": uncompressed_bytes,
        "sha256": zip_sha256,
        "script_count": len(scripts),
        "asset_file_count": len(files),
        "total_packaged_files": len(ordered),
    }
    (docs_dir / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    info = package_resource()
    print(json.dumps(info, indent=2))
