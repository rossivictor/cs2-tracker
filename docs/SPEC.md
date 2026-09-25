# CS2 Tracker — Spec de Produto

> **Status:** premissa central confirmada · **Data:** 2026-09-20
> Consolida as decisões da sessão de grilling. Nada do produto foi
> implementado ainda (§10/Passo 0 é infra de spike, não produto).
> O Passo 0 (experimento de RCON, §10) rodou: falhou na primeira tentativa,
> causa raiz identificada e corrigida (search path do `botprofile.vpk`
> faltando no `gameinfo.gi`) — **D2 confirmado** depois do fix. O fix é
> automático via `docker/pre.sh`, versionado no repo e reproduzível do zero.
> **Item 8 (2026-09-20):** `web/app.py` passou a servir `/` (home) e
> `/report` direto do banco (sem gerar HTML estático pra isso), e todo o
> wizard (Jogador→Resumo) passou a renderizar como modal por cima dessa
> home real — ver §11. A TUI (`wizard_tui.py`) **não foi tocada** e segue
> sendo o caminho principal de jogo: TUI e web ficam em paralelo até o web
> provar paridade em uso real (D13).

---

## 1. Visão

Um app local que transforma o CS2 num jogo single-player contra times profissionais.
Você abre o Docker Desktop, abre o app no browser, monta a partida escolhendo **com
quem** joga e **contra quem** joga — pros reais, com nome, arma preferida e ritmo de
jogo próprios — e entra no servidor pelo mesmo ritual de sempre.

A promessa: *"jogar ao lado dos seus ídolos contra um time de verdade"*.

O que sustenta a promessa hoje é o `botprofile.vpk` que acompanha o
[CS2-Bot-Improver](https://github.com/ed0ard/CS2-Bot-Improver): **1.233 perfis
nomeados**, incluindo os pros da cena, cada um com `Skill`, `ReactionTime`,
`AimFocus*`, `WeaponPreference`, personalidade e `VoicePitch` próprios, e
**~40 rosters de times** prontos.

## 2. O que este produto NÃO é

- **Não é uma plataforma hospedada.** Roda na máquina do usuário, um servidor, um jogador.
- **Não tem anti-cheat nem ranking global.** Não há adversário humano pra trapacear.
- **Não é multiplayer.** 1 humano, 9 bots. Não há lobby, fila ou convite.
- **Não promete IA de time.** Os bots não fazem execute coordenado nem utility de
  equipe. O que varia entre um pro e outro é reação, mira e preferência de arma.
- **Não é comercial.** Usa nomes e marcas reais sob esse pressuposto (§9).

## 3. Usuário e contexto

Um jogador só — o dono da máquina. Sessão típica: abrir o Docker, abrir
`localhost`, montar a partida em menos de um minuto, jogar um MD1 ou MD3,
e olhar as estatísticas depois. Frequência esperada: algumas vezes por semana.
O app é a única interface; não há CLI de uso cotidiano (só de depuração).

## 4. Conceitos

| Termo | Definição |
|---|---|
| **Profile** | Entrada nomeada no `botprofile.vpk` (ex.: `"NiKo"`). Carrega skill, reação, foco de mira, preferência de arma, personalidade. **Imutável e carregada no boot do servidor.** É a chave primária de todo o domínio |
| **Roster** | Um time real: nome, logo, e os 5 profiles que o compõem |
| **Lineup** | As 5 vagas de um lado de uma partida. A sua tem você + 4 profiles; a do adversário tem 5 profiles |
| **MatchSetup** | Formato + mapas + lados + as duas lineups. É o que o wizard monta |
| **Series** | MD1 / MD3 / MD5. Os bots são **destruídos e recriados a cada troca de mapa** |
| **VetoStep** | Um passo de ban ou pick. Os passos do adversário consultam a preferência real do roster |
| **Session** | O estado do wizard no servidor. Sobrevive ao fechamento da aba |
| **Head-to-head** | Seu desempenho agregado contra um profile ou contra um roster |
| **Marco** | Conquista derivada do histórico ("primeira vitória contra a Vitality") |

## 5. Fluxo do usuário

```
Perfil (1x) → Formato → Lineups → Mapas → Partida → Relatório
```

1. **Perfil** — na primeira vez, nick + SteamID64. Fica salvo; nas próximas, o app
   abre direto no passo 2. Sem login, sem Steam OpenID.
2. **Formato** — MD1, MD3 ou MD5; tamanho de time (1x1 até 5x5).
3. **Lineups** — dois seletores: **seu time** e **adversário**. Cada um aceita
   *time pronto*, *montar manualmente* ou *aleatório*. Três presets de um clique
   pré-preenchem os seletores e continuam editáveis:
   - *Ao lado dos ídolos* — você escolhe os companheiros, adversário aleatório
   - *Contra um time real* — adversário é um roster pronto
   - *Pros aleatórios* — sorteia os dois lados
4. **Mapas** — escolher diretamente, **ou** fazer veto (§7), conforme o jogador preferir.
5. **Partida** — botão *Iniciar servidor*; log ao vivo; o jogador conecta pelo CS2,
   digita `.ready` no chat e volta pra clicar em *Tudo pronto, iniciar partida*.
   Fechar a aba não interrompe nada: reabrir reidrata a partida em andamento.
6. **Relatório** — estatísticas da partida, head-to-head e marcos.

## 6. Seleção de lineups

O seletor mostra cards com nome, time, função, arma preferida e uma leitura honesta
do estilo derivada do template do profile (ex.: *"AWPer, reação rápida, agressivo"*).

**Regra dura, imposta pelo engine:** nomes são únicos no servidor inteiro, sem
distinção de time. Os dois seletores compartilham um pool: escolher `NiKo` de um
lado o remove do outro, e o **seu próprio nick** também sai do pool. Ver §10.

## 7. Formato e veto

Todo formato (MD1/MD3/MD5) aceita dois caminhos:

- **Escolha direta** — o jogador aponta os mapas e os lados. Dois cliques até o jogo.
- **Veto** — sequência competitiva alternada, com o adversário respondendo segundo
  a preferência real do seu roster. É o caminho com imprevisibilidade.

### Modelo de veto

O adversário não sorteia uniformemente: escolhe por peso, a partir dos dados de
veto reais do time.

- **Passo de ban:** sorteio ponderado pelo `ban_pct` dos mapas restantes
- **Passo de pick:** sorteio ponderado pelo `pick_pct` dos mapas restantes
- **Primeiro ban / primeiro pick:** os mapas marcados `first_ban` / `first_pick`
  recebem um reforço no passo correspondente
- Todo mapa mantém um peso mínimo, pra que nenhuma sequência seja determinística

### Fonte dos dados

Curadoria manual: o usuário lê a página pública de estatísticas do time e transcreve.
**Sem scraping** — não há fonte legal, atual e legível por máquina de tendência de
veto (HLTV proíbe em ToS e bloqueia por Cloudflare; Liquipedia não tem ordem de veto;
o dataset aberto com veto completo termina em 2020).

**Validade: 2 a 3 meses.** O Active Duty muda a cada temporada Premier (~6 meses;
a última foi 06/07/2026, Cache no lugar de Overpass) e cada troca zera o histórico
dos mapas afetados. Por isso todo snapshot é datado e versionado pelo pool.

### `data/rosters.json`

```json
{
  "snapshot_date": "2026-09-19",
  "map_pool_version": "2026-07-06",
  "teams": [
    {
      "id": "furia",
      "display_name": "FURIA",
      "logo": "fur",
      "players": ["KSCERATO", "yuurih", "FalleN", "molodoy", "YEKINDAR"],
      "veto": {
        "de_ancient": { "win_pct": 50.0, "pick_pct": 16, "ban_pct": 61, "first_ban": true },
        "de_anubis":  { "win_pct":  0.0, "pick_pct":  6, "ban_pct": 59 },
        "de_mirage":  { "win_pct": 44.4, "pick_pct": 33, "ban_pct":  6, "first_pick": true },
        "de_nuke":    { "win_pct": 71.4, "pick_pct": 26, "ban_pct":  8 },
        "de_inferno": { "win_pct": 50.0, "pick_pct": 26, "ban_pct": 24 },
        "de_cache":   { "win_pct": 50.0, "pick_pct": 21, "ban_pct": 24 },
        "de_dust2":   { "win_pct": 50.0, "pick_pct": 21, "ban_pct":  6 }
      }
    }
  ]
}
```

`players` guarda o **nome do profile no VPK** — imutável, é o que vai no
`bot_add_ct`. `display_name` é o que a tela mostra. A separação existe pra que
trocar por nomes genéricos seja swap de arquivo, não refactor (§9).

## 8. Estatísticas e progressão

O banco já grava nome de bot em `kills` e `damages`, com flag `is_human`. Nenhuma
migração de schema é necessária — falta consulta e tela.

- **Head-to-head por profile** — seu K/D, ADR e taxa de duelo contra cada pro
- **Marcos** — conquistas derivadas do histórico: primeira vitória contra um time,
  primeiro 30-bomb, N rounds de entry ganhos. É a "progressão pessoal" do produto;
  não há ELO nem nível, porque todo profile pro tem `Skill = 100` e não existe
  escala de força pra calibrar
- **Repetir última partida** — um botão que pré-preenche os seletores com o setup
  anterior. Cobre o caso mais frequente: a revanche

## 9. Nomes, marcas e uso pessoal

O app usa nomes de jogadores e times reais. Isso é aceitável **enquanto o uso for
pessoal e não comercial** — é a premissa declarada do projeto. Publicar o repositório
com esses nomes já é distribuição, com risco baixo mas não nulo.

Por isso o roster é **dado, não código**, com `display_name` separado de `profile`.
Um eventual lançamento público troca um arquivo e não toca em catálogo, telas, banco
ou URLs.

## 10. Restrições do engine

Levantadas do código do bot manager da Valve e da inspeção do volume local. Todas
são imposições, não escolhas:

1. **Nome duplicado falha duro.** `UTIL_IsNameTaken` roda antes da busca do perfil e
   é agnóstico de time: `bot_add_ct "NiKo"` com NiKo já no servidor retorna
   `Error - NiKo is already in the game.` e **não adiciona bot nenhum**. Colide também
   com o nick do humano.
2. **Profile inexistente falha em silêncio.** `Error - no profile for 'X' exists.`,
   sem bot e sem sinal pro app → é preciso validar o roster contra o VPK e **conferir
   a contagem** depois dos adds, sob pena de entrar num 4v5 sem perceber.
3. **`bot_add` auto-incrementa `bot_quota`.** Re-setar a quota depois dos adds faz
   `MaintainBotQuota` **chutar bots nomeados**. A ordem correta é
   `bot_quota_mode normal` → `bot_quota 0` → `bot_kick` → adds nomeados → **nada**.
4. **Bots nomeados não sobrevivem à troca de mapa.** Todos os clientes caem no
   `changelevel` e são recriados aleatoriamente pela quota. Re-adicionar por nome a
   cada mapa é **obrigatório**, e suficiente se rodar depois do `css_start`.
5. **Todo profile pro tem `Skill = 100`.** Não existe "FURIA no modo fácil": as
   variantes Low/Medium/High do VPK compartilham o mesmo roster pro e diferem apenas
   nos templates dos bots genéricos. O produto é pro contra pro, sem dial.

### ⚠️ Passo 0 — RESULTADO (executado em 2026-09-19)

**Positivo, após correção de causa raiz. D2 confirmado.** Primeira rodada:
`bot_add_ct "NiKo"` retornou `Error - no profile for 'NiKo' exists.` — testado
também com `s1mple`, `ZywOo`, `donk`, `m0NESY`, `huNter-`: todos falharam da
mesma forma, enquanto `bot_add_ct Osiris` (nome stock) funcionou normalmente.

Restrições da §10 confirmadas ao vivo no mesmo experimento:

- **#1 (nome duplicado falha duro):** `bot_add_ct Osiris` duas vezes, e depois
  `bot_add_t Osiris`, todos retornaram `Error - Osiris is already in the game.`
  — confirmado que é agnóstico de time.
- **#3 (`bot_add` auto-incrementa `bot_quota`):** um único `bot_add_ct Osiris`
  levou `bot_quota` de `0` pra `2`, e o `MaintainBotQuota` completou a vaga
  sozinho com um bot aleatório (`Syfers`) antes do próximo comando rodar —
  reproduzido em condição real, não só lido no código.

**Causa raiz (F0.2) e correção:**

`bot_difficulty`/`custom_bot_difficulty` fora de faixa (5) foi descartado como
causa: o README já documentava que o CS2-Bot-Improver ignora esses cvars
inteiramente. O `overrides/botprofile.vpk` ativo também foi descartado como
"arquivo errado" — é um VPK binário válido (assinatura `0x55aa1234`), contém
1.709 perfis nomeados incluindo `NiKo` em sintaxe correta
(`ProTop+RiflePro+RiflePersonality "NiKo"`, i.e. templates seguidos do nome
entre aspas), e internamente expõe um arquivo virtual `/botprofile.db` —
exatamente o nome que `libserver.so` (o binário do engine) referencia.

A causa real: **o dedicated server nunca monta `overrides/botprofile.vpk`
como search path.** O dump de boot (`docker logs`) lista explicitamente todos
os VPKs montados nos grupos `GAME`/`MOD`/`PLATFORM` — só aparecem
`pak01.vpk`/`shaders_vulkan.vpk` de `csgo/`, `csgo_imported/`, `csgo_core/` e
`core/`. `overrides/botprofile.vpk` nunca é citado. A convenção "solte o
arquivo em `overrides/`" do CS2-Bot-Improver parece assumir um mount
automático que só existe pra listen server / client, não pro `srcds`
dedicado que este projeto usa.

**Fix aplicado e verificado:** adicionar uma entrada explícita de search path
no `gameinfo.gi` do servidor, antes do `Game csgo` genérico (pra ter
prioridade), e reiniciar o container:

```
# game/csgo/gameinfo.gi, dentro de FileSystem/SearchPaths, logo após
# "Game csgo/addons/metamod":
Game    csgo/overrides/botprofile.vpk
```

Após `docker restart cs2-spike`: `bot_add_ct NiKo` **funciona**
(`ClientPutInServer create new player controller [NiKo]`, confirmado no
`status`). Efeito colateral esperado: `bot_add_ct Osiris` passou a falhar
(`Error - no profile for 'Osiris' exists.`) — o VPK customizado (variante
`Low`, 1.709 perfis) substitui o banco padrão em vez de somar a ele, e
`Osiris` não está entre esses 1.709.

**Conclusão:** a premissa central (D2) se sustenta. **§1, §6 e §7 seguem
válidos como especificados.**

**Item 0 (2026-09-20):** o fix virou automático via `docker/pre.sh`, montado
por bind mount em `/home/steam/cs2-dedicated/pre.sh` (`docker-compose.yml`).
A imagem já roda `source "${STEAMAPPDIR}/pre.sh"` depois do `steamcmd` e
antes de subir o `cs2.sh` (hook oficial de `entry.sh`); nosso `pre.sh`
mantém o `source` original da imagem (`xbirdcs2matchzy/start.sh`) e adiciona
um patch idempotente em `gameinfo.gi` (só insere a linha se ainda não
existir). Validado do zero: restaurei o `gameinfo.gi` original, rodei
`docker compose up -d --force-recreate` e o log de boot mostrou
`[cs2-tracker] gameinfo.gi patched: ...` sozinho, sem intervenção manual;
`bot_add_ct NiKo` voltou a funcionar. Um segundo `docker restart` confirmou
que não duplica a linha (`gameinfo.gi ja tem o search path ..., nada a
fazer`). Sobrevive a `docker compose down -v` e a clonar o repo numa máquina
nova, porque o `pre.sh` vem do repositório, não do volume.

Pendências que seguem em aberto antes do M1:

- Só a variante `Low` foi testada. Trocar pra `Medium`/`High` (ou pro fluxo
  completo de `roster.py` validando contra o VPK) ainda não foi validado com
  o search path corrigido.
- Vale re-rodar o teste com mais alguns nomes de rosters reais (§7) pra
  confirmar cobertura, não só os 5 testados.

Se o RCON devolver resposta vazia, ler de `docker logs cs2-spike`: o CS2 manda
`CONSOLE_ECHO` pro console do servidor, não pro socket.

## 11. Arquitetura

```
browser (HTMX + SSE)
    ↕
FastAPI  ──  WizardSession (estado) ──  roster.py ── data/rosters.json
    │
    └──  wizard_core  ──  start_match  ──  RCON ──  cs2-spike (Docker)
                                       └──  watcher.py ── parser.py ── SQLite
```

- **FastAPI + Jinja + HTMX + SSE.** Sem build step, sem Node. O app sobe com Python.
- **`WizardSession`** no servidor guarda o estado do wizard e da partida ativa;
  a página reidrata a partir dele.
- **Home e report como rotas, não geradores estáticos (Feito em 2026-09-20).**
  `GET /` e `GET /report` chamam `home.build_context()`/`report.build_payload()`
  direto contra o SQLite a cada request — a mesma camada de cálculo que já existia
  em `stats.py`. `home.py --out`/`report.py --out` (geração de arquivo local) ainda
  existem e continuam sendo chamados pelo `watcher.py` depois de cada ingestão, mas
  viraram redundantes pro app: servem só quem quiser um HTML solto pra arquivar/
  compartilhar manualmente. Aposentar essa chamada duplicada do `watcher.py` é
  parte do [M6 F6.1](features/M6-estatisticas.md).
- **Wizard como modal sobre a home (Feito em 2026-09-20).** `/`, `/report` e as
  telas do wizard (`/setup` → `/summary`) compartilham o mesmo `templates/shell.html`.
  O wizard renderiza a home real de fundo e o passo atual num `.modal-overlay` por
  cima — fechar (✕) só navega pra `/`, sem resetar o `WizardSession`, então reabrir
  por `/setup` reidrata exatamente no passo em que parou (D14). O report também
  passou a reusar o estilo visual da home, inclusive a lista de partidas (linha
  colorida por resultado, placar em mono, ícone do mapa) em vez de tabela.
- **Log ao vivo por SSE — ainda não existe.** É o que falta pro botão "Iniciar
  partida" do modal funcionar de verdade (Etapa 6). O `contextlib.redirect_stdout`
  atual é global do processo e precisa virar um sink explícito — num servidor web
  ele engoliria o log do próprio servidor.
- **`wizard_tui.py` fica.** TUI e web operam **em paralelo** até o web provar
  paridade em uso real — ver D13 e [M7 F7.3](features/M7-acabamento.md). Nenhuma
  mudança em módulo compartilhado (`wizard_core.py`, `start_match.py`,
  `watcher.py`) pode quebrar a TUI nesse meio tempo. O headless continua existindo
  também no CLI do `start_match.py`, que ganha argumentos de roster.

### Confiabilidade do início de partida

O warmup às vezes trava — causa raiz desconhecida. O app tenta `css_start` +
rebalanceio automaticamente até 2 vezes antes de desistir, mantém o botão manual
como último recurso, e **registra cada ocorrência** (estado do `docker logs`,
clientes conectados, mapa da série, tempo desde o `css_start`). O objetivo do
registro é acumular evidência pra atacar a causa depois — hoje o remédio é manual
e não deixa rastro.

## 12. Decisões

| # | Decisão |
|---|---|
| D1 | App **local pessoal**; mercado é hipótese futura |
| D2 | IA = **profiles nomeados do VPK** via `bot_add_ct "<perfil>"` em runtime. Plugin próprio é trabalho futuro |
| D3 | **Nomes oficiais** no uso pessoal; roster como dado, com `display_name` separado |
| D4 | **Sem anti-cheat, sem ranking global** |
| D5 | **1 humano** + 9 bots |
| D6 | **Evoluir o `cs2-tracker`**, não recomeçar |
| D7 | **Local**: Docker Desktop + localhost; ritual de entrada idêntico ao atual |
| D8 | **Perfil local** (nick + SteamID salvo), sem Steam OpenID |
| D9 | **MD1/MD3/MD5**, cada um com escolha direta de mapas **ou** veto |
| D10 | **SQLite atual**, sem migração |
| D11 | Início de partida: **auto-retry (2x)** + botão manual + telemetria |
| D12 | **Sem dial de dificuldade** — pro contra pro, e medir se é divertido |
| D13 | TUI e web **em paralelo** até o web provar paridade em uso real (série MD3 completa jogada pelo browser); só então a TUI é aposentada (M7/F7.3). Headless fica com o CLI do `start_match.py` |
| D14 | **Sessão stateful** — reabrir a aba reidrata a partida |
| D15 | **FastAPI + Jinja + HTMX + SSE**, sem build step |
| D16 | Catálogo **híbrido**: times transcritos + atributos extraídos do VPK |
| D17 | **Dois seletores + presets como atalho**, com pool compartilhado |
| D18 | **Head-to-head por profile** |
| D19 | Veto por **preferência real curada à mão**, datada e versionada pelo pool |
| D20 | `report.py` vira **camada de consulta**; gerador estático morre (cálculo já extraído pra `stats.py`, ver §11) |
| D21 | Progressão = **marcos**, sem ELO nem nível |
| D22 | **"Repetir última partida"** em vez de lineups salvas |

## 13. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Só a variante `Low` do VPK foi validada com o search path corrigido | Baixo — `Medium`/`High` podem ter alguma diferença de formato não testada | Trocar de variante e re-rodar o Passo 0 antes de assumir paridade |
| A fidelidade decepciona: 5 templates de skill pra 1.233 nomes, então muitos pros são mecanicamente idênticos | Alto — o nome vira enfeite | Cards honestos sobre o estilo; head-to-head dá peso ao nome; plugin próprio no futuro |
| 9 jogadores com `Skill = 100` tornam a partida frustrante | Alto | Medir jogando; se doer, ajustar por **composição** (5 seus vs 4 deles), nunca mentindo sobre o skill |
| Warmup travado continua aparecendo | Médio | Auto-retry + telemetria (§11) |
| Dados de veto envelhecem | Baixo | Snapshot datado; re-curar por temporada |

## 14. Ordem de implementação

| # | Etapa | Depende de |
|---|---|---|
| **0** | ~~Experimento de RCON — validar `bot_add_ct "NiKo"`~~ **Rodou em 2026-09-19, confirmado após fix (§10)** | — |
| 0.5 | ~~Automatizar o fix do `gameinfo.gi` (search path do `botprofile.vpk`) no bootstrap do container~~ **Feito em 2026-09-20 via `docker/pre.sh`** | 0 |
| 1 | ~~`WizardSession` extraído + sink de log no lugar do `redirect_stdout`~~ **Feito em 2026-09-20** | — |
| 2 | ~~Bots nomeados no `start_match.py` (ordem de quota, re-add por mapa), testável pelo CLI~~ **Feito em 2026-09-20** | 0, 0.5 |
| 3 | ~~`data/rosters.json` + `roster.py` com validação contra o VPK~~ **Feito em 2026-09-20** | 0 |
| 4 | ~~App web: perfil, formato, mapas, veto~~ **Feito em 2026-09-20 (F3.1+F3.2; F3.3/F3.4 seguem item 6)** | 1 |
| 5 | ~~Seletor de lineups~~ **Feito em 2026-09-20** (F4.1, F4.2, F4.3, F4.4) | 3, 4 |
| 5.5 | ~~Home e report unificados no app web (sem gerar HTML estático); wizard inteiro renderiza como modal por cima da home~~ **Feito em 2026-09-20** | 3.5 (parcial), 4, 5 |
| 6 | Tela de partida: iniciar servidor de verdade + log ao vivo (SSE) + auto-retry + reidratar partida em progresso — o que falta pro botão "Iniciar partida" do modal funcionar | 5.5 |
| 7 | `report.py`/`stats.py` como consulta + head-to-head | 6 |
| 8 | Marcos, repetir-última, preferências de veto no bot | 7 |
| 9 | Deletar `wizard_tui.py` — **só depois** que o fluxo web (6→8) rodar uma série completa em uso real; até lá TUI e web seguem em paralelo (D13) | 6, 7, 8 |

## 15. Em aberto

- **Bloqueio central agora: o launcher da tela de Partida (Etapa 6).** Iniciar o
  servidor de verdade a partir do browser, log ao vivo por SSE, auto-retry e
  reidratar uma partida em progresso — sem isso o botão "Iniciar partida" do
  modal (§11) continua desabilitado, e as Etapas 7, 8 e 9 ficam travadas atrás
  dele (nenhuma delas foi começada)
- `matches.mode`/`opponent_roster_id`/tabela `rosters` ainda não existem no
  schema — enquanto isso, todo item do histórico (home e report) mostra o globo
  de "Competitivo", nunca o escudo do adversário (M3.5, divergência #3)
- Nomes e números de veto dos demais times (a FURIA em §7 é o exemplo; faltam os outros)
- Se `status` lista bots por RCON no CS2, ou se o `docker logs` continua sendo o
  caminho de leitura do estado dos times
- Qual a causa raiz do warmup travado. **Novo dado (2026-09-20, TUI):** dessa vez
  não travou — **crashou** (`WatchDog! Server took too long to process` →
  `FATAL ERROR: Watchdog timeout exceeded, exiting`), matando o container inteiro
  (sem `restart policy` no `docker-compose.yml`, não voltou sozinho). Aconteceu
  logo no `Changelevel to de_anubis` de uma série multi-mapa, imediatamente depois
  de `[MatchZy] [LoadMatchFromJSON]` recarregar e os 10 bots nomeados entrarem —
  mesma janela que `4e9d652` (fix de crash multi-mapa) tentou cobrir; pode ser
  cobertura incompleta desse fix, não uma causa nova
- Validar o fix do search path (§10, Passo 0, `docker/pre.sh`) com as
  variantes `Medium`/`High` do VPK — só `Low` foi testada
- Manter a TUI funcionando (D13) é uma restrição contínua, não uma tarefa única:
  toda mudança futura em `wizard_core.py`/`start_match.py`/`watcher.py` (inclusive
  no trabalho do launcher, Etapa 6) precisa ser testada pela TUI também, não só
  pelo browser
