# Royal Fortress - Remake (beta)

MTA:SA resource: procedural fortress assets (DFF/COL/TXD) + Lua scripts.

## One-click build (Windows)

1. Install Python 3.10+ (https://www.python.org) and check "Add to PATH".
2. Double-click `tools/build_all.bat` (or run `python tools/build_all.py`).
   It creates nothing manually: installs deps, generates textures, builds all assets,
   writes meta.xml, runs the validator.

## Manual build

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
.venv/bin/pip install -r requirements.txt       # Linux/macOS
python tools/materials.py
python tools/build.py
python tools/make_meta.py
python tools/validate.py
```

## Shaders

Wet-floor reflection shader: `client/shaders/wet_floor.fx`.
Apply in client Lua with `engineApplyShaderToWorldTexture(shader, "rf_marble*")` etc.

## Outputs

- `assets/` - DFF/COL/TXD
- `client/data/world.json` - streaming manifest
- `docs/rooms.json`, `docs/validation_report.json`
- `meta.xml`
