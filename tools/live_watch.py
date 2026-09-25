#!/usr/bin/env python3
"""
Observador ao vivo da subida de partida — pra investigar o round fantasma
(docs/features/M0.5-placar.md, F0.5.5) enquanto alguém joga de verdade.

Junta três fontes numa timeline única com timestamp relativo ao início:

  [docker]  linhas relevantes do `docker logs -f` do container
  [evento]  cada linha nova do events-live/current.jsonl, resumida
  [placar]  o placar do jogo lido por RCON a cada N segundos

O objetivo é responder, com carimbo de tempo: em que instante o round
fantasma dispara, o que o servidor tinha de jogador em cada time naquele
momento, e se o placar do jogo mudou por causa dele.

Uso (deixe rodando ANTES de clicar em iniciar servidor no wizard):
    .venv\\Scripts\\python.exe tools/live_watch.py
    .venv\\Scripts\\python.exe tools/live_watch.py --out logs/teste1.log
"""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import CONTAINER_NAME, EVENTS_LIVE_DIR, load_env  # noqa: E402

T0 = time.time()
_print_lock = threading.Lock()
_out_file = None

# Linhas do log do servidor que importam pra essa investigação.
DOCKER_PATTERNS = [
    (re.compile(r"OnPreResetRound|OnRoundStart|World triggered", re.I), "round"),
    (re.compile(r'"(.+?)" (entered the game|joined team|disconnected)', re.I), "jogador"),
    (re.compile(r"Warmup|warmup", re.I), "warmup"),
    (re.compile(r"MatchZy|matchzy|live\.cfg|css_start|Match starting|going live", re.I), "matchzy"),
    (re.compile(r"Game Over|SFUI_Notice|Team_?Score|round_?end", re.I), "fim"),
    (re.compile(r"bot_quota|bot_add|bot_kick", re.I), "bot"),
]


def emit(source, text):
    line = f"[{time.time() - T0:7.1f}s] [{source:<7}] {text}"
    with _print_lock:
        print(line, flush=True)
        if _out_file:
            _out_file.write(line + "\n")
            _out_file.flush()


def watch_docker(container):
    proc = subprocess.Popen(
        ["docker", "logs", "-f", "--tail", "0", container],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    for raw in proc.stdout:
        raw = raw.rstrip()
        if not raw:
            continue
        for pattern, tag in DOCKER_PATTERNS:
            if pattern.search(raw):
                emit("docker", f"({tag}) {raw[:200]}")
                break


def summarize_event(e):
    t = e.get("type")
    rn = e.get("round_num")
    if t == "round_start":
        return f"round {rn} COMEÇOU — lado do humano: {e.get('human_side') or '?'}"
    if t == "round_end":
        return f"round {rn} TERMINOU — vencedor {e.get('winner') or '?'} ({e.get('reason')})"
    if t == "round_officially_ended":
        return f"round {rn} encerrado oficialmente"
    if t == "player_death":
        return (f"round {rn}: {e.get('attacker_name')} matou {e.get('victim_name')} "
                f"({e.get('weapon')})")
    return None  # player_hurt e resto: ruído demais pra timeline


def watch_events(events_path, verbose):
    """Tail do current.jsonl, resistente a truncamento (OnMapStart zera o arquivo)."""
    pos = 0
    emit("evento", f"observando {events_path}")
    while True:
        try:
            size = events_path.stat().st_size if events_path.exists() else 0
            if size < pos:  # truncado: troca de mapa
                emit("evento", "--- arquivo truncado (troca de mapa) ---")
                pos = 0
            if size > pos:
                with open(events_path, encoding="utf-8-sig") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                for line in chunk.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = summarize_event(e)
                    if msg:
                        emit("evento", msg)
                    elif verbose:
                        emit("evento", line[:160])
        except Exception as exc:
            emit("evento", f"[erro] {exc}")
        time.sleep(0.5)


def rcon(host, port, password, command, timeout=5):
    """Mesmo caminho do start_match.py: o pacote `rcon` direto do host.

    A primeira versão disto chamava `rcon-cli` via `docker exec` e falhou o
    teste inteiro de 19/09/2026 — esse binário não existe no PATH da imagem,
    então o log ficou sem nenhuma leitura de placar.
    """
    from rcon.source import Client as RconClient

    with RconClient(host, port, passwd=password, timeout=timeout) as client:
        return client.run(command)


def watch_score(host, port, password, interval):
    """Placar autoritativo do jogo via get5_status da MatchZy.

    NÃO usar mp_teamscore_1/mp_teamscore_2: esses são o placar da SÉRIE
    (mapas ganhos numa BO-N), não os rounds do mapa atual. O get5_status
    devolve JSON com gamestate, round_number e current_map_score por time —
    é o único jeito de ver o instante exato em que um ponto é creditado.
    """
    last = None
    while True:
        try:
            raw = rcon(host, port, password,
                       "get5_status; mp_ignore_round_win_conditions")
            snapshot = None
            try:
                data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
                teams = data.get("team1", {}), data.get("team2", {})
                snapshot = (
                    f"estado={data.get('gamestate')} round={data.get('round_number')} "
                    + " ".join(
                        f"{t.get('name', '?')}[{t.get('side', '?')}]={t.get('current_map_score')}"
                        for t in teams
                    )
                )
            except (ValueError, AttributeError):
                snapshot = raw[:200] or None
            # Mostra a camada 2 abrindo e fechando: enquanto estiver em 1,
            # nenhum round pode terminar (nem por bomba, nem por tempo).
            m = re.search(r'"mp_ignore_round_win_conditions" = "(\w+)"', raw)
            if m and snapshot:
                estado = "LIGADO" if m.group(1) in ("1", "true") else "desligado"
                snapshot += f" | bloqueio de fim de round: {estado}"
            if snapshot and snapshot != last:
                emit("placar", snapshot)
                last = snapshot
        except Exception as exc:
            emit("placar", f"[erro] {exc}")
        time.sleep(interval)


def main():
    global _out_file
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--container", default=CONTAINER_NAME)
    ap.add_argument("--events-dir", default=EVENTS_LIVE_DIR)
    ap.add_argument("--rcon-host", default="127.0.0.1")
    ap.add_argument("--rcon-port", type=int, default=27015)
    # 0.25s: o round fantasma dura ~1,3s, então uma amostragem lenta não
    # consegue dizer se o placar mudou por causa dele.
    ap.add_argument("--score-interval", type=float, default=0.25)
    ap.add_argument("--no-score", action="store_true",
                    help="não consultar placar por RCON (evita concorrer com o wizard)")
    ap.add_argument("--verbose", action="store_true", help="mostra todo evento do jsonl")
    ap.add_argument("--out", default=None, help="salva a timeline num arquivo também")
    args = ap.parse_args()

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        _out_file = open(path, "a", encoding="utf-8")
        _out_file.write(f"\n===== sessão iniciada {datetime.now().isoformat()} =====\n")

    events_path = Path(args.events_dir) / "current.jsonl"

    emit("setup", f"container={args.container} eventos={events_path}")
    emit("setup", "Deixe rodando e suba a partida pelo wizard. Ctrl+C encerra.")

    threads = [
        threading.Thread(target=watch_docker, args=(args.container,), daemon=True),
        threading.Thread(target=watch_events, args=(events_path, args.verbose), daemon=True),
    ]
    if not args.no_score:
        password = load_env().get("CS2_RCONPW")
        if not password or password == "CHANGE_ME_LOCAL_ONLY":
            emit("setup", "[AVISO] CS2_RCONPW não configurado; placar por RCON desligado.")
        else:
            threads.append(threading.Thread(
                target=watch_score,
                args=(args.rcon_host, args.rcon_port, password, args.score_interval),
                daemon=True,
            ))

    for t in threads:
        t.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        emit("setup", "encerrado.")
        if _out_file:
            _out_file.close()


if __name__ == "__main__":
    main()
