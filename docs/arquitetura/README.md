---
tipo: indice
status: rascunho
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; cards K1.5 e S1.1)"
atualizado: 2026-10-13
---

# Arquitetura

Como o sistema funciona hoje, entre módulos: caminho de jogo, pipeline de captura, contrato do JSONL e schema do SQLite. Para o porquê de cada escolha, veja os [ADRs](../README.md#decisões-adrs).

Notas:

- [contrato-events-jsonl.md](contrato-events-jsonl.md) (rascunho): tipos, gerações, BOM, nomes de arquivo e a regra do round que define órfão e cauda (K1.5).

Notas previstas:

- `caminho-de-jogo.md` e `alvo.md`: o fluxo TUI → `start_match` → `watcher` → `parser` e para onde ele vai.
- `schema-sqlite.md`: tabelas, colunas e convenções.
- `nao-apagar.md`: o que a poda não toca, com a condição de cada refutação (S1.1).
