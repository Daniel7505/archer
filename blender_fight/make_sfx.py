"""make_sfx.py - synthesizes the fight soundtrack (numpy only) from events.json written by fight_scene.py.
Sounds: bow twang (Karplus-Strong), arrow whoosh (swept band-passed noise), lightning zap (crackle + chirp),
thud/bonk, clash boom, a soft chime for the bow, plus a quiet meadow bed (wind + birds).
Usage: python3 make_sfx.py  -> fight_sfx.wav (44.1 kHz, 16-bit stereo)"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
rng = np.random.default_rng(7)
ev = json.load(open(os.path.join(HERE, "events.json")))
DUR = ev["frames"] / ev["fps"] + 1.0
N = int(DUR * SR)
mix = np.zeros((N, 2))

def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    w = np.clip((f - lo * 0.7) / (lo * 0.3 + 1e-9), 0, 1) * np.clip((hi * 1.3 - f) / (hi * 0.3), 0, 1)
    return np.fft.irfft(X * w, len(x))

def env(n, a, d, shape=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) * shape / max(d, 1e-4))
    return e

def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR); sig = sig[: max(0, N - i)]
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    mix[i:i + len(sig), 0] += sig * gain * l * 1.414
    mix[i:i + len(sig), 1] += sig * gain * r * 1.414

def twang(f0=98.0):
    n = int(0.9 * SR); p = int(SR / f0)
    buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 30)
    snap = bandpass(rng.normal(0, 1, n), 1500, 6000) * np.exp(-t * 120)
    s = out * np.exp(-t * 4) + 0.8 * thump + 0.5 * snap
    return s / np.abs(s).max()

def whoosh(dur=0.4, pitch=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    out = np.zeros(n); seg = 2048
    for k in range(0, n, seg // 2):              # time-varying band: rises then falls (doppler-ish)
        c = (500 + 2500 * np.sin(np.pi * min(1, k / n))) * pitch
        part = noise[k:k + seg]
        if len(part) < 64: break
        bp = bandpass(part, c * 0.6, c * 1.6) * np.hanning(len(part))
        out[k:k + len(part)] += bp
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    s = out * e
    return s / (np.abs(s).max() + 1e-9)

def zap(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    crack = rng.normal(0, 1, n) * (rng.random(n // 220 + 1).repeat(220)[:n] > 0.55)
    crack = bandpass(crack, 800, 9000)
    chirp = np.sign(np.sin(2 * np.pi * np.cumsum(2400 * np.exp(-t * 9) + 120) / SR)) * 0.4
    buzz = np.sin(2 * np.pi * 110 * t) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 37 * t)))
    s = (crack * 0.9 + chirp * 0.5 + buzz * 0.3) * env(n, 0.003, dur, 3.5)
    return s / np.abs(s).max()

def thud(pitch=1.0):
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = 75 * pitch * (1 + 0.6 * np.exp(-t * 25))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    s += 0.35 * bandpass(rng.normal(0, 1, n), 100, 900) * np.exp(-t * 40)
    return s / np.abs(s).max()

def bonk():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 520 * np.exp(-t * 3.5)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.exp(-t * 22)
    s += 0.6 * thud(1.4)[:n]
    return s / np.abs(s).max()

def boom():
    n = int(2.2 * SR); t = np.arange(n) / SR
    low = np.sin(2 * np.pi * np.cumsum(48 * (1 + 1.5 * np.exp(-t * 6))) / SR) * np.exp(-t * 2.2)
    body = bandpass(rng.normal(0, 1, n), 60, 1800) * np.exp(-t * 3.0)
    crack = bandpass(rng.normal(0, 1, n), 2000, 10000) * np.exp(-t * 12)
    sparkle = bandpass(rng.normal(0, 1, n) * (rng.random(n) > 0.995), 3000, 12000) * np.exp(-t * 2.5) * 3
    s = 1.0 * low + 0.8 * body + 0.5 * crack + 0.4 * sparkle
    return s / np.abs(s).max()

def chime():
    n = int(2.5 * SR); t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, a, d in ((880, 1, 1.5), (1320, 0.5, 2.0), (1760, 0.3, 2.8), (2640, 0.15, 4)))
    s *= np.minimum(1, t / 0.01)
    return s / np.abs(s).max()

GEN = {"twang": lambda e: twang(), "whoosh": lambda e: whoosh(e.get("dur", 0.4), e.get("pitch", 1.0)),
       "zap": lambda e: zap(max(0.2, e.get("dur", 0.45))), "thud": lambda e: thud(e.get("pitch", 1.0)),
       "bonk": lambda e: bonk(), "boom": lambda e: boom(), "chime": lambda e: chime()}
LEVEL = {"twang": 0.55, "whoosh": 0.35, "zap": 0.6, "thud": 0.6, "bonk": 0.55, "boom": 0.95, "chime": 0.14}
for e in ev["events"]:
    s = GEN[e["kind"]](e)
    put(s, e["t"], LEVEL[e["kind"]] * e.get("gain", 1.0), pan=float(rng.uniform(-0.3, 0.3)))

# meadow bed: soft wind + sparse birdsong
t = np.arange(N) / SR
wind = bandpass(rng.normal(0, 1, N), 80, 700); wind /= np.abs(wind).max()
wind *= 0.035 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t + 1.0))
mix += wind[:, None]
for bt in np.arange(0.6, DUR - 1, 2.3) + rng.uniform(0, 1.2, len(np.arange(0.6, DUR - 1, 2.3))):
    n = int(0.12 * SR); tt = np.arange(n) / SR
    for k in range(rng.integers(2, 4)):
        f = rng.uniform(3200, 4800) * (1 + 0.3 * np.sin(2 * np.pi * 18 * tt))
        chirp = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.12) ** 2
        put(chirp, bt + k * 0.16, 0.025, pan=float(rng.uniform(-0.8, 0.8)))

# small room/air reverb
ir_n = int(0.7 * SR); ir = rng.normal(0, 1, ir_n) * np.exp(-np.arange(ir_n) / SR * 7); ir /= np.sqrt((ir ** 2).sum())
for c in range(2):
    wet = np.fft.irfft(np.fft.rfft(mix[:, c], N + ir_n) * np.fft.rfft(ir, N + ir_n))[:N]
    mix[:, c] = mix[:, c] + 0.18 * wet
mix /= np.abs(mix).max()
mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.89     # gentle soft-clip compression
fade = np.minimum(1, (N - np.arange(N)) / (0.6 * SR)); mix *= fade[:, None]
pcm = (mix * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, "fight_sfx.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("wrote fight_sfx.wav", DUR, "s,", len(ev["events"]), "events")
