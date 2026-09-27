---
tipo: indice
status: rascunho
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; cards K1.5 e S1.1)"
atualizado: 2026-09-26
---

# Arquitetura

Como o sistema funciona hoje, entre módulos: caminho de jogo, pipeline de captura, contrato do JSONL e schema do SQLite. Para o porquê de cada escolha, veja os [ADRs](../README.md#decisões-adrs).

Notas previstas:

- `caminho-de-jogo.md` e `alvo.md`: o fluxo TUI → `start_match` → `watcher` → `parser` e para onde ele vai.
- `contrato-events-jsonl.md`: tipos, gerações, BOM e a definição de órfão (K1.5).
- `schema-sqlite.md`: tabelas, colunas e convenções.
- `nao-apagar.md`: o que a poda não toca, com a condição de cada refutação (S1.1).
