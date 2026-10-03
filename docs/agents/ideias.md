---
tipo: referencia
status: vigente
fontes:
  - "PR #39"
  - "PR #46"
atualizado: 2026-10-03
---

# Ideias que ainda não viraram card

Sugestões dos QAs e dos papéis que ficaram fora dos critérios. Antes de virar card, cada uma passa pelo Victor. Quando virar card, sai daqui com o ID dele.

## Harness e janela

- O `vigiar` poderia tratar o `claude.exe` do app e os shells interativos como processo de sessão, não como raiz da árvore do servidor (QA do B0.7e).
- Faltam testes no `vigiar` para "PID cego que volta legível na releitura" e "cs2.exe que aparece só na releitura" (QA do B0.7e).
- `tools/evidencia_partida.py`: recusar com saída 2 quando o `--partida` termina em `.dem` e ler a build e as versões do log desde o StartedAt; hoje sai "Metamod ? · CSSharp ? · build ?" (QA do G7 do B0.8).
- Gravar no registro de janela o comando exato do `docker run :ro` que lê `overrides/` (QA do B0.9).

## Guarda

- Limites do B0.5e ainda não listados um a um no docstring: `-Destination (Join-Path ...)`, `cp -s`, `Copy-Item -Recurse -Des`, `ln -s` (QA do B0.5e).

## KB

- Citações por número de linha que andaram com os diffs (ADR-0005 em `trilha-de-bots.md`; ADR-0003, ADR-0004, `docs/README.md` e `politica-de-comentarios.md` no `AGENTS.md`; notas que citam `versoes-conhecidas.md`), sem teste que as pegue.
- Textos antigos de "volume novo e vazio": `docs/runbooks/b1.3-cssharp-1.0.375.md`, `trilha-de-bots.md`, comentários de `tools/jogavel.py` e `tests/test_jogavel.py`.
- `docs/runbooks/README.md` ainda lista `inventario-volume` em "Previstos".
- Procedimento para reaplicar o contador de matchid da MatchZy se o volume for reconstruído da semente (QA do B0.9).

## Dados

- A partida 40 (events_74_map0) tem 13 rounds distintos em `round_stats` para 14 contados; talvez o último round só na cauda do `current.jsonl` (QA do G7 do B0.8; P1).
- `events_50_map0` sem linha no banco e `demo_path` divergente em `events_45_map2` (V1).
