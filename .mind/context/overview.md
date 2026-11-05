---
type: overview
title: pinguim 2d
description: Jogo de plataforma 2D em Godot 4.6 (GDScript) em que um pinguim atravessa fases sazonais (floresta, gelo, trópicos), pulando e desviando de esqueletos. Exportado para Web e publicado via GitHub Pages/Render.
resource: enzosamuca/godot-pinguim-2d
tags: [overview, godot-game, pinguim]
timestamp: 2026-11-05T00:00:00Z
---

# pinguim 2d

> **Ativo:** pinguim | **Repo:** enzosamuca/godot-pinguim-2d | **Tipo:** godot-game | **Última atualização:** 2026-11
> **MindHub:** none
> **Chave SonarQube:** <!-- Needs Human Confirmation: sem sonar-project.properties -->
> **Stack:** Godot 4.6 (feature Mobile), GDScript, renderer `mobile`, Jolt Physics (3D; o jogo é 2D)

## O que é este repositório

Jogo de plataforma 2D de pixel art. O jogador controla um pinguim com máquina de estados (andar, pular com pulo duplo, agachar, deslizar, morrer). Cada fase é uma cena `.tscn` independente com TileMapLayers, um player, esqueletos patrulheiros e um gatilho `level_end` que carrega a próxima fase. Pisar em cima de um esqueleto o derrota; tocá-lo de lado mata o pinguim e recarrega a fase. Há botões de toque (`mobileControls.tscn`) para mobile/web.

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | GDScript (Godot 4.6) |
| Engine | Godot 4.6, `config/features=["4.6","Mobile"]` |
| Render | `renderer/rendering_method="mobile"`, driver Windows `d3d12`, filtro de textura nearest (`default_texture_filter=0`) |
| Viewport | 400x208, stretch `canvas_items` |
| Física | gravidade 2D `1352.364`; Jolt Physics só para 3D |
| Build/Export | preset "Web" (`export_presets.cfg`) → `dist-web/` |
| Banco / Mensageria / Cache | nenhum |

## Interfaces Externas Principais

Não há API de rede. Pontos de entrada do jogo:

| Interface | Caminho | Método | Observações |
|---|---|---|---|
| Cena principal | `run/main_scene="uid://bux8wouug3i0e"` | Godot | O uid corresponde a `scene/tropic.tscn` <!-- Needs Human Confirmation: confirmar se a fase inicial deveria ser `game.tscn` --> |
| Input Map | `left`, `right`, `jump`, `duck` | Teclado / toque | Ver `code-patterns.md` |

## Classes / Módulos Principais

| Classe / Módulo | Caminho | Propósito |
|---|---|---|
| `player` (CharacterBody2D) | `scripts/player.gd` | Controlador do pinguim: enum `playerstate` (idle, walk, jump, fall, duck, slide, dead), pulo duplo, colisor pequeno/grande |
| `skeleton` (CharacterBody2D) | `scripts/skeleton.gd` | Inimigo patrulheiro: `skeletonstate` (walk, dead), RayCast2D de parede/chão |
| `level_end` (Area2D) | `scripts/level_end.gd` | Troca de fase para `res://scene/<next_level>.tscn` |
| `Camera2D` | `camera.gd` | Segue o primeiro nó do grupo `player` |

Cenas: `scene/game.tscn`, `forest.tscn`, `ice.tscn`, `tropic.tscn`, `mobileControls.tscn`; entidades em `scene/entities/` (`player`, `skeleton`, `level_end`, `câmera`). Existe um temporário `scene/tropic.tscn5925326199.tmp` (resíduo do editor).

## Contexto de Implantação

- **Context path:** N/A (jogo web estático)
- **Perfis ativos:** N/A
- **Implantado como:** export Web (`dist-web.html` renomeado para `index.html`), publicado na branch `deploy` e disparo de webhook do Render (`.github/workflows/deploy-web.yml`)

## Referência de Configuração

_(N/A — sem propriedades de configuração de runtime Spring.)_ Configurações do jogo:

| Propriedade | Padrão | Propósito | Origem |
|---|---|---|---|
| `window/size/viewport_width` / `viewport_height` | `400` / `208` | Resolução base | project.godot |
| `window/stretch/mode` | `canvas_items` | Escala de pixel art | project.godot |
| `2d/default_gravity` | `1352.364` | Gravidade usada em `get_gravity()` | project.godot |
| `pointing/emulate_touch_from_mouse` | `true` | Mouse emula toque (botões mobile) | project.godot |
| `@export max_speed` | `100.0` | Velocidade horizontal máxima | `player.gd` |
| `@export acerelacao` / `desacerelacao` / `desacerelacao_slide` | `80.0` | Aceleração, desaceleração, desaceleração no slide | `player.gd` |
| `@export max_jump_count` | `2` | Quantidade de pulos (duplo) | `player.gd` |
| `@export next_level` | `""` (por instância) | Nome da próxima cena | `level_end.gd` |
| Segredo CI `RENDER_WEBHOOK` | — | Webhook do deploy no Render | deploy-web.yml |

## Dependências de Outros Repositórios do Projeto

Nenhuma. Assets de terceiros em `sprites/Seasonal Tilesets/` (há `LICENSE.txt`).

## Integrações Externas

GitHub Actions (imagem `barichello/godot-ci:4.6`), GitHub Pages (branch `deploy`), Render (webhook).

## Build e Execução

```shell
# Executar (Godot 4.6 no PATH)
godot --path .

# Export Web (CI)
godot --headless --verbose --export-release "Web" build/web/dist-web.html
```

## Esquema de Versão

Sem versionamento explícito (sem `version` no project.godot).
