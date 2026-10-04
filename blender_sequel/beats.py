"""beats.py - prints the beat sheet (film timestamps + the actual seeded damage rolls) as markdown -> beat_sheet.md"""
import json, os
SEQ = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(SEQ, "film_timeline.json")))
R = json.load(open(os.path.join(SEQ, "rolls.json"))); ROLL = {r["id"]: r for r in R["rolls"]}
start = dict(zip(TL["segments"], TL["starts"]))
def ts(seg, f): t = start[seg] + (f - 1) / 24; return f"{int(t // 60)}:{t % 60:05.2f}"
rows = []
for seg, hudf in (("fight", "hud_fightwin.json"), ("capture", "hud_capture.json"), ("brute", "hud_brute.json"), ("summon", "hud_summon.json")):
    for h in json.load(open(os.path.join(SEQ, hudf)))["hits"]:
        if h.get("id"):
            r = ROLL[h["id"]]
            rows.append((start[seg] + (h["frame"] - 1) / 24, ts(seg, h["frame"]), seg, h["frame"], h["id"], r["attacker"], r["kind"],
                         f'{r["roll"]:.4f}', r["base"], r["dmg"], r["tag"] or "-", f'{r["target"]} -> {max(0, r["hp_after"])}'))
        else:
            rows.append((start[seg] + (h["frame"] - 1) / 24, ts(seg, h["frame"]), seg, h["frame"], "-", "-", h["text"], "-", "-", "-", "-", h.get("target", "")))
rows.sort()
out = ["| film time | segment | seg frame | id | attacker | move | roll | base | dmg | tag | HP after |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows: out.append("| " + " | ".join(str(x) for x in r[1:]) + " |")
txt = f"Seed {R['seed']} (rolls.py). Segment starts (s): " + ", ".join(f"{k} {v}" for k, v in start.items()) + \
      f"; total {TL['total']:.2f} s\n\n" + "\n".join(out) + "\n"
open(os.path.join(SEQ, "beat_sheet.md"), "w").write(txt); print(txt)
