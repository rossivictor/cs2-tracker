#!/usr/bin/env python3
"""
Testes de tools/evidencia_partida.py (card H1.1).

Gabarito escrito à mão. As fixtures reais vêm das cópias só leitura do backup
de 26/09, anonimizadas (SteamID64 abaixo da base, [U:1:0], "Jogador"):

  - serie45_2026-09-19_live_watch.txt: recorte da timeline do live_watch da
    série 45 (três mapas; o map1 se perdeu e o map2 ficou com demo_path do
    map1);
  - eventos/: cabeça e cauda de events_45_map0/map2 e events_50_map0, os
    rounds 1 e 3 e o round_stats do 15 do events_60_map0, e a cauda real do
    current.jsonl de 26/09;
  - banco_recorte.sql: as linhas 13, 14 e 24 da tabela matches.

O docker_logs_partida60_sintetico.txt é montado à mão com as formas de linha
citadas em docs/ (runbooks e handoff), porque o backup não guarda docker logs
de 26/09. Os demais cenários (crash, overflow, colisão) são linhas escritas
no próprio teste. Nada de Docker, rede ou banco real. Os logs são .txt porque
o gitignore global desta máquina ignora *.log.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "tools" / "hooks"))

import evidencia_partida as ep  # noqa: E402
import pii  # noqa: E402

FIX = RAIZ / "tests" / "fixtures" / "logs"
SERIE45 = FIX / "serie45_2026-09-19_live_watch.txt"
PARTIDA60 = FIX / "docker_logs_partida60_sintetico.txt"
EVENTOS = FIX / "eventos"
SHA_A = "a" * 64
SHA_B = "b" * 64


# ------------------------------------------------------------ apoio

@pytest.fixture
def banco(tmp_path):
    """Banco de fixture montado do recorte SQL, fora de qualquer checkout."""
    caminho = tmp_path / "banco" / "copia.sqlite"
    caminho.parent.mkdir()
    conn = sqlite3.connect(caminho)
    conn.executescript((FIX / "banco_recorte.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    return caminho


def _inserir(banco, demo_name, mapa, placar, lados, played_at="2026-09-27T20:00:00"):
    conn = sqlite3.connect(banco)
    conn.execute(
        "INSERT INTO matches (demo_name, map, played_at, score_mine, score_theirs, score_ct,"
        " score_t, demo_path, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'events')",
        (demo_name, mapa, played_at, placar[0], placar[1], lados[0], lados[1],
         f"docker\\events-live\\{demo_name}.jsonl"))
    conn.commit()
    conn.close()


def _arquivo(tmp_path, nome, linhas):
    caminho = tmp_path / nome
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def _pasta_eventos(tmp_path, arquivos):
    """{nome: [dict]} -> pasta com os JSONL."""
    pasta = tmp_path / "eventos"
    pasta.mkdir(exist_ok=True)
    for nome, eventos in arquivos.items():
        (pasta / nome).write_text("".join(json.dumps(e) + "\n" for e in eventos),
                                  encoding="utf-8")
    return pasta


def _sha(tmp_path, pre_sh=SHA_A):
    montados = _arquivo(tmp_path, "sha_container.txt", [
        f"{pre_sh}  /home/steam/cs2-dedicated/pre.sh",
        f"{SHA_B}  /home/steam/cs2-dedicated/game/csgo/addons/counterstrikesharp/plugins/"
        "Cs2TrackerEvents/Cs2TrackerEvents.dll"])
    referencia = _arquivo(tmp_path, "sha_checkout.txt", [
        f"{SHA_A}  docker/pre.sh",
        f"{SHA_B} *docker/plugins/Cs2TrackerEvents/Cs2TrackerEvents.dll"])
    return montados, referencia


def _log(*linhas):
    return ep.analisar_log("\n".join(linhas))


def _veredito_do_log(log, fatais=()):
    """Veredito com só o log (sem eventos, banco nem sha)."""
    res = {"log": log, "partidas": [], "entradas": {"eventos": None, "db": None},
           "sha": None, "config_hash": {"agora": None, "janela": None}}
    return ep.veredito(res, set(), set(fatais))


# ------------------------------------------------------------ recortes reais

def test_serie45_de_19_09_da_ruim_pela_colisao_e_sem_evidencia_do_map1(banco):
    res = ep.avaliar(log=SERIE45, eventos=EVENTOS, db=banco)
    log = res["log"]
    assert log["carimbo"] == "live_watch"
    assert log["linhas"] == 57   # só as [docker] do recorte (grep -c)
    assert [(p["demo_name"], p["mapa"], p["inicio_demo"]) for p in log["partidas"]] == [
        ("events_45_map0", "de_nuke", "2026-09-19T17:34:52"),
        ("events_45_map1", "de_dust2", "2026-09-19T18:01:08"),
        ("events_45_map2", "de_ancient", "2026-09-19T19:16:26"),
    ]
    assert log["partida_sem_fim"] is None and log["repetidos"] == []
    assert log["crash"] == {"segfault": 0, "stack_overflow": 0, "core_dumped": 0,
                            "fatal_motor": 0}
    assert log["overflow"]["episodios"] == [] and log["assinaturas"] == {}
    assert log["carregados"] == {} and log["builds"] == []

    por = {p["demo_name"]: p for p in res["partidas"]}
    m0, m1, m2 = por["events_45_map0"], por["events_45_map1"], por["events_45_map2"]
    assert (m0["arquivado"], m0["ingerida"], m0["colisoes"]) == (True, True, [])
    assert (m0["banco"]["map"], m0["banco"]["score_mine"], m0["banco"]["score_theirs"]) == \
        ("de_nuke", 6, 13)
    assert m0["times_5x5"] is None          # JSONL de 19/09 não tinha round_stats
    assert (m1["arquivado"], m1["ingerida"]) == (False, False)
    assert m2["colisoes"] == ["demo_path do banco aponta para events_45_map1"]

    assert res["current"]["estado"] == "cauda_normal" and res["current"]["rounds"] == [16]
    assert res["acervo"] == {
        "sem_linha_no_banco": ["events_50_map0"],
        "mapa_null": [],
        "placar_fora_do_mr12": {},
        "demo_path_divergente": {"events_45_map2": "events_45_map1"},
    }
    v = res["veredito"]
    assert v["g7"] == ep.RUIM
    assert v["ruim"] == ["events_45_map2: colisão: demo_path do banco aponta para events_45_map1"]
    assert v["sem_evidencia"] == [
        "log sem [MatchZy ... LOADED]: colete desde o StartedAt",
        "log sem [Cs2TrackerEvents] Pronto: colete desde o StartedAt",
        "events_45_map0: JSONL sem round_stats nem freeze_end para conferir o 5x5",
        "events_45_map1: JSONL não arquivado",
        "events_45_map1: não ingerida (sem linha no banco)",
        "events_45_map2: JSONL sem round_stats nem freeze_end para conferir o 5x5",
        "sha montados não conferidos (--sha-montados e --sha-referencia)",
    ]


def test_partida60_com_overflow_so_no_signon_da_ok(banco, tmp_path):
    montados, referencia = _sha(tmp_path)
    res = ep.avaliar(log=PARTIDA60, eventos=EVENTOS, db=banco,
                     sha_montados=montados, sha_referencia=referencia)
    log = res["log"]
    assert log["carimbo"] == "docker -t"
    assert log["versoes"] == {"metamod": "2.0.0.1469", "cssharp": "v1.0.375"}
    assert log["builds"] == ["1.41.8.5"]
    assert log["carregados"] == {"MatchZy": "0.8.15", "Cs2TrackerEvents": "Pronto"}
    assert log["boots_matchzy"] == 1 and log["prontos"] == 1
    assert log["assinaturas"] == {"CSSharp": {"CEntityIOOutput_FireOutputInternal": 1}}
    [episodio] = log["overflow"]["episodios"]
    assert (episodio["linha"], episodio["classe"], episodio["segundos_apos_full"],
            episodio["partida"]) == (13, "signon", 0.1, "events_60_map0")
    assert log["overflow"]["por_partida"] == {"events_60_map0": {"signon": 1}}

    [p] = res["partidas"]
    assert (p["demo_name"], p["mapa"], p["arquivado"], p["ingerida"]) == \
        ("events_60_map0", "de_anubis", True, True)
    assert (p["times_5x5"], p["colisoes"]) == (True, [])
    # Round 15 do recorte: utility 2+2+1+0+0+2+1+2+0 e flash 1+1+1+0+0+1+2+2+2
    # dos 9 bots; no round 3, 5 danos de HE de pancc/PerfectPin e a única
    # cegueira é do humano.
    assert p["granadas_bot"] == {"bots": 9, "dano_de_granada": 5, "cegueiras": 0,
                                 "motor": {"utility": 10, "flash": 10, "ate_round": 15}}
    assert res["sha"]["conferidos"] == ["Cs2TrackerEvents.dll", "pre.sh"]
    assert res["veredito"] == {"g7": ep.OK, "ruim": [], "sem_evidencia": []}
    assert ep.formatar(res).splitlines()[-1] == "VEREDITO G7: OK"


def test_assinatura_proibida_do_card_vira_ruim(banco, tmp_path):
    montados, referencia = _sha(tmp_path)
    res = ep.avaliar(log=PARTIDA60, eventos=EVENTOS, db=banco, sha_montados=montados,
                     sha_referencia=referencia,
                     assinaturas_proibidas=["CEntityIOOutput_FireOutputInternal"])
    assert res["veredito"]["ruim"] == [
        "assinatura proibida no log: CEntityIOOutput_FireOutputInternal"]


def test_fixtures_nao_tem_pii():
    arquivos = [p for p in FIX.rglob("*") if p.is_file()]
    assert len(arquivos) == 8
    for caminho in arquivos:
        assert pii.achar(caminho.read_text(encoding="utf-8")) == [], caminho.name


# ------------------------------------------------------------ carimbo de tempo

def test_carimbo_docker_t_e_texto_sem_prefixo():
    linhas, formato = ep.ler_linhas("2026-09-26T16:24:00.500000000Z [MatchZy] a\n"
                                    "2026-09-26T16:24:02Z b")
    assert formato == "docker -t"
    assert [(n, c) for n, _, c in linhas] == [(1, "[MatchZy] a"), (2, "b")]
    assert linhas[1][1] - linhas[0][1] == pytest.approx(1.5)


def test_carimbo_live_watch_so_linhas_docker_e_base_da_sessao():
    linhas, formato = ep.ler_linhas(
        "===== sessão iniciada 2026-09-19T14:31:32 =====\n"
        "[   99.7s] [docker ] (matchzy) [MatchZy] x\n"
        "[  100.0s] [evento ] round 1 COMEÇOU\n"
        "[  101.2s] [docker ] (round) y")
    assert formato == "live_watch"
    assert [(n, c) for n, _, c in linhas] == [(2, "[MatchZy] x"), (4, "y")]
    assert linhas[1][1] - linhas[0][1] == pytest.approx(1.5)


def test_carimbo_hora_passa_da_meia_noite_e_linha_L():
    hora, formato = ep.ler_linhas("23:59:59 a\n00:00:01 b")
    assert formato == "hora" and hora[1][1] - hora[0][1] == pytest.approx(2)
    ele, formato = ep.ler_linhas("L 09/26/2026 - 16:04:00: a\nL 09/26/2026 - 16:04:10: b")
    assert formato == "L" and ele[1][1] - ele[0][1] == pytest.approx(10)


def test_sem_carimbo_fica_sem_tempo():
    linhas, formato = ep.ler_linhas("a\nb")
    assert formato == "sem carimbo" and [t for _, t, _ in linhas] == [None, None]


# ------------------------------------------------------------ crash, plugins, versões

def test_contagem_de_crash_e_stack_overflow_nao_e_overflow_de_rede():
    log = _log(
        "./cs2.sh: line 109: 250 Segmentation fault (core dumped)",
        "Stack overflow.",
        'FATAL ERROR: Error reading from loaded packed store ".../botprofile.vpk"',
        "Aborted (core dumped)",
        "[MatchZy] tudo certo")
    assert log["crash"] == {"segfault": 1, "stack_overflow": 1, "core_dumped": 2,
                            "fatal_motor": 1}
    assert log["overflow"]["episodios"] == [] and log["fatal_plugin"] == []
    assert _veredito_do_log(log)["ruim"] == [
        "1x Segmentation fault no log", "1x Stack overflow no log",
        "2x core dumped no log", "1x FATAL ERROR no log"]


def test_log_limpo_nao_conta_crash():
    log = _log("[MatchZy 0.8.15 LOADED]", "Long frame: 20ms elapsed")
    assert set(log["crash"].values()) == {0}


def test_assinaturas_por_nome_e_por_plugin_e_recusados():
    log = _log(
        "CSSharp: Failed to find signature for 'CEntityIOOutput_FireOutputInternal'",
        "CSSharp: [EntityManager][EmitSoundFilter] - Failed to emit a sound. Signature "
        "for 'CBaseEntity_EmitSoundFilter' is not found. The latest update may have "
        "broken it.",
        "CSSharp: Failed to find signature for 'CEntityIOOutput_FireOutputInternal'",
        "(plugin: Patches - Bot AI) Vision_AlwaysWatchApproachPoints_Cave: FAILED",
        "(plugin: Patches - Bot AI) AttackState_RetreatOnSniper_Disable: FAILED",
        "(plugin: Patches - Bot AI) Nav_Something: OK",
        "[META] Failed to load plugin addons/RayTrace/bin/RayTrace.so: Plugin uses old "
        "SourceHook Metamod build")
    assert log["assinaturas"] == {
        "CSSharp": {"CEntityIOOutput_FireOutputInternal": 2, "CBaseEntity_EmitSoundFilter": 1},
        "Patches - Bot AI": {"Vision_AlwaysWatchApproachPoints_Cave": 1,
                             "AttackState_RetreatOnSniper_Disable": 1},
    }
    assert log["recusados"] == ["RayTrace.so"]


def test_fatal_error_de_plugin_e_ruim_salvo_quando_esperado():
    linha = ("(plugin: BotAimImprover) Fatal error during Load() (signature broken?). "
             "Plugin inactive.")
    log = _log(linha)
    assert log["fatal_plugin"] == [{"linha": 1, "plugin": "BotAimImprover", "texto": linha}]
    assert log["crash"]["fatal_motor"] == 0
    assert _veredito_do_log(log)["ruim"] == ["Fatal error de BotAimImprover (linha 1)"]
    assert _veredito_do_log(log, fatais={"BotAimImprover"})["ruim"] == []


def test_carga_versoes_e_build_que_muda_no_meio():
    log = _log(
        "[METAMOD SETUP] complete: version 2.0.0.1411 installed.",
        "[CSSHARP SETUP] complete: version v1.0.373 installed.",
        "ServerVersion=2000917  PatchVersion=1.41.8.4",
        "[MatchZy 0.8.15 LOADED]",
        "[Cs2TrackerEvents] Pronto — gravando em /x/current.jsonl",
        "Finished loading plugin RoundDamageRecap",
        "ServerVersion=2000918  PatchVersion=1.41.8.5",
        "[MatchZy 0.8.15 LOADED]")
    assert log["versoes"] == {"metamod": "2.0.0.1411", "cssharp": "v1.0.373"}
    assert log["builds"] == ["1.41.8.4", "1.41.8.5"]
    assert log["boots_matchzy"] == 2 and log["prontos"] == 1
    assert log["carregados"] == {"MatchZy": "0.8.15", "Cs2TrackerEvents": "Pronto",
                                 "RoundDamageRecap": "carregado"}
    v = _veredito_do_log(log)
    assert "build mudou no log (1.41.8.4 -> 1.41.8.5): 2 variáveis" in v["sem_evidencia"]
    assert not any("LOADED" in m or "Pronto" in m for m in v["sem_evidencia"])
    assert v["ruim"] == ["MatchZy carregou 2x: o processo reiniciou"]


# ------------------------------------------------------------ overflow

def test_overflow_signon_em_jogo_e_frequencia_por_partida():
    lento = "[Jogador] DISCONNECTING. ProcessMessages has taken more than 300ms"
    caiu = "[Server] Disconnect client 'Jogador' from server: NETWORK_DISCONNECT_OVERFLOW"
    full = "[SignonState] Client 1 'Jogador' signon state SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL"
    log = _log(*(f"2026-09-27T20:{hora}Z {texto}" for hora, texto in [
        ("00:00", lento),
        ("00:10", full),
        ("00:40", lento),
        ("00:40.5", "Disconnecting netchan because of excessive CPU usage"),
        ("01:00", "[MatchZy] [FULL CONNECT] Player ID: 1, Name: Jogador has connected!"),
        ("02:00.5", caiu),
        ("03:00", "[MatchZy] [HandleMatchEnd] MAP ENDED, isMatchSetup: True matchid: 61 "
                  "currentMapNumber: 0"),
        ("10:00", "-> SIGNONSTATE_FULL"),
        ("11:00", caiu),
    ]))
    ov = log["overflow"]
    assert [(e["linha"], e["classe"], e["segundos_apos_full"], e["linhas"], e["partida"])
            for e in ov["episodios"]] == [
        (1, "signon", None, 1, "events_61_map0"),     # antes de qualquer FULL
        (3, "signon", 30.0, 2, "events_61_map0"),     # 2 linhas, meio segundo entre elas
        (6, "em_jogo", 60.5, 1, "events_61_map0"),
        (9, "signon", 60.0, 1, None),                 # 60 s cravados ainda é signon
    ]
    assert ov["total"] == {"signon": 3, "em_jogo": 1}
    assert ov["por_partida"] == {"events_61_map0": {"signon": 2, "em_jogo": 1},
                                 "(fora de partida)": {"signon": 1}}
    assert "1 overflow(s) depois de SIGNONSTATE_FULL + 60 s" in _veredito_do_log(log)["ruim"]


def test_overflow_na_troca_de_mapa_antes_do_novo_full_e_signon():
    caiu = "[Server] Disconnect client 'Jogador' from server: NETWORK_DISCONNECT_OVERFLOW"
    log = _log(*(f"2026-09-27T21:{hora}Z {texto}" for hora, texto in [
        ("00:00", "[MatchZy] [FULL CONNECT] Player ID: 1, Name: Jogador has connected!"),
        ("30:00", "[MatchZy] [ChangeMap] Changing map to de_dust2 with delay 3"),
        ("30:20", caiu),                                   # 30 min depois do FULL antigo
        ("31:00", "[SignonState] Client 1 'Jogador' signon state SIGNONSTATE_SPAWN -> "
                  "SIGNONSTATE_FULL"),
        ("40:00", "[SignonState] Client 1 'Jogador' signon state SIGNONSTATE_FULL -> "
                  "SIGNONSTATE_NONE"),
        ("40:30", caiu),
    ]))
    assert [(e["linha"], e["classe"]) for e in log["overflow"]["episodios"]] == [
        (3, "signon"), (6, "signon")]


def test_overflow_sem_carimbo_depois_do_full_e_sem_evidencia():
    log = _log("NETWORK_DISCONNECT_OVERFLOW", "-> SIGNONSTATE_FULL",
               "NETWORK_DISCONNECT_OVERFLOW")
    assert [e["classe"] for e in log["overflow"]["episodios"]] == ["signon", "sem_carimbo"]
    v = _veredito_do_log(log)
    assert v["ruim"] == []
    assert ("1 overflow(s) depois de FULL sem carimbo de tempo: salve o log com docker logs -t"
            in v["sem_evidencia"])


# ------------------------------------------------------------ placar, mapa, banco

@pytest.mark.parametrize("placar", [(13, 0), (13, 11), (11, 13), (16, 12), (16, 14),
                                    (15, 19), (22, 20), (21, 21)])
def test_placar_que_fecha_mr12(placar):
    assert ep.motivo_placar(*placar) is None


@pytest.mark.parametrize("placar", [(13, 12), (12, 12), (12, 5), (16, 15), (17, 14),
                                    (14, 12), (19, 14), (25, 21), (None, 13)])
def test_placar_que_nao_fecha_mr12(placar):
    assert ep.motivo_placar(*placar) is not None


def test_placar_incompleto_diz_que_ninguem_chegou_a_13():
    assert ep.motivo_placar(12, 5) == "12x5: ninguém chegou a 13 (partida incompleta)"


def test_mapa_null_placar_fora_e_soma_por_lado_no_banco(banco, tmp_path):
    _inserir(banco, "events_61_map0", None, (13, 12), (13, 12))
    _inserir(banco, "events_62_map0", "de_nuke", (13, 2), (3, 11))
    fim = "[MatchZy] [HandleMatchEnd] MAP ENDED, isMatchSetup: True matchid: {} currentMapNumber: 0"
    log = _arquivo(tmp_path, "docker.log", [fim.format(61), fim.format(62)])
    res = ep.avaliar(log=log, db=banco)
    ruim = res["veredito"]["ruim"]
    assert "events_61_map0: mapa NULL no banco" in ruim
    assert ("events_61_map0: placar 13x12 não fecha MR12 (13 no tempo normal; 16, 19 ou 22 "
            "na prorrogação)") in ruim
    assert ("events_62_map0: placar por lado (3+11) não soma o placar da partida (13+2)"
            in ruim)
    assert res["acervo"]["mapa_null"] == ["events_61_map0"]
    assert list(res["acervo"]["placar_fora_do_mr12"]) == ["events_61_map0"]


def test_jsonl_arquivado_sem_linha_some_quando_a_linha_existe(banco):
    _inserir(banco, "events_50_map0", "de_mirage", (13, 9), (9, 13))
    res = ep.avaliar(eventos=EVENTOS, db=banco)
    assert res["acervo"]["sem_linha_no_banco"] == []


def test_colisao_por_demo_name_repetido_linha_antiga_e_mapa_diferente(banco, tmp_path):
    demo = ("[MatchZy] [StartDemoRecoding] Starting demo recording, path: "
            "MatchZy/2026-09-28_20-00-00_45_{}_Jogador_vs_Bots.dem")
    fim = "[MatchZy] [HandleMatchEnd] MAP ENDED, isMatchSetup: True matchid: 45 currentMapNumber: 0"
    log = _arquivo(tmp_path, "docker.log", [demo.format("de_mirage"), fim,
                                            demo.format("de_mirage"), fim])
    res = ep.avaliar(log=log, db=banco)
    assert res["log"]["repetidos"] == ["events_45_map0"]
    [p] = res["partidas"]
    assert p["colisoes"] == [
        "demo_name repetido no log (matchid reusado)",
        "mapa do banco (de_nuke) difere do log (de_mirage)",
        "linha do banco é de 2026-09-19, antes da partida do log (2026-09-28)",
    ]
    assert res["veredito"]["g7"] == ep.RUIM


# ------------------------------------------------------------ eventos

def test_current_com_rounds_nao_arquivados_e_ruim(tmp_path):
    pasta = _pasta_eventos(tmp_path, {"current.jsonl": [
        {"type": "snapshot", "round_num": 2, "tick": 1, "players": []},
        {"type": "round_start", "round_num": 3, "tick": 2, "human_side": "t"},
        {"type": "player_hurt", "round_num": 3, "tick": 3, "weapon": "ak47"}]})
    res = ep.avaliar(eventos=pasta)
    assert res["current"] == {"estado": "com_rounds", "rounds": [3], "linhas_ruins": 0,
                              "tipos": {"snapshot": 1, "round_start": 1, "player_hurt": 1}}
    assert "current.jsonl com rounds não arquivados (rounds [3])" in res["veredito"]["ruim"]


def test_current_cauda_real_vazio_e_ausente(tmp_path):
    cauda = ep.analisar_current(EVENTOS)
    assert cauda["estado"] == "cauda_normal"
    assert cauda["tipos"] == {"snapshot": 43, "round_stats": 1, "round_officially_ended": 1}
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    assert ep.analisar_current(vazio) == {"estado": "ausente"}
    (vazio / "current.jsonl").write_text("", encoding="utf-8")
    assert ep.analisar_current(vazio)["estado"] == "vazio"


def test_times_5x5_do_round_stats_freeze_end_e_sem_dado():
    evs60, _ = ep.ler_jsonl(EVENTOS / "events_60_map0.jsonl")
    assert ep.times(evs60) == (True, {})
    seis = [{"side": "ct"}] * 6 + [{"side": "t"}] * 5 + [{"side": ""}]
    assert ep.times([{"type": "round_stats", "round_num": 2, "players": seis}]) == \
        (False, {2: (6, 5)})
    assert ep.times([{"type": "freeze_end", "round_num": 1, "players": seis[1:]}]) == (True, {})
    assert ep.times([{"type": "round_start", "round_num": 1}]) == (None, {})


def test_granadas_de_bot_sem_flag_de_bot_nao_mede():
    evs45, _ = ep.ler_jsonl(EVENTOS / "events_45_map0.jsonl")
    assert ep.granadas_bot(evs45) is None


def test_granadas_de_bot_conta_so_bot_e_so_granada():
    jogadores = [{"name": "bot1", "is_bot": True, "side": "t", "utility_count": 3,
                  "flash_count": 2},
                 {"name": "Jogador", "is_bot": False, "side": "ct", "utility_count": 9,
                  "flash_count": 9},
                 {"name": "GOTV", "is_bot": True, "side": "", "utility_count": 7,
                  "flash_count": 7}]
    eventos = [
        {"type": "round_stats", "round_num": 4, "players": jogadores},
        {"type": "player_hurt", "attacker_name": "bot1", "weapon": "hegrenade"},
        {"type": "player_hurt", "attacker_name": "bot1", "weapon": "inferno"},
        {"type": "player_hurt", "attacker_name": "bot1", "weapon": "ak47"},
        {"type": "player_hurt", "attacker_name": "Jogador", "weapon": "hegrenade"},
        {"type": "player_blind", "attacker_name": "bot1"},
        {"type": "player_blind", "attacker_name": "Jogador"},
    ]
    assert ep.granadas_bot(eventos) == {"bots": 1, "dano_de_granada": 2, "cegueiras": 1,
                                        "motor": {"utility": 3, "flash": 2, "ate_round": 4}}


# ------------------------------------------------------------ sha e config-hash

def test_sha_montado_divergente_e_sem_evidencia(banco, tmp_path):
    montados, referencia = _sha(tmp_path, pre_sh="c" * 64)
    res = ep.avaliar(log=PARTIDA60, eventos=EVENTOS, db=banco,
                     sha_montados=montados, sha_referencia=referencia)
    assert res["sha"]["divergentes"] == ["pre.sh"]
    assert res["veredito"] == {"g7": ep.SEM, "ruim": [],
                               "sem_evidencia": ["sha montado divergente: pre.sh"]}


def test_config_hash_diferente_do_da_janela_e_sem_evidencia(banco, tmp_path):
    montados, referencia = _sha(tmp_path)
    res = ep.avaliar(log=PARTIDA60, eventos=EVENTOS, db=banco, sha_montados=montados,
                     sha_referencia=referencia, config_hash="abc", config_hash_janela="abd")
    assert res["veredito"]["sem_evidencia"] == ["config-hash diferente do da janela"]


# ------------------------------------------------------------ só leitura

def test_banco_abre_so_leitura_e_mtime_fica_intacto(banco):
    antes = banco.stat()
    conteudo = hashlib.sha256(banco.read_bytes()).hexdigest()
    res = ep.avaliar(log=SERIE45, eventos=EVENTOS, db=banco)
    depois = banco.stat()
    assert res["entradas"]["banco_intacto"] is True
    assert (depois.st_mtime_ns, depois.st_size) == (antes.st_mtime_ns, antes.st_size)
    assert hashlib.sha256(banco.read_bytes()).hexdigest() == conteudo
    assert sorted(p.name for p in banco.parent.iterdir()) == ["copia.sqlite"]
    conn = ep.abrir_banco(banco)
    # Mesmo desligando o query_only, o mode=ro do arquivo continua barrando.
    conn.execute("PRAGMA query_only = 0")
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("DELETE FROM matches")
    conn.close()


def test_banco_real_recusado_sem_a_flag_e_so_leitura_com_ela(banco, monkeypatch, capsys):
    monkeypatch.setattr(ep, "BANCO_REAL", banco)
    antes = banco.stat()
    assert ep.main(["--db", str(banco)]) == 2
    assert "recusado: é o banco real" in capsys.readouterr().err
    assert ep.main(["--db", str(banco), "--leitura-banco-real", "--json"]) == 3
    saida = json.loads(capsys.readouterr().out)
    assert saida["entradas"]["banco_intacto"] is True
    assert banco.stat().st_mtime_ns == antes.st_mtime_ns


def test_main_json_e_codigo_de_saida(banco, tmp_path, capsys):
    montados, referencia = _sha(tmp_path)
    codigo = ep.main(["--log", str(PARTIDA60), "--eventos", str(EVENTOS), "--db", str(banco),
                      "--sha-montados", str(montados), "--sha-referencia", str(referencia),
                      "--json"])
    assert codigo == 0
    assert json.loads(capsys.readouterr().out)["veredito"]["g7"] == "OK"
    assert ep.main(["--log", str(SERIE45), "--eventos", str(EVENTOS), "--db", str(banco)]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == (
        "VEREDITO G7: RUIM — events_45_map2: colisão: demo_path do banco aponta para "
        "events_45_map1")


def test_sem_partida_terminada_e_partida_sem_fim(tmp_path):
    log = _arquivo(tmp_path, "docker.log", [
        "[MatchZy] [ChangeMap] Changing map to de_inferno with delay 0",
        "[MatchZy] [StartLive] Starting Live! Executing Live CFG from MatchZy/live.cfg"])
    res = ep.avaliar(log=log)
    assert res["log"]["partida_sem_fim"] == {"mapa": "de_inferno", "inicio_demo": None,
                                             "linha_inicio": 1}
    assert "nenhuma partida terminou no log (MAP ENDED)" in res["veredito"]["sem_evidencia"]
