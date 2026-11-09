extends Node3D

const Props = preload("res://scripts/props.gd")

var kind := ""
var anim: AnimationPlayer
var mesh_root: Node3D
var moving := false
var bob := 0.0
var hop_left := 0.0
var spin_t := 0.0
var flash_t := 0.0
var bow_t := 0.0
var fallen := false

const LABEL_Y := {
	"archer": 2.15,
	"panda": 1.45,
	"mite": 1.05,
	"lurker": 1.75,
	"boss": 2.55,
	"lina": 2.0,
}


func configure(kind_name: String, label_text: String) -> void:
	kind = kind_name
	mesh_root = Node3D.new()
	mesh_root.name = "MeshRoot"
	add_child(mesh_root)
	match kind:
		"archer":
			_build_archer()
		"panda":
			_build_panda()
		"mite":
			_build_mite()
		"lurker":
			_build_lurker()
		"boss":
			_build_boss()
		"lina":
			_build_lina()
		_:
			mesh_root.add_child(Props.sphere(0.4, Color.WHITE, Vector3(0, 0.5, 0)))
	var label := Label3D.new()
	label.text = label_text
	label.font_size = 32
	label.pixel_size = 0.008
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.outline_size = 8
	label.outline_modulate = Color(0, 0, 0, 0.85)
	label.position = Vector3(0, float(LABEL_Y.get(kind, 1.6)), 0)
	label.modulate = Color("fff6e8")
	add_child(label)


func _build_archer() -> void:
	var packed = load("res://assets/archer/archer_rigged.glb")
	if packed == null:
		push_warning("Archer model missing. Using a block stand-in.")
		_build_archer_block()
		return
	var model: Node = packed.instantiate()
	model.name = "ArcherModel"
	# The exported face looks along +Z. Godot's forward is -Z, so turn the model around.
	model.rotation.y = PI
	model.scale = Vector3.ONE * 0.78
	mesh_root.add_child(model)
	anim = _find_anim(model)
	_tune_anims()
	play_loop("idle")


func _build_archer_block() -> void:
	mesh_root.add_child(Props.cylinder(0.28, 1.5, Color("c48a62"), Vector3(0, 0.9, 0)))
	mesh_root.add_child(Props.sphere(0.22, Color("c48a62"), Vector3(0, 1.75, 0)))
	mesh_root.add_child(Props.box(Vector3(0.08, 1.15, 0.08), Color("7a4a22"), Vector3(0.28, 0.95, -0.05)))


func _build_panda() -> void:
	# Placeholder. Built from primitives on purpose.
	# The rigged panda in blender_fight is the stock Panda3D sample and is not used.
	var white := Color("f4f1ea")
	var black := Color("1b1c1f")
	mesh_root.add_child(Props.capsule_z(0.38, 1.45, white, Vector3(0, 0.58, 0.05)))
	mesh_root.add_child(Props.sphere(0.34, white, Vector3(0, 0.74, -0.78)))
	mesh_root.add_child(Props.sphere(0.14, black, Vector3(-0.22, 1.05, -0.82)))
	mesh_root.add_child(Props.sphere(0.14, black, Vector3(0.22, 1.05, -0.82)))
	mesh_root.add_child(Props.sphere(0.1, black, Vector3(-0.12, 0.76, -1.02)))
	mesh_root.add_child(Props.sphere(0.1, black, Vector3(0.12, 0.76, -1.02)))
	mesh_root.add_child(Props.sphere(0.035, white, Vector3(-0.12, 0.78, -1.1)))
	mesh_root.add_child(Props.sphere(0.035, white, Vector3(0.12, 0.78, -1.1)))
	mesh_root.add_child(Props.sphere(0.05, Color("c47a8a"), Vector3(0, 0.66, -1.08)))
	for x in [-0.28, 0.28]:
		for z in [-0.42, 0.46]:
			mesh_root.add_child(Props.cylinder(0.1, 0.36, black, Vector3(x, 0.18, z)))
	mesh_root.add_child(Props.sphere(0.12, white, Vector3(0, 0.62, 0.78)))
	mesh_root.add_child(Props.cylinder(0.2, 0.12, Color("e0b15a"), Vector3(0, 0.8, -0.5)))


func _build_mite() -> void:
	mesh_root.add_child(Props.sphere(0.38, Color("d85a28"), Vector3(0, 0.42, 0), 0.35))
	mesh_root.add_child(Props.sphere(0.12, Color("2a2420"), Vector3(0.18, 0.58, -0.08)))
	mesh_root.add_child(Props.sphere(0.1, Color("ffb15a"), Vector3(-0.12, 0.22, 0.16), 0.7))


func _build_lurker() -> void:
	mesh_root.add_child(Props.cylinder(0.22, 1.15, Color("3d6a38"), Vector3(0, 0.7, 0)))
	mesh_root.add_child(Props.sphere(0.26, Color("1e3a24"), Vector3(0, 1.4, 0)))
	mesh_root.add_child(Props.box(Vector3(0.95, 0.08, 0.08), Color("6b4a2a"), Vector3(0, 0.95, 0)))
	mesh_root.add_child(Props.sphere(0.07, Color("d8e2c8"), Vector3(-0.08, 1.46, -0.2)))
	mesh_root.add_child(Props.sphere(0.07, Color("d8e2c8"), Vector3(0.08, 1.46, -0.2)))


func _build_boss() -> void:
	var stone := Color("8a867e")
	var moss := Color("4f7a45")
	mesh_root.add_child(Props.sphere(0.58, stone, Vector3(0, 0.72, 0)))
	mesh_root.add_child(Props.sphere(0.44, stone, Vector3(0, 1.42, 0)))
	mesh_root.add_child(Props.sphere(0.28, moss, Vector3(0.22, 1.15, 0.12)))
	mesh_root.add_child(Props.sphere(0.22, moss, Vector3(-0.28, 0.62, -0.08)))
	mesh_root.add_child(Props.cylinder(0.18, 0.42, Color("c4a574"), Vector3(0, 1.2, 0.48)))
	mesh_root.add_child(Props.sphere(0.1, Color("6b4423"), Vector3(0, 1.46, 0.48)))
	mesh_root.add_child(Props.sphere(0.06, Color("f2e2a8"), Vector3(-0.12, 1.5, -0.36), 0.5))
	mesh_root.add_child(Props.sphere(0.06, Color("f2e2a8"), Vector3(0.12, 1.5, -0.36), 0.5))


func _build_lina() -> void:
	mesh_root.add_child(Props.cylinder(0.32, 1.25, Color("2f6d62"), Vector3(0, 0.75, 0)))
	mesh_root.add_child(Props.sphere(0.22, Color("e2b394"), Vector3(0, 1.52, 0)))
	mesh_root.add_child(Props.sphere(0.24, Color("d9dde2"), Vector3(0, 1.7, 0.02)))
	mesh_root.add_child(Props.box(Vector3(0.42, 0.16, 0.28), Color("c4552a"), Vector3(0.42, 0.7, 0.05)))


func _find_anim(node: Node):
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var found = _find_anim(child)
		if found:
			return found
	return null


func _tune_anims() -> void:
	if anim == null:
		return
	for lib_name in anim.get_animation_library_list():
		var lib := anim.get_animation_library(lib_name)
		var names := lib.get_animation_list()
		for anim_name in names:
			var copy: Animation = lib.get_animation(anim_name).duplicate()
			if str(anim_name) in ["idle", "walk"]:
				copy.loop_mode = Animation.LOOP_LINEAR
			else:
				copy.loop_mode = Animation.LOOP_NONE
			lib.remove_animation(anim_name)
			lib.add_animation(anim_name, copy)


func anim_names() -> PackedStringArray:
	if anim == null:
		return PackedStringArray()
	return anim.get_animation_list()


func play_loop(anim_name: String) -> void:
	if anim == null or not anim.has_animation(anim_name):
		return
	if anim.current_animation == anim_name and anim.is_playing():
		return
	anim.speed_scale = 1.25 if anim_name == "walk" else 1.0
	anim.play(anim_name)


func play_once(anim_name: String) -> void:
	if anim == null or not anim.has_animation(anim_name):
		return
	anim.speed_scale = 1.0
	anim.play(anim_name)
	if not anim.animation_finished.is_connected(_back_to_idle):
		anim.animation_finished.connect(_back_to_idle)


func _back_to_idle(_anim_name: StringName = &"") -> void:
	if fallen:
		return
	play_loop("walk" if moving else "idle")


func set_moving(value: bool) -> void:
	moving = value
	if fallen:
		return
	play_loop("walk" if value else "idle")


func face_dir(dir: Vector3) -> void:
	dir.y = 0.0
	if dir.length_squared() < 0.0004:
		return
	look_at(global_position + dir, Vector3.UP)


func spin() -> void:
	spin_t = 0.38


func hop() -> void:
	hop_left = 0.28


func flash() -> void:
	flash_t = 0.16


func bow() -> void:
	bow_t = 1.2


func fall() -> void:
	fallen = true
	if mesh_root:
		mesh_root.rotation.x = 1.15
		mesh_root.position.y = 0.05


func revive() -> void:
	fallen = false
	if mesh_root:
		mesh_root.rotation.x = 0.0
		mesh_root.position.y = 0.0


func _process(delta: float) -> void:
	if mesh_root == null or fallen:
		return
	bob += delta * (7.5 if moving else 1.8)
	var bob_y := sin(bob) * (0.05 if moving else 0.015)
	if hop_left > 0.0:
		hop_left -= delta
		var k := clampf(1.0 - hop_left / 0.28, 0.0, 1.0)
		bob_y += sin(k * PI) * 0.42
	if bow_t > 0.0:
		bow_t -= delta
		var bend := 1.0 - absf(bow_t - 0.6) / 0.6
		mesh_root.rotation.x = 0.45 * clampf(bend, 0.0, 1.0)
	elif spin_t <= 0.0:
		mesh_root.rotation.x = 0.0
	mesh_root.position.y = bob_y
	if spin_t > 0.0:
		spin_t -= delta
		mesh_root.rotation.y += delta * TAU / 0.38
		if spin_t <= 0.0:
			mesh_root.rotation.y = 0.0
	if flash_t > 0.0:
		flash_t -= delta
		mesh_root.scale = Vector3.ONE * 1.08
	else:
		mesh_root.scale = Vector3.ONE
