#!/usr/bin/env python3
"""
Skills de projeto em .claude/skills (card H1.7). Skill só aponta, então
valem as cercas dos papéis (test_papeis_agentes.py, de onde vêm o parser
estrito de frontmatter e o leitor de comandos do board): frontmatter que o
Claude Code lê, curta, Python absoluto, comando do board que o CLI aceita,
subcomando do jogavel.py que existe, link que existe e nenhuma frase do
AGENTS.md copiada. Só leitura de arquivo versionado.
"""
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from test_papeis_agentes import (  # noqa: E402
    AGENTS_MD, PYTHON, _PYTHON_SOLTO, _comandos_do_board, ler_frontmatter)
from tools import jogavel  # noqa: E402
from tools.board.modelo import STATUS  # noqa: E402

SKILLS = RAIZ / ".claude" / "skills"
NOMES = ["board-cs2", "cs2-partida", "cs2-servidor", "cs2-web"]


def _texto(nome):
    return (SKILLS / nome / "SKILL.md").read_text(encoding="utf-8")


def test_existem_exatamente_as_quatro_skills():
    assert sorted(p.name for p in SKILLS.iterdir()) == NOMES


@pytest.mark.parametrize("nome", NOMES)
def test_skill_curta_que_so_aponta(nome):
    texto = _texto(nome)
    chaves, _ = ler_frontmatter(texto)
    assert set(chaves) == {"name", "description"} and chaves["name"] == nome
    assert 80 <= len(chaves["description"]) <= 300 and "Use " in chaves["description"]
    assert len(texto.splitlines()) <= 60
    assert texto.count(".venv/Scripts/python.exe") == texto.count(PYTHON)
    assert not _PYTHON_SOLTO.findall(texto)
    for alvo in re.findall(r"\]\(([^)#]+)\)", texto):
        assert (SKILLS / nome / alvo).resolve().is_file(), alvo
    for caminho in re.findall(r"`((?:tools|tests|web)/[\w./-]+\.py)", texto):
        assert (RAIZ / caminho).is_file(), caminho
    for _, opcoes, bruto in _comandos_do_board(texto):  # levanta ErroBoard se o CLI recusa
        assert opcoes.get("status", "Backlog") in STATUS, bruto


def test_board_cs2_cita_os_seis_comandos_do_cli():
    citados = {c for c, _, _ in _comandos_do_board(_texto("board-cs2"))}
    assert citados == {"validar", "fila", "mover", "historico", "criar", "reclassificar"}


def test_cs2_servidor_cita_cada_subcomando_do_jogavel_e_so_os_que_existem():
    acao = next(a for a in jogavel.montar_parser()._actions if a.dest == "comando")
    secao = re.search(r"## `tools/jogavel\.py`\n(.*?)\n## ", _texto("cs2-servidor"), re.S).group(1)
    citados = {t.split()[0] for t in re.findall(r"`([^`\n]+)`", secao)
               if t[0] != "-" and not t.startswith("tools/")}
    assert citados == set(acao.choices) - {"up", "recreate", "stop"}  # sem os apelidos


@pytest.mark.parametrize("nome", NOMES)
def test_nao_copia_regra_do_agents_md(nome):
    # O mesmo corte do test_papeis_agentes: frase a frase e célula a célula.
    texto, copiadas, em_bloco = _texto(nome), [], False
    for linha in AGENTS_MD.read_text(encoding="utf-8").splitlines():
        if linha.lstrip().startswith("```"):
            em_bloco = not em_bloco
            continue
        for trecho in ([] if em_bloco else re.split(r"\s*\|\s*|(?<=[.;:])\s+|\s+\(", linha)):
            regra = re.sub(r"^\s*(?:-|\d+\.)\s*", "", trecho).strip()
            if len(regra) >= 30 and regra in texto:
                copiadas.append(regra[:60])
    assert not copiadas, f"regra universal fica só no AGENTS.md: {copiadas}"
