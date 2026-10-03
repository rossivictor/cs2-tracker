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
    posix = repo.principal.as_posix()
    return (texto.replace("{P}", posix)
                 .replace("{PW}", str(repo.principal))
                 .replace("{M}", "/" + posix[0].lower() + posix[2:])  # /c/... do Git Bash
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
    # B0.5d: o docker-compose.yml deixou de casar a rede, e o .exe não pode escapar.
    ("Bash", "wt", "python -c \"import os; os.system('docker-compose.exe down')\""),
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


# ------------- leitura pelo nome literal e @(...) do PowerShell (card B0.5c)
# Só guarda.decidir com evento sintético: nenhum destes comandos roda de
# verdade, e {P} é um checkout principal falso em tmp_path. Antes do B0.5c
# só o curinga era conferido: o nome literal em cat/head/xxd/type/Get-Content
# e sqlite3 -readonly passava, e o PowerShell não olhava dentro de @(...),
# nem quando o cmdlet escrevia ou apagava.

BANCO, ENV, LISTA = "banco", "env", "lista"
ALTERNATIVA = {BANCO: ("mode=ro pedida ao PM", "tools/backup.py"), ENV: (".env.example",),
               LISTA: ("Em vez disso: escreva o caminho literal",)}

LEITURA_LITERAL_BLOQUEADA = [
    # Os 7 do Problema, em Bash.
    ("Bash", "wt", "cat {P}/cs2_tracker.db", BANCO),
    ("Bash", "wt", "cat {P}/cs2_tracker.db > {F}/destino/c.db", BANCO),
    ("Bash", "wt", "head -c 100 {P}/cs2_tracker.db", BANCO),
    ("Bash", "wt", "xxd {P}/cs2_tracker.db", BANCO),
    ("Bash", "wt", "sqlite3 -readonly {P}/cs2_tracker.db 'select count(*) from matches'", BANCO),
    ("Bash", "wt", "sqlite3 {F}/x.db < {P}/cs2_tracker.db", BANCO),
    ("Bash", "wt", "cat {P}/.env", ENV),
    # Os 3 do Problema, em PowerShell.
    ("PowerShell", "wt", "Get-Content {P}/cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "type {P}/cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "Get-Content {P}/.env", ENV),
    # Os 5 do Problema com @(...): cópia, leitura, escrita e remoção.
    ("PowerShell", "wt", "Copy-Item @('{P}/cs2_tracker.db') {F}/destino", BANCO),
    ("PowerShell", "wt", "Copy-Item @('{P}/.env') {F}/destino", ENV),
    ("PowerShell", "wt", "Get-Content @('{P}/.env')", ENV),
    ("PowerShell", "wt", "Set-Content @('{P}/cs2_tracker.db') 'x'", BANCO),
    ("PowerShell", "wt", "Move-Item @('{P}/cs2_tracker.db') {F}/destino", BANCO),
    # -wal, -shm e -journal do banco.
    ("Bash", "wt", "cat {P}/cs2_tracker.db-wal", BANCO),
    ("Bash", "wt", "xxd {P}/cs2_tracker.db-shm", BANCO),
    ("Bash", "wt", "head -c 10 {P}/cs2_tracker.db-journal", BANCO),
    ("Bash", "wt", "sqlite3 -readonly {P}/cs2_tracker.db-wal .tables", BANCO),
    ("PowerShell", "wt", "Get-Content {PW}\\cs2_tracker.db-shm", BANCO),
    ("PowerShell", "wt", "Get-Content @('{P}/cs2_tracker.db-wal')", BANCO),
    ("PowerShell", "wt", "Copy-Item @('{P}/cs2_tracker.db-journal') {F}/destino", BANCO),
    # Outras formas de ler o mesmo arquivo: pasta relativa, $RAIZ sem valor,
    # outros leitores, URI do sqlite, cmd /c, -LiteralPath, lista nua com mais
    # de um item, nome que o Windows lê como o mesmo arquivo.
    ("Bash", "principal", "cat cs2_tracker.db", BANCO),
    ("Bash", "principal", "cat .env", ENV),
    ("Bash", "wt", "cat ../../../cs2_tracker.db", BANCO),
    ("Bash", "wt", 'cat "$RAIZ/cs2_tracker.db"', BANCO),
    ("Bash", "wt", 'cat "$RAIZ"/.env', ENV),
    ("Bash", "wt", "cat {P}/.ENV", ENV),
    ("Bash", "wt", "cat {P}/cs2_tracker.db.", BANCO),
    ("Bash", "wt", "cat '{P}/cs2_tracker.db::$DATA'", BANCO),
    ("Bash", "wt", "grep SRCDS {P}/.env", ENV),
    ("Bash", "wt", "grep -rn -e SRCDS {P}/.env", ENV),
    ("Bash", "wt", "sed -n p {P}/.env", ENV),
    ("Bash", "wt", "awk '{print}' {P}/.env", ENV),
    ("Bash", "wt", "tail -n 3 {P}/.env", ENV),
    ("Bash", "wt", "strings {P}/cs2_tracker.db", BANCO),
    ("Bash", "wt", "sqlite3 -readonly 'file:{P}/cs2_tracker.db?mode=ro' .tables", BANCO),
    ("Bash", "wt", "sqlite3 {F}/x.db .dump < {P}/.env", ENV),
    ("PowerShell", "wt", "cmd /c type {PW}\\cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "Get-Content -LiteralPath {PW}\\.env", ENV),
    ("PowerShell", "wt", "gc -Path:{P}/cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "Select-String -Pattern SRCDS -Path {P}/.env", ENV),
    # Lista nua: cada string é argumento do cmdlet, inclusive a que começa com -.
    ("PowerShell", "wt", "Copy-Item -Path @('docs/README.md', '{P}/.env') -Destination {F}/d", ENV),
    ("PowerShell", "wt", 'Get-Content @( "docs/README.md" , "{P}/.env" )', ENV),
    ("PowerShell", "wt", "Remove-Item @('-Filter', '{P}/cs2_tracker.db')", BANCO),
    ("PowerShell", "wt", "$lista = @('{P}/.env'); Get-Content $lista", ENV),
    # Opção sem valor não esconde o arquivo; --file=<arquivo> lê o arquivo.
    ("Bash", "wt", "grep -e x {P}/.env", ENV),
    ("Bash", "wt", "grep -n -e '\\.env' -f {P}/.env x", ENV),
    ("Bash", "wt", "grep -T X {P}/.env", ENV),
    ("Bash", "wt", "grep --file={P}/.env x", ENV),
    ("Bash", "wt", "jq -C . {P}/.env", ENV),
    ("Bash", "wt", "jq '.a' {P}/.env", ENV),
    ("Bash", "wt", "jq -r .env {P}/cs2_tracker.db", BANCO),
    ("Bash", "wt", "rg -g '*.py' X {P}/.env", ENV),
    ("PowerShell", "wt", "Select-String -Path {P}/.env -Pattern '\\.env'", ENV),
    ("PowerShell", "wt", "Select-String -Pattern '.env' -Path {P}/.env", ENV),
]

# Critério 2 (trocado em 30/09): ao lado de cmdlet de arquivo, @( que não é
# lista literal nua falha fechado, qualquer que seja o caminho de dentro,
# inclusive um da worktree. {A} é o caminho; \n é quebra de linha de verdade.
CMDLETS_DE_ARQUIVO = [
    "Get-Content", "gc", "type", "cat", "Import-Csv", "Format-Hex", "Select-String", "sls",
    "Copy-Item", "cpi", "copy", "cp", "Move-Item", "mi", "move", "mv", "Rename-Item", "ren",
    "Remove-Item", "ri", "rm", "del", "erase", "rd", "rmdir",
    "Set-Content", "sc", "Add-Content", "ac", "Out-File", "Clear-Content", "clc", "New-Item",
    "ni", "tee", "Tee-Object"]
ENVOLTORIOS_DE_LISTA = [
    '@("{A}")[0]', '(@("{A}"))', '$(@("{A}"))', '@("{A}").FullName', '(@("{A}"))[0]',
    '@(@("{A}"))', '-Path:(@("{A}"))', '-Path:@("{A}")', '( @("{A}") )', '$( @("{A}") )',
    '([string[]] @("{A}"))', '[string[]]@("{A}")', '(<# c #>@("{A}"))', '(\n@("{A}"))',
    '@("{A}").Trim()', '@("{A}"<# c #>)', '@(\n"{A}")', '@("{A}", \n"x")', '@("{A}" + "")',
    '@("{A}")+@("x")', '@("{A}$x")', "@('{A}', $x)", '@("{A}`t")', "@('x', (\"{A}\"))",
    '@(Get-Item "{A}")', '@($sem_valor)', "@('{A}’,’x')"]
ALVOS_DA_LISTA = ["docs/README.md", "{P}/cs2_tracker.db", "{P}/.env"]


@pytest.mark.parametrize("envoltorio", ENVOLTORIOS_DE_LISTA)
@pytest.mark.parametrize("cmdlet", CMDLETS_DE_ARQUIVO)
def test_arroba_que_nao_e_lista_nua_fecha_nos_cmdlets_de_arquivo(repo, cmdlet, envoltorio):
    for alvo in ALVOS_DA_LISTA:
        comando = f"{cmdlet} {envoltorio.replace('{A}', alvo)} {{F}}/d"
        for preflight_do_jogo in (0, 3):
            codigo, erro, _ = _comando(repo, "PowerShell", "wt", comando,
                                       preflight=lambda: preflight_do_jogo)
            assert codigo == 2, (comando, erro)
            assert "só passa como lista literal nua" in erro, (comando, erro)
            assert "Em vez disso: escreva o caminho literal" in erro


@pytest.mark.parametrize("comando", [
    "Copy-Item @('docs/README.md') {F}\\destino",
    "Copy-Item @('docs/README.md', \"docs/SPEC.md\") {F}\\destino",
    "Get-Content @( 'docs/README.md' )",
    "Copy-Item -Path @('docs/README.md') -Destination {F}\\destino",
    "Remove-Item @('cs2_tracker.db')",
    "Set-Content docs/nota.md -Value @('a', 'b')"])
def test_lista_literal_nua_passa_e_cada_string_vira_argumento(repo, comando):
    assert _comando(repo, "PowerShell", "wt", comando) == (0, "", "")


def test_arroba_entre_aspas_tambem_fecha(repo):
    """A guarda não sabe se o @( veio de dentro de aspas: sobra bloqueio. Para
    gravar esse texto, mande-o pelo pipe ('texto @(x)' | Set-Content arq)."""
    assert _comando(repo, "PowerShell", "wt", "Set-Content docs/nota.md 'a @(b) c'")[0] == 2
    assert _comando(repo, "PowerShell", "wt", "'a @(b) c' | Set-Content docs/nota.md")[0] == 0


# Critério 2, retomada 3: no PowerShell a linha que termina em vírgula ou em
# operador continua na de baixo. Antes, a guarda cortava o comando na quebra e
# a linha de baixo virava outro comando: os 6 primeiros saíam 0, e o PowerShell
# 5.1 lia, gravava ou apagava o arquivo da linha de baixo (QA, reprovação 3).
CONTINUACAO_BLOQUEADA = [
    "Get-Content 'docs/README.md',\n@('{P}/.env')[0]",
    "Get-Content -Path 'docs/README.md',\n@('{P}/.env')",
    "Get-Content 'docs/README.md', #c\n@('{P}/.env')[0]",
    "Get-Content 'docs/README.md',\r\n@('{P}/.env')[0]",
    "Set-Content 'docs/x.md',\n@('{P}/cs2_tracker.db').Trim() 'x'",
    "Remove-Item 'docs/x.md',\n@('{P}/cs2_tracker.db')[0]",
    # Várias continuações em cadeia, linha em branco e comentário entre elas, e
    # a continuação no meio dos argumentos.
    "Get-Content 'docs/a.md',\n'docs/b.md',\n\n# c\n<# d #>\n@('{P}/.env')[0] -Encoding utf8",
    "Copy-Item -Path 'docs/a.md',\n'{P}/cs2_tracker.db' -Destination {F}/d",
    "Get-Content -Encoding utf8 -Path 'docs/a.md',\r\n  '{P}/.env'",
    "Get-Content 'docs/README.md', <# c\nc #> @('{P}/.env')[0]",
]
OPERADORES_NO_FIM = ["-join", "-and", "-or", "-f", "+", "-replace", "-split", "-eq", "-like",
                     "-match", "-band", "-CNotMatch", "-ilike", "-xor", "=", "*", "%", "-", ".."]
# B0.5d: o `..` (1 ..<LF>5) e o comentário colado ao operador (-join<#c#>,
# -join#c) também continuam a linha no PowerShell 5.1.
DEPOIS_DO_OPERADOR = ["\n", "\r\n", " #c\n", " <# c #>\n", "\n\n", "\n# c\n\n", "\r\n\r\n",
                      "#c\n", "<#c#>\n", "<#c#>\r"]


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("comando", CONTINUACAO_BLOQUEADA)
def test_linha_que_termina_em_virgula_continua_no_powershell(repo, comando, preflight_do_jogo):
    codigo, erro, _ = _comando(repo, "PowerShell", "wt", comando,
                               preflight=lambda: preflight_do_jogo)
    assert codigo == 2, (comando, erro)
    assert "Em vez disso:" in erro


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
def test_linha_que_termina_em_operador_tambem_junta_a_de_baixo(repo, preflight_do_jogo):
    for op in OPERADORES_NO_FIM:
        for meio in DEPOIS_DO_OPERADOR:
            for alvo in ("{P}/.env", "{P}/cs2_tracker.db"):
                comando = f"Get-Content 'docs/README.md' {op}{meio}@('{alvo}')[0]"
                codigo, erro, _ = _comando(repo, "PowerShell", "wt", comando,
                                           preflight=lambda: preflight_do_jogo)
                assert codigo == 2, (comando, erro)
                assert "só passa como lista literal nua" in erro, (comando, erro)


@pytest.mark.parametrize("comando,operador", [
    ("Get-Content 'docs/README.md',", "','"),
    ("Get-Content 'docs/README.md',\n", "','"),
    ("Get-Content 'docs/README.md',\r\n\r\n# só comentário", "','"),
    ("Get-Content 'docs/README.md', <# bloco que não fecha\n", "','"),
    ("Get-Content 'docs/README.md' -join", "'-join'"),
    ("$x = 'docs/README.md' +\n", "'+'")])
def test_operador_sem_linha_de_baixo_falha_fechado(repo, comando, operador):
    codigo, erro, _ = _comando(repo, "PowerShell", "wt", comando)
    assert codigo == 2
    assert f"termina em {operador}" in erro and "falha fechada" in erro


@pytest.mark.parametrize("ferramenta,comando", [
    # Vírgula ou operador dentro de aspas não continua a linha.
    ("PowerShell", "Write-Output 'a,'\nGet-Content docs/README.md"),
    ("PowerShell", 'Write-Output "-join"\nGet-Content docs/README.md'),
    ("PowerShell", "Write-Output 'a,\nb'"),
    # Continuação legítima, só com arquivos da worktree.
    ("PowerShell", "Get-Content 'docs/README.md',\n  'docs/SPEC.md'\nGet-Content docs/x.md"),
    ("PowerShell", "$texto = 'a' +\n'b'"),
    # Curinga e `..` no fim não pedem linha de baixo.
    ("PowerShell", "Get-ChildItem *"),
    ("PowerShell", "Set-Location .."),
    # Bash não muda: vírgula e operador no fim da linha não juntam nada.
    ("Bash", "echo a,\ncat docs/README.md"),
    ("Bash", "echo a -and\nls *"),
    ("Bash", "echo a,")])
def test_continuacao_so_vale_para_o_powershell_e_fora_de_aspas(repo, ferramenta, comando):
    assert _comando(repo, ferramenta, "wt", comando) == (0, "", "")


# Critério 2, 2ª extensão (01/10): no PowerShell 5.1 o CR sozinho também é fim
# de linha e encerra o comentário #. A guarda lia o CR como espaço e só fechava
# o comentário no LF: o comentário engolia a linha de baixo, e o comando depois
# do CR colava no de cima. Todas estas formas saíam 0 (QA, reprovação 4).
CMDLETS_DO_CR = ["Set-Content", "Copy-Item", "Move-Item", "Remove-Item", "Get-Content", "gc",
                 "ri", "type"]
ALVOS_DO_CR = ["@('{P}/.env')[0]", "@('{P}/cs2_tracker.db')[0]", "'{P}/.env'",
               "{P}/cs2_tracker.db"]
FORMAS_DO_CR = [
    "{c} 'docs/README.md', #c\r{a}\nWrite-Output ok",
    "{c} 'docs/README.md', #c\r{a}\r\nWrite-Output ok",
    "{c} 'docs/README.md', #c\r{a}\rWrite-Output ok",
    "{c} 'docs/README.md',\r{a}",
    "Write-Output x\r{c} {a}",
    "Write-Output x #c\r{c} {a}\r\n",
    "{c} `\r{a}",
    "& {c} 'docs/README.md', #c\r{a}\nWrite-Output ok",
    "Invoke-Command {{ {c} 'docs/README.md', #c\r{a} }}\r\nWrite-Output ok",
    # Here-string com CR sozinho: o corpo acaba no CR'@ e a linha de baixo é comando.
    "Write-Output @'\rit's\r'@\r{c} {a}"]


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("forma", FORMAS_DO_CR)
def test_cr_sozinho_e_fim_de_linha_e_de_comentario_no_powershell(repo, forma, preflight_do_jogo):
    for cmdlet in CMDLETS_DO_CR:
        for alvo in ALVOS_DO_CR:
            comando = forma.format(c=cmdlet, a=alvo)
            codigo, erro, _ = _comando(repo, "PowerShell", "wt", comando,
                                       preflight=lambda: preflight_do_jogo)
            assert codigo == 2, (comando, erro)
            assert "Em vez disso:" in erro


@pytest.mark.parametrize("comando", [
    "Get-Content 'docs/README.md',\r  'docs/SPEC.md'\rGet-Content docs/x.md",
    "Get-Content 'docs/README.md', #c\r'docs/SPEC.md'\r\nWrite-Output ok",
    "Write-Output x\rGet-Content docs/README.md\rRemove-Item cs2_tracker.db",
    "# comentário\rCopy-Item @('docs/README.md') {F}\\destino",
    "$texto = 'a' +\r'b'",
    "Get-Content docs/README.md `\r -Encoding utf8",
    "git commit -m @'\r\nGuarda: CR, vírgula,\r\n# e Remove-Item @('x')[0] no corpo\r\n'@",
    "Write-Output @'\rit's, #c\r'@\rGet-Content docs/README.md"])
def test_cr_sozinho_nao_vira_falso_positivo(repo, comando):
    assert _comando(repo, "PowerShell", "wt", comando) == (0, "", "")


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("ferramenta,lugar,comando,tipo", LEITURA_LITERAL_BLOQUEADA)
def test_leitura_pelo_nome_e_lista_do_powershell_sao_bloqueadas(
        repo, monkeypatch, ferramenta, lugar, comando, tipo, preflight_do_jogo):
    for nome in ("RAIZ", "DATA", "VARIAVEL_QUE_NAO_EXISTE_B05C"):
        monkeypatch.delenv(nome, raising=False)
    codigo, erro, _ = _comando(repo, ferramenta, lugar, comando,
                               preflight=lambda: preflight_do_jogo)
    assert codigo == 2, erro
    assert erro.startswith("guarda (B0.5) bloqueou:")
    assert "Em vez disso:" in erro
    for trecho in ALTERNATIVA[tipo]:
        assert trecho in erro, erro


LEITURA_LITERAL_LIBERADA = [
    # O que o card manda continuar passando.
    ("Bash", "wt", f"{PYTHON_DO_JOGO} tools/backup.py --destino \"{{F}}/bk\""),
    ("Bash", "principal", f"{PYTHON_DO_JOGO} tools/backup.py --destino \"{{F}}/bk\""),
    ("Bash", "wt", "rm -f cs2_tracker.db"),
    ("PowerShell", "wt", "Remove-Item cs2_tracker.db"),
    ("Bash", "wt", "cat docs/README.md"),
    ("PowerShell", "wt", "Get-Content .env.example"),
    ("PowerShell", "wt", "Copy-Item @('docs/README.md') {F}\\destino"),
    ("Bash", "wt", "git status"),
    # Vizinhos que não podem virar falso positivo.
    ("Bash", "wt", "cat cs2_tracker.db"),  # o banco da PRÓPRIA worktree
    ("Bash", "wt", "cat .env.example"),
    ("Bash", "wt", "head -n 5 docs/README.md"),
    ("Bash", "wt", "grep -rn '.env' docs"),
    ("Bash", "wt", "grep -rn 'cs2_tracker.db' docs AGENTS.md"),
    ("Bash", "wt", "sed -n p docs/README.md"),
    ("Bash", "wt", "cat \"{F}\"/bk/cs2_tracker.backup.db"),
    ("Bash", "wt", "sqlite3 -readonly \"{F}/bk/cs2_tracker.backup.db\" '.tables'"),
    ("Bash", "wt", "ls {P}/.env {P}/cs2_tracker.db"),  # só metadados: não lê o conteúdo
    ("PowerShell", "wt", "Get-Content -Path .env.example"),
    # @(...) ao lado de comando que não lê nem escreve arquivo segue livre.
    ("PowerShell", "wt", "Get-ChildItem @($sem_valor)"),
    ("PowerShell", "wt", "Get-ChildItem (@($sem_valor))[0]"),
    ("PowerShell", "wt", "$linhas = @(Get-Content docs/README.md); $linhas.Count"),
    ("PowerShell", "wt", "git add @('docs/README.md')"),
    # O valor de -e, --regexp e -Pattern é padrão, e o de --exclude é glob: não é
    # arquivo. O jq lê o arquivo, não o filtro.
    ("Bash", "wt", "grep -n -e '\\.env' AGENTS.md"),
    ("Bash", "wt", "rg -n -e '\\.env' AGENTS.md"),
    ("Bash", "wt", "grep -n --regexp '\\.env' AGENTS.md"),
    ("Bash", "wt", "grep -rn X --exclude .env ."),
    ("Bash", "wt", "grep -rn X --exclude=.env ."),
    ("Bash", "wt", "rg -g '.env' X docs"),
    ("Bash", "wt", "sed -n -e '/.env/p' docs/README.md"),
    ("Bash", "wt", "jq '.env' x.json"),
    ("Bash", "wt", "jq -e '.env' x.json"),
    ("PowerShell", "wt", "Select-String -Path AGENTS.md -Pattern '\\.env'"),
    ("PowerShell", "wt", "Select-String -Pattern '.env' -Path AGENTS.md"),
    ("PowerShell", "wt", "Select-String -Pattern:'.env' -Path:AGENTS.md"),
    ("PowerShell", "wt", 'Select-String -Path AGENTS.md -Pattern "\\.env"'),
    ("Bash", "wt", 'grep -n -e "\\.env" AGENTS.md'),
    ("Bash", "wt", "rg -T py X docs"),
]


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("ferramenta,lugar,comando", LEITURA_LITERAL_LIBERADA)
def test_leitura_que_nao_toca_o_banco_nem_o_env_do_principal_passa(
        repo, ferramenta, lugar, comando, preflight_do_jogo):
    assert _comando(repo, ferramenta, lugar, comando,
                    preflight=lambda: preflight_do_jogo) == (0, "", "")


def test_lista_do_powershell_abre_cada_item_como_argumento_do_cmdlet(repo):
    """Gabarito à mão: com o banco no meio da lista e a lista no meio dos
    argumentos, o motivo cita o item (o banco), não a lista inteira."""
    _, erro, _ = _comando(repo, "PowerShell", "wt",
                          "Copy-Item @('docs/README.md', '{P}/cs2_tracker.db') {F}\\d")
    assert "cs2_tracker.db" in erro and "@(" not in erro.split("Em vez disso:")[0]


def test_leitura_do_env_explica_a_alternativa(repo):
    _, erro, _ = _comando(repo, "Bash", "wt", "cat {P}/.env")
    assert ".env.example" in erro and "não se lê, copia nem imprime" in erro


# ---------------------------- formas indiretas (card B0.5d)
# Só guarda.decidir com evento sintético e {P} falso em tmp_path: nada roda.
# Na main a776a94 (antes do card) todas as bloqueadas saíam 0, menos três que
# ficam de guarda contra regressão: crase e $(...) com o nome do .env ou com
# curinga (já falhavam fechado pelo nome) e o Select-String com lista de dois.
_Q, _QQ = chr(0x2019), chr(0x201D)  # aspas tipográficas: ’ e ”
FORMAS_INDIRETAS_BLOQUEADAS = [
    # Os 7 do Problema.
    ("Bash", "wt", "cp {P}/cs2_tracker.{db,db-wal} {F}/", BANCO),
    ("Bash", "wt", "cat `echo {P}`/cs2_tracker.d?", BANCO),
    ("Bash", "wt", "ls {P}/cs2_tracker.d? | xargs cat", BANCO),
    ("Bash", "wt", "for f in {P}/cs2_*.db; do cat $f; done", BANCO),
    ("Bash", "wt", "tar cf {F}/a.tar {P}/cs2_*.db", BANCO),
    ("Bash", "wt", "cp -r {P} {F}/", BANCO),
    ("Bash", "wt", "cat {P}/CS2_TR~1.DB", BANCO),
    # Critério 2: crase e $(...) colados ao padrão do banco ou do .env.
    ("Bash", "wt", "cat $(echo {P})/cs2_tracker.d?", BANCO),
    ("Bash", "wt", "cat `echo {P}`/.env", ENV),
    ("Bash", "wt", "cat $(echo {P}/cs2_tracker.db)", BANCO),
    # Critério 3: a raiz inteira, por qualquer copiador, inclusive subindo da worktree.
    ("Bash", "wt", "cp -a {P} {F}/", BANCO),
    ("Bash", "principal", "cp -r . {F}/x", BANCO),
    ("PowerShell", "wt", "Copy-Item -Recurse {P} {F}/x", BANCO),
    ("PowerShell", "wt", "robocopy {PW} {F}\\x /E", BANCO),
    ("PowerShell", "wt", "xcopy {PW} {F}\\x /E /I", BANCO),
    ("PowerShell", "wt", "Copy-Item {P} {F}/x -Recurse -Filter *.db", BANCO),
    ("Bash", "wt", "zip -r {F}/a.zip {P}", BANCO),
    # Vizinhos: 8.3 na pasta, rm por 8.3, pipe e xargs.
    ("Bash", "wt", "cat C:/Users/Victor/Projetos/CS2-TR~1/cs2_tracker.db", BANCO),
    ("Bash", "wt", "rm {P}/CS2_TR~1.DB", BANCO),
    ("Bash", "wt", "echo {P}/.env | xargs cat", ENV),
    ("PowerShell", "wt", "'{P}/cs2_tracker.db' | Remove-Item", BANCO),
    # QA do B0.5c: Select-String -Path nomeado e padrão posicional (N1).
    ("PowerShell", "wt", "Select-String -Path {P}/.env SRCDS", ENV),
    ("PowerShell", "wt", "sls -LiteralPath {P}/cs2_tracker.db x", BANCO),
    ("PowerShell", "wt", "Select-String -Path @('docs/a.md', '{P}/.env') SRCDS", ENV),
    # # e <# colados ao token anterior (N3, N5) e aspas tipográficas (N4).
    ("PowerShell", "wt", "Write-Output 'a'#'\nRemove-Item '{P}/cs2_tracker.db'\n#'", BANCO),
    ("PowerShell", "wt", "Write-Output 'a'#'\rRemove-Item '{P}/cs2_tracker.db'\r#'", BANCO),
    ("PowerShell", "wt", "$x=1#'\nGet-Content '{P}/.env'\n#'", ENV),
    ("PowerShell", "wt", "Write-Output (1)#'\nGet-Content '{P}/.env'\n#'", ENV),
    ("PowerShell", "wt", "Write-Output a<#b\nGet-Content '{P}/.env'\n#>", ENV),
    ("PowerShell", "wt", f"Write-Output 'a{_Q}\nGet-Content '{{P}}/.env'", ENV),
    ("PowerShell", "wt", f'Write-Output "a{_QQ}\nGet-Content \'{{P}}/.env\'', ENV),
    ("PowerShell", "wt", f"Write-Output @'\nx\n{_Q}@\nGet-Content '{{P}}/.env'", ENV),
    # Splatting (N2) e os extras dos QA anteriores.
    ("PowerShell", "wt", "$a = @('{P}/.env'); Get-Content @a", LISTA),
    ("PowerShell", "wt", "fhx {P}/.env", ENV),
    ("PowerShell", "wt", "ipcsv {P}/cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "Get-Content FileSystem::{P}/cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "Get-Content $('{P}/.env')", ENV),
    ("PowerShell", "wt", "Get-Content -Path:$('{P}/cs2_tracker.db')", BANCO),
    ("PowerShell", "wt", "Get-Content ('{P}/cs2' + '_tracker.db')", BANCO),
    ("Bash", "wt", "grep --color X {P}/.env", ENV),
    # QA 1 do B0.5d. Cópia da raiz com as opções lidas pelo nome (C3).
    ("PowerShell", "wt", "robocopy {PW} {F}\\x /E /XD .git", BANCO),
    ("PowerShell", "wt", "robocopy /E {PW} {F}\\x", BANCO),
    ("PowerShell", "wt", "xcopy /E /I {PW} {F}\\x", BANCO),
    ("PowerShell", "wt", "Copy-Item -Recurse -Path:{P} {F}/x", BANCO),
    ("Bash", "wt", "cp -rt {F}/x {P}", BANCO),
    ("Bash", "wt", "cp -r --target-directory {F}/x {P}", BANCO),
    ("Bash", "wt", "tar -C{P} -cf x.tar .", BANCO),
    ("Bash", "wt", "tar cf x.tar --directory={P} .", BANCO),
    # Crase igual ao $(...), e substituição colada a curinga (C2).
    ("Bash", "wt", "cat $(echo {P}/cs2_tracker.d)?", BANCO),
    ("Bash", "wt", "cat `echo {P}/cs2_tracker.d?`", BANCO),
    ("Bash", "wt", "cat `ls {P}/cs2_*.db`", BANCO),
    ("Bash", "wt", "cp `echo {P}/cs2_tracker.db` {F}/", BANCO),
    ("Bash", "wt", "sqlite3 `echo {P}/cs2_tracker.db`", BANCO),
    # for depois de palavra-chave.
    ("Bash", "wt", "if true; then for f in {P}/cs2_*.db; do cat $f; done; fi", BANCO),
    ("Bash", "wt", "{ for f in {P}/cs2_*.db; do cat $f; done; }", BANCO),
    ("Bash", "wt", "! for f in {P}/cs2_*.db; do cat $f; done", BANCO),
    ("Bash", "wt", "for x in 1; do for f in {P}/cs2_*.db; do cat $f; done; done", BANCO),
    ("Bash", "wt", "while true; do for f in {P}/.env; do cat $f; done; done", ENV),
    # <# literal e # comentário na mesma linha (5.1), soma sem espaço, cmd /c com aspas.
    ("PowerShell", "wt", "Write-Output a<#b 'c'#'\nGet-Content {P}/.env\n#'#>", ENV),
    ("PowerShell", "wt", "Write-Output a<#b(1)#'\nGet-Content {P}/.env\n#'#>", ENV),
    ("PowerShell", "wt", "Get-Content ('{P}/.e'+'nv')", ENV),
    ("PowerShell", "wt", 'cmd /c powershell -c "& {Get-Content {P}/.env}"', ENV),
    ("Bash", "wt", 'cmd //c powershell -c "Get-Content {P}/.env"', ENV),
] + [("PowerShell", "wt", f"Get-Content{chr(c)}{{P}}/.env", ENV)
     for c in (0x0B, 0x0C, 0x85, 0xA0, 0x2003)  # VT, FF, NEL, NBSP, EM SPACE
     ] + [("PowerShell", "wt", f"{sls}docs/a.md,{{P}}/.env x", ENV)  # a lista toda vai ao -Path
          for sls in ("Select-String -Path ", "Select-String -LiteralPath ", "sls -Path ",
                      "Select-String -Path:")] + [
    ("PowerShell", "wt", "Select-String -Path 'docs/a.md','{P}/.env' x", ENV),
    ("PowerShell", "wt", "Select-String -Path docs/a.md, {P}/.env x", ENV)] + [
    # QA 2 do B0.5d. Item entre parênteses na lista do -Path: a vírgula marca o
    # grupo de fora, e (...) vale pelas palavras de dentro (regressão N1).
    ("PowerShell", "wt", f"{sls}docs/a.md,{item} x", tipo)
    for sls in ("Select-String -Path ", "Select-String -LiteralPath ", "Select-String -Path:",
                "sls -Path ")
    for item, tipo in (('("{P}/.env")', ENV), ("('{P}/.env')", ENV), ("(Join-Path {P} .env)", ENV),
                       ('("{P}/cs2_tracker.db")', BANCO),
                       ("(Join-Path {P} cs2_tracker.db)", BANCO))] + [
    # Substituição colada ao nome ou ao curinga do banco: vale a palavra montada
    # E o nome, que falha fechado com a pasta sem resolver (regressão C2).
    ("Bash", "wt", f"{leitor} {sub}", BANCO)
    for leitor in ("cat", "head", "xxd", "sqlite3 -readonly")
    for sub in ("$(cd {P}; pwd)/cs2_tracker.db", "$(cd {P}; pwd)/cs2_*.db",
                "$(echo {P}; true)/cs2_tracker.db", "$(echo {P} | tr a a)/cs2_tracker.db",
                "`cd {P}; pwd`/cs2_*.db")] + [
    ("PowerShell", "wt", 'Get-Content "$(cd {P}; pwd)/cs2_tracker.db"', BANCO),
    # robocopy e xcopy com a raiz no formato do Git Bash (/c/...), com e sem //E.
    ("Bash", "wt", "robocopy {M} {F}/x //E", BANCO),
    ("Bash", "wt", "robocopy {M} {F}/x", BANCO),
    ("Bash", "wt", "xcopy {M} {F}/x //E //I", BANCO),
    ("Bash", "wt", "xcopy {M} {F}/x", BANCO)]


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("ferramenta,lugar,comando,tipo", FORMAS_INDIRETAS_BLOQUEADAS)
def test_forma_indireta_de_ler_o_banco_ou_o_env_e_bloqueada(repo, ferramenta, lugar, comando,
                                                             tipo, preflight_do_jogo):
    codigo, erro, _ = _comando(repo, ferramenta, lugar, comando,
                               preflight=lambda: preflight_do_jogo)
    assert codigo == 2, (comando, erro)
    assert erro.startswith("guarda (B0.5) bloqueou:") and "Em vez disso:" in erro
    for trecho in ALTERNATIVA[tipo]:
        assert trecho in erro, (comando, erro)


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("ferramenta,lugar,comando", [
    # Os 5 do critério 4.
    ("Bash", "wt", "cp -r docs {F}/"),
    ("Bash", "wt", "tar cf {F}/d.tar docs"),
    ("Bash", "wt", "for f in docs/*.md; do cat $f; done"),
    ("Bash", "wt", "ls docs/*.md | xargs cat"),
    ("Bash", "wt", "cp tests/fixtures/{a,b}.json {F}/"),
    # Subpasta do principal, a própria worktree, filtro inofensivo e vizinhos.
    ("Bash", "principal", "cp -r docs {F}/"),
    ("Bash", "wt", "cp -r . {F}/x"),
    ("PowerShell", "wt", "Copy-Item -Recurse docs {F}/x"),
    ("PowerShell", "wt", "robocopy {PW} {F}\\x *.md /S"),
    ("PowerShell", "wt", "Copy-Item {P} {F}/x -Recurse -Filter *.md"),
    ("Bash", "wt", "find . -name '*.py' | xargs grep -l '\\.env'"),
    ("PowerShell", "wt", "Get-ChildItem docs | Get-Content"),
    ("Bash", "wt", "cat docs/README~1.md"),
    ("PowerShell", "wt", "Select-String -Path AGENTS.md '\\.env'"),  # era falso positivo
    ("PowerShell", "wt", "Write-Output a#b\nGet-Content docs/README.md"),
    ("PowerShell", "wt", f"Write-Output {_Q}a{_Q}; $x = 1 ..\n5"),
    ("Bash", "wt", "grep --color=auto X docs/README.md"),
    ("Bash", "wt", "python -c \"import subprocess; subprocess.run(['ls', 'docker-compose.yml'])\""),
    # QA 1 do B0.5d: as correções não barram subpasta, filtro nem substituição comum.
    ("PowerShell", "wt", "robocopy /MIR docs {F}\\x /XD node_modules .git"),
    ("Bash", "wt", "cp -rt {F}/x docs"),
    ("Bash", "wt", "tar -czf {F}/x.tgz -C docs ."),
    ("Bash", "wt", "cat $(git ls-files docs) `echo docs/README.md`"),
    ("Bash", "wt", "if true; then for f in docs/*.md; do cat $f; done; fi"),
    ("PowerShell", "wt", "Select-String -Path docs/a.md, docs/b.md x"),
    ("PowerShell", "wt", "cmd /c \"echo .env & dir docs\""),
    # QA 2 do B0.5d: as correções não barram item comum, substituição comum nem subpasta.
    ("PowerShell", "wt", "Select-String -Path docs/a.md,('docs/b.md') x"),
    ("PowerShell", "wt", "Select-String -Path docs/a.md,(Join-Path docs b.md) x"),
    ("Bash", "wt", "cat $(pwd)/docs/a.md"),
    ("Bash", "wt", "cat $(git rev-parse --show-toplevel)/docs/a.md"),
    ("Bash", "wt", "head `pwd`/docs/a.md"),
    ("Bash", "wt", "robocopy docs {F}/x //E"),
    ("Bash", "wt", "robocopy {M}/docs {F}/x //E"),
    ("Bash", "wt", "xcopy docs {F}/x //E //I"),
])
def test_forma_indireta_que_nao_alcanca_o_banco_nem_o_env_passa(repo, ferramenta, lugar, comando,
                                                                preflight_do_jogo):
    assert _comando(repo, ferramenta, lugar, comando,
                    preflight=lambda: preflight_do_jogo) == (0, "", "")


# Card B0.5e: cópia ou movimentação para uma PASTA do checkout principal com
# o nome de origem do banco ou do .env. A guarda junta o nome da origem à pasta.
COPIA_PARA_PASTA_BLOQUEADA = [
    # Os 2 do Problema.
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination {P}", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination {P}/", BANCO),
    # Os lados do banco e o .env.
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db-wal -Destination {P}", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db-shm -Destination {P}", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db-journal -Destination {P}/", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/.env -Destination {P}", ENV),
    ("PowerShell", "wt", "Copy-Item -Path {F}/.env -Destination {P}/", ENV),
    # Abreviações de -Destination e -Destination:<valor>.
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Des {P}", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Dest {P}/", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/.env -destinat {P}", ENV),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination:{P}", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path:{F}/.env -Dest:{P}/", ENV),
    # Parâmetros em qualquer ordem, origem posicional com destino nomeado.
    ("PowerShell", "wt", "Copy-Item -Destination {P} -Path {F}/cs2_tracker.db", BANCO),
    ("PowerShell", "wt", "Copy-Item -Destination {P}/ {F}/.env", ENV),
    ("PowerShell", "wt", "Copy-Item -Force -Destination:{P} -LiteralPath {F}/cs2_tracker.db",
     BANCO),
    # -LiteralPath e o alias -LP.
    ("PowerShell", "wt", "Copy-Item -LiteralPath {F}/cs2_tracker.db -Destination {P}", BANCO),
    ("PowerShell", "wt", "Copy-Item -LP {F}/.env -Destination {P}", ENV),
    # Os aliases.
    ("PowerShell", "wt", "cpi -Path {F}/cs2_tracker.db -Destination {P}", BANCO),
    ("PowerShell", "wt", "copy -Path {F}/.env -Destination {P}/", ENV),
    ("PowerShell", "wt", "cp -Path {F}/cs2_tracker.db -Destination {P}", BANCO),
    ("PowerShell", "wt", "Move-Item -Path {F}/cs2_tracker.db -Destination {P}", BANCO),
    ("PowerShell", "wt", "mi -Path {F}/.env -Destination {P}/", ENV),
    ("PowerShell", "wt", "move -LiteralPath {F}/cs2_tracker.db-wal -Destination {P}/docs", BANCO),
    ("PowerShell", "wt", "mv -Path {F}/.env -Destination:{P}", ENV),
    # Lista nua na origem: com @(...) e com vírgula.
    ("PowerShell", "wt", "Copy-Item -Path @('{F}/a.txt', '{F}/cs2_tracker.db') -Destination {P}",
     BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/a.txt,{F}/.env -Destination {P}/", ENV),
    # Subpasta do principal, destino relativo a partir dele e pasta que não se resolve.
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination {P}/docs", BANCO),
    ("PowerShell", "principal", "Copy-Item -Path {F}/cs2_tracker.db -Destination .", BANCO),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination $sem_valor", BANCO),
    # Forma GNU cuja origem a guarda lia como valor de opção (cp -u x <R>).
    ("Bash", "wt", "cp -u {F}/cs2_tracker.db {P}", BANCO)]


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("ferramenta,lugar,comando,tipo", COPIA_PARA_PASTA_BLOQUEADA)
def test_copia_para_pasta_do_principal_com_o_nome_do_banco_ou_do_env_e_bloqueada(
        repo, ferramenta, lugar, comando, tipo, preflight_do_jogo):
    codigo, erro, _ = _comando(repo, ferramenta, lugar, comando,
                               preflight=lambda: preflight_do_jogo)
    assert codigo == 2, (comando, erro)
    assert erro.startswith("guarda (B0.5) bloqueou:") and "Em vez disso:" in erro
    motivo = "é o banco cs2_tracker.db" if tipo == BANCO else "é o .env"
    assert motivo in erro, (comando, erro)
    for trecho in ALTERNATIVA[tipo]:
        assert trecho in erro, (comando, erro)


def test_copia_para_pasta_nomeia_o_arquivo_que_seria_sobrescrito(repo):
    _, erro, _ = _comando(repo, "PowerShell", "wt",
                          "Copy-Item -Path {F}/cs2_tracker.db -Destination {P}/")
    assert f"em {repo.principal.as_posix()}/cs2_tracker.db:" in erro, erro


@pytest.mark.parametrize("preflight_do_jogo", [0, 3])
@pytest.mark.parametrize("ferramenta,lugar,comando", [
    # Os 4 do critério 2.
    ("PowerShell", "wt", "Copy-Item -Path {F}/a.txt -Destination {P}"),
    ("PowerShell", "wt", "Copy-Item docs/README.md {F}"),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination {F}/outra/"),
    ("PowerShell", "wt", "Remove-Item cs2_tracker.db"),
    # Vizinhos: outras formas dos mesmos 4.
    ("PowerShell", "wt", "Copy-Item -Path docs/README.md -Destination {F}"),
    ("PowerShell", "wt", "Copy-Item -Destination:{P}/docs -LiteralPath {F}/a.txt"),
    ("PowerShell", "wt", "Copy-Item {F}/cs2_tracker.db {F}/outra/"),
    ("PowerShell", "wt", "Copy-Item -Path {F}/cs2_tracker.db -Destination ."),
    ("Bash", "wt", "cp {F}/cs2_tracker.db {F}/outra/"),
    ("Bash", "wt", "rm cs2_tracker.db"),
    ("Bash", "wt", "rm {P}/.claude/worktrees/agente/cs2_tracker.db"),
])
def test_copia_que_nao_sobrescreve_o_banco_nem_o_env_do_principal_passa(
        repo, ferramenta, lugar, comando, preflight_do_jogo):
    assert _comando(repo, ferramenta, lugar, comando,
                    preflight=lambda: preflight_do_jogo) == (0, "", "")


def test_copia_da_raiz_explica_o_que_vai_junto_e_a_alternativa(repo):
    _, erro, _ = _comando(repo, "Bash", "wt", "cp -r {P} {F}/")
    assert "raiz do checkout principal" in erro and ".env" in erro
    assert "Em vez disso:" in erro and "tools/backup.py" in erro and "docs/" in erro


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
