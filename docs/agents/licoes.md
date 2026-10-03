---
tipo: referencia
status: vigente
fontes:
  - "PR #24"
  - "PR #30"
  - "PR #34"
  - "PR #39"
  - "PR #46"
atualizado: 2026-10-03
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
