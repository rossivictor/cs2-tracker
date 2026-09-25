# M4 — Seletor de lineups

> **Depende de:** M1, M3 · **Bloqueia:** M7
> **Entrega:** montar "eu + donk + ZywOo contra a FURIA" no browser.

A tela mais interativa do app, e a que expressa a proposta de valor. As restrições
de unicidade de nome (SPEC.md §10) são regra de UI aqui, não detalhe de backend.

---

## F4.1 — API do catálogo

### Objetivo

Expor o catálogo da F1.1 pro front, com busca e filtro feitos no servidor.

### Comportamento

- Listar times com nome, logo e os cinco jogadores
- Listar perfis com nome, time de origem, função, arma preferida e uma leitura de
  estilo derivada do template (`ProTop`, `SniperPure`, `FastshotPersonality` → *"AWPer
  agressivo, reação rápida"*)
- Busca por texto e filtro por time, função e arma, resolvidos no servidor —
  o front não carrega o catálogo inteiro
- Times com perfil ausente no VPK não aparecem (F1.1)

### Critério de aceite

- Buscar "awp" devolve os AWPers; buscar "furia" devolve o time e seus jogadores
- A leitura de estilo é derivada do template, nunca escrita à mão por jogador
- A listagem responde rápido o bastante pra busca enquanto digita

---

## F4.2 — Seletor de duas lineups

### Objetivo

Preencher as vagas dos dois times respeitando a unicidade global de nomes.

### Comportamento

Dois painéis — **seu time** e **adversário** — cada um com vagas conforme o
`team_size`. Sua primeira vaga é você e não é editável.

Cada painel aceita três modos:

| Modo | Efeito |
|---|---|
| Time pronto | Preenche as vagas com um roster do catálogo |
| Manual | Vaga a vaga, pelos cards |
| Aleatório | Sorteia entre os perfis válidos |

**Pool compartilhado (regra dura).** Nomes são únicos no servidor inteiro, sem
distinção de time (SPEC.md §10, restrição 1). Então:

- Escolher um perfil de um lado o **desabilita do outro**
- Escolher um time pronto cujo jogador já está do outro lado avisa o conflito e
  pede resolução — não resolve sozinho em silêncio
- O **nick do jogador** sai do pool: se o seu nick for igual a um perfil, aquele
  perfil fica indisponível, com explicação
- Sorteio aleatório nunca produz colisão

**Validação antes de avançar:** todas as vagas preenchidas, nenhum nome repetido,
todos os perfis existentes no VPK.

### Critério de aceite

- Escolher `ZywOo` no seu time o desabilita na lista do adversário
- Escolher "Vitality" como adversário quando `ZywOo` já está do seu lado produz aviso
  explícito, não um 4v5 silencioso
- Um jogador com nick `donk` não consegue escolher o perfil `donk` e entende por quê
- 1x1 até 5x5 funcionam, com o número certo de vagas

---

## F4.3 — Presets

### Objetivo

Os três modos da SPEC.md §5 como atalho de um clique, sem virar caminho de código
separado.

### Comportamento

Três botões que apenas **pré-preenchem** os dois seletores e deixam tudo editável:

| Preset | Efeito |
|---|---|
| Ao lado dos ídolos | Seu time em modo manual, adversário aleatório |
| Contra um time real | Adversário em modo time pronto, seu time aleatório |
| Pros aleatórios | Os dois lados sorteados |

Nenhum preset trava nada. Depois de clicar, o jogador pode mudar qualquer vaga.

### Critério de aceite

- Cada preset deixa os dois painéis num estado válido e editável
- Não existe caminho de código que um preset percorra e a montagem manual não
- Editar depois de um preset não perde o que já estava preenchido

---

## F4.4 — Nome e logo do time no jogo

### Objetivo

Fazer o placar do CS2 refletir o que foi montado na tela.

### Comportamento

- `mp_teamname_1` recebe o nome do seu time (o seu nick, ou o roster escolhido)
- `mp_teamname_2` e `mp_teamlogo_2` recebem o time adversário
- Lineup montada manualmente, sem time de origem, usa um rótulo neutro
- No `match_config`, `team1.name` continua saindo da identidade
  ([wizard_core.py:132](../../wizard_core.py)) — resolver a sobreposição entre esse
  campo e o `mp_teamname_1`

### Critério de aceite

- Jogar contra a FURIA mostra FURIA e o logo dela no placar
- Uma lineup manual não mostra nome de time errado herdado da partida anterior
