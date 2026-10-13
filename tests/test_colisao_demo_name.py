#!/usr/bin/env python3
"""
Colisão de demo_name nunca descarta partida (card P1.1a).

O demo_name é a chave única de `matches` (parser.py, SCHEMA) e vem do nome do
arquivo arquivado: events_<matchid>_map<N>. Se o matchid da MatchZy se repete
(contador reiniciado, snapshot restaurado), o nome já existe. Antes, o watcher
via o arquivo antigo, não renomeava o current.jsonl e mandava ingerir o
ANTIGO; o parser respondia "já está no banco" e a partida nova se perdia no
truncamento do mapa seguinte.

Os testes passam pelo watcher de verdade (on_matchzy_map_finished) e pelo
parser de verdade, com banco e pasta de captura em tmp_path. Só o report e a
home viram fake. Os números esperados (rounds, vencedor) são os das partidas
escritas à mão abaixo, não recalculados pelo código.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import parser as parser_mod  # noqa: E402
import watcher  # noqa: E402
from identity import PlayerIdentity  # noqa: E402

HUMANO = "cobaia"
IDENT = PlayerIdentity(name=HUMANO, steamid="76561190000000001")
BOT = "Bot Kaiser"
CARIMBO = "20261013T150000Z"


def _round(num, vencedor):
    base = 1000 * num
    return [
        {"type": "round_start", "round_num": num, "tick": base, "human_side": "t"},
        {"type": "player_death", "round_num": num, "tick": base + 500,
         "attacker_name": HUMANO, "attacker_steamid": IDENT.steamid, "attacker_side": "t",
         "victim_name": BOT, "victim_steamid": None, "victim_side": "ct",
         "weapon": "ak47", "headshot": True, "distance": 500.0},
        {"type": "round_end", "round_num": num, "tick": base + 900,
         "winner": vencedor, "reason": "ct_killed" if vencedor == "t" else "t_killed"},
        {"type": "round_officially_ended", "round_num": num, "tick": base + 950},
    ]


# Duas partidas diferentes, para saber qual das duas foi ingerida.
PARTIDA_ANTIGA = _round(1, "t")                                   # 1 round
PARTIDA_NOVA = _round(1, "ct") + _round(2, "ct") + _round(3, "t")  # 3 rounds


def _escrever(caminho, eventos):
    caminho.write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")


def _watcher(tmp_path, monkeypatch):
    eventos = tmp_path / "events-live"
    eventos.mkdir()
    monkeypatch.setattr(watcher, "_carimbo_utc", lambda: CARIMBO)
    monkeypatch.setattr(watcher, "generate_report", lambda *a, **k: None)
    monkeypatch.setattr(watcher, "generate_home", lambda *a, **k: None)
    w = watcher.MatchWatcher(
        demo_dir=tmp_path / "demos", identity=IDENT, db_path=str(tmp_path / "t.db"),
        report_path=str(tmp_path / "report.html"), home_path=str(tmp_path / "home.html"),
        mode="matchzy", demos_live_dir=tmp_path / "demos-live",
        stats_live_dir=tmp_path / "stats-live", events_live_dir=eventos,
    )
    w._current_map = "de_mirage"
    return w


def _partidas(w):
    """[(demo_name, nº de rounds, demo_path só com o nome)], em ordem de id."""
    conn = sqlite3.connect(w.db_path)
    try:
        return [
            (nome, rounds, Path(caminho).name)
            for nome, rounds, caminho in conn.execute(
                "SELECT m.demo_name, (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.id),"
                " m.demo_path FROM matches m ORDER BY m.id"
            )
        ]
    finally:
        conn.close()


def _fim_de_mapa(w, eventos, matchid="45", mapa=0):
    _escrever(w.events_live_dir / "current.jsonl", eventos)
    w.on_matchzy_map_finished(matchid, mapa, None)


def test_partida_normal_e_ingerida_com_o_nome_sem_sufixo(tmp_path, monkeypatch):
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_NOVA)

    assert _partidas(w) == [("events_45_map0", 3, "events_45_map0.jsonl")]
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == ["events_45_map0.jsonl"]


def test_colisao_em_disco_arquiva_com_sufixo_utc_e_ingere_a_partida_nova(tmp_path, monkeypatch):
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_ANTIGA)
    antigo = (w.events_live_dir / "events_45_map0.jsonl").read_bytes()

    _fim_de_mapa(w, PARTIDA_NOVA)  # mesmo matchid, mesmo mapa

    assert _partidas(w) == [
        ("events_45_map0", 1, "events_45_map0.jsonl"),
        ("events_45_map0__20261013T150000Z", 3, "events_45_map0__20261013T150000Z.jsonl"),
    ]
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == [
        "events_45_map0.jsonl", "events_45_map0__20261013T150000Z.jsonl",
    ]
    # O arquivo antigo não é tocado.
    assert (w.events_live_dir / "events_45_map0.jsonl").read_bytes() == antigo


def test_colisao_no_mesmo_segundo_ganha_contador(tmp_path, monkeypatch):
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_ANTIGA)
    _fim_de_mapa(w, PARTIDA_NOVA)
    _fim_de_mapa(w, PARTIDA_ANTIGA + _round(2, "t"))  # 3ª vez, mesmo carimbo

    assert [(nome, rounds) for nome, rounds, _ in _partidas(w)] == [
        ("events_45_map0", 1),
        ("events_45_map0__20261013T150000Z", 3),
        ("events_45_map0__20261013T150000Z-2", 2),
    ]


def test_colisao_so_no_banco_tambem_ganha_sufixo(tmp_path, monkeypatch):
    # O arquivo antigo saiu da pasta, mas a linha dele continua em matches:
    # sem olhar o banco, o parser pularia a partida nova.
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_ANTIGA)
    (w.events_live_dir / "events_45_map0.jsonl").unlink()

    _fim_de_mapa(w, PARTIDA_NOVA)

    assert [(nome, rounds) for nome, rounds, _ in _partidas(w)] == [
        ("events_45_map0", 1),
        ("events_45_map0__20261013T150000Z", 3),
    ]


def test_sem_eventos_novos_reingere_o_arquivado_sem_criar_sufixo(tmp_path, monkeypatch):
    # current.jsonl vazio: não há partida nova para salvar. O comportamento de
    # antes fica (tenta o arquivado; já no banco, o parser pula).
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_ANTIGA)
    (w.events_live_dir / "current.jsonl").write_bytes(b"")

    w.on_matchzy_map_finished("45", 0, None)

    assert [(nome, rounds) for nome, rounds, _ in _partidas(w)] == [("events_45_map0", 1)]
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == [
        "current.jsonl", "events_45_map0.jsonl",
    ]


def test_demo_name_no_banco_so_le(tmp_path):
    db = tmp_path / "nao_existe.db"
    assert parser_mod.demo_name_no_banco(str(db), "events_1_map0") is False
    assert not db.exists()  # não cria banco

    vazio = tmp_path / "sem_tabela.db"
    sqlite3.connect(vazio).close()
    assert parser_mod.demo_name_no_banco(str(vazio), "events_1_map0") is False
