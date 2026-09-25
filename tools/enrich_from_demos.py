#!/usr/bin/env python3
"""
Enriquece partidas que JÁ estão no banco com o que só a demo tem.

Nunca cria partida. O casamento é por (matchid, mapa) lido do nome do
arquivo contra `matches.demo_name` (events_<matchid>_map<N>); demo sem par
no banco é pulada, e partida sem demo fica como está. Isso é o ponto: as
demos em docker/demos-live/ cobrem matchids que já foram ingeridos pelo
plugin, então ingeri-las como partida criaria uma segunda linha pra mesma
partida, com placar e K/D contados duas vezes.

O que a demo acrescenta e o plugin não tem:
  - player_positions de verdade (o caminho de eventos grava uma linha
    sintética em x=y=z=0 só pra registrar o lado) -> heatmap e radar
  - rounds.freeze_end_tick -> âncora da economia
  - flash_duration / equip_value / armor / has_helmet / has_defuser

O que NÃO é tocado, de propósito: kills, damages, rounds (fora do
freeze_end_tick), placar e outcome. Nesses a fonte do plugin é melhor — ela
traz o lado e o nome de cada bot, que o dataframe de kills do awpy não traz,
e é disso que dependem clutch, trade e head-to-head. Sobrescrever com a demo
perderia essas três métricas.

Antes de escrever qualquer coisa, confere se a numeração de round das duas
fontes bate (mesma quantidade e mesma sequência de vencedor). Se não bater,
pula a partida: posição colada no round errado é pior que posição nenhuma.

Uso:
    .venv\\Scripts\\python.exe tools/enrich_from_demos.py [--dry-run]
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import polars as pl  # noqa: E402
from awpy import Demo  # noqa: E402

from config import DB_PATH, DEMOS_LIVE_DIR  # noqa: E402
from identity import resolve_identity  # noqa: E402
from parser import PLAYER_PROPS, init_db  # noqa: E402

# 2026-09-19_15-25-11_44_de_inferno_can1sh_vs_Bots.dem
NAME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_[\d-]+_(?P<matchid>\d+)_(?P<map>de_[a-z0-9]+)_"
)


def _parse_demo_name(path: Path):
    m = NAME_RE.match(path.name)
    if not m:
        return None
    return m.group("matchid"), m.group("map")


def _find_match(conn, matchid, map_name):
    """Partida já existente para (matchid, mapa). Casa pelo matchid dentro de
    demo_name porque o sufixo _map<N> do plugin nem sempre corresponde à
    ordem real dos mapas na série."""
    rows = conn.execute(
        """SELECT id, demo_name, map, player_name, source
             FROM matches
            WHERE demo_name LIKE ? AND map = ?""",
        (f"events\\_{matchid}\\_map%".replace("\\_", "_"), map_name),
    ).fetchall()
    return rows[0] if len(rows) == 1 else None


def _rounds_align(db_rounds, demo_rounds):
    """As duas fontes numeram rounds por conta própria. Só escreve se a
    sequência de vencedores bater — é o que prova que o round N de uma é o
    round N da outra."""
    db_seq = [r["winner_side"] for r in db_rounds if r["counted"]]
    demo_seq = [r["winner"] for r in demo_rounds]
    if not db_seq or not demo_seq:
        return False, "uma das fontes não tem round com vencedor"
    if len(db_seq) != len(demo_seq):
        return False, f"{len(db_seq)} rounds no banco vs {len(demo_seq)} na demo"
    if db_seq != demo_seq:
        diff = next(i for i, (a, b) in enumerate(zip(db_seq, demo_seq)) if a != b)
        return False, f"sequência de vencedores diverge no round {diff + 1}"
    return True, ""


def enrich_one(conn, match_row, demo_path, dry_run=False):
    """Devolve (ok, mensagem)."""
    identity = resolve_identity(match_row["player_name"], None)

    try:
        dem = Demo(str(demo_path))
        dem.parse(player_props=PLAYER_PROPS)
    except BaseException as exc:  # noqa: BLE001
        # BaseException e não Exception: arquivo truncado faz o parser Rust
        # do demoparser2 levantar pyo3_runtime.PanicException, que herda de
        # BaseException e passaria batido por um `except Exception`,
        # derrubando o lote inteiro por causa de um arquivo. Interrupção do
        # usuário continua subindo.
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return False, f"demo não parseia ({type(exc).__name__}: {str(exc)[:70]})"

    # Trava contra destruição de dado bom. Este enriquecedor APAGA todas as
    # posições da partida antes de reinserir as da demo — o que era inofensivo
    # quando o caminho de eventos só gravava linhas sintéticas (x=y=z=0) pra
    # registrar o lado. Desde o plugin v0.3.0 ele grava posição de verdade dos
    # 10 jogadores, com a posição da kill no tique exato, e a demo daria algo
    # PIOR: só o humano, e num espaço de tiques diferente do que as kills
    # gravadas pelo plugin usam (o join de stats.match_positions é por
    # igualdade de tique, então o resultado seria zero posição, em silêncio).
    ja_tem_posicao_real = conn.execute(
        "SELECT 1 FROM player_positions WHERE match_id=? AND x IS NOT NULL "
        "AND (x <> 0 OR y <> 0) LIMIT 1",
        (match_row["id"],),
    ).fetchone()
    if ja_tem_posicao_real:
        return False, "já tem posição real (plugin v0.3.0+) — enriquecer só pioraria"

    demo_rounds = list(dem.rounds.iter_rows(named=True))
    db_rounds = conn.execute(
        "SELECT round_num, winner_side, COALESCE(counted,1) AS counted "
        "FROM rounds WHERE match_id=? ORDER BY round_num",
        (match_row["id"],),
    ).fetchall()

    aligned, why = _rounds_align(db_rounds, demo_rounds)
    if not aligned:
        return False, f"rounds não alinham: {why}"

    if identity.has_steamid and "steamid" in dem.ticks.columns:
        human = dem.ticks.filter(pl.col("steamid").cast(pl.Utf8) == identity.steamid)
    else:
        human = dem.ticks.filter(pl.col("name") == identity.name)
    if human.height == 0:
        return False, f"nenhum tick de '{identity.name}' na demo"

    # round_num da demo -> round_num do banco, pela ordem dos rounds contados.
    counted_nums = [r["round_num"] for r in db_rounds if r["counted"]]
    remap = {d["round_num"]: counted_nums[i] for i, d in enumerate(demo_rounds)}

    def _bool(value):
        return None if value is None else int(bool(value))

    positions = [
        (match_row["id"], remap[t["round_num"]], t["tick"], t["X"], t["Y"], t["Z"],
         t["side"], t["place"], t["health"],
         t.get("flash_duration"), t.get("current_equip_value"), t.get("armor"),
         _bool(t.get("has_helmet")), _bool(t.get("has_defuser")))
        for t in human.iter_rows(named=True)
        if t["round_num"] in remap
    ]
    freeze = [
        (d["freeze_end"], match_row["id"], remap[d["round_num"]])
        for d in demo_rounds
        if d["round_num"] in remap
    ]

    if dry_run:
        return True, f"{len(positions)} posições, {len(freeze)} freeze_end (dry-run)"

    cur = conn.cursor()
    # As posições sintéticas do caminho de eventos (x=y=z=0) saem: elas só
    # existiam pra registrar o lado, que os rounds já guardam em human_side.
    cur.execute("DELETE FROM player_positions WHERE match_id=?", (match_row["id"],))
    cur.executemany(
        """INSERT INTO player_positions (match_id, round_num, tick, x, y, z, side, place, health,
                                          flash_duration, equip_value, armor, has_helmet, has_defuser)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        positions,
    )
    cur.executemany(
        "UPDATE rounds SET freeze_end_tick=? WHERE match_id=? AND round_num=?",
        freeze,
    )
    conn.commit()
    return True, f"{len(positions)} posições, {len(freeze)} freeze_end"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--demos-dir", default=DEMOS_LIVE_DIR)
    ap.add_argument("--dry-run", action="store_true",
                    help="não escreve; só diz o que faria e por que pularia")
    args = ap.parse_args()

    # Aplica as migrações de coluna antes de qualquer UPDATE que dependa delas.
    init_db(args.db).close()

    demos_dir = Path(args.demos_dir)
    demos = sorted(demos_dir.glob("*.dem"))
    if not demos:
        raise SystemExit(f"[ERRO] Nenhum .dem em {demos_dir}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    enriquecidas = puladas = 0
    motivos = {}
    try:
        for demo_path in demos:
            parsed = _parse_demo_name(demo_path)
            if not parsed:
                print(f"[PULA] {demo_path.name}: nome fora do padrão")
                puladas += 1
                continue
            matchid, map_name = parsed
            match_row = _find_match(conn, matchid, map_name)
            if match_row is None:
                print(f"[PULA] {demo_path.name}: sem partida correspondente no banco")
                puladas += 1
                motivos["sem par no banco"] = motivos.get("sem par no banco", 0) + 1
                continue

            ok, msg = enrich_one(conn, match_row, demo_path, args.dry_run)
            marca = "OK   " if ok else "[PULA]"
            print(f"{marca} match {match_row['id']:>3} {match_row['demo_name']:<18} "
                  f"({map_name}): {msg}")
            if ok:
                enriquecidas += 1
            else:
                puladas += 1
                chave = msg.split("(")[0].strip()
                motivos[chave] = motivos.get(chave, 0) + 1
    finally:
        conn.close()

    print()
    print(f"[RESUMO] {enriquecidas} partida(s) enriquecida(s), {puladas} pulada(s).")
    for motivo, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
        print(f"         {n:>3}x  {motivo}")


if __name__ == "__main__":
    main()
