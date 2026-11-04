#!/usr/bin/env python3
"""
Prova que, entre dois commits, só comentários mudaram (card K1.9; política
em docs/politica-de-comentarios.md, "Ordem: extrair antes de podar").

  <ref_antes> <ref_depois> [arquivos...]: compara cada arquivo nas duas
             refs (pelo `git show`, sem tocar no working tree). Sem
             arquivos, usa os que o `git diff --name-only` aponta entre elas.

O que conta como "só comentário", por tipo:

  .py        AST igual (ast.dump sem posições e sem docstrings) e a mesma
             sequência de tokens fora COMMENT, NL e as docstrings. Docstring
             de módulo, classe ou função pode mudar, mas a saída avisa: ela é
             `__doc__`, e há código que a lê (help de argparse). Shebang e
             `# -*- coding` não são só comentário: mudar conta.
  .yml/.yaml as linhas sem comentário `#` (fora de aspas, com o escape da
             aspa dupla, de string que atravessa linhas e de bloco `|`/`>`)
             e sem linha vazia, com o fim de linha preservado; com PyYAML
             instalado, também o parse. Não roda `docker compose config`: o dev
             não roda docker, e a prova do container é do servidor, na janela.
  .cfg       as linhas depois de tirar o comentário `//` (fora de aspas
             duplas: `//` dentro de valor entre aspas não é comentário) e as
             linhas vazias. `#` no cfg não é comentário: vai para o console.

Outro tipo de arquivo, arquivo que só existe numa das refs ou fonte que não
compila contam como mudança: a ferramenta falha fechado.

Saída 0: só comentários mudaram em todos. 1: algo mudou, com o diff do que
mudou (já sem comentários). 2: uso errado ou git falhou. Só biblioteca
padrão (PyYAML é opcional); o único processo é o git do repo. Uso:

    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/checar_so_comentarios.py origin/main HEAD docker-compose.yml
    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/checar_so_comentarios.py origin/main HEAD --repo <checkout>
"""
from __future__ import annotations

import argparse
import ast
import difflib
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_DOCSTRING_EM = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_BLOCO_YAML = re.compile(r":\s*[|>][+-]?\d*\s*$|^\s*-\s*[|>][+-]?\d*\s*$")


class ErroDeUso(Exception):
    """Ref inexistente, git ausente ou repositório inválido (saída 2)."""


def git(repo: Path, *args: str) -> bytes:
    """Roda `git -C repo args` e devolve o stdout; erro vira ErroDeUso."""
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    except FileNotFoundError as exc:
        raise ErroDeUso("git não encontrado no PATH") from exc
    if r.returncode != 0:
        raise ErroDeUso(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def ler(repo: Path, ref: str, caminho: str) -> str | None:
    """Conteúdo do arquivo na ref, ou None se ele não existe nela."""
    git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{ref}:{caminho}"],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return git(repo, "show", f"{ref}:{caminho}").decode("utf-8")


# ---------------------------------------------------------------- Python

def _docstrings(arvore: ast.AST) -> list[tuple[str, ast.Constant]]:
    """(dono, nó) de cada docstring de módulo, classe e função."""
    achadas = []
    for no in ast.walk(arvore):
        if isinstance(no, _DOCSTRING_EM) and no.body:
            primeiro = no.body[0]
            if (isinstance(primeiro, ast.Expr) and isinstance(primeiro.value, ast.Constant)
                    and isinstance(primeiro.value.value, str)):
                dono = "módulo" if isinstance(no, ast.Module) else no.name
                achadas.append((dono, primeiro.value))
    return achadas


def _sem_docstrings(arvore: ast.AST) -> str:
    for no in ast.walk(arvore):
        if isinstance(no, _DOCSTRING_EM) and no.body:
            primeiro = no.body[0]
            if (isinstance(primeiro, ast.Expr) and isinstance(primeiro.value, ast.Constant)
                    and isinstance(primeiro.value.value, str)):
                no.body = no.body[1:] or [ast.Pass()]
    return ast.dump(arvore, include_attributes=False, indent=1)


def _tokens(fonte: str, posicoes_doc: set[tuple[int, int]]) -> list[str]:
    fora = {tokenize.COMMENT, tokenize.NL, tokenize.ENCODING}
    saida = []
    pular_newline = False
    for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
        if tok.type in fora:
            continue
        if tok.type == tokenize.STRING and tok.start in posicoes_doc:
            pular_newline = True  # a docstring sai com o fim da linha dela
            continue
        if pular_newline:
            pular_newline = False
            if tok.type == tokenize.NEWLINE:
                continue
        if tok.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE,
                        tokenize.ENDMARKER):
            saida.append(tokenize.tok_name[tok.type])
        else:
            saida.append(f"{tokenize.tok_name[tok.type]} {tok.string}")
    return saida


_CODING = re.compile(r"^[ \t\f]*#.*?coding[:=]")


def _cabecalho(fonte: str) -> list[str]:
    """Shebang (linha 1) e declaração de encoding (linhas 1 e 2, PEP 263):
    parecem comentário, mas mudam como o arquivo roda ou é lido."""
    linhas = fonte.split("\n")[:2]
    return [l.rstrip("\r") for n, l in enumerate(linhas)
            if (n == 0 and l.startswith("#!")) or _CODING.match(l)]


def comparar_python(antes: str, depois: str) -> tuple[list[str], list[str]]:
    """(diferenças, avisos). Diferença vazia = só comentários e docstrings."""
    try:
        a, d = ast.parse(antes), ast.parse(depois)
    except SyntaxError as exc:
        return [f"não compila: {exc}"], []
    diffs = []
    cab_a, cab_d = _cabecalho(antes), _cabecalho(depois)
    if cab_a != cab_d:
        diffs.append("shebang ou declaração de encoding diferente (não é só comentário):")
        diffs += _diff(cab_a, cab_d)
    docs_a, docs_d = dict(_docstrings(a)), dict(_docstrings(d))
    pos_a = {(n.lineno, n.col_offset) for n in docs_a.values()}
    pos_d = {(n.lineno, n.col_offset) for n in docs_d.values()}
    avisos = []
    for dono in sorted(set(docs_a) | set(docs_d)):
        va = docs_a[dono].value if dono in docs_a else None
        vd = docs_d[dono].value if dono in docs_d else None
        if va != vd:
            estado = "removida" if vd is None else "nova" if va is None else "mudou"
            avisos.append(f"docstring de {dono} {estado} (é __doc__: confira quem a lê)")
    dump_a, dump_d = _sem_docstrings(a), _sem_docstrings(d)
    if dump_a != dump_d:
        diffs.append("AST diferente:")
        diffs += _diff(dump_a.splitlines(), dump_d.splitlines())
    try:
        tok_a, tok_d = _tokens(antes, pos_a), _tokens(depois, pos_d)
    except (tokenize.TokenError, SyntaxError) as exc:
        return diffs + [f"tokens ilegíveis: {exc}"], avisos
    if tok_a != tok_d:
        diffs.append("tokens diferentes (fora comentário, NL e docstring):")
        diffs += _diff(tok_a, tok_d)
    return diffs, avisos


# ---------------------------------------------------------------- YAML

def _varrer(linha: str, marca: str, aspas: str, dentro: str | None = None) -> tuple[str, str | None]:
    """(a linha até o comentário `marca`, a aspa que ficou aberta no fim).

    O que está entre `aspas` não é comentário; dentro de aspa dupla, a
    barra invertida escapa o caractere seguinte. Linha que termina com aspa
    aberta fica inteira: falha fechado. No YAML (`#`), o comentário começa no
    início da linha ou depois de espaço; no cfg (`//`), em qualquer ponto."""
    i = 0
    while i < len(linha):
        c = linha[i]
        if dentro:
            if dentro == '"' and c == "\\":
                i += 2
                continue
            if c == dentro:
                dentro = None
        elif c in aspas:
            dentro = c
        elif linha.startswith(marca, i) and (marca != "#" or i == 0 or linha[i - 1] in " \t"):
            return linha[:i], None
        i += 1
    return linha, dentro


def normalizar_yaml(texto: str) -> list[str]:
    """Linhas sem comentário e sem linha vazia; bloco `|`/`>` e string entre
    aspas que atravessa linhas ficam literais."""
    saida = []
    bloco_recuo = None
    aspa = None
    for linha in texto.split("\n"):
        recuo = len(linha) - len(linha.lstrip(" "))
        if bloco_recuo is not None:
            if linha.strip() == "" or recuo > bloco_recuo:
                saida.append(linha)
                continue
            bloco_recuo = None
        continuacao = aspa is not None
        codigo, aspa = _varrer(linha, "#", "'\"", aspa)
        codigo = codigo.rstrip(" \t")
        if codigo.strip() or continuacao:
            saida.append(codigo)
            if aspa is None and _BLOCO_YAML.search(codigo):
                bloco_recuo = recuo
    while saida and not saida[-1].strip():
        saida.pop()
    return saida


def comparar_yaml(antes: str, depois: str) -> tuple[list[str], list[str]]:
    na, nd = normalizar_yaml(antes), normalizar_yaml(depois)
    diffs = [] if na == nd else ["linhas sem comentário diferentes:"] + _diff(na, nd)
    avisos = []
    try:
        import yaml  # opcional: a .venv do jogo pode não ter
    except ImportError:
        avisos.append("PyYAML ausente: só a comparação de linhas")
    else:
        try:
            if yaml.safe_load(antes) != yaml.safe_load(depois):
                diffs.append("parse YAML diferente")
        except yaml.YAMLError as exc:
            diffs.append(f"YAML ilegível: {exc}")
    return diffs, avisos


# ---------------------------------------------------------------- cfg

def normalizar_cfg(texto: str) -> list[str]:
    """Linhas do cfg sem o comentário `//` (fora de aspas duplas) e sem vazias."""
    saida = []
    for linha in texto.split("\n"):
        codigo = _varrer(linha, "//", '"')[0].rstrip(" \t")
        if codigo.strip():
            saida.append(codigo)
    return saida


def comparar_cfg(antes: str, depois: str) -> tuple[list[str], list[str]]:
    na, nd = normalizar_cfg(antes), normalizar_cfg(depois)
    return ([] if na == nd else ["linhas sem comentário diferentes:"] + _diff(na, nd)), []


# ---------------------------------------------------------------- geral

COMPARADORES = {
    ".py": ("python", comparar_python),
    ".yml": ("yaml", comparar_yaml),
    ".yaml": ("yaml", comparar_yaml),
    ".cfg": ("cfg", comparar_cfg),
}


def _diff(a: list[str], b: list[str]) -> list[str]:
    return ["  " + l for l in difflib.unified_diff(a, b, "antes", "depois", n=1, lineterm="")]


def comparar_arquivo(caminho: str, antes: str | None, depois: str | None):
    """(tipo, diferenças, avisos) de um arquivo."""
    tipo, funcao = COMPARADORES.get(Path(caminho).suffix.lower(), ("?", None))
    if funcao is None:
        return tipo, ["tipo de arquivo sem comparador: conta como mudança"], []
    if antes is None or depois is None:
        return tipo, ["o arquivo só existe numa das refs"], []
    return (tipo, *funcao(antes, depois))


def checar(repo: Path, ref_antes: str, ref_depois: str, arquivos: list[str]) -> tuple[int, list[str]]:
    """(código de saída, linhas do relatório)."""
    if not arquivos:
        saida = git(repo, "diff", "--name-only", ref_antes, ref_depois).decode("utf-8")
        arquivos = [l for l in saida.splitlines() if l.strip()]
    if not arquivos:
        return 0, [f"nada mudou entre {ref_antes} e {ref_depois}"]
    linhas, codigo = [], 0
    for caminho in arquivos:
        caminho = caminho.replace("\\", "/")
        tipo, diffs, avisos = comparar_arquivo(
            caminho, ler(repo, ref_antes, caminho), ler(repo, ref_depois, caminho))
        if diffs:
            codigo = 1
            linhas.append(f"MUDOU {caminho} ({tipo})")
            linhas += ["  " + d for d in diffs]
        else:
            linhas.append(f"OK {caminho} ({tipo}): só comentários mudaram")
        linhas += [f"  aviso: {a}" for a in avisos]
    linhas.append("RESULTADO: " + ("só comentários" if codigo == 0 else "mudou algo além de comentário"))
    return codigo, linhas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prova que, entre duas refs, só comentários mudaram (card K1.9).")
    ap.add_argument("ref_antes")
    ap.add_argument("ref_depois")
    ap.add_argument("arquivos", nargs="*")
    ap.add_argument("--repo", type=Path, default=RAIZ, help="checkout git (padrão: este)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        codigo, linhas = checar(args.repo, args.ref_antes, args.ref_depois, args.arquivos)
    except ErroDeUso as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    print("\n".join(linhas))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
