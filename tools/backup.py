#!/usr/bin/env python3
"""
Backup do que o jogo produz e não é reproduzível (card B0.6), sem tocar no
jogo: banco, captura, perfil, logs e board. Tudo na origem é só lido; nada
nela muda, nem o mtime.

O que vai para o destino:
  - banco: cópia pela API de backup do SQLite, com a origem aberta em
    mode=ro. No destino roda `PRAGMA integrity_check` e conta as linhas de
    `matches` (tabela ausente fica anotada, sem quebrar). A cópia se chama
    cs2_tracker.backup.db para nunca ser confundida com o banco vivo;
  - pastas copiadas com shutil.copy2: docker/events-live (current e
    arquivados), logs e docs/board-cs2 (o vault do Obsidian, fora do git:
    ADR-0002); arquivo data/profile.json;
  - docker/plugins/*/: nenhum binário é copiado. Cada pasta vira um
    manifesto sha256 (arquivo, bytes, sha256) em plugins/<nome>.sha256, no
    formato do sha256sum, e no MANIFESTO.json;
  - MANIFESTO.json e MANIFESTO.txt (resumo legível), escritos por último:
    backup sem manifesto é backup interrompido.
O que não existe na origem é pulado e dito no manifesto.

Preflight (tools/preflight.py) antes de ler qualquer coisa:
  0 livre          segue;
  4 janela aberta  segue: o backup só lê, não mexe no servidor;
  3 (ou qualquer outro código) Victor jogando ou sem certeza: recusa, a não
                   ser com --leitura-com-jogo. Com a flag, a leitura acontece
                   com o jogo aberto; o banco sai consistente pela API de
                   backup, mas o current.jsonl pode estar no meio de uma
                   partida. O manifesto registra a flag.

Os caminhos seguem os padrões do config.py (./cs2_tracker.db,
./docker/events-live). Como o preflight, este script não lê o .env: se o
banco ou a captura foram mudados de lugar por lá, o backup não os acha e
diz "ausente" no manifesto.

Códigos de saída: 0 ok; 1 backup feito com problema (banco ausente, integridade,
erro de cópia); 2 uso errado (argumento, destino que já existe ou dentro da
origem); 3 recusado pelo preflight.

Só biblioteca padrão. O primeiro backup real é do Victor ou do PM, do
checkout principal (ou de uma worktree: a origem padrão é sempre o checkout
principal):
    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/backup.py
    ... tools/backup.py --destino D:/outro/lugar --leitura-com-jogo
Destino padrão: C:/Users/Victor/cs2-tracker-backups/<AAAA-MM-DD>/backup-<HHMM>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight  # noqa: E402

RAIZ_BACKUPS = Path("C:/Users/Victor/cs2-tracker-backups")
BANCO = Path("cs2_tracker.db")  # padrão de config.DB_PATH
BANCO_NO_DESTINO = "cs2_tracker.backup.db"
PASTAS = (Path("docker/events-live"), Path("logs"), Path("docs/board-cs2"))
ARQUIVOS = (Path("data/profile.json"),)
PLUGINS = Path("docker/plugins")

OK, COM_PROBLEMA, USO, RECUSADO = 0, 1, 2, 3
LIBERADO = (preflight.LIVRE, preflight.JANELA)

Preflight = Callable[[Path], "preflight.Resultado"]


class ErroDeUso(Exception):
    """Argumento que o backup não aceita. Vira código 2."""


def consultar_preflight(origem: Path, listar=preflight.listar_processos):
    return preflight.avaliar(raiz=origem, listar=listar)


def destino_padrao(agora: datetime) -> Path:
    return RAIZ_BACKUPS / agora.strftime("%Y-%m-%d") / agora.strftime("backup-%H%M")


def _sha256(arquivo: Path) -> str:
    h = hashlib.sha256()
    with arquivo.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# ------------------------------------------------------------- banco

def copiar_banco(origem: Path, destino: Path) -> dict:
    fonte = origem / BANCO
    info = {"origem": BANCO.as_posix(), "arquivo": BANCO_NO_DESTINO}
    if not fonte.is_file():
        return {**info, "status": "ausente"}
    alvo = destino / BANCO_NO_DESTINO
    try:
        src = sqlite3.connect(fonte.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            dst = sqlite3.connect(alvo)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        leitura = sqlite3.connect(alvo.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            integridade = [linha[0] for linha in leitura.execute("PRAGMA integrity_check")]
            tem_matches = leitura.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='matches'").fetchone()
            matches = (leitura.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
                       if tem_matches else None)
        finally:
            leitura.close()
    except sqlite3.Error as exc:
        return {**info, "status": "erro", "erro": f"{exc.__class__.__name__}: {exc}"}
    info.update(status="copiado" if integridade == ["ok"] else "erro",
                bytes=alvo.stat().st_size, sha256=_sha256(alvo),
                integrity_check=integridade, matches=matches)
    if matches is None:
        info["observacao"] = "tabela matches ausente"
    return info


# ------------------------------------------------------ pastas e arquivos

def copiar_pasta(origem: Path, destino: Path, rel: Path) -> dict:
    fonte = origem / rel
    info = {"origem": rel.as_posix()}
    if not fonte.is_dir():
        return {**info, "status": "ausente"}
    erros = []
    try:
        shutil.copytree(fonte, destino / rel, copy_function=shutil.copy2)
    except shutil.Error as exc:  # copia o resto e junta as falhas no fim
        erros = [f"{a}: {motivo}" for a, _b, motivo in exc.args[0]]
    except OSError as exc:
        erros = [f"{exc.__class__.__name__}: {exc}"]
    copiados = [p for p in (destino / rel).rglob("*") if p.is_file()]
    info.update(status="erro" if erros else "copiado", arquivos=len(copiados),
                bytes=sum(p.stat().st_size for p in copiados))
    if erros:
        info["erros"] = erros
    return info


def copiar_arquivo(origem: Path, destino: Path, rel: Path) -> dict:
    fonte = origem / rel
    info = {"origem": rel.as_posix()}
    if not fonte.is_file():
        return {**info, "status": "ausente"}
    try:
        (destino / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fonte, destino / rel)
    except OSError as exc:
        return {**info, "status": "erro", "erros": [f"{exc.__class__.__name__}: {exc}"]}
    return {**info, "status": "copiado", "bytes": fonte.stat().st_size}


def manifestar_plugins(origem: Path, destino: Path) -> dict:
    """Uma entrada por pasta docker/plugins/*/, sem copiar nenhum binário."""
    raiz = origem / PLUGINS
    if not raiz.is_dir():
        return {}
    saida = destino / "plugins"
    manifestos = {}
    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir()):
        arquivos = sorted((a for a in pasta.rglob("*") if a.is_file()),
                          key=lambda a: a.relative_to(pasta).as_posix())
        itens = [{"arquivo": a.relative_to(pasta).as_posix(), "bytes": a.stat().st_size,
                  "sha256": _sha256(a)} for a in arquivos]
        manifestos[pasta.name] = itens
        saida.mkdir(exist_ok=True)
        (saida / f"{pasta.name}.sha256").write_text(
            "".join(f"{i['sha256']}  {i['arquivo']}\n" for i in itens), encoding="utf-8")
    return manifestos


# ------------------------------------------------------------- manifesto

def _resumo(m: dict) -> str:
    linhas = [f"Backup do cs2-tracker em {m['criado_em']}",
              f"origem: {m['origem']}",
              f"preflight {m['preflight']['codigo']}: {m['preflight']['motivo']}"]
    if m["leitura_com_jogo"]:
        linhas.append("feito com --leitura-com-jogo")
    b = m["banco"]
    linha = f"banco: {b['status']}"
    if "integrity_check" in b:
        linha += f", integrity_check {'; '.join(b['integrity_check'])}"
        linha += f", matches {b['matches'] if b['matches'] is not None else 'sem tabela'}"
    linhas.append(linha + (f" ({b['erro']})" if "erro" in b else ""))
    for item in m["pastas"] + m["arquivos"]:
        extra = f", {item['arquivos']} arquivos" if "arquivos" in item else ""
        linhas.append(f"{item['origem']}: {item['status']}{extra}")
    for nome, itens in m["plugins"].items():
        linhas.append(f"docker/plugins/{nome}: {len(itens)} arquivos por sha256 "
                      f"(plugins/{nome}.sha256)")
    linhas.append("resultado: " + ("OK" if not m["problemas"] else
                                   "COM PROBLEMA: " + "; ".join(m["problemas"])))
    return "\n".join(linhas) + "\n"


def fazer_backup(origem: Path, destino: Path, resultado_preflight, leitura_com_jogo: bool,
                 agora: datetime) -> dict:
    destino.mkdir(parents=True)
    m = {"versao": 1, "card": "B0.6", "criado_em": agora.isoformat(timespec="seconds"),
         "origem": origem.as_posix(), "destino": destino.as_posix(),
         "preflight": {"codigo": resultado_preflight.codigo,
                       "motivo": resultado_preflight.motivo},
         "leitura_com_jogo": leitura_com_jogo,
         "banco": copiar_banco(origem, destino),
         "pastas": [copiar_pasta(origem, destino, rel) for rel in PASTAS],
         "arquivos": [copiar_arquivo(origem, destino, rel) for rel in ARQUIVOS],
         "plugins": manifestar_plugins(origem, destino)}
    # banco ausente é problema; pasta ou arquivo ausente só fica anotado
    falhas = [m["banco"]] if m["banco"]["status"] != "copiado" else []
    falhas += [item for item in m["pastas"] + m["arquivos"] if item["status"] == "erro"]
    m["problemas"] = [f"{item['origem']}: {item['status']}" for item in falhas]
    (destino / "MANIFESTO.json").write_text(
        json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / "MANIFESTO.txt").write_text(_resumo(m), encoding="utf-8")
    return m


def _validar(origem: Path, destino: Path) -> None:
    if not origem.is_dir():
        raise ErroDeUso(f"origem {origem} não é uma pasta")
    if destino.exists():
        raise ErroDeUso(f"destino {destino} já existe; o backup não sobrescreve")
    if destino.resolve().is_relative_to(origem.resolve()):
        raise ErroDeUso(f"destino {destino} fica dentro da origem: o repositório é "
                        "público e o backup leva dado pessoal")


def main(argv: Optional[list] = None, consultar: Preflight = consultar_preflight,
         agora: Optional[datetime] = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):  # em pipe o padrão seria cp1252
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(
        description="Backup só leitura de banco, events-live, perfil, logs e board, com "
                    "manifesto sha256 dos plugins. Recusa com o Victor jogando (preflight 3).",
        epilog="Saída: 0 ok, 1 feito com problema, 2 uso errado, 3 recusado pelo preflight. "
               "Rode com o Python da .venv: tools/backup.py [--destino PASTA_NOVA]. "
               "Detalhes no início de tools/backup.py.")
    parser.add_argument("--origem", type=Path, default=None,
                        help="checkout a copiar; padrão: o checkout principal")
    parser.add_argument("--destino", type=Path, default=None,
                        help="pasta nova do backup; padrão: "
                             f"{RAIZ_BACKUPS.as_posix()}/<AAAA-MM-DD>/backup-<HHMM>")
    parser.add_argument("--leitura-com-jogo", action="store_true",
                        help="lê mesmo com preflight 3 (Victor jogando ou sem certeza)")
    args = parser.parse_args(argv)
    momento = agora or datetime.now()
    try:
        origem = args.origem or preflight.resolver_raiz_principal(preflight.raiz_do_script())
        destino = args.destino or destino_padrao(momento)
        _validar(origem, destino)
        origem, destino = origem.absolute(), destino.absolute()
    except (ErroDeUso, preflight.DeteccaoFalhou) as exc:
        print(f"backup: {exc}", file=sys.stderr)
        return USO

    resultado = consultar(origem)
    if resultado.codigo not in LIBERADO and not args.leitura_com_jogo:
        print(f"preflight {resultado.codigo}: {resultado.motivo}")
        print("backup recusado: o Victor pode estar jogando. Rode depois da partida, ou "
              "com --leitura-com-jogo se precisar ler assim mesmo.", file=sys.stderr)
        return RECUSADO

    m = fazer_backup(origem, destino, resultado, args.leitura_com_jogo, momento)
    print(_resumo(m), end="")
    print(f"backup em {destino}")
    return COM_PROBLEMA if m["problemas"] else OK


if __name__ == "__main__":
    sys.exit(main())
