# Wicklight Grove

A short original game for Nick and Suni. The archer and the panda, from the films in this repo, walk a little map together and fight as partners.

The **shape** of the play is inspired by Nintendo 64's Quest 64 (also called Holy Magic Century): an agility gauge, a circle you can walk inside, spells aimed as circles on the ground, and four elements that grow when you cast them. This is not that game. It does not use its characters, names, maps, music, items, or text. Do not add those assets later.

It is a private gift. It is not for sale.

The old Panda3D sketch is still `archer.py` at the repo root. This Godot project sits beside it and does not replace it.

## Open it

1. Install **Godot 4.7** or newer from [godotengine.org](https://godotengine.org/download). The project was made with Godot 4.7.2. The standard build is enough. You do not need the .NET version.
2. In Godot, choose **Import**, then select `godot/project.godot` in this repository.
3. Press **F5** or the Play button.

The window is 1280×720. The renderer is Compatibility, so it can open on more computers.

## How to play

You start at Bramblewick Camp. Lina keeps the tea, and nothing wanders there. The story is still short: Mosswick has corked the grove's wicklights into jars. The way runs north across the Golden Meadow, east into the Lantern Grove, and on to the Sealed Stair. The ground is wide. You can leave the path.

The archer and the panda share **one life**. They are two bodies. A red circle hurts each body it catches, so standing in the same circle can hurt twice. Standing together inside Dewmend heals a little extra.

### On the map

Foes are out in the open. Cinder mites patrol the meadow. Thicket sprigs patrol the grove. Kiln pebbles roll around the stair. The thicket lurker is taller, and Mosswick sits on a jar. Walk around them, or touch one.

Touching a foe fades the map to black and opens a cleared battle field in the colors of that place. It is not an unseen ambush. Win, and that foe is gone when you return. Leave the region and come back later, and the ordinary ones are walking again. Mosswick stays gone after the story ends. Camp never grows foes.

The road forks. West of the meadow fork is Lamb Hill, only a view. East of the camp hedge, still in the meadow, is Pebble Creek. The grove has a Jar Nook. The stair has a Broken Landing. Berries, spirit sips, and short notes are lying in those corners. None of them are required to reach Mosswick. The east trees past the grove are empty on purpose.

| Key | Action |
|---|---|
| W A S D or arrows | Walk |
| Q and R | Turn the camera. Right-drag does it too |
| Mouse wheel | Zoom |
| F | Talk to Lina, or read a sign. Lina restores life, spirit, and berries |
| B | Spell book. This is also where you place element points |
| Space or Enter | Continue dialogue |
| Esc | Close the spell book |

Walk into a berry, a sip, or a note to take it. You do not need F for those.

### In a fight

The fade lands you in the clearing. Gauges fill on their own. Whoever fills first acts. Time waits while you choose.

1. A **blue circle** appears. Walk inside it with WASD, or click a spot inside it. Space when you are standing where you want.
2. Choose **1 Attack**, **2 Spell**, **3 Item**, or **4 Defend**. Esc goes back to walking.
3. Aim the colored circle with the mouse or the arrow keys. Click or Space to release it. Esc backs out.
4. Red circles are enemy attacks. They land where the circle is drawn. Step out of that reach on your own turn.

Attacks:

- **Archer — Aimed Shot.** A small circle at long range. Physical. It does not grow an element.
- **Panda — Spin Kick.** Close and wide. Physical.
- **Panda's lightning is Skyfang Bolt**, a wind spell: a tight circle at long range.

Spells spend **spirit** and grow that element. Two casts of a starter spell raise it from level 1 to 2. Keep going, or place a level-up point, and level 3 learns the stronger spell. You can use the new spell in the next fight, and sometimes before the current one ends if you reached 3 mid-battle.

| Element | Starter | At level 3 |
|---|---|---|
| Fire | Ember Shot, a small burst | Hearthburst, wider and hotter |
| Water | Dewmend, a heal around you | Rainring, a placed heal that also slows |
| Earth | Stonefoot, damage and a short next step | Bulwark, less damage for whoever stands in it |
| Wind | Skyfang Bolt, the lightning | Slipstream, a shove and then a free step |

Items do not grow an element. A Grove Berry heals. A Spirit Sip restores spirit. Lina refills berries when you talk to her.

Clearing a fight gives experience. A single mite is a small fight. The lurker and Mosswick are the large ones. A character level gives **two points** to place into any elements. A few meadow mites, or one bigger fight, will get you there.

If you fall, you can try the battle again, or go back to camp. Camp undoes that fight's spirit growth and puts the tea on. Winning keeps the growth.

## What you can finish in this slice

- Walk a large camp, meadow, grove, and stair, plus Lamb Hill, Pebble Creek, the Jar Nook, and Broken Landing.
- See foes on the map, walk around them, or touch one and fade into a clearing.
- Fight mites, sprigs, pebbles, the lurker, and Mosswick.
- Cast, grow an element by using it, and see a stronger spell appear.
- Win or lose. Winning against Mosswick lights the jars. Beaten foes stay gone until you leave that region and return.

There is no save file yet. Closing the game starts the story over. That is enough for one sitting.

## What is placeholder

- **The panda is a stand-in** made of simple Godot shapes (a scarf included so it reads as ours). The rigged panda under `blender_fight/exports/` is the stock Panda3D sample model. Nick does not own that mesh, so it is not in this project and should not be shipped as the character.
- Lina, the mites, the lurker, Mosswick, the camp, the grove, and the ruin are blockout meshes.
- **The archer is the original rig** from `blender_fight/exports/archer_rigged.glb` (the film's procedural archer, with idle, walk, aimed shot, hit, bow, victory, and defeat).
- The meadow motif is a short original loop written for this prototype. It is not from the films and not from Quest 64.
- Enemy movement is simple: they step toward you, then put a circle down.

## What a later pass could add

- An original panda rig, with the lightning and the spin kick on its own bones.
- The spirit mount, the backpack, and Aldermoor, picking up from the chapter 2 film.
- More spells per element, a real save, and a versus tease once the story slice feels good.
- Richer ground, crowds, and the ocarina as a thing you can play rather than a film beat.

## Check without the editor

From the repository root, with Godot 4.7 on your PATH:

```
godot --headless --path godot --script res://tests/smoke.gd
```

That run checks the element math, a scripted meadow battle (including fire growing to level 3 and Dewmend), and that a visible map foe can fade you into a clearing and, after the win, be gone until you leave the region and come back. `SMOKE PASS` means those checks held.

This copy was checked with Godot 4.7.2. The headless smoke test passed. Frames were also rendered with software OpenGL: the title, the camp (archer, placeholder panda, Lina), and the meadow fight with the blue step circle. Mouse aiming was not clicked through by hand on that machine. If the archer faces backward on yours, the model yaw is `PI` in `godot/scripts/actor_visual.gd`.
