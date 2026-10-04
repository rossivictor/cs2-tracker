#!/usr/bin/env python3
"""
Smoke da TUI (card T1.5): o wizard_tui.py monta e percorre o fluxo inteiro
headless (App.run_test do Textual, Pilot), em bo1 e bo3, até o Resumo, sem
lançar nada. É a prova offline (G4) de que um card que toca wizard_core,
start_match, watcher, config, identity ou cs2tracker/server não quebrou a
TUI; o lançamento em si fica no tests/test_tui_integracao.py.

Nada vivo: o core.launch vira uma trava que falha se for chamado, e o ROOT
do wizard aponta para uma pasta temporária com um match_config e um compose
escritos à mão (o docker/match_config.spike.json do repo nunca é lido nem
escrito). O wizard_tui.py não muda (AGENTS.md, D13): só os atributos do
módulo são trocados pelo monkeypatch.

Também roda o tools/make_screenshots.py numa pasta temporária: ele percorre
o mesmo fluxo e estava quebrado desde que o estado do veto e dos lados foi
para a WizardSession (F2.1).
"""
import asyncio
import json
import time

import pytest

import wizard_core
import wizard_tui
from tools import make_screenshots
from wizard_tui import (
    FormatScreen, IdentityScreen, MapSelectScreen, SideScreen, SummaryScreen,
    VetoScreen, WizardApp,
)

TAMANHO = (100, 34)
NICK = "cobaia"
STEAMID = "76561190000000001"  # fictício, abaixo da base 76561197960265728

# Gabarito do template: o mesmo formato do docker/match_config.spike.json,
# escrito à mão com o jogador fictício.
MATCH_CONFIG_BASE = {
    "num_maps": 1,
    "maplist": ["de_mirage"],
    "map_sides": ["team1_ct"],
    "clinch_series": True,
    "players_per_team": 5,
    "team1": {"name": NICK, "players": {STEAMID: NICK}},
    "team2": {"name": "Bots", "players": {"76561190000000002": "BotTeamPlaceholder"}},
}


@pytest.fixture
def raiz_falsa(tmp_path, monkeypatch):
    """ROOT do wizard numa pasta temporária: match_config e compose à mão."""
    (tmp_path / "docker").mkdir()
    (tmp_path / "docker" / "match_config.spike.json").write_text(
        json.dumps(MATCH_CONFIG_BASE, indent=2), encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  cs2:\n    environment:\n      - CS2_MAXPLAYERS=11\n", encoding="utf-8")
    monkeypatch.setattr(wizard_tui, "ROOT", tmp_path)
    monkeypatch.setattr(wizard_core, "ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def veto_sem_espera(monkeypatch):
    """Zera o countdown do bot e a pausa do fim do veto: são só pausas de
    tela (o worker do turno do bot roda igual), e com elas o arquivo
    passaria dos 20 s do critério."""
    monkeypatch.setattr(wizard_tui, "BOT_TURN_COUNTDOWN_S", 0)
    monkeypatch.setattr(wizard_tui, "VETO_RESULT_DWELL_S", 0)


@pytest.fixture
def sem_launch(monkeypatch):
    chamadas = []

    def launch_proibido(*args, **kwargs):
        chamadas.append((args, kwargs))
        raise AssertionError("o smoke não lança partida")

    monkeypatch.setattr(wizard_core, "launch", launch_proibido)
    return chamadas


async def esperar(app, condicao, timeout=10.0, passo=0.05):
    inicio = time.monotonic()
    while time.monotonic() - inicio < timeout:
        if condicao():
            return
        await asyncio.sleep(passo)
    raise TimeoutError(f"condição não satisfeita em {timeout}s (tela: {app.screen!r})")


async def clicar(pilot, seletor):
    """Clica e espera o efeito -active do Button (0.2 s) passar: dentro dele
    o Textual ignora um segundo clique no mesmo widget."""
    await pilot.click(seletor)
    await pilot.pause()
    await asyncio.sleep(0.25)


async def jogador_e_formato(app, pilot, formato):
    await esperar(app, lambda: isinstance(app.screen, IdentityScreen))
    app.screen.query_one("#player_input").value = NICK
    await clicar(pilot, "#continue")
    await esperar(app, lambda: isinstance(app.screen, FormatScreen))
    await clicar(pilot, f"#{formato}")
    await clicar(pilot, "#continue")
    await esperar(app, lambda: isinstance(app.screen, MapSelectScreen))


async def lados(app, pilot, escolhas):
    await esperar(app, lambda: isinstance(app.screen, SideScreen))
    for i, lado in enumerate(escolhas):
        await esperar(app, lambda: bool(app.screen.query("#side_radio")))
        await clicar(pilot, f"#{lado}")
        await clicar(pilot, "#confirm")
        await esperar(app, lambda: app.session.side_index == i + 1)
    await esperar(app, lambda: isinstance(app.screen, SummaryScreen))
    await pilot.pause()


def texto_do_resumo(app) -> str:
    return str(app.screen.query_one("#summary_text").render())


def test_smoke_bo1_escolha_direta_ate_o_resumo(raiz_falsa, sem_launch):
    inicio = time.monotonic()

    async def roteiro():
        app = WizardApp(rcon_password="fake", skip_up=True)
        async with app.run_test(size=TAMANHO) as pilot:
            await jogador_e_formato(app, pilot, "bo1")
            await clicar(pilot, "#map-de_nuke")
            await clicar(pilot, "#continue")
            await lados(app, pilot, ["t"])
            return app.session, texto_do_resumo(app)

    sessao, resumo = asyncio.run(roteiro())

    assert resumo == (
        "Jogador: cobaia (76561190000000001)\n"
        "Formato: BO1\n"
        "Jogadores por time: 5\n"
        "Mapas:\n"
        "  1. de_nuke (T)"
    )
    setup = sessao.to_match_setup()
    assert setup.identity == wizard_core.PlayerIdentity(name=NICK, steamid=STEAMID)
    assert (setup.format, setup.team_size) == ("bo1", 5)
    assert setup.maps == [wizard_core.MapChoice("de_nuke", "t")]
    assert (setup.my_lineup, setup.enemy_lineup) == ([], [])
    assert sem_launch == []
    assert time.monotonic() - inicio < 20


def test_smoke_bo3_com_veto_ate_o_resumo(raiz_falsa, sem_launch, veto_sem_espera, monkeypatch):
    # O bot sempre tira o primeiro mapa do que sobrou: a série fica fixa.
    monkeypatch.setattr(wizard_core, "resolve_bot_step", lambda pool: pool[0])
    inicio = time.monotonic()

    async def meu_turno(app, pilot, mapa, indice):
        await esperar(app, lambda: app.session.veto_step_index == indice
                      and bool(app.screen.query(f"#map-buttons #map-{mapa}")))
        await clicar(pilot, f"#map-{mapa}")
        await esperar(app, lambda: app.session.veto_step_index > indice)

    async def roteiro():
        app = WizardApp(rcon_password="fake", skip_up=True)
        async with app.run_test(size=TAMANHO) as pilot:
            await jogador_e_formato(app, pilot, "bo3")
            await clicar(pilot, "#veto")
            await esperar(app, lambda: isinstance(app.screen, VetoScreen))
            # bo3 no pool de 7: ban, ban, pick, pick, ban, ban; você começa.
            await meu_turno(app, pilot, "de_cache", 0)    # bot bane de_dust2
            await meu_turno(app, pilot, "de_nuke", 2)     # bot escolhe de_mirage
            await meu_turno(app, pilot, "de_anubis", 4)   # bot bane de_inferno
            await lados(app, pilot, ["ct", "t", "ct"])
            return app.session, texto_do_resumo(app)

    sessao, resumo = asyncio.run(roteiro())

    assert sessao.veto_history == [
        "Você baniu de_cache",
        "Bot baniu de_dust2",
        "Você escolheu de_nuke",
        "Bot escolheu de_mirage",
        "Você baniu de_anubis",
        "Bot baniu de_inferno",
        "Mapa decisivo: de_ancient",
    ]
    assert resumo == (
        "Jogador: cobaia (76561190000000001)\n"
        "Formato: BO3\n"
        "Jogadores por time: 5\n"
        "Mapas:\n"
        "  1. de_nuke (CT)\n"
        "  2. de_mirage (T)\n"
        "  3. de_ancient (CT)"
    )
    assert sem_launch == []
    assert time.monotonic() - inicio < 20


def test_make_screenshots_percorre_o_wizard_numa_pasta_temporaria(raiz_falsa, veto_sem_espera,
                                                                  tmp_path):
    launch_real = wizard_core.launch
    saida = tmp_path / "img"

    salvos = asyncio.run(make_screenshots.main(saida))

    assert salvos == [
        "01-jogador.svg", "02-formato.svg", "03-mapas.svg", "04-veto.svg",
        "05-lados.svg", "06-resumo.svg", "07-partida.svg",
    ]
    assert sorted(p.name for p in saida.iterdir()) == salvos
    resumo = (saida / "06-resumo.svg").read_text(encoding="utf-8")
    assert "cobaia" in resumo and "BO3" in resumo
    assert "terminal-06-resumo" in resumo  # id fixo, sem o aleatório do Rich
    # A troca do launch pelo log falso não vaza para quem importou o módulo.
    assert wizard_core.launch is launch_real
