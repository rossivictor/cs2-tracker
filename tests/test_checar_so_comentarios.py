#!/usr/bin/env python3
"""
tools/checar_so_comentarios.py (card K1.9): entre duas refs, só comentários
mudaram em .py, no YAML do compose e no cfg do CS2.

Cada caso monta um repositório git em tmp_path com dois commits, "antes" e
"depois", e roda a ferramenta entre eles. O gabarito (0 ou 1, e o que a saída
diz) está escrito à mão em cada caso. Só git local: nada de docker, rede ou
banco.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import checar_so_comentarios as csc  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _repo(tmp_path: Path, antes: dict, depois: dict) -> Path:
    """Repo com o commit "antes" (tag a) e o "depois" (tag d)."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "teste@example.invalid")
    _git(repo, "config", "user.name", "Teste")
    _git(repo, "config", "core.autocrlf", "false")
    for rotulo, arquivos in (("a", antes), ("d", depois)):
        for caminho, texto in arquivos.items():
            alvo = repo / caminho
            alvo.parent.mkdir(parents=True, exist_ok=True)
            if texto is None:
                alvo.unlink()
            else:
                alvo.write_bytes(texto.encode("utf-8"))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "--allow-empty", "-m", rotulo)
        _git(repo, "tag", rotulo)
    return repo


def _rodar(repo, *arquivos, capsys):
    codigo = csc.main(["a", "d", "--repo", str(repo), *arquivos])
    capturado = capsys.readouterr()
    assert codigo != 2, f"uso errado ou git falhou: {capturado.err}"
    return codigo, capturado.out


# ------------------------------------------------------------ Python

PY_ANTES = '''"""Módulo de teste."""
# comentário longo
# de três
# linhas
X = 1  # inline


def f(a):
    """Docstring da função."""
    # comentário dentro
    return a + X
'''


def test_python_so_comentarios_sai_0(tmp_path, capsys):
    depois = PY_ANTES.replace("# comentário longo\n# de três\n# linhas\n", "# ver [[nota]]\n")
    depois = depois.replace("  # inline", "")
    repo = _repo(tmp_path, {"m.py": PY_ANTES}, {"m.py": depois})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 0
    assert "OK m.py (python): só comentários mudaram" in saida
    assert "aviso" not in saida


def test_python_docstring_muda_sai_0_com_aviso(tmp_path, capsys):
    depois = PY_ANTES.replace('"""Docstring da função."""', '"""Outra docstring."""')
    repo = _repo(tmp_path, {"m.py": PY_ANTES}, {"m.py": depois})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 0
    assert "aviso: docstring de f mudou" in saida


def test_python_docstring_de_modulo_removida_avisa(tmp_path, capsys):
    depois = PY_ANTES.replace('"""Módulo de teste."""\n', "")
    repo = _repo(tmp_path, {"m.py": PY_ANTES}, {"m.py": depois})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 0
    assert "aviso: docstring de módulo removida" in saida


@pytest.mark.parametrize("troca", [
    ("X = 1", "X = 2"),                      # valor
    ("return a + X", "return X + a"),         # ordem
    ("def f(a):", "def f(b):"),               # nome
])
def test_python_codigo_muda_sai_1(tmp_path, capsys, troca):
    repo = _repo(tmp_path, {"m.py": PY_ANTES}, {"m.py": PY_ANTES.replace(*troca)})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 1
    assert "MUDOU m.py (python)" in saida
    assert "AST diferente" in saida


def test_python_string_que_nao_e_docstring_conta(tmp_path, capsys):
    antes = 'def f():\n    return "a"\n'
    depois = 'def f():\n    return "b"\n'
    repo = _repo(tmp_path, {"m.py": antes}, {"m.py": depois})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 1
    assert "-     value=Constant(value='a'))" in saida
    assert "+     value=Constant(value='b'))" in saida


def test_python_aspas_trocadas_mudam_os_tokens_mas_nao_o_ast(tmp_path, capsys):
    antes = "Y = 'abc'\n"
    depois = 'Y = "abc"\n'
    repo = _repo(tmp_path, {"m.py": antes}, {"m.py": depois})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 1
    assert "AST diferente" not in saida
    assert "tokens diferentes" in saida


@pytest.mark.parametrize("cabeca", [
    "# -*- coding: utf-8 -*-\n",
    "#!/usr/bin/env python3\n",
    "#!/usr/bin/env python3\n# vim: set fileencoding=latin-1 :\n",
])
def test_python_shebang_ou_coding_removido_conta(tmp_path, capsys, cabeca):
    repo = _repo(tmp_path, {"m.py": cabeca + "X = 1\n"}, {"m.py": "X = 1\n"})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 1
    assert "shebang ou declaração de encoding diferente" in saida


def test_python_comentario_comum_na_linha_1_nao_e_cabecalho(tmp_path, capsys):
    repo = _repo(tmp_path, {"m.py": "# comentário qualquer\nX = 1\n"}, {"m.py": "X = 1\n"})
    codigo, _ = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 0


def test_python_que_nao_compila_conta_como_mudanca(tmp_path, capsys):
    repo = _repo(tmp_path, {"m.py": PY_ANTES}, {"m.py": PY_ANTES + "def (\n"})
    codigo, saida = _rodar(repo, "m.py", capsys=capsys)
    assert codigo == 1
    assert "não compila" in saida


# ------------------------------------------------------------ YAML

YML_ANTES = """# cabeçalho
services:
  srv:
    image: img  # comentário inline
    environment:
      # bloco longo
      # de comentário
      - A=1
      - B="x # não é comentário"
    command: |
      linha 1
      # dentro do bloco literal
"""


def test_yaml_so_comentarios_sai_0(tmp_path, capsys):
    depois = YML_ANTES.replace("# cabeçalho\n", "").replace("      # bloco longo\n      # de comentário\n",
                                                          "      # ver [[nota]]\n")
    depois = depois.replace("  # comentário inline", "")
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES}, {"docker-compose.yml": depois})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 0
    assert "OK docker-compose.yml (yaml)" in saida


@pytest.mark.parametrize("troca", [
    ("- A=1", "- A=2"),
    ('x # não é comentário', 'x'),                         # dentro de aspas
    ("      # dentro do bloco literal\n", ""),            # dentro de bloco |
    ("    image: img", "    image: outra"),
])
def test_yaml_valor_muda_sai_1(tmp_path, capsys, troca):
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES},
                 {"docker-compose.yml": YML_ANTES.replace(*troca)})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 1
    assert "MUDOU docker-compose.yml (yaml)" in saida


def test_yaml_linha_descomentada_conta(tmp_path, capsys):
    antes = "volumes:\n  # - ./a:/b\n  - ./c:/d\n"
    depois = "volumes:\n  - ./a:/b\n  - ./c:/d\n"
    repo = _repo(tmp_path, {"docker-compose.yml": antes}, {"docker-compose.yml": depois})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 1
    assert "+  - ./a:/b" in saida


@pytest.mark.parametrize("antes,depois", [
    # aspa dupla escapada: o `# x` ainda está dentro da string
    ('k: "a\\" # x"\n', 'k: "a\\"\n'),
    # string entre aspas que atravessa linhas: a 2ª linha não é comentário
    ('k: "abc\n  # dentro"\n', 'k: "abc\n  "\n'),
    ("k: 'abc\n  # dentro'\n", "k: 'abc\n  '\n"),
])
def test_yaml_aspa_escapada_ou_aberta_falha_fechado(tmp_path, capsys, antes, depois):
    repo = _repo(tmp_path, {"docker-compose.yml": antes}, {"docker-compose.yml": depois})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 1
    assert "MUDOU docker-compose.yml (yaml)" in saida


def test_yaml_comentario_depois_da_aspa_fechada_continua_comentario(tmp_path, capsys):
    antes = 'k: "a\\"b" # x\nj: \'it\'\'s\' # y\n'
    depois = 'k: "a\\"b"\nj: \'it\'\'s\'\n'
    repo = _repo(tmp_path, {"docker-compose.yml": antes}, {"docker-compose.yml": depois})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 0, saida


class _YamlFalso:
    """Módulo yaml de mentira: o teste diz o que o safe_load devolve."""

    class YAMLError(Exception):
        pass

    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = 0

    def safe_load(self, texto):
        self.chamadas += 1
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado(texto)


def test_yaml_sem_pyyaml_avisa_e_compara_so_as_linhas(tmp_path, capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", None)  # import yaml dá ImportError
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES},
                 {"docker-compose.yml": YML_ANTES.replace("# cabeçalho\n", "")})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 0
    assert "aviso: PyYAML ausente: só a comparação de linhas" in saida


def test_yaml_com_pyyaml_parse_igual_sai_0_sem_aviso(tmp_path, capsys, monkeypatch):
    falso = _YamlFalso(lambda texto: {"services": 1})
    monkeypatch.setitem(sys.modules, "yaml", falso)
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES},
                 {"docker-compose.yml": YML_ANTES.replace("# cabeçalho\n", "")})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 0
    assert falso.chamadas == 2
    assert "PyYAML ausente" not in saida


def test_yaml_com_pyyaml_parse_diferente_sai_1(tmp_path, capsys, monkeypatch):
    # as linhas sem comentário são iguais; só o parse (de mentira) difere
    monkeypatch.setitem(sys.modules, "yaml", _YamlFalso(lambda texto: len(texto)))
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES},
                 {"docker-compose.yml": YML_ANTES.replace("# cabeçalho\n", "")})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 1
    assert "parse YAML diferente" in saida


def test_yaml_com_pyyaml_ilegivel_sai_1(tmp_path, capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "yaml", _YamlFalso(_YamlFalso.YAMLError("quebrado")))
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES}, {"docker-compose.yml": YML_ANTES})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 1
    assert "YAML ilegível: quebrado" in saida


def test_yaml_com_pyyaml_de_verdade(tmp_path, capsys):
    pytest.importorskip("yaml")
    depois = YML_ANTES.replace("# cabeçalho\n", "").replace("  # comentário inline", "")
    repo = _repo(tmp_path, {"docker-compose.yml": YML_ANTES}, {"docker-compose.yml": depois})
    codigo, saida = _rodar(repo, "docker-compose.yml", capsys=capsys)
    assert codigo == 0, saida
    repo2 = _repo(tmp_path / "2", {"docker-compose.yml": YML_ANTES},
                  {"docker-compose.yml": YML_ANTES.replace("- A=1", "- A=2")})
    codigo, saida = _rodar(repo2, "docker-compose.yml", capsys=capsys)
    assert codigo == 1


# ------------------------------------------------------------ cfg

CFG_ANTES = """// ====
// cabeçalho
// ====

// Bot quota
bot_quota                               10
hostname "a // b"
// diário
// longo
tv_delay                                0
"""


def test_cfg_so_comentarios_sai_0(tmp_path, capsys):
    depois = CFG_ANTES.replace("// diário\n// longo\n", "// ver [[nota]]\n").replace("// Bot quota\n", "")
    repo = _repo(tmp_path, {"x.cfg": CFG_ANTES}, {"x.cfg": depois})
    codigo, saida = _rodar(repo, "x.cfg", capsys=capsys)
    assert codigo == 0
    assert "OK x.cfg (cfg)" in saida


@pytest.mark.parametrize("troca", [
    ("bot_quota                               10", "bot_quota                               9"),
    ('hostname "a // b"', 'hostname "a"'),           # // dentro de aspas é valor
    ("// diário\n", "# diário\n"),                    # # no cfg vai ao console
    ("tv_delay                                0", "tv_delay 0"),   # byte a byte
])
def test_cfg_valor_muda_sai_1(tmp_path, capsys, troca):
    repo = _repo(tmp_path, {"x.cfg": CFG_ANTES}, {"x.cfg": CFG_ANTES.replace(*troca)})
    codigo, saida = _rodar(repo, "x.cfg", capsys=capsys)
    assert codigo == 1
    assert "MUDOU x.cfg (cfg)" in saida


def test_cfg_crlf_conta_como_mudanca(tmp_path, capsys):
    repo = _repo(tmp_path, {"x.cfg": CFG_ANTES}, {"x.cfg": CFG_ANTES.replace("\n", "\r\n")})
    codigo, _ = _rodar(repo, "x.cfg", capsys=capsys)
    assert codigo == 1


# ------------------------------------------------------------ geral

def test_sem_arquivos_usa_o_diff_entre_as_refs(tmp_path, capsys):
    repo = _repo(tmp_path, {"m.py": PY_ANTES, "x.cfg": CFG_ANTES},
                 {"m.py": PY_ANTES, "x.cfg": CFG_ANTES.replace("10", "11")})
    codigo, saida = _rodar(repo, capsys=capsys)
    assert codigo == 1
    assert "MUDOU x.cfg" in saida
    assert "m.py" not in saida


def test_tipo_sem_comparador_e_arquivo_novo_contam_como_mudanca(tmp_path, capsys):
    repo = _repo(tmp_path, {"a.sh": "echo 1\n"}, {"a.sh": "echo 1 # c\n", "novo.py": "X = 1\n"})
    codigo, saida = _rodar(repo, "a.sh", "novo.py", capsys=capsys)
    assert codigo == 1
    assert "MUDOU a.sh (?)" in saida
    assert "MUDOU novo.py (python)" in saida
    assert "só existe numa das refs" in saida


def test_ref_inexistente_sai_2(tmp_path, capsys):
    repo = _repo(tmp_path, {"m.py": PY_ANTES}, {"m.py": PY_ANTES})
    assert csc.main(["a", "naoexiste", "m.py", "--repo", str(repo)]) == 2
    assert "erro:" in capsys.readouterr().err
