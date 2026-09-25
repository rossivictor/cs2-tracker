#!/usr/bin/env python3
"""
CS2 Tracker — Telas de partidas
================================
Monta o contexto das duas telas novas (F6.1): a lista de todas as suas
partidas (/partidas) e o detalhe de uma partida (/partidas/<id>).

Mesmo papel que home.build_context tem pra home: nenhum cálculo de
estatística mora aqui — tudo vem de stats.load_stats. O que este módulo faz
é o que a tela precisa e o cálculo não deve saber: formatar, escolher ícone,
normalizar coordenada pra SVG e comparar uma partida com a sua própria média.

Substitui o papel do #dashboard-view/#match-view de templates/report.html,
que era uma página só com os dois modos trocados por location.hash. O
report.py antigo continua de pé e continua gerando report.html estático: ele
é o único caminho que funciona offline, via file://, e só sai de cena quando
estas telas provarem paridade em uso real.
"""

import json
from pathlib import Path

import stats as stats_mod
from stats import (
    BUY_LABEL,
    HITGROUP_ORDER,
    load_stats,
    match_loadout,
    map_bg_path,
    map_icon_path,
    map_label,
    map_slug,
    match_positions,
    merged_weapon_label,
    weapon_icon_path,
    weapon_label,
)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
MAP_RADAR_PATH = ROOT / "data" / "map_radar.json"

SIDES = [("all", "Geral"), ("ct", "CT"), ("t", "TR")]

# Quantas partidas entram na leitura de "forma recente" — o strip de
# vitórias/derrotas e o delta dos KPIs.
RECENT_N = 5
RECENT_STRIP_N = 20
# Mínimo de partidas anteriores pra comparar uma partida com a sua média.
# Abaixo disso a média é ruído e a coluna Δ sai vazia em vez de enganosa.
DELTA_MIN_HISTORY = 3
# Quantas partidas anteriores entram nessa média móvel.
DELTA_WINDOW = 10

REASON_LABEL = {
    "bomb_defused": "Bomba defusada",
    "bomb_exploded": "Bomba explodiu",
    "t_killed": "TRs eliminados",
    "ct_killed": "CTs eliminados",
    "TargetSaved": "Tempo esgotado",
}
# Agrupamento do motivo pra barra empilhada de "como os rounds foram ganhos".
REASON_GROUP = {
    "t_killed": "elim", "ct_killed": "elim",
    "bomb_exploded": "bomb", "bomb_defused": "defuse",
    "TargetSaved": "time",
}
REASON_GROUP_LABEL = {
    "elim": "Eliminação", "bomb": "Bomba", "defuse": "Defuse",
    "time": "Tempo", "other": "Outros",
}
REASON_GROUP_COLOR = {
    "elim": "var(--win)", "bomb": "var(--amber)",
    "defuse": "#60a5fa", "time": "var(--muted)", "other": "#3f5551",
}
SIDE_LABEL = {"ct": "CT", "t": "TR"}


# --------------------------------------------------------------------------- #
# Helpers de apresentação
# --------------------------------------------------------------------------- #

def _asset_exists(rel_path):
    return (STATIC / rel_path).exists()


def _map_view(map_name):
    """Ícone, rótulo e arte de fundo de um mapa. A arte é opcional: falta
    bg-aurora.webp em static/, e mapa novo entra sem arte até alguém pôr o
    arquivo lá — por isso o template checa `bg` em vez de assumir."""
    bg = map_bg_path(map_name)
    icon = map_icon_path(map_name)
    return {
        "name": map_name,
        "label": map_label(map_name),
        "icon": icon if _asset_exists(icon) else None,
        "bg": bg if _asset_exists(bg) else None,
    }


def _weapon_view(weapon, merged=False):
    """`merged=True` no quadro de armas, onde canonical_weapon já juntou os
    pares silenciado/base e o rótulo precisa dizer que são dois."""
    icon = weapon_icon_path(weapon)
    return {
        "weapon": weapon,
        "label": merged_weapon_label(weapon) if merged else weapon_label(weapon),
        "icon": icon if _asset_exists(icon) else None,
    }


# --------------------------------------------------------------------------- #
# Radar: mundo -> imagem 2D
# --------------------------------------------------------------------------- #

_MAP_RADAR_CACHE = None


def _map_radar_data():
    """Snapshot gerado por tools/extract_map_radar.py a partir dos
    resource/overviews/*.txt do próprio CS2. Ausente = o app funciona, só
    sem radar — não é motivo pra quebrar a tela."""
    global _MAP_RADAR_CACHE
    if _MAP_RADAR_CACHE is None:
        try:
            _MAP_RADAR_CACHE = json.loads(MAP_RADAR_PATH.read_text(encoding="utf-8"))["maps"]
        except (OSError, ValueError, KeyError):
            _MAP_RADAR_CACHE = {}
    return _MAP_RADAR_CACHE


def radar_meta(map_name):
    return _map_radar_data().get(map_name or "")


def world_to_radar(meta, x, y):
    """Coordenada de mundo -> fração 0..1 da imagem de radar.

    pixel = (x - pos_x)/scale no eixo X e (pos_y - y)/scale no Y (o Y do
    mundo cresce pro norte, o da imagem pra baixo). Dividir por image_size
    deixa o resultado independente da resolução do arquivo — as imagens em
    static/ estão em 1000px e o radar oficial é 1024, e normalizando isso
    deixa de importar.

    `rotate` e `zoom` do overview não entram, igual em
    awpy.plot.utils.game_to_pixel_axis: a imagem já vem orientada.

    Conferido de duas formas independentes, no Mirage:

    1. Contra as âncoras que o próprio overview publica — o centróide das
       posições com place='TSpawn' cai a 0,005 do TSpawn_x/TSpawn_y do jogo.
    2. Amostrando o pixel da imagem de radar sob cada posição real gravada:
       99,9% dos 8.245 pontos caem em área desenhada do mapa. Deslocar o
       transform em 5% derruba pra 65%, e em 10% pra ~51% — ou seja, o
       alinhamento tem um pico nítido e está nele."""
    span = meta["scale"] * meta["image_size"]
    return (x - meta["pos_x"]) / span, (meta["pos_y"] - y) / span


def _radar_image(map_name, level=None):
    """static/radar-<slug>.webp, ou -upper/-lower nos mapas de dois níveis."""
    slug = map_slug(map_name)
    name = f"radar-{slug}-{level}.webp" if level else f"radar-{slug}.webp"
    return name if _asset_exists(name) else None


def _fmt_date(iso):
    return iso.replace("T", " ")[:16] if iso else ""


def _series_tag(num_maps):
    """BO3/BO5 como etiqueta ao lado do nome do mapa. BO1 não vira etiqueta:
    é o formato padrão, e marcar todas as partidas com "BO1" só acrescenta
    ruído — a etiqueta existe pra dizer que aquele mapa faz parte de uma
    série (pedido em 22/09/2026)."""
    return f"BO{num_maps}" if num_maps and num_maps > 1 else ""


def _pct(value, digits=0):
    """Arredonda pra exibição. Com digits=0 devolve int, senão o template
    imprimiria "65.0%" onde o número tem uma casa que não existe."""
    if value is None:
        return None
    return int(round(value)) if digits == 0 else round(value, digits)


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _round_hitgroups(rows):
    return [{**r, "hit_pct": _pct(r["hit_pct"]), "dmg_pct": _pct(r["dmg_pct"])} for r in rows]


# --------------------------------------------------------------------------- #
# Tela: todas as partidas
# --------------------------------------------------------------------------- #

def _match_delta(match_adr, history):
    """Quanto o ADR desta partida ficou acima/abaixo da sua média recente.

    É a coluna-síntese com sinal que dá direção de leitura à lista. Comparar
    contra a PRÓPRIA média (e não contra um rating absoluto) é deliberado:
    não existe rank de matchmaking nem base populacional aqui pra calibrar um
    número absoluto, e inventar um fingiria uma precisão que o dado não tem.
    """
    if match_adr is None or len(history) < DELTA_MIN_HISTORY:
        return None
    baseline = _mean(history[-DELTA_WINDOW:])
    if baseline is None:
        return None
    return match_adr - baseline


def _summary_from_stats(stats_list):
    """Agrega uma lista de stats-por-partida no mesmo formato que os cards
    esperam. Reusa o acumulador de stats.py pra não existir uma segunda
    definição de ADR/KAST/entry% com arredondamento diferente."""
    acc = stats_mod._empty_map_acc()
    for s in stats_list:
        stats_mod._add_stats_to_acc(acc, s)
    return stats_mod._finalize_acc(acc)


def _kpis(matches_stats):
    """Cards do topo: valor geral + delta das últimas RECENT_N contra o resto.

    O delta só aparece quando há histórico suficiente dos dois lados — sem
    isso ele compararia as últimas 5 partidas com 1 partida antiga.
    """
    overall = _summary_from_stats(matches_stats)
    if not overall:
        return []

    recent = _summary_from_stats(matches_stats[-RECENT_N:])
    older = _summary_from_stats(matches_stats[:-RECENT_N])
    comparable = bool(older) and len(matches_stats) > RECENT_N

    def delta(key):
        if not comparable or not recent:
            return None
        a, b = recent.get(key), older.get(key)
        return None if a is None or b is None else a - b

    specs = [
        ("adr", "ADR", 1, ""),
        ("kast_pct", "KAST", 0, "%"),
        ("kd", "K/D", 2, ""),
        ("hs_pct", "HS", 0, "%"),
        ("round_win_pct", "Rounds ganhos", 0, "%"),
        ("entry_pct", "Entry", 0, "%"),
    ]
    cards = []
    for key, label, digits, suffix in specs:
        value = overall.get(key)
        if value is None:
            continue
        cards.append({
            "key": key,
            "label": label,
            "value": round(value, digits),
            "suffix": suffix,
            "delta": _pct(delta(key), digits),
            "digits": digits,
        })
    return cards


def _map_cards(maps_leaderboard, side):
    """Cartão por mapa com arte de fundo e barras por lado. As barras são de
    ADR, normalizadas pelo maior ADR do conjunto — barra só faz sentido
    contra uma referência, e aqui a referência é o seu melhor mapa."""
    rows = []
    for entry in maps_leaderboard:
        s = entry["stats"].get(side)
        if not s:
            continue
        rows.append({
            "map": _map_view(entry["map"]),
            "matches": s["matches"],
            "win_pct": _pct(s["round_win_pct"]),
            "kd": round(s["kd"], 2),
            "adr": _pct(s["adr"], 1),
            "kast_pct": _pct(s["kast_pct"]),
            "ct_adr": _pct((entry["stats"].get("ct") or {}).get("adr"), 1),
            "t_adr": _pct((entry["stats"].get("t") or {}).get("adr"), 1),
        })
    # O pico tem que considerar os TRÊS valores: o ADR de um lado pode ser
    # maior que o ADR geral do mesmo mapa (é a média dos dois), e usar só o
    # geral como referência faria a barra daquele lado passar de 100%.
    peak = max(
        [v for r in rows for v in (r["adr"], r["ct_adr"], r["t_adr"]) if v is not None]
        or [0]
    ) or 1
    for r in rows:
        r["adr_bar"] = round(100 * (r["adr"] or 0) / peak)
        r["ct_bar"] = round(100 * (r["ct_adr"] or 0) / peak)
        r["t_bar"] = round(100 * (r["t_adr"] or 0) / peak)
    rows.sort(key=lambda r: (-(r["adr"] or 0), -r["matches"]))
    return rows


def _match_rows(matches_data, side):
    """Linhas da lista, com a coluna Δ e os grupos de coluna alternáveis.

    Ordem: mais recente primeiro (load_stats devolve por played_at crescente,
    que é o que o cálculo do Δ precisa; a inversão é só de apresentação).
    """
    rows = []
    adr_history = []
    for match in matches_data:
        s = match["stats"].get(side)
        mk = (s or {}).get("multi_kills") or {}
        adr = (s or {}).get("adr")
        row = {
            "id": match["id"],
            "played_at": _fmt_date(match["played_at"]),
            "map": _map_view(match["map"]),
            "score_mine": match["score_mine"],
            "score_theirs": match["score_theirs"],
            "outcome": match["outcome"],
            "series": _series_tag(match["series_num_maps"]),
            "source": match["source"],
            "has_side": bool(s),
            "kills": (s or {}).get("kills"),
            "deaths": (s or {}).get("deaths"),
            "kd": round(s["kd"], 2) if s else None,
            "adr": _pct(adr, 1),
            "hs_pct": _pct((s or {}).get("hs_pct")),
            "kast_pct": _pct((s or {}).get("kast_pct")),
            "entry_for": (s or {}).get("entry_for"),
            "entry_against": (s or {}).get("entry_against"),
            "entry_diff": (
                s["entry_for"] - s["entry_against"]
                if s and s.get("entry_for") is not None else None
            ),
            "trade_kills": (s or {}).get("trade_kills"),
            "traded_deaths": (s or {}).get("traded_deaths"),
            "clutch_wins": (s or {}).get("clutch_wins"),
            "clutch_count": (s or {}).get("clutch_count"),
            "mk2": mk.get("2k"), "mk3": mk.get("3k"),
            "mk4": mk.get("4k"), "mk5": mk.get("5k"),
            "delta": _pct(_match_delta(adr, adr_history), 1),
        }
        rows.append(row)
        if adr is not None:
            adr_history.append(adr)
    rows.reverse()
    return rows


def _trend_series(matches_data, side):
    """Séries do gráfico de tendência, alternáveis por checkbox no template.
    Uma lista de pontos por métrica, na ordem cronológica."""
    labels, adr, kd, hs, kast = [], [], [], [], []
    for match in matches_data:
        s = match["stats"].get(side)
        if not s:
            continue
        labels.append(_fmt_date(match["played_at"]))
        adr.append(_pct(s.get("adr"), 1))
        kd.append(round(s["kd"], 2))
        hs.append(_pct(s.get("hs_pct")))
        kast.append(_pct(s.get("kast_pct")))
    return {
        "labels": labels,
        "series": [
            {"key": "adr", "label": "ADR", "color": "#5eead4", "data": adr, "on": True},
            {"key": "kast", "label": "KAST %", "color": "#fbbf24", "data": kast, "on": True},
            {"key": "kd", "label": "K/D", "color": "#a78bfa", "data": kd, "on": False},
            {"key": "hs", "label": "HS %", "color": "#60a5fa", "data": hs, "on": False},
        ],
    }


def _recent_strip(matches_data):
    """Últimas partidas como pontos de vitória/derrota — a forma recente lida
    de relance, que nenhuma média mostra."""
    strip = []
    for match in matches_data[-RECENT_STRIP_N:]:
        strip.append({
            "id": match["id"],
            "outcome": match["outcome"],
            "map": _map_view(match["map"]),
            "score": f"{match['score_mine']}×{match['score_theirs']}"
                     if match["score_mine"] is not None else "-",
            "played_at": _fmt_date(match["played_at"]),
        })
    strip.reverse()
    wins = sum(1 for s in strip if s["outcome"] == "win")
    return {"items": strip, "wins": wins, "losses": len(strip) - wins}


def build_list_context(db_path, side="all", map_filter=None):
    """Contexto de GET /partidas."""
    if side not in dict(SIDES):
        side = "all"
    data = load_stats(db_path)
    matches_data = data["matches"]

    map_options = sorted({m["map"] for m in matches_data if m["map"]})
    if map_filter and map_filter in map_options:
        matches_data = [m for m in matches_data if m["map"] == map_filter]
    else:
        map_filter = None

    scoped_stats = [m["stats"].get(side) for m in matches_data]
    maps_lb = stats_mod._map_leaderboard(matches_data)

    return {
        "active_page": "matches",
        "sides": SIDES,
        "side": side,
        "map_filter": map_filter,
        "map_options": [{"value": m, **_map_view(m)} for m in map_options],
        "has_matches": bool(matches_data),
        "total_matches": len(matches_data),
        "kpis": _kpis(scoped_stats),
        "recent": _recent_strip(matches_data),
        "trend": _trend_series(matches_data, side),
        "map_cards": _map_cards(maps_lb, side),
        "rows": _match_rows(matches_data, side),
        "records": data["records"].get(side),
        "head_to_head": (data["head_to_head"].get(side) or [])[:10],
        "hitgroups": _round_hitgroups(data["hitgroups"].get(side) or []),
        "reason_split": _reason_split(matches_data, side),
    }


# --------------------------------------------------------------------------- #
# Barra empilhada: como os rounds são ganhos
# --------------------------------------------------------------------------- #

def _reason_split(matches_data, side):
    """rounds.reason agrupado — gravado desde sempre, nunca mostrado.
    Só conta round VENCIDO por você: "como você ganha" é a pergunta útil."""
    acc = {}
    total = 0
    for match in matches_data:
        for r in match.get("rounds") or []:
            if r["result"] != "win":
                continue
            if side != "all" and r["human_side"] != side:
                continue
            group = REASON_GROUP.get(r["reason"], "other")
            acc[group] = acc.get(group, 0) + 1
            total += 1
    if not total:
        return []
    order = ["elim", "bomb", "defuse", "time", "other"]
    return [
        {
            "key": group,
            "label": REASON_GROUP_LABEL[group],
            "count": acc[group],
            "pct": round(100 * acc[group] / total),
            "color": REASON_GROUP_COLOR[group],
        }
        for group in order
        if group in acc
    ]


# --------------------------------------------------------------------------- #
# Tela: uma partida
# --------------------------------------------------------------------------- #

def _compare_to_average(match, matches_data, side, keys):
    """Quanto cada métrica desta partida ficou acima/abaixo da sua média nas
    OUTRAS partidas. É o que transforma "ADR 102" em "ADR 102, +16 contra a
    sua média" — um número sozinho não diz se foi bom."""
    others = [
        m["stats"].get(side) for m in matches_data
        if m["id"] != match["id"] and m["stats"].get(side)
    ]
    mine = match["stats"].get(side) or {}
    result = {}
    for key in keys:
        baseline = _mean([o.get(key) for o in others])
        value = mine.get(key)
        result[key] = {
            "value": value,
            "baseline": baseline,
            "delta": None if (value is None or baseline is None) else value - baseline,
            "samples": len(others),
        }
    return result


def _radar(positions, map_name):
    """Posições do mundo em cima da imagem 2D do mapa.

    Dois modos, e a tela diz qual está em uso:

    - "world": há metadado do mapa em data/map_radar.json. A conversão é a
      oficial do jogo (ver world_to_radar), então o ponto cai no lugar certo
      da imagem de radar. Mapa de dois níveis (Nuke) vira duas camadas,
      separadas pela altitude que o próprio overview declara.
    - "bbox": mapa sem metadado. Cai na normalização pela área percorrida na
      partida — os agrupamentos continuam legíveis, mas não há imagem por
      trás e a forma do mapa não aparece.
    """
    if not positions:
        return None

    meta = radar_meta(map_name)
    raw_points = positions["points"]

    if meta:
        lower_max = meta.get("lower_level_max_units")
        levels = []
        if lower_max is None:
            groups = [(None, "Radar", raw_points)]
        else:
            upper = [p for p in raw_points if (p["z"] is None or p["z"] > lower_max)]
            lower = [p for p in raw_points if p["z"] is not None and p["z"] <= lower_max]
            groups = [("upper", "Nível superior", upper), ("lower", "Nível inferior", lower)]

        for key, label, group in groups:
            if not group and key is not None:
                continue
            points = []
            for p in group:
                u, v = world_to_radar(meta, p["x"], p["y"])
                points.append({
                    **p,
                    "weapon_label": weapon_label(p["weapon"]),
                    "cx": round(100 * u, 2),
                    "cy": round(100 * v, 2),
                })
            levels.append({
                "key": key or "default",
                "label": label,
                "image": _radar_image(map_name, key),
                "points": points,
                "kills": sum(1 for p in points if p["type"] == "kill"),
                "deaths": sum(1 for p in points if p["type"] == "death"),
            })
        # Abre no nível onde mais coisa aconteceu.
        levels.sort(key=lambda lv: -(lv["kills"] + lv["deaths"]))
        mode = "world"
    else:
        box = positions["bbox"]
        span_x = (box["max_x"] - box["min_x"]) or 1
        span_y = (box["max_y"] - box["min_y"]) or 1
        points = [
            {
                **p,
                "weapon_label": weapon_label(p["weapon"]),
                "cx": round(100 * (p["x"] - box["min_x"]) / span_x, 2),
                "cy": round(100 * (box["max_y"] - p["y"]) / span_y, 2),
            }
            for p in raw_points
        ]
        levels = [{
            "key": "default", "label": "Radar", "image": None, "points": points,
            "kills": sum(1 for p in points if p["type"] == "kill"),
            "deaths": sum(1 for p in points if p["type"] == "death"),
        }]
        mode = "bbox"

    return {
        "mode": mode,
        "levels": levels,
        "has_image": any(lv["image"] for lv in levels),
        "places": positions["places"][:8],
        "kills": sum(1 for p in raw_points if p["type"] == "kill"),
        "deaths": sum(1 for p in raw_points if p["type"] == "death"),
    }


BUY_COLOR = {"eco": "var(--loss)", "force": "var(--amber)", "full": "var(--win)"}
# Teto da barra de equipamento. 6.500 é o que um jogador carrega num full buy
# folgado (rifle + colete/capacete + quatro granadas + kit); acima disso a
# barra satura, e saturar é melhor que reescalar por partida — assim a mesma
# largura significa a mesma compra em qualquer partida.
EQUIP_BAR_MAX = 6500


def _round_blocks(match, side, loadout=None):
    """Timeline: um bloco por round, com motivo, entry e o seu K/D nele.

    `loadout` (stats.match_loadout) entra quando existe — só as partidas de
    .dem reprocessadas depois de PLAYER_PROPS têm. Round sem loadout mostra a
    linha sem a parte de economia, em vez de mostrar zero.
    """
    loadout = loadout or {}
    blocks = []
    mine = theirs = 0
    for r in match["rounds"]:
        if r["result"] == "win":
            mine += 1
        elif r["result"] == "loss":
            theirs += 1
        if side != "all" and r["human_side"] != side:
            continue
        group = REASON_GROUP.get(r["reason"], "other")
        blocks.append({
            "round_num": r["round_num"],
            "result": r["result"],
            "human_side": r["human_side"],
            "side_label": SIDE_LABEL.get(r["human_side"], "-"),
            "reason": r["reason"],
            "reason_label": REASON_LABEL.get(r["reason"], r["reason"] or "-"),
            "reason_group": group,
            "reason_color": REASON_GROUP_COLOR[group],
            "bomb_plant": r["bomb_plant"],
            "bomb_site": r["bomb_site"],
            "kills": r["kills"],
            "deaths": r["deaths"],
            "entry": r["entry"],
            "score_mine": mine,
            "score_theirs": theirs,
            "loadout": _loadout_view(loadout.get(r["round_num"])),
        })
    return blocks


def _loadout_view(entry):
    if not entry:
        return None
    equip = entry["equip_value"] or 0
    return {
        **entry,
        "buy_label": BUY_LABEL.get(entry["buy"], "—"),
        "buy_color": BUY_COLOR.get(entry["buy"], "var(--muted)"),
        "equip_bar": min(100, round(100 * equip / EQUIP_BAR_MAX)),
    }


def _loadout_summary(loadout):
    """Agregado da partida: quanto você compra, e quanto tempo passa cego."""
    if not loadout:
        return None
    rounds = list(loadout.values())
    equips = [r["equip_value"] for r in rounds if r["equip_value"] is not None]
    buys = {}
    for r in rounds:
        if r["buy"]:
            buys[r["buy"]] = buys.get(r["buy"], 0) + 1
    total = sum(buys.values())
    return {
        "rounds": len(rounds),
        "avg_equip": round(sum(equips) / len(equips)) if equips else None,
        "blind_time": round(sum(r["blind_time"] for r in rounds), 1),
        "flashes": sum(r["flashes"] for r in rounds),
        "buys": [
            {
                "key": key,
                "label": BUY_LABEL[key],
                "color": BUY_COLOR[key],
                "count": buys[key],
                "pct": round(100 * buys[key] / total),
            }
            for key in ("eco", "force", "full")
            if key in buys
        ],
    }


def build_detail_context(db_path, match_id, side="all"):
    """Contexto de GET /partidas/<id>. Devolve None quando a partida não
    existe — a rota transforma isso em 404."""
    if side not in dict(SIDES):
        side = "all"
    data = load_stats(db_path)
    match = next((m for m in data["matches"] if m["id"] == match_id), None)
    if match is None:
        return None

    s = match["stats"].get(side)
    comparison = _compare_to_average(
        match, data["matches"], side, ["adr", "kast_pct", "kd", "hs_pct"]
    )

    weapons = [
        {**w, **_weapon_view(w["weapon"], merged=True), "hs_pct": _pct(w["hs_pct"])}
        for w in (match["weapons"].get(side) or [])
    ]
    peak_dmg = max([w["dmg"] for w in weapons] or [0]) or 1
    for w in weapons:
        w["dmg_bar"] = round(100 * w["dmg"] / peak_dmg)

    feed = match["kill_feed"]
    if side != "all":
        feed = [e for e in feed if e["human_side"] == side]
    feed = [{**e, **_weapon_view(e["weapon"])} for e in feed]

    rounds = match["rounds"]
    reason_split = _reason_split([match], side)
    loadout = match_loadout(db_path, match_id)

    return {
        "active_page": "matches",
        "sides": SIDES,
        "side": side,
        "match": match,
        "map": _map_view(match["map"]),
        "played_at": _fmt_date(match["played_at"]),
        "series": _series_tag(match["series_num_maps"]),
        "stats": s,
        "comparison": comparison,
        "weapons": weapons,
        "hitgroups": _round_hitgroups(match["hitgroups"].get(side) or []),
        "hitgroup_order": HITGROUP_ORDER,
        "head_to_head": match["head_to_head"].get(side) or [],
        "rounds": _round_blocks(match, side, loadout),
        "total_rounds": len(rounds),
        "reason_split": reason_split,
        "loadout_summary": _loadout_summary(loadout),
        "feed": feed,
        "radar": _radar(match_positions(db_path, match_id), match["map"]),
        "ct_stats": match["stats"].get("ct"),
        "t_stats": match["stats"].get("t"),
        "bombsites": match["bombsites"].get(side) or [],
        "longest_kill": match["longest_kill"].get(side),
    }
