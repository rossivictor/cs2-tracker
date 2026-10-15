#!/usr/bin/env python3
"""
tools/reingest_events.py reingere o arquivo sufixado da colisão (card P1.1b).

Numa colisão o watcher arquiva a partida nova como
events_<matchid>_map<N>__<utc>.jsonl (P1.1a). O NAME_RE antigo só casava
events_<matchid>_map<N>, e o arquivo sufixado não era reingerível. Banco e
pasta em tmp_path; os números esperados são os das partidas escritas à mão.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import reingest_events  # noqa: E402

HUMANO = "cobaia"


def _partida(rounds):
    eventos = []
    for num, vencedor in enumerate(rounds, start=1):
        base = 1000 * num
        eventos += [
            {"type": "round_start", "round_num": num, "tick": base, "human_side": "t"},
            {"type": "player_death", "round_num": num, "tick": base + 500,
             "attacker_name": HUMANO, "attacker_steamid": None, "attacker_side": "t",
             "victim_name": "Bot Kaiser", "victim_steamid": None, "victim_side": "ct",
             "weapon": "ak47", "headshot": True, "distance": 500.0},
            {"type": "round_end", "round_num": num, "tick": base + 900,
             "winner": vencedor, "reason": "ct_killed" if vencedor == "t" else "t_killed"},
        ]
    return eventos


def _escrever(pasta, nome, eventos):
    (pasta / nome).write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")


def test_reingere_o_arquivo_sufixado(tmp_path, monkeypatch, capsys):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_45_map0.jsonl", _partida(["t"]))
    _escrever(pasta, "events_45_map0__20261013T150000Z.jsonl", _partida(["ct", "ct", "t"]))
    _escrever(pasta, "events_45_map0__20261013T150000Z-2.jsonl", _partida(["t", "t"]))
    # Fora do padrão: nem órfão nem a cauda guardada sem round_end entram.
    _escrever(pasta, "orphan_20261013T150000Z.jsonl", _partida(["t"]))
    _escrever(pasta, "sem_round_end_events_45_map0__20261013T150001Z.jsonl", [])
    db = tmp_path / "t.db"
    monkeypatch.setattr(sys, "argv", ["reingest_events.py", "--db", str(db),
                                      "--events-dir", str(pasta), "--player", HUMANO])

    reingest_events.main()

    conn = sqlite3.connect(db)
    try:
        linhas = conn.execute(
            "SELECT m.demo_name, (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.id)"
            " FROM matches m ORDER BY m.demo_name").fetchall()
    finally:
        conn.close()
    assert linhas == [
        ("events_45_map0", 1),
        ("events_45_map0__20261013T150000Z", 3),
        ("events_45_map0__20261013T150000Z-2", 2),
    ]
    assert "[REINGEST] 3 arquivo(s)" in capsys.readouterr().out


def test_name_re_casa_so_o_sufixo_do_watcher():
    casa = reingest_events.NAME_RE.match
    assert casa("events_45_map0__20261013T150000Z")
    assert casa("events_45_map0__20261013T150000Z-12")
    assert not casa("events_45_map0__copia")
    assert not casa("events_45_map0__20261013T150000Z.bak")
