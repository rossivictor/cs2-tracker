---
tipo: runbook
status: vigente
fontes:
  - "docs/runbooks/trilha-de-bots.md:32-47 (máscaras no efcaa42)"
  - "docs/runbooks/trilha-de-bots.md:303-331 (registro G6 e G7)"
  - "docs/runbooks/trilha-de-bots.md:347-369 (épocas)"
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
atualizado: 2026-10-02
---

# Versões conhecidas

> **Para quem:** o papel servidor, na volta ao jogável e na Janela 0; o tech-manager, ao criar
> uma tag `jogavel-*`; o QA, ao conferir uma coleta.
> **Card:** B0.3. Cada tag registrada aqui é uma combinação em que o Victor jogou
> ([ADR-0004](../adr/0004-jogo-sempre-jogavel.md)).

A volta ao jogável precisa saber qual combinação era a boa, e até aqui essa informação estava
espalhada em commits, runbooks e registros de janela. Esta nota junta tudo por tag.

Convenções:

- sha256 aparece abreviado (8 caracteres) nas tabelas. O valor inteiro está em
  [Hashes completos](#hashes-completos).
- **não registrado** quer dizer que nenhuma fonte guardou o valor. A nota diz de onde ele viria.
  Nenhum valor daqui é estimado.
- Fontes fora do git: os registros de janela em `logs/janelas/2026-09-27.md`, `2026-09-28.md`,
  `2026-09-30.md` e `2026-10-02.md` (checkout principal) e as coletas em
  `C:/Users/Victor/cs2-tracker-backups/2026-09-27/`, `2026-09-28/`, `2026-10-01/` e
  `2026-10-02/`. Nas tabelas, `b1.x/...` é relativo a `2026-09-27/`, a coleta da partida 36
  aparece como `2026-10-01/g7-2000922-partida/`, e a da Janela 0 como `2026-10-02/janela0/`.

## O que não mudou em nenhuma tag

| Item | Valor | Fonte |
|---|---|---|
| Imagem | `xbird/cs2-matchzy`, sem tag no compose (vale a `latest` local). Digest `sha256:1056e003…`, o mesmo de 27/09 01:44 (antes do B1.3r) a 30/09 23:05 (janela da build 2000922). O container de 28/09 não foi recriado desde então: na coleta da partida 36 (01/10) o `Created` segue `2026-09-28T01:30:07Z` | `b1.3r/antes-container.txt`; registros de janela; `2026-10-01/g7-2000922-partida/estado-container.txt` |
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

**Estado no ar:** desde a Janela 0 (02/10), o `candidato-8` (`214b25b`, B0.8), que fecha com a
partida do Victor (G7). Ele só muda o compose (volume `cs2-data` external, com nome fixo): o
volume, os mounts e o config-hash são os da `jogavel-2026-10-01`, a última tag
([inventário do volume](inventario-volume.md)). Na `jogavel-2026-10-01`, o compose é o mesmo
da `jogavel-2026-09-28`. As duas variáveis que entraram depois dela, sem commit, foram
validadas juntas na partida 36 (época "VPK Low" da [trilha](trilha-de-bots.md#épocas)): o VPK
Low desde 28/09 19:54 e a build 2000922, que veio do SteamCMD no restart da janela de 30/09
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
`02e5e958…`, o Low (`sha-vpk.txt` da coleta).

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
| `candidato-8` | `214b25b` | B0.8 (volume external), aplicado na Janela 0 | aberto: espera a partida do Victor |

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

### Época atual: `jogavel-2026-10-01` (compose igual ao da `jogavel-2026-09-28`)

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

No `candidato-8` (`214b25b`, B0.8) as máscaras são as mesmas, e as linhas descem 2 por causa do
comentário novo no mount do `cs2-data`: 102, 109, 144, 153 e 164 (mascarados), 152, 161 e 173
(máscaras comentadas), 149 e 157 (binds). Conferido em 02/10 com
`git grep -n -E '_empty|plugins/(BotAimImprover|BotRandomizer)' 214b25b -- docker-compose.yml`.

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
B0.3b).

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
candidato-2           36ff2fe29210820d59c8b82cab7675c9f10be47bccaa6392ab78d4420cef85a8 · 8cb6674414bc5f5e4cf0c01b363736de4168b0a0a30c6be26a2f000e89fc5f13
candidato-8           46b77848b093402604970cf197a35c0c2d34769a8532f2ad7bfcc1fd0ad2b4c6 · 2a88947413497d434de821142c11498132662e5ce11af2a7c31d948047486cf5
```

O CRLF do `candidato-8` é o da Janela 0 (`depois-medicoes.txt`); o blob LF saiu de
`git show 214b25b:docker-compose.yml | sha256sum`, em 02/10.

config-hash:

```
jogavel-2026-09-27    5576531460072ecb9957c935c16886bc8600cec2824b3335db67a371266351df
jogavel-2026-09-27-2  a68705896cd9fe0c7f2f5688a196e6898099a98680165878d9dbcb42c10e1c31
jogavel-2026-09-27-3  dc0a3295d095f11e4cf7be41ac2068a2c1dadf0020e816b7bc84b4db0bb28996
jogavel-2026-09-27-4  ecbbf707988a34deaade85cbbf25753374ea8d02ecce9fc628de4da32e0631fa
jogavel-2026-09-27-5  a6bbdcefd88953243f810e902d8d4ab8ff0b0590d9aed75f7c419389bbfecb0b
jogavel-2026-09-28    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
jogavel-2026-10-01    3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37
candidato-2           c8a2a53512439ea4f9baa7cbe2e598e2c4b24b1c0725738593c42e3b2f860ac5
candidato-8           3970b702027592f02ad17e304f76ba8c19148bc9eedd060b9a679870da44fa37  (Janela 0)
```

Arquivos montados e imagem:

```
aebb5df56682181f8a132c1e3c808f83ba1afac10060146238c04d097727762c  cfg/gamemode_competitive_server.cfg (disco, CRLF)
a0c195eec36b76670aa2e44e619cd92202407287c04df5613e99b26c40fe5b6f  cfg/gamemode_competitive_server.cfg (blob LF do git)
233e5aa08cfe40d4c3a638031f630e7617270e1379ce09ed5390c97ae03c4f1d  pre.sh (LF no disco e no git)
697760a7566ee54a08b95bf804d6c21ab709b8e2762d83e5f8f846787270e115  Cs2TrackerEvents.dll
137a42f20c1c33f69fa95942437a43a0d431dd8e4beac71e985ee4697dbfdd99  Cs2TrackerEvents.deps.json
ca994b0c37bf60e122b8ce4d25a1950bb71c82866b62f74c7240df5e37d07287  Cs2TrackerEvents.pdb
2f5fb06d61ee4984ae95dab3e8b097a3a29a6f2fe1c0e1990f9b76bf3319c785  match_config.spike.json (partida 26)
a6f6960623c91a4d6742e7b934d841792288f017fc6e5aa190f74106e9a9a627  match_config.spike.json (partidas 27, 29, 30 e 31)
f8eeeaf7fb2913f0d6baf1dd712631b5ddc137b075266e2f1c6e13b45657074f  match_config.spike.json (partida 28)
0816da11af268caff0a19fc6d4040d795897a9478b74d7bcd052795d0facb1bd  match_config.spike.json (partida 36)
2000bf4e864826f24678f4cbb0e381f1399341f9a4bc54b01ab6debf8d89a7cf  match_config.spike.json (Janela 0, 02/10)
7075101b5d7ac0369eac102b04d23561611b88d5ce44ea0fcc68ff1fe55ad71b  RoundDamageRecap.dll (volume)
sha256:1056e0031e44709aa5e30a0a0a8f3d5de86c7ee16aa6fee1ec29726a7940ad04  xbird/cs2-matchzy
```

VPK (`overrides/<variante>/botprofile.vpk`, no volume):

```
02e5e958f3e0372b5616d858014d5801a980c23961556da9206a97887c1b29d0  Low (116432 B)
ba754b610aaeb67a3088a796b92cf28c49ac725ac071760aaf24208583dcc585  Medium (408010 B)
b08bf74eb74f1a0c9e84fb12c4a92bdb972703d35303cc69f9258176f0a10176  High (116192 B)
```
