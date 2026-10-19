---
tipo: arquitetura
status: rascunho
fontes:
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:52 (ModuleVersion 0.4.0)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:79-144 (Load, ResetForNewMap e truncamento)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:251-337 (fila, thread de escrita e UTF8Encoding sem BOM)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:360-712 (os onze tipos)"
  - "parser.py:1037-1055 (leitura em utf-8-sig)"
  - "parser.py:1103-1199 (despacho por type)"
  - "watcher.py:502-587 (arquivamento e colisão, P1.1a e P1.1b)"
  - "start_match.py:52-120 (órfão real, P1.1, e a morte de pós-jogo, P1.1d)"
  - "start_match.py:823-831"
  - "tools/evidencia_partida.py:86-89 (TIPOS_DA_CAUDA)"
  - "tools/evidencia_partida.py:523-556 (analisar_current e a morte pelo world)"
  - "tools/jogavel.py:93-104 (partida em curso)"
  - "tests/test_orphan_e_log.py:57-248"
  - "tests/test_evidencia_partida.py:969-999"
  - "tools/anonimizar_fixtures.py:9-14 (as três fixtures de captura)"
  - "tests/fixtures/captura/orfao_falso_83.jsonl:1-16 (cauda da partida 83, P1.1d)"
  - "tests/fixtures/captura/orfao_falso_87.jsonl:1-15 (cauda da partida 87, P1.1d)"
  - "commit 193cd6c"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (cards K1.5, P1.1, P1.1a, P1.10 e S7.1 a S7.3)"
  - "backup:temp-artifacts/eb5adec0/audit/dead_captura.json (captura-29: gerações e formato)"
  - "backup:temp-artifacts/eb5adec0/audit/harness.json (findings[6]: tipos por geração e 14 arquivos com BOM)"
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[4] item 10 e findings[6])"
atualizado: 2026-10-19
---

# Contrato do events JSONL

O plugin de captura `Cs2TrackerEvents` (CounterStrikeSharp, hoje v0.4.0) grava a partida num
JSONL, e o Python lê esse arquivo para arquivar, ingerir e julgar a partida. O contrato entre
os dois é implícito: nenhuma linha carrega versão ou schema, e o formato existe só no C#, nos
ramos do `parser.py` e nas fixtures (auditoria, captura-29). Esta nota descreve o que o código
faz hoje. A fonte da verdade é o código: onde esta nota e ele divergirem, vale o código, e a
nota se corrige.

Os termos (arquivamento, cauda, órfão, map index) estão no [glossário](../dominio/glossario.md).
As pegadinhas do engine que moldaram o formato estão em
[captura-e-eventos](../armadilhas/captura-e-eventos.md) (itens 38 a 46): aqui só o link.
Fora da seção 4, `:N` sozinho é linha do último arquivo citado por inteiro.

## 1. Quem escreve e quem lê

| Quem | O que faz com o arquivo | Fonte |
|---|---|---|
| Plugin `Cs2TrackerEvents` | único escritor; grava `current.jsonl` em append, uma linha por evento | `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:251-337` |
| `watcher.py` | arquiva: renomeia `current.jsonl` no fim do mapa e manda ingerir | `watcher.py:502-587` |
| `parser.store_match_from_events` | ingere no SQLite | `parser.py:992-1199` |
| `start_match.preservar_orfao` | antes da partida, preserva o `current.jsonl` com round real | `start_match.py:79-106` |
| `tools/evidencia_partida.py` | G7: classifica o `current.jsonl` e os arquivados, sobre cópia | `tools/evidencia_partida.py:465-487` |
| `tools/jogavel.py` | recusa o `voltar` com partida em curso | `tools/jogavel.py:296-322` |
| `tools/preflight.py` | só o mtime do `current.jsonl` (menos de 10 min = Victor jogando) | `tools/preflight.py:317-330` |
| `tools/reingest_events.py` | reingere os arquivados `events_<matchid>_map<N>`, com ou sem `__<utc>` | `tools/reingest_events.py:26-27` |

## 2. A linha

- UTF-8, um objeto JSON por linha, terminada em `\n` (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:306-310`).
- Todo evento tem três campos comuns: `type` (texto), `round_num` (inteiro, de 1 em diante) e
  `tick` (inteiro, `Server.TickCount` no instante do hook).
- Ordem: a de emissão. A thread do jogo serializa e enfileira numa fila FIFO, e uma thread
  própria grava (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:251-293`).
- Só ao vivo. Nada sai no warmup (`IsLive`, `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:160-164`), e todo
  handler, fora o `round_start`, ignora o evento enquanto `round_num` é 0. O `round_start`
  incrementa o contador, que zera a cada mapa (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:116-122`, `:446-449`).
- Leitura tolerante. O parser pula linha vazia, conta e descarta com aviso a linha ilegível
  (`parser.py:1044-1055`) e ignora `type` que não conhece: o laço não tem `else`
  (`parser.py:1103-1199`).

## 3. Gerações

"Geração" é a versão do plugin que gravou o arquivo. Como nenhuma linha diz a versão, a geração
se reconhece pelos tipos e campos presentes e pelo BOM. No disco de 26/09 havia dois formatos:
o da v0.2.0-spike (`events_40` a `events_52`) e o da v0.3 em diante (`events_58` em diante). A
v0.3.1 e a v0.4.0 mudaram só a escrita, não o formato (auditoria, captura-29). O `.cs` entrou no
git num commit só (`commit 193cd6c`, 25/09): o código das gerações antigas não está no repo.

| Geração | O que mudou no formato | BOM | Fixture |
|---|---|---|---|
| v0.2.0-spike | 7 tipos vistos: `round_start`, `round_end`, `round_officially_ended`, `player_death` (sem posição), `player_hurt`, `bomb_planted` e `bomb_defused` (sem `place`) | sim | `tests/fixtures/captura/events_44_map0.jsonl` (mapa inteiro) |
| v0.3.0 | entram `snapshot` (2 Hz, no lugar do laço de 8 Hz da v0.2), `freeze_end`, `round_stats` e `player_blind`; `player_death` ganha `attacker_pos` e `victim_pos` | não | `tests/fixtures/captura/events_59_map0.jsonl` (sem os snapshots, fora um por round) |
| v0.3.x | `bomb_planted` e `bomb_defused` ganham `place`; se entrou na 0.3.0 ou na 0.3.1 não está registrado | não | `events_59_map0.jsonl` |
| v0.3.1 | nenhuma: `StreamWriter` mantido aberto | não | — |
| v0.4.0 (atual) | nenhuma: fila em memória e thread de escrita | não | `tests/fixtures/captura/current.jsonl` (cauda de 03/10) |

Fontes: o desenho em três fontes da v0.3.0 (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:29-47`, `parser.py:1005-1016`),
a contagem de tipos por arquivo (auditoria, harness findings[6]) e as três fixtures, contadas
neste card. Lacuna: a auditoria contou 8 tipos nos arquivos até o `events_52`, e a fixture da
v0.2 tem 7, sem nenhum de amostragem, embora a v0.2 tivesse um laço de 8 Hz. O oitavo tipo não
foi identificado. O parser lê as duas gerações pela ausência de campo (`e.get`) e por um fallback
de compatibilidade: o `site` 0/1 do `_bomb_site` (`parser.py:251-267`). O fallback de
`equip_round_start` (`parser.py:1133`) não é de geração: a v0.3 manda `equip_freeze_end` 0 ou
nulo em ~90 % das entradas (auditoria, captura-29).

Previstas, ainda não implementadas: a v0.4.1 (P1.10), que renomeia para `orphan_<utc>` no
`Load` e no `OnMapStart` em vez de truncar, e a v1 (S7.1 a S7.3), com JSON Schema, `capture_id`
único e arquivo `.part` renomeado no fim do mapa.

## 4. Tipos de evento

Além dos campos comuns. "Lado" é `"t"`, `"ct"` ou `""` (sem time). `steamid` é o SteamID64 em
texto decimal, e `null` para bot ou sem jogador (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:179-183`). Nome é o
nick no jogo, e `""` sem jogador. Posição é `{x, y, z, place}` (x/y/z com uma casa, `place` é o
callout) ou `null` sem pawn válido (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:191-204`).

| `type` | Quando sai | Campos | Geração | O que o parser faz |
|---|---|---|---|---|
| `round_start` | `EventRoundStart` ao vivo; incrementa `round_num` (`:446-461`) | `human_side`: lado do primeiro jogador que não é bot | v0.2 | `start_tick`, `human_side` |
| `freeze_end` | fim do freezetime (`:468-504`) | `players[]`, abaixo | v0.3.0 | `freeze_end_tick` e loadout; `money` não é lido |
| `round_end` | `EventRoundEnd` (`:506-519`) | `winner` (lado); `reason`: `bomb_exploded`, `bomb_defused`, `t_killed` (CT venceu), `ct_killed` (TR venceu), `round_draw`, `terrorists_surrender`, `cts_surrender` ou o nome cru do enum (a fixture tem `TargetSaved`) (`:206-216`) | v0.2 | `winner_side`, `reason`, `end_tick` |
| `round_stats` | `EventRoundOfficiallyEnded`, antes do próximo (`:531-597`) | `players[]`, abaixo | v0.3.0 | delta por round (`parser.py:961-989`) |
| `round_officially_ended` | mesmo hook, logo depois (`:599-604`) | só os comuns | v0.2 | ignorado |
| `player_death` | `EventPlayerDeath` (`:608-632`) | `attacker_name`, `attacker_steamid`, `attacker_side`, `victim_name`, `victim_steamid`, `victim_side`, `weapon` (texto, `"world"` sem atacante), `headshot` (bool), `distance` (número), `attacker_pos` e `victim_pos` (posição, v0.3.0) | v0.2 | `kills` e posição de origem "evento" |
| `player_hurt` | `EventPlayerHurt` (`:634-652`) | `attacker_name`, `attacker_steamid`, `victim_name`, `victim_steamid`, `weapon`, `hitgroup` (inteiro), `dmg_health` (dano bruto, item 40), `dmg_armor`; sem lado | v0.2 | `damages`, depois cortado (`clamp_damage_health`) |
| `player_blind` | `EventPlayerBlind` (`:659-674`) | `attacker_name`, `attacker_side`, `victim_name`, `victim_side`, `duration` (segundos, duas casas); sem steamid | v0.3.0 | `player_blinds` |
| `bomb_planted` | `EventBombPlanted` (`:676-696`) | `player_name`, `steamid`, `site` (índice de entidade, item 44), `place` (`BombsiteA`/`B`, v0.3+) | v0.2 | `bomb_plant`, `bomb_site` |
| `bomb_defused` | `EventBombDefused` (`:698-712`) | os mesmos do `bomb_planted` | v0.2 | ignorado |
| `snapshot` | a cada 32 tiques (~2 Hz), ao vivo e com `round_num` > 0 (`:360-409`) | `players[]` com chaves curtas, abaixo | v0.3.0 | `player_positions` de origem "amostra" |

Na tabela e na lista abaixo, `:N` é linha de `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs`.

`players[]` de cada tipo:

- `snapshot` (`:379-389`): `n` nome, `b` é bot, `s` lado, `x`/`y`/`z`, `h` vida, `p_` callout.
  As chaves são curtas de propósito: são dezenas de milhares de linhas por partida.
- `freeze_end` (`:477-493`): `name`, `is_bot`, `side`, `equip_freeze_end` e `equip_round_start`
  (inteiro ou `null`), `armor`, `has_helmet`, `has_defuser` (bool), `money` (inteiro ou `null`).
- `round_stats` (`:542-588`): `name`, `is_bot`, `side` e os contadores de `CSMatchStats_t`,
  ACUMULADOS na partida (os 30 de `parser.py:927-937`, de `kills` a `kill_reward`), mais `money` e
  `cash_spent_round`, que já são do round (`parser.py:939-941`).

O `freeze_end` e o `round_stats` trazem também o bot do GOTV (nome do servidor terminado em "CSTV", sem lado e zerado); o `snapshot` não, porque pula quem não tem pawn com posição (`:373-377`), e o bot do GOTV não tem pawn (`parser.py:947-949`). Na fixture `events_59_map0.jsonl`: 14 de 14 `freeze_end` e 13 de 13 `round_stats` com ele, 0 de 15 `snapshot`. O parser o descarta nos três (`_participa`, item 45).

## 5. BOM

- O escritor atual não grava BOM: o `StreamWriter` usa `UTF8Encoding(false)`
  (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:335`), e o truncamento grava texto vazio (`:137`).
- Arquivos da v0.2.0-spike começam com o BOM do UTF-8 (`EF BB BF`): em 26/09, 14 dos 18 JSONL da
  pasta, e nenhum da v0.3 em diante (auditoria, harness findings[6]). A fixture
  `events_44_map0.jsonl` guarda o BOM de propósito (`tools/anonimizar_fixtures.py:9`); as outras
  duas não têm. Por que a v0.2 gravava BOM não dá para conferir: o código dela não está no git.
- O BOM fica colado na linha 1, que é o `round_start` do round 1. Lido como `utf-8` puro, essa
  linha caía no `JSONDecodeError`, calado por um `continue`: o round 1 de toda partida perdia
  `start_tick` e `human_side` ([M0.5, F0.5.0](../features/M0.5-placar.md)).
- Regra: todo leitor abre com `utf-8-sig` (`parser.py:1044`, `start_match.py:68`,
  `tools/evidencia_partida.py:430`, `tools/live_watch.py:101`, `tools/anonimizar_fixtures.py:120`).
  O `tools/jogavel.py:306` lê bytes, e o `json.loads` reconhece o BOM sozinho. O BOM só existe no
  byte 0.
- O comentário de `parser.py:1040-1043` diz que o plugin escreve com BOM: isso só valia para a
  v0.2 (auditoria, infra findings[4], item 10). A correção é da poda, não deste card.

## 6. Arquivos e nomes

Todos na pasta da captura: `game/csgo/events-live/` no container, `docker/events-live/` no host
(`docker-compose.yml:188`, `config.py:43`, `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:85`). A pasta real é zona
proibida para agentes: os arquivos têm SteamID64 e nicks reais.

| Arquivo | Quem cria | Quando |
|---|---|---|
| `current.jsonl` | plugin | truncado (vazio) no `Load` e em todo `OnMapStart` (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:107-114`, `:137`; item 46); recriado em append quando some (`:324-337`) |
| `events_<matchid>_map<N>.jsonl` (`__<utc>`, `-2`… na colisão) | `watcher.py`, por rename do `current.jsonl` | na linha `WritePlayerStatsToCsv` da MatchZy, fim do mapa (`watcher.py:412-427`, `:530-562`) |
| `orphan_<AAAAMMDDTHHMMSSZ>.jsonl` (`-2`, `-3`… se o nome existe) | `start_match.preservar_orfao`, por rename, com cópia de reserva | no `run_match`, antes do `compose_up` e do `loadmatch`, se houver órfão real (seção 7) (`start_match.py:79-106`, `:823-831`) |

- `<matchid>` é o id da partida na MatchZy. `<N>` é o número do mapa que a MatchZy dá
  (`currentMapNumber`, `match_data_map<N>`), de base 0: o mapa 1 de uma MD3 é `map0`. Sem
  número no log, o watcher usa 0 (`watcher.py:516-519`).
- O nome sem extensão é o `demo_name`, chave única de `matches` (`parser.py:67`, `:1019`).
  `demo_name` já gravado faz o parser pular a ingestão (`parser.py:1024-1032`).
- Colisão (P1.1a, P1.1b): se o nome já existe em disco ou no banco e o `current.jsonl` tem uma
  partida, ela vira `events_<matchid>_map<N>__<AAAAMMDDTHHMMSSZ>` (`-2`, `-3`… no mesmo segundo),
  e o antigo fica intacto (`watcher.py:528-556`). Arquivo antigo fora do banco ganha `[AVISO]` no
  log da partida. Sem nenhum `round_end`, o `current.jsonl` não é partida (é a cauda de um fim
  repetido): vira `sem_round_end_<nome>__<utc>.jsonl`, com `[AVISO]` e sem linha no banco.
  O `evidencia_partida` casa a partida do log com o nome sufixado mais novo
  (`tools/evidencia_partida.py:718-750`), e o `reingest_events` reingere o sufixado
  (`tools/reingest_events.py:26-27`). A partida sem colisão segue sem sufixo e sem aviso.
- `orphan_*` e `sem_round_end_*` não são ingeridos por ninguém de forma automática: o watcher
  só olha o nome do arquivado e o `reingest_events` só casa `events_*`.
- Num leitor do Windows, o `current.jsonl` aberto impede o rename do watcher
  (`tools/evidencia_partida.py:711-715`). Leia sempre uma cópia.

## 7. Cauda normal e órfão: a regra do round

**Arquivamento** é o rename do watcher. Por construção, o `current.jsonl` só tem o que o plugin
gravou depois do último arquivamento ou do último truncamento.

**Cauda normal** é o que o plugin ainda grava depois do arquivamento numa partida que terminou:
os `snapshot` de 2 Hz, que seguem até a troca de mapa, e o `round_stats` e o
`round_officially_ended` do último round, que saem depois da linha do CSV da MatchZy. A fixture
`tests/fixtures/captura/current.jsonl` é uma cauda real: 44 snapshots, 1 `round_stats` e 1
`round_officially_ended`. Por isso o arquivado não tem o `round_stats` do último round
(`tools/evidencia_partida.py:508-513`).

**Órfão real** é a regra do round do P1.1: o `current.jsonl` com pelo menos um `round_start`,
`player_death` ou `player_hurt` (`EVENTOS_DE_PARTIDA`, `start_match.py:52-60`). Basta um. Ele é a
partida que caiu antes do arquivamento (matchid 75, 04/10: segfault na troca para o mapa 2) e
vira `orphan_<utc>.jsonl`. A exceção é a **morte de pós-jogo** do P1.1d: o `player_death` pelo
`world` com atacante = vítima (mesmo SteamID64, não vazio) não conta, e sem `round_start` no
arquivo ele é cauda (`morte_de_pos_jogo`, `start_match.py:67-90`). Tudo o mais é cauda: fica
para o plugin truncar, como antes. Os testes usam a cauda real do T1.3 e os dois órfãos falsos
reais, anonimizados (`tests/test_orphan_e_log.py:57-248`).

Quatro leitores classificam o `current.jsonl`, e cada um com a própria regra:

| Leitor | Conta como partida | Conta como cauda ou ignora |
|---|---|---|
| `start_match.preservar_orfao` (P1.1, P1.1d) | `round_start`, `player_hurt` e `player_death` fora a morte de pós-jogo | todo o resto, inclusive `round_end`, `freeze_end`, `player_blind` e bomba sozinhos (`tests/test_orphan_e_log.py:90-97`); sem `round_start`, a morte de pós-jogo (`start_match.py:67-90`) |
| `evidencia_partida.analisar_current` (G7) | todo tipo fora da cauda: `com_rounds` | `snapshot`, `round_stats`, `round_officially_ended`; sem `round_start`, também a morte de pós-jogo (`tools/evidencia_partida.py:101`, `:523-556`) |
| `jogavel.py`, partida em curso | qualquer tipo fora o `snapshot` há menos de 2 min (idade = mtime + snapshots depois dele ÷ 2) | `snapshot` (`tools/jogavel.py:93-104`, `:296-322`) |
| `preflight.py` | arquivo mexido há menos de 10 min | — (`tools/preflight.py:317-330`) |

Com `com_rounds`, o `evidencia_partida` separa a **partida abandonada** (o log tem uma partida
sem fim: SEM EVIDÊNCIA) da falha de arquivamento (todas terminaram: RUIM)
(`tools/evidencia_partida.py:874-889`).

### A morte pelo `world` sem `round_start` (resolvido no P1.1d)

Ao sair na tela final, o humano morre pelo `world` (atacante = vítima, mesmo SteamID64), e esse
`player_death` cai na cauda (partida 27, 27/09). O `evidencia_partida` sempre a tratou como
cauda normal quando não há `round_start` no arquivo (`tools/evidencia_partida.py:523-556`;
`tests/test_evidencia_partida.py:969-999`). O `start_match` do P1.1 contava qualquer
`player_death` e preservava esse arquivo como `orphan_*`: órfão falso, nada perdido, um arquivo
sobrando. Aconteceu de verdade nas caudas das partidas 83 (`orphan_20261015T164958Z`, round 17)
e 87 (`orphan_20261019T185248Z`, round 25), cada uma com snapshots, 1 `round_stats`, 1
`round_officially_ended` e essa morte; as duas, anonimizadas, são as fixtures
`tests/fixtures/captura/orfao_falso_83.jsonl` e `orfao_falso_87.jsonl`.

Desde o P1.1d o `start_match` segue a mesma regra. Ela tem duas implementações de propósito,
`start_match.morte_de_pos_jogo` e `evidencia_partida._morte_de_pos_jogo`: a ferramenta do G7
não importa o caminho de jogo (que lê o `.env` ao importar o `config`), e o caminho de jogo não
depende de um arquivo de fora do protocolo 1. O que as mantém iguais é o teste
`test_preservar_orfao_concorda_com_analisar_current` (`tests/test_orphan_e_log.py:208-248`), que
roda os dois leitores sobre a cauda real do T1.3 com cada combinação de `round_start`, dano,
morte de round, morte de pós-jogo e as duas quase-mortes de pós-jogo (pelo `world` de outro
SteamID64; suicídio por granada), e sobre os arquivos reais. A regra não olha quem morreu: o
`world` com atacante = vítima conta mesmo sendo outro SteamID64 (a partida 44 tem uma assim no
round 2, que só vira órfão com o `round_start` dela).

A recíproca também existe só no código: `round_end`, `freeze_end`, `player_blind` ou bomba
sozinhos na cauda são cauda para o `start_match` e `com_rounds` para o `evidencia_partida`. Não
há caso real disso nas caudas da fixture, e ela fica fora do domínio do teste de concordância.

## 8. O que o contrato não garante

- Versão, schema, mapa, matchid e placar não estão no arquivo. Mapa, matchid e número do mapa
  vêm do log da MatchZy e do `match_config.json` (`watcher.py:433-487`).
- `round_num` não é o round oficial: conta todo round ao vivo, inclusive o round fantasma e o
  reiniciado ([matchzy](../armadilhas/matchzy.md), item 31; captura, item 39), e recomeça a cada mapa.
- `human_side` às vezes vem vazio no round 1; o parser infere pela primeira kill
  (`parser.py:1201-1212`).
- Identidade: só `player_death`, `player_hurt` e bomba trazem steamid. Nos demais, o humano é
  achado por nome e `is_bot` (`parser.py:279-292`).
- Perda em crash: a fila é memória. O que não foi drenado quando o processo cai se perde; só o
  `Unload` drena (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:714-726`).
- Fila cheia (20 000 linhas): descarta linha de qualquer tipo, não só snapshot, e avisa uma vez
  (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:255-267`).
- Hipótese, lida no código e não vista ao vivo: se o snapshot lançar exceção, o handler zera o
  contador de round (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:415-421`). O próximo `round_start` volta a
  contar do 1 no mesmo arquivo, e o snapshot volta junto, apesar do comentário "amostragem
  desligada".
- Hipótese: o `Writer()` confere a existência do `current.jsonl` uma vez por lote
  (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:331`). Um lote que cruze o rename do watcher pode gravar linhas
  no arquivo já arquivado.
- `tick` vale para ordenar dentro do arquivo e casar kill com posição pelo mesmo tique. Se ele
  é monotônico entre mapas e boots não foi verificado.
- Campos instáveis: `equip_freeze_end` (0 ou nulo na maioria), `site` (índice de entidade, use
  `place`), `dmg_health` (bruto) e `reason` (pode vir o nome cru do enum).
- Lidos por ninguém na ingestão: `round_officially_ended`, `bomb_defused`, o `money` do
  `freeze_end` e quem plantou a bomba.
