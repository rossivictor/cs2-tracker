#!/usr/bin/env python3
"""
Testes do hook de guarda (card B0.5): tools/hooks/guarda.py e
tools/hooks/pii.py.

Quase tudo chama guarda.decidir() direto, com um checkout principal falso
em tmp_path (pasta com .git diretório), uma worktree falsa dentro dele
(.claude/worktrees/agente, com .git arquivo) e o preflight injetado. Nenhum
docker, pip ou preflight de verdade roda, e o .env real nunca é lido: o
arquivo_env aponta pra tmp_path.

Três testes rodam o hook como processo, do jeito que o Claude Code roda: de
dentro de uma worktree git REAL (git worktree add --no-checkout num
diretório temporário, removida no fim), pelo comando exato do
.claude/settings.json no Git Bash, e medindo o tempo.
"""
import ast
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GUARDA = RAIZ / "tools" / "hooks" / "guarda.py"
SETTINGS = RAIZ / ".claude" / "settings.json"
PYTHON_DO_JOGO = "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe"
sys.path.insert(0, str(GUARDA.parent))

import guarda  # noqa: E402
import pii  # noqa: E402

SEGREDO = "segredo-do-rcon-7f3a9"
TOKEN = "TOKENFALSO0123456789ABCDEF"
# Casa o padrão de SteamID64 real, mas fica abaixo da base 76561197960265728:
# não existe conta com esse número, então nenhum dado de verdade entra no repo.
ID_REAL_FALSO = "76561190000000002"


@pytest.fixture
def repo(tmp_path):
    principal = tmp_path / "principal"
    (principal / ".git").mkdir(parents=True)
    wt = principal / ".claude" / "worktrees" / "agente"
    wt.mkdir(parents=True)
    (wt / ".git").write_text("gitdir: ../../../.git/worktrees/agente\n", encoding="utf-8")
    fora = tmp_path / "outro"
    fora.mkdir()
    return SimpleNamespace(principal=principal, wt=wt, fora=fora, tmp=tmp_path)


def _formatar(texto, repo):
    return (texto.replace("{P}", repo.principal.as_posix())
                 .replace("{PW}", str(repo.principal))
                 .replace("{F}", repo.fora.as_posix()))


def _decidir(repo, ferramenta, entrada, lugar="wt", preflight=lambda: 0, arquivo_env=None):
    cwd = {"wt": repo.wt, "principal": repo.principal, "fora": repo.fora}[lugar]
    evento = {"hook_event_name": "PreToolUse", "tool_name": ferramenta,
              "tool_input": entrada, "cwd": str(cwd)}
    return guarda.decidir(evento, principal=str(repo.principal), preflight=preflight,
                          arquivo_env=str(arquivo_env or repo.tmp / "nao-existe.env"))


def _comando(repo, ferramenta, lugar, comando, **kw):
    return _decidir(repo, ferramenta, {"command": _formatar(comando, repo)}, lugar, **kw)


# ------------------------------------------------------ comandos barrados

_GIT_CLEAN_B64 = base64.b64encode("git clean -fdx".encode("utf-16-le")).decode()

BLOQUEADOS = [
    ("Bash", "wt", "git status && git clean -fd"),
    ("Bash", "wt", 'git -C "{P}" clean -fdX'),
    ("Bash", "wt", "ls | xargs git clean -n"),
    ("Bash", "wt", "echo $(git clean -fd)"),
    ("Bash", "wt", "git stash push --all -m tudo"),
    ("Bash", "principal", "cd C:/outro/lugar && docker compose up -d"),
    ("Bash", "principal", "cd /c/Users && docker compose ps"),
    ("Bash", "wt", "docker compose up -d"),
    ("Bash", "fora", "docker-compose up -d"),
    ("Bash", "principal", "docker compose -f .claude/worktrees/agente/docker-compose.yml up -d"),
    ("Bash", "principal", 'docker compose --project-directory "{F}" up -d'),
    ("Bash", "principal", "docker compose -p outro up -d"),
    ("Bash", "principal", "COMPOSE_PROJECT_NAME=outro docker compose up -d"),
    ("Bash", "principal", "docker compose run --rm build-plugin"),
    ("Bash", "principal", "docker-compose down -v"),
    ("Bash", "principal", "docker compose down --volumes"),
    ("Bash", "principal", "docker compose down"),
    ("Bash", "wt", 'bash -c "cd \\"{P}\\" && docker compose down -v"'),
    ("Bash", "wt", "docker volume rm cs2-tracker_cs2-data"),
    ("Bash", "wt", "sudo docker volume prune -f"),
    ("Bash", "wt", "docker system prune -a --volumes"),
    ("Bash", "wt", "pip install requests"),
    ("Bash", "wt", f'"{PYTHON_DO_JOGO}" -m pip install ruff'),
    ("Bash", "wt", "uv pip install ruff"),
    ("Bash", "wt", "python -c \"import os; os.system('pip install ruff')\""),
    ("Bash", "wt", "python -m uvicorn web.app:app --reload"),
    ("Bash", "wt", "uvicorn web.app:app --host 127.0.0.1 --port=8000"),
    ("Bash", "wt", "python -m http.server"),
    ("Bash", "wt", "docker run --rm -p 8000:8000 alpine"),
    ("Bash", "wt", "echo segredo > .env"),
    ("Bash", "wt", 'cp /tmp/x.db "{P}/cs2_tracker.db"'),
    ("Bash", "principal", "rm -f cs2_tracker.db"),
    ("Bash", "principal", "rm -rf docker"),
    ("Bash", "wt", 'echo "{}" | tee -a "{P}/docker/events-live/current.jsonl"'),
    ("Bash", "wt", 'echo x > "C:\\cs2server\\game\\csgo\\cfg\\server.cfg"'),
    ("Bash", "wt", 'mv "{P}/data/profile.json" /tmp/perfil.json'),
    ("Bash", "wt", "sqlite3 \"{P}/cs2_tracker.db\" 'delete from matches'"),
    ("Bash", "wt", "find \"{P}/docker/events-live\" -name '*.jsonl' -delete"),
    ("Bash", "wt", "cd ../../.. && rm -f cs2_tracker.db"),
    ("Bash", "wt", "cat <<EOF\n$(git clean -fd)\nEOF\n"),
    ("Bash", "wt", "diff <(git clean -n) lista.txt"),
    ("Bash", "wt", "echo `git clean -fd`"),
    ("Bash", "wt", "$(which docker) compose down -v"),
    ("Bash", "wt", "timeout 5 docker compose down"),
    ("Bash", "wt", "find . -name x -exec git clean -f {} \\;"),
    ("Bash", "wt", "node -e \"require('child_process').execSync('git clean -fdx')\""),
    ("PowerShell", "wt", "1..3 | % { docker compose down }"),
    ("PowerShell", "principal", "Set-Location C:\\outro; docker compose up -d"),
    ("PowerShell", "wt",
     '& "C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" compose down -v'),
    ("PowerShell", "wt", "Remove-Item -Recurse -Force {PW}\\docker\\events-live"),
    ("PowerShell", "wt", "Set-Content -Path {PW}\\.env -Value x"),
    ("PowerShell", "wt", "'x' | Out-File C:\\cs2server\\x.txt"),
    ("PowerShell", "wt", "Start-Process docker -ArgumentList 'compose','run','x'"),
    ("PowerShell", "wt", "Start-Process -FilePath uvicorn -ArgumentList 'web.app:app'"),
    ("PowerShell", "principal", "$env:COMPOSE_PROJECT_NAME = 'x'; docker compose up -d"),
    ("PowerShell", "wt", 'cmd /c "cd C:\\x & docker compose up"'),
    ("PowerShell", "wt", f"powershell -NoProfile -EncodedCommand {_GIT_CLEAN_B64}"),
    ("PowerShell", "wt", "Invoke-Expression 'docker volume prune -f'"),
    ("PowerShell", "wt", "$saida = docker compose down -v"),
    ("PowerShell", "wt", "git status; git clean -fdx"),
    ("PowerShell", "wt", "python -m pip install ruff"),
]


@pytest.mark.parametrize("ferramenta,lugar,comando", BLOQUEADOS)
def test_comando_perigoso_e_bloqueado_com_motivo_e_alternativa(repo, ferramenta, lugar, comando):
    codigo, erro, _ = _comando(repo, ferramenta, lugar, comando)
    assert codigo == 2, erro
    assert erro.startswith("guarda (B0.5) bloqueou:")
    assert "Em vez disso:" in erro


# ------------------------------------------------------ comandos liberados

PERMITIDOS = [
    ("Bash", "wt", "git status && git log --oneline -3"),
    ("Bash", "wt", "git diff --stat origin/main...HEAD"),
    ("Bash", "wt", 'git commit -m "Bloquear docker compose down -v e git clean (card B0.5)"'),
    ("Bash", "wt", "git commit -F - <<'EOF'\nBloqueia docker compose down -v\n"
                   "git clean -fdx e pip install\nEOF\n"),
    ("Bash", "wt", "git commit -m \"$(cat <<'EOF'\nTítulo (card B0.5)\n\n"
                   "1) docker compose down -v\nEOF\n)\" && git push -u origin chore/B0.5-x"),
    ("Bash", "wt", f'"{PYTHON_DO_JOGO}" -m pytest -q -p no:cacheprovider'),
    ("Bash", "wt", "export PATH=\"$(echo \"$PATH\" | tr ':' '\\n' | grep -vi docker | paste -sd:)\""),
    ("Bash", "wt", 'grep -rn "git clean" docs AGENTS.md'),
    ("Bash", "wt", "git stash push -u -m b05-tag"),
    ("Bash", "principal", "docker compose ps"),
    ("Bash", "principal", "docker compose up -d --force-recreate"),
    ("Bash", "principal", "cd docker && docker compose config -q"),
    ("Bash", "wt", "docker ps"),
    ("Bash", "wt", "pip list"),
    ("Bash", "wt", "python -m uvicorn web.app:app --port 8010"),
    ("Bash", "wt", "python -m http.server 8010"),
    ("Bash", "wt", "curl -s http://127.0.0.1:8000/"),
    ("Bash", "wt", "rm -f cs2_tracker.db"),
    ("Bash", "wt", "echo nota > docs/nota.md 2>&1"),
    ("Bash", "wt", "cp .env.example /tmp/exemplo"),
    ("Bash", "wt", "ls docker/events-live"),
    ("Bash", "wt", "cd ../../.. && docker compose ps"),
    ("Bash", "wt", "cat <<'EOF'\n$(git clean -fd)\nEOF\n"),
    ("Bash", "wt", "x=$((1 << 2)); echo $x"),
    ("Bash", "wt", "docker compose version"),
    ("PowerShell", "wt", "$nota = @'\n$(git clean -fd)\n'@"),
    ("PowerShell", "wt", "git status; git log --oneline -3"),
    ("PowerShell", "wt",
     "$env:PATH = ($env:PATH -split ';' | Where-Object { $_ -notmatch 'Docker' }) -join ';'"),
    ("PowerShell", "wt", "Get-Content .env.example"),
    ("PowerShell", "principal", "docker compose ps"),
    ("PowerShell", "wt", "Remove-Item cs2_tracker.db"),
]


@pytest.mark.parametrize("ferramenta,lugar,comando", PERMITIDOS)
def test_comando_normal_passa(repo, ferramenta, lugar, comando):
    assert _comando(repo, ferramenta, lugar, comando) == (0, "", "")


def test_compose_na_worktree_fala_do_volume_e_do_checkout_principal(repo):
    _, erro, _ = _comando(repo, "Bash", "wt", "docker compose up -d")
    assert "fora do checkout principal" in erro
    assert guarda.PRINCIPAL in erro


def test_down_com_v_fala_do_volume(repo):
    _, erro, _ = _comando(repo, "Bash", "principal", "docker compose down -v")
    assert "volume do jogo" in erro


def test_porta_8000_sugere_a_8010(repo):
    _, erro, _ = _comando(repo, "Bash", "wt", "uvicorn web.app:app")
    assert "8000" in erro and "8010" in erro


# ------------------------------------------------------------ docker logs

@pytest.mark.parametrize("ferramenta,lugar,comando", [
    ("Bash", "wt", "docker logs --since 10m cs2-spike"),
    ("PowerShell", "wt", "docker container logs cs2-spike"),
    ("Bash", "principal", "docker compose logs --tail 50"),
])
@pytest.mark.parametrize("codigo_preflight,bloqueia", [(3, True), (1, True), (0, False),
                                                       (4, False)])
def test_docker_logs_segue_o_preflight(repo, ferramenta, lugar, comando, codigo_preflight,
                                       bloqueia):
    codigo, erro, _ = _comando(repo, ferramenta, lugar, comando,
                               preflight=lambda: codigo_preflight)
    assert codigo == (2 if bloqueia else 0), erro
    if bloqueia:
        assert f"preflight.py devolveu {codigo_preflight}" in erro


def test_preflight_so_roda_quando_o_comando_tem_docker_logs(repo):
    chamadas = []

    def preflight():
        chamadas.append(1)
        return 3

    for comando in ("git status", "docker ps", "docker compose ps", "ls docker/logs"):
        assert _comando(repo, "Bash", "principal", comando, preflight=preflight)[0] == 0
    assert chamadas == []


# ------------------------------------------------------------ falha fechada

def test_erro_interno_em_comando_com_docker_git_ou_pip_bloqueia(repo, monkeypatch):
    def quebra(*_a, **_k):
        raise RuntimeError("bug de teste")

    monkeypatch.setattr(guarda, "analisar_comando", quebra)
    for comando in ("docker ps", "git status", "pip list"):
        codigo, erro, _ = _comando(repo, "Bash", "wt", comando)
        assert codigo == 2
        assert "falha fechada" in erro


def test_erro_interno_em_comando_comum_so_avisa(repo, monkeypatch):
    def quebra(*_a, **_k):
        raise RuntimeError("bug de teste")

    monkeypatch.setattr(guarda, "analisar_comando", quebra)
    codigo, erro, saida = _comando(repo, "PowerShell", "wt", "Get-ChildItem")
    assert codigo == 0 and erro == ""
    assert "erro interno" in json.loads(saida)["systemMessage"]


def test_json_quebrado_falha_fechado_so_se_menciona_docker_git_ou_pip():
    assert guarda.decidir('{"tool_name": "Bash", "tool_input": {"command": "docker')[0] == 2
    assert guarda.decidir('{"tool_name": "Bash", "tool_input": {"command": "ls')[0] == 0


def test_erro_em_ferramenta_de_arquivo_nunca_bloqueia(repo, monkeypatch):
    def quebra(*_a, **_k):
        raise ValueError(SEGREDO)

    monkeypatch.setattr(pii, "ler_segredos", quebra)
    codigo, erro, saida = _decidir(repo, "Write", {
        "file_path": str(repo.wt / "docs" / "git-e-docker.md"), "content": "texto"})
    assert codigo == 0 and erro == ""
    assert SEGREDO not in saida


# --------------------------------------------------- ferramentas de arquivo

@pytest.mark.parametrize("ferramenta,campo,caminho", [
    ("Write", "file_path", "{WT}/.env"),
    ("Edit", "file_path", "C:\\cs2server\\game\\csgo\\cfg\\server.cfg"),
    ("Write", "file_path", "{P}/data/profile.json"),
    ("MultiEdit", "file_path", "{P}/docker/events-live/events_50_map0.jsonl"),
    ("NotebookEdit", "notebook_path", "{P}/docker/events-live/analise.ipynb"),
    ("Write", "file_path", "{WT}/cs2_tracker.db"),
])
def test_ferramenta_de_arquivo_nao_escreve_em_zona_proibida(repo, ferramenta, campo, caminho):
    caminho = caminho.replace("{WT}", str(repo.wt)).replace("{P}", str(repo.principal))
    codigo, erro, _ = _decidir(repo, ferramenta, {campo: caminho, "content": "x",
                                                  "new_string": "x", "new_source": "x"})
    assert codigo == 2, erro


def _env_falso(repo):
    (repo.tmp / ".env.example").write_text("CS2_RCONPW=CHANGE_ME_LOCAL_ONLY\n", encoding="utf-8")
    env = repo.tmp / ".env"
    env.write_text(f"SRCDS_TOKEN={TOKEN}\nCS2_RCONPW=\"{SEGREDO}\"\n"
                   f"MATCHZY_ADMINS={ID_REAL_FALSO}\n", encoding="utf-8")
    return env


@pytest.mark.parametrize("ferramenta,entrada,esperado", [
    ("Write", {"file_path": "docs/partida.md", "content": f"jogador {ID_REAL_FALSO}"},
     "SteamID64"),
    ("Edit", {"file_path": "docs/SPEC.md", "old_string": "a", "new_string": "conta [U:1:0]"},
     "SteamID3"),
    ("MultiEdit", {"file_path": "tests/fixtures/eventos.jsonl",
                   "edits": [{"old_string": "a", "new_string": '{"ip": "192.0.2.10"}'}]},
     "IPv4"),
    ("Write", {"file_path": "docs/runbooks/servidor.md", "content": f"rcon_password {SEGREDO}"},
     "CS2_RCONPW"),
    ("Write", {"file_path": "tests/fixtures/env.txt", "content": f"token: {TOKEN}"},
     "SRCDS_TOKEN"),
])
def test_pii_em_docs_e_fixtures_e_bloqueado_sem_imprimir_o_valor(repo, ferramenta, entrada,
                                                                 esperado):
    entrada = dict(entrada, file_path=str(repo.wt / entrada["file_path"]))
    codigo, erro, _ = _decidir(repo, ferramenta, entrada, arquivo_env=_env_falso(repo))
    assert codigo == 2, erro
    assert esperado in erro
    for valor in (SEGREDO, TOKEN, ID_REAL_FALSO, "192.0.2.10", "[U:1:0]"):
        assert valor not in erro


@pytest.mark.parametrize("caminho,texto", [
    ("docs/partida.md", "fictícios: 76561198000000001, 76561190000000001 e [U:1:39734273]"),
    ("docs/servidor.md", "sobe em 0.0.0.0, testa em 127.0.0.1; Metamod 2.0.0.1411, v1.0.373"),
    ("web/app.py", f"# fora de docs/ e tests/fixtures/: {ID_REAL_FALSO} 198.51.100.1"),
])
def test_texto_limpo_ou_fora_da_area_publica_passa(repo, caminho, texto):
    entrada = {"file_path": str(repo.wt / caminho), "content": texto}
    assert _decidir(repo, "Write", entrada, arquivo_env=_env_falso(repo)) == (0, "", "")


def test_sem_env_a_checagem_de_segredo_e_pulada_mas_o_resto_vale(repo):
    assert pii.ler_segredos(repo.tmp / "nao-existe.env") == []
    texto_ok = {"file_path": str(repo.wt / "docs" / "x.md"), "content": SEGREDO}
    assert _decidir(repo, "Write", texto_ok)[0] == 0
    texto_id = {"file_path": str(repo.wt / "docs" / "x.md"), "content": ID_REAL_FALSO}
    assert _decidir(repo, "Write", texto_id)[0] == 2


def test_segredos_do_env_ignoram_o_valor_publico_do_exemplo_e_quebram_a_lista(tmp_path):
    (tmp_path / ".env.example").write_text("CS2_RCONPW=CHANGE_ME_LOCAL_ONLY\n", encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("# comentário\nexport SRCDS_TOKEN='abc'\nCS2_RCONPW=CHANGE_ME_LOCAL_ONLY\n"
                   f"MATCHZY_ADMINS={ID_REAL_FALSO}, 76561198000000001\nOUTRA=valor-longo\n",
                   encoding="utf-8")
    segredos = pii.ler_segredos(env)
    # "abc" é curto demais (casaria palavra comum); o placeholder é público.
    assert ("SRCDS_TOKEN", "abc") not in segredos
    assert not any(chave == "CS2_RCONPW" for chave, _ in segredos)
    assert ("MATCHZY_ADMINS", ID_REAL_FALSO) in segredos
    assert ("MATCHZY_ADMINS", "76561198000000001") not in segredos  # fictício continua livre
    assert not any(chave == "OUTRA" for chave, _ in segredos)


def test_pii_bordas_de_steamid_e_ip():
    assert pii.achar("76561190000000002345") == []  # 20 dígitos: não é SteamID64
    assert pii.achar("versão 1.2.3.400 e 256.1.1.1") == []
    assert pii.achar("fim de frase 203.0.113.9.") == ["IPv4 na linha 1"]
    assert pii.achar("a\nb 76561190000000003") == ["SteamID64 real na linha 2"]


# ---------------------------------------------------------------- registro

def test_registrado_no_settings_com_interpretador_absoluto_e_claude_project_dir():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entradas = settings["hooks"]["PreToolUse"]
    assert len(entradas) == 1
    assert set(entradas[0]["matcher"].split("|")) == {"Bash", "PowerShell", "Edit", "Write",
                                                      "MultiEdit", "NotebookEdit"}
    (hook,) = entradas[0]["hooks"]
    assert hook["type"] == "command"
    # Forma shell com Git Bash fixo: no PowerShell, "caminho entre aspas"
    # sozinho não executa nada e o hook passaria em branco.
    assert hook["shell"] == "bash" and "args" not in hook
    assert hook["command"] == (f'"{PYTHON_DO_JOGO}" "$CLAUDE_PROJECT_DIR/tools/hooks/guarda.py"')
    # Timeout estourado libera a chamada: tem que caber o preflight do docker logs.
    assert hook["timeout"] > guarda.TIMEOUT_PREFLIGHT_S


def test_hook_e_pii_so_usam_biblioteca_padrao():
    for arquivo in (GUARDA, GUARDA.with_name("pii.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            nomes = ([a.name for a in no.names] if isinstance(no, ast.Import)
                     else [no.module] if isinstance(no, ast.ImportFrom) else [])
            for nome in nomes:
                raiz = nome.split(".")[0]
                assert raiz in sys.stdlib_module_names or raiz == "pii", (arquivo.name, nome)


# ------------------------------------------------------- como processo

def _rodar_hook(argv, evento, cwd, **kw):
    return subprocess.run(argv, input=json.dumps(evento).encode("utf-8"), cwd=cwd,
                          capture_output=True, timeout=60, **kw)


def test_de_dentro_de_uma_worktree_real_bloqueia_compose_e_pip(tmp_path):
    git = shutil.which("git")
    if git is None:
        pytest.skip("git não está no PATH")
    wt = tmp_path / f"guarda-{uuid.uuid4().hex[:8]}"
    subprocess.run([git, "-C", str(RAIZ), "worktree", "add", "--detach", "--no-checkout",
                    str(wt), "HEAD"], check=True, capture_output=True, timeout=60)
    try:
        assert (wt / ".git").is_file()  # worktree ligada de verdade
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(wt))
        casos = [("Bash", "docker compose up -d", 2),
                 ("Bash", "docker compose run --rm build-plugin", 2),
                 ("Bash", "pip install requests", 2),
                 ("PowerShell", "docker compose up -d", 2),
                 ("PowerShell", "python -m pip install requests", 2),
                 ("Bash", "git status", 0)]
        for ferramenta, comando, esperado in casos:
            evento = {"hook_event_name": "PreToolUse", "tool_name": ferramenta,
                      "tool_input": {"command": comando}, "cwd": str(wt)}
            proc = _rodar_hook([sys.executable, str(GUARDA)], evento, wt, env=env)
            erro = proc.stderr.decode("utf-8")
            assert proc.returncode == esperado, (comando, erro)
            if esperado == 2:
                assert "guarda (B0.5) bloqueou" in erro
    finally:
        subprocess.run([git, "-C", str(RAIZ), "worktree", "remove", "--force", str(wt)],
                       capture_output=True, timeout=60)


def _git_bash():
    git = shutil.which("git")
    if git is None:
        return None
    for pasta in Path(git).resolve().parents:
        if (pasta / "bin" / "bash.exe").is_file():
            return pasta / "bin" / "bash.exe"
    return None


def test_comando_do_settings_roda_no_git_bash_e_bloqueia():
    bash = _git_bash()
    if bash is None or not Path(PYTHON_DO_JOGO).is_file():
        pytest.skip("precisa do Git Bash e da .venv do jogo")
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    comando = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(RAIZ))  # com contrabarras, como no Windows
    for texto, esperado in (("git status && git clean -fd", 2), ("git status", 0)):
        evento = {"tool_name": "Bash", "tool_input": {"command": texto}, "cwd": str(RAIZ)}
        proc = _rodar_hook([str(bash), "-c", comando], evento, RAIZ, env=env)
        assert proc.returncode == esperado, proc.stderr.decode("utf-8", "replace")


def test_desempenho(repo):
    longo = " && ".join(["git status", "git log --oneline -5", 'echo "a b c" | grep a'] * 30)
    inicio = time.perf_counter()
    assert _comando(repo, "Bash", "wt", longo)[0] == 0
    assert time.perf_counter() - inicio < 0.05  # a análise em si: dezenas de µs por comando
    evento = {"tool_name": "Bash", "tool_input": {"command": "git status"}, "cwd": str(RAIZ)}
    tempos = []
    for _ in range(5):
        inicio = time.perf_counter()
        assert _rodar_hook([sys.executable, str(GUARDA)], evento, RAIZ).returncode == 0
        tempos.append(time.perf_counter() - inicio)
    # Meta do card: < 150 ms por chamada (medido ~70 ms direto, ~100 ms pelo
    # Git Bash). A folga aqui é pra máquina ocupada não derrubar a suíte.
    assert sorted(tempos)[2] < 0.5
