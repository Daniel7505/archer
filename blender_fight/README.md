# Archer vs Panda: an evenly matched duel in the golden-hour meadow

A ~17.5 s Cycles cinematic plus game-ready rigs. Everything is scripted. `fight_scene.py` loads `../scene.blend`
(made by `../build_scene.py`, which is not modified) and adds the stock Panda3D panda, the fight animation, the FX,
the camera and the renders.

| File | What it is |
|---|---|
| `fight.mp4` | 1280x720 native, 24 fps, 420 frames (17.5 s). H.264 video with AAC audio (the synthesized SFX) |
| `fight_hero_1920x1080.png` | Hero still of the clash (frame 317): the arrow meets the lightning in mid-air |
| `fight_scene.py` | Builds the whole shot. Actions: `save check preview anim still export` |
| `panda_extract.py` | Panda3D-side converter: stock `models/panda-model` + `models/panda-walk4` -> `panda_src/panda.json` |
| `panda_src/` | `panda.json` (mesh, UVs, skin weights, 42 joints, 61-frame walk) and the stock `panda-model.jpg` texture |
| `make_sfx.py` | numpy synth: `events.json` (written by fight_scene.py) -> `fight_sfx.wav` |
| `exports/archer_rigged.glb/.fbx` | Archer, 19-bone rig, 8 clips |
| `exports/panda_rigged.glb/.fbx` | Panda, 43-bone rig (stock skeleton + `root`), textured, 9 clips |
| `fight.blend` | The saved, fully built scene (compressed) |

## Rebuild
```
B=/workspace/blender/blender-4.2.23-linux-x64/blender
/path/to/python-with-panda3d panda_extract.py panda_src/panda.json   # only when re-converting the panda
cd ..   # archer_scene/
$B -b scene.blend -P fight/fight_scene.py -- check save            # framing/obstruction check + events.json
$B -b scene.blend -P fight/fight_scene.py -- anim samples=6 volume=0 res=1280x720
$B -b scene.blend -P fight/fight_scene.py -- still sframe=317 ssamples=48 volume=0
$B -b scene.blend -P fight/fight_scene.py -- export
cd fight && python3 make_sfx.py
ffmpeg -framerate 24 -i frames/f_%04d.png -i fight_sfx.wav -c:v libx264 -pix_fmt yuv420p -crf 17 -c:a aac -b:a 192k -shortest fight.mp4
```

## Panda conversion
panda3d-gltf and blend2bam cannot go from egg to glTF, so `panda_extract.py` uses the Panda3D Python API directly.
It loads the stock Actor, walks the `CharacterJoint` hierarchy (bind matrices from `getDefaultValue`), reads the
vertex data with its `TransformBlendTable` (real per-vertex joint weights, up to 4 joints), and samples the local
joint matrices for all 61 frames of `panda-walk4`. `fight_scene.build_panda()` then rebuilds the mesh, UVs,
custom normals, texture, a 42-joint armature (plus a new `root` bone, because the stock rig has separate hips and
shoulders roots) and the walk action. Each bone's rest matrix is the joint's bind matrix. The pose bases are solved
so that deform == `N(f) @ N_bind^-1`, which is exactly Panda3D's skinning. **The original rig, weights and walk
cycle are preserved.** Nothing was rebuilt or auto-weighted. The panda is scaled to 1.45 m tall and about 2.9 m long,
a heavy bruiser against the agile 1.9 m archer.

## Beat sheet (t = (frame-1)/24)
| Time | Frames | Beat |
|---|---|---|
| 0.0-2.3 s | 1-56 | Standoff. The panda walks in along the path in front of the practice target. The archer holds full draw |
| 2.9 s | 70 | Arrow 1 is loosed (twang and whoosh). The panda reads the draw and **rolls aside** (64-82). The arrow skims past and thunks into the practice target (3.3 s, frame 80). **Near miss** |
| 4.0-4.7 s | 96-114 | The panda rears up and **lightning** cracks from its jaws (zap and blue light flash) |
| 4.75 s | 115 | The archer's sidestep comes too late. The bolt **clips his bow shoulder** (sparks), and he staggers. *Panda 1-0* |
| 6.4-6.5 s | 154-158 | Arrow 2 **bonks off the panda's shoulder** (thick fur, cartoon "bonk"), and the panda flinches. *1-1* |
| 7.5-8.4 s | 180-204 | The panda charges |
| 8.5-9.3 s | 204-226 | **Spin kick**: a 360° airborne spin with the hind legs out. The archer dives aside (211-231), and the kick whooshes about 2 m past. **Near miss** |
| 10.1-10.2 s | 244-246 | The archer **counters** at point-blank range: another bonk on the flank. *Archer 2-1* |
| 11.0-12.3 s | 266-296 | Both reset. The panda backs off and the archer steps back in |
| 12.3-13.0 s | 296-314 | The panda rears again while the archer draws. **Both fire at the same instant** |
| 13.1 s | 316 | The arrow meets the lightning in mid-air: an energy burst, shock ring and sparks (boom). **Both are knocked back** (317-340). *2-2* |
| 14.8-16.8 s | 356-404 | Silence, then a mutual **respect bow** (chime). The camera pulls back over the meadow. It's a draw. End at 17.5 s |

## Game-ready exports (`exports/`)
* Each fighter is exported alone at the origin as GLB (Y-up) and FBX (FBX_SCALE_ALL), rigged and skinned.
* Clips (glTF animation names / FBX takes `Archer|<clip>`, `Panda|<clip>`):
  * archer: `idle walk attack_arrow dodge hit_react respect_bow victory defeat`
  * panda: `idle walk attack_lightning dodge spin_kick hit_react respect_bow victory defeat`
* The clips are in place. Locomotion and knockback in the film are object-level motion and are not baked into the clips.
  The dodge roll's lift and the spin kick's jump are on the `root` bone.
* Archer extras: a `nock` bone (the string's centre follows it; a Copy Location constraint to `nock_target` on
  `hand.R` is baked into the clips) and an `arrow` bone (the nocked arrow; scale 0.001 = arrow hidden after release).
  In `attack_arrow`, the release is clip frame 8.
* Panda: lightning fires from the mouth (`Bone_jaw02`) at `attack_lightning` frame 18. The stock Panda3D joint names
  are kept. The `Dummy_*_foot_heel/toe` helpers are non-deforming.
* The panda keeps its stock texture. The archer's procedural materials are flattened to flat colours, as in the base scene.
  Each move is a separate Blender action, so `fight.blend` can be re-exported.

## Render
Cycles CPU, 1280x720 native, 6 spp adaptive + OIDN, persistent data. The god-ray volume is disabled
(`volume=0`) to fit the time budget. The look is a little crisper and more saturated than the base scene
(the compositor mist haze is still on). Grass density is faded out within about 2-6 m of the camera path.
`check` verified that both fighters' centres are in frame on all 420 frames and that no tree or prop blocks the
camera's view of either fighter.

Render stats (8-core CPU): 420 frames in 2998 s (50.0 min, about 7.1 s per frame). The 1920x1080 still at 48 spp took 86 s.
The scene build plus the framing check takes about 15 s. The export takes about 20 s. The mux takes about 10 s.

## Limitations (honest list)
* The panda is the stock **quadruped**. It has no hands, so the "lightning" comes from its mouth and its paws only
  rise in the rear-up. All panda moves except the stock walk are new keyframed FK poses. They read clearly but are simple.
* The stock walk is played 2.4-2.8x faster to match the ground speed, so some paw skating remains, mostly in the charge.
* The archer still has rigid per-part skinning (visible primitive joints). The arms use an analytic 2-bone IK.
  The hand ends about 10 cm short of the bow string when re-nocking, so the string centre blends to the hand over 2 frames.
  The new arrow pops onto the string. It is never seen travelling from the quiver.
* In the finale, the archer's next nocked arrow reappears about 3 frames after release. The clash flash covers it.
* Hits are scripted, not simulated. Arrows bounce off on hand-tuned ballistic arcs. The spin kick passes about 2 m from the archer.
* There's no cloth or fur secondary motion. The cloak follows the spine.
* 6 spp + denoise leaves some distant grass shimmer and slightly soft detail. More samples or `volume=1` cost about 1.5-2x the render time.
* The audio is simple procedural synthesis, roughly timed to the events (±1 frame). There's no music.
