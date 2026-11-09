extends Node3D

const ActorVisual = preload("res://scripts/actor_visual.gd")
const Props = preload("res://scripts/props.gd")
const Circle = preload("res://scripts/circle.gd")
const Pads = preload("res://scripts/pads.gd")

signal encounter_hit(battle_id: String, foe_id: String)
signal lina_talk
signal sign_read(text: String)
signal pickup_found(kind: String, note: String)
signal npc_talk(who: String)

var party = null
var active := false
var yaw := 0.0
var hero: CharacterBody3D
var hero_visual: Node3D
var panda_body: CharacterBody3D
var panda: Node3D
var panda_prev := Vector3.ZERO
var quill_pos := Vector3(102.0, 0.0, -40.0)
var ilvane_pos := Vector3(150.0, 0.0, -38.0)
var lina_pos := Vector3(8.0, 0.0, 28.0)
var signs: Array = []
var jars: Array = []
var foes := {}
var pickups := {}
var region_now := "camp"
var left_regions := {}

const TILE := 8.0

# Map foes. Camp is intentionally absent.
const FOE_TABLE := [
	{"id": "mite_1", "region": "meadow", "battle": "mite", "kind": "mite", "name": "Cinder Mite", "scale": 1.0, "special": false,
		"at": [16, -26], "patrol": [[16, -26], [28, -26], [28, -38], [16, -38]]},
	{"id": "mite_2", "region": "meadow", "battle": "mite", "kind": "mite", "name": "Cinder Mite", "scale": 1.0, "special": false,
		"at": [-22, -30], "patrol": [[-22, -30], [-34, -30], [-34, -44], [-22, -44]]},
	{"id": "mite_3", "region": "meadow", "battle": "mite", "kind": "mite", "name": "Cinder Mite", "scale": 1.0, "special": false,
		"at": [8, -54], "patrol": [[8, -54], [8, -66], [-6, -66], [-6, -54]]},
	{"id": "mite_4", "region": "meadow", "battle": "mite", "kind": "mite", "name": "Cinder Mite", "scale": 1.0, "special": false,
		"at": [34, -58], "patrol": [[34, -58], [46, -58], [46, -70], [34, -70]]},
	{"id": "mite_5", "region": "meadow", "battle": "mite", "kind": "mite", "name": "Cinder Mite", "scale": 1.0, "special": false,
		"at": [-30, -62], "patrol": [[-30, -62], [-18, -62], [-18, -74], [-30, -74]]},
	{"id": "sprig_1", "region": "grove", "battle": "sprig", "kind": "lurker", "name": "Thicket Sprig", "scale": 0.82, "special": false,
		"at": [78, -28], "patrol": [[78, -28], [92, -28], [92, -40], [78, -40]]},
	{"id": "sprig_2", "region": "grove", "battle": "sprig", "kind": "lurker", "name": "Thicket Sprig", "scale": 0.82, "special": false,
		"at": [104, -48], "patrol": [[104, -48], [112, -48], [112, -60], [104, -60]]},
	{"id": "sprig_3", "region": "grove", "battle": "sprig", "kind": "lurker", "name": "Thicket Sprig", "scale": 0.82, "special": false,
		"at": [84, -68], "patrol": [[84, -68], [96, -68], [96, -58], [84, -58]]},
	{"id": "lurker", "region": "grove", "battle": "lurker", "kind": "lurker", "name": "Thicket Lurker", "scale": 1.35, "special": true,
		"at": [72, -56], "patrol": [[72, -56], [80, -52], [72, -48], [64, -52]]},
	{"id": "pebble_1", "region": "stair", "battle": "pebble", "kind": "mite", "name": "Kiln Pebble", "scale": 0.9, "special": false,
		"at": [100, -96], "patrol": [[100, -96], [112, -96], [112, -108], [100, -108]]},
	{"id": "pebble_2", "region": "stair", "battle": "pebble", "kind": "mite", "name": "Kiln Pebble", "scale": 0.9, "special": false,
		"at": [76, -112], "patrol": [[76, -112], [76, -124], [88, -124], [88, -112]]},
	{"id": "mosswick", "region": "stair", "battle": "stair", "kind": "boss", "name": "Mosswick", "scale": 1.55, "special": true,
		"at": [92, -128], "patrol": [[92, -128]]},
]


func build() -> void:
	_ground()
	_hedges()
	_dress_camp()
	_dress_meadow()
	_dress_grove()
	_dress_ruin()
	_dress_margins()
	_dress_aldermoor_road()
	_make_hero()
	for spec in FOE_TABLE:
		_spawn_foe(spec)
	_pickup("berry_hill", "berry", Vector3(-48, 0, -16), "")
	_pickup("note_hill", "note", Vector3(-44, 0, -22), "A flat stone on Lamb Hill: the wicklights used to race the wind up here. Lina says the hill never won.")
	_pickup("sip_creek", "sip", Vector3(36, 0, -2), "")
	_pickup("note_creek", "note", Vector3(26, 0, 2), "Pebble Creek is warm even in the morning. It is not on the way to anything. That is the nice part.")
	_pickup("berry_nook", "berry", Vector3(112, 0, -16), "")
	_pickup("note_nook", "note", Vector3(106, 0, -20), "Bark scratch in the Jar Nook: Mosswick counts jars the way other people count sheep. He is not cruel. He is unfinished.")
	_pickup("sip_landing", "sip", Vector3(70, 0, -114), "")
	_pickup("note_landing", "note", Vector3(74, 0, -108), "Broken Landing. The stair was longer once. The rest of it is still just stone.")
	_sign(Vector3(0, 0, 16), "Meadow", "Golden Meadow is north. The mites wander in the grass. They do not cross into camp. Walk around them, or let one take you to a clearing.")
	_sign(Vector3(0, 0, -40), "Fork", "The east road finds the Lantern Grove. West is only Lamb Hill, and the view.")
	_sign(Vector3(58, 0, -36), "Grove", "Lantern Grove. Smaller things wander. The tall lurker keeps to the north path, and you can walk around it.")
	_sign(Vector3(92, 0, -84), "Stair", "The Sealed Stair. Mosswick is the one sitting on the jar. The kiln pebbles are only pebbles.")
	_sign(Vector3(148, 0, -22), "Later", "The east trees are still empty. There is room to grow, later.")
	region_now = "camp"


func _physics_process(delta: float) -> void:
	if hero == null:
		return
	poll_region()
	if not active:
		hero.velocity = Vector3.ZERO
		_tick_foes(0.0)
		return
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var look := Vector3(-sin(yaw), 0.0, -cos(yaw))
	var right := Vector3(cos(yaw), 0.0, -sin(yaw))
	var dir := right * input.x + look * -input.y
	if dir.length() > 0.08:
		dir = dir.normalized()
		hero.velocity = dir * 6.8
		if hero_visual:
			hero_visual.face_dir(dir)
			hero_visual.set_moving(true)
	else:
		hero.velocity = Vector3.ZERO
		if hero_visual:
			hero_visual.set_moving(false)
	hero.move_and_slide()
	hero.global_position.y = 0.9
	if Pads.panda_uses_pad():
		_steer_panda(delta)
	else:
		_follow_panda(delta)
	_tick_foes(delta)


func region_id() -> String:
	if hero == null:
		return "camp"
	var p := hero.global_position
	if p.x > 100.0 and p.z < -30.0 and p.z > -52.0:
		return "road"
	if p.x > 58.0 and p.z < -78.0:
		return "stair"
	if p.x > 58.0:
		return "grove"
	if p.z > 12.0:
		return "camp"
	return "meadow"


func region_name() -> String:
	if hero == null:
		return ""
	var p := hero.global_position
	if region_id() == "road":
		if p.x > 146.0:
			return "Aldermoor Gate"
		return "The Aldermoor Road"
	if p.x < -40.0 and p.z < 6.0 and p.z > -40.0:
		return "Lamb Hill"
	if p.x > 18.0 and p.x < 50.0 and p.z > -12.0 and p.z < 10.0:
		return "Pebble Creek"
	if p.x > 100.0 and p.z > -30.0 and p.z < -6.0 and p.x < 124.0:
		return "Jar Nook"
	if p.x > 62.0 and p.x < 82.0 and p.z < -100.0 and p.z > -126.0:
		return "Broken Landing"
	match region_id():
		"camp":
			return "Bramblewick Camp"
		"grove":
			return "Lantern Grove"
		"stair":
			return "The Sealed Stair"
		_:
			return "Golden Meadow"


func place(pos: Vector3) -> void:
	if hero == null:
		return
	hero.global_position = Vector3(pos.x, 0.9, pos.z)
	hero.velocity = Vector3.ZERO
	if panda_body:
		panda_body.global_position = hero.global_position + Vector3(1.2, 0.0, 1.3)
		panda_body.global_position.y = 0.9
		panda_prev = panda_body.global_position
	poll_region()


func poll_region() -> void:
	var region := region_id()
	if region == region_now:
		return
	if region_now != "camp":
		left_regions[region_now] = true
	region_now = region
	if region != "camp" and bool(left_regions.get(region, false)):
		_respawn_region(region)
		left_regions[region] = false


func coop_active() -> bool:
	return Pads.panda_uses_pad()


func count_foes(region: String) -> int:
	var n := 0
	for id in foes.keys():
		if str(foes[id].region) == region:
			n += 1
	return n


func foe_visible(id: String) -> bool:
	if not foes.has(id):
		return false
	var node: Node3D = foes[id].node
	return node.visible and not bool(foes[id].defeated)


func nudge_from_foe(foe_id: String) -> void:
	if hero == null or not foes.has(foe_id):
		return
	var node: Node3D = foes[foe_id].node
	var away: Vector3 = hero.global_position - node.global_position
	away.y = 0.0
	if away.length() < 0.2:
		away = Vector3(0, 0, 1)
	hero.global_position += away.normalized() * 3.4
	hero.global_position.y = 0.9


func on_foe_beaten(foe_id: String) -> void:
	if not foes.has(foe_id):
		return
	var foe: Dictionary = foes[foe_id]
	foe.defeated = true
	if str(foe.battle) == "stair":
		foe.gone_for_good = true
	var node: Node3D = foe.node
	node.visible = false
	var area: Area3D = foe.area
	area.monitoring = false


func interact() -> void:
	if hero == null:
		return
	if _near_party(lina_pos, 2.8):
		lina_talk.emit()
		return
	if _near_party(quill_pos, 2.8):
		npc_talk.emit("quill")
		return
	if _near_party(ilvane_pos, 2.8):
		npc_talk.emit("ilvane")
		return
	for sign in signs:
		var s: Vector3 = sign.pos
		if _near_party(s, 2.6):
			sign_read.emit(sign.text)
			return


func _near_party(pos: Vector3, radius: float) -> bool:
	if hero and Vector2(hero.global_position.x - pos.x, hero.global_position.z - pos.z).length() < radius:
		return true
	if panda_body and Vector2(panda_body.global_position.x - pos.x, panda_body.global_position.z - pos.z).length() < radius:
		return true
	return false


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


func _respawn_region(region: String) -> void:
	for id in foes.keys():
		var foe: Dictionary = foes[id]
		if str(foe.region) != region:
			continue
		if bool(foe.get("gone_for_good", false)):
			continue
		foe.defeated = false
		foe.wait = 0.4
		foe.leg = 0
		var node: Node3D = foe.node
		var home: Vector3 = foe.home
		node.position = home
		node.visible = true
		var area: Area3D = foe.area
		area.monitoring = true


func _tick_foes(delta: float) -> void:
	if delta <= 0.0:
		return
	for id in foes.keys():
		var foe: Dictionary = foes[id]
		if bool(foe.defeated):
			continue
		var points: Array = foe.points
		var visual: Node3D = foe.visual
		if points.size() < 2:
			if visual.has_method("set_moving"):
				visual.set_moving(false)
			continue
		var wait := float(foe.wait)
		if wait > 0.0:
			foe.wait = wait - delta
			if visual.has_method("set_moving"):
				visual.set_moving(false)
			continue
		var node: Node3D = foe.node
		var leg := int(foe.leg)
		var target: Vector3 = points[leg]
		var to: Vector3 = target - node.position
		to.y = 0.0
		var step := 1.65 * delta
		if to.length() <= step:
			node.position = Vector3(target.x, 0.0, target.z)
			foe.leg = (leg + 1) % points.size()
			foe.wait = 0.85
			if visual.has_method("set_moving"):
				visual.set_moving(false)
		else:
			var dir: Vector3 = to.normalized()
			node.position += dir * step
			if visual.has_method("face_dir"):
				visual.face_dir(dir)
			if visual.has_method("set_moving"):
				visual.set_moving(true)


func _spawn_foe(spec: Dictionary) -> void:
	var root := Node3D.new()
	root.name = str(spec.id)
	var at: Array = spec.at
	root.position = Vector3(at[0], 0.0, at[1])
	var visual := ActorVisual.new()
	root.add_child(visual)
	visual.configure(str(spec.kind), str(spec.name))
	var scl := float(spec.scale)
	root.scale = Vector3(scl, scl, scl)
	var area := Area3D.new()
	area.collision_layer = 0
	area.collision_mask = 1
	area.monitorable = false
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 1.15
	cyl.height = 2.0
	shape.shape = cyl
	shape.position = Vector3(0, 1.0, 0)
	area.add_child(shape)
	root.add_child(area)
	var foe_id := str(spec.id)
	area.body_entered.connect(_on_foe_body.bind(foe_id))
	if bool(spec.special):
		var ring := Circle.new()
		root.add_child(ring)
		var tint := Color(0.85, 0.45, 0.25, 0.35) if str(spec.battle) == "lurker" else Color(0.75, 0.55, 0.85, 0.4)
		ring.setup(tint)
		ring.show_at(Vector3.ZERO, 2.1)
	add_child(root)
	var points: Array = []
	for pair in spec.patrol:
		points.append(Vector3(pair[0], 0.0, pair[1]))
	foes[foe_id] = {
		"id": foe_id,
		"region": str(spec.region),
		"battle": str(spec.battle),
		"node": root,
		"visual": visual,
		"area": area,
		"home": root.position,
		"points": points,
		"leg": 0,
		"wait": 0.3,
		"defeated": false,
		"gone_for_good": false,
	}


func _on_foe_body(body: Node, foe_id: String) -> void:
	if not active or (body != hero and body != panda_body):
		return
	if not foes.has(foe_id) or bool(foes[foe_id].defeated):
		return
	active = false
	encounter_hit.emit(str(foes[foe_id].battle), foe_id)


func _follow_panda(delta: float) -> void:
	if panda_body == null or hero == null:
		return
	var side := hero.global_transform.basis.x
	var back := hero.global_transform.basis.z
	var target: Vector3 = hero.global_position + side * 1.15 + back * 1.35
	target.y = 0.9
	panda_body.velocity = Vector3.ZERO
	panda_body.global_position = panda_body.global_position.lerp(target, 1.0 - exp(-5.0 * delta))
	panda_body.global_position.y = 0.9
	var step: Vector3 = panda_body.global_position - panda_prev
	if step.length() > 0.03:
		_face_flat(panda_body, Vector3(step.x, 0, step.z))
		if panda:
			panda.set_moving(true)
	elif panda:
		panda.set_moving(false)
	panda_prev = panda_body.global_position


func _steer_panda(delta: float) -> void:
	if panda_body == null:
		return
	var stick := Pads.left_stick()
	if stick.length() < 0.08:
		panda_body.velocity = Vector3.ZERO
		if panda:
			panda.set_moving(false)
		return
	var look := Vector3(-sin(yaw), 0.0, -cos(yaw))
	var right := Vector3(cos(yaw), 0.0, -sin(yaw))
	var dir := (right * stick.x + look * -stick.y).normalized()
	panda_body.velocity = dir * 6.8
	_face_flat(panda_body, dir)
	if panda:
		panda.set_moving(true)
	panda_body.move_and_slide()
	panda_body.global_position.y = 0.9
	panda_prev = panda_body.global_position


func _face_flat(body: Node3D, dir: Vector3) -> void:
	dir.y = 0.0
	if dir.length_squared() < 0.0004:
		return
	body.look_at(body.global_position + dir, Vector3.UP)


func _make_hero() -> void:
	hero = CharacterBody3D.new()
	hero.name = "Hero"
	hero.position = Vector3(0, 0.9, 30)
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
	panda_body = CharacterBody3D.new()
	panda_body.name = "PandaBody"
	panda_body.position = Vector3(1.4, 0.9, 31.4)
	var panda_shape := CollisionShape3D.new()
	var panda_capsule := CapsuleShape3D.new()
	panda_capsule.radius = 0.42
	panda_capsule.height = 1.2
	panda_shape.shape = panda_capsule
	panda_body.add_child(panda_shape)
	panda = ActorVisual.new()
	panda.position = Vector3(0, -0.9, 0)
	panda_body.add_child(panda)
	panda.configure("panda", "Panda")
	add_child(panda_body)
	panda_prev = panda_body.global_position


func _ground() -> void:
	var big := Props.box(Vector3(280, 0.3, 280), Color("4e6b3c"), Vector3(50, -0.2, -60))
	big.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(big)
	_tiles(-24, 12, 24, 46, [Color("c4a06a"), Color("b89260")], 0.02)
	_tiles(-60, -80, 58, 12, [Color("7ea354"), Color("8fb862")], 0.02)
	_tiles(18, -12, 52, 10, [Color("6aa8c4"), Color("7eb8d0")], 0.03)
	_tiles(58, -80, 128, -8, [Color("3e6844"), Color("345c3c")], 0.02)
	_tiles(128, -80, 160, -8, [Color("35563a"), Color("2e4c34")], 0.02)
	_tiles(58, -168, 128, -78, [Color("9a9488"), Color("8b857c")], 0.02)
	_tiles(58, -168, 160, -140, [Color("7d786f"), Color("726d66")], 0.02)
	_path(-6, -78, 6, 12, Color("d2b48c"))
	_path(-56, -22, 6, -14, Color("d2b48c"))
	_path(6, -44, 70, -32, Color("c9a978"))
	_path(78, -78, 90, -32, Color("6d5a3e"))
	_path(70, -140, 104, -78, Color("b7aa96"))


func _tiles(x0: float, z0: float, x1: float, z1: float, colors: Array, y: float) -> void:
	var x := x0
	var col := 0
	while x < x1:
		var z := z0
		var row := 0
		while z < z1:
			var color: Color = colors[(col + row) % colors.size()]
			var w := minf(TILE, x1 - x)
			var d := minf(TILE, z1 - z)
			_patch(x, z, x + w, z + d, color, y)
			z += TILE
			row += 1
		x += TILE
		col += 1


func _path(x0: float, z0: float, x1: float, z1: float, color: Color) -> void:
	_patch(x0, z0, x1, z1, color, 0.05)


func _hedges() -> void:
	var hedge := Color("6f8f4e")
	var dark := Color("2f5a38")
	var stone := Color("9a948c")
	# Outer ring. The east and far north are empty on purpose.
	_wall(-60, 46, 160, 46, hedge)
	_wall(-60, -168, -60, 46, hedge)
	_wall(160, -168, 160, 46, dark)
	_wall(-60, -168, 160, -168, stone)
	# Camp hedge, with a wide gate onto the meadow. Never locked.
	_wall(-60, 12, -8, 12, hedge)
	_wall(8, 12, 160, 12, hedge)


func _patch(x0: float, z0: float, x1: float, z1: float, color: Color, y: float) -> void:
	var size := Vector3(absf(x1 - x0), 0.06, absf(z1 - z0))
	var pos := Vector3((x0 + x1) * 0.5, y, (z0 + z1) * 0.5)
	var mesh := Props.box(size, color, pos)
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mesh)


func _wall(x1: float, z1: float, x2: float, z2: float, color: Color) -> void:
	var mid := Vector3((x1 + x2) * 0.5, 0.7, (z1 + z2) * 0.5)
	var sx := absf(x2 - x1)
	var sz := absf(z2 - z1)
	var size := Vector3(sx + 0.8, 1.35, 0.8) if sx >= sz else Vector3(0.8, 1.35, sz + 0.8)
	var mesh := Props.box(size, color, mid)
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mesh)
	_static_box(mid, size)


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
	add_child(Props.cylinder(0.18, 0.5, Color("4a3424"), Vector3(-6.0, 0.25, 32.0)))
	add_child(Props.sphere(0.22, Color("ff8a3c"), Vector3(-6.0, 0.55, 32.0), 2.2))
	var fire := OmniLight3D.new()
	fire.position = Vector3(-6.0, 0.9, 32.0)
	fire.light_color = Color("ffb060")
	fire.light_energy = 1.3
	fire.omni_range = 8.0
	add_child(fire)
	add_child(Props.box(Vector3(3.2, 1.45, 2.2), Color("8c3d3d"), Vector3(14.0, 0.75, 34.0)))
	_jar(Vector3(-14.0, 0, 26.0))
	# A quiet side yard. Still camp, still safe.
	add_child(Props.box(Vector3(2.4, 0.45, 0.5), Color("a07a48"), Vector3(18.0, 0.28, 22.0)))
	_pickup("berry_yard", "berry", Vector3(18.0, 0, 18.5), "")
	_sign(Vector3(16.0, 0, 20.0), "Yard", "Lina's drying yard. Nothing wanders here. The tea is the dangerous part, and only if you forget it.")


func _dress_meadow() -> void:
	for pos in [Vector3(-40, 0, -8), Vector3(-48, 0, -28), Vector3(48, 0, -18), Vector3(-36, 0, -70), Vector3(40, 0, -74), Vector3(12, 0, -8), Vector3(-14, 0, -46)]:
		_tree(pos, false)
	# Lamb Hill: a ring of stones and a step, west of the fork. Not on the way to the grove.
	for i in 8:
		var angle := TAU * float(i) / 8.0
		var stone := Props.cylinder(0.45, 0.7, Color("b7b1a4"), Vector3(-46 + cos(angle) * 4.2, 0.35, -18 + sin(angle) * 4.2))
		add_child(stone)
	add_child(Props.cylinder(1.6, 0.35, Color("cfc6b4"), Vector3(-46, 0.2, -18)))
	# Creek reeds. The water tiles are already blue.
	for pos in [Vector3(22, 0, -6), Vector3(30, 0, 4), Vector3(42, 0, -8), Vector3(24, 0, 6)]:
		add_child(Props.cylinder(0.08, 0.9, Color("2f6a48"), pos + Vector3(0, 0.45, 0)))
	add_child(Props.sphere(0.35, Color("d9d3c6"), Vector3(34, 0.2, 0)))


func _dress_grove() -> void:
	for pos in [Vector3(66, 0, -18), Vector3(96, 0, -22), Vector3(118, 0, -34), Vector3(70, 0, -70), Vector3(110, 0, -72), Vector3(88, 0, -16), Vector3(124, 0, -58)]:
		_tree(pos, true)
	_jar(Vector3(100, 0, -24))
	_jar(Vector3(114, 0, -18))
	_jar(Vector3(108, 0, -30))
	# Jar Nook, a side pocket off the east trees.
	add_child(Props.cylinder(0.55, 1.4, Color("6b5438"), Vector3(110, 0.7, -14)))


func _dress_ruin() -> void:
	for pos in [Vector3(68, 0, -90), Vector3(118, 0, -92), Vector3(66, 0, -132), Vector3(120, 0, -134), Vector3(92, 0, -146)]:
		add_child(Props.cylinder(0.55, 2.6, Color("b7b1a6"), pos + Vector3(0, 1.3, 0)))
	_jar(Vector3(88, 0, -124))
	_jar(Vector3(96, 0, -132))
	_jar(Vector3(92, 0, -136))
	add_child(Props.box(Vector3(6.0, 0.4, 2.0), Color("a39d94"), Vector3(92, 0.25, -118)))
	# Broken Landing, a side alcove of cracked steps.
	add_child(Props.box(Vector3(3.5, 0.35, 1.4), Color("8d877c"), Vector3(70, 0.2, -116)))
	add_child(Props.box(Vector3(2.4, 0.55, 1.2), Color("7a756c"), Vector3(73, 0.3, -112)))


func _dress_aldermoor_road() -> void:
	# Stone road east of the meadow fork, ending at a shut gate.
	_path(70, -48, 158, -34, Color("d9d3c4"))
	for x in [80, 100, 120, 140]:
		add_child(Props.cylinder(0.12, 2.2, Color("f4f1ea"), Vector3(x, 1.1, -32)))
		add_child(Props.box(Vector3(0.7, 1.1, 0.08), Color("2a4f86"), Vector3(x, 2.0, -32)))
		add_child(Props.cylinder(0.12, 2.2, Color("f4f1ea"), Vector3(x, 1.1, -50)))
		add_child(Props.box(Vector3(0.7, 1.1, 0.08), Color("2a4f86"), Vector3(x, 2.0, -50)))
	# The gate itself. The city doors stay closed this chapter.
	add_child(Props.cylinder(0.7, 4.2, Color("f7f4ee"), Vector3(156, 2.1, -48)))
	add_child(Props.cylinder(0.7, 4.2, Color("f7f4ee"), Vector3(156, 2.1, -34)))
	add_child(Props.box(Vector3(1.2, 3.2, 10.0), Color("e7e2d8"), Vector3(158.2, 1.6, -41)))
	add_child(Props.box(Vector3(0.4, 1.6, 6.0), Color("c9a24a"), Vector3(157.4, 3.5, -41)))
	add_child(Props.box(Vector3(14.0, 3.4, 1.2), Color("f4f1ea"), Vector3(162, 1.7, -30)))
	add_child(Props.box(Vector3(14.0, 3.4, 1.2), Color("f4f1ea"), Vector3(162, 1.7, -52)))
	add_child(Props.box(Vector3(1.0, 2.4, 8.0), Color("23406e"), Vector3(157.2, 2.6, -41)))
	var quill := ActorVisual.new()
	quill.position = quill_pos
	add_child(quill)
	quill.configure("lina", "Quill")
	quill.scale = Vector3(0.92, 0.92, 0.92)
	var ilvane := ActorVisual.new()
	ilvane.position = ilvane_pos
	add_child(ilvane)
	ilvane.configure("lina", "Ilvane")
	_sign(Vector3(74, 0, -30), "Aldermoor", "The stone road runs east to Aldermoor, the white city. The gate is ahead. The doors are shut. Seer Ilvane waits outside.")
	_sign(Vector3(146, 0, -30), "Gate", "Aldermoor. White stone, blue banners, a leaf over three waves. Press F to speak with Ilvane. The city itself is not open yet.")


func _dress_margins() -> void:
	# A few trees in the unused east, so the empty room reads as woods waiting, not a hole.
	for pos in [Vector3(140, 0, -24), Vector3(150, 0, -48), Vector3(142, 0, -64)]:
		_tree(pos, true)


func _tree(pos: Vector3, dark: bool) -> void:
	add_child(Props.cylinder(0.28, 1.7, Color("5a3b28"), pos + Vector3(0, 0.85, 0)))
	var leaf := Color("2c6240") if dark else Color("3f8f4a")
	add_child(Props.sphere(1.15, leaf, pos + Vector3(0, 2.15, 0)))
	var body := StaticBody3D.new()
	body.position = pos + Vector3(0, 0.9, 0)
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.55
	cyl.height = 1.8
	shape.shape = cyl
	body.add_child(shape)
	add_child(body)


func _jar(pos: Vector3) -> void:
	var node := Node3D.new()
	node.position = pos
	add_child(node)
	node.add_child(Props.cylinder(0.32, 0.62, Color("c4a574"), Vector3(0, 0.36, 0)))
	var cork := Props.sphere(0.18, Color("6b4423"), Vector3(0, 0.74, 0))
	cork.name = "Cork"
	node.add_child(cork)
	var wick := Props.sphere(0.14, Color("f6e3a1"), Vector3(0, 1.05, 0), 2.4)
	wick.name = "Wick"
	wick.visible = false
	node.add_child(wick)
	var glow := OmniLight3D.new()
	glow.name = "Glow"
	glow.position = Vector3(0, 1.15, 0)
	glow.light_color = Color("ffd48a")
	glow.light_energy = 0.9
	glow.omni_range = 4.2
	glow.visible = false
	node.add_child(glow)
	jars.append(node)
	var body := StaticBody3D.new()
	body.position = pos + Vector3(0, 0.35, 0)
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.36
	cyl.height = 0.7
	shape.shape = cyl
	body.add_child(shape)
	add_child(body)


func _sign(pos: Vector3, short: String, full: String) -> void:
	add_child(Props.cylinder(0.1, 1.35, Color("6b4a2e"), pos + Vector3(0, 0.68, 0)))
	var label := Label3D.new()
	label.text = short
	label.font_size = 32
	label.pixel_size = 0.01
	label.position = pos + Vector3(0, 1.7, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 8
	label.modulate = Color("f3e2c2")
	add_child(label)
	signs.append({"pos": pos, "text": full})


func _pickup(id: String, kind: String, pos: Vector3, note: String) -> void:
	var node := Node3D.new()
	node.position = pos
	add_child(node)
	if kind == "berry":
		node.add_child(Props.sphere(0.22, Color("c4553a"), Vector3(0, 0.28, 0), 0.35))
	elif kind == "sip":
		node.add_child(Props.sphere(0.2, Color("7ec8ea"), Vector3(0, 0.28, 0), 0.8))
		node.add_child(Props.cylinder(0.12, 0.18, Color("d9eef8"), Vector3(0, 0.16, 0)))
	else:
		node.add_child(Props.box(Vector3(0.42, 0.06, 0.3), Color("f0e2c4"), Vector3(0, 0.12, 0)))
	var area := Area3D.new()
	area.collision_layer = 0
	area.collision_mask = 1
	area.monitorable = false
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 1.05
	cyl.height = 1.4
	shape.shape = cyl
	shape.position = Vector3(0, 0.7, 0)
	area.add_child(shape)
	node.add_child(area)
	area.body_entered.connect(_on_pickup.bind(id))
	pickups[id] = {"kind": kind, "note": note, "node": node, "taken": false}


func _on_pickup(body: Node, id: String) -> void:
	if not active or (body != hero and body != panda_body):
		return
	if not pickups.has(id) or bool(pickups[id].taken):
		return
	pickups[id].taken = true
	var node: Node3D = pickups[id].node
	node.visible = false
	pickup_found.emit(str(pickups[id].kind), str(pickups[id].note))
