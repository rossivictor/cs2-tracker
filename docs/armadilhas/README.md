---
tipo: indice
status: rascunho
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (card K1.4)"
  - "backup:temp-artifacts/eb5adec0/audit/comments.json (kind=armadilha)"
atualizado: 2026-10-13
---

# Armadilhas

Pegadinhas do engine do CS2, da MatchZy, dos plugins, dos dados de evento e do Windows que já custaram partida ou horas de investigação. Cada uma tem sintoma, causa, contorno e fonte `caminho:linha`.

Os 54 itens, hoje espalhados em comentários, chegam no K1.4, verificados pelo `tools/checar_fontes.py`.

## Existentes

- [engine-cs2.md](engine-cs2.md): o overflow no signon (`NETWORK_DISCONNECT_OVERFLOW` na entrada), com a frequência por partida desde 19/09 e as hipóteses do `warmup.cfg`, da carga do host e da entrada fria (P1.13).
