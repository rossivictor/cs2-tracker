#!/usr/bin/env python3
"""
CS2 Tracker — Parser
=====================
Converte um .dem (gravado pelo watcher.py via GOTV) em dados estruturados
usando awpy, e grava tudo num SQLite: rounds, kills, dano e a posição
(só do jogador humano, filtrado por nome — não guarda tick de bot).

Requer Python <3.14 (awpy 2.x exige >=3.11,<3.14) — rode a partir do
.venv do projeto, não do Python do sistema.

Sobre economia: o awpy 2.0.2 não expõe dinheiro (quanto você tinha, quanto
gastou) — isso continua de fora. Mas expõe `current_equip_value`, o valor do
equipamento que você carrega, como player prop; é o que permite classificar
o round em eco/force/full-buy. Ver PLAYER_PROPS abaixo.

Limite que vale saber antes de pedir qualquer coisa por jogador: nesta demo
**só o humano aparece em `dem.ticks`** — os bots não entram no stream de
ticks, e por isso não há como somar o equipamento do time nem saber a
economia do adversário. Tudo que sai daqui é do jogador, não do time.

Uso standalone (reprocessar uma demo órfã, sem precisar do watcher):
    python parser.py <caminho.dem> --map de_mirage --score-ct 1 \\
                      --score-t 13 --minutes 19 --player can1sh \\
                      --db cs2_tracker.db
"""

import argparse
import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

import polars as pl
from awpy import Demo

from config import DB_PATH
from identity import PlayerIdentity, resolve_identity

# Propriedades por jogador pedidas ao awpy no parse. Sem passar isto, o awpy
# extrai só 6 (["last_place_name","X","Y","Z","health","team_name"]) e tudo
# abaixo é descartado silenciosamente — era o caso até 21/09/2026.
#
# A lista é explícita e não `awpy.demo.DEFAULT_PLAYER_PROPS` de propósito:
# pedimos o que gravamos. Ficaram de fora, com motivo:
#   - inventory: lista de strings por tick, pesada, e nada lê hoje
#   - pitch/yaw/velocity_*/accuracy_penalty/zoom_lvl: são a matéria-prima de
#     crosshair placement e counter-strafing, que são outra feature — entram
#     junto com ela, não antes
#   - ping/team_clan_name: não descrevem jogo
#
# Nome de saída != nome pedido em alguns casos (awpy.parsers.utils.fix_common_names):
# armor_value -> armor, team_name -> side, last_place_name -> place.
PLAYER_PROPS = [
    "armor_value",
    "has_helmet",
    "has_defuser",
    "flash_duration",
    "current_equip_value",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demo_name TEXT UNIQUE NOT NULL,
    map TEXT,
    played_at TEXT,
    score_ct INTEGER,
    score_t INTEGER,
    score_mine INTEGER,
    score_theirs INTEGER,
    score_source TEXT,
    outcome TEXT,
    duration_minutes INTEGER,
    demo_path TEXT,
    player_name TEXT,
    source TEXT DEFAULT 'demo',
    agg_kills INTEGER,
    agg_deaths INTEGER,
    agg_assists INTEGER,
    agg_damage INTEGER,
    agg_hs_kills INTEGER,
    agg_shots_fired INTEGER,
    agg_shots_hit INTEGER
);

CREATE TABLE IF NOT EXISTS rounds (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    winner_side TEXT,
    reason TEXT,
    bomb_plant INTEGER,
    bomb_site TEXT,
    start_tick INTEGER,
    freeze_end_tick INTEGER,
    end_tick INTEGER,
    human_side TEXT,
    counted INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS kills (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    attacker_name TEXT,
    attacker_steamid TEXT,
    attacker_side TEXT,
    victim_name TEXT,
    victim_steamid TEXT,
    victim_side TEXT,
    weapon TEXT,
    headshot INTEGER,
    distance REAL,
    attacker_is_human INTEGER,
    victim_is_human INTEGER,
    post_mortem INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS damages (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    attacker_name TEXT,
    attacker_steamid TEXT,
    victim_name TEXT,
    victim_steamid TEXT,
    weapon TEXT,
    hitgroup TEXT,
    dmg_health INTEGER,
    dmg_armor INTEGER,
    attacker_is_human INTEGER,
    victim_is_human INTEGER,
    post_mortem INTEGER DEFAULT 0,
    -- Ver clamp_damage_health: dmg_health guarda a vida REMOVIDA e esta
    -- coluna o que a fonte reportou, que pode passar de 100.
    dmg_health_raw INTEGER
);

CREATE TABLE IF NOT EXISTS player_positions (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    x REAL,
    y REAL,
    z REAL,
    side TEXT,
    place TEXT,
    health INTEGER,
    flash_duration REAL,
    equip_value INTEGER,
    armor INTEGER,
    has_helmet INTEGER,
    has_defuser INTEGER,
    -- A tabela nasceu guardando só o humano (a demo só trazia ele). A fonte
    -- 'events' traz os 10 jogadores, então passou a precisar dizer quem é
    -- quem. Linhas antigas ficam com NULL, e NULL significa "é o humano" —
    -- por isso quem consulta usa COALESCE(is_human, 1).
    player_name TEXT,
    is_human INTEGER
);

-- Flash sofrida, uma linha por evento player_blind. Tabela própria porque a
-- duração aqui é exata e discreta; pra demo o mesmo dado só existe como
-- salto de flash_duration entre amostras, e as duas coisas não somam do
-- mesmo jeito (ver stats.match_loadout).
CREATE TABLE IF NOT EXISTS player_blinds (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    tick INTEGER,
    attacker_name TEXT,
    attacker_side TEXT,
    victim_name TEXT,
    victim_side TEXT,
    victim_is_human INTEGER,
    duration REAL
);

-- Contadores do próprio engine (CSMatchStats_t), um registro por round por
-- jogador. O plugin emite o ACUMULADO da partida a cada round e a ingestão
-- guarda aqui o DELTA do round — entry, clutch, multi-kill, precisão e
-- utility contados pelo jogo, não derivados por janela de tique em
-- stats.py. Só existe na fonte 'events'.
CREATE TABLE IF NOT EXISTS round_stats (
    match_id INTEGER NOT NULL REFERENCES matches(id),
    round_num INTEGER,
    player_name TEXT,
    is_human INTEGER,
    side TEXT,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    damage INTEGER,
    headshot_kills INTEGER,
    objective INTEGER,
    live_time INTEGER,
    shots_fired INTEGER,
    shots_on_target INTEGER,
    entry_count INTEGER,
    entry_wins INTEGER,
    clutch_1v1_count INTEGER,
    clutch_1v1_wins INTEGER,
    clutch_1v2_count INTEGER,
    clutch_1v2_wins INTEGER,
    multi_2k INTEGER,
    multi_3k INTEGER,
    multi_4k INTEGER,
    multi_5k INTEGER,
    utility_count INTEGER,
    utility_successes INTEGER,
    utility_enemies INTEGER,
    utility_damage INTEGER,
    flash_count INTEGER,
    flash_successes INTEGER,
    enemies_flashed INTEGER,
    equipment_value INTEGER,
    money_saved INTEGER,
    cash_earned INTEGER,
    kill_reward INTEGER,
    -- Estes dois são estado no fim do round, não delta: dinheiro em caixa e
    -- quanto foi gasto no round, que o jogo já dá por round.
    money INTEGER,
    cash_spent_round INTEGER
);
"""

# Nenhuma tabela filha tinha índice: só existia o UNIQUE implícito de
# matches.demo_name. Toda consulta de stats.py filtra por match_id, e
# _clear_match_children (reingestão) apaga por match_id — sem índice isso é
# varredura completa. Com 165k linhas em player_positions o custo já era
# visível, e o radar da tela de partida faz lookup por (match_id, round_num,
# tick), daí a terceira coluna no índice de posições.
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_rounds_match   ON rounds(match_id, round_num);
CREATE INDEX IF NOT EXISTS idx_kills_match    ON kills(match_id, round_num);
CREATE INDEX IF NOT EXISTS idx_kills_tick     ON kills(match_id, tick);
CREATE INDEX IF NOT EXISTS idx_damages_match  ON damages(match_id, round_num);
CREATE INDEX IF NOT EXISTS idx_pos_match      ON player_positions(match_id, round_num, tick);
CREATE INDEX IF NOT EXISTS idx_matches_played ON matches(played_at);
CREATE INDEX IF NOT EXISTS idx_blinds_match   ON player_blinds(match_id, round_num);
CREATE INDEX IF NOT EXISTS idx_rstats_match   ON round_stats(match_id, round_num);
"""


def _s(value):
    """Converte steamid pra string, preservando None (bots costumam vir sem steamid)."""
    return None if value is None else str(value)


def _bomb_site(event):
    """"A"/"B" de um bomb_planted vindo do plugin.

    O campo `site` do evento do jogo é o ÍNDICE DE ENTIDADE do alvo da bomba
    (valores vistos: 370, 3956), não 0/1 — a leitura antiga assumia 0=A/1=B e
    por isso gravou NULL em todos os rounds de origem 'events'. O plugin passou
    a mandar `place`, o nome que o jogo dá à região ("BombsiteA"), que é o que
    dá pra normalizar. O fallback em 0/1 fica pra não perder nada de um JSONL
    gravado por plugin antigo.
    """
    place = (event.get("place") or "").strip().lower()
    if place.endswith("a"):
        return "A"
    if place.endswith("b"):
        return "B"
    site = event.get("site")
    return "A" if site == 0 else "B" if site == 1 else None


def _is_human(name, steamid, identity: PlayerIdentity) -> bool:
    """Prefere comparação por steamid (estável a troca de nick); cai pra
    nome quando a identidade não tem steamid resolvido (modo native, ou
    matchzy sem correspondência no match_config)."""
    if identity.has_steamid:
        return steamid is not None and str(steamid) == identity.steamid
    return name == identity.name


def _is_human_named(name, identity: PlayerIdentity, is_bot=None) -> bool:
    """Versão por NOME, pros eventos do plugin que não carregam steamid
    (snapshot, freeze_end, round_stats, player_blind).

    Existe porque _is_human prefere steamid e, numa identidade resolvida via
    match_config (modo MatchZy), devolveria False pra todos esses eventos —
    marcando o próprio jogador como bot em player_positions e round_stats.

    Aqui o nome basta: é o nick in-game que o servidor reporta, o mesmo de
    identity.name. is_bot entra como trava — o projeto roda sempre 1 humano
    contra bots, então um bot não é o humano nem que o nick coincida."""
    if is_bot:
        return False
    return name is not None and name == identity.name


_NEW_MATCH_COLUMNS = {
    "source": "TEXT DEFAULT 'demo'",
    "agg_kills": "INTEGER",
    "agg_deaths": "INTEGER",
    "agg_assists": "INTEGER",
    "agg_damage": "INTEGER",
    "agg_hs_kills": "INTEGER",
    "agg_shots_fired": "INTEGER",
    "agg_shots_hit": "INTEGER",
    # Placar do ponto de vista do humano. score_ct/score_t continuam sendo
    # rounds por LADO, que num MR12 não são o placar de ninguém (os times
    # trocam de lado no intervalo) — ver docs/features/M0.5-placar.md.
    "score_mine": "INTEGER",
    "score_theirs": "INTEGER",
    "score_source": "TEXT",
    "outcome": "TEXT",
    # Tamanho da série (1/3/5 -> BO1/BO3/BO5), lido do match_config.json no
    # momento da ingestão (ver watcher.on_matchzy_map_finished). NULL em
    # partidas ingeridas antes desta coluna existir — não dá pra
    # reconstruir isso retroativamente.
    "series_num_maps": "INTEGER",
}

_NEW_EVENT_COLUMNS = {
    # 1 = evento ocorrido depois da primeira morte do humano no round, ou
    # seja, com ele controlando um bot (takeover). Não conta pro K/D dele.
    "post_mortem": "INTEGER DEFAULT 0",
}

# Só em damages. Fica fora de _NEW_EVENT_COLUMNS porque kills não tem dano.
_NEW_DAMAGE_COLUMNS = {
    # O valor que a fonte reportou, antes do corte por vida restante — ver
    # clamp_damage_health. Guardado pra que o recálculo seja idempotente e
    # pra não destruir o dado bruto.
    "dmg_health_raw": "INTEGER",
}

# Vida de um jogador no começo do round. Não há cura em competitivo, então o
# total de dano de vida que uma vítima pode sofrer numa vida é isto.
MAX_HEALTH = 100


def clamp_damage_health(damages_rows):
    """Corta o dano de vida pelo que a vítima ainda tinha de vida.

    As duas fontes reportam o dano BRUTO da bala, não a vida que ela tirou.
    Medido numa partida real em 23/09/2026: uma kill registrou 136 de dano
    num jogador que tinha no máximo 100 de vida. Somando o bruto, o ADR saía
    18% acima do que o próprio engine contabiliza (1614 contra 1370 em 10
    rounds, ~20 de excesso por kill) — e é o número capado que a HLTV e o
    Leetify usam, então o nosso nunca foi comparável com as referências.

    O acumulado é por (round, vítima) e atravessa atacantes: se um bot já
    tirou 80 de vida, o seu tiro de 100 conta 20. Por isso a ordem de
    processamento é por tique, não a ordem em que as linhas chegaram.

    LINHA SEM VÍTIMA IDENTIFICADA NÃO É CORTADA. Na fonte demo o awpy deixa
    victim_name/victim_steamid nulos na maioria das linhas (335 de 362 numa
    partida do banco) — sem saber em quem o tiro acertou, todas cairiam no
    mesmo balde de 100 e a partida inteira seria cortada em 85%. Preferir o
    dano bruto a um número inventado: quem não tem como ser corrigido fica
    como está, e a limitação é da fonte, não do cálculo.

    Devolve linhas com o dano cortado na posição de dmg_health e o valor
    original acrescentado no fim. Funciona com a tupla de 12 campos (antes
    de mark_post_mortem) e com a de 13 (depois).
    """
    acumulado = {}                     # (round_num, vítima) -> vida já tirada
    cortado = [0] * len(damages_rows)

    def ordem(i):
        r = damages_rows[i]
        return (r[0] if r[0] is not None else -1,
                r[1] if r[1] is not None else -1,
                i)

    for i in sorted(range(len(damages_rows)), key=ordem):
        row = damages_rows[i]
        bruto = row[8] or 0
        # steamid primeiro: é estável a troca de nick. Bot costuma vir sem.
        vitima = row[5] or row[4]
        if not vitima:
            cortado[i] = bruto
            continue
        chave = (row[0], vitima)
        ja_tirado = acumulado.get(chave, 0)
        real = max(0, min(bruto, MAX_HEALTH - ja_tirado))
        acumulado[chave] = ja_tirado + real
        cortado[i] = real

    return [
        row[:8] + (cortado[i],) + row[9:] + (row[8],)
        for i, row in enumerate(damages_rows)
    ]

_NEW_ROUND_COLUMNS = {
    # Lado do humano NESTE round, vindo do round_start do plugin. É o que
    # permite converter winner_side em vitória/derrota do humano.
    "human_side": "TEXT",
    # 0 = round que não conta pro placar (round fantasma da janela de
    # rebalanceamento de bots, round abortado por restart).
    "counted": "INTEGER DEFAULT 1",
    # Fim do freeze time. É a âncora certa pra ler o equipamento do round:
    # antes disso a compra ainda está acontecendo, depois já entra arma
    # trocada/recolhida do chão. Só a ingestão de .dem preenche (o plugin não
    # manda esse tick) — NULL nas partidas de origem 'events'.
    "freeze_end_tick": "INTEGER",
}

_NEW_POSITION_COLUMNS = {
    # Vindas de PLAYER_PROPS. NULL nas partidas ingeridas antes de
    # 21/09/2026, quando o parse era feito sem player_props — não dá pra
    # reconstruir sem reprocessar a demo.
    "flash_duration": "REAL",
    "equip_value": "INTEGER",
    "armor": "INTEGER",
    "has_helmet": "INTEGER",
    "has_defuser": "INTEGER",
    # Vindas da fonte 'events' (plugin v0.3.0), que grava os 10 jogadores e
    # não só o humano. NULL nas linhas antigas = humano.
    "player_name": "TEXT",
    "is_human": "INTEGER",
}


def _migrate_columns(conn, table, new_columns):
    """Adiciona colunas novas em bancos já existentes — CREATE TABLE IF NOT
    EXISTS não altera uma tabela que já existe, então isso cobre esse caso."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, decl in new_columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _migrate_matches_columns(conn):
    _migrate_columns(conn, "matches", _NEW_MATCH_COLUMNS)


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    _migrate_columns(conn, "matches", _NEW_MATCH_COLUMNS)
    _migrate_columns(conn, "rounds", _NEW_ROUND_COLUMNS)
    _migrate_columns(conn, "kills", _NEW_EVENT_COLUMNS)
    _migrate_columns(conn, "damages", _NEW_EVENT_COLUMNS)
    _migrate_columns(conn, "damages", _NEW_DAMAGE_COLUMNS)
    _migrate_columns(conn, "player_positions", _NEW_POSITION_COLUMNS)
    # Depois das migrações de coluna: CREATE INDEX IF NOT EXISTS é idempotente,
    # então isso também cria os índices em bancos antigos na primeira abertura.
    conn.executescript(INDEXES)
    conn.commit()
    return conn


def parse_and_store(demo_path, meta, db_path, identity: PlayerIdentity,
                    force: bool = False):
    demo_path = Path(demo_path)
    demo_name = demo_path.stem

    conn = init_db(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, played_at FROM matches WHERE demo_name = ?", (demo_name,))
    existing = cur.fetchone()
    reingest_id = None
    keep_played_at = None
    if existing:
        if not force:
            print(f"[PARSER] {demo_name} já está no banco (match_id={existing[0]}), pulando.")
            conn.close()
            return existing[0]
        reingest_id, keep_played_at = existing
        print(f"[PARSER] Reprocessando {demo_name} (match_id={reingest_id}).")
        _clear_match_children(cur, reingest_id)

    print(f"[PARSER] Parseando {demo_path} ...")
    dem = Demo(str(demo_path))
    # Sem player_props o awpy extrai só 6 propriedades e descarta flash,
    # equipamento e colete. Ver PLAYER_PROPS.
    dem.parse(player_props=PLAYER_PROPS)

    # Ticks do humano primeiro: é deles que sai o lado dele em cada round,
    # necessário pro placar por time (os lados trocam no intervalo).
    if identity.has_steamid and "steamid" in dem.ticks.columns:
        human_ticks = dem.ticks.filter(pl.col("steamid").cast(pl.Utf8) == identity.steamid)
    else:
        human_ticks = dem.ticks.filter(pl.col("name") == identity.name)

    side_counts = {}
    for t in human_ticks.iter_rows(named=True):
        side = t["side"]
        if not side:
            continue
        side_counts.setdefault(t["round_num"], Counter())[side] += 1
    human_side_by_round = {
        rn: c.most_common(1)[0][0] for rn, c in side_counts.items() if c
    }

    rounds_by_num = {}
    for r in dem.rounds.iter_rows(named=True):
        rounds_by_num[r["round_num"]] = {
            "winner_side": r["winner"], "reason": r["reason"],
            "bomb_plant": int(bool(r["bomb_plant"])), "bomb_site": r["bomb_site"],
            "start_tick": r["start"], "end_tick": r["end"],
            "freeze_end_tick": r["freeze_end"],
        }

    # Tuplas montadas SEM match_id, na mesma ordem do caminho de eventos, pra
    # que mark_post_mortem enxergue os mesmos índices nos dois caminhos. O
    # match_id é prefixado só na hora do INSERT.
    kills_rows = [
        (
            k["round_num"], k["tick"],
            k["attacker_name"], _s(k["attacker_steamid"]), k["attacker_side"],
            k["victim_name"], _s(k["victim_steamid"]), k["victim_side"],
            k["weapon"], int(bool(k["headshot"])), k["distance"],
            int(_is_human(k["attacker_name"], k["attacker_steamid"], identity)),
            int(_is_human(k["victim_name"], k["victim_steamid"], identity)),
        )
        for k in dem.kills.iter_rows(named=True)
    ]
    damages_rows = [
        (
            d["round_num"], d["tick"],
            d["attacker_name"], _s(d["attacker_steamid"]),
            d["victim_name"], _s(d["victim_steamid"]),
            d["weapon"], d["hitgroup"], d["dmg_health"], d["dmg_armor"],
            int(_is_human(d["attacker_name"], d["attacker_steamid"], identity)),
            int(_is_human(d["victim_name"], d["victim_steamid"], identity)),
        )
        for d in dem.damages.iter_rows(named=True)
    ]
    # Mesmo takeover de bot do caminho de eventos: ao morrer, o jogador
    # assume um companheiro e o controlador mantém a identidade dele.
    kills_rows, damages_rows = mark_post_mortem(kills_rows, damages_rows)
    # Depois do post_mortem e antes do INSERT: o corte não depende de quem
    # causou o dano, só de quanta vida a vítima ainda tinha.
    damages_rows = clamp_damage_health(damages_rows)

    round_nums = sorted(rounds_by_num)
    counted, reconciliado = mark_counted_rounds(
        rounds_by_num, kills_rows, damages_rows, human_side_by_round
    )
    rounds_rows = [
        (rn, rounds_by_num[rn]["winner_side"], rounds_by_num[rn]["reason"],
         rounds_by_num[rn]["bomb_plant"], rounds_by_num[rn]["bomb_site"],
         rounds_by_num[rn]["start_tick"], rounds_by_num[rn]["freeze_end_tick"],
         rounds_by_num[rn]["end_tick"],
         human_side_by_round.get(rn), int(counted[rn]))
        for rn in round_nums
    ]

    # score_ct/score_t são rounds por LADO — informação válida, mas não o
    # placar de ninguém num MR12. O placar de verdade é score_mine/theirs.
    score_ct = meta.get("score_ct")
    score_t = meta.get("score_t")
    if score_ct is None or score_t is None:
        score_ct = sum(1 for r in rounds_rows if r[1] == "ct" and r[8])
        score_t = sum(1 for r in rounds_rows if r[1] == "t" and r[8])
    score_mine, score_theirs, score_source = team_score(
        rounds_by_num, human_side_by_round, counted, reconciliado
    )
    outcome = outcome_from_score(score_mine, score_theirs)

    minutes = meta.get("minutes")
    if minutes is None and rounds_rows:
        ticks_start = [r[5] for r in rounds_rows if r[5] is not None]
        ticks_end = [r[6] for r in rounds_rows if r[6] is not None]
        if ticks_start and ticks_end:
            minutes = round((max(ticks_end) - min(ticks_start)) / 64 / 60)

    print(f"[PARSER] Placar reconstruído: {score_mine} x {score_theirs} "
          f"({outcome}, fonte={score_source}); por lado CT {score_ct} : TR {score_t}.")

    played_at = keep_played_at or datetime.now().isoformat(timespec="seconds")
    if reingest_id is not None:
        cur.execute(
            """UPDATE matches SET map=?, played_at=?, score_ct=?, score_t=?,
                                   score_mine=?, score_theirs=?, score_source=?, outcome=?,
                                   duration_minutes=?, demo_path=?, player_name=?,
                                   series_num_maps=?
               WHERE id=?""",
            (
                meta.get("map"), played_at, score_ct, score_t,
                score_mine, score_theirs, score_source, outcome,
                minutes, str(demo_path), identity.name, meta.get("series_num_maps"),
                reingest_id,
            ),
        )
        match_id = reingest_id
    else:
        cur.execute(
            """INSERT INTO matches (demo_name, map, played_at, score_ct, score_t,
                                     score_mine, score_theirs, score_source, outcome,
                                     duration_minutes, demo_path, player_name, series_num_maps)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                demo_name, meta.get("map"), played_at,
                score_ct, score_t, score_mine, score_theirs, score_source, outcome,
                minutes, str(demo_path), identity.name, meta.get("series_num_maps"),
            ),
        )
        match_id = cur.lastrowid
    cur.executemany(
        """INSERT INTO rounds (match_id, round_num, winner_side, reason, bomb_plant, bomb_site,
                                start_tick, freeze_end_tick, end_tick, human_side, counted)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in rounds_rows],
    )

    cur.executemany(
        """INSERT INTO kills (match_id, round_num, tick, attacker_name, attacker_steamid, attacker_side,
                               victim_name, victim_steamid, victim_side, weapon, headshot, distance,
                               attacker_is_human, victim_is_human, post_mortem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in kills_rows],
    )
    cur.executemany(
        """INSERT INTO damages (match_id, round_num, tick, attacker_name, attacker_steamid,
                                 victim_name, victim_steamid, weapon, hitgroup, dmg_health, dmg_armor,
                                 attacker_is_human, victim_is_human, post_mortem, dmg_health_raw)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in damages_rows],
    )

    if identity.has_steamid and "steamid" in dem.ticks.columns:
        human_ticks = dem.ticks.filter(pl.col("steamid").cast(pl.Utf8) == identity.steamid)
    else:
        human_ticks = dem.ticks.filter(pl.col("name") == identity.name)
    # Os nomes de saída de algumas props diferem do que se pede ao awpy
    # (fix_common_names): armor_value vira armor. Ver PLAYER_PROPS.
    def _bool(value):
        return None if value is None else int(bool(value))

    positions_rows = [
        (match_id, t["round_num"], t["tick"], t["X"], t["Y"], t["Z"], t["side"],
         t["place"], t["health"],
         t.get("flash_duration"), t.get("current_equip_value"), t.get("armor"),
         _bool(t.get("has_helmet")), _bool(t.get("has_defuser")))
        for t in human_ticks.iter_rows(named=True)
    ]
    cur.executemany(
        """INSERT INTO player_positions (match_id, round_num, tick, x, y, z, side, place, health,
                                          flash_duration, equip_value, armor, has_helmet, has_defuser)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        positions_rows,
    )

    conn.commit()
    conn.close()

    print(
        f"[PARSER] match_id={match_id}: {len(rounds_rows)} rounds, {len(kills_rows)} kills, "
        f"{len(damages_rows)} damages, {len(positions_rows)} posições de '{identity.name}'"
    )
    return match_id


def store_match_from_csv(csv_path, meta, db_path, identity: PlayerIdentity):
    """
    Ingestão alternativa via o CSV de stats que a própria MatchZy já
    escreve ao fim de cada mapa (docker/stats-live/<matchid>/
    match_data_map<N>_<matchid>.csv) — usada no fluxo Docker enquanto o
    bug de eventos de combate faltando na demo GOTV (player_death/
    player_hurt/weapon_fire/round_officially_ended) não é resolvido.

    Diferente de parse_and_store (via awpy/.dem), esse CSV só tem
    estatísticas agregadas da partida inteira por jogador — sem detalhe
    de round, kill a kill ou posição. Por isso não popula rounds/kills/
    damages/player_positions; score_ct/score_t/duration_minutes ficam
    None (não tem como derivar isso do CSV) e as colunas agg_* carregam
    o que dá pra mostrar no relatório (ver report.py).
    """
    csv_path = Path(csv_path)
    demo_name = meta.get("demo_name") or csv_path.stem

    conn = init_db(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM matches WHERE demo_name = ?", (demo_name,))
    existing = cur.fetchone()
    if existing:
        print(f"[PARSER] {demo_name} já está no banco (match_id={existing[0]}), pulando.")
        conn.close()
        return existing[0]

    print(f"[PARSER] Lendo stats de {csv_path} ...")
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    row = None
    if identity.has_steamid:
        row = next((r for r in rows if r.get("steamid64") == identity.steamid), None)
    if row is None:
        row = next((r for r in rows if r.get("name") == identity.name), None)

    if row is None:
        print(f"[PARSER] Jogador '{identity.name}' não encontrado em {csv_path}, pulando.")
        conn.close()
        return None

    def _int(key):
        value = row.get(key, "")
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return None

    cur.execute(
        """INSERT INTO matches (demo_name, map, played_at, score_ct, score_t, duration_minutes,
                                 demo_path, player_name, source,
                                 agg_kills, agg_deaths, agg_assists, agg_damage, agg_hs_kills,
                                 agg_shots_fired, agg_shots_hit)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'csv', ?, ?, ?, ?, ?, ?, ?)""",
        (
            demo_name,
            meta.get("map"),
            datetime.now().isoformat(timespec="seconds"),
            None,
            None,
            None,
            str(csv_path),
            identity.name,
            _int("kills"),
            _int("deaths"),
            _int("assists"),
            _int("damage"),
            _int("head_shot_kills"),
            _int("shots_fired_total"),
            _int("shots_on_target_total"),
        ),
    )
    match_id = cur.lastrowid
    conn.commit()
    conn.close()

    print(f"[PARSER] match_id={match_id}: stats agregadas de '{identity.name}' gravadas (fonte: csv)")
    return match_id


# mp_maxrounds 24 (server-configs/cfg/gamemode_competitive_server.cfg) => MR12:
# 12 rounds por metade, e quem chega a 13 fecha o mapa.
ROUNDS_PER_HALF = 12
CLINCH_SCORE = ROUNDS_PER_HALF + 1


def mark_counted_rounds(rounds_by_num, kills_rows, damages_rows, human_side_by_round):
    """Decide quais rounds contam pro placar. Devolve (counted, reconciliado).

    Dois tipos de round entram no stream sem terem sido jogados:

    - **Round fantasma**: zero mortes e zero danos. Nasce da janela em que o
      start_match rebalanceia os bots (bot_quota 0 / bot_kick / adds) DEPOIS
      do css_start — o humano fica sozinho de um lado, o engine encerra o
      round na hora e o IsLive() do plugin, que só olha WarmupPeriod, aceita.
    - **Round abortado**: round_start sem round_end, de um restart no meio.

    O problema: às vezes o engine CONTOU o round fantasma no placar oficial
    (visto na Ancient, onde a partida começou 1x0) e às vezes descartou. Nada
    no stream distingue os dois casos — falta o placar autoritativo do jogo.
    A saída é o invariante do formato: num mapa MR12 encerrado alguém chega a
    13. Se depois dos descartes ninguém chega, o fantasma mais recente era
    legítimo e volta a contar.

    Esta reconciliação é uma muleta. Ela morre no dia em que o plugin emitir
    TotalRoundsPlayed e o placar dos times — aí o fantasma vira simplesmente
    "o round em que o placar não mudou".
    """
    deaths = Counter(k[0] for k in kills_rows)
    hurts = Counter(d[0] for d in damages_rows)

    counted = {}
    for rn, r in rounds_by_num.items():
        if r["winner_side"] is None:
            counted[rn] = False  # abortado: começou e nunca terminou
        elif deaths[rn] == 0 and hurts[rn] == 0:
            counted[rn] = False  # fantasma: ninguém sequer tomou dano
        else:
            counted[rn] = True

    def best_score():
        mine, theirs, _, _ = _tally(rounds_by_num, human_side_by_round, counted)
        return max(mine, theirs)

    reconciliado = False
    dropped_phantoms = sorted(
        rn for rn, ok in counted.items()
        if not ok and rounds_by_num[rn]["winner_side"] is not None
    )
    # Só reconcilia se a partida parece encerrada (alguém perto do clinch) —
    # uma partida abandonada no meio legitimamente não chega a 13.
    while dropped_phantoms and best_score() == CLINCH_SCORE - 1:
        rn = dropped_phantoms.pop()
        counted[rn] = True
        reconciliado = True
        print(f"  [PLACAR] Round {rn} parecia fantasma, mas sem ele ninguém "
              f"chega a {CLINCH_SCORE} — o engine contou esse round. Revertido.")

    for rn, ok in sorted(counted.items()):
        if not ok:
            motivo = ("abortado (sem round_end)"
                      if rounds_by_num[rn]["winner_side"] is None
                      else "fantasma (0 mortes, 0 danos)")
            print(f"  [PLACAR] Round {rn} não conta: {motivo}.")

    return counted, reconciliado


def _tally(rounds_by_num, human_side_by_round, counted):
    """(meus rounds, rounds deles, rounds sem lado conhecido, rounds contados)."""
    mine = theirs = unknown = total = 0
    for rn, r in rounds_by_num.items():
        if not counted.get(rn):
            continue
        winner = r["winner_side"]
        if not winner:
            continue
        total += 1
        side = human_side_by_round.get(rn)
        if not side:
            unknown += 1
        elif side == winner:
            mine += 1
        else:
            theirs += 1
    return mine, theirs, unknown, total


def team_score(rounds_by_num, human_side_by_round, counted, reconciliado=False):
    """Placar do ponto de vista do humano.

    É a única conta que faz sentido num MR12: os times trocam de lado no
    intervalo, então somar rounds por LADO ao longo da partida inteira
    mistura os rounds do humano com os do adversário.
    """
    mine, theirs, unknown, total = _tally(rounds_by_num, human_side_by_round, counted)
    if total == 0:
        return None, None, None
    if unknown:
        # Round sem lado conhecido fica de fora em vez de ser chutado — um
        # número errado é pior que um número marcado como incompleto.
        print(f"  [AVISO] {unknown} round(s) sem lado do humano; placar parcial.")
        source = "rounds-partial"
    elif reconciliado:
        source = "rounds-reconciled"
    else:
        source = "rounds"
    return mine, theirs, source


def outcome_from_score(mine, theirs):
    if mine is None or theirs is None:
        return None
    return "win" if mine > theirs else "loss" if theirs > mine else "tie"


TICKRATE = 64

# Armas cujo dano chega DEPOIS de sair da mão: uma utility lançada em vida
# pode matar depois da morte de quem lançou, e o MatchZy (com razão) credita
# a kill. A janela é curta e por arma — sem teto, uma granada lançada pelo
# jogador JÁ controlando um bot seria creditada a ele indevidamente.
DELAYED_WEAPON_WINDOW_S = {
    # explosão é praticamente instantânea depois que a granada assenta
    "hegrenade": 1,
    "flashbang": 1,
    "smokegrenade": 1,
    "decoy": 1,
    # fogo queima por alguns segundos
    "inferno": 4,
    "molotov": 4,
    "incgrenade": 4,
    "firebomb": 4,
}


def mark_post_mortem(kills_rows, damages_rows):
    """Marca eventos ocorridos depois da primeira morte do humano no round.

    O projeto é 1 humano vs bots, e ao morrer o jogador assume um bot
    companheiro — o controlador mantém a identidade dele, então todo abate
    e toda morte subsequente no mesmo round entram no stream como se
    fossem do humano. Isso inflava o K/D: 28/24 contra os 22/18 que o
    próprio MatchZy registrou no Dust2.

    Com esta marcação os três mapas da série 44 batem exatamente com o CSV
    do MatchZy (22/18, 12/9, 13/8).

    Devolve (kills_rows, damages_rows) com a flag anexada ao fim de cada tupla.
    """
    first_death = {}
    for k in kills_rows:
        round_num, tick, victim_is_human = k[0], k[1], k[12]
        if not victim_is_human or tick is None:
            continue
        if round_num not in first_death or tick < first_death[round_num]:
            first_death[round_num] = tick

    def is_post(round_num, tick, attacker_is_human, weapon):
        dead_at = first_death.get(round_num)
        if dead_at is None or tick is None or tick <= dead_at:
            return False
        if attacker_is_human:
            window = DELAYED_WEAPON_WINDOW_S.get((weapon or "").lower())
            if window is not None and (tick - dead_at) <= window * TICKRATE:
                return False  # utility lançada em vida, dentro da janela dela
        return True

    kills_out = [
        k + (int(is_post(k[0], k[1], k[11], k[8])),) for k in kills_rows
    ]
    damages_out = [
        d + (int(is_post(d[0], d[1], d[10], d[6])),) for d in damages_rows
    ]
    n = sum(k[-1] for k in kills_out)
    if n:
        print(f"  [K/D] {n} evento(s) de kill marcados como pós-morte "
              f"(humano controlando bot) e fora do K/D dele.")
    return kills_out, damages_out


def _clear_match_children(cur, match_id):
    """Apaga as linhas filhas de uma partida pra reingestão. NÃO apaga a
    linha de matches: o id é usado em deep link (#match-<id>) e nos
    recordes pessoais do report, então ele é preservado e atualizado."""
    for table in ("rounds", "kills", "damages", "player_positions",
                  "player_blinds", "round_stats"):
        cur.execute(f"DELETE FROM {table} WHERE match_id = ?", (match_id,))


# Ordem das colunas de round_stats depois de (match_id, round_num, player_name,
# is_human, side). Precisa bater com o CREATE TABLE.
_ROUND_STAT_FIELDS = (
    "kills", "deaths", "assists", "damage", "headshot_kills", "objective", "live_time",
    "shots_fired", "shots_on_target",
    "entry_count", "entry_wins",
    "clutch_1v1_count", "clutch_1v1_wins", "clutch_1v2_count", "clutch_1v2_wins",
    "multi_2k", "multi_3k", "multi_4k", "multi_5k",
    "utility_count", "utility_successes", "utility_enemies", "utility_damage",
    "flash_count", "flash_successes", "enemies_flashed",
    "equipment_value", "money_saved", "cash_earned", "kill_reward",
    "money", "cash_spent_round",
)

# Estes dois já são estado do round (dinheiro em caixa, gasto no round) e não
# acumulado da partida — subtrair o round anterior daria lixo.
_ROUND_STAT_ABSOLUTE = frozenset({"money", "cash_spent_round"})


def _participa(side, is_human) -> bool:
    """Se essa entrada de jogador é de alguém que está de fato jogando.

    O bot do GOTV/SourceTV aparece em Utilities.GetPlayers() junto com os
    jogadores e chega aqui com o nome do servidor ("CS2 Tracker - Spike
    MatchZy"), sem time, sem pawn e com todos os contadores zerados.
    Confirmado ao vivo em 23/09/2026 — sem filtro ele entra em round_stats e
    vira um adversário na matriz de duelos que nunca luta.

    O critério é não ter time: quem joga sempre está em 't' ou 'ct' enquanto
    o round está ao vivo, e só gravamos ao vivo. O humano nunca é descartado,
    nem que o lado venha vazio — perder o loadout dele por causa de um campo
    ausente seria pior do que deixar passar uma linha estranha.
    """
    return bool(is_human) or bool(side)


def _round_stats_deltas(round_stats_raw):
    """Transforma o acumulado-da-partida que o plugin manda a cada round no
    valor DO round.

    O plugin emite CSMatchStats_t inteiro no fim de cada round, e esses campos
    crescem durante a partida. O delta é contra o round anterior DAQUELE
    jogador, não contra o round anterior em geral: bot que entrou no meio da
    partida começa do zero no round em que aparece.

    Delta negativo vira 0. Acontece de verdade quando o jogo zera as stats
    (troca de lado no intervalo, em algumas configurações) — nesse caso o
    acumulado cai e a subtração daria número negativo, que não significa nada
    como "o que rendeu neste round".
    """
    anterior = {}       # nome -> {campo: acumulado no round anterior}
    linhas = []
    for round_num in sorted(round_stats_raw):
        for nome, is_human, side, bruto in round_stats_raw[round_num]:
            prev = anterior.get(nome, {})
            valores = []
            for campo in _ROUND_STAT_FIELDS:
                atual = bruto.get(campo)
                if campo in _ROUND_STAT_ABSOLUTE or atual is None:
                    valores.append(atual)
                    continue
                valores.append(max(0, atual - (prev.get(campo) or 0)))
            linhas.append((round_num, nome, int(bool(is_human)), side or None, *valores))
            anterior[nome] = {c: bruto.get(c) for c in _ROUND_STAT_FIELDS}
    return linhas


def store_match_from_events(events_path, meta, db_path, identity: PlayerIdentity,
                            force: bool = False):
    """
    Ingestão via o JSONL escrito ao vivo pelo plugin Cs2TrackerEvents
    (CounterStrikeSharp) — docker/plugins-src/Cs2TrackerEvents. Cada linha
    é um evento (round_start/round_end/player_death/player_hurt/
    bomb_planted/bomb_defused) capturado direto dos hooks server-side,
    contornando o bug de combate faltando na demo GOTV (ver
    store_match_from_csv). Diferente do CSV agregado da MatchZy, aqui a
    gente tem detalhe por round e por evento — popula rounds/kills/damages
    igual ao fluxo antigo via awpy (parse_and_store), só que a fonte é
    o servidor ao vivo, não o .dem.

    Desde o plugin v0.3.0 também popula:

    - player_positions, de duas origens. O `snapshot` (2 Hz) dá o trajeto;
      o `player_death` carrega a posição do matador e da vítima no tique
      exato da kill. É a segunda que importa pro heatmap: stats.match_positions
      casa kill com posição por igualdade de tique, e uma amostra a cada 32
      tiques nunca cairia no tique da kill.
    - player_blinds, do `player_blind` — flash sofrida, com duração exata.
    - round_stats, do `round_stats` — contadores do engine. O plugin manda o
      acumulado da partida a cada round; aqui vira delta por round.
    - rounds.freeze_end_tick e o loadout (equipamento/armadura/kit), do
      `freeze_end`, que é o instante canônico do "o que cada um comprou".
    """
    events_path = Path(events_path)
    demo_name = meta.get("demo_name") or events_path.stem

    conn = init_db(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, played_at FROM matches WHERE demo_name = ?", (demo_name,))
    existing = cur.fetchone()
    reingest_id = None
    keep_played_at = None
    if existing:
        if not force:
            print(f"[PARSER] {demo_name} já está no banco (match_id={existing[0]}), pulando.")
            conn.close()
            return existing[0]
        reingest_id, keep_played_at = existing
        print(f"[PARSER] Reprocessando {demo_name} (match_id={reingest_id}).")
        _clear_match_children(cur, reingest_id)

    print(f"[PARSER] Lendo eventos de {events_path} ...")
    events = []
    bad_lines = 0
    # utf-8-sig, não utf-8: o plugin escreve o arquivo com BOM, e ele fica
    # colado na PRIMEIRA linha — que é sempre o round_start do round 1.
    # Lendo como utf-8 puro, essa linha morria no JSONDecodeError abaixo e
    # o round 1 perdia start_tick e human_side.
    with open(events_path, encoding="utf-8-sig") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                bad_lines += 1
                print(f"  [AVISO] linha {lineno} ilegível, ignorada: {exc}")
    if bad_lines:
        print(f"  [AVISO] {bad_lines} linha(s) descartada(s) em {events_path.name}.")

    if not events:
        print(f"[PARSER] Nenhum evento em {events_path}, pulando.")
        conn.close()
        return None

    rounds_by_num = {}
    kills_rows = []
    damages_rows = []
    positions_raw = []   # [(origem, tupla)] — ver add_position
    blinds_rows = []
    # round_num -> [ (nome, is_human, side, {campo: acumulado}) ], como veio do
    # plugin. O delta por round é calculado depois de ler tudo.
    round_stats_raw = {}
    human_side_by_round = {}  # round_num -> "ct"/"t", vindo do round_start (ver plugin)

    def round_entry(round_num):
        return rounds_by_num.setdefault(round_num, {
            "winner_side": None, "reason": None, "bomb_plant": 0, "bomb_site": None,
            "start_tick": None, "end_tick": None, "freeze_end_tick": None,
        })

    def add_position(round_num, tick, pos, name, is_human, side, health=None,
                     equip_value=None, armor=None, has_helmet=None, has_defuser=None,
                     origem="amostra"):
        """Uma linha de player_positions. pos é o objeto {x,y,z,place} do
        plugin, ou None quando o dado é só de loadout (freeze_end) e não de
        posição — nesse caso x/y/z ficam NULL em vez de 0, pra não desenhar
        o jogador no canto do mapa (stats.match_positions descarta 0,0 mas a
        bounding box de quem normaliza por bbox não tem como saber).

        `origem` separa o que veio de um evento (posição no tique exato) do
        que veio da amostragem de trajeto. Quando uma kill cai justo num tique
        de amostragem, o mesmo jogador gera as duas — e as duas sobreviveriam,
        porque o `place` de cada uma é diferente (o evento traz o callout do
        momento). Ver a deduplicação logo antes do INSERT."""
        positions_raw.append((origem, (
            round_num, tick,
            pos.get("x") if pos else None,
            pos.get("y") if pos else None,
            pos.get("z") if pos else None,
            side or None,
            pos.get("place") if pos else None,
            health, None, equip_value, armor, has_helmet, has_defuser,
            name, int(bool(is_human)),
        )))

    for e in events:
        etype = e.get("type")
        round_num = e.get("round_num")
        tick = e.get("tick")

        if etype == "round_start":
            r = round_entry(round_num)
            r["start_tick"] = tick
            if e.get("human_side"):
                human_side_by_round[round_num] = e["human_side"]
        elif etype == "round_end":
            r = round_entry(round_num)
            r["winner_side"] = e.get("winner") or None
            r["reason"] = e.get("reason")
            r["end_tick"] = tick
        elif etype == "bomb_planted":
            r = round_entry(round_num)
            r["bomb_plant"] = 1
            r["bomb_site"] = _bomb_site(e)
        elif etype == "freeze_end":
            r = round_entry(round_num)
            r["freeze_end_tick"] = tick
            for p in e.get("players") or []:
                nome = p.get("name")
                if not _participa(p.get("side"),
                                  _is_human_named(nome, identity, p.get("is_bot"))):
                    continue   # bot do GOTV — ver _participa
                # Os dois campos vêm do plugin porque não está documentado
                # qual dos dois o jogo já preencheu neste instante; o primeiro
                # não-nulo e não-zero ganha.
                equip = p.get("equip_freeze_end") or p.get("equip_round_start")
                add_position(
                    round_num, tick, None, nome,
                    _is_human_named(nome, identity, p.get("is_bot")), p.get("side"),
                    equip_value=equip,
                    armor=p.get("armor"),
                    has_helmet=int(bool(p.get("has_helmet"))) if p.get("has_helmet") is not None else None,
                    has_defuser=int(bool(p.get("has_defuser"))) if p.get("has_defuser") is not None else None,
                )
        elif etype == "snapshot":
            for p in e.get("players") or []:
                nome = p.get("n")
                if not _participa(p.get("s"),
                                  _is_human_named(nome, identity, p.get("b"))):
                    continue
                add_position(
                    round_num, tick,
                    {"x": p.get("x"), "y": p.get("y"), "z": p.get("z"), "place": p.get("p_")},
                    nome, _is_human_named(nome, identity, p.get("b")), p.get("s"),
                    health=p.get("h"),
                )
        elif etype == "round_stats":
            round_stats_raw[round_num] = [
                (p.get("name"), humano, p.get("side"), p)
                for p in (e.get("players") or [])
                for humano in [_is_human_named(p.get("name"), identity, p.get("is_bot"))]
                if _participa(p.get("side"), humano)
            ]
        elif etype == "player_blind":
            nome = e.get("victim_name")
            blinds_rows.append((
                round_num, tick,
                e.get("attacker_name"), e.get("attacker_side") or None,
                nome, e.get("victim_side") or None,
                int(_is_human_named(nome, identity)),
                e.get("duration"),
            ))
        elif etype == "player_death":
            atacante = e.get("attacker_name")
            vitima = e.get("victim_name")
            atacante_humano = _is_human(atacante, e.get("attacker_steamid"), identity)
            vitima_humana = _is_human(vitima, e.get("victim_steamid"), identity)
            kills_rows.append((
                round_num, tick,
                atacante, e.get("attacker_steamid"), e.get("attacker_side") or None,
                vitima, e.get("victim_steamid"), e.get("victim_side") or None,
                e.get("weapon"), int(bool(e.get("headshot"))), e.get("distance"),
                int(atacante_humano), int(vitima_humana),
            ))
            # Posição no tique exato da kill — é o que faz o heatmap funcionar
            # sem depender de cair numa amostra do snapshot.
            if e.get("attacker_pos"):
                add_position(round_num, tick, e["attacker_pos"], atacante,
                             atacante_humano, e.get("attacker_side"), origem="evento")
            if e.get("victim_pos"):
                add_position(round_num, tick, e["victim_pos"], vitima,
                             vitima_humana, e.get("victim_side"), health=0,
                             origem="evento")
        elif etype == "player_hurt":
            damages_rows.append((
                round_num, tick,
                e.get("attacker_name"), e.get("attacker_steamid"),
                e.get("victim_name"), e.get("victim_steamid"),
                e.get("weapon"), e.get("hitgroup"), e.get("dmg_health"), e.get("dmg_armor"),
                int(_is_human(e.get("attacker_name"), e.get("attacker_steamid"), identity)),
                int(_is_human(e.get("victim_name"), e.get("victim_steamid"), identity)),
            ))

    # Fallback pros rounds sem human_side vindo do round_start (raro — visto
    # no round 1 em teste real, provavelmente o time do humano ainda não
    # tinha sido atribuído no exato tick em que o evento disparou): infere
    # pelo primeiro kill do round envolvendo o humano.
    for k in kills_rows:
        rn = k[0]
        if rn in human_side_by_round:
            continue
        if k[11]:  # attacker_is_human
            human_side_by_round[rn] = k[4]
        elif k[12]:  # victim_is_human
            human_side_by_round[rn] = k[7]

    kills_rows, damages_rows = mark_post_mortem(kills_rows, damages_rows)
    # Depois do post_mortem e antes do INSERT: o corte não depende de quem
    # causou o dano, só de quanta vida a vítima ainda tinha.
    damages_rows = clamp_damage_health(damages_rows)

    round_nums = sorted(rounds_by_num)
    counted, reconciliado = mark_counted_rounds(
        rounds_by_num, kills_rows, damages_rows, human_side_by_round
    )

    # Mesma ordem de colunas do caminho da demo (parse_and_store), incluindo
    # freeze_end_tick entre start e end.
    rounds_rows = [
        (rn, rounds_by_num[rn]["winner_side"], rounds_by_num[rn]["reason"],
         rounds_by_num[rn]["bomb_plant"], rounds_by_num[rn]["bomb_site"],
         rounds_by_num[rn]["start_tick"], rounds_by_num[rn]["freeze_end_tick"],
         rounds_by_num[rn]["end_tick"],
         human_side_by_round.get(rn), int(counted[rn]))
        for rn in round_nums
    ]

    score_ct = sum(1 for r in rounds_rows if r[1] == "ct" and r[9])
    score_t = sum(1 for r in rounds_rows if r[1] == "t" and r[9])
    score_mine, score_theirs, score_source = team_score(
        rounds_by_num, human_side_by_round, counted, reconciliado
    )
    outcome = outcome_from_score(score_mine, score_theirs)

    minutes = None
    ticks_start = [r[5] for r in rounds_rows if r[5] is not None]
    ticks_end = [r[7] for r in rounds_rows if r[7] is not None]
    if ticks_start and ticks_end:
        minutes = round((max(ticks_end) - min(ticks_start)) / 64 / 60)

    print(f"[PARSER] Placar reconstruído: {score_mine} x {score_theirs} "
          f"({outcome}, fonte={score_source}); por lado CT {score_ct} : TR {score_t}.")

    # Na reingestão o played_at original é preservado — datetime.now() aqui
    # reescreveria a data de toda partida reprocessada pra hoje e embaralharia
    # o gráfico de tendência do report, que ordena por played_at.
    played_at = keep_played_at or datetime.now().isoformat(timespec="seconds")

    if reingest_id is not None:
        cur.execute(
            """UPDATE matches SET map=?, played_at=?, score_ct=?, score_t=?,
                                   score_mine=?, score_theirs=?, score_source=?, outcome=?,
                                   duration_minutes=?, demo_path=?, player_name=?, source='events',
                                   series_num_maps=?
               WHERE id=?""",
            (
                meta.get("map"), played_at, score_ct, score_t,
                score_mine, score_theirs, score_source, outcome,
                minutes, str(events_path), identity.name, meta.get("series_num_maps"),
                reingest_id,
            ),
        )
        match_id = reingest_id
    else:
        cur.execute(
            """INSERT INTO matches (demo_name, map, played_at, score_ct, score_t,
                                     score_mine, score_theirs, score_source, outcome,
                                     duration_minutes, demo_path, player_name, source,
                                     series_num_maps)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'events', ?)""",
            (
                demo_name, meta.get("map"), played_at,
                score_ct, score_t, score_mine, score_theirs, score_source, outcome,
                minutes, str(events_path), identity.name, meta.get("series_num_maps"),
            ),
        )
        match_id = cur.lastrowid

    cur.executemany(
        """INSERT INTO rounds (match_id, round_num, winner_side, reason, bomb_plant, bomb_site,
                                start_tick, freeze_end_tick, end_tick, human_side, counted)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in rounds_rows],
    )
    cur.executemany(
        """INSERT INTO kills (match_id, round_num, tick, attacker_name, attacker_steamid, attacker_side,
                               victim_name, victim_steamid, victim_side, weapon, headshot, distance,
                               attacker_is_human, victim_is_human, post_mortem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in kills_rows],
    )
    cur.executemany(
        """INSERT INTO damages (match_id, round_num, tick, attacker_name, attacker_steamid,
                                 victim_name, victim_steamid, weapon, hitgroup, dmg_health, dmg_armor,
                                 attacker_is_human, victim_is_human, post_mortem, dmg_health_raw)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in damages_rows],
    )

    # Linha sintética por round só pra alimentar _dominant_side_by_round
    # (report.py), que precisa do lado do humano em TODO round. Só entra nos
    # rounds em que o humano não deixou nenhuma posição real — antes o plugin
    # não mandava posição e isso valia sempre; hoje é exceção (round em que
    # ele não matou, não morreu e não apareceu em amostra nenhuma). x/y/z
    # ficam NULL e não 0,0,0 pra não desenhar ninguém no canto do mapa.
    # Uma kill que cai num tique de amostragem gera duas linhas do mesmo
    # jogador no mesmo tique. A do evento ganha: é a posição no instante
    # exato, e o callout dela é o do momento da kill. Sem isso o heatmap
    # desenha o ponto duas vezes — e DISTINCT na consulta não resolveria,
    # porque o `place` das duas difere.
    chaves_evento = {(t[0], t[1], t[13]) for origem, t in positions_raw
                     if origem == "evento"}
    positions_rows = [
        t for origem, t in positions_raw
        if origem == "evento" or (t[0], t[1], t[13]) not in chaves_evento
    ]

    rounds_com_posicao = {r[0] for r in positions_rows
                          if r[14] and r[2] is not None}
    positions_rows.extend(
        (rn, rounds_by_num[rn]["start_tick"] or 0, None, None, None, side, None,
         100, None, None, None, None, None, identity.name, 1)
        for rn, side in human_side_by_round.items()
        if rn not in rounds_com_posicao
    )
    cur.executemany(
        """INSERT INTO player_positions (match_id, round_num, tick, x, y, z, side, place,
                                          health, flash_duration, equip_value, armor,
                                          has_helmet, has_defuser, player_name, is_human)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in positions_rows],
    )
    cur.executemany(
        """INSERT INTO player_blinds (match_id, round_num, tick, attacker_name, attacker_side,
                                       victim_name, victim_side, victim_is_human, duration)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(match_id,) + row for row in blinds_rows],
    )

    round_stats_rows = _round_stats_deltas(round_stats_raw)
    cur.executemany(
        f"""INSERT INTO round_stats (match_id, round_num, player_name, is_human, side,
                                      {", ".join(_ROUND_STAT_FIELDS)})
            VALUES ({", ".join("?" * (5 + len(_ROUND_STAT_FIELDS)))})""",
        [(match_id,) + row for row in round_stats_rows],
    )

    conn.commit()
    conn.close()

    print(
        f"[PARSER] match_id={match_id}: {len(rounds_rows)} rounds, {len(kills_rows)} kills, "
        f"{len(damages_rows)} damages, {len(positions_rows)} posições, "
        f"{len(blinds_rows)} flashes sofridas, {len(round_stats_rows)} registros de "
        f"round_stats (fonte: events)"
    )
    return match_id


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Parser (awpy -> SQLite)")
    parser.add_argument("demo", help="Caminho do arquivo .dem")
    parser.add_argument("--map", required=True)
    parser.add_argument("--score-ct", required=True)
    parser.add_argument("--score-t", required=True)
    parser.add_argument("--minutes", required=True)
    parser.add_argument("--player", required=True, help="Nome do jogador humano (in-game) ou SteamID64")
    parser.add_argument("--match-config", default=None,
                         help="Caminho do match_config.json pra cruzar steamid<->nick (opcional, "
                              "usado quando disponível; sem ele cai pra comparação só por nome)")
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    meta = {
        "map": args.map,
        "score_ct": args.score_ct,
        "score_t": args.score_t,
        "minutes": args.minutes,
    }
    identity = resolve_identity(args.player, args.match_config)
    parse_and_store(args.demo, meta, args.db, identity)


if __name__ == "__main__":
    main()
