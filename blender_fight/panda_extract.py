"""Extract the stock Panda3D panda (models/panda-model + models/panda-walk4) into a JSON intermediate
(mesh, UVs, skin weights, joint hierarchy with bind matrices, per-frame local joint matrices).
Run with a python that has panda3d installed:  python panda_extract.py out.json
"""
import sys, json
from panda3d.core import loadPrcFileData
loadPrcFileData('', 'window-type none\naudio-library-name null')
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import GeomVertexReader, CharacterJoint

base = ShowBase()
a = Actor("models/panda-model", {"walk": "models/panda-walk4"})
bundle = a.getPartBundle("modelRoot")

def m2l(m):  # row-major LMatrix4 (row-vector convention) -> nested list
    return [[m.getCell(r, c) for c in range(4)] for r in range(4)]

joints, order = {}, []
def walk(group, parent):
    for i in range(group.getNumChildren()):
        ch = group.getChild(i)
        if isinstance(ch, CharacterJoint):
            joints[ch.getName()] = dict(parent=parent, bind=m2l(ch.getDefaultValue()), obj=ch)
            order.append(ch.getName())
            walk(ch, ch.getName())
        else:
            walk(ch, parent)
walk(bundle, None)

nf = a.getNumFrames("walk")
frames = {n: [] for n in order}
for f in range(nf):
    a.pose("walk", f)
    a.update(force=True)
    bundle.forceUpdate()
    for n in order:
        frames[n].append(m2l(joints[n]["obj"].getTransform()))

verts, norms, uvs, weights, tris = [], [], [], [], []
for gnp in a.findAllMatches("**/+GeomNode"):
    gn = gnp.node()
    netm = gnp.getMat(a)
    for gi in range(gn.getNumGeoms()):
        g = gn.getGeom(gi)
        vd = g.getVertexData()
        off = len(verts)
        rv = GeomVertexReader(vd, "vertex"); rn = GeomVertexReader(vd, "normal")
        rt = GeomVertexReader(vd, "texcoord"); rb = GeomVertexReader(vd, "transform_blend")
        table = vd.getTransformBlendTable()
        for i in range(vd.getNumRows()):
            p = netm.xformPoint(rv.getData3()); verts.append([p[0], p[1], p[2]])
            n = rn.getData3(); norms.append([n[0], n[1], n[2]])
            t = rt.getData2(); uvs.append([t[0], t[1]])
            bl = table.getBlend(rb.getData1i())
            w = {}
            for k in range(bl.getNumTransforms()):
                w[bl.getTransform(k).getJoint().getName()] = w.get(bl.getTransform(k).getJoint().getName(), 0) + bl.getWeight(k)
            weights.append(w)
        dg = g.decompose()
        for pi in range(dg.getNumPrimitives()):
            pr = dg.getPrimitive(pi)
            for k in range(pr.getNumPrimitives()):
                s, e = pr.getPrimitiveStart(k), pr.getPrimitiveEnd(k)
                tris.append([off + pr.getVertex(j) for j in range(s, e)])

out = dict(joints=[dict(name=n, parent=joints[n]["parent"], bind=joints[n]["bind"]) for n in order],
           fps=a.getFrameRate("walk"), num_frames=nf, frames=frames,
           verts=verts, normals=norms, uvs=uvs, weights=weights, tris=tris)
json.dump(out, open(sys.argv[1], "w"))
print("joints", len(order), "verts", len(verts), "tris", len(tris), "frames", nf)
import numpy as np
V = np.array(verts); print("bounds", V.min(0), V.max(0))
