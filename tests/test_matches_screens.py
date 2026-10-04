#!/usr/bin/env python3
"""
Testes das duas telas de partidas (F6.1): matches.build_list_context,
matches.build_detail_context e as rotas /partidas e /partidas/<id>.

O que importa aqui não é o HTML, é o contrato do contexto: a coluna Δ só
aparece com histórico suficiente, a barra de mapa nunca passa de 100%, e
partida inexistente vira 404 em vez de estourar.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matches
from parser import init_db


def _db(tmp_path, n_matches=6, adrs=None):
    """Banco sintético com n partidas de 10 rounds, uma kill e um dano por
    round, com o dano controlado por `adrs` pra fixar o ADR de cada partida."""
    path = tmp_path / "t.db"
    conn = init_db(str(path))
    adrs = adrs or [100] * n_matches
    for i in range(n_matches):
        mid = i + 1
        conn.execute(
            """INSERT INTO matches (id, demo_name, map, played_at, player_name, source,
                                    score_mine, score_theirs, outcome)
               VALUES (?,?,?,?,'cobaia','events',13,5,'win')""",
            (mid, f"d{mid}.dem", "de_mirage", f"2026-09-{10 + i:02d}T20:00:00"),
        )
        for rnd in range(1, 11):
            conn.execute(
                """INSERT INTO rounds (match_id, round_num, winner_side, human_side, counted)
                   VALUES (?,?,'t','t',1)""",
                (mid, rnd),
            )
            conn.execute(
                """INSERT INTO kills (match_id, round_num, tick, attacker_name, victim_name,
                                      attacker_side, victim_side, weapon, headshot,
                                      attacker_is_human, victim_is_human)
                   VALUES (?,?,?,'cobaia','arT','t','ct','ak47',1,1,0)""",
                (mid, rnd, rnd * 100),
            )
            conn.execute(
                """INSERT INTO damages (match_id, round_num, weapon, hitgroup, dmg_health,
                                        attacker_is_human, victim_is_human)
                   VALUES (?,?,'ak47','head',?,1,0)""",
                (mid, rnd, adrs[i]),
            )
    conn.commit()
    conn.close()
    return str(path)


# --------------------------------------------------------------------------- #
# Lista
# --------------------------------------------------------------------------- #

def test_lista_vazia_nao_estoura(tmp_path):
    path = tmp_path / "vazio.db"
    init_db(str(path)).close()
    ctx = matches.build_list_context(str(path))
    assert ctx["has_matches"] is False
    assert ctx["rows"] == []
    assert ctx["kpis"] == []


def test_lista_traz_uma_linha_por_partida_mais_recente_primeiro(tmp_path):
    ctx = matches.build_list_context(_db(tmp_path, 3))
    assert [r["id"] for r in ctx["rows"]] == [3, 2, 1]


def test_delta_so_aparece_com_historico_suficiente(tmp_path):
    # DELTA_MIN_HISTORY=3: as três primeiras partidas não têm base.
    ctx = matches.build_list_context(_db(tmp_path, 6))
    by_id = {r["id"]: r for r in ctx["rows"]}
    assert by_id[1]["delta"] is None
    assert by_id[2]["delta"] is None
    assert by_id[3]["delta"] is None
    assert by_id[4]["delta"] is not None


def test_delta_e_a_diferenca_contra_a_media_anterior(tmp_path):
    # 3 partidas a 100 de dano/round e a quarta a 200: ADR 100 vs média 100.
    ctx = matches.build_list_context(_db(tmp_path, 4, adrs=[100, 100, 100, 200]))
    by_id = {r["id"]: r for r in ctx["rows"]}
    assert by_id[4]["adr"] == 200.0
    assert by_id[4]["delta"] == 100.0


def test_barra_do_mapa_nunca_passa_de_cem(tmp_path):
    ctx = matches.build_list_context(_db(tmp_path, 4))
    for card in ctx["map_cards"]:
        for key in ("adr_bar", "ct_bar", "t_bar"):
            assert 0 <= card[key] <= 100, (card["map"]["label"], key, card[key])


def test_filtro_de_mapa_invalido_e_ignorado(tmp_path):
    ctx = matches.build_list_context(_db(tmp_path, 3), map_filter="de_inexistente")
    assert ctx["map_filter"] is None
    assert len(ctx["rows"]) == 3


def test_lado_invalido_cai_para_geral(tmp_path):
    ctx = matches.build_list_context(_db(tmp_path, 3), side="xxx")
    assert ctx["side"] == "all"


def test_percentuais_saem_inteiros(tmp_path):
    ctx = matches.build_list_context(_db(tmp_path, 4))
    row = ctx["rows"][0]
    assert isinstance(row["kast_pct"], int)
    assert isinstance(row["hs_pct"], int)
    assert isinstance(ctx["map_cards"][0]["win_pct"], int)


def test_forma_recente_conta_vitorias(tmp_path):
    ctx = matches.build_list_context(_db(tmp_path, 4))
    assert ctx["recent"]["wins"] == 4
    assert ctx["recent"]["losses"] == 0


# --------------------------------------------------------------------------- #
# Detalhe
# --------------------------------------------------------------------------- #

def test_detalhe_de_partida_inexistente_e_none(tmp_path):
    assert matches.build_detail_context(_db(tmp_path, 2), 999) is None


def test_detalhe_compara_com_a_media_das_outras(tmp_path):
    # Partida 4 com o dobro do dano das outras três.
    ctx = matches.build_detail_context(_db(tmp_path, 4, adrs=[100, 100, 100, 200]), 4)
    adr = ctx["comparison"]["adr"]
    assert adr["value"] == 200.0
    assert adr["baseline"] == 100.0
    assert adr["delta"] == 100.0
    assert adr["samples"] == 3


def test_detalhe_sem_posicao_nao_mostra_radar(tmp_path):
    # Banco sintético não popula player_positions: a aba do mapa some em vez
    # de desenhar tudo na origem.
    ctx = matches.build_detail_context(_db(tmp_path, 2), 1)
    assert ctx["radar"] is None


def test_detalhe_traz_timeline_com_placar_corrente(tmp_path):
    ctx = matches.build_detail_context(_db(tmp_path, 2), 1)
    rounds = ctx["rounds"]
    assert len(rounds) == 10
    assert rounds[0]["score_mine"] == 1
    assert rounds[-1]["score_mine"] == 10


def test_detalhe_junta_armas_silenciadas_no_rotulo(tmp_path):
    path = _db(tmp_path, 1)
    conn = sqlite3.connect(path)
    # A demo grava a morte como m4a1_silencer e o dano como m4a1.
    conn.execute(
        """INSERT INTO kills (match_id, round_num, tick, attacker_name, victim_name,
                              attacker_side, victim_side, weapon, headshot,
                              attacker_is_human, victim_is_human)
           VALUES (1,1,50,'cobaia','arT','t','ct','m4a1_silencer',0,1,0)"""
    )
    conn.execute(
        """INSERT INTO damages (match_id, round_num, weapon, hitgroup, dmg_health,
                                attacker_is_human, victim_is_human)
           VALUES (1,1,'m4a1','chest',90,1,0)"""
    )
    conn.commit()
    conn.close()

    ctx = matches.build_detail_context(path, 1)
    row = next(w for w in ctx["weapons"] if w["weapon"] == "m4a1")
    assert row["label"] == "M4A4 / M4A1-S"
    assert row["kills"] == 1
    assert row["dmg"] == 90  # sem a reconciliação isso seria 0


def test_detalhe_de_lado_nao_jogado_vem_sem_stats(tmp_path):
    # Todas as partidas sintéticas são de TR: o recorte CT fica vazio.
    ctx = matches.build_detail_context(_db(tmp_path, 2), 1, side="ct")
    assert ctx["stats"] is None


# --------------------------------------------------------------------------- #
# Rotas
# --------------------------------------------------------------------------- #

@pytest.fixture
def client(tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    db = _db(tmp_path, 6)
    import web.app as app_module

    monkeypatch.setattr(app_module, "DB_PATH", db)
    return TestClient(app_module.app)


def test_rota_lista_responde(client):
    r = client.get("/partidas")
    assert r.status_code == 200
    assert "Minhas partidas" in r.text


def test_rota_lista_aceita_filtros(client):
    assert client.get("/partidas?lado=t").status_code == 200
    assert client.get("/partidas?lado=ct&mapa=de_mirage").status_code == 200


def test_rota_detalhe_responde(client):
    r = client.get("/partidas/1")
    assert r.status_code == 200
    assert "Mirage" in r.text


def test_rota_detalhe_inexistente_e_404(client):
    assert client.get("/partidas/999").status_code == 404


def test_relatorio_antigo_continua_de_pe(client):
    # A tela nova não aposenta report.py: ele é o único caminho que funciona
    # offline (report.html estático via file://).
    assert client.get("/report").status_code == 200
