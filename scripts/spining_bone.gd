extends Area2D


var speed = 1
var direction = 1


# Called every frame. 'delta' is the elapsed time since the previous frame.
func _process(delta: float) -> void:
	position.x += speed  * delta
