#!/usr/bin/env python3
"""
Testes da etiqueta de série (BO3/BO5) e da descoberta do nome do mapa.

Os dois nasceram do mesmo episódio, em 22/09/2026: a info de série foi
adicionada junto com um `_current_map` lido do log, e o nome do mapa passou
a depender de um arquivo .dem que nem sempre existe — duas partidas entraram
no banco com map=NULL.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matches  # noqa: E402
import watcher  # noqa: E402


# --------------------------------------------------------------------------- #
# A etiqueta
# --------------------------------------------------------------------------- #

def test_bo1_nao_vira_etiqueta():
    # BO1 é o formato padrão: marcar toda partida com "BO1" é só ruído.
    assert matches._series_tag(1) == ""


def test_bo3_e_bo5_viram_etiqueta():
    assert matches._series_tag(3) == "BO3"
    assert matches._series_tag(5) == "BO5"


def test_serie_desconhecida_nao_vira_etiqueta():
    # Partidas ingeridas antes da coluna series_num_maps existir.
    assert matches._series_tag(None) == ""
    assert matches._series_tag(0) == ""


# --------------------------------------------------------------------------- #
# Nome do mapa — as três fontes, em ordem
# --------------------------------------------------------------------------- #

def _watcher(tmp_path, maplist=None, current_map=None, demos=()):
    demos_dir = tmp_path / "demos"
    demos_dir.mkdir(exist_ok=True)
    for nome in demos:
        (demos_dir / nome).write_bytes(b"x")

    config = tmp_path / "match_config.json"
    if maplist is not None:
        config.write_text(json.dumps({"num_maps": len(maplist), "maplist": maplist}),
                          encoding="utf-8")

    w = watcher.MatchWatcher.__new__(watcher.MatchWatcher)
    w._current_map = current_map
    w.match_config_path = config if maplist is not None else None
    w.demos_live_dir = demos_dir
    return w


def test_changemap_do_log_tem_prioridade(tmp_path):
    w = _watcher(tmp_path, maplist=["de_dust2"], current_map="de_nuke")
    assert w._map_name_for("52", 0) == "de_nuke"


def test_sem_changemap_usa_o_maplist_do_match_config(tmp_path):
    # É o caso do PRIMEIRO mapa de qualquer série: o wizard troca o mapa e só
    # depois sobe o watcher, que segue `docker logs -f --tail 0` — a linha
    # [ChangeMap] já passou quando ele começa a ler.
    w = _watcher(tmp_path, maplist=["de_nuke"], current_map=None)
    assert w._map_name_for("52", 0) == "de_nuke"


def test_maplist_respeita_o_indice_do_mapa_na_serie(tmp_path):
    w = _watcher(tmp_path, maplist=["de_dust2", "de_ancient", "de_inferno"])
    assert w._map_name_for("44", 0) == "de_dust2"
    assert w._map_name_for("44", 1) == "de_ancient"
    assert w._map_name_for("44", 2) == "de_inferno"


def test_sem_match_config_cai_pro_nome_da_demo(tmp_path):
    w = _watcher(tmp_path, maplist=None,
                 demos=("2026-09-22_21-05-25_52_de_nuke_cobaia_vs_Bots.dem",))
    assert w._map_name_for("52", 0) == "de_nuke"


def test_sem_nenhuma_fonte_devolve_none_em_vez_de_estourar(tmp_path):
    # Era exatamente este caminho que gravava map=NULL: sem [ChangeMap] e com
    # a demo atrasada pelo tv_delay, não sobrava fonte nenhuma.
    w = _watcher(tmp_path, maplist=None)
    assert w._map_name_for("52", 0) is None


def test_maplist_curto_nao_estoura_indice(tmp_path):
    # Série com 1 mapa mas o log diz map_number=2 (já aconteceu: série 45
    # tinha 2 demos pra 3 mapas).
    w = _watcher(tmp_path, maplist=["de_nuke"])
    assert w._map_name_for("45", 2) is None


def test_match_config_ilegivel_nao_derruba_a_ingestao(tmp_path):
    config = tmp_path / "match_config.json"
    config.write_text("{ isto nao e json", encoding="utf-8")
    demos_dir = tmp_path / "demos"
    demos_dir.mkdir()
    w = watcher.MatchWatcher.__new__(watcher.MatchWatcher)
    w._current_map = None
    w.match_config_path = config
    w.demos_live_dir = demos_dir
    assert w._map_name_for("52", 0) is None
    assert w._series_num_maps() is None
