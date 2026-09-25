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
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

try:
    from rcon.source import Client as RconClient
except ImportError:
    RconClient = None

from config import COMPOSE_FILE, CONTAINER_NAME, MATCH_CONFIG_FILE, load_env

ROOT = Path(__file__).resolve().parent

# Sink de log explícito (F2.2, docs/features/M2-nucleo.md): qualquer callable
# de uma linha de texto. print() é o default — mesma assinatura, e é o que o
# CLI precisa sem passar nada. Nenhuma função aqui usa contextlib.redirect_
# stdout: quem quiser capturar a saída (ex.: wizard_tui.py) passa seu próprio
# sink em vez de redirecionar o stdout do processo inteiro.
Sink = Callable[[str], None]


def container_running(container_name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def compose_up(compose_file: Path, log: Sink = print):
    log(f"[DOCKER] Subindo servidor ({compose_file.name})...")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True, cwd=ROOT,
    )


def rcon_run(host, port, password, command, timeout=5):
    if RconClient is None:
        raise RuntimeError("pacote 'rcon' não instalado — rode: pip install rcon")
    with RconClient(host, port, passwd=password, timeout=timeout) as client:
        return client.run(command)


def human_side_from_config(match_config_path: Path, log: Sink = print) -> str:
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
        log(f"[AVISO] não consegui ler {match_config_path} ({exc}), assumindo team1=CT.")
    return "ct"


def set_map_in_config(match_config_path: Path, map_name: str, log: Sink = print):
    """Sobrescreve maplist (bo1) no match_config antes de carregar a partida."""
    data = json.loads(match_config_path.read_text(encoding="utf-8"))
    data["maplist"] = [map_name]
    data["num_maps"] = 1
    match_config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"[CONFIG] {match_config_path.name}: maplist -> [{map_name}]")


def set_side_in_config(match_config_path: Path, side: str, log: Sink = print):
    """
    Sobrescreve map_sides no match_config. A MatchZy fixa o time humano
    (team1) no lado declarado aqui e desabilita a troca manual pelo menu
    do jogo enquanto o match está carregado — então o único jeito de jogar
    de TR é mudar isso antes do matchzy_loadmatch, não em jogo.
    """
    data = json.loads(match_config_path.read_text(encoding="utf-8"))
    data["map_sides"] = [f"team1_{side}"]
    match_config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"[CONFIG] {match_config_path.name}: map_sides -> [team1_{side}]")


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


_STATUS_PLAYER_RE = re.compile(r"^\s*\d+\s+.*'[^']*'\s*$", re.MULTILINE)


def rcon_client_count(rcon_host, rcon_port, rcon_password, timeout: int = 5) -> int:
    """Conta clientes conectados via RCON `status` — sinal imediato do
    próprio servidor, ao contrário de wait_for_team_snapshot (que infere de
    OnPreResetRound, um evento que só atualiza a cada reset de round do
    warmup — 19-29s medidos ao vivo em 2026-09-20, às vezes mais de um
    ciclo pra todo mundo aparecer com time atribuído). Não distingue time
    (isso continua sendo trabalho de wait_for_team_snapshot/
    fix_bot_overflow); só confirma que todo mundo entrou."""
    response = rcon_run(rcon_host, rcon_port, rcon_password, "status", timeout=timeout) or ""
    if "---------players--------" in response:
        response = response.split("---------players--------", 1)[1]
    if "#end" in response:
        response = response.split("#end", 1)[0]
    return len(_STATUS_PLAYER_RE.findall(response))


def wait_for_client_count(rcon_host, rcon_port, rcon_password, expected_clients: int,
                           timeout_s: int = 20, interval_s: float = 1.0) -> int:
    """Espera até `status` reportar pelo menos `expected_clients`, ou até
    `timeout_s` esgotar. É o gate de "todo mundo entrou" (SPEC.md §10,
    restrição 2) usado por _balance_bots — mais rápido e confiável que
    wait_for_team_snapshot porque consulta o servidor direto em vez de
    esperar um evento raro no log. 20s de folga é generoso: `status` é
    imediato, não depende de ciclo de warmup nenhum."""
    deadline = time.time() + timeout_s
    count = 0
    while time.time() < deadline:
        count = rcon_client_count(rcon_host, rcon_port, rcon_password)
        if count >= expected_clients:
            return count
        time.sleep(interval_s)
    return count


def fix_bot_overflow(container_name, rcon_host, rcon_port, rcon_password,
                      human_name, target_ct, target_t, log: Sink = print):
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
            log(f"[MATCHZY] {label} com {len(bots)} bot(s), esperado {target} — "
                f"kickando excedente(s): {to_kick}")
            for name in to_kick:
                rcon_run(rcon_host, rcon_port, rcon_password, f'bot_kick "{name}"')


LIVE_OVERRIDE_PATH = "/home/steam/cs2-dedicated/game/csgo/cfg/MatchZy/live_override.cfg"


def write_live_override(container_name: str, total_bots: int, block_win_conditions: bool = True,
                         log: Sink = print):
    """Escreve o cfg/MatchZy/live_override.cfg DENTRO do container.

    Esse arquivo é o único gancho suportado que roda DEPOIS do live.cfg: a
    última linha do live.cfg é `exec MatchZy/live_override.cfg`, no mesmo
    flush de console. Tudo que a gente setava antes do css_start era
    revertido pelo próprio live.cfg (linha 4 `bot_quota 0`, linha 58
    `mp_ignore_round_win_conditions 0`) — daí as tentativas anteriores terem
    falhado.

    Duas camadas aqui:

    1. Reafirmar `bot_quota`. O live.cfg NÃO dá bot_kick, só zera a quota;
       os bots do warmup só são despejados no think seguinte do gerenciador,
       que acontece depois deste exec. Reafirmando a quota, os bots já
       montados e spawnados atravessam a virada — e aí não existe janela.
    2. `mp_ignore_round_win_conditions 1` como rede. Se a camada 1 perder a
       corrida contra o callback da cvar, isto impede o engine de encerrar o
       round enquanto houver bot conectado e não spawnado (que o engine conta
       como MORTO, e é o que gera o round fantasma).

    ATENÇÃO: com a camada 2 ligada NENHUM round termina — nem por bomba, nem
    por tempo. Quem chama é obrigado a desligar depois (ver clear_ignore_win
    e o finally em _force_start_and_balance_bots).

    Usa `docker exec` em vez de bind mount de propósito: bind mount de
    arquivo único é por inode e o container continuaria vendo a versão
    antiga a cada reescrita; além disso não exige mexer no compose nem
    recriar o container. É o mesmo padrão do swap de botprofile.vpk.
    """
    # Conteudo ASCII puro de proposito: isto atravessa um pipe do Windows ate
    # um container Linux, e text=True usa a codificacao local (cp1252 aqui).
    linhas = [
        "// Gerado pelo cs2-tracker a cada css_start.",
        "// Ver start_match.write_live_override e docs/features/M0.5-placar.md",
        "bot_quota_mode normal",
        "mp_autoteambalance 0",
        "mp_limitteams 0",
        f"bot_quota {total_bots}",
    ]
    if block_win_conditions:
        linhas.append("mp_ignore_round_win_conditions 1")
    conteudo = "\n".join(linhas) + "\n"

    subprocess.run(
        ["docker", "exec", "-i", container_name,
         "sh", "-c", f"cat > {LIVE_OVERRIDE_PATH}"],
        input=conteudo, check=True, capture_output=True,
        text=True, encoding="utf-8",
    )
    log(f"[MATCHZY] live_override.cfg escrito (bot_quota {total_bots}"
        f"{', bloqueio de fim de round ligado' if block_win_conditions else ''}).")


def say_in_game(rcon_host, rcon_port, rcon_password, mensagem: str, log: Sink = print):
    """Manda uma linha pro chat do jogo. Nunca derruba o fluxo se falhar —
    é feedback, não etapa da partida. Texto sem acento de propósito: passa
    por RCON e o chat do CS2 engasga com não-ASCII."""
    try:
        rcon_run(rcon_host, rcon_port, rcon_password, f'say "[CS2 Tracker] {mensagem}"')
    except Exception as exc:
        log(f"  [AVISO] não consegui avisar no chat do jogo ({exc}).")


def set_scoreboard_names(rcon_host, rcon_port, rcon_password, *, my_team_name: str,
                          enemy_team_name: str, enemy_team_logo: str, log: Sink = print):
    """
    mp_teamname_1/mp_teamname_2/mp_teamlogo_2 (F4.4, docs/features/
    M4-seletor.md) — reafirmados por RCON a cada mapa (mesmo padrão de
    bot_quota/live_override, F1.3): o match_config já grava team1/team2.name
    na carga inicial, mas isso sozinho não cobre a troca de mapa de uma
    série nem garante que o placar não repita o nome de uma partida
    anterior no mesmo processo do servidor — daí reafirmar aqui, sempre,
    nunca condicional a "só se mudou".

    enemy_team_logo vazio ("") limpa um logo antigo em vez de deixá-lo
    pendurado (é exatamente o critério de aceite da F4.4: lineup manual não
    pode mostrar nome/logo herdado da partida anterior).
    """
    try:
        rcon_run(rcon_host, rcon_port, rcon_password, f'mp_teamname_1 "{my_team_name}"')
        rcon_run(rcon_host, rcon_port, rcon_password, f'mp_teamname_2 "{enemy_team_name}"')
        rcon_run(rcon_host, rcon_port, rcon_password, f'mp_teamlogo_2 "{enemy_team_logo}"')
        log(f'[MATCHZY] Placar: "{my_team_name}" x "{enemy_team_name}" (logo: {enemy_team_logo or "-"}).')
    except Exception as exc:
        log(f"  [AVISO] Não consegui atualizar nome/logo do time no placar ({exc}).")


def clear_ignore_win_conditions(rcon_host, rcon_port, rcon_password, log: Sink = print):
    """Desliga a camada 2. Se isto não rodar, a partida não termina nunca."""
    try:
        rcon_run(rcon_host, rcon_port, rcon_password, "mp_ignore_round_win_conditions 0")
        log("[MATCHZY] Bloqueio de fim de round desligado.")
    except Exception as exc:
        log(f"  [ERRO] Não consegui desligar mp_ignore_round_win_conditions ({exc}).")
        log("  A partida NÃO vai terminar round nenhum. Rode manualmente:")
        log("    mp_ignore_round_win_conditions 0")


class BotAddError(RuntimeError):
    """Uma sequência de bot_add_ct/bot_add_t falhou (nome já em uso ou perfil
    inexistente no botprofile.vpk ativo — SPEC.md §10, restrições 1 e 2) ou a
    contagem final de clientes não bateu com o esperado. Levantada ANTES do
    css_start: nunca deixa o jogador entrar numa partida incompleta sem
    perceber (docs/features/M1-lineups-headless.md, F1.2)."""


def _named_add_commands(side_cmd: str, names) -> List[str]:
    """`names`: uma entrada por bot, na ordem em que entram. `None` pede um
    bot anônimo (perfil sorteado pelo engine, o modo de sempre); uma string
    pede um perfil por nome — a chave do botprofile.vpk (SPEC.md §7), não o
    display_name."""
    return [f'{side_cmd} "{name}"' if name else side_cmd for name in names]


def _balance_bots(*, rcon_host, rcon_port, rcon_password, container_name,
                  ct_names, t_names, player, log: Sink = print):
    """Monta os times. Deve rodar com a partida AINDA EM WARMUP.

    Em warmup o IsWarmupPeriod() faz o CheckWinConditions do engine virar
    no-op, então o vaivém de bot_kick/bot_add não pode gerar round fantasma.
    Com a partida ao vivo, o mesmo laço é inseguro em QUALQUER espaçamento:
    um bot conectado e ainda não spawnado conta como morto pro engine e
    dispara vitória por extermínio. Os 0,2s entre adds não mitigam isso —
    são a causa.

    ct_names/t_names: listas de nome de perfil (ou None pra bot anônimo) —
    ver _named_add_commands. O tamanho de cada lista É a contagem de bots
    daquele lado; quem monta as listas (_force_start_and_balance_bots)
    decide entre lineup nomeada ou preenchimento anônimo por team_size.
    """
    rcon_run(rcon_host, rcon_port, rcon_password,
             "bot_quota 0; bot_quota_mode normal; mp_autoteambalance 0")
    rcon_run(rcon_host, rcon_port, rcon_password, "bot_kick")
    time.sleep(1)  # dá tempo dos slots dos bots kickados liberarem antes de re-adicionar

    add_sequence = [
        cmd for pair in itertools.zip_longest(
            _named_add_commands("bot_add_ct", ct_names),
            _named_add_commands("bot_add_t", t_names),
        )
        for cmd in pair if cmd is not None
    ]
    for cmd in add_sequence:
        response = rcon_run(rcon_host, rcon_port, rcon_password, cmd)
        # Restrição 1 (nome duplicado, agnóstico de time) e restrição 2
        # (perfil inexistente) do SPEC.md §10 — a engine responde com texto,
        # não com um erro RCON de verdade, então sem checar a resposta o
        # script seguiria em frente com um bot a menos e ninguém perceberia
        # até o 4v5 (ou pior) já estar ao vivo.
        if response and ("no profile for" in response or "already in the game" in response):
            raise BotAddError(f"{cmd} -> {response.strip()}")
        time.sleep(0.2)  # um bot por vez, servidor precisa processar o join antes do próximo
    log(f"  -> {len(add_sequence)} bot(s) adicionado(s): {len(ct_names)} CT + {len(t_names)} TR")

    total_bots = len(ct_names) + len(t_names)
    rcon_run(rcon_host, rcon_port, rcon_password, f"bot_quota {total_bots}")

    if player:
        count = wait_for_client_count(rcon_host, rcon_port, rcon_password,
                                       expected_clients=total_bots + 1)
        if count < total_bots + 1:
            raise BotAddError(
                f"Só {count} cliente(s) no servidor após os adds, esperado "
                f"{total_bots + 1} ({len(ct_names)} CT + {len(t_names)} TR + você). "
                "Confira os nomes de perfil (docker logs) antes de tentar de novo."
            )
        fix_bot_overflow(container_name, rcon_host, rcon_port, rcon_password,
                         player, len(ct_names), len(t_names), log=log)
    return total_bots


def _resolve_lineup_names(*, human_side: str, team_size: int, player,
                           my_lineup: Optional[List[str]], enemy_lineup: Optional[List[str]]):
    """
    Decide as listas de nome (ou None pra anônimo) de cada lado a partir da
    lineup escolhida (F1.2, docs/features/M1-lineups-headless.md) — ou cai no
    preenchimento anônimo de sempre quando nenhuma lineup é passada (o wizard
    ainda não monta lineup nenhuma; só o CLI --mine/--enemy usa por enquanto).

    Levanta BotAddError (não deixa chegar no RCON) se:
    - o tamanho de alguma lineup não bate com team_size
    - o nick do humano colide com um perfil da lineup (SPEC.md §10 restrição
      1 — o add falharia silenciosamente lá na frente, então recusa aqui,
      cedo, com mensagem explícita, como pede o critério de aceite da F1.2)
    """
    my_lineup = my_lineup or []
    enemy_lineup = enemy_lineup or []

    if my_lineup and len(my_lineup) != team_size - 1:
        raise BotAddError(
            f"my_lineup tem {len(my_lineup)} nome(s), esperado {team_size - 1} "
            f"(team_size {team_size} menos você)."
        )
    if enemy_lineup and len(enemy_lineup) != team_size:
        raise BotAddError(
            f"enemy_lineup tem {len(enemy_lineup)} nome(s), esperado {team_size}."
        )
    if player and player in my_lineup:
        raise BotAddError(f"Seu nick ({player!r}) está na sua própria lineup — escolha outro perfil.")
    if player and player in enemy_lineup:
        raise BotAddError(f"Seu nick ({player!r}) está na lineup adversária — escolha outro perfil.")

    my_names: List[Optional[str]] = list(my_lineup) if my_lineup else [None] * (team_size - 1)
    enemy_names: List[Optional[str]] = list(enemy_lineup) if enemy_lineup else [None] * team_size

    if human_side == "ct":
        return my_names, enemy_names  # ct_names, t_names
    return enemy_names, my_names


def _force_start_and_balance_bots(*, rcon_host, rcon_port, rcon_password, container_name,
                                   team_size, player, local_match_config, log: Sink = print,
                                   my_lineup: Optional[List[str]] = None,
                                   enemy_lineup: Optional[List[str]] = None,
                                   enemy_team_name: Optional[str] = None,
                                   enemy_team_logo: str = ""):
    """
    Balanceamento de bots + "forçar início" (css_start) — repetido a cada
    mapa de uma série BO3/BO5, não só no primeiro. A MatchZy nunca inicia um
    mapa sozinha aqui: ela exige jogadores DE VERDADE prontos pra contar como
    "time pronto" ([IsTeamReady] minPlayers:5 playerCount:0 — bots não
    contam). css_start ignora esse check e força o "ao vivo" direto.

    ORDEM IMPORTA, e ela é o oposto da que este código tinha até 19/09/2026:
    os times são montados ANTES do css_start, ainda no warmup. Montar depois
    criava o round fantasma (ver docs/features/M0.5-placar.md, F0.5.5). O que
    antes impedia essa ordem — o live.cfg zerar a quota — é resolvido pelo
    live_override.cfg, que roda depois dele.

    my_lineup/enemy_lineup: nomes de profile (F1.2) — repetido a cada mapa
    porque bots nomeados não sobrevivem ao changelevel (SPEC.md §10, restrição
    4), e este método já é re-chamado por mapa da série (ver run_match).
    enemy_team_name/enemy_team_logo: nome/logo do adversário pro placar
    (F4.4) — só reafirmado quando uma lineup foi de fato montada (my_lineup
    ou enemy_lineup não vazio); enemy_team_name=None é o sinal de "nenhuma
    lineup, não mexe no placar" (modo anônimo de sempre).
    """
    human_side = human_side_from_config(local_match_config, log=log)
    ct_names, t_names = _resolve_lineup_names(
        human_side=human_side, team_size=team_size, player=player,
        my_lineup=my_lineup, enemy_lineup=enemy_lineup,
    )
    log(f"[MATCHZY] Time humano no lado {human_side.upper()}. "
        f"Balanceando pra {team_size}x{team_size} "
        f"({len(ct_names)} bot(s) CT + {len(t_names)} bot(s) TR) ainda no warmup...")

    total_bots = _balance_bots(
        rcon_host=rcon_host, rcon_port=rcon_port, rcon_password=rcon_password,
        container_name=container_name, ct_names=ct_names, t_names=t_names, player=player,
        log=log,
    )

    if enemy_team_name is not None:
        set_scoreboard_names(
            rcon_host, rcon_port, rcon_password,
            my_team_name=player or "", enemy_team_name=enemy_team_name,
            enemy_team_logo=enemy_team_logo, log=log,
        )

    override_ok = True
    try:
        write_live_override(container_name, total_bots, block_win_conditions=True, log=log)
    except Exception as exc:
        override_ok = False
        log(f"  [AVISO] Não consegui escrever o live_override.cfg ({exc}).")
        log("  Seguindo sem ele: o round fantasma pode voltar a acontecer.")

    try:
        # Aviso no chat do jogo ANTES do css_start: entre o clique no wizard e
        # o primeiro round passam ~5s em que nada muda na tela, e sem isso o
        # jogador alt-tabba achando que travou.
        say_in_game(rcon_host, rcon_port, rcon_password,
                    "Montando os times... a partida comeca em instantes.", log=log)

        log("[MATCHZY] Forçando início da partida (css_start)...")
        try:
            response = rcon_run(rcon_host, rcon_port, rcon_password, "css_start")
            log(f"  -> {response or '(sem resposta)'}")
        except Exception as exc:
            log(f"  [AVISO] css_start falhou via RCON ({exc}).")
            log("  Digite '.start' manualmente no chat do jogo.")

        # Deixa o live.cfg + o override assentarem e reconcilia os times.
        #
        # Isto é obrigatório, não é paranoia: o gamemode_competitive_server.cfg
        # tem `bot_quota 10` e é reexecutado pela engine na virada pro ao vivo,
        # sobrepondo a quota do override. Observado ao vivo em 19/09/2026 —
        # 11 clientes (CT 6 : TR 5) em vez de 10, com o bot extra sempre no CT.
        #
        # A ordem aqui importa: reafirmar a quota ANTES de kickar. Kickar com a
        # quota ainda em 10 só faz o gerenciador repor o bot na sequência.
        time.sleep(3)
        if player:
            rcon_run(rcon_host, rcon_port, rcon_password,
                     f"bot_quota_mode normal; bot_quota {total_bots}")
            snapshot = read_docker_team_snapshot(container_name)
            presentes = sum(len(v) for v in snapshot.values()) if snapshot else 0
            if presentes and presentes < total_bots + 1:
                log(f"  [AVISO] {presentes} cliente(s) após o css_start, "
                    f"esperado {total_bots + 1}. Recompondo os times...")
                _balance_bots(
                    rcon_host=rcon_host, rcon_port=rcon_port, rcon_password=rcon_password,
                    container_name=container_name, ct_names=ct_names, t_names=t_names,
                    player=player, log=log,
                )
            else:
                # Sobra é o caso comum. fix_bot_overflow kicka pelo nome quem
                # excede o alvo de cada lado — seguro aqui porque a camada 2
                # ainda está ligada, então nenhum round pode terminar no meio.
                fix_bot_overflow(container_name, rcon_host, rcon_port, rcon_password,
                                 player, len(ct_names), len(t_names), log=log)
                rcon_run(rcon_host, rcon_port, rcon_password, f"bot_quota {total_bots}")
                final = read_docker_team_snapshot(container_name)
                if final:
                    n_ct = sum(1 for n, t in final.values() if t == "CT")
                    n_t = sum(1 for n, t in final.values() if t == "TERRORIST")
                    log(f"[MATCHZY] Times após reconciliação: CT {n_ct} : TR {n_t} "
                        f"(esperado {len(ct_names) + (1 if human_side == 'ct' else 0)} : "
                        f"{len(t_names) + (0 if human_side == 'ct' else 1)}).")
                    say_in_game(rcon_host, rcon_port, rcon_password,
                                f"Times prontos: CT {n_ct} x {n_t} TR. Valendo!", log=log)
    finally:
        # Camada 2 SEMPRE desligada, mesmo se algo acima explodir — senão a
        # partida não termina round nenhum.
        if override_ok:
            clear_ignore_win_conditions(rcon_host, rcon_port, rcon_password, log=log)
            # E o arquivo é reescrito sem a linha de bloqueio. Sem isso, um
            # live_override.cfg esquecido com `mp_ignore_round_win_conditions 1`
            # travaria qualquer partida iniciada fora deste fluxo (ex.: .start
            # digitado no chat do jogo).
            try:
                write_live_override(container_name, total_bots, block_win_conditions=False, log=log)
            except Exception as exc:
                log(f"  [AVISO] Não consegui limpar o live_override.cfg ({exc}).")
                log("  Rode antes de iniciar uma partida manualmente:")
                log("    mp_ignore_round_win_conditions 0")

    rcon_run(rcon_host, rcon_port, rcon_password, "mp_autoteambalance 1")


def force_start_and_balance_bots(*, rcon_host, rcon_port, rcon_password, container_name,
                                  team_size, player, local_match_config, rcon_lock=None,
                                  log: Sink = print, my_lineup: Optional[List[str]] = None,
                                  enemy_lineup: Optional[List[str]] = None,
                                  enemy_team_name: Optional[str] = None,
                                  enemy_team_logo: str = ""):
    """Serializa o ciclo inteiro de css_start + balanceamento.

    O mesmo lock é compartilhado pelas chamadas automáticas de run_match e
    pelo botão manual do wizard, evitando que duas sequências RCON se cruzem.
    No uso via CLI, cria um lock local por compatibilidade.
    """
    lock = rcon_lock or threading.Lock()
    with lock:
        _force_start_and_balance_bots(
            rcon_host=rcon_host,
            rcon_port=rcon_port,
            rcon_password=rcon_password,
            container_name=container_name,
            team_size=team_size,
            player=player,
            local_match_config=local_match_config,
            log=log,
            my_lineup=my_lineup,
            enemy_lineup=enemy_lineup,
            enemy_team_name=enemy_team_name,
            enemy_team_logo=enemy_team_logo,
        )


def wait_for_next_map_warmup(container_name: str, since_ts: float, timeout_s: int = 240,
                              log: Sink = print) -> bool:
    """
    Espera passivamente (só lendo docker logs) o próximo mapa de uma série
    BO3/BO5 carregar e entrar em warmup, pra saber a hora certa de repetir
    force_start_and_balance_bots(). Só olha logs a partir de `since_ts`
    (time.time() capturado antes do mapa atual terminar) pra não reagir a
    um "[StartWarmup]" antigo, do mapa anterior.

    Retorna True se detectou o próximo mapa entrando em warmup, False se
    `remainingMaps: 0` apareceu primeiro (série acabou, não tem próximo
    mapa) ou o timeout estourou.
    """
    since_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(since_ts))
    deadline = time.time() + timeout_s
    seen_changemap = False
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "logs", "--since", since_iso, container_name],
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
        text = result.stdout + result.stderr
        if "remainingMaps: 0" in text:
            log("[MATCHZY] A série terminou (remainingMaps: 0); não há próximo mapa.")
            return False
        if "[MatchZy] [ChangeMap]" in text:
            seen_changemap = True
        if seen_changemap and "[MatchZy] [StartWarmup]" in text:
            return True
        time.sleep(2)
    log(f"[AVISO] Timeout de {timeout_s}s esperando ChangeMap -> StartWarmup.")
    return False


def start_watcher(container_name: str, player: str, match_config_path: Path,
                  on_output=None, log: Sink = print) -> subprocess.Popen:
    """
    Sobe watcher.py --mode matchzy em paralelo. O objetivo, nos dois modos
    abaixo, é o mesmo: um único lugar pra acompanhar launcher + watcher.

    Sem on_output (caminho do CLI): herda stdout/stderr do processo atual,
    então as duas saídas caem no terminal de quem rodou start_match.py.

    Com on_output (caminho do wizard): captura a saída num pipe e entrega
    linha a linha pro callback, de uma thread própria. O Textual toma conta
    do terminal, então output herdado sairia impresso por cima do canvas da
    TUI em vez de ir pro painel de log. O -u é obrigatório nesse modo: com
    stdout ligado num pipe o Python do filho troca pra buffer de bloco e as
    linhas só apareceriam lá no fim, todas de uma vez.
    """
    log(f"[WATCHER] Subindo watcher.py --mode matchzy --player {player} em paralelo...")
    cmd = [sys.executable, "watcher.py", "--mode", "matchzy",
           "--player", player, "--container", container_name,
           "--match-config", str(match_config_path)]
    if on_output is None:
        return subprocess.Popen(cmd, cwd=ROOT)

    cmd.insert(1, "-u")
    proc = subprocess.Popen(
        cmd, cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )

    def pump_output():
        for line in proc.stdout:
            on_output(line.rstrip())

    threading.Thread(target=pump_output, daemon=True, name="watcher-output").start()
    return proc


def wait_for_rcon(host, port, password, timeout_s=300, interval_s=5, log: Sink = print):
    log(f"[RCON] Esperando {host}:{port} ficar disponível (timeout {timeout_s}s)...")
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            rcon_run(host, port, password, "echo start_match_ready", timeout=5)
            log("[RCON] Conectado.")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(interval_s)
    raise TimeoutError(f"RCON não respondeu em {timeout_s}s (último erro: {last_error})")


def run_match(*, container_name, match_config, compose_file, rcon_host, rcon_port,
              rcon_password, team_size, boot_timeout, skip_up, player, map_name=None,
              side=None, on_watcher_started=None, watcher_output=None,
              confirm_ready=None, rcon_lock=None, log: Sink = print,
              my_lineup: Optional[List[str]] = None, enemy_lineup: Optional[List[str]] = None,
              enemy_team_name: Optional[str] = None, enemy_team_logo: str = ""):
    """
    Orquestração completa (passos 1-5 do docker/SPIKE.md), sem nenhum
    acoplamento a argparse — corpo extraído de main() pra ser reaproveitado
    tanto pelo CLI quanto pelo wizard_core.launch() (wizard_core.py).

    match_config/compose_file: nomes de arquivo relativos (o mesmo formato
    que args.match_config/args.compose_file tinham antes), não Path.
    map_name/side: já resolvidos por fora (ex.: pelo veto do wizard) — só
    são aplicados aqui se vierem preenchidos, igual ao --map/--side do CLI.
    my_lineup/enemy_lineup: nomes de profile (F1.2, docs/features/
    M1-lineups-headless.md) — repassados a force_start_and_balance_bots em
    TODO mapa da série, não só no primeiro (bots nomeados não sobrevivem ao
    changelevel). None/vazio (default) preserva o preenchimento anônimo de
    sempre, por contagem de team_size.
    on_watcher_started: callback opcional, chamado com o subprocess.Popen do
    watcher assim que ele sobe — usado pelo wizard_tui.py pra conseguir
    encerrar o watcher quando a UI fecha (essa função fica bloqueada em
    watcher_proc.wait() numa worker thread que o Textual não enxerga).
    watcher_output: callback opcional que recebe cada linha do watcher (ver
    start_watcher) — sem ele o watcher herda o terminal, como sempre.
    confirm_ready: callback opcional que substitui o input() bloqueante da
    espera "já conectei e dei .ready". Default: o mesmo input() de sempre
    (é o que o CLI usa); o wizard passa um botão na TUI no lugar, porque o
    prompt de terminal fica invisível por baixo do canvas do Textual.
    log: sink de log explícito (F2.2, docs/features/M2-nucleo.md) — recebe
    cada linha que antes ia direto pro stdout. Default print, então o CLI
    continua funcionando sem passar nada. Repassado a toda função chamada
    daqui que também fala com o "terminal" — nenhuma delas usa
    contextlib.redirect_stdout.

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
    rcon_lock = rcon_lock or threading.Lock()

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
            log(f"[DOCKER] Container '{container_name}' já está rodando.")
        else:
            compose_up(compose_file_path, log=log)

    local_match_config = ROOT / "docker" / Path(match_config).name

    watcher_proc = None
    if player:
        watcher_proc = start_watcher(container_name, player, local_match_config,
                                     on_output=watcher_output, log=log)
        if on_watcher_started:
            on_watcher_started(watcher_proc)

    if map_name:
        set_map_in_config(local_match_config, map_name, log=log)
    if side:
        set_side_in_config(local_match_config, side, log=log)

    wait_for_rcon(rcon_host, rcon_port, rcon_password, timeout_s=boot_timeout, log=log)

    log(f"[MATCHZY] Carregando {match_config}...")
    response = rcon_run(rcon_host, rcon_port, rcon_password,
                         f"matchzy_loadmatch {match_config}")
    log(f"  -> {response or '(sem resposta)'}")

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

    log("")
    log("=" * 70)
    log("Agora conecte no servidor pelo client normal do CS2:")
    log("  Servidores -> Rede Local -> conectar")
    log("  (ou, com a console do jogo ligada: connect 127.0.0.1:27015)")
    log("Depois de conectado, digite '.ready' no chat do jogo.")
    log("=" * 70)
    if confirm_ready is None:
        input("Pressione Enter aqui quando estiver conectado e pronto pra forçar o início... ")
    else:
        confirm_ready()

    force_start_and_balance_bots(
        rcon_host=rcon_host, rcon_port=rcon_port, rcon_password=rcon_password,
        container_name=container_name, team_size=team_size, player=player,
        local_match_config=local_match_config, rcon_lock=rcon_lock, log=log,
        my_lineup=my_lineup, enemy_lineup=enemy_lineup,
        enemy_team_name=enemy_team_name, enemy_team_logo=enemy_team_logo,
    )

    # BO3/BO5: a MatchZy troca de mapa sozinha ao fim de cada um (mp_
    # match_restart_delay + changelevel), mas o mapa seguinte cai na mesma
    # trava de warmup do primeiro ([IsTeamReady] minPlayers:5 playerCount:0
    # — bots não contam como "prontos") e os bots não voltam sozinhos
    # (bot_quota_mode volta pra "fill" quando gamemode_competitive_server.cfg
    # reexecuta no load do novo mapa). Sem repetir force_start_and_balance_bots
    # aqui, a série trava no warmup do mapa 2 pra sempre — observado ao vivo.
    # Você já está conectado, então não precisa de confirm_ready de novo.
    num_maps = json.loads(local_match_config.read_text(encoding="utf-8")).get("num_maps", 1)
    for map_index in range(2, num_maps + 1):
        log(f"\n[MATCHZY] Esperando o mapa {map_index}/{num_maps} da série carregar...")
        since_ts = time.time()
        if not wait_for_next_map_warmup(container_name, since_ts, log=log):
            log("[AVISO] Não detectei o próximo mapa entrando em warmup "
                "(série já pode ter terminado) — seguindo sem forçar de novo.")
            break
        try:
            wait_for_rcon(rcon_host, rcon_port, rcon_password, timeout_s=60, log=log)
            force_start_and_balance_bots(
                rcon_host=rcon_host, rcon_port=rcon_port, rcon_password=rcon_password,
                container_name=container_name, team_size=team_size, player=player,
                local_match_config=local_match_config, rcon_lock=rcon_lock, log=log,
                my_lineup=my_lineup, enemy_lineup=enemy_lineup,
                enemy_team_name=enemy_team_name, enemy_team_logo=enemy_team_logo,
            )
        except Exception as exc:
            # Não deixa um hiccup aqui derrubar o run_match inteiro (e junto
            # o watcher/gravação) — o pior caso é você precisar digitar
            # '.start' manualmente no chat pra esse mapa específico.
            log(f"[AVISO] Falha ao forçar o mapa {map_index}/{num_maps} ({exc}). "
                "Digite '.start' manualmente no chat do jogo se precisar.")

    log("")
    if watcher_proc:
        log("Pronto — jogue normalmente. O watcher já está rodando em paralelo e vai")
        log("gravar sozinho no cs2_tracker.db/report.html ao fim da partida.")
        log("Pressione Ctrl+C aqui quando terminar de jogar (encerra o watcher junto).")
        try:
            watcher_proc.wait()
        except KeyboardInterrupt:
            log("\n[WATCHER] Encerrando...")
            watcher_proc.terminate()
            try:
                watcher_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                watcher_proc.kill()
    else:
        log("Pronto — jogue normalmente. Demo e stats caem em docker/demos-live/ e")
        log("docker/stats-live/ ao fim da partida. Rode em paralelo, ANTES de conectar,")
        log("pra cair sozinho no cs2_tracker.db/report.html (ou use --player pra o script")
        log("já subir isso sozinho da próxima vez):")
        log("  .venv\\Scripts\\python.exe watcher.py --mode matchzy --player <seu_nick>")


def main():
    parser = argparse.ArgumentParser(description="Automatiza os passos 1-5 do docker/SPIKE.md")
    parser.add_argument("--compose-file", default=COMPOSE_FILE)
    parser.add_argument("--container-name", default=CONTAINER_NAME,
                         help="container_name definido no compose")
    parser.add_argument("--match-config", default=MATCH_CONFIG_FILE,
                         help="Arquivo dentro de game/csgo (o mesmo mapeado no volume do compose)")
    parser.add_argument("--map", default=None,
                         help="Sobrescreve o maplist do match_config antes de carregar "
                              "(pool do wizard: de_dust2, de_mirage, de_inferno, de_nuke, "
                              "de_ancient, de_anubis, de_cache). Default: mantém o que já "
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
    parser.add_argument("--mine", default=None,
                         help="Lineup dos SEUS companheiros (sem você), perfil por perfil, "
                              "separados por vírgula — a chave do botprofile.vpk, ex.: "
                              "'NiKo,s1mple,donk,ZywOo'. Precisa ter exatamente team_size-1 "
                              "nomes. Sem isso (default), os bots do seu time são anônimos "
                              "(perfil sorteado pelo engine), como sempre.")
    parser.add_argument("--enemy", default=None,
                         help="Lineup ADVERSÁRIA, perfil por perfil, separados por vírgula — "
                              "mesmo formato de --mine, mas com team_size nomes (não ocupa "
                              "vaga sua). Sem isso, o time adversário é anônimo.")
    args = parser.parse_args()

    my_lineup = [name.strip() for name in args.mine.split(",")] if args.mine else None
    enemy_lineup = [name.strip() for name in args.enemy.split(",")] if args.enemy else None

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
        my_lineup=my_lineup,
        enemy_lineup=enemy_lineup,
    )


if __name__ == "__main__":
    main()
