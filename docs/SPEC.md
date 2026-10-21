# CS2 Tracker — Spec de Produto

> **Status:** premissa central confirmada · **Data:** 2026-09-20 · **Status real das D1–D22 em 2026-10-13 (K1.6):** §12 e §16; visão vigente no [ADR-0001](adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md)
> Consolida as decisões da sessão de grilling. Em 20/09 nada do produto estava implementado; hoje o
> wizard (TUI e web), a captura e as estatísticas rodam, e o que cada decisão já cumpre está na §12 (K1.6).
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

Em 20/09 o diagnóstico era "o warmup às vezes trava, causa raiz desconhecida", e a
resposta decidida foi auto-retry, botão manual e telemetria (D11). **O P1.12 (20/10)
registra a causa: era bug de código do orquestrador, não do servidor**, corrigido no
P1.5 (`f6191a4`, PR #102) e validado numa MD3 real em 20/10 (tag `jogavel-2026-10-20`).
A espera pelo warmup do mapa seguinte (`wait_for_next_map_warmup`, em `start_match.py`)
desistia sempre durante o mapa 1, por dois defeitos somados:

- o teto era de 240 s contados logo depois do `css_start` do mapa 1, então vencia com o
  mapa 1 ainda em jogo;
- o `docker logs --since` recebia a hora UTC sem fuso (sem o `Z`), que o Docker lê como
  hora local: em -03, 3 h no futuro, e a leitura voltava vazia.

Sobrava o botão manual em todo mapa 2+, que era o "warmup que trava". Desde o P1.5, a
espera dura o mapa anterior inteiro (teto de 3 h por espera, `TETO_ESPERA_MAPA_S`), para
quando a série acaba ou o watcher encerra, e lê o log por um cursor da série inteira
(`CursorDockerLogs`): `--since` em epoch, que só avança, e leitura pelo fim (`--tail -t`
filtrado pelo carimbo) quando o json-file corrompido devolve o `--since` vazio
([armadilha](armadilhas/windows-e-docker.md), "`docker logs --since` volta vazio"). Na
MD3 de 20/10, o mapa 2 começou sozinho, sem o botão.

Com a causa fechada, a D11 foi **rebaixada** (§12): auto-retry e telemetria deixam de ser
decisão vigente e nunca foram implementados ([M5](features/M5-confiabilidade.md), F5.1 e
F5.2). O botão **Forçar início / rebalancear bots** da TUI segue como remédio manual para
um início que não pegar; a pendência dele está na §15.

A queda do servidor de 04/10 na virada de série da MD3 (segfault) é outra coisa: não tem
causa provada e não é este bug. O estado dela fica no
[runbook do B1.12](runbooks/b1.12-segfault-troca-de-mapa-md3.md) e no item da §15.

## 12. Decisões

| # | Decisão | Status em 13/10 (K1.6) | Evidência |
|---|---|---|---|
| D1 | App **local pessoal**; mercado é hipótese futura | parcialmente superada pelo [ADR-0001](adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md) | "local pessoal" vale ([ADR-0001](adr/0001-visao-partidas-avulsas-carreira-horizonte-longo.md), [ADR-0003](adr/0003-repo-publico.md)); o mercado deixou de orientar decisão (ADR-0001, Decisão e Consequências) |
| D2 | IA = **profiles nomeados do VPK** via `bot_add_ct "<perfil>"` em runtime. Plugin próprio é trabalho futuro | vigente | `start_match.py:425-429` e `start_match.py:452-466`; a IA própria segue como direção (ADR-0001, Camada 3), e os plugins de bot de terceiros são da [trilha de bots](adr/0005-trilha-de-bots-uma-variavel-por-vez.md) |
| D3 | **Nomes oficiais** no uso pessoal; roster como dado, com `display_name` separado | vigente | `roster.py:1-12`, `roster.py:219-236`; ponto de extensão 3 do ADR-0001 |
| D4 | **Sem anti-cheat, sem ranking global** | vigente | nada no código implementa anti-cheat ou ranking global: o "ranking" de `stats.py:982` é por mapa, das partidas do próprio jogador |
| D5 | **1 humano** + 9 bots | vigente | um `WizardSession` só (`web/app.py:79-82`); tamanho de time de 1 até o máximo do compose (`web/app.py:260-274`), 9 bots no 5x5 |
| D6 | **Evoluir o `cs2-tracker`**, não recomeçar | vigente | o repo é o mesmo desde o `b953406` (02/09), e o produto da SPEC foi construído sobre ele (`f6a4e6b`, `193cd6c`) |
| D7 | **Local**: Docker Desktop + localhost; ritual de entrada idêntico ao atual | vigente | [ADR-0007](adr/0007-servidor-dedicado-em-docker-com-matchzy.md) e [ADR-0010](adr/0010-volume-cs2-data-external.md); `docker-compose.yml:14-15`, `docker-compose.yml:189-191` |
| D8 | **Perfil local** (nick + SteamID salvo), sem Steam OpenID | vigente | `data/profile.json` lido e gravado em `web/app.py:141-152` |
| D9 | **MD1/MD3/MD5**, cada um com escolha direta de mapas **ou** veto | vigente | `wizard_core.py:52`, `wizard_core.py:96-139`, `wizard_core.py:220-229`; rotas `/maps` e `/veto` em `web/app.py:571-655` |
| D10 | **SQLite atual**, sem migração | parcialmente cumprida; revisão prevista no S2.5 | SQLite segue único (`parser.py:433-436`), mas já há migração aditiva por `ALTER TABLE` (`parser.py:420-430`); o S2.5 escreve o ADR que revisa a D10 (`docs/agents/plano-2026-09-26.json:1924`) |
| D11 | Início de partida: **auto-retry (2x)** + botão manual + telemetria | rebaixada em 20/10 (P1.12) | o travamento entre mapas era bug de código da espera do mapa seguinte, corrigido no P1.5 (§11; `start_match.py:1031-1084` e o laço dos mapas 2..N em `start_match.py:1313-1338`; tag `jogavel-2026-10-20`); por isso auto-retry e telemetria deixam de ser decisão vigente e seguem sem implementação ([M5](features/M5-confiabilidade.md), F5.1 e F5.2); o botão manual "Forçar início" segue como remédio (`wizard_tui.py:634-638` → `wizard_core.py:540-568`); volta a ser proposta se um mapa da série voltar a ficar no warmup com o P1.5 no ar; linhas no `c228d93` |
| D12 | **Sem dial de dificuldade** — pro contra pro, e medir se é divertido | vigente | o app não escolhe dificuldade (`start_match.py:811-816`); a variante do `botprofile.vpk` é decisão do Victor, trocada só em janela (AGENTS.md:15) |
| D13 | TUI e web **em paralelo** até o web provar paridade em uso real (série MD3 completa jogada pelo browser); só então a TUI é aposentada (M7/F7.3). Headless fica com o CLI do `start_match.py` | ainda aberta | a web não inicia partida: as rotas param no Resumo (`web/app.py:706-735`); a TUI fica viva e sem diff (AGENTS.md:10); cumprir é da S6 (`docs/agents/sprints.md:67`) e do S8.1 |
| D14 | **Sessão stateful** — reabrir a aba reidrata a partida | parcialmente cumprida | reabrir reidrata o wizard (`web/app.py:79-82`, `web/app.py:176-183`); a partida não, porque a web ainda não a inicia; reidratar e sobreviver ao reinício do uvicorn é do S6.2 (`docs/agents/plano-2026-09-26.json:2300`) |
| D15 | **FastAPI + Jinja + HTMX + SSE**, sem build step | parcialmente cumprida | FastAPI e Jinja (`web/app.py:24-27`), HTMX por CDN, sem build (`web/templates/wizard_modal.html:12`); o SSE ainda não existe (S6.2) |
| D16 | Catálogo **híbrido**: times transcritos + atributos extraídos do VPK | vigente | times em `data/rosters.json`; atributos lidos do VPK em `roster.py:239-257`, estilo em `roster.py:111`, cards em `roster.py:280-299` |
| D17 | **Dois seletores + presets como atalho**, com pool compartilhado | vigente com o [ADR-0013](adr/0013-lineups-grade-de-logos-e-sorteio-no-lugar-dos-presets.md) | dois seletores e pool compartilhado valem (`web/app.py:309-336`); a grade de logos e o sorteio de time substituem os presets como atalho desde o redesenho de 20/09 (`web/app.py:457-463`, `web/app.py:516-518`), confirmado pelo Victor em 13/10 |
| D18 | **Head-to-head por profile** | vigente | `stats.py:562-572` (por partida) e `stats.py:1139-1146` (somado), na tela em `templates/match_detail.html:300-304` |
| D19 | Veto por **preferência real curada à mão**, datada e versionada pelo pool | ainda aberta | o bot veta com sorteio uniforme (`wizard_core.py:141-143`), e só um dos dez times tem dado de veto (`data/rosters.json:10`) |
| D20 | `report.py` vira **camada de consulta**; gerador estático morre (cálculo já extraído pra `stats.py`, ver §11) | parcialmente cumprida | `/` e `/report` são rotas sobre o banco (`web/app.py:176-183`, `web/app.py:206-212`), mas o watcher ainda gera os HTML estáticos (`watcher.py:263-266`, `watcher.py:507-510`); aposentar é do S4.4, depois da D13 (`docs/agents/plano-2026-09-26.json:2097`) |
| D21 | Progressão = **marcos**, sem ELO nem nível | ainda aberta | nenhum marco no código; é a Etapa 8 (§14) |
| D22 | **"Repetir última partida"** em vez de lineups salvas | ainda aberta | nenhum "repetir" no código; é a Etapa 8 (§14) |

## 13. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Só a variante `Low` do VPK foi validada com o search path corrigido | Baixo — `Medium`/`High` podem ter alguma diferença de formato não testada | Trocar de variante e re-rodar o Passo 0 antes de assumir paridade |
| A fidelidade decepciona: 5 templates de skill pra 1.233 nomes, então muitos pros são mecanicamente idênticos | Alto — o nome vira enfeite | Cards honestos sobre o estilo; head-to-head dá peso ao nome; plugin próprio no futuro |
| 9 jogadores com `Skill = 100` tornam a partida frustrante | Alto | Medir jogando; se doer, ajustar por **composição** (5 seus vs 4 deles), nunca mentindo sobre o skill |
| Warmup travado continua aparecendo | Médio | A causa de código foi corrigida no P1.5 (§11); sobra o botão manual. Se voltar com o P1.5 no ar, o [M5](features/M5-confiabilidade.md) (auto-retry e telemetria, rebaixados na D11) volta a ser proposta |
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
| 6 | Tela de partida: iniciar servidor de verdade + log ao vivo (SSE) + ~~auto-retry~~ (rebaixado com a D11 em 20/10, §11) + reidratar partida em progresso — o que falta pro botão "Iniciar partida" do modal funcionar | 5.5 |
| 7 | `report.py`/`stats.py` como consulta + head-to-head | 6 |
| 8 | Marcos, repetir-última, preferências de veto no bot | 7 |
| 9 | Deletar `wizard_tui.py` — **só depois** que o fluxo web (6→8) rodar uma série completa em uso real; até lá TUI e web seguem em paralelo (D13) | 6, 7, 8 |

## 15. Em aberto

- **Bloqueio central agora: o launcher da tela de Partida (Etapa 6).** Iniciar o
  servidor de verdade a partir do browser, log ao vivo por SSE e reidratar uma
  partida em progresso (o auto-retry saiu com a D11 rebaixada, §11) — sem isso o
  botão "Iniciar partida" do modal (§11) continua desabilitado, e as Etapas 7, 8 e
  9 ficam travadas atrás dele (nenhuma delas foi começada)
- `matches.mode`/`opponent_roster_id`/tabela `rosters` ainda não existem no
  schema — enquanto isso, todo item do histórico (home e report) mostra o globo
  de "Competitivo", nunca o escudo do adversário (M3.5, divergência #3)
- Nomes e números de veto dos demais times (a FURIA em §7 é o exemplo; faltam os outros)
- Se `status` lista bots por RCON no CS2, ou se o `docker logs` continua sendo o
  caminho de leitura do estado dos times
- ~~Qual a causa raiz do warmup travado~~ **Respondida no P1.12 (20/10):** bug de
  código na espera do mapa seguinte, corrigido no P1.5 (§11). Seguem abertas duas
  quedas do servidor, que não são esse bug nem uma a outra:
  - **04/10, segfault na virada de série da MD3:** sem causa provada. H1 (BotBuyPatch
    sobre bots já chutados) e H2 (SIGSEGV da CSSharp ao logar exceção) seguem abertas,
    a H3a (idade do processo) segue sem teste, e o T1 e o T2 somaram 24 viradas sem
    queda ([runbook do B1.12](runbooks/b1.12-segfault-troca-de-mapa-md3.md), seções 8
    e 9). Não está resolvida.
  - **20/09, crash do watchdog** (TUI), registrado quando ainda se procurava a causa
    do warmup travado: dessa vez não travou — **crashou** (`WatchDog! Server took
    too long to process` → `FATAL ERROR: Watchdog timeout exceeded, exiting`),
    matando o container inteiro (sem `restart policy` no `docker-compose.yml`, não
    voltou sozinho). Aconteceu logo no `Changelevel to de_anubis` de uma série
    multi-mapa, imediatamente depois de `[MatchZy] [LoadMatchFromJSON]` recarregar e
    os 10 bots nomeados entrarem — mesma janela que `4e9d652` (fix de crash
    multi-mapa) tentou cobrir; pode ser cobertura incompleta desse fix, não uma
    causa nova
- O botão manual **Forçar início / rebalancear bots** monta os times pelo lado do
  mapa 1 em qualquer mapa da série: `wizard_core.force_start` chama
  `force_start_and_balance_bots` sem `map_index`, que fica no padrão 0 e lê
  `map_sides[0]` (`wizard_core.py:540-568`, `start_match.py:853-883`, no `c228d93`).
  O laço automático dos mapas 2..N já passa o mapa certo (P1.6,
  `start_match.py:1325-1332`)
- Validar o fix do search path (§10, Passo 0, `docker/pre.sh`) com as
  variantes `Medium`/`High` do VPK — só `Low` foi testada
- Manter a TUI funcionando (D13) é uma restrição contínua, não uma tarefa única:
  toda mudança futura em `wizard_core.py`/`start_match.py`/`watcher.py` (inclusive
  no trabalho do launcher, Etapa 6) precisa ser testada pela TUI também, não só
  pelo browser

## 16. Reconciliação das decisões (K1.6, 2026-10-13)

O texto das D1–D22 e o resto desta SPEC ficam como o Victor decidiu em 19–20/09; o
K1.6 só acrescentou as colunas de status e evidência da §12 e a linha de status no
topo. Os `caminho:N` da §12 valem no commit do K1.6.

- **vigente**: a decisão vale e o código a cumpre.
- **parcialmente cumprida**: vale, mas falta parte; a coluna diz o que falta e qual card cobre.
- **parcialmente superada**: parte dela foi trocada por ADR ou por mudança registrada no código.
- **ainda aberta**: vale, e o código ainda não a cumpre.
- **rebaixada**: deixou de ser decisão vigente porque a premissa caiu; a coluna diz o que sobra dela e quando volta a ser proposta.

O P1.12 (20/10) rebaixou a D11 e, com ela, reescreveu a "Confiabilidade do início de
partida" da §11, a mitigação do warmup na §13, a Etapa 6 da §14 e os itens do warmup na
§15. Os `caminho:N` da linha D11 valem no `c228d93`.

Decisões tomadas depois da SPEC, e que antes só estavam em commit, viraram ADRs
retroativos ([índice](README.md#decisões-adrs)):

- [ADR-0007](adr/0007-servidor-dedicado-em-docker-com-matchzy.md): servidor dedicado em Docker, com a MatchZy conduzindo a partida (D7).
- [ADR-0008](adr/0008-captura-por-plugin-proprio.md): captura por plugin próprio, não pela demo.
- [ADR-0009](adr/0009-versoes-fixas-de-metamod-cssharp-e-matchzy.md): Metamod, CSSharp e MatchZy com versão fixa.
- [ADR-0010](adr/0010-volume-cs2-data-external.md): volume do servidor external, com nome fixo.
- [ADR-0011](adr/0011-python-3-13-unico.md): um interpretador só, Python 3.13 com dependências travadas.
- [ADR-0012](adr/0012-suite-hermetica-e-ci-antes-do-merge.md): suíte hermética e CI obrigatório antes do merge.
