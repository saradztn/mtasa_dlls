# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline  (contact sheet of all textures, QA only)
import time, numpy as np, sys, traceback
sys.path.insert(0, '.')
from pk import tex
from PIL import Image
t0 = time.time(); cells = []
only = sys.argv[1:] 
for n in tex.NAMES:
    if only and n not in only: continue
    t = time.time()
    try:
        a = (np.clip(tex.GEN[n](), 0, 1) * 255 + .5).astype(np.uint8)
    except Exception:
        print('FAIL', n); traceback.print_exc(); continue
    print('%-16s %s %.1fs' % (n, a.shape, time.time() - t))
    im = Image.fromarray(a, 'RGBA' if a.shape[2] == 4 else 'RGB').convert('RGBA')
    if a.shape[2] == 4:
        bg = Image.new('RGBA', im.size, (120, 150, 200, 255)); bg.alpha_composite(im); im = bg
    cells.append(im.resize((200, max(4, int(200 * a.shape[0] / a.shape[1])))).convert('RGB'))
cols = 7; rows = (len(cells) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 204, rows * 204), (30, 30, 30))
for i, c in enumerate(cells): sheet.paste(c, ((i % cols) * 204, (i // cols) * 204))
sheet.save('_work/tex_sheet.png'); print('total %.1fs' % (time.time() - t0))
