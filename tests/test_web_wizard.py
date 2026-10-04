#!/usr/bin/env python3
"""
Testes do wizard web (F3.1/F3.2, docs/features/M3-web-paridade.md) — sobem o
FastAPI em processo (starlette TestClient, sem servidor de verdade) e
percorrem os dois caminhos de mapa até o Resumo, igual o smoke test da TUI.
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
    """Cada teste começa com uma WizardSession limpa e um profile.json que
    não é o do repositório de verdade."""
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


def _skip_lineups(client):
    """Equivalente ao antigo botão "Seguir sem lineup" (removido no item 5,
    2026-09-20): marcar os dois lados como "Competitivo" e confirmar chega
    no mesmo lugar — lineup vazia dos dois lados (WizardSession.skip_lineups)."""
    client.post("/lineups/select-competitive", data={"side": "mine"})
    client.post("/lineups/select-competitive", data={"side": "enemy"})
    return client.post("/lineups/confirm")


def test_index_shows_home_not_wizard(client):
    # "/" é a home real agora (item 8, 2026-09-20) — o wizard só abre a
    # partir de /setup ("Configurar partida"/"JOGAR" na barra).
    resp = client.get("/")
    assert resp.url.path == "/"
    assert "TRACKER" in resp.text
    assert "Quem vai jogar" not in resp.text


def test_setup_is_the_wizard_entry_point_when_no_saved_profile(client):
    resp = client.get("/setup")
    assert resp.url.path == "/setup"
    assert "Quem vai jogar" in resp.text


def test_direct_path_full_flow(client):
    resp = client.post("/setup", data={"player": "cobaia", "fmt": "bo1", "team_size": "5"})
    assert resp.url.path == "/lineups", resp.text

    resp = _skip_lineups(client)
    assert resp.url.path == "/maps", resp.text

    resp = client.post("/maps/toggle", data={"map_name": "de_dust2"})
    assert resp.url.path == "/maps"
    assert "1. de_dust2" in resp.text or "de_dust2" in resp.text

    resp = client.post("/maps/confirm")
    assert resp.url.path == "/sides", resp.text
    assert "de_dust2" in resp.text

    resp = client.post("/sides", data={"side": "ct"})
    assert resp.url.path == "/summary", resp.text
    assert "cobaia" in resp.text
    assert "BO1" in resp.text
    assert "DE_DUST2" not in resp.text  # não maiúscula o nome do mapa
    assert "de_dust2" in resp.text


def test_direct_path_wrong_map_count_shows_error(client):
    client.post("/setup", data={"player": "cobaia", "fmt": "bo3", "team_size": "5"})
    _skip_lineups(client)
    client.post("/maps/toggle", data={"map_name": "de_dust2"})

    resp = client.post("/maps/confirm")
    assert resp.url.path == "/maps"
    assert "Escolha exatamente 3 mapa(s)" in resp.text


def test_veto_path_full_flow(client):
    client.post("/setup", data={"player": "cobaia", "fmt": "bo1", "team_size": "5"})
    _skip_lineups(client)
    resp = client.post("/maps/veto/start")
    assert resp.url.path == "/veto", resp.text

    guard = 0
    while webapp._session.step == core.STEP_MAPS:
        guard += 1
        assert guard <= 10, "veto não terminou"
        step = webapp._session.current_veto_step()
        if step.actor == "you":
            map_name = webapp._session.map_pool[0]
            resp = client.post("/veto/pick", data={"map_name": map_name})
        else:
            # O turno do bot conclui via header HX-Redirect (interpretado
            # pelo JS do htmx no browser de verdade) — um client "cru" como
            # este precisa seguir manualmente.
            resp = client.get("/veto/bot-turn")
            if resp.headers.get("HX-Redirect"):
                resp = client.get(resp.headers["HX-Redirect"])
            else:
                # Resposta de swap do HTMX: só o fragmento de #veto-box, NUNCA
                # a página inteira de novo (bug já visto ao vivo: devolver
                # "veto.html" completo aqui duplicava <html>/<head>/<body>
                # dentro do próprio #veto-box).
                assert "<html" not in resp.text.lower(), resp.text
                assert 'id="veto-box"' in resp.text

    assert webapp._session.step == core.STEP_SIDES
    assert resp.url.path == "/sides", resp.text

    resp = client.post("/sides", data={"side": "ct"})
    assert resp.url.path == "/summary"


def test_back_navigation_through_all_steps(client):
    client.post("/setup", data={"player": "cobaia", "fmt": "bo1", "team_size": "5"})
    _skip_lineups(client)
    client.post("/maps/toggle", data={"map_name": "de_dust2"})
    client.post("/maps/confirm")
    client.post("/sides", data={"side": "ct"})
    assert webapp._session.step == core.STEP_SUMMARY

    resp = client.post("/back")
    assert resp.url.path == "/sides"
    assert webapp._session.side_index == 0

    resp = client.post("/back")
    assert resp.url.path == "/maps"

    resp = client.post("/back")
    assert resp.url.path == "/lineups"

    # Jogador e Formato viraram uma tela só (item 6, 2026-09-20) — os dois
    # passos internos do WizardSession (IDENTITY, FORMAT) continuam
    # distintos, mas ambos caem na mesma rota "/setup".
    resp = client.post("/back")
    assert resp.url.path == "/setup"
    assert webapp._session.step == core.STEP_FORMAT

    resp = client.post("/back")
    assert resp.url.path == "/setup"
    assert webapp._session.step == core.STEP_IDENTITY


def test_saved_profile_skips_identity_on_next_visit(client, tmp_path):
    client.post("/setup", data={"player": "cobaia", "fmt": "bo1", "team_size": "5"})
    assert (webapp.PROFILE_PATH).exists()

    # Nova sessão (processo reiniciado, na prática) — profile.json continua lá.
    webapp._session = core.WizardSession()
    resp = client.get("/setup")
    assert resp.url.path == "/setup"
    assert webapp._session.step == core.STEP_FORMAT, "deveria pular direto pro passo 2 (D8)"


def test_reset_clears_session(client):
    client.post("/setup", data={"player": "cobaia", "fmt": "bo1", "team_size": "5"})
    assert webapp._session.step != core.STEP_IDENTITY

    # follow_redirects=False de propósito: seguir o redirect até "/" ativaria
    # o auto-skip do perfil salvo (D8) e reavançaria a sessão — o que é
    # comportamento correto do app, só não o que este teste quer observar.
    client.post("/reset", follow_redirects=False)
    assert webapp._session.step == core.STEP_IDENTITY
    assert webapp._session.identity is None
