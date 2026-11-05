---
type: instruction
title: Segurança — godot-pinguim-2d
description: Requisitos de segurança do jogo pinguim 2d — segredos de CI, entrada e dependências.
resource: godot-pinguim-2d
tags: [security, instruction]
timestamp: 2026-11-05T00:00:00Z
---

# Segurança — godot-pinguim-2d

> Padrão de segurança compartilhado: `.mind/_global/instructions/security.md`

## Logging

Sem biblioteca de logging; só `push_error("player not found")` em `camera.gd`. Não registrar dados pessoais.

## Autenticação

N/A — jogo offline, sem contas.

## Autorização

N/A.

## Validação de Entrada

Entrada apenas via Input Map (teclado/toque). `level_end.next_level` é concatenado ao caminho `res://scene/`; mantenha valores controlados pelo projeto.

## Gestão de CVEs de Dependências

Sem gerenciador de pacotes; depende da versão do Godot (4.6) e da imagem `barichello/godot-ci:4.6`.

## Gestão de Segredos

`RENDER_WEBHOOK` e `GITHUB_TOKEN` via GitHub Secrets; nunca commitar o webhook.

<!-- Needs Human Confirmation for any sections not verifiable from static analysis -->
