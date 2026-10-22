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
  - "docker-compose.yml:62-64"
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
atualizado: 2026-10-22
---

# Versões conhecidas

> **Para quem:** o papel servidor, na volta ao jogável e na Janela 0; o tech-manager, ao criar uma tag `jogavel-*`; o QA, ao conferir uma coleta.
> **Card:** B0.3. Cada tag registrada aqui é uma combinação em que o Victor jogou ([ADR-0004](../adr/0004-jogo-sempre-jogavel.md)).

A volta ao jogável precisa saber qual combinação era a boa, e até aqui essa informação estava espalhada em commits, runbooks e registros de janela. Esta nota junta tudo por tag.

Convenções:

- sha256 aparece abreviado (8 caracteres) nas tabelas. O valor inteiro está em [Hashes completos](#hashes-completos).
- **não registrado** quer dizer que nenhuma fonte guardou o valor. A nota diz de onde ele viria. Nenhum valor daqui é estimado.
- Fontes fora do git: os registros de janela em `logs/janelas/2026-09-27.md`, `2026-09-28.md`, `2026-09-30.md`, `2026-10-02.md`, `2026-10-13.md`, `2026-10-14.md`, `2026-10-16.md`, `2026-10-17.md` e `2026-10-19.md` (checkout principal), as coletas em `C:/Users/Victor/cs2-tracker-backups/2026-09-27/`, `2026-09-28/`, `2026-10-01/`, `2026-10-02/`, `2026-10-03/`, `2026-10-12/`, `2026-10-13/`, `2026-10-14/`, `2026-10-15/`, `2026-10-16/`, `2026-10-17/`, `2026-10-19/`, `2026-10-20/` e `2026-10-21/`, e os Históricos do card 17 (B0.8), do card 62,7 (T1.3c), do card 80 (P1.1), do card 26 (B1.7), do card 80,7 (P1.1b), do card 81 (P1.2), do card 80,8 (P1.1c), do card 80,9 (P1.1d), dos cards 82 (P1.3) e 83 (P1.4), dos cards 84 (P1.5) e 85 (P1.6) e dos cards 86 (P1.7) e 87 (P1.8) no board.
  Nas tabelas, `b1.x/...` é relativo a `2026-09-27/`, a coleta da partida 36 aparece como `2026-10-01/g7-2000922-partida/`, a da Janela 0 como `2026-10-02/janela0/`, a do G7 do B0.8 como `2026-10-03/coleta-g7-b0.8-0015/`, a do G7 do `candidato-9` como `2026-10-12/coleta-g7-candidato-9/`, a do G7 do `candidato-10` como `2026-10-13/coleta-g7-p1.1/`, a da janela de diagnóstico do B1.12b como `2026-10-13/janela-diag/`, a do G7 do `candidato-11` como `2026-10-14/coleta-g7-p1.1a/`, a da janela do B1.9b como `2026-10-14/b1.9b/`, a do G7 do `candidato-12` como `2026-10-14/coleta-g7-b1.9b/`, a da janela do B1.7 como `2026-10-14/b1.7/`, a do G7 do `candidato-13` como `2026-10-14/coleta-g7-b1.7/`, a do G7 do `candidato-14` como `2026-10-15/coleta-g7-p1.1b/`, as das janelas do P1.2 como `2026-10-16/p1.2/` (vanilla on) e `2026-10-17/p1.2/` (vanilla off), a do G7 do `candidato-15` como `2026-10-17/coleta-g7-p1.2/`, a do G7 do `candidato-16` como `2026-10-19/coleta-g7-p1.1c/`, a do G7 do `candidato-17` como `2026-10-19/coleta-g7-p1.1d/` a do G7 do `candidato-18` como `2026-10-19/coleta-g7-p1.3-p1.4/`, a do G7 do `candidato-20` como `2026-10-20/coleta-g7-p1.5-p1.6/`, a do G7 do `candidato-21` (reprovado) como `2026-10-20/coleta-g7-p1.7-p1.8/` e a do G7 do `candidato-22` como `2026-10-21/coleta-g7-p1.7-p1.8-v2/`.

## O que não mudou em nenhuma tag

| Item | Valor | Fonte |
|---|---|---|
| Imagem | `xbird/cs2-matchzy`, sem tag no compose (vale a `latest` local). Digest `sha256:1056e003…`, o mesmo de 27/09 01:44 (antes do B1.3r) a 30/09 23:05 (janela da build 2000922). O container de 28/09 durou até a partida 36: na coleta dela (01/10) o `Created` segue `2026-09-28T01:30:07Z`. A Janela 0 (02/10, B0.8) o recriou: desde então o `Created` é `2026-10-02T03:30:20Z` (coleta de 12/10). As janelas de 14/10 (B1.9b e B1.7) o recriaram de novo: o da `jogavel-2026-10-14-3` é de `2026-10-15T00:15:44Z`, e a `jogavel-2026-10-16` jogou no mesmo, reiniciado sem recreate. O digest da imagem nessas janelas: não registrado. As janelas do P1.2 o recriaram mais duas vezes (vanilla on em 16/10, off em 17/10) e leram o digest: `1056e003…`, o mesmo. O da `jogavel-2026-10-17` é de `2026-10-17T19:33:02Z`, e a `jogavel-2026-10-19` jogou no mesmo, subido pelo `start_match` sem recreate (`StartedAt` 2026-10-19T18:52:48Z). A `jogavel-2026-10-19-2` e a `jogavel-2026-10-19-3` jogaram no mesmo e na mesma subida: o `start_match` o achou rodando. A `jogavel-2026-10-20` jogou no mesmo container, sem recreate, numa subida nova: reiniciado às 2026-10-20T16:49:06Z, fora de janela. A `jogavel-2026-10-21` também, sem recreate, em outra subida: a TUI subiu às 2026-10-21T21:57:21Z o container parado pela queda do Docker Desktop (estado no ar) | `b1.3r/antes-container.txt`; registros de janela; `2026-10-01/g7-2000922-partida/estado-container.txt`; `2026-10-12/coleta-g7-candidato-9/container-inspect.txt`; `2026-10-17/p1.2/antes-container.txt` e `off-container.txt`; Históricos dos cards 80,8, 80,9, 82, 83, 84, 85, 86 e 87 |
| MatchZy | `0.8.15` (`MATCHZY_FIXED_VERSION`) | compose de todas as tags |
| Captura | CS2 Tracker Events 0.4.0: DLL `697760a7…`, `.deps.json` `137a42f2…`, `.pdb` `ca994b0c…`. A DLL é de 23/09, e o checkout de 26/09 já tinha esse sha | `backup:MANIFESTO.sha256`; [manifesto](#manifesto-do-plugin-de-captura) |
| `pre.sh` | `233e5aa0…`. Sem diff entre `efcaa42` e `origin/main` | `git diff --stat efcaa42 origin/main -- docker/pre.sh` vazio |
| `gamemode_competitive_server.cfg` | `aebb5df5…` no disco (CRLF; o blob LF do git é `a0c195ee…`). Sem diff entre `efcaa42` e `origin/main` | idem, `server-configs/` |
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

**Estado no ar:** a `jogavel-2026-10-21` (`69c45b1`). Ela fecha o `candidato-22` (o mesmo commit, merge do PR #109 sobre o #108), o par P1.7 + P1.8 da exceção do Victor de 19/10 ao trilho único ([sprints](../agents/sprints.md#exceções-aprovadas)), refeito depois do `candidato-21` reprovado (nota abaixo): P1.7, a contagem de presentes pelo `status` do RCON, sem a SourceTV (`6d6aa2b`, PR #108); P1.8, o `live_override.cfg` neutro antes do `loadmatch` (`d5e61d7`, PR #109, o `7b53343` reaplicado). Validado pela partida 96 (`VEREDITO G7: OK` do `evidencia_partida.py` com `--partida events_96_map0 --build-esperada 2000934`, sobre o log cortado no `StartedAt` e a cópia do banco em `mode=ro`; Históricos dos cards 86 e 87 e mensagem da tag).
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
(ressalvas acima). Nas três tags de 14/10 também não: nenhuma das janelas de 14/10 escreveu no volume. Na `jogavel-2026-10-16` também não, e não houve janela desde as de 14/10. Na `jogavel-2026-10-17` também não: as janelas do P1.2 não escreveram no volume. Na `jogavel-2026-10-19` também não, e não houve janela desde a de 17/10. Na `jogavel-2026-10-19-2` também não, pelo mesmo motivo. Na `jogavel-2026-10-19-3` também não: a janela T2 de 19/10 não escreveu no volume. Na `jogavel-2026-10-20` também não: a janela T2 de 20/10 só reiniciou o container e virou mapas, sem trocar o VPK. Na `jogavel-2026-10-21` também não: o par P1.7 + P1.8 não teve janela.

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
| 2000934 | 2026-10-21T21:57:21Z (18:57 em -03), na subida pela TUI do container parado pela queda do Docker Desktop; download terminado às 22:01:57Z | update do SteamCMD no boot, sem janela nem OK prévio. A 1ª tentativa falhou com `Error! App '730' state is 0x6 after update job` (21:57:33Z); a 2ª verificou a instalação inteira (73389778054 bytes, ~73,4 GB; de 21:57:41Z a 22:01:43Z), baixou o resto da atualização (22:01:45Z a 22:01:49Z) e terminou com `Success! App '730' fully installed` às 22:01:57Z. Do `StartedAt` ao `Pronto` da captura (22:02:06Z): ~4 min 45 s | partida 96 (21/10, de_inferno 13x5, G7 OK com `--build-esperada 2000934`). No boot: BotAI do fork com `m_gameState = 0x50F8` (OnUpdate e OnBombPlanted concordam, como na 2000933) e `Applied 40/40 patches.`, 9 plugins carregados e nenhuma assinatura falha. **Ressalva:** a conferência formal do BotAI do fork nesta build (B1.7c: `conferir_botai` sobre a cópia do `libserver.so` da 2000934, [a cada build nova](b1.7b-botai-fork-assinatura.md#a-cada-build-nova-do-cs2)) ainda não rodou: a cópia sai do container e pede janela, e o fork jogou a partida 96 sem ela | `jogavel-2026-10-21` |

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

Com a válvula on (janela de 16/10, G6 do on), o config-hash do `candidato-15` foi `0f3ff2b2…`
(`2026-10-16/p1.2/on-config-hash-janela.txt`, igual ao `docker compose config --hash` com os dois `-f`).
Nenhuma partida jogou nele.

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
build novo ganha uma pasta nova ao lado, e a velha não se apaga. Para restaurar, o servidor
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
a `jogavel-2026-10-20`, o K1.20, e a `jogavel-2026-10-21`, o K1.21).

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
K1.20), e os da `jogavel-2026-10-21`, pelo `git show 69c45b1:` (22/10, K1.21).

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
candidato-2           c8a2a53512439ea4f9baa7cbe2e598e2c4b24b1c0725738593c42e3b2f860ac5
candidato-8           3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37  (Janela 0)
candidato-13          837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b  (janela do B1.7, 14/10)
candidato-15          837cbcbcb6a2544a4ff1452864c92802463b181286114e5baec427d691e5e48b  (válvula off, janela de 17/10; = H_off)
candidato-15 (on)     0f3ff2b280f9470f63cc402764ff70ea4bf374e2d9dcb3f1fec1c08790dfe9e5  (válvula on, janela de 16/10; sem partida)
```

Arquivos montados e imagem:

```
aebb5df56682181f8a132c1e3c808f83ba1afac10060146238c04d097727762c  cfg/gamemode_competitive_server.cfg (disco, CRLF)
a0c195eec36b76670aa2e44e619cd92202407287c04df5613e99b26c40fe5b6f  cfg/gamemode_competitive_server.cfg (blob LF do git)
233e5aa08cfe40d4c3a638031f630e7617270e1379ce09ed5390c97ae03c4f1d  pre.sh (LF no disco e no git)
697760a7566ee54a08b95bf804d6c21ab709b8e2762d83e5f8f846787270e115  Cs2TrackerEvents.dll
137a42f20c1c33f69fa95942437a43a0d431dd8e4beac71e985ee4697dbfdd99  Cs2TrackerEvents.deps.json
ca994b0c37bf60e122b8ce4d25a1950bb71c82866b62f74c7240df5e37d07287  Cs2TrackerEvents.pdb
2f5fb06d61ee4984ae95dab3e8b097a3a29a6f2fe1c0e1990f9b76bf3319c785  match_config.spike.json (partida 26, matchid 74 e coleta de 14/10 depois da partida 82)
a6f6960623c91a4d6742e7b934d841792288f017fc6e5aa190f74106e9a9a627  match_config.spike.json (partidas 27, 29, 30 e 31)
f8eeeaf7fb2913f0d6baf1dd712631b5ddc137b075266e2f1c6e13b45657074f  match_config.spike.json (partida 28 e coleta de 17/10, depois da partida 85)
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
sha256:1056e0031e44709aa5e30a0a0a8f3d5de86c7ee16aa6fee1ec29726a7940ad04  xbird/cs2-matchzy
```

Binários do servidor (cópia só leitura, fora do repo, em `C:/Users/Victor/cs2-tracker-backups/`):

```
c7741272b76f16e936d6224dc121105e8051e1bc4d834be016c35ee3c63cac5a  libserver.so build 2000930 (PatchVersion 1.41.9.0, VersionDate Oct 08 2026; 41724600 B) em 2026-10-13/janela-diag/libserver-2000930/
d73f5d3b360fce87708451a239f8961399b34a2f7e4354326a5948c8676cfad2  libserver.so build 2000931 (PatchVersion 1.41.9.1, VersionDate Oct 14 2026; 41726328 B) em 2026-10-14/b1.7/libserver-2000931/
d73f5d3b360fce87708451a239f8961399b34a2f7e4354326a5948c8676cfad2  libserver.so build 2000933 (o mesmo arquivo da 2000931; steam.inf com VersionDate Oct 15 2026) em 2026-10-16/libserver-2000933/
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
