#!/usr/bin/env python3
"""
Aviso de captura não carregada (card P1.4; ADR-0004, Q19=B).

A regra do card: sem a DLL no checkout, ou sem 'CS2 Tracker Events' no
`css_plugins list` E sem a linha de load no docker logs, sai um [AVISO] bem
visível no sink (TUI) e em logs/partidas/, e a partida SEGUE. Aborta só com
CS2_TRACKER_EXIGIR_CAPTURA=1.

O que este arquivo mais vigia é o falso positivo: com o plugin carregado, ou
quando o servidor não responde de forma legível (RCON vazio, docker logs
indisponível ou sem boot), não sai [AVISO] e o opt-in não aborta.

Tudo com fakes: ROOT em tmp_path, rcon_run e subprocess trocados por
monkeypatch. Nenhum docker, RCON, processo ou rede (tests/conftest.py, T1.4).
As respostas abaixo seguem o formato real do `css_plugins list` e do boot da
CounterStrikeSharp (cores ANSI incluídas), escritas à mão.
"""
import subprocess
import types
from pathlib import Path

import pytest

import start_match
from test_tui_integracao import (  # noqa: F401  (fixtures do G4, T1.5)
    NICK, EsperaIndevida, launch_vigiado, lancar_pela_tui, servidor,
)

OPT_IN = "CS2_TRACKER_EXIGIR_CAPTURA"
CONTAINER = "cs2-teste"

LISTA_COM = (
    "  List of all plugins currently loaded by CounterStrikeSharp: 3 plugins loaded.\n"
    '  [#1:LOADED]: "MatchZy" (0.8.15) by WD- (https://github.com/shobhit-pathak/)\n'
    "    A plugin for running and managing CS2 practice/pugs/scrims/matches!\n"
    '  [#2:LOADED]: "CS2 Tracker Events" (0.4.0) by cs2-tracker\n'
    '  [#3:LOADED]: "RoundDamageRecap" (1.2.0) by YuGeYu (modified by ed0ard)\n'
)
LISTA_SEM = (
    "  List of all plugins currently loaded by CounterStrikeSharp: 2 plugins loaded.\n"
    '  [#1:LOADED]: "MatchZy" (0.8.15) by WD- (https://github.com/shobhit-pathak/)\n'
    '  [#2:LOADED]: "RoundDamageRecap" (1.2.0) by YuGeYu (modified by ed0ard)\n'
)

E = "\x1b"


def _linha_cssharp(texto, plugin):
    """Uma linha do PluginContext como o docker logs entrega (com as cores)."""
    return (f"2026-10-02T03:17:32.489385960Z {E}[39;49m{E}[37m03:17:32{E}[39;49m{E}[39;49m"
            f"{E}[30m [{E}[39;49m{E}[39;49m{E}[37mINFO{E}[39;49m{E}[39;49m{E}[30m] (cssharp:"
            f"{E}[39;49m{E}[39;49m{E}[37mPluginContext{E}[39;49m{E}[39;49m{E}[30m) "
            f"{E}[39;49m{E}[39;49m{E}[37m{texto} {E}[39;49m{E}[39;49m{E}[36m{plugin}{E}[39;49m\n")


BOOT_COM = (_linha_cssharp("Finished loading plugin", "MatchZy")
            + _linha_cssharp("Loading plugin", "Cs2TrackerEvents")
            + _linha_cssharp("Finished loading plugin", "CS2 Tracker Events")
            + _linha_cssharp("Finished loading plugin", "RoundDamageRecap"))
BOOT_SEM = (_linha_cssharp("Finished loading plugin", "MatchZy")
            + _linha_cssharp("Finished loading plugin", "RoundDamageRecap"))
SO_PRONTO = ("2026-10-12T21:38:03.581242556Z [MatchZy 0.8.15 LOADED] MatchZy by WD-\n"
             "2026-10-12T21:38:03.777893184Z [Cs2TrackerEvents] Pronto — gravando em "
             "/home/steam/cs2-dedicated/game/csgo/events-live/current.jsonl\n")
SEM_BOOT = "2026-10-19T19:00:00.000000000Z Long frame: 20ms elapsed\n"


def _com_dll(raiz: Path):
    dll = raiz / "docker" / "plugins" / "Cs2TrackerEvents" / "Cs2TrackerEvents.dll"
    dll.parent.mkdir(parents=True, exist_ok=True)
    dll.write_bytes(b"dll de teste")


@pytest.fixture(autouse=True)
def _sem_opt_in(monkeypatch):
    monkeypatch.delenv(OPT_IN, raising=False)


# ------------------------------------------------------ leitura das respostas

@pytest.mark.parametrize("resposta, esperado", [
    (LISTA_COM, "carregada"),
    (LISTA_SEM, "ausente"),
    ("", "incerta"),
    (None, "incerta"),
    ("   \n", "incerta"),
    ("Unknown command 'css_plugins'!", "incerta"),
])
def test_plugins_list_so_diz_ausente_com_uma_lista_de_verdade(resposta, esperado):
    assert start_match.captura_no_plugins_list(resposta) == esperado


@pytest.mark.parametrize("texto, esperado", [
    (BOOT_COM, "carregada"),
    (SO_PRONTO, "carregada"),
    (BOOT_SEM, "ausente"),
    (SEM_BOOT, "incerta"),
    ("", "incerta"),
    (None, "incerta"),
])
def test_docker_logs_so_diz_ausente_com_o_boot_dos_plugins(texto, esperado):
    assert start_match.captura_no_docker_logs(texto) == esperado


def test_a_linha_de_load_com_cor_nao_vira_ausente():
    # Sem tirar o ANSI, o nome vem colado no código de cor e não casaria.
    assert "Finished loading plugin CS2 Tracker Events" not in BOOT_COM
    assert start_match.captura_no_docker_logs(BOOT_COM) == "carregada"


# ------------------------------------------------------------ docker logs

def _subprocess_falso(monkeypatch, run):
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=run, TimeoutExpired=subprocess.TimeoutExpired))


def test_docker_logs_do_boot_le_desde_o_started_at(monkeypatch):
    chamadas = []

    def run(argv, **kw):
        chamadas.append(argv)
        if argv[1] == "inspect":
            return subprocess.CompletedProcess(argv, 0, "2026-10-19T18:50:12.123456789Z\n", "")
        return subprocess.CompletedProcess(argv, 0, "linha do stdout\n", "linha do stderr\n")

    _subprocess_falso(monkeypatch, run)
    assert start_match.docker_logs_do_boot(CONTAINER) == "linha do stdout\nlinha do stderr\n"
    assert chamadas == [
        ["docker", "inspect", "-f", "{{.State.StartedAt}}", CONTAINER],
        ["docker", "logs", "--since", "2026-10-19T18:50:12.123456789Z", CONTAINER],
    ]


@pytest.mark.parametrize("falha", ["inspect_rc", "inspect_vazio", "logs_rc", "sem_docker", "timeout"])
def test_docker_logs_indisponivel_e_none(monkeypatch, falha):
    def run(argv, **kw):
        if falha == "sem_docker":
            raise FileNotFoundError("docker")
        if falha == "timeout":
            raise subprocess.TimeoutExpired(argv, 10)
        if argv[1] == "inspect":
            if falha == "inspect_rc":
                return subprocess.CompletedProcess(argv, 1, "", "No such object")
            if falha == "inspect_vazio":
                return subprocess.CompletedProcess(argv, 0, "\n", "")
            return subprocess.CompletedProcess(argv, 0, "2026-10-19T18:50:12Z\n", "")
        return subprocess.CompletedProcess(argv, 1, BOOT_SEM, "error from daemon")

    _subprocess_falso(monkeypatch, run)
    assert start_match.docker_logs_do_boot(CONTAINER) is None


# --------------------------------------------------------- regra do card

@pytest.fixture
def servidor_falso(tmp_path, monkeypatch):
    """ROOT em tmp_path (sem DLL até o teste pôr), RCON e docker logs falsos
    que só anotam o que foi pedido."""
    estado = types.SimpleNamespace(lista="", logs=None, rcon=[], docker=0)

    def rcon_run(host, port, password, command, timeout=5):
        estado.rcon.append(command)
        if isinstance(estado.lista, Exception):
            raise estado.lista
        return estado.lista

    def docker_logs_do_boot(container):
        assert container == CONTAINER
        estado.docker += 1
        return estado.logs

    monkeypatch.setattr(start_match, "ROOT", tmp_path)
    monkeypatch.setattr(start_match, "rcon_run", rcon_run)
    monkeypatch.setattr(start_match, "docker_logs_do_boot", docker_logs_do_boot)
    return estado


def _avisar(log):
    return start_match.avisar_captura(container_name=CONTAINER, rcon_host="127.0.0.1",
                                      rcon_port=27015, rcon_password="fake", log=log.append)


def _avisos(log):
    return [l for l in log if l.startswith("[AVISO]")]


def test_sem_dll_avisa_e_segue(servidor_falso):
    log = []
    assert _avisar(log) is False  # a partida segue
    assert "[AVISO] CAPTURA NÃO CARREGADA: docker/plugins/Cs2TrackerEvents/" \
           "Cs2TrackerEvents.dll não existe no checkout." in log
    assert "[AVISO] A partida SEGUE. Para abortar nesse caso: " \
           "CS2_TRACKER_EXIGIR_CAPTURA=1 no .env." in log
    assert _avisos(log) == log  # o bloco inteiro é [AVISO], com a barra antes e depois
    assert log[0] == log[-1] == "[AVISO] " + "!" * 62


def test_sem_dll_basta_mesmo_com_o_servidor_dizendo_carregado(servidor_falso):
    # "Sem DLL, ou ...": a DLL ausente no checkout avisa sozinha.
    servidor_falso.lista, servidor_falso.logs = LISTA_COM, BOOT_COM
    log = []
    _avisar(log)
    assert "[AVISO] CAPTURA NÃO CARREGADA: docker/plugins/Cs2TrackerEvents/" \
           "Cs2TrackerEvents.dll não existe no checkout." in log


def test_lista_sem_a_captura_e_boot_sem_a_linha_avisa(servidor_falso, tmp_path):
    _com_dll(tmp_path)
    servidor_falso.lista, servidor_falso.logs = LISTA_SEM, BOOT_SEM
    log = []
    assert _avisar(log) is False
    assert ("[AVISO] CAPTURA NÃO CARREGADA: 'CS2 Tracker Events' fora do css_plugins list "
            "e sem a linha de load no docker logs do boot.") in log
    assert servidor_falso.rcon == ["css_plugins list"]


@pytest.mark.parametrize("lista, logs, motivo", [
    # Plugin carregado de verdade: a lista basta, e nem lê o docker logs.
    (LISTA_COM, None, "[CAPTURA] Plugin de captura carregado ('CS2 Tracker Events' no css_plugins list)."),
    # O "E" do card: com a linha de load no boot, a lista sem o nome não avisa.
    (LISTA_SEM, BOOT_COM, "[CAPTURA] Plugin de captura carregado (linha de load no docker logs)."),
    ("", SO_PRONTO, "[CAPTURA] Plugin de captura carregado (linha de load no docker logs)."),
    # RCON vazio é "não sei", nunca "ausente" (o falso negativo do critério 3).
    ("", BOOT_SEM, "[CAPTURA] Não consegui confirmar o plugin de captura "
                   "(sem resposta legível de css_plugins list); sigo sem aviso."),
    ("", None, "[CAPTURA] Não consegui confirmar o plugin de captura "
               "(sem resposta legível de css_plugins list e docker logs); sigo sem aviso."),
    ("Unknown command 'css_plugins'!", BOOT_SEM,
     "[CAPTURA] Não consegui confirmar o plugin de captura "
     "(sem resposta legível de css_plugins list); sigo sem aviso."),
    (RuntimeError("RCON caiu"), BOOT_SEM,
     "[CAPTURA] Não consegui confirmar o plugin de captura "
     "(sem resposta legível de css_plugins list); sigo sem aviso."),
    # docker logs indisponível ou sem boot legível também é "não sei".
    (LISTA_SEM, None, "[CAPTURA] Não consegui confirmar o plugin de captura "
                      "(sem resposta legível de docker logs); sigo sem aviso."),
    (LISTA_SEM, SEM_BOOT, "[CAPTURA] Não consegui confirmar o plugin de captura "
                          "(sem resposta legível de docker logs); sigo sem aviso."),
])
def test_sem_falso_positivo(servidor_falso, tmp_path, monkeypatch, lista, logs, motivo):
    monkeypatch.setenv(OPT_IN, "1")  # nem com o opt-in: sem prova de ausência não aborta
    _com_dll(tmp_path)
    servidor_falso.lista, servidor_falso.logs = lista, logs
    log = []
    assert _avisar(log) is False
    assert log == [motivo]
    assert _avisos(log) == []
    if lista is LISTA_COM:
        assert servidor_falso.docker == 0


# ------------------------------------------------------------- o opt-in

@pytest.mark.parametrize("ambiente, no_env, esperado", [
    (None, None, False),
    ("1", None, True),
    (" 1 ", None, True),
    ("0", None, False),
    ("", None, False),
    ("true", None, False),
    (None, "1", True),
    (None, "0", False),
    ("0", "1", False),  # o ambiente vence o .env
])
def test_exigir_captura(tmp_path, ambiente, no_env, esperado):
    arquivo = tmp_path / ".env"
    if no_env is not None:
        arquivo.write_text(f"# comentário\n{OPT_IN}={no_env}\n", encoding="utf-8")
    environ = {} if ambiente is None else {OPT_IN: ambiente}
    assert start_match.exigir_captura(arquivo, environ=environ) is esperado


def test_com_opt_in_e_sem_captura_pede_para_abortar(servidor_falso, monkeypatch):
    monkeypatch.setenv(OPT_IN, "1")
    log = []
    assert _avisar(log) is True
    assert "[AVISO] CS2_TRACKER_EXIGIR_CAPTURA=1: a partida não começa sem a captura." in log
    assert not any("A partida SEGUE" in l for l in log)


def test_opt_in_pelo_env_do_root(servidor_falso, tmp_path):
    (tmp_path / ".env").write_text(f"{OPT_IN}=1\n", encoding="utf-8")
    assert _avisar([]) is True


# ------------------------------------------------- run_match com fakes

class Parar(Exception):
    """Interrompe o run_match logo depois do loadmatch."""


@pytest.fixture
def partida(tmp_path, monkeypatch, servidor_falso):
    """run_match até o loadmatch: o resto do caminho (compose, RCON, watcher)
    só anota a ordem."""
    estado = types.SimpleNamespace(logs=[], ordem=[], watcher_parado=False, srv=servidor_falso)
    rcon_captura = start_match.rcon_run

    def rcon_run(host, port, password, command, timeout=5):
        estado.ordem.append(command)
        if command.startswith("matchzy_loadmatch"):
            raise Parar
        return rcon_captura(host, port, password, command, timeout)

    def start_watcher(container, player, config, on_output=None, log=print):
        estado.ordem.append("watcher")

        def terminate():
            estado.watcher_parado = True

        return types.SimpleNamespace(terminate=terminate)

    monkeypatch.setattr(start_match, "EVENTS_LIVE_DIR", "./docker/events-live")
    monkeypatch.setattr(start_match, "read_max_players", lambda _: None)
    monkeypatch.setattr(start_match, "docker_fora_do_ar", lambda: None)
    monkeypatch.setattr(start_match, "container_running", lambda _: True)
    monkeypatch.setattr(start_match, "wait_for_rcon",
                        lambda *_a, **_k: estado.ordem.append("wait_for_rcon"))
    monkeypatch.setattr(start_match, "rcon_run", rcon_run)
    monkeypatch.setattr(start_match, "start_watcher", start_watcher)
    return estado


def _rodar(partida):
    start_match.run_match(
        container_name=CONTAINER, match_config="match_config.spike.json",
        compose_file="docker-compose.yml", rcon_host="127.0.0.1", rcon_port=27015,
        rcon_password="fake", team_size=5, boot_timeout=1, skip_up=False,
        player=NICK, log=partida.logs.append)


def _log_da_partida(tmp_path):
    arquivos = list((tmp_path / "logs" / "partidas").glob("partida_*.log"))
    assert len(arquivos) == 1, arquivos
    return [linha[9:] for linha in arquivos[0].read_text(encoding="utf-8").splitlines()]


def test_run_match_sem_dll_avisa_na_tela_e_no_log_e_carrega_a_partida(partida, tmp_path):
    with pytest.raises(Parar):  # chegou ao loadmatch: a partida seguiu
        _rodar(partida)
    aviso = ("[AVISO] CAPTURA NÃO CARREGADA: docker/plugins/Cs2TrackerEvents/"
             "Cs2TrackerEvents.dll não existe no checkout.")
    assert aviso in partida.logs
    assert aviso in _log_da_partida(tmp_path)
    assert partida.ordem == ["watcher", "wait_for_rcon", "matchzy_loadmatch match_config.spike.json"]
    assert partida.watcher_parado is False


def test_run_match_confere_a_captura_depois_do_rcon_e_antes_do_loadmatch(partida, tmp_path):
    _com_dll(tmp_path)
    partida.srv.lista = LISTA_COM
    with pytest.raises(Parar):
        _rodar(partida)
    assert partida.ordem == ["watcher", "wait_for_rcon", "css_plugins list",
                             "matchzy_loadmatch match_config.spike.json"]
    assert _avisos(partida.logs) == []
    assert "[CAPTURA] Plugin de captura carregado ('CS2 Tracker Events' no css_plugins list)." \
        in _log_da_partida(tmp_path)


def test_run_match_com_opt_in_e_sem_captura_aborta_antes_do_loadmatch(partida, tmp_path, monkeypatch):
    monkeypatch.setenv(OPT_IN, "1")
    with pytest.raises(SystemExit) as saida:
        _rodar(partida)
    assert str(saida.value) == ("Partida não iniciada: a captura não carregou "
                                "(CS2_TRACKER_EXIGIR_CAPTURA=1).")
    assert not any(c.startswith("matchzy_loadmatch") for c in partida.ordem)
    assert partida.watcher_parado is True
    assert "[AVISO] CS2_TRACKER_EXIGIR_CAPTURA=1: a partida não começa sem a captura." \
        in _log_da_partida(tmp_path)


def test_run_match_com_opt_in_e_rcon_vazio_nao_aborta(partida, tmp_path, monkeypatch):
    monkeypatch.setenv(OPT_IN, "1")
    _com_dll(tmp_path)
    partida.srv.lista, partida.srv.logs = "", None
    with pytest.raises(Parar):
        _rodar(partida)
    assert _avisos(partida.logs) == []
    assert partida.watcher_parado is False


# ------------------------------------- G4: TUI -> launch -> run_match

def _texto(tela):
    """O painel de log quebra linha longa na largura da tela (100 colunas),
    com o espaço no fim do pedaço: colados, os pedaços refazem cada linha."""
    return "".join(tela)


def _rcon_com_lista(monkeypatch, servidor, lista):
    base = servidor.cliente()

    class RconComLista(base):
        def run(self, comando):
            resposta = super().run(comando)
            return lista if comando == "css_plugins list" else resposta

    monkeypatch.setattr(start_match, "RconClient", RconComLista)


def test_tui_com_a_captura_carregada_nao_mostra_aviso(servidor, launch_vigiado, tmp_path, monkeypatch):
    _com_dll(tmp_path)
    _rcon_com_lista(monkeypatch, servidor, LISTA_COM)
    tela = _texto(lancar_pela_tui("bo1", ["de_nuke"], ["t"], launch_vigiado))

    assert "[AVISO]" not in tela and "CAPTURA NÃO CARREGADA" not in tela, tela
    assert "[CAPTURA] Plugin de captura carregado ('CS2 Tracker Events' no css_plugins list)." in tela
    i_lista = servidor.rcon.index("css_plugins list")
    assert servidor.rcon.index("echo start_match_ready") < i_lista \
        < servidor.rcon.index("matchzy_loadmatch match_config.spike.json")
    assert servidor.rcon.count("css_start") == 1


def test_tui_sem_dll_mostra_o_aviso_e_a_partida_segue(servidor, launch_vigiado, tmp_path):
    tela = _texto(lancar_pela_tui("bo1", ["de_nuke"], ["t"], launch_vigiado))

    aviso = ("[AVISO] CAPTURA NÃO CARREGADA: docker/plugins/Cs2TrackerEvents/"
             "Cs2TrackerEvents.dll não existe no checkout.")
    assert aviso in tela, tela
    assert aviso in _log_da_partida(tmp_path)
    assert [c for c in servidor.rcon if c.startswith("matchzy_loadmatch")] == \
        ["matchzy_loadmatch match_config.spike.json"]
    assert servidor.rcon.count("css_start") == 1


def test_tui_com_opt_in_e_sem_captura_para_com_a_mensagem(servidor, launch_vigiado, tmp_path,
                                                          monkeypatch):
    monkeypatch.setenv(OPT_IN, "1")
    base = servidor.cliente()

    class RconSemLoad(base):
        def run(self, comando):
            # Se o abort falhar, o loadmatch encerra o launch com erro em vez
            # de deixar o run_match esperando o "já conectei" para sempre.
            if comando.startswith("matchzy_loadmatch"):
                raise EsperaIndevida("loadmatch com o opt-in e sem captura")
            return super().run(comando)

    monkeypatch.setattr(start_match, "RconClient", RconSemLoad)
    tela = _texto(lancar_pela_tui("bo1", ["de_nuke"], ["t"], launch_vigiado, ate_o_ready=False))

    assert isinstance(launch_vigiado.erro, SystemExit)
    assert ("[ERRO] Partida não iniciada: a captura não carregou "
            "(CS2_TRACKER_EXIGIR_CAPTURA=1).") in tela, tela
    assert not any(c.startswith("matchzy_loadmatch") for c in servidor.rcon)
    assert len(servidor.popen) == 1  # o watcher subiu e o run_match o encerrou
