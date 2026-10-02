# Created by: Arena.ai Agent Mode (AI) - Ashfall MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# audio.py - procedural ambience of the dead city: wind, distant rumble, crickets, creaking metal, crows and small
#            birds.  All files are short loops / one-shots, 22050 Hz mono 16 bit.
# -----------------------------------------------------------------------------
import os
import wave
import numpy as np

SR = 22050


def _write(path, x):
    x = np.clip(x, -1, 1)
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((x * 32000).astype('<i2').tobytes())
    w.close()
    return os.path.basename(path)


def _loop(x):
    """crossfade the ends so the loop has no click"""
    n = int(SR * 0.25)
    t = np.linspace(0, 1, n)
    x[:n] = x[:n] * t + x[-n:] * (1 - t)
    return x


def wind(d=9.0, seed=1):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    x = r.standard_normal(n)
    k = np.ones(900) / 900
    x = np.convolve(x, k, 'same')
    x += 0.4 * np.convolve(r.standard_normal(n), np.ones(140) / 140, 'same')
    t = np.arange(n) / SR
    gust = 0.55 + 0.45 * (np.sin(t * 0.5) * 0.5 + np.sin(t * 0.23 + 2) * 0.3 + np.sin(t * 1.1 + 4) * 0.2)
    x = x * gust
    x /= np.abs(x).max()
    return _loop(x * 0.9)


def rumble(d=10.0, seed=2):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    x = np.convolve(r.standard_normal(n), np.ones(2400) / 2400, 'same')
    t = np.arange(n) / SR
    x = x * (0.5 + 0.5 * np.sin(t * 0.31))
    for _ in range(4):                      # distant collapses
        t0 = int(r.uniform(0.5, d - 2.5) * SR)
        L = int(r.uniform(0.8, 1.8) * SR)
        th = r.standard_normal(L) * np.exp(-np.arange(L) / (SR * 0.5))
        th = np.convolve(th, np.ones(600) / 600, 'same')
        x[t0:t0 + L] += th * 0.8
    x /= np.abs(x).max()
    return _loop(x * 0.85)


def crickets(d=7.0, seed=3):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    x = np.zeros(n)
    t = np.arange(n) / SR
    for f0 in (4300.0, 4700.0):
        ph = 2 * np.pi * f0 * t
        tr = (np.sin(2 * np.pi * 24 * t + r.uniform(0, 6)) > 0.2) * (np.sin(2 * np.pi * 0.7 * t + r.uniform(0, 6)) > -0.2)
        x += np.sin(ph) * tr * 0.5
    x /= np.abs(x).max()
    return _loop(x * 0.8)


def creak(seed=4):
    r = np.random.default_rng(seed)
    d = 2.2
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 320 * np.exp(-t * 0.8) + 90 * np.sin(t * 9) * np.exp(-t)
    ph = np.cumsum(2 * np.pi * f / SR)
    x = np.sin(ph) + 0.5 * np.sin(ph * 2.02)
    x *= np.exp(-t * 1.6) * (0.6 + 0.4 * np.sin(t * 30))
    x /= np.abs(x).max()
    return x * 0.9


def bird(seed, kind=0):
    r = np.random.default_rng(seed)
    d = r.uniform(0.9, 1.6)
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    nb = r.integers(2, 5)
    for k in range(nb):
        t0 = k * d / nb + r.uniform(0, 0.05)
        m = (t >= t0) & (t < t0 + 0.18)
        tt = t[m] - t0
        f0 = r.uniform(2200, 3600) if kind == 0 else r.uniform(1400, 2200)
        f = f0 + r.uniform(-900, 900) * tt / 0.18 + 60 * np.sin(tt * 90)
        x[m] += np.sin(np.cumsum(2 * np.pi * f / SR)) * np.sin(np.pi * tt / 0.18)
    x /= max(np.abs(x).max(), 1e-6)
    return x * 0.85


def crow(seed=9):
    r = np.random.default_rng(seed)
    d = 1.4
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(3):
        t0 = k * 0.38
        m = (t >= t0) & (t < t0 + 0.28)
        tt = t[m] - t0
        f = 620 - 260 * tt / 0.28 + 40 * np.sin(tt * 70)
        s = np.sin(np.cumsum(2 * np.pi * f / SR)) + 0.6 * np.sin(np.cumsum(2 * np.pi * f * 2.1 / SR))
        x[m] += s * np.exp(-tt * 6) * np.sin(np.pi * np.minimum(tt / 0.28, 1))
    x /= max(np.abs(x).max(), 1e-6)
    return x * 0.85


def make_all(outdir):
    os.makedirs(outdir, exist_ok=True)
    out = []
    out.append(_write(os.path.join(outdir, 'wind_loop.wav'), wind()))
    out.append(_write(os.path.join(outdir, 'rumble_loop.wav'), rumble()))
    out.append(_write(os.path.join(outdir, 'crickets_loop.wav'), crickets()))
    out.append(_write(os.path.join(outdir, 'creak.wav'), creak()))
    for i in range(4):
        out.append(_write(os.path.join(outdir, 'bird%d.wav' % (i + 1)), bird(20 + i, i % 2)))
    out.append(_write(os.path.join(outdir, 'crow.wav'), crow()))
    return out
