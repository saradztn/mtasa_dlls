"""Generate meta.xml (scripts + every exported asset) and the procedural flame sprite."""
import json, math
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent


def flame_png(path):
    w, h = 64, 128; img = Image.new('RGBA', (w, h)); px = img.load()
    for y in range(h):
        t = y / (h - 1)                     # 0 = top (tip), 1 = bottom
        half = 0.42 * w * (math.sin(math.pi * min(1, t * 1.08)) ** 0.9) * (0.35 + 0.65 * t)
        for x in range(w):
            d = abs(x - (w - 1) / 2) / max(half, 1e-3)
            if d >= 1: continue
            core = max(0.0, 1 - d) ** 1.6
            a = core * min(1, (1 - t) * 6) * min(1, t * 4 + .2)
            r = 255; g = int(140 + 110 * core * t); b = int(40 + 170 * core ** 3 * t)
            px[x, y] = (r, min(g, 255), min(b, 255), int(255 * min(1, a * 1.25)))
    path.parent.mkdir(parents=True, exist_ok=True); img.save(path)


def main():
    flame_png(ROOT / 'client' / 'img' / 'flame.png')
    W = json.loads((ROOT / 'client' / 'data' / 'world.json').read_text())
    files = ['client/data/world.json', 'client/img/flame.png']
    from pathlib import Path as _P
    for _f in sorted((_P(ROOT) / 'client' / 'shaders').glob('*.fx')):
        files.append(_f.relative_to(ROOT).as_posix())
    files += [v['path'] for v in W['txds'].values()]
    for m in W['models'].values(): files += [m['col'], m['dff']]
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<meta>',
           '  <info name="Royal Fortress" author="Royal Fortress project" version="%s" type="script" description="Explorable royal fortress: 109 spaces, 27 mechanisms, real DFF/TXD/COL" />' % '2.0.0-remake-beta',
           '  <min_mta_version server="1.6.0" client="1.6.0-9.22678" />', '  <oop>false</oop>',
           '  <script src="shared/config.lua" type="shared" cache="true" />',
           '  <script src="server/main.lua" type="server" />']
    for s in ('models', 'scene', 'mechanisms', 'lights', 'hud', 'core'):
        out.append('  <script src="client/%s.lua" type="client" cache="true" />' % s)
    for f in sorted(set(files)):
        assert (ROOT / f).exists(), f
        out.append('  <file src="%s" download="true" />' % f)
    out.append('</meta>')
    (ROOT / 'meta.xml').write_text('\n'.join(out) + '\n')
    print('meta.xml: %d files' % len(set(files)))


if __name__ == '__main__':
    main()
