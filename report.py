#!/usr/bin/env python3
"""
CS2 Tracker — Report
=====================
Gera um relatório HTML estático a partir do cs2_tracker.db: K/D, ADR,
headshot %, taxa de vitória de round e evolução por partida (gráfico).
Não depende de servidor nem de build — o .html gerado abre direto no
navegador, sem precisar de nada além do arquivo em si (Chart.js vem via
CDN, carregado quando você abrir o arquivo).

Uso:
    .venv\\Scripts\\python.exe report.py --db cs2_tracker.db --out report.html
"""

import argparse
import html
import sqlite3
import webbrowser
from pathlib import Path


def fetch_matches(conn):
    return conn.execute(
        """SELECT id, demo_name, map, played_at, score_ct, score_t, duration_minutes, player_name
           FROM matches ORDER BY played_at"""
    ).fetchall()


def round_win_rate(conn, match_id):
    """Compara o lado do jogador humano em cada round com o vencedor do
    round — precisa disso (em vez de comparar direto score_ct/score_t)
    porque os lados trocam na virada de metade da partida."""
    rounds = conn.execute(
        "SELECT round_num, winner_side FROM rounds WHERE match_id=?", (match_id,)
    ).fetchall()
    side_counts = conn.execute(
        """SELECT round_num, side, COUNT(*) FROM player_positions
           WHERE match_id=? GROUP BY round_num, side""",
        (match_id,),
    ).fetchall()

    dominant_side = {}
    for round_num, side, count in side_counts:
        if round_num not in dominant_side or count > dominant_side[round_num][1]:
            dominant_side[round_num] = (side, count)

    wins, decided_rounds = 0, 0
    for round_num, winner_side in rounds:
        human_side = dominant_side.get(round_num, (None, 0))[0]
        if human_side is None:
            continue
        decided_rounds += 1
        if human_side == winner_side:
            wins += 1
    return wins, decided_rounds


def per_match_stats(conn, match_id):
    kills = conn.execute(
        "SELECT COUNT(*) FROM kills WHERE match_id=? AND attacker_is_human=1", (match_id,)
    ).fetchone()[0]
    deaths = conn.execute(
        "SELECT COUNT(*) FROM kills WHERE match_id=? AND victim_is_human=1", (match_id,)
    ).fetchone()[0]
    hs_kills = conn.execute(
        "SELECT COUNT(*) FROM kills WHERE match_id=? AND attacker_is_human=1 AND headshot=1",
        (match_id,),
    ).fetchone()[0]
    dmg = conn.execute(
        "SELECT COALESCE(SUM(dmg_health),0) FROM damages WHERE match_id=? AND attacker_is_human=1",
        (match_id,),
    ).fetchone()[0]
    rounds_played = conn.execute(
        "SELECT COUNT(*) FROM rounds WHERE match_id=?", (match_id,)
    ).fetchone()[0]
    wins, decided_rounds = round_win_rate(conn, match_id)

    return {
        "kills": kills,
        "deaths": deaths,
        "kd": kills / deaths if deaths else float(kills),
        "hs_pct": (100 * hs_kills / kills) if kills else 0.0,
        "adr": (dmg / rounds_played) if rounds_played else 0.0,
        "rounds_played": rounds_played,
        "round_wins": wins,
        "round_win_pct": (100 * wins / decided_rounds) if decided_rounds else 0.0,
    }


def build_html(matches_data):
    if not matches_data:
        return "<h1>CS2 Tracker</h1><p>Nenhuma partida no banco ainda.</p>"

    total_kills = sum(m["stats"]["kills"] for m in matches_data)
    total_deaths = sum(m["stats"]["deaths"] for m in matches_data)
    total_dmg_rounds = sum(m["stats"]["rounds_played"] for m in matches_data)
    total_dmg = sum(m["stats"]["adr"] * m["stats"]["rounds_played"] for m in matches_data)
    total_round_wins = sum(m["stats"]["round_wins"] for m in matches_data)
    total_hs_kills = sum(
        round(m["stats"]["hs_pct"] / 100 * m["stats"]["kills"]) for m in matches_data
    )

    summary = {
        "matches": len(matches_data),
        "kd": total_kills / total_deaths if total_deaths else float(total_kills),
        "adr": total_dmg / total_dmg_rounds if total_dmg_rounds else 0.0,
        "hs_pct": (100 * total_hs_kills / total_kills) if total_kills else 0.0,
        "round_win_pct": (100 * total_round_wins / total_dmg_rounds) if total_dmg_rounds else 0.0,
    }

    labels = [html.escape(m["played_at"][:16]) for m in matches_data]
    kd_series = [round(m["stats"]["kd"], 2) for m in matches_data]
    adr_series = [round(m["stats"]["adr"], 1) for m in matches_data]

    rows_html = "\n".join(
        f"""<tr>
            <td>{html.escape(m["played_at"][:16])}</td>
            <td>{html.escape(m["map"])}</td>
            <td>{m["score_ct"]}:{m["score_t"]}</td>
            <td>{m["stats"]["kills"]}</td>
            <td>{m["stats"]["deaths"]}</td>
            <td>{m["stats"]["kd"]:.2f}</td>
            <td>{m["stats"]["adr"]:.1f}</td>
            <td>{m["stats"]["hs_pct"]:.0f}%</td>
            <td>{m["stats"]["round_win_pct"]:.0f}%</td>
        </tr>"""
        for m in matches_data
    )

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>CS2 Tracker — Relatório</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; background: #0f1115; color: #e8e8e8; margin: 0; padding: 32px; }}
  h1 {{ margin-top: 0; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 32px; }}
  .card {{ background: #1a1d24; border-radius: 10px; padding: 16px 24px; min-width: 120px; }}
  .card .value {{ font-size: 28px; font-weight: 700; }}
  .card .label {{ font-size: 13px; color: #9aa0aa; text-transform: uppercase; letter-spacing: .04em; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #2a2e37; font-size: 14px; }}
  th {{ color: #9aa0aa; font-weight: 600; }}
  canvas {{ max-width: 100%; background: #1a1d24; border-radius: 10px; padding: 16px; box-sizing: border-box; }}
</style>
</head>
<body>
<h1>CS2 Tracker — Relatório</h1>

<div class="cards">
  <div class="card"><div class="value">{summary["matches"]}</div><div class="label">Partidas</div></div>
  <div class="card"><div class="value">{summary["kd"]:.2f}</div><div class="label">K/D</div></div>
  <div class="card"><div class="value">{summary["adr"]:.1f}</div><div class="label">ADR médio</div></div>
  <div class="card"><div class="value">{summary["hs_pct"]:.0f}%</div><div class="label">Headshot %</div></div>
  <div class="card"><div class="value">{summary["round_win_pct"]:.0f}%</div><div class="label">Round win rate</div></div>
</div>

<canvas id="trend" height="90"></canvas>

<table>
<thead>
<tr><th>Data</th><th>Mapa</th><th>Placar</th><th>K</th><th>D</th><th>K/D</th><th>ADR</th><th>HS%</th><th>Round win%</th></tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>

<script>
new Chart(document.getElementById('trend'), {{
  type: 'line',
  data: {{
    labels: {labels},
    datasets: [
      {{ label: 'K/D', data: {kd_series}, borderColor: '#5eb1ff', yAxisID: 'y', tension: 0.25 }},
      {{ label: 'ADR', data: {adr_series}, borderColor: '#ff9f5e', yAxisID: 'y1', tension: 0.25 }}
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    scales: {{
      y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'K/D' }} }},
      y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'ADR' }}, grid: {{ drawOnChartArea: false }} }}
    }}
  }}
}});
</script>
</body>
</html>"""


def generate_report(db_path, out_path):
    conn = sqlite3.connect(db_path)
    matches = fetch_matches(conn)

    matches_data = []
    for (mid, demo_name, map_name, played_at, score_ct, score_t, duration_minutes, player_name) in matches:
        matches_data.append({
            "id": mid,
            "demo_name": demo_name,
            "map": map_name,
            "played_at": played_at,
            "score_ct": score_ct,
            "score_t": score_t,
            "duration_minutes": duration_minutes,
            "player_name": player_name,
            "stats": per_match_stats(conn, mid),
        })
    conn.close()

    out_path = Path(out_path)
    out_path.write_text(build_html(matches_data), encoding="utf-8")
    print(f"[REPORT] {len(matches_data)} partida(s) — relatório gerado em {out_path.resolve()}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Report (SQLite -> HTML local)")
    parser.add_argument("--db", default="./cs2_tracker.db")
    parser.add_argument("--out", default="./report.html")
    parser.add_argument("--open", action="store_true", help="Abre o relatório no navegador ao terminar")
    args = parser.parse_args()

    out_path = generate_report(args.db, args.out)
    if args.open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
