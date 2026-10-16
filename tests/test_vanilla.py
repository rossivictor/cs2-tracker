#!/usr/bin/env python3
"""
Válvula vanilla (card P1.2): config.compose_files() é a única fonte da lista
de -f do docker compose, com o estado em data/servidor.json; o start_match
e o tools/jogavel.py (recreate, compose config e config-hash) a usam; o
`jogavel.py vanilla on|off` grava o estado e recria na janela; e o
docker-compose.vanilla.yml mascara só os plugins de bot.

Com o vanilla off (padrão) o argv do docker compose é o de antes do P1.2:
`-f <base>` no start_match e sem -f no jogavel.py. Os gabaritos são escritos
à mão. Tudo em tmp_path, com o docker falso do tests/test_jogavel.py: nada
de processo de verdade, Docker, RCON ou rede.
"""
import json
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

import config
import start_match

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import jogavel  # noqa: E402
from jogavel import FALHA, OK, PARTIDA, RECUSA  # noqa: E402
from test_jogavel import _registro, _rodar, janela, montado, mundo  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parent.parent
BASE = "docker-compose.yml"
VANILLA = "docker-compose.vanilla.yml"


def _estado(raiz, texto):
    (raiz / "data").mkdir(parents=True, exist_ok=True)
    (raiz / "data" / "servidor.json").write_text(texto, encoding="utf-8")


def _override(raiz):
    (raiz / VANILLA).write_text("services: {}\n", encoding="utf-8")


# ------------------------------------------------- config.compose_files

def test_sem_servidor_json_so_o_base(tmp_path):
    _override(tmp_path)
    assert config.compose_files(raiz=tmp_path, base=BASE) == ["docker-compose.yml"]
    assert config.compose_files(raiz=tmp_path) == [config.COMPOSE_FILE]


def test_vanilla_ligado_empilha_o_override_depois_do_base(tmp_path):
    _override(tmp_path)
    _estado(tmp_path, '{"vanilla": true}')
    assert config.compose_files(raiz=tmp_path, base=BASE) == \
        ["docker-compose.yml", "docker-compose.vanilla.yml"]


def test_vanilla_false_so_o_base(tmp_path):
    _override(tmp_path)
    _estado(tmp_path, '{"vanilla": false, "outra": 1}')
    assert config.compose_files(raiz=tmp_path, base=BASE) == ["docker-compose.yml"]


@pytest.mark.parametrize("texto, motivo", [
    ("{vanilla: true", "ilegível"),
    ('["vanilla"]', "não é um objeto"),
    ('{"vanilla": "true"}', "não é true/false"),
    ('{"vanilla": 1}', "não é true/false"),
])
def test_servidor_json_invalido_conta_como_off_com_aviso(tmp_path, texto, motivo):
    _override(tmp_path)
    _estado(tmp_path, texto)
    avisos = []
    assert config.compose_files(raiz=tmp_path, base=BASE, avisar=avisos.append) == ["docker-compose.yml"]
    assert len(avisos) == 1 and motivo in avisos[0] and avisos[0].startswith("[AVISO] ")


def test_vanilla_ligado_sem_o_override_no_checkout_sobe_so_o_base(tmp_path):
    # tag anterior ao P1.2 (voltar) com o estado ainda ligado: o jogo sobe
    _estado(tmp_path, '{"vanilla": true}')
    avisos = []
    assert config.compose_files(raiz=tmp_path, base=BASE, avisar=avisos.append) == ["docker-compose.yml"]
    assert "docker-compose.vanilla.yml não existe" in avisos[0]


def test_parametro_vanilla_vence_o_arquivo(tmp_path):
    _override(tmp_path)
    _estado(tmp_path, '{"vanilla": true}')
    assert config.compose_files(raiz=tmp_path, base=BASE, vanilla=False) == ["docker-compose.yml"]
    _estado(tmp_path, '{"vanilla": false}')
    assert config.compose_files(raiz=tmp_path, base=BASE, vanilla=True) == \
        ["docker-compose.yml", "docker-compose.vanilla.yml"]


# ------------------------------------------------------------ start_match

@pytest.fixture
def docker_do_start_match(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(start_match, "ROOT", tmp_path)
    monkeypatch.setattr(start_match, "subprocess", types.SimpleNamespace(
        run=lambda argv, **kw: chamadas.append((list(argv), kw))))
    return chamadas


def test_compose_up_com_vanilla_off_e_o_argv_de_antes(tmp_path, docker_do_start_match):
    _override(tmp_path)
    _estado(tmp_path, '{"vanilla": false}')
    start_match.compose_up(tmp_path / BASE, log=lambda _t: None)
    assert docker_do_start_match == [(
        ["docker", "compose", "-f", str(tmp_path / "docker-compose.yml"), "up", "-d"],
        {"check": True, "cwd": tmp_path})]


def test_compose_up_com_vanilla_on_leva_os_dois_f(tmp_path, docker_do_start_match):
    _override(tmp_path)
    _estado(tmp_path, '{"vanilla": true}')
    logs = []
    start_match.compose_up(tmp_path / BASE, log=logs.append)
    assert docker_do_start_match == [(
        ["docker", "compose", "-f", str(tmp_path / "docker-compose.yml"),
         "-f", str(tmp_path / "docker-compose.vanilla.yml"), "up", "-d"],
        {"check": True, "cwd": tmp_path})]
    assert logs == ["[DOCKER] Subindo servidor (docker-compose.yml + docker-compose.vanilla.yml)..."]


# ---------------------------------------------------------- tools/jogavel

@pytest.fixture
def com_f(mundo):
    """O docker falso do test_jogavel não conhece -f: aqui os pares `-f X`
    do compose saem antes de ele responder (o mundo.docker guarda o argv
    inteiro)."""
    responder = mundo._docker

    def _docker(args):
        if args[:1] == ["compose"]:
            resto = args[1:]
            while resto[:1] == ["-f"]:
                resto = resto[2:]
            args = ["compose", *resto]
        return responder(args)
    mundo._docker = _docker
    return mundo


UP_BASE = "compose up -d --force-recreate"
UP_VANILLA = "compose -f docker-compose.yml -f docker-compose.vanilla.yml up -d --force-recreate"


def _servidor_json(mundo):
    return json.loads((mundo.raiz / "data" / "servidor.json").read_text(encoding="utf-8"))


def test_recriar_com_vanilla_off_e_o_argv_de_antes(janela, com_f):
    _override(janela.raiz)
    assert _rodar(janela, "recriar") == OK
    assert [c for c in janela.docker if c.startswith("compose")] == [UP_BASE]


def test_recriar_com_vanilla_on_empilha_o_override(janela, com_f):
    _override(janela.raiz)
    _estado(janela.raiz, '{"vanilla": true}')
    assert _rodar(janela, "recriar") == OK
    assert [c for c in janela.docker if c.startswith("compose")] == [UP_VANILLA]


def test_vanilla_on_grava_o_estado_e_recria_na_janela(janela, com_f, capsys):
    _override(janela.raiz)
    _estado(janela.raiz, '{"outra": 1}')
    assert _rodar(janela, "vanilla", "on") == OK
    assert _servidor_json(janela) == {"outra": 1, "vanilla": True}
    assert [c for c in janela.docker if c.startswith("compose")] == [UP_VANILLA]
    assert janela.docker[0] == "logs -t cs2-spike"  # os logs se salvam antes do recreate
    assert "vanilla: off -> on" in capsys.readouterr().out
    assert " jogavel.py vanilla on: saída 0\n" in _registro(janela)
    assert not list((janela.raiz / "data").glob("*.tmp"))


def test_vanilla_off_grava_o_estado_e_recria_so_com_o_base(janela, com_f):
    _override(janela.raiz)
    _estado(janela.raiz, '{"vanilla": true}')
    assert _rodar(janela, "vanilla", "off") == OK
    assert _servidor_json(janela) == {"vanilla": False}
    assert [c for c in janela.docker if c.startswith("compose")] == [UP_BASE]


@pytest.mark.parametrize("acao, estado, comando", [
    ("on", None, "[seco] docker " + UP_VANILLA),
    ("off", '{"vanilla": true}', "[seco] docker " + UP_BASE),
])
def test_vanilla_seco_nao_grava_nem_recria(janela, com_f, capsys, acao, estado, comando):
    _override(janela.raiz)
    if estado:
        _estado(janela.raiz, estado)
    antes = (janela.raiz / "data" / "servidor.json").read_bytes() if estado else None
    assert _rodar(janela, "vanilla", acao, "--seco") == OK
    saida = capsys.readouterr().out
    assert f"[seco] data/servidor.json: vanilla {'true' if acao == 'on' else 'false'}" in saida
    assert comando in saida.splitlines()
    assert not any(c.startswith("compose") for c in janela.docker)
    arquivo = janela.raiz / "data" / "servidor.json"
    assert arquivo.read_bytes() == antes if estado else not arquivo.exists()


def test_vanilla_on_sem_janela_recusa_e_nao_grava(mundo, monkeypatch):
    _override(mundo.raiz)
    monkeypatch.chdir(mundo.raiz)
    mundo.preflight = 4
    assert _rodar(mundo, "vanilla", "on") == RECUSA
    assert not (mundo.raiz / "data" / "servidor.json").exists() and mundo.docker == []


def test_vanilla_on_com_o_victor_jogando_recusa_e_nao_grava(janela):
    _override(janela.raiz)
    janela.preflight = 3
    assert _rodar(janela, "vanilla", "on") == PARTIDA
    assert not (janela.raiz / "data" / "servidor.json").exists() and janela.docker == []


def test_vanilla_on_sem_o_override_falha_sem_gravar(janela):
    assert _rodar(janela, "vanilla", "on") == FALHA
    assert not (janela.raiz / "data" / "servidor.json").exists() and janela.docker == []


def test_vanilla_status_so_le(mundo, capsys):
    _override(mundo.raiz)
    _estado(mundo.raiz, '{"vanilla": true}')
    assert _rodar(mundo, "vanilla", "status") == OK
    assert "vanilla: on (data/servidor.json); compose: docker-compose.yml + docker-compose.vanilla.yml" \
        in capsys.readouterr().out
    assert mundo.docker == []


def test_coletar_com_vanilla_on_compara_o_config_hash_do_compose_empilhado(montado, com_f, tmp_path):
    _override(montado.raiz)
    _estado(montado.raiz, '{"vanilla": true}')
    assert _rodar(montado, "coletar", "--destino", str(tmp_path / "g7")) == OK
    assert [c for c in montado.docker if c.startswith("compose")] == [
        "compose -f docker-compose.yml -f docker-compose.vanilla.yml config --format json",
        "compose -f docker-compose.yml -f docker-compose.vanilla.yml config --hash cs2-server"]


def test_override_conta_como_infra(mundo):
    ex = jogavel.Executor(mundo.raiz, rodar=mundo.rodar)
    assert jogavel.infra_no_delta(ex, ["docker-compose.vanilla.yml", "start_match.py"]) == \
        ["docker-compose.vanilla.yml"]


# ------------------------------------------------- docker-compose.vanilla.yml

MOUNT = re.compile(r"^\s+- (\./[^:\s]+):(/\S+)\s*$")
EMPTY = "./docker/plugins/_empty"
PLUGINS_CSSHARP = "/home/steam/cs2-dedicated/game/csgo/addons/counterstrikesharp/plugins/"
# Gabarito à mão, do docker-compose.yml da jogavel-2026-09-26 (o vanilla de
# antes da trilha de bots, ADR-0005): as pastas cobertas por _empty.
MASCARADOS_EM_26_09 = {
    PLUGINS_CSSHARP + nome for nome in
    ("RayTraceImpl", "BotAI", "BotAimImprover", "BotBuy", "BotHiderImpl", "BotRandomizer",
     "BotState", "NadeSystem")} | {
    "/home/steam/cs2-dedicated/game/csgo/addons/RayTrace",
    "/home/steam/cs2-dedicated/game/csgo/addons/BotHider"}


def _montagens(texto):
    """(fonte, destino) das linhas de volume não comentadas, na ordem."""
    return [m.groups() for m in map(MOUNT.match, texto.splitlines()) if m]


def _efetivo(*textos):
    """Merge do compose para volumes de serviço: o destino é a chave, e o
    arquivo de depois substitui o de antes."""
    final = {}
    for texto in textos:
        final.update({destino: fonte for fonte, destino in _montagens(texto)})
    return final


def test_override_volta_as_mascaras_de_26_09(tmp_path):
    base = (RAIZ / BASE).read_text(encoding="utf-8")
    vanilla = (RAIZ / VANILLA).read_text(encoding="utf-8")
    assert re.search(r"^services:\n  cs2-server:\n    volumes:\n", vanilla, re.M)
    assert "\n  cs2-server:\n" in base
    efetivo = _efetivo(base, vanilla)
    assert {d for d, f in efetivo.items() if f == EMPTY} == MASCARADOS_EM_26_09
    # Sem o override, o base de hoje carrega os plugins de bot (a trilha).
    assert {d for d, f in _efetivo(base).items() if f == EMPTY} < MASCARADOS_EM_26_09


def test_override_so_mascara_plugin_de_bot_e_nunca_a_matchzy_nem_a_captura(tmp_path):
    base = (RAIZ / BASE).read_text(encoding="utf-8")
    vanilla = (RAIZ / VANILLA).read_text(encoding="utf-8")
    montagens = _montagens(vanilla)
    assert montagens and all(fonte == EMPTY for fonte, _ in montagens)
    for _, destino in montagens:
        assert destino.startswith(PLUGINS_CSSHARP), destino
        assert "MatchZy" not in destino and "Cs2TrackerEvents" not in destino
        assert destino in base  # o destino existe no base (bind ou máscara comentada)
    efetivo = _efetivo(base, vanilla)
    assert efetivo[PLUGINS_CSSHARP + "Cs2TrackerEvents"] == "./docker/plugins/Cs2TrackerEvents"
    assert efetivo["/home/steam/cs2-dedicated/game/csgo/events-live"] == "./docker/events-live"
    assert efetivo["/home/steam/cs2-dedicated/game/csgo/MatchZy"] == "./docker/demos-live"


def test_estado_ignorado_pelo_git():
    ignorado = subprocess.run(["git", "check-ignore", "-q", "data/servidor.json"], cwd=RAIZ)
    assert ignorado.returncode == 0
