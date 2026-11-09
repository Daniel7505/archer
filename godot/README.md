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

## The story so far

This follows the films, not a borrowed plot. The archer and the panda already fought and became partners. Their pack still holds what they took off Grubbo: a gold-coin buckle, a moustache comb, some coins, and a Mystery Shard. The spirit panda can be a mount later. That call is not on this stretch of road yet.

Bramblewick Camp, the meadow, the grove, and the stair are the opening wilds. Mosswick corking the wicklights is trouble on the way, not the whole game. East of the meadow a stone road runs to **Aldermoor**, the white city. The doors are shut. **Seer Ilvane** waits outside and will not buy the shard. She names the work **Whispers of the Orb**: seven cursed orbs, and the shard is a whisper of one. Peddler Quill, on that road, only sells the rumor.

## How to play

You start at Bramblewick Camp. A pale stone road leaves the yard and runs north, then east. Follow it. It passes Quill's stall, the valley gate, Briarwell, Wayside Camp, and Holt, and it ends at Aldermoor's shut wall. Lina keeps the tea, and nothing wanders in the yard. North of camp is the Golden Meadow, then the Lantern Grove and the Sealed Stair. You can leave the path. Lamb Hill, Pebble Creek, the Jar Nook, and Broken Landing are optional. Briarwell is a small cluster of roofs partway to the city wall.

Each of them has a **life**. **Spirit is shared.** A red circle hurts every body standing in it. Dewmend heals each of you inside it, and a little more when you stand together. If one of you falls, the other can still act and can heal them. If both fall, the fight is lost.

### On the map

Foes are out in the open. Cinder mites patrol the meadow. Thicket sprigs patrol the grove. Kiln pebbles roll around the stair. The thicket lurker is taller, and Mosswick sits on a jar. Walk around them, or touch one.

Touching a foe fades the map to black and opens a cleared battle field in the colors of that place. It is not an unseen ambush. Win, and that foe is gone when you return. Leave the region and come back later, and the ordinary ones are walking again. Mosswick stays gone after the story ends. Camp never grows foes.

The road forks. West of the meadow fork is Lamb Hill, only a view. East of the camp hedge, still in the meadow, is Pebble Creek. The grove has a Jar Nook. The stair has a Broken Landing. Berries, spirit sips, and short notes are lying in those corners. None of them are required to reach Mosswick. Past the valley gate the stone road keeps going, with trees and grass on either side, until Aldermoor's walls.

### One player

With no controller plugged in, the keyboard walks the archer and the panda follows. In a fight, the same keys play whoever's gauge fills, archer or panda.

| Key | Action |
|---|---|
| W A S D or arrows | Walk the archer. In a fight, walk the blue circle |
| Mouse | Aim a spell or shot, then click |
| Q and R, or right-drag | Turn the camera left and right. Right-drag also looks up and down |
| Mouse wheel | Zoom |
| F | Talk to someone at a stop, or read a sign |
| B | Spell book, the pack, and element points |
| Space | Jump while walking. In a talk or a fight, Space still confirms |
| Enter | Confirm, begin, and advance a talk. 1 attack, 2 spell, 3 item, 4 defend |
| Esc | Back, or close the spell book |

### Two players on one computer

Plug a PlayStation DualShock or DualSense, or any standard pad, into the desktop. No account and no network. The first pad is player 2.

Player 1 keeps the keyboard and mouse as the archer. Player 2 is the panda: left stick to walk, right stick or the d-pad to aim circles. Cross confirms, Circle backs out, Square attacks, Triangle opens spells, L1 is the item, R1 defends. The names match a PlayStation pad. An Xbox-style pad uses the same positions: A, B, X, Y, LB, RB.

On the map you move at the same time. The camera pulls back to frame both of you. In a fight, time waits on each gauge. When the archer's gauge fills, player 1 acts. When the panda's fills, player 2 acts. If the pad never moves, the game stays single-player and the panda keeps following.

There is no online play.

Walk into a berry, a sip, or a note to take it. You do not need F for those. F is for people and signs. Lina refills life, shared spirit, and berries.

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

## Where the talks send you

The talks are a path, not a journal. Press F when you are standing with someone.

1. **Bramblewick Camp**, Lina's yard. This is where you start, and where you come back for tea. Lina sends you to Quill.
2. **Quill's stall**, on the east road, still this side of the grove. A counter, a blue awning, and crates. Quill sends you to Ilvane.
3. **The valley gate**. White pillars and a blue door. Ilvane will not take the shard. She names Whispers of the Orb, then points you to Briarwell and to the warrior on the road.
4. **Briarwell**, blue roofs and a fire just off the road in the outer fields. A neighbor sends you on to Wayside Camp and names Holt.
5. **Wayside Camp**, two tents and a fire, the last stop before the wall. The watcher says Holt is ahead.
6. **Holt** stands on the road in a red ring, the same kind of mark as the other large foes. The white wall is behind them. The city doors stay shut. Touching Holt fades into a fight, the same way the mites do.

## How big it is

The overworld move speed is 6.8 meters a second. Times below are for a clear run along open ground, not a straight line through hedges.

The first zone is the opening wilds plus the valley gate: Bramblewick Camp, the Golden Meadow, the Lantern Grove, the Sealed Stair, and the Aldermoor road up to that gate. Crossing it the long way, east to west along the open band, or south to north from camp to the far stair wall, takes about a minute and a half to two minutes.

Past the valley gate, the outer fields are the second zone. The stone road to Aldermoor's walls is a several-minute walk, a few times the first crossing, with room north and south for Briarwell and Ash Ridge. The city interior stays shut. You can see the walls.

## Streaming

The ground is cut into 128 meter chunks. A flat painted slab and a few big foliage cards stay up for the horizon, so the distance does not turn into a hole. Trees, grass, houses, collision, and wandering foes are only awake in the chunks around the party. In co-op that circle follows both of you. Grass cards and tree cards fade out with distance.

Foliage is a collage, not a modeled forest. Each tree is a brown trunk plus three crossed cards that share one painted leaf texture. Hedges are a low green mass with a short fan of those same cards. Grass is a smaller clump of cards. Distant chunks keep three oversized cards so a woods still reads after the detail has gone to sleep. Ground tiles are flat unshaded color, like a painted board. Houses in Briarwell are simple white masses with blue roofs. The look is the warm, readable shapes of the films, kept cheap enough to repeat across both zones.

## What you can finish in this slice

- Cross the opening valley in about two minutes, then walk the outer fields for several minutes toward Aldermoor's walls.
- Start in Lina's yard, then follow the talks: Quill's stall, Ilvane at the valley gate, Briarwell, Wayside Camp, and Holt on the road before the shut wall.
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
