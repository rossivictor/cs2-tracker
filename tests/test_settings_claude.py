#!/usr/bin/env python3
"""
Testes do .claude/settings.json (card B0.4, Q3=A): as travas deny/ask existem
em dobro, Bash(...) e PowerShell(...), e cobrem os comandos do card.

O casamento é uma emulação da regra documentada do Claude Code
(code.claude.com/docs/en/permissions, "Wildcard patterns"): `*` casa
qualquer texto, e um ` *` final, quando é o único curinga, também casa o
comando sem argumentos. Serve pra pegar regra digitada errada ou apagada,
não substitui o motor real. O hook de guarda (B0.5) é a trava que analisa
de verdade.
"""
import json
import re
from pathlib import Path

import pytest

SETTINGS = Path(__file__).resolve().parent.parent / ".claude" / "settings.json"


@pytest.fixture(scope="module")
def permissoes():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]


def _casa(padrao, comando):
    if padrao.endswith(" *") and padrao.count("*") == 1:
        regex = re.escape(padrao[:-2]) + r"(?: .*)?"
    else:
        regex = ".*".join(re.escape(parte) for parte in padrao.split("*"))
    return re.fullmatch(regex, comando, re.DOTALL) is not None


def _decisao(permissoes, ferramenta, comando):
    for lista in ("deny", "ask"):
        for regra in permissoes.get(lista, []):
            prefixo = f"{ferramenta}("
            if regra.startswith(prefixo) and _casa(regra[len(prefixo):-1], comando):
                return lista
    return None


def _padroes(regras, ferramenta):
    prefixo = f"{ferramenta}("
    return [r[len(prefixo):-1] for r in regras if r.startswith(prefixo)]


@pytest.mark.parametrize("lista", ["deny", "ask"])
def test_cada_regra_existe_para_bash_e_powershell(permissoes, lista):
    regras = permissoes[lista]
    assert regras
    assert all(r.startswith(("Bash(", "PowerShell(")) and r.endswith(")") for r in regras)
    assert sorted(_padroes(regras, "Bash")) == sorted(_padroes(regras, "PowerShell"))


def test_nenhuma_regra_comeca_com_curinga(permissoes):
    # "Bash(* -m pip install *)" casaria `git commit -m "... pip install ..."`.
    for regra in permissoes["deny"] + permissoes["ask"]:
        assert not regra.split("(", 1)[1].startswith("*"), regra


def test_sem_allow_e_sem_hook_ainda(permissoes):
    # Allow amplia poder e depende de confiança no workspace; o hook é o B0.5.
    assert "allow" not in permissoes
    assert "hooks" not in json.loads(SETTINGS.read_text(encoding="utf-8"))


@pytest.mark.parametrize("ferramenta", ["Bash", "PowerShell"])
@pytest.mark.parametrize("comando", [
    "docker compose down",
    "docker compose down -v",
    "docker compose -f docker-compose.yml down -v",
    "docker-compose down --volumes",
    "docker compose run --rm build-plugin",
    "docker compose -p cs2-tracker run cs2 bash",
    "docker volume rm cs2-tracker_cs2-data",
    "docker volume remove cs2-tracker_cs2-data",
    "docker volume prune -f",
    "docker system prune -a --volumes",
    "git clean -fdX",
    "git clean",
    "pip install awpy",
    "python -m pip install -r requirements.txt",
    "py -m pip install ruff",
    ".venv/Scripts/python.exe -m pip install ruff",
    "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m pip install ruff",
    "/c/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/pip.exe install ruff",
    "uv pip install ruff",
])
def test_comandos_proibidos_caem_no_deny(permissoes, ferramenta, comando):
    assert _decisao(permissoes, ferramenta, comando) == "deny"


@pytest.mark.parametrize("ferramenta", ["Bash", "PowerShell"])
@pytest.mark.parametrize("comando", [
    "docker compose up -d",
    "docker compose up -d --force-recreate",
    "docker compose -f docker-compose.yml up",
    "docker compose stop",
    "docker compose restart cs2",
    "docker run --rm -v cs2-tracker_cs2-data:/d alpine ls /d",
    "docker exec cs2-spike sha256sum /home/steam/cs2-dedicated/x",
    "docker cp cs2-spike:/tmp/a ./a",
    "docker container exec cs2-spike ls",
    "docker stop cs2-spike",
])
def test_comandos_de_servidor_pedem_confirmacao(permissoes, ferramenta, comando):
    assert _decisao(permissoes, ferramenta, comando) == "ask"


@pytest.mark.parametrize("ferramenta", ["Bash", "PowerShell"])
@pytest.mark.parametrize("comando", [
    'git commit -m "Travar pip install e docker compose down (card B0.4)"',
    "git status",
    "git log --oneline -5",
    "docker compose ps",
    "docker compose config -q",
    "docker ps",
    "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m pytest -q",
    "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py",
])
def test_comandos_comuns_nao_sao_barrados(permissoes, ferramenta, comando):
    assert _decisao(permissoes, ferramenta, comando) is None
