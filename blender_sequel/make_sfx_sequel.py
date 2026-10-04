"""make_sfx_sequel.py - synthesized SFX for the sequel segments (numpy only).
Generators (twang, whoosh, zap, thud, bonk, boom, chime) are copied from ../fight/make_sfx.py; new ones: step, punch,
bash, crush (crushing blow sting), crit (sparkle sting), shimmer (spirit pad), heal (rising arpeggio), boing, stars
(dizzy twinkles), greed (brute grunt), roar (ghostly panda roar).  Events come from hud_<segment>.json (written by
sequel_scene.py).  The summon segment also mixes ../ocarina/melody.wav (the original ocarina melody).
Usage: python3 make_sfx_sequel.py [fight capture brute summon] -> sfx_<segment>.wav (44.1 kHz stereo, RMS-matched)"""
import json, os, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
rng = np.random.default_rng(11)
N = 0; mix = None
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


def step(pitch=1.0):
    n = int(0.25 * SR); t = np.arange(n) / SR
    s = bandpass(rng.normal(0, 1, n), 120 * pitch, 1400 * pitch) * np.exp(-t * 28)
    s += 0.6 * np.sin(2 * np.pi * 60 * pitch * t) * np.exp(-t * 30)
    return s / np.abs(s).max()

def punch():
    n = int(0.45 * SR); t = np.arange(n) / SR
    s = thud(0.9)[:n] + 0.7 * bandpass(rng.normal(0, 1, n), 300, 3000) * np.exp(-t * 35)
    return s / np.abs(s).max()

def bash():
    n = int(0.9 * SR); t = np.arange(n) / SR
    s = 1.2 * thud(0.6)[:n] if len(thud(0.6)) >= n else np.pad(thud(0.6), (0, n - len(thud(0.6))))
    s = s + 0.6 * bandpass(rng.normal(0, 1, n), 80, 2500) * np.exp(-t * 12)
    ring = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((310, 6), (523, 8), (741, 10))) * 0.25
    s = np.tanh(2.5 * (s + ring))
    return s / np.abs(s).max()

def crush():
    n = int(0.8 * SR); t = np.arange(n) / SR
    low = np.sin(2 * np.pi * np.cumsum(55 * (1 + 2 * np.exp(-t * 12))) / SR) * np.exp(-t * 5)
    grit = np.tanh(6 * bandpass(rng.normal(0, 1, n), 200, 3000)) * np.exp(-t * 9)
    stab = np.sign(np.sin(2 * np.pi * 146.8 * t)) * np.exp(-t * 7) * 0.4
    s = low + 0.5 * grit + stab
    return s / np.abs(s).max()

def crit():
    n = int(0.9 * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for k, f in enumerate((1046.5, 1318.5, 1568.0, 2093.0)):
        i = int(k * 0.045 * SR); tt = t[: n - i]
        s[i:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) * (0.9 - 0.15 * k)
    s += 0.25 * bandpass(rng.normal(0, 1, n) * (rng.random(n) > 0.99), 4000, 12000) * np.exp(-t * 4)
    return s / np.abs(s).max()

def shimmer(dur=2.5):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for f in (523.3, 659.3, 784.0, 987.8, 1174.7):
        s += np.sin(2 * np.pi * f * t * (1 + 0.003 * np.sin(2 * np.pi * 5 * t))) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.7 + f / 2000) * t))
    tw = bandpass(rng.normal(0, 1, n) * (rng.random(n) > 0.997), 3000, 11000) * 2
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    s = (s / 5 + tw) * e
    return s / np.abs(s).max()

def heal():
    n = int(1.4 * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k, f in enumerate((523.3, 659.3, 784.0, 1046.5, 1318.5)):
        i = int(k * 0.08 * SR); tt = t[: n - i]
        s[i:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 3.5)
    return s / np.abs(s).max()

def boing():
    n = int(0.7 * SR); t = np.arange(n) / SR
    f = 180 + 140 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 3) + 120 * np.exp(-t * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    return s / np.abs(s).max()

def stars(dur=3.0):
    n = int(dur * SR); s = np.zeros(n)
    for k in range(int(dur * 5)):
        i = int(k * 0.2 * SR); m = int(0.12 * SR); tt = np.arange(m) / SR
        f = (2200 if k % 2 == 0 else 2650) * (1 + 0.05 * np.sin(2 * np.pi * 30 * tt))
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.12) ** 2
        s[i:i + m] += c[: max(0, n - i)]
    s *= np.linspace(1, 0.3, n)
    return s / np.abs(s).max()

def greed():
    n = int(0.9 * SR); t = np.arange(n) / SR
    f0 = 95 * (1 + 0.15 * np.sin(2 * np.pi * 2.2 * t))
    saw = 2 * ((np.cumsum(f0) / SR) % 1) - 1
    s = bandpass(saw, 200, 900) + 0.6 * bandpass(saw, 1000, 1500)
    s *= np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 0.7
    return s / np.abs(s).max()

def roar():
    n = int(1.6 * SR); t = np.arange(n) / SR
    f0 = 110 * (1 + 0.4 * np.sin(np.pi * np.clip(t / 1.6, 0, 1)))
    saw = 2 * ((np.cumsum(f0) / SR) % 1) - 1
    s = bandpass(saw, 150, 1200) + 0.5 * bandpass(rng.normal(0, 1, n), 300, 2500)
    s *= np.sin(np.pi * np.clip(t / 1.6, 0, 1)) ** 0.8
    ch = np.zeros(n)                                          # ghostly chorus/echo
    for d, g in ((0.09, 0.6), (0.21, 0.4), (0.37, 0.25)):
        i = int(d * SR); ch[i:] += s[: n - i] * g
    s = s + ch
    return s / np.abs(s).max()

GEN = {"twang": lambda e: twang(), "whoosh": lambda e: whoosh(e.get("dur", 0.4), e.get("pitch", 1.0)),
       "zap": lambda e: zap(max(0.2, e.get("dur", 0.45))), "thud": lambda e: thud(e.get("pitch", 1.0)),
       "bonk": lambda e: bonk(), "boom": lambda e: boom(), "chime": lambda e: chime(),
       "step": lambda e: step(e.get("pitch", 1.0)), "punch": lambda e: punch(), "bash": lambda e: bash(),
       "crush": lambda e: crush(), "crit": lambda e: crit(), "shimmer": lambda e: shimmer(e.get("dur", 2.5)),
       "heal": lambda e: heal(), "boing": lambda e: boing(), "stars": lambda e: stars(e.get("dur", 3.0)),
       "greed": lambda e: greed(), "roar": lambda e: roar()}
LEVEL = {"twang": 0.55, "whoosh": 0.35, "zap": 0.6, "thud": 0.6, "bonk": 0.55, "boom": 0.95, "chime": 0.14,
         "step": 0.18, "punch": 0.7, "bash": 0.85, "crush": 0.45, "crit": 0.3, "shimmer": 0.22, "heal": 0.3,
         "boing": 0.4, "stars": 0.16, "greed": 0.35, "roar": 0.4}

def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, w.getnchannels()) / 32768.0
    return a if a.shape[1] == 2 else np.repeat(a, 2, axis=1)

def make(seg):
    global N, mix
    hud = json.load(open(os.path.join(HERE, f"hud_{'fightwin' if seg == 'fight' else seg}.json")))
    DUR = hud["frames"] / hud["fps"]
    N = int(DUR * SR); mix = np.zeros((N, 2))
    rolls = {r["id"]: r for r in json.load(open(os.path.join(HERE, "rolls.json")))["rolls"]}
    evs = list(hud["events"])
    for h in hud["hits"]:                                     # crit / crushing-blow stings follow the seeded rolls
        r = rolls.get(h.get("id") or "")
        if r and r["crit"]:
            k = "crush" if r["attacker"] in ("panda", "brute") else "crit"
            if not any(e["kind"] == k and abs(e["frame"] - h["frame"]) <= 2 for e in evs):
                evs.append(dict(frame=h["frame"], kind=k))
    for e in evs:
        s = GEN[e["kind"]](e)
        put(s, (e["frame"] - 1) / hud["fps"], LEVEL[e["kind"]] * e.get("gain", 1.0), pan=float(rng.uniform(-0.3, 0.3)))
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
    ir_n = int(0.7 * SR); ir = rng.normal(0, 1, ir_n) * np.exp(-np.arange(ir_n) / SR * 7); ir /= np.sqrt((ir ** 2).sum())
    for c in range(2):
        wet = np.fft.irfft(np.fft.rfft(mix[:, c], N + ir_n) * np.fft.rfft(ir, N + ir_n))[:N]
        mix[:, c] = mix[:, c] + 0.18 * wet
    mix /= np.abs(mix).max()
    mix = np.tanh(2.2 * mix) / np.tanh(2.2) * 0.89
    if "melody" in hud:                                       # the original ocarina melody (summon)
        mel = read_wav(os.path.join(HERE, "..", "ocarina", "melody.wav"))
        f1 = hud["melody"]["f1"]; m = min(len(mel), int((f1 - 1) / hud["fps"] * SR), N)
        mel = mel[:m].copy(); fo = int(0.8 * SR); mel[-fo:] *= np.linspace(1, 0, fo)[:, None]
        mel /= np.abs(mel).max()
        mix *= 0.75; mix[:m] += 0.8 * mel
    # RMS match across segments (final loudnorm happens in stitch.sh), peak-safe
    rms = np.sqrt((mix ** 2).mean()); mix *= 0.12 / max(rms, 1e-6)
    pk = np.abs(mix).max()
    if pk > 0.95: mix = np.tanh(mix / pk * 1.6) / np.tanh(1.6) * 0.95
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(HERE, f"sfx_{seg}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("wrote", f"sfx_{seg}.wav", round(DUR, 2), "s", len(hud["events"]), "events")

if __name__ == "__main__":
    for s in (sys.argv[1:] or ["fight", "capture", "brute", "summon"]):
        if os.path.exists(os.path.join(HERE, f"hud_{'fightwin' if s == 'fight' else s}.json")): make(s)
