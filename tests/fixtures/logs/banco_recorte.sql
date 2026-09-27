-- Recorte da tabela matches do backup de 26/09 (cópia só leitura), card H1.1.
-- Mesmas colunas e mesma ordem do banco real (o ALTER TABLE deixou as novas no fim).
-- Linhas 13 e 14: série 45 de 19/09 (a 14 é a que ficou com demo_path do map1).
-- Linha 24: events_60_map0 de 26/09, a partida da tag jogavel-2026-09-26.
-- Anonimizado: player_name trocado por "Jogador".
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demo_name TEXT UNIQUE NOT NULL,
    map TEXT,
    played_at TEXT,
    score_ct INTEGER,
    score_t INTEGER,
    duration_minutes INTEGER,
    demo_path TEXT,
    player_name TEXT,
    source TEXT DEFAULT 'demo', agg_kills INTEGER, agg_deaths INTEGER, agg_assists INTEGER,
    agg_damage INTEGER, agg_hs_kills INTEGER, agg_shots_fired INTEGER, agg_shots_hit INTEGER,
    score_mine INTEGER, score_theirs INTEGER, score_source TEXT, outcome TEXT, series_num_maps INTEGER
);
INSERT INTO matches (id, demo_name, map, played_at, score_ct, score_t, demo_path, player_name,
                     source, score_mine, score_theirs, score_source, outcome, series_num_maps)
VALUES
 (13, 'events_45_map0', 'de_nuke', '2026-09-19T15:00:06', 12, 7,
  'docker\events-live\events_45_map0.jsonl', 'Jogador', 'events', 6, 13, 'rounds', 'loss', NULL),
 (14, 'events_45_map2', 'de_ancient', '2026-09-19T16:46:48', 11, 9,
  'docker\events-live\events_45_map1.jsonl', 'Jogador', 'events', 7, 13, 'rounds', 'loss', NULL),
 (24, 'events_60_map0', 'de_anubis', '2026-09-26T13:37:51', 3, 12,
  'docker\events-live\events_60_map0.jsonl', 'Jogador', 'events', 13, 2, 'rounds', 'win', 1);
