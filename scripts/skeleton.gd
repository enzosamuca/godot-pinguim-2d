extends CharacterBody2D

enum skeletonstate {
	walk,
	dead
}

@onready var anim: AnimatedSprite2D = $AnimatedSprite2D
@onready var hitbox: Area2D = $hitbox
@onready var wall_detector: RayCast2D = $WallDetector
@onready var ground_detector: RayCast2D = $GroundDetector

const SPEED = 30.0
const JUMP_VELOCITY = -400.0

var status: skeletonstate
var direction = 1

func _ready() -> void:
	go_to_walk_state()

func _physics_process(delta: float) -> void:
	# Add the gravity.
	if not is_on_floor():
		velocity += get_gravity() * delta
		
	match status:
		skeletonstate.walk:
			walk_state(delta)
		skeletonstate.dead:
			dead_state(delta)

	move_and_slide()

func go_to_walk_state():
	status = skeletonstate.walk
	anim.play("walk")

func go_to_dead_state():
	status = skeletonstate.dead
	anim.play("dead")
	hitbox.process_mode = Node.PROCESS_MODE_DISABLED
	velocity = Vector2.ZERO

func walk_state(delta):
	velocity.x = direction * SPEED
	
	if wall_detector.is_colliding():
		scale.x *= -1
		direction *= -1
		
	if not ground_detector.is_colliding():
		scale.x *= -1
		direction *= -1

func dead_state(delta):
	pass

func take_demage():
	go_to_dead_state()
