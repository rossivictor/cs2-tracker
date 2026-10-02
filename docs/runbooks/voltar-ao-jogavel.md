---
tipo: runbook
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.playability_protocol, seções 2, 5 e 7)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (judgements[1].must_fix[1], runtime file)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.playability_protocol, seção 8, janelas)"
  - "tools/jogavel.py:1-28"
  - "tools/jogavel.py:59-66 (eventos de round)"
  - "tools/jogavel.py:238-305 (partida em curso)"
  - "tools/jogavel.py:310-354 (runtime file e volta do merge falho)"
  - "tools/jogavel.py:385-415 (recreate só do checkout principal)"
  - "tools/jogavel.py:459-501 (voltar)"
  - "tools/jogavel.py:900-1131 (janela abrir, fechar, vigiar e aborto; timeouts do ciclo no B0.7c)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:452-703 (tipos de evento)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:641-670 (a volta à mão que o voltar substitui)"
  - "docs/runbooks/versoes-conhecidas.md:200-216 (manifesto do plugin de captura)"
atualizado: 2026-10-01
---

# Voltar ao jogável

> **Para quem:** o Victor, sem agente nenhum, e o papel servidor.
> **Card:** B0.7: `status`, `voltar` e `atualizar` (fatia 1) e a [janela](#janela) (`abrir`,
> `fechar`, `vigiar`; fatia 2). A pasta do plugin pelo manifesto, o `marcar`, a RCON e o
> `coletar` são do B0.7b.

Voltar ao jogável é um comando: ele devolve o checkout principal à última tag `jogavel-*` e
recria o container só se a infra mudou. Rode do checkout principal, no PowerShell ou no Git
Bash:

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py voltar --seco
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py voltar
```

- O `--seco` mostra, com o prefixo `[seco]`, o que mudaria (switch, `docker logs`, recreate) e
  não muda nada. O que só lê roda: `git diff`, `docker compose config` e a lista de processos.
- `--tag X` escolhe outra tag. A válvula vanilla, até o P1.2, é `voltar --tag jogavel-2026-09-26`.

## Quando ele recusa

Só com partida em curso (saída 3):

- `current.jsonl` com evento de round há menos de 2 min: todo tipo que o plugin grava fora o
  `snapshot` (`round_start`, `freeze_end`, `round_end`, `round_stats`,
  `round_officially_ended`, `player_death`, `player_hurt`, `player_blind`, bomba). A idade soma
  o mtime do arquivo e os snapshots gravados depois do último evento (2 por segundo): a cauda
  de snapshots do fim da partida não conta. O `freeze_end` conta: um round sem dano nem
  flash dura até 115 s depois dele, e do `round_start` já seriam mais de 2 min;
- o `watcher.py` rodando (ingerindo);
- sem certeza sobre o watcher, recusa: a lista de processos falhou, ou há `python` sem linha
  de comando legível (só o `tasklist` respondeu: PowerShell falhou e o `wmic` não existe nesta
  máquina). Recusa mesmo com o `cs2.exe` aberto, que numa partida viva sempre está. Qualquer
  python aberto (o uvicorn, por exemplo) basta: feche-o ou use `--agora`.

CS2, TUI e `start_match` abertos só geram aviso com o que fechar. Feche-os antes do recreate:
o `start_match` sobe o container quando o acha parado e competiria com a volta.

Numa emergência, `voltar --agora` segue mesmo com partida em curso, depois de você digitar
`VOLTAR`. Qualquer outra resposta não muda nada (saída 5). Com partida em curso ele não lê
`docker logs` (proibido nessa hora): a build "antes" sai como `não lida (partida em curso)`, o
log do container antigo se perde no recreate, e a build "depois" é lida normalmente.

## O que ele faz, na ordem

1. Salva `docker logs -t cs2-spike` em `logs/jogavel/<data>_<hora>-voltar/`, porque o
   recreate descarta o log do container antigo. Daí sai a build do CS2 "antes"
   (`GC Connection established for server version N`). Com `--agora` e partida em curso, pula
   este passo.
2. Protege o `docker/match_config.spike.json`, que o `start_match` reescreve a cada partida:
   copia para a mesma pasta, tira do caminho (`git checkout --` se rastreado; apaga se não
   rastreado e a tag o rastreia) e, depois da troca, restaura a cópia se a tag o rastreia. Se
   a tag não o rastreia (depois do P1.6), a cópia fica só na pasta. Sem `git stash`.
3. `git switch --detach <tag>`.
4. **Pasta do plugin de captura: ainda à mão até o B0.7b.** A `docker/plugins/Cs2TrackerEvents/`
   é ignorada pelo git e não volta com o switch. Confira o sha256 da DLL com o manifesto em
   [versoes-conhecidas](versoes-conhecidas.md#manifesto-do-plugin-de-captura) e, se divergir,
   copie a pasta da cópia de lá com o container parado.
5. Confere que `docker/pre.sh` não tem `\r`. Se tiver, para antes do recreate (saída 6) e
   imprime o comando de conserto; depois rode o que ele manda (`voltar --tag X --recriar`).
6. Se a infra difere entre o commit de antes e a tag (compose, `docker/plugins/` ou fonte de
   bind tirada de `docker compose config`), roda `docker compose up -d --force-recreate`,
   espera a linha do GC no log novo (até 10 min) e imprime a build "depois". Se `docker compose
   config` falhar, todo arquivo mudado conta como infra. Sem infra diferente, não recria.

**Build mudou** (`ATENÇÃO: a build do CS2 mudou`): o SteamCMD atualizou o jogo no boot. São
duas variáveis, e o cliente do Victor precisa da mesma build. A build não volta por git.

O recreate só roda do checkout principal, resolvido a partir do próprio `tools/jogavel.py`:
numa worktree ou num clone avulso passado em `--raiz`, o compose criaria projeto e volume
novos, vazios, e o `jogavel.py` recusa (saída 5).

## atualizar e status

- `jogavel.py status` só lê: HEAD, última tag `jogavel-*`, delta até a `origin/main` (sem
  fetch) e a infra dele, janela, preflight, `pre.sh`, runtime file, candidato e container.
- `jogavel.py atualizar [--seco]` traz a `origin/main` (fetch e `merge --ff-only`; do HEAD
  destacado, antes `switch main`). Precisa de preflight 0. Commit que toca infra só passa com
  janela aberta (preflight 4); sem ela, recusa (saída 5) e lista os arquivos. No fim imprime
  "Reabra a TUI e o uvicorn". Infra trazida na janela ainda pede o recreate do servidor.
  Se o `merge --ff-only` falhar depois do `switch main` (a main local divergiu), ele volta ao
  HEAD de antes e sai com 1; se nem a volta der, imprime onde o checkout ficou e o
  `git switch` para voltar.

## Janela

Só o papel servidor, do checkout principal (fora dele recusa, saída 5), e só depois da frase
do Victor, do "terminei" da trilha de bots ou do OK dele repassado pelo PM (AGENTS.md).
Todos aceitam `--seco`.

- `janela abrir --por "<frase literal>" [--teto 30]`: só com preflight 0 (3 recusa com saída 3)
  e sem marca nenhuma, nem vencida (saída 5). Cria `logs/janelas/ABERTA` com o mtime da
  abertura, o HEAD, o teto e o estado do container, e abre uma seção no
  `logs/janelas/<data>.md`. Teto padrão 45 min; na trilha de bots, 30. Renovar é fechar e
  abrir de novo, com novo OK: nada toca o mtime da marca depois da abertura.
- `janela vigiar [--intervalo 30]`: deixe rodando em segundo plano. A cada ≤30 s lista os
  processos e o `docker ps`. O `current.jsonl` não conta: na janela quem escreve nele é o
  servidor.
  - Processo do Victor (`cs2.exe`, TUI, `start_match`, `watcher`, ou `python` sem linha de
    comando legível): aborta (saída 3), registra e, se o checkout mudou na janela, roda o
    `voltar --tag <HEAD da abertura>`, que recusa com partida em curso. VPK, volume e pasta do
    plugin voltam pelo rollback do runbook do passo. A marca fica até o `fechar`.
  - **Depois de um aborto só cabe `janela fechar`**: nada de seguir o passo, de rodar o
    `vigiar` de novo nem de abrir outra janela por cima. A janela acabou; outra só com nova
    frase do Victor.
  - Nenhuma chamada do ciclo espera mais que 20 s: a lista de processos (30 s fora do ciclo)
    cai para 20 s, e o `docker ps` espera 10 s. Com o docker pendurado (27/09), a checagem
    dos processos do Victor segue a cada ≤30 s. O `voltar` do aborto já está fora do ciclo e
    usa os timeouts dele (o recreate espera até 15 min).
  - `docker ps` que estoura os 10 s vira `estado do container desconhecido` no registro, uma
    vez quando entra e uma quando volta a responder, e a vigilância segue. Desconhecido não
    conta como de pé: passou de 5 min assim, avisa como o container parado. No `fechar`,
    desconhecido não passa no item do container.
  - O tempo vem do relógio de parede contra o mtime da marca, não da soma dos ciclos. Ciclo
    acima de 30 s (um `docker` preso esperando aprovação, como em 27/09) vai para o registro
    com a chamada mais lenta, e o próximo ciclo começa sem esperar.
  - Avisa uma vez quando faltam 5 min para o teto e quando o container, de pé na abertura,
    passa de 5 min parado. No teto sai com 7 (janela vencida). Marca apagada: sai com 0.
- `janela fechar --feito matchzy --feito cvars --feito sha256`: checklist de fechamento (G6).
  Confere sozinho o container (de pé, ou parado como já estava na abertura) e o `pre.sh` sem
  `\r`. Os outros três são à mão até o B0.7b, e cada um só passa com o `--feito` dele:
  - `matchzy`: `get5_status` com `"gamestate":"none"` (`css_endmatch` ou restart), pela RCON;
  - `cvars`: pela RCON, na [referência do fechamento](smoke-partida-de-bots.md#referência-do-fechamento)
    (`mp_ignore_round_win_conditions`, `sv_hibernate_when_empty`, `bot_quota`,
    `bot_join_after_player`);
  - `sha256`: sha256 dos arquivos montados, dentro do container, igual ao checkout.

  Item faltando: a marca fica e ele diz o que falta (saída 5). Tudo ok: linha de fechamento no
  registro e marca apagada.

## Saídas

| Código | Quer dizer |
|---|---|
| 0 | ok |
| 1 | falha (tag inexistente, git ou docker falhou) |
| 2 | uso errado |
| 3 | partida em curso, preflight que não libera o `atualizar` ou o `janela abrir`, vigília abortada por processo do Victor |
| 5 | recusado por regra: infra sem janela, confirmação errada, branch que não é a `main`, recreate ou janela fora do checkout principal, janela já aberta ou sem `--por`, checklist pendente |
| 6 | `docker/pre.sh` com `\r` depois da troca |
| 7 | janela vencida (teto da marca ou 45 min pelo mtime) |
