---
tipo: adr
status: aceito
aliases: [ADR-0005]
fontes:
  - "transcript eb5adec0 @ 2026-09-26T22:10:19Z"
  - "transcript de92b218 @ 2026-09-05T02:41:33Z"
  - "docs/runbooks/trilha-de-bots.md:13-29"
  - "docs/runbooks/trilha-de-bots.md:59-70"
  - "docs/runbooks/trilha-de-bots.md:251-253"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:14-54"
  - "docs/historico/2026-09-26-handoff-plugins-de-bot.md:15-18"
  - "docker-compose.yml:63-65"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:64-68"
  - "transcript eb5adec0 @ 2026-09-27T02:25:52Z"
  - "transcript eb5adec0 @ 2026-09-27T02:46:34Z"
  - "PR #4"
  - "backup:temp-artifacts/eb5adec0/audit/critic.json (gaps[2]; top_risks[5])"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (sprint B1; Q2, Q7, Q9, Q16 e Q17)"
atualizado: 2026-09-27
---

# ADR-0005: Trilha de bots primeiro, uma variável por vez

## Contexto

A atualização do CS2 de 23/09 derrubou a suíte de plugins de bot. Desde então, todos estão mascarados por `./docker/plugins/_empty`, e os bots jogam com IA e mira vanilla. A premissa da D2 da SPEC, a IA melhorada do CS2-Bot-Improver, não vale desde então. Para o Victor, é o problema mais sentido: bots fáceis, sem granada e sem reação (critic, lacuna 3). Em 05/09, ver os bots usando granada tinha sido o ponto alto. Uma sessão paralela (`5a2af0df`) já tinha um plano para subir a CSSharp e religar os plugins, e o handoff dela virou a sprint B1 (Q2=A).

Na pauta de 26/09, o Victor escolheu: "Bots primeiro, porque eu quero que o jogo continue funcionando com os plugins, enquanto desenvolvemos."

O B1.1 mostrou que o primeiro passo aprovado não funciona como uma linha. A CSSharp 1.0.375 exige Metamod com KHook (API 18, build 1467 ou mais novo), e todo Metamod a partir do 1459 recusa plugin da API 17. Só dois pares funcionam: Metamod 1411 com CSSharp até a 1.0.374, e Metamod 1467+ com a 1.0.375. O 2.0.0.1469 é o submódulo da própria 375. Subir só a CSSharp deixaria MatchZy e captura sem carregar.

## Decisão

- **Prioridade:** a trilha de bots (B1) é a primeira frente de produto do programa. Ela anda junto com as sprints Offline (H1, T1, K1...), que não tocam no caminho de jogo. Durante a B1, só card da B1 edita o compose.
- **Uma variável por partida:** cada passo muda uma coisa só, é aplicado em janela e é validado numa partida normal do Victor ([ADR-0004](0004-jogo-sempre-jogavel.md)). Os confundidores ficam registrados: o overflow no signon, o update do SteamCMD no boot e o RayTrace.
- **Quando as versões são acopladas, a variável é o par compatível.** Metamod + CSSharp sobem e voltam juntos (B1.3r, `docker-compose.yml:63-64`). O rollback restaura os dois. Um par descasado nunca é estado intermediário aceitável.
- **Ordem:** B1.3r (o par, com a suíte ainda mascarada) → B1.4 BotAimImprover → B1.5 BotState → B1.6 BotBuy → B1.7 BotAI → B1.8 NadeSystem → B1.9 BotRandomizer `5dfe948` → B1.10 (fechamento). Plugin sem guarda confirmada passa antes por partida só de bots, em janela pré-partida (Q7=A).
- **Fixo durante a B1:** o `botprofile.vpk` High (Q9=A). A MatchZy segue na 0.8.15. Download de versão ou de plugin só com OK explícito (G5).
- **Fora da B1:** plugins nativos do Metamod, RayTrace e BotHider ficam na B2, fora do backlog ativo, que só acontece se Q16=A. Plugin que não religar fica registrado pelo nome como degradado ou mascarado. O que fazer com ele é a Q17, respondida no fim da B1.

## Alternativas consideradas

- **Saneamento primeiro, bots depois**: o Victor recusou. É o problema que ele sente jogando.
- **B1.3 como aprovado (só `CSSHARP_FIXED_VERSION`)**: a CSSharp não carrega no Metamod 1411, e com ela caem MatchZy e captura.
- **Religar a suíte inteira de uma vez**: se a partida quebrar, ninguém sabe qual plugin causou, e um crash no meio da partida derruba o jogo dele. A sessão paralela já tinha errado três vezes por concluir a partir de uma observação só.
- **Ficar na 373 e editar `gamedata.json` no volume** (opção C do runbook): ninguém validou, não corrige o listener nem os vtables, e é sobrescrito em qualquer troca de versão.

## Consequências

- A trilha pede ~7 partidas normais do Victor, com janelas pós-"terminei" e 2 a 4 janelas pré-partida curtas.
- Cada passo muda o comportamento dos bots, então as estatísticas ganham épocas (registro no B1.10; coluna `bot_suite` no S2.4). Métricas de épocas diferentes não se comparam como oráculo (critic, risco 6).
- O B1.3r não cabe numa janela de "terminei" (15 a 30 min): ele pede a janela da Q4, com snapshot do volume antes e smoke só de bots depois, por causa do risco #1446 (stack overflow no ChangeTeam do primeiro bot, com Metamod 1469).
- Verificação: G6 na janela (assinaturas pelo nome, as linhas `complete` das duas versões, zero segfault) e G7 na partida seguinte.

## Status

Aceito em 2026-09-26. Em 27/09 (UTC), o Victor escolheu testar o par numa janela, com portão, que é a opção (B) do runbook do B1.3r, e com ela aprovou os downloads. O B1.3r é entregue pelo PR #4, que só é mergeado com a janela aberta. O B1.10 atualiza este ADR com o resultado de cada plugin.

## Fontes

- Transcript `eb5adec0` @ 22:10Z: a prioridade; @ 02:25Z e 02:46Z de 27/09: a pergunta do B1.3r e a escolha dele. Transcript `de92b218` @ 05/09: o valor das granadas.
- Runbooks `trilha-de-bots.md` (objetivo, ordem e a regra do par) e `b1.3-cssharp-1.0.375.md` (a pesquisa do B1.1 e os riscos #1443 e #1446). Handoff: a premissa "uma linha de YAML" corrigida.
- Plano, sprint B1: critérios de saída, Q2, Q7, Q9, Q16 e Q17.
