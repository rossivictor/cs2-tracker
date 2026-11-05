---
tipo: arquitetura
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/dead_captura.json (candidates[]: verification.verdict, reason e evidence)"
  - "backup:temp-artifacts/eb5adec0/audit/dead_apresentacao.json (candidates[]: verification.verdict, reason e evidence)"
  - "backup:temp-artifacts/eb5adec0/audit/dead_orquestracao.json (candidates[]: verification.verdict, reason e evidence)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (críticas: preservados por decisão, SVGs a pedido do dono, home.html e tiles F3.5)"
  - "docs/agents/plano-2026-09-26.json:13 (princípio: refutado nunca, incerto ganha card de checagem)"
  - "docs/agents/plano-2026-09-26.json:1418 (orquestracao-13 e 52 refutados: não apagar)"
  - "docs/agents/plano-2026-09-26.json:1634-1654 (S1.1)"
  - "docs/agents/plano-2026-09-26.json:1674-1712 (S1.3 e S1.4)"
  - "docs/agents/plano-2026-09-26.json:1751-1808 (S1.7, S1.8 e S1.9)"
  - "docs/agents/plano-2026-09-26.json:2043-2140 (S4.1, S4.4 e S4.5)"
  - "docs/agents/plano-2026-09-26.json:2210-2226 (S5.3: o CLI mantém --map e --side)"
  - "docs/agents/plano-2026-09-26.json:2317-2333 (S6.3: botão Iniciar)"
  - "docs/agents/plano-2026-09-26.json:2366-2382 (S7.1: contrato v1 e ADR do que se captura)"
  - "docs/adr/0006-pauta-1.md:53-56 (Q11, Q13 e Q14)"
  - "docs/adr/0006-pauta-1.md:71-83 (Consequências da Q11=C, da Q13 e da Q14)"
  - "docs/agents/sprints.md:155-159 (ordem da S1 e a divergência do S1.4)"
  - "AGENTS.md:10 (wizard_tui.py vivo e sem diff até a D13)"
  - "AGENTS.md:32 (C:/cs2server intocado)"
  - "parser.py:56-62"
  - "parser.py:246"
  - "parser.py:449-650"
  - "parser.py:1388-1412"
  - "tools/enrich_from_demos.py:45"
  - "tools/reingest_demos.py:34"
  - "watcher.py:58"
  - "watcher.py:71-87"
  - "watcher.py:261-262"
  - "watcher.py:545-546"
  - "stats.py:1387-1413"
  - "stats.py:1212-1214"
  - "matches.py:491-565"
  - "roster.py:194-216"
  - "roster.py:275-277"
  - "roster.py:320-357"
  - "roster.py:146-171"
  - "start_match.py:420-438"
  - "start_match.py:692-713"
  - "start_match.py:1492-1517"
  - "wizard_core.py:33-35"
  - "wizard_core.py:142-144"
  - "wizard_core.py:431-490"
  - "web/app.py:206-212"
  - "web/app.py:281-564"
  - "web/templates/wizard_modal.html:12"
  - "web/templates/summary.html:30"
  - "templates/_home_content.html:14-56"
  - "templates/shell.html:52-57"
  - "templates/shell.html:99-115"
  - "tests/test_matches_screens.py:228-231"
  - "config.py:16-43"
  - "docker-compose.yml:112-113"
  - "server-configs/cfg/gamemode_competitive_server.cfg:14-18"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:489-572"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:597-735"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:805-841"
  - "tools/evidencia_partida.py:101"
  - "docs/runbooks/versoes-conhecidas.md:746"
  - "README.md:515"
atualizado: 2026-11-05
---

# Não apagar

A régua da poda (S1): o que nenhum card de poda tira, por que fica e o que muda isso. O QA confere o diff de cada card de poda contra esta lista: refutado, preservado ou incerto sumindo reprova.

**Totais:** 14 refutados · 20 preservados por decisão (18 IDs da auditoria e 2 itens de fora dela) · 7 incertos · 1 decisão pendente (Q11). A auditoria de 26/09 tem 144 vereditos: 123 confirmados, 14 refutados e 7 incertos.

As referências `arquivo:linha` foram conferidas no código de 05/11 (`origin/main` 01074ef); o veredito diz a linha de 26/09, que pode ter andado.

## Como usar

1. **Só sai o que está CONFIRMADO e consta como removível no card de poda.** O ID tem de estar no critério ou no escopo do card, e fora das tabelas abaixo.
2. **REFUTADO, PRESERVADO POR DECISÃO e INCERTO nunca saem por card de poda**, nem em parte, nem "de carona" num bloco vizinho.
3. **Refutado só volta a ser candidato por re-verificação registrada** que satisfaça a "condição que levanta a refutação" da linha, feita por quem a linha diz. Até lá, a linha vale.
4. **Item de poda que toque em código de uma linha desta lista cita o ID dela no PR**, e diz o que ficou no lugar.
5. Confirmado com ressalva no próprio veredito ("não é código a apagar", "decisão de produto") está na tabela de preservados, e vale como preservado.

## Refutados (14)

A remoção foi refutada pela verificação de 26/09: o item está vivo ou a alegação errou.

| ID | Onde / o quê | Por que a remoção foi refutada | Condição que levanta a refutação | Quem decide | Card |
|---|---|---|---|---|---|
| captura-2 | `parser.py`: `parse_and_store` (449-650), `_s` (246), `main` (1388-1412) e `PLAYER_PROPS` (56-62) | Junta destinos diferentes: `PLAYER_PROPS` é importado por `tools/enrich_from_demos.py:45`, e `parse_and_store` serve ao modo nativo (`watcher.py:58`) e ao `tools/reingest_demos.py:34` | `parse_and_store`, `_s`, `main`: veredito novo de que não sobrou chamador vivo (modo nativo e `reingest_demos` fora). `PLAYER_PROPS`: o `enrich_from_demos` removido (S1.2) e nenhum importador no `grep` | QA cético do S1.3 (veredito); a remoção é do S1.4, na ordem dele | S1.3, S1.4 |
| captura-17 | regeneração do `report.html`/`index.html` a cada ingestão: `watcher.py:261-262` e `watcher.py:545-546` (funções em `watcher.py:71-87`) | Fluxo vivo e documentado: quem joga pela TUI vê as estatísticas sem subir o uvicorn; a aposentadoria é condicionada, não decidida | Q13=A: S6.4 (MD3 pelo browser) feito, S4.1 com paridade, e o Victor confirma a paridade na 8000 | Victor (paridade); QA cético do S4.4 | S4.4 |
| captura-42 | fallback de tempo cego por saltos de `flash_duration` em `match_loadout` (`stats.py:1387-1413`) e a coluna `player_positions.flash_duration` | Serve à tela das partidas 1 e 2 (`source='demo'`) e ao que o `enrich_from_demos` grava nas partidas `events` sem `player_blinds`; tem teste | Nenhuma partida `source='demo'` no banco (só depois da decisão da Q11, abaixo), `enrich_from_demos` fora (S1.2) e nenhum outro produtor de `flash_duration` não nulo | QA cético do S1.3; Victor na Q11 | S1.3 (o S1.5 tira awpy e polars sem tocar no fallback) |
| captura-46 | `docker/build-events-plugin.sh` e `docker/build-events-plugin.ps1` | Não são equivalentes na prática: em 26/09 o `.sh` falhava no Git Bash do host (conversão de caminho do MSYS) e o build que funcionou foi o `.ps1`. Desde então o 0.4.1 saiu do `.sh` (`docs/runbooks/versoes-conhecidas.md:746`) e o `README.md:515` documenta os dois | Um script só provado no host do Victor, com README, `.gitignore:8` e runbooks na mesma PR; e o `.ps1` só sai com a condição do orquestracao-42 | Victor | nenhum |
| captura-47 | dois leitores de VPK: índice em `tools/extract_map_radar.py:51` e regex em `roster.py:239-254`; `data/map_radar.json` com 22 mapas | Cada leitor sustenta um fluxo vivo (pak01 só pelo índice; `botprofile.db` é texto); mapas fora do pool continuam alcançáveis pelo `--map` | Não é remoção: só uma refatoração que unifique os leitores, com teste dos dois fluxos; os mapas extras só saem se o `--map` passar a validar contra o pool | card próprio de refatoração, com QA | nenhum |
| captura-48 | modo `bbox` do radar em `matches.py:491-565` | Alcançável: mapa NULL cai em `bbox` (já aconteceu em 22/09) e o `--map` aceita mapa fora do snapshot; tem teste | Mapa NULL impossível na ingestão e `--map` validado contra `data/map_radar.json`, com teste. O docstring velho de `stats.match_positions` (`stats.py:1212-1214`) é a parte confirmada: corrigir o comentário pode | card próprio, com QA | nenhum |
| apresentacao-2 | `report.py`, rota `GET /report` (`web/app.py:206-212`) e o chip "Relatório antigo" (`templates/matches.html:15`) | Em uso e sem paridade: é a única tela com vitória por bombsite, a nota de `score_source` e o card de assists | S4.1 com paridade (bombsite, `score_source`, assists), S6.4 feito e o Victor confirmando a paridade na 8000 (Q13=A) | Victor; QA cético do S4.4 | S4.1, S4.4 |
| apresentacao-37 | documentação dos geradores estáticos no README e as mensagens do `start_match` que citam `report.html` | Descreve comportamento atual: os geradores seguem vivos (captura-17) | Os geradores aposentados no S4.4; aí o README e as mensagens mudam na mesma PR | QA cético do S4.4 | S4.4 |
| apresentacao-41 | `test_relatorio_antigo_continua_de_pe` (`tests/test_matches_screens.py:228-231`) | Única cobertura do `/report`, que o watcher roda depois de cada partida. O `templates/report.html` já está versionado; o comentário do teste ("único caminho offline") segue errado e pode ser corrigido | O `/report` aposentado no S4.4 (o teste sai junto) ou trocado por teste de paridade de `/partidas` | QA cético do S4.4 | S4.4 |
| orquestracao-2 | CLI de validação do roster: `read_container_profile_names` (`roster.py:275-277`), `validate_against_server` e `missing_profiles` (`roster.py:194-216`), `main --validate` (`roster.py:320-357`) | `missing_profiles` está no caminho vivo (`valid_teams`); o CLI diz quais perfis faltam em cada time, critério da F1.1 e da validação das variantes do VPK | Outro instrumento que dê o mesmo diagnóstico por time, com teste, e o Victor de acordo. A casca de uma linha (`read_container_profile_names`) pode ser incorporada sem isso | Victor | nenhum |
| orquestracao-6 | `TEAM_LOGO_FILES` e `Team.logo` (`roster.py:146-171`; campo `logo` em `data/rosters.json`) | Não é duplicação: um é o código de logo do jogo (`mp_teamlogo_2`), o outro o arquivo em `static/`; nenhum deriva do outro | Não é remoção: só mover o nome do arquivo para `data/rosters.json` (o `logo_path` da M3.5), por card próprio | card próprio, com QA | nenhum |
| orquestracao-13 | `set_map_in_config`/`set_side_in_config` (`start_match.py:420-438`) e `--map`/`--side` (`start_match.py:1498-1506`) | É o único mecanismo de mapa e lado do CLI, caminho headless permanente (D13) | O CLI montar um `MatchSetup` e passar por `build_match_config`; aí só as `set_*` saem. As flags ficam ("o CLI mantém --map e --side") | QA do S5.3 | S5.3 |
| orquestracao-42 | `docker/build-events-plugin.ps1` | É o ponto de entrada do Victor no Windows (o `bash` do PATH dele cai no WSL); a DLL é ignorada, então os scripts são o único jeito de gerar o plugin num clone limpo | O Victor dizer que não usa mais o `.ps1`, com outro caminho de build documentado e provado | Victor | nenhum |
| orquestracao-52 | `write_match_config`, `load_base_config` e `resolve_setup_identity` (`wizard_core.py:442-472`) | Cascas finas, mas no caminho vivo da web e da TUI; `resolve_setup_identity` é a fachada que mantém o web sem importar `identity` | Não é remoção: embutir nos chamadores é refatoração cosmética, por card próprio, com G4 | card próprio, com QA | nenhum |

## Preservados por decisão (20)

Confirmados mortos, sem uso ou incompletos, mas ficam por decisão do Victor ou do plano. A condição aqui é o que levanta a preservação.

| ID | Onde / o quê | Por que fica | O que levanta a preservação | Quem decide | Card |
|---|---|---|---|---|---|
| orquestracao-4 | `Team.veto` (`roster.py:146`; `data/rosters.json`); o bot sorteia uniforme em `wizard_core.py:142-144` | Dado curado para o veto ponderado (F7.1, `docs/features/M7-acabamento.md`; SPEC §14, item 8): pendência, não lixo | A F7.1 descartada pelo Victor | Victor | F7.1 (sem card na S1) |
| orquestracao-10 | `set_scoreboard_names` (`start_match.py:692-713`) | Metade pronta do placar F4.4; fica viva com o launcher web | O S6.3 entregue e a função ainda sem chamador, com veredito novo | QA do S6.3 | S6.3 |
| orquestracao-11 | caminho lineup → placar no núcleo: `NEUTRAL_ENEMY_LABEL`, `_ROSTER_CATALOG` (`wizard_core.py:33-35`), ramo de `team2` e `_scoreboard_args` (`wizard_core.py:431-490`) | Fiação pendente da Etapa 6; tirar `_scoreboard_args` ou `to_match_setup` quebra a TUI | O mesmo do orquestracao-10 | QA do S6.3 | S6.3 |
| orquestracao-12 | tela de Lineups (`web/app.py:281-564`, `web/templates/lineups.html`) | Feature incompleta, bloqueada pela Etapa 6; remover quebra o fluxo web e os testes | Nenhuma: com o S6.3 ela passa a ter saída | Victor | S6.3 |
| orquestracao-39 | HTMX por CDN (`web/templates/wizard_modal.html:12`) | Decisão D15; é o turno do bot no veto (`hx-trigger="load delay:1.2s"`), coberto por teste | Um ADR revendo a D15, com substituto do turno do bot e o teste do veto verde | Victor (ADR) | nenhum |
| captura-23 | `round_stats` (32 contadores do engine): emitido em `Cs2TrackerEventsPlugin.cs:660-735`, gravado na tabela `round_stats` | Contrato do plugin: o conjunto do que se captura é decidido no S7.1 (contrato v1, ADR do que se captura); `round_stats` também é cauda normal para a evidência (`tools/evidencia_partida.py:101`) | O ADR do S7.1 tirando o tipo do contrato | Victor (ADR do S7.1) | S7.1 |
| captura-24 | `freeze_end.players[].money` (`Cs2TrackerEventsPlugin.cs:597-633`) | Contrato do plugin, como o captura-23 | O mesmo do captura-23 | Victor (ADR do S7.1) | S7.1 |
| captura-25 | `bomb_defused` e `bomb_planted.player_name/steamid` (`Cs2TrackerEventsPlugin.cs:805-841`), `round_officially_ended` (`:728-735`) | Contrato do plugin; o handler de `round_officially_ended` é o que emite `round_stats` | O mesmo do captura-23 | Victor (ADR do S7.1) | S7.1 |
| captura-26 | `snapshot` a 2 Hz (`Cs2TrackerEventsPlugin.cs:489-572`) | Contrato do plugin; é a cauda normal que o órfão ignora (`tools/evidencia_partida.py:101`) | O mesmo do captura-23 | Victor (ADR do S7.1) | S7.1 |
| apresentacao-3, -4, -5 | export estático: `home.generate_home`/`main`, as chamadas no watcher (as do captura-17), `--report-out`/`--home-out`, `REPORT_PATH`/`HOME_PATH` (`config.py:39-40`) e os `report.html`/`index.html` gerados | Q13=A: o estático só se aposenta depois do S6.4 e da paridade confirmada na 8000 | O mesmo do captura-17 | Victor; QA cético do S4.4 | S4.4 |
| apresentacao-14 | vitória por bombsite: `_bombsites_for_round_nums`, `_bombsite_leaderboard` e a chave `bombsites` (`stats.py:357`, `stats.py:1086`, `stats.py:1502`; `matches.py:716`) | Lacuna de paridade: o S4.1 leva para `/partidas`, não apaga | Nenhuma por poda | QA do S4.1 | S4.1 |
| apresentacao-15 | `kast_has_assists`, `kast_has_trades`, a lista `clutches`, `sampled_ticks` (`stats.py:647-652`, `stats.py:782-787`, `stats.py:1300`) | O S1.7 diz "15, 22, 31 e 33 ficam"; o S4.1 trata o 15 | O S4.1 fechado, com veredito novo de que nenhuma tela lê | QA do S4.1 | S1.7, S4.1 |
| apresentacao-22 | tiles `.mode-pro`/`.mode-comp` e o crest "Competitivo" (`templates/_home_content.html:14-56`) | Q14=A: os tiles ficam como pendência; a F3.5.2 fica fora do S4.5; o S1.7 diz que ficam | Uma resposta nova do Victor (implementar ou remover a F3.5.2), registrada no ADR-0006 | Victor | S1.7, S4.5 |
| apresentacao-23 | wizard web sem saída: "Iniciar partida" desabilitado (`web/templates/summary.html:30`) | Feature incompleta (Etapa 6, D13) | Nenhuma: o S6.3 habilita o botão | QA do S6.3 | S6.3 |
| apresentacao-31 | `static/weapons/` (100 SVGs; 57 sem casamento com o banco em 26/09) | O Victor pediu o conjunto completo de armas (19/09); o S1.7 e o S4.5 dizem que os SVGs ficam | Só pedido explícito do Victor | Victor | S1.7, S4.5 |
| apresentacao-33 | `docs/prototypes/home.html` | Q14=A: é a única especificação visual da F3.5.2 e da F3.5.3 e **nunca é apagado** | Nenhuma por poda; só o Victor revogando a Q14 no ADR-0006 | Victor | S1.7, S4.5 |
| (fora da auditoria) | `wizard_tui.py` | Vivo e sem diff até a D13 (AGENTS.md) | A D13 cumprida (MD3 pelo browser) e o OK do Victor | Victor | S8.3 |
| (fora da auditoria) | `C:/cs2server` | Intocado: a única semente de recuperação (AGENTS.md) | Nenhuma | Victor | S1.4 (critério "intocado") |

## Pendente: Q11 e o critério do S1.4

**Pendente: o PM leva ao Victor antes do dev do S1.4.** A Q11=C (apagar as partidas 1 e 2, de origem demo) diverge do critério do S1.4 no plano, que diz "partidas 1–2 mantidas". O critério não se reescreve aqui, e esta lista não diz que o S1.4 mudou.

Pelo ADR-0006 (Consequências), a Q11=C implica:

- apagar as linhas das partidas 1 e 2 numa janela de dados, com backup antes pelo `tools/backup.py`, e só depois tirar o caminho de demo e o awpy;
- as duas partidas não têm JSONL: o backup é a única volta;
- o S1.4 deixa de ser só Offline e Partida e passa a pedir janela de dados e backup;
- efeitos em S1.2 e S1.5 (tiram `enrich_from_demos` e o awpy), S1.3 (re-verifica a cadeia sabendo que ela não terá linhas a servir), S2.1 (import sem awpy) e S3.1 (reingestão dourada sem linhas de origem demo).

Até a decisão chegar ao S1.4, ficam **no lugar**: as linhas do banco das partidas 1 e 2, a demo da partida 2 que é o `demo_path` dela (`demos/`, ressalva do captura-49) e o caminho de reingestão por demo (`tools/reingest_demos.py`, `parse_and_store`, o fallback do captura-42).

## Incertos (7)

O veredito não fechou. Todos apontam para o [S1.9, "Checar os incertos"](../agents/sprints.md#posição-em-0511) (card 109), que dá veredito novo a cada um, com dump de cvars de bot em janela, e **não remove nada**. Depois do veredito, o item vira confirmado (e só sai por um card de poda que o liste) ou refutado (e entra na tabela acima). O plano de 26/09 e as críticas chamam esse card de "S1.8", numa numeração antiga; o card vigente é o S1.9.

| ID | Onde / o quê | Por que é incerto (o que faltou) | Aponta para | Quem decide |
|---|---|---|---|---|
| captura-34 | overrides `CS2_TRACKER_*` (`load_env`/`_get`, `config.py:16-35`) e os defaults `REPORT_PATH`, `HOME_PATH`, `DEMO_DIR`, `DEMOS_LIVE_DIR`, `STATS_LIVE_DIR` (`config.py:39-43`) | O `_get` parecia sem uso, mas `load_env` é chamado ao vivo (senha RCON) e os cinco defaults servem ao fluxo matchzy. Desde 26/09, o `tools/reingest_events.py:50` lê `CS2_TRACKER_DB_PATH` pelo `load_env`. Só se resolve depois do captura-17 e do fim do fallback por demo | S1.9 | Victor |
| apresentacao-21 | dropdown do JOGAR e CSS `.menu button`/`.dot` (`templates/shell.html:52-57`, `:105-109`), rodapé "sem servidor" (`:115`), ramo `report` do nav (`:99`) | Mistura: o dropdown e o CSS são sobra do protótipo; o rodapé está certo nos estáticos e o ramo `report` vive enquanto o `/report` viver | S1.9 | Victor |
| orquestracao-5 | comentário de `CONTAINER_VPK_PATH` (`roster.py:32-36`) | Ambíguo, não comprovadamente errado: "via docker/pre.sh" pode fechar a oração do search path. Reescrever é clareza, não poda | S1.9 | Victor |
| orquestracao-23 | flags `--compose-file`, `--container-name`, `--match-config`, `--rcon-host`, `--rcon-port`, `--boot-timeout`, `--skip-up` (`start_match.py:1492-1517`) | Sem rastro no repo, mas flag de CLI se usa à mão; `--skip-up` e `--boot-timeout` já foram usadas; as três primeiras são acopladas ao compose | S1.9 | Victor (depende também da Q15) |
| orquestracao-28 | leitores de `docker logs`: `read_docker_team_snapshot` (`start_match.py:465`), `wait_for_next_map_warmup` (`start_match.py:1162`), `tail_docker_logs` (`watcher.py:318`) e `tools/live_watch.py:61`; depois de 26/09 vieram `start_match.py:211` e `start_match.py:1060` | Cada leitor faz um trabalho vivo diferente; consolidável no mecanismo (S5.2, S7.5), não removível | S1.9 | Victor |
| orquestracao-46 | `bot_difficulty`, `custom_bot_difficulty`, `sv_auto_adjust_bot_difficulty` e os thresholds (`gamemode_competitive_server.cfg:14-18`) | "Sem efeito" só pela documentação, sem medição; bots anônimos e a quota podem depender deles; a linha 16 (`false`) provavelmente segura as lineups nomeadas | S1.9 (o dump de cvars em janela é para este) | Victor, em janela |
| orquestracao-51 | `stdin_open` e `tty` (`docker-compose.yml:112-113`) | `tty: true` muda o buffer do stdout que chega ao `docker logs`, que o watcher lê ao vivo; nunca testado sem | S1.9 (só uma partida de teste ao vivo fecha) | Victor, em janela |

## Como esta lista é mantida

- Linha muda de status (refutado → removível, incerto → confirmado ou refutado, preservado → removível) só por veredito novo registrado no Histórico do card que o produziu, e por PR de docs que atualiza esta lista com o `atualizado` novo.
- O PR de poda que tira um item que estava aqui linka a linha atualizada desta lista.
- A lista nunca encolhe por ser inconveniente: uma linha só sai quando a condição dela foi satisfeita e registrada.
- Decisão nova do Victor (Q11 no S1.4, uma revisão da Q13 ou da Q14) entra no ADR-0006 primeiro e aqui depois.
