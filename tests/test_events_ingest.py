#!/usr/bin/env python3
"""
Testes da ingestão via plugin Cs2TrackerEvents v0.3.0 (parser.store_match_from_events).

O que estes testes seguram é o contrato entre o plugin e o banco. Três coisas
quebraram em silêncio antes e não podem voltar:

1. bomb_site saía sempre NULL porque o parser lia `site`, que é índice de
   entidade (370, 3956) e não 0/1. Agora lê `place` ("BombsiteA").
2. player_positions passou a guardar os 10 jogadores. Toda consulta que antes
   assumia "só tem o humano aqui" precisa filtrar — sem isso o lado dominante
   de cada round vira o dos 9 bots e o heatmap multiplica cada kill por 10.
3. Os eventos novos não carregam steamid, e _is_human prefere steamid. Numa
   identidade resolvida por match_config isso marcaria o próprio jogador como
   bot.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import parser as parser_mod
import stats
from identity import PlayerIdentity

HUMANO = "can1sh"
# Identidade COM steamid de propósito: é o modo MatchZy, e é o cenário em que
# a detecção por nome dos eventos novos precisa funcionar mesmo assim.
IDENT = PlayerIdentity(name=HUMANO, steamid="76561190000000001")
BOT = "Bot Kaiser"


def _jsonl(tmp_path, eventos, nome="current.jsonl"):
    caminho = tmp_path / nome
    caminho.write_text(
        "".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8"
    )
    return caminho


def _ingerir(tmp_path, eventos, mapa="de_mirage"):
    db = str(tmp_path / "t.db")
    caminho = _jsonl(tmp_path, eventos)
    match_id = parser_mod.store_match_from_events(
        caminho, {"map": mapa}, db, IDENT
    )
    return db, match_id


def _linhas(db, sql, *args):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def _snapshot(round_num, tick, *jogadores):
    """jogadores: tuplas (nome, is_bot, side, x, y)."""
    return {
        "type": "snapshot", "round_num": round_num, "tick": tick,
        "players": [
            {"n": n, "b": b, "s": s, "x": x, "y": y, "z": 0.0, "h": 100, "p_": "Mid"}
            for (n, b, s, x, y) in jogadores
        ],
    }


def _partida_minima():
    """Um round completo, com o humano em T matando um bot."""
    return [
        {"type": "round_start", "round_num": 1, "tick": 100, "human_side": "t"},
        {"type": "freeze_end", "round_num": 1, "tick": 200, "players": [
            {"name": HUMANO, "is_bot": False, "side": "t", "equip_freeze_end": 4700,
             "equip_round_start": 200, "armor": 100, "has_helmet": True,
             "has_defuser": False, "money": 1500},
            {"name": BOT, "is_bot": True, "side": "ct", "equip_freeze_end": 850,
             "equip_round_start": 0, "armor": 0, "has_helmet": False,
             "has_defuser": True, "money": 3200},
        ]},
        _snapshot(1, 232, (HUMANO, False, "t", 10.0, 20.0), (BOT, True, "ct", -50.0, 60.0)),
        {"type": "player_death", "round_num": 1, "tick": 555,
         "attacker_name": HUMANO, "attacker_steamid": IDENT.steamid, "attacker_side": "t",
         "victim_name": BOT, "victim_steamid": None, "victim_side": "ct",
         "weapon": "ak47", "headshot": True, "distance": 812.5,
         "attacker_pos": {"x": 11.0, "y": 21.0, "z": 0.0, "place": "Palace"},
         "victim_pos": {"x": -51.0, "y": 61.0, "z": 0.0, "place": "TSpawn"}},
        {"type": "round_end", "round_num": 1, "tick": 900,
         "winner": "t", "reason": "ct_killed"},
        {"type": "round_officially_ended", "round_num": 1, "tick": 950},
    ]


# --------------------------------------------------------------------------- #
# _bomb_site — o bug que deixou 266 rounds com NULL
# --------------------------------------------------------------------------- #

def test_bomb_site_le_place_e_ignora_indice_de_entidade():
    # 370 e 3956 são valores reais observados no campo `site`.
    assert parser_mod._bomb_site({"place": "BombsiteA", "site": 370}) == "A"
    assert parser_mod._bomb_site({"place": "BombsiteB", "site": 3956}) == "B"


def test_bomb_site_cai_para_0_1_quando_nao_ha_place():
    """JSONL gravado por plugin anterior ao v0.3.0 não tem `place`."""
    assert parser_mod._bomb_site({"site": 0}) == "A"
    assert parser_mod._bomb_site({"site": 1}) == "B"


def test_bomb_site_desconhecido_vira_none_em_vez_de_chute():
    assert parser_mod._bomb_site({"site": 370}) is None
    assert parser_mod._bomb_site({}) is None
    assert parser_mod._bomb_site({"place": ""}) is None


def test_bomb_site_chega_no_banco(tmp_path):
    eventos = _partida_minima()
    eventos.insert(-2, {"type": "bomb_planted", "round_num": 1, "tick": 700,
                        "player_name": HUMANO, "steamid": IDENT.steamid,
                        "site": 3956, "place": "BombsiteB"})
    db, mid = _ingerir(tmp_path, eventos)
    (linha,) = _linhas(db, "SELECT bomb_plant, bomb_site FROM rounds WHERE match_id=?", mid)
    assert linha["bomb_plant"] == 1
    assert linha["bomb_site"] == "B"


# --------------------------------------------------------------------------- #
# Identidade por nome nos eventos sem steamid
# --------------------------------------------------------------------------- #

def test_is_human_named_reconhece_o_humano_sem_steamid():
    """_is_human devolveria False aqui — a identidade tem steamid e o evento não."""
    assert parser_mod._is_human(HUMANO, None, IDENT) is False
    assert parser_mod._is_human_named(HUMANO, IDENT) is True


def test_is_human_named_nao_confunde_bot_de_mesmo_nick():
    assert parser_mod._is_human_named(HUMANO, IDENT, is_bot=True) is False


def test_posicoes_marcam_humano_e_bot_corretamente(tmp_path):
    db, mid = _ingerir(tmp_path, _partida_minima())
    linhas = _linhas(
        db, "SELECT DISTINCT player_name, is_human FROM player_positions WHERE match_id=?", mid
    )
    marcas = {l["player_name"]: l["is_human"] for l in linhas}
    assert marcas[HUMANO] == 1
    assert marcas[BOT] == 0


# --------------------------------------------------------------------------- #
# Posição: a kill carrega a sua própria, no tique exato
# --------------------------------------------------------------------------- #

def test_player_death_grava_posicao_no_tique_da_kill(tmp_path):
    db, mid = _ingerir(tmp_path, _partida_minima())
    linhas = _linhas(
        db, "SELECT player_name, x, y, place, health FROM player_positions "
            "WHERE match_id=? AND tick=555 ORDER BY player_name", mid
    )
    por_nome = {l["player_name"]: l for l in linhas}
    assert por_nome[HUMANO]["place"] == "Palace"
    assert (por_nome[HUMANO]["x"], por_nome[HUMANO]["y"]) == (11.0, 21.0)
    # A vítima entra com health 0 — ela acabou de morrer.
    assert por_nome[BOT]["health"] == 0


def test_match_positions_casa_a_kill_sem_depender_da_amostragem(tmp_path):
    """O tique da kill (555) não é múltiplo de 32; se o casamento dependesse da
    amostragem de trajeto, este teste devolveria zero pontos."""
    db, mid = _ingerir(tmp_path, _partida_minima())
    resultado = stats.match_positions(db, mid)
    assert resultado is not None
    assert len(resultado["points"]) == 1
    ponto = resultado["points"][0]
    assert ponto["type"] == "kill"
    assert (ponto["x"], ponto["y"]) == (11.0, 21.0)


def test_match_positions_nao_multiplica_a_kill_pelos_jogadores_do_tique(tmp_path):
    """Kill num tique que TAMBÉM tem amostra dos 10 jogadores. Sem o filtro de
    is_human o join devolveria uma cópia por jogador presente."""
    eventos = _partida_minima()
    # 555 é o tique da kill: coloca uma amostra exatamente nele.
    eventos.insert(-2, _snapshot(1, 555,
                                 (HUMANO, False, "t", 11.0, 21.0),
                                 (BOT, True, "ct", -51.0, 61.0)))
    db, mid = _ingerir(tmp_path, eventos)
    resultado = stats.match_positions(db, mid)
    assert len(resultado["points"]) == 1


def test_bbox_ignora_linhas_sem_posicao(tmp_path):
    """As linhas de freeze_end existem só pelo loadout e têm x/y NULL."""
    db, mid = _ingerir(tmp_path, _partida_minima())
    resultado = stats.match_positions(db, mid)
    assert resultado["bbox"]["min_x"] == 10.0
    assert resultado["bbox"]["max_x"] == 11.0


# --------------------------------------------------------------------------- #
# Lado dominante — o bot não pode decidir de que lado você jogou
# --------------------------------------------------------------------------- #

def test_lado_dominante_ignora_os_bots(tmp_path):
    """9 linhas de bot CT contra 1 do humano T no mesmo round. O lado do humano
    é T, e sem o filtro a contagem bruta diria CT."""
    eventos = _partida_minima()
    bots = [(f"Bot {i}", True, "ct", float(i), float(i)) for i in range(9)]
    eventos.insert(-2, _snapshot(1, 264, (HUMANO, False, "t", 10.0, 20.0), *bots))
    db, mid = _ingerir(tmp_path, eventos)

    conn = sqlite3.connect(db)
    try:
        assert stats._dominant_side_by_round(conn, mid) == {1: "t"}
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Loadout, vindo do freeze_end
# --------------------------------------------------------------------------- #

def test_loadout_vem_do_freeze_end_e_e_do_humano(tmp_path):
    db, mid = _ingerir(tmp_path, _partida_minima())
    loadout = stats.match_loadout(db, mid)
    assert loadout[1]["equip_value"] == 4700          # não 850, do bot
    assert loadout[1]["armor"] == 100
    assert loadout[1]["has_helmet"] is True
    assert loadout[1]["has_defuser"] is False


def test_freeze_end_tick_chega_nos_rounds(tmp_path):
    db, mid = _ingerir(tmp_path, _partida_minima())
    (linha,) = _linhas(db, "SELECT freeze_end_tick FROM rounds WHERE match_id=?", mid)
    assert linha["freeze_end_tick"] == 200


# --------------------------------------------------------------------------- #
# Flash sofrida
# --------------------------------------------------------------------------- #

def test_duas_flashes_no_mesmo_round_somam(tmp_path):
    """É exatamente o caso que a heurística de saltos de flash_duration errava:
    ela contaria só a diferença entre as duas, não as duas."""
    eventos = _partida_minima()
    for tick, dur in ((300, 3.5), (400, 2.0)):
        eventos.insert(-2, {"type": "player_blind", "round_num": 1, "tick": tick,
                            "attacker_name": BOT, "attacker_side": "ct",
                            "victim_name": HUMANO, "victim_side": "t",
                            "duration": dur})
    db, mid = _ingerir(tmp_path, eventos)
    loadout = stats.match_loadout(db, mid)
    assert loadout[1]["flashes"] == 2
    assert loadout[1]["blind_time"] == 5.5


def test_flash_que_pegou_o_bot_nao_conta_como_sua(tmp_path):
    eventos = _partida_minima()
    eventos.insert(-2, {"type": "player_blind", "round_num": 1, "tick": 300,
                        "attacker_name": HUMANO, "attacker_side": "t",
                        "victim_name": BOT, "victim_side": "ct", "duration": 4.0})
    db, mid = _ingerir(tmp_path, eventos)
    loadout = stats.match_loadout(db, mid)
    assert loadout[1]["flashes"] == 0
    assert loadout[1]["blind_time"] == 0.0


# --------------------------------------------------------------------------- #
# round_stats — acumulado do engine vira delta por round
# --------------------------------------------------------------------------- #

def _bruto(**kwargs):
    base = {c: 0 for c in parser_mod._ROUND_STAT_FIELDS}
    base.update(kwargs)
    return base


def test_delta_subtrai_o_round_anterior_do_mesmo_jogador():
    bruto = {
        1: [(HUMANO, True, "t", _bruto(kills=2, damage=180, shots_fired=30))],
        2: [(HUMANO, True, "t", _bruto(kills=5, damage=400, shots_fired=71))],
    }
    linhas = parser_mod._round_stats_deltas(bruto)
    campos = parser_mod._ROUND_STAT_FIELDS
    r2 = dict(zip(campos, linhas[1][4:]))
    assert r2["kills"] == 3
    assert r2["damage"] == 220
    assert r2["shots_fired"] == 41


def test_delta_e_por_jogador_nao_global():
    """Bot que só aparece no round 2 começa do zero, não herda o acumulado
    do humano."""
    bruto = {
        1: [(HUMANO, True, "t", _bruto(kills=4))],
        2: [(HUMANO, True, "t", _bruto(kills=4)),
            (BOT, False, "ct", _bruto(kills=1))],
    }
    linhas = parser_mod._round_stats_deltas(bruto)
    idx_kills = 4 + parser_mod._ROUND_STAT_FIELDS.index("kills")
    por_chave = {(l[0], l[1]): l[idx_kills] for l in linhas}
    assert por_chave[(2, HUMANO)] == 0
    assert por_chave[(2, BOT)] == 1


def test_delta_negativo_vira_zero():
    """O jogo zera as stats em algumas trocas de lado; o acumulado cai e a
    subtração daria negativo, que não significa nada como valor do round."""
    bruto = {
        1: [(HUMANO, True, "t", _bruto(kills=9))],
        2: [(HUMANO, True, "ct", _bruto(kills=1))],
    }
    linhas = parser_mod._round_stats_deltas(bruto)
    idx_kills = 4 + parser_mod._ROUND_STAT_FIELDS.index("kills")
    assert linhas[1][idx_kills] == 0


def test_money_passa_direto_por_nao_ser_acumulado():
    bruto = {
        1: [(HUMANO, True, "t", _bruto(money=1500, cash_spent_round=3200))],
        2: [(HUMANO, True, "t", _bruto(money=800, cash_spent_round=4750))],
    }
    linhas = parser_mod._round_stats_deltas(bruto)
    campos = parser_mod._ROUND_STAT_FIELDS
    assert dict(zip(campos, linhas[1][4:]))["money"] == 800
    assert dict(zip(campos, linhas[1][4:]))["cash_spent_round"] == 4750


def test_round_stats_chega_no_banco_com_delta(tmp_path):
    eventos = _partida_minima()
    eventos += [
        {"type": "round_stats", "round_num": 1, "tick": 950, "players": [
            {"name": HUMANO, "is_bot": False, "side": "t",
             "kills": 1, "damage": 100, "entry_count": 1, "entry_wins": 1,
             "shots_fired": 12, "shots_on_target": 5, "money": 3200},
        ]},
        {"type": "round_start", "round_num": 2, "tick": 1000, "human_side": "t"},
        {"type": "round_end", "round_num": 2, "tick": 1800,
         "winner": "ct", "reason": "t_killed"},
        {"type": "round_stats", "round_num": 2, "tick": 1850, "players": [
            {"name": HUMANO, "is_bot": False, "side": "t",
             "kills": 3, "damage": 275, "entry_count": 2, "entry_wins": 1,
             "shots_fired": 40, "shots_on_target": 14, "money": 1400},
        ]},
    ]
    db, mid = _ingerir(tmp_path, eventos)
    linhas = _linhas(
        db, "SELECT round_num, is_human, kills, damage, entry_count, entry_wins, "
            "shots_fired, shots_on_target, money FROM round_stats "
            "WHERE match_id=? ORDER BY round_num", mid
    )
    assert len(linhas) == 2
    assert linhas[0]["is_human"] == 1
    assert linhas[1]["kills"] == 2            # 3 acumulado - 1 do round anterior
    assert linhas[1]["damage"] == 175
    assert linhas[1]["entry_wins"] == 0       # entrou no entry e perdeu
    assert linhas[1]["shots_on_target"] == 9
    assert linhas[1]["money"] == 1400         # absoluto, não delta


# --------------------------------------------------------------------------- #
# Reingestão
# --------------------------------------------------------------------------- #

def test_reingestao_limpa_as_tabelas_novas(tmp_path):
    """Sem player_blinds/round_stats em _clear_match_children, reprocessar uma
    partida duplicaria as linhas em vez de substituir."""
    eventos = _partida_minima()
    eventos.append({"type": "round_stats", "round_num": 1, "tick": 950, "players": [
        {"name": HUMANO, "is_bot": False, "side": "t", "kills": 1},
    ]})
    eventos.insert(-3, {"type": "player_blind", "round_num": 1, "tick": 300,
                        "attacker_name": BOT, "attacker_side": "ct",
                        "victim_name": HUMANO, "victim_side": "t", "duration": 1.5})

    db = str(tmp_path / "t.db")
    caminho = _jsonl(tmp_path, eventos)
    parser_mod.store_match_from_events(caminho, {"map": "de_mirage"}, db, IDENT)
    parser_mod.store_match_from_events(caminho, {"map": "de_mirage"}, db, IDENT, force=True)

    for tabela in ("player_blinds", "round_stats", "player_positions", "kills"):
        (linha,) = _linhas(db, f"SELECT COUNT(*) AS n FROM {tabela}")
        assert linha["n"] > 0, tabela
    (blinds,) = _linhas(db, "SELECT COUNT(*) AS n FROM player_blinds")
    assert blinds["n"] == 1
    (rstats,) = _linhas(db, "SELECT COUNT(*) AS n FROM round_stats")
    assert rstats["n"] == 1


# --------------------------------------------------------------------------- #
# Degradação: JSONL de plugin antigo continua ingerindo
# --------------------------------------------------------------------------- #

def test_jsonl_sem_os_eventos_novos_ainda_funciona(tmp_path):
    """Compatibilidade pra trás: os 39 JSONL já arquivados não têm snapshot,
    freeze_end, round_stats nem player_blind."""
    eventos = [
        {"type": "round_start", "round_num": 1, "tick": 100, "human_side": "t"},
        {"type": "player_death", "round_num": 1, "tick": 555,
         "attacker_name": HUMANO, "attacker_steamid": IDENT.steamid, "attacker_side": "t",
         "victim_name": BOT, "victim_steamid": None, "victim_side": "ct",
         "weapon": "ak47", "headshot": False, "distance": 300.0},
        {"type": "round_end", "round_num": 1, "tick": 900,
         "winner": "t", "reason": "ct_killed"},
    ]
    db, mid = _ingerir(tmp_path, eventos)
    assert mid is not None
    (kills,) = _linhas(db, "SELECT COUNT(*) AS n FROM kills WHERE match_id=?", mid)
    assert kills["n"] == 1
    # Sem posição real, a aba do mapa some em vez de desenhar na origem.
    assert stats.match_positions(db, mid) is None
    # Mas o lado do humano continua conhecido, que é pro que a linha sintética serve.
    conn = sqlite3.connect(db)
    try:
        assert stats._dominant_side_by_round(conn, mid) == {1: "t"}
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Bot do GOTV/SourceTV
# --------------------------------------------------------------------------- #

GOTV = "CS2 Tracker - Spike MatchZy"


def test_bot_do_gotv_nao_entra_como_jogador(tmp_path):
    """Visto ao vivo em 23/09/2026: o bot do SourceTV aparece em
    Utilities.GetPlayers() com o nome do servidor, sem time, sem pawn e com
    tudo zerado — e virava um adversário na matriz de duelos que nunca luta."""
    eventos = _partida_minima()
    for e in eventos:
        if e["type"] == "freeze_end":
            e["players"].append({
                "name": GOTV, "is_bot": True, "side": "",
                "equip_freeze_end": 0, "equip_round_start": 0,
                "armor": 0, "has_helmet": False, "has_defuser": False, "money": 800,
            })
    eventos.append({"type": "round_stats", "round_num": 1, "tick": 950, "players": [
        {"name": HUMANO, "is_bot": False, "side": "t", "kills": 1},
        {"name": GOTV, "is_bot": True, "side": "", "kills": 0},
    ]})
    db, mid = _ingerir(tmp_path, eventos)

    nomes_pos = {l["player_name"] for l in _linhas(
        db, "SELECT DISTINCT player_name FROM player_positions WHERE match_id=?", mid)}
    nomes_rs = {l["player_name"] for l in _linhas(
        db, "SELECT DISTINCT player_name FROM round_stats WHERE match_id=?", mid)}
    assert GOTV not in nomes_pos
    assert GOTV not in nomes_rs
    assert HUMANO in nomes_pos and HUMANO in nomes_rs


def test_humano_sem_lado_nao_e_descartado():
    """A trava do filtro: perder o loadout do jogador porque o campo de time
    veio vazio seria pior do que deixar passar uma linha estranha."""
    assert parser_mod._participa("", True) is True
    assert parser_mod._participa(None, True) is True
    assert parser_mod._participa("", False) is False
    assert parser_mod._participa("ct", False) is True
