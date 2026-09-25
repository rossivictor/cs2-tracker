# M6 — Estatísticas

> **Depende de:** M3 · **Independente do M5** · **Bloqueia:** M7
> **Entrega:** "meu K/D contra o ZywOo" e "primeira vitória contra a FURIA".

Sem head-to-head, o nome do pro é enfeite. Este é o milestone que dá peso ao nome —
e é barato, porque **o dado já está no banco**: `kills` e `damages` guardam
`attacker_name`/`victim_name` com flag `is_human`. Nenhuma migração de schema.

---

## F6.1 — `report.py` como camada de consulta

### Objetivo

Transformar o gerador de HTML estático numa camada de consulta que o app consome.

### Contexto

**Metade disto já aconteceu, adiantado e por outro motivo.** Pra unificar a home
([M3.5](M3.5-home.md)) com o relatório sem esperar o M3 existir, as funções de cálculo
— `_stats_for_round_nums` e companhia — já saíram de `report.py` e viraram `stats.py`,
um módulo de consulta puro (SQLite -> dict) sem HTML nenhum, hoje consumido por
`report.py` **e** por `home.py`. O que falta desta feature não é mais extrair o
cálculo — é o app (`web/`) passar a chamar `stats.py` direto, e então **aposentar os
dois geradores estáticos** (`report.py` e `home.py`), não só o antigo `report.py`.

### Comportamento

- `stats.py` ganha parâmetros de filtro (por perfil, por período) que hoje não tem —
  hoje só serve consultas "tudo" ou "por partida"
- O app (`web/`) passa a chamar `stats.py`; os geradores estáticos (`report.py`,
  `home.py`) são aposentados
- As estatísticas existentes são preservadas integralmente: K/D, HS%, ADR, entry,
  streak, leaderboard por mapa, por bombsite, recordes pessoais, timeline, kill feed
- Partidas vindas de CSV continuam degradando como hoje (sem ADR)

### Arquivos

| Arquivo | Ação |
|---|---|
| `stats.py` | ✅ já existe — ganha parâmetros de filtro novos |
| `report.py`, `home.py` | Geração de HTML removida (aposentados) |
| `web/` | Telas de estatística, consumindo `stats.py` |

### Critério de aceite

- Toda estatística que `report.html`/`index.html` mostram hoje está no app
- Nenhum arquivo HTML é gerado por script — só pelo app, sob demanda
- Uma consulta aceita filtro por partida, por período e por adversário

### Estado — 21/09/2026 🟡

Entregue: as duas telas novas (`GET /partidas` e `GET /partidas/<id>`, contexto em
`matches.py`, templates `matches.html` / `match_detail.html`), renderizadas no
servidor a partir de `stats.py`. A barra de navegação aponta pra elas. Filtro por
lado e por mapa funcionando.

`stats.py` ganhou as derivadas que faltavam, todas do dado que já estava gravado:
**KAST**, **trades**, **multi-kills**, **clutches 1vX**, **regiões de acerto**
(`damages.hitgroup`, que nunca tinha sido lido) e **head-to-head por adversário**
(a F6.2 abaixo, na versão por partida). `stats.match_positions` cruza
`player_positions` com `kills.tick` e alimenta o radar da aba Mapa. As tabelas
filhas ganharam índice por `match_id` em `parser.INDEXES` — não havia nenhum.

**Não entregue de propósito:**

- `report.py` e `home.py` **não** foram aposentados. `/report` continua de pé porque
  é o mesmo código que gera o `report.html` estático, o único caminho que funciona
  offline via `file://`. Sai de cena quando `/partidas` provar paridade em uso real.
- Filtro por período e por adversário ainda não existem (só lado e mapa).

### Economia e flash — 21/09/2026 ✅

`parser.PLAYER_PROPS` passou a ser pedido no `dem.parse()`. Até então o parse era
feito sem argumento nenhum, e o awpy extraía só 6 propriedades
(`last_place_name`, `X`, `Y`, `Z`, `health`, `team_name`) — flash, valor de
equipamento e colete eram descartados na ingestão, sem aviso.

Entrou no schema: `rounds.freeze_end_tick` e, em `player_positions`,
`flash_duration`, `equip_value`, `armor`, `has_helmet`, `has_defuser`. A leitura é
`stats.match_loadout`, e a tela de partida ganhou a coluna de economia na linha do
tempo (eco/force/full com o valor) mais o resumo de compra e tempo cego.

`tools/reingest_demos.py` reprocessa as partidas de origem `demo` que já estão no
banco. Não dá pra reconstruir esses campos sem reler a demo.

**A nota do topo de `parser.py` sobre economia estava desatualizada** e foi
corrigida: dinheiro o awpy realmente não expõe, mas `current_equip_value` sim.

**Limite que apareceu ao implementar, e que muda o que dá pra fazer:** nesta demo
**só o humano aparece em `dem.ticks`** — os bots não entram no stream de ticks.
Então não existe economia do time nem do adversário, e a barra por round é a **sua
compra**, não a comparação entre os dois lados que um tracker de matchmaking mostra.
Pelo mesmo motivo, "inimigos cegados por você" continua fora: sem os ticks dos bots
não há a quem atribuir a flash.

**Limites que as telas mostram explicitamente**, em vez de esconder:

- Partidas ingeridas de `.dem` saem sem **trade**, **clutch** e **head-to-head**: o
  dataframe de kills do awpy não traz lado nem nome dos bots. As do plugin têm os dois.
- KAST é K/S/T, sem assist — nenhuma das duas fontes de ingestão traz assistente.
- O radar não tem imagem de mapa (não existe em `static/`): os pontos são
  normalizados pela área percorrida na partida.
- M4A4/M4A1-S e P2000/USP-S aparecem juntas no quadro de armas: a demo registra a
  morte com o nome da arma silenciada e o dano com o da versão base
  (`stats.WEAPON_CANONICAL`). Antes disso a linha saía com kills e dano zero.
- Economia e tempo cego só aparecem nas partidas de origem `demo` reprocessadas
  depois de `PLAYER_PROPS`. As de origem `events` dizem isso na própria aba de
  rounds em vez de mostrar zero.

### Em aberto: as 39 demos não ingeridas

`docker/demos-live/` tem 39 `.dem` (matchids 11 a 48). As de matchid 40–48 são as
**mesmas partidas** que já estão no banco pelo caminho do plugin (`events_40` a
`events_48`) — ingeri-las criaria uma segunda linha pra cada uma, com placar e K/D
contados duas vezes. As de 11 a 39 são histórico que nunca foi ingerido por caminho
nenhum.

Importar isso exige deduplicação por matchid e uma decisão sobre qual fonte ganha
quando as duas existem (a demo é mais rica: tem posição, economia e flash; o plugin
tem lado e nome dos bots, que a demo não tem). Por isso `tools/reingest_demos.py`
**só** toca partidas que já existem no banco com `source='demo'`, e não varre pasta
atrás de arquivo novo.

---

## F6.2 — Head-to-head por perfil

### Objetivo

Estatística cruzada entre você e cada pro que você já enfrentou ou com quem jogou.

### Comportamento

**Contra um adversário:**

- Duelos ganhos e perdidos, K/D contra aquele perfil
- Dano causado e sofrido
- Arma mais usada por ele contra você
- Partidas em que se enfrentaram

**Contra um time:** o mesmo, agregado pelos cinco perfis do roster — "seu retrospecto
contra a FURIA".

**Com um companheiro:** quantas partidas ao lado dele, e o resultado — o outro lado
da fantasia, que a fonte de dados já permite.

### Contexto de implementação

`kills` e `damages` já têm `attacker_name`, `victim_name`, `attacker_is_human`,
`victim_is_human` e o lado. O que falta é agrupar por nome de bot em vez de descartar.
Cuidado: bots stock (Ava, Osiris) convivem no histórico com perfis pro — as partidas
antigas são todas stock. A tela precisa lidar com isso sem parecer quebrada.

### Critério de aceite

- Uma tela de adversário mostra o retrospecto contra aquele perfil
- O agregado por time bate com a soma dos cinco jogadores
- Partidas antigas, com bots stock, aparecem sem erro e sem poluir a lista de pros
- Um perfil nunca enfrentado não aparece, ou aparece explicitamente zerado

---

## F6.3 — Marcos

### Objetivo

Dar sensação de progressão sem ELO nem nível (D21).

### Contexto

Não existe escala de força pra calibrar rating: todo perfil pro tem `Skill = 100`
(SPEC.md §10, restrição 5). Marcos derivam do histórico e não precisam de modelo.

### Comportamento

Conquistas calculadas sobre o banco, não armazenadas como estado — recalcular é
barato e evita inconsistência:

| Categoria | Exemplos |
|---|---|
| Primeiras vezes | Primeira vitória contra um time, primeira partida ao lado de um ídolo |
| Volume | N partidas, N rounds de entry ganhos, N times diferentes enfrentados |
| Desempenho | Primeiro 30-bomb, melhor ADR, maior sequência de abates |
| Coleção | Enfrentou todos os jogadores de um time, jogou em todos os mapas do pool |

Marcos novos aparecem destacados no relatório logo depois da partida que os
desbloqueou.

### Critério de aceite

- Os marcos são derivados por consulta, sem tabela de estado
- Recalcular sobre o mesmo banco dá sempre o mesmo resultado
- O histórico existente (partidas contra bots stock) produz marcos coerentes, sem
  atribuir vitórias a times que nunca foram enfrentados
- Um marco recém-desbloqueado é identificável como novo
