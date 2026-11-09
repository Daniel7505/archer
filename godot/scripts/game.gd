extends Node3D

const PartyState = preload("res://scripts/party_state.gd")
const Rules = preload("res://scripts/rules.gd")
const OverworldScript = preload("res://scripts/overworld.gd")
const BattleScript = preload("res://scripts/battle.gd")
const HudScript = preload("res://scripts/hud.gd")

enum Mode { TITLE, PLAY, TALK, BOOK, BATTLE, LEVELUP, DEFEAT, ENDING }

const INTRO := [
	"Lina: You already settled the fight between you. The pack still holds Grubbo's buckle, his comb, some coins, and the Mystery Shard.",
	"Lina: Mosswick corked the wicklights on the way. That is early trouble, not the whole road.",
	"Lina: This yard is home. The first stop is close: Quill's stall, on the east road, this side of the grove.",
	"Archer: We walk it together.",
	"Panda: And we do not stand in the same red circle.",
]

const ENDING := [
	"Mosswick sits down. His pockets are empty, and he looks smaller.",
	"The jars pop. Wicklights rise and sit in the branches like candles that learned to float.",
	"The panda bumps the archer's shoulder. Neither of them did it alone.",
	"The grove is awake.",
]

var party = PartyState.new()
var mode: int = Mode.TITLE
var overworld: Node3D
var battle: Node3D
var hud: CanvasLayer
var camera: Camera3D
var sun: DirectionalLight3D
var cam_yaw := 0.2
var cam_dist := 11.5
var cam_height := 8.0
var cam_pitch := 0.58
const PITCH_MIN := 0.12
const PITCH_MAX := 1.05
var cam_snap := true
var viewing_battle := false
var dialogue: Array = []
var dialogue_i := 0
var dialogue_then: Callable = Callable()
var after_points: Callable = Callable()
var battle_snapshot: Dictionary = {}
var current_battle := ""
var current_foe := ""
var instant_transitions := false
var panel_ids: Array = []
var music: AudioStreamPlayer


func _ready() -> void:
	_register_inputs()
	_build_world()
	_show_title()


func _process(delta: float) -> void:
	if mode == Mode.TITLE:
		cam_yaw += delta * 0.06
	if Input.is_action_pressed("camera_left"):
		cam_yaw -= delta * 1.35
	if Input.is_action_pressed("camera_right"):
		cam_yaw += delta * 1.35
	if overworld:
		overworld.yaw = cam_yaw
	if battle:
		battle.camera_yaw = cam_yaw
	_update_camera(delta)
	if hud and party:
		hud.set_vitals(party)
		if viewing_battle and Rules.ENCOUNTERS.has(current_battle):
			hud.set_region(Rules.ENCOUNTERS[current_battle].title)
		elif overworld and mode != Mode.TITLE:
			hud.set_region(overworld.region_name())
		if mode == Mode.PLAY:
			var hint := "WASD walk. Space jumps. Right-drag looks around. F talk. B book."
			if overworld.coop_active():
				hint = "Co-op. Archer WASD, Space jumps. Panda left stick. Right-drag looks around. F talk. B book."
			if party.pending_points > 0:
				hint = "Element points to place. Press B.  " + hint
			hud.set_prompt(hint)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			cam_dist = clampf(cam_dist - 1.1, 7.0, 18.0)
			return
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			cam_dist = clampf(cam_dist + 1.1, 7.0, 18.0)
			return
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		cam_yaw -= event.relative.x * 0.006
		nudge_camera_pitch(event.relative.y * 0.004)
		return
	if event is InputEventKey and event.echo:
		return
	match mode:
		Mode.TITLE:
			if event.is_action_pressed("confirm"):
				_begin_game()
		Mode.PLAY:
			if event.is_action_pressed("interact") and overworld:
				overworld.interact()
			elif event.is_action_pressed("book"):
				_open_book()
		Mode.TALK:
			if event.is_action_pressed("confirm") or event.is_action_pressed("cancel"):
				_advance_talk()
		Mode.BATTLE:
			if battle:
				battle.input_event(event)
		Mode.BOOK:
			if event.is_action_pressed("cancel"):
				_close_book()
			else:
				_panel_number(event)
		Mode.LEVELUP, Mode.DEFEAT, Mode.ENDING:
			_panel_number(event)


func _on_choice(id: String) -> void:
	if id.begins_with("point_"):
		_spend_from_ui(id.trim_prefix("point_"))
		return
	match mode:
		Mode.TITLE:
			if id == "begin":
				_begin_game()
		Mode.BATTLE:
			if battle:
				battle.choose(id)
		Mode.DEFEAT:
			if id == "retry":
				_retry()
			elif id == "camp":
				_back_camp()
		Mode.ENDING:
			if id == "walk":
				hud.hide_text_panel()
				mode = Mode.PLAY
				overworld.active = true
		Mode.BOOK:
			if id == "close":
				_close_book()


func debug_skip_title() -> void:
	party.intro_done = true
	hud.hide_text_panel()
	mode = Mode.PLAY
	overworld.active = true
	_apply_play_cam()


func debug_battle(id: String) -> void:
	instant_transitions = true
	current_foe = ""
	battle_snapshot = party.snapshot()
	current_battle = id
	mode = Mode.BATTLE
	overworld.active = false
	overworld.visible = false
	battle.visible = true
	viewing_battle = true
	hud.set_battle_mode(true)
	battle.instant = true
	battle.begin(id, party, true)
	battle.force_turn("archer")


func debug_touch(foe_id: String) -> void:
	instant_transitions = true
	var battle_id := str(overworld.foes[foe_id].battle)
	_on_encounter(battle_id, foe_id)


func debug_finish_battle() -> void:
	instant_transitions = true
	for fighter in battle.fighters:
		if fighter.side == "enemy":
			fighter.hp = 0
	battle._check_end()


func _register_inputs() -> void:
	_bind("move_forward", KEY_W)
	_bind("move_forward", KEY_UP)
	_bind("move_back", KEY_S)
	_bind("move_back", KEY_DOWN)
	_bind("move_left", KEY_A)
	_bind("move_left", KEY_LEFT)
	_bind("move_right", KEY_D)
	_bind("move_right", KEY_RIGHT)
	_bind("confirm", KEY_SPACE)
	_bind("confirm", KEY_ENTER)
	_bind("jump", KEY_SPACE)
	_bind("confirm", KEY_KP_ENTER)
	_bind("cancel", KEY_ESCAPE)
	_bind("interact", KEY_F)
	_bind("book", KEY_B)
	_bind("camera_left", KEY_Q)
	_bind("camera_right", KEY_R)
	_bind_joy("p2_confirm", JOY_BUTTON_A)
	_bind_joy("p2_cancel", JOY_BUTTON_B)
	_bind_joy("p2_attack", JOY_BUTTON_X)
	_bind_joy("p2_spell", JOY_BUTTON_Y)
	_bind_joy("p2_item", JOY_BUTTON_LEFT_SHOULDER)
	_bind_joy("p2_defend", JOY_BUTTON_RIGHT_SHOULDER)


func _bind_joy(action: String, button: JoyButton) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventJoypadButton.new()
	ev.device = 0
	ev.button_index = button
	InputMap.action_add_event(action, ev)


func _bind(action: String, key: Key) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventKey.new()
	ev.physical_keycode = key
	InputMap.action_add_event(action, ev)


func _build_world() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color("8eb8d4")
	sky_mat.sky_horizon_color = Color("f3c98a")
	sky_mat.ground_bottom_color = Color("6d8a48")
	sky_mat.ground_horizon_color = Color("e7c48a")
	sky_mat.sun_angle_max = 32.0
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.12
	env.fog_enabled = true
	env.fog_light_color = Color("f0d7b0")
	env.fog_density = 0.00072
	env.fog_aerial_perspective = 0.25
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -38, 0)
	sun.light_color = Color("ffe2b0")
	sun.light_energy = 1.35
	sun.shadow_enabled = DisplayServer.get_name() != "headless"
	sun.directional_shadow_max_distance = 220.0
	add_child(sun)

	camera = Camera3D.new()
	camera.current = true
	camera.fov = 55.0
	add_child(camera)

	hud = HudScript.new()
	hud.name = "HUD"
	add_child(hud)
	hud.choice.connect(_on_choice)

	overworld = OverworldScript.new()
	overworld.name = "Overworld"
	add_child(overworld)
	overworld.party = party
	overworld.build()
	overworld.encounter_hit.connect(_on_encounter)
	overworld.lina_talk.connect(_talk_lina)
	overworld.sign_read.connect(_on_sign)
	overworld.pickup_found.connect(_on_pickup)
	overworld.npc_talk.connect(_on_npc)

	battle = BattleScript.new()
	battle.name = "Battle"
	add_child(battle)
	battle.visible = false
	battle.hud = hud
	battle.battle_over.connect(_on_battle_over)


func _show_title() -> void:
	mode = Mode.TITLE
	overworld.active = false
	_apply_play_cam()
	var body := "A short original quest for Nick and Suni.\n\nThe archer and the panda are already partners. The wicklights are trouble on the road to Aldermoor, not the end of it. Seven cursed orbs are only a whisper so far.\n\nOne keyboard walks the archer. A PlayStation controller, if you plug one in, walks the panda.\n\nWASD to walk. Space to begin.\n\nGrok Bot wrote the words, for Nick and Suni."
	_show_panel("Wicklight Grove", body, [{"id": "begin", "label": "Begin"}])


func _begin_game() -> void:
	if mode != Mode.TITLE:
		return
	hud.hide_text_panel()
	panel_ids.clear()
	_start_music()
	if party.intro_done:
		mode = Mode.PLAY
		overworld.active = true
		return
	_say(INTRO, _after_intro)


func _after_intro() -> void:
	party.intro_done = true
	party.full_rest()
	_open_book()


func _talk_lina() -> void:
	if not party.intro_done:
		_say(INTRO, _after_intro)
		return
	var lines: Array = []
	if party.ending_seen:
		lines.append("Lina: You brought the lights home. The tea tastes brighter.")
	elif party.cleared.grove:
		lines.append("Lina: The lurker is a poor doorman. The stair is north through the trees, when you want it.")
	elif party.cleared.meadow:
		lines.append("Lina: You came back. Lamb Hill and Pebble Creek are still there if the mites can wait.")
	else:
		lines.append("Lina: This yard is home. Come back when you need the breath.")
	lines.append("Lina: Quill's stall is east, on the stone road, this side of the grove. That is the next talk.")
	lines.append("Lina: Sit. Pears, tea, and a full breath.")
	_say(lines, _do_rest)


func _do_rest() -> void:
	party.full_rest()
	hud.toast("Life and spirit restored. Berries refilled.")
	mode = Mode.PLAY
	overworld.active = true


func _on_npc(who: String) -> void:
	if who == "quill":
		_say([
			"Peddler Quill: Berries, news, and no shards. I do not buy what came off Grubbo.",
			"Peddler Quill: The next talk is Seer Ilvane, at the valley gate. White pillars, a blue door. You can see them from this road.",
			"Peddler Quill: She will not take the shard. She will point you into the fields.",
		], Callable())
	elif who == "ilvane":
		party.heard_orbs = true
		_say([
			"Ilvane: I am the seer. I will not take the Mystery Shard. It is not a coin.",
			"Ilvane: There are seven cursed orbs. The shard is a whisper of one of them. The work is called Whispers of the Orb.",
			"Ilvane: This gate opens the outer fields. Stop at Briarwell, the blue roofs just off the road.",
			"Ilvane: A warrior named Holt stands the road before Aldermoor's wall. The city doors stay shut.",
		], Callable())
	elif who == "briar":
		_say([
			"Neighbor: You found Briarwell. The next fire is Wayside Camp, still on the road, closer to the white wall.",
			"Neighbor: Holt is the warrior. The ring is on the road ahead of that camp. Do not look for a city door.",
		], Callable())
	elif who == "wayside":
		_say([
			"Watcher: Holt is ahead of you, on the road, this side of the wall. The red ring marks the warrior.",
			"Watcher: Walk up and you will see them. The doors behind them stay shut.",
		], Callable())


func _on_sign(text: String) -> void:
	_say([text], Callable())


func _on_pickup(kind: String, note: String) -> void:
	if kind == "berry":
		var count := party.add_item("grove_berry", 1)
		hud.toast("Grove Berry. You are carrying %d." % count)
	elif kind == "sip":
		var count := party.add_item("spirit_sip", 1)
		hud.toast("Spirit Sip. You are carrying %d." % count)
	elif kind == "note" and note != "":
		_say([note], Callable())


func _on_encounter(battle_id: String, foe_id: String) -> void:
	if party.pending_points > 0:
		overworld.nudge_from_foe(foe_id)
		overworld.active = true
		_say(["Place your element points before the next fight. Press B."], Callable())
		return
	current_foe = foe_id
	_begin_from_map(battle_id)


func _begin_from_map(id: String) -> void:
	battle_snapshot = party.snapshot()
	current_battle = id
	overworld.active = false
	await _fade(1.0)
	mode = Mode.BATTLE
	overworld.visible = false
	battle.visible = true
	hud.set_battle_mode(true)
	_apply_battle_cam()
	battle.instant = instant_transitions
	battle.begin(id, party, instant_transitions)
	await _fade(0.0)
	var intro := str(Rules.ENCOUNTERS[id].get("intro", ""))
	if intro != "":
		hud.toast(intro)


func _on_battle_over(victory: bool) -> void:
	if victory:
		var enc: Dictionary = Rules.ENCOUNTERS[current_battle]
		var levels: int = party.grant_victory_xp(int(enc.xp))
		var region := str(enc.get("region", ""))
		if region == "meadow":
			party.cleared.meadow = true
		elif current_battle == "lurker":
			party.cleared.grove = true
		elif current_battle == "stair":
			party.cleared.stair = true
		if current_foe != "":
			overworld.on_foe_beaten(current_foe)
		if levels > 0:
			hud.toast("Level %d. Place %d element points." % [party.level, party.pending_points])
		var afterwards := func():
			if bool(enc.get("boss", false)):
				_start_ending()
			else:
				_leave_battle(str(enc.win))
		if party.pending_points > 0:
			_open_levelup(afterwards)
		else:
			afterwards.call()
	else:
		_open_defeat()


func _leave_battle(line: String) -> void:
	await _fade(1.0)
	battle.clear_for_exit()
	battle.visible = false
	overworld.visible = true
	if current_foe != "":
		overworld.nudge_from_foe(current_foe)
	hud.set_battle_mode(false)
	hud.clear_choices()
	_apply_play_cam()
	await _fade(0.0)
	mode = Mode.PLAY
	overworld.active = true
	current_foe = ""
	if line != "":
		hud.toast(line)


func _open_defeat() -> void:
	mode = Mode.DEFEAT
	_show_panel(
		"The jars stay shut",
		"The wicklights are still waiting.\n\nTry this battle again, or walk back to Lina. Her tea puts you back together, and this fight's spirit growth is undone.",
		[
			{"id": "retry", "label": "1  Try again"},
			{"id": "camp", "label": "2  Back to camp"},
		]
	)


func _retry() -> void:
	party.restore(battle_snapshot)
	hud.hide_text_panel()
	panel_ids.clear()
	mode = Mode.BATTLE
	hud.set_battle_mode(true)
	battle.begin(current_battle, party, false)


func _back_camp() -> void:
	party.restore(battle_snapshot)
	party.full_rest()
	current_foe = ""
	battle.clear_for_exit()
	battle.visible = false
	overworld.visible = true
	overworld.place(Vector3(0, 0, 12))
	hud.hide_text_panel()
	hud.set_battle_mode(false)
	panel_ids.clear()
	_apply_play_cam()
	mode = Mode.PLAY
	overworld.active = true
	hud.toast("Lina's tea puts you back together.")


func _start_ending() -> void:
	party.ending_seen = true
	await _fade(1.0)
	battle.clear_for_exit()
	battle.visible = false
	overworld.visible = true
	overworld.celebrate()
	overworld.play_thanks()
	hud.set_battle_mode(false)
	_apply_play_cam()
	await _fade(0.0)
	_say(ENDING, _show_ending_card)


func _show_ending_card() -> void:
	mode = Mode.ENDING
	overworld.active = false
	_show_panel("The grove is awake", "Happy Christmas, Nick and Suni.", [{"id": "walk", "label": "Walk the bright grove"}])


func _open_levelup(then: Callable) -> void:
	mode = Mode.LEVELUP
	after_points = then
	overworld.active = false
	_refresh_levelup()


func _refresh_levelup() -> void:
	var body := "Level %d. Place one point into an element.\n%d left.\n\nA point raises that element by one level. Level 3 learns the stronger spell.\n\n%s" % [party.level, party.pending_points, _element_status()]
	var choices: Array = []
	var index := 1
	for id in ["earth", "water", "fire", "wind"]:
		choices.append({"id": "point_" + id, "label": "%d  %s" % [index, id.capitalize()]})
		index += 1
	_show_panel("A quiet level", body, choices)


func _open_book() -> void:
	mode = Mode.BOOK
	overworld.active = false
	_refresh_book()


func _refresh_book() -> void:
	var body := "Grok Bot wrote the words, for Nick and Suni.\n\n"
	body += "Cast a spell and that element grows. Level 3 unlocks its stronger spell. A character level also gives points you can place.\n\n"
	body += "Level %d    next at %d xp (%d/%d)\n" % [party.level, party.xp_to_next, party.xp, party.xp_to_next]
	body += "Archer %d/%d    Panda %d/%d    Shared spirit %d/%d\n\n" % [party.archer_hp, party.archer_hp_max, party.panda_hp, party.panda_hp_max, party.mp, party.mp_max]
	body += "Pack, from Grubbo: Gold-Coin Buckle, Moustache Comb, Mystery Shard, a handful of coins.\n"
	if party.heard_orbs:
		body += "Quest: Whispers of the Orb. Seven cursed orbs. The shard stays in the pack.\n"
	else:
		body += "The shard is unsolved. The Aldermoor road is east of the meadow.\n"
	body += "The spirit panda is a mount for a later stretch of road.\n\n"
	body += _element_status()
	body += "\n\nArcher: Aimed Shot, a small long circle. Panda: Spin Kick, close and wide. The panda's lightning is Skyfang Bolt, a wind spell.\n"
	body += "Each of you has a life. Spirit is shared. A red circle hurts every body it catches.\n"
	body += "Grove berries %d    Spirit sips %d" % [int(party.items.grove_berry), int(party.items.spirit_sip)]
	var choices: Array = []
	var index := 1
	if party.pending_points > 0:
		body = "%d point%s waiting.\n\n" % [party.pending_points, "" if party.pending_points == 1 else "s"] + body
		for id in ["earth", "water", "fire", "wind"]:
			choices.append({"id": "point_" + id, "label": "%d  %s" % [index, id.capitalize()]})
			index += 1
	choices.append({"id": "close", "label": "%d  Close" % index})
	_show_panel("Spell book", body, choices)


func _close_book() -> void:
	hud.hide_text_panel()
	panel_ids.clear()
	mode = Mode.PLAY
	overworld.active = true


func _spend_from_ui(element: String) -> void:
	var msgs: Array = party.spend_point(element)
	for msg in msgs:
		hud.toast(str(msg))
	if mode == Mode.LEVELUP:
		if party.pending_points > 0:
			_refresh_levelup()
		else:
			hud.hide_text_panel()
			panel_ids.clear()
			var then := after_points
			after_points = Callable()
			if then.is_valid():
				then.call()
	elif mode == Mode.BOOK:
		_refresh_book()


func _element_status() -> String:
	var lines: PackedStringArray = []
	for id in ["earth", "water", "fire", "wind"]:
		var e: Dictionary = party.elements[id]
		var need := Rules.xp_to_advance(int(e.level))
		var bits: PackedStringArray = []
		for row in Rules.spell_rows(party.elements):
			if str(row.element) != id:
				continue
			if row.known:
				bits.append("%s (%d spirit) — %s" % [row.name, int(row.mp), row.blurb])
			else:
				bits.append("%s unlocks at level %d." % [row.name, int(row.need)])
		lines.append("%s  level %d   (%d/%d)\n  %s" % [id.capitalize(), int(e.level), int(e.xp), need, "\n  ".join(bits)])
	return "\n".join(lines)


func _say(lines: Array, then: Callable) -> void:
	dialogue = lines
	dialogue_i = 0
	dialogue_then = then
	mode = Mode.TALK
	overworld.active = false
	_show_line()


func _show_line() -> void:
	if dialogue_i < dialogue.size():
		hud.show_dialogue(str(dialogue[dialogue_i]))


func _advance_talk() -> void:
	dialogue_i += 1
	if dialogue_i >= dialogue.size():
		hud.hide_dialogue()
		var then := dialogue_then
		dialogue_then = Callable()
		if then.is_valid():
			then.call()
		else:
			mode = Mode.PLAY
			overworld.active = true
	else:
		_show_line()


func _show_panel(title: String, body: String, choices: Array) -> void:
	panel_ids.clear()
	for entry in choices:
		panel_ids.append(str(entry.id))
	hud.show_text_panel(title, body, choices)


func _panel_number(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed:
		return
	var keycode: int = event.keycode if event.keycode != 0 else int(event.physical_keycode)
	var index := int(keycode) - KEY_1
	if index >= 0 and index < panel_ids.size():
		_on_choice(str(panel_ids[index]))


func nudge_camera_pitch(amount: float) -> void:
	cam_pitch = clampf(cam_pitch + amount, PITCH_MIN, PITCH_MAX)


func _apply_battle_cam() -> void:
	cam_dist = 15.5
	cam_height = 11.5
	viewing_battle = true
	cam_snap = true


func _apply_play_cam() -> void:
	cam_dist = 12.5
	cam_height = 8.2
	viewing_battle = false
	cam_snap = true


func _fade(target: float) -> void:
	if hud == null:
		return
	hud.fade_to(target)
	if instant_transitions:
		hud.fade.color.a = target
		await get_tree().process_frame
		return
	await get_tree().create_timer(0.45).timeout


func _update_camera(delta: float) -> void:
	var target := Vector3(0, 1.2, 10)
	var dist := cam_dist
	if viewing_battle:
		target = Vector3(0, 1.0, 0)
	elif overworld and overworld.coop_active() and overworld.panda_body:
		var a: Vector3 = overworld.hero.global_position
		var b: Vector3 = overworld.panda_body.global_position
		target = (a + b) * 0.5 + Vector3(0, 1.2, 0)
		var sep := Vector2(a.x - b.x, a.z - b.z).length()
		dist = clampf(12.5 + sep * 0.5, 12.5, 28.0)
	elif overworld and overworld.hero:
		target = overworld.hero.global_position + Vector3(0, 1.2, 0)
	var elev := clampf(cam_pitch, PITCH_MIN, PITCH_MAX)
	var horiz := cos(elev) * dist
	var vert := sin(elev) * dist
	if viewing_battle:
		vert = maxf(vert, 4.0)
	var desired := target + Vector3(sin(cam_yaw) * horiz, vert, cos(cam_yaw) * horiz)
	if cam_snap:
		camera.global_position = desired
		cam_snap = false
	else:
		camera.global_position = camera.global_position.lerp(desired, 1.0 - exp(-4.0 * delta))
	if camera.global_position.distance_squared_to(target) > 0.01:
		camera.look_at(target, Vector3.UP)


func _start_music() -> void:
	if DisplayServer.get_name() == "headless":
		return
	if music or not ResourceLoader.exists("res://assets/audio/meadow_motif.wav"):
		return
	music = AudioStreamPlayer.new()
	music.stream = load("res://assets/audio/meadow_motif.wav")
	music.volume_db = -18.0
	music.finished.connect(func():
		if music:
			music.play()
	)
	add_child(music)
	music.play()
