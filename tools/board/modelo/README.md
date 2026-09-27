# Board do cs2-tracker

Este vault é o board de sprints do cs2-tracker: um `.md` por card e a visão Esteira no `Board.base`. Ele fica fora do git e só no checkout principal (Q21=A, ADR-0002 em `docs/adr/0002-kb-e-board-no-obsidian.md`). Nasceu do modelo versionado em `tools/board/modelo/`, por este comando:

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board iniciar
```

## Quem escreve aqui: o CLI

Card só se escreve pelo CLI do board. Ele confere os valores exatos, carimba o `## Histórico` e reclassifica os dependentes:

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board validar
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board fila --agora
```

Sem comando, ele mostra o uso completo (`criar`, `mover`, `historico`, `reclassificar`, `--seco` e `--papel`). Rode da raiz do checkout principal ou de uma worktree dele.

- Arrastar card no kanban grava o `Status` direto no arquivo, sem entrada no Histórico e sem conferência. Prefira o `mover`. Se arrastar, rode o `validar` depois.
- Não renomeie card: o nome `<Ordem> - <título>` é o alvo dos wikilinks de `Depende de` e `Bloqueia`.

## O que tem no vault

- `Board.base`: a visão Esteira (Bases, do núcleo do Obsidian). É um kanban por `Status`, na ordem do board, com os reprovados primeiro e depois a `Ordem`. O card mostra ID, Verificação, Executor e Camada, e acusa valor fora da lista e dependência pendente.
- `README.md`: esta nota. O CLI nunca a lê como card.
- `.obsidian/`: Bases ligado e o plugin da comunidade "Better Kanban Bases View" (`bases-kanban-view-ttvl`, Obsidian 1.10.2 ou mais novo) na lista. O plugin não vem junto: instale em Configurações → Plugins da comunidade (card H1.5). O kanban da Esteira depende dele. O `obsidian-kanban` não entra.

## Atualizar o modelo

Rodar o `iniciar` de novo cria só o que falta e nunca sobrescreve. Esta nota e a config do Obsidian, se diferentes do modelo, ficam como estão, com aviso e o diff. `Board.base` diferente do modelo faz o comando sair 1 com o diff: confira, guarde o seu se quiser, apague ou renomeie o `Board.base` e rode de novo.
