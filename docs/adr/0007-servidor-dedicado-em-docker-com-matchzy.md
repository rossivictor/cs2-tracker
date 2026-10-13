---
tipo: adr
status: aceito
aliases: [ADR-0007]
fontes:
  - "commit b953406"
  - "commit 4c19249"
  - "commit 8a3ff2f"
  - "commit 53f9abd"
  - "commit 193cd6c (escrita no bind mount degrada com o tamanho do arquivo)"
  - "watcher.py:13-20 (listen server sem RCON TCP)"
  - "docker/SPIKE.md:1-8 (a pergunta do spike e o plano B)"
  - "docker/SPIKE.md:10-21 (resultado e as duas ressalvas)"
  - "docker/SPIKE.md:46-52 (por que a imagem pronta)"
  - "docker-compose.yml:14-15"
  - "docker-compose.yml:189-191"
  - "start_match.py:535-539 (bots não contam como time pronto; css_start)"
  - "start_match.py:869 (matchzy_loadmatch)"
  - "docs/runbooks/versoes-conhecidas.md:68 (imagem sem tag no compose)"
  - "docs/armadilhas/legado-gotv-e-nativo.md:24-28 (item 54, modo nativo)"
  - "backup:temp-artifacts/eb5adec0/audit/arch.json (integracao: controle do jogo em três canais)"
  - "docs/agents/sprints.md:68 (S7: 0 regex sobre docker logs)"
atualizado: 2026-10-13
---

# ADR-0007: Servidor dedicado em Docker, com a MatchZy conduzindo a partida

## Contexto

O primeiro pipeline (02/09, `b953406`) rodava um servidor dedicado nativo no Windows. Ele nasceu de uma limitação: o listen server do menu ("Practice with Bots") nunca abre o RCON por TCP, então só o dedicado deixa um programa mandar comandos ao jogo (`watcher.py:13-20`).

Em 04/09 (`4c19249`), um spike testou o risco que bloqueava a orquestração: a MatchZy aceita um time só de bots como adversário e reporta o resultado? Se não aceitasse, o plano B eram cvars diretos, sem a MatchZy controlando a série (`docker/SPIKE.md:1-8`). Passou, com duas ressalvas: bots não dão `.ready`, e a MatchZy zera a `bot_quota` ao carregar a partida. O spike usou a imagem `xbird/cs2-matchzy`, com Metamod, CounterStrikeSharp e MatchZy já instalados, porque ela já tinha funcionado em outro projeto do Victor e evitava montar essa pilha à mão (`docker/SPIKE.md:46-52`).

Em 06/09, o `start_match.py` passou a fazer os passos do spike por RCON (`8a3ff2f`), e o watcher passou a seguir o `docker logs` do container em vez do `console.log` nativo (`53f9abd`). Por que o Docker ficou, e não o dedicado nativo, os commits não dizem além disso: motivo não registrado.

## Decisão

- **O servidor é o container `cs2-spike`, da imagem `xbird/cs2-matchzy`** (`docker-compose.yml:14-15`), na porta 27015 da máquina do Victor (`docker-compose.yml:189-191`). É a D7 da SPEC ("Docker Desktop + localhost").
- **A MatchZy conduz a partida.** O app carrega a configuração com `matchzy_loadmatch` (`start_match.py:869`) e força o início com `css_start`, porque bots não contam como time pronto (`start_match.py:535-539`). Contagem de rounds, fim de mapa e placar da série são da MatchZy.
- **O app fala com o jogo por três canais:** RCON para comandos, `docker logs` para estado e arquivos em bind mount para dados.
- **A imagem não tem tag no compose** e vale a `latest` local (`docs/runbooks/versoes-conhecidas.md:68`). Os addons dentro dela têm versão fixa ([ADR-0009](0009-versoes-fixas-de-metamod-cssharp-e-matchzy.md)). Por que a imagem ficou sem tag: motivo não registrado.

## Alternativas consideradas

- **Listen server (partida pelo menu)**: sem RCON por TCP, nada de fora consegue mandar comando.
- **Dedicado nativo no Windows** (o "modo nativo"): foi o primeiro pipeline e ainda existe como legado no `watcher.py`. Sai na poda (S1.4), e o porquê fica no item 54 das armadilhas (`docs/armadilhas/legado-gotv-e-nativo.md:24-28`).
- **Cvars diretos, sem MatchZy** (plano B do spike): não foi preciso, porque o spike passou.
- **Instalar Metamod, CSSharp e MatchZy à mão**: o spike preferiu a imagem pronta para fugir da parte mais frágil.

## Consequências

- Mexer no servidor é mexer num container e num volume vivos: só o papel servidor, só em janela ([ADR-0004](0004-jogo-sempre-jogavel.md)), e o volume é external ([ADR-0010](0010-volume-cs2-data-external.md)).
- O estado lido do `docker logs` por regex é frágil; o S7 (plugin JSONL v1) quer zerar essa leitura.
- O Docker Desktop no Windows tem custo próprio: a escrita no bind mount degrada com o tamanho do arquivo ([ADR-0008](0008-captura-por-plugin-proprio.md)).
- Verificação: G6 na janela (linhas de load da MatchZy e da captura) e G7 na partida.

## Status

Aceito na prática desde 04/09/2026 (`4c19249`) e 06/09 (`8a3ff2f`), na `main`. ADR retroativo, escrito pelo K1.6 em 13/10 a partir dos commits; o texto não passou pela leitura do Victor.

## Fontes

- Commits `b953406`, `4c19249`, `8a3ff2f` e `53f9abd`: a sequência nativo → spike → orquestração por RCON.
- `docker/SPIKE.md`: a pergunta, o resultado e a escolha da imagem.
- Compose, `start_match.py` e o registro de versões: o estado de hoje.
