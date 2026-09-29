---
tipo: indice
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; playability_protocol)"
atualizado: 2026-09-28
---

# Runbooks

Procedimentos passo a passo, com pré-condição, rollback e o que conferir no fim. Quem opera servidor, container, RCON ou volume é o papel servidor, em janela ([AGENTS.md](../../AGENTS.md)).

## Existentes

- [trilha-de-bots.md](trilha-de-bots.md): a sprint B1, que religa os plugins de bot um por partida real.
- [b1.3-cssharp-1.0.375.md](b1.3-cssharp-1.0.375.md): o B1.3r, que sobe o par Metamod 2.0.0.1469 + CSSharp 1.0.375, com a janela, o G6 e o rollback.
- [versoes-conhecidas.md](versoes-conhecidas.md): a combinação boa de cada tag `jogavel-*` (versões, máscaras, config-hash e sha256), para a volta ao jogável (B0.3).
- [smoke-partida-de-bots.md](smoke-partida-de-bots.md): a partida só de bots dentro da janela, com as três armadilhas de 27/09 e o fechamento nas cvars do boot (B0.9b).

## Previstos

- Jogo: `jogar`, `voltar-ao-jogavel` (B0.7).
- Servidor: `janela-de-manutencao`, `servidor-boot-saudavel` (K1.4), `inventario-volume` (B0.9), `reconstruir-volume` (B0.8), `compilar-plugin` (B1.2).
- Dados: `backup-e-restauracao`.
