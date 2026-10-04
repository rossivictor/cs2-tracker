#!/usr/bin/env python3
"""
Testes da tela de Mapas (item 7, 2026-09-20): duas opções grandes (escolha
direta / veto), a escolha direta abrindo num modal, e os botões de mapa (nos
dois fluxos) carregando imagem de fundo real de static/.
"""
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import web.app as webapp
import wizard_core as core


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "PROFILE_PATH", tmp_path / "profile.json")
    webapp._session = core.WizardSession()
    webapp._direct_selection.clear()
    webapp._lineup_slots["mine"] = []
    webapp._lineup_slots["enemy"] = []
    webapp._browsing = None
    yield


@pytest.fixture
def client():
    return TestClient(webapp.app, follow_redirects=True)


def _to_maps(client, fmt="bo1", team_size=5):
    client.post("/setup", data={"player": "cobaia", "fmt": fmt, "team_size": str(team_size)})
    client.post("/lineups/select-competitive", data={"side": "mine"})
    client.post("/lineups/select-competitive", data={"side": "enemy"})
    client.post("/lineups/confirm")


def test_maps_screen_shows_two_big_option_cards_without_map_grid(client):
    _to_maps(client)
    resp = client.get("/maps")
    assert 'class="mode-card"' in resp.text
    assert "Escolher o mapa pra jogar" in resp.text
    assert "Fazer veto" in resp.text
    # o grid de mapas só aparece dentro do modal (?open=direct), não na
    # tela inicial das duas opções. "class=modal-overlay" sozinho não serve
    # mais de sinal: o wizard inteiro já vive num desses por cima da home
    # (item 8, 2026-09-20) — o que importa é o grid de mapas em si.
    assert 'class="map-btn' not in resp.text


def test_maps_open_direct_shows_modal_with_map_backgrounds(client):
    _to_maps(client)
    resp = client.get("/maps", params={"open": "direct"})
    assert 'class="modal-overlay"' in resp.text
    assert 'class="map-btn' in resp.text
    assert "/static/bg-dust2.webp" in resp.text
    assert "/static/bg-mirage.webp" in resp.text


def test_toggling_a_map_keeps_the_modal_open(client):
    _to_maps(client)
    resp = client.post("/maps/toggle", data={"map_name": "de_dust2"})
    assert resp.url.path == "/maps"
    assert resp.url.query == b"open=direct" or "open=direct" in str(resp.url)
    assert 'class="modal-overlay"' in resp.text
    assert "1." in resp.text  # ordem do clique


def test_veto_grid_buttons_use_map_backgrounds(client):
    _to_maps(client, fmt="bo1")
    resp = client.post("/maps/veto/start")
    assert resp.url.path == "/veto"
    assert 'class="map-btn"' in resp.text
    assert "/static/bg-" in resp.text
