#!/usr/bin/env python3
"""
Web dourado (card H1.7): o app web (`web.app:app`) contra dados de fixture,
para o dev e o QA verem a web sem tocar no jogo do Victor.

  --check      roda os pedidos dourados em processo (TestClient), sem abrir
               porta; sai 0 se todos batem com o esperado, 1 se algum não bate
  (sem flag)   sobe o uvicorn em 127.0.0.1:8010 (--porta N; a 8000 é recusada,
               é a do Victor)
  --pasta D    onde criar o banco e o profile.json de fixture (padrão: uma
               pasta temporária nova)

Fica de fora: o banco real (`DB_PATH` aponta para um banco novo, com o
schema do parser.init_db e sem partida), o `data/profile.json` (`PROFILE_PATH`
na pasta da fixture) e o docker cp: o `_get_profile_cards` do app chama
`roster.read_container_profile_templates`, trocada aqui, antes de qualquer
pedido, pela leitura de um botprofile.vpk de fixture com o parser de verdade.
Por garantia, `subprocess.run` e `Popen` levantam erro no processo inteiro.
Nada em web/, roster.py ou no caminho de jogo muda: só troca de atributo em
tempo de execução. No navegador: configuração `web-golden` do launch.json.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PORTA_PADRAO = 8010
PORTA_DO_VICTOR = 8000

# O catálogo da fixture: dois times inteiros do data/rosters.json (FURIA e
# Vitality), cada perfil com um template de 3 partes no formato do VPK. A
# Natus Vincere fica de fora de propósito: time com perfil ausente some do
# catálogo (F1.1), e o dourado confere que sumiu.
CATALOGO_FIXTURE = {
    "KSCERATO": "ProTop+RiflePro+RiflePersonality",
    "yuurih": "ProFast+Rusher+RusherPersonality",
    "FalleN": "ProSteady+SniperPro+SniperPersonality",
    "molodoy": "ProPrecise+Scoper+ScoperPersonality",
    "YEKINDAR": "ProFast+Duelist+FreemanPersonality",
    "ZywOo": "ProTop+SniperPure+SniperPersonality",
    "mezii": "ProSteady+Camper+CamperPersonality",
    "flameZ": "ProFast+Rusher+RusherPersonality",
    "apEX": "RankRifler+RiflePro+RiflePersonality",
    "ropz": "ProPrecise+Fastshot+FastshotPersonality",
}

# Os pedidos dourados: (método, caminho, formulário, caminho final esperado,
# textos que precisam estar na resposta, textos que não podem estar). Os
# textos são escritos à mão a partir dos templates, não recalculados pelo app.
DOURADO = [
    ("GET", "/", None, "/",
     ["Escolha um lado e entre no servidor."], ["Quem vai jogar"]),
    ("GET", "/setup", None, "/setup",
     ["Quem vai jogar"], []),
    ("POST", "/setup", {"player": "golden", "fmt": "bo1", "team_size": "5"}, "/lineups",
     ['title="FURIA"', 'title="Vitality"'], ['title="Natus Vincere"']),
    ("GET", "/lineups/browse?side=enemy&slot=0", None, "/lineups/browse",
     ["FURIA — Rifle, reação de elite, equilibrado",
      "Vitality — Sniper, reação de elite, paciente",
      "Vitality — Rifle, reação mediana, equilibrado"],
     ["w0nderful", "Nenhum perfil disponível"]),
]


class ProcessoProibido(RuntimeError):
    """O web dourado nunca roda processo (docker cp incluído)."""


def _sem_processo(*args, **kwargs):
    raise ProcessoProibido(f"web_golden não roda processo: {args[:1]!r}")


def escrever_vpk_fixture(destino: Path, catalogo: dict = CATALOGO_FIXTURE) -> Path:
    """Um botprofile.vpk mínimo: a assinatura de VPK e as entradas
    `<template>  "<perfil>"` que o roster lê dos bytes (roster.py)."""
    corpo = b"".join(f'{template}  "{nome}"\n'.encode("latin1") + b"\tEnd\n"
                     for nome, template in catalogo.items())
    # A quebra depois da assinatura importa: o 0x34 é o "4" do ASCII e,
    # colado, entraria no template do primeiro perfil.
    destino.write_bytes(b"\x34\x12\xaa\x55\n" + corpo)
    return destino


def montar_app(pasta: Path, trocar: Callable = setattr):
    """Prepara a fixture em `pasta` e devolve o app web pronto para pedidos.

    `trocar` é o setattr usado em cada troca: os testes passam o
    monkeypatch.setattr, que desfaz tudo no fim do teste."""
    import parser as parser_demos
    import roster
    import web.app as webapp
    import wizard_core as core

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    banco = pasta / "cs2_tracker_fixture.db"
    parser_demos.init_db(str(banco)).close()
    vpk = escrever_vpk_fixture(pasta / "botprofile.vpk")

    trocar(subprocess, "run", _sem_processo)
    trocar(subprocess, "Popen", _sem_processo)
    trocar(roster, "read_container_profile_templates",
           lambda *a, **k: roster.read_vpk_profile_templates(vpk))
    trocar(webapp, "DB_PATH", str(banco))
    trocar(webapp, "PROFILE_PATH", pasta / "profile.json")
    # Estado do wizard do zero: o catálogo é relido com a troca acima.
    trocar(webapp, "_profile_cards_cache", None)
    trocar(webapp, "_session", core.WizardSession())
    trocar(webapp, "_direct_selection", [])
    trocar(webapp, "_lineup_slots", {"mine": [], "enemy": []})
    trocar(webapp, "_competitive", {"mine": False, "enemy": False})
    trocar(webapp, "_browsing", None)
    trocar(webapp, "_flash", None)
    return webapp.app


def verificar(app) -> List[str]:
    """Roda o DOURADO em processo; devolve as divergências (vazia = ok)."""
    from starlette.testclient import TestClient

    falhas = []
    cliente = TestClient(app, follow_redirects=True)
    for metodo, caminho, dados, final, presentes, ausentes in DOURADO:
        resposta = cliente.request(metodo, caminho, data=dados)
        rotulo = f"{metodo} {caminho}"
        if resposta.status_code != 200:
            falhas.append(f"{rotulo}: HTTP {resposta.status_code}")
            continue
        if resposta.url.path != final:
            falhas.append(f"{rotulo}: terminou em {resposta.url.path}, esperado {final}")
        falhas += [f"{rotulo}: falta {t!r}" for t in presentes if t not in resposta.text]
        falhas += [f"{rotulo}: sobra {t!r}" for t in ausentes if t in resposta.text]
    return falhas


def _servir(app, porta: int) -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=porta)


def ler_argumentos(argv: Optional[list] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="App web contra banco e catálogo de VPK de fixture, na 8010 (card H1.7).")
    ap.add_argument("--check", action="store_true",
                    help="roda os pedidos dourados em processo, sem abrir porta")
    ap.add_argument("--porta", type=int, default=PORTA_PADRAO,
                    help=f"porta do uvicorn (padrão {PORTA_PADRAO}; {PORTA_DO_VICTOR} é recusada)")
    ap.add_argument("--pasta", type=Path, default=None,
                    help="pasta da fixture (padrão: temporária nova)")
    return ap.parse_args(argv)


def main(argv: Optional[list] = None, servir: Callable = _servir) -> int:
    for fluxo in (sys.stdout, sys.stderr):  # em pipe o padrão seria cp1252
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    args = ler_argumentos(argv)
    if args.porta == PORTA_DO_VICTOR:
        print(f"[ERRO] a porta {PORTA_DO_VICTOR} é do Victor: use a {PORTA_PADRAO}.",
              file=sys.stderr)
        return 2
    pasta = args.pasta or Path(tempfile.mkdtemp(prefix="web_golden_"))
    app = montar_app(pasta)
    print(f"fixture em {pasta}")
    if args.check:
        falhas = verificar(app)
        for falha in falhas:
            print(f"DIVERGE  {falha}")
        resumo = "ok" if not falhas else f"{len(falhas)} divergência(s)"
        print(f"{len(DOURADO)} pedidos dourados: {resumo}")
        return 1 if falhas else 0
    print(f"web dourado em http://127.0.0.1:{args.porta}/ (Ctrl+C para parar)")
    servir(app, args.porta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
