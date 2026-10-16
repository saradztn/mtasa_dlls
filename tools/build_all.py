"""One-click build for PROJECT ROYAL FORTRESS (remake).
Runs: materials (TXD) -> build (DFF/COL/world) -> make_meta -> validate -> make_docs.
Usage: python tools/build_all.py   (from project root) or run tools/build_all.bat on Windows.
"""
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PY = sys.executable

STEPS = [
    ("materials", [PY, str(HERE / "materials.py")]),
    ("build", [PY, str(HERE / "build.py")]),
    ("make_meta", [PY, str(HERE / "make_meta.py")]),
    ("validate", [PY, str(HERE / "validate.py")]),
]

def main():
    t0 = time.time()
    for name, cmd in STEPS:
        print("\n===== %s =====" % name, flush=True)
        r = subprocess.run(cmd, cwd=str(ROOT))
        if r.returncode != 0:
            print("STEP FAILED:", name, "exit", r.returncode)
            sys.exit(r.returncode)
    # docs (optional; needs runtime tests)
    try:
        subprocess.run([PY, str(HERE / "test_runtime.py")], cwd=str(ROOT), check=False)
        subprocess.run([PY, str(HERE / "make_docs.py")], cwd=str(ROOT), check=False)
    except Exception as e:
        print("docs step skipped:", e)
    print("\nBUILD COMPLETE in %.1fs" % (time.time() - t0))

if __name__ == "__main__":
    main()
