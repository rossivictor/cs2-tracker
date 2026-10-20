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
import threading
import time
import types
from datetime import datetime, timezone
from pathlib import Path

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


def _carimbo(ns):
    """O carimbo do `docker logs -t` (RFC3339 com 9 casas) de um instante em ns."""
    base = datetime.fromtimestamp(ns // 10**9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{ns % 10**9:09d}Z"


def _ns(carimbo):
    """Gabarito: '2026-09-19T18:00:30Z' (fração opcional) em ns, sem o start_match."""
    base, _, fracao = carimbo.rstrip("Z").partition(".")
    segundos = int(datetime.fromisoformat(base).replace(tzinfo=timezone.utc).timestamp())
    return segundos * 10**9 + int(fracao.ljust(9, "0"))


class Servidor:
    """Docker e RCON falsos; guarda tudo o que sairia para o servidor."""

    def __init__(self, snapshot=""):
        self.rcon = []
        self.docker = []
        self.snapshot = snapshot  # saída do `docker logs --tail` sem -t (os times)
        self.logs_t = self._mapa_novo  # o `docker logs -t` da espera do mapa seguinte
        self.relogio = None
        self.css_start = []  # instante (no relógio falso) de cada css_start
        self.watcher_vivo = True
        self._ns = int((time.time() + 3600) * 10**9)

    def _mapa_novo(self, argv):
        """Cada leitura já traz o mapa seguinte pronto: troca, você entra, warmup."""
        linhas = []
        for texto in ("[MatchZy] [ChangeMap] Changing map to de_ancient with delay 3",
                      f"[MatchZy] [FULL CONNECT] Player ID: 0, Name: {NICK} has connected!",
                      "[MatchZy] [StartWarmup] Starting warmup!"):
            self._ns += 10**9
            linhas.append(f"{_carimbo(self._ns)} {texto}\n")
        return subprocess.CompletedProcess(argv, 0, "".join(linhas), "")

    def run(self, argv, **kwargs):
        self.docker.append(list(argv))
        assert argv[0] == "docker", argv
        if argv[1] == "inspect":
            return subprocess.CompletedProcess(argv, 0, "true\n", "")
        if argv[1:3] == ["logs", "-t"]:
            return self.logs_t(argv)
        if argv[1:3] == ["logs", "--tail"]:
            return subprocess.CompletedProcess(argv, 0, self.snapshot, "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def Popen(self, argv, **kwargs):
        return types.SimpleNamespace(
            stdout=io.StringIO(""), wait=lambda timeout=None: 0,
            poll=lambda: None if self.watcher_vivo else 0,
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
                servidor.rcon.append(comando)
                if comando == "css_start":
                    servidor.css_start.append(servidor.relogio.t if servidor.relogio else None)
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


# -- P1.5: mapas 2..N sozinhos ---------------------------------------------

SERIE_BO3 = Path(__file__).resolve().parent / "fixtures" / "captura" / "serie_bo3.log"
CONTAINER = "cs2-spike"


class Relogio:
    """time.time/time.sleep falsos: dormir só anda o relógio."""

    def __init__(self, carimbo):
        self.t = _ns(carimbo) / 10**9

    def time(self):
        return self.t

    def sleep(self, segundos):
        self.t += segundos


class LogDoContainer:
    """O `docker logs -t` do container no instante do relógio falso. Com
    since_quebrado, o --since sai vazio com código 0, como no json-file
    corrompido do cs2-spike (desde 18/10); o --tail segue lendo pelo fim."""

    def __init__(self, linhas, relogio, since_quebrado=False):
        self.linhas = [(_ns(linha.split(" ", 1)[0]), linha) for linha in linhas]
        self.relogio = relogio
        self.since_quebrado = since_quebrado
        self.args = []        # o que veio entre `logs -t` e o container
        self.devolvidas = []  # linhas devolvidas em cada chamada

    def __call__(self, argv, **kwargs):
        assert argv[:3] == ["docker", "logs", "-t"] and argv[-1] == CONTAINER, argv
        agora = round(self.relogio.t * 10**9)
        visiveis = [(ns, linha) for ns, linha in self.linhas if ns <= agora]
        if argv[3] == "--since":
            segundos, fracao = argv[4].split(".")
            desde = int(segundos) * 10**9 + int(fracao)
            saida = [] if self.since_quebrado else [l for ns, l in visiveis if ns >= desde]
        else:
            assert argv[3] == "--tail", argv
            saida = [l for _, l in visiveis[-int(argv[4]):]]
        self.args.append(argv[3:5])
        self.devolvidas.append(len(saida))
        return subprocess.CompletedProcess(argv, 0, "".join(l + "\n" for l in saida), "")


@pytest.fixture
def log_falso(monkeypatch):
    def montar(linhas, inicio, since_quebrado=False):
        relogio = Relogio(inicio)
        log = LogDoContainer(linhas, relogio, since_quebrado)
        monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(run=log))
        monkeypatch.setattr(start_match, "time", types.SimpleNamespace(
            sleep=relogio.sleep, time=relogio.time))
        return log, relogio
    return montar


ABCD = ["2026-10-20T12:00:10.000000000Z linha A", "2026-10-20T12:00:11.000000000Z linha B",
        "2026-10-20T12:00:11.000000000Z linha C", "2026-10-20T12:00:12.000000000Z linha D"]
E05, E11 = "1792497605.000000000", "1792497611.000000000"  # 20/10 12:00:05 e 12:00:11 UTC


def _ler(cursor, relogio, carimbo):
    relogio.t = _ns(carimbo) / 10**9
    novas = cursor.novas()
    for ns, _ in novas:
        cursor.avancar(ns)
    return [linha.split(" ", 1)[1] for _, linha in novas]


def test_since_em_epoch_avanca_ate_a_ultima_linha_lida(log_falso):
    log, relogio = log_falso(ABCD, "2026-10-20T12:00:05Z")
    cursor = start_match.CursorDockerLogs(CONTAINER, _ns("2026-10-20T12:00:05Z"))
    assert _ler(cursor, relogio, "2026-10-20T12:00:11.5Z") == ["linha A", "linha B", "linha C"]
    assert _ler(cursor, relogio, "2026-10-20T12:00:11.8Z") == []
    assert _ler(cursor, relogio, "2026-10-20T12:00:12.5Z") == ["linha D"]
    # O --since é inclusivo: relê só o B e o C, do carimbo do cursor, e os pula.
    assert log.args == [["--since", E05], ["--since", E11], ["--since", E11]]
    assert log.devolvidas == [3, 2, 3]
    assert (cursor.chamadas, cursor.linhas_lidas) == (3, 8)


def test_json_file_corrompido_le_pelo_fim(log_falso):
    log, relogio = log_falso(ABCD, "2026-10-20T12:00:05Z", since_quebrado=True)
    avisos = []
    cursor = start_match.CursorDockerLogs(CONTAINER, _ns("2026-10-20T12:00:05Z"), avisos.append)
    assert _ler(cursor, relogio, "2026-10-20T12:00:11.5Z") == ["linha A", "linha B", "linha C"]
    assert _ler(cursor, relogio, "2026-10-20T12:00:12.5Z") == ["linha D"]
    assert _ler(cursor, relogio, "2026-10-20T12:00:13Z") == []
    # Um --since vazio, e dali em diante só o fim, N linhas por chamada.
    assert log.args == [["--since", E05], ["--tail", "200"], ["--tail", "200"], ["--tail", "200"]]
    assert len(avisos) == 1 and avisos[0].startswith("[AVISO] docker logs --since voltou sem")


@pytest.mark.parametrize("novas, tails, aviso", [
    (450, ["200", "400", "800"], False),
    (5200, ["200", "400", "800", "1600", "3200", "5000"], True),
])
def test_pelo_fim_dobra_o_tail_so_ate_achar_linha_velha(log_falso, novas, tails, aviso):
    linhas = ["2026-10-20T12:00:59.000000000Z velha"] + [
        f"2026-10-20T12:01:00.{i:09d}Z linha {i}" for i in range(novas)]
    log, relogio = log_falso(linhas, "2026-10-20T12:01:30Z", since_quebrado=True)
    avisos = []
    cursor = start_match.CursorDockerLogs(CONTAINER, _ns("2026-10-20T12:00:59.5Z"), avisos.append)
    cursor.pelo_fim = True
    lidas = _ler(cursor, relogio, "2026-10-20T12:01:30Z")
    assert [a[1] for a in log.args] == tails
    assert max(log.devolvidas) <= 5000
    if aviso:  # mais linhas novas que o teto: entrega as 5000 mais novas e avisa
        assert lidas[0] == "linha 200" and lidas[-1] == "linha 5199"
        assert avisos == ["[AVISO] Mais de 5000 linhas novas no docker logs entre duas "
                          "leituras: pode ter ficado linha sem ler."]
    else:
        assert lidas == [f"linha {i}" for i in range(450)]


def test_teto_de_3h_e_nao_240s(log_falso):
    """Nenhum mapa novo: a espera dura 3 h no relógio falso (2161 leituras,
    de 5 em 5 s), e não os 240 s de antes."""
    log, relogio = log_falso([], "2026-10-20T12:00:00Z")
    logs = []
    assert start_match.wait_for_next_map_warmup(CONTAINER, log=logs.append) is False
    assert relogio.t - _ns("2026-10-20T12:00:00Z") / 10**9 == 3 * 3600
    assert len(log.args) == 2 * 2161  # --since vazio + conferência pelo fim, em cada
    assert logs == ["[AVISO] Teto de 3 h esperando o próximo mapa "
                    "(ChangeMap -> FULL CONNECT -> StartWarmup)."]


@pytest.mark.parametrize("linha, decide_cedo, esperado", [
    ("MATCH ENDED, remainingMaps: 1, NumMaps: 3, Team1SeriesScore: 2, Team2SeriesScore: 0",
     True, "[MATCHZY] A série terminou; não há próximo mapa."),
    ("MATCH ENDED, remainingMaps: 1, NumMaps: 3, Team1SeriesScore: 2, Team2SeriesScore: 0",
     False, "[AVISO] Teto de 0.5 h esperando o próximo mapa "
            "(ChangeMap -> FULL CONNECT -> StartWarmup)."),
    ("MATCH ENDED, remainingMaps: 0, NumMaps: 3, Team1SeriesScore: 1, Team2SeriesScore: 2",
     False, "[MATCHZY] A série terminou; não há próximo mapa."),
])
def test_serie_decidida_para_a_espera(log_falso, linha, decide_cedo, esperado):
    log_falso([f"2026-10-20T12:00:10.000000000Z [MatchZy] [HandleMatchEnd] {linha}"],
              "2026-10-20T12:00:00Z")
    logs = []
    assert start_match.wait_for_next_map_warmup(
        CONTAINER, log=logs.append, timeout_s=1800, decide_cedo=decide_cedo) is False
    assert logs[-1] == esperado


def _serie_da_fixture(servidor, tmp_path, monkeypatch, since_quebrado):
    relogio = Relogio("2026-09-19T17:34:15Z")  # você conectado no mapa 1 (17:34:10)
    linhas = SERIE_BO3.read_text(encoding="utf-8").splitlines()
    log = LogDoContainer(linhas, relogio, since_quebrado)
    servidor.logs_t, servidor.relogio = log, relogio
    monkeypatch.setattr(start_match, "time", types.SimpleNamespace(
        sleep=relogio.sleep, time=relogio.time))
    _escrever_config(tmp_path, num_maps=3, maplist=["de_nuke", "de_dust2", "de_ancient"],
                     map_sides=["team1_ct", "team1_t", "team1_ct"])
    return log, _rodar()


@pytest.mark.parametrize("since_quebrado", [False, True])
def test_md3_da_fixture_mapas_2_e_3_sem_botao(servidor, tmp_path, monkeypatch, since_quebrado):
    """serie_bo3.log (série 45, 19/09) com o relógio falso: os mapas 2 e 3
    começam sozinhos depois que você entra no mapa novo (FULL CONNECT às
    18:00:30 e 18:36:06), e não no ChangeMap de 18:00:17, que sai com o
    mapa velho ainda no ar."""
    log, logs = _serie_da_fixture(servidor, tmp_path, monkeypatch, since_quebrado)

    assert _bots_por_mapa(servidor.rcon) == [(4, 5), (5, 4), (4, 5)]  # P1.6 segue valendo
    _, mapa2, mapa3 = servidor.css_start
    assert _ns("2026-09-19T18:00:30Z") <= mapa2 * 10**9 <= _ns("2026-09-19T18:00:40Z")
    assert _ns("2026-09-19T18:36:06Z") <= mapa3 * 10**9 <= _ns("2026-09-19T18:36:16Z")
    assert not any("Falha ao forçar" in l or "Não detectei" in l for l in logs)
    assert json.loads((tmp_path / "docker" / CONFIG).read_text(encoding="utf-8"))["num_maps"] == 3

    # Limites: 17:34:15 -> 18:36:16 são 3721 s, uma leitura a cada 5 s.
    assert len(log.args) <= 3721 // 5 + 10
    if since_quebrado:  # nunca mais que as 200 linhas do fim por chamada
        assert max(log.devolvidas) <= 200
        assert sum(1 for l in logs if "voltou sem as linhas novas" in l) == 1
    else:  # 779 linhas na janela, as conferências pelo fim antes de o --since
        # provar que lê, e o grupo de mesmo carimbo do cursor (até 14 na fixture)
        assert sum(log.devolvidas) <= 779 + 3 * 200 + 14 * len(log.args)
        # O --tail 1 do cursor (17:34:20.8, depois dos 5.8 s de montagem) e uma
        # conferência em 20.8, 25.8 e 30.8: a primeira linha nova é a de 17:34:32.
        assert [a for a in log.args if a[0] == "--tail"] == [["--tail", "1"]] + [["--tail", "200"]] * 3


@pytest.mark.parametrize("como, motivo", [
    ("watcher", "o watcher encerrou (TUI fechada ou Ctrl+C)"),
    ("evento", "cancelado por quem iniciou a partida"),
])
def test_espera_cancelavel(servidor, tmp_path, como, motivo):
    _escrever_config(tmp_path, num_maps=3, maplist=["de_inferno", "de_ancient", "de_dust2"],
                     map_sides=["team1_ct", "team1_t", "team1_ct"])
    cancelar = threading.Event()
    if como == "watcher":
        servidor.watcher_vivo = False
    else:
        cancelar.set()
    logs = _rodar(cancelar=cancelar)
    assert servidor.rcon.count("css_start") == 1
    assert f"[MATCHZY] Parei de esperar o próximo mapa: {motivo}." in logs
