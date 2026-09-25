#!/usr/bin/env python3
"""
Testes da conversão mundo -> imagem de radar (aba Mapa).

O alinhamento de verdade foi conferido uma vez contra os dados reais —
99,9% das 8.245 posições gravadas caem em área desenhada do radar do
Mirage, e deslocar 5% derruba pra 65%. Isso não vira teste automático
porque depende do banco e das imagens; o que fica fixo aqui é a fórmula,
o snapshot de metadados e a separação de níveis.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matches  # noqa: E402

# Valores reais do resource/overviews/de_mirage.txt do CS2.
MIRAGE = {"pos_x": -3230.0, "pos_y": 1713.0, "scale": 5.0, "image_size": 1024,
          "lower_level_max_units": None}


# --------------------------------------------------------------------------- #
# A fórmula
# --------------------------------------------------------------------------- #

def test_canto_superior_esquerdo_e_a_origem_da_imagem():
    u, v = matches.world_to_radar(MIRAGE, MIRAGE["pos_x"], MIRAGE["pos_y"])
    assert u == pytest.approx(0.0)
    assert v == pytest.approx(0.0)


def test_canto_inferior_direito_e_o_fim_da_imagem():
    span = MIRAGE["scale"] * MIRAGE["image_size"]
    u, v = matches.world_to_radar(MIRAGE, MIRAGE["pos_x"] + span, MIRAGE["pos_y"] - span)
    assert u == pytest.approx(1.0)
    assert v == pytest.approx(1.0)


def test_y_do_mundo_cresce_ao_contrario_do_y_da_imagem():
    # No CS o Y cresce pro norte; na imagem cresce pra baixo.
    _, v_norte = matches.world_to_radar(MIRAGE, 0, 1000)
    _, v_sul = matches.world_to_radar(MIRAGE, 0, -1000)
    assert v_norte < v_sul


def test_resolucao_da_imagem_nao_muda_o_resultado():
    # O retorno é fração 0..1, então serve pro arquivo de 1000px em static/
    # e pro radar oficial de 1024px sem ajuste nenhum.
    ponto = (-1000.0, 500.0)
    u, v = matches.world_to_radar(MIRAGE, *ponto)
    assert 0 < u < 1 and 0 < v < 1


def test_bate_com_a_ancora_publicada_pelo_proprio_jogo():
    # TSpawn_x/TSpawn_y do overview do Mirage: 0.87 / 0.36. O centróide real
    # das posições com place='TSpawn' cai em (0.865, 0.362).
    u, v = matches.world_to_radar(MIRAGE, 1197.0, -139.0)
    assert u == pytest.approx(0.87, abs=0.02)
    assert v == pytest.approx(0.36, abs=0.02)


# --------------------------------------------------------------------------- #
# O snapshot gerado por tools/extract_map_radar.py
# --------------------------------------------------------------------------- #

def test_snapshot_cobre_os_mapas_com_imagem_em_static():
    dados = matches._map_radar_data()
    assert dados, "data/map_radar.json não carregou"
    for slug in ("ancient", "anubis", "cache", "dust2", "inferno", "mirage", "nuke"):
        assert f"de_{slug}" in dados, f"falta metadado de de_{slug}"


def test_todo_mapa_do_snapshot_tem_os_campos_da_conversao():
    for nome, meta in matches._map_radar_data().items():
        assert meta["scale"] > 0, nome
        assert meta["image_size"] > 0, nome
        assert isinstance(meta["pos_x"], (int, float)), nome
        assert isinstance(meta["pos_y"], (int, float)), nome


def test_nuke_tem_limiar_de_nivel_e_mirage_nao():
    dados = matches._map_radar_data()
    assert dados["de_nuke"]["lower_level_max_units"] == -495
    assert dados["de_mirage"]["lower_level_max_units"] is None


def test_snapshot_e_json_valido_com_procedencia():
    bruto = json.loads((ROOT / "data" / "map_radar.json").read_text(encoding="utf-8"))
    assert "snapshot_date" in bruto
    assert "overviews" in bruto["source"]


# --------------------------------------------------------------------------- #
# Montagem da aba Mapa
# --------------------------------------------------------------------------- #

def _pos(x, y, z=0.0, tipo="kill"):
    return {"round_num": 1, "type": tipo, "x": x, "y": y, "z": z,
            "place": "Middle", "side": "t", "weapon": "ak47", "opponent": "arT"}


def _positions(points):
    return {"points": points, "places": [], "bbox": {"min_x": -1, "max_x": 1, "min_y": -1, "max_y": 1},
            "sampled_ticks": 10}


def test_mapa_conhecido_usa_o_transform_do_jogo(tmp_path):
    radar = matches._radar(_positions([_pos(-3230.0, 1713.0)]), "de_mirage")
    assert radar["mode"] == "world"
    assert len(radar["levels"]) == 1
    p = radar["levels"][0]["points"][0]
    assert (p["cx"], p["cy"]) == (0.0, 0.0)


def test_mapa_desconhecido_cai_na_bounding_box():
    radar = matches._radar(_positions([_pos(0, 0), _pos(100, 100)]), "de_inexistente")
    assert radar["mode"] == "bbox"
    assert radar["levels"][0]["image"] is None


def test_nuke_separa_os_dois_niveis_pela_altitude():
    # -495 é o limiar que o overview do Nuke declara.
    pontos = [_pos(0, 0, z=100.0), _pos(0, 0, z=-800.0), _pos(0, 0, z=-800.0)]
    radar = matches._radar(_positions(pontos), "de_nuke")
    niveis = {lv["key"]: lv for lv in radar["levels"]}
    assert set(niveis) == {"upper", "lower"}
    assert len(niveis["upper"]["points"]) == 1
    assert len(niveis["lower"]["points"]) == 2
    # Abre no nível onde mais coisa aconteceu.
    assert radar["levels"][0]["key"] == "lower"


def test_nuke_sem_ponto_no_andar_de_baixo_nao_mostra_o_nivel_vazio():
    radar = matches._radar(_positions([_pos(0, 0, z=100.0)]), "de_nuke")
    assert [lv["key"] for lv in radar["levels"]] == ["upper"]


def test_cada_nivel_aponta_pra_sua_imagem():
    radar = matches._radar(_positions([_pos(0, 0, z=100.0), _pos(0, 0, z=-800.0)]), "de_nuke")
    imagens = {lv["key"]: lv["image"] for lv in radar["levels"]}
    assert imagens["upper"] == "radar-nuke-upper.webp"
    assert imagens["lower"] == "radar-nuke-lower.webp"


def test_mapa_de_um_nivel_usa_a_imagem_simples():
    radar = matches._radar(_positions([_pos(0, 0)]), "de_mirage")
    assert radar["levels"][0]["image"] == "radar-mirage.webp"
    assert radar["has_image"] is True


def test_sem_posicao_nao_ha_radar():
    assert matches._radar(None, "de_mirage") is None
