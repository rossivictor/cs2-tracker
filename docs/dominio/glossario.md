---
tipo: dominio
status: vigente
fontes:
  - "AGENTS.md:9-15 (jogável, trilho único, VPK)"
  - "AGENTS.md:47-55 (janela)"
  - "AGENTS.md:57-65 (preflight e coleta)"
  - "AGENTS.md:81-87 (caminho de jogo e degrau)"
  - "AGENTS.md:121-126 (gates, candidato e jogável)"
  - "docs/agents/sprints.md:24 (trilho e pista paralela)"
  - "docs/adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md:45-52 (camadas do produto)"
  - "docs/adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md:76 (Camada 1/2 tem dois sentidos)"
  - "start_match.py:327-340 (camadas da proteção de round)"
  - "start_match.py:52-59 (órfão real)"
  - "tools/evidencia_partida.py:86-89 (cauda)"
  - "tools/jogavel.py:1668-1705 (snapshot do volume)"
  - "docs/runbooks/trilha-de-bots.md:375-380 (épocas)"
  - "watcher.py:178-195 (matchid e número do mapa no log da MatchZy)"
  - "parser.py:65-80 (demo_name e source)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (Q10: partidas órfãs; cards V1.2 a V1.4)"
atualizado: 2026-10-15
---

# Glossário

O vocabulário do cs2-tracker: o do jogo, o da captura e o do programa de saneamento. Cada termo
diz onde vale o sentido dado. Palavra que muda de sentido conforme o arquivo está na primeira
seção. O formato do JSONL em si está no [contrato](../arquitetura/contrato-events-jsonl.md).

## Termos com mais de um sentido

| Termo | Sentido | Onde vale | Fonte |
|---|---|---|---|
| **órfão** | `current.jsonl` com pelo menos um `round_start`, `player_death` ou `player_hurt`: partida que caiu antes do arquivamento. Vira `orphan_<utc>.jsonl` | captura, P1.1 (`start_match`) | `start_match.py:52-59` |
| | **partida órfã**: JSONL capturado que nunca entrou no banco (`events_50_map0.jsonl`, `partida_23set.jsonl`); o destino de cada uma é a Q10 | sprint V1 | `docs/agents/sprints.md:60`; plano, Q10 |
| | **demo órfã**: `.dem` sem ingestão, reprocessada à mão pelo `parser.py` | caminho legado da demo | `parser.py:22` |
| | **lease órfão**: card `Em andamento` sem `Branch` há mais de 2 h | board, tech-manager | `.claude/agents/tech-manager.md:47` |
| | **órfão de versão**: arquivo que só existe na versão antiga de Metamod ou CSSharp e fica no volume depois da extração por cima | servidor, volume | `docs/runbooks/b1.3-cssharp-1.0.375.md:138` |
| | **par órfão**: patch de memória gravado pela metade, que o BotAI desfaz | plugins de bot | `docs/runbooks/trilha-de-bots.md:131-133` |
| | **socket órfão**: socket do Docker Desktop que trava o boot dele | Windows | `docs/armadilhas/windows-e-docker.md:35` |
| **cauda** | **cauda normal**: o que o plugin grava depois do arquivamento numa partida que terminou (`snapshot`, e o `round_stats` e o `round_officially_ended` do último round) | captura, G7 | `tools/evidencia_partida.py:86-89` |
| | os últimos bytes de um arquivo, lidos sem abrir o resto (4 MB do `current.jsonl`; `docker logs --tail`) | `jogavel.py`, `watcher.py` | `tools/jogavel.py:105` |
| **snapshot** | evento `snapshot` do plugin: posição de todos os jogadores a ~2 Hz | captura | `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:350-409` |
| | cópia `.tgz`, só lendo, dos addons, das versões e do `gameinfo.gi` do volume, tirada antes de mexer nele; é a volta pelo caminho 2 | servidor, janela | `tools/jogavel.py:1604-1606`, `:1668-1705` |
| **janela** | **janela de manutenção**: até 45 min abertos pela frase do Victor, só para o papel servidor | servidor | `AGENTS.md:47-55` |
| | **Janela 0**: a primeira, que ensaiou o `jogavel.py` na B0 | B0 | `docs/agents/sprints.md:55` |
| | **janela de dados**: escrita no banco real com o watcher parado e backup antes | V1.4 | `docs/agents/sprints.md:60` |
| | o intervalo entre o fim do mapa e o próximo `OnMapStart`, único momento de arquivar | `watcher.py` | `watcher.py:512-514` |
| **candidato** | merge de um degrau que espera partida, com a tag `candidato-N`; um por vez | programa | `AGENTS.md:126` |
| | `data/candidato.json`, que faz o `run_match` imprimir a linha `[INFO]` do candidato em teste | `start_match` | `start_match.py:135-138` |
| **trilho** | **trilho único**: no máximo uma mudança não validada no caminho de jogo | programa | `AGENTS.md:14` |
| | **trilho do jogo**: a pista das sprints que mexem no caminho de jogo (B0, B1, P1, S1…S7), contra a pista paralela (H1, T1, K1, V1) | `sprints.md` | `docs/agents/sprints.md:24` |
| **trilha de bots** | outra palavra: a B1, que religa os plugins de bot um por partida | B1 | `AGENTS.md:50` |
| **Camada 1, 2, 3** | camadas do modo carreira: 1 orquestração de campeonato, 2 cara de campeonato, 3 bots com personalidade | produto, ADR-0001 | `docs/adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md:47-52` |
| | camadas da proteção contra o round fantasma: 1 reafirmar `bot_quota`, 2 `mp_ignore_round_win_conditions 1`, que precisa ser desligada | `start_match` | `start_match.py:327-340` |
| **fonte** | `matches.source`, de onde veio a partida: `demo`, `csv` ou `events` (plugin) | banco | `parser.py:79` |
| | entrada de `fontes` no frontmatter de uma nota, com gramática própria | KB | `docs/README.md:68-74` |

## Programa e processo

- **Caminho de jogo**: os arquivos que, se mudam, mudam a partida (compose, `pre.sh`, plugins,
  cfg, `start_match`, `wizard_*`, `watcher`, `parser` e os demais da lista). (`AGENTS.md:81-86`)
- **Degrau**: diff no caminho de jogo. Vira candidato e só fecha depois de partida real (G7).
  (`AGENTS.md:87`)
- **Jogável**: o estado em que a `main` joga. A tag `jogavel-AAAA-MM-DD` marca o commit que passou
  pelo G7. **Voltar ao jogável** é o `jogavel.py voltar`, sem agente. (`AGENTS.md:9`, `:103`, `:126`)
- **Válvula vanilla**: voltar à tag sem plugins de bot (`voltar --tag jogavel-2026-09-26`); o
  `jogavel vanilla on|off` é do P1.2. (`docs/runbooks/voltar-ao-jogavel.md:42`)
- **Preflight**: `tools/preflight.py`; 0 livre, 3 Victor jogando, 4 janela aberta. (`AGENTS.md:57-65`)
- **"terminei"**: o Victor fechou a TUI e o jogo; na trilha de bots, libera o próximo passo.
  (`AGENTS.md:50`)
- **Coleta**: o `jogavel.py coletar` depois da partida, só lendo: `docker logs --since`, sha256
  dentro do container e config-hash. Roda com preflight 0, sem janela. (`AGENTS.md:40`)
- **G0 a G7**: os gates. **G6** é o servidor na janela (load, assinaturas, zero segfault, sha256).
  **G7** é a partida real, julgada pelo `evidencia_partida.py` sobre a coleta.
  (`AGENTS.md:123-125`)
- **Época**: estado do servidor que muda o comportamento dos bots (build do CS2, VPK, plugins
  ativos). A fronteira é o `demo_name`; métricas de épocas diferentes não se comparam.
  (`docs/runbooks/trilha-de-bots.md:375-380`)

## Partida e jogo

- **Humano**: o único jogador que não é bot; o resto da partida é bot com perfil de pro.
  (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:455-458`)
- **Série, MD1, MD3, MD5**: partida de 1, 3 ou 5 mapas. `num_maps` no `match_config.json`,
  `series_num_maps` no banco. (`docs/SPEC.md:58`, `watcher.py:443-447`)
- **matchid**: o id inteiro da série na MatchZy. O `match_config.json` não o fixa, e o contador
  é da MatchZy: restaurar snapshot não pode voltá-lo.
  ([matchzy](../armadilhas/matchzy.md), item 17; `watcher.py:184-195`;
  `docs/adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md:61`)
- **Número do mapa** (map index): a posição do mapa na série, de base 0, como a MatchZy dá
  (`currentMapNumber`, `match_data_map<N>`). O mapa 1 de uma MD3 é o `map0`. (`watcher.py:412-427`)
- **demo_name**: chave única de cada mapa no banco. Na captura é `events_<matchid>_map<N>`; o nome
  vem do tempo em que a fonte era a demo. (`parser.py:67`, `watcher.py:523`)
- **round_num**: o contador de rounds ao vivo do plugin, que recomeça a cada mapa; não é o round
  oficial. ([contrato](../arquitetura/contrato-events-jsonl.md), seção 8)
- **Round fantasma**: round encerrado na hora, com bot ainda sem spawn contado como morto.
  ([matchzy](../armadilhas/matchzy.md), item 31; [captura](../armadilhas/captura-e-eventos.md), item 39)
- **Post-mortem**: kills e mortes do humano depois de morrer, quando ele controla um bot; o
  parser as marca e não as conta. ([captura](../armadilhas/captura-e-eventos.md), item 38)
- **Signon**: a entrada do cliente no servidor, de `SIGNONSTATE_*` até `FULL`; o overflow no
  signon derruba o jogador na entrada. (`docs/armadilhas/engine-cs2.md:32`)

## Captura e dados

- **Plugin de captura**: `Cs2TrackerEvents`, plugin CSSharp nosso que grava o JSONL.
  (`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:49-53`)
- **Geração**: a versão do plugin que gravou um JSONL (v0.2.0-spike, v0.3, v0.4.0), reconhecida
  pelos tipos, campos e BOM. ([contrato](../arquitetura/contrato-events-jsonl.md), seção 3)
- **current.jsonl**: o arquivo em que o plugin grava agora, truncado a cada mapa.
- **Arquivamento**: o rename do `current.jsonl` para `events_<matchid>_map<N>.jsonl` pelo watcher,
  no fim do mapa; se o nome já existe em disco ou no banco, desde o P1.1a a partida nova vai
  como `events_<matchid>_map<N>__<utc>.jsonl`, e o arquivo antigo fica intacto. (`watcher.py:523-562`)
- **Partida abandonada**: `current.jsonl` com rounds de uma partida que o log mostra sem fim; no
  G7 é SEM EVIDÊNCIA, não RUIM. (`tools/evidencia_partida.py:874-889`)
- **round_stats**: evento do fim de round com os contadores do engine (`CSMatchStats_t`)
  acumulados na partida; o parser guarda o delta. (`parser.py:961-989`)
- **BOM**: os 3 bytes do UTF-8 no começo dos arquivos da v0.2; todo leitor abre com `utf-8-sig`.
  ([contrato](../arquitetura/contrato-events-jsonl.md), seção 5)

## Servidor e componentes

- **MatchZy**: plugin CSSharp que conduz a partida (`loadmatch`, série, CSV de stats, demos).
  ([versões conhecidas](../runbooks/versoes-conhecidas.md); [armadilhas](../armadilhas/matchzy.md))
- **CSSharp**: CounterStrikeSharp, a camada .NET de plugins do servidor, sobre o Metamod.
- **Metamod**: o carregador de plugins nativos do Source 2, base do CSSharp.
- **GOTV, CSTV, SourceTV**: o espectador de transmissão do servidor (`TV_ENABLE`). Ocupa um slot e
  aparece como jogador sem time: o **bot do GOTV**, que a ingestão descarta.
  (`start_match.py:833-835`; [captura](../armadilhas/captura-e-eventos.md), item 45)
- **Bot profile**: o `botprofile.vpk` com os perfis nomeados dos bots, nas variantes Low, Medium
  e High; hoje Low, trocado só em janela. (`AGENTS.md:15`)
- **RCON**: o console remoto do servidor; só o papel servidor, em janela. (`AGENTS.md:48`)
- **SteamID64**: o id numérico de uma conta Steam. No repo só entra fictício, abaixo de
  76561197960265728 (ex.: 76561190000000001). O SteamID3 (`[U:1:n]`) também é PII.
  ([ADR-0003](../adr/0003-repo-publico.md))
