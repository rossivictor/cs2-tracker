#!/usr/bin/env python3
"""
Testes do tools/enrich_from_demos.py.

Não dá pra testar o caminho feliz com demo de verdade: as 39 demos em
docker/demos-live/ não parseiam (gravação da MatchZy sai com ~1,5s, sem
nenhum evento de combate). O que estes testes fixam é o que protege os
dados — que o importador nunca inventa partida, nunca casa demo com a
partida errada, e nunca escreve quando a numeração de round das duas fontes
diverge.
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import enrich_from_demos as enrich  # noqa: E402
from parser import init_db  # noqa: E402


def _db(tmp_path):
    path = tmp_path / "t.db"
    conn = init_db(str(path))
    conn.execute(
        """INSERT INTO matches (id, demo_name, map, played_at, player_name, source)
           VALUES (1,'events_44_map0','de_dust2','2026-09-19T12:00:00','can1sh','events')"""
    )
    conn.execute(
        """INSERT INTO matches (id, demo_name, map, played_at, player_name, source)
           VALUES (2,'events_44_map1','de_ancient','2026-09-19T12:30:00','can1sh','events')"""
    )
    conn.commit()
    conn.close()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------------------------------- #
# Nome do arquivo
# --------------------------------------------------------------------------- #

def test_le_matchid_e_mapa_do_nome():
    got = enrich._parse_demo_name(
        Path("2026-09-19_15-25-11_44_de_inferno_can1sh_vs_Bots.dem")
    )
    assert got == ("44", "de_inferno")


def test_nome_fora_do_padrao_e_ignorado():
    assert enrich._parse_demo_name(Path("qualquer_coisa.dem")) is None
    assert enrich._parse_demo_name(Path("20260902_211440_de_mirage.dem")) is None


# --------------------------------------------------------------------------- #
# Casamento com o banco — a guarda contra duplicar partida
# --------------------------------------------------------------------------- #

def test_casa_pelo_matchid_e_mapa(tmp_path):
    conn = _db(tmp_path)
    row = enrich._find_match(conn, "44", "de_dust2")
    assert row["id"] == 1
    assert row["demo_name"] == "events_44_map0"


def test_mesmo_matchid_mapa_diferente_casa_com_a_outra_partida(tmp_path):
    conn = _db(tmp_path)
    assert enrich._find_match(conn, "44", "de_ancient")["id"] == 2


def test_demo_sem_par_no_banco_nao_casa(tmp_path):
    conn = _db(tmp_path)
    # matchid que nunca foi ingerido — é o caso das 30 demos antigas.
    assert enrich._find_match(conn, "11", "de_mirage") is None
    # matchid existe, mas nesse mapa não há partida.
    assert enrich._find_match(conn, "44", "de_nuke") is None


# --------------------------------------------------------------------------- #
# Alinhamento de round — a guarda contra posição no round errado
# --------------------------------------------------------------------------- #

def _db_rounds(winners, counted=None):
    counted = counted or [1] * len(winners)
    return [
        {"round_num": i + 1, "winner_side": w, "counted": c}
        for i, (w, c) in enumerate(zip(winners, counted))
    ]


def _demo_rounds(winners):
    return [{"round_num": i + 1, "winner": w} for i, w in enumerate(winners)]


def test_alinha_quando_a_sequencia_de_vencedores_bate():
    ok, _ = enrich._rounds_align(_db_rounds(["t", "ct", "t"]), _demo_rounds(["t", "ct", "t"]))
    assert ok is True


def test_nao_alinha_com_quantidade_diferente():
    ok, why = enrich._rounds_align(_db_rounds(["t", "ct"]), _demo_rounds(["t", "ct", "t"]))
    assert ok is False
    assert "2 rounds no banco vs 3 na demo" in why


def test_nao_alinha_quando_o_vencedor_diverge():
    ok, why = enrich._rounds_align(_db_rounds(["t", "ct", "t"]), _demo_rounds(["t", "t", "t"]))
    assert ok is False
    assert "round 2" in why


def test_round_nao_contado_fica_fora_da_comparacao():
    # O round fantasma do rebalanceamento não existe na demo; ignorá-lo é o
    # que faz as duas sequências baterem.
    db = _db_rounds(["t", "ct", "t"], counted=[1, 0, 1])
    ok, _ = enrich._rounds_align(db, _demo_rounds(["t", "t"]))
    assert ok is True


def test_fonte_vazia_nao_alinha():
    assert enrich._rounds_align([], _demo_rounds(["t"]))[0] is False
    assert enrich._rounds_align(_db_rounds(["t"]), [])[0] is False


# --------------------------------------------------------------------------- #
# Nunca cria partida
# --------------------------------------------------------------------------- #

def test_demo_ilegivel_nao_escreve_nada(tmp_path):
    conn = _db(tmp_path)
    antes = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    fake = tmp_path / "2026-09-19_14-32-54_44_de_dust2_can1sh_vs_Bots.dem"
    fake.write_bytes(b"nao e uma demo")

    row = enrich._find_match(conn, "44", "de_dust2")
    ok, msg = enrich.enrich_one(conn, row, fake)

    assert ok is False
    assert "não parseia" in msg
    assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == antes
    assert conn.execute("SELECT COUNT(*) FROM player_positions").fetchone()[0] == 0


def test_o_importador_nao_tem_insert_em_matches():
    # Guarda de intenção: o arquivo inteiro não pode conter INSERT em
    # matches. Enriquecer é UPDATE de partida existente, nunca criação.
    fonte = (ROOT / "tools" / "enrich_from_demos.py").read_text(encoding="utf-8")
    assert "INSERT INTO matches" not in fonte
    assert "INSERT INTO kills" not in fonte
    assert "INSERT INTO damages" not in fonte
