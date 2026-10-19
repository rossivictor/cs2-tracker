#!/usr/bin/env python3
"""
Watcher isolado dos geradores (card P1.3).

O watcher é caminho de jogo; report, home e o stats que eles importam não
deveriam ser. Antes, `from report import ...` e `from home import ...` ficavam
no topo do watcher.py: um erro em qualquer um dos três impedia o watcher de
subir, e a partida não era ingerida. Agora os imports são tardios, dentro do
try, e só a regeneração das páginas falha.

Cada teste injeta um módulo quebrado em sys.modules, importa o watcher do zero
e passa um fim de mapa pelas linhas de log da MatchZy (handle_matchzy_line),
com o parser de verdade e banco em tmp_path. O gabarito (2 rounds, nome do
arquivo, mapa) é o da partida escrita à mão abaixo.
"""
import importlib
import json
import sqlite3
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity import PlayerIdentity  # noqa: E402

HUMANO = "cobaia"
IDENT = PlayerIdentity(name=HUMANO, steamid="76561190000000001")
BOT = "Bot Kaiser"


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


PARTIDA = _round(1, "t") + _round(2, "ct")  # 2 rounds

# Fim de mapa como a MatchZy escreve no log do container.
LINHAS_FIM_DE_MAPA = [
    "[ChangeMap] Changing map to de_mirage",
    "[HandleMatchEnd] MAP ENDED, matchid: 7 currentMapNumber: 0",
    "[SetMatchEndData] Data updated for matchId: 7 winnerName: team_cobaia",
    "[WritePlayerStatsToCsv] Match stats for ID: 7 written successfully at: "
    "/opt/stats/7/match_data_map0_7.csv",
]


def _modulo_que_explode(nome, funcao):
    """Módulo importável cujo gerador quebra ao ser chamado."""
    mod = types.ModuleType(nome)

    def _explode(*_a, **_k):
        raise RuntimeError(f"{nome} quebrado de propósito")

    setattr(mod, funcao, _explode)
    return mod


def _watcher_do_zero(monkeypatch):
    """Importa o watcher.py de novo, com o sys.modules já sabotado. Com os
    imports no topo, é aqui que o watcher não subia."""
    monkeypatch.delitem(sys.modules, "watcher", raising=False)
    return importlib.import_module("watcher")


def _fim_de_mapa(mod, tmp_path):
    eventos = tmp_path / "events-live"
    eventos.mkdir()
    (eventos / "current.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in PARTIDA), encoding="utf-8")
    w = mod.MatchWatcher(
        demo_dir=tmp_path / "demos", identity=IDENT, db_path=str(tmp_path / "t.db"),
        report_path=str(tmp_path / "report.html"), home_path=str(tmp_path / "home.html"),
        mode="matchzy", demos_live_dir=tmp_path / "demos-live",
        stats_live_dir=tmp_path / "stats-live", events_live_dir=eventos,
    )
    for linha in LINHAS_FIM_DE_MAPA:
        w.handle_matchzy_line(linha)
    return w


def _partidas(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT m.demo_name, m.map, (SELECT COUNT(*) FROM rounds r WHERE r.match_id = m.id)"
            " FROM matches m ORDER BY m.id"
        ).fetchall()
    finally:
        conn.close()


def _sabotar_ausentes(monkeypatch):
    # None em sys.modules faz o `import` levantar ImportError.
    monkeypatch.setitem(sys.modules, "report", None)
    monkeypatch.setitem(sys.modules, "home", None)


def _sabotar_stats(monkeypatch):
    # O report.py e a home.py de verdade, reimportados, quebram no `from stats`.
    monkeypatch.setitem(sys.modules, "stats", None)
    monkeypatch.delitem(sys.modules, "report", raising=False)
    monkeypatch.delitem(sys.modules, "home", raising=False)


def _sabotar_geradores(monkeypatch):
    # Importam, mas o gerador explode na chamada.
    monkeypatch.setitem(sys.modules, "report", _modulo_que_explode("report", "generate_report"))
    monkeypatch.setitem(sys.modules, "home", _modulo_que_explode("home", "generate_home"))


@pytest.mark.parametrize("sabotar", [_sabotar_ausentes, _sabotar_stats, _sabotar_geradores],
                         ids=["report_e_home_ausentes", "stats_quebrado", "geradores_explodem"])
def test_watcher_sobe_e_ingere_com_modulo_quebrado(tmp_path, monkeypatch, capsys, sabotar):
    sabotar(monkeypatch)
    mod = _watcher_do_zero(monkeypatch)

    w = _fim_de_mapa(mod, tmp_path)

    assert _partidas(w.db_path) == [("events_7_map0", "de_mirage", 2)]
    assert sorted(p.name for p in w.events_live_dir.iterdir()) == ["events_7_map0.jsonl"]
    saida = capsys.readouterr().out
    assert "[AVISO] report.html não regenerado" in saida
    assert "[AVISO] home.html não regenerada" in saida
    assert not (tmp_path / "report.html").exists()
    assert not (tmp_path / "home.html").exists()


def test_report_quebrado_nao_impede_a_home(tmp_path, monkeypatch):
    chamadas = []
    home = types.ModuleType("home")
    home.generate_home = lambda db, destino: chamadas.append(Path(destino).name)
    monkeypatch.setitem(sys.modules, "report", _modulo_que_explode("report", "generate_report"))
    monkeypatch.setitem(sys.modules, "home", home)
    mod = _watcher_do_zero(monkeypatch)

    _fim_de_mapa(mod, tmp_path)

    assert chamadas == ["home.html"]


def test_imports_de_report_e_home_nao_ficam_no_topo():
    """O watcher.py não importa report, home nem stats fora de função (nem
    num try do topo, que roda na carga do módulo)."""
    import ast

    no_topo = set()

    def _visitar(no):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return
        if isinstance(no, ast.Import):
            no_topo.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            no_topo.add(no.module.split(".")[0])
        for filho in ast.iter_child_nodes(no):
            _visitar(filho)

    _visitar(ast.parse((ROOT / "watcher.py").read_text(encoding="utf-8")))
    assert "parser" in no_topo  # sanidade: o visitante enxerga o topo
    assert no_topo.isdisjoint({"report", "home", "stats"})
