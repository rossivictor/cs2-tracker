#!/usr/bin/env python3
"""
tools/checar_fontes.py (card K1.4): as fontes `caminho:linha` de docs/ apontam
para arquivo do repo e linha que existe, e cada armadilha numerada tem
sintoma, causa, contorno e fonte.

Os casos montam um repo de mentira em tmp_path; o último confere o repo de
verdade (critério do card: checar_fontes verde e os 54 itens distribuídos).
Só leitura de arquivo: nada de processo, rede, Docker ou banco.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import checar_fontes  # noqa: E402
from checar_fontes import checar, conferir_entrada, main  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def _repo(tmp_path, notas: dict, codigo: dict | None = None) -> Path:
    for caminho, texto in (codigo or {"mod.py": "a\nb\nc\n"}).items():
        arquivo = tmp_path / caminho
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_bytes(texto.encode("utf-8"))
    for caminho, texto in notas.items():
        nota = tmp_path / "docs" / caminho
        nota.parent.mkdir(parents=True, exist_ok=True)
        nota.write_text(texto, encoding="utf-8", newline="\n")
    return tmp_path


def _nota(*fontes, corpo=""):
    linhas = ["---", "tipo: armadilha", "status: rascunho", "fontes:"]
    linhas += [f'  - "{f}"' for f in fontes]
    linhas += ["atualizado: 2026-10-13", "---", "", corpo]
    return "\n".join(linhas)


def _item(n, fonte="`mod.py:2`", sem=()):
    campos = {"Sintoma": "s", "Causa": "c", "Contorno": "k", "Fonte": fonte}
    linhas = [f"### {n}. Item"]
    linhas += [f"- **{c}:** {v}" for c, v in campos.items() if c not in sem]
    return "\n".join(linhas) + "\n"


# ---- uma entrada ----------------------------------------------------------

def test_caminho_com_linha_dentro_do_arquivo_passa(tmp_path):
    _repo(tmp_path, {})
    assert conferir_entrada(tmp_path, "mod.py:3") is None
    assert conferir_entrada(tmp_path, "mod.py:1-3 (detalhe)") is None


def test_linha_alem_do_fim_e_erro_com_o_total(tmp_path):
    _repo(tmp_path, {})
    assert conferir_entrada(tmp_path, "mod.py:4") == "linha 4 além do fim de mod.py (3 linhas)"
    assert conferir_entrada(tmp_path, "mod.py:2-9") == "linha 9 além do fim de mod.py (3 linhas)"


def test_ultima_linha_sem_quebra_final_conta(tmp_path):
    _repo(tmp_path, {}, {"sem_fim.py": "a\nb\nc"})
    assert conferir_entrada(tmp_path, "sem_fim.py:3") is None
    assert conferir_entrada(tmp_path, "sem_fim.py:4") == "linha 4 além do fim de sem_fim.py (3 linhas)"


def test_arquivo_que_nao_existe_e_erro(tmp_path):
    _repo(tmp_path, {})
    assert conferir_entrada(tmp_path, "logs/janelas/2026-09-28.md:7-13") == \
        "arquivo não existe no repo: logs/janelas/2026-09-28.md"
    assert conferir_entrada(tmp_path, "docs:1") == "arquivo não existe no repo: docs"


def test_caminho_que_sai_do_repo_e_erro(tmp_path):
    _repo(tmp_path, {"x.md": "x"})
    assert conferir_entrada(tmp_path / "docs", "../mod.py:1") == "arquivo não existe no repo: ../mod.py"


def test_intervalo_invertido_ou_linha_zero_e_erro(tmp_path):
    _repo(tmp_path, {})
    assert conferir_entrada(tmp_path, "mod.py:3-2") == "intervalo inválido em 'mod.py:3-2'"
    assert conferir_entrada(tmp_path, "mod.py:0") == "intervalo inválido em 'mod.py:0'"


def test_formas_fora_do_repo_so_tem_a_forma_conferida(tmp_path):
    _repo(tmp_path, {})
    for entrada in ("repo:kalendas docs/agents/licoes.md:220-226",
                    "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13])",
                    "transcript 1ba4cab3 @ 2026-09-19T18:36:28Z", "commit bafe2b4", "PR #4"):
        assert conferir_entrada(tmp_path, entrada) is None, entrada
    assert conferir_entrada(tmp_path, "repo:kalendas docs/x.md:5-1") == \
        "intervalo inválido em 'repo:kalendas docs/x.md:5-1'"


def test_forma_fora_da_gramatica_e_erro(tmp_path):
    _repo(tmp_path, {})
    for entrada in ("kalendas:docs/agents/licoes.md:220-226", "commit 779a979 PR 4",
                    "mod.py:100-106,150-157", "C:/cs2server/game/x.cfg:1"):
        assert conferir_entrada(tmp_path, entrada).startswith("fora da gramática"), entrada


# ---- frontmatter e corpo ---------------------------------------------------

def test_erro_do_frontmatter_diz_nota_e_linha(tmp_path):
    _repo(tmp_path, {"runbooks/r.md": _nota("commit abc1234", "mod.py:7")})
    assert checar(tmp_path) == ["docs/runbooks/r.md:6: linha 7 além do fim de mod.py (3 linhas)"]


def test_corpo_so_e_conferido_em_armadilhas(tmp_path):
    corpo = _item(1, fonte="`mod.py:99`")
    _repo(tmp_path, {"runbooks/r.md": _nota("mod.py:1", corpo=corpo),
                     "armadilhas/a.md": _nota("mod.py:1", corpo=corpo)})
    assert checar(tmp_path) == ["docs/armadilhas/a.md:13: linha 99 além do fim de mod.py (3 linhas)"]


def test_texto_fora_das_crases_na_fonte_nao_e_conferido(tmp_path):
    fonte = "`mod.py:2` · `commit bafe2b4` (auditoria: mod.py:400)"
    _repo(tmp_path, {"armadilhas/a.md": _nota("mod.py:1", corpo=_item(1, fonte=fonte))})
    assert checar(tmp_path) == []


def test_fonte_sem_crase_e_erro(tmp_path):
    _repo(tmp_path, {"armadilhas/a.md": _nota("mod.py:1", corpo=_item(5, fonte="mod.py:2"))})
    assert checar(tmp_path) == ["docs/armadilhas/a.md:13: linha Fonte sem entrada entre crases"]


def test_item_numerado_sem_campo_e_erro(tmp_path):
    corpo = _item(1) + "\n" + _item(2, sem=("Contorno", "Fonte")) + "\n" + _item(3)
    _repo(tmp_path, {"armadilhas/a.md": _nota("mod.py:1", corpo=corpo)})
    assert checar(tmp_path) == ["docs/armadilhas/a.md:15: item 2 sem Contorno, Fonte"]


def test_secao_sem_numero_nao_precisa_dos_quatro_campos(tmp_path):
    corpo = "## Resumo\n\n### Assinatura\n\ntexto\n\n" + _item(1)
    _repo(tmp_path, {"armadilhas/a.md": _nota("mod.py:1", corpo=corpo)})
    assert checar(tmp_path) == []


def test_vault_do_board_e_pasta_oculta_ficam_de_fora(tmp_path):
    ruim = _nota("mod.py:50")
    _repo(tmp_path, {"board-cs2/c.md": ruim, ".obsidian/x.md": ruim, "ok.md": _nota("mod.py:2")})
    assert checar(tmp_path) == []


def test_main_sai_0_verde_e_1_com_a_lista(tmp_path, capsys):
    _repo(tmp_path, {"ok.md": _nota("mod.py:2")})
    assert main(["--raiz", str(tmp_path)]) == 0
    _repo(tmp_path, {"ruim.md": _nota("nada.py:1")})
    assert main(["--raiz", str(tmp_path)]) == 1
    saida = capsys.readouterr().out
    assert "docs/ruim.md:5: arquivo não existe no repo: nada.py" in saida
    assert "checar_fontes: 1 erro(s)." in saida


# ---- o repo de verdade -----------------------------------------------------

def test_repo_verde():
    assert checar(RAIZ) == []


def test_os_54_itens_estao_nas_armadilhas_uma_vez_cada():
    numeros = []
    for nota in sorted((RAIZ / "docs" / "armadilhas").glob("*.md")):
        numeros += [int(n) for n in re.findall(r"^### (\d+)\. ", nota.read_text(encoding="utf-8"), re.M)]
    assert sorted(numeros) == list(range(1, 55))


def test_gramatica_e_a_mesma_do_teste_da_kb():
    # O teste da KB (K1.1) prende a gramática do docs/README.md; o checador
    # precisa aceitar e recusar o mesmo.
    sys.path.insert(0, str(RAIZ / "tests"))
    import test_base_de_conhecimento as kb
    exemplos = ["watcher.py:455-491", "repo:kalendas docs/agents/licoes.md:260-266",
                "backup:temp-artifacts/eb5adec0/audit/git.json (findings[8])",
                "transcript 1ba4cab3 @ 2026-09-19T18:36:28Z", "commit 4c19249", "PR #4",
                "kalendas:docs/agents/licoes.md:220-226", "commit 779a979 PR 4",
                "transcript eb5adec0 22:10Z", "a.py:1-2,5"]
    for entrada in exemplos:
        assert (kb._forma_da_fonte(entrada) is None) == (checar_fontes.forma(entrada) is None), entrada
