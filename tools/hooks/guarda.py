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
  - docker volume rm/remove/prune e docker system prune;
  - git clean (qualquer forma) e git stash --all (tira os ignorados do disco);
  - pip install/uninstall, python -m pip, uv pip install/uninstall/sync;
  - uvicorn, http.server e afins ouvindo na 8000 (a porta do Victor),
    inclusive pela porta padrão; docker run -p 8000:...;
  - escrita em cs2_tracker.db (qualquer caminho; apagar o lixo de uma
    worktree pode), .env, data/profile.json, docker/events-live/**,
    C:/cs2server/** e o volume do Docker, por ferramenta de arquivo,
    redirecionamento ou comando (rm, cp, mv, tee, Set-Content...);
  - docker logs / compose logs quando tools/preflight.py não devolve 0 ou 4;
  - no Write/Edit em docs/** e tests/fixtures/**, dado pessoal e segredo
    (tools/hooks/pii.py).

Falha fechada com escopo: exceção ao analisar um comando que menciona
docker, git ou pip sai com 2. Qualquer outro erro interno sai com 0 e um
aviso (systemMessage): bug no hook não pode travar o trabalho normal.

Só biblioteca padrão. Sem `docker logs` no comando, fica abaixo de 150 ms.
"""
from __future__ import annotations

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
_SENSIVEL = re.compile(r"docker|git|pip", re.IGNORECASE)


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
                f"{p}/docker/events-live", "c:/cs2server"]


ALT_BANCO = ("banco em tmp_path ou fixture; dado real só numa cópia mode=ro pedida ao PM "
             "(apagar o cs2_tracker.db que a suíte cria na SUA worktree pode, pelo nome)")
ALT_ENV = "use o .env.example; o .env é do Victor, e só ele edita"
ALT_PERFIL = "perfil em tmp_path nos testes"
ALT_EVENTS = "fixture anonimizada em tests/fixtures/"
ALT_CS2SERVER = "nada: C:/cs2server é a única semente de recuperação do servidor"
ALT_VOLUME = "nada: o volume cs2-tracker_cs2-data não é reproduzível"
_EVENTS_LIVE = re.compile(r"(^|/)docker/events-live(/|$)")


def _motivo_protegido(bruto, ctx, modo="escrita"):
    """(motivo, alternativa) se `bruto` é caminho protegido, senão None.
    modo: escrita, apagar (o cs2_tracker.db fora do principal pode) ou mover."""
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
    return None


def _checar_caminho(alvo, ctx, modo, acao):
    achado = _motivo_protegido(alvo, ctx, modo)
    if achado:
        raise Bloqueio(f"{acao} em {alvo}: {achado[0]}", achado[1])


# ----------------------------------------------------------- tokenização

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

    def __init__(self, texto, dialeto):
        self.t = texto
        self.n = len(texto)
        self.i = 0
        self.d = dialeto
        self.heredocs = []

    def _prox(self, k=1):
        j = self.i + k
        return self.t[j] if j < self.n else "\0"

    def ler(self, fecha=False):
        toks, pal, anin = [], [], []
        tem = False
        prof = 0
        t, n, d = self.t, self.n, self.d

        def fechar():
            nonlocal pal, anin, tem
            if tem:
                toks.append(_Tok("p", "".join(pal), anin))
            elif anin:
                toks.append(_Tok("a", "", anin))
            pal, anin, tem = [], [], False

        def separar():
            fechar()
            toks.append(_SEP)

        while self.i < n:
            c = t[self.i]
            prox = self._prox()
            if c in " \t\r":
                fechar()
                self.i += 1
            elif c == "\n":
                separar()
                self.i += 1
                if self.heredocs:
                    self._corpos(toks)
            elif c == "#" and not tem and d != "cmd":
                fim = t.find("\n", self.i)
                self.i = n if fim < 0 else fim
            elif (d == "bash" and c == "\\") or (d == "ps" and c == "`") or (d == "cmd" and c == "^"):
                if prox == "\r" and self._prox(2) == "\n":
                    self.i += 3
                elif prox == "\n":
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
                self.i += 1
            else:
                pal.append(c)
                tem = True
                self.i += 1
        fechar()
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
        fim_linha = t.find("\n", self.i)
        if fim_linha < 0 or t[self.i + 2:fim_linha].strip():
            return False
        fim = t.find("\n" + aspas + "@", fim_linha)
        corpo = t[fim_linha + 1:] if fim < 0 else t[fim_linha + 1:fim]
        self.i = n if fim < 0 else fim + 3
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
    _analisar_tokens(_Leitor(texto, dialeto).ler(), dialeto, ctx)


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
                _checar_caminho(alvo, ctx, "escrita", f"redirecionamento {op}")
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


def _programa(palavra):
    nome = palavra.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()
    for ext in _EXTENSOES:
        if nome.endswith(ext):
            return nome[:-len(ext)]
    return nome


def _analisar_palavras(palavras, dialeto, ctx, env_local=None):
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
            atrib[m.group(1).upper()] = m.group(2)
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
            if bruto.lower().startswith("$env:"):
                ctx.env[m.group(1).upper()] = " ".join(direita)
            if direita:  # $x = docker ... executa o lado direito
                _analisar_palavras(direita, dialeto, ctx)
            return
    prog = _programa(bruto)
    if ("$" in bruto or "`" in bruto) and prog not in _TRATADORES:
        prog = next((k for k in _DINAMICOS if k in bruto.lower()), prog)
    if _RE_PYTHON.match(prog):
        prog = "python"
    elif _RE_PIP.match(prog):
        prog = "pip"
    tratador = _TRATADORES.get(prog)
    if tratador:
        tratador(prog, args, dialeto, ctx, env)
    if prog in _TODOS_ESCRITORES:  # perl tem os dois: -e e -i
        for alvo, modo in _alvos_de_escrita(prog, args):
            _checar_caminho(alvo, ctx, modo, prog)
    if prog not in _SEM_PORTA:
        _porta_generica(prog, args)


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
_COPIAR = {"cp", "copy", "copy-item", "cpi", "xcopy", "robocopy", "install", "rsync", "scp"}
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
    if sub == "logs":
        _checar_preflight(ctx, "docker compose logs")


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
    if sub == "clean":
        raise Bloqueio("git clean apaga não rastreados e ignorados: banco, events-live, .env e "
                       "a DLL (critic, risco 1)",
                       "apague só o que você criou, pelo nome")
    if sub == "stash" and any(a in ("-a", "--all") or (a.startswith("-") and not a.startswith("--")
                                                       and a[1:].isalpha() and "a" in a[1:])
                              for a in resto):
        raise Bloqueio("git stash --all tira do disco os ignorados (banco, events-live, .env)",
                       "git stash push -m <tag> só com o que é rastreado, ou um commit WIP")


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
    (re.compile(r"\bpip\d*(?:\.exe)?\W{1,6}(?:un)?install\b", re.I), "pip install"),
]


def _rede_codigo(codigo, origem):
    """Código inline (python -c, node -e...) não é analisável: procura o texto."""
    for regex, oque in _REDE:
        if regex.search(codigo or ""):
            raise Bloqueio(f"código inline ({origem}) chama {oque}",
                           "rode o comando direto, onde a guarda vê, e só o que as regras permitem")


def _h_python(prog, args, dialeto, ctx, env):
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-m" or (a.startswith("-m") and len(a) > 2 and not a.startswith("--")):
            modulo = (a[2:] if len(a) > 2 else (args[i + 1] if i + 1 < len(args) else "")).lower()
            resto = args[i + 1:] if len(a) > 2 else args[i + 2:]
            if modulo in ("pip", "pip.__main__"):
                _h_pip("pip", resto, dialeto, ctx, env)
            elif modulo in ("http.server", "simplehttpserver"):
                _checar_servidor("http.server", resto, env)
            elif modulo == "django":
                _checar_servidor("django-admin", resto, env)
            elif modulo in _SERVIDORES:
                _checar_servidor(modulo, resto, env)
            else:
                _porta_generica(modulo, resto)
            return
        if a == "-c" or (a.startswith("-c") and len(a) > 2 and not a.startswith("--")):
            _rede_codigo(a[2:] if len(a) > 2 else (args[i + 1] if i + 1 < len(args) else ""),
                         "python -c")
            return
        if a in ("-W", "-X", "--check-hash-based-pycs"):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        if _programa(a) == "manage.py":
            _checar_servidor("django-admin", args[i + 1:], env)
        return


def _h_inline(prog, args, dialeto, ctx, env):
    for opcao in ("-e", "-E", "--eval", "-p", "--print", "-r"):
        for codigo in _valores_opcao(args, opcao):
            _rede_codigo(codigo, f"{prog} {opcao}")
    if prog == "php":
        _checar_servidor("php", args, env)


# ------------------------------------------------------------ servidores

_SERVIDORES = {"uvicorn", "gunicorn", "hypercorn", "daphne", "fastapi", "flask", "mkdocs",
               "django-admin", "http-server", "serve", "live-server"}
_SEM_PORTA = {"git", "gh", "grep", "rg", "findstr", "select-string", "sls", "echo", "printf",
              "write-output", "write-host", "sed", "awk", "cat", "type"}


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
                texto = base64.b64decode(args[i + 1] if i + 1 < len(args) else "").decode("utf-16-le")
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
}


def _embrulho(prog, args, dialeto, ctx, env):
    """sudo, nohup, xargs, timeout...: o comando de verdade vem depois das opções."""
    i = _primeiro_nao_opcao(args, _EMBRULHO_VALOR.get(prog, ()))
    if prog == "timeout" and i < len(args):
        i += 1  # a duração
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


_TRATADORES = {
    "docker": _h_docker, "docker-compose": _h_compose, "git": _h_git, "pip": _h_pip,
    "python": _h_python, "uv": _h_uv,
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
    "export": _exportar, "declare": _exportar, "typeset": _exportar,
}
for _nome in _SERVIDORES:
    _TRATADORES[_nome] = _h_servidor
for _nome in ("sudo", "nohup", "time", "command", "builtin", "exec", "nice", "timeout", "stdbuf",
              "xargs", "watch", "winpty", "unbuffer", "call", "npx", "bunx", "pnpx", "uvx",
              "poetry", "pipenv", "pipx", "."):
    _TRATADORES[_nome] = _embrulho


# -------------------------------------------------- ferramentas de arquivo

def _em_area_publica(caminho, ctx):
    absoluto = _absoluto(caminho, ctx.cwd)
    raiz = _raiz_git(absoluto)[0] if absoluto else None
    if raiz:
        relativo = absoluto[len(raiz.rstrip("/")) + 1:].lower()
        return relativo.startswith(("docs/", "tests/fixtures/"))
    chave = "/" + _barras(caminho).lower()
    return "/docs/" in chave or "/tests/fixtures/" in chave


def _avaliar_arquivo(ferramenta, entrada, ctx):
    caminho = entrada.get("file_path") or entrada.get("notebook_path") or ""
    if not isinstance(caminho, str) or not caminho:
        return
    _checar_caminho(caminho, ctx, "escrita", ferramenta)
    if not _em_area_publica(caminho, ctx):
        return
    textos = [entrada.get("content"), entrada.get("new_string"), entrada.get("new_source")]
    textos += [e.get("new_string") for e in entrada.get("edits") or [] if isinstance(e, dict)]
    texto = "\n".join(t for t in textos if isinstance(t, str))
    if not texto:
        return
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pii
    achados = pii.achar(texto, pii.ler_segredos(ctx.arquivo_env))
    if achados:
        raise Bloqueio(f"dado pessoal em {caminho} (repositório público): " + "; ".join(achados),
                       "IDs fictícios (76561198000000001, 76561190000000001), 127.0.0.1/0.0.0.0 "
                       "ou um <marcador>; segredo nunca entra no repositório")


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
