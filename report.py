#!/usr/bin/env python3
"""
CS2 Tracker — Report
=====================
Gera um relatório HTML estático a partir do cs2_tracker.db: dashboard
com stats agregados + lista clicável de partidas, e uma página de
detalhe por partida (quadro de armas, linha do tempo de rounds, feed de
kills/mortes). Toda estatística (cards, quadro de armas, linha do tempo,
feed) vem em 3 variantes — Geral / CT / TR — trocadas por um toggle na
própria página, sem recarregar. Tudo num único .html — os dados vão
embutidos como JSON inline e a navegação entre dashboard/detalhe é feita
em JS puro via location.hash, sem servidor, sem build, sem fetch (evita
problema de CORS ao abrir o arquivo direto via file://).

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
    já que os lados trocam na metade da partida, e pra separar as
    estatísticas em Geral/CT/TR."""
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


def _fetch_match_raw(conn, match_id):
    rounds = conn.execute(
        """SELECT round_num, winner_side, reason, bomb_plant, bomb_site
           FROM rounds WHERE match_id=? ORDER BY round_num""",
        (match_id,),
    ).fetchall()
    kills = conn.execute(
        """SELECT round_num, tick, attacker_name, attacker_is_human, victim_name,
                  victim_is_human, weapon, headshot, distance
           FROM kills WHERE match_id=? ORDER BY tick""",
        (match_id,),
    ).fetchall()
    damages = conn.execute(
        """SELECT round_num, attacker_is_human, victim_is_human, weapon, dmg_health
           FROM damages WHERE match_id=?""",
        (match_id,),
    ).fetchall()
    return rounds, kills, damages


def _side_round_nums(rounds, dominant_side, side):
    if side is None:
        return {r["round_num"] for r in rounds}
    return {r["round_num"] for r in rounds if dominant_side.get(r["round_num"]) == side}


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

    return {
        "kills": my_kills_count,
        "deaths": my_deaths_count,
        "kd": my_kills_count / my_deaths_count if my_deaths_count else float(my_kills_count),
        "hs_pct": (100 * hs_kills / my_kills_count) if my_kills_count else 0.0,
        "adr": my_dmg / rounds_played,
        "rounds_played": rounds_played,
        "round_wins": wins,
        "round_win_pct": 100 * wins / rounds_played,
    }


def _weapons_for_round_nums(kills, damages, round_nums):
    scoped_kills = [k for k in kills if k["round_num"] in round_nums and k["attacker_is_human"]]
    scoped_damages = [d for d in damages if d["round_num"] in round_nums and d["attacker_is_human"]]

    kills_by_weapon, hs_by_weapon, dmg_by_weapon = {}, {}, {}
    for k in scoped_kills:
        kills_by_weapon[k["weapon"]] = kills_by_weapon.get(k["weapon"], 0) + 1
        if k["headshot"]:
            hs_by_weapon[k["weapon"]] = hs_by_weapon.get(k["weapon"], 0) + 1
    for d in scoped_damages:
        dmg_by_weapon[d["weapon"]] = dmg_by_weapon.get(d["weapon"], 0) + (d["dmg_health"] or 0)

    weapons = set(kills_by_weapon) | set(dmg_by_weapon)
    rows = [
        {
            "weapon": w,
            "kills": kills_by_weapon.get(w, 0),
            "headshots": hs_by_weapon.get(w, 0),
            "dmg": dmg_by_weapon.get(w, 0),
        }
        for w in weapons
    ]
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

    rows = []
    for r in rounds:
        round_num = r["round_num"]
        human_side = dominant_side.get(round_num)
        k, d = kd_by_round.get(round_num, (0, 0))
        result = "-" if human_side is None else ("win" if human_side == r["winner_side"] else "loss")
        rows.append({
            "round_num": round_num,
            "winner_side": r["winner_side"],
            "reason": r["reason"],
            "bomb_plant": bool(r["bomb_plant"]),
            "bomb_site": r["bomb_site"],
            "human_side": human_side,
            "result": result,
            "kills": k,
            "deaths": d,
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


def build_match_data(conn, row):
    mid = row["id"]
    dominant_side = _dominant_side_by_round(conn, mid)
    rounds, kills, damages = _fetch_match_raw(conn, mid)

    scopes = {
        "all": _side_round_nums(rounds, dominant_side, None),
        "ct": _side_round_nums(rounds, dominant_side, "ct"),
        "t": _side_round_nums(rounds, dominant_side, "t"),
    }

    return {
        "id": mid,
        "demo_name": row["demo_name"],
        "map": row["map"],
        "played_at": row["played_at"],
        "score_ct": row["score_ct"],
        "score_t": row["score_t"],
        "duration_minutes": row["duration_minutes"],
        "player_name": row["player_name"],
        "stats": {
            side: _stats_for_round_nums(rounds, kills, damages, dominant_side, nums)
            for side, nums in scopes.items()
        },
        "weapons": {
            side: _weapons_for_round_nums(kills, damages, nums)
            for side, nums in scopes.items()
        },
        "rounds": _round_timeline(rounds, kills, dominant_side),
        "kill_feed": _kill_feed(kills, dominant_side),
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
  .side-toggle { display: flex; gap: 8px; margin-bottom: 20px; }
  .side-toggle button {
    background: #1a1d24; color: #9aa0aa; border: 1px solid #2a2e37; border-radius: 8px;
    padding: 6px 16px; font-size: 13px; font-weight: 600; cursor: pointer;
  }
  .side-toggle button.active { background: #5eb1ff; color: #0f1115; border-color: #5eb1ff; }
  #match-view { display: none; }
</style>
</head>
<body>

<div id="dashboard-view">
  <h1>CS2 Tracker — Dashboard</h1>
  <div class="side-toggle" id="dashboard-toggle"></div>
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
  <div class="side-toggle" id="match-toggle"></div>
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
      <thead><tr><th>Round</th><th>Seu lado</th><th>Resultado</th><th>Vencedor</th><th>Motivo</th><th>Bomba</th><th>Seu K/D no round</th></tr></thead>
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

const SIDES = [["all", "Geral"], ["ct", "CT"], ["t", "TR"]];
let currentSide = "all";

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

function sideToggle(containerId, onChange) {
  const el = document.getElementById(containerId);
  el.innerHTML = SIDES.map(([key, lbl]) =>
    `<button data-side="${key}" class="${key === currentSide ? 'active' : ''}">${lbl}</button>`
  ).join("");
  el.querySelectorAll("button").forEach(btn => {
    btn.onclick = () => { currentSide = btn.dataset.side; onChange(); };
  });
}

function statsSummary(statsList) {
  // statsList: lista de objetos stats (já filtrados pelo lado escolhido), pulando null (partida sem round nesse lado)
  const present = statsList.filter(s => s);
  if (present.length === 0) return null;
  const totalKills = present.reduce((s, m) => s + m.kills, 0);
  const totalDeaths = present.reduce((s, m) => s + m.deaths, 0);
  const totalRounds = present.reduce((s, m) => s + m.rounds_played, 0);
  const totalDmg = present.reduce((s, m) => s + m.adr * m.rounds_played, 0);
  const totalWins = present.reduce((s, m) => s + m.round_wins, 0);
  const totalHs = present.reduce((s, m) => s + Math.round(m.hs_pct / 100 * m.kills), 0);
  return {
    kills: totalKills,
    deaths: totalDeaths,
    kd: totalDeaths ? totalKills / totalDeaths : totalKills,
    adr: totalRounds ? totalDmg / totalRounds : 0,
    hs_pct: totalKills ? 100 * totalHs / totalKills : 0,
    rounds_played: totalRounds,
    round_win_pct: totalRounds ? 100 * totalWins / totalRounds : 0,
  };
}

function summaryCardsHtml(s, matchCount) {
  if (!s) return "<p>Sem rounds nesse lado ainda.</p>";
  return [
    matchCount != null ? card(matchCount, "Partidas") : null,
    card(s.kd.toFixed(2), "K/D"),
    card(s.adr.toFixed(1), "ADR médio"),
    card(s.hs_pct.toFixed(0) + "%", "Headshot %"),
    card(s.round_win_pct.toFixed(0) + "%", "Round win rate"),
  ].filter(Boolean).join("");
}

function renderDashboard() {
  document.getElementById("dashboard-view").style.display = "block";
  document.getElementById("match-view").style.display = "none";

  if (DATA.length === 0) {
    document.getElementById("summary-cards").innerHTML = "<p>Nenhuma partida no banco ainda.</p>";
    return;
  }

  sideToggle("dashboard-toggle", renderDashboard);

  const agg = statsSummary(DATA.map(m => m.stats[currentSide]));
  document.getElementById("summary-cards").innerHTML = summaryCardsHtml(agg, DATA.length);

  document.getElementById("matches-tbody").innerHTML = DATA.map(m => {
    const s = m.stats[currentSide];
    if (!s) {
      return `<tr class="clickable-row" onclick="location.hash='match-${m.id}'">
        <td>${fmtDate(m.played_at)}</td><td>${m.map}</td><td>${m.score_ct}:${m.score_t}</td>
        <td colspan="6">— sem rounds nesse lado —</td>
      </tr>`;
    }
    return `<tr class="clickable-row" onclick="location.hash='match-${m.id}'">
      <td>${fmtDate(m.played_at)}</td>
      <td>${m.map}</td>
      <td>${m.score_ct}:${m.score_t}</td>
      <td>${s.kills}</td>
      <td>${s.deaths}</td>
      <td>${s.kd.toFixed(2)}</td>
      <td>${s.adr.toFixed(1)}</td>
      <td>${s.hs_pct.toFixed(0)}%</td>
      <td>${s.round_win_pct.toFixed(0)}%</td>
    </tr>`;
  }).join("");

  const trendMatches = DATA.filter(m => m.stats[currentSide]);
  if (window._trendChart) window._trendChart.destroy();
  window._trendChart = new Chart(document.getElementById('trend'), {
    type: 'line',
    data: {
      labels: trendMatches.map(m => fmtDate(m.played_at)),
      datasets: [
        { label: 'K/D', data: trendMatches.map(m => Math.round(m.stats[currentSide].kd * 100) / 100), borderColor: '#5eb1ff', yAxisID: 'y', tension: 0.25 },
        { label: 'ADR', data: trendMatches.map(m => Math.round(m.stats[currentSide].adr * 10) / 10), borderColor: '#ff9f5e', yAxisID: 'y1', tension: 0.25 }
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

  sideToggle("match-toggle", () => renderMatch(id));

  const s = m.stats[currentSide];
  document.getElementById("match-cards").innerHTML = s
    ? [
        card(s.kills, "Kills"),
        card(s.deaths, "Deaths"),
        card(s.kd.toFixed(2), "K/D"),
        card(s.adr.toFixed(1), "ADR"),
        card(s.hs_pct.toFixed(0) + "%", "Headshot %"),
        card(s.round_win_pct.toFixed(0) + "%", "Round win rate"),
        card(s.rounds_played, "Rounds"),
      ].join("")
    : "<p>Você não jogou nesse lado nessa partida.</p>";

  const weapons = m.weapons[currentSide];
  document.getElementById("weapons-tbody").innerHTML = weapons.map(w => `
    <tr>
      <td>${label(WEAPON_LABEL, w.weapon)}</td>
      <td>${w.kills}</td>
      <td>${w.headshots}</td>
      <td>${w.dmg}</td>
    </tr>`).join("") || `<tr><td colspan="4">Sem dados de arma.</td></tr>`;

  const rounds = currentSide === "all" ? m.rounds : m.rounds.filter(r => r.human_side === currentSide);
  document.getElementById("rounds-tbody").innerHTML = rounds.map(r => `
    <tr>
      <td>${r.round_num}</td>
      <td>${r.human_side ? label(SIDE_LABEL, r.human_side) : '-'}</td>
      <td><span class="pill ${r.result}">${r.result === 'win' ? 'Vitória' : r.result === 'loss' ? 'Derrota' : '-'}</span></td>
      <td>${label(SIDE_LABEL, r.winner_side)}</td>
      <td>${label(REASON_LABEL, r.reason)}</td>
      <td>${r.bomb_plant ? ('Sim (' + (r.bomb_site || '?') + ')') : '-'}</td>
      <td><span class="kill">${r.kills}</span> / <span class="death">${r.deaths}</span></td>
    </tr>`).join("") || `<tr><td colspan="7">Sem rounds nesse lado.</td></tr>`;

  const feed = currentSide === "all" ? m.kill_feed : m.kill_feed.filter(e => e.human_side === currentSide);
  document.getElementById("feed-tbody").innerHTML = feed.map(e => `
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
    conn.row_factory = sqlite3.Row
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
