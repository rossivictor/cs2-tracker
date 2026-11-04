#!/usr/bin/env python3
"""
Reprocessa os .jsonl de eventos já arquivados em docker/events-live/,
recalculando placar por time, lado do humano por round e marcação de
round fantasma — sem precisar rejogar nada.

Preserva o id, o played_at e o series_num_maps de cada partida (deep link
do report, gráfico de tendência e etiqueta BO3/BO5 dependem deles). Partida
nova (arquivo que não está no banco) recebe o --series-num-maps, se dado.

O humano é identificado por SteamID, como no watcher ao vivo: a SteamID vem
de --steamid, do --match-config ou do próprio --player quando ele é um
SteamID64. Sem SteamID a ferramenta recusa: só pelo nome ela classificaria
o humano diferente do watcher (card V1.1).

--db é obrigatório. Apontar para o banco real do app (cs2_tracker.db ou o
CS2_TRACKER_DB_PATH do .env) exige --confirmo-banco-real; o caminho normal
é uma cópia (tools/backup.py).

Uso:
    .venv\\Scripts\\python.exe tools/reingest_events.py --db <copia.db> --steamid <SteamID64> [--dry-run]
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from config import EVENTS_LIVE_DIR  # noqa: E402
from identity import PlayerIdentity, resolve_identity  # noqa: E402
from parser import init_db, store_match_from_events  # noqa: E402

# Com o sufixo __<utc>[-n] que o watcher dá numa colisão (P1.1a; P1.1b).
NAME_RE = re.compile(r"^events_(?P<matchid>\d+)_map(?P<mapnum>\d+)(?:__\d{8}T\d{6}Z(?:-\d+)?)?$")
STEAMID64_RE = re.compile(r"^\d{17}$")
NOME_BANCO_REAL = "cs2_tracker.db"


def eh_banco_real(db) -> bool:
    """True quando --db é o banco do app: o arquivo de nome cs2_tracker.db
    (o default do config.py, em qualquer checkout ou worktree) ou o caminho
    do CS2_TRACKER_DB_PATH do .env, resolvido a partir da raiz do repo."""
    alvo = Path(db).resolve()
    if alvo.name.lower() == NOME_BANCO_REAL:
        return True
    do_env = config.load_env().get("CS2_TRACKER_DB_PATH")
    if not do_env:
        return False
    caminho = Path(do_env)
    if not caminho.is_absolute():
        caminho = ROOT / caminho
    return alvo == caminho.resolve()


def identidade(player, steamid, match_config, nome_no_banco) -> PlayerIdentity:
    """Identidade do humano com SteamID obrigatória (card V1.1).

    O nick continua necessário: snapshot, round_stats e player_blind não
    trazem steamid e o parser os casa por nome (_is_human_named). Kills e
    dano casam por steamid sempre que a identidade tem uma (_is_human)."""
    if steamid is not None and not STEAMID64_RE.match(steamid):
        raise SystemExit(f"[ERRO] --steamid não é um SteamID64 (17 dígitos): {steamid!r}")
    player = player or nome_no_banco
    ident = resolve_identity(player, match_config) if player else None
    steamid = steamid or (ident.steamid if ident else None)
    if steamid is None:
        raise SystemExit("[ERRO] Sem a SteamID do humano; passe --steamid ou --match-config.")
    nome = ident.name if ident else None
    if nome is None or STEAMID64_RE.match(nome):
        # --player foi a SteamID e o match_config não deu o nick.
        nome = nome_no_banco
    if nome is None or STEAMID64_RE.match(nome):
        raise SystemExit("[ERRO] Sem o nick do humano; passe --player com o nick.")
    return PlayerIdentity(name=nome, steamid=steamid)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True,
                    help="banco a reprocessar; de preferência uma cópia")
    ap.add_argument("--confirmo-banco-real", action="store_true",
                    help="exigido quando --db é o banco real do app")
    ap.add_argument("--events-dir", default=EVENTS_LIVE_DIR)
    ap.add_argument("--player", default=None,
                    help="nick/SteamID64; padrão: o player_name já gravado nas partidas")
    ap.add_argument("--steamid", default=None,
                    help="SteamID64 do humano; padrão: a do --match-config ou do --player")
    ap.add_argument("--match-config", default=None,
                    help="match_config.json pra cruzar nick<->SteamID (opcional)")
    ap.add_argument("--series-num-maps", type=int, default=None,
                    help="tamanho da série (1, 3 ou 5) das partidas novas; as do banco mantêm o seu")
    ap.add_argument("--dry-run", action="store_true",
                    help="só lista o que seria reprocessado")
    args = ap.parse_args()

    # Antes de qualquer acesso ao banco: o init_db abaixo já grava as
    # migrações, até no --dry-run.
    if eh_banco_real(args.db) and not args.confirmo_banco_real:
        raise SystemExit(f"[ERRO] {args.db} é o banco real do app. Rode numa cópia "
                         "(tools/backup.py) ou passe --confirmo-banco-real.")

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
            "SELECT demo_name, id, map, player_name, score_mine, score_theirs,"
            " series_num_maps FROM matches"
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

    nome_no_banco = next(
        (r["player_name"] for r in known.values() if r["player_name"]), None
    )
    identity = identidade(args.player, args.steamid, args.match_config, nome_no_banco)
    print(f"\n[REINGEST] Jogador: {identity.name} (steamid={identity.steamid})\n")

    for path in files:
        row = known.get(path.stem)
        meta = {
            "demo_name": path.stem,
            "map": row["map"] if row else None,
            # O UPDATE do parser grava series_num_maps; sem ele aqui a
            # reingestão apagava a etiqueta BO3/BO5 (card V1.1).
            "series_num_maps": row["series_num_maps"] if row else args.series_num_maps,
        }
        store_match_from_events(path, meta, args.db, identity, force=True)
        print()

    print("[REINGEST] Concluído. Regere o report pra ver o resultado.")


if __name__ == "__main__":
    main()
