# M7 — Acabamento

> **Depende de:** M4, M6
> **Entrega:** o veto ganha personalidade, a revanche fica a um clique, e a TUI sai de cena.

Nada aqui é essencial pra jogar. Tudo aqui é o que faz o produto parecer acabado.

---

## F7.1 — Veto com preferência real

### Objetivo

Trocar o `random.choice` do adversário ([wizard_core.py:104](../../wizard_core.py))
por escolha ponderada pelos dados reais de veto do time.

### Contexto

O comentário do próprio código admite que o veto do bot é ritmo, não decisão. Com
times nomeados e os dados da SPEC.md §7, os passos do adversário passam a refletir
o comportamento real do time.

### Comportamento

- **Passo de ban:** sorteio ponderado pelo `ban_pct` dos mapas restantes
- **Passo de pick:** sorteio ponderado pelo `pick_pct` dos mapas restantes
- **Primeiro ban / primeiro pick:** mapas marcados `first_ban`/`first_pick` ganham
  reforço no passo correspondente
- **Piso de peso:** todo mapa mantém probabilidade mínima — a sequência nunca é
  determinística, senão o veto perde a graça que justificou existir (D9)
- **Sem dados:** time sem bloco `veto` cai no aleatório uniforme de hoje
- A tela nomeia quem agiu: "FURIA baniu Ancient"

Tomando a FURIA como exemplo (SPEC.md §7): Ancient 61% de ban e marcado *first ban*,
Anubis 59% de ban com 0% de vitória, Mirage 33% de pick e marcado *first pick*.
O veto resultante é reconhecível sem ser previsível.

### Critério de aceite

- Rodando muitos vetos da FURIA, Ancient e Anubis dominam os bans e Mirage os picks
- Nenhum mapa é impossível de sair
- Time sem dados de veto continua funcionando
- O snapshot vencido (SPEC.md §7: validade de 2 a 3 meses) é sinalizado na tela,
  não silenciosamente usado como se fosse atual

---

## F7.2 — Repetir última partida

### Objetivo

Um clique pra revanche (D22).

### Comportamento

- Botão na tela inicial e no fim do relatório
- Pré-preenche formato, tamanho de time, lineups e mapas a partir da última partida
- **Pré-preenche, não dispara** — tudo continua editável antes de iniciar
- Sem histórico, o botão não aparece
- Se um perfil da última partida não existir mais no catálogo, avisa e deixa a vaga
  em aberto em vez de falhar

### Critério de aceite

- Repetir uma partida contra a FURIA reconstitui as dez vagas e o formato
- Editar depois de repetir funciona normalmente
- Primeira execução do app, sem histórico, não mostra o botão

---

## F7.3 — Aposentar a TUI

### Objetivo

Remover o `wizard_tui.py` (902 linhas) agora que o web tem paridade e o CLI cobre
o headless.

### Pré-condições

Não é um delete de rotina. Antes:

- O app web fez pelo menos uma série MD3 completa, de ponta a ponta, em uso real
- O CLI da F1.4 sobe partida sem browser
- Nada em `wizard_core.py` ou `start_match.py` ainda importa do `wizard_tui`

### Comportamento

- `wizard_tui.py` removido
- `textual` sai do `requirements.txt`
- README reescrito: o ponto de entrada passa a ser `docker compose up -d` + o app web
- Os SVGs de `docs/img/` que mostram as telas do Textual saem ou são refeitos

### Critério de aceite

- `grep -r wizard_tui` não retorna nada fora do histórico do git
- O README descreve o fluxo real, sem menção à TUI
- Instalar do zero pelo README leva a uma partida funcionando

### Observação

A TUI é o caminho conhecido-bom. Aposentá-la cedo demais troca uma coisa que
funciona por uma que ainda não foi testada em uso real — por isso este é o último
item do último milestone.
