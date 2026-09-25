#!/usr/bin/env python3
"""
Recalcula damages.dmg_health das partidas JÁ no banco, cortando pelo que a
vítima ainda tinha de vida (ver parser.clamp_damage_health).

Por que dá pra fazer sem reprocessar nada: a tabela damages guarda TODOS os
eventos de dano, de todos os atacantes, com round e tique. Isso é tudo que o
corte precisa — não há informação nova a extrair da demo nem do JSONL.

Idempotente: lê sempre de dmg_health_raw quando ela já existe, então rodar
duas vezes dá o mesmo resultado.

    python tools/fix_damage_clamp.py --dry-run     # só mostra o impacto
    python tools/fix_damage_clamp.py               # aplica
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DB_PATH
from parser import MAX_HEALTH, init_db


def _linhas_da_partida(conn, match_id):
    return conn.execute(
        """SELECT rowid, round_num, tick,
                  COALESCE(victim_steamid, victim_name) AS vitima,
                  COALESCE(dmg_health_raw, dmg_health) AS bruto
             FROM damages WHERE match_id=?
            ORDER BY round_num, tick, rowid""",
        (match_id,),
    ).fetchall()


def _corta(linhas):
    """[(rowid, dmg_cortado, bruto)] na ordem de tique."""
    acumulado = {}
    saida = []
    for rowid, round_num, _tick, vitima, bruto in linhas:
        bruto = bruto or 0
        if not vitima:
            # Sem saber em quem acertou não dá pra cortar — ver
            # parser.clamp_damage_health. Fonte demo é quase toda assim.
            saida.append((rowid, bruto, bruto))
            continue
        chave = (round_num, vitima)
        ja = acumulado.get(chave, 0)
        real = max(0, min(bruto, MAX_HEALTH - ja))
        acumulado[chave] = ja + real
        saida.append((rowid, real, bruto))
    return saida


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true",
                    help="não grava; só mostra quanto cada partida muda")
    args = ap.parse_args()

    if not Path(args.db).exists():
        print(f"[FIX] banco não encontrado: {args.db}")
        return 1

    # Pela init_db pra garantir que dmg_health_raw existe antes do UPDATE.
    init_db(args.db).close()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    partidas = cur.execute(
        "SELECT id, map, played_at, source FROM matches ORDER BY id"
    ).fetchall()

    print(f"{'id':>4} {'mapa':<12} {'fonte':<8} {'bruto':>8} {'cortado':>8} {'dif':>7} {'%':>7}")
    tot_bruto = tot_cortado = 0
    for match_id, mapa, _played, source in partidas:
        linhas = _linhas_da_partida(conn, match_id)
        if not linhas:
            continue
        cortadas = _corta(linhas)
        bruto = sum(b for _r, _c, b in cortadas)
        cortado = sum(c for _r, c, _b in cortadas)
        tot_bruto += bruto
        tot_cortado += cortado
        pct = (bruto - cortado) / bruto * 100 if bruto else 0
        print(f"{match_id:>4} {str(mapa)[:12]:<12} {str(source):<8} "
              f"{bruto:>8} {cortado:>8} {bruto - cortado:>7} {pct:>6.1f}%")

        if not args.dry_run:
            cur.executemany(
                "UPDATE damages SET dmg_health=?, dmg_health_raw=? WHERE rowid=?",
                [(c, b, r) for r, c, b in cortadas],
            )

    dif = tot_bruto - tot_cortado
    pct = dif / tot_bruto * 100 if tot_bruto else 0
    print(f"{'':>4} {'TOTAL':<12} {'':<8} {tot_bruto:>8} {tot_cortado:>8} {dif:>7} {pct:>6.1f}%")

    if args.dry_run:
        print("\n[FIX] dry-run: nada foi gravado.")
    else:
        conn.commit()
        print("\n[FIX] aplicado. dmg_health agora é vida removida; "
              "o valor original ficou em dmg_health_raw.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
