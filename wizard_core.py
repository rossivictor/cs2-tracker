#!/usr/bin/env python3
"""
CS2 Tracker — Wizard Core
==========================
Lógica de negócio do wizard de partida (nick/SteamID -> mapa/formato ->
veto -> jogadores -> start_match), sem nenhuma dependência de UI. A ideia
é que wizard_tui.py (Textual) seja só a casca: se um dia a UI migrar pra
outra tecnologia (ex.: Tauri), este módulo continua igual.

Reaproveita direto identity.py (resolução de nick/SteamID64) e as funções
já existentes em start_match.py (subida do container, RCON, run_match) —
não reimplementa nada disso.
"""
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional

from identity import PlayerIdentity, resolve_identity
from start_match import ROOT, read_max_players, run_match

DEFAULT_MAP_POOL = [
    "de_dust2", "de_mirage", "de_inferno", "de_nuke",
    "de_ancient", "de_anubis", "de_cache",
]

MAPS_PER_FORMAT = {"bo1": 1, "bo3": 3, "bo5": 5}

Side = Literal["ct", "t"]
Actor = Literal["you", "bot"]
Action = Literal["ban", "pick"]


@dataclass(frozen=True)
class VetoStep:
    actor: Actor
    action: Action
    # Preenchido só depois que o passo é resolvido (mapa banido/escolhido).
    map_name: Optional[str] = None


@dataclass(frozen=True)
class MapChoice:
    map_name: str
    side: Side


@dataclass
class MatchSetup:
    identity: PlayerIdentity
    format: Literal["bo1", "bo3", "bo5"]
    team_size: int
    maps: List[MapChoice] = field(default_factory=list)


def generate_veto_sequence(pool: List[str], fmt: str) -> List[VetoStep]:
    """
    Sequência padrão de veto competitivo, alternando ator "you"/"bot".
    Como o oponente é sempre bot (sem veto real no servidor — ver
    docker/SPIKE.md), os passos "bot" só existem pra manter o ritmo
    familiar do veto; quem resolve de fato é sempre o humano na tela de
    veto do wizard, os passos "bot" são resolvidos automaticamente
    (ban aleatório) por resolve_bot_step().

    - bo1: bane até sobrar 1 mapa (pick automático do que sobrar).
    - bo3/bo5: ban, ban, pick, pick, [pick, pick,] ban, ban, decider
      (mapa que sobrar depois dos bans finais).
    """
    num_maps = MAPS_PER_FORMAT[fmt]
    pool_size = len(pool)
    steps: List[VetoStep] = []
    actors: List[Actor] = ["you", "bot"]

    if fmt == "bo1":
        bans_needed = pool_size - 1
        for i in range(bans_needed):
            steps.append(VetoStep(actor=actors[i % 2], action="ban"))
        return steps

    # bo3/bo5: 2 bans, depois picks alternados até faltar 1 mapa (decider),
    # depois bans finais até sobrar só o decider.
    picks_needed = num_maps - 1  # o último mapa é sempre o "decider" (sobra).
    bans_needed = pool_size - 1 - picks_needed
    opening_bans = min(2, bans_needed)
    remaining_bans_after_picks = bans_needed - opening_bans

    turn = 0
    for _ in range(opening_bans):
        steps.append(VetoStep(actor=actors[turn % 2], action="ban"))
        turn += 1
    for _ in range(picks_needed):
        steps.append(VetoStep(actor=actors[turn % 2], action="pick"))
        turn += 1
    for _ in range(remaining_bans_after_picks):
        steps.append(VetoStep(actor=actors[turn % 2], action="ban"))
        turn += 1

    return steps


def resolve_bot_step(remaining_pool: List[str]) -> str:
    """Turno automático do bot: escolha aleatória dentre os mapas restantes."""
    return random.choice(remaining_pool)


def decider_map(remaining_pool: List[str]) -> str:
    """Mapa que sobra depois de todos os passos de ban/pick — o decider."""
    if len(remaining_pool) != 1:
        raise ValueError(f"Esperava 1 mapa restante pro decider, sobraram {remaining_pool}")
    return remaining_pool[0]


def build_match_config(base_config: dict, setup: MatchSetup) -> dict:
    """
    Versão multi-mapa de set_map_in_config/set_side_in_config
    (start_match.py) — monta o match_config final (bo1/bo3/bo5) a partir
    do MatchSetup montado pelo wizard, preservando os demais campos do
    template (clinch_series, players_per_team, team2/bots) como estavam.
    """
    data = dict(base_config)
    data["maplist"] = [m.map_name for m in setup.maps]
    data["num_maps"] = len(setup.maps)
    data["map_sides"] = [f"team1_{m.side}" for m in setup.maps]
    data["players_per_team"] = setup.team_size

    team1 = dict(data.get("team1", {}))
    team1["name"] = setup.identity.name
    if setup.identity.has_steamid:
        team1["players"] = {setup.identity.steamid: setup.identity.name}
    data["team1"] = team1

    return data


def write_match_config(path: Path, data: dict):
    """Mesmo padrão de escrita usado em start_match.py (indent=2, sem ASCII)."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CONFIG] {path.name}: maplist -> {data['maplist']} "
          f"(map_sides -> {data['map_sides']})")


def load_base_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_setup_identity(player_arg: str, match_config_path: Optional[Path] = None) -> PlayerIdentity:
    """Fina casca sobre identity.resolve_identity, reexportada aqui pra
    quem só importa wizard_core não precisar saber de identity.py."""
    return resolve_identity(player_arg, match_config_path)


def max_team_size(compose_file: Path) -> Optional[int]:
    """CS2_MAXPLAYERS do docker-compose.yml, convertido pro maior team_size
    possível (2x team_size + 1 slot de GOTV) — usado pra validar a tela de
    formato/jogadores do wizard antes mesmo de tentar subir o container."""
    max_players = read_max_players(compose_file)
    if max_players is None:
        return None
    return (max_players - 1) // 2


def launch(
    setup: MatchSetup,
    *,
    container_name: str,
    compose_file: str,
    match_config_file: str,
    rcon_host: str,
    rcon_port: int,
    rcon_password: str,
    boot_timeout: int = 300,
    skip_up: bool = False,
    on_watcher_started=None,
):
    """
    Escreve o match_config final e dispara run_match (start_match.py) —
    mesma orquestração do CLI (docker up, RCON, matchzy_loadmatch, balanceio
    de bots), só que dirigida pelo MatchSetup montado no wizard em vez de
    argparse. Os prints de run_match continuam indo pro stdout; quem quiser
    capturá-los pra um widget (ex.: wizard_tui.py) faz isso por fora,
    redirecionando stdout ao redor da chamada a launch().

    on_watcher_started: repassado direto pro run_match (ver docstring lá) —
    é como o wizard_tui.py consegue o handle do watcher pra encerrar junto
    quando a UI fecha.
    """
    local_match_config = ROOT / "docker" / Path(match_config_file).name
    base_config = load_base_config(local_match_config)
    final_config = build_match_config(base_config, setup)
    write_match_config(local_match_config, final_config)

    run_match(
        container_name=container_name,
        match_config=match_config_file,
        compose_file=compose_file,
        rcon_host=rcon_host,
        rcon_port=rcon_port,
        rcon_password=rcon_password,
        team_size=setup.team_size,
        boot_timeout=boot_timeout,
        skip_up=skip_up,
        player=setup.identity.name,
        on_watcher_started=on_watcher_started,
    )
