"""`python -m tools.board <comando>`: ver `tools/board/cli.py`."""
import sys

from tools.board.cli import main

# Em pipe (Git Bash, ferramenta do agente) o padrão seria cp1252, e "→" e
# "ç" quebrariam a saída. Console de verdade já recebe Unicode. Linha a linha,
# para o aviso do stderr não sair antes do cabeçalho do stdout no pipe.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        if _fluxo.isatty():
            _fluxo.reconfigure(errors="replace")
        else:
            _fluxo.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except (AttributeError, ValueError, OSError):
        pass

sys.exit(main())
