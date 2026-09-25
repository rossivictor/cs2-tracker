#!/usr/bin/env python3
"""
Reprocessa as partidas de origem 'demo' que já estão no banco, relendo o
.dem que gerou cada uma.

Existe por causa de PLAYER_PROPS: até 21/09/2026 o parse era feito sem
pedir propriedades por jogador, então flash, valor de equipamento e colete
foram descartados na ingestão. Não dá pra reconstruir isso de dentro do
banco — só relendo a demo.

Só toca partidas que JÁ existem no banco com source='demo' (casadas por
matches.demo_path). Não varre pasta de demo atrás de arquivo novo: as demos
em docker/demos-live/ incluem partidas já ingeridas pelo caminho do plugin,
e ingeri-las aqui criaria uma segunda linha pra mesma partida, com o placar
contado duas vezes. Importar essas é outro problema, que precisa de
deduplicação por matchid e ainda não foi resolvido.

Preserva o id e o played_at de cada partida (deep link /partidas/<id>,
gráfico de tendência e recordes dependem deles).

Uso:
    .venv\\Scripts\\python.exe tools/reingest_demos.py [--dry-run]
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH  # noqa: E402
from identity import resolve_identity  # noqa: E402
from parser import init_db, parse_and_store  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true",
                    help="só lista o que seria reprocessado")
    ap.add_argument("--match-config", default=None,
                    help="match_config.json pra cruzar steamid<->nick (opcional)")
    args = ap.parse_args()

    # init_db aplica as migrações de coluna novas (freeze_end_tick,
    # player_positions.flash_duration e cia.) antes de qualquer INSERT.
    init_db(args.db).close()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, demo_name, demo_path, map, player_name, score_ct, score_t,
                  duration_minutes, series_num_maps
           FROM matches WHERE source = 'demo' ORDER BY id"""
    ).fetchall()
    conn.close()

    if not rows:
        raise SystemExit("[INFO] Nenhuma partida com source='demo' no banco.")

    faltando = []
    alvos = []
    for row in rows:
        path = Path(row["demo_path"]) if row["demo_path"] else None
        if path and path.exists():
            alvos.append((row, path))
        else:
            faltando.append(row)

    for row in faltando:
        print(f"[PULA] match {row['id']} ({row['demo_name']}): "
              f".dem não encontrado em {row['demo_path']}")

    print(f"[INFO] {len(alvos)} partida(s) para reprocessar.")
    if args.dry_run:
        for row, path in alvos:
            print(f"  match {row['id']:>3}  {row['map']:<12} {path}")
        return

    for row, path in alvos:
        meta = {
            "map": row["map"],
            # score_ct/score_t e minutes são recalculados da demo quando
            # None; passar os antigos aqui congelaria um valor que a própria
            # reingestão existe pra corrigir.
            "score_ct": None,
            "score_t": None,
            "minutes": None,
            "series_num_maps": row["series_num_maps"],
        }
        identity = resolve_identity(row["player_name"], args.match_config)
        parse_and_store(path, meta, args.db, identity, force=True)

    print(f"[OK] {len(alvos)} partida(s) reprocessada(s).")


if __name__ == "__main__":
    main()
