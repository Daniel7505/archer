extends SceneTree

const Rules = preload("res://scripts/rules.gd")
const PartyState = preload("res://scripts/party_state.gd")
const BattleScript = preload("res://scripts/battle.gd")

var failed := false


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	if not _rules():
		failed = true
	if not await _logic_battle():
		failed = true
	if not await _scene():
		failed = true
	print("SMOKE %s" % ("PASS" if not failed else "FAIL"))
	quit(1 if failed else 0)


func check(cond: bool, msg: String) -> bool:
	if cond:
		print("  ok  ", msg)
		return true
	failed = true
	push_error("FAIL " + msg)
	print("  FAIL ", msg)
	return false


func _rules() -> bool:
	print("rules")
	var ok := true
	var grown: Dictionary = Rules.add_element_xp(1, 0, 12)
	ok = check(int(grown.level) == 1 and int(grown.xp) == 12, "one ember stays level 1") and ok
	grown = Rules.add_element_xp(1, 12, 12)
	ok = check(int(grown.level) == 2 and int(grown.xp) == 4, "second ember reaches fire 2") and ok
	ok = check(Rules.hurt(10, true, 1.0) == 5, "defend halves") and ok
	ok = check(Rules.hurt(10, false, 0.6) == 6, "bulwark reduces") and ok
	ok = check(Rules.in_circle(Vector3(0.4, 0, 0.2), Vector3.ZERO, 1.0), "circle catches a nearby body") and ok
	ok = check(not Rules.in_circle(Vector3(3, 0, 0), Vector3.ZERO, 1.0), "circle misses a far body") and ok
	var clamped: Vector3 = Rules.clamp_move(Vector3.ZERO, 2.0, Vector3.ZERO, 8.0, Vector3(0, 0, -9))
	ok = check(Rules.flat(clamped, Vector3.ZERO) <= 2.05, "move clamp stays in the step circle") and ok
	var party = PartyState.new()
	var snap: Dictionary = party.snapshot()
	party.note_cast("fire", 12)
	party.archer_hp = 10
	party.panda_hp = 12
	party.restore(snap)
	ok = check(party.archer_hp == 64 and party.panda_hp == 64 and int(party.elements.fire.xp) == 0, "defeat rollback undoes spirit growth") and ok
	party.note_cast("fire", 12)
	party.note_cast("fire", 12)
	ok = check(int(party.elements.fire.level) == 2, "use-to-level reaches 2") and ok
	party.pending_points = 1
	var msgs: Array = party.spend_point("fire")
	ok = check(int(party.elements.fire.level) == 3, "a level point reaches 3") and ok
	ok = check(Rules.is_known(party.elements, "hearthburst"), "hearthburst unlocks at fire 3") and ok
	var joined := " ".join(msgs)
	ok = check("Hearthburst" in joined, "point announces Hearthburst") and ok
	var levels := party.grant_victory_xp(32)
	ok = check(levels == 1 and party.pending_points == 2, "meadow xp levels the pair and gives two points") and ok
	return ok


func _logic_battle() -> bool:
	print("battle")
	var ok := true
	var party = PartyState.new()
	var battle = BattleScript.new()
	root.add_child(battle)
	await process_frame
	battle.begin("meadow", party, true)
	ok = check(battle.fighter("archer") != null and battle.fighter("mite_a") != null, "meadow spawns the pair and mites") and ok
	var names: PackedStringArray = battle.fighter("archer").visual.anim_names()
	print("  archer anims: ", ", ".join(names))
	ok = check(names.has("idle") and names.has("walk") and names.has("attack_arrow"), "archer clips imported") and ok
	battle.debug_run_enemy("mite_b")
	for _i in 12:
		await process_frame
		if battle.state == "gauge" or battle.over:
			break
	ok = check(battle.state == "gauge" or battle.over, "enemy turn returns to the gauges") and ok
	var saw := false
	for _cast in 4:
		if battle.over:
			break
		battle.force_turn("archer")
		var mite = battle.fighter("mite_a")
		var result: Dictionary = battle.debug_cast("ember_shot", mite.pos)
		for msg in result.get("messages", []):
			if "Hearthburst" in str(msg):
				saw = true
	ok = check(int(party.elements.fire.level) == 3, "four Ember Shots grow fire to 3") and ok
	ok = check(saw, "the stronger fire spell is announced") and ok
	ok = check(Rules.is_known(party.elements, "hearthburst"), "hearthburst is castable after use") and ok
	ok = check(party.mp == 0, "spirit was spent on the casts") and ok
	battle.fighter("archer").pos = Vector3.ZERO
	battle.fighter("panda").pos = Vector3(0.3, 0, 0.2)
	battle.fighter("archer").defending = false
	battle.fighter("panda").defending = false
	battle.fighter("archer").guard_mult = 1.0
	battle.fighter("panda").guard_mult = 1.0
	party.archer_hp = 50
	party.panda_hp = 50
	battle.debug_apply_attack(Vector3.ZERO, 10, 2.0)
	ok = check(party.archer_hp == 40 and party.panda_hp == 40, "a circle that catches both bodies hurts each life") and ok
	party.archer_hp = 40
	party.panda_hp = 40
	battle.fighter("archer").defending = true
	battle.fighter("panda").pos = Vector3(6, 0, 6)
	battle.debug_apply_attack(Vector3.ZERO, 10, 0.6)
	ok = check(party.archer_hp == 35 and party.panda_hp == 40, "defend halves only the body that braced") and ok
	party.archer_hp = 20
	party.panda_hp = 20
	party.mp = 20
	battle.force_turn("panda")
	var spot: Vector3 = battle.fighter("panda").pos
	battle.fighter("archer").pos = spot
	battle.debug_cast("dew_mend", spot)
	ok = check(party.archer_hp == 46 and party.panda_hp == 46, "Dewmend heals each body inside, more when both stand there") and ok
	ok = check(int(party.elements.water.xp) == 12, "water grows by being cast") and ok
	battle.force_turn("panda")
	var foe = battle.fighter("mite_b")
	var aim: Vector3 = foe.pos if foe != null else Vector3(0, 0, -3)
	battle.debug_cast("skyfang", aim)
	ok = check(int(party.elements.wind.xp) > 0 or int(party.elements.wind.level) > 1, "a scripted panda action can cast") and ok
	battle.queue_free()
	return ok


func _scene() -> bool:
	print("scene")
	var ok := true
	var packed = load("res://scenes/main.tscn")
	ok = check(packed != null, "main scene loads") and ok
	if packed == null:
		return false
	var game = packed.instantiate()
	root.add_child(game)
	await process_frame
	await process_frame
	ok = check(game.get_node_or_null("Overworld") != null, "overworld exists") and ok
	ok = check(game.get_node_or_null("Battle") != null, "battle exists") and ok
	ok = check(game.get_node_or_null("HUD") != null, "hud exists") and ok
	ok = check(InputMap.has_action("p2_confirm") and InputMap.has_action("p2_attack") and InputMap.has_action("p2_spell") and InputMap.has_action("p2_item") and InputMap.has_action("p2_defend"), "player 2 pad actions exist") and ok
	ok = check(not game.overworld.coop_active(), "without a pad the party stays single-player") and ok
	game.debug_skip_title()
	var zone1_ew: float = game.overworld.zone1_cross_seconds()
	var zone1_ns: float = game.overworld.zone1_north_south_seconds()
	var zone2_long: float = game.overworld.zone2_cross_seconds()
	var zone2_wide: float = game.overworld.zone2_breadth_seconds()
	print("  zone1 east-west %.1f s, north-south %.1f s, zone2 road %.1f s, zone2 breadth %.1f s" % [zone1_ew, zone1_ns, zone2_long, zone2_wide])
	ok = check(zone1_ew >= 90.0 and zone1_ew <= 120.0, "first zone east-west crossing is Northshire-scale") and ok
	ok = check(zone1_ns >= 90.0 and zone1_ns <= 120.0, "first zone north-south crossing is Northshire-scale") and ok
	ok = check(zone2_long > zone1_ew * 2.5 and zone2_long >= 180.0, "second zone road is several times longer") and ok
	ok = check(zone2_wide >= 150.0, "second zone has a long cross-country breadth") and ok
	var camp_here: Vector3 = game.overworld._w(0.0, 30.0)
	var far_here: Vector3 = game.overworld.zone2_sample_point()
	ok = check(game.overworld.is_chunk_awake_at_world(camp_here), "the camp chunk starts awake") and ok
	ok = check(not game.overworld.is_chunk_awake_at_world(far_here), "the far fields start asleep") and ok
	ok = check(game.overworld.awake_chunk_count() * 4 < game.overworld.chunk_count(), "most chunks are not simulated") and ok
	ok = check(game.overworld.region_name() == "Bramblewick Camp", "camp is named") and ok
	ok = check(game.overworld.count_foes("camp") == 0, "camp has no wandering foes") and ok
	ok = check(game.overworld.count_foes("meadow") >= 4, "the meadow has visible wanderers") and ok
	ok = check(game.overworld.foe_visible("lurker") and game.overworld.foe_visible("mosswick"), "the lurker and Mosswick stand on the map") and ok
	game.overworld.place(Vector3(0, 0, -30))
	ok = check(game.overworld.region_name() == "Golden Meadow", "meadow is named") and ok
	game.overworld.place(Vector3(-46, 0, -18))
	ok = check(game.overworld.region_name() == "Lamb Hill", "the hill overlook is off the main road") and ok
	game.overworld.place(Vector3(88, 0, -40))
	ok = check(game.overworld.region_name() == "Lantern Grove", "grove is named") and ok
	game.overworld.place(Vector3(90, 0, -110))
	ok = check(game.overworld.region_name() == "The Sealed Stair", "stair is named") and ok
	game.debug_touch("mite_1")
	for _step in 8:
		await process_frame
	ok = check(game.battle.visible and not game.overworld.visible, "touching a map foe fades into a battle field") and ok
	ok = check(game.battle.fighter("mite_a") != null, "the clearing uses the meadow fight") and ok
	game.debug_finish_battle()
	for _step in 8:
		await process_frame
	ok = check(game.overworld.visible and not game.battle.visible, "winning returns to the overworld") and ok
	ok = check(not game.overworld.foe_visible("mite_1"), "the beaten foe is gone") and ok
	game.overworld.place(Vector3(0, 0, 30))
	game.overworld.place(Vector3(0, 0, -30))
	ok = check(game.overworld.foe_visible("mite_1"), "leaving the meadow and coming back brings the foe back") and ok
	game.debug_battle("meadow")
	await process_frame
	ok = check(game.battle.fighter("panda") != null, "story battle has the panda") and ok
	var hp_before: int = game.battle.fighter("mite_a").hp
	game.battle.debug_cast("ember_shot", game.battle.fighter("mite_a").pos)
	ok = check(game.battle.fighter("mite_a").hp < hp_before, "ember shot deals damage in the running scene") and ok
	ok = check(int(game.party.elements.fire.xp) > 0 or int(game.party.elements.fire.level) > 1, "the scene party grew fire") and ok
	return ok
