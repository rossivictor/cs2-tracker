#!/usr/bin/env python3
"""
Testes de roster.py (F1.1, docs/features/M1-lineups-headless.md) — carga do
catálogo, validação contra uma lista de perfis "disponíveis" (fake, sem
depender do container) e o critério de aceite de nunca deixar time com
perfil ausente aparecer como opção.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roster import (
    RosterCatalog,
    Team,
    build_profile_catalog,
    derive_style,
    load_rosters,
    search_profiles,
)

REAL_ROSTERS_PATH = Path(__file__).resolve().parent.parent / "data" / "rosters.json"

EXPECTED_TEAMS = {"furia", "vitality", "natus_vincere", "g2", "spirit", "mouz"}


def test_real_catalog_has_at_least_ten_teams_including_the_named_ones():
    catalog = load_rosters(REAL_ROSTERS_PATH)
    assert len(catalog.teams) >= 10
    ids = {t.id for t in catalog.teams}
    assert EXPECTED_TEAMS <= ids


def test_real_catalog_every_team_has_five_unique_players():
    catalog = load_rosters(REAL_ROSTERS_PATH)
    for team in catalog.teams:
        assert len(team.players) == 5, team.id
        assert len(set(team.players)) == 5, f"{team.id} tem jogador repetido"


def test_real_catalog_no_player_shared_across_teams():
    catalog = load_rosters(REAL_ROSTERS_PATH)
    seen = {}
    for team in catalog.teams:
        for player in team.players:
            assert player not in seen, f"{player} aparece em {seen.get(player)} e {team.id}"
            seen[player] = team.id


def test_furia_has_curated_veto_data():
    catalog = load_rosters(REAL_ROSTERS_PATH)
    furia = catalog.get("furia")
    assert furia is not None
    assert furia.veto is not None
    assert "de_mirage" in furia.veto


def test_display_name_swap_does_not_require_code_change(tmp_path):
    """Trocar display_name por um nome genérico é só editar o JSON — carrega
    de novo sem tocar em roster.py (SPEC.md §9)."""
    data = json.loads(REAL_ROSTERS_PATH.read_text(encoding="utf-8"))
    data["teams"][0]["display_name"] = "Time Genérico"
    fake_path = tmp_path / "rosters.json"
    fake_path.write_text(json.dumps(data), encoding="utf-8")

    catalog = load_rosters(fake_path)
    assert catalog.teams[0].display_name == "Time Genérico"
    # players (a chave real do VPK) não muda com o swap de display_name.
    assert catalog.teams[0].players == data["teams"][0]["players"]


def _fake_catalog():
    return RosterCatalog(
        snapshot_date="2026-01-01",
        map_pool_version="2026-01-01",
        teams=[
            Team(id="ok", display_name="OK Team", logo="ok", players=["a", "b", "c", "d", "e"]),
            Team(id="broken", display_name="Broken Team", logo="brk",
                 players=["a", "MISSING1", "c", "MISSING2", "e"]),
        ],
    )


def test_validate_against_server_flags_missing_profiles():
    catalog = _fake_catalog()
    missing = catalog.validate_against_server(available_profiles={"a", "b", "c", "d", "e"})
    assert missing == {"broken": ["MISSING1", "MISSING2"]}


def test_valid_teams_excludes_team_with_missing_profile():
    catalog = _fake_catalog()
    valid = catalog.valid_teams(available_profiles={"a", "b", "c", "d", "e"})
    assert [t.id for t in valid] == ["ok"]


def test_valid_teams_includes_everyone_when_all_profiles_present():
    catalog = _fake_catalog()
    valid = catalog.valid_teams(
        available_profiles={"a", "b", "c", "d", "e", "MISSING1", "MISSING2"}
    )
    assert {t.id for t in valid} == {"ok", "broken"}


def test_get_unknown_team_returns_none():
    catalog = _fake_catalog()
    assert catalog.get("does-not-exist") is None


# -- F4.1: leitura de estilo + catálogo de perfis ---------------------------

def test_derive_style_from_real_niko_template():
    # ProTop+RiflePro+RiflePersonality — template real do NiKo no VPK ativo
    # (docs/SPEC.md §10, Passo 0).
    style = derive_style("ProTop+RiflePro+RiflePersonality")
    assert style.role == "Rifle"
    assert style.weapon == "Rifle"
    assert style.reaction == "reação de elite"
    assert style.personality == "equilibrado"
    assert style.summary == "Rifle, reação de elite, equilibrado"


def test_derive_style_sniper_template():
    style = derive_style("ProPrecise+SniperPro+SniperPersonality")
    assert style.weapon == "AWP"
    assert style.role == "Sniper"


def test_derive_style_unknown_token_falls_back_to_placeholder():
    style = derive_style("TotallyNew+Token+Combo")
    assert style.role == "?"
    assert style.weapon == "?"
    assert style.reaction == "?"
    assert style.personality == "?"


def test_build_profile_catalog_only_includes_valid_teams():
    catalog = _fake_catalog()  # "ok" (a..e) válido, "broken" tem 2 ausentes
    templates = {
        "a": "ProTop+RiflePro+RiflePersonality",
        "b": "ProTop+RiflePro+RiflePersonality",
        "c": "ProTop+RiflePro+RiflePersonality",
        "d": "ProTop+RiflePro+RiflePersonality",
        "e": "ProTop+RiflePro+RiflePersonality",
        # MISSING1/MISSING2 do time "broken" propositalmente ausentes daqui.
    }
    cards = build_profile_catalog(catalog, templates)
    assert {c.team_id for c in cards} == {"ok"}
    assert len(cards) == 5


def test_search_profiles_by_query_and_weapon():
    catalog = _fake_catalog()
    templates = {
        "a": "ProTop+SniperPro+SniperPersonality",
        "b": "ProSteady+RiflePro+RiflePersonality",
        "c": "ProSteady+RiflePro+RiflePersonality",
        "d": "ProSteady+RiflePro+RiflePersonality",
        "e": "ProSteady+RiflePro+RiflePersonality",
    }
    cards = build_profile_catalog(catalog, templates)

    assert [c.name for c in search_profiles(cards, weapon="AWP")] == ["a"]
    assert {c.name for c in search_profiles(cards, query="ok team")} == {"a", "b", "c", "d", "e"}
    assert search_profiles(cards, query="nao existe") == []


# -- F4.4: identificar o time de origem de uma lineup -----------------------

def test_identify_team_matches_exact_roster_regardless_of_order():
    catalog = _fake_catalog()
    team = catalog.identify_team(["e", "c", "a", "d", "b"])  # ordem embaralhada
    assert team is not None
    assert team.id == "ok"


def test_identify_team_returns_none_for_manual_mix():
    catalog = _fake_catalog()
    team = catalog.identify_team(["a", "b", "c", "d", "MISSING1"])  # mistura
    assert team is None


def test_identify_team_returns_none_for_empty_lineup():
    catalog = _fake_catalog()
    assert catalog.identify_team([]) is None
