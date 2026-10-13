---
tipo: armadilha
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 38-46)"
  - "docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:79-144"
  - "parser.py:337-361"
  - "parser.py:741-761"
  - "parser.py:871-884"
  - "commit 193cd6c"
atualizado: 2026-10-13
---

# Armadilhas da captura e dos dados de evento

Itens 38 a 46 da lista de 54 da auditoria de 26/09 ([índice](README.md)): o que o engine
entrega ao plugin `Cs2TrackerEvents` e o que o `parser.py` precisa corrigir na ingestão.

### 38. Depois de morrer, o humano controla um bot com a identidade dele
- **Sintoma:** K/D inflado (28/24 contra os 22/18 do CSV da MatchZy no Dust2).
- **Causa:** ao assumir um bot companheiro, o controlador mantém a identidade do humano, e as kills e mortes seguintes entram como dele.
- **Contorno:** `mark_post_mortem` marca tudo depois da primeira morte do humano no round; os três mapas da série 44 batem com o CSV.
- **Fonte:** `parser.py:871-884`

### 39. O engine às vezes conta o round fantasma no placar
- **Sintoma:** placar que não fecha em 13 num MR12 encerrado.
- **Causa:** o round fantasma (MatchZy, item 31) às vezes entra no placar oficial e às vezes não, e o stream não traz o placar autoritativo.
- **Contorno:** reconciliação pelo invariante MR12: se ninguém chega a 13 depois dos descartes, o fantasma mais recente volta a contar. Muleta até o plugin emitir o placar.
- **Fonte:** `parser.py:741-761`

### 40. `player_hurt.dmg_health` é o dano bruto
- **Sintoma:** 136 de dano numa vítima de 100 de vida; ADR 18 % acima do engine (1614 contra 1370 em 10 rounds).
- **Causa:** as duas fontes reportam o dano da bala, não a vida removida.
- **Contorno:** `clamp_damage_health` corta pelo acumulado por (round, vítima), em ordem de tique; o bruto fica em `dmg_health_raw`. Linha sem vítima identificada não é cortada.
- **Fonte:** `commit 193cd6c` · `parser.py:337-361`

### 41. `Server.GameDirectory` devolve `.../game`
- **Sintoma:** arquivo de eventos gravado fora da pasta montada.
- **Causa:** a API devolve `.../game`, não `.../game/csgo`, apesar do nome.
- **Contorno:** o plugin monta `game/csgo/events-live/current.jsonl` à mão.
- **Fonte:** `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:81-85`

### 42. `OnMapStart` não dispara para o mapa já carregado
- **Sintoma:** na primeira partida depois do boot, o arquivo de eventos nunca é criado.
- **Causa:** o plugin carrega com o mapa já em pé, e o listener só pega as trocas seguintes.
- **Contorno:** `ResetForNewMap()` também no `Load()`. Por isso o boot loga duas linhas `[Cs2TrackerEvents] Pronto`.
- **Fonte:** `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:107-114`

### 43. Gravar no bind mount do Windows na thread do jogo derruba o jogador
- **Sintoma:** escrita de 0,9 ms no início a 8,2 ms (pico 99,9 ms) aos 18 min, contra 15,6 ms de tique; `NETWORK_DISCONNECT_OVERFLOW` em jogo (23/09).
- **Causa:** o bind mount Docker → Windows é lento e piora com o tamanho do arquivo; nenhuma política de flush resolve.
- **Contorno:** a v0.4.0 só serializa e enfileira; uma thread própria grava. O overflow no signon é outra coisa ([engine-cs2](engine-cs2.md)).
- **Fonte:** `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:232-250`

### 44. `EventBombPlanted.Site` é índice de entidade
- **Sintoma:** `bomb_site` NULL em todos os 266 rounds de origem `events`.
- **Causa:** `Site` traz o índice da entidade do alvo (370, 3956), não 0/1.
- **Contorno:** gravar o `LastPlaceName` (`BombsiteA`) em `place` e manter `site` bruto.
- **Fonte:** `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:686-693`

### 45. O bot do GOTV aparece como jogador
- **Sintoma:** um adversário que nunca luta na matriz de duelos, com o nome do servidor + CSTV.
- **Causa:** `Utilities.GetPlayers()` inclui o SourceTV, sem time, sem pawn e com contadores zerados.
- **Contorno:** `_participa` descarta quem não tem time; o humano nunca é descartado.
- **Fonte:** `parser.py:944-958`

### 46. `current.jsonl` é truncado no boot e a cada mapa
- **Sintoma:** rounds de uma partida que caiu antes do arquivamento somem no mapa seguinte.
- **Causa:** `ResetForNewMap` grava o arquivo vazio no `Load()` e em todo `OnMapStart`; só o watcher salva, renomeando.
- **Contorno:** o `run_match` preserva o arquivo com round real como `orphan_<utc>.jsonl` antes do loadmatch (P1.1).
- **Fonte:** `docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs:134-137` · `start_match.py:52-59` · `start_match.py:79-106`
