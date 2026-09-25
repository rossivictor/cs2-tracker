# M5 — Confiabilidade do início

> **Depende de:** M3 · **Independente do M6**
> **Entrega:** o warmup travado deixa de exigir intervenção, e passa a deixar rastro.

O warmup às vezes trava e a causa raiz é desconhecida. Este milestone não a resolve —
ele torna o sintoma raro pro jogador e acumula a evidência pra atacar a causa depois.

---

## F5.1 — Auto-retry do início

### Objetivo

Repetir `css_start` + rebalanceamento automaticamente antes de pedir socorro ao
jogador.

### Contexto

Hoje o remédio é o botão manual **Forçar início / rebalancear bots**
([wizard_tui.py:693](../../wizard_tui.py)), que repete a sequência de
`force_start_and_balance_bots`. As peças de detecção já existem:
`wait_for_team_snapshot` lê o estado real dos times do `docker logs`
([start_match.py:139](../../start_match.py)) e `wait_for_next_map_warmup` detecta
warmup ([start_match.py:263](../../start_match.py)).

### Comportamento

- Condição de disparo: passou o tempo esperado, todos os clientes esperados estão
  conectados, e o jogo continua em warmup
- Até **2 tentativas** automáticas, espaçadas, cada uma anunciada no log em
  linguagem clara ("O início não pegou, tentando de novo (1/2)")
- Depois das duas, para de tentar e destaca o botão manual, que continua existindo
- Vale em **todo mapa da série**, não só no primeiro — é entre mapas que o problema
  mais apareceu ([start_match.py:456](../../start_match.py))
- Cada tentativa serializa pelo `rcon_lock`, sem concorrer com o botão manual

### Critério de aceite

- Um início travado se resolve sozinho, com o jogador só vendo a mensagem
- Depois de 2 falhas, o app para de tentar e diz o que fazer
- Apertar o botão manual durante um retry automático não dispara duas sequências
- Um início que funciona de primeira não dispara retry nenhum

---

## F5.2 — Telemetria do warmup

### Objetivo

Registrar cada ocorrência com contexto suficiente pra diagnosticar a causa depois.

### Contexto

Hoje o remédio é manual e **não deixa rastro**: não há registro de quando foi preciso,
nem do estado do servidor no momento. Sem isso, investigar a causa raiz é adivinhação
— foi o que já não funcionou.

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

### Critério de aceite

- Todo disparo gera exatamente um registro
- O registro basta pra reconstruir o que acontecia, sem ter o container no ar
- Uma sessão de uso real produz um corpus consultável por mapa e por posição na série
- Nenhum dado de diagnóstico vaza pro `report`

### Resultado esperado

Depois de algumas semanas de uso, ter uma resposta empírica pra: acontece mais no
mapa 2+? Está correlacionado com contagem errada de clientes? Bots nomeados pioram?
Isso é o insumo pra atacar a causa — item aberto na SPEC.md §15.
