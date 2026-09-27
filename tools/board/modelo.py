"""
Modelo do board: os valores exatos dos campos, o grafo de dependências, a
fila de despacho com o trilho único, a reclassificação depois do merge e o
plano de criação de card. Porte de `kalendas/scripts/lib/board.ts` com os
campos do cs2-tracker (card H1.3).

Os valores vêm do `board_schema` do plano de 2026-09-26
(C:/Users/Victor/cs2-tracker-backups/2026-09-26/temp-artifacts/eb5adec0/plan/all.json).
Quando um deles mudar lá, muda aqui junto. O ID do plano mora na
propriedade `Card` (B1.3r, P1.1a).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .frontmatter import (
    Valor,
    acrescentar_historico,
    formatar_frontmatter,
    ler_frontmatter,
)

STATUS = (
    "Backlog",
    "Bloqueada",
    "Pronta para começar",
    "Em andamento",
    "Em testes",
    "PR aberta",
    "Aguardando partida",
    "Concluída",
)
CAMADAS = (
    "Infra/Harness",
    "Bots/Servidor",
    "Captura",
    "Dados",
    "Orquestração",
    "TUI",
    "Web",
    "Docs/KB",
)
VERIFICACOES = ("Offline", "Servidor", "Partida")
EXECUTORES = ("Agente", "Humano", "Agente+Humano")
JANELAS = ("nenhuma", "pré", "pós", "dados")
PARTIDAS = ("—", "leve", "MD3", "MD3-browser")
PAPEIS = ("PM", "TM", "dev", "QA", "servidor")

# Só estes o reclassificar move: card em andamento, em testes, com PR ou
# aguardando partida não é dele.
RECLASSIFICAVEIS = ("Backlog", "Bloqueada", "Pronta para começar")
# Trilho único (Q6=A): no máximo um card de caminho de jogo nestes status.
NO_TRILHO = ("Em andamento", "Em testes", "PR aberta", "Aguardando partida")

ID_CARD = re.compile(r"^[A-Z]\d+\.\d+[a-z]?$")
ID_SPRINT = re.compile(r"^[A-Z]\d+$")
# Caracteres que o Obsidian recusa em nome de arquivo ou que quebram o wikilink.
PROIBIDOS_NO_TITULO = re.compile(r'[\\/:*?"<>|\[\]#^]')
_PREFIXO_ORDEM = re.compile(r"^(\d+(?:,\d+)?) - ")
_ROLLBACK = re.compile(r"^##\s+Rollback\b", re.MULTILINE)


class ErroBoard(Exception):
    """Erro de uso ou de dado do board; a mensagem vai para o usuário."""


@dataclass
class Cartao:
    nome: str  # nome do arquivo sem .md: é o alvo do wikilink
    caminho: Optional[Path]
    props: Dict[str, Valor]
    texto: str


def alvo_do_link(link: str) -> str:
    achado = re.match(r"^\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]$", link.strip())
    return (achado.group(1) if achado else link).strip()


def wikilink(nome: str) -> str:
    return f"[[{nome}]]"


def ler_ordem(bruto) -> float:
    """`11,5`, `11.5` e 11.5 viram 11.5; inteiro volta int (12, não 12.0)."""
    if isinstance(bruto, bool):
        raise ErroBoard(f'Ordem inválida: "{bruto}"')
    if isinstance(bruto, (int, float)):
        valor = float(bruto)
    else:
        texto = str(bruto).strip().replace(",", ".")
        if not re.match(r"^-?\d+(\.\d+)?$", texto):
            raise ErroBoard(f'Ordem inválida: "{bruto}"')
        valor = float(texto)
    if not math.isfinite(valor):
        raise ErroBoard(f'Ordem inválida: "{bruto}"')
    return int(valor) if valor.is_integer() else valor


def rotulo_ordem(ordem) -> str:
    return str(ler_ordem(ordem)).replace(".", ",")


def _numero(valor: Valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def ordem_de(cartao: Cartao) -> Optional[float]:
    valor = cartao.props.get("Ordem")
    return valor if _numero(valor) else None


def _lista(cartao: Cartao, chave: str) -> List[str]:
    valor = cartao.props.get(chave)
    return [alvo_do_link(item) for item in valor] if isinstance(valor, list) else []


def depende_de(cartao: Cartao) -> List[str]:
    return _lista(cartao, "Depende de")


def bloqueia(cartao: Cartao) -> List[str]:
    return _lista(cartao, "Bloqueia")


def status_de(cartao: Cartao) -> str:
    valor = cartao.props.get("Status")
    return "" if valor is None else str(valor)


def caminho_de_jogo(cartao: Cartao) -> bool:
    return cartao.props.get("Caminho de jogo") is True


class Quadro:
    def __init__(self, cartoes: Iterable[Cartao]):
        self.cartoes: List[Cartao] = list(cartoes)
        self._por_nome = {c.nome: c for c in self.cartoes}

    def get(self, nome: str) -> Optional[Cartao]:
        return self._por_nome.get(nome)

    def add(self, cartao: Cartao) -> None:
        self.cartoes.append(cartao)
        self._por_nome[cartao.nome] = cartao

    def por_ordem(self, bruto) -> Cartao:
        ordem = ler_ordem(bruto)
        achados = [c for c in self.cartoes if ordem_de(c) == ordem]
        if not achados:
            raise ErroBoard(f"nenhum card com Ordem {rotulo_ordem(ordem)}")
        if len(achados) > 1:
            raise ErroBoard(f"mais de um card com Ordem {rotulo_ordem(ordem)}")
        return achados[0]

    def resolver(self, ref: str) -> Cartao:
        """Aceita `12`, `11,5`, o ID do plano (`B1.3r`), o nome ou o wikilink."""
        alvo = alvo_do_link(str(ref))
        pelo_nome = self.get(alvo)
        if pelo_nome is not None:
            return pelo_nome
        if ID_CARD.match(alvo):
            achados = [c for c in self.cartoes if c.props.get("Card") == alvo]
            if len(achados) == 1:
                return achados[0]
            raise ErroBoard(f"{'nenhum' if not achados else 'mais de um'} card com Card {alvo}")
        return self.por_ordem(alvo)

    def pendentes(self, cartao: Cartao) -> List[str]:
        """Dependências fora de `Concluída`. Link para card que não existe conta como pendente."""
        return [
            nome for nome in depende_de(cartao)
            if (dep := self.get(nome)) is None or status_de(dep) != "Concluída"
        ]

    def dependentes(self, nome: str) -> List[Cartao]:
        return [c for c in self.cartoes if nome in depende_de(c)]

    def no_trilho(self) -> List[Cartao]:
        """Cards de caminho de jogo entre Em andamento e Aguardando partida."""
        return sorted(
            (c for c in self.cartoes if caminho_de_jogo(c) and status_de(c) in NO_TRILHO),
            key=lambda c: ordem_de(c) or 0,
        )


def classificar(quadro: Quadro, cartao: Cartao) -> str:
    """
    Os limiares do `board_schema` (0 pendentes = Pronta; 1 = Bloqueada; 2 ou
    mais = Backlog), com o refinamento do kalendas: a única pendente que
    ainda tem pendente própria é uma cadeia, e conta como 2 (Backlog).
    """
    pendentes = quadro.pendentes(cartao)
    if not pendentes:
        return "Pronta para começar"
    if len(pendentes) == 1:
        dep = quadro.get(pendentes[0])
        if dep is not None and not quadro.pendentes(dep):
            return "Bloqueada"
    return "Backlog"


def carregar(pasta: Path) -> Quadro:
    cartoes = []
    for caminho in sorted(Path(pasta).glob("*.md")):
        texto = caminho.read_bytes().decode("utf-8")
        props = ler_frontmatter(texto)
        if props is None or "Status" not in props:
            continue
        cartoes.append(Cartao(caminho.stem, caminho, props, texto))
    return Quadro(cartoes)


# ---------------------------------------------------------------------------
# validar
# ---------------------------------------------------------------------------

@dataclass
class Problema:
    cartao: str
    nivel: str  # "erro" ou "aviso"
    mensagem: str


_LISTAS_FECHADAS = (
    ("Camada", CAMADAS),
    ("Verificação", VERIFICACOES),
    ("Executor", EXECUTORES),
    ("Janela", JANELAS),
    ("Partida", PARTIDAS),
)


def _mostrar(valor: Valor) -> str:
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    return str(valor)


def _checar_campos(cartao: Cartao, add) -> None:
    props = cartao.props
    status = status_de(cartao)
    if status not in STATUS:
        add("erro", f'Status "{status}" não é um dos oito')

    card = props.get("Card")
    if not isinstance(card, str) or not ID_CARD.match(card):
        add("erro", f'Card "{_mostrar(card)}" fora do formato do plano (ex.: B1.3r)')
    sprint = props.get("Sprint")
    if not isinstance(sprint, str) or not ID_SPRINT.match(sprint):
        add("erro", f'Sprint "{_mostrar(sprint)}" fora do formato (ex.: B1)')
    elif isinstance(card, str) and ID_CARD.match(card) and not card.startswith(f"{sprint}."):
        add("erro", f'Card "{card}" não é do Sprint "{sprint}"')

    for chave, valores in _LISTAS_FECHADAS:
        if chave not in props:
            add("erro", f"{chave} ausente ({' · '.join(valores)})")
        elif props[chave] not in valores or not isinstance(props[chave], str):
            add("erro", f'{chave} "{_mostrar(props[chave])}" fora da lista ({" · ".join(valores)})')

    for chave in ("Caminho de jogo", "Infra", "Reprovada"):
        if not isinstance(props.get(chave), bool):
            add("erro", f'{chave} "{_mostrar(props.get(chave))}" não é true/false')
    if props.get("Infra") is True and not caminho_de_jogo(cartao):
        add("erro", "Infra true exige Caminho de jogo true (infra é caminho de jogo)")

    for chave in ("Reprovações", "Devoluções"):
        valor = props.get(chave)
        if valor is not None and not (_numero(valor) and valor >= 0 and float(valor).is_integer()):
            add("erro", f'{chave} "{_mostrar(valor)}" não é vazio nem inteiro >= 0')
    custo = props.get("Custo")
    if custo is not None and not (_numero(custo) and custo >= 0):
        add("erro", f'Custo "{_mostrar(custo)}" não é vazio nem número de tokens')
    for chave in ("Branch", "PR", "Candidato"):
        valor = props.get(chave)
        if valor is not None and not isinstance(valor, str):
            add("erro", f'{chave} "{_mostrar(valor)}" não é texto nem null')
    for chave in ("Depende de", "Bloqueia"):
        if chave in props and not isinstance(props[chave], list):
            add("erro", f'{chave} "{_mostrar(props[chave])}" não é lista de wikilinks')

    ordem = ordem_de(cartao)
    if ordem is None:
        add("erro", f'Ordem "{_mostrar(props.get("Ordem"))}" não é número')
    else:
        prefixo = _PREFIXO_ORDEM.match(cartao.nome)
        if prefixo is None or ler_ordem(prefixo.group(1)) != ordem:
            add("erro", f"nome do arquivo não começa com a Ordem ({rotulo_ordem(ordem)} - …)")

    aberto = status != "Concluída"
    if aberto and caminho_de_jogo(cartao) and not _ROLLBACK.search(cartao.texto):
        add("erro", 'caminho de jogo sem a seção "## Rollback", que é obrigatória')
    if status == "Aguardando partida" and not caminho_de_jogo(cartao):
        add("aviso", '"Aguardando partida" é só de caminho de jogo; sem ele, o merge leva a Concluída')
    reprovacoes = props.get("Reprovações")
    if aberto and _numero(reprovacoes) and reprovacoes >= 2:
        add("aviso", f"{reprovacoes} reprovações: vai para a pauta do Victor")
    devolucoes = props.get("Devoluções")
    if aberto and _numero(devolucoes) and devolucoes >= 3:
        add("aviso", f"{devolucoes} devoluções: o card sai do sprint")


def validar(quadro: Quadro, tudo: bool = False) -> List[Problema]:
    """
    Por padrão só mostra problema de card aberto; `tudo` inclui os de card
    em Concluída. Erro faz o `validar` sair 1; aviso não.
    """
    problemas: List[Problema] = []
    ordens: Dict[float, List[str]] = {}
    ids: Dict[str, List[str]] = {}

    for cartao in quadro.cartoes:
        def add(nivel: str, mensagem: str, _nome: str = cartao.nome) -> None:
            problemas.append(Problema(_nome, nivel, mensagem))

        _checar_campos(cartao, add)
        ordem = ordem_de(cartao)
        if ordem is not None:
            ordens.setdefault(ordem, []).append(cartao.nome)
        card = cartao.props.get("Card")
        if isinstance(card, str):
            ids.setdefault(card, []).append(cartao.nome)

        for nome in depende_de(cartao):
            dep = quadro.get(nome)
            if dep is None:
                add("erro", f"Depende de [[{nome}]], que não existe")
            elif cartao.nome not in bloqueia(dep):
                add("aviso", f"Depende de [[{nome}]], mas ele não lista este card em Bloqueia")
        for nome in bloqueia(cartao):
            bloqueado = quadro.get(nome)
            if bloqueado is None:
                add("erro", f"Bloqueia [[{nome}]], que não existe")
            elif cartao.nome not in depende_de(bloqueado):
                add("aviso", f"Bloqueia [[{nome}]], mas ele não lista este card em Depende de")

        status = status_de(cartao)
        if status in RECLASSIFICAVEIS:
            esperado = classificar(quadro, cartao)
            # Backlog com a fila livre pode ser decisão do Victor: só avisa.
            if esperado != status:
                add("aviso", f'Status "{status}", mas as dependências dizem "{esperado}"')

    for ordem, nomes in ordens.items():
        if len(nomes) > 1:
            problemas += [Problema(n, "erro", f"Ordem {rotulo_ordem(ordem)} repetida") for n in nomes]
    for card, nomes in ids.items():
        if len(nomes) > 1:
            problemas += [Problema(n, "erro", f"Card {card} repetido") for n in nomes]
    trilho = quadro.no_trilho()
    if len(trilho) > 1:
        lista = ", ".join(wikilink(c.nome) for c in trilho)
        mensagem = f"trilho único: {len(trilho)} cards de caminho de jogo em curso (máx. 1): {lista}"
        problemas += [Problema(c.nome, "aviso", mensagem) for c in trilho]

    if tudo:
        return problemas
    return [
        p for p in problemas
        if (c := quadro.get(p.cartao)) is None or status_de(c) != "Concluída"
    ]


# ---------------------------------------------------------------------------
# fila
# ---------------------------------------------------------------------------

@dataclass
class Fila:
    cartoes: List[Cartao]
    trilho: List[Cartao]
    fora_pelo_trilho: List[Cartao] = field(default_factory=list)
    fora_pelo_preflight: List[Cartao] = field(default_factory=list)


def fila(quadro: Quadro, preflight: Optional[int] = None) -> Fila:
    """
    "Pronta para começar" na ordem de despacho: Reprovada primeiro, depois
    Ordem. Com o trilho ocupado, sai o caminho de jogo. Com o preflight
    consultado e diferente de 0, só Verificação Offline.
    """
    prontos = sorted(
        (c for c in quadro.cartoes if status_de(c) == "Pronta para começar"),
        key=lambda c: (c.props.get("Reprovada") is not True, ordem_de(c) or 0),
    )
    resultado = Fila([], quadro.no_trilho())
    for cartao in prontos:
        if resultado.trilho and caminho_de_jogo(cartao):
            resultado.fora_pelo_trilho.append(cartao)
        elif preflight not in (None, 0) and cartao.props.get("Verificação") != "Offline":
            resultado.fora_pelo_preflight.append(cartao)
        else:
            resultado.cartoes.append(cartao)
    return resultado


# ---------------------------------------------------------------------------
# reclassificar
# ---------------------------------------------------------------------------

@dataclass
class Reclassificacao:
    cartao: Cartao
    de: str
    para: str
    pendentes: List[str]
    sem_executor: bool


def reclassificar(quadro: Quadro, concluido: Cartao) -> List[Reclassificacao]:
    """
    Depois que `concluido` chega a Concluída: recalcula os dependentes
    diretos e os dependentes deles (a cadeia encurta: Backlog vira Bloqueada).
    """
    alvo: Dict[str, Cartao] = {}
    for direto in quadro.dependentes(concluido.nome):
        alvo[direto.nome] = direto
        for segundo in quadro.dependentes(direto.nome):
            alvo[segundo.nome] = segundo
    mudancas = []
    for cartao in alvo.values():
        de = status_de(cartao)
        if de not in RECLASSIFICAVEIS:
            continue
        para = classificar(quadro, cartao)
        if para == de:
            continue
        mudancas.append(Reclassificacao(
            cartao, de, para, quadro.pendentes(cartao),
            para == "Pronta para começar" and cartao.props.get("Executor") not in EXECUTORES,
        ))
    return sorted(mudancas, key=lambda m: ordem_de(m.cartao) or 0)


# ---------------------------------------------------------------------------
# criar
# ---------------------------------------------------------------------------

CHAVES_DA_SPEC = (
    "ordem", "titulo", "card", "sprint", "camada", "verificacao", "executor",
    "caminho_de_jogo", "infra", "janela", "partida", "depende_de", "status", "corpo",
)


@dataclass
class Planejado:
    cartao: Cartao
    status: str
    atualiza_bloqueia: List[Cartao]


def _exigir_da_lista(onde: str, rotulo: str, valor, valores) -> None:
    if not isinstance(valor, str) or valor not in valores:
        raise ErroBoard(f'{onde}: {rotulo} "{_mostrar(valor)}" fora da lista ({" · ".join(valores)})')


def planejar_criacao(quadro: Quadro, spec: dict, entrada: str) -> Planejado:
    """
    Monta o card sem gravar. `entrada` é a linha do Histórico, com
    `{status}` e `{pendentes}` a preencher. Status sai das dependências; só
    `"status": "Backlog"` é aceito, para estacionar de propósito.
    """
    if not isinstance(spec, dict):
        raise ErroBoard("cada card da spec é um objeto JSON")
    onde = f'card "{spec.get("titulo", "?")}"'
    desconhecidas = sorted(set(spec) - set(CHAVES_DA_SPEC))
    if desconhecidas:
        raise ErroBoard(f"{onde}: chave desconhecida {', '.join(desconhecidas)} "
                        f"(aceitas: {', '.join(CHAVES_DA_SPEC)})")
    titulo = str(spec.get("titulo") or "").strip()
    if not titulo:
        raise ErroBoard(f"{onde}: falta titulo")
    if PROIBIDOS_NO_TITULO.search(titulo):
        raise ErroBoard(f'{onde}: o título não pode ter \\ / : * ? " < > | [ ] # ^ '
                        "(quebra o arquivo ou o wikilink)")
    if "ordem" not in spec:
        raise ErroBoard(f"{onde}: falta ordem")
    ordem = ler_ordem(spec["ordem"])
    if any(ordem_de(c) == ordem for c in quadro.cartoes):
        raise ErroBoard(f"{onde}: a Ordem {rotulo_ordem(ordem)} já existe no board")

    card = spec.get("card")
    if not isinstance(card, str) or not ID_CARD.match(card):
        raise ErroBoard(f'{onde}: card "{_mostrar(card)}" fora do formato do plano (ex.: B1.3r)')
    if any(c.props.get("Card") == card for c in quadro.cartoes):
        raise ErroBoard(f"{onde}: o Card {card} já existe no board")
    sprint = spec.get("sprint", card.split(".")[0])
    if sprint != card.split(".")[0]:
        raise ErroBoard(f'{onde}: sprint "{_mostrar(sprint)}" não bate com o card {card}')

    _exigir_da_lista(onde, "Camada", spec.get("camada"), CAMADAS)
    _exigir_da_lista(onde, "Verificação", spec.get("verificacao"), VERIFICACOES)
    _exigir_da_lista(onde, "Executor", spec.get("executor"), EXECUTORES)
    janela = spec.get("janela", "nenhuma")
    _exigir_da_lista(onde, "Janela", janela, JANELAS)
    partida = spec.get("partida", "—")
    _exigir_da_lista(onde, "Partida", partida, PARTIDAS)
    jogo = spec.get("caminho_de_jogo")
    if not isinstance(jogo, bool):
        raise ErroBoard(f"{onde}: caminho_de_jogo é obrigatório e é true ou false")
    infra = spec.get("infra", False)
    if not isinstance(infra, bool):
        raise ErroBoard(f"{onde}: infra é true ou false")
    if infra and not jogo:
        raise ErroBoard(f"{onde}: infra true exige caminho_de_jogo true")
    if "status" in spec and spec["status"] != "Backlog":
        raise ErroBoard(f'{onde}: status só aceita "Backlog"; o resto sai das dependências')
    corpo = spec.get("corpo")
    if not isinstance(corpo, str) or not corpo.strip():
        raise ErroBoard(f"{onde}: falta corpo (origem, problema, critérios e arquivos)")
    if jogo and not _ROLLBACK.search(corpo):
        raise ErroBoard(f'{onde}: caminho de jogo exige a seção "## Rollback" no corpo')

    referencias = spec.get("depende_de", [])
    if not isinstance(referencias, list):
        raise ErroBoard(f"{onde}: depende_de é uma lista de Ordem, Card ou nome")
    deps = []
    for ref in referencias:
        try:
            deps.append(quadro.resolver(str(ref)))
        except ErroBoard as erro:
            raise ErroBoard(f'{onde}: dependência "{ref}": {erro}') from None

    nome = f"{rotulo_ordem(ordem)} - {titulo}"
    props: Dict[str, Valor] = {
        "Card": card,
        "Status": "Backlog",
        "Sprint": sprint,
        "Ordem": ordem,
        "Camada": spec["camada"],
        "Verificação": spec["verificacao"],
        "Executor": spec["executor"],
        "Caminho de jogo": jogo,
        "Infra": infra,
        "Janela": janela,
        "Partida": partida,
        "Reprovada": False,
        "Reprovações": 0,
        "Devoluções": 0,
        "Branch": None,
        "PR": None,
        "Candidato": None,
        "Custo": None,
        "Bloqueia": [],
        "Depende de": [wikilink(dep.nome) for dep in deps],
    }
    rascunho = Cartao(nome, None, props, "")
    sonda = Quadro(quadro.cartoes + [rascunho])
    status = "Backlog" if spec.get("status") == "Backlog" else classificar(sonda, rascunho)
    props["Status"] = status

    pendentes = len(sonda.pendentes(rascunho))
    texto = "\n".join(formatar_frontmatter(props) + [corpo.rstrip()])
    linha = entrada.replace("{status}", status).replace("{pendentes}", str(pendentes))
    rascunho.texto = acrescentar_historico(texto, linha)
    return Planejado(rascunho, status, deps)
