# Grafo de Dependências — godot-pinguim-2d

> Última atualização: 2026-11

## Grafo de Módulos Internos

```
project.godot  (main_scene = tropic.tscn)
├── scene/game.tscn, forest.tscn, ice.tscn, tropic.tscn   (fases)
│   ├── scene/entities/player.tscn    → scripts/player.gd
│   │   └── scene/mobileControls.tscn (CanvasLayer)
│   ├── scene/entities/skeleton.tscn  → scripts/skeleton.gd
│   ├── scene/entities/level_end.tscn → scripts/level_end.gd
│   └── scene/entities/câmera.tscn    → camera.gd
├── tiles/terrain.tres, tiles/decoration/
└── sprites/ (1 - Penguin, 3 - Skeleton, Seasonal Tilesets), assets/buttons/
```

## Dependências de Compilação de Outros Repositórios do Projeto

| Dependência | Usada para |
|---|---|
| _(nenhuma)_ | |

## Tópicos Kafka

_(nenhum)_

## Tabelas Principais do Banco

_(nenhuma)_
