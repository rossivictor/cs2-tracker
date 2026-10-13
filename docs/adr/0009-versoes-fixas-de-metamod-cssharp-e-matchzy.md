---
tipo: adr
status: aceito
aliases: [ADR-0009]
fontes:
  - "commit fde0ed5"
  - "commit 779a979"
  - "PR #4"
  - "docker-compose.yml:55-64"
  - "docs/armadilhas/imagem-e-boot.md:18-22 (item 1)"
  - "docs/runbooks/versoes-conhecidas.md:64-69 (o que não mudou em nenhuma tag)"
  - ".github/workflows/ci.yml:31-49 (job compose)"
atualizado: 2026-10-13
---

# ADR-0009: Metamod, CounterStrikeSharp e MatchZy com versão fixa no compose

## Contexto

A imagem `xbird/cs2-matchzy` ([ADR-0007](0007-servidor-dedicado-em-docker-com-matchzy.md)) baixa a versão mais nova de Metamod, CounterStrikeSharp e MatchZy a cada boot, sem checar compatibilidade. Em 11/09, depois de o container ficar parado alguns dias, entrou um Metamod com a interface de plugin 18, enquanto a CSSharp, o RayTrace e o BotHider instalados ainda eram da interface 17. O boot mostrou `[META] Loaded 0 plugins.`, e `matchzy_loadmatch` e `css_start` viraram comando desconhecido: sem MatchZy, não há partida (`fde0ed5`; item 1 em `docs/armadilhas/imagem-e-boot.md:18-22`).

## Decisão

- **As três versões ficam fixas no `docker-compose.yml`**, pelas variáveis da própria imagem: `MMSOURCE_FIXED_VERSION`, `CSSHARP_FIXED_VERSION` e `MATCHZY_FIXED_VERSION` (`docker-compose.yml:55-64`). Decidido no `fde0ed5` (11/09), com as versões que funcionavam naquela sessão.
- **Versão só muda por card, em janela, como degrau** ([ADR-0004](0004-jogo-sempre-jogavel.md)). Foi assim na única troca até hoje: Metamod 2.0.0.1411 e CSSharp v1.0.373 para 2.0.0.1469 e v1.0.375 (`779a979`, PR #4, B1.3r).
- **Metamod e CSSharp formam um par que não se separa** (a regra do par é do [ADR-0005](0005-trilha-de-bots-uma-variavel-por-vez.md)). A MatchZy segue na 0.8.15 desde o pin (`docs/runbooks/versoes-conhecidas.md:64-69`).
- **O que cada tag jogável rodou** fica em [versoes-conhecidas](../runbooks/versoes-conhecidas.md).

## Alternativas consideradas

- **Deixar a imagem atualizar sozinha**: foi o estado até 11/09, e derrubou MatchZy e captura.

## Consequências

- Atualização de addon nunca chega por acaso; chega por card, com download só com OK explícito (G5).
- O pin cobre só os addons. A imagem segue sem tag ([ADR-0007](0007-servidor-dedicado-em-docker-com-matchzy.md)), e o build do CS2 ainda pode subir no boot pelo SteamCMD sem OK prévio, como na troca para o VPK Low ([ADR-0005](0005-trilha-de-bots-uma-variavel-por-vez.md), Resultado).
- Verificação: o job `compose` do CI valida o modelo, e o G6 confere as linhas `complete` das versões no boot.

## Status

Aceito na prática desde 11/09/2026 (`fde0ed5`), na `main`. ADR retroativo, escrito pelo K1.6 em 13/10 a partir dos commits; confirmado pelo Victor em 13/10.

## Fontes

- Commit `fde0ed5`: o incidente e o pin. Commit `779a979` e PR #4: a troca do par pelo B1.3r.
- Compose, armadilha 1 e versões conhecidas: o estado de hoje.
