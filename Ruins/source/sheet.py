# Created by: Arena.ai Agent Mode (AI) - Ruins MTA:SA asset pipeline
import sys, time, numpy as np
from PIL import Image
sys.path.insert(0, '.')
import importlib
mod = importlib.import_module('rn.' + sys.argv[1])
names = sys.argv[3:] or list(mod.GEN)
T = 256; cols = 6
rows = (len(names) + cols - 1) // cols
sheet = Image.new('RGB', (cols * T, rows * T), (40, 0, 40))
for i, n in enumerate(names):
    t = time.time()
    a = np.clip(mod.GEN[n](), 0, 1)
    print(n, a.shape, '%.1fs' % (time.time() - t), 'mean %.2f' % a[..., :3].mean(), flush=True)
    rgb = a[..., :3]
    if a.shape[2] == 4:
        bg = np.where(((np.arange(a.shape[0])[:, None] // 32 + np.arange(a.shape[1])[None, :] // 32) % 2)[..., None] == 0, 0.25, 0.4)
        rgb = rgb * a[..., 3:4] + bg * (1 - a[..., 3:4])
    im = Image.fromarray((rgb * 255).astype(np.uint8)).resize((T, T), Image.LANCZOS)
    sheet.paste(im, ((i % cols) * T, (i // cols) * T))
sheet.save(sys.argv[2])
