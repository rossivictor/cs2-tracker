#!/usr/bin/env python3
"""
CS2 Tracker — Home
====================
Gera a tela inicial (docs/features/M3.5-home.md) como .html estático, no
mesmo modelo do report.py: sem servidor, gerado a partir do
cs2_tracker.db toda vez que uma partida é ingerida (ver watcher.py). Ao
contrário do relatório, a home é renderizada no servidor (Jinja, em tempo
de build) — não há tabela grande o bastante aqui pra justificar reimplementar
side-toggle e paginação em JS.

Uso:
    .venv\\Scripts\\python.exe home.py --db cs2_tracker.db --out index.html
"""

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import DB_PATH, HOME_PATH
from stats import load_stats, map_bg_path, map_icon_path, map_label, weapon_icon_path, weapon_label

ROOT = Path(__file__).resolve().parent

RECENT_MATCHES_LIMIT = 5
MIN_MATCHES_FOR_BEST_MAP = 3


def _fmt_date(iso):
    return iso.replace("T", " ")[:16] if iso else ""


def _match_row(match):
    stats = match["stats"].get("all")
    return {
        "id": match["id"],
        "map_label": map_label(match["map"]),
        "map_icon": map_icon_path(match["map"]),
        "score_mine": match["score_mine"],
        "score_theirs": match["score_theirs"],
        "outcome": match["outcome"],
        "played_at": _fmt_date(match["played_at"]),
        "kd_label": f'{stats["kills"]}/{stats["deaths"]}' if stats else "-",
        "adr": f'{stats["adr"]:.1f}' if stats and stats.get("adr") is not None else "-",
        "hs_pct": f'{stats["hs_pct"]:.0f}%' if stats else "-",
    }


def _best_map_view(row):
    if row is None:
        return None
    s = row["stats"]["all"]
    return {
        "map_label": map_label(row["map"]),
        "map_icon": map_icon_path(row["map"]),
        "map_bg": map_bg_path(row["map"]),
        "matches": s["matches"],
        "win_pct": f'{s["round_win_pct"]:.0f}%' if s.get("round_win_pct") is not None else "-",
        "adr": f'{s["adr"]:.1f}' if s.get("adr") is not None else "-",
        "kd": f'{s["kd"]:.2f}',
        "hs_pct": f'{s["hs_pct"]:.0f}%',
    }


def _top_weapon_view(weapons):
    if not weapons:
        return None
    w = weapons[0]
    return {
        "weapon_label": weapon_label(w["weapon"]),
        "icon": weapon_icon_path(w["weapon"]),
        "dmg_total": f'{w["dmg"]:,}'.replace(",", "."),
        "kills": w["kills"],
        "dmg_share_pct": f'{w["dmg_share_pct"]:.0f}%' if w.get("dmg_share_pct") is not None else "-",
    }


def _sides_view(sides, matches_data):
    ct, t = sides.get("ct"), sides.get("t")
    if not ct and not t:
        return None
    total_matches = len({m["id"] for m in matches_data})
    return {
        "ct_pct": ct["round_win_pct"] if ct and ct.get("round_win_pct") is not None else 0,
        "t_pct": t["round_win_pct"] if t and t.get("round_win_pct") is not None else 0,
        "total_matches": total_matches,
    }


def _half_donut_dasharray(pct):
    """Arco de 180° com raio 46 (mesmo path do protótipo) — comprimento
    total ~144.5. pct em 0-100."""
    arc_len = 144.51
    return f"{arc_len * pct / 100:.1f} {arc_len:.1f}"


def build_context(db_path):
    data = load_stats(db_path)
    matches_data = data["matches"]
    has_matches = bool(matches_data)

    recent = sorted(matches_data, key=lambda m: m["played_at"] or "", reverse=True)[:RECENT_MATCHES_LIMIT]
    best_map_view = _best_map_view(data["best_map"])
    top_weapon = _top_weapon_view(data["weapons"])
    sides = _sides_view(data["sides"], matches_data)

    ctx = {
        "active_page": "home",
        "has_matches": has_matches,
        "recent_matches": [_match_row(m) for m in recent],
        "best_map": best_map_view,
        "best_map_min_matches": MIN_MATCHES_FOR_BEST_MAP,
        "top_weapon": top_weapon,
        "sides": sides,
    }
    if sides:
        ctx["sides"]["ct_dasharray"] = _half_donut_dasharray(sides["ct_pct"])
        ctx["sides"]["t_dasharray"] = _half_donut_dasharray(sides["t_pct"])
    return ctx


def generate_home(db_path, out_path):
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("home.html")
    html = template.render(**build_context(db_path))

    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")
    print(f"[HOME] home gerada em {out_path.resolve()}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Home (SQLite -> HTML local)")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--out", default=HOME_PATH)
    args = parser.parse_args()
    generate_home(args.db, args.out)


if __name__ == "__main__":
    main()
