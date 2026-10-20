# M5 — Confiabilidade do início

> **Depende de:** M3 · **Independente do M6**
> **Status:** rebaixado em 20/10 (P1.12), com a D11 ([SPEC §12](../SPEC.md#12-decisões)):
> F5.1 e F5.2 não são decisão vigente e não têm card.
> **Entrega (original, de 20/09, não vigente):** o warmup travado deixa de exigir
> intervenção, e passa a deixar rastro.

Este milestone nasceu em 20/09 de "o warmup às vezes trava e a causa raiz é
desconhecida": não ia resolvê-la, só tornar o sintoma raro pro jogador (F5.1) e
acumular evidência pra atacar a causa depois (F5.2).

**A causa foi achada, e era de código.** O "warmup que trava" entre os mapas da série
vinha da espera pelo mapa seguinte no orquestrador (`wait_for_next_map_warmup`, em
`start_match.py`): o teto de 240 s contava do `css_start` do mapa 1 e vencia com ele
ainda em jogo, e o `docker logs --since` ia com a hora UTC sem fuso, lida pelo Docker
como hora local (3 h no futuro, em -03), e voltava vazio. Sobrava o botão manual em
todo mapa 2+. O P1.5 corrigiu os dois (`f6191a4`, PR #102), e a MD3 real de 20/10
(tag `jogavel-2026-10-20`) teve o mapa 2 começando sozinho. O detalhe está na
[SPEC §11](../SPEC.md#confiabilidade-do-início-de-partida).

Com a causa fechada, F5.1 e F5.2 ficaram **rebaixadas**: nunca foram implementadas,
saem da lista do que se vai construir e não têm card. O botão manual **Forçar início
/ rebalancear bots** da TUI segue como remédio para um início que não pegar.

**Quando voltam:** se, com o P1.5 no ar, um mapa da série voltar a ficar no warmup
sem começar sozinho, o sintoma tem outra causa, e F5.1 e F5.2 voltam a ser proposta,
por card novo e decisão do Victor. As seções abaixo ficam como registro do que foi
decidido em 20/09.

**O que não é deste milestone:** a queda do servidor de 04/10 na virada de série da
MD3 (segfault) não tem causa provada e não é o bug acima; retry nenhum a cobriria,
porque o processo morre. O estado dela fica no
[runbook do B1.12](../runbooks/b1.12-segfault-troca-de-mapa-md3.md) e na
[SPEC §15](../SPEC.md#15-em-aberto), junto com o crash do watchdog de 20/09.

---

## F5.1 — Auto-retry do início

> **Rebaixada em 20/10 (P1.12):** sem card e não vigente. O texto é o de 20/09; só o
> Contexto foi posto em dia.

### Objetivo

Repetir `css_start` + rebalanceamento automaticamente antes de pedir socorro ao
jogador.

### Contexto

Em 20/09 o remédio era o botão manual **Forçar início / rebalancear bots** (a
`LaunchScreen` do `wizard_tui.py`), que repete `force_start_and_balance_bots` por
`wizard_core.force_start`. Desde o P1.5, os mapas 2..N começam sozinhos (o laço do
`run_match`, em `start_match.py`), e o botão ficou para o início que não pegar. As
peças de detecção existem: `read_docker_team_snapshot` lê o estado real dos times do
`docker logs`, e `wait_for_next_map_warmup` detecta o warmup do mapa seguinte
(`[ChangeMap]` → `[FULL CONNECT]` → `[StartWarmup]`), lendo pelo `CursorDockerLogs`
(todos em `start_match.py`).

### Comportamento

- Condição de disparo: passou o tempo esperado, todos os clientes esperados estão
  conectados, e o jogo continua em warmup
- Até **2 tentativas** automáticas, espaçadas, cada uma anunciada no log em
  linguagem clara ("O início não pegou, tentando de novo (1/2)")
- Depois das duas, para de tentar e destaca o botão manual, que continua existindo
- Vale em **todo mapa da série**, não só no primeiro — é entre mapas que o problema
  mais apareceu (o laço dos mapas 2..N do `run_match`; era ali o bug corrigido no
  P1.5)
- Cada tentativa serializa pelo `rcon_lock`, sem concorrer com o botão manual

### Critério de aceite (histórico, não vigente)

- Um início travado se resolve sozinho, com o jogador só vendo a mensagem
- Depois de 2 falhas, o app para de tentar e diz o que fazer
- Apertar o botão manual durante um retry automático não dispara duas sequências
- Um início que funciona de primeira não dispara retry nenhum

---

## F5.2 — Telemetria do warmup

> **Rebaixada em 20/10 (P1.12):** sem card e não vigente. O texto é o de 20/09; só o
> Contexto e o Resultado esperado foram postos em dia.

### Objetivo

Registrar cada ocorrência com contexto suficiente pra diagnosticar a causa depois.

### Contexto

Em 20/09 o remédio era manual e **não deixava rastro**: não havia registro de quando
foi preciso, nem do estado do servidor no momento, e a aposta era que, sem isso,
investigar a causa raiz seria adivinhação. A causa acabou achada sem telemetria,
lendo o código da espera e o `docker logs` (P1.5). A telemetria nunca foi
implementada.

### Comportamento

Cada disparo (automático ou manual) grava um registro com:

| Campo | Por quê |
|---|---|
| Timestamp e tempo desde o `css_start` | Distinguir "demorou" de "travou" |
| Mapa e índice na série | O problema aparece mais na troca de mapa |
| Clientes conectados por time, do `docker logs` | Detectar 6x5, 4x5, cliente interno do MatchZy |
| Trecho relevante do `docker logs` | Evidência bruta |
| Tentativa nº e se resolveu | Medir eficácia do retry |
| Lineup em uso | Testar se bots nomeados mudam a frequência |

Destino: arquivo append-only em `docker/` (mesmo padrão resistente a crash do
`events-live/current.jsonl`), não o banco — é dado de diagnóstico, não de produto.

### Critério de aceite (histórico, não vigente)

- Todo disparo gera exatamente um registro
- O registro basta pra reconstruir o que acontecia, sem ter o container no ar
- Uma sessão de uso real produz um corpus consultável por mapa e por posição na série
- Nenhum dado de diagnóstico vaza pro `report`

### Resultado esperado (original, não vigente)

Em 20/09: depois de algumas semanas de uso, ter uma resposta empírica pra: acontece
mais no mapa 2+? Está correlacionado com contagem errada de clientes? Bots nomeados
pioram? Isso seria o insumo pra atacar a causa, então item aberto na SPEC §15.

A primeira pergunta foi respondida pelo código, sem corpus: a espera desistia em todo
mapa 2+ (P1.5), e o item da §15 fechou no P1.12. As outras duas só voltam se o
sintoma voltar, como no topo desta nota.
