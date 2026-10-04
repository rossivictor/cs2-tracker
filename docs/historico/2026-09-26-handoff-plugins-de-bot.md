<!--
Documento histórico: não editar abaixo da linha horizontal. Correções e
decisões novas vão para docs/runbooks/trilha-de-bots.md.
-->

> **Handoff da sessão paralela dos plugins de bot (cópia literal)**
>
> - **Origem:** arquivo `prompt-nova-sessao.md` da sessão paralela `5a2af0df`, reescrito
>   em 2026-09-26 às 13:47 (horário local). Copiado do backup do B0.2:
>   `C:/Users/Victor/cs2-tracker-backups/2026-09-26/temp-artifacts/5a2af0df/prompt-nova-sessao.md`
>   (sha256 `9c73f532028a65187986426602371546fb7df567f1bb872f7959e86a225d4e5b`).
> - **Data:** 2026-09-26.
> - **O que virou:** a trilha B1 do programa ("Trilha de bots", cards B1.1 a B1.10). O
>   runbook vivo é [docs/runbooks/trilha-de-bots.md](../runbooks/trilha-de-bots.md).
> - **Premissa corrigida depois:** o passo 1 abaixo ("Reverter é uma linha de YAML") não se
>   sustenta. O B1.1 mostrou que a CounterStrikeSharp 1.0.375 exige Metamod com KHook, então
>   Metamod e CSSharp sobem juntos. Ver
>   [docs/runbooks/b1.3-cssharp-1.0.375.md](../runbooks/b1.3-cssharp-1.0.375.md).
> - Abaixo da linha está o texto original, sem nenhuma alteração. Os números de linha do
>   `docker-compose.yml` citados nele valem para o commit `efcaa42`.

---

# Prompt para a nova sessão

Investigar se dá para atualizar por conta própria os plugins de bot do CS2-Bot-Improver, que
pararam de funcionar depois de uma atualização do CS2, e devolvê-los ao ar.

---

## Contexto

`C:\Users\Victor\Projetos\cs2-tracker` — servidor CS2 dedicado local em Docker
(`xbird/cs2-matchzy`) + MatchZy + CounterStrikeSharp, para jogar contra bots e coletar
estatísticas. Container `cs2-spike`, volume `cs2-tracker_cs2-data`. Branch
`feat/stats-web-e-captura-por-api`. Tudo em português. Testes:
`.venv/Scripts/python.exe -m pytest tests/ -q` (240 passando).

Em 2026-09-23 uma atualização do CS2 (hoje na build `1.41.8.5`) invalidou assinaturas de
memória. O servidor passou a cair com `Segmentation fault` e a derrubar o cliente com
`NETWORK_DISCONNECT_OVERFLOW`. A mitigação foi mascarar a suíte inteira montando
`./docker/plugins/_empty` por cima — `docker-compose.yml` linhas 141-155.

Com os plugins fora, os bots perderam: granada (NadeSystem), skins e facas (BotRandomizer),
reatividade e consciência (BotAI, BotState, BotVision), mira (BotAimImprover). É isso que se
quer de volta.

## A hipótese a testar

**Boa parte da quebra pode não ser dos plugins, e sim do CounterStrikeSharp.** Duas das
mensagens de erro mais frequentes no nosso log vêm dele, não deles:

    CSSharp: Failed to find signature for 'CEntityIOOutput_FireOutputInternal'
    CSSharp: [EntityManager][EmitSoundFilter] - Failed to emit a sound.
             Signature for 'CBaseEntity_EmitSoundFilter' is not found.
             The latest update may have broken it.

A segunda precedeu diretamente um dos dois segfaults, num round em que o NadeSystem estava
reproduzindo uma granada.

Estamos no CSSharp **v1.0.373**. A **v1.0.375**, de 2026-09-24, traz `fix: for update v1.41.8.2`
e `chore: Update Schema Definitions to v1.41.8.2`.

Se a hipótese estiver certa, parte dos plugins volta a funcionar **sem recompilar nada**.

## Fatos verificados (não precisa redescobrir)

**As assinaturas do CSSharp ficam em arquivo de texto, editável sem compilar:**
`/d/game/csgo/addons/counterstrikesharp/gamedata/gamedata.json` no volume (datado de
2026-08-25, anterior à quebra). As duas acima estão lá, com ramo `windows` e `linux`.

**Versões fixadas** em `docker-compose.yml` linhas 63-65:
`MMSOURCE_FIXED_VERSION=2.0.0.1411`, `CSSHARP_FIXED_VERSION=v1.0.373`,
`MATCHZY_FIXED_VERSION=0.8.15`. Os scripts de setup da imagem comparam com um `*version.txt`
no volume e extraem por cima, então downgrade funciona editando o YAML.

**Só o BotRandomizer foi corrigido upstream.** Conferido repo a repo:

| Repositório                          | Último commit | Situação                     |
|--------------------------------------|---------------|------------------------------|
| `ed0ard/CS2-Bot-Randomizer`          | 2026-09-25    | **tem a correção**           |
| `ed0ard/CS2-BotAI`                   | 2026-08-27    | nada desde a quebra; só o PR #7 aberto, que corrige 1 das 43 assinaturas Linux |
| `ed0ard/CS2-Bot-NadeSystem`          | 2026-09-04    | nada                         |
| `ed0ard/CS2-Smarter-Bot` (BotState)  | 2026-09-02    | nada                         |
| `ed0ard/CS2-Bot-Buy`                 | 2026-06-28    | nada                         |

O agregador `ed0ard/CS2-Bot-Improver` tem branch default **`main`** (comparar com `master` dá
404). O diff `v1.4.4..main` toca **apenas** BotRandomizer.

**O fonte é público e compilável.** Cada plugin gerenciado tem `.cs` + `.csproj` em
`addons/counterstrikesharp/plugins/<Nome>/`, com as assinaturas hardcoded no C# e ramo
explícito Windows/Linux (o BotAI tem `LinuxPatchDefinitions.cs` com 43 entradas e
`WindowsPatchDefinitions.cs` com 42). Versão de compilação por plugin:

    BotAI 1.0.371 · BotAimImprover 1.0.371 · NadeSystem 1.0.373
    BotState 1.0.373 · BotRandomizer 1.0.375 · BotBuy 1.0.367 (net8.0)

Os demais são `net10.0`. **Não há solução, script de build nem CI no repositório** — o PR #140
que adicionava GitHub Actions está aberto, não mergeado.

**A máquina de build já existe neste projeto:** `docker/build-events-plugin.sh` roda
`mcr.microsoft.com/dotnet/sdk:10.0 dotnet publish` num container descartável com o fonte
montado em `/src`. Serve igual para esses plugins. Em Git Bash precisa de `MSYS_NO_PATHCONV=1`
e `$(pwd -W)` nos caminhos do `-v`; há uma versão `.ps1` que já funciona no Windows sem isso.

**Plugins nativos (Metamod)** — BotHider, BotVision, BotController — não têm fonte no
repositório, mas suas assinaturas ficam em `gamedata.json` por plugin, **editáveis sem
compilar**. As versões corrigidas (BotHider v0.5.0, BotVision v0.3.0, BotController v0.7.0,
todas de 2026-09-25) exigem **Metamod build 1469+ e CSSharp 1.0.375+**, e estamos em 1411/373.
Detalhe não explicado: o `bv_reveal` sai como `Unknown command` no log, e o BotVision **não
está entre os plugins que mascaramos** — ou ele falhou ao carregar sozinho, ou nem está
instalado.

## Plano

Uma variável por vez. Depois de cada passo, um BO1 completo e leitura do log.

**1. Subir o CSSharp de v1.0.373 para v1.0.375, com a suíte de bots AINDA mascarada.**
Editar `CSSHARP_FIXED_VERSION` no `docker-compose.yml` e recriar o container (`docker compose
up -d` — `restart` não basta para mudança de mount ou de env).
*Sucesso:* `CEntityIOOutput_FireOutputInternal` e `CBaseEntity_EmitSoundFilter` somem do log,
MatchZy 0.8.15 e o nosso `Cs2TrackerEvents` continuam carregando, e um BO1 roda sem segfault.
Reverter é uma linha de YAML.
*Atenção:* o nosso plugin é compilado contra a API 1.0.373
(`docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEvents.csproj`) e usa
`ActionTrackingServices.MatchStats`, `CSMatchStats_t`, `InGameMoneyServices`,
`Listeners.OnTick`, `EventPlayerBlind`, `EventRoundFreezeEnd`. Se quebrar, recompilar contra a
1.0.375 é o primeiro remédio.

**2. Religar UM plugin por vez e classificar.** Comentar uma linha `_empty` por vez e recriar o
container. A pergunta de cada etapa é: *este plugin continua quebrado com o CSSharp novo, ou
só estava sendo vítima dele?*

Ordem, por segurança comprovada no código: **BotAimImprover** (checa `Handle == IntPtr.Zero` e
se desativa limpo) → **BotState** → **BotBuy** → **BotAI** → **NadeSystem** →
**BotRandomizer**. Os dois últimos por último porque são os únicos que invocam ponteiro de
função **sem** checar se a assinatura resolveu.

*Sucesso por etapa:* BO1 completo com troca de mapa, zero `Segmentation fault`, e a linha de
load sem `Fatal error`. Registrar, para cada plugin, quais assinaturas falharam **pelo nome** —
não só a contagem. No BotAI são 43 possíveis; saber quais 15 falham é o que permite decidir se
vale caçar assinatura.

**3. Recompilar o BotRandomizer a partir do `main`,** que já tem a correção (commit `5dfe948`,
que troca a assinatura Linux e a Windows). Usar o mecanismo do `build-events-plugin.sh`.
*Sucesso:* skins, facas e luvas de volta, sem crash.

**4. Só o que sobrar depois disso** é candidato a descobrir assinatura na mão. Aí sim avaliar
o esforço: é reverse engineering de padrão de bytes no `libserver.so`, e o ecossistema usa IDA
Pro. Provavelmente o BotAI é o que resiste.

## Variável de confusão — leia antes de culpar um plugin

Em 2026-09-26 às 16:04 o usuário foi derrubado com `NETWORK_DISCONNECT_OVERFLOW` **com a suíte
mascarada**. O log mostra a desconexão coincidindo com o MatchZy executando o `warmup.cfg` ao
detectar o primeiro jogador:

    16:04:00.761  SIGNONSTATE_SPAWN -> SIGNONSTATE_FULL
    16:04:01.742  [MatchZy] [FULL CONNECT] First player has connected, starting warmup!
    16:04:01.880  [StartWarmup] Executing Warmup CFG from MatchZy/warmup.cfg
    16:04:01.887  DISCONNECTING. ProcessMessages has taken more than 237ms
    16:04:01.905  Long frame: 256.89ms elapsed, 256.20ms sim time

Um overflow no signon **não** é evidência contra o plugin que você acabou de religar. Só conta
como regressão o que acontecer depois do jogador já estar dentro.

Segunda causa concorrente de segfault, não excluída: o `RayTrace`, que o próprio
`docker-compose.yml` (linhas 93-108) documenta como `core dumped` na segunda troca de mapa, e
que foi mascarado no **mesmo commit** que a suíte de bots.

## Erros da sessão anterior, commitados, que devem ser corrigidos

1. Os comentários no `docker-compose.yml` dizem que BotAI, BotAimImprover e RayTrace são
   "embutidos na imagem" e que se deve "religar quando a imagem publicar plugins
   recompilados". **É falso.** A imagem `xbird/cs2-matchzy` é de 2026-05-19 e não contém nada
   disso — verificado baixando o manifest e grepando as camadas. Os arquivos chegaram ao
   volume por caminho manual, não versionado (datados de 2026-09-05, origem desconhecida). O
   plano escrito ali nunca dispararia.
2. O comentário afirma que reativação parcial "foi pior que tudo ou nada". Não está
   comprovado, e cada plugin gerenciado degrada de forma independente.
3. A atribuição do segfault a BotAI/BotAimImprover não está provada — os dois são plugins
   gerenciados que falham de forma segura (o BotAI valida os bytes originais antes de escrever
   e faz rollback de par órfão).

## Regras

- Uma variável por experimento. A sessão anterior errou três vezes por concluir a partir de
  uma observação só.
- Nunca `docker compose down -v`: o volume tem ~73 GB de CS2 e a instalação manual dos
  plugins, que não é reproduzível.
- Nunca sobrescrever arquivo que o servidor tem mapeado em memória com ele rodando — foi assim
  que um `cp` do `botprofile.vpk` matou o processo em 26/09 (`FATAL ERROR: Error reading from
  loaded packed store`). Pare o container antes.
- Não quebrar nem aposentar `wizard_tui.py`.
- Rodar os testes antes de commitar.

## Se sobrar espaço: contribuição upstream

Não é o objetivo, mas se aparecer, a PR vai **no repo do plugin**, nunca no agregador (lá uma
PR foi fechada com "Thanks!", enquanto o `CS2-BotAI` mergeou 5 PRs de assinatura de 4 pessoas).

O candidato mais fácil, achado só lendo código: o CSSharp **engole** a falha de resolução de
assinatura — `BaseMemoryFunction.CreateValveFunctionBySignature` faz `catch(Exception){}` e
devolve `IntPtr.Zero`, então o construtor nunca lança. Consequência: o `try/catch` de
`BotRandomizer.LoadAttributeWriter()` é código morto, e o **NadeSystem não tem nenhum guard de
zero** antes de invocar `_smokeCreate` / `_heCreate` / `_molotovCreate`. O BotAimImprover, no
mesmo ecossistema, já faz esse check — é o precedente a citar.
