extends Node3D

const ActorVisual = preload("res://scripts/actor_visual.gd")
const Props = preload("res://scripts/props.gd")
const Circle = preload("res://scripts/circle.gd")

signal encounter_hit(id: String)
signal lina_talk
signal gate_msg(which: String)
signal sign_read(text: String)

var party = null
var active := false
var yaw := 0.0
var hero: CharacterBody3D
var hero_visual: Node3D
var panda: Node3D
var panda_prev := Vector3.ZERO
var lina_pos := Vector3(4.2, 0, 11.6)
var gate_grove: StaticBody3D
var gate_ruin: StaticBody3D
var triggers := {}
var markers := {}
var signs: Array = []
var jars: Array = []

const WALLS := [
	[-8, 16, 8, 16],
	[8, 16, 8, 6],
	[8, 6, 14, 6],
	[14, 6, 14, -12],
	[14, -18, 14, -22],
	[14, -22, -14, -22],
	[-14, -22, -14, 0],
	[-14, 0, -8, 0],
	[-8, 0, -8, 16],
	[-8, 6, -3, 6],
	[3, 6, 8, 6],
	[-3, 0, -3, 6],
	[3, 0, 3, 6],
	[14, -12, 18, -12],
	[14, -18, 18, -18],
	[14, -8, 18, -8],
	[14, -22, 18, -22],
	[18, -8, 36, -8],
	[36, -8, 36, -30],
	[36, -30, 28, -30],
	[22, -30, 18, -30],
	[18, -30, 18, -18],
	[18, -12, 18, -8],
	[22, -30, 22, -38],
	[28, -30, 28, -38],
	[18, -30, 18, -54],
	[18, -54, 36, -54],
	[36, -54, 36, -30],
	[18, -38, 22, -38],
	[28, -38, 36, -38],
]


func build() -> void:
	_ground()
	for segment in WALLS:
		var color := Color("6f8f4e")
		if segment[1] < -32 or segment[3] < -32 or (segment[0] > 17 and segment[1] < -29):
			color = Color("9a948c")
		elif segment[0] > 16 or segment[2] > 16:
			color = Color("2f5a38")
		_wall(segment[0], segment[1], segment[2], segment[3], color)
	_dress_camp()
	_dress_meadow()
	_dress_grove()
	_dress_ruin()
	_make_hero()
	_make_encounter("meadow", Vector3(0, 0, -11), "the grass is cracking", Color(0.95, 0.55, 0.25, 0.38))
	_make_encounter("grove", Vector3(27, 0, -19), "a dim jar-light", Color(0.45, 0.75, 0.55, 0.38))
	_make_encounter("stair", Vector3(27, 0, -46), "Mosswick waits", Color(0.85, 0.45, 0.35, 0.4))
	gate_grove = _gate(Vector3(16.0, 0.7, -15.0), Vector3(3.4, 1.4, 6.3))
	gate_ruin = _gate(Vector3(25.0, 0.7, -34.0), Vector3(7.0, 1.4, 3.2))
	refresh_gates()
	_sign(Vector3(0, 0, 7.4), "Camp", "Bramblewick Camp. Lina keeps the tea. Press F beside her.")
	_sign(Vector3(0, 0, -1.2), "Meadow", "Golden Meadow. Something in the grass is cracking.")
	_sign(Vector3(20, 0, -14), "Grove", "Lantern Grove. The jars in the branches are still shut.")
	_sign(Vector3(25, 0, -40), "Stair", "The Sealed Stair. Mosswick thinks lights belong in jars.")


func _physics_process(delta: float) -> void:
	if hero == null:
		return
	if not active:
		hero.velocity = Vector3.ZERO
		return
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var look := Vector3(-sin(yaw), 0.0, -cos(yaw))
	var right := Vector3(cos(yaw), 0.0, -sin(yaw))
	var dir := right * input.x + look * -input.y
	if dir.length() > 0.08:
		dir = dir.normalized()
		hero.velocity = dir * 5.2
		if hero_visual:
			hero_visual.face_dir(dir)
			hero_visual.set_moving(true)
	else:
		hero.velocity = Vector3.ZERO
		if hero_visual:
			hero_visual.set_moving(false)
	hero.move_and_slide()
	hero.global_position.y = 0.9
	_follow_panda(delta)


func region_name() -> String:
	if hero == null:
		return ""
	var p := hero.global_position
	if p.z > 5.5 and p.x < 12.0:
		return "Bramblewick Camp"
	if p.z < -36.0:
		return "The Sealed Stair"
	if p.x > 17.0:
		return "Lantern Grove"
	if p.z < 1.0:
		return "Golden Meadow"
	return "The path between"


func place(pos: Vector3) -> void:
	if hero == null:
		return
	hero.global_position = Vector3(pos.x, 0.9, pos.z)
	hero.velocity = Vector3.ZERO
	if panda:
		panda.global_position = hero.global_position + Vector3(1.2, 0, 1.3)
		panda_prev = panda.global_position


func nudge_out(id: String) -> void:
	if not triggers.has(id) or hero == null:
		return
	var area: Node3D = triggers[id]
	var away := hero.global_position - area.global_position
	away.y = 0.0
	if away.length() < 0.2:
		away = Vector3(0, 0, 1)
	hero.global_position += away.normalized() * 3.2
	hero.global_position.y = 0.9


func set_trigger_enabled(id: String, enabled: bool) -> void:
	if triggers.has(id) and is_instance_valid(triggers[id]):
		triggers[id].monitoring = enabled


func refresh_gates() -> void:
	var meadow_clear := party != null and bool(party.cleared.get("meadow", false))
	var grove_clear := party != null and bool(party.cleared.get("grove", false))
	_set_open(gate_grove, meadow_clear)
	_set_open(gate_ruin, grove_clear)


func on_battle_won(id: String) -> void:
	if triggers.has(id) and is_instance_valid(triggers[id]):
		triggers[id].queue_free()
		triggers.erase(id)
	for key in [id, id + "_label"]:
		if markers.has(key) and is_instance_valid(markers[key]):
			markers[key].queue_free()
			markers.erase(key)
	refresh_gates()


func interact() -> void:
	if hero == null:
		return
	var p := hero.global_position
	if Vector2(p.x - lina_pos.x, p.z - lina_pos.z).length() < 2.5:
		lina_talk.emit()
		return
	if gate_grove and gate_grove.visible and _near(gate_grove, p):
		gate_msg.emit("grove")
		return
	if gate_ruin and gate_ruin.visible and _near(gate_ruin, p):
		gate_msg.emit("ruin")
		return
	for sign in signs:
		var s: Vector3 = sign.pos
		if Vector2(p.x - s.x, p.z - s.z).length() < 2.3:
			sign_read.emit(sign.text)
			return


func celebrate() -> void:
	for jar in jars:
		if not is_instance_valid(jar):
			continue
		var cork: Node = jar.get_node_or_null("Cork")
		if cork:
			cork.visible = false
		var wick: Node = jar.get_node_or_null("Wick")
		if wick:
			wick.visible = true
		var glow: Node = jar.get_node_or_null("Glow")
		if glow:
			glow.visible = true


func play_thanks() -> void:
	if hero_visual:
		hero_visual.play_once("respect_bow")
	if panda and panda.has_method("bow"):
		panda.bow()


func _follow_panda(delta: float) -> void:
	if panda == null or hero == null:
		return
	var side := hero.global_transform.basis.x
	var back := hero.global_transform.basis.z
	var target: Vector3 = hero.global_position + side * 1.15 + back * 1.25
	target.y = 0.0
	panda.global_position = panda.global_position.lerp(target, 1.0 - exp(-5.0 * delta))
	var step := panda.global_position - panda_prev
	if step.length() > 0.03 and panda.has_method("face_dir"):
		panda.face_dir(Vector3(step.x, 0, step.z))
		panda.set_moving(true)
	elif panda.has_method("set_moving"):
		panda.set_moving(false)
	panda_prev = panda.global_position


func _make_hero() -> void:
	hero = CharacterBody3D.new()
	hero.name = "Hero"
	hero.position = Vector3(0, 0.9, 12)
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.38
	capsule.height = 1.5
	shape.shape = capsule
	hero.add_child(shape)
	hero_visual = ActorVisual.new()
	hero.add_child(hero_visual)
	hero_visual.position = Vector3(0, -0.9, 0)
	hero_visual.configure("archer", "Archer")
	add_child(hero)
	panda = ActorVisual.new()
	panda.position = Vector3(1.3, 0, 13.3)
	add_child(panda)
	panda.configure("panda", "Panda")
	panda_prev = panda.global_position


func _make_encounter(id: String, pos: Vector3, caption: String, color: Color) -> void:
	var area := Area3D.new()
	area.position = pos
	area.collision_layer = 0
	area.collision_mask = 1
	area.monitorable = false
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 2.25
	cyl.height = 2.0
	shape.shape = cyl
	shape.position = Vector3(0, 1.0, 0)
	area.add_child(shape)
	area.body_entered.connect(_on_body.bind(id))
	add_child(area)
	triggers[id] = area
	var ring := Circle.new()
	add_child(ring)
	ring.setup(color)
	ring.show_at(pos, 2.15)
	markers[id] = ring
	var label := Label3D.new()
	label.text = caption
	label.font_size = 28
	label.pixel_size = 0.007
	label.position = pos + Vector3(0, 1.6, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 6
	label.modulate = Color("fff1d6")
	add_child(label)
	markers[id + "_label"] = label


func _on_body(body: Node, id: String) -> void:
	if not active or body != hero:
		return
	if party != null and bool(party.cleared.get(id, false)):
		return
	active = false
	encounter_hit.emit(id)


func _ground() -> void:
	var big := Props.box(Vector3(140, 0.2, 140), Color("5d7a40"), Vector3(10, -0.16, -16))
	big.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(big)
	_patch(-8, 6, 8, 16, Color("a8845a"), 0.02)
	_patch(-3, 0, 3, 6, Color("c2a36b"), 0.03)
	_patch(-14, -22, 14, 0, Color("7ea354"), 0.02)
	_patch(14, -18, 18, -12, Color("c2a36b"), 0.03)
	_patch(18, -30, 36, -8, Color("3e6844"), 0.02)
	_patch(22, -38, 28, -30, Color("b7aa90"), 0.03)
	_patch(18, -54, 36, -38, Color("8f897f"), 0.02)


func _patch(x0: float, z0: float, x1: float, z1: float, color: Color, y: float) -> void:
	var size := Vector3(absf(x1 - x0), 0.05, absf(z1 - z0))
	var pos := Vector3((x0 + x1) * 0.5, y, (z0 + z1) * 0.5)
	var mesh := Props.box(size, color, pos)
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mesh)


func _wall(x1: float, z1: float, x2: float, z2: float, color: Color) -> void:
	var mid := Vector3((x1 + x2) * 0.5, 0.62, (z1 + z2) * 0.5)
	var sx := absf(x2 - x1)
	var sz := absf(z2 - z1)
	var size := Vector3(sx + 0.6, 1.24, 0.6) if sx >= sz else Vector3(0.6, 1.24, sz + 0.6)
	var mesh := Props.box(size, color, mid)
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mesh)
	_static_box(mid, size)


func _gate(pos: Vector3, size: Vector3) -> StaticBody3D:
	var body := _static_box(pos, size)
	body.add_child(Props.box(size, Color("3c5a32"), Vector3.ZERO))
	return body


func _set_open(gate: StaticBody3D, open: bool) -> void:
	if gate == null:
		return
	gate.visible = not open
	var shape := gate.get_node_or_null("CollisionShape3D")
	if shape:
		shape.set("disabled", open)


func _static_box(pos: Vector3, size: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	add_child(body)
	return body


func _dress_camp() -> void:
	var lina := ActorVisual.new()
	lina.position = lina_pos
	add_child(lina)
	lina.configure("lina", "Lina")
	add_child(Props.cylinder(0.16, 0.45, Color("4a3424"), Vector3(-2.2, 0.22, 13.2)))
	add_child(Props.sphere(0.18, Color("ff8a3c"), Vector3(-2.2, 0.5, 13.2), 2.2))
	var fire := OmniLight3D.new()
	fire.position = Vector3(-2.2, 0.8, 13.2)
	fire.light_color = Color("ffb060")
	fire.light_energy = 1.25
	fire.omni_range = 6.5
	add_child(fire)
	add_child(Props.box(Vector3(2.4, 1.25, 1.7), Color("8c3d3d"), Vector3(5.5, 0.68, 14.3)))
	_jar(Vector3(-5.2, 0, 10.5))


func _dress_meadow() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 560
	for i in 14:
		var pos := Vector3(rng.randf_range(-12, 12), 0, rng.randf_range(-20, -2))
		if absf(pos.x) < 2.2:
			continue
		var color := Color("f2d36b") if i % 2 == 0 else Color("dce7f2")
		add_child(Props.sphere(0.12, color, pos + Vector3(0, 0.12, 0)))
	_tree(Vector3(-11, 0, -6), false)
	_tree(Vector3(-10.5, 0, -18), false)
	_tree(Vector3(11, 0, -5), false)
	_tree(Vector3(10, 0, -18.5), false)


func _dress_grove() -> void:
	for pos in [Vector3(22, 0, -12), Vector3(32, 0, -13), Vector3(33, 0, -24), Vector3(21, 0, -26), Vector3(30.5, 0, -22)]:
		_tree(pos, true)
	_jar(Vector3(24, 0, -14))
	_jar(Vector3(31, 0, -17))
	_jar(Vector3(23.5, 0, -24))


func _dress_ruin() -> void:
	for pos in [Vector3(20, 0, -42), Vector3(33, 0, -43), Vector3(21, 0, -51), Vector3(33, 0, -51)]:
		add_child(Props.cylinder(0.4, 2.2, Color("b7b1a6"), pos + Vector3(0, 1.1, 0)))
	_jar(Vector3(24, 0, -44))
	_jar(Vector3(29, 0, -47))
	_jar(Vector3(26, 0, -51))
	add_child(Props.box(Vector3(4.2, 0.35, 1.4), Color("a39d94"), Vector3(27, 0.2, -49)))


func _tree(pos: Vector3, dark: bool) -> void:
	add_child(Props.cylinder(0.22, 1.35, Color("5a3b28"), pos + Vector3(0, 0.68, 0)))
	var leaf := Color("2c6240") if dark else Color("3f8f4a")
	add_child(Props.sphere(0.85, leaf, pos + Vector3(0, 1.75, 0)))
	var body := StaticBody3D.new()
	body.position = pos + Vector3(0, 0.7, 0)
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.4
	cyl.height = 1.4
	shape.shape = cyl
	body.add_child(shape)
	add_child(body)


func _jar(pos: Vector3) -> void:
	var node := Node3D.new()
	node.position = pos
	add_child(node)
	node.add_child(Props.cylinder(0.28, 0.55, Color("c4a574"), Vector3(0, 0.32, 0)))
	var cork := Props.sphere(0.16, Color("6b4423"), Vector3(0, 0.66, 0))
	cork.name = "Cork"
	node.add_child(cork)
	var wick := Props.sphere(0.12, Color("f6e3a1"), Vector3(0, 0.95, 0), 2.4)
	wick.name = "Wick"
	wick.visible = false
	node.add_child(wick)
	var glow := OmniLight3D.new()
	glow.name = "Glow"
	glow.position = Vector3(0, 1.05, 0)
	glow.light_color = Color("ffd48a")
	glow.light_energy = 0.85
	glow.omni_range = 3.6
	glow.visible = false
	node.add_child(glow)
	jars.append(node)
	var body := StaticBody3D.new()
	body.position = pos + Vector3(0, 0.3, 0)
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.32
	cyl.height = 0.6
	shape.shape = cyl
	body.add_child(shape)
	add_child(body)


func _sign(pos: Vector3, short: String, full: String) -> void:
	add_child(Props.cylinder(0.08, 1.1, Color("6b4a2e"), pos + Vector3(0, 0.55, 0)))
	var label := Label3D.new()
	label.text = short
	label.font_size = 28
	label.pixel_size = 0.008
	label.position = pos + Vector3(0, 1.35, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 6
	label.modulate = Color("f3e2c2")
	add_child(label)
	signs.append({"pos": pos, "text": full})


func _near(body: Node3D, p: Vector3) -> bool:
	return Vector2(p.x - body.global_position.x, p.z - body.global_position.z).length() < 2.8
