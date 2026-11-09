extends RefCounted

## Player 2 is the first gamepad Godot sees (device 0).
## A PlayStation DualShock or DualSense, or an XInput pad, both show up here.
## latched becomes true the first time that stick actually moves, so a pad that
## is merely plugged in does not steal the single-player follow camera.

static var latched := false


static func connected() -> bool:
	return Input.get_connected_joypads().size() > 0


static func left_stick() -> Vector2:
	return _stick(JOY_AXIS_LEFT_X, JOY_AXIS_LEFT_Y, true)


static func right_stick() -> Vector2:
	return _stick(JOY_AXIS_RIGHT_X, JOY_AXIS_RIGHT_Y, true)


static func panda_uses_pad() -> bool:
	return connected() and latched


static func _stick(axis_x: JoyAxis, axis_y: JoyAxis, mark: bool) -> Vector2:
	if not connected():
		return Vector2.ZERO
	var raw := Vector2(Input.get_joy_axis(0, axis_x), Input.get_joy_axis(0, axis_y))
	if raw.length() < 0.28:
		return Vector2.ZERO
	if mark:
		latched = true
	return raw.normalized()
