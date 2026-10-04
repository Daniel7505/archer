"""
sequel_scene.py - "Archer vs Panda: Part 2".  Builds four shots on top of ../scene.blend:

  mode=fightwin  the duel re-choreographed from frame 266 so the ARCHER NARROWLY WINS (frames 1-265 are identical
                 to ../fight/frames and are reused);   writes frames_fightwin/ + hud_fightwin.json + sfx_fightwin.json
  mode=capture   defeated panda slumps and fades; its spirit swirls into the blue ocarina (ocarina rig from
                 ../ocarina/ocarina_scene.py)
  mode=brute     travel down the path + the fight with GRUBBO THE GREEDY (original brute character)
  mode=summon    the archer plays the ocarina melody (finger animation from ocarina_scene.py), a ghost panda appears,
                 charges and casts a triple lightning strike; Grubbo is knocked out (cartoon stars)
  mode=export    game-ready brute rig (idle/walk/bash/hit_react/knockout) + ghost-panda material variant

  B=/workspace/blender/blender-4.2.23-linux-x64/blender
  $B -b ../scene.blend -P sequel_scene.py -- mode=<m> [check] [preview frames=a,b] [anim] [still] samples=6 res=1280x720
"""
import bpy, bmesh, math, random, sys, os, json, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

SEQ = "/workspace/archer_scene/sequel"
FIGHT_PY = "/workspace/archer_scene/fight/fight_scene.py"
OCA_PY = "/workspace/archer_scene/ocarina/ocarina_scene.py"
_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SOPTS = dict(a.split("=", 1) for a in _argv if "=" in a)
SACTS = [a for a in _argv if "=" not in a]
MODE = SOPTS.get("mode", "fightwin")

# ---- pull in all fight_scene definitions (panda import, clips, solvers, FX, camera fitting) without running it
_saved_argv = sys.argv
sys.argv = [sys.argv[0], "--", "noauto"]
_g = globals(); _f = _g.get("__file__")
_g["__file__"] = FIGHT_PY
exec(compile(open(FIGHT_PY).read(), FIGHT_PY, "exec"), _g)
_g["__file__"] = _f
sys.argv = _saved_argv
OPTS.clear(); OPTS.update(SOPTS)          # fight_scene.render_setup/parse_res read OPTS
ROLLS = {r["id"]: r for r in json.load(open(os.path.join(SEQ, "rolls.json")))["rolls"]}

def load_ocarina_rig():
    """Run ocarina_scene.py (setup only) in its own namespace: bow stowed, ocarina, finger bones, IK hands,
    finger animation from notes.json on frames 1..NF."""
    sys.argv = [sys.argv[0], "--"]
    ns = {"__name__": "ocarina_setup", "__file__": OCA_PY}
    exec(compile(open(OCA_PY).read(), OCA_PY, "exec"), ns)
    sys.argv = _saved_argv
    return ns

def set_axis(a0, u):
    """re-point fight_scene's fight-frame helpers (fw, AXIS_YAW, camera azimuths) to a new arena."""
    global A0, U, V, AXIS_YAW
    A0 = Vector(a0); U = Vector(u).normalized(); V = Vector((-U.y, U.x)); AXIS_YAW = math.atan2(U.y, U.x)

def mat(name, col, rough=0.6, metal=0.0, emit=None, estr=0.0, sheen=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    # painted look: soft noise variation in the base colour (glTF export uses export_color)
    N = m.node_tree.nodes; L = m.node_tree.links
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9.0
    mx = N.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 0.25
    mx.inputs[6].default_value = (*col, 1); L.new(nz.outputs["Color"], mx.inputs[7])
    L.new(mx.outputs[2], b.inputs["Base Color"])
    m["export_color"] = col
    return m

# ============================================================================= GRUBBO THE GREEDY (original brute)
BR_BONES = ["hips", "spine", "neck", "head", "upperarm.L", "forearm.L", "hand.L", "upperarm.R", "forearm.R",
            "hand.R", "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"]

def build_brute(name="Grubbo"):
    M = dict(
        purple=mat("M_BrutePurple", (0.15, 0.04, 0.42), 0.75, sheen=0.4),
        purple_d=mat("M_BrutePurpleDark", (0.07, 0.02, 0.20), 0.7),
        yellow=mat("M_BruteYellow", (0.95, 0.66, 0.06), 0.7, sheen=0.3),
        skin=mat("M_BruteSkin", (0.72, 0.45, 0.30), 0.55),
        hair=mat("M_BruteMustache", (0.10, 0.055, 0.03), 0.8, sheen=0.6),
        iron=mat("M_BruteIron", (0.40, 0.40, 0.43), 0.35, metal=1.0),
        gold=mat("M_BruteGold", (1.0, 0.70, 0.18), 0.25, metal=1.0),
        leather=mat("M_BruteLeather", (0.25, 0.13, 0.06), 0.6),
        eye=mat("M_BruteEye", (0.02, 0.015, 0.01), 0.2), white=mat("M_BruteEyeWhite", (0.9, 0.88, 0.82), 0.3))
    mats = list(M.keys())
    bm = bmesh.new(); dl = bm.verts.layers.deform.verify()
    def tag(vs, m, g):
        for f in {f for v in vs for f in v.link_faces}: f.material_index = mats.index(m)
        for v in vs: v[dl].clear(); v[dl][BR_BONES.index(g)] = 1.0
        return vs
    def sph(c, r, m, g, sc=(1, 1, 1), sub=2, rot=None):
        Mx = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal((*sc, 1))
        return tag(bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=Mx)["verts"], m, g)
    def cyl(p1, p2, r1, r2, m, g, seg=12, cap=True):
        p1 = Vector(p1); p2 = Vector(p2); d = p2 - p1
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        Mx = Matrix.Translation((p1 + p2) / 2) @ q.to_matrix().to_4x4()
        return tag(bmesh.ops.create_cone(bm, cap_ends=cap, segments=seg, radius1=r1, radius2=r2, depth=d.length, matrix=Mx)["verts"], m, g)
    J = {k: Vector(v) for k, v in dict(
        pelvis=(0, 0, 0.74), chest=(0, 0, 1.30), neck=(0, -0.03, 1.47), headc=(0, -0.06, 1.65),
        shL=(0.44, 0.0, 1.30), elL=(0.60, -0.02, 0.98), wrL=(0.64, -0.08, 0.70), hdL=(0.65, -0.09, 0.60),
        hipL=(0.18, 0, 0.70), knL=(0.21, -0.04, 0.40), anL=(0.22, 0.0, 0.09)).items()}
    for k in list(J):
        if k.endswith("L"): J[k[:-1] + "R"] = Vector((-J[k].x, J[k].y, J[k].z))
    # torso: big barrel belly + broad chest (purple tunic), yellow sash, gold coin buckle, coin pouch
    sph((0, -0.03, 1.02), 1.0, "purple", "hips", sc=(0.46, 0.40, 0.40), sub=3)
    sph((0, 0.0, 1.26), 1.0, "purple", "spine", sc=(0.48, 0.34, 0.20), sub=3)
    sph((0, -0.18, 1.18), 1.0, "yellow", "spine", sc=(0.20, 0.17, 0.16), sub=2)          # yellow shirt V at the chest
    cyl((0, -0.02, 0.80), (0, -0.02, 0.92), 0.43, 0.45, "yellow", "hips", seg=24)       # sash
    cyl((0, -0.45, 0.86), (0, -0.48, 0.86), 0.085, 0.085, "gold", "hips", seg=18)       # big coin buckle
    cyl((0, -0.48, 0.86), (0, -0.49, 0.86), 0.05, 0.05, "leather", "hips", seg=4)       # square hole (coin style)
    sph((-0.34, -0.22, 0.78), 1.0, "leather", "hips", sc=(0.12, 0.10, 0.13))            # coin pouch
    for i, (dx, dz) in enumerate(((-0.02, 0.10), (0.04, 0.12), (0.0, 0.15))):
        cyl((-0.34 + dx, -0.25, 0.78 + dz), (-0.34 + dx, -0.24, 0.80 + dz), 0.035, 0.035, "gold", "hips", seg=12)
    # hem / skirt of the tunic
    cyl((0, -0.02, 0.80), (0, -0.02, 0.62), 0.44, 0.40, "purple_d", "hips", seg=24, cap=False)
    # legs: short stubby yellow trousers + purple boots
    for s in "LR":
        hp, kn, an = J["hip" + s], J["kn" + s], J["an" + s]
        cyl(hp, kn, 0.16, 0.14, "yellow", "thigh." + s); sph(kn, 0.14, "yellow", "shin." + s)
        cyl(kn, an + Vector((0, 0, 0.08)), 0.135, 0.12, "yellow", "shin." + s)
        cyl(an + Vector((0, 0, 0.16)), an - Vector((0, 0, 0.04)), 0.14, 0.14, "purple_d", "shin." + s)
        sph(an + Vector((0, -0.10, -0.02)), 1.0, "purple_d", "foot." + s, sc=(0.13, 0.20, 0.08))
        cyl(an + Vector((0, 0.0, -0.08)), an + Vector((0, -0.12, -0.08)), 0.13, 0.12, "leather", "foot." + s)
    # arms: yellow sleeves, bare thick forearms, purple fingerless gloves (big fists)
    for s in "LR":
        sh, el, wr, hd = J["sh" + s], J["el" + s], J["wr" + s], J["hd" + s]
        sph(sh, 0.15, "yellow", "upperarm." + s); cyl(sh, el, 0.14, 0.12, "yellow", "upperarm." + s)
        sph(el, 0.115, "skin", "forearm." + s); cyl(el, wr, 0.115, 0.125, "skin", "forearm." + s)
        cyl(wr + (el - wr).normalized() * 0.06, wr - (el - wr).normalized() * 0.03, 0.13, 0.13, "purple", "forearm." + s)
        sph(hd, 0.13, "purple", "hand." + s, sc=(1.0, 1.05, 0.95))
        sph(hd + Vector((0, -0.10, -0.02)), 0.06, "skin", "hand." + s, sc=(1.4, 0.8, 0.8))   # knuckles
    # left shoulder: big riveted iron pauldron (the bash shoulder) + strap
    sL = J["shL"]
    v = sph(sL + Vector((0.04, 0, 0.06)), 1.0, "iron", "upperarm.L", sc=(0.25, 0.25, 0.17), sub=3)
    for vv in v:
        if vv.co.z < sL.z - 0.02: vv.co.z = sL.z - 0.02 + (vv.co.z - sL.z + 0.02) * 0.3
    for a in range(5):
        ang = -0.9 + a * 0.45
        sph(sL + Vector((0.04 + 0.2 * math.cos(ang) * 0.9, 0.2 * math.sin(ang), 0.13)), 0.025, "gold", "upperarm.L", sub=1)
    sph(sL + Vector((0.12, 0, 0.21)), 1.0, "iron", "upperarm.L", sc=(0.05, 0.05, 0.08), sub=1)  # stud
    cyl((0.36, -0.30, 1.38), (-0.36, -0.28, 0.92), 0.03, 0.03, "leather", "spine", seg=6)
    # neck + head: bald, small nose, heavy unibrow, BIG droopy walrus mustache, topknot, gold earring
    cyl(J["chest"], J["neck"] + Vector((0, 0, 0.06)), 0.14, 0.13, "skin", "neck")
    hc = J["headc"]
    sph(hc, 1.0, "skin", "head", sc=(0.17, 0.165, 0.18), sub=3)
    sph(hc + Vector((0, -0.04, -0.10)), 1.0, "skin", "head", sc=(0.15, 0.14, 0.09))          # heavy jaw
    for s in (-1, 1):
        sph(hc + Vector((s * 0.165, 0.0, 0.0)), 1.0, "skin", "head", sc=(0.03, 0.045, 0.055))  # ears
        sph(hc + Vector((s * 0.06, -0.155, 0.035)), 0.026, "white", "head", sub=2)
        sph(hc + Vector((s * 0.06, -0.176, 0.035)), 0.013, "eye", "head", sub=1)
        cyl(hc + Vector((s * 0.0, -0.165, 0.075)), hc + Vector((s * 0.11, -0.15, 0.09)), 0.022, 0.016, "hair", "head", seg=6)
    sph(hc + Vector((0, -0.18, -0.01)), 1.0, "skin", "head", sc=(0.03, 0.03, 0.035))            # small nose
    # walrus mustache: two thick bushy lobes that droop past the chin
    for s in (-1, 1):
        pts = [(0.012, -0.185, -0.045), (0.06, -0.18, -0.06), (0.11, -0.16, -0.09), (0.14, -0.13, -0.14),
               (0.15, -0.11, -0.19), (0.14, -0.10, -0.23)]
        rs = [0.035, 0.045, 0.048, 0.044, 0.036, 0.026]
        for p, r in zip(pts, rs):
            sph(hc + Vector((s * p[0], p[1], p[2])), r, "hair", "head", sc=(1.0, 0.75, 1.1), sub=2)
    sph(hc + Vector((0, -0.05, 0.17)), 1.0, "hair", "head", sc=(0.05, 0.05, 0.04))              # topknot
    cyl(hc + Vector((0, 0.0, 0.18)), hc + Vector((0, 0.13, 0.08)), 0.025, 0.012, "hair", "head", seg=6)
    cyl(hc + Vector((0.175, -0.01, -0.06)), hc + Vector((0.175, 0.01, -0.06)), 0.028, 0.028, "gold", "head", seg=14)
    me = bpy.data.meshes.new(name + "_Mesh"); bm.normal_update(); bm.to_mesh(me); bm.free()
    for k in mats: me.materials.append(M[k])
    me.shade_smooth()
    body = link_ob(bpy.data.objects.new(name + "_Body", me))
    for g in BR_BONES: body.vertex_groups.new(name=g)
    ad = bpy.data.armatures.new(name + "Rig"); arm = link_ob(bpy.data.objects.new(name, ad))
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.selected_objects: o.select_set(False)
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); eb = ad.edit_bones
    def B(n, h, t, p=None):
        b = eb.new(n); b.head = h; b.tail = t
        if p: b.parent = eb[p]
    B("hips", (0, 0, 0.66), (0, 0, 0.92)); B("spine", (0, 0, 0.92), J["chest"], "hips")
    B("neck", J["chest"], J["neck"] + Vector((0, 0, 0.06)), "spine")
    B("head", J["neck"] + Vector((0, 0, 0.06)), hc + Vector((0, 0, 0.2)), "neck")
    for s in "LR":
        B("upperarm." + s, J["sh" + s], J["el" + s], "spine"); B("forearm." + s, J["el" + s], J["wr" + s], "upperarm." + s)
        B("hand." + s, J["wr" + s], J["hd" + s] + Vector((0, 0, -0.08)), "forearm." + s)
        B("thigh." + s, J["hip" + s], J["kn" + s], "hips"); B("shin." + s, J["kn" + s], J["an" + s], "thigh." + s)
        B("foot." + s, J["an" + s], J["an" + s] + Vector((0, -0.18, -0.05)), "shin." + s)
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    body.parent = arm; body.modifiers.new("Armature", 'ARMATURE').object = arm
    return arm, body

BR_DEF = dict({b: (0, 0, 0) for b in BR_BONES}, hips_loc=(0, 0, 0))
def brute_solver(arm, p):
    out = {}
    for b in BR_BONES:
        off = Vector(p["hips_loc"]) if b == "hips" else Vector((0, 0, 0))
        out[b] = basis_from_R(arm, b, rotm(p[b]), off)
    return out, {}

def brute_clips(arm, prefix="brute_"):
    D = BR_DEF; clips = {}
    def mk(n, nf, keys=None, fn=None):
        clips[n] = bake_clip(arm, prefix + n, nf, fn or (lambda f: lerp_pose(keys, f, D)), brute_solver)
    def arms(l=(0, 0, 0), r=(0, 0, 0), fl=(0, 0, 0), fr=(0, 0, 0)):
        return {"upperarm.L": l, "upperarm.R": r, "forearm.L": fl, "forearm.R": fr}
    def idle(f):
        t = f / 48 * 2 * math.pi; p = dict(D)
        p["hips_loc"] = (0, 0, -0.012 * (1 - math.cos(t))); p["spine"] = (-2 * math.sin(t), 0, 0)
        p["head"] = (0, 0, 6 * math.sin(t * 0.5)); p.update(arms((0, 3 * math.sin(t), 0), (0, -3 * math.sin(t), 0),
                                                                (-15 - 5 * math.sin(t), 0, 0), (-15 - 5 * math.sin(t), 0, 0)))
        return p
    mk("idle", 48, fn=idle)
    def walk(f):
        t = f / 24 * 2 * math.pi; p = dict(D); s = math.sin(t); c = math.cos(t)
        p["hips_loc"] = (0, 0, -0.02 + 0.03 * abs(c)); p["hips"] = (0, 6 * s, 4 * s)
        p["thigh.L"] = (-28 * s, 0, 0); p["thigh.R"] = (28 * s, 0, 0)
        p["shin.L"] = (max(0, 35 * c), 0, 0); p["shin.R"] = (max(0, -35 * c), 0, 0)
        p.update(arms((22 * s, 0, 0), (-22 * s, 0, 0), (-20, 0, 0), (-20, 0, 0)))
        p["spine"] = (6, 0, -5 * s); return p
    mk("walk", 24, fn=walk)
    mk("bash", 36, [
        (0, {}), (8, dict(hips_loc=(0, 0.04, -0.10), spine=(18, 0, -38), head=(-10, 0, 30),
                         **arms((0, -15, 25), (25, 0, 10), (-60, 0, 0), (-50, 0, 0)), **{"thigh.L": (-20, 0, 0), "thigh.R": (25, 0, 0),
                         "shin.R": (30, 0, 0)})),
        (12, dict(hips_loc=(0, 0, -0.04), spine=(28, 0, -45), **{"thigh.L": (-40, 0, 0), "thigh.R": (30, 0, 0), "shin.L": (20, 0, 0),
                                                                  "shin.R": (50, 0, 0)})),
        (16, dict(**{"thigh.L": (30, 0, 0), "thigh.R": (-40, 0, 0), "shin.L": (50, 0, 0), "shin.R": (20, 0, 0)})),
        (20, dict(spine=(14, 0, -60), head=(-5, 0, 35), **{"thigh.L": (-35, 0, 0), "thigh.R": (25, 0, 0), "shin.L": (10, 0, 0),
                                                            "shin.R": (30, 0, 0)}, **arms((0, -25, 35), (40, 0, 20), (-70, 0, 0), (-40, 0, 0)))),
        (24, {}), (36, dict(hips_loc=(0, 0, 0), spine=(0, 0, 0), head=(0, 0, 0), **{b: (0, 0, 0) for b in BR_BONES if b not in ("spine", "head")}))])
    mk("hit_react", 20, [
        (0, {}), (3, dict(hips_loc=(0, 0.10, -0.03), spine=(-16, 0, 8), head=(-22, 0, -10), **arms((0, -40, 0), (0, 40, 0), (-30, 0, 0), (-30, 0, 0)))),
        (9, dict(spine=(-8, 0, 4), head=(-10, 0, -4))),
        (20, dict(hips_loc=(0, 0, 0), spine=(0, 0, 0), head=(0, 0, 0), **arms()))])
    def ko(f):
        p = lerp_pose([(0, {}), (5, dict(hips_loc=(0, 0.15, 0.12), hips=(-25, 0, 15), spine=(-20, 0, 0), head=(-25, 0, 20),
                                         **arms((0, -70, 0), (0, 70, 0)), **{"thigh.L": (-30, 0, 0), "thigh.R": (-10, 0, 0)})),
                       (13, dict(hips_loc=(0, 0.45, -0.38), hips=(-88, 0, 25), spine=(-5, 0, 0), head=(-10, 0, 25),
                                 **arms((0, -95, 20), (0, 95, -20), (-20, 0, 0), (-20, 0, 0)),
                                 **{"thigh.L": (-55, 0, 0), "thigh.R": (-35, 0, 0), "shin.L": (40, 0, 0), "shin.R": (20, 0, 0)})),
                       (17, dict(hips_loc=(0, 0.47, -0.30))), (21, dict(hips_loc=(0, 0.48, -0.38))),
                       (40, dict(head=(-10, 0, -20)))], f, D)
        if f > 21:   # dizzy head roll + twitching boots
            p["head"] = (-10 + 6 * math.sin(f * 0.5), 0, 22 * math.sin(f * 0.35))
            p["foot.L"] = (12 * math.sin(f * 0.9), 0, 0)
        return p
    mk("knockout", 40, fn=ko)
    return clips

# ============================================================================= HUD / SFX bookkeeping
HUD = dict(hits=[])          # floating numbers: screen positions are projected through the final camera later
def hud_hit(f, world, roll_id=None, text=None, kind="dmg", target=None):
    HUD["hits"].append(dict(frame=f, world=list(world), id=roll_id, text=text, kind=kind, target=target))

def project_hud(mode, nframes, extra=None):
    from bpy_extras.object_utils import world_to_camera_view
    for h in HUD["hits"]:
        scene.frame_set(h["frame"])
        c = world_to_camera_view(scene, scene.camera, Vector(h["world"]))
        h["x"] = round(c.x, 4); h["y"] = round(1 - c.y, 4)
    d = dict(mode=mode, frames=nframes, fps=FPS, hits=HUD["hits"], events=sorted(EVENTS, key=lambda e: e["frame"]))
    if extra: d.update(extra)
    json.dump(d, open(os.path.join(SEQ, f"hud_{mode}.json"), "w"), indent=1)

def render_frames(mode, f0, f1, samples=6):
    render_setup(int(SOPTS.get("samples", samples)), parse_res((1280, 720)))
    od = os.path.join(SEQ, f"frames_{mode}"); os.makedirs(od, exist_ok=True)
    scene.frame_start = int(SOPTS.get("start", f0)); scene.frame_end = int(SOPTS.get("end", f1))
    scene.render.filepath = os.path.join(od, "f_####")
    t = time.time(); bpy.ops.render.render(animation=True)
    dt = time.time() - t
    print(f"ANIM {mode} {scene.frame_start}-{scene.frame_end} done in {dt:.1f}s")
    with open(os.path.join(SEQ, "render_log.txt"), "a") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {mode} frames {scene.frame_start}-{scene.frame_end} "
                 f"samples={scene.cycles.samples} {dt:.0f}s\n")

def preview(mode, frames, res=(640, 360), samples=8):
    render_setup(int(SOPTS.get("samples", samples)), parse_res(res))
    for f in frames:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(SEQ, "tmp", f"{mode}_{f:04d}.png")
        bpy.ops.render.render(write_still=True)

# ============================================================================= MODE fightwin
# frames 1..265 are the original duel (reused from ../fight/frames); from 266 the duel is re-choreographed.
W_L2_FIRE, W_L2_HIT = 286, 287
W_A4_REL, W_A4_HIT = 308, 310
W_KICK, W_KICK_HIT = 322, 337
W_L3_FIRE, W_L3_HIT = 370, 371
W_A5_REL, W_A5_HIT = 394, 396
W_DEFEAT = 397

def setup_fightwin():
    global ARCHER_STRIPS, PANDA_STRIPS, ARCHER_PATH, PANDA_PATH, LINEAR_SEGS, SHOTS
    ARCHER_STRIPS = [s for s in ARCHER_STRIPS if s[1] <= 236] + [
        ("archer_hit_react", W_L2_HIT, {"bin": 1}),
        ("archer_attack_arrow", W_A4_REL - 8, {}),
        ("archer_hit_react", W_KICK_HIT, {"bin": 1}),
        ("archer_hit_react", W_L3_HIT, {"bin": 1}),
        ("archer_attack_arrow", W_A5_REL - 8, {}),
        ("archer_victory", 405, {"hold": True})]
    PANDA_STRIPS = [s for s in PANDA_STRIPS if s[1] <= 246] + [
        ("panda_attack_lightning", W_L2_FIRE - 18, {}),
        ("panda_hit_react", W_A4_HIT, {"bin": 1}),
        ("panda_spin_kick", W_KICK, {}),
        ("panda_attack_lightning", W_L3_FIRE - 18, {}),
        ("panda_defeat", W_DEFEAT, {"hold": True, "bin": 2})]
    ARCHER_PATH = [k for k in ARCHER_PATH if k[0] <= 266] + [
        (W_L2_HIT, (-0.45, -2.0)), (297, (-0.9, -2.25)), (W_KICK_HIT, (-0.9, -2.25)), (349, (-1.8, -2.65)),
        (W_L3_HIT, (-1.8, -2.65)), (381, (-2.1, -2.75))]
    PANDA_PATH = [k for k in PANDA_PATH if k[0] <= 268] + [
        (296, (1.7, 0.55)), (318, (2.0, 0.65)), (328, (2.0, 0.65)), (W_KICK_HIT, (0.0, -1.15)),
        (344, (0.1, -1.05)), (W_A5_HIT, (0.1, -1.05)), (406, (0.4, -0.85))]
    LINEAR_SEGS = {"panda": {(1, 56), (180, 206), (328, W_KICK_HIT)}, "archer": set()}
    SHOTS = SHOTS[:6] + [
        (266, 299, (108, 100), (9, 9), 30, 0.84, 0.50, (1.0, 1.0)),    # lightning L2 (crushing blow)
        (300, 321, (16, 22), (10, 9), 32, 0.85, 0.45, (1.0, 1.0)),      # over the shoulder: arrow A4
        (322, 350, (80, 92), (5, 6), 26, 0.80, 0.45, (1.0, 1.0)),      # spin kick connects
        (351, 383, (128, 118), (10, 10), 32, 0.84, 0.45, (1.0, 1.0)),  # lightning L3, archer down to 17
        (384, 420, (62, 72), (7, 10), 30, 0.84, 0.45, (1.0, 1.2))]     # final crit arrow, panda slumps

def build_fx_win(parm):
    build_fx(parm)                                             # original FX (arrows 1-3, lightning 1, clash)
    for ob in list(bpy.data.objects):                          # drop the old clash beat (frames 314+)
        if ob.name.startswith(("Arrow4", "Bolt2", "Clash", "Spark_Clash")):
            bpy.data.objects.remove(ob, do_unlink=True)
    EVENTS[:] = [e for e in EVENTS if e["frame"] <= 265]
    # HUD for the reused part
    hud_hit(F_BOLT1_HIT, bone_world(ARCH, "upperarm.L", F_BOLT1_HIT) + Vector((0, 0, 0.35)), "L1", target="archer")
    hud_hit(F_ARROW2_HIT, bone_world(parm, "Bone_lf_clavicle", F_ARROW2_HIT) + Vector((0, 0, 0.45)), "A2", target="panda")
    hud_hit(F_ARROW3_HIT, bone_world(parm, "Bone_spine02", F_ARROW3_HIT) + Vector((0, 0, 0.6)), "A3", target="panda")
    # L2: lightning to the archer's bow shoulder (crushing blow)
    mouth = bone_world(parm, "Bone_jaw02", W_L2_FIRE)
    hit = bone_world(ARCH, "upperarm.L", W_L2_HIT) + Vector((0, 0, 0.05))
    bolt("BoltW2", mouth, hit, W_L2_FIRE, nframes=7, seed=21)
    bolt("BoltW2b", hit, hit + (hit - mouth).normalized() * 1.1 + Vector((0, 0, -0.3)), W_L2_FIRE + 1, nframes=4, seed=22, light_e=0)
    sparks("Spark_W2", hit, W_L2_HIT, n=20, color=(0.6, 0.8, 1.0), speed=3.0, seed=23)
    hud_hit(W_L2_HIT, hit + Vector((0, 0, 0.35)), "L2", target="archer")
    ev(W_L2_FIRE - 14, "whoosh", dur=0.4, gain=0.4, pitch=0.5); ev(W_L2_FIRE, "zap", dur=0.5); ev(W_L2_HIT, "thud", gain=0.9, pitch=0.8)
    ev(W_L2_HIT, "crush")
    # A4: arrow bonks the panda's flank
    tgt = bone_world(parm, "Bone_spine02", W_A4_HIT) + Vector((0, 0, 0.05))
    fly_arrow("ArrowW4", W_A4_REL, W_A4_HIT, tgt, after="bounce", seed=24)
    sparks("Spark_W4", tgt, W_A4_HIT, n=10, color=(1.0, 0.85, 0.5), speed=2.0, seed=25, size=0.022)
    hud_hit(W_A4_HIT, tgt + Vector((0, 0, 0.6)), "A4", target="panda")
    ev(W_A4_REL, "twang"); ev(W_A4_REL, "whoosh", dur=0.25); ev(W_A4_HIT, "bonk")
    # spin kick connects
    ev(W_KICK + 8, "whoosh", dur=0.3, gain=0.6, pitch=0.7); ev(W_KICK + 12, "whoosh", dur=0.45, gain=1.0, pitch=1.2)
    kc = bone_world(ARCH, "spine", W_KICK_HIT) + Vector((0, 0, 0.15))
    sparks("Spark_Kick", kc, W_KICK_HIT, n=16, color=(1.0, 0.9, 0.6), speed=3.0, seed=26)
    flash("KickFlash", kc, W_KICK_HIT, radius=0.6, light_e=2500)
    hud_hit(W_KICK_HIT, kc + Vector((0, 0, 0.6)), "K", target="archer")
    ev(W_KICK_HIT, "punch"); ev(W_KICK + 22, "thud", gain=1.0, pitch=0.55)
    # L3
    mouth = bone_world(parm, "Bone_jaw02", W_L3_FIRE)
    hit = bone_world(ARCH, "spine", W_L3_HIT) + Vector((0, 0, 0.25))
    bolt("BoltW3", mouth, hit, W_L3_FIRE, nframes=7, seed=27)
    sparks("Spark_W3", hit, W_L3_HIT, n=18, color=(0.6, 0.8, 1.0), speed=2.8, seed=28)
    hud_hit(W_L3_HIT, hit + Vector((0, 0, 0.45)), "L3", target="archer")
    ev(W_L3_FIRE - 14, "whoosh", dur=0.4, gain=0.4, pitch=0.5); ev(W_L3_FIRE, "zap", dur=0.5); ev(W_L3_HIT, "thud", gain=0.8, pitch=0.9)
    # A5: the deciding crit
    tgt = bone_world(parm, "Bone_skull", W_A5_HIT) + Vector((0, 0, 0.05))
    fly_arrow("ArrowW5", W_A5_REL, W_A5_HIT, tgt, after="bounce", seed=29)
    flash("CritFlash", tgt, W_A5_HIT, radius=0.9, color=(1.0, 0.8, 0.35), light_e=5000)
    sparks("Spark_W5", tgt, W_A5_HIT, n=22, color=(1.0, 0.75, 0.3), speed=3.5, seed=30, life=12)
    hud_hit(W_A5_HIT, tgt + Vector((0, 0, 0.55)), "A5", target="panda")
    ev(W_A5_REL, "twang"); ev(W_A5_REL, "whoosh", dur=0.25); ev(W_A5_HIT, "bonk"); ev(W_A5_HIT, "crit")
    ev(W_DEFEAT + 8, "thud", gain=0.9, pitch=0.5); ev(W_DEFEAT + 14, "whoosh", dur=0.6, gain=0.3, pitch=0.4)
    ev(410, "chime")

def build_fightwin():
    scene.frame_start = 1; scene.frame_end = FRAME_END; scene.render.fps = FPS
    setup_fightwin()
    parm, pbody, _ = build_panda()
    upgrade_archer(); archer_clips(ARCH); panda_clips(parm)
    layout_nla(parm, panda_stride(parm))
    POS = key_motion(parm)
    build_fx_win(parm)
    boxes = eval_boxes()
    cam, CAMS = build_camera(boxes)
    thin_grass_near_camera(CAMS)
    end = POS[FRAME_END]
    project_hud("fightwin", FRAME_END, dict(
        archer_end=list(end[0]), panda_end=list(end[1]), archer_yaw=ARCH.rotation_euler.z))
    return parm, boxes, POS

# ============================================================================= shared: ocarina-rig shots
def emis(name, col, strength):
    return bpy.data.materials.get(name) or emission_mat(name, col, strength)

def ghost_material(name="M_PandaGhost", alpha=0.38, strength=3.0):
    """translucent emissive spirit look, keeps the panda's fur pattern as brighter/darker glow."""
    m = bpy.data.materials.get(name)
    if m: return m
    src = bpy.data.materials["M_Panda"]
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tx = N.new("ShaderNodeTexImage"); tx.image = src.node_tree.nodes["Image Texture"].image
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.10, 0.45, 1.0, 1); ramp.color_ramp.elements[1].color = (0.75, 1.0, 1.0, 1)
    L.new(tx.outputs[0], ramp.inputs[0])
    L.new(ramp.outputs[0], b.inputs["Emission Color"]); L.new(ramp.outputs[0], b.inputs["Base Color"])
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Roughness"].default_value = 0.4
    # rim boost: more opaque/brighter at grazing angles (classic ghost look)
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.35
    mx = N.new("ShaderNodeMath"); mx.operation = 'MULTIPLY_ADD'
    mx.inputs[1].default_value = 0.55; mx.inputs[2].default_value = alpha
    L.new(lw.outputs["Facing"], mx.inputs[0])
    av = N.new("ShaderNodeValue"); av.name = "ghost_alpha"; av.outputs[0].default_value = 1.0
    mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    L.new(mx.outputs[0], mul.inputs[0]); L.new(av.outputs[0], mul.inputs[1]); L.new(mul.outputs[0], b.inputs["Alpha"])
    m.blend_method = 'BLEND' if hasattr(m, "blend_method") else None
    m["export_color"] = (0.45, 0.85, 1.0)
    return m

def key_value_node(m, node_name, keys):
    n = m.node_tree.nodes[node_name]
    for f, v in keys:
        n.outputs[0].default_value = v; n.outputs[0].keyframe_insert("default_value", frame=f)

def look_cam(name, keys, lens_keys=None):
    """keys: [(frame, loc, target)] smooth Bezier camera (+ optional [(frame, lens)])."""
    cd = bpy.data.cameras.new(name); cd.clip_end = 400; cd.clip_start = 0.05; cd.sensor_width = 36
    cam = link_ob(bpy.data.objects.new(name, cd))
    tg = link_ob(bpy.data.objects.new(name + "_Tgt", None))
    tc = cam.constraints.new('TRACK_TO'); tc.target = tg; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    for f, lp, tp in keys:
        cam.location = lp; cam.keyframe_insert("location", frame=f)
        tg.location = tp; tg.keyframe_insert("location", frame=f)
    for f, l in (lens_keys or [(1, 35)]):
        cd.lens = l; cd.keyframe_insert("lens", frame=f)
    for ob in (cam, tg, cd):
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
    scene.camera = cam
    return cam

def ctrl_keys(ns, keys):
    """re-key the ocarina control: keys = [(frame, t)] with t=0 lowered (belt/chest), 1 = at the mouth."""
    ctrl = ns["ctrl"]; lo = ns["basis_low"]; pl = ns["basis_play"]
    ctrl.animation_data.action.fcurves.clear() if ctrl.animation_data and ctrl.animation_data.action else None
    l0, q0, _ = lo.decompose(); l1, q1, _ = pl.decompose()
    ctrl.rotation_mode = 'QUATERNION'
    for f, t in keys:
        ctrl.location = l0.lerp(l1, t); ctrl.rotation_quaternion = q0.slerp(q1, t)
        ctrl.keyframe_insert("location", frame=f); ctrl.keyframe_insert("rotation_quaternion", frame=f)
    for fc in ctrl.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'; kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'

def strip_finger_keys(ns, after=None):
    act = ns["arm"].animation_data.action
    for fc in list(act.fcurves):
        if '"f_' in fc.data_path:
            if after is None:
                act.fcurves.remove(fc)
            else:
                for i in reversed(range(len(fc.keyframe_points))):
                    if fc.keyframe_points[i].co[0] > after: fc.keyframe_points.remove(fc.keyframe_points[i])
                fc.keyframe_points.insert(after + 5, 0.0)      # fingers relax onto the holes

def ocarina_glow(ns, keys, light_keys=None):
    """animate the glaze emission (blue glow) of M_OcarinaGlaze + a small point light at the ocarina."""
    g = bpy.data.materials["M_OcarinaGlaze"]; P = g.node_tree.nodes["Principled BSDF"]
    P.inputs["Emission Color"].default_value = (0.35, 0.75, 1.0, 1)
    for f, e in keys:
        P.inputs["Emission Strength"].default_value = e
        P.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
    ld = bpy.data.lights.new("OcarinaGlow", 'POINT'); ld.color = (0.45, 0.8, 1.0); ld.shadow_soft_size = 0.05
    lo = link_ob(bpy.data.objects.new("OcarinaGlow", ld)); lo.parent = ns["oc"]
    for f, e in (light_keys or [(f, e * 6) for f, e in keys]):
        ld.energy = e; ld.keyframe_insert("energy", frame=f)
    return lo

def spirit_stream(name, src_pts, dest_fn, f0, f1, n=48, seed=0, color=(0.55, 0.95, 1.0), swirl_r=0.9, turns=1.6):
    """glowing motes rise off the panda and spiral into dest_fn(frame) (the ocarina), + 3 ribbon trails."""
    rnd = random.Random(seed)
    mm = emis(name + "_M", color, 18.0)
    mt = emis(name + "_MT", (0.35, 0.85, 1.0), 8.0)
    for i in range(n):
        p0 = src_pts[rnd.randrange(len(src_pts))].copy()
        st = f0 + rnd.uniform(0, (f1 - f0) * 0.45); dur = rnd.uniform(0.45, 0.6) * (f1 - f0)
        en = min(f1, st + dur); ph = rnd.uniform(0, 2 * math.pi); rr = swirl_r * rnd.uniform(0.6, 1.2)
        rise = rnd.uniform(0.5, 1.1); sz = rnd.uniform(0.018, 0.04)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=sz)
        ob = mesh_from_bm(f"{name}_{i}", bm, [mm]); ob.visible_shadow = False
        fs = list(range(int(st), int(en) + 1))
        for f in fs:
            k = (f - st) / (en - st); k = max(0.0, min(1.0, k))
            d = dest_fn(f)
            base = p0.lerp(d, smooth(k)) + Vector((0, 0, rise * math.sin(math.pi * min(1, k * 1.15))))
            ang = ph + turns * 2 * math.pi * k; r = rr * math.sin(math.pi * k) * (1 - 0.3 * k)
            ax = (d - p0); ax.z = 0; ax = ax.normalized() if ax.length > 1e-4 else Vector((1, 0, 0))
            side = Vector((-ax.y, ax.x, 0)); up = Vector((0, 0, 1))
            ob.location = base + side * (r * math.cos(ang)) + up * (r * 0.6 * math.sin(ang))
            s = (0.3 + 0.7 * math.sin(math.pi * min(1, k * 1.6))) * (1 - 0.85 * max(0, k - 0.85) / 0.15)
            ob.scale = (s, s, s)
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("scale", frame=f)
        key_vis(ob, [(int(st), int(en))])
    # ribbons: curves along the same kind of spiral, a moving visible window (bevel_factor start/end)
    for j in range(3):
        p0 = src_pts[rnd.randrange(len(src_pts))].copy(); ph = j * 2.1
        fr_ref = int(f0 + (f1 - f0) * 0.7); d = dest_fn(fr_ref)
        cu = bpy.data.curves.new(f"{name}_Rib{j}", 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = 0.008; cu.bevel_resolution = 2
        sp = cu.splines.new('POLY'); K = 60; sp.points.add(K - 1)
        ax = (d - p0); ax.z = 0; ax = ax.normalized(); side = Vector((-ax.y, ax.x, 0))
        for i in range(K):
            k = i / (K - 1)
            base = p0.lerp(d, smooth(k)) + Vector((0, 0, 0.8 * math.sin(math.pi * min(1, k * 1.15))))
            ang = ph + turns * 2 * math.pi * k; r = swirl_r * math.sin(math.pi * k) * (1 - 0.3 * k)
            q = base + side * (r * math.cos(ang)) + Vector((0, 0, r * 0.6 * math.sin(ang)))
            sp.points[i].co = (*q, 1); sp.points[i].radius = 0.4 + 1.2 * math.sin(math.pi * k)
        cu.materials.append(mt)
        ob = link_ob(bpy.data.objects.new(f"{name}_Rib{j}", cu)); ob.visible_shadow = False
        a = int(f0 + 8 + j * 6); b_ = int(f1 - 4 + j * 2)
        for f, s0, s1 in ((a, 0.0, 0.0), (a + (b_ - a) * 0.5, 0.15, 0.6), (b_, 0.995, 1.0)):
            cu.bevel_factor_start = s0; cu.bevel_factor_end = s1
            cu.keyframe_insert("bevel_factor_start", frame=int(f)); cu.keyframe_insert("bevel_factor_end", frame=int(f))
        key_vis(ob, [(a, b_)])
    # moving light inside the stream
    ld = bpy.data.lights.new(name + "_L", 'POINT'); ld.color = color; ld.shadow_soft_size = 0.3
    lo = link_ob(bpy.data.objects.new(name + "_L", ld))
    c0 = sum(src_pts, Vector()) / len(src_pts)
    for f in range(int(f0), int(f1) + 1, 3):
        k = (f - f0) / (f1 - f0); lo.location = c0.lerp(dest_fn(f), smooth(k)) + Vector((0, 0, 0.5 * math.sin(math.pi * k)))
        ld.energy = 120 * math.sin(math.pi * k) + 10
        lo.keyframe_insert("location", frame=f); ld.keyframe_insert("energy", frame=f)

def mesh_points(ob, n=200, seed=0, frame=None):
    if frame: scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get(); e = ob.evaluated_get(dg); me = e.to_mesh()
    rnd = random.Random(seed); vs = me.vertices
    pts = [e.matrix_world @ vs[rnd.randrange(len(vs))].co for _ in range(n)]
    e.to_mesh_clear(); return pts

# ============================================================================= MODE capture
CAP_N = 120
def build_capture():
    d = json.load(open(os.path.join(SEQ, "hud_fightwin.json")))
    pa = Vector(d["archer_end"]); pp = Vector(d["panda_end"])
    th = math.atan2(pp.y - pa.y, pp.x - pa.x)
    ARCH.location = pa; ARCH.rotation_euler = (0, 0, th + math.radians(55))   # ocarina rig faces Rh@X (-55 deg)
    bpy.context.view_layer.update()
    ns = load_ocarina_rig()
    scene.frame_start = 1; scene.frame_end = CAP_N; scene.render.fps = FPS
    strip_finger_keys(ns)
    ctrl_keys(ns, [(1, 0.0), (14, 0.0), (34, 0.55), (CAP_N, 0.6)])     # hold the ocarina up toward the spirit
    # panda: defeat pose held, slumps a little further, fades out 30..88
    parm, pbody, _ = build_panda(); panda_clips(parm)
    ad = parm.animation_data_create(); ad.action = None
    s = add_strip(parm, bpy.data.actions["panda_defeat"], -40, hold=True, bin=0); s.extrapolation = 'HOLD'
    parm.location = pp; parm.rotation_euler = (0, 0, math.atan2(-(pa.x - pp.x), pa.y - pp.y))
    parm.keyframe_insert("location", frame=1); parm.keyframe_insert("location", frame=26)
    parm.location = pp + Vector((0, 0, -0.10)); parm.keyframe_insert("location", frame=70)
    m = bpy.data.materials["M_Panda"]; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (0.25, 0.7, 1.0, 1)
    for f, al, em in ((1, 1.0, 0.0), (24, 1.0, 0.0), (40, 0.8, 0.35), (62, 0.35, 0.6), (86, 0.0, 0.3)):
        b.inputs["Alpha"].default_value = al; b.inputs["Alpha"].keyframe_insert("default_value", frame=f)
        b.inputs["Emission Strength"].default_value = em; b.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
    key_vis(pbody, [(1, 88)])
    scene.frame_set(30)
    src = mesh_points(pbody, 300, seed=4, frame=30)
    oc = ns["oc"]
    OCP = {}
    for f in range(1, CAP_N + 1):
        scene.frame_set(f); OCP[f] = oc.matrix_world.translation.copy()
    spirit_stream("Spirit", src, lambda f: OCP[max(1, min(CAP_N, f))], 28, 96, n=56, seed=11)
    ocarina_glow(ns, [(1, 0.0), (60, 0.0), (80, 4.0), (98, 16.0), (108, 6.0), (CAP_N, 4.0)])
    sparks("Spark_Absorb", OCP[97], 97, n=18, color=(0.6, 0.95, 1.0), speed=1.6, life=12, seed=12, size=0.015)
    hud_hit(100, OCP[100] + Vector((0, 0, 0.45)), None, text="+40 HP  SPIRIT BOND", kind="heal", target="archer")
    ev(20, "whoosh", dur=0.8, gain=0.25, pitch=0.4); ev(28, "shimmer", dur=2.8); ev(97, "chime"); ev(100, "heal")
    # camera: side-on two-shot, then push in on the glowing ocarina
    mid = pa.lerp(pp, 0.5); line = (pp - pa); line.z = 0; line.normalize()
    perp = Vector((-line.y, line.x, 0))
    yaw_last = AXIS_YAW + math.radians(72); cdir = Vector((math.cos(yaw_last), math.sin(yaw_last), 0))
    if perp.dot(cdir) > 0: perp = -perp            # same side as the last fight shot
    z0 = ground(mid.x, mid.y)
    ocw = OCP[100]
    look_cam("Cam_Capture", [
        (1, mid + perp * 5.2 + Vector((0, 0, 1.2)) - line * 0.3, mid + Vector((0, 0, 0.75))),
        (40, mid + perp * 4.6 + Vector((0, 0, 1.35)) - line * 0.4, mid + Vector((0, 0, 0.9)) - line * 0.2),
        (CAP_N, ocw + perp * 2.1 + line * 1.1 + Vector((0, 0, 0.0)), ocw + Vector((0, 0, -0.05)))],
        [(1, 30), (60, 32), (CAP_N, 36)])
    project_hud("capture", CAP_N)
    return ns

# ============================================================================= MODE brute (travel + Grubbo fight)
BR_N = 264
BR_STOP = Vector((0.72, 12.6))           # archer stops here on the path (world xy); the brute waits up the path
BR_HOME = Vector((1.2, 16.0))
B_A6_REL, B_A6_HIT = 118, 121
B_BASH1, B_BASH1_HIT = 140, 160
B_A7_REL, B_A7_HIT = 194, 196
B_BASH2, B_BASH2_HIT = 212, 232

def uv_of(xy):
    r = Vector(xy) - A0; return (r.dot(U), r.dot(V))

def layout_generic(ob, base, strips, nframes):
    ad = ob.animation_data_create(); ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    b = add_strip(ob, bpy.data.actions[base], 1, repeat=math.ceil(nframes / 48) + 2, bin=0, bout=0); b.extrapolation = 'HOLD'
    for name, start, kw in strips:
        add_strip(ob, bpy.data.actions[name], start, **kw)

def path_uv(path, f, linear=()):
    for (f0, a), (f1, b) in zip(path, path[1:]):
        if f0 <= f <= f1:
            k = (f - f0) / (f1 - f0) if f1 > f0 else 1
            if (f0, f1) not in linear: k = smooth(k)
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    return path[-1][1] if f > path[-1][0] else path[0][1]

def key_motion_pair(A, Bo, apath, bpath, nframes, alin=(), blin=(), a_face=None, b_face=None):
    """a_face(f, pa, pb) / b_face(...) may return a yaw override (radians) else they face each other."""
    for ob in (A, Bo):
        a = new_action(ob.name + "_motion2"); ob.animation_data.action = a
    POS = {}
    for f in range(1, nframes + 1):
        pa = fw(*path_uv(apath, f, alin)); pb = fw(*path_uv(bpath, f, blin))
        d = pb - pa
        ya = math.atan2(d.y, d.x); yb = math.atan2(-d.x, d.y)
        if a_face: ya = a_face(f, pa, pb, ya)
        if b_face: yb = b_face(f, pa, pb, yb)
        A.location = (pa.x, pa.y, pa.z - 0.02); A.rotation_euler = (0, 0, ya)
        Bo.location = pb; Bo.rotation_euler = (0, 0, yb)
        for ob in (A, Bo):
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
        POS[f] = (pa.copy(), pb.copy())
    for ob in (A, Bo):
        fc = ob.animation_data.action.fcurves.find("rotation_euler", index=2); prev = None
        for kp in fc.keyframe_points:
            if prev is not None:
                while kp.co[1] - prev > math.pi: kp.co[1] -= 2 * math.pi
                while kp.co[1] - prev < -math.pi: kp.co[1] += 2 * math.pi
            prev = kp.co[1]
        finish_action(ob.animation_data.action)
    return POS

def eval_boxes_pair(nameA, nameB, nframes, solo=()):
    dg = bpy.context.evaluated_depsgraph_get(); out = {}
    for f in range(1, nframes + 1):
        scene.frame_set(f); res = []
        for nm in (nameA, nameB):
            ob = bpy.data.objects[nm].evaluated_get(dg)
            res.append([ob.matrix_world @ Vector(c) for c in ob.bound_box])
        if any(a <= f <= b for a, b in solo): res[1] = res[0]
        out[f] = res
    return out

def belt_ocarina(glow=2.0):
    """small glowing ocarina hanging at the archer's belt (continuity after the spirit capture)."""
    m = bpy.data.materials.new("M_BeltOcarina"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.08, 0.30, 0.85, 1); b.inputs["Roughness"].default_value = 0.25
    b.inputs["Emission Color"].default_value = (0.35, 0.75, 1.0, 1); b.inputs["Emission Strength"].default_value = glow
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0,
                                                matrix=Matrix.Diagonal((0.065, 0.04, 0.036, 1)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.016, radius2=0.012, depth=0.05,
                          matrix=Matrix.Translation((-0.075, 0, 0.0)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    ob = mesh_from_bm("BeltOcarina", bm, [m])
    cord = bpy.data.curves.new("BeltCord", 'CURVE'); cord.dimensions = '3D'; cord.bevel_depth = 0.004
    sp = cord.splines.new('POLY'); sp.points.add(1); sp.points[0].co = (0, 0, 0.03, 1); sp.points[1].co = (0, 0, 0.12, 1)
    co = link_ob(bpy.data.objects.new("BeltCord", cord)); co.parent = ob
    cord.materials.append(bpy.data.materials.get("M_BruteLeather") or m)
    scene.frame_set(1)
    ob.parent = ARCH; ob.parent_type = 'BONE'; ob.parent_bone = "hips"
    ob.matrix_world = ARCH.matrix_world @ Matrix.Translation((0.20, -0.06, 0.86)) @ Matrix.Rotation(math.radians(80), 4, 'Y')
    return ob

def build_brute_shot():
    global FRAME_END, SHOTS
    FRAME_END = BR_N
    set_axis(BR_STOP, BR_HOME - BR_STOP)
    scene.frame_start = 1; scene.frame_end = BR_N; scene.render.fps = FPS
    upgrade_archer(); archer_clips(ARCH)
    barm, bbody = build_brute(); brute_clips(barm)
    s0 = uv_of((1.55, 8.9)); home = uv_of(BR_HOME); start_b = (home[0] + 1.7, home[1] - 0.25)
    layout_generic(ARCH, "archer_idle", [
        ("archer_walk", 1, {"repeat": 3.0, "bin": 0, "bout": 6}),
        ("archer_attack_arrow", B_A6_REL - 8, {}),
        ("archer_hit_react", B_BASH1_HIT, {"bin": 1}),
        ("archer_attack_arrow", B_A7_REL - 8, {}),
        ("archer_dodge", B_BASH2_HIT - 9, {})], BR_N)
    layout_generic(barm, "brute_idle", [
        ("brute_walk", 72, {"repeat": 1.25, "bin": 2, "bout": 5}),
        ("brute_hit_react", B_A6_HIT, {"bin": 1}),
        ("brute_bash", B_BASH1, {}),
        ("brute_hit_react", B_A7_HIT, {"bin": 1}),
        ("brute_bash", B_BASH2, {}),
        ("brute_hit_react", B_BASH2_HIT + 6, {"bin": 2})], BR_N)
    apath = [(1, s0), (72, (0.0, 0.0)), (B_BASH1_HIT, (0.0, 0.0)), (B_BASH1_HIT + 10, (-1.25, -0.05)),
             (B_BASH2_HIT - 9, (-1.25, -0.05)), (B_BASH2_HIT + 1, (-1.35, -1.3))]
    bpath = [(1, start_b), (72, start_b), (102, home), (B_A6_HIT, home), (B_A6_HIT + 6, (home[0] + 0.2, home[1])),
             (B_BASH1 + 10, (home[0] + 0.2, home[1])), (B_BASH1_HIT, (1.0, 0.0)), (B_BASH1_HIT + 10, (0.6, 0.0)),
             (B_A7_HIT, (0.6, 0.0)), (B_A7_HIT + 6, (0.85, 0.0)), (B_BASH2 + 10, (0.85, 0.0)),
             (B_BASH2_HIT, (-1.6, -0.05)), (B_BASH2_HIT + 12, (-2.6, -0.15))]
    blin = {(B_BASH1 + 10, B_BASH1_HIT), (B_BASH2 + 10, B_BASH2_HIT)}
    travel_yaw = math.atan2(*(fw(0, 0) - fw(*s0)).yx)
    # the archer's walk clip walks along the archer's local -Y (rest-pose front); his fight facing is local +X
    def a_face(f, pa, pb, y, ty=travel_yaw):
        walk_y = ty + math.radians(90)            # local -Y -> travel direction
        if f <= 64: return walk_y
        if f <= 84:
            k = smooth((f - 64) / 20); dy = (y - walk_y + math.pi) % (2 * math.pi) - math.pi
            return walk_y + dy * k
        return y
    lock = {}
    def b_face(f, pa, pb, y):
        if f <= 101:
            dvec = fw(*home) - fw(*start_b); return math.atan2(-(-dvec.x), -dvec.y)  # face walking dir
        if B_BASH2 + 10 <= f <= B_BASH2_HIT + 16:                      # committed charge: no turning
            lock.setdefault("y", y); return lock["y"]
        if B_BASH2_HIT + 16 < f <= B_BASH2_HIT + 30:
            k = smooth((f - B_BASH2_HIT - 16) / 14); y0 = lock["y"]; dy = (y - y0 + math.pi) % (2 * math.pi) - math.pi
            return y0 + dy * k
        return y
    POS = key_motion_pair(ARCH, barm, apath, bpath, BR_N, blin=blin, a_face=a_face, b_face=b_face)
    key_vis(bbody, [(73, BR_N)])
    belt_ocarina()
    # ---- FX + events + HUD
    for f in range(4, 72, 12): ev(f, "step", gain=0.35)
    for f in range(76, 102, 12): ev(f, "step", gain=0.7, pitch=0.6)
    ev(104, "greed")                                                       # "Hrrm... shiny!" (grunt synth)
    t6 = bone_world(barm, "spine", B_A6_HIT) + Vector((0, 0, 0.15))
    fly_arrow("ArrowB6", B_A6_REL, B_A6_HIT, t6, after="bounce", seed=41)
    sparks("Spark_B6", t6, B_A6_HIT, n=10, color=(1.0, 0.85, 0.5), speed=2.0, seed=42, size=0.022)
    hud_hit(B_A6_HIT, t6 + Vector((0, 0, 0.75)), "A6", target="brute")
    ev(B_A6_REL, "twang"); ev(B_A6_REL, "whoosh", dur=0.25); ev(B_A6_HIT, "bonk")
    for f in (B_BASH1 + 4, B_BASH1 + 12, B_BASH1 + 16): ev(f, "step", gain=0.9, pitch=0.5)
    ev(B_BASH1 + 9, "whoosh", dur=0.4, gain=0.8, pitch=0.5)
    hb = bone_world(ARCH, "spine", B_BASH1_HIT) + Vector((0, 0, 0.2))
    flash("BashFlash", hb, B_BASH1_HIT, radius=0.8, light_e=3000)
    sparks("Spark_Bash", hb, B_BASH1_HIT, n=20, color=(1.0, 0.9, 0.6), speed=3.2, seed=43)
    hud_hit(B_BASH1_HIT, hb + Vector((0, 0, 0.55)), "BASH1", target="archer")
    ev(B_BASH1_HIT, "bash"); ev(B_BASH1_HIT, "crush"); ev(B_BASH1_HIT + 10, "thud", gain=0.7, pitch=0.7)
    t7 = bone_world(barm, "head", B_A7_HIT) + Vector((0, 0, 0.1))
    fly_arrow("ArrowB7", B_A7_REL, B_A7_HIT, t7, after="bounce", seed=44)
    flash("CritFlashB", t7, B_A7_HIT, radius=0.7, color=(1.0, 0.8, 0.35), light_e=4000)
    sparks("Spark_B7", t7, B_A7_HIT, n=18, color=(1.0, 0.75, 0.3), speed=3.0, seed=45)
    hud_hit(B_A7_HIT, t7 + Vector((0, 0, 0.5)), "A7", target="brute")
    ev(B_A7_REL, "twang"); ev(B_A7_REL, "whoosh", dur=0.25); ev(B_A7_HIT, "bonk"); ev(B_A7_HIT, "crit")
    for f in (B_BASH2 + 4, B_BASH2 + 12, B_BASH2 + 16): ev(f, "step", gain=0.9, pitch=0.5)
    ev(B_BASH2 + 9, "whoosh", dur=0.5, gain=0.9, pitch=0.45); ev(B_BASH2_HIT - 8, "whoosh", dur=0.3, gain=0.5, pitch=1.4)
    hud_hit(B_BASH2_HIT - 2, bone_world(ARCH, "head", B_BASH2_HIT - 2) + Vector((0, 0, 0.45)), None, text="DODGE!",
            kind="miss", target="archer")
    ev(B_BASH2_HIT + 8, "thud", gain=0.9, pitch=0.5); ev(B_BASH2_HIT + 14, "step", gain=0.7, pitch=0.5)
    # ---- camera
    SHOTS = [(1, 72, (200, 185), (8, 7), 35, 0.80, 0.5, (1.9, 1.5)),        # travel: walking toward camera
             (73, 108, (22, 28), (8, 7), 32, 0.84, 0.62, (1.0, 1.0)),      # over the shoulder: Grubbo strolls in
             (109, 135, (96, 100), (6, 6), 30, 0.84, 0.50, (1.0, 1.0)),    # arrow A6
             (136, 175, (70, 80), (5, 5), 26, 0.80, 0.45, (1.0, 1.0)),     # shoulder bash (crushing blow)
             (176, 205, (128, 120), (9, 9), 32, 0.84, 0.45, (1.0, 1.0)),   # arrow A7 crit
             (206, 264, (100, 92), (10, 11), 26, 0.82, 0.50, (1.05, 1.1))]   # bash 2 dodged
    boxes = eval_boxes_pair("Archer_Body", "Grubbo_Body", BR_N, solo=[(1, 72)])
    cam, CAMS = build_camera(boxes)
    thin_grass_near_camera(CAMS)
    project_hud("brute", BR_N, dict(card=dict(text="GRUBBO THE GREEDY", sub="loves gold, hates sharing", f0=86, f1=134),
                                    archer_end=list(POS[BR_N][0]), brute_end=list(POS[BR_N][1])))
    return barm, boxes

# ============================================================================= MODE summon (ocarina -> ghost panda -> KO)
SUM_N = 240
S_PLAY_END = 170
S_FIRE = 152; S_BOLTS = (152, 157, 162)
S_KO = 162

def shot_cam(name, shots):
    """hard cuts between shots; inside a shot location/target/lens ease from start to end values."""
    cd = bpy.data.cameras.new(name); cd.clip_end = 400; cd.clip_start = 0.05; cd.sensor_width = 36
    cam = link_ob(bpy.data.objects.new(name, cd)); cam.rotation_mode = 'QUATERNION'
    prev = None
    for f0, f1, l0, t0, l1, t1, n0, n1 in shots:
        for f in range(f0, f1 + 1):
            k = smooth((f - f0) / max(1, f1 - f0))
            loc = l0.lerp(l1, k); tg = t0.lerp(t1, k)
            loc.z = max(loc.z, ground(loc.x, loc.y) + 0.35)
            q = (tg - loc).to_track_quat('-Z', 'Y')
            if prev is not None and prev.dot(q) < 0: q = -q
            prev = q
            cam.location = loc; cam.rotation_quaternion = q; cd.lens = n0 + (n1 - n0) * k
            cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f)
            cd.keyframe_insert("lens", frame=f)
    for a in (cam.animation_data.action, cd.animation_data.action):
        for fc in a.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    scene.camera = cam
    return cam

def star_mesh(name, r1=0.11, r2=0.045, depth=0.03, mat_=None):
    bm = bmesh.new(); vs = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5; r = r1 if i % 2 == 0 else r2
        vs.append(bm.verts.new((r * math.cos(a), 0, r * math.sin(a))))
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.y += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_from_bm(name, bm, [mat_])

def dizzy_stars(arm, f0, f1, n=5, seed=0):
    mm = emis("M_Stars", (1.0, 0.72, 0.08), 3.0)
    for i in range(n):
        ob = star_mesh(f"Star_{i}", mat_=mm); ob.visible_shadow = False
        for f in range(f0, f1 + 1, 2):
            h = bone_world(arm, "head", f, tail=True)
            a = 2 * math.pi * (i / n) + (f - f0) * 0.22
            ob.location = h + Vector((0.38 * math.cos(a), 0.38 * math.sin(a), 0.12 + 0.05 * math.sin(a * 2)))
            ob.rotation_euler = (0, (f - f0) * 0.3 + i, a + math.pi / 2)
            s = min(1.0, (f - f0) / 8); ob.scale = (s, s, s)
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
            ob.keyframe_insert("scale", frame=f)
        key_vis(ob, [(f0, f1)])

def build_summon():
    global FRAME_END
    FRAME_END = SUM_N
    d = json.load(open(os.path.join(SEQ, "hud_brute.json"))) if os.path.exists(os.path.join(SEQ, "hud_brute.json")) else None
    set_axis(BR_STOP, BR_HOME - BR_STOP)
    P = lambda u, v, z=0.0: fw(u, v) + Vector((0, 0, z))
    pa = fw(0, 0); pb_end = fw(4.6, 0.0)
    th = math.atan2(pb_end.y - pa.y, pb_end.x - pa.x)
    ARCH.location = (pa.x, pa.y, pa.z - 0.02); ARCH.rotation_euler = (0, 0, th + math.radians(55))
    bpy.context.view_layer.update()
    ns = load_ocarina_rig()
    scene.frame_start = 1; scene.frame_end = SUM_N; scene.render.fps = FPS
    strip_finger_keys(ns, after=S_PLAY_END - 2)
    ctrl_keys(ns, [(1, 0.15), (8, 0.15), (30, 1.0), (S_PLAY_END - 2, 1.0), (S_PLAY_END + 16, 0.2), (SUM_N, 0.2)])
    oc = ns["oc"]
    ocarina_glow(ns, [(1, 4.0), (40, 5.0), (60, 14.0), (95, 14.0), (110, 5.0), (S_PLAY_END, 5.0), (SUM_N, 3.0)])
    # ---- brute: walks up, freezes at the music, takes the triple lightning, KO
    barm, bbody = build_brute(); brute_clips(barm)
    layout_generic(barm, "brute_idle", [("brute_walk", 1, {"repeat": 1.7, "bin": 0, "bout": 6}),
                                        ("brute_hit_react", S_BOLTS[0], {"bin": 1}),
                                        ("brute_hit_react", S_BOLTS[1], {"bin": 1}),
                                        ("brute_knockout", S_KO, {"hold": True, "bin": 1})], SUM_N)
    # ---- ghost panda (the same rigged panda, spirit material)
    parm, pbody, _ = build_panda(); panda_clips(parm)
    gm = ghost_material(); pbody.data.materials[0] = gm
    v_nat = panda_stride(parm)
    rate = min(2.8, (2.6 / (28 / FPS)) / v_nat)
    layout_generic(parm, "panda_idle", [
        ("panda_walk", 104, {"scale": 1 / rate, "repeat": max(1.0, 30 / (48 / rate)), "bin": 2, "bout": 4}),
        ("panda_attack_lightning", S_FIRE - 18, {}),
        ("panda_victory", 186, {"hold": True})], SUM_N)
    key_value_node(gm, "ghost_alpha", [(1, 0.0), (70, 0.0), (100, 1.0), (205, 1.0), (236, 0.0)])
    b = gm.node_tree.nodes["Principled BSDF"]
    for f, e in ((70, 8.0), (100, 3.0), (S_FIRE, 3.0), (S_FIRE + 2, 6.0), (S_KO + 4, 3.0)):
        b.inputs["Emission Strength"].default_value = e; b.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
    key_vis(pbody, [(70, 237)])
    ppath = [(1, (0.9, 1.7)), (104, (0.9, 1.7)), (134, (1.75, 0.3))]
    bpath = [(1, (5.9, 0.35)), (40, (4.6, 0.0))]
    for ob in (parm, barm):
        a = new_action(ob.name + "_motion3"); ob.animation_data.action = a
    for f in range(1, SUM_N + 1):
        pp = P(*path_uv(ppath, f)); pbp = P(*path_uv(bpath, f, {(1, 40)}))
        dvec = pp - pbp
        fwd = -dvec.normalized(); fwd.z = 0
        zf = ground(*(pp + fwd * 1.0).xy); zb = ground(*(pp - fwd * 1.0).xy); pp.z = min(pp.z, (zf + zb) / 2)
        parm.location = pp; parm.rotation_euler = (0, 0, math.atan2(-dvec.x, dvec.y))
        db = pbp - pa
        barm.location = pbp; barm.rotation_euler = (0, 0, math.atan2(-(-db.x), -db.y) if f > 0 else 0)
        for ob in (parm, barm):
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
    for ob in (parm, barm): finish_action(ob.animation_data.action)
    # ---- summon swirl: motes leave the ocarina and gather into the panda's shape
    OCP = {}
    for f in range(1, SUM_N + 1):
        scene.frame_set(f); OCP[f] = oc.matrix_world.translation.copy()
    src = [OCP[50] + Vector((random.uniform(-.05, .05), random.uniform(-.05, .05), random.uniform(-.05, .05))) for _ in range(40)]
    tgt_pts = mesh_points(pbody, 200, seed=7, frame=100)
    rnd = random.Random(5)
    spirit_stream("Summon", src, lambda f, T=tgt_pts: T[(f * 7) % len(T)], 46, 100, n=60, seed=21, swirl_r=0.6, turns=1.2)
    sparks("Spark_Materialize", parm.matrix_world.translation + Vector((0, 0, 0.8)), 98, n=24, color=(0.6, 0.95, 1.0),
           speed=2.2, life=14, seed=22, size=0.02)
    # ---- triple lightning
    for i, (fb, rid, sd) in enumerate(zip(S_BOLTS, ("B1", "B2", "B3"), (31, 33, 35))):
        mouth = bone_world(parm, "Bone_jaw02", fb)
        tgt = bone_world(barm, ("spine", "head", "spine")[i], fb) + Vector((0, 0, 0.1 + 0.1 * i))
        bolt(f"GhostBolt{i}", mouth, tgt, fb, nframes=6, seed=sd, color=(0.5, 0.9, 1.0), light_e=3500)
        sparks(f"Spark_G{i}", tgt, fb, n=16, color=(0.55, 0.9, 1.0), speed=2.8, seed=sd + 1)
        hud_hit(fb + 1, tgt + Vector((0, 0, 0.55 + 0.12 * i)), rid, target="brute")
        ev(fb, "zap", dur=0.35, gain=0.9); ev(fb + 1, "thud", gain=0.6, pitch=1.1)
        if ROLLS[rid]["crit"]: ev(fb + 1, "crit")
    flash("KOFlash", bone_world(barm, "spine", S_KO), S_KO, radius=1.0, color=(0.6, 0.9, 1.0), light_e=5000)
    hud_hit(S_KO + 14, bone_world(barm, "head", S_KO + 14) + Vector((0, 0, 0.8)), None, text="K.O.!", kind="ko", target="brute")
    dizzy_stars(barm, S_KO + 12, SUM_N, n=5)
    ev(S_KO + 8, "thud", gain=1.0, pitch=0.45); ev(S_KO + 13, "thud", gain=0.6, pitch=0.6); ev(S_KO + 12, "boing")
    ev(S_KO + 18, "stars", dur=3.0)
    ev(46, "shimmer", dur=2.4); ev(98, "chime"); ev(100, "whoosh", dur=0.6, gain=0.5, pitch=0.8)
    for f in range(108, 134, 7): ev(f, "step", gain=0.5, pitch=0.8)
    ev(S_FIRE - 14, "whoosh", dur=0.4, gain=0.5, pitch=0.5); ev(190, "roar"); ev(205, "shimmer", dur=1.4, gain=0.5)
    for f in (6, 18, 30): ev(f, "step", gain=0.6, pitch=0.55)
    # ---- camera
    kc = bone_world(barm, "spine", 215); U3 = Vector((U.x, U.y, 0)); V3 = Vector((V.x, V.y, 0))
    shot_cam("Cam_Summon", [
        (1, 64, P(1.7, -2.3, 1.55), P(0, 0, 1.30), P(1.25, -1.6, 1.55), P(0, 0, 1.42), 35, 40),
        (65, 103, P(1.5, -6.2, 1.45), P(1.7, -0.4, 0.95), P(1.7, -5.8, 1.5), P(1.8, -0.4, 0.95), 28, 28),
        (104, 150, P(-2.0, -2.6, 0.95), P(3.0, -0.2, 0.85), P(-0.9, -2.5, 1.0), P(3.4, -0.1, 0.85), 30, 32),
        (151, 200, P(2.8, -3.2, 1.25), P(3.0, 0.1, 0.85), P(3.1, -3.0, 1.3), P(3.3, 0.1, 0.8), 22, 22),
        (201, SUM_N, kc + U3 * -1.9 + V3 * -4.6 + Vector((0, 0, 1.5)), kc + Vector((0, 0, 0.15)),
         kc + U3 * -1.5 + V3 * -4.0 + Vector((0, 0, 1.3)), kc + Vector((0, 0, 0.1)), 30, 32)])
    project_hud("summon", SUM_N, dict(melody=dict(f0=1, f1=S_PLAY_END + 8)))
    return ns

# ============================================================================= MODE export (game-ready rigs)
def _export(arm, body, clips, base, vl):
    ad = arm.animation_data_create(); ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    for a in clips:
        tr = ad.nla_tracks.new(); tr.name = a.name; tr.strips.new(a.name, int(a.frame_range[0]), a)
    for pb in arm.pose.bones: pb.matrix_basis.identity()
    bpy.ops.object.select_all(action='DESELECT')
    for o in (arm, body): o.hide_set(False); o.hide_render = False; o.select_set(True)
    vl.objects.active = arm
    glb = base + ".glb"; fbx = base + ".fbx"
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_yup=True,
                              export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                              export_def_bones=False, export_lights=False, export_cameras=False,
                              export_anim_single_armature=True, export_reset_pose_bones=True)
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                             path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE')
    print("EXPORTED", glb, fbx, [a.name for a in clips])

def export_sequel():
    ex = os.path.join(SEQ, "exports"); os.makedirs(ex, exist_ok=True)
    vl = bpy.context.view_layer
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)
    for o in list(bpy.data.objects):          # export only what we build here
        if o.type in ('ARMATURE',) or o.name.startswith("Archer"): o.hide_set(True)
    # ---- Grubbo
    barm, bbody = build_brute(); brute_clips(barm, prefix="brute_")
    for m in bbody.data.materials:
        b = m.node_tree.nodes.get("Principled BSDF")
        for sock in ("Base Color", "Normal"):
            for l in list(b.inputs[sock].links): m.node_tree.links.remove(l)
        b.inputs["Base Color"].default_value = (*m["export_color"], 1)
    clips = sorted([a for a in bpy.data.actions if a.name.startswith("brute_")], key=lambda a: a.name)
    for a in clips: a.name = a.name[len("brute_"):]
    _export(barm, bbody, clips, os.path.join(ex, "brute_grubbo_rigged"), vl)
    for a in clips: bpy.data.actions.remove(a)
    barm.hide_set(True); bbody.hide_set(True)
    # ---- ghost panda (same rig + clips as ../fight/exports/panda_rigged, translucent emissive material)
    parm, pbody, _ = build_panda(); panda_clips(parm)
    src = bpy.data.materials["M_Panda"]
    gm = bpy.data.materials.new("M_PandaGhost_glTF"); gm.use_nodes = True
    N = gm.node_tree.nodes; L = gm.node_tree.links; b = N["Principled BSDF"]
    tx = N.new("ShaderNodeTexImage"); tx.image = src.node_tree.nodes["Image Texture"].image
    L.new(tx.outputs[0], b.inputs["Base Color"])
    b.inputs["Emission Color"].default_value = (0.35, 0.8, 1.0, 1); b.inputs["Emission Strength"].default_value = 1.5
    b.inputs["Alpha"].default_value = 0.4; b.inputs["Roughness"].default_value = 0.4
    try: gm.surface_render_method = 'BLENDED'
    except Exception: pass
    pbody.data.materials[0] = gm
    clips = sorted([a for a in bpy.data.actions if a.name.startswith("panda_")], key=lambda a: a.name)
    for a in clips: a.name = a.name[len("panda_"):]
    _export(parm, pbody, clips, os.path.join(ex, "panda_ghost_rigged"), vl)

# ============================================================================= main
if MODE == "fightwin":
    parm, BOXES, POS = build_fightwin()
    if "check" in SACTS: check_framing(BOXES)
    if "preview" in SACTS: preview("fightwin", [int(x) for x in SOPTS.get("frames", "265,287,310,337,371,396,420").split(",")])
    if "anim" in SACTS: render_frames("fightwin", 266, FRAME_END)
    if "save" in SACTS: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SEQ, "fightwin.blend"), compress=True)
elif MODE == "capture":
    build_capture()
    if "preview" in SACTS: preview("capture", [int(x) for x in SOPTS.get("frames", "1,30,50,70,90,100,120").split(",")])
    if "anim" in SACTS: render_frames("capture", 1, CAP_N)
    if "save" in SACTS: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SEQ, "capture.blend"), compress=True)
elif MODE == "brute":
    barm, BOXES = build_brute_shot()
    if "check" in SACTS: check_framing(BOXES)
    if "preview" in SACTS: preview("brute", [int(x) for x in SOPTS.get("frames", "1,40,72,90,121,155,160,196,232,250").split(",")])
    if "anim" in SACTS: render_frames("brute", 1, BR_N)
    if "save" in SACTS: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SEQ, "brute.blend"), compress=True)
elif MODE == "summon":
    build_summon()
    if "preview" in SACTS: preview("summon", [int(x) for x in SOPTS.get("frames", "30,85,120,152,157,175,220").split(",")])
    if "anim" in SACTS: render_frames("summon", 1, SUM_N)
    if "still" in SACTS:
        render_setup(int(SOPTS.get("ssamples", 32)), (1920, 1080))
        scene.frame_set(int(SOPTS.get("sframe", 157)))
        scene.render.filepath = os.path.join(SEQ, "ghost_panda_summon_1920x1080.png")
        t = time.time(); bpy.ops.render.render(write_still=True); print(f"STILL {time.time() - t:.1f}s")
        with open(os.path.join(SEQ, "render_log.txt"), "a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} summon still frame {scene.frame_current} {time.time() - t:.0f}s\n")
    if "save" in SACTS: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SEQ, "summon.blend"), compress=True)
elif MODE == "export":
    export_sequel()
