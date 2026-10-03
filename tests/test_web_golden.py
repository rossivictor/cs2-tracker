#!/usr/bin/env python3
"""
Testes do web dourado (card H1.7, tools/web_golden.py): os pedidos dourados
batem com a fixture, nenhum processo roda (docker cp incluído, com um
gravador que prova ter dente), sem a injeção o dourado fica vermelho, a 8000
é recusada e o launch.json tem a web-golden que a guarda deixa subir.

Tudo em processo, com tmp_path e monkeypatch: o montar_app recebe o
monkeypatch.setattr, que desfaz cada troca no fim do teste (o web.app é o
mesmo módulo do test_web_wizard).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import roster  # noqa: E402
from tools import web_golden as wg  # noqa: E402


@pytest.fixture
def gravador(monkeypatch):
    """Troca subprocess.run e Popen por um gravador que registra e recusa."""
    chamadas = []

    def gravar(*args, **kwargs):
        chamadas.append(list(args[0]) if args else [])
        raise RuntimeError("processo proibido no teste")

    def instalar():
        monkeypatch.setattr(subprocess, "run", gravar)
        monkeypatch.setattr(subprocess, "Popen", gravar)
    instalar()
    return chamadas, instalar


def test_dourado_bate_com_a_fixture_sem_rodar_processo(tmp_path, monkeypatch, gravador):
    chamadas, instalar = gravador
    app = wg.montar_app(tmp_path, monkeypatch.setattr)
    with pytest.raises(wg.ProcessoProibido):  # a trava do próprio montar_app
        subprocess.run(["docker", "cp", "cs2-spike:/x", "y"])
    instalar()  # o gravador por cima da trava, para contar as chamadas
    assert wg.verificar(app) == []
    templates = roster.read_container_profile_templates("cs2-spike")
    assert templates["ZywOo"] == "ProTop+SniperPure+SniperPersonality"
    assert len(templates) == 10 and "w0nderful" not in templates
    assert chamadas == []
    # Perfil e banco na pasta da fixture, não no data/ nem no banco do repo.
    perfil = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert perfil == {"player": "golden"}
    import web.app as webapp
    assert Path(webapp.DB_PATH).parent == tmp_path


def test_o_gravador_pega_o_docker_cp_sem_a_injecao(gravador):
    chamadas, _ = gravador
    with pytest.raises(RuntimeError):
        roster.read_container_profile_templates("cs2-spike")
    assert chamadas[0][:2] == ["docker", "cp"]


def test_sem_a_injecao_o_dourado_fica_vermelho(tmp_path, monkeypatch, gravador):
    # Catálogo vazio é o que o app mostra quando o docker cp falha.
    app = wg.montar_app(tmp_path, monkeypatch.setattr)
    monkeypatch.setattr(roster, "read_container_profile_templates", lambda *a, **k: {})
    falhas = wg.verificar(app)
    assert "POST /setup: falta 'title=\"FURIA\"'" in falhas
    assert "GET /lineups/browse?side=enemy&slot=0: sobra 'Nenhum perfil disponível'" in falhas


def test_vpk_de_fixture_nao_cola_a_assinatura_no_primeiro_template(tmp_path):
    vpk = wg.escrever_vpk_fixture(tmp_path / "b.vpk", {"p1": "ProTop+RiflePro+RiflePersonality"})
    assert vpk.read_bytes().startswith(b"\x34\x12\xaa\x55")
    assert roster.read_vpk_profile_templates(vpk) == {"p1": "ProTop+RiflePro+RiflePersonality"}


@pytest.mark.parametrize("argv, codigo, servidas", [
    (["--porta", "8000"], 2, []),
    ([], 0, [8010]),
])
def test_8000_recusada_antes_de_montar_e_8010_por_padrao(tmp_path, monkeypatch, argv, codigo,
                                                         servidas):
    montadas, servidas_de_fato = [], []
    monkeypatch.setattr(wg, "montar_app", lambda pasta, *a: montadas.append(pasta))
    assert wg.main(argv + ["--pasta", str(tmp_path)],
                   servir=lambda app, porta: servidas_de_fato.append(porta)) == codigo
    assert servidas_de_fato == servidas
    assert montadas == ([tmp_path] if servidas else [])


@pytest.mark.parametrize("estragar, esperado", [(False, 0), (True, 1)])
def test_check_sai_0_ou_1_sem_abrir_porta(tmp_path, monkeypatch, capsys, estragar, esperado):
    real = wg.montar_app

    def montar(pasta):
        app = real(pasta, monkeypatch.setattr)
        if estragar:
            monkeypatch.setattr(roster, "read_container_profile_templates", lambda *a, **k: {})
        return app

    monkeypatch.setattr(wg, "montar_app", montar)
    servidas = []
    assert wg.main(["--check", "--pasta", str(tmp_path)],
                   servir=lambda app, porta: servidas.append(porta)) == esperado
    assert servidas == []
    assert ("4 pedidos dourados: ok" in capsys.readouterr().out) is (esperado == 0)


def test_launch_json_web_golden_na_8010_wizard_web_intacta_e_a_guarda_concorda(tmp_path):
    dados = json.loads((RAIZ / ".claude" / "launch.json").read_text(encoding="utf-8"))
    confs = {c["name"]: c for c in dados["configurations"]}
    assert confs["web-golden"] == {
        "name": "web-golden",
        "runtimeExecutable": "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe",
        "runtimeArgs": ["tools/web_golden.py", "--porta", "8010"], "port": 8010}
    assert confs["wizard-web"] == {
        "name": "wizard-web", "runtimeExecutable": ".venv\\Scripts\\python.exe",
        "runtimeArgs": ["-m", "uvicorn", "web.app:app", "--host", "127.0.0.1", "--port", "8000"],
        "port": 8000}

    sys.path.insert(0, str(RAIZ / "tools" / "hooks"))
    import guarda
    principal = tmp_path / "principal"
    (principal / ".claude").mkdir(parents=True)
    (principal / ".git").mkdir()
    (principal / ".claude" / "launch.json").write_text(json.dumps(dados), encoding="utf-8")
    for nome, esperado in (("web-golden", 0), ("wizard-web", 2)):
        evento = {"hook_event_name": "PreToolUse", "tool_input": {"name": nome},
                  "tool_name": "mcp__Claude_Browser__preview_start", "cwd": str(principal)}
        codigo, erro, _ = guarda.decidir(evento, principal=str(principal), preflight=lambda: 0,
                                         arquivo_env=str(tmp_path / "nao-existe.env"))
        assert codigo == esperado, (nome, erro)
