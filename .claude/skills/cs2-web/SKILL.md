---
name: cs2-web
description: App web do cs2-tracker (FastAPI em web/, wizard e estatísticas). Use para rodar ou verificar a web sem o jogo, na porta 8010 com banco e catálogo de VPK de fixture (tools/web_golden.py), nunca na 8000.
---

# Web do cs2-tracker

- Código: `web/app.py` (rotas; a lógica do wizard é a do `wizard_core.py`), `web/templates/` e `templates/` (home e relatório), `static/`.
- Escopo e paridade com a TUI: [M3-web-paridade.md](../../../docs/features/M3-web-paridade.md), [M3.5-home.md](../../../docs/features/M3.5-home.md) e [M4-seletor.md](../../../docs/features/M4-seletor.md). O que vale para o `wizard_tui.py` e desde quando `web/` é caminho de jogo: [AGENTS.md](../../../AGENTS.md).

## Web dourado: a web sem o jogo

A 8000 é a `wizard-web` do Victor. Para ver a web, use o `tools/web_golden.py`: banco novo com o schema e sem partida, `profile.json` na pasta da fixture e o catálogo de perfis lido de um `botprofile.vpk` de fixture, sem `docker cp`. Processo nenhum roda, e a 8000 é recusada.

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/web_golden.py --check
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/web_golden.py
```

- `--check`: os pedidos dourados em processo, sem porta; sai 0 quando todos batem.
- Sem flag: uvicorn em `http://127.0.0.1:8010/`. No navegador do Claude, `preview_start` com a configuração `web-golden` do `.claude/launch.json`, que roda o `tools/web_golden.py` do worktree onde foi aberta.
- `--pasta <D>`: guarda a fixture numa pasta sua (padrão: temporária nova).

Na verificação Web do QA, prove que a página é a da branch (passo 5 do [qa.md](../../agents/qa.md)).

## Testes

`tests/test_web_wizard.py` (fluxo do wizard), `tests/test_matches_screens.py` (partidas) e `tests/test_web_golden.py` (a ferramenta acima). Falha de `no such table: matches` nos testes web é a baseline do AGENTS.md (Testes), não deste código.
