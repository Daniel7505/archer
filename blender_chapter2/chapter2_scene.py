"""
chapter2_scene.py - "Archer vs Panda: Chapter 2 - The Road to Aldermoor".
Continues from the sequel's end (Grubbo K.O.).  Builds on ../scene.blend and execs ../sequel/sequel_scene.py
(which execs ../fight/fight_scene.py) for rigs, clips, FX and helpers.

  mode=loot     Grubbo drops 4 glowing loot items with loot beams; the archer collects them   (frames_loot)
  mode=mount    the archer plays a NEW ocarina melody (notes2.json), the ghost panda appears; seated, they set off
  mode=ride     gallop down the road to the gates of ALDERMOOR (original city), slow to a walk at the gate
  mode=city     inside: across the canal bridge into the market square
  mode=stills   vendor stills (3), dusk skyline still, hero still (gate arrival, 1920x1080)
  mode=export   reusable city module pieces (wall, tower, gatehouse, roof houses, stalls, bridge, statue, banner)
  mode=citytest quick look renders of the city
  B=/workspace/blender/blender-4.2.23-linux-x64/blender
  $B -b ../scene.blend -P chapter2_scene.py -- mode=<m> [preview frames=a,b] [anim] samples=6 volume=0
Renders never overwrite existing frames (placeholders), so an interrupted render resumes where it stopped.
"""
import bpy, bmesh, math, random, sys, os, json, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

CH = "/workspace/archer_scene/chapter2"
_a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
COPTS = dict(a.split("=", 1) for a in _a if "=" in a); CACTS = [a for a in _a if "=" not in a]
CMODE = COPTS.get("mode", "citytest")
_saved = sys.argv
sys.argv = [sys.argv[0], "--", "mode=none"] + [f"{k}={v}" for k, v in COPTS.items() if k != "mode"]
_g = globals(); _f = _g.get("__file__"); _g["__file__"] = "/workspace/archer_scene/sequel/sequel_scene.py"
exec(compile(open("/workspace/archer_scene/sequel/sequel_scene.py").read(), "sequel_scene.py", "exec"), _g)
_g["__file__"] = _f; sys.argv = _saved
SEQ = CH                                  # sequel helpers (project_hud, ...) now write into chapter2/
HUD["hits"] = []; EVENTS.clear()

def logline(msg):
    with open(os.path.join(CH, "render_log.txt"), "a") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

def render_frames(mode, f0, f1, samples=6):
    """resumable: existing frames are skipped (use_overwrite False + placeholders)."""
    render_setup(int(COPTS.get("samples", samples)), parse_res((1280, 720)))
    od = os.path.join(CH, f"frames_{mode}"); os.makedirs(od, exist_ok=True)
    # drop empty placeholders left by an interrupted run
    for fn in os.listdir(od):
        if os.path.getsize(os.path.join(od, fn)) == 0: os.remove(os.path.join(od, fn))
    r = scene.render; r.use_overwrite = False; r.use_placeholder = True
    scene.frame_start = int(COPTS.get("start", f0)); scene.frame_end = int(COPTS.get("end", f1))
    r.filepath = os.path.join(od, "f_####")
    logline(f"{mode} render start {scene.frame_start}-{scene.frame_end} (have {len(os.listdir(od))})")
    t = time.time(); bpy.ops.render.render(animation=True)
    logline(f"{mode} render DONE {scene.frame_start}-{scene.frame_end} samples={scene.cycles.samples} {time.time() - t:.0f}s")

def preview(mode, frames, res=(640, 360), samples=8):
    render_setup(int(COPTS.get("samples", samples)), parse_res(res))
    for f in frames:
        scene.frame_set(f); scene.render.filepath = os.path.join(CH, "tmp", f"{mode}_{f:04d}.png")
        bpy.ops.render.render(write_still=True)

def still(path, frame, res, samples):
    render_setup(samples, res); scene.frame_set(frame); scene.render.filepath = path
    t = time.time(); bpy.ops.render.render(write_still=True); logline(f"still {os.path.basename(path)} {time.time() - t:.0f}s")

# ============================================================================= ALDERMOOR (original city)
GATE = Vector((10.0, 57.0)); Z0 = 1.2         # gate centre (xy) and city floor height
CITY_X = (-12.0, 32.0); CITY_Y = (57.0, 101.0)

ROAD = [(4.6, 27.0), (2.6, 33.0), (3.2, 41.0), (7.0, 49.5), (10.0, 55.5), (10.0, 60.0)]
ROAD_Z = [None] * len(ROAD)
def road_dist(x, y):
    best = 1e9
    for A, Bp in zip(ROAD[:-1], ROAD[1:]):
        A = Vector(A); Bp = Vector(Bp); ab = Bp - A; t = max(0, min(1, (Vector((x, y)) - A).dot(ab) / ab.length_squared))
        best = min(best, (Vector((x, y)) - (A + ab * t)).length)
    return best

def flatten_terrain():
    for i, (x, y) in enumerate(ROAD):
        ROAD_Z[i] = min(ground(x, y), Z0 - 0.05) if y < GATE.y - 1 else Z0 - 0.05
    ROAD_Z[0] = ground(*ROAD[0])
    """level a shelf for the city (smooth falloff into the hills), clear grass inside, carve the road to the gate."""
    me = _T.data; n = len(me.vertices)
    co = np.zeros(n * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    mw = np.array(_T.matrix_world); wi = np.linalg.inv(mw)
    w = (np.c_[co, np.ones(n)] @ mw.T)[:, :3]
    dx = np.maximum(0, np.maximum(CITY_X[0] - 2 - w[:, 0], w[:, 0] - CITY_X[1] - 2))
    dy = np.maximum(0, np.maximum(CITY_Y[0] - 1 - w[:, 1], w[:, 1] - CITY_Y[1] - 2))
    d = np.hypot(dx, dy); k = np.clip(d / 14.0, 0, 1); k = k * k * (3 - 2 * k)
    inside = d < 1e-6
    # road: leaves the meadow path at (4.6, 27), skirts west of the cottage garden, climbs to the gate
    pts = np.array(ROAD)
    best_d = np.full(n, 1e9); best_z = np.zeros(n)
    for (A, Bp, za, zb) in zip(pts[:-1], pts[1:], ROAD_Z[:-1], ROAD_Z[1:]):
        ab = Bp - A; tt = np.clip(((w[:, :2] - A) @ ab) / (ab @ ab), 0, 1); proj = A + tt[:, None] * ab
        dd = np.hypot(*(w[:, :2] - proj).T); upd = dd < best_d
        best_d = np.where(upd, dd, best_d); best_z = np.where(upd, za + (zb - za) * tt, best_z)
    dr = best_d; zr = best_z
    road = dr < 1.8
    kr = np.clip((dr - 1.8) / 6.0, 0, 1); kr = kr * kr * (3 - 2 * kr)
    roadzone = (dr < 8) & (w[:, 1] > 26)
    w[:, 2] = np.where(inside, Z0 - 0.08, Z0 - 0.08 + (w[:, 2] - (Z0 - 0.08)) * k)
    w[:, 2] = np.where(roadzone, zr + (w[:, 2] - zr) * kr, w[:, 2])
    lo = (np.c_[w, np.ones(n)] @ wi.T)[:, :3].astype(np.float32)
    me.vertices.foreach_set("co", lo.ravel()); me.update()
    g = np.zeros(n, dtype=np.float32); me.attributes["grass"].data.foreach_get("value", g)
    p = np.zeros(n, dtype=np.float32); me.attributes["path"].data.foreach_get("value", p)
    g = np.where(inside | road, 0.0, g); p = np.where(road, np.maximum(p, np.clip(1.6 - dr / 1.4, 0, 1)), p)
    me.attributes["grass"].data.foreach_set("value", g.astype(np.float32)); me.attributes["path"].data.foreach_set("value", p.astype(np.float32))
    me.update()
    global _BVH
    from mathutils.bvhtree import BVHTree
    _BVH = BVHTree.FromPolygons([_mw @ v.co for v in me.vertices], [tuple(pp.vertices) for pp in me.polygons])
    # trees/rocks: hide inside the city + road, re-seat the rest on the new surface
    for o in bpy.data.objects:
        if o.name.startswith(("pine", "oak", "rock")):
            x, y = o.location.x, o.location.y
            ddx = max(0, CITY_X[0] - 3 - x, x - CITY_X[1] - 3); ddy = max(0, CITY_Y[0] - 3 - y, y - CITY_Y[1] - 3)
            near_road = road_dist(x, y) < 4.0
            if (ddx == 0 and ddy == 0) or near_road:
                o.hide_render = True; o.hide_viewport = True
            elif y > 40:
                o.location.z = ground(x, y) - 0.05

def M(name, col, rough=0.7, metal=0.0, **kw):
    return mat("C_" + name, col, rough, metal, **kw)

def brick_mat(name, c1, c2, mortar=(0.55, 0.53, 0.5), scale=2.0, rough=0.75, vertical=True):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord"); br = N.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (*c1, 1); br.inputs["Color2"].default_value = (*c2, 1)
    br.inputs["Mortar"].default_value = (*mortar, 1); br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = 0.015
    if vertical:      # bricks on every vertical face: u = x + y, v = z
        sp = N.new("ShaderNodeSeparateXYZ"); ad = N.new("ShaderNodeMath"); ad.operation = 'ADD'
        cb = N.new("ShaderNodeCombineXYZ"); L.new(tc.outputs["Object"], sp.inputs[0])
        L.new(sp.outputs[0], ad.inputs[0]); L.new(sp.outputs[1], ad.inputs[1]); L.new(ad.outputs[0], cb.inputs[0])
        L.new(sp.outputs[2], cb.inputs[1]); L.new(cb.outputs[0], br.inputs["Vector"])
    else:
        L.new(tc.outputs["Object"], br.inputs["Vector"])
    L.new(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    m["export_color"] = tuple((a + c) / 2 for a, c in zip(c1, c2))
    return m

def emblem_image():
    """original Aldermoor emblem (gold alder leaf over three silver waves), drawn by make_assets.py (PIL)."""
    return os.path.join(CH, "aldermoor_banner.png")

def banner_mat():
    m = bpy.data.materials.get("C_Banner")
    if m: return m
    m = bpy.data.materials.new("C_Banner"); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links; b = N["Principled BSDF"]
    tx = N.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(emblem_image())
    L.new(tx.outputs["Color"], b.inputs["Base Color"])
    # black notch -> transparent
    sep = N.new("ShaderNodeSeparateColor"); L.new(tx.outputs["Color"], sep.inputs[0])
    mx = N.new("ShaderNodeMath"); mx.operation = 'GREATER_THAN'; mx.inputs[1].default_value = 0.02
    L.new(sep.outputs[2], mx.inputs[0]); L.new(mx.outputs[0], b.inputs["Alpha"])
    b.inputs["Roughness"].default_value = 0.8; b.inputs["Sheen Weight"].default_value = 0.5
    m["export_color"] = (0.09, 0.17, 0.47)
    return m

def window_mat():
    m = bpy.data.materials.get("C_Window")
    if m: return m
    m = mat("C_Window", (0.05, 0.08, 0.14), 0.15, emit=(1.0, 0.62, 0.25), estr=0.0)
    return m

MODS = {}
def module(name, build):
    """build a reusable module once into its own collection (not in the scene); returns the collection."""
    if name in MODS: return MODS[name]
    c = bpy.data.collections.new("MOD_" + name)
    bm = bmesh.new(); mats = []
    def mi(m):
        if m not in mats: mats.append(m)
        return mats.index(m)
    def box(c0, size, m, rot=0.0):
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c0) @ Matrix.Rotation(rot, 4, 'Z') @ Matrix.Diagonal((*size, 1)))
        for f in {f for v in r["verts"] for f in v.link_faces}: f.material_index = mi(m)
        return r["verts"]
    def cyl(c0, r1, r2, h, m, seg=16):
        rr = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=h,
                                   matrix=Matrix.Translation(Vector(c0) + Vector((0, 0, h / 2))))
        for f in {f for v in rr["verts"] for f in v.link_faces}: f.material_index = mi(m)
        return rr["verts"]
    def sph(c0, r, m, sc=(1, 1, 1), sub=2):
        rr = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(c0) @ Matrix.Diagonal((*sc, 1)))
        for f in {f for v in rr["verts"] for f in v.link_faces}: f.material_index = mi(m)
        return rr["verts"]
    def prism(c0, w, d, h, m, over=0.3):     # gable roof along x
        x0, y0, z0 = c0; hw = w / 2 + over; hd = d / 2 + over
        vs = [bm.verts.new(p) for p in ((x0 - hw, y0 - hd, z0), (x0 + hw, y0 - hd, z0), (x0 + hw, y0, z0 + h), (x0 - hw, y0, z0 + h),
                                         (x0 - hw, y0 + hd, z0), (x0 + hw, y0 + hd, z0))]
        fs = [bm.faces.new((vs[0], vs[1], vs[2], vs[3])), bm.faces.new((vs[3], vs[2], vs[5], vs[4])),
              bm.faces.new((vs[0], vs[3], vs[4])), bm.faces.new((vs[1], vs[5], vs[2])), bm.faces.new((vs[0], vs[4], vs[5], vs[1]))]
        for f in fs: f.material_index = mi(m)
    def poly_extrude(pts2d, y0, y1, m):     # 2D (x,z) outline extruded along y
        vs = [bm.verts.new((x, y0, z)) for x, z in pts2d]
        f = bm.faces.new(vs); f.material_index = mi(m)
        ex = bmesh.ops.extrude_face_region(bm, geom=[f])
        for v in [e for e in ex["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.y = y1
    build(box=box, cyl=cyl, sph=sph, prism=prism, poly=poly_extrude, bm=bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("MESH_" + name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    for p in me.polygons: p.use_smooth = False
    ob = bpy.data.objects.new("PIECE_" + name, me); c.objects.link(ob)
    MODS[name] = c
    return c

def city_materials():
    return dict(stone=brick_mat("C_StoneWall", (0.86, 0.84, 0.79), (0.78, 0.76, 0.71), scale=1.6),
                stone2=M("StoneTrim", (0.92, 0.90, 0.86), 0.6), roof=brick_mat("C_RoofTiles", (0.10, 0.22, 0.58), (0.08, 0.17, 0.46),
                                                                               mortar=(0.05, 0.08, 0.2), scale=4.0, rough=0.5),
                wood=M("Wood", (0.30, 0.17, 0.08), 0.7), gold=M("Gold", (1.0, 0.72, 0.25), 0.3, 0.9),
                plaster=M("Plaster", (0.93, 0.91, 0.86), 0.85), dark=M("DarkInset", (0.06, 0.05, 0.05), 0.9),
                window=window_mat(), statue=brick_mat("C_StatueStone", (0.80, 0.79, 0.76), (0.74, 0.73, 0.70), scale=0.9),
                iron=M("Iron", (0.25, 0.25, 0.27), 0.4, 0.8), banner=banner_mat(),
                cloth_r=M("ClothRed", (0.60, 0.10, 0.08), 0.85), cloth_b=M("ClothBlue", (0.10, 0.25, 0.65), 0.85),
                cloth_g=M("ClothGreen", (0.15, 0.45, 0.20), 0.85), cloth_y=M("ClothYellow", (0.85, 0.65, 0.15), 0.85),
                goods=M("Goods", (0.75, 0.45, 0.20), 0.6), fruit=M("Fruit", (0.85, 0.25, 0.15), 0.5))

def build_modules():
    C = city_materials()
    def wall(box, cyl, sph, prism, poly, bm):           # 6 m segment along x, 1.4 thick, 6 high, crenellated
        box((0, 0, 3.0), (6.0, 1.4, 6.0), C["stone"]); box((0, 0, 0.3), (6.0, 1.7, 0.6), C["stone2"])
        box((0, 0, 6.05), (6.0, 1.6, 0.25), C["stone2"])
        for i in range(5):
            for y in (-0.62, 0.62):
                box((-2.4 + i * 1.2, y, 6.6), (0.6, 0.35, 0.9), C["stone"])
    def tower(box, cyl, sph, prism, poly, bm):
        cyl((0, 0, 0), 2.4, 2.2, 10.0, C["stone"], seg=20); cyl((0, 0, 10.0), 2.65, 2.65, 0.7, C["stone2"], seg=20)
        cyl((0, 0, 10.7), 2.85, 0.05, 5.0, C["roof"], seg=20); sph((0, 0, 15.9), 0.22, C["gold"])
        for a in range(4):
            ang = a * math.pi / 2 + 0.4
            box((2.25 * math.cos(ang), 2.25 * math.sin(ang), 6.5), (0.25, 0.25, 1.1), C["window"], rot=ang)
            box((2.25 * math.cos(ang + 0.8), 2.25 * math.sin(ang + 0.8), 3.2), (0.25, 0.25, 0.9), C["window"], rot=ang + 0.8)
    def gatehouse(box, cyl, sph, prism, poly, bm):      # opening 4 m wide along y (road passes along +y)
        for s in (-1, 1):
            box((s * 4.0, 0, 6.0), (4.0, 4.4, 12.0), C["stone"]); box((s * 4.0, 0, 12.3), (4.6, 5.0, 0.6), C["stone2"])
            cyl((s * 4.0, 0, 12.6), 3.4, 0.05, 5.5, C["roof"], seg=4)
            sph((s * 4.0, 0, 18.2), 0.3, C["gold"])
            for z in (5.0, 8.5): box((s * 4.0, -2.22, z), (0.6, 0.1, 1.2), C["window"])
        pts = [(-2.0, 4.0)] + [(2.0 * math.cos(math.pi - math.pi * i / 16), 4.0 + 2.0 * math.sin(math.pi - math.pi * i / 16)) for i in range(17)] + \
              [(2.0, 4.0), (2.0, 9.0), (-2.0, 9.0)]
        poly(pts[1:18] + [(2.0, 9.0), (-2.0, 9.0)], -1.8, 1.8, C["stone"])
        box((0, -2.0, 9.4), (12.0, 0.5, 0.8), C["stone2"])
        for i in range(6): box((-3.0 + i * 1.2, -2.0, 10.2), (0.6, 0.5, 0.9), C["stone"])
        box((0, -1.95, 7.6), (1.4, 0.15, 1.2), C["gold"])          # gold leaf plaque
        for s in (-1, 1):                                            # open doors
            box((s * 2.4, -1.2, 2.6), (0.15, 2.0, 5.0), C["wood"], rot=0)
        # portcullis teeth (raised)
        for i in range(7): box((-1.8 + i * 0.6, 0.0, 7.5), (0.08, 0.08, 1.0), C["iron"])
    def house(box, cyl, sph, prism, poly, bm, h=4.5, w=4.0, d=5.0):
        box((0, 0, h / 2), (w, d, h), C["plaster"]); box((0, 0, 0.25), (w + 0.1, d + 0.1, 0.5), C["stone"])
        box((0, 0, h - 0.1), (w + 0.15, d + 0.15, 0.2), C["wood"])
        prism((0, 0, h), w, d, 2.4, C["roof"], over=0.35)
        box((w * 0.3, 0.8, h + 1.6), (0.5, 0.5, 1.8), C["stone"])
        box((0, -d / 2 - 0.02, 1.05), (0.95, 0.1, 2.1), C["wood"])
        for sx in (-1, 1):
            box((sx * w * 0.3, -d / 2 - 0.03, h * 0.62), (0.7, 0.1, 0.9), C["window"])
            box((sx * w * 0.3, d / 2 + 0.03, h * 0.62), (0.7, 0.1, 0.9), C["window"])
            box((sx * w / 2 + sx * 0.03, 0, h * 0.62), (0.1, 0.8, 0.9), C["window"])
    def tallhouse(**k): house(**k, h=7.0, w=4.4, d=5.0)
    def stall(colkey):
        def f(box, cyl, sph, prism, poly, bm):
            box((0, 0, 0.5), (3.0, 1.1, 1.0), C["wood"]); box((0, 0, 1.03), (3.2, 1.3, 0.08), C["wood"])
            for sx in (-1.45, 1.45):
                for sy in (-0.6, 0.6): box((sx, sy, 1.3), (0.1, 0.1, 2.6 if sy > 0 else 2.2), C["wood"])
            for i in range(6):                                     # striped slanted canopy
                bm_m = C[colkey] if i % 2 == 0 else C["plaster"]
                vs = box((-1.5 + 0.25 + i * 0.5, 0, 2.5), (0.5, 1.7, 0.05), bm_m)
                for v in vs: v.co.z += (v.co.y) * 0.3
            for i in range(5):
                sph((-1.1 + i * 0.55, -0.1, 1.2), 0.13, C["goods"] if i % 2 else C["fruit"], sub=1)
            box((0.9, 0.25, 1.25), (0.5, 0.35, 0.35), C["goods"])
        return f
    def bridge(box, cyl, sph, prism, poly, bm):              # spans 7 m along y, 3.6 wide (canal along x)
        n = 14
        for i in range(n):
            t0 = i / n; t1 = (i + 1) / n
            y0 = -3.5 + 7 * t0; y1 = -3.5 + 7 * t1; z0 = 0.55 * math.sin(math.pi * t0); z1 = 0.55 * math.sin(math.pi * t1)
            for x0, x1, zt, m in ((-1.8, 1.8, 0.0, C["stone"]), (-1.9, -1.6, 0.8, C["stone2"]), (1.6, 1.9, 0.8, C["stone2"])):
                vs = [bm.verts.new(p) for p in ((x0, y0, z0 - 0.35), (x1, y0, z0 - 0.35), (x1, y1, z1 - 0.35), (x0, y1, z1 - 0.35),
                                                (x0, y0, z0 + zt + 0.02), (x1, y0, z0 + zt + 0.02), (x1, y1, z1 + zt + 0.02), (x0, y1, z1 + zt + 0.02))]
                for q in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                    bm.faces.new([vs[j] for j in q]).material_index = mi_bridge(m)
        for s in (-1, 1):
            box((0, s * 1.0, -0.9), (3.6, 0.6, 1.6), C["stone"])
    _mi_cache = {}
    def mi_bridge(m): return _BRIDGE_MATS.index(m)
    # (bridge uses a fixed material list; set below)
    def statue(box, cyl, sph, prism, poly, bm):              # original "Warden of the Alders" guardian (5.5 m)
        box((0, 0, 1.2), (2.4, 2.4, 2.4), C["stone2"]); box((0, 0, 2.5), (2.0, 2.0, 0.2), C["stone"])
        S = C["statue"]
        cyl((0, 0, 2.6), 0.95, 0.45, 3.1, S, seg=12)            # long cloak/robe
        box((0, 0, 5.9), (0.95, 0.6, 1.1), S)                    # chest plate
        sph((0, 0, 6.85), 0.36, S); cyl((0, 0, 6.95), 0.42, 0.08, 0.9, S, seg=8)   # head + tall pointed helm
        for s in (-1, 1): box((s * 0.42, 0.05, 7.05), (0.06, 0.5, 0.45), S)          # cheek guards
        cyl((0.65, 0, 6.2), 0.25, 0.22, 0.25, S)                 # pauldron R
        cyl((-0.65, 0, 6.2), 0.25, 0.22, 0.25, S)
        box((-0.95, -0.25, 5.0), (0.25, 0.25, 1.4), S)           # left arm down
        rr = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.95, radius2=0.95, depth=0.14,
                                   matrix=Matrix.Translation((-1.1, -0.45, 4.7)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        for f in {f for v in rr["verts"] for f in v.link_faces}: f.material_index = mi_statue(S)
        rr = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.42, radius2=0.42, depth=0.06,
                                   matrix=Matrix.Translation((-1.1, -0.54, 4.75)) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Diagonal((0.6, 1.2, 1, 1)))
        for f in {f for v in rr["verts"] for f in v.link_faces}: f.material_index = mi_statue(C["gold"])   # leaf boss
        box((0.95, -0.2, 6.3), (0.25, 0.25, 1.2), S)             # right arm raised
        cyl((1.0, -0.25, 2.8), 0.07, 0.07, 6.2, S, seg=8)        # tall staff
        sph((1.0, -0.25, 9.25), 0.32, C["gold"])                 # lantern orb
        for k in range(4):
            a = k * math.pi / 2; box((1.0 + 0.32 * math.cos(a), -0.25 + 0.32 * math.sin(a), 9.25), (0.06, 0.06, 0.8), S)
    def banner(box, cyl, sph, prism, poly, bm):
        cyl((0, 0, 0), 0.07, 0.06, 6.0, C["wood"], seg=8); sph((0, 0, 6.05), 0.12, C["gold"])
        box((0.75, 0, 5.7), (1.6, 0.06, 0.06), C["wood"])
        n = 8
        for i in range(n):                                       # cloth strip with a gentle wave
            z1 = 5.65 - i * 0.45; z0 = z1 - 0.45
            vs = [bm.verts.new(p) for p in ((0.05, 0.03 * math.sin(i), z0), (1.45, 0.03 * math.sin(i), z0),
                                             (1.45, 0.03 * math.sin(i + 1), z1), (0.05, 0.03 * math.sin(i + 1), z1))]
            f = bm.faces.new(vs); f.material_index = mi_banner(C["banner"])
    # material index helpers for the hand-made faces
    global _BRIDGE_MATS
    _BRIDGE_MATS = [C["stone"], C["stone2"]]
    def mi_statue(m):
        return STAT_MATS.index(m)
    def mi_banner(m): return BAN_MATS.index(m)
    STAT_MATS = [C["stone2"], C["stone"], C["statue"], C["gold"]]
    BAN_MATS = [C["wood"], C["gold"], C["banner"]]
    # wrap builds whose faces use fixed lists: pre-register the materials in that order
    def pre(mlist, fn):
        def f(box, cyl, sph, prism, poly, bm):
            for m in mlist: box((0, 0, -100), (0.001, 0.001, 0.001), m)    # registers order; tiny hidden cube
            fn(box, cyl, sph, prism, poly, bm)
        return f
    module("wall", wall); module("tower", tower); module("gatehouse", gatehouse)
    module("house", lambda **k: house(**k)); module("tallhouse", lambda **k: tallhouse(**k))
    for ck in ("cloth_r", "cloth_b", "cloth_g", "cloth_y"): module("stall_" + ck[-1], stall(ck))
    module("bridge", pre(_BRIDGE_MATS, bridge)); module("statue", pre(STAT_MATS, statue)); module("banner", pre(BAN_MATS, banner))
    # strip the registration cubes
    me = MODS["banner"].objects[0].data; uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = ((v.x - 0.05) / 1.4, (v.z - 2.05) / 3.6)
    for name in ("bridge", "statue", "banner"):
        me = MODS[name].objects[0].data; bmx = bmesh.new(); bmx.from_mesh(me)
        bmesh.ops.delete(bmx, geom=[v for v in bmx.verts if v.co.z < -50], context='VERTS'); bmx.to_mesh(me); bmx.free()
    return C

def inst(name, loc, rot=0.0, scale=1.0, coll=None):
    e = bpy.data.objects.new(f"I_{name}", None); e.instance_type = 'COLLECTION'; e.instance_collection = MODS[name]
    e.location = loc; e.rotation_euler = (0, 0, rot); e.scale = (scale,) * 3
    (coll or C_CITY).objects.link(e); return e

C_CITY = None
def build_city():
    global C_CITY
    flatten_terrain()
    C_CITY = bpy.data.collections.new("Aldermoor"); scene.collection.children.link(C_CITY)
    C = build_modules()
    z = Z0
    # paving inside the walls + canal (along x at y=CANAL_Y)
    def plane(name, x0, x1, y0, y1, zz, m):
        bm = bmesh.new(); vs = [bm.verts.new((x, y, zz)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        bm.faces.new(vs); return mesh_from_bm(name, bm, [m])
    pave = brick_mat("C_Paving", (0.70, 0.68, 0.63), (0.62, 0.60, 0.56), mortar=(0.45, 0.43, 0.40), scale=0.6, rough=0.85, vertical=False)
    CY = 68.0
    plane("Paving_S", CITY_X[0], CITY_X[1], CITY_Y[0] - 0.5, CY - 2.2, z, pave)
    plane("Paving_N", CITY_X[0], CITY_X[1], CY + 2.2, CITY_Y[1], z, pave)
    water = mat("C_Water", (0.05, 0.18, 0.22), 0.05); water.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.0
    plane("Canal_Water", CITY_X[0], CITY_X[1], CY - 2.2, CY + 2.2, z - 0.9, water)
    plane("Canal_Bed", CITY_X[0], CITY_X[1], CY - 2.3, CY + 2.3, z - 1.6, C["dark"])
    for s in (-1, 1):                                      # canal walls / curbs
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(((CITY_X[0] + CITY_X[1]) / 2, CY + s * 2.35, z - 0.7)) @ Matrix.Diagonal((CITY_X[1] - CITY_X[0], 0.3, 1.5, 1)))
        ob = mesh_from_bm(f"CanalWall{s}", bm, [C["stone2"]])
    # walls: front (with gatehouse), sides, back
    gx, gy = GATE.x, GATE.y
    for x in np.arange(CITY_X[0] + 3, CITY_X[1] - 2, 6.0):
        if abs(x - gx) < 5: continue
        inst("wall", (x, gy, z))
        inst("wall", (x, CITY_Y[1], z))
    for y in np.arange(CITY_Y[0] + 3, CITY_Y[1] - 2, 6.0):
        if abs(y - CY) < 3: continue
        inst("wall", (CITY_X[0], y, z), rot=math.pi / 2); inst("wall", (CITY_X[1], y, z), rot=math.pi / 2)
    inst("gatehouse", (gx, gy, z))
    for x, y in ((CITY_X[0], gy), (CITY_X[1], gy), (CITY_X[0], CITY_Y[1]), (CITY_X[1], CITY_Y[1]), (gx - 17, gy), (gx + 17, gy),
                 (CITY_X[0], CY), (CITY_X[1], CY)):
        inst("tower", (x, y, z))
    # guardian statues flank the road outside the gate
    for s in (-1, 1):
        g = ground(gx + s * 6.0, gy - 4.0)
        inst("statue", (gx + s * 6.0, gy - 4.0, max(g, z - 0.4)), rot=0.0 if s > 0 else 0.0, scale=1.0).scale.x = s * 1.0
    # main avenue houses (gate -> canal -> market), market square around (gx, 84)
    rnd = random.Random(4)
    rows = []
    for side in (-1, 1):
        for y in np.arange(gy + 4.5, CY - 2.5, 5.6):
            rows.append((gx + side * 7.5, y, side))
        for y in np.arange(CY + 5.0, 78, 5.6):
            rows.append((gx + side * 7.5, y, side))
        for y in np.arange(gy + 4.5, CITY_Y[1] - 3, 6.0):
            rows.append((gx + side * 15.5, y, side))
    for x, y, side in rows:
        if 77 < y < 93 and abs(x - gx) < 12: continue
        if abs(y - CY) < 3.5: continue
        name = "tallhouse" if rnd.random() < 0.4 else "house"
        inst(name, (x, y, z), rot=side * math.pi / 2 + math.pi, scale=rnd.uniform(0.9, 1.1))
    # market square ring of houses
    for i in range(7):
        a = math.pi * (0.1 + 0.8 * i / 6); x = gx + 13 * math.cos(a); y = 87 + 8 * math.sin(a) + 3
        inst("tallhouse" if i % 2 else "house", (x, y, z), rot=a + math.pi / 2, scale=1.05)
    # keep: cluster of towers at the back for the skyline
    for dx, dy, sc in ((0, 0, 1.9), (-5, 1, 1.3), (5, 1, 1.3), (0, 4, 1.5)):
        inst("tower", (gx + dx, 97 + dy, z), scale=sc)
    # bridges over the canal: avenue + a side street
    inst("bridge", (gx, CY, z)); inst("bridge", (gx + 15.5, CY, z))
    # market stalls + banners
    for i, (dx, dy, col, r) in enumerate(((-6, 82, "r", 0.3), (-2, 86.5, "b", 0.0), (3, 86.5, "g", 0.0), (7, 82, "y", -0.3),
                                         (-7, 77.5, "y", 0.5), (7.5, 77.5, "b", -0.5))):
        inst("stall_" + col, (gx + dx, dy, z), rot=math.pi + r)
    for x, y, r in ((gx - 2.6, gy + 2.5, 0), (gx + 2.6, gy + 2.5, math.pi), (gx - 3.5, 76, 0), (gx + 3.5, 76, math.pi),
                    (gx - 9, 80, 0), (gx + 9, 80, math.pi), (gx - 2.5, gy - 2.6, 0), (gx + 2.5, gy - 2.6, math.pi)):
        inst("banner", (x, y, z if y > gy else ground(x, y)), rot=r)
    # banners on the gatehouse face
    for s in (-1, 1):
        e = inst("banner", (gx + s * 4.0 - 0.75, gy - 2.35, z + 2.2), rot=0.0, scale=1.0)
    # lanterns (dusk): small emissive spheres on poles along the avenue
    lm = mat("C_Lantern", (1.0, 0.7, 0.35), 0.4, emit=(1.0, 0.62, 0.25), estr=0.0)
    for y in np.arange(gy + 6, 80, 6):
        for s in (-1, 1):
            bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.05, radius2=0.05, depth=3.0,
                                                    matrix=Matrix.Translation((gx + s * 4.2, y, z + 1.5)))
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.18, matrix=Matrix.Translation((gx + s * 4.2, y, z + 3.1)))
            ob = mesh_from_bm("Lantern", bm, [lm])
    print("CITY built:", len(C_CITY.objects), "objects/instances")

def set_dusk(k=1.0):
    """dusk grade: lower warmer sun, darker sky, glowing windows and lanterns."""
    sun = bpy.data.objects["Sun"]; sun.data.energy = 7.0 * (1 - 0.8 * k); sun.data.color = (1.0, 0.55 + 0.3 * (1 - k), 0.35 + 0.4 * (1 - k))
    sun.rotation_euler.x = sun.rotation_euler.x + math.radians(8 * k)
    bg = scene.world.node_tree.nodes.get("Background")
    if bg: bg.inputs[1].default_value = bg.inputs[1].default_value * (1 - 0.65 * k)
    for n in ("C_Window", "C_Lantern"):
        b = bpy.data.materials[n].node_tree.nodes["Principled BSDF"]; b.inputs["Emission Strength"].default_value = 6.0 * k
    if "LanternLight" in bpy.data.objects: bpy.data.objects["LanternLight"].data.energy *= 1 + 2 * k


# ============================================================================= rider + gallop
NOTES2 = os.path.join(CH, "notes2.json")
def load_ocarina_rig2(notes=None):
    """ocarina_scene.py setup with a different notes file (finger animation for the new melody)."""
    src = open(OCA_PY).read()
    if notes:
        src = src.replace('NOTES = json.load(open(os.path.join(D, "notes.json")))', f'NOTES = json.load(open({notes!r}))')
    sys.argv = [sys.argv[0], "--"]
    ns = {"__name__": "ocarina_setup", "__file__": OCA_PY}
    exec(compile(src, OCA_PY, "exec"), ns)
    sys.argv = _saved
    return ns

GALLOP_N = 12
def gallop_clip(parm):
    """bounding 'lope' for the ghost panda: front pair and rear pair alternate, back flexes, body bounces."""
    D = PANDA_DEF
    def fn(f):
        t = f / GALLOP_N * 2 * math.pi; p = dict(D)
        p["root_loc"] = (0, 0, 0.05 + 0.06 * math.sin(2 * t - 0.6))
        p["root"] = (GP * 7 * math.sin(t), 0, 0)
        p["Bone_spine02"] = (GP * 6 * math.sin(t + 0.5), 0, 0)
        p["Bone_neck"] = (-GP * 5 * math.sin(t), 0, 0)
        for s, ph in (("l", 0.0), ("r", 0.45)):
            p[f"Bone_{s}f_leg_upper"] = (GL * 38 * math.sin(t + ph), 0, 0)
            p[f"Bone_{s}f_leg_lower"] = (GL * max(0.0, 45 * math.cos(t + ph)), 0, 0)
            p[f"Bone_{s}r_leg_upper"] = (GL * 34 * math.sin(t + math.pi + ph), 0, 0)
            p[f"Bone_{s}r_leg_lower"] = (-GL * max(0.0, 40 * math.cos(t + math.pi + ph)), 0, 0)
        return p
    return bake_clip(parm, "panda_gallop", GALLOP_N, fn, panda_solver)
GL = float(COPTS.get("gl", 1)); GP = float(COPTS.get("gp", 1))

def seat_rider(ns, parm, ref_frame=1, lean=8.0):
    """sit the (ocarina-rig) archer astride the panda: legs straddle, parented to the panda's mid spine."""
    arm = ns["arm"]; P_ = arm.pose.bones
    act = arm.animation_data.action
    for s, sg in (("L", 1), ("R", -1)):
        for b, e in ((f"thigh.{s}", (RX * 75, 0, sg * RZ * 28)), (f"shin.{s}", (-RX * 70, 0, 0)), (f"foot.{s}", (RX * 20, 0, 0))):
            pb = P_[b]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = [math.radians(a) for a in e]
            pb.keyframe_insert("rotation_euler", frame=1)
    P_["spine"].rotation_mode = 'XYZ'
    scene.frame_set(ref_frame)
    hip = arm.matrix_world @ P_["hips"].head
    back = parm.matrix_world @ parm.pose.bones["Bone_spine02"].head
    top = Vector((back.x, back.y, parm.matrix_world.translation.z + PANDA_H * SEAT_H))
    fwdp = parm.matrix_world.to_3x3() @ Vector((0, -1, 0)); fwdp.z = 0; top += fwdp.normalized() * SEAT_F
    Mw = arm.matrix_world.copy(); Mw.translation += (top - hip)
    arm.parent = parm; arm.parent_type = 'BONE'; arm.parent_bone = "Bone_spine02"
    arm.matrix_world = Mw
    return arm
RX = float(COPTS.get("rx", 1)); RZ = float(COPTS.get("rz", 1)); SEAT_H = float(COPTS.get("seat", 0.93)); SEAT_F = float(COPTS.get("seatf", 0.45))


# ============================================================================= LOOT
LOOT = [  # id, name, rarity, colour (beam), landing (u, v) in the summon frame
    ("buckle", "Gold-Coin Buckle", "Rare", (0.25, 0.55, 1.0), (3.55, -1.15)),
    ("comb", "Moustache Comb", "Uncommon", (0.25, 1.0, 0.3), (3.0, 0.75)),
    ("shard", "Mystery Shard", "Epic", (0.75, 0.3, 1.0), (4.1, -1.75)),
    ("coins", "12 Gold Coins", "Common", (1.0, 0.95, 0.85), (3.3, -0.2))]
LOOT_N = 216
L_DROP = (14, 20, 26, 32); L_PICK = (120, 138, 156, 174)

def loot_mesh(kind):
    C = city_materials() if "C_Gold" not in bpy.data.materials else None
    gold = bpy.data.materials["C_Gold"]
    bm = bmesh.new(); mats = [gold]
    if kind == "buckle":
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.11, radius2=0.11, depth=0.03, matrix=Matrix.Rotation(math.radians(90), 4, 'X'))
        r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.05, matrix=Matrix.Translation((0, -0.02, 0)) @ Matrix.Diagonal((1, 0.4, 1, 1)))
    elif kind == "comb":
        mats = [mat("C_Ivory", (0.92, 0.86, 0.7), 0.4)]
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, 0, 0.04)) @ Matrix.Diagonal((0.24, 0.02, 0.05, 1)))
        for i in range(9):
            bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((-0.105 + i * 0.026, 0, -0.03)) @ Matrix.Diagonal((0.012, 0.018, 0.09, 1)))
    elif kind == "shard":
        mats = [mat("C_Shard", (0.4, 0.1, 0.7), 0.1, emit=(0.7, 0.3, 1.0), estr=4.0)]
        bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.07, radius2=0.0, depth=0.22, matrix=Matrix.Translation((0, 0, 0.11)))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.07, radius2=0.0, depth=0.12, matrix=Matrix.Translation((0, 0, -0.06)) @ Matrix.Rotation(math.pi, 4, 'X'))
    else:
        for i in range(6):
            a = i * 1.1; bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.045, radius2=0.045, depth=0.012,
                                               matrix=Matrix.Translation((0.06 * math.cos(a) * (i > 2), 0.06 * math.sin(a) * (i > 2), 0.013 * (i % 3))))
    return mesh_from_bm("Loot_" + kind, bm, mats)

def beam_mat(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes; L = m.node_tree.links
    for n in list(N): N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); tr = N.new("ShaderNodeBsdfTransparent")
    mx = N.new("ShaderNodeMixShader"); tc = N.new("ShaderNodeTexCoord"); sp = N.new("ShaderNodeSeparateXYZ")
    em.inputs[0].default_value = (*col, 1); em.inputs[1].default_value = 6.0
    L.new(tc.outputs["Generated"], sp.inputs[0])
    pw = N.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.6; L.new(sp.outputs["Z"], pw.inputs[0])
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.4
    fac = N.new("ShaderNodeMath"); fac.operation = 'MAXIMUM'; L.new(pw.outputs[0], fac.inputs[0]); L.new(lw.outputs["Facing"], fac.inputs[1])
    op = N.new("ShaderNodeValue"); op.name = "opac"; op.outputs[0].default_value = 1.0
    inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L.new(fac.outputs[0], inv.inputs[1])
    mul = N.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; L.new(inv.outputs[0], mul.inputs[0]); L.new(op.outputs[0], mul.inputs[1])
    one = N.new("ShaderNodeMath"); one.operation = 'SUBTRACT'; one.inputs[0].default_value = 1.0; L.new(mul.outputs[0], one.inputs[1])
    L.new(one.outputs[0], mx.inputs[0]); L.new(em.outputs[0], mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2])
    # mix fac: 0 -> emission, 1 -> transparent ; fac = 1 - (1-max(z^.6, rim)) * opac
    L.new(mx.outputs[0], out.inputs[0])
    return m

def summon_stage():
    set_axis(BR_STOP, BR_HOME - BR_STOP)

def ko_brute(nframes, stars=True):
    barm, bbody = build_brute(); brute_clips(barm)
    ad = barm.animation_data_create(); ad.action = None
    s_ = add_strip(barm, bpy.data.actions["brute_knockout"], -60, hold=True, bin=0); s_.extrapolation = 'HOLD'
    pa = fw(0, 0); pb = fw(4.6, 0.0); db = pb - pa
    barm.location = pb; barm.rotation_euler = (0, 0, math.atan2(db.x, -db.y))
    if stars: dizzy_stars(barm, 1, nframes, n=5)
    return barm

def build_loot():
    global FRAME_END
    FRAME_END = LOOT_N
    scene.frame_start = 1; scene.frame_end = LOOT_N; scene.render.fps = FPS
    summon_stage(); city_materials()
    barm = ko_brute(LOOT_N)
    upgrade_archer(); archer_clips(ARCH)
    layout_generic(ARCH, "archer_idle", [("archer_walk", 52, {"repeat": 2.5, "bin": 4, "bout": 6})], LOOT_N)
    apath = [(1, (0.0, 0.0)), (50, (0.0, 0.0)), (112, (2.55, -0.25))]
    a = new_action("Archer_motionL"); ARCH.animation_data.action = a
    for f in range(1, LOOT_N + 1):
        u, v = path_uv(apath, f); p = fw(u, v)
        tgt = fw(3.5, -0.3) if f > 40 else fw(4.6, 0)
        d = tgt - p
        walking = 50 <= f <= 112
        yaw = math.atan2(d.x, -d.y) if walking else math.atan2(d.y, d.x)
        if 112 < f <= 126: k = smooth((f - 112) / 14); y0 = math.atan2(d.x, -d.y); y1 = math.atan2(d.y, d.x); yaw = y0 + ((y1 - y0 + math.pi) % (2 * math.pi) - math.pi) * k
        if 36 < f < 50: k = smooth((f - 36) / 14); y1 = math.atan2(d.x, -d.y); y0 = math.atan2(d.y, d.x); yaw = y0 + ((y1 - y0 + math.pi) % (2 * math.pi) - math.pi) * k
        ARCH.location = (p.x, p.y, p.z - 0.02); ARCH.rotation_euler = (0, 0, yaw)
        ARCH.keyframe_insert("location", frame=f); ARCH.keyframe_insert("rotation_euler", frame=f)
    finish_action(a)
    src = bone_world(barm, "spine", 10)
    for i, (lid, name, rar, col, (lu, lv)) in enumerate(LOOT):
        ob = loot_mesh(lid); ob.rotation_mode = 'XYZ'
        land = fw(lu, lv) + Vector((0, 0, 0.18)); f0 = L_DROP[i]; f1 = f0 + 12; fp = L_PICK[i]
        for f in range(f0, LOOT_N + 1):
            if f <= f1:
                k = (f - f0) / 12; p = src.lerp(land, k) + Vector((0, 0, 1.2 * math.sin(math.pi * k)))
            elif f < fp:
                p = land + Vector((0, 0, 0.05 * math.sin((f - f1) * 0.25)))
            else:
                k = min(1, (f - fp) / 8); hand = bone_world(ARCH, "spine", f) + Vector((0, 0, 0.1))
                p = land.lerp(hand, smooth(k)) + Vector((0, 0, 0.4 * math.sin(math.pi * k)))
            sc = 1.0 if f < fp else max(0.01, 1 - (f - fp) / 8)
            ob.location = p; ob.rotation_euler = (0.3 * math.sin(f * 0.1), 0, f * 0.12); ob.scale = (sc,) * 3
            for dp in ("location", "rotation_euler", "scale"): ob.keyframe_insert(dp, frame=f)
            if f > fp + 8: break
        key_vis(ob, [(f0, fp + 8)])
        # loot beam
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.09, radius2=0.05, depth=3.2, matrix=Matrix.Translation((0, 0, 1.6)))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.35, radius2=0.35, depth=0.01, matrix=Matrix.Translation((0, 0, 0.01)))
        bmat = beam_mat(f"M_Beam_{lid}", col)
        beam = mesh_from_bm(f"Beam_{lid}", bm, [bmat]); beam.location = fw(lu, lv); beam.visible_shadow = False
        opn = bmat.node_tree.nodes["opac"]
        for f, o in ((f1, 0.0), (f1 + 6, 1.0), (fp, 1.0), (fp + 8, 0.0)):
            opn.outputs[0].default_value = o; opn.outputs[0].keyframe_insert("default_value", frame=f)
        key_vis(beam, [(f1, fp + 8)])
        ld = bpy.data.lights.new(f"BeamL_{lid}", 'POINT'); ld.color = col; ld.shadow_soft_size = 0.2
        lo = link_ob(bpy.data.objects.new(f"BeamL_{lid}", ld)); lo.location = land + Vector((0, 0, 0.3))
        for f, e in ((f1 - 1, 0), (f1 + 4, 60), (fp, 60), (fp + 6, 0)):
            ld.energy = e; ld.keyframe_insert("energy", frame=f)
        sparks(f"Spark_Pick_{lid}", bone_world(ARCH, "spine", fp + 8) + Vector((0, 0, 0.1)), fp + 8, n=12, color=col, speed=1.5, life=10, seed=60 + i, size=0.015)
        ev(f0, "pop"); ev(f1, "loot_land", rarity=rar); ev(fp + 8, "pickup", rarity=rar)
        HUD.setdefault("loot", []).append(dict(id=lid, name=name, rarity=rar, drop=f0, land=f1, pick=fp + 8))
    for f in range(56, 112, 12): ev(f, "step", gain=0.35)
    ev(1, "stars", dur=4.0)
    # cameras: drop close-up, then wide for the walk-in/collection (action kept left of the bag UI)
    U3 = Vector((U.x, U.y, 0)); V3 = Vector((V.x, V.y, 0)); c = fw(3.6, -0.3)
    shot_cam("Cam_Loot", [
        (1, 60, c + U3 * -1.2 + V3 * -4.2 + Vector((0, 0, 1.6)), c + Vector((0, 0, 0.5)), c + U3 * -1.0 + V3 * -3.8 + Vector((0, 0, 1.5)), c + Vector((0, 0, 0.5)), 30, 32),
        (61, LOOT_N, fw(1.2, -6.4) + Vector((0, 0, 2.2)), fw(3.4, -0.6) + Vector((0, 0, 0.7)) + V3 * -0.0 + U3 * 0.6,
         fw(1.6, -5.6) + Vector((0, 0, 2.0)), fw(3.2, -0.4) + Vector((0, 0, 0.8)) + U3 * 0.8, 28, 30)])
    project_hud("loot", LOOT_N, dict(loot=HUD.get("loot", [])))


# ============================================================================= MOUNT (new melody, ghost panda appears and bows)
MOUNT_N = 176
def follow_cam(name, shots):
    """shots: [(f0, f1, fn(f) -> (loc, tgt, lens))], hard cuts, keyed every frame."""
    cd = bpy.data.cameras.new(name); cd.clip_end = 600; cd.clip_start = 0.05; cd.sensor_width = 36
    cam = link_ob(bpy.data.objects.new(name, cd)); cam.rotation_mode = 'QUATERNION'; prev = None
    for f0, f1, fn in shots:
        for f in range(f0, f1 + 1):
            loc, tg, lens = fn(f); loc = Vector(loc); loc.z = max(loc.z, ground(loc.x, loc.y) + 0.4)
            q = (Vector(tg) - loc).to_track_quat('-Z', 'Y')
            if prev is not None and prev.dot(q) < 0: q = -q
            prev = q; cam.location = loc; cam.rotation_quaternion = q; cd.lens = lens
            cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f); cd.keyframe_insert("lens", frame=f)
    for a in (cam.animation_data.action, cd.animation_data.action):
        for fc in a.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    scene.camera = cam; return cam

def ghost_panda(alpha_keys):
    parm, pbody, _ = build_panda(); panda_clips(parm); gallop_clip(parm)
    gm = ghost_material(); pbody.data.materials[0] = gm
    key_value_node(gm, "ghost_alpha", alpha_keys)
    return parm, pbody, gm

def build_mount():
    global FRAME_END
    FRAME_END = MOUNT_N; scene.frame_start = 1; scene.frame_end = MOUNT_N; scene.render.fps = FPS
    summon_stage(); city_materials()
    barm = ko_brute(MOUNT_N)
    pa = fw(2.55, -0.25); pspawn = fw(3.4, 2.4)
    h = (pspawn - pa); h.z = 0; h.normalize(); perp = (-h).cross(Vector((0, 0, 1)))
    face = (h * math.cos(math.radians(28)) + perp * math.sin(math.radians(28))).normalized()
    ARCH.location = (pa.x, pa.y, pa.z - 0.02); ARCH.rotation_euler = (0, 0, math.radians(55)); bpy.context.view_layer.update()
    ns = load_ocarina_rig2(NOTES2)
    ARCH.rotation_euler = (0, 0, math.atan2(face.x, -face.y)); bpy.context.view_layer.update()
    strip_finger_keys(ns, after=168)
    ctrl_keys(ns, [(1, 0.15), (12, 0.15), (30, 1.0), (166, 1.0), (176, 0.4)])
    ocarina_glow(ns, [(1, 4.0), (40, 6.0), (70, 14.0), (115, 14.0), (130, 5.0), (MOUNT_N, 4.0)])
    parm, pbody, gm = ghost_panda([(1, 0.0), (88, 0.0), (122, 1.0), (MOUNT_N, 1.0)])
    layout_generic(parm, "panda_idle", [("panda_respect_bow", 132, {"hold": False})], MOUNT_N)
    d = pa - pspawn; parm.location = pspawn; parm.rotation_euler = (0, 0, math.atan2(d.x, -d.y) + math.radians(20))
    key_vis(pbody, [(86, MOUNT_N)])
    oc = ns["oc"]; OCP = {}
    for f in range(1, MOUNT_N + 1): scene.frame_set(f); OCP[f] = oc.matrix_world.translation.copy()
    tgt_pts = mesh_points(pbody, 200, seed=8, frame=120)
    src = [OCP[70] + Vector((random.uniform(-.05, .05), random.uniform(-.05, .05), random.uniform(-.05, .05))) for _ in range(40)]
    spirit_stream("Summon2", src, lambda f, T=tgt_pts: T[(f * 7) % len(T)], 66, 120, n=60, seed=31, swirl_r=0.6, turns=1.3)
    sparks("Spark_Mat2", pspawn + Vector((0, 0, 0.8)), 118, n=24, color=(0.6, 0.95, 1.0), speed=2.2, life=14, seed=32, size=0.02)
    ev(66, "shimmer", dur=2.4); ev(118, "chime"); ev(120, "whoosh", dur=0.6, gain=0.5, pitch=0.8); ev(150, "roar", gain=0.5)
    U3 = Vector((U.x, U.y, 0)); V3 = Vector((V.x, V.y, 0))
    side = face.cross(Vector((0, 0, 1)))
    mid = pa.lerp(pspawn, 0.5)
    follow_cam("Cam_Mount", [
        (1, 80, lambda f: (pa + face * (3.2 - 0.6 * f / 80) + side * 0.8 + Vector((0, 0, 1.5)), pa + Vector((0, 0, 1.3)), 40)),
        (81, MOUNT_N, lambda f: (mid + perp * (6.2 - 0.6 * (f - 81) / 95) + Vector((0, 0, 1.6)),
                                 mid + Vector((0, 0, 0.9)), 30))])
    project_hud("mount", MOUNT_N, dict(melody=dict(file="melody2.wav", f0=1, f1=172)))

# ============================================================================= RIDE (gallop to the gates of Aldermoor)
def catmull(pts, n_per=24):
    P = [Vector((*p, 0)) for p in pts]; P = [P[0]] + P + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        for k in range(n_per):
            t = k / n_per; p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2]); return out

def path_table(pts):
    S = [0.0]
    for a, b in zip(pts, pts[1:]): S.append(S[-1] + (b - a).length)
    return S
def at_s(pts, S, s):
    s = max(0, min(S[-1], s)); i = max(0, min(len(S) - 2, int(np.searchsorted(S, s) - 1)))
    k = (s - S[i]) / max(1e-6, S[i + 1] - S[i]); p = pts[i].lerp(pts[i + 1], k); t = (pts[i + 1] - pts[i]).normalized()
    return p, t

def speed_profile(L, vmax, a_up=4.0, a_dn=2.6, vend=0.0, start_v=0.0, hold=20):
    s = 0.0; v = start_v; out = []
    while s < L - 1e-3 and len(out) < 2000:
        brake = (v * v - vend * vend) / (2 * a_dn)
        if L - s <= brake + 0.05: v = max(vend if vend > 0 else 0.35, v - a_dn / FPS)
        else: v = min(vmax, v + a_up / FPS)
        s = min(L, s + v / FPS); out.append((s, v))
    for _ in range(hold): out.append((L, 0.0))
    return out

def mount_and_ride(waypts, vmax, start_v=0.0, vend=0.0, hold=20, nmax=None):
    """ghost panda follows a smooth path with a physical speed profile; gallop phase follows distance travelled
    (stride 2.75 m per 12-frame cycle) and fades into idle when slow -> minimal paw sliding."""
    pts = catmull(waypts); S = path_table(pts)
    prof = speed_profile(S[-1], vmax, start_v=start_v, vend=vend, hold=hold)
    if nmax: prof = prof[:nmax]
    N = len(prof)
    parm, pbody, gm = ghost_panda([(1, 1.0)])
    ad = parm.animation_data_create(); ad.action = None
    base = add_strip(parm, bpy.data.actions["panda_idle"], 1, repeat=math.ceil(N / 48) + 2, bin=0, bout=0); base.extrapolation = 'HOLD'
    gs = add_strip(parm, bpy.data.actions["panda_gallop"], 1, repeat=400, bin=0, bout=0)
    gs.use_animated_time = True; gs.use_animated_influence = True
    a = new_action("Panda_rideMotion"); ad.action = a
    phase = 0.0; POS = {}
    for i, (sd, v) in enumerate(prof):
        f = i + 1
        p, t = at_s(pts, S, sd); pz = Vector((p.x, p.y, 0)); fwd = Vector((t.x, t.y, 0)).normalized()
        zf = ground(*(pz + fwd * 1.0).xy); zb = ground(*(pz - fwd * 1.0).xy)
        loc = Vector((p.x, p.y, min(ground(p.x, p.y), (zf + zb) / 2)))
        parm.location = loc; parm.rotation_euler = (0, 0, math.atan2(fwd.x, -fwd.y))
        parm.keyframe_insert("location", frame=f); parm.keyframe_insert("rotation_euler", frame=f)
        phase += v / 2.75 * GALLOP_N / FPS
        gs.strip_time = 1 + (phase % (GALLOP_N * 300)); gs.keyframe_insert("strip_time", frame=f)
        gs.influence = max(0.0, min(1.0, (v - 0.3) / 1.6)); gs.keyframe_insert("influence", frame=f)
        POS[f] = (loc.copy(), fwd.copy(), v)
    fc = a.fcurves.find("rotation_euler", index=2); prev = None
    for kp in fc.keyframe_points:
        if prev is not None:
            while kp.co[1] - prev > math.pi: kp.co[1] -= 2 * math.pi
            while kp.co[1] - prev < -math.pi: kp.co[1] += 2 * math.pi
        prev = kp.co[1]
    finish_action(a)
    for fcv in gs.fcurves:
        for kp in fcv.keyframe_points: kp.interpolation = 'LINEAR'
    # rider (ocarina rig, ocarina lowered = reins), seated
    p1, f1_, _ = POS[1]
    ARCH.location = p1; ARCH.rotation_euler = (0, 0, math.radians(55)); bpy.context.view_layer.update()
    ns = load_ocarina_rig2(NOTES2)
    strip_finger_keys(ns); ctrl_keys(ns, [(1, 0.05), (N, 0.05)])
    ocarina_glow(ns, [(1, 3.0), (N, 3.0)])
    scene.frame_set(1); ARCH.rotation_euler = (0, 0, parm.rotation_euler.z); bpy.context.view_layer.update()
    seat_rider(ns, parm)
    # small dust puffs at the paws while galloping + paw beats for the SFX
    last = -99
    for f in range(1, N + 1):
        if POS[f][2] > 2.0 and f - last >= 6:
            ev(f, "paw", gain=min(1.0, POS[f][2] / 5.5)); last = f
        elif 0.4 < POS[f][2] <= 2.0 and f - last >= 12:
            ev(f, "paw", gain=0.4); last = f
    return parm, POS, N, ns

RIDE_WAY = None
def build_ride():
    global FRAME_END
    summon_stage(); build_city(); scene.view_settings.exposure = 0.25
    start = fw(3.4, 2.4)
    way = [tuple(start.xy), (1.0, 19.2), (2.5, 22.2), (3.6, 24.6), (4.4, 27.5), (2.8, 33.0), (3.2, 41.0), (7.0, 49.0), (10.0, 52.4)]
    parm, POS, N, ns = mount_and_ride(way, 5.8, start_v=0.0, vend=0.0, hold=26)
    global RIDE_PARM; RIDE_PARM = parm
    FRAME_END = N; scene.frame_start = 1; scene.frame_end = N; scene.render.fps = FPS
    def sm(f, k=10):
        fs = [POS[min(N, max(1, g))] for g in range(f - k, f + k + 1)]
        return sum((x[0] for x in fs), Vector()) / len(fs), sum((x[1] for x in fs), Vector()).normalized()
    up = Vector((0, 0, 1))
    def s1(f):
        p, t = sm(f); side = t.cross(up)
        return p + side * 6.2 - t * 0.8 + Vector((0, 0, 1.7)), p + t * 1.2 + Vector((0, 0, 1.45)), 32
    def s2(f):
        p, t = sm(f); side = t.cross(up)
        return p + t * 7.5 - side * 1.8 + Vector((0, 0, 1.0)), p + Vector((0, 0, 1.3)), 32
    gate = Vector((GATE.x, GATE.y + 0.5, Z0 + 6.0)); CAMG = Vector((3.4, 41.6, 0))
    def s3(f):
        p, t = sm(f, 6); k = smooth(min(1, (f - c2) / max(1, N - c2)))
        c = CAMG + Vector((1.6 * k, 2.6 * k, 0)); c.z = ground(c.x, c.y) + 1.6 - 0.3 * k
        return c, p.lerp(gate, 0.38) + Vector((0, 0, 0.5)), 22
    c1 = 84; c2 = 156
    follow_cam("Cam_Ride", [(1, c1, s1), (c1 + 1, c2, s2), (c2 + 1, N, s3)])
    thin_grass_near_camera({f: (scene.camera.location, None, None) for f in [1]} if False else {})
    ev(1, "whoosh", dur=0.6, gain=0.5, pitch=0.7); ev(c2 + 30, "fanfare"); ev(N - 20, "city", dur=3.0)
    project_hud("ride", N, dict(hero_frame=N - 8, cuts=[c1 + 1, c2 + 1]))
    return N

# ============================================================================= CITY (canal bridge -> market square)
def build_city_shot():
    global FRAME_END
    build_city(); scene.view_settings.exposure = 0.25
    way = [(10.0, 61.0), (10.0, 66.0), (10.0, 70.0), (10.0, 74.0), (9.6, 77.5)]
    parm, POS, N, ns = mount_and_ride(way, 2.4, start_v=2.0, vend=0.0, hold=24)
    FRAME_END = N; scene.frame_start = 1; scene.frame_end = N; scene.render.fps = FPS
    up = Vector((0, 0, 1))
    c1 = min(N - 30, 88)
    def s1(f):
        p, t, _ = POS[f]
        return p - t * 5.5 + Vector((0, 0, 3.4)), p + t * 4.0 + Vector((0, 0, 1.0)), 30
    def s2(f):
        p, t, _ = POS[f]
        return Vector((15.5, 85.5, Z0 + 2.4)), p.lerp(Vector((10, 82, Z0)), 0.2) + Vector((0, 0, 1.3)), 34
    follow_cam("Cam_City", [(1, c1, s1), (c1 + 1, N, s2)])
    ev(1, "city", dur=N / FPS); ev(int(N * 0.3), "bridge")
    project_hud("city", N, dict(cuts=[c1 + 1]))
    return N


# ============================================================================= VENDORS (simple original NPCs) + montage stills
VENDORS = [  # stall index (dx, dy, rot) from build_city, name, robe colour, accent
    ((-6, 82, 0.3), "Mira the Jeweler", (0.2, 0.45, 0.3), (0.95, 0.75, 0.2), "mira"),
    ((-2, 86.5, 0.0), "Old Tobin, Barber & Curios", (0.42, 0.26, 0.14), (0.85, 0.8, 0.7), "tobin"),
    ((3, 86.5, 0.0), "Seer Ilvane", (0.12, 0.14, 0.42), (0.7, 0.4, 1.0), "seer")]

def build_vendor(kind, robe, accent, M):
    bm = bmesh.new(); mats = [mat("V_Robe_" + kind, robe, 0.8), mat("V_Skin", (0.86, 0.62, 0.48), 0.6), mat("V_Acc_" + kind, accent, 0.4, metal=0.6 if kind == "mira" else 0.0),
                              mat("V_Dark", (0.04, 0.03, 0.03), 0.5), mat("V_White", (0.92, 0.92, 0.9), 0.7),
                              mat("V_Orb", (0.6, 0.35, 1.0), 0.2, emit=(0.6, 0.3, 1.0), estr=6.0), mat("V_Wood", (0.35, 0.2, 0.1), 0.8)]
    def add(geom_fn, mi):
        before = set(bm.faces); geom_fn(); [setattr(f, "material_index", mi) for f in set(bm.faces) - before]
    T = Matrix.Translation; Rx = lambda a: Matrix.Rotation(math.radians(a), 4, 'X')
    add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.4, radius2=0.22, depth=1.15, matrix=T((0, 0, 0.58))), 0)
    add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.23, radius2=0.2, depth=0.42, matrix=T((0, 0, 1.36))), 0)
    add(lambda: bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.17, matrix=T((0, 0, 1.73))), 1)
    for sx in (-1, 1):
        add(lambda sx=sx: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.07, radius2=0.06, depth=0.5, matrix=T((sx * 0.24, -0.18, 1.33)) @ Rx(60)), 0)
        add(lambda sx=sx: bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.065, matrix=T((sx * 0.24, -0.4, 1.2))), 1)
        add(lambda sx=sx: bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.022, matrix=T((sx * 0.06, -0.155, 1.76))), 3)
    if kind == "mira":
        add(lambda: bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.19, matrix=T((0, 0.04, 1.79)) @ Matrix.Diagonal((1, 1, 0.9, 1))), 6)
        add(lambda: bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.1, matrix=T((0, 0.17, 1.92))), 6)
        add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.2, radius2=0.2, depth=0.03, matrix=T((0, -0.02, 1.53))), 2)
        add(lambda: bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.04, matrix=T((0, -0.21, 1.47))), 5)
    elif kind == "tobin":
        add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.12, radius2=0.01, depth=0.3, matrix=T((0, -0.12, 1.52)) @ Rx(180)), 4)
        for sx in (-1, 1):
            add(lambda sx=sx: bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.035, radius2=0.01, depth=0.16, matrix=T((sx * 0.08, -0.17, 1.66)) @ Matrix.Rotation(math.radians(sx * 80), 4, 'Y')), 4)
        add(lambda: bmesh.ops.create_cube(bm, size=1, matrix=T((0, -0.3, 0.95)) @ Matrix.Diagonal((0.5, 0.04, 0.8, 1))), 4)
    else:
        add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.24, radius2=0.0, depth=0.6, matrix=T((0, 0.04, 1.98)) @ Rx(-12)), 0)
        add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.025, radius2=0.025, depth=2.1, matrix=T((0.45, -0.25, 1.05))), 6)
        add(lambda: bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.1, matrix=T((0.45, -0.25, 2.15))), 5)
    bm.transform(M)
    ob = mesh_from_bm("Vendor_" + kind, bm, mats)
    if kind == "seer":
        ld = bpy.data.lights.new("OrbLight", 'POINT'); ld.energy = 25; ld.color = (0.7, 0.45, 1.0)
        lo = link_ob(bpy.data.objects.new("OrbLight", ld)); lo.location = M @ Vector((0.45, -0.25, 2.15))
    return ob

def stall_frame(dx, dy, r):
    th = math.pi + r; R = Matrix.Rotation(th, 4, 'Z')
    o = Vector((GATE.x + dx, dy, Z0)); return (lambda lx, ly, lz=0.0: o + (R @ Vector((lx, ly, lz)))), th

def build_stills():
    build_city(); scene.view_settings.exposure = 0.25
    ARCH.location = (10, 70, Z0); ARCH.rotation_euler = (0, 0, math.radians(55)); bpy.context.view_layer.update()
    ns = load_ocarina_rig2(NOTES2); strip_finger_keys(ns); ctrl_keys(ns, [(1, 0.1), (10, 0.1)])
    shots = []
    for (dx, dy, r), name, robe, acc, kind in VENDORS:
        L, th = stall_frame(dx, dy, r)
        build_vendor(kind, robe, acc, Matrix.Translation(L(0, 0.85)) @ Matrix.Rotation(th, 4, 'Z'))
        shots.append((kind, L))
    return ns, shots

def place_archer_at(L):
    p = L(0.75, -1.45); h = L(0, 1.0) - p; h.z = 0; h.normalize()
    ARCH.location = (p.x, p.y, Z0 - 0.02); ARCH.rotation_euler = (0, 0, math.atan2(h.x, -h.y)); bpy.context.view_layer.update()

# ============================================================================= main dispatch (filled below)

def cam_at(loc, tgt, lens=35, name="CamTest"):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 600; cd.clip_start = 0.05
    cam = link_ob(bpy.data.objects.new(name, cd)); cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); scene.camera = cam; return cam

if CMODE == "citytest":
    build_city()
    for o in bpy.data.objects:
        if o.type == 'MESH' and not o.hide_render:
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            if all(min(v[i] for v in bb) <= (10, 40, 2.6)[i] <= max(v[i] for v in bb) for i in range(3)): print("CAMINSIDE", o.name)
    views = [((4.5, 42, 2.8), (10, 57, 6), 30), ((10, 61, 2.4), (10, 85, 3), 28), ((10, 74, 3.0), (10, 88, 1.5), 30),
             ((-34, 34, 14), (10, 78, 4), 35)]
    for i, (l, t, lens) in enumerate(views):
        cam_at(l, t, lens)
        if i == 3: set_dusk(1.0)
        still(os.path.join(CH, "tmp", f"city_{i}.png"), 1, (640, 360), 8)

if CMODE == "ridetest":
    parm, pbody, _ = build_panda(); panda_clips(parm); gallop_clip(parm)
    pbody.data.materials[0] = ghost_material()
    pp = fw(0, 0); parm.location = pp; parm.rotation_euler = (0, 0, 0)
    ARCH.location = pp; ARCH.rotation_euler = (0, 0, math.radians(55)); bpy.context.view_layer.update()
    ns = load_ocarina_rig2()
    strip_finger_keys(ns); ctrl_keys(ns, [(1, 0.0), (100, 0.0)])
    ad = parm.animation_data_create(); s_ = add_strip(parm, bpy.data.actions["panda_gallop"], 1, repeat=10, bin=0, bout=0)
    ARCH.rotation_euler = (0, 0, 0); bpy.context.view_layer.update()
    seat_rider(ns, parm)
    cam_at(pp + Vector((4.5, -1.0, 1.3)), pp + Vector((0, 0, 1.0)), 35)
    for f in (1, 4, 7, 10):
        still(os.path.join(CH, "tmp", f"ride_{f}.png"), f, (480, 270), 8)

if CMODE == "loot":
    build_loot()
    if "preview" in CACTS: preview("loot", [int(x) for x in COPTS.get("frames", "20,45,90,125,150,200").split(",")])
    if "anim" in CACTS: render_frames("loot", 1, LOOT_N)

if CMODE == "mount":
    build_mount()
    if "preview" in CACTS: preview("mount", [int(x) for x in COPTS.get("frames", "40,100,125,160").split(",")])
    if "anim" in CACTS: render_frames("mount", 1, MOUNT_N)
if CMODE == "ride":
    N_ = build_ride()
    if "preview" in CACTS: preview("ride", [int(x) for x in COPTS.get("frames", "20,60,110,150,200,%d" % (N_ - 8)).split(",")])
    if "anim" in CACTS: render_frames("ride", 1, N_)
    if "still" in CACTS or "herotest" in CACTS:
        sf = int(COPTS.get("sframe", N_ - 8)); scene.frame_set(sf)
        pe = RIDE_PARM.matrix_world.translation.copy(); print("HERO panda at", pe)
        hc = Vector((pe.x - 4.2, pe.y - 7.4, 0)); hc.z = ground(hc.x, hc.y) + 0.9
        cd = bpy.data.cameras.new("HeroCam"); cd.lens = 22; cd.clip_end = 600
        hcam = link_ob(bpy.data.objects.new("HeroCam", cd)); hcam.location = hc
        hcam.rotation_mode = 'QUATERNION'; hcam.rotation_quaternion = (Vector((pe.x + 0.9, pe.y + 2.0, Z0 + 3.0)) - hc).to_track_quat('-Z', 'Y')
        scene.camera = hcam
        if "herotest" in CACTS: still(os.path.join(CH, "tmp", "hero_test.png"), sf, (960, 540), 8)
        else: still(os.path.join(CH, "hero_gate_arrival_1920x1080.png"), sf, (1920, 1080), int(COPTS.get("ssamples", 32)))
if CMODE == "city":
    N_ = build_city_shot()
    if "preview" in CACTS: preview("city", [int(x) for x in COPTS.get("frames", "20,70,100,%d" % (N_ - 10)).split(",")])
    if "anim" in CACTS: render_frames("city", 1, N_)

if CMODE == "stills":
    ns_, shots_ = build_stills()
    res_ = (640, 360) if "preview" in CACTS else (1280, 720); spp_ = 8 if "preview" in CACTS else int(COPTS.get("ssamples", 16))
    outd = os.path.join(CH, "tmp") if "preview" in CACTS else os.path.join(CH, "stills"); os.makedirs(outd, exist_ok=True)
    for kind, L in shots_:
        fn = os.path.join(outd, f"vendor_{kind}.png")
        if os.path.exists(fn) and "preview" not in CACTS: continue
        place_archer_at(L)
        cam_at(L(-1.5, -3.1, 1.65), L(0.4, 0.45, 1.45), 30)
        still(fn, 1, res_, spp_)
    fn = os.path.join(outd, "dusk_skyline.png")
    if not os.path.exists(fn) or "preview" in CACTS:
        ARCH.location = (10, 75, Z0 - 0.02); bpy.context.view_layer.update()
        set_dusk(1.0); cam_at((-30, 40, 22), (10, 80, 3), 35); still(fn, 1, res_, spp_)

# ============================================================================= MODE export: Aldermoor module kit + ghost panda with gallop
def export_flat_material(m):
    """glTF/FBX friendly copy: flat export_color (or image texture for the banner emblem)."""
    em = bpy.data.materials.new(m.name + "_x"); em.use_nodes = True
    N = em.node_tree.nodes; L = em.node_tree.links; b = N["Principled BSDF"]
    sb = m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
    col = m.get("export_color") or (tuple(sb.inputs["Base Color"].default_value)[:3] if sb else (0.8, 0.8, 0.8))
    b.inputs["Base Color"].default_value = (*col, 1)
    if sb:
        for k in ("Roughness", "Metallic", "Emission Strength"): b.inputs[k].default_value = sb.inputs[k].default_value
        b.inputs["Emission Color"].default_value = sb.inputs["Emission Color"].default_value
    img = next((n.image for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if m.use_nodes else None
    if img:
        tx = N.new("ShaderNodeTexImage"); tx.image = img; L.new(tx.outputs[0], b.inputs["Base Color"])
        tx.interpolation = 'Closest'
    return em

def export_chapter2():
    ex = os.path.join(CH, "exports"); os.makedirs(ex, exist_ok=True); vl = bpy.context.view_layer
    for o in vl.objects:
        try: o.hide_set(True); o.select_set(False)
        except Exception: pass
    build_modules()
    kit = bpy.data.collections.new("Aldermoor_Kit"); scene.collection.children.link(kit)
    x = 0.0; cache = {}; made = []
    order = ["wall", "tower", "gatehouse", "house", "tallhouse", "stall_r", "stall_b", "stall_g", "stall_y", "bridge", "statue", "banner"]
    for name in order:
        if name not in MODS: continue
        for src in MODS[name].objects:
            if src.type != 'MESH': continue
            me = src.data.copy(); ob = bpy.data.objects.new("Aldermoor_" + name, me); kit.objects.link(ob)
            for i, m in enumerate(me.materials):
                if m is None: continue
                if m.name not in cache: cache[m.name] = export_flat_material(m)
                me.materials[i] = cache[m.name]
            w = max(2.0, ob.dimensions.x)
            ob.location = (x + w / 2, 0, 0); x += w + 2.0; made.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in made: ob.select_set(True)
    vl.objects.active = made[0]
    base = os.path.join(ex, "aldermoor_modules")
    bpy.ops.export_scene.gltf(filepath=base + ".glb", export_format='GLB', use_selection=True, export_yup=True,
                              export_animations=False, export_lights=False, export_cameras=False)
    bpy.ops.export_scene.fbx(filepath=base + ".fbx", use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             object_types={'MESH'}, path_mode='COPY', embed_textures=True, mesh_smooth_type='FACE')
    print("EXPORTED kit", [o.name for o in made])
    for ob in made: ob.hide_set(True)
    # ghost panda with the new gallop clip (same rig/material as ../sequel/exports/panda_ghost_rigged + gallop)
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)
    parm, pbody, _ = build_panda(); panda_clips(parm); gallop_clip(parm)
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
    _export(parm, pbody, clips, os.path.join(ex, "panda_ghost_mount_gallop"), vl)

if CMODE == "export":
    export_chapter2()

# ============================================================================= MODE establish: crane reveal of Aldermoor (camera only)
EST_N = 120
if CMODE == "establish":
    build_city(); scene.view_settings.exposure = 0.25
    FRAME_END = EST_N; scene.frame_start = 1; scene.frame_end = EST_N; scene.render.fps = FPS
    A0, T0, A1, T1 = Vector((7.0, 43.0, 0)), Vector((10, 57, 4.0)), Vector((4.5, 31.0, 0)), Vector((10, 76, 5.0))
    def est(f):
        k = smooth((f - 1) / (EST_N - 1)); c = A0.lerp(A1, k); c.z = ground(c.x, c.y) + 1.4 + 10.0 * k
        return c, T0.lerp(T1, k), 30 - 4 * k
    follow_cam("Cam_Est", [(1, EST_N, est)])
    ev(1, "city", dur=EST_N / FPS); ev(30, "fanfare")
    project_hud("establish", EST_N, dict(title=dict(text="ALDERMOOR", sub="the White City by the River", f0=28, f1=110)))
    if "preview" in CACTS: preview("establish", [1, 60, 120])
    if "anim" in CACTS: render_frames("establish", 1, EST_N)

if CMODE == "ride1":     # re-render of the side-tracking shot (frames 1-84) with a wider framing (rider's head was cropped)
    N_ = build_ride()
    if "preview" in CACTS: preview("ride1", [30, 70])
    if "anim" in CACTS: render_frames("ride1", 1, 84)
