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

    Adicione --debug na primeira vez rodando: ele imprime toda linha de
    log relacionada a Match_/Round_/Game Over/MatchStatus que ainda não
    bateu com nenhum padrão, pra você calibrar os regexes em PATTERNS
    com o formato real do seu log (pode variar entre versões do jogo).
"""

import argparse
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

try:
    from rcon.source import Client as RconClient
except ImportError:
    RconClient = None

from parser import parse_and_store


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


class MatchWatcher:
    def __init__(self, log_path, demo_dir, server_demo_dir, player_name, db_path,
                 rcon_host, rcon_port, rcon_password, print_only=False, debug=False):
        self.log_path = Path(log_path)
        self.demo_dir = Path(demo_dir)
        self.demo_dir.mkdir(parents=True, exist_ok=True)
        self.server_demo_dir = Path(server_demo_dir)
        self.player_name = player_name
        self.db_path = db_path
        self.rcon_host = rcon_host
        self.rcon_port = rcon_port
        self.rcon_password = rcon_password
        self.print_only = print_only
        self.debug = debug

        self.recording = False
        self.current_demo_name = None

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

        parse_and_store(source_path, meta, self.db_path, self.player_name)

        dest_path = self.demo_dir / f"{demo_name}.dem"
        shutil.move(str(source_path), str(dest_path))
        print(f"[PIPELINE] Demo arquivada em {dest_path}")

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


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Match Watcher")
    parser.add_argument("--log", required=True, help="Caminho do console.log do CS2")
    parser.add_argument("--demo-dir", default="./demos",
                         help="Pasta onde arquivar os .dem já parseados")
    parser.add_argument("--server-demo-dir", required=True,
                         help="Pasta game/csgo do servidor dedicado, onde o GOTV grava o .dem")
    parser.add_argument("--player", required=True,
                         help="Nome in-game do jogador humano (usado pra filtrar posição/heatmap)")
    parser.add_argument("--db", default="./cs2_tracker.db", help="Caminho do SQLite")
    parser.add_argument("--rcon-host", default="127.0.0.1")
    parser.add_argument("--rcon-port", type=int, default=27015)
    parser.add_argument("--rcon-password", default="")
    parser.add_argument("--print-only", action="store_true",
                         help="Não envia comando de fato, só imprime (record/stop manual)")
    parser.add_argument("--debug", action="store_true",
                         help="Mostra linhas de log ainda não reconhecidas")
    args = parser.parse_args()

    watcher = MatchWatcher(
        log_path=args.log,
        demo_dir=args.demo_dir,
        server_demo_dir=args.server_demo_dir,
        player_name=args.player,
        db_path=args.db,
        rcon_host=args.rcon_host,
        rcon_port=args.rcon_port,
        rcon_password=args.rcon_password,
        print_only=args.print_only,
        debug=args.debug,
    )
    watcher.tail()


if __name__ == "__main__":
    main()