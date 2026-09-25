#!/usr/bin/env python3
"""
Testes da tela de Lineups (F4.1/F4.2, docs/features/M4-seletor.md) — sobem o
FastAPI em processo com um catálogo de perfis FAKE (sem depender do
container/VPK real) e cobrem: pool compartilhado entre os dois lados,
colisão com o nick do humano, presets, aleatório e a validação final.
"""
import re
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import roster
import web.app as webapp
import wizard_core as core


def fake_catalog():
    return roster.RosterCatalog(
        snapshot_date="2026-01-01",
        map_pool_version="2026-01-01",
        teams=[
            roster.Team(id="teama", display_name="Team A", logo="a",
                        players=["a1", "a2", "a3", "a4", "a5"]),
            roster.Team(id="teamb", display_name="Team B", logo="b",
                        players=["b1", "b2", "b3", "b4", "b5"]),
        ],
    )


def fake_cards():
    catalog = fake_catalog()
    templates = {p: "ProSteady+RiflePro+RiflePersonality" for team in catalog.teams for p in team.players}
    return roster.build_profile_catalog(catalog, templates)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, "PROFILE_PATH", tmp_path / "profile.json")
    monkeypatch.setattr(webapp, "_ROSTERS", fake_catalog())
    monkeypatch.setattr(webapp, "_profile_cards_cache", fake_cards())
    webapp._session = core.WizardSession()
    webapp._direct_selection.clear()
    webapp._lineup_slots["mine"] = []
    webapp._lineup_slots["enemy"] = []
    webapp._browsing = None
    yield


@pytest.fixture
def client():
    return TestClient(webapp.app, follow_redirects=True)


def _to_lineups(client, team_size=3):
    client.post("/setup", data={"player": "can1sh", "fmt": "bo1", "team_size": str(team_size)})


def test_lineups_screen_shows_right_slot_counts(client):
    _to_lineups(client, team_size=3)
    resp = client.get("/lineups")
    assert resp.status_code == 200
    assert len(webapp._lineup_slots["mine"]) == 2  # team_size - 1
    assert len(webapp._lineup_slots["enemy"]) == 3


def test_pick_fills_slot_and_shows_style(client):
    _to_lineups(client)
    resp = client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})
    assert webapp._lineup_slots["mine"][0] == "a1"
    assert "a1" in resp.text
    assert "Team A" in resp.text


def test_pick_same_name_on_other_side_is_rejected():
    pass  # coberto por test_shared_pool_excludes_name_from_other_side abaixo


def test_shared_pool_excludes_name_from_other_side(client):
    _to_lineups(client)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})

    resp = client.post("/lineups/pick", data={"side": "enemy", "slot": 0, "name": "a1"})
    assert "já está escolhido em outra vaga" in resp.text
    assert webapp._lineup_slots["enemy"][0] is None


def test_human_nick_cannot_be_picked(client):
    _to_lineups(client)  # identity.name == "can1sh"
    resp = client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "can1sh"})
    assert "não pode ser escolhido" in resp.text
    assert webapp._lineup_slots["mine"][0] is None


def test_browse_excludes_used_and_human_names(client):
    _to_lineups(client)
    client.post("/lineups/pick", data={"side": "enemy", "slot": 0, "name": "b1"})

    resp = client.get("/lineups/browse", params={"side": "mine", "slot": 0})
    # "b1" aparece legitimamente no painel adversário (já escolhido lá) —
    # o que não pode aparecer é como CARD ESCOLHÍVEL na busca (um form de
    # pick com esse nome no hidden input).
    assert 'name="name" value="b1"' not in resp.text  # já usado do outro lado
    assert 'name="name" value="can1sh"' not in resp.text  # nick do humano


def test_random_team_overwrites_side_with_a_full_catalog_team(client):
    """"Sortear 1 time" (item 5, 2026-09-20) — mesmo caminho de código do
    clique num logo, mas o time é escolhido pelo servidor."""
    _to_lineups(client, team_size=5)
    client.post("/lineups/pick", data={"side": "enemy", "slot": 0, "name": "b1"})

    client.post("/lineups/random-team", data={"side": "enemy"})

    enemy = webapp._lineup_slots["enemy"]
    assert None not in enemy
    assert set(enemy) in ({"a1", "a2", "a3", "a4", "a5"}, {"b1", "b2", "b3", "b4", "b5"})


def test_random_lineup_overwrites_all_slots_without_collision(client):
    """"Gerar lineup aleatória" (item 5, 2026-09-20) substitui a lineup
    inteira — diferente do antigo "Aleatório", que só preenchia vagas
    vazias."""
    _to_lineups(client, team_size=3)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})

    client.post("/lineups/random-lineup", data={"side": "mine"})
    client.post("/lineups/random-lineup", data={"side": "enemy"})

    all_names = webapp._lineup_slots["mine"] + webapp._lineup_slots["enemy"]
    assert None not in all_names
    assert len(set(all_names)) == len(all_names)  # sem colisão
    assert "can1sh" not in all_names


def test_confirm_requires_all_slots_filled(client):
    _to_lineups(client, team_size=3)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})

    resp = client.post("/lineups/confirm")
    assert resp.url.path == "/lineups"
    assert "Preencha todas as vagas" in resp.text
    assert webapp._session.step == core.STEP_LINEUPS


def test_confirm_commits_to_session_and_advances(client):
    _to_lineups(client, team_size=3)
    client.post("/lineups/random-lineup", data={"side": "mine"})
    client.post("/lineups/random-lineup", data={"side": "enemy"})

    resp = client.post("/lineups/confirm")
    assert resp.url.path == "/maps"
    assert webapp._session.step == core.STEP_MAPS
    assert len(webapp._session.my_lineup) == 2
    assert len(webapp._session.enemy_lineup) == 3


def test_back_from_lineups_to_format_and_forward_again(client):
    _to_lineups(client, team_size=3)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})

    resp = client.post("/back")
    assert resp.url.path == "/setup"

    # Reenviar o mesmo team_size não deveria perder a escolha (a
    # repopulação do _reset_lineup_slots só entra em ação se o tamanho
    # mudar OU se a sessão já tiver uma lineup confirmada — como não
    # confirmamos ainda, a vaga é perdida aqui, que é o esperado: só o que
    # foi *confirmado* sobrevive a voltar até o Jogador & Formato).
    resp = client.post("/setup", data={"fmt": "bo1", "team_size": "3"})
    assert resp.url.path == "/lineups"


def test_back_from_maps_to_lineups_restores_confirmed_lineup(client):
    _to_lineups(client, team_size=3)
    client.post("/lineups/random-lineup", data={"side": "mine"})
    client.post("/lineups/random-lineup", data={"side": "enemy"})
    client.post("/lineups/confirm")
    assert webapp._session.step == core.STEP_MAPS
    confirmed_mine = list(webapp._session.my_lineup)

    resp = client.post("/back")
    assert resp.url.path == "/lineups"
    assert webapp._lineup_slots["mine"] == confirmed_mine


def test_browse_pick_forms_use_the_browsed_slot_not_result_position(client):
    """Regressão: o campo oculto `slot` de cada card de resultado precisa
    ser o da VAGA sendo trocada (browsing[1]), não a posição do card dentro
    da grade de resultados — bug real reportado pelo usuário: trocar KSCERATO
    (MT2/slot 0) por yuurih acabava sobrescrevendo outra vaga (a posição de
    yuurih na lista), e uma posição fora do intervalo causava um 500."""
    _to_lineups(client, team_size=5)  # mine tem 4 vagas, catálogo fake tem 10 — resultados > vagas
    resp = client.get("/lineups/browse", params={"side": "mine", "slot": 1})
    assert resp.status_code == 200

    slot_values = set(re.findall(
        r'name="slot" value="(\d+)">\s*<input type="hidden" name="name"', resp.text
    ))
    assert slot_values == {"1"}, (
        f"todo card de resultado deveria carregar slot=1 (a vaga sendo trocada), achei {slot_values}"
    )


def test_swap_at_high_slot_index_does_not_500(client):
    """O card N-ésimo da lista de resultados tem index0 >= len(slots) pra
    times pequenos — antes do fix isso virava IndexError (500) ao tentar
    _lineup_slots[side][slot]. Agora _valid_slot recusa com uma mensagem."""
    _to_lineups(client, team_size=2)  # mine tem só 1 vaga (índice 0)
    resp = client.post("/lineups/pick", data={"side": "mine", "slot": 7, "name": "a1"})
    assert resp.status_code == 200
    assert "Vaga inválida" in resp.text
    assert webapp._lineup_slots["mine"] == [None]


def test_swap_replaces_the_intended_slot_end_to_end(client):
    """Reproduz o cenário relatado: preenche 3 vagas, troca a do MEIO
    especificamente, e confirma que só ela mudou."""
    _to_lineups(client, team_size=4)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})
    client.post("/lineups/pick", data={"side": "mine", "slot": 1, "name": "a2"})
    client.post("/lineups/pick", data={"side": "mine", "slot": 2, "name": "a3"})

    resp = client.get("/lineups/browse", params={"side": "mine", "slot": 1})
    slot_values = set(re.findall(
        r'name="slot" value="(\d+)">\s*<input type="hidden" name="name"', resp.text
    ))
    assert slot_values == {"1"}

    client.post("/lineups/pick", data={"side": "mine", "slot": 1, "name": "b1"})
    assert webapp._lineup_slots["mine"] == ["a1", "b1", "a3"]


# -- Item 1 (2026-09-20): grade de logos + modo competitivo -----------------

def test_select_team_overwrites_existing_manual_picks(client):
    """Diferente do "Time pronto" antigo (só preenche vaga vazia), a grade
    de logos SUBSTITUI a lineup inteira — era o bug reportado ("checkbox
    só funciona quando as vagas estão livres")."""
    _to_lineups(client, team_size=5)
    client.post("/lineups/pick", data={"side": "enemy", "slot": 0, "name": "b1"})
    client.post("/lineups/pick", data={"side": "enemy", "slot": 1, "name": "b2"})

    client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teama"})

    assert webapp._lineup_slots["enemy"] == ["a1", "a2", "a3", "a4", "a5"]


def test_select_team_highlights_correctly(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teamb"})
    page = client.get("/lineups").text

    # dois grids (mine/enemy) listam os mesmos times — só o form do lado
    # "enemy" pro teamb deve ter a classe "selected".
    forms = re.findall(
        r'<input type="hidden" name="side" value="(\w+)">\s*'
        r'<input type="hidden" name="team_id" value="teamb">\s*'
        r'<button type="submit" class="logo-box ([^"]*)"',
        page,
    )
    by_side = dict(forms)
    assert "selected" in by_side["enemy"]
    assert "selected" not in by_side["mine"]


def test_select_team_switching_teams_replaces_whole_lineup(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teama"})
    assert webapp._lineup_slots["enemy"] == ["a1", "a2", "a3", "a4", "a5"]

    client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teamb"})
    assert webapp._lineup_slots["enemy"] == ["b1", "b2", "b3", "b4", "b5"]


def test_select_team_reports_conflict_with_other_side(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})

    resp = client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teama"})
    assert "ficou de fora" in resp.text
    assert "a1" in resp.text
    assert webapp._lineup_slots["enemy"][0] is None  # a1 não entrou (colidiu)
    assert webapp._lineup_slots["mine"][0] == "a1"  # e não foi removido do outro lado


def test_select_competitive_locks_and_zeroes_slots(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/pick", data={"side": "enemy", "slot": 0, "name": "a1"})

    client.post("/lineups/select-competitive", data={"side": "enemy"})

    assert webapp._competitive["enemy"] is True
    assert webapp._lineup_slots["enemy"] == [None] * 5


def test_competitive_page_shows_locked_placeholder(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-competitive", data={"side": "enemy"})
    page = client.get("/lineups").text
    assert "Player competitivo rand" in page
    assert "Escolher perfil" not in page.split("ADVERSÁRIO")[-1] if "ADVERSÁRIO" in page else True


def test_manual_pick_clears_competitive_flag(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-competitive", data={"side": "mine"})
    assert webapp._competitive["mine"] is True

    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})
    assert webapp._competitive["mine"] is False


def test_select_team_clears_competitive_flag(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-competitive", data={"side": "enemy"})
    client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teama"})
    assert webapp._competitive["enemy"] is False


def test_confirm_allows_one_side_competitive_other_manual(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-team", data={"side": "enemy", "team_id": "teama"})
    client.post("/lineups/select-competitive", data={"side": "mine"})

    resp = client.post("/lineups/confirm")
    assert resp.url.path == "/maps"
    assert webapp._session.my_lineup == []
    assert webapp._session.enemy_lineup == ["a1", "a2", "a3", "a4", "a5"]


def test_confirm_both_competitive_behaves_like_skip(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-competitive", data={"side": "mine"})
    client.post("/lineups/select-competitive", data={"side": "enemy"})

    resp = client.post("/lineups/confirm")
    assert resp.url.path == "/maps"
    assert webapp._session.my_lineup == []
    assert webapp._session.enemy_lineup == []


def test_confirm_competitive_side_does_not_require_slots_filled(client):
    _to_lineups(client, team_size=5)
    client.post("/lineups/select-competitive", data={"side": "mine"})
    client.post("/lineups/pick", data={"side": "enemy", "slot": 0, "name": "a1"})
    client.post("/lineups/pick", data={"side": "enemy", "slot": 1, "name": "a2"})
    client.post("/lineups/pick", data={"side": "enemy", "slot": 2, "name": "a3"})
    client.post("/lineups/pick", data={"side": "enemy", "slot": 3, "name": "a4"})
    client.post("/lineups/pick", data={"side": "enemy", "slot": 4, "name": "a5"})

    resp = client.post("/lineups/confirm")
    assert resp.url.path == "/maps"  # não pede pra preencher o lado competitivo


# -- Itens 2 e 3 (2026-09-20): linha do humano + ícones sem texto -----------

def test_human_row_shows_name_and_no_swap_or_remove_buttons(client):
    _to_lineups(client, team_size=3)
    page = client.get("/lineups").text
    assert "can1sh (você)" in page
    # a linha do humano é a única sem forms de troca/remoção associados —
    # não dá pra isolar por posição no HTML puro, então valida indiretamente:
    # o texto "Trocar"/"Limpar" não existe mais em lugar nenhum (item 3),
    # e a linha do humano mostra estatística (ou o aviso de "sem partidas").
    assert "Trocar" not in page
    assert "Limpar" not in page
    assert ("partida" in page) or ("Sem partidas registradas" in page)


def test_bot_rows_use_icon_only_buttons(client):
    _to_lineups(client, team_size=3)
    client.post("/lineups/pick", data={"side": "mine", "slot": 0, "name": "a1"})
    page = client.get("/lineups").text
    assert 'class="icon-btn"' in page
    # sem TEXTO visível "Trocar"/"Limpar" (só em atributos title/aria-label,
    # que são o que dá acessibilidade ao botão só-ícone).
    assert ">Trocar<" not in page
    assert ">Limpar<" not in page
    assert 'title="Trocar"' in page
    assert 'title="Remover"' in page


# -- Item 4 (2026-09-20): modal de troca -------------------------------------

def test_browse_opens_modal_overlay(client):
    _to_lineups(client, team_size=3)
    resp = client.get("/lineups/browse", params={"side": "mine", "slot": 0})
    assert 'class="modal-overlay"' in resp.text
    assert webapp._browsing == ("mine", 0)


def test_browse_cancel_closes_modal_without_picking(client):
    _to_lineups(client, team_size=3)
    client.get("/lineups/browse", params={"side": "mine", "slot": 0})

    resp = client.post("/lineups/browse/cancel")
    assert resp.url.path == "/lineups"
    assert webapp._browsing is None
    # o wizard inteiro agora vive dentro de um modal por cima da home (item
    # 8, 2026-09-20), então "class=modal-overlay" sempre aparece uma vez —
    # o que precisa sumir é o modal *interno* de escolher jogador.
    assert "Escolher jogador" not in resp.text
    assert webapp._lineup_slots["mine"][0] is None


def test_active_filter_gets_highlighted(client):
    _to_lineups(client, team_size=3)
    resp = client.get("/lineups/browse", params={"side": "mine", "slot": 0, "q": "a1"})
    # o campo de texto (com o valor "a1") ganha a classe de destaque; o
    # dropdown de função, que não foi usado, não ganha.
    q_input = re.search(r'name="q"[\s\S]*?>', resp.text).group()
    role_select = re.search(r'<select name="role"[^>]*>', resp.text).group()
    assert 'class="filter-active"' in q_input
    assert 'class="filter-active"' not in role_select
