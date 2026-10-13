---
tipo: indice
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/plan/all.json (card K1.4)"
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13]: a lista dos 54 itens)"
  - "backup:temp-artifacts/eb5adec0/audit/comments.json (kind=armadilha)"
atualizado: 2026-10-13
---

# Armadilhas

Pegadinhas do engine do CS2, da MatchZy, dos plugins, dos dados de evento e do Windows que já custaram partida ou horas de investigação. Cada item numerado tem sintoma, causa, contorno e fonte `caminho:linha`, conferidos pelo `tools/checar_fontes.py`.

## De onde vêm os 54

São os 54 itens do último achado da auditoria de infra de 26/09 (`infra.json`, `findings[13]`, "Runbook: quirks e gotchas"), a lista que o plano chama de "54 armadilhas". Cada item mantém o número da auditoria (o S1.4 cita o "item 54"). Os 39 comentários `kind=armadilha` do `comments.json` são outra varredura, do código inteiro, e só em parte se sobrepõem a esta lista: não entram na contagem.

A linha de cada fonte foi conferida contra o código de 13/10. Quando ela mudou desde a auditoria, o item diz a antiga em "(auditoria: ...)", fora das crases, para não ser conferida.

## Notas

| Nota | Itens | O que cobre |
|---|---|---|
| [imagem-e-boot.md](imagem-e-boot.md) | 1–6, 10–13 | Pin dos addons, update do CS2 no boot, máscaras, variáveis da imagem, crash na troca de mapa |
| [bots-e-perfis.md](bots-e-perfis.md) | 7–9, 24–30, 32–35, 37 | `botprofile.vpk`, quota, perfis nomeados, estado dos times pela RCON |
| [matchzy.md](matchzy.md) | 14–23, 31 | `.ready`, `live.cfg` e `live_override.cfg`, fim de partida no log, round fantasma |
| [captura-e-eventos.md](captura-e-eventos.md) | 38–46 | Plugin de captura e correções do parser: post_mortem, MR12, dano bruto, bomb site, GOTV |
| [windows-e-docker.md](windows-e-docker.md) | 36, 47–52 | cp1252, SteamCMD, GSLT, Docker Desktop, bind mount, volume, Git Bash |
| [legado-gotv-e-nativo.md](legado-gotv-e-nativo.md) | 53–54 | `tv_delay` do GOTV e modo nativo, na fila da poda |
| [engine-cs2.md](engine-cs2.md) | — | O overflow no signon (`NETWORK_DISCONNECT_OVERFLOW` na entrada), com a frequência por partida desde 19/09 e as hipóteses (P1.13) |

O checklist do que um boot saudável mostra no log é o runbook [servidor-boot-saudavel](../runbooks/servidor-boot-saudavel.md).
