#!/usr/bin/env python3
"""
Testes do .claude/settings.json (card B0.4, Q3=A): as travas deny/ask de
comando existem em dobro, Bash(...) e PowerShell(...), cobrem os comandos do
card, e os arquivos proibidos têm deny de Read e Edit.

O casamento é uma emulação da regra documentada do Claude Code
(code.claude.com/docs/en/permissions, "Wildcard patterns"): `*` casa
qualquer texto, e um ` *` final, quando é o único curinga, também casa o
comando sem argumentos. Serve pra pegar regra digitada errada ou apagada,
não substitui o motor real. O hook de guarda (B0.5) é a trava que analisa
de verdade.

Toda regra de comando precisa de um exemplo nas tabelas abaixo que SÓ ela
casa (dentro da sua lista): assim, apagar qualquer regra muda a decisão de
algum exemplo e derruba um teste. Regra nova sem exemplo exclusivo também
derruba.
"""
import json
import re
from pathlib import Path

import pytest

SETTINGS = Path(__file__).resolve().parent.parent / ".claude" / "settings.json"
FERRAMENTAS_DE_COMANDO = ("Bash", "PowerShell")
PRINCIPAL = "//c/Users/Victor/Projetos/cs2-tracker"
VENV = "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts"


@pytest.fixture(scope="module")
def permissoes():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]


def _casa(padrao, comando):
    if padrao.endswith(" *") and padrao.count("*") == 1:
        regex = re.escape(padrao[:-2]) + r"(?: .*)?"
    else:
        regex = ".*".join(re.escape(parte) for parte in padrao.split("*"))
    return re.fullmatch(regex, comando, re.DOTALL) is not None


def _padroes(regras, ferramenta):
    prefixo = f"{ferramenta}("
    return [r[len(prefixo):-1] for r in regras if r.startswith(prefixo)]


def _decisao(permissoes, ferramenta, comando):
    for lista in ("deny", "ask"):
        if any(_casa(p, comando) for p in _padroes(permissoes.get(lista, []), ferramenta)):
            return lista
    return None


def _formas_compose(sub, args):
    """As quatro formas que as três regras de um subcomando do compose cobrem:
    `<sub> *` (com e sem argumento), `* <sub>` e `* <sub> *`."""
    formas = []
    for binario in ("docker compose", "docker-compose"):
        formas += [f"{binario} {sub}", f"{binario} {sub} {args}",
                   f"{binario} -f docker-compose.yml {sub}",
                   f"{binario} -f docker-compose.yml {sub} {args}"]
    return formas


PROIBIDOS = [
    *_formas_compose("down", "-v"),
    "docker-compose down --volumes",
    *_formas_compose("run", "--rm build-plugin"),
    "docker compose -p cs2-tracker run cs2 bash",
    "docker volume rm cs2-tracker_cs2-data",
    "docker volume remove cs2-tracker_cs2-data",
    "docker volume prune -f",
    "docker system prune -a --volumes",
    "git clean -fdX",
    "git clean",
    "git -C C:/Users/Victor/Projetos/cs2-tracker clean -fdX",
    "git -C ../.. clean",
    "pip install awpy",
    "pip3 install awpy",
    "pip.exe uninstall -y textual",
    "pip uninstall textual",
    "python -m pip install -r requirements.txt",
    "python3 -m pip uninstall -y ruff",
    "python.exe -m pip install ruff",
    "py -m pip install ruff",
    "uv pip install ruff",
    "uv pip uninstall textual",
    "uv pip sync requirements.txt",
    ".venv/Scripts/python.exe -m pip install ruff",
    ".venv\\Scripts\\python.exe -m pip uninstall -y ruff",
    ".venv/Scripts/pip.exe install ruff",
    ".venv/Scripts/pip uninstall ruff",
    f"{VENV}/python.exe -m pip install ruff",
    f"{VENV}/python.exe -m pip uninstall -y textual",
    "C:\\Users\\Victor\\Projetos\\cs2-tracker\\.venv\\Scripts\\python.exe -m pip install ruff",
    f"{VENV}/pip3.exe install ruff",
    f"{VENV}/pip.exe uninstall ruff",
    "/c/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/pip.exe install ruff",
    "/c/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/pip uninstall ruff",
    "/c/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m pip install ruff",
    "/c/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m pip uninstall ruff",
]

DE_SERVIDOR = [
    *_formas_compose("up", "-d"),
    "docker compose up -d --force-recreate",
    *_formas_compose("stop", "cs2"),
    *_formas_compose("restart", "cs2"),
    *_formas_compose("kill", "cs2"),
    *_formas_compose("exec", "cs2 sh"),
    *_formas_compose("cp", "cs2:/tmp/a ./a"),
    *_formas_compose("rm", "-s -f"),
    *_formas_compose("pause", "cs2"),
    "docker run --rm -v cs2-tracker_cs2-data:/d alpine ls /d",
    "docker container run --rm alpine true",
    "docker exec cs2-spike sha256sum /home/steam/cs2-dedicated/x",
    "docker container exec cs2-spike ls",
    "docker cp cs2-spike:/tmp/a ./a",
    "docker container cp cs2-spike:/tmp/a ./a",
    "docker stop cs2-spike",
    "docker container stop cs2-spike",
    "docker restart cs2-spike",
    "docker container restart cs2-spike",
    "docker kill cs2-spike",
    "docker container kill cs2-spike",
    "docker rm -f cs2-spike",
    "docker container rm cs2-spike",
    "git push --force origin chore/B0.4-agents-md",
    "git push --force-with-lease origin chore/B0.4-agents-md",
    "git push -f origin chore/B0.4-agents-md",
    "git push origin chore/B0.4-agents-md -f",
    "git push origin main",
    "git push origin main --tags",
    "git push origin HEAD:main",
    "git reset --hard",
    "git reset --hard origin/main",
]

COMUNS = [
    'git commit -m "Travar pip install e docker compose down (card B0.4)"',
    # Falso positivo da regra antiga "C:*pip* install *" (revisão do B0.4).
    'C:/Program Files/Git/cmd/git.exe commit -m "pipeline: install hook"',
    "git status",
    "git log --oneline -5",
    "git -C C:/Users/Victor/Projetos/cs2-tracker status",
    "git push -u origin chore/B0.4-agents-md",
    "git push origin HEAD:chore/B0.4-agents-md",
    "git push origin chore/B0.4-main-fix",
    "git reset --soft HEAD~1",
    "docker compose ps",
    "docker compose config -q",
    "docker compose logs --tail 50",
    "docker ps",
    "docker inspect cs2-spike",
    "docker logs --since 2026-09-26T10:00:00 cs2-spike",
    "pip list",
    "pip show pytest",
    "uv --version",
    f"{VENV}/python.exe -m pip list",
    f"{VENV}/python.exe -m pytest -q -k pip",
    f"{VENV}/python.exe tools/preflight.py",
]

TABELAS = {"deny": PROIBIDOS, "ask": DE_SERVIDOR}

# Arquivos que nenhum agente lê nem escreve (AGENTS.md, zonas proibidas). O
# deny de Read vale pras ferramentas de arquivo e pros comandos de arquivo
# que o Claude Code reconhece no Bash (cat, head, sed, tee, redirecionamento);
# o de Edit cobre também o NotebookEdit.
ARQUIVOS_PROIBIDOS = [
    ".env",
    f"{PRINCIPAL}/.env",
    f"{PRINCIPAL}/cs2_tracker.db*",
    f"{PRINCIPAL}/data/profile.json",
    f"{PRINCIPAL}/docker/events-live/**",
    "//c/cs2server/**",
]


@pytest.mark.parametrize("lista", ["deny", "ask"])
def test_cada_regra_de_comando_existe_para_bash_e_powershell(permissoes, lista):
    regras = permissoes[lista]
    assert regras
    assert all(r.startswith(("Bash(", "PowerShell(", "Read(", "Edit(")) and r.endswith(")")
               for r in regras)
    assert _padroes(regras, "Bash")
    assert sorted(_padroes(regras, "Bash")) == sorted(_padroes(regras, "PowerShell"))


def test_nenhuma_regra_de_comando_comeca_com_curinga(permissoes):
    # "Bash(* -m pip install *)" casaria `git commit -m "... pip install ..."`.
    for lista in ("deny", "ask"):
        for ferramenta in FERRAMENTAS_DE_COMANDO:
            for padrao in _padroes(permissoes[lista], ferramenta):
                assert not padrao.startswith("*"), padrao


def test_sem_allow(permissoes):
    # Allow amplia poder e depende de confiança no workspace. O registro do
    # hook de guarda (B0.5) é conferido em tests/test_guarda.py.
    assert "allow" not in permissoes


def test_arquivos_proibidos_tem_deny_de_read_e_edit(permissoes):
    for ferramenta in ("Read", "Edit"):
        assert sorted(_padroes(permissoes["deny"], ferramenta)) == sorted(ARQUIVOS_PROIBIDOS)
    assert not _padroes(permissoes["ask"], "Read")
    # A própria guarda (B0.5) no checkout principal: editar pede confirmação ao
    # Victor. Nas worktrees o caminho é outro, e o card que mexe nela segue livre.
    assert sorted(_padroes(permissoes["ask"], "Edit")) == sorted(
        [f"{PRINCIPAL}/.claude/settings.json", f"{PRINCIPAL}/tools/hooks/**"])
    # O .env.example é o que o agente usa no lugar do .env: fica liberado.
    assert ".env.example" not in _padroes(permissoes["deny"], "Read")


@pytest.mark.parametrize("lista", ["deny", "ask"])
def test_toda_regra_de_comando_tem_um_exemplo_so_dela(permissoes, lista):
    padroes = _padroes(permissoes[lista], "Bash")
    sem_exemplo = []
    for padrao in padroes:
        outros = [p for p in padroes if p != padrao]
        if not any(_casa(padrao, c) and not any(_casa(o, c) for o in outros)
                   for c in TABELAS[lista]):
            sem_exemplo.append(padrao)
    assert not sem_exemplo, f"regras sem exemplo exclusivo em {lista}: {sem_exemplo}"


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_COMANDO)
@pytest.mark.parametrize("comando", PROIBIDOS)
def test_comandos_proibidos_caem_no_deny(permissoes, ferramenta, comando):
    assert _decisao(permissoes, ferramenta, comando) == "deny"


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_COMANDO)
@pytest.mark.parametrize("comando", DE_SERVIDOR)
def test_comandos_de_servidor_pedem_confirmacao(permissoes, ferramenta, comando):
    assert _decisao(permissoes, ferramenta, comando) == "ask"


@pytest.mark.parametrize("ferramenta", FERRAMENTAS_DE_COMANDO)
@pytest.mark.parametrize("comando", COMUNS)
def test_comandos_comuns_nao_sao_barrados(permissoes, ferramenta, comando):
    assert _decisao(permissoes, ferramenta, comando) is None
