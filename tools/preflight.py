#!/usr/bin/env python3
"""
Preflight: diz se dá pra mexer em coisa viva (servidor, container, RCON,
banco) agora. Rode ANTES de tocar em qualquer coisa que o Victor usa pra
jogar (AGENTS.md, "Preflight"; card B0.4).

Códigos de saída (protocolo de jogabilidade, seção 10 do plano):

  0  livre: nenhum sinal de partida e nenhuma janela aberta
  3  Victor jogando, ou não deu pra ter certeza (falha segura)
  4  janela de manutenção aberta

O 3 tem precedência sobre o 4: com o Victor jogando, nem janela aberta
libera o servidor.

Sinais de "Victor jogando" (qualquer um basta):
  - processo cs2.exe rodando;
  - processo python rodando wizard_tui.py, watcher.py ou start_match.py
    (como script ou com -m). `pytest tests/test_watcher.py` não conta: o que
    vale é o nome do script, não um pedaço dele;
  - docker/events-live/current.jsonl modificado há menos de 10 min. Só o
    mtime é consultado; o conteúdo nunca é lido.

Janela aberta: existe logs/janelas/ABERTA.

Se a própria detecção falhar (nenhum jeito de listar processos, python com
linha de comando ilegível, erro de E/S), a resposta é 3: sem certeza, trata
como se ele estivesse jogando.

Rodado de dentro de uma worktree de agente, olha o checkout PRINCIPAL
(resolvido pelo arquivo .git da worktree), porque é lá que ficam
docker/events-live e logs/janelas. O caminho de events-live é o padrão
(./docker/events-live): o preflight não lê o .env.

Só biblioteca padrão. Uso:
    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py
    C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py --raiz <checkout>
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

LIVRE = 0
JOGANDO = 3
JANELA = 4

# current.jsonl mexido há menos que isso = partida em curso (seção 10).
JANELA_CURRENT_JSONL_S = 10 * 60

CURRENT_JSONL = Path("docker") / "events-live" / "current.jsonl"
MARCA_JANELA = Path("logs") / "janelas" / "ABERTA"

SCRIPTS_DO_JOGO = ("wizard_tui", "watcher", "start_match")
_SCRIPTS = "|".join(SCRIPTS_DO_JOGO)
# "...\python.exe wizard_tui.py", "python -u watcher.py --mode matchzy",
# "python C:\...\start_match.py": o nome do script é um token inteiro,
# precedido de início, espaço, aspas, barra ou contrabarra.
_RE_SCRIPT = re.compile(
    rf"""(?:^|[\s"'\\/])({_SCRIPTS})\.py(?=$|[\s"'])""", re.IGNORECASE
)
# "python -m wizard_tui"
_RE_MODULO = re.compile(
    rf"""(?:^|\s)-m\s+["']?({_SCRIPTS})(?=$|[\s"'])""", re.IGNORECASE
)

TIMEOUT_LISTAGEM_S = 30


class DeteccaoFalhou(Exception):
    """Não deu pra saber se o Victor está jogando. Vira código 3."""


@dataclass(frozen=True)
class Processo:
    pid: int
    nome: str
    # None = a ferramenta de listagem não informa a linha de comando
    # (tasklist) ou o Windows não a entregou.
    linha: Optional[str]


@dataclass(frozen=True)
class Resultado:
    codigo: int
    motivo: str


Executor = Callable[..., "subprocess.CompletedProcess[bytes]"]
Listador = Callable[[], "list[Processo]"]


# ---------------------------------------------------------------- raiz

def raiz_do_script() -> Path:
    return Path(__file__).resolve().parent.parent


def resolver_raiz_principal(raiz: Path) -> Path:
    """Devolve o checkout principal a partir de um checkout ou worktree.

    Numa worktree, `.git` é um arquivo "gitdir: <repo>/.git/worktrees/<nome>",
    e esse diretório tem um `commondir` apontando pro .git principal.
    """
    git = raiz / ".git"
    if git.is_dir():
        return raiz
    if not git.is_file():
        raise DeteccaoFalhou(f"{raiz} não é um checkout git (sem .git)")
    conteudo = git.read_text(encoding="utf-8").strip()
    if not conteudo.startswith("gitdir:"):
        raise DeteccaoFalhou(f"{git} não aponta pra um gitdir")
    gitdir = Path(conteudo[len("gitdir:"):].strip())
    if not gitdir.is_absolute():
        gitdir = raiz / gitdir
    commondir = gitdir / "commondir"
    if not commondir.is_file():
        raise DeteccaoFalhou(f"{gitdir} não tem commondir")
    comum = Path(commondir.read_text(encoding="utf-8").strip())
    if not comum.is_absolute():
        comum = gitdir / comum
    principal = comum.resolve().parent
    if not (principal / ".git").is_dir():
        raise DeteccaoFalhou(f"checkout principal não encontrado em {principal}")
    return principal


# ---------------------------------------------------------- processos

def _exe_do_sistema(nome: str) -> str:
    """Caminho absoluto em System32 quando existe (hook pode rodar com PATH
    mínimo); senão, o nome puro, resolvido pelo PATH."""
    raiz_win = os.environ.get("SystemRoot") or os.environ.get("windir")
    if raiz_win:
        for sub in ("System32", r"System32\WindowsPowerShell\v1.0"):
            candidato = Path(raiz_win) / sub / nome
            if candidato.is_file():
                return str(candidato)
    return nome


def _decodificar(saida: bytes) -> str:
    # wmic redirecionado escreve UTF-16; o resto sai em UTF-8 ou na página
    # OEM. Os marcadores procurados são ASCII, então "replace" basta.
    if saida.startswith(b"\xff\xfe") or (len(saida) > 1 and saida[1:2] == b"\x00"):
        return saida.decode("utf-16", errors="replace")
    try:
        return saida.decode("utf-8")
    except UnicodeDecodeError:
        return saida.decode("cp850", errors="replace")


def _rodar(executar: Executor, argv: list) -> str:
    # Chamado de um hook, sem console: não deixa o Windows piscar janela.
    extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        proc = executar(argv, capture_output=True, timeout=TIMEOUT_LISTAGEM_S, **extra)
    except (OSError, subprocess.SubprocessError) as exc:
        raise DeteccaoFalhou(f"{Path(argv[0]).name}: {exc.__class__.__name__}") from exc
    if proc.returncode != 0:
        raise DeteccaoFalhou(f"{Path(argv[0]).name} saiu com {proc.returncode}")
    return _decodificar(proc.stdout or b"")


def via_powershell(executar: Executor = subprocess.run) -> list:
    comando = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    texto = _rodar(executar, [_exe_do_sistema("powershell.exe"),
                              "-NoProfile", "-NonInteractive", "-Command", comando])
    texto = texto.strip().lstrip("﻿")
    if not texto:
        raise DeteccaoFalhou("Get-CimInstance não devolveu nada")
    try:
        dados = json.loads(texto)
    except ValueError as exc:
        raise DeteccaoFalhou("Get-CimInstance devolveu JSON inválido") from exc
    if isinstance(dados, dict):
        dados = [dados]
    processos = []
    for item in dados:
        processos.append(Processo(pid=int(item.get("ProcessId") or 0),
                                  nome=str(item.get("Name") or ""),
                                  linha=item.get("CommandLine")))
    return processos


def via_wmic(executar: Executor = subprocess.run) -> list:
    texto = _rodar(executar, [_exe_do_sistema("wmic.exe"), "process", "get",
                              "ProcessId,Name,CommandLine", "/format:csv"])
    processos = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("Node,"):
            continue
        # Colunas em ordem alfabética: Node,CommandLine,Name,ProcessId. A
        # linha de comando pode ter vírgula e o wmic não põe aspas: corta o
        # Node pela esquerda e Name/ProcessId pela direita.
        partes = linha.split(",", 1)
        if len(partes) != 2:
            continue
        resto = partes[1].rsplit(",", 2)
        if len(resto) != 3:
            continue
        cmd, nome, pid = resto
        try:
            pid_int = int(pid)
        except ValueError:
            continue
        processos.append(Processo(pid=pid_int, nome=nome, linha=cmd or None))
    if not processos:
        raise DeteccaoFalhou("wmic não devolveu processos")
    return processos


def via_tasklist(executar: Executor = subprocess.run) -> list:
    texto = _rodar(executar, [_exe_do_sistema("tasklist.exe"), "/FO", "CSV", "/NH"])
    processos = []
    for linha in csv.reader(io.StringIO(texto)):
        if len(linha) < 2:
            continue
        try:
            pid = int(linha[1])
        except ValueError:
            continue
        processos.append(Processo(pid=pid, nome=linha[0], linha=None))
    if not processos:
        raise DeteccaoFalhou("tasklist não devolveu processos")
    return processos


LISTADORES = (via_powershell, via_wmic, via_tasklist)


def listar_processos(executar: Executor = subprocess.run) -> list:
    """Tenta PowerShell (Get-CimInstance), wmic e tasklist, nessa ordem.
    Só o tasklist não dá a linha de comando: aí python vira falha segura."""
    falhas = []
    for listador in LISTADORES:
        try:
            return listador(executar)
        except DeteccaoFalhou as exc:
            falhas.append(str(exc))
        except Exception as exc:  # saída estranha: tenta o próximo método
            falhas.append(f"{listador.__name__}: {exc.__class__.__name__}")
    raise DeteccaoFalhou("não deu pra listar os processos (" + "; ".join(falhas) + ")")


def _eh_python(nome: str) -> bool:
    base = nome.lower()
    if base.endswith(".exe"):
        base = base[:-4]
    return base.startswith("python") or base in ("py", "pyw")


def script_do_jogo(linha: str) -> Optional[str]:
    """Nome do script do jogo que a linha de comando roda, ou None."""
    achado = _RE_SCRIPT.search(linha) or _RE_MODULO.search(linha)
    return achado.group(1).lower() if achado else None


def sinais_nos_processos(processos: list, proprios: frozenset = frozenset()) -> list:
    """Sinais de jogo na lista de processos.

    `proprios` são os PIDs do próprio preflight e do lançador da .venv que o
    chamou: sem linha de comando (tasklist), eles não contam como python
    suspeito; senão o fallback do tasklist sempre se veria e daria 3.
    """
    sinais = []
    sem_linha = []
    for p in processos:
        nome = p.nome.lower()
        if nome in ("cs2.exe", "cs2"):
            sinais.append(f"cs2.exe (PID {p.pid})")
        elif _eh_python(nome):
            if p.linha is None:
                if p.pid not in proprios:
                    sem_linha.append(p.pid)
                continue
            script = script_do_jogo(p.linha)
            if script:
                sinais.append(f"python {script} (PID {p.pid})")
    if sem_linha and not sinais:
        pids = ", ".join(str(pid) for pid in sem_linha)
        raise DeteccaoFalhou(f"python sem linha de comando legível (PID {pids})")
    return sinais


# ----------------------------------------------------------- arquivos

def sinal_current_jsonl(raiz: Path, agora: float) -> Optional[str]:
    caminho = raiz / CURRENT_JSONL
    try:
        mtime = caminho.stat().st_mtime
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DeteccaoFalhou(f"não deu pra consultar {CURRENT_JSONL.as_posix()}: "
                             f"{exc.__class__.__name__}") from exc
    idade = agora - mtime
    # mtime no futuro (relógio do container adiantado) conta como recente.
    if idade < JANELA_CURRENT_JSONL_S:
        minutos = max(0, int(idade // 60))
        return f"current.jsonl modificado há {minutos} min"
    return None


def janela_aberta(raiz: Path) -> bool:
    marca = raiz / MARCA_JANELA
    try:
        marca.stat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise DeteccaoFalhou(f"não deu pra consultar {MARCA_JANELA.as_posix()}: "
                             f"{exc.__class__.__name__}") from exc
    return True


# ----------------------------------------------------------- decisão

def avaliar(raiz: Optional[Path] = None,
            agora: Optional[float] = None,
            listar: Listador = listar_processos) -> Resultado:
    try:
        principal = resolver_raiz_principal(raiz if raiz is not None else raiz_do_script())
        momento = time.time() if agora is None else agora
        sinais = sinais_nos_processos(listar(), frozenset({os.getpid(), os.getppid()}))
        recente = sinal_current_jsonl(principal, momento)
        if recente:
            sinais.append(recente)
        aberta = janela_aberta(principal)
    except DeteccaoFalhou as exc:
        return Resultado(JOGANDO, f"falha segura, tratando como Victor jogando: {exc}")
    except Exception as exc:  # qualquer surpresa também é falha segura
        return Resultado(JOGANDO, "falha segura, tratando como Victor jogando: "
                                  f"erro inesperado ({exc.__class__.__name__}: {exc})")

    if sinais:
        motivo = "Victor jogando: " + "; ".join(sinais)
        if aberta:
            motivo += " (a janela aberta não vale enquanto ele joga)"
        return Resultado(JOGANDO, motivo)
    if aberta:
        return Resultado(JANELA, f"janela de manutenção aberta ({MARCA_JANELA.as_posix()})")
    return Resultado(LIVRE, "livre: nenhum sinal de partida e nenhuma janela aberta")


def main(argv: Optional[list] = None, listar: Listador = listar_processos) -> int:
    parser = argparse.ArgumentParser(
        description="Diz se dá pra mexer no que é vivo: 0 livre, 3 Victor jogando, "
                    "4 janela aberta (3 tem precedência).")
    parser.add_argument("--raiz", type=Path, default=None,
                        help="checkout (ou worktree) a examinar; padrão: o deste script")
    args = parser.parse_args(argv)
    resultado = avaliar(raiz=args.raiz, listar=listar)
    try:
        # Console de verdade já recebe Unicode. Em pipe (Git Bash, ferramenta
        # do agente, hook) o padrão seria cp1252 e o "ç" chegaria quebrado.
        if sys.stdout.isatty():
            sys.stdout.reconfigure(errors="replace")
        else:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    motivo = " ".join(resultado.motivo.split())  # sempre uma linha só
    print(f"preflight {resultado.codigo}: {motivo}")
    return resultado.codigo


if __name__ == "__main__":
    sys.exit(main())
