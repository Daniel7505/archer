"""hud_ch2.py - 2D overlays for Chapter 2 (PIL, system python):
 loot      WoW-style backpack grid (slots fill at the pick-up frames, rarity-coloured names, loot toasts, gold counter)
 mount     song caption + "New mount" toast
 ride      passthrough
 establish ALDERMOOR title card
 city      zone text "Market Square"
 montage   Ken Burns over the vendor stills + vendor UI (sell rows, SOLD stamps, gold counter ticking) + dusk ending card
Icons are drawn procedurally into icons/.  python3 hud_ch2.py [seg ...]   -> comp_<seg>/f_####.png (+ hud_montage.json events)"""
import json, os, sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CH = os.path.dirname(os.path.abspath(__file__)); W, H = 1280, 720; FPS = 24
def font(name, size): return ImageFont.truetype(os.path.join(CH, "fonts", name), size)
LG = "LuckiestGuy-Regular.ttf"; LO = "LilitaOne-Regular.ttf"
RAR = {"Common": (240, 240, 240), "Uncommon": (40, 230, 40), "Rare": (40, 130, 255), "Epic": (185, 80, 255)}
GOLD = (255, 205, 60)
LOOT = json.load(open(os.path.join(CH, "hud_loot.json")))["loot"]

def outlined(d, xy, text, f, fill, stroke=(15, 10, 8), sw=3, anchor="mm", alpha=255):
    d.text(xy, text, font=f, fill=(*fill[:3], alpha), stroke_width=sw, stroke_fill=(*stroke, alpha), anchor=anchor)
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def back_out(x):
    x = max(0.0, min(1.0, x)); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ------------------------------------------------------------------ icons (procedural, original)
def make_icons():
    os.makedirs(os.path.join(CH, "icons"), exist_ok=True); S = 192; out = {}
    def canvas(): return Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # Gold-Coin Buckle: gold frame with a coin in the middle and a prong
    im = canvas(); d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 46, 166, 146), 26, outline=(150, 100, 20), width=22); d.rounded_rectangle((30, 50, 162, 142), 24, outline=(255, 205, 70), width=14)
    d.ellipse((66, 66, 126, 126), fill=(255, 215, 80), outline=(160, 105, 20), width=6); d.text((96, 96), "G", font=font(LG, 40), fill=(170, 110, 20), anchor="mm")
    d.rectangle((4, 84, 30, 108), fill=(120, 72, 36)); d.rectangle((162, 84, 188, 108), fill=(120, 72, 36)); out["buckle"] = im
    # Moustache Comb: ivory comb + a little moustache silhouette
    im = canvas(); d = ImageDraw.Draw(im)
    d.rounded_rectangle((22, 50, 170, 86), 14, fill=(240, 228, 196), outline=(140, 120, 90), width=5)
    for i in range(12): d.rectangle((30 + i * 12, 84, 37 + i * 12, 150), fill=(240, 228, 196), outline=(140, 120, 90), width=2)
    d.chord((60, 56, 98, 80), 0, 180, fill=(90, 55, 30)); d.chord((94, 56, 132, 80), 0, 180, fill=(90, 55, 30)); out["comb"] = im
    # Mystery Shard: purple crystal with glow
    im = canvas(); d = ImageDraw.Draw(im)
    g = Image.new("RGBA", (S, S), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse((30, 30, 162, 162), fill=(170, 80, 255, 140)); g = g.filter(ImageFilter.GaussianBlur(18))
    im.alpha_composite(g); d = ImageDraw.Draw(im)
    d.polygon([(96, 14), (140, 80), (110, 178), (60, 150), (52, 70)], fill=(150, 70, 230), outline=(240, 200, 255))
    d.polygon([(96, 14), (110, 178), (60, 150)], fill=(190, 120, 255)); d.line([(96, 14), (110, 178)], fill=(250, 230, 255), width=3); out["shard"] = im
    # 12 Gold Coins: stack
    im = canvas(); d = ImageDraw.Draw(im)
    for k in range(6): y = 150 - k * 16; d.ellipse((40, y - 18, 130, y + 18), fill=(235, 180, 40), outline=(150, 95, 15), width=5)
    for k in range(3): y = 160 - k * 16; d.ellipse((96, y - 16, 176, y + 16), fill=(255, 210, 70), outline=(150, 95, 15), width=5)
    out["coins"] = im
    # coin glyph for counters
    im = canvas(); d = ImageDraw.Draw(im); d.ellipse((16, 16, 176, 176), fill=(255, 205, 60), outline=(150, 95, 15), width=14)
    d.ellipse((56, 56, 136, 136), outline=(200, 140, 30), width=8); out["coin"] = im
    for k, v in out.items(): v.save(os.path.join(CH, "icons", f"{k}.png"))
    return out
ICONS = make_icons()
def icon(k, s): return ICONS[k].resize((s, s), Image.LANCZOS)

def slot(ov, d, x, y, s, item=None, rar=None, pop=1.0, glow=0.0):
    d.rounded_rectangle((x, y, x + s, y + s), 8, fill=(25, 22, 30, 235), outline=(90, 80, 70, 255), width=2)
    if item:
        if glow > 0:
            g = Image.new("RGBA", (s + 40, s + 40), (0, 0, 0, 0)); ImageDraw.Draw(g).rounded_rectangle((12, 12, s + 28, s + 28), 12, fill=(*RAR[rar], int(200 * glow)))
            ov.alpha_composite(g.filter(ImageFilter.GaussianBlur(8)), (x - 20, y - 20))
        ss = max(4, int((s - 10) * pop)); ov.alpha_composite(icon(item, ss), (x + (s - ss) // 2, y + (s - ss) // 2))
        d.rounded_rectangle((x, y, x + s, y + s), 8, outline=(*RAR[rar], 255), width=3)

def bag(ov, f, x0, y0, filled, gold, alpha_k=1.0, highlight=None):
    """backpack panel: 4x3 grid; filled = [(id, rarity, fill_frame)]"""
    d = ImageDraw.Draw(ov); s = 62; gap = 8; cols, rows = 4, 3
    w = cols * s + (cols + 1) * gap; h = rows * s + (rows + 1) * gap + 78
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 14, fill=(48, 34, 24, 235), outline=(200, 160, 80, 255), width=4)
    d.rounded_rectangle((x0 + 6, y0 + 6, x0 + w - 6, y0 + 38), 9, fill=(80, 55, 32, 255))
    outlined(d, (x0 + w // 2, y0 + 22), "BACKPACK", font(LG, 24), (255, 225, 150), sw=2)
    for i in range(cols * rows):
        cx = x0 + gap + (i % cols) * (s + gap); cy = y0 + 44 + gap + (i // cols) * (s + gap)
        it = filled[i] if i < len(filled) else None
        if it and f >= it[2]:
            k = (f - it[2]) / 8; slot(ov, d, cx, cy, s, it[0], it[1], pop=back_out(k), glow=max(0, 1 - (f - it[2]) / 30) + (0.6 if highlight == i else 0))
        else: slot(ov, d, cx, cy, s)
    ov.alpha_composite(icon("coin", 26), (x0 + 14, y0 + h - 36))
    outlined(d, (x0 + 48, y0 + h - 23), f"{gold}", font(LG, 26), GOLD, sw=3, anchor="lm")
    outlined(d, (x0 + w - 14, y0 + h - 23), f"{sum(1 for it in filled if f >= it[2])}/12", font(LO, 20), (230, 220, 200), sw=2, anchor="rm")
    return w, h

def toast(d, x, y, parts, alpha):
    """parts: [(text, colour)] drawn left->right"""
    fx = font(LO, 26)
    for t, c in parts:
        outlined(d, (x, y), t, fx, c, sw=3, anchor="lm", alpha=alpha); x += d.textlength(t, font=fx)

def load(seg, f):
    if seg == "ride" and f <= 84 and os.path.exists(os.path.join(CH, "frames_ride1", f"f_{f:04d}.png")) and os.path.getsize(os.path.join(CH, "frames_ride1", f"f_{f:04d}.png")) > 0:
        seg = "ride1"     # re-framed side-tracking shot
    return Image.open(os.path.join(CH, f"frames_{seg}", f"f_{f:04d}.png")).convert("RGBA")
def save(seg, f, im):
    out = os.path.join(CH, f"comp_{seg}"); os.makedirs(out, exist_ok=True)
    im.convert("RGB").save(os.path.join(out, f"f_{f:04d}.png"), compress_level=1)

# ------------------------------------------------------------------ segments
def seg_loot():
    hud = json.load(open(os.path.join(CH, "hud_loot.json"))); n = hud["frames"]
    filled = [(L["id"], L["rarity"], L["pick"] + 8) for L in LOOT]
    for f in range(1, n + 1):
        im = load("loot", f); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        k = ease((f - 108) / 12)
        if k > 0:
            gold = 12 if f >= filled[3][2] else 0
            bw, bh = 4 * 62 + 5 * 8, 3 * 62 + 4 * 8 + 78
            x0 = int(W - 24 - bw + (1 - k) * (bw + 40)); y0 = H - 24 - bh
            bag(ov, f, x0, y0, filled, gold)
            for i, L in enumerate(LOOT):                     # tooltip next to the slot for ~1.6 s
                fs = filled[i][2]; dt = f - fs
                life = min(40, filled[i + 1][2] - fs) if i + 1 < len(filled) else 40
                if 0 <= dt < life:
                    a = int(255 * min(1, dt / 4) * min(1, (life - dt) / 4))
                    sx = x0 + 8 + (i % 4) * 70; sy = y0 + 52 + (i // 4) * 70
                    tw = max(d.textlength(L["name"], font=font(LO, 24)), 120) + 28
                    tx = sx + 31 - tw // 2; tx = min(tx, W - 10 - tw); ty = sy - 74
                    d.rounded_rectangle((tx, ty, tx + tw, ty + 62), 8, fill=(12, 14, 30, int(a * 0.92)), outline=(*RAR[L["rarity"]], a), width=2)
                    outlined(d, (tx + 14, ty + 20), L["name"], font(LO, 24), RAR[L["rarity"]], sw=2, anchor="lm", alpha=a)
                    outlined(d, (tx + 14, ty + 45), L["rarity"], font(LO, 18), (210, 210, 210), sw=2, anchor="lm", alpha=a)
        # loot toasts (bottom-left, stacking)
        shown = [(i, L) for i, L in enumerate(LOOT) if f >= filled[i][2]]
        for j, (i, L) in enumerate(shown):
            dt = f - filled[i][2]; a = int(255 * min(1, dt / 5))
            if L["id"] == "coins": parts = [("You loot ", (255, 240, 200)), ("12 Gold", GOLD)]
            else: parts = [("You receive loot: ", (255, 240, 200)), (f"[{L['name']}]", RAR[L["rarity"]])]
            toast(d, 30, H - 40 - (len(shown) - 1 - j) * 34, parts, a)
        save("loot", f, Image.alpha_composite(im, ov))
    print("loot done", n)

def seg_mount():
    hud = json.load(open(os.path.join(CH, "hud_mount.json"))); n = hud["frames"]
    for f in range(1, n + 1):
        im = load("mount", f); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        if 20 <= f <= 100:
            a = int(255 * min(1, (f - 20) / 8) * min(1, (100 - f) / 10))
            outlined(d, (W // 2, H - 60), "~ The Swiftpaw Air ~", font(LO, 34), (190, 235, 255), stroke=(10, 25, 45), sw=3, alpha=a)
            outlined(d, (W // 2, H - 28), "a new ocarina song", font(LO, 20), (220, 230, 240), sw=2, alpha=a)
        if 128 <= f:
            k = back_out((f - 128) / 10); a = int(255 * min(1, (f - 128) / 6))
            bw = 420; x0 = W // 2 - bw // 2; y0 = int(40 - (1 - k) * 60)
            d.rounded_rectangle((x0, y0, x0 + bw, y0 + 76), 14, fill=(10, 30, 50, int(a * 0.85)), outline=(130, 220, 255, a), width=3)
            outlined(d, (W // 2, y0 + 24), "NEW MOUNT LEARNED", font(LG, 26), (150, 230, 255), sw=3, alpha=a)
            outlined(d, (W // 2, y0 + 55), "Spirit Panda", font(LO, 26), RAR["Epic"], sw=3, alpha=a)
        save("mount", f, Image.alpha_composite(im, ov))
    print("mount done", n)

def seg_pass(seg):
    hud = json.load(open(os.path.join(CH, f"hud_{seg}.json"))); n = hud["frames"]
    for f in range(1, n + 1): save(seg, f, load(seg, f))
    print(seg, "done", n)

def seg_establish():
    hud = json.load(open(os.path.join(CH, "hud_establish.json"))); n = hud["frames"]
    for f in range(1, n + 1):
        im = load("establish", f); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        if 26 <= f <= 116:
            a = int(255 * min(1, (f - 26) / 14) * min(1, (116 - f) / 12)); sc = 1 + 0.04 * (f - 26) / 90
            outlined(d, (W // 2, 120), "ALDERMOOR", font(LG, int(84 * sc)), (255, 248, 230), stroke=(30, 40, 80), sw=6, alpha=a)
            d.line((W // 2 - 220, 175, W // 2 + 220, 175), fill=(255, 210, 90, a), width=3)
            outlined(d, (W // 2, 205), "the White City by the River", font(LO, 30), (230, 225, 210), stroke=(30, 40, 80), sw=3, alpha=a)
        save("establish", f, Image.alpha_composite(im, ov))
    print("establish done", n)

def seg_city():
    hud = json.load(open(os.path.join(CH, "hud_city.json"))); n = hud["frames"]; c = hud["cuts"][0]
    for f in range(1, n + 1):
        im = load("city", f); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        if c + 6 <= f <= n:
            a = int(255 * min(1, (f - c - 6) / 12) * min(1, (n - f) / 10 + 0.0001))
            outlined(d, (W // 2, 90), "Market Square", font(LG, 54), (255, 230, 140), stroke=(40, 25, 10), sw=5, alpha=a)
            outlined(d, (W // 2, 136), "Aldermoor", font(LO, 28), (240, 235, 225), sw=3, alpha=a)
        save("city", f, Image.alpha_composite(im, ov))
    print("city done", n)

# ------------------------------------------------------------------ montage (stills -> Ken Burns + vendor UI)
VEND = [("mira", "Mira the Jeweler", "\"Real coin-gold! I'll pay well.\"", "buckle", 35, (0.0, 0.0, 1.0, 1.10, 0.06, 0.02)),
        ("tobin", "Old Tobin, Barber & Curios", "\"A comb fit for a fine moustache!\"", "comb", 9, (0.0, 0.0, 1.08, 1.0, 0.04, 0.05)),
        ("seer", "Seer Ilvane", "\"This shard hums with old magic... keep it.\"", "shard", None, (0.0, 0.0, 1.0, 1.12, 0.05, 0.0))]
SEGF = 108; DUSKF = 144
def kb(src, f, n, z0, z1, dx, dy):
    k = ease(f / max(1, n - 1)); z = z0 + (z1 - z0) * k
    w = W / z; h = H / z; cx = W / 2 + dx * W * (k - 0.5); cy = H / 2 + dy * H * (k - 0.5)
    cx = min(max(cx, w / 2), W - w / 2); cy = min(max(cy, h / 2), H - h / 2)
    return src.crop((int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))).resize((W, H), Image.BICUBIC)

def vendor_panel(ov, d, f, name, quote, sell, price, gold_before, bag_items):
    x0, y0, pw = 34, 70, 430
    rows = bag_items; ph = 150 + 74 * len(rows) + 60
    k = back_out(f / 10); x0 = int(x0 - (1 - k) * 480)
    d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), 16, fill=(40, 28, 20, 238), outline=(205, 165, 85, 255), width=4)
    d.rounded_rectangle((x0 + 8, y0 + 8, x0 + pw - 8, y0 + 56), 10, fill=(92, 60, 34, 255))
    outlined(d, (x0 + pw // 2, y0 + 32), name, font(LG, 25 if len(name) < 20 else 21), (255, 228, 160), sw=2)
    outlined(d, (x0 + pw // 2, y0 + 80), quote, font(LO, 18), (235, 225, 205), sw=2)
    outlined(d, (x0 + 20, y0 + 116), "SELL ITEMS", font(LG, 20), (200, 190, 170), sw=2, anchor="lm")
    gold = gold_before; ev = []
    for i, (iid, iname, rar, pr) in enumerate(rows):
        ry = y0 + 136 + i * 74; is_t = iid == sell
        hl = is_t and 22 <= f
        d.rounded_rectangle((x0 + 14, ry, x0 + pw - 14, ry + 64), 10, fill=(70, 52, 34, 255) if hl else (55, 40, 28, 230),
                            outline=(*RAR[rar], 255) if hl else (90, 70, 50, 255), width=3 if hl else 1)
        slot(ov, d, x0 + 20, ry + 4, 56, iid, rar)
        outlined(d, (x0 + 88, ry + 22), iname, font(LO, 22), RAR[rar], sw=2, anchor="lm")
        ptxt = "Not for sale" if pr is None else f"{pr} gold"
        outlined(d, (x0 + 88, ry + 46), ptxt, font(LO, 18), GOLD if pr else (200, 180, 230), sw=2, anchor="lm")
        if is_t and f >= 40:
            sk = back_out((f - 40) / 8); stamp = "SOLD!" if price else "KEEP"
            st = Image.new("RGBA", (240, 90), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
            colr = (230, 40, 40) if price else (170, 90, 255)
            sd.rounded_rectangle((6, 6, 234, 84), 12, outline=(*colr, 255), width=6)
            sd.text((120, 46), stamp, font=font(LG, 50), fill=(*colr, 255), anchor="mm")
            st = st.rotate(-12, expand=True, resample=Image.BICUBIC)
            s = max(0.05, 2.2 - 1.2 * sk); st = st.resize((max(1, int(st.width * s * 0.62)), max(1, int(st.height * s * 0.62))), Image.LANCZOS)
            st.putalpha(st.getchannel("A").point(lambda v: int(v * min(1, (f - 40) / 4))))
            ov.alpha_composite(st, (int(x0 + pw - 30 - st.width), int(ry + 32 - st.height / 2)))
    if price:
        k2 = ease((f - 46) / 30); gold = gold_before + int(round(price * k2))
        for j in range(10):                                   # coins flying to the counter
            t = (f - 46 - j * 2) / 14
            if 0 < t < 1:
                sx, sy = x0 + pw - 90, y0 + 136 + 32; ex, ey = x0 + 60, y0 + ph - 30
                px = sx + (ex - sx) * t; py = sy + (ey - sy) * t - 60 * math.sin(math.pi * t)
                ov.alpha_composite(icon("coin", 22), (int(px), int(py)))
    d.rounded_rectangle((x0 + 14, y0 + ph - 50, x0 + pw - 14, y0 + ph - 12), 10, fill=(25, 18, 12, 255))
    ov.alpha_composite(icon("coin", 28), (x0 + 24, y0 + ph - 45))
    pulse = 1.0 + (0.15 * math.sin(math.pi * min(1, max(0, (f - 46) / 30))) if price else 0)
    outlined(d, (x0 + 62, y0 + ph - 31), f"{gold}", font(LG, int(28 * pulse)), GOLD, sw=3, anchor="lm")
    outlined(d, (x0 + pw - 26, y0 + ph - 31), "gold", font(LO, 20), (230, 215, 180), sw=2, anchor="rm")
    return gold

def seg_montage():
    events = []; F = 0; gold = 12
    items = [("buckle", "Gold-Coin Buckle", "Rare", 35), ("comb", "Moustache Comb", "Uncommon", 9), ("shard", "Mystery Shard", "Epic", None)]
    for vi, (kind, name, quote, sell, price, kbp) in enumerate(VEND):
        src = Image.open(os.path.join(CH, "stills", f"vendor_{kind}.png")).convert("RGBA")
        rows = [it for it in items]
        for f in range(SEGF):
            im = kb(src, f, SEGF, kbp[2], kbp[3], kbp[4], kbp[5]); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
            g = vendor_panel(ov, d, f, name, quote, sell, price, gold, rows)
            save("montage", F + f + 1, Image.alpha_composite(im, ov))
        events += [dict(frame=F + 4, kind="ui_open"), dict(frame=F + 22, kind="ui_click")]
        if price: events += [dict(frame=F + 40, kind="stamp"), dict(frame=F + 46, kind="coins", dur=1.3)]
        else: events += [dict(frame=F + 40, kind="sparkle")]
        if price: gold += price; items = [it for it in items if it[0] != sell]
        F += SEGF
    src = Image.open(os.path.join(CH, "stills", "dusk_skyline.png")).convert("RGBA")
    for f in range(DUSKF):
        im = kb(src, f, DUSKF, 1.12, 1.0, -0.05, 0.03); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        a = int(255 * min(1, max(0, (f - 30) / 18)))
        if a:
            outlined(d, (W // 2, H - 150), "CHAPTER 2  -  ALDERMOOR", font(LG, 46), (255, 235, 190), stroke=(30, 20, 40), sw=5, alpha=a)
            outlined(d, (W // 2, H - 100), f"Gold: {gold}     Bag: Mystery Shard (Epic)     Mount: Spirit Panda", font(LO, 24), (235, 225, 210), sw=3, alpha=a)
        b = int(255 * min(1, max(0, (f - 80) / 18)))
        if b: outlined(d, (W // 2, H - 52), "To be continued...", font(LO, 30), (200, 210, 255), stroke=(20, 20, 50), sw=3, alpha=b)
        fade = max(0, (f - (DUSKF - 18)) / 18)
        im = Image.alpha_composite(im, ov)
        if fade > 0: im = Image.blend(im, Image.new("RGBA", (W, H), (0, 0, 0, 255)), fade)
        save("montage", F + f + 1, im)
    events += [dict(frame=F + 1, kind="bells"), dict(frame=F + 80, kind="chime")]
    F += DUSKF
    json.dump(dict(mode="montage", frames=F, fps=FPS, events=events, gold_final=gold,
                   melody=dict(file="melody2.wav", f0=F - DUSKF - 10, f1=F, gain=0.45)), open(os.path.join(CH, "hud_montage.json"), "w"), indent=1)
    print("montage done", F, "gold", gold)

SEGS = dict(loot=seg_loot, mount=seg_mount, ride=lambda: seg_pass("ride"), establish=seg_establish, city=seg_city, montage=seg_montage)
if __name__ == "__main__":
    for s in (sys.argv[1:] or list(SEGS)): SEGS[s]()
