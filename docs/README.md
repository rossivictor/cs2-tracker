---
tipo: moc
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; card K1.1)"
  - "backup:temp-artifacts/eb5adec0/audit/comments.json (proposed_kb_structure)"
  - "AGENTS.md:91-96"
atualizado: 2026-10-01
---

# Base de conhecimento do cs2-tracker

> **O código diz o quê; a KB diz o porquê.** No código fica só o invariante local e um link curto (`ver [[ADR-0004]]`). Decisão, investigação, procedimento e pegadinha moram aqui, em `docs/`, versionados junto com o código. Como decidir o que sai do comentário: [politica-de-comentarios.md](politica-de-comentarios.md).

As regras para agentes ficam no [AGENTS.md](../AGENTS.md), na raiz. O board de sprints não mora aqui: é o vault `docs/board-cs2/`, fora do git ([ADR-0002](adr/0002-kb-e-board-no-obsidian.md)).

## Por onde começar

1. [ADR-0001: visão](adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md): partidas avulsas agora, modo carreira no horizonte longo.
2. [SPEC.md](SPEC.md): o produto especificado em 19–20/09 (decisões D1–D22). O status real de cada decisão é do K1.6.
3. [features/](features/README.md): specs de feature por milestone (M0–M7).
4. [runbooks/](runbooks/README.md): procedimentos passo a passo, como a trilha de bots.
5. [historico/](historico/README.md): investigações e handoffs, que não se editam.

## Mapa

| Pasta | O que guarda | Índice |
|---|---|---|
| `adr/` | Decisões com contexto, alternativas e consequências | tabela abaixo |
| `arquitetura/` | Como o sistema funciona hoje, entre módulos | [README](arquitetura/README.md) |
| `dominio/` | Glossário, métricas e placar MR12 | [README](dominio/README.md) |
| `runbooks/` | Procedimentos passo a passo, com rollback | [README](runbooks/README.md) |
| `armadilhas/` | Pegadinhas do engine, da MatchZy, dos plugins e do Windows | [README](armadilhas/README.md) |
| `historico/` | Timeline, investigações datadas e handoffs | [README](historico/README.md) |
| `agents/` | Plano, sprints, lições e playbook do PM | [README](agents/README.md) |
| `features/` | Specs de feature (M0–M7) | [README](features/README.md) |
| `img/`, `prototypes/` | Telas do README e o protótipo `home.html` (destino no Q14) | — |

## Decisões (ADRs)

| ADR | Decisão | Status |
|---|---|---|
| [0000](adr/0000-modelo.md) | Modelo de ADR | modelo |
| [0001](adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md) | Visão: partidas avulsas agora, carreira no horizonte longo | aceito (28/09) |
| [0002](adr/0002-kb-e-board-no-obsidian.md) | KB versionada em `docs/` e board no Obsidian, sem Notion | aceito |
| [0003](adr/0003-repo-publico.md) | Repo público, sem uso comercial e sem PII nova | aceito |
| [0004](adr/0004-jogo-sempre-jogavel.md) | O jogo está sempre jogável | aceito |
| [0005](adr/0005-trilha-de-bots-uma-variavel-por-vez.md) | Trilha de bots primeiro, uma variável por vez | aceito |
| 0006 | Respostas da pauta Q1–Q21 (card V1.9) | a escrever |
| 0007+ | ADRs retroativos, tirados dos commits e das D1–D22 (card K1.6) | a escrever |

## Frontmatter padrão

Toda nota nova começa assim:

```yaml
---
tipo: adr            # moc, politica, modelo, indice, arquitetura, dominio, runbook, armadilha, historico ou agents
status: aceito       # ADR: proposto, aceito, substituído ou descartado. Outras notas: rascunho, vigente ou obsoleta
aliases: [ADR-0004]  # só em ADR: é o que faz o [[ADR-0004]] do código abrir a nota no Obsidian
fontes:
  - "watcher.py:125"
  - "transcript de92b218 @ 2026-09-03T01:19:04Z"
atualizado: 2026-09-26
---
```

- `fontes` diz de onde saiu cada afirmação. Cada entrada tem uma forma só, e o `tools/checar_fontes.py` (K1.4) segue esta gramática:
  - `caminho:N` ou `caminho:N-M`, sem espaço: arquivo deste repo, relativo à raiz;
  - `repo:<nome> caminho:N` ou `repo:<nome> caminho:N-M`: outro repositório, em `C:/Users/Victor/Projetos/<nome>` (ex.: `repo:kalendas docs/agents/licoes.md:220-226`);
  - `backup:<caminho>`: relativo a `C:/Users/Victor/cs2-tracker-backups/2026-09-26/`, onde estão a auditoria e o plano (B0.2). Um `backup:../<data>/...` sai dessa pasta para o backup de outra data, como o `backup:../2026-09-27/b1.5/` do frontmatter do [smoke só de bots](runbooks/smoke-partida-de-bots.md), a única fonte assim no repo;
  - `transcript <8 primeiros caracteres do id> @ AAAA-MM-DDTHH:MM:SSZ`: sessão local do Claude Code, que não é versionada;
  - `commit <sha>` ou `PR #<n>`.
  - Qualquer entrada pode terminar com ` (detalhe)`, só para quem lê (ex.: as chaves de um JSON). O checador ignora esse sufixo, e fora dele não há texto livre.
- A linha de um `caminho:N` vale no último commit que tocou a nota (`git log -1 -- <nota>`), não na data de `atualizado`: o código pode andar depois, e a nota é revista quando alguém mexer nela.
- `atualizado` é a data da última revisão de conteúdo, não de formatação.
- As notas anteriores ao K1.1 (SPEC.md, features/ e os dois runbooks) ainda não têm frontmatter. Elas ganham o frontmatter quando forem revisadas (K1.4, K1.6). O handoff em `historico/` fica como está.

## Regras da KB

- Tudo em pt-BR. Entre notas, use link relativo em Markdown, que funciona no GitHub e no Obsidian. `[[...]]` só no código, pela política de comentários.
- Nome de arquivo único na KB inteira: o `[[nome]]` do Obsidian depende disso. A exceção são os `README.md` de índice de cada pasta, que nunca se citam com `[[ ]]`.
- Sem PII: nenhum SteamID64 real, IP ou segredo ([ADR-0003](adr/0003-repo-publico.md)). O `tools/hooks/pii.py` barra no Write e no Edit. Arquivo escrito por Bash ou PowerShell não passa por ele: em `docs/`, só Edit e Write.
- Nota de `historico/` não se edita. Correção vai para a nota viva, e o histórico ganha só um link. O índice `historico/README.md` é a exceção: ganha uma linha a cada nota nova.
- ADR aceito não se reescreve: decisão nova vira ADR novo, que substitui o antigo ([modelo](adr/0000-modelo.md)).
