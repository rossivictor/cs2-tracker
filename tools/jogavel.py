#!/usr/bin/env python3
"""
Voltar ao jogável e atualizar o checkout principal sem depender de agente
(cards B0.7 e B0.7b; protocolo de jogabilidade, seções 2, 3, 5 a 9 do plano
de 26/09). Runbook: docs/runbooks/voltar-ao-jogavel.md.

  status     só lê: HEAD, última tag jogavel-*, delta até origin/main, janela,
             preflight, pre.sh, runtime file e container.
  voltar     [--tag X] [--seco] [--agora] [--recriar] [--plugin SHA]: volta o
             checkout para a última jogavel-* (ou X), restaura a pasta do
             plugin de captura pelo manifesto sha256 (container parado) e
             recria o container se a infra ou a pasta do plugin mudou.
  atualizar  [--seco]: traz a origin/main com preflight 0; commit de infra só
             com janela aberta (preflight 4).
  janela     abrir --por "frase" [--teto N] | fechar [--feito ITEM...] |
             vigiar [--intervalo S], todos com [--seco] e só no checkout
             principal (fatia 2; protocolo, seção 8).

Todo git, docker e preflight passa pelo Executor, o único ponto que roda
processo: os testes o trocam por um docker falso e um repo em tmp_path. Com
--seco, o que muda algo (switch, merge, docker logs, recreate, cópia) só é
impresso; o que só lê roda (git diff, docker compose config, preflight). O
git fetch do `atualizar` roda mesmo no --seco: só mexe em origin/*.

Saída: 0 ok; 1 falha; 2 uso errado; 3 partida em curso, preflight que não
libera ou vigília abortada por processo do Victor; 5 recusado por regra
(infra sem janela, confirmação errada, branch, janela já aberta, checklist
pendente); 6 docker/pre.sh com '\\r' depois da troca (recreate abortado);
7 janela vencida (teto ou 45 min pelo mtime da marca).
"""
from __future__ import annotations

import argparse
import hashlib
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

OK, FALHA, USO, PARTIDA, RECUSA, CRLF, VENCIDA = 0, 1, 2, 3, 5, 6, 7

CONTAINER = "cs2-spike"
COMPOSE = "docker-compose.yml"
PRE_SH = Path("docker/pre.sh")
# Estado de runtime do start_match, rastreado até o P1.6 (docker/runtime/).
RUNTIME = Path("docker/match_config.spike.json")
PLUGINS = "docker/plugins/"
CANDIDATO = Path("data/candidato.json")
PASTA_LOGS = Path("logs/jogavel")
PREFLIGHT = Path(__file__).resolve().parent / "preflight.py"
# Pasta do plugin de captura: ignorada pelo git, não volta com o switch.
PLUGIN_CAPTURA = Path("docker/plugins/Cs2TrackerEvents")
DLL_CAPTURA = "Cs2TrackerEvents.dll"
# Cópias da pasta, uma por sha256 da DLL, com o manifesto ao lado (card B0.3;
# versoes-conhecidas.md, "Manifesto do plugin de captura"). A velha nunca se
# apaga: um build novo ganha uma pasta nova.
COPIAS_PLUGIN = Path("C:/Users/Victor/cs2-tracker-backups/plugins/Cs2TrackerEvents")
# MANIFEST.txt é o do B0.3; MANIFESTO.sha256, o dos builds do upstream (B1.4b, B1.9).
NOMES_MANIFESTO = ("MANIFEST.txt", "MANIFESTO.sha256")
RE_SHA = re.compile(r"^[0-9a-f]{64}$")
# Linha que o `marcar` grava na mensagem da tag anotada.
RE_PLUGIN_NA_TAG = re.compile(r"^plugin Cs2TrackerEvents: ([0-9a-f]{64})\s*$", re.M)
PARADO = ("Exited", "Created", "não existe")

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

    def para_preflight(self, argv, **kw):
        """Adapta o executor ao `executar` do preflight.listar_processos,
        com o timeout dele (30 s), não o de 120 s do executor."""
        ch = self(*argv, timeout=kw.get("timeout"))
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
    evento = evento_de_round_recente(ex.raiz, agora)
    bloqueios, avisos = sinais_de_processo(ex)
    return ([evento] if evento else []) + bloqueios, avisos


def sinais_de_processo(ex: Executor) -> tuple:
    """(bloqueios, avisos) só da lista de processos, sem o current.jsonl:
    é o que o `janela vigiar` olha, porque na janela quem escreve no
    current.jsonl é o servidor (boot, changelevel, smoke só de bots)."""
    bloqueios, avisos = [], []
    try:
        processos = preflight.listar_processos(ex.para_preflight)
    except preflight.DeteccaoFalhou as exc:
        return [f"sem certeza sobre o watcher: {exc}"], avisos
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


def parar_container(ex: Executor) -> int:
    """`docker stop` e confere que parou. Sem conseguir ler o estado não
    há certeza de que o servidor está parado: falha (DLL não se troca com
    o servidor vivo)."""
    estado = estado_container(ex)
    if estado.startswith("docker indisponível"):
        print(f"container {CONTAINER}: {estado}; sem certeza de que está parado")
        return FALHA
    if estado.startswith(PARADO):
        print(f"container {CONTAINER} já parado: {estado}")
        return OK
    ch = ex.docker("stop", CONTAINER, muda=True, timeout=180)
    if ch.seco:
        return OK
    depois = estado_container(ex)
    if not ch.ok or not depois.startswith(PARADO):
        print(f"falhou: docker stop {CONTAINER} ({ch.erro.strip() or ch.codigo}); estado: {depois}")
        return FALHA
    print(f"container {CONTAINER} parado em {ch.segundos:.0f} s: {depois}")
    return OK


# ------------------------------------------------ manifesto do plugin

def sha256_de(arquivo: Path) -> str:
    h = hashlib.sha256()
    with Path(arquivo).open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_manifesto(arquivo: Path) -> dict:
    """{nome: sha256}. Entende o MANIFEST.txt do B0.3 (sha256, bytes, mtime e
    nome) e a saída do sha256sum (sha256 e nome, com '*' no modo binário):
    o sha256 é a 1ª coluna e o nome, a última. Linha fora disso é erro, e
    manifesto que não se lê inteiro não restaura nada."""
    itens = {}
    # Os comentários podem vir em cp1252; as linhas de dados são ASCII.
    texto = Path(arquivo).read_text(encoding="utf-8", errors="replace")
    for n, linha in enumerate(texto.splitlines(), 1):
        partes = linha.split()
        if not partes or partes[0].startswith("#"):
            continue
        nome = partes[-1].lstrip("*")
        if len(partes) < 2 or not RE_SHA.match(partes[0].lower()) or nome in ("", ".", "..") \
                or "/" in nome or "\\" in nome:
            raise ValueError(f"{Path(arquivo).name}:{n}: linha fora do formato 'sha256 ... nome'")
        itens[nome] = partes[0].lower()
    if not itens:
        raise ValueError(f"{Path(arquivo).name}: manifesto vazio")
    return itens


def diferencas(pasta: Path, esperado: dict, ignorar: tuple = ()) -> list:
    """O que a pasta tem de diferente do manifesto: arquivo que falta, sha256
    diferente, ou arquivo (ou subpasta) a mais."""
    atuais = {a.name: a for a in pasta.iterdir() if a.name not in ignorar} if pasta.is_dir() else {}
    difs = [f"falta {n}" for n in esperado if n not in atuais]
    difs += [f"sha256 diferente: {n}" for n, sha in esperado.items()
             if n in atuais and (not atuais[n].is_file() or sha256_de(atuais[n]) != sha)]
    difs += [f"a mais: {n}" for n in sorted(set(atuais) - set(esperado))]
    return difs


def manifesto_da_copia(copia: Path) -> Optional[Path]:
    return next((copia / n for n in NOMES_MANIFESTO if (copia / n).is_file()), None)


def plugin_do_alvo(ex: Executor, alvo: str) -> Optional[str]:
    """sha256 da DLL que o `marcar` gravou na mensagem da tag anotada."""
    ch = ex.git("tag", "-l", "--format=%(contents)", alvo)
    achado = RE_PLUGIN_NA_TAG.search(ch.saida) if ch.ok else None
    return achado.group(1) if achado else None


def restaurar_plugin(ex: Executor, sha_dll: str, pasta: Path) -> tuple:
    """Passo 4 do voltar (protocolo 7): a pasta do plugin de captura volta a
    ser a cópia do manifesto, inteira (DLL, .deps.json, .pdb), com o
    container parado, e é conferida depois. O que havia antes vai para
    `pasta`/plugin-antes (nada se apaga). Devolve (código, mudou)."""
    copia = COPIAS_PLUGIN / sha_dll
    manifesto = manifesto_da_copia(copia)
    if manifesto is None:
        print(f"pasta do plugin: sem manifesto ({' nem '.join(NOMES_MANIFESTO)}) em {copia}")
        return FALHA, False
    try:
        esperado = ler_manifesto(manifesto)
    except (OSError, ValueError) as exc:
        print(f"pasta do plugin: manifesto ilegível: {exc}")
        return FALHA, False
    if esperado.get(DLL_CAPTURA) != sha_dll:
        print(f"pasta do plugin: o manifesto de {copia} não dá {DLL_CAPTURA} com sha256 {sha_dll[:12]}")
        return FALHA, False
    destino = ex.raiz / PLUGIN_CAPTURA
    difs = diferencas(destino, esperado)
    if not difs:
        print(f"pasta do plugin confere com o manifesto {sha_dll[:12]}: nada a restaurar")
        return OK, False
    print(f"pasta do plugin difere do manifesto {sha_dll[:12]}: {'; '.join(difs)}")
    ruins = diferencas(copia, esperado, ignorar=NOMES_MANIFESTO)
    if ruins:
        print(f"a cópia {copia} não confere com o próprio manifesto ({'; '.join(ruins)}): nada foi trocado")
        return FALHA, False
    if not eh_checkout_principal(ex.raiz):
        print(f"pasta do plugin: {ex.raiz} não é o checkout principal, nada foi trocado")
        return RECUSA, False
    codigo = parar_container(ex)  # DLL não se troca com o servidor vivo
    if codigo != OK:
        print("pasta do plugin não restaurada: o container não está comprovadamente parado")
        return codigo, False
    if ex.seco:
        print(f"[seco] restauraria {destino} de {copia} ({len(esperado)} arquivos)")
        return OK, True
    antes = pasta / "plugin-antes"
    antes.mkdir(parents=True, exist_ok=True)
    destino.mkdir(parents=True, exist_ok=True)
    for item in list(destino.iterdir()):
        if item.name in esperado and item.is_file():
            shutil.copy2(item, antes / item.name)  # evidência do que havia
        else:
            shutil.move(str(item), str(antes / item.name))
    for nome in esperado:
        shutil.copy2(copia / nome, destino / nome)  # por cima: o bind da pasta segue valendo
    sobra = diferencas(destino, esperado)
    if sobra:
        print(f"ATENÇÃO: depois da cópia a pasta ainda difere do manifesto: {'; '.join(sobra)}. "
              f"O container ficou parado; a pasta de antes está em {antes}")
        return FALHA, True
    print(f"pasta do plugin restaurada do manifesto {sha_dll[:12]} e conferida "
          f"({len(esperado)} arquivos); a de antes ficou em {antes}")
    return OK, True


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
    print(f"container {CONTAINER}: {estado_container(ex)}")
    return OK


def estado_container(ex: Executor) -> str:
    """Status do `docker ps` ("Up 2 hours", "Exited (255) ..."), só leitura."""
    ch = ex.docker("ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Status}}")
    if not ch.ok:
        return f"docker indisponível ({ch.erro.strip() or ch.codigo})"
    return ch.saida.strip() or "não existe"


def cmd_voltar(args, ex: Executor, agora: float, entrada: Callable = input, **_kw) -> int:
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
    print(f"checkout em {alvo}")
    cr = contar_cr(ex.raiz)
    if cr:
        # Antes de parar o container pelo plugin: abortado aqui, o jogo segue de
        # pé. O HEAD já está no alvo: o voltar de novo não veria diferença de infra.
        extra = " --recriar" if infra or args.recriar else ""
        print(f"ABORTADO antes do recreate: docker/pre.sh tem {cr} '\\r'. Conserte com\n"
              f"  {conserto_cr(ex.raiz)}\ne rode de novo: tools/jogavel.py voltar --tag {alvo}{extra}")
        return CRLF
    sha_plugin = args.plugin or plugin_do_alvo(ex, alvo)
    codigo_plugin, plugin_mudou = OK, False
    if sha_plugin:
        codigo_plugin, plugin_mudou = restaurar_plugin(ex, sha_plugin, pasta)
        if codigo_plugin != OK and plugin_mudou:
            return codigo_plugin  # pasta pela metade: o container fica parado
    else:
        print(f"pasta do plugin: {alvo} não registra o manifesto (tag anterior ao B0.7b ou commit "
              "sem tag); confira à mão pelo manifesto em docs/runbooks/versoes-conhecidas.md ou "
              "rode com --plugin <sha256 da DLL>")
    if plugin_mudou:
        infra = infra + [PLUGIN_CAPTURA.as_posix() + "/"]
    if not infra and not args.recriar:
        print("infra igual à do alvo: sem recreate")
        return codigo_plugin
    print("infra difere: " + (", ".join(infra) or "--recriar"))
    codigo = recriar(ex, build, sem_build)
    return codigo if codigo != OK else codigo_plugin


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


# ------------------------------------------------------------ janela

MARCA = preflight.MARCA_JANELA
TETO_MAX_MIN = preflight.DURACAO_MAX_JANELA_S // 60
INTERVALO_VIGIA_S = 30  # protocolo 8: vigiar a cada ≤30 s
AVISO_FIM_S = 5 * 60    # avisa quando faltam 5 min para o teto
PARADO_MAX_S = 5 * 60   # container parado no máximo ~5 min por passo
# Checklist de fechamento (G6) que pede RCON ou docker exec: à mão até o
# B0.7b, e o `fechar` só passa com cada um confirmado por --feito.
MANUAIS = {
    "matchzy": 'MatchZy sem partida carregada: get5_status com "gamestate":"none" '
               "(css_endmatch ou restart), pela RCON",
    "cvars": 'cvars nos valores do "antes" da janela, pela RCON: mp_ignore_round_win_conditions 0, '
             "sv_hibernate_when_empty, bot_quota e bot_join_after_player "
             "(docs/runbooks/smoke-partida-de-bots.md)",
    "sha256": "sha256 dos arquivos montados dentro do container = checkout (docker exec "
              "sha256sum; o `coletar` do B0.7b automatiza)",
}


def _hora(t: float, formato: str = "%H:%M:%S") -> str:
    return datetime.fromtimestamp(t).strftime(formato)


def ler_marca(raiz: Path) -> dict:
    """O que o `abrir` gravou na marca. Marca feita à mão vem vazia; o
    preflight só lê o mtime dela."""
    try:
        dados = json.loads((raiz / MARCA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def registrar(ex: Executor, dados: dict, linha: str, t: float) -> None:
    """Acrescenta uma linha ao registro da janela (logs/janelas/<data da abertura>.md)."""
    rel = dados.get("registro") or f"logs/janelas/{_hora(t, '%Y-%m-%d')}.md"
    if ex.seco:
        print(f"[seco] {rel} += {linha.strip()}")
        return
    arquivo = ex.raiz / rel
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8") as f:
        f.write(linha + "\n")


def _avisar(ex: Executor, dados: dict, t: float, texto: str) -> None:
    print(f"{_hora(t)} {texto}")
    registrar(ex, dados, f"- {_hora(t)} vigiar: {texto}", t)


def cmd_janela(args, ex: Executor, entrada: Callable = input,
               relogio: Callable = time.time, **_kw) -> int:
    if not eh_checkout_principal(ex.raiz):
        print(f"janela recusada: {ex.raiz} não é o checkout principal, onde mora a marca")
        return RECUSA
    acao = {"abrir": janela_abrir, "fechar": janela_fechar, "vigiar": janela_vigiar}[args.acao]
    return acao(args, ex, relogio, entrada)


def janela_abrir(args, ex: Executor, relogio: Callable, _entrada) -> int:
    marca = ex.raiz / MARCA
    if marca.exists():
        # Nada de renovar: a idade conta do mtime, e renovar é fechar e abrir
        # de novo com novo OK do Victor (janela de 27/09, 08:23).
        print(f"abrir recusado: janela {estado_janela(ex.raiz, relogio())}. Feche com `janela fechar`")
        return RECUSA
    por = (args.por or "").strip()
    if not por:
        print('abrir recusado: passe --por "<frase literal do Victor>" (o "pode mexer no servidor", '
              'o "terminei" da trilha de bots ou o OK dele repassado pelo PM)')
        return RECUSA
    if not 0 < args.teto <= TETO_MAX_MIN:
        print(f"abrir recusado: --teto vai de 1 a {TETO_MAX_MIN} min")
        return USO
    codigo, motivo = consultar_preflight(ex)
    print(motivo)
    if codigo != preflight.LIVRE:
        print("abrir recusado: precisa de preflight 0 (janela nunca abre com o Victor jogando)")
        return PARTIDA if codigo == preflight.JOGANDO else RECUSA
    t = relogio()
    head = ex.git("rev-parse", "HEAD").saida.strip()
    ramo = ex.git("branch", "--show-current").saida.strip() or "destacado"
    container = estado_container(ex)
    dados = {"aberta_em": _hora(t, "%Y-%m-%dT%H:%M:%S"), "por": por, "teto_min": args.teto,
             "head": head, "container": container,
             "registro": f"logs/janelas/{_hora(t, '%Y-%m-%d')}.md"}
    if ex.seco:
        print(f"[seco] criaria {MARCA.as_posix()}: {json.dumps(dados, ensure_ascii=False)}")
    else:
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        os.utime(marca, (t, t))  # a idade conta daqui; ninguém mais mexe no mtime
    fim = t + args.teto * 60
    for linha in (f"\n# Janela {_hora(t, '%Y-%m-%d %H:%M')} (jogavel.py janela abrir)",
                  f'- Aberta por: "{por}" · teto {args.teto} min',
                  f"- Preflight: 0 às {_hora(t)} · marca ABERTA {_hora(t)} (vence {_hora(fim)})",
                  f"- Checkout: {ramo} {head[:9]} · container {CONTAINER}: {container}"):
        registrar(ex, dados, linha, t)
    print(f"{'[seco] ' if ex.seco else ''}janela aberta às {_hora(t)}; vence às {_hora(fim)}. "
          "Antes de mexer: backup.py, docker "
          "logs salvos e snapshot se for mexer no volume. Deixe rodando: jogavel.py janela vigiar")
    return OK


def janela_fechar(args, ex: Executor, relogio: Callable, _entrada) -> int:
    marca = ex.raiz / MARCA
    if not marca.exists():
        print(f"fechar: nenhuma janela aberta (sem {MARCA.as_posix()})")
        return FALHA
    dados, t = ler_marca(ex.raiz), relogio()
    print(f"janela {estado_janela(ex.raiz, t)}\nchecklist de fechamento (G6):")
    estado, antes = estado_container(ex), str(dados.get("container") or "")
    # De pé, ou deixado como estava: parado já na abertura (janela VPK de 28/09).
    como_estava = antes and not antes.startswith("Up") and not estado.startswith("docker indisponível")
    feitos = set(args.feito or [])
    itens = [(estado.startswith("Up") or bool(como_estava),
              f"container {CONTAINER}: {estado} (na abertura: {antes or 'não registrado'})"),
             (contar_cr(ex.raiz) == 0, "docker/pre.sh sem '\\r'")]
    itens += [(chave in feitos, f"{chave} (à mão): {texto}") for chave, texto in MANUAIS.items()]
    for ok, texto in itens:
        print(f"  [{'ok' if ok else 'FALTA'}] {texto}")
    if not all(ok for ok, _ in itens):
        pendentes = [c for c in MANUAIS if c not in feitos]
        extra = f" Confira à mão e passe --feito {' --feito '.join(pendentes)}." if pendentes else ""
        print(f"fechar recusado: a marca fica até o checklist passar.{extra}")
        return RECUSA
    head = ex.git("rev-parse", "HEAD").saida.strip()
    registrar(ex, dados, f"- Fechamento {_hora(t)} (jogavel.py janela fechar): container {estado} · "
              f"pre.sh LF · à mão, pelo servidor: {', '.join(MANUAIS)} · checkout {head[:9]} "
              f"(na abertura {str(dados.get('head') or '?')[:9]}) · ABERTA removida", t)
    if ex.seco:
        print(f"[seco] apagaria {MARCA.as_posix()}")
    else:
        marca.unlink()
    print("janela fechada")
    return OK


def janela_vigiar(args, ex: Executor, relogio: Callable, entrada: Callable) -> int:
    """Laço a cada ≤30 s. O tempo vem do relógio de parede e do mtime da
    marca, nunca da soma dos ciclos: um comando preso (o docker que esperou
    aprovação por horas em 27/09) aparece como ciclo lento no registro e não
    esconde o vencimento."""
    if not 0 < args.intervalo <= INTERVALO_VIGIA_S:
        print(f"vigiar: --intervalo vai até {INTERVALO_VIGIA_S} s")
        return USO
    dados = ler_marca(ex.raiz)
    teto_min = dados.get("teto_min")
    teto = min(teto_min * 60 if isinstance(teto_min, int) and teto_min > 0 else TETO_MAX_MIN * 60,
               TETO_MAX_MIN * 60)
    vigiar_container = str(dados.get("container") or "").startswith("Up")
    avisou_fim = avisou_parado = False
    parado_desde = None
    print(f"vigiando a janela a cada {args.intervalo:g} s (teto {teto // 60} min)")
    while True:
        ex.historico.clear()  # só o ciclo atual: a listagem de processos é grande
        inicio = relogio()
        bloqueios, avisos = sinais_de_processo(ex)
        if bloqueios or avisos:
            return _abortar(ex, dados, bloqueios + avisos, relogio, entrada)
        estado = estado_container(ex)
        t = relogio()
        if t - inicio > INTERVALO_VIGIA_S:
            lenta = max(ex.historico, key=lambda c: c.segundos)
            _avisar(ex, dados, t, f"ciclo de {t - inicio:.0f} s (limite {INTERVALO_VIGIA_S} s): "
                                  f"`{' '.join(lenta.argv)}` levou {lenta.segundos:.0f} s")
        try:
            idade = preflight.idade_da_marca(ex.raiz, t)
        except preflight.DeteccaoFalhou as exc:
            print(f"vigiar: {exc}")
            return FALHA
        if idade is None:
            print(f"{_hora(t)} marca removida: janela fechada, fim da vigília")
            return OK
        restante = teto - idade
        if restante <= 0 or not preflight.janela_vale(idade):
            _avisar(ex, dados, t, f"JANELA VENCIDA (marca de {int(idade // 60)} min, teto "
                                  f"{teto // 60} min): pare, devolva o jogável e rode `janela fechar`")
            return VENCIDA
        if restante <= AVISO_FIM_S and not avisou_fim:
            avisou_fim = True
            _avisar(ex, dados, t, f"faltam {int(restante // 60)} min para o teto "
                                  f"({_hora(t + restante)}): comece o fechamento")
        if vigiar_container and not estado.startswith("Up"):
            parado_desde = t if parado_desde is None else parado_desde
            if t - parado_desde > PARADO_MAX_S and not avisou_parado:
                avisou_parado = True
                _avisar(ex, dados, t, f"container {CONTAINER} parado há {int((t - parado_desde) // 60)} "
                                      f"min (máximo ~5 min por passo): {estado}")
        else:
            parado_desde, avisou_parado = None, False
        ex.dormir(max(0.0, args.intervalo - (relogio() - inicio)))


def _abortar(ex: Executor, dados: dict, sinais: list, relogio: Callable, entrada: Callable) -> int:
    """Processo do Victor na janela: avisa e devolve o checkout da abertura
    pelo `voltar` (que recria só se a infra difere e recusa com partida em
    curso). A marca fica: quem fecha é o `janela fechar`."""
    _avisar(ex, dados, relogio(), "ABORTO, processo do Victor (" + "; ".join(sinais) +
            "): pare tudo no servidor; a marca fica até o `janela fechar`")
    head = dados.get("head")
    if not head:
        print("HEAD da abertura desconhecido (marca sem dados): confira e rode `jogavel.py voltar`")
        return PARTIDA
    if ex.git("rev-parse", "HEAD").saida.strip() == head:
        print(f"checkout igual ao da abertura ({head[:9]}): nada a voltar pelo git")
    else:
        volta = argparse.Namespace(tag=head, agora=False, recriar=False, plugin=None)
        codigo = cmd_voltar(volta, ex, relogio(), entrada)
        _avisar(ex, dados, relogio(), f"voltar --tag {head[:9]} (checkout da abertura): saída {codigo}")
    print("VPK, volume e pasta do plugin não voltam pelo git: siga o rollback do runbook do passo")
    return PARTIDA


def _perguntar(entrada: Callable, texto: str) -> str:
    try:
        return entrada(texto).strip()
    except EOFError:
        return ""


def _sha256_arg(texto: str) -> str:
    if not RE_SHA.match(texto.lower()):
        raise argparse.ArgumentTypeError("esperado o sha256 inteiro (64 hex)")
    return texto.lower()


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
    voltar.add_argument("--plugin", type=_sha256_arg, default=None,
                        help="sha256 da DLL de captura a restaurar (tag sem o registro do `marcar`)")
    atualizar = sub.add_parser("atualizar", help="traz a origin/main para o checkout")
    atualizar.add_argument("--seco", action="store_true", help="só mostra o que faria")
    janela = sub.add_parser("janela", help="abrir, fechar ou vigiar a janela de manutenção")
    janela.add_argument("acao", choices=("abrir", "fechar", "vigiar"))
    janela.add_argument("--seco", action="store_true", help="só mostra o que faria")
    janela.add_argument("--por", help="abrir: frase literal do Victor, ou o OK dele repassado pelo PM")
    janela.add_argument("--teto", type=int, default=TETO_MAX_MIN,
                        help=f"abrir: minutos de janela (até {TETO_MAX_MIN}; trilha de bots: 30)")
    janela.add_argument("--feito", action="append", choices=tuple(MANUAIS),
                        help="fechar: item do checklist conferido à mão (repita para cada um)")
    janela.add_argument("--intervalo", type=float, default=INTERVALO_VIGIA_S,
                        help=f"vigiar: segundos entre ciclos (até {INTERVALO_VIGIA_S})")
    return parser


COMANDOS = {"status": cmd_status, "voltar": cmd_voltar, "atualizar": cmd_atualizar,
            "janela": cmd_janela}


def main(argv: Optional[list] = None, fabrica: Callable = Executor,
         entrada: Callable = input, agora: Optional[float] = None,
         relogio: Callable = time.time) -> int:
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
    return COMANDOS[args.comando](args, ex, agora=relogio() if agora is None else agora,
                                  entrada=entrada, relogio=relogio)


if __name__ == "__main__":
    sys.exit(main())
