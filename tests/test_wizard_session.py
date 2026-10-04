#!/usr/bin/env python3
"""
Testes de WizardSession (F2.1, docs/features/M2-nucleo.md) — nenhuma
dependência de Textual. Cobrem MD1/MD3/MD5 pelos dois caminhos (escolha
direta e veto) e as transições de "voltar" que pulam passos que não se
aplicam.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identity import PlayerIdentity
import wizard_core as core


def make_identity() -> PlayerIdentity:
    return PlayerIdentity(name="cobaia", steamid="76561190000000001")


def new_session() -> core.WizardSession:
    session = core.WizardSession()
    session.set_identity(make_identity())
    return session


def to_maps_step(session: core.WizardSession, fmt: str, team_size: int = 5) -> None:
    """set_format + skip_lineups — a maioria destes testes é sobre Mapas/
    Veto/Lados, não sobre Lineups (F4.2, tem teste próprio), então pula
    direto pro modo anônimo de sempre, igual o wizard_tui.py faz."""
    session.set_format(fmt, team_size)
    session.skip_lineups()


@pytest.mark.parametrize("fmt", ["bo1", "bo3", "bo5"])
def test_direct_path(fmt):
    session = new_session()
    to_maps_step(session, fmt)
    assert session.step == core.STEP_MAPS

    needed = core.MAPS_PER_FORMAT[fmt]
    maps = core.DEFAULT_MAP_POOL[:needed]
    session.choose_maps_direct(maps)
    assert session.step == core.STEP_SIDES
    assert session.maps_in_order == maps

    for i, map_name in enumerate(maps):
        assert session.side_index == i
        session.set_side("ct" if i % 2 == 0 else "t")

    assert session.step == core.STEP_SUMMARY
    assert [c.map_name for c in session.map_choices] == maps

    setup = session.to_match_setup()
    assert setup.identity == make_identity()
    assert setup.format == fmt
    assert setup.team_size == 5
    assert len(setup.maps) == needed


@pytest.mark.parametrize("fmt", ["bo1", "bo3", "bo5"])
def test_veto_path(fmt):
    session = new_session()
    to_maps_step(session, fmt)
    session.start_veto()
    assert session.veto_active
    assert session.step == core.STEP_MAPS

    # Resolve o veto inteiro escolhendo sempre o primeiro mapa restante do
    # pool, sem se importar de quem seria o turno (actor) — o objetivo aqui é
    # só validar que a sequência termina no número certo de mapas.
    guard = 0
    while session.step == core.STEP_MAPS:
        guard += 1
        assert guard <= 10, "veto não terminou — possível loop infinito"
        step = session.current_veto_step()
        assert step is not None
        map_name = session.map_pool[0]
        session.resolve_veto_step(map_name)

    assert not session.veto_active
    assert session.step == core.STEP_SIDES
    needed = core.MAPS_PER_FORMAT[fmt]
    assert len(session.maps_in_order) == needed
    assert len(set(session.maps_in_order)) == needed  # sem mapa repetido

    for map_name in session.maps_in_order:
        session.set_side("ct")

    assert session.step == core.STEP_SUMMARY
    setup = session.to_match_setup()
    assert len(setup.maps) == needed


def test_resolve_veto_step_rejects_map_outside_pool():
    session = new_session()
    to_maps_step(session, "bo1")
    session.start_veto()
    with pytest.raises(core.WizardError):
        session.resolve_veto_step("de_vertigo")  # fora do DEFAULT_MAP_POOL


def test_set_format_before_identity_raises():
    session = core.WizardSession()
    with pytest.raises(core.WizardError):
        session.set_format("bo1", team_size=5)


def test_choose_maps_direct_wrong_count_raises():
    session = new_session()
    to_maps_step(session, "bo3")
    with pytest.raises(core.WizardError):
        session.choose_maps_direct(["de_mirage"])  # bo3 precisa de 3


def test_set_side_outside_step_raises():
    session = new_session()
    to_maps_step(session, "bo1")
    with pytest.raises(core.WizardError):
        session.set_side("ct")  # ainda no passo Mapas


def test_back_from_identity_raises():
    session = core.WizardSession()
    with pytest.raises(core.WizardError):
        session.back()


def test_back_undoes_format():
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.back()
    assert session.step == core.STEP_FORMAT


def test_back_from_sides_undoes_last_side_without_leaving_step():
    session = new_session()
    to_maps_step(session, "bo3")
    maps = core.DEFAULT_MAP_POOL[:3]
    session.choose_maps_direct(maps)
    session.set_side("ct")
    session.set_side("t")
    assert session.side_index == 2

    session.back()
    assert session.step == core.STEP_SIDES
    assert session.side_index == 1
    assert len(session.map_choices) == 1


def test_back_from_first_side_returns_to_maps_and_skips_veto():
    """Um veto concluído não é resumível: voltar do primeiro mapa de Lados
    pula direto pro passo Mapas, sem reativar o veto (docs/features/
    M2-nucleo.md, F2.1)."""
    session = new_session()
    to_maps_step(session, "bo1")
    session.start_veto()
    while session.step == core.STEP_MAPS:
        session.resolve_veto_step(session.map_pool[0])

    assert session.side_index == 0
    session.back()
    assert session.step == core.STEP_MAPS
    assert not session.veto_active


def test_skip_lineups_leaves_anonymous_mode():
    session = new_session()
    session.set_format("bo1", team_size=5)
    assert session.step == core.STEP_LINEUPS
    session.skip_lineups()
    assert session.step == core.STEP_MAPS
    assert session.my_lineup == []
    assert session.enemy_lineup == []


def test_set_lineups_happy_path():
    session = new_session()
    session.set_format("bo1", team_size=3)
    session.set_lineups(my_lineup=["NiKo", "m0NESY"], enemy_lineup=["s1mple", "ZywOo", "donk"])
    assert session.step == core.STEP_MAPS
    assert session.my_lineup == ["NiKo", "m0NESY"]
    assert session.enemy_lineup == ["s1mple", "ZywOo", "donk"]
    setup = session.to_match_setup()
    assert setup.my_lineup == ["NiKo", "m0NESY"]
    assert setup.enemy_lineup == ["s1mple", "ZywOo", "donk"]


def test_set_lineups_wrong_size_raises():
    session = new_session()
    session.set_format("bo1", team_size=5)
    with pytest.raises(core.WizardError):
        session.set_lineups(my_lineup=["NiKo"], enemy_lineup=["s1mple"] * 5)  # precisa de 4


def test_set_lineups_overlap_between_sides_raises():
    session = new_session()
    session.set_format("bo1", team_size=2)
    with pytest.raises(core.WizardError):
        session.set_lineups(my_lineup=["NiKo"], enemy_lineup=["NiKo", "s1mple"])


def test_set_lineups_human_nick_collision_raises():
    session = new_session()  # identity.name == "cobaia"
    session.set_format("bo1", team_size=2)
    with pytest.raises(core.WizardError):
        session.set_lineups(my_lineup=["cobaia"], enemy_lineup=["NiKo", "s1mple"])


def test_back_from_lineups_returns_to_format():
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.back()
    assert session.step == core.STEP_FORMAT


def test_back_from_maps_returns_to_lineups_not_format():
    session = new_session()
    to_maps_step(session, "bo1")
    session.back()
    assert session.step == core.STEP_LINEUPS


FURIA_PLAYERS = ["KSCERATO", "yuurih", "FalleN", "molodoy", "YEKINDAR"]


def test_to_match_setup_identifies_known_team_for_scoreboard():
    """F4.4: uma lineup que bate 100% com um roster do catálogo ganha
    nome/logo próprios pro placar."""
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.set_lineups(my_lineup=["s1mple", "ZywOo", "donk", "NiKo"], enemy_lineup=FURIA_PLAYERS)
    setup = session.to_match_setup()
    assert setup.enemy_team_name == "FURIA"
    assert setup.enemy_team_logo == "fur"


def test_to_match_setup_manual_mix_uses_neutral_label():
    session = new_session()
    session.set_format("bo1", team_size=5)
    mixed = FURIA_PLAYERS[:-1] + ["s1mple"]  # 4 da FURIA + 1 de fora: não é nenhum time
    session.set_lineups(my_lineup=["ZywOo", "donk", "NiKo", "m0NESY"], enemy_lineup=mixed)
    setup = session.to_match_setup()
    assert setup.enemy_team_name == core.NEUTRAL_ENEMY_LABEL
    assert setup.enemy_team_logo == ""


def test_scoreboard_args_none_when_no_lineup():
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.skip_lineups()
    setup = session.to_match_setup()
    enemy_team_name, enemy_team_logo = core._scoreboard_args(setup)
    assert enemy_team_name is None
    assert enemy_team_logo == ""


def test_scoreboard_args_set_when_lineup_used():
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.set_lineups(my_lineup=["s1mple", "ZywOo", "donk", "NiKo"], enemy_lineup=FURIA_PLAYERS)
    setup = session.to_match_setup()
    enemy_team_name, enemy_team_logo = core._scoreboard_args(setup)
    assert enemy_team_name == "FURIA"
    assert enemy_team_logo == "fur"


def test_build_match_config_sets_team2_name_only_when_lineup_used():
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.set_lineups(my_lineup=["s1mple", "ZywOo", "donk", "NiKo"], enemy_lineup=FURIA_PLAYERS)
    setup = session.to_match_setup()
    base_config = {"team1": {}, "team2": {"name": "Bots"}}
    data = core.build_match_config(base_config, setup)
    assert data["team2"]["name"] == "FURIA"


def test_build_match_config_leaves_team2_placeholder_without_lineup():
    session = new_session()
    session.set_format("bo1", team_size=5)
    session.skip_lineups()
    session.choose_maps_direct([core.DEFAULT_MAP_POOL[0]])
    setup = session.to_match_setup()
    base_config = {"team1": {}, "team2": {"name": "Bots"}}
    data = core.build_match_config(base_config, setup)
    assert data["team2"]["name"] == "Bots"


def test_back_from_summary_reopens_last_map():
    session = new_session()
    to_maps_step(session, "bo1")
    session.choose_maps_direct([core.DEFAULT_MAP_POOL[0]])
    session.set_side("ct")
    assert session.step == core.STEP_SUMMARY

    session.back()
    assert session.step == core.STEP_SIDES
    assert session.side_index == 0
    assert session.map_choices == []
