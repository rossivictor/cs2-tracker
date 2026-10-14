---
tipo: runbook
status: vigente
fontes:
  - "docs/runbooks/trilha-de-bots.md:310-321 (registro G6, coluna do smoke)"
  - "docs/runbooks/trilha-de-bots.md:342 (nota do passo 3, B1.5)"
  - "docs/runbooks/trilha-de-bots.md:213-253 (confundidores)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:198-225 (preparação do shell: rcon e prontos)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:278-289 (estado antes, cvars pela RCON)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:483-497 (passo 9: cvars do boot, a referência do fechamento)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:547-581 (passo 11, fechamento)"
  - "docs/runbooks/b1.9-botrandomizer-upstream.md:47-57"
  - "commit 5095d29 (esperar_warmup nasce no B0.9b, 28/09, depois dos smokes de 27/09)"
  - "backup:../2026-09-27/b1.5/docker-logs-smoke.txt (Pronto e StartWarmup das duas trocas: linhas 218, 374, 460 e 604)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:114-138 (Pronto no OnMapStart)"
  - "server-configs/cfg/gamemode_competitive_server.cfg:9-11"
  - "docker-compose.yml:42"
  - "start_match.py:345-370"
  - "tools/preflight.py:21-25"
  - ".claude/agents/servidor.md:54-64"
  - "docs/runbooks/voltar-ao-jogavel.md:182-188 (coleta incompleta: json-file corrompido em 05/10 e 06/10)"
  - "backup:../2026-10-13/janela-diag/janela.vars (marca, desde e esperar_padrao, usados ao vivo no T1 do B1.12b)"
  - "backup:../2026-10-13/janela-diag/t1-resumo.txt (OK do esperar_padrao para Pronto e StartWarmup nas 12 trocas; 351 a 413 linhas por ciclo)"
  - "backup:../2026-10-13/janela-diag/fechamento.txt (OK do esperar_padrao no changelevel do fechamento)"
  - "backup:../2026-10-13/janela-diag/docker-logs-antes.txt (o docker logs para a frente termina em 2026-10-05T02:44:21Z)"
atualizado: 2026-10-13
---

# Smoke só de bots

Uma partida só de bots, sem o Victor, que expõe um candidato a bots entrando no time e a uma
troca de mapa antes da partida real dele. Quem roda é o papel servidor, **dentro da janela**
(Q7=A), depois do G6 do passo e antes do fechamento da janela. O runbook do passo diz se o
smoke é exigido e o que ele tem de específico (ex.: as duas trocas do
[B1.3r](b1.3-cssharp-1.0.375.md#10-smoke-só-de-bots-q7a-condição-do-b11-para-o-b13r)).

Contexto: [trilha de bots](trilha-de-bots.md). Ele nasceu das janelas de 27/09 (B1.3r, B1.5,
B1.6, B1.8 e B1.9), em que cada smoke redescobriu as mesmas três [armadilhas](#armadilhas). A
quarta, a do log lido pelo começo, veio da janela de diagnóstico de 13/10 (B1.12b).

O smoke **não gera partida no banco**: sem partida carregada na MatchZy não há "MAP ENDED"
para o watcher. O resíduo que ele deixa no `current.jsonl` e na contagem de rounds é zerado
pelo `changelevel` do [fechamento](#fechamento).

## Pré-condições

1. Janela aberta (marca `logs/janelas/ABERTA`), G6 do passo feito e a
   [referência do fechamento](#referência-do-fechamento) salva pela RCON. A lista de cvars dela
   precisa ter `bot_join_after_player`, porque o smoke o muda.
2. Shell preparado como na [preparação do shell do B1.3r](b1.3-cssharp-1.0.375.md#preparação-do-shell):
   `RAIZ`, `PY`, a pasta `BK` do passo e a função `rcon`. O `rcon` lê a senha do `.env` dentro
   do processo do Python e nunca a imprime; nunca rode `cat .env`. Sem a função `rcon` não há
   smoke nem fechamento por RCON: registre o smoke como INCONCLUSIVO e siga a regra do resultado
   abaixo. O `prontos` e o `esperar_pronto` daquela preparação contam do começo do log e não
   servem mais ([armadilha 4](#armadilhas)): use os ajudantes abaixo.
3. Preflight 4 entre as fases. Com a janela válida, o `current.jsonl` truncado pelo boot e por
   cada `changelevel` não conta (`tools/preflight.py:21-25`). Um 3 durante o smoke é processo
   (`cs2.exe`, TUI, `watcher` ou `start_match`): o Victor abriu o jogo, e o smoke aborta.

Ajudantes que leem o log pelo fim, com marca de carimbo (cole no mesmo shell; são os do
`janela.vars` da janela de 13/10, só com comentários e quebra de linha a mais):

```bash
marca() { docker logs -t --tail 1 cs2-spike 2>&1 | tail -1 | cut -d' ' -f1; }   # carimbo da última linha
desde() { docker logs -t --tail ${2:-5000} cs2-spike 2>&1 | awk -v t="$1" '$1 > t'; }   # linhas depois da marca $1, entre as últimas $2
esperar_padrao() {   # espera o texto $2 depois da marca $1 (até $3 × 5 s; padrão 36, 3 min)
  for i in $(seq ${3:-36}); do [ "$(desde "$1" | grep -cF "$2")" -gt 0 ] && { echo "OK    $2"; return 0; }; sleep 5; done
  echo "FALTA $2"; return 1
}
```

Uso: `m=$(marca)` **antes** do evento; depois, `esperar_padrao "$m" '[Cs2TrackerEvents] Pronto'`
e `esperar_padrao "$m" '[MatchZy] [StartWarmup]'`. Eles substituem o `prontos` e o
`esperar_pronto` do B1.3r e o `warmups` e o `esperar_warmup` que este runbook trazia, que
contavam linhas do começo do log ([armadilha 4](#armadilhas)).

- **Já rodaram ao vivo:** no T1 do [B1.12](b1.12-segfault-troca-de-mapa-md3.md#83-t1-braço-a-12-viradas-sem-queda)
  (13/10), o `esperar_padrao` devolveu `OK` para o `Pronto` e para o `StartWarmup` nas 12
  trocas e no `changelevel` do fechamento (`t1-resumo.txt` e `fechamento.txt` da janela).
- A marca é o carimbo da última linha do próprio log, no mesmo relógio das linhas que o `desde`
  compara: o atraso entre o relógio do host e o da VM do Docker Desktop não conta. Um salto do
  relógio da VM para trás entre a marca e o evento contaria; não foi visto até aqui.
- O `desde` só olha as últimas 5000 linhas (o segundo argumento muda isso). Um evento mais
  antigo que isso some da conta: para esperar, tire a marca logo antes do comando.
- O `esperar_warmup` antigo **nunca rodou ao vivo** (nasceu em 28/09, no B0.9b, depois dos
  smokes de 27/09) e, com o log de hoje, daria `FALTA` em toda troca.

## Valores do boot

O fechamento devolve estes valores. A referência é a da **mesma** janela, pela
[regra do fechamento](#referência-do-fechamento); a tabela só diz o que já se viu.

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
  `[MatchZy] [StartWarmup] ... Executing Warmup CFG from MatchZy/warmup.cfg` veio de 1,5 s a
  4,35 s depois do `Pronto`: no B1.5, 4,00 s na 1ª troca (de_inferno, linhas 218 e 374) e
  1,52 s na 2ª (de_mirage, linhas 460 e 604); 4,02 s no B1.6 (linhas 187 e 342) e 4,35 s no
  B1.9 (linhas 339 e 495). Bot readicionado antes disso cai quando o warmup zera a quota.
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

### 4. O `docker logs` lido do começo para em 05/10

- **Onde apareceu:** na coleta de 12/10, com o `docker-logs.txt` de 0 bytes e código 0
  ([coleta incompleta](voltar-ao-jogavel.md#coleta-incompleta)); de novo na coleta de 13/10; e na
  janela de diagnóstico de 13/10 (B1.12b), em que o `docker logs` lido para a frente parou em
  2026-10-05T02:44:21Z: o `docker-logs-antes.txt` da janela termina nesse carimbo. Com isso, o
  `prontos` e o `warmups` ficam presos na contagem de 05/10, e o `esperar_pronto` e o
  `esperar_warmup` dariam `FALTA` em toda troca, mesmo com a troca boa.
- **Por quê:** o json-file do container tem uma entrada corrompida depois de cada parada brusca
  (05/10 02:44Z e 06/10 04:04Z, sem linhas de desligamento). Lido do começo (sem `--tail`, ou
  com `--since`), o `docker logs` para em silêncio na primeira delas, com código 0. O `--tail`
  lê do fim, e o trecho depois da última parada brusca sai inteiro. A versão antiga deste
  runbook também guardava o log do smoke pela contagem de linhas (`N=$(docker logs | wc -l)` e
  `tail -n +N`), que cai no mesmo buraco: o log do smoke sairia vazio.
- **O que fazer:** ler tudo pelo fim, com a marca de carimbo: `marca`, `desde` e
  `esperar_padrao` ([pré-condições](#pré-condições)) e o log do smoke pelo
  [passo 3](#3-o-que-olhar-no-log). Não recrie o container para "limpar" o log: o recreate
  descarta o json-file, com as linhas que ainda se leem, e é infra, só em janela. Num container
  recriado, a leitura do começo volta a funcionar até a próxima parada brusca, e os ajudantes
  pelo fim seguem valendo do mesmo jeito.

## Procedimento

As durações medidas vêm do [registro G6 da trilha](trilha-de-bots.md#janela-g6) e dos registros
das janelas de 27/09 (`logs/janelas/2026-09-27.md`).

| Fase | Medido | Onde |
|---|---|---|
| Fase 1, mapa do boot | 3 min (B1.5, B1.9), 2,5 min (B1.6); 5 rounds, 21:18–21:27 (B1.8, o card pedia 5 rounds) | registros das janelas |
| Troca de mapa até readicionar | ~30 s (B1.9) | registro da janela do B1.9 |
| Fase 2, mapa novo | 2 min (B1.9); 1,5 min depois da 2ª troca (B1.5) | registros das janelas |
| Janela inteira (ff, recreate, G6, smoke e fechamento) | 8 min (B1.9, 22:29–22:37) | [registro G6](trilha-de-bots.md#janela-g6) |

O smoke só com fechamento não foi cronometrado à parte: meça do `M=` ao `fechamento-rcon.txt` e
anote no registro da janela.

### 1. Entrada

```bash
M=$(marca)                                # carimbo do log antes do smoke (armadilha 4)
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
m=$(marca); rcon "changelevel de_inferno"
esperar_padrao "$m" '[Cs2TrackerEvents] Pronto' && esperar_padrao "$m" '[MatchZy] [StartWarmup]'
#   folga até ~30 s desde o changelevel (armadilha 2)
rcon "bot_join_after_player 0"; rcon "bot_quota_mode normal"; rcon "bot_quota 10"
rcon "mp_warmup_end"
rcon "status" > "$BK/smoke-status-2.txt"  # bots nos dois times de novo
```

- Escolha um mapa diferente de `de_mirage`, o do boot, para a troca ser de verdade.
- Reenviar o `bot_join_after_player 0` é defesa: não se mediu se ele sobrevive ao load. O
  `bot_quota` e o `bot_quota_mode` não sobrevivem (armadilha 2).
- `FALTA` num dos dois `esperar_padrao` quer dizer que a troca de mapa não terminou em 3 min:
  é motivo para voltar pelo runbook do passo. Antes, confira com `desde "$m" | grep -F
  'StartWarmup'` que a linha não está lá; se estiver, o erro é do ajudante: registre e siga
  pela [armadilha 2](#armadilhas).
- Fase 2: 2 min de rounds. Se o passo pedir outra troca (o B1.3r pede duas), repita este bloco
  com o mapa seguinte.

### 3. O que olhar no log

O log do smoke é lido pelo fim, a partir da marca `M` da entrada. Não é lido do começo
([armadilha 4](#armadilhas)) nem por `--since`: no Docker Desktop, um relógio da VM atrasado
(acontece depois de suspender o PC) apagaria justamente um crash, e a marca, por ser um
carimbo do próprio log, não depende do relógio do host.

```bash
T=20000   # linhas lidas do fim; o T1 de 13/10 deu 351 a 413 linhas por ciclo de ~1 min 45 s
[[ "$(docker logs -t --tail $T cs2-spike 2>&1 | head -1 | cut -d' ' -f1)" < "$M" ]] || echo "FALTA cobertura: o --tail $T não chega à marca; aumente o T"
desde "$M" $T > "$BK/docker-logs-smoke.txt"
L="$BK/docker-logs-smoke.txt"
grep -nE 'Segmentation fault|Stack overflow|core dumped|FATAL ERROR' "$L" || echo "OK    smoke sem crash"
grep -c 'MatchZy 0.8.15 LOADED' "$L"      # precisa ser 0: outro LOADED = o processo reiniciou
grep -nE '<plugin do passo>|Unhandled exception|Error invoking callback|signature failed|Fatal error' "$L"
```

- **Cobertura:** a conferência da primeira linha e o `T` nasceram aqui em 13/10 (card B1.12c)
  e ainda não rodaram ao vivo. No primeiro smoke, anote no registro se ela passou e quantas
  linhas o `docker-logs-smoke.txt` teve. Um `FALTA cobertura` não é crash: aumente o `T` e
  leia de novo.
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

### Referência do fechamento

Regra única, para este runbook e para o
[passo 11 do B1.3r](b1.3-cssharp-1.0.375.md#11-fechamento-g6), com ou sem smoke: as cvars
voltam às **do boot do candidato**, lidas pela RCON depois do G6 e antes da entrada do smoke.
No B1.3r essa leitura é o `depois-rcon.txt` do
[passo 9](b1.3-cssharp-1.0.375.md#9-g6-o-que-o-log-precisa-ter-e-não-ter), que traz o
`bot_join_after_player`.

- **Por quê:** o recreate da janela sobe um processo novo do jogo, com as cvars do boot, e é
  nesse boot que o Victor joga a partida seguinte. O passo 9 do B1.3r chama esses valores de
  "normais" e os guarda para o fechamento. O fechamento do B1.5 devolveu o
  `bot_join_after_player 1`, o `true` do boot ([armadilha 3](#armadilhas)).
- **O que não é referência:** o estado do passo 1 do runbook do passo (o `antes-rcon.txt` do
  B1.3r) é do container anterior ao recreate. Ele serve para comparar build e inventário, não
  cvar.

```bash
rcon get5_status                          # gamestate "none"; se não for: rcon css_endmatch
rcon "mp_ignore_round_win_conditions 0"
rcon "bot_kick"
rcon "bot_join_after_player 1"            # armadilha 3: o valor do boot é true
rcon "bot_quota <valor da referência>"
rcon "bot_quota_mode <valor da referência>"
rcon "sv_hibernate_when_empty <valor da referência>"
m=$(marca); rcon "changelevel de_mirage"   # zera os rounds do smoke e trunca o current.jsonl
esperar_padrao "$m" '[Cs2TrackerEvents] Pronto'
for c in get5_status bot_join_after_player sv_hibernate_when_empty bot_quota bot_quota_mode mp_ignore_round_win_conditions; do echo "== $c"; rcon "$c"; done > "$BK/fechamento-rcon.txt" 2>&1
```

- O `fechamento-rcon.txt` precisa bater com a [referência](#referência-do-fechamento): `get5_status` none,
  `bot_join_after_player` true, `sv_hibernate_when_empty` e `mp_ignore_round_win_conditions`
  false. `bot_quota` e `bot_quota_mode` são a única diferença aceita em relação à referência:
  saem do `gamemode_competitive_server.cfg`, reexecutado no load do `de_mirage`, e por isso
  `10 fill` é o normal depois dessa troca (fechamento do B1.5) mesmo que a referência lida
  logo depois do boot diga `bot_quota 0`; os dois valores são jogáveis
  ([valores do boot](#valores-do-boot)).
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
