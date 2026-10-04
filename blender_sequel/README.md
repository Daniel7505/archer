# Archer vs Panda – Part 2 (sequel + full film)

`full_film.mp4` (not committed): 1280x720, 24 fps, **56.9 s**, AAC stereo, integrated loudness about -16 LUFS.
Order: ocarina intro (reused `../ocarina/ocarina_performance.mp4`), then the duel (the archer narrowly wins), then the spirit capture, then the travel and the Grubbo fight, then the ocarina summon with the ghost panda and the K.O. Each join is a 0.4 s crossfade (video and audio).

## Pipeline
```
B=/workspace/blender/blender-4.2.23-linux-x64/blender
python3 rolls.py                                  # seeded combat rolls -> rolls.json (seed 560)
$B -b ../scene.blend -P sequel_scene.py -- mode=fightwin anim volume=0 samples=6   # frames 266-420 (1-265 reused from ../fight/frames)
$B -b ../scene.blend -P sequel_scene.py -- mode=capture  anim volume=0 samples=6   # 120 frames
$B -b ../scene.blend -P sequel_scene.py -- mode=brute    anim volume=0 samples=6   # 264 frames (travel = frames 1-72)
$B -b ../scene.blend -P sequel_scene.py -- mode=summon   anim still volume=0 samples=6 ssamples=32   # 240 frames + hero still
$B -b ../scene.blend -P sequel_scene.py -- mode=export                             # game-ready rigs -> exports/
python3 hud_composite.py      # HP bars, floating damage numbers, CRIT!/CRUSHING BLOW!/heal/DODGE!/K.O., name card
python3 make_sfx_sequel.py    # synthesized SFX per segment (+ original melody.wav in the summon)
python3 stitch.py             # encode, loudnorm, crossfade -> full_film.mp4 + film_timeline.json
python3 beats.py              # beat_sheet.md
```
Extra flags: `check` (framing and obstruction test), `preview frames=a,b`, `save`.
`sequel_scene.py` execs `../fight/fight_scene.py` for the panda import, the clips, the FX and camera fitting, and `../ocarina/ocarina_scene.py` for the ocarina, the finger animation and the IK hands. HUD screen positions are projected through the final cameras into `hud_<segment>.json`.

## Combat rules (rolls.py, one RNG rolled in story order, seed 560)
- Arrows do 15. An archer crit (25%) adds 75%, so 15 becomes 26.
- Panda lightning does 20 and the spin kick 18. Grubbo's shoulder bash does 25.
- An enemy crushing blow (20%) adds 25%: 20→25, 18→22, 25→31.
- Ghost-panda lightning does 20, or 35 on a crit (25%).
- The Spirit Bond heals the archer by 40 (scripted, not rolled).
- HP: archer 100, panda 80, Grubbo 120.
- The seed was chosen by search so the story holds: the panda falls exactly on the last arrow, the archer ends the duel at 17 HP, and Grubbo falls on the third bolt.
- The rolls themselves are real outputs of `random.Random(560)`; see `beat_sheet.md`.

## Grubbo the Greedy (original character)
He has a stocky barrel body in a purple tunic, with a yellow sash and a gold-coin buckle, a coin pouch, and yellow sleeves and trousers. He wears purple boots and gloves and a riveted iron pauldron on one shoulder. He is bald with a topknot, has a unibrow and a big droopy walrus moustache, and wears a gold earring. His attack is a shoulder bash.
He has **no cap and no letter emblem**. He is built from primitives in this script and is not based on any existing game character.

## Exports (`exports/`)
- `brute_grubbo_rigged.glb/.fbx` has 16 bones, rigid skinning and the clips idle, walk, bash, hit_react and knockout. Materials are flattened to colours.
- `panda_ghost_rigged.glb/.fbx` is the same panda rig and clips as `blender_fight/exports/panda_rigged`. It uses a translucent emissive ghost material variant: glTF alphaMode BLEND, alpha 0.4, cyan emissive.

## Limitations
- Frames 1–265 of the duel and the intro are reused renders. The intro is still the 640x360 upscale; there was no budget for a native re-render.
- Brute, travel and summon are rendered at 6 spp plus denoise, so there is some softness and grass shimmer.
- Grubbo is primitive-built with rigid weights, so the joints are visible up close. Purple reads a bit magenta under the golden-hour light.
- Grubbo's knockout falls onto his back, but the facing is approximate.
- The capture and summon use the ocarina rig, so the bow is stowed (hard cut and crossfade from the drawn bow).
- The summon is re-staged at the brute location, so positions differ slightly from the end of the brute shot.
- The archer walks with the bow held in the travel shot.
- Some damage popups are short (they are cut at shot changes).
- The melody is truncated with a fade at about 7 s.
