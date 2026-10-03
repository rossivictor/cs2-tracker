---
name: cs2-servidor
description: Servidor CS2 do cs2-tracker (container, RCON, volume, janela de manutenção). Use antes de mexer no que está no ar ou para achar o papel servidor, o preflight, o tools/jogavel.py e o runbook certo.
---

# Servidor do cs2-tracker

Só o papel servidor opera o jogo, e só em janela: o procedimento inteiro está em [servidor.md](../../agents/servidor.md). Fora desse papel, esta skill serve para saber o estado e para quem pedir; as regras (janela, zonas proibidas, preflight) estão no [AGENTS.md](../../../AGENTS.md).

## Estado, sem mudar nada

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py status
```

O significado de cada saída do preflight está no AGENTS.md (Preflight); o `status` mostra HEAD, última `jogavel-*`, delta até a `origin/main`, janela e container.

## `tools/jogavel.py`

- Do Victor e do servidor: `status`, `voltar`, `atualizar`.
- Janela: `janela abrir --por "<frase>"`, `janela vigiar`, `janela fechar`.
- Tags: `marcar candidato|jogavel <commit> -m "<card e evidência>"`.
- Pós-partida, só leitura: `coletar`.
- Só com a janela aberta: `recriar`, `parar`, `rcon "<cmd>"`, `snapshot --destino <D>`, `restaurar --de <tgz>`, `soak`.

Todos têm `--seco`; as saídas e opções estão no topo de `tools/jogavel.py` e em `--help`.

## Runbooks (`docs/runbooks/`)

- [README.md](../../../docs/runbooks/README.md): o índice.
- [voltar-ao-jogavel.md](../../../docs/runbooks/voltar-ao-jogavel.md): `status`, `voltar`, `atualizar` e a janela.
- [b1.3-cssharp-1.0.375.md](../../../docs/runbooks/b1.3-cssharp-1.0.375.md): o modelo de janela (passos, G6, rollback).
- [trilha-de-bots.md](../../../docs/runbooks/trilha-de-bots.md): ordem da sprint B1 e o registro.
- [smoke-partida-de-bots.md](../../../docs/runbooks/smoke-partida-de-bots.md): partida só de bots na janela e o fechamento.
- [versoes-conhecidas.md](../../../docs/runbooks/versoes-conhecidas.md), [inventario-volume.md](../../../docs/runbooks/inventario-volume.md) e [reconstruir-volume.md](../../../docs/runbooks/reconstruir-volume.md): o que cada tag jogável tinha, o volume e a recuperação.

Registro de cada janela: `C:/Users/Victor/Projetos/cs2-tracker/logs/janelas/<data>.md`. Por que tudo isso: [ADR-0004](../../../docs/adr/0004-jogo-sempre-jogavel.md).
