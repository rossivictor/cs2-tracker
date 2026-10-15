---
tipo: adr
status: aceito
aliases: [ADR-0010]
fontes:
  - "commit c2a90e4"
  - "commit e715253"
  - "docker-compose.yml:66-69 (mount do cs2-data)"
  - "docker-compose.yml:199-208 (cs2-data external, name cs2-tracker_cs2-data)"
  - "AGENTS.md:32"
  - "AGENTS.md:35"
  - "docs/runbooks/reconstruir-volume.md:1-25"
  - "docs/runbooks/versoes-conhecidas.md:229 (candidato-8, B0.8)"
  - ".github/workflows/ci.yml:31-49 (job compose)"
  - "tools/hooks/guarda.py:1723 (compose down)"
  - "tools/hooks/guarda.py:1810-1814 (volume rm/prune e system prune)"
atualizado: 2026-10-15
---

# ADR-0010: O volume do servidor é external, com nome fixo

## Contexto

O volume `cs2-data` guarda o jogo e os addons do servidor ([ADR-0007](0007-servidor-dedicado-em-docker-com-matchzy.md)): ~73 GB, com plugins instalados à mão, que o SteamCMD não reproduz por causa do erro 0x602 (`c2a90e4`). Até 01/10, o nome do volume vinha do projeto do compose, que sem `name:` é o nome da pasta. Um `docker compose` rodado de uma worktree criava projeto e volume novos e vazios, e o volume real ficava sem proteção pelo nome.

## Decisão

Decidido no `c2a90e4` (B0.8, 01/10):

- **O `cs2-data` é `external: true`, com `name: cs2-tracker_cs2-data`** (`docker-compose.yml:199-208`). O compose nunca cria nem apaga esse volume: se ele não existir, o `up` falha.
- **O projeto continua sem `name:`.** A chave do serviço e os mounts não mudaram (`docker-compose.yml:66-69`).
- **O compose roda só do checkout principal, pelo papel servidor.** A proibição já existia; o `e715253` (B0.8b) trocou o motivo: com o volume external, um compose de outra pasta não cria mais volume vazio, mas monta o volume vivo e sobe com os binds daquela pasta (AGENTS.md:35).

## Alternativas consideradas

- **Volume com nome derivado do projeto** (o estado até 01/10): uma worktree esquecida criava um servidor vazio sem ninguém perceber.
- **Dar `name:` ao projeto**: não feito; o B0.8 mudou só o volume. Motivo não registrado.

## Consequências

- O volume não é reproduzível, e o external não o protege de tudo: `container_name` só barra `up` com o container existindo, `compose run` monta o volume vivo, e o Cursor não roda hook. O que falta proteger e a reconstrução a partir da semente `C:/cs2server` estão em [reconstruir-volume](../runbooks/reconstruir-volume.md).
- Ninguém toca no volume nem no `C:/cs2server` (AGENTS.md:32); `docker volume rm`, `prune` e `compose down` ficam barrados pela guarda.
- Verificação: o job `compose` do CI roda `docker compose config -q`, que valida o modelo sem exigir o volume.

## Status

Aceito na prática desde 01/10/2026 (`c2a90e4`), na `main`. No servidor, entrou como `candidato-8` na Janela 0 e foi validado na partida que deu a `jogavel-2026-10-03` (`docs/runbooks/versoes-conhecidas.md:229`). ADR retroativo, escrito pelo K1.6 em 13/10 a partir dos commits; confirmado pelo Victor em 13/10.

## Fontes

- Commits `c2a90e4` (o external e o porquê) e `e715253` (o motivo novo da regra do compose).
- Compose, AGENTS.md e o runbook de reconstrução: o estado de hoje.
