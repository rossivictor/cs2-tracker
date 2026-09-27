#!/usr/bin/env python3
"""
Testes dos papéis em .claude/agents (card H1.6): tech-manager, dev, qa e
servidor. O PM é a sessão principal e não tem arquivo.

Por que cada checagem existe:
- Frontmatter que não é YAML válido faz o Claude Code ignorar o agente sem
  aviso: no kalendas, um `: ` sem aspas na description do qa.md sumiu com o
  papel (kalendas, L35). A .venv do jogo não tem PyYAML e nada se instala,
  então o parser daqui é um subconjunto ESTRITO de YAML, só biblioteca
  padrão: `chave: valor` numa linha, valor sem aspas ou entre aspas. Ele
  recusa o que um parser YAML recusaria ou leria diferente (`: ` ou ` #`
  num valor sem aspas, indicador no começo, chave repetida) e também o que
  este formato não usa (lista em bloco, valor vazio, tab).
- Modelo e isolamento de cada papel vêm do plano de 2026-09-26
  (agents[].model_and_isolation).
- No máximo 120 linhas por papel: o kalendas chegou a 4,6 mil linhas de
  processo e mediu o custo em contexto (kalendas, L32 e L38).
- A linha de topo que manda não reabrir o próprio prompt (kalendas, L57).
- Python pelo caminho absoluto: worktree não tem .venv (AGENTS.md).
- Relatório de formato fixo por papel, e board só pelo CLI (H1.3).
- Nenhuma linha copiada do AGENTS.md: regra universal mora lá, e o papel
  guarda só o próprio procedimento (kalendas, L38).

Só leitura de arquivo versionado: nada de processo, rede, Docker ou banco.
"""
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
AGENTES = RAIZ / ".claude" / "agents"
AGENTS_MD = RAIZ / "AGENTS.md"
PYTHON = "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe"
TOPO = "Este arquivo e o AGENTS.md já estão no seu contexto; não os abra com Read"
MAX_LINHAS = 120

# Plano 2026-09-26, agents[].model_and_isolation. O qa é sonnet por padrão; o
# PM o abre com opus em Captura, Dados e poda (parâmetro do Agent, não daqui).
# O servidor opera o checkout principal: sem worktree.
PLANO = {
    "tech-manager": ("sonnet", "worktree"),
    "dev": ("opus", "worktree"),
    "qa": ("sonnet", "worktree"),
    "servidor": ("opus", None),
}
PAPEIS = sorted(PLANO)
OBRIGATORIAS = {"name", "description", "model"}
PERMITIDAS = OBRIGATORIAS | {"isolation", "tools"}
FERRAMENTAS_DE_ESCRITA = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Campos do relatório fixo, na ordem em que aparecem no bloco do papel.
RELATORIO = {
    "dev": [
        "STATUS: PRONTO | BLOQUEADO", "BRANCH:", "COMMITS:", "ARQUIVOS:",
        "COMO VERIFICAR", "CRITÉRIOS", "ATENDIDO | NÃO ATENDIDO", "TESTES",
        "FALHAS VS BASELINE:", "RISCOS",
    ],
    "qa": [
        "VEREDITO: APROVADO | REPROVADO | DEVOLUÇÃO TÉCNICA | SEM EVIDÊNCIA",
        "CRITÉRIOS", "ATENDIDO | NÃO ATENDIDO | SEM EVIDÊNCIA", "TESTES", "G7",
        "BOARD", "FREIO",
    ],
    "tech-manager": [
        "DECISÃO DE FILA:", "PR:", "MERGE:", "TAGS:", "BOARD", "RECLASSIFICADO:",
        "BLOQUEADO / PRECISA DO PM", "PRÓXIMO PASSO",
    ],
    "servidor": [
        "JANELA:", "RUNBOOK:", "PREFLIGHT:", "BACKUP E SNAPSHOT:", "MUDANÇA:", "G6:",
        "FECHAMENTO:", "RESULTADO:", "REGISTRO: logs/janelas/<data>.md",
    ],
}

# Regra que o card manda codificar em cada papel. Sumir com uma delas numa
# poda de texto derruba o teste.
REGRAS_DO_PAPEL = {
    "dev": ["não consulta o board", "Docker", "`wizard_tui.py`", "`start_match.py`",
            "Não abre PR, não mergeia", "Não edita critério de aceite"],
    "qa": ["nunca edita código", "tools/evidencia_partida.py", "cópias",
           "**Reprovação:**", "**Devolução técnica:**", "2ª reprovação", "3ª devolução"],
    "tech-manager": ["--merge --delete-branch", "Squash ou rebase, nunca", "candidato-N",
                     "jogavel-<AAAA-MM-DD", "Trilho único", "janela aberta (preflight 4)",
                     "devolução técnica", "3ª devolução"],
    "servidor": ["docs/runbooks/", "tools/jogavel.py", "pode mexer no servidor", "Backup",
                 "Snapshot", "--force-recreate", "G6", "Fechamento (checklist G6)",
                 "Rollback", "sem worktree"],
}


class FrontmatterInvalido(ValueError):
    pass


_CHAVE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?: (.*))?$")
_INDICADOR_NO_COMECO = re.compile(r"""^[-?:,\[\]{}#&*!|>'"%@`]""")
_PYTHON_SOLTO = re.compile(r"(?<![\w./\\-])(?:python3?|py)(?:\.exe)?[ \t]+(?:-m[ \t]|[\w./\\-]+\.py\b)")


def _escalar(bruto, numero):
    if bruto != bruto.strip():
        raise FrontmatterInvalido(f"linha {numero}: espaço sobrando no valor")
    if bruto.startswith('"'):
        try:
            valor = json.loads(bruto)
        except ValueError as erro:
            raise FrontmatterInvalido(f"linha {numero}: aspas duplas mal fechadas ({erro})")
        if not isinstance(valor, str):
            raise FrontmatterInvalido(f"linha {numero}: valor entre aspas não é texto")
        return valor
    if bruto.startswith("'"):
        miolo = bruto[1:-1]
        if len(bruto) < 2 or not bruto.endswith("'") or "'" in miolo.replace("''", ""):
            raise FrontmatterInvalido(f"linha {numero}: aspas simples mal fechadas")
        return miolo.replace("''", "'")
    if _INDICADOR_NO_COMECO.match(bruto):
        raise FrontmatterInvalido(f"linha {numero}: valor sem aspas começa com indicador YAML")
    if ": " in bruto or bruto.endswith(":"):
        raise FrontmatterInvalido(f'linha {numero}: ": " sem aspas no valor (kalendas, L35)')
    if " #" in bruto:
        raise FrontmatterInvalido(f'linha {numero}: " #" sem aspas vira comentário e corta o valor')
    return bruto


def ler_frontmatter(texto):
    """Devolve (chaves, linhas do corpo) ou levanta FrontmatterInvalido."""
    if texto.startswith("\ufeff"):
        raise FrontmatterInvalido("BOM antes do --- de abertura")
    linhas = texto.split("\n")
    if linhas[0] != "---":
        raise FrontmatterInvalido("a primeira linha precisa ser ---")
    try:
        fim = linhas.index("---", 1)
    except ValueError:
        raise FrontmatterInvalido("sem --- de fechamento")
    chaves = {}
    for numero, linha in enumerate(linhas[1:fim], start=2):
        if "\t" in linha:
            raise FrontmatterInvalido(f"linha {numero}: tab no frontmatter")
        casou = _CHAVE.match(linha)
        if not casou:
            raise FrontmatterInvalido(f"linha {numero}: fora do formato `chave: valor`: {linha!r}")
        chave, bruto = casou.group(1), casou.group(2)
        if chave in chaves:
            raise FrontmatterInvalido(f"linha {numero}: chave {chave} repetida")
        if bruto is None or not bruto.strip():
            raise FrontmatterInvalido(f"linha {numero}: {chave} sem valor na mesma linha")
        chaves[chave] = _escalar(bruto, numero)
    return chaves, linhas[fim + 1:]


def _texto(papel):
    return (AGENTES / f"{papel}.md").read_text(encoding="utf-8")


def _blocos_de_codigo(texto):
    return re.findall(r"^```[^\n]*\n(.*?)^```", texto, re.MULTILINE | re.DOTALL)


# --------------------------------------------------------------- o parser tem dente


@pytest.mark.parametrize("frontmatter", [
    "---\nname: qa\ndescription: Julga o card: aprova ou reprova\n---\n",
    "---\nname: qa\ndescription: termina com dois pontos:\n---\n",
    "---\nname: qa\ndescription: corta aqui #e some\n---\n",
    "---\nname: qa\ndescription: \"aspas que não fecham\n---\n",
    "---\nname: qa\nname: dev\n---\n",
    "---\nname: qa\ntools:\n  - Read\n---\n",
    "---\nname: qa\n",
    "\ufeff---\nname: qa\n---\n",
])
def test_parser_recusa_frontmatter_que_o_claude_code_perderia(frontmatter):
    with pytest.raises(FrontmatterInvalido):
        ler_frontmatter(frontmatter)


def test_parser_aceita_dois_pontos_entre_aspas_e_devolve_o_valor():
    chaves, corpo = ler_frontmatter(
        "---\nname: qa\ndescription: \"Julga o card: aprova\"\nmodel: 'sonnet'\n---\ncorpo\n")
    assert chaves == {"name": "qa", "description": "Julga o card: aprova", "model": "sonnet"}
    assert corpo[0] == "corpo"


# --------------------------------------------------------------- os papéis


def test_existem_exatamente_os_quatro_papeis_e_o_pm_nao_tem_arquivo():
    assert sorted(p.stem for p in AGENTES.glob("*.md")) == PAPEIS
    assert not list(AGENTES.glob("pm*"))


@pytest.mark.parametrize("papel", PAPEIS)
def test_frontmatter_valido_com_as_chaves_obrigatorias(papel):
    chaves, _ = ler_frontmatter(_texto(papel))
    assert OBRIGATORIAS <= set(chaves), f"faltam {OBRIGATORIAS - set(chaves)}"
    assert set(chaves) <= PERMITIDAS, f"chave desconhecida: {set(chaves) - PERMITIDAS}"
    assert chaves["name"] == papel
    assert len(chaves["description"]) >= 80, "description curta demais para o PM escolher o papel"


@pytest.mark.parametrize("papel", PAPEIS)
def test_modelo_e_isolamento_seguem_o_plano(papel):
    chaves, _ = ler_frontmatter(_texto(papel))
    modelo, isolamento = PLANO[papel]
    assert chaves["model"] == modelo
    assert chaves.get("isolation") == isolamento


@pytest.mark.parametrize("papel", PAPEIS)
def test_description_sem_dois_pontos_e_espaco_fora_de_aspas(papel):
    linha = next(x for x in _texto(papel).split("\n") if x.startswith("description:"))
    valor = linha[len("description:"):].strip()
    assert valor.startswith(('"', "'")) or ": " not in valor


@pytest.mark.parametrize("papel", PAPEIS)
def test_no_maximo_120_linhas(papel):
    assert len(_texto(papel).splitlines()) <= MAX_LINHAS


@pytest.mark.parametrize("papel", PAPEIS)
def test_linha_de_topo_manda_nao_reabrir_o_proprio_prompt(papel):
    _, corpo = ler_frontmatter(_texto(papel))
    primeira = next(x for x in corpo if x.strip())
    assert primeira.startswith(TOPO), primeira


@pytest.mark.parametrize("papel", PAPEIS)
def test_cita_o_python_absoluto_e_nenhum_interpretador_solto(papel):
    texto = _texto(papel)
    assert PYTHON in texto
    relativos = [m.start() for m in re.finditer(r"\.venv/Scripts/python\.exe", texto)
                 if not texto[:m.end()].endswith(PYTHON)]
    assert not relativos, "worktree não tem .venv: use o caminho absoluto"
    assert not _PYTHON_SOLTO.findall(texto), "python do sistema é o 3.14: use o absoluto"


@pytest.mark.parametrize("papel", PAPEIS)
def test_relatorio_de_formato_fixo(papel):
    campos = RELATORIO[papel]
    blocos = [b for b in _blocos_de_codigo(_texto(papel)) if campos[0] in b]
    assert len(blocos) == 1, f"um bloco de relatório começando por {campos[0]!r}"
    posicao = -1
    for campo in campos:
        achou = blocos[0].find(campo, posicao + 1)
        assert achou > posicao, f"{campo!r} ausente ou fora de ordem no relatório"
        posicao = achou


@pytest.mark.parametrize("papel", ["tech-manager", "qa", "servidor"])
def test_board_so_pelo_cli_com_o_python_absoluto(papel):
    texto = _texto(papel)
    assert f"{PYTHON} -m tools.board" in texto
    assert "nunca edit nem write em `docs/board-cs2/`" in texto.lower()


def test_dev_nao_toca_no_board():
    texto = _texto("dev")
    assert "Não lê nem grava o board" in texto
    assert "tools.board" not in texto


def test_qa_e_so_leitura_por_ferramenta_e_nao_so_por_regra():
    chaves, _ = ler_frontmatter(_texto("qa"))
    ferramentas = {f.strip() for f in chaves["tools"].split(",")}
    assert not ferramentas & FERRAMENTAS_DE_ESCRITA
    assert {"Read", "Bash"} <= ferramentas
    assert "opus" in chaves["description"], "o PM precisa ver quando abrir o qa com opus"


@pytest.mark.parametrize("papel", PAPEIS)
def test_regras_que_o_card_pede_em_cada_papel(papel):
    texto = _texto(papel)
    faltam = [regra for regra in REGRAS_DO_PAPEL[papel] if regra not in texto]
    assert not faltam, f"{papel}.md perdeu: {faltam}"


@pytest.mark.parametrize("papel", PAPEIS)
def test_nao_copia_regra_do_agents_md(papel):
    texto = _texto(papel)
    copiadas = []
    em_bloco = False
    for linha in AGENTS_MD.read_text(encoding="utf-8").splitlines():
        if linha.lstrip().startswith("```"):
            em_bloco = not em_bloco
            continue
        if em_bloco:  # comando (o preflight) não é regra: citar é certo
            continue
        # Frase a frase e célula a célula: copiar meia linha também é cópia.
        for trecho in re.split(r"\s*\|\s*|(?<=[.;:])\s+|\s+\(", linha):
            regra = re.sub(r"^\s*(?:-|\d+\.)\s*", "", trecho).strip()
            if len(regra) >= 30 and regra in texto:
                copiadas.append(regra[:60])
    assert not copiadas, f"regra universal fica só no AGENTS.md: {copiadas}"
