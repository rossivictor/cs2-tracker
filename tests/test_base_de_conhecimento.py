#!/usr/bin/env python3
"""
Regressões da revisão da KB (cards K1.1 a K1.3): cada teste prende um erro
que a revisão achou em docs/ e que é barato voltar sem ninguém notar.

- A política de comentários mandava citar ADR no cfg do CS2 com `#`, que o
  engine não trata como comentário. O K1.9 poda justamente esse cfg.
- O ADR-0002 tratava a Q21 como pergunta aberta, mas o AGENTS.md a lista
  entre as decisões definitivas.
- Comando `git grep` com `|` sem -E, que nunca casa nada.
- Nome de nota repetido quebra o `[[nome]]` do Obsidian (os README.md de
  índice são a exceção).
- Interpretador relativo, que não existe numa worktree.
- `fontes` fora da gramática que o checar_fontes.py (K1.4) vai ler.
- Exceção de SteamID fictício do pii.py sem registro no ADR-0003.

Só leitura de arquivo versionado: nada de processo, rede, Docker ou banco.
"""
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
ADRS = DOCS / "adr"
POLITICA = DOCS / "politica-de-comentarios.md"
CFGS = RAIZ / "server-configs" / "cfg"

sys.path.insert(0, str(RAIZ / "tools" / "hooks"))
import pii  # noqa: E402


def _notas():
    """Toda nota .md da KB, sem o vault do board e sem pasta oculta
    (.obsidian): no checkout principal, docs/board-cs2/ existe fora do git."""
    notas = []
    for caminho in sorted(DOCS.rglob("*.md")):
        partes = caminho.relative_to(DOCS).parts
        if partes[0] == "board-cs2" or any(p.startswith(".") for p in partes):
            continue
        notas.append(caminho)
    return notas


def _secao(texto, titulo):
    """Corpo da seção `## titulo` até o próximo `## `."""
    achado = re.search(rf"^## {re.escape(titulo)}\s*$(.*?)(?=^## |\Z)", texto, re.M | re.S)
    assert achado, f"seção '## {titulo}' sumiu"
    return achado.group(1)


def _fontes(texto):
    """Entradas de `fontes` do frontmatter inicial, ou [] se não houver."""
    if not texto.startswith("---\n"):
        return []
    fim = texto.index("\n---", 4)
    entradas, dentro = [], False
    for linha in texto[4:fim].splitlines():
        if linha.startswith("fontes:"):
            dentro = True
            continue
        if dentro:
            item = re.match(r'^\s+-\s+"(.*)"\s*$', linha)
            if item:
                entradas.append(item.group(1))
            elif linha and not linha[0].isspace():
                dentro = False
    return entradas


# ---- cfg do CS2: o comentário é //, nunca # --------------------------------

@pytest.mark.parametrize("cfg", sorted(CFGS.glob("*.cfg")), ids=lambda p: p.name)
def test_cfg_do_cs2_nao_tem_linha_com_cerquilha(cfg):
    linhas = cfg.read_text(encoding="utf-8", errors="replace").splitlines()
    com_cerquilha = [n for n, linha in enumerate(linhas, 1) if linha.lstrip().startswith("#")]
    assert not com_cerquilha, f"{cfg.name}: '#' não é comentário no cfg, linhas {com_cerquilha}"


def test_politica_cita_cfg_com_barras_e_nunca_com_cerquilha():
    secao = _secao(POLITICA.read_text(encoding="utf-8"), "Como citar")
    linhas = secao.splitlines()
    com_cerquilha = [linha for linha in linhas if "`# ver [[" in linha]
    assert com_cerquilha, "a política perdeu a forma com # (Python, YAML, shell)"
    assert not any("cfg" in linha for linha in com_cerquilha)
    assert any("cfg" in linha and "`// ver [[" in linha for linha in linhas)
    assert any("CSS" in linha and "`/* ver [[" in linha for linha in linhas)


# ---- decisão definitiva não volta a ser pergunta ---------------------------

def _qs_definitivas():
    agents = (RAIZ / "AGENTS.md").read_text(encoding="utf-8")
    return set(re.findall(r"\bQ\d+\b", _secao(agents, "Decisões definitivas (não voltam a ser pergunta)")))


def test_agents_lista_a_q21_como_definitiva():
    assert "Q21" in _qs_definitivas()


_PERGUNTA_ABERTA = re.compile(
    r"\b(Q\d+)\b(?:\s+formal)?\s+(?:for respondida|tem prazo|está em aberto|segue em aberto|ainda está aberta)",
    re.I)


@pytest.mark.parametrize("adr", sorted(ADRS.glob("*.md")), ids=lambda p: p.name)
def test_adr_nao_reabre_decisao_definitiva(adr):
    definitivas = _qs_definitivas()
    reabertas = {q for q in _PERGUNTA_ABERTA.findall(adr.read_text(encoding="utf-8")) if q in definitivas}
    assert not reabertas, f"{adr.name} trata como aberta: {sorted(reabertas)}"


def test_padrao_de_pergunta_aberta_pega_a_frase_da_revisao():
    assert _PERGUNTA_ABERTA.search("A Q21 formal tem prazo no H1.4.")
    assert _PERGUNTA_ABERTA.search("Se a Q21 for respondida com B, um ADR novo substitui este.")
    assert not _PERGUNTA_ABERTA.search("pela escolha do Victor, que responde a Q21 com A.")


# ---- comandos citados na KB ------------------------------------------------

_GIT_GREP = re.compile(r"git grep((?:\s+-[-\w]+)*)\s+([\"'])(.*?)\2")


def _flags_de_regex_estendida(flags):
    return any(f in ("--extended-regexp", "--perl-regexp") or
               (re.fullmatch(r"-[A-Za-z]+", f) and ("E" in f or "P" in f))
               for f in flags.split())


def test_git_grep_com_alternancia_usa_regex_estendida():
    erradas = []
    for nota in _notas():
        for n, linha in enumerate(nota.read_text(encoding="utf-8").splitlines(), 1):
            for flags, _, padrao in _GIT_GREP.findall(linha):
                if "|" in padrao and "\\|" not in padrao and not _flags_de_regex_estendida(flags):
                    erradas.append(f"{nota.relative_to(RAIZ)}:{n}")
    assert not erradas, f"`|` sem -E é literal no git grep: {erradas}"


def test_checagem_de_git_grep_reconhece_o_erro():
    flags, _, padrao = _GIT_GREP.findall('`git grep -i "bracket|tournament|career"`')[0]
    assert "|" in padrao and not _flags_de_regex_estendida(flags)
    flags, _, _ = _GIT_GREP.findall("`git grep -iE \"a|b\" -- '*.py'`")[0]
    assert _flags_de_regex_estendida(flags)


def test_notas_vivas_usam_o_interpretador_pelo_caminho_absoluto():
    absoluto = "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe"
    relativas = []
    for nota in _notas():
        if nota.relative_to(DOCS).parts[0] == "historico":  # histórico não se edita
            continue
        texto = nota.read_text(encoding="utf-8")
        for achado in re.finditer(r"\.venv/Scripts/python\.exe", texto):
            if not texto[:achado.end()].endswith(absoluto):
                relativas.append(f"{nota.relative_to(RAIZ)}:{texto.count(chr(10), 0, achado.start()) + 1}")
    assert not relativas, f"worktree não tem .venv: use {absoluto} em {relativas}"


# ---- nomes de nota e frontmatter ------------------------------------------

def test_nome_de_nota_unico_na_kb_menos_os_readme_de_indice():
    vistos = {}
    for nota in _notas():
        if nota.name != "README.md":
            vistos.setdefault(nota.name, []).append(str(nota.relative_to(DOCS)))
    repetidos = {nome: caminhos for nome, caminhos in vistos.items() if len(caminhos) > 1}
    assert not repetidos, f"[[nome]] ambíguo no Obsidian: {repetidos}"


_CODIGO = r"[^\s:()]+:(\d+)(?:-(\d+))?"
_FORMAS_DE_FONTE = [
    re.compile(rf"^{_CODIGO}$"),
    re.compile(rf"^repo:[\w.-]+ {_CODIGO}$"),
    re.compile(r"^backup:\S+$"),
    re.compile(r"^transcript [0-9a-f]{8} @ \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"),
    re.compile(r"^commit [0-9a-f]{7,40}$"),
    re.compile(r"^PR #\d+$"),
]


def _forma_da_fonte(entrada):
    """O match da forma da entrada, sem o ` (detalhe)` final, ou None."""
    sem_detalhe = re.sub(r" \(.*\)$", "", entrada)
    for forma in _FORMAS_DE_FONTE:
        achado = forma.match(sem_detalhe)
        if achado:
            return achado
    return None


def test_fontes_seguem_a_gramatica_do_moc():
    fora = []
    for nota in _notas():
        for entrada in _fontes(nota.read_text(encoding="utf-8")):
            achado = _forma_da_fonte(entrada)
            if achado is None:
                fora.append(f"{nota.relative_to(RAIZ)}: {entrada}")
            elif achado.re.groups and achado.group(2) and int(achado.group(2)) < int(achado.group(1)):
                fora.append(f"{nota.relative_to(RAIZ)}: intervalo invertido em {entrada}")
    assert not fora, "fonte fora da gramática do docs/README.md:\n" + "\n".join(fora)


@pytest.mark.parametrize("entrada", [
    "kalendas:docs/agents/licoes.md:220-226",  # outro repo sem o prefixo repo:
    "commit 779a979 PR 4",                     # texto livre fora do (detalhe)
    "transcript eb5adec0 22:10Z",
])
def test_gramatica_de_fontes_recusa_forma_ambigua(entrada):
    assert _forma_da_fonte(entrada) is None


def test_gramatica_de_fontes_aceita_as_formas_do_moc():
    for entrada in ("watcher.py:455-491", "repo:kalendas docs/agents/licoes.md:260-266",
                    "backup:temp-artifacts/eb5adec0/audit/git.json (findings[8])",
                    "transcript 1ba4cab3 @ 2026-09-19T18:36:28Z", "commit 4c19249", "PR #4"):
        assert _forma_da_fonte(entrada) is not None, entrada


# ---- ADR-0003 e o pii.py ---------------------------------------------------

def test_adr_0003_nomeia_todo_id_ficticio_acima_da_base():
    adr = (ADRS / "0003-repo-publico.md").read_text(encoding="utf-8")
    acima = [i for i in pii.IDS_FICTICIOS if int(i) > pii.BASE_STEAMID64]
    assert acima, "o pii.py não libera mais nenhum ID acima da base: revise o ADR-0003"
    for steamid in acima:
        assert steamid in adr, "ID liberado pelo pii.py sem registro no ADR-0003"
