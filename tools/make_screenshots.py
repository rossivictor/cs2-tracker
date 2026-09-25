#!/usr/bin/env python3
"""
CS2 Tracker — Screenshots do wizard
====================================
Gera os SVGs de docs/img/ que o README usa, rodando o wizard_tui.py headless
(App.run_test do Textual) e salvando um screenshot por tela. Como o script
percorre o fluxo inteiro — Jogador, Formato, Mapas, Veto, Lados, Resumo,
Partida —, ele também funciona como smoke test da TUI: se algum seletor ou
alguma tela quebrar, ele falha em vez de gerar imagem errada.

Nada de Docker/RCON acontece aqui: wizard_core.launch é substituído por um
log falso, então o match_config real nunca é reescrito.

Uso:
    .venv\\Scripts\\python.exe tools/make_screenshots.py
"""
import asyncio
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import wizard_core as core       # noqa: E402
import wizard_tui                # noqa: E402
from wizard_tui import (         # noqa: E402
    IdentityScreen, LaunchScreen, MapSelectScreen, SideScreen, SummaryScreen,
    VetoScreen, WizardApp,
)

OUT_DIR = ROOT / "docs" / "img"
SIZE = (100, 34)
PLAYER = "can1sh"
FORMAT = "bo3"
VETO_SEED = 7  # turno do bot é random.choice — fixa a sequência entre execuções

FAKE_LOG = [
    "[CONFIG] match_config.spike.json: maplist -> ['de_mirage', 'de_nuke', 'de_inferno']",
    "[DOCKER] Container 'cs2-spike' já está rodando.",
    "[WATCHER] Subindo watcher.py --mode matchzy --player can1sh em paralelo...",
    "[RCON] Esperando 127.0.0.1:27015 ficar disponível (timeout 300s)...",
    "[RCON] Conectado.",
    "[WATCHER] [WATCHER] Seguindo docker logs de cs2-spike...",
    "[MATCHZY] Carregando match_config.spike.json...",
    "  -> Match config loaded",
    "",
    "=" * 70,
    "Agora conecte no servidor pelo client normal do CS2:",
    "  Servidores -> Rede Local -> conectar",
    "  (ou, com a console do jogo ligada: connect 127.0.0.1:27015)",
    "Depois de conectado, digite '.ready' no chat do jogo.",
    "=" * 70,
]


def fake_launch(setup, *, confirm_ready=None, **kwargs):
    """Stand-in de wizard_core.launch: imprime um log plausível e para na
    mesma confirmação que o run_match de verdade pede."""
    for line in FAKE_LOG:
        print(line)
    if confirm_ready:
        confirm_ready()


async def wait_until(app, predicate, timeout=30.0, step=0.1):
    """Espera uma condição da UI (troca de tela, botão montado) em vez de
    chutar sleeps — o veto tem turnos de bot com timer de 2s no meio."""
    waited = 0.0
    while waited < timeout:
        if predicate():
            return
        await asyncio.sleep(step)
        waited += step
    raise TimeoutError(f"condição não satisfeita em {timeout}s (tela: {app.screen!r})")


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(VETO_SEED)
    core.launch = fake_launch

    app = WizardApp(rcon_password="dummy")
    saved = []

    async def shot(name):
        # Espera o efeito "-active" do Button (0.2s) passar: um print tirado
        # logo depois de um clique pegaria o botão aceso, e a cor variaria
        # entre execuções.
        await asyncio.sleep(0.3)
        path = Path(app.save_screenshot(name, path=str(OUT_DIR)))
        # O Rich gera um id aleatório por export ("terminal-<n>-r1", ...), o que
        # faria cada regeração aparecer no git diff mesmo sem a UI ter mudado.
        # Cada SVG é referenciado como <img> no README, isolado, então um id
        # fixo por arquivo não colide com nada.
        svg = path.read_text(encoding="utf-8")
        svg = re.sub(r"terminal-\d+", f"terminal-{path.stem}", svg)
        path.write_text(svg, encoding="utf-8")
        saved.append(name)

    async with app.run_test(size=SIZE) as pilot:
        # --- 1/6 Jogador -------------------------------------------------
        # push_screen(IdentityScreen) acontece no on_mount do App, então a
        # primeira tela ainda não existe quando o run_test devolve o pilot.
        await wait_until(app, lambda: isinstance(app.screen, IdentityScreen))
        player_input = app.screen.query_one("#player_input")
        # Sem isso o cursor piscando entra no SVG numa fase aleatória e o
        # arquivo muda a cada regeração mesmo sem a UI ter mudado.
        player_input.cursor_blink = False
        player_input.value = PLAYER
        await pilot.pause()
        await shot("01-jogador.svg")
        await pilot.click("#continue")

        # --- 2/6 Formato -------------------------------------------------
        await pilot.click(f"#{FORMAT}")
        await pilot.pause()
        await shot("02-formato.svg")
        await pilot.click("#continue")

        # --- 3/6 Mapas ---------------------------------------------------
        await wait_until(app, lambda: isinstance(app.screen, MapSelectScreen))
        await pilot.click("#map-de_mirage")
        await pilot.pause()
        await shot("03-mapas.svg")
        # O print do veto é o interessante aqui, então desmarca e vai pro veto.
        await pilot.click("#map-de_mirage")
        await pilot.click("#veto")

        # --- 3/6 Veto ----------------------------------------------------
        await wait_until(app, lambda: isinstance(app.screen, VetoScreen))
        veto = app.screen
        shot_taken = False
        while isinstance(app.screen, VetoScreen):
            buttons = list(veto.query("#map-buttons Button"))
            if not buttons:  # turno do bot, com countdown visível
                await asyncio.sleep(0.2)
                continue
            if not shot_taken and veto.step_index >= 2:
                # Já tem histórico na tela (seu ban + o do bot) e é sua vez.
                await shot("04-veto.svg")
                shot_taken = True
            await pilot.click(f"#{buttons[0].id}")
            await asyncio.sleep(0.25)

        # --- 4/6 Lados ---------------------------------------------------
        await wait_until(app, lambda: isinstance(app.screen, SideScreen))
        side = app.screen
        while isinstance(app.screen, SideScreen):
            # O RadioSet é remontado a cada mapa (refresh_prompt), então espera
            # ele existir em vez de assumir que já está na árvore.
            await wait_until(app, lambda: bool(side.query("#side_radio")))
            await pilot.click("#ct")
            await pilot.pause()
            if side.index == 0:
                await shot("05-lados.svg")
            await pilot.click("#confirm")
            # Button ignora um clique dentro do efeito -active (0.2s), e o
            # Confirmar é o mesmo widget em todos os mapas da série.
            await asyncio.sleep(0.25)

        # --- 5/6 Resumo --------------------------------------------------
        await wait_until(app, lambda: isinstance(app.screen, SummaryScreen))
        await pilot.pause()
        await shot("06-resumo.svg")
        await pilot.click("#launch")

        # --- 6/6 Partida -------------------------------------------------
        await wait_until(app, lambda: isinstance(app.screen, LaunchScreen))
        await wait_until(app, lambda: bool(app.screen.query("#ready")))
        await pilot.pause()
        await shot("07-partida.svg")
        await pilot.click("#ready")  # libera a worker thread parada no Event
        await pilot.pause()

    for name in saved:
        print(f"[SHOT] docs/img/{name}")
    print(f"[OK] {len(saved)} screenshot(s) em {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
