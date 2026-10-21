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
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

try:
    from rcon.source import Client as RconClient
except ImportError:
    RconClient = None

from config import COMPOSE_FILE, CONTAINER_NAME, EVENTS_LIVE_DIR, MATCH_CONFIG_FILE, compose_files, load_env

ROOT = Path(__file__).resolve().parent

# Sink de log explícito (F2.2, docs/features/M2-nucleo.md): qualquer callable
# de uma linha de texto. print() é o default — mesma assinatura, e é o que o
# CLI precisa sem passar nada. Nenhuma função aqui usa contextlib.redirect_
# stdout: quem quiser capturar a saída (ex.: wizard_tui.py) passa seu próprio
# sink em vez de redirecionar o stdout do processo inteiro.
Sink = Callable[[str], None]

# Órfão real (P1.1): o plugin de captura trunca o current.jsonl no próximo
# OnMapStart, e o loadmatch (ou a subida do container) dispara um. Se a
# partida anterior caiu antes do watcher arquivar (BO3 matchid 75, 04/10:
# segfault na troca para o mapa 2), os rounds dela estão só ali. Basta UM
# destes eventos para ser partida de verdade. O resto (snapshot, round_stats,
# round_officially_ended) é a cauda normal de toda partida já arquivada, e
# segue sendo truncada pelo plugin, como antes. Exceção (P1.1d): a morte de
# pós-jogo (morte_de_pos_jogo) também é cauda; contrato do JSONL, §7.
EVENTOS_DE_PARTIDA = frozenset({"round_start", "player_death", "player_hurt"})


def _carimbo_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def morte_de_pos_jogo(evento: dict) -> bool:
    """O jogador morto pelo 'world' com atacante = vítima: o resto da tela
    final (sair, trocar de time), não round (P1.1d). Mesma regra do
    tools/evidencia_partida._morte_de_pos_jogo; o teste
    test_orphan_e_log.py::test_preservar_orfao_concorda_com_analisar_current
    prova que as duas concordam. Só vale sem round_start no arquivo: com um,
    o round_start já faz do arquivo um órfão."""
    atacante = evento.get("attacker_steamid")
    return (evento.get("type") == "player_death" and evento.get("weapon") == "world"
            and bool(atacante) and atacante == evento.get("victim_steamid"))


def _tem_evento_de_partida(caminho: Path) -> bool:
    # utf-8-sig: o plugin já gravou arquivo com BOM (events_44_map0).
    with caminho.open(encoding="utf-8-sig", errors="replace") as arquivo:
        for linha in arquivo:
            try:
                evento = json.loads(linha)
            except ValueError:
                continue
            if (isinstance(evento, dict) and evento.get("type") in EVENTOS_DE_PARTIDA
                    and not morte_de_pos_jogo(evento)):
                return True
    return False


def preservar_orfao(pasta_eventos: Path, log: Sink = print) -> Optional[Path]:
    """Renomeia o current.jsonl para orphan_<utc>.jsonl quando ele tem round
    real; devolve o caminho novo, ou None. Nunca para a partida: se nem o
    rename nem a cópia derem certo, avisa e segue."""
    current = Path(pasta_eventos) / "current.jsonl"
    try:
        if not current.is_file() or not _tem_evento_de_partida(current):
            return None
    except OSError as exc:
        log(f"[AVISO] Não consegui ler {current} ({exc}); sigo sem conferir órfão.")
        return None
    carimbo = _carimbo_utc()
    destino = current.with_name(f"orphan_{carimbo}.jsonl")
    n = 2
    while destino.exists():  # nunca sobrescreve um órfão anterior
        destino = current.with_name(f"orphan_{carimbo}-{n}.jsonl")
        n += 1
    try:
        current.rename(destino)
    except OSError as exc:
        try:
            shutil.copy2(current, destino)
        except OSError:
            log(f"[AVISO] current.jsonl tem rounds não arquivados e não consegui "
                f"preservá-lo ({exc}): o próximo mapa vai truncá-lo.")
            return None
    log(f"[CAPTURA] current.jsonl tinha rounds sem arquivar: preservado em {destino.name}.")
    return destino


def sink_com_arquivo(log: Sink, pasta: Path, nome: str) -> Sink:
    """Sink que repassa cada linha a `log` e a acrescenta em pasta/nome
    (logs/partidas/, P1.1). Falha de escrita vira um [AVISO] só, e as linhas
    seguintes vão só para `log`: o arquivo nunca para a partida."""
    caminho = Path(pasta) / nome
    trava = threading.Lock()
    estado = {"ok": True}

    def escrever(linha: str):
        log(linha)
        with trava:
            if not estado["ok"]:
                return
            try:
                caminho.parent.mkdir(parents=True, exist_ok=True)
                with caminho.open("a", encoding="utf-8") as arquivo:
                    arquivo.write(f"{datetime.now():%H:%M:%S} {linha}\n")
                return
            except Exception as exc:  # qualquer falha: a partida segue
                estado["ok"] = False
                erro = exc
        log(f"[AVISO] Não consegui gravar o log em {caminho} ({erro}); a partida segue sem ele.")

    return escrever


def aviso_candidato(arquivo: Path, log: Sink = print) -> None:
    """Linha [INFO] do candidato em teste (protocolo 5, P1.1), lida do
    data/candidato.json que o `jogavel.py marcar candidato` grava. Sem o
    arquivo, não diz nada."""
    arquivo = Path(arquivo)
    if not arquivo.is_file():
        return
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        tag = dados.get("tag") or "?"
        nota = dados.get("nota") or ""
        commit = str(dados.get("commit") or "")[:9]
    except Exception:
        tag, nota, commit = "?", "data/candidato.json ilegível", ""
    detalhe = ", ".join(p for p in (nota, commit and f"commit {commit}") if p)
    log(f"[INFO] Candidato em teste: {tag}" + (f" ({detalhe})" if detalhe else "")
        + ". Esta partida valida esse degrau; para desfazer: tools/jogavel.py voltar.")


# Aviso de captura não carregada (P1.4; ADR-0004, Q19=B). Captura que não
# carrega avisa e a partida segue; abortar é opt-in do Victor. Falso positivo
# é o pior erro aqui: o aviso só sai com a DLL ausente no checkout, OU com as
# DUAS evidências do servidor faltando de forma afirmativa (o css_plugins list
# respondeu uma lista sem o plugin E o docker logs do boot tem plugins
# carregando, mas não o nosso). RCON vazio, docker logs indisponível ou sem
# boot legível é "não sei", nunca "ausente": sem aviso.
DLL_CAPTURA = Path("docker") / "plugins" / "Cs2TrackerEvents" / "Cs2TrackerEvents.dll"
NOME_CAPTURA = "CS2 Tracker Events"  # ModuleName do Cs2TrackerEventsPlugin.cs
EXIGIR_CAPTURA = "CS2_TRACKER_EXIGIR_CAPTURA"
CARREGADA, AUSENTE, INCERTA = "carregada", "ausente", "incerta"
# Cabeçalho do `css_plugins list` da CounterStrikeSharp: só com ele a resposta
# é uma lista de verdade (e a falta do nome vale como "ausente").
_LISTA_DE_PLUGINS = re.compile(r"List of all plugins currently loaded|\[#\d+:[A-Z]+\]")
# Linha de load da captura no boot: a da CounterStrikeSharp e a do plugin.
_LOAD_CAPTURA = re.compile(r"Finished loading plugin CS2 Tracker Events\b|\[Cs2TrackerEvents\] Pronto")
# Prova de que o recorte do docker logs pegou o boot dos plugins.
_BOOT_DE_PLUGINS = re.compile(r"Finished loading plugin |\[MatchZy [\d.]+ LOADED\]")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def captura_no_plugins_list(resposta) -> str:
    """CARREGADA se o css_plugins list cita a captura; AUSENTE só se a
    resposta é uma lista de plugins sem ela; INCERTA no resto (vazia, None,
    comando desconhecido)."""
    texto = _ANSI.sub("", resposta or "")
    if NOME_CAPTURA in texto:
        return CARREGADA
    if _LISTA_DE_PLUGINS.search(texto):
        return AUSENTE
    return INCERTA


def captura_no_docker_logs(texto) -> str:
    """CARREGADA com a linha de load da captura; AUSENTE só se o recorte tem
    o boot dos plugins (outro plugin carregou) e nada dela; INCERTA no resto
    (None, vazio, log sem boot legível)."""
    texto = _ANSI.sub("", texto or "")
    if _LOAD_CAPTURA.search(texto):
        return CARREGADA
    if _BOOT_DE_PLUGINS.search(texto):
        return AUSENTE
    return INCERTA


def docker_logs_do_boot(container_name: str) -> Optional[str]:
    """O docker logs desde o StartedAt do container (o boot atual), stdout e
    stderr juntos; None se qualquer passo falha ou demora."""
    try:
        inicio = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.StartedAt}}", container_name],
            capture_output=True, text=True, timeout=10,
        )
        desde = (inicio.stdout or "").strip()
        if inicio.returncode != 0 or not desde:
            return None
        logs = subprocess.run(
            ["docker", "logs", "--since", desde, container_name],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30,
        )
    except Exception:  # docker fora do PATH, timeout, qualquer erro: não sei
        return None
    if logs.returncode != 0:
        return None
    return (logs.stdout or "") + (logs.stderr or "")


def checar_captura(*, container_name, rcon_host, rcon_port, rcon_password) -> tuple:
    """(estado, motivo): CARREGADA, AUSENTE ou INCERTA, pela regra do P1.4:
    sem a DLL, ou sem a captura no css_plugins list E sem a linha de load no
    docker logs."""
    if not (ROOT / DLL_CAPTURA).is_file():
        return AUSENTE, f"{DLL_CAPTURA.as_posix()} não existe no checkout"
    try:
        lista = captura_no_plugins_list(
            rcon_run(rcon_host, rcon_port, rcon_password, "css_plugins list"))
    except Exception:
        lista = INCERTA
    if lista == CARREGADA:
        return CARREGADA, f"'{NOME_CAPTURA}' no css_plugins list"
    logs = captura_no_docker_logs(docker_logs_do_boot(container_name))
    if logs == CARREGADA:
        return CARREGADA, "linha de load no docker logs"
    if lista == AUSENTE and logs == AUSENTE:
        return AUSENTE, (f"'{NOME_CAPTURA}' fora do css_plugins list e sem a "
                         "linha de load no docker logs do boot")
    faltou = [nome for nome, estado in (("css_plugins list", lista), ("docker logs", logs))
              if estado == INCERTA]
    return INCERTA, f"sem resposta legível de {' e '.join(faltou)}"


def exigir_captura(arquivo_env: Optional[Path] = None, environ=None) -> bool:
    """O opt-in da Q19=B: CS2_TRACKER_EXIGIR_CAPTURA=1 no ambiente ou no .env
    (o ambiente vence). Qualquer outro valor, ou nenhum, é não."""
    environ = os.environ if environ is None else environ
    valor = environ.get(EXIGIR_CAPTURA)
    if valor is None:
        try:
            valor = load_env(Path(arquivo_env or ROOT / ".env")).get(EXIGIR_CAPTURA)
        except Exception:
            valor = None
    return (valor or "").strip() == "1"


def avisar_captura(*, container_name, rcon_host, rcon_port, rcon_password,
                   log: Sink = print) -> bool:
    """Confere a captura e diz o resultado pelo sink (TUI e logs/partidas/).
    Devolve True se a partida deve abortar: só com a captura ausente e o
    opt-in ligado. Sem o opt-in, o [AVISO] sai e a partida segue."""
    estado, motivo = checar_captura(container_name=container_name, rcon_host=rcon_host,
                                    rcon_port=rcon_port, rcon_password=rcon_password)
    if estado == CARREGADA:
        log(f"[CAPTURA] Plugin de captura carregado ({motivo}).")
        return False
    if estado == INCERTA:
        log(f"[CAPTURA] Não consegui confirmar o plugin de captura ({motivo}); sigo sem aviso.")
        return False
    exigir = exigir_captura()
    barra = "[AVISO] " + "!" * 62
    log(barra)
    log(f"[AVISO] CAPTURA NÃO CARREGADA: {motivo}.")
    log("[AVISO] Sem ela, os eventos round a round desta partida não são gravados "
        "(docker/events-live).")
    if exigir:
        log(f"[AVISO] {EXIGIR_CAPTURA}=1: a partida não começa sem a captura.")
    else:
        log(f"[AVISO] A partida SEGUE. Para abortar nesse caso: {EXIGIR_CAPTURA}=1 no .env.")
    log(barra)
    return exigir


# Docker fora do ar (P1.1c): com o Docker Desktop parado (as quedas noturnas,
# exit 0x40010004), o `docker compose up -d` esperava em silêncio e a TUI
# ficava em "Subindo servidor..." sem erro (15/10). O `docker version` com
# timeout curto responde antes: rc 0 só com o daemon no ar.
DOCKER_FORA_DO_AR = "Docker Desktop não está rodando: abra o Docker Desktop e tente de novo."
DOCKER_TIMEOUT_S = 10


def docker_fora_do_ar(timeout_s: float = DOCKER_TIMEOUT_S) -> Optional[str]:
    """None se o daemon do Docker responde; senão, o motivo em uma linha.
    Falha fechada: docker fora do PATH, timeout ou qualquer erro ao chamar
    também contam como fora do ar."""
    try:
        resultado = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except FileNotFoundError:
        return "o comando docker não está no PATH"
    except subprocess.TimeoutExpired:
        return f"o daemon do Docker não respondeu em {timeout_s:g}s"
    except Exception as exc:  # qualquer outra falha também para antes do compose
        return f"falha ao chamar o docker ({exc})"
    if resultado.returncode == 0:
        return None
    linhas = [l.strip() for l in (resultado.stderr or "").splitlines() if l.strip()]
    return linhas[-1] if linhas else f"docker version saiu com código {resultado.returncode}"


def container_running(container_name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def compose_up(compose_file: Path, log: Sink = print):
    """`docker compose up -d` com os -f de config.compose_files() (card
    P1.2): o compose_file e, com o vanilla ligado, o override dele. Com o
    vanilla off o argv é o de antes: só o `-f <compose_file>`."""
    arquivos = [ROOT / a for a in compose_files(raiz=ROOT, base=compose_file, avisar=log)]
    log(f"[DOCKER] Subindo servidor ({' + '.join(a.name for a in arquivos)})...")
    subprocess.run(
        ["docker", "compose", *[x for a in arquivos for x in ("-f", str(a))], "up", "-d"],
        check=True, cwd=ROOT,
    )


def rcon_run(host, port, password, command, timeout=5):
    if RconClient is None:
        raise RuntimeError("pacote 'rcon' não instalado — rode: pip install rcon")
    with RconClient(host, port, passwd=password, timeout=timeout) as client:
        return client.run(command)


def human_side_from_config(match_config_path: Path, map_index: int = 0,
                           log: Sink = print) -> str:
    """
    Lê map_sides[map_index] do match_config pra saber de que lado o time
    humano (team1, por convenção deste projeto) começa no mapa `map_index`
    da série (0 = primeiro mapa). P1.6: numa MD3 com map_sides
    [team1_ct, team1_t, ...] o mapa 2 é de TR; ler sempre o [0] montava os
    times do mapa 2 com o lado do mapa 1.
    Default "ct" (mesmo default do match_config.spike.json) se o
    arquivo não existir, não tiver o campo ou não tiver esse índice.
    """
    try:
        data = json.loads(match_config_path.read_text(encoding="utf-8"))
        sides = data.get("map_sides", [])
        if map_index < len(sides):
            return "t" if sides[map_index] == "team1_t" else "ct"
        if sides:
            log(f"[AVISO] map_sides de {match_config_path.name} não tem o mapa "
                f"{map_index + 1} ({sides}), assumindo team1=CT.")
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

    Numa série (num_maps > 1) o --side vale para todos os mapas: grava um
    lado por mapa, em vez de deixar só o [0] e os mapas seguintes sem lado
    (P1.6). Na MD1 a lista continua com um elemento só.
    """
    data = json.loads(match_config_path.read_text(encoding="utf-8"))
    data["map_sides"] = [f"team1_{side}"] * max(1, int(data.get("num_maps") or 1))
    match_config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"[CONFIG] {match_config_path.name}: map_sides -> {data['map_sides']}")


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

# A SourceTV (TV_ENABLE=1 no compose) entra no changelevel como cliente BOT no
# slot 0 e fica a partida inteira; o bot_kick puro não a derruba. No `status`:
#    0      BOT    0    0     active      0 '<hostname> CSTV'
# Não é jogador: contá-la dava 11 num 5x5 certo e 10 num 4x5 (partida 95,
# 20/10; P1.7). Exige a coluna de tempo "BOT" e o nome terminando em "CSTV",
# para um humano de nome parecido (tempo tipo 00:36) continuar contando.
_STATUS_CSTV_RE = re.compile(r"^\s*\d+\s+BOT\s+.*'(?:[^']* )?CSTV'\s*$")


def rcon_client_count(rcon_host, rcon_port, rcon_password, timeout: int = 5) -> int:
    """Conta clientes conectados via RCON `status` — sinal imediato do
    próprio servidor, ao contrário de wait_for_team_snapshot (que infere de
    OnPreResetRound, um evento que só atualiza a cada reset de round do
    warmup — 19-29s medidos ao vivo em 2026-09-20, às vezes mais de um
    ciclo pra todo mundo aparecer com time atribuído). Não distingue time
    (isso continua sendo trabalho de wait_for_team_snapshot/
    fix_bot_overflow); só confirma que todo mundo entrou.

    Conta jogadores (humano + bots): a linha da SourceTV fica de fora (ver
    _STATUS_CSTV_RE). Com a TV desligada a linha não existe e a conta é a
    mesma, sem depender do TV_ENABLE."""
    response = rcon_run(rcon_host, rcon_port, rcon_password, "status", timeout=timeout) or ""
    if "---------players--------" in response:
        response = response.split("---------players--------", 1)[1]
    if "#end" in response:
        response = response.split("#end", 1)[0]
    return sum(1 for linha in _STATUS_PLAYER_RE.findall(response)
               if not _STATUS_CSTV_RE.match(linha))


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

    Devolve os nomes kickados (lista vazia se ninguém sobrou): quem chama
    precisa saber se houve kick para esperar o servidor assentar antes de
    contar de novo (P1.7).
    """
    snapshot = read_docker_team_snapshot(container_name)
    ct_bots = [name for name, team in snapshot.values() if team == "CT" and name != human_name]
    t_bots = [name for name, team in snapshot.values()
              if team == "TERRORIST" and name != human_name]

    kicked = []
    for label, bots, target in (("CT", ct_bots, target_ct), ("TR", t_bots, target_t)):
        excess = len(bots) - target
        if excess > 0:
            to_kick = bots[:excess]
            log(f"[MATCHZY] {label} com {len(bots)} bot(s), esperado {target} — "
                f"kickando excedente(s): {to_kick}")
            for name in to_kick:
                rcon_run(rcon_host, rcon_port, rcon_password, f'bot_kick "{name}"')
            kicked.extend(to_kick)
    return kicked


# Teto da espera pela contagem de clientes depois do css_start e depois do
# kick do excedente (P1.7). A reposição da quota é assíncrona: o servidor
# repõe o bot kickado no think seguinte, então a primeira leitura pode vir
# com um a menos. Com todo mundo dentro, a espera sai na primeira leitura.
PRESENTES_TIMEOUT_S = 10


def _contar_presentes(rcon_host, rcon_port, rcon_password, esperado: int,
                      log: Sink = print) -> int:
    """Clientes conectados AGORA (humano + bots, sem a SourceTV), pelo `status` do RCON, com
    espera limitada até chegar a `esperado` (P1.7).

    Não usa o bloco OnPreResetRound do docker logs: ele só se renova no reset
    de round seguinte e, logo depois de um kick, ainda mostra quem já saiu
    (partidas 89, 91 e 93, 19-20/10). O `status` não traz o time de ninguém,
    só quem está conectado. 0 quer dizer "não deu para medir".
    """
    try:
        return wait_for_client_count(rcon_host, rcon_port, rcon_password,
                                     expected_clients=esperado,
                                     timeout_s=PRESENTES_TIMEOUT_S)
    except Exception as exc:
        log(f"  [AVISO] Não consegui contar os clientes pelo status do RCON ({exc}).")
        return 0


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
                                   map_index: int = 0,
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
    map_index: mapa da série que está entrando (0 = primeiro), para ler o
    lado do time humano em map_sides[map_index] (P1.6). O mesmo lado manda
    na montagem dos times e na reconciliação esperada CT:TR, mais abaixo.
    """
    human_side = human_side_from_config(local_match_config, map_index=map_index, log=log)
    ct_names, t_names = _resolve_lineup_names(
        human_side=human_side, team_size=team_size, player=player,
        my_lineup=my_lineup, enemy_lineup=enemy_lineup,
    )
    log(f"[MATCHZY] Time humano no lado {human_side.upper()} "
        f"(mapa {map_index + 1}, map_sides[{map_index}]). "
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
            # P1.7: presentes conta CLIENTES pelo status do RCON. A soma
            # antiga dos tamanhos das tuplas (nome, time) do snapshot dava 2
            # por cliente, e a recomposição nunca disparava.
            esperado = total_bots + 1
            presentes = _contar_presentes(rcon_host, rcon_port, rcon_password, esperado, log=log)
            if presentes and presentes < esperado:
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
                kicked = fix_bot_overflow(container_name, rcon_host, rcon_port, rcon_password,
                                          player, len(ct_names), len(t_names), log=log)
                rcon_run(rcon_host, rcon_port, rcon_password, f"bot_quota {total_bots}")
                # P1.7: a contagem final é medida DEPOIS do kick, pelo status.
                # Reler o bloco OnPreResetRound repetia o 6:4 de antes do kick.
                # O status não traz time, então o log não afirma CT:TR.
                if kicked:
                    time.sleep(1)  # o kick sai e a quota repõe no think seguinte
                final = _contar_presentes(rcon_host, rcon_port, rcon_password, esperado, log=log)
                if final:
                    exp_ct = len(ct_names) + (1 if human_side == 'ct' else 0)
                    exp_t = len(t_names) + (0 if human_side == 'ct' else 1)
                    log(f"[MATCHZY] Clientes após reconciliação (status do RCON): {final} "
                        f"(esperado {esperado}: {exp_ct} CT + {exp_t} TR; "
                        "o status não informa o lado).")
                    if final == esperado:
                        say_in_game(rcon_host, rcon_port, rcon_password,
                                    f"Times prontos: {final} jogadores em campo. Valendo!",
                                    log=log)
                    else:
                        say_in_game(rcon_host, rcon_port, rcon_password,
                                    f"Atencao: {final} jogadores em campo, esperado {esperado}.",
                                    log=log)
                else:
                    log("  [AVISO] Clientes após reconciliação: não medidos (status sem clientes ou com erro).")
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
                                  log: Sink = print, map_index: int = 0,
                                  my_lineup: Optional[List[str]] = None,
                                  enemy_lineup: Optional[List[str]] = None,
                                  enemy_team_name: Optional[str] = None,
                                  enemy_team_logo: str = ""):
    """Serializa o ciclo inteiro de css_start + balanceamento.

    O mesmo lock é compartilhado pelas chamadas automáticas de run_match e
    pelo botão manual do wizard, evitando que duas sequências RCON se cruzem.
    No uso via CLI, cria um lock local por compatibilidade.
    map_index: mapa da série (0 = primeiro); ver _force_start_and_balance_bots.
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
            map_index=map_index,
            my_lineup=my_lineup,
            enemy_lineup=enemy_lineup,
            enemy_team_name=enemy_team_name,
            enemy_team_logo=enemy_team_logo,
        )


# Mapas 2..N da série sozinhos (P1.5). A espera do mapa seguinte começa logo
# depois do css_start do mapa anterior e dura o mapa inteiro (um mapa da
# série de 19/09 levou 70 min). O teto vale por espera, não pela série: uma
# MD3 longa passa de 3 h somando os mapas, e desistir antes do fim real do
# mapa anterior devolveria o mapa seguinte ao botão.
TETO_ESPERA_MAPA_S = 3 * 60 * 60
# O warmup do mapa novo não acaba sozinho (bots não contam como prontos):
# 5 s de atraso não custam nada e poupam chamadas ao docker.
INTERVALO_ESPERA_MAPA_S = 5
DOCKER_LOGS_TIMEOUT_S = 30
# Leitura pelo fim (o contorno do B0.7h): N linhas do fim, dobrando só se
# nenhuma delas for velha (lacuna possível), até o N dos ajudantes do smoke.
TAIL_PELO_FIM, TAIL_PELO_FIM_TETO = 200, 5000

_CARIMBO_DOCKER = re.compile(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?Z\s")
_FIM_DE_MAPA = re.compile(r"MATCH ENDED, remainingMaps: (\d+), NumMaps: (\d+), "
                          r"Team1SeriesScore: (\d+), Team2SeriesScore: (\d+)")


def _carimbo_ns(linha: str) -> Optional[int]:
    """Nanossegundos UTC do carimbo do `docker logs -t` no começo da linha."""
    achado = _CARIMBO_DOCKER.match(linha)
    if not achado:
        return None
    base, fracao = achado.groups()
    segundos = int(datetime.fromisoformat(base).replace(tzinfo=timezone.utc).timestamp())
    return segundos * 10**9 + int((fracao or "").ljust(9, "0"))


class CursorDockerLogs:
    """Lê o docker logs do container para a frente, sem reler (P1.5).

    O cursor é o carimbo da última linha lida e só avança. O caminho principal
    é o `docker logs -t --since <epoch do cursor>`, que devolve só o que veio
    depois dele. Com o json-file corrompido (armadilha "docker logs --since
    volta vazio", desde 18/10) o --since sai vazio com código 0: enquanto ele
    não trouxer nada novo, o cursor confere pelo fim (`--tail 200 -t`, filtrado
    pelo carimbo); se o fim tem linha nova, o --since está quebrado e a leitura
    segue pelo fim até o fim da série. Depois que o --since trouxe linha nova
    uma vez, não se confere mais. O --since é inclusivo: as linhas que já
    lemos no carimbo do cursor são puladas pela contagem (`vistas`).
    """

    def __init__(self, container_name: str, desde_ns: int, log: Sink = print):
        self.container_name = container_name
        self.ns, self.vistas = desde_ns, 0
        self.pelo_fim = False
        self.since_provado = False  # o --since já trouxe linha nova: não confere mais
        self.chamadas = 0     # chamadas de docker logs
        self.linhas_lidas = 0  # linhas que o docker devolveu (o volume relido)
        self.log = log

    @classmethod
    def no_fim_do_log(cls, container_name: str, log: Sink = print) -> "CursorDockerLogs":
        """Cursor na última linha do log do container (`--tail 1`), e não no
        relógio do Windows, que pode andar fora do da VM do Docker. Sem
        resposta, cai no relógio."""
        cursor = cls(container_name, int(time.time() * 10**9), log)
        linhas = cursor._docker("--tail", "1")
        if linhas:  # 1 ns depois dela: o grupo do mesmo carimbo fica para trás
            cursor.ns = linhas[-1][0] + 1
        return cursor

    def _docker(self, *args) -> Optional[list]:
        self.chamadas += 1
        try:
            r = subprocess.run(
                ["docker", "logs", "-t", *args, self.container_name],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
                timeout=DOCKER_LOGS_TIMEOUT_S,
            )
        except Exception:  # docker fora, timeout: nada lido nesta volta
            return None
        if r.returncode != 0:
            return None
        brutas = (r.stdout or "").splitlines() + (r.stderr or "").splitlines()
        self.linhas_lidas += len(brutas)
        carimbadas = [(ns, linha) for linha in brutas if (ns := _carimbo_ns(linha)) is not None]
        return sorted(carimbadas, key=lambda par: par[0])

    def _depois_do_cursor(self, linhas) -> list:
        novas, pular = [], self.vistas
        for ns, linha in linhas:
            if ns < self.ns:
                continue
            if ns == self.ns and pular:
                pular -= 1
                continue
            novas.append((ns, linha))
        return novas

    def avancar(self, ns: int):
        """Marca como lida a linha de carimbo `ns` (nunca volta)."""
        if ns > self.ns:
            self.ns, self.vistas = ns, 1
        elif ns == self.ns:
            self.vistas += 1

    def since(self) -> str:
        return f"{self.ns // 10**9}.{self.ns % 10**9:09d}"

    def _ler_pelo_fim(self) -> list:
        n, melhor, topo = TAIL_PELO_FIM, [], None
        while True:
            linhas = self._docker("--tail", str(n))
            if not linhas or (topo is not None and linhas[-1] != topo):
                break  # vazio, ou o N cruzou uma entrada corrompida
            topo = linhas[-1]
            melhor = self._depois_do_cursor(linhas)
            velha = linhas[0][0] < self.ns or (linhas[0][0] == self.ns and not self.vistas)
            if velha or len(linhas) < n:
                break
            if n >= TAIL_PELO_FIM_TETO:
                self.log(f"[AVISO] Mais de {n} linhas novas no docker logs entre duas "
                         "leituras: pode ter ficado linha sem ler.")
                break
            n = min(2 * n, TAIL_PELO_FIM_TETO)
        return melhor

    def novas(self) -> list:
        """[(carimbo_ns, linha)] depois do cursor, na ordem; não avança."""
        if not self.pelo_fim:
            novas = self._depois_do_cursor(self._docker("--since", self.since()) or [])
            if novas or self.since_provado:
                self.since_provado = self.since_provado or bool(novas)
                return novas
            novas = self._ler_pelo_fim()
            if novas:
                self.pelo_fim = True
                self.log("[AVISO] docker logs --since voltou sem as linhas novas que o --tail "
                         "mostra (json-file corrompido?); sigo lendo o log pelo fim.")
            return novas
        return self._ler_pelo_fim()


def _fim_da_serie(linha: str, decide_cedo: bool) -> bool:
    """MATCH ENDED sem mapa seguinte: remainingMaps 0, ou (clinch_series) um
    time já com a maioria dos mapas, como no 2-0 de uma MD3."""
    achado = _FIM_DE_MAPA.search(linha)
    if not achado:
        return False
    restantes, num_maps, placar1, placar2 = map(int, achado.groups())
    return restantes == 0 or (decide_cedo and max(placar1, placar2) > num_maps // 2)


def wait_for_next_map_warmup(container_name: str, since_ts: Optional[float] = None,
                              timeout_s: float = TETO_ESPERA_MAPA_S, log: Sink = print, *,
                              cursor: Optional[CursorDockerLogs] = None,
                              exigir_conexao: bool = True, decide_cedo: bool = True,
                              cancelado: Optional[Callable[[], Optional[str]]] = None,
                              relogio: Optional[Callable[[], float]] = None,
                              dormir: Optional[Callable[[float], None]] = None,
                              intervalo_s: float = INTERVALO_ESPERA_MAPA_S) -> bool:
    """
    Espera passivamente (só lendo docker logs) o próximo mapa de uma série
    BO3/BO5 carregar e entrar em warmup, pra saber a hora certa de repetir
    force_start_and_balance_bots(). Lê pelo `cursor` (o mesmo da série
    inteira, P1.5), ou, sem ele, a partir de `since_ts` (epoch).

    O mapa novo está pronto com, nesta ordem: `[ChangeMap]`, `[FULL CONNECT]`
    (você entrou no mapa novo; com exigir_conexao=False, sem jogador, não se
    espera) e `[StartWarmup]`. O `[StartWarmup]` que sai junto com o
    `[ChangeMap]` é do mapa velho: o changelevel só vem 3 s depois, e forçar
    o início ali montaria os times no mapa que está saindo (B1.12, seção 1).

    True com o mapa novo em warmup. False se a série acabou (remainingMaps 0
    ou série decidida, com decide_cedo), se `cancelado()` devolveu um motivo
    ou se o teto de `timeout_s` (contado do início desta espera) estourou.
    relogio/dormir: time.time/time.sleep, trocáveis no teste.
    """
    relogio = relogio or time.time
    dormir = dormir or time.sleep
    if cursor is None:
        inicio = relogio() if since_ts is None else since_ts
        cursor = CursorDockerLogs(container_name, int(inicio * 10**9), log)
    prazo = relogio() + timeout_s
    viu_changemap = viu_conexao = False
    while True:
        motivo = cancelado() if cancelado else None
        if motivo:
            log(f"[MATCHZY] Parei de esperar o próximo mapa: {motivo}.")
            return False
        for ns, linha in cursor.novas():
            cursor.avancar(ns)
            if _fim_da_serie(linha, decide_cedo):
                log("[MATCHZY] A série terminou; não há próximo mapa.")
                return False
            if "[MatchZy] [ChangeMap]" in linha:
                viu_changemap, viu_conexao = True, False
            elif viu_changemap and "[MatchZy] [FULL CONNECT]" in linha:
                viu_conexao = True
            elif (viu_changemap and (viu_conexao or not exigir_conexao)
                  and "[MatchZy] [StartWarmup]" in linha):
                return True
        if relogio() >= prazo:
            log(f"[AVISO] Teto de {timeout_s / 3600:g} h esperando o próximo mapa "
                "(ChangeMap -> FULL CONNECT -> StartWarmup).")
            return False
        dormir(intervalo_s)


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
              enemy_team_name: Optional[str] = None, enemy_team_logo: str = "",
              cancelar: Optional[threading.Event] = None):
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
    cancelar: Event opcional que interrompe a espera dos mapas 2..N da série
    (P1.5); o fim do watcher também interrompe.

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

    # P1.1: tudo o que esta partida diz (e o watcher, quando a saída dele
    # passa por aqui) também vai para logs/partidas/; depois o aviso do
    # candidato e o órfão, antes do compose_up e do loadmatch.
    nome_log = f"partida_{_carimbo_utc()}.log"
    log = sink_com_arquivo(log, ROOT / "logs" / "partidas", nome_log)
    if watcher_output is not None:
        watcher_output = sink_com_arquivo(watcher_output, ROOT / "logs" / "partidas", nome_log)
    aviso_candidato(ROOT / "data" / "candidato.json", log=log)
    preservar_orfao(ROOT / EVENTS_LIVE_DIR, log=log)

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
        # P1.1c: a mensagem vai pelo sink (TUI e logs/partidas/); o sys.exit
        # para a partida sem esperar, como os outros [ERRO] daqui.
        motivo = docker_fora_do_ar()
        if motivo is not None:
            log(f"[ERRO] {DOCKER_FORA_DO_AR}")
            log(f"[DOCKER] Detalhe: {motivo}")
            sys.exit("Partida não iniciada: o Docker não respondeu.")
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

    # P1.4: com o RCON no ar os plugins já carregaram; aviso antes do
    # loadmatch, para o opt-in abortar sem deixar partida carregada.
    if avisar_captura(container_name=container_name, rcon_host=rcon_host,
                      rcon_port=rcon_port, rcon_password=rcon_password, log=log):
        if watcher_proc is not None:
            watcher_proc.terminate()
        sys.exit(f"Partida não iniciada: a captura não carregou ({EXIGIR_CAPTURA}=1).")

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
    # P1.5: a espera dura o mapa anterior inteiro (teto de 3 h por mapa) e lê
    # o docker logs por um cursor só, da série toda, que nunca volta. Ela para
    # se quem chamou setar `cancelar` ou se o watcher encerrar: fechar a TUI
    # mata o watcher, e sem isso a worker thread seguraria o processo.
    serie = json.loads(local_match_config.read_text(encoding="utf-8"))
    num_maps = serie.get("num_maps", 1)
    cursor = CursorDockerLogs.no_fim_do_log(container_name, log=log) if num_maps > 1 else None

    def cancelado() -> Optional[str]:
        if cancelar is not None and cancelar.is_set():
            return "cancelado por quem iniciou a partida"
        if watcher_proc is not None and watcher_proc.poll() is not None:
            return "o watcher encerrou (TUI fechada ou Ctrl+C)"
        return None

    for map_index in range(2, num_maps + 1):
        log(f"\n[MATCHZY] Esperando o mapa {map_index}/{num_maps} da série carregar "
            f"(até {TETO_ESPERA_MAPA_S // 3600} h; ele começa sozinho quando você entrar)...")
        if not wait_for_next_map_warmup(container_name, log=log, cursor=cursor,
                                        exigir_conexao=bool(player),
                                        decide_cedo=serie.get("clinch_series", True) is not False,
                                        cancelado=cancelado):
            log("[AVISO] Não detectei o próximo mapa entrando em warmup "
                "(série já pode ter terminado) — seguindo sem forçar de novo.")
            break
        try:
            wait_for_rcon(rcon_host, rcon_port, rcon_password, timeout_s=60, log=log)
            force_start_and_balance_bots(
                rcon_host=rcon_host, rcon_port=rcon_port, rcon_password=rcon_password,
                container_name=container_name, team_size=team_size, player=player,
                local_match_config=local_match_config, rcon_lock=rcon_lock, log=log,
                map_index=map_index - 1,  # P1.6: map_sides[i] do mapa que entrou
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
