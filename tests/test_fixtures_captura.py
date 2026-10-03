#!/usr/bin/env python3
"""
Fixtures anonimizadas da captura (card T1.3); o que cada uma guarda está no
tools/anonimizar_fixtures.py, que as gera das cópias do backup. Gabarito
escrito à mão, contado nas fixtures fora do parser. Nada de processo, Docker,
rede ou banco real: o banco de cada teste nasce em tmp_path.
"""
import ipaddress
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "tools" / "hooks"))

import evidencia_partida as ep  # noqa: E402
import parser as parser_mod  # noqa: E402
import pii  # noqa: E402
import watcher  # noqa: E402
from identity import PlayerIdentity  # noqa: E402

FIX = RAIZ / "tests" / "fixtures" / "captura"
ARQUIVOS = ("events_44_map0.jsonl", "events_59_map0.jsonl", "current.jsonl", "serie_bo3.log")
HUMANO = PlayerIdentity(name="Jogador", steamid="76561190000000001")
# Quem aparece com SteamID64 em cada arquivo, depois da troca.
IDS_ESPERADOS = {
    "events_44_map0.jsonl": {"76561190000000001", "76561190000000002"},
    "events_59_map0.jsonl": {"76561190000000001"},
    "current.jsonl": set(),
    "serie_bo3.log": {"76561190000000001"},
}
BLOCOS_DE_DOCUMENTACAO = [ipaddress.ip_network(r) for r in
                          ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
_IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")


def _texto(nome):
    return (FIX / nome).read_text(encoding="utf-8")


def _eventos(nome):
    return [json.loads(l) for l in (FIX / nome).read_text(encoding="utf-8-sig").splitlines()]


def _ingerir(tmp_path, nome):
    db = tmp_path / "banco.sqlite"
    parser_mod.store_match_from_events(FIX / nome, {"map": "de_teste"}, str(db), HUMANO)
    conn = sqlite3.connect(db)
    try:
        def um(sql):
            return conn.execute(sql).fetchone()
        return {
            "contagens": {t: um(f"SELECT COUNT(*) FROM {t}")[0]
                          for t in ("rounds", "kills", "damages", "player_blinds")},
            "placar": um("SELECT score_mine, score_theirs, outcome FROM matches"),
            "round1": um("SELECT start_tick, human_side FROM rounds WHERE round_num = 1"),
            "kd": (um("SELECT COUNT(*) FROM kills WHERE attacker_is_human = 1 "
                      "AND victim_is_human = 0")[0],
                   um("SELECT COUNT(*) FROM kills WHERE victim_is_human = 1")[0]),
        }
    finally:
        conn.close()


# ------------------------------------------------------------ existência e forma

def test_as_quatro_fixtures_existem_e_sao_pequenas():
    for nome in ARQUIVOS:
        assert (FIX / nome).stat().st_size < 400_000, nome


def test_so_events_44_comeca_com_bom():
    assert (FIX / "events_44_map0.jsonl").read_bytes().startswith(b"\xef\xbb\xbf")
    assert (FIX / "events_44_map0.jsonl").read_bytes().count(b"\xef\xbb\xbf") == 1
    for nome in ARQUIVOS[1:]:
        assert not (FIX / nome).read_bytes().startswith(b"\xef\xbb\xbf"), nome


def test_events_59_reduzido_guarda_um_snapshot_por_round():
    tipos = [e["type"] for e in _eventos("events_59_map0.jsonl")]
    assert len(tipos) == 711
    assert tipos.count("snapshot") == 15
    assert (tipos[0], tipos[-1]) == ("round_start", "round_end")


def test_current_e_so_a_cauda_pos_partida():
    eventos = _eventos("current.jsonl")
    assert len(eventos) == 46
    assert {e["round_num"] for e in eventos} == {15}
    assert [e["type"] for e in eventos[-2:]] == ["round_stats", "round_officially_ended"]
    assert "round_start" not in {e["type"] for e in eventos}


# ------------------------------------------------------------ anonimização

@pytest.mark.parametrize("nome", ARQUIVOS)
def test_pii_verde(nome):
    assert pii.achar(_texto(nome)) == [], nome


@pytest.mark.parametrize("nome", ARQUIVOS)
def test_steamid64_so_os_ficticios(nome):
    achados = set(re.findall(r"(?<!\d)7656119\d{10}(?!\d)", _texto(nome)))
    assert achados == IDS_ESPERADOS[nome]
    assert all(int(i) < pii.BASE_STEAMID64 for i in achados)


@pytest.mark.parametrize("nome", ARQUIVOS)
def test_steamid3_e_ip_trocados(nome):
    texto = _texto(nome)
    assert set(re.findall(r"\[U:1:\d+\]", texto)) <= {"[U:1:0]"}
    for ip in _IPV4.findall(texto):
        endereco = ipaddress.ip_address(ip)
        assert ip in pii.IPS_LIBERADOS or any(endereco in b for b in BLOCOS_DE_DOCUMENTACAO), ip


def test_o_humano_e_jogador_em_todo_arquivo():
    for nome in ARQUIVOS[1:3]:
        humanos = {j.get("n") or j.get("name") for e in _eventos(nome)
                   for j in e.get("players") or [] if j.get("b", j.get("is_bot")) is False}
        assert humanos == {"Jogador"}, nome
    assert "Name: Jogador has connected!" in _texto("serie_bo3.log")


# ------------------------------------------------------------ o código atual lê

def test_parser_le_events_44_com_bom(tmp_path):
    lido = _ingerir(tmp_path, "events_44_map0.jsonl")
    assert lido["contagens"] == {"rounds": 22, "kills": 154, "damages": 650, "player_blinds": 0}
    # Sem o utf-8-sig, o BOM derruba a 1ª linha e o round 1 perde tique e lado.
    assert lido["round1"] == (7905, "ct")
    # 9 rounds ganhos em 22, menos o round 1 (82 tiques, reinício), que não conta.
    assert lido["placar"] == (8, 13, "loss")
    assert lido["kd"] == (28, 24)


def test_parser_le_events_59_reduzido(tmp_path):
    lido = _ingerir(tmp_path, "events_59_map0.jsonl")
    assert lido["contagens"] == {"rounds": 15, "kills": 103, "damages": 454, "player_blinds": 61}
    assert lido["round1"] == (4039, "ct")
    assert lido["placar"] == (13, 1, "win")
    assert lido["kd"] == (37, 4)


def test_serie_bo3_casa_com_os_padroes_do_watcher():
    linhas, formato = ep.ler_linhas(_texto("serie_bo3.log"))
    assert formato == "docker -t" and len(linhas) == 1194
    padroes = watcher.MATCHZY_PATTERNS
    conteudos = [c for _, _, c in linhas]
    fins = [m.groups() for c in conteudos if (m := padroes["map_ended"].search(c))]
    assert fins == [("45", "0"), ("45", "1"), ("45", "2")]
    mapas = [m.group("map") for c in conteudos if (m := padroes["change_map"].search(c))]
    assert mapas == ["de_nuke", "de_dust2", "de_ancient"]
    assert sum(1 for c in conteudos if padroes["stats_written"].search(c)) == 3
    assert sum(1 for c in conteudos if "remainingMaps: 0" in c) == 1
