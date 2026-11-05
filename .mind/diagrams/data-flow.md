# Fluxo de Dados — godot-pinguim-2d

> Última atualização: 2026-11

## Fluxo Principal de Jogo

```mermaid
sequenceDiagram
    participant In as Input (teclado/toque)
    participant P as player.gd
    participant S as skeleton.gd
    participant L as level_end.gd
    participant T as SceneTree

    In->>P: left/right/jump/duck
    P->>P: _physics_process, match status, move_and_slide
    P->>S: hitbox.area_entered, take_demage() (se caindo)
    P->>P: go_to_dead_state() (se não caindo)
    P->>T: ReloadTimer 2s, reload_current_scene()
    P->>L: body_entered
    L->>T: change_scene_to_file(res://scene/next_level.tscn)
```

## Fluxos de Eventos Kafka

_(nenhum)_

## Contratos de Dados Principais

| Contrato | Formato | Schema / classe |
|---|---|---|
| Input Map | `project.godot` | ações `left`, `right`, `jump`, `duck` |
| Cenas | `.tscn` | `scene/**` |
| Tilesets | `.tres` | `tiles/terrain.tres`, `tiles/decoration/decoração.tres` |
