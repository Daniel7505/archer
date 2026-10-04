"""make_sfx_ch2.py - synthesized audio for Chapter 2 (numpy only).
Reuses the generators from ../sequel/make_sfx_sequel.py (whoosh, chime, step, shimmer, stars, roar) and adds:
pop, loot_land (rarity-pitched sparkle chime), pickup, coins, paw (soft heavy paw beat), fanfare (short original horn call),
city ambience (crowd murmur + canal water + distant bells), bridge, ui_open/ui_click, stamp, sparkle, bells.
Mount segment mixes melody2.wav (the new original ocarina tune); the montage ending mixes a soft reprise.
Usage: python3 make_sfx_ch2.py [loot mount ride establish city montage] -> sfx_<seg>.wav"""
import json, os, sys, wave, importlib.util
import numpy as np
CH = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sq", os.path.join(CH, "..", "sequel", "make_sfx_sequel.py")); sq = importlib.util.module_from_spec(spec); spec.loader.exec_module(sq)
SR = 44100; rng = np.random.default_rng(23); bandpass = sq.bandpass
N = 0; mix = None
def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i]; l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    mix[i:i + len(sig), 0] += sig * gain * l * 1.414; mix[i:i + len(sig), 1] += sig * gain * r * 1.414
def norm(s): return s / (np.abs(s).max() + 1e-9)
def tone(f, dur, dec=3.0, harm=((1, 1),)):
    t = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * h * t) for h, a in harm) * np.exp(-t * dec) * np.minimum(1, t / 0.004)

def pop():
    n = int(0.18 * SR); t = np.arange(n) / SR; f = 300 + 900 * np.exp(-t * 30)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22))
def loot_land(rarity="Common"):
    base = {"Common": 660, "Uncommon": 740, "Rare": 880, "Epic": 990}.get(rarity, 660)
    s = np.zeros(int(1.6 * SR))
    for k, m in enumerate((1, 1.25, 1.5, 2.0)):
        x = tone(base * m, 1.2, 3.5, ((1, 1), (2, 0.3), (3, 0.1))); i = int(k * 0.06 * SR); s[i:i + len(x)] += x[: len(s) - i] * (0.8 ** k)
    if rarity == "Epic": s += 0.4 * norm(bandpass(rng.normal(0, 1, len(s)) * (rng.random(len(s)) > 0.99), 4000, 12000)) * np.exp(-np.arange(len(s)) / SR * 2)
    return norm(s)
def pickup():
    s = np.zeros(int(0.5 * SR)); a = tone(1320, 0.3, 10); b = tone(1760, 0.3, 10); s[:len(a)] += a; i = int(0.07 * SR); s[i:i + len(b)] += b[: len(s) - i]
    return norm(s)
def clink(f):
    return tone(f, 0.35, 14, ((1, 1), (2.76, 0.5), (5.4, 0.25), (8.9, 0.12)))
def coins(dur=1.0):
    s = np.zeros(int((dur + 0.4) * SR))
    for t0 in np.sort(rng.uniform(0, dur, int(dur * 14))):
        x = clink(rng.uniform(2600, 4200)); i = int(t0 * SR); s[i:i + len(x)] += x[: len(s) - i] * rng.uniform(0.4, 1)
    return norm(s)
def paw(g=1.0):
    n = int(0.3 * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(55 * (1 + 0.8 * np.exp(-t * 30))) / SR) * np.exp(-t * 16)
    s += 0.5 * bandpass(rng.normal(0, 1, n), 200, 2500) * np.exp(-t * 35)    # grass / dirt scuff
    return norm(s)
def fanfare():
    # short original horn call (D4 - A4 - D5 - F#5 held), soft brass = odd/even harmonics with slow attack
    s = np.zeros(int(2.6 * SR)); notes = ((293.66, 0.0, 0.25), (440.0, 0.25, 0.25), (587.33, 0.5, 0.3), (739.99, 0.8, 1.6))
    for f, t0, d in notes:
        t = np.arange(int((d + 0.3) * SR)) / SR
        e = np.minimum(1, t / 0.05) * np.where(t < d, 1.0, np.exp(-(t - d) * 10))
        x = sum(a * np.sin(2 * np.pi * f * h * t + 0.2 * np.sin(2 * np.pi * 5 * t)) for h, a in ((1, 1), (2, 0.6), (3, 0.4), (4, 0.2), (5, 0.1))) * e
        i = int(t0 * SR); s[i:i + len(x)] += x[: len(s) - i]
    return norm(s)
def bells():
    s = np.zeros(int(4.0 * SR))
    for k, f in enumerate((392.0, 329.63, 293.66, 261.63)):
        x = tone(f, 3.0, 1.2, ((1, 1), (2.0, 0.6), (2.4, 0.4), (3.0, 0.25), (4.2, 0.15))); i = int(k * 0.55 * SR); s[i:i + len(x)] += x[: len(s) - i]
    return norm(s)
def city_amb(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    murmur = np.zeros(n)
    for k in range(7):                                   # babble: formant-ish bands with syllable-rate AM
        b = bandpass(rng.normal(0, 1, n), rng.uniform(250, 500), rng.uniform(900, 2200))
        am = np.clip(np.sin(2 * np.pi * rng.uniform(2.5, 5.0) * t + rng.uniform(0, 6)) + rng.uniform(-0.2, 0.4), 0, None)
        murmur += b * am * rng.uniform(0.5, 1)
    water = bandpass(rng.normal(0, 1, n), 1500, 7000) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.4 * t)) * 0.35
    s = norm(murmur) * 0.8 + norm(water) * 0.35
    fi = int(0.5 * SR); s[:fi] *= np.linspace(0, 1, fi); s[-fi:] *= np.linspace(1, 0, fi)
    return norm(s)
def ui_open(): return norm(np.concatenate([tone(520, 0.08, 20), tone(780, 0.25, 12)]))
def ui_click(): return norm(tone(1800, 0.06, 60) + 0.5 * bandpass(rng.normal(0, 1, int(0.06 * SR)), 2000, 8000) * np.exp(-np.arange(int(0.06 * SR)) / SR * 80))
def stamp():
    n = int(0.4 * SR); t = np.arange(n) / SR
    return norm(sq.thud(1.6)[:n] + 0.6 * bandpass(rng.normal(0, 1, n), 300, 3000) * np.exp(-t * 30))
def sparkle():
    s = np.zeros(int(1.6 * SR))
    for k in range(10):
        x = tone(rng.uniform(2000, 4000), 0.5, 8); i = int(k * 0.09 * SR); s[i:i + len(x)] += x[: len(s) - i] * 0.7
    return norm(s + 0.6 * sq.shimmer(1.6)[:len(s)])
def bridge(): return norm(sum(np.roll(np.pad(paw(), (0, int(0.2 * SR))), int(k * 0.09 * SR)) * 0.5 ** k for k in range(3)))

GEN = dict(pop=lambda e: pop(), loot_land=lambda e: loot_land(e.get("rarity", "Common")), pickup=lambda e: pickup(),
           coins=lambda e: coins(e.get("dur", 1.0)), paw=lambda e: paw(), fanfare=lambda e: fanfare(), bells=lambda e: bells(),
           city=lambda e: city_amb(e.get("dur", 3.0)), ui_open=lambda e: ui_open(), ui_click=lambda e: ui_click(), stamp=lambda e: stamp(),
           sparkle=lambda e: sparkle(), bridge=lambda e: bridge(),
           whoosh=lambda e: sq.whoosh(e.get("dur", 0.4), e.get("pitch", 1.0)), chime=lambda e: sq.chime(),
           step=lambda e: sq.step(e.get("pitch", 1.0)), shimmer=lambda e: sq.shimmer(e.get("dur", 2.5)),
           stars=lambda e: sq.stars(e.get("dur", 3.0)), roar=lambda e: sq.roar())
LEVEL = dict(pop=0.35, loot_land=0.30, pickup=0.35, coins=0.35, paw=0.45, fanfare=0.32, bells=0.25, city=0.22, ui_open=0.3,
             ui_click=0.3, stamp=0.55, sparkle=0.3, bridge=0.4, whoosh=0.35, chime=0.14, step=0.18, shimmer=0.22, stars=0.12, roar=0.35)

def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, w.getnchannels()) / 32768.0
    return a if a.shape[1] == 2 else np.repeat(a, 2, axis=1)

def make(seg):
    global N, mix
    hud = json.load(open(os.path.join(CH, f"hud_{seg}.json"))); fps = int(hud["fps"]); DUR = int(hud["frames"]) / fps
    N = int(DUR * SR); mix = np.zeros((N, 2)); evs = list(hud["events"])
    if seg == "loot":
        for L in hud["loot"]: evs.append(dict(frame=L["pick"] + 8, kind="coins" if L["id"] == "coins" else "pickup", dur=0.6))
    if seg in ("city", "establish") and not any(e["kind"] == "city" for e in evs): evs.append(dict(frame=1, kind="city", dur=DUR))
    for e in evs:
        if e["kind"] not in GEN: continue
        put(GEN[e["kind"]](e), (e["frame"] - 1) / fps, LEVEL[e["kind"]] * e.get("gain", 1.0), pan=float(rng.uniform(-0.3, 0.3)))
    t = np.arange(N) / SR
    if seg in ("loot", "mount", "ride"):                   # meadow wind + birds
        wind = norm(bandpass(rng.normal(0, 1, N), 80, 700)) * 0.035 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t + 1.0)); mix += wind[:, None]
        for bt in np.arange(0.6, DUR - 1, 2.1) + rng.uniform(0, 1.0, len(np.arange(0.6, DUR - 1, 2.1))):
            n = int(0.12 * SR); tt = np.arange(n) / SR
            for k in range(rng.integers(2, 4)):
                f = rng.uniform(3200, 4800) * (1 + 0.3 * np.sin(2 * np.pi * 18 * tt))
                put(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.12) ** 2, bt + k * 0.16, 0.025, pan=float(rng.uniform(-0.8, 0.8)))
    if seg == "montage":
        put(city_amb(DUR), 0, 0.12)
    ir_n = int(0.7 * SR); ir = rng.normal(0, 1, ir_n) * np.exp(-np.arange(ir_n) / SR * 7); ir /= np.sqrt((ir ** 2).sum())
    for c in range(2):
        wet = np.fft.irfft(np.fft.rfft(mix[:, c], N + ir_n) * np.fft.rfft(ir, N + ir_n))[:N]; mix[:, c] += 0.18 * wet
    mix /= np.abs(mix).max() + 1e-9; mix = np.tanh(2.0 * mix) / np.tanh(2.0) * 0.89
    if "melody" in hud:
        mel = read_wav(os.path.join(CH, hud["melody"]["file"])); f0 = hud["melody"]["f0"]; f1 = hud["melody"]["f1"]
        i0 = int((f0 - 1) / fps * SR); m = min(len(mel), int((f1 - f0) / fps * SR), N - i0)
        mel = mel[:m].copy(); fo = int(0.8 * SR); mel[-fo:] *= np.linspace(1, 0, fo)[:, None]; mel /= np.abs(mel).max()
        g = hud["melody"].get("gain", 0.85)
        if g > 0.6: mix *= 0.7
        mix[i0:i0 + m] += g * mel
    rms = np.sqrt((mix ** 2).mean()); mix *= 0.12 / max(rms, 1e-6)
    pk = np.abs(mix).max()
    if pk > 0.95: mix = np.tanh(mix / pk * 1.6) / np.tanh(1.6) * 0.95
    with wave.open(os.path.join(CH, f"sfx_{seg}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    print("wrote", f"sfx_{seg}.wav", round(DUR, 2), "s", len(evs), "events")

if __name__ == "__main__":
    for s in (sys.argv[1:] or ["loot", "mount", "ride", "establish", "city", "montage"]):
        if os.path.exists(os.path.join(CH, f"hud_{s}.json")): make(s)
