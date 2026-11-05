---
type: runbook
title: Visão Geral de DevOps — godot-pinguim-2d
description: Pipeline de export e deploy Web, fluxo de branches e testes do jogo pinguim 2d.
resource: godot-pinguim-2d
tags: [devops, ci-cd, github-actions, godot, runbook]
timestamp: 2026-11-05T00:00:00Z
---

# Visão Geral de DevOps — godot-pinguim-2d

> Última atualização: 2026-11

## Fluxo Git

Pelo histórico, o trabalho acontece na branch `dev` e entra em `main` via Pull Request (ex.: "Merge pull request #6 from enzosamuca/dev"). <!-- Needs Human Confirmation -->

## Estratégia de Branches

| Branch | Propósito |
|---|---|
| `main` | Produção; dispara o deploy |
| `dev` | Desenvolvimento |
| `deploy` | Saída do export Web (gerada pelo CI, `force_orphan`) |

## Pipelines de CI/CD

| Pipeline | Gatilho | Passos |
|---|---|---|
| `deploy-web.yml` (Export and Deploy Web) | push em `main` | checkout (lfs), templates de export, `godot --import`, `--export-release "Web"`, renomear para `index.html`, upload do artifact (7 dias), deploy na branch `deploy`, webhook Render |

## Artifactory

Não utilizado.

## Quality Gates

- Sem SonarQube, lint ou testes automatizados configurados.
- Chave Sonar: <!-- Needs Human Confirmation: SonarQube project key not found -->

## Testes

Nenhum teste automatizado encontrado (sem GUT/GdUnit). Validação manual jogando as fases.
