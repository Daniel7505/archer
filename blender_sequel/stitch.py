"""stitch.py - encodes the HUD-composited segments with their SFX and stitches the film:
ocarina intro (../ocarina/ocarina_performance.mp4) -> fight (archer wins) -> spirit capture -> travel + Grubbo fight
-> ocarina summon / ghost panda / K.O.   1280x720, 24 fps, per-segment loudnorm, 0.4 s crossfades (video + audio).
Usage: python3 stitch.py  -> full_film.mp4"""
import subprocess, os, json
SEQ = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(SEQ, "tmp"); os.makedirs(T, exist_ok=True)
XF = 0.4
LN = "loudnorm=I=-18:TP=-1.5:LRA=11,aresample=44100"
def run(cmd):
    print(" ".join(cmd[:6]), "..."); subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
segs = []
intro = os.path.join(T, "seg0_intro.mp4")
run(["ffmpeg", "-y", "-i", os.path.join(SEQ, "..", "ocarina", "ocarina_performance.mp4"), "-vf", "scale=1280:720,fps=24,format=yuv420p",
     "-af", LN, "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-ac", "2", intro])
segs.append(intro)
for i, s in enumerate(["fight", "capture", "brute", "summon"], 1):
    o = os.path.join(T, f"seg{i}_{s}.mp4")
    run(["ffmpeg", "-y", "-framerate", "24", "-i", os.path.join(SEQ, f"comp_{s}", "f_%04d.png"), "-i", os.path.join(SEQ, f"sfx_{s}.wav"),
         "-af", LN, "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-ac", "2", "-shortest", o])
    segs.append(o)
D = [dur(p) for p in segs]
inputs = sum([["-i", p] for p in segs], [])
fc = []; v = "[0:v]"; a = "[0:a]"; acc = D[0]
for i in range(1, len(segs)):
    off = acc - XF
    fc.append(f"{v}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[v{i}]")
    fc.append(f"{a}[{i}:a]acrossfade=d={XF}:c1=tri:c2=tri[a{i}]")
    v = f"[v{i}]"; a = f"[a{i}]"; acc = acc + D[i] - XF
fc.append(f"{a}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[aout]")
out = os.path.join(SEQ, "full_film.mp4")
run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", v, "-map", "[aout]", "-c:v", "libx264", "-crf", "18",
     "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
starts = []; acc = 0
for i, d in enumerate(D):
    starts.append(round(acc, 2)); acc += d - XF
json.dump(dict(segments=["intro", "fight", "capture", "brute", "summon"], durations=D, starts=starts, crossfade=XF,
               total=dur(out)), open(os.path.join(SEQ, "film_timeline.json"), "w"), indent=1)
print("FILM", out, round(dur(out), 2), "s; segment starts", starts)
