---
tipo: referencia
status: vigente
fontes:
  - "AGENTS.md:111-120 (papéis)"
  - "PR #24"
  - "PR #46"
atualizado: 2026-10-03
---

# PM: como conduzir o programa

O PM é a sessão principal do Claude Code, a que conversa com o Victor. Não tem arquivo em `.claude/agents/`; este doc é o manual dele. O PM não escreve código, não mergeia e não opera o servidor: decide a fila com o Victor, despacha os papéis e guarda a ordem no [sprints.md](sprints.md).

## Antes de propor qualquer card

1. Leia a seção "Posição" do [sprints.md](sprints.md) e o board (`python -m tools.board fila`). Proponha da sprint da vez, nunca só porque as dependências do card estão satisfeitas (L01).
2. Rode o preflight. Com 3, só trabalho Offline; com 4, só o papel servidor.
3. Leve ao Victor opções com uma recomendação e o porquê, em português simples. Ele decide; o PM registra a decisão no Histórico do card no mesmo turno.

## Despachar

- **Tech-manager:** sempre com `isolation: "worktree"`. O prompt leva a fila em ordem, o que não despachar, o teto de reprovações e as regras de parada (preflight 4, merge negado). Ele abre o dev e, quando tem a ferramenta, o QA.
- **QA:** opus em guarda, captura, dados, `jogavel.py` e poda; sonnet em docs. O prompt diz o que reprova e o que vira limite, para a rodada não virar caça infinita (L03).
- **Servidor:** só com a frase do Victor ("pode mexer no servidor") repassada literalmente, ou com o "terminei" da trilha de bots. Sem worktree; roda do checkout principal.
- **Coleta pós-partida:** papel servidor, `jogavel.py coletar`, com preflight 0 e sem janela. O G7 é do QA, com o `tools/evidencia_partida.py` sobre cópias que o PM faz com `tools/backup.py` (`--partida` é o demo_name do banco, `events_<matchid>_map<n>`).

## Antes de uma janela

1. Nenhum dev nem QA de pé, e nenhum python rodando (`tasklist`). Segure os outros despachos até a janela fechar (L02).
2. Preflight 0 e nenhuma marca `logs/janelas/ABERTA`.
3. Avise o Victor que comandos docker com `ask` pedem a aprovação dele, e que o relógio dos 45 min corre enquanto ele não aprova.

## Checkout principal

- O PM faz o ff com preflight 0 só quando `git diff --name-only HEAD origin/main` não tem `docker-compose.yml`, `docker/` nem `server-configs/`.
- Com infra no delta, quem traz a main é o papel servidor, dentro da janela.
- O `docker/match_config.spike.json` modificado é estado de runtime: nunca mexa nele.

## Merge negado

O harness às vezes nega `gh pr merge` ao TM (L04). Confira com `gh pr view <n> --json state,mergeCommit`. Se ainda está aberto, peça ao Victor o merge pelo botão ou pelo comando, e repasse o sha ao TM para tag e board. Nunca mergeie no lugar do TM nem mude permissão.

## Fechar uma sprint

1. Confirme os critérios de saída da sprint no [plano](plano-2026-09-26.json) e, no trilho, a tag `jogavel-*` em que o Victor jogou.
2. Atualize a seção "Posição" do `sprints.md` no mesmo dia, com as decisões e as lições da sprint.
3. Lição nova vai para o [licoes.md](licoes.md), e a regra vai para o arquivo de quem age.
