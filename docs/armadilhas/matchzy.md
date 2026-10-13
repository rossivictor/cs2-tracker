---
tipo: armadilha
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 14-23 e 31)"
  - "start_match.py:194-213"
  - "start_match.py:313-413"
  - "start_match.py:528-653"
  - "watcher.py:124-165"
  - "docs/features/M0.5-placar.md:138-162"
atualizado: 2026-10-13
---

# Armadilhas da MatchZy

Itens 14 a 23 e 31 da lista de 54 da auditoria de 26/09 ([índice](README.md)): o ciclo de
partida da MatchZy 0.8.15 com um humano contra bots, e o que dá para ler do log dela.

### 14. Bots não dão `.ready`
- **Sintoma:** a partida fica em warmup esperando (`[IsTeamReady] minPlayers:5 playerCount:0`), em todo mapa da série.
- **Causa:** a MatchZy só conta jogador de verdade como pronto.
- **Contorno:** `css_start` pela RCON força o ao vivo; o `run_match` repete o ciclo a cada mapa.
- **Fonte:** `docker/SPIKE.md:17-18` · `start_match.py:534-539` · `start_match.py:907-913` (auditoria: start_match.py:432-436)

### 15. O `live.cfg` desfaz o que vem antes do `css_start`
- **Sintoma:** quota e bloqueio de fim de round setados antes do `css_start` somem no ao vivo.
- **Causa:** o `live.cfg` zera `bot_quota` (linha 4) e `mp_ignore_round_win_conditions` (linha 58). O único gancho depois dele é o `cfg/MatchZy/live_override.cfg`, na última linha. Ele não dá `bot_kick`: os bots só saem no think seguinte.
- **Contorno:** o `start_match` escreve o `live_override.cfg` com a quota reafirmada. O README ainda diz que o ajuste tem que vir depois do `css_start`: está desatualizado (item 31).
- **Fonte:** `start_match.py:316-345` · `docs/features/M0.5-placar.md:141-162` · `README.md:481-482` (auditoria: start_match.py:217-233)

### 16. `mp_ignore_round_win_conditions 1` precisa sempre ser desligado
- **Sintoma:** nenhum round termina, nem por bomba, nem por tempo, nem num `.start` manual.
- **Causa:** a rede da camada 2 do override; se o processo morrer no meio, o `live_override.cfg` fica no volume com a linha ligada.
- **Contorno:** `finally` que desliga a cvar e reescreve o arquivo sem a linha. Se falhar, rodar `mp_ignore_round_win_conditions 0` à mão.
- **Fonte:** `start_match.py:338-340` · `start_match.py:405-413` · `start_match.py:639-653` (auditoria: start_match.py:235-237 e :536-550)

### 17. `matchid` inteiro e `team2` com `players`
- **Sintoma:** `matchid should be an integer!` ou `team2 should have 'players' JSON!` no loadmatch.
- **Causa:** validação do JSON da MatchZy.
- **Contorno:** `matchid` numérico ou ausente; `team2.players` com um SteamID64 fictício que nunca conecta.
- **Fonte:** `docker/SPIKE.md:154-160`

### 18. `cannot load a new match` com partida meio carregada
- **Sintoma:** o loadmatch novo é recusado em texto, e o fluxo forçava o início da partida antiga (vetou um mapa, subiu outro).
- **Causa:** a MatchZy guarda na memória uma partida que travou antes do `css_start`.
- **Contorno:** o `run_match` para com erro explícito; reiniciar o container limpa o estado (papel servidor).
- **Fonte:** `start_match.py:872-885` (auditoria: start_match.py:759-772)

### 19. O lado do time humano fica travado
- **Sintoma:** não dá para trocar de lado pelo menu do jogo com a partida carregada.
- **Causa:** a MatchZy fixa o `team1` no lado do `map_sides`.
- **Contorno:** escrever `map_sides` no `match_config` antes do `matchzy_loadmatch`.
- **Fonte:** `start_match.py:203-213` (auditoria: start_match.py:100-106)

### 20. `MATCH ENDED` nem sempre aparece
- **Sintoma:** fim de partida não detectado (matchid 9 teve só o `MAP ENDED`).
- **Causa:** a linha de fim de série com placar é irregular, mesmo em BO1.
- **Contorno:** o gatilho é o `[WritePlayerStatsToCsv]` do mesmo matchid, último passo do pipeline da MatchZy; o vencedor vem do `[SetMatchEndData]` anterior.
- **Fonte:** `watcher.py:124-152`

### 21. `Match_Start` não existe no log do container
- **Sintoma:** mapa sem nome (o `World triggered "Match_Start"` do modo nativo nunca chega).
- **Causa:** o log da MatchZy não tem a linha; o nome vem do `[ChangeMap]`, e com `--tail 0` só a partir do mapa 2.
- **Contorno:** três fontes, nesta ordem: `[ChangeMap]`, `maplist` do `match_config` por número do mapa, nome do `.dem`.
- **Fonte:** `watcher.py:162-164` · `watcher.py:415-431`

### 22. A MatchZy só loga no stdout do container
- **Sintoma:** nenhum arquivo de log no host para o watcher seguir.
- **Causa:** a MatchZy não grava log em arquivo.
- **Contorno:** seguir `docker logs -f` (watcher) e ler `docker logs --tail` (estado dos times).
- **Fonte:** `watcher.py:322-325` · `start_match.py:225-228`

### 23. `mp_teamscore_1/2` é o placar da série
- **Sintoma:** o placar lido não muda round a round.
- **Causa:** as cvars contam mapas ganhos na BO-N.
- **Contorno:** placar do mapa pelo `get5_status` (JSON com `current_map_score`).
- **Fonte:** `tools/live_watch.py:136-143`

### 31. Montar os times ao vivo gera round fantasma
- **Sintoma:** round encerrado na hora, com zero mortes e zero danos, às vezes contado no placar (partida começando 1x0).
- **Causa:** bot conectado e não spawnado conta como morto, e o `CheckWinConditions` dá vitória por extermínio. Só o warmup o anula (`IsWarmupPeriod`); o freezetime não.
- **Contorno:** montar os times no warmup, antes do `css_start` (ordem invertida em 19/09), com o item 15 segurando a quota.
- **Fonte:** `start_match.py:434-441` · `start_match.py:541-545` · `docs/features/M0.5-placar.md:138-139` (auditoria: start_match.py:331-338)
