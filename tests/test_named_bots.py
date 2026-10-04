#!/usr/bin/env python3
"""
Testes de _resolve_lineup_names (F1.2, docs/features/M1-lineups-headless.md)
— validação pura de lineup nomeada, sem RCON. A adição de fato (bot_add_ct/
bot_add_t, detecção de nome inexistente/duplicado) foi validada ao vivo
contra o container (docs/SPEC.md não guarda esse log; ver histórico da
sessão), porque depende do botprofile.vpk carregado no servidor.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from start_match import BotAddError, _resolve_lineup_names


def test_anonymous_fallback_when_no_lineup():
    ct_names, t_names = _resolve_lineup_names(
        human_side="ct", team_size=5, player="cobaia", my_lineup=None, enemy_lineup=None,
    )
    assert ct_names == [None] * 4
    assert t_names == [None] * 5


@pytest.mark.parametrize("human_side,expected_ct,expected_t", [
    ("ct", ["a", "b"], ["e1", "e2", "e3"]),
    ("t", ["e1", "e2", "e3"], ["a", "b"]),
])
def test_named_lineup_assigned_to_correct_side(human_side, expected_ct, expected_t):
    ct_names, t_names = _resolve_lineup_names(
        human_side=human_side, team_size=3, player="cobaia",
        my_lineup=["a", "b"], enemy_lineup=["e1", "e2", "e3"],
    )
    assert ct_names == expected_ct
    assert t_names == expected_t


def test_my_lineup_wrong_size_raises():
    with pytest.raises(BotAddError):
        _resolve_lineup_names(
            human_side="ct", team_size=5, player="cobaia",
            my_lineup=["a", "b"],  # precisa de 4 (team_size - 1)
            enemy_lineup=None,
        )


def test_enemy_lineup_wrong_size_raises():
    with pytest.raises(BotAddError):
        _resolve_lineup_names(
            human_side="ct", team_size=5, player="cobaia",
            my_lineup=None,
            enemy_lineup=["a", "b", "c"],  # precisa de 5 (team_size)
        )


def test_human_nick_collision_with_my_lineup_raises():
    with pytest.raises(BotAddError):
        _resolve_lineup_names(
            human_side="ct", team_size=2, player="NiKo",
            my_lineup=["NiKo"], enemy_lineup=None,
        )


def test_human_nick_collision_with_enemy_lineup_raises():
    with pytest.raises(BotAddError):
        _resolve_lineup_names(
            human_side="ct", team_size=1, player="NiKo",
            my_lineup=None, enemy_lineup=["NiKo"],
        )
