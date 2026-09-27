"""
Testes do CLI do board (card H1.3), portados de kalendas/scripts/lib/board.test.ts
e estendidos com os campos do cs2-tracker: Card, Sprint, Verificação,
Caminho de jogo, trilho único e preflight na fila.

Tudo em tmp_path: o board real (docs/board-cs2 do checkout principal) nunca
é lido nem escrito, o relógio é fixo e o preflight é injetado.
"""
import json
import re
import runpy
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tools.board import cli  # noqa: E402
from tools.board.frontmatter import (  # noqa: E402
    acrescentar_historico,
    definir_propriedade,
    formatar_escalar,
    ler_frontmatter,
)
from tools.board.modelo import (  # noqa: E402
    Quadro,
    carregar,
    classificar,
    fila,
    reclassificar,
    validar,
)

AGORA = datetime(2026, 9, 26, 23, 18)
ROLLBACK = "\n\n## Rollback\n\nReverter o merge e rodar `jogavel.py voltar`."


def nome_de(c):
    return f"{str(c['ordem']).replace('.', ',')} - {c['titulo']}"


def texto_card(c):
    def links(nomes):
        if not nomes:
            return " []"
        return "".join(f'\n  - "[[{n}]]"' for n in nomes)

    jogo = c.get("jogo", False)
    campos = {
        "ID": c.get("card", f"H1.{round(c['ordem'] * 10)}"),
        "Status": c["status"],
        "Sprint": c.get("sprint", "H1"),
        "Ordem": c["ordem"],
        "Camada": c.get("camada", "Infra/Harness"),
        "Verificação": c.get("verificacao", "Offline"),
        "Executor": c.get("executor", "Agente"),
        "Caminho de jogo": "true" if jogo else "false",
        "Infra": c.get("infra", "false"),
        "Janela": c.get("janela", "nenhuma"),
        "Partida": c.get("partida", "—"),
        "Reprovada": c.get("reprovada", "false"),
        "Reprovações": c.get("reprovacoes", "null"),
        "Devoluções": c.get("devolucoes", "null"),
        "Branch": "null",
    }
    linhas = ["---"]
    for chave, valor in campos.items():
        if valor == "omitir":
            continue
        linhas.append(f"{chave}: {'null' if valor is None else valor}")
    linhas += [f"Bloqueia:{links(c.get('bloqueia'))}", f"Depende de:{links(c.get('depende'))}"]
    corpo = c.get("corpo", "**Problema:** algo." + (ROLLBACK if jogo else ""))
    return "\n".join(linhas + ["---", corpo, ""])


def montar(tmp_path, cards):
    board = tmp_path / "board-cs2"
    board.mkdir(parents=True)
    for c in cards:
        (board / f"{nome_de(c)}.md").write_bytes(texto_card(c).encode("utf-8"))
    (board / "Painel.md").write_text("[[Board.base]]\n", encoding="utf-8")
    return board


def rodar(board, *argv, preflight=lambda: 0):
    out, err = [], []
    codigo = cli.main([*argv, f"--board={board}"], agora=lambda: AGORA,
                      preflight=preflight, log=out.append, erro=err.append)
    return SimpleNamespace(codigo=codigo, out="\n".join(out), err="\n".join(err))


def ler(board, nome):
    return (board / f"{nome}.md").read_bytes().decode("utf-8")


def props(board, nome):
    return ler_frontmatter(ler(board, nome))


# Grafo de referência: A concluído; B depende de A (vira Pronta); C depende de B (cadeia);
# D depende de B e de E (2 pendentes); F depende de C, que depende de B.
A = {"ordem": 1, "titulo": "A", "status": "Concluída", "bloqueia": ["2 - B"]}
B = {"ordem": 2, "titulo": "B", "status": "Bloqueada", "depende": ["1 - A"],
     "bloqueia": ["3 - C", "4 - D"]}
C = {"ordem": 3, "titulo": "C", "status": "Backlog", "depende": ["2 - B"], "bloqueia": ["6 - F"]}
D = {"ordem": 4, "titulo": "D", "status": "Backlog", "depende": ["2 - B", "5 - E"]}
E = {"ordem": 5, "titulo": "E", "status": "Em andamento", "bloqueia": ["4 - D"]}
F = {"ordem": 6, "titulo": "F", "status": "Backlog", "depende": ["3 - C"]}


# ---------------------------------------------------------------------------
# frontmatter
# ---------------------------------------------------------------------------

def test_le_escalares_aspas_numero_com_ponto_booleanos_null_e_listas_de_wikilink():
    lido = ler_frontmatter(texto_card({**B, "ordem": 90.5, "card": "B1.3r", "sprint": "B1"}))
    assert lido["Status"] == "Bloqueada"
    assert lido["ID"] == "B1.3r"
    assert lido["Ordem"] == 90.5
    assert lido["Verificação"] == "Offline"
    assert lido["Caminho de jogo"] is False
    assert lido["Partida"] == "—"
    assert lido["Reprovações"] is None
    assert lido["Depende de"] == ["[[1 - A]]"]
    assert lido["Bloqueia"] == ["[[3 - C]]", "[[4 - D]]"]


def test_definir_propriedade_troca_so_a_linha_e_preserva_o_resto_byte_a_byte():
    antes = texto_card(B)
    depois = definir_propriedade(antes, "Status", "Pronta para começar")
    assert depois == antes.replace("Status: Bloqueada", "Status: Pronta para começar")


def test_definir_propriedade_troca_lista_inteira_de_lista_para_vazia_e_de_volta():
    vazia = definir_propriedade(texto_card(B), "Bloqueia", [])
    assert ler_frontmatter(vazia)["Bloqueia"] == []
    assert "Bloqueia: []\nDepende de:" in vazia
    de_volta = definir_propriedade(vazia, "Bloqueia", ["[[9 - Z]]"])
    assert ler_frontmatter(de_volta)["Bloqueia"] == ["[[9 - Z]]"]


def test_definir_propriedade_com_ancora_poe_a_chave_nova_logo_depois_dela():
    texto = texto_card({**B, "executor": "omitir"})
    depois = definir_propriedade(texto, "Executor", "Agente", depois_de="Verificação")
    assert "Verificação: Offline\nExecutor: Agente\nCaminho de jogo: false" in depois
    # Âncora ausente: vai para o fim do frontmatter.
    no_fim = definir_propriedade(texto, "Executor", "Agente", depois_de="Inexistente")
    assert "Executor: Agente\n---" in no_fim


def test_definir_propriedade_preserva_crlf():
    crlf = texto_card(B).replace("\n", "\r\n")
    depois = definir_propriedade(crlf, "Status", "Backlog")
    assert "\r\n" in depois and "\n" not in depois.replace("\r\n", "")


def test_formatar_escalar_poe_aspas_so_quando_o_yaml_leria_outra_coisa():
    assert formatar_escalar("B1.3r") == "B1.3r"
    assert formatar_escalar("—") == "—"
    assert formatar_escalar("feat/H1.3-board-cli") == "feat/H1.3-board-cli"
    assert formatar_escalar("true") == '"true"'
    assert formatar_escalar("12") == '"12"'
    assert formatar_escalar("a: b") == '"a: b"'
    assert formatar_escalar("") == '""'
    assert formatar_escalar(11.5) == "11.5"
    assert formatar_escalar(False) == "false"
    assert formatar_escalar(None) == "null"


@pytest.mark.parametrize("valor", ["a\nb", "a\r\nb", "tab\taqui", "nul\x00", "del\x7f"])
def test_formatar_escalar_poe_aspas_em_caractere_de_controle_e_volta_igual(valor):
    formatado = formatar_escalar(valor)
    assert formatado.startswith('"') and "\n" not in formatado and "\r" not in formatado
    texto = definir_propriedade(texto_card(B), "Branch", valor)
    lido = ler_frontmatter(texto)
    assert lido["Branch"] == valor and lido["Status"] == "Bloqueada"


def test_propriedade_limpa_no_obsidian_le_como_null_e_lista_com_item_como_lista():
    texto = texto_card(B).replace("Branch: null", "Branch:").replace(
        "Reprovações: null", "Reprovações:")
    lido = ler_frontmatter(texto)
    assert lido["Branch"] is None and lido["Reprovações"] is None
    assert lido["Depende de"] == ["[[1 - A]]"]
    vazia = ler_frontmatter(texto.replace('Depende de:\n  - "[[1 - A]]"', "Depende de:"))
    assert vazia["Depende de"] is None


def test_validar_aceita_propriedade_limpa_no_obsidian(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    caminho = board / "2 - B.md"
    texto = caminho.read_bytes().decode("utf-8")
    for chave in ("Reprovações", "Devoluções", "Bloqueia"):
        texto = re.sub(rf"^{chave}:.*$", f"{chave}:", texto, flags=re.MULTILINE)
    texto = texto.replace("Branch: null", "Branch:\nPR:\nCandidato:\nCusto:")
    caminho.write_bytes(texto.encode("utf-8"))
    resultado = rodar(board, "validar")
    assert resultado.codigo == 0, resultado.out
    assert "ERRO" not in resultado.out


def test_acrescentar_historico_cria_a_secao_e_acrescenta_no_fim():
    criado = acrescentar_historico(texto_card(B), "- **26/09/2026 23:18 · TM** — um")
    assert criado.endswith("## Histórico\n\n- **26/09/2026 23:18 · TM** — um\n")
    duas = acrescentar_historico(criado, "- **26/09/2026 23:19 · TM** — dois")
    assert duas.endswith("— um\n- **26/09/2026 23:19 · TM** — dois\n")


def test_acrescentar_historico_entra_antes_da_secao_seguinte():
    texto = texto_card({**B, "corpo": "## Histórico\n\n- velho\n\n## Notas\n\ntexto"})
    assert "- velho\n- novo\n\n## Notas" in acrescentar_historico(texto, "- novo")


# ---------------------------------------------------------------------------
# classificar: os limiares do board_schema
# ---------------------------------------------------------------------------

def _quadro(tmp_path, cards):
    return carregar(montar(tmp_path, cards))


def test_zero_pendentes_vira_pronta_mesmo_com_dependencia_concluida(tmp_path):
    q = _quadro(tmp_path, [A, B])
    assert classificar(q, q.get("2 - B")) == "Pronta para começar"


def test_uma_pendente_sem_pendentes_proprias_vira_bloqueada(tmp_path):
    q = _quadro(tmp_path, [A, B, C])
    assert classificar(q, q.get("3 - C")) == "Bloqueada"


def test_uma_pendente_com_cadeia_vira_backlog(tmp_path):
    q = _quadro(tmp_path, [{**A, "status": "Em testes"}, B, C])
    assert classificar(q, q.get("3 - C")) == "Backlog"


@pytest.mark.parametrize("status", ["Em andamento", "Em testes", "PR aberta", "Aguardando partida"])
def test_card_em_curso_ou_aguardando_partida_conta_como_pendente(tmp_path, status):
    q = _quadro(tmp_path, [{**A, "status": status}, B])
    assert classificar(q, q.get("2 - B")) == "Bloqueada"


def test_duas_pendentes_vira_backlog(tmp_path):
    q = _quadro(tmp_path, [A, B, D, E])
    assert classificar(q, q.get("4 - D")) == "Backlog"


def test_link_para_card_que_nao_existe_conta_como_pendente(tmp_path):
    q = _quadro(tmp_path, [{**B, "depende": ["77 - Sumiu"]}])
    assert q.pendentes(q.get("2 - B")) == ["77 - Sumiu"]


def test_resolver_aceita_ordem_com_virgula_ou_ponto_nome_wikilink_e_card(tmp_path):
    q = Quadro(_quadro(tmp_path, [{**B, "ordem": 0.5, "titulo": "Meio"}]).cartoes)
    for ref in ("0,5", "0.5", "0,5 - Meio", "[[0,5 - Meio]]", "H1.5"):
        assert q.resolver(ref).nome == "0,5 - Meio"


# ---------------------------------------------------------------------------
# reclassificar
# ---------------------------------------------------------------------------

def test_reclassificar_promove_direto_e_segunda_ordem_sem_tocar_em_andamento(tmp_path):
    q = _quadro(tmp_path, [A, B, C, D, E, F])
    mudancas = reclassificar(q, q.get("1 - A"))
    assert [(m.cartao.nome, m.de, m.para) for m in mudancas] == [
        ("2 - B", "Bloqueada", "Pronta para começar"),
        ("3 - C", "Backlog", "Bloqueada"),
    ]


def test_reclassificar_grava_status_escreve_historico_com_o_relogio_e_rele(tmp_path):
    board = montar(tmp_path, [A, B, C, D, E, F])
    resultado = rodar(board, "reclassificar", "--concluido=1")
    assert resultado.codigo == 0, resultado.err
    assert props(board, "2 - B")["Status"] == "Pronta para começar"
    assert props(board, "3 - C")["Status"] == "Bloqueada"
    assert props(board, "4 - D")["Status"] == "Backlog"
    assert props(board, "6 - F")["Status"] == "Backlog"
    assert (
        "- **26/09/2026 23:18 · TM** — Reclassificado de `Bloqueada` para `Pronta para começar` "
        "com a conclusão do [[1 - A]] (sem dependência pendente). Feito por "
        "`tools.board reclassificar`."
    ) in ler(board, "2 - B")
    # Sem "python": o Histórico não pode ensinar o interpretador do sistema (AGENTS.md).
    assert "python -m" not in ler(board, "2 - B")


def test_reclassificar_aceita_o_card_do_plano_e_seco_nao_grava(tmp_path):
    board = montar(tmp_path, [A, B])
    antes = ler(board, "2 - B")
    resultado = rodar(board, "reclassificar", "--concluido=H1.10", "--seco")
    assert resultado.codigo == 0
    assert "2 · Bloqueada → Pronta para começar" in resultado.out
    assert ler(board, "2 - B") == antes


def test_reclassificar_recusa_card_fora_de_concluida(tmp_path):
    board = montar(tmp_path, [{**A, "status": "Aguardando partida", "jogo": True}, B])
    resultado = rodar(board, "reclassificar", "--concluido=1")
    assert resultado.codigo == 1
    assert "Mova para Concluída antes" in resultado.err


def test_reclassificar_seco_antes_do_merge_simula_sem_gravar(tmp_path):
    board = montar(tmp_path, [{**A, "status": "PR aberta"}, B])
    antes = ler(board, "2 - B")
    resultado = rodar(board, "reclassificar", "--concluido=1", "--seco")
    assert resultado.codigo == 0
    assert "simulação" in resultado.out
    assert "2 · Bloqueada → Pronta para começar" in resultado.out
    assert ler(board, "2 - B") == antes


def test_reclassificar_avisa_quando_promove_card_sem_executor(tmp_path):
    board = montar(tmp_path, [A, {**B, "executor": None}])
    assert "PREENCHA O Executor" in rodar(board, "reclassificar", "--concluido=1").out


# ---------------------------------------------------------------------------
# validar
# ---------------------------------------------------------------------------

def _mensagens(board, tudo=False):
    return [f"{p.nivel}:{p.mensagem}" for p in validar(carregar(board), tudo=tudo)]


def test_validar_acusa_valores_fora_dos_exatos(tmp_path):
    board = montar(tmp_path, [
        A,
        {**B, "status": "Pronta", "camada": "Ui", "executor": "Robô", "verificacao": "Remota",
         "janela": "pre", "partida": "BO3", "reprovada": "sim", "infra": "talvez"},
        {"ordem": 7, "titulo": "Sem executor", "status": "Backlog", "executor": "omitir"},
    ])
    mensagens = _mensagens(board)
    for esperado in (
        'erro:Status "Pronta" não é um dos oito',
        'erro:Camada "Ui" fora da lista (Infra/Harness · Bots/Servidor · Captura · Dados · '
        "Orquestração · TUI · Web · Docs/KB)",
        'erro:Executor "Robô" fora da lista (Agente · Humano · Agente+Humano)',
        'erro:Verificação "Remota" fora da lista (Offline · Servidor · Partida)',
        'erro:Janela "pre" fora da lista (nenhuma · pré · pós · dados)',
        'erro:Partida "BO3" fora da lista (— · leve · MD3 · MD3-browser)',
        'erro:Reprovada "sim" não é true/false',
        'erro:Infra "talvez" não é true/false',
        "erro:Executor ausente (Agente · Humano · Agente+Humano)",
    ):
        assert esperado in mensagens


def test_validar_confere_ordem_com_o_nome_e_so_olha_concluidos_com_tudo(tmp_path):
    board = montar(tmp_path, [A])
    (board / "9 - Nome errado.md").write_text(
        texto_card({**A, "ordem": 8, "titulo": "x", "card": "H1.8"}), encoding="utf-8")
    assert not any("nome do arquivo" in m for m in _mensagens(board))
    assert "erro:nome do arquivo não começa com a Ordem (8 - …)" in _mensagens(board, tudo=True)


def test_validar_acusa_ordem_e_card_repetidos_e_card_fora_do_sprint(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 3, "titulo": "x", "status": "Backlog", "card": "H1.3"},
        {"ordem": 4, "titulo": "y", "status": "Backlog", "card": "H1.3"},
        {"ordem": 5, "titulo": "z", "status": "Backlog", "card": "B1.3r"},
        {"ordem": 6, "titulo": "w", "status": "Backlog", "card": "h1-6"},
    ])
    (board / "5 - repetida.md").write_text(
        texto_card({"ordem": 5, "titulo": "r", "status": "Backlog", "card": "H1.9"}),
        encoding="utf-8")
    mensagens = _mensagens(board)
    assert mensagens.count("erro:ID H1.3 repetido") == 2
    assert mensagens.count("erro:Ordem 5 repetida") == 2
    assert 'erro:ID "B1.3r" não é do Sprint "H1"' in mensagens
    assert 'erro:ID "h1-6" fora do formato do plano (ex.: B1.3r)' in mensagens


def test_validar_exige_rollback_no_caminho_de_jogo_e_infra_dentro_dele(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 1, "titulo": "sem rollback", "status": "Backlog", "jogo": True,
         "corpo": "**Problema:** x."},
        {"ordem": 2, "titulo": "infra solta", "status": "Backlog", "infra": "true"},
        {"ordem": 3, "titulo": "com rollback", "status": "Backlog", "jogo": True},
    ])
    problemas = [(p.cartao, p.mensagem) for p in validar(carregar(board))]
    assert ("1 - sem rollback", 'caminho de jogo sem a seção "## Rollback", que é obrigatória') \
        in problemas
    assert ("2 - infra solta", "Infra true exige Caminho de jogo true (infra é caminho de jogo)") \
        in problemas
    assert not any(nome == "3 - com rollback" and "Rollback" in m for nome, m in problemas)


def test_validar_acusa_link_quebrado_e_avisa_espelho_e_freios(tmp_path):
    board = montar(tmp_path, [
        {**A, "bloqueia": []},
        {**B, "depende": ["1 - A", "77 - Sumiu"], "bloqueia": [], "reprovacoes": 2,
         "devolucoes": 3},
        {"ordem": 9, "titulo": "espera", "status": "Aguardando partida"},
    ])
    mensagens = _mensagens(board)
    assert "erro:Depende de [[77 - Sumiu]], que não existe" in mensagens
    assert "aviso:Depende de [[1 - A]], mas ele não lista este card em Bloqueia" in mensagens
    assert "aviso:2 reprovações: vai para a pauta do Victor" in mensagens
    assert "aviso:3 devoluções: o card sai do sprint" in mensagens
    assert ('aviso:"Aguardando partida" é só de caminho de jogo; sem ele, o merge leva a '
            "Concluída") in mensagens


def test_validar_avisa_trilho_unico_com_dois_cards_de_caminho_de_jogo_em_curso(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 1, "titulo": "um", "status": "Em testes", "jogo": True},
        {"ordem": 2, "titulo": "dois", "status": "Aguardando partida", "jogo": True},
        {"ordem": 3, "titulo": "fora", "status": "Em andamento"},
    ])
    trilho = [p for p in validar(carregar(board)) if p.mensagem.startswith("trilho único")]
    assert [p.cartao for p in trilho] == ["1 - um", "2 - dois"]
    assert all(p.nivel == "aviso" and "2 cards de caminho de jogo" in p.mensagem for p in trilho)


def test_validar_sai_1_com_erro_e_0_so_com_aviso(tmp_path):
    assert rodar(montar(tmp_path / "e", [{**A, "status": "Concluído"}]), "validar",
                 "--tudo").codigo == 1
    so_aviso = montar(tmp_path / "a", [{**B, "depende": [], "bloqueia": [], "status": "Backlog"}])
    resultado = rodar(so_aviso, "validar")
    assert resultado.codigo == 0
    assert resultado.out.endswith("1 cards · 0 erro(s) · 1 aviso(s)")


BOM = "﻿".encode("utf-8")


def test_card_com_bom_do_powershell_entra_no_board_e_o_mover_preserva_o_bom(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    caminho = board / "2 - B.md"
    caminho.write_bytes(BOM + caminho.read_bytes())
    resultado = rodar(board, "validar")
    assert resultado.out.endswith("2 cards · 0 erro(s) · 1 aviso(s)"), resultado.out
    assert rodar(board, "mover", "--card=2", "--status=Backlog", "--texto=Parado.").codigo == 0
    gravado = caminho.read_bytes()
    assert gravado.startswith(BOM + b"---\n")
    assert props(board, "2 - B")["Status"] == "Backlog"


def test_md_que_nao_e_utf8_ou_sem_status_fica_fora_com_aviso_e_nome(tmp_path):
    board = montar(tmp_path, [A])
    (board / "Latin1.md").write_bytes("---\nStatus: Backlog\nTítulo: é\n---\n".encode("cp1252"))
    (board / "Nota.md").write_text("---\ntags: []\n---\nnota solta\n", encoding="utf-8")
    resultado = rodar(board, "validar")
    assert resultado.codigo == 0
    assert "aviso · Latin1 · Latin1.md não é UTF-8 (byte 0xed na posição 21)" in resultado.out
    assert "aviso · Nota · Nota.md tem frontmatter sem Status" in resultado.out
    assert "1 cards · 0 erro(s) · 2 aviso(s)" in resultado.out
    # Os outros comandos continuam de pé e também avisam.
    fila_ = rodar(board, "fila")
    assert fila_.codigo == 0
    assert "Latin1.md não é UTF-8" in fila_.err


def test_spec_e_arquivo_com_bom_do_powershell(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    spec = tmp_path / "spec.json"
    spec.write_bytes(BOM + json.dumps(BASE, ensure_ascii=False).encode("utf-8"))
    assert rodar(board, "criar", f"--spec={spec}").codigo == 0
    arquivo = tmp_path / "entrada.md"
    arquivo.write_bytes(BOM + "Entregue.".encode("utf-8"))
    assert rodar(board, "historico", "--card=2", f"--arquivo={arquivo}").codigo == 0
    texto = ler(board, "2 - B")
    assert "- **26/09/2026 23:18 · TM** — Entregue." in texto
    assert "﻿" not in texto
    ruim = tmp_path / "ruim.md"
    ruim.write_bytes("Entregue à noite.".encode("cp1252"))
    resultado = rodar(board, "historico", "--card=2", f"--arquivo={ruim}")
    assert resultado.codigo == 1 and "ruim.md não é UTF-8" in resultado.err


# ---------------------------------------------------------------------------
# fila
# ---------------------------------------------------------------------------

def test_fila_reprovados_primeiro_depois_ordem_so_pronta(tmp_path):
    q = _quadro(tmp_path, [
        {"ordem": 10, "titulo": "dez", "status": "Pronta para começar"},
        {"ordem": 2.5, "titulo": "dois", "status": "Pronta para começar"},
        {"ordem": 30, "titulo": "trinta", "status": "Pronta para começar", "reprovada": "true"},
        {"ordem": 1, "titulo": "um", "status": "Backlog"},
    ])
    assert [c.nome for c in fila(q).cartoes] == ["30 - trinta", "2,5 - dois", "10 - dez"]


def test_fila_com_trilho_livre_mostra_o_caminho_de_jogo_marcado(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 1, "titulo": "jogo", "status": "Pronta para começar", "jogo": True},
        {"ordem": 2, "titulo": "offline", "status": "Pronta para começar"},
    ])
    resultado = rodar(board, "fila")
    assert resultado.out.splitlines() == [
        "Trilho: livre",
        "1 · H1.10 · Offline · Agente · Infra/Harness · caminho de jogo · 1 - jogo",
        "2 · H1.20 · Offline · Agente · Infra/Harness · 2 - offline",
        '2 card(s) na fila de "Pronta para começar"',
    ]


def test_fila_com_trilho_ocupado_esconde_o_caminho_de_jogo(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 1, "titulo": "candidato", "status": "Aguardando partida", "jogo": True,
         "card": "B1.3r", "sprint": "B1"},
        {"ordem": 2, "titulo": "jogo", "status": "Pronta para começar", "jogo": True},
        {"ordem": 3, "titulo": "offline", "status": "Pronta para começar"},
    ])
    resultado = rodar(board, "fila")
    assert resultado.out.splitlines()[0] == (
        "Trilho: ocupado por 1 · B1.3r (Aguardando partida); 1 card(s) de caminho de jogo "
        "fora da fila")
    assert "2 - jogo" not in resultado.out
    assert "3 - offline" in resultado.out
    assert "TRILHO VIOLADO" not in resultado.out


def test_fila_acusa_trilho_violado_com_dois_em_curso(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 1, "titulo": "um", "status": "PR aberta", "jogo": True},
        {"ordem": 2, "titulo": "dois", "status": "Em andamento", "jogo": True},
    ])
    resultado = rodar(board, "fila")
    assert resultado.codigo == 0
    assert "TRILHO VIOLADO: 2 cards de caminho de jogo em curso" in resultado.out


def _board_de_verificacoes(tmp_path):
    return montar(tmp_path, [
        {"ordem": 1, "titulo": "offline", "status": "Pronta para começar"},
        {"ordem": 2, "titulo": "servidor", "status": "Pronta para começar",
         "verificacao": "Servidor"},
        {"ordem": 3, "titulo": "partida", "status": "Pronta para começar",
         "verificacao": "Partida"},
    ])


@pytest.mark.parametrize("codigo, cabecalho, nomes", [
    (0, "Preflight 0 (livre)", ["1 - offline", "2 - servidor", "3 - partida"]),
    (3, "Preflight 3 (Victor jogando); só Offline, 2 card(s) fora da fila", ["1 - offline"]),
    (4, "Preflight 4 (janela aberta: só o papel servidor mexe no que é vivo); 2 card(s) de "
        "Servidor ou Partida só para o papel servidor",
     ["1 - offline", "2 - servidor", "3 - partida"]),
    (1, "Preflight 1 (código 1 conta como 3: Victor jogando); só Offline, 2 card(s) fora "
        "da fila", ["1 - offline"]),
])
def test_fila_agora_consulta_o_preflight_3_so_offline_e_4_mantem_o_do_servidor(
        tmp_path, codigo, cabecalho, nomes):
    resultado = rodar(_board_de_verificacoes(tmp_path), "fila", "--agora",
                      preflight=lambda: codigo)
    assert cabecalho in resultado.out.splitlines()
    for nome in ("1 - offline", "2 - servidor", "3 - partida"):
        assert (nome in resultado.out) == (nome in nomes)


def test_fila_agora_com_janela_aberta_marca_servidor_e_partida_so_para_o_papel_servidor(
        tmp_path):
    # G0: "4 = só o servidor". O papel servidor, que usa o CLI, não pode ver a fila
    # vazia justo na janela dele; os outros papéis veem a marca e deixam o card.
    linhas = rodar(_board_de_verificacoes(tmp_path), "fila", "--agora",
                   preflight=lambda: 4).out.splitlines()
    assert "1 · H1.10 · Offline · Agente · Infra/Harness · 1 - offline" in linhas
    assert ("2 · H1.20 · Servidor · Agente · Infra/Harness · só papel servidor · "
            "2 - servidor") in linhas
    assert ("3 · H1.30 · Partida · Agente · Infra/Harness · só papel servidor · "
            "3 - partida") in linhas


def test_fila_sem_agora_nao_roda_o_preflight(tmp_path):
    def nao_chame():
        raise AssertionError("preflight rodou sem --agora")

    resultado = rodar(_board_de_verificacoes(tmp_path), "fila", preflight=nao_chame)
    assert resultado.codigo == 0
    assert "3 card(s) na fila" in resultado.out


def test_rodar_preflight_devolve_o_codigo_e_falha_vira_3(monkeypatch):
    chamadas = []

    def falso(argv, **_):
        chamadas.append(argv)
        return SimpleNamespace(returncode=4)

    monkeypatch.setattr(cli.subprocess, "run", falso)
    assert cli.rodar_preflight() == 4
    assert chamadas[0][0] == sys.executable
    assert chamadas[0][1].endswith("preflight.py")

    def explode(*_, **__):
        raise OSError("sem interpretador")

    monkeypatch.setattr(cli.subprocess, "run", explode)
    assert cli.rodar_preflight() == 3


# ---------------------------------------------------------------------------
# criar
# ---------------------------------------------------------------------------

def _spec(tmp_path, valor):
    caminho = tmp_path / f"spec-{len(list(tmp_path.glob('spec-*')))}.json"
    caminho.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")
    return f"--spec={caminho}"


def test_criar_em_lote_deriva_o_status_e_espelha_o_bloqueia(tmp_path):
    # B está Bloqueada, sem pendentes próprias: o Novo nasce Bloqueada, e o que depende
    # dele nasce em Backlog, por cadeia.
    board = montar(tmp_path, [A, {**B, "bloqueia": []}, {**E, "bloqueia": []}])
    resultado = rodar(board, "criar", _spec(tmp_path, [
        {"ordem": "7,5", "titulo": "Novo", "card": "T1.1", "camada": "Dados",
         "verificacao": "Offline", "executor": "Agente", "caminho_de_jogo": False,
         "depende_de": ["2"], "corpo": "**Problema:** novo."},
        {"ordem": 8, "titulo": "Depois do novo", "card": "T1.2", "camada": "Docs/KB",
         "verificacao": "Offline", "executor": "Humano", "caminho_de_jogo": False,
         "depende_de": ["T1.1"], "corpo": "x"},
        {"ordem": 9, "titulo": "Livre", "card": "T1.3", "sprint": "T1", "camada": "Bots/Servidor",
         "verificacao": "Partida", "executor": "Agente+Humano", "caminho_de_jogo": True,
         "infra": True, "janela": "pós", "partida": "leve", "corpo": "x" + ROLLBACK},
        {"ordem": 10, "titulo": "Estacionado", "card": "T1.4", "camada": "Web",
         "verificacao": "Offline", "executor": "Agente", "caminho_de_jogo": False,
         "status": "Backlog", "corpo": "x"},
    ]))
    assert resultado.codigo == 0, resultado.err
    novo = props(board, "7,5 - Novo")
    assert novo["Status"] == "Bloqueada"
    assert novo["Ordem"] == 7.5
    assert novo["ID"] == "T1.1" and novo["Sprint"] == "T1"
    assert novo["Reprovada"] is False and novo["Caminho de jogo"] is False
    assert novo["Depende de"] == ["[[2 - B]]"]
    assert novo["Bloqueia"] == ["[[8 - Depois do novo]]"]
    assert props(board, "8 - Depois do novo")["Status"] == "Backlog"
    livre = props(board, "9 - Livre")
    assert livre["Status"] == "Pronta para começar"
    assert (livre["Infra"], livre["Janela"], livre["Partida"]) == (True, "pós", "leve")
    assert props(board, "10 - Estacionado")["Status"] == "Backlog"
    assert props(board, "2 - B")["Bloqueia"] == ["[[7,5 - Novo]]"]
    texto = ler(board, "7,5 - Novo")
    assert texto.startswith("---\nID: T1.1\nStatus: Bloqueada\nSprint: T1\nOrdem: 7.5\n")
    assert ("## Histórico\n\n- **26/09/2026 23:18 · PM** — Card criado por "
            "`tools.board criar`. Status inicial: `Bloqueada` "
            "(1 dependência(s) pendente(s)).") in texto
    assert rodar(board, "validar").codigo == 0


BASE = {"ordem": 50, "titulo": "Ok", "card": "T1.50", "camada": "Dados",
        "verificacao": "Offline", "executor": "Agente", "caminho_de_jogo": False, "corpo": "x"}


@pytest.mark.parametrize("troca, mensagem", [
    ({"titulo": "Com: dois-pontos"}, "o título não pode ter"),
    ({"ordem": 1}, "a Ordem 1 já existe"),
    ({"card": "H1.10"}, "o ID H1.10 já existe"),
    ({"card": "t1.51"}, "fora do formato do plano"),
    ({"sprint": "T2"}, 'sprint "T2" não bate com o card T1.51'),
    ({"camada": "Infra"}, 'Camada "Infra" fora da lista'),
    ({"executor": "Robô"}, 'Executor "Robô" fora da lista'),
    ({"verificacao": "offline"}, 'Verificação "offline" fora da lista'),
    ({"janela": "pre"}, 'Janela "pre" fora da lista'),
    ({"caminho_de_jogo": None}, "caminho_de_jogo é obrigatório"),
    ({"caminho_de_jogo": True}, 'caminho de jogo exige a seção "## Rollback"'),
    ({"infra": True}, "infra true exige caminho_de_jogo true"),
    ({"status": "Pronta para começar"}, 'status só aceita "Backlog"'),
    ({"depende_de": ["404"]}, "nenhum card com Ordem 404"),
    ({"depende_de": ["Z9.9"]}, "nenhum card com ID Z9.9"),
    ({"corpo": ""}, "falta corpo"),
    ({"plataforma": "Todas"}, "chave desconhecida plataforma"),
    # O disco recusaria só na hora de gravar: tem de cair no planejamento.
    ({"titulo": "Ruim\ncom quebra"}, "caractere de controle"),
    ({"titulo": "Tab\taqui"}, "caractere de controle"),
    ({"titulo": "x" * 300}, "encurte o título"),
    # O validar recusaria o nome: criar não pode fazer card que já nasce com erro.
    ({"ordem": -3}, 'ordem "-3" não vira prefixo de nome'),
    ({"ordem": 1e-7}, 'ordem "1e-07" não vira prefixo de nome'),
])
def test_criar_recusa_spec_invalida_sem_gravar_nada(tmp_path, troca, mensagem):
    board = montar(tmp_path, [A])
    antes = sorted(p.name for p in board.iterdir())
    resultado = rodar(board, "criar", _spec(tmp_path, [
        BASE, {**BASE, "ordem": 51, "card": "T1.51", **troca}]))
    assert resultado.codigo == 1
    assert mensagem in resultado.err
    assert sorted(p.name for p in board.iterdir()) == antes


def test_criar_com_a_mesma_dependencia_duas_vezes_grava_uma_e_conta_uma(tmp_path):
    # "2" e "H1.20" são o mesmo card: 1 pendente sem cadeia = Bloqueada, não Backlog.
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    assert rodar(board, "criar", _spec(tmp_path, {**BASE, "depende_de": ["2", "H1.20"]})) \
        .codigo == 0
    novo = props(board, "50 - Ok")
    assert novo["Depende de"] == ["[[2 - B]]"]
    assert novo["Status"] == "Bloqueada"
    assert props(board, "2 - B")["Bloqueia"] == ["[[50 - Ok]]"]


def test_pendentes_nao_conta_dependencia_repetida(tmp_path):
    q = _quadro(tmp_path, [A, {**B, "status": "Em andamento", "bloqueia": []},
                           {**C, "depende": ["2 - B", "2 - B"], "bloqueia": []}])
    assert q.pendentes(q.get("3 - C")) == ["2 - B"]
    assert classificar(q, q.get("3 - C")) == "Bloqueada"


def test_criar_com_falha_no_disco_no_meio_do_lote_nao_grava_nada(tmp_path, monkeypatch):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    antes = {p.name: p.read_bytes() for p in board.iterdir()}
    abrir = open
    escritos = []

    def open_que_falha_no_segundo(caminho, modo="r", *args, **kwargs):
        if "w" in modo:
            escritos.append(caminho)
            if len(escritos) == 2:
                raise OSError(22, "Invalid argument")
        return abrir(caminho, modo, *args, **kwargs)

    monkeypatch.setattr("builtins.open", open_que_falha_no_segundo)
    resultado = rodar(board, "criar", _spec(tmp_path, [
        {**BASE, "depende_de": ["2"]}, {**BASE, "ordem": 51, "card": "T1.51", "titulo": "Dois"}]))
    assert resultado.codigo == 1
    assert "nada gravado" in resultado.err
    assert {p.name: p.read_bytes() for p in board.iterdir()} == antes


def test_gravacao_interrompida_na_troca_diz_o_que_ja_foi_gravado(tmp_path, monkeypatch):
    board = montar(tmp_path, [A])
    trocar = cli.os.replace
    feitas = []

    def replace_que_falha_no_segundo(origem, destino):
        feitas.append(destino)
        if len(feitas) == 2:
            raise OSError(13, "Permission denied")
        trocar(origem, destino)

    monkeypatch.setattr(cli.os, "replace", replace_que_falha_no_segundo)
    with pytest.raises(cli.ErroBoard, match=r"interrompida em b\.md.*Já gravados: a\.md"):
        cli._gravar_lote([(board / "a.md", "um"), (board / "b.md", "dois")])
    assert not list(board.glob("*.tmp"))


def test_criar_seco_nao_grava(tmp_path):
    board = montar(tmp_path, [A])
    antes = sorted(p.name for p in board.iterdir())
    resultado = rodar(board, "criar", "--seco", _spec(tmp_path, BASE))
    assert resultado.codigo == 0
    assert "Pronta para começar · 50 - Ok" in resultado.out
    assert "(seco: nada gravado)" in resultado.out
    assert sorted(p.name for p in board.iterdir()) == antes


# ---------------------------------------------------------------------------
# mover e historico: agente em worktree grava o board pelo CLI
# ---------------------------------------------------------------------------

def test_mover_muda_status_e_branch_e_carimba_data_hora_e_papel_pelo_relogio(tmp_path):
    board = montar(tmp_path, [A, {**B, "status": "Pronta para começar", "bloqueia": []}])
    resultado = rodar(board, "mover", "--card=2", "--status=Em andamento",
                      "--branch=feat/H1.3-board-cli", "--papel=dev",
                      "--texto=Escolhido para o lote 1.")
    assert resultado.codigo == 0, resultado.err
    lido = props(board, "2 - B")
    assert (lido["Status"], lido["Branch"]) == ("Em andamento", "feat/H1.3-board-cli")
    assert "- **26/09/2026 23:18 · dev** — Escolhido para o lote 1." in ler(board, "2 - B")
    assert "2 · Pronta para começar → Em andamento · Branch feat/H1.3-board-cli" in resultado.out


def test_mover_em_card_que_ja_tinha_erro_grava_avisa_e_sai_0(tmp_path):
    # Caminho de jogo sem "## Rollback" já é erro antes do mover. Sair 1 depois de
    # gravar faria o agente repetir e contar a reprovação duas vezes (freio falso).
    board = montar(tmp_path, [{"ordem": 1, "titulo": "sem rollback", "status": "Em testes",
                               "jogo": True, "corpo": "**Problema:** x."}])
    resultado = rodar(board, "mover", "--card=1", "--status=Pronta para começar",
                      "--reprovada=true", "--reprovacao", "--papel=QA", "--texto=Reprovado.")
    assert resultado.codigo == 0, resultado.err
    assert "gravado: 1 - sem rollback" in resultado.out
    assert ('aviso · 1 - sem rollback · caminho de jogo sem a seção "## Rollback", que é '
            "obrigatória (erro que o card já tinha; não impediu a gravação)") in resultado.err
    assert props(board, "1 - sem rollback")["Reprovações"] == 1


def test_mover_que_criaria_erro_novo_recusa_sem_gravar(tmp_path):
    # Concluída não cobra Rollback; reabrir o card de caminho de jogo sem ele cobra.
    board = montar(tmp_path, [{"ordem": 1, "titulo": "sem rollback", "status": "Concluída",
                               "jogo": True, "corpo": "**Problema:** x."}])
    antes = ler(board, "1 - sem rollback")
    for seco in ([], ["--seco"]):
        resultado = rodar(board, "mover", "--card=1", "--status=Em andamento", *seco)
        assert resultado.codigo == 1
        assert "nada gravado em 1 - sem rollback: o card ficaria com erro novo" in resultado.err
        assert "Rollback" in resultado.err
    assert ler(board, "1 - sem rollback") == antes


def test_mover_branch_com_quebra_de_linha_grava_entre_aspas(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    assert rodar(board, "mover", "--card=2", "--branch=x\ny").codigo == 0
    lido = props(board, "2 - B")
    assert lido["Branch"] == "x\ny"
    assert lido["Status"] == "Bloqueada" and lido["Depende de"] == ["[[1 - A]]"]
    assert 'Branch: "x\\ny"' in ler(board, "2 - B")


def test_mover_reprova_e_soma_reprovacoes_e_devolucoes_de_null_e_de_1(tmp_path):
    board = montar(tmp_path, [A, {**B, "status": "Em testes", "bloqueia": []}])
    args = ["mover", "--card=H1.20", "--status=Pronta para começar", "--reprovada=true",
            "--reprovacao", "--devolucao"]
    assert rodar(board, *args, "--papel=QA", "--texto=Critério 2 falhou.").codigo == 0
    lido = props(board, "2 - B")
    assert (lido["Reprovada"], lido["Reprovações"], lido["Devoluções"]) == (True, 1, 1)
    assert rodar(board, *args).codigo == 0
    assert props(board, "2 - B")["Reprovações"] == 2


def test_mover_grava_pr_candidato_e_custo_e_limpa_com_null(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    assert rodar(board, "mover", "--card=2", "--pr=https://github.com/x/y/pull/9",
                 "--candidato=candidato-3", "--custo=812000").codigo == 0
    lido = props(board, "2 - B")
    assert (lido["PR"], lido["Candidato"], lido["Custo"]) == (
        "https://github.com/x/y/pull/9", "candidato-3", 812000)
    assert rodar(board, "mover", "--card=2", "--pr=null").codigo == 0
    assert props(board, "2 - B")["PR"] is None
    assert "tokens" in rodar(board, "mover", "--card=2", "--custo=muito").err


def test_mover_preserva_crlf_do_card(tmp_path):
    board = montar(tmp_path, [A])
    caminho = board / "2 - B.md"
    caminho.write_bytes(texto_card({**B, "bloqueia": []}).replace("\n", "\r\n").encode("utf-8"))
    assert rodar(board, "mover", "--card=2", "--status=Backlog", "--texto=Parado.").codigo == 0
    gravado = caminho.read_bytes().decode("utf-8")
    assert "Status: Backlog\r\n" in gravado and "\n" not in gravado.replace("\r\n", "")


def test_historico_de_varias_linhas_vem_de_arquivo_e_mantem_as_linhas_seguintes(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    arquivo = tmp_path / "entrada.md"
    arquivo.write_text("Entregue ao QA.\n\n  **Como verificar:**\n  1. Rodar o validar.\n",
                       encoding="utf-8")
    assert rodar(board, "historico", "--card=2", f"--arquivo={arquivo}").codigo == 0
    assert ("- **26/09/2026 23:18 · TM** — Entregue ao QA.\n\n  **Como verificar:**\n"
            "  1. Rodar o validar.") in ler(board, "2 - B")


def test_historico_seco_nao_grava(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    antes = ler(board, "2 - B")
    resultado = rodar(board, "historico", "--card=2", "--texto=Algo.", "--seco")
    assert resultado.codigo == 0
    assert "(seco: nada gravado)" in resultado.out
    assert ler(board, "2 - B") == antes


@pytest.mark.parametrize("entrada", [
    # A forma exata do carimbo, com data velha e papel fora da lista.
    "- **01/01/2020 00:00 · Robô** — aprovado",
    # Papel válido e data de ontem: o carimbo continua sendo do CLI.
    "- **25/09/2026 10:00 · QA** — Aprovado.",
    # Qualquer cabeçalho em negrito com travessão, mesmo sem data.
    "  * **Robô** – aprovado",
    # Carimbo forjado numa linha seguinte, recuada ou não.
    "Entregue.\n- **01/01/2020 00:00 · Robô** — aprovado",
    "Entregue.\n  - **01/01/2020 00:00 · QA** — aprovado",
])
@pytest.mark.parametrize("via", ["texto", "arquivo"])
def test_historico_recusa_entrada_ja_carimbada_e_nao_grava(tmp_path, entrada, via):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    antes = ler(board, "2 - B")
    if via == "arquivo":
        arquivo = tmp_path / "entrada.md"
        arquivo.write_text(entrada, encoding="utf-8")
        opcao = f"--arquivo={arquivo}"
    else:
        opcao = f"--texto={entrada}"
    resultado = rodar(board, "historico", "--card=2", opcao, "--papel=QA")
    assert resultado.codigo == 1
    assert "O carimbo é do CLI" in resultado.err
    assert ler(board, "2 - B") == antes


def test_mover_com_entrada_carimbada_nao_grava_nem_os_campos(tmp_path):
    board = montar(tmp_path, [A, {**B, "status": "Em testes", "bloqueia": []}])
    antes = ler(board, "2 - B")
    resultado = rodar(board, "mover", "--card=2", "--status=PR aberta",
                      "--texto=- **01/01/2020 00:00 · Robô** — aprovado")
    assert resultado.codigo == 1
    assert ler(board, "2 - B") == antes


def test_historico_carimba_com_o_relogio_e_o_papel_e_linha_sem_recuo_fica_dentro(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    resultado = rodar(board, "historico", "--card=2", "--papel=QA",
                      "--texto=Aprovado.\n## Rollback\n- item solto\n\n  já recuada")
    assert resultado.codigo == 0, resultado.err
    texto = ler(board, "2 - B")
    assert ("- **26/09/2026 23:18 · QA** — Aprovado.\n  ## Rollback\n  - item solto\n\n"
            "  já recuada") in texto
    # A linha sem recuo não abriu seção nova: a próxima entrada cai no Histórico.
    assert rodar(board, "historico", "--card=2", "--texto=Depois.").codigo == 0
    assert texto.count("## Histórico") == ler(board, "2 - B").count("## Histórico") == 1
    assert ler(board, "2 - B").rstrip().endswith("- **26/09/2026 23:18 · TM** — Depois.")


def test_mover_recusa_status_fora_dos_oito_e_seco_nao_grava(tmp_path):
    board = montar(tmp_path, [A, {**B, "bloqueia": []}])
    antes = ler(board, "2 - B")
    ruim = rodar(board, "mover", "--card=2", "--status=Em Testes")
    assert ruim.codigo == 1
    assert 'Status "Em Testes" não é um dos oito' in ruim.err
    assert rodar(board, "mover", "--card=2", "--status=Em testes", "--seco").codigo == 0
    assert ler(board, "2 - B") == antes


def test_mover_preenche_o_executor_e_recusa_valor_fora_da_lista(tmp_path):
    board = montar(tmp_path, [A, {**B, "executor": None, "bloqueia": []}])
    assert rodar(board, "mover", "--card=2", "--executor=Agente+Humano").codigo == 0
    assert props(board, "2 - B")["Executor"] == "Agente+Humano"
    assert "fora da lista" in rodar(board, "mover", "--card=2", "--executor=Robô").err


def test_mover_para_o_trilho_ocupado_avisa_o_trilho_unico(tmp_path):
    board = montar(tmp_path, [
        {"ordem": 1, "titulo": "candidato", "status": "Aguardando partida", "jogo": True},
        {"ordem": 2, "titulo": "outro", "status": "Pronta para começar", "jogo": True},
    ])
    resultado = rodar(board, "mover", "--card=2", "--status=Em andamento")
    assert resultado.codigo == 0
    assert "aviso · 2 - outro · trilho único: 2 cards de caminho de jogo" in resultado.err


@pytest.mark.parametrize("argv, mensagem", [
    (["mover", "--card=1"], "nada para mover"),
    (["historico", "--card=1"], "informe --texto"),
    (["mover", "--card=1", "--status=Backlog", "--papel=Robô"], '--papel "Robô" fora da lista'),
    (["mover", "--card=1", "--estado=Backlog"], "opção desconhecida --estado para mover"),
    (["mover", "--card"], "--card precisa de valor"),
    (["mover", "--card=1", "Backlog"], 'argumento solto "Backlog"'),
    (["validar", "--seco"], "opção desconhecida --seco para validar"),
    (["mover", "--card=1", "--seco=sim", "--status=Backlog"], "--seco não leva valor"),
    (["apagar"], 'comando desconhecido "apagar"'),
])
def test_cli_recusa_uso_errado_sem_gravar(tmp_path, argv, mensagem):
    board = montar(tmp_path, [A])
    antes = ler(board, "1 - A")
    resultado = rodar(board, *argv)
    assert resultado.codigo == 1
    assert mensagem in resultado.err
    assert ler(board, "1 - A") == antes


# ---------------------------------------------------------------------------
# onde fica o board e como se chama o CLI
# ---------------------------------------------------------------------------

def test_board_padrao_e_o_caminho_absoluto_do_checkout_principal(tmp_path, monkeypatch):
    assert cli.BOARD_PADRAO.as_posix() == "C:/Users/Victor/Projetos/cs2-tracker/docs/board-cs2"
    monkeypatch.setattr(cli, "BOARD_PADRAO", tmp_path / "nao-existe")
    err = []
    assert cli.main(["validar"], log=lambda _: None, erro=err.append) == 1
    assert "board não encontrado" in err[0] and "--board=<pasta>" in err[0]


def test_python_m_tools_board_chama_o_main(tmp_path, monkeypatch, capsys):
    board = montar(tmp_path, [A])
    monkeypatch.setattr(sys, "argv", ["tools.board", "validar", f"--board={board}"])
    with pytest.raises(SystemExit) as saida:
        runpy.run_module("tools.board", run_name="__main__")
    assert saida.value.code == 0
    assert "1 cards · 0 erro(s) · 0 aviso(s)" in capsys.readouterr().out
