#!/usr/bin/env python3
"""
Testes de stats.human_quick_summary — usado pela linha do jogador humano na
tela de Lineups (item 2, 2026-09-20). Sem depender do relatório completo.

Calcula a partir de kills/damages (attacker_is_human/victim_is_human), a
mesma fonte que as partidas reais 'demo'/'events' usam — matches.agg_* só
existe pra partidas ingeridas via CSV puro, que não populam kills/damages/
rounds (ver stats.human_quick_summary e parser.store_match_from_csv).
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parser import init_db
from stats import human_quick_summary


def _insert_match(conn, match_id, demo_name, map_name="de_mirage"):
    conn.execute(
        "INSERT INTO matches (id, demo_name, map, player_name) VALUES (?, ?, ?, 'cobaia')",
        (match_id, demo_name, map_name),
    )


def _insert_round(conn, match_id, round_num, counted=1):
    conn.execute(
        "INSERT INTO rounds (match_id, round_num, counted) VALUES (?, ?, ?)",
        (match_id, round_num, counted),
    )


def _insert_kill(conn, match_id, round_num, attacker_is_human, victim_is_human):
    conn.execute(
        """INSERT INTO kills (match_id, round_num, attacker_is_human, victim_is_human)
           VALUES (?, ?, ?, ?)""",
        (match_id, round_num, attacker_is_human, victim_is_human),
    )


def _insert_damage(conn, match_id, round_num, dmg_health, attacker_is_human=1):
    conn.execute(
        """INSERT INTO damages (match_id, round_num, dmg_health, attacker_is_human)
           VALUES (?, ?, ?, ?)""",
        (match_id, round_num, dmg_health, attacker_is_human),
    )


def test_missing_db_returns_empty_summary(tmp_path):
    summary = human_quick_summary(tmp_path / "does_not_exist.db")
    assert summary == {"matches": 0, "adr": None, "kd": None}


def test_empty_db_returns_empty_summary(tmp_path):
    db_path = tmp_path / "empty.db"
    init_db(str(db_path))
    summary = human_quick_summary(db_path)
    assert summary == {"matches": 0, "adr": None, "kd": None}


def test_summary_computed_from_kills_damages_and_counted_rounds(tmp_path):
    db_path = tmp_path / "cs2_tracker.db"
    init_db(str(db_path))
    conn = sqlite3.connect(db_path)
    _insert_match(conn, 1, "m1")
    for round_num in range(1, 6):
        _insert_round(conn, 1, round_num, counted=1)
    # 3 abates do humano, 2 mortes do humano, 500 de dano total em 5 rounds contados.
    _insert_kill(conn, 1, 1, attacker_is_human=1, victim_is_human=0)
    _insert_kill(conn, 1, 2, attacker_is_human=1, victim_is_human=0)
    _insert_kill(conn, 1, 3, attacker_is_human=1, victim_is_human=0)
    _insert_kill(conn, 1, 4, attacker_is_human=0, victim_is_human=1)
    _insert_kill(conn, 1, 5, attacker_is_human=0, victim_is_human=1)
    for round_num in range(1, 6):
        _insert_damage(conn, 1, round_num, dmg_health=100, attacker_is_human=1)
    conn.commit()
    conn.close()

    summary = human_quick_summary(db_path)
    assert summary["matches"] == 1
    assert summary["kd"] == 3 / 2
    assert summary["adr"] == 500 / 5


def test_summary_ignores_uncounted_rounds(tmp_path):
    db_path = tmp_path / "cs2_tracker.db"
    init_db(str(db_path))
    conn = sqlite3.connect(db_path)
    _insert_match(conn, 1, "m1")
    _insert_round(conn, 1, 1, counted=1)
    _insert_round(conn, 1, 2, counted=0)  # warmup/descartado
    _insert_damage(conn, 1, 1, dmg_health=100)
    _insert_damage(conn, 1, 2, dmg_health=999)  # não deve contar
    conn.commit()
    conn.close()

    summary = human_quick_summary(db_path)
    assert summary["adr"] == 100 / 1


def test_summary_ignores_non_human_kills_and_damage(tmp_path):
    db_path = tmp_path / "cs2_tracker.db"
    init_db(str(db_path))
    conn = sqlite3.connect(db_path)
    _insert_match(conn, 1, "m1")
    _insert_round(conn, 1, 1, counted=1)
    _insert_kill(conn, 1, 1, attacker_is_human=0, victim_is_human=0)  # bot vs bot
    _insert_damage(conn, 1, 1, dmg_health=200, attacker_is_human=0)  # bot batendo em alguém
    conn.commit()
    conn.close()

    summary = human_quick_summary(db_path)
    assert summary["kd"] is None
    assert summary["adr"] is None


def test_summary_counts_matches_even_without_kills(tmp_path):
    """Uma partida sem nenhum abate do humano ainda conta como partida
    jogada — só o kd/adr é que ficam None."""
    db_path = tmp_path / "cs2_tracker.db"
    init_db(str(db_path))
    conn = sqlite3.connect(db_path)
    _insert_match(conn, 1, "m1")
    conn.commit()
    conn.close()

    summary = human_quick_summary(db_path)
    assert summary["matches"] == 1
    assert summary["adr"] is None
    assert summary["kd"] is None
