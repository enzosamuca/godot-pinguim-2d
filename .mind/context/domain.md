---
type: glossary
title: Vocabulário do Domínio — godot-pinguim-2d
description: Glossário de domínio do jogo pinguim 2d — estados, entidades, cenas, camadas e conceitos de gameplay.
resource: godot-pinguim-2d
tags: [glossary, domain, vocabulary, pinguim]
timestamp: 2026-11-05T00:00:00Z
---

# Vocabulário do Domínio — godot-pinguim-2d

> Glossário local do repositório.

| Termo | Definição | Implementado em |
|---|---|---|
| **Pinguim (player)** | Personagem controlado pelo jogador; pertence ao grupo `player` | `scripts/player.gd`, `scene/entities/player.tscn` |
| **playerstate** | Enum de estados do player: idle, walk, jump, fall, duck, slide, dead | `player.gd` |
| **Idle** | Parado no chão; transita para walk/jump/duck | `idle_state` |
| **Walk** | Andando; vira slide se agachar, fall se sair do chão | `walk_state` |
| **Jump** | Subindo após aplicar `JUMP_VELOCITY` (-300) | `go_to_jump_state`, `jump_state` |
| **Fall** | Caindo (`velocity.y > 0`); zera `jump_count` ao tocar o chão | `fall_state` |
| **Pulo duplo** | Até `max_jump_count` (2) pulos antes de tocar o chão | `jump_count`, `max_jump_count` |
| **Duck (agachar)** | Estado parado agachado, com colisor pequeno | `duck_state`, `set_small_colider` |
| **Slide (deslizar)** | Agachar enquanto anda: desacelera com `desacerelacao_slide` | `slide_state` |
| **Dead** | Morte do player: zera velocidade e inicia `ReloadTimer` (2 s) | `go_to_dead_state` |
| **ReloadTimer** | Timer one-shot que recarrega a fase após a morte | `_on_reload_timer_timeout` |
| **Colisor pequeno/grande** | Cápsula redimensionada ao agachar/levantar (altura 25 vs 35) | `set_small_colider`, `set_large_colider` |
| **Aceleração** | `acerelacao`/`desacerelacao`: usados em `move_toward` no eixo X | `move()` |
| **hitbox** | Area2D do player e do esqueleto usada no combate | `_on_hitbox_area_entered` |
| **Stomp (pisão)** | Cair (`velocity.y > 0`) sobre o inimigo o derrota e faz o player pular | `_on_hitbox_area_entered` |
| **Skeleton (esqueleto)** | Inimigo patrulheiro de velocidade 30 | `scripts/skeleton.gd` |
| **skeletonstate** | Enum do esqueleto: walk, dead | `skeleton.gd` |
| **WallDetector / GroundDetector** | RayCast2D que inverte a direção em parede ou borda | `skeleton.gd` |
| **take_demage** | Método (grafia original) chamado no inimigo atingido pelo pisão | `skeleton.gd` |
| **level_end** | Area2D que, ao ser tocada, troca para a próxima fase | `scripts/level_end.gd` |
| **next_level** | Export por instância com o nome da cena seguinte | `level_end.gd` |
| **Fases** | `game`, `forest`, `ice`, `tropic` | `scene/*.tscn` |
| **Câmera** | Camera2D que segue o nó do grupo `player` | `camera.gd`, `scene/entities/câmera.tscn` |
| **Grupos** | `player` e `inimigos` (declarados em project.godot) | `project.godot` |
| **Camadas de física** | 1 terrain, 2 player, 3 enemies, 4 level_end | `project.godot` |
| **mobileControls** | CanvasLayer com TouchScreenButton para left/right/jump/duck | `scene/mobileControls.tscn` |
| **TileMapLayer** | Camadas de terreno e decoração das fases | `tiles/terrain.tres`, `tiles/decoration/` |
| **Export Web** | Preset "Web" que gera `dist-web.html` | `export_presets.cfg` |
