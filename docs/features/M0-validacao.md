# M0 — Validação da premissa

> **Bloqueia:** M1, e por consequência M4 e M7.
> **Esforço:** minutos.
> **Entrega:** um fato anotado na SPEC.md que confirma ou destrói D2.

Todo o produto assume que dá pra pedir um pro específico ao servidor. Duas evidências
conflitam sobre isso (SPEC.md §10) e nenhuma linha de código deve ser escrita antes
de resolver o conflito.

---

## F0.1 — Provar que perfis pro nomeados existem e entram

### Objetivo

Determinar se `bot_add_ct "<nome de pro>"` cria um bot com aquele perfil neste
servidor, e de quebra medir o comportamento real de três das cinco restrições da
SPEC.md §10.

### Procedimento

Com o container de pé (`docker compose up -d`), enviar por RCON, em ordem:

| # | Comando | O que está sendo medido |
|---|---|---|
| 1 | `bot_kick; bot_quota 0; bot_quota_mode normal` | Estado limpo |
| 2 | `status` | Linha de base: como o CS2 lista bots, se lista |
| 3 | `bot_add_ct Osiris` | Caminho feliz com perfil stock conhecido |
| 4 | `bot_quota` | Restrição 3: a quota auto-incrementou pra 1? |
| 5 | `bot_add_ct Osiris` | Restrição 1: nome duplicado no mesmo time |
| 6 | `bot_add_t Osiris` | Restrição 1: nome duplicado em time oposto |
| 7 | `bot_add_ct NiKo` | **A pergunta central** |
| 8 | `status` | Confirmar quem está de fato no servidor |
| 9 | `bot_quota 0` | Restrição 3: o bot nomeado é chutado? |

Se o RCON devolver corpo vazio, ler a saída em `docker logs cs2-spike` — o CS2 manda
`CONSOLE_ECHO` pro console do servidor, não pro socket.

### Resultados possíveis

| Resultado do passo 7 | Significado | Ação |
|---|---|---|
| Bot `NiKo` aparece no `status` | ✅ D2 confirmado, produto viável como especificado | Seguir pro M1 |
| `Error - no profile for 'NiKo' exists.` | ❌ O VPK com os pros não está ativo | Ir pra F0.2 |
| Bot entra com outro nome | ⚠️ Comportamento divergente do esperado | Investigar antes de seguir |

### Critério de aceite

- Os nove comandos foram executados e a resposta de cada um está registrada
- A pergunta "`bot_add_ct "NiKo"` funciona?" tem resposta sim ou não
- SPEC.md §10 atualizada com o resultado e a data

### Observação

Vale testar mais de um nome de pro (`s1mple`, `ZywOo`, `donk`), porque um único
negativo pode ser erro de grafia — os nomes no VPK têm maiúsculas e caracteres
específicos (`huNter-`, `m0NESY`).

---

## F0.2 — Diagnóstico: por que só nomes stock apareceram até hoje

> Condicional: só roda se F0.1 der negativo, **ou** se der positivo e você quiser
> entender por que os pros nunca saíram no sorteio.

### Objetivo

Explicar por que os ~3.700 eventos de 4 partidas em `docker/events-live/*.jsonl`
contêm apenas os ~20 perfis stock da Valve, se o VPK instalado tem 1.233.

### Hipóteses, em ordem de custo

1. **`bot_difficulty 5` está fora da faixa válida** e colapsa a seleção aleatória
   para um subconjunto. O valor está em `server-configs/cfg/gamemode_competitive_server.cfg:13-18`
   e a faixa histórica do engine é 0–3. Teste: baixar pra `3`, `bot_kick`,
   `bot_quota 10`, e ver que nomes saem.
2. **O VPK ativo não é o que se supõe.** Conferir qual arquivo está em
   `game/csgo/overrides/botprofile.vpk` dentro do volume `cs2-tracker_cs2-data`
   e se ele contém mesmo as entradas de pro.
3. **As partidas gravadas são anteriores** à instalação do VPK do CS2-Bot-Improver.
   Conferir a data dos `.jsonl` contra a data de criação do volume.

### Critério de aceite

- Uma das três hipóteses confirmada com evidência, ou todas descartadas com evidência
- Se a causa for corrigível por cvar ou por arquivo, a correção está aplicada e
  reproduzida

### Impacto se nada resolver

D2 cai. O produto passaria a depender de construir um `botprofile.db` próprio com os
perfis pro e empacotá-lo em VPK — o que reintroduz "rebuild + restart por partida"
e obriga a revisitar SPEC.md §1, §6 e §7.
