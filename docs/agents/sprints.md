---
tipo: referencia
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.sprints)"
  - "backup:temp-artifacts/eb5adec0/plan/plan.md (seção 3, Sequência)"
  - "commit 0164cc3 (candidato-17 e tag jogavel-2026-10-19-2, do P1.1d)"
  - "commit a32ef5e (candidato-18 e tag jogavel-2026-10-19-3, do par P1.3 + P1.4)"
  - "backup:../2026-10-19/janela-t2/t2-velho-resumo.txt (T2, braço processo velho: 6 viradas, memória antes de cada uma de 1,988 a 3,514 GiB, 3,599 GiB no fim)"
  - "commit 9e5ab8e (candidato-19, do P1.6)"
  - "commit c228d93 (candidato-20 e tag jogavel-2026-10-20, do par P1.5 + P1.6)"
  - "backup:../2026-10-20/janela-t2/t2-novo-resumo.txt (T2, braço processo novo: restart às 09:11, 6 viradas, memória de 1,507 a 2,906 GiB; leitura e recomendação no Histórico do card 29,95, B1.12d)"
  - "commit 69c45b1 (candidato-22 e tag jogavel-2026-10-21, do par P1.7 + P1.8 refeito)"
  - "commit bd94909 (merge do PR #105, do P1.12)"
atualizado: 2026-10-22
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
| 7 | **P1** | trilho | Bugs de jogabilidade (depois da B1 e da T1) | 80–92 |
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
| 04/10 | wizard_tui.py com diff antes da D13, só o placeholder do campo de jogador (dado pessoal do Victor) | Victor | T1.3c |
| 19/10 | Exceção ao trilho único (Q6=A) para 3 pares de degraus defensivos com evidências disjuntas, validados juntos numa partida só: P1.3+P1.4, P1.7+P1.8 e P1.9+P1.11 (este numa janela só). P1.6, P1.5 e P1.10 seguem sozinhos; como o P1.11 depende do P1.10, o P1.10 vai antes do par P1.9+P1.11 | Victor (chat com o PM) | no par, o TM leva os dois cards até o merge, com um candidato só, no 2º merge, e a fase 2 do QA julga os dois pela mesma partida; reprovação reverte o par |
| 20/10 | P1.5 em par com o P1.6: o P1.5 foi desenvolvido com o P1.6 (`candidato-19`) ainda no ar, e uma MD3 só valida os dois. Motivo: sem o P1.5 os mapas 2 e 3 não chegam ao laço automático (a espera desistia em 240 s), e o botão manual de forçar início usa o lado do mapa 1. Substitui, para esses dois cards, o "sozinhos" da linha de 19/10. Antes, em 19/10, o Victor já tinha adiantado o P1.6 para antes do fim do T2, com a MD3 de validação só depois do T2 | Victor (chat com o PM) | um candidato só (`candidato-20`, com o `candidato-19` ancestral), e a fase 2 do QA julga os dois pela mesma MD3; reprovação reverte os dois |

## Posição em 22/10

Foto do board (`docs/board-cs2/`, fora do git) nesta data. **O status de cada card é o do board**; esta seção diz a sprint da vez, a ordem da fila e as decisões que a mudaram.

- **Fechadas:** B0 (03/10), B1 com as sobras (B1.9b skins; B1.7 BotAI religado pelo fork 1.8.12-b1.7b), H1, T1 (12/10). A K1 só tem a poda de comentários (K1.9, card 78) aberta; o K1.7 (76) está adiado.
- **Trilho: P1.** Validados e com tag: P1.1 (`jogavel-2026-10-13`), P1.1a (`jogavel-2026-10-14`), P1.1b (`jogavel-2026-10-16`), P1.2 (`jogavel-2026-10-17`; válvula vanilla; partida 85 (`events_85_map0`) em 17/10), P1.1c (`jogavel-2026-10-19`; partida 88 (`events_88_map0`) em 19/10), P1.1d (`jogavel-2026-10-19-2`, no `0164cc3`; partida 89 (`events_89_map0`) em 19/10), o par P1.3 (82) + P1.4 (83) (`jogavel-2026-10-19-3`, no `a32ef5e`; partida 91 (`events_91_map0`) em 19/10) e o par P1.5 (84) + P1.6 (85) (`jogavel-2026-10-20`, no `c228d93`; MD3 de matchid 93 (`events_93_map0` e `events_93_map1`, 2x0) em 20/10) e o par P1.7 (86) + P1.8 (87) (`jogavel-2026-10-21`, no `69c45b1`; partida 96 (`events_96_map0`) em 21/10). A 1ª tentativa desse par (`candidato-21`, partida 95) foi reprovada pelo QA, porque a contagem do P1.7 incluía a SourceTV, e revertida; o par refeito é o `candidato-22` ([versões conhecidas](../runbooks/versoes-conhecidas.md#tags-jogáveis)). A base do trilho é a `jogavel-2026-10-21`. A MD3 acabou em 2x0, então o início sozinho de um mapa 3 e o lado dele (`map_sides[2]`) não foram vistos ao vivo. Ordem aprovada pelo Victor para o resto da P1 (opção A de 22/10), um candidato por vez:
  1. P1.10 (89), sozinho, com a conferência do BotAI do fork na 2000934 (B1.7c) na janela dele: vai antes do par seguinte porque o P1.11 depende dele.
  2. P1.9 (88, tira o SteamID real do `match_config.spike.json` versionado) + P1.11 (90), em par e numa janela só.
- **T2 (B1.12d, card 29,95, Concluída no board): fechado.** Braço processo velho na janela de 19/10 e braço processo novo na de 20/10 (09:08–09:27, com o `docker restart` aprovado na hora pelo Victor), 6 viradas cada, sem queda, segfault nem `FATAL`; somando o T1 de 13/10, 24 viradas sem queda e pico de 4,5 GiB de 7,69. A memória do container sobe a cada carga de mapa e não é devolvida. Recomendação: reiniciar o servidor antes de uma MD3 é precaução barata (o restart custa 13 s), não correção comprovada; as hipóteses H1 e H2 seguem abertas ([B1.12, 9.5](../runbooks/b1.12-segfault-troca-de-mapa-md3.md#95-recomendação-ao-victor)).
- **Pista paralela, sem servidor:** P1.12 (91; SPEC e M5) concluído (merge `bd94909`, PR #105); K1.9 (poda) depois; V1 a semear.
- **Sobras de janela:** T1.7 (`.gitattributes`), B0.11 (comentários do compose), B0.7d (bloquear docker cru).
- **MD3:** liberada depois do T2 (o crash de 04/10 foi na virada de série; o T1 e o T2 do B1.12 somaram 24 viradas sem queda) e já jogada na validação do par P1.5 + P1.6. Antes de uma MD3, o restart do servidor é a precaução do T2, com o OK do Victor na hora.
- **Ambiente:** o Docker Desktop cai quase toda madrugada desde 13/09 (exit 0x40010004; `docs/armadilhas/windows-e-docker.md`): o container para, o json-file corrompe e o `coletar` reconstrói pelo `--tail` (B0.7h). Build do CS2 em vigor: 2000934, desde a subida de 21/10 (SteamCMD; BotAI do fork com `Applied 40/40`, mas sem a conferência formal do B1.7c, que vai na janela do P1.10). A 2000933, a anterior, foi conferida para o BotAI do fork em 16/10.
- **Decisões do Victor de 15 a 17/10:** ordem nova do trilho (MD1 primeiro); P1.1c e P1.1d; vanilla on/off só em janela.
- **Decisão do Victor de 19/10:** os 3 pares da exceção ao trilho único (ver "Exceções aprovadas") e a ordem de então: P1.3+P1.4 → T2 → P1.6 → P1.5 → P1.7+P1.8 → P1.10 → P1.9+P1.11. Com a janela T2 vencida, a opção A: o resto do T2 numa janela curta depois.
- **Decisões do Victor de 20/10:** T2 fechado, com a opção C para o restart (o `docker restart` segue na regra ask do B0.4, e ele aprova na hora); P1.6 adiantado e P1.5 em par com ele (ver "Exceções aprovadas"); a fila do trilho fica P1.7+P1.8 → P1.10 → P1.9+P1.11, com o P1.12 na pista paralela.
- **Decisão do Victor de 22/10 (opção A):** com o P1.7 + P1.8 validados, a fila restante é P1.10 sozinho, com a conferência do BotAI na janela dele, e depois o par P1.9 + P1.11 numa janela.

Quem fecha uma sprint, abre exceção ou muda a fila atualiza esta seção no mesmo dia (PM). Sprint nova semeada no board ganha a faixa na tabela "Ordem de execução".
