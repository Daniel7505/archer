# "Lope to Aldermoor" - SECOND original ocarina melody (own composition, not any Nintendo or Blizzard tune): bright D-Lydian galloping figure, 132 bpm
import numpy as np, json, wave
SR = 44100; BPM = 132; BEAT = 60 / BPM; LEAD = 0.8; TAIL = 1.0
NAMES = {"D5":74,"E5":76,"F#5":78,"G#5":80,"A5":81,"B5":83,"C#6":85,"D6":86,"E6":88}
SCALE = ["D5","E5","F#5","G#5","A5","B5","C#6","D6","E6"]   # fingering index = scale position
mel = [("D5",0.5),("F#5",0.5),("A5",0.5),("D6",1),("C#6",0.5),("A5",0.5),("B5",1),
       ("A5",0.5),("F#5",0.5),("E5",0.5),("F#5",0.5),("A5",1.5),
       ("B5",0.5),("C#6",0.5),("D6",0.5),("E6",1),("D6",0.5),("B5",0.5),("A5",2)]
notes = []; t = LEAD
for n, b in mel:
    d = b * BEAT
    notes.append(dict(start=round(t,4), duration=round(d,4), pitch=n, midi=NAMES[n],
                      freq=round(440*2**((NAMES[n]-69)/12),3), fingering_index=SCALE.index(n)))
    t += d
total = t + TAIL
N = int(total * SR); out = np.zeros(N)
rng = np.random.default_rng(9)
for i, nt in enumerate(notes):
    st = int(nt["start"]*SR); dur = nt["duration"]; L = int((dur+0.12)*SR)
    tt = np.arange(L)/SR
    vib = 1 + 0.004*np.sin(2*np.pi*5.2*tt) * np.clip((tt-0.25)/0.3,0,1)
    ph = 2*np.pi*np.cumsum(nt["freq"]*vib)/SR
    tone = np.sin(ph) + 0.10*np.sin(2*ph+0.3) + 0.03*np.sin(3*ph)
    # breath noise: lowpassed white noise, stronger at attack
    nz = rng.standard_normal(L); k = np.ones(12)/12; nz = np.convolve(nz, k, "same")
    nz *= 0.05 + 0.25*np.exp(-tt/0.06)
    att = 0.045; rel = 0.12
    env = np.clip(tt/att,0,1) * np.clip((dur+0.12-tt)/rel,0,1)
    env *= 1 - 0.12*(tt/max(dur,0.1))   # slight decay of breath pressure
    seg = (tone*0.9 + nz*0.6) * env * 0.3
    out[st:st+L] += seg[:max(0,min(L,N-st))]
# light reverb: a few feedback-comb + allpass (Schroeder) stages
def fast_comb(x, d, g):
    y = np.copy(x); n = len(x)
    for s in range(d, n, d):
        e = min(s+d, n); y[s:e] += g*y[s-d:e-d]
    return y
wet = sum(fast_comb(out, int(SR*dl), g) for dl, g in ((0.0297,0.78),(0.0371,0.76),(0.0411,0.74),(0.0437,0.72)))/4
def allpass(x, d, g):
    y = np.zeros_like(x); buf = np.copy(x)
    for s in range(0, len(x), d):
        e = min(s+d, len(x)); prev = y[s-d:e-d] if s>=d else 0; xp = x[s-d:e-d] if s>=d else 0
        y[s:e] = -g*x[s:e] + xp + g*prev
    return y
wet = allpass(allpass(wet, int(SR*0.005), 0.7), int(SR*0.0017), 0.7)
mix = out*0.8 + wet*0.35
fade = np.clip((total - np.arange(N)/SR)/0.6, 0, 1); mix *= fade
mix /= np.max(np.abs(mix))*1.12
st = np.stack([mix, np.roll(mix, int(SR*0.0007))], 1)   # tiny stereo widening
with wave.open("melody2.wav","wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st*32767).astype(np.int16).tobytes())
json.dump(dict(bpm=BPM, total_seconds=round(total,4), fps=24, lead_in=LEAD, scale_for_fingering=SCALE,
               fingering_rule="index k = number of fingers lifted, in order FINGER_LIFT_ORDER",
               notes=notes), open("notes2.json","w"), indent=1)
print("total", total, "notes", len(notes))
