---
tipo: armadilha
status: vigente
fontes:
  - "backup:temp-artifacts/eb5adec0/audit/infra.json (findings[13], itens 36 e 47-52)"
  - "docker/SPIKE.md:150-196"
  - "docker-compose.yml:196-205"
  - "docs/historico/2026-09-26-handoff-plugins-de-bot.md:101-104"
atualizado: 2026-10-13
---

# Armadilhas do Windows e do Docker Desktop

Itens 36 e 47 a 52 da lista de 54 da auditoria de 26/09 ([índice](README.md)): o host é
Windows 11 com Docker Desktop sobre WSL2, e o shell dos agentes é o Git Bash.

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
- **Fonte:** `docker-compose.yml:196-205` · `AGENTS.md:35` (auditoria: sem linha, "compose sem name:")

### 52. Git Bash reescreve caminho de container
- **Sintoma:** o build do plugin pelo `.sh` cria um diretório `Cs2TrackerEvents;C`; `-C /d` vira `D:/` e `/in/...` vira `C:/Program Files/Git/in/...`.
- **Causa:** a conversão automática de caminhos POSIX do MSYS.
- **Contorno:** `export MSYS_NO_PATHCONV=1` e caminhos `C:/...`; o `.ps1` de build funciona sem isso.
- **Fonte:** `docs/historico/2026-09-26-handoff-plugins-de-bot.md:101-104` · `docs/runbooks/b1.3-cssharp-1.0.375.md:228-233` (auditoria: sem linha)
