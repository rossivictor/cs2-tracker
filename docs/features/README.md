# Specs de Feature — Índice

Quebra da [SPEC.md](../SPEC.md) em features executáveis, organizadas por milestone.
Cada milestone entrega algo que **funciona sozinho** e pode ser usado antes do próximo.

**Convenção:** features são `F<milestone>.<n>` e o ID é estável — se uma feature for
cortada, o número não é reaproveitado. Cada spec tem objetivo, escopo, comportamento,
arquivos afetados e critério de aceite.

---

## Milestones

| # | Milestone | Entrega | Depende de |
|---|---|---|---|
| **M0** | [Validação da premissa](M0-validacao.md) | Saber se `bot_add_ct "NiKo"` funciona nesta máquina | — |
| **M0.5** | [Correção do placar](M0.5-placar.md) ✅ | Placar, vitória/derrota e K/D corretos, histórico incluído | — |
| **M1** | [Lineups nomeadas (headless)](M1-lineups-headless.md) | Jogar contra a FURIA pelo terminal | M0 |
| **M2** | [Núcleo desacoplado da UI](M2-nucleo.md) | Core testável sem Textual | — |
| **M3** | [App web com paridade](M3-web-paridade.md) | Partida completa pelo browser | M1, M2 |
| **M3.5** | [Home e barra de navegação](M3.5-home.md) 🟡 | Tela inicial que resume o histórico e dispara partida em 1 clique | M3 |
| **M4** | [Seletor de lineups](M4-seletor.md) | Montar "eu + donk contra a FURIA" no browser | M1, M3 |
| **M5** | [Confiabilidade do início](M5-confiabilidade.md) | Warmup travado deixa de ser problema manual | M3 |
| **M6** | [Estatísticas](M6-estatisticas.md) | Head-to-head contra cada pro + marcos | M3 |
| **M7** | [Acabamento](M7-acabamento.md) | Veto com personalidade, revanche, TUI aposentada | M4, M6 |

## Dependências

```
M0 ──► M1 ──┬──► M3 ──┬──► M3.5 🟡
            │         │
M2 ─────────┘         ├──► M4 ──┐
                      │         │
                      ├──► M5   ├──► M7
                      │         │
M0.5 ✅ ──────────────┴──► M6 ──┘
```

**M0.5 já está feito.** Ele nasceu fora do plano original, de um placar
errado numa BO3 real, e precisava vir antes do M1: o M1 gera muitas partidas
e o head-to-head do M6 se apoia em placar e vitória/derrota corretos — dado
ruim na base contamina tudo que vem depois.

**M3.5 está parcialmente feito, fora de ordem.** A fatia de M3.5 que só precisa de
dado real e HTML estático (histórico, melhor mapa, arma mais letal, melhor lado) não
depende do M3 existir — só de banco. Ela já foi implementada (`stats.py`, `home.py`,
`templates/`) sem esperar o app web. O que continua bloqueado por M3: início de
partida em 1 clique, launcher, log ao vivo — ver "Status de implementação" em
[M3.5-home.md](M3.5-home.md).

**M0 e M2 podem começar ao mesmo tempo.** M2 (extrair o `WizardSession`, trocar o
`redirect_stdout`) não depende de nada e é puro refactor do que já existe — dá pra
fazer enquanto o M0 ainda não foi rodado.

**M5 e M6 são independentes entre si** e ambos só precisam do M3.

## Por que esta ordem

**M1 vem antes de qualquer trabalho de web.** Ele entrega a proposta de valor
inteira — jogar contra um time real, com os pros certos — usando o CLI que já existe.
Se a fidelidade decepcionar (risco registrado em SPEC.md §13), você descobre no
milestone 1, antes de ter escrito uma linha de front.

**O seletor (M4) vem depois da paridade (M3).** O M3 substitui a TUI com o fluxo que
já existe; o M4 acrescenta a tela nova. Separar os dois evita depurar refactor e
feature nova ao mesmo tempo.

**A TUI só morre no M7.** Ela continua sendo o caminho conhecido-bom até o web ter
provado paridade em uso real, não só em teoria.

## Registro de resultados

O M0 produz um fato que pode invalidar o resto. Quando rodar, anote o resultado em
[SPEC.md §10](../SPEC.md) — a spec é o documento vivo, estes arquivos são o plano.
