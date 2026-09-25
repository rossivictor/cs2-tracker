# M2 — Núcleo desacoplado da UI

> **Depende de:** nada · **Bloqueia:** M3
> **Entrega:** o estado do wizard e o log da partida deixam de depender do Textual.
> **Pode rodar em paralelo com M0 e M1.**

Puro refactor do que já existe. Nenhum comportamento novo — a TUI continua
funcionando idêntica ao fim do milestone, agora por cima do núcleo extraído.

---

## F2.1 — `WizardSession`

### Objetivo

Tirar o estado do wizard de dentro das telas do Textual e colocá-lo num objeto
testável, sem UI.

### Contexto

Hoje o estado está espalhado entre atributos do `WizardApp` (`identity`, `format`,
`team_size`, `setup_maps` — [wizard_tui.py:856](../../wizard_tui.py)) e a pilha de
telas. O "voltar" é `pop_screen` com regras ad-hoc: o `SideScreen.action_back`
pula a tela de veto ([wizard_tui.py:536](../../wizard_tui.py)). Browser não tem pilha
de telas, então essas regras precisam virar transições explícitas.

### Comportamento

Um objeto que guarda:

- Passo atual, e quais passos já foram resolvidos
- Identidade, formato, tamanho de time
- Pool de mapas restante, sequência de veto, índice do passo, histórico
- Mapas escolhidos com lado
- (M1) as duas lineups

E expõe transições nomeadas — `set_format`, `ban_map`, `pick_map`, `set_side`,
`back` — cada uma validando a pré-condição e recusando transição inválida.
`back` é explícito e sabe pular passos que não se aplicam (ex.: voltar de lados
pra veto ou pra escolha direta, conforme o caminho tomado).

### Arquivos

| Arquivo | Ação |
|---|---|
| `wizard_core.py` | 🆕 `WizardSession` |
| `wizard_tui.py` | Telas passam a ler/escrever na sessão em vez de nos atributos do app |
| `tests/` | 🆕 testes das transições, sem UI |

### Critério de aceite

- A TUI funciona exatamente como antes, incluindo o caso do voltar que pula a tela
  de veto
- Existe teste que percorre MD1, MD3 e MD5 pelos dois caminhos (escolha direta e
  veto) sem instanciar nada de Textual
- Transição inválida (ex.: banir mapa fora do passo de ban) é recusada com erro claro

---

## F2.2 — Sink de log explícito

### Objetivo

Trocar o `contextlib.redirect_stdout`, que é global do processo, por um sink
passado explicitamente.

### Contexto

A tela de launch captura a saída do `run_match` redirecionando o stdout do processo
inteiro ([wizard_tui.py:742](../../wizard_tui.py)). Isso funciona numa TUI de um
processo só. Num servidor web, engole o log do próprio servidor — e quebra se
houver mais de uma partida no processo.

São três pontos em que o núcleo fala com o terminal por conta própria:

| Ponto | Hoje | Depois |
|---|---|---|
| `print()` dentro do `run_match` | Capturado por `redirect_stdout` | Parâmetro `log=` recebido e usado explicitamente |
| `confirm_ready` | `threading.Event` esperado numa worker thread ([wizard_tui.py:660](../../wizard_tui.py)) | Continua sendo um callback — quem chama decide como confirmar |
| `watcher_output` | Já é callback | Sem mudança |

### Comportamento

- `run_match` e as funções que ele chama recebem um sink e escrevem nele
- Sem sink, o padrão é escrever no stdout — o CLI da F1.4 continua funcionando
- Nenhum `redirect_stdout` sobra no código

### Arquivos

| Arquivo | Ação |
|---|---|
| `start_match.py` | `run_match` e auxiliares recebem e usam o sink |
| `wizard_core.py` | `launch`/`force_start` repassam o sink |
| `wizard_tui.py` | Passa um sink que escreve no `RichLog`, sem redirecionar stdout |

### Critério de aceite

- `grep redirect_stdout` não retorna nada
- A TUI mostra o log do launcher e do watcher no mesmo painel, como antes
- O CLI da F1.4 imprime no terminal sem receber sink nenhum
- Duas chamadas simultâneas a `run_match` com sinks diferentes não misturam saída
