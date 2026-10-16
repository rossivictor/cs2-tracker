---
tipo: runbook
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.playability_protocol, seções 2, 5 e 7)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (judgements[1].must_fix[1], runtime file)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.playability_protocol, seção 8, janelas)"
  - "tools/jogavel.py:1-52"
  - "tools/jogavel.py:101-108 (eventos de round)"
  - "tools/jogavel.py:311-370 (partida em curso)"
  - "tools/jogavel.py:393-437 (runtime file e volta do merge falho)"
  - "tools/jogavel.py:468-499 (recreate só do checkout principal)"
  - "tools/jogavel.py:578-742 (voltar: pasta do plugin pelo manifesto em 578-633, pre.sh antes dela em 716-724)"
  - "tools/jogavel.py:931-1316 (janela abrir, fechar, vigiar e aborto; timeouts do ciclo no B0.7c)"
  - "tools/jogavel.py:1088-1229 (python sem linha confirmado na releitura e árvore do servidor, B0.7e)"
  - "tools/jogavel.py:1340-1373 (conferência do log salvo, B0.7f)"
  - "tools/jogavel.py:1375-1520 (leitura pelo fim, build do boot atual e LEIAME, B0.7h)"
  - "tools/jogavel.py:440-465 (build antes e depois do recreate, lida pelo fim, B0.7h)"
  - "tools/jogavel.py:1523-1611 (coletar e a reconstrução automática, B0.7h)"
  - "backup:../2026-10-12/coleta-g7-candidato-9/docker-logs-reconstruido.LEIAME.txt (log vazio e reconstrução por --tail)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:452-703 (tipos de evento)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:641-670 (a volta à mão que o voltar substitui)"
  - "docs/runbooks/versoes-conhecidas.md:400-416 (manifesto do plugin de captura)"
  - "config.py:50-99 (compose_files e data/servidor.json, P1.2)"
  - "tools/jogavel.py:1724-1782 (vanilla on, off e status, P1.2)"
  - "docker-compose.vanilla.yml:1-31 (o que o override mascara)"
atualizado: 2026-10-16
---

# Voltar ao jogável

> **Para quem:** o Victor, sem agente nenhum, e o papel servidor.
> **Card:** B0.7: `status`, `voltar` e `atualizar` (fatia 1) e a [janela](#janela) (`abrir`,
> `fechar`, `vigiar`; fatia 2). A pasta do plugin pelo manifesto, o `marcar`, a RCON e o
> `coletar` são do B0.7b.

Voltar ao jogável é um comando: ele devolve o checkout principal à última tag `jogavel-*` e
recria o container só se a infra mudou. Rode do checkout principal, no PowerShell ou no Git
Bash:

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py voltar --seco
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py voltar
```

- O `--seco` mostra, com o prefixo `[seco]`, o que mudaria (switch, `docker logs`, recreate) e
  não muda nada. O que só lê roda: `git diff`, `docker compose config` e a lista de processos.
- `--tag X` escolhe outra tag. O recreate do `voltar` mantém o estado da
  [válvula vanilla](#válvula-vanilla): ele usa os mesmos `-f`.

## Quando ele recusa

Só com partida em curso (saída 3):

- `current.jsonl` com evento de round há menos de 2 min: todo tipo que o plugin grava fora o
  `snapshot` (`round_start`, `freeze_end`, `round_end`, `round_stats`,
  `round_officially_ended`, `player_death`, `player_hurt`, `player_blind`, bomba). A idade soma
  o mtime do arquivo e os snapshots gravados depois do último evento (2 por segundo): a cauda
  de snapshots do fim da partida não conta. O `freeze_end` conta: um round sem dano nem
  flash dura até 115 s depois dele, e do `round_start` já seriam mais de 2 min;
- o `watcher.py` rodando (ingerindo);
- sem certeza sobre o watcher, recusa: a lista de processos falhou, ou há `python` sem linha
  de comando legível (só o `tasklist` respondeu: PowerShell falhou e o `wmic` não existe nesta
  máquina). Recusa mesmo com o `cs2.exe` aberto, que numa partida viva sempre está. Qualquer
  python aberto (o uvicorn, por exemplo) basta: feche-o ou use `--agora`.

CS2, TUI e `start_match` abertos só geram aviso com o que fechar. Feche-os antes do recreate:
o `start_match` sobe o container quando o acha parado e competiria com a volta.

Numa emergência, `voltar --agora` segue mesmo com partida em curso, depois de você digitar
`VOLTAR`. Qualquer outra resposta não muda nada (saída 5). Com partida em curso ele não lê
`docker logs` (proibido nessa hora): a build "antes" sai como `não lida (partida em curso)`, o
log do container antigo se perde no recreate, e a build "depois" é lida normalmente.

## O que ele faz, na ordem

1. Salva `docker logs -t cs2-spike` em `logs/jogavel/<data>_<hora>-voltar/`, porque o
   recreate descarta o log do container antigo. A build do CS2 "antes" (`GC Connection
   established for server version N`) não sai desse arquivo: sai do log lido pelo fim, e só
   de linha com carimbo do StartedAt em diante, a do boot atual (B0.7h; veja
   [leitura pelo fim](#leitura-pelo-fim)). Com `--agora` e partida em curso, pula este passo.
2. Protege o `docker/match_config.spike.json`, que o `start_match` reescreve a cada partida:
   copia para a mesma pasta, tira do caminho (`git checkout --` se rastreado; apaga se não
   rastreado e a tag o rastreia) e, depois da troca, restaura a cópia se a tag o rastreia. Se
   a tag não o rastreia (depois do P1.6), a cópia fica só na pasta. Sem `git stash`.
3. `git switch --detach <tag>`.
4. Confere que `docker/pre.sh` não tem `\r`. Se tiver, para antes do recreate (saída 6) e
   imprime o comando de conserto; depois rode o que ele manda (`voltar --tag X --recriar`).
5. **Pasta do plugin de captura, pelo manifesto** (B0.7b, `2dee94b`). A
   `docker/plugins/Cs2TrackerEvents/` é ignorada pelo git e não volta com o switch. O `voltar`
   lê o sha256 da DLL na mensagem da tag (a linha `plugin Cs2TrackerEvents:` que o `marcar`
   grava) ou em `--plugin <sha256>` e compara a pasta com o manifesto da cópia em
   `C:/Users/Victor/cs2-tracker-backups/plugins/Cs2TrackerEvents/<sha256>/`. Se divergir, para
   o container, guarda o que havia em `plugin-antes/`, copia a da cópia e confere de novo;
   pasta trocada conta como infra no passo 6. Tag sem essa linha (anterior ao B0.7b): ele avisa,
   e a conferência é à mão, pelo [manifesto](versoes-conhecidas.md#manifesto-do-plugin-de-captura).
6. Se a infra difere entre o commit de antes e a tag (compose, `docker/plugins/` ou fonte de
   bind tirada de `docker compose config`), roda `docker compose up -d --force-recreate`,
   espera a linha do GC do boot novo, lida pelo fim (até 10 min), e imprime a build "depois".
   Se `docker compose config` falhar, todo arquivo mudado conta como infra. Sem infra
   diferente, não recria.

**Build mudou** (`ATENÇÃO: a build do CS2 mudou`): o SteamCMD atualizou o jogo no boot. São
duas variáveis, e o cliente do Victor precisa da mesma build. A build não volta por git.

O recreate só roda do checkout principal, resolvido a partir do próprio `tools/jogavel.py`:
numa worktree ou num clone avulso passado em `--raiz`, o compose montaria o volume vivo com os
binds de lá ([reconstruir-volume](reconstruir-volume.md)), e o `jogavel.py` recusa (saída 5).

## atualizar e status

- `jogavel.py status` só lê: HEAD, última tag `jogavel-*`, delta até a `origin/main` (sem
  fetch) e a infra dele, janela, preflight, `pre.sh`, runtime file, candidato e container.
- `jogavel.py atualizar [--seco]` traz a `origin/main` (fetch e `merge --ff-only`; do HEAD
  destacado, antes `switch main`). Precisa de preflight 0. Commit que toca infra só passa com
  janela aberta (preflight 4); sem ela, recusa (saída 5) e lista os arquivos. No fim imprime
  "Reabra a TUI e o uvicorn". Infra trazida na janela ainda pede o recreate do servidor.
  Se o `merge --ff-only` falhar depois do `switch main` (a main local divergiu), ele volta ao
  HEAD de antes e sai com 1; se nem a volta der, imprime onde o checkout ficou e o
  `git switch` para voltar.

## Janela

Só o papel servidor, do checkout principal (fora dele recusa, saída 5), e só depois da frase
do Victor, do "terminei" da trilha de bots ou do OK dele repassado pelo PM (AGENTS.md).
Todos aceitam `--seco`.

- `janela abrir --por "<frase literal>" [--teto 30]`: só com preflight 0 (3 recusa com saída 3)
  e sem marca nenhuma, nem vencida (saída 5). Cria `logs/janelas/ABERTA` com o mtime da
  abertura, o HEAD, o teto e o estado do container, e abre uma seção no
  `logs/janelas/<data>.md`. Teto padrão 45 min; na trilha de bots, 30. Renovar é fechar e
  abrir de novo, com novo OK: nada toca o mtime da marca depois da abertura.
- `janela vigiar [--intervalo 30]`: deixe rodando em segundo plano. A cada ≤30 s lista os
  processos e o `docker ps`. O `current.jsonl` não conta: na janela quem escreve nele é o
  servidor.
  - Processo do Victor (`cs2.exe`, TUI, `start_match` ou `watcher` com linha legível, ou a
    lista de processos que falha toda): aborta no mesmo ciclo (saída 3), registra e, se o
    checkout mudou na janela, roda o `voltar --tag <HEAD da abertura>`, que recusa com partida
    em curso. VPK, volume e pasta do plugin voltam pelo rollback do runbook do passo. A marca
    fica até o `fechar`.
  - `python` sem linha de comando legível (B0.7e) é quase sempre um python saindo, inclusive os
    do próprio servidor (janela 0 de 02/10). Ele só aborta se repetir: o ciclo espera 4 s e
    relê pelo mesmo método, com 6 s de teto (no máximo 10 s entre as leituras). Abortam o
    mesmo PID ainda vivo ou outro python sem linha; sumiu, o registro diz `sinal sem
    confirmação` e a vigília segue. Releitura que falha conta como o Victor jogando.
  - Não conta python sem linha que descende do `vigiar` ou do processo que abriu a janela: o
    `abrir` grava na marca a cadeia de ancestrais dele (PID e hora de criação), e a raiz é o
    ancestral mais próximo comum ao `abrir` e ao `vigiar` (o agente servidor). Explorer,
    terminal do Windows e afins não valem como raiz. Sem a árvore (só `wmic`/`tasklist`, ou
    marca sem ela), vale só a confirmação.
  - **Depois de um aborto só cabe `janela fechar`**: nada de seguir o passo, de rodar o
    `vigiar` de novo nem de abrir outra janela por cima. A janela acabou; outra só com nova
    frase do Victor.
  - Nenhuma chamada do ciclo espera mais que 20 s: a lista de processos (30 s fora do ciclo)
    cai para 20 s, e o `docker ps` espera 10 s. Com o docker pendurado (27/09), a checagem
    dos processos do Victor segue a cada ≤30 s. O `voltar` do aborto já está fora do ciclo e
    usa os timeouts dele (o recreate espera até 15 min).
  - `docker ps` que estoura os 10 s vira `estado do container desconhecido` no registro, uma
    vez quando entra e uma quando volta a responder, e a vigilância segue. Desconhecido não
    conta como de pé: passou de 5 min assim, avisa como o container parado. No `fechar`,
    desconhecido não passa no item do container.
  - O tempo vem do relógio de parede contra o mtime da marca, não da soma dos ciclos. Ciclo
    acima de 30 s (um `docker` preso esperando aprovação, como em 27/09) vai para o registro
    com a chamada mais lenta, e o próximo ciclo começa sem esperar.
  - Avisa uma vez quando faltam 5 min para o teto e quando o container, de pé na abertura,
    passa de 5 min parado. No teto sai com 7 (janela vencida). Marca apagada: sai com 0.
- `janela fechar --feito matchzy --feito cvars --feito sha256`: checklist de fechamento (G6).
  Confere sozinho o container (de pé, ou parado como já estava na abertura) e o `pre.sh` sem
  `\r`. Os outros três são à mão até o B0.7b, e cada um só passa com o `--feito` dele:
  - `matchzy`: `get5_status` com `"gamestate":"none"` (`css_endmatch` ou restart), pela RCON;
  - `cvars`: pela RCON, na [referência do fechamento](smoke-partida-de-bots.md#referência-do-fechamento)
    (`mp_ignore_round_win_conditions`, `sv_hibernate_when_empty`, `bot_quota`,
    `bot_join_after_player`);
  - `sha256`: sha256 dos arquivos montados, dentro do container, igual ao checkout.

  Item faltando: a marca fica e ele diz o que falta (saída 5). Tudo ok: linha de fechamento no
  registro e marca apagada.

## Coletar

`jogavel.py coletar [--destino D]`, do checkout principal, com preflight 0 e sem janela: grava
em `D` (ou `logs/jogavel/<data>_<hora>-coletar/`) o `docker-logs.txt` (`docker logs -t --since
<StartedAt>`), o `head.txt`, os dois config-hash e o sha256 dos montados, dentro do container e
no checkout. Quem julga o G7 é o QA, pelo `evidencia_partida.py`.

Depois de gravar tudo, ele confere o log salvo (B0.7f). Vazio (0 bytes ou só espaço), ou sem
nenhuma linha carimbada do StartedAt em diante, é log incompleto. Linha sem carimbo não conta:
com `-t` toda linha vem carimbada, e sem carimbo não se prova que é desta subida. O
`docker-logs.txt` fica como está, o vazio também, porque ele é a evidência da falha.

Com o log incompleto, ele o reconstrói sozinho pelo fim (B0.7h), só lendo: grava ao lado o
`docker-logs-reconstruido.txt` e o `docker-logs-reconstruido.LEIAME.txt` (os N lidos, o
intervalo coberto, por que parou, as fronteiras e as perdas) e confere o reconstruído pela
mesma regra. Tem linha do StartedAt em diante: sai com 0 e um `AVISO` que manda julgar o G7
pelo reconstruído e citar o LEIAME; se a leitura não chegou a uma linha de antes do StartedAt
(nem ao começo do json-file), um segundo `AVISO` diz que o começo da subida pode faltar. Só se
a reconstrução também falhar (nada desta subida, ou `docker logs --tail` com erro) ele sai com
8 e `coleta INCOMPLETA`, e aí vale a [reconstrução à mão](#coleta-incompleta).

### Leitura pelo fim

O `docker logs --tail N` conta N linhas de trás para a frente no json-file e decodifica para a
frente dali; numa entrada corrompida ele para em silêncio, com código 0. A saída é então só o
trecho do segmento legível (o pedaço entre duas paradas bruscas) em que o N caiu, até o fim
dele, e a última linha da saída diz que segmento é. O `jogavel.py` dobra o N a partir de 1 até
a última linha mudar (uma fronteira), acha por busca binária o maior N que ainda lê o segmento
inteiro e segue para o segmento de antes; um N que cai bem na entrada corrompida devolve nada,
e ela conta como perda. Para na primeira linha de antes do StartedAt (o boot desta subida está
inteiro), no começo do json-file ou no teto de 1048576 linhas. A união das leituras, sem
duplicata e na ordem do carimbo, é o reconstruído.

A mesma leitura dá a build do CS2 do `recriar`, do `voltar` e do `restaurar`, antes e depois do
recreate: a última linha `GC Connection established` com carimbo do StartedAt em diante. Lido
do começo, o log mostraria a de um boot de antes da primeira parada brusca (na janela do B1.9b,
"antes 2000924" quando o boot era da 2000930). O `docker-logs.txt` que o `recriar` salva antes
do recreate continua sendo o `docker logs -t` lido do começo.

### Coleta incompleta

Em 12/10 o `docker-logs.txt` saiu com 0 bytes e código 0: o json-file do container tinha uma
entrada corrompida depois de cada parada brusca (05/10 e 06/10, sem linhas de desligamento), e
o `docker logs` lendo para a frente (sem `--tail`, ou com `--since`) para em silêncio na
primeira delas. Não julgue o G7 por esse log; reconstrua-o lendo do fim. Desde o B0.7h o
`coletar` faz isso sozinho ([leitura pelo fim](#leitura-pelo-fim)); os passos abaixo são para
quando ele sai com 8 mesmo assim, com a reconstrução automática falha.

1. Não apague nada da pasta da coleta e não recrie o container: o recreate descarta o
   json-file, e com ele as linhas que ainda se leem.
2. Com preflight 0 (é a mesma leitura do `coletar`, sem janela), no Git Bash e na pasta da
   coleta, leia o fim do log em tamanhos crescentes:

   ```
   for n in $(seq 100 100 16000); do docker logs -t --tail $n cs2-spike > tail-$n.txt 2>&1; done
   ```

   O PowerShell 5.1 grava o `>` em UTF-16: use o Git Bash. Onde a leitura muda de segmento
   legível (uma fronteira), repita de 1 em 1 em volta do N dela para não perder linha.
3. Junte as leituras sem duplicata e na ordem do carimbo. A linha inteira, com o carimbo de
   largura fixa do `-t`, é a chave e também a ordem:

   ```
   C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -c "import glob; linhas = {l for f in glob.glob('tail-*.txt') for l in open(f, encoding='utf-8')}; open('docker-logs-reconstruido.txt', 'w', encoding='utf-8', newline='\n').writelines(sorted(linhas))"
   ```

4. Confira que o reconstruído tem linhas do StartedAt em diante (o boot desta subida) e
   escreva ao lado um `docker-logs-reconstruido.LEIAME.txt`: os N lidos, o intervalo coberto,
   as fronteiras e as perdas conhecidas (a entrada corrompida de cada fronteira). Linhas com o
   mesmo carimbo podem sair em ordem diferente da original.
5. O QA julga o G7 pelo reconstruído e cita o LEIAME. O modelo é a coleta de 12/10, em
   `C:/Users/Victor/cs2-tracker-backups/2026-10-12/coleta-g7-candidato-9/`.

## Válvula vanilla

Card P1.2. Bots com IA e mira vanilla, sem plugin de bot do CSSharp, como antes da trilha de
bots (`jogavel-2026-09-26`), mas com o código, a CSSharp e a captura de hoje. Até o P1.2 era
`voltar --tag jogavel-2026-09-26`, que voltava o código inteiro; sem janela, essa volta
continua valendo numa emergência.

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py vanilla status
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py vanilla on --seco
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py vanilla on
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py vanilla off
```

- `vanilla on|off` é comando do servidor, só na janela (como o `recriar`): salva os logs,
  para se o `pre.sh` tem `\r`, grava `"vanilla": true|false` em `data/servidor.json` (ignorado
  pelo git; escrita atômica, as outras chaves ficam) e roda `docker compose up -d
  --force-recreate`. Depois, o G6 do runbook do passo.
- Grava e recria juntos de propósito: o estado gravado sem recreate deixaria o container
  diferente do checkout, e o `start_match`, achando o container parado, rodaria o `compose up
  -d`, que recria fora da janela.
- `--seco` mostra o estado que gravaria e o `docker compose` com os `-f`, sem gravar nem recriar.
- `vanilla status` e o `status` só leem. `data/servidor.json` ausente, ilegível, que não é
  objeto ou com `vanilla` que não é `true`/`false` conta como off, com aviso.
- A lista de `-f` sai só de `config.compose_files()`: o `docker-compose.yml` e, ligado, o
  `docker-compose.vanilla.yml` depois dele. Usam essa lista o `compose up -d` do `start_match`
  (container parado), o `recriar`, o `voltar`, o `coletar` (`compose config` e config-hash) e o
  `status`. Desligado, o argv é o de antes do P1.2: `-f docker-compose.yml` no `start_match` e
  sem `-f` no `jogavel.py`.
- O override cobre com `./docker/plugins/_empty` o BotAI, o BotAimImprover, o BotRandomizer, o
  BotBuy, o BotState e o NadeSystem; RayTrace e BotHider o base já mascara. A MatchZy e a
  captura (Cs2TrackerEvents) ficam: sem a captura a partida não é ingerida.
- Ligado num checkout sem o override (um `voltar` para tag anterior ao P1.2), sobe só o base,
  com aviso. Um `docker compose up` digitado à mão, sem os `-f`, também sobe sem o override: na
  janela, recrie pelo `jogavel.py`.

## Saídas

| Código | Quer dizer |
|---|---|
| 0 | ok |
| 1 | falha (tag inexistente, git ou docker falhou) |
| 2 | uso errado |
| 3 | partida em curso, preflight que não libera o `atualizar` ou o `janela abrir`, vigília abortada por processo do Victor |
| 5 | recusado por regra: infra sem janela, confirmação errada, branch que não é a `main`, recreate ou janela fora do checkout principal, janela já aberta ou sem `--por`, checklist pendente |
| 6 | `docker/pre.sh` com `\r` depois da troca |
| 7 | janela vencida (teto da marca ou 45 min pelo mtime) |
| 8 | coleta incompleta: `docker-logs.txt` vazio ou sem linha do StartedAt em diante, e a reconstrução pelo fim também; veja [Coleta incompleta](#coleta-incompleta) |
