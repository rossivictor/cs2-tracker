#!/usr/bin/env python3
"""
CS2 Tracker — Wizard (Textual)
================================
UI do wizard de partida: nick/SteamID64 -> formato (bo1/bo3/bo5) -> mapas
(escolha manual ou veto) -> lado por mapa -> resumo -> dispara start_match.

Este arquivo só monta telas e reage a eventos — toda a lógica (veto,
montagem do match_config, orquestração docker/RCON) vive em wizard_core.py
e start_match.py, sem nenhum import de Textual. A ideia é que uma futura
troca de UI (ex.: Tauri) precise reescrever só este arquivo.

Todo o fluxo acontece dentro da TUI, inclusive a espera do "já conectei no
servidor" (botão na LaunchScreen) e o acompanhamento do watcher.py — as
duas saídas, launcher e watcher, caem no mesmo painel de log.

Uso:
    .venv\\Scripts\\python.exe wizard_tui.py
"""
import asyncio
import threading
from pathlib import Path
from typing import Iterable, List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    Button, Footer, Input, RadioButton, RadioSet, RichLog, Static,
)

from config import COMPOSE_FILE, CONTAINER_NAME, MATCH_CONFIG_FILE, ROOT, load_env
import wizard_core as core

FORMATS = ["bo1", "bo3", "bo5"]
SIDES = [("ct", "CT"), ("t", "TR")]
BOT_TURN_COUNTDOWN_S = 2  # "timer" visível antes do bot resolver o turno de veto
VETO_RESULT_DWELL_S = 2   # tempo que o último veto + decider ficam na tela antes de seguir

# Passos mostrados na barra inferior. O veto NÃO é um passo próprio: ele é
# uma sub-tela do passo "Mapas", justamente pra a contagem total não mudar
# quando o usuário escolhe os mapas na mão em vez de vetar.
STEPS = ["Jogador", "Formato", "Mapas", "Lados", "Resumo", "Partida"]
STEP_BAR_CELLS = 4  # células de "█" por passo na barra de progresso

# ---------------------------------------------------------------------------
# Arte ASCII do título. Cada glifo é uma tupla de linhas de mesma largura;
# montar por composição (em vez de colar o bloco pronto) é o que garante que
# as linhas continuem alinhadas se alguém mexer numa letra.
# ---------------------------------------------------------------------------
_FULL_GLYPHS = {
    "C": (" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"),
    "S": ("███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"),
    "2": ("██████╗ ", "╚════██╗", " █████╔╝", "██╔═══╝ ", "███████╗", "╚══════╝"),
    "T": ("████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "),
    "R": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"),
    "A": (" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "K": ("██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"),
    "E": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"),
}
_MINI_GLYPHS = {
    "C": ("╔═╗", "║  ", "╚═╝"),
    "S": ("╔═╗", "╚═╗", "╚═╝"),
    "2": ("╔═╗", "╔═╝", "╚═╝"),
    "T": ("╔╦╗", " ║ ", " ╩ "),
    "R": ("╦═╗", "╠╦╝", "╩╚═"),
    "A": ("╔═╗", "╠═╣", "╩ ╩"),
    "K": ("╦╔═", "╠╩╗", "╩ ╩"),
    "E": ("╔═╗", "║╣ ", "╚═╝"),
}


def _render_banner(text: str, glyphs: dict, gap: str) -> str:
    rows = len(next(iter(glyphs.values())))
    return "\n".join(
        "".join(gap if ch == " " else glyphs[ch][row] for ch in text)
        for row in range(rows)
    )


BANNER_FULL = _render_banner("CS2 TRACKER", _FULL_GLYPHS, "  ")      # 83 colunas
BANNER_COMPACT = _render_banner("CS2 TRACKER", _MINI_GLYPHS, "  ")   # 32 colunas
BANNER_FULL_MIN_WIDTH = 88  # abaixo disso o banner grande quebraria a linha


class StepBar(Static):
    """Barra inferior: quantos passos existem até jogar e onde você está."""

    def __init__(self, step: Optional[int]):
        super().__init__(self._build(step), id="step_bar")

    @staticmethod
    def _build(step: Optional[int]) -> str:
        if step is None:
            return ""
        chain = []
        for i, name in enumerate(STEPS, start=1):
            if i < step:
                chain.append(f"[green]{name}[/]")
            elif i == step:
                chain.append(f"[bold cyan]{name}[/]")
            else:
                chain.append(f"[dim]{name}[/]")
        total = STEP_BAR_CELLS * len(STEPS)
        filled = STEP_BAR_CELLS * step
        bar = "█" * filled + "░" * (total - filled)
        return (
            " [dim]>[/] ".join(chain)
            + "\n"
            + f"[cyan]{bar}[/] [bold]passo {step}/{len(STEPS)}[/] [dim]-[/] {STEPS[step - 1]}"
        )


class WizardScreen(Screen):
    """
    Casca comum de todas as telas: arte ASCII no topo, corpo da tela no
    meio, barra de passos + footer embaixo, e o "Voltar" (Esc ou botão).

    Subclasses implementam content() em vez de compose(), e sobrescrevem
    can_go_back()/action_back() quando o voltar tem semântica própria (ex.:
    a SideScreen volta um mapa antes de sair da tela).
    """

    STEP: Optional[int] = None
    BINDINGS = [("escape", "back", "Voltar")]

    def compose(self) -> ComposeResult:
        yield Static(self.banner_text(), id="banner")
        yield Vertical(*self.content(), id="body")
        yield StepBar(self.STEP)
        yield Footer()

    def content(self) -> Iterable[Widget]:
        return ()

    def banner_text(self) -> str:
        return BANNER_COMPACT

    def can_go_back(self) -> bool:
        # screen_stack começa com a tela default do App, então > 2 significa
        # "tem uma tela do wizard embaixo desta".
        return len(self.app.screen_stack) > 2

    def check_action(self, action: str, parameters) -> Optional[bool]:
        # Esconde o "Voltar" do footer nas telas onde ele não existe.
        if action == "back":
            return self.can_go_back()
        return True

    def action_back(self) -> None:
        if self.can_go_back():
            self.app.pop_screen()

    def nav_buttons(self, *extra: Button) -> Horizontal:
        """Linha de ação padrão: Voltar (quando existe) + o resto."""
        buttons: List[Button] = []
        if self.can_go_back():
            buttons.append(Button("Voltar", id="back"))
        buttons.extend(extra)
        return Horizontal(*buttons, classes="actions")


class IdentityScreen(WizardScreen):
    STEP = 1

    INTRO = (
        "Este wizard monta uma partida contra bots no servidor local: sobe o "
        "container, carrega a série, balanceia os times e ainda grava demo e "
        "stats sozinho no fim.\n\n"
        f"São {len(STEPS)} passos até jogar - a barra lá embaixo mostra onde você está. "
        "Use Tab e as setas pra navegar, Enter pra confirmar e Esc pra voltar um passo.\n\n"
        "Pra começar, digite seu nick in-game (o mesmo que aparece no placar) ou "
        "seu SteamID64 e confirme em Continuar."
    )

    def banner_text(self) -> str:
        if self.app.size.width >= BANNER_FULL_MIN_WIDTH:
            return BANNER_FULL
        return BANNER_COMPACT

    def content(self) -> Iterable[Widget]:
        return (
            Static(self.INTRO, id="intro"),
            Static("Nick in-game ou SteamID64:", classes="label"),
            Input(placeholder="ex.: can1sh ou 76561198100290385", id="player_input"),
            Static("", id="error"),
            self.nav_buttons(Button("Continuar", id="continue", variant="primary")),
        )

    def can_go_back(self) -> bool:
        return False  # primeira tela

    def on_mount(self) -> None:
        self.query_one("#player_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.advance()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.advance()

    def advance(self) -> None:
        value = self.query_one("#player_input", Input).value.strip()
        if not value:
            self.query_one("#error", Static).update("Informe um nick ou SteamID64.")
            return
        local_match_config = ROOT / "docker" / Path(self.app.match_config_file).name
        identity = core.resolve_setup_identity(value, local_match_config)
        self.app.session.set_identity(identity)
        self.app.push_screen(FormatScreen())


class FormatScreen(WizardScreen):
    STEP = 2

    def content(self) -> Iterable[Widget]:
        # bo1 já vem marcado: o RadioSet do Textual só move o cursor ao
        # montar, sem pressionar nada, e "nenhum formato escolhido" não é um
        # estado inicial útil aqui.
        return (
            Static("Formato da série:", classes="label"),
            RadioSet(
                *[
                    RadioButton(fmt.upper(), id=fmt, value=(fmt == "bo1"))
                    for fmt in FORMATS
                ],
                id="format_radio",
            ),
            Static("Jogadores por time (contando você):", classes="label"),
            Input(value="5", id="team_size_input"),
            Static("", id="error"),
            self.nav_buttons(Button("Continuar", id="continue", variant="primary")),
        )

    def on_mount(self) -> None:
        self.query_one("#format_radio", RadioSet).focus()

    def action_back(self) -> None:
        if self.can_go_back():
            self.app.session.back()
        super().action_back()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_back()
            return
        if event.button.id != "continue":
            return
        error = self.query_one("#error", Static)

        radio_set = self.query_one("#format_radio", RadioSet)
        pressed = radio_set.pressed_button
        if pressed is None:
            error.update("Escolha bo1, bo3 ou bo5.")
            return
        fmt = pressed.id

        team_size_raw = self.query_one("#team_size_input", Input).value.strip()
        if not team_size_raw.isdigit() or int(team_size_raw) < 1:
            error.update("Jogadores por time precisa ser um número >= 1.")
            return
        team_size = int(team_size_raw)

        compose_file_path = ROOT / self.app.compose_file
        max_size = core.max_team_size(compose_file_path)
        if max_size is not None and team_size > max_size:
            error.update(
                f"team_size {team_size} excede o máximo suportado pelo "
                f"CS2_MAXPLAYERS atual do {compose_file_path.name} ({max_size})."
            )
            return

        try:
            self.app.session.set_format(fmt, team_size)
            # A TUI não tem tela de Lineups (F4.2 é só do app web) — pula
            # direto pro modo anônimo de sempre, sem o jogador nunca ver
            # esse passo existir.
            self.app.session.skip_lineups()
        except core.WizardError as exc:
            error.update(str(exc))
            return
        self.app.push_screen(MapSelectScreen())


class MapSelectScreen(WizardScreen):
    """Escolha manual dos mapas (na ordem da série) ou atalho pro veto."""

    STEP = 3

    def __init__(self):
        super().__init__()
        self.selected: List[str] = []

    def content(self) -> Iterable[Widget]:
        return (
            Static("", id="map_status", classes="label"),
            Static(
                "Clique nos mapas na ordem em que quer jogar - ou pule direto pro "
                "veto, com bans e picks alternando com o bot.",
                id="map_help",
            ),
            Container(
                *[
                    Button(map_name, id=f"map-{map_name}")
                    for map_name in core.DEFAULT_MAP_POOL
                ],
                id="map-buttons",
            ),
            Static("", id="error"),
            self.nav_buttons(
                Button("Continuar", id="continue", variant="primary"),
                Button("Fazer veto", id="veto", variant="success"),
            ),
        )

    @property
    def maps_needed(self) -> int:
        return core.MAPS_PER_FORMAT[self.app.session.format]

    def on_mount(self) -> None:
        self.refresh_maps()
        self.query_one(f"#map-{core.DEFAULT_MAP_POOL[0]}", Button).focus()

    def action_back(self) -> None:
        if self.can_go_back():
            self.app.session.back()
            # A TUI não tem tela de Lineups (ver FormatScreen.on_button_
            # pressed) — se o back() acima parou lá, pula mais um passo pra
            # trás de novo, transparente, direto pro Formato.
            if self.app.session.step == core.STEP_LINEUPS:
                self.app.session.back()
        super().action_back()

    def refresh_maps(self) -> None:
        for map_name in core.DEFAULT_MAP_POOL:
            button = self.query_one(f"#map-{map_name}", Button)
            if map_name in self.selected:
                button.label = f"{self.selected.index(map_name) + 1}. {map_name}"
                button.variant = "success"
            else:
                button.label = map_name
                button.variant = "default"
        self.query_one("#map_status", Static).update(
            f"{self.app.session.format.upper()} - escolha {self.maps_needed} mapa(s). "
            f"Selecionados: {len(self.selected)}/{self.maps_needed}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        error = self.query_one("#error", Static)

        if button_id == "back":
            self.action_back()
            return

        if button_id.startswith("map-"):
            map_name = button_id.removeprefix("map-")
            if map_name in self.selected:
                self.selected.remove(map_name)
            else:
                self.selected.append(map_name)
            error.update("")
            self.refresh_maps()
            return

        if button_id == "veto":
            self.app.session.start_veto()
            self.app.push_screen(VetoScreen())
            return

        if button_id == "continue":
            try:
                self.app.session.choose_maps_direct(list(self.selected))
            except core.WizardError as exc:
                error.update(str(exc))
                return
            self.app.push_screen(SideScreen())


class VetoScreen(WizardScreen):
    """Sub-tela do passo Mapas — todo o estado do veto em si (pool restante,
    sequência, índice, histórico) vive em WizardSession; esta tela só lê e
    manda transições (session.resolve_veto_step)."""

    STEP = 3

    def __init__(self) -> None:
        super().__init__()
        # Setado ao voltar: o turno do bot roda num worker com sleep, e sem
        # isso ele voltaria a mexer numa tela que já saiu da pilha.
        self.aborted = False

    def content(self) -> Iterable[Widget]:
        return (
            Static("", id="veto_status", classes="label"),
            RichLog(id="veto_history", wrap=True, highlight=False),
            Container(id="map-buttons"),
        )

    async def on_mount(self) -> None:
        await self.refresh_state()

    def action_back(self) -> None:
        # Desfazer passo a passo não faz sentido com turno de bot aleatório
        # no meio - voltar aqui aborta o veto inteiro (session.back() com
        # veto_active=True só desarma a flag, mantém o passo Mapas) e
        # devolve pra tela de mapas, onde dá pra re-vetar ou escolher na mão.
        self.aborted = True
        self.app.session.back()
        super().action_back()

    async def refresh_state(self) -> None:
        if self.aborted:
            return
        session = self.app.session
        status = self.query_one("#veto_status", Static)
        buttons_box = self.query_one("#map-buttons", Container)
        await buttons_box.remove_children()

        step = session.current_veto_step()
        verbo = "banir" if step.action == "ban" else "escolher"
        if step.actor == "you":
            status.update(f"Sua vez: {verbo} um mapa.")
            for map_name in session.map_pool:
                await buttons_box.mount(Button(map_name, id=f"map-{map_name}"))
            buttons_box.query(Button).first().focus()
        else:
            self.run_bot_turn(step, verbo)

    @work
    async def run_bot_turn(self, step: core.VetoStep, verbo: str) -> None:
        """Timer visível antes do bot resolver - dá tempo de acompanhar em
        vez do turno resolver instantaneamente sem feedback nenhum."""
        status = self.query_one("#veto_status", Static)
        for remaining in range(BOT_TURN_COUNTDOWN_S, 0, -1):
            if self.aborted:
                return
            status.update(f"Bot vai {verbo} um mapa em {remaining}s...")
            await asyncio.sleep(1)
        if self.aborted:
            return
        choice = core.resolve_bot_step(self.app.session.map_pool)
        self.apply_step(choice)

    @work(exclusive=True)
    async def apply_step(self, map_name: str) -> None:
        if self.aborted:
            return
        session = self.app.session
        history_log = self.query_one("#veto_history", RichLog)
        before = len(session.veto_history)
        session.resolve_veto_step(map_name)
        # resolve_veto_step escreve 1 linha (ban/pick) — ou 2, se este for o
        # último passo (a segunda é "Mapa decisivo: <mapa>").
        for i, line in enumerate(session.veto_history[before:], start=before + 1):
            history_log.write(f"{i}. {line}")

        if session.step != core.STEP_MAPS:
            # Veto concluído — session já resolveu o decider e entrou no
            # passo Lados (session._enter_sides). Última linha do histórico
            # é sempre a do decider, que é justamente o que o usuário perdia
            # de vista ao sair direto pra tela seguinte.
            status = self.query_one("#veto_status", Static)
            status.update(
                f"{session.veto_history[-2]} - veto concluído.\n"
                f"{session.veto_history[-1]}. Série: {', '.join(session.maps_in_order)}"
            )
            # Pausa proposital: sem ela o último passo (que é sempre do bot) e
            # a linha do decider eram escritos e cobertos pela tela seguinte na
            # mesma frame, e o veto do bot nunca aparecia.
            await asyncio.sleep(VETO_RESULT_DWELL_S)
            if self.aborted:
                return
            # Empilha normalmente; quem cuida de não deixar o usuário voltar
            # pra um veto já concluído (que não teria como seguir em frente de
            # novo) é o SideScreen.action_back, que pula esta tela.
            self.app.push_screen(SideScreen())
            return

        await self.refresh_state()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not event.button.id or not event.button.id.startswith("map-"):
            return
        step = self.app.session.current_veto_step()
        if step is None or step.actor != "you":
            return
        map_name = event.button.id.removeprefix("map-")
        self.apply_step(map_name)


class SideScreen(WizardScreen):
    """Passo Lados — lê/escreve maps_in_order/side_index/map_choices direto
    da WizardSession; nenhum estado próprio de progresso."""

    STEP = 4

    def content(self) -> Iterable[Widget]:
        return (
            Static("", id="side_status", classes="label"),
            Container(id="side-radio-box"),
            Static("", id="error"),
            self.nav_buttons(Button("Confirmar", id="confirm", variant="primary")),
        )

    async def on_mount(self) -> None:
        await self.refresh_prompt()

    async def on_screen_resume(self) -> None:
        # Voltando do resumo: SummaryScreen.action_back já chamou
        # session.back() (que desfaz o último lado escolhido) antes de dar
        # pop — session.side_index já reflete o mapa certo, só precisa
        # re-renderizar.
        await self.refresh_prompt()

    async def refresh_prompt(self) -> None:
        session = self.app.session
        map_name = session.maps_in_order[session.side_index]
        self.query_one("#side_status", Static).update(
            f"Mapa {session.side_index + 1}/{len(session.maps_in_order)}: "
            f"{map_name} - seu lado?"
        )
        # RadioSet não expõe um jeito de limpar a seleção (pressed_button
        # não tem setter) - remonta do zero a cada mapa em vez de tentar
        # resetar o widget existente.
        box = self.query_one("#side-radio-box", Container)
        await box.remove_children()
        radio_set = RadioSet(
            *[RadioButton(label, id=code) for code, label in SIDES], id="side_radio"
        )
        await box.mount(radio_set)
        # Foco explícito: o #side-radio-box é composto vazio (o RadioSet só
        # entra aqui), então o auto-focus do Textual pegaria o Confirmar, que
        # nesse momento só sabe reclamar que nada foi escolhido.
        radio_set.focus()

    def can_go_back(self) -> bool:
        return self.app.session.side_index > 0 or super().can_go_back()

    def action_back(self) -> None:
        had_index = self.app.session.side_index > 0
        self.app.session.back()
        if had_index:
            self.query_one("#error", Static).update("")
            self.run_worker(self.refresh_prompt())
            return
        super().action_back()
        # Um veto concluído não tem como seguir em frente de novo (a sequência
        # já acabou), então voltar dali seria um beco sem saída: pula direto
        # pra tela de mapas, onde dá pra re-vetar ou escolher na mão.
        if isinstance(self.app.screen, VetoScreen):
            self.app.pop_screen()

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_back()
            return
        if event.button.id != "confirm":
            return
        radio_set = self.query_one("#side_radio", RadioSet)
        pressed = radio_set.pressed_button
        error = self.query_one("#error", Static)
        if pressed is None:
            error.update("Escolha CT ou TR.")
            return
        error.update("")

        session = self.app.session
        session.set_side(pressed.id)

        if session.step == core.STEP_SUMMARY:
            self.app.push_screen(SummaryScreen())
        else:
            await self.refresh_prompt()


class SummaryScreen(WizardScreen):
    STEP = 5

    def content(self) -> Iterable[Widget]:
        session = self.app.session
        lines = [
            f"Jogador: {session.identity.name}"
            + (f" ({session.identity.steamid})" if session.identity.has_steamid else ""),
            f"Formato: {session.format.upper()}",
            f"Jogadores por time: {session.team_size}",
            "Mapas:",
        ]
        for i, choice in enumerate(session.map_choices, start=1):
            lines.append(f"  {i}. {choice.map_name} ({choice.side.upper()})")

        return (
            Static("\n".join(lines), id="summary_text"),
            self.nav_buttons(Button("Iniciar partida", id="launch", variant="primary")),
        )

    def on_mount(self) -> None:
        self.query_one("#launch", Button).focus()

    def action_back(self) -> None:
        # Desfaz o último lado escolhido (session.back() no passo Resumo
        # volta pro passo Lados já com side_index decrementado) antes do pop
        # — SideScreen.on_screen_resume só precisa re-renderizar.
        self.app.session.back()
        super().action_back()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_back()
            return
        if event.button.id != "launch":
            return
        self.app.push_screen(LaunchScreen())


class LaunchScreen(WizardScreen):
    STEP = 6

    HINT = (
        "Enquanto o servidor sobe, deixe o CS2 aberto. Quando o log pedir, conecte por\n"
        "Jogar > Servidores > Rede Local, ou pela console do jogo: connect 127.0.0.1:27015\n"
        "Já conectado, digite .ready no chat do jogo e volte aqui pra confirmar.\n"
        "Se um mapa ficar no warmup, use Forçar início para repetir o start e rebalancear."
    )

    def content(self) -> Iterable[Widget]:
        return (
            Static(self.HINT, id="launch_hint"),
            Horizontal(
                Button(
                    "Forçar início / rebalancear bots",
                    id="force_start",
                    variant="warning",
                ),
                Container(id="ready-box"),
                id="launch-actions",
            ),
            RichLog(id="log", wrap=True, highlight=False),
        )

    def can_go_back(self) -> bool:
        return False  # a partida já está subindo

    def on_mount(self) -> None:
        self.run_worker(self.do_launch, thread=True)

    # -- ponte entre a worker thread e a UI -------------------------------
    def confirm_ready(self) -> None:
        """Chamado de dentro do run_match (worker thread) no lugar do input()
        bloqueante do CLI: mostra o botão e segura a thread até o clique."""
        event = threading.Event()
        self.app.ready_event = event
        self.app.call_from_thread(self.show_ready_button)
        event.wait()

    def show_ready_button(self) -> None:
        box = self.query_one("#ready-box", Container)
        button = Button(
            "Já conectei e dei .ready - iniciar partida", id="ready", variant="success"
        )
        box.mount(button)
        button.focus()

    def _make_log(self, log_widget: RichLog) -> core.Sink:
        """Sink de log explícito (F2.2, docs/features/M2-nucleo.md) — repassa
        cada linha pro RichLog via call_from_thread (do_launch/do_force_start
        rodam em worker thread, e widgets Textual só podem ser tocados a
        partir da thread principal). Sem redirect_stdout: só o que passa por
        aqui aparece na tela, então nenhuma saída de outra thread (ex.: o
        servidor web, numa app futura) cai aqui por engano."""
        app = self.app

        def log(text: str) -> None:
            text = text.rstrip("\n")
            if text:
                app.call_from_thread(log_widget.write, text)

        return log

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "force_start":
            event.button.disabled = True
            self.run_worker(
                lambda: self.do_force_start(event.button),
                thread=True,
                exclusive=False,
            )
            return
        if event.button.id != "ready":
            return
        await self.query_one("#ready-box", Container).remove_children()
        ready_event = self.app.ready_event
        self.app.ready_event = None
        if ready_event:
            ready_event.set()

    def do_force_start(self, button: Button) -> None:
        app = self.app
        log = self._make_log(self.query_one("#log", RichLog))
        setup = app.session.to_match_setup()
        try:
            log("[WIZARD] Início manual solicitado.")
            core.force_start(
                setup,
                container_name=app.container_name,
                match_config_file=app.match_config_file,
                rcon_host=app.rcon_host,
                rcon_port=app.rcon_port,
                rcon_password=app.rcon_password,
                rcon_lock=app.rcon_lock,
                log=log,
            )
            log("[WIZARD] Início manual concluído.")
        except BaseException as exc:
            log(f"[ERRO] Falha no início manual: {exc}")
        finally:
            app.call_from_thread(setattr, button, "disabled", False)

    def do_launch(self) -> None:
        app = self.app
        log = self._make_log(self.query_one("#log", RichLog))
        setup = app.session.to_match_setup()

        def on_watcher_started(proc):
            app.call_from_thread(setattr, app, "watcher_proc", proc)

        try:
            core.launch(
                setup,
                container_name=app.container_name,
                compose_file=app.compose_file,
                match_config_file=app.match_config_file,
                rcon_host=app.rcon_host,
                rcon_port=app.rcon_port,
                rcon_password=app.rcon_password,
                boot_timeout=app.boot_timeout,
                skip_up=app.skip_up,
                on_watcher_started=on_watcher_started,
                watcher_output=lambda line: log(f"[WATCHER] {line}"),
                confirm_ready=self.confirm_ready,
                rcon_lock=app.rcon_lock,
                log=log,
            )
        except BaseException as exc:  # inclui o sys.exit() do start_match
            log(f"[ERRO] {exc}")
        finally:
            app.call_from_thread(setattr, app, "watcher_proc", None)


class WizardApp(App):
    CSS = """
    #banner {
        color: $accent;
        text-style: bold;
        padding: 0 2;
        height: auto;
    }
    #body {
        padding: 1 2;
        height: 1fr;
        overflow-y: auto;
    }
    #step_bar {
        height: 2;
        padding: 0 2;
        background: $panel;
    }
    .label {
        margin-top: 1;
    }
    .actions {
        height: auto;
        margin-top: 1;
    }
    .actions Button {
        margin-right: 2;
    }
    #intro, #map_help, #launch_hint {
        color: $text-muted;
        margin-bottom: 1;
    }
    #error {
        color: red;
    }
    /* Grid pra os 7 mapas do pool caberem em 2 linhas em vez de virar uma
       coluna de 21 linhas (o veto ainda encolhe a lista a cada passo). */
    #map-buttons {
        layout: grid;
        grid-size: 4;
        grid-rows: 3;
        grid-gutter: 0 1;
        height: auto;
    }
    #map-buttons Button {
        width: 100%;
    }
    #launch-actions, #ready-box {
        height: auto;
    }
    #launch-actions {
        margin-bottom: 1;
    }
    #launch-actions Button {
        margin-right: 2;
    }
    /* Container tem height: 1fr por padrão, o que empurraria os botões de
       ação pro rodapé do corpo com um vão enorme no meio. */
    #side-radio-box {
        height: auto;
    }
    #log {
        height: 1fr;
    }
    #veto_history {
        height: 10;
        border: solid $accent;
    }
    """
    BINDINGS = [("q", "quit", "Sair")]
    TITLE = "CS2 Tracker"

    def __init__(
        self,
        *,
        container_name: str = CONTAINER_NAME,
        compose_file: str = COMPOSE_FILE,
        match_config_file: str = MATCH_CONFIG_FILE,
        rcon_host: str = "127.0.0.1",
        rcon_port: int = 27015,
        rcon_password: Optional[str] = None,
        boot_timeout: int = 300,
        skip_up: bool = False,
    ):
        super().__init__()
        self.container_name = container_name
        self.compose_file = compose_file
        self.match_config_file = match_config_file
        self.rcon_host = rcon_host
        self.rcon_port = rcon_port
        self.rcon_password = rcon_password
        self.boot_timeout = boot_timeout
        self.skip_up = skip_up

        # Estado do wizard (F2.1, docs/features/M2-nucleo.md) — as telas
        # (ver *Screen acima) leem e escrevem aqui em vez de em atributos
        # soltos do App; toda a lógica de transição/validação/"voltar" vive
        # em WizardSession, sem nenhuma dependência de Textual.
        self.session = core.WizardSession()

        # Setado por LaunchScreen.do_launch assim que run_match sobe o
        # watcher.py (via on_watcher_started) - run_match fica bloqueado
        # em watcher_proc.wait() numa worker thread que o Textual não
        # enxerga, então sair da UI (q/ctrl+q) não encerraria o watcher
        # sozinho sem isso; action_quit abaixo mata o processo primeiro.
        self.watcher_proc = None
        # Idem pro "já conectei": a worker thread fica parada nesse Event, e
        # sair da UI sem liberá-lo deixaria a thread pendurada no exit.
        self.ready_event: Optional[threading.Event] = None
        # Serializa as sequências RCON automáticas e as disparadas pelo
        # botão manual da LaunchScreen.
        self.rcon_lock = threading.Lock()

    def on_mount(self) -> None:
        self.push_screen(IdentityScreen())

    def action_quit(self) -> None:
        if self.ready_event:
            self.ready_event.set()
            self.ready_event = None
        if self.watcher_proc and self.watcher_proc.poll() is None:
            self.watcher_proc.terminate()
            try:
                self.watcher_proc.wait(timeout=10)
            except Exception:
                self.watcher_proc.kill()
        self.exit()


def main():
    env = load_env(ROOT / ".env")
    rcon_password = env.get("CS2_RCONPW")
    if not rcon_password or rcon_password == "CHANGE_ME_LOCAL_ONLY":
        raise SystemExit(
            "[ERRO] CS2_RCONPW não configurado - preencha .env (veja .env.example)."
        )
    WizardApp(rcon_password=rcon_password).run()


if __name__ == "__main__":
    main()
