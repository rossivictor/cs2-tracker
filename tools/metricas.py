#!/usr/bin/env python3
"""
Métricas de linhas: a régua da poda da S1 (card S1.0, ex-H1.11).

A S1 mira "pelo menos 500 linhas a menos que a base de 8.028 (raiz + web +
cs2tracker, sem tools/ e tests/)" (plano de 26/09, critério de saída da S1).
Esta ferramenta mede essas linhas hoje, mostra a diferença para a base e,
com --ref, para qualquer ponto do git.

Escopo (o que entra na conta):
  - raiz: os *.py da raiz do repo, sem descer em subpasta;
  - web: os *.py de web/, recursivo;
  - cs2tracker: os *.py de cs2tracker/, recursivo (o pacote ainda pode não
    existir; aí a área sai com 0 arquivos).
  Fora dele, mesmo que tenha .py: tests/, tools/, docs/, docker/, .venv/,
  .claude/ (worktrees dos agentes), __pycache__/ e qualquer outra pasta da
  raiz. Só *.py conta: templates HTML, CSS e JSON da web não entram.

Linha: linha física terminada em quebra, o que `wc -l` conta. É a mesma
régua da base: medida assim, a tag jogavel-2026-09-26 dá exatamente 8.028.
Um resto depois da última quebra (arquivo sem quebra final) não conta.
Cada linha cai em uma de três classes, nesta ordem:
  - comentario: dentro de uma docstring (o literal de string que abre o
    módulo, uma classe ou uma função, achado pelo ast, da primeira à última
    linha dele, inclusive as em branco do meio) ou começando com '#'
    depois dos espaços. Comentário no fim de uma linha de código conta
    como código. Arquivo que não compila fica só com o '#'.
  - branco: só espaços;
  - codigo: o resto.
  total = codigo + comentario + branco.

Grupos (subconjuntos do escopo, mostrados além do total):
  - ingestao: os arquivos de cs2tracker/ingest/ (recursivo) mais os da
    raiz listados em INGESTAO_RAIZ (parser.py, que grava as partidas no
    banco a partir de eventos, CSV ou demo, e watcher.py, que dispara a
    ingestão no fim da partida), quando existem.
  - rcon: os arquivos do escopo que são cliente RCON, achados pelo
    conteúdo: importam o pacote `rcon` (`from rcon...` ou `import rcon`)
    ou implementam o protocolo Source RCON à mão (`SERVERDATA_AUTH`).
  O grupo conta o arquivo inteiro, não só as funções de RCON ou de
  ingestão. A saída lista quais arquivos entraram em cada grupo.

Só leitura e só stdlib: nada de rede, docker, banco, .env nem
docker/events-live. Com --ref, lê o git por `git ls-tree` e `git show`,
sem tocar no checkout.

Uso:
  .venv/Scripts/python.exe tools/metricas.py
  .venv/Scripts/python.exe tools/metricas.py --ref origin/main
  .venv/Scripts/python.exe tools/metricas.py --ref jogavel-2026-09-26 --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Base do plano de 26/09 (raiz + web + cs2tracker, sem tools/ e tests/).
BASE_PLANO_2026_09_26 = 8028
# Meta da S1: pelo menos isso a menos que a base.
META_S1_A_MENOS = 500

AREAS = ("raiz", "web", "cs2tracker")
PASTAS_FORA = ("tests", "tools", "docs", "docker", ".venv", ".claude",
               "__pycache__")
INGESTAO_RAIZ = ("parser.py", "watcher.py")
_RE_RCON = re.compile(
    r"^\s*(from\s+rcon[\s.]|import\s+rcon\b)|SERVERDATA_AUTH", re.MULTILINE)

RAIZ_REPO = Path(__file__).resolve().parent.parent


@dataclass
class Contagem:
    codigo: int = 0
    comentario: int = 0
    branco: int = 0

    @property
    def total(self) -> int:
        return self.codigo + self.comentario + self.branco

    def somar(self, outra: "Contagem") -> None:
        self.codigo += outra.codigo
        self.comentario += outra.comentario
        self.branco += outra.branco

    def como_dict(self) -> dict:
        return {"total": self.total, "codigo": self.codigo,
                "comentario": self.comentario, "branco": self.branco}


@dataclass
class Grupo:
    contagem: Contagem = field(default_factory=Contagem)
    arquivos: list = field(default_factory=list)

    def incluir(self, caminho: str, c: Contagem) -> None:
        self.contagem.somar(c)
        self.arquivos.append(caminho)

    def como_dict(self) -> dict:
        return {**self.contagem.como_dict(), "arquivos": sorted(self.arquivos)}


def _linhas_de_docstring(texto: str) -> set:
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return set()
    linhas = set()
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef,
                               ast.AsyncFunctionDef)):
            continue
        corpo = no.body
        if (corpo and isinstance(corpo[0], ast.Expr)
                and isinstance(corpo[0].value, ast.Constant)
                and isinstance(corpo[0].value.value, str)):
            doc = corpo[0]
            linhas.update(range(doc.lineno, doc.end_lineno + 1))
    return linhas


def contar_texto(texto: str) -> Contagem:
    """Classifica as linhas físicas de um fonte Python (ver docstring)."""
    c = Contagem()
    docs = _linhas_de_docstring(texto)
    # Só as linhas com quebra, como o wc -l (ver docstring).
    for n, linha in enumerate(texto.split("\n")[:-1], start=1):
        limpa = linha.strip()
        if n in docs or limpa.startswith("#"):
            c.comentario += 1
        elif not limpa:
            c.branco += 1
        else:
            c.codigo += 1
    return c


def area_de(caminho: str):
    """Área do caminho relativo (com '/'), ou None se está fora do escopo."""
    partes = caminho.split("/")
    if not partes[-1].endswith(".py"):
        return None
    if "__pycache__" in partes:
        return None
    if len(partes) == 1:
        return "raiz"
    if partes[0] in ("web", "cs2tracker"):
        return partes[0]
    return None


def eh_ingestao(caminho: str) -> bool:
    return caminho in INGESTAO_RAIZ or caminho.startswith("cs2tracker/ingest/")


def eh_rcon(texto: str) -> bool:
    return bool(_RE_RCON.search(texto))


def medir(fontes) -> dict:
    """fontes: iterável de (caminho relativo com '/', texto)."""
    areas = {a: Grupo() for a in AREAS}
    total = Contagem()
    ingestao, rcon = Grupo(), Grupo()
    for caminho, texto in fontes:
        area = area_de(caminho)
        if area is None:
            continue
        c = contar_texto(texto)
        areas[area].incluir(caminho, c)
        total.somar(c)
        if eh_ingestao(caminho):
            ingestao.incluir(caminho, c)
        if eh_rcon(texto):
            rcon.incluir(caminho, c)
    return {
        "total": total.como_dict(),
        "base": BASE_PLANO_2026_09_26,
        "diferenca_base": total.total - BASE_PLANO_2026_09_26,
        "areas": {a: g.como_dict() for a, g in areas.items()},
        "ingestao": ingestao.como_dict(),
        "rcon": rcon.como_dict(),
    }


def _ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def fontes_do_disco(raiz: Path):
    """Arquivos do escopo na árvore de trabalho, sem seguir PASTAS_FORA."""
    for p in sorted(raiz.glob("*.py")):
        if p.is_file():
            yield p.name, _ler(p)
    for area in ("web", "cs2tracker"):
        base = raiz / area
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            rel = p.relative_to(raiz).as_posix()
            if p.is_file() and not set(rel.split("/")) & set(PASTAS_FORA):
                yield rel, _ler(p)


def _git(raiz: Path, *args) -> str:
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True,
                       check=True)
    return r.stdout.decode("utf-8", errors="replace")


def fontes_do_git(raiz: Path, ref: str):
    """Arquivos do escopo no ref, lidos por git show (sem tocar no checkout)."""
    for caminho in sorted(_git(raiz, "ls-tree", "-r", "--name-only", ref,
                               "--", ".").splitlines()):
        if area_de(caminho) is not None:
            yield caminho, _git(raiz, "show", f"{ref}:{caminho}")


def _linha(nome: str, d: dict) -> str:
    return (f"  {nome:<11} {d['total']:>6}  (codigo {d['codigo']}, "
            f"comentario {d['comentario']}, branco {d['branco']})")


def formatar(hoje: dict, ref_nome=None, no_ref=None) -> str:
    t = hoje["total"]["total"]
    out = ["Linhas do escopo (raiz + web + cs2tracker, só *.py, sem tools/ "
           "e tests/)", _linha("total", hoje["total"])]
    for a in AREAS:
        out.append(_linha(a, hoje["areas"][a]))
    falta = t - (BASE_PLANO_2026_09_26 - META_S1_A_MENOS)
    out.append(f"Base do plano de 26/09: {BASE_PLANO_2026_09_26}; hoje: {t}; "
               f"diferença: {hoje['diferenca_base']:+d}")
    out.append(f"Meta da S1 (base - {META_S1_A_MENOS} = "
               f"{BASE_PLANO_2026_09_26 - META_S1_A_MENOS}): "
               + ("atingida" if falta <= 0 else f"faltam {falta} linhas"))
    for nome in ("ingestao", "rcon"):
        g = hoje[nome]
        out.append(_linha(nome, g))
        for arq in g["arquivos"]:
            out.append(f"    - {arq}")
    out.append(f"Comentários no escopo: {hoje['total']['comentario']}")
    if no_ref is not None:
        r = no_ref["total"]["total"]
        out.append(f"No ref {ref_nome}: {r}; agora: {t}; "
                   f"diferença: {t - r:+d}")
        for a in AREAS:
            ra, ha = no_ref["areas"][a]["total"], hoje["areas"][a]["total"]
            out.append(f"  {a:<11} {ra:>6} -> {ha:>6} ({ha - ra:+d})")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--raiz", type=Path, default=RAIZ_REPO,
                    help="raiz do repo (padrão: a deste arquivo)")
    ap.add_argument("--ref", help="ref git para comparar (ex.: origin/main)")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    hoje = medir(fontes_do_disco(args.raiz))
    no_ref = None
    if args.ref:
        try:
            no_ref = medir(fontes_do_git(args.raiz, args.ref))
        except (subprocess.CalledProcessError, OSError) as e:
            print(f"metricas: não li o ref {args.ref!r}: {e}", file=sys.stderr)
            return 2
    if args.json:
        saida = {"hoje": hoje}
        if no_ref is not None:
            saida["ref"] = {"nome": args.ref, **no_ref}
        print(json.dumps(saida, ensure_ascii=False, indent=2))
    else:
        print(formatar(hoje, args.ref, no_ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
