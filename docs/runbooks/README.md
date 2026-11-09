---
tipo: indice
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (final.kb_structure; playability_protocol)"
  - "docs/runbooks/versoes-conhecidas.md:203 (jogavel-2026-10-25: o B1.3s com a partida 97)"
  - "docs/runbooks/versoes-conhecidas.md:244-249 (a jogavel-2026-10-25 fecha o candidato-24 do B1.3s; janela de 25/10 15:01)"
  - "docs/runbooks/versoes-conhecidas.md:205 (jogavel-2026-10-26-2: o B1.13 com a partida 101)"
  - "docs/runbooks/versoes-conhecidas.md:228-230 (a jogavel-2026-10-26-2 fecha o candidato-26 do B1.13; janela de 26/10 13:48)"
atualizado: 2026-11-09
---

# Runbooks

Procedimentos passo a passo, com pré-condição, rollback e o que conferir no fim. Quem opera servidor, container, RCON ou volume é o papel servidor, em janela ([AGENTS.md](../../AGENTS.md)).

## Existentes

- [trilha-de-bots.md](trilha-de-bots.md): a sprint B1, que religa os plugins de bot um por partida real.
- [b1.3-cssharp-1.0.375.md](b1.3-cssharp-1.0.375.md): o B1.3r, que sobe o par Metamod 2.0.0.1469 + CSSharp 1.0.375, com a janela, o G6 e o rollback.
- [b1.3s-cssharp-1.0.378.md](b1.3s-cssharp-1.0.378.md): o B1.3s, CSSharp 1.0.378 (fix do CS2 v1.41.9.2) instalada à mão no volume, com o sha256 do asset sem runtime conferido, o G6 e a volta pelo snapshot (executado na janela de 25/10 15:01, 3ª tentativa, e validado pela partida 97, G7 OK: `jogavel-2026-10-25`, em [versões conhecidas](versoes-conhecidas.md#tags-jogáveis); Históricos dos cards 22,5 e 89).
- [b1.4-botaimimprover.md](b1.4-botaimimprover.md): o B1.4, que tira a máscara do BotAimImprover do volume (ficou inativo pela guarda).
- [b1.4b-botaimimprover-upstream.md](b1.4b-botaimimprover-upstream.md): o B1.4b, BotAimImprover compilado do upstream por bind mount, com o sha256 fixado.
- [b1.9-botrandomizer-upstream.md](b1.9-botrandomizer-upstream.md): o B1.9, BotRandomizer compilado do upstream por bind mount, com o smoke só de bots na janela.
- [b1.13-plugins-de-bot-2000935.md](b1.13-plugins-de-bot-2000935.md): o B1.13, os 6 plugins de bot conferidos offline na 2000935 com a CSSharp 1.0.378 (`tools/conferir_plugins_bot.py`), o NadeSystem de um fork com a assinatura da smoke refeita e o roteiro da janela que desliga a válvula vanilla (executado na janela de 26/10 13:48, com a build do NadeSystem, e validado pela partida 101, G7 OK: `jogavel-2026-10-26-2`, em [versões conhecidas](versoes-conhecidas.md#tags-jogáveis); Histórico do card 29,97).
- [b1.15-plugins-de-bot-2000940.md](b1.15-plugins-de-bot-2000940.md): o B1.15, os 6 plugins de bot conferidos offline na build 2000940 (CS2 v1.41.9.5) sem mudar nada, os releases e issues lidos e o roteiro da janela que desliga a válvula vanilla junto com o ff do K1.9 (executado em 04/11: G6, smoke e partida 107 com G7 OK; a ressalva do overflow no signon e o critério "sem queda depois de `FULL` + 60 s e sem segfault").
- [b1.9b-botrandomizer-2000930.md](b1.9b-botrandomizer-2000930.md): o B1.9b, a assinatura do construtor de `CEconItemView` corrigida no upstream para a build 2000930, com a conferência no `libserver.so`, o plano de build e a volta à mão (rascunho: build e janela pendentes).
- [b1.12-segfault-troca-de-mapa-md3.md](b1.12-segfault-troca-de-mapa-md3.md): o B1.12, investigação do segfault na virada de série da MD3 de 04/10, com as hipóteses e os testes de janela (rascunho: T0 e T1 braço A em 13/10, T2 em 19/10 e 20/10, sem queda reproduzida).
- [b1.7b-botai-fork-assinatura.md](b1.7b-botai-fork-assinatura.md): o B1.7b, BotAI de um fork do 1.8.12 com o `m_gameState` lido por assinatura no load, a conferência no `libserver.so` da 2000930, o build e a troca por bind (rascunho: build e janela pendentes).
- [versoes-conhecidas.md](versoes-conhecidas.md): a combinação boa de cada tag `jogavel-*` (versões, máscaras, config-hash e sha256), para a volta ao jogável (B0.3).
- [smoke-partida-de-bots.md](smoke-partida-de-bots.md): a partida só de bots dentro da janela, com as três armadilhas de 27/09 e o fechamento nas cvars do boot (B0.9b).
- [voltar-ao-jogavel.md](voltar-ao-jogavel.md): o `tools/jogavel.py` (`status`, `voltar`, `atualizar` e a janela: `abrir`, `vigiar` e o checklist do `fechar`) (B0.7).
- [reconstruir-volume.md](reconstruir-volume.md): o que o `cs2-data` external protege e o que não, e a reconstrução a partir do `C:/cs2server` (B0.8).
- [servidor-boot-saudavel.md](servidor-boot-saudavel.md): o que o log, a RCON e os arquivos montados mostram num boot saudável, o ruído conhecido e as linhas proibidas, ligadas às [armadilhas](../armadilhas/README.md) (K1.4).
- [inventario-volume.md](inventario-volume.md): o inventário do volume da Janela 0 (B0.9).
- [s1.9-dump-cvars-bot.md](s1.9-dump-cvars-bot.md): o S1.9, dump só leitura das cvars de bot pela RCON em janela (dificuldade, thresholds, quota e as do cfg), com a conferência contra o `gamemode_competitive_server.cfg` versionado (rascunho: janela pendente).

## Previstos

- Jogo: `jogar`.
- Servidor: `janela-de-manutencao`, `compilar-plugin` (B1.2).
- Dados: `backup-e-restauracao`.
