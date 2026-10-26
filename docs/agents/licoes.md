---
tipo: referencia
status: vigente
fontes:
  - "PR #24"
  - "PR #30"
  - "PR #34"
  - "PR #39"
  - "PR #46"
  - "backup:../2026-10-26/g7-b1.13-copia/docs/board-cs2/ (Históricos dos cards 82 (19/10 18:25, o ff que puxou o P1.3), 84 (20/10 13:27, a TUI com o candidato.json do candidato-20), 89 (22/10 20:14, o candidato.json com a DLL errada), 29,8 (13/10 22:35), 81 (16/10 16:07), 86 (20/10, a CSTV) e 22,5 (24 e 25/10, os PARE do runbook))"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-19.md (linhas 53-54: o docker restart esperou a aprovação e a janela T2 venceu)"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-22.md (linhas 8 e 14: o build com o container já parado e o candidato.json com a DLL 697760a7)"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-23.md (linhas 31-34: as quedas na entrada do humano e o NadeSystem na 2000935)"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-24.md (linha 16: o PARE do dono 0:0)"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-25.md (linha 17: o PARE dos donos misturados em shared/)"
  - "backup:../2026-10-26/g7-b1.13-copia/logs/janelas/2026-10-26.md (linha 22: o comando só leitura do G6 na aprovação e a janela vencida)"
  - "tools/jogavel.py:798-810 (o atualizar faz o ff até a ponta do origin/main)"
  - "start_match.py:152-168 (o aviso do candidato lê o data/candidato.json sem conferir o HEAD)"
  - "PR #108"
atualizado: 2026-10-26
---

# Lições do programa

O que o programa aprendeu errando, e onde cada lição virou regra.

**Uma lição só fecha quando a regra está no arquivo de quem age.** O dev lê `.claude/agents/dev.md`, o QA lê `qa.md`, o TM lê `tech-manager.md`, o servidor lê `servidor.md`, o PM lê o [pm-playbook](pm-playbook.md), e todos leem o `AGENTS.md`. Este livro guarda a história (sintoma, causa, data); o arquivo do papel guarda a regra, curta. Quando os dois divergirem, vale o arquivo do papel.

## Como registrar

Uma entrada por lição, com número novo, nunca reaproveitado:

```
### L<nn> · <nome curto>
- **Quando:** <data ou card>
- **Sintoma:** o que se viu
- **Causa:** por que aconteceu
- **Regra:** o que passou a valer, em uma frase
- **Onde mora:** arquivo e seção
- **Estado:** aplicada | pendente (<o que falta e quem decide>)
```

Lição pendente é aviso: a regra ainda não chegou a quem age.

---

### L01 · A ordem das sprints só existia no plano
- **Quando:** 28/09, logo depois do B1.10.
- **Sintoma:** a B1 andou antes de a B0 fechar sem que isso estivesse visível, e o PM chegou a propor a T1 com a B0 e a H1 abertas, olhando só as dependências dos cards.
- **Causa:** a ordem e a exceção da via rápida (Q0=A) moravam no plano de 26/09, no backup, e em notas espalhadas de card; card com dependência satisfeita parecia "da vez".
- **Regra:** sprint seguinte só começa com a anterior fechada, salvo exceção do Victor registrada; todo agente lê o `sprints.md` antes de propor ou despachar card.
- **Onde mora:** [sprints.md](sprints.md) ("A regra"); `AGENTS.md`, "Onde mora o conhecimento".
- **Estado:** aplicada (PR #24).

### L02 · Janela aberta com outro agente rodando python
- **Quando:** Janela 0, 01/10 23:42–23:51.
- **Sintoma:** o `jogavel.py janela vigiar` abortou a janela depois de 5 min, sem mudança no ar; o Victor teve de dizer a frase de novo.
- **Causa:** o vigiar trata "python sem linha de comando legível" como o Victor jogando (G0). Havia um QA rodando a suíte em paralelo, e o diagnóstico da 2ª tentativa mostrou que os próprios `jogavel.py rcon` e `snapshot` do servidor também aparecem assim no instante em que saem.
- **Regra:** antes de despachar o servidor, nenhum dev ou QA de pé; o vigiar só aborta por python cego se o sinal se repetir na releitura, e a árvore do próprio servidor não conta.
- **Onde mora:** `AGENTS.md`, "Lições da B0 que viraram regra"; [pm-playbook](pm-playbook.md), "Antes de uma janela"; `tools/jogavel.py` (B0.7e, PR #46).
- **Estado:** aplicada.

### L03 · Enumerar formas na guarda não converge
- **Quando:** B0.5c (5 rodadas, 30/09–01/10) e B0.5d (3 rodadas, 01–02/10).
- **Sintoma:** cada conserto da guarda abria outra forma de contorno: 317 de 330 envoltórios de `@(...)` escapavam na 2ª reprovação do B0.5c; o B0.5d abriu duas regressões ao fechar a 1ª reprovação.
- **Causa:** a guarda tentava listar cada embrulho possível de um caminho, em vez de falhar fechado diante do que não consegue resolver.
- **Regra:** regra que falha fechado no lugar de enumeração; teto por card (classe nova vira limite no docstring e não reprova); conserto de classe nova só por card próprio na fila.
- **Onde mora:** `AGENTS.md`, "Lições da B0 que viraram regra"; docstring de `tools/hooks/guarda.py`, "O que a guarda NÃO cobre".
- **Estado:** aplicada (decisões do Victor de 30/09 a 02/10; PR #30 e PR #39).

### L04 · O harness às vezes nega `gh pr merge` ao TM
- **Quando:** PR #34 (30/09), PR #38 (01/10), e uma consulta depois do merge do PR #40 (02/10).
- **Sintoma:** o classificador do harness negou o merge ("Merge Without Review", "Modify Shared Resources") ou a conferência seguinte, sem padrão claro; outros merges do mesmo TM passaram.
- **Causa:** a regra é do harness, não do `.claude/settings.json`; o mesmo comando pode passar ou não.
- **Regra:** o TM não repete nem contorna; devolve a lista de merges pendentes, e o Victor mergeia. O PM confere o estado com `gh pr view` antes de repassar o sha.
- **Onde mora:** `AGENTS.md`, "Lições da B0 que viraram regra"; [pm-playbook](pm-playbook.md), "Merge negado".
- **Estado:** aplicada.

### L05 · Critério do plano que travaria o servidor
- **Quando:** B0.7b, 30/09.
- **Sintoma:** o critério 5 mandava o hook bloquear todo docker fora do `jogavel.py`; mergeado, ele travaria o papel servidor no rollback e na coleta, que ainda usam docker cru pelos runbooks.
- **Causa:** o plano de 26/09 supunha os runbooks já migrados para o `jogavel.py`.
- **Regra:** critério em conflito com o estado vivo não se reescreve: o TM comenta no card e para; o Victor decide (aqui, opção C: o critério saiu para um card próprio, o B0.7d, estacionado até a migração).
- **Onde mora:** `AGENTS.md`, "Critério de aceite do card não se reescreve"; card B0.7d no board.
- **Estado:** aplicada.

### L06 · O ff pela ponta do `origin/main` puxou um degrau a mais
- **Quando:** 19/10, no ff do PM pelo `jogavel.py atualizar` (~18:2x).
- **Sintoma:** o ff do checkout principal trouxe o P1.3 (`watcher.py`, caminho de jogo), mergeado e ainda sem candidato; o servidor voltou o checkout para a `jogavel-2026-10-19-2` (`0164cc3`) às 18:25, a pedido do Victor, sem janela.
- **Causa:** o `atualizar` faz o ff até a ponta do `origin/main` (`tools/jogavel.py:798-810`), não até o SHA que o PM conferiu; um merge entre a conferência e o ff entra junto.
- **Regra:** o ff do checkout principal vai pelo SHA conferido: logo antes do ff, `origin/main` tem de ser esse SHA; se andou, o ff espera e o delta se confere de novo.
- **Onde mora:** [pm-playbook](pm-playbook.md), "Checkout principal".
- **Estado:** pendente (o PM já tem a regra; falta no `servidor.md`, passo 3, que ainda diz `merge --ff-only origin/main`, e no `atualizar`, que não aceita SHA: card a criar, decide o PM com o Victor).

### L07 · O candidato anunciado antes de chegar ao checkout
- **Quando:** 19, 22 e 25/10 (datas do card K1.23). Registros achados: 20/10 13:27 (card 84) e 22/10 (janela, linha 14).
- **Sintoma:** em 20/10 o Victor abriu a TUI sobre o `9e5ab8e` com o `data/candidato.json` já do `candidato-20`, e o PM o fez fechar antes do `.ready`; em 22/10 o `candidato.json` e a tag `candidato-23` registraram a DLL `697760a7…` (0.4.0), porque o `marcar` rodou antes do build da 0.4.1.
- **Causa:** o `marcar candidato` grava o `data/candidato.json` no merge, antes de o código chegar ao checkout principal (ff do PM ou do servidor, em janela); o `aviso_candidato` (`start_match.py:152-168`) mostra na TUI o que o arquivo diz, sem conferir o HEAD.
- **Regra:** antes de liberar a partida, o PM confere que o HEAD do checkout principal contém o candidato do `candidato.json` (`git merge-base --is-ancestor candidato-N HEAD`); se não contém, avisa o Victor que a partida não vale como G7.
- **Onde mora:** [pm-playbook](pm-playbook.md), "Checkout principal".
- **Estado:** pendente (o PM já tem a regra; o `marcar` gravar o arquivo só com o código no checkout é card a criar, decide o PM com o Victor).

### L08 · `cd` numa subpasta do checkout principal
- **Quando:** 20/10, na sessão do PM.
- **Sintoma:** um `cd` numa subpasta do checkout principal mudou o diretório da sessão, e as worktrees dos agentes sumiram.
- **Causa:** o diretório do shell persiste entre comandos na sessão. O mecanismo do sumiço das worktrees não ficou registrado em card nem em janela (relato do PM no card K1.23).
- **Regra:** nenhum `cd` para dentro do checkout principal: caminho absoluto em todo comando, e `git -C <raiz>` para git.
- **Onde mora:** [pm-playbook](pm-playbook.md), "Checkout principal"; os prompts de despacho do PM já levam a regra.
- **Estado:** pendente (falta no `AGENTS.md`, para todos os papéis; decide o PM).

### L09 · Janelas vencidas esperando aprovação de comando docker
- **Quando:** 13/10 (card 29,8), 16/10 (card 81), 19/10 (T2) e 26/10 09:52, as quatro que os registros mostram.
- **Sintoma:** a janela venceu com o comando seguinte na fila de aprovação: o `docker exec` do T0 (13/10, ~80 min), o `docker exec` do G6 do vanilla on (16/10, ~1 h 15), o `docker restart` do braço processo novo (19/10, de 19:21 a ~22:08) e o `docker port`/`inspect`/`exec sha256sum`, só leitura, do G6 do `candidato-25` (26/10, de ~10:08 a 10:56).
- **Causa:** comando docker em `ask` espera o Victor, e o relógio dos 45 min corre durante a espera. O portão do preflight barra a escrita depois do vencimento, mas a janela se perde.
- **Regra:** o PM só despacha o servidor com o Victor dizendo que fica no PC até o fechamento e o lembra de que cada comando docker pede a aprovação dele; G6 que ficou em `FALTA` por vencimento se completa numa janela curta só de leitura (26/10 11:01) ou na coleta.
- **Onde mora:** [pm-playbook](pm-playbook.md), "Antes de uma janela"; `servidor.md`, "Janela vencida no meio" e "Coleta".
- **Estado:** aplicada.

### L10 · Runbook com premissas sobre o volume que só a janela confirma
- **Quando:** B1.3s, janelas de 24/10 22:58 e 25/10 11:22.
- **Sintoma:** as duas janelas pararam no passo 5, sem mudança no servidor e com o jogo fora do ar: em 24/10 o runbook exigia dono `steam` e o volume é todo `0:0`; em 25/10, `addons/counterstrikesharp/shared/` inteiro é `1000:1000` (109 entradas). Os PRs #113 e #114 acertaram o runbook, e a 3ª janela (25/10 15:01) instalou a v1.0.378.
- **Causa:** o runbook supôs donos e árvore do volume sem conferir os registros reais (inventário e janelas anteriores).
- **Regra:** antes da 1ª janela de um runbook, toda premissa sobre o volume é conferida contra registros reais; o que só a janela confirma vira passo de leitura com PARE explícito, antes do snapshot.
- **Onde mora:** `docs/runbooks/b1.3s-cssharp-1.0.378.md` ("O que as janelas de 24 e 25/10 mostraram").
- **Estado:** pendente (a regra geral falta no `dev.md`, para quem escreve runbook, e no `qa.md`, fase 1; decide o PM).

### L11 · Build nova do CS2 quebra o CSSharp e plugins nativos
- **Quando:** build 2000935, de 22/10 (recreate da janela do P1.10) a 26/10 (B1.13).
- **Sintoma:** na janela de 22/10 só o BotAI do fork foi conferido (40/40). Em 23 e 24/10 o servidor caiu com segfault 11 a 30 s depois da entrada do humano, 3 vezes, até com a válvula vanilla on; no smoke de 23/10 o NadeSystem logou `Invalid function pointer`.
- **Causa:** o update v1.41.9.2 mudou vtables e assinaturas que a CSSharp v1.0.375 e a smoke do NadeSystem 1.2.1 usam. A conferência por build cobria só o BotAI.
- **Regra:** a cada build nova, antes de jogar com plugins nativos, todos se conferem sobre a cópia do `libserver.so` da build (o gamedata da CSSharp e os 6 de bot, pelo `tools/conferir_plugins_bot.py`), não só o BotAI.
- **Onde mora:** [b1.13](../runbooks/b1.13-plugins-de-bot-2000935.md); `tools/conferir_plugins_bot.py`.
- **Estado:** pendente (o `servidor.md`, passo 9, ainda cita só o BotAI do fork; decide o PM).

### L12 · A contagem pelo `status` do RCON inclui a CSTV
- **Quando:** P1.7, G7 reprovado na partida 95 (20/10).
- **Sintoma:** o `start_match` contou 11 clientes num 5x5 e disparou o aviso falso de 11 jogadores em campo.
- **Causa:** o `status` lista o cliente da SourceTV; o fake do teste (`tests/test_balanceamento.py`) não tinha a CSTV, e por isso a fase 1 passou.
- **Regra:** fake de servidor em teste reproduz uma amostra real da saída (aqui, a linha da CSTV no `status`).
- **Onde mora:** `start_match.py` (P1.7 refeito, PR #108: a CSTV sai da contagem, com testes com a CSTV no fake).
- **Estado:** pendente (a regra geral do fake falta no `dev.md`; decide o PM).

### L13 · DLL compilada com o container de pé
- **Quando:** janela do P1.10, 22/10.
- **Sintoma:** o servidor rodou o build da DLL 0.4.1 (`docker/build-events-plugin.sh`, que escreve em `docker/plugins/`, montado) sem parar o container antes; ele estava `Exited (255)` desde 15:02Z por causa da queda do Docker Desktop, e por isso nada pegou o servidor vivo.
- **Causa:** a estrutura da janela no `servidor.md` não tem passo de build; a ordem saiu do runbook do card.
- **Regra:** build de plugin montado só depois do passo 4 (Parar), com o container parado conferido e registrado; o `AGENTS.md` já proíbe trocar DLL com o servidor vivo.
- **Onde mora:** `AGENTS.md`, zonas proibidas ("trocar VPK ou DLL com o servidor vivo").
- **Estado:** pendente (o passo de build depois do 4 falta no `servidor.md`; decide o PM).
