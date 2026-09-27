---
tipo: politica
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/comments.json (summary, stats, items)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (princípio 'Extrair antes de podar'; cards K1.9 e S1.1)"
  - "AGENTS.md:82-89"
atualizado: 2026-09-26
---

# Política de comentários

**O código diz o quê; a KB diz o porquê.** O comentário serve a quem vai editar aquela linha. Todo o resto vai para `docs/`, com a fonte `caminho:linha`, e o código aponta para lá.

## Por que existe

A auditoria de 26/09 contou 2.967 linhas de comentário e docstring em 15.654 (19%): 72% do `docker-compose.yml` e 69% do `gamemode_competitive_server.cfg`, que tem 77 linhas de diário do experimento de GOTV. O conhecimento é real, mas está espalhado. A mesma explicação aparece até 5 vezes (sink de log F2.2, `skip_lineups`, placar F4.4). Há comentário errado, como o `start_match.py:678-716`, que ensina a trocar o VPK com o servidor vivo, o que o `bafe2b4` mostrou que derruba o servidor. E há 162 citações D#/F#/M# em 34 arquivos e 63 datas em 26, que prendem o código ao histórico.

Os 147 blocos classificados se dividem em: 61 vão para a KB, 45 ficam curtos, 28 viram card e 13 são apagados.

## O que pode ficar no código

- **Invariante local**: o que quebra se a linha mudar. Exemplos: ordem obrigatória de chamadas, unidade, convenção de NULL (`COALESCE(is_human,1)`: NULL é o humano).
- **Racional curto de uma escolha não óbvia ali mesmo.** Exemplo: `TICKRATE` duplicado de propósito para não puxar awpy (`stats.py:42-47`).
- **Contrato na docstring**: o que a função recebe, o que devolve e o que levanta.
- **Aviso de perigo imediato**, numa linha com link. Exemplo: `# nunca trocar o VPK com o servidor vivo (FATAL); ver [[<nota de armadilhas/>]]`. O `start_match.py:678-716` pede esse aviso no lugar do procedimento errado.

Limite: até ~3 linhas por bloco. Se precisar de mais, é nota da KB.

## O que vai para a KB

| Conteúdo | Destino | Exemplo da auditoria |
|---|---|---|
| Decisão: por que X e não Y, e as alternativas | `adr/` | post_mortem aplicado no SELECT (`stats.py:234-249`) |
| Procedimento passo a passo | `runbooks/` | troca do `botprofile.vpk` (`start_match.py:678-716`) |
| Pegadinha do engine, da MatchZy, de plugin ou do Windows | `armadilhas/` | M4A1-S e USP-S com nomes diferentes em kill e dano (`stats.py:111-140`) |
| Definição de domínio: métrica, placar, lado | `dominio/` | KAST como K/S/T (`stats.py:416-427`) |
| Como os módulos conversam | `arquitetura/` | ordem do pipeline de ingestão (`parser.py:527-537`) |
| Investigação datada, "item N, 2026-09-20", diário de experimento | `historico/` | diário do GOTV/`tv_delay` no cfg |

## O que vira card, e o que se apaga

- **Vira card**: pendência escrita em prosa ("Religar quando...", "muleta", "por enquanto", "ainda não ingere"). O card nasce no board com a fonte `caminho:linha`. O comentário fica até o card fechar e passa a citar o ID dele (`ver card P1.5`). TODO sem card não entra.
- **Apaga**: comentário obsoleto ou errado, confirmado no código. Exemplos: caminho de asset velho (`stats.py:153-155`) e origem errada do `_current_map` (`watcher.py:200-203`). Também se apagam frase de changelog ("agora", "desde sempre", "nunca lido por nenhuma tela") e explicação duplicada, que fica num lugar só, com link nos outros.

## O que não entra mais em comentário novo

- Data, número de item de pedido ou nome de sessão: isso é histórico.
- D#, F# ou M# solto. Cite o ADR (`ver [[ADR-00xx]]`). Enquanto o ADR não existir (K1.6), o D# pode ficar, e o K1.9 troca.
- Diário de experimento, lista de tentativas ou "o que já testamos".
- Segredo, SteamID64 real ou IP ([ADR-0003](adr/0003-repo-publico.md)).

## Como citar

- **No código**, o `[[nome]]` do Obsidian, que também dá para achar com `grep`:
  - Python, YAML, cfg e shell: `# ver [[ADR-0004]]`;
  - C# e JS: `// ver [[ADR-0004]]`;
  - Jinja: `{# ver [[ADR-0004]] #}`;
  - HTML: `<!-- ver [[ADR-0004]] -->`.
- ADR se cita pelo alias `ADR-00xx`. As outras notas, pelo nome do arquivo sem `.md` (ex.: `ver [[contrato-events-jsonl]]`), que é único na KB.
- **Na KB**: link relativo em Markdown para outra nota, e `caminho:linha` do código no `fontes` do frontmatter.

## Ordem: extrair antes de podar

1. A nota da KB nasce primeiro, com a fonte (K1.4–K1.6).
2. Só então o comentário encolhe ou sai. A poda (K1.9) prova com `checar_so_comentarios.py` que só comentários mudaram, e o PR linka a nota de cada bloco removido.
3. Comentário em arquivo de caminho de jogo segue a regra de degrau do [AGENTS.md](../AGENTS.md). Em arquivo montado no container (compose, cfg, `pre.sh`), ele só chega ao servidor em janela, com `--force-recreate`.
4. Nada que esteja no `arquitetura/nao-apagar.md` (S1.1) é podado.

Comentário novo segue esta política desde já. O estoque antigo só é podado no K1.9.
