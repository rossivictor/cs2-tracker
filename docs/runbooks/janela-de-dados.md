---
tipo: runbook
status: rascunho
fontes:
  - "tools/reingest_events.py:38 (NAME_RE: só events_<matchid>_map<N>[__<utc>] entra)"
  - "tools/reingest_events.py:43-56 e 101-104 (banco real só com --confirmo-banco-real)"
  - "tools/reingest_events.py:107 (reprocessa TODO events_*.jsonl da --events-dir, com force=True na 155)"
  - "tools/reingest_events.py:113 (init_db grava as migrações, até no --dry-run)"
  - "tools/reingest_events.py:140-144 (nick padrão: o player_name da 1ª linha do banco; Jogador impresso)"
  - "tools/reingest_events.py:148-155 (partida nova: map None e o --series-num-maps)"
  - "parser.py:1275 e 1294-1302 (partida nova: played_at = datetime.now(); demo_path = caminho do arquivo lido)"
  - "identity.py:30-61 (--match-config dá a SteamID pelo nick; arquivo ausente vira {} e o reingest recusa)"
  - "tools/ficha_orfas.py:41-42, 87-88 e 455-472 (cópia mode=ro, sha256 antes e depois, órfãs x já no banco)"
  - "tools/backup.py:9-11, 64, 115 e 237 (cópia pela API de backup, integrity_check, nome .backup.db, destino novo)"
  - "tools/jogavel.py:1094-1181 (janela abrir e fechar; checklist matchzy, cvars e sha256)"
  - "tools/hooks/guarda.py:32-37 (escrita em cs2_tracker.db e em docker/events-live/** barrada para todo agente)"
  - "tools/preflight.py:17-21 e 71 (o que é Victor jogando; 45 min de janela)"
  - "config.py:38 e 44 (./cs2_tracker.db e ./docker/events-live)"
  - "start_match.py:100-117 (o orphan_<utc> é o current.jsonl preservado; o carimbo é a hora da partida SEGUINTE)"
  - "watcher.py:484-526 (o nome que a partida teria: events_<matchid>_map<N>, com map e series_num_maps do match_config)"
  - "tools/evidencia_partida.py:114-116 (o watcher grava played_at uns 10 s depois do MAP ENDED)"
  - "backup:../2026-11-04/ficha-orfas/ficha-orfas.md (a ficha das 10, 04/11 19:13: sha256, mapa, placar e data de cada uma)"
  - "backup:../2026-11-04/partida-k19-b115/MANIFESTO.txt (o backup de 04/11 18:39: banco integrity_check ok, 72 partidas, 81 arquivos em events-live)"
  - "backup:../2026-11-04/partida-k19-b115/cs2_tracker.backup.db (lido numa cópia mode=ro: colunas de matches, maior id 77, nenhum demo_name events_105_*)"
  - "backup:../2026-11-04/partida-k19-b115/docker/events-live/ (nenhum events_105_*; os 10 arquivos com os sha256 da ficha)"
  - "backup:../2026-11-04/partida-k19-b115/logs/jogavel/2026-11-04_121114-vanilla-on/docker-logs.txt:21446, 24397 e 24399 (changelevel de_ancient; MAP ENDED do matchid 105, mapa 0; NumMaps 1)"
  - "backup:../2026-11-04/partida-k19-b115/logs/partidas/partida_20261028T004916Z.log:1 (o start_match das 21:49 preservou o orphan_20261028T004916Z)"
atualizado: 2026-11-04
---

# Janela de dados: ingerir a órfã aprovada na Q10 e arquivar as outras

Roteiro do papel servidor para pôr no banco real do jogo a partida que o Victor aprovou na Q10
(card 32): `orphan_20261028T004916Z.jsonl`, de_ancient 13x3. As outras 9 são ARQUIVAR. Nada aqui
mexe em container, volume, RCON de partida ou checkout: a janela escreve só no `cs2_tracker.db`,
e só no passo 7.

**Status: rascunho, não executável até o fim.** Quatro passos não têm comando no repo (lacunas
L1 a L4, no fim). Sem L3 não há volta do banco: **enquanto L1, L2 e L3 estiverem abertas, a janela
roda do passo 0 ao 6 (backup, ensaio em cópia, arquivo) e fecha sem o passo 7.** O QA confere as
premissas abaixo antes da primeira janela.

## Premissas (conferidas em 04/11 contra as cópias; a janela relê no passo 2)

| Premissa | Valor | Fonte |
|---|---|---|
| Banco real | `C:/Users/Victor/Projetos/cs2-tracker/cs2_tracker.db` (o padrão do `config.py`); é nele que o watcher grava: a cópia de 18:39 já tem a partida de 18:28 (id 77, `events_107_map0`) | `config.py:38`; MANIFESTO.txt e a cópia do banco |
| Colunas de `matches` que o passo 7 grava | `demo_name`, `map`, `played_at`, `score_mine`, `score_theirs`, `outcome`, `series_num_maps`, `source`, `demo_path` (e as tabelas filhas `rounds`, `kills`, `damages`, `player_positions`, `player_blinds`, `round_stats`) | `parser.py:1294-1302`; `PRAGMA table_info(matches)` na cópia |
| Pasta da captura | `docker/events-live/`, montada no container | `config.py:44`; `docker-compose.yml:102` |
| Nome do arquivo aprovado | `orphan_20261028T004916Z.jsonl`, 2951242 bytes, sha256 `869abda9609642c74638e32c3e843c5f3ab500f1299c266da71e63e352ca0560` | ficha, seção do arquivo; `sha256sum` na cópia |
| Nome que o reingest aceita | `events_105_map0.jsonl` | `tools/reingest_events.py:38` |
| matchid 105 é o desta partida | `MAP ENDED ... matchid: 105 currentMapNumber: 0` às 22:50:25Z de 27/10 (19:50:25 em Brasília), 22 s antes do último evento do arquivo (mtime 19:50:47 -03:00); `changelevel "de_ancient"` às 22:25:12Z, na carga dessa partida | docker-logs.txt:21446 e 24397; mtime da cópia |
| matchid 105 livre | nenhum `demo_name` `events_105_*` no banco (ids 75 e 76 são o 106) e nenhum `events_105_*` em `events-live`; o MatchZy já passou do 105 (107 em 04/11), então não o reusa | cópia do banco; listagem da cópia de `events-live` |
| Série | MD1: `MATCH ENDED, remainingMaps: 0, NumMaps: 1` | docker-logs.txt:24399 |
| Mapa | `de_ancient` (o changelevel acima, e a ficha: 3691 callouts exclusivos de de_ancient) | docker-logs.txt:21446; ficha |
| played_at certo | `2026-10-27T19:50:47` (hora local, como o watcher grava: o mtime do último evento; o carimbo do nome, 00:49Z de 28/10, é a hora do `start_match` seguinte) | ficha, linha "data"; `start_match.py:100-117`; `tools/evidencia_partida.py:114-116` |
| Placar esperado | 13 x 3 (win, fonte rounds); CT 11 : TR 5; 17 rounds, 122 kills, 582 damages, 28597 posições, 129 flashes, 150 round_stats | ficha; ensaio do card V1.4a numa cópia do backup de 18:39 |
| O que o reingest grava numa partida nova | `map` NULL, `played_at` = hora da janela, `demo_path` = o caminho lido (a pasta `ingerir/`), `series_num_maps` = `--series-num-maps` | `tools/reingest_events.py:148-155`; `parser.py:1275`; ensaio do card |
| As 9 a arquivar, por sha256 (16 primeiros) | `events_50_map0` a636bcc29ac043de · `orphan_20261015T164958Z` 6e4aa9215a474502 · `orphan_20261017T215938Z` 8692814aa0e1b26f · `orphan_20261019T185248Z` fa1ed6ab596e53ae · `orphan_20261023T222551Z` 3c13a11c31c903a0 · `orphan_20261026T165628Z` f28d07ebf0261bdd · `orphan_20261026T170007Z` d419ee2ede339a6e · `orphan_20261104T205651Z` dfdac4eb4d293237 · `orphan_20261104T210037Z` 4f937b6a739f9d67 | ficha; `sha256sum` na cópia |
| Pasta de arquivamento | `C:/Users/Victor/cs2-tracker-backups/<data da janela>/janela-de-dados/arquivo-orfas/`, fora do repo e fora da montagem | escolha deste runbook; `tools/backup.py:233-240` recusa destino dentro da origem pelo mesmo motivo |

**Nunca aponte o `reingest_events` para `docker/events-live/`.** Ele reprocessa todo
`events_*.jsonl` da pasta com `force=True` (`tools/reingest_events.py:107` e `155`): reescreveria as
70 partidas e inseriria o `events_50_map0`, que é ARQUIVAR. A `--events-dir` é sempre a pasta
`ingerir/`, com um arquivo só.

## Pré-condições

1. Frase do Victor, literal e com hora, no prompt do servidor: "pode mexer no servidor" (Q4,
   até 45 min). O PM confirma que ele fica no PC (servidor.md, Janela).
2. Preflight 0, nenhum dev ou QA de pé (AGENTS.md, lições da B0), trilho sem passo de infra
   pendente nesta janela.
3. O app web do Victor (porta 8000) fechado: nenhum preflight o detecta, e ele lê o banco. O PM
   pergunta; sem resposta, não siga.
4. L1, L2 e L3 com ferramenta (card próprio) para rodar o passo 7. Sem elas, pare no 6.

## Preparação do shell

```bash
export MSYS_NO_PATHCONV=1
RAIZ=C:/Users/Victor/Projetos/cs2-tracker; PY=C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe
BK="C:/Users/Victor/cs2-tracker-backups/$(date +%F)/janela-de-dados"; mkdir -p "$BK"
cp "$RAIZ/tools/preflight.py" "$BK/preflight.py"
printf 'RAIZ=%s\nPY=%s\nBK=%s\n' "$RAIZ" "$PY" "$BK" > "$BK/janela.vars"
```

Cada chamada recarrega com `. "C:/Users/Victor/cs2-tracker-backups/<data>/janela-de-dados/janela.vars"`.

## Procedimento

0. **Abrir.** `"$PY" "$RAIZ/tools/jogavel.py" janela abrir --por "<frase literal do Victor>"`: recusa
   sem preflight 0 e cria a marca e a seção no `logs/janelas/<data>.md` (`tools/jogavel.py:1103-1147`).
   Deixe `"$PY" "$RAIZ/tools/jogavel.py" janela vigiar` em segundo plano: TUI, `watcher`,
   `start_match` ou `cs2.exe` abortam a janela (voltar-ao-jogavel.md, Janela).
1. **Backup antes**, com o preflight 4:

   ```bash
   "$PY" "$RAIZ/tools/backup.py" --destino "$BK/backup-antes"
   ```

   Precisa sair 0 com `banco: copiado, integrity_check ok, matches <N>`. Anote o N e o sha256 do
   `cs2_tracker.backup.db` (no `MANIFESTO.json`) no registro. Saída diferente de 0: pare e feche.
2. **Reler as premissas** (só leitura, sobre a cópia do passo 1):

   ```bash
   E="$BK/backup-antes/docker/events-live"
   ls "$E" | grep -c '^events_105_'                                  # 0
   (cd "$E" && sha256sum events_50_map0.jsonl orphan_*.jsonl) > "$BK/orfas-antes.sha256"
   "$PY" "$RAIZ/tools/ficha_orfas.py" --db "$BK/backup-antes/cs2_tracker.backup.db" \
     --events-dir "$E" --saida "$BK/ficha-antes.md"
   ```

   **PARE** se: algum `events_105_*` existe; o sha256 do `orphan_20261028T004916Z.jsonl` não é o
   `869abda9…`; a ficha não traz as mesmas 10 órfãs da tabela (órfã nova fica para outra Q10);
   ou a ficha muda o mapa, o placar ou a data da aprovada. Do cabeçalho da ficha
   (`Humano: <nick>, SteamID terminada em <4 dígitos>`), anote o nick em `NICK=` e os 4 dígitos no
   registro (nunca a SteamID inteira).
3. **Cópia com o nome aceito**, a partir do backup, nunca do `events-live`:

   ```bash
   mkdir -p "$BK/ingerir"
   cp -p "$E/orphan_20261028T004916Z.jsonl" "$BK/ingerir/events_105_map0.jsonl"
   sha256sum "$BK/ingerir/events_105_map0.jsonl"                    # 869abda9…
   ```

   A pasta `ingerir/` fica para sempre: o `demo_path` da linha nova aponta para ela.
4. **Arquivo das originais** (as 10, a aprovada inclusive), fora do repo:

   ```bash
   mkdir -p "$BK/arquivo-orfas"
   (cd "$E" && cp -p events_50_map0.jsonl orphan_*.jsonl "$BK/arquivo-orfas/")
   (cd "$BK/arquivo-orfas" && sha256sum -c "$BK/orfas-antes.sha256")  # 10 OK
   ```

   Os originais continuam em `docker/events-live/` (L4).
5. **Ensaio numa cópia do banco**, que nunca é o backup:

   ```bash
   cp "$BK/backup-antes/cs2_tracker.backup.db" "$BK/ensaio.db"
   "$PY" "$RAIZ/tools/reingest_events.py" --db "$BK/ensaio.db" --events-dir "$BK/ingerir" \
     --player "$NICK" --match-config "$RAIZ/docker/runtime/match_config.spike.json" \
     --series-num-maps 1 | tee "$BK/reingest-ensaio.txt"
   ```

   Precisa mostrar `1 arquivo(s)`, `events_105_map0: não está no banco`, `Jogador: <NICK>` com a
   SteamID terminando nos 4 dígitos do passo 2, `Placar reconstruído: 13 x 3 (win, fonte=rounds);
   por lado CT 11 : TR 5` e `17 rounds, 122 kills, 582 damages`. Sem a SteamID (`[ERRO] Sem a
   SteamID do humano`): o `match_config` de runtime não tem o nick; pare.
6. **Conferir o ensaio:**

   ```bash
   "$PY" "$RAIZ/tools/ficha_orfas.py" --db "$BK/ensaio.db" --events-dir "$BK/ingerir" \
     --saida "$BK/ficha-ensaio.md"
   ```

   Precisa dar `0 órfã(s); 1 arquivo(s) já no banco` e banco `inalterado`. **Sem L1, L2 e L3, a
   janela termina aqui:** vá ao passo 10.
7. **Ingerir no banco real**, com o portão na mesma chamada:

   ```bash
   "$PY" "$BK/preflight.py" --raiz "$RAIZ"; c=$?; [ $c -eq 4 ] || { echo "JANELA FECHADA (preflight $c): não executei"; exit 1; }
   "$PY" "$RAIZ/tools/reingest_events.py" --db "$RAIZ/cs2_tracker.db" --confirmo-banco-real \
     --events-dir "$BK/ingerir" --player "$NICK" \
     --match-config "$RAIZ/docker/runtime/match_config.spike.json" --series-num-maps 1 \
     | tee "$BK/reingest-real.txt"
   ```

   A saída tem de ser a do ensaio, linha a linha, menos o `match_id=` (anote-o no registro).
   Diferente: pare e vá à Volta.
8. **Corrigir `map` e `played_at`** da linha nova para `de_ancient` e `2026-10-27T19:50:47`.
   **LACUNA L1 e L2: não há comando.** Até haver, a linha fica com `map` NULL e `played_at` da
   janela, e é por isso que o passo 7 não roda sem elas.
9. **Integridade e conferência**, numa cópia nova:

   ```bash
   "$PY" "$RAIZ/tools/backup.py" --destino "$BK/backup-depois"
   "$PY" "$RAIZ/tools/ficha_orfas.py" --db "$BK/backup-depois/cs2_tracker.backup.db" \
     --events-dir "$BK/ingerir" --saida "$BK/ficha-depois.md"
   ```

   O `MANIFESTO.txt` precisa de `integrity_check ok, matches <N+1>`, e a ficha, de `0 órfã(s); 1
   arquivo(s) já no banco`. Qualquer outra coisa: Volta.
10. **Fechar.** Nada no servidor mudou, mas o `fechar` pede o checklist (`tools/jogavel.py:1150-1181`):
    `"$PY" "$RAIZ/tools/jogavel.py" rcon "get5_status"` (`"gamestate":"none"`), as cvars da
    [referência do fechamento](smoke-partida-de-bots.md#referência-do-fechamento) pela mesma
    `rcon` e o sha256 dos montados pelo passo 11 do [b1.3](b1.3-cssharp-1.0.375.md) (os dois
    `sha256sum` do bloco "Inventário e arquivos montados"). Depois,
    `"$PY" "$RAIZ/tools/jogavel.py" janela fechar --feito matchzy --feito cvars --feito sha256`,
    registro fechado e `historico` no card (servidor.md, Board).

## Volta (restaurar o backup)

O backup que vale é o `$BK/backup-antes/cs2_tracker.backup.db`, com o sha256 do passo 1.
**LACUNA L3: não há comando que o devolva ao `cs2_tracker.db`.** O `tools/backup.py` só copia do
banco para fora, e a guarda barra `cp` sobre o `cs2_tracker.db` para todo agente
(`tools/hooks/guarda.py:32-37`; um `cp <backup> <RAIZ>/cs2_tracker.db` sai 2 com "é o banco
cs2_tracker.db"). Não contorne. Antes do passo 7, a volta é não fazer nada: o banco real não foi
tocado. Do passo 7 em diante, sem L3: pare, registre e o PM leva ao Victor.

**Aborto por processo** (o vigiar sai 3): antes do 7, nada a desfazer; registre e
`janela fechar`. Durante ou depois do 7: não mexa mais; registre o último passo completo e o PM
avisa o Victor.

## Lacunas de ferramenta (cada uma é card; nada aqui as contorna)

- **L1, played_at:** o reingest grava `datetime.now()` numa partida nova (`parser.py:1275`) e
  não tem flag de data (`tools/reingest_events.py:81-97`).
- **L2, map:** partida nova entra com `map` NULL (`tools/reingest_events.py:150`); não há
  `--map`. O watcher tira o mapa do `match_config` (`watcher.py:482-483`), que a órfã não tem.
- **L3, restauração do banco:** nenhum comando, e a guarda barra a cópia por cima (acima). O
  runbook `backup-e-restauracao` segue em Previstos no [README](README.md).
- **L4, tirar os originais de `docker/events-live/`:** a guarda barra `mv` e `rm` lá
  (`tools/hooks/guarda.py:32-37`). Enquanto ficam, a ficha continua listando as 10 e o
  `events_50_map0` casa o `NAME_RE`: o aviso de nunca apontar o reingest para a pasta vale até lá.

## Modelo do registro (`logs/janelas/<data>.md`, depois das linhas do `janela abrir`)

```
- Passo: janela de dados (janela-de-dados.md) · órfã orphan_20261028T004916Z → events_105_map0
- Backup antes: backup-antes/ · matches <N> · sha256 <…> · integrity_check ok
- Premissas relidas: events_105_* 0 · 10 sha256 = tabela · ficha-antes = ficha de 04/11 · SteamID …<4>
- Arquivo: arquivo-orfas/ · 10 OK
- Ensaio: reingest-ensaio.txt · 13 x 3 · ficha-ensaio 0 órfãs, 1 no banco
- Banco real: <não tocado: L1/L2/L3 abertas | match_id <id> · reingest-real.txt = ensaio>
- Depois: backup-depois/ · matches <N+1> · integrity_check ok · ficha-depois 0 órfãs, 1 no banco
- Fechamento: get5_status none · cvars = referência · sha montados = checkout · ABERTA removida
```
