#!/usr/bin/env python3
"""
Integração TUI -> core.launch -> run_match (card T1.5, G4): a TUI headless
(Pilot) monta a partida, clica em "Iniciar partida" e no "já conectei", e o
wizard_core.launch e o start_match.run_match de verdade rodam até o fim
contra docker, RCON e watcher falsos. O teste confere o que sairia para o
servidor: o argv do `docker compose`, o argumento do `matchzy_loadmatch`, o
match_config escrito e o argv do watcher.

Os fakes são monkeypatch de Python nos módulos (start_match.subprocess,
start_match.RconClient, start_match.time): nenhum processo, rede ou porta.
Se algo escapar, as travas do tests/conftest.py (T1.4) levantam erro.
O ROOT aponta para uma pasta temporária com match_config e compose escritos
à mão: o docker/match_config.spike.json do repo nunca é lido nem escrito.
O wizard_tui.py não muda (AGENTS.md, D13).
"""
import asyncio
import io
import json
import subprocess
import sys
import threading
import time
import types

import pytest

import start_match
import wizard_core
import wizard_tui
from wizard_tui import (
    FormatScreen, IdentityScreen, LaunchScreen, MapSelectScreen, SideScreen,
    SummaryScreen, WizardApp,
)

TAMANHO = (100, 34)
NICK = "cobaia"
STEAMID = "76561190000000001"  # fictício, abaixo da base 76561197960265728
RCON_SENHA = "fake"

MATCH_CONFIG_BASE = {
    "num_maps": 1,
    "maplist": ["de_mirage"],
    "map_sides": ["team1_ct"],
    "clinch_series": True,
    "players_per_team": 5,
    "team1": {"name": NICK, "players": {STEAMID: NICK}},
    "team2": {"name": "Bots", "players": {"76561190000000002": "BotTeamPlaceholder"}},
}

# Resposta do `status` com 10 clientes (9 bots + você): o gate de
# wait_for_client_count do 5x5.
STATUS_10 = "---------players--------\n" + "".join(
    f"  {i} 00:01 0 0 active 0 'jogador{i}'\n" for i in range(10)) + "#end\n"


class EsperaIndevida(BaseException):
    """Docker fora do ar e mesmo assim o start_match seguiu para inspect,
    compose, watcher ou RCON (P1.1c). BaseException para não ser engolida
    pelos retries do wait_for_rcon: o teste falha em vez de travar no
    "já conectei"."""


class Servidor:
    """O que a partida mandaria para fora: chamadas de docker e de RCON."""

    def __init__(self):
        self.docker = []      # (argv, kwargs)
        self.popen = []       # argv do watcher
        self.rcon = []        # comandos, na ordem
        self.conexoes = []    # (host, porta, senha)
        self.lock = threading.Lock()
        self.daemon_no_ar = True  # P1.1c: False simula o Docker Desktop parado
        self.carimbo = int(time.time()) + 3600  # do docker logs -t, à frente do relógio

    # -- docker (start_match.subprocess.run) --------------------------------
    def run(self, argv, **kwargs):
        with self.lock:
            self.docker.append((list(argv), kwargs))
        assert argv[0] == "docker", argv
        if argv[1] == "version":
            if self.daemon_no_ar:
                return subprocess.CompletedProcess(argv, 0, "28.0.1\n", "")
            return subprocess.CompletedProcess(
                argv, 1, "", "error during connect: o daemon não responde\n")
        if not self.daemon_no_ar:
            raise EsperaIndevida(f"docker com o daemon fora do ar: {argv!r}")
        if argv[1] == "inspect":
            return subprocess.CompletedProcess(argv, 1, "", "No such object")
        if argv[1:3] == ["logs", "-t"]:
            # Série (P1.5): cada leitura traz o próximo mapa carregado, você
            # dentro e o warmup, com carimbos novos (o cursor só anda).
            with self.lock:
                self.carimbo += 3
                base = self.carimbo
            linhas = "".join(
                f"{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(base + i))}.000000000Z {texto}\n"
                for i, texto in enumerate(("[MatchZy] [ChangeMap]", "[MatchZy] [FULL CONNECT]",
                                           "[MatchZy] [StartWarmup]")))
            return subprocess.CompletedProcess(argv, 0, linhas, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    # -- watcher (start_match.subprocess.Popen) -----------------------------
    def Popen(self, argv, **kwargs):
        with self.lock:
            self.popen.append(list(argv))
        if not self.daemon_no_ar:
            raise EsperaIndevida(f"watcher com o daemon fora do ar: {argv!r}")
        # poll None: o watcher segue vivo (o fim dele interrompe a série, P1.5).
        return types.SimpleNamespace(stdout=io.StringIO(""), wait=lambda timeout=None: 0,
                                     poll=lambda: None, terminate=lambda: None,
                                     kill=lambda: None)

    # -- RCON (start_match.RconClient) --------------------------------------
    def cliente(self):
        servidor = self

        class RconFalso:
            def __init__(self, host, port, passwd=None, timeout=None):
                with servidor.lock:
                    servidor.conexoes.append((host, port, passwd))
                if not servidor.daemon_no_ar:
                    raise EsperaIndevida("RCON com o daemon fora do ar")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def run(self, comando):
                with servidor.lock:
                    servidor.rcon.append(comando)
                if comando == "echo start_match_ready":
                    return "start_match_ready"
                if comando.startswith("matchzy_loadmatch"):
                    return "Match config loaded"
                if comando == "status":
                    return STATUS_10
                return ""

        return RconFalso


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "match_config.spike.json").write_text(
        json.dumps(MATCH_CONFIG_BASE, indent=2), encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  cs2:\n    environment:\n      - CS2_MAXPLAYERS=11\n", encoding="utf-8")
    for modulo in (wizard_tui, wizard_core, start_match):
        monkeypatch.setattr(modulo, "ROOT", tmp_path)

    srv = Servidor()
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=srv.run, Popen=srv.Popen, PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT,
        TimeoutExpired=subprocess.TimeoutExpired))
    monkeypatch.setattr(start_match, "RconClient", srv.cliente())
    # Só o time do start_match: as esperas viram instantâneas, o resto do
    # processo (Textual, asyncio) segue com o time de verdade.
    monkeypatch.setattr(start_match, "time", types.SimpleNamespace(
        sleep=lambda s: None, time=time.time, strftime=time.strftime, gmtime=time.gmtime))
    return srv


@pytest.fixture
def launch_vigiado(monkeypatch):
    """O core.launch de verdade, com um aviso de fim e a exceção guardada:
    o do_launch da TUI engole qualquer erro no painel de log."""
    estado = types.SimpleNamespace(fim=threading.Event(), erro=None, logs=[])
    launch_real = wizard_core.launch

    def launch(setup, **kwargs):
        log_tela = kwargs["log"]

        def log(texto):
            estado.logs.append(texto)
            log_tela(texto)

        kwargs["log"] = log
        try:
            launch_real(setup, **kwargs)
        except BaseException as exc:
            estado.erro = exc
            raise
        finally:
            estado.fim.set()

    monkeypatch.setattr(wizard_core, "launch", launch)
    return estado


async def esperar(app, condicao, timeout=10.0, passo=0.05):
    inicio = time.monotonic()
    while time.monotonic() - inicio < timeout:
        if condicao():
            return
        await asyncio.sleep(passo)
    raise TimeoutError(f"condição não satisfeita em {timeout}s (tela: {app.screen!r})")


async def clicar(pilot, seletor):
    await pilot.click(seletor)
    await pilot.pause()
    await asyncio.sleep(0.25)  # o -active do Button ignora clique por 0.2 s


def lancar_pela_tui(formato, mapas, lados, launch_vigiado, ate_o_ready=True):
    """Monta a partida pela TUI e clica em "Iniciar partida" (e, com
    ate_o_ready, no "já conectei"). Devolve as linhas do painel de log."""
    tela = []

    async def roteiro():
        app = WizardApp(rcon_password=RCON_SENHA)  # skip_up=False: passa pelo compose
        async with app.run_test(size=TAMANHO) as pilot:
            await esperar(app, lambda: isinstance(app.screen, IdentityScreen))
            app.screen.query_one("#player_input").value = NICK
            await clicar(pilot, "#continue")
            await esperar(app, lambda: isinstance(app.screen, FormatScreen))
            await clicar(pilot, f"#{formato}")
            await clicar(pilot, "#continue")
            await esperar(app, lambda: isinstance(app.screen, MapSelectScreen))
            for mapa in mapas:
                await clicar(pilot, f"#map-{mapa}")
            await clicar(pilot, "#continue")
            await esperar(app, lambda: isinstance(app.screen, SideScreen))
            for i, lado in enumerate(lados):
                await esperar(app, lambda: bool(app.screen.query("#side_radio")))
                await clicar(pilot, f"#{lado}")
                await clicar(pilot, "#confirm")
                await esperar(app, lambda: app.session.side_index == i + 1)
            await esperar(app, lambda: isinstance(app.screen, SummaryScreen))
            await clicar(pilot, "#launch")
            await esperar(app, lambda: isinstance(app.screen, LaunchScreen))
            if ate_o_ready:
                await esperar(app, lambda: bool(app.screen.query("#ready")))
                await clicar(pilot, "#ready")
            await esperar(app, launch_vigiado.fim.is_set)
            await pilot.pause()
            await asyncio.sleep(0.25)  # o do_launch escreve o [ERRO] depois do fim
            await pilot.pause()
            tela.extend(linha.text for linha in app.screen.query_one("#log").lines)

    asyncio.run(roteiro())
    if ate_o_ready:
        assert launch_vigiado.erro is None, launch_vigiado.logs
    return tela


@pytest.mark.parametrize("formato, mapas, lados, sides_esperados", [
    ("bo1", ["de_nuke"], ["t"], ["team1_t"]),
    ("bo3", ["de_inferno", "de_ancient", "de_dust2"], ["ct", "t", "t"],
     ["team1_ct", "team1_t", "team1_t"]),
])
def test_tui_lanca_run_match_com_compose_e_loadmatch_certos(
        servidor, launch_vigiado, tmp_path, formato, mapas, lados, sides_esperados):
    lancar_pela_tui(formato, mapas, lados, launch_vigiado)

    # docker compose: o argv exato do start_match.compose_up, no ROOT.
    compose = [(argv, kw) for argv, kw in servidor.docker if argv[1] == "compose"]
    assert compose == [(
        ["docker", "compose", "-f", str(tmp_path / "docker-compose.yml"), "up", "-d"],
        {"check": True, "cwd": tmp_path},
    )]
    # P1.1c: antes de tudo, a conferência do daemon; com ele no ar, o
    # caminho segue o de antes (inspect e compose).
    assert servidor.docker[0] == (
        ["docker", "version", "--format", "{{.Server.Version}}"],
        {"capture_output": True, "text": True, "timeout": 10},
    )
    assert servidor.docker[1][0] == ["docker", "inspect", "-f", "{{.State.Running}}", "cs2-spike"]

    # RCON: sempre no servidor local, com a senha dada à TUI.
    assert set(servidor.conexoes) == {("127.0.0.1", 27015, RCON_SENHA)}
    loads = [c for c in servidor.rcon if c.startswith("matchzy_loadmatch")]
    assert loads == ["matchzy_loadmatch match_config.spike.json"]
    # O load vem depois do RCON responder e antes de forçar o início.
    i_load = servidor.rcon.index("matchzy_loadmatch match_config.spike.json")
    assert servidor.rcon.index("echo start_match_ready") < i_load
    assert i_load < servidor.rcon.index("css_start")
    # Um css_start por mapa da série (o run_match repete no mapa 2 e 3).
    assert servidor.rcon.count("css_start") == len(mapas)

    # O arquivo que o loadmatch carrega: o match_config que o launch escreveu.
    escrito = json.loads((tmp_path / "docker" / "match_config.spike.json")
                         .read_text(encoding="utf-8"))
    assert escrito == {
        "num_maps": len(mapas),
        "maplist": mapas,
        "map_sides": sides_esperados,
        "clinch_series": True,
        "players_per_team": 5,
        "team1": {"name": NICK, "players": {STEAMID: NICK}},
        "team2": {"name": "Bots", "players": {"76561190000000002": "BotTeamPlaceholder"}},
    }

    # watcher: argv montado, mas processo falso.
    assert servidor.popen == [[
        sys.executable, "-u", "watcher.py", "--mode", "matchzy", "--player", NICK,
        "--container", "cs2-spike",
        "--match-config", str(tmp_path / "docker" / "match_config.spike.json"),
    ]]


def test_tui_com_vanilla_ligado_sobe_o_compose_com_o_override(servidor, launch_vigiado, tmp_path):
    """Card P1.2: com "vanilla": true no data/servidor.json, o mesmo clique da
    TUI (sem diff nela) sobe o compose com o override empilhado depois do
    base. Com o vanilla off, o argv é o do teste acima, o de antes do P1.2."""
    (tmp_path / "docker-compose.vanilla.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "servidor.json").write_text('{"vanilla": true}', encoding="utf-8")
    lancar_pela_tui("bo1", ["de_nuke"], ["t"], launch_vigiado)

    compose = [(argv, kw) for argv, kw in servidor.docker if argv[1] == "compose"]
    assert compose == [(
        ["docker", "compose", "-f", str(tmp_path / "docker-compose.yml"),
         "-f", str(tmp_path / "docker-compose.vanilla.yml"), "up", "-d"],
        {"check": True, "cwd": tmp_path},
    )]
    assert [c for c in servidor.rcon if c.startswith("matchzy_loadmatch")] == \
        ["matchzy_loadmatch match_config.spike.json"]


def test_tui_com_o_docker_fora_do_ar_mostra_a_mensagem_e_nao_espera(
        servidor, launch_vigiado, tmp_path):
    """Card P1.1c: com o Docker Desktop parado, o clique em "Iniciar partida"
    termina logo com a mensagem clara no painel da TUI (sem diff no
    wizard_tui.py: ela sai pelo sink do start_match) e no log da partida, sem
    compose, RCON nem watcher."""
    servidor.daemon_no_ar = False
    inicio = time.monotonic()
    tela = lancar_pela_tui("bo1", ["de_nuke"], ["t"], launch_vigiado, ate_o_ready=False)
    assert time.monotonic() - inicio < 30  # o roteiro inteiro; sem esperar o boot

    assert isinstance(launch_vigiado.erro, SystemExit)
    msg = "[ERRO] Docker Desktop não está rodando: abra o Docker Desktop e tente de novo."
    assert msg in tela, tela
    assert "[DOCKER] Detalhe: error during connect: o daemon não responde" in tela, tela
    assert "[ERRO] Partida não iniciada: o Docker não respondeu." in tela, tela

    # Só o `docker version`: nada de inspect, compose, RCON ou watcher.
    assert [argv for argv, _kw in servidor.docker] == [
        ["docker", "version", "--format", "{{.Server.Version}}"]]
    assert servidor.rcon == [] and servidor.conexoes == [] and servidor.popen == []

    arquivos = list((tmp_path / "logs" / "partidas").glob("partida_*.log"))
    assert len(arquivos) == 1, arquivos
    assert msg in arquivos[0].read_text(encoding="utf-8")
