#!/usr/bin/env python3
"""
Suíte hermética (card T1.4): nenhum teste lê ou escreve o banco real, roda
docker ou abre conexão para fora da máquina, com ou sem o Docker no PATH.

Antes da coleta (pytest_configure, antes de qualquer tests/test_*.py importar
o app), numa pasta temporária da sessão:

- golden.db: o schema do parser.init_db, sem partida (o mesmo banco do
  tools/web_golden.py), somente leitura. O `config.DB_PATH` aponta para ele;
  os módulos que fazem `from config import DB_PATH` (home, matches, report,
  parser, watcher, web.app) já importam o valor trocado. Era a causa das 42
  falhas `no such table: matches`: o "./cs2_tracker.db" relativo abria um
  banco vazio no worktree (ou o banco real, rodando do checkout principal).
- os outros caminhos do config (report, home, demos e as pastas *-live, o
  docker/events-live incluído) também vão para a pasta da sessão.

Travas que valem para a sessão inteira, inclusive na coleta:

- docker: `Popen._execute_child` (por onde passam run, check_output, call e
  Popen) e `os.system` recusam o executável docker com DockerProibido. Ela
  herda de FileNotFoundError de propósito: é o mesmo erro do docker fora do
  PATH, e o app já trata esse caso (catálogo vazio no wizard web). Teste que
  precisa do docker usa fake via monkeypatch, como já fazem os de hoje.
- rede: connect, connect_ex e sendto só passam para loopback numa porta que
  um socket deste processo abriu (o socketpair do asyncio no Windows, que o
  TestClient usa); o resto, inclusive o RCON local e a porta 8000, levanta
  RedeProibida.
- sqlite3.connect só abre banco na pasta temporária (tmp_path, a da sessão)
  ou em tests/fixtures; fora disso levanta BancoProibido sem abrir nada, e o
  teste falha no fim mesmo que o código tenha engolido o erro.

Por teste (autouse): o `web.app.PROFILE_PATH` vai para uma pasta temporária
do teste, nunca o data/profile.json. A fixture `hermetico` dá aos testes as
classes de erro e a pasta da sessão (tests/test_hermetico.py).
"""
from __future__ import annotations

import ipaddress
import os
import re
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import types
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

FIXTURES = RAIZ / "tests" / "fixtures"


class DockerProibido(FileNotFoundError):
    """A suíte nunca roda docker (T1.4): use fake via monkeypatch."""


class RedeProibida(ConnectionRefusedError):
    """A suíte nunca abre conexão para fora deste processo (T1.4)."""


class BancoProibido(RuntimeError):
    """A suíte só abre banco em pasta temporária ou em tests/fixtures (T1.4)."""


# ---------------------------------------------------------------- docker

_PROGRAMAS_DOCKER = {"docker", "docker-compose", "com.docker.cli"}
_DOCKER_NO_SHELL = re.compile(r"""(?:^|[\s&|;("'/\\])docker(?:-compose)?(?:\.exe)?(?=["'\s]|$)""", re.I)


def _nome_programa(args, executable) -> str:
    if executable:
        alvo = os.fsdecode(executable)
    elif isinstance(args, (str, bytes, os.PathLike)):
        texto = os.fsdecode(args).strip()
        alvo = texto[1:].split('"', 1)[0] if texto.startswith('"') else (texto.split() or [""])[0]
    else:
        args = list(args)
        alvo = os.fsdecode(args[0]) if args else ""
    nome = re.split(r"[\\/]", alvo)[-1].lower()
    return nome[:-4] if nome.endswith(".exe") else nome


def e_docker(args, executable=None, shell=False) -> bool:
    """True se o processo pedido é o docker (direto ou por um shell)."""
    if _nome_programa(args, executable) in _PROGRAMAS_DOCKER:
        return True
    if shell:
        texto = os.fsdecode(args) if isinstance(args, (str, bytes, os.PathLike)) else " ".join(map(str, args))
        return bool(_DOCKER_NO_SHELL.search(texto))
    return False


def _recusar_docker(args):
    raise DockerProibido(f"docker proibido na suíte (card T1.4); use fake via monkeypatch: {args!r}")


# ---------------------------------------------------------------- rede

_portas_deste_processo: set = set()


def _e_loopback(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    host = str(host).split("%", 1)[0]
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _conferir_destino(sock, endereco) -> None:
    if sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(endereco, tuple):
        host, porta = endereco[0], endereco[1]
        if _e_loopback(host) and porta in _portas_deste_processo:
            return
    raise RedeProibida(f"conexão proibida na suíte (card T1.4): {endereco!r}; use fake via monkeypatch")


# ---------------------------------------------------------------- banco

_violacoes_banco: list = []


def _caminho_do_banco(database, uri: bool):
    """Caminho no disco que o sqlite3 abriria, ou None se é em memória."""
    if isinstance(database, (bytes, os.PathLike)):
        database = os.fsdecode(database)
    database = str(database)
    if database in ("", ":memory:"):
        return None
    if uri and database.startswith("file:"):
        partes = urllib.parse.urlsplit(database)
        consulta = urllib.parse.parse_qs(partes.query)
        if "memory" in consulta.get("mode", []) or partes.path in ("", ":memory:"):
            return None
        return Path(urllib.request.url2pathname(partes.path))
    return Path(database)


def _dentro(caminho: Path, raiz: Path) -> bool:
    c = os.path.normcase(str(caminho))
    r = os.path.normcase(str(raiz)).rstrip("\\/")
    return c == r or c.startswith(r + os.sep)


def banco_permitido(caminho: Path, raizes) -> bool:
    caminho = Path(caminho).resolve()
    return any(_dentro(caminho, Path(r).resolve()) for r in raizes)


# ---------------------------------------------------------------- sessão

_estado = types.SimpleNamespace(pasta=None, golden=None, raizes=[], desfazer=[])


def _trocar(alvo, nome, valor):
    antigo = getattr(alvo, nome)
    setattr(alvo, nome, valor)
    _estado.desfazer.append((alvo, nome, antigo))


def _instalar_travas():
    execute_child = subprocess.Popen._execute_child

    def _execute_child_guardado(self, args, executable, *resto, **kw):
        # Mesma ordem no Windows e no POSIX: preexec_fn, close_fds, pass_fds,
        # cwd, env, startupinfo, creationflags, shell...
        shell = kw.get("shell", resto[7] if len(resto) > 7 else False)
        if e_docker(args, executable, shell):
            _recusar_docker(args)
        return execute_child(self, args, executable, *resto, **kw)

    os_system = os.system

    def _system_guardado(comando):
        if e_docker(comando, shell=True):
            _recusar_docker(comando)
        return os_system(comando)

    _trocar(subprocess.Popen, "_execute_child", _execute_child_guardado)
    _trocar(os, "system", _system_guardado)

    bind = socket.socket.bind
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex
    sendto = socket.socket.sendto

    def _bind(self, endereco):
        bind(self, endereco)
        try:
            nome = self.getsockname()
        except OSError:
            return
        if isinstance(nome, tuple) and _e_loopback(nome[0]):
            _portas_deste_processo.add(nome[1])

    def _connect(self, endereco):
        _conferir_destino(self, endereco)
        return connect(self, endereco)

    def _connect_ex(self, endereco):
        _conferir_destino(self, endereco)
        return connect_ex(self, endereco)

    def _sendto(self, dados, *resto):
        _conferir_destino(self, resto[-1])
        return sendto(self, dados, *resto)

    _trocar(socket.socket, "bind", _bind)
    _trocar(socket.socket, "connect", _connect)
    _trocar(socket.socket, "connect_ex", _connect_ex)
    _trocar(socket.socket, "sendto", _sendto)

    conectar = sqlite3.connect

    def _connect_sqlite(database, *args, **kwargs):
        uri = kwargs.get("uri", args[6] if len(args) > 6 else False)
        caminho = _caminho_do_banco(database, bool(uri))
        if caminho is not None and not banco_permitido(caminho, _estado.raizes):
            erro = BancoProibido(
                f"banco fora da pasta temporária e de tests/fixtures (card T1.4): {caminho}")
            _violacoes_banco.append(str(caminho))
            raise erro
        return conectar(database, *args, **kwargs)

    _trocar(sqlite3, "connect", _connect_sqlite)


def _apontar_config(pasta: Path, golden: Path):
    import config

    _trocar(config, "DB_PATH", str(golden))
    for nome, destino in (("REPORT_PATH", "report.html"), ("HOME_PATH", "index.html"),
                          ("DEMO_DIR", "demos"), ("DEMOS_LIVE_DIR", "demos-live"),
                          ("STATS_LIVE_DIR", "stats-live"), ("EVENTS_LIVE_DIR", "events-live")):
        _trocar(config, nome, str(pasta / destino))


def pytest_configure(config):
    pasta = Path(tempfile.mkdtemp(prefix="cs2tracker_suite_")).resolve()
    _estado.pasta = pasta
    _estado.raizes = [pasta, Path(tempfile.gettempdir()), FIXTURES]
    basetemp = config.option.basetemp
    if basetemp:
        _estado.raizes.append(Path(basetemp))
    _instalar_travas()

    import parser as parser_demos

    golden = pasta / "golden.db"
    parser_demos.init_db(str(golden)).close()
    os.chmod(golden, stat.S_IREAD)
    _estado.golden = golden
    _apontar_config(pasta, golden)


def pytest_unconfigure(config):
    while _estado.desfazer:
        alvo, nome, antigo = _estado.desfazer.pop()
        setattr(alvo, nome, antigo)
    if _estado.pasta is not None:
        if _estado.golden is not None and _estado.golden.exists():
            os.chmod(_estado.golden, stat.S_IREAD | stat.S_IWRITE)
        shutil.rmtree(_estado.pasta, ignore_errors=True)


@pytest.fixture
def hermetico():
    """As travas da suíte, para os testes que provam que elas valem."""
    return types.SimpleNamespace(
        DockerProibido=DockerProibido, RedeProibida=RedeProibida, BancoProibido=BancoProibido,
        pasta=_estado.pasta, golden=_estado.golden, violacoes_banco=_violacoes_banco,
        e_docker=e_docker, conferir_destino=_conferir_destino,
        banco_permitido=lambda caminho: banco_permitido(caminho, _estado.raizes))


@pytest.fixture(autouse=True)
def _suite_hermetica(request, monkeypatch, tmp_path_factory):
    webapp = sys.modules.get("web.app")
    if webapp is not None:
        monkeypatch.setattr(webapp, "PROFILE_PATH", tmp_path_factory.mktemp("perfil") / "profile.json")
    _violacoes_banco.clear()
    yield
    if _violacoes_banco:
        abertos = list(_violacoes_banco)
        _violacoes_banco.clear()
        pytest.fail(f"o teste tentou abrir banco fora da pasta temporária: {abertos}")
