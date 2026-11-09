extends RefCounted

const Rules = preload("res://scripts/rules.gd")

var hp := 64
var hp_max := 64
var mp := 28
var mp_max := 28
var level := 1
var xp := 0
var xp_to_next := 30
var pending_points := 0
var intro_done := false
var ending_seen := false
var elements := {
	"earth": {"level": 1, "xp": 0},
	"water": {"level": 1, "xp": 0},
	"fire": {"level": 1, "xp": 0},
	"wind": {"level": 1, "xp": 0},
}
var items := {
	"grove_berry": 3,
	"spirit_sip": 2,
}
var cleared := {
	"meadow": false,
	"grove": false,
	"stair": false,
}


func snapshot() -> Dictionary:
	return {
		"hp": hp,
		"hp_max": hp_max,
		"mp": mp,
		"mp_max": mp_max,
		"level": level,
		"xp": xp,
		"xp_to_next": xp_to_next,
		"pending_points": pending_points,
		"elements": elements.duplicate(true),
		"items": items.duplicate(true),
	}


func restore(data: Dictionary) -> void:
	hp = int(data.hp)
	hp_max = int(data.hp_max)
	mp = int(data.mp)
	mp_max = int(data.mp_max)
	level = int(data.level)
	xp = int(data.xp)
	xp_to_next = int(data.xp_to_next)
	pending_points = int(data.pending_points)
	elements = data.elements.duplicate(true)
	items = data.items.duplicate(true)


func note_cast(element: String, amount: int) -> Array:
	var e: Dictionary = elements[element]
	var result: Dictionary = Rules.add_element_xp(int(e.level), int(e.xp), amount)
	e.level = int(result.level)
	e.xp = int(result.xp)
	elements[element] = e
	var msgs: Array = []
	var title := element.capitalize()
	msgs.append("+%d %s" % [amount, title])
	for lv in result.leveled:
		msgs.append("%s is now level %d." % [title, int(lv)])
		for spell_name in Rules.spells_unlocked(element, int(lv)):
			msgs.append("New spell: %s." % spell_name)
	return msgs


func spend_point(element: String) -> Array:
	var msgs: Array = []
	if pending_points <= 0 or not elements.has(element):
		return msgs
	pending_points -= 1
	var e: Dictionary = elements[element]
	e.level = int(e.level) + 1
	elements[element] = e
	var title := element.capitalize()
	msgs.append("A point settles into %s. It is now level %d." % [title, int(e.level)])
	for spell_name in Rules.spells_unlocked(element, int(e.level)):
		msgs.append("New spell: %s." % spell_name)
	return msgs


func grant_victory_xp(amount: int) -> int:
	xp += amount
	var gained := 0
	var guard := 0
	while xp >= xp_to_next and guard < 8:
		xp -= xp_to_next
		level += 1
		gained += 1
		pending_points += 2
		hp_max += 8
		mp_max += 4
		hp = mini(hp_max, hp + 8)
		mp = mini(mp_max, mp + 4)
		xp_to_next = 30 + (level - 1) * 20
		guard += 1
	return gained


func heal(amount: int) -> void:
	hp = mini(hp_max, hp + amount)


func spirit(amount: int) -> void:
	mp = mini(mp_max, mp + amount)


func use_item(id: String) -> String:
	if int(items.get(id, 0)) <= 0:
		return "Nothing left."
	items[id] = int(items[id]) - 1
	if id == "grove_berry":
		var before := hp
		heal(22)
		return "Grove Berry. +%d life." % (hp - before)
	if id == "spirit_sip":
		var before := mp
		spirit(14)
		return "Spirit Sip. +%d spirit." % (mp - before)
	return "Used."


func add_item(id: String, amount: int) -> int:
	items[id] = int(items.get(id, 0)) + amount
	return int(items[id])


func full_rest() -> void:
	hp = hp_max
	mp = mp_max
	if int(items.get("grove_berry", 0)) < 3:
		items.grove_berry = 3
	if int(items.get("spirit_sip", 0)) < 1:
		items.spirit_sip = 1
