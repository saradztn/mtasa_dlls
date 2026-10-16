#!/usr/bin/env python3
"""Reproducible Royal Palace asset build and MTA resource packager."""
from pathlib import Path
import sys, subprocess, shutil, json, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent

def main():
    if sys.version_info < (3,9): raise SystemExit('Python 3.9+ required')
    venv=ROOT/'.venv'; py=venv/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    if not py.exists():
        subprocess.check_call([sys.executable,'-m','venv',str(venv)])
    pip=venv/('Scripts/pip.exe' if sys.platform=='win32' else 'bin/pip')
    subprocess.check_call([str(pip),'install','-r',str(ROOT/'requirements.txt')])
    def run(script): subprocess.check_call([str(py),str(ROOT/script)],cwd=ROOT)
    run('materials.py'); run('generator/build_assets.py')
    w=json.loads((ROOT/'client/data/world.json').read_text(encoding='utf8'))
    out=ROOT/'output/RoyalPalace'; staging=ROOT/'output/.RoyalPalace-staging'
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    for d in ('assets','client/data'): shutil.copytree(ROOT/d,staging/d)
    shutil.copy2(ROOT/'client.lua',staging/'client.lua')
    (staging/'server').mkdir()
    shutil.copy2(ROOT/'server/main.lua',staging/'server/main.lua')
    files=['client.lua','server/main.lua','client/data/world.json']
    for t in w['txds'].values(): files.append(t['path'])
    for m in w['models'].values(): files.extend([m['dff'],m['col']])
    meta=ET.Element('meta'); ET.SubElement(meta,'info',{'name':'RoyalPalace AAA','author':'RoyalPalace build pipeline','version':'1.0.0','type':'script','description':'Royal Palace environment with genuine DFF/COL/TXD assets'})
    ET.SubElement(meta,'script',{'src':'server/main.lua','type':'server','cache':'true'})
    ET.SubElement(meta,'script',{'src':'client.lua','type':'client','cache':'true'})
    for f in sorted(set(files)): ET.SubElement(meta,'file',{'src':f,'download':'true'})
    ET.indent(meta,space='  '); ET.ElementTree(meta).write(staging/'meta.xml',encoding='utf-8',xml_declaration=True)
    ET.parse(staging/'meta.xml')
    ET.ElementTree(meta).write(ROOT/'meta.xml',encoding='utf-8',xml_declaration=True)
    # Validate the generated binaries and room connectivity before promoting staging.
    subprocess.check_call([str(py),str(ROOT/'validate.py')],cwd=ROOT)
    if out.exists(): shutil.rmtree(out)
    staging.rename(out)
    report={'models':len(w['models']),'instances':len(w['objects']),'rooms':len(w['rooms']),'vertices':w['stats']['vertices'],'triangles':w['stats']['triangles'],'txds':len(w['txds']),'resource':str(out)}
    (ROOT/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('\nBUILD SUCCESS — '+json.dumps(report,ensure_ascii=False))
if __name__=='__main__': main()
