extends RefCounted

## One body on the battle field.
## Heroes do not keep their own life. The pair shares PartyState.hp.

var id := ""
var kind := ""
var side := ""
var display := ""
var agility := 8.0
var gauge := 0.0
var move_radius := 3.0
var pos := Vector3.ZERO
var hp := 0
var hp_max := 0
var defending := false
var guard_mult := 1.0
var slow_turns := 0
var root_scale := 1.0
var attack_index := 0
var visual = null
