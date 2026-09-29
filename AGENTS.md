# cs2-tracker: regras para agentes

App local que transforma o CS2 num single-player contra times pro: servidor dedicado em Docker (MatchZy + CounterStrikeSharp + plugin próprio de captura), wizard (TUI e web) para montar a partida e estatísticas em SQLite.
Um jogador só, o Victor, numa máquina Windows 11. Ele joga ~10–15 mapas por semana, sem avisar, enquanto os agentes trabalham.
Aqui fica só o que vale para todo mundo, inclusive para a sessão que conversa com ele. Cada regra traz a origem entre parênteses.

## Decisões definitivas (não voltam a ser pergunta)

- O jogo está sempre jogável: a `main` sempre joga, todo sprint termina numa tag `jogavel-*` em que ele jogou, e nada o impede de jogar. (princípio 1; tag `jogavel-2026-09-26`)
- `wizard_tui.py` fica vivo e sem diff até a D13: MD3 completa jogada pelo browser + OK do Victor. Não proponha aposentá-lo. (SPEC D13; memória do Victor)
- Visão: partidas avulsas agora; modo carreira no horizonte longo. (plano 2026-09-26; critic, lacuna 1)
- KB e board no Obsidian, sem Notion: KB versionada em `docs/`, board em `docs/board-cs2/`, fora do git. (Q21=A; critic, lacuna 2)
- Repo público: nenhum SteamID64 real, IP ou segredo em `docs/`, `tests/` ou commit. (princípio; critic, risco 8)
- Trilho único: no máximo uma mudança não validada em partida no caminho de jogo; ele joga sobre um candidato por vez. (Q6=A)
- `botprofile.vpk` na variante Low; trocar só em janela, com o servidor parado. (Victor, 28/09; substitui o Medium de 27/09 e a Q9=A "High fixo")
- Tudo em pt-BR: docs, comentários, commits e nomes de teste. (princípio)

## Python: um interpretador só

- Sempre `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe`, pelo caminho ABSOLUTO: worktree não tem `.venv`, e o `python`/`py` do sistema é o 3.14, incompatível. (B0.4; auditoria harness)
- Nunca `pip install` nem `pip uninstall` (nem via `python -m pip` ou `uv pip`): a `.venv` é a do jogo. Precisa de dependência? Pare e peça ao Victor. (princípio; deny no settings)

## Zonas proibidas e o que fazer no lugar

| Nunca | Em vez disso | Origem |
|---|---|---|
| ler ou escrever o `cs2_tracker.db` real | `tmp_path` e fixture; dado real só numa cópia `mode=ro` pedida ao PM | auditoria git/critic |
| ler, copiar ou imprimir o `.env` | `.env.example`; worktree nasce sem `.env` | critic; B0.5 |
| mexer em `data/profile.json` | perfil em `tmp_path` nos testes | D8 |
| mexer em `docker/events-live/` (current e arquivados) | fixture anonimizada em `tests/fixtures/` | critic (events_50) |
| editar, reverter ou commitar `docker/match_config.spike.json` | é estado de runtime do `start_match`: deixe como está; `git add` só por caminho | auditoria git |
| tocar no volume `cs2-tracker_cs2-data` ou em `C:/cs2server` | nada: o volume não é reproduzível e o `C:/cs2server` é a única semente de recuperação | critic, infra |
| `docker compose down` (com ou sem `-v`), `docker volume rm`/`prune`, `docker system prune` | nada disso; parar o jogo é do papel servidor, em janela | deny B0.4 |
| `docker compose run` | build do plugin só pelo papel servidor, em janela | deny B0.4 |
| `docker compose` fora do checkout principal | sem `name:`, o compose cria projeto e volume novos, vazios: só o servidor, de `C:/Users/Victor/Projetos/cs2-tracker` | critic, risco 2 |
| `git clean` (qualquer flag, inclusive com `-C`) | apague só o que você criou, pelo nome: os ignorados incluem banco, events-live, `.env` e a DLL | critic, risco 1 |
| usar a porta 8000 | é do Victor; use a 8010 com banco de fixture | Q3=A; protocolo 9 |
| trocar VPK ou DLL com o servidor vivo | só em janela, com o servidor parado (dá FATAL/segfault) | bafe2b4 |
| `docker logs` com partida em curso | espere preflight 0; a coleta roda depois da partida | protocolo 11 |
| container, RCON, `docker exec`/`cp`/`run` | só o papel servidor, em janela; dev, qa e tech-manager nunca rodam docker. Exceção: a coleta só leitura pós-partida do servidor (`jogavel.py coletar`: `docker logs --since`, `docker exec sha256sum`, config-hash) basta preflight 0, sem janela | plano, papéis; protocolos 6 e 9; ask B0.4 |
| rodar `wizard_tui.py`, `start_match.py` ou `watcher.py` de verdade | fakes e smoke com Pilot (G4); jogar é do Victor. Exceção: o papel servidor, em janela, pode rodar partida só de bots | plano, papel dev; Q7=A |
| push na `main`, `--force`, `reset --hard`, reescrever histórico publicado | branch do card e PR | convenção; ask B0.4 |

O hook `tools/hooks/guarda.py` barra boa parte desta tabela antes de todo Bash, PowerShell, Edit, Write e `preview_start` do navegador, e PII (`tools/hooks/pii.py`): segredo do `.env` em qualquer arquivo do repo; SteamID em `docs/`, `tests/`, `.cursor/`, `.env.example` e `*.md` da raiz; IP nos mesmos, menos `tests/` fora de `tests/fixtures/`. SteamID fictício fica abaixo da base 76561197960265728 (ex.: 76561190000000001). O bloqueio diz motivo e alternativa; não contorne, pare e peça ao Victor. (B0.5)

## Janela de manutenção

- Servidor, container, RCON e volume só mudam em janela aberta pelo Victor; quem opera é o papel servidor. (princípio 3; protocolo 9)
- Abre quando ele escreve "pode mexer no servidor": no máximo 45 min, sempre devolve o jogo jogável, e aborta na hora se ele abrir o jogo ou a TUI. (Q4=A)
- Trilha de bots: depois de "terminei" (= fechei a TUI e o jogo), o servidor pode aplicar o próximo passo e volta sozinho se o boot falhar. (Q5=A)
- Partida só de bots é permitida dentro da janela. (Q7=A)
- Janela nunca abre por ausência de processo. Marca: `logs/janelas/ABERTA` no checkout principal; registro em `logs/janelas/<data>.md`. (protocolo 8)
- Só o papel servidor cria e apaga a marca, e só depois da frase do Victor, do "terminei" na trilha de bots ou de OK explícito dele repassado pelo PM. A idade conta do mtime: não renove com `touch`. Marca com mais de 45 min é janela vencida e o preflight não devolve 4. (Q4=A; protocolo 8)
- Infra (compose, fontes de bind, plugins) só muda em janela, com `docker compose up -d --force-recreate` do checkout principal. (protocolo 2)
- O candidato de infra pode estar mergeado no `origin/main` antes da janela; quem o traz ao checkout principal é só o papel servidor, dentro dela. Fora de janela ninguém (PM, Cursor, outro agente) faz `pull`/`merge` da `main` no checkout principal se `git diff --stat HEAD origin/main` tiver arquivo de infra; delta sem infra pode. (decisão do PM, 27/09; H1.6)

## Preflight: antes de tocar em qualquer coisa viva

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py
```

- `0` livre · `3` Victor jogando (cs2.exe; python rodando `wizard_tui`, `watcher.py` ou `start_match`; `current.jsonl` mexido há menos de 10 min) · `4` janela aberta. O 3 vence o 4. (protocolo 10; B0.4)
- Se a detecção falha, a resposta é 3. Qualquer código diferente de 0 e 4 também conta como 3 (2: argumento errado ou script ausente numa worktree anterior ao B0.4; 1: crash). (G0)
- Com 3, só trabalho Offline; com 4, só o papel servidor. Com 0 o servidor continua exigindo janela para mexer. Exceção: a coleta só leitura pós-partida (`jogavel.py coletar`: `docker logs --since`, `docker exec sha256sum`, config-hash) roda com preflight 0, sem janela. (protocolos 6 e 9)
- Rode do checkout principal ou de uma worktree dele: da worktree, ele olha o checkout principal (resolvido pelo `.git`). Num clone avulso ele olharia o próprio clone; sem `tools/preflight.py` na worktree, use `C:/Users/Victor/Projetos/cs2-tracker/tools/preflight.py`. (B0.4)

## Testes

- `C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`, no SEU worktree: no checkout principal os testes web leem o banco real. (auditoria harness)
- Até o T1.4 a suíte não é hermética: testes web chamam `docker cp` (`roster.py`). Rode com o Docker fora do PATH. (T1.4)
  - Git Bash: `export PATH="$(echo "$PATH" | tr ':' '\n' | grep -vi docker | paste -sd:)"`
  - PowerShell: `$env:PATH = ($env:PATH -split ';' | Where-Object { $_ -notmatch 'Docker' }) -join ';'`
- Baseline até o T1.4: num worktree limpo, com o Docker fora do PATH, as mesmas 42 falhas conhecidas (`no such table: matches`; a auditoria mediu 43 antes do efcaa42). Compare a LISTA de falhas antes e depois do card, não o total de aprovados, e não conserte falha fora do card. (T1.4)
- A suíte cria um `cs2_tracker.db` vazio no worktree: é lixo local ignorado; apague pelo nome. (auditoria harness)
- Teste novo usa `tmp_path` e `monkeypatch`: nada de processo real, Docker, RCON, rede ou porta 8000. (DoD)

## Branch, commit e PR

- 1 card = 1 branch = 1 PR de até ~400 linhas; branch `<tipo>/<ID>-<slug>` a partir de `origin/main` (ex.: `chore/B0.4-agents-md`). (DoD do card)
- Commit: título em pt-BR terminando em `(card <ID>)`, corpo com o porquê, trailer `Co-Authored-By`. (convenção)
- `git add` por caminho, nunca `-A` nem `.`. Merge commit, sem squash, feito pelo tech-manager depois do QA. (DoD)
- Caminho de jogo (protocolo 1):
  - `docker-compose.yml`, `docker/pre.sh`, `docker/plugins-src/**`, `docker/plugins/**` e `server-configs/**`;
  - `start_match.py`, `wizard_core.py`, `wizard_tui.py`, `watcher.py`, `parser.py`, `config.py`, `identity.py` e `roster.py`;
  - `stats.py`, `home.py` e `report.py`, até o P1.3 provar o isolamento;
  - `cs2tracker/{settings,db,ingest,server}`;
  - `web/`, a partir do S6.3.
- Qualquer diff nesses arquivos é um degrau: vira candidato e só fecha depois de partida real (G7). A exceção é diff só de comentário em arquivo NÃO montado, provado por `docker compose config` idêntico e `checar_so_comentarios.py`. (protocolo 1)
- Critério de aceite do card não se reescreve: se estiver errado, comente e pare. (kalendas, AGENTS.md)

## Onde mora o conhecimento

- Ordem das sprints: [`docs/agents/sprints.md`](docs/agents/sprints.md). Leia antes de propor ou despachar card: sprint seguinte só começa com a anterior fechada, salvo exceção do Victor registrada lá. (H1.9)
- `docs/`: KB em construção (`SPEC.md`, `features/`; depois `adr/`, `runbooks/`, `armadilhas/`). O código diz o quê; a KB diz o porquê. (K1)
- Board: `C:/Users/Victor/Projetos/cs2-tracker/docs/board-cs2/`, vault do Obsidian que só existe no checkout principal. Nasce do modelo versionado em `tools/board/modelo/` pelo `-m tools.board iniciar`, que só cria o que falta e nunca sobrescreve. (Q21=A; H1.4)
- Backups, auditoria e plano: `C:/Users/Victor/cs2-tracker-backups/2026-09-26/` (plano em `temp-artifacts/eb5adec0/plan/all.json`). (B0.2)
- Travas: `.claude/settings.json` (deny/ask em Bash e PowerShell; deny de Read/Edit nos arquivos proibidos), hook de guarda (B0.5) e `.cursor/rules/agentes.mdc` para o Cursor, que não roda hooks e só carrega regra `.mdc`. (Q3=A)
