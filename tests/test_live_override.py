#!/usr/bin/env python3
"""
live_override.cfg neutro antes do matchzy_loadmatch (card P1.8).

Se o processo do start_match morre entre o css_start e o finally de
_force_start_and_balance_bots, o live_override.cfg fica no volume com
`mp_ignore_round_win_conditions 1` e a quota daquela partida
(docs/armadilhas/matchzy.md, item 16). O run_match agora regrava o arquivo
neutro (só comentário) antes do loadmatch, e a falha disso não derruba a
partida.

Os gabaritos (conteúdo do arquivo, ordem das gravações e do RCON) estão
escritos à mão. Os fakes seguem os do tests/test_serie_md3.py: monkeypatch
de start_match.subprocess, start_match.RconClient e start_match.time, com o
ROOT numa pasta temporária. Nenhum processo, Docker ou RCON de verdade; o
docker/match_config.spike.json do repo nunca é lido nem escrito.
"""
import io
import json
import subprocess
import time
import types

import pytest

import start_match

NICK = "cobaia"
CONFIG = "match_config.spike.json"
CONTAINER = "cs2-spike"
CAMINHO = "/home/steam/cs2-dedicated/game/csgo/cfg/MatchZy/live_override.cfg"
ARGV_GRAVAR = ["docker", "exec", "-i", CONTAINER, "sh", "-c", f"cat > {CAMINHO}"]

NEUTRO = (
    "// Gerado pelo cs2-tracker antes do matchzy_loadmatch: override neutro.\n"
    "// O css_start de cada mapa reescreve este arquivo com a quota da partida.\n"
    "// Ver start_match.neutralizar_live_override (card P1.8).\n"
)

# O que o css_start de um 5x5 com você dentro grava (9 bots), com e sem a rede.
COM_BLOQUEIO = ("// Gerado pelo cs2-tracker a cada css_start.\n"
                "// Ver start_match.write_live_override e docs/features/M0.5-placar.md\n"
                "bot_quota_mode normal\nmp_autoteambalance 0\nmp_limitteams 0\n"
                "bot_quota 9\nmp_ignore_round_win_conditions 1\n")
SEM_BLOQUEIO = ("// Gerado pelo cs2-tracker a cada css_start.\n"
                "// Ver start_match.write_live_override e docs/features/M0.5-placar.md\n"
                "bot_quota_mode normal\nmp_autoteambalance 0\nmp_limitteams 0\n"
                "bot_quota 9\n")

STATUS_10 = "---------players--------\n" + "".join(
    f"  {i} 00:01 0 0 active 0 'jogador{i}'\n" for i in range(10)) + "#end\n"


class Servidor:
    """Docker e RCON falsos. `ordem` intercala, na ordem em que saíram, os
    comandos de RCON e as gravações do live_override.cfg (o conteúdo)."""

    def __init__(self):
        self.ordem = []
        self.falhar_neutro = False
        self._ns = int((time.time() + 3600) * 10**9)

    def _mapa_novo(self, argv):
        linhas = []
        for texto in ("[MatchZy] [ChangeMap] Changing map to de_ancient with delay 3",
                      f"[MatchZy] [FULL CONNECT] Player ID: 0, Name: {NICK} has connected!",
                      "[MatchZy] [StartWarmup] Starting warmup!"):
            self._ns += 10**9
            carimbo = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self._ns // 10**9))
            linhas.append(f"{carimbo}.{self._ns % 10**9:09d}Z {texto}\n")
        return subprocess.CompletedProcess(argv, 0, "".join(linhas), "")

    def run(self, argv, **kwargs):
        assert argv[0] == "docker", argv
        if argv[1] == "exec" and argv[-1].startswith("cat > "):
            assert list(argv) == ARGV_GRAVAR
            if self.falhar_neutro and kwargs["input"] == NEUTRO:
                raise subprocess.CalledProcessError(1, argv, "", "Error: No such container")
            self.ordem.append(("override", kwargs["input"]))
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[1] == "inspect":
            return subprocess.CompletedProcess(argv, 0, "true\n", "")
        if argv[1:3] == ["logs", "-t"]:
            return self._mapa_novo(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    def Popen(self, argv, **kwargs):
        return types.SimpleNamespace(
            stdout=io.StringIO(""), wait=lambda timeout=None: 0, poll=lambda: None,
            terminate=lambda: None, kill=lambda: None)

    def cliente(self):
        servidor = self

        class RconFalso:
            def __init__(self, host, port, passwd=None, timeout=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def run(self, comando):
                servidor.ordem.append(("rcon", comando))
                if comando == "echo start_match_ready":
                    return "start_match_ready"
                if comando.startswith("matchzy_loadmatch"):
                    return "Match config loaded"
                if comando == "status":
                    return STATUS_10
                return ""

        return RconFalso

    def gravacoes(self):
        return [conteudo for tipo, conteudo in self.ordem if tipo == "override"]

    def indice(self, item):
        return self.ordem.index(item)


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  cs2:\n    environment:\n      - CS2_MAXPLAYERS=11\n", encoding="utf-8")
    monkeypatch.setattr(start_match, "ROOT", tmp_path)
    monkeypatch.delenv(start_match.EXIGIR_CAPTURA, raising=False)
    srv = Servidor()
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=srv.run, Popen=srv.Popen, PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT,
        TimeoutExpired=subprocess.TimeoutExpired, CalledProcessError=subprocess.CalledProcessError))
    monkeypatch.setattr(start_match, "RconClient", srv.cliente())
    monkeypatch.setattr(start_match, "time", types.SimpleNamespace(
        sleep=lambda s: None, time=time.time, strftime=time.strftime, gmtime=time.gmtime))
    return srv


def _escrever_config(tmp_path, num_maps):
    dados = {"num_maps": num_maps, "maplist": ["de_inferno", "de_ancient", "de_dust2"][:num_maps],
             "map_sides": ["team1_ct"] * num_maps, "clinch_series": True,
             "players_per_team": 5, "team1": {"name": NICK}, "team2": {"name": "Bots"}}
    (tmp_path / "docker" / CONFIG).write_text(json.dumps(dados, indent=2), encoding="utf-8")


def _rodar():
    logs = []
    start_match.run_match(
        container_name=CONTAINER, match_config=CONFIG, compose_file="docker-compose.yml",
        rcon_host="127.0.0.1", rcon_port=27015, rcon_password="fake", team_size=5,
        boot_timeout=5, skip_up=True, player=NICK, confirm_ready=lambda: None,
        log=logs.append)
    return logs


# -- o arquivo neutro ------------------------------------------------------

def test_neutro_so_tem_comentario(servidor):
    logs = []
    assert start_match.neutralizar_live_override(CONTAINER, log=logs.append) is True
    assert servidor.gravacoes() == [NEUTRO]
    # Nenhuma linha é comando: sem bot_quota, sem mp_ignore_round_win_conditions.
    assert all(linha.startswith("//") for linha in NEUTRO.splitlines())
    assert NEUTRO.isascii()  # atravessa um pipe do Windows (cp1252) até o Linux
    assert logs == ["[MATCHZY] live_override.cfg neutro "
                    "(sem quota e sem bloqueio de fim de round)."]


def test_neutro_que_falha_avisa_e_nao_levanta(servidor):
    servidor.falhar_neutro = True
    logs = []
    assert start_match.neutralizar_live_override(CONTAINER, log=logs.append) is False
    assert servidor.gravacoes() == []
    assert logs[0].startswith("  [AVISO] Não consegui neutralizar o live_override.cfg (")
    assert logs[-1] == "    mp_ignore_round_win_conditions 0"


# -- run_match: neutro antes do loadmatch ----------------------------------

def test_md1_neutro_antes_do_loadmatch(servidor, tmp_path):
    _escrever_config(tmp_path, num_maps=1)
    logs = _rodar()

    # Neutro, depois a rede do css_start e a limpeza do finally.
    assert servidor.gravacoes() == [NEUTRO, COM_BLOQUEIO, SEM_BLOQUEIO]
    i_neutro = servidor.indice(("override", NEUTRO))
    i_load = servidor.indice(("rcon", f"matchzy_loadmatch {CONFIG}"))
    assert servidor.indice(("rcon", "echo start_match_ready")) < i_neutro < i_load
    # Entre o neutro e o loadmatch não sai nada para o servidor.
    assert i_load == i_neutro + 1
    assert i_load < servidor.indice(("override", COM_BLOQUEIO)) \
        < servidor.indice(("rcon", "css_start")) < servidor.indice(("override", SEM_BLOQUEIO))
    assert "[MATCHZY] live_override.cfg neutro (sem quota e sem bloqueio de fim de round)." in logs


def test_md3_neutro_so_uma_vez_e_cada_mapa_segue_igual(servidor, tmp_path):
    """Mapas 2..N (P1.5) não passam pelo loadmatch: o neutro sai uma vez só, e
    cada mapa continua com a rede ligada antes do css_start e limpa depois."""
    _escrever_config(tmp_path, num_maps=3)
    _rodar()

    assert servidor.gravacoes() == [NEUTRO] + [COM_BLOQUEIO, SEM_BLOQUEIO] * 3
    assert [c for t, c in servidor.ordem if t == "rcon"].count(f"matchzy_loadmatch {CONFIG}") == 1
    assert [c for t, c in servidor.ordem if t == "rcon"].count("css_start") == 3


def test_falha_do_neutro_nao_aborta_a_partida(servidor, tmp_path):
    servidor.falhar_neutro = True
    _escrever_config(tmp_path, num_maps=1)
    logs = _rodar()

    assert servidor.gravacoes() == [COM_BLOQUEIO, SEM_BLOQUEIO]
    rcon = [c for t, c in servidor.ordem if t == "rcon"]
    assert rcon.count(f"matchzy_loadmatch {CONFIG}") == 1
    assert rcon.count("css_start") == 1
    aviso = [linha for linha in logs if "neutralizar o live_override.cfg" in linha]
    assert len(aviso) == 1 and aviso[0].startswith("  [AVISO] ")
    assert logs.index(aviso[0]) < logs.index(f"[MATCHZY] Carregando {CONFIG}...")
