"""hud_composite.py - draws the game HUD on top of the rendered frames (PIL):
bottom HP bars (archer left, enemy right) with a lagging damage trail, floating damage numbers at the
screen positions projected in Blender (hud_<seg>.json), CRIT!/CRUSHING BLOW!/heal/dodge/K.O. popups and
Grubbo's name card.   python3 hud_composite.py [seg ...]    (segments: fight capture brute summon)
Damage values come from rolls.json (seeded RNG, see rolls.py)."""
import json, os, sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SEQ = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720
def font(name, size):
    for p in (os.path.join(SEQ, "fonts", name), f"/usr/share/fonts/truetype/sand-box/google/{name.split('-')[0].replace('LuckiestGuy', 'Luckiest Guy').replace('LilitaOne', 'Lilita One')}/{name}",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()
F_NUM = font("LuckiestGuy-Regular.ttf", 46); F_NUM_BIG = font("LuckiestGuy-Regular.ttf", 60)
F_TAG = font("LuckiestGuy-Regular.ttf", 26); F_NAME = font("LilitaOne-Regular.ttf", 24); F_HP = font("LilitaOne-Regular.ttf", 20)
F_CARD = font("LuckiestGuy-Regular.ttf", 64); F_SUB = font("LilitaOne-Regular.ttf", 28)

R = json.load(open(os.path.join(SEQ, "rolls.json")))
ROLL = {r["id"]: r for r in R["rolls"]}

COL = dict(dmg=(255, 255, 255), crit=(255, 196, 40), crush=(255, 70, 50), heal=(90, 255, 120), miss=(220, 230, 255),
           ko=(255, 220, 60))

# segment definitions: frames source, starting HP, enemy bar
SEGS = {
    "fight":   dict(n=420, src=lambda f: os.path.join(SEQ, "..", "fight", "frames", f"f_{f:04d}.png") if f <= 265
                    else os.path.join(SEQ, "frames_fightwin", f"f_{f:04d}.png"),
                    hud="hud_fightwin.json", archer=100, cuts=[61, 96, 146, 180, 236, 266, 300, 322, 351, 384], enemy=("PANDA", 80, 80), enemy_vis=(1, 420)),
    "capture": dict(n=120, src=lambda f: os.path.join(SEQ, "frames_capture", f"f_{f:04d}.png"), hud="hud_capture.json",
                    archer=None, enemy=("PANDA", 0, 80), enemy_vis=(1, 30)),
    "brute":   dict(n=264, src=lambda f: os.path.join(SEQ, "frames_brute", f"f_{f:04d}.png"), hud="hud_brute.json", cuts=[73, 109, 136, 176, 206],
                    archer=None, enemy=("GRUBBO THE GREEDY", 120, 120), enemy_vis=(86, 264)),
    "summon":  dict(n=240, src=lambda f: os.path.join(SEQ, "frames_summon", f"f_{f:04d}.png"), hud="hud_summon.json", cuts=[65, 104, 151, 201],
                    archer=None, enemy=("GRUBBO THE GREEDY", None, 120), enemy_vis=(1, 240)),
}

def hp_timeline():
    """archer/enemy HP at the start of every segment, following the story order."""
    a = 100; out = {}
    pf = 80
    out["fight"] = dict(archer=a, enemy=80)
    for k in ("L1", "A2", "A3", "L2", "A4", "K", "L3", "A5"):
        if ROLL[k]["target"] == "archer": a -= ROLL[k]["dmg"]
    out["capture"] = dict(archer=a, enemy=0)
    a = min(100, a + R["heal"]); b = 120
    out["brute"] = dict(archer=a, enemy=b)
    for k in ("A6", "BASH1", "A7"):
        if ROLL[k]["target"] == "archer": a -= ROLL[k]["dmg"]
        else: b -= ROLL[k]["dmg"]
    out["summon"] = dict(archer=a, enemy=b)
    return out

def outlined(d, xy, text, f, fill, stroke=(20, 12, 8), sw=4, anchor="mm", alpha=255):
    d.text(xy, text, font=f, fill=(*fill, alpha), stroke_width=sw, stroke_fill=(*stroke, alpha), anchor=anchor)

def bar(d, x, y, w, h, val, trail, mx, col, name, right=False, alpha=255):
    a = alpha
    d.rounded_rectangle((x - 3, y - 3, x + w + 3, y + h + 3), radius=8, fill=(15, 10, 8, int(a * 0.85)))
    d.rounded_rectangle((x, y, x + w, y + h), radius=6, fill=(60, 45, 40, a))
    def seg(v, c):
        L = max(0, min(1, v / mx)) * w
        if L < 2: return
        if right: d.rounded_rectangle((x + w - L, y, x + w, y + h), radius=6, fill=(*c, a))
        else: d.rounded_rectangle((x, y, x + L, y + h), radius=6, fill=(*c, a))
    seg(trail, (255, 235, 160)); seg(val, col)
    # glossy highlight
    d.rectangle((x + 4, y + 3, x + w - 4, y + h // 3), fill=(255, 255, 255, int(a * 0.18)))
    nx = x + w if right else x
    outlined(d, (nx, y - 16), name, F_NAME, (255, 245, 225), sw=3, anchor="rs" if right else "ls", alpha=a)
    outlined(d, (x + w if not right else x, y - 16), f"{max(0, round(val))} / {mx}", F_HP, (255, 255, 255), sw=3,
             anchor="rs" if not right else "ls", alpha=a)

def hp_col(v, mx):
    k = v / mx
    if k > 0.5: return (70, 200, 80)
    if k > 0.25: return (235, 190, 40)
    return (225, 60, 45)

def run(seg):
    S = SEGS[seg]; hud = json.load(open(os.path.join(SEQ, S["hud"])))
    start = hp_timeline()[seg]
    out = os.path.join(SEQ, f"comp_{seg}"); os.makedirs(out, exist_ok=True)
    # change lists: (frame, who, delta)
    ch = []; pops = []
    for h in hud["hits"]:
        f = h["frame"]
        if h.get("id"):
            r = ROLL[h["id"]]; who = "archer" if r["target"] == "archer" else "enemy"
            ch.append((f, who, -r["dmg"]))
            kind = "crush" if (r["crit"] and r["attacker"] in ("panda", "brute")) else ("crit" if r["crit"] else "dmg")
            pops.append(dict(f=f, x=h["x"], y=h["y"], text=f"-{r['dmg']}", tag=r["tag"], kind=kind, who=who))
        else:
            if h["kind"] == "heal": ch.append((f, "archer", R["heal"]))
            pops.append(dict(f=f, x=h["x"], y=h["y"], text=h["text"], tag="", kind=h["kind"], who=h.get("target")))
    def hp_at(who, f, lag=0):
        v = start["archer" if who == "archer" else "enemy"]
        for cf, w, dv in ch:
            if w != who: continue
            t = (f - cf - lag) / 6.0
            if t >= 0: v += dv * min(1.0, t)
        return v
    mx_e = S["enemy"][2]; ename = S["enemy"][0]
    for f in (ONLY or range(1, S["n"] + 1)):
        src = S["src"](f)
        im = Image.open(src).convert("RGBA")
        if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        # bottom vignette strip so the bars read on bright grass
        grad = Image.new("L", (1, 120)); grad.putdata([int(150 * (i / 119) ** 1.6) for i in range(120)])
        ov.paste((0, 0, 0, 255), (0, H - 120, W, H), grad.resize((W, 120)))
        d = ImageDraw.Draw(ov)
        va = hp_at("archer", f); ta = max(va, hp_at("archer", f, lag=14))
        bar(d, 40, H - 52, 430, 22, va, ta, 100, hp_col(va, 100), "ARCHER")
        e0, e1 = S["enemy_vis"]
        if e0 <= f <= e1:
            fade = 255
            if seg == "capture": fade = int(255 * max(0, 1 - (f - 1) / 30))
            if seg == "brute": fade = int(255 * min(1, (f - e0) / 10))
            if fade > 0:
                ve = max(0, hp_at("enemy", f)); te = max(ve, hp_at("enemy", f, lag=14))
                bar(d, W - 40 - 430, H - 52, 430, 22, ve, te, mx_e, hp_col(max(ve, 0.01), mx_e) if ve > 0 else (90, 90, 90),
                    ename + ("  (K.O.)" if ve <= 0 and seg == "summon" else ""), right=True, alpha=fade)
        # name card
        card = hud.get("card")
        if card and card["f0"] <= f <= card["f1"]:
            t = f - card["f0"]; L = card["f1"] - card["f0"]
            a = int(255 * min(1, t / 6, (L - t) / 8))
            slide = int(40 * (1 - min(1, t / 8)) ** 2)
            d.rounded_rectangle((W // 2 - 330, 70 - slide, W // 2 + 330, 190 - slide), radius=14, fill=(60, 15, 90, int(a * 0.72)),
                                outline=(255, 200, 40, a), width=4)
            outlined(d, (W // 2, 118 - slide), card["text"], F_CARD, (255, 205, 40), stroke=(50, 10, 70), sw=5, alpha=a)
            outlined(d, (W // 2, 164 - slide), card["sub"], F_SUB, (255, 245, 230), stroke=(40, 10, 60), sw=3, alpha=a)
            outlined(d, (W // 2, 214 - slide), "120 HP   |   SHOULDER BASH 25", F_HP, (255, 230, 200), sw=3, alpha=a)
        # floating popups
        for p in pops:
            t = f - p["f"]; L = 34 if p["kind"] in ("dmg", "miss") else 40
            nxt = [c for c in S.get("cuts", []) if c > p["f"]]
            if nxt: L = min(L, nxt[0] - 1 - p["f"])
            if not (0 <= t <= L): continue
            a = int(255 * min(1, (L - t) / max(3, min(10, L / 3))))
            pop = 1.0 + 0.5 * max(0, 1 - t / 5)
            k = sum(1 for q in pops if q is not p and 0 < p["f"] - q["f"] <= 15 and q["kind"] not in ("heal",))
            x = p["x"] * W + 120 * k * (1 if k % 2 else -1); y = p["y"] * H - 70 * (1 - (1 - t / L) ** 2)
            x = min(max(x, 120), W - 120); y = min(max(y, 90), H - 150)
            col = COL[p["kind"]]
            big = p["kind"] in ("crit", "crush", "ko", "heal")
            fsz = int((60 if big else 46) * pop)
            fnt = font("LuckiestGuy-Regular.ttf", fsz)
            txt = p["text"]
            if p["kind"] == "heal": fnt = font("LuckiestGuy-Regular.ttf", int(40 * pop))
            outlined(d, (x, y), txt, fnt, col, sw=5, alpha=a)
            if p["tag"]:
                outlined(d, (x, y - fsz * 0.85), p["tag"], font("LuckiestGuy-Regular.ttf", int(28 * min(pop, 1.2))),
                         col, stroke=(60, 10, 0) if p["kind"] == "crush" else (40, 20, 0), sw=4, alpha=a)
        # subtle glow behind popups
        im = Image.alpha_composite(im, ov).convert("RGB")
        im.save(os.path.join(out, f"f_{f:04d}.png"), compress_level=1)
    print("HUD", seg, "done", S["n"], "frames; start HP", start)

ONLY = None
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("only=")]
    for a in sys.argv[1:]:
        if a.startswith("only="): ONLY = [int(x) for x in a[5:].split(",")]
    for s in (args or list(SEGS)): run(s)
