---
tipo: armadilha
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 53-54)"
  - "server-configs/cfg/gamemode_competitive_server.cfg:53-131"
  - "watcher.py:13-56"
  - "README.md:404-482"
atualizado: 2026-10-13
---

# Armadilhas do GOTV e do modo nativo (legado)

Itens 53 e 54 da lista de 54 da auditoria de 26/09 ([índice](README.md)). Os dois caminhos
estão na fila da poda (S1.4 e S1.10): este registro existe para que o porquê sobreviva ao
código. Quando o código sair, o item fica, com a fonte trocada pelo commit da remoção.

### 53. O CS2 trava `tv_delay` em 960, e delay alto piora a demo
- **Sintoma:** com `tv_delay 960`, a MatchZy loga `Going to stop demorecording in 974.5s` e o `.dem` nunca é escrito; o `mp_match_restart_delay` estica (105 virou 130 s) e o cliente cai na votação entre mapas.
- **Causa:** o engine limita o delay a 960 s, e a gravação só cobre o buffer: a duração da demo sempre acompanhou o delay, sem conter a partida.
- **Contorno:** `tv_delay 0`. A captura de verdade é o plugin; a demo é só reserva do nome do mapa.
- **Fonte:** `server-configs/cfg/gamemode_competitive_server.cfg:90-129` · `watcher.py:426-430`

### 54. Listen server não abre RCON TCP (modo nativo)
- **Sintoma:** RCON não conecta numa partida local pelo menu; `netstat` só mostra UDP na porta do jogo.
- **Causa:** limitação do listen server da Source 2. No dedicado nativo: sem `+ip 0.0.0.0` o RCON fica preso no IP da rede local; sem `-condebug` não há `console.log` (caminho fixo); sem `log on` não há `World triggered`; `record` não existe no dedicado.
- **Contorno:** servidor dedicado com `-condebug -conclearlog -usercon`, `+ip 0.0.0.0`, `log on` e gravação por `tv_record`.
- **Fonte:** `watcher.py:13-56` · `README.md:432-439` · `README.md:459-477` (auditoria: README.md:462-478)
