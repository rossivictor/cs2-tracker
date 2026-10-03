---
name: cs2-partida
description: Validação por partida real no cs2-tracker (G6 da janela, G7 da partida, tags candidato-N e jogavel-*, coleta pós-partida e tools/evidencia_partida.py). Use para julgar um candidato ou entender o que a próxima partida valida.
---

# Partida como evidência

O degrau do caminho de jogo (regra no AGENTS.md) espera a partida do Victor para fechar. Esta skill aponta onde cada passo está escrito; o porquê é a [ADR-0004](../../../docs/adr/0004-jogo-sempre-jogavel.md).

| Passo | Quem | Onde está |
|---|---|---|
| tag `candidato-N` no merge do degrau | tech-manager | [tech-manager.md](../../agents/tech-manager.md), seção 1 |
| G6: o candidato no ar, conferido na janela | servidor | runbook do card e [servidor.md](../../agents/servidor.md), Janela |
| coleta pós-partida (`tools/jogavel.py coletar`) | servidor | [servidor.md](../../agents/servidor.md), Coleta pós-partida |
| G7: a partida julgada pela ferramenta | QA, fase 2 | [qa.md](../../agents/qa.md), Duas fases e passo 5 |
| tag `jogavel-AAAA-MM-DD` e `Concluída` | tech-manager | [tech-manager.md](../../agents/tech-manager.md), seção 2 |

## A ferramenta do G7

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/evidencia_partida.py --help
```

Ela lê só cópias (logs com `-t`, eventos, banco `mode=ro`, sha256 e os dois config-hash) e recusa o banco e a pasta de eventos reais. A linha completa e o que cada saída quer dizer estão no passo 5 do [qa.md](../../agents/qa.md); o veredito é dela, não do que a TUI anuncia.

## O que está valendo agora

```
C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe tools/jogavel.py status
```

Mostra a última `jogavel-*` e o candidato em espera (`data/candidato.json`). O histórico das tags fica em `logs/jogavel/tags.md` e, com versões e hashes, em [versoes-conhecidas.md](../../../docs/runbooks/versoes-conhecidas.md). Ordem dos degraus de bot: [trilha-de-bots.md](../../../docs/runbooks/trilha-de-bots.md).
