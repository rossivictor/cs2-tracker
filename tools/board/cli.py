"""
Linha de comando do board (card H1.3). Uso e regras: `USO`, abaixo.

Agente em worktree grava o board só por aqui: o vault fica no checkout
principal, fora do git, e o Edit fora do worktree é recusado. O carimbo do
`## Histórico` vem do relógio e do --papel, não da cabeça de quem escreve:
entrada que já chega carimbada é recusada.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .frontmatter import acrescentar_historico, definir_propriedade, ler_frontmatter
from .modelo import (
    CAMPO_ID,
    EXECUTORES,
    PAPEIS,
    STATUS,
    Cartao,
    ErroBoard,
    Problema,
    Quadro,
    bloqueia,
    carregar,
    fila,
    ordem_de,
    planejar_criacao,
    reclassificar,
    rotulo_ordem,
    status_de,
    validar,
    wikilink,
)

PRINCIPAL = Path("C:/Users/Victor/Projetos/cs2-tracker")
BOARD_PADRAO = PRINCIPAL / "docs" / "board-cs2"
# Como o Histórico registra o comando: sem "python", que empurraria o agente para o
# interpretador do sistema (3.14) em vez do .venv pelo caminho absoluto (AGENTS.md).
COMANDO = "tools.board"

USO = f"""Uso: C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board <comando>
(da raiz do checkout principal ou de uma worktree)

  validar [--tudo]                 confere valores exatos, Ordem x nome do arquivo e wikilinks
                                   dos cards abertos (--tudo: com os concluídos); sai 1 com erro
  fila [--agora]                   "Pronta para começar" na ordem de despacho (Reprovada, depois
                                   Ordem); trilho ocupado esconde o caminho de jogo; --agora roda
                                   o preflight: 3 (ou código que conta como 3) mostra só
                                   Verificação Offline; 4 marca Servidor e Partida como só do
                                   papel servidor
  reclassificar --concluido=<ref>  depois do merge: recalcula os dependentes (Backlog também,
                                   inclusive o estacionado de propósito)
  criar --spec=<arquivo.json>      cria card(s) a partir de um objeto ou lista; o lote inteiro
                                   é conferido antes de gravar
  mover --card=<ref> [--status=<Status>] [--branch=<nome>|null] [--pr=<url>|null]
        [--candidato=<tag>|null] [--custo=<tokens>|null] [--reprovada=true|false]
        [--reprovacao] [--devolucao] [--executor=<Executor>]
        [--texto=<entrada> | --arquivo=<caminho>]
                                   grava campos de um card, com a entrada no ## Histórico;
                                   recusa sem gravar só o que criaria erro novo no card
  historico --card=<ref> (--texto=<entrada> | --arquivo=<caminho>)
                                   só acrescenta a entrada no ## Histórico

  <ref>: Ordem (12 ou 11,5), {CAMPO_ID} do plano (B1.3r) ou nome do arquivo.
  <entrada>: só o texto. O CLI carimba "- **DD/MM/AAAA HH:MM · <papel>** —" com o relógio
             e o --papel; entrada que já vem carimbada é recusada. Linhas seguintes sem
             recuo ganham dois espaços, para ficarem dentro da entrada.
  --seco       mostra o que faria, sem gravar (reclassificar, criar, mover, historico);
               no reclassificar, simula o card como concluído mesmo antes do merge
  --papel=<{' | '.join(PAPEIS)}>  quem assina a entrada (padrão: TM; PM no criar)
  --board=<pasta>                  padrão: {BOARD_PADRAO.as_posix()}"""

_COMUNS = {"board="}
_ESCRITA = {"seco", "papel="}
_FLAGS: Dict[str, set] = {
    "validar": {"tudo"},
    "fila": {"agora"},
    "reclassificar": {"concluido="} | _ESCRITA,
    "criar": {"spec="} | _ESCRITA,
    "mover": {"card=", "status=", "branch=", "pr=", "candidato=", "custo=", "reprovada=",
              "reprovacao", "devolucao", "executor=", "texto=", "arquivo="} | _ESCRITA,
    "historico": {"card=", "texto=", "arquivo="} | _ESCRITA,
}
_SIGNIFICADO_PREFLIGHT = {
    0: "livre",
    3: "Victor jogando",
    4: "janela aberta: só o papel servidor mexe no que é vivo",
}


def ler_argumentos(argv: List[str]):
    """Devolve (comando, opções). Opção com valor é sempre `--nome=valor`."""
    soltos = [a for a in argv if not a.startswith("--")]
    if not soltos:
        return None, {}
    comando = soltos[0]
    if comando not in _FLAGS:
        raise ErroBoard(f'comando desconhecido "{comando}"')
    if len(soltos) > 1:
        raise ErroBoard(f'argumento solto "{soltos[1]}": os valores vão em --nome=valor')
    aceitas = _FLAGS[comando] | _COMUNS
    opcoes: Dict[str, object] = {}
    for arg in argv:
        if not arg.startswith("--"):
            continue
        nome, igual, valor = arg[2:].partition("=")
        if f"{nome}=" in aceitas and igual:
            opcoes[nome] = valor
        elif f"{nome}=" in aceitas:
            raise ErroBoard(f"--{nome} precisa de valor: --{nome}=<valor>")
        elif nome in aceitas and not igual:
            opcoes[nome] = True
        elif nome in aceitas:
            raise ErroBoard(f"--{nome} não leva valor")
        else:
            raise ErroBoard(f"opção desconhecida --{nome} para {comando}")
    return comando, opcoes


# Entrada que já começa carimbada: `- **<qualquer coisa>** —`.
_CABECALHO = re.compile(r"^\s*[-*+]\s+\*\*[^*\n]*\*\*\s*[—–-]")
# Item com data e hora em negrito em qualquer linha: é a forma do carimbo, recuada ou não.
_CARIMBO_NO_MEIO = re.compile(r"^\s*[-*+]\s+\*\*\s*\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}")


def entrada_historico(texto: str, carimbo: str, papel: str) -> str:
    """
    Monta a entrada `- **DD/MM/AAAA HH:MM · <papel>** — ...` sempre com o
    carimbo do CLI (relógio e --papel já validado). Entrada que já chega
    carimbada é recusada: data, hora e papel escritos por quem chama não
    entram no Histórico. Linha seguinte sem recuo ganha dois espaços, para
    ficar dentro da entrada e não virar entrada nova nem seção nova.
    """
    linhas = texto.rstrip().splitlines()
    while linhas and not linhas[0].strip():
        linhas.pop(0)
    if not linhas:
        raise ErroBoard("a entrada do Histórico está vazia")
    if _CABECALHO.match(linhas[0]) or any(_CARIMBO_NO_MEIO.match(l) for l in linhas):
        raise ErroBoard(
            "a entrada já vem carimbada (- **... · <papel>** —). O carimbo é do CLI, com "
            "a data e a hora do relógio e o --papel: mande só o texto")
    primeira, *resto = linhas
    resto = [l if not l.strip() or l[0] in " \t" else f"  {l}" for l in resto]
    return "\n".join([f"- **{carimbo} · {papel}** — {primeira.strip()}"] + resto)


def _achar_preflight() -> Path:
    local = Path(__file__).resolve().parents[1] / "preflight.py"
    return local if local.exists() else PRINCIPAL / "tools" / "preflight.py"


def rodar_preflight() -> int:
    """Código do tools/preflight.py; se nem der para rodar, 3 (falha segura)."""
    try:
        proc = subprocess.run([sys.executable, str(_achar_preflight())],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return 3
    return proc.returncode


def _gravar_lote(itens: Sequence[Tuple[Path, str]]) -> None:
    """
    Grava tudo ou nada, até onde o disco deixa: cada texto vai primeiro para
    um temporário de nome curto na mesma pasta e só depois, com todos
    escritos, os os.replace trocam os arquivos. Falha na primeira fase apaga
    os temporários e não mexe em card nenhum; falha na troca diz quais
    arquivos já foram trocados.
    """
    temporarios: List[Tuple[Path, Path]] = []
    try:
        for caminho, texto in itens:
            temporario = caminho.parent / f".board-{uuid.uuid4().hex[:12]}.tmp"
            temporarios.append((temporario, caminho))
            with open(temporario, "w", encoding="utf-8", newline="") as arquivo:
                arquivo.write(texto)
    except OSError as caught:
        for temporario, _ in temporarios:
            try:
                temporario.unlink()
            except OSError:
                pass
        raise ErroBoard(f"nada gravado: {caught}") from None
    trocados: List[str] = []
    for indice, (temporario, caminho) in enumerate(temporarios):
        try:
            os.replace(temporario, caminho)
        except OSError as caught:
            for resto, _ in temporarios[indice:]:
                try:
                    resto.unlink()
                except OSError:
                    pass
            ja = ", ".join(trocados) if trocados else "nenhum"
            raise ErroBoard(f"gravação interrompida em {caminho.name}: {caught}. "
                            f"Já gravados: {ja}") from None
        trocados.append(caminho.name)


def _gravar(caminho: Path, texto: str) -> None:
    _gravar_lote([(caminho, texto)])


def _ler_utf8(caminho: Path, o_que: str) -> str:
    """Texto de arquivo do usuário (spec, --arquivo), sem o BOM do PowerShell 5.1."""
    try:
        return caminho.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as caught:
        raise ErroBoard(f"{o_que} {caminho.as_posix()} não é UTF-8 "
                        f"(posição {caught.start}): regrave em UTF-8") from None


def _nulo_ou_texto(valor: str) -> Optional[str]:
    return None if valor in ("", "null") else valor


def main(argv: Optional[List[str]] = None, *,
         agora: Callable[[], datetime] = datetime.now,
         preflight: Callable[[], int] = rodar_preflight,
         log: Callable[[str], None] = print,
         erro: Optional[Callable[[str], None]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if erro is None:
        def erro(linha: str) -> None:
            print(linha, file=sys.stderr)
    try:
        comando, opcoes = ler_argumentos(argv)
        if comando is None:
            log(USO)
            return 1
        pasta = Path(str(opcoes.get("board", BOARD_PADRAO)))
        if not pasta.is_dir():
            raise ErroBoard(f"board não encontrado em {pasta.as_posix()}. Passe --board=<pasta>.")
        papel = str(opcoes.get("papel", "PM" if comando == "criar" else "TM"))
        if papel not in PAPEIS:
            raise ErroBoard(f'--papel "{papel}" fora da lista ({" · ".join(PAPEIS)})')
        seco = bool(opcoes.get("seco"))
        carimbo = agora().strftime("%d/%m/%Y %H:%M")
        quadro = carregar(pasta)
        if comando != "validar":  # o validar já lista os ignorados
            for p in quadro.ignorados:
                erro(f"[board] aviso · {p.mensagem}")
        executar = {
            "validar": _validar, "fila": _fila, "reclassificar": _reclassificar,
            "criar": _criar, "mover": _mover, "historico": _mover,
        }[comando]
        return executar(comando=comando, opcoes=opcoes, quadro=quadro, pasta=pasta,
                        papel=papel, seco=seco, carimbo=carimbo,
                        preflight=preflight, log=log, erro=erro)
    except (ErroBoard, OSError, ValueError) as caught:
        erro(f"[board] {caught}")
        return 1


def _validar(*, opcoes, quadro: Quadro, log, **_) -> int:
    problemas = validar(quadro, tudo=bool(opcoes.get("tudo")))
    erros = [p for p in problemas if p.nivel == "erro"]
    for p in problemas:
        log(f"{'ERRO ' if p.nivel == 'erro' else 'aviso'} · {p.cartao} · {p.mensagem}")
    log(f"{len(quadro.cartoes)} cards · {len(erros)} erro(s) · "
        f"{len(problemas) - len(erros)} aviso(s)")
    return 1 if erros else 0


def _ordem(cartao: Cartao) -> str:
    ordem = ordem_de(cartao)
    return "?" if ordem is None else rotulo_ordem(ordem)


def _curto(cartao: Cartao) -> str:
    return f"{_ordem(cartao)} · {cartao.props.get(CAMPO_ID)}"


def _fila(*, opcoes, quadro: Quadro, preflight, log, **_) -> int:
    codigo = bruto = None
    if opcoes.get("agora"):
        # Qualquer código fora de 0, 3 e 4 conta como 3 (AGENTS.md, "Preflight").
        bruto = preflight()
        codigo = bruto if bruto in _SIGNIFICADO_PREFLIGHT else 3
    resultado = fila(quadro, codigo)
    if not resultado.trilho:
        log("Trilho: livre")
    else:
        ocupantes = ", ".join(f"{_curto(c)} ({status_de(c)})" for c in resultado.trilho)
        log(f"Trilho: ocupado por {ocupantes}; {len(resultado.fora_pelo_trilho)} card(s) "
            "de caminho de jogo fora da fila")
    if len(resultado.trilho) > 1:
        log(f"TRILHO VIOLADO: {len(resultado.trilho)} cards de caminho de jogo em curso "
            "(máx. 1; exceção só com evidências disjuntas justificadas no card)")
    if codigo is not None:
        significado = (_SIGNIFICADO_PREFLIGHT[codigo] if bruto == codigo
                       else f"código {bruto} conta como 3: {_SIGNIFICADO_PREFLIGHT[3]}")
        if codigo == 0:
            filtro = ""
        elif codigo == 4:
            filtro = (f"; {len(resultado.so_servidor)} card(s) de Servidor ou Partida só "
                      "para o papel servidor")
        else:
            filtro = f"; só Offline, {len(resultado.fora_pelo_preflight)} card(s) fora da fila"
        log(f"Preflight {bruto} ({significado}){filtro}")
    for cartao in resultado.cartoes:
        props = cartao.props
        marcas = ""
        if props.get("Caminho de jogo") is True:
            marcas += " · caminho de jogo"
        if props.get("Reprovada") is True:
            marcas += f" · Reprovada {props.get('Reprovações') or 0}x"
        if cartao in resultado.so_servidor:
            marcas += " · só papel servidor"
        log(f"{_curto(cartao)} · {props.get('Verificação')} · {props.get('Executor')} · "
            f"{props.get('Camada')}{marcas} · {cartao.nome}")
    log(f'{len(resultado.cartoes)} card(s) na fila de "Pronta para começar"')
    return 0


def _reclassificar(*, opcoes, quadro: Quadro, papel, seco, carimbo, log, **_) -> int:
    ref = opcoes.get("concluido")
    if not ref:
        raise ErroBoard(f"informe --concluido=<Ordem, {CAMPO_ID} ou nome do card que foi para "
                        "Concluída>")
    concluido = quadro.resolver(str(ref))
    if status_de(concluido) != "Concluída":
        if not seco:
            raise ErroBoard(f'{concluido.nome} está em "{status_de(concluido)}". '
                            "Mova para Concluída antes de reclassificar.")
        # Prever a promoção antes do merge é o uso do --seco: simula, não grava.
        log(f'(simulação: {concluido.nome} está em "{status_de(concluido)}"; '
            "calculado como se estivesse em Concluída)")
        concluido.props["Status"] = "Concluída"
    mudancas = reclassificar(quadro, concluido)
    gravar: List[Tuple[Path, str]] = []
    for m in mudancas:
        aviso = " · PREENCHA O Executor" if m.sem_executor else ""
        log(f"{_ordem(m.cartao)} · {m.de} → {m.para}{aviso} · "
            f"{m.cartao.nome}")
        if seco:
            continue
        motivo = ("sem dependência pendente" if not m.pendentes
                  else "pendente: " + ", ".join(wikilink(n) for n in m.pendentes))
        texto = definir_propriedade(m.cartao.texto, "Status", m.para)
        texto = acrescentar_historico(texto, (
            f"- **{carimbo} · {papel}** — Reclassificado de `{m.de}` para `{m.para}` com a "
            f"conclusão do {wikilink(concluido.nome)} ({motivo}). Feito por "
            f"`{COMANDO} reclassificar`."))
        gravar.append((m.cartao.caminho, texto))
    if not seco:
        _gravar_lote(gravar)
        for m in mudancas:
            relido = ler_frontmatter(m.cartao.caminho.read_bytes().decode("utf-8")) or {}
            if relido.get("Status") != m.para:
                raise ErroBoard(f"releitura de {m.cartao.nome} divergiu: {relido.get('Status')}")
    log(f"{len(mudancas)} card(s) reclassificado(s){' (seco: nada gravado)' if seco else ''}")
    return 0


def _criar(*, opcoes, quadro: Quadro, pasta: Path, papel, seco, carimbo, log, **_) -> int:
    caminho_spec = opcoes.get("spec")
    if not caminho_spec:
        raise ErroBoard("informe --spec=<arquivo.json> com um card ou uma lista de cards")
    try:
        lido = json.loads(_ler_utf8(Path(str(caminho_spec)), "a spec"))
    except json.JSONDecodeError as caught:
        raise ErroBoard(f"spec não é JSON válido: {caught}") from None
    specs = lido if isinstance(lido, list) else [lido]
    entrada = (f"- **{carimbo} · {papel}** — Card criado por `{COMANDO} criar`. Status "
               "inicial: `{status}` ({pendentes} dependência(s) pendente(s)).")

    # Planeja o lote inteiro antes de gravar (título, Ordem, caminho, dependências), e
    # _gravar_lote grava tudo ou nada: spec ruim no meio não deixa board pela metade.
    planejados = []
    for spec in specs:
        plano = planejar_criacao(quadro, spec, entrada, pasta=pasta)
        quadro.add(plano.cartao)
        for dep in plano.atualiza_bloqueia:
            nomes = bloqueia(dep) + [plano.cartao.nome]
            dep.props["Bloqueia"] = [wikilink(n) for n in dict.fromkeys(nomes)]
            dep.texto = definir_propriedade(dep.texto, "Bloqueia", dep.props["Bloqueia"])
        planejados.append(plano)

    tocados: Dict[Path, Cartao] = {}
    for plano in planejados:
        extra = (f" · Bloqueia atualizado em {len(plano.atualiza_bloqueia)}"
                 if plano.atualiza_bloqueia else "")
        log(f"{plano.status} · {plano.cartao.nome}{extra}")
        tocados[plano.cartao.caminho] = plano.cartao
        for dep in plano.atualiza_bloqueia:
            tocados[dep.caminho] = dep
    if not seco:
        _gravar_lote([(caminho, cartao.texto) for caminho, cartao in tocados.items()])
        for plano in planejados:
            relido = ler_frontmatter(plano.cartao.caminho.read_bytes().decode("utf-8")) or {}
            if relido.get("Status") != plano.status:
                raise ErroBoard(f"releitura de {plano.cartao.nome} divergiu")
    log(f"{len(planejados)} card(s) criado(s){' (seco: nada gravado)' if seco else ''}")
    return 0


def _ler_texto(opcoes) -> Optional[str]:
    if "texto" in opcoes and "arquivo" in opcoes:
        raise ErroBoard("use --texto ou --arquivo, não os dois")
    if "arquivo" in opcoes:
        return _ler_utf8(Path(str(opcoes["arquivo"])), "o --arquivo")
    return opcoes.get("texto")


def _contador(valor) -> int:
    return int(valor) if isinstance(valor, (int, float)) and not isinstance(valor, bool) else 0


def _mover(*, comando, opcoes, pasta: Path, quadro: Quadro, papel, seco, carimbo,
           log, erro, **_) -> int:
    ref = opcoes.get("card")
    if not ref:
        raise ErroBoard(f"informe --card=<Ordem, {CAMPO_ID} ou nome do card>")
    cartao = quadro.resolver(str(ref))
    texto_entrada = _ler_texto(opcoes)
    texto = cartao.texto
    mudancas: List[str] = []

    if comando == "historico":
        if texto_entrada is None or not texto_entrada.strip():
            raise ErroBoard("informe --texto=<entrada> ou --arquivo=<caminho>")
    else:
        campos = ("status", "branch", "pr", "candidato", "custo", "reprovada",
                  "reprovacao", "devolucao", "executor")
        if not any(c in opcoes for c in campos):
            raise ErroBoard("nada para mover: informe --status, --branch, --pr, --candidato, "
                            "--custo, --reprovada, --reprovacao, --devolucao ou --executor")
        if "executor" in opcoes:
            executor = str(opcoes["executor"])
            if executor not in EXECUTORES:
                raise ErroBoard(f'Executor "{executor}" fora da lista ({" · ".join(EXECUTORES)})')
            texto = definir_propriedade(texto, "Executor", executor)
            mudancas.append(f"Executor {executor}")
        if "status" in opcoes:
            status = str(opcoes["status"])
            if status not in STATUS:
                raise ErroBoard(f'Status "{status}" não é um dos oito: {" · ".join(STATUS)}')
            texto = definir_propriedade(texto, "Status", status)
            mudancas.append(f"{status_de(cartao)} → {status}")
        for opcao, chave in (("branch", "Branch"), ("pr", "PR"), ("candidato", "Candidato")):
            if opcao in opcoes:
                valor = _nulo_ou_texto(str(opcoes[opcao]))
                texto = definir_propriedade(texto, chave, valor)
                mudancas.append(f"{chave} {valor or 'null'}")
        if "custo" in opcoes:
            bruto = _nulo_ou_texto(str(opcoes["custo"]))
            if bruto is not None and not bruto.isdigit():
                raise ErroBoard(f'--custo precisa ser tokens (inteiro) ou null, recebido "{bruto}"')
            texto = definir_propriedade(texto, "Custo", None if bruto is None else int(bruto))
            mudancas.append(f"Custo {bruto or 'null'}")
        if "reprovada" in opcoes:
            reprovada = opcoes["reprovada"]
            if reprovada not in ("true", "false"):
                raise ErroBoard(f'--reprovada precisa ser true ou false, recebido "{reprovada}"')
            texto = definir_propriedade(texto, "Reprovada", reprovada == "true")
            mudancas.append(f"Reprovada {reprovada}")
        for opcao, chave in (("reprovacao", "Reprovações"), ("devolucao", "Devoluções")):
            if opcao in opcoes:
                atual = _contador(cartao.props.get(chave))
                texto = definir_propriedade(texto, chave, atual + 1)
                mudancas.append(f"{chave} {atual} → {atual + 1}")
    if texto_entrada is not None and texto_entrada.strip():
        texto = acrescentar_historico(texto, entrada_historico(texto_entrada, carimbo, papel))
        mudancas.append("entrada no Histórico")

    # Confere antes de gravar: só recusa (sem gravar nada) o erro que ESTE comando
    # criaria. Erro que o card já tinha vira aviso e não impede a gravação; sair 1
    # depois de gravar faria o agente repetir o comando e somar a reprovação duas vezes.
    novos = _erros_novos(quadro, cartao, texto)
    if novos:
        raise ErroBoard(f"nada gravado em {cartao.nome}: o card ficaria com erro novo: "
                        + "; ".join(p.mensagem for p in novos))
    log(f"{_ordem(cartao)} · {' · '.join(mudancas)} · {cartao.nome}"
        f"{' (seco: nada gravado)' if seco else ''}")
    if seco:
        return 0

    _gravar(cartao.caminho, texto)
    depois = carregar(pasta)
    relido = depois.get(cartao.nome)
    esperado = opcoes.get("status")
    if relido is None or (esperado is not None and status_de(relido) != esperado):
        raise ErroBoard(f"gravado, mas a releitura de {cartao.nome} divergiu: "
                        f"{None if relido is None else status_de(relido)}")
    log(f"gravado: {cartao.nome}")
    for p in validar(depois):
        if p.cartao != cartao.nome:
            continue
        ja = " (erro que o card já tinha; não impediu a gravação)" if p.nivel == "erro" else ""
        erro(f"[board] aviso · {p.cartao} · {p.mensagem}{ja}")
    return 0


def _problemas_de(quadro: Quadro, nome: str) -> List[Problema]:
    return [p for p in validar(quadro, tudo=True) if p.cartao == nome]


def _erros_novos(quadro: Quadro, cartao: Cartao, texto: str) -> List[Problema]:
    """Erros que o card teria com `texto` e não tem hoje (Concluída incluída)."""
    ja = {p.mensagem for p in _problemas_de(quadro, cartao.nome) if p.nivel == "erro"}
    novo = Cartao(cartao.nome, cartao.caminho, ler_frontmatter(texto) or {}, texto)
    simulado = Quadro([novo if c is cartao else c for c in quadro.cartoes])
    return [p for p in _problemas_de(simulado, cartao.nome)
            if p.nivel == "erro" and p.mensagem not in ja]
