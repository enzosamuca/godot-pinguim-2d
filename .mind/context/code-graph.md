# Grafo de Código — `godot-pinguim-2d`

> A análise Tree-sitter não encontrou arquivos analisáveis (GDScript não é suportado) neste onboarding.
> Este arquivo será preenchido na próxima execução do `update-repo`, caso o suporte exista.

## Referência de Configuração

Ver `.mind/context/overview.md` (seção Referência de Configuração).

## Notas de Implementação Relevantes

- Todo estado vive nos nós; não há persistência entre sessões.
- Player e esqueleto usam máquina de estados com `enum` + `match`.
- Morte do player recarrega a cena após 2 s (`ReloadTimer`).
- A troca de fase usa `change_scene_to_file` com `next_level` por instância de `level_end`.
- Ordem das fases: forest → ice → tropic → forest.
- A cena principal do projeto (`run/main_scene`) aponta para `tropic.tscn`.
