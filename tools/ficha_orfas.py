#!/usr/bin/env python3
"""
Ficha das partidas órfãs, feita só em cópias (card V1.2).

Órfã é o .jsonl de eventos que não tem linha em `matches`: o
events_<matchid>_map<N>[__<utc>].jsonl que o watcher arquivou e não entrou
no banco, e o orphan_<utc>.jsonl que o start_match preservou de uma partida
que caiu antes do arquivamento. Para cada uma a ficha traz o que o Victor
precisa para decidir, na Q10, entre ingerir e arquivar: mapa, placar por
time, lado do humano, data e K/D, cada um com a fonte.

Nada é escrito em banco nenhum que já exista:

- o --db (uma cópia, de preferência a do tools/backup.py) é aberto com
  mode=ro, e o sha256 dele é registrado antes e depois da leitura. Se mudar,
  a ferramenta sai com erro;
- cada órfã é ingerida pelo próprio parser.store_match_from_events num
  SQLite novo, numa pasta temporária apagada no fim, e lida de lá pelo
  stats.build_match_data: placar, rounds contados e K/D saem da mesma conta
  do report;
- os .jsonl só são lidos.

O humano é casado por SteamID, como no watcher e no reingest_events (V1.1).
Sem --steamid, a SteamID é a que o próprio banco marca como humano
(kills.attacker_is_human); o nick, sem --player, é o player_name da partida
mais recente. snapshot, round_stats e player_blind casam pelo nick, mas o K/D
sai de kills, que casa pela SteamID. A ficha só mostra o fim da SteamID.

O mapa não vem no .jsonl: ele é inferido comparando os callouts da órfã
(snapshot e posição das kills) com os de cada mapa no banco
(player_positions.place); só vota o callout exclusivo de um mapa. A ficha diz
que é inferência e mostra os votos. O índice do alvo da bomba (`site`) não
serve: é índice de entidade e muda a cada partida no mesmo mapa. Arquivo de
plugin antigo, sem posição, fica com mapa desconhecido: o watcher tirava o
mapa do nome da demo, que não está nos eventos.

A data também não: a ficha dá o mtime do arquivo (último evento gravado; o
tools/backup.py preserva o mtime), o carimbo UTC do nome quando existe e as
partidas do banco imediatamente antes e depois.

A ficha com dado real fica FORA do repositório: --saida recusa caminho
dentro de um checkout git. Sem --saida, a ficha vai para o stdout.

Uso:
    .venv\\Scripts\\python.exe tools/ficha_orfas.py --db <copia.db> --events-dir <copia/events-live> [--saida <fora-do-repo>.md]
"""
import argparse
import contextlib
import hashlib
import io
import json
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import stats  # noqa: E402
from identity import PlayerIdentity  # noqa: E402
from parser import store_match_from_events  # noqa: E402
from reingest_events import NAME_RE, STEAMID64_RE, eh_banco_real  # noqa: E402

ORPHAN_RE = re.compile(r"^orphan_(?P<utc>\d{8}T\d{6}Z)(?:-\d+)?$")
CARIMBO_RE = re.compile(r"(?:^orphan_|__)(?P<utc>\d{8}T\d{6}Z)(?:-\d+)?$")
# Não é partida: o arquivo que o plugin ainda está escrevendo (ou a cauda).
IGNORADOS = frozenset({"current.jsonl"})
MR = 12              # MR12: 13 fecha o tempo normal
PRORROGACAO = 3      # MR3 por prorrogação: 4 fecha


# --------------------------------------------------------------- leitura

def sha256_de(caminho) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def abrir_ro(db) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def classificar(caminho: Path) -> str:
    """'padrão' (o reingest_events casa), 'orphan' (orphan_<utc> do
    start_match) ou 'fora' (nenhum dos dois)."""
    if NAME_RE.match(caminho.stem):
        return "padrão"
    if ORPHAN_RE.match(caminho.stem):
        return "orphan"
    return "fora"


def humano_do_banco(conn):
    """(steamid, nick) do humano segundo o banco: a SteamID mais frequente em
    kills.attacker_is_human e o player_name da partida mais recente."""
    linha = conn.execute(
        """SELECT attacker_steamid, COUNT(*) FROM kills
           WHERE attacker_is_human = 1 AND attacker_steamid IS NOT NULL
           GROUP BY attacker_steamid ORDER BY COUNT(*) DESC LIMIT 1"""
    ).fetchone()
    nick = conn.execute(
        """SELECT player_name FROM matches WHERE player_name IS NOT NULL
           ORDER BY played_at DESC LIMIT 1"""
    ).fetchone()
    return (linha[0] if linha else None), (nick[0] if nick else None)


def identidade(conn, steamid=None, player=None):
    """(PlayerIdentity, fonte). Recusa sem SteamID: só pelo nick o K/D
    divergiria do watcher (V1.1)."""
    if steamid is not None and not STEAMID64_RE.match(steamid):
        raise SystemExit(f"[ERRO] --steamid não é um SteamID64 (17 dígitos): {steamid!r}")
    do_banco, nick_do_banco = humano_do_banco(conn)
    fonte = "--steamid" if steamid else "kills.attacker_is_human do banco"
    steamid = steamid or do_banco
    if steamid is None:
        raise SystemExit("[ERRO] Sem a SteamID do humano: o banco não tem kill do humano; "
                         "passe --steamid.")
    nick = player or nick_do_banco
    if nick is None:
        raise SystemExit("[ERRO] Sem o nick do humano; passe --player.")
    return PlayerIdentity(name=nick, steamid=str(steamid)), fonte


def ler_cru(caminho: Path, ident: PlayerIdentity) -> dict:
    """O que a ficha tira direto do .jsonl, antes do parser: callouts
    (Counter de place), se há round_start, se o humano aparece e as linhas
    ilegíveis. Lê com utf-8-sig: há arquivo com BOM (contrato-events-jsonl).

    O humano aparece se algum evento traz a SteamID dele ou se algum jogador
    que não é bot está num time (o bot da CSTV vem com is_bot e sem time). Sem
    isso, é partida só de bots (o smoke da janela)."""
    lugares, ruins, round_start, humano = Counter(), 0, False, False
    with open(caminho, encoding="utf-8-sig", errors="replace") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha:
                continue
            try:
                e = json.loads(linha)
            except ValueError:
                ruins += 1
                continue
            if not isinstance(e, dict):
                continue
            tipo = e.get("type")
            round_start = round_start or tipo == "round_start"
            if ident.steamid in (e.get("attacker_steamid"), e.get("victim_steamid"),
                                 e.get("steamid")):
                humano = True
            if tipo == "snapshot":
                for p in e.get("players") or []:
                    if p.get("p_"):
                        lugares[p["p_"]] += 1
                    humano = humano or (p.get("b") is False and bool(p.get("s")))
            elif tipo in ("freeze_end", "round_stats"):
                humano = humano or any(p.get("is_bot") is False and p.get("side")
                                       for p in e.get("players") or [])
            elif tipo == "player_death":
                for chave in ("attacker_pos", "victim_pos"):
                    if (e.get(chave) or {}).get("place"):
                        lugares[e[chave]["place"]] += 1
    return {"lugares": lugares, "ilegiveis": ruins, "round_start": round_start,
            "humano": humano}


# ------------------------------------------------------------------ mapa

def callouts_por_mapa(conn) -> dict:
    """{place: {mapas em que aparece}}, das partidas do banco."""
    por_lugar = {}
    for linha in conn.execute(
        """SELECT DISTINCT m.map, p.place FROM player_positions p
           JOIN matches m ON m.id = p.match_id
           WHERE p.place IS NOT NULL AND p.place <> '' AND m.map IS NOT NULL"""
    ):
        por_lugar.setdefault(linha[1], set()).add(linha[0])
    return por_lugar


def inferir_mapa(lugares: Counter, por_lugar: dict):
    """(mapa ou None, explicação). Só vota o callout exclusivo de um mapa:
    CTSpawn e BombsiteA existem em quase todos e não dizem nada."""
    votos = Counter()
    for lugar, n in lugares.items():
        mapas = por_lugar.get(lugar)
        if mapas and len(mapas) == 1:
            votos[next(iter(mapas))] += n
    if not votos:
        return None, ("nenhum callout exclusivo de um mapa: o plugin desta gravação não "
                      "mandava posição, e o mapa não está nos eventos")
    total = sum(votos.values())
    partes = ", ".join(f"{m} {n}" for m, n in votos.most_common(3))
    (mapa, n), = votos.most_common(1)
    rotulo = "inferido" if n == total else "inferido, com votos em mais de um mapa"
    return mapa, (f"{rotulo} pelos callouts: {total} amostras com callout exclusivo de "
                  f"um mapa ({partes})")


# ---------------------------------------------------------------- placar

def placar_fechado(mine, theirs) -> bool:
    """MR12: 13 com o outro em até 11; empate em 12 vai para prorrogações
    MR3 (16, 19, ...), fechadas por quem chega a 4 nelas."""
    if mine is None or theirs is None:
        return False
    vence, perde = max(mine, theirs), min(mine, theirs)
    if perde < MR:
        return vence == MR + 1
    prorrogacao = (perde - MR) // PRORROGACAO
    return vence == MR + PRORROGACAO * (prorrogacao + 1) + 1


def _lados(rounds) -> str:
    """'CT nos rounds 1-12, T nos 13-22', na numeração dos rounds contados
    (a do placar do jogo)."""
    trechos = []
    for i, r in enumerate(rounds, start=1):
        lado = (r["human_side"] or "?").upper()
        if trechos and trechos[-1][0] == lado:
            trechos[-1][2] = i
        else:
            trechos.append([lado, i, i])
    return ", ".join(f"{lado} {'no round' if a == b else 'nos rounds'} "
                     f"{a if a == b else f'{a}-{b}'}" for lado, a, b in trechos)


def _quando(ts) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def vizinhas(conn, momento: str):
    antes = conn.execute(
        "SELECT demo_name, played_at FROM matches WHERE played_at <= ? "
        "ORDER BY played_at DESC LIMIT 1", (momento,)).fetchone()
    depois = conn.execute(
        "SELECT demo_name, played_at FROM matches WHERE played_at > ? "
        "ORDER BY played_at LIMIT 1", (momento,)).fetchone()
    return antes, depois


def ficha(caminho: Path, ident: PlayerIdentity, conn, por_lugar) -> dict:
    """Tudo o que a ficha mostra de uma órfã, ingerida num banco temporário."""
    cru = ler_cru(caminho, ident)
    mapa, mapa_prova = inferir_mapa(cru["lugares"], por_lugar)
    saida = io.StringIO()
    with tempfile.TemporaryDirectory(prefix="ficha_orfas_") as pasta:
        banco = Path(pasta) / "orfa.db"
        with contextlib.redirect_stdout(saida):
            match_id = store_match_from_events(
                caminho, {"demo_name": caminho.stem, "map": mapa}, banco, ident)
        dados, rounds_todos = None, []
        if match_id is not None:
            tmp = sqlite3.connect(banco)
            tmp.row_factory = sqlite3.Row
            try:
                linha = tmp.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
                dados = stats.build_match_data(tmp, linha)
                rounds_todos = tmp.execute(
                    "SELECT round_num, winner_side, human_side, counted FROM rounds "
                    "WHERE match_id = ? ORDER BY round_num", (match_id,)).fetchall()
            finally:
                tmp.close()
    contados = [r for r in rounds_todos if r["counted"]]
    abortados = [r["round_num"] for r in rounds_todos if r["winner_side"] is None]
    fantasmas = [r["round_num"] for r in rounds_todos
                 if r["winner_side"] is not None and not r["counted"]]
    mine = dados["score_mine"] if dados else None
    theirs = dados["score_theirs"] if dados else None
    st = dados["stats"]["all"] if dados else None

    motivos = []
    if not cru["round_start"]:
        motivos.append("sem round_start: cauda de uma partida já arquivada (órfão falso, "
                       "P1.1d), não é partida")
    if not cru["humano"]:
        motivos.append("o humano não aparece nos eventos: partida só de bots (smoke de "
                       "janela?)")
    if not contados:
        motivos.append("nenhum round contado")
    elif not placar_fechado(mine, theirs):
        motivos.append(f"placar não fecha o mapa ({mine} x {theirs}): partida interrompida "
                       "ou abandonada")
    if dados and dados["score_source"] == "rounds-partial":
        motivos.append("round sem lado do humano fica fora do placar")
    if cru["humano"] and (st is None or (st["kills"] == 0 and st["deaths"] == 0)):
        motivos.append("nenhuma kill nem morte do humano pela SteamID")

    stat = caminho.stat()
    momento = _quando(stat.st_mtime)
    carimbo = CARIMBO_RE.search(caminho.stem)
    return {
        "arquivo": caminho.name,
        "classe": classificar(caminho),
        "bytes": stat.st_size,
        "sha256": sha256_de(caminho),
        "mapa": mapa,
        "mapa_prova": mapa_prova,
        "placar": (mine, theirs),
        "outcome": dados["outcome"] if dados else None,
        "por_lado": (dados["score_ct"], dados["score_t"]) if dados else (None, None),
        "score_source": dados["score_source"] if dados else None,
        "completo": not motivos,
        "motivos": motivos,
        "rounds_arquivo": len(rounds_todos),
        "rounds_contados": len(contados),
        "abortados": abortados,
        "fantasmas": fantasmas,
        "lado_inicial": (contados[0]["human_side"] or "?").upper() if contados else None,
        "lados": _lados(contados) if contados else None,
        "mtime": momento,
        "carimbo_utc": carimbo.group("utc") if carimbo else None,
        "vizinhas": vizinhas(conn, momento),
        "duracao_min": dados["duration_minutes"] if dados else None,
        "stats": st,
        "humano": cru["humano"],
        "linhas_ilegiveis": cru["ilegiveis"],
        "avisos": [linha.strip() for linha in saida.getvalue().splitlines()
                   if any(t in linha for t in ("[AVISO]", "[PLACAR]", "[K/D]"))],
    }


# ---------------------------------------------------------------- saída

CLASSE = {
    "padrão": "casa o padrão events_<matchid>_map<N>[__<utc>]: o reingest_events a ingere",
    "orphan": "orphan_<utc> do start_match: não casa o padrão do reingest_events "
              "(ingerir exige renomear uma cópia)",
    "fora": "não casa o padrão do reingest_events nem o orphan_<utc>",
}
RESULTADO = {"win": "vitória", "loss": "derrota", "tie": "empate", None: "sem resultado"}


def _kd(st, humano=True) -> str:
    if not humano:
        return "não se aplica: o humano não aparece nos eventos"
    if st is None:
        return "indisponível (nenhum round contado)"
    kd = f"{st['kills'] / st['deaths']:.2f}" if st["deaths"] else "sem mortes"
    return (f"{st['kills']}/{st['deaths']} = {kd}; ADR {st['adr']:.1f}; "
            f"HS {st['hs_pct']:.0f}%; {st['rounds_played']} rounds")


def _vizinha(linha) -> str:
    return f"{linha['demo_name']} ({linha['played_at']})" if linha else "nenhuma"


def markdown(cab: dict, fichas: list, ingeridas: list, ignorados: list) -> str:
    out = [
        "# Ficha das partidas órfãs",
        "",
        f"- Gerada em {cab['gerada']} por tools/ficha_orfas.py (card V1.2), só em cópias.",
        f"- Banco: `{cab['db']}`, aberto com mode=ro.",
        f"  - sha256 antes: `{cab['sha_antes']}`",
        f"  - sha256 depois: `{cab['sha_depois']}`",
        f"  - {'inalterado' if cab['sha_antes'] == cab['sha_depois'] else 'MUDOU'}",
        f"- Eventos: `{cab['eventos']}`",
        f"- Humano: {cab['nick']}, SteamID terminada em {cab['steamid'][-4:]} "
        f"(fonte: {cab['fonte_id']}).",
        f"- {len(fichas)} órfã(s); {len(ingeridas)} arquivo(s) já no banco; "
        f"ignorados: {', '.join(ignorados) or 'nenhum'}.",
        "",
        "Fontes: o placar, os rounds e o K/D saem do parser.store_match_from_events num banco "
        "temporário e do stats.build_match_data (a conta do report: rounds contados, kills "
        "pós-morte fora). O mapa é inferido (o .jsonl não o traz). A data é o mtime do arquivo, "
        "o carimbo UTC do nome e as partidas vizinhas no banco; o .jsonl não tem relógio.",
    ]
    for f in fichas:
        mine, theirs = f["placar"]
        resultado = ("sem lado do humano em algum round, placar incompleto"
                     if f["score_source"] == "rounds-partial" else RESULTADO[f["outcome"]])
        placar = (f"humano {mine} x {theirs} adversário ({resultado}); "
                  f"por lado CT {f['por_lado'][0]} : TR {f['por_lado'][1]}; "
                  f"fonte {f['score_source']}" if mine is not None else "sem placar")
        situacao = "completo" if f["completo"] else "PARCIAL: " + "; ".join(f["motivos"])
        rounds = (f"{f['rounds_arquivo']} no arquivo, {f['rounds_contados']} contados"
                  + (f"; abortados (sem round_end): {f['abortados']}" if f["abortados"] else "")
                  + (f"; fantasmas: {f['fantasmas']}" if f["fantasmas"] else ""))
        data = (f"último evento gravado (mtime) {f['mtime']}"
                + (f"; carimbo do nome {f['carimbo_utc']} UTC" if f["carimbo_utc"] else "")
                + f"; no banco, antes: {_vizinha(f['vizinhas'][0])}, depois: "
                f"{_vizinha(f['vizinhas'][1])}")
        out += [
            "",
            f"## {f['arquivo']}",
            "",
            "| campo | valor |",
            "|---|---|",
            f"| nome | {CLASSE[f['classe']]} |",
            f"| tamanho e sha256 | {f['bytes']} bytes, `{f['sha256']}` |",
            f"| mapa | {f['mapa'] or 'desconhecido'} ({f['mapa_prova']}) |",
            f"| placar | {placar} |",
            f"| situação | {situacao} |",
            f"| rounds | {rounds} |",
            f"| humano nos eventos | {'sim' if f['humano'] else 'não'} |",
            f"| lado do humano | inicial {f['lado_inicial'] or '?'}; {f['lados'] or 'sem rounds'}"
            f"{' (numeração dos rounds contados)' if f['lados'] else ''} |",
            f"| data | {data} |",
            f"| duração | {f['duracao_min'] if f['duracao_min'] is not None else '?'} min (ticks) |",
            f"| K/D do humano | {_kd(f['stats'], f['humano'])} |",
        ]
        if f["linhas_ilegiveis"]:
            out.append(f"| linhas ilegíveis | {f['linhas_ilegiveis']} |")
        if f["avisos"]:
            out += ["", "Avisos do parser:", ""] + [f"- `{a}`" for a in f["avisos"]]
    if ingeridas:
        out += ["", "## Já no banco (não são órfãs)", "", ", ".join(ingeridas)]
    return "\n".join(out) + "\n"


def dentro_de_repo(caminho: Path) -> bool:
    alvo = caminho.resolve()
    return any((p / ".git").exists() for p in (alvo, *alvo.parents))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="cópia do banco (aberta com mode=ro)")
    ap.add_argument("--confirmo-banco-real", action="store_true",
                    help="exigido quando --db é o banco real do app")
    ap.add_argument("--events-dir", required=True, help="cópia da pasta events-live")
    ap.add_argument("--steamid", default=None,
                    help="SteamID64 do humano; padrão: a que o banco marca como humano")
    ap.add_argument("--player", default=None,
                    help="nick do humano; padrão: o player_name da partida mais recente")
    ap.add_argument("--saida", default=None,
                    help="arquivo .md da ficha, fora de qualquer repositório git")
    args = ap.parse_args(argv)

    if eh_banco_real(args.db) and not args.confirmo_banco_real:
        raise SystemExit(f"[ERRO] {args.db} é o banco real do app. Rode numa cópia "
                         "(tools/backup.py) ou passe --confirmo-banco-real.")
    db = Path(args.db)
    if not db.is_file():
        raise SystemExit(f"[ERRO] Banco não encontrado: {db}")
    pasta = Path(args.events_dir)
    if not pasta.is_dir():
        raise SystemExit(f"[ERRO] Pasta de eventos não encontrada: {pasta}")
    saida = Path(args.saida) if args.saida else None
    if saida is not None and dentro_de_repo(saida):
        raise SystemExit(f"[ERRO] {saida} está dentro de um repositório git: a ficha tem "
                         "dado real e fica fora do repo.")

    sha_antes = sha256_de(db)
    conn = abrir_ro(db)
    try:
        ident, fonte_id = identidade(conn, args.steamid, args.player)
        mapa_por_nome = {r["demo_name"]: r["map"]
                         for r in conn.execute("SELECT demo_name, map FROM matches")}
        arquivos = sorted(pasta.glob("*.jsonl"))
        ignorados = [p.name for p in arquivos if p.name in IGNORADOS]
        ingeridas = [p.stem for p in arquivos
                     if p.name not in IGNORADOS and p.stem in mapa_por_nome]
        orfas = [p for p in arquivos
                 if p.name not in IGNORADOS and p.stem not in mapa_por_nome]
        por_lugar = callouts_por_mapa(conn)
        fichas = [ficha(p, ident, conn, por_lugar) for p in orfas]
    finally:
        conn.close()
    sha_depois = sha256_de(db)

    texto = markdown({
        "gerada": datetime.now().isoformat(timespec="seconds"),
        "db": str(db), "eventos": str(pasta),
        "sha_antes": sha_antes, "sha_depois": sha_depois,
        "nick": ident.name, "steamid": ident.steamid, "fonte_id": fonte_id,
    }, fichas, ingeridas, ignorados)

    if saida is None:
        sys.stdout.write(texto)
    else:
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(texto, encoding="utf-8")
        print(f"[FICHA] {len(fichas)} órfã(s) em {saida}")
        for f in fichas:
            mine, theirs = f["placar"]
            print(f"  - {f['arquivo']}: {f['mapa'] or 'mapa ?'}, {mine} x {theirs}, "
                  f"{'completo' if f['completo'] else 'parcial'}")
    print(f"[FICHA] sha256 do banco antes {sha_antes[:12]}, depois {sha_depois[:12]}",
          file=sys.stderr)
    if sha_antes != sha_depois:
        print("[ERRO] O sha256 do banco mudou durante a leitura.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
