#!/usr/bin/env python3
"""
CS2 Tracker — Config
=====================
Fonte única dos defaults de path/nome usados por parser.py, watcher.py,
report.py e start_match.py. Cada valor pode ser sobrescrito via .env
(chave em maiúsculas, prefixo CS2_TRACKER_) ou via flag de linha de
comando de cada script — .env < literal default < flag explícita.
"""
import json
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
HOME_PATH = _get("CS2_TRACKER_HOME_PATH", "./index.html")
DEMO_DIR = _get("CS2_TRACKER_DEMO_DIR", "./demos")
DEMOS_LIVE_DIR = _get("CS2_TRACKER_DEMOS_LIVE_DIR", "./docker/demos-live")
STATS_LIVE_DIR = _get("CS2_TRACKER_STATS_LIVE_DIR", "./docker/stats-live")
EVENTS_LIVE_DIR = _get("CS2_TRACKER_EVENTS_LIVE_DIR", "./docker/events-live")
CONTAINER_NAME = _get("CS2_TRACKER_CONTAINER", "cs2-spike")
COMPOSE_FILE = _get("CS2_TRACKER_COMPOSE_FILE", "docker-compose.yml")
MATCH_CONFIG_FILE = _get("CS2_TRACKER_MATCH_CONFIG", "match_config.spike.json")
ROSTERS_FILE = _get("CS2_TRACKER_ROSTERS_FILE", "data/rosters.json")

# Válvula vanilla (card P1.2): o override que mascara os plugins de bot e o
# estado do papel servidor que diz se ele entra. Ignorado pelo git.
COMPOSE_VANILLA = "docker-compose.vanilla.yml"
SERVIDOR_JSON = "data/servidor.json"


def estado_servidor(raiz: Path = None) -> tuple:
    """(estado, aviso) de data/servidor.json. Ausente: ({}, None). JSON
    inválido ou que não é objeto: ({}, aviso), e o vanilla conta como off."""
    arquivo = Path(raiz or ROOT) / SERVIDOR_JSON
    try:
        estado = json.loads(arquivo.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, None
    except (OSError, ValueError) as exc:
        return {}, f"{SERVIDOR_JSON} ilegível ({exc.__class__.__name__}): vanilla conta como off"
    if not isinstance(estado, dict):
        return {}, f"{SERVIDOR_JSON} não é um objeto JSON: vanilla conta como off"
    return estado, None


def vanilla_ligado(raiz: Path = None, avisar=None) -> bool:
    """O campo `vanilla` de data/servidor.json; só o booleano true liga."""
    estado, aviso = estado_servidor(raiz)
    valor = estado.get("vanilla", False)
    if not isinstance(valor, bool):
        aviso, valor = f"{SERVIDOR_JSON}: vanilla={valor!r} não é true/false: conta como off", False
    if aviso and avisar:
        avisar(f"[AVISO] {aviso}")
    return valor


def compose_files(raiz: Path = None, base=None, vanilla: bool = None, avisar=None) -> list:
    """Única fonte da lista ordenada de `-f` do docker compose (card P1.2),
    para o start_match, o tools/jogavel.py e o recreate: o base (padrão
    COMPOSE_FILE) e, com o vanilla ligado em data/servidor.json (ou
    `vanilla=True`), o docker-compose.vanilla.yml empilhado depois dele.
    Caminhos relativos à raiz. Vanilla ligado num checkout sem o override
    (tag anterior ao P1.2): sobe só o base, com aviso, para o jogo subir."""
    raiz = Path(raiz or ROOT)
    arquivos = [str(base or COMPOSE_FILE)]
    if vanilla is None:
        vanilla = vanilla_ligado(raiz, avisar)
    if vanilla and not (raiz / COMPOSE_VANILLA).is_file():
        if avisar:
            avisar(f"[AVISO] vanilla ligado, mas {COMPOSE_VANILLA} não existe em {raiz}: só o base")
        vanilla = False
    if vanilla:
        arquivos.append(COMPOSE_VANILLA)
    return arquivos
