---
tipo: runbook
status: rascunho
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], recomendação: checklist de boot saudável)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.txt (linhas 13976-14360: boot de 12/10 21:37Z, com update para a 2000930)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.txt (linhas 9810-10220: boot de 05/10 23:12Z, sem update)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.txt (linhas 21, 2230, 9096: ruídos de 04/10 e 05/10)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:434-527"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:547-567"
  - "docs/runbooks/trilha-de-bots.md:180-277"
  - "docs/runbooks/versoes-conhecidas.md:88-89"
  - "docs/runbooks/versoes-conhecidas.md:151-165"
  - "docker/pre.sh:41-44"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:107-114"
atualizado: 2026-10-13
---

# Boot saudável do servidor

> **Para quem:** o papel servidor, depois de todo `up -d --force-recreate` ou restart em
> janela (é o G6), e na coleta só leitura pós-partida, sobre o trecho de boot do log
> coletado. **O que não é:** procedimento de janela. Os comandos são os do
> [B1.3r](b1.3-cssharp-1.0.375.md), passos 8, 9 e 11, e este runbook não traz comando docker
> novo: diz o que o log, a RCON e os arquivos precisam mostrar. Rascunho até a primeira janela
> que o usar.

A referência é a combinação da `jogavel-2026-10-12` ([versões conhecidas](versoes-conhecidas.md)):
Metamod 2.0.0.1469, CSSharp v1.0.375, MatchZy 0.8.15, captura 0.4.0 e 8 plugins. Mudou a
combinação? Atualize as linhas abaixo no mesmo PR que muda o compose.

## 1. O log do boot, na ordem

Trechos do boot de 12/10 21:37Z, sem cor e sem carimbo. O número entre colchetes é a
[armadilha](../armadilhas/README.md) que a linha protege.

| # | Linha esperada | O que prova |
|---|---|---|
| 1 | `Redirecting stderr to '/home/steam/Steam/logs/stderr.txt'` | Começo do processo. É a marca de boot que o P1.13 usa. |
| 2 | `Success! App '730' already up to date.` | Build igual. Se sair `fully installed.`, o SteamCMD baixou build nova: registre como segunda variável (confundidor 3 da trilha) [2]. |
| 3 | `[METAMOD SETUP] Version 2.0.0.1469 is already installed. No action needed.` | Pin do Metamod [1]. Num boot que troca versão: `complete: version X installed.` |
| 4 | `[CSSHARP SETUP] Version v1.0.375 ...` e `[MATCHZY SETUP] Version 0.8.15 ...` | O par e a MatchZy pinados [1]. |
| 5 | `[cs2-tracker] gameinfo.gi ja tem o search path de overrides/botprofile.vpk, nada a fazer` | Search path do VPK [7]. Depois de update do jogo o `gameinfo.gi` volta ao original, e a linha certa é `gameinfo.gi patched: ...`. O `AVISO: marcador ... nao encontrado` é falha. |
| 6 | `GAME "/home/steam/cs2-dedicated/game/csgo/overrides/botprofile.vpk" (vpk)` no dump de search paths | O patch valeu. |
| 7 | `[META] Failed to load plugin addons/RayTrace/...: File not found` e o mesmo de `addons/BotHider/` | As máscaras do lado nativo [3]. São esperadas. |
| 8 | `[MatchZy 0.8.15 LOADED]` | MatchZy carregada. |
| 9 | 8 linhas `Finished loading plugin`: MatchZy, BotBuyPatch, CS2 Tracker Events, NadeSystem, BotAimImprover, Smarter-Bot, RoundDamageRecap e BotRandomizer | A suíte da época. A ordem varia. |
| 10 | `[BotAimImprover] Loaded (Linux).` | Assinatura do upstream ok. `Plugin inactive.` aqui é regressão. |
| 11 | `[META] Loaded 1 plugin.` | A CSSharp carregou no Metamod. `Loaded 0 plugins` é o item [1]. |
| 12 | `[Cs2TrackerEvents] Pronto — gravando em .../events-live/current.jsonl`, **duas vezes** | Uma no `Load()` e outra no mapa inicial [42]. Cada `Pronto` trunca o `current.jsonl` [46]. |
| 13 | `SV:  Connection to Steam servers successful.` e `SV:  VAC secure mode is activated.` | GSLT aceito e VAC ligado [11] [48]. |
| 14 | `GC Connection established for server version <build>` | A build no ar. Anote-a: o cliente do Victor precisa da mesma. |

Busca sobre o log salvo no passo 8 do B1.3r (só leitura de arquivo, nada de docker):

```bash
L="$BK/docker-logs-boot.txt"
for s in "[MatchZy 0.8.15 LOADED]" "[Cs2TrackerEvents] Pronto" "VAC secure mode is activated" "[META] Loaded 1 plugin." "GC Connection established"; do
  grep -qF "$s" "$L" && echo "OK    $s" || echo "FALTA $s"
done
grep -c 'Finished loading plugin' "$L"   # 8 por boot nesta época
grep -n 'gameinfo.gi' "$L"               # "ja tem" ou "patched", nunca o AVISO
```

## 2. Ruído conhecido (não reprova o boot)

- `failed to dlopen ... librenderdoc.so`, `texturebase.cpp ... Falling back to error texture!`,
  `GameTypes: missing mapgroupsSP entry` e `[S_API FAIL] Tried to access Steam interface ...
  before SteamAPI_Init succeeded.`: o servidor headless, em todo boot.
- `Unknown command 'bot_defer_to_human'!` e `[Smarter-Bot] BotController API not available`:
  nos boots de 04/10, 05/10 e 12/10. O BotController não está no volume.
- `Unknown command 'bv_reveal'`: BotVision, ruído da trilha (confundidor 4).
- `[MatchZy] [GetCoachSpawns - FATAL] Error getting coach spawns`: no loadmatch de mapa sem
  arquivo de spawn de coach. Não casa o `FATAL ERROR` do G6.
- `Long frame` no boot e no loadmatch. Só pesa na entrada do humano
  ([overflow no signon](../armadilhas/engine-cs2.md)).

## 3. O que não pode aparecer

A lista do G6 é a do passo 9 do B1.3r, mais as linhas das armadilhas:

| Linha | Armadilha |
|---|---|
| `Loaded 0 plugins`, `requires Metamod with KHook`, `Unknown command` para `matchzy_loadmatch` ou `css_start` | [1](../armadilhas/imagem-e-boot.md) |
| `Segmentation fault`, `core dumped`, `Stack overflow`, `FATAL ERROR`, `Fatal error` (fora da linha que o passo espera) | [2](../armadilhas/imagem-e-boot.md), [13](../armadilhas/imagem-e-boot.md) |
| `CEntityIOOutput_FireOutputInternal`, `CBaseEntity_EmitSoundFilter` | assinaturas do G6 (B1.3r, passo 9) |
| `logger with name 'RayTrace' already exists` | [4](../armadilhas/imagem-e-boot.md) |
| `Error reading from loaded packed store` | [9](../armadilhas/bots-e-perfis.md) |
| `VAC secure mode disabled` | [11](../armadilhas/imagem-e-boot.md) |
| `We're not logged into Steam`, repetido | [48](../armadilhas/windows-e-docker.md) |
| `marcador 'Game csgo/addons/metamod' nao encontrado` | [7](../armadilhas/bots-e-perfis.md) |
| `[Cs2TrackerEvents] ResetForNewMap FALHOU` | [42](../armadilhas/captura-e-eventos.md) |

Os avisos `Failed to find signature` e `Failed to load plugin` que não sejam os do item 7 da
seção 1 vão para o `g6-avisos.txt` pelo nome (B1.3r, passo 9).

## 4. RCON e arquivos montados

Pelos blocos do passo 9 do B1.3r (estado pela RCON, inventário, sha256 e config-hash):

- `version`: a mesma build da linha 14. Mudou desde o "antes"? Duas variáveis.
- `meta list` com a CSSharp; `css_plugins list` com `MatchZy` e `CS2 Tracker Events`.
- `get5_status`: gamestate `none`, sem partida carregada (senão o loadmatch seguinte recusa:
  [18](../armadilhas/matchzy.md)).
- `mp_ignore_round_win_conditions 0` e `bot_quota_mode` igual ao da referência do fechamento
  do [smoke](smoke-partida-de-bots.md#referência-do-fechamento): um 1 esquecido no
  `live_override.cfg` trava todo round ([16](../armadilhas/matchzy.md)).
- sha256 dos arquivos montados igual dentro do container e no checkout; `pre.sh` sem CR
  (`grep -cU $'\r'` igual a 0); config-hash do container igual ao do `docker compose config
  --hash`.
- Variante do VPK: só pelo sha256 lido no volume (trilha, critério 8). O boot não a anuncia.

## 5. Na coleta pós-partida

O `jogavel.py coletar` guarda o log, os sha256 e o config-hash. Aplique as seções 1 a 3 ao
trecho do boot que antecede a partida, do `Redirecting stderr` até o loadmatch. O veredito da
partida é do `tools/evidencia_partida.py` ([G7](trilha-de-bots.md#partida-g7)), não deste
checklist.
