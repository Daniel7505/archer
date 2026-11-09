extends CanvasLayer

signal choice(id: String)

var life_label: Label
var life_bar: ProgressBar
var life_fill: StyleBoxFlat
var panda_label: Label
var panda_bar: ProgressBar
var panda_fill: StyleBoxFlat
var spirit_label: Label
var spirit_bar: ProgressBar
var element_box: VBoxContainer
var element_bits := {}
var point_label: Label
var region_label: Label
var prompt: Label
var choice_bar: HBoxContainer
var row_box: VBoxContainer
var rows := {}
var dialogue: PanelContainer
var dialogue_label: Label
var toast_label: Label
var toast_time := 0.0
var toast_queue: Array = []
var panel: PanelContainer
var panel_title: Label
var panel_body: RichTextLabel
var panel_choices: HBoxContainer
var fade: ColorRect
var fade_target := 0.0
var battle_panel: PanelContainer


func _ready() -> void:
	layer = 10
	_build()


func _build() -> void:
	fade = ColorRect.new()
	fade.color = Color(0, 0, 0, 0)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade.set_anchors_preset(Control.PRESET_FULL_RECT)

	var left := PanelContainer.new()
	left.offset_left = 16
	left.offset_top = 16
	left.offset_right = 390
	left.offset_bottom = 400
	left.add_theme_stylebox_override("panel", _panel_style())
	add_child(left)
	var left_box := VBoxContainer.new()
	left_box.add_theme_constant_override("separation", 6)
	left.add_child(left_box)
	region_label = _label("Bramblewick Camp", 18)
	left_box.add_child(region_label)
	life_label = _label("Archer 64/64", 16)
	left_box.add_child(life_label)
	var life_ui := _bar(Color("7dbe6a"))
	life_bar = life_ui.bar
	life_fill = life_ui.fill
	left_box.add_child(life_bar)
	panda_label = _label("Panda 64/64", 16)
	left_box.add_child(panda_label)
	var panda_ui := _bar(Color("f0e6c8"))
	panda_bar = panda_ui.bar
	panda_fill = panda_ui.fill
	left_box.add_child(panda_bar)
	spirit_label = _label("Spirit 28/28", 16)
	left_box.add_child(spirit_label)
	spirit_bar = _bar(Color("6aa4d6")).bar
	left_box.add_child(spirit_bar)
	element_box = VBoxContainer.new()
	element_box.add_theme_constant_override("separation", 4)
	left_box.add_child(element_box)
	for id in ["earth", "water", "fire", "wind"]:
		element_bits[id] = _add_element_row(id)
	point_label = _label("", 15)
	point_label.modulate = Color("f0d48a")
	left_box.add_child(point_label)

	battle_panel = PanelContainer.new()
	battle_panel.anchor_left = 1
	battle_panel.anchor_right = 1
	battle_panel.offset_left = -300
	battle_panel.offset_right = -16
	battle_panel.offset_top = 16
	battle_panel.offset_bottom = 430
	battle_panel.add_theme_stylebox_override("panel", _panel_style())
	battle_panel.visible = false
	add_child(battle_panel)
	row_box = VBoxContainer.new()
	row_box.add_theme_constant_override("separation", 6)
	battle_panel.add_child(row_box)

	var prompt_panel := PanelContainer.new()
	prompt_panel.anchor_left = 0.16
	prompt_panel.anchor_right = 0.84
	prompt_panel.anchor_top = 1.0
	prompt_panel.anchor_bottom = 1.0
	prompt_panel.offset_top = -168
	prompt_panel.offset_bottom = -96
	prompt_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	prompt_panel.add_theme_stylebox_override("panel", _panel_style())
	add_child(prompt_panel)
	prompt = _label("", 18)
	prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	prompt.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	prompt.mouse_filter = Control.MOUSE_FILTER_IGNORE
	prompt_panel.add_child(prompt)

	choice_bar = HBoxContainer.new()
	choice_bar.alignment = BoxContainer.ALIGNMENT_CENTER
	choice_bar.add_theme_constant_override("separation", 10)
	choice_bar.anchor_left = 0.05
	choice_bar.anchor_right = 0.95
	choice_bar.anchor_top = 1
	choice_bar.anchor_bottom = 1
	choice_bar.offset_top = -88
	choice_bar.offset_bottom = -16
	add_child(choice_bar)

	dialogue = PanelContainer.new()
	dialogue.visible = false
	dialogue.anchor_left = 0.08
	dialogue.anchor_right = 0.92
	dialogue.anchor_top = 1
	dialogue.anchor_bottom = 1
	dialogue.offset_top = -210
	dialogue.offset_bottom = -28
	dialogue.add_theme_stylebox_override("panel", _panel_style())
	add_child(dialogue)
	var dbox := VBoxContainer.new()
	dialogue.add_child(dbox)
	dialogue_label = _label("", 20)
	dialogue_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	dbox.add_child(dialogue_label)
	var hint := _label("Space to continue", 14)
	hint.modulate = Color(1, 1, 1, 0.7)
	dbox.add_child(hint)

	panel = PanelContainer.new()
	panel.visible = false
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.offset_left = -380
	panel.offset_top = -280
	panel.offset_right = 380
	panel.offset_bottom = 280
	panel.add_theme_stylebox_override("panel", _panel_style())
	add_child(panel)
	var pbox := VBoxContainer.new()
	pbox.add_theme_constant_override("separation", 10)
	panel.add_child(pbox)
	panel_title = _label("", 32)
	panel_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	pbox.add_child(panel_title)
	panel_body = RichTextLabel.new()
	panel_body.bbcode_enabled = false
	panel_body.scroll_active = true
	panel_body.custom_minimum_size = Vector2(680, 300)
	panel_body.add_theme_font_size_override("normal_font_size", 18)
	panel_body.add_theme_color_override("default_color", Color("f6efe2"))
	pbox.add_child(panel_body)
	panel_choices = HBoxContainer.new()
	panel_choices.alignment = BoxContainer.ALIGNMENT_CENTER
	panel_choices.add_theme_constant_override("separation", 8)
	pbox.add_child(panel_choices)

	toast_label = _label("", 20)
	toast_label.visible = false
	toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	toast_label.anchor_left = 0.25
	toast_label.anchor_right = 0.75
	toast_label.offset_top = 78
	toast_label.offset_bottom = 120
	toast_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(toast_label)
	add_child(fade)


func _add_element_row(id: String) -> Dictionary:
	var row := HBoxContainer.new()
	var name := _label(id.capitalize(), 15)
	name.custom_minimum_size = Vector2(70, 0)
	name.modulate = _element_color(id)
	row.add_child(name)
	var bar: ProgressBar = _bar(_element_color(id)).bar
	bar.custom_minimum_size = Vector2(160, 12)
	row.add_child(bar)
	var detail := _label("1", 15)
	detail.custom_minimum_size = Vector2(110, 0)
	row.add_child(detail)
	element_box.add_child(row)
	return {"bar": bar, "detail": detail}


func _process(delta: float) -> void:
	var alpha := fade.color.a
	fade.color.a = lerpf(alpha, fade_target, 1.0 - exp(-8.0 * delta))
	if toast_time > 0.0:
		toast_time -= delta
		if toast_time <= 0.0:
			_next_toast()


func set_region(text: String) -> void:
	region_label.text = text


func set_prompt(text: String) -> void:
	prompt.text = text


func set_vitals(party) -> void:
	life_label.text = "Archer  %d/%d    level %d%s" % [party.archer_hp, party.archer_hp_max, party.level, "  down" if party.archer_hp <= 0 else ""]
	life_bar.max_value = party.archer_hp_max
	life_bar.value = party.archer_hp
	if life_fill:
		life_fill.bg_color = Color("c4552a") if party.archer_hp * 3 <= party.archer_hp_max else Color("7dbe6a")
	panda_label.text = "Panda  %d/%d%s" % [party.panda_hp, party.panda_hp_max, "  down" if party.panda_hp <= 0 else ""]
	panda_bar.max_value = party.panda_hp_max
	panda_bar.value = party.panda_hp
	if panda_fill:
		panda_fill.bg_color = Color("c4552a") if party.panda_hp * 3 <= party.panda_hp_max else Color("f0e6c8")
	spirit_label.text = "Shared spirit  %d/%d" % [party.mp, party.mp_max]
	spirit_bar.max_value = maxi(1, party.mp_max)
	spirit_bar.value = party.mp
	var rules = preload("res://scripts/rules.gd")
	for id in ["earth", "water", "fire", "wind"]:
		var e: Dictionary = party.elements[id]
		var need: int = rules.xp_to_advance(int(e.level))
		var bits: Dictionary = element_bits[id]
		bits.detail.text = "lv %d   %d/%d" % [int(e.level), int(e.xp), need]
		bits.bar.max_value = need
		bits.bar.value = int(e.xp)
	if party.pending_points > 0:
		point_label.text = "%d element point%s to place  (B)" % [party.pending_points, "" if party.pending_points == 1 else "s"]
	else:
		point_label.text = "Two lives. One shared spirit."


func set_battle_mode(on: bool) -> void:
	battle_panel.visible = on
	if not on:
		_clear_rows()


func set_rows(entries: Array) -> void:
	var seen := {}
	for entry in entries:
		var id := str(entry.id)
		seen[id] = true
		if not rows.has(id):
			rows[id] = _make_row()
		var ui: Dictionary = rows[id]
		ui.name.text = entry.display
		ui.name.modulate = Color("f0d48a") if entry.active else Color("f6efe2")
		if entry.side == "enemy":
			ui.hp.visible = true
			ui.hp.max_value = maxi(1, int(entry.hp_max))
			ui.hp.value = int(entry.hp)
		else:
			ui.hp.visible = false
		ui.gauge.max_value = 100
		ui.gauge.value = float(entry.gauge)
	var stale: Array = []
	for id in rows.keys():
		if not seen.has(id):
			stale.append(id)
	for id in stale:
		rows[id].root.queue_free()
		rows.erase(id)


func _make_row() -> Dictionary:
	var box := VBoxContainer.new()
	var name := _label("", 15)
	box.add_child(name)
	var hp: ProgressBar = _bar(Color("d07a62")).bar
	hp.custom_minimum_size = Vector2(220, 10)
	box.add_child(hp)
	var gauge: ProgressBar = _bar(Color("e6d39a")).bar
	gauge.custom_minimum_size = Vector2(220, 10)
	box.add_child(gauge)
	row_box.add_child(box)
	return {"root": box, "name": name, "hp": hp, "gauge": gauge}


func _clear_rows() -> void:
	for id in rows.keys():
		rows[id].root.queue_free()
	rows.clear()


func show_choices(entries: Array) -> void:
	_clear_choice_bar(choice_bar)
	for entry in entries:
		choice_bar.add_child(_choice_button(entry))


func clear_choices() -> void:
	_clear_choice_bar(choice_bar)


func show_dialogue(text: String) -> void:
	dialogue.visible = true
	dialogue_label.text = text


func hide_dialogue() -> void:
	dialogue.visible = false


func show_text_panel(title: String, body: String, entries: Array) -> void:
	panel.visible = true
	panel_title.text = title
	panel_body.text = body
	_clear_choice_bar(panel_choices)
	for entry in entries:
		panel_choices.add_child(_choice_button(entry))


func hide_text_panel() -> void:
	panel.visible = false
	_clear_choice_bar(panel_choices)


func toast(text: String) -> void:
	if text == "":
		return
	if not toast_label.visible:
		toast_label.text = text
		toast_label.visible = true
		toast_time = 2.4
	else:
		toast_queue.append(text)


func _next_toast() -> void:
	if toast_queue.is_empty():
		toast_label.visible = false
		toast_label.text = ""
		return
	toast_label.text = str(toast_queue.pop_front())
	toast_label.visible = true
	toast_time = 2.4


func fade_to(alpha: float) -> void:
	fade_target = alpha


func _choice_button(entry: Dictionary) -> Button:
	var button := Button.new()
	button.text = str(entry.label)
	button.disabled = bool(entry.get("disabled", false))
	button.focus_mode = Control.FOCUS_NONE
	button.custom_minimum_size = Vector2(150, 46)
	button.add_theme_font_size_override("font_size", 16)
	button.pressed.connect(_emit_choice.bind(str(entry.id)))
	return button


func _emit_choice(id: String) -> void:
	choice.emit(id)


func _clear_choice_bar(bar: HBoxContainer) -> void:
	for child in bar.get_children():
		child.queue_free()


func _label(text: String, size: int) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", Color("f6efe2"))
	return label


func _bar(color: Color) -> Dictionary:
	var bar := ProgressBar.new()
	bar.max_value = 100
	bar.value = 0
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(220, 14)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.45)
	bg.set_corner_radius_all(4)
	var fg := StyleBoxFlat.new()
	fg.bg_color = color
	fg.set_corner_radius_all(4)
	bar.add_theme_stylebox_override("background", bg)
	bar.add_theme_stylebox_override("fill", fg)
	return {"bar": bar, "fill": fg}


func _panel_style() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.10, 0.08, 0.07, 0.82)
	style.border_color = Color(0.85, 0.7, 0.42, 0.85)
	style.set_border_width_all(2)
	style.set_corner_radius_all(12)
	style.set_content_margin_all(12)
	return style


func _element_color(id: String) -> Color:
	match id:
		"earth":
			return Color("c4a36a")
		"water":
			return Color("8ec4e0")
		"fire":
			return Color("f0a070")
		"wind":
			return Color("8ed9bf")
	return Color.WHITE
