# Spike — Passo 0: MatchZy reconhece bots como adversário?

Objetivo único deste teste: descobrir se o MatchZy considera uma
partida "ao vivo" e reporta o resultado quando `team2` do
`match_config.json` não tem nenhum jogador humano — só bots do CS2
preenchendo via `bot_quota fill`. Esse é o risco bloqueante da Camada 1
(ver conversa anterior): se não funcionar, a arquitetura muda — cai pro
plano B de cvars diretos, sem MatchZy controlando a série.

## Resultado: PASSOU

Testado em 2026-09-04, bo1 completo em de_mirage, humano vs 9 bots.
**MatchZy funciona com bots como adversário, ponta a ponta** — com duas
ressalvas que a automação da Camada 1 precisa cobrir (nenhuma delas é
bloqueante, só passos extras):

1. Bots não dão `.ready` — a partida trava em "aguardando" até um admin
   mandar `.start` manualmente (via RCON ou chat).
2. O MatchZy zera `bot_quota` ao carregar o match — precisa repor via
   RCON (`bot_quota 10` + `bot_quota_mode fill`) logo depois do
   `.start` pros bots preencherem o time vazio.

Fora isso, tudo automático: contagem de rounds, detecção de fim de
partida, placar de série, nome do vencedor (`winnerName: Bots` no log
— o MatchZy trata bots como um "time" válido pra fins de resultado),
gravação de demo (`MatchZy/<matchid>_<mapa>_<time1>_vs_<time2>.dem`) e
CSV de stats por jogador (`MatchZy_Stats/<matchid>/match_data_map<N>_<matchid>.csv`).
Log de referência do fim de partida:

```
[MatchZy] [HandleMatchEnd] MATCH ENDED, remainingMaps: 0, NumMaps: 1, Team1SeriesScore: 0, Team2SeriesScore: 1
[MatchZy] [SetMatchEndData] Data updated for matchId: 1 winnerName: Bots
[MatchZy] [WritePlayerStatsToCsv] Match stats for ID: 1 written successfully at: .../MatchZy_Stats/1/match_data_map0_1.csv
```

Conclusão pra Camada 1: o gerador de `match_config.json` (Passo 4 do
plano original) pode contar com o ciclo `matchzy_loadmatch` →
`.start`/RCON → `bot_quota` de volta → jogo automático até o fim →
resultado + demo prontos, sem MatchZy travando ou rejeitando bots em
nenhum ponto do fluxo.

Este spike **não** é a stack final. Não tem orquestração de torneio,
não tem watcher.py plugado, não grava nada em banco. É só pra validar
essa variável isolada.

**Nota:** usa a imagem `xbird/cs2-matchzy` (Metamod + CounterStrikeSharp
+ MatchZy pré-instalados sobre `joedwards32/cs2`) em vez de instalar os
três manualmente — a mesma imagem que você já usou com sucesso no
[cs2-ai-bot-coach](https://github.com/rossivictor/cs2-ai-bot-coach)
(CounterStrikeSharp carregou lá e um plugin custom rodou). Isso elimina
a parte mais frágil de montar essa stack do zero. Só o uso do MatchZy
pra orquestrar série com bot como adversário é território não testado
naquele repo (ele nunca chama `matchzy_loadmatch`).

Também vale registrar pra depois: existe um projeto de terceiros,
[matchzy-auto-tournament](https://github.com/sivert-io/matchzy-auto-tournament),
que já faz bracket automation completo em cima do MatchZy. A
documentação dele (e do fork "MatchZy Enhanced" do mesmo autor) não
menciona bots em nenhum lugar — é construído assumindo humano vs
humano. Não invalida o spike, só confirma que ninguém documentou esse
caso de uso; vale revisitar esse repo depois do Passo 0 (se passar) como
possível base pra Camada 1 em vez de escrever tudo do zero.

## Pré-requisitos

- Docker + Docker Compose instalados.
- Um Game Server Login Token (GSLT): gere em
  https://steamcommunity.com/dev/managegameservers, app "Counter-Strike 2
  (Dedicated Server)".
- Seu SteamID64. Formas fáceis de pegar:
  - Client do CS2 aberto → seu perfil Steam → copiar link do perfil →
    colar em https://steamid.io (ele mostra o `steamID64`).

## Passo a passo

### 1. Configurar

```bash
cp .env.example .env
```

Edite `.env` e preencha `SRCDS_TOKEN` (o GSLT do passo anterior) e
`MATCHZY_ADMINS` (seu SteamID64).

Edite `docker/match_config.spike.json` e troque `STEAMID64_AQUI` pelo
mesmo SteamID64 (mantenha `SeuNick` ou troque pelo seu nick in-game,
tanto faz pro teste).

### 2. Subir o servidor

```bash
docker compose up -d
docker compose logs -f cs2-server
```

Primeira subida demora — a imagem baixa o jogo inteiro via SteamCMD
(~40-60GB) mais Metamod/CounterStrikeSharp/MatchZy antes do servidor
ficar pronto.

**Confirme que carregou tudo** antes de seguir: entre no console do
container (`docker attach --sig-proxy=false cs2-spike`) e rode `meta
version` (Metamod) e `css_plugins list` (deve listar o MatchZy). `Ctrl+P
Ctrl+Q` pra sair do attach sem derrubar o container.

### 3. Confirmar RCON de fora do container

Antes de acoplar qualquer script, valide a conectividade isolada — mesma
lição que já foi validada no fluxo nativo (bind errado quebra RCON):

```bash
netstat -ano | findstr "27015"
```

Espera `TCP ... LISTENING` na 27015.

### 4. Conectar e carregar o match

No client normal do CS2: **Servidores → Rede Local**, conecte no seu
servidor. Uma vez conectado, mande o comando via RCON (reaproveitando o
mesmo mecanismo já validado em `watcher.py`):

```bash
.venv\Scripts\python.exe -c "from rcon.source import Client; c = Client('127.0.0.1', 27015, passwd='CHANGE_ME_LOCAL_ONLY'); print(c.run('matchzy_loadmatch match_config.spike.json'))"
```

(troque `CHANGE_ME_LOCAL_ONLY` pela senha real que você colocou em `.env`)

Observe o console do servidor (`docker attach`) e o chat/console do
client. O MatchZy deve confirmar que carregou a partida.

### 5. Ver se o time de bots é aceito

No chat do jogo, mande `.ready` (você é o único humano em `team1`).
`team2` não tem ninguém pra dar ready — é exatamente esse o ponto de
teste:

- **Se o servidor entrar em modo "ao vivo" sozinho** (ou depois de você
  digitar `.ready`), sem travar esperando o outro time: sinal positivo,
  siga pra jogar o mapa inteiro.
- **Se travar** esperando ready de `team2` indefinidamente: tente forçar
  via `.start` no chat (comando admin do MatchZy, "force starts a
  match"). Como seu SteamID64 já está em `MATCHZY_ADMINS`, isso deve
  funcionar sem precisar editar `admins.json` na mão.

### 6. Jogar até o fim e checar o resultado

Termine o mapa (13 rounds ou o que vier primeiro). No console do
servidor, procure por linhas do MatchZy reportando fim de série/mapa
(prefixo costuma ser `[MatchZy]`). Isso é o sinal de que ele reconheceu
a partida como válida do início ao fim, não só que "carregou" o config.

## Gotchas resolvidos durante o teste

- **`matchid` no JSON precisa ser inteiro, não string.** `"matchid": "spike-001"` falha com
  `[MatchZy] [LoadMatchDataCommand] matchid should be an integer!`. Deixe o campo de fora
  (auto-gera) ou use um número puro.
- **`team2` precisa do campo `players`, mesmo vazio de verdade.** Sem ele, falha com
  `team2 should have 'players' JSON!`. Solução: um SteamID64 qualquer (formato válido, não
  precisa ser uma conta real) como placeholder — é esse "jogador fantasma" que nunca vai
  conectar, e é justamente ele que expõe o comportamento dos gotchas 1 e 2 do Resultado acima.
- **Baixar o jogo do zero pelo SteamCMD dentro do Docker é frágil neste ambiente
  (Windows + Docker Desktop + WSL2)** — 4 tentativas seguidas falharam com
  `Error! App '730' state is 0x602 after update job` bem no fim da verificação (~99%),
  cada uma reiniciando o download do zero. Se você já tem uma instalação nativa validada
  (ex.: `C:/cs2server` do fluxo do `watcher.py`), copie `game/` e `steamapps/` direto pro
  volume Docker (`docker run --rm -v cs2-tracker_cs2-data:/data -v "C:/caminho:/source:ro" alpine cp -a /source/game/. /data/game/` etc., com `MSYS_NO_PATHCONV=1` se rodar via Git Bash) —
  o SteamCMD reconhece a instalação existente e só baixa o delta.
- **GSLT (`SRCDS_TOKEN`) pode expirar ou ficar "preso"** de uma sessão anterior que não
  desconectou direito (comum depois de vários `docker stop`/crash seguidos). Sintoma:
  servidor sobe normal, mas clientes levam timeout (`5003: Timed out attempting to connect`)
  tentando conectar — mesmo com RCON e UDP básico (`A2S_INFO`) funcionando. No log do
  servidor aparece `Cert request for invalid failed... We're not logged into Steam` de forma
  contínua. Fix: gerar um GSLT novo em
  https://steamcommunity.com/dev/managegameservers e recriar o container.
- **Docker Desktop pode travar na inicialização** com "unexpected error" citando um socket
  órfão (`dockerInference`, `docker-secrets-engine`, etc.) que nem ele mesmo consegue apagar
  (`Não é possível o acesso ao arquivo pelo sistema` / Win32 error 1920 — reparse point de
  AF_UNIX socket que o Windows não sabe processar sem o backend rodando). Bug conhecido
  (`docker/desktop-feedback#460`). Apagar o arquivo nunca funciona, mesmo com
  `wsl --shutdown` antes; o fix é **renomear a pasta pai inteira**
  (`%LOCALAPPDATA%\Docker\run`, ou a pasta específica do serviço que falhar) e deixar o
  Docker Desktop recriar do zero no próximo start.

## Troubleshooting

- **`meta version` ou `css_plugins list` não reconhecidos**: a imagem
  não terminou de instalar os addons ainda, ou algo falhou no boot —
  cheque `docker compose logs cs2-server` por erros antes desse ponto.
  Como último recurso, `FORCE_DELETE_ADDONS=true` (env var da imagem)
  força reinstalar addons/cfg do zero na próxima subida.
- **RCON não conecta**: confira se `CS2_RCONPW` no `.env` bate com o que
  você usou no comando Python, e se a porta 27015 TCP está mapeada (veja
  `docker compose ps`).
- **Cliente do jogo dá timeout ao conectar, mas RCON funciona**: veja o
  gotcha do GSLT acima — quase sempre é o servidor não estar logado na
  Steam, não um problema de rede/firewall.

## Próximo passo

Passo 0 passou — próximo é o Passo 1 do plano original: adaptar o
`watcher.py` pra consumir o ciclo de vida do MatchZy (hook de fim de
partida) em vez de detectar por regex do `console.log`, e então montar
o schema `career.db` (teams/tournaments/bracket_matches) por cima.
