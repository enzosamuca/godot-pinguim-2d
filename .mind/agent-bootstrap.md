---
type: index
title: Base de Conhecimento de IA Mind — godot-pinguim-2d
description: Índice de bootstrap dos agentes de godot-pinguim-2d — arquivos de contexto sempre carregados, regras de código e registro de skills.
resource: godot-pinguim-2d
tags: [index, agent, bootstrap, mind, skills]
timestamp: 2026-11-05T00:00:00Z
---

# Base de Conhecimento de IA Mind — godot-pinguim-2d

<!-- mind-managed: do not remove this block -->
<!-- agent-bootstrap-template-version: 2.2 -->

> **Este repositório usa uma base de conhecimento de IA interna (`.mind/`).**
> O `.mind/` guarda o conhecimento somente deste repositório e de como ele se relaciona com os outros.
> A visão do projeto inteiro (todos os repositórios, visão geral, domínios de conhecimento) fica no MindHub.
> Não é um catálogo de serviços: nunca crie `catalog-info.yaml`, `port.yml` ou `cortex.yaml`.

## Contexto sempre carregado

Leia estes arquivos no início de toda sessão:

- `.mind/context/overview.md` — Jogo de plataforma 2D em Godot 4.6/GDScript: stack, cenas, scripts principais e configuração
- `.mind/context/domain.md` — Glossário do jogo: estados, entidades, fases, camadas de física
- `.mind/context/business-logic.md` — Fluxos do player, combate, patrulha do esqueleto, troca de fases e câmera
- `.mind/context/code-graph.md` — Stub do grafo de código (GDScript não analisado) e notas de implementação
- `.mind/diagrams/cloud-architecture.md` — Pipeline de export Web, GitHub Pages e Render
- `.mind/diagrams/data-flow.md` — Fluxo input → player → inimigo → troca de cena
- `.mind/topology/dependency-graph.md` — Relação entre cenas, scripts, tilesets e sprites
- `.mind/topology/external-resources.md` — Webhook do Render e consumidores
- `.mind/devops/overview.md` — CI/CD, branches, qualidade e testes
- `.mind/instructions/code-patterns.md` — Convenções GDScript e estrutura do projeto
- `.mind/instructions/security.md` — Segredos de CI e validação de entrada
- `.mind/evolution/README.md` — Funcionalidades em andamento (nenhuma no momento)

## Regra inegociável

> Esta regra está **sempre ativa** em todas as sessões de agente neste repo. As demais regras de
> código e de segurança estão em `.mind/instructions/code-patterns.md` e `.mind/instructions/security.md`.

1. **Indentação** — leia o contexto ao redor antes de editar qualquer arquivo; siga exatamente o estilo existente (tabs vs espaços, largura da indentação).

## Skills

| Local | Tipo | Propósito |
|---|---|---|
| `.mind/skills/<nome>/SKILL.md` | Skills do kit Mind neste repo | `onboard-repo` (`/mind-onboard`) e `update-repo` (`/mind-update`) |

Índice completo: `.mind/skills/_index.md`

## Atualizando a documentação

Para atualizar o `.mind/` quando o código mudar: `/mind-update`.
<!-- end mind-managed block -->
