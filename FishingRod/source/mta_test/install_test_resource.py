# Created by: Arena.ai Agent Mode (AI) - FishingRod MTA:SA asset pipeline
# Copies the shipped assets next to meta.xml so this folder is a ready-to-start MTA resource:
#   python3 install_test_resource.py [path/to/mods/deathmatch/resources]
# then in game:  /start FishingRod_test   and   /fishrod
import os, shutil, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, '..', '..'))
dst = os.path.join(here, 'FishingRod_test')
os.makedirs(os.path.join(dst, 'maps'), exist_ok=True)
for src, name in (('model/FishingRod.dff', 'FishingRod.dff'), ('texture/FishingRod.txd', 'FishingRod.txd'),
                  ('collision/FishingRod.col', 'FishingRod.col')):
    shutil.copy(os.path.join(root, src), os.path.join(dst, name))
for f in os.listdir(os.path.join(root, 'texture', 'maps')):
    shutil.copy(os.path.join(root, 'texture', 'maps', f), os.path.join(dst, 'maps', f))
for f in ('meta.xml', 'client.lua', 'shader.fx'):
    shutil.copy(os.path.join(here, f), os.path.join(dst, f))
print('resource written to', dst)
if len(sys.argv) > 1:
    out = os.path.join(sys.argv[1], 'FishingRod_test')
    shutil.copytree(dst, out, dirs_exist_ok=True)
    print('copied to', out)
