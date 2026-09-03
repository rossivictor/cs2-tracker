# CS2 Tracker — Match Watcher

Monitora o log de um servidor dedicado do CS2 em tempo real, detecta início
e fim de partida, dispara gravação de demo (GOTV) automaticamente via
RCON e, ao final de cada partida, parseia o `.dem` com awpy e grava
rounds/kills/dano/posição num SQLite.

## Por que servidor dedicado (e não "Practice with Bots")

RCON **não funciona** em listen server / partida offline via menu do CS2 —
confirmado via `netstat` (só abre UDP, nunca o TCP que RCON precisa), mesmo
com `rcon_password` e `-usercon` configurados. É limitação da engine, não
erro de configuração. Por isso este projeto assume um servidor dedicado
local (via SteamCMD), que expõe RCON de verdade.

## Estrutura deste repositório

```
watcher.py                                       # tail do log + RCON/GOTV
parser.py                                        # awpy -> SQLite
requirements.txt                                 # awpy, rcon (Python <3.14)
server-configs/cfg/server.cfg                    # vai pro servidor dedicado
server-configs/cfg/gamemode_competitive_server.cfg  # vai pro servidor dedicado
demos/                                           # .dem já parseados, arquivados (git-ignored)
cs2_tracker.db                                   # SQLite gerado pelo parser (git-ignored)
```

### Onde cada arquivo satélite deve ir

Esses dois `.cfg` **não rodam a partir daqui** — copie-os para dentro da
instalação do servidor dedicado (não do client normal do CS2):

| Arquivo neste repo | Destino |
|---|---|
| `server-configs/cfg/server.cfg` | `<instalação do servidor dedicado>/game/csgo/cfg/server.cfg` |
| `server-configs/cfg/gamemode_competitive_server.cfg` | `<instalação do servidor dedicado>/game/csgo/cfg/gamemode_competitive_server.cfg` |

**Antes de copiar `server.cfg`**, troque `CHANGE_ME_LOCAL_ONLY` por uma
senha real — o valor no repo é só um placeholder (não versionamos senha
real de propósito).

`gamemode_competitive_server.cfg` existe como arquivo separado (e não
dentro do `server.cfg`) por um motivo específico: o CS2 executa o config
interno do modo competitivo *depois* do `server.cfg`, então qualquer
`bot_quota`/`bot_difficulty`/etc. colocado no `server.cfg` diretamente é
sobrescrito. `gamemode_competitive_server.cfg` é o hook que a engine chama
*depois* desse config interno, dando a última palavra pra essas cvars.

## Setup — servidor dedicado (uma vez)

1. Baixe o SteamCMD: https://developer.valvesoftware.com/wiki/SteamCMD

2. Baixe os arquivos do servidor dedicado (pasta separada do client normal):
   ```bash
   steamcmd.exe +force_install_dir C:/cs2server +login anonymous +app_update 730 validate +quit
   ```

3. Copie os dois arquivos de `server-configs/cfg/` pra
   `C:/cs2server/game/csgo/cfg/` (ajustando a senha, como descrito acima).

4. Suba o servidor:
   ```bash
   C:/cs2server/game/bin/win64/cs2.exe -dedicated -console -usercon -condebug -conclearlog +map de_mirage +exec server.cfg +ip 0.0.0.0
   ```
   - `+ip 0.0.0.0` é obrigatório: sem isso o RCON bind fica preso no IP da
     rede local (ex.: `192.168.x.x`) em vez de aceitar `127.0.0.1`.
   - `-condebug -conclearlog` geram o `console.log` que o watcher lê, em
     `game/csgo/console.log` (caminho fixo, não customizável na Source 2).

5. Confirme que o TCP abriu (não só UDP):
   ```powershell
   netstat -ano | findstr "27015"
   ```
   Espera `TCP 0.0.0.0:27015 ... LISTENING`.

## Setup — ambiente Python (uma vez)

O `parser.py` usa awpy 2.x, que exige Python `>=3.11,<3.14`. Se seu Python
do sistema for 3.14+ (`python --version`), instale o 3.13 à parte (dá pra
coexistir, via `py -0` pra conferir versões instaladas) e crie um venv só
pro projeto:

```bash
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Todo comando abaixo (`watcher.py` e `parser.py`) roda através desse
`.venv`, não do Python do sistema.

## Setup — watcher (a cada sessão de teste)

```bash
.venv\Scripts\python.exe watcher.py --log "C:/cs2server/game/csgo/console.log" --server-demo-dir "C:/cs2server/game/csgo" --demo-dir ./demos --player seu_nick_in_game --rcon-host 127.0.0.1 --rcon-password sua_senha --debug
```

Conecte no servidor pelo client normal do CS2 (globinho → Servidores →
Rede Local) e jogue. O watcher deve mostrar `[CMD] tv_record ...` sem erro
no início da partida, e no final: `[CMD] tv_stoprecord`, o placar, o
resumo do parser (`[PARSER] match_id=...`), a demo arquivada em
`./demos/` e `[REPORT] N partida(s) — relatório gerado em ...` — o
`report.html` é regenerado automaticamente a cada partida, não precisa
rodar nada manualmente depois.

`--server-demo-dir` é a pasta `game/csgo` do servidor **dedicado** (onde
o GOTV grava o `.dem` de verdade) — normalmente a mesma pasta de `--log`.
`--player` é o seu nick in-game, usado pra filtrar a posição/heatmap só
pra você (bots não entram nessa tabela de qualquer forma — o awpy só
trackeia clientes conectados de verdade em `ticks`).

Use `--debug` sempre que for calibrar os regexes em `PATTERNS` — ele
imprime toda linha de log relacionada a `Match_`/`Round_`/`Game Over`/
`MatchStatus` que ainda não bateu com nenhum padrão.

Use `--print-only` como fallback manual (imprime o comando em vez de
mandar via RCON) se o RCON falhar por outro motivo além dos já cobertos
aqui.

## Parser / banco de dados

`parser.py` lê o `.dem` com awpy e grava em `cs2_tracker.db` (SQLite,
git-ignored):

| Tabela | Conteúdo |
|---|---|
| `matches` | 1 linha por partida — mapa, placar, duração, caminho do demo, nome do jogador |
| `rounds` | round a round — vencedor, motivo, plant de bomba |
| `kills` | quem matou quem, arma, headshot, distância (`attacker_is_human`/`victim_is_human` marcam se é você) |
| `damages` | dano por evento, com os mesmos flags `*_is_human` (dá pra computar ADR agrupando por round) |
| `player_positions` | posição tick a tick — **só do jogador humano** (`--player`) |

**TODO conhecido**: economia/compra (dinheiro gasto por round) fica de
fora por ora — o awpy 2.0.2 não expõe um dataframe de compra com valor
monetário, só o evento `item_pickup` sem o dado de dinheiro. Revisitar se
uma versão futura do awpy cobrir isso.

Pra reprocessar uma demo manualmente (sem precisar do watcher rodando):
```bash
.venv\Scripts\python.exe parser.py "C:/cs2server/game/csgo/20260902_202208_de_mirage.dem" --map de_mirage --score-ct 1 --score-t 13 --minutes 19 --player seu_nick_in_game --db cs2_tracker.db
```

## Relatório

`report.py` lê o `cs2_tracker.db` e gera um único `.html` estático local
(sem servidor, sem build, sem fetch — os dados vão embutidos como JSON
inline no arquivo). O `watcher.py` já regenera esse arquivo sozinho ao
fim de cada partida; rode manualmente só se quiser reprocessar fora
desse fluxo:

```bash
.venv\Scripts\python.exe report.py --db cs2_tracker.db --out report.html --open
```

O `.html` tem duas telas, navegadas em JS puro via `location.hash` (sem
recarregar a página):

- **Dashboard** (`report.html`): cards agregados (K/D, ADR, HS%, round
  win rate), gráfico de evolução por partida, e a lista de partidas —
  clique numa linha pra abrir o detalhe.
- **Detalhe da partida** (`report.html#match-<id>`): quadro de armas
  (kills/headshots/dano por arma), linha do tempo round a round (quem
  venceu, motivo, plant de bomba, seu K/D naquele round) e o feed
  cronológico de kills/mortes.

Round win rate compara o lado do jogador humano em cada round (via
`player_positions`) com `rounds.winner_side`, em vez de só olhar o
placar final — necessário porque os lados trocam na metade da partida.

Toda estatística (cards, quadro de armas, linha do tempo, feed) vem em
**3 variantes** — Geral / CT / TR —, trocadas por um toggle no topo da
página, tanto no dashboard quanto no detalhe da partida. CT + TR sempre
somam exatamente igual a Geral. Se você só jogou 1 ou 2 rounds de um
lado numa partida (ex.: virada de metade cedo), o toggle daquele lado
mostra só esses rounds — armas, linha do tempo e feed todos recortados
igual.

**Limitação conhecida**: o quadro de armas pode separar a mesma arma em
duas linhas (ex.: "M4A1-S" com kills e "M4A4" com dano, ou vice-versa) —
o evento de kill e o de dano do CS2 às vezes usam nomes internos
diferentes pra variantes com/sem silenciador. Os números de cada linha
continuam corretos, só não ficam somados numa única arma.

## Gotchas já resolvidos (documentados também no docstring de `watcher.py`)

- **`log on`**: sem isso, o servidor não escreve `World triggered "..."`
  nem `Game Over: ...` no log — nem aparecem como linha não reconhecida,
  simplesmente não existem no arquivo.
- **`record`/`stop` não existem em servidor dedicado**: são comandos de
  client. Gravação server-side é via GOTV (`tv_record`/`tv_stoprecord`),
  que é o que o script usa.
- **Auto-exec de `.cfg` no CS2 é instável**: force com `+exec server.cfg`
  na linha de comando em vez de confiar no auto-load.
- **`con_logfile` não existe mais** (era CS:GO/Source 1) — o caminho do
  log é sempre `game/csgo/console.log`, sem opção de customizar.
