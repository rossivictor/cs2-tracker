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
  - "commit ba17644 (candidato-23, do P1.10)"
  - "commit a0b4dca (candidato-24, do B1.3s)"
  - "commit cc17bb4 (tag jogavel-2026-10-25, do par B1.3s + P1.10)"
  - "backup:../2026-10-25/g7-b1.3s-p1.10-copia/logs/janelas/2026-10-23.md (linhas 28-35: quedas na 2000935, NadeSystem e vanilla on)"
  - "commit c67e548 (candidato-25, do par P1.9 + P1.11)"
  - "commit 09e54bd (tag jogavel-2026-10-26, do par P1.9 + P1.11 com o P1.9b)"
  - "commit 57e357b (candidato-26 e tag jogavel-2026-10-26-2, do B1.13)"
  - "backup:../2026-10-26/g7-b1.13-copia/docs/board-cs2/ (Históricos dos cards 88 (opção A de 22/10), 29,97 (B1.13 antes de fechar a P1, decisão de 25/10) e 29,98 (B1.14; a entrada de 26/10 14:53, a música de MVP, veio depois da cópia e está só no board do checkout principal))"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-26.md (linhas 19 e 23: o recriar que devolve 0 com o boot falho e o residual de 0 B; 133: o residual apagado)"
atualizado: 2026-10-26
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
| 22/10 | Opção A: o P1.10 sozinho, antes do par P1.9 + P1.11, com a conferência do BotAI na janela dele; a dependência do board P1.10 → P1.9 é só de sequência do plano (o P1.10 mexe só no plugin, o par no `docker-compose.yml`). Depois, o par numa janela só, validado por uma partida | Victor (chat com o PM) | o P1.10 virou o `candidato-23`; o par, o `candidato-25` (`jogavel-2026-10-26`) |
| 24/10 | B1.3s (card 22,5, CSSharp v1.0.378) em par com o P1.10 (`candidato-23`, ainda sem partida): o jogo estava fora do ar por causa externa (a build 2000935 derrubava a CSSharp 1.0.375 com humano), e as evidências são disjuntas (entrada do humano sem queda × captura sem órfão). Substitui o "sozinho" do P1.10 na linha de 19/10. O Victor aprovou junto o download do asset oficial (G5) | Victor (chat com o PM) | `candidato-24` com o `candidato-23` ancestral, validados pela partida 97 (`jogavel-2026-10-25`) |
| 25/10 | B1.13 (card 29,97, sobra da B1 fechada) antes de fechar a P1: os plugins de bot voltam na build 2000935 antes do fechamento, contra a regra 5 (sobra atrás da sprint aberta) | Victor (chat com o PM) | entrou depois do par P1.9 + P1.11, no trilho único: `candidato-26`, validado pela partida 101 (`jogavel-2026-10-26-2`) |

## Posição em 26/10

Foto do board (`docs/board-cs2/`, fora do git) nesta data. **O status de cada card é o do board**; esta seção diz a sprint da vez, a ordem da fila e as decisões que a mudaram.

- **Fechadas:** B0 (03/10), B1 com as sobras (B1.9b skins; B1.7 BotAI religado pelo fork 1.8.12-b1.7b; B1.3s, CSSharp v1.0.378, em 25/10; B1.13, os 6 plugins de bot na 2000935, em 26/10), H1, T1 (12/10) e **P1 (26/10, tag `jogavel-2026-10-26-2`)**. A K1 só tem a poda de comentários (K1.9, card 78) aberta; o K1.7 (76) está adiado.
- **P1 FECHADA em 26/10** pelo Victor: "Fecha a P1 com as duas ressalvas registradas." Últimos degraus: o par P1.9 (88, template do `match_config` em `docker/match_config.template.json` e runtime em `docker/runtime/`, montado) + P1.11 (90, 27015/tcp só em 127.0.0.1), com o P1.9b (88,5, coleta e evidência no caminho novo), na `jogavel-2026-10-26` (`09e54bd`; partida 100, `events_100_map0`), e o B1.13 na `jogavel-2026-10-26-2` (`57e357b`; partida 101, `events_101_map0`; [versões conhecidas](../runbooks/versoes-conhecidas.md#tags-jogáveis)). **Ressalvas do Victor**, só com prova por teste:
  1. o início sozinho do mapa 3 de uma MD3 (e o lado dele, `map_sides[2]`): a MD3 de 20/10 foi 2x0;
  2. "partida interrompida gera 1 orphan com os rounds dela": só prova por teste desde o P1.10.
  Quando qualquer das duas acontecer ao vivo, o QA confere na coleta normal da partida, sem card novo.
- **Trilho até a P1:** P1.1 (`jogavel-2026-10-13`), P1.1a (`jogavel-2026-10-14`), P1.1b (`jogavel-2026-10-16`), P1.2 (`jogavel-2026-10-17`; válvula vanilla), P1.1c (`jogavel-2026-10-19`), P1.1d (`jogavel-2026-10-19-2`), P1.3 + P1.4 (`jogavel-2026-10-19-3`), P1.5 + P1.6 (`jogavel-2026-10-20`; MD3 de matchid 93, 2x0), P1.7 + P1.8 (`jogavel-2026-10-21`; o `candidato-21` reprovado e revertido antes), P1.10 com o B1.3s (`jogavel-2026-10-25`), P1.9 + P1.11 (`jogavel-2026-10-26`) e o B1.13 (`jogavel-2026-10-26-2`). O P1.12 (91; SPEC e M5) fechou na pista paralela (PR #105).
- **Estado no ar:** a `jogavel-2026-10-26-2` (`57e357b`), build 2000935, CSSharp v1.0.378, **válvula vanilla off** desde a janela de 26/10 13:48, com os 6 plugins de bot (BotAI do fork com `Applied 40/40`; NadeSystem 1.2.1-b1.13 de um fork local, com a assinatura nova da smoke). O arquivo residual de 0 B `game/csgo/match_config.spike.json` do volume foi apagado nessa janela, com o OK do Victor.
- **Próximas, pela ordem:** K1.9 (78, poda de comentários, para fechar a K1) e a V1 (pista paralela, a semear), depois a S1 (trilho, depois da K1). Com a P1 fechada, nenhum degrau do trilho está na fila até a S1.
- **Abertos fora da ordem, a decidir pelo Victor:** B1.14 (29,98, Pronta para começar; o título fala da música de round vencido, mas em 26/10 o Victor identificou a de MVP em loop entre os halves; paliativo dele: volume da música de MVP zerado); e, ainda sem card: container pausado lido como rodando pelo `start_match` (23/10); a LAN com servidores duplicados; o botão de forçar início que usa o lado do mapa 1; o `jogavel.py recriar` que devolve 0 com o boot falho (26/10 09:53, SteamCMD com timeout e exit 5); a captura sem `equip_value` de bot (o `equip_freeze_end` é 0 para bot em toda partida); e docs com o caminho antigo do `match_config` (`docker/match_config.spike.json`, antes do P1.9). Sobras de antes: T1.7 (`.gitattributes`), B0.11 (comentários do compose), B0.7d (bloquear docker cru), B1.2 e B1.8b.
- **Lições do fechamento:** L06 a L13 em [licoes.md](licoes.md); as regras do PM (L06 a L09) já estão no [pm-playbook](pm-playbook.md), e as de outros papéis seguem pendentes, com o arquivo que deve recebê-las.
- **T2 (B1.12d, card 29,95, Concluída no board): fechado.** Braço processo velho na janela de 19/10 e braço processo novo na de 20/10 (09:08–09:27, com o `docker restart` aprovado na hora pelo Victor), 6 viradas cada, sem queda, segfault nem `FATAL`; somando o T1 de 13/10, 24 viradas sem queda e pico de 4,5 GiB de 7,69. A memória do container sobe a cada carga de mapa e não é devolvida. Recomendação: reiniciar o servidor antes de uma MD3 é precaução barata (o restart custa 13 s), não correção comprovada; as hipóteses H1 e H2 seguem abertas ([B1.12, 9.5](../runbooks/b1.12-segfault-troca-de-mapa-md3.md#95-recomendação-ao-victor)).
- **MD3:** liberada depois do T2 (o crash de 04/10 foi na virada de série; o T1 e o T2 do B1.12 somaram 24 viradas sem queda) e já jogada na validação do par P1.5 + P1.6, na 2000933 e com os plugins de bot. Na 2000935 com a CSSharp v1.0.378 ainda não houve MD3 (as de G7 desde então, 97, 100 e 101, foram MD1). Antes de uma MD3, o restart do servidor é a precaução do T2, com o OK do Victor na hora.
- **Ambiente:** o Docker Desktop cai quase toda madrugada desde 13/09 (exit 0x40010004; `docs/armadilhas/windows-e-docker.md`): o container para, o json-file corrompe e o `coletar` reconstrói pelo `--tail` (B0.7h). Nas coletas de 25 e 26/10 o log veio inteiro, sem reconstrução: cada container era o do recreate da janela do dia. Build do CS2 em vigor: **2000935** (CS2 v1.41.9.2), desde o recreate da janela de 22/10; a 2000934 durou de 21 a 22/10 e nunca teve a conferência do BotAI. CSSharp em vigor: v1.0.378, desde a janela de 25/10. Em 23/10 o container ficou pausado numa tentativa de jogo, e o `start_match` o leu como rodando (armadilha em `windows-e-docker.md`).
- **Decisões do Victor de 15 a 17/10:** ordem nova do trilho (MD1 primeiro); P1.1c e P1.1d; vanilla on/off só em janela.
- **Decisão do Victor de 19/10:** os 3 pares da exceção ao trilho único (ver "Exceções aprovadas") e a ordem de então: P1.3+P1.4 → T2 → P1.6 → P1.5 → P1.7+P1.8 → P1.10 → P1.9+P1.11. Com a janela T2 vencida, a opção A: o resto do T2 numa janela curta depois.
- **Decisões do Victor de 20/10:** T2 fechado, com a opção C para o restart (o `docker restart` segue na regra ask do B0.4, e ele aprova na hora); P1.6 adiantado e P1.5 em par com ele (ver "Exceções aprovadas"); a fila do trilho fica P1.7+P1.8 → P1.10 → P1.9+P1.11, com o P1.12 na pista paralela.
- **Decisão do Victor de 22/10 (opção A):** com o P1.7 + P1.8 validados, a fila restante é P1.10 sozinho, com a conferência do BotAI na janela dele, e depois o par P1.9 + P1.11 numa janela.
- **Decisão do Victor de 23/10 (opção B):** com a queda na entrada do humano na 2000935, não jogar até a correção; o jogo fica em vanilla on, e a investigação dos plugins de bot na 2000935 fica para depois.
- **Decisão do Victor de 24/10:** o card B1.3s (CSSharp v1.0.378 oficial, com o download aprovado) em par com o P1.10 (ver "Exceções aprovadas").
- **Decisão do Victor de 25/10:** os plugins de bot voltam antes de fechar a P1 (B1.13, ver "Exceções aprovadas").
- **Decisões do Victor de 26/10:** OK do download do NuGet `CounterStrikeSharp.API` 1.0.375 (G5) e da janela do B1.13; OK de apagar o residual de 0 B do volume; a P1 fechada com as duas ressalvas (acima).

Quem fecha uma sprint, abre exceção ou muda a fila atualiza esta seção no mesmo dia (PM). Sprint nova semeada no board ganha a faixa na tabela "Ordem de execução".
