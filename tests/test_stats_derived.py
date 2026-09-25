#!/usr/bin/env python3
"""
Testes das métricas derivadas novas de stats.py (F6.1): KAST, trades,
multi-kills, clutches, regiões de acerto e head-to-head.

Todas saem do que já estava gravado no banco — nenhuma exige mudança de
ingestão. O que essas métricas têm de traiçoeiro é a dependência de ORDEM
(tick) e de LADO (attacker_side/victim_side), e é isso que estes testes
fixam: a janela de trade tem borda, e quando o lado não vem a métrica
precisa sair None em vez de sair errada.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stats
from parser import init_db
from stats import TRADE_WINDOW_TICKS

MID = 1


def _conn(tmp_path):
    conn = init_db(str(tmp_path / "t.db"))
    conn.execute(
        "INSERT INTO matches (id, demo_name, map, played_at, player_name, source) "
        "VALUES (?, 'd.dem', 'de_mirage', '2026-09-20T20:00:00', 'can1sh', 'demo')",
        (MID,),
    )
    conn.row_factory = sqlite3.Row
    return conn


def _round(conn, num, human_side="t", winner="t", counted=1):
    conn.execute(
        """INSERT INTO rounds (match_id, round_num, winner_side, human_side, counted)
           VALUES (?, ?, ?, ?, ?)""",
        (MID, num, winner, human_side, counted),
    )


def _kill(conn, rnd, tick, attacker, victim, a_side, v_side,
          a_human=0, v_human=0, weapon="ak47", headshot=0, post_mortem=0):
    conn.execute(
        """INSERT INTO kills (match_id, round_num, tick, attacker_name, victim_name,
                              attacker_side, victim_side, weapon, headshot,
                              attacker_is_human, victim_is_human, post_mortem)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (MID, rnd, tick, attacker, victim, a_side, v_side, weapon, headshot,
         a_human, v_human, post_mortem),
    )


def _damage(conn, rnd, hitgroup, dmg, a_human=1):
    conn.execute(
        """INSERT INTO damages (match_id, round_num, weapon, hitgroup, dmg_health,
                                attacker_is_human, victim_is_human)
           VALUES (?,?,'ak47',?,?,?,0)""",
        (MID, rnd, hitgroup, dmg, a_human),
    )


def _build(conn):
    row = conn.execute("SELECT * FROM matches WHERE id=?", (MID,)).fetchone()
    return stats.build_match_data(conn, row)


def _all(conn):
    return _build(conn)["stats"]["all"]


# --------------------------------------------------------------------------- #
# normalize_hitgroup — os dois formatos que convivem no banco
# --------------------------------------------------------------------------- #

def test_normalize_hitgroup_aceita_texto_e_numero():
    # Origem 'demo' grava texto, origem 'events' grava o enum do engine.
    assert stats.normalize_hitgroup("head") == "head"
    assert stats.normalize_hitgroup("1") == "head"
    assert stats.normalize_hitgroup("chest") == stats.normalize_hitgroup("2") == "chest"
    assert stats.normalize_hitgroup("left_arm") == stats.normalize_hitgroup("4") == "arms"
    assert stats.normalize_hitgroup("right_leg") == stats.normalize_hitgroup("7") == "legs"


def test_normalize_hitgroup_agrupa_neck_em_cabeca_e_generic_em_outros():
    assert stats.normalize_hitgroup("neck") == "head"
    assert stats.normalize_hitgroup("generic") == stats.normalize_hitgroup("0") == "other"
    assert stats.normalize_hitgroup("gear") == "other"
    assert stats.normalize_hitgroup(None) is None
    assert stats.normalize_hitgroup("inexistente") is None


def test_hitgroups_somam_as_duas_fontes_na_mesma_regiao(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _damage(conn, 1, "head", 100)   # formato demo
    _damage(conn, 1, "1", 50)       # formato plugin, mesma região
    _damage(conn, 1, "chest", 30)
    rows = {r["hitgroup"]: r for r in _build(conn)["hitgroups"]["all"]}
    assert rows["head"]["hits"] == 2
    assert rows["head"]["dmg"] == 150
    assert rows["chest"]["hits"] == 1


def test_hitgroups_ignoram_dano_que_nao_e_seu(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _damage(conn, 1, "head", 100, a_human=0)
    assert _build(conn)["hitgroups"]["all"] == []


# --------------------------------------------------------------------------- #
# KAST
# --------------------------------------------------------------------------- #

def test_kast_conta_round_com_kill(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "bot1", "t", "ct", a_human=1)
    s = _all(conn)
    assert s["kast_rounds"] == 1
    assert s["kast_pct"] == 100.0


def test_kast_conta_round_em_que_voce_sobreviveu_sem_matar(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "bot_ct", "bot_t", "ct", "t")  # ninguém seu morreu
    assert _all(conn)["kast_rounds"] == 1


def test_kast_nao_conta_round_em_que_voce_morreu_sem_trade(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "algoz", "can1sh", "ct", "t", v_human=1)
    s = _all(conn)
    assert s["kast_rounds"] == 0
    assert s["kast_pct"] == 0.0


def test_kast_conta_round_em_que_voce_foi_trocado(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "algoz", "can1sh", "ct", "t", v_human=1)
    # Aliado (mesmo lado que você no round) vinga dentro da janela.
    _kill(conn, 1, 100 + TRADE_WINDOW_TICKS - 1, "aliado", "algoz", "t", "ct")
    s = _all(conn)
    assert s["kast_rounds"] == 1
    assert s["traded_deaths"] == 1


def test_vinganca_fora_da_janela_nao_e_trade(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "algoz", "can1sh", "ct", "t", v_human=1)
    _kill(conn, 1, 100 + TRADE_WINDOW_TICKS + 1, "aliado", "algoz", "t", "ct")
    s = _all(conn)
    assert s["traded_deaths"] == 0
    assert s["kast_rounds"] == 0


def test_kast_sem_assists_sempre_sinalizado(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "bot1", "t", "ct", a_human=1)
    assert _all(conn)["kast_has_assists"] is False


# --------------------------------------------------------------------------- #
# Trade kills feitos por você
# --------------------------------------------------------------------------- #

def test_trade_kill_quando_voce_vinga_um_aliado(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "algoz", "aliado", "ct", "t")          # aliado seu morre
    _kill(conn, 1, 150, "can1sh", "algoz", "t", "ct", a_human=1)  # você vinga
    assert _all(conn)["trade_kills"] == 1


def test_kill_normal_nao_vira_trade(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 150, "can1sh", "inimigo", "t", "ct", a_human=1)
    assert _all(conn)["trade_kills"] == 0


def test_vingar_morte_de_inimigo_nao_e_trade(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    # Quem morreu antes era do lado CT, não do seu: matar o algoz não é trade.
    _kill(conn, 1, 100, "outro_t", "bot_ct", "t", "ct")
    _kill(conn, 1, 150, "can1sh", "outro_t", "t", "t", a_human=1)
    assert _all(conn)["trade_kills"] == 0


# --------------------------------------------------------------------------- #
# Lado desconhecido: degrada explicitamente em vez de mentir
# --------------------------------------------------------------------------- #

def test_sem_lado_trades_e_clutches_saem_none(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    # É o caso real das partidas ingeridas de .dem: kills sem lado.
    _kill(conn, 1, 100, "algoz", "can1sh", None, None, v_human=1)
    _kill(conn, 1, 150, "aliado", "algoz", None, None)
    s = _all(conn)
    assert s["trade_kills"] is None
    assert s["traded_deaths"] is None
    assert s["clutches"] is None
    assert s["clutch_count"] is None
    assert s["kast_has_trades"] is False
    # KAST continua saindo — as componentes K e S não dependem de lado.
    assert s["kast_pct"] is not None


# --------------------------------------------------------------------------- #
# Multi-kills
# --------------------------------------------------------------------------- #

def test_multi_kills_por_round(tmp_path):
    conn = _conn(tmp_path)
    for rnd, n in ((1, 1), (2, 2), (3, 3), (4, 5)):
        _round(conn, rnd)
        for i in range(n):
            _kill(conn, rnd, 100 + i, "can1sh", f"bot{i}", "t", "ct", a_human=1)
    mk = _all(conn)["multi_kills"]
    assert mk == {"2k": 1, "3k": 1, "4k": 0, "5k": 1}


def test_seis_kills_num_round_entram_no_balde_de_ace(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    for i in range(6):
        _kill(conn, 1, 100 + i, "can1sh", f"bot{i}", "t", "ct", a_human=1)
    assert _all(conn)["multi_kills"]["5k"] == 1


def test_kill_pos_mortem_nao_conta_como_sua(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "bot1", "t", "ct", a_human=1)
    # Takeover de bot depois da sua morte: existe no jogo, não é sua.
    _kill(conn, 1, 200, "can1sh", "bot2", "t", "ct", a_human=1, post_mortem=1)
    s = _all(conn)
    assert s["kills"] == 1
    assert s["multi_kills"]["2k"] == 0


# --------------------------------------------------------------------------- #
# Clutches
# --------------------------------------------------------------------------- #

def _kill_teammates(conn, rnd, n, start_tick=100):
    """Mata n aliados seus (lado 't'), um por tick."""
    for i in range(n):
        _kill(conn, rnd, start_tick + i, "inimigo", f"aliado{i}", "ct", "t")


def test_clutch_1v2_ganho(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, human_side="t", winner="t")
    # 3 inimigos já caíram -> sobram 2; seus 4 aliados caem -> você fica só.
    for i in range(3):
        _kill(conn, 1, 10 + i, "aliado0", f"ct{i}", "t", "ct")
    _kill_teammates(conn, 1, 4, start_tick=100)
    s = _all(conn)
    assert s["clutches"] == [{"vs": 2, "count": 1, "wins": 1}]
    assert s["clutch_count"] == 1
    assert s["clutch_wins"] == 1


def test_clutch_perdido_conta_como_tentativa(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, human_side="t", winner="ct")
    _kill_teammates(conn, 1, 4)
    s = _all(conn)
    assert s["clutch_count"] == 1
    assert s["clutch_wins"] == 0
    assert s["clutches"][0]["vs"] == 5


def test_sem_clutch_quando_alguem_do_seu_lado_sobrevive(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, human_side="t", winner="t")
    _kill_teammates(conn, 1, 3)  # sobram você + 1 aliado
    assert _all(conn)["clutch_count"] == 0


def test_morrer_antes_de_ficar_sozinho_nao_e_clutch(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, human_side="t", winner="ct")
    _kill_teammates(conn, 1, 3, start_tick=100)
    _kill(conn, 1, 200, "inimigo", "can1sh", "ct", "t", v_human=1)  # você morre
    _kill(conn, 1, 300, "inimigo", "aliado_ultimo", "ct", "t")      # o último cai depois
    assert _all(conn)["clutch_count"] == 0


# --------------------------------------------------------------------------- #
# Head-to-head
# --------------------------------------------------------------------------- #

def test_head_to_head_saldo_por_adversario(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "arT", "t", "ct", a_human=1)
    _kill(conn, 1, 110, "can1sh", "arT", "t", "ct", a_human=1)
    _kill(conn, 1, 120, "arT", "can1sh", "ct", "t", v_human=1)
    _kill(conn, 1, 130, "can1sh", "KSCERATO", "t", "ct", a_human=1)
    rows = {r["opponent"]: r for r in _build(conn)["head_to_head"]["all"]}
    assert rows["arT"] == {"opponent": "arT", "kills": 2, "deaths": 1, "diff": 1}
    assert rows["KSCERATO"]["diff"] == 1


def test_head_to_head_ignora_fogo_amigo(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "aliado", "t", "t", a_human=1)
    assert _build(conn)["head_to_head"]["all"] == []


def test_head_to_head_ignora_suicidio(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "can1sh", "t", "t", a_human=1, v_human=1, weapon="world")
    assert _build(conn)["head_to_head"]["all"] == []


def test_head_to_head_agregado_soma_entre_partidas(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1)
    _kill(conn, 1, 100, "can1sh", "arT", "t", "ct", a_human=1)
    conn.commit()
    data = stats.load_stats(str(tmp_path / "t.db"))
    rows = {r["opponent"]: r for r in data["head_to_head"]["all"]}
    assert rows["arT"]["kills"] == 1


# --------------------------------------------------------------------------- #
# Rounds não contados continuam fora de tudo
# --------------------------------------------------------------------------- #

def test_round_nao_contado_fica_fora_do_kast(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, counted=1)
    _kill(conn, 1, 100, "can1sh", "bot1", "t", "ct", a_human=1)
    _round(conn, 2, counted=0)
    _kill(conn, 2, 200, "algoz", "can1sh", "ct", "t", v_human=1)
    s = _all(conn)
    assert s["rounds_played"] == 1
    assert s["kast_pct"] == 100.0
