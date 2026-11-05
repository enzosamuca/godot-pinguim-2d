---
type: reference
title: Lógica de Negócio — godot-pinguim-2d
description: Mecânica interna do jogo pinguim 2d — máquina de estados do player, patrulha do esqueleto, combate e troca de fases.
resource: godot-pinguim-2d
tags: [business-logic, implementation, call-flow]
timestamp: 2026-11-05T00:00:00Z
---

# Lógica de Negócio — godot-pinguim-2d

> Última atualização: 2026-11
> Origem: leitura de `scripts/*.gd`, `camera.gd` e cenas. Nomes baseados em evidência.
<!-- Needs Human Confirmation: verify step ordering with owning team -->

## Pontos de Entrada

| Superfície | Caminho / Gatilho | Classe / função handler | Método / ação de entrada |
|---|---|---|---|
| Loop de física | `_physics_process` a cada frame | `player.gd` | `_physics_process` |
| Loop de física | `_physics_process` a cada frame | `skeleton.gd` | `_physics_process` |
| Sinal Area2D | `hitbox.area_entered` do player | `player.gd` | `_on_hitbox_area_entered` |
| Sinal Area2D | `body_entered` do level_end | `level_end.gd` | `_on_body_entered` |
| Sinal Timer | `ReloadTimer.timeout` | `player.gd` | `_on_reload_timer_timeout` |
| Loop de render | `_process` | `camera.gd` | `_process` |

---

## Passo a Passo: Controle do Player

### Passo 1 — Física (`player.gd::_physics_process`)

1. Se fora do chão, soma `get_gravity() * delta` à velocidade.
2. Despacha por `match status` para `idle_state`, `walk_state`, `jump_state`, `fall_state`, `duck_state`, `slide_state` ou `dead_state`.
3. Chama `move_and_slide()`.

> **Acesso a dados:** nenhum — estado em memória do nó.

### Passo 2 — Movimento horizontal (`move` / `update_direction`)

1. `Input.get_axis("left","right")` define `direction` e inverte o sprite (`flip_h`).
2. `move_toward` acelera até `direction * max_speed` ou desacelera a zero.

> **Acesso a dados:** Input Map (`project.godot`).

### Passo 3 — Transições de estado

1. idle → walk (direction≠0), jump (`jump`), duck (`duck` pressionado).
2. walk → idle, jump, slide (`duck`), fall (sai do chão, `jump_count += 1`).
3. jump/fall → novo jump se `jump_count < max_jump_count`; jump → fall quando `velocity.y > 0`; fall → idle/walk ao tocar o chão (zera `jump_count`).
4. duck → idle ao soltar `duck`; slide → walk ao soltar ou duck quando `velocity.x == 0`.

> **Acesso a dados:** `AnimatedSprite2D` (`anim.play`), `CollisionShape2D` (colisor pequeno/grande).

---

## Passo a Passo: Combate Player × Esqueleto

### Passo 1 — Contato (`player.gd::_on_hitbox_area_entered`)

1. Se `velocity.y > 0`: chama `area.get_parent().take_demage()` e `go_to_jump_state()`.
2. Caso contrário e `status != dead`: `go_to_dead_state()`.

> **Acesso a dados:** nenhum.

### Passo 2 — Morte do inimigo (`skeleton.gd`)

1. `take_demage()` → `go_to_dead_state()`: toca `dead`, desativa o hitbox (`PROCESS_MODE_DISABLED`), zera velocidade.

> **Acesso a dados:** nenhum.

### Passo 3 — Morte do player

1. `go_to_dead_state()` zera velocidade e inicia `ReloadTimer` (2 s, one-shot).
2. `_on_reload_timer_timeout()` → `get_tree().reload_current_scene()`.

> **Acesso a dados:** recarrega a cena atual (estado reiniciado).

---

## Passo a Passo: Patrulha do Esqueleto

### Passo 1 — Estado walk (`skeleton.gd::walk_state`)

1. `velocity.x = direction * SPEED` (30).
2. Se `wall_detector.is_colliding()`: inverte `scale.x` e `direction`.
3. Se `not ground_detector.is_colliding()`: inverte `scale.x` e `direction`.

> **Acesso a dados:** RayCast2D `WallDetector` e `GroundDetector`.

---

## Passo a Passo: Progressão de Fases

### Passo 1 — Gatilho (`level_end.gd::_on_body_entered`)

1. Chama `load_next_scene` via `call_deferred`.

> **Acesso a dados:** nenhum.

### Passo 2 — Troca de cena

1. `get_tree().change_scene_to_file("res://scene/" + next_level + ".tscn")`.

> **Acesso a dados:** sistema de arquivos `res://scene/`.

### Passo 3 — Ordem configurada nas cenas

1. `forest` → `ice` → `tropic` → `forest` (valores de `next_level` em `forest.tscn`, `ice.tscn`, `tropic.tscn`).
2. `game.tscn` não contém nó `level_end` <!-- Needs Human Confirmation: confirmar se game.tscn ainda faz parte do fluxo -->.

> **Acesso a dados:** nenhum.

---

## Passo a Passo: Câmera

### Passo 1 — Seguir o player (`camera.gd`)

1. `_ready` → `get_target()`: pega o primeiro nó do grupo `player` (`push_error` se ausente).
2. `_process`: `position = target.position`.

> **Acesso a dados:** grupo `player`. Em `ice.tscn` a câmera é filha do player.

### Passo 2 — Observação

1. Em `game.tscn` o nó player não aparece com `groups=["player"]` na cena; verificar se a câmera acha o alvo <!-- Needs Human Confirmation -->.

> **Acesso a dados:** nenhum.

---

## Mapa de Acesso a Dados

| Passo / Operação | Handler / DAO / Serviço | Store / Schema | Tabela / Endpoint / Recurso | Cache / CDN | L/E |
|---|---|---|---|---|---|
| Leitura de input | `player.gd` | Input Map | `left/right/jump/duck` | Nenhum | L |
| Troca de fase | `level_end.gd` | Sistema de arquivos | `res://scene/<next_level>.tscn` | Nenhum | L |
| Recarregar fase | `player.gd` | SceneTree | cena atual | Nenhum | L |

---

## Arquitetura de Cache / Estado

_(nenhum — sem persistência; todo estado vive nos nós e é perdido ao recarregar a cena)_

---

## Tipos Enumerados e Catálogo de Estratégias

| Enum / Tipo | Constantes (quantidade) | Despacho / Factory | Configurável em tempo de execução? |
|---|---|---|---|
| `playerstate` | idle, walk, jump, fall, duck, slide, dead (7) | `match status` em `_physics_process` | Não |
| `skeletonstate` | walk, dead (2) | `match status` em `_physics_process` | Não |

---

## Caminhos Críticos de Performance

| Classe / função / componente | Chamado em | Ponto de atenção |
|---|---|---|
| `player._physics_process` | Todo frame de física | Um `match` + `move_and_slide` |
| `skeleton._physics_process` | Todo frame, por esqueleto (até 9 em `ice.tscn`) | 2 RayCasts por instância |
| `camera._process` | Todo frame | Atribuição direta de posição |

---

## Processamento Assíncrono / em Segundo Plano

| Classe / tarefa / effect | Gatilho | Efeito |
|---|---|---|
| `ReloadTimer` | Morte do player | Recarrega a cena após 2 s |
| `level_end.load_next_scene` | `call_deferred` | Troca de cena fora do callback de física |
