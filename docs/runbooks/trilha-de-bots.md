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
| 141 | `counterstrikesharp/plugins/BotAI` | CSSharp | B1.7 |
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
| 5 | B1.7 | linha 141 (BotAI) | guarda forte nas 43 assinaturas, **mas** escreve num offset fixo de `CCSBot` a cada spawn de bot | pós-partida; smoke só de bots recomendado |
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
  Int32 zero em `CCSBot+0x5100+0x0C`. O offset é fixo, da build 14172 (PR #5, jul/26), e só
  é protegido por "endereço legível". Com o layout de `CCSBot` mudado, isso pode corromper
  memória em silêncio, sem assinatura que barre.
- Recomendação do B1.1, que não é critério do card: um [smoke só de bots](smoke-partida-de-bots.md)
  antes da partida do Victor (Q7=A permite).
- Registrar pelo nome quais das 43 assinaturas falham (card). No upstream, não há commit
  desde 27/08, e o PR #7 ("fix: Update sig") está aberto.

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

- O `try/catch` de `BotRandomizer.cs:95-130` é código morto: o construtor de
  `MemoryFunctionWithReturn` nunca lança, porque a CSSharp engole a falha e devolve zero. O
  `NativeAvailable` fica verdadeiro com handle zero (`WeaponItemViewStore.cs:30`). Cada
  chamada lança exceção, apanhada no catch "GiveNamedItem pre-hook failed" (316). O resultado
  é sem crash e sem skins.
- A correção upstream é o commit `18d1510` (24/09, "fix: Update sig", do PR #8 do upstream:
  assinatura nova de `SetOrAddAttributeValueByName` para Linux e Windows), com o csproj na
  CSSharp.API 1.0.375 no `276f1ce`, o commit compilado ([runbook](b1.9-botrandomizer-upstream.md)).
  O plano e o card B1.9 citam `5dfe948` e `d5cf9e0`, que não existem no clone do upstream
  (conferido no B1.10). O nome do card fica como está.
- A licença é AGPL-3.0, como a de todos os repositórios ed0ard. Por isso ele compila
  localmente, no container do SDK (o mecanismo de `docker/build-events-plugin.sh`), pelo papel
  servidor. Clone e download só com OK.

### Fora da B1

RayTrace/RayTraceImpl, BotHider/BotHiderImpl, BotVision e BotController são plugins nativos e
ficam para o sprint B2 (Q16). As versões corrigidas deles (BotHider v0.5.0, BotVision v0.3.0,
BotController v0.7.0) pedem Metamod 1469+ e CSSharp 1.0.375+. Se o B1.3r for aplicado, o B2.2
("Subir o Metamod") fica absorvido por ele, e sobra o B2.3 (nativos um por vez).

## Critérios de sucesso de cada passo

Valem na janela (G6) e na partida do Victor (G7). Todos precisam valer:

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

O veredito de cada passo é um destes:

- **religado:** carregou, sem assinatura faltando e sem crash;
- **degradado:** carregou com alguma assinatura faltando e segue ativo, sem crash;
- **inativo:** carregou, mas a própria guarda o desativou (ex.: a linha `Plugin inactive.`
  do BotAimImprover), sem crash. Na prática equivale a mascarado: o comportamento dos bots
  não muda;
- **mascarado:** a máscara voltou;
- **bloqueado:** depende de outra coisa.

## Confundidores: leia antes de culpar um plugin

1. **Overflow no signon causado pelo `warmup.cfg` da MatchZy.** Em 26/09 às 16:04, com a
   suíte mascarada, o Victor caiu no instante em que a MatchZy executou o warmup ao detectar
   o primeiro jogador:

   ```
   16:04:00.761  SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL
   16:04:01.742  [MatchZy] [FULL CONNECT] First player has connected, starting warmup!
   16:04:01.880  [StartWarmup] Executing Warmup CFG from MatchZy/warmup.cfg
   16:04:01.887  DISCONNECTING. ProcessMessages has taken more than 237ms
   16:04:01.905  Long frame: 256.89ms elapsed, 256.20ms sim time
   ```

   Isso não é evidência contra o plugin religado. Só conta o que acontece com o jogador já
   dentro, depois de FULL + 60 s. A investigação própria é o P1.13.

   Hipótese do B1.1, não testada: na 373, o offset de `Respawn` está errado (272; o certo é
   276), e a MatchZy chama `SwitchTeam` + `Respawn` no warmup. Se o overflow sumir depois do
   B1.3r, registre como observação, não como conclusão.
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
  rodado de uma worktree cria projeto e volume novos, vazios.
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

Preencha uma linha por passo, na janela e depois da partida. Se o passo voltar e for
refeito, use uma linha nova com o mesmo passo e sufixo (ex.: `2b`). A coluna "Smoke só de
bots" traz o resultado do [runbook do smoke](smoke-partida-de-bots.md#resultado).

### Janela (G6)

| Passo | Janela (data, hora, frase que abriu) | Mudança efetiva | Build CS2 antes → depois | Snapshot (arquivo, sha256 abreviado) | G6 (load lines, assinaturas) | Smoke só de bots |
|---|---|---|---|---|---|---|
| 1 · B1.3r | 27/09 01:44 ("pode mexer no servidor"); vencida 2× por espera de aprovação, renovada 08:08 com OK; fechada 09:41 | Metamod 2.0.0.1411→2.0.0.1469, CSSharp v1.0.373→v1.0.375 | 2000918 → 2000918 | volume-addons-0144.tgz, 89556340… | complete 1469 e 375; MatchZy e captura carregadas; 0 linha proibida (FireOutputInternal sumiu); RayTrace/BotHider recusados (mascarados) | inconclusivo: bots não entram sem humano (faltou `bot_join_after_player 0`) |
| 2 · B1.4 | 27/09 15:20–15:23 ("terminei") | máscara do BotAimImprover removida (versão do volume) | igual | não precisa (sem escrita no volume) | BotAimImprover INATIVO: `PickNewAimSpot signature resolved to zero address` | — |
| 2b · B1.4b | 27/09 15:44–15:56 ("Pode juntar") | BotAimImprover do upstream `c3d10f5` por bind mount + VPK Medium (15:34) | igual | não precisa (bind mount) | `[BotAimImprover] Loaded (Linux)`; sha no container = manifesto | — |
| 3 · B1.5 | 27/09 18:38–18:56 ("terminei") | máscara do BotState removida (versão do volume) | igual | não precisa | Smarter-Bot 1.9.4 carregado, sem falha de assinatura; `BotController API not available` | OK: 10 bots em mirage e de novo após troca de mapa; 0 crash |
| 4 · B1.6 | 27/09 19:52–20:17 ("fechei o jogo, pode seguir") | máscara do BotBuy removida (volume) | igual | não precisa | BotBuyPatch 1.0.12 carregado; 0 linha proibida | OK: bots entram antes e depois da troca (readição com o mapa assentado) |
| 5 · B1.7 | — | **pulado** (decisão do Victor, 27/09): BotAI escreve por offset fixo do CCSBot (`0x5100+0x0C`), deslocado pelo update de 23/09; upstream sem correção desde 27/08 | — | — | — | — |
| 6 · B1.8 | 27/09 21:17–21:28 ("terminei") | máscara do NadeSystem removida (volume) | igual | não precisa | NadeSystem 1.2.1, "3703 grenades in DB"; sem EmitSoundFilter | OK: 5 rounds, 0 crash, replays de smoke/flash; 182 cegueiras |
| 7 · B1.9 | 27/09 22:29–22:37 ("pode aplicar", Victor no PC) | BotRandomizer do upstream `276f1ce` (com a correção `18d1510`) por bind mount, no lugar da máscara | igual | não precisa (bind mount) | BotRandomizer 1.3.2, "Catalog loaded: 35 weapons, 1456 weapon paints, 10565 stickers, 81 charms"; 0 `signature failed`; sha no container = manifesto (5/5) | OK: 10 bots em mirage e de novo após a troca para inferno (readição); 0 crash, 0 exceção do BotRandomizer |

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

### Notas por passo

Assinaturas que falharam, pelo nome; plugins recusados no `meta list`; impressão do Victor,
se vier (não bloqueia).

- **1 · B1.3r:** nenhuma assinatura falhou. RoundDamageRecap (ed0ard) carregado e sem máscara. O container reiniciou às 13:48 sem recreate (config-hash igual). Jogo "liso" na impressão do Victor.
- **2 · B1.4:** o BotAimImprover do volume (05/09) não carrega na build atual; a correção veio do upstream (B1.4b). Bots da partida 27 (com B1.4b + Medium): 14 utility + 19 flash, 63 cegueiras. Impressão do Victor: "bem desafiador e bem maneiro de jogar".
- **3 · B1.5:** Victor: K/D 0,41, ADR 46 na partida 28 (média até 26/09: K/D 2,93, ADR 130) — "beeem mais desafiador". BotController nativo não disponível (Metamod 1469 recusa plugins da interface 17): recursos do Smarter-Bot que dependem dele ficam desligados até a B2. No smoke, depois do `changelevel` a quota volta a zero no load: é preciso readicionar os bots para testar a entrada deles no mapa novo ([smoke só de bots](smoke-partida-de-bots.md#armadilhas), armadilha 2).
- **4 · B1.6:** CTs trocaram a AUG pela M4A1 (146 vs 30 hits); entropia de armas 3,18 bits (ref. 2,54). Com BotState + BotBuy os bots deixaram de usar granada (0 dano/cegueira nas partidas 28 e 29).
- **5 · B1.7:** pulado. Religar só com correção upstream do offset `m_gameState` do CCSBot, ou após verificação do offset na build atual.
- **6 · B1.8:** granadas voltaram (324 replays na partida 30). Aviso do engine "Grenade has no weapon info" nas granadas replayed: a contagem de utility do motor não credita o bot. Victor: 9/13, K/D 0,69, primeira derrota da trilha.
- **7 · B1.9:** nenhuma assinatura falhou (0 `signature failed` e 0 `cosmetics disabled` na janela e na partida). Skins, facas e luvas confirmadas pelo Victor. O `5dfe948` do plano não existe no clone do upstream: a correção de assinatura é o `18d1510`, ancestral do `276f1ce` compilado. Avisos iguais aos da partida 30: 3 `Error invoking callback` do BotBuyPatch e "Grenade has no weapon info" (ver [Sobras](#sobras)).
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
| VPK Low | 28/09 19:54:52 (VPK) e 19:59:26 (build 2000919); build 2000922 em 30/09 23:10 | VPK Medium → Low, a pedido do Victor; no mesmo boot, o steamcmd da imagem atualizou o CS2 sem OK prévio (G5); o restart da janela de 30/09 levou à 2000922 | os mesmos da 7 | Low | 2000919 → 2000922 | 36 (matchid 71, `events_71_map0`, de_ancient 13x7, 01/10, G7 OK na 2000922). Ressalva: a `events_70` (MD3, 30/09, antes da janela) já jogou o Low na 2000919, sem G7 | **validada**: jogavel-2026-10-01 |

- O B1.7 não abriu época: foi pulado, e o BotAI segue mascarado.
- Na partida, a época do VPK se confere pelo chat: o RoundDamageRecap compara o sha256 do
  VPK ativo com as variantes e anuncia, por exemplo, "BOT Difficulty: Low [1/3]".
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
| BotAI | 5 · B1.7 | mascarado (pulado) | — |
| NadeSystem | 6 · B1.8 | religado | 1.2.1, do volume |
| BotRandomizer | 7 · B1.9 | religado | 1.3.2, upstream `276f1ce`, bind mount |
| RayTrace/RayTraceImpl, BotHider/BotHiderImpl | fora da B1 | mascarado | — |
| BotVision, BotController | fora da B1 | ausentes do volume | — |

Nenhum plugin que ficou no ar tem assinatura falhando, nem na janela nem na partida. A única
falha da trilha foi a `PickNewAimSpot` do BotAimImprover do volume (B1.4), trocado pelo do
upstream. O BotAI não chegou a ser testado, então as 43 assinaturas dele ficam sem lista.

### Sobras

1. **BotAI:** mascarado. Escreve Int32 zero em `CCSBot+0x5100+0x0C` a cada spawn, num offset
   da build 14172 que o update de 23/09 deslocou. O upstream não tem commit desde 27/08, e o
   PR #7 dele segue aberto. O card B1.7a confere o offset na build atual, que desde 28/09 é a
   2000919.
2. **Nativos do Metamod, para a B2:** RayTrace/RayTraceImpl e BotHider/BotHiderImpl seguem
   mascarados (no boot, `[META] Failed to load plugin ... File not found`, efeito da máscara).
   BotVision e BotController nem estão no volume: o snapshot `volume-addons-0144`, de 27/09,
   não tem pasta deles. Efeitos: o Smarter-Bot loga `BotController API not available` e
   desliga o que depende dele, e `Unknown command 'bv_reveal'` é ruído.
3. **BotBuyPatch:** 3 `Error invoking callback` (`BotBuyPatch.cs:258`, `ArgumentNullException`
   em `get_PlayerPawn` no `OnRoundStart`) no warmup do changelevel. Foram iguais nas partidas
   30, 31 e 36 (esta no warmup do 1º mapa, build 2000922), sem efeito visto: ruído conhecido.
4. **NadeSystem:** "Grenade has no weapon info" nas granadas replayed (141 avisos na partida
   30, 68 na 31). A contagem de utility do motor não credita o bot. É o card B1.8b.
5. **Época VPK Low:** validada em 01/10 (partida 36, `jogavel-2026-10-01`, build 2000922). O
   Low e a build entraram juntos (confundidor 3); a `events_70` já jogou o Low na 2000919, sem G7.
6. **Fora da trilha:** o GOTV não grava `.dem` desde 21/09
   (`CDemoFile::Open: couldn't open file ... for writing`). Já é a Q12, no S1.2.

### Recomendação para a Q16 (etapa 2: nativos)

(A), como no plano, começando só quando a época VPK Low tiver uma partida validada e a P1
estiver estável. Duas coisas mudaram desde o plano:

- O Metamod 1469 e a CSSharp 1.0.375 estão no ar desde o B1.3r. O B2.2 ("Subir o Metamod")
  fica absorvido, e o B2.1 se reduz a conferir as versões corrigidas (BotHider v0.5.0,
  BotVision v0.3.0, BotController v0.7.0) contra o par atual. Sobra o B2.3, um nativo por
  partida.
- O BotAimImprover do upstream traça a visada com o `Trace` da própria CSSharp
  (`BotAimImprover.cs:407-417` em `c3d10f5`), não com o RayTrace. Nenhum plugin ativo
  conhecido depende do RayTrace, então o B2.5 segue condicional.

O ganho mais visível é o BotController, que o Smarter-Bot já espera. Mas cada nativo muda o
comportamento dos bots de novo, e a dificuldade acabou de mudar duas vezes a pedido do Victor:
uma época nova só se lê depois que a atual assentar. Dentro da B2, o B2.4
(`BOT_PROFILE_VARIANT`) é o de retorno mais imediato, porque tira do procedimento à mão a troca
de VPK, que já aconteceu duas vezes. A decisão é do Victor.

### Recomendação para a Q17 (o que sobrou quebrado)

(A) para as três sobras de plugin. Para o BotAI, é o que o Victor já escolheu na prática em
27/09: pular e esperar.

- **BotAI:** fica mascarado. Só volta com correção upstream do offset ou com o offset conferido
  pelo B1.7a na build atual, num passo próprio, com smoke só de bots. A (B), caçar à mão, não
  compensa: o risco é corromper memória em silêncio, sem assinatura que barre.
- **BotBuyPatch e NadeSystem:** aceitos como estão. Nenhum dos dois derrubou partida, e o do
  NadeSystem só distorce a contagem de utility (B1.8b).
- A (C), PR no upstream, fica opcional e sem prazo.
