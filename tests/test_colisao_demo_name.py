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


def test_partida_normal_e_ingerida_com_o_nome_sem_sufixo(tmp_path, monkeypatch, capsys):
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_NOVA)

    assert _partidas(w) == [("events_45_map0", 3, "events_45_map0.jsonl")]
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == ["events_45_map0.jsonl"]
    # P1.1b: a partida normal não ganha aviso nem a linha de colisão.
    saida = capsys.readouterr().out
    assert "[AVISO]" not in saida and "já existe" not in saida


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


def test_demo_name_no_banco_abre_em_mode_ro(tmp_path, monkeypatch):
    # P1.1b (nota do card): a pergunta do watcher não pode escrever no banco.
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE matches (demo_name TEXT)")
    conn.execute("INSERT INTO matches VALUES ('events_1_map0')")
    conn.commit()
    conn.close()
    aberturas = []
    conectar = parser_mod.sqlite3.connect

    def _espiao(database, *args, **kwargs):
        aberturas.append((str(database), kwargs.get("uri")))
        return conectar(database, *args, **kwargs)

    monkeypatch.setattr(parser_mod.sqlite3, "connect", _espiao)
    assert parser_mod.demo_name_no_banco(str(db), "events_1_map0") is True
    [(database, uri)] = aberturas
    assert database.startswith("file:") and database.endswith("?mode=ro") and uri is True


# --------------------------------------------------------------------------- #
# P1.1b: linha fantasma e arquivo antigo fora do banco
# --------------------------------------------------------------------------- #

# Cauda real de um current.jsonl depois do arquivamento (44 snapshot, 1
# round_stats, 1 round_officially_ended; nenhum round_end): é o que o
# current.jsonl recriado tem quando o fim do mesmo mapa chega duas vezes.
CAUDA_REAL = ROOT / "tests" / "fixtures" / "captura" / "current.jsonl"


def test_fim_repetido_so_com_cauda_nao_cria_linha_fantasma(tmp_path, monkeypatch, capsys):
    # A reprodução do QA do P1.1a: o mapa termina, é arquivado e ingerido;
    # o fim chega de novo com o current.jsonl recriado só com a cauda.
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_NOVA)
    cauda = CAUDA_REAL.read_bytes()
    (w.events_live_dir / "current.jsonl").write_bytes(cauda)
    capsys.readouterr()

    w.on_matchzy_map_finished("45", 0, None)

    # Sem linha sufixada de 0 rounds: só a partida de verdade.
    assert _partidas(w) == [("events_45_map0", 3, "events_45_map0.jsonl")]
    # O arquivo é guardado fora do padrão events_*, com o conteúdo intacto.
    guardado = w.events_live_dir / "sem_round_end_events_45_map0__20261013T150000Z.jsonl"
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == [
        "events_45_map0.jsonl", "sem_round_end_events_45_map0__20261013T150000Z.jsonl",
    ]
    assert guardado.read_bytes() == cauda
    saida = capsys.readouterr().out
    assert ("[AVISO] events_45_map0 já existe e o current.jsonl novo não tem round_end: "
            "guardado como sem_round_end_events_45_map0__20261013T150000Z.jsonl, "
            "sem linha no banco") in saida


def test_fim_repetido_duas_vezes_no_mesmo_segundo_nao_sobrescreve(tmp_path, monkeypatch):
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_NOVA)
    for _ in range(2):
        (w.events_live_dir / "current.jsonl").write_bytes(CAUDA_REAL.read_bytes())
        w.on_matchzy_map_finished("45", 0, None)

    assert [nome for nome, _, _ in _partidas(w)] == ["events_45_map0"]
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == [
        "events_45_map0.jsonl",
        "sem_round_end_events_45_map0__20261013T150000Z-2.jsonl",
        "sem_round_end_events_45_map0__20261013T150000Z.jsonl",
    ]


def test_colisao_com_arquivo_antigo_fora_do_banco_avisa(tmp_path, monkeypatch, capsys):
    # O events_45_map0.jsonl antigo nunca foi ingerido (watcher caído, por
    # exemplo). A partida nova entra sufixada e o log avisa do antigo.
    w = _watcher(tmp_path, monkeypatch)
    _escrever(w.events_live_dir / "events_45_map0.jsonl", PARTIDA_ANTIGA)

    _fim_de_mapa(w, PARTIDA_NOVA)

    assert _partidas(w) == [
        ("events_45_map0__20261013T150000Z", 3, "events_45_map0__20261013T150000Z.jsonl"),
    ]
    saida = capsys.readouterr().out
    assert ("[AVISO] events_45_map0.jsonl já existia e não está no banco: essa partida "
            "antiga segue fora das estatísticas (tools/reingest_events.py)") in saida


def test_colisao_com_antigo_no_banco_nao_avisa_do_antigo(tmp_path, monkeypatch, capsys):
    w = _watcher(tmp_path, monkeypatch)
    _fim_de_mapa(w, PARTIDA_ANTIGA)
    capsys.readouterr()

    _fim_de_mapa(w, PARTIDA_NOVA)

    assert "[AVISO]" not in capsys.readouterr().out
