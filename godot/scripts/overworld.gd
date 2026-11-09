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
var quill_pos := Vector3.ZERO
var ilvane_pos := Vector3.ZERO
var lina_pos := Vector3.ZERO
var briar_pos := Vector3.ZERO
var wayside_pos := Vector3.ZERO
var holt_pos := Vector3.ZERO
var briar_built := false
var wayside_built := false
var signs: Array = []
var jars: Array = []
var foes := {}
var pickups := {}
var region_now := "camp"
var left_regions := {}

const TILE := 16.0
const ZONE1_SCALE := 3.34
const WALK_SPEED := 6.8
const CHUNK := 128.0
const STREAM_RADIUS := 380.0
const ZONE2_LENGTH := 2350.0
const ZONE2_BREADTH := 1680.0

var chunks := {}
var stream_timer := 0.0
var zone2_start := Vector3.ZERO
var zone2_end := Vector3.ZERO
var zone2_road_z := 0.0
var canopy_mat: ShaderMaterial
var canopy_dark: ShaderMaterial
var grass_mat: ShaderMaterial
var foliage_shader: Shader
var canopy_quad: QuadMesh
var grass_quad: QuadMesh

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
	quill_pos = _w(104.0, -30.0)
	ilvane_pos = _w(150.0, -38.0)
	_init_foliage()
	_ground()
	_hedges()
	_dress_camp()
	_dress_meadow()
	_dress_grove()
	_dress_ruin()
	_dress_margins()
	_dress_aldermoor_road()
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
	_sign(Vector3(148, 0, -22), "Fields", "Past the valley gate are the outer fields. Aldermoor's walls are the long white line, not this door.")
	_scatter_valley()
	_register_outer_fields()
	_build_city_wall()
	_make_hero()
	_update_stream()
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
	stream_timer += delta
	if stream_timer >= 0.35:
		stream_timer = 0.0
		_update_stream()
	_tick_foes(delta)


func region_id() -> String:
	if hero == null:
		return "camp"
	var p := hero.global_position
	if zone2_start != Vector3.ZERO and p.x > zone2_start.x - 12.0:
		return "fields"
	var x := p.x / ZONE1_SCALE
	var z := p.z / ZONE1_SCALE
	p = Vector3(x, 0, z)
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
	var raw := hero.global_position
	if region_id() == "fields":
		if briar_pos != Vector3.ZERO and raw.distance_to(briar_pos) < 70.0:
			return "Briarwell"
		if wayside_pos != Vector3.ZERO and raw.distance_to(wayside_pos) < 46.0:
			return "Wayside Camp"
		if holt_pos != Vector3.ZERO and raw.distance_to(holt_pos) < 55.0:
			return "Holt's Road"
		if raw.distance_to(Vector3(zone2_start.x + 1500.0, raw.y, zone2_road_z - 520.0)) < 90.0:
			return "Ash Ridge"
		if raw.x > zone2_end.x - 80.0:
			return "Aldermoor Walls"
		return "The Outer Fields"
	var p := Vector3(raw.x / ZONE1_SCALE, 0, raw.z / ZONE1_SCALE)
	if p.x > 98.0 and p.x < 112.0 and p.z > -40.0 and p.z < -22.0:
		return "Quill's Stall"
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
	place_world(_w(pos.x, pos.z))


func place_world(pos: Vector3) -> void:
	if hero == null:
		return
	hero.global_position = Vector3(pos.x, 0.9, pos.z)
	hero.velocity = Vector3.ZERO
	if panda_body:
		panda_body.global_position = hero.global_position + Vector3(1.6, 0.0, 1.4)
		panda_body.global_position.y = 0.9
		panda_prev = panda_body.global_position
	_update_stream()
	poll_region()


func _w(x: float, z: float) -> Vector3:
	return Vector3(x * ZONE1_SCALE, 0.0, z * ZONE1_SCALE)


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
	if str(foe.battle) == "stair" or str(foe.battle) == "holt":
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
	if briar_pos != Vector3.ZERO and _near_party(briar_pos, 3.2):
		npc_talk.emit("briar")
		return
	if wayside_pos != Vector3.ZERO and _near_party(wayside_pos, 3.2):
		npc_talk.emit("wayside")
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
		if not is_detail_awake_near(node.global_position):
			continue
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
	root.position = _w(float(at[0]), float(at[1]))
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
		ring.name = "Mark"
		root.add_child(ring)
		var tint := Color(0.75, 0.55, 0.85, 0.4)
		if str(spec.battle) == "lurker":
			tint = Color(0.85, 0.45, 0.25, 0.35)
		elif str(spec.battle) == "holt":
			tint = Color(0.78, 0.18, 0.14, 0.5)
		ring.setup(tint)
		ring.show_at(Vector3.ZERO, 2.1)
	_adopt(root, root.position)
	var points: Array = []
	for pair in spec.patrol:
		points.append(_w(float(pair[0]), float(pair[1])))
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
	hero.position = Vector3(0, 0.9, 30.0 * ZONE1_SCALE)
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
	panda_body.position = Vector3(1.6, 0.9, 30.0 * ZONE1_SCALE + 1.4)
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
	_wall(160, -168, 160, -54, dark)
	_wall(160, -28, 160, 46, dark)
	_wall(-60, -168, 160, -168, stone, false)
	# Camp hedge, with a wide gate onto the meadow. Never locked.
	_wall(-60, 12, -8, 12, hedge)
	_wall(8, 12, 160, 12, hedge)


func _patch(x0: float, z0: float, x1: float, z1: float, color: Color, y: float) -> void:
	var span_x := absf(x1 - x0)
	var span_z := absf(z1 - z0)
	if span_x > 36.0 or span_z > 36.0:
		var steps_x := maxi(1, int(ceil(span_x / 32.0)))
		var steps_z := maxi(1, int(ceil(span_z / 32.0)))
		for ix in steps_x:
			for iz in steps_z:
				var ax := lerpf(x0, x1, float(ix) / float(steps_x))
				var bx := lerpf(x0, x1, float(ix + 1) / float(steps_x))
				var az := lerpf(z0, z1, float(iz) / float(steps_z))
				var bz := lerpf(z0, z1, float(iz + 1) / float(steps_z))
				_patch(minf(ax, bx), minf(az, bz), maxf(ax, bx), maxf(az, bz), color, y)
		return
	var wx0 := x0 * ZONE1_SCALE
	var wz0 := z0 * ZONE1_SCALE
	var wx1 := x1 * ZONE1_SCALE
	var wz1 := z1 * ZONE1_SCALE
	var pos := Vector3((wx0 + wx1) * 0.5, y, (wz0 + wz1) * 0.5)
	_adopt(_paint_box(Vector3(absf(wx1 - wx0), 0.08, absf(wz1 - wz0)), color, pos), pos)


func _wall(x1: float, z1: float, x2: float, z2: float, color: Color, leafy: bool = true) -> void:
	var length := Vector2(x2 - x1, z2 - z1).length()
	var steps := maxi(1, int(ceil(length / 28.0)))
	for i in steps:
		var a := float(i) / float(steps)
		var b := float(i + 1) / float(steps)
		_wall_segment(lerpf(x1, x2, a), lerpf(z1, z2, a), lerpf(x1, x2, b), lerpf(z1, z2, b), color, leafy)


func _wall_segment(x1: float, z1: float, x2: float, z2: float, color: Color, leafy: bool) -> void:
	var mid := _w((x1 + x2) * 0.5, (z1 + z2) * 0.5)
	mid.y = 0.7
	var sx := absf(x2 - x1) * ZONE1_SCALE
	var sz := absf(z2 - z1) * ZONE1_SCALE
	var size := Vector3(sx + 1.1, 1.45, 1.1) if sx >= sz else Vector3(1.1, 1.45, sz + 1.1)
	_adopt(_paint_box(size, color, mid), mid)
	_adopt(_static_body(mid, size), mid)
	if leafy:
		var dir := _w(x2, z2) - _w(x1, z1)
		if dir.length() > 0.2:
			_hedge_fan(mid, dir.normalized())


func _static_body(pos: Vector3, size: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.position = pos
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	return body


func _dress_camp() -> void:
	# A tight yard around the spawn, in world meters, so home reads as one place.
	var yard := Vector3(0.0, 0.0, 30.0 * ZONE1_SCALE)
	_adopt(_paint_box(Vector3(14.0, 0.08, 12.0), Color("c4a06a"), yard + Vector3(0, 0.06, 0)), yard)
	lina_pos = yard + Vector3(3.2, 0.0, 0.6)
	var lina := ActorVisual.new()
	lina.position = lina_pos
	_adopt(lina, lina_pos)
	lina.configure("lina", "Lina")
	var hearth := yard + Vector3(-2.4, 0.0, 1.8)
	_adopt(Props.cylinder(0.7, 0.22, Color("6b5344"), hearth + Vector3(0, 0.12, 0)), hearth)
	_adopt(Props.sphere(0.28, Color("ff8a3c"), hearth + Vector3(0, 0.42, 0), 2.2), hearth)
	var fire := OmniLight3D.new()
	fire.position = hearth + Vector3(0, 0.8, 0)
	fire.light_color = Color("ffb060")
	fire.light_energy = 1.4
	fire.omni_range = 14.0
	_adopt(fire, hearth)
	var tent_at := yard + Vector3(5.4, 0.0, -1.2)
	_adopt(_paint_box(Vector3(3.4, 1.6, 2.4), Color("8c3d3d"), tent_at + Vector3(0, 0.8, 0)), tent_at)
	var bench := yard + Vector3(1.2, 0.0, -2.6)
	_adopt(_paint_box(Vector3(1.8, 0.42, 0.55), Color("a07a48"), bench + Vector3(0, 0.28, 0)), bench)
	var line_a := yard + Vector3(-1.2, 0.0, -2.2)
	var line_b := yard + Vector3(-4.2, 0.0, -2.2)
	_adopt(Props.cylinder(0.08, 2.2, Color("6b4a2e"), line_a + Vector3(0, 1.1, 0)), line_a)
	_adopt(Props.cylinder(0.08, 2.2, Color("6b4a2e"), line_b + Vector3(0, 1.1, 0)), line_b)
	var cloth := MeshInstance3D.new()
	cloth.mesh = canopy_quad
	cloth.scale = Vector3(0.55, 0.28, 0.55)
	cloth.position = (line_a + line_b) * 0.5 + Vector3(0, 1.7, 0)
	cloth.rotation.y = PI / 2.0
	cloth.material_override = _flat_mat(Color("d4553a"))
	cloth.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_adopt(cloth, cloth.position)
	_jar(Vector3(yard.x / ZONE1_SCALE - 1.6, 0, yard.z / ZONE1_SCALE + 0.8))
	_pickup("berry_yard", "berry", Vector3((yard.x - 3.6) / ZONE1_SCALE, 0, (yard.z - 1.2) / ZONE1_SCALE), "")
	var home := Label3D.new()
	home.text = "Bramblewick"
	home.font_size = 52
	home.pixel_size = 0.014
	home.position = yard + Vector3(0, 3.4, 0)
	home.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	home.modulate = Color("f3e2c2")
	_adopt(home, home.position)
	_sign_world(yard + Vector3(0, 0, 4.2), "Home", "Bramblewick Camp. Lina's yard is home. Nothing wanders here. Press F. She will point you to Quill's stall, east on the stone road.")


func _dress_meadow() -> void:
	for pos in [Vector3(-40, 0, -8), Vector3(-48, 0, -28), Vector3(48, 0, -18), Vector3(-36, 0, -70), Vector3(40, 0, -74), Vector3(12, 0, -8), Vector3(-14, 0, -46)]:
		_tree(pos, false)
	# Lamb Hill: a ring of stones and a step, west of the fork. Not on the way to the grove.
	for i in 8:
		var angle := TAU * float(i) / 8.0
		var stone := Props.cylinder(0.9, 1.8, Color("b7b1a4"), Vector3(-46 + cos(angle) * 4.2, 0.9, -18 + sin(angle) * 4.2))
		_place_design(stone)
	_place_design(Props.cylinder(2.4, 0.45, Color("cfc6b4"), Vector3(-46, 0.25, -18)))
	# Creek reeds. The water tiles are already blue.
	for pos in [Vector3(22, 0, -6), Vector3(30, 0, 4), Vector3(42, 0, -8), Vector3(24, 0, 6)]:
		_place_design(Props.cylinder(0.08, 1.4, Color("2f6a48"), pos + Vector3(0, 0.7, 0)))
	_place_design(Props.sphere(0.55, Color("d9d3c6"), Vector3(34, 0.3, 0)))


func _dress_grove() -> void:
	for pos in [Vector3(66, 0, -18), Vector3(96, 0, -22), Vector3(118, 0, -34), Vector3(70, 0, -70), Vector3(110, 0, -72), Vector3(88, 0, -16), Vector3(124, 0, -58)]:
		_tree(pos, true)
	_jar(Vector3(100, 0, -24))
	_jar(Vector3(114, 0, -18))
	_jar(Vector3(108, 0, -30))
	# Jar Nook, a side pocket off the east trees.
	_place_design(Props.cylinder(0.7, 2.2, Color("6b5438"), Vector3(110, 1.1, -14)))


func _dress_ruin() -> void:
	for pos in [Vector3(68, 0, -90), Vector3(118, 0, -92), Vector3(66, 0, -132), Vector3(120, 0, -134), Vector3(92, 0, -146)]:
		_place_design(Props.cylinder(0.8, 4.2, Color("b7b1a6"), pos + Vector3(0, 2.1, 0)))
	_jar(Vector3(88, 0, -124))
	_jar(Vector3(96, 0, -132))
	_jar(Vector3(92, 0, -136))
	_place_design(Props.box(Vector3(8.0, 0.5, 2.4), Color("a39d94"), Vector3(92, 0.3, -118)))
	_place_design(Props.box(Vector3(4.5, 0.45, 1.8), Color("8d877c"), Vector3(70, 0.25, -116)))
	_place_design(Props.box(Vector3(3.2, 0.7, 1.5), Color("7a756c"), Vector3(73, 0.4, -112)))


func _dress_aldermoor_road() -> void:
	# Stone road east of the meadow fork, ending at a shut gate.
	_path(70, -48, 158, -34, Color("d9d3c4"))
	for x in [80, 100, 120, 140]:
		_place_design(Props.cylinder(0.16, 3.4, Color("f4f1ea"), Vector3(x, 1.7, -32)))
		_place_design(Props.box(Vector3(1.1, 1.6, 0.08), Color("2a4f86"), Vector3(x, 3.2, -32)))
		_place_design(Props.cylinder(0.16, 3.4, Color("f4f1ea"), Vector3(x, 1.7, -50)))
		_place_design(Props.box(Vector3(1.1, 1.6, 0.08), Color("2a4f86"), Vector3(x, 3.2, -50)))
	# Valley gate. The road continues through it into the outer fields. The city is not here.
	_place_design(Props.cylinder(0.85, 6.5, Color("f7f4ee"), Vector3(156, 3.2, -50)))
	_place_design(Props.cylinder(0.85, 6.5, Color("f7f4ee"), Vector3(156, 3.2, -32)))
	_place_design(Props.box(Vector3(0.5, 2.2, 8.0), Color("c9a24a"), Vector3(156.4, 5.6, -41)))
	_place_design(Props.box(Vector3(1.4, 3.6, 12.0), Color("23406e"), Vector3(156.8, 3.2, -41)))
	_dress_quill_stall()
	var quill := ActorVisual.new()
	quill.position = quill_pos
	_adopt(quill, quill_pos)
	quill.configure("lina", "Quill")
	var ilvane := ActorVisual.new()
	ilvane.position = Vector3(150, 0, -38)
	_place_design(ilvane)
	ilvane.configure("lina", "Ilvane")
	_sign(Vector3(74, 0, -30), "Aldermoor", "The stone road runs east to Aldermoor, the white city. The gate is ahead. The doors are shut. Seer Ilvane waits outside.")
	_sign(Vector3(146, 0, -30), "Gate", "The valley door. The outer fields are through here. Aldermoor's walls are still a long walk east. Press F for Ilvane. She will not take the shard.")


func _dress_margins() -> void:
	# A few trees in the unused east, so the empty room reads as woods waiting, not a hole.
	for pos in [Vector3(140, 0, -24), Vector3(150, 0, -48), Vector3(142, 0, -64)]:
		_tree(pos, true)


func _tree(pos: Vector3, dark: bool) -> void:
	var holder := Node3D.new()
	holder.position = Vector3(pos.x, 0.0, pos.z)
	var trunk := Props.cylinder(0.22, 2.4, Color("5a3b28"), Vector3(0, 1.2, 0))
	holder.add_child(trunk)
	for i in 3:
		var card := MeshInstance3D.new()
		card.mesh = canopy_quad
		card.position = Vector3(0, 3.15, 0)
		card.rotation.y = float(i) * PI / 3.0
		card.material_override = canopy_dark if dark else canopy_mat
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		holder.add_child(card)
	var body := _static_body(Vector3(0, 1.3, 0), Vector3(0.7, 2.6, 0.7))
	holder.add_child(body)
	_place_design(holder)


func _jar(pos: Vector3) -> void:
	var node := Node3D.new()
	node.position = pos
	_place_design(node)
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
	var body := _static_body(node.position + Vector3(0, 0.35, 0), Vector3(0.7, 0.7, 0.7))
	_adopt(body, body.position)


func _dress_quill_stall() -> void:
	var stall := quill_pos
	_adopt(_paint_box(Vector3(4.2, 0.9, 1.4), Color("8a5a32"), stall + Vector3(-1.6, 0.45, -0.2)), stall)
	var awning := MeshInstance3D.new()
	awning.mesh = canopy_quad
	awning.scale = Vector3(1.15, 0.42, 1.0)
	awning.position = stall + Vector3(-1.4, 1.7, -0.2)
	awning.rotation.x = -PI / 2.2
	awning.material_override = _flat_mat(Color("2a4f86"))
	awning.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_adopt(awning, awning.position)
	_adopt(_paint_box(Vector3(0.7, 0.7, 0.7), Color("c4a574"), stall + Vector3(-3.2, 0.35, 0.8)), stall)
	_adopt(_paint_box(Vector3(0.55, 0.5, 0.55), Color("6b4423"), stall + Vector3(-2.6, 0.9, 0.9)), stall)
	var banner := Label3D.new()
	banner.text = "Quill"
	banner.font_size = 48
	banner.pixel_size = 0.012
	banner.position = stall + Vector3(0, 2.6, 0)
	banner.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	banner.modulate = Color("f3e2c2")
	_adopt(banner, banner.position)
	_sign_world(stall + Vector3(2.2, 0, 1.4), "Stall", "Quill's stall. Berries and news. Press F. He sends you on to Seer Ilvane at the valley gate.")


func _sign(pos: Vector3, short: String, full: String) -> void:
	_place_design(Props.cylinder(0.1, 1.6, Color("6b4a2e"), pos + Vector3(0, 0.8, 0)))
	var label := Label3D.new()
	label.text = short
	label.font_size = 48
	label.pixel_size = 0.012
	label.position = pos + Vector3(0, 2.1, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 10
	label.modulate = Color("f3e2c2")
	_place_design(label)
	signs.append({"pos": _w(pos.x, pos.z), "text": full})


func _sign_world(pos: Vector3, short: String, full: String) -> void:
	_adopt(Props.cylinder(0.1, 1.6, Color("6b4a2e"), pos + Vector3(0, 0.8, 0)), pos)
	var label := Label3D.new()
	label.text = short
	label.font_size = 48
	label.pixel_size = 0.012
	label.position = pos + Vector3(0, 2.1, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 10
	label.modulate = Color("f3e2c2")
	_adopt(label, label.position)
	signs.append({"pos": pos, "text": full})


func _pickup(id: String, kind: String, pos: Vector3, note: String) -> void:
	var node := Node3D.new()
	node.position = pos
	_place_design(node)
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


func _place_design(node: Node3D) -> void:
	node.position = Vector3(node.position.x * ZONE1_SCALE, node.position.y, node.position.z * ZONE1_SCALE)
	_adopt(node, node.position)


func _init_foliage() -> void:
	canopy_quad = QuadMesh.new()
	canopy_quad.size = Vector2(6.8, 5.6)
	grass_quad = QuadMesh.new()
	grass_quad.size = Vector2(1.7, 1.25)
	canopy_mat = _foliage_material(_paint_canopy(Color("6ea24a"), Color("2f6b38"), Color("d7e39a")), 80.0, 220.0)
	canopy_dark = _foliage_material(_paint_canopy(Color("3d7a45"), Color("1e4a2c"), Color("c5d98a")), 80.0, 220.0)
	grass_mat = _foliage_material(_paint_canopy(Color("8fb85a"), Color("4e7a32"), Color("e7efb0")), 18.0, 46.0)


func _foliage_material(tex: Texture2D, fade_min: float, fade_max: float) -> ShaderMaterial:
	if foliage_shader == null:
		foliage_shader = Shader.new()
		foliage_shader.code = "shader_type spatial;
render_mode unshaded, cull_disabled;
uniform sampler2D tex : filter_linear, repeat_disable;
uniform float cutoff = 0.35;
uniform float fade_start = 80.0;
uniform float fade_end = 220.0;
void fragment() {
	vec4 col = texture(tex, UV);
	float dist = length(VERTEX);
	float fade = clamp((fade_end - dist) / max(fade_end - fade_start, 0.001), 0.0, 1.0);
	if (col.a < cutoff || fade < 0.04) {
		discard;
	}
	ALBEDO = col.rgb;
}"
	var mat := ShaderMaterial.new()
	mat.shader = foliage_shader
	mat.set_shader_parameter("tex", tex)
	mat.set_shader_parameter("fade_start", fade_min)
	mat.set_shader_parameter("fade_end", fade_max)
	return mat


func _paint_canopy(leaf: Color, shade: Color, tip: Color) -> ImageTexture:
	var image := Image.create(96, 96, false, Image.FORMAT_RGBA8)
	image.fill(Color(0, 0, 0, 0))
	var blobs := [
		[48, 58, 30, 26, leaf],
		[34, 46, 18, 16, shade],
		[62, 44, 16, 18, leaf],
		[48, 34, 14, 12, tip],
		[40, 68, 12, 10, shade],
		[58, 66, 11, 9, leaf],
	]
	for blob in blobs:
		_paint_blob(image, int(blob[0]), int(blob[1]), int(blob[2]), int(blob[3]), blob[4])
	return ImageTexture.create_from_image(image)


func _paint_blob(image: Image, cx: int, cy: int, rx: int, ry: int, color: Color) -> void:
	for y in range(maxi(0, cy - ry), mini(image.get_height(), cy + ry)):
		for x in range(maxi(0, cx - rx), mini(image.get_width(), cx + rx)):
			var nx := float(x - cx) / float(rx)
			var ny := float(y - cy) / float(ry)
			var d := nx * nx + ny * ny
			if d <= 1.0:
				var edge := clampf((1.0 - d) * 2.2, 0.0, 1.0)
				var src := image.get_pixel(x, y)
				var out := Color(color.r, color.g, color.b, edge)
				image.set_pixel(x, y, src.blend(out))


func _scatter_valley() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 560
	for i in 240:
		var x := rng.randf_range(-54.0, 148.0)
		var z := rng.randf_range(-158.0, 6.0)
		if _blocks_crossing(x, z):
			continue
		_tree(Vector3(x, 0, z), x > 55.0)
		if i % 2 == 0:
			_grass(Vector3(x + rng.randf_range(-3.0, 3.0), 0, z + rng.randf_range(-2.0, 2.0)))
	for i in 160:
		var x := rng.randf_range(-52.0, 150.0)
		var z := rng.randf_range(-155.0, 4.0)
		if _blocks_crossing(x, z):
			continue
		_grass(Vector3(x, 0, z))


func _blocks_crossing(x: float, z: float) -> bool:
	if z > 10.0 and absf(x) < 24.0:
		return true
	if absf(x) < 8.0 and z < 14.0:
		return true
	if absf(z + 41.0) < 8.0 and x > -58.0:
		return true
	if absf(x - 104.0) < 5.0 and absf(z + 30.0) < 5.0:
		return true
	if absf(x - 150.0) < 4.0 and absf(z + 38.0) < 4.0:
		return true
	return false


func _hedge_fan(mid: Vector3, dir: Vector3) -> void:
	for i in 2:
		var card := MeshInstance3D.new()
		card.mesh = canopy_quad
		card.scale = Vector3(0.9, 0.58, 0.9)
		card.position = mid + dir * ((float(i) - 0.5) * 6.0) + Vector3(0, 0.9, 0)
		card.rotation.y = atan2(dir.x, dir.z) + float(i) * 0.75
		card.material_override = canopy_mat
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_adopt(card, card.position)


func _paint_box(size: Vector3, color: Color, pos: Vector3) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.material_override = _flat_mat(color)
	node.position = pos
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return node


func _grass(pos: Vector3) -> void:
	var holder := Node3D.new()
	holder.position = pos
	for i in 3:
		var card := MeshInstance3D.new()
		card.mesh = grass_quad
		card.position = Vector3(float(i) * 0.15, 0.4, 0)
		card.rotation.y = float(i) * 0.8
		card.material_override = grass_mat
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		holder.add_child(card)
	_place_design(holder)


func _register_outer_fields() -> void:
	zone2_road_z = -41.0 * ZONE1_SCALE
	zone2_start = Vector3(164.0 * ZONE1_SCALE, 0.0, zone2_road_z)
	zone2_end = zone2_start + Vector3(ZONE2_LENGTH, 0.0, 0.0)
	briar_pos = Vector3(zone2_start.x + 900.0, 0.0, zone2_road_z + 62.0)
	wayside_pos = zone2_end + Vector3(-520.0, 0.0, 22.0)
	holt_pos = zone2_end + Vector3(-190.0, 0.0, 6.0)
	var x := zone2_start.x
	while x < zone2_end.x + CHUNK:
		var z := zone2_road_z - ZONE2_BREADTH * 0.5
		var z_limit := zone2_road_z + ZONE2_BREADTH * 0.5
		while z < z_limit:
			var key := _chunk_key(Vector3(x, 0, z))
			var chunk := _ensure_chunk(key, Vector3(x, 0, z))
			chunk.zone = "fields"
			z += CHUNK
		x += CHUNK


func _build_city_wall() -> void:
	var wall_at := Vector3(zone2_end.x, 8.0, zone2_road_z)
	add_child(_paint_box(Vector3(10.0, 16.0, 380.0), Color("f6f3ec"), wall_at))
	add_child(_static_body(wall_at, Vector3(10.0, 16.0, 380.0)))
	for i in range(-4, 5):
		var banner := MeshInstance3D.new()
		banner.mesh = canopy_quad
		banner.position = Vector3(zone2_end.x - 6.0, 11.0, zone2_road_z + float(i) * 36.0)
		banner.material_override = _flat_mat(Color("2a4f86"))
		banner.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(banner)
	add_child(_paint_box(Vector3(8.0, 8.0, 18.0), Color("23406e"), Vector3(zone2_end.x - 2.0, 5.0, zone2_road_z)))


func _flat_mat(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	return mat


func _build_fields_detail(chunk: Dictionary) -> void:
	var key: Vector2i = chunk.key
	var origin := _chunk_center(key)
	var rng := RandomNumberGenerator.new()
	rng.seed = int(abs(key.x * 9176 + key.y * 131)) + 3
	for i in rng.randi_range(12, 18):
		var pos := origin + Vector3(rng.randf_range(-52, 52), 0, rng.randf_range(-52, 52))
		if absf(pos.z - zone2_road_z) < 12.0 or _near_hub(pos, 16.0):
			continue
		_tree_world(pos, rng.randf() > 0.45)
	for i in 12:
		var tuft := origin + Vector3(rng.randf_range(-46, 46), 0, rng.randf_range(-46, 46))
		if absf(tuft.z - zone2_road_z) < 9.0:
			continue
		_grass_world(tuft)
	if absf(origin.z - zone2_road_z) < CHUNK:
		chunk.detail.add_child(_paint_box(Vector3(CHUNK, 0.12, 14.0), Color("cbbfa6"), Vector3(origin.x, 0.06, zone2_road_z)))
	if not briar_built and origin.distance_to(briar_pos) < 90.0:
		briar_built = true
		_hamlet(chunk, briar_pos)
	if not wayside_built and origin.distance_to(wayside_pos) < 90.0:
		wayside_built = true
		_wayside(chunk, wayside_pos)
	if _chunk_key(holt_pos) == key:
		_mark_holt(chunk)
	var ridge := Vector3(zone2_start.x + 1500.0, 0, zone2_road_z - 520.0)
	if origin.distance_to(ridge) < 90.0:
		_ridge(chunk, ridge)
	if int(abs(key.x + key.y)) % 4 == 0 and absf(origin.z - zone2_road_z) > 40.0:
		var imp_at := origin + Vector3(rng.randf_range(-20, 20), 0, rng.randf_range(-20, 20))
		if not _near_hub(imp_at, 24.0):
			_spawn_field_foe(chunk, imp_at)


func _hamlet(chunk: Dictionary, at: Vector3) -> void:
	for i in 6:
		var spot := at + Vector3(float(i % 3) * 16.0 - 16.0, 0, float(i / 3) * 18.0)
		var house := Props.box(Vector3(7.0, 3.2, 6.0), Color("f4f1ea"), spot + Vector3(0, 1.6, 0))
		house.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		chunk.detail.add_child(house)
		var solid := _static_body(spot + Vector3(0, 1.6, 0), Vector3(7.0, 3.2, 6.0))
		chunk.detail.add_child(solid)
		_gather_shapes(solid, chunk)
		var roof := Props.box(Vector3(8.0, 1.4, 7.0), Color("2a4f86"), spot + Vector3(0, 3.6, 0))
		roof.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		chunk.detail.add_child(roof)
	var label := Label3D.new()
	label.text = "Briarwell"
	label.font_size = 64
	label.pixel_size = 0.02
	label.position = at + Vector3(0, 6.0, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	chunk.detail.add_child(label)
	var hearth := at + Vector3(-6.0, 0.0, -6.0)
	chunk.detail.add_child(Props.cylinder(0.6, 0.2, Color("6b5344"), hearth + Vector3(0, 0.12, 0)))
	chunk.detail.add_child(Props.sphere(0.22, Color("ff8a3c"), hearth + Vector3(0, 0.36, 0), 1.6))
	for bench_x in [-2.2, 2.4]:
		chunk.detail.add_child(_paint_box(Vector3(1.6, 0.4, 0.5), Color("a07a48"), at + Vector3(bench_x, 0.28, -4.0)))
	var neighbor := ActorVisual.new()
	neighbor.position = briar_pos
	chunk.detail.add_child(neighbor)
	neighbor.configure("neighbor", "Neighbor")
	_sign_world(at + Vector3(0, 0, 8), "Briarwell", "Briarwell. Blue roofs, one fire. Press F. The next stop is Wayside Camp, on the road, before the warrior and the shut wall.")


func _wayside(chunk: Dictionary, at: Vector3) -> void:
	chunk.detail.add_child(_paint_box(Vector3(3.6, 1.5, 2.6), Color("c4a574"), at + Vector3(-3.2, 0.75, 0)))
	chunk.detail.add_child(_paint_box(Vector3(3.2, 1.3, 2.2), Color("8c3d3d"), at + Vector3(3.0, 0.65, 1.2)))
	var solid_a := _static_body(at + Vector3(-3.2, 0.75, 0), Vector3(3.6, 1.5, 2.6))
	var solid_b := _static_body(at + Vector3(3.0, 0.65, 1.2), Vector3(3.2, 1.3, 2.2))
	chunk.detail.add_child(solid_a)
	chunk.detail.add_child(solid_b)
	_gather_shapes(solid_a, chunk)
	_gather_shapes(solid_b, chunk)
	chunk.detail.add_child(Props.cylinder(0.55, 0.18, Color("6b5344"), at + Vector3(0, 0.12, -2.4)))
	chunk.detail.add_child(Props.sphere(0.2, Color("ff8a3c"), at + Vector3(0, 0.34, -2.4), 1.4))
	var cloth := MeshInstance3D.new()
	cloth.mesh = canopy_quad
	cloth.scale = Vector3(0.7, 0.9, 0.7)
	cloth.position = at + Vector3(0.2, 2.4, 1.6)
	cloth.material_override = _flat_mat(Color("8c2f2f"))
	cloth.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	chunk.detail.add_child(cloth)
	var watcher := ActorVisual.new()
	watcher.position = wayside_pos + Vector3(0.4, 0, -1.2)
	chunk.detail.add_child(watcher)
	watcher.configure("watcher", "Watcher")
	var label := Label3D.new()
	label.text = "Wayside"
	label.font_size = 48
	label.pixel_size = 0.014
	label.position = at + Vector3(0, 3.2, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.modulate = Color("f3e2c2")
	chunk.detail.add_child(label)
	_sign_world(at + Vector3(0, 0, 4.5), "Wayside", "Wayside Camp. The last fire before the wall. Press F. Holt, the warrior, stands on the road ahead. The city doors stay shut.")


func _mark_holt(chunk: Dictionary) -> void:
	if foes.has("holt"):
		return
	var pole := holt_pos + Vector3(-4.5, 0, -2.0)
	chunk.detail.add_child(Props.cylinder(0.12, 4.2, Color("f4f1ea"), pole + Vector3(0, 2.1, 0)))
	var cloth := MeshInstance3D.new()
	cloth.mesh = canopy_quad
	cloth.scale = Vector3(0.55, 0.7, 0.55)
	cloth.position = pole + Vector3(0.4, 3.4, 0)
	cloth.material_override = _flat_mat(Color("8c2f2f"))
	cloth.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	chunk.detail.add_child(cloth)
	var pos := holt_pos
	_spawn_foe({
		"id": "holt",
		"region": "fields",
		"battle": "holt",
		"kind": "warrior",
		"name": "Holt",
		"scale": 1.45,
		"special": true,
		"at": [pos.x / ZONE1_SCALE, pos.z / ZONE1_SCALE],
		"patrol": [
			[pos.x / ZONE1_SCALE, pos.z / ZONE1_SCALE],
			[(pos.x + 8.0) / ZONE1_SCALE, (pos.z + 4.0) / ZONE1_SCALE],
			[(pos.x - 6.0) / ZONE1_SCALE, (pos.z + 3.0) / ZONE1_SCALE],
		],
	})


func _near_hub(pos: Vector3, radius: float) -> bool:
	if briar_pos != Vector3.ZERO and pos.distance_to(briar_pos) < radius:
		return true
	if wayside_pos != Vector3.ZERO and pos.distance_to(wayside_pos) < radius:
		return true
	if holt_pos != Vector3.ZERO and pos.distance_to(holt_pos) < radius:
		return true
	return false


func _ridge(chunk: Dictionary, at: Vector3) -> void:
	chunk.detail.add_child(Props.cylinder(6.0, 2.2, Color("cfc6b4"), at + Vector3(0, 1.1, 0)))
	chunk.detail.add_child(Props.cylinder(3.2, 3.4, Color("b7b1a4"), at + Vector3(0, 2.4, 0)))
	var card := MeshInstance3D.new()
	card.mesh = canopy_quad
	card.position = at + Vector3(0, 6.5, 0)
	card.material_override = _flat_mat(Color("2a4f86"))
	chunk.detail.add_child(card)
	signs.append({"pos": at, "text": "Ash Ridge. From here the valley gate is small, and the white walls are still ahead. The spirit panda is for a longer road than this one."})


func _spawn_field_foe(chunk: Dictionary, pos: Vector3) -> void:
	var spec := {
		"id": "imp_%d_%d" % [int(chunk.key.x), int(chunk.key.y)],
		"region": "fields",
		"battle": "mite",
		"kind": "mite",
		"name": "Thistle Imp",
		"scale": 1.0,
		"special": false,
		"at": [pos.x / ZONE1_SCALE, pos.z / ZONE1_SCALE],
		"patrol": [
			[pos.x / ZONE1_SCALE, pos.z / ZONE1_SCALE],
			[(pos.x + 18.0) / ZONE1_SCALE, pos.z / ZONE1_SCALE],
			[(pos.x + 18.0) / ZONE1_SCALE, (pos.z + 14.0) / ZONE1_SCALE],
		],
	}
	_spawn_foe(spec)


func _tree_world(pos: Vector3, dark: bool) -> void:
	var holder := Node3D.new()
	holder.position = pos
	holder.add_child(Props.cylinder(0.22, 2.4, Color("5a3b28"), Vector3(0, 1.2, 0)))
	for i in 3:
		var card := MeshInstance3D.new()
		card.mesh = canopy_quad
		card.position = Vector3(0, 3.15, 0)
		card.rotation.y = float(i) * PI / 3.0
		card.material_override = canopy_dark if dark else canopy_mat
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		holder.add_child(card)
	holder.add_child(_static_body(Vector3(0, 1.3, 0), Vector3(0.7, 2.6, 0.7)))
	_adopt(holder, pos)


func _grass_world(pos: Vector3) -> void:
	var holder := Node3D.new()
	holder.position = pos
	for i in 3:
		var card := MeshInstance3D.new()
		card.mesh = grass_quad
		card.position = Vector3(float(i) * 0.15, 0.4, 0)
		card.rotation.y = float(i) * 0.8
		card.material_override = grass_mat
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		holder.add_child(card)
	_adopt(holder, pos)


func _adopt(node: Node, at: Vector3) -> void:
	var key := _chunk_key(at)
	var chunk: Dictionary = _ensure_chunk(key, at)
	chunk.detail.add_child(node)
	chunk.built = true
	_gather_shapes(node, chunk)


func _ensure_chunk(key: Vector2i, sample: Vector3) -> Dictionary:
	if chunks.has(key):
		return chunks[key]
	var root := Node3D.new()
	root.name = "Chunk_%d_%d" % [key.x, key.y]
	var detail := Node3D.new()
	detail.name = "Detail"
	detail.visible = false
	root.add_child(detail)
	var center := _chunk_center(key)
	root.add_child(_paint_box(Vector3(CHUNK, 0.16, CHUNK), _biome_color(center), Vector3(center.x, -0.12, center.z)))
	if zone2_start != Vector3.ZERO and center.x > zone2_start.x - 20.0 and absf(center.z - zone2_road_z) < CHUNK * 0.6:
		root.add_child(_paint_box(Vector3(CHUNK, 0.08, 14.0), Color("cbbfa6"), Vector3(center.x, 0.02, zone2_road_z)))
	var far := Node3D.new()
	far.name = "FarFoliage"
	for i in 3:
		var card := MeshInstance3D.new()
		card.mesh = canopy_quad
		card.scale = Vector3(2.4, 2.4, 2.4)
		card.position = center + Vector3(float(i - 1) * 28.0, 4.5, float((i % 2) * 24 - 12))
		card.rotation.y = float(i) * 0.9
		card.material_override = canopy_dark if center.x > zone2_start.x else canopy_mat
		card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		far.add_child(card)
	root.add_child(far)
	add_child(root)
	var chunk := {
		"key": key,
		"root": root,
		"detail": detail,
		"far": far,
		"awake": false,
		"built": false,
		"zone": "valley" if sample.x < 160.0 * ZONE1_SCALE else "fields",
		"shapes": [],
	}
	chunks[key] = chunk
	return chunk


func _gather_shapes(node: Node, chunk: Dictionary) -> void:
	if node is CollisionShape3D:
		chunk.shapes.append(node)
	for child in node.get_children():
		_gather_shapes(child, chunk)


func _chunk_key(at: Vector3) -> Vector2i:
	return Vector2i(int(floor(at.x / CHUNK)), int(floor(at.z / CHUNK)))


func _chunk_center(key: Vector2i) -> Vector3:
	return Vector3((float(key.x) + 0.5) * CHUNK, 0.0, (float(key.y) + 0.5) * CHUNK)


func _biome_color(world: Vector3) -> Color:
	if zone2_start != Vector3.ZERO and world.x > zone2_start.x - 20.0:
		return Color("7ea354") if int(floor(world.x / CHUNK) + floor(world.z / CHUNK)) % 2 == 0 else Color("6f9a4c")
	var x := world.x / ZONE1_SCALE
	var z := world.z / ZONE1_SCALE
	if z > 12.0 and absf(x) < 30.0:
		return Color("c4a06a")
	if x > 58.0 and z < -78.0:
		return Color("9a9488")
	if x > 58.0:
		return Color("3f6b46")
	if x > 18.0 and x < 52.0 and z > -12.0 and z < 10.0:
		return Color("7eb4cc")
	return Color("8fb862")


func _update_stream() -> void:
	if hero == null:
		return
	var anchors: Array[Vector3] = [hero.global_position]
	if panda_body:
		anchors.append(panda_body.global_position)
	for key in chunks.keys():
		var chunk: Dictionary = chunks[key]
		var center: Vector3 = _chunk_center(key)
		var near := false
		for anchor in anchors:
			if Vector2(center.x - anchor.x, center.z - anchor.z).length() <= STREAM_RADIUS:
				near = true
				break
		if near == bool(chunk.awake):
			continue
		_set_awake(chunk, near)


func _set_awake(chunk: Dictionary, on: bool) -> void:
	if on and not bool(chunk.built) and str(chunk.zone) == "fields":
		_build_fields_detail(chunk)
		chunk.built = true
	var detail: Node3D = chunk.detail
	detail.visible = on
	var far: Node3D = chunk.far
	far.visible = not on
	for shape in chunk.shapes:
		shape.disabled = not on
	chunk.awake = on


func is_detail_awake_near(at: Vector3) -> bool:
	var key := _chunk_key(at)
	if not chunks.has(key):
		return false
	return bool(chunks[key].awake)


func is_chunk_awake_at_world(at: Vector3) -> bool:
	return is_detail_awake_near(at)


func awake_chunk_count() -> int:
	var n := 0
	for key in chunks.keys():
		if bool(chunks[key].awake):
			n += 1
	return n


func chunk_count() -> int:
	return chunks.size()


func zone1_cross_seconds() -> float:
	var west := _w(-58.0, -41.0)
	var east := _w(156.0, -41.0)
	return Vector2(east.x - west.x, east.z - west.z).length() / WALK_SPEED


func zone1_north_south_seconds() -> float:
	var south := _w(0.0, 42.0)
	var north := _w(0.0, -162.0)
	return Vector2(north.x - south.x, north.z - south.z).length() / WALK_SPEED


func zone2_cross_seconds() -> float:
	if zone2_start == Vector3.ZERO:
		return 0.0
	return zone2_start.distance_to(zone2_end) / WALK_SPEED


func zone2_breadth_seconds() -> float:
	return ZONE2_BREADTH / WALK_SPEED


func zone2_sample_point() -> Vector3:
	return zone2_start + Vector3(ZONE2_LENGTH * 0.72, 0.9, 0.0)
