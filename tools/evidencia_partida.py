#!/usr/bin/env python3
"""
Evidência de partida (card H1.1): cruza o que o servidor logou, o que a
captura arquivou e o que o banco guardou, e diz se a partida serve de
evidência para o G7 (plano, protocolo de jogabilidade §6, "evidência de
carona"; runbook do B1.3r, "Depois da janela").

Só leitura e só biblioteca padrão. Todas as entradas são explícitas:

  --log ARQ       docker logs salvos desde o StartedAt, com `docker logs -t`:
                  só o carimbo de cada linha separa overflow de signon de
                  overflow em jogo. Linha sem carimbo próprio fica sem tempo
                  (não herda o da anterior). A timeline do tools/live_watch.py
                  também é lida (só as linhas [docker]), mas o live_watch
                  filtra o docker por round, jogador, warmup, MatchZy, fim e
                  bot: crash, overflow, SIGNONSTATE e a carga da captura nunca
                  chegam nela, e com ela o veredito é no máximo SEM EVIDÊNCIA.
  --eventos DIR   CÓPIA da pasta de captura: events_<matchid>_map<N>.jsonl
                  arquivados e current.jsonl. A docker/events-live do checkout
                  principal é recusada (AGENTS.md, zonas proibidas). O sufixo
                  __<utc> do P1.1a já é listado; casar a partida do log com o
                  arquivo sufixado fica para o P1.1a (DoD 4).
  --db ARQ        CÓPIA do banco SQLite pedida ao PM, aberta com mode=ro; o
                  relatório diz se o mtime ficou intacto. O banco real do
                  checkout principal é sempre recusado (AGENTS.md; runbook da
                  trilha de bots, critério 4).
  --sha-montados, --sha-referencia   saídas de sha256sum (dentro do container
                  e do checkout ou do registro da janela), casadas pelo nome.
                  Os 5 arquivos do protocolo §3 precisam estar conferidos.
  --config-hash, --config-hash-janela   o config-hash de agora e o da janela;
                  sem os dois não há OK (G7).
  --partida DEMO  julga só esta partida (repetível). Sem ela, julga as que
                  terminaram no log ("MAP ENDED").
  --assinatura-proibida NOME, --fatal-esperado PLUGIN   critérios do card.

Veredito, na última linha:
  RUIM           crash (Segmentation fault, Stack overflow, core dumped,
                 FATAL ERROR, MatchZy carregada de novo = processo que
                 reiniciou), Fatal error de plugin não esperado, overflow
                 depois de SIGNONSTATE_FULL + 60 s, assinatura proibida, mapa
                 NULL, placar fora do MR12, times fora de 5x5, colisão de
                 demo_name, current.jsonl com rounds não arquivados quando
                 todas as partidas do log terminaram em MAP ENDED;
  SEM EVIDÊNCIA  falta entrada, nenhuma partida terminou, partida abandonada
                 (current.jsonl com os rounds da partida sem fim), partida não
                 arquivada ou não ingerida, placar parcial, log sem as linhas
                 de carga, timeline do live_watch, overflow sem carimbo, sha
                 ou config-hash não conferido;
  OK             nenhum dos dois.
RUIM vence SEM EVIDÊNCIA, menos quando a evidência é inválida: sha montado
divergente, arquivo da referência que não foi conferido no container, build
que mudou no log ou config-hash diferente do da janela. Aí o servidor não
rodava o candidato, ou mudaram 2 variáveis: o veredito é SEM EVIDÊNCIA e os
motivos de RUIM ficam listados (protocolo §6; runbook da trilha de bots,
confundidor 3). O que o acervo mostra fora das partidas julgadas (JSONL antigo
sem linha no banco, por exemplo) é informativo.

Saída: 0 OK, 1 RUIM, 3 SEM EVIDÊNCIA, 2 uso errado ou recusa, 4 erro interno
(a ferramenta quebrou: não é veredito e não é motivo de revert).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

CHECKOUT = Path("C:/Users/Victor/Projetos/cs2-tracker")
BANCO_REAL = CHECKOUT / "cs2_tracker.db"
EVENTOS_REAL = CHECKOUT / "docker" / "events-live"
OK, RUIM, SEM = "OK", "RUIM", "SEM EVIDÊNCIA"
CODIGO = {OK: 0, RUIM: 1, SEM: 3}
ERRO_INTERNO = 4
SEGUNDOS_SIGNON = 60
# mp_overtime_limit em server-configs/cfg/gamemode_competitive_server.cfg.
LIMITE_PRORROGACOES = 3
# Depois do arquivamento o plugin ainda escreve isto no current.jsonl: é normal.
TIPOS_DA_CAUDA = frozenset({"snapshot", "round_stats", "round_officially_ended"})
GRANADAS = frozenset({"hegrenade", "inferno", "molotov", "incgrenade"})
# Linhas de overflow da mesma classe mais próximas que isto são o mesmo episódio.
EPISODIO_S, EPISODIO_LINHAS = 5.0, 20
# Protocolo §3 e G6: sha256 lido DENTRO do container destes arquivos.
SHA_DO_PROTOCOLO = ("gamemode_competitive_server.cfg", "pre.sh", "match_config.spike.json",
                    "Cs2TrackerEvents.dll", "Cs2TrackerEvents.deps.json")
# Fontes de placar em que score_ct + score_t = score_mine + score_theirs. No
# rounds-partial o round sem lado do humano fica fora do placar da partida.
SOMA_CONFERE = frozenset({"rounds", "rounds-reconciled"})
# O parser grava played_at com datetime.now() ao ingerir, uns 10 s depois do
# MAP ENDED (reingestão mantém o original). Linha mais velha que o fim da
# partida menos isto é de outra partida: matchid reusado.
TOLERANCIA_PLAYED_AT_S = 15 * 60
# Fuso do Windows onde rodam o watcher (played_at) e o live_watch (cabeçalho
# da sessão). None = o fuso desta máquina, que é a do Victor.
FUSO_LOCAL = None


class Recusa(Exception):
    """Entrada que a ferramenta não lê (banco real, events-live viva, arquivo ausente)."""


def _epoch_local(dt: datetime) -> float:
    """Epoch de uma data ingênua na hora local do Windows (FUSO_LOCAL)."""
    if dt.tzinfo is None and FUSO_LOCAL is not None:
        dt = dt.replace(tzinfo=FUSO_LOCAL)
    return dt.timestamp()


def _data_local(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, FUSO_LOCAL).replace(tzinfo=None)


def _int(valor):
    """int de verdade (bool não conta) ou None: o JSONL vem de fora."""
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _texto(valor):
    return valor if isinstance(valor, str) else None


def _contagem(valor) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _jogadores(evento) -> list:
    jogadores = evento.get("players")
    return [p for p in jogadores if isinstance(p, dict)] if isinstance(jogadores, list) else []


# ------------------------------------------------------------------ log

_T_DOCKER = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z?\s?(.*)$")
_T_SESSAO = re.compile(r"^===== sessão iniciada (\S+) =====")
_T_LIVE = re.compile(r"^\[\s*(\d+(?:\.\d+)?)s\] \[(\w+)\s*\] ?(?:\(\w+\) )?(.*)$")
_T_L = re.compile(r"^L (\d\d/\d\d/\d{4} - \d\d:\d\d:\d\d): ?(.*)$")
_T_HORA = re.compile(r"^(\d\d):(\d\d):(\d\d(?:\.\d+)?)\s+(.*)$")

_CRASH = (
    ("segfault", "Segmentation fault", re.compile(r"Segmentation fault|SIGSEGV")),
    ("stack_overflow", "Stack overflow", re.compile(r"Stack overflow", re.I)),
    ("core_dumped", "core dumped", re.compile(r"core dumped", re.I)),
    ("fatal_motor", "FATAL ERROR", re.compile(r"FATAL ERROR")),
)
_FATAL_PLUGIN = re.compile(r"Fatal error")
_ASSINATURAS = (
    re.compile(r"Failed to find signature for '([^']+)'"),
    re.compile(r"Signature for '([^']+)' is not found"),
    re.compile(r"\(plugin: [^)]+\)\s*([\w.]+): FAILED\b"),
)
_RECUSADO = re.compile(r"Failed to load plugin ([^\s:]+)")
_MATCHZY = re.compile(r"\[MatchZy ([\d.]+) LOADED\]")
_PRONTO = re.compile(r"\[Cs2TrackerEvents\] Pronto")
_CARREGOU = re.compile(r"Finished loading plugin (.+?)\s*$")
_SETUP = re.compile(r"\[(METAMOD|CSSHARP) SETUP\] complete: version (\S+?) installed")
_BUILD = re.compile(r"PatchVersion=(\S+)|Exe version (\S+)")
_OVERFLOW = re.compile(
    r"NETWORK_DISCONNECT_OVERFLOW|ProcessMessages has taken more than|"
    r"Disconnecting netchan because of excessive CPU|overflowed reliable|"
    r"reliable (?:buffer|channel|stream|state) overflow", re.I)
_FULL = re.compile(r"->\s*SIGNONSTATE_FULL\b|\[FULL CONNECT\]")
# Cliente saindo do FULL (conectando de novo ou caiu): até o próximo FULL, é signon.
_FORA_DO_FULL = re.compile(r"->\s*SIGNONSTATE_(?!FULL\b)\w+")
_TROCA_MAPA = re.compile(r"\[ChangeMap\] Changing map to (\w+)")
_DEMO = re.compile(r"Starting demo recording, path: \S*?"
                   r"(\d{4}-\d\d-\d\d)_(\d\d)-(\d\d)-(\d\d)_(\d+)_([a-z]+_[a-z0-9]+)_")
_LIVE = re.compile(r"\[StartLive\]")
_FIM_MAPA = re.compile(r"MAP ENDED.*?matchid: (\d+) currentMapNumber: (\d+)")


def ler_texto(caminho) -> str:
    """UTF-8, ou UTF-16 quando o log veio de um `>` do PowerShell."""
    bruto = Path(caminho).read_bytes()
    if bruto[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return bruto.decode("utf-16")
    return bruto.decode("utf-8-sig", errors="replace")


def _ler(texto: str):
    """([(número, segundos ou None, texto sem prefixo, absoluto)], formatos,
    linhas sem carimbo).

    Cada linha fica com o próprio carimbo ou sem tempo: herdar o da anterior
    num log carimbado só em parte (L, hora) daria a um FULL e a um overflow
    10 min depois o mesmo tempo. `absoluto` diz se o tempo é epoch de verdade
    (docker -t, em UTC; live_watch com o cabeçalho da sessão). Na timeline do
    live_watch as linhas [evento], [placar] e [setup] não são do servidor e
    ficam de fora."""
    linhas, formatos, sem_carimbo = [], set(), 0
    base = hora_anterior = None
    dia = 0
    for n, bruta in enumerate(texto.splitlines(), 1):
        bruta = bruta.rstrip()
        if not bruta:
            continue
        if m := _T_SESSAO.match(bruta):
            try:
                base = _epoch_local(datetime.fromisoformat(m.group(1)))
            except ValueError:
                base = None
            continue
        t, corpo, absoluto, formato = None, bruta, False, None
        if m := _T_DOCKER.match(bruta):
            try:
                inicio = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
            except ValueError:
                inicio = None   # carimbo malformado: a linha fica sem tempo
            if inicio is not None:
                micro = int((m.group(2) or "0")[:6].ljust(6, "0"))
                t, corpo = inicio.timestamp() + micro / 1e6, m.group(3)
                absoluto, formato = True, "docker -t"
        elif m := _T_LIVE.match(bruta):
            if m.group(2) != "docker":
                continue
            t, corpo = (base or 0.0) + float(m.group(1)), m.group(3)
            absoluto, formato = base is not None, "live_watch"
        elif m := _T_L.match(bruta):
            try:
                t = _epoch_local(datetime.strptime(m.group(1), "%m/%d/%Y - %H:%M:%S"))
                corpo, formato = m.group(2), "L"
            except ValueError:
                t = None
        elif m := _T_HORA.match(bruta):
            s = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            if hora_anterior is not None and s < hora_anterior - 43200:
                dia += 1   # passou da meia-noite
            hora_anterior = s
            t, corpo, formato = dia * 86400 + s, m.group(4), "hora"
        if formato:
            formatos.add(formato)
        else:
            sem_carimbo += 1
        linhas.append((n, t, corpo, absoluto))
    return linhas, formatos, sem_carimbo


def _rotulo(formatos, sem_carimbo) -> str:
    if not formatos:
        return "sem carimbo"
    rotulo = " + ".join(sorted(formatos))
    return rotulo + (f" ({sem_carimbo} linha(s) sem carimbo)" if sem_carimbo else "")


def ler_linhas(texto: str):
    """([(número, segundos ou None, texto sem prefixo)], rótulo do carimbo)."""
    linhas, formatos, sem_carimbo = _ler(texto)
    return [(n, t, corpo) for n, t, corpo, _ in linhas], _rotulo(formatos, sem_carimbo)


def _plugin(corpo: str) -> str:
    """Dono da linha: (plugin: X), CSSharp, ou o primeiro [X]."""
    if m := re.search(r"\(plugin: ([^)]+)\)", corpo):
        return m.group(1).strip()
    if "CSSharp" in corpo or "CounterStrikeSharp" in corpo:
        return "CSSharp"
    if m := re.search(r"\[([A-Za-z][\w .-]*)\]", corpo):
        return m.group(1)
    return "?"


def _novo_trecho(inicio):
    return {"inicio": inicio, "mapa": None, "mapa_demo": None, "demo": None, "live": False}


def analisar_log(texto: str) -> dict:
    linhas, formatos, sem_carimbo = _ler(texto)
    crash = {chave: 0 for chave, _, _ in _CRASH}
    crash_linhas, fatal_plugin, recusados, builds = [], [], [], []
    assinaturas: dict[str, Counter] = {}
    carregados, versoes = {}, {}
    boots = prontos = 0
    sinais, overflows, partidas = [], [], []
    trecho = _novo_trecho(1)
    for n, t, corpo, absoluto in linhas:
        for chave, _, rx in _CRASH:
            if rx.search(corpo):
                crash[chave] += 1
                crash_linhas.append({"linha": n, "tipo": chave, "texto": corpo[:160]})
        if _FATAL_PLUGIN.search(corpo):
            fatal_plugin.append({"linha": n, "plugin": _plugin(corpo), "texto": corpo[:160]})
        for rx in _ASSINATURAS:
            if m := rx.search(corpo):
                assinaturas.setdefault(_plugin(corpo), Counter())[m.group(1)] += 1
                break
        if m := _RECUSADO.search(corpo):
            recusados.append(m.group(1).rsplit("/", 1)[-1])
        if m := _MATCHZY.search(corpo):
            boots += 1
            carregados["MatchZy"] = m.group(1)
        if _PRONTO.search(corpo):
            prontos += 1
            carregados["Cs2TrackerEvents"] = "Pronto"
        if m := _CARREGOU.search(corpo):
            carregados.setdefault(m.group(1), "carregado")
        if m := _SETUP.search(corpo):
            versoes[m.group(1).lower()] = m.group(2)
        if m := _BUILD.search(corpo):
            build = m.group(1) or m.group(2)
            if build not in builds:
                builds.append(build)
        if _FULL.search(corpo):
            sinais.append((n, t, "full"))
        elif _FORA_DO_FULL.search(corpo) or _TROCA_MAPA.search(corpo):
            sinais.append((n, t, "conectando"))
        if _OVERFLOW.search(corpo):
            overflows.append((n, t, corpo))
        if m := _TROCA_MAPA.search(corpo):
            trecho["mapa"] = m.group(1)
        if m := _DEMO.search(corpo):
            data, hh, mm, ss = m.group(1, 2, 3, 4)
            trecho["demo"] = f"{data}T{hh}:{mm}:{ss}"
            trecho["mapa_demo"] = m.group(6)
        if _LIVE.search(corpo):
            trecho["live"] = True
        if m := _FIM_MAPA.search(corpo):
            matchid, num = int(m.group(1)), int(m.group(2))
            partidas.append({
                "demo_name": f"events_{matchid}_map{num}", "matchid": matchid, "mapa_num": num,
                "mapa": trecho["mapa_demo"] or trecho["mapa"], "inicio_demo": trecho["demo"],
                "fim_epoch": t if absoluto else None,
                "linha_inicio": trecho["inicio"], "linha_fim": n,
            })
            trecho = _novo_trecho(n + 1)
    sem_fim = None
    if trecho["live"] or trecho["demo"]:
        sem_fim = {"mapa": trecho["mapa_demo"] or trecho["mapa"], "inicio_demo": trecho["demo"],
                   "linha_inicio": trecho["inicio"]}
    nomes = Counter(p["demo_name"] for p in partidas)
    return {
        "linhas": len(linhas), "carimbo": _rotulo(formatos, sem_carimbo),
        "timeline_live_watch": "live_watch" in formatos,
        "crash": crash, "crash_linhas": crash_linhas, "fatal_plugin": fatal_plugin,
        "assinaturas": {p: dict(c) for p, c in sorted(assinaturas.items())},
        "recusados": recusados, "carregados": carregados, "boots_matchzy": boots,
        "prontos": prontos, "versoes": versoes, "builds": builds,
        "overflow": _episodios(overflows, sinais, partidas, sem_fim),
        "partidas": partidas, "partida_sem_fim": sem_fim,
        "repetidos": sorted(n for n, q in nomes.items() if q > 1),
    }


def _classe(n, t, sinais):
    """signon (antes de FULL + 60 s), em_jogo, ou sem_carimbo. Antes de
    qualquer FULL, ou com o cliente fora dele (troca de mapa, outro estado de
    signon), ainda é signon: o FULL que vale é o da conexão atual."""
    anteriores = [(ns, ts, tipo) for ns, ts, tipo in sinais if ns < n]
    if not anteriores or anteriores[-1][2] != "full":
        return "signon", None
    _, tf, _ = anteriores[-1]
    if t is None or tf is None:
        return "sem_carimbo", None
    delta = round(t - tf, 1)
    return ("signon" if delta <= SEGUNDOS_SIGNON else "em_jogo"), delta


def _dono(n, partidas, sem_fim):
    for p in partidas:
        if p["linha_inicio"] <= n <= p["linha_fim"]:
            return p["demo_name"]
    if sem_fim and n >= sem_fim["linha_inicio"]:
        return "(partida sem fim)"
    return None


def _episodios(overflows, sinais, partidas, sem_fim) -> dict:
    """Agrupa linhas de overflow em episódios. Cada linha é classificada antes
    de agrupar, e só entra no episódio anterior se tem a mesma classe e a
    mesma partida: uma série que atravessa FULL + 60 s vira um episódio de
    signon e outro em jogo, e o em jogo não some dentro do primeiro."""
    episodios = []
    for n, t, corpo in overflows:
        classe, delta = _classe(n, t, sinais)
        dono = _dono(n, partidas, sem_fim)
        ult = episodios[-1] if episodios else None
        if ult is not None and ult["classe"] == classe and ult["partida"] == dono:
            perto = (t - ult["_t"] <= EPISODIO_S) if (t is not None and ult["_t"] is not None) \
                else (n - ult["_n"] <= EPISODIO_LINHAS)
            # Um FULL no meio é reconexão: o overflow seguinte é outro episódio.
            reconectou = any(ult["_n"] < ns < n for ns, _, tipo in sinais if tipo == "full")
            if perto and not reconectou:
                ult["_t"], ult["_n"] = t, n
                ult["linhas"] += 1
                continue
        episodios.append({"linha": n, "classe": classe, "segundos_apos_full": delta,
                          "partida": dono, "texto": corpo[:160],
                          "linhas": 1, "_t": t, "_n": n})
    por_partida: dict = {}
    for e in episodios:
        del e["_t"], e["_n"]
        chave = e["partida"] or "(fora de partida)"
        por_partida.setdefault(chave, Counter())[e["classe"]] += 1
    total = Counter(e["classe"] for e in episodios)
    return {"episodios": episodios, "total": dict(total),
            "por_partida": {k: dict(v) for k, v in por_partida.items()}}


# ------------------------------------------------------------------ eventos

# O sufixo __<utc> é o do P1.1a (colisão de demo_name nunca descarta partida).
_ARQUIVADO = re.compile(r"^events_(\d+)_map(\d+)(?:__[\w-]+)?\.jsonl$")


def ler_jsonl(caminho):
    eventos, ruins = [], 0
    with open(caminho, encoding="utf-8-sig", errors="replace") as arq:
        for linha in arq:
            linha = linha.strip()
            if not linha:
                continue
            try:
                evento = json.loads(linha)
            except json.JSONDecodeError:
                ruins += 1
                continue
            if isinstance(evento, dict):
                eventos.append(evento)
            else:
                ruins += 1
    return eventos, ruins


def arquivados(pasta: Path) -> dict:
    return {p.stem: p for p in sorted(pasta.iterdir())
            if _ARQUIVADO.match(p.name) and p.is_file()}


def _tipo(evento) -> str:
    tipo = evento.get("type")
    return tipo if isinstance(tipo, str) else str(tipo)


def analisar_current(pasta: Path) -> dict:
    """current.jsonl depois do arquivamento: só a cauda (snapshot, round_stats,
    round_officially_ended) é normal; qualquer outro evento é round que não
    foi arquivado."""
    caminho = pasta / "current.jsonl"
    if not caminho.is_file():
        return {"estado": "ausente"}
    eventos, ruins = ler_jsonl(caminho)
    if not eventos:
        return {"estado": "vazio", "linhas_ruins": ruins}
    tipos = Counter(_tipo(e) for e in eventos)
    fora = [e for e in eventos if _tipo(e) not in TIPOS_DA_CAUDA]
    rounds = {_int(e.get("round_num")) for e in (fora or eventos)}
    return {"estado": "com_rounds" if fora else "cauda_normal", "tipos": dict(tipos),
            "rounds": sorted(r for r in rounds if r is not None), "linhas_ruins": ruins}


def times(eventos) -> tuple:
    """(True/False/None, {round: (ct, t)} fora de 5x5). Vem do round_stats ou,
    sem ele, do freeze_end. Só lado ct/t conta: o bot do GOTV não tem lado."""
    por_round = {}
    for tipo in ("round_stats", "freeze_end"):
        for e in eventos:
            if e.get("type") == tipo:
                lados = Counter(_texto(p.get("side")) for p in _jogadores(e))
                por_round[_int(e.get("round_num"))] = (lados.get("ct", 0), lados.get("t", 0))
        if por_round:
            break
    if not por_round:
        return None, {}
    fora = {r: v for r, v in sorted(por_round.items(), key=lambda kv: kv[0] or 0)
            if v != (5, 5)}
    return not fora, fora


def granadas_bot(eventos):
    """Granadas dos bots (linha de base do B1.8). O motor (CSMatchStats_t) dá
    o acumulado de utility_count e flash_count no último round_stats do
    arquivo, que costuma parar um round antes do fim: o round_stats do último
    round sai depois do arquivamento, na cauda do current.jsonl. Os eventos dão
    o dano de granada e as cegueiras causadas por bot, da partida inteira."""
    bots, humanos = set(), set()
    for e in eventos:
        for p in _jogadores(e):
            nome, bot = _texto(p.get("name", p.get("n"))), p.get("is_bot", p.get("b"))
            # Sem lado ct/t é o bot do GOTV, que não joga.
            if nome is not None and bot is not None and p.get("side", p.get("s")) in ("ct", "t"):
                (bots if bot else humanos).add(nome)
    bots -= humanos
    if not bots:
        return None
    dano = sum(1 for e in eventos if e.get("type") == "player_hurt"
               and _texto(e.get("weapon")) in GRANADAS
               and _texto(e.get("attacker_name")) in bots)
    cegueiras = sum(1 for e in eventos if e.get("type") == "player_blind"
                    and _texto(e.get("attacker_name")) in bots)
    stats = [e for e in eventos if e.get("type") == "round_stats"]
    motor = None
    if stats:
        ultimo = max(stats, key=lambda e: _int(e.get("round_num")) or 0)
        jog = [p for p in _jogadores(ultimo)
               if p.get("is_bot") and p.get("side") in ("ct", "t")]
        motor = {"utility": sum(_contagem(p.get("utility_count")) for p in jog),
                 "flash": sum(_contagem(p.get("flash_count")) for p in jog),
                 "ate_round": _int(ultimo.get("round_num"))}
    return {"bots": len(bots), "dano_de_granada": dano, "cegueiras": cegueiras, "motor": motor}


# ------------------------------------------------------------------ banco

def _mesmo_arquivo(a, b) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _checar_banco(caminho: Path):
    if not caminho.is_file():
        raise Recusa(f"banco não encontrado: {caminho}")
    if _mesmo_arquivo(caminho, BANCO_REAL):
        raise Recusa("é o banco real do checkout principal, que agente nunca abre "
                     "(AGENTS.md, zonas proibidas): peça ao PM uma cópia mode=ro")


def abrir_banco(caminho) -> sqlite3.Connection:
    """Conexão mode=ro + query_only numa cópia; o banco real é recusado."""
    caminho = Path(caminho)
    _checar_banco(caminho)
    conn = sqlite3.connect(caminho.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = 1")
    conn.row_factory = sqlite3.Row
    return conn


def ler_matches(caminho) -> tuple:
    """({demo_name: linha}, intacto): lê a tabela matches e confere que o
    mtime e o tamanho do arquivo não mudaram."""
    _checar_banco(Path(caminho))
    antes = os.stat(caminho)
    conn = abrir_banco(caminho)
    try:
        cursor = conn.execute("SELECT * FROM matches")
        if "demo_name" not in [d[0] for d in cursor.description]:
            raise Recusa("tabela matches sem a coluna demo_name")
        linhas = {r["demo_name"]: dict(r) for r in cursor if isinstance(r["demo_name"], str)}
    except sqlite3.Error as exc:
        raise Recusa(f"banco sem tabela matches legível: {exc}") from exc
    finally:
        conn.close()
    depois = os.stat(caminho)
    intacto = (antes.st_mtime_ns, antes.st_size) == (depois.st_mtime_ns, depois.st_size)
    return linhas, intacto


def _placar(valor):
    """Placar como int, aceitando o texto de dígitos; senão None."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, str) and valor.strip().isdigit():
        return int(valor)
    return None


def motivo_placar(a, b):
    """None se a x b fecha MR12 com prorrogação MR3 (até LIMITE_PRORROGACOES,
    e empate depois dela); senão, o motivo."""
    if a is None or b is None:
        return "placar vazio"
    na, nb = _placar(a), _placar(b)
    if na is None or nb is None:
        return f"{a!r}x{b!r}: placar não numérico"
    a, b = na, nb
    alto, baixo = max(a, b), min(a, b)
    if alto == 13 and baixo <= 11:
        return None
    for k in range(LIMITE_PRORROGACOES):
        base = 12 + 3 * k
        if alto == base + 4 and base <= baixo <= base + 2:
            return None
    if alto == baixo == 12 + 3 * LIMITE_PRORROGACOES:
        return None
    if alto < 13:
        return f"{a}x{b}: ninguém chegou a 13 (partida incompleta)"
    return f"{a}x{b} não fecha MR12 (13 no tempo normal; 16, 19 ou 22 na prorrogação)"


def _stem(caminho):
    if not caminho:
        return None
    return re.split(r"[\\/]", str(caminho))[-1].rsplit(".", 1)[0]


def _data(texto):
    try:
        return datetime.fromisoformat(str(texto)[:19])
    except ValueError:
        return None


def colisoes(partida: dict, linha, repetidos) -> list:
    motivos = []
    if partida["demo_name"] in repetidos:
        motivos.append("demo_name repetido no log (matchid reusado)")
    if not linha:
        return motivos
    stem = _stem(linha.get("demo_path"))
    if stem and stem != partida["demo_name"]:
        motivos.append(f"demo_path do banco aponta para {stem}")
    if partida.get("mapa") and linha.get("map") and linha["map"] != partida["mapa"]:
        motivos.append(f"mapa do banco ({linha['map']}) difere do log ({partida['mapa']})")
    jogada, inicio = _data(linha.get("played_at")), _data(partida.get("inicio_demo"))
    fim = partida.get("fim_epoch")
    if jogada and fim is not None:
        # Mesmo dia e mesmo mapa também pega: snapshot restaurado reusa o
        # matchid, o watcher pula o arquivamento e o parser, a ingestão.
        if _epoch_local(jogada) < fim - TOLERANCIA_PLAYED_AT_S:
            motivos.append(f"linha do banco é de {jogada:%Y-%m-%d %H:%M}, antes do fim da "
                           f"partida no log ({_data_local(fim):%Y-%m-%d %H:%M})")
    elif jogada and inicio and jogada < inicio - timedelta(days=1):
        # Sem carimbo absoluto no log, só a data da demo (UTC do container).
        motivos.append(f"linha do banco é de {jogada:%Y-%m-%d}, antes da partida do log "
                       f"({inicio:%Y-%m-%d})")
    return motivos


def acervo(linhas: dict, arquivos) -> dict:
    """O que está errado no banco e na pasta, fora das partidas julgadas."""
    placar = {}
    for dn, r in linhas.items():
        if r.get("score_source") == "rounds-partial":
            continue   # placar parcial não diz nada sobre o MR12
        if r.get("score_mine") is not None and r.get("score_theirs") is not None:
            if motivo := motivo_placar(r["score_mine"], r["score_theirs"]):
                placar[dn] = motivo
    return {
        "sem_linha_no_banco": sorted(set(arquivos or ()) - set(linhas)),
        "mapa_null": sorted(dn for dn, r in linhas.items() if not r.get("map")),
        "placar_fora_do_mr12": placar,
        "demo_path_divergente": {dn: _stem(r.get("demo_path")) for dn, r in sorted(linhas.items())
                                 if _stem(r.get("demo_path")) not in (None, dn)},
    }


# ------------------------------------------------------------------ sha

_SHA = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$")


def ler_sha(caminho) -> dict:
    """sha256sum -> {nome do arquivo: hash}; o caminho varia entre container e checkout."""
    saida = {}
    for linha in ler_texto(caminho).splitlines():
        if m := _SHA.match(linha.strip()):
            saida[re.split(r"[\\/]", m.group(2))[-1]] = m.group(1).lower()
    return saida


def comparar_sha(montados: dict, referencia: dict) -> dict:
    """`so_na_referencia` é arquivo que devia estar montado e não foi conferido
    no container: o `docker exec sha256sum` manda o arquivo ausente para o
    stderr, então a DLL não montada some da lista sem erro."""
    comuns = sorted(set(montados) & set(referencia))
    return {"conferidos": comuns,
            "divergentes": [n for n in comuns if montados[n] != referencia[n]],
            "so_no_container": sorted(set(montados) - set(referencia)),
            "so_na_referencia": sorted(set(referencia) - set(montados))}


# ------------------------------------------------------------------ juntar

def _checar_eventos(pasta: Path):
    if not pasta.is_dir():
        raise Recusa(f"pasta de eventos não encontrada: {pasta}")
    if _mesmo_arquivo(pasta, EVENTOS_REAL):
        # No Windows, o open() do Python não compartilha FILE_SHARE_DELETE: com
        # o current.jsonl aberto aqui, o rename do watcher para arquivar falha.
        raise Recusa("é a docker/events-live viva do checkout principal (AGENTS.md, zonas "
                     "proibidas): use uma cópia da pasta")


def avaliar(log=None, eventos=None, db=None, partidas=(), sha_montados=None,
            sha_referencia=None, config_hash=None, config_hash_janela=None,
            assinaturas_proibidas=(), fatais_esperados=()) -> dict:
    res = {"entradas": {"log": log and str(log), "eventos": eventos and str(eventos),
                        "db": db and str(db)}}
    res["log"] = analisar_log(ler_texto(log)) if log else None
    linhas = arquivos = None
    if eventos:
        pasta = Path(eventos)
        _checar_eventos(pasta)
        arquivos = arquivados(pasta)
        res["current"] = analisar_current(pasta)
    if db:
        linhas, res["entradas"]["banco_intacto"] = ler_matches(db)
        res["acervo"] = acervo(linhas, arquivos)
    res["sha"] = (comparar_sha(ler_sha(sha_montados), ler_sha(sha_referencia))
                  if sha_montados and sha_referencia else None)
    res["config_hash"] = {"agora": config_hash, "janela": config_hash_janela}

    do_log = {p["demo_name"]: p for p in (res["log"] or {}).get("partidas", [])}
    nomes = list(partidas) or list(do_log)
    repetidos = (res["log"] or {}).get("repetidos", [])
    julgadas = []
    for dn in dict.fromkeys(nomes):
        p = dict(do_log.get(dn) or {"demo_name": dn, "mapa": None, "inicio_demo": None,
                                    "fim_epoch": None})
        linha = (linhas or {}).get(dn)
        p["arquivado"] = None if arquivos is None else dn in arquivos
        p["ingerida"] = None if linhas is None else linha is not None
        p["banco"] = linha and {k: linha.get(k) for k in (
            "id", "map", "played_at", "score_mine", "score_theirs", "score_ct", "score_t",
            "score_source", "demo_path")}
        p["colisoes"] = colisoes(p, linha, repetidos)
        p["times_5x5"], p["fora_de_5x5"], p["granadas_bot"] = None, {}, None
        if p["arquivado"]:
            evs, _ = ler_jsonl(arquivos[dn])
            p["times_5x5"], p["fora_de_5x5"] = times(evs)
            p["granadas_bot"] = granadas_bot(evs)
        julgadas.append(p)
    res["partidas"] = julgadas
    res["veredito"] = veredito(res, set(assinaturas_proibidas), set(fatais_esperados))
    return res


def veredito(res: dict, proibidas: set, fatais_esperados: set) -> dict:
    ruim, sem, invalidam = [], [], []

    def invalida(motivo):
        """SEM EVIDÊNCIA que vence RUIM: a partida não testou o candidato."""
        sem.append(motivo)
        invalidam.append(motivo)

    log = res["log"]
    if log is None:
        sem.append("sem --log")
    else:
        for chave, rotulo, _ in _CRASH:
            if log["crash"][chave]:
                ruim.append(f"{log['crash'][chave]}x {rotulo} no log")
        for f in log["fatal_plugin"]:
            if f["plugin"] not in fatais_esperados:
                ruim.append(f"Fatal error de {f['plugin']} (linha {f['linha']})")
        total = log["overflow"]["total"]
        if total.get("em_jogo"):
            ruim.append(f"{total['em_jogo']} overflow(s) depois de SIGNONSTATE_FULL + "
                        f"{SEGUNDOS_SIGNON} s")
        if total.get("sem_carimbo"):
            sem.append(f"{total['sem_carimbo']} overflow(s) depois de FULL sem carimbo de "
                       "tempo: salve o log com docker logs -t")
        if log.get("timeline_live_watch"):
            sem.append("timeline do live_watch não captura crash nem overflow: salve o log "
                       "com docker logs -t")
        vistas = {n for nomes in log["assinaturas"].values() for n in nomes}
        for nome in sorted(proibidas & vistas):
            ruim.append(f"assinatura proibida no log: {nome}")
        if log["boots_matchzy"] > 1:
            # Desde o StartedAt a MatchZy carrega uma vez; outra carga é o
            # cs2.sh subindo o processo de novo (runbook do B1.3r, passo 10).
            ruim.append(f"MatchZy carregou {log['boots_matchzy']}x: o processo reiniciou")
        if "MatchZy" not in log["carregados"]:
            sem.append("log sem [MatchZy ... LOADED]: colete desde o StartedAt")
        if not log["prontos"]:
            sem.append("log sem [Cs2TrackerEvents] Pronto: colete desde o StartedAt")
        if len(log["builds"]) > 1:
            invalida(f"build mudou no log ({' -> '.join(log['builds'])}): 2 variáveis")
    if not res["partidas"]:
        sem.append("nenhuma partida terminou no log (MAP ENDED)")
    for p in res["partidas"]:
        dn = p["demo_name"]
        if p["arquivado"] is False:
            sem.append(f"{dn}: JSONL não arquivado")
        if p["ingerida"] is False:
            sem.append(f"{dn}: não ingerida (sem linha no banco)")
        if b := p["banco"]:
            if not b["map"]:
                ruim.append(f"{dn}: mapa NULL no banco")
            if b.get("score_source") == "rounds-partial":
                sem.append(f"{dn}: placar parcial ({b['score_mine']}x{b['score_theirs']}): "
                           "round sem lado do humano (score_source rounds-partial)")
            elif motivo := motivo_placar(b["score_mine"], b["score_theirs"]):
                ruim.append(f"{dn}: placar {motivo}")
            elif b.get("score_source") in SOMA_CONFERE:
                ct, t, mine, theirs = (_placar(b[k]) for k in (
                    "score_ct", "score_t", "score_mine", "score_theirs"))
                if None not in (ct, t) and ct + t != mine + theirs:
                    ruim.append(f"{dn}: placar por lado ({b['score_ct']}+{b['score_t']}) não "
                                f"soma o placar da partida ({b['score_mine']}+"
                                f"{b['score_theirs']})")
        if p["times_5x5"] is False:
            ruim.append(f"{dn}: times fora de 5x5 nos rounds {list(p['fora_de_5x5'])}")
        elif p["arquivado"] and p["times_5x5"] is None:
            sem.append(f"{dn}: JSONL sem round_stats nem freeze_end para conferir o 5x5")
        for c in p["colisoes"]:
            ruim.append(f"{dn}: colisão: {c}")
    if res["entradas"]["eventos"] is None:
        sem.append("sem --eventos")
    elif res["current"]["estado"] == "com_rounds":
        rounds = f"current.jsonl com rounds não arquivados (rounds {res['current']['rounds']})"
        if log is None:
            sem.append(f"{rounds}: sem --log não dá para saber se a partida foi abandonada")
        elif sf := log["partida_sem_fim"]:
            # Protocolo §6: abandonada é sem evidência; e o P1 trata o órfão da
            # partida interrompida como normal.
            sem.append(f"partida abandonada: current.jsonl com rounds da partida sem fim "
                       f"({sf['mapa'] or '?'}, desde a linha {sf['linha_inicio']}; rounds "
                       f"{res['current']['rounds']})")
        else:
            # Todas terminaram em MAP ENDED e ainda há rounds: o arquivamento
            # falhou ou houve colisão.
            ruim.append(rounds)
    if res["entradas"]["db"] is None:
        sem.append("sem --db")
    sha = res["sha"]
    if sha is None or not sha["conferidos"]:
        sem.append("sha montados não conferidos (--sha-montados e --sha-referencia)")
    else:
        if sha["divergentes"]:
            invalida(f"sha montado divergente: {', '.join(sha['divergentes'])}")
        if sha["so_na_referencia"]:
            invalida(f"sha não conferido no container: {', '.join(sha['so_na_referencia'])}")
        faltam = [n for n in SHA_DO_PROTOCOLO
                  if n not in sha["conferidos"] and n not in sha["so_na_referencia"]]
        if faltam:
            sem.append(f"sha sem os arquivos do protocolo §3: {', '.join(faltam)}")
    ch = res["config_hash"]
    if not (ch["agora"] and ch["janela"]):
        sem.append("config-hash não conferido (--config-hash e --config-hash-janela)")
    elif ch["agora"] != ch["janela"]:
        invalida("config-hash diferente do da janela")
    g7 = SEM if invalidam else RUIM if ruim else SEM if sem else OK
    return {"g7": g7, "ruim": ruim, "sem_evidencia": sem, "invalidam": invalidam}


# ------------------------------------------------------------------ texto

def _lista(itens, vazio="nenhum"):
    return ", ".join(itens) if itens else vazio


def formatar(res: dict) -> str:
    s = []
    e = res["entradas"]
    intacto = {True: "sim", False: "NÃO", None: "-"}[e.get("banco_intacto")]
    s.append("Evidência de partida (card H1.1), só leitura")
    s.append(f"Entradas: log={e['log']} · eventos={e['eventos']} · banco={e['db']} "
             f"(mode=ro; mtime intacto: {intacto})")
    if log := res["log"]:
        c = log["crash"]
        s += ["", "== Servidor (log) ==",
              f"Linhas: {log['linhas']} · carimbo: {log['carimbo']}"]
        if log.get("timeline_live_watch"):
            s.append("Aviso: a timeline do live_watch não guarda crash, overflow, SIGNONSTATE "
                     "nem a carga da captura; as contagens abaixo não valem (use docker logs -t)")
        s.append(f"Crash: segfault {c['segfault']} · Stack overflow {c['stack_overflow']} · "
                 f"core dumped {c['core_dumped']} · FATAL ERROR {c['fatal_motor']}")
        s += [f"  linha {x['linha']}: {x['texto']}" for x in log["crash_linhas"][:5]]
        s.append("Fatal error de plugin: " + _lista(
            [f"{f['plugin']} (linha {f['linha']})" for f in log["fatal_plugin"]]))
        s.append("Assinaturas que falharam, por plugin:"
                 + ("" if log["assinaturas"] else " nenhuma"))
        for plugin, nomes in log["assinaturas"].items():
            s.append(f"  {plugin}: " + ", ".join(f"{n} ({q}x)" for n, q in nomes.items()))
        s.append("Plugins recusados: " + _lista(log["recusados"]))
        s.append("Plugins carregados: " + _lista(
            [f"{k} {v}" for k, v in log["carregados"].items()], "nenhuma linha de carga")
            + f" · boots da MatchZy: {log['boots_matchzy']}")
        v = log["versoes"]
        s.append(f"Metamod {v.get('metamod', '?')} · CSSharp {v.get('cssharp', '?')} · "
                 f"build {_lista(log['builds'], '?')}")
        ov = log["overflow"]
        t = ov["total"]
        s.append(f"Overflow: {len(ov['episodios'])} episódio(s) · signon {t.get('signon', 0)} · "
                 f"em jogo {t.get('em_jogo', 0)} · sem carimbo {t.get('sem_carimbo', 0)}")
        for epi in ov["episodios"]:
            quando = ("" if epi["segundos_apos_full"] is None
                      else f", {epi['segundos_apos_full']} s após FULL")
            s.append(f"  linha {epi['linha']} ({epi['classe']}{quando}; {epi['linhas']} "
                     f"linha(s); {epi['partida'] or 'fora de partida'}): {epi['texto']}")
        for dn, q in ov["por_partida"].items():
            s.append(f"  por partida: {dn}: " + ", ".join(f"{k} {n}" for k, n in sorted(q.items())))
        if sf := log["partida_sem_fim"]:
            s.append(f"Partida sem fim no log: {sf['mapa']} desde a linha {sf['linha_inicio']}")
    s += ["", "== Partidas julgadas =="]
    for p in res["partidas"] or []:
        s.append(f"{p['demo_name']} · mapa do log {p.get('mapa') or '?'} · "
                 f"demo {p.get('inicio_demo') or '?'}")
        b = p["banco"]
        placar = f"{b['score_mine']}x{b['score_theirs']}" if b else "-"
        s.append(f"  arquivado: {_sn(p['arquivado'])} · ingerida: {_sn(p['ingerida'])}"
                 + (f" (id {b['id']}, mapa {b['map']}, placar {placar})" if b else "")
                 + f" · 5x5: {_sn(p['times_5x5'])}")
        if g := p["granadas_bot"]:
            m = g["motor"]
            motor = (f"motor {m['utility']} utility + {m['flash']} flash até o round "
                     f"{m['ate_round']}" if m else "motor -")
            s.append(f"  granadas de bot ({g['bots']} bots): {motor} · dano de granada "
                     f"{g['dano_de_granada']} · cegueiras {g['cegueiras']}")
        s.append("  colisão: " + _lista(p["colisoes"], "nenhuma"))
    if not res["partidas"]:
        s.append("nenhuma")
    if cur := res.get("current"):
        tipos = ", ".join(f"{k} {v}" for k, v in sorted((cur.get("tipos") or {}).items()))
        detalhe = f" ({tipos}; rounds {cur['rounds']})" if tipos else ""
        s += ["", f"current.jsonl: {cur['estado']}{detalhe}"]
    if ac := res.get("acervo"):
        placar = [f"{k} ({v})" for k, v in ac["placar_fora_do_mr12"].items()]
        divergente = [f"{k} -> {v}" for k, v in ac["demo_path_divergente"].items()]
        s += ["", "== Acervo (fora do veredito) ==",
              "JSONL arquivado sem linha no banco: " + _lista(ac["sem_linha_no_banco"]),
              "Mapa NULL: " + _lista(ac["mapa_null"]),
              "Placar fora do MR12: " + _lista(placar),
              "demo_path divergente: " + _lista(divergente)]
    sha, ch = res["sha"], res["config_hash"]
    s += ["", "== sha montados e config-hash =="]
    if sha:
        s.append(f"conferidos {len(sha['conferidos'])} · divergentes: {_lista(sha['divergentes'])}"
                 f" · só no container: {_lista(sha['so_no_container'])}"
                 f" · só na referência: {_lista(sha['so_na_referencia'])}")
    else:
        s.append("sha: não informado")
    s.append(f"config-hash: agora {ch['agora'] or '-'} · janela {ch['janela'] or '-'}")
    v = res["veredito"]
    anulado = v["g7"] == SEM and bool(v["ruim"])
    s.append("")
    s += [f"  RUIM{' (anulado: evidência inválida)' if anulado else ''}: {m}" for m in v["ruim"]]
    s += [f"  sem evidência{' (invalida)' if m in v['invalidam'] else ''}: {m}"
          for m in v["sem_evidencia"]]
    # A linha final traz os motivos que decidiram: os que invalidam a
    # evidência, os de RUIM, ou os de sem evidência.
    if anulado:
        motivos = v["invalidam"] + ["RUIM anulado: " + "; ".join(v["ruim"])]
    else:
        motivos = v["ruim"] or v["sem_evidencia"]
    s.append(f"VEREDITO G7: {v['g7']}" + (" — " + "; ".join(motivos) if motivos else ""))
    return "\n".join(s)


def _sn(valor):
    return {True: "sim", False: "NÃO", None: "-"}[valor]


def _erro(mensagem: str):
    try:
        print(mensagem, file=sys.stderr)
    except UnicodeEncodeError:
        print(ascii(mensagem), file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Evidência de partida para o G7 (card H1.1), só leitura.")
    ap.add_argument("--log", help="docker logs -t salvos desde o StartedAt")
    ap.add_argument("--eventos", help="cópia da pasta com events_*_map*.jsonl e current.jsonl")
    ap.add_argument("--db", help="cópia mode=ro do banco pedida ao PM (o real é recusado)")
    ap.add_argument("--partida", action="append", default=[], metavar="DEMO_NAME")
    ap.add_argument("--sha-montados", help="sha256sum de dentro do container")
    ap.add_argument("--sha-referencia", help="sha256sum do checkout ou da janela")
    ap.add_argument("--config-hash")
    ap.add_argument("--config-hash-janela")
    ap.add_argument("--assinatura-proibida", action="append", default=[], metavar="NOME")
    ap.add_argument("--fatal-esperado", action="append", default=[], metavar="PLUGIN")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args(argv)
    if not (args.log or args.eventos or args.db or args.partida):
        ap.error("informe ao menos --log, --eventos, --db ou --partida")
    try:
        for caminho in (args.log, args.sha_montados, args.sha_referencia):
            if caminho and not Path(caminho).is_file():
                raise Recusa(f"arquivo não encontrado: {caminho}")
        res = avaliar(
            log=args.log, eventos=args.eventos, db=args.db, partidas=args.partida,
            sha_montados=args.sha_montados, sha_referencia=args.sha_referencia,
            config_hash=args.config_hash, config_hash_janela=args.config_hash_janela,
            assinaturas_proibidas=args.assinatura_proibida,
            fatais_esperados=args.fatal_esperado)
        texto = json.dumps(res, ensure_ascii=False, indent=1) if args.json else formatar(res)
    except Recusa as exc:
        _erro(f"recusado: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001 - erro interno não pode virar RUIM (código 1)
        _erro(f"erro: {type(exc).__name__}: {exc} (sem veredito)")
        return ERRO_INTERNO
    try:
        # Mesmo cuidado do preflight: em pipe o padrão seria cp1252.
        if sys.stdout.isatty():
            sys.stdout.reconfigure(errors="replace")
        else:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    print(texto)
    return CODIGO[res["veredito"]["g7"]]


if __name__ == "__main__":
    sys.exit(main())
