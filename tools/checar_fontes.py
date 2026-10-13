#!/usr/bin/env python3
"""
Confere as fontes da KB (card K1.4): cada `caminho:N` de docs/ aponta para um
arquivo que existe neste repo, e a linha N (ou o intervalo N-M) cabe nele.

O que é lido, sempre em docs/**/*.md (sem o vault docs/board-cs2/ e sem pasta
oculta, como no tests/test_base_de_conhecimento.py):

1. As entradas de `fontes` do frontmatter, pela gramática do docs/README.md
   (seção "Frontmatter padrão").
2. Em docs/armadilhas/, a linha `- **Fonte:**` de cada item. Ali cada entrada
   vai entre crases, com a mesma gramática; o texto fora das crases é só para
   quem lê. Item numerado (`### N. título`) precisa ter as quatro linhas:
   Sintoma, Causa, Contorno e Fonte.

O que se confere em cada entrada:

- `caminho:N` e `caminho:N-M`: forma, intervalo não invertido, arquivo
  existente relativo à raiz e linha dentro do arquivo. A linha só diz que o
  trecho existe; se ele ainda diz o que a nota afirma é revisão humana.
- `repo:<nome> caminho:N`, `backup:...`, `transcript ...`, `commit ...` e
  `PR #n`: só a forma. Outro repositório, backup e sessão ficam fora deste
  checkout, e commit pode não estar no clone.

Saída 0 sem erro; 1 com a lista de erros (um por linha, `nota:linha: motivo`).
Só biblioteca padrão; não abre processo nem rede. Uso:

    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/checar_fontes.py
    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/checar_fontes.py --raiz <checkout>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_CODIGO = r"(?P<caminho>[^\s:()]+):(?P<ini>\d+)(?:-(?P<fim>\d+))?"
FORMAS = {
    "caminho": re.compile(rf"^{_CODIGO}$"),
    "repo": re.compile(rf"^repo:[\w.-]+ {_CODIGO}$"),
    "backup": re.compile(r"^backup:\S+$"),
    "transcript": re.compile(r"^transcript [0-9a-f]{8} @ \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$"),
    "commit": re.compile(r"^commit [0-9a-f]{7,40}$"),
    "pr": re.compile(r"^PR #\d+$"),
}
CAMPOS_DO_ITEM = ("Sintoma", "Causa", "Contorno", "Fonte")
_ITEM = re.compile(r"^### (\d+)\. ")
_LINHA_FONTE = re.compile(r"^- \*\*Fonte:\*\*(.*)$")


def forma(entrada: str):
    """(nome da forma, match) da entrada sem o ` (detalhe)` final, ou None."""
    sem_detalhe = re.sub(r" \(.*\)$", "", entrada)
    for nome, regex in FORMAS.items():
        achado = regex.match(sem_detalhe)
        if achado:
            return nome, achado
    return None


def notas(raiz: Path) -> list[Path]:
    docs = raiz / "docs"
    saida = []
    for caminho in sorted(docs.rglob("*.md")):
        partes = caminho.relative_to(docs).parts
        if partes[0] == "board-cs2" or any(p.startswith(".") for p in partes):
            continue
        saida.append(caminho)
    return saida


def fontes_do_frontmatter(texto: str) -> list[tuple[int, str]]:
    """(linha da nota, entrada) de cada item de `fontes`, ou [] sem frontmatter."""
    linhas = texto.splitlines()
    if not linhas or linhas[0] != "---":
        return []
    saida, dentro = [], False
    for n, linha in enumerate(linhas[1:], 2):
        if linha == "---":
            break
        if linha.startswith("fontes:"):
            dentro = True
            continue
        if dentro:
            item = re.match(r'^\s+-\s+"(.*)"\s*$', linha)
            if item:
                saida.append((n, item.group(1)))
            elif linha and not linha[0].isspace():
                dentro = False
    return saida


def _total_de_linhas(arquivo: Path) -> int:
    dados = arquivo.read_bytes()
    return dados.count(b"\n") + (1 if dados and not dados.endswith(b"\n") else 0)


def conferir_entrada(raiz: Path, entrada: str) -> str | None:
    """Motivo do erro, ou None se a entrada está boa."""
    achado = forma(entrada)
    if achado is None:
        return f"fora da gramática do docs/README.md: {entrada!r}"
    nome, m = achado
    if nome not in ("caminho", "repo"):
        return None
    ini, fim = int(m.group("ini")), int(m.group("fim") or m.group("ini"))
    if ini < 1 or fim < ini:
        return f"intervalo inválido em {entrada!r}"
    if nome == "repo":
        return None
    caminho = m.group("caminho")
    arquivo = raiz / caminho
    if caminho.startswith("/") or ".." in Path(caminho).parts or not arquivo.is_file():
        return f"arquivo não existe no repo: {caminho}"
    total = _total_de_linhas(arquivo)
    if fim > total:
        return f"linha {fim} além do fim de {caminho} ({total} linhas)"
    return None


def conferir_armadilha(raiz: Path, texto: str) -> list[tuple[int, str]]:
    """Erros do corpo de uma nota de docs/armadilhas/: entradas da linha
    `- **Fonte:**` e os quatro campos de cada item numerado."""
    erros = []
    linhas = texto.splitlines()
    item, campos, n_item = None, set(), 0

    def fechar():
        if item is not None:
            faltam = [c for c in CAMPOS_DO_ITEM if c not in campos]
            if faltam:
                erros.append((n_item, f"item {item} sem {', '.join(faltam)}"))

    for n, linha in enumerate(linhas, 1):
        novo = _ITEM.match(linha)
        if novo or linha.startswith("## ") or linha.startswith("### "):
            fechar()
            item, campos, n_item = (novo.group(1), set(), n) if novo else (None, set(), 0)
            continue
        for campo in CAMPOS_DO_ITEM:
            if linha.startswith(f"- **{campo}:**"):
                campos.add(campo)
        fonte = _LINHA_FONTE.match(linha)
        if not fonte:
            continue
        entradas = re.findall(r"`([^`]+)`", fonte.group(1))
        if not entradas:
            erros.append((n, "linha Fonte sem entrada entre crases"))
        for entrada in entradas:
            motivo = conferir_entrada(raiz, entrada)
            if motivo:
                erros.append((n, motivo))
    fechar()
    return erros


def checar(raiz: Path) -> list[str]:
    raiz = Path(raiz)
    erros = []
    for nota in notas(raiz):
        texto = nota.read_text(encoding="utf-8")
        nome = nota.relative_to(raiz).as_posix()
        for n, entrada in fontes_do_frontmatter(texto):
            motivo = conferir_entrada(raiz, entrada)
            if motivo:
                erros.append(f"{nome}:{n}: {motivo}")
        if nota.parent == raiz / "docs" / "armadilhas":
            erros += [f"{nome}:{n}: {motivo}" for n, motivo in conferir_armadilha(raiz, texto)]
    return erros


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Confere as fontes caminho:linha de docs/.")
    parser.add_argument("--raiz", type=Path, default=RAIZ, help="checkout a conferir (padrão: este)")
    args = parser.parse_args(argv)
    erros = checar(args.raiz)
    for erro in erros:
        print(erro)
    if erros:
        print(f"checar_fontes: {len(erros)} erro(s).")
        return 1
    print(f"checar_fontes: ok ({len(notas(args.raiz))} notas).")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
