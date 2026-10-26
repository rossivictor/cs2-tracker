---
tipo: indice
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; playability_protocol)"
atualizado: 2026-10-24
---

# Runbooks

Procedimentos passo a passo, com pré-condição, rollback e o que conferir no fim. Quem opera servidor, container, RCON ou volume é o papel servidor, em janela ([AGENTS.md](../../AGENTS.md)).

## Existentes

- [trilha-de-bots.md](trilha-de-bots.md): a sprint B1, que religa os plugins de bot um por partida real.
- [b1.3-cssharp-1.0.375.md](b1.3-cssharp-1.0.375.md): o B1.3r, que sobe o par Metamod 2.0.0.1469 + CSSharp 1.0.375, com a janela, o G6 e o rollback.
- [b1.3s-cssharp-1.0.378.md](b1.3s-cssharp-1.0.378.md): o B1.3s, CSSharp 1.0.378 (fix do CS2 v1.41.9.2) instalada à mão no volume, com o sha256 do asset sem runtime conferido, o G6 e a volta pelo snapshot.
- [b1.4-botaimimprover.md](b1.4-botaimimprover.md): o B1.4, que tira a máscara do BotAimImprover do volume (ficou inativo pela guarda).
- [b1.4b-botaimimprover-upstream.md](b1.4b-botaimimprover-upstream.md): o B1.4b, BotAimImprover compilado do upstream por bind mount, com o sha256 fixado.
- [b1.9-botrandomizer-upstream.md](b1.9-botrandomizer-upstream.md): o B1.9, BotRandomizer compilado do upstream por bind mount, com o smoke só de bots na janela.
- [b1.13-plugins-de-bot-2000935.md](b1.13-plugins-de-bot-2000935.md): o B1.13, os 6 plugins de bot conferidos offline na 2000935 com a CSSharp 1.0.378 (`tools/conferir_plugins_bot.py`), o NadeSystem de um fork com a assinatura da smoke refeita e o roteiro da janela que desliga a válvula vanilla (rascunho: build e janela pendentes).
- [b1.9b-botrandomizer-2000930.md](b1.9b-botrandomizer-2000930.md): o B1.9b, a assinatura do construtor de `CEconItemView` corrigida no upstream para a build 2000930, com a conferência no `libserver.so`, o plano de build e a volta à mão (rascunho: build e janela pendentes).
- [b1.12-segfault-troca-de-mapa-md3.md](b1.12-segfault-troca-de-mapa-md3.md): o B1.12, investigação do segfault na virada de série da MD3 de 04/10, com as hipóteses e os testes de janela (rascunho: T0 e T1 braço A em 13/10, T2 em 19/10 e 20/10, sem queda reproduzida).
- [b1.7b-botai-fork-assinatura.md](b1.7b-botai-fork-assinatura.md): o B1.7b, BotAI de um fork do 1.8.12 com o `m_gameState` lido por assinatura no load, a conferência no `libserver.so` da 2000930, o build e a troca por bind (rascunho: build e janela pendentes).
- [versoes-conhecidas.md](versoes-conhecidas.md): a combinação boa de cada tag `jogavel-*` (versões, máscaras, config-hash e sha256), para a volta ao jogável (B0.3).
- [smoke-partida-de-bots.md](smoke-partida-de-bots.md): a partida só de bots dentro da janela, com as três armadilhas de 27/09 e o fechamento nas cvars do boot (B0.9b).
- [voltar-ao-jogavel.md](voltar-ao-jogavel.md): o `tools/jogavel.py` (`status`, `voltar`, `atualizar` e a janela: `abrir`, `vigiar` e o checklist do `fechar`) (B0.7).
- [reconstruir-volume.md](reconstruir-volume.md): o que o `cs2-data` external protege e o que não, e a reconstrução a partir do `C:/cs2server` (B0.8).
- [servidor-boot-saudavel.md](servidor-boot-saudavel.md): o que o log, a RCON e os arquivos montados mostram num boot saudável, o ruído conhecido e as linhas proibidas, ligadas às [armadilhas](../armadilhas/README.md) (K1.4).
- [inventario-volume.md](inventario-volume.md): o inventário do volume da Janela 0 (B0.9).

## Previstos

- Jogo: `jogar`.
- Servidor: `janela-de-manutencao`, `compilar-plugin` (B1.2).
- Dados: `backup-e-restauracao`.
