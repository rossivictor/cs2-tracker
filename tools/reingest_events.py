#!/usr/bin/env python3
"""
Reprocessa os .jsonl de eventos já arquivados em docker/events-live/,
recalculando placar por time, lado do humano por round e marcação de
round fantasma — sem precisar rejogar nada.

Preserva o id e o played_at de cada partida (deep link do report e
gráfico de tendência dependem deles).

Uso:
    .venv\\Scripts\\python.exe tools/reingest_events.py [--dry-run]
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH, EVENTS_LIVE_DIR  # noqa: E402
from identity import resolve_identity  # noqa: E402
from parser import init_db, store_match_from_events  # noqa: E402

NAME_RE = re.compile(r"^events_(?P<matchid>\d+)_map(?P<mapnum>\d+)$")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--events-dir", default=EVENTS_LIVE_DIR)
    ap.add_argument("--player", default=None,
                    help="nick/SteamID64; padrão: o player_name já gravado nas partidas")
    ap.add_argument("--dry-run", action="store_true",
                    help="só lista o que seria reprocessado")
    args = ap.parse_args()

    events_dir = Path(args.events_dir)
    files = sorted(p for p in events_dir.glob("events_*.jsonl") if NAME_RE.match(p.stem))
    if not files:
        raise SystemExit(f"[ERRO] Nenhum events_*.jsonl em {events_dir}")

    # init_db aplica as migrações de coluna (score_mine, human_side, counted)
    # antes de qualquer SELECT que dependa delas.
    init_db(args.db).close()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    known = {
        row["demo_name"]: row
        for row in conn.execute(
            "SELECT demo_name, id, map, player_name, score_mine, score_theirs FROM matches"
        )
    }
    conn.close()

    print(f"[REINGEST] {len(files)} arquivo(s) em {events_dir}\n")
    for path in files:
        row = known.get(path.stem)
        if row is None:
            print(f"  - {path.stem}: não está no banco, será inserido como partida nova")
        else:
            antes = (f"{row['score_mine']} x {row['score_theirs']}"
                     if row["score_mine"] is not None else "sem placar por time")
            print(f"  - {path.stem}: match_id={row['id']} ({row['map']}), antes: {antes}")

    if args.dry_run:
        print("\n[REINGEST] --dry-run, nada foi alterado.")
        return

    player = args.player or next(
        (r["player_name"] for r in known.values() if r["player_name"]), None
    )
    if not player:
        raise SystemExit("[ERRO] Não achei o jogador; passe --player.")
    identity = resolve_identity(player)
    print(f"\n[REINGEST] Jogador: {identity.name} "
          f"(steamid={identity.steamid or 'não resolvido'})\n")

    for path in files:
        row = known.get(path.stem)
        meta = {"demo_name": path.stem, "map": row["map"] if row else None}
        store_match_from_events(path, meta, args.db, identity, force=True)
        print()

    print("[REINGEST] Concluído. Regere o report pra ver o resultado.")


if __name__ == "__main__":
    main()
