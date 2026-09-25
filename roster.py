#!/usr/bin/env python3
"""
CS2 Tracker — Roster
======================
Catálogo de times reais (F1.1, docs/features/M1-lineups-headless.md) — dado
versionado em data/rosters.json (schema em SPEC.md §7), validável contra os
perfis que o botprofile.vpk ativo do servidor realmente tem.

`players` guarda o nome do profile no VPK — imutável, é o que vai direto no
bot_add_ct/bot_add_t. `display_name` é o que a tela mostra. A separação
existe pra que trocar por nomes genéricos seja swap de arquivo, não refactor
(SPEC.md §9).

Uso (validação standalone, sem precisar do wizard nem do start_match.py):
    .venv\\Scripts\\python.exe roster.py --validate
    .venv\\Scripts\\python.exe roster.py --validate --container cs2-spike
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from config import CONTAINER_NAME, ROSTERS_FILE

ROOT = Path(__file__).resolve().parent

# Caminho do VPK dentro do container — o mesmo mount fixo pelo projeto
# (README.md "Bots: dificuldade e comportamento"; overrides/{Low,Medium,High}
# são as variantes disponíveis, mas só a copiada por cima deste caminho é a
# que o servidor de fato usa, via docker/pre.sh).
CONTAINER_VPK_PATH = "/home/steam/cs2-dedicated/game/csgo/overrides/botprofile.vpk"

# Formato de cada entrada do botprofile.db embutido no VPK:
# "<Templates+Separados+Por+Mais>  \"<NomeDoPerfil>\"" seguido de atributos e
# "End" — ver docs/SPEC.md §10 (Passo 0) pra como isso foi descoberto. O
# grupo 1 (o "template") é sempre 3 partes fixas — reação+arma+personalidade
# — confirmado varrendo as 64 combinações distintas dos 1709 perfis do VPK
# ativo (nenhuma delas tem 2 nem 4 partes). read_vpk_profile_templates usa
# isso pra derivar função/arma/estilo sem nenhum texto escrito à mão por
# jogador (F4.1, docs/features/M4-seletor.md).
_PROFILE_ENTRY_RE = re.compile(rb'([A-Za-z0-9_+\-]+)\s+"([^"]+)"\s*\r?\n')

# As 3 partes do template, na ordem em que sempre aparecem — ver comentário
# acima. Cada dicionário só cobre os tokens observados nos 1709 perfis do
# VPK ativo em 2026-09-20; um token novo (VPK atualizado) cai no fallback
# "?" em vez de quebrar a leitura de estilo.
_REACTION_LABELS = {
    "ProTop": "reação de elite",
    "ProFast": "reação rápida",
    "ProSteady": "reação estável",
    "ProPrecise": "precisão antes de velocidade",
    "ProSlow": "reação mais lenta",
    "RankRifler": "reação mediana",
    "RankDuelist": "reação mediana",
    "RankOthers": "reação mediana",
}
_ROLE_LABELS = {
    "RiflePro": "Rifle",
    "SniperPro": "Sniper",
    "SniperPure": "Sniper",
    "Fastshot": "Rifle (fastshot)",
    "Camper": "Lurker",
    "Rusher": "Entry",
    "Duelist": "Entry/Duelista",
    "Scoper": "Sniper posicional",
}
_WEAPON_LABELS = {
    "RiflePro": "Rifle",
    "SniperPro": "AWP",
    "SniperPure": "AWP",
    "Fastshot": "Rifle",
    "Camper": "Rifle",
    "Rusher": "Rifle",
    "Duelist": "Rifle",
    "Scoper": "AWP",
}
_PERSONALITY_LABELS = {
    "RiflePersonality": "equilibrado",
    "SniperPersonality": "paciente",
    "FreemanPersonality": "freelancer",
    "CamperPersonality": "posicional",
    "RusherPersonality": "agressivo",
    "FastshotPersonality": "reflexo rápido",
    "ScoperPersonality": "sniper posicional",
}


@dataclass(frozen=True)
class ProfileStyle:
    """Leitura de estilo derivada do template do profile (SPEC.md §6: "cards
    com... uma leitura honesta do estilo derivada do template do profile,
    ex.: 'AWPer, reação rápida, agressivo'"). Nunca escrita à mão por
    jogador — os 4 campos vêm só dos dicionários acima aplicados às 3 partes
    do template."""
    template: str
    role: str
    weapon: str
    reaction: str
    personality: str

    @property
    def summary(self) -> str:
        return f"{self.role}, {self.reaction}, {self.personality}"


def derive_style(template: str) -> ProfileStyle:
    parts = template.split("+")
    reaction_tok = parts[0] if len(parts) > 0 else ""
    role_tok = parts[1] if len(parts) > 1 else ""
    personality_tok = parts[2] if len(parts) > 2 else ""
    return ProfileStyle(
        template=template,
        role=_ROLE_LABELS.get(role_tok, "?"),
        weapon=_WEAPON_LABELS.get(role_tok, "?"),
        reaction=_REACTION_LABELS.get(reaction_tok, "?"),
        personality=_PERSONALITY_LABELS.get(personality_tok, "?"),
    )


@dataclass(frozen=True)
class ProfileCard:
    """Um jogador pronto pra mostrar no seletor de lineups (F4.2) — nome,
    time de origem e a leitura de estilo (F4.1)."""
    name: str
    team_id: str
    team_display_name: str
    team_logo: str
    style: ProfileStyle


@dataclass(frozen=True)
class Team:
    id: str
    display_name: str
    logo: str
    players: List[str]
    # Dados de veto reais e curados à mão (SPEC.md §7) — opcional; hoje só a
    # FURIA tem números (é o exemplo da spec). Times sem isso continuam
    # jogáveis (escolha direta ou veto uniforme), só não pesam a favor de
    # nenhum mapa específico no veto do adversário.
    veto: Optional[Dict[str, dict]] = None


# Arquivo real em static/ pra cada time que já tem logo pronto no projeto
# (mesma pasta usada por home.py/report.py — ver stats.py map_icon_path pro
# padrão). Time sem entrada aqui cai no selo de texto (ver web/templates/
# lineups.html) — nem todo time do catálogo (data/rosters.json) tem logo
# baixado ainda.
TEAM_LOGO_FILES: Dict[str, str] = {
    "furia": "furia.png",
    "vitality": "vitality.png",
    "spirit": "spirit.png",
    "mouz": "mouz.svg",
    "faze": "faze.png",
    "mibr": "mibr.png",
    "falcons": "falcons.png",
    "legacy": "legacy.png",
    "natus_vincere": "navi.svg",
    "g2": "g2.webp",
}


def team_logo_asset(team_id: str) -> Optional[str]:
    """Nome do arquivo em static/ pro logo do time, ou None se não tiver
    (cai no selo de texto)."""
    return TEAM_LOGO_FILES.get(team_id)


@dataclass(frozen=True)
class RosterCatalog:
    snapshot_date: str
    map_pool_version: str
    teams: List[Team] = field(default_factory=list)

    def get(self, team_id: str) -> Optional[Team]:
        return next((t for t in self.teams if t.id == team_id), None)

    def identify_team(self, players: Iterable[str]) -> Optional[Team]:
        """Time cujo elenco bate exatamente com `players` (ordem não importa)
        — usado pra saber se uma lineup escolhida É um roster do catálogo ou
        uma montagem manual/mista (F4.4, docs/features/M4-seletor.md: nome e
        logo do time no placar só fazem sentido quando dá pra identificar
        um time de origem; senão a lineup usa rótulo neutro)."""
        wanted = set(players)
        if not wanted:
            return None
        return next((t for t in self.teams if set(t.players) == wanted), None)

    def missing_profiles(self, team: Team, available_profiles: Iterable[str]) -> List[str]:
        """Profiles do time que NÃO existem em available_profiles, na ordem
        original do roster."""
        available = set(available_profiles)
        return [p for p in team.players if p not in available]

    def validate_against_server(self, available_profiles: Iterable[str]) -> Dict[str, List[str]]:
        """{team_id: [profiles ausentes]} — só entra no dict quem tem pelo
        menos um profile faltando. Dict vazio = catálogo inteiro válido."""
        available = set(available_profiles)
        result = {}
        for team in self.teams:
            missing = self.missing_profiles(team, available)
            if missing:
                result[team.id] = missing
        return result

    def valid_teams(self, available_profiles: Iterable[str]) -> List[Team]:
        """Só os times com os 5 profiles presentes no VPK ativo — um time
        com qualquer perfil ausente some do catálogo em vez de falhar no
        meio do bot_add (critério de aceite da F1.2)."""
        available = set(available_profiles)
        return [t for t in self.teams if not self.missing_profiles(t, available)]


def load_rosters(path: Path = None) -> RosterCatalog:
    path = path or (ROOT / ROSTERS_FILE)
    data = json.loads(path.read_text(encoding="utf-8"))
    teams = [
        Team(
            id=t["id"],
            display_name=t["display_name"],
            logo=t["logo"],
            players=list(t["players"]),
            veto=t.get("veto"),
        )
        for t in data["teams"]
    ]
    return RosterCatalog(
        snapshot_date=data["snapshot_date"],
        map_pool_version=data["map_pool_version"],
        teams=teams,
    )


def read_vpk_profile_templates(vpk_path: Path) -> Dict[str, str]:
    """
    Extrai {nome_do_profile: template} do botprofile.db embutido num
    botprofile.vpk — mesma técnica usada pra diagnosticar o Passo 0
    (docs/SPEC.md §10): o VPK é um pacote real (assinatura 0x55aa1234), mas o
    conteúdo do botprofile.db é texto puro, então dá pra extrair direto dos
    bytes com regex, sem precisar de um parser de VPK completo.
    """
    data = Path(vpk_path).read_bytes()
    return {
        name.decode("latin1"): template.decode("latin1")
        for template, name in _PROFILE_ENTRY_RE.findall(data)
    }


def read_vpk_profile_names(vpk_path: Path) -> Set[str]:
    """Só os nomes — casca fina sobre read_vpk_profile_templates pra quem
    (F1.1) só precisa validar existência, não a leitura de estilo (F4.1)."""
    return set(read_vpk_profile_templates(vpk_path).keys())


def read_container_profile_templates(container_name: str = CONTAINER_NAME,
                                      vpk_path: str = CONTAINER_VPK_PATH) -> Dict[str, str]:
    """`docker cp` o botprofile.vpk ativo de dentro do container pra um
    arquivo temporário e lê de lá — pra validar/derivar estilo contra o que
    o servidor REALMENTE tem carregado, não contra uma cópia local que pode
    estar desatualizada."""
    with tempfile.TemporaryDirectory() as tmp:
        local_copy = Path(tmp) / "botprofile.vpk"
        subprocess.run(
            ["docker", "cp", f"{container_name}:{vpk_path}", str(local_copy)],
            check=True, capture_output=True, text=True, timeout=10,
        )
        return read_vpk_profile_templates(local_copy)


def read_container_profile_names(container_name: str = CONTAINER_NAME,
                                  vpk_path: str = CONTAINER_VPK_PATH) -> Set[str]:
    return set(read_container_profile_templates(container_name, vpk_path).keys())


def build_profile_catalog(catalog: RosterCatalog, templates: Dict[str, str]) -> List[ProfileCard]:
    """
    Um ProfileCard por jogador dos times válidos (F1.1 valid_teams) — a
    "API do catálogo" da F4.1. Profile sem template no VPK ativo não devia
    acontecer aqui (o time já teria sido filtrado por valid_teams), mas cai
    num ProfileStyle "?" em vez de KeyError se acontecer.
    """
    cards = []
    for team in catalog.valid_teams(templates.keys()):
        for player in team.players:
            template = templates.get(player, "")
            cards.append(ProfileCard(
                name=player,
                team_id=team.id,
                team_display_name=team.display_name,
                team_logo=team.logo,
                style=derive_style(template),
            ))
    return cards


def search_profiles(cards: Iterable[ProfileCard], *, query: str = "", team_id: str = "",
                     role: str = "", weapon: str = "") -> List[ProfileCard]:
    """Busca por texto (nome ou time) + filtro por time/função/arma — tudo
    resolvido aqui (servidor), o front só manda os parâmetros (F4.1)."""
    query = query.strip().lower()
    result = []
    for card in cards:
        if query and query not in card.name.lower() and query not in card.team_display_name.lower():
            continue
        if team_id and card.team_id != team_id:
            continue
        if role and card.style.role != role:
            continue
        if weapon and card.style.weapon != weapon:
            continue
        result.append(card)
    return result


def main():
    parser = argparse.ArgumentParser(description="Catálogo de rosters — carrega e valida data/rosters.json")
    parser.add_argument("--rosters-file", default=None,
                         help=f"Default: {ROSTERS_FILE} (raiz do repo)")
    parser.add_argument("--validate", action="store_true",
                         help="Compara o catálogo contra o botprofile.vpk ativo do container "
                              "(docker cp + leitura local) e lista times com perfil ausente")
    parser.add_argument("--container", default=CONTAINER_NAME,
                         help="Container de onde ler o botprofile.vpk ativo (--validate)")
    args = parser.parse_args()

    rosters_path = Path(args.rosters_file) if args.rosters_file else (ROOT / ROSTERS_FILE)
    catalog = load_rosters(rosters_path)
    print(f"{len(catalog.teams)} time(s) carregado(s) de {rosters_path.name} "
          f"(snapshot {catalog.snapshot_date}, map pool {catalog.map_pool_version}):")
    for team in catalog.teams:
        veto_tag = " [veto]" if team.veto else ""
        print(f"  - {team.id}: {team.display_name}{veto_tag} — {', '.join(team.players)}")

    if not args.validate:
        return

    print(f"\nLendo botprofile.vpk ativo do container '{args.container}'...")
    try:
        available = read_container_profile_names(args.container)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"[ERRO] Não consegui ler o VPK do container: {exc.stderr or exc}")
    print(f"{len(available)} profile(s) encontrado(s) no VPK ativo.\n")

    missing = catalog.validate_against_server(available)
    if not missing:
        print("Catálogo inteiro validado — todos os times têm os 5 perfis no VPK ativo.")
        return

    print(f"{len(missing)} time(s) com perfil ausente (somem do catálogo até corrigir):")
    for team_id, names in missing.items():
        team = catalog.get(team_id)
        print(f"  - {team_id} ({team.display_name}): {', '.join(names)}")


if __name__ == "__main__":
    main()
