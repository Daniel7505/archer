extends RefCounted

static func material(color: Color, rough: float = 0.9, emit: float = 0.0) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = rough
	if emit > 0.0:
		mat.emission_enabled = true
		mat.emission = color
		mat.emission_energy_multiplier = emit
	return mat


static func mesh_node(mesh: Mesh, mat: Material, pos: Vector3) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.material_override = mat
	node.position = pos
	return node


static func cylinder(radius: float, height: float, color: Color, pos: Vector3, emit: float = 0.0) -> MeshInstance3D:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	return mesh_node(mesh, material(color, 0.9, emit), pos)


static func sphere(radius: float, color: Color, pos: Vector3, emit: float = 0.0) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	return mesh_node(mesh, material(color, 0.82, emit), pos)


static func box(size: Vector3, color: Color, pos: Vector3) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	return mesh_node(mesh, material(color), pos)


static func capsule_z(radius: float, height: float, color: Color, pos: Vector3) -> MeshInstance3D:
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = maxf(height, radius * 2.0 + 0.05)
	var node := mesh_node(mesh, material(color), pos)
	node.rotation.x = PI / 2.0
	return node
