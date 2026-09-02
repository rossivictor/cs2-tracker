# CS2 Tracker — Match Watcher

Monitora o log de um servidor dedicado do CS2 em tempo real, detecta início
e fim de partida, e dispara gravação de demo (GOTV) automaticamente via
RCON. Ao final de cada partida, chama um hook onde depois entra o parser
(awpy) e a gravação no banco.

## Por que servidor dedicado (e não "Practice with Bots")

RCON **não funciona** em listen server / partida offline via menu do CS2 —
confirmado via `netstat` (só abre UDP, nunca o TCP que RCON precisa), mesmo
com `rcon_password` e `-usercon` configurados. É limitação da engine, não
erro de configuração. Por isso este projeto assume um servidor dedicado
local (via SteamCMD), que expõe RCON de verdade.

## Estrutura deste repositório

```
watcher.py                                       # o script principal
server-configs/cfg/server.cfg                    # vai pro servidor dedicado
server-configs/cfg/gamemode_competitive_server.cfg  # vai pro servidor dedicado
demos/                                           # scratch local (git-ignored)
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

## Setup — watcher (a cada sessão de teste)

```bash
pip install rcon
python watcher.py --log "C:/cs2server/game/csgo/console.log" --demo-dir ./demos --rcon-host 127.0.0.1 --rcon-password sua_senha --debug
```

Conecte no servidor pelo client normal do CS2 (globinho → Servidores →
Rede Local) e jogue. O watcher deve mostrar `[CMD] tv_record ...` sem erro
no início da partida, e `[CMD] tv_stoprecord` com o placar no final.

Use `--debug` sempre que for calibrar os regexes em `PATTERNS` — ele
imprime toda linha de log relacionada a `Match_`/`Round_`/`Game Over`/
`MatchStatus` que ainda não bateu com nenhum padrão.

Use `--print-only` como fallback manual (imprime o comando em vez de
mandar via RCON) se o RCON falhar por outro motivo além dos já cobertos
aqui.

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
