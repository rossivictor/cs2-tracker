#!/usr/bin/env python3
"""
Container pausado (card P1.15): pausado, o `docker inspect` diz
State.Running = true e State.Paused = true. Antes, o start_match lia só o
Running, pulava o compose up e ficava em "Esperando RCON" para sempre
(docs/armadilhas/windows-e-docker.md). Agora ele confere o Paused antes da
espera do RCON, diz a causa e o que fazer pelo sink (o que a TUI mostra) e
para, sem despausar.

Docker falso por monkeypatch em start_match.subprocess, com a saída do
`docker inspect` de tests/fixtures/docker_inspect_state.json. O caminho pela
TUI (Pilot) está em tests/test_tui_integracao.py.
"""
import json
import subprocess
import types
from pathlib import Path

import pytest

import start_match

AMOSTRA = json.loads((Path(__file__).parent / "fixtures" / "docker_inspect_state.json")
                     .read_text(encoding="utf-8"))

ARGV_VERSION = ["docker", "version", "--format", "{{.Server.Version}}"]
ARGV_RUNNING = ["docker", "inspect", "-f", "{{.State.Running}}", "cs2-teste"]
ARGV_STATE = ["docker", "inspect", "-f", "{{json .State}}", "cs2-teste"]

MENSAGEM = (
    "[ERRO] O container 'cs2-teste' está pausado no Docker Desktop: o servidor parou no meio "
    "e o RCON não vai responder. Abra o Docker Desktop, dê play (Resume) no container "
    "e tente de novo; se o servidor cair ao despausar, tente de novo que ele sobe do zero."
)


class DockerFalso:
    """Daemon no ar e o container no estado pedido ("pausado" ou "rodando"):
    o `{{.State.Running}}` diz `true` nos dois, como o docker de verdade."""

    def __init__(self, estado):
        self.estado = estado
        self.chamadas = []

    def run(self, argv, **kwargs):
        self.chamadas.append((list(argv), kwargs))
        if argv[:2] == ["docker", "version"]:
            return subprocess.CompletedProcess(argv, 0, "28.0.1\n", "")
        if argv[:4] == ["docker", "inspect", "-f", "{{.State.Running}}"]:
            return subprocess.CompletedProcess(argv, 0, "true\n", "")
        if argv[:4] == ["docker", "inspect", "-f", "{{json .State}}"]:
            return subprocess.CompletedProcess(argv, 0, AMOSTRA[self.estado], "")
        raise AssertionError(f"docker inesperado: {argv!r}")


def _docker(monkeypatch, estado):
    falso = DockerFalso(estado)
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=falso.run, TimeoutExpired=subprocess.TimeoutExpired))
    return falso


def _saida(monkeypatch, rc, stdout):
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=lambda argv, **kw: subprocess.CompletedProcess(argv, rc, stdout, "")))


# ------------------------------------------------------ container_pausado

def test_pausado_de_verdade_e_running_true_e_pausado(monkeypatch):
    falso = _docker(monkeypatch, "pausado")
    # O bug: o Running sozinho diz que está tudo bem.
    assert start_match.container_running("cs2-teste") is True
    assert start_match.container_pausado("cs2-teste") is True
    assert falso.chamadas[-1] == (ARGV_STATE, {"capture_output": True, "text": True})


def test_rodando_nao_e_pausado(monkeypatch):
    _docker(monkeypatch, "rodando")
    assert start_match.container_pausado("cs2-teste") is False


@pytest.mark.parametrize("rc, stdout", [
    (1, ""),                       # No such object
    (0, "isto não é json\n"),
    (0, "[]\n"),
    (0, '{"Paused":"true"}\n'),    # só o booleano true conta
])
def test_saida_estranha_conta_como_nao_pausado(monkeypatch, rc, stdout):
    _saida(monkeypatch, rc, stdout)
    assert start_match.container_pausado("cs2-teste") is False


# ------------------------------------------------------ run_match

class Parar(Exception):
    """Interrompe o run_match no wait_for_rcon (o caminho feliz chegou lá)."""


@pytest.fixture
def mundo(tmp_path, monkeypatch):
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


def _rodar(mundo):
    start_match.run_match(
        container_name="cs2-teste", match_config="match_config.spike.json",
        compose_file="docker-compose.yml", rcon_host="127.0.0.1", rcon_port=27015,
        rcon_password="fake", team_size=5, boot_timeout=300, skip_up=False,
        player=None, log=mundo.logs.append)


def test_container_pausado_da_a_causa_e_sai_sem_esperar_o_rcon(mundo, monkeypatch, tmp_path):
    falso = _docker(monkeypatch, "pausado")
    with pytest.raises(SystemExit) as saida:
        _rodar(mundo)

    assert str(saida.value) == "Partida não iniciada: o container do servidor está pausado."
    assert mundo.logs[-1] == MENSAGEM
    arquivos = list((tmp_path / "logs" / "partidas").glob("partida_*.log"))
    assert len(arquivos) == 1, arquivos
    assert arquivos[0].read_text(encoding="utf-8").splitlines()[-1][9:] == MENSAGEM
    # Sem compose, sem unpause, sem espera do RCON.
    assert [argv for argv, _kw in falso.chamadas] == [ARGV_VERSION, ARGV_RUNNING, ARGV_STATE]
    assert mundo.esperas == []
    assert not any("já está rodando" in linha for linha in mundo.logs)


def test_container_rodando_segue_como_antes(mundo, monkeypatch):
    falso = _docker(monkeypatch, "rodando")
    with pytest.raises(Parar):
        _rodar(mundo)

    assert [argv for argv, _kw in falso.chamadas] == [ARGV_VERSION, ARGV_RUNNING, ARGV_STATE]
    assert "[DOCKER] Container 'cs2-teste' já está rodando." in mundo.logs
    assert MENSAGEM not in mundo.logs
    assert mundo.esperas == ["wait_for_rcon"]
