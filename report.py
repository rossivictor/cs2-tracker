#!/usr/bin/env python3
"""
CS2 Tracker — Report
=====================
Gera um relatório HTML estático a partir do cs2_tracker.db: dashboard
com stats agregados, recordes pessoais, ranking por mapa e lista
clicável de partidas, mais uma página de detalhe por partida (quadro de
armas, linha do tempo de rounds, feed de kills/mortes). Toda estatística
(cards, quadro de armas, linha do tempo, feed) vem em 3 variantes —
Geral / CT / TR — trocadas por um toggle na própria página, sem
recarregar. O cálculo (SQLite -> dict) mora em stats.py, compartilhado
com home.py; aqui só sobra montar o payload e renderizar o template
(templates/report.html via Jinja, ver templates/shell.html pro
cabeçalho/CSS compartilhados com a home). Os dados vão embutidos como
JSON inline e a navegação entre dashboard/detalhe é feita em JS puro via
location.hash, sem servidor, sem build, sem fetch (evita problema de
CORS ao abrir o arquivo direto via file://).

Uso:
    .venv\\Scripts\\python.exe report.py --db cs2_tracker.db --out report.html
"""

import argparse
import json
import webbrowser
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import DB_PATH, REPORT_PATH
from stats import load_stats, map_icon_path, map_label

ROOT = Path(__file__).resolve().parent


def build_html(payload):
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return template.render(active_page="report", payload_json=payload_json)


def build_payload(db_path):
    """Payload consumido pelo template (embutido como JSON, ver build_html).
    Compartilhado entre o gerador estático (generate_report) e a rota
    GET /report do app web — uma única fonte pros dois, igual home.build_context.
    map_icon/map_label vêm aqui (e não do JS) pra reusar os mesmos helpers de
    stats.py que a home usa, sem duplicar a tabela de nomes/ícones em JS."""
    data = load_stats(db_path)
    matches = []
    for m in data["matches"]:
        m = dict(m)
        m["map_icon"] = map_icon_path(m["map"])
        m["map_label"] = map_label(m["map"])
        matches.append(m)
    return {
        "matches": matches,
        "maps": data["maps"],
        "records": data["records"],
        "bombsites": data["bombsites"],
    }


def generate_report(db_path, out_path):
    payload = build_payload(db_path)
    out_path = Path(out_path)
    out_path.write_text(build_html(payload), encoding="utf-8")
    print(f"[REPORT] {len(payload['matches'])} partida(s) — relatório gerado em {out_path.resolve()}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="CS2 Tracker — Report (SQLite -> HTML local)")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--out", default=REPORT_PATH)
    parser.add_argument("--open", action="store_true", help="Abre o relatório no navegador ao terminar")
    args = parser.parse_args()

    out_path = generate_report(args.db, args.out)
    if args.open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
