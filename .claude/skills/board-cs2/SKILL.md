---
name: board-cs2
description: Board do cs2-tracker (vault Obsidian docs/board-cs2) pelo CLI tools.board. Use para ver a fila, validar o vault, mover card, anotar no Histórico, criar ou reclassificar cards.
---

# Board do cs2-tracker

O vault é `C:/Users/Victor/Projetos/cs2-tracker/docs/board-cs2/`, fora do git, e só se grava pelo CLI: Edit e Write ali nunca, porque o CLI é quem carimba o `## Histórico` e confere os valores. Ler um card com Read pode.

Ajuda completa, com cada opção e o formato de `<ref>`:

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board
```

| Para quê | Depois de `-m tools.board` |
|---|---|
| conferir o vault | `validar` (com `--tudo`, os concluídos entram) |
| o que despachar agora | `fila --agora` (consulta o preflight) |
| mudar status ou campos | `mover --card=<ID> --status="Em testes" --texto=<entrada>` |
| só anotar | `historico --card=<ID> --texto=<entrada>` |
| criar cards | `criar --spec=<arquivo.json>` |
| depois do merge | `reclassificar --concluido=<ID>` |
| ensaiar uma escrita | a mesma linha com `--seco` |

- Quem assina: `--papel=` (TM é o padrão). O dev não toca no board ([dev.md](../../agents/dev.md)).
- Quais `mover` cada papel faz e em que momento: seção Board de [tech-manager.md](../../agents/tech-manager.md), [qa.md](../../agents/qa.md) e [servidor.md](../../agents/servidor.md).
- Valores aceitos (status, executor, papel, trilho): `tools/board/modelo.py`. Vault novo: `iniciar`, a partir de `tools/board/modelo/`.
- Por que Obsidian e fora do git: [ADR-0002](../../../docs/adr/0002-kb-e-board-no-obsidian.md). Ordem das sprints: [sprints.md](../../../docs/agents/sprints.md).
