---
tipo: referencia
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.sprints)"
  - "backup:temp-artifacts/eb5adec0/plan/plan.md (seção 3, Sequência)"
atualizado: 2026-09-30
---

# Ordem das sprints

Este arquivo diz **em que ordem** as sprints andam e **o que cada uma contempla**, pelas siglas do board. O status de cada card continua no board (`docs/board-cs2/`); aqui fica a ordem, que muda pouco, e as exceções que o Victor aprovou.

Todo agente, inclusive o PM, lê este arquivo antes de propor ou despachar o próximo card.

## Como ler as siglas

- A sigla é o campo `Sprint:` do card (B0, B1, H1, T1, K1...). O ID do card leva a sigla na frente: `B0.7` é o card 7 da B0.
- O número do arquivo no board (campo `Ordem:`) agrupa a sprint por dezena: `12 - ...` é da B0, `26 - ...` da B1. O `,5` marca card acrescentado depois do plano (`14,5` = B0.5b).
- Faixas semeadas em 28/09: **10–19 B0 · 20–29 B1 · 40–48 H1 · 60–67 T1 · 70–78 K1**. As outras sprints ganham faixa quando forem semeadas.

## A regra

1. **Duas pistas.** O **trilho do jogo** (B0 → B1 → P1 → S1…S7) mexe no caminho de jogo e anda uma mudança por vez, cada uma validada numa partida do Victor. A **pista paralela** (H1 → T1 → K1 → V1) não toca no jogo e anda junto, também uma sprint por vez.
2. **Sprint seguinte só começa com a anterior fechada.** Fechada = critérios de saída do plano cumpridos e, no trilho do jogo, uma tag `jogavel-*` em que o Victor jogou. Vale para as duas pistas.
3. **O trilho do jogo tem prioridade.** Havendo card da sprint aberta do trilho pronto para começar, ele vai antes do card da pista paralela.
4. **Pular a ordem só com exceção do Victor, registrada abaixo.** Card com dependência satisfeita não basta: a sprint dele também precisa ser a da vez.
5. **Sobras** de uma sprint fechada (cards `,5` abertos depois do fechamento) ficam na faixa dela e entram na fila atrás da sprint aberta do trilho.

## Ordem de execução

| # | Sigla | Pista | Sprint | Faixa no board |
|---|---|---|---|---|
| 1 | **B0** | trilho | Linha de base jogável e travas | 10–19 |
| 2 | **B1** | trilho | Trilha de bots | 20–29 |
| 3 | **H1** | paralela | Harness enxuto | 40–48 |
| 4 | **T1** | paralela | Testes herméticos, G4 e CI | 60–67 |
| 5 | **K1** | paralela | Base de conhecimento | 70–78 |
| 6 | **V1** | paralela | Pauta e partidas órfãs | a semear |
| 7 | **P1** | trilho | Bugs de jogabilidade (depois da B1 e da T1) | a semear |
| 8 | **S1** | trilho | Poda verificada (depois da K1) | a semear |
| 9 | **S2** | trilho | Schema versionado | a semear |
| 10 | **S3** | trilho | Ingestão única | a semear |
| 11 | **S4** | trilho | Apresentação | a semear |
| 12 | **S5** | trilho | Configuração e MatchRunner | a semear |
| 13 | **S6** | trilho | Launcher web e D13 | a semear |
| 14 | **S7** | trilho | Plugin JSONL v1 | a semear |
| — | B2 | trilho | Bots etapa 2 | fora do backlog ativo; só se Q16=A |
| — | S8 | trilho | Aposentar a TUI | fora do backlog ativo; só depois da D13 e do OK do Victor |

## O que cada sprint contempla

| Sigla | Objetivo | Fecha quando | Pede do Victor |
|---|---|---|---|
| **B0** | Referência jogável, volta em um comando (`jogavel.py`), travas, backup e volume external | tag no origin; backup com manifesto; hook testado em worktree; `jogavel.py` parte 1 ensaiado na Janela 0; volume external com mounts idênticos | abrir a Janela 0 (30–45 min) e jogar depois |
| **B1** | CSSharp 1.0.375 e os plugins de bot religados um por partida | CSSharp ativo; cada plugin religado ou mascarado; BotRandomizer; épocas registradas | ~7 partidas e janelas curtas |
| **H1** | Evidência de partida por ferramenta, CLI e vault do board, papéis, skills, AGENTS.md completo | `evidencia_partida.py` e CLI com testes; vault aberto; 4 papéis e 4 skills; AGENTS.md completo | ~15 min para abrir o vault |
| **T1** | Suíte verde em clone limpo, G4 (smoke da TUI) e CI | CI verde em clone limpo; G4 e integração TUI → run_match; PII e CRLF no CI | responder a Q20 |
| **K1** | Tirar o conhecimento dos comentários para `docs/` antes de qualquer poda | ADRs 0001–0005; 54 armadilhas com fonte; contrato JSONL e glossário; poda provada | ~20 min para ler o ADR-0001 |
| **V1** | Salvar as partidas órfãs e registrar as respostas da pauta | órfãs decididas e ingeridas ou arquivadas; ADR-0006 | ~15 min e 1 janela de dados |
| **P1** | MD3 automática, nenhuma partida perdida, aviso de captura, válvula vanilla | mapas 2 e 3 sozinhos; órfão certo; colisão sem descarte; aviso de captura; vanilla em um comando | 1 MD3 e ~6 partidas |
| **S1** | Apagar só o que foi confirmado, depois da KB | `nao-apagar.md`; cadeia da demo; CSV removido; ≥ 500 linhas a menos | 3–4 partidas |
| **S2** | Migrações aditivas com `user_version` | `user_version` ≥ 1 com backup; tag anterior roda no banco migrado | 2 partidas |
| **S3** | Um só `persist_match`, provado por reingestão dourada | um escritor só; diferenças aprovadas | 2 partidas e 10 min |
| **S4** | Uma fonte por métrica nas telas; fim do estático depois do S6.4 | paridade de /partidas; K/D e ADR iguais em todas as telas | 2 partidas e 5 min |
| **S5** | Runner único, com a TUI sem diff | Settings, RCON e Docker únicos; MatchRunner; MD3 pela TUI | ~3 partidas e 1 MD3 |
| **S6** | Iniciar pelo browser e cumprir a D13 | MD3 completa pelo browser | 1 MD3 pelo browser |
| **S7** | Plugin JSONL v1: arquivo por mapa, placar do engine, watcher por pasta | schema v1; 3 placares batendo; 0 regex sobre `docker logs` | 3 partidas e 1 janela |

## Exceções aprovadas

| Data | Exceção | Quem aprovou | Efeito |
|---|---|---|---|
| 26/09 | Via rápida (Q0=A): a B1 começou antes de a B0 fechar, sem o `jogavel.py` nem a Janela 0 | Victor | a trilha andou com runbooks à mão; a B0 ficou com B0.3, B0.5b, B0.6, B0.7, B0.7b, B0.8, B0.9, B0.9b e B0.11 abertos |
| 27/09 | Passos da B1 por runbook à mão enquanto o `jogavel.py` não existe | PM | ver `docs/runbooks/trilha-de-bots.md` |
| 26–28/09 | K1.1, K1.2 e K1.3 feitos antes da T1 | sem registro de decisão | ficam como estão; não abrem precedente |

## Posição em 30/09

Tirada do board (`docs/board-cs2/`, fora do git): campos `Status` e `Depende de` dos cards. O board manda no status; esta seção diz só quem é a sprint da vez e a fila dela, e pode estar um passo atrás.

- **Trilho:** B1 fechada pelo B1.10 (tag `jogavel-2026-09-28`). A **B0 é a sprint aberta** e vai primeiro.
- **Pista paralela:** a **H1 é a sprint aberta** (H1.1b, H1.7, H1.8, H1.9; o H1.10 está adiado). O H1.8 depende do B0.7b, então a H1 só fecha depois do B0.7b. T1 espera a H1.
- **Feito na B0:** B0.3, B0.6, B0.5b e B0.9b em 28/09 (PRs #25 a #28); B0.7 (PRs #31 e #32) e B0.9c (PR #33) em 30/09.
- **Fila da B0**, na ordem aprovada pelo Victor em 30/09 (B0.5c → B0.7 → B0.7b → B0.5d → B0.9c):
  1. B0.5c (guarda: leitura literal do banco e do `.env`, e `@(...)` no PowerShell): parado depois de 2 reprovações, com o critério 2 em pauta para o Victor. O B0.5d espera por ele.
  2. B0.7b (`jogavel.py` parte 2): parado pelo conflito do critério 5 (bloquear docker cru travaria os runbooks do servidor), em pauta para o Victor.
  3. B0.8 e B0.11 (compose), aplicados na Janela 0 (B0.9), que o Victor abre. A partida seguinte dele fecha a B0 com uma tag.
- **Sobras da B1:** B1.10b, B1.7a e B1.8b sem servidor; B1.7 (BotAI) e B1.2 (depende do T1.1) no caminho de jogo, depois da B0.
- **Validação pendente no jogo:** VPK Low e a build 2000919 do CS2, na próxima partida do Victor.

Quem fecha uma sprint, abre exceção ou muda a fila atualiza esta seção no mesmo dia (PM). Sprint nova semeada no board ganha a faixa na tabela "Ordem de execução".
