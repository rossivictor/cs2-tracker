#!/usr/bin/env python3
"""
Confere as fontes da KB (card K1.4): cada `caminho:N` de docs/ aponta para um
arquivo que existe neste repo, e a linha N (ou o intervalo N-M) cabe nele.

O que é lido, sempre em docs/**/*.md (sem o vault docs/board-cs2/ e sem pasta
oculta, como no tests/test_base_de_conhecimento.py):

1. As entradas de `fontes` do frontmatter, pela gramática do docs/README.md
   (seção "Frontmatter padrão"). Fecha em erro, porque vai ser trava de CI:
   sob `fontes:`, toda linha não vazia até a próxima chave tem de ser
   `  - "entrada"`; `fontes:` com valor na mesma linha (lista inline), item
   sem aspas duplas e frontmatter aberto sem `---` de fechamento são erro.
   O BOM do UTF-8 no começo da nota é ignorado; nota que não é UTF-8 é erro.
2. Em docs/armadilhas/ (e subpastas), a linha `- **Fonte:**` de cada item,
   com as linhas recuadas logo abaixo dela. Ali cada entrada vai entre
   crases, com a mesma gramática; o texto fora das crases é só para quem lê.
   Item numerado (`### N. título`) precisa ter as quatro linhas, Sintoma,
   Causa, Contorno e Fonte, nenhuma vazia, e pelo menos uma fonte
   `caminho:N` ou `repo:`.

O que se confere em cada entrada:

- `caminho:N` e `caminho:N-M`: forma, intervalo não invertido, caminho com
  `/` (nunca `\\`), relativo, sem `..`, que resolvido (link e junction
  inclusive) fica dentro da raiz, arquivo existente escrito como no disco e
  linha dentro do arquivo. A linha só diz que o trecho existe; se ele ainda
  diz o que a nota afirma é revisão humana.
- `repo:<nome> caminho:N`, `backup:...`, `transcript ...`, `commit ...` e
  `PR #n`: só a forma. Outro repositório, backup e sessão ficam fora deste
  checkout, e commit pode não estar no clone.

Raiz sem docs/ ou sem nota é erro (protege de `--raiz` digitado errado).
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
_CAMPO = re.compile(r"^- \*\*(Sintoma|Causa|Contorno|Fonte):\*\*(.*)$")
_CRASES = re.compile(r"`([^`]+)`")
_CHAVE_FONTES = re.compile(r"^fontes\s*:(.*)$")
_ITEM_DE_FONTES = re.compile(r'^ +- +"([^"]*)"\s*$')
_CHAVE = re.compile(r"^[A-Za-z_][\w-]*\s*:")
_BOM = "\ufeff"


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


def ler_frontmatter(texto: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(fontes, erros) do frontmatter inicial, cada um como (linha da nota, texto).

    Sem frontmatter (a primeira linha não é `---`), as duas listas vêm vazias.
    """
    linhas = texto.removeprefix(_BOM).splitlines()
    if not linhas or linhas[0].rstrip() != "---":
        return [], []
    fontes, erros, dentro = [], [], False
    for n, linha in enumerate(linhas[1:], 2):
        if linha.rstrip() == "---":
            return fontes, erros
        chave = _CHAVE_FONTES.match(linha)
        if chave:
            dentro = True
            if chave.group(1).strip():
                erros.append((n, f"`fontes:` com valor na mesma linha, fora da gramática: {linha.strip()!r}"))
            continue
        if not dentro or not linha.strip():
            continue
        item = _ITEM_DE_FONTES.match(linha)
        if item:
            fontes.append((n, item.group(1)))
        elif _CHAVE.match(linha):
            dentro = False
        else:
            erros.append((n, f"item de `fontes` fora da gramática (use `  - \"...\"`): {linha.strip()!r}"))
    # Sem fechamento, o corpo inteiro passaria por frontmatter: o resto é ruído.
    return [], [(1, "frontmatter aberto sem `---` de fechamento")]


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
    if "\\" in caminho:
        return f"caminho com barra invertida (use /): {caminho}"
    if caminho.startswith("/"):
        return f"caminho absoluto (use relativo à raiz): {caminho}"
    if ".." in caminho.split("/"):
        return f"caminho sai do repo: {caminho}"
    base = Path(raiz).resolve()
    arquivo = base / caminho
    try:
        relativo = arquivo.resolve().relative_to(base).as_posix()
    except (OSError, ValueError):
        return f"caminho resolve fora do repo (link ou junction): {caminho}"
    if not arquivo.is_file():
        return f"arquivo não existe no repo: {caminho}"
    if relativo != caminho:
        return f"caminho difere do arquivo no repo ({relativo}): {caminho}"
    total = _total_de_linhas(arquivo)
    if fim > total:
        return f"linha {fim} além do fim de {caminho} ({total} linhas)"
    return None


def conferir_armadilha(raiz: Path, texto: str) -> list[tuple[int, str]]:
    """Erros do corpo de uma nota de docs/armadilhas/: entradas da linha
    `- **Fonte:**` (e das linhas recuadas logo abaixo) e os quatro campos de
    cada item numerado."""
    erros = []
    item, n_item, campos, com_entrada, com_codigo = None, 0, set(), False, False
    fonte_n, fonte_qtd = None, 0  # linha da Fonte aberta e quantas entradas ela tem

    def fechar_fonte():
        if fonte_n is not None and fonte_qtd == 0:
            erros.append((fonte_n, "linha Fonte sem entrada entre crases"))

    def fechar_item():
        if item is None:
            return
        faltam = [c for c in CAMPOS_DO_ITEM if c not in campos]
        if faltam:
            erros.append((n_item, f"item {item} sem {', '.join(faltam)}"))
        elif com_entrada and not com_codigo:
            erros.append((n_item, f"item {item} sem fonte `caminho:N` nem `repo:`"))

    for n, linha in enumerate(texto.removeprefix(_BOM).splitlines(), 1):
        if fonte_n is not None and linha[:1].isspace() and linha.strip():
            entradas = _CRASES.findall(linha)
        else:
            fechar_fonte()
            fonte_n = None
            novo = _ITEM.match(linha)
            if novo or linha.startswith("## ") or linha.startswith("### "):
                fechar_item()
                item, n_item = (novo.group(1), n) if novo else (None, 0)
                campos, com_entrada, com_codigo = set(), False, False
                continue
            campo = _CAMPO.match(linha)
            if not campo:
                continue
            nome, resto = campo.groups()
            campos.add(nome)
            if not resto.strip():
                erros.append((n, f"campo {nome} vazio"))
                continue
            if nome != "Fonte":
                continue
            fonte_n, fonte_qtd = n, 0
            entradas = _CRASES.findall(resto)
        fonte_qtd += len(entradas)
        for entrada in entradas:
            com_entrada = True
            achado = forma(entrada)
            com_codigo = com_codigo or (achado is not None and achado[0] in ("caminho", "repo"))
            motivo = conferir_entrada(raiz, entrada)
            if motivo:
                erros.append((n, motivo))
    fechar_fonte()
    fechar_item()
    return erros


def checar(raiz: Path) -> list[str]:
    raiz = Path(raiz)
    docs = raiz / "docs"
    if not docs.is_dir():
        return [f"{raiz.as_posix()}: sem pasta docs/ (a --raiz aponta para um checkout?)"]
    lista = notas(raiz)
    if not lista:
        return [f"{docs.as_posix()}: nenhuma nota .md para conferir"]
    erros = []
    for nota in lista:
        nome = nota.relative_to(raiz).as_posix()
        try:
            texto = nota.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            erros.append(f"{nome}: não é UTF-8")
            continue
        fontes, achados = ler_frontmatter(texto)
        for n, entrada in fontes:
            motivo = conferir_entrada(raiz, entrada)
            if motivo:
                achados.append((n, motivo))
        if nota.relative_to(docs).parts[0] == "armadilhas":
            achados += conferir_armadilha(raiz, texto)
        erros += [f"{nome}:{n}: {motivo}" for n, motivo in sorted(achados, key=lambda a: a[0])]
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
