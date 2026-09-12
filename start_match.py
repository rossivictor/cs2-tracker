#!/usr/bin/env python3
"""
CS2 Tracker — Start Match
==========================
Automatiza os passos 1-5 de docker/SPIKE.md: sobe o container Docker do
servidor MatchZy (se não estiver rodando), espera o RCON ficar disponível,
carrega o match_config e balanceia os bots por lado (bot_kick + bot_add_ct/
bot_add_t exatos) — bot_quota_mode fill não divide certo com 1 humano já
ocupando um time (observado: 4x5 em vez de 5x5).

Com --player, já sobe o watcher.py --mode matchzy em paralelo e fica
esperando ele (Ctrl+C encerra os dois) — um único comando cobre subir o
servidor, carregar o match, balancear os bots, forçar o início e gravar
demo/stats no banco/relatório ao final. Sem --player, deixa a partida
pronta e você roda o watcher à mão em outro terminal.

Uso:
    .venv\\Scripts\\python.exe start_match.py --player seu_nick_in_game
    .venv\\Scripts\\python.exe start_match.py --player seu_nick --map de_inferno --team-size 5
    .venv\\Scripts\\python.exe start_match.py --skip-up   # container já está rodando
"""

import argparse
import itertools
import json
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    from rcon.source import Client as RconClient
except ImportError:
    RconClient = None

from config import COMPOSE_FILE, CONTAINER_NAME, MATCH_CONFIG_FILE, load_env

ROOT = Path(__file__).resolve().parent


def container_running(container_name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def compose_up(compose_file: Path):
    print(f"[DOCKER] Subindo servidor ({compose_file.name})...")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True, cwd=ROOT,
    )


def rcon_run(host, port, password, command, timeout=5):
    if RconClient is None:
        raise RuntimeError("pacote 'rcon' não instalado — rode: pip install rcon")
    with RconClient(host, port, passwd=password, timeout=timeout) as client:
        return client.run(command)


def human_side_from_config(match_config_path: Path) -> str:
    """
    Lê map_sides do match_config pra saber de que lado o time humano
    (team1, por convenção deste projeto) começa no mapa carregado.
    Default "ct" (mesmo default do match_config.spike.json) se o
    arquivo não existir ou não tiver o campo.
    """
    try:
        data = json.loads(match_config_path.read_text(encoding="utf-8"))
        sides = data.get("map_sides", [])
        if sides and sides[0] == "team1_t":
            return "t"
    except Exception as exc:
        print(f"[AVISO] não consegui ler {match_config_path} ({exc}), assumindo team1=CT.")
    return "ct"


def set_map_in_config(match_config_path: Path, map_name: str):
    """Sobrescreve maplist (bo1) no match_config antes de carregar a partida."""
    data = json.loads(match_config_path.read_text(encoding="utf-8"))
    data["maplist"] = [map_name]
    data["num_maps"] = 1
    match_config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CONFIG] {match_config_path.name}: maplist -> [{map_name}]")


def set_side_in_config(match_config_path: Path, side: str):
    """
    Sobrescreve map_sides no match_config. A MatchZy fixa o time humano
    (team1) no lado declarado aqui e desabilita a troca manual pelo menu
    do jogo enquanto o match está carregado — então o único jeito de jogar
    de TR é mudar isso antes do matchzy_loadmatch, não em jogo.
    """
    data = json.loads(match_config_path.read_text(encoding="utf-8"))
    data["map_sides"] = [f"team1_{side}"]
    match_config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CONFIG] {match_config_path.name}: map_sides -> [team1_{side}]")


def read_max_players(compose_file: Path):
    """Lê CS2_MAXPLAYERS do docker-compose.yml (regex simples, sem parser YAML)."""
    try:
        match = re.search(r"CS2_MAXPLAYERS=(\d+)", compose_file.read_text(encoding="utf-8"))
        return int(match.group(1)) if match else None
    except Exception:
        return None


# "<nome><id><steamid><TIME>" OnPreResetRound — evento que a MatchZy solta
# a cada reset de round com o time atual de cada cliente conectado. É a
# mesma fonte que watcher.py usa em modo matchzy (a MatchZy não escreve log
# em arquivo no host, só no stdout do container).
_TEAM_LINE_RE = re.compile(
    r'"(?P<name>[^"<]+)<(?P<cid>\d+)><[^>]*>(?:<(?P<team>CT|TERRORIST|Unassigned|SPECTATOR)>)?"'
    r'\s+OnPreResetRound'
)


def read_docker_team_snapshot(container_name: str, tail: int = 300) -> dict:
    """{client_id: (nome, time)} com o time MAIS RECENTE de cada cliente
    conectado, lido do docker logs (não do console.log — ver watcher.py)."""
    result = subprocess.run(
        ["docker", "logs", "--tail", str(tail), container_name],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    snapshot = {}
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        m = _TEAM_LINE_RE.search(line)
        if m and m.group("team"):
            snapshot[m.group("cid")] = (m.group("name"), m.group("team"))
    return snapshot


def wait_for_team_snapshot(container_name: str, expected_clients: int, timeout_s: int = 12,
                            interval_s: float = 1.0) -> dict:
    """
    Espera passivamente (só lendo docker logs, sem mandar nenhum comando pra
    engine) até o OnPreResetRound trazer pelo menos `expected_clients`
    clientes distintos, ou até `timeout_s` esgotar — o que vier primeiro.
    Puramente observacional de propósito: uma tentativa anterior usava
    mp_restartgame pra forçar esse evento na hora e isso interrompeu a
    gravação da demo que a MatchZy tinha acabado de iniciar (ver
    fix_bot_overflow). Fica dentro do orçamento de freeze time (~15s).
    """
    deadline = time.time() + timeout_s
    snapshot = {}
    while time.time() < deadline:
        snapshot = read_docker_team_snapshot(container_name)
        if len(snapshot) >= expected_clients:
            return snapshot
        time.sleep(interval_s)
    return snapshot


def fix_bot_overflow(container_name, rcon_host, rcon_port, rcon_password,
                      human_name, target_ct, target_t):
    """
    bot_add_ct/bot_add_t não garante contra entidades internas da MatchZy
    (ex.: um cliente "ScopedEconomy" que deveria ficar Unassigned) acabando
    designadas pra um time por engano — observado ao vivo como 6x5 mesmo
    com o balanceamento explícito certo. Confere via docker logs quem a
    engine realmente colocou em cada time e kicka pelo nome quem sobrar.
    Roda ainda na janela de freeze time, depois do balanceamento normal e
    antes do primeiro round valer.
    """
    snapshot = read_docker_team_snapshot(container_name)
    ct_bots = [name for name, team in snapshot.values() if team == "CT" and name != human_name]
    t_bots = [name for name, team in snapshot.values()
              if team == "TERRORIST" and name != human_name]

    for label, bots, target in (("CT", ct_bots, target_ct), ("TR", t_bots, target_t)):
        excess = len(bots) - target
        if excess > 0:
            to_kick = bots[:excess]
            print(f"[MATCHZY] {label} com {len(bots)} bot(s), esperado {target} — "
                  f"kickando excedente(s): {to_kick}")
            for name in to_kick:
                rcon_run(rcon_host, rcon_port, rcon_password, f'bot_kick "{name}"')


def start_watcher(container_name: str, player: str, match_config_path: Path) -> subprocess.Popen:
    """
    Sobe watcher.py --mode matchzy em paralelo, herdando stdout/stderr do
    processo atual (as duas saídas aparecem no mesmo terminal). Não redireciona
    nada porque o objetivo é justamente um único lugar pra acompanhar tudo.
    """
    print(f"[WATCHER] Subindo watcher.py --mode matchzy --player {player} em paralelo...")
    return subprocess.Popen(
        [sys.executable, "watcher.py", "--mode", "matchzy",
         "--player", player, "--container", container_name,
         "--match-config", str(match_config_path)],
        cwd=ROOT,
    )


def wait_for_rcon(host, port, password, timeout_s=300, interval_s=5):
    print(f"[RCON] Esperando {host}:{port} ficar disponível (timeout {timeout_s}s)...")
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            rcon_run(host, port, password, "echo start_match_ready", timeout=5)
            print("[RCON] Conectado.")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(interval_s)
    raise TimeoutError(f"RCON não respondeu em {timeout_s}s (último erro: {last_error})")


def run_match(*, container_name, match_config, compose_file, rcon_host, rcon_port,
              rcon_password, team_size, boot_timeout, skip_up, player, map_name=None,
              side=None, on_watcher_started=None):
    """
    Orquestração completa (passos 1-5 do docker/SPIKE.md), sem nenhum
    acoplamento a argparse — corpo extraído de main() pra ser reaproveitado
    tanto pelo CLI quanto pelo wizard_core.launch() (wizard_core.py).

    match_config/compose_file: nomes de arquivo relativos (o mesmo formato
    que args.match_config/args.compose_file tinham antes), não Path.
    map_name/side: já resolvidos por fora (ex.: pelo veto do wizard) — só
    são aplicados aqui se vierem preenchidos, igual ao --map/--side do CLI.
    on_watcher_started: callback opcional, chamado com o subprocess.Popen do
    watcher assim que ele sobe — usado pelo wizard_tui.py pra conseguir
    encerrar o watcher quando a UI fecha (essa função fica bloqueada em
    watcher_proc.wait() numa worker thread que o Textual não enxerga).

    Dificuldade dos bots NÃO é configurável aqui: o plugin CS2-Bot-Improver
    (github.com/ed0ard/CS2-Bot-Improver) que este projeto usa ignora os
    cvars nativos bot_difficulty/custom_bot_difficulty — ele lê um arquivo
    estático (game/csgo/overrides/botprofile.vpk) carregado só na subida do
    processo do jogo, então não dá pra trocar via RCON em runtime. Fixo em
    "Low" (fácil) por enquanto — ver overrides/{Low,Medium,High}/botprofile.vpk
    já presentes na imagem se quiser trocar manualmente (copiar por cima de
    overrides/botprofile.vpk dentro do container e reiniciá-lo).
    """
    compose_file_path = ROOT / compose_file

    # 2x team_size (times cheios) + 1 slot pro GOTV/SourceTV, que ocupa uma
    # vaga própria mesmo sem ser um jogador de verdade.
    needed_slots = team_size * 2 + 1
    max_players = read_max_players(compose_file_path)
    if max_players is not None and needed_slots > max_players:
        sys.exit(
            f"[ERRO] team_size {team_size} precisa de {needed_slots} slots "
            f"(times + GOTV), mas CS2_MAXPLAYERS no {compose_file_path.name} está em "
            f"{max_players}. Suba esse valor e rode 'docker compose up -d' de novo "
            "(recria o container) antes de tentar de novo."
        )

    if not skip_up:
        if container_running(container_name):
            print(f"[DOCKER] Container '{container_name}' já está rodando.")
        else:
            compose_up(compose_file_path)

    local_match_config = ROOT / "docker" / Path(match_config).name

    watcher_proc = None
    if player:
        watcher_proc = start_watcher(container_name, player, local_match_config)
        if on_watcher_started:
            on_watcher_started(watcher_proc)

    if map_name:
        set_map_in_config(local_match_config, map_name)
    if side:
        set_side_in_config(local_match_config, side)

    wait_for_rcon(rcon_host, rcon_port, rcon_password, timeout_s=boot_timeout)

    print(f"[MATCHZY] Carregando {match_config}...")
    response = rcon_run(rcon_host, rcon_port, rcon_password,
                         f"matchzy_loadmatch {match_config}")
    print(f"  -> {response or '(sem resposta)'}")

    # A MatchZy recusa carregar um match novo se já tiver um "meio carregado"
    # na memória (ex.: uma execução anterior que travou antes do css_start) —
    # ela responde com essa mensagem em vez de um erro RCON de verdade, então
    # sem checar o texto o script seguia em frente e forçava o início do
    # match ANTIGO (observado: vetou um mapa, subiu outro). Falha explícita
    # aqui é melhor que seguir com o servidor num estado que não bate com o
    # match_config que acabamos de escrever.
    if response and "cannot load a new match" in response:
        sys.exit(
            "[ERRO] O servidor já tinha uma partida carregada e recusou o "
            f"match_config novo ({match_config}). Resposta da MatchZy: "
            f"{response!r}. Reinicie o container (docker compose restart "
            f"{container_name}) pra limpar o estado e rode de novo."
        )

    print()
    print("=" * 70)
    print("Agora conecte no servidor pelo client normal do CS2:")
    print("  Servidores -> Rede Local -> conectar")
    print("Depois de conectado, digite '.ready' no chat do jogo.")
    print("=" * 70)
    input("Pressione Enter aqui quando estiver conectado e pronto pra forçar o início... ")

    # Suposição não 100% confirmada: CounterStrikeSharp costuma expor todo
    # ChatCommand (".start") também como ConsoleCommand ("css_start"),
    # utilizável via RCON. Se falhar, cai pro fallback manual abaixo — o
    # comando de chat ainda funciona normalmente (você já é admin via
    # MATCHZY_ADMINS, confirmado no spike).
    print("[MATCHZY] Forçando início da partida (css_start)...")
    try:
        response = rcon_run(rcon_host, rcon_port, rcon_password, "css_start")
        print(f"  -> {response or '(sem resposta)'}")
    except Exception as exc:
        print(f"  [AVISO] css_start falhou via RCON ({exc}).")
        print("  Digite '.start' manualmente no chat do jogo.")

    # Balanceamento dos bots DEPOIS do css_start, não antes. css_start executa
    # MatchZy/live.cfg no servidor, que reseta bots/bot_quota (uma partida
    # "de verdade" pro MatchZy pressupõe só humanos) — balancear antes só pra
    # ver tudo ser zerado de novo assim que a partida vira "ao vivo" (foi
    # assim que sobrou 0 bots, todo mundo "morto" já no round 1). Fazendo
    # isso logo em seguida, ainda dá tempo de terminar dentro do freeze time
    # (~15s padrão) antes de alguém poder se mexer/atirar de verdade.
    #
    # bot_quota_mode fill deixa a divisão CT/TR a critério da engine, que não
    # bate certo com 1 humano já ocupando um time (observado: 4x5 em vez de
    # 5x5). Em vez disso: zera os bots e adiciona a quantidade exata por
    # lado, sabendo de que lado o humano (team1) está pelo match_config.
    human_side = human_side_from_config(local_match_config)
    ct_bots = team_size - 1 if human_side == "ct" else team_size
    t_bots = team_size if human_side == "ct" else team_size - 1
    print(f"[MATCHZY] Time humano no lado {human_side.upper()}. "
          f"Balanceando pra {team_size}x{team_size} "
          f"({ct_bots} bot(s) CT + {t_bots} bot(s) TR)...")

    # mp_autoteambalance desligado durante o ajuste: adicionar um lado inteiro
    # antes do outro cria um desequilíbrio momentâneo grande (ex.: 5x0), o
    # suficiente pra engine kickar um bot sozinha antes do outro lado terminar
    # de encher (foi assim que sobrou 5x4 numa rodada anterior). Intercalar
    # ct/t reduz o desequilíbrio a no máximo 1 durante o processo, mas
    # desligar o autobalance também evita qualquer race remanescente.
    rcon_run(rcon_host, rcon_port, rcon_password,
              "bot_quota 0; bot_quota_mode normal; mp_autoteambalance 0")
    rcon_run(rcon_host, rcon_port, rcon_password, "bot_kick")
    time.sleep(1)  # dá tempo dos slots dos bots kickados liberarem antes de re-adicionar

    add_sequence = [
        cmd for pair in itertools.zip_longest(
            ["bot_add_ct"] * ct_bots, ["bot_add_t"] * t_bots
        )
        for cmd in pair if cmd is not None
    ]
    for cmd in add_sequence:
        rcon_run(rcon_host, rcon_port, rcon_password, cmd)
        time.sleep(0.2)  # um bot por vez, servidor precisa processar o join antes do próximo
    print(f"  -> {len(add_sequence)} bot(s) adicionado(s): {ct_bots} CT + {t_bots} TR")

    # bot_quota não é só a leva inicial — a engine mantém esse número
    # continuamente, kickando bots de sobra até bater a meta. Deixá-lo em 0
    # (usado acima só pra não interferir no ajuste manual) fazia a engine ir
    # kickando os bots aos poucos até sobrar só o humano. Trava no total real
    # que acabamos de montar, pra ela manter (e repor, se um bot cair) esse
    # número em vez de zerar.
    total_bots = ct_bots + t_bots
    rcon_run(rcon_host, rcon_port, rcon_password, f"bot_quota {total_bots}")

    # Confere de verdade quem a engine colocou em cada time antes de
    # reativar o autobalance — bot_add_ct/bot_add_t não garante contra
    # entidades internas da MatchZy (ex.: "ScopedEconomy") entrando num
    # time por engano (observado ao vivo como 6x5 mesmo com esse
    # balanceamento certo). Tentativa anterior usava mp_restartgame pra
    # forçar um OnPreResetRound fresco na hora — só que isso interrompeu a
    # gravação da demo que a MatchZy tinha acabado de iniciar (demo saiu
    # truncada em ~30s, sem round_end nenhum). Espera passiva, só lendo o
    # docker logs (sem mandar nenhum comando de engine), ainda dentro do
    # freeze time (~15s de orçamento, ver comentário acima).
    if player:
        wait_for_team_snapshot(container_name, expected_clients=total_bots + 1, timeout_s=12)
        fix_bot_overflow(container_name, rcon_host, rcon_port, rcon_password,
                          player, ct_bots, t_bots)

    rcon_run(rcon_host, rcon_port, rcon_password, "mp_autoteambalance 1")

    print()
    if watcher_proc:
        print("Pronto — jogue normalmente. O watcher já está rodando em paralelo e vai")
        print("gravar sozinho no cs2_tracker.db/report.html ao fim da partida.")
        print("Pressione Ctrl+C aqui quando terminar de jogar (encerra o watcher junto).")
        try:
            watcher_proc.wait()
        except KeyboardInterrupt:
            print("\n[WATCHER] Encerrando...")
            watcher_proc.terminate()
            try:
                watcher_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                watcher_proc.kill()
    else:
        print("Pronto — jogue normalmente. Demo e stats caem em docker/demos-live/ e")
        print("docker/stats-live/ ao fim da partida. Rode em paralelo, ANTES de conectar,")
        print("pra cair sozinho no cs2_tracker.db/report.html (ou use --player pra o script")
        print("já subir isso sozinho da próxima vez):")
        print("  .venv\\Scripts\\python.exe watcher.py --mode matchzy --player <seu_nick>")


def main():
    parser = argparse.ArgumentParser(description="Automatiza os passos 1-5 do docker/SPIKE.md")
    parser.add_argument("--compose-file", default=COMPOSE_FILE)
    parser.add_argument("--container-name", default=CONTAINER_NAME,
                         help="container_name definido no compose")
    parser.add_argument("--match-config", default=MATCH_CONFIG_FILE,
                         help="Arquivo dentro de game/csgo (o mesmo mapeado no volume do compose)")
    parser.add_argument("--map", default=None,
                         help="Sobrescreve o maplist do match_config antes de carregar "
                              "(ex.: de_inferno, de_ancient, de_nuke, de_dust2, de_overpass, "
                              "de_anubis, de_vertigo, de_train). Default: mantém o que já "
                              "está no arquivo.")
    parser.add_argument("--side", choices=["ct", "t"], default=None,
                         help="Lado do seu time (team1) no mapa. A MatchZy trava a escolha "
                              "pelo menu do jogo, então precisa vir daqui. Default: mantém "
                              "o que já está no arquivo (map_sides).")
    parser.add_argument("--rcon-host", default="127.0.0.1")
    parser.add_argument("--rcon-port", type=int, default=27015)
    parser.add_argument("--rcon-password", default=None,
                         help="Default: lê CS2_RCONPW do .env")
    parser.add_argument("--team-size", type=int, default=5,
                         help="Jogadores por time, contando o humano (default 5 = 5x5)")
    parser.add_argument("--boot-timeout", type=int, default=300,
                         help="Segundos de espera pelo RCON após subir o container")
    parser.add_argument("--skip-up", action="store_true",
                         help="Não tenta subir o container, assume que já está rodando")
    parser.add_argument("--player", default=None,
                         help="Seu nick in-game. Se informado, sobe o watcher.py --mode matchzy "
                              "em paralelo (grava demo/stats no banco e regenera o report.html "
                              "sozinho ao fim da partida) e o script fica esperando ele até você "
                              "encerrar com Ctrl+C. Sem isso, você precisa rodar o watcher à mão "
                              "em outro terminal.")
    args = parser.parse_args()

    env = load_env(ROOT / ".env")
    rcon_password = args.rcon_password or env.get("CS2_RCONPW")
    if not rcon_password or rcon_password == "CHANGE_ME_LOCAL_ONLY":
        sys.exit(
            "[ERRO] CS2_RCONPW não configurado — preencha .env "
            "(veja .env.example) ou passe --rcon-password."
        )

    run_match(
        container_name=args.container_name,
        match_config=args.match_config,
        compose_file=args.compose_file,
        rcon_host=args.rcon_host,
        rcon_port=args.rcon_port,
        rcon_password=rcon_password,
        team_size=args.team_size,
        boot_timeout=args.boot_timeout,
        skip_up=args.skip_up,
        player=args.player,
        map_name=args.map,
        side=args.side,
    )


if __name__ == "__main__":
    main()
