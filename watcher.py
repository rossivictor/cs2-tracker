#!/usr/bin/env python3
"""
CS2 Tracker — Match Watcher
=============================
Monitora o log do CS2 em tempo real (tail -f), detecta início e fim de
partida e dispara tv_record/tv_stoprecord (GOTV) automaticamente. Ao
final de cada partida, chama um hook (on_match_finished) onde depois
plugamos o parser (awpy) e a gravação no banco.

Requisitos (rode a partir do .venv do projeto — awpy exige Python <3.14):
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt

IMPORTANTE — RCON só funciona em servidor DEDICADO:
    Listen server (client hospedando partida local/offline com bots, via
    "Practice with Bots" do menu) NUNCA abre o listener TCP de RCON no
    CS2, mesmo com rcon_password e -usercon configurados — confirmado
    via netstat (só aparece UDP, nunca TCP, na porta do jogo). Não é bug
    de configuração, é limitação do modo listen server nessa engine.
    Pra RCON funcionar de verdade, suba um servidor dedicado (SteamCMD,
    app 730, `cs2.exe -dedicated`) e conecte nele como client normal
    (`connect 127.0.0.1:27015`).

    Além disso, em servidor dedicado o comando de client `record`/`stop`
    não existe ("Can't record on dedicated server.") — a gravação
    server-side é feita via GOTV: `tv_enable 1` uma vez no startup, e
    depois `tv_record <nome>` / `tv_stoprecord` por partida (é o que
    este script manda).

Setup necessário no servidor:
    1. Habilite o log em arquivo via opção de inicialização:
         -condebug -conclearlog -usercon
       Não existe cvar pra customizar nome/caminho do arquivo na Source 2
       (con_logfile era do CS:GO/Source 1 e foi removido — o CS2 nem
       reconhece o comando). Com -condebug o log sempre vai parar, sem
       exceção, em:
         <install>/game/csgo/console.log

    2. No server.cfg (não confie em autoexec.cfg pra servidor dedicado —
       o auto-exec de cfg no CS2 é instável; force com `+exec server.cfg`
       na linha de comando de qualquer forma):
         log on                  # sem isso, "World triggered ..." e
                                  # "Game Over: ..." nem aparecem no log
         rcon_password "sua_senha_local"
         sv_lan 1                # dispensa GSLT pra teste local
         tv_enable 1

    3. Bind explícito em todas as interfaces, senão o RCON escuta só no
       IP da rede local (ex.: 192.168.x.x) e não em 127.0.0.1:
         +ip 0.0.0.0

    4. bot_quota/bot_quota_mode/bot_difficulty e outras cvars de partida
       NÃO vão em server.cfg — o config interno do modo (ex.: competitive)
       roda depois e sobrescreve. Coloque essas em
       game/csgo/cfg/gamemode_competitive_server.cfg, que o engine executa
       depois do gamemode base especificamente pra permitir isso.

    5. --print-only continua disponível como fallback manual (imprime o
       comando em vez de mandar via RCON) caso o RCON falhe por qualquer
       outro motivo além dos dois acima.

Uso:
    .venv\\Scripts\\python.exe watcher.py --log "C:/.../csgo/console.log" \\
                       --server-demo-dir "C:/.../csgo" \\
                       --demo-dir ./demos \\
                       --player seu_nick_in_game \\
                       --rcon-password minha_senha
                       # (ou --print-only pra testar sem RCON)

    --server-demo-dir é a pasta game/csgo do servidor DEDICADO (onde o
    GOTV realmente grava o .dem) — normalmente igual à pasta de --log,
    já que console.log e o .dem ficam na mesma pasta.

    Ao fim de cada partida, o hook on_match_finished já dispara sozinho:
    parseia o .dem (parser.py), arquiva em --demo-dir e regenera o
    relatório (--report-out, default ./report.html) — não precisa rodar
    report.py manualmente depois de cada partida, só quando quiser
    reprocessar algo fora do fluxo normal do watcher.

    Adicione --debug na primeira vez rodando: ele imprime toda linha de
    log relacionada a Match_/Round_/Game Over/MatchStatus que ainda não
    bateu com nenhum padrão, pra você calibrar os regexes em PATTERNS
    com o formato real do seu log (pode variar entre versões do jogo).
"""

import argparse
import json
import re
import shutil
import subprocess
import time
import traceback
from datetime import datetime
from glob import glob
from pathlib import Path

try:
    from rcon.source import Client as RconClient
except ImportError:
    RconClient = None

from parser import parse_and_store, store_match_from_csv, store_match_from_events
from report import generate_report
from home import generate_home
from config import (
    CONTAINER_NAME, DB_PATH, DEMO_DIR, DEMOS_LIVE_DIR, EVENTS_LIVE_DIR,
    HOME_PATH, MATCH_CONFIG_FILE, REPORT_PATH, ROOT, STATS_LIVE_DIR,
)
from identity import resolve_identity


# ---------------------------------------------------------------------------
# Padrões de log — CONFIRME e ajuste com os logs reais das suas partidas.
# Rode com --debug pra imprimir linhas não reconhecidas e calibrar aqui.
# ---------------------------------------------------------------------------
PATTERNS = {
    "match_start": re.compile(r'World triggered "Match_Start" on "(?P<map>\w+)"'),
    "warmup_end": re.compile(r'World triggered "Warmup_End"'),
    "game_over": re.compile(
        r'Game Over: competitive \S* ?(?P<map>\S+) '
        r'score (?P<score_ct>\d+):(?P<score_t>\d+) after (?P<minutes>\d+) min'
    ),
}

# ---------------------------------------------------------------------------
# Passo 3 (Camada 1) — fim de partida via MatchZy (log do container Docker,
# não mais o console.log nativo). Calibrado em cima de duas partidas reais:
#
#   matchid 6: veio HandleMatchEnd "MAP ENDED" seguido de um segundo
#   HandleMatchEnd "MATCH ENDED, remainingMaps: 0, NumMaps: 1,
#   Team1SeriesScore: 1, Team2SeriesScore: 0" antes do SetMatchEndData.
#
#   matchid 9: só veio o HandleMatchEnd "MAP ENDED" — a segunda linha
#   "MATCH ENDED" com o placar de série NÃO apareceu.
#
# Ou seja, a linha "MATCH ENDED" com placar não é confiável como gatilho
# (curioso — mesmo tipo de match bo1, com e sem ela). WritePlayerStatsToCsv
# é o único evento que se repetiu nas duas partidas E é logicamente o
# último passo do pipeline do MatchZy (stats já persistidas), então é o
# gatilho definitivo de "partida terminou de verdade". SetMatchEndData vem
# antes dele sempre e carrega o winnerName — o watcher guarda esse valor
# e só dispara o hook de fim de partida quando o WritePlayerStatsToCsv
# do MESMO matchid chegar.
# ---------------------------------------------------------------------------
MATCHZY_PATTERNS = {
    "match_winner": re.compile(
        r'\[SetMatchEndData\] Data updated for matchId: (?P<matchid>\d+) '
        r'winnerName: (?P<winner>.+?)\s*$'
    ),
    "stats_written": re.compile(
        r'\[WritePlayerStatsToCsv\] Match stats for ID: (?P<matchid>\d+) '
        r'written successfully at: (?P<csv_path>\S+)\s*$'
    ),
    # Número do mapa dito pelo próprio MatchZy. É a fonte autoritativa: a
    # versão anterior deduzia o índice contando os .dem em disco, e a demo
    # só é descarregada `tvFlushDelay` segundos DEPOIS do fim do mapa (15s
    # por padrão) — mais que os 10s que o watcher esperava. Na série 45
    # (19/09/2026) isso perdeu um mapa inteiro e rotulou outro errado.
    "map_ended": re.compile(
        r'\[HandleMatchEnd\] MAP ENDED.*?matchid: (?P<matchid>\d+) '
        r'currentMapNumber: (?P<mapnum>\d+)'
    ),
    # Nome do mapa. O 'World triggered "Match_Start"' do modo nativo NÃO
    # aparece no log do container — conferido no log de 19/09/2026.
    "change_map": re.compile(r'\[ChangeMap\] Changing map to (?P<map>\w+)'),
}


class MatchWatcher:
    def __init__(self, log_path=None, demo_dir=None, server_demo_dir=None, identity=None,
                 db_path=None, report_path=None, home_path=None,
                 rcon_host="127.0.0.1", rcon_port=27015, rcon_password="",
                 print_only=False, debug=False,
                 mode="native", container=None, demos_live_dir=None, stats_live_dir=None,
                 events_live_dir=None, match_config_path=None):
        self.mode = mode
        self.match_config_path = Path(match_config_path) if match_config_path else None
        self.log_path = Path(log_path) if log_path else None
        self.demo_dir = Path(demo_dir or DEMO_DIR)
        self.demo_dir.mkdir(parents=True, exist_ok=True)
        self.server_demo_dir = Path(server_demo_dir) if server_demo_dir else None
        self.identity = identity
        self.db_path = db_path or DB_PATH
        self.report_path = report_path or REPORT_PATH
        self.home_path = home_path or HOME_PATH
        self.rcon_host = rcon_host
        self.rcon_port = rcon_port
        self.rcon_password = rcon_password
        self.print_only = print_only
        self.debug = debug

        self.recording = False
        self.current_demo_name = None

        # Modo matchzy (Docker) — ver MATCHZY_PATTERNS.
        self.container = container or CONTAINER_NAME
        self.demos_live_dir = Path(demos_live_dir or DEMOS_LIVE_DIR)
        self.stats_live_dir = Path(stats_live_dir or STATS_LIVE_DIR)
        self.events_live_dir = Path(events_live_dir or EVENTS_LIVE_DIR)
        self._pending_winners = {}
        # Nome do mapa em jogo, vindo do 'Match_Start' do log — fonte mais
        # confiável que o nome do arquivo .dem, que pode nem existir ainda
        # (ou nunca existir) na hora de arquivar os eventos.
        self._current_map = None
        # matchid -> currentMapNumber, preenchido pelo 'MAP ENDED'.
        self._pending_map_number = {}

    # ------------------------------------------------------------------
    def send_command(self, command: str):
        """Envia um comando pro jogo via RCON, ou só imprime se --print-only."""
        print(f"[CMD] {command}")
        if self.print_only:
            return
        if RconClient is None:
            print("  (pacote 'rcon' não instalado — rode: pip install rcon)")
            return
        try:
            with RconClient(self.rcon_host, self.rcon_port, passwd=self.rcon_password) as client:
                response = client.run(command)
                if response:
                    print(f"  -> {response}")
        except Exception as exc:
            print(f"  [ERRO] não consegui enviar via RCON: {exc}")
            print("  Rode com --print-only e execute manualmente no console do jogo.")

    # ------------------------------------------------------------------
    def start_recording(self, map_name="unknown"):
        if self.recording:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_demo_name = f"{timestamp}_{map_name}"
        self.send_command(f"tv_record {self.current_demo_name}")
        self.recording = True
        print(f"[MATCH] Gravação iniciada: {self.current_demo_name}.dem")

    def stop_recording(self, meta=None):
        if not self.recording:
            return
        self.send_command("tv_stoprecord")
        self.recording = False
        print(f"[MATCH] Gravação finalizada: {self.current_demo_name}.dem")
        if meta:
            print(f"[MATCH] Placar: {meta}")
        self.on_match_finished(self.current_demo_name, meta)
        self.current_demo_name = None

    # ------------------------------------------------------------------
    def on_match_finished(self, demo_name, meta):
        """
        Hook chamado quando uma partida termina e o .dem já foi fechado.
        O GOTV grava o .dem dentro da pasta game/csgo/ do servidor
        dedicado (server_demo_dir), não em demo_dir — parseia de lá e só
        depois arquiva o arquivo em demo_dir.
        """
        source_path = self.server_demo_dir / f"{demo_name}.dem"
        if not source_path.exists():
            print(f"[PIPELINE] .dem não encontrado em {source_path}, pulando parse")
            return

        parse_and_store(source_path, meta, self.db_path, self.identity)

        dest_path = self.demo_dir / f"{demo_name}.dem"
        shutil.move(str(source_path), str(dest_path))
        print(f"[PIPELINE] Demo arquivada em {dest_path}")

        generate_report(self.db_path, self.report_path)
        generate_home(self.db_path, self.home_path)

    # ------------------------------------------------------------------
    def tail(self):
        """Segue o arquivo de log tipo `tail -f`, tolerando o arquivo ser recriado."""
        print(f"[WATCHER] Monitorando: {self.log_path}")
        f = None
        inode = None
        while True:
            try:
                if f is None or self.log_path.stat().st_ino != inode:
                    if f:
                        f.close()
                    f = open(self.log_path, "r", encoding="utf-8", errors="ignore")
                    f.seek(0, 2)  # pula pro final do que já existe
                    inode = self.log_path.stat().st_ino
                    print("[WATCHER] (Re)conectado ao arquivo de log.")

                line = f.readline()
                if not line:
                    time.sleep(0.25)
                    continue

                self.handle_line(line.strip())

            except FileNotFoundError:
                print("[WATCHER] Log ainda não existe, aguardando...")
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n[WATCHER] Encerrado pelo usuário.")
                break

    # ------------------------------------------------------------------
    def handle_line(self, line):
        m = PATTERNS["match_start"].search(line)
        if m:
            self.start_recording(map_name=m.group("map"))
            return

        m = PATTERNS["game_over"].search(line)
        if m:
            meta = {
                "map": m.group("map"),
                "score_ct": m.group("score_ct"),
                "score_t": m.group("score_t"),
                "minutes": m.group("minutes"),
            }
            self.stop_recording(meta=meta)
            return

        if self.debug and any(k in line for k in ("Match_", "Round_", "Game Over", "MatchStatus")):
            print(f"[DEBUG] linha não tratada: {line}")

    # ------------------------------------------------------------------
    # Modo matchzy (Docker) — ver MATCHZY_PATTERNS.
    # ------------------------------------------------------------------
    def tail_docker_logs(self):
        """Segue `docker logs -f` do container, igual a um `tail -f` só que
        do stdout do container em vez de um arquivo no host (MatchZy não
        escreve log nenhum no host)."""
        print(f"[WATCHER] Monitorando container Docker: {self.container}")
        while True:
            proc = None
            try:
                proc = subprocess.Popen(
                    ["docker", "logs", "-f", "--tail", "0", self.container],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="ignore",
                )
                print("[WATCHER] Conectado ao log do container.")
                for line in proc.stdout:
                    try:
                        self.handle_matchzy_line(line.strip())
                    except Exception as exc:
                        # Um bug no handler de UMA linha (ex.: o NameError em
                        # stored_any, 2026-09-21) não pode derrubar o watcher
                        # pro resto da série — sem isso, um mapa com problema
                        # silenciosamente perdia a ingestão dos mapas
                        # seguintes inteiros, sem nenhum aviso na tela.
                        print(f"[WATCHER] [ERRO] Falha processando linha do log "
                              f"(seguindo mesmo assim): {exc!r}")
                        traceback.print_exc()
                proc.wait()
                print(f"[WATCHER] `docker logs` encerrou (container parado?). Tentando de novo em 5s...")
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n[WATCHER] Encerrado pelo usuário.")
                if proc:
                    proc.terminate()
                break
            except FileNotFoundError:
                print("[WATCHER] Comando 'docker' não encontrado. Docker está instalado e no PATH?")
                time.sleep(5)

    def handle_matchzy_line(self, line):
        m = MATCHZY_PATTERNS["change_map"].search(line)
        if m:
            self._current_map = m.group("map")
            return

        m = MATCHZY_PATTERNS["map_ended"].search(line)
        if m:
            # Guardado aqui e consumido no stats_written, que vem ~0,1s
            # depois e garante que o CSV já está em disco.
            self._pending_map_number[m.group("matchid")] = int(m.group("mapnum"))
            return

        m = MATCHZY_PATTERNS["match_winner"].search(line)
        if m:
            self._pending_winners[m.group("matchid")] = m.group("winner")
            return

        m = MATCHZY_PATTERNS["stats_written"].search(line)
        if m:
            matchid = m.group("matchid")
            # O número do mapa vem do CAMINHO DO CSV que o próprio MatchZy
            # acabou de escrever (match_data_map<N>_<matchid>.csv). Antes ele
            # era deduzido contando as demos em disco, o que quebrava feio: na
            # série 45 (19/09/2026) faltou a demo de um mapa, todos os índices
            # escorregaram, o mapa 1 foi perdido inteiro e o mapa 2 acabou
            # arquivado como "map1".
            map_number = self._pending_map_number.pop(matchid, None)
            if map_number is None:
                csv_match = re.search(r"match_data_map(\d+)_\d+\.csv", m.group("csv_path"))
                if csv_match:
                    map_number = int(csv_match.group(1))
            winner = self._pending_winners.pop(matchid, None)
            self.on_matchzy_map_finished(matchid, map_number, winner)
            return

        if self.debug and "MatchZy" in line:
            print(f"[DEBUG] linha MatchZy não tratada: {line}")

    def _match_config(self):
        """match_config.json que o wizard acabou de escrever. None quando o
        arquivo não existe ou está ilegível — nunca derruba a ingestão."""
        if not self.match_config_path:
            return None
        try:
            return json.loads(self.match_config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _series_num_maps(self):
        """Tamanho da série (1/3/5) lido do match_config.json — usado pra
        exibir BO3/BO5 no report (docs/SPEC.md, pedido em 2026-09-21)."""
        data = self._match_config()
        return data.get("num_maps") if data else None

    def _map_name_for(self, matchid, map_number):
        """Nome do mapa que acabou de terminar, em três fontes.

        1. `_current_map`, do '[ChangeMap]' do log. Só pega do SEGUNDO mapa
           de uma série em diante: o wizard troca o mapa e SÓ DEPOIS sobe o
           watcher, e o watcher segue `docker logs -f --tail 0`, que começa
           do fim do log. A linha do primeiro mapa já passou.
        2. O maplist do match_config.json, indexado por map_number. É a fonte
           boa pro primeiro mapa: o wizard escreveu esse arquivo antes de
           carregar a série, então ele já está em disco e não depende de
           tempo nenhum.
        3. O nome do arquivo .dem. Última reserva, e frágil: a demo pode
           demorar (com tv_delay alto a MatchZy só fecha o arquivo
           tv_delay+14.5s depois do fim da partida — em 22/09/2026 isso fez
           duas partidas entrarem com map=NULL) ou não existir (série 45: 2
           demos pra 3 mapas).
        """
        if self._current_map:
            return self._current_map

        data = self._match_config() or {}
        maplist = data.get("maplist") or []
        if map_number is not None and 0 <= map_number < len(maplist):
            return maplist[map_number]

        demos = sorted(
            glob(str(self.demos_live_dir / f"*_{matchid}_*.dem")),
            key=lambda p: Path(p).stat().st_mtime,
        )
        if map_number is not None and 0 <= map_number < len(demos):
            alvo = demos[map_number]
        elif demos:
            alvo = demos[-1]
        else:
            return None
        achou = re.search(
            r"_\d+_(?P<map>de_\w+)_(?P<team1>.+)_vs_(?P<team2>.+)\.dem$", Path(alvo).name
        )
        return achou.group("map") if achou else None

    def on_matchzy_map_finished(self, matchid, map_number, winner):
        """
        Chamado quando o MatchZy termina de escrever o CSV de stats de UM
        MAPA (WritePlayerStatsToCsv) — o último passo do pipeline dele, ou
        seja, demo e stats já estão em disco.

        Trata só o mapa que acabou. A versão anterior reprocessava a série
        inteira a cada mapa e, pior, numerava os mapas enumerando as demos em
        disco: bastava uma demo faltar pra todos os índices escorregarem.

        O arquivamento dos eventos é urgente: o plugin só escreve em
        "current.jsonl" e trunca esse arquivo no próximo OnMapStart. Entre
        esta linha de log e o começo do mapa seguinte é a única janela.
        """
        if map_number is None:
            print("[PIPELINE] Não consegui extrair o número do mapa do log; "
                  "usando 0 como fallback.")
            map_number = 0

        map_name = self._map_name_for(matchid, map_number)
        meta = {"map": map_name, "winner": winner, "series_num_maps": self._series_num_maps()}
        demo_name = f"events_{matchid}_map{map_number}"
        archived = self.events_live_dir / f"{demo_name}.jsonl"
        current = self.events_live_dir / "current.jsonl"

        # Arquiva PRIMEIRO, ingere depois: o rename é o que salva os dados do
        # truncamento, e qualquer erro de ingestão depois disso é recuperável
        # (tools/reingest_events.py).
        if not archived.exists() and current.exists() and current.stat().st_size > 0:
            current.rename(archived)
            print(f"[PIPELINE] Eventos do mapa {map_number} arquivados em {archived.name}")

        stored = False
        if archived.exists():
            meta["demo_name"] = demo_name
            store_match_from_events(archived, meta, self.db_path, self.identity)
            stored = True
        else:
            print(f"[PIPELINE] Sem eventos pro mapa {map_number} de {matchid} "
                  f"(current.jsonl vazio ou já truncado).")
            csv_path = self.stats_live_dir / str(matchid) / f"match_data_map{map_number}_{matchid}.csv"
            for _ in range(20):  # até ~10s de espera pelo bind mount
                if csv_path.exists():
                    break
                time.sleep(0.5)
            if csv_path.exists():
                print(f"[PIPELINE] CSV de stats existe ({csv_path.name}), mas só tem "
                      f"agregado — sem rounds nem placar. Não ingerido; use "
                      f"tools/reingest_events.py se os eventos aparecerem.")
            else:
                print(f"[PIPELINE] Nem eventos nem CSV pro mapa {map_number}, pulando.")

        print(f"[MATCH] matchid={matchid} finalizado (vencedor: {winner or '?'})")
        if stored:
            generate_report(self.db_path, self.report_path)
            generate_home(self.db_path, self.home_path)


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Match Watcher")
    parser.add_argument("--mode", choices=["native", "matchzy"], default="native",
                         help="native: tail de console.log + RCON/GOTV (servidor dedicado nativo). "
                              "matchzy: docker logs -f + demos/stats já gravados pelo MatchZy (fluxo Docker)")
    parser.add_argument("--log", help="Caminho do console.log do CS2 (obrigatório no modo native)")
    parser.add_argument("--demo-dir", default=DEMO_DIR,
                         help="Pasta onde arquivar os .dem já parseados (modo native)")
    parser.add_argument("--server-demo-dir",
                         help="Pasta game/csgo do servidor dedicado, onde o GOTV grava o .dem "
                              "(obrigatório no modo native)")
    parser.add_argument("--player", required=True,
                         help="Nome in-game do jogador humano (ou SteamID64) — usado pra filtrar "
                              "posição/heatmap")
    parser.add_argument("--match-config", default=str(ROOT / "docker" / MATCH_CONFIG_FILE),
                         help="Caminho do match_config.json pra resolver steamid do jogador "
                              "(modo matchzy). Ignorado no modo native.")
    parser.add_argument("--db", default=DB_PATH, help="Caminho do SQLite")
    parser.add_argument("--report-out", default=REPORT_PATH,
                         help="Caminho do relatório HTML, regenerado ao fim de cada partida")
    parser.add_argument("--home-out", default=HOME_PATH,
                         help="Caminho da home HTML, regenerada ao fim de cada partida")
    parser.add_argument("--rcon-host", default="127.0.0.1")
    parser.add_argument("--rcon-port", type=int, default=27015)
    parser.add_argument("--rcon-password", default="")
    parser.add_argument("--print-only", action="store_true",
                         help="Não envia comando de fato, só imprime (record/stop manual) (modo native)")
    parser.add_argument("--container", default=CONTAINER_NAME,
                         help="Nome do container Docker do servidor MatchZy (modo matchzy)")
    parser.add_argument("--demos-live-dir", default=DEMOS_LIVE_DIR,
                         help="Pasta onde o MatchZy grava as demos, mapeada no docker-compose (modo matchzy)")
    parser.add_argument("--stats-live-dir", default=STATS_LIVE_DIR,
                         help="Pasta onde o MatchZy grava os CSVs de stats, mapeada no docker-compose (modo matchzy)")
    parser.add_argument("--events-live-dir", default=EVENTS_LIVE_DIR,
                         help="Pasta onde o plugin Cs2TrackerEvents escreve current.jsonl, mapeada no "
                              "docker-compose (modo matchzy) — fonte preferida sobre o CSV quando presente")
    parser.add_argument("--debug", action="store_true",
                         help="Mostra linhas de log ainda não reconhecidas")
    args = parser.parse_args()

    if args.mode == "native" and (not args.log or not args.server_demo_dir):
        parser.error("--log e --server-demo-dir são obrigatórios no modo native")

    match_config_path = Path(args.match_config) if args.mode == "matchzy" else None
    identity = resolve_identity(args.player, match_config_path)

    watcher = MatchWatcher(
        match_config_path=match_config_path,
        mode=args.mode,
        log_path=args.log,
        demo_dir=args.demo_dir,
        server_demo_dir=args.server_demo_dir,
        identity=identity,
        db_path=args.db,
        report_path=args.report_out,
        home_path=args.home_out,
        rcon_host=args.rcon_host,
        rcon_port=args.rcon_port,
        rcon_password=args.rcon_password,
        print_only=args.print_only,
        debug=args.debug,
        container=args.container,
        demos_live_dir=args.demos_live_dir,
        stats_live_dir=args.stats_live_dir,
        events_live_dir=args.events_live_dir,
    )

    if args.mode == "matchzy":
        watcher.tail_docker_logs()
    else:
        watcher.tail()


if __name__ == "__main__":
    main()