---
tipo: runbook
status: vigente
fontes:
  - "docker-compose.yml:15 (container_name: cs2-spike)"
  - "docker-compose.yml:66-69 (mount do cs2-data)"
  - "docker-compose.yml:196-205 (cs2-data external, name cs2-tracker_cs2-data; B0.8)"
  - "docker-compose.yml:83 (bind do pre.sh)"
  - "docker-compose.yml:149 (bind do BotAimImprover)"
  - "docker-compose.yml:157 (bind do BotRandomizer)"
  - "docker-compose.yml:178-188 (binds de saída e da captura)"
  - ".gitignore:4-23 (pastas de plugin, de saída e .env fora do git)"
  - "docker/SPIKE.md:160-167 (0x602 e a semeadura a partir do C:/cs2server)"
  - "docs/adr/0004-jogo-sempre-jogavel.md:40"
  - "tools/hooks/guarda.py:15-19 (o que o hook bloqueia no compose)"
  - "tools/hooks/guarda.py:1095-1145 (compose run, down e compose fora do checkout principal)"
  - "tools/hooks/guarda.py:1219-1221 (docker volume rm/prune)"
  - ".cursor/rules/agentes.mdc:8-11 (Cursor sem hook)"
  - ".cursor/rules/agentes.mdc:31-33 (proibições do volume e do compose)"
  - "AGENTS.md:32-35 (zonas proibidas: volume, C:/cs2server, compose run, compose fora do checkout)"
  - "tools/jogavel.py:1219-1230 (snapshot e restauração dos addons)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:387-417 (snapshot dos addons: o único backup da instalação manual)"
  - "docs/runbooks/versoes-conhecidas.md:40-50 (o que não mudou, RoundDamageRecap do volume)"
  - "docs/runbooks/versoes-conhecidas.md:158-186 (sha256 dentro do container)"
  - "docs/runbooks/versoes-conhecidas.md:275-280 (VPK no volume, com sha256)"
  - "backup:temp-artifacts/eb5adec0/audit/critic.json (top_risks[1]; contradição HOME=/home/steam × 0x602)"
atualizado: 2026-10-01
---

# Reconstruir o volume

> **Para quem:** o papel servidor, que é o único que opera container e volume, o PM e o Victor.
> **Card:** B0.8, que deixou o `cs2-data` external com nome fixo.
> **Quando:** ler antes de qualquer janela que mexa no compose; executar a
> [reconstrução](#reconstruir-a-partir-da-semente) só se o volume `cs2-tracker_cs2-data` não
> existir mais, com janela aberta e OK explícito do Victor.
> **Pré-condição:** preflight 4
> (`C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/preflight.py`), do
> checkout principal. Com 3, nada; com 0, falta a janela.
> **Links:** [voltar ao jogável](voltar-ao-jogavel.md), [versões conhecidas](versoes-conhecidas.md),
> [B1.3r](b1.3-cssharp-1.0.375.md) (snapshot e restauração), [ADR-0004](../adr/0004-jogo-sempre-jogavel.md).

O volume `cs2-tracker_cs2-data` tem ~73 GB: o jogo, os addons que a imagem instala e os plugins
de bot instalados à mão em 05/09, de origem não versionada. Ele não se reproduz pelo SteamCMD
(ver [0x602](#0x602)), e a única semente de recuperação é o `C:/cs2server`. Nunca rode
`docker compose down` (com ou sem `-v`), `docker volume rm`/`prune` ou `docker system prune`,
nem como passo deste runbook.

## Proteção real

### O que o external faz

Até o B0.8, o compose declarava só `cs2-data:`. O nome real do volume vinha do projeto, que
sem `name:` é o nome da pasta: `cs2-tracker` no checkout principal, daí
`cs2-tracker_cs2-data`. Numa worktree a pasta é outra, e o compose criava um projeto e um
volume novos e vazios (critic, risco 2). Agora o bloco `volumes:` do fim do compose diz
`external: true` e `name: cs2-tracker_cs2-data`:

- o nome do volume não depende mais do projeto nem da pasta;
- o compose nunca cria esse volume: se ele não existir, o `up` falha em vez de subir um
  servidor vazio;
- o `docker compose down -v` não remove volume external.

O projeto continua sem `name:`. Por isso o container continua pertencendo ao projeto
`cs2-tracker` só quando o compose roda do checkout principal.

### O que ele não protege

- **A worktree agora acha o volume vivo.** Antes, um compose de worktree criava um volume
  vazio; agora ele monta o `cs2-tracker_cs2-data` de verdade. O external troca "volume
  vazio" por "volume certo", e o que barra o compose de worktree continua sendo o que está
  abaixo.
- **`docker volume rm` e `prune`** apagam o volume como antes. Quem barra é o hook e o
  `.claude/settings.json`, só no Claude Code.
- **Escrita errada dentro do volume** (trocar VPK ou DLL com o servidor vivo, restaurar
  snapshot errado) não tem relação com o nome.

### `container_name`

O serviço tem `container_name: cs2-spike`. Um `up` de outro projeto (uma worktree) tenta criar
outro container com o mesmo nome, e o Docker recusa por conflito de nome. Essa é a única trava
mecânica contra o `up` de worktree, e só vale enquanto o `cs2-spike` existe (de pé, rodando ou
parado). Com o container removido, nada barra.

### `docker compose run`

O `run` cria um container avulso com nome próprio do projeto e do serviço, sem usar o
`container_name`. Ele montaria o volume vivo (e, de uma worktree, os binds dela) mesmo com o
`cs2-spike` de pé, com dois processos nos mesmos arquivos. Por isso o hook
`tools/hooks/guarda.py` bloqueia todo `compose run`, de qualquer pasta, e o AGENTS.md o lista
nas zonas proibidas.

### `up` de worktree com o container removido

As fontes de bind do compose são relativas (`./docker/...`, `./server-configs/...`): um `up`
feito de uma worktree, com o `cs2-spike` removido, sobe o volume vivo com os binds **da
worktree**, não os do checkout principal:

- as pastas ignoradas pelo git não existem numa worktree nova
  (`docker/plugins/Cs2TrackerEvents/`, `BotAimImprover/`, `BotRandomizer/`). O bind monta uma
  pasta vazia, e a captura e esses dois plugins somem dentro do container;
- `cfg`, `pre.sh` e `match_config.spike.json` passam a ser os da branch da worktree;
- `demos-live`, `stats-live` e `events-live` passam a gravar na worktree, onde o watcher do
  checkout principal não lê;
- a worktree nasce sem `.env`: `SRCDS_TOKEN`, `CS2_RCONPW` e `MATCHZY_ADMINS` saem vazios.

O hook bloqueia compose com diretório, `-f` ou `--project-directory` fora do checkout
principal, e com projeto (`-p`, `COMPOSE_PROJECT_NAME`) diferente de `cs2-tracker`.

### Cursor sem hook

O Cursor não roda o hook nem o `.claude/settings.json`: só carrega a regra
`.cursor/rules/agentes.mdc`, que repete as proibições (volume, `C:/cs2server`, `compose run`,
compose fora do checkout principal). Ali a barreira é só essa regra e o `container_name`.

## Semente `C:/cs2server`

O `C:/cs2server` é a instalação nativa do fluxo antigo do `watcher.py` (~67 GB, medido pela
auditoria de 26/09) e a única semente para reconstruir o volume. Ninguém escreve nele, apaga ou
move: nem a "aposentadoria do modo nativo" (critic, risco 2). Na reconstrução ele é montado só
leitura.

A semente devolve o jogo, não o resto. Ela não tem:

- os plugins de bot e o RoundDamageRecap instalados à mão no volume em 05/09. A única cópia
  fora do volume é o snapshot dos addons, `volume-addons-*.tgz`
  ([B1.3r, passo 6](b1.3-cssharp-1.0.375.md#6-snapshot-só-leitura-imediatamente-antes-da-troca)).
  Hoje só existe o de 27/09 01:44 (`C:/Users/Victor/cs2-tracker-backups/2026-09-27/b1.3r/`),
  tirado antes do B1.3r: ele traz o par Metamod 1411 + CSSharp 1.0.373 e os plugins como
  estavam naquela madrugada;
- as três variantes do `botprofile.vpk` em `game/csgo/overrides/`. O snapshot só leva
  `addons/`, e nos backups em `C:/Users/Victor/cs2-tracker-backups/` não há `.vpk` (conferido
  em 01/10). Os sha256 estão em [versões conhecidas](versoes-conhecidas.md#hashes-completos).

## Reconstruir a partir da semente

Só descrição: os comandos exatos saem do registro da janela que executar, pelo papel servidor.
Se o volume ainda existe, isto não é reconstrução: é [voltar](voltar-ao-jogavel.md) ou restaurar
os addons (`tools/jogavel.py restaurar`). Apagar o volume nunca é passo daqui; se algum dia for
preciso, quem decide e executa é o Victor.

1. **Confirmar a perda.** O sinal é o `up` falhar por volume external inexistente.
   `docker volume ls` e `docker volume inspect cs2-tracker_cs2-data` confirmam. Anote no
   registro da janela.
2. **Criar o volume vazio com o nome exato** (`docker volume create cs2-tracker_cs2-data`):
   com external, o compose não o cria.
3. **Semear do `C:/cs2server`.** Copiar `game/` e `steamapps/` para o volume num container
   descartável, com a semente montada `:ro`, como em `docker/SPIKE.md:163-167`. No Git Bash,
   `MSYS_NO_PATHCONV=1`.
4. **Subir do checkout principal** (`tools/jogavel.py recriar`, que é o
   `docker compose up -d --force-recreate`). O SteamCMD reconhece a instalação e baixa só o
   delta. A imagem instala Metamod, CSSharp e MatchZy pelas versões fixadas no compose, e o
   `pre.sh` registra o `overrides/botprofile.vpk` no `gameinfo.gi`. O boot baixa coisa da rede:
   peça o OK com a lista de downloads, como no
   [B1.3r](b1.3-cssharp-1.0.375.md#downloads-que-a-imagem-faz-no-boot-pedir-ok-com-esta-tabela).
5. **Plugins de bot.** Decidir com o PM e o Victor se restaura o snapshot de 27/09
   (`tools/jogavel.py restaurar --de <tgz>`, que não toca no `gameinfo.gi` nem no
   `matchzy.db*`). Ele traz os `*_version.txt` do par antigo, e o setup da imagem os compara com
   as versões fixadas. Sem snapshot, os plugins que vêm do volume (BotBuy, BotState,
   NadeSystem, RoundDamageRecap e os mascarados) se perdem. Os que vêm por bind
   (Cs2TrackerEvents, BotAimImprover, BotRandomizer) voltam com o checkout principal.
6. **VPK.** Sem cópia conhecida, as variantes e o VPK ativo se perdem com o volume, e os bots
   com nome de pro vêm do profile do VPK (comentário do compose, `docs/SPEC.md` §D2). Trazê-los
   de volta é decisão do Victor; a variante em vigor é a Low (AGENTS.md).
7. **Conferir.** G6 do boot, `meta list` e `css_plugins list`, os sha256 dos montados e o
   config-hash contra [versões conhecidas](versoes-conhecidas.md), e o smoke
   [só de bots](smoke-partida-de-bots.md). O fechamento é a partida do Victor (G7).

## 0x602

O que o repo documenta (`docker/SPIKE.md:160-167`, 04/09): baixar o jogo do zero pelo SteamCMD
dentro do Docker, neste ambiente (Windows + Docker Desktop + WSL2), falhou 4 vezes seguidas com
`Error! App '730' state is 0x602 after update job`, perto de 99% da verificação, e cada
tentativa recomeçava o download do zero. O que resolveu foi copiar `game/` e `steamapps/` do
`C:/cs2server` para o volume: o SteamCMD reconhece a instalação e baixa só o delta.

O comentário do compose sobre o `HOME=/home/steam` o chama de "causa raiz documentada" de falhas
de verificação. A auditoria de 26/09 (critic, contradição sobre o `HOME`) achou no transcript
que ele **não** resolveu o 0x602: o que resolveu foi a semente. Ele fica, sem efeito comprovado.

A causa do 0x602 não está documentada no repo. Por isso o volume não se recria baixando: a
reconstrução sempre parte do `C:/cs2server`.
