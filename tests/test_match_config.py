#!/usr/bin/env python3
"""
match_config template × runtime (card P1.9).

- O template versionado (docker/match_config.template.json) nasce com o
  jogador fictício e nunca é escrito; o runtime, que cada partida reescreve,
  fica em docker/runtime/, pasta ignorada pelo git e montada inteira no
  container (game/csgo/runtime/).
- O wizard_tui.py não muda (D13): o nome que o config exporta faz
  ROOT/"docker"/<nome> ser o runtime, e a tela de identidade da TUI (que
  monta ROOT/"docker"/<.name do nome>) chega nele pelo wizard_core.
- Não herda nada: a partida nova parte do template, nunca do runtime da
  anterior.
- git status limpo depois de jogar.

Tudo em tmp_path, com os fakes do tests/test_tui_integracao.py: nada de
docker, RCON ou processo real, e o runtime de verdade nunca é lido.
"""
import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import config
import start_match
import wizard_core
import wizard_tui
from identity import PlayerIdentity
from wizard_core import MapChoice, MatchSetup
from wizard_tui import FormatScreen, IdentityScreen, WizardApp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tui_integracao import (  # noqa: E402,F401
    MATCH_CONFIG_BASE, NICK, STEAMID, TAMANHO, clicar, esperar, lancar_pela_tui,
    launch_vigiado, servidor,
)

RAIZ = Path(__file__).resolve().parent.parent
CSGO = "/home/steam/cs2-dedicated/game/csgo"
MOUNT = re.compile(r"^\s+- (\./[^:\s]+):(/\S+)\s*$")

# Gabarito à mão do template versionado: só IDs fictícios, abaixo da base
# 76561197960265728; o de team2 é o placeholder que nunca conecta (armadilha 17).
TEMPLATE_GABARITO = {
    "num_maps": 1,
    "maplist": ["de_mirage"],
    "map_sides": ["team1_ct"],
    "clinch_series": True,
    "players_per_team": 5,
    "team1": {"name": "cobaia", "players": {"76561190000000001": "cobaia"}},
    "team2": {"name": "Bots", "players": {"76561190000000002": "BotTeamPlaceholder"}},
}

# Runtime de uma partida anterior: tudo nele é lixo para a próxima, menos o
# par nick/SteamID, de onde a tela de identidade tira o SteamID do nick.
RUNTIME_ANTERIOR = {
    "num_maps": 3,
    "maplist": ["de_dust2", "de_anubis", "de_cache"],
    "map_sides": ["team1_ct", "team1_ct", "team1_ct"],
    "clinch_series": False,
    "players_per_team": 2,
    "matchid": 77,
    "lixo_da_anterior": True,
    "team1": {"name": NICK, "players": {STEAMID: NICK}},
    "team2": {"name": "Time da anterior", "players": {"76561190000000003": "Velho"}},
}


def _escrever(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, indent=2), encoding="utf-8")


def _ler(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _git(cwd: Path, *args) -> str:
    feito = subprocess.run(["git", "-c", "user.name=teste", "-c", "user.email=teste@exemplo.invalid",
                            "-c", "core.autocrlf=false", *args],
                           cwd=cwd, capture_output=True, text=True, check=True)
    return feito.stdout


def _montagens(texto: str) -> dict:
    """{destino: fonte} das linhas de volume não comentadas."""
    return {d: f for f, d in (m.groups() for m in map(MOUNT.match, texto.splitlines()) if m)}


# ------------------------------------------------------------ nome e caminho

def test_nome_exportado_pelo_config_faz_root_docker_nome_ser_o_runtime(tmp_path):
    assert config.MATCH_CONFIG_FILE == "runtime/match_config.spike.json"
    assert wizard_tui.MATCH_CONFIG_FILE == config.MATCH_CONFIG_FILE
    runtime = tmp_path / "docker" / "runtime" / "match_config.spike.json"
    assert tmp_path / "docker" / config.MATCH_CONFIG_FILE == runtime
    assert config.caminho_match_config(tmp_path) == runtime
    # Nome solto (o de antes do P1.9, ou um .env antigo) também vai para a pasta montada.
    assert config.caminho_match_config(tmp_path, "match_config.spike.json") == runtime
    assert config.match_config_no_container() == "runtime/match_config.spike.json"
    assert config.match_config_no_container("match_config.spike.json") == \
        "runtime/match_config.spike.json"


def test_compose_monta_a_pasta_do_runtime_com_e_sem_o_vanilla():
    base = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    vanilla = (RAIZ / "docker-compose.vanilla.yml").read_text(encoding="utf-8")
    for efetivo in (_montagens(base), {**_montagens(base), **_montagens(vanilla)}):
        assert efetivo[f"{CSGO}/runtime"] == "./docker/runtime"
        assert not [d for d, f in efetivo.items() if "match_config" in d + f]
    # O que o loadmatch lê dentro do container é o arquivo que o host escreve.
    assert f"{CSGO}/runtime/match_config.spike.json" == \
        f"{CSGO}/{config.match_config_no_container()}"


def test_template_versionado_sem_pii_e_runtime_fora_do_git():
    assert _ler(RAIZ / config.MATCH_CONFIG_TEMPLATE) == TEMPLATE_GABARITO
    rastreados = _git(RAIZ, "ls-files", "--", "docker/").splitlines()
    assert "docker/match_config.template.json" in rastreados
    assert "docker/match_config.spike.json" not in rastreados
    for ignorado in ("docker/runtime/match_config.spike.json", "docker/match_config.spike.json"):
        assert subprocess.run(["git", "check-ignore", "-q", ignorado], cwd=RAIZ).returncode == 0


# ------------------------------------------------------- TUI sem diff (G4)

def test_tela_de_identidade_da_tui_tira_o_steamid_do_runtime(tmp_path, monkeypatch):
    """A IdentityScreen monta ROOT/"docker"/<.name do nome> (wizard_tui.py:210)
    e não muda: quem a leva ao runtime é o wizard_core. Um arquivo velho
    solto em docker/, com outro SteamID para o mesmo nick, não é lido."""
    for modulo in (wizard_tui, wizard_core):
        monkeypatch.setattr(modulo, "ROOT", tmp_path)
    _escrever(tmp_path / "docker" / "runtime" / "match_config.spike.json", RUNTIME_ANTERIOR)
    _escrever(tmp_path / "docker" / "match_config.spike.json",
              {"team1": {"name": NICK, "players": {"76561190000000009": NICK}}})
    identidade = []

    async def roteiro():
        app = WizardApp(rcon_password="fake")
        async with app.run_test(size=TAMANHO) as pilot:
            await esperar(app, lambda: isinstance(app.screen, IdentityScreen))
            app.screen.query_one("#player_input").value = NICK
            await clicar(pilot, "#continue")
            await esperar(app, lambda: isinstance(app.screen, FormatScreen))
            identidade.append(app.session.identity)

    asyncio.run(roteiro())
    assert identidade == [PlayerIdentity(name=NICK, steamid=STEAMID)]


def test_tui_lanca_do_template_sem_herdar_o_runtime_anterior(servidor, launch_vigiado, tmp_path):
    """Integração TUI -> core.launch -> run_match com fakes: o runtime da
    partida anterior só empresta o SteamID do nick; o resto sai do template."""
    runtime = tmp_path / "docker" / "runtime" / "match_config.spike.json"
    _escrever(runtime, RUNTIME_ANTERIOR)
    lancar_pela_tui("bo1", ["de_nuke"], ["t"], launch_vigiado)

    assert _ler(runtime) == {
        "num_maps": 1,
        "maplist": ["de_nuke"],
        "map_sides": ["team1_t"],
        "clinch_series": True,
        "players_per_team": 5,
        "team1": {"name": NICK, "players": {STEAMID: NICK}},
        "team2": {"name": "Bots", "players": {"76561190000000002": "BotTeamPlaceholder"}},
    }
    assert _ler(tmp_path / "docker" / "match_config.template.json") == MATCH_CONFIG_BASE
    assert [c for c in servidor.rcon if c.startswith("matchzy_loadmatch")] == \
        ["matchzy_loadmatch runtime/match_config.spike.json"]
    assert servidor.popen[0][-2:] == ["--match-config", str(runtime)]
    assert not (tmp_path / "docker" / "match_config.spike.json").exists()


# ------------------------------------------------------------ não herda nada

def _launch_sem_servidor(tmp_path, monkeypatch, setup):
    chamadas = []
    monkeypatch.setattr(wizard_core, "ROOT", tmp_path)
    monkeypatch.setattr(wizard_core, "run_match", lambda **kw: chamadas.append(kw))
    wizard_core.launch(setup, container_name="cs2-teste", compose_file="docker-compose.yml",
                       match_config_file=config.MATCH_CONFIG_FILE, rcon_host="127.0.0.1",
                       rcon_port=27015, rcon_password="fake", log=lambda _linha: None)
    return chamadas


def test_launch_nao_herda_nada_do_runtime_anterior(tmp_path, monkeypatch):
    """Sem SteamID na identidade, o team1.players é o do template, e não o
    jogador da partida anterior; nenhum campo da anterior sobrevive."""
    _escrever(tmp_path / "docker" / "match_config.template.json", TEMPLATE_GABARITO)
    runtime = tmp_path / "docker" / "runtime" / "match_config.spike.json"
    _escrever(runtime, RUNTIME_ANTERIOR)
    setup = MatchSetup(identity=PlayerIdentity(name="outro"), format="bo1", team_size=3,
                       maps=[MapChoice("de_inferno", "ct")])
    chamadas = _launch_sem_servidor(tmp_path, monkeypatch, setup)

    assert _ler(runtime) == {
        "num_maps": 1,
        "maplist": ["de_inferno"],
        "map_sides": ["team1_ct"],
        "clinch_series": True,
        "players_per_team": 3,
        "team1": {"name": "outro", "players": {"76561190000000001": "cobaia"}},
        "team2": {"name": "Bots", "players": {"76561190000000002": "BotTeamPlaceholder"}},
    }
    assert [c["match_config"] for c in chamadas] == ["runtime/match_config.spike.json"]


def test_launch_cria_a_pasta_do_runtime_quando_falta(tmp_path, monkeypatch):
    _escrever(tmp_path / "docker" / "match_config.template.json", TEMPLATE_GABARITO)
    setup = MatchSetup(identity=PlayerIdentity(name=NICK, steamid=STEAMID), format="bo1",
                       team_size=5, maps=[MapChoice("de_mirage", "t")])
    _launch_sem_servidor(tmp_path, monkeypatch, setup)
    escrito = _ler(tmp_path / "docker" / "runtime" / "match_config.spike.json")
    assert escrito["team1"] == {"name": NICK, "players": {STEAMID: NICK}}
    assert escrito["map_sides"] == ["team1_t"]


def test_cli_sem_runtime_nasce_do_template_e_nao_toca_no_existente(tmp_path):
    _escrever(tmp_path / "docker" / "match_config.template.json", TEMPLATE_GABARITO)
    runtime = tmp_path / "docker" / "runtime" / "match_config.spike.json"
    assert start_match.garantir_runtime(tmp_path, runtime, log=lambda _linha: None) is True
    assert _ler(runtime) == TEMPLATE_GABARITO
    _escrever(runtime, RUNTIME_ANTERIOR)
    assert start_match.garantir_runtime(tmp_path, runtime, log=lambda _linha: None) is False
    assert _ler(runtime) == RUNTIME_ANTERIOR


# ------------------------------------------------- git status depois de jogar

def test_git_status_limpo_depois_de_jogar(tmp_path, monkeypatch):
    """Clone com o .gitignore e o template do repo: depois de uma partida (o
    launch reescreve o runtime) e com a cópia local do arquivo de antes do
    P1.9 ainda na pasta, o git status não mostra nada."""
    shutil.copy2(RAIZ / ".gitignore", tmp_path / ".gitignore")
    (tmp_path / "docker").mkdir()
    shutil.copy2(RAIZ / config.MATCH_CONFIG_TEMPLATE, tmp_path / config.MATCH_CONFIG_TEMPLATE)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".gitignore", config.MATCH_CONFIG_TEMPLATE)
    _git(tmp_path, "commit", "-q", "-m", "base")
    _escrever(tmp_path / "docker" / "match_config.spike.json", RUNTIME_ANTERIOR)

    setup = MatchSetup(identity=PlayerIdentity(name=NICK, steamid=STEAMID), format="bo3",
                       team_size=5, maps=[MapChoice("de_nuke", "ct"), MapChoice("de_ancient", "t"),
                                          MapChoice("de_dust2", "ct")])
    _launch_sem_servidor(tmp_path, monkeypatch, setup)

    assert (tmp_path / "docker" / "runtime" / "match_config.spike.json").is_file()
    assert _git(tmp_path, "status", "--porcelain", "--untracked-files=all") == ""
