---
tipo: armadilha
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 36 e 47-52)"
  - "docker/SPIKE.md:150-196"
  - "docker-compose.yml:199-208"
  - "docs/historico/2026-09-26-handoff-plugins-de-bot.md:101-104"
  - "docs/runbooks/versoes-conhecidas.md:169 (json-file com entradas corrompidas depois das paradas de 05/10 e 06/10)"
  - "docs/runbooks/b1.3-cssharp-1.0.375.md:733-737 (o compose não tem restart policy)"
  - "start_match.py:845-849 (a TUI sobe o container parado ao iniciar a partida)"
  - "tools/jogavel.py:1573-1580 (reconstrução do log pelo fim, B0.7h)"
  - "backup:../2026-10-01/g7-vpk-low-2000922/NOTA.txt (linhas 3-5: exit 0x40010004 na suspensão de 30/09 23:56 em -03)"
  - "backup:../2026-10-15/coleta-g7-p1.1b/docker-logs-reconstruido.LEIAME.txt (--since vazio, reconstrução desde o StartedAt 2026-10-16T00:30:01Z, 1 entrada ilegível na fronteira)"
  - "backup:../2026-10-15/coleta-g7-p1.1b/docker-logs-reconstruido.txt (linhas 1-188: última entrada antes da parada de 15/10, SteamCMD e Success)"
  - "docs/runbooks/voltar-ao-jogavel.md:202-207 (o --tail N lê do fim e para calado numa entrada corrompida)"
  - "docs/runbooks/smoke-partida-de-bots.md:64-65 (marca e desde, com --tail 5000)"
  - "docs/runbooks/versoes-conhecidas.md:80 (coleta do P1.1c: docker-logs.txt vazio, reconstrução desde 2026-10-18T03:02:10Z)"
  - "docs/runbooks/versoes-conhecidas.md:177 (json-file corrompido pela parada noturna)"
  - "tools/jogavel.py:1589-1592 (o --since para em silêncio na entrada corrompida, B0.7h)"
  - "backup:../2026-10-19/g7-p1.3-p1.4-copia/logs/janelas/2026-10-19.md (linha 15: --tail acima de ~7410 linhas para na entrada de 2026-10-18T03:02Z; registro de 20/10 em logs/janelas/2026-10-20.md, linha 17, --since vazio depois do restart, só no checkout principal)"
atualizado: 2026-10-20
---

# Armadilhas do Windows e do Docker Desktop

Itens 36 e 47 a 52 da lista de 54 da auditoria de 26/09 ([índice](README.md)), e dois que
vieram depois dela, a parada noturna do Docker Desktop e o `docker logs --since` vazio: o host é Windows 11 com Docker Desktop sobre
WSL2, e o shell dos agentes é o Git Bash.

### 36. Não-ASCII pela RCON e pelo pipe do Windows
- **Sintoma:** o `say` no chat do jogo sai quebrado; arquivo escrito no container por `docker exec` chega com acento trocado.
- **Causa:** o chat do CS2 engasga com não-ASCII, e o `text=True` do `subprocess` no Windows usa o cp1252.
- **Contorno:** mensagens sem acento e conteúdo ASCII puro no que atravessa o pipe.
- **Fonte:** `start_match.py:347-348` · `start_match.py:371-374` (auditoria: start_match.py:244-245 e :268-271)

### 47. SteamCMD falha perto de 99 % no Docker Desktop
- **Sintoma:** `Error! App '730' state is 0x602 after update job`, e o download recomeça do zero (4 vezes seguidas).
- **Causa:** download do jogo do zero dentro do Docker Desktop/WSL2 é frágil neste ambiente.
- **Contorno:** semear o volume a partir de uma instalação nativa (`C:/cs2server`); o SteamCMD reconhece e baixa só o delta. O `C:/cs2server` é a única semente: não se toca ([reconstruir volume](../runbooks/reconstruir-volume.md)).
- **Fonte:** `docker/SPIKE.md:161-167`

### 48. GSLT preso ou vencido
- **Sintoma:** o cliente leva `5003: Timed out attempting to connect`, com RCON e `A2S_INFO` funcionando; o log repete `We're not logged into Steam`.
- **Causa:** token expirado ou preso numa sessão anterior que não desconectou (vários stop ou crash seguidos).
- **Contorno:** gerar um GSLT novo e recriar o container (papel servidor, em janela). Boot saudável mostra `Connection to Steam servers successful.`
- **Fonte:** `docker/SPIKE.md:168-174` · `docker/SPIKE.md:194-196`

### 49. Docker Desktop travado por socket órfão
- **Sintoma:** "unexpected error" na inicialização, citando um socket AF_UNIX que não se apaga (Win32 1920).
- **Causa:** reparse point de socket que o Windows não processa sem o backend (docker/desktop-feedback#460).
- **Contorno:** renomear a pasta pai inteira (`%LOCALAPPDATA%\Docker\run`) e deixar o Docker Desktop recriar.
- **Fonte:** `docker/SPIKE.md:175-182`

### 50. Bind mount de arquivo único é por inode
- **Sintoma:** o container segue vendo a versão antiga de um arquivo montado depois que o host o reescreve.
- **Causa:** o bind de arquivo prende o inode; reescrita por rename cria outro.
- **Contorno:** o `live_override.cfg` vai por `docker exec`, sem bind. Arquivo montado só muda com o container recriado, em janela.
- **Fonte:** `start_match.py:342-345` (auditoria: start_match.py:239-241)

### 51. O nome do volume vinha da pasta do projeto
- **Sintoma:** compose rodado de uma worktree criava um volume novo e vazio de 40 a 60 GB.
- **Causa:** sem `name:` no projeto, o volume era `<pasta>_cs2-data`.
- **Contorno:** desde o B0.8 o `cs2-data` é external com nome fixo; agora o risco inverteu: de outra pasta, o compose monta o volume VIVO. Compose só do checkout principal, pelo papel servidor.
- **Fonte:** `docker-compose.yml:199-208` · `AGENTS.md:35` (auditoria: sem linha, "compose sem name:")

### 52. Git Bash reescreve caminho de container
- **Sintoma:** o build do plugin pelo `.sh` cria um diretório `Cs2TrackerEvents;C` (relato da auditoria, sem fonte no repo); `-C /d` vira `D:/` e `/in/...` vira `C:/Program Files/Git/in/...`.
- **Causa:** a conversão automática de caminhos POSIX do MSYS.
- **Contorno:** `export MSYS_NO_PATHCONV=1` e caminhos `C:/...`; o `.ps1` de build funciona sem isso.
- **Fonte:** `docs/historico/2026-09-26-handoff-plugins-de-bot.md:101-104` · `docs/runbooks/b1.3-cssharp-1.0.375.md:228-233` (auditoria: sem linha)

## Depois da auditoria

Itens que apareceram depois de 26/09. Não têm número: a numeração é a dos 54 da auditoria ([índice](README.md)).

### Docker Desktop para de madrugada (exit 0x40010004)
- **Sintoma:** o container `cs2-spike` amanhece parado, sem nenhuma linha de desligamento no log. Registrado em 29/09, 01/10, 05/10, 06/10, 14/10 e 15/10 (na de 15/10, o backend saiu às 04:07:55Z). O efeito aparece em dois lugares:
  - no json-file de logs: a parada é brusca, e o segmento dela fica com entrada ilegível na fronteira, onde o `docker logs` lendo para a frente para em silêncio. As de 05/10 e 06/10 esvaziaram o `docker-logs.txt` da coleta de 12/10; na de 15/10, o `docker logs --since <StartedAt>` da coleta da partida 84 voltou vazio, e o log só saiu reconstruído pelo fim, desde o `StartedAt`, com 1 entrada ilegível na fronteira;
  - na TUI: nada avisa a parada. O container só volta quando a TUI inicia a partida e roda o `docker compose up -d`, e o problema aparece na hora de jogar: esse boot roda o SteamCMD, que pode trazer build nova sem janela (a 2000933, em 15/10) e esticar a espera (~2 min 48 s do `StartedAt` ao `Pronto`).
- **Causa:** o backend do Docker Desktop sai com exit `0x40010004`, e o container cai junto; o compose não tem restart policy, e o container não sobe sozinho quando o Docker Desktop volta. O gatilho só foi lido na de 01/10 (30/09 23:56 em -03, junto de uma suspensão do PC); nas outras não foi investigado: fica como pendência.
- **Contorno:** na coleta, o `jogavel.py coletar` reconstrói o log pelo fim (`docker logs -t --tail N`, B0.7h), e o G7 se julga pelo `docker-logs-reconstruido.txt` citando o LEIAME. Antes de jogar, conte com o boot inteiro do SteamCMD, e confira a build no `GC Connection established for server version` da coleta ([épocas de build](../runbooks/versoes-conhecidas.md#épocas-de-build)).
- **Fonte:** `docs/runbooks/versoes-conhecidas.md:169` · `docs/runbooks/b1.3-cssharp-1.0.375.md:733-737` · `start_match.py:845-849` · `tools/jogavel.py:1573-1580` · `backup:../2026-10-01/g7-vpk-low-2000922/NOTA.txt` (linhas 3-5: a de 01/10) · `backup:../2026-10-15/coleta-g7-p1.1b/docker-logs-reconstruido.LEIAME.txt` (a de 15/10) · `backup:../2026-10-15/coleta-g7-p1.1b/docker-logs-reconstruido.txt` (linhas 1-2: a última entrada antes da parada e a primeira do boot pela TUI) (as datas de 29/09, 05/10, 06/10 e 14/10 e a hora de 15/10: Histórico do card 80,7 no board, K1.14)

### `docker logs --since` volta vazio no `cs2-spike` (desde 18/10)
- **Sintoma:** o `docker logs --since <carimbo>` do container sai vazio, com código 0, mesmo com o jogo escrevendo no log; um ajudante que espera uma linha por ele dá `FALTA` com a troca boa. Visto nas três coletas de 19/10 (`docker-logs.txt` vazio, log reconstruído desde 2026-10-18T03:02:10Z) e na janela T2 de 20/10, já depois de um `docker restart`. Um `docker logs --tail N` com N grande demais também falha calado: na janela T2 de 19/10, acima de ~7410 linhas ele cruzava a entrada corrompida e parava nela.
- **Causa:** o json-file do container, que vem do recreate de 17/10, tem uma entrada corrompida logo depois de 2026-10-18T03:02Z, na fronteira de uma parada do container (o registro da `jogavel-2026-10-19` a atribui à parada noturna, item acima). O `docker logs` lido para a frente, sem `--tail` ou com `--since`, para em silêncio na primeira entrada corrompida, antes de chegar ao carimbo pedido. O `--tail N` conta N linhas do fim e lê para a frente dali: se o N cai antes da entrada corrompida, a saída é o trecho antigo até ela, ou nada. O `docker restart` não descarta o json-file; só o recreate, que é infra e só roda em janela.
- **Contorno:** ler pelo fim, com um N que não chegue à entrada corrompida: os ajudantes `marca`, `desde` e `esperar_padrao` do [smoke só de bots](../runbooks/smoke-partida-de-bots.md#pré-condições) (`--tail 5000`, filtrando pelo carimbo da marca), e a coleta pelo `jogavel.py coletar`, que reconstrói o log pelo fim sozinha (B0.7h). Confira que a última linha da saída é recente: ela diz de que trecho o `--tail` leu. Não recrie o container para limpar o log.
- **Fonte:** `docs/runbooks/voltar-ao-jogavel.md:202-207` · `docs/runbooks/smoke-partida-de-bots.md:64-65` · `docs/runbooks/smoke-partida-de-bots.md:167-170` · `tools/jogavel.py:1589-1592` · `docs/runbooks/versoes-conhecidas.md:80` (coleta do P1.1c: docker-logs.txt vazio e reconstrução desde 18/10 03:02:10Z) · `docs/runbooks/versoes-conhecidas.md:177` (json-file corrompido pela parada noturna) · `backup:../2026-10-19/g7-p1.3-p1.4-copia/logs/janelas/2026-10-19.md` (linha 15: o --tail acima de ~7410 linhas para na entrada de 18/10 03:02Z; os ajudantes usam --tail 5000) (a de 20/10, depois do restart: registro logs/janelas/2026-10-20.md, linha 17, só no checkout principal)
