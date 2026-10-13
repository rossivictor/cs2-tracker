---
tipo: armadilha
status: rascunho
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 1-6 e 10-13)"
  - "docker-compose.yml:12-64"
  - "docker-compose.yml:84-173"
  - "docs/runbooks/trilha-de-bots.md:238-277"
atualizado: 2026-10-13
---

# Armadilhas da imagem, do boot e dos plugins

Itens 1 a 6 e 10 a 13 da lista de 54 da auditoria de 26/09 (o porquê da numeração está no
[índice](README.md)). A imagem é a `xbird/cs2-matchzy`; o boot é o do container `cs2-spike`.
Rascunho: a causa do item 6 nunca foi investigada, e a do item 13 está aberta no B1.12.

### 1. Addons sem versão fixa quebram no boot
- **Sintoma:** `[META] Loaded 0 plugins`; `matchzy_loadmatch` e `css_start` viram `Unknown command`.
- **Causa:** sem pin, a imagem baixa o "latest" de Metamod, CSSharp e MatchZy a cada boot. Metamod ≥ 1459 recusa plugin da interface 17, e a CSSharp ≥ 1.0.375 exige Metamod com KHook (≥ 1467).
- **Contorno:** versões fixadas no compose, sempre em par válido (1411 com CSSharp ≤ 1.0.374, ou 1469 com 1.0.375). Troca e volta só pelo runbook do B1.3r. Corrigido no código.
- **Fonte:** `docker-compose.yml:55-64` · `docs/runbooks/b1.3-cssharp-1.0.375.md:458-466` (auditoria: docker-compose.yml:55-65)

### 2. Update do CS2 no boot invalida plugin nativo de bot
- **Sintoma:** depois do update de 23/09, `Vision_...: FAILED` (15 detours), `Fatal error during Load() (signature broken?)`, segfault no warmup e `NETWORK_DISCONNECT_OVERFLOW` no cliente.
- **Causa:** o SteamCMD atualiza o app 730 em todo start do container. Plugin que faz patch de memória por assinatura erra o endereço na build nova e segue escrevendo.
- **Contorno:** máscara por pasta vazia e religação de um plugin por partida ([trilha](../runbooks/trilha-de-bots.md)). Registre a build antes e depois de toda janela: build nova é uma segunda variável.
- **Fonte:** `docker-compose.yml:110-143` · `docs/runbooks/trilha-de-bots.md:263-266` · `docs/runbooks/versoes-conhecidas.md:151-165` (auditoria: docker-compose.yml:109-155)

### 3. Plugin embutido tem dois lados para mascarar
- **Sintoma:** o plugin segue carregando, e crashando, com o wrapper CSSharp já mascarado.
- **Causa:** RayTrace e BotHider têm o wrapper .NET em `counterstrikesharp/plugins/` e um plugin Metamod nativo em `addons/<nome>/`, registrado num `.vdf`. O nativo é quem age.
- **Contorno:** bind de `./docker/plugins/_empty` nos dois caminhos. No boot, `[META] Failed to load plugin addons/RayTrace/...: File not found` (e o mesmo do BotHider) é o esperado.
- **Fonte:** `docker-compose.yml:94-109` · `docker-compose.yml:162-164` (auditoria: docker-compose.yml:93-108 e :147-149)

### 4. RayTrace aborta na segunda troca de mapa
- **Sintoma:** `spdlog::spdlog_ex — logger with name 'RayTrace' already exists`, core dumped; numa BO3, entre o mapa 1 e o 2.
- **Causa:** o plugin registra o logger sem checar se ele já existe de um load anterior.
- **Contorno:** mascarado (item 3); com Metamod ≥ 1459 o nativo nem carrega. Diante de crash na segunda troca, confira o `meta list` antes de culpar o plugin religado.
- **Fonte:** `docker-compose.yml:94-102` · `docs/runbooks/trilha-de-bots.md:258-262` (auditoria: docker-compose.yml:93-100)

### 5. Mascarar a suíte de bots pela metade é pior
- **Sintoma:** o log enche de `Unknown command 'bv_reveal'!` logo antes de um crash.
- **Causa:** os plugins da suíte chamam comandos uns dos outros (o BotAI registra comandos que os outros usam).
- **Contorno:** uma variável por vez, pela trilha. Hoje o `bv_reveal` sozinho é ruído conhecido do BotVision, não regressão.
- **Fonte:** `docker-compose.yml:130-134` · `docs/runbooks/trilha-de-bots.md:271-272` (auditoria: docker-compose.yml:129-133)

### 6. DefaultAgents quebra o modelo da arma
- **Sintoma:** `RESOURCE_TYPE_MODEL ... not resident`, viewmodel gigante e textura faltando no HUD; some ao desligar o plugin.
- **Causa:** não investigada (recurso não cacheado ou incompatível com a CSSharp pinada são hipóteses).
- **Contorno:** o mount fica comentado; religar reintroduz o bug.
- **Fonte:** `docker-compose.yml:84-93` (auditoria: docker-compose.yml:83-92)

### 10. SteamCMD precisa de `HOME=/home/steam`
- **Sintoma:** falhas de verificação recorrentes do SteamCMD.
- **Causa:** com `HOME=/root`, logs e cache vão para fora do volume, numa pasta que o usuário `steam` (uid 1000) não possui (joedwards32/CS2#130).
- **Contorno:** `HOME=/home/steam` no `environment` do compose.
- **Fonte:** `docker-compose.yml:17-21`

### 11. `CS2_LAN=1` desliga o VAC mesmo com GSLT
- **Sintoma:** `status` diz `insecure`; o boot loga `SV: VAC secure mode disabled.`
- **Causa:** a variável força o modo insecure, com ou sem `SRCDS_TOKEN`. Não era a causa da demo vazia do GOTV (descartado em 21/09).
- **Contorno:** `CS2_LAN=0`. Boot saudável mostra `VAC secure mode is activated.`
- **Fonte:** `docker-compose.yml:25-39` (auditoria: docker-compose.yml:25-30)

### 12. O GOTV ocupa um slot
- **Sintoma:** com `CS2_MAXPLAYERS=10`, os 9 bots do 5x5 enchem o servidor, e o humano recebe "servidor cheio".
- **Causa:** o SourceTV consome uma vaga própria, fora dos times.
- **Contorno:** `CS2_MAXPLAYERS = 2 × time + 1`; o `run_match` recusa `team_size` que não cabe.
- **Fonte:** `docker-compose.yml:43-47` · `start_match.py:833-843`

### 13. Crash na troca de mapa da série derruba o container
- **Sintoma:** `WatchDog! Server took too long to process` e `FATAL ERROR: Watchdog timeout exceeded` no `changelevel` de uma série (20/09); segfault na virada de série da MD3 de 04/10.
- **Causa:** em aberto ([B1.12](../runbooks/b1.12-segfault-troca-de-mapa-md3.md), hipóteses H1 a H4). Sem `restart policy`, o container não volta sozinho.
- **Contorno:** jogar MD1 até os testes do B1.12; a volta é do papel servidor ([voltar ao jogável](../runbooks/voltar-ao-jogavel.md)).
- **Fonte:** `docs/SPEC.md:396-401` · `docs/runbooks/b1.12-segfault-troca-de-mapa-md3.md:45-60` (auditoria: docs/SPEC.md:392-400)
