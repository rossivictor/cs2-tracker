#!/usr/bin/env python3
"""
Prova das travas do tests/conftest.py (card T1.4): a suíte não roda docker,
não abre conexão para fora do processo e não abre o banco real.

Nenhum teste aqui chama o docker de verdade nem conecta em porta viva: o
docker pedido é um caminho que não existe (sem a trava, o erro seria o
FileNotFoundError comum, não o DockerProibido), o host de rede é um nome
.invalid (sem a trava, gaierror) e o banco recusado fica numa pasta que não
existe (sem a trava, OperationalError). Os gabaritos são escritos à mão.
"""
import os
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DOCKER_FALSO = str(RAIZ / "pasta_que_nao_existe_t14" / "docker.exe")


def _checkout_principal() -> Path:
    """O checkout principal: o próprio RAIZ, ou o dono do worktree (só
    caminho, sem abrir nada além do arquivo .git)."""
    marca = RAIZ / ".git"
    if marca.is_file():
        gitdir = Path(marca.read_text(encoding="utf-8").split("gitdir:", 1)[1].strip())
        return gitdir.parents[2]  # <principal>/.git/worktrees/<nome>
    return RAIZ


# ------------------------------------------------------------------ docker

@pytest.mark.parametrize("args, shell, esperado", [
    (["docker", "cp", "cs2-spike:/x", "y"], False, True),
    (["C:/Program Files/Docker/docker.exe", "ps"], False, True),
    (["docker-compose.exe", "down"], False, True),
    ('"C:/Program Files/Docker/docker.exe" logs cs2-spike', False, True),
    ("docker compose up -d", True, True),
    ("cd . && docker ps", True, True),
    ("C:\\Docker\\docker.exe ps", True, True),
    ('"C:/Docker/docker" ps', True, True),
    ("git log -- docker/x", True, False),
    (["git", "add", "docker"], False, False),
    (["git", "log", "--", "docker/match_config.spike.json"], False, False),
    ("git status docker", False, False),
    ([sys.executable, "-c", "print(1)"], False, False),
])
def test_reconhece_o_docker_pelo_programa(hermetico, args, shell, esperado):
    assert hermetico.e_docker(args, None, shell) is esperado


def test_subprocess_run_recusa_docker(hermetico):
    with pytest.raises(hermetico.DockerProibido, match="card T1.4"):
        subprocess.run([DOCKER_FALSO, "ps"], capture_output=True)


def test_check_output_e_popen_recusam_docker(hermetico):
    with pytest.raises(hermetico.DockerProibido):
        subprocess.check_output([DOCKER_FALSO, "cp", "cs2-spike:/x", "y"])
    with pytest.raises(hermetico.DockerProibido):
        subprocess.Popen(f'"{DOCKER_FALSO}" logs cs2-spike')


def test_shell_e_os_system_recusam_docker(hermetico):
    with pytest.raises(hermetico.DockerProibido):
        subprocess.run(f'cd . && "{DOCKER_FALSO}" ps', shell=True)
    with pytest.raises(hermetico.DockerProibido):
        os.system(f'"{DOCKER_FALSO}" compose down')


def test_docker_proibido_e_o_mesmo_erro_do_docker_fora_do_path(hermetico):
    # O app trata FileNotFoundError como "docker ausente" (catálogo vazio).
    assert issubclass(hermetico.DockerProibido, FileNotFoundError)


def test_processo_que_nao_e_docker_continua_rodando():
    feito = subprocess.run([sys.executable, "-c", "print('ok')"], capture_output=True, text=True)
    assert feito.returncode == 0 and feito.stdout.strip() == "ok"


# ------------------------------------------------------------------ rede

def test_conexao_para_fora_e_recusada(hermetico):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(hermetico.RedeProibida, match="card T1.4"):
            sock.connect(("servidor.invalid", 27015))
        with pytest.raises(hermetico.RedeProibida):
            sock.connect_ex(("servidor.invalid", 80))
    finally:
        sock.close()


def test_udp_para_fora_e_recusado(hermetico):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(hermetico.RedeProibida):
            sock.sendto(b"x", ("servidor.invalid", 27015))
    finally:
        sock.close()


def test_loopback_em_porta_alheia_e_recusado(hermetico):
    # RCON local e a 8000 do Victor: loopback, mas porta que este processo
    # não abriu. O socket falso não conecta em nada: só a conferência roda.
    falso = types.SimpleNamespace(family=socket.AF_INET)
    for porta in (27015, 8000):
        with pytest.raises(hermetico.RedeProibida):
            hermetico.conferir_destino(falso, ("127.0.0.1", porta))
    with pytest.raises(hermetico.RedeProibida):
        hermetico.conferir_destino(falso, ("localhost", 27015))


def test_socketpair_do_proprio_processo_funciona():
    # O asyncio do TestClient usa socketpair (loopback, porta deste processo).
    a, b = socket.socketpair()
    try:
        a.sendall(b"t14")
        assert b.recv(3) == b"t14"
    finally:
        a.close()
        b.close()


# ------------------------------------------------------------------ banco

def test_config_e_app_apontam_para_o_golden(hermetico):
    import config
    import home
    import web.app as webapp

    golden = str(hermetico.golden)
    assert golden.endswith("golden.db")
    assert config.DB_PATH == golden
    assert home.DB_PATH == golden
    assert webapp.DB_PATH == golden
    assert Path(golden).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
    for nome in ("EVENTS_LIVE_DIR", "STATS_LIVE_DIR", "DEMOS_LIVE_DIR", "REPORT_PATH", "HOME_PATH"):
        assert Path(getattr(config, nome)).parent == hermetico.pasta, nome


def test_golden_tem_o_schema_e_nenhuma_partida(hermetico):
    conn = sqlite3.connect(hermetico.golden.as_uri() + "?mode=ro", uri=True)
    try:
        assert conn.execute("select count(*) from matches").fetchone() == (0,)
    finally:
        conn.close()
    assert not hermetico.golden.stat().st_mode & stat.S_IWRITE  # somente leitura


def test_banco_fora_da_pasta_temporaria_e_recusado(hermetico):
    proibido = RAIZ / "pasta_que_nao_existe_t14" / "cs2_tracker.db"
    with pytest.raises(hermetico.BancoProibido, match="card T1.4"):
        sqlite3.connect(str(proibido))
    with pytest.raises(hermetico.BancoProibido):
        sqlite3.connect(proibido.as_uri() + "?mode=ro", uri=True)
    assert hermetico.violacoes_banco == [str(proibido), str(proibido)]
    hermetico.violacoes_banco.clear()  # senão o conftest falha este teste no fim


def test_banco_do_checkout_principal_nunca_e_permitido(hermetico):
    # Só a regra de caminho: nada é aberto.
    for raiz in {RAIZ, _checkout_principal()}:
        assert not hermetico.banco_permitido(raiz / "cs2_tracker.db")


def test_banco_em_tmp_e_em_memoria_passam(tmp_path):
    for alvo, uri in ((str(tmp_path / "x.db"), False), (":memory:", False),
                      ("file:t14?mode=memory", True)):
        sqlite3.connect(alvo, uri=uri).close()


def test_perfil_do_app_fica_fora_do_data(hermetico):
    import web.app as webapp

    perfil = Path(webapp.PROFILE_PATH).resolve()
    assert not perfil.is_relative_to((RAIZ / "data").resolve())
    assert perfil.is_relative_to(Path(tempfile.gettempdir()).resolve())


def test_home_do_app_abre_com_o_golden():
    from starlette.testclient import TestClient
    import web.app as webapp

    resposta = TestClient(webapp.app).get("/")
    assert resposta.status_code == 200
    assert "TRACKER" in resposta.text
