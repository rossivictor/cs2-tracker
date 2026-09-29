#!/usr/bin/env python3
"""
Testes do hook de guarda (card B0.5): tools/hooks/guarda.py e
tools/hooks/pii.py.

Quase tudo chama guarda.decidir() direto, com um checkout principal falso
em tmp_path (pasta com .git diretório), uma worktree falsa dentro dele
(.claude/worktrees/agente, com .git arquivo) e o preflight injetado. Nenhum
docker, pip ou preflight de verdade roda, e o .env real nunca é lido: o
arquivo_env aponta pra tmp_path.

Alguns testes rodam o hook como processo, do jeito que o Claude Code roda: de
dentro de uma worktree git REAL (git worktree add --no-checkout num
diretório temporário, removida no fim), pelo comando exato do
.claude/settings.json no Git Bash (com e sem o script no lugar), e medindo
o tempo.

SteamID64 "real" aqui é montado em tempo de execução (ID_REAL_FALSO): a
guarda confere tests/, e este arquivo não pode carregar um literal que ela
barraria.
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
# SteamID64 que a guarda trata como de pessoa de verdade (acima da base
# 76561197960265728). É o maior número que o padrão 7656119 + 10 dígitos
# aceita (conta 2039734271, a mais longe das já emitidas) e é montado em tempo
# de execução: este arquivo não carrega SteamID64 literal, e a guarda confere
# tests/. Abaixo da base não existe conta: é fictício e passa.
ID_REAL_FALSO = "7656119" + "9" * 10
OUTRO_ID_REAL_FALSO = "7656119" + "9" * 9 + "8"
ID3_REAL_FALSO = f"[U:1:{int(ID_REAL_FALSO) - pii.BASE_STEAMID64}]"


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
    # Revisão do B0.5, bloqueante 1: variável com o valor no próprio comando
    # (as ferramentas não guardam estado entre chamadas, o valor está no texto).
    ("Bash", "wt", f"PY={PYTHON_DO_JOGO}; $PY -m pip install requests"),
    ("Bash", "wt", f'PY={PYTHON_DO_JOGO}\n"$PY" -m uvicorn web.app:app'),
    ("Bash", "wt", f"export PY={PYTHON_DO_JOGO}; $PY -m uvicorn web.app:app"),
    ("Bash", "wt", f"V=C:/Users/Victor/Projetos/cs2-tracker/.venv; ${{V}}/Scripts/python.exe "
                   "-m pip install x"),
    ("PowerShell", "wt", f"$py = '{PYTHON_DO_JOGO}'; & $py -m pip install requests"),
    ("PowerShell", "wt", f"$env:PY = '{PYTHON_DO_JOGO}'; & $env:PY -m pip install x"),
    ("PowerShell", "wt", f"Set-Variable -Name py -Value '{PYTHON_DO_JOGO}'; & $py -m pip install x"),
    ("Bash", "principal", "D=docker; $D compose down -v"),
    ("Bash", "principal", "DC='docker compose'; $DC down -v"),
    ("Bash", "wt", "C=clean; git $C -fdx"),
    ("PowerShell", "principal", "$d='docker'; & $d compose down -v"),
    ("Bash", "wt", 'P="{P}"; rm -rf "$P/docker"'),
    # Variável sem valor conhecido: vale o primeiro argumento e as palavras seguintes.
    ("Bash", "wt", "$PY_SEM_VALOR_B05 -m pip install x"),
    ("Bash", "wt", "${PY_SEM_VALOR_B05} -m uvicorn web.app:app"),
    ("Bash", "principal", "$D_SEM_VALOR_B05 compose down -v"),
    # Não bloqueantes da revisão: curinga a partir do checkout principal.
    ("Bash", "principal", "rm -rf *"),
    ("Bash", "principal", "rm -rf ./*"),
    ("Bash", "principal", "rm -rf docker/*"),
    ("Bash", "principal", "rm -rf docker/events-*"),
    ("Bash", "principal", "rm -f cs2_tracker.*"),
    ("Bash", "principal", "rm -f cs2_*.db"),
    ("Bash", "principal", "rm -f .env*"),
    ("Bash", "principal", "rm -rf **/events-live"),
    ("Bash", "wt", "rm -rf ../../../*"),
    ("PowerShell", "principal", "Remove-Item * -Recurse -Force"),
    # Embrulho desconhecido, função, alias e afins.
    ("Bash", "principal", "setsid docker compose down -v"),
    ("Bash", "wt", "flock /tmp/trava git clean -fdx"),
    ("Bash", "wt", "flock -c 'git clean -fdx' /tmp/trava"),
    ("Bash", "principal", "ionice -c3 docker compose down"),
    ("Bash", "wt", "script -qc 'git clean -fdx' /dev/null"),
    ("Bash", "principal", "busybox rm -rf docker"),
    ("PowerShell", "principal", "cmd /c start /b docker compose down"),
    ("Bash", "principal", "com.docker.cli compose down -v"),
    ("Bash", "principal", 'd(){ docker "$@"; }; d compose down -v'),
    ("Bash", "principal", 'function d { docker "$@"; }\nd compose down -v'),
    ("PowerShell", "principal", "function d { docker @args }; d compose down -v"),
    ("Bash", "principal", "alias d=docker\nd compose down -v"),
    ("PowerShell", "principal", "Set-Alias d docker; d compose down -v"),
    ("Bash", "wt", "git -c alias.x=clean x -fdx"),
    ("Bash", "wt", "git -c alias.x='!git clean -fdx' x"),
    ("Bash", "wt", "git config alias.limpa 'clean -fdx'"),
    ("Bash", "wt", "python -Im pip install x"),
    ("Bash", "wt", "python -Esm pip install x"),
    ("PowerShell", "wt", "[IO.File]::WriteAllText('{PW}\\.env', 'x')"),
    ("PowerShell", "principal", "[System.IO.File]::Delete(\"$PWD\\cs2_tracker.db\")"),
    ("PowerShell", "principal", "Remove-Item (Join-Path $PWD 'cs2_tracker.db')"),
    ("Bash", "principal", "ln -sf /dev/null cs2_tracker.db"),
    ("Bash", "wt", "uv add requests"),
    ("Bash", "wt", "python -c \"import uvicorn; uvicorn.run('web.app:app')\""),
    ("Bash", "wt", "python -c \"import shutil; shutil.rmtree('{P}/docker/events-live')\""),
    ("Bash", "wt", "python -c \"open('{P}/.env', 'w').write('x')\""),
    ("Bash", "principal", "python -c \"import os; os.remove('cs2_tracker.db')\""),
    ("Bash", "wt", "node -e \"require('fs').rmSync('{P}/docker/events-live', {recursive: true})\""),
    ("Bash", "wt", "python -c \"import pip; pip.main(['install', 'x'])\""),
    ("Bash", "principal", "echo {} > docker/match_config.spike.json"),
    ("Bash", "principal", "docker compose config"),
    ("Bash", "principal", "docker inspect cs2-spike"),
    ("PowerShell", "wt", "docker container inspect cs2-spike"),
    ("Bash", "wt", "docker inspect --format '{{json .Config.Env}}' cs2-spike"),
    ("PowerShell", "wt", "powershell -EncodedCommand @@@nao-e-base64"),
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
    # O que as correções da revisão não podem pegar.
    ("Bash", "wt", f'PY={PYTHON_DO_JOGO}; "$PY" -m pytest -q -p no:cacheprovider'),
    ("PowerShell", "wt", f"$py = '{PYTHON_DO_JOGO}'; & $py -m pytest -q -p no:cacheprovider"),
    ("Bash", "wt", 'MSG="docker compose down -v e git clean"; git commit -m "$MSG"'),
    ("Bash", "wt", "echo docker compose down -v"),
    ("Bash", "wt", "which docker git pip python uvicorn"),
    ("Bash", "wt", "ls docker git"),
    ("Bash", "wt", "man git-clean"),
    ("Bash", "wt", "python -Im pytest -q"),
    ("Bash", "wt", "python -W ignore -m pytest -q"),
    ("Bash", "wt", "rm -f cs2_*.db"),
    ("Bash", "wt", "rm -rf *"),
    ("Bash", "principal", "rm -f *.pyc"),
    ("Bash", "principal", "rm -rf build/* .pytest_cache"),
    ("Bash", "principal", "docker compose config -q"),
    ("Bash", "principal", "docker compose config --hash '*'"),
    ("Bash", "principal", "docker compose config --services"),
    ("Bash", "wt", "docker inspect --format '{{.State.Status}}' cs2-spike"),
    ("PowerShell", "wt", "[IO.File]::ReadAllText('.env.example')"),
    ("PowerShell", "wt", "Remove-Item (Join-Path $PWD 'cs2_tracker.db')"),
    ("PowerShell", "wt", "Get-ChildItem docs | Where-Object { $_.Name -match 'git' }"),
    ("Bash", "wt", "python -c \"import os; os.remove('cs2_tracker.db')\""),
    ("Bash", "wt", "python -c \"print(open('README.md').read())\""),
    ("Bash", "wt", "python -c \"import uvicorn; uvicorn.run('web.app:app', port=8010)\""),
    ("Bash", "wt", "git -c core.pager=cat log --oneline -3"),
    ("Bash", "wt", 'st(){ git status "$@"; }; st --short'),
    ("Bash", "wt", "alias gs='git status'\ngs"),
    ("Bash", "wt", "setsid ls docs"),
]


@pytest.mark.parametrize("ferramenta,lugar,comando", PERMITIDOS)
def test_comando_normal_passa(repo, ferramenta, lugar, comando):
    assert _comando(repo, ferramenta, lugar, comando) == (0, "", "")


# --------------------------------- leitura com curinga do banco (card B0.5b)
# Destino em {F} (absoluto, fora do repositório): antes do B0.5b só o destino
# era conferido, e ali o curinga não alcança nada protegido, então todos
# estes passavam. Decisão: curinga puro (*, *.db) lê o banco quando a pasta é
# o checkout principal e barra; na worktree passa; pasta que não se resolve
# ($RAIZ sem valor, /tmp do Git Bash) falha fechado pelo nome.

LEITURA_DO_BANCO_BLOQUEADA = [
    # Os 4 do Problema do card, em Bash.
    ("Bash", "wt", 'cp -p "$RAIZ"/cs2_tracker.db* "{F}/destino/"'),
    ("Bash", "wt", 'cp "{P}"/cs2_tracker.d? "{F}/destino/"'),
    ("Bash", "wt", 'cp "{P}"/cs2_*.db "{F}/destino/"'),
    ("Bash", "wt", 'cat "{P}"/cs2_tracker.db* > "{F}/destino/c.db"'),
    # Os 2 em PowerShell.
    ("PowerShell", "wt", "Copy-Item -Path {PW}\\cs2_tracker.db* -Destination {F}\\destino"),
    ("PowerShell", "wt", "Get-Content {PW}\\cs2_tracker.db*"),
    # Variações: $RAIZ com valor, lados do banco, sqlite3 -readonly, type, copy,
    # gc, -LiteralPath e Join-Path, subir da worktree, curinga puro no principal.
    ("Bash", "wt", 'RAIZ="{P}"; cp -p "$RAIZ"/cs2_tracker.db* "{F}/destino/"'),
    ("Bash", "wt", 'cat "{P}"/cs2_tracker.db-w?l > "{F}/destino/wal"'),
    ("Bash", "wt", 'cp "{P}"/cs2_* "{F}/destino/"'),
    ("Bash", "wt", "sqlite3 -readonly \"{P}\"/cs2_*.db '.tables'"),
    ("Bash", "wt", "cat ../../../cs2_tracker.db*"),
    ("Bash", "wt", "cat /tmp/*.db"),
    ("Bash", "principal", "cat *.db"),
    ("Bash", "principal", "cat *"),
    ("PowerShell", "wt", "type {PW}\\cs2_tracker.d?"),
    ("PowerShell", "wt", "gc {PW}\\cs2_tracker.db-shm*"),
    ("PowerShell", "wt", "cmd /c copy {PW}\\cs2_tracker.db* {F}\\destino\\"),
    ("PowerShell", "wt", "Copy-Item -LiteralPath {PW}\\cs2_tracker.db-journal* {F}\\destino"),
    ("PowerShell", "wt", "Copy-Item (Join-Path '{PW}' 'cs2_tracker.db*') {F}\\destino"),
]


@pytest.mark.parametrize("ferramenta,lugar,comando", LEITURA_DO_BANCO_BLOQUEADA)
def test_curinga_que_le_o_banco_do_principal_e_bloqueado(repo, monkeypatch, ferramenta, lugar,
                                                        comando):
    monkeypatch.delenv("RAIZ", raising=False)
    codigo, erro, _ = _comando(repo, ferramenta, lugar, comando)
    assert codigo == 2, erro
    assert erro.startswith("guarda (B0.5) bloqueou:")
    assert "(leitura)" in erro
    assert "Em vez disso:" in erro
    assert "mode=ro pedida ao PM" in erro and "tools/backup.py" in erro


LEITURA_LIBERADA = [
    ("Bash", "wt", 'cp docs/*.md "{F}/destino/"'),
    ("Bash", "principal", 'cp docs/*.md "{F}/destino/"'),
    ("Bash", "wt", 'cp tests/*.py *.json "{F}/destino/"'),
    ("PowerShell", "wt", "Get-Content docs\\*.md"),
    # O banco que a suíte cria na PRÓPRIA worktree: apagar e ler pelo nome.
    ("Bash", "wt", "rm -f cs2_tracker.db"),
    ("PowerShell", "wt", "Remove-Item cs2_tracker.db"),
    ("Bash", "wt", "cat cs2_tracker.db*"),
    ("Bash", "wt", "cat *"),
    # O backup do B0.6 e a cópia que ele produz.
    ("Bash", "principal", f"{PYTHON_DO_JOGO} tools/backup.py --destino \"{{F}}/bk\" "
                          "--leitura-com-jogo"),
    ("Bash", "wt", f"{PYTHON_DO_JOGO} tools/backup.py --destino \"{{F}}/bk\""),
    ("Bash", "wt", 'cp "{F}"/bk/cs2_tracker.backup.* "{F}/copia/"'),
    ("Bash", "principal",
     "sqlite3 -readonly \"{F}/bk/cs2_tracker.backup.db\" 'select count(*) from matches'"),
]


@pytest.mark.parametrize("ferramenta,lugar,comando", LEITURA_LIBERADA)
def test_curinga_que_nao_le_o_banco_do_principal_passa(repo, ferramenta, lugar, comando):
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


def test_falha_fechada_so_com_a_palavra_inteira(repo, monkeypatch):
    # "digit", "github", "pipe" e "Pipfile" têm git/pip dentro, mas não são docker, git ou pip.
    def quebra(*_a, **_k):
        raise RuntimeError("bug de teste")

    monkeypatch.setattr(guarda, "analisar_comando", quebra)
    codigo, erro, saida = _comando(repo, "Bash", "wt", "echo digit github pipe Pipfile")
    assert codigo == 0 and erro == "" and "erro interno" in saida
    for comando in ("docker.exe ps", "git.exe status", "pip3 list", "docker-compose ps"):
        assert _comando(repo, "Bash", "wt", comando)[0] == 2, comando


@pytest.mark.parametrize("valor", ["@@@", "QQ", "QUJD"])
def test_encoded_command_ilegivel_bloqueia_sem_erro_interno(repo, valor):
    # Base64 quebrado ou UTF-16 de tamanho ímpar: bloqueio com motivo, não falha fechada.
    codigo, erro, _ = _comando(repo, "PowerShell", "wt", f"pwsh -EncodedCommand {valor}")
    assert codigo == 2
    assert "EncodedCommand ilegível" in erro and "falha fechada" not in erro


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
    ("Edit", "file_path", "{P}/docker/match_config.spike.json"),
])
def test_ferramenta_de_arquivo_nao_escreve_em_zona_proibida(repo, ferramenta, campo, caminho):
    caminho = caminho.replace("{WT}", str(repo.wt)).replace("{P}", str(repo.principal))
    codigo, erro, _ = _decidir(repo, ferramenta, {campo: caminho, "content": "x",
                                                  "new_string": "x", "new_source": "x"})
    assert codigo == 2, erro


def test_match_config_da_worktree_e_editavel(repo):
    # Só a cópia do checkout principal é estado de runtime do start_match.
    entrada = {"file_path": str(repo.wt / "docker" / "match_config.spike.json"),
               "old_string": "a", "new_string": "b"}
    assert _decidir(repo, "Edit", entrada) == (0, "", "")


# ------------------------------------------------ navegador do Claude

def _launch(repo, configuracoes):
    pasta = repo.principal / ".claude"
    pasta.mkdir(exist_ok=True)
    (pasta / "launch.json").write_text(json.dumps({"version": "0.0.1",
                                                   "configurations": configuracoes}),
                                       encoding="utf-8")


@pytest.mark.parametrize("ferramenta", ["mcp__Claude_Browser__preview_start",
                                        "mcp__remote-devices__Claude_Browser__preview_start"])
def test_preview_start_na_8000_e_bloqueado(repo, ferramenta):
    _launch(repo, [
        {"name": "wizard-web", "runtimeExecutable": ".venv\\Scripts\\python.exe",
         "runtimeArgs": ["-m", "uvicorn", "web.app:app", "--port", "8000"], "port": 8000},
        {"name": "porta-padrao", "runtimeExecutable": "uvicorn", "runtimeArgs": ["web.app:app"],
         "port": 8010},
        {"name": "fixture", "runtimeExecutable": ".venv\\Scripts\\python.exe",
         "runtimeArgs": ["-m", "uvicorn", "web.app:app", "--port", "8010"], "port": 8010},
    ])
    for nome, esperado in (("wizard-web", 2), ("porta-padrao", 2), ("fixture", 0)):
        codigo, erro, _ = _decidir(repo, ferramenta, {"name": nome}, lugar="principal")
        assert codigo == esperado, (nome, erro)
    # Com url, o preview só abre uma aba: não sobe servidor.
    assert _decidir(repo, ferramenta, {"url": "http://127.0.0.1:8000"})[0] == 0


def test_launch_json_do_repo_ainda_tem_a_wizard_web_na_8000_e_a_guarda_barra(repo):
    # A troca da wizard-web pra 8010 com banco de fixture é decisão do Victor;
    # até lá, a guarda barra o preview_start dela.
    configuracoes = json.loads((RAIZ / ".claude" / "launch.json").read_text(encoding="utf-8"))
    _launch(repo, configuracoes["configurations"])
    codigo, erro, _ = _decidir(repo, "mcp__Claude_Browser__preview_start", {"name": "wizard-web"},
                               lugar="principal")
    assert codigo == 2 and "8000" in erro


def _env_falso(repo):
    (repo.tmp / ".env.example").write_text("CS2_RCONPW=CHANGE_ME_LOCAL_ONLY\n", encoding="utf-8")
    env = repo.tmp / ".env"
    env.write_text(f"SRCDS_TOKEN={TOKEN}\nCS2_RCONPW=\"{SEGREDO}\"\n"
                   f"MATCHZY_ADMINS={ID_REAL_FALSO}\n", encoding="utf-8")
    return env


@pytest.mark.parametrize("ferramenta,entrada,esperado", [
    ("Write", {"file_path": "docs/partida.md", "content": f"jogador {ID_REAL_FALSO}"},
     "SteamID64"),
    ("Edit", {"file_path": "docs/SPEC.md", "old_string": "a",
              "new_string": f"conta {ID3_REAL_FALSO}"},
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
    for valor in (SEGREDO, TOKEN, ID_REAL_FALSO, "192.0.2.10", ID3_REAL_FALSO):
        assert valor not in erro


@pytest.mark.parametrize("caminho,texto", [
    ("docs/partida.md", "fictícios: 76561198000000001, 76561190000000001 e [U:1:39734273]"),
    # Até a base não existe conta: fixture anonimizada pode ter quantos jogadores quiser.
    ("tests/fixtures/eventos.jsonl", "76561190000000002 76561190000000003 76561197960265728 "
                                     "[U:1:0]"),
    ("docs/servidor.md", "sobe em 0.0.0.0, testa em 127.0.0.1; Metamod 2.0.0.1411, v1.0.373"),
    ("docs/matriz.md", "| CS2 build 1.40.9.3 | ok |\nPatchVersion=1.40.9.3\nversão: 1.40.9.3"),
    ("web/app.py", f"# fora de docs/ e tests/: {OUTRO_ID_REAL_FALSO} 198.51.100.1"),
    ("tests/test_rede.py", "# IP em teste fora de tests/fixtures/ pode: 198.51.100.1"),
    ("docs/board-cs2/cartao.md", f"board local, fora do git: {OUTRO_ID_REAL_FALSO}"),
])
def test_texto_limpo_ou_fora_da_area_publica_passa(repo, caminho, texto):
    entrada = {"file_path": str(repo.wt / caminho), "content": texto}
    assert _decidir(repo, "Write", entrada, arquivo_env=_env_falso(repo)) == (0, "", "")


@pytest.mark.parametrize("caminho,texto,esperado", [
    # Segredo do .env não é de nenhum arquivo do repositório.
    (".env.example", f"SRCDS_TOKEN={TOKEN}", "SRCDS_TOKEN"),
    ("web/app.py", f'SENHA = "{SEGREDO}"', "CS2_RCONPW"),
    ("docs/board-cs2/cartao.md", f"token {TOKEN}", "SRCDS_TOKEN"),
    # SteamID em qualquer lugar de tests/, não só em tests/fixtures/.
    ("tests/test_x.py", f'JOGADOR = "{OUTRO_ID_REAL_FALSO}"', "SteamID64"),
    ("AGENTS.md", "servidor em 198.51.100.7", "IPv4"),
    (".env.example", "CS2_IP=198.51.100.7", "IPv4"),
    (".cursor/rules/agentes.mdc", f"jogador {OUTRO_ID_REAL_FALSO}", "SteamID64"),
])
def test_pii_fora_de_docs_tambem_e_barrado(repo, caminho, texto, esperado):
    entrada = {"file_path": str(repo.wt / caminho), "content": texto}
    codigo, erro, _ = _decidir(repo, "Write", entrada, arquivo_env=_env_falso(repo))
    assert codigo == 2, erro
    assert esperado in erro
    for valor in (SEGREDO, TOKEN, OUTRO_ID_REAL_FALSO, "198.51.100.7"):
        assert valor not in erro


def test_senha_fraca_do_env_so_conta_na_area_publica(repo):
    # Senha fraca ("password") casaria meio repositório: fora de docs/ e afins,
    # só vale segredo forte (token, SteamID, 8+ com letra e dígito).
    env = repo.tmp / ".env"
    env.write_text("CS2_RCONPW=password\n", encoding="utf-8")
    codigo_web = {"file_path": str(repo.wt / "web" / "app.py"), "content": "# password"}
    assert _decidir(repo, "Write", codigo_web, arquivo_env=env) == (0, "", "")
    doc = {"file_path": str(repo.wt / "docs" / "x.md"), "content": "rcon: password"}
    codigo, erro, _ = _decidir(repo, "Write", doc, arquivo_env=env)
    assert codigo == 2 and "CS2_RCONPW" in erro


def test_fora_de_repositorio_nao_confere_pii(repo):
    entrada = {"file_path": str(repo.fora / "rascunho.md"),
               "content": f"{SEGREDO} {OUTRO_ID_REAL_FALSO} 198.51.100.1"}
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
    assert pii.achar(f"a\nb {ID_REAL_FALSO}") == ["SteamID64 real na linha 2"]


def test_pii_steamid_ate_a_base_e_ficticio_e_versao_nao_e_ip():
    for ficticio in ("76561190000000002", "76561190000000099", str(pii.BASE_STEAMID64),
                     "[U:1:0]", "76561198000000001"):
        assert pii.achar(ficticio) == [], ficticio
    assert pii.achar(str(pii.BASE_STEAMID64 + 1)) == ["SteamID64 real na linha 1"]
    for versao in ("CS2 build 1.40.9.3", "PatchVersion=1.40.9.3", "Versão do jogo: 1.40.9.3",
                   "version 1.40.9.3"):
        assert pii.achar(versao) == [], versao
    # Só `=` não basta: chave de IP com valor de IP continua sendo IP.
    assert pii.achar("SERVER_IP=203.0.113.9") == ["IPv4 na linha 1"]
    # Os interruptores do escopo: fora de docs/, tests/ sem fixtures não confere IP.
    assert pii.achar(f"{ID_REAL_FALSO} 203.0.113.9", ids=False, ips=False) == []


# ---------------------------------------------------------------- registro

COMANDO_DO_HOOK = (
    'g="$CLAUDE_PROJECT_DIR/tools/hooks/guarda.py"; if [ -f "$g" ]; then '
    f'exec "{PYTHON_DO_JOGO}" "$g"; else '
    'echo "guarda (B0.5) ausente em $g: hook desligado" >&2; exit 1; fi')


def test_registrado_no_settings_com_interpretador_absoluto_e_claude_project_dir():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entradas = settings["hooks"]["PreToolUse"]
    assert len(entradas) == 2
    assert set(entradas[0]["matcher"].split("|")) == {"Bash", "PowerShell", "Edit", "Write",
                                                      "MultiEdit", "NotebookEdit"}
    # Com caractere de regex, o matcher é regex sem âncora (docs de hooks): as
    # âncoras deixam só o preview_start, do navegador local ou do remoto.
    assert entradas[1]["matcher"] == "^mcp__.*__preview_start$"
    for entrada in entradas:
        (hook,) = entrada["hooks"]
        assert hook["type"] == "command"
        # Forma shell com Git Bash fixo: no PowerShell, "caminho entre aspas"
        # sozinho não executa nada e o hook passaria em branco.
        assert hook["shell"] == "bash" and "args" not in hook
        # Interpretador absoluto; script pelo $CLAUDE_PROJECT_DIR, conferido antes:
        # sem ele, o python sairia com 2 e travaria toda ferramenta da sessão.
        assert hook["command"] == COMANDO_DO_HOOK
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
                 ("Bash", f"PY={PYTHON_DO_JOGO}; $PY -m pip install requests", 2),
                 ("PowerShell", "docker compose up -d", 2),
                 ("PowerShell", "python -m pip install requests", 2),
                 ("PowerShell", f"$py = '{PYTHON_DO_JOGO}'; & $py -m pip install requests", 2),
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


@pytest.mark.parametrize("projeto", ["pasta-vazia", None])
def test_sem_o_script_o_hook_avisa_e_nao_trava_a_sessao(tmp_path, projeto):
    # Voltar pra tag jogavel-2026-09-26 (sem tools/hooks) ou settings de uma
    # worktree com $CLAUDE_PROJECT_DIR no checkout principal: o python sairia
    # com 2 ("can't open file") e o Claude Code barraria TODA ferramenta,
    # inclusive o Edit que conserta o settings. Com a checagem, sai com 1:
    # erro visível, que não bloqueia.
    bash = _git_bash()
    if bash is None:
        pytest.skip("precisa do Git Bash")
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if projeto:
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    evento = {"tool_name": "Bash", "tool_input": {"command": "git clean -fdx"},
              "cwd": str(tmp_path)}
    for entrada in settings["hooks"]["PreToolUse"]:
        proc = _rodar_hook([str(bash), "-c", entrada["hooks"][0]["command"]], evento, tmp_path,
                           env=env)
        erro = proc.stderr.decode("utf-8", "replace")
        assert proc.returncode == 1, erro
        assert "guarda (B0.5) ausente" in erro


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
    # Meta do card: < 150 ms por chamada (medido ~70-110 ms direto, ~100-130 ms
    # pelo Git Bash, conforme a carga da máquina). O tempo do processo é
    # relatório, não critério: depende da máquina, e a análise em si já tem o
    # limite apertado acima. Com `pytest -s` a mediana aparece.
    print(f"\nguarda: mediana de {sorted(tempos)[2] * 1000:.0f} ms por chamada (processo)")
