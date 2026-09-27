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
- As passagens de bastão que a 1ª revisão do H1.6 achou quebradas: todo
  comando do board citado nos papéis passa pelo parser do CLI de verdade;
  G6/G7 RUIM reprova sem tirar o card de "Aguardando partida" (senão o
  trilho aparece livre com o candidato ruim na main); o QA separa a fase
  antes do merge da fase da partida; Agente+Humano é despachado; a
  retomada tem comando.
- As regras da 2ª revisão e da janela de 27/09 (logs/janelas/2026-09-27.md),
  uma por teste ou por linha de REGRAS_DAS_REVISOES: a coleta grava os dois
  config-hash que o G7 exige; a Concluída sai da fase 2 inteira; o degrau
  só de Python não pede janela; a janela conta com as aprovações "ask"; o
  que o papel diz que a guarda deixa, ela deixa (e o banco por cp ela
  barra); o aborto por processo sai do candidato antes de subir o
  container.
- As da 3ª revisão, com a decisão do PM de 27/09: o tech-manager mergeia o
  degrau de infra logo depois da fase 1 do QA, sem pausa de janela, e o
  que protege o jogo é o ff do checkout, que só o servidor faz, em janela;
  a janela vencida no meio não muda mais nada, mas ainda deve a volta (sai
  do candidato antes do docker start, e o G6 que faltou se completa na
  coleta); o portão imprime o código do preflight; o relógio é uma regra
  de caber (o que falta mais uma volta), e a Q5 tem teto de 30 min.
- As da 4ª revisão (R4): com o merge de infra a qualquer hora, a volta à
  main depois do revert é o ff sem janela feito em detach, com o delta
  conferido antes, e o `switch main` só roda no passo 3 (a main local
  ainda aponta para o candidato revertido); o relógio soma o boot medido
  no registro, e os 15 min do passo 8 são o limite de aborto.

Só leitura de arquivo versionado e a guarda em processo, com um checkout
falso no tmp_path: nada de processo, rede, Docker ou banco.
"""
import json
import re
import shlex
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tools.board.cli import ler_argumentos  # noqa: E402
from tools.board.modelo import STATUS  # noqa: E402

AGENTES = RAIZ / ".claude" / "agents"
AGENTS_MD = RAIZ / "AGENTS.md"
EVIDENCIA = RAIZ / "tools" / "evidencia_partida.py"
PYTHON = "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe"
REGISTRO = "C:/Users/Victor/Projetos/cs2-tracker/logs/janelas/<data>.md"
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
        "BOARD", "FREIO", "PRÓXIMO PASSO", "servidor refaz a coleta",
    ],
    "tech-manager": [
        "DECISÃO DE FILA:", "PR:", "MERGE:", "TAGS:", "BOARD", "RECLASSIFICADO:",
        "BLOQUEADO / PRECISA DO PM", "PRÓXIMO PASSO",
    ],
    "servidor": [
        "JANELA:", "RUNBOOK:", "PREFLIGHT:", "BACKUP E SNAPSHOT:", "MUDANÇA:", "G6:",
        "FECHAMENTO:", "RESULTADO:", f"REGISTRO: {REGISTRO}",
    ],
}

# Poucas invariantes por papel, as que definem o papel. O resto das regras
# vem com o motivo em REGRAS_DAS_REVISOES ou num teste próprio: lista longa
# de frases literais quebra a cada lição nova e desestimula manter o papel.
REGRAS_DO_PAPEL = {
    "dev": ["Não lê nem grava o board", "Não abre PR, não mergeia", "**Retomada**",
            "DEPOIS DO MERGE"],
    "qa": ["nunca edita código", "**Reprovação:**", "**Devolução técnica:**",
           "**Fase 2, card em `Aguardando partida`**"],
    "tech-manager": ["--merge --delete-branch", "Squash ou rebase, nunca", "candidato-N",
                     "**devolução técnica**"],
    "servidor": ["sem worktree", "**Snapshot**", "**Fechamento (checklist G6):**",
                 "**Candidato: ff do checkout para o candidato.**"],
}

# Regra que uma revisão do H1.6 mandou pôr no papel, com a origem. A = 1ª
# revisão da 2ª rodada (máquina de estados), B = lente B, R3 = 3ª revisão
# (bloqueantes novos 1 e 2, com a decisão do PM de 27/09); o que tem teste
# próprio abaixo não se repete aqui.
REGRAS_DAS_REVISOES = [
    ("A-B2 execução = janela tem lease", "tech-manager", "execução = janela; PM abre o servidor"),
    ("A-B2 o QA julga a janela na fase 1", "qa", "Card cuja execução foi a própria janela"),
    ("A-B2 o dev faz os docs do registro", "dev", "Card cuja execução foi a janela"),
    ("A-B3 smoke inconclusivo não é candidato no ar", "servidor",
     "o RESULTADO não é `candidato no ar`"),
    ("A-B3 smoke inconclusivo só com OK do Victor", "qa", "smoke INCONCLUSIVO só conta com o OK"),
    ("A-B5 Victor no PC para o ask", "servidor", "fica no PC para aprovar os comandos docker em ask"),
    ("A-B5 janela vencida no meio", "servidor", "**Janela vencida no meio:**"),
    ("A-B5 renovação é janela nova", "servidor", "Renovar é abrir janela nova"),
    ("R3-1 vencida não muda, mas deve a volta", "servidor",
     "nenhum passo de mudança, mas a volta continua devida e não leva portão"),
    ("R3-1 o G6 que faltou se completa na coleta", "servidor", "G6 completado na coleta"),
    ("R3-1 o QA aceita o G6 da coleta", "qa", "vale o G6 só de leitura que a coleta completou"),
    ("R3-2 o relógio é regra de caber", "servidor",
     "Antes do passo 4, some o que falta pelo runbook do card"),
    ("R3-2 a conta leva uma volta", "servidor", "fechamento e mais uma volta"),
    ("R3-2 teto da Q5 na abertura", "servidor", "Q5: teto de 30 min (runbook, pré-condição 2)"),
    ("R3 a janela não espera merge", "servidor", "a janela não espera merge"),
    ("R3 merge do degrau de infra sem pausa", "tech-manager",
     "mergeie logo depois da fase 1 do QA, a qualquer hora, sem pausa de janela"),
    ("R3 degrau de infra pede janela depois do merge", "tech-manager",
     '"PM: pedir janela ao Victor; o servidor faz o ff do candidato-N no passo 3"'),
    ("R3 trilho único no origin/main", "tech-manager",
     "no máximo um candidato mergeado e ainda não validado"),
    ("R4-1 alguém pede a volta do checkout depois do revert", "tech-manager",
     'PRÓXIMO PASSO: "PM: servidor devolve o checkout (Ff sem janela, delta sem infra)"'),
    ("R4-1 o ff sem janela não sai do detach", "servidor",
     "Em detach, o ff roda em detach mesmo, sem `switch main`"),
    ("R4-2 o boot medido vai para o registro", "servidor",
     "Grave no registro o tempo medido do recreate até o `Pronto`"),
    ("A-B7 banco sem cópia até o B0.6", "servidor", "banco sem cópia (guarda; B0.6)"),
    ("B-B1 degrau sem infra sem janela", "tech-manager", "**Degrau sem infra**"),
    ("B-B1 atualizar sem contradição", "tech-manager", "fora do `jogavel.py atualizar`"),
    ("B-B1 ff sem janela", "servidor", "**Ff sem janela**"),
    ("B-B5 a cópia do banco é do servidor", "servidor", "que é você quem faz"),
    ("A tag de volta sem papéis", "servidor", "Tag sem `.claude/agents` ou `.claude/settings.json`"),
    ("A worktree atrás da main (TM)", "tech-manager",
     "`git fetch origin && git switch --detach origin/main`"),
    ("A worktree atrás da main (QA)", "qa", "`git fetch origin && git switch --detach origin/main`"),
    ("A ff do checkout depois do merge", "tech-manager", "PM: ff do checkout principal"),
    ("A lease órfão", "tech-manager", "Lease órfão"),
    ("A 2 reprovações não se despacham", "tech-manager", "`Reprovações` abaixo de 2"),
    ("A saída 2/4 refaz a coleta", "qa", "o PRÓXIMO PASSO é o servidor refazer a coleta"),
    ("A diff só de comentário no delta", "servidor", "checar_so_comentarios"),
    ("A board sem semente", "tech-manager", "board ainda sem a semente do H1.9"),
    ("B nome de tag ocupado", "tech-manager", "`jogavel-AAAA-MM-DD-2`"),
    ("B revert sem QA é exceção", "tech-manager", 'exceção ao "depois do QA" do AGENTS.md'),
    ("B preflight 4 não para o TM", "tech-manager", "com 4 você segue no Offline"),
    ("B vigilância depois do PR #8", "servidor", "Desde o PR #8"),
]


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


def test_qa_nao_tem_edit_nem_write():
    # Bash e PowerShell ainda escrevem em disco: o que impede é a regra do
    # papel. A ferramenta só tira o caminho mais curto (Edit/Write).
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


# --------------------------------------------------------------- passagens de bastão


_COMANDOS_DO_BOARD = ("validar", "fila", "reclassificar", "criar", "mover", "historico")


def _comandos_do_board(texto):
    """Todo comando do tools.board citado no papel, em bloco ou em `crase`."""
    achados = []
    for bloco in _blocos_de_codigo(texto):
        achados += [linha.split("-m tools.board ", 1)[1] for linha in bloco.splitlines()
                    if "-m tools.board " in linha]
    prosa = re.sub(r"^```[^\n]*\n.*?^```", "", texto, flags=re.MULTILINE | re.DOTALL)
    for trecho in re.findall(r"`([^`\n]+)`", prosa):
        if "-m tools.board " in trecho:
            achados.append(trecho.split("-m tools.board ", 1)[1])
        elif trecho.split(" ", 1)[0] in _COMANDOS_DO_BOARD:
            achados.append(trecho)
    return [ler_argumentos(shlex.split(cmd)) + (cmd,) for cmd in achados]


@pytest.mark.parametrize("papel", ["tech-manager", "qa", "servidor"])
def test_todo_comando_do_board_passa_pelo_parser_do_cli(papel):
    # ler_argumentos é o parser do H1.3: opção que ele não conhece levanta
    # ErroBoard, e o agente ficaria preso num comando que o CLI recusa.
    comandos = _comandos_do_board(_texto(papel))
    assert comandos, f"{papel}.md não cita comando do board"
    for comando, opcoes, bruto in comandos:
        assert comando in _COMANDOS_DO_BOARD, bruto
        if "status" in opcoes:
            assert opcoes["status"] in STATUS, f"status fora dos oito: {bruto}"


def test_parser_dos_comandos_pega_opcao_que_o_cli_nao_conhece():
    from tools.board.modelo import ErroBoard
    with pytest.raises(ErroBoard):
        _comandos_do_board("`mover --card=<ID> --estado=Concluída`")


def test_g6_ou_g7_ruim_reprova_sem_tirar_o_card_de_aguardando_partida():
    # Com --status, o card sairia de "Aguardando partida": o NO_TRILHO do
    # modelo só olha o status, o trilho apareceria livre com o candidato
    # ruim na main e a fila despacharia o card antes do revert.
    comandos = [o for c, o, _ in _comandos_do_board(_texto("qa")) if c == "mover"]
    assert any(o.get("reprovacao") and "status" not in o for o in comandos)
    assert "fica em `Aguardando partida`, segurando o trilho" in _texto("qa")


def test_tech_manager_so_libera_o_trilho_depois_do_revert():
    comandos = [o for c, o, _ in _comandos_do_board(_texto("tech-manager")) if c == "mover"]
    depois_do_revert = [o for o in comandos if o.get("candidato") == "null"]
    assert depois_do_revert, "falta o mover que limpa o candidato depois do revert"
    assert all(o.get("status") == "Pronta para começar" and o.get("branch") == "null"
               and o.get("pr") == "null" for o in depois_do_revert)


def test_tech_manager_nao_segura_agente_mais_humano_pela_parte_do_victor():
    # A parte do Victor (janela, partida) vem DEPOIS do merge: exigir que
    # ela esteja feita antes do despacho trava o trilho B1 inteiro.
    texto = _texto("tech-manager")
    assert "vem depois do merge" in texto
    assert "`Agente+Humano` só com" not in texto


def test_servidor_tem_os_passos_0_a_11_da_janela():
    # A numeração é a do modelo de janela (runbook do B1.3r), mas o teste não
    # prende o papel aos títulos de um runbook de card: um passo novo no
    # runbook (o smoke corrigido, por exemplo) não quebra o H1.6.
    passos = re.findall(r"^(\d+)\. \*\*", _texto("servidor"), re.MULTILINE)
    assert passos == [str(n) for n in range(12)]


# --------------------------------------------------------------- 2ª revisão e janela de 27/09


def _secao(texto, inicio, fim):
    """Do `inicio` até a próxima ocorrência de `fim` depois dele."""
    ini = texto.index(inicio)
    corte = texto.find(fim, ini + len(inicio))
    return texto[ini:corte if corte >= 0 else None]


def _movers(papel):
    return [(o, bruto) for c, o, bruto in _comandos_do_board(_texto(papel)) if c == "mover"]


def _passos_do_servidor():
    return dict(re.findall(r"^(\d+)\. (.+)$", _texto("servidor"), re.MULTILINE))


@pytest.mark.parametrize("origem, papel, trecho", REGRAS_DAS_REVISOES,
                         ids=[r[0] for r in REGRAS_DAS_REVISOES])
def test_regra_da_revisao_esta_no_papel(origem, papel, trecho):
    assert trecho in _texto(papel), f"{papel}.md perdeu a regra {origem!r}"


ROTULO_CONFIG_HASH = ("docker inspect cs2-spike --format "
                      "'{{index .Config.Labels \"com.docker.compose.config-hash\"}}'")
HASH_DE_AGORA = 'cd "$RAIZ" && docker compose config --hash cs2-server'
PORTAO = ('"$PY" "$BK/preflight.py" --raiz "$RAIZ"; c=$?; [ $c -eq 4 ] || '
          '{ echo "JANELA FECHADA (preflight $c): não executei"; exit 1; }; docker stop cs2-spike')
VOLTA_PARA_A_TAG = 'git -C "$RAIZ" switch --detach <tag jogavel>'


def test_coleta_grava_os_dois_config_hash_que_o_g7_exige():
    # A-B1: sem --config-hash e --config-hash-janela o evidencia_partida.py
    # nunca dá OK (SEM EVIDÊNCIA por construção), e o candidato ficaria para
    # sempre em "Aguardando partida". A janela de 27/09 não gravou nenhum.
    ferramenta = EVIDENCIA.read_text(encoding="utf-8")
    assert '"--config-hash"' in ferramenta and '"--config-hash-janela"' in ferramenta
    servidor, qa = _texto("servidor"), _texto("qa")
    coleta = _secao(servidor, "## Coleta pós-partida", "\n## ")
    for trecho in (ROTULO_CONFIG_HASH, HASH_DE_AGORA, "config-hash-janela.txt",
                   "config-hash.txt", "head.txt"):
        assert trecho in coleta, trecho
    g6 = _passos_do_servidor()["9"]
    assert "config-hash da janela" in g6 and "config --hash cs2-server" in g6
    comando = re.search(r"tools/evidencia_partida\.py --log [^\n]*", qa).group(0)
    assert "--config-hash <h>" in comando and "--config-hash-janela <h>" in comando
    assert "config-hash.txt" in qa and "config-hash-janela.txt" in qa


@pytest.fixture
def guarda_no_checkout(tmp_path):
    """A guarda de verdade (tools/hooks/guarda.py), num checkout falso."""
    hooks = str(RAIZ / "tools" / "hooks")
    if hooks not in sys.path:
        sys.path.insert(0, hooks)
    import guarda
    principal = tmp_path / "principal"
    (principal / ".git").mkdir(parents=True)
    prefixo = (f"export MSYS_NO_PATHCONV=1; RAIZ={principal.as_posix()}; PY={PYTHON}; "
               f"BK={(tmp_path / 'backups' / 'b1.3r').as_posix()}; ")

    def decidir(comando, preflight=4):
        evento = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                  "tool_input": {"command": prefixo + comando}, "cwd": str(principal)}
        codigo, erro, _ = guarda.decidir(evento, principal=principal.as_posix(),
                                         preflight=lambda: preflight,
                                         arquivo_env=str(tmp_path / "nao-existe.env"))
        return codigo, erro
    return decidir


@pytest.mark.parametrize("comando", [
    PORTAO, ROTULO_CONFIG_HASH, HASH_DE_AGORA, "docker inspect cs2-spike --format '{{.Created}}'",
])
def test_o_que_o_servidor_manda_rodar_passa_pela_guarda(guarda_no_checkout, comando):
    # A janela de 27/09 parou na guarda (cópia do banco, docker logs depois do
    # boot): comando que o papel manda rodar precisa passar por ela. O portão
    # (A-B5) confere a janela na mesma chamada, e uma aprovação "ask" atrasada
    # não age com a janela vencida.
    assert comando in _texto("servidor")
    codigo, erro = guarda_no_checkout(comando)
    assert codigo == 0, erro


def test_o_papel_nao_copia_o_banco_por_cp_e_a_guarda_barra_a_copia(guarda_no_checkout):
    # A-B7 e B-B3: o passo 2 dizia "ou só cópia com sha256", que a guarda barra;
    # o servidor pararia no meio da janela, com o relógio correndo.
    assert not re.search(r"\bcp\b[^`\n]*cs2_tracker\.db", _texto("servidor"))
    assert guarda_no_checkout('cp -p "$RAIZ/cs2_tracker.db" "$BK/"')[0] == 2
    codigo, erro = guarda_no_checkout('cp -p "$RAIZ/docker/events-live/current.jsonl" "$BK/"')
    assert codigo == 0, erro  # o que o passo 2 manda copiar, a guarda deixa


def test_concluida_sem_caminho_de_jogo_espera_o_depois_do_merge_e_o_historico_guarda_o_merge():
    # A-B2: com critério DEPOIS DO MERGE, card sem caminho de jogo ia direto a
    # Concluída e a partida nunca era julgada. A-nb: merge e tag sem --texto
    # sumiam do Histórico.
    movers = _movers("tech-manager")
    assert any(o.get("status") == "Aguardando partida" and "candidato" not in o
               for o, _ in movers)
    assert ("sem caminho de jogo e sem critério DEPOIS DO MERGE: `mover --card=<ID> "
            "--status=Concluída") in _texto("tech-manager")
    for opcoes, bruto in movers:
        if opcoes.get("status") in ("Concluída", "Aguardando partida"):
            assert "texto" in opcoes, bruto


def test_concluida_do_degrau_sai_da_fase_2_inteira():
    # A-B3: a Concluída olhava só o "G7 OK", e o resto do DEPOIS DO MERGE (o
    # smoke INCONCLUSIVO de 27/09, por exemplo) passava sem veredito.
    qa, tm = _texto("qa"), _texto("tech-manager")
    fase2 = [o["texto"] for c, o, _ in _comandos_do_board(qa)
             if str(o.get("texto", "")).startswith("FASE 2: ")]
    assert {t.split(";")[0] for t in fase2} >= {"FASE 2: APROVADO", "FASE 2: REPROVADO"}
    assert all("partida <data>" in t and "HEAD <sha" in t for t in fase2)
    assert "todo critério DEPOIS DO MERGE do card ATENDIDO" in qa
    assert "**Fase 2 APROVADO:**" in tm and "**G7 OK:**" not in tm


def test_merge_do_degrau_de_infra_sai_antes_da_janela_e_o_passo_3_e_so_o_ff():
    # Decisão do PM de 27/09 (R3-2): a pausa de merge dentro da janela
    # (servidor → PM → TM → PM → servidor) nunca cabia numa Q5 e fazia todo
    # degrau de infra esperar uma Q4. O candidato continua protegido porque
    # só o servidor o traz ao checkout principal, pelo ff, em janela: o ff
    # sem janela recusa infra, e o boot só aplica o que está no checkout.
    tm, servidor = _texto("tech-manager"), _texto("servidor")
    for velho in ("## Na pausa da janela", "aguarda janela", "retome a janela", "pausa da janela>"):
        assert velho not in tm, velho
    for velho in ("aguardando merge", "**Pausa para o merge", "retome a janela"):
        assert velho not in servidor, velho
    infra = next(x for x in tm.splitlines() if "**Degrau de infra**" in x)
    assert "sem pausa de janela" in infra and "o ff sem janela recusa infra" in infra
    passo3 = _passos_do_servidor()["3"]
    assert passo3.startswith("**Candidato: ff do checkout para o candidato.**")
    assert "já está no `origin/main`, com a tag `candidato-N`" in passo3
    assert "merge --ff-only origin/main" in passo3 and "sem ff, feche sem mudança" in passo3
    ff_sem_janela = next(x for x in servidor.splitlines() if "**Ff sem janela**" in x)
    assert "sem infra" in ff_sem_janela and "Infra no delta" in ff_sem_janela


def test_janela_vencida_no_meio_ainda_deve_a_volta_e_sai_do_candidato_antes_do_start():
    # R3-1: "nenhum passo novo; feche só por RCON" deixava o checkout no
    # candidato depois do ff do passo 3, e o `compose up -d` do próximo
    # start_match aplicaria o candidato sem snapshot nem G6. Com o container
    # parado não há RCON, e depois do 7 o G6 incompleto prendia o card.
    vencida = _secao(_texto("servidor"), "**Janela vencida no meio:**", "\n**")
    antes, entre, depois = (vencida[vencida.index(m):] for m in
                            ("antes do passo 3", "entre o ff do 3 e o recreate do 7",
                             "do 7 em diante"))
    assert "nada a desfazer" in antes.split("\n")[0]
    assert "`docker start cs2-spike` se ele parou" in antes.split("\n")[0]
    linha = entre.split("\n")[0]
    assert VOLTA_PARA_A_TAG in linha and linha.index(VOLTA_PARA_A_TAG) < linha.index(
        "docker start cs2-spike")
    linha = depois.split("\n")[0]
    assert "feche por RCON" in linha and "G6 `FALTA` no registro" in linha
    assert "se completa na coleta, com preflight 0" in linha
    coleta = _secao(_texto("servidor"), "## Coleta pós-partida", "\n## ")
    assert "G6 `FALTA`" in coleta and "G6 completado na coleta" in coleta
    assert "apague a marca" in vencida


def test_portao_imprime_o_codigo_do_preflight():
    # R3-1: o mesmo "JANELA FECHADA" para preflight 3 e para janela vencida
    # deixava o agente seguir o ramo errado; o código e o motivo dizem qual.
    servidor = _texto("servidor")
    assert PORTAO in servidor and 'echo "JANELA FECHADA (preflight $c)' in PORTAO
    portao = _secao(servidor, "**Portão em cada escrita.**", "\n\n")
    assert "3 por processo é o aborto por processo" in portao
    assert "0, ou 3 só pelo `current.jsonl`, é a janela vencida" in portao


def test_relogio_e_regra_de_caber_e_nao_numero_fixo():
    # R3-2: "passo 4 com 25 min" e "11 até o minuto 35" não comportavam o boot,
    # o smoke e a volta; o teto de 30 min da Q5 tinha sumido. R4-2: somar o
    # limite de aborto (15 min) como boot, duas vezes, dava ~40 min antes do
    # G6: nada cabia numa Q5 e o degrau de infra prendia o trilho. O boot da
    # janela do B1.4 levou ~32 s.
    servidor = _texto("servidor")
    for velho in ("Não comece o passo 4 com menos de 25 min", "até o minuto 35"):
        assert velho not in servidor, velho
    relogio = _secao(servidor, "**Relógio: cabe ou não.**", "\n\n")
    for parcela in ("parar e snapshot", "boot medido", "G6", "smoke se o card exige",
                    "fechamento e mais uma volta", "outro boot medido"):
        assert parcela in relogio, parcela
    assert "boot até 15 min" not in relogio
    assert "Boot medido é o tempo do último recreate no registro, com folga" in relogio
    assert "Os 15 min do passo 8 são o limite de aborto, não a estimativa" in relogio
    assert "limite de aborto" in _passos_do_servidor()["8"]
    assert "+ 45 min na Q4, + 30 na Q5" in relogio and "feche sem mudança" in relogio
    assert relogio.index(VOLTA_PARA_A_TAG) < relogio.index("o passo 11")
    abertura = _secao(servidor, "**Abertura.**", "\n\n")
    assert "Q5: teto de 30 min (runbook, pré-condição 2)" in abertura


DELTA = 'git -C "$RAIZ" diff --stat HEAD origin/main'
FF = 'git -C "$RAIZ" merge --ff-only origin/main'
RUNBOOK_B13 = RAIZ / "docs" / "runbooks" / "b1.3-cssharp-1.0.375.md"


def test_switch_main_so_no_passo_3_e_a_volta_do_revert_confere_o_delta_antes_do_ff():
    # R4-1: depois do revert, a main local ainda aponta para o candidato que
    # falhou, e o merge de infra sai a qualquer hora (decisão do PM, 27/09).
    # A volta por `fetch && switch main && merge --ff-only`, sem olhar o
    # delta, traria ao checkout, fora de janela, um degrau de infra mergeado
    # nesse meio-tempo (a retomada do card), e o `compose up -d` do próximo
    # start_match o subiria sem snapshot nem G6. Um `switch main` solto põe o
    # checkout no próprio candidato que falhou.
    servidor = _texto("servidor")
    for achado in re.finditer(r"switch main", servidor):
        linha = servidor[servidor.rfind("\n", 0, achado.start()) + 1:
                         servidor.find("\n", achado.end())]
        antes = servidor[achado.start() - 5:achado.start()]
        depois = servidor[achado.end():achado.end() + 45]
        assert (linha.startswith("3. ") or antes == "sem `"
                or "`, este só no passo 3, dentro da janela" in depois), linha
    assert "a `main` local ainda aponta para o candidato revertido" in servidor
    volta = _secao(servidor, "**Abortar e voltar**", "\n\n")
    volta = volta[volta.index("Depois do merge do revert"):]
    assert "a volta à main é o **Ff sem janela**, feito ainda em detach" in volta
    assert volta.index(DELTA) < volta.index(FF)
    assert "com infra no delta" in volta and "fique na tag até o passo 3" in volta
    ff_sem_janela = next(x for x in servidor.splitlines() if "**Ff sem janela**" in x)
    assert ff_sem_janela.index(DELTA) < ff_sem_janela.index(FF)

    runbook = RUNBOOK_B13.read_text(encoding="utf-8")
    assert "É o único lugar do `switch main`" in _secao(runbook, "### 3. ", "\n### ")
    volta_rb = _secao(runbook, "### Depois de qualquer volta", "\n## ")
    comandos = "\n".join(re.findall(r"^[ \t]*```bash\n(.*?)^[ \t]*```", volta_rb,
                                    re.MULTILINE | re.DOTALL))
    assert "switch main" not in comandos
    assert comandos.index(DELTA) < comandos.index(FF)
    assert "Com infra no delta" in volta_rb and "fique na tag" in volta_rb


@pytest.mark.parametrize("comando", [DELTA, FF])
def test_a_volta_do_revert_passa_pela_guarda_com_preflight_0(guarda_no_checkout, comando):
    # R4-1: a volta depois do revert é fora de janela, com preflight 0.
    assert comando in _texto("servidor")
    codigo, erro = guarda_no_checkout(comando, preflight=0)
    assert codigo == 0, erro


@pytest.mark.parametrize("preflight", [0, 3])
@pytest.mark.parametrize("comando", [VOLTA_PARA_A_TAG, "docker start cs2-spike"])
def test_a_volta_da_janela_vencida_passa_pela_guarda_sem_janela(guarda_no_checkout, comando,
                                                               preflight):
    # R3-1: a volta não leva portão e roda com a janela vencida (preflight 0,
    # ou 3 pelo current.jsonl do boot): a guarda não pode barrar nenhum dos dois.
    assert comando in _texto("servidor")
    codigo, erro = guarda_no_checkout(comando.replace("<tag jogavel>", "jogavel-2026-09-27"),
                                      preflight=preflight)
    assert codigo == 0, erro


def test_tech_manager_nao_manda_e_proibe_o_atualizar():
    # B-B1 e kalendas L65: "nunca muda pelas suas mãos" proibia o `atualizar`
    # que o mesmo arquivo manda rodar; e degrau só de Python pedia janela.
    tm = _texto("tech-manager")
    assert "nunca muda pelas suas mãos" not in tm
    assert "**Degrau de infra** (`Infra: true`" in tm


def test_aborto_por_processo_sai_do_candidato_antes_de_subir_o_container():
    # A-B6: com o container parado e o checkout no candidato, o `compose up -d`
    # do start_match recriaria o container com o candidato, sem snapshot.
    aborto = _secao(_texto("servidor"), "**Aborto por processo**", "\n**")
    assert aborto.index("switch --detach <tag jogavel>") < aborto.index("docker start cs2-spike")
    assert "o `docker logs` espera o preflight 0" in aborto


def test_smoke_e_fechamento_cuidam_do_bot_join_after_player():
    # B-B4: sem `bot_join_after_player 0` os bots não entram sem humano, e o
    # smoke de 27/09 deu INCONCLUSIVO; o fechamento devolve o valor de antes.
    passos = _passos_do_servidor()
    assert "`bot_join_after_player`" in passos["1"]
    assert "`bot_join_after_player 0` antes do `bot_quota`" in passos["10"]
    assert "`bot_join_after_player` nos valores de antes" in passos["11"]


def test_coleta_com_preflight_3_nao_prende_a_sessao_do_pm():
    # B-B5: "espere a partida acabar" segurava a conversa com o Victor por
    # tempo indefinido; ele joga 2 ou 3 mapas seguidos.
    coleta = _secao(_texto("servidor"), "## Coleta pós-partida", "\n## ")
    assert "espere a partida acabar" not in coleta.lower()
    assert "RESULTADO `coleta adiada: preflight 3" in coleta


@pytest.mark.parametrize("papel", PAPEIS)
def test_registro_da_janela_pelo_caminho_absoluto(papel):
    # O QA roda num worktree, onde logs/ não existe: o caminho relativo dá um
    # SEM EVIDÊNCIA falso no G6.
    assert not re.findall(r"(?<!cs2-tracker/)logs/janelas/<data>", _texto(papel))


def test_terceira_devolucao_fica_gravada_e_o_revert_sai_em_pt_br():
    # A-nb: "não devolva: escale" deixava o card segurando o trilho, e o aviso
    # de 3 devoluções do validar nunca disparava. O `git revert` cru gera
    # commit em inglês, sem "(card <ID>)".
    assert any(o.get("status") == "Bloqueada" and o.get("devolucao")
               for o, _ in _movers("tech-manager"))
    commit = re.search(r'git revert --no-commit -m 1 <merge> && git commit -m "([^"]+)"',
                       _texto("tech-manager"))
    assert commit and commit.group(1).endswith("(card <ID>)")
