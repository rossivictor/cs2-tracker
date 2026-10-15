# Trilha de bots (sprint B1)

> **Para quem:** o papel servidor, que opera container, RCON e volume em janela, o PM e o Victor.
> **Origem:** o handoff da sessão paralela `5a2af0df`
> ([cópia literal](../historico/2026-09-26-handoff-plugins-de-bot.md)), corrigido pela
> pesquisa do B1.1 (2026-09-26, só leitura). Este documento é do card B0.11 (parte docs).
> Os cards B1.7, B1.9 e B1.10 também escrevem aqui.
> **Números de linha** do `docker-compose.yml` valem para o `efcaa42` (tag
> `jogavel-2026-09-26`) e foram conferidos no checkout principal em 2026-09-26. Um PR que mexa
> no compose, como o B1.3r ou a parte "compose" do B0.11, pode deslocá-los. Por isso cada
> passo cita também o alvo da máscara, que não muda.

## Objetivo

Devolver aos bots o que a atualização do CS2 de 23/09/2026 tirou deles: granadas
(NadeSystem), skins e facas (BotRandomizer), reatividade e consciência (BotAI, BotState),
mira (BotAimImprover) e compra (BotBuy). Um plugin por vez, cada um validado numa partida
real do Victor, sem deixar o jogo injogável em nenhum momento.

Ponto de partida, na tag `jogavel-2026-09-26`:

- Metamod `2.0.0.1411`, CounterStrikeSharp `v1.0.373` e MatchZy `0.8.15` (compose:63-65).
- A suíte inteira de plugins de bot está mascarada por `./docker/plugins/_empty`
  (compose:141-155), e o RayTrace também (101 e 108).
- Os bots têm IA e mira vanilla. O `botprofile.vpk` é o High. A Q9=A o fixava até o fim da
  B1, mas o Victor o trocou duas vezes durante a trilha (ver [Épocas](#épocas)).

A trilha termina no B1.10. Nesse ponto, cada plugin está religado, degradado ou mascarado, as
assinaturas que falharam estão registradas pelo nome e as épocas de comportamento dos bots
estão anotadas para as estatísticas.

## Máscaras no ponto de partida

O estado de cada alvo no fim da trilha está no [Fechamento](#fechamento).

| Linha (efcaa42) | Alvo mascarado, em `game/csgo/addons/` | Tipo | Quem religa |
|---|---|---|---|
| 101 | `counterstrikesharp/plugins/RayTraceImpl` | CSSharp | fora da B1 (B2, Q16) |
| 108 | `RayTrace` | Metamod nativo | fora da B1 (B2) |
| 141 | `counterstrikesharp/plugins/BotAI` | CSSharp | B1.7: religado em 14/10 pelo bind de `./docker/plugins/BotAI`, o fork do B1.7b ([religar pelo fork](#religar-o-botai-pelo-fork)) |
| 142 | `counterstrikesharp/plugins/BotAimImprover` | CSSharp | B1.4 |
| 143 | `counterstrikesharp/plugins/BotBuy` | CSSharp | B1.6 |
| 144 | `counterstrikesharp/plugins/BotHiderImpl` | CSSharp | fora da B1 (B2) |
| 145 | `counterstrikesharp/plugins/BotRandomizer` | CSSharp | B1.9 (vira bind de `./docker/plugins/BotRandomizer`) |
| 146 | `counterstrikesharp/plugins/BotState` | CSSharp | B1.5 |
| 149 | `BotHider` | Metamod nativo | fora da B1 (B2) |
| 155 | `counterstrikesharp/plugins/NadeSystem` | CSSharp | B1.8 |

Religar um plugin é comentar a linha `_empty` do alvo no PR do card e recriar o container na
janela. O plugin que reaparece é o que está no volume. Ele veio de uma instalação manual de
05/09, de origem não versionada, e não da imagem (handoff, "Erros da sessão anterior").

Os comentários do compose sobre esses plugins (linhas 93-140) têm três afirmações falsas,
listadas no handoff:

- que RayTrace, BotAI e BotAimImprover vêm "embutidos na imagem";
- que mascarar só uma parte da suíte "foi pior";
- que o segfault veio de BotAI e BotAimImprover.

A correção é a parte "compose" do B0.11, num PR separado e só de comentário.

## Ordem dos passos

| Passo | Card | Mudança no compose | O que o B1.1 achou no fonte | Janela |
|---|---|---|---|---|
| 1 | B1.3, reescrito como **B1.3r** | linhas 63-64: o par Metamod `2.0.0.1469` + CSSharp `v1.0.375`, com a suíte ainda mascarada | a 1.0.375 não carrega no Metamod 1411. **Bloqueado até decisão do Victor** ([runbook](b1.3-cssharp-1.0.375.md)) | janela "pode mexer no servidor" (Q4, 45 min), com smoke só de bots; não cabe nos 15 a 30 min do pós-"terminei" |
| 2 | B1.4 | linha 142 (BotAimImprover) | guarda explícita: sem a assinatura, desativa-se limpo antes de qualquer hook | pós-partida |
| 3 | B1.5 | linha 146 (BotState) | guarda efetiva: só escreve se o endereço resolveu e os bytes originais batem | pré-partida, com partida só de bots (card) |
| 4 | B1.6 | linha 143 (BotBuy) | não tem assinatura própria; usa o `GiveNamedItem` da CSSharp, que não mudou | pré-partida, com partida só de bots (card) |
| 5 | B1.7 | linha 141 (BotAI); pelo fork, vira bind de `./docker/plugins/BotAI` ([religar pelo fork](#religar-o-botai-pelo-fork)) | guarda forte nas 43 assinaturas, **mas** escreve num offset fixo de `CCSBot` a cada spawn de bot | pós-partida; smoke só de bots recomendado |
| 6 | B1.8 | linha 155 (NadeSystem) | **sem guarda**; chama `DispatchSpawn()`, que na 1.0.373 é ponteiro nulo. Só roda com CSSharp 1.0.375 ou mais nova | pré-partida, com partida só de bots de 5 rounds ou mais (card) |
| 7 | B1.9 | linha 145 vira bind de `./docker/plugins/BotRandomizer` | **sem guarda**; a correção upstream é o commit `18d1510` (o plano dizia `5dfe948`) | pré-partida, com partida só de bots (card) |
| 8 | B1.10 | nenhuma | fechamento: registro, sobras pelo nome e ADR-0005 | offline |

A evidência de cada passo vem do B1.1. Os clones que ele leu estão em
`C:/Users/Victor/cs2-tracker-backups/2026-09-26/temp-artifacts/5a2af0df/` (`improver/`,
`botai/`, `bullseye/`, `cbi/`).

### Passo 1 · B1.3r: CSSharp 1.0.375 com Metamod 1469, suíte mascarada

- O card pedia "o PR muda só `CSSHARP_FIXED_VERSION`", e isso não funciona. A 1.0.375 exige
  Metamod com KHook (plugin API 18), e o nosso 1411 é API 17. O procedimento, os downloads e
  a volta estão em [b1.3-cssharp-1.0.375.md](b1.3-cssharp-1.0.375.md).
- O que se espera no log: somem `CEntityIOOutput_FireOutputInternal` e
  `CBaseEntity_EmitSoundFilter`.
  - A assinatura de FireOutputInternal mudou na 375. O sumiço dela no boot é a prova do G6
    (o runbook confere antes, no log da 373, que o padrão casa).
  - A de EmitSoundFilter não mudou. O erro dela é efeito em cascata: na 373, quando
    FireOutputInternal falha, `EntityManager::OnAllInitialized` retorna antes de resolver
    EmitSoundFilter, DispatchSpawn e TakeDamageOld.
  - O erro de EmitSoundFilter só é logado quando algo chama EmitSound, e quem chama é o
    NadeSystem, mascarado. A ausência dele no B1.3r não prova nada: ela **só é verificável
    no B1.8**.
- Efeito colateral esperado: o Metamod 1469 recusa os plugins nativos compilados para a API
  17 (RayTrace, BotHider, BotVision e BotController). É uma recusa limpa, e RayTrace e BotHider
  já estão mascarados. Na janela, faça o inventário com `meta list` e `css_plugins list`,
  porque BotControllerImpl, RoundDamageRecap e BotVision não têm máscara e não se sabe se
  estão no volume.

### Passo 2 · B1.4: BotAimImprover

- Guarda em `BotAimImprover.cs:163-181` (clone `improver/`). Sem a assinatura, ele loga
  `Fatal error during Load() (signature broken?). Plugin inactive.` e sai.
- O resultado mais provável é **inativo**, não crash. Os offsets de `CCSBot` mudaram depois
  de 23/09, e o upstream CS2-Bullseye-Bot (PR #8, 25/09) trocou por curinga os bytes que a
  assinatura instalada ainda fixa (`8B 8F E0 59 00 00`, por inferência do B1.1). A versão do
  volume deve falhar a assinatura e se desativar.
- **Essa linha exata é esperada no B1.4.** Ela não reprova o critério 5 e não entra no grep
  de linhas proibidas do G6 desse passo, que continua procurando `Fatal error` em qualquer
  outra linha. Com ela, o veredito é **inativo**, não degradado: o plugin não roda.
- Sem o RayTrace nativo, `PointVisibleFromEye` devolve `true` e o plugin trata tudo como
  visível (`BotAimImprover.cs:412-424`).

### Passo 3 · B1.5: BotState

- Os patches de FOV só escrevem se `FindSignature` não devolver zero e se os bytes originais
  baterem com o esperado (`BotState.cs:2186-2215`).
- Os hooks DefuseBomb e Blind (1565-1590, 1671-1686) não checam zero. Mas `.Hook()` com
  handle zero lança exceção gerenciada, que cai no `try/catch` e desliga o recurso (1542). Os
  callbacks descartam endereço de bot zero (1617, 1712).

### Passo 4 · B1.6: BotBuy

- Não usa assinatura nem offset fixo. Protege `ItemServices` nulo (`BotBuy.cs:345, 367`).
  Foi compilado contra a 1.0.367 (net8.0).
- Critério extra do card: as compras dos bots precisam variar mais que no `events_60`, a
  partida que serviu de evidência da `jogavel-2026-09-26`.

### Passo 5 · B1.7: BotAI

- Tem a guarda mais forte da suíte: descarta endereço zero (`BotAI.cs:60`), confere se o
  endereço é válido e os bytes originais antes de gravar (150-180) e desfaz par órfão
  (95-115).
- A exceção é o `UpdateBotBombState` (121, 138, 224-240). A cada spawn de bot, ele escreve um
  Int32 zero em `CCSBot+0x5100+0x0C`. O offset é fixo, da build 14172 (`f746074`, 30/07, no
  CS2-Bot-Improver, clone `cbi/`), e só é protegido por "endereço legível". Se o layout de
  `CCSBot` mudou, isso corrompe memória em silêncio, sem assinatura que barre.
- Recomendação do B1.1, que não é critério do card: um [smoke só de bots](smoke-partida-de-bots.md)
  antes da partida do Victor (Q7=A permite).
- Registrar pelo nome quais das 43 assinaturas falham (card). No upstream, não há commit
  desde 27/08, e o PR #7 ("fix: Update sig") está aberto. Critério trocado em 14/10, com OK do Victor: o BotAI volta pelo fork do B1.7b, por bind ([religar pelo fork](#religar-o-botai-pelo-fork)).

### Passo 6 · B1.8: NadeSystem

- Não tem guarda: cria as funções nativas sem checar o handle (`NadeSystem.cs:357-379`). As
  chamadas (`Replay.cs:253/282/312`, `SpecialGrenades.cs:77`) estão dentro de `try/catch`,
  então um handle zero vira exceção gerenciada, não segfault.
- Os vetores reais de crash são outros:
  - `DispatchSpawn()` (`Replay.cs:197, 238, 385`; `SpecialGrenades.cs:106`). Na 1.0.373,
    com o jogo atual, esse ponteiro fica nulo, e isso casa com o segfault "enquanto o
    NadeSystem reproduzia granada". A conclusão vem da leitura do código; ninguém reproduziu.
  - `Teleport()`, que na 373 usa o offset velho (162; o certo é 164).
  - `pawn.EmitSound` (`Audio.cs:98, 264`), que é a origem do erro de EmitSoundFilter no log.
- **Pré-requisito duro:** o B1.3r aplicado e validado. Na 373, este passo não roda.
- Linha de base de granadas de bot medida no `events_60` (card; ferramenta do H1.1).

### Passo 7 · B1.9: BotRandomizer do upstream

- Antes do `18d1510`, a assinatura de `SetOrAddAttributeValueByName` não casava, e o `try/catch`
  de `BotRandomizer.cs:95-130` é código morto: o construtor de `MemoryFunctionWithReturn` não
  lança, porque a CSSharp engole a falha e devolve handle zero. O `NativeAvailable` fica
  verdadeiro (`WeaponItemViewStore.cs:30`), o pre-hook de `GiveNamedItem` liga, e a chamada
  nativa lança dentro do `TryPrepare`, cujo catch loga uma vez `Failed to prepare a weapon item
  view` (`WeaponItemViewStore.cs:95-104`; o catch do pre-hook, 316, só pega o que falha fora
  dele): sem crash e sem skins. Na build 2000930 isso voltou ([Sobras](#sobras), 7).
- A correção upstream é o `18d1510` (24/09, "fix: Update sig", PR #8 do upstream), com o csproj
  na 1.0.375 no `276f1ce`, o commit compilado ([runbook](b1.9-botrandomizer-upstream.md)). Os
  `5dfe948` e `d5cf9e0` do plano existem no CS2-Bot-Improver (`cbi/`), com as mesmas mudanças.
- A licença é AGPL-3.0, como a de todos os repositórios ed0ard. Por isso ele compila
  localmente, no container do SDK (o mecanismo de `docker/build-events-plugin.sh`), pelo papel
  servidor. Clone e download só com OK.

### Fora da B1

RayTrace/RayTraceImpl, BotHider/BotHiderImpl, BotVision e BotController são plugins nativos e
ficam para o sprint B2 (Q16). As versões corrigidas deles (BotHider v0.5.0, BotVision v0.3.0,
BotController v0.7.0) pedem Metamod 1469+ e CSSharp 1.0.375+. Se o B1.3r for aplicado, o B2.2
("Subir o Metamod") fica absorvido por ele, e sobra o B2.3 (nativos um por vez).

## Critérios de sucesso de cada passo

Valem na janela (G6) e na partida do Victor (G7). Os itens 1 a 7 precisam valer; o 8 é
registro e não reprova o passo:

1. **BO1 completo com troca de mapa.** Escolha um mapa diferente de `de_mirage`, o
   `CS2_STARTMAP`, para que o `loadmatch` troque de mapa.
2. **Zero `Segmentation fault`** no `docker logs` desde o `StartedAt` do container. Também
   zero `Stack overflow`, zero `core dumped` e nenhum crash-loop.
3. **Nenhum overflow depois de `SIGNONSTATE_FULL` + 60 s.** Um
   `NETWORK_DISCONNECT_OVERFLOW` no signon não conta contra o plugin (ver confundidores).
4. **Partida ingerida.** O watcher loga
   `[PIPELINE] Eventos do mapa N arquivados em events_<matchid>_mapN.jsonl`, e a partida
   aparece no banco. O QA confere numa cópia `mode=ro`, nunca no banco vivo.
5. A linha de load do plugin religado aparece sem `Fatal error`. A exceção é a linha de
   desativação pela guarda que o próprio passo documenta como esperada (no B1.4,
   `Fatal error during Load() (signature broken?). Plugin inactive.`), e aí o veredito é
   **inativo**. As assinaturas que falharam ficam registradas **pelo nome**, não só pela
   contagem.
6. MatchZy e captura carregados: o log mostra `[MatchZy 0.8.15 LOADED]` e
   `[Cs2TrackerEvents] Pronto — gravando em`.
7. A build do CS2 antes e depois da janela fica registrada. O sha256 dos arquivos montados,
   lido dentro do container, é igual ao do checkout.
8. **Variante do `botprofile.vpk` e época.** A variante ativa só se prova pelo sha256 de
   `game/csgo/overrides/botprofile.vpk` lido **no volume** pelo papel servidor e comparado com
   o de `overrides/{Low,Medium,High}/botprofile.vpk` (valores em
   [versões conhecidas](versoes-conhecidas.md#hashes-completos)), com a hora da leitura.
   - Quem lê: o servidor, na janela ou na coleta só leitura pós-partida (preflight 0, sem
     janela), com `docker exec cs2-spike sha256sum` nos quatro caminhos, sob
     `/home/steam/cs2-dedicated/game/csgo/overrides/`. Dev, QA e tech-manager não rodam docker.
   - O `jogavel.py coletar` ainda **não** lê o VPK: ele confere só os arquivos montados do
     checkout (binds de arquivo e pastas de `docker/plugins/`), e o VPK mora no volume, fora
     deles. Ler o VPK na coleta é card separado; até lá, a leitura é esse `docker exec` à mão.
   - Registre `VPK: <variante> (<sha abreviado>, lido <data hora>, <janela|coleta>)` e a época
     da tabela [Épocas](#épocas). Hoje é a "VPK Low": `02e5e958…` desde 28/09 19:54:52, em
     vigor na `jogavel-2026-10-03`.
   - Sem esse sha, registre `VPK: <variante> inferida (<de onde>)`. Foi o caso do G7 do B0.8
     (`candidato-8`, matchid 74): o log não anuncia a dificuldade (0 ocorrências de
     `difficulty`), a coleta não leu o VPK, e o Low ficou inferido do
     [inventário da Janela 0](inventario-volume.md#vpk).
   - O "BOT Difficulty: <variante> [n/3]" do RoundDamageRecap 1.2.0 aparece **só no chat do
     jogo**. Ele não vai para o `docker logs` nem para o JSONL, e o `evidencia_partida.py` não
     o vê: não é evidência coletável. O relato do Victor de que viu o anúncio vale junto com a
     partida (`demo_name` ou matchid) e a hora, como relato, e não substitui o sha. Uma
     lembrança sem partida e hora já virou pedido de janela (28/09 18:22: "do High para o
     Medium", com o Medium ativo desde 27/09 15:34; a hipótese da janela é que o "High"
     lembrado era da partida 26, a última no High).

O veredito de cada passo é um destes:

- **religado:** carregou, sem assinatura faltando e sem crash;
- **degradado:** carregou com alguma assinatura faltando e segue ativo, sem crash;
- **inativo:** carregou, mas a própria guarda o desativou (ex.: a linha `Plugin inactive.`
  do BotAimImprover), sem crash. Na prática equivale a mascarado: o comportamento dos bots
  não muda;
- **mascarado:** a máscara voltou;
- **bloqueado:** depende de outra coisa.

## Confundidores: leia antes de culpar um plugin

1. **Overflow no signon (a causa não é o `warmup.cfg`; ver abaixo).** Em 26/09 às 16:04, com a
   suíte mascarada, o Victor caiu logo depois do FULL CONNECT, quando a MatchZy ia executar o
   warmup ao detectar o primeiro jogador:

   ```
   16:04:00.761  SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL
   16:04:01.742  [MatchZy] [FULL CONNECT] First player has connected, starting warmup!
   16:04:01.880  [StartWarmup] Executing Warmup CFG from MatchZy/warmup.cfg
   16:04:01.887  DISCONNECTING. ProcessMessages has taken more than 237ms
   16:04:01.905  Long frame: 256.89ms elapsed, 256.20ms sim time
   ```

   Isso não é evidência contra o plugin religado. Só conta o que acontece com o jogador já
   dentro, depois de FULL + 60 s: essa regra de veredito segue valendo.

   A explicação é que caiu. O P1.13 (`945d9b0`, [engine-cs2](../armadilhas/engine-cs2.md), H1) mediu: em 26/09 o tempo
   foi gasto no handler de FULL CONNECT, e o `execing MatchZy/warmup.cfg` só saiu no frame seguinte; em 04/10 a queda veio
   antes de qualquer ação da MatchZy, já na CSSharp 1.0.375, o que enfraquece também a hipótese do offset de `Respawn` da 373.
2. **RayTrace na segunda troca de mapa.** O RayTrace aborta na segunda troca de mapa de uma
   sessão, com `logger with name 'RayTrace' already exists` e core dumped (compose:93-108).
   Ele foi mascarado no mesmo commit que a suíte de bots, então um crash anterior a esse
   commit pode ter sido dele. Com Metamod 1459 ou mais novo, o nativo nem carrega. Diante de
   um crash na segunda troca de mapa, confira o `meta list` antes de culpar o plugin religado.
3. **Update do CS2 pelo SteamCMD no boot.** Todo start do container roda o update do app 730.
   Se sair uma build nova durante a janela, mudaram duas variáveis. Registre a build antes e
   depois (RCON `version`). Se ela mudou, anote "2 variáveis" e não conclua nada sobre o
   plugin.
4. **Ruídos conhecidos:**
   - `SIGSEGV` em `libtier0.so` no runtime .NET 10, causado pelo mutex nomeado do Serilog
     (CSSharp #1427). É aleatório, inclusive na troca de mapa, e afeta a 373 e a 375. Um
     segfault desses, sozinho, não condena o plugin: olhe o backtrace.
   - `Unknown command 'bv_reveal'`: é um comando do BotVision, que não está mascarado e talvez
     nem esteja instalado. É ruído, não regressão.
   - Com CSSharp 1.0.375 ou mais nova:
     - #1446: Stack overflow no ChangeTeam/SetPawn de bot, aberta em 26/09. Derruba o
       servidor.
     - #1443: o humano nasce fora do mapa no warmup, depois de SwitchTeam + Respawn. Está
       corrigida só na master. Mata no warmup, sem derrubar.

## Regras

- **Uma variável por experimento.** Um passo é uma linha do compose. A única exceção é o
  B1.3r: o par Metamod + CSSharp conta como uma variável, porque um não roda sem o outro
  (B1.1). A sessão anterior errou três vezes por concluir a partir de uma observação só.
- **Nunca `docker compose down -v`.** Também nunca `down`, `volume rm` ou `prune`. O volume
  `cs2-tracker_cs2-data` tem ~73 GB de CS2 e a instalação manual dos plugins, que não é
  reproduzível. Nunca use `FORCE_DELETE_ADDONS=true`, que apaga `addons/` inteiro.
- **Nunca sobrescreva arquivo que o servidor tem mapeado enquanto ele roda.** Em 26/09, um
  `cp` do `botprofile.vpk` matou o processo com
  `FATAL ERROR: Error reading from loaded packed store` (bafe2b4).
- **Pare o container antes de trocar VPK ou DLL.** Vale para o `Cs2TrackerEvents.dll` (B1.2)
  e para o DLL do BotRandomizer (B1.9). O VPK também só troca assim; a variante vigente está
  no [AGENTS.md](../../AGENTS.md).
- **A TUI fica.** `wizard_tui.py` fica sem diff, e o Victor joga por ela durante toda a
  trilha. Nada aqui a aposenta.
- **Compose só do checkout principal** (`C:/Users/Victor/Projetos/cs2-tracker`), com
  `docker compose up -d --force-recreate`. O `restart` não aplica env nem mount, e o compose
  rodado de uma worktree monta o volume vivo com os binds dela ([reconstruir-volume](reconstruir-volume.md)).
- **Snapshot antes de qualquer escrita no volume**, seja a extração da imagem no B1.3r ou uma
  restauração.
- **Janela só por frase do Victor:** "pode mexer no servidor" (Q4=A, no máximo 45 min) ou,
  na trilha de bots, "terminei" (Q5=A, 15 a 30 min). Aborta se ele abrir o jogo ou a TUI, e
  nunca abre por ausência de processo. O B1.3r não cabe numa janela de "terminei" e pede a
  Q4.
- **Um candidato por vez** (Q6=A). Partida só de bots dentro da janela é permitida (Q7=A).
- **Download de versão ou de plugin só com OK explícito do Victor** (G5).
- **Critério de aceite de card não se reescreve.** Se estiver errado, registre e pare, como
  aconteceu no B1.3.

## Como um passo chega ao jogo

1. O PR do card traz a linha. O tech-manager o mergeia logo depois do QA, a qualquer hora, e o
   merge na main vira o `candidato-N`. Nenhum boot fora da janela aplica a mudança: um boot só
   aplica o que está no checkout principal, e só o servidor leva o candidato até lá, pelo ff
   feito dentro da janela (fora dela, o ff recusa infra).
2. A janela abre depois do "terminei" (pós-partida, até 30 min) ou do "pode mexer no
   servidor" (pré-partida, até 45 min). Nela: preflight, backup, ff do checkout para o
   candidato, snapshot, `--force-recreate`, G6 e, quando o card pede, o
   [smoke só de bots](smoke-partida-de-bots.md). Passo
   que não cabe em 30 min, como o B1.3r, espera uma janela "pode mexer no servidor".
3. O Victor recebe o aviso do que a próxima partida valida.
4. Ele joga uma partida normal. Depois vêm a coleta dos logs e a evidência (G7).
5. Com o G7 ok: tag `jogavel-<data>` e uma linha no registro abaixo. Com o G7 ruim: volta pelo
   runbook do passo, e o plugin volta a ficar mascarado. O checkout fica na tag até o revert
   e só sai dela pelo ff sem janela, com o delta conferido: infra no delta espera o passo 3
   da próxima janela.

A via rápida (Q0=A) valeu para o passo 1. Enquanto o `tools/jogavel.py` (B0.7/B0.7b) não existir, os passos seguem runbooks próprios com comandos à mão (decisão do PM em 27/09, para a trilha não parar): [B1.4](b1.4-botaimimprover.md). Quando o `jogavel.py` chegar, ele substitui os comandos crus.

## Registro

Preencha uma linha por passo, na janela e depois da partida. Se o passo voltar e for refeito, use uma
linha nova com o mesmo passo e sufixo (ex.: `2b`). A coluna "Smoke só de bots" traz o resultado do
[runbook do smoke](smoke-partida-de-bots.md#resultado). A variante do VPK e a época (critério 8) entram
nas [Notas por passo](#notas-por-passo), como lida (com o sha e a hora) ou inferida (com a origem).

### Janela (G6)

| Passo | Janela (data, hora, frase que abriu) | Mudança efetiva | Build CS2 antes → depois | Snapshot (arquivo, sha256 abreviado) | G6 (load lines, assinaturas) | Smoke só de bots |
|---|---|---|---|---|---|---|
| 1 · B1.3r | 27/09 01:44 ("pode mexer no servidor"); vencida 2× por espera de aprovação, renovada 08:08 com OK; fechada 09:41 | Metamod 2.0.0.1411→2.0.0.1469, CSSharp v1.0.373→v1.0.375 | 2000918 → 2000918 | volume-addons-0144.tgz, 89556340… | complete 1469 e 375; MatchZy e captura carregadas; 0 linha proibida (FireOutputInternal sumiu); RayTrace/BotHider recusados (mascarados) | inconclusivo: bots não entram sem humano (faltou `bot_join_after_player 0`) |
| 2 · B1.4 | 27/09 15:20–15:23 ("terminei") | máscara do BotAimImprover removida (versão do volume) | igual | não precisa (sem escrita no volume) | BotAimImprover INATIVO: `PickNewAimSpot signature resolved to zero address` | — |
| 2b · B1.4b | 27/09 15:44–15:56 ("Pode juntar") | BotAimImprover do upstream `c3d10f5` por bind mount + VPK Medium (15:34) | igual | não precisa (bind mount) | `[BotAimImprover] Loaded (Linux)`; sha no container = manifesto | — |
| 3 · B1.5 | 27/09 18:38–18:56 ("terminei") | máscara do BotState removida (versão do volume) | igual | não precisa | Smarter-Bot 1.9.4 carregado, sem falha de assinatura; `BotController API not available` | OK: 10 bots em mirage e de novo após troca de mapa; 0 crash |
| 4 · B1.6 | 27/09 19:52–20:17 ("fechei o jogo, pode seguir") | máscara do BotBuy removida (volume) | igual | não precisa | BotBuyPatch 1.0.12 carregado; 0 linha proibida | OK: bots entram antes e depois da troca (readição com o mapa assentado) |
| 5 · B1.7 | — | **pulado** (decisão do Victor, 27/09): BotAI escreve por offset fixo do CCSBot (`0x5100+0x0C`), da build 14172 e não conferido depois do update de 23/09 (B1.7a, 13/10: deslocado −8, `0x50F8` na 2000930); upstream sem correção desde 27/08 | — | — | — | — |
| 6 · B1.8 | 27/09 21:17–21:28 ("terminei") | máscara do NadeSystem removida (volume) | igual | não precisa | NadeSystem 1.2.1, "3703 grenades in DB"; sem EmitSoundFilter | OK: 5 rounds, 0 crash, replays de smoke/flash; 182 cegueiras |
| 7 · B1.9 | 27/09 22:29–22:37 ("pode aplicar", Victor no PC) | BotRandomizer do upstream `276f1ce` (com a correção `18d1510`) por bind mount, no lugar da máscara | igual | não precisa (bind mount) | BotRandomizer 1.3.2, "Catalog loaded: 35 weapons, 1456 weapon paints, 10565 stickers, 81 charms"; 0 `signature failed`; sha no container = manifesto (5/5) | OK: 10 bots em mirage e de novo após a troca para inferno (readição); 0 crash, 0 exceção do BotRandomizer |
| 5b · B1.7 | 14/10 20:57–21:24 ("pode mexer no servidor", Victor no PC) | máscara do BotAI trocada pelo bind de `./docker/plugins/BotAI` (fork 1.8.12-b1.7b, `412416b`) | 2000930 → **2000931** (SteamCMD no 1º recreate; volta à máscara, conferência do fork na 2000931 com `RESULTADO: OK`, 2º recreate) | não precisa (bind mount) | `B1.7b: m_gameState = 0x50F8`, `Applied 40/40 patches.`; 0 `FAILED`, `patch disabled` ou `NAO resolvido`; 9 plugins carregados; sha no container = checkout (17/17), BotAI = manifesto | OK: 10 bots em mirage e de novo após a troca para inferno (readição); 0 crash, 0 exceção do BotAI; bomba plantada sem evidência no log (ficou para o G7) |

### Partida (G7)

| Passo | Partida (`demo_name`, mapa) | Troca de mapa | Segfault | Overflow pós FULL + 60 s | Ingerida | Veredito | Época a partir de |
|---|---|---|---|---|---|---|---|
| 1 · B1.3r | events_63_map0, de_inferno (partida 26, 13x7, 5x5) | não (MD1) | 0 | 0 (nenhum overflow) | sim | **OK** (config-hash 55765314… igual) | jogavel-2026-09-27 |
| 2 · B1.4 + 2b · B1.4b | events_64_map0, de_dust2 (partida 27, 13x8, 5x5) | não (MD1) | 0 | 0 (1 overflow só no signon) | sim | **OK** (após correção do detector, PR #15) | jogavel-2026-09-27-2 (VPK Medium) |
| 3 · B1.5 | events_65_map0, de_inferno (partida 28, 13x8) | não | 0 | 0 | sim | **OK** | jogavel-2026-09-27-3 |
| 4 · B1.6 | events_66_map0, de_dust2 (partida 29, 13x8) | não | 0 | 0 | sim | **OK** · armas distintas dos bots 17 (ref. 11) | jogavel-2026-09-27-4 |
| 5 · B1.7 | — | — | — | — | — | pulado | — |
| 6 · B1.8 | events_67_map0, de_dust2 (partida 30, 5x13) | não | 0 | 0 | sim | **OK** · cegueiras de bot 10,17/rd (ref. 3,33) | jogavel-2026-09-27-5 |
| 7 · B1.9 | events_68_map0, de_dust2 (partida 31, 3x13) | não | 0 | 0 | sim | **OK** · skins confirmadas pelo Victor | jogavel-2026-09-28 |
| 5b · B1.7 | events_83_map0, de_nuke (partida 83, 13x3, 5x5) | não (MD1; o `loadmatch` trocou de_mirage → de_nuke) | 0 | 0 | sim (id 48) | **OK** (`--build-esperada 2000931`) · BotAI 40/40 do boot ao fim; 12 bombas plantadas (3 por bot, 9 pelo Victor) e 2 defuses, os dois de bot | jogavel-2026-10-14-3 (build 2000931) |

### Notas por passo

Assinaturas que falharam, pelo nome; plugins recusados no `meta list`; impressão do Victor, se vier (não bloqueia).

- **1 · B1.3r:** nenhuma assinatura falhou. RoundDamageRecap (ed0ard) carregado e sem máscara. O container reiniciou às 13:48 sem recreate (config-hash igual). Jogo "liso" na impressão do Victor.
- **2 · B1.4:** o BotAimImprover do volume (05/09) não carrega na build atual; a correção veio do upstream (B1.4b). Bots da partida 27 (com B1.4b + Medium): 14 utility + 19 flash, 63 cegueiras. Impressão do Victor: "bem desafiador e bem maneiro de jogar".
- **3 · B1.5:** Victor: K/D 0,41, ADR 46 na partida 28 (média até 26/09: K/D 2,93, ADR 130) — "beeem mais desafiador". BotController não disponível: do volume só consta a API compartilhada (`counterstrikesharp/shared/BotControllerApi/BotControllerApi.dll`), sem o plugin nem o nativo (ver [Sobras](#sobras), 2): recursos do Smarter-Bot que dependem dele ficam desligados até a B2. No smoke, depois do `changelevel` a quota volta a zero no load: é preciso readicionar os bots para testar a entrada deles no mapa novo ([smoke só de bots](smoke-partida-de-bots.md#armadilhas), armadilha 2).
- **4 · B1.6:** CTs trocaram a AUG pela M4A1 (146 vs 30 hits); entropia de armas 3,18 bits (ref. 2,54). Com BotState + BotBuy os bots deixaram de usar granada (0 dano/cegueira nas partidas 28 e 29).
- **5 · B1.7:** pulado. Religar só com correção upstream do offset `m_gameState` do CCSBot, ou após verificação do offset na build atual. **Verificação do B1.7a** (13/10, offline, só leitura), na build **2000930** (PatchVersion 1.41.9.0, VersionDate Oct 08 2026), a do container na janela de diagnóstico de 13/10 e das partidas 79 e 80 ([versoes-conhecidas](versoes-conhecidas.md)): **DESLOCADO −8**, o `m_gameState` passou de `0x5100` para `0x50F8`; o `+0x0C` é **igual**. *Insumo:* a cópia do `libserver.so` da janela de 13/10 (B1.12b), `C:/Users/Victor/cs2-tracker-backups/2026-10-13/janela-diag/libserver-2000930/libserver.so`, 41724600 bytes, sha256 `c7741272…3cac5a` conferido antes da análise ([hashes](versoes-conhecidas.md#hashes-completos)). *Método, para reproduzir:* sem disassembler na máquina, busca de padrão em bytes com a biblioteca padrão do Python da `.venv`, num script fora do repo. O parse do ELF64 dá a `.text` no offset de arquivo `0x9fdbc0`, com `0x1af73df` bytes (VA = offset de arquivo + `0x1000`). O binário não tem `.symtab`, só `.dynsym`: os nomes de função vêm dos comentários do upstream (`LinuxPatchDefinitions.cs:17`, `:330` e `:349`), e o número sai sempre do `disp32`. As assinaturas são as do próprio BotAI com o `disp32` em curinga (`?`), e só a instrução que carrega o offset é decodificada à mão; cada padrão abaixo casa uma única vez na `.text`. *`m_gameState`, 1ª fonte:* `DefuseBombState::OnUpdate` (`LinuxPatchDefinitions.cs:351` com curinga), `55 48 8D BE ? ? ? ? 48 89 E5 41 54 53 48 89 F3 E8 ? ? ? ? BE 02 00 00 00 48 89 DF 49 89 C4 E8 ? ? ? ?`, casa no arquivo `0xc8c380` (VA `0xc8d380`) com `55 48 8d be f8 50 00 00`, ou seja, `lea rdi,[rsi+0x50F8]`, em que `rsi` é o `CCSBot *me`. *2ª fonte:* `CSGameState::OnBombPlanted` (`:335` com curinga), `48 8B 83 ? ? ? ? 48 8B 40 18 80 B8 24 06 00 00 02 0F 84 ? ? ? ? 48 8B 7B 18`, casa no arquivo `0xc20c89` (VA `0xc21c89`) com `48 8b 83 f8 50 00 00` (`mov rax,[rbx+0x50F8]`). As duas assinaturas exatas do 1.8.9 (`00 51 00 00`) não casam nenhuma vez. *Contraprova:* entre os `lea`/`mov` (`8D`/`8B`/`89`, modrm mod=10, sem SIB) da `.text`, o `disp32` `0x50F8` aparece 20 vezes, o `0x5100` nenhuma e o `0x5104` (`0x50F8+0x0C`) 6. O `0x5100` só aparece como `disp32` em dois acessos de byte, `c6 83 00 51 00 00 01` (arquivo `0xbeb547`) e `80 b8 00 51 00 00 00` (arquivo `0xc12a8d`): é o `m_isRoundOver`, `0x50F8+0x08`, e não o início do `CSGameState`. *Campo em `+0x0C`:* o `CSGameState::Reset` de `LinuxPatchDefinitions.cs:19` casa exato, `C6 47 08 00 48 89 07 48 C7 47 0C 00 00 00 00 C7 47 14 00 00 00 00 C3`, no arquivo `0x14f4ca7` (VA `0x14f5ca7`), e com os três offsets em curinga o casamento único é o mesmo: `m_isRoundOver` em `+0x08` e `m_bombState` em `+0x0C` (`BotAI.cs:21-22`), sem mudança. Na 2000930, o `m_bombState` do CCSBot fica em `0x5104`. *Controle da técnica:* o `PickNewAimSpot` do BotAimImprover em uso (bullseye, `BotAimImprover.cs:116-117`): a assinatura `55 48 89 E5 41 55 41 54 53 48 89 FB 48 83 EC 58 8B 8F ? ? 00 00 83 F9 FF` casa uma vez, no arquivo `0xbf6c10` (VA `0xbf7c10`), com `disp32` `0x59D8`, o `m_enemy` do fix `2e27900`/`c3d10f5` (antes, `0x59E0`); no corpo, `80 BB DC 59 00 00 00` (o bool `m_isEnemyVisible` em `0x59DC`) aparece duas vezes, o antigo `0x59E4` nenhuma, e o `m_targetSpot` é gravado em `0x596C`. Os campos que o BotAimImprover corrigiu batem na 2000930, e isso valida a técnica. *Comparação:* o `m_gameState` era `0x5108` antes do update de 09/07 e passou a `0x5100` na build que o upstream chama de 14172: as assinaturas `48 8B 83 08 51 00 00` e `55 48 8D BE 08 51 00 00` viraram `00 51 00 00` no `eedceee` (19/07) do CS2-Bot-Improver (clone `cbi/`), e a constante virou `0x5100` no `f746074` (30/07); no 1.8.9 (clone `botai/`, `1bcd6db`) ela está em `BotAI.cs:17-19`. Na 2000930 vale `0x50F8`: **deslocado −8**, o mesmo −8 que o fix do BotAimImprover (`2e27900`, mergeado no `c3d10f5`) aplicou à faixa `0x59xx` (`0x5974`/`0x59E0`/`0x59E4` → `0x596C`/`0x59D8`/`0x59DC`) e que o update de 09/07 já tinha aplicado de `0x4F5C` a `0x5E10` (`eedceee`). O campo que o BotAI zera (`0x5100+0x0C = 0x510C`) **não é mais o `m_bombState`** (`0x5104`). *Efeito do 1.8.9 como está, na 2000930:* as duas assinaturas com o offset (`OnBombPlanted_AllBotsLearnSite` e `DefuseBombState_OnUpdate_EngageAndInvestigate`) não casam e caem limpas, com `signature not found`, mas o `UpdateBotBombState` não tem assinatura (`BotAI.cs:224-240`): a cada spawn de bot ele leria o byte em `0x5108` (`m_gameState+0x10`, não o `m_isRoundOver`) e zeraria o Int32 em `0x510C` (`m_gameState+0x14`, um campo real do `CSGameState`, que o `Reset` também zera com `C7 47 14 00 00 00 00`). É corrupção silenciosa, e o `m_bombState` nem chega a ser tocado. *BotAI.dll do volume:* está disponível offline no snapshot `volume-addons-0144.tgz` do B1.3r (`C:/Users/Victor/cs2-tracker-backups/2026-09-27/b1.3r/`), em `counterstrikesharp/plugins/BotAI/BotAI.dll` (39424 bytes, mtime 04/09 22:19, sha256 `389814db…5e694b`). Extraído fora do repo e lido, tem `ModuleVersion` "1.8.9" (string UTF-16 única, nenhum "1.8.8"), as constantes `ldc.i4 0x5100` e `ldc.i4 0x5128` uma vez cada (sem `0x5108` nem `0x50F8`) e as assinaturas `48 8B 83 00 51 00 00` e `55 48 8D BE 00 51 00 00` em texto: é o 1.8.9 do clone `botai/`, e o efeito acima vale para ele. *Prévia offline, sem valor de G6:* das 43 assinaturas Linux do 1.8.9, 26 casam na 2000930 e 17 não (`Idle_IsSafeAlwaysFalse`, `EscapeFromBomb_OnEnter_NoEquipKnife`, `EscapeFromFlames_OnEnter_NoEquipKnife`, `SprayAllDistances_ForceHoldTrigger`, `AttackState_RetreatOnSniper_Disable`, `AttackState_SkipSniperSpreadCheck`, `AttackState_CanStrafe_jne`, `Vision_AlwaysWatchApproachPoints_Cave`, `Vision_AlwaysWatchApproachPoints`, `Vision_ApproachBody_SkipHidingSpotCheck`, `InViewCone_RemoveOuterFOV`, `OnAudibleEvent_GlobalHearRange`, `TBot_BombsiteSearch_UseKnownPlantedSite`, `OnBombPlanted_AllBotsLearnSite`, `DefuseBombState_OnUpdate_EngageAndInvestigate`, `DefuseBombState_OnEnter_EngageAndInvestigate` e `FlashbangAvoidance_Disable`); a lista que vale para o card continua sendo a do log da janela do B1.7. **Recomendação para o B1.7: não religar o DLL do volume como está, e manter mascarado até existir o fork corrigido compilado fora do repo**, como no B1.4b e no B1.9: o 1.8.9 lendo o `m_gameState` no load, pelo `disp32` da assinatura do `DefuseBombState::OnUpdate` com curinga e não pela constante, com o `UpdateBotBombState` desligado se ela não casar e com as duas assinaturas do offset também em curinga. Trocar só a constante por `0x50F8` volta a deixar a escrita sem guarda no próximo update do SteamCMD, que já trouxe quatro builds sem OK prévio ([Épocas](#épocas)). Antes da partida do Victor, um smoke só de bots. Com 17 dos 43 patches já perdidos na 2000930, cabe ao Victor decidir se o fork compensa. **5b · B1.7 (14/10):** religado pelo fork do B1.7b (1.8.12-b1.7b, base 1.8.12 aceita pelo Victor), na build 2000931: nenhuma entrada falhou (40/40 na janela e na partida 83), e a conferência do fork na 2000931 rodou antes do G6. Impressão do Victor depois da partida 83: "não senti muita diferença nos bots" (dado para decidir manter o fork, não critério). Detalhe em [Religar o BotAI pelo fork](#religar-o-botai-pelo-fork).
- **6 · B1.8:** granadas voltaram (324 replays na partida 30). Aviso do engine "Grenade has no weapon info" nas granadas replayed: a contagem de utility do motor não credita o bot. Victor: 9/13, K/D 0,69, primeira derrota da trilha.
- **7 · B1.9:** nenhuma assinatura falhou (0 `signature failed` e 0 `cosmetics disabled` na janela e na partida). Skins, facas e luvas confirmadas pelo Victor. O `5dfe948` do plano é do CS2-Bot-Improver (clone `cbi/`), não do CS2-Bot-Randomizer compilado: lá a correção de assinatura é o `18d1510`, ancestral do `276f1ce`. Avisos iguais aos da partida 30: 3 `Error invoking callback` do BotBuyPatch e "Grenade has no weapon info" (ver [Sobras](#sobras)).
- **8 · B1.10:** fechamento offline, sem janela nem partida: [Épocas](#épocas) e [Fechamento](#fechamento).

### Épocas

Cada linha é um estado do servidor que muda o comportamento dos bots. A hora (-03) é a do
recreate ou da troca. Para as estatísticas (coluna `bot_suite`, S2.4), a fronteira é o
`demo_name`: nenhuma partida caiu no meio de uma mudança.

| Época | Desde | Mudança | Plugins de bot ativos (acumulado) | VPK | Build CS2 | Partidas | Tag |
|---|---|---|---|---|---|---|---|
| 0 | ponto de partida (`efcaa42`) | Metamod 2.0.0.1411 + CSSharp v1.0.373; suíte mascarada desde o `193cd6c` (25/09) | nenhum: IA e mira vanilla | High | 2000918 em 27/09 | anteriores à 26; a `events_60` é a linha de base do B1.6 e do B1.8 | jogavel-2026-09-26 |
| 1 · B1.3r | 27/09 08:23 (candidato-1) | Metamod 2.0.0.1469 + CSSharp v1.0.375 | nenhum | High | 2000918 | 26 (`events_63_map0`) | jogavel-2026-09-27 |
| 2 · B1.4 | 27/09 15:21 (candidato-2) | BotAimImprover do volume, inativo pela guarda | nenhum | High | 2000918 | nenhuma | — |
| VPK Medium | 27/09 15:34:27 | VPK High → Medium, a pedido do Victor | nenhum | Medium | 2000918 | nenhuma | — |
| 2b · B1.4b | 27/09 15:54 (candidato-3) | BotAimImprover do upstream `c3d10f5`, ativo | BotAimImprover | Medium | 2000918 | 27 (`events_64_map0`) | jogavel-2026-09-27-2 |
| 3 · B1.5 | 27/09 18:45 (candidato-4) | BotState (Smarter-Bot 1.9.4) | + BotState | Medium | 2000918 | 28 (`events_65_map0`) | jogavel-2026-09-27-3 |
| 4 · B1.6 | 27/09 20:10 (candidato-5) | BotBuy (BotBuyPatch 1.0.12) | + BotBuy | Medium | 2000918 | 29 (`events_66_map0`) | jogavel-2026-09-27-4 |
| 6 · B1.8 | 27/09 21:17 (candidato-6) | NadeSystem 1.2.1 | + NadeSystem | Medium | 2000918 | 30 (`events_67_map0`) | jogavel-2026-09-27-5 |
| 7 · B1.9 | 27/09 22:30 (candidato-7) | BotRandomizer 1.3.2 | + BotRandomizer | Medium | 2000918 | 31 (`events_68_map0`) | jogavel-2026-09-28 |
| VPK Low | 28/09 19:54:52 (VPK) e 19:59:26 (build 2000919); build 2000922 em 30/09 23:10 | VPK Medium → Low, a pedido do Victor; no mesmo boot, o steamcmd da imagem atualizou o CS2 sem OK prévio (G5); o restart da janela de 30/09 levou à 2000922 | os mesmos da 7 | Low | 2000919 → 2000922 | 36 (matchid 71, `events_71_map0`, de_ancient 13x7, 01/10, G7 OK na 2000922). Ressalva: a `events_69` (partida 32, de_dust2 13x6, 30/09 15:59) e a `events_70` (MD3, 30/09, antes da janela) já jogaram o Low na 2000919, sem G7 | **validada**: jogavel-2026-10-01; em vigor na jogavel-2026-10-03 (B0.8, só o volume external, matchid 74) |
| Build 2000924 | 04/10 14:18, no boot que seguiu o segfault de 14:15 (B1.12) | o steamcmd da imagem atualizou o CS2 no boot, sem janela nem OK prévio (G5) | os mesmos da 7 | Low (inferido: [versões conhecidas](versoes-conhecidas.md#tags-jogáveis)) | 2000924 | 78 (matchid 78, `events_78_map0`, de_cache 13x8, 05/10, G7 OK). A 76 (04/10) já jogou nela, sem G7 | **validada**: jogavel-2026-10-12 |
| Build 2000930 | 12/10 18:37, no boot | o steamcmd da imagem atualizou o CS2 no boot, sem janela nem OK prévio (G5) | os mesmos da 7 | Low (inferido) | 2000930 | 79 (matchid 79, de_mirage 13x2, 12/10), confirmação | **validada**: jogavel-2026-10-12 |
| 5b · B1.7 + build 2000931 | 14/10 21:16 (candidato-13); a build 2000931 veio no recreate de 21:03, na mesma janela | BotAI do fork 1.8.12-b1.7b, por bind; a build nova é a 2ª variável (confundidor 3), coberta pela conferência do fork nela antes do G6 | os mesmos da 7 (o BotRandomizer é o b1.9b desde 14/10 19:07, `jogavel-2026-10-14-2`) + BotAI | Low (inferido) | 2000931 | 83 (matchid 83, `events_83_map0`, de_nuke 13x3, 14/10, G7 OK) | **validada**: jogavel-2026-10-14-3 |

- A época do VPK se prova pelo sha256 do VPK ativo lido no volume (critério 8 dos
  [Critérios de sucesso](#critérios-de-sucesso-de-cada-passo)). O RoundDamageRecap faz a mesma
  comparação e anuncia, por exemplo, "BOT Difficulty: Low [1/3]", mas só no chat do jogo: é
  relato do Victor, não evidência coletável.
- As versões e as tags desta tabela entram na lista de versões conhecidas, que é do card B0.3.

## Fechamento

Card B1.10, em 28/09, offline. Fontes: o registro acima, os registros das janelas de 27/09 e
28/09 (`logs/janelas/`, fora do git) e as coletas em `C:/Users/Victor/cs2-tracker-backups/`
(`2026-09-27/` e `2026-09-28/`).

| Alvo | Passo | Veredito | No ar |
|---|---|---|---|
| Metamod + CSSharp | 1 · B1.3r | religado | 2.0.0.1469 + v1.0.375, da imagem |
| BotAimImprover | 2 · B1.4 e 2b · B1.4b | religado (o do volume ficou inativo) | upstream `c3d10f5`, bind mount |
| BotState (Smarter-Bot) | 3 · B1.5 | religado, sem os recursos que dependem do BotController | 1.9.4, do volume |
| BotBuy (BotBuyPatch) | 4 · B1.6 | religado | 1.0.12, do volume |
| BotAI | 5 · B1.7 (pulado em 27/09) e 5b · B1.7 | religado em 14/10 (5b), 40/40 | fork 1.8.12-b1.7b (`412416b`), bind mount |
| NadeSystem | 6 · B1.8 | religado | 1.2.1, do volume |
| BotRandomizer | 7 · B1.9 (e B1.9b, 14/10: [sobra 7](#sobras)) | religado | 1.3.2, upstream `276f1ce` com o `4628750` (B1.9b), bind mount |
| RayTrace/RayTraceImpl, BotHider/BotHiderImpl | fora da B1 | mascarado | — |
| BotVision, BotController | fora da B1 | ausentes do volume (do BotController, só a API compartilhada) | — |

Nenhum plugin que ficou no ar tem assinatura falhando, nem na janela nem na partida. A única
falha da trilha foi a `PickNewAimSpot` do BotAimImprover do volume (B1.4), trocado pelo do
upstream. O BotAI ficou fora deste fechamento; o fork o religou em 14/10, com 40/40 (5b).

### Sobras

1. **BotAI:** não é mais sobra. O 1.8.9 do volume escreve Int32 zero em `CCSBot+0x5100+0x0C` a cada
   spawn, offset da build 14172, e o B1.7a (13/10) achou o `m_gameState` deslocado −8, em `0x50F8`,
   na 2000930 ([passo 5](#notas-por-passo)). Religado em 14/10 pelo fork do B1.7b, que lê o offset
   por assinatura (5b, [religar pelo fork](#religar-o-botai-pelo-fork)); o 1.8.9 não é usado.
2. **Nativos do Metamod, para a B2:** RayTrace/RayTraceImpl e BotHider/BotHiderImpl seguem
   mascarados (no boot, `[META] Failed to load plugin ... File not found`, efeito da máscara).
   O BotVision não está no volume, e o BotController só em parte: o snapshot
   `volume-addons-0144`, de 27/09, tem
   `counterstrikesharp/shared/BotControllerApi/BotControllerApi.dll`; faltam só o plugin e o
   nativo. Efeitos: o Smarter-Bot loga `BotController API not available` e desliga o que
   depende dele, e `Unknown command 'bv_reveal'` é ruído.
3. **BotBuyPatch:** 3 `Error invoking callback` (`ArgumentNullException` em `get_PlayerPawn`,
   nos 3 callbacks do `OnRoundStart`: `BotBuy.cs:258`, `:231` e `:213`, em
   `docker-logs.txt:538`, 550 e 562 da coleta da partida 31) no warmup do changelevel. Foram
   iguais nas partidas 30, 31 e 36 (esta no warmup do 1º mapa, build 2000922), sem efeito visto:
   ruído conhecido.
4. **NadeSystem:** "Grenade has no weapon info" nas granadas replayed (141 avisos na partida
   30, 68 na 31). A contagem de utility do motor não credita o bot. É o card B1.8b.
5. **Época VPK Low:** validada em 01/10 (partida 36, `jogavel-2026-10-01`, build 2000922). O
   Low e a build entraram juntos (confundidor 3); a `events_69` e a `events_70` já jogaram o Low
   na 2000919, sem G7.
6. **Fora da trilha:** o GOTV não grava `.dem` desde 21/09
   (`CDemoFile::Open: couldn't open file ... for writing`). Já é a Q12, no S1.2.
7. **BotRandomizer na build 2000930, corrigido pelo B1.9b em 14/10:** do boot de 12/10 (21:37Z)
   à janela do B1.9b, as armas dos bots vinham sem skin, e as facas com skin (relato do Victor,
   card K1.12). O log tinha um erro só por boot, no primeiro `GiveNamedItem` (12/10 21:38:43Z):
   `Failed to prepare a weapon item view`, com `NativeException: Invalid function pointer` em
   `WeaponItemViewStore.cs:57`, a chamada do construtor de `CEconItemView`. Nos boots de 04/10 e
   05/10 (2000924), nenhum erro do BotRandomizer. Fontes: `skins-extrato.txt` da coleta
   `2026-10-13/coleta-g7-p1.1/` e o log reconstruído da `2026-10-12/coleta-g7-candidato-9/`.
   Mecanismo, conferido no `libserver.so` da 2000930 pelo [B1.9b](b1.9b-botrandomizer-2000930.md):
   a assinatura do construtor deixou de casar, e a CSSharp devolveu handle zero sem `signature
   failed`; faca e luva vão pelo `CosmeticApplicator` (`BotRandomizer.cs:445-452`), que só usa
   a de `SetOrAddAttributeValueByName`. Sem crash nas partidas 79, 80 e 81. O `4628750` do
   upstream trouxe a assinatura nova, e com ele a janela de 14/10 e a partida 82 saíram sem o
   erro (`jogavel-2026-10-14-2`, [versões conhecidas](versoes-conhecidas.md)). Não é mais sobra.

### Recomendação para a Q16 (etapa 2: nativos)

(A), como no plano, começando só quando a época VPK Low tiver uma partida validada e a P1
estiver estável. Duas coisas mudaram desde o plano:

- O Metamod 1469 e a CSSharp 1.0.375 estão no ar desde o B1.3r. O B2.2 ("Subir o Metamod")
  fica absorvido, e o B2.1 se reduz a conferir as versões corrigidas (BotHider v0.5.0,
  BotVision v0.3.0, BotController v0.7.0) contra o par atual. Sobra o B2.3, um nativo por
  partida.
- O BotAimImprover do upstream traça a visada com o `Trace` da própria CSSharp
  (`BotAimImprover.cs:407-417` em `c3d10f5`), não com o RayTrace. Já o NadeSystem 1.2.1
  referencia o RayTrace, mas de forma opcional: o `NadeSystem.dll` do volume pede a capability
  dele (`RayTraceAPI`, `raytrace:craytraceinterface`) para o `FlashHasLoS` e, sem ela, loga
  `FlashHasLoS: RayTrace not loaded, skipping`. Ele roda com o RayTrace mascarado desde o B1.8.
  É o caso que o B2.5, condicional, testaria.

O ganho mais visível é o BotController, que o Smarter-Bot já espera. Mas cada nativo muda o
comportamento dos bots de novo, e a dificuldade acabou de mudar duas vezes a pedido do Victor:
uma época nova só se lê depois que a atual assentar. Dentro da B2, o B2.4
(`BOT_PROFILE_VARIANT`) é o de retorno mais imediato, porque tira do procedimento à mão a troca
de VPK, que já aconteceu duas vezes. A decisão é do Victor.

### Recomendação para a Q17 (o que sobrou quebrado)

(A) para as três sobras de plugin. Para o BotAI, a recomendação de 28/09 era a escolha de 27/09,
pular e esperar; é histórico desde 14/10, quando o fork religou o BotAI (abaixo).

- **BotAI:** ficou mascarado até o B1.7a achar o offset deslocado na 2000930 (`0x5100` → `0x50F8`).
  Voltou em 14/10 pelo fork corrigido fora do repo, num passo próprio (5b), com smoke só de
  bots. A (B), caçar à mão, não compensaria: o risco era corromper memória em silêncio, sem guarda.
- **BotBuyPatch e NadeSystem:** aceitos como estão. Nenhum dos dois derrubou partida, e o do
  NadeSystem só distorce a contagem de utility (B1.8b).
- A (C), PR no upstream, fica opcional e sem prazo.

## Religar o BotAI pelo fork

Passo 5 refeito pelo card B1.7, um degrau do trilho. Fica no fim do documento para não deslocar
as linhas que outras notas citam. O procedimento inteiro (fork, conferência, build, troca, G6,
volta) está no [runbook do B1.7b](b1.7b-botai-fork-assinatura.md); aqui fica o que a trilha
precisa para registrar o passo.

- **Por que o fork.** O B1.7a mostrou que o BotAI 1.8.9 do volume zeraria, a cada spawn de bot,
  um campo errado do `CSGameState` na build 2000930 ([passo 5](#notas-por-passo)). Em 14/10 o
  Victor trocou o critério do card (fork por bind, em vez de tirar a máscara) e aceitou a base
  1.8.12: o comportamento dos bots muda (8 patches em outro lugar, 3 novos, 6 a menos; a lista
  está no runbook do B1.7b). O 1.8.9 do volume não é usado: o bind cobre a pasta dele.
- **Mudança no compose.** A máscara `_empty` do alvo `counterstrikesharp/plugins/BotAI` (linha
  144 no `eb4cb0e`; 141 no `efcaa42`) vira o bind de `./docker/plugins/BotAI`, com três linhas
  de comentário acima. Nenhuma outra linha funcional muda. A pasta é gitignored, como as do
  B1.4b e do B1.9: o binário (AGPL) não entra no repo.
- **Pré-condições:** trilho livre (nenhum outro candidato esperando partida), o PR do B1.7
  mergeado, o build do fork feito e o manifesto registrado no runbook do B1.7b (seção Build),
  preflight 0 e janela aberta pelo Victor.
- **Só pelo servidor, em janela.** O compose novo é infra: só chega ao checkout principal pelo
  ff que o papel servidor faz dentro da janela ([como um passo chega ao jogo](#como-um-passo-chega-ao-jogo)).
- **A pasta antes do recreate.** `docker/plugins/BotAI/` precisa existir no checkout principal,
  com os 3 arquivos do manifesto e o sha256 conferido, **antes** do `--force-recreate`. Sem
  ela, o Docker cria uma pasta vazia, o plugin some sem erro no log e o passo parece
  "inativo" sem ter rodado. Enquanto a máscara está no ar, a cópia não toca no servidor vivo.
- **G6**, além dos [critérios de cada passo](#critérios-de-sucesso-de-cada-passo):
  1. Build do boot (`GC Connection established for server version`) e a **conferência das
     assinaturas do fork contra essa build**, pelo script do B1.7b, com `RESULTADO: OK`
     registrado: build, sha256 do `libserver.so` conferido e a última linha da saída. Com outra
     build que não a 2000930, a conferência roda sobre a cópia do `libserver.so` dela antes de
     religar ([a cada build nova](b1.7b-botai-fork-assinatura.md#a-cada-build-nova-do-cs2)).
     Saída 1 ou 2: o fork não religa, e a volta é decisão do PM.
  2. No log, o `m_gameState` resolvido e `Applied 40/40 patches.`; as linhas proibidas são as
     do G6 do runbook do B1.7b. Entrada que falhar vai **pelo nome** para as notas.
  3. sha256 dos 3 arquivos dentro do container igual ao manifesto. O `jogavel.py coletar`
     também os confere, porque a pasta é bind de `docker/plugins/`
     (`tools/jogavel.py:1305-1321`).
  4. Recomendação do B1.1, que não é critério: [smoke só de bots](smoke-partida-de-bots.md)
     até pelo menos uma bomba plantada, antes da partida do Victor (Q7=A).
- **G7**, a partida do Victor: zero segfault e nenhum overflow depois de `SIGNONSTATE_FULL` +
  60 s; MatchZy e captura carregadas e a partida ingerida; sha256 dos montados e config-hash
  iguais aos da janela. O que o Victor deve perceber está no G7 do runbook do B1.7b.
- **Conclusão do card**, uma destas:
  - **religado:** 40/40 patches, `m_gameState` resolvido, zero crash na janela e na partida;
  - **mascarado:** a máscara voltou, pela volta abaixo. Também é o caso em que o próprio fork
    se desliga (`NAO resolvido`): pelo vocabulário da trilha é **inativo**, que equivale a
    mascarado.
  - Para o BotAI não existe **degradado** em partida: o G6 exige 40/40 (decisão do PM, 14/10).
    Um load com alguma entrada desligada (o TBot no freio do B1.7c, 39/40, por exemplo) não vai
    para a partida do Victor, mesmo sem crash: volta à máscara, as entradas vão pelo nome para as
    notas e o caso vira card próprio.
- **Rollback**, se o G6 ou o G7 sair ruim: volta à máscara `_empty`, em janela, pelo papel
  servidor, do checkout principal: `git -C C:/Users/Victor/Projetos/cs2-tracker switch --detach <última tag jogavel-*>`
  e `docker compose up -d --force-recreate` (ou `jogavel.py voltar --tag <última jogavel-*>`,
  que recria quando o compose difere); depois, reverter o PR. Nunca `down`, `volume rm` ou
  `prune`. A pasta `docker/plugins/BotAI/` pode ficar: sem o bind, não é lida.
- **Registro.** Uma linha `5b · B1.7` nas tabelas de [janela](#janela-g6) e de
  [partida](#partida-g7), uma nota em [notas por passo](#notas-por-passo) com a saída da
  conferência e, com o G7 OK, a época nova, a linha do BotAI no [Fechamento](#fechamento) e a
  sobra 1. Feito pelo B1.7d (14/10), com o resultado abaixo.

### Resultado (14/10)

Fontes: o registro da janela de 14/10 (`logs/janelas/2026-10-14.md`, cópia em
`C:/Users/Victor/cs2-tracker-backups/2026-10-14/g7-b1.7-copia/`) e a coleta
`2026-10-14/coleta-g7-b1.7/`. Os hashes estão no [runbook do B1.7b](b1.7b-botai-fork-assinatura.md)
e em [versões conhecidas](versoes-conhecidas.md).

- **Janela** 20:57–21:24 (-03), aberta por "pode mexer no servidor". Build do fork `412416b`
  (manifesto em [build de 14/10](b1.7b-botai-fork-assinatura.md#build-de-1410-janela-do-b17)), conferência na 2000930 com `RESULTADO: OK` e ff do checkout
  principal para o `2619d70` (candidato-13).
- **Build nova no 1º recreate.** O SteamCMD trouxe a **2000931** (PatchVersion 1.41.9.1). O fork
  carregou com 40/40, mas sem conferência na build nova: o servidor voltou à máscara
  (`jogavel.py voltar --tag jogavel-2026-10-14-2`), copiou o `libserver.so` da 2000931 e rodou a
  conferência sobre ele (`RESULTADO: OK`, 40/40, `m_gameState` `0x50F8`, distância do TBot
  `0x2f0`) antes do 2º recreate. É a regra de [a cada build nova](b1.7b-botai-fork-assinatura.md#a-cada-build-nova-do-cs2)
  na prática: duas variáveis na mesma janela (confundidor 3), com a do CS2 conferida à parte.
- **G6:** `m_gameState = 0x50F8`, `Applied 40/40 patches.`, zero linha proibida do BotAI, zero
  segfault, 9 plugins, sha256 dos montados igual ao checkout (17/17), config-hash novo
  `837cbcbc…`. Smoke só de bots OK, sem prova de bomba plantada no log.
- **G7:** partida 83 (de_nuke 13x3, 5x5), `evidencia_partida.py --build-esperada 2000931` saiu 0.
  BotAI 40/40 do boot ao fim, sem nenhuma linha dele depois do boot; 12 `bomb_planted` (3 de
  bot, 9 do Victor) e 2 `bomb_defused`, os dois de bot, o que exercita o `OnBombPlanted` e o TBot. Os 3 `Error invoking
  callback` no changelevel são do BotBuyPatch ([sobra 3](#sobras)), já vistos com o BotAI
  mascarado. Partida ingerida (id 48). Tag `jogavel-2026-10-14-3` no `2619d70`.
- **Veredito:** religado. Com ele, todos os plugins de bot da B1 estão no ar.
- **Impressão do Victor**, depois da partida 83: "não senti muita diferença nos bots". É dado,
  não critério: pesa na decisão de manter o fork (que pede conferência a cada build nova do CS2)
  ou de voltar à máscara. A decisão é dele.
