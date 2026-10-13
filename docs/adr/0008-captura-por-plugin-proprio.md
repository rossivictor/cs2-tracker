---
tipo: adr
status: aceito
aliases: [ADR-0008]
fontes:
  - "commit 193cd6c"
  - "commit 5adb8bc"
  - "commit b953406"
  - "commit 4c19249"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:52 (ModuleVersion 0.4.0)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:251-337 (fila e thread de escrita)"
  - "parser.py:992-1199 (store_match_from_events)"
  - "docs/arquitetura/contrato-events-jsonl.md:42-52"
  - "docs/armadilhas/legado-gotv-e-nativo.md:18-22 (item 53)"
  - "pyproject.toml:20-21 (awpy e polars, só para demos)"
  - "docs/agents/plano-2026-09-26.json:1655 (S1.2)"
  - "docs/agents/plano-2026-09-26.json:1809 (S1.10)"
  - "docs/agents/sprints.md:68 (S7)"
atualizado: 2026-10-13
---

# ADR-0008: A partida é capturada por plugin próprio, não pela demo

## Contexto

Até 25/09, as estatísticas saíam da demo do GOTV, lida com o awpy 2.0.2 (`5adb8bc`). O pipeline foi validado no servidor dedicado nativo (`b953406`) e quebrou quando o servidor virou container (`4c19249`): todas as demos desde então tinham ~1,5 s de conteúdo. As tentativas de conserto (`tv_delay`, `tv_transmitall`, `CS2_LAN`) foram descartadas uma a uma, com medição (`193cd6c`; item 53 em `docs/armadilhas/legado-gotv-e-nativo.md:18-22`). Além disso, o awpy não expõe dinheiro gasto em versão nenhuma.

## Decisão

Decidido no `193cd6c` (25/09):

- **O plugin `Cs2TrackerEvents`** (CounterStrikeSharp, hoje 0.4.0: `Cs2TrackerEventsPlugin.cs:52`) **lê o jogo pela API e grava a partida num JSONL**. O `parser.store_match_from_events` ingere esse arquivo no SQLite (`parser.py:992-1199`). O contrato está em [contrato-events-jsonl](../arquitetura/contrato-events-jsonl.md).
- **Cada dado vem do lugar mais barato:** evento para o que pertence a um instante (a kill com a posição no tique exato), fim de round para o que o engine já conta (`CSMatchStats_t`: entry, clutch, utility, economia) e amostragem por tique só para o trajeto, a 2 Hz.
- **O disco fica fora da thread do jogo:** fila em memória e thread própria de escrita (`Cs2TrackerEventsPlugin.cs:251-337`). A escrita direta no bind mount do Docker no Windows degradou até 99,9 ms de pico e derrubou o jogador com `NETWORK_DISCONNECT_OVERFLOW`; com a fila, 0,036 ms.
- **A demo deixa de ser fonte.** O que sobra dela é legado: o `tools/enrich_from_demos.py` sai no S1.2, e o bloco GOTV do cfg, no S1.10.

## Alternativas consideradas

- **Consertar a demo no Docker**: três tentativas medidas, nenhuma funcionou (`193cd6c`).
- **Voltar ao dedicado nativo para ter demo** (dedução do escritor do K1.6: nenhum commit registra esta alternativa): desfaria o [ADR-0007](0007-servidor-dedicado-em-docker-com-matchzy.md) e ainda ficaria sem dinheiro.

## Consequências

- O formato da captura é um contrato implícito entre C# e Python, sem versão na linha; o S7 (`docs/agents/sprints.md:68`) quer um schema v1 com arquivo por mapa.
- Plugin de captura é caminho de jogo: muda só em janela, com sha256 dentro do container igual ao checkout (G6).
- Enquanto a poda não chega, o awpy e o polars seguem nas dependências só por causa das demos (`pyproject.toml:20-21`), e é deles a trava do Python abaixo de 3.14 ([ADR-0011](0011-python-3-13-unico.md)).
- O roster de pros nomeados não depende de plugin de bot: vem do `bot_add_ct` com o perfil do VPK (SPEC, D2).

## Status

Aceito na prática desde 25/09/2026 (`193cd6c`), na `main`. ADR retroativo, escrito pelo K1.6 em 13/10 a partir dos commits; o texto não passou pela leitura do Victor.

## Fontes

- Commit `193cd6c`: o problema da demo, o desenho em três camadas e as medições de escrita.
- Commits `5adb8bc`, `b953406` e `4c19249`: o caminho anterior e onde ele quebrou.
- Plugin, `parser.py` e contrato do JSONL: o estado de hoje. Plano: S1.2 e S1.10.
