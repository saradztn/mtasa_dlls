"""Rebuild and validate, failing on any failed stage. Run from any directory."""
from pathlib import Path
import argparse,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--skip-blender',action='store_true');p.add_argument('--environment-only',action='store_true');p.add_argument('--render',action='store_true');p.add_argument('--animation-previews',action='store_true');p.add_argument('--package',action='store_true');a=p.parse_args()
if a.skip_blender and a.environment_only:p.error("--skip-blender and --environment-only cannot be combined")
def run(name,*args):subprocess.run([sys.executable,str(ROOT/'tools'/name),*args],check=True,cwd=ROOT)
subprocess.run([sys.executable,str(ROOT/'tools/material_generator.py'),'--all'],check=True)
run('build_geometry.py');run('build_runtime.py')
if not a.skip_blender:
    run('build_blender.py',*(['--environment-only'] if a.environment_only else []))
    for f in ROOT.rglob('*.blend1'):f.unlink()
    if not a.environment_only:
        run('validate_fbx.py')
        run('validate_animation_contacts.py')
        run('validate_reference_skin.py')
    run('validate_sources.py')
run('validate.py');run('test_client.py');run('test_lighting.py');run('test_interactions.py');run('test_architecture.py')
if a.render:run('render_inspection.py')
if a.animation_previews:
    run('render_animation_previews.py');run('validate_animation_previews.py')
run('write_report.py')
if a.package:
    out=ROOT/'dist';out.mkdir(exist_ok=True);path=out/'ProjectSquidGenesis.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,6) as z:
        for f in sorted(ROOT.rglob('*')):
            if not f.is_file() or any(v in ('dist','__pycache__','.venv') for v in f.relative_to(ROOT).parts) or f.suffix in ('.pyc','.blend1'):continue
            z.write(f,Path('ProjectSquidGenesis')/f.relative_to(ROOT))
    print('ZIP:',path,path.stat().st_size,'bytes')
