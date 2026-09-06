#!/usr/bin/env python3
"""
CS2 Tracker — Config
=====================
Fonte única dos defaults de path/nome usados por parser.py, watcher.py,
report.py e start_match.py. Cada valor pode ser sobrescrito via .env
(chave em maiúsculas, prefixo CS2_TRACKER_) ou via flag de linha de
comando de cada script — .env < literal default < flag explícita.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_env(path: Path = None) -> dict:
    """Lê .env (KEY=VALUE, ignora comentários/linhas vazias)."""
    path = path or (ROOT / ".env")
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


_ENV = load_env()


def _get(key, default):
    return _ENV.get(key, default)


DB_PATH = _get("CS2_TRACKER_DB_PATH", "./cs2_tracker.db")
REPORT_PATH = _get("CS2_TRACKER_REPORT_PATH", "./report.html")
DEMO_DIR = _get("CS2_TRACKER_DEMO_DIR", "./demos")
DEMOS_LIVE_DIR = _get("CS2_TRACKER_DEMOS_LIVE_DIR", "./docker/demos-live")
CONTAINER_NAME = _get("CS2_TRACKER_CONTAINER", "cs2-spike")
COMPOSE_FILE = _get("CS2_TRACKER_COMPOSE_FILE", "docker-compose.yml")
MATCH_CONFIG_FILE = _get("CS2_TRACKER_MATCH_CONFIG", "match_config.spike.json")
