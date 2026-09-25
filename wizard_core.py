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
from typing import Callable, List, Literal, Optional

import roster
from identity import PlayerIdentity, resolve_identity
from start_match import (
    ROOT,
    force_start_and_balance_bots,
    read_max_players,
    run_match,
)

# Rótulo neutro pro adversário quando a lineup é montagem manual/mista, sem
# time de origem reconhecível (F4.4, docs/features/M4-seletor.md) — nunca
# fica em branco nem herda o nome de uma partida anterior.
NEUTRAL_ENEMY_LABEL = "Adversário"

_ROSTER_CATALOG = roster.load_rosters()

# Sink de log explícito (F2.2, docs/features/M2-nucleo.md) — qualquer callable
# que aceite uma linha de texto e a escreva em algum lugar. print() serve como
# default porque casa com essa assinatura (uma string, sem sep/end custom) e é
# o que o CLI (start_match.py --player ...) precisa sem passar nada.
Sink = Callable[[str], None]


class WizardError(ValueError):
    """Transição de WizardSession inválida pro estado atual — mensagem já
    pronta pra mostrar na tela, sem precisar traduzir a exceção."""

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
    # Nomes de profile (chave do botprofile.vpk, não display_name — ver
    # SPEC.md §7) pros companheiros (sem o humano) e pro time adversário.
    # Vazio (default) = modo anônimo de sempre: start_match.py enche os
    # times por contagem, sem pedir nome nenhum. Preenchido pelo CLI de
    # start_match.py (--mine/--enemy, F1.2) ou pela tela de Lineups do app
    # web (WizardSession.set_lineups, F4.2) — a TUI nunca preenche (skip_
    # lineups em toda troca de formato, ver wizard_tui.py).
    my_lineup: List[str] = field(default_factory=list)
    enemy_lineup: List[str] = field(default_factory=list)
    # Nome/logo do adversário pro placar do jogo (F4.4) — resolvidos em
    # WizardSession.to_match_setup() comparando enemy_lineup contra o
    # catálogo (roster.identify_team). NEUTRAL_ENEMY_LABEL/"" (nunca None)
    # pra nunca ficar em branco nem herdar nome de uma partida anterior.
    enemy_team_name: str = NEUTRAL_ENEMY_LABEL
    enemy_team_logo: str = ""


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


# Passos do wizard. "Partida"/launch fica de fora porque é orquestração
# externa, não navegação do wizard. O veto NÃO é um passo próprio: é uma
# sub-tela do passo Mapas (STEP_MAPS), sinalizada por `veto_active`, pra a
# contagem de passos não mudar entre escolha direta e veto.
#
# STEP_LINEUPS existe só pro app web (F4.2, docs/features/M4-seletor.md) —
# o wizard_tui.py (Textual) nunca mostra essa tela: FormatScreen chama
# skip_lineups() logo depois de set_format(), então pra quem usa a TUI o
# passo é invisível (my_lineup/enemy_lineup ficam vazios = bots anônimos,
# comportamento de sempre). O app web mostra a tela de verdade e chama
# set_lineups().
STEP_IDENTITY, STEP_FORMAT, STEP_LINEUPS, STEP_MAPS, STEP_SIDES, STEP_SUMMARY = range(1, 7)


@dataclass
class WizardSession:
    """
    Estado do wizard (F2.1, docs/features/M2-nucleo.md), sem nenhuma
    dependência de UI — o que antes vivia espalhado em atributos do
    WizardApp (wizard_tui.py) mais a pilha de telas do Textual. Transições
    nomeadas (`set_identity`, `set_format`, `set_lineups`/`skip_lineups`,
    `choose_maps_direct`/`start_veto`/`resolve_veto_step`, `set_side`,
    `back`) validam a pré-condição e recusam transição inválida levantando
    WizardError com mensagem pronta pra tela.

    `back()` sabe pular passos que não se aplicam: voltar de Lados pro
    primeiro mapa some do estado de Lados; voltar do primeiro mapa de Lados
    pra Mapas pula a tela de veto (um veto concluído não tem como continuar —
    o jeito de "refazer" é começar um veto novo ou escolher na mão).
    """

    identity: Optional[PlayerIdentity] = None
    format: Optional[Literal["bo1", "bo3", "bo5"]] = None
    team_size: Optional[int] = None
    step: int = STEP_IDENTITY

    # Passo Lineups (F4.2) — nomes de profile (chave do VPK), sem o humano
    # em my_lineup. Vazios = modo anônimo de sempre (skip_lineups, ou quem
    # nunca passou por STEP_LINEUPS nenhuma).
    my_lineup: List[str] = field(default_factory=list)
    enemy_lineup: List[str] = field(default_factory=list)

    # Sub-fluxo de veto — só relevante enquanto veto_active e step == STEP_MAPS.
    veto_active: bool = False
    map_pool: List[str] = field(default_factory=list)
    veto_steps: List[VetoStep] = field(default_factory=list)
    veto_step_index: int = 0
    veto_picks: List[str] = field(default_factory=list)
    veto_history: List[str] = field(default_factory=list)

    # Resultado do passo Mapas (via escolha direta OU veto concluído).
    maps_in_order: Optional[List[str]] = None

    # Passo Lados: um MapChoice por mapa de maps_in_order, um de cada vez.
    side_index: int = 0
    map_choices: List[MapChoice] = field(default_factory=list)

    # -- Jogador -----------------------------------------------------------

    def set_identity(self, identity: PlayerIdentity) -> None:
        if self.step != STEP_IDENTITY:
            raise WizardError("Identidade só pode ser definida no passo Jogador.")
        self.identity = identity
        self.step = STEP_FORMAT

    # -- Formato -------------------------------------------------------------

    def set_format(self, fmt: str, team_size: int) -> None:
        if self.step != STEP_FORMAT:
            raise WizardError("Formato só pode ser definido no passo Formato.")
        if fmt not in MAPS_PER_FORMAT:
            raise WizardError(f"Formato inválido: {fmt!r} (use bo1, bo3 ou bo5).")
        if team_size < 1:
            raise WizardError("Jogadores por time precisa ser pelo menos 1.")
        self.format = fmt
        self.team_size = team_size
        self.step = STEP_LINEUPS

    # -- Lineups (F4.2) --------------------------------------------------------

    def _validate_lineups(self, my_lineup: List[str], enemy_lineup: List[str]) -> None:
        # Lista vazia = lado "competitivo" (anônimo, F4.2 grade de logos) —
        # só valida o tamanho de um lado que foi de fato especificado. Os
        # dois vazios ao mesmo tempo são o skip_lineups() de sempre, não
        # passam por aqui.
        if my_lineup and len(my_lineup) != self.team_size - 1:
            raise WizardError(
                f"my_lineup tem {len(my_lineup)} nome(s), esperado {self.team_size - 1} "
                f"(team_size {self.team_size} menos você)."
            )
        if enemy_lineup and len(enemy_lineup) != self.team_size:
            raise WizardError(
                f"enemy_lineup tem {len(enemy_lineup)} nome(s), esperado {self.team_size}."
            )
        combined = my_lineup + enemy_lineup
        if len(set(combined)) != len(combined):
            raise WizardError("Um perfil aparece duas vezes entre as duas lineups.")
        human_name = self.identity.name if self.identity else None
        if human_name in combined:
            raise WizardError(
                f"Seu nick ({human_name!r}) colide com um perfil escolhido — "
                "nomes são únicos no servidor inteiro (SPEC.md §10)."
            )

    def set_lineups(self, my_lineup: List[str], enemy_lineup: List[str]) -> None:
        """Lineups nomeadas — nomes são únicos no servidor inteiro, sem
        distinção de time (SPEC.md §10 restrição 1), daí a validação cruzada
        entre my_lineup/enemy_lineup e contra o próprio nick do jogador."""
        if self.step != STEP_LINEUPS:
            raise WizardError("Lineups só podem ser definidas no passo Lineups.")
        self._validate_lineups(my_lineup, enemy_lineup)
        self.my_lineup = list(my_lineup)
        self.enemy_lineup = list(enemy_lineup)
        self.step = STEP_MAPS

    def skip_lineups(self) -> None:
        """Modo anônimo de sempre — é o que o wizard_tui.py chama logo após
        set_format(), porque a TUI não tem tela de lineups (só o app web,
        F4.2, tem)."""
        if self.step != STEP_LINEUPS:
            raise WizardError("Só há o que pular no passo Lineups.")
        self.my_lineup = []
        self.enemy_lineup = []
        self.step = STEP_MAPS

    # -- Mapas: escolha direta ou veto ---------------------------------------

    def choose_maps_direct(self, maps: List[str]) -> None:
        if self.step != STEP_MAPS:
            raise WizardError("Mapas só podem ser escolhidos no passo Mapas.")
        needed = MAPS_PER_FORMAT[self.format]
        if len(maps) != needed:
            raise WizardError(f"Escolha exatamente {needed} mapa(s) pro {self.format.upper()}.")
        if len(set(maps)) != len(maps):
            raise WizardError("Mapas repetidos não são permitidos.")
        invalid = [m for m in maps if m not in DEFAULT_MAP_POOL]
        if invalid:
            raise WizardError(f"Mapa(s) fora do pool: {', '.join(invalid)}.")
        self._enter_sides(list(maps))

    def start_veto(self, pool: Optional[List[str]] = None) -> None:
        if self.step != STEP_MAPS:
            raise WizardError("Veto só pode começar no passo Mapas.")
        self.map_pool = list(pool) if pool is not None else list(DEFAULT_MAP_POOL)
        self.veto_steps = generate_veto_sequence(self.map_pool, self.format)
        self.veto_step_index = 0
        self.veto_picks = []
        self.veto_history = []
        self.veto_active = True

    def current_veto_step(self) -> Optional[VetoStep]:
        if not self.veto_active:
            raise WizardError("Nenhum veto em andamento.")
        if self.veto_step_index >= len(self.veto_steps):
            return None
        return self.veto_steps[self.veto_step_index]

    def resolve_veto_step(self, map_name: str) -> None:
        step = self.current_veto_step()  # valida veto_active e levanta se concluído
        if step is None:
            raise WizardError("Veto já concluído — o mapa decisivo já foi definido.")
        if map_name not in self.map_pool:
            raise WizardError(f"{map_name!r} não está mais disponível no pool de veto.")

        self.map_pool.remove(map_name)
        if step.action == "pick":
            self.veto_picks.append(map_name)
        quem = "Você" if step.actor == "you" else "Bot"
        verbo = "baniu" if step.action == "ban" else "escolheu"
        self.veto_history.append(f"{quem} {verbo} {map_name}")
        self.veto_step_index += 1

        if self.veto_step_index >= len(self.veto_steps):
            decider = decider_map(self.map_pool)
            self.veto_history.append(f"Mapa decisivo: {decider}")
            self.veto_active = False
            self._enter_sides(self.veto_picks + [decider])

    def _enter_sides(self, maps_in_order: List[str]) -> None:
        self.maps_in_order = maps_in_order
        self.side_index = 0
        self.map_choices = []
        self.step = STEP_SIDES

    # -- Lados ---------------------------------------------------------------

    def set_side(self, side: str) -> None:
        if self.step != STEP_SIDES:
            raise WizardError("Lado só pode ser escolhido no passo Lados.")
        if side not in ("ct", "t"):
            raise WizardError(f"Lado inválido: {side!r} (use 'ct' ou 't').")
        if self.side_index >= len(self.maps_in_order):
            raise WizardError("Todos os lados já foram escolhidos.")
        map_name = self.maps_in_order[self.side_index]
        self.map_choices.append(MapChoice(map_name=map_name, side=side))
        self.side_index += 1
        if self.side_index >= len(self.maps_in_order):
            self.step = STEP_SUMMARY

    # -- Voltar ---------------------------------------------------------------

    def _back_from_sides(self) -> None:
        if self.side_index > 0:
            self.side_index -= 1
            if self.map_choices:
                self.map_choices.pop()
        else:
            # Nada escolhido ainda em Lados: sai pro passo Mapas. Um veto já
            # concluído não é resumível (a sequência acabou) — a única forma
            # de seguir é escolher na mão ou começar um veto novo.
            self.step = STEP_MAPS

    def back(self) -> None:
        if self.step == STEP_IDENTITY:
            raise WizardError("Não há passo anterior a Jogador.")
        elif self.step == STEP_FORMAT:
            self.step = STEP_IDENTITY
        elif self.step == STEP_LINEUPS:
            self.step = STEP_FORMAT
        elif self.step == STEP_MAPS:
            if self.veto_active:
                self.veto_active = False
            else:
                self.step = STEP_LINEUPS
        elif self.step == STEP_SIDES:
            self._back_from_sides()
        elif self.step == STEP_SUMMARY:
            self.step = STEP_SIDES
            self._back_from_sides()
        else:
            raise WizardError(f"Voltar não é suportado no passo {self.step}.")

    # -- Ponte pro launch ------------------------------------------------------

    def to_match_setup(self) -> MatchSetup:
        if self.identity is None or self.format is None or self.team_size is None:
            raise WizardError("Sessão incompleta: falta jogador, formato ou tamanho de time.")

        # F4.4: só um roster de verdade (elenco batendo 100% com um time do
        # catálogo) ganha nome/logo próprios no placar — qualquer outra
        # coisa (anônimo, manual, mistura) usa o rótulo neutro, nunca em
        # branco nem herdado de uma partida anterior.
        enemy_team = _ROSTER_CATALOG.identify_team(self.enemy_lineup) if self.enemy_lineup else None
        enemy_team_name = enemy_team.display_name if enemy_team else NEUTRAL_ENEMY_LABEL
        enemy_team_logo = enemy_team.logo if enemy_team else ""

        return MatchSetup(
            identity=self.identity,
            format=self.format,
            team_size=self.team_size,
            maps=list(self.map_choices),
            my_lineup=list(self.my_lineup),
            enemy_lineup=list(self.enemy_lineup),
            enemy_team_name=enemy_team_name,
            enemy_team_logo=enemy_team_logo,
        )


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

    # F4.4: só mexe no team2.name quando uma lineup foi de fato montada —
    # sem isso (modo anônimo de sempre), o placeholder do template
    # (ex.: "Bots") segue como estava, sem mudança de comportamento.
    if setup.enemy_lineup:
        team2 = dict(data.get("team2", {}))
        team2["name"] = setup.enemy_team_name
        data["team2"] = team2

    return data


def write_match_config(path: Path, data: dict, log: Sink = print):
    """Mesmo padrão de escrita usado em start_match.py (indent=2, sem ASCII)."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"[CONFIG] {path.name}: maplist -> {data['maplist']} "
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


def _scoreboard_args(setup: MatchSetup):
    """None pra enemy_team_name = "nenhuma lineup foi montada, não mexe no
    placar" (preserva o modo anônimo de sempre) — só quando alguma lineup
    foi de fato escolhida (F4.2) é que o placar (F4.4) entra em jogo."""
    if setup.my_lineup or setup.enemy_lineup:
        return setup.enemy_team_name, setup.enemy_team_logo
    return None, ""


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
    watcher_output=None,
    confirm_ready=None,
    rcon_lock=None,
    log: Sink = print,
):
    """
    Escreve o match_config final e dispara run_match (start_match.py) —
    mesma orquestração do CLI (docker up, RCON, matchzy_loadmatch, balanceio
    de bots), só que dirigida pelo MatchSetup montado no wizard em vez de
    argparse.

    on_watcher_started: repassado direto pro run_match (ver docstring lá) —
    é como o wizard_tui.py consegue o handle do watcher pra encerrar junto
    quando a UI fecha.
    watcher_output/confirm_ready: também repassados sem interpretação — são
    os dois pontos em que o run_match fala com o terminal por conta própria
    (saída do watcher e o input() de "já conectei"), e que uma UI precisa
    redirecionar pra dentro dela.
    log: sink de log explícito (F2.2, docs/features/M2-nucleo.md) — recebido
    e repassado pra run_match, sem redirect_stdout nenhum. Default print,
    então o CLI (start_match.py) continua funcionando sem passar nada.
    """
    local_match_config = ROOT / "docker" / Path(match_config_file).name
    base_config = load_base_config(local_match_config)
    final_config = build_match_config(base_config, setup)
    write_match_config(local_match_config, final_config, log=log)

    enemy_team_name, enemy_team_logo = _scoreboard_args(setup)
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
        watcher_output=watcher_output,
        confirm_ready=confirm_ready,
        rcon_lock=rcon_lock,
        log=log,
        my_lineup=setup.my_lineup,
        enemy_lineup=setup.enemy_lineup,
        enemy_team_name=enemy_team_name,
        enemy_team_logo=enemy_team_logo,
    )


def force_start(
    setup: MatchSetup,
    *,
    container_name: str,
    match_config_file: str,
    rcon_host: str,
    rcon_port: int,
    rcon_password: str,
    rcon_lock=None,
    log: Sink = print,
):
    """Repete manualmente o início/balanceamento da partida atual."""
    local_match_config = ROOT / "docker" / Path(match_config_file).name
    enemy_team_name, enemy_team_logo = _scoreboard_args(setup)
    force_start_and_balance_bots(
        rcon_host=rcon_host,
        rcon_port=rcon_port,
        rcon_password=rcon_password,
        container_name=container_name,
        team_size=setup.team_size,
        player=setup.identity.name,
        local_match_config=local_match_config,
        rcon_lock=rcon_lock,
        log=log,
        my_lineup=setup.my_lineup,
        enemy_lineup=setup.enemy_lineup,
        enemy_team_name=enemy_team_name,
        enemy_team_logo=enemy_team_logo,
    )
