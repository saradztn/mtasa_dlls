#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static validation for the spider_sa MTA:SA resource.

Checks performed:
  * meta.xml is well-formed, every referenced script/file exists and the script
    types are valid, min_mta_version is declared
  * Lua syntax of every shipped .lua file (luaparse, when available)
  * the built TXD really is a readable RenderWare dictionary:
      - chunk structure consumes the file exactly (no trailing garbage)
      - texture count matches the number of TextureNative sections
      - every texture has an 88 byte D3D9 header, platform 9, a valid
        rasterFormat / d3dFormat pair, power-of-two dimensions, 32 bit depth
      - each mip level size equals width * height * 4 (32 bit uncompressed)
      - names are unique and short enough for the 32 byte name field
      - the SA legal combination of "mipmaps stored" vs "auto mipmaps" is used
  * the texture names requested by the DFF equal the names inside the TXD
    (this is what makes the model textured in game)
  * the COL3 header is valid and its bounds agree with the DFF geometry
  * no TODO/FIXME/placeholder markers are shipped

This is a static check only: it cannot run the GTA engine, so the visual result
inside MTA still has to be confirmed in game.

Usage: python3 spider_sa/tools/validate.py
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
RESOURCE = TOOLS.parent
ROOT = RESOURCE.parent

FAILURES: list[str] = []
NOTES: list[str] = []
SKIP_DIRS = {"node_modules", ".git", "docs"}

RW_VERSION = 0x1803FFFF
CHUNK_STRUCT = 0x01
CHUNK_STRING = 0x02
CHUNK_EXTENSION = 0x03
CHUNK_TEXTURE = 0x06
CHUNK_MATERIAL = 0x07
CHUNK_TEXNATIVE = 0x15
CHUNK_TEXDICT = 0x16

FORMAT_TO_D3D = {
    0x0100: {0x31545844, 0x00000000},        # 1555 / DXT1
    0x0200: {0x31545844, 0x00000000, 0x00000016},   # 565 / DXT1
    0x0300: {0x33545844, 0x00000000},        # 4444 / DXT3
    0x0400: {0x00000032, 0x00000000},        # LUM8 / D3DFMT_L8 (50)
    0x0500: {0x00000015, 0x00000000},        # 8888 / A8R8G8B8 (21)
    0x0600: {0x00000016, 0x00000000},        # 888  / X8R8G8B8 (22)
    0x0A00: {0x00000014, 0x00000000},        # 555  / X1R5G5B5 (20)
}


# ---------------------------------------------------------------------------
# generic RenderWare chunk walking
# ---------------------------------------------------------------------------
def parse_chunks(data: bytes, offset: int = 0, depth: int = 0, limit: int | None = None):
    """Walk a chunk sequence. Returns (list_of_nodes, end_offset).

    A chunk is treated as a container when its payload parses exactly as a
    nested chunk sequence bounded by the payload end; structs and strings are
    leaves, so the walker never mistakes raw binary data for chunk headers.
    """
    if limit is None:
        limit = len(data)
    nodes = []
    pos = offset
    while pos + 12 <= limit:
        ctype, csize, cver = struct.unpack_from("<III", data, pos)
        if csize > limit - pos - 12:
            break
        payload = pos + 12
        children = []
        if depth < 8 and csize >= 12:
            kids, end = parse_chunks(data, payload, depth + 1, payload + csize)
            if kids and end == payload + csize:
                children = kids
        nodes.append({
            "type": ctype,
            "size": csize,
            "version": cver,
            "offset": pos,
            "payload": payload,
            "children": children,
        })
        pos += 12 + csize
    return nodes, pos


def walk(nodes):
    for node in nodes:
        yield node
        for child in walk(node["children"]):
            yield child


def read_string(data: bytes, offset: int) -> str:
    raw = data[offset:offset + 32]
    return raw.split(b"\x00")[0].decode("latin-1", "replace")


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def check_meta() -> dict:
    meta_path = RESOURCE / "meta.xml"
    try:
        tree = ET.parse(meta_path)
    except ET.ParseError as exc:
        FAILURES.append(f"meta.xml is not well-formed: {exc}")
        return {}
    root = tree.getroot()
    if root.tag != "meta":
        FAILURES.append(f"meta.xml root element is <{root.tag}>, expected <meta>")

    scripts = []
    for script in root.findall("script"):
        src = script.get("src")
        stype = script.get("type", "server")
        if not src:
            FAILURES.append("a <script> element has no src attribute")
            continue
        if stype not in ("client", "server", "shared"):
            FAILURES.append(f"script {src}: invalid type {stype!r}")
        if not (RESOURCE / src).is_file():
            FAILURES.append(f"script listed in meta.xml does not exist: {src}")
        scripts.append({"src": src, "type": stype})

    files = []
    for entry in root.findall("file"):
        src = entry.get("src")
        if not src:
            FAILURES.append("a <file> element has no src attribute")
            continue
        if not (RESOURCE / src).is_file():
            FAILURES.append(f"file listed in meta.xml does not exist: {src}")
        files.append(src)

    info = root.find("info")
    if info is None:
        FAILURES.append("meta.xml has no <info> element")
    if root.find("min_mta_version") is None:
        FAILURES.append("meta.xml has no <min_mta_version> element")
    NOTES.append(f"meta.xml: {len(scripts)} script(s), {len(files)} file(s)")
    return {"scripts": scripts, "files": files}


def check_lua_syntax() -> None:
    lua_files = sorted(p for p in RESOURCE.rglob("*.lua") if not any(s in p.parts for s in SKIP_DIRS))
    if not lua_files:
        FAILURES.append("no Lua files found")
        return

    node = shutil.which("node")
    luaparse_dir = TOOLS / "node_modules"
    if node is None or not (luaparse_dir / "luaparse").exists():
        NOTES.append("luaparse not installed - Lua syntax check skipped "
                     "(run: npm install --prefix spider_sa/tools)")
        return

    script = (
        "const fs=require('fs');const luaparse=require('luaparse');"
        "let bad=0;"
        "for(const f of process.argv.slice(1)){"
        "  const src=fs.readFileSync(f,'utf8');"
        "  try{luaparse.parse(src,{luaVersion:'5.1',comments:false});}"
        "  catch(e){bad++;console.log('FAIL '+f+': '+e.message);}"
        "}"
        "process.exit(bad?1:0);"
    )
    try:
        proc = subprocess.run(
            [node, "-e", script, *[str(p) for p in lua_files]],
            cwd=str(TOOLS), capture_output=True, text=True, timeout=120,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin", "NODE_PATH": str(luaparse_dir)},
        )
    except Exception as exc:                                   # pragma: no cover
        NOTES.append(f"Lua syntax check could not run: {exc}")
        return
    if proc.returncode != 0:
        for line in proc.stdout.strip().splitlines():
            FAILURES.append(f"Lua syntax: {line}")
    else:
        NOTES.append(f"Lua syntax OK ({len(lua_files)} files, parsed as Lua 5.1 like MTA)")


def check_txd() -> list[str]:
    path = RESOURCE / "assets" / "Dragon_2.5.txd"
    if not path.is_file():
        FAILURES.append("assets/Dragon_2.5.txd is missing")
        return []
    data = path.read_bytes()
    nodes, end = parse_chunks(data)
    if end != len(data):
        FAILURES.append(f"TXD: chunk walk stopped at {end} of {len(data)} bytes")
    if len(nodes) != 1 or nodes[0]["type"] != CHUNK_TEXDICT:
        FAILURES.append("TXD: root chunk is not a TextureDictionary (0x16)")
        return []
    root = nodes[0]
    if root["version"] != RW_VERSION:
        FAILURES.append(f"TXD: root version {root['version']:#x} != {RW_VERSION:#x}")
    kids = root["children"]
    if not kids or kids[0]["type"] != CHUNK_STRUCT:
        FAILURES.append("TXD: dictionary has no leading Struct")
        return []
    struct_node = kids[0]
    if struct_node["size"] < 4:
        FAILURES.append("TXD: dictionary Struct is too small")
        return []
    declared = struct.unpack_from("<H", data, struct_node["payload"])[0]
    textures = [n for n in kids if n["type"] == CHUNK_TEXNATIVE]
    if declared != len(textures):
        FAILURES.append(f"TXD: dictionary declares {declared} textures, found {len(textures)}")
    if not any(n["type"] == CHUNK_EXTENSION for n in kids):
        FAILURES.append("TXD: dictionary has no trailing Extension chunk")

    names: list[str] = []
    for index, tex in enumerate(textures):
        body = tex["payload"]
        size = tex["size"]
        inner = tex["children"]
        if not inner or inner[0]["type"] != CHUNK_STRUCT:
            FAILURES.append(f"TXD texture {index}: missing Struct")
            continue
        st = inner[0]
        header = data[st["payload"]:st["payload"] + 88]
        if len(header) < 88:
            FAILURES.append(f"TXD texture {index}: header shorter than 88 bytes")
            continue
        platform, filter_flags = struct.unpack_from("<II", header, 0)
        name = read_string(header, 8)
        mask = read_string(header, 40)
        raster_format, d3d_format = struct.unpack_from("<II", header, 72)
        width, height = struct.unpack_from("<HH", header, 80)
        depth, num_levels, raster_type, flags = struct.unpack_from("<4B", header, 84)

        if platform != 9:
            FAILURES.append(f"TXD {name!r}: platform {platform}, expected 9 (D3D9)")
        if not name:
            FAILURES.append(f"TXD texture {index}: empty name")
        if len(name) > 31:
            FAILURES.append(f"TXD {name!r}: name longer than 31 characters")
        if name in names:
            FAILURES.append(f"TXD {name!r}: duplicate texture name")
        names.append(name)
        if mask:
            FAILURES.append(f"TXD {name!r}: unexpected alpha mask name {mask!r}")
        allowed = FORMAT_TO_D3D.get(raster_format & 0x0F00)
        if allowed is None:
            FAILURES.append(f"TXD {name!r}: unsupported rasterFormat {raster_format:#x}")
        elif d3d_format not in allowed:
            FAILURES.append(f"TXD {name!r}: d3dFormat {d3d_format:#x} does not match "
                            f"rasterFormat {raster_format:#x}")
        if depth != 32:
            FAILURES.append(f"TXD {name!r}: depth {depth}, expected 32")
        if raster_type != 4:
            FAILURES.append(f"TXD {name!r}: rasterType {raster_type}, expected 4")
        if num_levels < 1:
            FAILURES.append(f"TXD {name!r}: no mip levels")
        if flags & 0x04 and num_levels > 1:
            FAILURES.append(f"TXD {name!r}: auto mipmaps enabled while shipping "
                            f"{num_levels} levels - GTA:SA fails to load that")
        if flags & 0x08:
            FAILURES.append(f"TXD {name!r}: compressed bit set on an uncompressed raster")
        if width == 0 or height == 0 or (width & (width - 1)) or (height & (height - 1)):
            FAILURES.append(f"TXD {name!r}: dimensions {width}x{height} are not power of two")

        # mip level data must fill the struct
        pos = st["payload"] + 88
        total = 0
        for level in range(num_levels):
            if pos + 4 > st["payload"] + st["size"]:
                FAILURES.append(f"TXD {name!r}: level {level} header outside the struct")
                break
            (level_size,) = struct.unpack_from("<I", data, pos)
            pos += 4 + level_size
            total += level_size
            expected = max(1, width >> level) * max(1, height >> level) * 4
            if level_size != expected:
                FAILURES.append(f"TXD {name!r}: level {level} is {level_size} bytes, "
                                f"expected {expected} for 32 bit data")
        if pos != st["payload"] + st["size"]:
            FAILURES.append(f"TXD {name!r}: level data ends at {pos}, struct ends at "
                            f"{st['payload'] + st['size']}")
        if not any(n["type"] == CHUNK_EXTENSION for n in inner):
            FAILURES.append(f"TXD {name!r}: missing per texture Extension chunk")

    NOTES.append(f"TXD: {len(textures)} texture(s), {len(data)} bytes: {', '.join(names)}")
    return names


def dff_texture_names() -> list[str]:
    path = RESOURCE / "assets" / "Dragon_2.5.dff"
    if not path.is_file():
        FAILURES.append("assets/Dragon_2.5.dff is missing")
        return []
    data = path.read_bytes()
    nodes, end = parse_chunks(data)
    if end != len(data):
        FAILURES.append(f"DFF: chunk walk stopped at {end} of {len(data)} bytes")
    names = []
    for node in walk(nodes):
        if node["type"] != CHUNK_TEXTURE:
            continue
        strings = [read_string(data, c["payload"]) for c in node["children"] if c["type"] == CHUNK_STRING]
        if strings and strings[0]:
            names.append(strings[0])
    # the DFF stores one texture chunk per material that has a texture
    return names


def dff_geometry_bounds():
    path = RESOURCE / "assets" / "Dragon_2.5.dff"
    if not path.is_file():
        return None
    data = path.read_bytes()
    fromlib = None
    nodes, _ = parse_chunks(data)
    for node in walk(nodes):
        if node["type"] != 0x0F:      # geometry
            continue
        for child in node["children"]:
            if child["type"] != CHUNK_STRUCT:
                continue
            base = child["payload"]
            # RenderWare geometry struct layout (RW 3.5/3.6, GTA:SA):
            #   u16 flags | u8 texCoordCount | u8 pad | u32 numTriangles
            #   u32 numVertices | u32 numMorphTargets
            #   [u32*3 if version < 3.4]  prelit colors  UVs  triangles
            #   bounding sphere (4f) | hasVertices u32 | hasNormals u32
            #   vertices  normals
            flags, texcoords = struct.unpack_from("<HB", data, base)
            ntri, nvert, nmorph = struct.unpack_from("<III", data, base + 4)
            if nvert == 0 or ntri == 0:
                continue
            payload_end = child["payload"] + child["size"]
            pos = base + 16                        # header is 16 bytes
            if child["version"] < 0x34000:
                pos += 12
            if flags & 0x08:                      # prelit vertex colours
                pos += nvert * 4
            if flags & 0x04 or flags & 0x80:      # one or two UV sets
                pos += max(1, texcoords) * nvert * 8 if flags & 0x04 else 0
                if flags & 0x80:
                    pos += nvert * 8
            pos += ntri * 8                        # triangles
            pos += 16 + 8                          # sphere + hasVertices/hasNormals
            if pos + nvert * 12 > payload_end:
                FAILURES.append("DFF: geometry vertex block runs past the struct")
                continue
            xs, ys, zs = [], [], []
            p = pos
            for _ in range(nvert):
                x, y, z = struct.unpack_from("<3f", data, p)
                xs.append(x); ys.append(y); zs.append(z)
                p += 12
            nonfinite = sum(1 for i in range(nvert)
                            if not (math.isfinite(xs[i]) and math.isfinite(ys[i]) and math.isfinite(zs[i])))
            if nonfinite:
                FAILURES.append(f"DFF: {nonfinite} non-finite vertices")
            finite = [i for i in range(nvert) if math.isfinite(xs[i])]
            if not finite:
                continue
            fromlib = (
                (min(xs[i] for i in finite), min(ys[i] for i in finite), min(zs[i] for i in finite)),
                (max(xs[i] for i in finite), max(ys[i] for i in finite), max(zs[i] for i in finite)),
                ntri, nvert,
            )
            break
        if fromlib:
            break
    return fromlib


def check_col(expected_bounds) -> None:
    path = RESOURCE / "assets" / "Dragon_2.5.col"
    if not path.is_file():
        FAILURES.append("assets/Dragon_2.5.col is missing")
        return
    data = path.read_bytes()
    if data[:4] != b"COL3":
        FAILURES.append(f"COL: magic is {data[:4]!r}, expected b'COL3'")
        return
    declared, = struct.unpack_from("<I", data, 4)
    if declared != len(data) - 8:
        FAILURES.append(f"COL: declared size {declared}, file has {len(data) - 8} bytes")
    name = read_string(data, 8)
    (model_id,) = struct.unpack_from("<H", data, 30)
    bmin = struct.unpack_from("<3f", data, 32)
    bmax = struct.unpack_from("<3f", data, 44)
    NOTES.append(f"COL: {name!r} model id {model_id}, bounds "
                 f"({bmin[0]:.3f}, {bmin[1]:.3f}, {bmin[2]:.3f}) .. "
                 f"({bmax[0]:.3f}, {bmax[1]:.3f}, {bmax[2]:.3f})")
    if expected_bounds:
        dmin, dmax, ntri, nvert = expected_bounds
        NOTES.append(f"DFF geometry: {ntri} triangles, {nvert} vertices, bounds "
                     f"({dmin[0]:.3f}, {dmin[1]:.3f}, {dmin[2]:.3f}) .. "
                     f"({dmax[0]:.3f}, {dmax[1]:.3f}, {dmax[2]:.3f})")
        for axis in range(3):
            if abs(bmin[axis] - dmin[axis]) > 0.1 or abs(bmax[axis] - dmax[axis]) > 0.1:
                FAILURES.append(f"COL bounds differ from the DFF geometry on axis {axis} "
                                f"({bmin[axis]:.3f}..{bmax[axis]:.3f} vs "
                                f"{dmin[axis]:.3f}..{dmax[axis]:.3f})")


def check_markers() -> None:
    markers = ("TODO", "FIXME", "XXX", "PLACEHOLDER", "implement later")
    for path in sorted(RESOURCE.rglob("*")):
        if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
            continue
        if path.suffix.lower() not in (".lua", ".xml", ".py", ".js", ".md"):
            continue
        if path.name in ("validate.py", "smoke_test.js"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker.lower() in text.lower():
                FAILURES.append(f"{path.relative_to(RESOURCE)} contains {marker!r}")


def main() -> int:
    meta = check_meta()
    check_lua_syntax()
    txd_names = check_txd()
    dff_names = dff_texture_names()
    bounds = dff_geometry_bounds()
    check_col(bounds)
    check_markers()

    if dff_names and txd_names:
        missing = [n for n in dff_names if n not in txd_names]
        extra = [n for n in txd_names if n not in dff_names]
        if missing:
            FAILURES.append(f"textures requested by the DFF but missing from the TXD: {missing}")
        if extra:
            NOTES.append(f"TXD holds textures the DFF does not use: {extra}")
        if not missing:
            NOTES.append("every texture name requested by the DFF exists in the TXD")
    if not meta.get("files"):
        FAILURES.append("meta.xml declares no asset files")

    print("spider_sa static validation")
    print("-" * 62)
    for note in NOTES:
        print("  note   " + note)
    for failure in FAILURES:
        print("  FAIL   " + failure)
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1
    print("\nAll static checks passed")
    print("(this validates structure and syntax, not the in-game result)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
