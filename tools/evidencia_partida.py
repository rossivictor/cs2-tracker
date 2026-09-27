#!/usr/bin/env python3
"""
Evidência de partida (card H1.1): cruza o que o servidor logou, o que a
captura arquivou e o que o banco guardou, e diz se a partida serve de
evidência para o G7 (plano, protocolo de jogabilidade §6, "evidência de
carona"; runbook do B1.3r, "Depois da janela").

Só leitura e só biblioteca padrão. Todas as entradas são explícitas:

  --log ARQ       docker logs salvos desde o StartedAt, de preferência com
                  `docker logs -t` (sem carimbo não dá para separar overflow
                  de signon de overflow em jogo). Também lê a timeline do
                  tools/live_watch.py, onde só as linhas [docker] contam.
  --eventos DIR   cópia da pasta de captura: events_<matchid>_map<N>.jsonl
                  arquivados e current.jsonl.
  --db ARQ        banco SQLite, aberto com mode=ro e sem padrão. O banco real
                  do checkout principal é recusado sem --leitura-banco-real, e
                  mesmo com ele abre só leitura; o relatório diz se o mtime
                  ficou intacto.
  --sha-montados, --sha-referencia   saídas de sha256sum (dentro do container
                  e do checkout ou do registro da janela), casadas pelo nome.
  --config-hash, --config-hash-janela   o config-hash de agora e o da janela.
  --partida DEMO  julga só esta partida (repetível). Sem ela, julga as que
                  terminaram no log ("MAP ENDED").
  --assinatura-proibida NOME, --fatal-esperado PLUGIN   critérios do card.

Veredito, na última linha:
  RUIM           crash (Segmentation fault, Stack overflow, core dumped,
                 FATAL ERROR, MatchZy carregada de novo = processo que
                 reiniciou), Fatal error de plugin não esperado, overflow
                 depois de SIGNONSTATE_FULL + 60 s, assinatura proibida, mapa
                 NULL, placar fora do MR12, times fora de 5x5, colisão de
                 demo_name, current.jsonl com rounds não arquivados;
  SEM EVIDÊNCIA  falta entrada, nenhuma partida terminou, partida não
                 arquivada ou não ingerida, log sem as linhas de carga, build
                 que mudou no meio, overflow sem carimbo, sha montado ou
                 config-hash divergente (ou não conferido);
  OK             nenhum dos dois.
RUIM vence SEM EVIDÊNCIA. O que o acervo mostra fora das partidas julgadas
(JSONL antigo sem linha no banco, por exemplo) é informativo.

Saída: 0 OK, 1 RUIM, 3 SEM EVIDÊNCIA, 2 uso errado ou recusa.
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

BANCO_REAL = Path("C:/Users/Victor/Projetos/cs2-tracker/cs2_tracker.db")
OK, RUIM, SEM = "OK", "RUIM", "SEM EVIDÊNCIA"
CODIGO = {OK: 0, RUIM: 1, SEM: 3}
SEGUNDOS_SIGNON = 60
# mp_overtime_limit em server-configs/cfg/gamemode_competitive_server.cfg.
LIMITE_PRORROGACOES = 3
# Depois do arquivamento o plugin ainda escreve isto no current.jsonl: é normal.
TIPOS_DA_CAUDA = frozenset({"snapshot", "round_stats", "round_officially_ended"})
GRANADAS = frozenset({"hegrenade", "inferno", "molotov", "incgrenade"})
# Linhas de overflow mais próximas que isto são o mesmo episódio.
EPISODIO_S, EPISODIO_LINHAS = 5.0, 20


class Recusa(Exception):
    """Entrada que a ferramenta não lê (banco real sem a flag, arquivo ausente)."""


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


def ler_linhas(texto: str):
    """([(número, segundos ou None, texto sem prefixo)], formato do carimbo).

    Linha sem carimbo próprio herda o último visto (o log é cronológico). Na
    timeline do live_watch as linhas [evento], [placar] e [setup] não são do
    servidor e ficam de fora."""
    linhas, formatos = [], set()
    base = ultimo = hora_anterior = None
    dia = 0
    for n, bruta in enumerate(texto.splitlines(), 1):
        bruta = bruta.rstrip()
        if not bruta:
            continue
        if m := _T_SESSAO.match(bruta):
            try:
                base = datetime.fromisoformat(m.group(1)).timestamp()
            except ValueError:
                base = None
            continue
        t, corpo = None, bruta
        if m := _T_DOCKER.match(bruta):
            micro = int((m.group(2) or "0")[:6].ljust(6, "0"))
            inicio = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
            t, corpo = inicio.timestamp() + micro / 1e6, m.group(3)
            formatos.add("docker -t")
        elif m := _T_LIVE.match(bruta):
            if m.group(2) != "docker":
                continue
            t, corpo = (base or 0.0) + float(m.group(1)), m.group(3)
            formatos.add("live_watch")
        elif m := _T_L.match(bruta):
            t = datetime.strptime(m.group(1), "%m/%d/%Y - %H:%M:%S").timestamp()
            corpo = m.group(2)
            formatos.add("L")
        elif m := _T_HORA.match(bruta):
            s = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            if hora_anterior is not None and s < hora_anterior - 43200:
                dia += 1   # passou da meia-noite
            hora_anterior = s
            t, corpo = dia * 86400 + s, m.group(4)
            formatos.add("hora")
        if t is None:
            t = ultimo
        else:
            ultimo = t
        linhas.append((n, t, corpo))
    return linhas, " + ".join(sorted(formatos)) or "sem carimbo"


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
    linhas, formato = ler_linhas(texto)
    crash = {chave: 0 for chave, _, _ in _CRASH}
    crash_linhas, fatal_plugin, recusados, builds = [], [], [], []
    assinaturas: dict[str, Counter] = {}
    carregados, versoes = {}, {}
    boots = prontos = 0
    sinais, overflows, partidas = [], [], []
    trecho = _novo_trecho(1)
    for n, t, corpo in linhas:
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
                "linha_inicio": trecho["inicio"], "linha_fim": n,
            })
            trecho = _novo_trecho(n + 1)
    sem_fim = None
    if trecho["live"] or trecho["demo"]:
        sem_fim = {"mapa": trecho["mapa_demo"] or trecho["mapa"], "inicio_demo": trecho["demo"],
                   "linha_inicio": trecho["inicio"]}
    nomes = Counter(p["demo_name"] for p in partidas)
    return {
        "linhas": len(linhas), "carimbo": formato, "crash": crash, "crash_linhas": crash_linhas,
        "fatal_plugin": fatal_plugin,
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
    episodios = []
    for n, t, corpo in overflows:
        ult = episodios[-1] if episodios else None
        if ult is not None:
            perto = (t - ult["_t"] <= EPISODIO_S) if (t is not None and ult["_t"] is not None) \
                else (n - ult["_n"] <= EPISODIO_LINHAS)
            # Um FULL no meio é reconexão: o overflow seguinte é outro episódio.
            reconectou = any(ult["_n"] < ns < n for ns, _, tipo in sinais if tipo == "full")
            if perto and not reconectou:
                ult["_t"], ult["_n"] = t, n
                ult["linhas"] += 1
                continue
        classe, delta = _classe(n, t, sinais)
        episodios.append({"linha": n, "classe": classe, "segundos_apos_full": delta,
                          "partida": _dono(n, partidas, sem_fim), "texto": corpo[:160],
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

_ARQUIVADO = re.compile(r"^events_(\d+)_map(\d+)\.jsonl$")


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
    return {p.stem: p for p in sorted(pasta.iterdir()) if _ARQUIVADO.match(p.name)}


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
    tipos = Counter(e.get("type") for e in eventos)
    fora = [e for e in eventos if e.get("type") not in TIPOS_DA_CAUDA]
    rounds = {e.get("round_num") for e in (fora or eventos)}
    return {"estado": "com_rounds" if fora else "cauda_normal", "tipos": dict(tipos),
            "rounds": sorted(r for r in rounds if isinstance(r, int)), "linhas_ruins": ruins}


def times(eventos) -> tuple:
    """(True/False/None, {round: (ct, t)} fora de 5x5). Vem do round_stats ou,
    sem ele, do freeze_end. Só lado ct/t conta: o bot do GOTV não tem lado."""
    por_round = {}
    for tipo in ("round_stats", "freeze_end"):
        for e in eventos:
            if e.get("type") == tipo:
                lados = Counter(p.get("side") for p in e.get("players") or [])
                por_round[e.get("round_num")] = (lados.get("ct", 0), lados.get("t", 0))
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
        for p in e.get("players") or []:
            nome, bot = p.get("name", p.get("n")), p.get("is_bot", p.get("b"))
            # Sem lado ct/t é o bot do GOTV, que não joga.
            if nome is not None and bot is not None and p.get("side", p.get("s")) in ("ct", "t"):
                (bots if bot else humanos).add(nome)
    bots -= humanos
    if not bots:
        return None
    dano = sum(1 for e in eventos if e.get("type") == "player_hurt"
               and e.get("weapon") in GRANADAS and e.get("attacker_name") in bots)
    cegueiras = sum(1 for e in eventos if e.get("type") == "player_blind"
                    and e.get("attacker_name") in bots)
    stats = [e for e in eventos if e.get("type") == "round_stats"]
    motor = None
    if stats:
        ultimo = max(stats, key=lambda e: e.get("round_num") or 0)
        jog = [p for p in ultimo.get("players") or []
               if p.get("is_bot") and p.get("side") in ("ct", "t")]
        motor = {"utility": sum(int(p.get("utility_count") or 0) for p in jog),
                 "flash": sum(int(p.get("flash_count") or 0) for p in jog),
                 "ate_round": ultimo.get("round_num")}
    return {"bots": len(bots), "dano_de_granada": dano, "cegueiras": cegueiras, "motor": motor}


# ------------------------------------------------------------------ banco

def _mesmo_arquivo(a, b) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _checar_banco(caminho: Path, permitir_real: bool):
    if not caminho.is_file():
        raise Recusa(f"banco não encontrado: {caminho}")
    if _mesmo_arquivo(caminho, BANCO_REAL) and not permitir_real:
        raise Recusa("é o banco real do checkout principal; use uma cópia mode=ro pedida "
                     "ao PM, ou passe --leitura-banco-real (abre só leitura)")


def abrir_banco(caminho, permitir_real=False) -> sqlite3.Connection:
    """Conexão mode=ro + query_only. O banco real só com a flag explícita."""
    caminho = Path(caminho)
    _checar_banco(caminho, permitir_real)
    conn = sqlite3.connect(caminho.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = 1")
    conn.row_factory = sqlite3.Row
    return conn


def ler_matches(caminho, permitir_real=False) -> tuple:
    """({demo_name: linha}, intacto): lê a tabela matches e confere que o
    mtime e o tamanho do arquivo não mudaram."""
    _checar_banco(Path(caminho), permitir_real)
    antes = os.stat(caminho)
    conn = abrir_banco(caminho, permitir_real)
    try:
        linhas = {r["demo_name"]: dict(r) for r in conn.execute("SELECT * FROM matches")}
    except sqlite3.Error as exc:
        raise Recusa(f"banco sem tabela matches legível: {exc}") from exc
    finally:
        conn.close()
    depois = os.stat(caminho)
    intacto = (antes.st_mtime_ns, antes.st_size) == (depois.st_mtime_ns, depois.st_size)
    return linhas, intacto


def motivo_placar(a, b):
    """None se a x b fecha MR12 com prorrogação MR3 (até LIMITE_PRORROGACOES,
    e empate depois dela); senão, o motivo."""
    if a is None or b is None:
        return "placar vazio"
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
    if jogada and inicio and jogada < inicio - timedelta(days=1):
        motivos.append(f"linha do banco é de {jogada:%Y-%m-%d}, antes da partida do log "
                       f"({inicio:%Y-%m-%d})")
    return motivos


def acervo(linhas: dict, arquivos) -> dict:
    """O que está errado no banco e na pasta, fora das partidas julgadas."""
    placar = {}
    for dn, r in linhas.items():
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
    comuns = sorted(set(montados) & set(referencia))
    return {"conferidos": comuns,
            "divergentes": [n for n in comuns if montados[n] != referencia[n]],
            "so_no_container": sorted(set(montados) - set(referencia)),
            "so_na_referencia": sorted(set(referencia) - set(montados))}


# ------------------------------------------------------------------ juntar

def avaliar(log=None, eventos=None, db=None, partidas=(), sha_montados=None,
            sha_referencia=None, config_hash=None, config_hash_janela=None,
            assinaturas_proibidas=(), fatais_esperados=(), leitura_banco_real=False) -> dict:
    res = {"entradas": {"log": log and str(log), "eventos": eventos and str(eventos),
                        "db": db and str(db)}}
    res["log"] = analisar_log(ler_texto(log)) if log else None
    linhas = arquivos = None
    if eventos:
        pasta = Path(eventos)
        if not pasta.is_dir():
            raise Recusa(f"pasta de eventos não encontrada: {pasta}")
        arquivos = arquivados(pasta)
        res["current"] = analisar_current(pasta)
    if db:
        linhas, res["entradas"]["banco_intacto"] = ler_matches(db, leitura_banco_real)
        res["acervo"] = acervo(linhas, arquivos)
    res["sha"] = (comparar_sha(ler_sha(sha_montados), ler_sha(sha_referencia))
                  if sha_montados and sha_referencia else None)
    res["config_hash"] = {"agora": config_hash, "janela": config_hash_janela}

    do_log = {p["demo_name"]: p for p in (res["log"] or {}).get("partidas", [])}
    nomes = list(partidas) or list(do_log)
    repetidos = (res["log"] or {}).get("repetidos", [])
    julgadas = []
    for dn in dict.fromkeys(nomes):
        p = dict(do_log.get(dn) or {"demo_name": dn, "mapa": None, "inicio_demo": None})
        linha = (linhas or {}).get(dn)
        p["arquivado"] = None if arquivos is None else dn in arquivos
        p["ingerida"] = None if linhas is None else linha is not None
        p["banco"] = linha and {k: linha.get(k) for k in (
            "id", "map", "played_at", "score_mine", "score_theirs", "score_ct", "score_t",
            "demo_path")}
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
    ruim, sem = [], []
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
            sem.append(f"build mudou no log ({' -> '.join(log['builds'])}): 2 variáveis")
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
            if motivo := motivo_placar(b["score_mine"], b["score_theirs"]):
                ruim.append(f"{dn}: placar {motivo}")
            elif None not in (b["score_ct"], b["score_t"]) and \
                    b["score_ct"] + b["score_t"] != b["score_mine"] + b["score_theirs"]:
                ruim.append(f"{dn}: placar por lado ({b['score_ct']}+{b['score_t']}) não soma "
                            f"o placar da partida ({b['score_mine']}+{b['score_theirs']})")
        if p["times_5x5"] is False:
            ruim.append(f"{dn}: times fora de 5x5 nos rounds {sorted(p['fora_de_5x5'])}")
        elif p["arquivado"] and p["times_5x5"] is None:
            sem.append(f"{dn}: JSONL sem round_stats nem freeze_end para conferir o 5x5")
        for c in p["colisoes"]:
            ruim.append(f"{dn}: colisão: {c}")
    if res["entradas"]["eventos"] is None:
        sem.append("sem --eventos")
    elif res["current"]["estado"] == "com_rounds":
        ruim.append(f"current.jsonl com rounds não arquivados (rounds {res['current']['rounds']})")
    if res["entradas"]["db"] is None:
        sem.append("sem --db")
    sha = res["sha"]
    if sha is None or not sha["conferidos"]:
        sem.append("sha montados não conferidos (--sha-montados e --sha-referencia)")
    elif sha["divergentes"]:
        sem.append(f"sha montado divergente: {', '.join(sha['divergentes'])}")
    ch = res["config_hash"]
    if ch["agora"] and ch["janela"] and ch["agora"] != ch["janela"]:
        sem.append("config-hash diferente do da janela")
    g7 = RUIM if ruim else SEM if sem else OK
    return {"g7": g7, "ruim": ruim, "sem_evidencia": sem}


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
              f"Linhas: {log['linhas']} · carimbo: {log['carimbo']}",
              f"Crash: segfault {c['segfault']} · Stack overflow {c['stack_overflow']} · "
              f"core dumped {c['core_dumped']} · FATAL ERROR {c['fatal_motor']}"]
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
            s.append(f"  linha {epi['linha']} ({epi['classe']}{quando}; "
                     f"{epi['partida'] or 'fora de partida'}): {epi['texto']}")
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
    s.append("")
    s += [f"  RUIM: {m}" for m in v["ruim"]]
    s += [f"  sem evidência: {m}" for m in v["sem_evidencia"]]
    # A linha final traz os motivos que decidiram: os de RUIM, se houver.
    motivos = v["ruim"] or v["sem_evidencia"]
    s.append(f"VEREDITO G7: {v['g7']}" + (" — " + "; ".join(motivos) if motivos else ""))
    return "\n".join(s)


def _sn(valor):
    return {True: "sim", False: "NÃO", None: "-"}[valor]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Evidência de partida para o G7 (card H1.1), só leitura.")
    ap.add_argument("--log", help="docker logs salvos (de preferência com -t)")
    ap.add_argument("--eventos", help="pasta com events_*_map*.jsonl e current.jsonl")
    ap.add_argument("--db", help="banco SQLite (cópia); aberto com mode=ro")
    ap.add_argument("--leitura-banco-real", action="store_true",
                    help="aceita o banco real do checkout principal, ainda só leitura")
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
            fatais_esperados=args.fatal_esperado, leitura_banco_real=args.leitura_banco_real)
    except Recusa as exc:
        print(f"recusado: {exc}", file=sys.stderr)
        return 2
    try:
        # Mesmo cuidado do preflight: em pipe o padrão seria cp1252.
        if sys.stdout.isatty():
            sys.stdout.reconfigure(errors="replace")
        else:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    print(json.dumps(res, ensure_ascii=False, indent=1) if args.json else formatar(res))
    return CODIGO[res["veredito"]["g7"]]


if __name__ == "__main__":
    sys.exit(main())
