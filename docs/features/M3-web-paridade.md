# M3 — App web com paridade

> **Depende de:** M1, M2 · **Bloqueia:** M4, M5, M6
> **Entrega:** uma partida completa, do perfil ao `.ready`, sem abrir a TUI.

O objetivo é **paridade**, não novidade: o fluxo é o mesmo de hoje, num browser.
O seletor de lineups é o M4 — aqui as lineups vêm dos presets de time (F1.1) num
`<select>` simples.

---

## F3.1 — Esqueleto do app e sessão stateful

### Objetivo

Subir o servidor FastAPI, servir templates, e guardar o estado do wizard e da
partida ativa fora do browser.

### Comportamento

- FastAPI + Jinja + HTMX, sem build step, bind em `127.0.0.1`
- Uma `WizardSession` (F2.1) viva no servidor, com a partida ativa referenciada nela
- **Só uma partida por vez** — o `rcon_lock` de hoje ([wizard_tui.py:874](../../wizard_tui.py))
  passa a valer pro processo; tentar iniciar uma segunda é recusado com mensagem
- Encerramento explícito: rota que mata o `watcher_proc` e libera o evento de ready,
  mais um handler de `atexit`/sinal que faz o mesmo se o servidor cair

### Contexto

A TUI mata o watcher e libera a thread ao sair ([wizard_tui.py:881](../../wizard_tui.py)).
Fechar uma aba não avisa nada, então esse encerramento tem que ter um dono explícito
no servidor.

### Arquivos

| Arquivo | Ação |
|---|---|
| `web/app.py`, `web/routes/`, `web/templates/` | 🆕 |
| `requirements.txt` | + fastapi, uvicorn, jinja2 |

### Critério de aceite

- `uvicorn web.app:app` sobe e serve a primeira tela
- Derrubar o servidor com uma partida ativa encerra o watcher
- Tentar iniciar uma segunda partida é recusado com mensagem, sem tocar no RCON

---

## F3.2 — Telas de setup

### Objetivo

Perfil, formato, mapas e veto no browser, com paridade com as telas do Textual.

### Comportamento

| Tela | Conteúdo |
|---|---|
| **Perfil** | Nick + SteamID64, salvos localmente; nas visitas seguintes o app pula direto pro formato. Sem Steam OpenID (D8) |
| **Formato** | MD1/MD3/MD5 + tamanho de time, validado contra o `CS2_MAXPLAYERS` do compose ([start_match.py:105](../../start_match.py)) |
| **Mapas** | Escolha direta **ou** veto (D9). A escolha direta é o padrão |
| **Veto** | Sequência alternada, histórico visível, adversário resolvendo sozinho. Peso por time é M7 — aqui segue aleatório |
| **Lados** | Lado por mapa escolhido |
| **Resumo** | Tudo antes de iniciar |

Voltar em qualquer passo usa o `back` da `WizardSession`, incluindo o caso que pula
a tela de veto.

### Critério de aceite

- MD1, MD3 e MD5 montáveis pelos dois caminhos de mapa
- Voltar funciona em todos os passos e não corrompe o estado
- Tamanho de time acima do suportado é recusado antes de subir o container

---

## F3.3 — Tela de partida

### Objetivo

Substituir a `LaunchScreen` do Textual: iniciar o servidor, mostrar o log ao vivo,
e confirmar o ready.

### Comportamento

- Botão **Iniciar servidor** dispara o `launch` numa thread
- Log do launcher e do watcher transmitido por **SSE**, consumindo o sink da F2.2
- Quando o núcleo chama `confirm_ready`, a tela mostra o botão
  **Tudo pronto, iniciar partida**; clicar libera a thread
- Botão **Forçar início / rebalancear bots** continua presente (auto-retry é o M5)
- Instrução de conexão visível, como no `HINT` de hoje ([wizard_tui.py:631](../../wizard_tui.py))

### Critério de aceite

- Log aparece em tempo real, sem recarregar a página
- O fluxo completo funciona: iniciar → conectar pelo CS2 → `.ready` → confirmar → jogar
- Fechar e reabrir a aba durante o boot não interrompe nada

---

## F3.4 — Reidratação

### Objetivo

Reabrir o browser durante uma partida e voltar exatamente pro estado em que estava.

### Comportamento

- Ao abrir qualquer página, o app checa se existe partida ativa e redireciona
  pra tela de partida
- O log é reidratado a partir de um buffer no servidor (últimas N linhas), e o SSE
  continua dali
- Se o botão de ready estava pendente, ele reaparece pendente
- Sem heartbeat: fechar a aba **não** encerra nada (D14)

### Critério de aceite

- Fechar a aba no meio de um MD3 e reabrir mostra a partida em andamento, com
  histórico de log
- Recarregar a página com o botão de ready pendente mantém o botão pendente
- O estado sobrevive a um F5 em qualquer tela do wizard, não só na de partida
