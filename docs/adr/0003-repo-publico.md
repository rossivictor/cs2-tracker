---
tipo: adr
status: aceito
aliases: [ADR-0003]
fontes:
  - "transcript eb5adec0 @ 2026-09-26T22:10:19Z"
  - "transcript 7010f738 @ 2026-09-19T13:33:09Z"
  - "AGENTS.md:13"
  - "AGENTS.md:42-44"
  - "tools/hooks/pii.py:1-21"
  - "commit 4c19249"
  - "backup:temp-artifacts/eb5adec0/audit/git.json (findings[1], findings[2], findings[8] e findings[9])"
  - "backup:temp-artifacts/eb5adec0/audit/critic.json (gaps[10]; top_risks[7])"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (princípios; cards B0.5, T1.3, T1.6 e S1.8)"
atualizado: 2026-09-26
---

# ADR-0003: Repo público, sem uso comercial e sem PII nova

## Contexto

O `rossivictor/cs2-tracker` no GitHub é público (`gh repo view`, na auditoria git). Em 26/09, 25 mil linhas existiam só no disco local. Publicar essas linhas era a forma de ter backup, mas também levaria ao público logos de times, artes extraídas dos VPKs da Valve, um DLL de terceiro (`docker/plugins/DefaultAgents/`) e o SteamID64 do Victor em arquivos novos. A crítica pediu decidir a visibilidade antes do push (critic, lacuna 11).

O SteamID64 dele já está no `origin/main` desde o `4c19249` (04/09), por causa do `docker/match_config.spike.json`, que também funciona como cadastro de identidade. Os segredos do `.env` (SRCDS_TOKEN e CS2_RCONPW) nunca foram versionados: o `git log -S` não os acha. Na auditoria, o repo inteiro tinha 4,5 MiB, sem blob grande e sem `.dem`, `.db` ou `.vpk`.

Perguntado, o Victor respondeu: "Pode subir, não tem uso comercial".

## Decisão

- **O repo continua público.** Serve ao Victor e a "um ou outro que achar o repo", sem uso comercial ([ADR-0001](0001-visao-partidas-avulsas-carreira-horizonte-longo.md)). Nomes e marcas reais seguem no uso pessoal (SPEC §9, D3).
- **O histórico não é reescrito por causa do SteamID.** Ele é público desde 04/09, e um `filter-repo` exigiria force-push na `main` por um ganho quase nulo. Reescrever histórico publicado continua proibido (AGENTS.md).
- **Daqui para frente, nenhuma PII nova:** nenhum SteamID64 real, `[U:1:n]`, IP (fora de `127.0.0.1` e `0.0.0.0`) ou segredo em `docs/`, `tests/`, `.cursor/`, `.env.example`, `*.md` da raiz ou mensagem de commit. Teste e fixture usam SteamID fictício abaixo da base 76561197960265728 (ex.: 76561190000000001).
- **A trava é determinística, não prosa:** o `tools/hooks/pii.py`, chamado pelo `guarda.py` em todo Write e Edit (B0.5), e o check de PII no CI (T1.6). O hook nunca imprime o valor achado.
- **Segredo só no `.env`**, que nunca é lido, copiado nem colado no chat. O `.env.example` guarda só placeholders.

## Alternativas consideradas

- **Tornar o repo privado**: o Victor escolheu subir. O que já é público continua público, porque clone e cache não voltam.
- **Reescrever o histórico (`filter-repo`) para tirar o SteamID**: dado já exposto há três semanas, force-push na `main` e risco nas branches e worktrees abertas, para um ganho quase nulo.
- **Backup só por `git bundle`, sem push**: resolvia o backup, mas deixava as 25 mil linhas fora do fluxo de PR e board que o programa precisa.

## Consequências

- Todo agente escreve fixture anonimizada: o T1.3 troca SteamID64, SteamID3 e IP antes de o dado entrar em `tests/fixtures/`. Dado real só vem das cópias de backup, nunca do banco, do `events-live` ou do `.env` vivos.
- O SteamID que já está na árvore sai quando o card de cada arquivo passar por ele. O P1.9 separa o `docker/match_config.spike.json` em template versionado e runtime fora do git, e essa é a hora de tirar dele a identidade. O `wizard_tui.py` fica sem diff até a D13. Enquanto isso, o hook impede que o SteamID se espalhe.
- A remoção do `docker/plugins/DefaultAgents/`, binário de terceiro já desligado, é do S1.8. A proveniência de logos, artes e ícones de arma ainda não está documentada: a auditoria git recomenda um `static/SOURCES.md`, e isso fica como ideia, sem card.
- Nota da KB com PII é bloqueada no Write. Se o bloqueio parecer falso, pare e peça ao Victor. Nunca contorne.

## Status

Aceito em 2026-09-26, pela resposta do Victor ("Pode subir, não tem uso comercial"). O merge da branch local na `main` e a tag `jogavel-2026-09-26` já estão no `origin` (B0.1).

## Fontes

- Transcript `eb5adec0` @ 22:10Z: a resposta sobre publicar. Transcript `7010f738` @ 19/09: "um ou outro que achar o repo".
- Auditoria git: repo público, o SteamID desde o `4c19249`, tokens nunca vazados e a recomendação de não usar `filter-repo`. Critic: lacuna 11 e o risco "publicar ao tentar fazer backup".
- `tools/hooks/pii.py` e AGENTS.md: a trava e a regra em vigor.
