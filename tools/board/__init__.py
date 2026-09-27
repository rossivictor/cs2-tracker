"""
CLI do board do Obsidian (card H1.3): as operações que não podem depender
de interpretação. Conferir valores, montar a fila com o trilho único,
reclassificar dependentes depois de um merge, criar card com o frontmatter
exato e gravar status e `## Histórico` pelos agentes.

    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board <comando>

Rode da raiz do checkout principal ou de uma worktree dele (o `-m` acha o
`tools` pela pasta atual). O board padrão é sempre o do checkout principal,
por caminho absoluto; `--board=<pasta>` troca (testes usam tmp_path).

Porte de `kalendas/scripts/lib/board.ts`. Partes: `frontmatter` (leitura e
escrita linha a linha), `modelo` (valores, grafo, validar, fila,
reclassificar, criar), `vault` (o `iniciar`, que cria o vault a partir da
pasta `modelo/`, card H1.4) e `cli` (comandos). Só biblioteca padrão.
"""
