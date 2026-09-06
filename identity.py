#!/usr/bin/env python3
"""
CS2 Tracker — Identity
========================
Resolve a identidade do jogador humano (steamid + nome) a partir do
--player passado pra watcher.py/start_match.py/parser.py, cruzando com
docker/match_config.spike.json quando disponível (modo matchzy). No
modo native não existe match_config.json — cai pra nome puro, sem
steamid (comportamento idêntico ao anterior a este módulo).
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_STEAMID64_RE = re.compile(r"^\d{17}$")


@dataclass(frozen=True)
class PlayerIdentity:
    name: str
    steamid: Optional[str] = None

    @property
    def has_steamid(self) -> bool:
        return self.steamid is not None


def _players_from_match_config(match_config_path: Path) -> dict:
    """Retorna {steamid_str: display_name} a partir de team1.players +
    team2.players. Silencioso se o arquivo não existir ou for inválido —
    modo native não tem esse arquivo."""
    try:
        data = json.loads(Path(match_config_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    players = {}
    for team_key in ("team1", "team2"):
        players.update(data.get(team_key, {}).get("players", {}))
    return players


def resolve_identity(player_arg: str, match_config_path: Optional[Path] = None) -> PlayerIdentity:
    """
    player_arg: valor bruto de --player (nick ou SteamID64 puro).
    match_config_path: caminho do match_config.json (modo matchzy) ou
    None (modo native — sempre cai no fallback nome-only).
    """
    players_by_id = _players_from_match_config(match_config_path) if match_config_path else {}

    if _STEAMID64_RE.match(player_arg):
        steamid = player_arg
        name = players_by_id.get(steamid, player_arg)
        return PlayerIdentity(name=name, steamid=steamid)

    for steamid, name in players_by_id.items():
        if name == player_arg:
            return PlayerIdentity(name=player_arg, steamid=steamid)

    return PlayerIdentity(name=player_arg, steamid=None)
