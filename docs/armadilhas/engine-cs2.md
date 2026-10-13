---
tipo: armadilha
status: rascunho
fontes:
  - "backup:../2026-10-04/coleta-bo3-interrompida/docker-logs-antes-do-start.txt (linhas 13762-13779: loadmatch do matchid 75; 13916-13995: entrada e overflow de 04/10; 14024-14040: reentrada)"
  - "backup:../2026-09-27/b1.3r/docker-logs-antes.txt (linhas 11415-11421: VPK, segfault e boot de 26/09; 11971-12032: overflow de 26/09; 12054: reentrada; 731-732 e 4706-4789: entrada e overflow em jogo de 23/09; 10306-10308: recv queue overflow)"
  - "backup:../2026-09-30/update-build/docker-logs-antes.txt (linhas 12072-12074: recv queue overflow na virada 70: 1→2)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.LEIAME.txt (cobertura e fronteiras de 05/10 e 06/10)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.txt (entradas de 05/10 e 12/10)"
  - "backup:temp-artifacts/eb5adec0/digests/claude_2026-09-21_5a2af0df.md (linhas 1572-1603, 1781-1788, 1932-1969 e 2683-2729: relatos de 23/09 e 26/09)"
  - "backup:repo-local/logs/teste-correcao.log (espelho filtrado da partida 45, 19/09)"
  - "backup:repo-local/events-live/ (nomes e mtime dos events_44 a events_60)"
  - "docs/runbooks/trilha-de-bots.md:240-257 (confundidor 1: warmup.cfg e o offset de Respawn)"
  - "docs/runbooks/trilha-de-bots.md:382-395 (épocas de build, VPK e plugins)"
  - "docs/runbooks/b1.12-segfault-troca-de-mapa-md3.md:265 (o overflow de 04/10 não tem relação com a queda)"
  - "docs/historico/2026-09-26-handoff-plugins-de-bot.md:152-165"
  - "docs/agents/sprints.md:87 (o P1.13 mede a carga do PC)"
  - "tools/evidencia_partida.py:79 (FULL + 60 s)"
  - "tools/evidencia_partida.py:164-170 (o que conta como overflow)"
  - "tools/jogavel.py:1321-1349 (o que o coletar guarda hoje)"
  - "commit b865873 (04/10 16:36Z, merge do T1.1)"
  - "commit 58f35b5 (04/10 16:41Z, T1.3b)"
  - "commit bafe2b4 (26/09 16:07Z)"
atualizado: 2026-10-13
---

# Armadilhas do engine do CS2

Pegadinhas do servidor dedicado do CS2 (o engine, não a MatchZy nem os plugins). Cada uma tem
sintoma, o que o log mostra, contorno e fonte. Hoje há uma.

## Overflow no signon (`NETWORK_DISCONNECT_OVERFLOW` na entrada)

> **Origem:** card P1.13, investigação Offline sobre cópias de log em
> `C:/Users/Victor/cs2-tracker-backups/` (nada vivo foi tocado). **Para quem:** o PM e o
> Victor (o que fazer quando acontece e o que medir), o QA (como contar) e quem religar plugin
> (não é regressão). Convenção: **E** é evidência (linha de log ou trecho lido), **H** é
> hipótese. Nick, SteamID e IP saíram dos trechos (`<jogador>`). Horários em UTC; o Victor
> joga em -03.

### Resumo

- **Não é estouro de buffer de rede.** O servidor derruba o jogador quando processar as
  mensagens dele num frame passa de um limite de tempo de relógio, e escreve o motivo:
  `Disconnecting netchan because of excessive CPU usage`. O cliente mostra "Overflow error".
  Ping e perda de pacote estavam limpos (E3).
- **Frequência.** Desde que há cópia de `docker logs` (23/09 21:41Z): **2 overflows no signon
  em 25 entradas novas** (8 %), em **2 das 22 sessões de jogo** cobertas: 26/09 16:04
  (partida 60) e 04/10 16:49 (matchid 75, mapa 1). **0 em 4** reentradas por troca de mapa.
  Mais 1 overflow **em jogo** (23/09 22:08), de causa conhecida e corrigida. De 19/09 a
  23/09 21:41Z não há cópia de log: só 3 relatos de 23/09, na época quebrada do update.
- **Reentrar resolveu 2 de 2** (79 s e 11 min depois), no mesmo processo do servidor.
- **`warmup.cfg` da MatchZy (hipótese da trilha): enfraquecida.** Em 04/10 a queda veio antes
  de a MatchZy fazer qualquer coisa com o jogador; em 26/09 o tempo foi gasto no handler de
  FULL CONNECT da MatchZy, e o `execing MatchZy/warmup.cfg` só saiu no frame seguinte (H1).
- **Carga do host: sem evidência que a separe.** As cópias não medem carga. Os sinais
  indiretos não acusam fome de CPU sustentada antes da queda de 04/10, e a reentrada 79 s
  depois passou barata (H2). Fica como possível agravante, a medir.
- **Padrão mais forte nos dados (H3): a entrada fica cara depois de horas sem humano.** As 5
  entradas com 1,6 h ou mais de servidor vazio custaram de 110 a 295 ms; das 19 entradas logo
  depois de boot ou de outra partida, só 2 passaram de 100 ms. O limite da queda está entre
  152 e 237 ms. Mecanismo desconhecido.
- **Não exige mudança de cfg.** Nenhuma linha de cfg ficou implicada. O próximo passo é medir
  (seção "O que medir a mais").

### Assinatura e como contar

A linha contada (crua, anonimizada; o carimbo vem do `docker logs -t`):

```
2026-10-04T16:49:35.916965088Z Disconnect client '<jogador>' from server: NETWORK_DISCONNECT_OVERFLOW
```

O episódio completo, de 04/10 (`docker-logs-antes-do-start.txt:13951-13995`, carimbos
cortados no milissegundo):

```
16:49:35.649  Client 1 '<jogador>' signon state SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL
16:49:35.913  [<jogador>] DISCONNECTING. ProcessMessages has taken more than 264ms to process 5 messages.  (Current message type: 'CNETMsg_StringCmd [5]')
16:49:35.916  netchan.cpp (1948) : Assertion Failed in function operator()():
16:49:35.916  Disconnecting netchan because of excessive CPU usage /+/ 264ms, 5, current message type: 'CNETMsg_StringCmd [5]'
16:49:35.916  Disconnect client '<jogador>' from server: NETWORK_DISCONNECT_OVERFLOW
16:49:35.925  Client 1 '<jogador>' signon state SIGNONSTATE_FULL -> SIGNONSTATE_NONE
16:49:35.925  SV:  Dropped client '<jogador>' from server(5): NETWORK_DISCONNECT_OVERFLOW
16:49:35.942  [#... UDP steamid:<id>@<ip>:<porta> '<jogador>'] closed by app, linger requested but not needed (2005) NETWORK_DISCONNECT_OVERFLOW
16:49:35.945  8.578125 Long frame (WarmupPeriod): 296.25ms elapsed, 295.45ms sim time, 1 ticks, 549..549.
```

Regras de contagem:

- **S1, o overflow:** uma linha `Disconnect client '<nick>' from server: NETWORK_DISCONNECT_OVERFLOW`
  é um episódio. O `DISCONNECTING`, o `Dropped` e o `closed by app` são o mesmo episódio.
- **No signon** quando o S1 vem até 5 s depois do `SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL` do
  mesmo jogador; **em jogo** quando vem depois. Os dois casos de signon vieram a +0,26 s e
  +1,13 s; o caso em jogo, a +14 min 37 s.
- **S2, o aviso (não derruba):** `NetChan <nick> ProcessMessages has taken more than <N>ms`,
  sem `DISCONNECTING`. Aparece a partir de uns 55 ms.
- **S3, outra coisa:** `recv queue overflow 100 messages already queued.`, da camada de rede da
  Steam. Saiu em rajadas de 3 linhas na troca de mapa da série (26/09 14:03:14 e 30/09
  21:11:24), com o jogador em `SIGNONSTATE_CHANGELEVEL`. Ele voltou a FULL 4 a 5 s depois e
  seguiu jogando. Não derruba e não entra na contagem.
- As cópias se sobrepõem (o mesmo trecho está em várias coletas). Como cada linha tem o
  carimbo do `docker logs -t` com nanossegundos, a linha inteira identifica o evento:
  deduplique por ela (`sort -u`).

Comandos reproduzíveis (Git Bash, só leitura das cópias):

```
B=C:/Users/Victor/cs2-tracker-backups
copias() { find "$B" -path '*/temp-artifacts' -prune -o -name 'docker-logs*.txt' -print0; }
copias | xargs -0 grep -h "from server: NETWORK_DISCONNECT_OVERFLOW" | sort -u   # S1: 3 linhas
copias | xargs -0 grep -h "SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL" | sort -u | wc -l   # 29 entradas
copias | xargs -0 grep -h "ProcessMessages has taken more than" | sort -u | wc -l   # 24 (S2 e os DISCONNECTING)
copias | xargs -0 grep -h "recv queue overflow" | sort -u | wc -l   # 6 (S3)
```

Os números da tabela abaixo saíram de uma linha do tempo única: todas as 53 cópias de
`docker-logs*.txt` (menos o LEIAME), deduplicadas pela linha inteira e ordenadas pelo
carimbo. Para cada entrada do humano (`SPAWN -> FULL`), mediram-se o primeiro `Long frame`
até 1,5 s depois do FULL, o aviso S2 até 1 s depois e o tempo desde o último boot
(`Redirecting stderr`) ou desde a última saída do humano (`SIGNONSTATE_FULL -> ...`).

### O que o log mostra

- E1. Nos dois casos de signon, o tempo gasto nas mensagens do jogador é quase todo o tempo
  de simulação de um único tick: 264 ms contra o `Long frame` de 295 ms de sim em 04/10;
  237 ms contra 256 ms em 26/09. O que trava é o processo do servidor num tick, não a rede.
- E2. **O limite observado fica entre 152 e 237 ms.** O maior aviso sem queda foi de 152 ms
  (23/09 21:53:26, `b1.3r/docker-logs-antes.txt:732`). As quedas vieram com 237, 264 e 317 ms
  (este em jogo), e com 598 ms no relato de 23/09 20:58Z. O nome e o valor da cvar do limite
  não estão em nenhuma cópia.
- E3. Não é a rede. O resumo da conexão de 26/09 traz 0 pacote perdido, 0 fora de ordem e
  ping mediano de 1 ms, em 21 amostras de 0 a 25 ms (`b1.3r/docker-logs-antes.txt:11986-12022`).
- E4. **Toda entrada tem um tick caro logo depois do FULL.** É o processamento dos
  `CNETMsg_StringCmd` que o cliente manda ao ficar FULL: o S2 sai de +0,06 a +0,26 s, sempre
  com esse tipo de mensagem. O custo desse tick vai de 1 a 76 ms em 22 entradas e de 110 a
  295 ms em 7 (coluna "Custo" da tabela). O overflow de 04/10 é a ponta dessa
  distribuição. Quais comandos o cliente manda nesse instante não aparece no log.
- E5. **Em 26/09 a queda veio de um segundo tick caro, o do FULL CONNECT da MatchZy.** O frame
  que derrubou começou por volta de 16:04:01,648 e durou 256,89 ms. Dentro dele, as 4 linhas do
  handler da MatchZy saíram com uns 70 ms de intervalo, das 16:04:01,671 às 16:04:01,880. Nas
  outras 27 entradas com FULL CONNECT, o mesmo trecho (do FULL CONNECT ao StartWarmup) levou de
  0 a 51 ms. O
  `execing MatchZy/warmup.cfg` só saiu às 16:04:01,908, no frame seguinte, depois da queda e do
  `Long frame` (`b1.3r/docker-logs-antes.txt:11977-12027`).

### Frequência por partida desde 19/09

#### De 19/09 a 23/09 21:41Z: sem cópia de `docker logs`

A primeira cópia começa no boot de 23/09 21:41:04Z (`b1.3r/docker-logs-antes.txt:1`). O
container anterior não foi copiado. As partidas abaixo saíram dos nomes e do mtime (-03) dos
arquivos em `repo-local/events-live/` e `stats-live/`.

| Data | Partidas | Overflow no signon | De onde |
|---|---|---|---|
| 19/09 | 44 (MD3, 3 mapas arquivados) | sem cópia | — |
| 19/09 | 45 (MD3; mapas 0 e 2 arquivados) | sem cópia; sem sinal no espelho | `teste-correcao.log`: espelho filtrado das 17:31Z às 20:04Z, que cobre os 3 mapas. Traz um FULL CONNECT por mapa e nenhuma linha de signon nem de desconexão. Inconclusivo: em 04/10 a queda veio antes do FULL CONNECT, e a reentrada produziu um FULL CONNECT só. |
| entre 19 e 21/09 | 46, 47 (sem arquivo nenhum) | sem cópia | — |
| 21/09 | 48 (mapas 0 e 2), 49 (só `stats-live`), 50, 51 | sem cópia | — |
| 22/09 | 52 | sem cópia | — |
| 23/09 | 53 a 57 (sem arquivo; provável época do update) | **3 relatos**, sem log copiado | transcript 5a2af0df: "Não consegui entrar" às 20:58Z (S1 a 598 ms, `Long frame` de 885 ms), "reproduziu duas vezes" por volta das 21:03Z (StringCmd e depois Move), e "Overflow error" às 21:27:55Z, aos 14 s de um boot. Era a build 2000914 recém-chegada, com 15 detours do BotAI falhando, o BotAimImprover inativo e segfaults. |

Os digests de transcript de 19/09 a 23/09 não têm nenhum outro relato de overflow. Isso não é
evidência de ausência: só cobrem as sessões com o Claude aberto.

#### De 23/09 21:41Z a 12/10: uma linha por entrada do humano

"Sem humano" é o tempo desde o último boot do processo ou a última saída do jogador, o que
vier depois. "Custo" é o tempo de sim do primeiro `Long frame` até 1,5 s depois do FULL, com o
aviso S2 entre parênteses. "Commits" conta os commits deste repo a ±30 min do FULL, o único
rastro de atividade de agente nas cópias, e só se lê como indício.

| FULL (UTC) | Partida | Build · VPK · época | Entrada | Sem humano | Custo (ms) | Overflow (Δ do FULL) | Desfecho | Commits |
|---|---|---|---|---|---|---|---|---|
| 23/09 21:53:26 | sem events (interrompida) | 2000914 · ? · pós-update | nova | 0,2 h | 163 (152) | **em jogo, +14 min 37 s** (317 ms) | derrubado em jogo | 0 |
| 25/09 22:36:15 | 58 | 2000918 · antes do High · 0 | nova | 0,3 h | 51 | não | seguiu | 0 |
| 26/09 13:39:33 | 59, mapa 1 | 2000918 · antes do High · 0 | nova | 0,0 h | 34 | não | seguiu | 0 |
| 26/09 14:03:18 | 59, mapa 2 | idem | troca de mapa | — | 26 | não (S3 às 14:03:14) | seguiu | — |
| **26/09 16:04:00** | **60** | 2000918 · High · 0 | nova | 0,05 h (boot 16:01:15, depois do segfault do VPK) | 134 (127) e 256 no FULL CONNECT | **signon, +1,13 s** (237 ms, Move) | derrubado; reentrou 11 min depois | 1 |
| 26/09 16:15:04 | 60 | idem | nova (reentrada) | 0,2 h | 19 | não | seguiu | 1 |
| 27/09 02:55:59 | 61 | 2000918 · High · 0 | nova | 0,0 h | 24 | não | seguiu | 7 |
| 27/09 12:50:35 | sem matchid (provável 62; 7 min) | 2000918 · High · 1 | nova | 1,45 h | 28 | não | saiu (DISCONNECT_BY_USER) | 0 |
| 27/09 16:49:08 | 63 | 2000918 · High · 1 | nova | 0,0 h | 25 | não | seguiu | 0 |
| 27/09 20:52:10 | 64 | 2000918 · Medium · 2b | nova | 1,95 h | 110 (103) | não | seguiu | 0 |
| 27/09 22:00:03 | 65 | 2000918 · Medium · 3 | nova | 0,2 h | 24 | não | seguiu | 5 |
| 27/09 23:29:23 | 66 | 2000918 · Medium · 4 | nova | 0,3 h | 16 | não | seguiu | 0 |
| 28/09 00:40:00 | 67 | 2000918 · Medium · 6 | nova | 0,4 h | 18 | não | seguiu | 2 |
| 28/09 22:00:02 | 68 | 2000918 · Medium · 7 | nova | 0,0 h | 76 (62) | não | seguiu | 0 |
| 30/09 18:31:22 | 69 | 2000919 · Low | nova | 0,0 h | 21 | não | seguiu | 1 |
| 30/09 20:37:29 | 70, mapa 1 | 2000919 · Low | nova | 1,6 h | 159 (149) | não | seguiu | 4 |
| 30/09 21:11:29 | 70, mapa 2 | 2000919 · Low | troca de mapa | — | 46 | não (S3 às 21:11:24) | seguiu | — |
| 30/09 21:49:38 | 70, mapa 3 | 2000919 · Low | troca de mapa | — | 21 | não | seguiu | — |
| 01/10 21:04:40 | 71 | 2000922 · Low | nova | 0,0 h | 37 | não | seguiu | 0 |
| 02/10 00:36:36 | 72 | 2000922 · Low | nova | 3,0 h | 128 (122) | não | seguiu | 5 |
| 02/10 01:05:42 | 73, mapa 1 | 2000922 · Low | nova | 0,1 h | 21 | não | seguiu | 2 |
| 02/10 01:39:25 | 73, mapa 2 | 2000922 · Low | troca de mapa | — | 17 | não | seguiu | — |
| 03/10 02:07:56 | 74 | 2000922 · Low | nova | 22,6 h | 112 (107) | não | seguiu | 1 |
| **04/10 16:49:35** | **75, mapa 1** | 2000922 · Low | nova | **37,6 h** (processo de 61,3 h) | **295 (264)** | **signon, +0,26 s** (264 ms, StringCmd) | derrubado; reentrou 79 s depois | 2 |
| 04/10 16:50:54 | 75, mapa 1 | 2000922 · Low | nova (reentrada) | 0,0 h | 15 | não | seguiu (a queda depois é o B1.12) | 2 |
| 04/10 17:19:36 | 76 | 2000924 · Low (inferido) | nova | 0,1 h | 27 | não | seguiu | 2 |
| 05/10 22:26:35 | sem matchid (provável 77; 5 min) | 2000924 · Low (inferido) | nova | 0,0 h | 33 | não | saiu (DISCONNECT_BY_USER) | 0 |
| 05/10 23:12:44 | 78 | 2000924 · Low (inferido) | nova | 0,0 h | 1 | não | seguiu | 0 |
| 12/10 21:38:30 | 79 | 2000930 · Low (inferido) | nova | 0,0 h | 22 | não | seguiu | 0 |

- As épocas são as da [trilha](../runbooks/trilha-de-bots.md#épocas). O VPK antes de 26/09
  16:01Z não está registrado. O transcript de 26/09 diz que o High foi copiado naquele
  instante; antes, o Low é provável.
- Buracos sem nenhuma linha, de 1,6 a 161 h: 24/09 02:51 → 25/09 21:44, 26/09 01:16 → 13:38,
  14:26 → 16:00, 20:28 → 27/09 02:54, 27/09 04:45 → 11:23, 28/09 03:10 → 21:59, 29/09 03:41 →
  30/09 18:30, 01/10 02:56 → 21:03, 05/10 02:44 → 22:25 e 06/10 04:04 → 12/10 21:37. Os dois
  últimos são as entradas corrompidas do json-file (LEIAME da coleta de 12/10). Nenhuma
  partida arquivada cai num buraco: a numeração dos events vai de 58 a 79 sem falha, menos a 62
  e a 77, que batem com as duas sessões curtas sem matchid.
- O "1 overflow só no signon" que a trilha registra no G7 do B1.4b (partida 27, matchid 64)
  é o aviso S2 de 103 ms das 20:52:10: não houve queda.
- Resultado: **2 overflows no signon em 25 entradas novas, ou 2 em 22 sessões de jogo.** O
  Victor caiu na entrada nas partidas 60 e 75 e voltou nas duas.

### Hipóteses

#### H1. Exec do `warmup.cfg` da MatchZy (o confundidor 1 da trilha)

A trilha e o handoff de 26/09 atribuem a queda das 16:04 ao `warmup.cfg` que a MatchZy executa
quando detecta o primeiro jogador. Junto vinha uma sub-hipótese do B1.1: o offset de `Respawn`
da CSSharp 1.0.373.

- A favor: em 26/09 a queda caiu entre o `[StartWarmup] ... Executing Warmup CFG` (16:04:01,880)
  e o `execing MatchZy/warmup.cfg` (16:04:01,908) (`b1.3r/docker-logs-antes.txt:11980-12027`).
- Contra:
  - Em 04/10 a queda veio a +0,26 s do FULL, antes de qualquer `[FULL CONNECT]` ou
    `[StartWarmup]` para aquela conexão. O `warmup.cfg` do mapa já tinha rodado às 16:49:29,
    6 s antes de o jogador conectar, sem ninguém no servidor
    (`docker-logs-antes-do-start.txt:13920-13921`).
  - Em 26/09 o tempo foi gasto antes do cfg: o frame de 256 ms engloba o handler de FULL
    CONNECT, com as linhas a 70 ms de intervalo, e o `execing` saiu no frame seguinte (E5).
  - Nas outras 23 entradas novas, o mesmo FULL CONNECT, `StartWarmup` e `execing warmup.cfg`
    rodaram sem queda, com 0 a 51 ms do FULL CONNECT ao StartWarmup.
  - A reentrada de 04/10, no mesmo processo e no mesmo mapa, executou o `warmup.cfg` às
    16:50:54,759 num frame de 15 ms de sim (`docker-logs-antes-do-start.txt:14030-14040`).
  - Offset de `Respawn`: a CSSharp é a 1.0.375 desde 27/09, e o overflow voltou em 04/10. A
    queda de 04/10 nem passou pela MatchZy, então não houve `SwitchTeam` + `Respawn`.
- **Veredito: não sustentada como causa.** O `warmup.cfg` não é caro. Em 26/09 foi o handler de
  FULL CONNECT da MatchZy que ficou lento, e lento de forma anormal (os mesmos passos levam
  até 51 ms em todas as outras entradas). Isso aponta para o processo todo lento naquele
  instante, não para o cfg. O processo tinha 3 min e subira depois do segfault do VPK das
  16:01:12 (`b1.3r/docker-logs-antes.txt:11415-11421`). Por que estava lento, as cópias não
  dizem.

#### H2. Carga do host (o PC do Victor com agentes e a suíte rodando)

- A favor:
  - O motivo da queda, escrito pelo próprio engine, é tempo de CPU de relógio (`excessive CPU
    usage`). O container roda no Docker Desktop do Windows e divide os núcleos com tudo o que
    roda no PC. Carga externa alonga o tick, e com ele o S2 (H, mecanismo plausível).
  - Em 04/10 havia agentes trabalhando: o merge do T1.1 às 16:36Z e o commit do T1.3b às
    16:41:49Z, 7 min antes da queda; o T1.3c seguiu até 17:27Z. A nota do card diz que rodavam
    a suíte na mesma máquina. Isso é relato do PM: nenhuma cópia registra o pytest.
  - Em 04/10, 3,5 s antes da conexão, saiu um `SteamNetworkingSockets lock held for 8.1ms ...
    This is usually a symptom of a general performance problem such as thread starvation`
    (`docker-logs-antes-do-start.txt:13928-13929`). Nos 30 s antes do FULL, 9 frames tiveram
    `elapsed` mais de 20 ms acima do `sim time`, o maior número entre as entradas. Só que a
    maioria é o loadmatch e a troca de mapa de 13 s antes.
- Contra:
  - A reentrada às 16:50:54, 79 s depois, no mesmo processo e com os mesmos agentes no
    PC, custou 15 ms. A entrada de 17:19, com commits a +4 e +7 min, custou 27 ms.
  - O snapshot da captura sai a cada 640 ticks (10 s) mesmo com o servidor vazio. Nos 10 min
    antes do FULL de 04/10, o intervalo entre snapshots desviou no máximo 3,6 ms de 10 s (média
    0,53 ms). É o mesmo das horas ociosas de 03/10 e 04/10, com máximo de 1,2 a 4,4 ms por
    bloco de 10 min. Na escala de 10 s, não há fome de CPU sustentada antes da queda.
  - O aviso de `lock held` não prevê a queda. As entradas de 30/09 20:37 (9 avisos, até 196 ms)
    e de 04/10 17:19 (10 avisos, até 192 ms) não caíram; a de 26/09 16:04 não teve nenhum.
  - Houve commits perto de entradas baratas (27/09 02:55, com 7 commits e 24 ms; 27/09 22:00,
    com 5 e 24 ms) e nenhum perto de entradas caras (27/09 20:52 e 28/09 22:00).
- **Veredito: não demonstrada e não descartada.** Os logs não separam carga do host de custo do
  próprio processo, porque o `sim time` também é relógio. Pode ser o agravante que levou o tick
  de 04/10 de uns 110 a 160 ms (o das outras entradas frias) a 295 ms. Medir é a seção
  seguinte.

#### H3. Entrada fria: o tick da entrada fica caro depois de horas sem humano

Hipótese nova, tirada da tabela.

- A favor:
  - As 5 entradas com 1,6 h ou mais de servidor sem humano custaram 110, 159, 128, 112 e 295 ms.
    A sexta, com 1,45 h, custou 28 ms. Das 19 entradas a menos de 0,4 h de um boot ou de outra
    partida (reentradas incluídas), só 2 passaram de 100 ms: 23/09, com plugins quebrados, e
    26/09 16:04, 3 min depois de um segfault. Em tabela 2×2, 5 de 6 contra 2 de 19 (Fisher
    unilateral, p ≈ 0,002).
  - O frame do loadmatch também foi o mais lento depois de longo ócio. Ele costuma ter de 200
    a 250 ms de `elapsed` com uns 3 ms de sim. Foram 908 ms em 03/10 02:06 (22,6 h vazio) e
    611 ms em 04/10 16:49 (37,6 h), este com 93 ms de sim
    (`docker-logs-antes-do-start.txt:13779`).
  - As duas reentradas, logo depois das quedas, foram baratas: 15 e 19 ms.
- Contra:
  - A amostra é pequena, e "sem humano" se confunde com a idade do processo e com o que
    rodava no PC durante o ócio.
  - Não explica o 26/09: lá a queda foi no handler de FULL CONNECT, com o processo de 3 min.
  - O loadmatch lento não é exclusivo do ócio: 656 ms em 28/09 21:59, logo depois de um boot,
    e 902 e 1088 ms em 23/09 e 25/09, na época dos plugins quebrados.
  - Não é a hibernação do servidor vazio: durante as 37 h antes de 04/10, o snapshot saiu a
    cada 10 s, ou seja, o servidor seguiu em tick. Nenhuma linha `hibernat` nas cópias.
- Mecanismos possíveis, todos H, sem evidência nas cópias: memória do processo paginada ou
  comprimida pelo WSL2 ou pelo Windows durante o ócio; cache de disco do host esvaziado por
  outra atividade (os agentes); estado do .NET da CSSharp (JIT em camadas, GC). O primeiro e o
  segundo ligam H3 a H2: a carga do PC durante o ócio, e não na hora da entrada, esfriaria o
  servidor.
- **Veredito: o padrão mais forte nos dados, com mecanismo em aberto.** Ela tem o mesmo
  formato do H3 do [B1.12](../runbooks/b1.12-segfault-troca-de-mapa-md3.md), o acúmulo no
  processo.

#### Descartadas como causa necessária

- **Plugins de bot:** houve overflow com a suíte mascarada (26/09, época 0) e com a suíte
  ligada (04/10, 7 plugins). As entradas caras aparecem nas duas. Em 23/09 os plugins quebrados
  pelo update agravaram muito (598 ms e `Long frame` de 885 ms, no transcript), mas foram
  mascarados e depois religados por versões que carregam.
- **O plugin de captura:** o overflow em jogo de 23/09 22:08 foi dele. A versão 0.3.1 gravava
  no bind mount do Windows na thread do jogo, e a escrita foi de 0,9 a 8,2 ms com pico de 99,9
  (transcript, linhas 1932-1969). A 0.4.0 tirou a escrita da thread. Hoje o snapshot custa
  0,003 ms com o servidor vazio.
- **Rede:** E3.

### O que medir a mais (nada disto foi executado)

1. **Custo da entrada no `evidencia_partida.py`.** O dado já está no log, então custa zero de
   coleta. Para cada `SPAWN -> FULL`: o primeiro `Long frame` depois do FULL, o S2, o S1 com o
   Δ, o tempo sem humano e a idade do processo. A ferramenta já separa signon de jogo
   (FULL + 60 s, `tools/evidencia_partida.py:79`). Ela não mede o custo e conta o aviso S2 como
   overflow (`:164-170`).
2. **Carga do host durante a partida.** O `jogavel.py coletar` roda depois da partida e só
   guarda logs, config-hash, HEAD e sha256 (`tools/jogavel.py:1321-1349`), então não tem como
   ver a carga da hora da entrada. É preciso um amostrador que rode enquanto o Victor joga e
   cujo arquivo o `coletar` copie. Ele grava, a cada 5 s: CPU total, CPU do processo do WSL2
   (`vmmem`), memória disponível e fila do processador. O `typeperf` do Windows faz isso sem
   dependência nova (sem `pip`).
3. **Atividade dos agentes com hora.** Início e fim de cada pytest e de cada sessão de dev ou
   QA, num arquivo em `logs/`. Hoje só os commits servem de indício, e a nota do card sobre a
   suíte de 04/10 é relato.
4. **Contadores de dentro do container, na coleta** (só leitura, preflight 0, como o
   `sha256sum`): `/proc/loadavg`, `/proc/pressure/cpu` e `/proc/pressure/memory` (o PSI, se o
   kernel do WSL2 expuser), e `pgmajfault` e `pswpin` de `/proc/vmstat`. São cumulativos: dizem
   se houve falta de página ou de CPU desde o boot, não na hora da entrada. Com o amostrador do
   item 2 dá para cruzar.
5. **Desenho do experimento natural, sem janela.** Separe cada entrada em 4 células: sem humano
   há 1,5 h ou mais, ou não; agente rodando no PC, ou não. Com 10 a 15 mapas por semana e uma
   entrada por partida, umas 3 a 4 semanas dão 5 entradas ou mais por célula. Leitura: se o
   custo alto aparece só nas frias, com ou sem agente, é H3; se só com agente, é H2; se nas
   frias com agente, são as duas. Um teste controlado (entrada fria com e sem carga sintética)
   seria vivo: só por card próprio, em janela.

### Contorno

- **Para o Victor:** se o CS2 mostrar "Overflow error" ao entrar, **conecte de novo.** Nas 2
  vezes, a segunda entrada passou (79 s e 11 min depois), e a partida seguiu normalmente. Nada no
  servidor precisa ser mexido.
- **Para quem avalia candidato:** overflow no signon não é regressão do plugin religado. Só
  conta o que acontece com o jogador dentro, depois de FULL + 60 s (trilha, confundidor 1; o
  `evidencia_partida.py` já separa). O confundidor 1 continua valendo como regra de veredito.
  A explicação dele (o `warmup.cfg`) é a que caiu (H1).
- **Para os agentes:** até a medição, não há base para parar de trabalhar enquanto o Victor
  joga (a decisão de 12/10 segue). Também não há base para dizer que a carga não importa.

### Próximos cards (propostas para o PM, nenhum é degrau)

1. **Custo da entrada no `evidencia_partida.py`** (Offline, ferramenta, sem caminho de jogo;
   depende do 40). Critério: nas cópias de 26/09 e 04/10, o relatório traz para cada entrada o
   custo do tick, o S2, o S1 com Δ e o tempo sem humano, batendo com a tabela acima (04/10:
   295 ms, 264 ms, +0,26 s, 37,6 h; 26/09: 134 ms e S1 a +1,13 s). O aviso S2 deixa de contar
   como overflow.
2. **Carga do host e atividade dos agentes registradas para a coleta** (ferramenta, sem
   caminho de jogo). Amostrador com `typeperf` (item 2), marca de pytest e de sessão de agente
   (item 3) e o `coletar` copiando a fatia desde o `StartedAt` mais os contadores do item 4.
   Critério: numa partida, a coleta traz a série de carga que cobre o FULL do Victor e diz se
   algum pytest rodava no momento.
3. **Mudança de cfg: não há.** Nenhuma linha de cfg ficou implicada, o `warmup.cfg` inclusive.
   Card degrau de cfg só se a medição apontar uma (por exemplo, o limite do E2 for de uma cvar
   e a decisão for subir esse limite). Hoje isso seria chute: o nome da cvar não está em
   nenhuma cópia.

### Lacunas de evidência

1. **19/09 a 23/09 21:41Z sem `docker logs`:** 14 partidas (44 a 57) sem como contar. O espelho
   de 19/09 é filtrado e não traz signon. Os relatos de 23/09 vêm de digest de transcript, não
   de log.
2. **Carga do host nunca medida:** nem CPU, nem memória, nem processos, em nenhuma partida. A
   presença de agentes vem só de commits, e a da suíte em 04/10, só do relato no card.
3. **Os comandos `StringCmd` que o cliente manda no FULL** e quem os trata (engine, MatchZy,
   CSSharp ou plugins) não aparecem no log.
4. **O limite da queda** está entre 152 e 237 ms. A cvar que o define, se houver, não foi
   identificada: não há fonte do engine nas cópias.
5. **26/09 16:04:** por que o handler de FULL CONNECT da MatchZy ficou de 4 a 40 vezes mais
   lento que o normal. O processo tinha 3 min, depois do segfault do VPK; carga do host ou
   estado do disco são H sem dado.
6. **O VPK antes de 26/09 16:01Z** não está registrado: o Low é provável pelo transcript.
7. **As sessões sem matchid** (27/09 12:50 e 05/10 22:26) foram ligadas às partidas 62 e 77 só
   pela falha na numeração dos events. O banco não foi lido.
8. **A cópia de 12/10 é reconstruída** com `--tail`. Ela perde uma linha por fronteira
   corrompida, e linhas com o mesmo carimbo podem estar fora de ordem (LEIAME). Nenhuma entrada
   do humano cai numa fronteira.
