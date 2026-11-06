# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"pinguim 2d" is a 2D platformer built with **Godot 4.6** using **GDScript**. The player controls a penguin character across seasonal levels (Grassland, Autumn Forest, Ice, Tropics), with a skeleton enemy. Rendering is configured for mobile with a 400x208 viewport using `canvas_items` stretch mode and nearest-neighbor texture filtering (pixel art).

## Build & Run Commands

```bash
# Run the game (requires Godot 4.6 in PATH)
godot --path .

# Export for web
godot --headless --export-all
```

The web export outputs to `dist-web/` with the entry point at `dist-web/dist-web.html`.

## Architecture

### Scene Structure

Levels are standalone `.tscn` files in `scene/` that instantiate reusable entity scenes from `scene/entities/`:

- **Level scenes** (`game.tscn`, `forest.tscn`, `ice.tscn`, `tropic.tscn`): Each contains a Player instance, TileMapLayers (terrain + decoration), and optionally a Camera2D and ParallaxBackground. Progression via `next_level` on each `level_end`: forest → ice → tropic → forest (loops). `game.tscn` has no incoming link here. The main scene in `project.godot` is currently `tropic.tscn` (uid `bux8wouug3i0e`); whether it should be `game.tscn` is unconfirmed (ask the repo owner).
- **Entity scenes** (`scene/entities/`: `player.tscn`, `skeleton.tscn`, `câmera.tscn`, `level_end.tscn`), plus `spining_bone.tscn` and `mobileControls.tscn` in `scene/`: self-contained reusable components with attached scripts.

### Scripts

- **`scripts/player.gd`** — Player controller using a finite state machine with 7 states (`idle`, `walk`, `jump`, `fall`, `duck`, `slide`, `dead`). Implements double jump (`@export max_jump_count`, default 2), duck/slide with collision shape modification, and acceleration-based movement (`@export max_speed=100`, `acerelacao`, `desacerelacao`, `desacerelacao_slide`). Constant: `JUMP_VELOCITY=-300`. Has a `ReloadTimer` used after death.
- **`scripts/skeleton.gd`** — Enemy with states `walk` and `dead`; `SPEED=30`.
- **`scripts/spining_bone.gd`** — Spinning bone hazard.
- **`scripts/level_end.gd`** — Area2D trigger that loads `res://scene/{next_level}.tscn` on player body entry. The `next_level` property is exported per-instance.
- **`camera.gd`** (root dir) — Camera2D that follows the player node found via the `"player"` group.

### Collision Layers

| Layer | Name      | Usage                           |
|-------|-----------|---------------------------------|
| 1     | terrain   | Ground, platforms               |
| 2     | player    | Player character                |
| 3     | enemies   | Reserved (skeleton uses layer 0)|
| 4     | level_end | Level transition trigger zones  |

Player mask: terrain (1) + level_end (4). Level end mask: player (2).

### Input Map

| Action | Keys                      |
|--------|---------------------------|
| left   | A, Left Arrow             |
| right  | D, Right Arrow            |
| jump   | W, Space, Up Arrow        |
| duck   | S, Down Arrow             |

### Assets

- **Sprites** in `sprites/1 - Penguin/` — 16x16 pixel art character poses
- **Tilesets** in `tiles/` — `terran.tres` (terrain with physics for 3 seasons), `decoração.tres` (decorations with animations)
- **Seasonal tilesets** in `sprites/Seasonal Tilesets/` — Grassland, Autumn Forest, Tropics variants

### Physics

Custom gravity: `1352.36` (set in project.godot). Jolt Physics enabled for 3D engine (2D uses default).

### Groups

- `player` — Player node instances (used by camera to find follow target)
- `inimigos` — Reserved for enemy entities
