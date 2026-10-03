#!/usr/bin/env python3
"""
Fixtures anonimizadas da captura (card T1.3), geradas por script para dar
para refazer. A origem são SÓ as cópias em C:/Users/Victor/cs2-tracker-backups/
(nunca a docker/events-live do checkout principal nem o banco real); outra
origem é recusada. Nada de valor real é impresso: só contagens.

Saem em tests/fixtures/captura/:
  events_44_map0.jsonl  o mapa inteiro, com o BOM que o plugin escreve;
  events_59_map0.jsonl  reduzido: todo evento menos `snapshot` (todos os
                        rounds, com kills, dano, flash, compras e round_stats)
                        e o primeiro snapshot de cada round; o snapshot (2 Hz)
                        é 91% do arquivo e só alimenta o trajeto;
  current.jsonl         a cauda pós-partida inteira da cópia de 03/10;
  serie_bo3.log         as linhas do docker da timeline do live_watch da série
                        45 (MD3), em `docker logs -t`: início da sessão (UTC-3,
                        levado a UTC) mais o segundo da linha. Saem o spam
                        "Long frame", stack trace com ANSI, linha com senha ou
                        token e as linhas do próprio live_watch.

Troca, consistente entre os arquivos: SteamID64 do humano -> 76561190000000001,
os demais 76561190000000002 em diante (abaixo da base: não existe conta); nome
do humano -> "Jogador", os outros -> alfabeto fonético; SteamID3 -> [U:1:0] e
IPv4 -> 127.0.0.1, os únicos que o tools/hooks/pii.py libera em tests/fixtures/
(ele barra até os blocos de documentação); STEAM_x:y:z -> STEAM_1:0:0. Se o
pii.achar ou a busca dos valores originais achar algo, nada é gravado.

Uso: python tools/anonimizar_fixtures.py [--eventos DIR] [--log ARQ] [--destino DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools" / "hooks"))
import pii  # noqa: E402

BACKUPS = Path("C:/Users/Victor/cs2-tracker-backups")
EVENTOS = BACKUPS / "2026-10-03" / "g7-b0.8-copia" / "docker" / "events-live"
LOG = BACKUPS / "2026-09-26" / "repo-local" / "logs" / "teste-correcao.log"
DESTINO = RAIZ / "tests" / "fixtures" / "captura"

BOM = "\ufeff"
HUMANO_NOME = "Jogador"
PRIMEIRO_ID = 76561190000000001
NOMES = ("Alfa", "Bravo", "Charlie", "Delta", "Eco", "Foxtrot", "Golfe", "Hotel", "India",
         "Julieta", "Kilo", "Lima", "Mike", "Novembro", "Oscar", "Papa", "Quebec", "Romeu",
         "Sierra", "Tango", "Uniforme", "Whiskey", "Xray", "Yankee", "Zulu")
CAMPOS_NOME = {"attacker_name", "victim_name", "player_name", "name", "n"}
# Aparecem onde cabe nome de jogador, mas não são gente.
NAO_JOGADOR = {"Bots", "Console", "CS2 Tracker - Spike MatchZy CSTV"}
FUSO_LIVE_WATCH = timedelta(hours=-3)

_ID64 = re.compile(r"(?<!\d)7656119\d{10}(?!\d)")
_STEAM2 = re.compile(r"STEAM_\d:\d:\d+")
_LINHA_LW = re.compile(r"^\[\s*([\d.]+)s\] \[(\w+)\s*\] (?:\((\w+)\) )?(.*)$")
_INICIO_LW = re.compile(r"sess\S+ iniciada (\S+) =")
_SEGREDO = re.compile(r"password|token|steamaccount|gslt", re.IGNORECASE)
# Onde a MatchZy e o live_watch põem nome de jogador.
_NOMES_LOG = (
    re.compile(r'"([^"<]+)<\d+><[^>]*>(?:<[^>]*>)?"'),
    re.compile(r"Name: (.+?) has connected!"),
    re.compile(r"round \d+: (.*?) matou (.*?) \(\w+\)$"),
    re.compile(r"MatchZy \| (.+?) vs (.+?)$"),
    re.compile(r"winnerName: (.+?)\s*$"),
    re.compile(r"_(?:de|cs)_[a-z0-9]+_(.+?)_vs_(.+?)\.dem"),
    re.compile(r"client '([^']+)'"),
)


class Anonimizador:
    def __init__(self, humano_id: str, humanos: set):
        self.ids = {humano_id: str(PRIMEIRO_ID)}
        self.nomes = {n: HUMANO_NOME for n in humanos}

    def id64(self, valor: str) -> str:
        return self.ids.setdefault(valor, str(PRIMEIRO_ID + len(self.ids)))

    def nome(self, valor: str) -> str:
        if not valor or valor in NAO_JOGADOR:
            return valor
        if valor not in self.nomes:
            i = len(set(self.nomes.values()) - {HUMANO_NOME})
            self.nomes[valor] = NOMES[i % len(NOMES)] + ("" if i < len(NOMES) else str(i // len(NOMES) + 1))
        return self.nomes[valor]

    def evento(self, obj, chave=None):
        if isinstance(obj, dict):
            return {k: self.evento(v, k) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.evento(v, chave) for v in obj]
        if isinstance(obj, str):
            if _ID64.fullmatch(obj):
                return self.id64(obj)
            if chave in CAMPOS_NOME:
                return self.nome(obj)
        return obj

    def texto(self, linha: str) -> str:
        """Troca nomes conhecidos (uma passada só, o mais longo primeiro, para
        um nome trocado não ser trocado de novo), ids, SteamID3, STEAM_ e IP."""
        reais = sorted((n for n in self.nomes if n), key=len, reverse=True)
        if reais:
            alt = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, reais)) + r")(?![A-Za-z0-9])")
            linha = alt.sub(lambda m: self.nomes[m.group(1)], linha)
        linha = _ID64.sub(lambda m: self.id64(m.group(0)), linha)
        linha = pii._STEAMID3.sub("[U:1:0]", linha)
        linha = _STEAM2.sub("STEAM_1:0:0", linha)
        return pii._IPV4.sub(lambda m: m.group(0) if (m.group(0) in pii.IPS_LIBERADOS
                                                      or pii._versao(linha, m.start())) else "127.0.0.1", linha)


def _ler_jsonl(caminho: Path) -> list:
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def _humano(eventos: list) -> tuple:
    """(SteamID64 mais frequente, nomes que andam com ele ou com is_bot falso)."""
    ids = Counter()
    for e in eventos:
        for p in ("attacker_", "victim_", ""):
            if e.get(p + "steamid"):
                ids[str(e[p + "steamid"])] += 1
    humano = ids.most_common(1)[0][0]
    nomes = set()
    for e in eventos:
        for p, campo in (("attacker_", "attacker_name"), ("victim_", "victim_name"), ("", "player_name")):
            if str(e.get(p + "steamid")) == humano and e.get(campo):
                nomes.add(e[campo])
        for j in e.get("players") or []:
            if j.get("b", j.get("is_bot")) is False:
                nomes.add(j.get("n") or j.get("name"))
    return humano, nomes


def _nomes_do_log(linhas: list) -> tuple:
    humanos, outros = set(), set()
    for l in linhas:
        for rx in _NOMES_LOG:
            for m in rx.finditer(l):
                (humanos if "has connected" in rx.pattern else outros).update(g for g in m.groups() if g)
    return humanos, outros - humanos


def _jsonl(eventos: list, anon: Anonimizador, bom: bool = False) -> str:
    corpo = "".join(json.dumps(anon.evento(e), separators=(",", ":"), ensure_ascii=False) + "\n"
                    for e in eventos)
    return (BOM if bom else "") + corpo


def _reduzir_59(eventos: list) -> list:
    vistos = set()
    saida = []
    for e in eventos:
        if e.get("type") == "snapshot":
            if e.get("round_num") in vistos:
                continue
            vistos.add(e.get("round_num"))
        saida.append(e)
    return saida


def _serie_bo3(texto: str, anon: Anonimizador, descartes: Counter) -> str:
    linhas = texto.splitlines()
    inicio = datetime.fromisoformat(_INICIO_LW.search(texto).group(1)) - FUSO_LIVE_WATCH
    saida = []
    for l in linhas:
        m = _LINHA_LW.match(l)
        if not m or m.group(2) != "docker":
            descartes["fora do docker"] += 1
            continue
        conteudo = m.group(4)
        motivo = ("Long frame" if " Long frame (" in f" {conteudo}" else
                  "stack trace" if "\x1b" in conteudo or conteudo.lstrip().startswith("at ") else
                  "senha/token" if _SEGREDO.search(conteudo) else None)
        if motivo:
            descartes[motivo] += 1
            continue
        t = inicio + timedelta(seconds=float(m.group(1)))
        saida.append(f"{t:%Y-%m-%dT%H:%M:%S}.{t.microsecond:06d}000Z {anon.texto(conteudo)}\n")
    return "".join(saida)


def _origem_ok(caminho: Path) -> Path:
    caminho = caminho.resolve()
    if BACKUPS.resolve() not in caminho.parents:
        sys.exit(f"origem fora de {BACKUPS}: recusada (AGENTS.md, zonas proibidas)")
    return caminho


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--eventos", type=Path, default=EVENTOS)
    ap.add_argument("--log", type=Path, default=LOG)
    ap.add_argument("--destino", type=Path, default=DESTINO)
    args = ap.parse_args(argv)
    eventos, log = _origem_ok(args.eventos), _origem_ok(args.log)

    e44 = _ler_jsonl(eventos / "events_44_map0.jsonl")
    e59 = _ler_jsonl(eventos / "events_59_map0.jsonl")
    cur = _ler_jsonl(eventos / "current.jsonl")
    serie = [e for n in ("events_45_map0.jsonl", "events_45_map2.jsonl") for e in _ler_jsonl(eventos / n)]
    texto_log = log.read_text(encoding="utf-8")
    humano, humanos = _humano(e44 + e59 + cur + serie)
    log_humanos, log_outros = _nomes_do_log(texto_log.splitlines())
    anon = Anonimizador(humano, humanos | log_humanos)

    descartes = Counter()
    saidas = {
        "events_44_map0.jsonl": _jsonl(e44, anon, bom=True),
        "events_59_map0.jsonl": _jsonl(_reduzir_59(e59), anon),
        "current.jsonl": _jsonl(cur, anon),
    }
    for e in serie:  # nomes dos bots da série entram no mapa antes do log
        anon.evento(e)
    for n in sorted(log_outros):
        anon.nome(n)
    saidas["serie_bo3.log"] = _serie_bo3(texto_log, anon, descartes)

    reais = [n for n in anon.nomes if n and n not in set(anon.nomes.values())]
    for nome, conteudo in saidas.items():
        achados = pii.achar(conteudo)
        sobras = sum(1 for n in reais if re.search(
            r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])", conteudo))
        sobras += sum(1 for i in anon.ids if i in conteudo)
        if achados or sobras:
            print(f"{nome}: pii {achados}, {sobras} valor(es) original(is) sobrando; nada gravado")
            return 1
    args.destino.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in saidas.items():
        (args.destino / nome).write_bytes(conteudo.encode("utf-8"))
        print(f"{nome}: {conteudo.count(chr(10))} linhas, {len(conteudo.encode('utf-8'))} bytes")
    print(f"SteamID64 trocados: {len(anon.ids)} (humano -> {PRIMEIRO_ID}, demais em sequência); "
          f"nomes trocados: {len(reais)}; descartes do log: {dict(descartes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
