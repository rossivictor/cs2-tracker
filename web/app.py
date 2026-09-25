#!/usr/bin/env python3
"""
CS2 Tracker — Wizard Web (F3.1/F3.2, docs/features/M3-web-paridade.md)
=========================================================================
Paridade com wizard_tui.py até o Resumo (Jogador -> Formato -> Mapas/Veto ->
Lados -> Resumo), num app FastAPI em vez de Textual. Toda a lógica de
transição/validação continua em wizard_core.WizardSession (F2.1) — este
arquivo só monta rotas e templates, igual o wizard_tui.py só monta telas.

A tela de Partida (SSE, log ao vivo, `.ready`) é a F3.3/item 6 do
docs/SPEC.md — ainda não existe aqui. Chegar no Resumo é o fim do caminho
por enquanto; pra realmente jogar, use wizard_tui.py ou start_match.py.

Uso:
    .venv\\Scripts\\python.exe -m uvicorn web.app:app --reload
Abre em http://127.0.0.1:8000/
"""
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # importa os módulos da raiz do repo (wizard_core, config, ...)

import home
import matches
import report
import roster
import stats
import wizard_core as core
from config import COMPOSE_FILE, CONTAINER_NAME, DB_PATH

PROFILE_PATH = ROOT / "data" / "profile.json"

STEP_NAMES = ["Jogador & Formato", "Lineups", "Mapas", "Lados", "Resumo"]
STEP_PATHS = {
    core.STEP_IDENTITY: "/setup",
    core.STEP_FORMAT: "/setup",
    core.STEP_LINEUPS: "/lineups",
    core.STEP_MAPS: "/maps",
    core.STEP_SIDES: "/sides",
    core.STEP_SUMMARY: "/summary",
}
# Jogador e Formato viraram uma única tela (item 6, 2026-09-20) — o
# WizardSession de baixo continua com os dois passos separados (é o mesmo
# core usado pela TUI, wizard_tui.py, que ainda mostra telas distintas), só
# a barra de progresso do web precisa achatar os dois num item só.
_STEP_DISPLAY_INDEX = {
    core.STEP_IDENTITY: 1,
    core.STEP_FORMAT: 1,
    core.STEP_LINEUPS: 2,
    core.STEP_MAPS: 3,
    core.STEP_SIDES: 4,
    core.STEP_SUMMARY: 5,
}

app = FastAPI(title="CS2 Tracker — Wizard")
# Duas pastas de template na mesma Environment: web/templates (wizard) e
# templates/ na raiz (home/report, docs/features/M3.5-home.md) — o wizard
# agora renderiza a home como fundo do modal de partida (item 8,
# 2026-09-20), então os dois conjuntos de página precisam compartilhar
# FileSystemLoader pra "extends"/"include" cruzarem as pastas.
templates = Jinja2Templates(directory=[
    str(Path(__file__).parent / "templates"),
    str(ROOT / "templates"),
])
# Mesma pasta static/ que home.py/report.py usam (logos de time, ícones de
# mapa/arma) — servida aqui pra a grade de logos da tela de Lineups (F4.2).
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

# Estado do wizard vivo no servidor (F3.1) — um único WizardSession de
# propósito: D1/D5 da SPEC.md são "1 humano, app local pessoal", não há
# conceito de múltiplos usuários simultâneos aqui.
_session = core.WizardSession()
# Seleção de mapas em progresso na tela de Mapas (escolha direta) — estado
# de UI, não da sessão: só vira parte do WizardSession quando o usuário
# confirma (session.choose_maps_direct), igual o MapSelectScreen.selected
# do wizard_tui.py.
_direct_selection: List[str] = []
_flash: Optional[str] = None

# Estado de UI da tela de Lineups (F4.2) — vagas em progresso, uma lista de
# Optional[str] por lado (None = vaga vazia). Só vira parte do WizardSession
# quando o usuário confirma (session.set_lineups), igual _direct_selection
# faz pra Mapas.
_lineup_slots: Dict[str, List[Optional[str]]] = {"mine": [], "enemy": []}
# Slot sendo escolhido agora ("mine"/"enemy", índice) — controla se a tela
# de Lineups mostra o buscador expandido pra aquela vaga. None = nenhum.
_browsing: Optional[tuple] = None
# "Competitivo" (grade de logos) — lado trava edição manual, vira anônimo
# (bot aleatório de verdade, decidido pelo servidor na hora de jogar, não
# um perfil pro nomeado). Zera os slots do lado ao ligar.
_competitive: Dict[str, bool] = {"mine": False, "enemy": False}

# Catálogo de perfis (F4.1) — roster.py já filtra times com perfil ausente
# no VPK (F1.1). Carregado sob demanda (não no import do módulo) e cacheado
# — testes monkeypatcham _profile_cards_cache pra não depender do container
# real, e o app não trava na subida se o docker ainda não estiver de pé.
_ROSTERS = roster.load_rosters()
_profile_cards_cache: Optional[List[roster.ProfileCard]] = None


def _get_profile_cards() -> List[roster.ProfileCard]:
    global _profile_cards_cache
    if _profile_cards_cache is None:
        try:
            templates = roster.read_container_profile_templates(CONTAINER_NAME)
        except Exception:
            # Container fora do ar (ex.: app rodando sem docker up ainda) —
            # catálogo vazio em vez de derrubar a tela de Lineups.
            templates = {}
        _profile_cards_cache = roster.build_profile_catalog(_ROSTERS, templates)
    return _profile_cards_cache


def _set_flash(message: str) -> None:
    global _flash
    _flash = message


def _pop_flash() -> Optional[str]:
    global _flash
    message, _flash = _flash, None
    return message


def _redirect_for_step() -> RedirectResponse:
    path = STEP_PATHS[_session.step]
    if _session.step == core.STEP_MAPS and _session.veto_active:
        path = "/veto"
    return RedirectResponse(path, status_code=HTTP_303_SEE_OTHER)


def _load_saved_profile() -> Optional[str]:
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        return data.get("player") or None
    except (OSError, json.JSONDecodeError):
        return None


def _save_profile(player: str) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps({"player": player}, ensure_ascii=False), encoding="utf-8")


def _render(request: Request, name: str, **context):
    # O wizard renderiza como modal por cima da home (item 8, 2026-09-20) —
    # wizard_modal.html inclui _home_content.html no fundo, então toda tela
    # do wizard carrega o mesmo contexto que a home usa pros boxes reais.
    base_ctx = home.build_context(DB_PATH)
    base_ctx["active_page"] = None
    base_ctx.update(context)
    base_ctx.update(
        steps=STEP_NAMES,
        step=_STEP_DISPLAY_INDEX.get(_session.step, len(STEP_NAMES)),
        session=_session,
        error=_pop_flash(),
    )
    return templates.TemplateResponse(request, name, base_ctx)


# --------------------------------------------------------------------------- #
# Jogador + Formato (item 6, 2026-09-20: uma tela só — "quem é você e como
# você quer jogar" — D8: perfil salvo localmente, sem Steam OpenID)
# --------------------------------------------------------------------------- #

@app.get("/")
def index(request: Request):
    # A home é a tela real agora (item 8, 2026-09-20) — não redireciona mais
    # pro wizard. Abrir/retomar a partida é um clique em "JOGAR" ou
    # "Configurar partida" (/setup), que reidrata o WizardSession existente
    # se já houver um em andamento (D14).
    return templates.TemplateResponse(request, "home.html", home.build_context(DB_PATH))


@app.get("/partidas")
def matches_screen(request: Request, lado: str = "all", mapa: Optional[str] = None):
    """Lista de todas as partidas (F6.1). Renderizada no servidor, ao
    contrário de /report — que embute o payload inteiro como JSON porque
    precisa funcionar também como arquivo estático aberto via file://."""
    context = matches.build_list_context(DB_PATH, side=lado, map_filter=mapa)
    return templates.TemplateResponse(request, "matches.html", context)


@app.get("/partidas/{match_id}")
def match_detail_screen(request: Request, match_id: int, lado: str = "all"):
    context = matches.build_detail_context(DB_PATH, match_id, side=lado)
    if context is None:
        return Response(
            content=f"Partida {match_id} não existe no banco.",
            status_code=404,
            media_type="text/plain; charset=utf-8",
        )
    return templates.TemplateResponse(request, "match_detail.html", context)


@app.get("/report")
def report_screen():
    """Relatório antigo (dashboard + detalhe numa página só, trocados por
    location.hash). Continua de pé porque é o mesmo código que report.py usa
    pra gerar o report.html estático — o único que funciona offline. Sai de
    cena quando /partidas provar paridade em uso real."""
    return Response(content=report.build_html(report.build_payload(DB_PATH)), media_type="text/html")


@app.get("/setup")
def setup_form(request: Request):
    # Perfil salvo (D8) só é auto-aplicado numa sessão que nunca teve
    # identidade nenhuma — se o passo voltou pra IDENTITY por /back,
    # _session.identity já está preenchido e este bloco não mexe nele, ou o
    # "Voltar" pra editar o nick reavançaria sozinho pro Formato de novo.
    if _session.step == core.STEP_IDENTITY and _session.identity is None:
        saved = _load_saved_profile()
        if saved:
            match_config_path = ROOT / "docker" / "match_config.spike.json"
            _session.set_identity(core.resolve_setup_identity(saved, match_config_path))
    if _session.step not in (core.STEP_IDENTITY, core.STEP_FORMAT):
        return _redirect_for_step()
    player = _session.identity.name if _session.identity else (_load_saved_profile() or "")
    return _render(
        request, "setup.html", formats=["bo1", "bo3", "bo5"],
        player=player,
        chosen_fmt=_session.format or "bo1",
        chosen_team_size=_session.team_size or 5,
    )


@app.post("/setup")
def setup_submit(player: str = Form(""), fmt: str = Form("bo1"), team_size: str = Form("5")):
    if _session.step not in (core.STEP_IDENTITY, core.STEP_FORMAT):
        return _redirect_for_step()

    # Perfil salvo (D8) já resolveu a identidade antes de chegar aqui (via
    # index()) — o form ainda manda o campo "player", mas só chamamos
    # set_identity de novo se o passo Jogador ainda estiver pendente
    # (set_identity() explode se chamado fora do passo STEP_IDENTITY).
    if _session.step == core.STEP_IDENTITY:
        player = player.strip()
        if not player:
            _set_flash("Informe um nick ou SteamID64.")
            return RedirectResponse("/setup", status_code=HTTP_303_SEE_OTHER)
        match_config_path = ROOT / "docker" / "match_config.spike.json"
        identity = core.resolve_setup_identity(player, match_config_path)
        try:
            _session.set_identity(identity)
        except core.WizardError as exc:
            _set_flash(str(exc))
            return RedirectResponse("/setup", status_code=HTTP_303_SEE_OTHER)
        _save_profile(player)

    if not team_size.isdigit() or int(team_size) < 1:
        _set_flash("Jogadores por time precisa ser um número >= 1.")
        return RedirectResponse("/setup", status_code=HTTP_303_SEE_OTHER)
    team_size_i = int(team_size)

    max_size = core.max_team_size(ROOT / COMPOSE_FILE)
    if max_size is not None and team_size_i > max_size:
        _set_flash(
            f"team_size {team_size_i} excede o máximo suportado pelo "
            f"CS2_MAXPLAYERS atual ({max_size})."
        )
        return RedirectResponse("/setup", status_code=HTTP_303_SEE_OTHER)

    try:
        _session.set_format(fmt, team_size_i)
    except core.WizardError as exc:
        _set_flash(str(exc))
        return RedirectResponse("/setup", status_code=HTTP_303_SEE_OTHER)
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


# --------------------------------------------------------------------------- #
# Lineups (F4.2, docs/features/M4-seletor.md) — dois painéis com pool de
# nomes compartilhado. _lineup_slots é o estado de UI (vagas em progresso);
# só vira parte do WizardSession em /lineups/confirm.
# --------------------------------------------------------------------------- #

def _reset_lineup_slots() -> None:
    """(Re)dimensiona os slots pro team_size atual, um lado de cada vez —
    um lado pode estar "competitivo" (anônimo) enquanto o outro tem lineup
    real. Se a sessão já tem uma lineup confirmada do tamanho certo pra um
    lado — por ex. voltando de Mapas pra Lineups — repopula esse lado em
    vez de esvaziar, pra não perder a escolha só por ter ido ver o resumo e
    voltado. `_competitive` não é tocado aqui de propósito: só quem liga/
    desliga é uma ação explícita do usuário (select-team/select-competitive/
    pick), então ele sobrevive ao ir-e-voltar igual o resto."""
    global _browsing
    if len(_session.my_lineup) == _session.team_size - 1:
        _lineup_slots["mine"] = list(_session.my_lineup)
        _competitive["mine"] = False
    else:
        _lineup_slots["mine"] = [None] * (_session.team_size - 1)
    if len(_session.enemy_lineup) == _session.team_size:
        _lineup_slots["enemy"] = list(_session.enemy_lineup)
        _competitive["enemy"] = False
    else:
        _lineup_slots["enemy"] = [None] * _session.team_size
    _browsing = None


def _used_elsewhere(side: str, slot: int) -> set:
    """Nomes já ocupando alguma vaga, em QUALQUER lado, exceto a própria
    vaga sendo editada agora — é o pool compartilhado (SPEC.md §10 restrição
    1: nomes são únicos no servidor inteiro, sem distinção de time)."""
    used = set()
    for s, slots in _lineup_slots.items():
        for i, name in enumerate(slots):
            if name and (s, i) != (side, slot):
                used.add(name)
    return used


def _lineups_context(request: Request) -> dict:
    all_cards = _get_profile_cards()
    human_name = _session.identity.name if _session.identity else None

    browse_results = None
    if _browsing is not None:
        side, slot = _browsing
        q = request.query_params.get("q", "")
        team_id = request.query_params.get("team_id", "")
        role = request.query_params.get("role", "")
        weapon = request.query_params.get("weapon", "")
        excluded = _used_elsewhere(side, slot) | ({human_name} if human_name else set())
        browse_results = [
            c for c in roster.search_profiles(all_cards, query=q, team_id=team_id, role=role, weapon=weapon)
            if c.name not in excluded
        ]

    valid_teams = _ROSTERS.valid_teams(c.name for c in all_cards) if all_cards else []
    selected_team_id = {
        side: (getattr(_ROSTERS.identify_team([n for n in _lineup_slots[side] if n]), "id", None))
        for side in ("mine", "enemy")
    }
    team_logo_asset = {team.id: roster.team_logo_asset(team.id) for team in valid_teams}

    return dict(
        mine_slots=_lineup_slots["mine"],
        enemy_slots=_lineup_slots["enemy"],
        browsing=_browsing,
        browse_results=browse_results,
        card_by_name={c.name: c for c in all_cards},
        teams=valid_teams,
        selected_team_id=selected_team_id,
        team_logo_asset=team_logo_asset,
        competitive=_competitive,
        roles=sorted({c.style.role for c in all_cards}),
        weapons=sorted({c.style.weapon for c in all_cards}),
        human_name=human_name,
        human_stats=stats.human_quick_summary(ROOT / DB_PATH),
        query_params=dict(request.query_params),
    )


@app.get("/lineups")
def lineups_screen(request: Request):
    if _session.step != core.STEP_LINEUPS:
        return _redirect_for_step()
    if len(_lineup_slots["mine"]) != _session.team_size - 1 \
            or len(_lineup_slots["enemy"]) != _session.team_size:
        _reset_lineup_slots()
    return _render(request, "lineups.html", **_lineups_context(request))


@app.get("/lineups/browse")
def lineups_browse(request: Request, side: str, slot: int):
    global _browsing
    if _session.step != core.STEP_LINEUPS:
        return _redirect_for_step()
    if not _valid_slot(side, slot):
        _set_flash("Vaga inválida — tente de novo.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    _browsing = (side, slot)
    return _render(request, "lineups.html", **_lineups_context(request))


@app.post("/lineups/browse/cancel")
def lineups_browse_cancel():
    """Fecha o modal de troca (item 4, 2026-09-20) sem escolher ninguém."""
    global _browsing
    _browsing = None
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


def _valid_slot(side: str, slot: int) -> bool:
    """Guarda contra (side, slot) fora do intervalo — nunca deveria acontecer
    vindo da UI (o slot embutido no form é sempre o da vaga sendo editada,
    não o índice do card na lista de resultados — bug corrigido em
    lineups.html), mas uma request malformada/repetida não pode virar
    IndexError -> 500."""
    return side in _lineup_slots and 0 <= slot < len(_lineup_slots[side])


@app.post("/lineups/pick")
def lineups_pick(side: str = Form(...), slot: int = Form(...), name: str = Form(...)):
    global _browsing
    if not _valid_slot(side, slot):
        _set_flash("Vaga inválida — tente escolher o perfil de novo.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    human_name = _session.identity.name if _session.identity else None
    if name == human_name:
        _set_flash(f"Seu nick ({name!r}) não pode ser escolhido — já é você.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    if name in _used_elsewhere(side, slot):
        _set_flash(f"{name!r} já está escolhido em outra vaga — nomes são únicos no servidor inteiro.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    _lineup_slots[side][slot] = name
    _competitive[side] = False  # escolher perfil manualmente sai do modo competitivo
    _browsing = None
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


@app.post("/lineups/clear")
def lineups_clear(side: str = Form(...), slot: int = Form(...)):
    if not _valid_slot(side, slot):
        _set_flash("Vaga inválida — tente de novo.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    _lineup_slots[side][slot] = None
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


def _apply_random(side: str) -> bool:
    """Sorteia perfis pras vagas VAZIAS de `side`, sem colisão. Retorna True
    se sobrou vaga sem perfil disponível pro sorteio."""
    human_name = _session.identity.name if _session.identity else None
    all_cards = _get_profile_cards()
    slots = _lineup_slots[side]
    empty_indexes = [i for i, v in enumerate(slots) if v is None]
    shortage = False
    for i in empty_indexes:
        used = _used_elsewhere(side, i) | ({human_name} if human_name else set())
        available = [c.name for c in all_cards if c.name not in used and c.name not in slots]
        if not available:
            shortage = True
            break
        slots[i] = random.choice(available)
    return shortage


def _apply_random_full(side: str) -> bool:
    """"Gerar lineup aleatória" (item 5, 2026-09-20): zera `side` inteiro e
    sorteia de novo — diferente de _apply_random puro, que só preenche o que
    estava vazio. Substitui, não soma."""
    _lineup_slots[side] = [None] * len(_lineup_slots[side])
    return _apply_random(side)


def _load_team_into_side(side: str, team_id: str) -> Optional[List[str]]:
    """Grade de logos (F4.2, item 1 do redesenho pedido em 2026-09-20):
    SUBSTITUI a lineup inteira de `side` pelo roster `team_id` — diferente
    de _apply_preset, que só preenche vaga vazia. É a troca de time pelo
    clique no logo: escolher outro time troca a lineup inteira, não soma. A
    vaga cujo jogador colide com o outro lado ou com o nick do humano fica
    de fora (retornada como conflito) em vez de resolver sozinho em
    silêncio. Retorna None se o team_id não existe."""
    team = _ROSTERS.get(team_id)
    if team is None:
        return None
    human_name = _session.identity.name if _session.identity else None
    other_side = "enemy" if side == "mine" else "mine"
    other_used = {n for n in _lineup_slots[other_side] if n}
    needed = len(_lineup_slots[side])
    new_slots: List[Optional[str]] = [None] * needed
    conflicts = []
    for i, player in enumerate(team.players[:needed]):
        if player == human_name or player in other_used:
            conflicts.append(player)
            continue
        new_slots[i] = player
    if len(team.players) < needed:
        conflicts.extend(["(faltam jogadores no roster)"] * (needed - len(team.players)))
    _lineup_slots[side] = new_slots
    _competitive[side] = False
    return conflicts


@app.post("/lineups/select-team")
def lineups_select_team(side: str = Form(...), team_id: str = Form(...)):
    conflicts = _load_team_into_side(side, team_id)
    if conflicts is None:
        _set_flash(f"Time {team_id!r} não existe no catálogo.")
    elif conflicts:
        team = _ROSTERS.get(team_id)
        _set_flash(
            f"{team.display_name} carregado, mas ficou de fora: {', '.join(conflicts)} "
            "(colisão com a outra lineup ou com seu nick, ou o time tem menos jogadores que vagas)."
        )
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


@app.post("/lineups/select-competitive")
def lineups_select_competitive(side: str = Form(...)):
    """"Competitivo": trava a edição manual desse lado — na hora de jogar,
    cada vaga recebe um bot anônimo de verdade (perfil sorteado pelo
    próprio engine, não um pro nomeado escolhido aqui)."""
    if side not in _lineup_slots:
        _set_flash(f"Lado {side!r} inválido.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    _lineup_slots[side] = [None] * len(_lineup_slots[side])
    _competitive[side] = True
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


@app.post("/lineups/random-team")
def lineups_random_team(side: str = Form(...)):
    """"Sortear 1 time" (item 5, 2026-09-20): mesmo caminho de código do
    clique num logo (_load_team_into_side, substitui a lineup inteira), só
    que o time é sorteado em vez de escolhido — devolve a imprevisibilidade
    que os presets antigos tinham. "Competitivo" nunca entra no sorteio."""
    team_ids = [t.id for t in _ROSTERS.valid_teams(c.name for c in _get_profile_cards())]
    if not team_ids:
        _set_flash("Nenhum time disponível pro sorteio ainda.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    conflicts = _load_team_into_side(side, random.choice(team_ids))
    if conflicts:
        _set_flash(
            f"Time sorteado, mas ficou de fora: {', '.join(conflicts)} "
            "(colisão com a outra lineup ou com seu nick)."
        )
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


@app.post("/lineups/random-lineup")
def lineups_random_lineup(side: str = Form(...)):
    """"Gerar lineup aleatória" (item 5, 2026-09-20): substitui a lineup
    inteira de `side` por jogadores individuais sorteados."""
    if side not in _lineup_slots:
        _set_flash(f"Lado {side!r} inválido.")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    _competitive[side] = False
    if _apply_random_full(side):
        _set_flash("Não sobrou perfil disponível pro sorteio — preencha o resto na mão.")
    return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)


@app.post("/lineups/confirm")
def lineups_confirm():
    # "Competitivo" (item 1, grade de logos) = esse lado vira anônimo — não
    # precisa (e não pode) estar preenchido, session.set_lineups aceita uma
    # lista vazia como "sem lineup pra esse lado".
    mine = [] if _competitive["mine"] else _lineup_slots["mine"]
    enemy = [] if _competitive["enemy"] else _lineup_slots["enemy"]
    if (not _competitive["mine"] and None in mine) or (not _competitive["enemy"] and None in enemy):
        _set_flash("Preencha todas as vagas antes de continuar (ou marque 'Competitivo').")
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    try:
        if _competitive["mine"] and _competitive["enemy"]:
            _session.skip_lineups()
        else:
            _session.set_lineups(my_lineup=list(mine), enemy_lineup=list(enemy))
    except core.WizardError as exc:
        _set_flash(str(exc))
        return RedirectResponse("/lineups", status_code=HTTP_303_SEE_OTHER)
    _reset_lineup_slots()
    return RedirectResponse("/maps", status_code=HTTP_303_SEE_OTHER)


# --------------------------------------------------------------------------- #
# Mapas — escolha direta ou veto
# --------------------------------------------------------------------------- #

@app.get("/maps")
def maps_form(request: Request):
    if _session.step != core.STEP_MAPS:
        return _redirect_for_step()
    if _session.veto_active:
        return RedirectResponse("/veto", status_code=HTTP_303_SEE_OTHER)
    return _render(
        request, "maps.html",
        pool=core.DEFAULT_MAP_POOL,
        selected=_direct_selection,
        maps_needed=core.MAPS_PER_FORMAT[_session.format],
        # "Escolher mapa(s)" abre num modal (item 7, 2026-09-20) em vez de
        # navegar pra outra tela — o próprio /maps decide se mostra o
        # overlay via query param.
        open_direct=request.query_params.get("open") == "direct",
        map_bg={m: stats.map_bg_path(m) for m in core.DEFAULT_MAP_POOL},
        map_label={m: stats.map_label(m) for m in core.DEFAULT_MAP_POOL},
    )


@app.post("/maps/toggle")
def maps_toggle(map_name: str = Form(...)):
    if map_name in _direct_selection:
        _direct_selection.remove(map_name)
    else:
        _direct_selection.append(map_name)
    # Mantém o modal de escolha direta aberto (item 7, 2026-09-20) — sem
    # isso, cada clique num mapa fechava o overlay e voltava pros 2 cards.
    return RedirectResponse("/maps?open=direct", status_code=HTTP_303_SEE_OTHER)


@app.post("/maps/confirm")
def maps_confirm():
    try:
        _session.choose_maps_direct(list(_direct_selection))
    except core.WizardError as exc:
        _set_flash(str(exc))
        return RedirectResponse("/maps?open=direct", status_code=HTTP_303_SEE_OTHER)
    _direct_selection.clear()
    return RedirectResponse("/sides", status_code=HTTP_303_SEE_OTHER)


@app.post("/maps/veto/start")
def veto_start():
    _direct_selection.clear()
    _session.start_veto()
    return RedirectResponse("/veto", status_code=HTTP_303_SEE_OTHER)


# --------------------------------------------------------------------------- #
# Veto — sub-tela do passo Mapas
# --------------------------------------------------------------------------- #

def _veto_context() -> dict:
    return dict(
        veto_step=_session.current_veto_step(),
        pool=_session.map_pool,
        history=_session.veto_history,
        # Botões de mapa com imagem de fundo (item 7, 2026-09-20) — mesmo
        # tratamento visual da escolha direta.
        map_bg={m: stats.map_bg_path(m) for m in _session.map_pool},
        map_label={m: stats.map_label(m) for m in _session.map_pool},
    )


@app.get("/veto")
def veto_screen(request: Request):
    if _session.step != core.STEP_MAPS or not _session.veto_active:
        return _redirect_for_step()
    return _render(request, "veto.html", **_veto_context())


@app.post("/veto/pick")
def veto_pick(map_name: str = Form(...)):
    try:
        _session.resolve_veto_step(map_name)
    except core.WizardError as exc:
        _set_flash(str(exc))
        return RedirectResponse("/veto", status_code=HTTP_303_SEE_OTHER)
    if _session.step != core.STEP_MAPS:
        return RedirectResponse("/sides", status_code=HTTP_303_SEE_OTHER)
    return RedirectResponse("/veto", status_code=HTTP_303_SEE_OTHER)


@app.get("/veto/bot-turn")
def veto_bot_turn(request: Request):
    """Chamado via HTMX (hx-trigger="load delay:...") quando o passo atual é
    do bot — resolve o turno server-side e devolve o fragmento atualizado,
    ou redireciona pra Lados se o veto acabou de concluir."""
    if _session.step != core.STEP_MAPS or not _session.veto_active:
        return _redirect_for_step()
    step = _session.current_veto_step()
    if step is not None and step.actor == "bot":
        choice = core.resolve_bot_step(_session.map_pool)
        _session.resolve_veto_step(choice)
    if _session.step != core.STEP_MAPS:
        return Response(status_code=200, headers={"HX-Redirect": "/sides"})
    # Só o fragmento aqui, NUNCA o "veto.html" completo — é um swap de
    # #veto-box via HTMX (hx-swap="outerHTML"), não uma navegação de página;
    # devolver o documento inteiro (com <html>/<head>/<body> de novo)
    # duplicaria a página dentro dela mesma.
    return templates.TemplateResponse(request, "_veto_fragment.html", {
        **_veto_context(),
        "error": _pop_flash(),
    })


# --------------------------------------------------------------------------- #
# Lados
# --------------------------------------------------------------------------- #

@app.get("/sides")
def sides_form(request: Request):
    if _session.step != core.STEP_SIDES:
        return _redirect_for_step()
    map_name = _session.maps_in_order[_session.side_index]
    return _render(request, "sides.html", map_name=map_name)


@app.post("/sides")
def sides_submit(side: str = Form(...)):
    try:
        _session.set_side(side)
    except core.WizardError as exc:
        _set_flash(str(exc))
        return RedirectResponse("/sides", status_code=HTTP_303_SEE_OTHER)
    if _session.step == core.STEP_SUMMARY:
        return RedirectResponse("/summary", status_code=HTTP_303_SEE_OTHER)
    return RedirectResponse("/sides", status_code=HTTP_303_SEE_OTHER)


# --------------------------------------------------------------------------- #
# Resumo
# --------------------------------------------------------------------------- #

@app.get("/summary")
def summary_screen(request: Request):
    if _session.step != core.STEP_SUMMARY:
        return _redirect_for_step()
    return _render(request, "summary.html")


# --------------------------------------------------------------------------- #
# Voltar / recomeçar
# --------------------------------------------------------------------------- #

@app.post("/back")
def back():
    try:
        _session.back()
    except core.WizardError as exc:
        _set_flash(str(exc))
    else:
        _direct_selection.clear()
    return _redirect_for_step()


@app.post("/reset")
def reset():
    global _session
    _session = core.WizardSession()
    _direct_selection.clear()
    _lineup_slots["mine"] = []
    _lineup_slots["enemy"] = []
    _competitive["mine"] = False
    _competitive["enemy"] = False
    return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
