#!/usr/bin/env python3
"""
tools/checar_fontes.py (card K1.4): as fontes `caminho:linha` de docs/ apontam
para arquivo do repo e linha que existe, e cada armadilha numerada tem
sintoma, causa, contorno e fonte.

Os casos montam um repo de mentira em tmp_path; o último confere o repo de
verdade (critério do card: checar_fontes verde e os 54 itens distribuídos).
Só leitura de arquivo: nada de processo, rede, Docker ou banco.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert conferir_entrada(tmp_path / "docs", "../mod.py:1") == "caminho sai do repo: ../mod.py"
    assert conferir_entrada(tmp_path, "docs/../mod.py:1") == "caminho sai do repo: docs/../mod.py"


def test_caminho_absoluto_e_erro_mesmo_apontando_para_dentro(tmp_path):
    # Sem o guarda, a raiz é que levaria a culpa ("resolve fora do repo"),
    # e no Windows `raiz / "/x"` vira o drive da raiz.
    _repo(tmp_path, {})
    absoluto = "/" + (tmp_path / "mod.py").as_posix().split(":", 1)[-1].lstrip("/")
    assert conferir_entrada(tmp_path, f"{absoluto}:1") == f"caminho absoluto (use relativo à raiz): {absoluto}"
    assert conferir_entrada(tmp_path, "/etc/hosts:1") == "caminho absoluto (use relativo à raiz): /etc/hosts"


def test_barra_invertida_e_erro_em_qualquer_so(tmp_path):
    # No Windows `raiz / "\\Windows\\win.ini"` vira C:\Windows\win.ini, e
    # `sub\m.py` passava aqui e quebrava no Linux.
    _repo(tmp_path, {}, {"sub/m.py": "a\n"})
    assert conferir_entrada(tmp_path, "\\Windows\\win.ini:1") == \
        "caminho com barra invertida (use /): \\Windows\\win.ini"
    assert conferir_entrada(tmp_path, "sub\\m.py:1") == "caminho com barra invertida (use /): sub\\m.py"
    assert conferir_entrada(tmp_path, "sub/m.py:1") is None


def test_caminho_que_resolve_fora_da_raiz_e_erro(tmp_path, monkeypatch):
    # Simula um link sem precisar de privilégio: o arquivo existe na raiz,
    # mas resolvido ele cai fora dela.
    raiz = _repo(tmp_path / "repo", {}, {"mod.py": "a\n", "link.py": "a\n"})
    fora = tmp_path / "fora.txt"
    fora.write_text("a\n", encoding="utf-8")
    original = Path.resolve

    def resolve_falso(self, strict=False):
        return fora if self.name == "link.py" else original(self, strict)

    monkeypatch.setattr(Path, "resolve", resolve_falso)
    assert conferir_entrada(raiz, "link.py:1") == "caminho resolve fora do repo (link ou junction): link.py"
    assert conferir_entrada(raiz, "mod.py:1") is None


def _ligar_pasta(link: Path, alvo: Path) -> bool:
    """Junction no Windows (mklink /J, sem privilégio), symlink nos outros."""
    try:
        if os.name == "nt":
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(alvo)],
                               capture_output=True, timeout=30)
            return r.returncode == 0 and link.is_dir()
        os.symlink(alvo, link, target_is_directory=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def test_junction_ou_symlink_para_fora_do_repo_e_erro(tmp_path):
    raiz = _repo(tmp_path / "repo", {"r.md": _nota("vendor/segredo.txt:1")})
    alvo = tmp_path / "fora"
    alvo.mkdir()
    (alvo / "segredo.txt").write_text("a\nb\n", encoding="utf-8")
    if not _ligar_pasta(raiz / "vendor", alvo):
        pytest.skip("não deu para criar junction/symlink nesta máquina")
    assert (raiz / "vendor" / "segredo.txt").is_file()
    assert checar(raiz) == [
        "docs/r.md:5: caminho resolve fora do repo (link ou junction): vendor/segredo.txt"]


def test_caminho_escrito_diferente_do_disco_e_erro(tmp_path):
    # `./mod.py` e (no Windows) `MOD.py` achariam o arquivo aqui e não no Linux.
    _repo(tmp_path, {})
    assert conferir_entrada(tmp_path, "./mod.py:1") == "caminho difere do arquivo no repo (mod.py): ./mod.py"
    if os.name == "nt":
        assert conferir_entrada(tmp_path, "MOD.py:1") == "caminho difere do arquivo no repo (mod.py): MOD.py"


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


def test_bom_no_comeco_da_nota_nao_esconde_a_fonte(tmp_path):
    _repo(tmp_path, {"r.md": "﻿" + _nota("mod.py:99")})
    assert checar(tmp_path) == ["docs/r.md:5: linha 99 além do fim de mod.py (3 linhas)"]


def _frontmatter(*linhas):
    return "\n".join(["---", "tipo: runbook", *linhas, "atualizado: 2026-10-13", "---", "", "corpo"])


def test_fontes_fora_da_gramatica_no_frontmatter_e_erro(tmp_path):
    casos = {
        "inline.md": (_frontmatter('fontes: ["mod.py:99"]'),
                      "docs/inline.md:3: `fontes:` com valor na mesma linha, fora da gramática: "
                      "'fontes: [\"mod.py:99\"]'"),
        "simples.md": (_frontmatter("fontes:", "  - 'mod.py:99'"),
                       "docs/simples.md:4: item de `fontes` fora da gramática (use `  - \"...\"`): \"- 'mod.py:99'\""),
        "sem_aspas.md": (_frontmatter("fontes:", "  - mod.py:99"),
                         "docs/sem_aspas.md:4: item de `fontes` fora da gramática (use `  - \"...\"`): '- mod.py:99'"),
        "coluna_0.md": (_frontmatter("fontes:", '- "mod.py:99"'),
                        "docs/coluna_0.md:4: item de `fontes` fora da gramática (use `  - \"...\"`): '- \"mod.py:99\"'"),
    }
    for nome, (texto, erro) in casos.items():
        pasta = tmp_path / nome.removesuffix(".md")
        _repo(pasta, {nome: texto})
        assert checar(pasta) == [erro], nome


def test_frontmatter_sem_fechamento_e_erro(tmp_path):
    _repo(tmp_path, {"r.md": "---\ntipo: runbook\nfontes:\n  - \"mod.py:2\"\n\ncorpo sem fechar\n"})
    assert checar(tmp_path) == ["docs/r.md:1: frontmatter aberto sem `---` de fechamento"]


def test_nota_que_nao_e_utf8_e_erro_sem_traceback(tmp_path, capsys):
    _repo(tmp_path, {"ok.md": _nota("mod.py:2")})
    (tmp_path / "docs" / "latin1.md").write_bytes(_nota("mod.py:2", corpo="ação").encode("latin-1"))
    assert main(["--raiz", str(tmp_path)]) == 1
    saida = capsys.readouterr()
    assert saida.out.splitlines() == ["docs/latin1.md: não é UTF-8", "checar_fontes: 1 erro(s)."]
    assert "Traceback" not in saida.err


def test_raiz_sem_docs_ou_sem_nota_e_erro(tmp_path, capsys):
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    assert main(["--raiz", str(vazia)]) == 1
    assert f"{vazia.as_posix()}: sem pasta docs/" in capsys.readouterr().out
    (vazia / "docs" / "board-cs2").mkdir(parents=True)
    (vazia / "docs" / "board-cs2" / "c.md").write_text(_nota("mod.py:1"), encoding="utf-8")
    assert main(["--raiz", str(vazia)]) == 1
    assert f"{vazia.as_posix()}/docs: nenhuma nota .md para conferir" in capsys.readouterr().out


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


def test_campo_vazio_e_fonte_sem_codigo_sao_erro(tmp_path):
    vazio = "### 1. Item\n- **Sintoma:**\n- **Causa:** c\n- **Contorno:** k\n- **Fonte:** `mod.py:2`\n"
    corpo = vazio + "\n" + _item(2, fonte="`commit abc1234` · `PR #4`")
    _repo(tmp_path, {"armadilhas/a.md": _nota("mod.py:1", corpo=corpo)})
    assert checar(tmp_path) == ["docs/armadilhas/a.md:10: campo Sintoma vazio",
                                "docs/armadilhas/a.md:15: item 2 sem fonte `caminho:N` nem `repo:`"]


def test_linha_recuada_continua_a_fonte(tmp_path):
    fonte = "`mod.py:2` ·\n  `mod.py:99` (continua)\n\n`mod.py:500` fora da Fonte"
    _repo(tmp_path, {"armadilhas/a.md": _nota("mod.py:1", corpo=_item(1, fonte=fonte))})
    assert checar(tmp_path) == ["docs/armadilhas/a.md:14: linha 99 além do fim de mod.py (3 linhas)"]


def test_armadilha_em_subpasta_tambem_e_conferida(tmp_path):
    _repo(tmp_path, {"armadilhas/sub/a.md": _nota("mod.py:1", corpo=_item(1, fonte="`mod.py:99`"))})
    assert checar(tmp_path) == ["docs/armadilhas/sub/a.md:13: linha 99 além do fim de mod.py (3 linhas)"]


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
