#!/usr/bin/env python3
"""
CS2 Tracker — Stats
=====================
Camada de cálculo pura (SQLite -> dict), sem HTML nenhum. Extraído de
report.py pra que a home (home.py) e o relatório (report.py) leiam os
mesmos números, sem risco de divergir num cálculo duplicado.
"""

MAP_ICON_OVERRIDES = {
    # A maioria dos ícones segue "{mapa}.png" — estas duas fogem do padrão
    # e não dá pra derivar por convenção.
    "dust2": "dust-2.png",
    "inferno": "inferno.webp",
}

MAP_LABEL_OVERRIDES = {
    "dust2": "Dust 2",
}

# Espelho do WEAPON_LABEL em JS dentro de templates/report.html — o
# relatório é renderizado no cliente (dados embutidos + JS) e a home é
# renderizada no servidor (Jinja), então a mesma tabela existe duas vezes
# por natureza da arquitetura. Mudar uma exige mudar a outra.
WEAPON_LABEL = {
    "hkp2000": "P2000", "glock": "Glock-18", "usp_silencer": "USP-S", "p250": "P250",
    "fiveseven": "Five-SeveN", "tec9": "Tec-9", "cz75a": "CZ75-Auto", "deagle": "Desert Eagle",
    "elite": "Dual Berettas", "revolver": "R8 Revolver",
    "mac10": "MAC-10", "mp9": "MP9", "mp7": "MP7", "mp5sd": "MP5-SD", "ump45": "UMP-45",
    "p90": "P90", "bizon": "PP-Bizon",
    "ak47": "AK-47", "m4a1": "M4A4", "m4a1_silencer": "M4A1-S", "famas": "FAMAS",
    "galilar": "Galil AR", "aug": "AUG", "sg556": "SG 553", "awp": "AWP", "ssg08": "SSG 08",
    "scar20": "SCAR-20", "g3sg1": "G3SG1",
    "nova": "Nova", "xm1014": "XM1014", "mag7": "MAG-7", "sawedoff": "Sawed-Off",
    "m249": "M249", "negev": "Negev",
    "hegrenade": "Granada HE", "flashbang": "Flashbang", "smokegrenade": "Smoke",
    "molotov": "Molotov", "inferno": "Incendiário/Molotov", "decoy": "Decoy",
    "knife": "Faca", "knife_t": "Faca", "planted_c4": "Bomba (C4)", "taser": "Zeus x27",
}


# Espelho de parser.TICKRATE e da janela de trade que o awpy usa por padrão
# (awpy.stats.kast.calculate_trades, trade_length_in_seconds=5.0). Definido
# aqui em vez de importado de parser.py de propósito: stats.py é camada pura
# e importar parser puxaria awpy+polars pra dentro da home e do wizard.
TICKRATE = 64
TRADE_WINDOW_TICKS = 5 * TICKRATE

# 5v5 é o único formato que o projeto monta (roster.Team tem players[5], e
# start_match.py preenche os dois lados com 5). Usado só para derivar quantos
# continuam vivos num round a partir das mortes — ver _clutches.
TEAM_SIZE = 5

# damages.hitgroup chega em DOIS formatos, por causa das duas fontes de
# ingestão: a demo (awpy) grava texto ("head", "left_arm"), e o plugin
# CounterStrikeSharp grava o enum numérico do engine como string ("1", "4").
# Conferido no banco: origem 'demo' só tem texto, origem 'events' só tem
# número. Normalizar aqui é o que permite somar as duas fontes na mesma tela.
_HITGROUP_NUMERIC = {
    "0": "generic", "1": "head", "2": "chest", "3": "stomach",
    "4": "left_arm", "5": "right_arm", "6": "left_leg", "7": "right_leg",
    "8": "gear",
}
# Regiões exibidas. Braços e pernas juntam os dois lados (a distinção
# esquerda/direita não muda decisão nenhuma do jogador), e "neck" — que só a
# demo produz, 2 ocorrências no banco — entra em cabeça por ser a mesma
# região de mira. generic/gear viram "outros": é onde cai dano de utility,
# que não tem região de acerto.
_HITGROUP_GROUP = {
    "head": "head", "neck": "head",
    "chest": "chest",
    "stomach": "stomach",
    "left_arm": "arms", "right_arm": "arms",
    "left_leg": "legs", "right_leg": "legs",
    "generic": "other", "gear": "other",
}
HITGROUP_LABEL = {
    "head": "Cabeça", "chest": "Peito", "stomach": "Estômago",
    "arms": "Braços", "legs": "Pernas", "other": "Outros",
}
HITGROUP_ORDER = ["head", "chest", "stomach", "arms", "legs", "other"]


def normalize_hitgroup(raw):
    """Devolve a região canônica (chave de HITGROUP_LABEL) ou None quando o
    valor não é reconhecido — ver _HITGROUP_NUMERIC pro porquê dos 2 formatos."""
    if raw is None:
        return None
    key = str(raw).strip().lower().replace(" ", "_")
    key = _HITGROUP_NUMERIC.get(key, key)
    return _HITGROUP_GROUP.get(key)


def map_slug(name):
    """de_mirage -> mirage. Mesma normalização que report.html faz em JS
    (fmtMap) — mantida em espelho pra bater nos dois lugares."""
    if not name:
        return "?"
    return name[3:] if name.startswith("de_") else name


def map_label(name):
    slug = map_slug(name)
    return MAP_LABEL_OVERRIDES.get(slug, slug.capitalize())


def weapon_label(weapon):
    return WEAPON_LABEL.get(weapon, weapon)


# As duas armas com silenciador reportam o nome da versão BASE no evento de
# dano, mas o próprio nome no evento de morte: a M4A1-S mata como
# "m4a1_silencer" e machuca como "m4a1"; a USP-S mata como "usp_silencer" e
# machuca como "hkp2000". Conferido no banco — são os dois únicos nomes que
# aparecem em kills e nunca em damages. Sem reconciliar isso, o quadro de
# armas mostra uma linha com kills e zero dano e outra com dano e zero kill.
#
# A reconciliação é pro lado do nome base porque é o único que as DUAS
# tabelas conhecem; em troca não dá pra separar M4A4 de M4A1-S no agregado,
# e o rótulo diz isso em vez de escolher uma das duas. O feed de kills e a
# kill mais longa NÃO passam por aqui: ali o evento de morte é a fonte e o
# nome exato da arma é informação boa.
WEAPON_CANONICAL = {
    "m4a1_silencer": "m4a1",
    "usp_silencer": "hkp2000",
}
WEAPON_MERGED_LABEL = {
    "m4a1": "M4A4 / M4A1-S",
    "hkp2000": "P2000 / USP-S",
}


def canonical_weapon(weapon):
    return WEAPON_CANONICAL.get(weapon, weapon)


def merged_weapon_label(weapon):
    """Rótulo do quadro de armas — usa o nome do par quando canonical_weapon
    juntou duas armas que o dado não separa."""
    return WEAPON_MERGED_LABEL.get(weapon) or weapon_label(weapon)


def map_icon_path(map_name):
    slug = map_slug(map_name)
    return MAP_ICON_OVERRIDES.get(slug, f"{slug}.png")


def map_bg_path(map_name):
    return f"bg-{map_slug(map_name)}.webp"


def weapon_icon_path(weapon):
    """assets/weapons/{weapon}.svg bate 1:1 com damages.weapon — ver
    docs/features/M3.5-home.md."""
    return f"weapons/{weapon}.svg"


def fetch_matches(conn):
    return conn.execute(
        """SELECT id, demo_name, map, played_at, score_ct, score_t,
                  score_mine, score_theirs, score_source, outcome,
                  duration_minutes, player_name,
                  source, agg_kills, agg_deaths, agg_assists, agg_damage, agg_hs_kills,
                  agg_shots_fired, agg_shots_hit, series_num_maps
           FROM matches ORDER BY played_at"""
    ).fetchall()


def _human_side_by_round(conn, match_id, rounds):
    """Lado do humano em cada round. Prefere rounds.human_side (gravado
    direto do round_start do plugin) e cai pro cálculo via player_positions
    pra partidas ingeridas antes dessa coluna existir."""
    from_rounds = {
        r["round_num"]: r["human_side"] for r in rounds if r["human_side"]
    }
    if from_rounds:
        return from_rounds
    return _dominant_side_by_round(conn, match_id)


def _team_score_from_rounds(rounds, human_side):
    """Placar do ponto de vista do humano, a partir dos rounds contados.

    Só serve de reserva pra partidas ainda não reprocessadas — o número
    bom vem de matches.score_mine/score_theirs, calculado na ingestão
    (ver parser.team_score). Devolve (None, None) quando falta lado em
    algum round: melhor não mostrar placar do que mostrar errado."""
    mine = theirs = 0
    for r in rounds:
        if not r["counted"] or not r["winner_side"]:
            continue
        side = human_side.get(r["round_num"])
        if not side:
            return None, None
        if side == r["winner_side"]:
            mine += 1
        else:
            theirs += 1
    if mine == 0 and theirs == 0:
        return None, None
    return mine, theirs


def _dominant_side_by_round(conn, match_id):
    """Lado que o jogador humano mais apareceu em cada round (via
    player_positions) — necessário pra comparar com rounds.winner_side,
    já que os lados trocam na metade da partida, e pra separar as
    estatísticas em Geral/CT/TR.

    O filtro de is_human não é detalhe: desde o plugin v0.3.0 a tabela guarda
    os 10 jogadores, e sem ele o lado "dominante" de todo round passaria a ser
    o dos 9 bots. Linhas antigas (fonte demo) têm is_human NULL e são todas do
    humano, daí o COALESCE."""
    side_counts = conn.execute(
        """SELECT round_num, side, COUNT(*) FROM player_positions
           WHERE match_id=? AND COALESCE(is_human, 1) = 1
           GROUP BY round_num, side""",
        (match_id,),
    ).fetchall()
    dominant = {}
    for round_num, side, count in side_counts:
        if round_num not in dominant or count > dominant[round_num][1]:
            dominant[round_num] = (side, count)
    return {r: side for r, (side, _count) in dominant.items()}


def _fetch_match_raw(conn, match_id):
    rounds = conn.execute(
        """SELECT round_num, winner_side, reason, bomb_plant, bomb_site,
                  human_side, COALESCE(counted, 1) AS counted
           FROM rounds WHERE match_id=? ORDER BY round_num""",
        (match_id,),
    ).fetchall()
    # post_mortem = evento depois da primeira morte do humano no round, ou
    # seja, ele controlando um bot. O evento continua existindo (aconteceu
    # no jogo), mas deixa de ser atribuído a ele — zerar as flags aqui faz
    # todo consumidor abaixo herdar a correção. Ver parser.mark_post_mortem.
    # attacker_side/victim_side NÃO levam o AND NOT post_mortem: eles
    # descrevem o que aconteceu no jogo (de que lado estava quem morreu),
    # não a quem o evento é atribuído. Zerá-los quebraria a contagem de
    # vivos por lado que _clutches e _kast_and_trades fazem.
    kills = conn.execute(
        """SELECT round_num, tick, attacker_name, victim_name, weapon, headshot, distance,
                  attacker_side, victim_side,
                  attacker_is_human AND NOT COALESCE(post_mortem, 0) AS attacker_is_human,
                  victim_is_human   AND NOT COALESCE(post_mortem, 0) AS victim_is_human
           FROM kills WHERE match_id=? ORDER BY tick""",
        (match_id,),
    ).fetchall()
    damages = conn.execute(
        """SELECT round_num, weapon, dmg_health, hitgroup,
                  attacker_is_human AND NOT COALESCE(post_mortem, 0) AS attacker_is_human,
                  victim_is_human   AND NOT COALESCE(post_mortem, 0) AS victim_is_human
           FROM damages WHERE match_id=?""",
        (match_id,),
    ).fetchall()
    return rounds, kills, damages


def _side_round_nums(rounds, dominant_side, side):
    if side is None:
        return {r["round_num"] for r in rounds}
    return {r["round_num"] for r in rounds if dominant_side.get(r["round_num"]) == side}


def _normalize_bomb_site(site):
    if not site:
        return None
    key = str(site).strip().lower().replace(" ", "")
    if key in ("a", "0", "bombsite_a", "bombsitea"):
        return "A"
    if key in ("b", "1", "bombsite_b", "bombsiteb"):
        return "B"
    if key.endswith("_a") or key.endswith("sitea"):
        return "A"
    if key.endswith("_b") or key.endswith("siteb"):
        return "B"
    return str(site)


def _first_kill_by_round(kills, round_nums):
    first = {}
    for k in kills:
        rn = k["round_num"]
        if rn not in round_nums:
            continue
        tick = k["tick"] if k["tick"] is not None else 0
        prev = first.get(rn)
        if prev is None or tick < (prev["tick"] if prev["tick"] is not None else 0):
            first[rn] = k
    return first


def _entry_counts(kills, round_nums):
    for_n = against_n = 0
    for k in _first_kill_by_round(kills, round_nums).values():
        if k["attacker_is_human"]:
            for_n += 1
        elif k["victim_is_human"]:
            against_n += 1
    return for_n, against_n


def _max_kill_streak(kills, round_nums):
    scoped = [k for k in kills if k["round_num"] in round_nums]
    scoped.sort(key=lambda k: (k["tick"] if k["tick"] is not None else 0))
    streak = best = 0
    for k in scoped:
        if k["attacker_is_human"]:
            streak += 1
            if streak > best:
                best = streak
        if k["victim_is_human"]:
            streak = 0
    return best


def _longest_kill(kills, round_nums):
    best = None
    for k in kills:
        if k["round_num"] not in round_nums or not k["attacker_is_human"]:
            continue
        if k["distance"] is None:
            continue
        if best is None or k["distance"] > best["distance"]:
            best = {
                "distance": round(k["distance"], 1),
                "weapon": k["weapon"],
                "opponent": k["victim_name"] or "bot",
                "round_num": k["round_num"],
            }
    return best


def _life_events(kills, dominant_side):
    events = []
    ordered = sorted(kills, key=lambda k: (k["tick"] if k["tick"] is not None else 0))
    for k in ordered:
        side = dominant_side.get(k["round_num"])
        if k["attacker_is_human"]:
            events.append({
                "tick": k["tick"],
                "round_num": k["round_num"],
                "type": "kill",
                "human_side": side,
            })
        if k["victim_is_human"]:
            events.append({
                "tick": k["tick"],
                "round_num": k["round_num"],
                "type": "death",
                "human_side": side,
            })
    return events


def _bombsites_for_round_nums(rounds, dominant_side, round_nums):
    acc = {}
    for r in rounds:
        if r["round_num"] not in round_nums or not r["bomb_plant"]:
            continue
        site = _normalize_bomb_site(r["bomb_site"])
        if not site:
            continue
        row = acc.setdefault(site, {"plants": 0, "wins": 0})
        row["plants"] += 1
        if dominant_side.get(r["round_num"]) == r["winner_side"]:
            row["wins"] += 1
    return [
        {
            "site": site,
            "plants": data["plants"],
            "wins": data["wins"],
            "win_pct": 100 * data["wins"] / data["plants"] if data["plants"] else 0.0,
        }
        for site, data in sorted(acc.items())
    ]


def _tick(kill):
    return kill["tick"] if kill["tick"] is not None else 0


def _kills_by_round(kills, round_nums):
    """Kills do recorte agrupadas por round e ordenadas por tick — base de
    KAST, trades e clutches, que são todos sensíveis à ordem dos eventos."""
    grouped = {}
    for k in kills:
        if k["round_num"] in round_nums:
            grouped.setdefault(k["round_num"], []).append(k)
    for rows in grouped.values():
        rows.sort(key=_tick)
    return grouped


# Fração mínima de kills com lado preenchido pra confiar em trades/clutches.
# As partidas ingeridas de .dem vêm quase sem lado (202 de 221 kills nulas no
# banco atual) porque o dataframe de kills do awpy não traz o time do bot;
# as ingeridas do plugin vêm 100% preenchidas. Abaixo do corte a métrica sai
# como None em vez de sair errada — ver _stats_for_round_nums.
_SIDES_MIN_COVERAGE = 0.9


def _sides_known(grouped):
    """True quando dá pra saber de que lado estava cada morto no recorte."""
    total = known = 0
    for rows in grouped.values():
        for k in rows:
            total += 1
            if k["victim_side"]:
                known += 1
    return bool(total) and (known / total) >= _SIDES_MIN_COVERAGE


def _kast_and_trades(rounds, grouped, dominant_side, round_nums, sides_known):
    """KAST e contagem de trades.

    KAST aqui é K/S/T: assist não existe em nenhuma das duas fontes de
    ingestão (nem o dataframe de kills do awpy nem o player_death do plugin
    trazem assistente), então a componente A fica de fora — quem consome
    precisa dizer isso na tela, e é o que `kast_has_assists=False` sinaliza.
    Sem lado dos mortos a componente T também cai, e aí KAST vira K/S puro:
    `kast_has_trades` diz qual das duas versões este número é.

    Trocado (traded_deaths): você morreu e alguém do seu lado matou o seu
    algoz dentro da janela. Trade feito (trade_kills): você matou alguém que
    acabara de matar um aliado seu, dentro da mesma janela."""
    kast_rounds = trade_kills = traded_deaths = 0

    for r in rounds:
        rn = r["round_num"]
        if rn not in round_nums:
            continue
        my_side = dominant_side.get(rn)
        events = grouped.get(rn, [])

        got_kill = any(k["attacker_is_human"] for k in events)
        my_death = next((k for k in events if k["victim_is_human"]), None)
        survived = my_death is None

        traded = False
        if my_death is not None and sides_known and my_side and my_death["attacker_name"]:
            killer = my_death["attacker_name"]
            t0 = _tick(my_death)
            for k in events:
                if k is my_death or not (t0 <= _tick(k) <= t0 + TRADE_WINDOW_TICKS):
                    continue
                if k["victim_name"] == killer and k["attacker_side"] == my_side:
                    traded = True
                    break
        if traded:
            traded_deaths += 1

        if got_kill or survived or traded:
            kast_rounds += 1

        if sides_known and my_side:
            for k in events:
                if not k["attacker_is_human"] or not k["victim_name"]:
                    continue
                t1 = _tick(k)
                for prev in events:
                    if prev is k or not (t1 - TRADE_WINDOW_TICKS <= _tick(prev) <= t1):
                        continue
                    if prev["attacker_name"] == k["victim_name"] and prev["victim_side"] == my_side:
                        trade_kills += 1
                        break

    return {
        "kast_rounds": kast_rounds,
        "trade_kills": trade_kills if sides_known else None,
        "traded_deaths": traded_deaths if sides_known else None,
    }


def _multi_kills(grouped):
    """Rounds com 2, 3, 4 e 5+ kills suas. 5+ entra no balde de 5 (ace) — com
    takeover de bot dá pra passar de 5 mortes num round, mas só a primeira
    vida conta (post_mortem), então isso é raro e não merece balde próprio."""
    buckets = {2: 0, 3: 0, 4: 0, 5: 0}
    for events in grouped.values():
        n = sum(1 for k in events if k["attacker_is_human"])
        if n >= 5:
            buckets[5] += 1
        elif n in buckets:
            buckets[n] += 1
    return {f"{n}k": count for n, count in buckets.items()}


def _clutches(rounds, grouped, dominant_side, round_nums, sides_known):
    """Situações em que você ficou por último vivo do seu lado, e quantos
    inimigos ainda havia nesse momento.

    Conta a partir da SUA vida: o takeover de bot faz você continuar jogando
    depois de morrer, mas esses eventos já saem marcados como post_mortem no
    resto do arquivo, então manter o mesmo corte aqui é o que deixa o número
    comparável com kills/deaths/ADR."""
    if not sides_known:
        return None
    acc = {}
    for r in rounds:
        rn = r["round_num"]
        if rn not in round_nums:
            continue
        my_side = dominant_side.get(rn)
        if not my_side:
            continue
        my_dead = enemy_dead = 0
        found = None
        for k in grouped.get(rn, []):
            side = k["victim_side"]
            if side == my_side:
                my_dead += 1
            elif side:
                enemy_dead += 1
            if k["victim_is_human"]:
                break  # você morreu: o que vier depois não é clutch seu
            if found is None and TEAM_SIZE - my_dead == 1:
                found = max(1, TEAM_SIZE - enemy_dead)
        if found is None:
            continue
        bucket = acc.setdefault(found, {"count": 0, "wins": 0})
        bucket["count"] += 1
        if r["winner_side"] == my_side:
            bucket["wins"] += 1
    return [
        {"vs": vs, "count": data["count"], "wins": data["wins"]}
        for vs, data in sorted(acc.items())
    ]


def _hitgroups_for_round_nums(damages, round_nums):
    """Onde os seus tiros acertam, por região. Vem de damages.hitgroup, que é
    gravado desde sempre e nunca foi lido por nenhuma tela."""
    acc = {}
    for d in damages:
        if d["round_num"] not in round_nums or not d["attacker_is_human"]:
            continue
        group = normalize_hitgroup(d["hitgroup"])
        if not group:
            continue
        bucket = acc.setdefault(group, {"hits": 0, "dmg": 0})
        bucket["hits"] += 1
        bucket["dmg"] += d["dmg_health"] or 0

    total_hits = sum(b["hits"] for b in acc.values())
    total_dmg = sum(b["dmg"] for b in acc.values())
    return [
        {
            "hitgroup": group,
            "label": HITGROUP_LABEL[group],
            "hits": acc[group]["hits"],
            "dmg": acc[group]["dmg"],
            "hit_pct": 100 * acc[group]["hits"] / total_hits if total_hits else 0.0,
            "dmg_pct": 100 * acc[group]["dmg"] / total_dmg if total_dmg else 0.0,
        }
        for group in HITGROUP_ORDER
        if group in acc
    ]


def _head_to_head(kills, round_nums):
    """Saldo de duelos contra cada adversário nominal.

    É o que nenhum tracker de mercado consegue fazer com partida de
    matchmaking: aqui os adversários são perfis de pro nomeados (F1.1), então
    "quantas vezes o arT te matou" é uma pergunta respondível. Sai direto de
    kills.attacker_name/victim_name, sem migração de schema (F6.2 do
    docs/features/M6-estatisticas.md).

    Fogo amigo fica de fora: com lado conhecido, kill em que os dois lados são
    iguais não é duelo. Suicídio/queda (attacker == victim) idem."""
    acc = {}
    for k in kills:
        if k["round_num"] not in round_nums:
            continue
        if k["attacker_name"] and k["attacker_name"] == k["victim_name"]:
            continue
        same_side = (
            k["attacker_side"] and k["victim_side"]
            and k["attacker_side"] == k["victim_side"]
        )
        if same_side:
            continue
        if k["attacker_is_human"] and k["victim_name"]:
            acc.setdefault(k["victim_name"], {"kills": 0, "deaths": 0})["kills"] += 1
        elif k["victim_is_human"] and k["attacker_name"]:
            acc.setdefault(k["attacker_name"], {"kills": 0, "deaths": 0})["deaths"] += 1

    rows = [
        {
            "opponent": name,
            "kills": data["kills"],
            "deaths": data["deaths"],
            "diff": data["kills"] - data["deaths"],
        }
        for name, data in acc.items()
    ]
    rows.sort(key=lambda r: (-r["diff"], -r["kills"], r["opponent"]))
    return rows


def _stats_for_round_nums(rounds, kills, damages, dominant_side, round_nums):
    scoped_rounds = [r for r in rounds if r["round_num"] in round_nums]
    rounds_played = len(scoped_rounds)
    if rounds_played == 0:
        return None

    scoped_kills = [k for k in kills if k["round_num"] in round_nums]
    scoped_damages = [d for d in damages if d["round_num"] in round_nums]

    my_kills = [k for k in scoped_kills if k["attacker_is_human"]]
    my_kills_count = len(my_kills)
    my_deaths_count = sum(1 for k in scoped_kills if k["victim_is_human"])
    hs_kills = sum(1 for k in my_kills if k["headshot"])
    my_dmg = sum(d["dmg_health"] or 0 for d in scoped_damages if d["attacker_is_human"])
    wins = sum(1 for r in scoped_rounds if dominant_side.get(r["round_num"]) == r["winner_side"])
    entry_for, entry_against = _entry_counts(kills, round_nums)
    entry_total = entry_for + entry_against

    grouped = _kills_by_round(kills, round_nums)
    sides_known = _sides_known(grouped)
    kast = _kast_and_trades(scoped_rounds, grouped, dominant_side, round_nums, sides_known)
    clutches = _clutches(scoped_rounds, grouped, dominant_side, round_nums, sides_known)
    clutch_count = sum(c["count"] for c in clutches) if clutches is not None else None
    clutch_wins = sum(c["wins"] for c in clutches) if clutches is not None else None

    return {
        "kills": my_kills_count,
        "deaths": my_deaths_count,
        "kd": my_kills_count / my_deaths_count if my_deaths_count else float(my_kills_count),
        "hs_pct": (100 * hs_kills / my_kills_count) if my_kills_count else 0.0,
        "hs_kills": hs_kills,
        "adr": my_dmg / rounds_played,
        "dmg_total": my_dmg,
        "rounds_played": rounds_played,
        "round_wins": wins,
        "round_win_pct": 100 * wins / rounds_played,
        "entry_for": entry_for,
        "entry_against": entry_against,
        "entry_pct": (100 * entry_for / entry_total) if entry_total else None,
        "max_streak": _max_kill_streak(kills, round_nums),
        # KAST é K/S/T — sem assist em nenhuma fonte, e sem T quando o lado
        # dos mortos não vem. As duas flags dizem o que este número é.
        "kast_rounds": kast["kast_rounds"],
        "kast_pct": 100 * kast["kast_rounds"] / rounds_played,
        "kast_has_assists": False,
        "kast_has_trades": sides_known,
        "trade_kills": kast["trade_kills"],
        "traded_deaths": kast["traded_deaths"],
        "multi_kills": _multi_kills(grouped),
        "clutches": clutches,
        "clutch_count": clutch_count,
        "clutch_wins": clutch_wins,
    }


def _weapons_for_round_nums(kills, damages, round_nums):
    scoped_kills = [k for k in kills if k["round_num"] in round_nums and k["attacker_is_human"]]
    scoped_damages = [d for d in damages if d["round_num"] in round_nums and d["attacker_is_human"]]

    # canonical_weapon junta os dois pares silenciado/base que kills e
    # damages nomeiam de formas diferentes — sem isso a M4A1-S aparece com
    # kills e dano zero. Ver WEAPON_CANONICAL.
    kills_by_weapon, hs_by_weapon, dmg_by_weapon = {}, {}, {}
    for k in scoped_kills:
        weapon = canonical_weapon(k["weapon"])
        kills_by_weapon[weapon] = kills_by_weapon.get(weapon, 0) + 1
        if k["headshot"]:
            hs_by_weapon[weapon] = hs_by_weapon.get(weapon, 0) + 1
    for d in scoped_damages:
        weapon = canonical_weapon(d["weapon"])
        dmg_by_weapon[weapon] = dmg_by_weapon.get(weapon, 0) + (d["dmg_health"] or 0)

    weapons = set(kills_by_weapon) | set(dmg_by_weapon)
    rows = []
    for w in weapons:
        kills_n = kills_by_weapon.get(w, 0)
        hs_n = hs_by_weapon.get(w, 0)
        rows.append({
            "weapon": w,
            "kills": kills_n,
            "headshots": hs_n,
            "hs_pct": (100 * hs_n / kills_n) if kills_n else None,
            "dmg": dmg_by_weapon.get(w, 0),
        })
    rows.sort(key=lambda r: (-r["kills"], -r["dmg"]))
    return rows


def _round_timeline(rounds, kills, dominant_side):
    kd_by_round = {}
    for k in kills:
        entry = kd_by_round.setdefault(k["round_num"], [0, 0])
        if k["attacker_is_human"]:
            entry[0] += 1
        if k["victim_is_human"]:
            entry[1] += 1

    first_kills = _first_kill_by_round(kills, {r["round_num"] for r in rounds})
    rows = []
    for r in rounds:
        round_num = r["round_num"]
        human_side = dominant_side.get(round_num)
        k, d = kd_by_round.get(round_num, (0, 0))
        result = "-" if human_side is None else ("win" if human_side == r["winner_side"] else "loss")
        fk = first_kills.get(round_num)
        if fk is None:
            entry_kind = None
        elif fk["attacker_is_human"]:
            entry_kind = "for"
        elif fk["victim_is_human"]:
            entry_kind = "against"
        else:
            entry_kind = "other"
        rows.append({
            "round_num": round_num,
            "winner_side": r["winner_side"],
            "reason": r["reason"],
            "bomb_plant": bool(r["bomb_plant"]),
            "bomb_site": _normalize_bomb_site(r["bomb_site"]),
            "human_side": human_side,
            "result": result,
            "kills": k,
            "deaths": d,
            "entry": entry_kind,
        })
    return rows


def _kill_feed(kills, dominant_side):
    feed = []
    for k in kills:
        if not (k["attacker_is_human"] or k["victim_is_human"]):
            continue
        if k["attacker_is_human"]:
            kind, opponent = "kill", k["victim_name"] or "bot"
        else:
            kind, opponent = "death", k["attacker_name"] or "bot"
        feed.append({
            "round_num": k["round_num"],
            "tick": k["tick"],
            "type": kind,
            "opponent": opponent,
            "weapon": k["weapon"],
            "headshot": bool(k["headshot"]),
            "distance": round(k["distance"], 0) if k["distance"] is not None else None,
            "human_side": dominant_side.get(k["round_num"]),
        })
    return feed


def _agg_stats_from_row(row):
    """Stats de partidas ingeridas via CSV da MatchZy (fonte 'csv') — só
    tem agregado da partida inteira, sem round/kill a kill, então adr/
    round_win_pct/rounds_played ficam None (sem como derivar do CSV).
    Ver parser.store_match_from_csv."""
    kills = row["agg_kills"] or 0
    deaths = row["agg_deaths"] or 0
    hs = row["agg_hs_kills"] or 0
    return {
        "kills": kills,
        "deaths": deaths,
        "kd": kills / deaths if deaths else float(kills),
        "hs_pct": (100 * hs / kills) if kills else 0.0,
        "hs_kills": hs,
        "adr": None,
        "dmg_total": row["agg_damage"],
        "assists": row["agg_assists"],
        "rounds_played": None,
        "round_wins": None,
        "round_win_pct": None,
        "entry_for": None,
        "entry_against": None,
        "entry_pct": None,
        "max_streak": None,
        # O CSV da MatchZy TEM essas colunas (v1_count/v1_wins, entry_count,
        # enemy2ks..enemy5ks) e o parser ainda não as ingere — quando ingerir,
        # é aqui que elas entram. Ver docs/features/M6-estatisticas.md.
        "kast_rounds": None,
        "kast_pct": None,
        "kast_has_assists": False,
        "kast_has_trades": False,
        "trade_kills": None,
        "traded_deaths": None,
        "multi_kills": None,
        "clutches": None,
        "clutch_count": None,
        "clutch_wins": None,
    }


def build_match_data(conn, row):
    mid = row["id"]
    score_ct = row["score_ct"]
    score_t = row["score_t"]
    score_mine = row["score_mine"]
    score_theirs = row["score_theirs"]
    score_source = row["score_source"]
    outcome = row["outcome"]

    empty_sides = {"all": None, "ct": None, "t": None}

    if row["source"] == "csv":
        stats = {"all": _agg_stats_from_row(row), "ct": None, "t": None}
        weapons = {"all": [], "ct": [], "t": []}
        rounds_timeline = []
        kill_feed = []
        longest_kill = dict(empty_sides)
        bombsites = {"all": [], "ct": [], "t": []}
        life_events = []
        hitgroups = {"all": [], "ct": [], "t": []}
        head_to_head = {"all": [], "ct": [], "t": []}
    else:
        rounds, kills, damages = _fetch_match_raw(conn, mid)
        dominant_side = _human_side_by_round(conn, mid, rounds)
        # Rounds não contados (fantasma da janela de rebalanceamento, round
        # abortado por restart) saem de todas as estatísticas — ver
        # parser.mark_counted_rounds.
        rounds = [r for r in rounds if r["counted"]]

        if score_mine is None or score_theirs is None:
            # Partida ingerida antes do placar por time existir: reconstrói
            # aqui. Note que NÃO se recalcula score_ct/score_t — eles são
            # rounds por lado, que num MR12 não são o placar de ninguém.
            score_mine, score_theirs = _team_score_from_rounds(rounds, dominant_side)
            if score_mine is not None:
                score_source = score_source or "rounds-render"
                outcome = outcome or (
                    "win" if score_mine > score_theirs
                    else "loss" if score_theirs > score_mine else "tie"
                )

        scopes = {
            "all": _side_round_nums(rounds, dominant_side, None),
            "ct": _side_round_nums(rounds, dominant_side, "ct"),
            "t": _side_round_nums(rounds, dominant_side, "t"),
        }

        stats = {
            side: _stats_for_round_nums(rounds, kills, damages, dominant_side, nums)
            for side, nums in scopes.items()
        }
        weapons = {
            side: _weapons_for_round_nums(kills, damages, nums)
            for side, nums in scopes.items()
        }
        rounds_timeline = _round_timeline(rounds, kills, dominant_side)
        kill_feed = _kill_feed(kills, dominant_side)
        longest_kill = {
            side: _longest_kill(kills, nums) for side, nums in scopes.items()
        }
        bombsites = {
            side: _bombsites_for_round_nums(rounds, dominant_side, nums)
            for side, nums in scopes.items()
        }
        life_events = _life_events(kills, dominant_side)
        hitgroups = {
            side: _hitgroups_for_round_nums(damages, nums) for side, nums in scopes.items()
        }
        head_to_head = {
            side: _head_to_head(kills, nums) for side, nums in scopes.items()
        }

    return {
        "id": mid,
        "demo_name": row["demo_name"],
        "map": row["map"],
        "played_at": row["played_at"],
        "score_ct": score_ct,
        "score_t": score_t,
        "score_mine": score_mine,
        "score_theirs": score_theirs,
        "score_source": score_source,
        "outcome": outcome,
        "duration_minutes": row["duration_minutes"],
        "player_name": row["player_name"],
        "source": row["source"],
        "series_num_maps": row["series_num_maps"],
        "stats": stats,
        "weapons": weapons,
        "rounds": rounds_timeline,
        "kill_feed": kill_feed,
        "longest_kill": longest_kill,
        "bombsites": bombsites,
        "life_events": life_events,
        "hitgroups": hitgroups,
        "head_to_head": head_to_head,
    }


def _empty_map_acc():
    return {
        "matches": 0,
        "kills": 0,
        "deaths": 0,
        "hs_kills": 0,
        "dmg_total": 0,
        "rounds_played": 0,
        "round_wins": 0,
        "entry_for": 0,
        "entry_against": 0,
        # kast_rounds só soma junto com os rounds da mesma partida, senão o
        # percentual final sai sobre um denominador que não é dele.
        "kast_rounds": 0,
        "kast_rounds_played": 0,
        "trade_kills": 0,
        "traded_deaths": 0,
        "trades_rounds": 0,
        "multi_kills": {"2k": 0, "3k": 0, "4k": 0, "5k": 0},
        "clutch_count": 0,
        "clutch_wins": 0,
    }


def _finalize_acc(acc):
    if acc["matches"] == 0:
        return None
    kills, deaths = acc["kills"], acc["deaths"]
    entry_total = acc["entry_for"] + acc["entry_against"]
    rounds = acc["rounds_played"]
    return {
        "matches": acc["matches"],
        "kills": kills,
        "deaths": deaths,
        "kd": kills / deaths if deaths else float(kills),
        "hs_pct": (100 * acc["hs_kills"] / kills) if kills else 0.0,
        "adr": (acc["dmg_total"] / rounds) if rounds else None,
        "rounds_played": rounds or None,
        "round_wins": acc["round_wins"] if rounds else None,
        "round_win_pct": (100 * acc["round_wins"] / rounds) if rounds else None,
        "entry_for": acc["entry_for"] if entry_total else None,
        "entry_against": acc["entry_against"] if entry_total else None,
        "entry_pct": (100 * acc["entry_for"] / entry_total) if entry_total else None,
        "kast_pct": (
            100 * acc["kast_rounds"] / acc["kast_rounds_played"]
            if acc["kast_rounds_played"] else None
        ),
        "trade_kills": acc["trade_kills"] if acc["trades_rounds"] else None,
        "traded_deaths": acc["traded_deaths"] if acc["trades_rounds"] else None,
        "multi_kills": acc["multi_kills"],
        "clutch_count": acc["clutch_count"] or None,
        "clutch_wins": acc["clutch_wins"] if acc["clutch_count"] else None,
        "clutch_pct": (
            100 * acc["clutch_wins"] / acc["clutch_count"] if acc["clutch_count"] else None
        ),
    }


def _add_stats_to_acc(acc, stats):
    if not stats:
        return
    acc["matches"] += 1
    acc["kills"] += stats["kills"]
    acc["deaths"] += stats["deaths"]
    acc["hs_kills"] += stats.get("hs_kills") or 0
    if stats.get("rounds_played"):
        acc["rounds_played"] += stats["rounds_played"]
        acc["round_wins"] += stats.get("round_wins") or 0
        if stats.get("dmg_total") is not None:
            acc["dmg_total"] += stats["dmg_total"]
        elif stats.get("adr") is not None:
            acc["dmg_total"] += stats["adr"] * stats["rounds_played"]
    if stats.get("entry_for") is not None:
        acc["entry_for"] += stats["entry_for"]
        acc["entry_against"] += stats.get("entry_against") or 0
    if stats.get("kast_rounds") is not None and stats.get("rounds_played"):
        acc["kast_rounds"] += stats["kast_rounds"]
        acc["kast_rounds_played"] += stats["rounds_played"]
    if stats.get("trade_kills") is not None:
        acc["trade_kills"] += stats["trade_kills"]
        acc["traded_deaths"] += stats.get("traded_deaths") or 0
        acc["trades_rounds"] += stats.get("rounds_played") or 0
    for bucket, count in (stats.get("multi_kills") or {}).items():
        acc["multi_kills"][bucket] = acc["multi_kills"].get(bucket, 0) + count
    if stats.get("clutch_count") is not None:
        acc["clutch_count"] += stats["clutch_count"]
        acc["clutch_wins"] += stats.get("clutch_wins") or 0


def _map_leaderboard(matches_data):
    """Ranking por mapa: mesmo cálculo de _stats_for_round_nums, agregado
    por matches.map em vez de por partida. CSV entra no K/D; ADR/win%/entry
    só nas fontes com detalhe por round."""
    by_map = {}
    for match in matches_data:
        name = match["map"] or "?"
        bucket = by_map.setdefault(name, {side: _empty_map_acc() for side in ("all", "ct", "t")})
        for side in ("all", "ct", "t"):
            _add_stats_to_acc(bucket[side], match["stats"].get(side))
    rows = []
    for name, sides in by_map.items():
        rows.append({
            "map": name,
            "stats": {side: _finalize_acc(acc) for side, acc in sides.items()},
        })
    rows.sort(key=lambda row: -((row["stats"]["all"] or {}).get("kd") or 0))
    return rows


def best_map(maps_leaderboard, min_matches=3):
    """Mapa em destaque na home: ADR como critério primário (dano é o que
    foi pedido), K/D como desempate. Fora do ranking completo (que ordena
    por K/D) porque a home só precisa de UM mapa em destaque, com um
    critério diferente — ver divergência registrada em M3.5-home.md."""
    candidates = [
        row for row in maps_leaderboard
        if (row["stats"]["all"] or {}).get("matches", 0) >= min_matches
        and (row["stats"]["all"] or {}).get("adr") is not None
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (-(row["stats"]["all"]["adr"] or 0), -(row["stats"]["all"]["kd"] or 0))
    )
    return candidates[0]


def side_summary(matches_data):
    """Round win% por lado (CT/TR), agregado em TODAS as partidas — mesmo
    cálculo do ranking por mapa, só que sem particionar por mapa."""
    result = {}
    for side in ("ct", "t"):
        acc = _empty_map_acc()
        for match in matches_data:
            _add_stats_to_acc(acc, match["stats"].get(side))
        result[side] = _finalize_acc(acc)
    return result


def _personal_records(matches_data):
    """Recordes pessoais por lado: melhor K/D e ADR de uma partida, maior
    kill à distância, maior sequência de kills sem morrer (entre partidas,
    na ordem de played_at) e a sequência atual."""
    records = {}
    for side in ("all", "ct", "t"):
        best_kd = best_adr = longest = None
        max_streak = current = 0
        for match in matches_data:
            stats = match["stats"].get(side)
            if stats:
                if best_kd is None or stats["kd"] > best_kd["value"]:
                    best_kd = {
                        "value": stats["kd"],
                        "map": match["map"],
                        "played_at": match["played_at"],
                        "id": match["id"],
                    }
                if stats.get("adr") is not None:
                    if best_adr is None or stats["adr"] > best_adr["value"]:
                        best_adr = {
                            "value": stats["adr"],
                            "map": match["map"],
                            "played_at": match["played_at"],
                            "id": match["id"],
                        }
            lk = (match.get("longest_kill") or {}).get(side)
            if lk and (longest is None or lk["distance"] > longest["distance"]):
                longest = {**lk, "map": match["map"], "id": match["id"]}
            events = match.get("life_events") or []
            # Uma partida CSV não informa a ordem de kills/mortes. Não é
            # seguro ligar uma sequência anterior a outra posterior
            # atravessando esse trecho desconhecido.
            if match["source"] == "csv":
                current = 0
                continue
            if side != "all":
                events = [e for e in events if e.get("human_side") == side]
            for event in events:
                if event["type"] == "kill":
                    current += 1
                    if current > max_streak:
                        max_streak = current
                else:
                    current = 0
        records[side] = {
            "best_kd": best_kd,
            "best_adr": best_adr,
            "longest_kill": longest,
            "max_kill_streak": max_streak,
            "current_kill_streak": current,
        }
    return records


def _bombsite_leaderboard(matches_data):
    result = {}
    for side in ("all", "ct", "t"):
        acc = {}
        for match in matches_data:
            for row in (match.get("bombsites") or {}).get(side) or []:
                bucket = acc.setdefault(row["site"], {"plants": 0, "wins": 0})
                bucket["plants"] += row["plants"]
                bucket["wins"] += row["wins"]
        result[side] = [
            {
                "site": site,
                "plants": data["plants"],
                "wins": data["wins"],
                "win_pct": 100 * data["wins"] / data["plants"] if data["plants"] else 0.0,
            }
            for site, data in sorted(acc.items())
        ]
    return result


def _weapon_leaderboard(matches_data):
    """Dano/kills por arma, somado entre TODAS as partidas (o que
    _weapons_for_round_nums calcula por partida). Só enxerga partidas com
    detalhe de kill/dano (fonte 'demo') — CSV não distingue arma.

    Ranking por dano bruto: premia a arma mais usada, não necessariamente a
    mais letal (a AK-47 tende a vencer por ser a mais comprada). kills e
    dmg_share_pct ficam ao lado como secundários pra essa leitura não ficar
    escondida — ver divergência registrada em M3.5-home.md."""
    totals = {}
    for match in matches_data:
        for row in (match["weapons"].get("all") or []):
            acc = totals.setdefault(row["weapon"], {"kills": 0, "headshots": 0, "dmg": 0})
            acc["kills"] += row["kills"]
            acc["headshots"] += row["headshots"]
            acc["dmg"] += row["dmg"]

    total_dmg = sum(acc["dmg"] for acc in totals.values())
    rows = []
    for weapon, acc in totals.items():
        rows.append({
            "weapon": weapon,
            "kills": acc["kills"],
            "headshots": acc["headshots"],
            "hs_pct": (100 * acc["headshots"] / acc["kills"]) if acc["kills"] else None,
            "dmg": acc["dmg"],
            "dmg_share_pct": (100 * acc["dmg"] / total_dmg) if total_dmg else None,
        })
    rows.sort(key=lambda r: -r["dmg"])
    return rows


def _head_to_head_leaderboard(matches_data):
    """Saldo de duelos contra cada pro, somado entre TODAS as partidas."""
    result = {}
    for side in ("all", "ct", "t"):
        acc = {}
        for match in matches_data:
            for row in (match.get("head_to_head") or {}).get(side) or []:
                bucket = acc.setdefault(row["opponent"], {"kills": 0, "deaths": 0})
                bucket["kills"] += row["kills"]
                bucket["deaths"] += row["deaths"]
        rows = [
            {
                "opponent": name,
                "kills": data["kills"],
                "deaths": data["deaths"],
                "diff": data["kills"] - data["deaths"],
            }
            for name, data in acc.items()
        ]
        rows.sort(key=lambda r: (-r["diff"], -r["kills"], r["opponent"]))
        result[side] = rows
    return result


def _hitgroup_leaderboard(matches_data):
    """Regiões de acerto somadas entre todas as partidas. Junta as duas
    fontes de ingestão porque normalize_hitgroup já reconciliou os dois
    formatos em que damages.hitgroup é gravado."""
    result = {}
    for side in ("all", "ct", "t"):
        acc = {}
        for match in matches_data:
            for row in (match.get("hitgroups") or {}).get(side) or []:
                bucket = acc.setdefault(row["hitgroup"], {"hits": 0, "dmg": 0})
                bucket["hits"] += row["hits"]
                bucket["dmg"] += row["dmg"]
        total_hits = sum(b["hits"] for b in acc.values())
        total_dmg = sum(b["dmg"] for b in acc.values())
        result[side] = [
            {
                "hitgroup": group,
                "label": HITGROUP_LABEL[group],
                "hits": acc[group]["hits"],
                "dmg": acc[group]["dmg"],
                "hit_pct": 100 * acc[group]["hits"] / total_hits if total_hits else 0.0,
                "dmg_pct": 100 * acc[group]["dmg"] / total_dmg if total_dmg else 0.0,
            }
            for group in HITGROUP_ORDER
            if group in acc
        ]
    return result


def match_positions(db_path, match_id):
    """Onde no mapa você matou e morreu, pra tela de uma partida.

    Duas fontes populam player_positions. Na demo é o humano tick a tick; na
    fonte 'events' são os 10 jogadores, e o próprio player_death carrega a
    posição do matador e da vítima. Só interessa a posição do HUMANO nos dois
    casos — a kill é dele ou a morte é dele — daí o filtro de is_human, que
    também evita multiplicar cada kill pelas 10 linhas do mesmo tique.

    Devolve None quando não há posição real: a aba do mapa simplesmente não
    aparece nessas partidas, em vez de desenhar tudo na origem.

    O casamento kill<->posição é por tick exato, e é por isso que o plugin
    carimba a posição dentro do próprio player_death: a amostragem de trajeto
    é de 2 Hz e praticamente nunca cairia no tique da kill. Kill sem posição
    correspondente é descartada em vez de chutada.

    DISTINCT porque uma kill que cai exatamente num tique de amostragem tem
    duas linhas idênticas (a do evento e a da amostra), e sem isso o ponto
    seria desenhado duas vezes.

    Não há imagem de radar em static/ — quem desenha normaliza x/y pela
    bounding box devolvida aqui. Trocar por um radar de verdade depois é só
    substituir a normalização pelos pos_x/pos_y/scale do mapa."""
    import sqlite3
    from pathlib import Path

    if not Path(db_path).exists():
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        box = conn.execute(
            """SELECT MIN(x) AS min_x, MAX(x) AS max_x, MIN(y) AS min_y, MAX(y) AS max_y,
                      COUNT(*) AS n
               FROM player_positions
              WHERE match_id=? AND COALESCE(is_human, 1) = 1
                AND x IS NOT NULL AND (x <> 0 OR y <> 0)""",
            (match_id,),
        ).fetchone()
        if not box or not box["n"]:
            return None

        rows = conn.execute(
            """SELECT DISTINCT k.round_num, k.tick, p.x, p.y, p.z, p.place, p.side,
                      k.attacker_is_human AND NOT COALESCE(k.post_mortem, 0) AS mine,
                      k.victim_is_human   AND NOT COALESCE(k.post_mortem, 0) AS theirs,
                      k.weapon, k.attacker_name, k.victim_name
               FROM kills k
               JOIN player_positions p
                 ON p.match_id = k.match_id
                AND p.round_num = k.round_num
                AND p.tick = k.tick
                AND COALESCE(p.is_human, 1) = 1
                AND p.x IS NOT NULL
               WHERE k.match_id = ?
                 AND (k.attacker_is_human OR k.victim_is_human)
               ORDER BY k.tick""",
            (match_id,),
        ).fetchall()
    finally:
        conn.close()

    points = []
    places = {}
    for r in rows:
        if not (r["mine"] or r["theirs"]):
            continue
        kind = "kill" if r["mine"] else "death"
        points.append({
            "round_num": r["round_num"],
            "type": kind,
            "x": r["x"],
            "y": r["y"],
            # z separa os níveis num mapa de dois andares (Nuke, Vertigo) —
            # o limiar vem do overview do jogo, ver data/map_radar.json.
            "z": r["z"],
            "place": r["place"],
            "side": r["side"],
            "weapon": r["weapon"],
            "opponent": (r["victim_name"] if r["mine"] else r["attacker_name"]) or "bot",
        })
        if r["place"]:
            bucket = places.setdefault(r["place"], {"kills": 0, "deaths": 0})
            bucket["kills" if kind == "kill" else "deaths"] += 1

    if not points:
        return None

    place_rows = [
        {
            "place": name,
            "kills": data["kills"],
            "deaths": data["deaths"],
            "diff": data["kills"] - data["deaths"],
        }
        for name, data in places.items()
    ]
    place_rows.sort(key=lambda p: (-(p["kills"] + p["deaths"]), p["place"]))

    return {
        "points": points,
        "places": place_rows,
        "bbox": {
            "min_x": box["min_x"], "max_x": box["max_x"],
            "min_y": box["min_y"], "max_y": box["max_y"],
        },
        "sampled_ticks": box["n"],
    }


# Faixas de compra, em valor de equipamento de UM jogador no fim do freeze
# time. Não é dinheiro (o awpy não expõe dinheiro) — é o que você carrega.
# Os cortes são convenção do jogo, não número oficial: abaixo de 2000 não dá
# rifle + colete, e a partir de 4000 dá rifle com colete e utility.
BUY_ECO_MAX = 2000
BUY_FORCE_MAX = 4000
BUY_LABEL = {"eco": "Eco", "force": "Force", "full": "Full buy", None: "—"}


def classify_buy(equip_value):
    if equip_value is None:
        return None
    if equip_value < BUY_ECO_MAX:
        return "eco"
    if equip_value < BUY_FORCE_MAX:
        return "force"
    return "full"


def match_loadout(db_path, match_id):
    """Por round: o que você carregava no fim do freeze time e quanto tempo
    ficou cego. Devolve {} quando a partida não tem esse dado.

    Duas fontes: partidas de .dem ingeridas depois de 21/09/2026 (quando o
    parser passou a pedir PLAYER_PROPS) e partidas de origem 'events' a partir
    do plugin v0.3.0, que manda o evento freeze_end. Partidas anteriores a
    isso não têm, e não dá pra reconstruir sem reprocessar. Por isso o retorno
    é um dict por round_num e não uma lista — quem consome faz
    `.get(round_num)` e some da tela quando não houver.

    O fim do freeze time é a âncora certa pro valor do equipamento: antes a
    compra ainda está acontecendo, depois já entra arma recolhida do chão.

    Tempo cego é a soma dos SALTOS positivos de flash_duration dentro do
    round. flash_duration é um contador que cai a cada tick, então somar os
    valores contaria a mesma flash centenas de vezes; somar só as subidas dá
    uma linha por flash que te pegou, com a duração dela.
    """
    import sqlite3
    from pathlib import Path

    if not Path(db_path).exists():
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        loadout = conn.execute(
            """SELECT r.round_num,
                      (SELECT p.equip_value FROM player_positions p
                        WHERE p.match_id=r.match_id AND p.round_num=r.round_num
                          AND COALESCE(p.is_human, 1) = 1
                          AND p.tick >= r.freeze_end_tick
                        ORDER BY p.tick LIMIT 1) AS equip_value,
                      (SELECT p.armor FROM player_positions p
                        WHERE p.match_id=r.match_id AND p.round_num=r.round_num
                          AND COALESCE(p.is_human, 1) = 1
                          AND p.tick >= r.freeze_end_tick
                        ORDER BY p.tick LIMIT 1) AS armor,
                      (SELECT p.has_helmet FROM player_positions p
                        WHERE p.match_id=r.match_id AND p.round_num=r.round_num
                          AND COALESCE(p.is_human, 1) = 1
                          AND p.tick >= r.freeze_end_tick
                        ORDER BY p.tick LIMIT 1) AS has_helmet,
                      (SELECT p.has_defuser FROM player_positions p
                        WHERE p.match_id=r.match_id AND p.round_num=r.round_num
                          AND COALESCE(p.is_human, 1) = 1
                          AND p.tick >= r.freeze_end_tick
                        ORDER BY p.tick LIMIT 1) AS has_defuser
               FROM rounds r
               WHERE r.match_id=? AND r.freeze_end_tick IS NOT NULL""",
            (match_id,),
        ).fetchall()

        # Fonte 'events': o evento player_blind dá a duração exata de cada
        # flash sofrida, uma linha por flash. É preferida quando existe.
        blind = conn.execute(
            """SELECT round_num, SUM(duration) AS blind_time, COUNT(*) AS flashes
                 FROM player_blinds
                WHERE match_id=? AND victim_is_human=1 AND duration > 0
                GROUP BY round_num""",
            (match_id,),
        ).fetchall()
        if not blind:
            # Fonte demo: não há evento, só flash_duration amostrada tick a
            # tick. flash_duration é um contador que DECRESCE, então somar os
            # valores contaria a mesma flash centenas de vezes; somar só as
            # SUBIDAS dá uma linha por flash, com a duração dela. Só funciona
            # com amostragem densa — com eventos discretos, duas flashes no
            # mesmo round viriam como uma, e é por isso que a fonte 'events'
            # tem tabela própria em vez de reaproveitar isto.
            blind = conn.execute(
                """WITH f AS (
                       SELECT round_num, flash_duration,
                              LAG(flash_duration) OVER (
                                  PARTITION BY round_num ORDER BY tick
                              ) AS prev
                         FROM player_positions
                        WHERE match_id=? AND flash_duration IS NOT NULL
                          AND COALESCE(is_human, 1) = 1
                   )
                   SELECT round_num,
                          SUM(CASE WHEN flash_duration > COALESCE(prev, 0)
                                   THEN flash_duration - COALESCE(prev, 0)
                                   ELSE 0 END) AS blind_time,
                          SUM(CASE WHEN flash_duration > COALESCE(prev, 0)
                                   THEN 1 ELSE 0 END) AS flashes
                     FROM f GROUP BY round_num""",
                (match_id,),
            ).fetchall()
    finally:
        conn.close()

    blind_by_round = {r["round_num"]: r for r in blind}
    result = {}
    for row in loadout:
        rn = row["round_num"]
        b = blind_by_round.get(rn)
        result[rn] = {
            "equip_value": row["equip_value"],
            "buy": classify_buy(row["equip_value"]),
            "armor": row["armor"],
            "has_helmet": bool(row["has_helmet"]) if row["has_helmet"] is not None else None,
            "has_defuser": bool(row["has_defuser"]) if row["has_defuser"] is not None else None,
            "blind_time": round(b["blind_time"], 2) if b and b["blind_time"] else 0.0,
            "flashes": (b["flashes"] if b else 0) or 0,
        }
    return result


def human_quick_summary(db_path) -> dict:
    """
    Resumo leve do humano pra fora do relatório — usado pela linha do
    jogador humano na tela de Lineups (item 2, 2026-09-20): quantidade de
    partidas, ADR e K/D, sem rodar o pipeline pesado de build_match_data.

    Calcula direto de kills/damages (attacker_is_human/victim_is_human),
    restrito a rounds "counted" — é a mesma fonte de verdade que
    build_match_data usa pras partidas 'demo'/'events'. NÃO cobre partidas
    ingeridas via CSV puro (source='csv'): essas só têm matches.agg_* e não
    populam kills/damages/rounds (ver parser.store_match_from_csv) — hoje
    não existe nenhuma no banco deste projeto, então fica de fora de
    propósito em vez de misturar duas fontes com granularidade diferente.

    Se o banco não existir ainda (primeira execução, nenhuma partida
    jogada), devolve tudo vazio em vez de estourar.
    """
    import sqlite3
    from pathlib import Path

    empty = {"matches": 0, "adr": None, "kd": None}
    if not Path(db_path).exists():
        return empty

    conn = sqlite3.connect(db_path)
    try:
        matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        if not matches:
            return empty
        kills = conn.execute(
            """SELECT COUNT(*) FROM kills k
               JOIN rounds r ON r.match_id = k.match_id AND r.round_num = k.round_num
               WHERE k.attacker_is_human = 1 AND r.counted = 1"""
        ).fetchone()[0]
        deaths = conn.execute(
            """SELECT COUNT(*) FROM kills k
               JOIN rounds r ON r.match_id = k.match_id AND r.round_num = k.round_num
               WHERE k.victim_is_human = 1 AND r.counted = 1"""
        ).fetchone()[0]
        damage = conn.execute(
            """SELECT SUM(d.dmg_health) FROM damages d
               JOIN rounds r ON r.match_id = d.match_id AND r.round_num = d.round_num
               WHERE d.attacker_is_human = 1 AND r.counted = 1"""
        ).fetchone()[0]
        rounds = conn.execute("SELECT COUNT(*) FROM rounds WHERE counted = 1").fetchone()[0]
        adr = (damage / rounds) if damage and rounds else None
        kd = (kills / deaths) if deaths else (float(kills) if kills else None)
        return {"matches": matches, "adr": adr, "kd": kd}
    finally:
        conn.close()


def load_stats(db_path):
    """Ponto de entrada único: abre o banco, monta matches_data e todos os
    agregados derivados dele. report.py e home.py chamam esta função em vez
    de recalcular cada um por conta própria."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    matches_data = [build_match_data(conn, row) for row in fetch_matches(conn)]
    conn.close()

    maps = _map_leaderboard(matches_data)
    return {
        "matches": matches_data,
        "maps": maps,
        "records": _personal_records(matches_data),
        "bombsites": _bombsite_leaderboard(matches_data),
        "weapons": _weapon_leaderboard(matches_data),
        "best_map": best_map(maps),
        "sides": side_summary(matches_data),
        "head_to_head": _head_to_head_leaderboard(matches_data),
        "hitgroups": _hitgroup_leaderboard(matches_data),
    }
