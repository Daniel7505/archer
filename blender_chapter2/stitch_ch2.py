"""stitch_ch2.py - encodes the HUD-composited Chapter 2 segments with their SFX, stitches chapter2.mp4
(loot -> mount -> ride -> establish -> city -> vendor montage + dusk ending; 0.4 s crossfades), then appends it to the
sequel film with a 1.0 s crossfade -> full_film_v2.mp4.   python3 stitch_ch2.py"""
import subprocess, os, json
CH = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(CH, "tmp"); os.makedirs(T, exist_ok=True)
XF = 0.4; XF_FILM = 1.0
LN = "loudnorm=I=-18:TP=-1.5:LRA=11,aresample=44100"
SEGS = ["loot", "mount", "ride", "establish", "city", "montage"]
def run(cmd):
    print(" ".join(cmd[:6]), "..."); subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
def chain(files, xfs, out, final_ln="loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100", crf="18"):
    D = [dur(p) for p in files]; inputs = sum([["-i", p] for p in files], []); fc = []; v = "[0:v]"; a = "[0:a]"; acc = D[0]
    for i in range(1, len(files)):
        x = xfs[i - 1]; off = acc - x
        fc.append(f"{v}[{i}:v]xfade=transition=fade:duration={x}:offset={off:.3f}[v{i}]")
        fc.append(f"{a}[{i}:a]acrossfade=d={x}:c1=tri:c2=tri[a{i}]"); v = f"[v{i}]"; a = f"[a{i}]"; acc += D[i] - x
    fc.append(f"{a}{final_ln}[aout]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", v, "-map", "[aout]", "-c:v", "libx264", "-crf", crf,
         "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    return D
segs = []
for i, s in enumerate(SEGS):
    o = os.path.join(T, f"c2seg{i}_{s}.mp4")
    run(["ffmpeg", "-y", "-framerate", "24", "-i", os.path.join(CH, f"comp_{s}", "f_%04d.png"), "-i", os.path.join(CH, f"sfx_{s}.wav"),
         "-af", LN, "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-ac", "2", "-shortest", o])
    segs.append(o)
ch2 = os.path.join(CH, "chapter2.mp4")
D = chain(segs, [XF] * (len(segs) - 1), ch2)
starts = []; acc = 0
for d in D: starts.append(round(acc, 2)); acc += d - XF
seq = os.path.join(CH, "..", "sequel", "full_film.mp4")
full = os.path.join(CH, "full_film_v2.mp4")
chain([seq, ch2], [XF_FILM], full)
json.dump(dict(segments=SEGS, durations=D, starts=starts, crossfade=XF, chapter2=dur(ch2),
               full_film_v2=dur(full), chapter2_starts_in_full_film=round(dur(seq) - XF_FILM, 2)), open(os.path.join(CH, "film_timeline.json"), "w"), indent=1)
print("CH2", round(dur(ch2), 2), "s; starts", starts, "| FULL", round(dur(full), 2), "s")
