extends Node3D

const Rules = preload("res://scripts/rules.gd")
const Fighter = preload("res://scripts/fighter.gd")
const ActorVisual = preload("res://scripts/actor_visual.gd")
const Circle = preload("res://scripts/circle.gd")
const Props = preload("res://scripts/props.gd")
const Pads = preload("res://scripts/pads.gd")

signal battle_over(victory: bool)

var party = null
var hud = null
var instant := false
var state := "idle"
var encounter_id := ""
var encounter := {}
var fighters: Array = []
var active = null
var move_origin := Vector3.ZERO
var move_radius := 0.0
var aim_pos := Vector3.ZERO
var aim_spell: Dictionary = {}
var aim_kind := ""
var menu_ids: Array = []
var camera_yaw := 0.0
var coach := false
var coach_used := false
var over := false
var last_messages: Array = []
var last_mouse := Vector2(-9999, -9999)
var field: Node3D
var move_circle: Node3D
var aim_circle: Node3D
var threat_circle: Node3D
var aim_line: MeshInstance3D

const GAUGE_SPEED := 7.0


func _ready() -> void:
	field = Node3D.new()
	field.name = "Field"
	add_child(field)
	move_circle = Circle.new()
	move_circle.setup(Color(0.30, 0.55, 0.95, 0.33))
	add_child(move_circle)
	aim_circle = Circle.new()
	aim_circle.setup(Color(0.95, 0.75, 0.3, 0.4))
	add_child(aim_circle)
	threat_circle = Circle.new()
	threat_circle.setup(Color(0.90, 0.18, 0.16, 0.42))
	add_child(threat_circle)
	aim_line = MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(1, 1, 1)
	aim_line.mesh = box
	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(1, 0.9, 0.45, 0.75)
	aim_line.material_override = mat
	aim_line.visible = false
	add_child(aim_line)
	_hide_circles()


func begin(id: String, party_state, snap_instant: bool = false) -> void:
	instant = snap_instant
	party = party_state
	encounter_id = id
	encounter = Rules.ENCOUNTERS[id]
	coach = bool(encounter.get("coach", false))
	coach_used = false
	over = false
	state = "gauge"
	_clear_field()
	_build_theme(str(encounter.theme))
	_spawn_pair()
	_spawn_enemies()
	_hide_circles()
	fighter("archer").gauge = 78.0
	fighter("panda").gauge = 36.0
	for f in fighters:
		if f.side == "enemy":
			f.gauge = 22.0
	_prompt("The agility gauges are filling. Whoever fills first acts.")
	_refresh_rows()


func clear_for_exit() -> void:
	over = true
	state = "idle"
	active = null
	_hide_circles()
	_clear_field()


func fighter(id: String):
	for f in fighters:
		if f.id == id:
			return f
	return null


func _process(delta: float) -> void:
	if over or state == "idle" or party == null:
		return
	if state == "gauge":
		_fill(delta)
		_maybe_start()
	elif state == "move" or state == "extra_move":
		if active:
			_steer_body(delta)
	elif state == "aim":
		_steer_aim(delta)
	_sync()
	_refresh_rows()


func input_event(event: InputEvent) -> void:
	if over or state == "idle":
		return
	if event is InputEventKey and event.echo:
		return
	var panda_turn: bool = active != null and str(active.kind) == "panda"
	if panda_turn and event.is_action_pressed("p2_cancel"):
		_cancel()
		return
	if panda_turn and event.is_action_pressed("p2_confirm"):
		_confirm()
		return
	if panda_turn and state == "menu":
		if event.is_action_pressed("p2_attack"):
			choose("attack")
			return
		if event.is_action_pressed("p2_spell"):
			choose("spells")
			return
		if event.is_action_pressed("p2_item"):
			choose("items")
			return
		if event.is_action_pressed("p2_defend"):
			choose("defend")
			return
	if event.is_action_pressed("cancel"):
		_cancel()
		return
	if event.is_action_pressed("confirm"):
		_confirm()
		return
	if event is InputEventKey and event.pressed and state in ["menu", "spells", "items"]:
		var keycode: int = event.keycode if event.keycode != 0 else int(event.physical_keycode)
		var index := int(keycode) - KEY_1
		if index >= 0 and index < menu_ids.size():
			var picked := str(menu_ids[index])
			if picked != "":
				choose(picked)
			return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if active != null and active.kind == "panda" and Pads.panda_uses_pad():
			return
		if _pointer_over_ui():
			return
		var point = _ground(event.position)
		if point == null:
			return
		if (state == "move" or state == "extra_move") and active:
			active.pos = Rules.clamp_move(move_origin, move_radius, Vector3.ZERO, Rules.ARENA_R, point)
			active.visual.face_dir(active.pos - move_origin)
		elif state == "aim":
			_set_aim(point)
			_confirm_aim()


func choose(id: String) -> void:
	if over:
		return
	if state == "menu":
		if id == "attack":
			_begin_aim_attack()
		elif id == "spells":
			_open_spells()
		elif id == "items":
			_open_items()
		elif id == "defend":
			_do_defend()
	elif state == "spells":
		if id == "back":
			_open_menu()
		elif Rules.SPELLS.has(id):
			_begin_aim_spell(id)
	elif state == "items":
		if id == "back":
			_open_menu()
		else:
			_do_item(id)


func force_turn(id: String) -> void:
	var body = fighter(id)
	if body == null:
		return
	_begin_player(body)


func debug_cast(spell_id: String, at: Vector3) -> Dictionary:
	var result: Dictionary = resolve_now(active, Rules.SPELLS[spell_id], at)
	last_messages = result.get("messages", [])
	if not bool(result.get("ok", false)):
		return result
	_present(result)
	if not over:
		_close_turn()
	return result


func debug_apply_attack(at: Vector3, power: int, radius: float) -> void:
	resolve_enemy_hit(fighter("mite_a"), {"name": "test", "power": power, "radius": radius, "root": false}, at)


func debug_run_enemy(id: String) -> void:
	instant = true
	var body = fighter(id)
	if body:
		_enemy_turn(body)


func resolve_now(caster, spell: Dictionary, at: Vector3) -> Dictionary:
	var result := {"ok": true, "floats": [], "messages": []}
	if caster == null or party == null:
		result.ok = false
		return result
	var cost := int(spell.get("mp", 0))
	if cost > 0 and party.mp < cost:
		result.ok = false
		return result
	if cost > 0:
		party.mp -= cost
	var element := str(spell.get("element", ""))
	if element != "":
		result.messages = party.note_cast(element, int(spell.get("xp", 0)))
	var radius := float(spell.get("radius", 0.0))
	var damage := int(spell.get("damage", 0))
	var heal := int(spell.get("heal", 0))
	if damage > 0:
		for enemy in _living("enemy"):
			if Rules.in_circle(enemy.pos, at, radius):
				var dealt := Rules.hurt(damage, enemy.defending, enemy.guard_mult)
				enemy.hp -= dealt
				result.floats.append({"at": enemy.pos, "text": str(dealt), "color": Color(1, 0.86, 0.45)})
				if enemy.visual:
					enemy.visual.flash()
				if enemy.hp <= 0:
					enemy.hp = 0
					enemy.gauge = 0.0
					if enemy.visual:
						enemy.visual.fall()
	if heal > 0:
		var inside: Array = []
		for hero in _heroes():
			if Rules.in_circle(hero.pos, at, radius):
				inside.append(hero)
		if not inside.is_empty():
			var bonus := 8 if inside.size() >= 2 else 0
			for hero in inside:
				var gained: int = party.heal_body(hero.kind, heal + bonus)
				result.floats.append({
					"at": hero.pos,
					"text": "+%d" % gained,
					"color": Color(0.65, 0.95, 0.78),
				})
				if gained > 0 and hero.visual and hero.visual.fallen:
					hero.visual.revive()
	if bool(spell.get("root", false)):
		for enemy in _living("enemy"):
			if Rules.in_circle(enemy.pos, at, radius):
				enemy.root_scale = 0.42
				result.floats.append({"at": enemy.pos + Vector3(0, 0.45, 0), "text": "rooted", "color": Color(0.86, 0.72, 0.42)})
	if bool(spell.get("slow", false)):
		for enemy in _living("enemy"):
			if Rules.in_circle(enemy.pos, at, radius):
				enemy.slow_turns = maxi(enemy.slow_turns, 1)
				result.floats.append({"at": enemy.pos + Vector3(0.2, 0.55, 0), "text": "slow", "color": Color(0.65, 0.82, 1)})
	var push := float(spell.get("push", 0.0))
	if push > 0.0:
		for enemy in _living("enemy"):
			if enemy.hp > 0 and Rules.in_circle(enemy.pos, at, radius):
				var away: Vector3 = enemy.pos - at
				away.y = 0.0
				if away.length() < 0.2:
					away = Vector3(1, 0, 0)
				enemy.pos = Rules.clamp_arena(enemy.pos + away.normalized() * push, Vector3.ZERO, Rules.ARENA_R)
	var guard := float(spell.get("guard", 0.0))
	if guard > 0.0:
		for hero in _living("hero"):
			if Rules.in_circle(hero.pos, at, radius):
				hero.guard_mult = guard
				result.floats.append({"at": hero.pos, "text": "guard", "color": Color(0.82, 0.76, 0.55)})
	_check_end()
	return result


func resolve_enemy_hit(enemy, attack: Dictionary, at: Vector3) -> void:
	if party == null:
		return
	var radius := float(attack.radius)
	var caught := 0
	for hero in _living("hero"):
		if Rules.in_circle(hero.pos, at, radius):
			var dealt := Rules.hurt(int(attack.power), hero.defending, hero.guard_mult)
			party.hurt_body(hero.kind, dealt)
			caught += 1
			_float(hero.pos, str(dealt), Color(1, 0.45, 0.4))
			if hero.visual:
				hero.visual.flash()
				if party.is_up(hero.kind):
					hero.visual.play_once("hit_react")
				else:
					hero.gauge = 0.0
					hero.visual.fall()
			if bool(attack.get("root", false)):
				hero.root_scale = 0.42
				_float(hero.pos + Vector3(0, 0.5, 0), "rooted", Color(0.9, 0.7, 0.4))
	if caught == 0:
		_float(at, "miss", Color(0.85, 0.85, 0.85))
	_check_end()


func _fill(delta: float) -> void:
	for f in fighters:
		if not _is_living(f):
			continue
		var rate: float = f.agility
		if f.slow_turns > 0:
			rate *= 0.58
		f.gauge = minf(100.0, f.gauge + rate * GAUGE_SPEED * delta)


func _maybe_start() -> void:
	if state != "gauge":
		return
	var best = null
	for f in fighters:
		if _is_living(f) and f.gauge >= 100.0 and (best == null or f.gauge > best.gauge):
			best = f
	if best:
		_start_turn(best)


func _start_turn(f) -> void:
	if f.slow_turns > 0:
		f.slow_turns -= 1
	f.gauge = 100.0
	if f.side == "enemy":
		_enemy_turn(f)
	else:
		_begin_player(f)


func _begin_player(f) -> void:
	active = f
	f.defending = false
	f.guard_mult = 1.0
	var rooted: bool = f.root_scale < 0.99
	state = "move"
	move_origin = f.pos
	move_radius = f.move_radius * f.root_scale
	f.root_scale = 1.0
	_show_move_circle()
	var hint := "%s's turn. Walk inside the blue circle, then Space." % f.display
	if f.kind == "panda" and Pads.panda_uses_pad():
		hint = "Panda's turn. Left stick walks the circle. Cross confirms. Square attacks, Triangle casts, L1 item, R1 defend."
	if coach and not coach_used:
		hint += " That circle is the whole step for this action."
		coach_used = true
	if rooted:
		hint += " Stonefoot shortened this step."
	_prompt(hint)
	if hud:
		hud.clear_choices()


func _enemy_turn(f) -> void:
	state = "busy"
	active = f
	if hud:
		hud.clear_choices()
	_hide_aim()
	var step_r: float = f.move_radius * f.root_scale
	var rooted: bool = f.root_scale < 0.99
	f.root_scale = 1.0
	var attack: Dictionary = _pick_attack(f)
	var dest: Vector3 = _plan_dest(f, step_r, attack)
	_prompt("%s moves.%s" % [f.display, " Stonefoot holds them." if rooted else ""])
	move_circle.show_at(f.pos, step_r)
	if not instant:
		await _glide(f, dest)
	else:
		f.pos = dest
	if over:
		return
	var aim: Vector3 = Rules.clamp_aim(f.pos, _plan_aim(f, attack), float(attack.range), Vector3.ZERO, Rules.ARENA_R)
	move_circle.dismiss()
	threat_circle.show_at(aim, float(attack.radius))
	_prompt("%s uses %s. Red is where it lands." % [f.display, attack.name])
	if f.visual:
		f.visual.face_dir(aim - f.pos)
		if f.kind == "mite":
			f.visual.hop()
	if not instant:
		await _wait(0.85)
	else:
		await _wait(0.0)
	if over:
		return
	resolve_enemy_hit(f, attack, aim)
	_hide_circles()
	if over:
		return
	_close_turn()


func _open_menu() -> void:
	if active == null:
		return
	state = "menu"
	_hide_aim()
	var attack_name := "Aimed Shot" if active.kind == "archer" else "Spin Kick"
	menu_ids = ["attack", "spells", "items", "defend"]
	_show_choices([
		{"id": "attack", "label": "1  " + attack_name},
		{"id": "spells", "label": "2  Spell"},
		{"id": "items", "label": "3  Item"},
		{"id": "defend", "label": "4  Defend"},
	])
	var hint := "1 attack, 2 spell, 3 item, 4 defend. Esc walks again."
	if coach:
		hint = "Arrows and the spin kick are physical. Spells spend spirit and grow that element. " + hint
	_prompt(hint)


func _open_spells() -> void:
	state = "spells"
	var rows: Array = []
	menu_ids = []
	var index := 1
	for spec in Rules.spell_rows(party.elements):
		var known := bool(spec.known)
		var label := "%d  %s" % [index, spec.label]
		var disabled: bool = (not known) or party.mp < int(spec.mp)
		if known and party.mp < int(spec.mp):
			label += "  (need spirit)"
		rows.append({
			"id": spec.id if known else "locked",
			"label": label,
			"disabled": disabled or not known,
		})
		menu_ids.append(spec.id if known else "")
		index += 1
	rows.append({"id": "back", "label": "Back"})
	_show_choices(rows)
	_prompt("Pick a spell. Grey ones are locked, or they cost more spirit than you have. Esc goes back.")


func _open_items() -> void:
	state = "items"
	var berries := int(party.items.get("grove_berry", 0))
	var sips := int(party.items.get("spirit_sip", 0))
	menu_ids = ["grove_berry", "spirit_sip"]
	_show_choices([
		{"id": "grove_berry", "label": "1  Grove Berry (%d)  +22 life" % berries, "disabled": berries <= 0},
		{"id": "spirit_sip", "label": "2  Spirit Sip (%d)  +14 spirit" % sips, "disabled": sips <= 0},
		{"id": "back", "label": "Back"},
	])
	_prompt("Items do not grow an element. Esc goes back.")


func _begin_aim_attack() -> void:
	aim_kind = "attack"
	aim_spell = Rules.physical_attack(active.kind)
	_begin_aim()


func _begin_aim_spell(id: String) -> void:
	var spell: Dictionary = Rules.SPELLS[id]
	if party.mp < int(spell.mp):
		_prompt("Not enough spirit for %s." % spell.name)
		return
	aim_kind = "spell"
	aim_spell = spell
	_begin_aim()


func _begin_aim() -> void:
	state = "aim"
	if hud:
		hud.clear_choices()
	var reach := float(aim_spell.get("range", 0.0))
	var self_center := bool(aim_spell.get("self_center", false))
	aim_pos = _default_aim(reach, self_center)
	_place_aim_circle()
	last_mouse = get_viewport().get_mouse_position() if get_viewport() else Vector2.ZERO
	_prompt(_aim_prompt())


func _confirm() -> void:
	if state == "move":
		_open_menu()
	elif state == "extra_move":
		_close_turn()
	elif state == "aim":
		_confirm_aim()


func _cancel() -> void:
	if state == "aim":
		if aim_kind == "spell":
			_open_spells()
		else:
			_open_menu()
	elif state == "spells" or state == "items":
		_open_menu()
	elif state == "menu":
		state = "move"
		_show_move_circle()
		if hud:
			hud.clear_choices()
		_prompt("%s, still walking. Space when you are standing where you want." % active.display)


func _confirm_aim() -> void:
	if state != "aim" or active == null:
		return
	var spell := aim_spell
	var at := aim_pos
	var caster = active
	state = "busy"
	_hide_aim()
	if hud:
		hud.clear_choices()
	_play_and_resolve(caster, spell, at)


func _play_and_resolve(caster, spell: Dictionary, at: Vector3) -> void:
	var extra := float(spell.get("extra_move", 0.0))
	if not instant:
		_play_cast_visual(caster, spell, at)
		await _wait(0.22)
	if over:
		return
	var result := resolve_now(caster, spell, at)
	last_messages = result.get("messages", [])
	if not bool(result.get("ok", false)):
		_prompt("Not enough spirit.")
		_open_spells()
		return
	_present(result)
	if over:
		return
	if extra > 0.0 and caster == active and _is_living(caster):
		state = "extra_move"
		move_origin = caster.pos
		move_radius = extra
		_show_move_circle()
		_prompt("Slipstream gives a free step. Walk, then Space.")
		return
	_close_turn()


func _do_defend() -> void:
	if active == null:
		return
	active.defending = true
	_float(active.pos, "defend", Color(0.8, 0.86, 0.95))
	if active.visual:
		active.visual.play_once("dodge")
	_prompt("%s braces. Hits that catch them are halved until their next turn." % active.display)
	_close_turn()


func _do_item(id: String) -> void:
	if active == null:
		return
	if int(party.items.get(id, 0)) <= 0:
		_prompt("You do not have that.")
		return
	var msg := str(party.use_item(id, active.kind))
	_float(active.pos, msg, Color(0.7, 0.95, 0.7))
	_prompt(msg)
	_close_turn()


func _close_turn() -> void:
	if over:
		return
	if active:
		active.gauge = 0.0
		if active.visual:
			active.visual.set_moving(false)
	active = null
	state = "gauge"
	_hide_circles()
	if hud:
		hud.clear_choices()
	_prompt("Gauges are filling.")
	_check_end()


func _check_end() -> bool:
	if over or party == null:
		return over
	if not party.any_up():
		_finish(false)
		return true
	for f in fighters:
		if f.side == "enemy" and f.hp > 0:
			return false
	if fighters.is_empty():
		return false
	_finish(true)
	return true


func _finish(victory: bool) -> void:
	if over:
		return
	over = true
	state = "victory" if victory else "defeat"
	_hide_circles()
	if hud:
		hud.clear_choices()
	for f in fighters:
		if f.side == "hero" and f.visual:
			f.visual.play_once("victory" if victory else "defeat")
	battle_over.emit(victory)


func _steer_body(delta: float) -> void:
	var input := _move_input()
	if input.length() < 0.08 or active == null or active.visual == null:
		if active and active.visual:
			active.visual.set_moving(false)
		return
	var dir := _input_dir(input)
	if dir.length() < 0.01:
		return
	var pos: Vector3 = active.pos + dir * 6.2 * delta
	active.pos = Rules.clamp_move(move_origin, move_radius, Vector3.ZERO, Rules.ARENA_R, pos)
	active.visual.face_dir(dir)
	active.visual.set_moving(true)


func _steer_aim(delta: float) -> void:
	if aim_spell.is_empty():
		return
	if bool(aim_spell.get("self_center", false)):
		aim_pos = active.pos if active else aim_pos
		_place_aim_circle()
		return
	var input := _aim_input()
	var moved := false
	if input.length() > 0.08:
		aim_pos += _input_dir(input) * 8.0 * delta
		moved = true
	elif not _pad_owns_panda() and get_viewport():
		var mouse := get_viewport().get_mouse_position()
		if mouse.distance_to(last_mouse) > 3.0:
			var point = _ground(mouse)
			if point != null:
				aim_pos = point
				moved = true
		last_mouse = mouse
	aim_pos = Rules.clamp_aim(active.pos, aim_pos, float(aim_spell.get("range", 0.0)), Vector3.ZERO, Rules.ARENA_R)
	_place_aim_circle()
	if moved:
		_prompt(_aim_prompt())


func _pad_owns_panda() -> bool:
	return active != null and active.kind == "panda" and Pads.panda_uses_pad()


func _move_input() -> Vector2:
	if _pad_owns_panda():
		var stick := Pads.left_stick()
		var dpad := _dpad_vector()
		if stick.length() > 0.01:
			return stick
		return dpad
	return Input.get_vector("move_left", "move_right", "move_forward", "move_back")


func _aim_input() -> Vector2:
	if _pad_owns_panda():
		var stick := Pads.right_stick()
		if stick.length() < 0.01:
			stick = Pads.left_stick()
		var dpad := _dpad_vector()
		if stick.length() > 0.01:
			return stick
		return dpad
	return Input.get_vector("move_left", "move_right", "move_forward", "move_back")


func _dpad_vector() -> Vector2:
	if not Pads.connected():
		return Vector2.ZERO
	var v := Vector2.ZERO
	if Input.is_joy_button_pressed(0, JOY_BUTTON_DPAD_LEFT):
		v.x -= 1.0
	if Input.is_joy_button_pressed(0, JOY_BUTTON_DPAD_RIGHT):
		v.x += 1.0
	if Input.is_joy_button_pressed(0, JOY_BUTTON_DPAD_UP):
		v.y -= 1.0
	if Input.is_joy_button_pressed(0, JOY_BUTTON_DPAD_DOWN):
		v.y += 1.0
	return v


func _input_dir(input: Vector2) -> Vector3:
	var look := Vector3(-sin(camera_yaw), 0.0, -cos(camera_yaw))
	var right := Vector3(cos(camera_yaw), 0.0, -sin(camera_yaw))
	var dir := right * input.x + look * -input.y
	return dir.normalized() if dir.length() > 0.001 else Vector3.ZERO


func _default_aim(reach: float, self_center: bool) -> Vector3:
	if active == null:
		return Vector3.ZERO
	if self_center or reach <= 0.0:
		return active.pos
	var target = _nearest(active.pos, _living("enemy"))
	var dest: Vector3 = active.pos + Vector3(0, 0, -1) * minf(reach, 2.0)
	if target:
		dest = target.pos
	return Rules.clamp_aim(active.pos, dest, reach, Vector3.ZERO, Rules.ARENA_R)


func _set_aim(point: Vector3) -> void:
	var reach := float(aim_spell.get("range", 0.0))
	if bool(aim_spell.get("self_center", false)):
		aim_pos = active.pos
	else:
		aim_pos = Rules.clamp_aim(active.pos, point, reach, Vector3.ZERO, Rules.ARENA_R)
	_place_aim_circle()


func _aim_prompt() -> String:
	var text := "%s. Circle radius %.1f m." % [aim_spell.get("name", "Aim"), float(aim_spell.get("radius", 0.0))]
	if bool(aim_spell.get("self_center", false)):
		text += " It stays on you. Space to cast."
	else:
		text += " Move the mouse or the arrows, then Space or click."
	if int(aim_spell.get("damage", 0)) > 0:
		var count := 0
		for enemy in _living("enemy"):
			if Rules.in_circle(enemy.pos, aim_pos, float(aim_spell.radius)):
				count += 1
		if count == 0:
			text += " Nobody is inside yet."
	elif int(aim_spell.get("heal", 0)) > 0:
		text += " Allies inside are healed."
	return text


func _pick_attack(f) -> Dictionary:
	var list: Array = Rules.ATTACKS[f.kind]
	var attack: Dictionary = list[f.attack_index % list.size()]
	f.attack_index += 1
	return attack


func _plan_dest(f, step_r: float, attack: Dictionary) -> Vector3:
	var target = _nearest(f.pos, _living("hero"))
	if target == null:
		return f.pos
	var desired := 1.5
	if f.kind == "lurker":
		desired = 4.4
	elif f.kind == "boss":
		desired = 3.3 if str(attack.name) == "Jar Slam" else 5.0
	elif f.kind == "warrior":
		desired = 2.3
	var dist := Rules.flat(f.pos, target.pos)
	var dest: Vector3 = f.pos
	if dist > desired + 0.3:
		dest = _move_toward(f.pos, target.pos, step_r)
	elif dist < maxf(0.4, desired - 0.6):
		var away: Vector3 = f.pos - target.pos
		away.y = 0.0
		if away.length() < 0.1:
			away = Vector3(1, 0, 0)
		dest = f.pos + away.normalized() * step_r
	else:
		var side := Vector3(-(target.pos.z - f.pos.z), 0.0, target.pos.x - f.pos.x)
		if side.length() > 0.1:
			dest = f.pos + side.normalized() * minf(step_r, 1.2)
	return Rules.clamp_move(f.pos, step_r, Vector3.ZERO, Rules.ARENA_R, dest)


func _plan_aim(f, attack: Dictionary) -> Vector3:
	var heroes := _living("hero")
	if f.kind == "boss" and str(attack.name) == "Jar Slam" and heroes.size() >= 2:
		if Rules.flat(heroes[0].pos, heroes[1].pos) <= 3.2:
			return (heroes[0].pos + heroes[1].pos) * 0.5
	var target = _nearest(f.pos, heroes)
	if target == null:
		return f.pos
	return target.pos


func _move_toward(a: Vector3, b: Vector3, step: float) -> Vector3:
	var d := b - a
	d.y = 0.0
	if d.length() <= step:
		return Vector3(b.x, 0.0, b.z)
	return a + d.normalized() * step


func _living(side: String) -> Array:
	var out: Array = []
	for f in fighters:
		if f.side == side and _is_living(f):
			out.append(f)
	return out


func _is_living(f) -> bool:
	if f == null:
		return false
	if f.side == "enemy":
		return f.hp > 0
	return party != null and party.is_up(f.kind)


func _heroes() -> Array:
	var out: Array = []
	for f in fighters:
		if f.side == "hero":
			out.append(f)
	return out


func _nearest(from: Vector3, group: Array):
	var best = null
	var best_d := 1e9
	for f in group:
		var d := Rules.flat(from, f.pos)
		if d < best_d:
			best_d = d
			best = f
	return best


func _play_cast_visual(caster, spell: Dictionary, at: Vector3) -> void:
	if caster == null or caster.visual == null:
		return
	caster.visual.face_dir(at - caster.pos)
	var spell_name := str(spell.get("name", ""))
	if caster.kind == "archer":
		caster.visual.play_once("attack_arrow")
	elif spell_name == "Spin Kick":
		caster.visual.spin()
	else:
		caster.visual.flash()
	if spell_name == "Aimed Shot":
		_shot(caster.pos + Vector3(0, 1.2, 0), at + Vector3(0, 0.4, 0), Color("e6c36a"), 0.06)
	elif spell_name == "Skyfang Bolt":
		_shot(caster.pos + Vector3(0, 0.9, 0), at + Vector3(0, 0.3, 0), Color("b7f3ff"), 0.12)


func _shot(a: Vector3, b: Vector3, color: Color, thick: float) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(1, 1, 1)
	mesh.mesh = box
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 2.0
	mat.albedo_color = color
	mesh.material_override = mat
	add_child(mesh)
	var diff := b - a
	var length := Vector2(diff.x, diff.z).length()
	mesh.global_position = (a + b) * 0.5
	if length > 0.05:
		mesh.look_at(Vector3(b.x, mesh.global_position.y, b.z), Vector3.UP)
	mesh.scale = Vector3(thick, thick, maxf(length, 0.1))
	var tw := create_tween()
	tw.tween_interval(0.18)
	tw.finished.connect(mesh.queue_free)


func _present(result: Dictionary) -> void:
	for msg in result.get("messages", []):
		if hud:
			hud.toast(str(msg))
	for fl in result.get("floats", []):
		_float(fl.at, str(fl.text), fl.color)


func _float(at: Vector3, text: String, color: Color) -> void:
	if instant:
		return
	var label := Label3D.new()
	label.text = text
	label.font_size = 48
	label.pixel_size = 0.01
	label.modulate = color
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 6
	label.position = at + Vector3(0, 1.5, 0)
	label.no_depth_test = true
	add_child(label)
	var tw := create_tween()
	tw.tween_property(label, "position:y", label.position.y + 1.1, 0.7)
	tw.parallel().tween_property(label, "modulate:a", 0.0, 0.7)
	tw.finished.connect(label.queue_free)


func _sync() -> void:
	for f in fighters:
		if f.visual:
			f.visual.position = f.pos


func _show_move_circle() -> void:
	move_circle.show_at(move_origin, move_radius)


func _place_aim_circle() -> void:
	var color := _aim_color(aim_spell)
	aim_circle.set_color(color)
	aim_circle.show_at(aim_pos, float(aim_spell.get("radius", 0.5)))
	if active == null:
		aim_line.visible = false
		return
	var a: Vector3 = active.pos + Vector3(0, 0.35, 0)
	var b: Vector3 = aim_pos + Vector3(0, 0.35, 0)
	var diff: Vector3 = b - a
	var length := Vector2(diff.x, diff.z).length()
	if length < 0.2:
		aim_line.visible = false
		return
	aim_line.visible = true
	aim_line.global_position = (a + b) * 0.5
	aim_line.look_at(Vector3(b.x, aim_line.global_position.y, b.z), Vector3.UP)
	aim_line.scale = Vector3(0.055, 0.055, length)
	var mat := aim_line.material_override as StandardMaterial3D
	if mat:
		mat.albedo_color = Color(color.r, color.g, color.b, 0.8)


func _aim_color(spell: Dictionary) -> Color:
	var element := str(spell.get("element", ""))
	if Rules.ELEMENT_COLOR.has(element):
		var base: Color = Rules.ELEMENT_COLOR[element]
		return Color(base.r, base.g, base.b, 0.42)
	return Color(0.95, 0.78, 0.35, 0.42)


func _hide_circles() -> void:
	move_circle.dismiss()
	_hide_aim()
	threat_circle.dismiss()


func _hide_aim() -> void:
	aim_circle.dismiss()
	aim_line.visible = false


func _prompt(text: String) -> void:
	if hud:
		hud.set_prompt(text)


func _show_choices(rows: Array) -> void:
	if hud:
		hud.show_choices(rows)


func _refresh_rows() -> void:
	if hud == null or not hud.battle_panel.visible:
		return
	var entries: Array = []
	for f in fighters:
		entries.append({
			"id": f.id,
			"display": f.display,
			"side": f.side,
			"gauge": f.gauge,
			"hp": f.hp,
			"hp_max": f.hp_max,
			"active": active == f,
		})
	hud.set_rows(entries)


func _pointer_over_ui() -> bool:
	if hud == null:
		return false
	var mouse := get_viewport().get_mouse_position()
	for button in hud.choice_bar.get_children():
		if button is Control and button.visible and button.get_global_rect().has_point(mouse):
			return true
	return false


func _ground(screen: Vector2):
	var cam := get_viewport().get_camera_3d() if get_viewport() else null
	if cam == null:
		return null
	var origin := cam.project_ray_origin(screen)
	var dir := cam.project_ray_normal(screen)
	if absf(dir.y) < 0.00001:
		return null
	var t := -origin.y / dir.y
	if t < 0.0:
		return null
	return origin + dir * t


func _wait(seconds: float) -> void:
	if instant or seconds <= 0.0:
		await get_tree().process_frame
		return
	await get_tree().create_timer(seconds).timeout


func _glide(body, dest: Vector3) -> void:
	var start: Vector3 = body.pos
	var dist := Rules.flat(start, dest)
	var duration := clampf(dist / 4.5, 0.15, 0.7)
	var t := 0.0
	if body.visual:
		body.visual.face_dir(dest - start)
		body.visual.set_moving(dist > 0.05)
	while t < duration:
		if over:
			return
		t += get_process_delta_time()
		body.pos = start.lerp(dest, clampf(t / duration, 0.0, 1.0))
		await get_tree().process_frame
	body.pos = dest
	if body.visual:
		body.visual.set_moving(false)


func _clear_field() -> void:
	var old := field.get_children()
	for child in old:
		field.remove_child(child)
		child.free()
	fighters.clear()
	active = null


func _spawn_pair() -> void:
	_add_hero("archer", "Archer", Vector3(-1.35, 0, 5.4), 12.0, 4.55)
	_add_hero("panda", "Panda", Vector3(1.35, 0, 6.15), 10.0, 4.15)


func _add_hero(id: String, display: String, pos: Vector3, agility: float, move_r: float) -> void:
	var body = Fighter.new()
	body.id = id
	body.kind = id
	body.side = "hero"
	body.display = display
	body.agility = agility
	body.move_radius = move_r
	body.pos = pos
	body.visual = _visual(id, display, pos)
	fighters.append(body)


func _spawn_enemies() -> void:
	for spec in encounter.enemies:
		var body = Fighter.new()
		body.id = spec.id
		body.kind = spec.kind
		body.side = "enemy"
		body.display = spec.name
		body.hp = int(spec.hp)
		body.hp_max = int(spec.hp)
		body.agility = float(spec.agility)
		body.move_radius = float(spec.move)
		body.pos = Vector3(spec.pos[0], 0, spec.pos[1])
		body.visual = _visual(spec.kind, spec.name, body.pos)
		fighters.append(body)


func _visual(kind: String, label_text: String, pos: Vector3) -> Node3D:
	var visual := ActorVisual.new()
	field.add_child(visual)
	visual.configure(kind, label_text)
	visual.position = pos
	return visual


func _build_theme(theme: String) -> void:
	var ground := Color("7ea354")
	if theme == "grove":
		ground = Color("3f6846")
	elif theme == "ruin":
		ground = Color("8d877c")
	var disc := Props.cylinder(Rules.ARENA_R + 1.5, 0.2, ground, Vector3(0, -0.1, 0))
	disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	field.add_child(disc)
	for i in 18:
		var angle := TAU * float(i) / 18.0
		var radius := Rules.ARENA_R + 0.85
		var post := Props.cylinder(0.12, 1.15, Color("6b4e32") if theme != "ruin" else Color("9a948c"), Vector3(sin(angle) * radius, 0.55, cos(angle) * radius))
		field.add_child(post)
	if theme == "meadow":
		for spot in [Vector3(-4.2, 0, -1.5), Vector3(3.6, 0, 1.2), Vector3(-2.2, 0, 2.4)]:
			field.add_child(Props.sphere(0.16, Color("f2d36b"), spot + Vector3(0, 0.16, 0)))
	elif theme == "grove":
		for spot in [Vector3(-5.0, 0, -1.0), Vector3(5.1, 0, 0.4), Vector3(-3.2, 0, -5.2)]:
			field.add_child(Props.cylinder(0.18, 1.3, Color("4a3428"), spot + Vector3(0, 0.65, 0)))
			field.add_child(Props.sphere(0.7, Color("2f6a40"), spot + Vector3(0, 1.55, 0)))
	else:
		for spot in [Vector3(-4.6, 0, -2.8), Vector3(4.7, 0, -2.2), Vector3(0.2, 0, -6.2)]:
			field.add_child(Props.cylinder(0.35, 1.8, Color("b1aaa0"), spot + Vector3(0, 0.9, 0)))
			field.add_child(Props.cylinder(0.16, 0.38, Color("c4a574"), spot + Vector3(0.7, 0.24, 0.4)))
	var north := Label3D.new()
	north.text = "N"
	north.font_size = 64
	north.pixel_size = 0.012
	north.position = Vector3(0, 0.25, -(Rules.ARENA_R - 0.3))
	north.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	field.add_child(north)
