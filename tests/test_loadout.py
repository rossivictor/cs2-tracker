#!/usr/bin/env python3
"""
Testes de stats.match_loadout — economia e tempo cego por round, vindos das
PLAYER_PROPS que o parser passou a pedir ao awpy em 21/09/2026.

O que precisa ficar fixo aqui é o contrato de degradação: partida sem esses
dados (ingerida pelo plugin, ou de .dem parseada antes da mudança) tem que
devolver vazio, não zero — zero diria "você não comprou nada", e o certo é
"não sabemos".
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matches
import stats
from parser import init_db

MID = 1


def _conn(tmp_path):
    conn = init_db(str(tmp_path / "t.db"))
    conn.execute(
        "INSERT INTO matches (id, demo_name, map, played_at, player_name, source) "
        "VALUES (?, 'd.dem', 'de_mirage', '2026-09-20T20:00:00', 'cobaia', 'demo')",
        (MID,),
    )
    return conn


def _round(conn, num, freeze_end=100, human_side="t", winner="t"):
    conn.execute(
        """INSERT INTO rounds (match_id, round_num, winner_side, human_side, counted,
                               start_tick, freeze_end_tick, end_tick)
           VALUES (?,?,?,?,1,?,?,?)""",
        (MID, num, winner, human_side, freeze_end - 50, freeze_end, freeze_end + 1000),
    )


def _pos(conn, rnd, tick, equip=None, flash=None, armor=None, helmet=None, defuser=None):
    conn.execute(
        """INSERT INTO player_positions (match_id, round_num, tick, x, y, z, side, place, health,
                                          flash_duration, equip_value, armor, has_helmet, has_defuser)
           VALUES (?,?,?,0,0,0,'t',NULL,100,?,?,?,?,?)""",
        (MID, rnd, tick, flash, equip, armor, helmet, defuser),
    )


def _loadout(tmp_path, conn):
    conn.commit()
    path = str(tmp_path / "t.db")
    conn.close()
    return stats.match_loadout(path, MID)


# --------------------------------------------------------------------------- #
# Classificação de compra
# --------------------------------------------------------------------------- #

def test_classificacao_de_compra():
    assert stats.classify_buy(0) == "eco"
    assert stats.classify_buy(1999) == "eco"
    assert stats.classify_buy(2000) == "force"
    assert stats.classify_buy(3999) == "force"
    assert stats.classify_buy(4000) == "full"
    assert stats.classify_buy(None) is None


# --------------------------------------------------------------------------- #
# Equipamento
# --------------------------------------------------------------------------- #

def test_equipamento_vem_do_fim_do_freeze_time(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, freeze_end=100)
    # Durante o freeze time a compra ainda está acontecendo...
    _pos(conn, 1, 50, equip=200, armor=0)
    # ...no fim dele é o que vale...
    _pos(conn, 1, 100, equip=4850, armor=100, helmet=1, defuser=1)
    # ...e depois entra arma recolhida do chão, que não é compra.
    _pos(conn, 1, 500, equip=9000, armor=100)
    lo = _loadout(tmp_path, conn)
    assert lo[1]["equip_value"] == 4850
    assert lo[1]["buy"] == "full"
    assert lo[1]["armor"] == 100
    assert lo[1]["has_helmet"] is True
    assert lo[1]["has_defuser"] is True


def test_round_sem_freeze_end_fica_de_fora(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        """INSERT INTO rounds (match_id, round_num, winner_side, human_side, counted, freeze_end_tick)
           VALUES (?,1,'t','t',1,NULL)""",
        (MID,),
    )
    _pos(conn, 1, 100, equip=4850)
    assert _loadout(tmp_path, conn) == {}


def test_partida_sem_props_devolve_vazio_e_nao_zero(tmp_path):
    # É o caso das partidas ingeridas pelo plugin: rounds existem, posições
    # existem (sintéticas), mas as colunas novas são NULL.
    conn = _conn(tmp_path)
    _round(conn, 1, freeze_end=100)
    _pos(conn, 1, 100)  # tudo None
    lo = _loadout(tmp_path, conn)
    assert lo[1]["equip_value"] is None
    assert lo[1]["buy"] is None


# --------------------------------------------------------------------------- #
# Tempo cego
# --------------------------------------------------------------------------- #

def test_tempo_cego_soma_so_as_subidas(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, freeze_end=100)
    _pos(conn, 1, 100, equip=4850, flash=0.0)
    # Uma flash de 2s: sobe pra 2.0 e vai decaindo tick a tick. Somar os
    # valores daria 2+1.5+1.0+0.5 = 5s de "cego" numa flash de 2s.
    _pos(conn, 1, 110, flash=2.0)
    _pos(conn, 1, 120, flash=1.5)
    _pos(conn, 1, 130, flash=1.0)
    _pos(conn, 1, 140, flash=0.5)
    _pos(conn, 1, 150, flash=0.0)
    lo = _loadout(tmp_path, conn)
    assert lo[1]["blind_time"] == 2.0
    assert lo[1]["flashes"] == 1


def test_duas_flashes_no_mesmo_round_contam_duas_vezes(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, freeze_end=100)
    _pos(conn, 1, 100, equip=4850, flash=0.0)
    _pos(conn, 1, 110, flash=2.0)
    _pos(conn, 1, 120, flash=0.0)
    _pos(conn, 1, 130, flash=1.5)
    _pos(conn, 1, 140, flash=0.0)
    lo = _loadout(tmp_path, conn)
    assert lo[1]["blind_time"] == 3.5
    assert lo[1]["flashes"] == 2


def test_flash_nao_vaza_entre_rounds(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, freeze_end=100)
    _round(conn, 2, freeze_end=200)
    _pos(conn, 1, 100, equip=4850, flash=0.0)
    _pos(conn, 1, 110, flash=3.0)
    _pos(conn, 2, 200, equip=4850, flash=0.0)
    _pos(conn, 2, 210, flash=1.0)
    lo = _loadout(tmp_path, conn)
    assert lo[1]["blind_time"] == 3.0
    assert lo[2]["blind_time"] == 1.0


def test_round_sem_flash_tem_tempo_cego_zero(tmp_path):
    conn = _conn(tmp_path)
    _round(conn, 1, freeze_end=100)
    _pos(conn, 1, 100, equip=4850, flash=0.0)
    lo = _loadout(tmp_path, conn)
    assert lo[1]["blind_time"] == 0.0
    assert lo[1]["flashes"] == 0


def test_banco_inexistente_devolve_vazio(tmp_path):
    assert stats.match_loadout(str(tmp_path / "nao_existe.db"), 1) == {}


# --------------------------------------------------------------------------- #
# Integração com a tela
# --------------------------------------------------------------------------- #

def _match_with_loadout(tmp_path, equips):
    conn = _conn(tmp_path)
    for i, equip in enumerate(equips, start=1):
        _round(conn, i, freeze_end=i * 1000)
        _pos(conn, i, i * 1000, equip=equip, armor=100, helmet=1, defuser=0, flash=0.0)
        conn.execute(
            """INSERT INTO kills (match_id, round_num, tick, attacker_name, victim_name,
                                  attacker_side, victim_side, weapon, headshot,
                                  attacker_is_human, victim_is_human)
               VALUES (?,?,?,'cobaia','arT','t','ct','ak47',1,1,0)""",
            (MID, i, i * 1000 + 10),
        )
        conn.execute(
            """INSERT INTO damages (match_id, round_num, weapon, hitgroup, dmg_health,
                                    attacker_is_human, victim_is_human)
               VALUES (?,?,'ak47','head',100,1,0)""",
            (MID, i),
        )
    conn.commit()
    conn.close()
    return str(tmp_path / "t.db")


def test_tela_de_detalhe_traz_economia_por_round(tmp_path):
    path = _match_with_loadout(tmp_path, [800, 2500, 5000])
    ctx = matches.build_detail_context(path, MID)
    buys = [r["loadout"]["buy"] for r in ctx["rounds"]]
    assert buys == ["eco", "force", "full"]
    assert ctx["rounds"][0]["loadout"]["equip_bar"] <= 100


def test_barra_de_equipamento_satura_em_cem(tmp_path):
    path = _match_with_loadout(tmp_path, [99000])
    ctx = matches.build_detail_context(path, MID)
    assert ctx["rounds"][0]["loadout"]["equip_bar"] == 100


def test_resumo_de_compra_da_partida(tmp_path):
    path = _match_with_loadout(tmp_path, [800, 2500, 5000, 5000])
    ctx = matches.build_detail_context(path, MID)
    resumo = ctx["loadout_summary"]
    assert resumo["rounds"] == 4
    assert resumo["avg_equip"] == round((800 + 2500 + 5000 + 5000) / 4)
    assert {b["key"]: b["count"] for b in resumo["buys"]} == {"eco": 1, "force": 1, "full": 2}


def test_tela_sem_loadout_nao_mostra_economia(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        """INSERT INTO rounds (match_id, round_num, winner_side, human_side, counted)
           VALUES (?,1,'t','t',1)""",
        (MID,),
    )
    conn.execute(
        """INSERT INTO kills (match_id, round_num, tick, attacker_name, victim_name,
                              attacker_side, victim_side, weapon, headshot,
                              attacker_is_human, victim_is_human)
           VALUES (?,1,10,'cobaia','arT','t','ct','ak47',1,1,0)""",
        (MID,),
    )
    conn.commit()
    conn.close()
    ctx = matches.build_detail_context(str(tmp_path / "t.db"), MID)
    assert ctx["loadout_summary"] is None
    assert ctx["rounds"][0]["loadout"] is None
