---
tipo: runbook
status: vigente
fontes:
  - "backup:../2026-10-02/janela0/inventario-matchzy-e-addons.txt (versões, core.json, gamedata.json, MatchZy, BotRandomizer do volume, DLL por pasta, matchzy.db)"
  - "backup:../2026-10-02/janela0/inventario-vpk.txt (overrides/ e gameinfo.gi:17)"
  - "backup:../2026-10-02/janela0/imagem.txt (digest)"
  - "backup:../2026-10-02/janela0/volume-addons-0013.tgz.sha256"
  - "backup:../2026-10-02/janela0/volume-addons-0013.lista.txt (contagens)"
  - "backup:../2026-10-02/janela0/antes-rcon.txt (build, meta list, css_plugins list)"
  - "backup:../2026-10-02/janela0/antes-medicoes.txt (volume, config-hash, compose antes)"
  - "backup:../2026-10-02/janela0/depois-medicoes.txt (compose depois do B0.8)"
  - "backup:../2026-10-02/janela0/final-medicoes.txt"
  - "backup:../2026-10-02/janela0/comparacao-mounts.txt"
  - "backup:../2026-10-02/janela0/sha-comparacao-boot1.txt"
  - "backup:../2026-10-02/janela0/fechamento-sha-container.txt"
  - "backup:../2026-10-02/janela0/fechamento-rcon.txt"
  - "backup:../2026-10-02/janela0/referencia-fechamento-rcon.txt"
  - "backup:../2026-10-02/janela0/voltar.txt"
  - "backup:../2026-10-01/janela0/volume-overrides-2350.tgz.sha256 (cópia dos VPK)"
  - "backup:../2026-09-27/b1.3r/volume-addons-0144.tgz.sha256"
  - "tools/jogavel.py:1219-1229 (itens do snapshot e exclusões da restauração)"
  - "tools/jogavel.py:1287-1324 (tirar_snapshot)"
  - "tools/jogavel.py:1368-1396 (cmd_restaurar)"
  - "watcher.py:476-483 (demo_name events_<matchid>_map<N> e o arquivamento)"
  - "docker-compose.yml:149 (bind do BotAimImprover)"
  - "docker-compose.yml:157 (bind do BotRandomizer)"
  - "docker-compose.yml:196-205 (cs2-data external; B0.8)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:387-416 (snapshot só leitura)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:697-710 (exclude do matchzy.db e do gameinfo.gi)"
  - "docs/runbooks/reconstruir-volume.md:123-133 (o que a semente não tem)"
  - "commit 214b25b"
  - "PR #38"
atualizado: 2026-10-02
---

# Inventário do volume

> **Para quem:** o papel servidor, antes de restaurar addons ou reconstruir o volume; o PM e o
> QA, para conferir uma coleta.
> **Card:** B0.9 (Janela 0), que mediu o volume `cs2-tracker_cs2-data` em 02/10, na janela de
> 00:12 às 00:39.
> **Quando:** ler antes de `tools/jogavel.py restaurar`, antes da
> [reconstrução](reconstruir-volume.md) e antes de mexer em `overrides/` ou no `matchzy.db`.
> **Links:** [versões conhecidas](versoes-conhecidas.md), [reconstruir o volume](reconstruir-volume.md),
> [voltar ao jogável](voltar-ao-jogavel.md), [B1.3r](b1.3-cssharp-1.0.375.md) (snapshot e
> restauração), [smoke só de bots](smoke-partida-de-bots.md).

O volume guarda o que o checkout não tem: o jogo, os addons que a imagem instala, os plugins de
bot instalados à mão em 05/09, as variantes do `botprofile.vpk` e o contador de `matchid` da
MatchZy. Esta nota diz o que havia nele em 02/10 e como restaurar sem descartar partida.

Convenções:

- sha256 abreviado (8 caracteres) nas tabelas; inteiro em [Hashes completos](#hashes-completos).
- **não registrado**: nenhuma fonte guardou o valor. A nota diz de onde ele viria.
- Os valores saem da pasta `C:/Users/Victor/cs2-tracker-backups/2026-10-02/janela0/` e do
  registro `logs/janelas/2026-10-02.md` (checkout principal, fora do git). O inventário dos
  addons foi lido do snapshot `volume-addons-0013.tgz`, sem docker; o de `overrides/`, por um
  container `:ro` do servidor.

## Estado medido em 02/10

| Item | Valor | Fonte |
|---|---|---|
| Volume | `cs2-tracker_cs2-data`, `CreatedAt` 2026-09-03T01:49:52Z (não recriado). Labels: `com.docker.compose.project=cs2-tracker`, `com.docker.compose.volume=cs2-data`, `com.docker.compose.config-hash` `0542d03b…` | `antes-medicoes.txt` = `final-medicoes.txt` |
| Imagem | `xbird/cs2-matchzy`, `sha256:1056e003…` (RepoDigest igual) | `imagem.txt` |
| Build CS2 | 2000922 | `antes-rcon.txt` |
| Metamod | 2.0.0.1469 (`mmsource_version.txt`) | snapshot |
| CounterStrikeSharp | v1.0.375 (`cssharp_version.txt`; `meta list`: `v1.0.375 @ 751eb0c`) | snapshot; `antes-rcon.txt` |
| MatchZy | 0.8.15 (`matchzy_version.txt`) | snapshot |
| Mounts | 15, iguais antes e depois do B0.8 (só muda a grafia da origem do bind, de `/run/desktop/mnt/host/c/...` para `C:\...`) | `comparacao-mounts.txt` |

## Plugins

### CounterStrikeSharp (`addons/counterstrikesharp/plugins/`)

O `css_plugins list` deu 8 LOADED, igual antes da janela, depois do B0.8 e no fechamento. Na
coluna "De onde", **volume** quer dizer que a pasta do volume é a que roda; **bind** quer dizer
que o compose monta a pasta do checkout por cima, e a cópia do volume fica escondida.

| Pasta | Plugin (versão) | De onde | DLL principal no volume |
|---|---|---|---|
| `MatchZy` | MatchZy 0.8.15 | volume (instalado pela imagem) | `MatchZy.dll` `6aab0e76…` |
| `BotBuy` | BotBuyPatch 1.0.12 | volume | `BotBuy.dll` `922c76a6…` |
| `BotState` | Smarter-Bot 1.9.4 | volume | `BotState.dll` `1beb93f8…` |
| `NadeSystem` | NadeSystem 1.2.1 | volume | `NadeSystem.dll` `9e4fc0cf…` |
| `RoundDamageRecap` | RoundDamageRecap 1.2.0 | volume | `RoundDamageRecap.dll` `7075101b…` |
| `Cs2TrackerEvents` | CS2 Tracker Events 0.4.0 | bind (`docker/plugins/Cs2TrackerEvents/`) | pasta vazia no volume |
| `BotAimImprover` | BotAimImprover 2.1.3 | bind (`docker/plugins/BotAimImprover/`, DLL `0749252c…`) | `dfeedab2…` (4 arquivos, escondidos) |
| `BotRandomizer` | BotRandomizer 1.3.2 | bind (`docker/plugins/BotRandomizer/`, DLL `5be52c02…`) | `56a61bea…` (6 arquivos, escondidos) |
| `BotAI` | não carregado: versão não registrada | mascarado (`_empty`) | `BotAI.dll` `389814db…` |
| `BotHiderImpl` | não carregado: versão não registrada | mascarado | `BotHiderImpl.dll` `d53d4b03…` |
| `RayTraceImpl` | não carregado | mascarado | só `RayTraceImpl.dll.disabled` (sha não registrado) |
| `DefaultAgents` | não carregado | — | pasta sem DLL; existe `configs/plugins/DefaultAgents/DefaultAgents.json` |

A versão de um plugin não carregado viria dos metadados da DLL, que a janela não leu.

### Metamod nativo (`addons/`)

`meta list` mostra 3 entradas: CounterStrikeSharp e duas `<NOFILE>`. As duas batem com os dois
"Failed to load plugin" do G6 do boot, `RayTrace` e `BotHider`, mascarados (ruído conhecido,
registro de 02/10). No volume há `addons/RayTrace/` (`RayTrace.so`, `gamedata.json`) e
`addons/BotHider/` (`BotHider.so` e quatro `.json`); sha256 não registrado.

## Configs

| Arquivo (em `addons/counterstrikesharp/`) | sha256 | Observação |
|---|---|---|
| `configs/core.json` | `32869462…` | `"FollowCS2ServerGuidelines": false` (linha 4) |
| `gamedata/gamedata.json` | `7d9bff7a…` | — |

## Deps: o BotRandomizer do volume

O compose monta `./docker/plugins/BotRandomizer` por cima da pasta (`docker-compose.yml:157`).
A pasta do volume, que é a instalação manual de 05/09, segue lá embaixo e só reaparece se o bind
sair. Ela tem 6 arquivos, contra os 5 do bind (o bind não tem `BotHiderApi.dll`):

| Arquivo | Bytes | sha256 |
|---|---|---|
| `BotHiderApi.dll` | 5120 | `4241f090…` |
| `BotRandomizer.deps.json` | 34695 | `c97ad455…` |
| `BotRandomizer.dll` | 102400 | `56a61bea…` |
| `BotRandomizer.pdb` | 34232 | `f222a7e9…` |
| `charm_placements.json` | 10149 | `6c2660cf…` |
| `cosmetic_catalog.json` | 1194008 | `ee847b01…` |

Os 5 do bind estão em [versões conhecidas](versoes-conhecidas.md#sha256-dentro-do-container) e
no [B1.9](b1.9-botrandomizer-upstream.md). O `BotAimImprover` do volume também ficou embaixo do
bind, com 4 arquivos (`BotAimImprover.dll`, `.deps.json`, `.pdb` e `RayTraceApi.dll`), contra os
3 do bind.

## Contador de matchid da MatchZy

- **Onde:** `game/csgo/addons/counterstrikesharp/plugins/MatchZy/matchzy.db`, SQLite, 57344 B,
  sha256 `bb170a03…`. Sem `-wal` nem `-shm` no snapshot (`journal_mode` `delete`).
- **Como:** tabela `matchzy_stats_matches`, com `matchid INTEGER PRIMARY KEY AUTOINCREMENT`. As
  outras tabelas são `matchzy_stats_maps`, `matchzy_stats_players` e `sqlite_sequence`.
- **Valor em 02/10 00:13:** `sqlite_sequence` de `matchzy_stats_matches` = 73, igual ao maior
  `matchid` da tabela. A próxima partida recebe o `matchid` 74.
- O valor anda a cada partida do Victor: o 73 vale para o snapshot, não para depois dele. O valor de
  agora sai do `matchzy.db` vivo ou do snapshot mais novo, lido pelo servidor.
- O banco também guarda nomes de time e `server_ip`. Nenhuma linha dele entra no repo: daqui,
  só o nome da tabela, o esquema da coluna e o contador.

Por que importa: o watcher nomeia a partida `events_<matchid>_map<N>` e só arquiva o
`current.jsonl` se o `events_<matchid>_map<N>.jsonl` ainda não existir (`watcher.py:476-483`).
Um contador que volta reusa um `matchid`, e a partida nova se perde
([B1.3r](b1.3-cssharp-1.0.375.md), exclusões da restauração).

## VPK

`game/csgo/overrides/`, todos de 05/09 01:19 no volume:

| Arquivo | Variante | Bytes | sha256 |
|---|---|---|---|
| `overrides/botprofile.vpk` | **ativo: Low** | 116432 | `02e5e958…` |
| `overrides/Low/botprofile.vpk` | Low | 116432 | `02e5e958…` |
| `overrides/Medium/botprofile.vpk` | Medium | 408010 | `ba754b61…` |
| `overrides/High/botprofile.vpk` | High | 116192 | `b08bf74e…` |

- `gameinfo.gi:17` registra `Game csgo/overrides/botprofile.vpk` (o `pre.sh` reaplica a linha a
  cada boot).
- **Cópia fora do volume:** `C:/Users/Victor/cs2-tracker-backups/2026-10-01/janela0/volume-overrides-2350.tgz`
  (sha256 `cf8b5c2d…`, 72664 B), tirada só leitura na primeira tentativa da Janela 0. Os quatro
  `.vpk` dentro dela têm os mesmos sha256 da tabela (conferido em 02/10, extraindo numa pasta
  temporária). O [reconstruir o volume](reconstruir-volume.md) ainda diz que não há `.vpk` nos
  backups: ele foi escrito antes dessa cópia.

## Snapshot dos addons

| Snapshot | sha256 | Tamanho | `metamod/` | `counterstrikesharp/` |
|---|---|---|---|---|
| `C:/Users/Victor/cs2-tracker-backups/2026-10-02/janela0/volume-addons-0013.tgz` (02/10 00:13) | `7eccca24…` | 94290153 B | 434 | 866 |
| `C:/Users/Victor/cs2-tracker-backups/2026-09-27/b1.3r/volume-addons-0144.tgz` (27/09, histórico: par Metamod 1411 + CSSharp 1.0.373) | `89556340…` | 80786285 B | não registrado aqui (ver `volume-addons-0144.lista.txt`) | idem |

O de 02/10 tem 1320 entradas: os três `*_version.txt`, o `gameinfo.gi` (só referência) e
`game/csgo/addons/` inteiro. Foi tirado com o container de pé, pelo `tools/jogavel.py snapshot`.
É o snapshot com o par 1469 + 375 e os 8 plugins de hoje.

## Como reproduzir o inventário

Só leitura, em dois caminhos:

- **Do snapshot, sem docker (qualquer papel):** extrair do `volume-addons-*.tgz` para uma pasta
  temporária os `*_version.txt`, o `configs/core.json`, o `gamedata/gamedata.json`, a pasta do
  plugin e o `plugins/MatchZy/matchzy.db`; rodar `sha256sum` e ler o contador com o SQLite em
  `mode=ro`
  (`select seq from sqlite_sequence where name='matchzy_stats_matches'`). Foi assim que este
  inventário foi conferido em 02/10. Apague a pasta temporária no fim.
- **Do volume vivo (só o papel servidor, em janela):** o snapshot sai do
  `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py snapshot --destino <pasta>`,
  que roda `docker run --rm --pull=never --user 0:0 --entrypoint tar` com o volume `:ro`,
  grava o `.sha256` e a `.lista.txt` ao lado e confere as contagens de `metamod/` e
  `counterstrikesharp/` (`tools/jogavel.py:1287-1324`). O `overrides/` não entra no snapshot: em
  02/10 o servidor o leu com outro `docker run ... :ro` (comando exato não registrado), e em
  01/10 tirou o `volume-overrides-2350.tgz`.

## Restauração e o contador

O `tools/jogavel.py restaurar --de <tgz>` (`tools/jogavel.py:1368-1396`) confere o sha256 do
tgz, tira um snapshot `queda-` do estado atual, para o container, extrai por cima e recria. A
extração **exclui** (`tools/jogavel.py:1226-1229`):

- `game/csgo/addons/counterstrikesharp/plugins/MatchZy/matchzy.db*`: o contador de `matchid`
  fica o do volume, e nenhum `matchid` se repete;
- `game/csgo/gameinfo.gi`: é da build do jogo, e o `pre.sh` e a imagem reaplicam as linhas dela
  a cada boot ([B1.3r](b1.3-cssharp-1.0.375.md)).

Restauração à mão segue a mesma regra: o `tar` leva os dois `--exclude`, como no rollback do
B1.3r.

**Reaplicar o contador** só é assunto se o `matchzy.db` do volume se perder (volume
reconstruído, por exemplo). O que as fontes sustentam:

- o contador é o `sqlite_sequence` de `matchzy_stats_matches`, e o próximo `matchid` é ele + 1;
- o valor a reaplicar tem de ser o maior `matchid` já usado: o do `matchzy.db` mais novo que
  existir (snapshot ou `matchzy.db.copia` da janela) ou, se for maior, o do nome dos
  `events_<matchid>_map<N>.jsonl` arquivados em `docker/events-live/` (leitura do servidor);
- se a semente `C:/cs2server` traz `matchzy.db`, e com qual valor: não registrado
  (viria de ler a semente, só leitura, numa janela).

O procedimento de reaplicação (parar o container, editar o banco ou copiar um `matchzy.db` de
volta, conferir o boot) não está registrado: fica a decidir pelo servidor com o PM e o Victor,
na janela em que for preciso, e entra nesta nota depois.

## Janela 0 (02/10, 00:12–00:39)

Registro: `logs/janelas/2026-10-02.md`; coleta: `C:/Users/Victor/cs2-tracker-backups/2026-10-02/janela0/`.

- **Abertura:** "pode mexer no servidor", preflight 0 às 00:12:21, `backup.py` OK, `vigiar` em
  segundo plano. A primeira tentativa (01/10, 23:42–23:51) foi abortada pelo `vigiar` ("python
  sem linha de comando legível"), sem parar nem recriar o container.
- **Snapshot e inventário:** 00:13:20, os valores desta nota.
- **B0.8 aplicado** (`candidato-8`, `214b25b`, PR #38):
  `atualizar` e `recriar` (`--force-recreate`), boot de ~38 s. Mesmo volume (`CreatedAt` e labels
  iguais), 15 mounts iguais, config-hash `3970b702…` inalterado, compose `86d9abd6…` → `46b77848…`.
  Os 14 montados (cfg, `pre.sh`, `match_config`, 3 da captura, 3 do BotAimImprover, 5 do
  BotRandomizer) deram o mesmo sha256 no container e no checkout.
- **Ensaio do voltar:** `jogavel.py voltar` para a `jogavel-2026-10-01` (`0472994`) às 00:29:04,
  recreate em 48 s, mesmo volume e mounts; depois `atualizar` + `recriar` de volta ao
  `candidato-8`, boot de ~35 s.
- **Smoke só de bots (Q7=A):** de_mirage 5x5 por ~2,6 min, `changelevel de_inferno` por
  ~1,8 min; 0 crash, 0 LOADED a mais, 0 exceção.
- **Fechamento:** `get5_status` `none`, cvars iguais à referência (`bot_join_after_player`
  true, `sv_hibernate_when_empty` false, `bot_quota` 0, `bot_quota_mode` fill,
  `mp_ignore_round_win_conditions` false), 14/14 sha256, de_mirage sem humanos; marca removida
  às 00:39:13.
- **Achado do `vigiar`:** o diagnóstico de processos (`diag-python.txt`) viu 4 vezes um python
  com linha de comando `<NULL>`, e todos eram do próprio servidor (o par lançador da `.venv` +
  filho, no instante da saída de um `jogavel.py`). O "python sem linha de comando legível" pode
  ser o próprio servidor, provável causa do aborto de 01/10.

## Hashes completos

```
7eccca24dbb5c4ec07ca2b5c83e86f845ca4bdf83ac8ac34021d2540ec51c8aa  volume-addons-0013.tgz (02/10)
8955634076ec5362734bae48c471a2ae39acfbc8c310eca70395a46ed56ffb81  volume-addons-0144.tgz (27/09)
cf8b5c2df30ac8d193bd4eaf7258b768c7cefa84dde001d82f2026ead141396e  volume-overrides-2350.tgz (01/10)
328694627ee9c165194d7b2ca0f9c2fd4373235ff9a26a91c13f7bf999d82c5e  configs/core.json
7d9bff7aaff8e9edb1ada4ca508fa4e2ad7b12e16ed00ee1b84dd0cb9a3e4ac5  gamedata/gamedata.json
bb170a030eaca879ce1d42d1958e5f488d8886637b9aafb884bc080febd0ae73  plugins/MatchZy/matchzy.db (02/10 00:13)
0542d03b4428d6553140ad509e621dda5ae75612e852d4faa185cc3a55137923  label config-hash do volume
sha256:1056e0031e44709aa5e30a0a0a8f3d5de86c7ee16aa6fee1ec29726a7940ad04  xbird/cs2-matchzy
```

DLL principal por pasta do volume (`plugins/<pasta>/<pasta>.dll`):

```
6aab0e76acede026ab9c92a655b34286de44892f514337d62710d08581eec5fd  MatchZy
922c76a6ac5f663abaa2f5596e3d98fb459da216d694f33a2950a32f2dc15f8d  BotBuy
1beb93f8d24f189ec9795c80760e4e59b27ce6333180b113f98f63ddd0f22c0a  BotState
9e4fc0cfd6b78d67c5eaec86f76c76a7accc59820fca3b02cbc517451d4074e4  NadeSystem
7075101b5d7ac0369eac102b04d23561611b88d5ce44ea0fcc68ff1fe55ad71b  RoundDamageRecap
dfeedab2080db857db140114ee25769c60c1cae08a26f56faf29eaf2fe67be07  BotAimImprover (embaixo do bind)
56a61bea39454f5cd9fcb1f4d28bfea48f9640a4dbe42a5d33f0cf3f0d841758  BotRandomizer (embaixo do bind)
389814db841820d2e270177eed8daad3a042f9b2631dcb0d3826ab3b765e694b  BotAI (mascarado)
d53d4b036082ffd57ad24d7637920f9ad9fb4580bc676a8b539a206137d41d00  BotHiderImpl (mascarado)
```

BotRandomizer do volume (embaixo do bind):

```
4241f0900dee26a024e519aeaf2fcbf596cdecd70ed3b5fa863cc5f8b6f20d1e  BotHiderApi.dll
c97ad455cdf70067ce1cf4db3f1c82439ab516a599fb7db1efe2ce928c50c118  BotRandomizer.deps.json
56a61bea39454f5cd9fcb1f4d28bfea48f9640a4dbe42a5d33f0cf3f0d841758  BotRandomizer.dll
f222a7e9426568c7dc663fe1ab160f3741ae045a45ebafb3e9c5ae51ebf0c1b6  BotRandomizer.pdb
6c2660cf41b62e2d79f693d3735fe9da91a975a116596839e0ab553491935b1c  charm_placements.json
ee847b01aac5dd268d8c2f31673b1d932cd61c3db1c4fcfe4b2da7b3496bbc33  cosmetic_catalog.json
```

Os sha256 dos VPK estão em [versões conhecidas](versoes-conhecidas.md#hashes-completos).
