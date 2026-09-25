# M1 — Lineups nomeadas (headless)

> **Depende de:** M0 · **Bloqueia:** M3 (parcialmente), M4
> **Entrega:** `python start_match.py --enemy-team furia --format bo3` sobe uma
> partida contra os cinco pros certos, com nome de time no placar.

Este é o milestone que entrega a proposta de valor inteira. Nenhum front envolvido:
se a fantasia de jogar contra a FURIA não funcionar aqui, ela não vai funcionar
com uma tela bonita em cima.

---

## F1.1 — Catálogo de rosters

### Objetivo

Ter os times e seus perfis como **dado versionado**, validável contra o que o
servidor realmente tem.

### Escopo

- `data/rosters.json` no schema da SPEC.md §7
- `roster.py`: carregar, consultar por id, listar, validar
- Transcrição inicial dos times a partir do `Commands.txt` do CS2-Bot-Improver
  (é a fonte dos nomes de perfil que **de fato existem** no VPK)
- Campo `veto` opcional por enquanto — só a FURIA tem números (M7 consome isso)

### Comportamento

- `load_rosters()` lê o JSON e devolve objetos tipados
- `validate_against_server(profiles_disponiveis)` compara os `players` de cada time
  com a lista real de perfis e devolve os ausentes
- Um time com qualquer perfil ausente é marcado inválido e **não aparece** como
  opção — melhor sumir do catálogo do que falhar no meio do `bot_add`
- `display_name` é sempre o que se mostra; `players` é sempre o que se envia ao servidor

### Arquivos

| Arquivo | Ação |
|---|---|
| `data/rosters.json` | 🆕 |
| `roster.py` | 🆕 |

### Critério de aceite

- Pelo menos 10 times carregados, entre eles FURIA, Vitality, NAVI, G2, Spirit, MOUZ
- `validate_against_server` acusa perfil inexistente antes de qualquer partida
- Um time com nome de perfil errado é reprovado e não aparece na listagem
- Trocar todos os `display_name` por nomes genéricos não exige mudar código nenhum

---

## F1.2 — Adição de bots por nome

### Objetivo

Substituir os `bot_add_ct`/`bot_add_t` anônimos de
[start_match.py:222](../../start_match.py) por adição por perfil, respeitando as
restrições do engine.

### Comportamento

**Ordem correta de comandos** (SPEC.md §10, restrição 3):

```
bot_quota_mode normal
bot_quota 0
bot_kick
<adds nomeados, intercalando CT e T>
mp_teamname_1 / mp_teamname_2 / mp_teamlogo_*
```

Depois dos adds **não se re-emite `bot_quota`** — cada add bem-sucedido já
incrementou a quota. Emitir de novo faz `MaintainBotQuota` chutar bot nomeado.

**Verificação pós-add:** um add que falha não incrementa a quota e não produz erro
visível pro app. Depois da sequência, conferir a contagem real por
`read_docker_team_snapshot` ([start_match.py:124](../../start_match.py)) e abortar com
mensagem clara se faltar alguém — nunca deixar o jogador entrar num 4v5 sem saber.

**Exclusão do nick humano:** se o nick do jogador colidir com um perfil da lineup,
o add falha silenciosamente. Validar antes e recusar com mensagem explícita.

### Arquivos

| Arquivo | Ação |
|---|---|
| `start_match.py` | `_force_start_and_balance_bots` recebe as lineups e emite adds nomeados |
| `wizard_core.py` | `MatchSetup` ganha `my_lineup` e `enemy_lineup` |

### Critério de aceite

- Um 5v5 sobe com os cinco nomes pedidos de cada lado, confirmado em `status` ou
  no `docker logs`
- Perfil inexistente na lineup ⇒ erro antes de subir a partida, não durante
- Nick do humano igual a um perfil da lineup ⇒ recusa com mensagem
- `fix_bot_overflow` continua funcionando (os clientes internos do MatchZy seguem
  aparecendo)

### Risco

`fix_bot_overflow` hoje chuta por nome ([start_match.py:160](../../start_match.py)).
Com bots nomeados, ele precisa distinguir "bot que eu pedi" de "cliente interno do
MatchZy" — chutar um pro por engano quebra a lineup em silêncio.

---

## F1.3 — Persistência da lineup na série

### Objetivo

Garantir que o mapa 2 de um MD3 tenha os mesmos pros do mapa 1.

### Contexto

Bots nomeados **não sobrevivem ao `changelevel`** (SPEC.md §10, restrição 4). Todos
os clientes caem e são recriados aleatoriamente pela quota. O repositório já
re-executa o balanceamento a cada mapa ([start_match.py:456](../../start_match.py))
justamente porque o `bot_quota_mode` reseta — falta passar os nomes nessa re-execução.

### Comportamento

- A lineup é propriedade da **série**, não do mapa
- A cada mapa, depois do `css_start` (que executa `live.cfg` e reseta os bots),
  re-adicionar por nome
- Se a re-adição falhar em algum mapa, avisar no log e oferecer o início manual

### Arquivos

| Arquivo | Ação |
|---|---|
| `start_match.py` | Laço de série repassa as lineups a cada mapa |

### Critério de aceite

- Um MD3 completo com os mesmos dez nomes nos três mapas, verificado a cada troca
- A verificação de contagem da F1.2 roda em todo mapa, não só no primeiro

---

## F1.4 — CLI de lineup

### Objetivo

Poder montar e subir qualquer partida pelo terminal — o caminho de depuração que
sobrevive à aposentadoria da TUI (D13).

### Escopo

Argumentos novos no `main()` do [start_match.py:509](../../start_match.py):

| Argumento | Efeito |
|---|---|
| `--enemy-team <id>` | Lineup adversária a partir do catálogo |
| `--my-team <id>` | Sua lineup a partir do catálogo (você ocupa uma vaga) |
| `--enemy <p1,p2,...>` | Lineup adversária perfil a perfil |
| `--mine <p1,p2,...>` | Seus companheiros perfil a perfil |
| `--random-enemy` / `--random-mine` | Sorteio dentre os perfis válidos |

Conflito entre `--enemy-team` e `--enemy` ⇒ erro. Lineup incompleta pro `team_size`
pedido ⇒ erro antes de subir nada.

### Critério de aceite

- `python start_match.py --enemy-team furia --format bo1 --map de_mirage` sobe uma
  partida contra os cinco jogadores da FURIA
- O placar do jogo mostra o nome e o logo do time adversário
- Pedir um time inválido lista os perfis ausentes e não sobe nada

### Por que isto importa

É o critério de saída do M1 e o momento de responder à pergunta da SPEC.md §13:
**é divertido?** Jogue algumas partidas aqui antes de investir no front.
