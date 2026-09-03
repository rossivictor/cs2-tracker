#!/usr/bin/env python3
"""
CS2 Tracker — Parser
=====================
Converte um .dem (gravado pelo watcher.py via GOTV) em dados estruturados
usando awpy, e grava tudo num SQLite: rounds, kills, dano e a posição
(só do jogador humano, filtrado por nome — não guarda tick de bot).

Requer Python <3.14 (awpy 2.x exige >=3.11,<3.14) — rode a partir do
.venv do projeto, não do Python do sistema.

TODO: economia/compra fica de fora por ora — o awpy 2.0.2 não expõe um
dataframe de dinheiro gasto, só o evento `item_pickup` (sem valor
monetário). Revisitar se uma versão futura do awpy cobrir isso.

Uso standalone (reprocessar uma demo órfã, sem precisar do watcher):
    python parser.py <caminho.dem> --map de_mirage --score-ct 1 \\
                      --score-t 13 --minutes 19 --player can1sh \\
                      --db cs2_tracker.db
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import polars as pl
from awpy import Demo

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demo_name TEXT UNIQUE NOT NULL,
    map TEXT,
    played_at TEXT,
    score_ct INTEGER,
    score_t INTEGER,
    duration_minutes INTEGER,
    demo_path TEXT,
    player_name TEXT
);

CREATE TABLE IF NOT EXISTS rounds (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    winner_side TEXT,
    reason TEXT,
    bomb_plant INTEGER,
    bomb_site TEXT,
    start_tick INTEGER,
    end_tick INTEGER
);

CREATE TABLE IF NOT EXISTS kills (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    attacker_name TEXT,
    attacker_steamid TEXT,
    attacker_side TEXT,
    victim_name TEXT,
    victim_steamid TEXT,
    victim_side TEXT,
    weapon TEXT,
    headshot INTEGER,
    distance REAL,
    attacker_is_human INTEGER,
    victim_is_human INTEGER
);

CREATE TABLE IF NOT EXISTS damages (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    attacker_name TEXT,
    attacker_steamid TEXT,
    victim_name TEXT,
    victim_steamid TEXT,
    weapon TEXT,
    hitgroup TEXT,
    dmg_health INTEGER,
    dmg_armor INTEGER,
    attacker_is_human INTEGER,
    victim_is_human INTEGER
);

CREATE TABLE IF NOT EXISTS player_positions (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    x REAL,
    y REAL,
    z REAL,
    side TEXT,
    place TEXT,
    health INTEGER
);
"""


def _s(value):
    """Converte steamid pra string, preservando None (bots costumam vir sem steamid)."""
    return None if value is None else str(value)


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def parse_and_store(demo_path, meta, db_path, human_name):
    demo_path = Path(demo_path)
    demo_name = demo_path.stem

    conn = init_db(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM matches WHERE demo_name = ?", (demo_name,))
    existing = cur.fetchone()
    if existing:
        print(f"[PARSER] {demo_name} já está no banco (match_id={existing[0]}), pulando.")
        conn.close()
        return existing[0]

    print(f"[PARSER] Parseando {demo_path} ...")
    dem = Demo(str(demo_path))
    dem.parse()

    cur.execute(
        """INSERT INTO matches (demo_name, map, played_at, score_ct, score_t, duration_minutes, demo_path, player_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            demo_name,
            meta.get("map"),
            datetime.now().isoformat(timespec="seconds"),
            meta.get("score_ct"),
            meta.get("score_t"),
            meta.get("minutes"),
            str(demo_path),
            human_name,
        ),
    )
    match_id = cur.lastrowid

    rounds_rows = [
        (match_id, r["round_num"], r["winner"], r["reason"],
         int(bool(r["bomb_plant"])), r["bomb_site"], r["start"], r["end"])
        for r in dem.rounds.iter_rows(named=True)
    ]
    cur.executemany(
        """INSERT INTO rounds (match_id, round_num, winner_side, reason, bomb_plant, bomb_site, start_tick, end_tick)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        rounds_rows,
    )

    kills_rows = [
        (
            match_id, k["round_num"], k["tick"],
            k["attacker_name"], _s(k["attacker_steamid"]), k["attacker_side"],
            k["victim_name"], _s(k["victim_steamid"]), k["victim_side"],
            k["weapon"], int(bool(k["headshot"])), k["distance"],
            int(k["attacker_name"] == human_name), int(k["victim_name"] == human_name),
        )
        for k in dem.kills.iter_rows(named=True)
    ]
    cur.executemany(
        """INSERT INTO kills (match_id, round_num, tick, attacker_name, attacker_steamid, attacker_side,
                               victim_name, victim_steamid, victim_side, weapon, headshot, distance,
                               attacker_is_human, victim_is_human)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        kills_rows,
    )

    damages_rows = [
        (
            match_id, d["round_num"], d["tick"],
            d["attacker_name"], _s(d["attacker_steamid"]),
            d["victim_name"], _s(d["victim_steamid"]),
            d["weapon"], d["hitgroup"], d["dmg_health"], d["dmg_armor"],
            int(d["attacker_name"] == human_name), int(d["victim_name"] == human_name),
        )
        for d in dem.damages.iter_rows(named=True)
    ]
    cur.executemany(
        """INSERT INTO damages (match_id, round_num, tick, attacker_name, attacker_steamid,
                                 victim_name, victim_steamid, weapon, hitgroup, dmg_health, dmg_armor,
                                 attacker_is_human, victim_is_human)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        damages_rows,
    )

    human_ticks = dem.ticks.filter(pl.col("name") == human_name)
    positions_rows = [
        (match_id, t["round_num"], t["tick"], t["X"], t["Y"], t["Z"], t["side"], t["place"], t["health"])
        for t in human_ticks.iter_rows(named=True)
    ]
    cur.executemany(
        """INSERT INTO player_positions (match_id, round_num, tick, x, y, z, side, place, health)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        positions_rows,
    )

    conn.commit()
    conn.close()

    print(
        f"[PARSER] match_id={match_id}: {len(rounds_rows)} rounds, {len(kills_rows)} kills, "
        f"{len(damages_rows)} damages, {len(positions_rows)} posições de '{human_name}'"
    )
    return match_id


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Parser (awpy -> SQLite)")
    parser.add_argument("demo", help="Caminho do arquivo .dem")
    parser.add_argument("--map", required=True)
    parser.add_argument("--score-ct", required=True)
    parser.add_argument("--score-t", required=True)
    parser.add_argument("--minutes", required=True)
    parser.add_argument("--player", required=True, help="Nome do jogador humano (in-game)")
    parser.add_argument("--db", default="./cs2_tracker.db")
    args = parser.parse_args()

    meta = {
        "map": args.map,
        "score_ct": args.score_ct,
        "score_t": args.score_t,
        "minutes": args.minutes,
    }
    parse_and_store(args.demo, meta, args.db, args.player)


if __name__ == "__main__":
    main()
