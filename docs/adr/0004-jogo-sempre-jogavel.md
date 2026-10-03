---
tipo: adr
status: aceito
aliases: [ADR-0004]
fontes:
  - "transcript eb5adec0 @ 2026-09-26T22:10:19Z"
  - "transcript eb5adec0 @ 2026-09-27T00:13:04Z"
  - "transcript 1ba4cab3 @ 2026-09-19T18:36:28Z"
  - "transcript 1ba4cab3 @ 2026-09-19T18:36:39Z"
  - "AGENTS.md:9"
  - "AGENTS.md:14"
  - "AGENTS.md:46-65"
  - "AGENTS.md:82-89"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (princípios 1 a 6; playability_protocol §1 a §11; gates G6 e G7)"
  - "backup:temp-artifacts/eb5adec0/audit/critic.json (gaps[2] e gaps[7]; top_risks[1] e top_risks[2])"
  - "docker-compose.yml:196-205 (cs2-data external, name cs2-tracker_cs2-data; B0.8)"
atualizado: 2026-10-03
---

# ADR-0004: O jogo está sempre jogável

## Contexto

O cs2-tracker é o jogo do Victor, e ele joga sem avisar enquanto os agentes trabalham. Na pauta de 26/09, ele justificou a prioridade assim: "Bots primeiro, porque eu quero que o jogo continue funcionando com os plugins, enquanto desenvolvemos. Gosto de jogar de vez em quando, e não quero ser travado por etapas do desenvolvimento." Depois, completou: "consigo jogar uns 10~15 mapas por semana".

O único caminho que joga (TUI → `start_match` → `watcher` → plugin → `parser`) tinha pouca cobertura: 0% na TUI, 6% no `start_match` e 13% no `watcher`. Só uma partida real prova esse caminho (critic, risco 3). Já houve regressão por deriva entre sessões (critic, lacuna 3). Em 19/09, com uma série em curso, ele pediu uma parcial do log e, segundos depois, recusou o comando docker que o agente rodou para achá-la (`docker ps`).

## Decisão

- **Jogável** = a TUI ou o `start_match`, rodados no checkout principal, sobem o servidor, os bots entram, a partida vai até o fim e é ingerida.
- **A `main` sempre joga.** Todo sprint termina numa tag `jogavel-AAAA-MM-DD`, num commit em que ele jogou. A primeira é `jogavel-2026-09-26`, no `efcaa42` (partida 24).
- **Trilho único (Q6=A):** no caminho de jogo ([AGENTS.md](../../AGENTS.md), "Caminho de jogo"), todo diff é um degrau. Ele vira `candidato-N` e só fecha depois de partida real (G7). Há no máximo um candidato por vez. A exceção são duas mudanças defensivas com evidências disjuntas, justificadas no card. O Victor é avisado pelo chat, por notificação e pelo `jogavel.py status`.
- **Evidência de carona:** a partida normal dele é o teste de aceitação. Depois dela, com preflight 0, o `jogavel.py coletar` salva logs e sha256 só lendo, e o QA julga o G7 sobre os logs, o JSONL arquivado e uma cópia só leitura do banco. G7 ok vira tag. Evidência ruim leva a revert e voltar. Sem evidência, o candidato espera a próxima partida. A impressão dele é bem-vinda, mas não bloqueia.
- **Voltar é um comando**, que funciona sem agente: `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py voltar`, no checkout principal (B0.7). Ele só recusa com partida em curso.
- **Janela (Q4=A, Q5=A, Q7=A):** servidor, container, RCON e volume só mudam em janela aberta pelo Victor ("pode mexer no servidor"; na trilha de bots, depois do "terminei"). A janela dura no máximo 45 min, é vigiada a cada 30 s ou menos e aborta se ele abrir o jogo ou a TUI. Nunca abre por ausência de processo.
- **Nada trava o jogo:** com preflight 3 (ele jogando), só trabalho Offline. A porta 8000 é dele. Agente não roda TUI, `start_match` nem `watcher` de verdade. Captura que não carrega gera aviso, e a partida segue (P1.4). Abortar só com opt-in dele, que é a Q19.

## Alternativas consideradas

- **Congelar o jogo durante o saneamento**: o Victor recusou ("não quero ser travado por etapas do desenvolvimento").
- **Servidor de homologação separado**: há uma máquina só e um volume de ~73 GB que não se reproduz (SteamCMD 0x602). Um compose de worktree criava um volume vazio (critic, risco 2); com o volume external (B0.8), ele monta o volume vivo e, com o container removido, sobe com os binds da worktree ([reconstruir-volume](../runbooks/reconstruir-volume.md)).
- **Várias mudanças por partida**: quando a partida quebra, ninguém sabe qual mudança causou. Uma variável por experimento ([ADR-0005](0005-trilha-de-bots-uma-variavel-por-vez.md)).
- **Validar só com partida de bots**: não cobre o caminho humano (entrada, `.ready`, TUI, post_mortem). Ela fica como pré-teste em janela (Q7=A).

## Consequências

- O ritmo do caminho de jogo é o das partidas dele, ~10–15 mapas por semana. Card com caminho de jogo espera em "Aguardando partida", e o resto anda em paralelo (Offline).
- Infra (compose, fontes de bind, plugins) só muda em janela, com `--force-recreate`, e o G6 confere o sha256 dentro do container. O `atualizar` recusa infra sem janela.
- O `wizard_tui.py` fica sem diff até a D13 (MD3 completa pelo browser e OK do Victor).
- Cada tag é registrada em `runbooks/versoes-conhecidas.md` (B0.3), com as versões, os plugins e o sha256 montado.
- Verificação: DoD do sprint = tag `jogavel-*` em que ele jogou. DoD do card com caminho de jogo = Concluída só depois do G7.

## Status

Aceito em 2026-09-26, pelas palavras do Victor acima e pelo "todas recomendadas" para Q0–Q9 (Q4, Q5, Q6 e Q7 = A). A tag `jogavel-2026-09-26` está no `origin`.

## Fontes

- Transcript `eb5adec0`: 22:10Z ("não quero ser travado") e 00:13Z (27/09 em UTC, "10~15 mapas por semana"). Transcript `1ba4cab3` (19/09): o pedido do log e a recusa do comando docker.
- Plano: princípios 1 a 6 e protocolo de jogabilidade §1 a §11, com G6 e G7. AGENTS.md: as regras em vigor.
- Critic: lacunas 3 e 8, risco 2 (o compose de worktree) e risco 3 (a cobertura do caminho de jogo).
