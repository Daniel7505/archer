"""
fight_scene.py - "Archer vs Panda" evenly matched duel cinematic in the golden-hour meadow.

Loads ../scene.blend (built by ../build_scene.py; that file is never modified), imports the stock
Panda3D panda (converted by panda_extract.py -> panda_src/panda.json), rigs both fighters with named
animation clips (actions), lays them out in the NLA, adds arrows, lightning, sparks, camera work and
renders.  Usage:

  B=/workspace/blender/blender-4.2.23-linux-x64/blender
  $B -b ../scene.blend -P fight_scene.py -- [actions] [key=value]
Actions:
  save        save fight.blend
  check       framing check (both fighters in frame on every frame) + write events.json
  preview     render a handful of frames  (frames=1,70,116  res=640x360 samples=8) -> tmp/
  anim        render all frames -> frames/f_####.png   (res=1280x720 samples=8 start= end=)
  still       render the hero still (sframe=, ssamples=) -> fight_hero_1920x1080.png
  export      export panda + archer rigs with named clips -> exports/*.glb / *.fbx
"""
import bpy, bmesh, math, random, sys, os, json, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/workspace/archer_scene/fight"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OPTS = dict(a.split("=", 1) for a in argv if "=" in a)
ACTIONS = [a for a in argv if "=" not in a]
scene = bpy.context.scene
FPS = 24
FRAME_END = 420
random.seed(3)

def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in scene.collection.children:
        scene.collection.children.link(c)
    return c
C_FIGHT = coll("Fight")

# ----------------------------------------------------------------------------- terrain height
_T = bpy.data.objects["Terrain"]
_me = _T.data
_mw = _T.matrix_world
_BVH = BVHTree.FromPolygons([_mw @ v.co for v in _me.vertices], [tuple(p.vertices) for p in _me.polygons])
def ground(x, y):
    hit = _BVH.ray_cast(Vector((x, y, 100.0)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else 0.0

# fight frame: archer stays near A0, axis U points to the panda, V is to the left of U
A0 = Vector((-0.6, 0.0))
U = Vector((0.6, 0.8)).normalized()
V = Vector((-U.y, U.x))
def fw(u, v):
    p = A0 + U * u + V * v
    return Vector((p.x, p.y, ground(p.x, p.y)))
AXIS_YAW = math.atan2(U.y, U.x)

def smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def interp_keys(t, keys, ease=True):
    """keys: [(t, value_tuple)], piecewise smoothstep interpolation of tuples."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            k = smooth(k) if ease else k
            return tuple(x + (y - x) * k for x, y in zip(a, b))
    return keys[-1][1]

# ----------------------------------------------------------------------------- materials
def emission_mat(name, color, strength, alpha_grad=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*color, 1); em.inputs[1].default_value = strength
    if alpha_grad:
        # fade along local +Y (0 at the head of the trail -> transparent at the tail)
        tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
        L.new(tc.outputs["Generated"], sep.inputs[0])
        tr = N.new("ShaderNodeBsdfTransparent"); mix = N.new("ShaderNodeMixShader")
        pw = N.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
        L.new(sep.outputs["Y"], pw.inputs[0])
        L.new(pw.outputs[0], mix.inputs[0]); L.new(em.outputs[0], mix.inputs[1]); L.new(tr.outputs[0], mix.inputs[2])
        L.new(mix.outputs[0], out.inputs[0])
    else:
        L.new(em.outputs[0], out.inputs[0])
    m["fx"] = 1
    return m

def link_ob(ob, c=None):
    (c or C_FIGHT).objects.link(ob); return ob

# ----------------------------------------------------------------------------- pose helpers (shared)
def rest_of(arm, bname):
    return arm.data.bones[bname].matrix_local.copy()

def delta_basis(arm, bname, rot=(0, 0, 0), loc=(0, 0, 0), pivot=None):
    """Bone basis for a rotation `rot` (XYZ euler degrees about ARMATURE axes, applied at the bone head
    as if the parent had not moved) plus an armature-space offset `loc`.  If pivot (armature space) is given,
    the rotation is about that point instead of the bone head."""
    R = Euler([math.radians(a) for a in rot], 'XYZ').to_matrix()
    rest = rest_of(arm, bname); r3 = rest.to_3x3()
    q = (r3.inverted() @ R @ r3).to_quaternion()
    off = Vector(loc)
    if pivot is not None:
        h = rest.translation; p = Vector(pivot)
        off = off + (p + R @ (h - p)) - h
    return r3.inverted() @ off, q

def key_bases(arm, action, frame, bases):
    """bases: {bone: (loc Vector, quat, scale tuple|None)} -> keyframes in `action` at frame."""
    for bn, b in bases.items():
        loc, q = b[0], b[1]; sc = b[2] if len(b) > 2 and b[2] is not None else (1, 1, 1)
        for path, vals in (("location", loc), ("rotation_quaternion", q), ("scale", sc)):
            dp = f'pose.bones["{bn}"].{path}'
            for i, v in enumerate(vals):
                fc = action.fcurves.find(dp, index=i)
                if fc is None:
                    fc = action.fcurves.new(dp, index=i, action_group=bn)
                fc.keyframe_points.insert(frame, v, options={'FAST'})

def finish_action(action, interp='LINEAR'):
    for fc in action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = interp
        fc.update()

def new_action(name):
    a = bpy.data.actions.get(name)
    if a: bpy.data.actions.remove(a)
    a = bpy.data.actions.new(name); a.use_fake_user = True
    return a

# ----------------------------------------------------------------------------- panda import
PANDA_H = 1.45                     # top of the head/back in metres (archer is ~1.9 m)
def build_panda():
    d = json.load(open(os.path.join(HERE, "panda_src", "panda.json")))
    V_ = np.array(d["verts"]); s = PANDA_H / V_[:, 2].max()
    def colm(m, scale=True):
        M = Matrix(m).transposed()           # panda row-vector -> column-vector
        if scale: M.translation = M.translation * s
        return M
    names = [j["name"] for j in d["joints"]]; parent = {j["name"]: j["parent"] for j in d["joints"]}
    loc = {j["name"]: colm(j["bind"]) for j in d["joints"]}
    def nets(local_of):
        out = {}
        for n in names:
            out[n] = (out[parent[n]] if parent[n] else Matrix.Identity(4)) @ local_of(n)
        return out
    NB = nets(lambda n: loc[n])
    # --- mesh
    me = bpy.data.meshes.new("Panda_Mesh")
    me.from_pydata([tuple(v * s) for v in V_], [], [tuple(t) for t in d["tris"]])
    me.validate(); me.update()
    uv = me.uv_layers.new(name="UVMap")
    uvs = d["uvs"]
    for li, l in enumerate(me.loops):
        uv.data[li].uv = uvs[l.vertex_index]
    me.shade_smooth()
    try:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in d["normals"]])
    except Exception as e:
        print("custom normals failed", e)
    mat = bpy.data.materials.new("M_Panda"); mat.use_nodes = True
    N = mat.node_tree.nodes; L = mat.node_tree.links; bs = N["Principled BSDF"]
    tx = N.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(HERE, "panda_src", "panda-model.jpg")); tx.image.pack()
    L.new(tx.outputs[0], bs.inputs["Base Color"])       # direct link so glTF/FBX pick up the texture
    bs.inputs["Roughness"].default_value = 0.85
    bs.inputs["Sheen Weight"].default_value = 0.6; bs.inputs["Sheen Roughness"].default_value = 0.4
    me.materials.append(mat)
    body = bpy.data.objects.new("Panda_Body", me); link_ob(body)
    # --- armature
    ad = bpy.data.armatures.new("PandaRig"); arm = bpy.data.objects.new("Panda", ad); link_ob(arm)
    ad.display_type = 'STICK'
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    r = eb.new("root"); r.head = (0, 0, 0); r.tail = (0, -0.3, 0)
    C4 = Matrix.Rotation(math.radians(-90), 4, 'Z')        # Blender bone +Y  <- joint +X
    children = {n: [c for c in names if parent[c] == n] for n in names}
    SC = {}
    for n in names:
        t, q, sc = NB[n].decompose(); SC[n] = sc
        b = eb.new(n)
        ln = 0.06
        if children[n]:
            ln = max(0.02, (NB[children[n][0]].translation - t).length)
        b.head = (0, 0, 0); b.tail = (0, ln, 0)
        b.matrix = Matrix.Translation(t) @ q.to_matrix().to_4x4() @ C4
    for n in names:
        eb[n].parent = eb[parent[n]] if parent[n] else eb["root"]
        eb[n].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for n in names:
        if n.startswith("Dummy_") and n.endswith(("heel", "toe")):
            ad.bones[n].use_deform = False
    ad.bones["root"].use_deform = False
    body.parent = arm
    mod = body.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
    for n in names: body.vertex_groups.new(name=n)
    for vi, w in enumerate(d["weights"]):
        for jn, wt in w.items():
            if wt > 1e-4: body.vertex_groups[jn].add([vi], wt, 'REPLACE')
    # --- stock walk clip -> action "panda_walk" (30 fps source, re-timed to 24 fps)
    REST = {n: ad.bones[n].matrix_local.copy() for n in names}
    REST["root"] = ad.bones["root"].matrix_local.copy()
    NBinv = {n: NB[n].inverted() for n in names}
    walk = new_action("panda_walk")
    WALK = []
    nf = d["num_frames"]
    for f in range(nf):
        NF = nets(lambda n: colm(d["frames"][n][f]))
        P = {n: NF[n] @ NBinv[n] @ REST[n] for n in names}
        P["root"] = REST["root"]
        bases = {"root": (Vector((0, 0, 0)), Quaternion(), (1, 1, 1))}
        for n in names:
            pn = parent[n] or "root"
            Bm = REST[n].inverted() @ REST[pn] @ P[pn].inverted() @ P[n]
            t, q, sc = Bm.decompose()
            bases[n] = (t, q, tuple(sc))
        WALK.append(bases)
        key_bases(arm, walk, 1 + f * FPS / d["fps"], bases)
    finish_action(walk)
    arm["walk_len"] = (nf - 1) * FPS / d["fps"]
    return arm, body, WALK

# ----------------------------------------------------------------------------- generic clip baking
def rotm(e):
    return Euler([math.radians(a) for a in e], 'XYZ').to_matrix()

def basis_from_R(arm, bname, R, off=Vector((0, 0, 0)), pivot=None):
    rest = rest_of(arm, bname); r3 = rest.to_3x3()
    q = (r3.inverted() @ R @ r3).to_quaternion()
    off = Vector(off)
    if pivot is not None:
        h = rest.translation; p = Vector(pivot)
        off = off + (p + R @ (h - p)) - h
    return (r3.inverted() @ off, q)

def lerp_pose(keys, f, defaults):
    """keys: [(frame, {param: tuple|float})]; params missing from a key inherit the previous key / default."""
    full = []
    cur = dict(defaults)
    for fr, p in keys:
        cur = dict(cur); cur.update(p); full.append((fr, cur))
    if f <= full[0][0]: return full[0][1]
    for (f0, a), (f1, b) in zip(full, full[1:]):
        if f <= f1:
            k = smooth((f - f0) / (f1 - f0)) if f1 > f0 else 1.0
            out = {}
            for n in a:
                x, y = a[n], b[n]
                if x is None or y is None: out[n] = y if k > 0.5 else x
                elif isinstance(x, (int, float)): out[n] = x + (y - x) * k
                else: out[n] = tuple(xx + (yy - xx) * k for xx, yy in zip(x, y))
            return out
    return full[-1][1]

def bake_clip(arm, name, nframes, pose_fn, solver, extra_paths=None):
    """pose_fn(f) -> params; solver(arm, params) -> ({bone: (loc, quat, scale)}, {datapath: value})."""
    act = new_action(name)
    prevq = {}
    for f in range(nframes + 1):
        bases, extra = solver(arm, pose_fn(f))
        for bn, b in bases.items():
            q = b[1]
            if bn in prevq and prevq[bn].dot(q) < 0: q = -q
            prevq[bn] = q
            bases[bn] = (b[0], q, b[2] if len(b) > 2 else None)
        key_bases(arm, act, 1 + f, bases)
        for dp, val in extra.items():
            fc = act.fcurves.find(dp) or act.fcurves.new(dp, action_group="fx")
            fc.keyframe_points.insert(1 + f, val, options={'FAST'})
    finish_action(act)
    return act

# ----------------------------------------------------------------------------- archer rig upgrade
ARCH = bpy.data.objects["Archer"]; ABODY = bpy.data.objects["Archer_Body"]
NOCK = Vector((0.065, -0.115, 1.54))
GRIP = Vector((0.712, -0.06, 1.47))
TIP_LO = Vector((0.547, -0.06, 0.67)); TIP_HI = Vector((0.547, -0.06, 2.27))
STRAIGHT = (TIP_LO + TIP_HI) / 2
ADIR = (GRIP + Vector((0, -0.01, 0.035)) - NOCK).normalized()

def upgrade_archer():
    """Make the string/nocked arrow animatable: string ends follow a 'nock' bone, nocked arrow on an 'arrow' bone."""
    me = ABODY.data
    mats = [m.name for m in me.materials]
    i_string = mats.index("M_String"); arrow_m = {mats.index(n) for n in ("M_BowWood", "M_Steel", "M_FletchRed")}
    bm = bmesh.new(); bm.from_mesh(me)
    dl = bm.verts.layers.deform.verify()
    gidx = {g.name: g.index for g in ABODY.vertex_groups}
    for n in ("nock", "arrow"):
        if n not in gidx: gidx[n] = ABODY.vertex_groups.new(name=n).index
    bm.verts.ensure_lookup_table()
    # loose parts
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; part = []
        seen.add(v.index)
        while stack:
            x = stack.pop(); part.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen: seen.add(o.index); stack.append(o)
        parts.append(part)
    kill = []; n_arrow = 0
    p0 = NOCK; p1 = NOCK + ADIR * 0.92
    def dist_line(c):
        t = max(0.0, min(1.0, (c - p0).dot(ADIR) / (p1 - p0).length)); return (c - (p0 + (p1 - p0) * t)).length
    for part in parts:
        fm = {f.material_index for v in part for f in v.link_faces}
        if fm == {i_string}:
            kill.extend(part); continue
        if fm and fm <= arrow_m and all(gidx["hand.L"] in v[dl] for v in part):
            if all(dist_line(v.co) < 0.045 for v in part):
                al = [(v.co - p0).dot(ADIR) for v in part]; zz = [v.co.z for v in part]
                if (max(al) - min(al)) > 1.2 * (max(zz) - min(zz)):
                    for v in part:
                        v[dl].clear(); v[dl][gidx["arrow"]] = 1.0
                    n_arrow += 1
    bmesh.ops.delete(bm, geom=list(set(kill)), context='VERTS')
    # new string: tip -> nock -> tip, nock ring weighted to the nock bone
    for a, b in ((TIP_HI, NOCK), (NOCK, TIP_LO)):
        d = b - a; q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
        r = bmesh.ops.create_cone(bm, cap_ends=False, segments=5, radius1=0.0035, radius2=0.0035, depth=d.length, matrix=M)
        for v in r["verts"]:
            near_nock = (v.co - NOCK).length < 0.05
            v[dl].clear(); v[dl][gidx["nock" if near_nock else "hand.L"]] = 1.0
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = i_string; f.smooth = True
    bm.to_mesh(me); bm.free(); me.update()
    print("ARCHER upgrade: arrow parts", n_arrow, "string verts removed", len(set(kill)))
    # bones
    bpy.context.view_layer.objects.active = ARCH
    for o in bpy.context.selected_objects: o.select_set(False)
    ARCH.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ARCH.data.edit_bones
    nb = eb.new("nock"); nb.head = NOCK; nb.tail = NOCK + ADIR * 0.1; nb.parent = eb["hand.L"]
    ab = eb.new("arrow"); ab.head = NOCK; ab.tail = NOCK + ADIR * 0.1; ab.parent = nb
    tb = eb.new("nock_target"); tb.head = NOCK; tb.tail = NOCK + ADIR * 0.05; tb.parent = eb["hand.R"]
    bpy.ops.object.mode_set(mode='OBJECT')
    ARCH.data.bones["nock_target"].use_deform = False
    c = ARCH.pose.bones["nock"].constraints.new('COPY_LOCATION'); c.name = "CopyHand"
    c.target = ARCH; c.subtarget = "nock_target"
    for pb in ARCH.pose.bones: pb.rotation_mode = 'QUATERNION'

# ----------------------------------------------------------------------------- archer solver (FK + analytic 2-bone IK)
def ik2(S, T, la, lb, pole):
    d = T - S; dist = min(d.length, (la + lb) * 0.999); dist = max(dist, abs(la - lb) * 1.001)
    ax = d.normalized()
    along = (la * la - lb * lb + dist * dist) / (2 * dist); h = math.sqrt(max(0.0, la * la - along * along))
    pp = (pole - ax * pole.dot(ax))
    pp = pp.normalized() if pp.length > 1e-6 else Vector((0, -1, 0))
    E = S + ax * along + pp * h
    Tn = S + ax * dist
    return E, Tn

def rotdiff(a, b):
    return a.normalized().rotation_difference(b.normalized()).to_matrix()

ARCH_DEF = {"hips": (0, 0, 0), "hips_loc": (0, 0, 0), "spine": (0, 0, 0), "neck": (0, 0, 0), "head": (0, 0, 0),
            "upperarm.L": (0, 0, 0), "forearm.L": (0, 0, 0), "hand.L": (0, 0, 0),
            "handR": None, "ankleL": (0, 0, 0), "ankleR": (0, 0, 0),
            "nock_inf": 1.0, "nock_off": (0, 0, 0), "arrow_s": 1.0}

def arch_solver(arm, p):
    B = arm.data.bones
    H = {n: B[n].head_local.copy() for n in B.keys()}
    T = {n: B[n].tail_local.copy() for n in B.keys()}
    out = {}
    def rot_about(R, h):
        return Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h)
    Rh = rotm(p["hips"]); off = Vector(p["hips_loc"])
    Dh = Matrix.Translation(off) @ rot_about(Rh, H["hips"])
    out["hips"] = basis_from_R(arm, "hips", Rh, off)
    Rs = rotm(p["spine"]); Ds = Dh @ rot_about(Rs, H["spine"]); out["spine"] = basis_from_R(arm, "spine", Rs)
    for n in ("neck", "head", "upperarm.L", "forearm.L", "hand.L"):
        out[n] = basis_from_R(arm, n, rotm(p[n]))
    # right arm IK
    S = (Ds @ H["upperarm.R"]); Rsp = Ds.to_3x3()
    la = (H["forearm.R"] - H["upperarm.R"]).length; lb = (H["hand.R"] - H["forearm.R"]).length
    if p["handR"] is None:
        out["upperarm.R"] = basis_from_R(arm, "upperarm.R", Matrix.Identity(3))
        out["forearm.R"] = basis_from_R(arm, "forearm.R", Matrix.Identity(3))
    else:
        tgt = Vector(p["handR"])
        rest_up = H["forearm.R"] - H["upperarm.R"]; rest_fo = H["hand.R"] - H["forearm.R"]
        pole = Rsp @ (H["forearm.R"] - (H["upperarm.R"] + H["hand.R"]) / 2) + Vector((0, 0.15, 0))
        E, Tn = ik2(S, tgt, la, lb, pole)
        Ru = rotdiff(rest_up, Rsp.inverted() @ (E - S))
        Rf = rotdiff(rest_fo, (Rsp @ Ru).inverted() @ (Tn - E))
        out["upperarm.R"] = basis_from_R(arm, "upperarm.R", Ru)
        out["forearm.R"] = basis_from_R(arm, "forearm.R", Rf)
    out["hand.R"] = basis_from_R(arm, "hand.R", Matrix.Identity(3))
    # legs IK (ankles planted in armature space unless offset)
    Rhip = Dh.to_3x3()
    for s in ("L", "R"):
        th, sh, ft = "thigh." + s, "shin." + s, "foot." + s
        aoff = Vector(p["ankle" + s])
        if off.length < 1e-6 and aoff.length < 1e-6 and Rh == Matrix.Identity(3):
            for n in (th, sh, ft): out[n] = basis_from_R(arm, n, Matrix.Identity(3))
            continue
        Sx = Dh @ H[th]; tgt = H[sh].copy() * 0 + T[sh] + aoff
        la = (H[sh] - H[th]).length; lb = (T[sh] - H[sh]).length
        mid = (H[th] + T[sh]) / 2; pole = (H[sh] - mid); pole = Rhip @ pole if pole.length > 1e-4 else Vector((0, -1, 0))
        pole = pole.normalized() + Vector((0, -0.6, 0))
        E, Tn = ik2(Sx, tgt, la, lb, pole)
        Ru = rotdiff(H[sh] - H[th], Rhip.inverted() @ (E - Sx))
        Rf = rotdiff(T[sh] - H[sh], (Rhip @ Ru).inverted() @ (Tn - E))
        out[th] = basis_from_R(arm, th, Ru); out[sh] = basis_from_R(arm, sh, Rf)
        out[ft] = basis_from_R(arm, ft, (Rhip @ Ru @ Rf).inverted())
    # nock / arrow
    r3 = rest_of(arm, "nock").to_3x3()
    out["nock"] = (r3.inverted() @ Vector(p["nock_off"]), Quaternion())
    sc = max(0.001, p["arrow_s"]); out["arrow"] = (Vector((0, 0, 0)), Quaternion(), (sc, sc, sc))
    out["nock_target"] = (Vector((0, 0, 0)), Quaternion())
    extra = {'pose.bones["nock"].constraints["CopyHand"].influence': p["nock_inf"]}
    return out, extra

R_REST = Vector((0.0, -0.10, 1.535))
R_FOLLOW = (-0.15, -0.02, 1.50)
R_QUIVER = (-0.08, 0.20, 1.72)
R_STRING = (0.45, -0.07, 1.47)
REL = {"nock_inf": 0.0, "nock_off": tuple(STRAIGHT - NOCK), "arrow_s": 0.0}

def archer_clips(arm):
    D = ARCH_DEF; R0 = tuple(R_REST)
    clips = {}
    def mk(name, n, keys, loop=None):
        fn = (lambda f: lerp_pose(keys, f, D)) if loop is None else loop
        clips[name] = bake_clip(arm, name, n, fn, arch_solver)
    def idle(f):
        t = f / 48 * 2 * math.pi
        p = dict(D); p["hips_loc"] = (0, 0, -0.008 * (1 - math.cos(t)))
        p["spine"] = (1.2 * math.sin(t), 0, 0.8 * math.sin(t)); p["head"] = (0, 0, 2.0 * math.sin(t * 0.5))
        p["handR"] = R0; return p
    mk("archer_idle", 48, None, loop=idle)
    def walk(f):
        t = f / 24 * 2 * math.pi
        p = dict(D); p["handR"] = R0
        p["hips_loc"] = (0, 0, -0.03 + 0.025 * math.cos(2 * t))
        p["ankleL"] = (0, -0.16 * math.sin(t), max(0.0, 0.09 * math.cos(t)))
        p["ankleR"] = (0, 0.16 * math.sin(t), max(0.0, -0.09 * math.cos(t)))
        p["spine"] = (2.0, 0, 3.0 * math.sin(t)); return p
    mk("archer_walk", 24, None, loop=walk)
    aim = {"handR": R0}
    mk("archer_attack_arrow", 30, [
        (0, dict(aim)), (5, {"handR": (-0.03, -0.09, 1.535), "spine": (0, 0, 2)}), (8, {}),
        (9, dict(REL, handR=(-0.07, -0.06, 1.53), **{"upperarm.L": (0, 0, -4)})),
        (12, {"handR": R_FOLLOW, "upperarm.L": (0, -3, -2), "spine": (0, 0, -3)}),
        (15, {}), (20, {"handR": R_QUIVER, "head": (0, 0, -12), "upperarm.L": (0, 0, 0), "spine": (0, 0, 0)}),
        (23, {"handR": (0.30, -0.08, 1.50), "head": (0, 0, 0)}),
        (24, {"handR": R_STRING, "arrow_s": 1.0}),
        (26, {"handR": (0.33, -0.08, 1.50), "nock_inf": 1.0, "nock_off": (0, 0, 0)}),
        (30, {"handR": R0})])
    mk("archer_dodge", 20, [
        (0, dict(aim)), (3, {"hips_loc": (0, 0, 0.06)}),
        (7, {"hips_loc": (0, 0.02, -0.24), "hips": (14, 0, 0), "spine": (16, 0, 0), "head": (-12, 0, 0)}),
        (14, {}), (20, {"hips_loc": (0, 0, 0), "hips": (0, 0, 0), "spine": (0, 0, 0), "head": (0, 0, 0)})])
    mk("archer_hit_react", 24, [
        (0, dict(aim)),
        (3, {"hips_loc": (-0.10, 0.05, -0.04), "hips": (0, -8, 0), "spine": (-6, -16, 0), "head": (-10, -14, 0),
             "neck": (0, -6, 0), "handR": (-0.10, -0.16, 1.42), "upperarm.L": (0, -22, 10), "forearm.L": (0, -10, 0),
             "ankleL": (0.0, 0, 0.08)}),
        (9, {"hips_loc": (-0.06, 0.03, -0.06), "spine": (-3, -10, 0), "head": (-4, -8, 0), "ankleL": (0, 0, 0)}),
        (24, {"hips_loc": (0, 0, 0), "hips": (0, 0, 0), "spine": (0, 0, 0), "head": (0, 0, 0), "neck": (0, 0, 0),
              "handR": R0, "upperarm.L": (0, 0, 0), "forearm.L": (0, 0, 0)})])
    relaxed = dict(REL, **{"upperarm.L": (0, 62, 8), "forearm.L": (0, 10, 0), "handR": (0.02, -0.19, 1.28)})
    mk("archer_respect_bow", 48, [
        (0, dict(aim)), (10, dict(relaxed)),
        (18, {"spine": (34, 0, 0), "neck": (10, 0, 0), "head": (14, 0, 0), "hips": (6, 0, 0), "hips_loc": (0, 0.05, -0.02)}),
        (32, {}), (42, {"spine": (0, 0, 0), "neck": (0, 0, 0), "head": (0, 0, 0), "hips": (0, 0, 0), "hips_loc": (0, 0, 0)}),
        (48, {})])
    mk("archer_victory", 36, [
        (0, dict(aim)), (8, dict(REL, **{"upperarm.L": (0, -75, 0), "forearm.L": (0, -15, 0), "handR": (-0.30, 0.02, 1.62),
                                         "spine": (-8, 0, 0), "head": (-12, 0, 0)})),
        (12, {"hips_loc": (0, 0, 0.07)}), (16, {"hips_loc": (0, 0, 0)}), (28, {}), (36, {})])
    mk("archer_defeat", 36, [
        (0, dict(aim)), (8, dict(REL, **{"upperarm.L": (0, 65, 0), "handR": (0.05, -0.2, 1.2)})),
        (18, {"hips_loc": (0, 0.05, -0.40), "ankleR": (0.0, 0.42, 0.06), "spine": (24, 0, 0), "head": (22, 0, 0),
              "upperarm.L": (0, 70, -10)}),
        (36, {})])
    return clips

# ----------------------------------------------------------------------------- panda clips (FK on the converted rig)
P_BONES = ["Bone_spine01", "Bone_spine02", "Bone_spine03", "Bone_neck", "Bone_skull", "Bone_jaw01",
           "Bone_lf_clavicle", "Bone_lf_leg_upper", "Bone_lf_leg_lower", "Bone_lf_foot",
           "Bone_rf_clavicle", "Bone_rf_leg_upper", "Bone_rf_leg_lower", "Bone_rf_foot",
           "Bone_lr_leg_hip", "Bone_lr_leg_upper", "Bone_lr_leg_lower", "Bone_lr_foot",
           "Bone_rr_leg_hip", "Bone_rr_leg_upper", "Bone_rr_leg_lower", "Bone_rr_foot"]
PANDA_DEF = dict({b: (0, 0, 0) for b in P_BONES}, root=(0, 0, 0), root_loc=(0, 0, 0), pivot=(0, 0.1, 0.7),
                 spin=0.0, roll=0.0)

def panda_solver(arm, p):
    out = {}
    R = rotm(p["root"]) @ Matrix.Rotation(math.radians(p["spin"]), 3, 'Z') @ Matrix.Rotation(math.radians(p["roll"]), 3, 'Y')
    out["root"] = basis_from_R(arm, "root", R, Vector(p["root_loc"]), pivot=Vector(p["pivot"]))
    for b in arm.data.bones.keys():
        if b == "root": continue
        out[b] = basis_from_R(arm, b, rotm(p[b]) if b in p else Matrix.Identity(3))
    return out, {}

def legs(front=(0, 0, 0), rear=(0, 0, 0), front_low=None, rear_low=None):
    d = {}
    for s in ("l", "r"):
        d[f"Bone_{s}f_leg_upper"] = front; d[f"Bone_{s}r_leg_upper"] = rear
        if front_low is not None: d[f"Bone_{s}f_leg_lower"] = front_low
        if rear_low is not None: d[f"Bone_{s}r_leg_lower"] = rear_low
    return d

def panda_clips(arm):
    D = PANDA_DEF; clips = {}
    REAR_PIV = (0, 0.70, 0.05)
    def mk(name, n, keys=None, fn=None):
        clips[name] = bake_clip(arm, name, n, fn or (lambda f: lerp_pose(keys, f, D)), panda_solver)
    def idle(f):
        t = f / 48 * 2 * math.pi
        p = dict(D); p["root_loc"] = (0, 0, -0.012 * (1 - math.cos(t)))
        p["Bone_spine02"] = (1.5 * math.sin(t), 0, 0); p["Bone_skull"] = (2 * math.sin(t), 0, 5 * math.sin(t * 0.5))
        p["Bone_jaw01"] = (2 + 2 * math.sin(t), 0, 0); return p
    mk("panda_idle", 48, fn=idle)
    reared = dict(root=(-36, 0, 0), pivot=REAR_PIV, Bone_lr_leg_hip=(30, 0, 0), Bone_rr_leg_hip=(30, 0, 0),
                  Bone_neck=(18, 0, 0), Bone_skull=(-8, 0, 0), Bone_jaw01=(14, 0, 0),
                  **legs(front=(-30, 0, 0), front_low=(50, 0, 0)))
    mk("panda_attack_lightning", 36, [
        (0, {}), (9, dict(reared)),
        (15, {"Bone_jaw01": (26, 0, 0), "Bone_skull": (-16, 0, 0), **legs(front=(-5, 0, 0), front_low=(70, 0, 0))}),
        (18, {"Bone_neck": (34, 0, 0), "Bone_skull": (6, 0, 0), "Bone_jaw01": (32, 0, 0),
              **legs(front=(-70, 0, 0), front_low=(10, 0, 0))}),
        (24, {}),
        (30, {"root": (0, 0, 0), "root_loc": (0, 0, -0.06), "Bone_lr_leg_hip": (0, 0, 0), "Bone_rr_leg_hip": (0, 0, 0),
              "Bone_neck": (0, 0, 0), "Bone_skull": (0, 0, 0), "Bone_jaw01": (6, 0, 0), **legs(front_low=(0, 0, 0))}),
        (36, {"root_loc": (0, 0, 0), "Bone_jaw01": (0, 0, 0), **legs()})])
    def dodge(f):
        k = smooth(f / 18)
        p = lerp_pose([(0, {}), (4, dict(Bone_neck=(25, 0, 0), **legs(front=(25, 0, 0), rear=(-25, 0, 0)))),
                       (14, {}), (18, dict(Bone_neck=(0, 0, 0), **legs()))], f, D)
        p["roll"] = -360.0 * smooth((f - 2) / 13); p["pivot"] = (0, 0.1, 0.62)
        p["root_loc"] = (0, 0, 0.30 * math.sin(math.pi * max(0.0, min(1.0, (f - 2) / 13))))
        return p
    mk("panda_dodge", 18, fn=dodge)
    def spin(f):
        p = lerp_pose([(0, {}), (6, dict(root_loc=(0, 0, -0.12), **legs(front=(-8, 0, 0), rear=(10, 0, 0)))),
                       (8, dict(root_loc=(0, 0, 0), **legs())),
                       (11, dict(Bone_neck=(10, 0, 0), **legs(front=(25, 0, 0), front_low=(40, 0, 0), rear=(75, 0, 0)))),
                       (18, {}), (22, dict(Bone_neck=(0, 0, 0), **legs(front_low=(0, 0, 0)))),
                       (24, dict(root_loc=(0, 0, -0.10), **legs(front=(-6, 0, 0)))),
                       (30, dict(root_loc=(0, 0, 0), **legs()))], f, D)
        a = max(0.0, min(1.0, (f - 8) / 14))
        if 8 <= f <= 22:
            p["root_loc"] = (0, 0, 0.85 * math.sin(math.pi * a))
        p["spin"] = 360.0 * smooth(a); p["pivot"] = (0, 0.1, 0.0)
        return p
    mk("panda_spin_kick", 30, fn=spin)
    mk("panda_hit_react", 20, [
        (0, {}), (3, dict(root=(-12, 0, 0), root_loc=(0, 0.16, 0.03), pivot=REAR_PIV, Bone_skull=(-16, 0, 8),
                          Bone_jaw01=(16, 0, 0), Bone_neck=(-6, 0, 0), **legs(front=(-14, 0, 0)))),
        (9, {"root": (-5, 0, 0), "root_loc": (0, 0.10, 0.0), "Bone_skull": (-6, 0, 4)}),
        (20, dict(root=(0, 0, 0), root_loc=(0, 0, 0), Bone_skull=(0, 0, 0), Bone_jaw01=(0, 0, 0), Bone_neck=(0, 0, 0), **legs()))])
    mk("panda_respect_bow", 48, [
        (0, {}), (12, dict(root=(9, 0, 0), pivot=REAR_PIV, Bone_neck=(30, 0, 0), Bone_skull=(22, 0, 0),
                           **legs(front=(-9, 0, 0), front_low=(14, 0, 0)))),
        (34, {}), (46, dict(root=(0, 0, 0), Bone_neck=(0, 0, 0), Bone_skull=(0, 0, 0), **legs(front_low=(0, 0, 0)))), (48, {})])
    mk("panda_victory", 36, [
        (0, {}), (10, dict(reared, root=(-50, 0, 0), Bone_jaw01=(30, 0, 0), Bone_skull=(-20, 0, 0),
                           **legs(front=(-60, 0, 30), front_low=(20, 0, 0)))),
        (16, {"Bone_skull": (-26, 0, 10)}), (22, {"Bone_skull": (-26, 0, -10)}), (28, {}),
        (36, dict(root=(0, 0, 0), Bone_lr_leg_hip=(0, 0, 0), Bone_rr_leg_hip=(0, 0, 0), Bone_neck=(0, 0, 0),
                  Bone_skull=(0, 0, 0), Bone_jaw01=(0, 0, 0), **legs(front_low=(0, 0, 0))))])
    splay = {}
    for s, sg in (("l", -1), ("r", 1)):
        splay[f"Bone_{s}f_leg_upper"] = (-20, sg * 55, 0); splay[f"Bone_{s}r_leg_upper"] = (20, sg * 55, 0)
    mk("panda_defeat", 36, [
        (0, {}), (14, dict(root_loc=(0, 0, -0.30), root=(0, 10, 0), Bone_neck=(25, 0, 0), Bone_skull=(10, 0, 0), **splay)),
        (36, {})])
    return clips

# ============================================================================= CHOREOGRAPHY
# frame numbers at 24 fps.  (u, v) = fight-axis coordinates (u toward the panda's side, v to the left).
F_ARROW1 = 70; F_ARROW1_END = 80
F_BOLT1 = 114; F_BOLT1_HIT = 115
F_ARROW2 = 154; F_ARROW2_HIT = 158
F_KICK = 204
F_ARROW3 = 244; F_ARROW3_HIT = 246
F_CLASH_FIRE = 314; F_CLASH = 316
F_BOW = 356

ARCHER_PATH = [(1, (0.0, 0.0)), (108, (0.0, 0.0)), (116, (0.0, -0.5)), (126, (-0.5, -0.65)),
               (212, (-0.5, -0.65)), (226, (-0.45, -2.0)), (266, (-0.45, -2.0)), (294, (0.0, -0.45)),
               (317, (0.0, -0.45)), (328, (-0.6, -0.5))]
PANDA_PATH = [(1, (9.6, 0.25)), (56, (7.0, 0.0)), (64, (7.0, 0.0)), (82, (7.1, 1.7)),
              (158, (7.1, 1.7)), (167, (7.45, 1.8)), (180, (7.45, 1.8)), (206, (3.2, 0.5)),
              (210, (3.2, 0.5)), (226, (0.75, 0.05)), (246, (0.75, 0.05)), (258, (1.7, 0.55)),
              (268, (1.7, 0.55)), (296, (6.0, 0.5)), (317, (6.0, 0.5)), (330, (6.7, 0.55))]
LINEAR_SEGS = {"panda": {(1, 56), (180, 206), (268, 296)}, "archer": {(266, 294)}}

# NLA strips: (action, start, kwargs)
ARCHER_STRIPS = [("archer_attack_arrow", F_ARROW1 - 8, {}),
                 ("archer_dodge", 106, {}), ("archer_hit_react", F_BOLT1_HIT, {"bin": 1}),
                 ("archer_attack_arrow", F_ARROW2 - 8, {}),
                 ("archer_dodge", 211, {"scale": 1.0}),
                 ("archer_attack_arrow", F_ARROW3 - 8, {}),
                 ("archer_walk", 266, {"repeat": 1.2, "scale": 1.0, "reverse": True}),
                 ("archer_attack_arrow", F_CLASH_FIRE - 8, {}),
                 ("archer_hit_react", F_CLASH + 1, {"bin": 1}),
                 ("archer_respect_bow", F_BOW, {"hold": True})]
PANDA_STRIPS = [("panda_walk", 1, {"walk_speed": 2.6 / (55 / FPS), "frames": 58, "bin": 0, "cap": 2.4}),
                ("panda_dodge", 64, {}),
                ("panda_attack_lightning", F_BOLT1 - 18, {}),
                ("panda_hit_react", F_ARROW2_HIT, {"bin": 1}),
                ("panda_walk", 180, {"walk_speed": 4.4 / (26 / FPS), "frames": 28, "cap": 2.8}),
                ("panda_spin_kick", F_KICK, {}),
                ("panda_hit_react", F_ARROW3_HIT, {"bin": 1}),
                ("panda_walk", 268, {"walk_speed": 4.3 / (28 / FPS), "frames": 28, "reverse": True, "cap": 2.4}),
                ("panda_attack_lightning", F_CLASH_FIRE - 18, {}),
                ("panda_hit_react", F_CLASH + 1, {"bin": 1}),
                ("panda_respect_bow", F_BOW + 2, {"hold": True})]

def path_at(path, f, who):
    for (f0, a), (f1, b) in zip(path, path[1:]):
        if f0 <= f <= f1:
            k = (f - f0) / (f1 - f0) if f1 > f0 else 1
            if (f0, f1) not in LINEAR_SEGS[who]: k = smooth(k)
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    return path[-1][1] if f > path[-1][0] else path[0][1]

def panda_stride(arm):
    arm.animation_data_create(); arm.animation_data.action = bpy.data.actions["panda_walk"]
    ys = []
    for f in range(1, 50):
        scene.frame_set(f); ys.append(arm.pose.bones["Bone_lf_foot"].head.y)
    arm.animation_data.action = None
    rng = max(ys) - min(ys); T = arm["walk_len"] / FPS
    return rng / (0.6 * T)        # ~natural ground speed of the stock cycle (m/s)

def add_strip(ob, act, start, scale=1.0, repeat=1.0, reverse=False, bin=3, bout=3, hold=False):
    tr = ob.animation_data.nla_tracks.new(); tr.name = f"{act.name}@{start}"
    s = tr.strips.new(act.name, int(start), act)
    s.use_auto_blend = False
    s.repeat = repeat; s.scale = scale; s.use_reverse = reverse
    L = s.frame_end - s.frame_start
    s.blend_in = min(bin, L / 2); s.blend_out = 0 if hold else min(bout, L / 2)
    s.extrapolation = 'HOLD_FORWARD' if hold else 'NOTHING'
    return s

def layout_nla(parm, v_nat):
    for ob, base, strips in ((ARCH, "archer_idle", ARCHER_STRIPS), (parm, "panda_idle", PANDA_STRIPS)):
        ad = ob.animation_data_create(); ad.action = None
        for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
        b = add_strip(ob, bpy.data.actions[base], 1, repeat=math.ceil(FRAME_END / 48) + 1, bin=0, bout=0)
        b.extrapolation = 'HOLD'
        for name, start, kw in strips:
            kw = dict(kw); act = bpy.data.actions[name]
            if "walk_speed" in kw:
                v = kw.pop("walk_speed"); nfr = kw.pop("frames"); cap = kw.pop("cap", 2.5)
                rate = min(cap, v / v_nat)                  # cycle playback speed-up so the paws roughly don't skate
                L = act.frame_range[1] - act.frame_range[0]
                kw["scale"] = 1.0 / rate; kw["repeat"] = max(1.0, nfr / (L / rate))
            add_strip(ob, act, start, **kw)

def key_motion(parm):
    """Object-level root motion: location + facing, keyed every frame (stays out of the game clips)."""
    for ob in (ARCH, parm):
        a = new_action(ob.name + "_motion"); a.use_fake_user = False
        ob.animation_data.action = a
    POS = {}
    for f in range(1, FRAME_END + 1):
        ua, va = path_at(ARCHER_PATH, f, "archer"); up, vp = path_at(PANDA_PATH, f, "panda")
        pa = fw(ua, va); pp = fw(up, vp)
        d = (pp - pa); yaw_a = math.atan2(d.y, d.x)
        # panda: keep the 2.9 m body on the ground (average of front/back ground heights)
        fwd = -d.normalized(); fwd.z = 0
        zf = ground(*(pp + fwd * 1.0).xy); zb = ground(*(pp - fwd * 1.0).xy)
        pp.z = min(pp.z, (zf + zb) / 2)
        ARCH.location = (pa.x, pa.y, pa.z - 0.02); ARCH.rotation_euler = (0, 0, yaw_a)
        parm.location = pp; parm.rotation_euler = (0, 0, math.atan2(-d.x, d.y))   # panda faces local -Y
        for ob in (ARCH, parm):
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
        POS[f] = (pa.copy(), pp.copy())
    for ob in (ARCH, parm):
        unwrap = ob.animation_data.action.fcurves.find("rotation_euler", index=2)
        prev = None
        for kp in unwrap.keyframe_points:
            if prev is not None:
                while kp.co[1] - prev > math.pi: kp.co[1] -= 2 * math.pi
                while kp.co[1] - prev < -math.pi: kp.co[1] += 2 * math.pi
            prev = kp.co[1]
        finish_action(ob.animation_data.action)
    return POS

# ============================================================================= FX
def key_vis(ob, ranges):
    """visible only inside [(f0, f1), ...] (inclusive)."""
    ob.hide_render = True; ob.hide_viewport = True
    ob.keyframe_insert("hide_render", frame=1); ob.keyframe_insert("hide_viewport", frame=1)
    for f0, f1 in ranges:
        ob.hide_render = False; ob.hide_viewport = False
        ob.keyframe_insert("hide_render", frame=f0); ob.keyframe_insert("hide_viewport", frame=f0)
        ob.hide_render = True; ob.hide_viewport = True
        ob.keyframe_insert("hide_render", frame=f1 + 1); ob.keyframe_insert("hide_viewport", frame=f1 + 1)
    for fc in ob.animation_data.action.fcurves:
        if fc.data_path.startswith("hide_"):
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'

def mesh_from_bm(name, bm, mats):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    return link_ob(bpy.data.objects.new(name, me))

M_TRAIL = None
def make_arrow(name):
    global M_TRAIL
    bm = bmesh.new()
    def cone(a, b, r1, r2, seg, mi):
        a = Vector(a); b = Vector(b); d = b - a
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=d.length,
                                  matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4())
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = mi
    cone((0, -0.84, 0), (0, 0, 0), 0.0075, 0.0075, 6, 0)
    cone((0, 0, 0), (0, 0.08, 0), 0.018, 0.0, 4, 1)
    cone((0, -0.83, 0), (0, -0.70, 0), 0.034, 0.012, 3, 2)
    M = bpy.data.materials
    ob = mesh_from_bm(name, bm, [M["M_BowWood"], M["M_Steel"], M["M_FletchRed"]])
    ob.rotation_mode = 'QUATERNION'
    # glowing streak behind the arrow
    if M_TRAIL is None:
        M_TRAIL = emission_mat("M_ArrowTrail", (1.0, 0.85, 0.55), 6.0, alpha_grad=True)
    bt = bmesh.new()
    r = bmesh.ops.create_cone(bt, cap_ends=False, segments=8, radius1=0.004, radius2=0.035, depth=1.8,
                              matrix=Matrix.Translation((0, -0.84 - 0.9, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'X'))
    tr = mesh_from_bm(name + "_Trail", bt, [M_TRAIL]); tr.parent = ob
    tr.visible_shadow = False
    return ob, tr

def bone_world(ob, bname, f, tail=False):
    scene.frame_set(f)
    pb = ob.pose.bones[bname]
    return ob.matrix_world @ (pb.tail if tail else pb.head)

def arrow_release(f):
    """world tip position + direction of the nocked arrow just before release frame f."""
    scene.frame_set(f)
    pb = ARCH.pose.bones["arrow"]
    h = ARCH.matrix_world @ pb.head; t = ARCH.matrix_world @ pb.tail
    d = (t - h).normalized()
    return h + d * 0.92 * ARCH.scale.x, d

def fly_arrow(name, f0, f1, target, after="stick", seed=0):
    """flight f0->f1 to target; after: 'stick' (embed), 'bounce' (deflect & fall), 'vanish'."""
    ob, tr = make_arrow(name)
    start, d0 = arrow_release(f0 - 1)
    rnd = random.Random(seed)
    path = []
    for f in range(f0, f1 + 1):
        k = (f - f0) / (f1 - f0)
        p = start.lerp(target, k) + Vector((0, 0, 0.12 * math.sin(math.pi * k)))
        path.append((f, p))
    prev = None
    for i, (f, p) in enumerate(path):
        nxt = path[min(i + 1, len(path) - 1)][1]; prv = path[max(i - 1, 0)][1]
        vel = (nxt - prv) if (nxt - prv).length > 1e-6 else (target - start)
        ob.location = p; q = vel.to_track_quat('Y', 'Z')
        if prev is not None and prev.dot(q) < 0: q = -q
        ob.rotation_quaternion = q; prev = q
        ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_quaternion", frame=f)
    vis_end = FRAME_END
    if after == "stick":
        vdir = (target - start).normalized()
        ob.location = target + vdir * 0.18; ob.keyframe_insert("location", frame=f1 + 1)
        vis_end = FRAME_END
    elif after == "bounce":
        vdir = (target - start).normalized()
        side = Vector((-vdir.y, vdir.x, 0)) * rnd.uniform(-1.5, 1.5)
        vel = -vdir * 2.5 + Vector((0, 0, 4.2)) + side
        p = target.copy(); axis = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3))).normalized()
        q0 = ob.rotation_quaternion.copy(); ang = 0.0; f = f1
        while f < FRAME_END:
            f += 1; dt = 1 / FPS
            vel.z -= 9.8 * dt; p = p + vel * dt; ang += 14.0 * dt
            g = ground(p.x, p.y) + 0.03
            landed = p.z <= g
            if landed:
                p.z = g; flat = Vector((vel.x, vel.y, 0))
                q = (flat if flat.length > 1e-3 else vdir).to_track_quat('Y', 'Z')
            else:
                q = Quaternion(axis, ang) @ q0
            if q.dot(prev) < 0: q = -q
            prev = q
            ob.location = p; ob.rotation_quaternion = q
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_quaternion", frame=f)
            if landed: break
    elif after == "vanish":
        vis_end = f1
    key_vis(ob, [(f0, vis_end)])
    key_vis(tr, [(f0, f1)])
    return ob

def bolt(name, A, B, f0, nframes=7, seed=1, color=(0.55, 0.75, 1.0), light_e=2500):
    """Jagged emissive lightning (3 flickering variants that grow from A) + a light flash."""
    mat = bpy.data.materials.get("M_Lightning") or emission_mat("M_Lightning", (0.75, 0.88, 1.0), 45.0)
    objs = []
    for vi in range(3):
        rnd = random.Random(seed * 10 + vi)
        cu = bpy.data.curves.new(f"{name}_{vi}", 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = 0.022; cu.bevel_resolution = 1; cu.use_fill_caps = True
        def jag(a, b, depth, amp):
            pts = [a, b]
            for lv in range(depth):
                new = [pts[0]]
                for p, q in zip(pts, pts[1:]):
                    m = (p + q) / 2; L = (q - p).length
                    off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * L * amp
                    new += [m + off, q]
                pts = new
            return pts
        main = jag(A, B, 5, 0.22)
        splines = [(main, 1.0)]
        for _ in range(3):
            i = rnd.randrange(4, len(main) - 6)
            st = main[i]; dirv = (main[min(i + 6, len(main) - 1)] - st)
            end = st + dirv * rnd.uniform(1.0, 2.0) + Vector((rnd.uniform(-.5, .5), rnd.uniform(-.5, .5), rnd.uniform(-.6, .2)))
            splines.append((jag(st, end, 3, 0.3), 0.5))
        for pts, w in splines:
            sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
            for k, p in enumerate(pts):
                sp.points[k].co = (*p, 1); sp.points[k].radius = w * (1.0 - 0.5 * k / len(pts))
        cu.materials.append(mat)
        ob = link_ob(bpy.data.objects.new(f"{name}_{vi}", cu)); ob.visible_shadow = False
        cu.bevel_factor_end = 0.35; cu.keyframe_insert("bevel_factor_end", frame=f0)
        cu.bevel_factor_end = 1.0; cu.keyframe_insert("bevel_factor_end", frame=f0 + 1)
        ranges = [(f, f) for f in range(f0, f0 + nframes) if (f - f0) % 3 == vi]
        key_vis(ob, ranges); objs.append(ob)
    ld = bpy.data.lights.new(name + "_Flash", 'POINT'); ld.color = color; ld.shadow_soft_size = 0.4
    lo = link_ob(bpy.data.objects.new(name + "_Flash", ld)); lo.location = A.lerp(B, 0.55) + Vector((0, 0, 0.3))
    for f, e in ((f0 - 1, 0), (f0, light_e), (f0 + 1, light_e * 0.6), (f0 + 2, light_e), (f0 + 4, light_e * 0.5),
                 (f0 + nframes, light_e * 0.2), (f0 + nframes + 2, 0)):
        ld.energy = e; ld.keyframe_insert("energy", frame=f)
    return objs

def sparks(name, c, f0, n=14, color=(1.0, 0.8, 0.4), speed=3.0, life=9, seed=0, size=0.03, strength=30):
    rnd = random.Random(seed)
    mat = emission_mat(name + "_M", color, strength)
    for i in range(n):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size)
        ob = mesh_from_bm(f"{name}_{i}", bm, [mat]); ob.visible_shadow = False; ob.rotation_mode = 'QUATERNION'
        v = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), abs(rnd.gauss(0.4, 1)))).normalized() * speed * rnd.uniform(0.5, 1.3)
        p = c.copy(); L = int(life * rnd.uniform(0.6, 1.2))
        for k in range(L + 1):
            ob.location = p; ob.rotation_quaternion = v.to_track_quat('Y', 'Z')
            s = 1.0 - k / L
            ob.scale = (s, s * 3.5 * min(1.0, v.length / 3), s)
            ob.keyframe_insert("location", frame=f0 + k); ob.keyframe_insert("scale", frame=f0 + k)
            ob.keyframe_insert("rotation_quaternion", frame=f0 + k)
            p = p + v / FPS; v.z -= 9.8 / FPS
        key_vis(ob, [(f0, f0 + L)])

def flash(name, c, f0, radius=1.1, color=(1.0, 0.72, 0.4), light_e=6000):
    m = bpy.data.materials.new(name + "_M"); m.use_nodes = True
    N = m.node_tree.nodes; Lk = m.node_tree.links
    for x in list(N): N.remove(x)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader"); lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.5
    em.inputs[0].default_value = (*color, 1); em.inputs[1].default_value = 12
    # energy ball: opacity = (1 - facing)^2 * opac  (soft rim, see-through, fades out via the keyed 'opac')
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    Lk.new(lw.outputs["Facing"], inv.inputs[1])
    sq = N.new("ShaderNodeMath"); sq.operation = 'POWER'; sq.inputs[1].default_value = 3.0; Lk.new(inv.outputs[0], sq.inputs[0])
    op = N.new("ShaderNodeValue"); op.name = "opac"; op.outputs[0].default_value = 1.0
    mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; Lk.new(sq.outputs[0], mul.inputs[0]); Lk.new(op.outputs[0], mul.inputs[1])
    Lk.new(mul.outputs[0], mix.inputs[0]); Lk.new(tr.outputs[0], mix.inputs[1]); Lk.new(em.outputs[0], mix.inputs[2])
    Lk.new(mix.outputs[0], out.inputs[0])
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1.0)
    ob = mesh_from_bm(name, bm, [m]); ob.location = c; ob.visible_shadow = False
    for f, s, e, o in ((f0, 0.15, 20, 0.9), (f0 + 2, 0.6, 9, 0.5), (f0 + 4, 0.85, 5, 0.25), (f0 + 7, 1.05, 1, 0.0)):
        ob.scale = (s * radius,) * 3; ob.keyframe_insert("scale", frame=f)
        em.inputs[1].default_value = e; em.inputs[1].keyframe_insert("default_value", frame=f)
        op.outputs[0].default_value = o; op.outputs[0].keyframe_insert("default_value", frame=f)
    key_vis(ob, [(f0, f0 + 7)])
    # flat shock ring
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=False, segments=48, radius=1.0)
    rng = link_ob(bpy.data.objects.new(name + "_Ring", bpy.data.meshes.new(name + "_RingMe")))
    bm.to_mesh(rng.data); bm.free()
    mod = rng.modifiers.new("skin", 'WIREFRAME'); mod.thickness = 0.03
    rng.data.materials.append(emission_mat(name + "_RingM", (1.0, 0.9, 0.7), 12))
    rng.location = c; rng.visible_shadow = False
    for f, s in ((f0, 0.2), (f0 + 8, 3.2)):
        rng.scale = (s, s, s); rng.keyframe_insert("scale", frame=f)
    key_vis(rng, [(f0, f0 + 8)])
    ld = bpy.data.lights.new(name + "_Light", 'POINT'); ld.color = color; ld.shadow_soft_size = 0.5
    lo = link_ob(bpy.data.objects.new(name + "_Light", ld)); lo.location = c + Vector((0, 0, 0.2))
    for f, e in ((f0 - 1, 0), (f0, light_e), (f0 + 3, light_e * 0.5), (f0 + 10, 0)):
        ld.energy = e; ld.keyframe_insert("energy", frame=f)

# ============================================================================= CAMERA
# (start, end, azimuth deg [start, end] relative to the fight axis, elevation deg [s, e], lens, margin, bias, dist mult [s, e])
# azimuth 0 = behind the archer looking at the panda, 90 = side-on (archer left / panda right), 180 = behind the panda
SHOTS = [(1, 60, (62, 78), (7, 6), 30, 0.80, 0.55, (1.15, 1.0)),       # standoff, panda walks in
         (61, 95, (24, 30), (9, 8), 35, 0.85, 0.30, (1.0, 1.0)),       # over the archer's shoulder: arrow 1, roll
         (96, 145, (112, 104), (9, 11), 32, 0.82, 0.50, (1.0, 1.0)),   # lightning clips the archer
         (146, 179, (160, 152), (10, 9), 35, 0.85, 0.62, (1.0, 1.0)),  # reverse: arrow 2 bonks the panda
         (180, 235, (78, 96), (4, 6), 26, 0.78, 0.50, (1.0, 1.0)),     # charge + spin kick (low, wide)
         (236, 265, (128, 120), (12, 10), 35, 0.85, 0.50, (1.0, 1.0)), # counter shot
         (266, 345, (68, 76), (7, 6), 26, 0.84, 0.50, (1.0, 1.0)),     # reposition + clash
         (346, 420, (58, 40), (6, 12), 32, 0.84, 0.50, (1.0, 1.35))]   # mutual bow, pull-out

def eval_boxes():
    """per frame: world-space bbox corners of both (deformed) bodies."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for f in range(1, FRAME_END + 1):
        scene.frame_set(f)
        res = []
        for nm in ("Archer_Body", "Panda_Body"):
            ob = bpy.data.objects[nm].evaluated_get(dg)
            res.append([ob.matrix_world @ Vector(c) for c in ob.bound_box])
        out[f] = res
    return out

def fit_camera(f, boxes, az, el, lens, margin, bias, mult, sensor=36.0, aspect=16 / 9):
    A, P = boxes
    ca = sum(A, Vector()) / 8; cp = sum(P, Vector()) / 8
    tgt = ca.lerp(cp, bias)
    yaw = AXIS_YAW + math.radians(az); e = math.radians(el)
    d = Vector((math.cos(yaw) * math.cos(e), math.sin(yaw) * math.cos(e), -math.sin(e)))
    right = d.cross(Vector((0, 0, 1))).normalized(); up = right.cross(d)
    tx = sensor / 2 / lens * margin; ty = tx / aspect
    best = 2.5
    for p in A + P:
        r = p - tgt
        x, y, z = r.dot(right), r.dot(up), r.dot(d)
        best = max(best, abs(x) / tx - z, abs(y) / ty - z)
    return tgt, d, best * mult

def build_camera(boxes):
    cd = bpy.data.cameras.new("Cam_Fight"); cd.clip_end = 400; cd.sensor_width = 36
    cam = link_ob(bpy.data.objects.new("Cam_Fight", cd)); cam.rotation_mode = 'QUATERNION'
    scene.camera = cam
    CAMS = {}
    for (f0, f1, az, el, lens, margin, bias, mult) in SHOTS:
        raw = []
        for f in range(f0, f1 + 1):
            k = (f - f0) / max(1, f1 - f0)
            a_ = az[0] + (az[1] - az[0]) * smooth(k); e_ = el[0] + (el[1] - el[0]) * smooth(k)
            m_ = mult[0] + (mult[1] - mult[0]) * smooth(k)
            raw.append((f, fit_camera(f, boxes[f], a_, e_, lens, margin, bias, m_)))
        n = len(raw)
        dist = [r[1][2] for r in raw]
        env = [max(dist[max(0, i - 10):i + 11]) for i in range(n)]            # conservative envelope
        sm = [sum(env[max(0, i - 8):i + 9]) / len(env[max(0, i - 8):i + 9]) for i in range(n)]
        tg = [r[1][0] for r in raw]
        tgs = [sum(tg[max(0, i - 5):i + 6], Vector()) / len(tg[max(0, i - 5):i + 6]) for i in range(n)]
        for i, (f, (t_, d_, _)) in enumerate(raw):
            loc = tgs[i] - d_ * max(sm[i], dist[i])
            loc.z = max(loc.z, ground(loc.x, loc.y) + 0.6)
            CAMS[f] = (loc, tgs[i], lens)
    prev = None
    for f in range(1, FRAME_END + 1):
        loc, t_, lens = CAMS[f]
        cam.location = loc; q = (t_ - loc).to_track_quat('-Z', 'Y')
        if prev is not None and prev.dot(q) < 0: q = -q
        prev = q; cam.rotation_quaternion = q; cd.lens = lens
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f)
        cd.keyframe_insert("lens", frame=f)
    for a in (cam.animation_data.action, cd.animation_data.action):
        for fc in a.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    return cam, CAMS

def thin_grass_near_camera(CAMS):
    """Fade the scatter density to zero within ~2 m of the camera path (less shimmer, no blades in the lens)."""
    me = _T.data
    if "grass" not in me.attributes: return
    n = len(me.vertices)
    co = np.zeros(n * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    co = np.c_[co, np.ones(n)] @ np.array(_mw).T
    camp = np.array([[c[0].x, c[0].y] for c in CAMS.values()])
    g = np.zeros(n, dtype=np.float32); me.attributes["grass"].data.foreach_get("value", g)
    dmin = np.full(n, 1e9)
    for i in range(0, len(camp), 2):
        dmin = np.minimum(dmin, np.hypot(co[:, 0] - camp[i, 0], co[:, 1] - camp[i, 1]))
    k = np.clip((dmin - 2.0) / 4.5, 0, 1); k = k * k * (3 - 2 * k)
    g2 = (g * (0.12 + 0.88 * k)).astype(np.float32)
    me.attributes["grass"].data.foreach_set("value", g2); me.update()
    print("GRASS thinned verts:", int((k < 0.99).sum()))

# ============================================================================= BUILD
EVENTS = []
def ev(f, kind, **kw):
    EVENTS.append(dict(t=round((f - 1) / FPS, 3), frame=f, kind=kind, **kw))

def build_fx(parm):
    # --- arrow 1: panda rolls clear, arrow skims past and sticks in the meadow behind it
    # it ends up in the practice target behind the panda (target face centre, see build_scene.build_target)
    tface = fw(13.0, 0.0); tface.z = ground(tface.x, tface.y) + 1.15
    tn = (Matrix.Rotation(math.atan2(-U.y, -U.x), 3, 'Z') @ Matrix.Rotation(math.radians(-12), 3, 'Y')) @ Vector((1, 0, 0))
    miss = tface + tn * 0.07 + Vector((-U.y, U.x, 0)) * 0.12 + Vector((0, 0, 0.06))
    fly_arrow("Arrow1", F_ARROW1, F_ARROW1_END, miss, after="stick", seed=1)
    ev(F_ARROW1, "twang"); ev(F_ARROW1, "whoosh", dur=0.45); ev(F_ARROW1_END, "thud", gain=0.35, pitch=1.6)
    ev(66, "whoosh", dur=0.5, gain=0.5, pitch=0.6); ev(80, "thud", gain=0.6, pitch=0.7)            # roll + landing
    ev(F_BOLT1 - 18 + 4, "whoosh", dur=0.4, gain=0.4, pitch=0.5)                                  # rear-up
    # --- lightning 1: clips the archer's bow shoulder as he tries to sidestep
    mouth = bone_world(parm, "Bone_jaw02", F_BOLT1)
    hit = bone_world(ARCH, "upperarm.L", F_BOLT1_HIT) + Vector((0, 0, 0.05))
    past = hit + (hit - mouth).normalized() * 1.2 + Vector((0, 0, -0.3))
    bolt("Bolt1", mouth, hit, F_BOLT1, nframes=7, seed=3)
    bolt("Bolt1b", hit, past, F_BOLT1 + 1, nframes=4, seed=4, light_e=0)
    sparks("Spark_Bolt1", hit, F_BOLT1_HIT, n=16, color=(0.6, 0.8, 1.0), speed=2.5, seed=5)
    ev(F_BOLT1, "zap", dur=0.45); ev(F_BOLT1_HIT, "thud", gain=0.7, pitch=1.0)
    # --- arrow 2: bonks off the panda's shoulder (thick fur, no harm done)
    tgt2 = bone_world(parm, "Bone_lf_clavicle", F_ARROW2_HIT) + Vector((0, 0, 0.12))
    fly_arrow("Arrow2", F_ARROW2, F_ARROW2_HIT, tgt2, after="bounce", seed=7)
    sparks("Spark_Arrow2", tgt2, F_ARROW2_HIT, n=10, color=(1.0, 0.85, 0.5), speed=2.0, seed=8, size=0.022)
    ev(F_ARROW2, "twang"); ev(F_ARROW2, "whoosh", dur=0.25); ev(F_ARROW2_HIT, "bonk")
    # --- charge + spin kick (near miss)
    ev(186, "thud", gain=0.35, pitch=0.6); ev(194, "thud", gain=0.35, pitch=0.6); ev(202, "thud", gain=0.35, pitch=0.6)
    ev(F_KICK + 8, "whoosh", dur=0.3, gain=0.6, pitch=0.7); ev(F_KICK + 13, "whoosh", dur=0.45, gain=1.0, pitch=1.2)
    ev(F_KICK + 22, "thud", gain=1.0, pitch=0.55); ev(214, "whoosh", dur=0.3, gain=0.4, pitch=1.4)
    # --- counter shot at close range: bonk on the panda's flank
    tgt3 = bone_world(parm, "Bone_spine02", F_ARROW3_HIT) + Vector((0, 0, 0.05))
    fly_arrow("Arrow3", F_ARROW3, F_ARROW3_HIT, tgt3, after="bounce", seed=9)
    sparks("Spark_Arrow3", tgt3, F_ARROW3_HIT, n=10, color=(1.0, 0.85, 0.5), speed=2.0, seed=10, size=0.022)
    ev(F_ARROW3, "twang"); ev(F_ARROW3_HIT, "bonk")
    ev(270, "thud", gain=0.25, pitch=0.6); ev(282, "thud", gain=0.25, pitch=0.6)
    # --- the clash: arrow and lightning meet in mid-air -> burst knocks both back
    mouth2 = bone_world(parm, "Bone_jaw02", F_CLASH_FIRE)
    nock2, _ = arrow_release(F_CLASH_FIRE - 1)
    M = nock2.lerp(mouth2, 0.45)
    fly_arrow("Arrow4", F_CLASH_FIRE, F_CLASH, M, after="vanish", seed=11)
    bolt("Bolt2", mouth2, M, F_CLASH_FIRE, nframes=4, seed=12)
    flash("Clash", M, F_CLASH, radius=1.3)
    sparks("Spark_ClashA", M, F_CLASH, n=18, color=(1.0, 0.8, 0.45), speed=4.0, seed=13, life=12)
    sparks("Spark_ClashB", M, F_CLASH, n=14, color=(0.6, 0.8, 1.0), speed=4.0, seed=14, life=12)
    ev(F_CLASH_FIRE, "twang"); ev(F_CLASH_FIRE, "zap", dur=0.2); ev(F_CLASH, "boom")
    ev(F_CLASH + 9, "thud", gain=0.6, pitch=0.8); ev(F_CLASH + 12, "thud", gain=0.8, pitch=0.55)
    ev(F_BOW + 14, "chime")
    return M

def build_all():
    scene.frame_start = 1; scene.frame_end = FRAME_END; scene.render.fps = FPS
    parm, pbody, _ = build_panda()
    upgrade_archer()
    archer_clips(ARCH); panda_clips(parm)
    v_nat = panda_stride(parm)
    print("PANDA natural walk speed m/s", round(v_nat, 2))
    layout_nla(parm, v_nat)
    POS = key_motion(parm)
    clash = build_fx(parm)
    boxes = eval_boxes()
    cam, CAMS = build_camera(boxes)
    thin_grass_near_camera(CAMS)
    # the old fly-through camera/targets stay in the file but are unused
    json.dump(dict(fps=FPS, frames=FRAME_END, events=sorted(EVENTS, key=lambda e: e["t"])),
              open(os.path.join(HERE, "events.json"), "w"), indent=1)
    return parm, boxes, CAMS

def check_framing(boxes):
    from bpy_extras.object_utils import world_to_camera_view
    bad = []; dg = bpy.context.evaluated_depsgraph_get()
    for f in range(1, FRAME_END + 1):
        scene.frame_set(f)
        cam = scene.camera
        vis = []
        for bb in boxes[f]:
            pts = [world_to_camera_view(scene, cam, p) for p in bb]
            inside = sum(1 for p in pts if 0 <= p.x <= 1 and 0 <= p.y <= 1 and p.z > 0) / 8
            c = world_to_camera_view(scene, cam, sum(bb, Vector()) / 8)
            vis.append((inside, 0 <= c.x <= 1 and 0 <= c.y <= 1 and c.z > 0))
        if not (vis[0][1] and vis[1][1]):
            bad.append((f, vis))
        # obstruction test camera -> each fighter centre
        for i, bb in enumerate(boxes[f]):
            c = sum(bb, Vector()) / 8; o = cam.matrix_world.translation
            dvec = c - o
            hit, loc, n_, idx, hob, _ = scene.ray_cast(dg, o, dvec.normalized(), distance=dvec.length - 1.6)
            if hit and hob.name not in ("Terrain",) and not hob.name.startswith(("Arrow", "Bolt", "Spark", "Clash", "God")):
                bad.append((f, f"fighter {i} blocked by {hob.name}"))
    print("FRAMING CHECK: problems on", len(bad), "frames")
    for b in bad[:40]: print("  ", b)
    return bad

def render_setup(samples, res):
    r = scene.render
    r.engine = 'CYCLES'; scene.cycles.device = 'CPU'
    scene.cycles.samples = samples; scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True; scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    r.resolution_x, r.resolution_y = res; r.resolution_percentage = 100
    r.use_persistent_data = True
    r.image_settings.file_format = 'PNG'; r.image_settings.color_depth = '8'
    if OPTS.get("volume", "1") == "0":
        bpy.data.objects["GodRayVolume"].hide_render = True

def parse_res(default):
    if "res" in OPTS:
        w, h = OPTS["res"].split("x"); return (int(w), int(h))
    return default

def export_rigs():
    """Game-ready exports: each fighter alone at the origin, rigged, one named clip per move."""
    parm, pbody, _ = build_panda()
    upgrade_archer(); archer_clips(ARCH); panda_clips(parm)
    ex = os.path.join(HERE, "exports"); os.makedirs(ex, exist_ok=True)
    # glTF/FBX cannot carry the procedural node trees: flatten the archer's materials to their export colour
    for m in ABODY.data.materials:
        if not m or not m.use_nodes or "export_color" not in m: continue
        b = m.node_tree.nodes.get("Principled BSDF")
        if not b: continue
        for sock in ("Base Color", "Normal"):
            for l in list(b.inputs[sock].links): m.node_tree.links.remove(l)
        b.inputs["Base Color"].default_value = (*m["export_color"], 1)
    vl = bpy.context.view_layer
    for a in list(bpy.data.actions):       # fly-through camera actions from scene.blend would become FBX takes
        if not a.name.startswith(("archer_", "panda_")): bpy.data.actions.remove(a)
    for name, arm, body, prefix in (("archer", ARCH, ABODY, "archer_"), ("panda", parm, pbody, "panda_")):
        clips = sorted([a for a in bpy.data.actions if a.name.startswith(prefix)], key=lambda a: a.name)
        if name == "panda":                # glTF 'ACTIONS' mode would otherwise also write the archer clips
            for a in list(bpy.data.actions):
                if a.name.startswith("archer_"): bpy.data.actions.remove(a)
        for a in clips: a.name = a.name[len(prefix):]
        saved = (arm.location.copy(), arm.rotation_euler.copy())
        arm.location = (0, 0, 0); arm.rotation_euler = (0, 0, 0)
        ad = arm.animation_data_create(); ad.action = None
        for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
        for a in clips:
            tr = ad.nla_tracks.new(); tr.name = a.name
            tr.strips.new(a.name, int(a.frame_range[0]), a)
        for pb in arm.pose.bones: pb.matrix_basis.identity()
        bpy.ops.object.select_all(action='DESELECT')
        for o in (arm, body): o.hide_set(False); o.select_set(True)
        vl.objects.active = arm
        glb = os.path.join(ex, f"{name}_rigged.glb"); fbx = os.path.join(ex, f"{name}_rigged.fbx")
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
        for a in clips: a.name = prefix + a.name
        arm.location, arm.rotation_euler = saved

if __name__ == "__main__" and ACTIONS == ["export"]:
    export_rigs()
elif __name__ == "__main__" and "noauto" not in ACTIONS:
    parm, BOXES, CAMS = build_all()
    for act in ACTIONS:
        if act == "save":
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "fight.blend"), compress=True)
        elif act == "check":
            check_framing(BOXES)
        elif act == "preview":
            render_setup(int(OPTS.get("samples", 8)), parse_res((640, 360)))
            for f in [int(x) for x in OPTS.get("frames", "1,70,116,158,220,246,316,380").split(",")]:
                scene.frame_set(f)
                scene.render.filepath = os.path.join(HERE, "tmp", f"prev_{f:04d}.png")
                t = time.time(); bpy.ops.render.render(write_still=True)
                print(f"PREVIEW {f} {time.time() - t:.1f}s")
        elif act == "anim":
            render_setup(int(OPTS.get("samples", 8)), parse_res((1280, 720)))
            scene.frame_start = int(OPTS.get("start", 1)); scene.frame_end = int(OPTS.get("end", FRAME_END))
            scene.frame_step = int(OPTS.get("step", 1))
            scene.render.filepath = os.path.join(HERE, "frames", "f_####")
            t = time.time(); bpy.ops.render.render(animation=True)
            print(f"ANIM done in {time.time() - t:.1f}s")
        elif act == "still":
            render_setup(int(OPTS.get("ssamples", 48)), (1920, 1080))
            scene.frame_set(int(OPTS.get("sframe", F_CLASH + 1)))
            scene.render.filepath = os.path.join(HERE, "fight_hero_1920x1080.png")
            t = time.time(); bpy.ops.render.render(write_still=True)
            print(f"STILL done in {time.time() - t:.1f}s")
