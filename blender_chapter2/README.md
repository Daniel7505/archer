# Chapter 2: Loot, the Spirit Panda mount and the White City of Aldermoor

56.7 s of new footage that picks up right where the sequel ends, with Grubbo knocked out. It is 1280x720 at 24 fps, rendered in Cycles at 6 spp.
`full_film_v2.mp4` is the sequel's `full_film.mp4` followed by this chapter, joined with a 1.0 s crossfade.

## Beat sheet
See `beat_sheet.md` for timestamps. In order:
1. **Loot**: four items arc out of Grubbo and land with rarity-coloured loot beams. The archer walks over and collects them, and a backpack grid fills slot by slot with tooltips and loot toasts.
   - Gold-Coin Buckle: Rare
   - Moustache Comb: Uncommon
   - Mystery Shard: Epic
   - 12 Gold Coins: Common
2. **Mount**: the archer plays *The Swiftpaw Air*, a new original ocarina tune (`make_melody2.py`, D-Lydian galloping figure at 132 bpm). A spirit stream calls up the ghost panda, which bows. The toast reads "NEW MOUNT LEARNED: Spirit Panda".
3. **Ride**: the archer sits on the panda's back and they gallop along the meadow path and the road to the gate of Aldermoor. The shots are a side track, a front track, then a wide arrival between the two Warden statues.
4. **Establish**: a crane pull-back over the walls with the title card "ALDERMOOR, the White City by the River".
5. **City**: the panda lopes in through the gate, over the canal bridge and into the market square. Zone text reads "Market Square".
6. **Shops**: a montage at three vendors.
   - Mira the Jeweler buys the buckle for 35 g.
   - Old Tobin, Barber & Curios, buys the comb for 9 g.
   - Seer Ilvane won't take the shard ("keep it").
   - The gold counter ticks 12 → 47 → 56.
   - It ends on a dusk skyline with "To be continued...". There is no quest scene.

## Aldermoor (original design)
The city is Stormwind-*inspired*: white stone walls, blue conical roofs, canals with bridges and a market square. Everything else is original:
- The name and the layout (a ring road around one avenue).
- The emblem: a gold alder leaf over three silver waves on deep blue (`make_assets.py`).
- The guardian statues: the "Wardens of the Alders" are robed figures with pointed helms, leaf-boss shields and orb staffs.

No Blizzard names, emblems, lion crests or landmarks are used.

The city is built from reusable modules: wall, tower, gatehouse, house, tallhouse, 4 stall colours, bridge, statue and banner. Each module is built once into its own collection and placed as **collection instances**, which keeps frames around 7–8 s.

## Files
| file | what |
|---|---|
| `chapter2_scene.py` | Blender 4.2 script. Modes: `loot`, `mount`, `ride` (+`still` = 1920x1080 hero), `city`, `establish`, `stills` (vendor + dusk stills), `export`, `citytest`, `ridetest`. Actions: `preview`, `anim`. Options: `samples=`, `volume=0`. Renders resume frame by frame and log to `render_log.txt`. |
| `run_queue.sh` / `queue.txt` | nohup render queue. Resumable: finished modes are recorded in `done.txt`. |
| `make_melody2.py` | Synthesizes the new original ocarina melody → `melody2.wav`, `notes2.json` (drives the finger animation). |
| `make_assets.py` | Draws the Aldermoor banner emblem (PIL). |
| `hud_ch2.py` | PIL overlays: backpack grid, toasts, mount toast, title and zone text, vendor UI with SOLD stamps and gold counter, Ken Burns montage. |
| `make_sfx_ch2.py` | numpy SFX: loot chimes by rarity, pops, pickups, coins, paw beats, horn call, city ambience (crowd, water, bells), UI clicks and stamps, plus the melody. |
| `stitch_ch2.py` | Encodes segments → `chapter2.mp4`, then `full_film_v2.mp4`. |
| `exports/aldermoor_modules.glb/.fbx` | The 12 city module pieces laid out in a row, with flat colours and the banner texture. |
| `exports/panda_ghost_mount_gallop.glb/.fbx` | The ghost panda rig with all clips **plus the new `gallop` clip** (12-frame cycle, about 2.75 m per stride). |

## Rebuild
```
B=blender-4.2/blender
for m in loot mount ride city establish; do $B -b ../scene.blend -P chapter2_scene.py -- mode=$m anim volume=0 samples=6; done
$B -b ../scene.blend -P chapter2_scene.py -- mode=ride still volume=0      # hero still
$B -b ../scene.blend -P chapter2_scene.py -- mode=stills volume=0 ssamples=16
$B -b ../scene.blend -P chapter2_scene.py -- mode=export
python3 hud_ch2.py && python3 make_sfx_ch2.py && python3 stitch_ch2.py
```
These need `../scene.blend`, `../fight/fight_scene.py`, `../sequel/sequel_scene.py` and `../ocarina/ocarina_scene.py` from the earlier chapters.

## Limitations
- Runtime is 56.7 s, slightly under the ~60 s target.
- The shop scene is a Ken Burns montage over 3 rendered vendor stills plus a dusk still, not animated footage. The vendors are static, low-detail primitive NPCs.
- During the loot beat the archer is the fight rig, so it walks and stands with the bow drawn instead of bending down. The items magnet into the archer.
- Mount to ride is a crossfade cut. There is no animated mount-up: the ride starts with the archer already seated, and the rider's pose is static (ocarina held low).
- The gallop is a procedural 12-frame cycle whose phase is tied to distance travelled. That keeps sliding small but not zero, especially while it eases from gallop to lope.
- The city is low-detail and blocky: there are no crowds, the canal reads more like a green strip than water at some angles, and banners are flat planes.
- The original ride side-tracking shot cropped the rider's head. It was re-rendered as `ride1` (frames 1-84) and swapped in.
- The full film still contains the earlier 640x360 upscaled ocarina intro from the sequel.
