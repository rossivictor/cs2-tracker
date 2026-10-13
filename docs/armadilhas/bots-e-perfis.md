---
tipo: armadilha
status: rascunho
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 7-9, 24-30, 32-35 e 37)"
  - "docs/SPEC.md:177-279"
  - "start_match.py:225-483"
  - "backup:repo-local/logs/teste-correcao.log (linha 799: kick do CSTV)"
atualizado: 2026-10-13
---

# Armadilhas dos bots, dos perfis e do RCON

Itens 7 a 9, 24 a 30, 32 a 35 e 37 da lista de 54 da auditoria de 26/09 ([índice](README.md)):
o `botprofile.vpk`, a quota de bots, os perfis nomeados e a leitura do estado dos times.
Rascunho: o item 37 é hipótese não testada, e os valores efetivos das cvars de bot (itens 29,
30 e 32) esperam o dump de cvars do S1.9.

### 7. O srcds não monta o `overrides/botprofile.vpk`
- **Sintoma:** `Error - no profile for '<nome>' exists.` para todo perfil pro, com o VPK certo no lugar; só os ~20 nomes stock funcionam.
- **Causa:** o dedicated server nunca registra o VPK como search path (o dump GAME/MOD do boot não o lista).
- **Contorno:** o `pre.sh` insere a linha no `gameinfo.gi`, idempotente e tolerante a `\n` e `\r\n`. Depois de update do jogo o `gameinfo.gi` volta ao original, e o boot loga `patched` de novo; sem update, `ja tem o search path`.
- **Fonte:** `docker/pre.sh:4-45` · `docs/SPEC.md:256-268` · `README.md:233-242`

### 8. O VPK custom substitui os perfis padrão
- **Sintoma:** com o VPK ativo, `bot_add_ct Osiris` passa a falhar com `no profile for 'Osiris'`.
- **Causa:** o VPK (variante Low: 1.709 perfis) troca o banco padrão em vez de somar a ele.
- **Contorno:** só nome que está no VPK ativo; o roster se valida contra ele.
- **Fonte:** `docs/SPEC.md:246-251` (auditoria: docs/SPEC.md:251-256)

### 9. Trocar o VPK com o servidor vivo derruba o servidor
- **Sintoma:** `FATAL ERROR: Error reading from loaded packed store` e `Segmentation fault`. O `cs2.sh` reinicia o processo e o perfil novo vale, o que engana: a partida em andamento morre.
- **Causa:** o jogo mantém o VPK mapeado em memória enquanto roda.
- **Contorno:** só em janela, com o container parado, por container descartável. O docstring do `run_match` ainda manda copiar dentro do container e reiniciar: está errado (poda do S1).
- **Fonte:** `commit bafe2b4` · `README.md:247-257` · `docs/runbooks/trilha-de-bots.md:287-292` · `start_match.py:811-818`

### 24. `bot_quota_mode fill` não divide certo com um humano
- **Sintoma:** 4x5 em vez de 5x5.
- **Causa:** o modo fill do engine conta o humano de um jeito que desequilibra os lados.
- **Contorno:** o `start_match` zera a quota, desliga o autobalance e adiciona a quantidade exata por lado, intercalando CT e TR.
- **Fonte:** `README.md:478-480` · `start_match.py:7-9` (auditoria: README.md:476-478)

### 25. `bot_add` mexe na quota sozinho
- **Sintoma:** um `bot_add_ct` leva `bot_quota` de 0 para 2, e o `MaintainBotQuota` completa a vaga com um bot aleatório; re-setar a quota depois dos adds chuta bot nomeado.
- **Causa:** `bot_add` auto-incrementa a quota, e o gerenciador corrige a contagem no think seguinte.
- **Contorno:** `bot_quota 0; bot_quota_mode normal` → `bot_kick` → adds nomeados → quota igual ao total adicionado.
- **Fonte:** `docs/SPEC.md:189-191` · `docs/SPEC.md:211-214` · `start_match.py:448-473`

### 26. Nome duplicado falha duro, sem olhar o time
- **Sintoma:** `Error - <nome> is already in the game.` e nenhum bot adicionado, inclusive quando o nome colide com o nick do humano.
- **Causa:** `UTIL_IsNameTaken` roda antes da busca do perfil e não olha o time.
- **Contorno:** a lineup recusa o nick do humano antes do RCON, e a resposta de cada add é conferida.
- **Fonte:** `docs/SPEC.md:182-185` · `start_match.py:515-518`

### 27. Perfil inexistente só aparece no texto da resposta
- **Sintoma:** um bot a menos, sem erro de RCON; o 4v5 só aparece ao vivo.
- **Causa:** o engine responde `no profile for` como texto comum.
- **Contorno:** checar a resposta de cada add e conferir a contagem de clientes pelo `status` antes do `css_start` (`BotAddError`).
- **Fonte:** `docs/SPEC.md:186-188` · `start_match.py:460-483` (auditoria: start_match.py:359-380)

### 28. Bots nomeados não sobrevivem ao `changelevel`
- **Sintoma:** no mapa 2 da série, os bots voltam aleatórios pela quota.
- **Causa:** todos os clientes caem na troca de mapa.
- **Contorno:** re-adicionar por nome em todo mapa; o `run_match` repete o balanceamento a cada mapa.
- **Fonte:** `docs/SPEC.md:192-194` · `start_match.py:547-549`

### 29. Todo perfil pro tem `Skill = 100`
- **Sintoma:** trocar Low, Medium ou High não muda a força dos pros nomeados.
- **Causa:** as variantes do VPK só mudam os templates dos bots genéricos.
- **Contorno:** não há dial por time; a dificuldade é a variante do VPK (Low desde 28/09).
- **Fonte:** `docs/SPEC.md:195-197`

### 30. O CS2-Bot-Improver ignora `bot_difficulty`
- **Sintoma:** `bot_difficulty` e `custom_bot_difficulty` não mudam nada; o cfg ainda seta 5.
- **Causa:** a dificuldade vem do VPK, lido só na subida do processo.
- **Contorno:** trocar a variante do VPK (item 9); nada por RCON nem pelo wizard.
- **Fonte:** `README.md:226-231` · `server-configs/cfg/gamemode_competitive_server.cfg:13-15` (auditoria: README.md:228-232)

### 32. O cfg do modo volta na virada para o ao vivo
- **Sintoma:** 11 clientes (CT 6 : TR 5), com o bot extra sempre no CT.
- **Causa:** o engine reexecuta o `gamemode_competitive_server.cfg`, que tem `bot_quota 10` e `fill`, por cima do override.
- **Contorno:** depois do `css_start`, reafirmar a quota **antes** de kickar o excedente; kickar com a quota em 10 só repõe o bot.
- **Fonte:** `start_match.py:600-612` · `server-configs/cfg/gamemode_competitive_server.cfg:9-11` (auditoria: start_match.py:497-505)

### 33. Cliente interno da MatchZy cai num time
- **Sintoma:** 6x5 com o balanceamento explícito certo.
- **Causa:** um cliente interno (`ScopedEconomy`), que deveria ficar Unassigned, é designado a um time.
- **Contorno:** `fix_bot_overflow` lê quem está em cada time e kicka pelo nome quem sobra.
- **Fonte:** `start_match.py:287-297` (auditoria: start_match.py:186-191)

### 34. `OnPreResetRound` atrasa no warmup
- **Sintoma:** esperar o time de cada cliente pelo log leva 19 a 29 s, às vezes mais de um ciclo.
- **Causa:** a MatchZy só loga o time a cada reset de round do warmup.
- **Contorno:** contar clientes pelo `status` da RCON, que é imediato; o log fica só para saber o time.
- **Fonte:** `start_match.py:253-266` · `start_match.py:225-232` (auditoria: start_match.py:150-157)

### 35. Resposta da RCON às vezes vem vazia
- **Sintoma:** o comando roda, e a resposta chega vazia.
- **Causa:** o CS2 manda `CONSOLE_ECHO` para o console do servidor, não para o socket.
- **Contorno:** ler o `docker logs` do container.
- **Fonte:** `docs/SPEC.md:278-279` (auditoria: docs/SPEC.md:276-277)

### 37. `bot_kick` sem argumento chuta também o GOTV
- **Sintoma:** `... CSTV kicked by Console` antes de cada início; o CSTV só volta no mapa seguinte.
- **Causa:** o `bot_kick` global do balanceamento expulsa todo bot, inclusive o cliente SourceTV. Hipótese não testada: é parte do bug da demo do GOTV vazia.
- **Contorno:** nenhum aplicado. Se o GOTV voltar a importar, kick por nome só dos bots de jogo.
- **Fonte:** `start_match.py:450` · `backup:repo-local/logs/teste-correcao.log` (linha 799)
