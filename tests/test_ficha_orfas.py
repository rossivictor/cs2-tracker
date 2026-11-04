#!/usr/bin/env python3
"""
tools/ficha_orfas.py: a ficha das órfãs feita só em cópias (card V1.2).

Critério: mapa, placar, lado, data e K/D feitos em cópia; o hash do banco
não muda. Banco e pastas em tmp_path, SteamID fictícia abaixo da base. Os
números esperados são contados à mão: nas partidas escritas aqui e na
fixture anonimizada events_60_map0 (cabeça da partida 60, T1.3).
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import ficha_orfas  # noqa: E402
from parser import init_db  # noqa: E402

HUMANO = "Jogador"
STEAMID = "76561190000000001"
FIXTURE_60 = ROOT / "tests" / "fixtures" / "logs" / "eventos" / "events_60_map0.jsonl"


def _round(num, vencedor, lado, humano_mata, lugar=None):
    """Um round com uma morte: o humano mata um bot (humano_mata) ou um bot
    mata o humano. `lugar` vira um snapshot do humano com esse callout."""
    base = 1000 * num
    humano = {"name": HUMANO, "steamid": STEAMID, "side": lado}
    bot = {"name": "Bot Kaiser", "steamid": None, "side": "ct" if lado == "t" else "t"}
    matador, vitima = (humano, bot) if humano_mata else (bot, humano)
    eventos = [{"type": "round_start", "round_num": num, "tick": base, "human_side": lado}]
    if lugar:
        eventos.append({"type": "snapshot", "round_num": num, "tick": base + 10, "players": [
            {"n": HUMANO, "b": False, "s": lado, "x": 1, "y": 1, "z": 1, "h": 100, "p_": lugar}]})
    eventos += [
        {"type": "player_death", "round_num": num, "tick": base + 500,
         "attacker_name": matador["name"], "attacker_steamid": matador["steamid"],
         "attacker_side": matador["side"], "victim_name": vitima["name"],
         "victim_steamid": vitima["steamid"], "victim_side": vitima["side"],
         "weapon": "ak47", "headshot": False, "distance": 300.0},
        {"type": "round_end", "round_num": num, "tick": base + 900, "winner": vencedor,
         "reason": "x"},
    ]
    return eventos


def _partida(vitorias_humanas, total, lugar=None):
    """MR12: humano T nos rounds 1-12 e CT depois. Ele vence os rounds de
    vitorias_humanas (e mata nelas) e perde os outros (e morre neles)."""
    eventos = []
    for num in range(1, total + 1):
        lado = "t" if num <= 12 else "ct"
        ganhou = num in vitorias_humanas
        vencedor = lado if ganhou else ("ct" if lado == "t" else "t")
        eventos += _round(num, vencedor, lado, ganhou, lugar)
    return eventos


def _escrever(pasta, nome, eventos):
    caminho = pasta / nome
    caminho.write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")
    return caminho


def _banco(caminho, ingeridas=(("events_49_map0", "de_nuke", "2026-09-21T16:00:00"),
                               ("events_51_map0", "de_mirage", "2026-09-21T21:00:00"))):
    """Cópia de banco com partidas já ingeridas, a kill do humano que dá a
    SteamID e os callouts de cada mapa (Heaven só na Nuke, Palace só na
    Mirage, CTSpawn nas duas)."""
    init_db(caminho).close()
    conn = sqlite3.connect(caminho)
    callouts = {"de_nuke": ["Heaven", "CTSpawn"], "de_mirage": ["PalaceInterior", "CTSpawn"]}
    for nome, mapa, quando in ingeridas:
        cur = conn.execute(
            "INSERT INTO matches (demo_name, map, played_at, player_name, source)"
            " VALUES (?, ?, ?, ?, 'events')", (nome, mapa, quando, HUMANO))
        mid = cur.lastrowid
        conn.execute(
            "INSERT INTO kills (match_id, round_num, tick, attacker_name, attacker_steamid,"
            " victim_name, attacker_is_human, victim_is_human) VALUES (?, 1, 1, ?, ?, 'bot', 1, 0)",
            (mid, HUMANO, STEAMID))
        for lugar in callouts.get(mapa, []):
            conn.execute(
                "INSERT INTO player_positions (match_id, round_num, tick, place, player_name,"
                " is_human) VALUES (?, 1, 1, ?, ?, 1)", (mid, lugar, HUMANO))
    conn.commit()
    conn.close()
    return caminho


@pytest.fixture
def copia(tmp_path):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    return tmp_path, pasta, _banco(tmp_path / "copia.db")


def _rodar(db, pasta, *extra, saida=None):
    saida = saida or db.parent / "ficha.md"
    codigo = ficha_orfas.main(["--db", str(db), "--events-dir", str(pasta),
                               "--saida", str(saida), *extra])
    return codigo, saida.read_text(encoding="utf-8")


def _secao(texto, arquivo):
    inicio = texto.index(f"## {arquivo}")
    fim = texto.find("\n## ", inicio + 1)
    return texto[inicio:fim if fim != -1 else None]


def test_so_a_orfa_ganha_ficha_e_a_ingerida_fica_listada(copia):
    _, pasta, db = copia
    _escrever(pasta, "events_49_map0.jsonl", _partida({1}, 2))
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 2))
    _escrever(pasta, "current.jsonl", _partida({1}, 1))

    codigo, texto = _rodar(db, pasta)

    assert codigo == 0
    assert "## events_50_map0.jsonl" in texto
    assert "## events_49_map0.jsonl" not in texto
    assert "## current.jsonl" not in texto
    assert "1 órfã(s); 1 arquivo(s) já no banco; ignorados: current.jsonl." in texto
    assert texto.rstrip().endswith("events_49_map0")


def test_partida_completa_placar_lado_kd_e_data(copia):
    _, pasta, db = copia
    # Vence 1-9 e 13-16 (13 rounds), perde 10, 11, 12, 17 e 18: 13 x 5.
    vitorias = set(range(1, 10)) | {13, 14, 15, 16}
    _escrever(pasta, "events_50_map0.jsonl", _partida(vitorias, 18, lugar="Heaven"))

    _, texto = _rodar(db, pasta)
    ficha = _secao(texto, "events_50_map0.jsonl")

    assert ("| placar | humano 13 x 5 adversário (vitória); por lado CT 7 : TR 11; "
            "fonte rounds |") in ficha
    assert "| situação | completo |" in ficha
    assert "| lado do humano | inicial T; T nos rounds 1-12, CT nos rounds 13-18 (numeração dos rounds contados) |" in ficha
    assert "| K/D do humano | 13/5 = 2.60;" in ficha
    assert "| rounds | 18 no arquivo, 18 contados |" in ficha
    assert "de_nuke (inferido pelos callouts: 18 amostras" in ficha
    assert "casa o padrão events_<matchid>_map<N>" in ficha
    # A data: mtime e as vizinhas do banco, porque o .jsonl não tem relógio.
    assert "último evento gravado (mtime)" in ficha
    assert "no banco, antes:" in ficha


def test_fixture_real_kd_sem_pos_morte_e_round_abortado(copia):
    _, pasta, db = copia
    shutil.copy2(FIXTURE_60, pasta / FIXTURE_60.name)

    _, texto = _rodar(db, pasta)
    ficha = _secao(texto, "events_60_map0.jsonl")

    # Round 1 sem round_end; round 3: o humano (T) mata Godypmu, morre para
    # PepperZap e as duas kills seguintes são dele controlando um bot.
    assert "| rounds | 2 no arquivo, 1 contados; abortados (sem round_end): [1] |" in ficha
    assert "| placar | humano 1 x 0 adversário (vitória);" in ficha
    assert "| K/D do humano | 1/1 = 1.00;" in ficha
    assert "| lado do humano | inicial T; T no round 1 (numeração dos rounds contados) |" in ficha
    assert "PARCIAL: placar não fecha o mapa (1 x 0)" in ficha


def test_parcial_e_sinalizado_sem_quebrar(copia):
    _, pasta, db = copia
    eventos = _partida({1, 2}, 3)
    eventos.append({"type": "round_start", "round_num": 4, "tick": 4000, "human_side": "t"})
    _escrever(pasta, "events_50_map0.jsonl", eventos)

    codigo, texto = _rodar(db, pasta)
    ficha = _secao(texto, "events_50_map0.jsonl")

    assert codigo == 0
    assert "PARCIAL: placar não fecha o mapa (2 x 1): partida interrompida" in ficha
    assert "| rounds | 4 no arquivo, 3 contados; abortados (sem round_end): [4] |" in ficha
    assert "| K/D do humano | 2/1 = 2.00;" in ficha


def test_fora_do_padrao_ganha_ficha_e_o_original_nao_muda(copia):
    _, pasta, db = copia
    orfao = _escrever(pasta, "orphan_20261028T004916Z.jsonl", _partida({1}, 2))
    avulso = _escrever(pasta, "partida_23set.jsonl", _partida({1}, 2))
    antes = {p: (p.read_bytes(), p.stat().st_mtime) for p in (orfao, avulso)}

    _, texto = _rodar(db, pasta)

    assert "orphan_<utc> do start_match: não casa o padrão" in _secao(texto, orfao.name)
    assert "carimbo do nome 20261028T004916Z UTC" in _secao(texto, orfao.name)
    assert "não casa o padrão do reingest_events nem o orphan_<utc>" in _secao(texto, avulso.name)
    assert {p: (p.read_bytes(), p.stat().st_mtime) for p in (orfao, avulso)} == antes


def test_cauda_sem_round_start_e_partida_so_de_bots(copia):
    _, pasta, db = copia
    cauda = [{"type": "snapshot", "round_num": 17, "tick": 10, "players": [
        {"n": HUMANO, "b": False, "s": "ct", "h": 100, "p_": "Heaven"}]}]
    bots = _partida({1}, 2)
    for e in bots:   # tira o humano: só bots, como no smoke da janela
        for chave in ("attacker", "victim"):
            if e.get(f"{chave}_steamid") == STEAMID:
                e[f"{chave}_name"], e[f"{chave}_steamid"] = "Bot Zeca", None
    _escrever(pasta, "orphan_20261015T164958Z.jsonl", cauda)
    _escrever(pasta, "orphan_20261104T205651Z.jsonl", bots)

    _, texto = _rodar(db, pasta)

    assert "sem round_start: cauda" in _secao(texto, "orphan_20261015T164958Z.jsonl")
    assert "de_nuke (inferido" in _secao(texto, "orphan_20261015T164958Z.jsonl")
    so_bots = _secao(texto, "orphan_20261104T205651Z.jsonl")
    assert "o humano não aparece nos eventos" in so_bots
    assert "| humano nos eventos | não |" in so_bots


def test_mapa_desconhecido_sem_callout_exclusivo(copia):
    _, pasta, db = copia
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 1, lugar="CTSpawn"))

    _, texto = _rodar(db, pasta)

    assert "| mapa | desconhecido (nenhum callout exclusivo" in texto


def test_hash_do_banco_nao_muda_e_vai_na_ficha(copia):
    _, pasta, db = copia
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 2))
    antes = ficha_orfas.sha256_de(db)

    codigo, texto = _rodar(db, pasta)

    assert codigo == 0
    assert ficha_orfas.sha256_de(db) == antes
    assert f"sha256 antes: `{antes}`" in texto
    assert f"sha256 depois: `{antes}`" in texto
    assert "  - inalterado" in texto
    assert sorted(p.name for p in db.parent.iterdir()) == ["copia.db", "events-live", "ficha.md"]


def test_hash_que_muda_da_erro(copia, monkeypatch):
    _, pasta, db = copia
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 2))
    valores = iter(["a" * 64, "b" * 64])
    original = ficha_orfas.sha256_de
    monkeypatch.setattr(ficha_orfas, "sha256_de",
                        lambda p: next(valores) if Path(p) == db else original(p))

    codigo, texto = _rodar(db, pasta)

    assert codigo == 1
    assert "  - MUDOU" in texto


def test_banco_real_sem_confirmacao_recusa(tmp_path):
    pasta = tmp_path / "events-live"
    pasta.mkdir()
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 2))
    real = _banco(tmp_path / "cs2_tracker.db")

    with pytest.raises(SystemExit, match="--confirmo-banco-real"):
        _rodar(real, pasta)
    assert not (tmp_path / "ficha.md").exists()

    codigo, _ = _rodar(real, pasta, "--confirmo-banco-real")
    assert codigo == 0


def test_saida_dentro_do_repo_recusa(copia):
    _, pasta, db = copia
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 2))
    dentro = ROOT / "tests" / "ficha_orfas_nao_deve_existir.md"

    with pytest.raises(SystemExit, match="repositório git"):
        ficha_orfas.main(["--db", str(db), "--events-dir", str(pasta), "--saida", str(dentro)])
    assert not dentro.exists()


def test_steamid_vem_do_banco_e_a_ficha_so_mostra_o_fim(copia):
    _, pasta, db = copia
    _escrever(pasta, "events_50_map0.jsonl", _partida({1}, 2))

    _, texto = _rodar(db, pasta)

    assert "Humano: Jogador, SteamID terminada em 0001 (fonte: kills.attacker_is_human" in texto
    assert STEAMID not in texto


def test_steamid_invalida_recusa(copia):
    _, pasta, db = copia
    with pytest.raises(SystemExit, match="SteamID64"):
        _rodar(db, pasta, "--steamid", "123")


@pytest.mark.parametrize("placar, fechado", [
    ((13, 11), True), ((5, 13), True), ((13, 12), False), ((12, 12), False),
    ((16, 14), True), ((15, 13), False), ((14, 16), True), ((19, 15), True),
    ((18, 16), False), ((8, 4), False),
])
def test_placar_fechado_mr12_com_prorrogacao(placar, fechado):
    assert ficha_orfas.placar_fechado(*placar) is fechado
