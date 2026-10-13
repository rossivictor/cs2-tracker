---
tipo: adr
status: aceito
aliases: [ADR-0012]
fontes:
  - "commit 6bf07e6"
  - "commit 185fbee"
  - "commit 6de3e95"
  - "commit 8abc99b"
  - "tests/conftest.py:1-39"
  - "tests/conftest.py:180-196 (travas do docker)"
  - ".github/workflows/ci.yml:18-22 (gatilhos: PR e push na main)"
  - ".github/workflows/ci.yml:31-204 (jobs compose, plugin, ruff, pytest, crlf-sh e pii)"
  - "AGENTS.md:68-73"
  - "AGENTS.md:123"
  - "docs/agents/sprints.md:83 (6 checks obrigatórios na main protegida; T1.8, Q20=A)"
atualizado: 2026-10-13
---

# ADR-0012: Suíte hermética e CI obrigatório antes do merge

## Contexto

Até a T1 (03 a 04/10), nada conferia o compose nem a compilação do plugin de captura antes do merge: um erro só aparecia no boot do servidor, já dentro da janela (`6bf07e6`). A suíte também não era hermética: o `DB_PATH` relativo abria um banco vazio na worktree (42 falhas `no such table: matches`) ou o banco real no checkout principal, e os testes da web chamavam `docker cp`, então a suíte só passava com o Docker fora do PATH (`185fbee`). E nenhum teste provava, offline, que a TUI ainda monta e lança a partida (`6de3e95`).

## Decisão

- **A suíte é hermética** (`185fbee`, T1.4). Antes da coleta, o `tests/conftest.py` aponta o app para um golden.db temporário, só com o schema, e instala travas para a sessão inteira: docker recusado, conexão só para loopback aberto pelo próprio processo, e `sqlite3.connect` só em pasta temporária ou em `tests/fixtures/` (`tests/conftest.py:1-39`). A baseline é 0 falhas, com ou sem o Docker no PATH (AGENTS.md:68-73).
- **O G4 prova a TUI sem jogo** (`6de3e95`, T1.5): smoke com Pilot até o Resumo e integração TUI → `run_match` com docker, RCON e watcher falsos.
- **O CI roda em todo PR e em todo push na `main`** (`.github/workflows/ci.yml:18-22`), com seis jobs (`6bf07e6`, T1.1; `8abc99b`, T1.6): `compose` (`docker compose config -q`), `plugin` (compila o Cs2TrackerEvents fora de `docker/plugins/`), `ruff` (só erros graves), `pytest` (Windows, 3.13), `crlf-sh` (sem CR nos `*.sh` do índice) e `pii` (`pii.achar` em `docs/` e `tests/fixtures/`).
- **Os seis checks são obrigatórios na `main` protegida** (T1.8, Q20=A; `docs/agents/sprints.md:83`). O merge é por PR, com merge commit, feito pelo tech-manager depois do QA.

## Alternativas consideradas

- **Rodar a suíte com o Docker fora do PATH** (o costume até o T1.4): o banco real ficava ao alcance do teste (`185fbee`); que isso "escondia o furo em vez de fechá-lo" é dedução do escritor do K1.6, não registrada em commit.
- **Validar o compose e o plugin só no boot**: o erro aparecia dentro da janela (`6bf07e6`), com o jogo parado.

## Consequências

- Teste novo usa `tmp_path`, `monkeypatch` e fixture anonimizada; o que precisa de docker, rede ou processo real usa fake ([ADR-0003](0003-repo-publico.md) para a anonimização).
- Os gates do AGENTS.md (AGENTS.md:123) ficam assim: G1 (pytest hermético), G2 (ruff no CI), G3 (CI) e G4 (TUI) antes do merge; G6 e G7 depois, na janela e na partida ([ADR-0004](0004-jogo-sempre-jogavel.md)).
- O CI não vê o que só a partida mostra: passar no CI não fecha um degrau do caminho de jogo.
- Um `cs2_tracker.db` que apareça numa worktree é sinal de teste furando o conftest.

## Status

Aceito na prática entre 03/10 (`6bf07e6`) e 04/10/2026 (`185fbee`, `6de3e95`, `8abc99b`), na `main`; a T1 fechou com a `jogavel-2026-10-12`. ADR retroativo, escrito pelo K1.6 em 13/10 a partir dos commits; confirmado pelo Victor em 13/10.

## Fontes

- Commits `6bf07e6`, `185fbee`, `6de3e95` e `8abc99b`: o problema e cada peça.
- `tests/conftest.py`, o workflow do CI, o AGENTS.md e o `sprints.md`: o estado de hoje.
