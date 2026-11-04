#!/usr/bin/env python3
"""
tools/reingest_events.py: o arquivo sufixado da colisão (card P1.1b) e a
reingestão segura das órfãs (card V1.1).

Numa colisão o watcher arquiva a partida nova como
events_<matchid>_map<N>__<utc>.jsonl (P1.1a). O NAME_RE antigo só casava
events_<matchid>_map<N>, e o arquivo sufixado não era reingerível.

V1.1: a reingestão gravava series_num_maps=NULL (apagava o BO3/BO5), casava
o humano só pelo nick (o watcher casa por SteamID) e tinha o banco real como
default do --db. Banco e pasta em tmp_path; SteamID fictícia abaixo da base;
os números esperados são os das partidas escritas à mão.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import reingest_events  # noqa: E402

HUMANO = "cobaia"
STEAMID_HUMANO = "76561190000000001"


def _partida(rounds, atacantes=None):
    """Um kill por round. atacantes: lista de (nome, steamid) do matador de
    cada round; padrão, o humano com a SteamID fictícia."""
    atacantes = atacantes or [(HUMANO, STEAMID_HUMANO)] * len(rounds)
    eventos = []
    for num, (vencedor, (nome, steamid)) in enumerate(zip(rounds, atacantes), start=1):
        base = 1000 * num
        eventos += [
            {"type": "round_start", "round_num": num, "tick": base, "human_side": "t"},
            {"type": "player_death", "round_num": num, "tick": base + 500,
             "attacker_name": nome, "attacker_steamid": steamid, "attacker_side": "t",
             "victim_name": "Bot Kaiser", "victim_steamid": None, "victim_side": "ct",
             "weapon": "ak47", "headshot": True, "distance": 500.0},
            {"type": "round_end", "round_num": num, "tick": base + 900,
             "winner": vencedor, "reason": "ct_killed" if vencedor == "t" else "t_killed"},
        ]
    return eventos


def _escrever(pasta, nome, eventos):
    (pasta / nome).write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")


def _rodar(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["reingest_events.py", *args])
    reingest_events.main()


def _consulta(db, sql):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


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

    _rodar(monkeypatch, "--db", str(db), "--events-dir", str(pasta),
           "--player", HUMANO, "--steamid", STEAMID_HUMANO)

    assert _consulta(db,
        "SELECT m.demo_name, (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.id)"
        " FROM matches m ORDER BY m.demo_name") == [
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


def test_series_num_maps_entra_na_nova_e_sobrevive_a_reingestao(tmp_path, monkeypatch):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_50_map0.jsonl", _partida(["t", "ct"]))
    db = tmp_path / "copia.db"
    base = ["--db", str(db), "--events-dir", str(pasta),
            "--player", HUMANO, "--steamid", STEAMID_HUMANO]

    _rodar(monkeypatch, *base, "--series-num-maps", "3")
    assert _consulta(db, "SELECT demo_name, series_num_maps FROM matches") == [
        ("events_50_map0", 3)]

    # Segunda passada sem a flag: a partida já está no banco e mantém o BO3.
    _rodar(monkeypatch, *base)
    assert _consulta(db, "SELECT demo_name, series_num_maps FROM matches") == [
        ("events_50_map0", 3)]


def test_humano_por_steamid_e_nao_pelo_nick(tmp_path, monkeypatch):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    # Round 1: o humano com outro nick (trocou de nome) e a SteamID dele.
    # Round 2: um bot com o mesmo nick do humano e sem SteamID.
    _escrever(pasta, "events_50_map0.jsonl", _partida(
        ["t", "t"], atacantes=[("nick_novo", STEAMID_HUMANO), (HUMANO, None)]))
    db = tmp_path / "copia.db"

    _rodar(monkeypatch, "--db", str(db), "--events-dir", str(pasta),
           "--player", HUMANO, "--steamid", STEAMID_HUMANO)

    assert _consulta(db, "SELECT round_num, attacker_name, attacker_is_human FROM kills"
                         " ORDER BY round_num") == [(1, "nick_novo", 1), (2, HUMANO, 0)]
    assert _consulta(db, "SELECT player_name FROM matches") == [(HUMANO,)]


def test_player_steamid64_pega_o_nick_do_banco(tmp_path, monkeypatch):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_50_map0.jsonl", _partida(["t"]))
    db = tmp_path / "copia.db"
    base = ["--db", str(db), "--events-dir", str(pasta)]
    _rodar(monkeypatch, *base, "--player", HUMANO, "--steamid", STEAMID_HUMANO)

    # --player com a SteamID: o nick vem do player_name já gravado.
    _rodar(monkeypatch, *base, "--player", STEAMID_HUMANO)

    assert _consulta(db, "SELECT player_name FROM matches") == [(HUMANO,)]
    assert _consulta(db, "SELECT attacker_is_human FROM kills") == [(1,)]


def test_sem_steamid_recusa_sem_gravar_partida(tmp_path, monkeypatch):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_50_map0.jsonl", _partida(["t"]))
    db = tmp_path / "copia.db"

    with pytest.raises(SystemExit, match="SteamID"):
        _rodar(monkeypatch, "--db", str(db), "--events-dir", str(pasta), "--player", HUMANO)

    assert _consulta(db, "SELECT COUNT(*) FROM matches") == [(0,)]


def test_db_e_obrigatorio(tmp_path, monkeypatch, capsys):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_50_map0.jsonl", _partida(["t"]))

    with pytest.raises(SystemExit) as erro:
        _rodar(monkeypatch, "--events-dir", str(pasta), "--steamid", STEAMID_HUMANO)

    assert erro.value.code == 2
    assert "--db" in capsys.readouterr().err


def test_banco_real_sem_confirmacao_recusa_sem_criar(tmp_path, monkeypatch):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_50_map0.jsonl", _partida(["t"]))
    real = tmp_path / "cs2_tracker.db"
    base = ["--db", str(real), "--events-dir", str(pasta),
            "--player", HUMANO, "--steamid", STEAMID_HUMANO]

    with pytest.raises(SystemExit, match="--confirmo-banco-real"):
        _rodar(monkeypatch, *base, "--dry-run")
    assert not real.exists()

    _rodar(monkeypatch, *base, "--confirmo-banco-real")
    assert _consulta(real, "SELECT demo_name FROM matches") == [("events_50_map0",)]


def test_banco_real_pelo_env(tmp_path, monkeypatch):
    do_env = tmp_path / "meu_banco.db"
    monkeypatch.setattr(reingest_events.config, "load_env",
                        lambda path=None: {"CS2_TRACKER_DB_PATH": str(do_env)})

    assert reingest_events.eh_banco_real(do_env)
    assert reingest_events.eh_banco_real(tmp_path / "x" / "CS2_TRACKER.DB")
    assert not reingest_events.eh_banco_real(tmp_path / "copia.db")
