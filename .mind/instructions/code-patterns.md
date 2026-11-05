# Padrões de Código — godot-pinguim-2d

> Padrões compartilhados: `.mind/_global/instructions/code-patterns.md`

## Estrutura do Projeto

```
camera.gd            # Camera2D que segue o grupo player
scene/               # fases (game, forest, ice, tropic) e mobileControls
scene/entities/      # player, skeleton, level_end, câmera
scripts/             # player.gd, skeleton.gd, level_end.gd
tiles/               # tilesets (.tres)
sprites/ assets/     # pixel art e botões de toque
export_presets.cfg   # preset Web
```

## Convenções de Nomenclatura

- GDScript em `snake_case`; estados com `go_to_<estado>_state()` e `<estado>_state(delta)`.
- Enums em minúsculas (`playerstate`, `skeletonstate`); `match status` despacha o estado.
- Nomes existentes com grafia própria (`acerelacao`, `desacerelacao`, `set_small_colider`, `take_demage`): mantenha ao editar.
- Indentação com tabs nos `.gd`.

## Padrões de Projeto Utilizados

| Padrão | Onde | Observações |
|---|---|---|
| Máquina de estados (enum + match) | `player.gd`, `skeleton.gd` | Transições em `go_to_*` |
| Cenas reutilizáveis | `scene/entities/` | Instanciadas nas fases |
| Grupos | `player`, `inimigos` | Câmera usa `get_nodes_in_group("player")` |
| Sinais | hitbox, ReloadTimer, level_end | Conectados nas cenas |

## Configuração do Spring

N/A.

## Convenções de Banco de Dados

N/A.

## Convenções de Commit e Branch

Mensagens curtas em português, ex.: "fase do gelo". Merge via PR a partir de `dev`.

## Padrões Específicos deste Repositório

- Camadas de física: 1 terrain, 2 player, 3 enemies, 4 level_end (máscara do player = 9, ou seja, terrain + level_end).
- Pixel art: filtro nearest, viewport 400x208.
- Nova fase: criar `.tscn` em `scene/`, instanciar player/câmera/skeleton/level_end e definir `next_level`.
- O `CLAUDE.md` existente descreve 5 estados e 3 fases (desatualizado: há 7 estados, a fase `ice` e o `skeleton`). <!-- Needs Human Confirmation -->
