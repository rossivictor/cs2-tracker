---
tipo: runbook
status: vigente
fontes:
  - "docs/runbooks/trilha-de-bots.md:310-321 (registro G6, coluna do smoke)"
  - "docs/runbooks/trilha-de-bots.md:342 (nota do passo 3, B1.5)"
  - "docs/runbooks/trilha-de-bots.md:213-253 (confundidores)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:198-225 (preparação do shell: rcon e prontos)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:275-286 (estado antes, cvars pela RCON)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:543-576 (passo 11, fechamento)"
  - "docs/runbooks/b1.9-botrandomizer-upstream.md:50-55"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:114-138 (Pronto no OnMapStart)"
  - "server-configs/cfg/gamemode_competitive_server.cfg:9-11"
  - "docker-compose.yml:42"
  - "start_match.py:345-370"
  - "tools/preflight.py:21-25"
  - ".claude/agents/servidor.md:54-64"
atualizado: 2026-09-28
---

# Smoke só de bots

Uma partida só de bots, sem o Victor, que expõe um candidato a bots entrando no time e a uma
troca de mapa antes da partida real dele. Quem roda é o papel servidor, **dentro da janela**
(Q7=A), depois do G6 do passo e antes do fechamento da janela. O runbook do passo diz se o
smoke é exigido e o que ele tem de específico (ex.: as duas trocas do
[B1.3r](b1.3-cssharp-1.0.375.md#10-smoke-só-de-bots-q7a-condição-do-b11-para-o-b13r)).

Contexto: [trilha de bots](trilha-de-bots.md). Ele nasceu das janelas de 27/09 (B1.3r, B1.5,
B1.6, B1.8 e B1.9), em que cada smoke redescobriu as mesmas três [armadilhas](#armadilhas).

O smoke **não gera partida no banco**: sem partida carregada na MatchZy não há "MAP ENDED"
para o watcher. O resíduo que ele deixa no `current.jsonl` e na contagem de rounds é zerado
pelo `changelevel` do [fechamento](#fechamento).

## Pré-condições

1. Janela aberta (marca `logs/janelas/ABERTA`), G6 do passo feito e o estado "antes" salvo pela
   RCON. A lista de cvars do "antes" precisa ter `bot_join_after_player`, porque o smoke o muda
   (`.claude/agents/servidor.md`, passo 1).
2. Shell preparado como na [preparação do shell do B1.3r](b1.3-cssharp-1.0.375.md#preparação-do-shell):
   `RAIZ`, `PY`, a pasta `BK` do passo e as funções `rcon`, `prontos` e `esperar_pronto`. O
   `rcon` lê a senha do `.env` dentro do processo do Python e nunca a imprime; nunca rode
   `cat .env`. Sem a função `rcon` não há smoke nem fechamento por RCON: registre o smoke como
   INCONCLUSIVO e siga a regra do resultado abaixo.
3. Preflight 4 entre as fases. Com a janela válida, o `current.jsonl` truncado pelo boot e por
   cada `changelevel` não conta (`tools/preflight.py:21-25`). Um 3 durante o smoke é processo
   (`cs2.exe`, TUI, `watcher` ou `start_match`): o Victor abriu o jogo, e o smoke aborta.

Funções que o smoke acrescenta às do B1.3r (cole no mesmo shell):

```bash
warmups() { docker logs cs2-spike 2>&1 | grep -cF '[MatchZy] [StartWarmup]'; }
esperar_warmup() {   # espera uma linha StartWarmup além das $1 que já havia (até 3 min)
  for i in $(seq 36); do [ "$(warmups)" -gt "$1" ] && { echo "OK    warmup novo"; return 0; }; sleep 5; done
  echo "FALTA warmup novo em 3 min"; return 1
}
```

## Valores do boot

O fechamento devolve estes valores. Compare sempre com o "antes" da **mesma** janela: ele é
a referência, e a tabela diz o que já se viu.

| cvar ou estado | Visto no boot | De onde vem |
|---|---|---|
| mapa | `de_mirage` | `CS2_STARTMAP` (`docker-compose.yml:42`) |
| `get5_status` | `"gamestate":"none"` | MatchZy sem partida carregada |
| `bot_join_after_player` | `true` (G6 do B1.4 e fechamento do B1.5, 27/09) | padrão do jogo; não está no repo |
| `sv_hibernate_when_empty` | `false` (antes e depois do B1.3r, 27/09) | padrão da imagem; não está no repo |
| `bot_quota` | `0` logo depois do boot (B1.3r e B1.4); `10` no fechamento do B1.5 | `gamemode_competitive_server.cfg:10` (`10`), reexecutado a cada load de mapa |
| `bot_quota_mode` | `fill` | `gamemode_competitive_server.cfg:11` |
| `mp_ignore_round_win_conditions` | `false` (B1.3r) | padrão |

Os dois valores de `bot_quota` são jogáveis: o `start_match` zera a quota, dá `bot_kick`,
adiciona os bots da partida um a um e reafirma a quota (`start_match.py:345-370`).

## Armadilhas

### 1. Sem `bot_join_after_player 0`, os bots não entram

- **Onde apareceu:** B1.3r, linha "1 · B1.3r" do [registro G6 da trilha](trilha-de-bots.md#janela-g6):
  smoke "inconclusivo: bots não entram sem humano (faltou `bot_join_after_player 0`)". No
  registro da janela (`logs/janelas/2026-09-27.md`, fora do git), o `status` depois de
  `bot_quota 10` + `mp_warmup_end` mostrou 0 humanos e só o CSTV.
- **Por quê:** o valor do boot é `true`: os bots esperam um humano para entrar. O smoke não tem
  humano.
- **O que fazer:** `bot_join_after_player 0` **antes** do `bot_quota` e do `mp_warmup_end`, e
  `sv_hibernate_when_empty 0` junto (sem humano o servidor pode hibernar, e os bots não
  entram). Só conte o tempo da fase depois do `status` com bots nos dois times.

### 2. Depois do `changelevel`, a quota volta a zero e a readição imediata não pega

- **Onde apareceu:**
  - B1.5: [nota do passo 3 no registro da trilha](trilha-de-bots.md#notas-por-passo): "depois do
    `changelevel` a quota volta a zero no load". Na janela, os bots não voltaram em de_inferno,
    e só entraram de novo readicionados depois da troca seguinte, para de_mirage.
  - B1.6: linha "4 · B1.6" do [registro G6](trilha-de-bots.md#janela-g6): "bots entram antes e
    depois da troca (readição com o mapa assentado)". O registro da janela diz que a readição
    imediata não pegou: o warmup zerou a quota logo depois do `Pronto`.
  - B1.9: linha "7 · B1.9" do registro G6 e item 3 do [runbook do passo](b1.9-botrandomizer-upstream.md#janela-pós-terminei-victor-no-pc):
    "bots readicionados com o mapa assentado depois do `changelevel`". Pelo registro da janela,
    a readição foi feita ~30 s depois do `changelevel` para de_inferno, e os 10 bots entraram.
- **Por quê:** o `[Cs2TrackerEvents] Pronto` não marca o mapa assentado. Ele sai no
  `OnMapStart` da captura (`Cs2TrackerEventsPlugin.cs:114` e `:138`), logo no início do
  load, **antes** do `Host activate` e do warmup da MatchZy. Nos logs dos smokes do B1.5, do
  B1.6 e do B1.9 (`docker-logs-smoke.txt` das coletas em
  `C:/Users/Victor/cs2-tracker-backups/2026-09-27/<passo>/`), a linha
  `[MatchZy] [StartWarmup] ... Executing Warmup CFG from MatchZy/warmup.cfg` veio 4,0 s, 4,0 s e
  4,35 s depois do `Pronto`. Bot readicionado antes disso cai quando o warmup zera a quota.
- **O que fazer:** depois do `changelevel`, espere o `Pronto` novo, **depois** o `StartWarmup`
  novo, e mais uma folga, até ~30 s contados do `changelevel` (o que deu certo no B1.9). Só
  então reenvie as cvars de entrada e confira o `status`. A folga além do `StartWarmup` não foi
  medida: se os bots não entrarem, espere mais 30 s e readicione de novo antes de concluir
  qualquer coisa.

### 3. O fechamento precisa voltar às cvars do boot

- **Onde apareceu:** no [passo 11 do B1.3r](b1.3-cssharp-1.0.375.md#11-fechamento-g6), que
  devolvia `bot_quota`, `bot_quota_mode` e `sv_hibernate_when_empty`, mas não o
  `bot_join_after_player` que o smoke muda. O fechamento do B1.5 (registro da janela) foi o
  primeiro a devolvê-lo: `bot_join_after_player 1`, `bot_quota 10 fill` e `get5_status` none.
- **Por quê:** o que o smoke deixa diferente do boot vira uma variável a mais na partida do
  Victor. O `changelevel de_mirage` final vem do passo 11 do B1.3r: se o smoke terminar em
  de_mirage com rounds ao vivo e a partida seguinte for em de_mirage, a MatchZy não troca de
  mapa, e os rounds dos bots entram na partida dele.
- **O que fazer:** o [fechamento](#fechamento) abaixo, com a conferência pela RCON.

## Procedimento

As durações medidas vêm do [registro G6 da trilha](trilha-de-bots.md#janela-g6) e dos registros
das janelas de 27/09 (`logs/janelas/2026-09-27.md`).

| Fase | Medido | Onde |
|---|---|---|
| Fase 1, mapa do boot | 3 min (B1.5, B1.9), 2,5 min (B1.6); 5 rounds, 21:18–21:27 (B1.8, o card pedia 5 rounds) | registros das janelas |
| Troca de mapa até readicionar | ~30 s (B1.9) | registro da janela do B1.9 |
| Fase 2, mapa novo | 2 min (B1.9); 1,5 min depois da 2ª troca (B1.5) | registros das janelas |
| Janela inteira (ff, recreate, G6, smoke e fechamento) | 8 min (B1.9, 22:29–22:37) | [registro G6](trilha-de-bots.md#janela-g6) |

O smoke só com fechamento não foi cronometrado à parte: meça do `N=` ao `fechamento-rcon.txt` e
anote no registro da janela.

### 1. Entrada

```bash
N=$(docker logs cs2-spike 2>&1 | wc -l)   # linhas do log antes do smoke
rcon "sv_hibernate_when_empty 0"          # sem humano o servidor pode hibernar
rcon "bot_join_after_player 0"            # armadilha 1: sem isso os bots não entram sem humano
rcon "bot_quota_mode normal"; rcon "bot_quota 10"
rcon "mp_warmup_end"
rcon "status" > "$BK/smoke-status.txt"    # precisa haver bots nos dois times
```

- Sem bots no `status`, espere 30 s e rode o `status` de novo. Se continuar vazio, o smoke é
  INCONCLUSIVO ([resultado](#resultado)).
- Fase 1: 2,5 a 3 min de rounds no mapa do boot, ou o que o card do passo pedir (o B1.8 pediu
  5 rounds). Preflight entre as fases.

### 2. Troca de mapa, com o mapa assentado

```bash
P=$(prontos); W=$(warmups); rcon "changelevel de_inferno"
esperar_pronto "$P" && esperar_warmup "$W"
#   folga até ~30 s desde o changelevel (armadilha 2)
rcon "bot_join_after_player 0"; rcon "bot_quota_mode normal"; rcon "bot_quota 10"
rcon "mp_warmup_end"
rcon "status" > "$BK/smoke-status-2.txt"  # bots nos dois times de novo
```

- Escolha um mapa diferente de `de_mirage`, o do boot, para a troca ser de verdade.
- Reenviar o `bot_join_after_player 0` é defesa: não se mediu se ele sobrevive ao load. O
  `bot_quota` e o `bot_quota_mode` não sobrevivem (armadilha 2).
- `FALTA` no `esperar_pronto` ou no `esperar_warmup` quer dizer que a troca de mapa não
  terminou em 3 min: é motivo para voltar pelo runbook do passo.
- Fase 2: 2 min de rounds. Se o passo pedir outra troca (o B1.3r pede duas), repita este bloco
  com o mapa seguinte.

### 3. O que olhar no log

O log do smoke é lido pela contagem de linhas `N`, e não por `--since`: no Docker Desktop, um
relógio da VM atrasado (acontece depois de suspender o PC) apagaria justamente um crash.

```bash
docker logs -t cs2-spike 2>&1 | tail -n +$((N+1)) > "$BK/docker-logs-smoke.txt"
L="$BK/docker-logs-smoke.txt"
grep -nE 'Segmentation fault|Stack overflow|core dumped|FATAL ERROR' "$L" || echo "OK    smoke sem crash"
grep -c 'MatchZy 0.8.15 LOADED' "$L"      # precisa ser 0: outro LOADED = o processo reiniciou
grep -nE '<plugin do passo>|Unhandled exception|Error invoking callback|signature failed|Fatal error' "$L"
```

- **Crash:** qualquer linha do primeiro `grep` reprova. O `SIGSEGV` em `libtier0.so` do
  Serilog (confundidor 4 da trilha) é aleatório: olhe o backtrace antes de culpar o plugin.
- **Reinício da MatchZy:** um `LOADED` dentro do smoke quer dizer que o processo do jogo caiu e
  subiu de novo, mesmo sem linha de crash.
- **Exceção do plugin do passo:** troque `<plugin do passo>` pelo nome dele no log (ex.:
  `BotRandomizer`, `NadeSystem`) e leia cada linha. Os textos já vistos na trilha:

  | Plugin | Linha que reprova | Fonte |
  |---|---|---|
  | BotRandomizer | `signature failed; ... cosmetics disabled`, `GiveNamedItem pre-hook failed` | [B1.9](b1.9-botrandomizer-upstream.md#janela-pós-terminei-victor-no-pc), passo 7 da trilha |
  | BotAimImprover | `Fatal error during Load() (signature broken?). Plugin inactive.` (veredito inativo) | passo 2 da trilha |

- **Ruído conhecido, que não reprova** ([Sobras da trilha](trilha-de-bots.md#sobras)): 3
  `Error invoking callback` do BotBuyPatch no warmup do `changelevel` (só reprova se o passo for
  o do BotBuy), "Grenade has no weapon info" do NadeSystem, `Failed to load plugin` do
  RayTrace e do BotHider mascarados, `Unknown command 'bv_reveal'`.

## Fechamento

```bash
rcon get5_status                          # gamestate "none"; se não for: rcon css_endmatch
rcon "mp_ignore_round_win_conditions 0"
rcon "bot_kick"
rcon "bot_join_after_player 1"            # armadilha 3: o valor do boot é true
rcon "bot_quota <valor do antes>"
rcon "bot_quota_mode <valor do antes>"
rcon "sv_hibernate_when_empty <valor do antes>"
P=$(prontos); rcon "changelevel de_mirage"   # zera os rounds do smoke e trunca o current.jsonl
esperar_pronto "$P"
for c in get5_status bot_join_after_player sv_hibernate_when_empty bot_quota bot_quota_mode mp_ignore_round_win_conditions; do echo "== $c"; rcon "$c"; done > "$BK/fechamento-rcon.txt" 2>&1
```

- O `fechamento-rcon.txt` precisa bater com o "antes": `get5_status` none,
  `bot_join_after_player` true, `sv_hibernate_when_empty` e `mp_ignore_round_win_conditions`
  false. `bot_quota` e `bot_quota_mode` saem do `gamemode_competitive_server.cfg`, reexecutado
  no load do `de_mirage`: `10 fill` é o normal depois dessa troca (fechamento do B1.5), e `0`
  também é jogável ([valores do boot](#valores-do-boot)).
- Se algo não voltar, um `docker restart cs2-spike` zera as cvars. Depois dele confira a
  build de novo: o SteamCMD roda a cada start (confundidor 3 da trilha).
- Depois daqui, o runbook do passo segue com o próprio fechamento da janela (remoção da marca,
  registro e aviso ao Victor).

## Resultado

Vai na coluna "Smoke só de bots" do [registro G6 da trilha](trilha-de-bots.md#janela-g6) e no
registro da janela: mapas, minutos de cada fase, bots no `status` antes e depois da troca, e a
contagem de crash, reinício e exceção.

- **OK:** bots nos dois times antes e depois de cada troca, 0 crash, 0 `LOADED` a mais, 0
  exceção do plugin do passo, e o fechamento conferido.
- **INCONCLUSIVO:** os bots não entraram (como no B1.3r), ou o smoke não rodou. Se o card
  exige o smoke, o resultado da janela não é "candidato no ar": volte pelo runbook do passo,
  ou deixe no ar só com OK explícito do Victor via PM, gravado no registro
  (`.claude/agents/servidor.md`, passo 10).
- **Voltar:** crash, reinício da MatchZy, exceção do plugin do passo, ou troca de mapa sem
  `Pronto` e `StartWarmup` em 3 min. A volta é a do runbook do passo, depois de salvar o
  `docker-logs-smoke.txt`.
