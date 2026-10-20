#!/usr/bin/env python3
"""
Lado por mapa numa série (card P1.6): o start_match lê o lado do time
humano em map_sides[i], o do mapa que está entrando, e não sempre no [0].

Antes do P1.6, numa MD3 com map_sides [team1_ct, team1_t, team1_ct], o mapa
2 era montado como se o humano fosse CT: 4 bots no CT e 5 no TR, mais o
humano no TR (4 x 6), e a reconciliação kickava pelo alvo errado.

Os gabaritos (contagem de bot_add_ct/bot_add_t por mapa, comandos de kick,
linhas de log) estão escritos à mão. Os fakes são os do
tests/test_tui_integracao.py: monkeypatch de start_match.subprocess,
start_match.RconClient e start_match.time, com o ROOT numa pasta
temporária. Nenhum processo, rede, Docker ou RCON de verdade; o
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
RCON_SENHA = "fake"
CONFIG = "match_config.spike.json"

# Resposta do `status` com 10 clientes (9 bots + você): o gate de
# wait_for_client_count do 5x5.
STATUS_10 = "---------players--------\n" + "".join(
    f"  {i} 00:01 0 0 active 0 'jogador{i}'\n" for i in range(10)) + "#end\n"


def _linha_time(nome, cid, time_):
    return f'"{nome}<{cid}><BOT><{time_}>" OnPreResetRound => CTMDBG\n'


class Servidor:
    """Docker e RCON falsos; guarda tudo o que sairia para o servidor."""

    def __init__(self, snapshot=""):
        self.rcon = []
        self.docker = []
        self.snapshot = snapshot  # saída do `docker logs --tail`

    def run(self, argv, **kwargs):
        self.docker.append(list(argv))
        assert argv[0] == "docker", argv
        if argv[1] == "inspect":
            return subprocess.CompletedProcess(argv, 0, "true\n", "")
        if argv[1:3] == ["logs", "--since"]:
            return subprocess.CompletedProcess(
                argv, 0, "[MatchZy] [ChangeMap]\n[MatchZy] [StartWarmup]\n", "")
        if argv[1:3] == ["logs", "--tail"]:
            return subprocess.CompletedProcess(argv, 0, self.snapshot, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def Popen(self, argv, **kwargs):
        return types.SimpleNamespace(stdout=io.StringIO(""), wait=lambda timeout=None: 0,
                                     poll=lambda: 0, terminate=lambda: None,
                                     kill=lambda: None)

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
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  cs2:\n    environment:\n      - CS2_MAXPLAYERS=11\n", encoding="utf-8")
    monkeypatch.setattr(start_match, "ROOT", tmp_path)
    monkeypatch.delenv(start_match.EXIGIR_CAPTURA, raising=False)
    srv = Servidor()
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=srv.run, Popen=srv.Popen, PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT,
        TimeoutExpired=subprocess.TimeoutExpired))
    monkeypatch.setattr(start_match, "RconClient", srv.cliente())
    monkeypatch.setattr(start_match, "time", types.SimpleNamespace(
        sleep=lambda s: None, time=time.time, strftime=time.strftime, gmtime=time.gmtime))
    return srv


def _escrever_config(tmp_path, **campos):
    dados = {"num_maps": 1, "maplist": ["de_mirage"], "clinch_series": True,
             "players_per_team": 5, "team1": {"name": NICK}, "team2": {"name": "Bots"}}
    dados.update(campos)
    caminho = tmp_path / "docker" / CONFIG
    caminho.parent.mkdir(exist_ok=True)
    caminho.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    return caminho


def _bots_por_mapa(rcon):
    """[(bot_add_ct, bot_add_t)] de cada montagem, na ordem: um item por
    css_start, contando os adds anônimos que vieram antes dele."""
    mapas, ct, t = [], 0, 0
    for comando in rcon:
        if comando == "bot_add_ct":
            ct += 1
        elif comando == "bot_add_t":
            t += 1
        elif comando == "css_start":
            mapas.append((ct, t))
            ct, t = 0, 0
    return mapas


def _rodar(**extra):
    logs = []
    kwargs = dict(
        container_name="cs2-spike", match_config=CONFIG, compose_file="docker-compose.yml",
        rcon_host="127.0.0.1", rcon_port=27015, rcon_password=RCON_SENHA, team_size=5,
        boot_timeout=5, skip_up=True, player=NICK, confirm_ready=lambda: None,
        log=logs.append,
    )
    kwargs.update(extra)
    start_match.run_match(**kwargs)
    return logs


# -- leitura do lado por índice de mapa ------------------------------------

@pytest.mark.parametrize("map_sides, indice, esperado", [
    (["team1_ct", "team1_t", "team1_ct"], 0, "ct"),
    (["team1_ct", "team1_t", "team1_ct"], 1, "t"),
    (["team1_ct", "team1_t", "team1_ct"], 2, "ct"),
    (["team1_t", "team1_ct", "team1_t"], 0, "t"),
    (["team1_t", "team1_ct", "team1_t"], 2, "t"),
    (["team1_t", "knife", "team1_t"], 1, "ct"),  # knife: não é TR declarado
])
def test_lado_lido_no_indice_do_mapa(tmp_path, map_sides, indice, esperado):
    caminho = _escrever_config(tmp_path, num_maps=3, map_sides=map_sides)
    logs = []
    assert start_match.human_side_from_config(caminho, map_index=indice,
                                              log=logs.append) == esperado
    assert logs == []


def test_sem_indice_le_o_primeiro_mapa(tmp_path):
    """O default (map_index=0) é o comportamento de sempre da MD1."""
    caminho = _escrever_config(tmp_path, map_sides=["team1_t"])
    assert start_match.human_side_from_config(caminho) == "t"


def test_map_sides_curto_assume_ct_e_avisa(tmp_path):
    caminho = _escrever_config(tmp_path, num_maps=3, map_sides=["team1_t"])
    logs = []
    assert start_match.human_side_from_config(caminho, map_index=2, log=logs.append) == "ct"
    assert logs == [f"[AVISO] map_sides de {CONFIG} não tem o mapa 3 (['team1_t']), "
                    "assumindo team1=CT."]


def test_sem_map_sides_assume_ct_calado(tmp_path):
    caminho = _escrever_config(tmp_path, num_maps=3)
    logs = []
    assert start_match.human_side_from_config(caminho, map_index=1, log=logs.append) == "ct"
    assert logs == []


def test_config_ilegivel_assume_ct(tmp_path):
    logs = []
    lado = start_match.human_side_from_config(tmp_path / "nao_existe.json", map_index=1,
                                              log=logs.append)
    assert lado == "ct"
    assert len(logs) == 1 and logs[0].startswith("[AVISO] não consegui ler ")


# -- set_side_in_config (--side do CLI) ------------------------------------

@pytest.mark.parametrize("num_maps, esperado", [
    (1, ["team1_t"]),
    (3, ["team1_t", "team1_t", "team1_t"]),
])
def test_set_side_grava_um_lado_por_mapa(tmp_path, num_maps, esperado):
    caminho = _escrever_config(tmp_path, num_maps=num_maps,
                               map_sides=["team1_ct"] * num_maps)
    logs = []
    start_match.set_side_in_config(caminho, "t", log=logs.append)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados["map_sides"] == esperado
    assert dados["num_maps"] == num_maps
    assert logs == [f"[CONFIG] {CONFIG}: map_sides -> {esperado}"]


# -- reconciliação dos times esperada por mapa -----------------------------

def test_reconciliacao_usa_o_lado_do_mapa(servidor, tmp_path):
    """Mapa 2 de uma MD3 com o humano no TR, e a engine com um bot a mais no
    CT (6 CT + 4 TR + você, o caso visto ao vivo em 19/09). O alvo certo é
    5 bots CT e 4 TR: kicka só um CT. Com o lado do mapa 1 (CT) o alvo seria
    4 CT e 5 TR, e o kick levaria dois."""
    caminho = _escrever_config(tmp_path, num_maps=3,
                               map_sides=["team1_ct", "team1_t", "team1_ct"])
    servidor.snapshot = (
        "".join(_linha_time(f"Ct{i}", i, "CT") for i in range(1, 7))
        + "".join(_linha_time(f"Tr{i}", 10 + i, "TERRORIST") for i in range(1, 5))
        + _linha_time(NICK, 0, "TERRORIST"))
    logs = []
    start_match.force_start_and_balance_bots(
        rcon_host="127.0.0.1", rcon_port=27015, rcon_password=RCON_SENHA,
        container_name="cs2-spike", team_size=5, player=NICK,
        local_match_config=caminho, log=logs.append, map_index=1)

    assert logs[0] == ("[MATCHZY] Time humano no lado T (mapa 2, map_sides[1]). "
                       "Balanceando pra 5x5 (5 bot(s) CT + 4 bot(s) TR) ainda no warmup...")
    assert _bots_por_mapa(servidor.rcon) == [(5, 4)]
    # O snapshot falso não muda: _balance_bots e a reconciliação leem o
    # mesmo 6 x 4 e kickam o mesmo excedente, um CT por vez.
    assert [c for c in servidor.rcon if c.startswith('bot_kick "')] == \
        ['bot_kick "Ct1"', 'bot_kick "Ct1"']
    assert "[MATCHZY] CT com 6 bot(s), esperado 5 — kickando excedente(s): ['Ct1']" in logs
    assert not any(linha.startswith("[MATCHZY] TR com") for linha in logs)
    assert "[MATCHZY] Times após reconciliação: CT 6 : TR 5 (esperado 5 : 5)." in logs


# -- série inteira pelo run_match ------------------------------------------

def test_md3_monta_cada_mapa_com_o_lado_dele(servidor, tmp_path):
    """O caminho do wizard: o launch grava o map_sides da série e chama o
    run_match sem map_name nem side."""
    _escrever_config(tmp_path, num_maps=3,
                     maplist=["de_inferno", "de_ancient", "de_dust2"],
                     map_sides=["team1_ct", "team1_t", "team1_ct"])
    logs = _rodar()

    # (bot_add_ct, bot_add_t) por mapa: o humano ocupa a quinta vaga do lado dele.
    assert _bots_por_mapa(servidor.rcon) == [(4, 5), (5, 4), (4, 5)]
    lados = [linha for linha in logs if linha.startswith("[MATCHZY] Time humano no lado")]
    assert [linha.split(". Balanceando")[0] for linha in lados] == [
        "[MATCHZY] Time humano no lado CT (mapa 1, map_sides[0])",
        "[MATCHZY] Time humano no lado T (mapa 2, map_sides[1])",
        "[MATCHZY] Time humano no lado CT (mapa 3, map_sides[2])",
    ]


def test_md3_toda_de_tr(servidor, tmp_path):
    _escrever_config(tmp_path, num_maps=3,
                     maplist=["de_inferno", "de_ancient", "de_dust2"],
                     map_sides=["team1_t", "team1_t", "team1_t"])
    _rodar()
    assert _bots_por_mapa(servidor.rcon) == [(5, 4), (5, 4), (5, 4)]


def test_md1_pelo_cli_com_map_e_side_nao_regride(servidor, tmp_path):
    """--map e --side do CLI (e o run_match(side=...)): a série do arquivo
    vira MD1 e o único mapa é montado com o humano no TR."""
    caminho = _escrever_config(tmp_path, num_maps=3,
                               maplist=["de_inferno", "de_ancient", "de_dust2"],
                               map_sides=["team1_ct", "team1_ct", "team1_ct"])
    _rodar(map_name="de_nuke", side="t")

    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados["maplist"] == ["de_nuke"]
    assert dados["num_maps"] == 1
    assert dados["map_sides"] == ["team1_t"]
    assert _bots_por_mapa(servidor.rcon) == [(5, 4)]
    assert servidor.rcon.count("matchzy_loadmatch match_config.spike.json") == 1


def test_side_sem_map_numa_serie_vale_para_todos_os_mapas(servidor, tmp_path):
    caminho = _escrever_config(tmp_path, num_maps=3,
                               maplist=["de_inferno", "de_ancient", "de_dust2"],
                               map_sides=["team1_ct", "team1_t", "team1_ct"])
    _rodar(side="t")

    assert json.loads(caminho.read_text(encoding="utf-8"))["map_sides"] == \
        ["team1_t", "team1_t", "team1_t"]
    assert _bots_por_mapa(servidor.rcon) == [(5, 4), (5, 4), (5, 4)]
