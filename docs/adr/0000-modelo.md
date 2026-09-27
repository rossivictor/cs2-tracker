---
tipo: modelo
status: vigente
aliases: [ADR-0000]
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (card K1.1; final.kb_structure)"
  - "backup:temp-artifacts/eb5adec0/audit/comments.json (proposed_kb_structure: ADR-0000-template)"
atualizado: 2026-09-26
---

# ADR-0000: Modelo de ADR

> **Como usar.** Copie o bloco abaixo da linha para `docs/adr/NNNN-slug.md`. O número tem 4 dígitos, é sequencial e nunca é reaproveitado.
>
> - Um ADR por decisão, com até ~80 linhas. Detalhe operacional vai para um runbook, e o ADR linka.
> - Status: `proposto` → `aceito`, e depois `substituído` ou `descartado`. ADR aceito não se reescreve. Decisão nova vira ADR novo, e o antigo ganha `status: substituído` e o link para o novo.
> - Pode entrar num ADR aceito, com `atualizado` novo: correção de fato, fonte nova e resultado previsto no próprio ADR (ex.: "o B1.10 atualiza este ADR").
> - Toda afirmação de fato tem fonte no frontmatter (formatos no [MOC](../README.md#frontmatter-padrão)). Nada de PII ([ADR-0003](0003-repo-publico.md)).
> - Palavras do Victor vão entre aspas, com o transcript e o horário.

---

```markdown
---
tipo: adr
status: proposto
aliases: [ADR-NNNN]
fontes:
  - "caminho/do/arquivo.py:10-20"
  - "transcript xxxxxxxx @ AAAA-MM-DDTHH:MM:SSZ"
atualizado: AAAA-MM-DD
---

# ADR-NNNN: <a decisão, numa frase>

## Contexto

<O problema e as forças em jogo. Fatos com fonte; o que foi medido e o que é suposição.>

## Decisão

<O que foi decidido, em frases afirmativas: "X é...", "Y só muda quando...".>

## Alternativas consideradas

- **<alternativa>**: <por que não>.

## Consequências

- <O que passa a ser obrigatório ou proibido, e para quem.>
- <O que fica mais caro ou mais lento.>
- <Como verificar que a decisão está sendo cumprida: teste, check, gate ou card.>

## Status

<Proposto | Aceito em AAAA-MM-DD por <quem> | Substituído por ADR-xxxx (com link relativo para o arquivo dele) em AAAA-MM-DD | Descartado em AAAA-MM-DD, porque...>

## Fontes

- <fonte>: <o que ela prova>.
```
