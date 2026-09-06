#!/usr/bin/env python3
"""
CS2 Tracker — Wizard (Textual)
================================
UI do wizard de partida: nick/SteamID64 -> mapa/formato (bo1/bo3/bo5) ->
veto (bans/picks) -> lado por mapa -> resumo -> dispara start_match.

Este arquivo só monta telas e reage a eventos — toda a lógica (veto,
montagem do match_config, orquestração docker/RCON) vive em wizard_core.py
e start_match.py, sem nenhum import de Textual. A ideia é que uma futura
troca de UI (ex.: Tauri) precise reescrever só este arquivo.

LIMITAÇÃO CONHECIDA deste protótipo: start_match.run_match() usa um
input() bloqueante pra esperar o "pronto pra forçar início" (o mesmo
prompt que o CLI usa). Como o Textual toma conta do terminal, esse input()
rodando na worker thread da LaunchScreen não é interativo pela tela do
wizard — acompanhe o terminal onde o wizard foi iniciado nesse momento
específico do fluxo (é o único ponto do protótipo que ainda depende do
terminal "por baixo" da TUI).

Uso:
    .venv\\Scripts\\python.exe wizard_tui.py
"""
import asyncio
import io
from pathlib import Path
from typing import List, Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button, Footer, Header, Input, RadioButton, RadioSet, RichLog, Static,
)

from config import COMPOSE_FILE, CONTAINER_NAME, MATCH_CONFIG_FILE, ROOT, load_env
import wizard_core as core

FORMATS = ["bo1", "bo3", "bo5"]
SIDES = [("ct", "CT"), ("t", "TR")]
BOT_TURN_COUNTDOWN_S = 2  # "timer" visível antes do bot resolver o turno de veto


class IdentityScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("Nick in-game ou SteamID64:", classes="label"),
            Input(placeholder="ex.: can1sh ou 76561198100290385", id="player_input"),
            Static("", id="error"),
            Button("Continuar", id="continue", variant="primary"),
            id="body",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "continue":
            return
        value = self.query_one("#player_input", Input).value.strip()
        if not value:
            self.query_one("#error", Static).update("Informe um nick ou SteamID64.")
            return
        local_match_config = ROOT / "docker" / Path(self.app.match_config_file).name
        self.app.identity = core.resolve_setup_identity(value, local_match_config)
        self.app.push_screen(FormatScreen())


class FormatScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("Formato da série:", classes="label"),
            RadioSet(*[RadioButton(fmt.upper(), id=fmt) for fmt in FORMATS], id="format_radio"),
            Static("Jogadores por time (contando você):", classes="label"),
            Input(value="5", id="team_size_input"),
            Static("", id="error"),
            Button("Continuar", id="continue", variant="primary"),
            id="body",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
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

        self.app.format = fmt
        self.app.team_size = team_size

        pool = list(core.DEFAULT_MAP_POOL)
        steps = core.generate_veto_sequence(pool, fmt)
        self.app.push_screen(VetoScreen(pool, steps))


class VetoScreen(Screen):
    def __init__(self, pool: List[str], steps: List[core.VetoStep]):
        super().__init__()
        self.pool = pool
        self.steps = steps
        self.step_index = 0
        self.picks: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("", id="veto_status", classes="label"),
            RichLog(id="veto_history", wrap=True, highlight=False),
            Container(id="map-buttons"),
            id="body",
        )
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_state()

    def current_step(self) -> Optional[core.VetoStep]:
        if self.step_index >= len(self.steps):
            return None
        return self.steps[self.step_index]

    def log_history(self, actor: core.Actor, action: core.Action, map_name: str) -> None:
        quem = "Você" if actor == "you" else "Bot"
        verbo = "baniu" if action == "ban" else "escolheu"
        self.query_one("#veto_history", RichLog).write(
            f"{self.step_index}. {quem} {verbo} {map_name}"
        )

    async def refresh_state(self) -> None:
        status = self.query_one("#veto_status", Static)
        buttons_box = self.query_one("#map-buttons", Container)
        await buttons_box.remove_children()

        step = self.current_step()
        if step is None:
            decider = core.decider_map(self.pool)
            maps_in_order = self.picks + [decider]
            self.query_one("#veto_history", RichLog).write(
                f"{len(self.steps) + 1}. Mapa decisivo: {decider}"
            )
            status.update(f"Veto concluído. Mapas: {', '.join(maps_in_order)}")
            self.app.push_screen(SideScreen(maps_in_order))
            return

        verbo = "banir" if step.action == "ban" else "escolher"
        if step.actor == "you":
            status.update(f"Sua vez: {verbo} um mapa.")
            for map_name in self.pool:
                await buttons_box.mount(Button(map_name, id=f"map-{map_name}"))
        else:
            self.run_bot_turn(step, verbo)

    @work
    async def run_bot_turn(self, step: core.VetoStep, verbo: str) -> None:
        """Timer visível antes do bot resolver — dá tempo de acompanhar em
        vez do turno resolver instantaneamente sem feedback nenhum."""
        status = self.query_one("#veto_status", Static)
        for remaining in range(BOT_TURN_COUNTDOWN_S, 0, -1):
            status.update(f"Bot vai {verbo} um mapa em {remaining}s...")
            await asyncio.sleep(1)
        choice = core.resolve_bot_step(self.pool)
        self.apply_step(step, choice)

    @work
    async def apply_step(self, step: core.VetoStep, map_name: str) -> None:
        self.pool.remove(map_name)
        if step.action == "pick":
            self.picks.append(map_name)
        self.step_index += 1
        self.log_history(step.actor, step.action, map_name)
        await self.refresh_state()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not event.button.id or not event.button.id.startswith("map-"):
            return
        step = self.current_step()
        if step is None or step.actor != "you":
            return
        map_name = event.button.id.removeprefix("map-")
        self.apply_step(step, map_name)


class SideScreen(Screen):
    def __init__(self, maps_in_order: List[str]):
        super().__init__()
        self.maps_in_order = maps_in_order
        self.index = 0
        self.choices: List[core.MapChoice] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("", id="side_status", classes="label"),
            Container(id="side-radio-box"),
            Static("", id="error"),
            Button("Confirmar", id="confirm", variant="primary"),
            id="body",
        )
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_prompt()

    async def refresh_prompt(self) -> None:
        map_name = self.maps_in_order[self.index]
        self.query_one("#side_status", Static).update(
            f"Mapa {self.index + 1}/{len(self.maps_in_order)}: {map_name} — seu lado?"
        )
        # RadioSet não expõe um jeito de limpar a seleção (pressed_button
        # não tem setter) — remonta do zero a cada mapa em vez de tentar
        # resetar o widget existente.
        box = self.query_one("#side-radio-box", Container)
        await box.remove_children()
        await box.mount(RadioSet(*[RadioButton(label, id=code) for code, label in SIDES], id="side_radio"))

    @work
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "confirm":
            return
        radio_set = self.query_one("#side_radio", RadioSet)
        pressed = radio_set.pressed_button
        error = self.query_one("#error", Static)
        if pressed is None:
            error.update("Escolha CT ou TR.")
            return
        error.update("")

        map_name = self.maps_in_order[self.index]
        self.choices.append(core.MapChoice(map_name=map_name, side=pressed.id))
        self.index += 1

        if self.index >= len(self.maps_in_order):
            self.app.setup_maps = self.choices
            self.app.push_screen(SummaryScreen())
        else:
            await self.refresh_prompt()


class SummaryScreen(Screen):
    def compose(self) -> ComposeResult:
        app = self.app
        lines = [
            f"Jogador: {app.identity.name}"
            + (f" ({app.identity.steamid})" if app.identity.has_steamid else ""),
            f"Formato: {app.format.upper()}",
            f"Jogadores por time: {app.team_size}",
            "Mapas:",
        ]
        for i, choice in enumerate(app.setup_maps, start=1):
            lines.append(f"  {i}. {choice.map_name} ({choice.side.upper()})")

        yield Header()
        yield Vertical(
            Static("\n".join(lines), id="summary_text"),
            Button("Iniciar partida", id="launch", variant="primary"),
            id="body",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "launch":
            return
        self.app.push_screen(LaunchScreen())


class _RichLogStream(io.TextIOBase):
    """stdout substituto que repassa cada write() pro RichLog da tela de
    launch, sempre via call_from_thread (run_match roda numa worker thread,
    e widgets Textual só podem ser tocados a partir da thread principal)."""

    def __init__(self, app: App, log_widget: RichLog):
        self._app = app
        self._log_widget = log_widget

    def write(self, text: str) -> int:
        text = text.rstrip("\n")
        if text:
            self._app.call_from_thread(self._log_widget.write, text)
        return len(text)

    def flush(self) -> None:
        pass


class LaunchScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(RichLog(id="log", wrap=True, highlight=False), id="body")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.do_launch, thread=True)

    def do_launch(self) -> None:
        import contextlib

        app = self.app
        log_widget = self.query_one("#log", RichLog)
        stream = _RichLogStream(app, log_widget)

        setup = core.MatchSetup(
            identity=app.identity,
            format=app.format,
            team_size=app.team_size,
            maps=app.setup_maps,
        )
        try:
            with contextlib.redirect_stdout(stream):
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
                )
        except Exception as exc:
            app.call_from_thread(log_widget.write, f"[ERRO] {exc}")


class WizardApp(App):
    CSS = """
    #body {
        padding: 1 2;
        height: 1fr;
        overflow-y: auto;
    }
    .label {
        margin-top: 1;
    }
    #error {
        color: red;
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

        # Preenchidos ao longo do wizard pelas telas (ver *Screen acima).
        self.identity = None
        self.format: Optional[str] = None
        self.team_size: Optional[int] = None
        self.setup_maps: List[core.MapChoice] = []

    def on_mount(self) -> None:
        self.push_screen(IdentityScreen())


def main():
    env = load_env(ROOT / ".env")
    rcon_password = env.get("CS2_RCONPW")
    if not rcon_password or rcon_password == "CHANGE_ME_LOCAL_ONLY":
        raise SystemExit(
            "[ERRO] CS2_RCONPW não configurado — preencha .env (veja .env.example)."
        )
    WizardApp(rcon_password=rcon_password).run()


if __name__ == "__main__":
    main()
