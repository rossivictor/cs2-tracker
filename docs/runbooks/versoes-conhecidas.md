---
tipo: runbook
status: vigente
fontes:
  - "docs/runbooks/trilha-de-bots.md:32-47 (máscaras no efcaa42)"
  - "docs/runbooks/trilha-de-bots.md:203-226 (critério 8: variante do VPK pelo sha256 lido no volume)"
  - "docs/runbooks/trilha-de-bots.md:329-361 (registro G6 e G7)"
  - "docs/runbooks/trilha-de-bots.md:376-400 (épocas)"
  - "backup:../2026-10-12/g7-candidato-9-copia/logs/janelas/2026-09-28.md (linhas 7-13: sha256 das três variantes e o RoundDamageRecap 1.2.0; cópia do registro fora do git)"
  - "backup:../2026-10-12/g7-candidato-9-copia/logs/janelas/2026-09-28.md (linha 26: as três variantes relidas na janela VPK Low)"
  - "docs/runbooks/b1.4b-botaimimprover-upstream.md:17-32"
  - "docs/runbooks/b1.9-botrandomizer-upstream.md:30-36"
  - "docker-compose.yml:34-36"
  - "commit efcaa42"
  - "backup:MANIFESTO.sha256 (repo-local/plugin-dll)"
  - "backup:2026-10-01/g7-2000922-partida/sha-montados.txt (coleta G7 da partida 36)"
  - "commit 0472994"
  - "backup:../2026-10-02/janela0/sha-comparacao-boot1.txt (Janela 0: 14 montados = checkout)"
  - "backup:../2026-10-02/janela0/fechamento-sha-container.txt"
  - "backup:../2026-10-02/janela0/depois-medicoes.txt (compose 46b77848 e config-hash)"
  - "backup:../2026-10-02/janela0/final-medicoes.txt"
  - "commit 214b25b"
  - "commit 063b8a4 (tag jogavel-2026-10-03)"
  - "backup:../2026-10-03/coleta-g7-b0.8-0015/docker-logs.txt (build 2000922, Metamod 2.0.0.1469, CSSharp v1.0.375, 8 Finished loading, nenhum anúncio de dificuldade)"
  - "backup:../2026-10-03/coleta-g7-b0.8-0015/config-hash.txt (igual ao config-hash-janela.txt)"
  - "backup:../2026-10-03/coleta-g7-b0.8-0015/sha-montados.txt (contra sha-referencia.txt)"
  - "docs/runbooks/inventario-volume.md:158-159 (VPK ativo Low na Janela 0)"
  - "commit 5a50fcb (candidato-9, T1.3c)"
  - "commit abd19aa (tag jogavel-2026-10-12; mensagem da tag)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.LEIAME.txt (log reconstruído por --tail)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.txt (builds 2000924 e 2000930, Metamod 2.0.0.1469, CSSharp v1.0.375, 8 Finished loading por boot, nenhum anúncio de dificuldade)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/sha-montados.txt (contra sha-referencia.txt)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/config-hash.txt (igual ao config-hash-janela.txt)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/container-inspect.txt (Created 2026-10-02T03:30:20Z)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/head.txt (abd19aa)"
  - "commit db59470 (candidato-10, P1.1)"
  - "commit 40b3826 (tag jogavel-2026-10-13; mensagem da tag)"
  - "backup:../2026-10-13/coleta-g7-p1.1/docker-logs-reconstruido.LEIAME.txt (log reconstruído por --tail; container sem reinício desde 12/10 21:37:09Z)"
  - "backup:../2026-10-13/coleta-g7-p1.1/docker-logs-reconstruido.txt (build 2000930, 8 Finished loading no boot, nenhum anúncio de dificuldade)"
  - "backup:../2026-10-13/coleta-g7-p1.1/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt)"
  - "backup:../2026-10-13/coleta-g7-p1.1/skins-extrato.txt (regressão do BotRandomizer na 2000930)"
  - "backup:../2026-10-13/janela-diag/libserver-2000930/LEIAME.txt (build 2000930, PatchVersion 1.41.9.0, VersionDate Oct 08 2026; cópia de 13/10 22:52)"
  - "backup:../2026-10-13/janela-diag/libserver-2000930/libserver.so.sha256 (sha256 da cópia)"
  - "backup:../2026-10-13/janela-diag/t0-2248.txt (tamanho, mtime e sha256sum do libserver.so dentro do container)"
  - "backup:../2026-10-13/janela-diag/sha-comparacao.txt (janela de diagnóstico: 19 montados iguais ao checkout)"
  - "commit 2619d70 (candidato-13 e tag jogavel-2026-10-14-3; mensagem da tag)"
  - "backup:../2026-10-14/g7-b1.7-copia/logs/janelas/2026-10-14.md (linhas 95-118: janela do B1.7, build 2000931, libserver d73f5d3b, G6 e config-hash 837cbcbc)"
  - "backup:../2026-10-14/coleta-g7-b1.7/docker-logs.txt (build 2000931, m_gameState 0x50F8 e Applied 40/40 no boot, 3 Error invoking callback do BotBuyPatch no changelevel)"
  - "backup:../2026-10-14/coleta-g7-b1.7/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt)"
  - "backup:../2026-10-14/b1.7/libserver-2000931/LEIAME.txt (build 2000931, PatchVersion 1.41.9.1, VersionDate Oct 14 2026)"
  - "backup:../2026-10-14/g7-b1.7-copia/docker/events-live/events_83_map0.jsonl (12 bomb_planted, 3 de bot e 9 do Victor; 2 bomb_defused, os dois de bot; contados pelo steamid, só leitura)"
  - "commit b8b492f (tag jogavel-2026-10-14; mensagem da tag)"
  - "commit eb4cb0e (candidato-12 e tag jogavel-2026-10-14-2; mensagem da tag)"
  - "backup:../2026-10-14/coleta-g7-p1.1a/docker-logs-reconstruido.LEIAME.txt (log reconstruído por --tail; Created 2026-10-02T03:30:20Z, StartedAt 2026-10-14T21:09:39Z, RestartCount 0)"
  - "backup:../2026-10-14/coleta-g7-p1.1a/r14-limpo.txt (build 2000930, 8 Finished loading no boot, 1 Failed to prepare a weapon item view, StartLive 21:11:04Z)"
  - "backup:../2026-10-14/coleta-g7-p1.1a/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt)"
  - "backup:../2026-10-14/g7-b1.7-copia/logs/janelas/2026-10-14.md (linhas 40-51: janela do B1.9b, DLL cfe7efc0, G6 e smoke)"
  - "backup:../2026-10-14/coleta-g7-b1.9b/docker-logs.txt (build 2000930, 8 Finished loading, 0 Failed to prepare a weapon item view, changelevel de_inferno 22:24:46Z, StartLive 22:26:52Z)"
  - "backup:../2026-10-14/coleta-g7-b1.9b/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt)"
  - "backup:../2026-10-14/g7-b1.9b-copia/logs/partidas/partida_20261014T210938Z.log (partida 81: events_81_map0, 13x3, match_id 46)"
  - "backup:../2026-10-14/g7-b1.9b-copia/logs/partidas/partida_20261014T222443Z.log (partida 82: events_82_map0, 13x2, match_id 47)"
  - "commit 9c9b648 (candidato-14 e tag jogavel-2026-10-16; mensagem das duas tags)"
  - "backup:../2026-10-15/coleta-g7-p1.1b/docker-logs-reconstruido.LEIAME.txt (docker-logs.txt vazio; log reconstruído por --tail, de 2026-10-15T04:07:45Z a 2026-10-16T01:13:13Z, 1 entrada ilegível na fronteira; StartedAt 2026-10-16T00:30:01Z)"
  - "backup:../2026-10-15/coleta-g7-p1.1b/docker-logs-reconstruido.txt (linhas 4-188: SteamCMD de 00:30:03Z a 00:32:41Z, state 0x6, appmanifest removido e verificação de 73389778054 bytes; 342 e 423: m_gameState 0x50F8 e Applied 40/40; 334-438: 9 Finished loading; 616: build 2000933; 779-801: 3 Error invoking callback; 3582: MAP ENDED do matchid 84)"
  - "backup:../2026-10-15/coleta-g7-p1.1b/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt)"
  - "backup:../2026-10-15/g7-p1.1b-copia/logs/partidas/partida_20261016T003001Z.log (partida 84: events_84_map0, 13x5, match_id 49, 19 rounds)"
  - "commit 1b5b5d3 (candidato-15 e tag jogavel-2026-10-17; mensagem das duas tags)"
  - "backup:../2026-10-17/g7-p1.2-copia/logs/janelas/2026-10-16.md (linhas 4-22: janela do vanilla on, vencida às 15:30:22 no G6; ff 9c9b648 para 1b5b5d3; conferência do B1.7b na 2000933; config-hash 0f3ff2b2; cópia igual ao registro do checkout principal)"
  - "backup:../2026-10-17/g7-p1.2-copia/logs/janelas/2026-10-17.md (linhas 4-25: janela do vanilla off, 9 Finished loading, Applied 40/40, sha 17/17, config-hash 837cbcbc = H_off)"
  - "backup:../2026-10-16/p1.2/on-config-hash-janela.txt (0f3ff2b2, vanilla on; H_off.txt da mesma pasta: 837cbcbc)"
  - "backup:../2026-10-16/p1.2/docker-logs-boot-on.limpo.txt (boot do vanilla on: 3 Finished loading, build 2000933)"
  - "backup:../2026-10-16/libserver-2000933/libserver.so.sha256 (d73f5d3b, o mesmo da 2000931; conferencia-2000933.txt ao lado)"
  - "backup:../2026-10-17/p1.2/off-config-hash-janela.txt (837cbcbc, vanilla off; igual ao H_off.txt da mesma pasta)"
  - "backup:../2026-10-17/p1.2/off-container.txt (Created 2026-10-17T19:33:02Z, imagem 1056e003; antes-container.txt da mesma pasta: o container do vanilla on, mesma imagem)"
  - "backup:../2026-10-17/coleta-g7-p1.2/docker-logs.txt (linha 62: already up to date; 208-312: 9 Finished loading, m_gameState 0x50F8 e Applied 40/40; 405: build 2000933; 520-535: loadmatch e changelevel de_inferno; 675-697: 3 Error invoking callback; 760: connect do Victor; 779-781: recv queue overflow; 879: StartLive; 3002: MAP ENDED do matchid 85)"
  - "backup:../2026-10-17/coleta-g7-p1.2/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt; head.txt 1b5b5d3)"
  - "backup:../2026-10-17/g7-p1.2-copia/logs/partidas/partida_20261017T204126Z.log (partida 85: events_85_map0, 13x3, match_id 50; horas em -03)"
  - "backup:../2026-10-17/g7-p1.2-copia/docs/board-cs2/ (Histórico do card 81, P1.2, na cópia do board da coleta de 17/10)"
  - "commit 54ef88d (candidato-16 e tag jogavel-2026-10-19; mensagem das duas tags)"
  - "backup:../2026-10-19/coleta-g7-p1.1c/docker-logs-reconstruido.LEIAME.txt (docker-logs.txt vazio; log reconstruído por --tail em 18 leituras, de 2026-10-18T03:02:10Z a 2026-10-19T19:32:45Z, 2259 linhas, 1 entrada ilegível na fronteira; StartedAt 2026-10-19T18:52:48Z, boot inteiro)"
  - "backup:../2026-10-19/coleta-g7-p1.1c/docker-logs-reconstruido.txt (linha 15: already up to date; 160-265: MatchZy LOADED e 9 Finished loading; 169 e 250: m_gameState 0x50F8 e Applied 40/40; 348-355: loadmatch; 423: build 2000933; 457: changelevel de_ancient; 625: SIGNONSTATE_FULL; 688: StartLive; 2147-2149: MAP ENDED e MATCH ENDED do matchid 88; 2155-2163: DISCONNECT_BY_USER)"
  - "backup:../2026-10-19/coleta-g7-p1.1c/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt; head.txt 54ef88d)"
  - "backup:../2026-10-19/g7-p1.1c-copia/logs/partidas/partida_20261019T185248Z.log (partida 88: events_88_map0, 13x4, match_id 53, 18 rounds; horas em -03)"
  - "backup:../2026-10-19/g7-p1.1c-copia/docs/board-cs2/ (Histórico do card 80,8, P1.1c, na cópia do board da coleta de 19/10; Histórico do card 81 com o Restarts 0 da partida 85)"
  - "commit 0164cc3 (candidato-17 e tag jogavel-2026-10-19-2; mensagem das duas tags)"
  - "backup:../2026-10-19/coleta-g7-p1.1d/docker-logs-reconstruido.LEIAME.txt (docker-logs.txt vazio; log reconstruído por --tail em 30 leituras, de 2026-10-18T03:02:10Z a 2026-10-19T20:49:07Z, 4601 linhas; 2 fronteiras, uma com 1 entrada ilegível e outra sem leitura vazia; StartedAt 2026-10-19T18:52:48Z, boot inteiro)"
  - "backup:../2026-10-19/coleta-g7-p1.1d/docker-logs-reconstruido.txt (linhas 1-2259 iguais às do reconstruído do P1.1c; 2475-2482: loadmatch; 2490: changelevel de_dust2; 2630, 2641 e 2652: 3 Error invoking callback do BotBuyPatch; 2705: SIGNONSTATE_FULL; 2796: StartLive; 4488-4490: MAP ENDED e MATCH ENDED do matchid 89; 4496-4504: DISCONNECT_BY_USER)"
  - "backup:../2026-10-19/coleta-g7-p1.1d/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt; head.txt 0164cc3)"
  - "backup:../2026-10-19/g7-p1.1d-copia/logs/partidas/partida_20261019T200739Z.log (partida 89: container já rodando, events_89_map0, 13x7, match_id 54, 21 rounds com o 1 abortado; horas em -03)"
  - "backup:../2026-10-19/g7-p1.1d-copia/docs/board-cs2/ (Histórico do card 80,9, P1.1d, na cópia do board da coleta de 19/10, até o merge; a coleta e o G7 estão no Histórico do board)"
  - "commit a32ef5e (candidato-18 e tag jogavel-2026-10-19-3, do par P1.3 + P1.4; mensagem das duas tags)"
  - "backup:../2026-10-19/coleta-g7-p1.3-p1.4/docker-logs-reconstruido.LEIAME.txt (docker-logs.txt vazio; log reconstruído por --tail em 24 leituras, de 2026-10-18T03:02:10Z a 2026-10-20T02:29:17Z, 22747 linhas; 1 fronteira, com 1 entrada ilegível; StartedAt 2026-10-19T18:52:48Z, boot inteiro)"
  - "backup:../2026-10-19/coleta-g7-p1.3-p1.4/docker-logs-reconstruido.txt (20334-20341: loadmatch; 20349: changelevel de_anubis; 20486, 20497 e 20508: 3 Error invoking callback do BotBuyPatch; 20554: SIGNONSTATE_FULL; 20582-20590: DISCONNECT_BY_USER no warmup; 20613: SIGNONSTATE_FULL da volta; 20702: StartLive; 22636-22638: MAP ENDED e MATCH ENDED do matchid 91; 22644-22652: DISCONNECT_BY_USER)"
  - "backup:../2026-10-19/coleta-g7-p1.3-p1.4/sha-montados.txt (contra sha-referencia.txt; config-hash.txt igual ao config-hash-janela.txt; head.txt a32ef5e)"
  - "backup:../2026-10-19/coleta-g7-p1.3-p1.4/partida_20261020T013216Z.log (partida 91: container já rodando, [CAPTURA] carregado às 22:32:17, events_91_map0, 13x3, match_id 56, 17 rounds com o 1 abortado, [REPORT] e [HOME] às 23:17:55; horas em -03)"
  - "backup:../2026-10-19/g7-p1.3-p1.4-copia/logs/janelas/2026-10-19.md (linha 59: ff manual do servidor para a32ef5e às 22:20, em detach, sem janela; cópia igual ao registro do checkout principal)"
  - "backup:../2026-10-19/g7-p1.3-p1.4-copia/docs/board-cs2/ (Históricos dos cards 82, P1.3, e 83, P1.4, na cópia do board da coleta de 19/10; o G7 está no Histórico do board)"
  - "commit 9e5ab8e (candidato-19, do P1.6; mensagem da tag)"
  - "commit c228d93 (candidato-20 e tag jogavel-2026-10-20, do par P1.5 + P1.6; mensagem das duas tags)"
  - "backup:../2026-10-20/coleta-g7-p1.5-p1.6/ (coleta pós-partida de 20/10, 15:16 em -03, sem janela, preflight 0: docker-logs.txt vazio, log reconstruído por --tail em 8 leituras, 0 fronteira e 0 entrada ilegível, boot inteiro; StartedAt 2026-10-20T16:49:06Z, RestartCount 0; 21 montados iguais ao checkout; config-hash 837cbcbc igual ao do compose; números e horários como o servidor e o QA os transcreveram nos Históricos dos cards 84 e 85)"
  - "backup:../2026-10-20/g7-p1.5-p1.6-copia/ (cópia só leitura da coleta de 20/10, sobre a qual o QA rodou o evidencia_partida.py: events_93_map0, id 58, e events_93_map1, id 59)"
  - "commit 29bf60f (candidato-21, do par P1.7 + P1.8, reprovado pela partida 95; mensagem da tag)"
  - "commit 6b95c77 (merge do PR #107, com o revert 1f49fa5 do par P1.7 + P1.8)"
  - "commit 69c45b1 (candidato-22 e tag jogavel-2026-10-21, do par refeito P1.7 + P1.8; mensagem das duas tags)"
  - "backup:../2026-10-20/coleta-g7-p1.7-p1.8/ (coleta da partida 95, 20/10 22:35 em -03, sem janela, preflight 0: docker-logs.txt vazio, log reconstruído por --tail em 9 leituras, 0 fronteira e 0 entrada ilegível; StartedAt 2026-10-20T16:49:06Z; números como o servidor e o QA os transcreveram nos Históricos dos cards 86 e 87)"
  - "backup:../2026-10-21/coleta-g7-p1.7-p1.8-v2/ (coleta da partida 96, 21/10 19:42 em -03, sem janela, preflight 0: docker-logs.txt vazio, log reconstruído por --tail em 7 leituras, 6432 linhas, 0 fronteira e 0 entrada ilegível; StartedAt 2026-10-21T21:57:21Z, RestartCount 0; 21 montados iguais ao checkout; config-hash.txt igual ao config-hash-janela.txt; head.txt 69c45b1; números e horários como o servidor e o QA os transcreveram nos Históricos dos cards 86 e 87)"
  - "backup:../2026-10-21/coleta-g7-p1.7-p1.8-v2/docker-logs-desde-startedat.LEIAME.txt (recorte do reconstruído no StartedAt, 4478 de 6432 linhas; o G7 se julga por ele)"
  - "backup:../2026-10-21/coleta-g7-p1.7-p1.8-v2/docker-logs-desde-startedat.txt (153: Success! App '730' fully installed às 22:01:57Z; 644: GC Connection established for server version 2000934; 952: StartLive às 22:04:00Z; 4361: MAP ENDED do matchid 96 às 22:30:50Z)"
  - "backup:../2026-10-21/g7-p1.7-p1.8-v2-copia/ (cópia só leitura da coleta de 21/10, sobre a qual o QA rodou o evidencia_partida.py: events_96_map0, id 63)"
  - "commit ba17644 (candidato-23, do P1.10; mensagem da tag, com a DLL 697760a7 da 0.4.0 por engano)"
  - "commit a0b4dca (candidato-24, do B1.3s; mensagem da tag, com a DLL 75d0d6df)"
  - "commit cc17bb4 (tag jogavel-2026-10-25, do par B1.3s + P1.10; mensagem da tag)"
  - "backup:../2026-10-25/g7-b1.3s-p1.10-copia/logs/janelas/2026-10-22.md (linhas 7-14: ff para ba17644, build da DLL 0.4.1 com o container parado, manifesto e a nota do candidato.json; 30-31: recreate e build 2000935; 36-42: G6, config-hash 837cbcbc, conferência do BotAI na 2000935 e VPK Low lido; cópia igual ao registro do checkout principal)"
  - "backup:../2026-10-25/g7-b1.3s-p1.10-copia/logs/janelas/2026-10-23.md (linhas 28-40: quedas de 23/10, smoke só de bots, NadeSystem, vanilla on e G6 com config-hash 0f3ff2b2; cópia igual ao registro do checkout principal)"
  - "backup:../2026-10-25/g7-b1.3s-p1.10-copia/logs/janelas/2026-10-24.md (linhas 10-19: queda de 24/10, zip conferido e o PARE do dono; cópia igual ao registro do checkout principal)"
  - "backup:../2026-10-25/g7-b1.3s-p1.10-copia/logs/janelas/2026-10-25.md (linhas 22-79: janela de 25/10 15:01, instalação da CSSharp v1.0.378, G6 e fechamento; a linha 80 do registro do checkout principal, a da coleta, veio depois da cópia)"
  - "backup:../2026-10-23/janela-1918/docker-logs-antes.txt (linhas 311 e 740: build 2000935 no recreate de 22/10; 1652-1653, 1990-2019 e 2694-2695: as três quedas de 23/10)"
  - "backup:../2026-10-24/b1.3s/docker-logs-antes.txt (linhas 1422-1423: SIGNONSTATE_SPAWN e segfault de 24/10)"
  - "backup:../2026-10-22/conferir_botai_2000935.txt (conferência do BotAI do fork na 2000935: RESULTADO: OK, 40/40)"
  - "backup:../2026-10-25/b1.3s-1501/g7-1541/ (coleta da partida 97, 25/10 15:41 em -03, sem janela, preflight 0: docker-logs.txt completo desde o StartedAt 2026-10-25T18:04:16Z, 1882 linhas, sem --tail; head.txt cc17bb4; config-hash.txt igual ao config-hash-janela.txt; 16 montados contra 7 arquivos de sha-referencia.txt)"
  - "backup:../2026-10-25/b1.3s-1501/g7-1541/docker-logs.txt (106: already up to date; 116: CSSharp v1.0.378; 251: MatchZy LOADED; 433: build 2000935; 613: LoadMatchFromJSON -1; 791 e 795: SPAWN e FULL do humano; 879: StartLive; 1763-1765: MAP ENDED e MATCH ENDED do matchid 97; 1780: saída do humano)"
  - "backup:../2026-10-25/g7-b1.3s-p1.10-copia/ (cópia só leitura da coleta de 25/10, sobre a qual o QA rodou o evidencia_partida.py: events_97_map0, id 64)"
  - "commit c67e548 (candidato-25, do par P1.9 + P1.11)"
  - "commit 09e54bd (tag jogavel-2026-10-26: o candidato-25 com o P1.9b, PR #119)"
  - "commit 57e357b (candidato-26 e tag jogavel-2026-10-26-2, do B1.13)"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-26.md (linhas 10-29: janela de 09:52, ff para 09e54bd, runtime semeado, recreate com o SteamCMD falho e G6 com FALTA; 53-65: janela de 11:01, G6 completo pela RCON; 67-72: coleta da partida 100; 118-135: janela do B1.13, vanilla off, G6 por plugin, smoke e residual apagado; cópia igual ao registro do checkout principal nessas linhas, e as 137-146 do registro, a coleta da partida 101, vieram depois da cópia)"
  - "backup:../2026-10-26/p1.9-p1.11/ (janela de 09:52: antes-portbindings.json, depois-port.txt, config-hash-novo-vanilla.txt, runtime-semeado-sha.txt e boot1-falhou-steamcmd.log)"
  - "backup:../2026-10-26/p1.9-p1.11/g7-1327/ (coleta da partida 100, 26/10 13:27 em -03, sem janela, preflight 0: docker-logs.txt desde o StartedAt 2026-10-26T13:04:13Z, 1990 linhas; head.txt 09e54bd; config-hash.txt igual ao config-hash-janela.txt; 16 montados contra 7 arquivos de sha-referencia.txt)"
  - "backup:../2026-10-26/p1.9-p1.11/g7-1327/docker-logs.txt (105-106: CSSharp v1.0.378; 241: MatchZy LOADED; 423: build 2000935; 682: LoadMatchFromJSON às 15:52:19Z; 856: FULL do humano; 943: StartLive às 15:53:25Z; 1877-1879: MAP ENDED e MATCH ENDED às 16:15:56Z; 1892-1893: saída do humano)"
  - "backup:../2026-10-26/b1.13/ (janela de 13:48: MANIFESTO.sha256 do NadeSystem, 51 linhas, sha256 facbe9df…; config-hash-janela.txt; sha-montados.txt)"
  - "backup:../2026-10-26/b1.13/g7-1441/ (coleta da partida 101, 26/10 14:41 em -03, sem janela, preflight 0: docker-logs.txt desde o StartedAt 2026-10-26T16:50:32Z, 3743 linhas; head.txt 57e357b; config-hash.txt igual ao config-hash-janela.txt; 72 montados contra 69 arquivos de sha-referencia.txt)"
  - "backup:../2026-10-26/b1.13/g7-1441/docker-logs.txt (93: already up to date; 238: MatchZy LOADED; 328: Applied 40/40; 331: NadeSystem Loaded; 436: build 2000935; 1513: LoadMatchFromJSON às 17:03:45Z; 1721 e 1724: SPAWN e FULL do humano; 1825: StartLive às 17:05:05Z; 3631-3633: MAP ENDED e MATCH ENDED às 17:29:49Z; 3645-3646: saída do humano)"
  - "backup:../2026-10-26/g7-p1.9-p1.11-copia/ (cópia só leitura da coleta de 26/10, sobre a qual o QA rodou o evidencia_partida.py: events_100_map0, id 67)"
  - "backup:../2026-10-26/g7-b1.13-copia/ (cópia só leitura da coleta de 26/10, sobre a qual o QA rodou o evidencia_partida.py: events_101_map0, id 68; Históricos dos cards 88, 88,5, 90 e 29,97 na cópia do board)"
  - "commit e4fb9d5 (candidato-27, objeto de tag 2b8ea918: K1.9, PRs #121 e #125; mensagem da tag)"
  - "commit f16121f (tag jogavel-2026-11-04, objeto de tag 121ff5fc: o candidato-27 com o runbook do B1.15, PR #126; mensagem da tag)"
  - "backup:../2026-11-04/janela-build/ (janela de 12:09: antes-*, docker-logs-antes.txt e o boot da 2000940; o registro das duas janelas e da coleta é o logs/janelas/2026-11-04.md, só no checkout principal: linhas 16-52, janela de 12:09, build 2000935 → 2000940 com a válvula on; 68-124, janela de 17:41 do K1.9 + B1.15, ff até f16121f, vanilla off, G6 por plugin, smoke e fechamento; 126-136, coleta da partida 107 e as duas entradas que caíram por overflow no signon)"
  - "backup:../2026-11-04/build-nova/MANIFESTO.sha256 (libserver-2000940.so 41807736 B, sha256 503c5b0e…; gamedata-1.0.378.json 62bd8c4f…)"
  - "backup:../2026-11-04/b1.15/ (janela de 17:41: conferir_botai_2000940.txt 973a6ed0…, conferencia-2000940.txt 9a180778…, docker-logs-boot.txt, docker-logs-smoke.txt, fechamento-config-hash.txt e sha-fechamento.txt; docker-logs-antes.txt com o overflow de 17:34Z, válvula on)"
  - "backup:../2026-11-04/partida-k19-b115/coleta/ (coleta da partida 107, 04/11 18:40 em -03, sem janela, preflight 0: docker-logs.txt desde o StartedAt 2026-11-04T20:44:37Z, 4370 linhas, sem --tail; head.txt f16121f; config-hash.txt igual ao config-hash-janela.txt; 72 montados contra 69 arquivos de sha-referencia.txt)"
  - "backup:../2026-11-04/partida-k19-b115/coleta/docker-logs.txt (98: already up to date; 333: Bot AI - Patches; 336-337: m_gameState e Applied 40/40; 523: build 2000940; 1678: LoadMatchFromJSON às 21:05:07Z; 1824-1846: os 3 Error invoking callback do BotBuyPatch; 1920 e 1930-1935: FULL da 1ª entrada e overflow de 1218 ms; 2006: FULL da 2ª entrada; 2106: StartLive às 21:07:43Z; 4251-4253: MAP ENDED e MATCH ENDED do matchid 107 às 21:28:51Z; 4259-4267: saída do humano)"
  - "backup:../2026-11-04/partida-k19-b115/ (cópia só leitura do banco, integrity ok, 72 partidas, sobre a qual o QA rodou o evidencia_partida.py: events_107_map0, id 77; Históricos dos cards 78 e 29,99 no board)"
  - "backup:../2026-11-04/partida-k19-b115/cs2_tracker.backup.db (lido em mode=ro em 05/11, P1.21: matches id 77, events_107_map0, de_dust2, score_mine 13, score_theirs 1, score_source rounds, outcome win; o 13x1 também no Histórico do card 78, 04/11 18:49)"
  - "commit 110bb98 (candidato-28: P1.15, o start_match com o container pausado, PR #128)"
  - "commit e80611e (tag jogavel-2026-11-04-2, objeto de tag 5446978: o candidato-28 com o P1.19, o V1.2 e o P1.20, PRs #129 a #131, sem caminho de jogo; mensagem da tag)"
  - "backup:../2026-11-04/partida-p115/coleta/ (coleta da partida 108, 04/11 21:11 em -03, sem janela, preflight 0: docker-logs.txt desde o StartedAt 2026-11-04T20:44:37Z, 7542 linhas, sem --tail; head.txt e80611e; config-hash.txt igual ao config-hash-janela.txt; 72 montados contra 69 arquivos de sha-referencia.txt; o registro é o logs/janelas/2026-11-04.md, linhas 138-148, só no checkout principal)"
  - "backup:../2026-11-04/partida-p115/coleta/docker-logs.txt (5089: LoadMatchFromJSON às 23:34:15Z; 5318-5319: FULL do humano e 419 ms, sem DISCONNECTING; 5416: StartLive às 23:36:01Z; 7430-7432: MAP ENDED e MATCH ENDED do matchid 108 às 00:00:07Z; 7439-7445: saída do humano)"
  - "backup:../2026-11-04/partida-p115/cs2_tracker.backup.db (cópia só leitura do banco, integrity ok, 73 partidas, lida em mode=ro: matches id 78, events_108_map0, de_mirage, score_mine 13, score_theirs 5, score_source rounds; Histórico do card 92,6 no board)"
  - "commit dff4222 (tag jogavel-2026-11-08, objeto de tag cc589db0: merge do PR #138, S1.1; o B1.16 não tem commit nem candidato)"
  - "commit 29087da (candidato-29 e tag jogavel-2026-11-09, objeto de tag 4692d8ae: merge do PR #139, B1.17)"
  - "backup:../2026-11-05/build-2000942/ (janela de 05/11 18:25: antes-*, depois-*, docker-logs-boot.txt e coleta-g6/; o registro é o logs/janelas/2026-11-05.md, só no checkout principal: build 2000940 → 2000942 com a válvula on, janela vencida às 19:10:30 e G6 completado só de leitura às 21:04)"
  - "backup:../2026-11-06/b1.16/ (janela de 06/11 17:34, card B1.16: MANIFESTO.sha256 com o libserver-2000942.so de 41850680 B ee0cc32a…, conferir_botai_2000942.txt 7dfef426…, conferencia-2000942.txt 8729e9d9…, antes-vpk.txt e depois-vpk.txt, docker-logs-boot.txt, docker-logs-smoke.txt e fechamento-*; o registro é o logs/janelas/2026-11-06.md, só no checkout principal)"
  - "backup:../2026-11-08/partida-b116/coleta/ (coleta da MD3 112, 08/11 17:31 em -03, sem janela, preflight 0: docker-logs.txt desde o StartedAt 2026-11-08T14:01:08Z, 6963 linhas; docker-logs-desde-created.txt desde 2026-11-06T20:39:17Z; head.txt dff4222; config-hash.txt igual ao config-hash-janela.txt; 72 montados contra 69 arquivos de sha-referencia.txt; vpk-ativo.txt Medium às 20:33:52Z; Histórico do card 29,991 no board)"
  - "backup:../2026-11-08/b1.17/ (janela de 08/11 19:04, card B1.17: delta.txt, antes-* e depois-*, docker-logs-boot.txt, docker-logs-smoke.txt, depois-vpk.txt e fechamento-*; o registro é o logs/janelas/2026-11-08.md, só no checkout principal)"
  - "backup:../2026-11-09/partida-b117/coleta/ (coleta das partidas 113 e 114, 09/11, sem janela, preflight 0: docker-logs.txt desde o StartedAt 2026-11-09T16:54:51Z, 7467 linhas; head.txt 29087da; config-hash.txt igual ao config-hash-janela.txt; 70 montados contra 66 arquivos de sha-referencia.txt; sha-vpk.txt com o ativo Medium; Histórico do card 29,992 no board)"
atualizado: 2026-11-09
---

# Versões conhecidas

> **Para quem:** o papel servidor, na volta ao jogável e na Janela 0; o tech-manager, ao criar uma tag `jogavel-*`; o QA, ao conferir uma coleta.
> **Card:** B0.3. Cada tag registrada aqui é uma combinação em que o Victor jogou ([ADR-0004](../adr/0004-jogo-sempre-jogavel.md)).

A volta ao jogável precisa saber qual combinação era a boa, e até aqui essa informação estava espalhada em commits, runbooks e registros de janela. Esta nota junta tudo por tag.

Convenções:

- sha256 aparece abreviado (8 caracteres) nas tabelas. O valor inteiro está em [Hashes completos](#hashes-completos).
- **não registrado** quer dizer que nenhuma fonte guardou o valor. A nota diz de onde ele viria. Nenhum valor daqui é estimado.
- Fontes fora do git: os registros de janela em `logs/janelas/2026-09-27.md`, `2026-09-28.md`, `2026-09-30.md`, `2026-10-02.md`, `2026-10-13.md`, `2026-10-14.md`, `2026-10-16.md`, `2026-10-17.md`, `2026-10-19.md`, `2026-10-22.md`, `2026-10-23.md`, `2026-10-24.md`, `2026-10-25.md`, `2026-10-26.md`, `2026-11-04.md`, `2026-11-05.md`, `2026-11-06.md` e `2026-11-08.md` (checkout principal), as coletas em `C:/Users/Victor/cs2-tracker-backups/2026-09-27/`, `2026-09-28/`, `2026-10-01/`, `2026-10-02/`, `2026-10-03/`, `2026-10-12/`, `2026-10-13/`, `2026-10-14/`, `2026-10-15/`, `2026-10-16/`, `2026-10-17/`, `2026-10-19/`, `2026-10-20/`, `2026-10-21/`, `2026-10-22/`, `2026-10-23/`, `2026-10-24/`, `2026-10-25/`, `2026-10-26/`, `2026-11-04/`, `2026-11-05/`, `2026-11-06/`, `2026-11-08/` e `2026-11-09/`, e os Históricos do card 17 (B0.8), do card 62,7 (T1.3c), do card 80 (P1.1), do card 26 (B1.7), do card 80,7 (P1.1b), do card 81 (P1.2), do card 80,8 (P1.1c), do card 80,9 (P1.1d), dos cards 82 (P1.3) e 83 (P1.4), dos cards 84 (P1.5) e 85 (P1.6), dos cards 86 (P1.7) e 87 (P1.8), dos cards 22,5 (B1.3s) e 89 (P1.10), do card 25,8 (B1.7c), dos cards 88 (P1.9), 88,5 (P1.9b) e 90 (P1.11), do card 29,97 (B1.13), dos cards 78 (K1.9) e 29,99 (B1.15), do card 92,6 (P1.15) e dos cards 29,991 (B1.16) e 29,992 (B1.17) no board.
  Nas tabelas, `b1.x/...` é relativo a `2026-09-27/`, a coleta da partida 36 aparece como `2026-10-01/g7-2000922-partida/`, a da Janela 0 como `2026-10-02/janela0/`, a do G7 do B0.8 como `2026-10-03/coleta-g7-b0.8-0015/`, a do G7 do `candidato-9` como `2026-10-12/coleta-g7-candidato-9/`, a do G7 do `candidato-10` como `2026-10-13/coleta-g7-p1.1/`, a da janela de diagnóstico do B1.12b como `2026-10-13/janela-diag/`, a do G7 do `candidato-11` como `2026-10-14/coleta-g7-p1.1a/`, a da janela do B1.9b como `2026-10-14/b1.9b/`, a do G7 do `candidato-12` como `2026-10-14/coleta-g7-b1.9b/`, a da janela do B1.7 como `2026-10-14/b1.7/`, a do G7 do `candidato-13` como `2026-10-14/coleta-g7-b1.7/`, a do G7 do `candidato-14` como `2026-10-15/coleta-g7-p1.1b/`, as das janelas do P1.2 como `2026-10-16/p1.2/` (vanilla on) e `2026-10-17/p1.2/` (vanilla off), a do G7 do `candidato-15` como `2026-10-17/coleta-g7-p1.2/`, a do G7 do `candidato-16` como `2026-10-19/coleta-g7-p1.1c/`, a do G7 do `candidato-17` como `2026-10-19/coleta-g7-p1.1d/` a do G7 do `candidato-18` como `2026-10-19/coleta-g7-p1.3-p1.4/`, a do G7 do `candidato-20` como `2026-10-20/coleta-g7-p1.5-p1.6/`, a do G7 do `candidato-21` (reprovado) como `2026-10-20/coleta-g7-p1.7-p1.8/`, a do G7 do `candidato-22` como `2026-10-21/coleta-g7-p1.7-p1.8-v2/`, a da janela do B1.3s como `2026-10-25/b1.3s-1501/`, a do G7 do par `candidato-23` + `candidato-24` como `2026-10-25/b1.3s-1501/g7-1541/`, a da janela da build 2000940 como `2026-11-04/janela-build/`, a da janela do K1.9 + B1.15 como `2026-11-04/b1.15/`, a do G7 do `candidato-27` como `2026-11-04/partida-k19-b115/coleta/` a do G7 do `candidato-28` como `2026-11-04/partida-p115/coleta/`, a da janela da build 2000942 como `2026-11-05/build-2000942/`, a da janela do B1.16 como `2026-11-06/b1.16/`, a do G7 do B1.16 como `2026-11-08/partida-b116/coleta/`, a da janela do B1.17 como `2026-11-08/b1.17/` e a do G7 do `candidato-29` como `2026-11-09/partida-b117/coleta/`.

## O que não mudou em nenhuma tag

| Item | Valor | Fonte |
|---|---|---|
| Imagem | `xbird/cs2-matchzy`, sem tag no compose (vale a `latest` local). Digest `sha256:1056e003…`, o mesmo de 27/09 01:44 (antes do B1.3r) a 30/09 23:05 (janela da build 2000922). O container de 28/09 durou até a partida 36: na coleta dela (01/10) o `Created` segue `2026-09-28T01:30:07Z`. A Janela 0 (02/10, B0.8) o recriou: desde então o `Created` é `2026-10-02T03:30:20Z` (coleta de 12/10). As janelas de 14/10 (B1.9b e B1.7) o recriaram de novo: o da `jogavel-2026-10-14-3` é de `2026-10-15T00:15:44Z`, e a `jogavel-2026-10-16` jogou no mesmo, reiniciado sem recreate. O digest da imagem nessas janelas: não registrado. As janelas do P1.2 o recriaram mais duas vezes (vanilla on em 16/10, off em 17/10) e leram o digest: `1056e003…`, o mesmo. O da `jogavel-2026-10-17` é de `2026-10-17T19:33:02Z`, e a `jogavel-2026-10-19` jogou no mesmo, subido pelo `start_match` sem recreate (`StartedAt` 2026-10-19T18:52:48Z). A `jogavel-2026-10-19-2` e a `jogavel-2026-10-19-3` jogaram no mesmo e na mesma subida: o `start_match` o achou rodando. A `jogavel-2026-10-20` jogou no mesmo container, sem recreate, numa subida nova: reiniciado às 2026-10-20T16:49:06Z, fora de janela. A `jogavel-2026-10-21` também, sem recreate, em outra subida: a TUI subiu às 2026-10-21T21:57:21Z o container parado pela queda do Docker Desktop. Depois dela, três recreates em janela: 22/10 (`Created` 2026-10-22T22:56:00Z, P1.10), 23/10 (22:25:13Z, vanilla on) e 25/10 (15:04:13 em -03, B1.3s), este com o digest relido: `1056e003…`, igual ao da tag local. A `jogavel-2026-10-25` jogou no de 25/10 (estado no ar) | `b1.3r/antes-container.txt`; registros de janela; `2026-10-01/g7-2000922-partida/estado-container.txt`; `2026-10-12/coleta-g7-candidato-9/container-inspect.txt`; `2026-10-17/p1.2/antes-container.txt` e `off-container.txt`; Históricos dos cards 80,8, 80,9, 82, 83, 84, 85, 86, 87, 22,5 e 89 |
| MatchZy | `0.8.15` (`MATCHZY_FIXED_VERSION`) | compose de todas as tags |
| Captura | CS2 Tracker Events 0.4.0: DLL `697760a7…`, `.deps.json` `137a42f2…`, `.pdb` `ca994b0c…`. A DLL é de 23/09, e o checkout de 26/09 já tinha esse sha. Vale **até a `jogavel-2026-10-21`**: a `jogavel-2026-10-25` tem a 0.4.1 (P1.10), com DLL `75d0d6df…`, `.pdb` `0697c375…` e o mesmo `.deps.json` | `backup:MANIFESTO.sha256`; [manifesto](#manifesto-do-plugin-de-captura) |
| `pre.sh` | `233e5aa0…`. Sem diff entre `efcaa42` e `origin/main` | `git diff --stat efcaa42 origin/main -- docker/pre.sh` vazio |
| `gamemode_competitive_server.cfg` | `aebb5df5…` no disco (CRLF; o blob LF do git é `a0c195ee…`). Sem diff entre `efcaa42` e o `57e357b` (`jogavel-2026-10-26-2`). Na `jogavel-2026-11-04` mudou só em comentário (K1.9, PR #121): `f3b0009c…` no disco do checkout principal e dentro do container, blob LF `7efa151a…` | `git diff --stat efcaa42 57e357b -- server-configs/` vazio; `2026-11-04/partida-k19-b115/coleta/sha-montados.txt`; `git cat-file blob f16121f:server-configs/cfg/gamemode_competitive_server.cfg \| sha256sum` |
| RoundDamageRecap | 1.2.0, do volume, sem máscara, DLL `7075101b…` (instalado em 05/09) | `2026-09-28/vpk-medium/backup.sha256` |
| .NET do CSSharp | 10.0.3 | inventário do B1.3r |

## Tags jogáveis

| Tag | Commit | Build CS2 | Metamod | CSSharp | Plugins de bot ativos | VPK | Partida de evidência |
|---|---|---|---|---|---|---|---|
| `jogavel-2026-09-26` | `efcaa42` | 2000918, lida em 27/09 01:44, antes do B1.3r. Na `events_60`: não registrado (viria do RCON `version` daquele dia) | 2.0.0.1411 | v1.0.373 | nenhum | High | `events_60` (linha de base do B1.6 e do B1.8) |
| `jogavel-2026-09-27` | `6915606` | 2000918 | 2.0.0.1469 | v1.0.375 | nenhum | High | partida 26, `events_63_map0`, de_inferno 13x7 |
| `jogavel-2026-09-27-2` | `88a6cb3` | 2000918 | 2.0.0.1469 | v1.0.375 | BotAimImprover (upstream `c3d10f5`, bind) | Medium | partida 27, `events_64_map0`, de_dust2 13x8 |
| `jogavel-2026-09-27-3` | `b651556` | 2000918 | 2.0.0.1469 | v1.0.375 | + BotState (Smarter-Bot 1.9.4, volume) | Medium | partida 28, `events_65_map0`, de_inferno 13x8 |
| `jogavel-2026-09-27-4` | `e838839` | 2000918 | 2.0.0.1469 | v1.0.375 | + BotBuy (BotBuyPatch 1.0.12, volume) | Medium | partida 29, `events_66_map0`, de_dust2 13x8 |
| `jogavel-2026-09-27-5` | `200e43f` | 2000918 | 2.0.0.1469 | v1.0.375 | + NadeSystem 1.2.1 (volume) | Medium | partida 30, `events_67_map0`, de_dust2 5x13 |
| `jogavel-2026-09-28` | `ee583fc` | 2000918 | 2.0.0.1469 | v1.0.375 | + BotRandomizer 1.3.2 (upstream `276f1ce`, bind) | Medium | partida 31, `events_68_map0`, de_dust2 3x13 |
| `jogavel-2026-10-01` | `0472994` | 2000922 (SteamCMD, janela de 30/09 23:05–23:16) | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-09-28` (8 plugins carregados) | Low | partida 36 (matchid 71), `events_71_map0`, de_ancient 13x7 (MD1, 01/10) |
| `jogavel-2026-10-03` | `063b8a4` | 2000922 | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-01`; 8 plugins carregados: MatchZy, CS2 Tracker Events, RoundDamageRecap, BotAimImprover, Smarter-Bot, BotBuyPatch, NadeSystem e BotRandomizer | Low (`02e5e958…`), por inferência: ver a ressalva abaixo | matchid 74 (id 40 no banco), `events_74_map0`, de_inferno 13x1 (03/10 em UTC, live 02:08–02:29Z; noite de 02/10 em -03) |
| `jogavel-2026-10-12` | `abd19aa` | 2000924 na partida 78 e 2000930 na partida 79, as duas trazidas pelo SteamCMD no boot ([Épocas de build](#épocas-de-build)) | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-03`; 8 plugins carregados em cada boot | Low (`02e5e958…`), por inferência, como na `jogavel-2026-10-03`: ver a ressalva abaixo | partida 78 (matchid 78, id 43 no banco), `events_78_map0`, de_cache 13x8 (05/10, G7 OK); confirmação: partida 79 (matchid 79, id 44 no banco), de_mirage 13x2 (12/10) |
| `jogavel-2026-10-13` | `40b3826` | 2000930 | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-12`; 8 plugins carregados no boot. O BotRandomizer carrega, mas na 2000930 as armas dos bots vêm sem skin: ver a regressão abaixo | Low (`02e5e958…`), por inferência, como na `jogavel-2026-10-12`: ver a ressalva abaixo | partida 80 (matchid 80, id 45 no banco), `events_80_map0`, de_ancient 13x5 (13/10, live 19:08Z–19:38Z, G7 OK) |
| `jogavel-2026-10-14` | `b8b492f` | 2000930 | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-13`; 8 plugins carregados no boot. O BotRandomizer ainda é o do B1.9, com as armas dos bots sem skin (1 `Failed to prepare a weapon item view` no boot): ver a regressão abaixo | Low (`02e5e958…`), por inferência, como na `jogavel-2026-10-13`: ver a ressalva abaixo | partida 81 (matchid 81, id 46 no banco), `events_81_map0`, de_dust2 13x3 (14/10, live desde 21:11Z, G7 OK) |
| `jogavel-2026-10-14-2` | `eb4cb0e` | 2000930 (a mesma antes e depois da janela do B1.9b) | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-14`, com o BotRandomizer b1.9b por bind (`276f1ce` com o `4628750` do upstream, DLL `cfe7efc0…`, [B1.9b](b1.9b-botrandomizer-2000930.md)); 8 plugins carregados no boot e nenhum `Failed to prepare a weapon item view` | Low (`02e5e958…`), por inferência: a janela do B1.9b não escreveu no volume, e a coleta não leu o VPK | partida 82 (matchid 82, id 47 no banco), `events_82_map0`, de_inferno 13x2 (14/10, live desde 22:26Z; validada pela mensagem da tag) |
| `jogavel-2026-10-14-3` | `2619d70` | 2000931 (SteamCMD, no 1º recreate da janela do B1.7, 14/10; [Épocas de build](#épocas-de-build)) | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-13`, com o BotRandomizer b1.9b (DLL `cfe7efc0…`, desde a `jogavel-2026-10-14-2`), + **BotAI** do fork 1.8.12-b1.7b por bind (DLL `8ed65092…`, [B1.7b](b1.7b-botai-fork-assinatura.md)); 9 plugins carregados no boot, BotAI com `Applied 40/40 patches.` | Low (`02e5e958…`), por inferência: as janelas de 14/10 não escreveram no volume, e a coleta não leu o VPK | partida 83 (matchid 83, id 48 no banco), `events_83_map0`, de_nuke 13x3 (14/10 em -03; live 15/10 01:43Z–02:09Z, G7 OK) |
| `jogavel-2026-10-16` | `9c9b648` | 2000933 (SteamCMD no boot de 2026-10-16T00:30:01Z, sem janela; [Épocas de build](#épocas-de-build)) | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-14-3`; 9 plugins carregados no boot, BotAI com `Applied 40/40 patches.`, mas sem a conferência do B1.7b na 2000933: ver a ressalva abaixo | Low (`02e5e958…`), por inferência: nenhuma janela desde as de 14/10, e a coleta não leu o VPK | partida 84 (matchid 84, id 49 no banco), `events_84_map0`, de_anubis 13x5 (15/10 21:34–22:02 em -03; `MAP ENDED` 2026-10-16T01:02:07Z, G7 OK). A data da tag é a da marcação (16/10), não a da partida |
| `jogavel-2026-10-17` | `1b5b5d3` | 2000933, a mesma da `jogavel-2026-10-16`, sem época nova: os boots das duas janelas do P1.2 dizem `already up to date`, e a partida rodou no da janela de 17/10 | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-16`; 9 plugins carregados no boot, BotAI com `Applied 40/40 patches.` A partida jogou com a válvula vanilla **off**: ver o estado no ar | Low (`02e5e958…`), por inferência: as janelas do P1.2 não escreveram no volume, e a coleta não leu o VPK | partida 85 (matchid 85, id 50 no banco), `events_85_map0`, de_inferno 13x3 (17/10, carga 20:41Z, live 21:02Z, fim 21:25Z; 17:41–18:25 em -03, G7 OK). Container do recreate da janela de 17/10, Restarts 0 (Histórico do card 81) |
| `jogavel-2026-10-19` | `54ef88d` | 2000933, a mesma da `jogavel-2026-10-17`, sem época nova: o boot de 19/10 diz `already up to date` | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-17`; 9 plugins carregados no boot (MatchZy, BotBuyPatch, CS2 Tracker Events, Bot AI - Patches, NadeSystem, BotAimImprover, Smarter-Bot, RoundDamageRecap e BotRandomizer), BotAI com `Applied 40/40 patches.` Válvula vanilla **off**: config-hash `837cbcbc…` = H_off | Low (`02e5e958…`), por inferência: nenhuma janela desde a de 17/10, e a coleta não leu o VPK | partida 88 (matchid 88, id 53 no banco), `events_88_map0`, de_ancient 13x4 (19/10, carga 18:53Z, live 18:54Z, fim 19:21Z; 15:52–16:21 em -03, da subida do servidor ao fim; G7 OK). Horários do log reconstruído pelo `--tail` (B0.7h): `docker-logs.txt` vazio, json-file corrompido pela parada noturna, 1 entrada ilegível na fronteira, antes do boot e fora da partida |
| `jogavel-2026-10-19-2` | `0164cc3` | 2000933, a mesma da `jogavel-2026-10-19`, sem época nova: a partida 89 rodou na mesma subida da 88, cujo boot diz `already up to date` | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-19` (9 plugins carregados no boot, BotAI com `Applied 40/40 patches.`). Válvula vanilla **off**: config-hash `837cbcbc…` = H_off, o da `jogavel-2026-10-19` | Low (`02e5e958…`), por inferência: nenhuma janela desde a de 17/10, e a coleta não leu o VPK | partida 89 (matchid 89, id 54 no banco), `events_89_map0`, de_dust2 13x7 (19/10, carga 20:07Z, live 20:09Z, fim 20:37Z; 17:07–17:37 em -03, da TUI, com o container já no ar, ao fim; G7 OK). 13x7 são os 20 rounds que contam: o parser registra 21, com o round 1 abortado (sem `round_end`). Horários do log reconstruído pelo `--tail` (B0.7h), com a ressalva do estado no ar |
| `jogavel-2026-10-19-3` | `a32ef5e` | 2000933, a mesma da `jogavel-2026-10-19-2`, sem época nova: a partida 91 rodou na mesma subida da 88, cujo boot diz `already up to date` | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-19-2` (9 plugins carregados no boot, BotAI com `Applied 40/40 patches.`). Válvula vanilla **off**: config-hash `837cbcbc…` = H_off, o da `jogavel-2026-10-19-2` | Low (`02e5e958…`), por inferência: a janela T2 de 19/10 não escreveu no volume, e a coleta não leu o VPK | partida 91 (matchid 91, id 56 no banco), `events_91_map0`, de_anubis 13x3 (19/10, carga 01:32Z, live 01:54Z, fim 02:17Z, já do dia 20 em UTC; 22:32–23:17 em -03, da TUI, com o container já no ar, ao fim; G7 OK do par P1.3 + P1.4). 13x3 são os 16 rounds que contam: o parser registra 17, com o round 1 abortado. Horários do log reconstruído pelo `--tail` (B0.7h), com a ressalva do estado no ar |
| `jogavel-2026-10-20` | `c228d93` | 2000933, a mesma da `jogavel-2026-10-19-3`, sem época nova: é a build do boot de 2026-10-20T16:49:07Z, em que a MD3 rodou | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-19-3`: 9 plugins carregados no boot (MatchZy 0.8.15, BotBuyPatch, CS2 Tracker Events, Bot AI - Patches com `Applied 40/40`, NadeSystem, BotAimImprover, Smarter-Bot, RoundDamageRecap e BotRandomizer). Válvula vanilla **off**: config-hash `837cbcbc…` = H_off, o da `jogavel-2026-10-19-3` | Low (`02e5e958…`), por inferência: as janelas T2 de 19 e 20/10 não trocaram o VPK, e a coleta não o leu | MD3 de matchid 93 (20/10, 2x0, sem mapa 3): mapa 1 `events_93_map0`, de_inferno 13x5 (id 58 no banco; carga pela TUI das 13:49:54 em -03, logo depois do boot de 16:49:07Z, e fim 17:17:36Z; o carimbo do `StartLive` do mapa 1 não foi transcrito neste registro, e a TUI leu o humano no CT às 13:50:58), e mapa 2 `events_93_map1`, de_cache 16x14 na prorrogação (id 59; `changelevel` 17:18:01Z, live 17:18:16Z sem botão, fim 18:05:41Z; 14:18–15:05 em -03). G7 OK nos dois mapas, do par P1.5 + P1.6. Horários do log reconstruído pelo `--tail` (B0.7h), com as ressalvas do estado no ar |
| `jogavel-2026-10-21` | `69c45b1` | **2000934**, época nova: SteamCMD na subida de 2026-10-21T21:57:21Z, sem janela ([Épocas de build](#épocas-de-build)) | 2.0.0.1469 | v1.0.375 | os mesmos da `jogavel-2026-10-20`: 9 plugins carregados no boot (MatchZy 0.8.15, BotBuyPatch, CS2 Tracker Events, Bot AI - Patches com `Applied 40/40` e `m_gameState = 0x50F8`, NadeSystem, BotAimImprover, Smarter-Bot, RoundDamageRecap e BotRandomizer), mas sem a conferência do B1.7c na 2000934: ver a época. Válvula vanilla **off**: config-hash `837cbcbc…` = H_off, o da `jogavel-2026-10-20` | Low (`02e5e958…`), por inferência: o par não teve janela, e a coleta não leu o VPK | partida 96 (matchid 96, id 63 no banco), `events_96_map0`, de_inferno 13x5 (21/10, carga 22:02:11Z, live 22:04:00Z, fim 22:30:50Z; 19:02–19:30 em -03, da TUI ao fim; G7 OK do par P1.7 + P1.8 refeito). 13x5 são os 18 rounds que contam: o parser registra 19, com o round 1 abortado (sem `round_end`). Horários do log reconstruído pelo `--tail` (B0.7h) e cortado no `StartedAt` |
| `jogavel-2026-10-25` | `cc17bb4` | **2000935** (CS2 v1.41.9.2), época nova: SteamCMD no recreate da janela de 22/10 ([Épocas de build](#épocas-de-build)) | 2.0.0.1469 | **v1.0.378** (`d9efaf8` no `meta list`), instalada à mão no volume na janela de 25/10 (B1.3s) | **nenhum**: válvula vanilla **on** desde a janela de 23/10. 3 plugins carregados no boot: MatchZy 0.8.15, CS2 Tracker Events **0.4.1** (DLL `75d0d6df…`) e RoundDamageRecap 1.2.0; RayTrace e BotHider recusados com `File not found` (as máscaras). Config-hash `0cf4006b…`, o da válvula on com o compose do B1.3s | Low (`02e5e958…`), lido no volume na janela de 22/10; as janelas de 23 e 25/10 não tocaram em `overrides/` | partida 97 (matchid 97, id 64 no banco), `events_97_map0`, de_inferno 13x0 (25/10, `loadmatch` 18:10:23Z, `SIGNONSTATE_SPAWN` do humano 18:10:58Z e `FULL` 18:11:04Z, live 18:11:21Z, fim 18:30:17Z; 15:10–15:30 em -03; G7 OK do par B1.3s + P1.10). 13x0 são os 13 rounds que contam: o parser registra 14, com o round 1 abortado. Log completo desde o `StartedAt` (1882 linhas, sem `--tail`) |
| `jogavel-2026-10-26` | `09e54bd` | 2000935, a mesma da `jogavel-2026-10-25`, sem época nova: no recreate de 26/10 09:53 o SteamCMD falhou (`Timeout`, exit 5), e no `docker start` seguinte verificou a instalação e confirmou a 2000935 | 2.0.0.1469 | v1.0.378 | **nenhum**: válvula vanilla **on**, como na `jogavel-2026-10-25`. 3 plugins carregados (`css_plugins list`): MatchZy 0.8.15, CS2 Tracker Events 0.4.1 e RoundDamageRecap 1.2.0. P1.9: template versionado em `docker/match_config.template.json` e runtime em `docker/runtime/` (a pasta inteira montada em `game/csgo/runtime`, sem bind de arquivo). P1.11: 27015/tcp publicado só em 127.0.0.1. Config-hash `1c412f6a…`, o da válvula on com o compose do par | Low (`02e5e958…`), por inferência: as janelas de 26/10 não escreveram em `overrides/`, e a coleta não leu o VPK | partida 100 (matchid 100, id 67 no banco), `events_100_map0`, de_ancient 13x4 (26/10, `loadmatch` 15:52:19Z, `FULL` do humano 15:53:14Z, live 15:53:25Z, fim 16:15:56Z; 12:52–13:16 em -03; G7 OK do par P1.9 + P1.11). O parser registra 18 rounds, com o round 1 abortado. Log completo desde o `StartedAt` (1990 linhas, sem `--tail`) |
| `jogavel-2026-10-26-2` | `57e357b` | 2000935, sem época nova: o boot do recreate de 26/10 13:50 diz `already up to date` | 2.0.0.1469 | v1.0.378 | os 6, com a válvula vanilla **off** desde a janela de 26/10 13:48 (B1.13): BotAI do fork (`Applied 40/40`, `m_gameState = 0x50F8`), BotAimImprover, BotRandomizer b1.9b, BotBuyPatch, Smarter-Bot e **NadeSystem 1.2.1-b1.13**, de um fork local com a assinatura nova da smoke (bind de `docker/plugins/NadeSystem/`, 51 arquivos pelo `MANIFESTO.sha256`). 9 plugins carregados no boot. Conferência offline dos 6 na 2000935 com a CSSharp 1.0.378 (`tools/conferir_plugins_bot.py`, `RESULTADO: OK`); a do BotAI é a de 22/10 (40/40), na mesma build. Config-hash `19d8fdd8…`, o da válvula off com o compose do B1.13 | Low (`02e5e958…`), por inferência, pelo mesmo motivo | partida 101 (matchid 101, id 68 no banco), `events_101_map0`, de_dust2 13x4 (26/10, `loadmatch` 17:03:45Z, `FULL` do humano 17:04:50Z, live 17:05:05Z, fim 17:29:49Z; 14:03–14:30 em -03; G7 OK). 18 `round_start`. Log completo desde o `StartedAt` (3743 linhas, sem `--tail`) |
| `jogavel-2026-11-04` | `f16121f` | **2000940** (CS2 v1.41.9.5), época nova: SteamCMD no recreate da janela de 04/11 12:09, com a válvula on ([Épocas de build](#épocas-de-build)); o recreate da janela de 17:41 diz `already up to date` | 2.0.0.1469 | v1.0.378 (`d9efaf8`) | os 6, com a válvula vanilla **off** desde a janela de 04/11 17:41 (B1.15), sem mudança de binário desde a `jogavel-2026-10-26-2`: BotAI do fork 1.8.12-b1.7b (`Applied 40/40`, `m_gameState = 0x50F8`), BotAimImprover 2.1.3, BotRandomizer b1.9b (1.3.2), BotBuyPatch 1.0.12, Smarter-Bot 1.9.4 e NadeSystem 1.2.1-b1.13. 9 plugins carregados no boot (com MatchZy 0.8.15, CS2 Tracker Events 0.4.1 e RoundDamageRecap 1.2.0). Conferência offline dos 6 na 2000940 com a CSSharp 1.0.378 (`conferir_botai` `973a6ed0…` e `tools/conferir_plugins_bot.py` `9a180778…`, `RESULTADO: OK` nas duas; [B1.15](b1.15-plugins-de-bot-2000940.md)). K1.9: comentários podados no compose, no cfg, no `start_match.py`, no `watcher.py` e no `parser.py`, sem mudança de comportamento. Config-hash `19d8fdd8…`, o mesmo da `jogavel-2026-10-26-2`: o K1.9 não muda o `docker compose config` | Low (`02e5e958…`), por inferência: as janelas de 04/11 não escreveram em `overrides/`, e a coleta não leu o VPK | partida 107 (matchid 107, id 77 no banco), `events_107_map0`, de_dust2 13x1 (04/11, `loadmatch` 21:05:07Z, 1ª entrada do humano derrubada por overflow no signon às 21:06:07Z, `FULL` da 2ª às 21:07:25Z, live 21:07:43Z, fim 21:28:51Z; 18:05–18:29 em -03; G7 OK **com ressalva**, abaixo). 13x1 pelos rounds, na cópia do banco (`partida-k19-b115/cs2_tracker.backup.db`, id 77, `score_mine` 13 e `score_theirs` 1) e no Histórico do card 78. Log completo desde o `StartedAt` (4370 linhas, sem `--tail`) |
| `jogavel-2026-11-04-2` | `e80611e` | 2000940, a mesma da `jogavel-2026-11-04`, sem época nova: a partida 108 rodou no container do recreate de 04/11 17:44, sem janela desde então | 2.0.0.1469 | v1.0.378 | os mesmos 6 da `jogavel-2026-11-04`, com a válvula vanilla **off**; 9 plugins carregados no boot de 20:44:37Z, o mesmo da partida 107. P1.15: o `start_match` lê o `State.Paused` antes da espera do RCON e para com `[ERRO]` se o container estiver pausado ([armadilha](../armadilhas/windows-e-docker.md#container-pausado-que-o-start_match-lê-como-rodando)). Config-hash `19d8fdd8…`, o mesmo da `jogavel-2026-11-04`: o delta `f16121f..e80611e` não toca infra | Low (`02e5e958…`), por inferência: nenhuma janela desde a de 04/11 17:41, e a coleta não leu o VPK | partida 108 (matchid 108, id 78 no banco), `events_108_map0`, de_mirage 13x5 (04/11, `loadmatch` 23:34:15Z, `FULL` do humano 23:35:41Z numa entrada só, sem overflow, live 23:36:01Z, fim 00:00:07Z do dia 05 em UTC; 20:34–21:00 em -03; G7 OK). 13x5 pelos rounds, na cópia do banco (`partida-p115/cs2_tracker.backup.db`, id 78). Log completo desde o `StartedAt` (7542 linhas, sem `--tail`) |
| `jogavel-2026-11-08` | `dff4222` | **2000942** (CS2 v1.41.9.6), época nova: SteamCMD no recreate do `vanilla on` da janela de 05/11 18:25, porque o cliente do Victor já estava nela ([Épocas de build](#épocas-de-build)); o recreate do `vanilla off` da janela de 06/11 diz `already up to date` | 2.0.0.1469 | v1.0.378 (`d9efaf8`) | os 6, com a válvula vanilla **off** desde a janela de 06/11 17:34 (B1.16), sem mudança de binário desde a `jogavel-2026-11-04-2`: BotAI do fork 1.8.12-b1.7b (`Applied 40/40`, `m_gameState = 0x50F8`), BotAimImprover 2.1.3, BotRandomizer b1.9b (1.3.2), BotBuyPatch 1.0.12, Smarter-Bot 1.9.4 e NadeSystem 1.2.1-b1.13. 9 plugins carregados no boot (com MatchZy 0.8.15, CS2 Tracker Events 0.4.1 e RoundDamageRecap 1.2.0). Conferência offline dos 6 na 2000942 com a CSSharp 1.0.378 (`conferir_botai` `7dfef426…` e `tools/conferir_plugins_bot.py` `8729e9d9…`, `RESULTADO: OK` nas duas). Config-hash `19d8fdd8…`, o mesmo da `jogavel-2026-11-04-2`: o delta `e80611e..dff4222` não toca infra | **Medium** (`ba754b61…`), **lido**: trocado com o servidor parado na janela de 06/11 (17:39:05), relido no fechamento dela (17:51:09) e na coleta de 08/11 (20:33:52Z) | MD3 de matchid 112 (ids 81 e 82 no banco), de_dust2 16x12 e de_mirage 13x7, 2x0 (08/11, `FULL` do humano 14:02:08Z; no `changelevel`, `recv queue overflow` às 14:44:28Z e `FULL` de novo às 14:44:32Z, sem desconexão; `MAP ENDED` do mapa 2 às 15:14:20Z e `DISCONNECT_BY_USER` às 15:14:35Z; 11:02–12:14 em -03; G7 OK **com ressalva**, abaixo). Log desde o `StartedAt` 2026-11-08T14:01:08Z (6963 linhas) |
| `jogavel-2026-11-09` | `29087da` | 2000942, a mesma da `jogavel-2026-11-08`, sem época nova: o recreate da janela de 08/11 diz `already up to date` | 2.0.0.1469 | v1.0.378 | os da `jogavel-2026-11-08` **sem o BotAimImprover**, mascarado por `./docker/plugins/_empty` (B1.17, `candidato-29`): BotAI do fork (`Applied 40/40`), BotRandomizer b1.9b, BotBuyPatch 1.0.12, Smarter-Bot 1.9.4 e NadeSystem 1.2.1-b1.13. 8 plugins carregados em cada boot (MatchZy, BotBuyPatch, CS2 Tracker Events, Bot AI - Patches, NadeSystem, Smarter-Bot, RoundDamageRecap e BotRandomizer) e nenhuma linha do BotAimImprover. Config-hash novo `6427c169…`: o compose muda só na fonte desse bind | Medium (`ba754b61…`), **lido** no G6 e no fechamento da janela de 08/11 e na coleta de 09/11 | partida 113 (matchid 113, id 83 no banco), de_inferno 13x5 (09/11, 16:55–17:23Z), e MD3 de matchid 114 (ids 84 e 85), de_mirage 11x13 e de_anubis 7x13, 0x2 (09/11, 18:03–19:01Z); 13:55–16:01 em -03; G7 OK. 3 `FULL` do humano (16:57Z, 18:04Z e 18:34Z, este no `changelevel` da MD3, depois de `recv queue overflow` às 18:34:02Z), sem queda; `DISCONNECT_BY_USER` só nos fins. Log desde o `StartedAt` 2026-11-09T16:54:51Z (7467 linhas) |

**Estado no ar:** a `jogavel-2026-11-09` (`29087da`, objeto de tag `4692d8ae`). Ela fecha o `candidato-29` (o mesmo commit, merge do PR #139; B1.17, card 29,992: só o BotAimImprover mascarado por `./docker/plugins/_empty`, para comparar a mira dos bots), fora do plano por decisão do Victor de 08/11 ("Vamos fazer o A"; [sprints](../agents/sprints.md#exceções-aprovadas)), validado pela partida 113 e pela MD3 114 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--build-esperada 2000942` e `--assinatura-proibida BotAimImprover`, 66 sha256 conferidos e 0 divergente, config-hash = janela `6427c169…`; Histórico do card 29,992 e mensagem da tag).

- **Janela de 08/11 19:04–19:24** (B1.17, frase "pode mexer no servidor"; registro de 08/11): ff pelo SHA `29087da` (`jogavel.py atualizar`; delta só o compose, o runbook da trilha e `tests/test_vanilla.py`), snapshot `volume-addons-1905.tgz` (`7596278d…`), recreate pelo `jogavel.py recriar` às 19:06:29, `already up to date`, `Pronto` em ~48 s, build 2000942 antes e depois.
- **G6:** 8 `Finished loading`, nenhuma linha `BotAimImprover`, `Applied 40/40` e `m_gameState = 0x50F8`, zero segfault; mounts = os de antes, só com a fonte do BotAimImprover trocada por `_empty`; sha dos montados 70/70 = checkout; `pre.sh` sem CR; VPK Medium `ba754b61…`; config-hash `6427c169…` = `docker compose config --hash`. Smoke só de bots (de_mirage → de_inferno, 5x5) sem crash nem linha do BotAimImprover. Fechamento = referência (get5 none).
- **Coleta G7** (09/11, sem janela, preflight 0, checkout no `29087da`): container do recreate de 08/11 (`Created` 2026-11-08T22:06:34Z), parado sem erro às 12:19:47Z de 09/11 e religado pelo `start_match` sem recreate (`StartedAt` 16:54:51Z, RestartCount 0); config-hash do container = compose = janela; 70/70 montados; VPK ativo Medium.
- **Evidência** (fase 2 do QA): APROVADO. Humano sem queda em 3 entradas e saída só nos fins. Impressão do Victor depois das duas partidas: "Melhorou bastante, e agora parece que tá num nível maneiro pra jogar" (relato da sessão 113 + 114, não de um matchid só).
- **Fora dos critérios:** o boot de 08/11 22:06Z ficou sem log de 00:47Z até a parada limpa das 12:19Z; o `vencedor: ?` cosmético depois do mapa 1 da MD3; o round 1 abortado, conhecido. Ruídos do log: os 3 `Error invoking callback` do BotBuyPatch em cada carga de mapa ([trilha](trilha-de-bots.md#sobras), item 3).

A `jogavel-2026-11-08` (`dff4222`, objeto de tag `cc589db0`) não fecha candidato: o B1.16 (card 29,991, fora do plano, a pedido do Victor em 06/11, "B: Medium e plugins") só mexeu no volume e na válvula, e o `dff4222` é o merge do PR #138 (S1.1, docs), o HEAD do checkout principal desde a janela de 05/11. Validada pela MD3 112 (`VEREDITO G7: OK` do `evidencia_partida.py`: build 2000942, 0 crash ou `FATAL`, 69 sha256 conferidos e 0 divergente, config-hash = compose `19d8fdd8…`; QA fase 2 APROVADO; Histórico do card 29,991 e mensagem da tag).

- **Janela de 05/11 18:25–21:05** (papel servidor, sem card, frase "pode mexer no servidor"; registro de 05/11): o cliente do Victor estava na 2000942 ("client out of date"). O `jogavel.py vanilla on` recriou o container (`Created` 21:48:28Z, depois de ~18 min de espera de aprovação) e o SteamCMD trouxe a **2000942** (1ª tentativa com `state is 0x6`, 2ª com verificação dos 73,4 GB); o `Pronto` saiu ~16 min depois do recreate, e o `jogavel.py` já tinha desistido (saída 1). A janela venceu às 19:10:30, no passo 3; o G6 foi completado só de leitura às 21:04 (3 plugins `LOADED`, 16/16 montados, config-hash `e863d2f6…` = compose com o override vanilla), e as conferências dos plugins de bot e o vanilla off ficaram para outra janela (L11). Nenhuma partida jogou nesse estado. Decisão do Victor: "A: parar TMs e janela".
- **Janela de 06/11 17:34–17:53** (B1.16, frase "pode mexer no servidor"; registro de 06/11): sem ff; cópia do `libserver.so` da 2000942 (41850680 B, `ee0cc32a…`) e as duas conferências dos 6 com `RESULTADO: OK`; VPK ativo lido `02e5e958…` (Low) às 17:35:44, servidor parado às 17:39:03, `overrides/Medium/botprofile.vpk` copiado sobre o ativo às 17:39:05 por container descartável e relido `ba754b61…` (Medium); `jogavel.py vanilla off` com recreate às 17:39:14, `already up to date`, `Pronto` em ~39 s.
- **G6:** 9 `Finished loading`, `Applied 40/40` e `m_gameState = 0x50F8`, `[BotAimImprover] Loaded (Linux)`, catálogo do BotRandomizer, `[NadeSystem] Loaded — 3703 grenades`; zero segfault; sha dos montados 71/71 = checkout; `pre.sh` sem CR; config-hash `19d8fdd8…` = compose. Smoke só de bots (de_mirage → de_inferno, 5x5): `Replayed` smoke 41, flash 30, HE 7, molotov 2, decoy 3, zero crash. Fechamento = referência (get5 none), VPK Medium às 17:51:09.
- **Partidas antes do G7, no mesmo container:** 109 (06/11, de_mirage, sem fim de mapa: lag e `recv queue overflow` às 21:08Z e saída do humano, sem crash), 110 (07/11, de_dust2, id 79) e 111 (07/11, de_inferno, id 80). O lag de 06/11 coincidiu com a máquina carregada (CPU 94%, fora da coleta).
- **Coleta G7** (08/11 17:31 em -03, sem janela, preflight 0, checkout no `dff4222`): container do recreate de 06/11 (`Created` 2026-11-06T20:39:17Z, `StartedAt` 2026-11-08T14:01:08Z, RestartCount 0), config-hash = compose = janela, VPK ativo Medium às 20:33:52Z.
- **Ressalvas do QA:** os `Error invoking callback` do BotBuyPatch (`Schema target points to null`, `BotBuy.cs:258`) no início de cada boot e de cada `changelevel` (12 no log desde o `Created` de 06/11), ruído conhecido ([trilha](trilha-de-bots.md#sobras), item 3); a 109 sem fim de mapa; a carga da máquina fora da coleta. Relato do Victor em 08/11, já neste estado: "os bots da dificuldade Medium tão muito rápidos e quase não erram tiro" ([armadilha 29](../armadilhas/bots-e-perfis.md#29-todo-perfil-pro-tem-skill--100)); daí o B1.17.

A `jogavel-2026-11-04-2` (`e80611e`, objeto de tag `5446978`) fecha o `candidato-28` (`110bb98`, merge do PR #128; P1.15, card 92,6: o `start_match` com o container pausado), validado pela partida 108 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--partida events_108_map0 --build-esperada 2000940`, saída 0, 0 segfault, 0 overflow, 69 sha256 sem divergência, config-hash = janela `19d8fdd8…`, sobre a coleta e a cópia do banco em `mode=ro`; Histórico do card 92,6 e mensagem da tag). O `e80611e` soma ao `110bb98` só o que fica fora do caminho de jogo: o P1.19 (PR #129, docs), o V1.2 (PR #130, `tools/ficha_orfas.py` e testes) e o P1.20 (PR #131, docs); o `start_match.py` é o mesmo.

- **Sem janela:** o PM fez o ff do checkout principal `f16121f` → `110bb98` com preflight 0, delta sem infra (`start_match.py` e testes), e o checkout chegou ao `e80611e` só com docs e `tools/` (Histórico do card 92,6, 04/11 19:25). G6 n/a: degrau sem infra.
- **Coleta G7** (04/11 21:11 em -03, sem janela, preflight 0, checkout no `e80611e`; registro, linhas 138-148): o mesmo container do recreate de 17:44 (`Created` 20:44:32Z, `StartedAt` 20:44:37Z, RestartCount 0, `Paused` false), log completo, 72/72 montados iguais ao checkout, config-hash do container = compose = janela, `19d8fdd8…`. Zero segfault e `Fatal error` no log da subida.
- **Evidência** (fase 2 do QA): `events_108_map0` (id 78) com saída 0 e `VEREDITO G7: OK`. O log da partida do `start_match` (`logs/partidas/partida_20261104T233414Z.log`, fora do git) diz `[DOCKER] Container 'cs2-spike' já está rodando.` às 20:34:14, sem `[ERRO]` nem menção a pausado, e o `[RCON] Conectado.` no mesmo segundo.
- **Entrada do humano:** uma só, `FULL` às 23:35:41Z, o maior `ProcessMessages` de 419 ms em 3 mensagens, sem `DISCONNECTING` ([overflow no signon](../armadilhas/engine-cs2.md#overflow-no-signon-network_disconnect_overflow-na-entrada)); saída às 00:00:13Z (`DISCONNECT_BY_USER`) depois do fim.
- **A tag saiu à mão:** o `jogavel.py marcar jogavel` daria o nome com a data da marcação (05/11), e a partida foi em 04/11. O tech-manager criou a tag com `git tag` e `git push` crus, então faltou a linha em `logs/jogavel/tags.md`, e o PM apagou o `data/candidato.json` (`candidato-28`, já validado) pelo nome, com preflight 0 (Histórico do card 92,6, 05/11 09:10). Desde o P1.21, o `marcar` aceita `--data AAAA-MM-DD`.
- **Ruídos do log, conhecidos:** os 3 `Error invoking callback` do BotBuyPatch (`PlayerPawn` nulo, `BotBuy.cs` 213/231/258) às 23:34:19Z, no `changelevel` do `loadmatch`, sem humano conectado ([trilha](trilha-de-bots.md#sobras), item 3).

A `jogavel-2026-11-04` (`f16121f`, objeto de tag `121ff5fc`) fecha o `candidato-27` (o objeto de tag `2b8ea918` sobre o commit `e4fb9d5`, merge do PR #125; K1.9, a poda de comentários, PRs #121 e #125) e o B1.15 (card 29,99, PR #126, só o runbook, sem candidato), validados juntos pela mesma partida, por exceção do Victor de 04/11 ao trilho único ([sprints](../agents/sprints.md#exceções-aprovadas)), com evidências disjuntas: sha256 do cfg e config-hash do compose para o K1.9, load dos 6 plugins e humano sem queda para o B1.15. O `f16121f` soma ao `e4fb9d5` só o runbook do B1.15. Validado pela partida 107 (`VEREDITO G7: OK` do `evidencia_partida.py`, saída 0, build 2000940, 0 segfault, sha256 sem divergência, config-hash = janela, ingerida com id 77; Históricos dos cards 78 e 29,99 e mensagem da tag).

- **Janela de 04/11 12:09–12:30** (papel servidor, sem card; registro, linhas 16-52): com o checkout no `1ad6805` e sem ff, o `jogavel.py vanilla on` recriou às 12:11:13 e o SteamCMD trouxe a **2000940** (a 1ª tentativa falhou com `state is 0x6`, a 2ª verificou e baixou; `Pronto` ~4 min 08 s depois do recreate). G6 com a válvula on: CSSharp v1.0.378, 3 plugins `LOADED`, config-hash `e863d2f6…` = compose com o override vanilla. Cópia do `libserver.so` e do gamedata em `2026-11-04/build-nova/`. Nenhuma partida jogou nesse estado.
- **Janela de 04/11 17:41–18:01** (K1.9 + B1.15, runbook [b1.15](b1.15-plugins-de-bot-2000940.md); registro, linhas 68-124): plugins do checkout = os de 26/10 (NadeSystem 51/51, BotAI, BotAimImprover e BotRandomizer 11/11); as duas conferências com `RESULTADO: OK` e os sha256 do runbook; fast-forward `f2f6c90` → `f16121f` pelo SHA (28 arquivos; `checar_so_comentarios.py`: só comentários; config-hash sem o override `19d8fdd8…` antes e depois do ff); `jogavel.py vanilla off` com recreate às 17:44:28, `already up to date`, `Pronto` em ~49 s, build 2000940 antes e depois.
- **G6 por plugin:** 9 `Finished loading`, `Applied 40/40` e `m_gameState = 0x50F8`, `[BotAimImprover] Loaded (Linux)`, catálogo do BotRandomizer, `[NadeSystem] Loaded — 3703 grenades`; zero linha proibida do passo 6 do runbook; 16 mounts = os do `antes-mounts.txt` da janela de 12:09; sha dos montados 68/68 = checkout. Smoke só de bots (de_mirage → de_inferno): `Replayed` smoke 40, flash 28, HE 9, molotov 4, decoy 4, zero `SpawnProjectile error`. Fechamento: cvars = referência, `pre.sh` sem CR, config-hash `19d8fdd8…` = `docker compose config --hash` sem o override.
- **Coleta G7** (04/11 18:40 em -03, sem janela, preflight 0, checkout no `f16121f`): container do recreate de 17:44 (`Created` 20:44:32Z, `StartedAt` 20:44:37Z, RestartCount 0), log completo, 72/72 montados iguais ao checkout, config-hash do container = compose = janela, `19d8fdd8…`. Zero segfault e `Fatal error`.
- **Evidência** (fase 2 do QA): `events_107_map0` (id 77) com saída 0 e `VEREDITO G7: OK`. K1.9 APROVADO (cfg `f3b0009c…` no container = checkout). B1.15 **APROVADO COM RESSALVA**: bots com os plugins (71 `Replayed` do NadeSystem na partida), partida ingerida.
- **Ressalva: a 1ª entrada do humano caiu por overflow no signon.** `FULL` às 21:06:05,99Z, `ProcessMessages` de 1218 ms em 6 mensagens `CNETMsg_SignonState` e `NETWORK_DISCONNECT_OVERFLOW` às 21:06:07,7Z, ~1,7 s depois do `FULL`. É a armadilha conhecida do [overflow no signon](../armadilhas/engine-cs2.md#overflow-no-signon-network_disconnect_overflow-na-entrada) (P1.13), não a queda da L11: a mesma assinatura saiu às 17:34:40Z (14:34 em -03), antes da janela de 17:41, com a válvula **on** (615 ms em 3 mensagens, só MatchZy, captura e RoundDamageRecap carregados), portanto é anterior aos plugins de bot. A 2ª entrada (`FULL` às 21:07:25Z) jogou até o fim, saída às 21:29:03Z (`DISCONNECT_BY_USER`), zero segfault. Decisão do Victor (04/11, chat): "Aprovar e manter", com os plugins ligados e sem `vanilla on`; o card do overflow, "Agora não".
- **Ruídos do log, conhecidos:** os 3 `Error invoking callback` do BotBuyPatch (`PlayerPawn` nulo, `BotBuy.cs` 213/231/258) às 21:05:08–09Z, no `changelevel` do `loadmatch`, sem humano conectado ([trilha](trilha-de-bots.md#sobras), item 3).

A `jogavel-2026-10-26-2` (`57e357b`) fecha o `candidato-26` (o mesmo commit, merge do PR #117; B1.13: os 6 plugins de bot religados na build 2000935 com a CSSharp v1.0.378, com o NadeSystem de um fork local), validado pela partida 101 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--partida events_101_map0 --build-esperada 2000935`, o config-hash = janela `19d8fdd8…` e `--assinatura-proibida` para `Invalid function pointer` e `SpawnProjectile error`, sobre o log da coleta e a cópia do banco em `mode=ro`; Histórico do card 29,97 e mensagem da tag).

- **Janela de 26/10 13:48–14:01** (B1.13, runbook [b1.13](b1.13-plugins-de-bot-2000935.md), passos 1 a 11): conferência offline dos 6 = `RESULTADO: OK`; granadas do volume 48/48 iguais às do fork (lidas por container descartável `:ro`, porque com a válvula on o `docker exec` vê a máscara); build do NadeSystem 1.2.1-b1.13 (NuGet `CounterStrikeSharp.API` 1.0.375, com o OK do Victor ao download, G5), `MANIFESTO.sha256` de 51 linhas, assinatura nova presente e antiga ausente; fast-forward `09e54bd` → `57e357b` (infra: o bind do NadeSystem no compose, comentário no `docker-compose.vanilla.yml` e o `.gitignore`); `jogavel.py vanilla off` com recreate às 13:50:25, `Pronto` em ~44 s, build 2000935 antes e depois.
- **G6 por plugin:** 9 `Finished loading` (MatchZy, CS2 Tracker Events, RoundDamageRecap, Bot AI - Patches, BotAimImprover, BotRandomizer, BotBuyPatch, Smarter-Bot e NadeSystem), `Applied 40/40` e `m_gameState = 0x50F8`, `[BotAimImprover] Loaded (Linux)`, catálogo do BotRandomizer, `[NadeSystem] Loaded — 3703 grenades`; zero `Invalid function pointer`, assinatura falha, `patch disabled`, `hook unavailable`, `Error invoking callback`, segfault e `FATAL`. Smoke só de bots (de_mirage → de_inferno): granadas lançadas (`Replayed` smoke 37, flash 26, HE 12, molotov 12, decoy 2), zero `SpawnProjectile error`; a compra ficou sem prova no smoke (o log não registra compra). Fechamento: cvars = referência, sha dos montados 69/69 = checkout (as 51 do NadeSystem = `MANIFESTO`), `pre.sh` sem CR, config-hash `19d8fdd8…` = `docker compose config --hash` sem o override vanilla.
- **Residual do volume apagado:** o `game/csgo/match_config.spike.json` de 0 B (root, de 2026-09-04, sobra do bind de arquivo de antes do P1.9, sem montagem) saiu no passo 10, pelo nome, com o OK do Victor de 26/10 ("Pode apagar o residual."); o `runtime/match_config.spike.json` ficou intacto.
- **Coleta G7** (26/10 14:41 em -03, sem janela, preflight 0, checkout no `57e357b`): container do recreate de 13:50 (`Created` 16:50:28Z, `StartedAt` 16:50:32Z), log completo, 72/72 montados iguais ao checkout, config-hash do container = compose = janela, `19d8fdd8…`. Zero segfault, `FATAL`, overflow, `Invalid function pointer`, `SpawnProjectile error` e `hook unavailable`.
- **Evidência** (fase 2 do QA): `events_101_map0` (id 68) com saída 0 e `VEREDITO G7: OK`: build 2000935 = esperada, 5x5, ingerida, 69 sha256 sem divergência. Granadas na partida: `Replayed` smoke 79, flash 44, HE 11, molotov 18. **Compra dos bots** provada pelos eventos da cópia: armas fora do spawn (p250 e cz75a no pistol; ak47, m4a1, awp, sg556, aug, p90, mp7, bizon, elite, deagle, HE e molotov) nas kills e danos de bot (`player_death`/`player_hurt`) em todos os rounds de 2 a 18, nos 9 bots; `cash_spent_round` > 0 em 14 de 16 rounds do `round_stats`; `armor` > 0 no `freeze_end` em todo round. O `equip_freeze_end` é 0 para bot em toda partida (também na 100 e na 63): artefato da captura, não prova. Humano: `FULL` 17:04:50Z, saída às 17:29:59Z (`DISCONNECT_BY_USER`) depois do fim, sem queda.
- **Ruídos do log, conhecidos:** os 3 `Error invoking callback` do BotBuyPatch (`get_PlayerPawn` nulo, `BotBuy.cs` 258/231/213) às 17:03:48Z, no `changelevel` do `loadmatch`, antes do humano e do live ([trilha](trilha-de-bots.md#sobras), item 3); 44 `Grenade has no weapon info`; `[META] Loaded 0 plugins (3 already loaded)` no `changelevel`.

A `jogavel-2026-10-26` (`09e54bd`) fecha o `candidato-25` (`c67e548`, merge do PR #118 sobre o #116), o par P1.9 + P1.11 da exceção do Victor de 19/10 ao trilho único, numa janela só ([sprints](../agents/sprints.md#exceções-aprovadas)): P1.9, o `match_config` com template versionado (`docker/match_config.template.json`, só com IDs fictícios) e runtime em `docker/runtime/`, uma pasta montada inteira e fora do git (PR #116); P1.11, a 27015/tcp publicada só em 127.0.0.1 (PR #118). O `09e54bd` soma ao `c67e548` o P1.9b (card 88,5, PR #119, só `tools/`): o `coletar` e o `evidencia_partida.py` conferem o `match_config` no caminho novo. Validado pela partida 100 (`VEREDITO G7: OK` com `--partida events_100_map0 --build-esperada 2000935` e o config-hash = janela `1c412f6a…`; Históricos dos cards 88 e 90 e mensagem da tag).

- **Janela de 26/10 09:52** (vencida às 10:37:08): o `docker/runtime/match_config.spike.json` foi semeado do arquivo vivo antes do ff (sha256 igual), e o `jogavel.py atualizar` fez o fast-forward `cc17bb4` → `09e54bd`, com o git limpo e o `spike.json` fora do git. Recreate às 09:53:20 com a válvula on: o SteamCMD falhou 3 vezes (`Timeout`) e o container saiu com exit 5, mas o `recriar` devolveu 0 depois de 10 min sem a linha do GC; o `docker start` das 10:04:13 verificou a instalação (~73,4 GB) e subiu na 2000935 (~3 min 36 s). O comando só leitura do G6 ficou na aprovação de ~10:08 a 10:56 ([lições](../agents/licoes.md), L09); o G6 lido depois deu `docker port` 27015/tcp → `127.0.0.1:27015` (27015/udp e 27020/udp em todas as interfaces), 19 mounts sem o bind de arquivo do `match_config` e com `./docker/runtime`, sha do runtime dentro = host e config-hash `1c412f6a…` = compose (com o override vanilla). Da LAN: TCP 27015 no IP privado da Wi-Fi do host recusado, loopback aceito (o teste foi do próprio host, não de outro aparelho).
- **Janela de 26/10 11:01–11:02** (só leitura, sem ff nem recreate): completou o G6 pela RCON no loopback: `version` 2000935, CSSharp v1.0.378 @ `d9efaf8`, 3 plugins `LOADED`, `get5_status` none, cvars do boot = fechamento, `changelevel` com `Pronto` em 2 s, sha256 dentro = checkout 5/5, `pre.sh` sem CR.
- **Coleta G7** (26/10 13:27 em -03, sem janela, preflight 0, checkout no `09e54bd`): container do recreate de 09:53 (`Created` 12:53:23Z, `StartedAt` 13:04:13Z, RestartCount 0), log completo, 16/16 montados iguais ao checkout, inclusive o `runtime/match_config.spike.json`, config-hash do container = compose, `1c412f6a…`, `git status --porcelain` vazio depois da partida. Zero segfault, `FATAL`, overflow e `Error invoking callback`.
- **Evidência** (fase 2 do QA): `events_100_map0` (id 67), saída 0 e `VEREDITO G7: OK`. P1.9: a TUI carregou `runtime/match_config.spike.json`, a MatchZy aceitou (`Success with matchid: -1`: o runtime não tem a chave `matchid`, e a MatchZy numerou 100), o humano entrou no team1 com o SteamID do config, e o runtime não herdou nada da partida anterior. P1.11: a TUI conectou o RCON em `127.0.0.1:27015`.

A `jogavel-2026-10-25` (`cc17bb4`) fecha o `candidato-24` (`a0b4dca`, merge do PR #112; B1.3s: CSSharp v1.0.378 oficial, `CSSHARP_FIXED_VERSION` no compose) e o `candidato-23`, ancestral dele (`ba17644`, merge do PR #111; P1.10: o plugin de captura 0.4.1, em que o `Load` e o `OnMapStart` só renomeiam para `orphan_` com `round_start`, `player_death` ou `player_hurt`), validados juntos por exceção do Victor de 24/10 ao trilho único ([sprints](../agents/sprints.md#exceções-aprovadas)), com evidências disjuntas. O `cc17bb4` traz, depois do `a0b4dca`, só os acertos do runbook do B1.3s (PRs #113 e #114, docs e teste). Validado pela partida 97 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--partida events_97_map0 --build-esperada 2000935 --assinatura-proibida FireOutputInternal`, sobre o log da coleta e a cópia do banco em `mode=ro`; Históricos dos cards 22,5 e 89 e mensagem da tag).

- **DLL do `candidato-23`:** a mensagem da tag `candidato-23` e o `data/candidato.json` registram por engano a DLL `697760a7…`, a da 0.4.0: o `jogavel.py marcar` rodou antes do build. A DLL certa da 0.4.1 é a `75d0d6df…` (51712 bytes), construída na janela de 22/10 com o container parado, com manifesto em `C:/Users/Victor/cs2-tracker-backups/plugins/Cs2TrackerEvents/75d0d6df…/`. Tag publicada não muda: a correção fica aqui e no registro da janela. A tag `candidato-24` e a `jogavel-2026-10-25` já trazem a `75d0d6df…`.
- **Janela de 22/10** (19:54–20:14, P1.10): fast-forward `69c45b1` → `ba17644`, build do plugin com o container já parado, recreate às 19:55:58. O boot trouxe a **2000935** sem pedir ([Épocas de build](#épocas-de-build)). G6 OK com a válvula off: 9 plugins, CS2 Tracker Events 0.4.1, nenhum `preservado em orphan_`, BotAI com `Applied 40/40 patches.`, sha256 montados iguais ao checkout e config-hash `837cbcbc…` = H_off.
- **A CSSharp v1.0.375 cai com humano na 2000935** (23 e 24/10): ver a quebra nas [Épocas de build](#épocas-de-build). Na janela de emergência de 23/10 (19:18–19:27) o servidor ligou a válvula vanilla (`jogavel.py vanilla on`, config-hash `0f3ff2b2…`, o da on do `candidato-15`), e o Victor decidiu não jogar até a correção (opção B). Nas janelas de 24/10 (22:58–23:22) e de 25/10 (11:22–11:28) o B1.3s parou antes do snapshot, pelo dono dos arquivos do volume, e o runbook foi acertado (PRs #113 e #114).
- **Janela de 25/10** (15:01–15:07, B1.3s, 3ª tentativa): fast-forward `0409dc5` → `cc17bb4`, snapshot `volume-addons-1503.tgz`, `unzip` do asset oficial (`counterstrikesharp-linux-1.0.378.zip`, 4137186 bytes, sha256 `26cf779e…` = o digest do GitHub) sem o `shared/`, e recreate às 15:04:13. Mudaram no volume só o `cssharp_version.txt`, o `.so` e o `gamedata.json` da CSSharp. G6 OK: `meta list` com `CounterStrikeSharp (v1.0.378 @ d9efaf8)`, MatchZy 0.8.15 `LOADED`, os 3 plugins da válvula on, zero segfault, os 5 montados iguais ao checkout, `pre.sh` sem CR e config-hash `0cf4006b…` = compose.
- **Coleta G7** (25/10 15:41 em -03, sem janela, preflight 0, checkout no `cc17bb4`): log do container completo desde o `StartedAt` 2026-10-25T18:04:16Z, sem reconstrução; os 16 caminhos montados iguais ao checkout; config-hash do container = compose = janela, `0cf4006b…`. Zero segfault, `FATAL`, overflow, `Error invoking callback` e `FireOutputInternal`; zero `preservado em orphan_` e nenhum `orphan_` novo.
- **Evidência** (fase 2 do QA): `events_97_map0` (id 64) com saída 0 e `VEREDITO G7: OK`: CSSharp v1.0.378, Metamod 2.0.0.1469, build 2000935 = esperada, boots da MatchZy 1, 5x5, nenhum `sem_round_end`, `current.jsonl` com cauda normal, 7 sha256 conferidos. B1.3s: o humano entrou (`SPAWN` 18:10:58Z, `FULL` 18:11:04Z), jogou até o fim e saiu às 18:30:26Z, sem a queda de 11 a 30 s depois do `SPAWN`. P1.10: `[Cs2TrackerEvents] Pronto` 4 vezes (2 no boot, 1 no `changelevel` do fechamento e 1 no `loadmatch`), nenhum `orphan_`, e a partida ingerida com 86 kills e 409 danos.
- **Ruídos do log, conhecidos:** `[LoadMatchFromJSON] Success with matchid: -1!` no `loadmatch` ([MatchZy](../armadilhas/matchzy.md#depois-da-auditoria)) e `Long frame (MatchEnded)` de dezenas de ms no fim ([engine](../armadilhas/engine-cs2.md#ruído-conhecido-long-frame-matchended-de-dezenas-de-ms)), os dois também nas coletas de 20 e 21/10.

A `jogavel-2026-10-21` (`69c45b1`) fecha o `candidato-22` (o mesmo commit, merge do PR #109 sobre o #108), o par P1.7 + P1.8 da exceção do Victor de 19/10 ao trilho único ([sprints](../agents/sprints.md#exceções-aprovadas)), refeito depois do `candidato-21` reprovado (nota abaixo): P1.7, a contagem de presentes pelo `status` do RCON, sem a SourceTV (`6d6aa2b`, PR #108); P1.8, o `live_override.cfg` neutro antes do `loadmatch` (`d5e61d7`, PR #109, o `7b53343` reaplicado). Validado pela partida 96 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--partida events_96_map0 --build-esperada 2000934`, sobre o log cortado no `StartedAt` e a cópia do banco em `mode=ro`; Históricos dos cards 86 e 87 e mensagem da tag).
G6 n/a: os dois cards não tinham infra nem janela. O compose não mudou desde o `candidato-15` (`git diff c228d93 69c45b1` vazio no compose, no `docker-compose.vanilla.yml`, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `807b940d…`), e o config-hash seguiu `837cbcbc…` = H_off.

- **Checkout:** o PM levou o checkout principal de `c228d93` a `69c45b1` por fast-forward na noite de 20/10 (`jogavel.py atualizar`, preflight 0, delta sem infra; Histórico das 23:51 em -03).
- **Container:** o do recreate de 17/10 (`Created` 2026-10-17T19:33:02Z, sem recreate desde então), numa subida nova: a TUI subiu o container parado pela queda do Docker Desktop, `StartedAt` 2026-10-21T21:57:21Z (18:57:21 em -03), RestartCount 0. Nessa subida o SteamCMD trouxe a build 2000934 ([Épocas de build](#épocas-de-build)).
- **Coleta G7** (21/10 19:42 em -03, sem janela, preflight 0, checkout no `69c45b1`): os 21 caminhos montados iguais ao checkout, o config-hash do container igual ao do compose, `837cbcbc…`, e build 2000934. Desde o `StartedAt`: zero segfault, zero `FATAL`, zero `recv queue overflow` e zero `Error invoking callback`.
- **Log cortado no `StartedAt`:** o `docker logs --since` saiu com 0 byte, e o `jogavel.py coletar` (B0.7h) reconstruiu pelo `--tail` em 7 leituras (6432 linhas, 0 fronteira, 0 entrada ilegível, boot inteiro), mas recuando até 2026-10-21T01:15:04Z, na partida 95. O servidor cortou o reconstruído no `StartedAt` (`docker-logs-desde-startedat.txt`, 4478 linhas, com LEIAME) e o G7 se julgou por ele: na partida 95, o reconstruído inteiro deu RUIM falso (`MatchZy carregou 3x`) por pegar boots de antes do `StartedAt`.
- **Evidência** (fase 2 do QA): `events_96_map0` (id 63) com saída 0 e `VEREDITO G7: OK`: boots da MatchZy 1, nenhuma assinatura falha, build 2000934 = esperada, 13x5, 5x5, nenhum `sem_round_end`, 18 sha256 conferidos. P1.7: a TUI loga às 19:04:04 `Clientes após reconciliação (status do RCON): 10` (esperado 10), com a SourceTV como cliente BOT no slot 0 (team 0) a partida inteira; nenhuma linha de aviso de jogadores a mais nem `Recompondo`. P1.8: às 19:02:11, `live_override.cfg neutro` antes do `Carregando match_config.spike.json`, e o único `execing MatchZy/live_override.cfg` do container é o do `live.cfg`, às 22:04:01Z; 5x5 em todos os blocos de round, do round 1 ao fim.
- **Não visto ao vivo:** a partida 96 começou já em 5x5, então o 6:4 do 1º bot no CT e o ramo `Recompondo` do P1.7 ficam cobertos só pelos testes.
- **O `candidato-21` reprovado** (`29bf60f`, merges `b8a9cd4`, PR #104, e `29bf60f`, PR #106): a 1ª tentativa do par jogou a partida 95 (20/10, MD1 de_mirage, matchid 95, id 62 no banco, `events_95_map0`, 1x13 para os bots, 15 rounds, build 2000933). O G7 da máquina passou (saída 0 sobre o reconstruído cortado no `StartedAt` 2026-10-20T16:49:06Z), mas o QA reprovou o P1.7: a TUI contou 11 clientes contra 10 esperados, porque o `status` do RCON inclui a SourceTV, cliente BOT do servidor a partida inteira; o estado real era 5x5. O P1.8 foi atendido na mesma partida, mas, pela exceção, a reprovação de um reverte o par: o servidor voltou o checkout principal à `jogavel-2026-10-20` às 22:44 de 20/10 (`jogavel.py voltar`, sem recreate), e o `6b95c77` (PR #107, com o revert `1f49fa5`) tirou os dois da `main`. O par voltou como `candidato-22`: o P1.7 corrigido (a SourceTV descontada pela linha do `status`) e o P1.8 reaplicado sem mudança de conteúdo.

A `jogavel-2026-10-20` (`c228d93`) fecha o `candidato-20` (o mesmo commit, merge do PR #102; P1.5: os mapas 2 e 3 da série começam sozinhos, sem o corte de 240 s e com teto de 3 h por mapa) e o `candidato-19`, ancestral dele (`9e5ab8e`, merge do PR #100; P1.6: o lado do humano por mapa, `map_sides[i]`), o par P1.5 + P1.6 da exceção do Victor de 20/10 ao trilho único ([sprints](../agents/sprints.md#exceções-aprovadas)). Validado pela MD3 de matchid 93 (`VEREDITO G7: OK` do `evidencia_partida.py` nos dois mapas, sobre o log reconstruído e a cópia do banco em `mode=ro`; Históricos dos cards 84 e 85 e mensagem da tag).
G6 n/a: os dois cards não tinham infra nem janela. O compose não mudou desde o `candidato-15` (`git diff a32ef5e c228d93` vazio no compose, no `docker-compose.vanilla.yml`, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `807b940d…`), e o config-hash seguiu `837cbcbc…` = H_off.

- **Checkout:** o PM levou o checkout principal de `9e5ab8e` a `c228d93` por fast-forward às 13:27 de 20/10 em -03 (`jogavel.py atualizar`, preflight 0, delta sem infra).
- **Container:** o do recreate de 17/10 (`Created` 2026-10-17T19:33:02Z, sem recreate desde então), numa subida nova: `StartedAt` 2026-10-20T16:49:06Z (13:49:06 em -03), RestartCount 0. É um restart fora de janela, e não o processo do restart da janela T2 de 20/10 (12:11:22Z). A sequência, como o QA a descreveu no Histórico do card 84: às 16:17:06Z, um `loadmatch` (resto da tentativa das 13:17 em -03, abandonada; sem o `matchid` no config, a MatchZy logou -1) trocou para de_inferno e ficou em warmup sem ninguém conectar; às 16:48:45Z, o `loadmatch` da TUI das 13:48 foi recusado com `A match is already setup with id: -1`, e o `start_match` saiu pedindo restart do container (`start_match.py:1262-1268`). O log não traz linha de parada, o boot recomeça às 16:49:07Z com o config-hash e os sha256 iguais, e a TUI das 13:49:54 carregou e jogou. Não afeta o G7.
- **Coleta G7** (20/10 15:16 em -03, sem janela, preflight 0, checkout no `c228d93`): os 21 caminhos montados iguais ao checkout, o config-hash do container igual ao do compose, `837cbcbc…`, e build 2000933. Desde o `StartedAt` (6455 linhas): zero segfault; 1 `FATAL`, benigno (a MatchZy em `GetCoachSpawns`, sem `spawns/coach/de_cache.json`); 3 `recv queue overflow` do cliente às 17:18:02Z, no meio do `changelevel` (S3 de [engine-cs2](../armadilhas/engine-cs2.md#assinatura-e-como-contar), fora da contagem); 6 `Error invoking callback` do BotBuyPatch (`BotBuy.cs` 213, 231 e 258), 3 no warmup do mapa 1 e 3 no `ChangeMap`, como no T2. Memória no fim: 1,68 GiB de 7,69.
- **Virada 1 → 2** (UTC): `MAP ENDED` e `MATCH ENDED` do mapa 1 às 17:17:36Z (remainingMaps 2, 1x0); `ChangeMap de_cache` e `StartWarmup` às 17:17:57Z; `changelevel` às 17:18:01Z; o Victor em `FULL CONNECT` às 17:18:07Z e no T às 17:18:10Z (`map_sides[1]` = `team1_t`); RCON e balanço da TUI às 14:18:12 em -03; `StartLive` (`css_start`) às 17:18:16Z, sem botão, e 5x5 a partir do round 2. O mapa 2 acabou às 18:05:41Z (`MAP ENDED` e `MATCH ENDED`, 2x0), sem `changelevel`: a série terminou.
- **Evidência** (fase 2 do QA): `events_93_map0` (id 58) e `events_93_map1` (id 59) com saída 0 e `VEREDITO G7: OK`, 5x5, 18 sha256 conferidos, build 2000933; `series_num_maps=3` nas linhas 58 e 59 do banco (nas anteriores, 1). P1.5: a espera do mapa 2/3 armou às 13:51:07 em -03 e durou 27 min, sem o corte de 240 s e sem nenhum `Teto de 3 h`; a espera 3/3 armou às 14:18:20 e terminou pelo `MATCH ENDED` (remainingMaps 1, 2x0), sem forçar. P1.6: `map_sides` = [`team1_ct`, `team1_t`, `team1_ct`]; a TUI pôs o humano no CT às 13:50:58 (mapa 1) e no T às 14:18:12 (mapa 2); `round_start.human_side`, no mapa 1, ct nos rounds 1–13 e t nos 14–19 e, no mapa 2, t nos 1–13, ct nos 14–28 e t nos 29–31 (prorrogação).
- **Não visto ao vivo:** o mapa 3 não foi jogado (2x0), então o início sozinho de um mapa 3 e o `map_sides[2]` ficam sem observação. Fora do card: o botão manual de forçar início (`wizard_core.force_start`) segue lendo `map_sides[0]`.
- **Log reconstruído:** o `docker logs --since` saiu com 0 byte, e o `jogavel.py coletar` (B0.7h) reconstruiu pelo `--tail` em 8 leituras, com 0 fronteira e 0 entrada ilegível; o boot desta subida está inteiro. Linhas por 5 s: no máximo 200 (no boot), 189 na virada e 40 no fim do mapa 2, nenhum trecho acima das 200 com que a dobra do `--tail` do P1.5 perderia linha sem avisar (sugestão do QA no card 84). Vale a ressalva do QA na `jogavel-2026-10-19-2`: o reconstruído também perde linhas dentro do segmento.
- **Avisos** (fora do G7): o `ClientPutInServer` de 5 dos 9 bots e o kick do excedente não aparecem no log nos dois mapas (com 0 fronteira, não é perda do reconstruído); a TUI loga `CT 6 : TR 4` na reconciliação do round 1, abortado, antes de o bot de reposição entrar (vai para o P1.7); o `.dem` não abre para escrita nos dois mapas (Q12/S1.2, não afeta a ingestão).

A `jogavel-2026-10-19-3` (`a32ef5e`) fecha o `candidato-18` (o mesmo commit, merge do PR #98 sobre o #96), o par P1.3 + P1.4 da exceção do Victor de 19/10 ao trilho único ([sprints](../agents/sprints.md#exceções-aprovadas)): P1.3, o watcher isolado de report, home e stats; P1.4, o aviso quando a captura não carregou. Validado pela partida 91 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--partida events_91_map0 --build-esperada 2000933`, sobre o log reconstruído e a cópia do banco em `mode=ro`; Históricos dos cards 82 e 83 e mensagem da tag).
G6 n/a: os dois cards não tinham infra nem janela. O compose não mudou desde o `candidato-15` (`git diff 0164cc3 a32ef5e` vazio no compose, no `docker-compose.vanilla.yml`, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `807b940d…`), e o config-hash seguiu `837cbcbc…` = H_off.

- **Container:** o mesmo da `jogavel-2026-10-19-2`, na mesma subida (`Created` 2026-10-17T19:33:02Z, `StartedAt` 2026-10-19T18:52:48Z, Restarts 0), que passou pela partida 90 e pela janela T2 de 19/10 sem restart. O `start_match` o achou rodando.
- **Coleta G7** (HEAD `a32ef5e`, 19/10 23:29 em -03, sem janela, preflight 0): os 21 caminhos montados iguais ao checkout, o config-hash do container igual ao do compose, `837cbcbc…`. A partida carregou às 01:32:17Z (`loadmatch` e `changelevel de_anubis`), o Victor entrou às 01:43:26Z (`SIGNONSTATE_FULL`), saiu no warmup às 01:43:35Z e voltou às 01:50:39Z; o `StartLive` veio às 01:54:47Z e o `MAP ENDED` e o `MATCH ENDED` do matchid 91 às 02:17:54Z. A saída dele (`DISCONNECT_BY_USER`, 02:18:05Z) foi depois do fim.
  Desde o `StartedAt`: zero segfault, `FATAL`, `Fatal error`, `Stack overflow`, `core dumped` e overflow. Os 27 `Error invoking callback` são os do BotBuyPatch, 3 por `changelevel`: nas cargas das partidas 89, 90 e 91 (01:32:18Z, antes de o Victor entrar) e nas 6 viradas da janela T2; nenhum entre 01:33Z e o fim.
- **Evidência** (`evidencia_partida.py` sobre a coleta e a cópia, fase 2 do QA): build 2000933 = a esperada, ingerida (id 56, 13x3), 18 sha256 conferidos sem divergência. P1.3: no log da partida (sha256 `ce30409f…`), zero `[AVISO]` e `[ERRO]`, e o `[REPORT]` e o `[HOME]` às 23:17:55, depois do `[MATCH] matchid=91 finalizado` (23:17:54). P1.4: `[CAPTURA] Plugin de captura carregado` às 22:32:17, e nenhum `CAPTURA NÃO CARREGADA`. O `CT 6 : TR 4` do log é a leitura velha do card 86.
- **Log reconstruído:** o `docker-logs.txt` saiu vazio, e o `jogavel.py coletar` (B0.7h) juntou 24 leituras `--tail N` em `docker-logs-reconstruido.txt` (22747 linhas, de 2026-10-18T03:02:10Z a 2026-10-20T02:29:17Z; o boot desta subida está inteiro). O LEIAME lista 1 fronteira, com 1 entrada ilegível entre 18/10 03:02:10Z e 19/10 18:52:50Z, antes do boot e fora da partida. Vale a ressalva do QA na `jogavel-2026-10-19-2`: o reconstruído também perde linhas dentro do segmento.
- **Nota de processo:** o checkout principal chegou ao `a32ef5e` por um `merge --ff-only` manual do servidor (19/10 ~22:20, em detach, sem janela e fora do `jogavel.py`), então o `data/candidato.json` não foi gravado e a TUI não mostrou `Candidato em teste` (o log da partida não tem a linha). O G7 vale pelo HEAD da coleta (`a32ef5e`, o próprio `candidato-18`).

A `jogavel-2026-10-19-2` (`0164cc3`) fecha o `candidato-17` (o mesmo commit, merge do PR #95; P1.1d: a morte de pós-jogo pelo world não vira mais órfão), validado pela partida 89 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--build-esperada 2000933`, sobre o log reconstruído e a cópia do banco em `mode=ro`; Histórico do card 80,9 e mensagem da tag).
G6 n/a: o card não tinha infra nem janela. O compose não mudou desde o `candidato-15` (`git diff 54ef88d 0164cc3` vazio no compose, no `docker-compose.vanilla.yml`, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `807b940d…`), e o config-hash seguiu `837cbcbc…` = H_off: a válvula segue off.

- **Container:** o mesmo da `jogavel-2026-10-19`, na mesma subida (`Created` 2026-10-17T19:33:02Z, `StartedAt` 2026-10-19T18:52:48Z, Restarts 0; Histórico do card 80,9). O `start_match` o achou rodando (`Container 'cs2-spike' já está rodando`, log da partida), e o boot é o da partida 88, descrito abaixo.
- **Coleta G7** (HEAD `0164cc3`, 19/10 17:49 em -03, sem janela, preflight 0): os 21 caminhos montados iguais ao checkout, o config-hash do container igual ao do compose, `837cbcbc…`, e o `pre.sh` sem CR. A partida carregou às 20:07:40Z (`loadmatch` e `changelevel de_dust2`), o Victor entrou às 20:08:13Z (`SIGNONSTATE_FULL`), o `StartLive` veio às 20:09:47Z e o `MAP ENDED` e o `MATCH ENDED` do matchid 89 às 20:37:54Z. A saída dele (`DISCONNECT_BY_USER`, 20:38:08Z) foi depois do fim.
  Desde o `StartedAt`: zero segfault, `FATAL`, `Fatal error`, `Stack overflow`, `core dumped` e overflow. Os 3 `Error invoking callback` são os do BotBuyPatch (`OnRoundStart`, `PlayerPawn` nulo) no `changelevel` da carga (20:07:46Z–20:07:47Z), antes de o Victor entrar: o ruído conhecido das partidas 83 a 85.
- **Evidência** (`evidencia_partida.py` sobre a coleta e a cópia, fase 2 do QA): build 2000933 = a esperada, arquivada, ingerida (id 54, 13x7), 5x5, 18 sha256 conferidos sem divergência, `current.jsonl` com cauda normal (round 21) e nenhum `orphan_*` novo (os mesmos 3 da cópia da partida 88). O `Times após reconciliação: CT 6 : TR 4` do log da partida é leitura velha: a partida rodou 5x5 em todo round que conta (nota do QA; card 86).
- **Log reconstruído:** o `docker-logs.txt` saiu vazio (0 bytes, json-file corrompido, como no P1.1c), e o `jogavel.py coletar` (B0.7h) juntou 30 leituras `docker logs -t --tail N` em `docker-logs-reconstruido.txt` (4601 linhas, de 2026-10-18T03:02:10Z a 2026-10-19T20:49:07Z; o boot desta subida está inteiro). O LEIAME lista 2 fronteiras: a de 1 entrada ilegível entre 18/10 03:02:10Z e 19/10 18:52:50Z, antes do boot e fora da partida, a mesma do P1.1c; e uma sem entrada ilegível (`20:49:07Z | 0 entrada(s) ilegível(is) | 18:52:50.512Z`). As perdas conhecidas, nas palavras dele: "1 entrada(s) ilegível(is) nas fronteiras, e ao menos a entrada corrompida de cada fronteira sem leitura vazia". E "em linhas com o mesmo carimbo a ordem pode diferir da original".
  Ressalva (nota do QA): o log reconstruído também perde linhas dentro do segmento, não só na fronteira ilegível. As linhas 1 a 2259 são iguais, uma a uma, às do reconstruído da coleta do P1.1c (a mesma subida, até 19:32:45Z).

A `jogavel-2026-10-19` (`54ef88d`) fecha o `candidato-16` (o mesmo commit, merge do PR #93; P1.1c: com o Docker Desktop fora do ar, o `start_match` avisa e para antes do compose), validado pela partida 88 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--build-esperada 2000933`, sobre o log reconstruído lido com `-t` e a cópia do banco em `mode=ro`; Histórico do card 80,8 e mensagem da tag).
G6 n/a: o card não tinha infra nem janela. O compose não mudou desde o `candidato-15` (`git diff 1b5b5d3 54ef88d` vazio no compose, no `docker-compose.vanilla.yml`, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `807b940d…`), e o config-hash seguiu `837cbcbc…` = H_off: a válvula segue off.

- **Container:** o do recreate da janela de 17/10 (`Created` 2026-10-17T19:33:02Z). Parou com o Docker Desktop ([armadilha da parada noturna](../armadilhas/windows-e-docker.md#docker-desktop-para-de-madrugada-exit-0x40010004)), e o `start_match` o achou parado e o subiu pelo compose, sem recreate (`StartedAt` 2026-10-19T18:52:48Z, Restarts 0). Boot: `already up to date` na 2000933, MatchZy 0.8.15 `LOADED`, CSSharp v1.0.375, 9 `Finished loading`, `m_gameState = 0x50F8` e `Applied 40/40 patches.`
- **Coleta G7** (HEAD `54ef88d`, 19/10 16:33 em -03, sem janela, preflight 0): os 21 caminhos montados iguais ao checkout, o config-hash do container igual ao do compose, `837cbcbc…`, e o `pre.sh` sem CR. A partida carregou às 18:53:04Z (`loadmatch`, e `changelevel de_ancient` às 18:53:05Z), o Victor entrou às 18:53:54Z (`SIGNONSTATE_FULL`), o `StartLive` veio às 18:54:15Z e o `MAP ENDED` do matchid 88 às 19:21:07Z. A saída dele (`DISCONNECT_BY_USER`, 19:21:16Z) foi depois do fim.
  Do `StartedAt` à coleta (19:32:45Z): zero segfault, `FATAL`, `Fatal error`, `Stack overflow`, `core dumped`, overflow e `Error invoking callback` (até ali, nem os 3 do BotBuyPatch no `changelevel` das partidas 83 a 85; eles voltaram na carga da partida 89, acima).
- **Log reconstruído:** o `docker-logs.txt` saiu vazio (json-file corrompido pela parada noturna), e o `jogavel.py coletar` (B0.7h) juntou 18 leituras `docker logs -t --tail N` em `docker-logs-reconstruido.txt` (2259 linhas, de 2026-10-18T03:02:10Z a 2026-10-19T19:32:45Z). A única perda que o LEIAME lista é 1 entrada ilegível na fronteira entre 18/10 03:02:10Z e 19/10 18:52:50Z (ver a ressalva do QA na `jogavel-2026-10-19-2`, acima), antes do boot desta subida e fora da partida (LEIAME da coleta).
- Sobra conhecida: a cauda `orphan_20261019T185248Z.jsonl` que o `start_match` preservou na subida é a cauda pós-jogo da partida 87, não sobra da parada noturna (P1.1d, card 80,9).

A `jogavel-2026-10-17` (`1b5b5d3`) fecha o `candidato-15` (o mesmo commit, merge do PR #89; P1.2: válvula vanilla, o `docker-compose.vanilla.yml` empilhado pelo `config.compose_files()` e ligado ou desligado pelo `tools/jogavel.py vanilla on|off`, só em janela), validado pela partida 85 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--build-esperada 2000933`; Histórico do card 81 e mensagem da tag).
A partida jogou com a válvula **off**: compose, mounts e config-hash (`837cbcbc…`) iguais aos da `jogavel-2026-10-16`. O on só existiu entre as duas janelas, e nenhuma partida rodou nele.

- **Vanilla on, janela de 16/10** (aberta às 14:45:22): o container estava `Exited (255)` desde 10:17 em -03 (parada brusca do Docker). Fast-forward `9c9b648` → `1b5b5d3`, `vanilla on` das 14:48:24 às 14:49:07, boot de ~29 s, build 2000933 antes e depois.
  G6 do on OK: MatchZy `LOADED`, 3 `Finished loading` (MatchZy, CS2 Tracker Events e RoundDamageRecap), nenhuma linha dos 6 plugins de bot, 19 mounts com os 6 de bot em `_empty`, os 6 sha256 montados iguais ao checkout, `pre.sh` sem CR e config-hash `0f3ff2b2…`, diferente do H_off.
- **Ressalva da janela de 16/10:** ela venceu às 15:30:22, no meio do G6 do on, com a aprovação de um `docker exec` do G6 esperando ~1 h 15. Depois do vencimento só houve leitura (o RCON do fechamento, às 16:06:58), sem mudança no ar, e o fechamento foi às 16:07. O vanilla off e o G6 dele ficaram para a janela seguinte.
- **Vanilla off, janela de 17/10** (16:32:15–16:41:14, 9 min): `vanilla off` das 16:32:59 às 16:33:47, boot de ~32 s, build 2000933 antes e depois.
  G6 do off OK: 9 `Finished loading`, `m_gameState = 0x50F8` e `Applied 40/40 patches.`, zero segfault, 15 mounts iguais aos do container H_off de 16/10 (sem `_empty` nos de bot), os 17 sha256 montados iguais ao checkout, config-hash da janela `837cbcbc…` = H_off e `data/servidor.json` com `vanilla` false. A partida 85 rodou no container desse recreate (`Created` 2026-10-17T19:33:02Z).
- **Coleta G7** (HEAD `1b5b5d3`): os 21 caminhos montados iguais ao checkout e o config-hash do container igual ao do compose, `837cbcbc…`. A partida subiu às 20:41:26Z (`loadmatch` e `changelevel de_inferno`), o Victor conectou às 21:01:25Z, o `StartLive` veio às 21:02:30Z e o `MAP ENDED` do matchid 85 às 21:25:36Z.
  Sobras conhecidas: os 3 `Error invoking callback` do BotBuyPatch no `changelevel` (20:41:30Z), como nas partidas 83 e 84, e 3 linhas `recv queue overflow` às 21:01:26Z, logo depois da entrada do Victor (S3 de [engine-cs2](../armadilhas/engine-cs2.md#assinatura-e-como-contar)), sem queda.

A `jogavel-2026-10-16` (`9c9b648`) fecha o `candidato-14` (o mesmo commit, merge do PR #86; P1.1b: sufixo `__utc` nas ferramentas e fim sem linha fantasma no watcher), validado pela partida 84 (saída do `evidencia_partida.py` com `--build-esperada 2000933`: `VEREDITO G7: OK`, sem sufixo nem aviso de colisão, zero segfault e zero overflow; Histórico do card 80,7).
G6 n/a: o card não tinha infra nem janela. O compose não mudou desde o `candidato-13` (`git diff 2619d70 9c9b648` vazio no compose, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `807b940d…`), e o config-hash seguiu `837cbcbc…`.
O container é o do 2º recreate de 14/10 (`Created` 2026-10-15T00:15:44Z): parou junto com o Docker Desktop na madrugada de 15/10 ([armadilha da parada noturna](../armadilhas/windows-e-docker.md#docker-desktop-para-de-madrugada-exit-0x40010004)) e subiu pela TUI às 21:30:01 em -03. Nesse boot o SteamCMD trouxe a 2000933 sem janela ([Épocas de build](#épocas-de-build)), e o boot levou ~2 min 48 s do `StartedAt` ao `Pronto`.
Sobras conhecidas, iguais às da partida 83: 3 `Error invoking callback` do BotBuyPatch no `changelevel`. O log da coleta foi reconstruído pelo fim (`docker-logs.txt` vazio), com 1 entrada ilegível na fronteira da parada de 15/10 (LEIAME da coleta).

**Ressalva do BotAI na 2000933:** o fork carregou como na 2000931 (`m_gameState = 0x50F8` e `Applied 40/40 patches.` no boot, e a partida 84 sem segfault), mas a conferência do [B1.7b](b1.7b-botai-fork-assinatura.md#a-cada-build-nova-do-cs2) sobre o `libserver.so` da 2000933 ainda não rodou, e nenhuma cópia desse binário foi guardada. Até ela rodar, o 40/40 é a única evidência do fork nesta build.
Atualização da janela de 16/10 (14:46–14:47, com o container parado): o `libserver.so` da 2000933 foi copiado só leitura para `C:/Users/Victor/cs2-tracker-backups/2026-10-16/libserver-2000933/`, e a conferência deu `RESULTADO: OK`. O binário é o mesmo da 2000931 (`d73f5d3b…`, 41726328 bytes).

A `jogavel-2026-10-14-3` (`2619d70`) fecha o `candidato-13` (o mesmo commit; B1.7: o BotAI religado pelo bind do fork do [B1.7b](b1.7b-botai-fork-assinatura.md), no compose e no `.gitignore`), aplicado na janela de 14/10 (20:57–21:24 em -03) e validado pela partida 83 (saída 0 do `evidencia_partida.py` com `--build-esperada 2000931`, `VEREDITO G7: OK`; Histórico do card 26).
G6 na janela: BotAI com `m_gameState = 0x50F8` e `Applied 40/40 patches.`, zero segfault, 9 plugins, os 17 arquivos montados iguais ao checkout e config-hash novo `837cbcbc…`, porque o compose mudou (a máscara do BotAI virou bind).
Na partida, o BotAI ficou em 40/40 do boot ao fim, com 12 bombas plantadas (3 por bot e 9 pelo Victor) e 2 defuses, os dois de bot.
A build mudou na mesma janela: o 1º recreate trouxe a 2000931 ([Épocas de build](#épocas-de-build)), e o fork só voltou ao ar depois da conferência dele nessa build.
O container é o do 2º recreate (`Created` 2026-10-15T00:15:44Z).

A `jogavel-2026-10-14-2` (`eb4cb0e`) fecha o `candidato-12` (o mesmo commit; B1.9b: o BotRandomizer do upstream `276f1ce` com o `4628750` por cima, compilado para a 2000930; [runbook](b1.9b-botrandomizer-2000930.md)), aplicado na janela de 14/10 (18:56–19:19 em -03) e validado pela partida 82 (mensagem da tag).
O merge (PR #78) só traz o runbook: a DLL nova (`cfe7efc0…`) é gitignored, e o servidor a trocou na pasta do bind com o container parado. O compose não mudou (`git diff 40b3826 eb4cb0e` vazio no compose, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `2a889474…`), e o config-hash seguiu `3970b702…`.
G6 na janela: build 2000930 antes e depois, 8 plugins, catálogo do BotRandomizer carregado, zero `signature failed`, os 14 montados iguais ao checkout (BotRandomizer = manifesto do b1.9b) e smoke só de bots sem `Failed to prepare a weapon item view` nem `Invalid function pointer`.
A partida 82 rodou no container dessa janela (`Created` 2026-10-14T22:06:31Z), e a coleta dela também não tem nenhum `Failed to prepare a weapon item view`: a regressão abaixo acabou ali.

A `jogavel-2026-10-14` (`b8b492f`) fecha o `candidato-11` (`ac844b1`, P1.1a: colisão de `demo_name` nunca descarta partida), validado pela partida 81 (14/10, `VEREDITO G7: OK` do `evidencia_partida.py` na cópia `g7-p1.1a-copia`, mensagem da tag).
O `ac844b1` é ancestral do `b8b492f`, e o delta entre os dois é só docs, tools, tests e o `README.md`. G6 n/a: o card não tinha infra nem janela.
O container era o da Janela 0, reiniciado em 14/10 sem recreate (`Created` 2026-10-02T03:30:20Z, `StartedAt` 2026-10-14T21:09:39Z, `RestartCount` 0, LEIAME da coleta): config-hash `3970b702…` e os 19 caminhos montados iguais ao checkout. O log da coleta foi reconstruído pelo fim, como nas de 12/10 e 13/10 (`docker-logs.txt` vazio).
O BotRandomizer ainda era o do B1.9: o boot teve o `Failed to prepare a weapon item view` da regressão abaixo.

A `jogavel-2026-10-13` (`40b3826`) fechou o `candidato-10` (`db59470`, P1.1: órfão real preservado, log em arquivo e aviso de candidato), validado pela partida 80 (13/10, saída 0 do `evidencia_partida.py` com `--build-esperada 2000930`, G7 OK; Histórico do card 80).
O `db59470` é ancestral do `40b3826`, e o delta entre os dois é só docs, tools e tests. G6 n/a: o card não tinha infra nem janela.
O compose não mudou desde o `candidato-8` (`git diff abd19aa 40b3826` vazio no compose, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`; blob LF `2a889474…`).
O container era o da Janela 0, sem reinício desde o boot de 12/10 (`StartedAt` 2026-10-12T21:37:09Z, `RestartCount` 0, `container-inspect.txt`): imagem, volume, mounts e config-hash (`3970b702…`) eram os da `jogavel-2026-10-12`, e os 19 caminhos montados bateram com o checkout.
A janela de diagnóstico de 13/10 (B1.12b, 22:48–23:17 em -03, depois da partida 80) não mudou nada no ar: checkout `c60009a`, container sem recreate nem reinício, 19 montados iguais ao checkout e config-hash igual (`sha-comparacao.txt` da `2026-10-13/janela-diag/`).

**Regressão do BotRandomizer na 2000930, corrigida pelo B1.9b** (do boot de 12/10 à janela do B1.9b em 14/10; partidas 79, 80 e 81): as armas
dos bots vêm sem skin, e as facas seguem com skin (relato do Victor, card K1.12). O log tem um
erro só, no primeiro `GiveNamedItem` do boot (12/10 21:38:43Z): `[BotRandomizer] Failed to
prepare a weapon item view`, com `NativeException: Invalid function pointer` em
`WeaponItemViewStore.cs:57` (`skins-extrato.txt` da coleta de 13/10). Nos boots da 2000924
(04/10 e 05/10), nenhum erro do BotRandomizer. Sem crash. O plugin é o mesmo da
`jogavel-2026-09-28` (os 5 arquivos montados = manifesto do [B1.9](b1.9-botrandomizer-upstream.md)):
mudou a build, não o plugin. A correção é a `jogavel-2026-10-14-2` (acima), e a leitura do
mecanismo está na sobra 7 da [trilha](trilha-de-bots.md#sobras).

A `jogavel-2026-10-12` (`abd19aa`) fechou o `candidato-9` (`5a50fcb`, T1.3c: placeholder da TUI e comentário do parser sem o SteamID e o nick reais), validado pela partida 78 (05/10, G7 OK) e confirmado pela 79 (12/10, saída 0 do `evidencia_partida.py`). O `5a50fcb` é ancestral do `abd19aa`, e o delta entre os dois não tem arquivo do caminho de jogo. G6 n/a: o card não tinha infra nem janela.
O compose não mudou desde o `candidato-8` (`git diff 063b8a4 abd19aa` vazio no compose, em `docker/pre.sh`, `docker/plugins*` e `server-configs/`), e o container é o da Janela 0 (`Created` 2026-10-02T03:30:20Z, `container-inspect.txt`): imagem, volume, mounts e config-hash são os da `jogavel-2026-10-03`. O que mudou sem commit foi a build, duas vezes, por update do SteamCMD no boot ([Épocas de build](#épocas-de-build)).

A `jogavel-2026-10-03` (`063b8a4`) fechou o `candidato-8` (`214b25b`, B0.8), aplicado na Janela 0 (02/10) e validado pela partida de 03/10 (G7 OK). O `214b25b` é ancestral do `063b8a4`, e o delta entre os dois é só docs, tools e tests, sem infra.
O B0.8 só mudou o compose (volume `cs2-data` external, com nome fixo): o volume, os mounts e o config-hash são os da `jogavel-2026-10-01` ([inventário do volume](inventario-volume.md)).

Ressalva sobre a dificuldade da `jogavel-2026-10-12` e da `jogavel-2026-10-13`: o Low também é
inferido, pelo mesmo caminho da `jogavel-2026-10-03`. As coletas de 12/10 e de 13/10 não leram
o sha do VPK ativo, e os logs reconstruídos não têm nenhum "BOT Difficulty". Da Janela 0 até a
partida 80 não houve janela (o registro seguinte ao de 02/10 em `logs/janelas/` é o de 13/10, da
janela de diagnóstico depois da partida 80, que não tocou no VPK), e o VPK só se troca em
janela, com o servidor parado. Os quatro boots do log (04/10 17:18Z, 05/10 22:25Z e 23:12Z,
12/10 21:37Z) são restarts do mesmo container, e o de 12/10 seguiu de pé até a coleta de 13/10. Na `jogavel-2026-10-14` vale o mesmo: entre a partida 80 e a 81 só houve a janela de diagnóstico, e a partida 81 rodou no mesmo container, reiniciado em 14/10 sem recreate.

**Log da coleta de 12/10:** foi reconstruído. O `docker-logs.txt` do `jogavel.py coletar` saiu vazio, porque o json-file do container tem entradas corrompidas logo depois de 2026-10-05T02:44:21Z e de 2026-10-06T04:04:33Z (paradas bruscas, sem linhas de desligamento), e o `docker logs` lendo para a frente para em silêncio na primeira delas, com código 0. O servidor juntou leituras `docker logs -t --tail N` (só leitura, preflight 0) em `docker-logs-reconstruido.txt` (sha256 `77fbb6ca…`, igual ao `sha256-coleta-extra.txt`), que cobre de 2026-10-04T16:49:25Z até a coleta e perde só a entrada corrompida de cada fronteira.
O detalhe está no `docker-logs-reconstruido.LEIAME.txt` da coleta. O G7 da partida 78 e a confirmação da 79 foram julgados sobre trechos desse arquivo, um por boot.
A coleta de 13/10 repetiu o caso (`coletar` saiu 8, `docker-logs.txt` vazio): o `docker-logs-reconstruido.txt` dela (sha256 `5099a568…`, igual ao `sha256-coleta-extra.txt`) cobre de 2026-10-02T03:30:25Z até a coleta, com o segmento do boot de 12/10 contínuo (13937 linhas), e o G7 da partida 80 foi julgado sobre esse segmento.

Ressalva do QA sobre a dificuldade da `jogavel-2026-10-03`: o Low é inferido, não lido na partida. O log não anuncia a dificuldade (nenhum "BOT Difficulty" na coleta) e a coleta não leu o sha do VPK ativo. O Low vem do inventário da Janela 0 (`overrides/botprofile.vpk` = `02e5e958…`, 02/10), e o container não foi recriado depois dela (`Created` 2026-10-02T03:30:20Z) nem houve janela até a partida.
Pelo critério 8 da [trilha](trilha-de-bots.md#critérios-de-sucesso-de-cada-passo), a variante dessa tag fica registrada como **inferida**.

Na `jogavel-2026-10-01`, o compose é o mesmo da `jogavel-2026-09-28`. As duas variáveis que
entraram depois dela, sem commit, foram validadas juntas na partida 36 (época "VPK Low" da
[trilha](trilha-de-bots.md#épocas)): o VPK Low desde 28/09 19:54 e a build 2000922, que veio do SteamCMD no restart da janela de 30/09
(a 2000919 de 28/09 ficou para trás). Por isso a tag não tem candidato. Ressalva: o Low já
tinha sido jogado na build 2000919 (`events_70`, MD3 de 30/09, antes da janela), sem coleta G7
nem tag; esta é a primeira partida com G7 do Low, e já na 2000922. A build não volta por git:
o SteamCMD atualiza o CS2 a cada start, e o cliente do Victor precisa da mesma build. A
`jogavel-2026-09-28` (VPK Medium, build 2000918) fica como a última combinação com a build
antiga.

VPK, por variante no volume (`overrides/<variante>/botprofile.vpk`): Low `02e5e958…`, Medium
`ba754b61…`, High `b08bf74e…`. O ativo é `overrides/botprofile.vpk`. Nas duas primeiras tags,
o ativo foi lido só na troca de 27/09 15:34, antes do `cp`: `b08bf74e…`, o High. Na
`jogavel-2026-09-28`, a coleta G7 leu `ba754b61…`, o Medium. Na `jogavel-2026-10-01`, leu
`02e5e958…`, o Low (`sha-vpk.txt` da coleta). Na `jogavel-2026-10-03`, na `jogavel-2026-10-12`
e na `jogavel-2026-10-13`, a coleta não leu o VPK: o `02e5e958…` é o do inventário da Janela 0
(ressalvas acima). Nas três tags de 14/10 também não: nenhuma das janelas de 14/10 escreveu no volume. Na `jogavel-2026-10-16` também não, e não houve janela desde as de 14/10. Na `jogavel-2026-10-17` também não: as janelas do P1.2 não escreveram no volume. Na `jogavel-2026-10-19` também não, e não houve janela desde a de 17/10. Na `jogavel-2026-10-19-2` também não, pelo mesmo motivo. Na `jogavel-2026-10-19-3` também não: a janela T2 de 19/10 não escreveu no volume. Na `jogavel-2026-10-20` também não: a janela T2 de 20/10 só reiniciou o container e virou mapas, sem trocar o VPK. Na `jogavel-2026-10-21` também não: o par P1.7 + P1.8 não teve janela. Na `jogavel-2026-10-25` o VPK foi **lido**: a janela de 22/10 leu `overrides/botprofile.vpk` = `02e5e958…`, o Low (com o Medium e o High iguais aos de referência), e as janelas seguintes não escreveram em `overrides/` (a de 23/10 só ligou a válvula; a de 25/10 só extraiu a CSSharp em `addons/`). Na `jogavel-2026-10-26` e na `jogavel-2026-10-26-2` não foi lido: as três janelas de 26/10 não escreveram em `overrides/` (a de 13:48 só apagou o `match_config.spike.json` residual em `game/csgo/`), e as coletas não leram o VPK. Na `jogavel-2026-11-04` também não: as duas janelas de 04/11 só recriaram o container (o SteamCMD da de 12:09 atualizou o jogo, fora de `overrides/`) e não leram o VPK, e a coleta também não. Na `jogavel-2026-11-04-2` também não: não houve janela desde a de 04/11 17:41, e a coleta não leu o VPK. Na `jogavel-2026-11-08` foi **lido** e **trocado**: a janela de 06/11 (B1.16) leu o ativo `02e5e958…` (Low) às 17:35:44, copiou o Medium sobre ele com o servidor parado às 17:39:05 e releu `ba754b61…` (Medium) logo depois e às 17:51:09; a coleta de 08/11 leu de novo o Medium (`vpk-ativo.txt`, 20:33:52Z). Na `jogavel-2026-11-09` também foi lido: `ba754b61…` no G6 e no fechamento da janela de 08/11 e na coleta de 09/11 (`sha-vpk.txt`, com as três variantes iguais às de referência).

### Épocas de build

A build não volta por git: o SteamCMD da imagem atualiza o CS2 em todo start do container, sem
janela nem OK prévio. Cada época abaixo começa no boot em que o log mostra o download
(`Success! App '730' fully installed`) e a build nova no `GC Connection established for server
version`. As anteriores (2000918, 2000919 e 2000922) estão na tabela de tags e na época "VPK
Low" da [trilha](trilha-de-bots.md#épocas).

| Build | Desde | Origem | Partida que validou | Tag |
|---|---|---|---|---|
| 2000924 | 04/10 17:18Z (14:18 em -03), no boot que seguiu o segfault de 17:15:26Z (B1.12) | update do SteamCMD no boot, sem janela nem OK prévio | partida 78 (05/10, de_cache 13x8, G7 OK). A partida 76 (04/10, matchid 76) já jogou nela antes do `candidato-9`, sem G7 | `jogavel-2026-10-12` |
| 2000930 | 12/10 21:37:11Z (18:37 em -03), no boot do container; download terminado às 21:37:57Z | update do SteamCMD no boot, sem janela nem OK prévio | partida 79 (12/10, de_mirage 13x2), como confirmação: saída 0 do `evidencia_partida.py` no trecho desse boot. Na época a ferramenta não lia a linha da build e mostrava `build ?`; a build saiu do log. Desde o H1.1c (`8310527`) ela lê a build da linha `GC Connection established for server version`, e o `--build-esperada` avisa build diferente da da janela. Validada de novo pela partida 80 (13/10, de_ancient 13x5, G7 OK com `--build-esperada 2000930`). Nela o BotRandomizer perdeu as skins das armas (regressão acima), e o B1.9b as devolveu: partidas 81 (P1.1a, G7 OK, ainda sem skin) e 82 (B1.9b) | `jogavel-2026-10-12`, `jogavel-2026-10-13`, `jogavel-2026-10-14` e `jogavel-2026-10-14-2` |
| 2000931 | 14/10 21:07 em -03 (download terminado às 00:07:02Z de 15/10), no 1º recreate da janela do B1.7 | update do SteamCMD no boot, dentro de uma janela, sem OK prévio para a build | partida 83 (14/10, de_nuke 13x3, G7 OK com `--build-esperada 2000931`). Antes do G6, o servidor conferiu o fork do BotAI na cópia do `libserver.so` dela (`RESULTADO: OK`, abaixo) | `jogavel-2026-10-14-3` |
| 2000933 | 2026-10-16T00:30:01Z (15/10 21:30 em -03), no boot pela TUI depois da parada noturna do Docker Desktop; download terminado às 00:32:41Z | update do SteamCMD no boot, sem janela nem OK prévio. A 1ª tentativa falhou com `Error! App '730' state is 0x6 after update job`; a 2ª removeu o appmanifest e verificou a instalação inteira (73389778054 bytes, ~73,4 GB) antes do download. Do `Checking for available updates` (00:30:03Z) ao `Success! App '730' fully installed` (00:32:41Z): ~2 min 38 s | partida 84 (15/10 em -03, de_anubis 13x5, G7 OK com `--build-esperada 2000933`). O BotAI do fork carregou 40/40, e a conferência dele nesta build rodou na janela de 16/10, com `RESULTADO: OK` (ressalva acima). De novo na partida 85 (17/10, de_inferno 13x3, G7 OK com `--build-esperada 2000933`) na 88 (19/10, de_ancient 13x4, G7 OK com `--build-esperada 2000933`) na 89 (19/10, de_dust2 13x7, G7 OK com `--build-esperada 2000933`) na 91 (19/10, de_anubis 13x3, G7 OK com `--build-esperada 2000933`) e na MD3 de matchid 93 (20/10, de_inferno 13x5 e de_cache 16x14, G7 OK nos dois mapas, build 2000933) | `jogavel-2026-10-16`, `jogavel-2026-10-17`, `jogavel-2026-10-19`, `jogavel-2026-10-19-2`, `jogavel-2026-10-19-3` e `jogavel-2026-10-20` |
| 2000934 | 2026-10-21T21:57:21Z (18:57 em -03), na subida pela TUI do container parado pela queda do Docker Desktop; download terminado às 22:01:57Z | update do SteamCMD no boot, sem janela nem OK prévio. A 1ª tentativa falhou com `Error! App '730' state is 0x6 after update job` (21:57:33Z); a 2ª verificou a instalação inteira (73389778054 bytes, ~73,4 GB; de 21:57:41Z a 22:01:43Z), baixou o resto da atualização (22:01:45Z a 22:01:49Z) e terminou com `Success! App '730' fully installed` às 22:01:57Z. Do `StartedAt` ao `Pronto` da captura (22:02:06Z): ~4 min 45 s | partida 96 (21/10, de_inferno 13x5, G7 OK com `--build-esperada 2000934`). No boot: BotAI do fork com `m_gameState = 0x50F8` (OnUpdate e OnBombPlanted concordam, como na 2000933) e `Applied 40/40 patches.`, 9 plugins carregados e nenhuma assinatura falha. **Ressalva:** a conferência formal do BotAI do fork nesta build (B1.7c: `conferir_botai` sobre a cópia do `libserver.so` da 2000934, [a cada build nova](b1.7b-botai-fork-assinatura.md#a-cada-build-nova-do-cs2)) ainda não rodou: a cópia sai do container e pede janela, e o fork jogou a partida 96 sem ela. Não rodou nunca: o recreate da janela de 22/10, que a faria, já trouxe a 2000935 | `jogavel-2026-10-21` |
| 2000935 (CS2 v1.41.9.2) | 2026-10-22T22:55:58Z (19:55:58 em -03), no recreate da janela de 22/10 (P1.10); download terminado às 22:59:44Z | update do SteamCMD no boot, dentro de uma janela, sem OK prévio para a build. Do recreate ao `Pronto` da captura: ~3 min 55 s | partida 97 (25/10, de_inferno 13x0, G7 OK com `--build-esperada 2000935`), já com a CSSharp v1.0.378 e a válvula vanilla on. O BotAI do fork foi conferido nela na janela de 22/10 (B1.7c: `libserver.so` de 41804088 bytes, `RESULTADO: OK`, 40/40, `m_gameState` 0x50F8, distância do TBot 0x2f0; boot com `Applied 40/40 patches.` e zero `patch disabled`). Antes da correção, a CSSharp v1.0.375 caía com humano nela: ver a quebra abaixo. De novo na partida 100 (26/10, de_ancient 13x4, válvula on) e na 101 (26/10, de_dust2 13x4, já com os 6 plugins de bot, conferidos offline nela pelo `tools/conferir_plugins_bot.py`), as duas com G7 OK e `--build-esperada 2000935` | `jogavel-2026-10-25`, `jogavel-2026-10-26` e `jogavel-2026-10-26-2` |
| 2000940 (CS2 v1.41.9.5) | 2026-11-04T15:11:21Z (12:11 em -03), no recreate do `vanilla on` da janela de 04/11 12:09; download terminado às 15:15:10Z | update do SteamCMD no boot, dentro de uma janela, sem OK prévio para a build. A 1ª tentativa falhou com `Error! App '730' state is 0x6 after update job` (15:12:03Z); a 2ª removeu o appmanifest, verificou e baixou. Do recreate ao `Pronto` da captura: ~4 min 08 s | partida 107 (04/11, de_dust2 13x1, G7 OK com ressalva), já com os 6 plugins de bot, conferidos offline nela antes da janela de 17:41 ([B1.15](b1.15-plugins-de-bot-2000940.md): `RESULTADO: OK` nas duas conferências, 40/40 do BotAI, as 28 assinaturas do gamedata da 1.0.378 casando 1 vez). O cliente do Victor também foi para a 2000940. Depois, a partida 108 (04/11, de_mirage 13x5, G7 OK), no mesmo container | `jogavel-2026-11-04` e `jogavel-2026-11-04-2` |
| 2000942 (CS2 v1.41.9.6) | 2026-11-05T21:48:40Z (18:48 em -03), no recreate do `vanilla on` da janela de 05/11 18:25; download terminado às 22:04:14Z, `GC Connection established for server version 2000942` às 22:04:39Z | update do SteamCMD no boot, dentro de uma janela, sem OK prévio para a build; motivo da janela: o cliente do Victor já estava nela ("client out of date"). A 1ª tentativa falhou com `Error! App '730' state is 0x6 after update job` (21:49:39Z); a 2ª verificou a instalação inteira (73,4 GB) e baixou. Do recreate ao `Pronto`: ~16 min, e o `jogavel.py` desistiu antes (sem `Pronto` em 10 min); a janela venceu com o G6 por RCON pendente | MD3 de matchid 112 (08/11, de_dust2 16x12 e de_mirage 13x7, G7 OK com ressalva), já com o VPK Medium e os 6 plugins de bot, conferidos offline nela na janela de 06/11 (`libserver.so` de 41850680 B, `ee0cc32a…`; `RESULTADO: OK` nas duas conferências, 40/40 do BotAI). Depois, a 113 e a MD3 114 (09/11, G7 OK com `--build-esperada 2000942`), sem o BotAimImprover | `jogavel-2026-11-08` e `jogavel-2026-11-09` |

**Quebra da CSSharp v1.0.375 na 2000935** (de 22/10 à janela do B1.3s em 25/10; nenhuma partida
completa): o servidor caiu com `Segmentation fault` nativo logo depois de o Victor entrar, 3
vezes: 23/10 21:48:26Z (16 s depois do `SIGNONSTATE_SPAWN`), 23/10 22:15:57Z (11 s) e 24/10
21:53:00Z (30 s), esta já com a válvula vanilla on. Nenhuma exceção gerenciada antes. Só bots,
no mesmo container, não cai (smoke de 23/10, 22:21–22:25Z, 10 bots e rounds rodando). A causa é
o update v1.41.9.2 do CS2: deslocamento de vtable do `IVEngineServer2` e assinaturas como
`CCSPlayerPawnBase_PostThink`. A correção oficial é o PR #1470 ("fix: Game Update v1.41.9.2") do
`roflmuffin/CounterStrikeSharp`, mergeado em 23/10, e o release v1.0.378, do mesmo dia, instalado
pelo [B1.3s](b1.3s-cssharp-1.0.378.md) na janela de 25/10. O que conferir quando acontecer de novo
está nas [armadilhas](../armadilhas/imagem-e-boot.md#depois-da-auditoria). Na mesma época, o
NadeSystem loga `Invalid function pointer` (idem), e os plugins de bot seguem fora (válvula on)
até a decisão do Victor de religá-los.

Os boots de 05/10 (22:25Z e 23:12Z) dizem `already up to date` e seguem na 2000924. O cliente
do Victor precisa estar na mesma build do servidor.

**Binário da build 2000930 guardado:** o `libserver.so` do container (ServerVersion 2000930,
PatchVersion 1.41.9.0, VersionDate Oct 08 2026; 41724600 bytes, mtime no container
2026-10-12 21:37:53Z, no boot de 12/10) foi copiado só leitura na janela de diagnóstico de
13/10 (B1.12b), para
`C:/Users/Victor/cs2-tracker-backups/2026-10-13/janela-diag/libserver-2000930/libserver.so`,
fora do repo, com o `LEIAME.txt` e o `libserver.so.sha256` ao lado. O sha256 da cópia é o mesmo
do `sha256sum` dentro do container (`c7741272…`, inteiro em [Hashes completos](#hashes-completos)).
É o insumo do B1.7a, que conferiria o offset do BotAI na build atual ([trilha](trilha-de-bots.md#sobras),
sobra 1), e de um backtrace futuro nesta build. A build não volta por git: esta cópia é o que
resta da 2000930 quando o SteamCMD trouxer a próxima.

**Binário da build 2000931 guardado:** o `libserver.so` do container (ServerVersion 2000931,
PatchVersion 1.41.9.1, VersionDate Oct 14 2026; 41726328 bytes) foi copiado só leitura na janela
do B1.7 (14/10 21:14, -03), para
`C:/Users/Victor/cs2-tracker-backups/2026-10-14/b1.7/libserver-2000931/libserver.so`, fora do
repo, com o `LEIAME.txt` e o `libserver.so.sha256` ao lado. O sha256 (`d73f5d3b…`, inteiro em
[Hashes completos](#hashes-completos)) é o mesmo do `sha256sum` dentro do container. É o insumo
da conferência do BotAI do fork nessa build
([a cada build nova](b1.7b-botai-fork-assinatura.md#a-cada-build-nova-do-cs2)).

### Candidatos

| Candidato | Commit | Card | Fechado por |
|---|---|---|---|
| `candidato-1` | `dbac993` | B1.3r | `jogavel-2026-09-27` |
| `candidato-2` | `f957875` | B1.4 (BotAimImprover do volume, inativo) | sem tag própria: jogado junto com o 3 |
| `candidato-3` | `ad8cc02` | B1.4b + VPK Medium | `jogavel-2026-09-27-2` |
| `candidato-4` | `7f09cc4` | B1.5 | `jogavel-2026-09-27-3` (mesmo compose) |
| `candidato-5` | `e838839` | B1.6 | `jogavel-2026-09-27-4` (mesmo commit) |
| `candidato-6` | `200e43f` | B1.8 | `jogavel-2026-09-27-5` (mesmo commit) |
| `candidato-7` | `6889930` | B1.9 | `jogavel-2026-09-28` (mesmo compose) |
| `candidato-8` | `214b25b` | B0.8 (volume external), aplicado na Janela 0 | `jogavel-2026-10-03` (validado; mesmo compose, no `063b8a4`) |
| `candidato-9` | `5a50fcb` | T1.3c (placeholder da TUI e comentário do parser sem o SteamID e o nick reais) | `jogavel-2026-10-12` (validado pela partida 78, confirmado pela 79; no `abd19aa`) |
| `candidato-10` | `db59470` | P1.1 (órfão real preservado, log em arquivo e aviso de candidato) | `jogavel-2026-10-13` (validado pela partida 80; no `40b3826`) |
| `candidato-11` | `ac844b1` | P1.1a (colisão de `demo_name` nunca descarta partida) | `jogavel-2026-10-14` (validado pela partida 81; no `b8b492f`) |
| `candidato-12` | `eb4cb0e` | B1.9b (BotRandomizer com o `4628750` do upstream para a 2000930; a DLL é trocada na pasta do bind), aplicado na janela de 14/10 | `jogavel-2026-10-14-2` (validado pela partida 82; mesmo commit) |
| `candidato-13` | `2619d70` | B1.7 (BotAI religado pelo bind do fork do B1.7b: compose e `.gitignore`), aplicado na janela de 14/10 | `jogavel-2026-10-14-3` (validado pela partida 83; mesmo commit) |
| `candidato-14` | `9c9b648` | P1.1b (sufixo `__utc` nas ferramentas e fim sem linha fantasma no watcher) | `jogavel-2026-10-16` (validado pela partida 84; mesmo commit) |
| `candidato-15` | `1b5b5d3` | P1.2 (válvula vanilla: `docker-compose.vanilla.yml` e `config.compose_files()`), ligada na janela de 16/10 e desligada na de 17/10 | `jogavel-2026-10-17` (validado pela partida 85, com a válvula off; mesmo commit) |
| `candidato-16` | `54ef88d` | P1.1c (com o Docker Desktop fora do ar, o `start_match` avisa e para antes do compose) | `jogavel-2026-10-19` (validado pela partida 88; mesmo commit) |
| `candidato-17` | `0164cc3` | P1.1d (a morte de pós-jogo pelo world não vira mais órfão) | `jogavel-2026-10-19-2` (validado pela partida 89; mesmo commit) |
| `candidato-18` | `a32ef5e` | par P1.3 + P1.4 (watcher isolado de report, home e stats; aviso quando a captura não carregou), por exceção do Victor ao trilho único | `jogavel-2026-10-19-3` (validado pela partida 91; mesmo commit) |
| `candidato-19` | `9e5ab8e` | P1.6 (o lado do humano por mapa, `map_sides[i]`) | `jogavel-2026-10-20` (validado junto com o `candidato-20` pela MD3 de matchid 93; ancestral do `c228d93`) |
| `candidato-20` | `c228d93` | P1.5 (os mapas 2 e 3 da série sozinhos, com teto de 3 h), em par com o P1.6 por exceção do Victor de 20/10 | `jogavel-2026-10-20` (validado pela MD3 de matchid 93; mesmo commit) |
| `candidato-21` | `29bf60f` | par P1.7 + P1.8 (contagem de presentes pelo `status` do RCON; `live_override.cfg` neutro antes do `loadmatch`), por exceção do Victor de 19/10 | nenhuma tag: reprovado pela partida 95 (a contagem do P1.7 incluía a SourceTV) e revertido pelo `6b95c77`; ver a nota no estado no ar |
| `candidato-22` | `69c45b1` | par P1.7 + P1.8 refeito (P1.7 sem a SourceTV, `6d6aa2b`; P1.8 reaplicado, `d5e61d7`) | `jogavel-2026-10-21` (validado pela partida 96; mesmo commit) |
| `candidato-23` | `ba17644` | P1.10 (plugin de captura 0.4.1 sem truncar), DLL construída na janela de 22/10. A tag registra por engano a DLL `697760a7…` (0.4.0); a certa é a `75d0d6df…` | `jogavel-2026-10-25` (validado junto com o `candidato-24` pela partida 97; ancestral do `cc17bb4`) |
| `candidato-24` | `a0b4dca` | B1.3s (CSSharp v1.0.378 oficial, instalada na janela de 25/10), em par com o P1.10 por exceção do Victor de 24/10 | `jogavel-2026-10-25` (validado pela partida 97; ancestral do `cc17bb4`, que só soma os PRs de docs #113 e #114) |
| `candidato-25` | `c67e548` | par P1.9 + P1.11 (`match_config` template × runtime em `docker/runtime/`; 27015/tcp só em 127.0.0.1), por exceção do Victor de 19/10, numa janela só | `jogavel-2026-10-26` (validado pela partida 100; ancestral do `09e54bd`, que soma o P1.9b, PR #119, só `tools/`) |
| `candidato-26` | `57e357b` | B1.13 (os 6 plugins de bot na 2000935, NadeSystem 1.2.1-b1.13 do fork local), antes de fechar a P1 por decisão do Victor de 25/10 | `jogavel-2026-10-26-2` (validado pela partida 101; mesmo commit) |
| `candidato-27` | `e4fb9d5` | K1.9 (poda de comentários no compose, no cfg, no `start_match.py`, no `watcher.py` e no `parser.py`; PRs #121, `9202cec`, sem tag, e #125). A tag é o objeto `2b8ea918` sobre o commit `e4fb9d5`. Validado em par com o B1.15 (card 29,99, só docs, sem candidato) por exceção do Victor de 04/11 | `jogavel-2026-11-04` (validado pela partida 107; ancestral do `f16121f`, que só soma o runbook do B1.15, PR #126) |
| `candidato-28` | `110bb98` | P1.15 (card 92,6: o `start_match` lê o `State.Paused` e para com `[ERRO]` antes da espera do RCON, sem despausar; PR #128), sem infra e sem janela | `jogavel-2026-11-04-2` (validado pela partida 108; ancestral do `e80611e`, que só soma docs e `tools/`, PRs #129 a #131) |
| `candidato-29` | `29087da` | B1.17 (card 29,992: a fonte do bind do BotAimImprover passa a `./docker/plugins/_empty`; PR #139), fora do plano por decisão do Victor de 08/11. A tag é o objeto `ee26675` sobre o commit `29087da`. A `jogavel-2026-11-08` antes dele não teve candidato: o B1.16 só mexeu no volume (VPK) e na válvula | `jogavel-2026-11-09` (validado pela partida 113 e pela MD3 114; mesmo commit) |

## Compose e config-hash

O sha256 do compose é o do arquivo no checkout principal, com CRLF (`core.autocrlf=true`); o
do blob LF do git fica em [Hashes completos](#hashes-completos). O config-hash é o
`docker compose config --hash cs2-server`, lido pelo servidor. Ele depende do compose **e** do
`.env`, por isso não se recalcula offline.

| Tag | Compose (checkout) | config-hash | Fonte do config-hash |
|---|---|---|---|
| `jogavel-2026-09-26` | `47cb7e8f…` | não registrado: a primeira janela que o leu foi a do B1.3r. Viria do `--hash` com o checkout no `efcaa42` e o `.env` daquele dia | — |
| `jogavel-2026-09-27` | `c5b35137…` | `55765314…` | `b1.3r/g7-1441/veredito.txt` |
| `jogavel-2026-09-27-2` | `c2b497a6…` | `a6870589…` | `b1.4b/config-hash.txt` |
| `jogavel-2026-09-27-3` | `c3aa595f…` | `dc0a3295…` | `b1.5/config-hash.txt` |
| `jogavel-2026-09-27-4` | `34a490fa…` | `ecbbf707…` | `b1.6/config-hash.txt` |
| `jogavel-2026-09-27-5` | `6d573f35…` | `a6bbdcef…` | `b1.8/config-hash.txt` |
| `jogavel-2026-09-28` | `86d9abd6…` | `3970b702…` | `b1.9/config-hash.txt`; igual na coleta G7 e nas janelas VPK de 28/09 |
| `jogavel-2026-10-01` | `86d9abd6…` (conferido com `sha256sum` no checkout principal em 01/10) | `3970b702…` | `2026-10-01/g7-2000922-partida/config-hash.txt`; igual ao do label do container (`config-hash-janela.txt`) e ao da janela de 30/09 |
| **Janela 0** (`candidato-8`, `214b25b`; não é tag) | `46b77848…` (era `86d9abd6…` antes do B0.8) | `3970b702…`, inalterado: o hash do serviço não cobre o bloco `volumes:` de topo, que é o que o B0.8 mudou | `2026-10-02/janela0/depois-medicoes.txt` e `final-medicoes.txt` (label do container = `--hash`) |
| `jogavel-2026-10-03` | `46b77848…` (o do `candidato-8`; conferido com `sha256sum` no checkout principal em 03/10) | `3970b702…` | `2026-10-03/coleta-g7-b0.8-0015/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao da Janela 0 |
| `jogavel-2026-10-12` | `46b77848…` (o do `candidato-8`; conferido com `sha256sum` no checkout principal em 12/10, com o HEAD no `abd19aa`) | `3970b702…` | `2026-10-12/coleta-g7-candidato-9/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-13` | `46b77848…` (o do `candidato-8`; conferido com `sha256sum` no checkout principal em 13/10, no K1.12) | `3970b702…` | `2026-10-13/coleta-g7-p1.1/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-14` | `46b77848…` (o do `candidato-8`, pelo blob: `git show b8b492f:docker-compose.yml \| sha256sum` dá o blob LF `2a889474…`, o mesmo; o CRLF não foi relido no checkout principal) | `3970b702…` | `2026-10-14/coleta-g7-p1.1a/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-14-2` | `46b77848…` (idem, pelo blob LF `2a889474…` do `eb4cb0e`; o B1.9b não mexeu no compose) | `3970b702…` | `2026-10-14/coleta-g7-b1.9b/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 da janela do B1.9b |
| `jogavel-2026-10-14-3` | `cc0e967e…` (o do `candidato-13`, em que a máscara do BotAI virou bind; conferido com `sha256sum` no checkout principal em 14/10, no B1.7d, com a `main` no `2619d70`) | `837cbcbc…`, novo: o compose mudou | `2026-10-14/coleta-g7-b1.7/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 da janela do B1.7 |
| `jogavel-2026-10-16` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show 9c9b648:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal) | `837cbcbc…` | `2026-10-15/coleta-g7-p1.1b/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-17` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show 1b5b5d3:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal). O `candidato-15` só acrescentou o `docker-compose.vanilla.yml` (blob LF `58c98479…`), que só entra com a válvula on | `837cbcbc…`, com a válvula off (= H_off) | `2026-10-17/coleta-g7-p1.2/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 do off (janela de 17/10) |
| `jogavel-2026-10-19` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show 54ef88d:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal). O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, fora com a válvula off | `837cbcbc…`, com a válvula off (= H_off) | `2026-10-19/coleta-g7-p1.1c/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-19-2` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show 0164cc3:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal). O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, fora com a válvula off | `837cbcbc…`, com a válvula off (= H_off) | `2026-10-19/coleta-g7-p1.1d/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-19-3` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show a32ef5e:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal). O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, fora com a válvula off | `837cbcbc…`, com a válvula off (= H_off) | `2026-10-19/coleta-g7-p1.3-p1.4/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-20` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show c228d93:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal). O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, fora com a válvula off | `837cbcbc…`, com a válvula off (= H_off) | `2026-10-20/coleta-g7-p1.5-p1.6/`: o config-hash do container igual ao do compose (Históricos dos cards 84 e 85) |
| `jogavel-2026-10-21` | `cc0e967e…` (o do `candidato-13`, pelo blob: `git show 69c45b1:docker-compose.yml \| sha256sum` dá o blob LF `807b940d…`, o mesmo; o CRLF não foi relido no checkout principal). O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, fora com a válvula off | `837cbcbc…`, com a válvula off (= H_off) | `2026-10-21/coleta-g7-p1.7-p1.8-v2/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-10-25` | não lido no checkout principal; pelo blob: `git show cc17bb4:docker-compose.yml \| sha256sum` dá o blob LF `eb787eee…`, novo, porque o `candidato-24` mudou o `CSSHARP_FIXED_VERSION` (e o comentário acima dele). O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, **dentro**, com a válvula on | `0cf4006b…`, novo, com a válvula on: o `environment` do serviço mudou | `2026-10-25/b1.3s-1501/g7-1541/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 da janela de 25/10 |
| `jogavel-2026-10-26` | não lido no checkout principal; pelo blob: `git show 09e54bd:docker-compose.yml \| sha256sum` dá o blob LF `9c7df35f…`, novo: o P1.9 troca o bind de arquivo do `match_config` pela pasta `./docker/runtime`, e o P1.11 publica a 27015/tcp em `127.0.0.1`. O `docker-compose.vanilla.yml` segue no blob LF `58c98479…`, **dentro**, com a válvula on | `1c412f6a…`, novo, com a válvula on (sem o override vanilla, o compose dá `d9c6ee27…`, sem uso) | `2026-10-26/p1.9-p1.11/g7-1327/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` dos G6 das janelas de 09:52 e 11:01 |
| `jogavel-2026-10-26-2` | não lido no checkout principal; pelo blob: `git show 57e357b:docker-compose.yml \| sha256sum` dá o blob LF `5de05481…`, novo: o B1.13 soma o bind do NadeSystem do fork. O `docker-compose.vanilla.yml` mudou só em comentário (blob LF `be0c3cf4…`) e fica **fora**, com a válvula off | `19d8fdd8…`, novo, com a válvula off | `2026-10-26/b1.13/g7-1441/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 da janela de 13:48 |
| `jogavel-2026-11-04` | não lido no checkout principal; pelo blob: `git cat-file blob f16121f:docker-compose.yml \| sha256sum` dá o blob LF `cb964ace…`, novo, mas só em comentário (K1.9). O `docker-compose.vanilla.yml` segue no blob LF `be0c3cf4…` e fica **fora**, com a válvula off | `19d8fdd8…`, o mesmo da `jogavel-2026-10-26-2`: o K1.9 não muda o `docker compose config`, e o valor foi o mesmo antes e depois do ff | `2026-11-04/partida-k19-b115/coleta/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 e do fechamento da janela de 17:41 (`2026-11-04/b1.15/fechamento-config-hash.txt`) |
| `jogavel-2026-11-04-2` | não lido no checkout principal; pelo blob: `git cat-file blob e80611e:docker-compose.yml \| sha256sum` dá `cb964ace…`, o mesmo da `jogavel-2026-11-04` (`git diff --stat f16121f e80611e -- docker-compose.yml docker-compose.vanilla.yml` vazio). O `docker-compose.vanilla.yml` segue `be0c3cf4…` e fica **fora** | `19d8fdd8…`, o mesmo da `jogavel-2026-11-04` | `2026-11-04/partida-p115/coleta/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta |
| `jogavel-2026-11-08` | não lido no checkout principal; pelo blob: `git cat-file blob dff4222:docker-compose.yml \| sha256sum` dá `cb964ace…`, o mesmo da `jogavel-2026-11-04-2` (o delta `e80611e..dff4222` não toca o compose). O `docker-compose.vanilla.yml` segue `be0c3cf4…` e fica **fora**, com a válvula off desde 06/11 | `19d8fdd8…`, o mesmo da `jogavel-2026-11-04-2` (na janela de 05/11, com a válvula on, `e863d2f6…`, sem partida) | `2026-11-08/partida-b116/coleta/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 e do fechamento da janela de 06/11 |
| `jogavel-2026-11-09` | não lido no checkout principal; pelo blob: `git cat-file blob 29087da:docker-compose.yml \| sha256sum` dá o blob LF `cb2516a9…`, novo: o B1.17 troca a fonte do bind do BotAimImprover por `./docker/plugins/_empty` (e o comentário acima dela). O `docker-compose.vanilla.yml` segue `be0c3cf4…` e fica **fora** | `6427c169…`, novo, com a válvula off: o `docker compose config` muda nesse mount | `2026-11-09/partida-b117/coleta/config-hash.txt`; igual ao `config-hash-janela.txt` da mesma coleta e ao `docker compose config --hash` do G6 e do fechamento da janela de 08/11 |

Com a válvula on (janela de 16/10, G6 do on), o config-hash do `candidato-15` foi `0f3ff2b2…`
(`2026-10-16/p1.2/on-config-hash-janela.txt`, igual ao `docker compose config --hash` com os dois `-f`).
Nenhuma partida jogou nele. O mesmo `0f3ff2b2…` voltou no G6 da janela de 23/10, quando o servidor
ligou a válvula com o checkout no `ba17644`; ali também nenhuma partida completa rodou. Na janela de
22/10, com a válvula off e o checkout no `ba17644`, o config-hash foi o H_off, `837cbcbc…`.

O `candidato-2` teve config-hash `c8a2a535…` (`b1.4/config-hash.txt`), e o compose dele foi
`36ff2fe2…`.

## Máscaras por época

Máscara é o bind de `./docker/plugins/_empty` sobre a pasta do plugin, em
`/home/steam/cs2-dedicated/game/csgo/addons/`. Para conferir as linhas:
`git grep -n _empty <commit> -- docker-compose.yml`.

### Época 0: `efcaa42` (`jogavel-2026-09-26`)

| Linha | Alvo | Tipo |
|---|---|---|
| 101 | `counterstrikesharp/plugins/RayTraceImpl` | CSSharp |
| 108 | `RayTrace` | Metamod nativo |
| 141 | `counterstrikesharp/plugins/BotAI` | CSSharp |
| 142 | `counterstrikesharp/plugins/BotAimImprover` | CSSharp |
| 143 | `counterstrikesharp/plugins/BotBuy` | CSSharp |
| 144 | `counterstrikesharp/plugins/BotHiderImpl` | CSSharp |
| 145 | `counterstrikesharp/plugins/BotRandomizer` | CSSharp |
| 146 | `counterstrikesharp/plugins/BotState` | CSSharp |
| 149 | `BotHider` | Metamod nativo |
| 155 | `counterstrikesharp/plugins/NadeSystem` | CSSharp |

São exatamente as linhas do critério 3 do B0.3 (101, 108, 141-146, 149 e 155): o `git grep`
no `efcaa42` devolve essas 10 linhas no compose e nenhuma outra `_empty` em arquivo montado.

### Época da `jogavel-2026-10-01` (compose igual ao da `jogavel-2026-09-28`)

| Alvo | Estado | Linha |
|---|---|---|
| RayTraceImpl | mascarado | 100 |
| RayTrace | mascarado | 107 |
| BotAI | mascarado (B1.7 pulado) | 142 |
| BotHiderImpl | mascarado | 151 |
| BotHider | mascarado | 162 |
| BotBuy | religado: máscara comentada | 150 |
| BotState | religado: máscara comentada | 159 |
| NadeSystem | religado: máscara comentada | 171 |
| BotAimImprover | religado: a máscara deu lugar ao bind de `./docker/plugins/BotAimImprover` | 147 |
| BotRandomizer | religado: a máscara deu lugar ao bind de `./docker/plugins/BotRandomizer` | 155 |

No `candidato-8` (`214b25b`, B0.8), e portanto na `jogavel-2026-10-03` e na `jogavel-2026-10-12` (compose sem diff até o `abd19aa`), as máscaras são as mesmas, e as linhas descem 2 por causa do
comentário novo no mount do `cs2-data`: 102, 109, 144, 153 e 164 (mascarados), 152, 161 e 173
(máscaras comentadas), 149 e 157 (binds). Conferido em 02/10 com
`git grep -n -E '_empty|plugins/(BotAimImprover|BotRandomizer)' 214b25b -- docker-compose.yml`.

No `candidato-13` (`2619d70`, B1.7), e portanto na `jogavel-2026-10-14-3`, a máscara do BotAI
(linha 144) deu lugar ao bind de `./docker/plugins/BotAI` (linha 147, com três linhas de
comentário acima), e as linhas abaixo dela descem 3: 102 e 109, 156 e 167 (mascarados); 155,
164 e 176 (máscaras comentadas); 152 e 160 (binds de BotAimImprover e BotRandomizer). Conferido
em 14/10 (B1.7d) com
`git grep -n -E '_empty|plugins/(BotAimImprover|BotRandomizer|BotAI)' 2619d70 -- docker-compose.yml`.

Na `jogavel-2026-11-04` (`f16121f`) as máscaras e os binds são os mesmos da
`jogavel-2026-10-26-2` (`57e357b`, que somou o bind do NadeSystem), mas a poda de comentários
do K1.9 sobe as linhas: 60 e 63, 79 e 90 (mascarados: RayTraceImpl, RayTrace, BotHiderImpl e
BotHider); 78 e 87 (máscaras comentadas de BotBuy e BotState); 70, 75, 83 e 94 (binds de BotAI,
BotAimImprover, BotRandomizer e NadeSystem). No `57e357b` eram 109, 116, 163 e 174; 162 e 171;
154, 159, 167 e 187. Conferido em 04/11 (P1.20) com
`git grep -n -E '_empty|plugins/(BotAimImprover|BotRandomizer|BotAI|NadeSystem)' <commit> -- docker-compose.yml`.
Na `jogavel-2026-11-04-2` (`e80611e`) também, nas mesmas linhas: o compose não mudou desde o `f16121f`. Na `jogavel-2026-11-08` (`dff4222`) também, pelo mesmo motivo. Na `jogavel-2026-11-09` (`29087da`) o BotAimImprover volta a ser máscara, na linha 78 (bind `_empty`, com o comentário do rollback na 77), e as linhas abaixo dele descem 3: 60 e 63, 82 e 93 (mascarados: RayTraceImpl, RayTrace, BotHiderImpl e BotHider); 81 e 90 (máscaras comentadas de BotBuy e BotState); 70, 86 e 97 (binds de BotAI, BotRandomizer e NadeSystem). Conferido em 09/11 (B1.18) com o mesmo `git grep` sobre o `29087da`.

Nas tags do meio, a máscara sai uma por vez, na ordem da tabela de tags: BotAimImprover
(`-27-2`), BotState (`-27-3`), BotBuy (`-27-4`), NadeSystem (`-27-5`) e BotRandomizer (`-28`).
BotVision e BotController não têm máscara e não estão no volume.

## sha256 dentro do container

São os arquivos montados que o protocolo manda conferir, lidos com `docker exec sha256sum`
pelo servidor. Em toda coleta, o valor dentro do container foi igual ao do checkout.

| Tag | Coleta | cfg | `pre.sh` | `match_config` | DLL | `.deps.json` |
|---|---|---|---|---|---|---|
| `jogavel-2026-09-26` | não registrado: antes do B1.3r ninguém coletou, e o container de então foi recriado em 27/09 08:23 | — | — | — | — | — |
| `jogavel-2026-09-27` | G7, `b1.3r/g7-1441/sha-montados.txt` | `aebb5df5…` | `233e5aa0…` | `2f5fb06d…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-09-27-2` | G7, `b1.4b/g7-1835/` | `aebb5df5…` | `233e5aa0…` | `a6f69606…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-09-27-3` | G7, `b1.5/g7-1951/` | `aebb5df5…` | `233e5aa0…` | `f8eeeaf7…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-09-27-4` | G7, `b1.6/g7-2113/` | `aebb5df5…` | `233e5aa0…` | `a6f69606…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-09-27-5` | G7, `b1.8/g7-2221/` | `aebb5df5…` | `233e5aa0…` | `a6f69606…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-09-28` | G7, `2026-09-28/g7-candidato-7/` | `aebb5df5…` | `233e5aa0…` | `a6f69606…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-01` | G7, `2026-10-01/g7-2000922-partida/` | `aebb5df5…` | `233e5aa0…` | `0816da11…` | `697760a7…` | `137a42f2…` |
| **Janela 0** (`candidato-8`) | B0.9, 02/10, janela 00:12–00:39: `2026-10-02/janela0/` (`sha-montados-boot1.txt` no boot do B0.8, `fechamento-sha-container.txt` no fechamento) | `aebb5df5…` | `233e5aa0…` | `2000bf4e…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-03` | G7, `2026-10-03/coleta-g7-b0.8-0015/` | `aebb5df5…` | `233e5aa0…` | `2f5fb06d…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-12` | G7, `2026-10-12/coleta-g7-candidato-9/` | `aebb5df5…` | `233e5aa0…` | `4eccec34…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-13` | G7, `2026-10-13/coleta-g7-p1.1/` | `aebb5df5…` | `233e5aa0…` | `a1e4ca22…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-14` | G7, `2026-10-14/coleta-g7-p1.1a/` | `aebb5df5…` | `233e5aa0…` | `b33fb17c…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-14-2` | G7, `2026-10-14/coleta-g7-b1.9b/` | `aebb5df5…` | `233e5aa0…` | `2f5fb06d…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-14-3` | G7, `2026-10-14/coleta-g7-b1.7/` | `aebb5df5…` | `233e5aa0…` | `52bf794a…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-16` | G7, `2026-10-15/coleta-g7-p1.1b/` | `aebb5df5…` | `233e5aa0…` | `d29f6b1a…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-17` | G7, `2026-10-17/coleta-g7-p1.2/` | `aebb5df5…` | `233e5aa0…` | `f8eeeaf7…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-19` | G7, `2026-10-19/coleta-g7-p1.1c/` | `aebb5df5…` | `233e5aa0…` | `0816da11…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-19-2` | G7, `2026-10-19/coleta-g7-p1.1d/` | `aebb5df5…` | `233e5aa0…` | `b33fb17c…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-19-3` | G7, `2026-10-19/coleta-g7-p1.3-p1.4/` | `aebb5df5…` | `233e5aa0…` | `d29f6b1a…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-20` | G7, `2026-10-20/coleta-g7-p1.5-p1.6/` | `aebb5df5…` | `233e5aa0…` | ver a nota abaixo | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-21` | G7, `2026-10-21/coleta-g7-p1.7-p1.8-v2/` | `aebb5df5…` | `233e5aa0…` | `2f5fb06d…` | `697760a7…` | `137a42f2…` |
| `jogavel-2026-10-25` | G7, `2026-10-25/b1.3s-1501/g7-1541/` | `aebb5df5…` | `233e5aa0…` | `f8eeeaf7…` | **`75d0d6df…`** (0.4.1) | `137a42f2…` |
| `jogavel-2026-10-26` | G7, `2026-10-26/p1.9-p1.11/g7-1327/` | `aebb5df5…` | `233e5aa0…` | `f34ea347…` (**`docker/runtime/`**) | `75d0d6df…` (0.4.1) | `137a42f2…` |
| `jogavel-2026-10-26-2` | G7, `2026-10-26/b1.13/g7-1441/` | `aebb5df5…` | `233e5aa0…` | `d2dd3f3f…` (`docker/runtime/`) | `75d0d6df…` (0.4.1) | `137a42f2…` |
| `jogavel-2026-11-04` | G7, `2026-11-04/partida-k19-b115/coleta/` | **`f3b0009c…`** (K1.9, só comentário) | `233e5aa0…` | `f399ef09…` (`docker/runtime/`) | `75d0d6df…` (0.4.1) | `137a42f2…` |
| `jogavel-2026-11-04-2` | G7, `2026-11-04/partida-p115/coleta/` | `f3b0009c…` | `233e5aa0…` | `c29e4d45…` (`docker/runtime/`) | `75d0d6df…` (0.4.1) | `137a42f2…` |
| `jogavel-2026-11-08` | G7, `2026-11-08/partida-b116/coleta/` | `f3b0009c…` | `233e5aa0…` | `0c9ce373…` (`docker/runtime/`) | `75d0d6df…` (0.4.1) | `137a42f2…` |
| `jogavel-2026-11-09` | G7, `2026-11-09/partida-b117/coleta/` | `f3b0009c…` | `233e5aa0…` | `358ad395…` (`docker/runtime/`) | `75d0d6df…` (0.4.1) | `137a42f2…` |

- O `match_config.spike.json` é estado de runtime: o `start_match` o reescreve a cada partida, e
  o sha muda com ela. Ele não identifica a combinação e fica aqui só como registro.
- Os binds de plugin de bot também foram conferidos nas coletas: BotAimImprover (3 arquivos,
  igual ao manifesto do [B1.4b](b1.4b-botaimimprover-upstream.md)) e BotRandomizer (5 arquivos,
  igual ao manifesto do [B1.9](b1.9-botrandomizer-upstream.md)).
- Na coleta da partida 36, os 19 caminhos do `sha-montados.txt` bateram com o checkout
  (`sha-referencia.txt`), inclusive os binds de BotAimImprover (3) e BotRandomizer (5). A pasta
  `2026-10-01/g7-vpk-low-2000922/`, da mesma tarde (17:58), não vale como evidência: o container
  estava parado porque o PC suspendeu em 30/09 23:56, e o `docker exec` não leu nada (`NOTA.txt`
  dela).
- Na Janela 0, os 14 caminhos (os 5 da tabela, o `.pdb` da captura `ca994b0c…` e os binds de
  BotAimImprover (3) e BotRandomizer (5)) bateram com o checkout no boot do B0.8
  (`sha-comparacao-boot1.txt`) e de novo no fechamento (`fechamento-sha-checkout.txt` ×
  `fechamento-sha-container.txt`). O `match_config` `2000bf4e…` é o que já estava no checkout:
  igual antes e depois do B0.8 e restaurado pelo `voltar` no ensaio.
- Na coleta da partida de 03/10 (matchid 74), os 19 caminhos de `sha-montados.txt` bateram com
  os 15 arquivos do checkout (`sha-referencia.txt`; as 5 máscaras são o mesmo
  `_empty/.gitkeep`), inclusive o `.pdb` da captura e os binds de BotAimImprover (3) e
  BotRandomizer (5). O `match_config` `2f5fb06d…` é o mesmo da partida 26.
- Na coleta de 12/10 (`candidato-9`), os 19 caminhos de `sha-montados.txt` bateram com os 15
  arquivos do checkout (`sha-referencia.txt`), do mesmo jeito: `.pdb` da captura, BotAimImprover
  (3), BotRandomizer (5) e as 5 máscaras. O `match_config` `4eccec34…` é o que o checkout tinha
  na hora da coleta, depois da partida 79.
- Na coleta de 13/10 (`candidato-10`), do mesmo jeito: os 19 caminhos bateram com os 15 arquivos
  do checkout. O `match_config` `a1e4ca22…` é o que o checkout tinha depois da partida 80. Os 5
  arquivos do BotRandomizer seguem iguais ao manifesto do B1.9, com as armas sem skin na 2000930.
- Nas duas coletas de 14/10 antes da janela do B1.7, os 19 caminhos de `sha-montados.txt`
  bateram com os 15 arquivos do checkout, do mesmo jeito. Na do `candidato-11` (partida 81), o
  BotRandomizer ainda é o do B1.9 (DLL `5be52c02…`) e o `match_config` é `b33fb17c…`; na do
  `candidato-12` (partida 82), o BotRandomizer é o do B1.9b (DLL `cfe7efc0…`, `.pdb`
  `539d6296…`; os outros 3 arquivos são os do B1.9) e o `match_config` é `2f5fb06d…`.
- Na coleta de 14/10 (`candidato-13`), os 21 caminhos de `sha-montados.txt` bateram com os 18
  arquivos do checkout (`sha-referencia.txt`): os 5 da tabela, o `.pdb` da captura,
  BotAimImprover (3), BotRandomizer (5, os do B1.9b: DLL `cfe7efc0…`), **BotAI (3, iguais ao
  manifesto do [B1.7b](b1.7b-botai-fork-assinatura.md))** e as 4 máscaras (o mesmo
  `_empty/.gitkeep`). O `match_config` `52bf794a…` é o que o checkout tinha depois da partida 83.
- Na coleta de 15/10 (`candidato-14`), do mesmo jeito: os 21 caminhos de `sha-montados.txt`
  bateram com os 18 arquivos do checkout (os mesmos 18 sha256 dos dois lados). O `match_config`
  `d29f6b1a…` é o que o checkout tinha depois da partida 84.
- Na coleta de 17/10 (`candidato-15`, válvula off), do mesmo jeito: os 21 caminhos de
  `sha-montados.txt` bateram com os 18 arquivos do checkout (os mesmos 18 sha256 dos dois lados).
  O `match_config` `f8eeeaf7…` é o que o checkout tinha depois da partida 85, o mesmo da partida 28.
- Na coleta de 19/10 (`candidato-16`), do mesmo jeito: os 21 caminhos de `sha-montados.txt`
  bateram com os 18 arquivos do checkout (os mesmos 18 sha256 dos dois lados). O `match_config`
  `0816da11…` é o que o checkout tinha depois da partida 88, o mesmo da partida 36.
- Na coleta de 19/10 do `candidato-17`, do mesmo jeito: os 21 caminhos de `sha-montados.txt`
  bateram com os 18 arquivos do checkout (os mesmos 18 sha256 dos dois lados). O `match_config`
  `b33fb17c…` é o que o checkout tinha depois da partida 89, o mesmo da coleta de 14/10 do
  `candidato-11`.
- Na coleta de 19/10 do `candidato-18`, do mesmo jeito (os mesmos 18 sha256 dos dois lados). O
  `match_config` `d29f6b1a…` é o que o checkout tinha depois da partida 91, o mesmo da coleta
  de 15/10, depois da partida 84.
- Na coleta de 20/10 do `candidato-20`, os 21 caminhos montados bateram com o checkout, e o QA
  conferiu os mesmos 18 sha256. O cfg, o `pre.sh`, a DLL e o `.deps.json` não mudaram desde a
  `jogavel-2026-10-19-3` (a DLL também está na mensagem da tag). O sha do `match_config` depois
  da MD3 não foi transcrito neste registro (K1.20, feito sem abrir a coleta): está no
  `sha-montados.txt` dela.
- Na coleta de 21/10 do `candidato-22`, os 21 caminhos de `sha-montados.txt` bateram com o
  checkout, e o QA conferiu os mesmos 18 sha256. O `match_config` `2f5fb06d…` é o que o checkout
  tinha depois da partida 96, o mesmo da partida 26.
- Na coleta de 25/10 do par `candidato-23` + `candidato-24` (válvula on), os 16 caminhos de
  `sha-montados.txt` bateram com os 7 arquivos do checkout (`sha-referencia.txt`): os 5 da
  tabela, o `.pdb` da 0.4.1 (`0697c375…`) e as 9 máscaras (o mesmo `_empty/.gitkeep`; com a
  válvula on, os 6 plugins de bot também viram máscara). O `match_config` `f8eeeaf7…` é o que o
  checkout tinha depois da partida 97, o mesmo da partida 28.
- Desde o P1.9 (`jogavel-2026-10-26`), o `match_config` montado é o
  `docker/runtime/match_config.spike.json`, dentro da pasta montada em `game/csgo/runtime`; o
  `coletar` e o `evidencia_partida.py` o conferem pelo P1.9b. Na coleta de 26/10 do
  `candidato-25` (válvula on), os 16 caminhos bateram com os 7 arquivos do checkout, como em
  25/10, com o runtime `f34ea347…` (o da partida 100) no lugar do arquivo antigo.
- Na coleta de 26/10 do `candidato-26` (válvula off), os 72 caminhos de `sha-montados.txt`
  bateram com os 69 arquivos do checkout: os 5 da tabela, o `.pdb` da captura, BotAI (3),
  BotAimImprover (3), BotRandomizer (5), as 51 do NadeSystem (= o `MANIFESTO.sha256` da janela;
  DLL `5ef13e7c…`) e o `_empty/.gitkeep` das máscaras restantes. O runtime `d2dd3f3f…` é o da
  partida 101.
- Na coleta de 04/11 do `candidato-27` (válvula off), do mesmo jeito: os 72 caminhos de
  `sha-montados.txt` bateram com os 69 arquivos do checkout, com os mesmos sha256 dos plugins de
  bot de 26/10 e o cfg novo do K1.9 (`f3b0009c…`). O runtime `f399ef09…` é o da partida 107. No
  G6 e no fechamento da janela de 17:41, o registro diz 68/68 mais o `_empty/.gitkeep`.
- Na coleta de 04/11 21:11 do `candidato-28`, no mesmo container: os mesmos 72 caminhos contra os 69 arquivos do checkout, sem divergência. O runtime `c29e4d45…` é o da partida 108.

### Como preencher na Janela 0 (B0.9)

**Cumprido em 02/10** (janela 00:12–00:39, registro `logs/janelas/2026-10-02.md`, coleta
`2026-10-02/janela0/`): os passos 1 a 4 saíram como abaixo, com 14 caminhos em vez de 5, e o
passo 5 é a linha **Janela 0** da tabela. Build 2000922; `meta list` com CSSharp v1.0.375; 8
plugins LOADED; imagem `sha256:1056e003…`; config-hash `3970b702…`. O inventário do volume
ficou em [inventário do volume](inventario-volume.md). O roteiro fica como registro do que se
fez:

Quem faz é o papel servidor, na janela aberta pelo Victor, com o container de pé e sem partida:

1. Preflight 4 (`C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py`).
2. `docker exec` com `sha256sum` dos cinco caminhos do protocolo: `cfg/gamemode_competitive_server.cfg`,
   `pre.sh`, `match_config.spike.json` e os dois arquivos de
   `addons/counterstrikesharp/plugins/Cs2TrackerEvents/`.
3. O mesmo `sha256sum` no checkout principal. Os cinco pares têm de bater; se algum divergir,
   isso é achado da janela, não valor para esta nota.
4. Anote também a build (RCON `version`), `meta list`, `css_plugins list`, o digest da imagem e
   o `docker compose config --hash cs2-server`.
5. No PR da B0.9, troque a linha **Janela 0** pelos valores, com a data e a pasta da coleta.

## Manifesto do plugin de captura

A pasta `docker/plugins/Cs2TrackerEvents/` é ignorada pelo git e só existe no checkout principal.
A cópia dela está em
`C:/Users/Victor/cs2-tracker-backups/plugins/Cs2TrackerEvents/697760a7566ee54a08b95bf804d6c21ab709b8e2762d83e5f8f846787270e115/`,
feita em 28/09 23:01 (card B0.3), com o `MANIFEST.txt` ao lado:

| Arquivo | Bytes | Data na origem | sha256 |
|---|---|---|---|
| `Cs2TrackerEvents.dll` | 49152 | 23/09 19:10 | `697760a7…` |
| `Cs2TrackerEvents.deps.json` | 33896 | 13/09 18:04 | `137a42f2…` |
| `Cs2TrackerEvents.pdb` | 16700 | 23/09 19:10 | `ca994b0c…` |

A cópia foi conferida contra a origem arquivo a arquivo. O nome da pasta é o sha256 da DLL: um
build novo ganha uma pasta nova ao lado, e a velha não se apaga.

A 0.4.1 (P1.10) é o build de 22/10 19:55, feito pelo `docker/build-events-plugin.sh` com o
container parado, e está na pasta
`C:/Users/Victor/cs2-tracker-backups/plugins/Cs2TrackerEvents/75d0d6dff63825ae7f1ef74678051efe9997bc7e03440628e15d4fdcf046988b/`,
com o `MANIFEST.txt` ao lado; a da 0.4.0 ficou intacta, para o rollback:

| Arquivo | Bytes | sha256 |
|---|---|---|
| `Cs2TrackerEvents.dll` | 51712 | `75d0d6df…` |
| `Cs2TrackerEvents.deps.json` | 33896 | `137a42f2…` (o mesmo da 0.4.0) |
| `Cs2TrackerEvents.pdb` | 17428 | `0697c375…` | Para restaurar, o servidor
para o container, na janela, e copia os três arquivos de volta
([trilha](trilha-de-bots.md#regras): DLL não se troca com o servidor vivo).

## Como registrar uma tag nova

Na criação de uma `jogavel-*`, o tech-manager acrescenta uma linha em cada tabela a partir do
registro da janela e da coleta G7: commit, build, Metamod/CSSharp/MatchZy, plugins, VPK, sha do
compose (`sha256sum docker-compose.yml` no checkout principal), config-hash, sha dos montados
dentro do container e a partida. O que a coleta não trouxe entra como **não registrado**.

A tag em si sai do `tools/jogavel.py marcar` (com o registro em `logs/jogavel/tags.md`, fora do
git). Este registro é à mão, num PR de docs com card próprio (a `jogavel-2026-10-01` foi o
B0.3b, a `jogavel-2026-10-03`, o B0.3c, a `jogavel-2026-10-12`, o T1.9, a `jogavel-2026-10-13`,
o K1.12, a `jogavel-2026-10-14-3`, o B1.7d, a `jogavel-2026-10-14` e a `jogavel-2026-10-14-2`,
o K1.13, a `jogavel-2026-10-16`, o K1.14, a `jogavel-2026-10-17`, o K1.15, a
`jogavel-2026-10-19`, o K1.16, a `jogavel-2026-10-19-2`, o K1.17, a `jogavel-2026-10-19-3`, o K1.18,
a `jogavel-2026-10-20`, o K1.20, a `jogavel-2026-10-21`, o K1.21, a `jogavel-2026-10-25`, o
K1.22, a `jogavel-2026-10-26` e a `jogavel-2026-10-26-2`, o K1.23, a `jogavel-2026-11-04`, o
P1.20, a `jogavel-2026-11-04-2`, o P1.21, e a `jogavel-2026-11-08` e a `jogavel-2026-11-09`, o B1.18). Quando a partida foi num dia e a marcação sai no seguinte, o
`marcar jogavel` leva `--data AAAA-MM-DD` com o dia da partida (P1.21).

## Hashes completos

Compose por tag (checkout CRLF · blob LF do git):

```
jogavel-2026-09-26    47cb7e8f01f61a4cf6fe035a7496e1db21c9b066c4185a9fc7c4eb42d7b633e5 · 58e116e42cf09a58f314bca072dcc92bff793a9f3b43e1516c05ff960b44b2cd
jogavel-2026-09-27    c5b3513752941b6e1accef104cb04c6d9bddf12af020fafee2a76dc1f1c39d6d · 9c262842a3c9ec8a98f7738cb3d1c856bd6a42613df85382e325e9286917e13e
jogavel-2026-09-27-2  c2b497a638473f9f25eaecb2154b573b95f447f040ecaf33656ecf9045c80d57 · d10130d6ce74e331e85905f1783dac92de86ae1e74a07753212263b0cb0de20a
jogavel-2026-09-27-3  c3aa595f1db789ed7a8494478b42d9501e33faa8b9ebf5452f88b203fd2a734d · b0ead173b9b5cf515137c873cca32ca559357982bfb6d2cc54066312fe0cf718
jogavel-2026-09-27-4  34a490fab64e6995672211ee1084cb404448d863ad6bd2b35834f998361a1d35 · d77e37a1148fcfa5fac2a028d00c931a205e1f16891b1c32026b008cbc2a2e5b
jogavel-2026-09-27-5  6d573f3534cc8954d9568f15b25a3a2d0e67ff2f3d05254f72a96f47007092e1 · 0dde3c10725eb89381d527c1b3e2c4a47a48d16dbef3b0c81a32e4a36ca6c125
jogavel-2026-09-28    86d9abd66ce0f6e939a0db41a0b0e862d2c56e1df0b3a509b635ca1fcf2ec19b · 7f49ec6e562f7f0fb5e54cd47bedec77e247b8c620870f598a09313fd905c69c
jogavel-2026-10-01    86d9abd66ce0f6e939a0db41a0b0e862d2c56e1df0b3a509b635ca1fcf2ec19b · 7f49ec6e562f7f0fb5e54cd47bedec77e247b8c620870f598a09313fd905c69c
jogavel-2026-10-03    46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5
jogavel-2026-10-12    46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5
jogavel-2026-10-13    46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5
jogavel-2026-10-14    46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5  (CRLF pelo blob)
jogavel-2026-10-14-2  46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5  (CRLF pelo blob)
jogavel-2026-10-14-3  cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7
jogavel-2026-10-16    cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-17    cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-19    cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-19-2  cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-19-3  cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-20    cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-21    cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7  (CRLF pelo blob)
jogavel-2026-10-25    não lido · eb787eeebbe1bb09ea555c08f0bf14c8a95070e31dbb9b0ea754bd7ce54ac84c
jogavel-2026-10-26    não lido · 9c7df35f75413410f3b5ab24060ef46d9059955307639207d0947b349f5dad5b
jogavel-2026-10-26-2  não lido · 5de05481bb4a556e2c1295eb12bcafbe28c6eb00ede4677e27832dafe8564fb7
jogavel-2026-11-04    não lido · cb964ace85e5b085c97506af8bb34b27c4b0b2a6623a1393acc15accee81d7fc
jogavel-2026-11-04-2  não lido · cb964ace85e5b085c97506af8bb34b27c4b0b2a6623a1393acc15accee81d7fc
jogavel-2026-11-08    não lido · cb964ace85e5b085c97506af8bb34b27c4b0b2a6623a1393acc15accee81d7fc
jogavel-2026-11-09    não lido · cb2516a96143abff884736672cb20c8034bfbe90dd1b1201dec9dcf66211cec1
candidato-2           36ff2fe29210820d59c8b82cab7675c9f10be47bccaa6392ab78d4420cef85a8 · 8cb6674414bc5f5e4cf0c01b363736de4168b0a0a30c6be26a2f000e89fc5f13
candidato-8           46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5
candidato-13          cc0e967e03a54d258258d2ba2268e352ceafab2756fd0dfba2a5371d959d87b4 · 807b940db01811b62999fd703b4b5b8216d05a0d5e17910e7e4a0f36282f14f7
```

O CRLF do `candidato-8` é o da Janela 0 (`depois-medicoes.txt`); o blob LF saiu de
`git show 214b25b:docker-compose.yml | sha256sum`, em 02/10. Os da `jogavel-2026-10-03` são os
mesmos: o CRLF lido no checkout principal em 03/10 e o blob LF de
`git show 063b8a4:docker-compose.yml | sha256sum`. Os da `jogavel-2026-10-12` também: o CRLF
lido no checkout principal em 12/10 e o blob LF de `git show abd19aa:docker-compose.yml |
sha256sum`. Os da `jogavel-2026-10-13` também: o CRLF lido no checkout principal em 13/10 (K1.12)
e o blob LF de `git show 40b3826:docker-compose.yml | sha256sum`. Os da `jogavel-2026-10-14-3` e do
`candidato-13` (o mesmo commit): o CRLF lido no checkout principal em 14/10 (B1.7d), com a `main`
no `2619d70`, e o blob LF de `git show 2619d70:docker-compose.yml | sha256sum`. Os da
`jogavel-2026-10-14` e da `jogavel-2026-10-14-2` saíram só do blob: `git show b8b492f:` e
`git show eb4cb0e:docker-compose.yml | sha256sum` dão o `2a889474…` do `candidato-8` (15/10,
K1.13), e o CRLF é o do mesmo blob, sem leitura no checkout principal nessas datas. Os da
`jogavel-2026-10-16` também saíram só do blob: `git show 9c9b648:docker-compose.yml | sha256sum`
dá o `807b940d…` do `candidato-13` (16/10, K1.14). Os da `jogavel-2026-10-17` também:
`git show 1b5b5d3:docker-compose.yml | sha256sum` dá o mesmo `807b940d…` (17/10, K1.15). O
`docker-compose.vanilla.yml` do `candidato-15`, que só entra com a válvula on, tem o blob LF
`58c98479a3fc8945d5ba10a44882830362f7374e7d65f8bea6404584e09799ff` (`git show
1b5b5d3:docker-compose.vanilla.yml | sha256sum`); o CRLF dele não foi lido. Os da
`jogavel-2026-10-19` também saíram só do blob: `git show 54ef88d:docker-compose.yml | sha256sum`
dá o mesmo `807b940d…`, e `git show 54ef88d:docker-compose.vanilla.yml | sha256sum`, o mesmo
`58c98479…` (19/10, K1.16). Os da `jogavel-2026-10-19-2` também: `git show 0164cc3:` dá os
mesmos `807b940d…` e `58c98479…` (19/10, K1.17). Os da `jogavel-2026-10-19-3` também, pelo
`git show a32ef5e:` (19/10, K1.18), os da `jogavel-2026-10-20`, pelo `git show c228d93:` (20/10,
K1.20), e os da `jogavel-2026-10-21`, pelo `git show 69c45b1:` (22/10, K1.21). O da
`jogavel-2026-10-25` mudou (o `candidato-24` trocou o `CSSHARP_FIXED_VERSION`): o blob LF saiu de
`git show cc17bb4:docker-compose.yml | sha256sum` (25/10, K1.22), e o CRLF não foi lido; o
`git show cc17bb4:docker-compose.vanilla.yml | sha256sum` segue `58c98479…`. Os das duas tags de
26/10 também mudaram e saíram do mesmo jeito (26/10, K1.23): `git show 09e54bd:` (o P1.9 e o
P1.11 mexem no compose; o `docker-compose.vanilla.yml` segue `58c98479…`) e `git show 57e357b:`
(o bind do NadeSystem; o `docker-compose.vanilla.yml` vira `be0c3cf4…`, só comentário). O CRLF
não foi lido em nenhuma das duas. O da `jogavel-2026-11-04` saiu de
`git cat-file blob f16121f:docker-compose.yml | sha256sum` (04/11, P1.20): o K1.9 só tirou
comentário; o `docker-compose.vanilla.yml` segue `be0c3cf4…`, e o CRLF não foi lido. O da
`jogavel-2026-11-04-2` saiu de `git cat-file blob e80611e:docker-compose.yml | sha256sum` (05/11, P1.21), igual. Os da `jogavel-2026-11-08` e da `jogavel-2026-11-09` saíram de `git cat-file blob dff4222:` e `29087da:docker-compose.yml | sha256sum` (09/11, B1.18); o `docker-compose.vanilla.yml` segue `be0c3cf4…` nas duas, e o CRLF não foi lido.

Os config-hash das duas tags de 26/10 e o da `jogavel-2026-11-04` ficam abreviados aqui (K1.23 e P1.20): o valor inteiro está nos
registros de janela e nas coletas, fora do git (`config-hash-janela.txt` de `2026-10-26/p1.9-p1.11/g7-1327/`
e de `2026-10-26/b1.13/`; o da `jogavel-2026-11-04` no registro de 04/11, linhas 97, 121 e 131, e
em `2026-11-04/partida-k19-b115/coleta/config-hash-janela.txt`; o da `jogavel-2026-11-04-2`, o mesmo, no registro,
linha 143, e em `2026-11-04/partida-p115/coleta/config-hash-janela.txt`). Os da `jogavel-2026-11-08` e da `jogavel-2026-11-09` também ficam abreviados (B1.18): o inteiro está nos registros de 06/11 e 08/11 e nos `config-hash-janela.txt` de `2026-11-08/partida-b116/coleta/` e `2026-11-09/partida-b117/coleta/`.

config-hash:

```
jogavel-2026-09-27    5576531460072ecb9957c935c16886bc8600cec2824b3335db67a371266351df
jogavel-2026-09-27-2  a68705896cd9fe0c7f2f5688a196e6898099a98680165878d9dbcb42c10e1c31
jogavel-2026-09-27-3  dc0a3295d095f11e4cf7be41ac2068a2c1dadf0020e816b7bc84b4db0bb28996
jogavel-2026-09-27-4  ecbbf707988a34deaade85cbbf25753374ea8d02ecce9fc628de4da32e0631fa
jogavel-2026-09-27-5  a6bbdcefd88953243f810e902d8d4ab8ff0b0590d9aed75f7c419389bbfecb0b
jogavel-2026-09-28    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-01    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-03    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-12    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-13    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-14    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-14-2  3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-14-3  837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-16    837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-17    837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-19    837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-19-2  837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-19-3  837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-20    837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-21    837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b
jogavel-2026-10-25    0cf4006bf30eefbd230b47bf17b85dbc5fa2e8ca57cfb8e9a79999847d7091b7  (válvula on, compose do candidato-24)
jogavel-2026-10-26    1c412f6a…  (válvula on, compose do candidato-25; abreviado de propósito, ver abaixo)
jogavel-2026-10-26-2  19d8fdd8…  (válvula off, compose do candidato-26; abreviado de propósito, ver abaixo)
jogavel-2026-11-04    19d8fdd8…  (válvula off, compose do candidato-27; o mesmo valor da jogavel-2026-10-26-2; abreviado de propósito, ver abaixo)
jogavel-2026-11-04-2  19d8fdd8…  (válvula off, o mesmo compose da jogavel-2026-11-04; abreviado de propósito, ver abaixo)
jogavel-2026-11-08    19d8fdd8…  (válvula off, o mesmo compose da jogavel-2026-11-04-2; abreviado de propósito, ver abaixo)
jogavel-2026-11-09    6427c169…  (válvula off, compose do candidato-29, BotAimImprover mascarado; abreviado de propósito, ver abaixo)
candidato-2           c8a2a53512439ea4f9baa7cbe2e598e2c4b24b1c0725738593c42e3b2f860ac5
candidato-8           3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37  (Janela 0)
candidato-13          837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b  (janela do B1.7, 14/10)
candidato-15          837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b  (válvula off, janela de 17/10; = H_off)
candidato-15 (on)     0f3ff2b280f9470f63cc402764ff70ea4bf374e2d9dcb3f1fec1c08790dfe9e5  (válvula on, janela de 16/10; sem partida)
04/11 (on)            e863d2f6…  (válvula on, janelas de 04/11: 12:09 no 1ad6805 e antes do vanilla off da de 17:41; sem partida)
05/11 (on)            e863d2f6…  (válvula on, janela de 05/11 no dff4222, build 2000942; sem partida)
```

Arquivos montados e imagem:

```
aebb5df56682181f8a132c1e3c808f83ba1afac10060146238c04d097727762c  cfg/gamemode_competitive_server.cfg (disco, CRLF)
a0c195eec36b76670aa2e44e619cd92202407287c04df5613e99b26c40fe5b6f  cfg/gamemode_competitive_server.cfg (blob LF do git)
f3b0009c8f0f092be10b685dfb8c540d8122d290d29f699975f9fe666e8b712c  cfg/gamemode_competitive_server.cfg (K1.9, no disco do checkout principal = container; jogavel-2026-11-04)
7efa151a0793b3d19b29419b2137bcb190137c9bafd8172366aa7081e12df9e5  cfg/gamemode_competitive_server.cfg (K1.9, blob LF do git no f16121f)
233e5aa08cfe40d4c3a638031f630e7617270e1379ce09ed5390c97ae03c4f1d  pre.sh (LF no disco e no git)
697760a7566ee54a08b95bf804d6c21ab709b8e2762d83e5f8f846787270e115  Cs2TrackerEvents.dll (0.4.0, até a jogavel-2026-10-21)
75d0d6dff63825ae7f1ef74678051efe9997bc7e03440628e15d4fdcf046988b  Cs2TrackerEvents.dll (0.4.1, desde a janela de 22/10; jogavel-2026-10-25)
137a42f20c1c33f69fa95942437a43a0d431dd8e4beac71e985ee4697dbfdd99  Cs2TrackerEvents.deps.json (0.4.0 e 0.4.1)
ca994b0c37bf60e122b8ce4d25a1950bb71c82866b62f74c7240df5e37d07287  Cs2TrackerEvents.pdb (0.4.0)
0697c3750bea2b9f0a526171b0b4c11fcc840470aa30882610aab5973f2b42aa  Cs2TrackerEvents.pdb (0.4.1)
2f5fb06d61ee4984ae95dab3e8b097a3a29a6f2fe1c0e1990f9b76bf3319c785  match_config.spike.json (partida 26, matchid 74 e coleta de 14/10 depois da partida 82)
a6f6960623c91a4d6742e7b934d841792288f017fc6e5aa190f74106e9a9a627  match_config.spike.json (partidas 27, 29, 30 e 31)
f8eeeaf7fb2913f0d6baf1dd712631b5ddc137b075266e2f1c6e13b45657074f  match_config.spike.json (partida 28 e coletas de 17/10, depois da partida 85, e de 25/10, depois da partida 97)
0816da11af268caff0a19fc6d4040d795897a9478b74d7bcd052795d0facb1bd  match_config.spike.json (partida 36 e coleta de 19/10, depois da partida 88)
2000bf4e864826f24678f4cbb0e381f1399341f9a4bc54b01ab6debf8d89a7cf  match_config.spike.json (Janela 0, 02/10)
4eccec340c7ba883aeeceafdaf6323880c2304e9c3180bac3a7412a542d95de9  match_config.spike.json (coleta de 12/10, depois da partida 79)
a1e4ca2276832a174bdbe15647670ebaf1a2980b7d1bc683f0c68f36ffef7752  match_config.spike.json (coleta de 13/10, depois da partida 80)
b33fb17c0f7b15356a2adda49112183c1335704ccc44d1038bdd6cfc8c5880cc  match_config.spike.json (coleta de 14/10, depois da partida 81, e coleta de 19/10, depois da partida 89)
52bf794a33fc6475b795cf91e4ff61794c264cdb03ee2429ae2d0dc38b8102a0  match_config.spike.json (coleta de 14/10, depois da partida 83)
d29f6b1afa277d039cc2bf98b37118f63c3d0137dc1295a2a717159e9fb4e829  match_config.spike.json (coleta de 15/10, depois da partida 84, e coleta de 19/10, depois da partida 91)
8ed65092390b11f46f89512756b0c3c3b426d0f5141c2703bcb8580e2e60cc9b  BotAI.dll (fork 1.8.12-b1.7b, bind; manifesto do B1.7b)
289b24434de6eb1d42a8a7d2b4d48d2b56973bc4a2791c80d4ea5fb8d938d0a3  BotAI.deps.json
5cb31900c202ac767e39f7a9b07db02005e57a1bf7659fe8188c7430c3f865d8  BotAI.pdb
5be52c02d87d51c1173639a9a98dbc44c05f4184a549ad494df479834a9a0bf3  BotRandomizer.dll (B1.9, até a partida 81)
cfe7efc035b19260a7b4d0caec3339d0714dfad6e32de85ddf6921aee03d98b8  BotRandomizer.dll (b1.9b, desde a janela do B1.9b, 14/10)
539d62969f176595f8e21607a98c1f3aa58c13de7e833b5e27957955fc4a646b  BotRandomizer.pdb (b1.9b)
7075101b5d7ac0369eac102b04d23561611b88d5ce44ea0fcc68ff1fe55ad71b  RoundDamageRecap.dll (volume)
5ef13e7c08e37b3b66c5cf021d8ececde6ba2f05b5733846e54047f6df1d69a0  NadeSystem.dll (1.2.1-b1.13, fork local, bind; desde a janela de 26/10 13:48)
8c1a498b8119af809ce6d103746450de21ad7d460960d2e63e235881f3824c55  NadeSystem.deps.json (1.2.1-b1.13)
859f7578f16f6a442d147e3992966fc5fa6105fd46aecfa383f3ef55de79e431  NadeSystem.pdb (1.2.1-b1.13)
facbe9df36a2acf63a81c4cd113434116e9a7d206dadeb3d66dd803382659593  MANIFESTO.sha256 do NadeSystem (51 linhas, em 2026-10-26/b1.13/)
sha256:1056e0031e44709aa5e30a0a0a8f3d5de86c7ee16aa6fee1ec29726a7940ad04  xbird/cs2-matchzy
```

Binários do servidor (cópia só leitura, fora do repo, em `C:/Users/Victor/cs2-tracker-backups/`):

```
c7741272b76f16e936d6224dc121105e8051e1bc4d834be016c35ee3c63cac5a  libserver.so build 2000930 (PatchVersion 1.41.9.0, VersionDate Oct 08 2026; 41724600 B) em 2026-10-13/janela-diag/libserver-2000930/
d73f5d3b360fce87708451a239f8961399b34a2f7e4354326a5948c8676cfad2  libserver.so build 2000931 (PatchVersion 1.41.9.1, VersionDate Oct 14 2026; 41726328 B) em 2026-10-14/b1.7/libserver-2000931/
d73f5d3b360fce87708451a239f8961399b34a2f7e4354326a5948c8676cfad2  libserver.so build 2000933 (o mesmo arquivo da 2000931; steam.inf com VersionDate Oct 15 2026) em 2026-10-16/libserver-2000933/
ac63a1513aac0d7716aa7920d5ee8728feb9953600aea79f3c2c92780ba8eae7  libserver.so build 2000935 (CS2 v1.41.9.2; 41804088 B) em 2026-10-22/libserver-2000935.so
503c5b0e3c7dc0c1c66f32d51437da6896cf7eb3a7dd299db9c01f89199b59f5  libserver.so build 2000940 (CS2 v1.41.9.5, VersionDate Nov 02 2026; 41807736 B) em 2026-11-04/build-nova/libserver-2000940.so
ee0cc32a…  libserver.so build 2000942 (CS2 v1.41.9.6, VersionDate Nov 04 2026; 41850680 B) em 2026-11-06/b1.16/libserver-2000942.so (inteiro no MANIFESTO.sha256 da pasta)
```

CounterStrikeSharp (asset oficial do release v1.0.378, sem runtime; cópia em
`C:/Users/Victor/cs2-tracker-backups/2026-10-24/b1.3s/download/`, reaproveitada em 25/10):

```
26cf779ec3c87c55f4e23496839c7cc1e2977952ae9795403c4a52253d76fc82  counterstrikesharp-linux-1.0.378.zip (4137186 B; = digest do GitHub)
```

VPK (`overrides/<variante>/botprofile.vpk`, no volume):

```
02e5e958f3e0372b5616d858014d5801a980c23961556da9206a97887c1b29d0  Low (116432 B)
ba754b610aaeb67a3088a796b92cf28c49ac725ac071760aaf24208583dcc585  Medium (408010 B)
b08bf74eb74f1a0c9e84fb12c4a92bdb972703d35303cc69f9258176f0a10176  High (116192 B)
```

São a referência do critério 8 da
[trilha](trilha-de-bots.md#critérios-de-sucesso-de-cada-passo): a variante ativa é a que tem o
mesmo sha256 do `overrides/botprofile.vpk`, lido no volume pelo servidor (janela ou coleta),
com a hora. Os três valores foram lidos no volume nas janelas VPK de 28/09 (18:23 e 19:52) e
de novo no inventário da Janela 0 (02/10). O RoundDamageRecap 1.2.0 faz a mesma comparação e
anuncia Low `[1/3]`, Medium `[2/3]` ou High `[3/3]`, só no chat do jogo: o anúncio não é
evidência coletável.
