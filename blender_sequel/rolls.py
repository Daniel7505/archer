"""Seeded combat rolls for the whole sequel (one RNG, rolled in story order).
Archer abilities: 25% crit, +75%.  Enemy hits: 20% crushing blow, +25%.  Ghost-panda lightning: 20, crit -> 35.
python3 rolls.py            -> prints the chosen seed's log and writes rolls.json
python3 rolls.py search     -> lists seeds that give the scripted story (close archer win etc.)"""
import random, json, sys, os

SEQUENCE = [  # (id, attacker, base, kind)
    ("L1", "panda", 20, "lightning"), ("A2", "archer", 15, "arrow"), ("A3", "archer", 15, "arrow"),
    ("L2", "panda", 20, "lightning"), ("A4", "archer", 15, "arrow"), ("K", "panda", 18, "spin_kick"),
    ("L3", "panda", 20, "lightning"), ("A5", "archer", 15, "arrow"),
    ("A6", "archer", 15, "arrow"), ("BASH1", "brute", 25, "shoulder_bash"), ("A7", "archer", 15, "arrow"),
    ("B1", "ghost", 20, "ghost_lightning"), ("B2", "ghost", 20, "ghost_lightning"), ("B3", "ghost", 20, "ghost_lightning")]
HEAL = 40

def roll(seed):
    rng = random.Random(seed); out = []
    for id_, who, base, kind in SEQUENCE:
        r = rng.random()
        if who in ("archer",):
            crit = r < 0.25; dmg = int(base * 1.75) if crit else base; tag = "CRIT!" if crit else ""
        elif who == "ghost":
            crit = r < 0.25; dmg = 35 if crit else 20; tag = "CRIT!" if crit else ""
        else:
            crit = r < 0.20; dmg = int(base * 1.25) if crit else base; tag = "CRUSHING BLOW!" if crit else ""
        out.append(dict(id=id_, attacker=who, kind=kind, base=base, roll=round(r, 4), crit=crit, dmg=dmg, tag=tag))
    return out

def story(seed):
    R = {r["id"]: r for r in roll(seed)}
    a, p = 100, 80
    for k in ("L1", "A2", "A3", "L2", "A4", "K", "L3"):
        if R[k]["attacker"] == "archer": p -= R[k]["dmg"]
        else: a -= R[k]["dmg"]
        if p <= 0 or a <= 0: return None
    if p - R["A5"]["dmg"] > 0: return None
    if not (10 <= a <= 20): return None
    a_end_fight = a; a = min(100, a + HEAL); b = 120
    b -= R["A6"]["dmg"]; a -= R["BASH1"]["dmg"]; b -= R["A7"]["dmg"]
    if a < 8: return None
    if b - R["B1"]["dmg"] - R["B2"]["dmg"] <= 0 or b - R["B1"]["dmg"] - R["B2"]["dmg"] - R["B3"]["dmg"] > 0: return None
    crits = sum(R[k]["crit"] for k in ("A2", "A3", "A4", "A5", "A6", "A7"))
    crush = sum(R[k]["crit"] for k in ("L1", "L2", "K", "L3", "BASH1"))
    gcrit = sum(R[k]["crit"] for k in ("B1", "B2", "B3"))
    if not (crush >= 1 and gcrit >= 1 and R["A5"]["crit"]): return None
    return dict(seed=seed, archer_after_fight=a_end_fight, crits=crits, crush=crush, gcrit=gcrit, archer_end=a)

if __name__ == "__main__":
    if "search" in sys.argv:
        for s in range(5000):
            st = story(s)
            if st: print(st)
        sys.exit()
    SEED = 0
    for s in range(100000):
        st = story(s)
        if st and 13 <= st["archer_after_fight"] <= 17 and st["crush"] >= 2: SEED = s; break
    R = roll(SEED); hp = {"archer": 100, "panda": 80, "brute": 120}
    target = {"L1": "archer", "A2": "panda", "A3": "panda", "L2": "archer", "A4": "panda", "K": "archer", "L3": "archer",
              "A5": "panda", "A6": "brute", "BASH1": "archer", "A7": "brute", "B1": "brute", "B2": "brute", "B3": "brute"}
    for r in R:
        if r["id"] == "A6": hp["archer"] = min(100, hp["archer"] + HEAL)
        t = target[r["id"]]; hp[t] -= r["dmg"]; r["target"] = t; r["hp_after"] = hp[t]
        print(f'{r["id"]:6s} {r["attacker"]:7s} {r["kind"]:16s} roll={r["roll"]:.4f} dmg={r["dmg"]:3d} {r["tag"]:15s} {t} -> {hp[t]}')
    json.dump(dict(seed=SEED, heal=HEAL, rolls=R), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rolls.json"), "w"), indent=1)
    print("SEED", SEED)
