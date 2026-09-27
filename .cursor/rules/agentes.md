---
description: Proibições do cs2-tracker para agentes (o jogo do Victor precisa continuar jogável)
alwaysApply: true
---

# cs2-tracker: proibições para agentes no Cursor

O Cursor não roda os hooks nem as permissões do `.claude/settings.json`, então
aqui as travas são só estas regras. Elas repetem as proibições do `AGENTS.md`
(na raiz), que continua sendo a fonte: leia-o inteiro antes de mexer.

O Victor joga ~10–15 mapas por semana, sem avisar. O jogo tem que continuar
jogável o tempo todo.

## Antes de tocar em qualquer coisa viva

Rode `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py`:
`0` livre, `3` Victor jogando (vence o 4), `4` janela de manutenção aberta.
Com 3, só trabalho offline. Servidor, container, RCON e volume só mudam em
janela aberta pelo Victor ("pode mexer no servidor", ou depois de "terminei"
na trilha de bots), e nunca por ausência de processo.

## Nunca

- Usar outro Python que não `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe` (o do sistema é o 3.14, incompatível).
- `pip install`, `python -m pip install` ou `uv pip install`: a `.venv` é a do jogo.
- Ler ou escrever o `cs2_tracker.db` real, o `.env`, o `data/profile.json` ou `docker/events-live/`.
- Editar, reverter ou commitar `docker/match_config.spike.json` (estado de runtime).
- Tocar no volume `cs2-tracker_cs2-data` ou em `C:/cs2server`.
- `docker compose down` (com ou sem `-v`), `docker volume rm`/`prune`, `docker system prune`, `docker compose run`.
- `docker compose` fora do checkout principal `C:/Users/Victor/Projetos/cs2-tracker`.
- `docker compose up`/`stop`/`restart`, `docker run`/`exec`/`cp` ou RCON sem janela aberta.
- `git clean` em qualquer forma; `git add -A` ou `git add .`; push na `main`; `--force`.
- Usar a porta 8000 (é do Victor); use a 8010.
- Trocar `botprofile.vpk` ou a DLL do plugin com o servidor vivo.
- `docker logs` com partida em curso.
- Rodar `wizard_tui.py`, `start_match.py` ou `watcher.py` de verdade.
- Propor aposentar ou mexer no `wizard_tui.py` antes da D13 (MD3 completa pelo browser + OK do Victor).
- Pôr SteamID64 real, IP ou segredo em `docs/`, `tests/` ou commit (o repositório é público).
