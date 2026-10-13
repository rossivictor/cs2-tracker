---
tipo: adr
status: aceito
aliases: [ADR-0013]
fontes:
  - "docs/SPEC.md:73-78 (Lineups: dois seletores e os três presets)"
  - "docs/SPEC.md:89-92 (pool compartilhado)"
  - "docs/SPEC.md:349 (D17)"
  - "web/app.py:309-336 (pool compartilhado na busca de perfil)"
  - "web/app.py:403-419 (rota /lineups/pick, vaga a vaga)"
  - "web/app.py:457-463 (grade de logos substitui a lineup)"
  - "web/app.py:486-488 (rota /lineups/select-team)"
  - "web/app.py:513-523 (rota /lineups/random-team)"
  - "web/app.py:516-518 (sorteio de time no lugar dos presets)"
  - "web/templates/lineups.html:83-108 (macro da grade de logos)"
  - "web/templates/lineups.html:119-121 (Seu time e Adversário)"
  - "web/templates/lineups.html:126-129 (botão Sortear 1 time)"
  - "web/templates/lineups.html:237 (grade de logos do adversário)"
  - "commit f6a4e6b"
atualizado: 2026-10-13
---

# ADR-0013: No wizard do browser, a grade de logos e o sorteio de time substituem os presets como atalho

## Contexto

A D17 da SPEC (19–20/09) decidiu "dois seletores + presets como atalho, com pool compartilhado" (`docs/SPEC.md:349`). O passo Lineups tinha dois seletores, **seu time** e **adversário**, e três presets de um clique que pré-preenchiam os dois lados: *Ao lado dos ídolos*, *Contra um time real* e *Pros aleatórios* (`docs/SPEC.md:73-78`). Os dois seletores compartilham um pool, porque o engine exige nome único no servidor inteiro (`docs/SPEC.md:89-92`).

No redesenho pedido em 20/09, os presets saíram do wizard do browser, e entraram a grade de logos e o sorteio de time, como registram as docstrings de `web/app.py:457-463` e `web/app.py:516-518`. A web entrou no repo em 25/09 já redesenhada (`f6a4e6b`), então o histórico do git não mostra código de preset: os presets só aparecem na SPEC e nessas docstrings. O K1.6 marcou a D17 como "parcialmente superada, sem ADR".

## Decisão

- **Os dois seletores ficam, com pool compartilhado.** O passo Lineups do browser mostra o painel "Seu time" e o painel "Adversário" (`web/templates/lineups.html:119-121`). A busca de perfil de uma vaga exclui os nomes já usados em qualquer vaga dos dois lados, menos a própria, e o nick do humano (`web/app.py:309-336`).
- **A grade de logos é o atalho de "time pronto".** Cada lado tem a sua grade (`web/templates/lineups.html:83-108`, usada para o seu time em `:119` e para o adversário em `:237`). O clique num logo **substitui** a lineup inteira daquele lado pelo roster do time, sem somar ao que já estava lá; a vaga cujo jogador colide com o outro lado ou com o nick do humano fica vazia e é avisada (`web/app.py:457-463`, rota em `web/app.py:486-488`).
- **O sorteio de time é o atalho do acaso.** "Sortear 1 time" (`web/templates/lineups.html:126-129`) faz o mesmo que o clique num logo, com o time sorteado entre os válidos, e devolve a imprevisibilidade que os presets tinham (`web/app.py:516-518`, rota em `web/app.py:513-523`).
- **Os presets não voltam como atalho** no wizard do browser. Não há preset no código no HEAD deste ADR.
- **Depois de qualquer atalho, cada vaga continua editável**, como nos presets da SPEC: escolher um perfil na vaga passa pela mesma regra do pool e recusa o nick do humano (`web/app.py:403-419`).

## Alternativas consideradas

- **Manter os presets como atalho** (o texto original da D17, `docs/SPEC.md:74-78`): o redesenho de 20/09 os tirou, e o Victor ficou com a grade e o sorteio ao escolher a opção (a) da D17 em 13/10. O porquê do redesenho não está registrado além das docstrings; que a grade cubra o *Contra um time real* e o sorteio, os *Pros aleatórios*, é dedução do escritor do K1.11.
- **Grade que soma à lineup em vez de substituir**: a docstring de `web/app.py:457-463` registra o contrário. Escolher outro time troca a lineup inteira.

## Consequências

- A D17 passa a valer com este ADR: a §12 da SPEC a marca como "vigente com o ADR-0013" e mantém o texto original da decisão.
- Este ADR fala só do wizard do browser. A TUI (`wizard_tui.py`) segue viva e sem diff até a D13 (AGENTS.md), e não entra aqui.
- O pool compartilhado continua sendo regra dura do engine: atalho novo de lineup tem de passar pela mesma exclusão de nomes (`web/app.py:309-336`).
- Reintroduzir preset, ou trocar a grade ou o sorteio por outro atalho, é decisão nova: ADR novo, que substitui este.

## Status

Aceito em 13/10/2026 pelo Victor, na conversa com o PM depois de ler o resumo de cada ADR: "confirmo os ADRs, D17 opção a" (repassado pelo card K1.11). A opção (a) é a grade de logos + o sorteio de time valendo como decisão no lugar dos presets.

## Fontes

- `docs/SPEC.md`: a D17 original, os presets e o pool compartilhado.
- `web/app.py` e `web/templates/lineups.html` no HEAD do K1.11: o que o wizard do browser faz hoje.
- Commit `f6a4e6b`: a web entrou no repo já com a grade e o sorteio.
