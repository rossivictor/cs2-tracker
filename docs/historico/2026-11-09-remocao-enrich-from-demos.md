---
tipo: historico
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/dead_captura.json (captura-11: verification.verdict confirmado, reason e evidence)"
  - "docs/agents/plano-2026-09-26.json:1654-1672 (S1.2: critério e arquivos)"
  - "docs/adr/0008-captura-por-plugin-proprio.md:35 (a demo deixa de ser fonte; o enrich_from_demos sai no S1.2)"
  - "docs/adr/0006-pauta-1.md:71-78 (Q11=C: S1.2 e S1.5 tiram o enrich_from_demos e o awpy)"
  - "docs/arquitetura/nao-apagar.md:119 (captura-2: PLAYER_PROPS espera esta remoção)"
  - "docs/arquitetura/nao-apagar.md:121 (captura-42: o fallback de flash_duration espera esta remoção)"
  - "docs/arquitetura/nao-apagar.md:166 (captura-3: awpy e polars esperam esta remoção)"
atualizado: 2026-11-09
---

<!--
Documento histórico: não editar abaixo da linha horizontal. Correções e
decisões novas vão para a nota viva (ADR ou docs/arquitetura/nao-apagar.md).
-->

# Remoção do `enrich_from_demos` (card S1.2, captura-11)

---

**Data:** 2026-11-09. **Card:** S1.2 (sprint S1, poda da Captura). **ID da auditoria de 26/09:** `captura-11`.

## O que saiu

- `tools/enrich_from_demos.py` (238 linhas): enriquecia partidas já ingeridas com o que só a demo tinha (posições reais, `rounds.freeze_end_tick`, `flash_duration`, `equip_value`, armadura e kit), casando o nome do `.dem` com `matches.demo_name`.
- `tests/test_enrich_from_demos.py` (153 linhas): os testes dele.

Nada mais importava o script; o `grep` por `enrich_from_demos` fora da KB só achava os dois arquivos e os comentários do `pyproject.toml`.

## Por quê

- **A demo deixa de ser fonte.** A [ADR-0008](../adr/0008-captura-por-plugin-proprio.md) fixa o plugin próprio como fonte da captura e marca o `enrich_from_demos` como legado a sair no S1.2.
- **Q11=C.** Na [ADR-0006](../adr/0006-pauta-1.md), o Victor decidiu apagar as linhas das partidas 1 e 2 (as de origem demo) no S1.4, e o S1.2 e o S1.5 tiram o `enrich_from_demos` e o awpy sabendo disso. Com a Q12=A, a ordem da S1 segue a do plano.
- **Veredito da auditoria: confirmado, sem ressalva.** O enriquecedor não tinha caminho feliz: as 39 demos de `docker/demos-live/` falhavam no parse do awpy (30 com `KeyError 'round_officially_ended'`, 9 com `TypeError`), nenhuma partida chegou a ser enriquecida, e nas partidas do plugin v0.3+ a trava de "já tem posição real" barrava tudo. Nenhum `.dem` chegou ao host depois de 21/09.
- **Fora da régua de proteção.** O `captura-11` não está nos refutados, nos preservados, nos confirmados com ressalva nem nos incertos de [nao-apagar.md](../arquitetura/nao-apagar.md): é um dos 58 confirmados sem ressalva.

## O que ficou

- `parser.py`, inclusive `PLAYER_PROPS` e `parse_and_store`: são do S1.3 (veredito novo, captura-2) e do S1.4 (remoção).
- `awpy` e `polars` no `pyproject.toml`: o `parser.py` ainda os importa. Só os comentários mudaram, para citar só o `parser.py`; as versões seguem iguais até o S1.5.
- O fallback de tempo cego por `flash_duration` (captura-42, `stats.py`) e a coluna `player_positions.flash_duration`: este card cumpre uma das condições dele ("`enrich_from_demos` fora"), mas o veredito é do S1.3.
- O import de awpy e polars no topo do `parser.py` (captura-3): este card cumpre a condição "`enrich_from_demos` fora"; o resto é do S1.3, S1.5 e S2.1.

## Volta

`git revert` do merge commit do S1.2 traz os dois arquivos de volta. O script não roda em produção nem faz parte do caminho de jogo.
