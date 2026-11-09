extends Node3D

var fill_mat: StandardMaterial3D
var ring_mat: StandardMaterial3D


func setup(color: Color) -> void:
	var fill := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 1.0
	cyl.bottom_radius = 1.0
	cyl.height = 0.045
	cyl.radial_segments = 48
	fill.mesh = cyl
	fill_mat = StandardMaterial3D.new()
	fill_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	fill_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fill_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	fill_mat.albedo_color = color
	fill.material_override = fill_mat
	fill.position.y = 0.05
	fill.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(fill)

	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.9
	torus.outer_radius = 1.0
	torus.rings = 8
	torus.ring_segments = 48
	ring.mesh = torus
	ring_mat = StandardMaterial3D.new()
	ring_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	ring_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	ring_mat.albedo_color = Color(color.r, color.g, color.b, minf(1.0, color.a + 0.45))
	ring.material_override = ring_mat
	ring.position.y = 0.08
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ring)
	visible = false


func set_color(color: Color) -> void:
	if fill_mat:
		fill_mat.albedo_color = color
	if ring_mat:
		ring_mat.albedo_color = Color(color.r, color.g, color.b, minf(1.0, color.a + 0.45))


func show_at(p: Vector3, radius: float) -> void:
	visible = radius > 0.05
	position = Vector3(p.x, 0.0, p.z)
	var r := maxf(radius, 0.05)
	scale = Vector3(r, 1.0, r)


func dismiss() -> void:
	visible = false
