---
tipo: adr
status: aceito
aliases: [ADR-0011]
fontes:
  - "commit 5adb8bc"
  - "commit d562258"
  - "commit 8abc99b"
  - "pyproject.toml:15"
  - "pyproject.toml:19-28"
  - ".python-version:1"
  - "AGENTS.md:18-21"
  - ".github/workflows/ci.yml:89"
  - ".github/workflows/ci.yml:117"
atualizado: 2026-10-13
---

# ADR-0011: Um interpretador só: Python 3.13 na `.venv` do jogo, com dependências travadas

## Contexto

Em 02/09, o parser de demo entrou com o awpy 2.0.2, que exige Python abaixo de 3.14. O projeto passou a usar uma `.venv` com Python 3.13 e um `requirements.txt`, em vez de instalar pacotes no Python do sistema (`5adb8bc`). O Python do sistema na máquina do Victor é o 3.14, incompatível (AGENTS.md:20).

Até 04/10, as dependências do jogo não estavam declaradas nem travadas, e o CI não tinha como reproduzir o ambiente (`d562258`).

## Decisão

- **O projeto roda em Python 3.13**, declarado em `.python-version` e no `requires-python = ">=3.13,<3.14"` (`pyproject.toml:15`), decidido no `d562258` (T1.2, 04/10).
- **A `.venv` do jogo é a única**, chamada pelo caminho absoluto, porque worktree não tem `.venv` (AGENTS.md:18-21).
- **A `.venv` não se altera por agente:** nada de `pip install` ou `pip uninstall`. Dependência nova é pedido ao Victor.
- **As versões ficam travadas:** o `pyproject.toml` lista as dependências diretas (`pyproject.toml:19-28`), o `requirements.lock` é o retrato `nome==versão` da `.venv`, e o `requirements-dev.txt` puxa o lock e acrescenta pytest, httpx e ruff.
- **O CI usa o mesmo 3.13** no Windows, como a máquina do Victor (`8abc99b`; `.github/workflows/ci.yml:89` e `:117`).

## Alternativas consideradas

- **Python do sistema (3.14)**: o awpy não roda nele.
- **Dependências sem lock**: o CI não reproduziria a `.venv`, e uma atualização silenciosa quebraria o jogo.

## Consequências

- O motivo da trava abaixo de 3.14 é o awpy, que só existe por causa das demos. Quando a poda tirar o caminho da demo (S1.2; [ADR-0008](0008-captura-por-plugin-proprio.md)), a trava pode ser revista, por card próprio. Este ADR não decide isso.
- Comando Python em doc, runbook ou relatório usa o caminho absoluto da `.venv`; o `tests/test_base_de_conhecimento.py` cobra isso nas notas vivas.
- Verificação: o job `pytest` do CI roda a suíte no 3.13 a partir do `requirements-dev.txt`.

## Status

Aceito na prática desde 02/09/2026 (`5adb8bc`, a `.venv` 3.13) e 04/10 (`d562258`, a declaração e o lock), na `main`. ADR retroativo, escrito pelo K1.6 em 13/10 a partir dos commits; o texto não passou pela leitura do Victor.

## Fontes

- Commits `5adb8bc` (awpy e a `.venv`), `d562258` (declaração e lock) e `8abc99b` (CI no 3.13).
- `pyproject.toml`, `.python-version`, AGENTS.md e o workflow do CI: o estado de hoje.
