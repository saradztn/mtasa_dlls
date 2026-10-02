# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# audio_qc.py - checks every WAV (format, peak, rms, silence, loop seam) and draws a spectrogram sheet to ../preview/audio_spectrograms.png
import os, sys, wave
import numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audio')
rows, bad = [], []
for fn in sorted(os.listdir(D)):
    if not fn.endswith('.wav'): continue
    w = wave.open(os.path.join(D, fn))
    n, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
    x = np.frombuffer(w.readframes(n), '<i2').astype(float) / 32768
    peak, rms = np.abs(x).max(), np.sqrt((x ** 2).mean())
    seam = abs(x[0] - x[-1]) / max(np.abs(np.diff(x)).mean(), 1e-9)
    loop = fn.endswith('_loop.wav')
    spec = np.abs(np.fft.rfft(x)); f = np.fft.rfftfreq(n, 1 / sr); cen = (spec * f).sum() / spec.sum()
    ok = (ch == 1 and sw == 2 and sr == 22050 and 0.3 < peak < 0.99 and rms > 0.02 and (not loop or seam < 12))
    rows.append((fn, n / sr, peak, rms, seam if loop else float('nan'), cen))
    print('%-20s %5.2fs peak %.2f rms %.3f centroid %5.0f Hz  %s %s' % (fn, n / sr, peak, rms, cen, ('seam %.1fx' % seam) if loop else '', 'OK' if ok else 'BAD'))
    if not ok: bad.append(fn)
# spectrogram sheet
cells = []
for fn, *_ in rows:
    w = wave.open(os.path.join(D, fn)); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
    N, hop = 512, 256
    fr = np.array([np.abs(np.fft.rfft(x[i:i + N] * np.hanning(N))) for i in range(0, max(len(x) - N, 1), hop)]).T
    fr = np.log1p(fr * 30); fr = fr / fr.max()
    im = Image.fromarray((np.flipud(fr[:200]) * 255).astype(np.uint8)).resize((360, 120))
    cells.append((fn, im))
sheet = Image.new('L', (3 * 364, 5 * 124), 20)
for i, (fn, im) in enumerate(cells): sheet.paste(im, ((i % 3) * 364, (i // 3) * 124))
os.makedirs(os.path.join(D, '..', 'preview'), exist_ok=True)
sheet.save(os.path.join(D, '..', 'preview', 'audio_spectrograms.png'))
print('BAD:', bad); sys.exit(1 if bad else 0)
