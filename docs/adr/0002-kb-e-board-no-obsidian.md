---
tipo: adr
status: aceito
aliases: [ADR-0002]
fontes:
  - "transcript eb5adec0 @ 2026-09-26T16:14:14Z"
  - "transcript eb5adec0 @ 2026-09-26T22:10:19Z"
  - "AGENTS.md:12"
  - "AGENTS.md:91-96"
  - "repo:kalendas docs/agents/licoes.md:220-226"
  - "repo:kalendas docs/agents/licoes.md:236-242"
  - "repo:kalendas docs/agents/licoes.md:252-258"
  - "repo:kalendas docs/agents/licoes.md:260-266"
  - "backup:temp-artifacts/eb5adec0/audit/kalendas.json (what_worked_or_lessons; board_mechanics; reuse_for_cs2)"
  - "backup:temp-artifacts/eb5adec0/audit/critic.json (gaps[1] e gaps[5])"
  - "backup:temp-artifacts/eb5adec0/audit/notion.json (summary)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (kb_structure; board_schema; Q21; cards H1.3 e H1.4)"
atualizado: 2026-09-27
---

# ADR-0002: KB versionada em `docs/` e board no Obsidian, sem Notion

## Contexto

Em 26/09 o Victor pediu uma base de conhecimento ("docs no Obsidian, por exemplo") e uma "base orquestradora (como um Board no Notion, por exemplo)" para planos de curto, médio e longo prazo. O projeto não tinha nenhuma das duas: o conhecimento estava em comentários, SPEC, `docker/SPIKE.md` e transcripts, e o Notion não tem nada do cs2-tracker (auditoria notion).

O próprio Victor já tinha passado pelo Notion no kalendas, e saído dele:

- **L13** (10/09): a seleção do Notion aceita valor desconhecido e cria a opção em silêncio. Agentes gravaram "Em execução", "Pronto para começar" e "Concluído", status que não existiam.
- **L15** (12 e 13/09): a cota de consulta (`rows`/`sql`) acabou no meio da esteira, com "reached the usage limit for Query Data Source". Na segunda vez, a cota só voltou de madrugada.
- **L54** (20 a 22/09): o teste da S15 rodou o board inteiro num vault local, sem cota, sem custo de API e sem espera. Em 22/09, o Obsidian virou o único board, e a raiz do Notion ganhou o aviso "All contents were moved to Obsidian".

Em 26/09, perguntado onde ficam a base de conhecimento e o board, o Victor escolheu "Obsidian, modelo kalendas". No kalendas, o board é um vault dentro do repo e ignorado pelo git, e o conhecimento versionado fica em `docs/`. É a opção A da Q21 ("como no kalendas"). Com essa resposta, a Q21 está respondida: o AGENTS.md a registra entre as decisões definitivas, que não voltam a ser pergunta.

## Decisão

- **KB em `docs/`, versionada no git**, junto com o código: Markdown com frontmatter (`tipo`, `status`, `fontes`, `atualizado`), links relativos e MOC em [docs/README.md](../README.md). Ela é lida pelo GitHub ou aberta no Obsidian como segundo vault, só leitura.
- **Board no vault próprio `docs/board-cs2/`**, fora do git e só no checkout principal. Tem um `.md` por card e o `Board.base` (Bases, do núcleo do Obsidian) com uma visão, a Esteira. O `Status` do frontmatter é a única fonte (L55).
- **Escrita no board só pelo CLI** `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board` (H1.3), que valida valores exatos, põe o carimbo de hora e reclassifica dependentes. Nunca por edição solta.
- **Sem Notion**, nem para board nem para KB.

## Alternativas consideradas

- **Notion para o board**: as L13, L15 e L54, e cada leitura e escrita custa cota e turno de ferramenta.
- **`docs/` inteiro como vault, com o board dentro (Q21=B)**: edição do Victor numa nota versionada viraria commit feito por agente, e status de card (estado vivo) se misturaria com o histórico do git.
- **Board versionado no git**: toda mudança de status viraria commit, e o status muda várias vezes por card.

## Consequências

- O `.gitignore` recebe `docs/board-cs2/` e `docs/.obsidian/` (B0.7). O board não aparece nas worktrees: agentes usam o caminho absoluto `C:/Users/Victor/Projetos/cs2-tracker/docs/board-cs2/` (AGENTS.md).
- Por ser ignorado, o board sumiria num `git clean -X`. Por isso o `git clean` é proibido e o `tools/backup.py` copia a pasta (B0.6).
- Sem Obsidian Sync: é uma máquina só. Plugins: Bases e "Better Kanban Bases View". O `obsidian-kanban` fica desligado, e nada de `types.json` herdado de outro vault (lição do kalendas).
- Aberto como segundo vault, `docs/` contém o vault do board, `docs/board-cs2/`. O Obsidian não tem modo só leitura, e a atualização automática de links ao renomear poderia reescrever card do board por fora do CLI. No vault da KB, "Automatically update internal links" fica desligado e `board-cs2/` entra em "Excluded files". A outra saída é ler a KB pelo GitHub. O H1.4 ou o H1.5 aplica.
- A KB precisa ser legível no GitHub: link relativo entre notas e `aliases` no ADR, para o `[[ADR-00xx]]` do código abrir no Obsidian ([política](../politica-de-comentarios.md)).
- Conhecimento que hoje está fora do repo, como os artifacts do claude.ai e os planos em `~/.claude/plans` (critic, lacuna 6), entra na KB como nota com fonte, não como link solto.

## Status

Aceito em 2026-09-26, pela escolha do Victor ("Obsidian, modelo kalendas"), que responde a Q21 com A. O vault é criado e aberto nos cards H1.4 e H1.5, que executam só o ramo A. A decisão é definitiva: só o próprio Victor a reabre, e por um ADR novo que substitua este.

## Fontes

- Transcript `eb5adec0`: o pedido de 16:14Z e a escolha de 22:10Z.
- kalendas `docs/agents/licoes.md`: L13, L15, L54 e L55, com sintoma, causa e regra.
- Auditoria: kalendas, critic (lacuna 2) e notion. Plano: `kb_structure`, `board_schema` e Q21.
