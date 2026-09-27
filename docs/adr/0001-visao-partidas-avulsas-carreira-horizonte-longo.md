---
tipo: adr
status: proposto
aliases: [ADR-0001]
fontes:
  - "transcript eb5adec0 @ 2026-09-26T22:10:19Z"
  - "transcript de92b218 @ 2026-09-03T01:19:04Z"
  - "transcript 7010f738 @ 2026-09-19T13:09:27Z"
  - "transcript 7010f738 @ 2026-09-19T13:16:46Z"
  - "transcript 7010f738 @ 2026-09-19T13:33:09Z"
  - "docs/SPEC.md:19-41"
  - "docs/SPEC.md:167-175"
  - "docs/SPEC.md:333-353"
  - "docker/SPIKE.md:198-203"
  - "wizard_core.py:73-93"
  - "wizard_core.py:411-438"
  - "start_match.py:855-890"
  - "roster.py:143"
  - "roster.py:154-165"
  - "start_match.py:883"
  - "roster.py:219-236"
  - "stats.py:567"
  - "parser.py:65-87"
  - "parser.py:311-315"
  - "backup:temp-artifacts/eb5adec0/audit/ (critic.json gaps[0]; notion.json; docs.json vision_digest; tx_inicio_31_08_05_09.json e tx_web_wizard_prototipos_19_09.json, vision)"
  - "backup:temp-artifacts/eb5adec0/plan/all.json (cards S2.2, S5.3 e S5.4)"
atualizado: 2026-09-27
---

# ADR-0001: Visão: partidas avulsas agora, modo carreira no horizonte longo

## Contexto

Três visões conviviam sem ninguém reconciliar (critic, lacuna 1):

1. **"CS2 Career Mode Offline"** (03/09): campeonatos estilo Major, jogados sozinho e offline contra bots, em três camadas. A visão nunca virou documento. Sobrou só em `docker/SPIKE.md:198-203` (`career.db`) e nos comentários "Camada 1". Nada foi implementado: `git grep -iE "bracket|tournament|career" -- '*.py'` não acha nada.
2. **"Faceit/GamersClub offline contra pros"** (19/09). Na resposta Q1=C, ele escolheu a opção demo/pitch da pergunta: um projeto que existe para provar a tese e vira produto se pegar.
3. **SPEC §1–§2** (20/09): partida avulsa contra times pro. "Não é comercial" (`SPEC.md:41`), e D1 diz que o "mercado é hipótese futura".

Ainda em 19/09, o Victor escreveu: "Minha ideia principal é fazer um jogo maneiro pra mim (e pra um ou outro que achar o repo)". Em 26/09, perguntado sobre a visão, ele escolheu "Avulsas agora, carreira depois". Sobre publicar o repo, respondeu: "não tem uso comercial".

## Decisão

- **Curto e médio prazo: partidas avulsas contra times pro**, como na SPEC §1. É o que o programa de sprints de 26/09 entrega. As D1–D22 seguem valendo até o K1.6 dar o status real de cada uma.
- **Horizonte longo: "CS2 Career Mode Offline"**, fora do backlog. Status de cada camada:

| Camada | O que é | Status |
|---|---|---|
| Partidas avulsas (SPEC) | MD1/MD3/MD5 contra pros, estatísticas, head-to-head e marcos | **vigente**: é o produto |
| 1 · Orquestração de campeonato | tabelas `teams`, `tournaments` e `bracket_matches`; o match_config da rodada seguinte sai do resultado anterior; elenco de adversários | **horizonte longo**: fora do backlog, com os pontos de extensão abaixo preservados |
| 2 · Cara de campeonato | tela de chave (grupos até a final), força do adversário por fase, overlay e narrativa de temporada | **horizonte longo**, depois da 1. A força por fase conflita com a D12 (sem dial) e a D21 (marcos, sem nível): a discussão reabre quando a Camada 1 entrar |
| 3 · Bots com personalidade/IA | comportamento por time; IA de verdade | **direção, não backlog**, nas palavras do Victor em 03/09. Hoje a personalidade vem dos perfis nomeados do VPK (D2) e dos plugins da [trilha de bots](0005-trilha-de-bots-uma-variavel-por-vez.md). O "CS2 AI Enemy Coach" do Drive é outro projeto |

- **Uso pessoal, sem fim comercial.** O cs2-tracker é "um jogo maneiro" para o Victor. O repo é público para quem achar ([ADR-0003](0003-repo-publico.md)), mas não tem uso comercial. A ideia de demo/pitch que pode virar produto deixa de guiar decisões: nenhuma escolha de arquitetura, dependência ou escopo se justifica por mercado. Se um dia virar produto, isso será um ADR novo, que substitui este, e a troca dos nomes reais por genéricos é trocar o `data/rosters.json` (SPEC §9, D3).

## Pontos de extensão que a arquitetura preserva

1. **MatchSetup é dado, sem UI.** `MatchSetup` (`wizard_core.py:73-93`) → `build_match_config` (`wizard_core.py:411-438`) é o caminho até o match_config. A Camada 1 geraria um MatchSetup por rodada. Checagem: `wizard_core.py` não importa Textual, FastAPI nem Jinja, e o S5.3 mantém uma validação só.
2. **Partida sobe sem tela.** O `start_match.py` roda pela linha de comando (`--map`, `--side`, `--mine`, `--enemy`: `start_match.py:855-890`). Checagem: G4 (integração TUI → `run_match`) e o CLI. O critério do S5.3 só garante `--map` e `--side`. Manter também `--mine` e `--enemy` no S5.3 e no S5.4 é pedido deste ADR, não do critério daqueles cards.
3. **Roster é dado.** Time, jogadores, logo e veto ficam em `data/rosters.json` e são lidos por `roster.load_rosters` (`roster.py:219-236`). A tabela `teams` da Camada 1 nasceria daí. Checagem: nenhum nome de time ou pro fixo na lógica ou nos dados de `.py` fora de `tests/`. Texto de ajuda, comentário e docstring não contam (ex.: `start_match.py:883`, `roster.py:143`, `stats.py:567`). Exceção conhecida: o `TEAM_LOGO_FILES` (`roster.py:154-165`), que mapeia em código o id do time para o arquivo de imagem do logo. Ele sai quando esse arquivo passar para o `data/rosters.json`, e nenhuma exceção nova entra.
4. **Série e mapa identificáveis.** Cada mapa vira uma linha em `matches`, com `demo_name` único `events_<matchid>_map<N>` e `series_num_maps` (`parser.py:65-87`, `parser.py:311-315`). Um `bracket_match` apontaria para a série pelo matchid. Checagem: colisão de nome nunca descarta partida (P1.1a), e restaurar um snapshot não volta o contador de matchid da MatchZy (B0.9).
5. **Schema só cresce por adição.** As migrações passam a ser só aditivas, com `user_version`, no S2.2. Hoje não há `user_version` no código. Então `teams`, `tournaments` e `bracket_matches` entrariam como tabelas novas, sem reescrever `matches`. Checagem: o teste "tag anterior roda contra banco migrado" (S2).
6. **Comportamento de bot fica fora do app.** A personalidade vem do perfil do VPK e dos plugins do servidor, e o app só escolhe perfis. Uma IA própria (Camada 3) entraria como mais um plugin, sem mexer em captura ou ingestão. Checagem: a captura (Cs2TrackerEvents) não depende de plugin de bot, e a B1 religa um por vez sem tocar nela.

## Alternativas consideradas

- **Carreira agora, com a Camada 1 no programa**: não. A partida avulsa ainda não inicia pelo browser (Etapa 6), e os bots estão degradados desde 23/09. Campeonato em cima disso multiplica o que quebra.
- **Descartar a carreira**: o Victor escolheu "carreira depois". Descartar também deixaria a poda livre para cortar o que a carreira vai precisar.
- **Demo/pitch comercial**: "não tem uso comercial", e nomes e marcas reais só se sustentam no uso pessoal (SPEC §9).

## Consequências

- O programa de 26/09 (B0 a S8) não tem card de campeonato. Ideia de carreira vai para `agents/ideias.md` (H1.9), não para o board.
- A poda (S1) e a refatoração (S2 a S7) não removem os seis pontos acima, e cada um tem sua checagem. Card que quebre um deles precisa de um ADR que substitua este. O `nao-apagar.md` (S1.1) cita este ADR.
- A SPEC §1–§2 continua valendo para o curto prazo, e o K1.6 põe nela o link para este ADR, sem reescrever a visão. O "Não é comercial" da SPEC §2 e a D1 ficam reconciliados: o mercado deixa de ser hipótese que orienta decisão.
- "Camada 1/2" tem dois sentidos: produto, aqui, e proteção de round, no `start_match.py`. O glossário (K1.5) separa os dois.

## Status

Proposto em 2026-09-26, a partir da escolha do Victor ("Avulsas agora, carreira depois"). Os seis pontos de extensão e as checagens foram escritos por agente. **Pendente:** a leitura dele (critério do K1.2, ~20 min). O que ele mudar nessa leitura entra aqui, e só então o status passa a `aceito`, com a data.

## Fontes

- Transcripts `de92b218` (as três camadas), `7010f738` (Q1=C e "jogo maneiro pra mim") e `eb5adec0` (a escolha de 26/09). Auditoria: critic (lacuna 1), notion (a visão só existia em transcript), docs, tx_inicio e tx_web_wizard.
- Código: os `caminho:linha` do frontmatter sustentam os pontos de extensão 1 a 4.
