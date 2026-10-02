# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# texsheet.py - contact sheet of every texture: python3 texsheet.py [out.png] [first] [last]
import sys, time
import numpy as np
from PIL import Image
sys.path.insert(0, '.')
from af import tex
a, b = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, len(tex.NAMES))
names = tex.NAMES[a:b]
t = time.time()
TS = 256
cols = 6
rows = (len(names) + cols - 1) // cols
sheet = np.zeros((rows * TS, cols * TS, 3), np.uint8)
for i, n in enumerate(names):
    t0 = time.time()
    im = np.clip(tex.GEN[n](), 0, 1)
    im = (im * 255 + .5).astype(np.uint8)
    pil = Image.fromarray(im, 'RGBA' if im.shape[2] == 4 else 'RGB').resize((TS, TS), Image.LANCZOS)
    arr = np.asarray(pil).astype(np.float32)
    if arr.shape[2] == 4:
        chk = (((np.arange(TS)[:, None] // 16) + (np.arange(TS)[None, :] // 16)) % 2 * 60 + 90).astype(np.float32)[..., None]
        al = arr[..., 3:4] / 255
        arr = arr[..., :3] * al + chk * (1 - al)
    y, x = divmod(i, cols)
    sheet[y * TS:(y + 1) * TS, x * TS:(x + 1) * TS] = arr[..., :3].astype(np.uint8)
    print('%-18s %.2fs' % (n, time.time() - t0))
Image.fromarray(sheet).save(sys.argv[1] if len(sys.argv) > 1 else '_work/tex_sheet.png')
print('total %.1fs' % (time.time() - t))
