#!/usr/bin/env python3
"""
Docker fora do ar (card P1.1c): antes do compose up, o start_match confere
se o daemon responde (`docker version` com timeout curto). Fora do ar, a
mensagem clara sai pelo sink (TUI e logs/partidas/) e o run_match para na
hora; no ar, segue como antes.

Docker falso por monkeypatch em start_match.subprocess: nenhum processo
real (o tests/conftest.py barra o docker de verdade, T1.4). O caminho pela
TUI (Pilot) está em tests/test_tui_integracao.py.
"""
import subprocess
import types

import pytest

import start_match

MENSAGEM = "[ERRO] Docker Desktop não está rodando: abra o Docker Desktop e tente de novo."
ARGV_VERSION = ["docker", "version", "--format", "{{.Server.Version}}"]


class DockerFalso:
    """Anota cada `subprocess.run` e responde o `docker version` com o
    comportamento pedido: "no_ar", "fora" (rc 1), "timeout" ou "ausente"."""

    def __init__(self, modo):
        self.modo = modo
        self.chamadas = []

    def run(self, argv, **kwargs):
        self.chamadas.append((list(argv), kwargs))
        if argv[:2] == ["docker", "version"]:
            if self.modo == "ausente":
                raise FileNotFoundError(2, "O sistema não pode encontrar o arquivo especificado")
            if self.modo == "timeout":
                raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))
            if self.modo == "fora":
                return subprocess.CompletedProcess(
                    argv, 1, "",
                    "Client:\n Version: 28.0.1\n\n"
                    "error during connect: open //./pipe/dockerDesktopLinuxEngine: "
                    "O sistema não pode encontrar o arquivo especificado.\n")
            return subprocess.CompletedProcess(argv, 0, "28.0.1\n", "")
        if argv[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(argv, 1, "", "No such object")
        return subprocess.CompletedProcess(argv, 0, "", "")


def _docker(monkeypatch, modo):
    falso = DockerFalso(modo)
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=falso.run, TimeoutExpired=subprocess.TimeoutExpired,
        CompletedProcess=subprocess.CompletedProcess))
    return falso


# ------------------------------------------------------ docker_fora_do_ar

def test_daemon_no_ar_devolve_none_com_timeout_curto(monkeypatch):
    falso = _docker(monkeypatch, "no_ar")
    assert start_match.docker_fora_do_ar() is None
    assert falso.chamadas == [
        (ARGV_VERSION, {"capture_output": True, "text": True, "timeout": 10})]


def test_daemon_fora_devolve_a_ultima_linha_do_erro(monkeypatch):
    _docker(monkeypatch, "fora")
    assert start_match.docker_fora_do_ar() == (
        "error during connect: open //./pipe/dockerDesktopLinuxEngine: "
        "O sistema não pode encontrar o arquivo especificado.")


def test_daemon_fora_sem_stderr_diz_o_codigo(monkeypatch):
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", ""),
        TimeoutExpired=subprocess.TimeoutExpired))
    assert start_match.docker_fora_do_ar() == "docker version saiu com código 1"


def test_daemon_que_nao_responde_vira_timeout(monkeypatch):
    _docker(monkeypatch, "timeout")
    assert start_match.docker_fora_do_ar() == "o daemon do Docker não respondeu em 10s"


def test_docker_fora_do_path(monkeypatch):
    _docker(monkeypatch, "ausente")
    assert start_match.docker_fora_do_ar() == "o comando docker não está no PATH"


def test_qualquer_outro_erro_tambem_conta_como_fora(monkeypatch):
    def explode(argv, **kw):
        raise PermissionError(13, "Acesso negado")
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=explode, TimeoutExpired=subprocess.TimeoutExpired))
    assert start_match.docker_fora_do_ar() == "falha ao chamar o docker ([Errno 13] Acesso negado)"


# ------------------------------------------------------ run_match

class Parar(Exception):
    """Interrompe o run_match no wait_for_rcon (o caminho feliz chegou lá)."""


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """ROOT em tmp_path; esperas e RCON viram falha imediata, para que
    qualquer espera indevida apareça como erro, não como teste lento."""
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  cs2:\n    environment:\n      - CS2_MAXPLAYERS=11\n", encoding="utf-8")
    monkeypatch.setattr(start_match, "ROOT", tmp_path)
    monkeypatch.setattr(start_match, "EVENTS_LIVE_DIR", "./docker/events-live")
    estado = types.SimpleNamespace(logs=[], esperas=[])

    def wait_for_rcon(*_a, **_k):
        estado.esperas.append("wait_for_rcon")
        raise Parar

    def proibido(*_a, **_k):
        raise AssertionError("o run_match não devia esperar nem dormir aqui")

    monkeypatch.setattr(start_match, "wait_for_rcon", wait_for_rcon)
    monkeypatch.setattr(start_match, "time", types.SimpleNamespace(sleep=proibido, time=proibido))
    return estado


def _rodar(mundo, skip_up=False):
    start_match.run_match(
        container_name="cs2-teste", match_config="match_config.spike.json",
        compose_file="docker-compose.yml", rcon_host="127.0.0.1", rcon_port=27015,
        rcon_password="fake", team_size=5, boot_timeout=300, skip_up=skip_up,
        player=None, log=mundo.logs.append)


def _log_da_partida(tmp_path):
    arquivos = list((tmp_path / "logs" / "partidas").glob("partida_*.log"))
    assert len(arquivos) == 1, arquivos
    return [linha[9:] for linha in arquivos[0].read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("modo, detalhe", [
    ("fora", "[DOCKER] Detalhe: error during connect: open //./pipe/dockerDesktopLinuxEngine: "
             "O sistema não pode encontrar o arquivo especificado."),
    ("timeout", "[DOCKER] Detalhe: o daemon do Docker não respondeu em 10s"),
    ("ausente", "[DOCKER] Detalhe: o comando docker não está no PATH"),
])
def test_docker_fora_do_ar_da_a_mensagem_e_sai_sem_esperar(mundo, monkeypatch, tmp_path,
                                                            modo, detalhe):
    falso = _docker(monkeypatch, modo)
    with pytest.raises(SystemExit) as saida:
        _rodar(mundo)

    assert str(saida.value) == "Partida não iniciada: o Docker não respondeu."
    # Sink (o que a TUI mostra) e log da partida: a mensagem clara e o detalhe.
    assert mundo.logs[-2:] == [MENSAGEM, detalhe]
    assert _log_da_partida(tmp_path)[-2:] == [MENSAGEM, detalhe]
    # Só o `docker version`: nem inspect, nem compose, nem espera do RCON.
    assert [argv for argv, _kw in falso.chamadas] == [ARGV_VERSION]
    assert mundo.esperas == []


def test_docker_no_ar_segue_como_hoje(mundo, monkeypatch, tmp_path):
    falso = _docker(monkeypatch, "no_ar")
    with pytest.raises(Parar):
        _rodar(mundo)

    assert [argv for argv, _kw in falso.chamadas] == [
        ARGV_VERSION,
        ["docker", "inspect", "-f", "{{.State.Running}}", "cs2-teste"],
        ["docker", "compose", "-f", str(tmp_path / "docker-compose.yml"), "up", "-d"],
    ]
    assert falso.chamadas[2][1] == {"check": True, "cwd": tmp_path}
    assert MENSAGEM not in mundo.logs
    assert "[DOCKER] Subindo servidor (docker-compose.yml)..." in mundo.logs
    assert mundo.esperas == ["wait_for_rcon"]


def test_com_skip_up_nao_confere_o_daemon(mundo, monkeypatch):
    """--skip-up (container já de pé) não passa pelo compose up: segue como
    antes, sem a conferência nova."""
    falso = _docker(monkeypatch, "fora")
    with pytest.raises(Parar):
        _rodar(mundo, skip_up=True)
    assert falso.chamadas == []
    assert MENSAGEM not in mundo.logs
