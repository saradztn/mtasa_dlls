# Created by: Arena.ai Agent Mode (AI) - Park MTA:SA asset pipeline
# -----------------------------------------------------------------------------
# audio.py - procedural sound effects for the park (numpy only, 16 bit mono WAV).
#   loops are built in the frequency domain (periodic by construction -> seamless), one-shots with envelopes.
#   fountain_loop, pond_loop, wind_loop, city_loop, crickets_loop   (loops)
#   bird1..bird5, frog, duck, gate_creak, swing_creak, bell          (one shots)
# -----------------------------------------------------------------------------
import wave
import numpy as np

SR = 22050


def _rng(seed):
    return np.random.default_rng(seed)


def norm(x, peak=0.8):
    x = np.asarray(x, np.float64)
    return x / max(np.abs(x).max(), 1e-9) * peak


def band_noise(n, lo, hi, rng, slope=0.0, sr=SR):
    """periodic band limited noise of n samples (flat or 1/f^slope), smooth band edges"""
    f = np.fft.rfftfreq(n, 1 / sr)
    mag = np.zeros_like(f)
    edge = lambda a, w: 1 / (1 + np.exp(-(f - a) / w))
    mag = edge(lo, max(lo * 0.12, 8)) * (1 - edge(hi, max(hi * 0.10, 8)))
    mag = mag * (np.maximum(f, 20) / 1000.0) ** (-slope)
    ph = rng.uniform(0, 2 * np.pi, len(f))
    sp = mag * np.exp(1j * ph) * rng.rayleigh(1.0, len(f))
    sp[0] = 0
    return np.fft.irfft(sp, n)


def periodic_env(n, rng, rates, depth, sr=SR):
    """slow periodic gain curve: sum of sines with integer cycles per loop"""
    t = np.arange(n) / n
    g = np.zeros(n)
    for r in rates:
        g += rng.uniform(0.5, 1.0) * np.sin(2 * np.pi * (r * t + rng.uniform()))
    g = g / max(np.abs(g).max(), 1e-9)
    return 1 - depth + depth * (g * 0.5 + 0.5)


def lowpass(x, fc, sr=SR):
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / sr)
    return np.fft.irfft(np.fft.rfft(x) / (1 + (f / fc) ** 4), n)


def highpass(x, fc, sr=SR):
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / sr)
    h = (f / fc) ** 4 / (1 + (f / fc) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * h, n)


def bandpass(x, lo, hi, sr=SR):
    return lowpass(highpass(x, lo, sr), hi, sr)


def add_wrapped(buf, start, sig):
    n = len(buf)
    idx = (start + np.arange(len(sig))) % n
    np.add.at(buf, idx, sig)


def save(path, x, sr=SR, fade=0.0):
    x = np.clip(np.asarray(x, np.float64), -1, 1)
    if fade > 0:
        k = int(fade * sr)
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype('<i2').tobytes())


# ------------------------------------------------------------------------------------------------ loops
def fountain_loop(sec=6.0):
    r = _rng(1)
    n = int(sec * SR)
    base = band_noise(n, 500, 7500, r, slope=0.35) * periodic_env(n, r, [3, 5, 7, 11], 0.35)
    low = band_noise(n, 90, 500, r, slope=0.0) * 0.5 * periodic_env(n, r, [2, 3], 0.4)
    drops = np.zeros(n)
    for _ in range(int(sec * 22)):             # plinking droplets falling into the basin
        f0 = r.uniform(900, 3200)
        L = int(r.uniform(0.012, 0.035) * SR)
        t = np.arange(L) / SR
        d = np.sin(2 * np.pi * f0 * t * (1 + 3 * t)) * np.exp(-t * r.uniform(120, 280)) * r.uniform(0.05, 0.25)
        add_wrapped(drops, int(r.integers(0, n)), d)
    return norm(0.9 * base / np.abs(base).max() + 0.6 * low / np.abs(low).max() + 0.6 * drops / max(np.abs(drops).max(), 1e-9), 0.7)


def pond_loop(sec=8.0):
    r = _rng(2)
    n = int(sec * SR)
    lap = band_noise(n, 120, 1100, r, slope=0.5) * periodic_env(n, r, [3, 4, 6], 0.7)
    lap = lowpass(lap, 900)
    glug = np.zeros(n)
    for _ in range(int(sec * 2.2)):
        f0 = r.uniform(250, 600)
        L = int(r.uniform(0.06, 0.14) * SR)
        t = np.arange(L) / SR
        d = np.sin(2 * np.pi * (f0 * t + 900 * t * t)) * np.exp(-t * r.uniform(30, 55)) * r.uniform(0.2, 0.5)
        add_wrapped(glug, int(r.integers(0, n)), d)
    hiss = band_noise(n, 2000, 6000, r, slope=0.2) * 0.12 * periodic_env(n, r, [5, 9], 0.8)
    return norm(norm(lap, 1) + 0.7 * glug + hiss, 0.6)


def wind_loop(sec=10.0):
    r = _rng(3)
    n = int(sec * SR)
    gust = periodic_env(n, r, [1, 2, 3], 0.85)
    body = lowpass(band_noise(n, 60, 900, r, slope=0.8), 700) * gust
    leaves = bandpass(band_noise(n, 2500, 9000, r, slope=0.0), 2800, 8500) * (gust ** 2.2) * periodic_env(n, r, [13, 17, 23], 0.5)
    whistle = np.sin(2 * np.pi * np.cumsum(520 + 90 * np.sin(2 * np.pi * np.arange(n) / n * 2 + 1)) / SR) * (gust ** 4) * 0.03
    return norm(norm(body, 1) * 0.9 + norm(leaves, 1) * 0.35 + whistle, 0.55)


def city_loop(sec=10.0):
    r = _rng(4)
    n = int(sec * SR)
    rumble = lowpass(band_noise(n, 35, 400, r, slope=1.2), 260) * periodic_env(n, r, [1, 2, 4], 0.4)
    cars = np.zeros(n)
    for k in range(3):                         # distant car passes: band noise swelling and fading
        L = int(r.uniform(1.6, 2.6) * SR)
        env = np.sin(np.linspace(0, np.pi, L)) ** 2
        c = bandpass(r.normal(size=L), 300, 1400) * env * r.uniform(0.3, 0.7)
        add_wrapped(cars, int(r.integers(0, n)), c)
    horn = np.zeros(n)
    t0 = int(r.uniform(0.2, 0.7) * n)
    t = np.arange(int(0.42 * SR)) / SR
    hn = (np.sin(2 * np.pi * 410 * t) + 0.6 * np.sin(2 * np.pi * 820 * t) + 0.3 * np.sin(2 * np.pi * 1230 * t)) * np.minimum(t * 40, 1) * np.minimum((0.42 - t) * 40, 1)
    add_wrapped(horn, t0, lowpass(hn, 1500) * 0.06)
    return norm(norm(rumble, 1) * 0.8 + norm(cars, 1) * 0.35 + horn, 0.45)


def crickets_loop(sec=6.0):
    r = _rng(5)
    n = int(sec * SR)
    out = np.zeros(n)
    for k in range(9):
        fc = r.uniform(4100, 5200)
        period = r.choice([1.0, 1.2, 1.5, 0.75, 2.0])         # seconds between chirp groups: must divide the loop evenly
        period = sec / round(sec / period)
        pulses = r.integers(3, 5)
        pr = r.uniform(0.045, 0.060)                           # pulse spacing
        amp = r.uniform(0.4, 1.0)
        for g in range(int(round(sec / period))):
            t0 = g * period + r.uniform(0, period * 0.8) * 0 + k * 0.137 % period
            for p in range(pulses):
                L = int(0.032 * SR)
                t = np.arange(L) / SR
                pulse = np.sin(2 * np.pi * fc * t + 0.5 * np.sin(2 * np.pi * 60 * t)) * np.sin(np.pi * t / 0.032) ** 1.5
                add_wrapped(out, int((t0 + p * pr) * SR), pulse * amp * 0.5)
    out = out + band_noise(n, 3000, 6500, r) * 0.01
    return norm(out, 0.5)


# ------------------------------------------------------------------------------------------------ one shots
def _env(L, a=0.01, d=0.05):
    e = np.ones(L)
    ka, kd = int(a * SR), int(d * SR)
    e[:ka] = np.linspace(0, 1, ka)
    e[-kd:] = np.linspace(1, 0, kd)
    return e


def chirp(f0, f1, dur, vib=0.0, vf=0.0, shape=1.0, harm=0.25):
    L = int(dur * SR)
    t = np.arange(L) / SR
    u = t / dur
    f = f0 + (f1 - f0) * u ** shape + vib * np.sin(2 * np.pi * vf * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + harm * np.sin(2 * ph) + harm * 0.4 * np.sin(3 * ph)
    return s * _env(L, 0.008, 0.02) * np.sin(np.pi * u) ** 0.5


def echo(x, delay=0.11, gain=0.28, taps=3):
    out = np.concatenate([x, np.zeros(int(delay * SR * (taps + 1)))])
    for k in range(1, taps + 1):
        d = int(delay * SR * k)
        out[d:d + len(x)] += x * gain ** k
    return out


def bird(kind):
    r = _rng(100 + kind)
    parts = []
    gap = lambda s: np.zeros(int(s * SR))
    if kind == 1:                                    # simple repeated tweet (sparrow)
        for i in range(r.integers(4, 7)):
            parts += [chirp(r.uniform(3200, 3800), r.uniform(2400, 3000), 0.09, shape=0.7), gap(r.uniform(0.07, 0.13))]
    elif kind == 2:                                  # rising whistle + trill (finch)
        parts += [chirp(2400, 4300, 0.22, shape=0.6), gap(0.05), chirp(4300, 3900, 0.14, vib=500, vf=38)]
        parts += [chirp(3800, 4600, 0.07)] * 3
        parts = [p for q in parts for p in (q, gap(0.04))]
    elif kind == 3:                                  # warble (blackbird-ish)
        f = 2200
        for i in range(9):
            f2 = f * r.uniform(0.8, 1.35)
            parts += [chirp(f, f2, r.uniform(0.07, 0.15), vib=150, vf=22, shape=0.8), gap(r.uniform(0.01, 0.05))]
            f = np.clip(f2, 1500, 3400)
    elif kind == 4:                                  # dove coo (low, vibrato)
        for d in (0.38, 0.22, 0.22, 0.55):
            parts += [chirp(520, 470, d, vib=18, vf=7, harm=0.1), gap(0.12)]
    else:                                            # cuckoo-like two notes + fast trill
        parts += [chirp(1500, 1250, 0.2, harm=0.08), gap(0.09), chirp(1250, 1000, 0.28, harm=0.08), gap(0.35)]
        parts += [chirp(2800, 2900, 0.04, vib=300, vf=45) for _ in range(5)]
    x = np.concatenate(parts)
    x = echo(x, 0.13, 0.22, 3)
    return norm(x, 0.7)


def frog():
    r = _rng(7)
    out = []
    for c in range(2):
        L = int(0.55 * SR)
        t = np.arange(L) / SR
        f = 160 + 60 * np.sin(np.pi * t / 0.55)
        pulses = np.sign(np.sin(2 * np.pi * 38 * t)) * 0.5 + 0.5
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.5 * np.sin(3 * ph)) * pulses
        s = bandpass(s, 220, 1900) * np.sin(np.pi * t / 0.55) ** 0.6
        out += [s, np.zeros(int(0.12 * SR))]
    x = np.concatenate(out)
    return norm(echo(x, 0.09, 0.2, 2), 0.7)


def duck():
    out = []
    for q in range(2):
        L = int(0.28 * SR)
        t = np.arange(L) / SR
        f = 520 - 140 * t / 0.28
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = sum(np.sin(k * ph) / k ** 0.8 for k in range(1, 9))
        s = bandpass(s, 400, 2600)
        s *= np.minimum(t * 120, 1) * np.exp(-t * 7)
        out += [s, np.zeros(int(0.09 * SR))]
    return norm(np.concatenate(out), 0.7)


def creak(sec, f0, f1, seed, rate=(18, 44)):
    r = _rng(seed)
    n = int(sec * SR)
    t = np.arange(n) / SR
    u = t / sec
    f = f0 + (f1 - f0) * np.sin(np.pi * u) + 12 * np.sin(2 * np.pi * 3.1 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = sum(np.sin(k * ph) / k for k in range(1, 14))
    stick = np.zeros(n)
    pos = 0
    while pos < n:
        L = int(r.uniform(1 / rate[1], 1 / rate[0]) * SR)
        stick[pos:pos + L] = r.uniform(0.2, 1.0)
        pos += L
    stick = lowpass(stick, 120)
    x = bandpass(saw * stick, 500, 2400)
    x += 0.3 * bandpass(r.normal(size=n), 800, 3000) * stick ** 2
    x *= np.sin(np.pi * u) ** 0.5
    return norm(x, 0.7)


def bell(sec=2.8):
    n = int(sec * SR)
    out = np.zeros(n)
    ratios = [(1.0, 1.0, 3.0), (2.0, 0.55, 3.6), (2.76, 0.4, 4.5), (5.4, 0.22, 6.0), (8.93, 0.12, 8.5)]
    for hit, t0 in enumerate((0.0, 0.55)):
        L = n - int(t0 * SR)
        t = np.arange(L) / SR
        s = sum(a * np.sin(2 * np.pi * 1760 * ratio * t) * np.exp(-t * dec) for ratio, a, dec in ratios) * np.minimum(t * 800, 1)
        out[int(t0 * SR):] += s * (1.0 if hit == 0 else 0.8)
    return norm(out, 0.65)


def make_all(outdir):
    import os
    os.makedirs(outdir, exist_ok=True)
    files = {}
    for name, x in (('fountain_loop', fountain_loop()), ('pond_loop', pond_loop()), ('wind_loop', wind_loop()), ('city_loop', city_loop()), ('crickets_loop', crickets_loop())):
        save(os.path.join(outdir, name + '.wav'), x)
        files[name] = len(x) / SR
    for k in range(1, 6):
        save(os.path.join(outdir, 'bird%d.wav' % k), bird(k), fade=0.01)
    save(os.path.join(outdir, 'frog.wav'), frog(), fade=0.01)
    save(os.path.join(outdir, 'duck.wav'), duck(), fade=0.01)
    save(os.path.join(outdir, 'gate_creak.wav'), creak(3.2, 95, 165, 11), fade=0.03)
    save(os.path.join(outdir, 'swing_creak.wav'), creak(1.7, 210, 330, 12, rate=(30, 70)), fade=0.03)
    save(os.path.join(outdir, 'bell.wav'), bell(), fade=0.005)
    return sorted(os.listdir(outdir))


if __name__ == '__main__':
    import sys
    print(make_all(sys.argv[1] if len(sys.argv) > 1 else '../audio'))
