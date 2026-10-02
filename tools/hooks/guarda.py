#!/usr/bin/env python3
"""
Hook de guarda do cs2-tracker (card B0.5). Roda antes de todo Bash,
PowerShell, Edit, Write, MultiEdit e NotebookEdit do Claude Code (PreToolUse,
registrado em .claude/settings.json) e barra o que quebra o jogo do Victor
ou vaza dado pessoal no repositório público. As regras deny/ask do settings
continuam valendo; o hook pega o que casamento de prefixo não pega (comando
encadeado, `cd` antes, caminho absoluto, shell dentro de shell).

Protocolo (code.claude.com/docs/en/hooks): lê o evento JSON da entrada
padrão e sai com 0 (segue o fluxo normal de permissão) ou 2 (bloqueia; o
stderr, com o motivo e a alternativa, volta pro agente).

Bloqueia:
  - docker compose / docker-compose com diretório de projeto, -f ou
    --project-directory fora do checkout principal (inclusive de uma
    worktree de agente) ou com projeto (-p, COMPOSE_PROJECT_NAME) que não
    seja cs2-tracker: sem `name:`, o compose cria projeto e volume vazios;
  - compose run e compose down (com ou sem -v/--volumes);
  - compose config sem -q (e afins) e docker inspect sem --format: imprimem
    os valores do .env na conversa;
  - docker volume rm/remove/prune e docker system prune;
  - git clean (qualquer forma, inclusive por alias) e git stash --all (tira
    os ignorados do disco);
  - pip install/uninstall, python -m pip, uv pip install/uninstall/sync,
    uv add/remove/sync;
  - uvicorn, http.server e afins ouvindo na 8000 (a porta do Victor),
    inclusive pela porta padrão; docker run -p 8000:...; preview_start do
    navegador do Claude com configuração do launch.json na 8000;
  - escrita em cs2_tracker.db (qualquer caminho; apagar o lixo de uma
    worktree pode), .env, data/profile.json, docker/events-live/**,
    docker/match_config.spike.json do checkout principal, C:/cs2server/** e
    o volume do Docker, por ferramenta de arquivo, redirecionamento, comando
    (rm, cp, mv, ln, tee, Set-Content...), curinga (rm -rf docker/*),
    chamada .NET ([IO.File]::Delete) ou código inline (python -c);
  - leitura com curinga que casa o cs2_tracker.db (e -wal, -shm, -journal)
    do checkout principal: origem de cp/Copy-Item/copy, cat/type/Get-Content
    e sqlite3 (card B0.5b); pasta que não se resolve falha fechado;
  - leitura pelo nome literal do cs2_tracker.db (e -wal, -shm, -journal) do
    checkout principal e do .env: cat, head, xxd, grep, type, Get-Content,
    sqlite3 (inclusive -readonly), cópia e `< arquivo` (card B0.5c); no
    PowerShell, ao lado de cmdlet que lê, copia, grava ou apaga, @(...) só
    passa como lista literal nua (@('a', "b"), cada string vira argumento do
    cmdlet); qualquer outro @( falha fechado. Linha que termina em vírgula ou
    operador continua na de baixo, e o CR sozinho é fim de linha, de
    comentário # e de here-string, como no PowerShell 5.1;
  - docker logs / compose logs quando tools/preflight.py não devolve 0 ou 4;
  - no Write/Edit, dado pessoal e segredo (tools/hooks/pii.py): segredo do
    .env em qualquer arquivo do repositório; SteamID em docs/**, tests/**,
    .cursor/**, .env.example e *.md da raiz; IPv4 nos mesmos, menos tests/
    fora de tests/fixtures/.

Variável é resolvida quando o valor está no próprio comando (PY=...; $PY,
$py = '...'; & $py, export, Set-Variable), assim como alias e função
definidos nele: as ferramentas Bash e PowerShell não guardam estado entre
chamadas, então o valor sempre está no texto. Programa que não dá pra
resolver ($X sem valor, embrulho desconhecido como setsid ou flock) ainda
tem as palavras seguintes conferidas (docker, git, pip, python, uvicorn).

Falha fechada com escopo: exceção ao analisar um comando que menciona
docker, git ou pip (palavra inteira) sai com 2. Qualquer outro erro interno
sai com 0 e um aviso (systemMessage): bug no hook não pode travar o trabalho
normal.

Limites conhecidos, que passam com 0 e ficam para o card B0.5d:
  - formas indiretas: chaves, crase, xargs, for, tar, cp -r da raiz, nome 8.3;
  - aliases fhx (Format-Hex) e ipcsv (Import-Csv);
  - NBSP e outros brancos do PowerShell (VT, FF, U+0085) no lugar do espaço;
  - cmd /c powershell -c "..." e o prefixo FileSystem:: no caminho;
  - Get-Content $('<R>/.env'), -Path:$(...) e Get-Content ('<R>' + '/.env');
  - caminho pelo pipe: '<R>/.env' | Get-Content;
  - operador colado a <#c#> no fim da linha, em modo expressão;
  - outras opções sem valor que _VALOR_NA_PROXIMA trata como com valor, da
    família de grep -T, jq -C e grep --file=;
  - falso positivo: Select-String -SimpleMatch "@(" arquivo sai 2.

Só biblioteca padrão. Sem `docker logs` no comando, fica abaixo de 150 ms.
"""
from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import sys

PRINCIPAL = "C:/Users/Victor/Projetos/cs2-tracker"
PROJETO_COMPOSE = "cs2-tracker"
PORTA_DO_VICTOR = 8000
PROFUNDIDADE_MAX = 8
TIMEOUT_PREFLIGHT_S = 45

DIALETO = {"Bash": "bash", "PowerShell": "ps"}
FERRAMENTAS_DE_ARQUIVO = ("Write", "Edit", "MultiEdit", "NotebookEdit")
# Palavra inteira: "digit", "github", "pipe" e "Pipfile" não contam.
_SENSIVEL = re.compile(r"\b(?:docker(?:-compose)?|git|pip\d*)\b", re.IGNORECASE)


class Bloqueio(Exception):
    def __init__(self, motivo: str, alternativa: str):
        super().__init__(motivo)
        self.motivo = motivo
        self.alternativa = alternativa


# ------------------------------------------------------------ caminhos

_DRIVE_MSYS = re.compile(r"^/(?:mnt/)?([a-zA-Z])(?=/|$)")
_DRIVE = re.compile(r"^[a-zA-Z]:")


def _barras(texto: str) -> str:
    """Barra normal; /c/x e /mnt/c/x (Git Bash, WSL) viram c:/x."""
    t = texto.replace("\\", "/")
    if t.startswith(("//?/", "//./")):
        t = t[4:]
    m = _DRIVE_MSYS.match(t)
    if m:
        t = m.group(1) + ":" + (t[m.end():] or "/")
    return t


def _absoluto(texto, base):
    """Caminho absoluto normalizado (maiúsculas preservadas) ou None se não
    dá pra saber: variável não expandida, relativo sem base, /tmp do Git Bash."""
    if not texto:
        return None
    t = _barras(texto.strip())
    if t == "~" or t.startswith("~/"):
        t = _barras(os.path.expanduser("~")) + t[1:]
    if "$" in t or "%" in t or t.startswith("~"):
        return None
    if _DRIVE.match(t):
        if len(t) > 2 and t[2] != "/":
            return None  # C:pasta, relativo ao drive
        t = t[:2] + "/" + t[2:].lstrip("/")
    elif t.startswith("/"):
        return None
    else:
        if not base:
            return None
        t = base.rstrip("/") + "/" + t
    t = posixpath.normpath(t)
    return t if _DRIVE.match(t) else None


def _raiz_git(caminho):
    """(raiz, é_worktree_ligada) do repositório que contém o caminho."""
    atual = caminho
    while atual:
        git = atual.rstrip("/") + "/.git"
        if os.path.isdir(git):
            return atual, False
        if os.path.isfile(git):
            return atual, True
        pai = posixpath.dirname(atual)
        if pai == atual:
            break
        atual = pai
    return None, False


class Contexto:
    """Estado da análise: diretório corrente (muda com cd), variáveis de
    ambiente vistas no comando e as dependências injetáveis nos testes."""

    def __init__(self, cwd, principal=PRINCIPAL, preflight=None, arquivo_env=None):
        self.cwd = _absoluto(cwd, None) if cwd else None
        self.principal = _absoluto(principal, None) or principal
        self.preflight = preflight or _rodar_preflight
        self.arquivo_env = arquivo_env or (self.principal + "/.env")
        self.env = {}
        # Alias e função definidos no próprio comando (nome em minúsculas).
        # Compartilhados com os filhos: sobra definição, nunca falta.
        self.apelidos = {}
        self.funcoes = {}
        self.expandindo = frozenset()  # funções já abertas nesta cadeia (recursão)
        self.profundidade = 0

    def filho(self):
        novo = Contexto.__new__(Contexto)
        novo.__dict__.update(self.__dict__)
        novo.env = dict(self.env)
        novo.profundidade = self.profundidade + 1
        if novo.profundidade > PROFUNDIDADE_MAX:
            raise RuntimeError("comando aninhado demais para analisar")
        return novo

    def no_principal(self, caminho) -> bool:
        """Dentro do checkout principal e fora de qualquer worktree ligada
        (as dos agentes moram em <principal>/.claude/worktrees/)."""
        if not caminho:
            return False
        if (caminho.lower() + "/").startswith(self.principal.lower() + "/.claude/worktrees/"):
            return False
        raiz, worktree = _raiz_git(caminho)
        return raiz is not None and not worktree and raiz.lower() == self.principal.lower()

    def protegidos(self):
        p = self.principal
        return [f"{p}/cs2_tracker.db", f"{p}/.env", f"{p}/data/profile.json",
                f"{p}/docker/events-live", f"{p}/docker/match_config.spike.json",
                "c:/cs2server"]


ALT_BANCO = ("banco em tmp_path ou fixture; dado real só numa cópia mode=ro pedida ao PM "
             "(tools/backup.py); apagar o cs2_tracker.db que a suíte cria na SUA worktree "
             "pode, pelo nome")
ALT_ENV = "use o .env.example; o .env é do Victor, e só ele edita"
ALT_PERFIL = "perfil em tmp_path nos testes"
ALT_EVENTS = "fixture anonimizada em tests/fixtures/"
ALT_CS2SERVER = "nada: C:/cs2server é a única semente de recuperação do servidor"
ALT_VOLUME = "nada: o volume cs2-tracker_cs2-data não é reproduzível"
ALT_SPIKE = ("deixe como está: é estado de runtime do start_match, que o reescreve a cada "
             "partida; git add só por caminho")
_EVENTS_LIVE = re.compile(r"(^|/)docker/events-live(/|$)")
_CURINGA = re.compile(r"[*?\[]")
_NOMES_DO_BANCO = ("cs2_tracker.db", "cs2_tracker.db-wal", "cs2_tracker.db-shm",
                   "cs2_tracker.db-journal")


def _motivo_protegido(bruto, ctx, modo="escrita"):
    """(motivo, alternativa) se `bruto` é caminho protegido, senão None.
    modo: escrita, apagar (o cs2_tracker.db fora do principal pode) ou mover."""
    if bruto.startswith("(") and bruto.endswith(")"):  # (Join-Path $PWD 'x') do PowerShell
        for caminho in _caminhos_de_expressao(bruto[1:-1], ctx):
            achado = _motivo_protegido(caminho, ctx, modo)
            if achado:
                return achado
        return None
    bruto = _expandir(bruto, ctx.env, ctx, "caminho", sistema=True)
    forma = _barras(bruto).rstrip("/")
    absoluto = _absoluto(bruto, ctx.cwd)
    chaves = [forma.lower()] + ([absoluto.lower()] if absoluto else [])
    nome = chaves[0].rsplit("/", 1)[-1]
    if nome == "cs2_tracker.db" or nome.startswith("cs2_tracker.db-"):
        lixo_local = (modo == "apagar" and absoluto is not None
                      and not ctx.no_principal(posixpath.dirname(absoluto)))
        if not lixo_local:
            return "é o banco cs2_tracker.db", ALT_BANCO
    if nome == ".env":
        return "é o .env (segredos do servidor)", ALT_ENV
    if absoluto and absoluto.lower() == f"{ctx.principal}/docker/match_config.spike.json".lower():
        return "é o docker/match_config.spike.json do checkout principal", ALT_SPIKE
    for chave in chaves:
        if chave == "data/profile.json" or chave.endswith("/data/profile.json"):
            return "é o data/profile.json (perfil do Victor)", ALT_PERFIL
        if _EVENTS_LIVE.search(chave):
            return "é o docker/events-live (captura das partidas)", ALT_EVENTS
        if chave == "c:/cs2server" or chave.startswith("c:/cs2server/"):
            return "é o C:/cs2server", ALT_CS2SERVER
        if "cs2-tracker_cs2-data" in chave or "docker-desktop-data" in chave:
            return "é o volume do Docker", ALT_VOLUME
    if modo in ("apagar", "mover") and absoluto:
        alvo = absoluto.lower().rstrip("/")
        for protegido in ctx.protegidos():
            protegido = protegido.lower()
            if protegido == alvo or protegido.startswith(alvo + "/"):
                return (f"leva junto {protegido}",
                        "apague ou mova só o que você criou, pelo nome")
    if _CURINGA.search(forma):
        return _motivo_curinga(forma, absoluto, ctx, modo)
    return None


def _segmentos_casam(padrao, alvo):
    """O padrão (lista de segmentos com curinga; ** vale qualquer número de
    segmentos) casa o caminho `alvo` inteiro?"""
    if not padrao:
        return not alvo
    if padrao[0] == "**":
        return any(_segmentos_casam(padrao[1:], alvo[k:]) for k in range(len(alvo) + 1))
    return (bool(alvo) and fnmatch.fnmatchcase(alvo[0], padrao[0])
            and _segmentos_casam(padrao[1:], alvo[1:]))


def _motivo_curinga(forma, absoluto, ctx, modo):
    """rm -rf *, docker/*, cs2_*.db: o curinga alcança algo protegido? Com a
    pasta conhecida, casa segmento a segmento com os caminhos protegidos; sem
    ela, vale o nome (banco e .env)."""
    if absoluto is None:
        nome = forma.lower().rsplit("/", 1)[-1]
        if _nome_casa_banco(nome):
            return f"o curinga {forma} casa o banco cs2_tracker.db", ALT_BANCO
        if nome.startswith(".") and fnmatch.fnmatchcase(".env", nome):
            return f"o curinga {forma} casa o .env", ALT_ENV
        return None
    padrao = absoluto.lower().split("/")
    lados = [f"{ctx.principal}/{banco}" for banco in _NOMES_DO_BANCO[1:]]
    for protegido in ctx.protegidos() + lados:
        alvo = protegido.lower().split("/")
        # Apagar ou mover uma pasta leva o que tem dentro: vale casar um ancestral.
        tamanhos = range(1, len(alvo) + 1) if modo in ("apagar", "mover") else [len(alvo)]
        if any(_segmentos_casam(padrao, alvo[:k]) for k in tamanhos):
            return (f"o curinga {forma} alcança {protegido}",
                    "apague ou mova só o que você criou, pelo nome, sem curinga")
    return None


def _nome_casa_banco(nome):
    """O curinga do nome (já em minúsculas) casa cs2_tracker.db, -wal, -shm
    ou -journal?"""
    return any(fnmatch.fnmatchcase(banco, nome) for banco in _NOMES_DO_BANCO)


ALT_LEITURA = ("banco em tmp_path ou fixture; dado real só numa cópia mode=ro pedida ao PM "
               "(tools/backup.py, card B0.6); nome ou curinga só numa pasta que não seja o "
               "checkout principal (o cs2_tracker.db da SUA worktree pode)")
ALT_ENV_LEITURA = ("use o .env.example; o .env é do Victor: não se lê, copia nem imprime "
                   "(o SRCDS_TOKEN e a senha do RCON iriam para a conversa)")


def _nome_do_arquivo(forma):
    """Último segmento em minúsculas, como o Windows o enxerga: sem ponto ou
    espaço no fim e sem fluxo alternativo (cs2_tracker.db::$DATA)."""
    nome = forma.lower().rsplit("/", 1)[-1]
    return nome.split(":", 1)[0].rstrip(". ")


def _motivo_leitura(bruto, ctx):
    """(motivo, alternativa) se um argumento de leitura (origem de
    cp/Copy-Item/copy, cat/type/Get-Content, sqlite3, head, xxd...) ou o alvo
    de um `<` lê o banco do checkout principal ou o .env, senão None.
    Curinga (card B0.5b): com a pasta conhecida, casa segmento a segmento com
    <principal>/cs2_tracker.db e os lados: *.db e * barram no checkout
    principal e passam na worktree. Nome literal (card B0.5c): o banco barra
    no checkout principal e passa na worktree; o .env barra em qualquer
    pasta, como na escrita. Pasta que não se resolve ("$RAIZ"/..., /tmp do
    Git Bash) falha fechado: vale o nome."""
    if bruto.startswith("(") and bruto.endswith(")"):  # (Join-Path $PWD 'x') do PowerShell
        for caminho in _caminhos_de_expressao(bruto[1:-1], ctx):
            achado = _motivo_leitura(caminho, ctx)
            if achado:
                return achado
        return None
    bruto = _expandir(bruto, ctx.env, ctx, "caminho", sistema=True)
    if bruto.lower().startswith("file:"):  # sqlite3 -readonly file:<banco>?mode=ro
        bruto = bruto[5:].split("?", 1)[0]
        if _DRIVE.match(bruto.lstrip("/")):
            bruto = bruto.lstrip("/")
    forma = _barras(bruto).rstrip("/")
    absoluto = _absoluto(bruto, ctx.cwd)
    if not _CURINGA.search(forma):
        return _motivo_leitura_literal(forma, absoluto, ctx)
    if absoluto is None:
        nome = forma.lower().rsplit("/", 1)[-1]
        if _nome_casa_banco(nome):
            return (f"o curinga {forma} casa o nome do banco cs2_tracker.db e a pasta não se "
                    "resolve: pode ser o checkout principal (falha fechada)", ALT_LEITURA)
        if nome.startswith(".") and fnmatch.fnmatchcase(".env", nome):
            return (f"o curinga {forma} casa o .env e a pasta não se resolve (falha fechada)",
                    ALT_ENV_LEITURA)
        return None
    padrao = absoluto.lower().split("/")
    for banco in _NOMES_DO_BANCO:
        alvo = f"{ctx.principal}/{banco}"
        if _segmentos_casam(padrao, alvo.lower().split("/")):
            return f"o curinga {forma} lê {alvo}, o banco do checkout principal", ALT_LEITURA
    if _segmentos_casam(padrao, f"{ctx.principal}/.env".lower().split("/")):
        return f"o curinga {forma} lê {ctx.principal}/.env", ALT_ENV_LEITURA
    return None


def _motivo_leitura_literal(forma, absoluto, ctx):
    nome = _nome_do_arquivo(forma)
    if nome == ".env":
        return f"{forma} é o .env (segredos do servidor)", ALT_ENV_LEITURA
    if nome in _NOMES_DO_BANCO:
        if absoluto is None:
            return (f"{forma} tem o nome do banco cs2_tracker.db e a pasta não se resolve: "
                    "pode ser o checkout principal (falha fechada)", ALT_LEITURA)
        if ctx.no_principal(posixpath.dirname(absoluto)):
            return f"{forma} é o banco cs2_tracker.db do checkout principal", ALT_LEITURA
    return None


def _caminhos_de_expressao(texto, ctx):
    """Caminhos candidatos de uma expressão (...) do PowerShell: o resultado
    do Join-Path, ou cada palavra dela."""
    palavras = _palavras(texto, "ps")
    if palavras and palavras[0].lower() == "join-path":
        nomeados, pos = _args_ps(palavras[1:])
        partes = [v for nome, v in nomeados
                  if nome in ("path", "childpath", "additionalchildpath")] + pos
        partes = [_expandir(p, ctx.env, ctx, "ps", sistema=True) for p in partes]
        if partes:
            return ["/".join([partes[0].rstrip("/\\")] + [p.strip("/\\") for p in partes[1:]])]
    return palavras


def _checar_caminho(alvo, ctx, modo, acao):
    achado = _motivo_protegido(alvo, ctx, modo)
    if achado:
        raise Bloqueio(f"{acao} em {alvo}: {achado[0]}", achado[1])


# ----------------------------------------------------------- tokenização

# Operadores do PowerShell que, no fim da linha, fazem o comando continuar na
# linha de baixo (card B0.5c). Os de comparação têm as variantes -c e -i. No
# modo argumento só a vírgula continua (o parser do 5.1 confirma); em expressão,
# qualquer um deles. Fica de fora o `..`, que no fim é `cd ..`.
_COMPARACAO_PS = ("eq", "ne", "gt", "ge", "lt", "le", "like", "notlike", "match", "notmatch",
                  "contains", "notcontains", "in", "notin", "replace", "split")
_OPERADORES_PS = (
    {f"-{p}{op}" for op in _COMPARACAO_PS for p in ("", "c", "i")}
    | {"-and", "-or", "-xor", "-not", "-band", "-bor", "-bxor", "-bnot", "-shl", "-shr",
       "-join", "-is", "-isnot", "-as", "-f"}
    | {"+", "-", "*", "/", "%", "!", "=", "+=", "-=", "*=", "/=", "%=", "??", "??="})


class _Tok:
    __slots__ = ("tipo", "texto", "aninhados")

    def __init__(self, tipo, texto="", aninhados=None):
        self.tipo = tipo  # p: palavra, s: separador, r: redirecionamento, a: só aninhados
        self.texto = texto
        self.aninhados = aninhados or []


_SEP = _Tok("s")


class _Leitor:
    """Quebra um comando (dialeto bash, ps ou cmd) em palavras já sem aspas,
    separadores (&&, ||, ;, |, &, quebra de linha, parênteses; chaves no
    PowerShell) e redirecionamentos. $(...), `...`, <(...) e @(...) viram
    listas de tokens aninhadas na palavra onde aparecem, pra serem analisadas
    também. Corpo de heredoc e de here-string é dado, não comando."""

    def __init__(self, texto, dialeto, juntar=False):
        self.t = texto
        self.n = len(texto)
        self.i = 0
        self.d = dialeto
        self.heredocs = []
        # PowerShell: linha que termina em vírgula ou operador continua na de
        # baixo. `juntar` trata essa quebra como espaço; sem ele, ela separa
        # como antes e só conta (card B0.5c).
        self.juntar = juntar
        self.continuacoes = 0
        self.aberto_no_fim = ""

    def _prox(self, k=1):
        j = self.i + k
        return self.t[j] if j < self.n else "\0"

    def _fim_da_linha(self, i):
        """Onde acaba a linha que contém i: no LF ou, no PowerShell, também no
        CR sozinho, que o 5.1 lê como fim de linha e de comentário (card B0.5c)."""
        fim = self.t.find("\n", i)
        fim = self.n if fim < 0 else fim
        cr = self.t.find("\r", i, fim) if self.d == "ps" else -1
        return fim if cr < 0 else cr

    def ler(self, fecha=False):
        toks, pal, anin = [], [], []
        tem = False
        prof = 0
        t, n, d = self.t, self.n, self.d
        cont = ""  # PS: vírgula ou operador que é o último token da linha até aqui

        def fechar():
            nonlocal pal, anin, tem, cont
            if tem:
                texto = "".join(pal)
                toks.append(_Tok("p", texto, anin))
                # Operador só se escrito cru: '-join' entre aspas é string.
                cont = texto if (d == "ps" and texto.lower() in _OPERADORES_PS
                                 and t.endswith(texto, 0, self.i)) else ""
            elif anin:
                toks.append(_Tok("a", "", anin))
                cont = ""
            pal, anin, tem = [], [], False

        def separar():
            nonlocal cont
            fechar()
            toks.append(_SEP)
            cont = ""

        while self.i < n:
            c = t[self.i]
            prox = self._prox()
            if c in " \t" or (c == "\r" and (d != "ps" or prox == "\n")):
                fechar()
                self.i += 1
            elif c in "\r\n":  # no PowerShell, CR sozinho também é fim de linha (5.1)
                if d == "ps":
                    fechar()
                    if cont:
                        self.continuacoes += 1
                        if self.juntar:  # a linha de baixo é o resto deste comando
                            self.i += 1
                            continue
                separar()
                self.i += 1
                if self.heredocs:
                    self._corpos(toks)
            elif c == "#" and not tem and d != "cmd":
                self.i = self._fim_da_linha(self.i)
            elif (d == "bash" and c == "\\") or (d == "ps" and c == "`") or (d == "cmd" and c == "^"):
                if prox == "\r" and self._prox(2) == "\n":
                    self.i += 3
                elif prox == "\n" or (prox == "\r" and d == "ps"):
                    self.i += 2
                else:
                    if prox != "\0":
                        pal.append(prox)
                    tem = True
                    self.i += 2
            elif c == "'" and d != "cmd":
                self._aspas_simples(pal)
                tem = True
            elif c == '"':
                self._aspas_duplas(pal, anin)
                tem = True
            elif c == "$" and prox == "(" and d != "cmd":
                self._substituicao(pal, anin)
                tem = True
            elif c == "@" and prox == "(" and d == "ps":
                self._substituicao(pal, anin)
                tem = True
            elif c == "@" and prox in "'\"" and d == "ps" and self._here_string(pal, anin):
                tem = True
            elif c == "$" and prox == "{" and d != "cmd":
                fim = t.find("}", self.i)
                fim = n - 1 if fim < 0 else fim
                pal.append(t[self.i:fim + 1])
                tem = True
                self.i = fim + 1
            elif c == "`" and d == "bash":
                self._crase(pal, anin)
                tem = True
            elif c in "<>" and prox == "(" and d == "bash":
                fechar()
                self.i += 2
                toks.append(_Tok("a", "", [self.ler(fecha=True)]))
            elif c == "<" and prox == "#" and d == "ps":
                fim = t.find("#>", self.i + 2)
                self.i = n if fim < 0 else fim + 2
            elif c in "<>":
                texto_pal = "".join(pal)
                if tem and (texto_pal.isdigit() or (d == "ps" and texto_pal == "*")):
                    pal, anin, tem = [], [], False  # descritor: 2>, *>
                else:
                    fechar()
                if c == "<" and d == "bash" and t.startswith("<<<", self.i):
                    toks.append(_Tok("r", "<<<"))
                    self.i += 3
                elif c == "<" and d == "bash" and prox == "<":
                    self._heredoc()
                else:
                    j = self.i + 1
                    if j < n and t[j] == c:
                        j += 1
                    if j < n and t[j] in "|&":
                        j += 1
                    toks.append(_Tok("r", t[self.i:j]))
                    self.i = j
                cont = ""
            elif c == "(" and d == "ps" and (tem or (toks and toks[-1].tipo != "s")):
                # Expressão em posição de argumento: Remove-Item (Join-Path $PWD 'x').
                # Vira uma palavra (o texto cru) com o conteúdo aninhado.
                ini = self.i
                self.i += 1
                anin.append(self.ler(fecha=True))
                pal.append(t[ini:self.i])
                tem = True
            elif c == "(":
                separar()
                prof += 1
                self.i += 1
            elif c == ")":
                self.i += 1
                if fecha and prof == 0:
                    fechar()
                    return toks
                prof = max(0, prof - 1)
                separar()
            elif c in "{}" and d == "ps":
                separar()
                self.i += 1
            elif c == ";":
                separar()
                self.i += 1
            elif c == "&":
                if prox == "&":
                    separar()
                    self.i += 2
                elif prox == ">" and d == "bash":
                    fechar()
                    op = "&>>" if t.startswith("&>>", self.i) else "&>"
                    toks.append(_Tok("r", op))
                    self.i += len(op)
                else:
                    separar()
                    self.i += 1
            elif c == "|":
                separar()
                self.i += 2 if prox in "|&" else 1
            elif c == "," and d == "ps":
                fechar()
                cont = ","
                self.i += 1
            else:
                pal.append(c)
                tem = True
                self.i += 1
        fechar()
        if cont and cont != "*":  # `ls *` é curinga; o resto pede a linha de baixo
            self.aberto_no_fim = cont
        return toks

    def _aspas_simples(self, pal):
        t, i = self.t, self.i + 1
        while True:
            fim = t.find("'", i)
            if fim < 0:
                pal.append(t[i:])
                self.i = self.n
                return
            pal.append(t[i:fim])
            if self.d == "ps" and t.startswith("''", fim):
                pal.append("'")
                i = fim + 2
                continue
            self.i = fim + 1
            return

    def _aspas_duplas(self, pal, anin):
        t, n, d = self.t, self.n, self.d
        i = self.i + 1
        while i < n:
            c = t[i]
            prox = t[i + 1] if i + 1 < n else "\0"
            if c == '"':
                if d == "ps" and prox == '"':
                    pal.append('"')
                    i += 2
                    continue
                self.i = i + 1
                return
            if d == "bash" and c == "\\" and prox in '"\\$`\n':
                if prox != "\n":
                    pal.append(prox)
                i += 2
            elif d == "ps" and c == "`" and prox != "\0":
                pal.append(prox)
                i += 2
            elif c == "$" and prox == "(" and d != "cmd":
                self.i = i
                self._substituicao(pal, anin)
                i = self.i
            elif c == "`" and d == "bash":
                self.i = i
                self._crase(pal, anin)
                i = self.i
            else:
                pal.append(c)
                i += 1
        self.i = n

    def _substituicao(self, pal, anin):
        t, ini = self.t, self.i
        if t.startswith("$((", ini):  # aritmética: não é comando
            fim = t.find("))", ini + 3)
            self.i = self.n if fim < 0 else fim + 2
        else:
            self.i = ini + 2
            anin.append(self.ler(fecha=True))
        pal.append(t[ini:self.i])

    def _crase(self, pal, anin):
        t, n = self.t, self.n
        j = self.i + 1
        while j < n and t[j] != "`":
            j += 2 if t[j] == "\\" else 1
        anin.append(_Leitor(t[self.i + 1:min(j, n)], "bash").ler())
        pal.append(t[self.i:j + 1])
        self.i = min(j + 1, n)

    def _heredoc(self):
        t, n = self.t, self.n
        i = self.i + 2
        tira_tabs = i < n and t[i] == "-"
        if tira_tabs:
            i += 1
        while i < n and t[i] in " \t":
            i += 1
        delim, citado = [], False
        while i < n and t[i] not in " \t\r\n;|&<>()":
            if t[i] in "'\"":
                fim = t.find(t[i], i + 1)
                fim = n if fim < 0 else fim
                delim.append(t[i + 1:fim])
                citado = True
                i = fim + 1
            elif t[i] == "\\":
                delim.append(t[i + 1:i + 2])
                citado = True
                i += 2
            else:
                delim.append(t[i])
                i += 1
        self.i = i
        if delim:
            self.heredocs.append(("".join(delim), tira_tabs, not citado))

    def _corpos(self, toks):
        t, n = self.t, self.n
        for delim, tira_tabs, expande in self.heredocs:
            ini = self.i
            while self.i < n:
                fim = t.find("\n", self.i)
                fim = n if fim < 0 else fim
                linha = t[self.i:fim].rstrip("\r")
                self.i = min(fim + 1, n)
                if (linha.lstrip("\t") if tira_tabs else linha) == delim:
                    break
            if expande:  # delimitador sem aspas: $(...) no corpo executa
                subs = _substituicoes(t[ini:self.i], "bash")
                if subs:
                    toks.append(_Tok("a", "", subs))
        self.heredocs = []

    def _here_string(self, pal, anin):
        t, n = self.t, self.n
        aspas = t[self.i + 1]
        fim_linha = self._fim_da_linha(self.i)  # CR sozinho também fecha a linha
        if fim_linha >= n or t[self.i + 2:fim_linha].strip():
            return False
        ini = fim_linha + (2 if t.startswith("\r\n", fim_linha) else 1)
        fim = re.compile("[\r\n]" + aspas + "@").search(t, ini - 1)
        corpo = t[ini:] if fim is None else t[ini:fim.start()]
        self.i = n if fim is None else fim.end()
        pal.append(corpo)
        if aspas == '"':
            anin.extend(_substituicoes(corpo, "ps"))
        return True


def _substituicoes(texto, dialeto):
    """Listas de tokens de cada $(...) (e `...` no bash) dentro de um texto."""
    subs, i = [], 0
    while True:
        i = texto.find("$(", i)
        if i < 0:
            break
        leitor = _Leitor(texto, dialeto)
        leitor.i = i + 2
        subs.append(leitor.ler(fecha=True))
        i = max(leitor.i, i + 2)
    if dialeto == "bash":
        for interno in re.findall(r"`([^`]*)`", texto):
            subs.append(_Leitor(interno, "bash").ler())
    return subs


def _palavras(texto, dialeto="bash"):
    return [tok.texto for tok in _Leitor(texto, dialeto).ler() if tok.tipo == "p"]


# ---------------------------------------------------------------- análise

def analisar_comando(texto, dialeto, ctx):
    _registrar_funcoes(texto, dialeto, ctx)
    if dialeto == "ps" and "::" in texto:
        _chamadas_dotnet(texto, ctx)
    leitor = _Leitor(texto, dialeto)
    toks = leitor.ler()
    if leitor.continuacoes:
        # Linha terminada em vírgula ou operador: o PowerShell junta a de baixo
        # ao comando (Remove-Item 'x',<NL>@('...')[0] apaga os dois). Analisa
        # juntas e separadas: a guarda não sabe se o operador era expressão ou
        # argumento, e cada leitura só pode somar bloqueio (card B0.5c).
        juntas = _Leitor(texto, dialeto, juntar=True)
        toks_juntos = juntas.ler()
        _fechar_se_aberto(juntas.aberto_no_fim)
        _analisar_tokens(toks_juntos, dialeto, ctx.filho())
    _fechar_se_aberto(leitor.aberto_no_fim)
    _analisar_tokens(toks, dialeto, ctx)


def _fechar_se_aberto(operador):
    if operador:
        raise Bloqueio(f"comando do PowerShell termina em {operador!r}, que pede continuação "
                       "na linha de baixo, e não há linha de baixo (falha fechada)",
                       "termine o comando sem vírgula nem operador solto no fim, ou ponha "
                       "a continuação na mesma linha")


# ------------------------------------------------ variáveis, alias e funções

_VAR = re.compile(r"\$(?:\{(?:env:)?([A-Za-z_][A-Za-z0-9_]*)\}|(?:env:)?([A-Za-z_][A-Za-z0-9_]*))",
                  re.IGNORECASE)
_SUBST_PWD = re.compile(r"\$\(\s*(?:pwd|get-location|gl)\s*\)", re.IGNORECASE)
# Automáticas do PowerShell ($_ no Where-Object...) nunca vêm do ambiente.
_AUTOMATICAS = {"_", "ARGS", "INPUT", "THIS", "PSITEM", "TRUE", "FALSE", "NULL", "MATCHES",
                "ERROR", "HOST", "LASTEXITCODE", "PSSCRIPTROOT"}
# Do ambiente do sistema, nunca: listas de pastas viram lixo quando expandidas.
_SISTEMA_NAO = {"_", "PATH", "PATHEXT", "PSMODULEPATH"}


def _expandir(palavra, env, ctx, dialeto, sistema=False):
    """$NOME, ${NOME}, $env:NOME, $PWD e $(pwd) trocados pelo valor conhecido:
    o que o comando definiu (env) e, com `sistema`, o ambiente do processo.
    Variável sem valor conhecido fica como está."""
    if "$" not in palavra or dialeto == "cmd":
        return palavra
    if ctx.cwd:
        palavra = _SUBST_PWD.sub(lambda _m: ctx.cwd, palavra)

    def troca(m):
        nome = (m.group(1) or m.group(2)).upper()
        if nome == "PWD":
            return ctx.cwd or m.group(0)
        if nome in env:
            return env[nome]
        if nome in _AUTOMATICAS:
            return m.group(0)
        if sistema and nome not in _SISTEMA_NAO:
            valor = os.environ.get(nome)
            if valor is not None:
                return valor
        return m.group(0)

    return _VAR.sub(troca, palavra)


_FUNCAO = {
    "bash": re.compile(r"(?:^|[\s;&|(])(?:function\s+([A-Za-z_][\w.:-]*)\s*(?:\(\s*\))?"
                       r"|([A-Za-z_][\w.:-]*)\s*\(\s*\))\s*\{"),
    "ps": re.compile(r"(?:^|[\s;&|({])(?:function|filter)\s+([\w.:-]+)\s*(?:\([^)]*\))?\s*\{",
                     re.IGNORECASE),
}


def _bloco(texto, ini):
    """Texto de `ini` até a chave que fecha o bloco aberto antes de `ini`."""
    prof = 1
    for j in range(ini, len(texto)):
        if texto[j] == "{":
            prof += 1
        elif texto[j] == "}":
            prof -= 1
            if prof == 0:
                return texto[ini:j]
    return texto[ini:]


def _registrar_funcoes(texto, dialeto, ctx):
    """d(){ docker "$@"; } e function d { docker @args }: guarda o corpo pra
    analisar quando `d` for chamado."""
    regex = _FUNCAO.get(dialeto)
    if regex is None or "{" not in texto:
        return
    for m in regex.finditer(texto):
        nome = next(g for g in m.groups() if g)
        ctx.funcoes[nome.lower()] = _bloco(texto, m.end())


_SIMPLES = re.compile(r"^[\w./:=@%+,-]+$")


def _citar(palavra, dialeto):
    if _SIMPLES.match(palavra):
        return palavra
    if dialeto == "ps":
        return "'" + palavra.replace("'", "''") + "'"
    return "'" + palavra.replace("'", "'\\''") + "'"


def _corpo_com_args(corpo, args, dialeto):
    """Corpo da função com "$@", $*, $1..$9, @args e $args trocados pelos argumentos."""
    citados = " ".join(_citar(a, dialeto) for a in args)
    crus = " ".join(args)
    corpo = re.sub(r'"\$\{?[@*]\}?"|@args\b', lambda _m: citados, corpo, flags=re.IGNORECASE)
    corpo = re.sub(r"\$\{?[@*]\}?|\$args\b|\$input\b", lambda _m: crus, corpo,
                   flags=re.IGNORECASE)
    return re.sub(r"\$\{?([1-9])\}?",
                  lambda m: args[int(m.group(1)) - 1] if int(m.group(1)) <= len(args) else "",
                  corpo)


_DOTNET = re.compile(r"\[(?:system\.)?io\.(file|directory|fileinfo|directoryinfo)\]\s*::\s*(\w+)"
                     r"\s*\(", re.IGNORECASE)
_SO_LEITURA_DOTNET = ("read", "exists", "get", "enumerate", "openread", "opentext")


def _chamadas_dotnet(texto, ctx):
    """[IO.File]::WriteAllText('.env', ...), [IO.File]::Delete(...) e afins."""
    for m in _DOTNET.finditer(texto):
        metodo = m.group(2).lower()
        if metodo.startswith(_SO_LEITURA_DOTNET):
            continue
        modo = ("apagar" if "delete" in metodo
                else "mover" if metodo in ("move", "replace") else "escrita")
        dentro = _bloco(texto.replace("(", "{").replace(")", "}"), m.end())
        # Caminho é o 1º argumento; em Move, Copy e Replace, o 2º também.
        quantos = 2 if metodo in ("move", "copy", "replace") else 1
        for arg in dentro.split(",")[:quantos]:
            caminho = arg.strip()
            if len(caminho) >= 2 and caminho[0] == caminho[-1] and caminho[0] in "'\"":
                caminho = caminho[1:-1]
            _checar_caminho(_expandir(caminho, ctx.env, ctx, "ps", sistema=True), ctx, modo,
                            f"[IO.{m.group(1)}]::{m.group(2)}")


def _analisar_tokens(toks, dialeto, ctx):
    segmento = []
    for tok in toks + [_SEP]:
        if tok.tipo == "s":
            if segmento:
                _analisar_segmento(segmento, dialeto, ctx)
            segmento = []
        else:
            segmento.append(tok)


_NULOS = {"/dev/null", "nul", "nul:", "$null", "/dev/stdout", "/dev/stderr"}


def _analisar_segmento(segmento, dialeto, ctx):
    palavras, redirs, pendente = [], [], None
    for tok in segmento:
        for sub in tok.aninhados:
            _analisar_tokens(sub, dialeto, ctx.filho())
        if tok.tipo == "r":
            pendente = tok.texto
        elif tok.tipo == "p":
            if pendente is not None:
                redirs.append((pendente, tok.texto))
                pendente = None
            else:
                palavras.append(tok.texto)
    for op, alvo in redirs:
        if (op in (">", ">>", ">|", "&>", "&>>") or (op == ">&" and not alvo.isdigit()
                                                      and alvo != "-")):
            if alvo.lower() not in _NULOS:
                alvo = _expandir(alvo, ctx.env, ctx, dialeto, sistema=True)
                _checar_caminho(alvo, ctx, "escrita", f"redirecionamento {op}")
        elif op == "<":  # sqlite3 x.db < cs2_tracker.db: lê o arquivo (card B0.5c)
            achado = _motivo_leitura(alvo, ctx)
            if achado:
                raise Bloqueio(f"redirecionamento < (leitura) em {alvo}: {achado[0]}", achado[1])
    if palavras:
        _analisar_palavras(palavras, dialeto, ctx)


_PALAVRAS_CHAVE = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until",
                   "!", "{", "}", "esac"}
_ATRIB = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)
_ATRIB_PS = re.compile(r"^\$(?:env:)?([A-Za-z_][A-Za-z0-9_]*)\s*(=.*)?$", re.IGNORECASE | re.DOTALL)
_EXTENSOES = (".exe", ".cmd", ".bat", ".com", ".ps1")
_RE_PYTHON = re.compile(r"^(python(\d+(\.\d+)*)?w?|pyw?)$")
_RE_PIP = re.compile(r"^pip(\d+(\.\d+)*)?$")
_DINAMICOS = ("docker-compose", "docker", "git", "pip", "uvicorn", "python")
# Programas que a rede de palavras procura depois de um programa desconhecido.
_VIGIADOS = {"docker", "docker-compose", "com.docker.cli", "git", "pip", "python", "uvicorn"}


def _programa(palavra):
    nome = palavra.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
    for ext in _EXTENSOES:
        if nome.endswith(ext):
            return nome[:-len(ext)]
    return nome


def _normalizar(prog):
    if _RE_PYTHON.match(prog):
        return "python"
    if _RE_PIP.match(prog):
        return "pip"
    return prog


def _adivinhar(args):
    """Programa provável quando o nome não se resolve ($X sem valor): pelo
    primeiro argumento. Sobra bloqueio, nunca falta."""
    primeiro = args[0].lower() if args else ""
    if primeiro in ("compose", "volume", "system", "logs", "inspect", "container"):
        return "docker"
    if primeiro in ("clean", "stash"):
        return "git"
    if primeiro in ("install", "uninstall"):
        return "pip"
    if primeiro == "-m" or primeiro.startswith("-c"):
        return "python"
    return None


def _analisar_palavras(palavras, dialeto, ctx, env_local=None, expandido=False):
    env = dict(ctx.env)
    env.update(env_local or {})
    i, atrib = 0, {}
    while i < len(palavras):
        w = palavras[i]
        if w in _PALAVRAS_CHAVE:
            i += 1
            continue
        m = _ATRIB.match(w) if dialeto != "ps" else None
        if m:
            atrib[m.group(1).upper()] = _expandir(m.group(2), {**env, **atrib}, ctx, dialeto,
                                                  sistema=True)
            i += 1
            continue
        break
    if i == len(palavras):
        ctx.env.update(atrib)  # VAR=x solto vale pro resto do comando
        return
    env.update(atrib)
    palavras = palavras[i:]
    bruto, args = palavras[0], palavras[1:]
    if dialeto == "ps" and bruto.startswith("$"):
        m = _ATRIB_PS.match(bruto)
        if m and (m.group(2) or (args and args[0].startswith("="))):
            direita = ((m.group(2) or "")[1:].strip().split() if m.group(2) else []) + args
            if direita and direita[0].startswith("="):
                direita[0] = direita[0][1:]
            direita = [w for w in direita if w]
            # $env:X = ... e $x = '<literal>': o valor fica pro `& $x` seguinte.
            if bruto.lower().startswith("$env:") or len(direita) == 1:
                ctx.env[m.group(1).upper()] = " ".join(
                    _expandir(w, env, ctx, dialeto, sistema=True) for w in direita)
            if direita:  # $x = docker ... executa o lado direito
                _analisar_palavras(direita, dialeto, ctx)
            return
    chave = bruto.lower()
    if not expandido and chave in ctx.apelidos:
        novas = _palavras(ctx.apelidos[chave], "ps" if dialeto == "ps" else "bash")
        _analisar_palavras(novas + args, dialeto, ctx.filho(), env, expandido=True)
        return
    if chave in ctx.funcoes and chave not in ctx.expandindo:
        filho = ctx.filho()
        # git(){ command git "$@"; }: dentro do corpo, `git` é o programa de novo.
        filho.expandindo = ctx.expandindo | {chave}
        analisar_comando(_corpo_com_args(ctx.funcoes[chave], args, dialeto), dialeto, filho)
        return
    brutos = args
    args = [_expandir(a, env, ctx, dialeto) for a in args]
    if "$" in bruto:
        valor = _expandir(bruto, env, ctx, dialeto, sistema=True)
        # DC='docker compose'; $DC down: sem aspas, o bash quebra o valor em palavras.
        if valor != bruto and not expandido and len(valor.split()) > 1:
            _analisar_palavras(valor.split() + args, dialeto, ctx.filho(), env, expandido=True)
        bruto = valor.strip()
    prog = _programa(bruto)
    desconhecido = ("$" in bruto or "`" in bruto) and prog not in _TRATADORES
    if desconhecido:
        prog = next((k for k in _DINAMICOS if k in bruto.lower()), None) or _adivinhar(args) \
            or prog
    prog = _normalizar(prog)
    tratador = _TRATADORES.get(prog)
    if tratador:
        tratador(prog, args, dialeto, ctx, env)
    if dialeto == "ps" and (prog in _LEITORES or prog in _TODOS_ESCRITORES):
        args = _abrir_listas_ps(prog, brutos, args)
    if prog in _TODOS_ESCRITORES:  # perl tem os dois: -e e -i
        for alvo, modo in _alvos_de_escrita(prog, args):
            _checar_caminho(alvo, ctx, modo, prog)
    if prog in _LEITORES:
        _checar_leitura(prog, args, ctx)
    if prog not in _SEM_PORTA:
        _porta_generica(prog, args)
    if (tratador is None or desconhecido) and prog not in _SO_TEXTO:
        _rede_de_palavras(args, dialeto, ctx, env)


def _rede_de_palavras(args, dialeto, ctx, env):
    """setsid docker ..., flock x git clean, $X -m pip install: programa
    desconhecido na frente não esconde docker, git, pip, python ou uvicorn
    nas palavras seguintes."""
    for k, palavra in enumerate(args):
        prog = _normalizar(_programa(palavra))
        if prog in _VIGIADOS:
            _TRATADORES[prog](prog, args[k + 1:], dialeto, ctx, env)


# ------------------------------------------------------------- opções

def _primeiro_nao_opcao(args, com_valor=()):
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return i + 1
        if not a.startswith("-") or a == "-":
            return i
        i += 2 if ("=" not in a and a in com_valor) else 1
    return i


def _valores_opcao(args, *nomes):
    """Valores de `--nome v`, `--nome=v` e `-xV` (nome curto de 1 letra)."""
    valores = []
    for i, a in enumerate(args):
        for nome in nomes:
            if a == nome and i + 1 < len(args):
                valores.append(args[i + 1])
            elif a.startswith(nome + "="):
                valores.append(a[len(nome) + 1:])
            elif len(nome) == 2 and nome[0] == "-" and a.startswith(nome) and len(a) > 2 \
                    and not a.startswith("--"):
                valores.append(a[2:])
    return valores


_PS_SWITCHES = {"recurse", "force", "append", "nonewline", "noclobber", "passthru", "whatif",
                "confirm", "container", "asjob", "wait", "nonewwindow", "usetransaction",
                "followsymlink", "r", "f", "rf", "fr", "v", "i", "p", "a", "n"}
_PS_NAO_CAMINHO = {"value", "encoding", "itemtype", "type", "filter", "include", "exclude",
                   "stream", "delimiter", "credential", "width", "inputobject", "erroraction",
                   "warningaction", "informationaction", "errorvariable", "outvariable",
                   "outbuffer", "pipelinevariable", "verb", "windowstyle", "argumentlist",
                   "depth", "s", "m", "mode", "e", "suffix"}


def _args_ps(args):
    """([(nome, valor)], posicionais) no estilo PowerShell (-Nome valor,
    -Nome:valor), que também serve pro GNU (--nome=valor, -x)."""
    nomeados, pos, i = [], [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            pos.extend(args[i + 1:])
            break
        if a.startswith("--") and len(a) > 2:
            nome, igual, valor = a[2:].partition("=")
            if igual:
                nomeados.append((nome.lower(), valor))
            i += 1
            continue
        if len(a) > 1 and a[0] == "-" and a[1].isalpha():
            nome, dois_pontos, valor = a[1:].partition(":")
            nome = nome.lower()
            if dois_pontos:
                nomeados.append((nome, valor))
            elif nome not in _PS_SWITCHES and i + 1 < len(args) and not args[i + 1].startswith("-"):
                nomeados.append((nome, args[i + 1]))
                i += 1
            i += 1
            continue
        pos.append(a)
        i += 1
    return nomeados, pos


# ---------------------------------------------------------- escritores

_APAGAR = {"rm", "del", "erase", "rmdir", "rd", "remove-item", "ri", "unlink", "rimraf"}
_MOVER = {"mv", "move", "move-item", "mi", "ren", "rename", "rename-item", "rni"}
# ln: o destino (o link criado) é o último argumento, como no cp.
_COPIAR = {"cp", "copy", "copy-item", "cpi", "xcopy", "robocopy", "install", "rsync", "scp",
           "ln"}
_GRAVAR = {"tee", "tee-object", "set-content", "sc", "add-content", "ac", "out-file",
           "clear-content", "clc", "new-item", "ni", "touch", "truncate", "mkdir", "md",
           "chmod", "chown", "attrib", "icacls", "takeown", "set-acl", "shred", "sqlite3",
           "dd", "sed", "perl", "curl", "wget", "invoke-webrequest", "iwr",
           "invoke-restmethod", "irm"}
_TODOS_ESCRITORES = _APAGAR | _MOVER | _COPIAR | _GRAVAR
_DESTINO = {"destination", "t", "target-directory"}


def _alvos_de_escrita(prog, args):
    """[(caminho, modo)] que o comando escreve, apaga ou move."""
    if prog == "dd":
        return [(a[3:], "escrita") for a in args if a.lower().startswith("of=")]
    if prog in ("curl", "wget", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"):
        saidas = _valores_opcao(args, "-o", "--output", "-O", "--output-document", "-OutFile",
                                "-outfile")
        return [(s, "escrita") for s in saidas]
    if prog in ("sed", "perl") and not any(
            a.startswith("-i") or a.startswith("--in-place")
            or (prog == "perl" and a.startswith("-") and not a.startswith("--") and "i" in a)
            for a in args):
        return []
    nomeados, pos = _args_ps(args)
    if prog == "sqlite3":
        if any(a.lower() in ("-readonly", "--readonly") for a in args):
            return []
        return [(pos[0], "escrita")] if pos else []
    caminhos = [v for nome, v in nomeados if nome not in _PS_NAO_CAMINHO]
    if prog in _APAGAR:
        return [(a, "apagar") for a in caminhos + pos]
    if prog in _MOVER:
        return [(a, "mover") for a in caminhos + pos]
    if prog in _COPIAR:
        destinos = [v for nome, v in nomeados if nome in _DESTINO]
        origens = pos
        if not destinos and pos and (len(pos) >= 2 or caminhos):
            destinos, origens = [pos[-1]], pos[:-1]
            if prog == "robocopy" and len(pos) >= 2:  # robocopy origem destino arquivos...
                destinos = [pos[1]] + [pos[1].rstrip("/\\") + "/" + a for a in pos[2:]]
                origens = []
        alvos = list(destinos)
        for destino in destinos:  # destino pasta: cp x/cs2_tracker.db .
            for origem in origens:
                alvos.append(destino.rstrip("/\\") + "/" + _barras(origem).rsplit("/", 1)[-1])
        return [(a, "escrita") for a in alvos]
    return [(a, "escrita") for a in caminhos + pos]


# Comandos que leem o arquivo e o mostram, copiam ou entregam a outro programa:
# nem o curinga (B0.5b) nem o nome literal (B0.5c) podem alcançar o banco do
# checkout principal ou o .env. Origem de cópia, cat/type/Get-Content (gc),
# sqlite3 (inclusive -readonly), head, xxd e afins.
_LEITORES_SIMPLES = {
    "cat", "tac", "nl", "head", "tail", "less", "more", "bat", "type", "get-content", "gc",
    "sqlite3", "xxd", "od", "hexdump", "strings", "format-hex", "base64", "base32", "md5sum",
    "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum", "b2sum", "cksum", "sort",
    "uniq", "cut", "paste", "fold", "fmt", "column", "diff", "cmp", "comm", "import-csv"}
# Cujo 1º argumento (fora das opções) é o padrão, o filtro ou o script, não um
# arquivo. jq e yq entram aqui: `jq '.env' x.json` lê x.json, não '.env'.
_LEITORES_COM_PADRAO = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "sed", "awk", "gawk",
                        "select-string", "sls", "jq", "yq"}
_LEITORES = _COPIAR | _LEITORES_SIMPLES | _LEITORES_COM_PADRAO
# Opções que dão o padrão ou o script: sobrando isso, todo argumento é arquivo.
_DA_PADRAO = ("-e", "-f", "--regexp", "--file", "-pattern", "-regexp", "-file")
# Destas o valor, na palavra seguinte, é o padrão e não um arquivo:
# grep -e '\.env' x. No jq o -e é só o código de saída.
_PADRAO_NA_PROXIMA = ("-e", "--regexp", "-pattern", "-regexp")
# Opções cujo valor, na palavra seguinte, é glob, número ou tipo: não se lê
# (grep -rn X --exclude .env .). Só as que nunca apontam um arquivo de entrada.
_VALOR_NA_PROXIMA = {"--exclude", "--include", "--exclude-dir", "--include-dir", "--glob",
                     "--iglob", "--type", "--type-not", "--max-count", "--after-context",
                     "--before-context", "--context", "--directories", "--devices", "--color",
                     "--colour", "--label", "-m", "-A", "-B", "-C", "-d", "-D",
                     "-exclude", "-include", "-encoding", "-context"}
# No grep, -T não leva valor; no jq, nenhuma opção curta leva (jq -C . x.json).
_VALOR_NA_PROXIMA_DE = {"rg": _VALOR_NA_PROXIMA | {"-g", "-t", "-T"},
                        "ag": _VALOR_NA_PROXIMA | {"-g"}, "jq": set(), "yq": set()}


def _alvos_sem_padrao(args, prog=""):
    """Palavras de um grep, rg, sed, awk, jq ou Select-String que podem ser
    arquivo: tudo, menos o padrão (a 1ª palavra que não é opção, se nenhuma
    opção o deu) e o valor de opção de glob ou número. Errar pra mais só barra
    um padrão que seja o nome do banco."""
    da_padrao = ("-f", "--file") if prog in ("jq", "yq") else _DA_PADRAO
    na_proxima = () if prog in ("jq", "yq") else _PADRAO_NA_PROXIMA
    com_valor = _VALOR_NA_PROXIMA_DE.get(prog, _VALOR_NA_PROXIMA)
    palavras, padrao_dado, so_palavras, pular = [], False, False, False
    for a in args:
        if pular:
            pular = False
        elif so_palavras or not (len(a) > 1 and a[0] == "-"):
            palavras.append(a)
        elif a == "--":
            so_palavras = True
        else:
            nome, _sep, valor = a.partition("=") if "=" in a else a.partition(":")
            if nome.startswith(da_padrao) or nome.lower().startswith(da_padrao[2:]):
                padrao_dado = True
                pular = not valor and nome.lower() in na_proxima
                if valor and nome.lower() in ("-f", "--file", "-file"):  # --file=<arquivo>
                    palavras.append(valor)
            elif valor and nome.lower() in ("-path", "-literalpath", "-lp", "--file"):
                palavras.append(valor)
            elif not valor and (nome in com_valor or nome.lower() in com_valor):
                pular = True
    return palavras if padrao_dado else palavras[1:]


def _alvos_de_leitura(prog, args):
    """Argumentos que `prog` pode ler: nomeados (-Path, -LiteralPath, o
    -readonly <banco> do sqlite3...), posicionais e o destino também. Só
    barra o que alcança o banco ou o .env, então conferir a mais não bloqueia
    `cp docs/*.md destino/`."""
    if prog in _LEITORES_COM_PADRAO:
        return _alvos_sem_padrao(args, prog)
    nomeados, pos = _args_ps(args)
    return [v for _nome, v in nomeados] + pos


def _checar_leitura(prog, args, ctx):
    for alvo in _alvos_de_leitura(prog, args):
        achado = _motivo_leitura(alvo, ctx)
        if achado:
            raise Bloqueio(f"{prog} (leitura) em {alvo}: {achado[0]}", achado[1])


# Lista literal nua do PowerShell (card B0.5c): @('a', "b") e nada em volta ou
# dentro, só strings literais separadas por vírgula, na mesma linha. Nenhuma
# aspa, nem as tipográficas que o PowerShell também aceita, dentro da string;
# "$x", "`t" e 'it''s' não são literais simples e ficam de fora.
_STRING_NUA_PS = r"""'[^'"\u2018-\u201e`$\r\n]*'|"[^'"\u2018-\u201e`$\r\n]*\""""
_LISTA_NUA_PS = re.compile(
    rf"^@\([ \t]*(?:{_STRING_NUA_PS})(?:[ \t]*,[ \t]*(?:{_STRING_NUA_PS}))*[ \t]*\)$")


def _abrir_listas_ps(prog, brutos, args):
    """Copy-Item @('a','b') d vira Copy-Item a b d: cada string da lista nua
    passa a ser argumento do cmdlet, e os outros checadores a veem. Qualquer
    outro @( num argumento (índice, membro, método, cast, parênteses, $(...),
    -Path:@(...), variável, comando, comentário ou quebra de linha, em volta ou
    dentro) falha fechado: a guarda não tenta seguir a expressão. `brutos` são
    os argumentos antes de trocar as variáveis; `$x = @('a')` só aparece
    expandido. Item que começa com - é caminho, não opção: ganha ./ na frente."""
    saida = []
    for bruto, expandido in zip(brutos, args):
        a = bruto if "@(" in bruto else expandido
        if "@(" not in a:
            saida.append(expandido)
            continue
        if not _LISTA_NUA_PS.match(a):
            raise Bloqueio(f"{prog} com {a} no PowerShell: @(...) ao lado de cmdlet que lê, "
                           "copia, grava ou apaga arquivo só passa como lista literal nua, "
                           "e isto não é uma (falha fechada)",
                           "escreva o caminho literal (Copy-Item 'docs/x.md' destino) ou a "
                           "lista nua @('docs/x.md', 'docs/y.md'), sem índice, membro, método, "
                           "cast, parênteses, $(...), variável, comentário nem quebra de linha")
        for item in re.findall(_STRING_NUA_PS, a[2:-1]):
            saida.append(("./" if item[1:2] == "-" else "") + item[1:-1])
    return saida


# ----------------------------------------------------------- tratadores

def _bloquear_compose_fora(lugar):
    raise Bloqueio(
        f"docker compose fora do checkout principal ({lugar or 'diretório desconhecido'}): "
        "sem `name:`, o compose cria projeto e volume novos e vazios",
        f"só o papel servidor, em janela, de {PRINCIPAL}")


def _h_compose(prog, args, dialeto, ctx, env):
    arquivos, projeto, diretorio = [], None, None
    com_valor = {"-f", "--file", "-p", "--project-name", "--project-directory", "--env-file",
                 "--profile", "--ansi", "--parallel", "--progress", "--workdir"}
    i = 0
    while i < len(args):
        a = args[i]
        if not a.startswith("-") or a == "-":
            break
        nome, igual, valor = a.partition("=")
        if nome in com_valor:
            if not igual:
                valor = args[i + 1] if i + 1 < len(args) else ""
                i += 1
            if nome in ("-f", "--file"):
                arquivos.append(valor)
            elif nome in ("-p", "--project-name"):
                projeto = valor
            elif nome in ("--project-directory", "--workdir"):
                diretorio = valor
        elif a.startswith("-p") and len(a) > 2 and not a.startswith("--"):
            projeto = a[2:]
        elif a.startswith("-f") and len(a) > 2 and not a.startswith("--"):
            arquivos.append(a[2:])
        i += 1
    sub = args[i].lower() if i < len(args) else ""
    resto = args[i + 1:]
    if sub in ("", "version", "ls", "help"):
        return
    if sub == "run":
        raise Bloqueio("docker compose run cria container avulso no projeto do jogo",
                       "build do plugin só pelo papel servidor, em janela, e pelo Victor")
    if sub == "down":
        volumes = any(a in ("-v", "--volumes") or a.startswith("--volumes=")
                      or (a.startswith("-") and not a.startswith("--") and "v" in a[1:])
                      for a in resto)
        raise Bloqueio("docker compose down" + (" -v apaga o volume do jogo (~73 GB, não "
                                                "reproduzível)" if volumes else
                                                " derruba o servidor do Victor"),
                       "nada disso; parar o jogo é do papel servidor, em janela, com stop")
    projeto = projeto or env.get("COMPOSE_PROJECT_NAME") or os.environ.get("COMPOSE_PROJECT_NAME")
    if projeto is not None and projeto.lower() != PROJETO_COMPOSE:
        raise Bloqueio(f"docker compose com projeto {projeto!r}: cria volume novo e vazio",
                       f"sem -p nem COMPOSE_PROJECT_NAME, do checkout principal {PRINCIPAL}")
    if not arquivos and env.get("COMPOSE_FILE"):
        arquivos = [f for f in env["COMPOSE_FILE"].split(";") if f]
    base = ctx.cwd
    if diretorio is not None:
        dir_projeto = _absoluto(diretorio, base)
    elif arquivos:
        primeiro = _absoluto(arquivos[0], base)
        dir_projeto = posixpath.dirname(primeiro) if primeiro else None
    else:
        dir_projeto = base
    lugares = [(dir_projeto, diretorio or base)] + [(_absoluto(f, base), f) for f in arquivos]
    for absoluto, bruto in lugares:
        if not ctx.no_principal(absoluto):
            _bloquear_compose_fora(absoluto or bruto)
    if sub == "config" and not any(a.split("=", 1)[0] in _CONFIG_SEGURO for a in resto):
        raise Bloqueio("docker compose config imprime os valores do .env (SRCDS_TOKEN, senha "
                       "do RCON) na conversa",
                       "docker compose config -q pra validar, --hash '*' pra comparar, "
                       "--services ou --volumes pra listar")
    if sub == "logs":
        _checar_preflight(ctx, "docker compose logs")


# Formas do compose config que não imprimem valor interpolado do .env.
_CONFIG_SEGURO = {"-q", "--quiet", "--services", "--volumes", "--profiles", "--images", "--hash",
                  "--networks", "--no-interpolate"}
_FORMATO_COM_ENV = re.compile(r"env|\{\{\s*(?:json\s+)?\.\s*(?:config\s*)?\}\}", re.IGNORECASE)


def _checar_preflight(ctx, oque):
    codigo = ctx.preflight()
    if codigo not in (0, 4):
        raise Bloqueio(f"{oque} com o Victor jogando (tools/preflight.py devolveu {codigo})",
                       "espere o preflight dar 0: a coleta roda depois da partida (protocolo 11)")


def _rodar_preflight():
    import subprocess
    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(aqui, "preflight.py")
    if not os.path.isfile(script):
        script = PRINCIPAL + "/tools/preflight.py"
    if not os.path.isfile(script):
        return 3
    extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        return subprocess.run([sys.executable, script], stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=TIMEOUT_PREFLIGHT_S,
                              **extra).returncode
    except Exception:
        return 3


def _h_docker(prog, args, dialeto, ctx, env):
    com_valor = {"--config", "-c", "--context", "-H", "--host", "-l", "--log-level",
                 "--tlscacert", "--tlscert", "--tlskey"}
    i = _primeiro_nao_opcao(args, com_valor)
    if i >= len(args):
        return
    sub, resto = args[i].lower(), args[i + 1:]
    if sub == "compose":
        _h_compose("docker-compose", resto, dialeto, ctx, env)
        return
    j = _primeiro_nao_opcao(resto)
    acao = resto[j].lower() if j < len(resto) else ""
    if sub == "container" and acao:
        sub, resto = acao, resto[j + 1:]
    if sub == "inspect":
        formatos = _valores_opcao(resto, "-f", "--format")
        if not formatos or any(_FORMATO_COM_ENV.search(f) for f in formatos):
            raise Bloqueio("docker inspect sem --format (ou com o Env no formato) imprime o "
                           "ambiente do container, com SRCDS_TOKEN e a senha do RCON",
                           "docker inspect --format '{{.State.Status}}' (só o campo que precisa)")
    if sub == "volume" and acao in ("rm", "remove", "prune"):
        raise Bloqueio(f"docker volume {acao} apaga o volume do jogo (~73 GB, não reproduzível)",
                       "nada: o volume cs2-tracker_cs2-data só é tocado pelo Victor")
    if sub == "system" and acao == "prune":
        raise Bloqueio("docker system prune pode levar containers, imagens e volumes do jogo",
                       "nada; limpeza do Docker é com o Victor")
    if sub == "logs":
        _checar_preflight(ctx, "docker logs")
    if sub in ("run", "create"):
        for publicacao in _valores_opcao(resto, "-p", "--publish"):
            partes = publicacao.split("/")[0].split(":")
            if len(partes) >= 2 and partes[-2] == str(PORTA_DO_VICTOR):
                raise Bloqueio("docker run publicando a porta 8000, que é do Victor",
                               "use a 8010")


def _h_git(prog, args, dialeto, ctx, env):
    i = _primeiro_nao_opcao(args, {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                                   "--super-prefix", "--config-env"})
    sub = args[i].lower() if i < len(args) else ""
    resto = args[i + 1:]
    apelidos = {}
    for valor in _valores_opcao(args[:i], "-c"):  # git -c alias.x=clean x
        chave, igual, corpo = valor.partition("=")
        if igual and chave.lower().startswith("alias."):
            apelidos[chave[6:].lower()] = corpo
    if sub in apelidos:
        _expandir_alias_git(apelidos[sub], resto, dialeto, ctx, env)
        return
    if sub == "config":  # git config alias.x '!docker compose down -v'
        for k, a in enumerate(resto):
            if a.lower().startswith("alias.") and k + 1 < len(resto):
                _expandir_alias_git(" ".join(resto[k + 1:]), [], dialeto, ctx, env)
                break
    if sub == "clean":
        raise Bloqueio("git clean apaga não rastreados e ignorados: banco, events-live, .env e "
                       "a DLL (critic, risco 1)",
                       "apague só o que você criou, pelo nome")
    if sub == "stash" and any(a in ("-a", "--all") or (a.startswith("-") and not a.startswith("--")
                                                       and a[1:].isalpha() and "a" in a[1:])
                              for a in resto):
        raise Bloqueio("git stash --all tira do disco os ignorados (banco, events-live, .env)",
                       "git stash push -m <tag> só com o que é rastreado, ou um commit WIP")


def _expandir_alias_git(corpo, resto, dialeto, ctx, env):
    """Alias do git: `!cmd` roda no shell; senão é um subcomando do git."""
    corpo = corpo.strip()
    if corpo.startswith("!"):
        analisar_comando(" ".join([corpo[1:]] + [_citar(a, "bash") for a in resto]), "bash",
                         ctx.filho())
    elif corpo:
        _h_git("git", _palavras(corpo) + resto, dialeto, ctx.filho(), env)


def _h_pip(prog, args, dialeto, ctx, env):
    if any(a.lower() in ("install", "uninstall") for a in args):
        raise Bloqueio("pip install/uninstall mexe na .venv do jogo",
                       "precisa de dependência? pare e peça ao Victor")


def _h_uv(prog, args, dialeto, ctx, env):
    i = _primeiro_nao_opcao(args, {"--directory", "--project", "--cache-dir", "--python", "-p",
                                   "--config-file", "--color"})
    sub = args[i].lower() if i < len(args) else ""
    resto = args[i + 1:]
    if sub == "pip" and any(a.lower() in ("install", "uninstall", "sync") for a in resto):
        raise Bloqueio("uv pip install/uninstall/sync mexe na .venv do jogo",
                       "precisa de dependência? pare e peça ao Victor")
    if sub in ("add", "remove", "sync"):
        raise Bloqueio(f"uv {sub} mexe nas dependências e na .venv",
                       "precisa de dependência? pare e peça ao Victor")
    if sub == "run":
        j = _primeiro_nao_opcao(resto, {"--with", "--python", "-p", "--directory", "--project",
                                        "--env-file", "--extra", "--group", "--package", "--index"})
        if j < len(resto):
            _analisar_palavras(resto[j:], dialeto, ctx.filho(), env)
    elif sub == "tool" and resto[:1] == ["run"]:
        _embrulho("uvx", resto[1:], dialeto, ctx, env)


_REDE = [
    (re.compile(r"docker(?:\W{1,6}|-)compose\W[\s\S]{0,120}?\b(down|run)\b", re.I), "docker compose down/run"),
    (re.compile(r"\bvolume\W{1,6}(rm|remove|prune)\b", re.I), "docker volume rm/prune"),
    (re.compile(r"\bsystem\W{1,6}prune\b", re.I), "docker system prune"),
    (re.compile(r"\bgit\W{1,6}(?:-C\W+\S+\W+)?clean\b", re.I), "git clean"),
    (re.compile(r"\bgit\W{1,6}-c\W+alias\.", re.I), "git -c alias"),
    (re.compile(r"\bpip\d*(?:\.exe)?\W{1,6}(?:un)?install\b", re.I), "pip install"),
    (re.compile(r"\bpip\s*\.\s*main\b|\bpip\._internal\b", re.I), "pip install (pip.main)"),
]
# Chamada com texto no 1º argumento (e talvez no 2º): a tabela diz o que ela
# faz com cada um. remove/replace/rename/move/copy/truncate são comuns demais
# (list.remove, str.replace) e só contam com os, shutil ou fs na frente.
_CODIGO_ARQUIVO = re.compile(
    r"(?:\b(?P<mod>\w+)\s*\.\s*)?\b(?P<f>\w+)\s*\(\s*[rbuf]*(?P<q1>['\"])(?P<a>.*?)(?P=q1)"
    r"(?:\s*,\s*[rbuf]*(?P<q2>['\"])(?P<b>.*?)(?P=q2))?")
_FUNCOES_DE_ARQUIVO = {
    **dict.fromkeys(("rmtree", "removedirs", "unlink", "unlinksync", "rmdir", "rmdirsync",
                     "rmsync"), ("apagar", None)),
    **dict.fromkeys(("renamesync",), ("mover", "escrita")),
    **dict.fromkeys(("copyfile", "copytree", "copyfilesync", "cpsync"), (None, "escrita")),
    **dict.fromkeys(("writefile", "writefilesync", "appendfile", "appendfilesync",
                     "truncatesync"), ("escrita", None)),
}
_FUNCOES_COM_MODULO = {
    "remove": ("apagar", None), "rm": ("apagar", None), "rename": ("mover", "escrita"),
    "replace": ("mover", "escrita"), "move": ("mover", "escrita"), "copy": (None, "escrita"),
    "copy2": (None, "escrita"), "cp": (None, "escrita"), "truncate": ("escrita", None),
}
_MODULOS_DE_ARQUIVO = {"os", "shutil", "fs", "fsp", "promises"}
_CODIGO_OPEN = re.compile(r"\bopen\s*\(\s*[rbuf]*(['\"])(.*?)\1\s*,\s*(?:mode\s*=\s*)?[rbuf]*"
                          r"(['\"])([^'\"]*)\3", re.IGNORECASE)
_CODIGO_PATH = re.compile(r"\bPath\s*\(\s*[rbuf]*(['\"])(.*?)\1\s*\)\s*\.\s*(write_text|"
                          r"write_bytes|unlink|rmdir|touch|rename|replace|open\s*\(\s*['\"]"
                          r"[^'\"]*[wax+])", re.IGNORECASE)
_UVICORN_RUN = re.compile(r"\buvicorn\s*\.\s*run\s*\(", re.IGNORECASE)


def _modo_da_funcao(modulo, funcao):
    """(modo do 1º argumento, modo do 2º) da chamada, ou (None, None)."""
    f = funcao.lower()
    if f in _FUNCOES_DE_ARQUIVO:
        return _FUNCOES_DE_ARQUIVO[f]
    if f in _FUNCOES_COM_MODULO and (modulo or "").lower() in _MODULOS_DE_ARQUIVO:
        return _FUNCOES_COM_MODULO[f]
    return None, None


def _rede_codigo(codigo, origem, ctx=None):
    """Código inline (python -c, node -e...) não é analisável: procura o texto."""
    codigo = codigo or ""
    for regex, oque in _REDE:
        if regex.search(codigo):
            raise Bloqueio(f"código inline ({origem}) chama {oque}",
                           "rode o comando direto, onde a guarda vê, e só o que as regras permitem")
    m = _UVICORN_RUN.search(codigo)
    if m:
        porta = re.search(r"\bport\s*=\s*(\d+)", codigo[m.end():])
        if porta is None or int(porta.group(1)) == PORTA_DO_VICTOR:
            raise Bloqueio(f"código inline ({origem}) sobe o uvicorn na 8000, que é do Victor",
                           "uvicorn.run(..., port=8010) com banco de fixture")
    if ctx is None:
        return
    for m in _CODIGO_ARQUIVO.finditer(codigo):
        modo_a, modo_b = _modo_da_funcao(m.group("mod"), m.group("f"))
        if modo_a:
            _checar_caminho(m.group("a"), ctx, modo_a, f"{origem}: {m.group('f')}")
        if modo_b and m.group("b") is not None:
            _checar_caminho(m.group("b"), ctx, modo_b, f"{origem}: {m.group('f')}")
    for m in _CODIGO_OPEN.finditer(codigo):
        if any(c in m.group(4).lower() for c in "wax+"):
            _checar_caminho(m.group(2), ctx, "escrita", f"{origem}: open(..., {m.group(4)!r})")
    for m in _CODIGO_PATH.finditer(codigo):
        modo = "apagar" if m.group(3).lower() in ("unlink", "rmdir") else (
            "mover" if m.group(3).lower() in ("rename", "replace") else "escrita")
        _checar_caminho(m.group(2), ctx, modo, f"{origem}: Path.{m.group(3).split('(')[0]}")


# Opções do python que levam valor; -c e -m encerram as opções.
_PY_COM_VALOR = "cmWX"


def _h_python(prog, args, dialeto, ctx, env):
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--check-hash-based-pycs":
            i += 2
            continue
        if a.startswith("--") or a == "-":
            if a in ("--", "-"):
                return  # script pela entrada padrão ou depois do --: não dá pra ver
            i += 1
            continue
        if not a.startswith("-"):
            if _programa(a) == "manage.py":
                _checar_servidor("django-admin", args[i + 1:], env)
            return
        # Opções curtas juntas: -Im pip, -Esm pip, -Wignore, -cCODIGO.
        j = next((k for k in range(1, len(a)) if a[k] in _PY_COM_VALOR), None)
        if j is None:
            i += 1
            continue
        opcao, valor = a[j], a[j + 1:]
        if valor:
            resto = args[i + 1:]
        else:
            valor = args[i + 1] if i + 1 < len(args) else ""
            resto = args[i + 2:]
        if opcao == "m":
            _h_modulo_python(valor.lower(), resto, dialeto, ctx, env)
            return
        if opcao == "c":
            _rede_codigo(valor, "python -c", ctx)
            return
        i += 1 if a[j + 1:] else 2


def _h_modulo_python(modulo, resto, dialeto, ctx, env):
    if modulo in ("pip", "pip.__main__") or modulo.startswith("pip._internal"):
        _h_pip("pip", resto, dialeto, ctx, env)
    elif modulo in ("http.server", "simplehttpserver"):
        _checar_servidor("http.server", resto, env)
    elif modulo == "django":
        _checar_servidor("django-admin", resto, env)
    elif modulo in _SERVIDORES:
        _checar_servidor(modulo, resto, env)
    else:
        _porta_generica(modulo, resto)


def _h_inline(prog, args, dialeto, ctx, env):
    for opcao in ("-e", "-E", "--eval", "-p", "--print", "-r"):
        for codigo in _valores_opcao(args, opcao):
            _rede_codigo(codigo, f"{prog} {opcao}", ctx)
    if prog == "php":
        _checar_servidor("php", args, env)


# ------------------------------------------------------------ servidores

_SERVIDORES = {"uvicorn", "gunicorn", "hypercorn", "daphne", "fastapi", "flask", "mkdocs",
               "django-admin", "http-server", "serve", "live-server"}
_SEM_PORTA = {"git", "gh", "grep", "rg", "findstr", "select-string", "sls", "echo", "printf",
              "write-output", "write-host", "sed", "awk", "cat", "type"}
# Programas cujos argumentos são texto ou nome, nunca um comando a executar:
# a rede de palavras não olha depois deles (echo docker compose down, man git clean).
_SO_TEXTO = _SEM_PORTA | {"man", "help", "get-help", "info", "tldr", "whatis", "apropos", "which",
                          "where", "whereis", "get-command", "gcm", "write-error",
                          "write-warning", "write-verbose", "write-debug", "write-information",
                          "out-host", "set-clipboard", "code", "notepad"}


def _int(valor, padrao):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return padrao


def _porta_de_endereco(valor, padrao):
    if valor is None:
        return padrao
    v = valor.strip()
    if v.lower().startswith(("unix:", "fd:")):
        return None
    if v.isdigit():
        return int(v)
    if ":" in v:
        return _int(v.rsplit(":", 1)[1].strip("/"), padrao)
    return padrao


def _porta_servidor(prog, args, env):
    """Porta TCP que o servidor vai ouvir (padrão incluído) ou None."""
    def valor(*nomes):
        achados = _valores_opcao(args, *nomes)
        return achados[-1] if achados else None

    posicionais = [a for a in args if not a.startswith("-")]
    if prog == "uvicorn":
        if valor("--uds", "--fd") is not None:
            return None
        return _int(valor("--port") or env.get("UVICORN_PORT"), PORTA_DO_VICTOR)
    if prog == "http.server":
        pos = [a for i, a in enumerate(args) if not a.startswith("-")
               and not (i and args[i - 1] in ("-b", "--bind", "-d", "--directory", "-p",
                                                "--protocol"))]
        return _int(pos[0], PORTA_DO_VICTOR) if pos else PORTA_DO_VICTOR
    if prog in ("gunicorn", "hypercorn"):
        binds = _valores_opcao(args, "-b", "--bind")
        portas = [_porta_de_endereco(b, PORTA_DO_VICTOR) for b in binds] or [PORTA_DO_VICTOR]
        return PORTA_DO_VICTOR if PORTA_DO_VICTOR in portas else portas[0]
    if prog == "daphne":
        return _int(valor("-p", "--port"), PORTA_DO_VICTOR)
    if prog == "fastapi" and posicionais[:1] and posicionais[0] in ("dev", "run"):
        return _int(valor("--port"), PORTA_DO_VICTOR)
    if prog == "flask" and "run" in posicionais:
        return _int(valor("--port", "-p") or env.get("FLASK_RUN_PORT"), 5000)
    if prog == "mkdocs" and "serve" in posicionais:
        return _porta_de_endereco(valor("-a", "--dev-addr"), PORTA_DO_VICTOR)
    if prog == "django-admin" and "runserver" in posicionais:
        depois = posicionais[posicionais.index("runserver") + 1:]
        return _porta_de_endereco(depois[0], PORTA_DO_VICTOR) if depois else PORTA_DO_VICTOR
    if prog == "php":
        endereco = valor("-S")
        return _porta_de_endereco(endereco, None) if endereco else None
    if prog in ("http-server", "live-server"):
        return _int(valor("-p", "--port"), 8080)
    if prog == "serve":
        return _porta_de_endereco(valor("-l", "--listen"), 3000)
    return None


def _checar_servidor(prog, args, env):
    if _porta_servidor(prog, args, env) == PORTA_DO_VICTOR:
        raise Bloqueio(f"{prog} na porta 8000, que é do Victor (padrão do {prog} incluído)",
                       "use --port 8010 com banco de fixture")


def _h_servidor(prog, args, dialeto, ctx, env):
    _checar_servidor(prog, args, env)


def _porta_generica(prog, args):
    for nome in ("--port", "--http-port", "--server.port"):
        if any(_int(v, None) == PORTA_DO_VICTOR for v in _valores_opcao(args, nome)):
            raise Bloqueio(f"{prog} {nome} 8000: a porta é do Victor", "use a 8010")
    for nome in ("--bind", "--listen", "--dev-addr", "--address", "--addr"):
        if any(_porta_de_endereco(v, None) == PORTA_DO_VICTOR and ":" in v
               for v in _valores_opcao(args, nome)):
            raise Bloqueio(f"{prog} {nome} ...:8000: a porta é do Victor", "use a 8010")


# ------------------------------------------------ shells e embrulhos

def _h_sh(prog, args, dialeto, ctx, env):
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-c" or (a.startswith("-") and not a.startswith("--") and "c" in a[1:]):
            if i + 1 < len(args):
                analisar_comando(args[i + 1], "bash", ctx.filho())
            return
        if a in ("-o", "+o", "-O", "+O", "--rcfile", "--init-file"):
            i += 2
        elif a.startswith(("-", "+")):
            i += 1
        else:
            return  # script: não dá pra ver o conteúdo


def _h_pwsh(prog, args, dialeto, ctx, env):
    filho = ctx.filho()
    i = 0
    while i < len(args):
        a = args[i]
        if a[:1] in ("-", "/") and len(a) > 1:
            nome = a[1:].split(":", 1)[0].lower()
            if nome in ("c", "command") or (len(nome) >= 3 and "command".startswith(nome)):
                analisar_comando(" ".join(args[i + 1:]), "ps", filho)
                return
            if nome in ("e", "ec") or (len(nome) >= 2 and "encodedcommand".startswith(nome)):
                import base64
                import binascii
                try:
                    texto = base64.b64decode(args[i + 1] if i + 1 < len(args) else "",
                                             validate=True).decode("utf-16-le")
                except (binascii.Error, UnicodeDecodeError, ValueError):
                    raise Bloqueio("-EncodedCommand ilegível: a guarda não consegue ver o comando",
                                   "rode o comando em texto puro") from None
                analisar_comando(texto, "ps", filho)
                return
            if nome in ("f", "file"):
                return
            if nome in ("wd", "workingdirectory") and i + 1 < len(args):
                filho.cwd = _absoluto(args[i + 1], ctx.cwd)
                i += 2
                continue
            if nome in ("ex", "ep", "w", "o", "of", "if", "v", "version", "executionpolicy",
                        "windowstyle", "outputformat", "inputformat", "configurationname",
                        "custompipename", "settingsfile", "config"):
                i += 2
                continue
            i += 1
            continue
        analisar_comando(" ".join(args[i:]), "ps", filho)
        return


def _h_cmd(prog, args, dialeto, ctx, env):
    for i, a in enumerate(args):
        if a.lower() in ("/c", "/k", "/r"):
            analisar_comando(" ".join(args[i + 1:]), "cmd", ctx.filho())
            return
        if a.lower()[:2] in ("/c", "/k", "/r") and len(a) > 2:
            analisar_comando(" ".join([a[2:]] + args[i + 1:]), "cmd", ctx.filho())
            return


def _h_eval(prog, args, dialeto, ctx, env):
    textos = [a for a in args if not (dialeto == "ps" and a.lower() == "-command")]
    analisar_comando(" ".join(textos), "ps" if prog in ("iex", "invoke-expression") else dialeto,
                     ctx.filho())


_START_VALORES = {"verb", "windowstyle", "credential", "environment", "redirectstandardinput"}
_START_PARAMS = {"filepath", "argumentlist", "args", "workingdirectory", "wait", "nonewwindow",
                 "passthru", "verb", "windowstyle", "credential", "loaduserprofile",
                 "usenewenvironment", "environment", "redirectstandardoutput",
                 "redirectstandarderror", "redirectstandardinput", "whatif", "confirm"}


def _h_start_process(prog, args, dialeto, ctx, env):
    filho = ctx.filho()
    arquivo, lista, soltos = None, [], []
    i = 0
    while i < len(args):
        a = args[i]
        nome = a[1:].split(":", 1)[0].lower() if a.startswith("-") and len(a) > 1 else None
        if prog == "start" and dialeto != "ps" and (a.startswith("/") and len(a) > 1 or not a):
            # start do cmd: /b, /min, /wait, /d <pasta> e o título "" não são o programa.
            i += 2 if a.lower() == "/d" else 1
            continue
        if nome == "filepath":
            arquivo = args[i + 1] if i + 1 < len(args) else None
            i += 2
        elif nome in ("argumentlist", "args"):
            i += 1
            while i < len(args) and not (args[i].startswith("-") and len(args[i]) > 1
                                         and args[i][1:].split(":")[0].lower() in _START_PARAMS):
                lista.append(args[i])
                i += 1
        elif nome == "workingdirectory":
            filho.cwd = _absoluto(args[i + 1], ctx.cwd) if i + 1 < len(args) else None
            i += 2
        elif nome in ("redirectstandardoutput", "redirectstandarderror"):
            if i + 1 < len(args):
                _checar_caminho(args[i + 1], ctx, "escrita", "Start-Process")
            i += 2
        elif nome in _START_VALORES:
            i += 2
        elif nome is not None:
            i += 1
        else:
            soltos.append(a)
            i += 1
    if arquivo is None and soltos:
        arquivo = soltos.pop(0)
    lista = lista or soltos
    if arquivo:
        palavras = [arquivo]
        for item in lista:
            palavras.extend(_palavras(item) if " " in item.strip() else [item])
        _analisar_palavras(palavras, "bash", filho, env)


_EMBRULHO_VALOR = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-r", "-t", "-U", "-T", "-D", "--chdir"},
    "nice": {"-n"}, "stdbuf": {"-i", "-o", "-e"}, "watch": {"-n", "--interval"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "xargs": {"-I", "-n", "-L", "-P", "-d", "-E", "-s", "-a", "--max-args", "--max-procs",
              "--delimiter", "--arg-file", "--replace"},
    "npx": {"-p", "--package"}, "bunx": {"-p", "--package"}, "uvx": {"--with", "--from", "-p",
                                                                    "--python"},
    "ionice": {"-c", "--class", "-n", "--classdata", "-p", "--pid", "-P", "--pgid", "-u", "--uid"},
    "doas": {"-u", "-C"}, "flock": {"-w", "--timeout", "-E", "--conflict-exit-code"},
}
# Embrulhos cujo 1º argumento depois das opções não é o comando: a duração
# (timeout), a prioridade (chrt), a máscara (taskset) e o arquivo de trava (flock).
_EMBRULHO_PULA_UM = {"timeout", "chrt", "taskset", "flock"}


def _embrulho(prog, args, dialeto, ctx, env):
    """sudo, nohup, xargs, timeout...: o comando de verdade vem depois das opções."""
    if prog in ("flock", "script"):  # flock -c 'cmd' arq, script -qc 'cmd' /dev/null
        for k, a in enumerate(args):
            if a.startswith("--command="):
                analisar_comando(a[len("--command="):], "bash", ctx.filho())
                return
            if a == "--command" or (a.startswith("-") and not a.startswith("--")
                                    and a.endswith("c")):
                if k + 1 < len(args):
                    analisar_comando(args[k + 1], "bash", ctx.filho())
                return
        if prog == "script":
            return  # sem -c, o script abre um shell interativo
    i = _primeiro_nao_opcao(args, _EMBRULHO_VALOR.get(prog, ()))
    if prog in _EMBRULHO_PULA_UM and i < len(args):
        i += 1
    resto = args[i:]
    if prog == "watch":
        analisar_comando(" ".join(resto), "bash", ctx.filho())
    elif prog in ("poetry", "pipenv", "pipx"):
        if args[:1] == ["run"]:
            _analisar_palavras(args[1:], dialeto, ctx.filho(), env)
    elif resto:
        _analisar_palavras(resto, dialeto, ctx.filho(), env)


def _h_env(prog, args, dialeto, ctx, env):
    filho, local, i = ctx.filho(), {}, 0
    while i < len(args):
        a = args[i]
        if a in ("-C", "--chdir") and i + 1 < len(args):
            filho.cwd = _absoluto(args[i + 1], ctx.cwd)
            i += 2
        elif a in ("-u", "--unset"):
            i += 2
        elif a in ("-S", "--split-string") and i + 1 < len(args):
            _analisar_palavras(_palavras(args[i + 1]) + args[i + 2:], dialeto, filho, local)
            return
        elif a.startswith("-"):
            i += 1
        elif _ATRIB.match(a):
            m = _ATRIB.match(a)
            local[m.group(1).upper()] = m.group(2)
            i += 1
        else:
            break
    if i < len(args):
        env_total = dict(env)
        env_total.update(local)
        _analisar_palavras(args[i:], dialeto, filho, env_total)


def _h_wsl(prog, args, dialeto, ctx, env):
    filho, i = ctx.filho(), 0
    while i < len(args):
        a = args[i]
        if a in ("-e", "--exec", "--"):
            i += 1
            break
        if a == "--cd" and i + 1 < len(args):
            filho.cwd = _absoluto(args[i + 1], ctx.cwd)
            i += 2
        elif a in ("-d", "--distribution", "-u", "--user", "--shell-type"):
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            break
    if i < len(args):
        _analisar_palavras(args[i:], "bash", filho, env)


def _h_find(prog, args, dialeto, ctx, env):
    for i, a in enumerate(args):
        if a in ("-exec", "-execdir", "-ok", "-okdir"):
            fim = next((j for j in range(i + 1, len(args)) if args[j] in (";", "+")), len(args))
            if fim > i + 1:
                _analisar_palavras(args[i + 1:fim], dialeto, ctx.filho(), env)
    if "-delete" in args:
        inicio = [a for a in args[:next((k for k, a in enumerate(args)
                                         if a.startswith(("-", "(", "!"))), len(args))]]
        for alvo in inicio or ["."]:
            _checar_caminho(alvo, ctx, "apagar", "find -delete")


def _mudar_diretorio(prog, args, dialeto, ctx, env):
    if dialeto == "ps" or "-" in prog:
        nomeados, pos = _args_ps(args)
        alvos = [v for nome, v in nomeados if nome in ("path", "literalpath", "lp", "pspath")] + pos
    else:
        alvos = [a for a in args if not (a.startswith("-") and a != "-")
                 and not (dialeto == "cmd" and a.lower() == "/d")]
    if not alvos:
        if dialeto != "cmd":
            ctx.cwd = _absoluto("~", None)
        return
    ctx.cwd = None if alvos[0] == "-" else _absoluto(alvos[0], ctx.cwd)


def _perder_diretorio(prog, args, dialeto, ctx, env):
    ctx.cwd = None


def _exportar(prog, args, dialeto, ctx, env):
    for a in args:
        m = _ATRIB.match(a)
        if m:
            ctx.env[m.group(1).upper()] = m.group(2)


def _nome_e_valor_ps(args):
    """(nome, valor) de Set-Alias/Set-Variable: -Name/-Value ou posicionais."""
    nomeados, pos = _args_ps(args)
    nome = next((v for n, v in nomeados if n == "name"), None)
    valor = next((v for n, v in nomeados if n == "value"), None)
    for p in pos:
        if nome is None:
            nome = p
        elif valor is None:
            valor = p
    return nome, valor


def _h_alias(prog, args, dialeto, ctx, env):
    """alias d=docker (bash) e Set-Alias d docker (PowerShell)."""
    if prog == "alias":
        for a in args:
            nome, igual, valor = a.partition("=")
            if igual and nome and not nome.startswith("-"):
                ctx.apelidos[nome.lower()] = valor
        return
    nome, valor = _nome_e_valor_ps(args)
    if nome and valor:
        ctx.apelidos[nome.lower()] = valor


def _h_set_variable(prog, args, dialeto, ctx, env):
    nome, valor = _nome_e_valor_ps(args)
    if nome and valor is not None:
        ctx.env[nome.upper()] = _expandir(valor, env, ctx, dialeto, sistema=True)


_TRATADORES = {
    "docker": _h_docker, "com.docker.cli": _h_docker, "docker-compose": _h_compose,
    "git": _h_git, "pip": _h_pip, "python": _h_python, "uv": _h_uv,
    "node": _h_inline, "bun": _h_inline, "deno": _h_inline, "perl": _h_inline,
    "ruby": _h_inline, "php": _h_inline,
    "bash": _h_sh, "sh": _h_sh, "zsh": _h_sh, "dash": _h_sh, "ksh": _h_sh, "git-bash": _h_sh,
    "powershell": _h_pwsh, "pwsh": _h_pwsh, "powershell_ise": _h_pwsh, "cmd": _h_cmd,
    "eval": _h_eval, "iex": _h_eval, "invoke-expression": _h_eval,
    "start-process": _h_start_process, "start": _h_start_process, "saps": _h_start_process,
    "env": _h_env, "wsl": _h_wsl, "find": _h_find,
    "cd": _mudar_diretorio, "chdir": _mudar_diretorio, "pushd": _mudar_diretorio,
    "set-location": _mudar_diretorio, "sl": _mudar_diretorio, "push-location": _mudar_diretorio,
    "popd": _perder_diretorio, "pop-location": _perder_diretorio,
    "export": _exportar, "declare": _exportar, "typeset": _exportar, "local": _exportar,
    "readonly": _exportar,
    "alias": _h_alias, "set-alias": _h_alias, "new-alias": _h_alias, "sal": _h_alias,
    "nal": _h_alias,
    "set-variable": _h_set_variable, "new-variable": _h_set_variable, "sv": _h_set_variable,
    "nv": _h_set_variable,
}
for _nome in _SERVIDORES:
    _TRATADORES[_nome] = _h_servidor
for _nome in ("sudo", "nohup", "time", "command", "builtin", "exec", "nice", "timeout", "stdbuf",
              "xargs", "watch", "winpty", "unbuffer", "call", "npx", "bunx", "pnpx", "uvx",
              "poetry", "pipenv", "pipx", ".", "setsid", "ionice", "chrt", "taskset", "busybox",
              "doas", "flock", "script"):
    _TRATADORES[_nome] = _embrulho


# -------------------------------------------------- ferramentas de arquivo

def _escopo_pii(caminho, ctx):
    """(ids, ips, segredos): o que conferir num Write/Edit nesse caminho.
    Segredo do .env: qualquer arquivo do repositório (nunca é lugar dele).
    SteamID: docs/, tests/, .cursor/, .env.example e *.md da raiz. IPv4:
    os mesmos, menos tests/ fora de tests/fixtures/. O board do Obsidian
    (docs/board-cs2/) fica fora do git e fora da checagem."""
    absoluto = _absoluto(caminho, ctx.cwd)
    raiz = _raiz_git(absoluto)[0] if absoluto else None
    if raiz:
        relativo = absoluto[len(raiz.rstrip("/")) + 1:].lower()
    elif absoluto:
        return False, False, False  # fora de repositório: scratchpad, temporário
    else:
        relativo = _barras(caminho).lower()
        while relativo.startswith("./"):
            relativo = relativo[2:]
        for marco in ("/docs/", "/tests/", "/.cursor/"):  # caminho sem base conhecida
            if marco in "/" + relativo:
                relativo = marco[1:] + ("/" + relativo).split(marco, 1)[1]
                break
    if relativo.startswith("docs/board-cs2/"):
        return False, False, True
    publico = (relativo.startswith(("docs/", "tests/fixtures/", ".cursor/"))
               or relativo == ".env.example" or ("/" not in relativo and relativo.endswith(".md")))
    return publico or relativo.startswith("tests/"), publico, True


def _avaliar_arquivo(ferramenta, entrada, ctx):
    caminho = entrada.get("file_path") or entrada.get("notebook_path") or ""
    if not isinstance(caminho, str) or not caminho:
        return
    _checar_caminho(caminho, ctx, "escrita", ferramenta)
    ids, ips, segredos = _escopo_pii(caminho, ctx)
    if not (ids or ips or segredos):
        return
    textos = [entrada.get("content"), entrada.get("new_string"), entrada.get("new_source")]
    textos += [e.get("new_string") for e in entrada.get("edits") or [] if isinstance(e, dict)]
    texto = "\n".join(t for t in textos if isinstance(t, str))
    if not texto:
        return
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pii
    valores = pii.ler_segredos(ctx.arquivo_env) if segredos else []
    if not ips:  # fora da área pública, só segredo que não casa palavra comum
        valores = [(chave, valor) for chave, valor in valores if pii.segredo_forte(valor)]
    achados = pii.achar(texto, valores, ids=ids, ips=ips)
    if achados:
        raise Bloqueio(f"dado pessoal em {caminho} (repositório público): " + "; ".join(achados),
                       "IDs fictícios abaixo da base 76561197960265728 (76561190000000001, "
                       "76561190000000002...), 127.0.0.1/0.0.0.0 ou um <marcador>; versão? "
                       "escreva v1.40.9.3; segredo nunca entra no repositório")


# ------------------------------------------------ navegador do Claude

def _avaliar_preview(entrada, ctx):
    """preview_start {name}: a configuração do .claude/launch.json não pode
    subir servidor na 8000 (a wizard-web sobe). {url} só abre uma aba."""
    nome = entrada.get("name")
    if not isinstance(nome, str) or not nome:
        return
    raizes = [_raiz_git(ctx.cwd)[0] if ctx.cwd else None,
              _absoluto(os.environ.get("CLAUDE_PROJECT_DIR", ""), None)]
    for raiz in raizes:
        if not raiz:
            continue
        try:
            with open(raiz + "/.claude/launch.json", encoding="utf-8") as arq:
                configuracoes = json.load(arq).get("configurations") or []
        except (OSError, ValueError, AttributeError):
            continue
        for conf in configuracoes:
            if isinstance(conf, dict) and conf.get("name") == nome:
                if _int(conf.get("port"), None) == PORTA_DO_VICTOR:
                    raise Bloqueio(f"preview_start {nome!r} sobe servidor na porta 8000, que é "
                                   "do Victor",
                                   "uma configuração na 8010 com banco de fixture (peça ao "
                                   "Victor pra criar no launch.json)")
                programa = conf.get("runtimeExecutable")
                if isinstance(programa, str) and programa:
                    filho = ctx.filho()
                    filho.cwd = raiz
                    _analisar_palavras([programa] + [str(a) for a in conf.get("runtimeArgs")
                                                     or []], "bash", filho)
                return


# ------------------------------------------------------------- decisão

def avaliar(evento, ctx):
    """Levanta Bloqueio se a chamada tem que ser barrada."""
    ferramenta = evento.get("tool_name")
    entrada = evento.get("tool_input") or {}
    if ferramenta in DIALETO:
        comando = entrada.get("command")
        if not isinstance(comando, str):
            raise TypeError("tool_input.command ausente")
        analisar_comando(comando, DIALETO[ferramenta], ctx)
    elif ferramenta in FERRAMENTAS_DE_ARQUIVO:
        _avaliar_arquivo(ferramenta, entrada, ctx)
    elif isinstance(ferramenta, str) and ferramenta.endswith("__preview_start"):
        _avaliar_preview(entrada, ctx)


def decidir(bruto, principal=PRINCIPAL, preflight=None, arquivo_env=None):
    """(código de saída, stderr, stdout) para o evento JSON `bruto`."""
    ferramenta, comando = None, None
    try:
        evento = json.loads(bruto) if isinstance(bruto, str) else bruto
        ferramenta = evento.get("tool_name")
        comando = (evento.get("tool_input") or {}).get("command")
        ctx = Contexto(evento.get("cwd") or os.getcwd(), principal, preflight, arquivo_env)
        avaliar(evento, ctx)
    except Bloqueio as b:
        return 2, (f"guarda (B0.5) bloqueou: {b.motivo}.\n"
                   f"Em vez disso: {b.alternativa}.\n"
                   "Se a regra estiver errada para este caso, pare e peça ao Victor; "
                   "não contorne a guarda (AGENTS.md).\n"), ""
    except Exception as exc:
        texto = comando if isinstance(comando, str) else (bruto if isinstance(bruto, str) else "")
        if ferramenta not in FERRAMENTAS_DE_ARQUIVO and _SENSIVEL.search(texto or ""):
            return 2, ("guarda (B0.5) bloqueou por falha fechada: erro interno "
                       f"({exc.__class__.__name__}: {exc}) ao analisar um comando que menciona "
                       "docker, git ou pip.\nEm vez disso: rode um comando por vez, sem aninhar "
                       "shell dentro de shell; se ainda falhar, peça ao Victor.\n"), ""
        aviso = {"systemMessage": f"guarda (B0.5): erro interno ({exc.__class__.__name__}); "
                                  f"{ferramenta or 'ferramenta'} liberado sem análise."}
        return 0, "", json.dumps(aviso, ensure_ascii=False)
    return 0, "", ""


def main():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    bruto = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    codigo, erro, saida = decidir(bruto)
    if erro:
        sys.stderr.write(erro)
    if saida:
        sys.stdout.write(saida)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
