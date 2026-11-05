"""Testes do tools/metricas.py (card S1.0): árvore falsa em tmp_path, gabarito à mão."""

import json

from tools import metricas

# 7 linhas: 3 de docstring (com a em branco do meio), 1 '#', 1 branco, 2 código.
MODULO = '''"""Docstring

do módulo."""
# comentário
import os

x = os.sep  # fim de linha conta como código
'''

# 5 linhas: docstring de função de 1 linha, '#' indentado, 1 branco, 2 código.
FUNCAO = '''def f():
    """Doc."""
    # nota

    return 1
'''

RCON = "from rcon.source import Client\nc = Client\n"          # 2 linhas
RCON_MAO = "SERVERDATA_AUTH = 3\n"                             # 1 linha
NAO_RCON = "# fala de rcon, mas não é cliente\nrcon_host = 1\n"  # 2 linhas


def _arvore(raiz, arquivos):
    for rel, texto in arquivos.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8", newline="\n")


def test_contar_texto_classifica_docstring_comentario_branco_codigo():
    c = metricas.contar_texto(MODULO)
    assert (c.total, c.comentario, c.branco, c.codigo) == (7, 4, 1, 2)
    c = metricas.contar_texto(FUNCAO)
    assert (c.total, c.comentario, c.branco, c.codigo) == (5, 2, 1, 2)


def test_linha_e_a_do_wc_l_resto_sem_quebra_nao_conta():
    assert metricas.contar_texto("a = 1\nb = 2").total == 1
    assert metricas.contar_texto("a = 1\r\nb = 2\r\n").total == 2


def test_arquivo_que_nao_compila_fica_so_com_o_jogo_da_velha():
    c = metricas.contar_texto('def (:\n"""não é doc"""\n# sim\n')
    assert (c.total, c.comentario, c.codigo) == (3, 1, 2)


def test_areas_exclusoes_e_diferenca_para_a_base(tmp_path):
    _arvore(tmp_path, {
        "a.py": MODULO,                      # raiz: 7
        "b.py": FUNCAO,                      # raiz: 5
        "notas.txt": "x\n" * 50,             # não é .py
        "web/app.py": FUNCAO,                # web: 5
        "web/sub/x.py": "a = 1\n",           # web: 1 (recursivo)
        "web/templates/t.html": "x\n" * 9,   # não é .py
        "cs2tracker/ingest/eventos.py": "a = 1\nb = 2\n",  # cs2tracker: 2
        "cs2tracker/__pycache__/z.py": "a\n" * 30,
        "tests/test_a.py": "a\n" * 40,
        "tools/t.py": "a\n" * 40,
        "docs/d.py": "a\n" * 40,
        "docker/p.py": "a\n" * 40,
        ".venv/v.py": "a\n" * 40,
        ".claude/worktrees/w/a.py": "a\n" * 40,
        "outra/o.py": "a\n" * 40,
    })
    r = metricas.medir(metricas.fontes_do_disco(tmp_path))
    assert r["areas"]["raiz"]["total"] == 12
    assert r["areas"]["raiz"]["arquivos"] == ["a.py", "b.py"]
    assert r["areas"]["web"]["total"] == 6
    assert r["areas"]["web"]["arquivos"] == ["web/app.py", "web/sub/x.py"]
    assert r["areas"]["cs2tracker"]["total"] == 2
    assert r["total"] == {"total": 20, "codigo": 9, "comentario": 8,
                          "branco": 3}
    assert r["base"] == 8028
    assert r["diferenca_base"] == 20 - 8028


def test_grupos_de_ingestao_e_rcon(tmp_path):
    _arvore(tmp_path, {
        "parser.py": FUNCAO,                           # ingestão: 5
        "watcher.py": RCON,                            # ingestão e rcon: 2
        "start_match.py": RCON_MAO,                    # rcon: 1
        "stats.py": NAO_RCON,                          # nenhum
        "cs2tracker/ingest/eventos.py": "a = 1\n",     # ingestão: 1
        "cs2tracker/server/rcon.py": RCON,             # rcon: 2
        "tools/cliente.py": RCON,                      # fora do escopo
    })
    r = metricas.medir(metricas.fontes_do_disco(tmp_path))
    assert r["ingestao"]["arquivos"] == [
        "cs2tracker/ingest/eventos.py", "parser.py", "watcher.py"]
    assert r["ingestao"]["total"] == 8
    assert r["rcon"]["arquivos"] == [
        "cs2tracker/server/rcon.py", "start_match.py", "watcher.py"]
    assert r["rcon"]["total"] == 5


def test_ref_git_le_por_ls_tree_e_show_e_compara(tmp_path, monkeypatch, capsys):
    _arvore(tmp_path, {"a.py": "a = 1\n"})
    no_ref = {"a.py": "a = 1\nb = 2\nc = 3\n", "web/app.py": "x = 1\n",
              "tests/t.py": "a\n" * 9, "README.md": "# r\n"}
    chamadas = []

    def git_falso(raiz, *args):
        chamadas.append(args)
        if args[0] == "ls-tree":
            assert args[3] == "v1"
            return "\n".join(no_ref) + "\n"
        assert args[0] == "show"
        ref, caminho = args[1].split(":", 1)
        assert ref == "v1"
        return no_ref[caminho]

    monkeypatch.setattr(metricas, "_git", git_falso)
    assert metricas.main(["--raiz", str(tmp_path), "--ref", "v1",
                          "--json"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert saida["hoje"]["total"]["total"] == 1
    assert saida["ref"]["nome"] == "v1"
    assert saida["ref"]["total"]["total"] == 4
    assert saida["ref"]["areas"]["web"]["arquivos"] == ["web/app.py"]
    # só os arquivos do escopo foram lidos por git show
    assert sorted(a[1] for a in chamadas if a[0] == "show") == [
        "v1:a.py", "v1:web/app.py"]


def test_saida_de_texto_mostra_base_meta_e_grupos(tmp_path, capsys):
    _arvore(tmp_path, {"watcher.py": RCON})
    assert metricas.main(["--raiz", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Base do plano de 26/09: 8028; hoje: 2; diferença: -8026" in out
    assert "faltam" not in out and "atingida" in out
    assert "    - watcher.py" in out
