extends RefCounted

## Pure numbers for Wicklight Grove.
## Original spells and places. The shape of the systems (gauge, move circle,
## element levels that grow by casting, points on a character level) is inspired
## by Quest 64. None of the names, spells, or story come from that game.

const ARENA_R := 8.7

const ELEMENT_COLOR := {
	"earth": Color("8d6a3a"),
	"water": Color("3a7ca5"),
	"fire": Color("c4552a"),
	"wind": Color("2f9a72"),
}

const SPELL_ORDER := [
	"ember_shot", "hearthburst",
	"dew_mend", "rain_ring",
	"stonefoot", "bulwark",
	"skyfang", "slipstream",
]

const SPELLS := {
	"ember_shot": {
		"name": "Ember Shot",
		"element": "fire",
		"need": 1,
		"mp": 7,
		"xp": 12,
		"damage": 18,
		"heal": 0,
		"radius": 1.55,
		"range": 7.5,
		"self_center": false,
		"root": false,
		"slow": false,
		"push": 0.0,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "A small fire circle. Burst damage.",
	},
	"hearthburst": {
		"name": "Hearthburst",
		"element": "fire",
		"need": 3,
		"mp": 14,
		"xp": 12,
		"damage": 30,
		"heal": 0,
		"radius": 2.7,
		"range": 6.8,
		"self_center": false,
		"root": false,
		"slow": false,
		"push": 0.4,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "A wider, hotter circle.",
	},
	"dew_mend": {
		"name": "Dewmend",
		"element": "water",
		"need": 1,
		"mp": 6,
		"xp": 12,
		"damage": 0,
		"heal": 18,
		"radius": 2.3,
		"range": 0.0,
		"self_center": true,
		"root": false,
		"slow": false,
		"push": 0.0,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "Heals whoever stands in the dew. Both of you inside heal more.",
	},
	"rain_ring": {
		"name": "Rainring",
		"element": "water",
		"need": 3,
		"mp": 12,
		"xp": 12,
		"damage": 0,
		"heal": 16,
		"radius": 3.2,
		"range": 7.0,
		"self_center": false,
		"root": false,
		"slow": true,
		"push": 0.0,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "Place a rain. Heals allies inside and slows foes inside.",
	},
	"stonefoot": {
		"name": "Stonefoot",
		"element": "earth",
		"need": 1,
		"mp": 6,
		"xp": 12,
		"damage": 12,
		"heal": 0,
		"radius": 1.7,
		"range": 6.2,
		"self_center": false,
		"root": true,
		"slow": false,
		"push": 0.0,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "Hurts, and the next step of anyone caught is short.",
	},
	"bulwark": {
		"name": "Bulwark",
		"element": "earth",
		"need": 3,
		"mp": 9,
		"xp": 12,
		"damage": 0,
		"heal": 0,
		"radius": 2.4,
		"range": 0.0,
		"self_center": true,
		"root": false,
		"slow": false,
		"push": 0.0,
		"guard": 0.6,
		"extra_move": 0.0,
		"blurb": "Stone skin on whoever stands in it. They take less.",
	},
	"skyfang": {
		"name": "Skyfang Bolt",
		"element": "wind",
		"need": 1,
		"mp": 8,
		"xp": 12,
		"damage": 16,
		"heal": 0,
		"radius": 1.15,
		"range": 8.6,
		"self_center": false,
		"root": false,
		"slow": false,
		"push": 1.5,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "The panda's lightning. A tight circle at long range.",
	},
	"slipstream": {
		"name": "Slipstream",
		"element": "wind",
		"need": 3,
		"mp": 11,
		"xp": 12,
		"damage": 9,
		"heal": 0,
		"radius": 2.05,
		"range": 7.0,
		"self_center": false,
		"root": false,
		"slow": false,
		"push": 2.7,
		"guard": 0.0,
		"extra_move": 3.2,
		"blurb": "A shove of wind, then a free step.",
	},
}

const ATTACKS := {
	"mite": [
		{"name": "Spark Hop", "power": 8, "radius": 1.35, "range": 2.35, "root": false},
	],
	"lurker": [
		{"name": "Bramble Toss", "power": 11, "radius": 1.75, "range": 5.6, "root": false},
	],
	"boss": [
		{"name": "Jar Slam", "power": 15, "radius": 2.55, "range": 4.3, "root": false},
		{"name": "Cork Seal", "power": 7, "radius": 2.15, "range": 6.2, "root": true},
	],
}

const ENCOUNTERS := {
	"meadow": {
		"title": "Golden Meadow",
		"theme": "meadow",
		"region": "meadow",
		"xp": 18,
		"coach": true,
		"intro": "The mite hops, and the grass opens into a clearing.",
		"win": "The mite cools into an ordinary stone.",
		"enemies": [
			{"id": "mite_a", "kind": "mite", "name": "Cinder Mite", "pos": [-1.2, -3.4], "hp": 30, "agility": 7.0, "move": 3.2},
			{"id": "mite_b", "kind": "mite", "name": "Cinder Mite", "pos": [1.8, -4.4], "hp": 30, "agility": 7.0, "move": 3.2},
		],
	},
	"mite": {
		"title": "Golden Meadow",
		"theme": "meadow",
		"region": "meadow",
		"xp": 14,
		"coach": true,
		"intro": "A cinder mite cracks out of the grass. The field fades to a clearing.",
		"win": "The mite cools into an ordinary stone.",
		"enemies": [
			{"id": "mite_a", "kind": "mite", "name": "Cinder Mite", "pos": [0.2, -3.6], "hp": 30, "agility": 7.0, "move": 3.2},
		],
	},
	"sprig": {
		"title": "Lantern Grove",
		"theme": "grove",
		"region": "grove",
		"xp": 16,
		"coach": false,
		"intro": "A thicket sprig unwinds. The trees give you a clearing.",
		"win": "The sprig folds back into the roots.",
		"enemies": [
			{"id": "sprig", "kind": "lurker", "name": "Thicket Sprig", "pos": [0.3, -3.8], "hp": 34, "agility": 8.0, "move": 3.4},
		],
	},
	"lurker": {
		"title": "Lantern Grove",
		"theme": "grove",
		"region": "grove",
		"xp": 28,
		"coach": false,
		"intro": "The thicket lurker is the tall one. It throws brambles in a wide circle.",
		"win": "The lurker folds back into the thicket. The stair is north, if you want it.",
		"enemies": [
			{"id": "lurker", "kind": "lurker", "name": "Thicket Lurker", "pos": [0.4, -4.2], "hp": 48, "agility": 9.0, "move": 3.6},
		],
	},
	"pebble": {
		"title": "The Sealed Stair",
		"theme": "ruin",
		"region": "stair",
		"xp": 14,
		"coach": false,
		"intro": "A kiln pebble rolls into the cleared stone.",
		"win": "The pebble cracks and goes quiet.",
		"enemies": [
			{"id": "pebble", "kind": "mite", "name": "Kiln Pebble", "pos": [0.6, -3.5], "hp": 28, "agility": 7.0, "move": 3.0},
		],
	},
	"stair": {
		"title": "The Sealed Stair",
		"theme": "ruin",
		"region": "stair",
		"xp": 55,
		"coach": false,
		"boss": true,
		"intro": "Mosswick sits on the last jar. He is not angry. He is only very certain that lights belong in pockets.",
		"win": "",
		"enemies": [
			{"id": "mosswick", "kind": "boss", "name": "Mosswick", "pos": [0.2, -3.6], "hp": 100, "agility": 10.0, "move": 3.4},
		],
	},
}


static func xp_to_advance(level: int) -> int:
	if level <= 1:
		return 20
	if level == 2:
		return 24
	return 28 + (level - 3) * 8


static func add_element_xp(level: int, xp: int, amount: int) -> Dictionary:
	var leveled: Array = []
	xp += amount
	var guard := 0
	while level < 20 and xp >= xp_to_advance(level) and guard < 12:
		xp -= xp_to_advance(level)
		level += 1
		leveled.append(level)
		guard += 1
	return {"level": level, "xp": xp, "leveled": leveled}


static func spells_unlocked(element: String, level: int) -> Array:
	var names: Array = []
	for id in SPELL_ORDER:
		var spell: Dictionary = SPELLS[id]
		if str(spell.element) == element and int(spell.need) == level:
			names.append(spell.name)
	return names


static func is_known(elements: Dictionary, spell_id: String) -> bool:
	var spell: Dictionary = SPELLS[spell_id]
	return int(elements[spell.element].level) >= int(spell.need)


static func spell_rows(elements: Dictionary) -> Array:
	var rows: Array = []
	for id in SPELL_ORDER:
		var spell: Dictionary = SPELLS[id]
		var lv := int(elements[spell.element].level)
		var known := lv >= int(spell.need)
		if not known and lv + 2 < int(spell.need):
			continue
		var label := "%s   %d spirit" % [spell.name, int(spell.mp)]
		if not known:
			label = "%s   (level %d)" % [spell.name, int(spell.need)]
		rows.append({
			"id": id,
			"label": label,
			"known": known,
			"mp": int(spell.mp),
			"need": int(spell.need),
			"name": spell.name,
			"blurb": spell.blurb,
			"element": spell.element,
		})
	return rows


static func physical_attack(kind: String) -> Dictionary:
	if kind == "panda":
		return {
			"name": "Spin Kick",
			"element": "",
			"mp": 0,
			"xp": 0,
			"damage": 16,
			"heal": 0,
			"radius": 1.75,
			"range": 2.45,
			"self_center": false,
			"root": false,
			"slow": false,
			"push": 0.8,
			"guard": 0.0,
			"extra_move": 0.0,
			"blurb": "Close and wide.",
		}
	return {
		"name": "Aimed Shot",
		"element": "",
		"mp": 0,
		"xp": 0,
		"damage": 14,
		"heal": 0,
		"radius": 0.68,
		"range": 9.4,
		"self_center": false,
		"root": false,
		"slow": false,
		"push": 0.0,
		"guard": 0.0,
		"extra_move": 0.0,
		"blurb": "A small circle at long range.",
	}


static func hurt(power: int, defending: bool, guard_mult: float) -> int:
	var amount := float(power)
	if defending:
		amount *= 0.5
	if guard_mult > 0.0 and guard_mult < 0.999:
		amount *= guard_mult
	return maxi(1, int(round(amount)))


static func flat(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


static func in_circle(point: Vector3, center: Vector3, radius: float) -> bool:
	return flat(point, center) <= radius + 0.05


static func clamp_arena(p: Vector3, center: Vector3, radius: float) -> Vector3:
	var d := Vector3(p.x - center.x, 0.0, p.z - center.z)
	if d.length() > radius and d.length() > 0.001:
		d = d.normalized() * radius
	return Vector3(center.x + d.x, 0.0, center.z + d.z)


static func clamp_move(origin: Vector3, move_r: float, arena_c: Vector3, arena_r: float, desired: Vector3) -> Vector3:
	var o := Vector3(origin.x, 0.0, origin.z)
	var p := Vector3(desired.x, 0.0, desired.z)
	var off := p - o
	if off.length() > move_r:
		p = o if off.length() < 0.001 else o + off.normalized() * move_r
	p = clamp_arena(p, arena_c, arena_r)
	off = p - o
	if off.length() > move_r:
		p = o if off.length() < 0.001 else o + off.normalized() * move_r
	return p


static func clamp_aim(origin: Vector3, desired: Vector3, reach: float, arena_c: Vector3, arena_r: float) -> Vector3:
	if reach <= 0.0:
		return Vector3(origin.x, 0.0, origin.z)
	return clamp_move(origin, reach, arena_c, arena_r, desired)
