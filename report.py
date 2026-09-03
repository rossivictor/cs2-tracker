#!/usr/bin/env python3
"""
CS2 Tracker — Report
=====================
Gera um relatório HTML estático a partir do cs2_tracker.db: dashboard
com stats agregados + lista clicável de partidas, e uma página de
detalhe por partida (quadro de armas, linha do tempo de rounds, feed de
kills/mortes). Tudo num único .html — os dados vão embutidos como JSON
inline e a navegação entre dashboard/detalhe é feita em JS puro via
location.hash, sem servidor, sem build, sem fetch (evita problema de
CORS ao abrir o arquivo direto via file://).

Uso:
    .venv\\Scripts\\python.exe report.py --db cs2_tracker.db --out report.html
"""

import argparse
import json
import sqlite3
import webbrowser
from pathlib import Path


def fetch_matches(conn):
    return conn.execute(
        """SELECT id, demo_name, map, played_at, score_ct, score_t, duration_minutes, player_name
           FROM matches ORDER BY played_at"""
    ).fetchall()


def _dominant_side_by_round(conn, match_id):
    """Lado que o jogador humano mais apareceu em cada round (via
    player_positions) — necessário pra comparar com rounds.winner_side,
    já que os lados trocam na metade da partida."""
    side_counts = conn.execute(
        """SELECT round_num, side, COUNT(*) FROM player_positions
           WHERE match_id=? GROUP BY round_num, side""",
        (match_id,),
    ).fetchall()
    dominant = {}
    for round_num, side, count in side_counts:
        if round_num not in dominant or count > dominant[round_num][1]:
            dominant[round_num] = (side, count)
    return {r: side for r, (side, _count) in dominant.items()}


def per_match_stats(conn, match_id, dominant_side):
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
    rounds = conn.execute(
        "SELECT round_num, winner_side FROM rounds WHERE match_id=?", (match_id,)
    ).fetchall()

    wins, decided = 0, 0
    for round_num, winner_side in rounds:
        human_side = dominant_side.get(round_num)
        if human_side is None:
            continue
        decided += 1
        if human_side == winner_side:
            wins += 1

    rounds_played = len(rounds)
    return {
        "kills": kills,
        "deaths": deaths,
        "kd": kills / deaths if deaths else float(kills),
        "hs_pct": (100 * hs_kills / kills) if kills else 0.0,
        "adr": (dmg / rounds_played) if rounds_played else 0.0,
        "rounds_played": rounds_played,
        "round_wins": wins,
        "round_win_pct": (100 * wins / decided) if decided else 0.0,
    }


def weapon_breakdown(conn, match_id):
    kills_by_weapon = dict(
        conn.execute(
            """SELECT weapon, COUNT(*) FROM kills
               WHERE match_id=? AND attacker_is_human=1 GROUP BY weapon""",
            (match_id,),
        ).fetchall()
    )
    hs_by_weapon = dict(
        conn.execute(
            """SELECT weapon, COUNT(*) FROM kills
               WHERE match_id=? AND attacker_is_human=1 AND headshot=1 GROUP BY weapon""",
            (match_id,),
        ).fetchall()
    )
    dmg_by_weapon = dict(
        conn.execute(
            """SELECT weapon, SUM(dmg_health) FROM damages
               WHERE match_id=? AND attacker_is_human=1 GROUP BY weapon""",
            (match_id,),
        ).fetchall()
    )

    weapons = set(kills_by_weapon) | set(dmg_by_weapon)
    rows = [
        {
            "weapon": w,
            "kills": kills_by_weapon.get(w, 0),
            "headshots": hs_by_weapon.get(w, 0),
            "dmg": dmg_by_weapon.get(w, 0) or 0,
        }
        for w in weapons
    ]
    rows.sort(key=lambda r: (-r["kills"], -r["dmg"]))
    return rows


def round_timeline(conn, match_id, dominant_side):
    rounds = conn.execute(
        """SELECT round_num, winner_side, reason, bomb_plant, bomb_site
           FROM rounds WHERE match_id=? ORDER BY round_num""",
        (match_id,),
    ).fetchall()
    kd_by_round = {}
    for round_num, k, d in conn.execute(
        """SELECT round_num, SUM(attacker_is_human), SUM(victim_is_human)
           FROM kills WHERE match_id=? GROUP BY round_num""",
        (match_id,),
    ).fetchall():
        kd_by_round[round_num] = (k or 0, d or 0)

    rows = []
    for round_num, winner_side, reason, bomb_plant, bomb_site in rounds:
        human_side = dominant_side.get(round_num)
        k, d = kd_by_round.get(round_num, (0, 0))
        result = "-" if human_side is None else ("win" if human_side == winner_side else "loss")
        rows.append({
            "round_num": round_num,
            "winner_side": winner_side,
            "reason": reason,
            "bomb_plant": bool(bomb_plant),
            "bomb_site": bomb_site,
            "human_side": human_side,
            "result": result,
            "kills": k,
            "deaths": d,
        })
    return rows


def kill_feed(conn, match_id):
    rows = conn.execute(
        """SELECT round_num, tick, attacker_name, attacker_is_human, victim_name,
                  victim_is_human, weapon, headshot, distance
           FROM kills WHERE match_id=? AND (attacker_is_human=1 OR victim_is_human=1)
           ORDER BY tick""",
        (match_id,),
    ).fetchall()

    feed = []
    for (round_num, tick, attacker_name, attacker_is_human, victim_name,
         victim_is_human, weapon, headshot, distance) in rows:
        if attacker_is_human:
            kind, opponent = "kill", victim_name or "bot"
        else:
            kind, opponent = "death", attacker_name or "bot"
        feed.append({
            "round_num": round_num,
            "tick": tick,
            "type": kind,
            "opponent": opponent,
            "weapon": weapon,
            "headshot": bool(headshot),
            "distance": round(distance, 0) if distance is not None else None,
        })
    return feed


def build_match_data(conn, row):
    (mid, demo_name, map_name, played_at, score_ct, score_t, duration_minutes, player_name) = row
    dominant_side = _dominant_side_by_round(conn, mid)
    return {
        "id": mid,
        "demo_name": demo_name,
        "map": map_name,
        "played_at": played_at,
        "score_ct": score_ct,
        "score_t": score_t,
        "duration_minutes": duration_minutes,
        "player_name": player_name,
        "stats": per_match_stats(conn, mid, dominant_side),
        "weapons": weapon_breakdown(conn, mid),
        "rounds": round_timeline(conn, mid, dominant_side),
        "kill_feed": kill_feed(conn, mid),
    }


TEMPLATE = """<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>CS2 Tracker — Relatório</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; background: #0f1115; color: #e8e8e8; margin: 0; padding: 32px; }
  h1 { margin-top: 0; }
  h2 { font-size: 18px; color: #cfd3da; margin: 28px 0 8px; }
  a { color: #5eb1ff; }
  .cards { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  .card { background: #1a1d24; border-radius: 10px; padding: 16px 24px; min-width: 120px; }
  .card .value { font-size: 28px; font-weight: 700; }
  .card .label { font-size: 13px; color: #9aa0aa; text-transform: uppercase; letter-spacing: .04em; }
  .table-wrap { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; margin-top: 8px; }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #2a2e37; font-size: 14px; white-space: nowrap; }
  th { color: #9aa0aa; font-weight: 600; }
  canvas { max-width: 100%; background: #1a1d24; border-radius: 10px; padding: 16px; box-sizing: border-box; }
  .clickable-row { cursor: pointer; }
  .clickable-row:hover { background: #1a1d24; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
  .pill.win { background: #16351f; color: #7be08a; }
  .pill.loss { background: #3a1a1a; color: #ff8a8a; }
  .pill.neutral { background: #2a2e37; color: #9aa0aa; }
  .back { display: inline-block; margin-bottom: 16px; cursor: pointer; }
  .kill { color: #7be08a; }
  .death { color: #ff8a8a; }
  #match-view { display: none; }
</style>
</head>
<body>

<div id="dashboard-view">
  <h1>CS2 Tracker — Dashboard</h1>
  <div class="cards" id="summary-cards"></div>
  <canvas id="trend" height="90"></canvas>
  <h2>Partidas</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Data</th><th>Mapa</th><th>Placar</th><th>K</th><th>D</th><th>K/D</th><th>ADR</th><th>HS%</th><th>Round win%</th></tr>
      </thead>
      <tbody id="matches-tbody"></tbody>
    </table>
  </div>
</div>

<div id="match-view">
  <span class="back" onclick="location.hash=''">&larr; voltar ao dashboard</span>
  <h1 id="match-title"></h1>
  <div class="cards" id="match-cards"></div>

  <h2>Armas</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Arma</th><th>Kills</th><th>Headshots</th><th>Dano</th></tr></thead>
      <tbody id="weapons-tbody"></tbody>
    </table>
  </div>

  <h2>Linha do tempo de rounds</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Round</th><th>Resultado</th><th>Vencedor</th><th>Motivo</th><th>Bomba</th><th>Seu K/D no round</th></tr></thead>
      <tbody id="rounds-tbody"></tbody>
    </table>
  </div>

  <h2>Feed de kills/mortes</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Round</th><th>Evento</th><th>Contra</th><th>Arma</th><th>HS</th><th>Distância</th></tr></thead>
      <tbody id="feed-tbody"></tbody>
    </table>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;

const REASON_LABEL = {
  bomb_defused: "Bomba defusada",
  bomb_exploded: "Bomba explodiu",
  t_killed: "Terroristas eliminados",
  ct_killed: "CTs eliminados",
};
const SIDE_LABEL = { ct: "CT", t: "TR" };
const WEAPON_LABEL = {
  hkp2000: "P2000", glock: "Glock-18", usp_silencer: "USP-S", p250: "P250",
  fiveseven: "Five-SeveN", tec9: "Tec-9", cz75a: "CZ75-Auto", deagle: "Desert Eagle",
  elite: "Dual Berettas", revolver: "R8 Revolver",
  mac10: "MAC-10", mp9: "MP9", mp7: "MP7", mp5sd: "MP5-SD", ump45: "UMP-45", p90: "P90", bizon: "PP-Bizon",
  ak47: "AK-47", m4a1: "M4A4", m4a1_silencer: "M4A1-S", famas: "FAMAS", galilar: "Galil AR",
  aug: "AUG", sg556: "SG 553", awp: "AWP", ssg08: "SSG 08", scar20: "SCAR-20", g3sg1: "G3SG1",
  nova: "Nova", xm1014: "XM1014", mag7: "MAG-7", sawedoff: "Sawed-Off",
  m249: "M249", negev: "Negev",
  hegrenade: "Granada HE", flashbang: "Flashbang", smokegrenade: "Smoke", molotov: "Molotov",
  inferno: "Incendiário/Molotov", decoy: "Decoy", knife: "Faca", knife_t: "Faca",
  planted_c4: "Bomba (C4)", taser: "Zeus x27",
};
function label(map, key) { return map[key] || key; }

function fmtDate(iso) { return iso ? iso.replace("T", " ").slice(0, 16) : ""; }

function card(value, lbl) {
  return `<div class="card"><div class="value">${value}</div><div class="label">${lbl}</div></div>`;
}

function summaryCards(matches) {
  const totalKills = matches.reduce((s, m) => s + m.stats.kills, 0);
  const totalDeaths = matches.reduce((s, m) => s + m.stats.deaths, 0);
  const totalRounds = matches.reduce((s, m) => s + m.stats.rounds_played, 0);
  const totalDmg = matches.reduce((s, m) => s + m.stats.adr * m.stats.rounds_played, 0);
  const totalWins = matches.reduce((s, m) => s + m.stats.round_wins, 0);
  const totalHs = matches.reduce((s, m) => s + Math.round(m.stats.hs_pct / 100 * m.stats.kills), 0);
  const kd = totalDeaths ? totalKills / totalDeaths : totalKills;
  const adr = totalRounds ? totalDmg / totalRounds : 0;
  const hsPct = totalKills ? 100 * totalHs / totalKills : 0;
  const winPct = totalRounds ? 100 * totalWins / totalRounds : 0;
  return [
    card(matches.length, "Partidas"),
    card(kd.toFixed(2), "K/D"),
    card(adr.toFixed(1), "ADR médio"),
    card(hsPct.toFixed(0) + "%", "Headshot %"),
    card(winPct.toFixed(0) + "%", "Round win rate"),
  ].join("");
}

function renderDashboard() {
  document.getElementById("dashboard-view").style.display = "";
  document.getElementById("match-view").style.display = "none";

  if (DATA.length === 0) {
    document.getElementById("summary-cards").innerHTML = "<p>Nenhuma partida no banco ainda.</p>";
    return;
  }

  document.getElementById("summary-cards").innerHTML = summaryCards(DATA);

  document.getElementById("matches-tbody").innerHTML = DATA.map(m => `
    <tr class="clickable-row" onclick="location.hash='match-${m.id}'">
      <td>${fmtDate(m.played_at)}</td>
      <td>${m.map}</td>
      <td>${m.score_ct}:${m.score_t}</td>
      <td>${m.stats.kills}</td>
      <td>${m.stats.deaths}</td>
      <td>${m.stats.kd.toFixed(2)}</td>
      <td>${m.stats.adr.toFixed(1)}</td>
      <td>${m.stats.hs_pct.toFixed(0)}%</td>
      <td>${m.stats.round_win_pct.toFixed(0)}%</td>
    </tr>`).join("");

  if (window._trendChart) window._trendChart.destroy();
  window._trendChart = new Chart(document.getElementById('trend'), {
    type: 'line',
    data: {
      labels: DATA.map(m => fmtDate(m.played_at)),
      datasets: [
        { label: 'K/D', data: DATA.map(m => Math.round(m.stats.kd * 100) / 100), borderColor: '#5eb1ff', yAxisID: 'y', tension: 0.25 },
        { label: 'ADR', data: DATA.map(m => Math.round(m.stats.adr * 10) / 10), borderColor: '#ff9f5e', yAxisID: 'y1', tension: 0.25 }
      ]
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y: { type: 'linear', position: 'left', title: { display: true, text: 'K/D' } },
        y1: { type: 'linear', position: 'right', title: { display: true, text: 'ADR' }, grid: { drawOnChartArea: false } }
      }
    }
  });
}

function renderMatch(id) {
  const m = DATA.find(x => x.id === id);
  if (!m) { location.hash = ''; return; }

  document.getElementById("dashboard-view").style.display = "none";
  document.getElementById("match-view").style.display = "block";

  document.getElementById("match-title").textContent =
    `${m.map} — ${m.score_ct}:${m.score_t} — ${fmtDate(m.played_at)}`;

  document.getElementById("match-cards").innerHTML = [
    card(m.stats.kills, "Kills"),
    card(m.stats.deaths, "Deaths"),
    card(m.stats.kd.toFixed(2), "K/D"),
    card(m.stats.adr.toFixed(1), "ADR"),
    card(m.stats.hs_pct.toFixed(0) + "%", "Headshot %"),
    card(m.stats.round_win_pct.toFixed(0) + "%", "Round win rate"),
    card(m.duration_minutes + " min", "Duração"),
  ].join("");

  document.getElementById("weapons-tbody").innerHTML = m.weapons.map(w => `
    <tr>
      <td>${label(WEAPON_LABEL, w.weapon)}</td>
      <td>${w.kills}</td>
      <td>${w.headshots}</td>
      <td>${w.dmg}</td>
    </tr>`).join("") || `<tr><td colspan="4">Sem dados de arma.</td></tr>`;

  document.getElementById("rounds-tbody").innerHTML = m.rounds.map(r => `
    <tr>
      <td>${r.round_num}</td>
      <td><span class="pill ${r.result}">${r.result === 'win' ? 'Vitória' : r.result === 'loss' ? 'Derrota' : '-'}</span></td>
      <td>${label(SIDE_LABEL, r.winner_side)}</td>
      <td>${label(REASON_LABEL, r.reason)}</td>
      <td>${r.bomb_plant ? ('Sim (' + (r.bomb_site || '?') + ')') : '-'}</td>
      <td><span class="kill">${r.kills}</span> / <span class="death">${r.deaths}</span></td>
    </tr>`).join("");

  document.getElementById("feed-tbody").innerHTML = m.kill_feed.map(e => `
    <tr>
      <td>${e.round_num}</td>
      <td class="${e.type}">${e.type === 'kill' ? 'Kill' : 'Morte'}</td>
      <td>${e.opponent}</td>
      <td>${label(WEAPON_LABEL, e.weapon)}</td>
      <td>${e.headshot ? 'HS' : '-'}</td>
      <td>${e.distance != null ? e.distance + 'u' : '-'}</td>
    </tr>`).join("") || `<tr><td colspan="6">Sem eventos.</td></tr>`;
}

function render() {
  const hash = location.hash.slice(1);
  if (hash.startsWith("match-")) {
    renderMatch(parseInt(hash.slice(6), 10));
  } else {
    renderDashboard();
  }
}
window.addEventListener("hashchange", render);
render();
</script>
</body>
</html>"""


def build_html(matches_data):
    payload = json.dumps(matches_data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA_JSON__", payload)


def generate_report(db_path, out_path):
    conn = sqlite3.connect(db_path)
    matches_data = [build_match_data(conn, row) for row in fetch_matches(conn)]
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
