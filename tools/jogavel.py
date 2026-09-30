#!/usr/bin/env python3
"""
Voltar ao jogável e atualizar o checkout principal sem depender de agente
(card B0.7, parte 1; protocolo de jogabilidade, seções 2, 5 e 7 do plano de
26/09). Runbook: docs/runbooks/voltar-ao-jogavel.md.

  status     só lê: HEAD, última tag jogavel-*, delta até origin/main, janela,
             preflight, pre.sh, runtime file e container.
  voltar     [--tag X] [--seco] [--agora] [--recriar]: volta o checkout para
             a última jogavel-* (ou X) e recria o container se a infra difere.
  atualizar  [--seco]: traz a origin/main com preflight 0; commit de infra só
             com janela aberta (preflight 4).
  janela     abrir|fechar|vigiar: fatia 2 do B0.7, ainda não implementado.

Todo git, docker e preflight passa pelo Executor, o único ponto que roda
processo: os testes o trocam por um docker falso e um repo em tmp_path. Com
--seco, o que muda algo (switch, merge, docker logs, recreate, cópia) só é
impresso; o que só lê roda (git diff, docker compose config, preflight). O
git fetch do `atualizar` roda mesmo no --seco: só mexe em origin/*.

Saída: 0 ok; 1 falha; 2 uso errado; 3 partida em curso ou preflight que não
libera; 5 recusado por regra (infra sem janela, confirmação errada, branch);
6 docker/pre.sh com '\\r' depois da troca (recreate abortado).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight  # noqa: E402

OK, FALHA, USO, PARTIDA, RECUSA, CRLF = 0, 1, 2, 3, 5, 6

CONTAINER = "cs2-spike"
COMPOSE = "docker-compose.yml"
PRE_SH = Path("docker/pre.sh")
# Estado de runtime do start_match, rastreado até o P1.6 (docker/runtime/).
RUNTIME = Path("docker/match_config.spike.json")
PLUGINS = "docker/plugins/"
CANDIDATO = Path("data/candidato.json")
PASTA_LOGS = Path("logs/jogavel")
PREFLIGHT = Path(__file__).resolve().parent / "preflight.py"

# Partida em curso (protocolo 7): evento de round há menos de 2 min. São
# todos os tipos que o plugin grava fora o snapshot (Cs2TrackerEventsPlugin.cs
# 452-703): sem o freeze_end, um round sem dano de 115 s somado a 15 s de
# freeze passaria dos 2 min contados do round_start.
PARTIDA_RECENTE_S = 120
EVENTOS_DE_ROUND = {"round_start", "freeze_end", "round_end", "round_stats",
                    "round_officially_ended", "player_death", "player_hurt",
                    "player_blind", "bomb_planted", "bomb_defused"}
# O plugin grava um "snapshot" 2x por segundo, também depois do fim da
# partida (Cs2TrackerEventsPlugin.cs:229): N snapshots depois do último
# evento de round são ~N/2 s sem round.
SNAPSHOTS_POR_S = 2
CAUDA_BYTES = 4 << 20
# "GC Connection established for server version 2000918, instance idx 1"
RE_BUILD = re.compile(r"GC Connection established for server version (\d+)")
ESPERA_BUILD_S, INTERVALO_BUILD_S = 600, 10
O_QUE_FECHAR = {"cs2.exe": "feche o CS2", "python wizard_tui": "feche a TUI",
                "python start_match": "feche o start_match (terminal da partida)"}


# ------------------------------------------------------------ executor

@dataclass
class Chamada:
    argv: list
    codigo: Optional[int]  # None: não terminou (timeout) ou não iniciou
    saida: str = ""
    erro: str = ""
    segundos: float = 0.0
    seco: bool = False

    @property
    def ok(self) -> bool:
        return self.codigo == 0


class Executor:
    """Único ponto que roda processo. `muda=True` marca o que altera algo:
    no --seco só é impresso. Cada chamada tem timeout e guarda o tempo gasto
    (lição de 27/09: um docker preso num ask venceu a janela duas vezes)."""

    def __init__(self, raiz: Path, seco: bool = False, rodar=subprocess.run,
                 relogio=time.monotonic, dormir=time.sleep, timeout: float = 120):
        self.raiz, self.seco, self.timeout = Path(raiz), seco, timeout
        self._rodar, self.relogio, self.dormir = rodar, relogio, dormir
        self.historico: list = []

    def __call__(self, *argv, muda: bool = False, timeout: Optional[float] = None) -> Chamada:
        argv = [str(a) for a in argv]
        if muda and self.seco:
            print("[seco] " + " ".join(argv))
            ch = Chamada(argv, 0, seco=True)
        else:
            limite = timeout or self.timeout
            inicio = self.relogio()
            try:
                p = self._rodar(argv, cwd=str(self.raiz), capture_output=True, timeout=limite)
                ch = Chamada(argv, p.returncode, _texto(p.stdout), _texto(p.stderr))
            except subprocess.TimeoutExpired:
                ch = Chamada(argv, None, erro=f"sem resposta em {limite:.0f} s")
            except OSError as exc:
                ch = Chamada(argv, None, erro=f"{exc.__class__.__name__}: {exc}")
            ch.segundos = self.relogio() - inicio
        self.historico.append(ch)
        return ch

    def git(self, *args, **kw) -> Chamada:
        return self("git", *args, **kw)

    def docker(self, *args, **kw) -> Chamada:
        return self("docker", *args, **kw)

    def para_preflight(self, argv, **_kw):
        """Adapta o executor ao `executar` do preflight.listar_processos."""
        ch = self(*argv)
        if ch.codigo is None:
            raise subprocess.SubprocessError(ch.erro)
        return subprocess.CompletedProcess(argv, ch.codigo, ch.saida.encode("utf-8"), b"")


def _texto(dados) -> str:
    if isinstance(dados, bytes):
        return dados.decode("utf-8", errors="replace")
    return dados or ""


# ------------------------------------------------------- git e estado

def ultima_tag_jogavel(ex: Executor) -> Optional[str]:
    ch = ex.git("for-each-ref", "--sort=-creatordate", "--format=%(refname:short)",
                "refs/tags/jogavel-*")
    tags = ch.saida.split() if ch.ok else []
    return tags[0] if tags else None


def rastreado(ex: Executor, ref: str, caminho: Path) -> bool:
    return ex.git("cat-file", "-e", f"{ref}:{caminho.as_posix()}").ok


def arquivos_mudados(ex: Executor, de: str, para: str) -> Optional[list]:
    ch = ex.git("diff", "--name-only", de, para)
    return [a for a in ch.saida.splitlines() if a] if ch.ok else None


def estado_janela(raiz: Path, agora: float) -> str:
    try:
        idade = preflight.idade_da_marca(raiz, agora)
    except preflight.DeteccaoFalhou as exc:
        return f"desconhecida ({exc})"
    if idade is None:
        return "fechada"
    minutos = max(0, int(idade // 60))
    return f"aberta há {minutos} min" if preflight.janela_vale(idade) else \
        f"vencida (marca de {minutos} min; só o papel servidor apaga)"


def consultar_preflight(ex: Executor) -> tuple:
    ch = ex(sys.executable, PREFLIGHT, "--raiz", ex.raiz)
    codigo = ch.codigo if ch.codigo in (preflight.LIVRE, preflight.JANELA) else preflight.JOGANDO
    return codigo, (ch.saida.strip() or ch.erro.strip() or f"preflight saiu com {ch.codigo}")


def contar_cr(raiz: Path) -> int:
    try:
        return (raiz / PRE_SH).read_bytes().count(b"\r")
    except FileNotFoundError:
        return 0


def conserto_cr(raiz: Path) -> str:
    alvo = (raiz / PRE_SH).as_posix()
    return (f'"{sys.executable}" -c "import pathlib; p = pathlib.Path(\'{alvo}\'); '
            f"p.write_bytes(p.read_bytes().replace(b'\\r\\n', b'\\n'))\"")


# -------------------------------------------------------------- infra

def fontes_de_bind(ex: Executor) -> Optional[list]:
    """Fontes de bind dentro do checkout, tiradas de `docker compose config`
    (protocolo 2). A saída traz o .env interpolado: nunca é impressa."""
    ch = ex.docker("compose", "config", "--format", "json")
    if not ch.ok:
        return None
    try:
        servicos = json.loads(ch.saida).get("services") or {}
    except (ValueError, AttributeError):
        return None
    fontes = set()
    for servico in servicos.values():
        for vol in servico.get("volumes") or []:
            if not isinstance(vol, dict) or vol.get("type") != "bind" or not vol.get("source"):
                continue
            fonte = Path(vol["source"])
            try:
                rel = (fonte if fonte.is_absolute() else ex.raiz / fonte).resolve()
                fontes.add(rel.relative_to(ex.raiz.resolve()).as_posix())
            except ValueError:  # fora do checkout: não vem do git
                continue
    return sorted(fontes)


def infra_no_delta(ex: Executor, mudados: list) -> list:
    """Arquivos de infra entre os mudados: o compose, docker/plugins/ e toda
    fonte de bind. Sem a lista de binds, todo arquivo mudado conta (falha
    segura: recria no voltar, recusa no atualizar sem janela)."""
    if not mudados:
        return []
    fontes = fontes_de_bind(ex)
    if fontes is None:
        print("aviso: `docker compose config` falhou; sem a lista de binds, todo "
              "arquivo mudado conta como infra")
        return list(mudados)
    return [a for a in mudados if a == COMPOSE or a.startswith(PLUGINS)
            or any(a == f or a.startswith(f.rstrip("/") + "/") for f in fontes)]


# ------------------------------------------------- partida em curso

def evento_de_round_recente(raiz: Path, agora: float) -> Optional[str]:
    arquivo = raiz / preflight.CURRENT_JSONL
    try:
        st = arquivo.stat()
    except FileNotFoundError:
        return None
    idade = agora - st.st_mtime
    if idade >= PARTIDA_RECENTE_S:
        return None
    with arquivo.open("rb") as f:  # só leitura, e só a cauda
        f.seek(max(0, st.st_size - CAUDA_BYTES))
        linhas = f.read().splitlines()
    snapshots = 0
    for linha in reversed(linhas):
        try:
            tipo = json.loads(linha).get("type")
        except (ValueError, AttributeError):
            continue
        if tipo == "snapshot":
            snapshots += 1
        elif tipo in EVENTOS_DE_ROUND:
            desde = max(0.0, idade) + snapshots / SNAPSHOTS_POR_S
            return f"current.jsonl com {tipo} há ~{int(desde)} s" if desde < PARTIDA_RECENTE_S else None
        if snapshots / SNAPSHOTS_POR_S >= PARTIDA_RECENTE_S:
            return None
    return None


def sinais_de_partida(ex: Executor, agora: float) -> tuple:
    """(bloqueios, avisos). Bloqueia só partida em curso: evento de round
    recente ou watcher ingerindo. cs2.exe, TUI e start_match viram aviso com
    o que fechar. Sem conseguir listar processos, ou com python sem linha de
    comando (só o tasklist respondeu), bloqueia (falha segura, G0).

    O preflight só dá python sem linha como falha quando não há outro sinal
    (preflight.py, sinais_nos_processos): para ele, o cs2.exe já basta para
    dar 3. Aqui o cs2.exe é só aviso, então o python cego bloqueia sempre:
    numa partida viva o cs2.exe está sempre lá, e o watcher seria invisível."""
    bloqueios, avisos = [], []
    evento = evento_de_round_recente(ex.raiz, agora)
    if evento:
        bloqueios.append(evento)
    try:
        processos = preflight.listar_processos(ex.para_preflight)
    except preflight.DeteccaoFalhou as exc:
        return bloqueios + [f"sem certeza sobre o watcher: {exc}"], avisos
    proprios = frozenset({os.getpid(), os.getppid()})
    cegos = [p.pid for p in processos if p.linha is None and p.pid not in proprios
             and preflight._eh_python(p.nome)]
    if cegos:
        bloqueios.append("sem certeza sobre o watcher: python sem linha de comando "
                         f"legível (PID {', '.join(map(str, cegos))})")
    # Os cegos já bloquearam: passados como próprios, não levantam de novo e
    # deixam os avisos (cs2.exe, TUI) saírem.
    sinais = preflight.sinais_nos_processos(processos, proprios | frozenset(cegos))
    for sinal in sinais:
        if sinal.startswith("python watcher"):
            bloqueios.append(f"watcher ingerindo ({sinal})")
        else:
            chave = next((k for k in O_QUE_FECHAR if sinal.startswith(k)), None)
            avisos.append(f"{O_QUE_FECHAR.get(chave, 'feche')}: {sinal}")
    return bloqueios, avisos


# ------------------------------------------- troca de commit e docker

def trocar_de_commit(ex: Executor, pasta: Path, alvo: str, *comandos) -> bool:
    """Roda os comandos git de troca protegendo o runtime file: copia para
    `pasta`, tira do caminho (checkout -- se rastreado; apaga se não
    rastreado e o alvo o rastreia), troca, e restaura a cópia se o alvo
    ainda o rastreia (protocolo 7, passo 2). Sem git stash.

    Se um comando falha depois de outro já ter mudado o checkout (o merge
    --ff-only depois do switch main do `atualizar`), volta ao HEAD de antes;
    se nem isso der, diz onde ficou e o comando para voltar."""
    arquivo, copia = ex.raiz / RUNTIME, pasta / RUNTIME.name
    no_alvo = rastreado(ex, alvo, RUNTIME)
    tinha = arquivo.is_file()
    sha_antes = ex.git("rev-parse", "HEAD").saida.strip()
    ramo_antes = ex.git("branch", "--show-current").saida.strip()
    volta = ("switch", ramo_antes) if ramo_antes else ("switch", "--detach", sha_antes)
    if tinha:
        print(f"{RUNTIME.as_posix()}: cópia em {copia}")
        if not ex.seco:
            pasta.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arquivo, copia)
        if rastreado(ex, "HEAD", RUNTIME):
            ex.git("checkout", "--", RUNTIME.as_posix(), muda=True)
        elif no_alvo and not ex.seco:
            arquivo.unlink()
    for i, comando in enumerate(comandos):
        ch = ex.git(*comando, muda=True)
        if not ch.ok:
            print(f"falhou: git {' '.join(comando)}\n{ch.erro.strip()}")
            if i > 0:
                if ex.git(*volta, muda=True).ok:
                    print(f"voltei ao HEAD de antes ({ramo_antes or 'destacado em ' + sha_antes[:9]})")
                else:
                    agora = ex.git("branch", "--show-current").saida.strip() or "HEAD destacado"
                    print(f"ATENÇÃO: o checkout ficou em {agora}, não no HEAD de antes. "
                          f"Para voltar: git {' '.join(volta)}")
            if tinha and not ex.seco:
                shutil.copy2(copia, arquivo)
            return False
    if tinha and no_alvo:
        print(f"{RUNTIME.as_posix()}: restaurado da cópia (rastreado em {alvo})")
        if not ex.seco:
            shutil.copy2(copia, arquivo)
    elif tinha:
        print(f"{RUNTIME.as_posix()}: não é rastreado em {alvo}; a cópia fica em {copia}")
    return True


def salvar_logs(ex: Executor, pasta: Path) -> Optional[str]:
    """Salva `docker logs -t` do container (o recreate os descarta) e
    devolve a build do CS2 que eles mostram."""
    ch = ex.docker("logs", "-t", CONTAINER, muda=True)
    if ch.seco:
        return None
    if not ch.ok:
        print(f"aviso: sem docker logs de {CONTAINER} ({ch.erro.strip() or ch.codigo})")
        return None
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "docker-logs.txt").write_text(ch.saida + ch.erro, encoding="utf-8")
    print(f"docker logs salvos em {pasta / 'docker-logs.txt'} ({ch.segundos:.1f} s)")
    builds = RE_BUILD.findall(ch.saida + ch.erro)
    return builds[-1] if builds else None


def esperar_build(ex: Executor) -> Optional[str]:
    fim = ex.relogio() + ESPERA_BUILD_S
    while True:
        ch = ex.docker("logs", CONTAINER)
        builds = RE_BUILD.findall(ch.saida + ch.erro) if ch.ok else []
        if builds:
            return builds[-1]
        if ex.relogio() >= fim:
            return None
        ex.dormir(INTERVALO_BUILD_S)


def checkout_principal() -> Path:
    """O checkout principal do repo deste script (numa worktree, o dela)."""
    return preflight.resolver_raiz_principal(preflight.raiz_do_script())


def eh_checkout_principal(raiz: Path) -> bool:
    try:
        return Path(raiz).resolve() == Path(checkout_principal()).resolve()
    except (preflight.DeteccaoFalhou, OSError):
        return False


def recriar(ex: Executor, build_antes: Optional[str], sem_build: str = "não registrada") -> int:
    if not eh_checkout_principal(ex.raiz):
        # Numa worktree ou num clone avulso (--raiz) o compose criaria
        # projeto e volume novos, vazios (AGENTS.md, zonas proibidas).
        print(f"recreate recusado: {ex.raiz} não é o checkout principal")
        return RECUSA
    print(f"build do CS2 antes: {build_antes or sem_build}")
    ch = ex.docker("compose", "up", "-d", "--force-recreate", muda=True, timeout=900)
    if not ch.ok:
        print(f"falhou: docker compose up -d --force-recreate ({ch.segundos:.0f} s)\n{ch.erro.strip()}")
        return FALHA
    if ex.seco:
        return OK
    depois = esperar_build(ex)
    print(f"build do CS2 depois: {depois or f'sem a linha do GC em {ESPERA_BUILD_S // 60} min'}")
    if build_antes and depois and depois != build_antes:
        print(f"ATENÇÃO: a build do CS2 mudou ({build_antes} -> {depois}). São duas "
              "variáveis, e o cliente do Victor precisa da mesma build.")
    return OK


# ---------------------------------------------------------- comandos

def _pasta(ex: Executor, nome: str) -> Path:
    return ex.raiz / PASTA_LOGS / f"{datetime.now():%Y-%m-%d_%H%M%S}-{nome}"


def cmd_status(args, ex: Executor, agora: float, **_kw) -> int:
    head = ex.git("rev-parse", "--short", "HEAD").saida.strip()
    ramo = ex.git("branch", "--show-current").saida.strip() or "destacado"
    tags = ex.git("tag", "--points-at", "HEAD").saida.split()
    print(f"checkout: {ex.raiz}\nHEAD: {head} ({ramo}) {' '.join(tags)}".rstrip())
    tag = ultima_tag_jogavel(ex)
    if tag:
        frente = ex.git("rev-list", "--count", f"{tag}..HEAD").saida.strip()
        print(f"última jogável: {tag}; HEAD está {frente} commit(s) à frente dela")
    mudados = arquivos_mudados(ex, "HEAD", "origin/main")
    if mudados is not None:
        infra = infra_no_delta(ex, mudados)
        print(f"origin/main (sem fetch): {len(mudados)} arquivo(s) diferente(s); infra: "
              f"{', '.join(infra) or 'nenhuma'}")
    print(f"janela: {estado_janela(ex.raiz, agora)}")
    print(consultar_preflight(ex)[1])
    cr = contar_cr(ex.raiz)
    print(f"pre.sh: {cr} '\\r' (conserto: {conserto_cr(ex.raiz)})" if cr else "pre.sh: LF")
    modificado = ex.git("status", "--porcelain", "--", RUNTIME.as_posix()).saida.strip()
    print(f"runtime file: {modificado or 'sem mudança local'}")
    candidato = ex.raiz / CANDIDATO
    if candidato.is_file():
        print(f"candidato: {candidato.read_text(encoding='utf-8').strip()}")
    ch = ex.docker("ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Status}}")
    print(f"container {CONTAINER}: {ch.saida.strip() or 'não existe'}" if ch.ok else
          f"container {CONTAINER}: docker indisponível ({ch.erro.strip() or ch.codigo})")
    return OK


def cmd_voltar(args, ex: Executor, agora: float, entrada: Callable = input) -> int:
    alvo = args.tag or ultima_tag_jogavel(ex)
    if not alvo or not ex.git("rev-parse", "--verify", "--quiet", f"{alvo}^{{commit}}").ok:
        print(f"voltar: tag {alvo or 'jogavel-*'} não encontrada")
        return FALHA
    bloqueios, avisos = sinais_de_partida(ex, agora)
    for aviso in avisos:
        print(f"aviso: {aviso}")
    if bloqueios:
        print("partida em curso: " + "; ".join(bloqueios))
        if not args.agora:
            print("voltar recusado. Espere a partida acabar, ou rode com --agora.")
            return PARTIDA
        resposta = _perguntar(entrada, "Voltar AGORA, no meio da partida? Digite VOLTAR: ")
        if resposta != "VOLTAR":
            print("confirmação diferente de VOLTAR: nada foi feito")
            return RECUSA
    mudados = arquivos_mudados(ex, "HEAD", alvo) or []
    infra = infra_no_delta(ex, mudados)
    pasta = _pasta(ex, "voltar")
    if bloqueios:
        # --agora: docker logs com partida em curso é proibido (AGENTS.md,
        # protocolo 11). A build "depois" sai do container novo.
        print("docker logs não lidos: partida em curso")
        build, sem_build = None, "não lida (partida em curso)"
    else:
        build, sem_build = salvar_logs(ex, pasta), "não registrada"
    if not trocar_de_commit(ex, pasta, alvo, ("switch", "--detach", alvo)):
        return FALHA
    print(f"checkout em {alvo}. Pasta do plugin de captura: a restauração pelo "
          "manifesto é do B0.7b; até lá, siga docs/runbooks/voltar-ao-jogavel.md")
    cr = contar_cr(ex.raiz)
    if cr:
        # O HEAD já está no alvo: o voltar de novo não veria diferença de infra.
        extra = " --recriar" if infra or args.recriar else ""
        print(f"ABORTADO antes do recreate: docker/pre.sh tem {cr} '\\r'. Conserte com\n"
              f"  {conserto_cr(ex.raiz)}\ne rode de novo: tools/jogavel.py voltar --tag {alvo}{extra}")
        return CRLF
    if not infra and not args.recriar:
        print("infra igual à do alvo: sem recreate")
        return OK
    print("infra difere: " + (", ".join(infra) or "--recriar"))
    return recriar(ex, build, sem_build)


def cmd_atualizar(args, ex: Executor, **_kw) -> int:
    codigo, motivo = consultar_preflight(ex)
    print(motivo)
    if codigo not in (preflight.LIVRE, preflight.JANELA):
        print("atualizar recusado: o Victor pode estar jogando (precisa de preflight 0)")
        return PARTIDA
    ramo = ex.git("branch", "--show-current").saida.strip()
    if ramo not in ("main", ""):
        print(f"atualizar recusado: o checkout está na branch {ramo}, não na main")
        return RECUSA
    alvo = "origin/main"
    if not ex.git("fetch", "origin", "--tags", timeout=300).ok:
        print(f"aviso: git fetch falhou; comparando com a {alvo} que já estava aqui")
    mudados = arquivos_mudados(ex, "HEAD", alvo)
    if mudados is None:
        print(f"atualizar: {alvo} não encontrada")
        return FALHA
    infra = infra_no_delta(ex, mudados)
    if infra and codigo != preflight.JANELA:
        print("atualizar recusado: o delta toca infra e não há janela aberta: "
              f"{', '.join(infra)}. Quem traz infra é o papel servidor, em janela.")
        return RECUSA
    comandos = ([("switch", "main")] if not ramo else []) + [("merge", "--ff-only", alvo)]
    if not trocar_de_commit(ex, _pasta(ex, "atualizar"), alvo, *comandos):
        return FALHA
    cr = contar_cr(ex.raiz)
    if cr:
        print(f"ATENÇÃO: docker/pre.sh tem {cr} '\\r'. Conserte antes de subir o servidor:\n"
              f"  {conserto_cr(ex.raiz)}")
        return CRLF
    if infra:
        print("infra mudou: na janela, recrie com `docker compose up -d --force-recreate` "
              f"do checkout principal ({', '.join(infra)})")
    print(f"checkout atualizado ({len(mudados)} arquivo(s)). Reabra a TUI e o uvicorn.")
    return OK


def cmd_janela(args, ex: Executor, **_kw) -> int:
    print(f"janela {args.acao}: ainda não implementado (fatia 2 do card B0.7). "
          "Siga o runbook do passo.")
    return FALHA


def _perguntar(entrada: Callable, texto: str) -> str:
    try:
        return entrada(texto).strip()
    except EOFError:
        return ""


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Voltar ao jogável e atualizar o checkout principal (card B0.7).",
        epilog="Saída: 0 ok, 1 falha, 2 uso, 3 partida em curso/preflight, 5 recusado "
               "por regra, 6 pre.sh com '\\r'. Detalhes no início de tools/jogavel.py.")
    parser.add_argument("--raiz", type=Path, default=None,
                        help="checkout a operar; padrão: o checkout principal")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("status", help="mostra o estado, sem mudar nada")
    voltar = sub.add_parser("voltar", help="volta à última tag jogavel-* (ou --tag)")
    voltar.add_argument("--tag", default=None, help="tag ou commit de destino")
    voltar.add_argument("--seco", action="store_true", help="só mostra o que faria")
    voltar.add_argument("--agora", action="store_true",
                        help="volta mesmo com partida em curso, com confirmação digitada")
    voltar.add_argument("--recriar", action="store_true",
                        help="recria o container mesmo com a infra igual (depois do conserto do pre.sh)")
    atualizar = sub.add_parser("atualizar", help="traz a origin/main para o checkout")
    atualizar.add_argument("--seco", action="store_true", help="só mostra o que faria")
    janela = sub.add_parser("janela", help="abrir, fechar ou vigiar a janela (fatia 2)")
    janela.add_argument("acao", choices=("abrir", "fechar", "vigiar"))
    return parser


COMANDOS = {"status": cmd_status, "voltar": cmd_voltar, "atualizar": cmd_atualizar,
            "janela": cmd_janela}


def main(argv: Optional[list] = None, fabrica: Callable = Executor,
         entrada: Callable = input, agora: Optional[float] = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):  # em pipe o padrão seria cp1252
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    args = montar_parser().parse_args(argv)
    try:
        raiz = args.raiz or checkout_principal()
    except preflight.DeteccaoFalhou as exc:
        print(f"jogavel: {exc}", file=sys.stderr)
        return USO
    ex = fabrica(Path(raiz).absolute(), seco=getattr(args, "seco", False))
    return COMANDOS[args.comando](args, ex, agora=time.time() if agora is None else agora,
                                  entrada=entrada)


if __name__ == "__main__":
    sys.exit(main())
