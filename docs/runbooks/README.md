---
tipo: indice
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; playability_protocol)"
atualizado: 2026-10-03
---

# Runbooks

Procedimentos passo a passo, com pré-condição, rollback e o que conferir no fim. Quem opera servidor, container, RCON ou volume é o papel servidor, em janela ([AGENTS.md](../../AGENTS.md)).

## Existentes

- [trilha-de-bots.md](trilha-de-bots.md): a sprint B1, que religa os plugins de bot um por partida real.
- [b1.3-cssharp-1.0.375.md](b1.3-cssharp-1.0.375.md): o B1.3r, que sobe o par Metamod 2.0.0.1469 + CSSharp 1.0.375, com a janela, o G6 e o rollback.
- [b1.4-botaimimprover.md](b1.4-botaimimprover.md): o B1.4, que tira a máscara do BotAimImprover do volume (ficou inativo pela guarda).
- [b1.4b-botaimimprover-upstream.md](b1.4b-botaimimprover-upstream.md): o B1.4b, BotAimImprover compilado do upstream por bind mount, com o sha256 fixado.
- [b1.9-botrandomizer-upstream.md](b1.9-botrandomizer-upstream.md): o B1.9, BotRandomizer compilado do upstream por bind mount, com o smoke só de bots na janela.
- [versoes-conhecidas.md](versoes-conhecidas.md): a combinação boa de cada tag `jogavel-*` (versões, máscaras, config-hash e sha256), para a volta ao jogável (B0.3).
- [smoke-partida-de-bots.md](smoke-partida-de-bots.md): a partida só de bots dentro da janela, com as três armadilhas de 27/09 e o fechamento nas cvars do boot (B0.9b).
- [voltar-ao-jogavel.md](voltar-ao-jogavel.md): o `tools/jogavel.py` (`status`, `voltar`, `atualizar` e a janela: `abrir`, `vigiar` e o checklist do `fechar`) (B0.7).
- [reconstruir-volume.md](reconstruir-volume.md): o que o `cs2-data` external protege e o que não, e a reconstrução a partir do `C:/cs2server` (B0.8).

## Previstos

- Jogo: `jogar`.
- Servidor: `janela-de-manutencao`, `servidor-boot-saudavel` (K1.4), `inventario-volume` (B0.9), `compilar-plugin` (B1.2).
- Dados: `backup-e-restauracao`.
