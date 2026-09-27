"""
Frontmatter no formato que o Obsidian grava nos cards, não YAML genérico:
escalares `Chave: valor` e listas `Chave:` seguidas de `  - "item"`.
Porte de `kalendas/scripts/lib/board.ts` (card H1.3).

Toda escrita troca só as linhas da chave pedida e mantém o resto do arquivo
byte a byte, inclusive o fim de linha (LF ou CRLF) e o BOM que o PowerShell
5.1 põe no começo (`Out-File`, `Set-Content -Encoding utf8`).
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple, Union

Valor = Union[str, int, float, bool, None, List[str]]

_NUMERO = re.compile(r"^-?\d+(\.\d+)?$")
_ITEM = re.compile(r"^\s+-\s*(.*)$")
_ENTRADA = re.compile(r"^([^\s:#][^:]*):(?:\s+(.*))?$")
_ASPAS_NO_INICIO = re.compile(r"""^[\s\-?:,\[\]{}#&*!|>'"%@`]""")
_PARECE_OUTRO_TIPO = re.compile(r"^(true|false|null|~|-?\d+(\.\d+)?)$")
_HISTORICO = re.compile(r"^##\s+Histórico\s*$")
_TITULO_1_OU_2 = re.compile(r"^#{1,2}\s")
# Quebra de linha ou outro caractere de controle solto no valor quebra o frontmatter.
_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")
BOM = "\ufeff"


def _linhas(texto: str) -> List[str]:
    return re.split(r"\r?\n", texto)


def _fim_de_linha(texto: str) -> str:
    return "\r\n" if "\r\n" in texto else "\n"


def ler_escalar(bruto: str) -> Valor:
    valor = bruto.strip()
    if valor in ("", "null", "~"):
        return None
    if valor == "true":
        return True
    if valor == "false":
        return False
    if valor == "[]":
        return []
    if len(valor) >= 2 and valor[0] == valor[-1] == '"':
        try:
            return json.loads(valor)
        except ValueError:
            return valor[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(valor) >= 2 and valor[0] == valor[-1] == "'":
        return valor[1:-1].replace("''", "'")
    if _NUMERO.match(valor):
        return float(valor) if "." in valor else int(valor)
    return valor


def _faixa(linhas: List[str]) -> Optional[Tuple[int, int]]:
    """Linhas do `---` de abertura e do de fechamento, ou None."""
    if not linhas or linhas[0].lstrip(BOM).strip() != "---":
        return None
    for indice in range(1, len(linhas)):
        if linhas[indice].strip() == "---":
            return 0, indice
    return None


def ler_frontmatter(texto: str) -> Optional[Dict[str, Valor]]:
    """
    `Chave:` sem valor é null até aparecer o primeiro `  - item`: é assim que
    fica uma propriedade de texto limpa no Obsidian (`Branch:`), e só vira
    lista se tiver item.
    """
    linhas = _linhas(texto)
    faixa = _faixa(linhas)
    if faixa is None:
        return None
    props: Dict[str, Valor] = {}
    chave_da_lista: Optional[str] = None
    for linha in linhas[faixa[0] + 1:faixa[1]]:
        item = _ITEM.match(linha)
        if item and chave_da_lista is not None:
            valor = ler_escalar(item.group(1))
            if not isinstance(props[chave_da_lista], list):
                props[chave_da_lista] = []
            props[chave_da_lista].append("" if valor is None else str(valor))
            continue
        entrada = _ENTRADA.match(linha)
        if not entrada:
            continue
        chave = entrada.group(1).strip()
        resto = entrada.group(2) or ""
        if resto.strip() == "":
            props[chave] = None
            chave_da_lista = chave
        else:
            props[chave] = ler_escalar(resto)
            chave_da_lista = None
    return props


def _precisa_aspas(valor: str) -> bool:
    return (
        valor == ""
        or bool(_CONTROLE.search(valor))
        or bool(_ASPAS_NO_INICIO.match(valor))
        or bool(re.search(r"\s$", valor))
        or bool(re.search(r": |\s#", valor))
        or bool(_PARECE_OUTRO_TIPO.match(valor))
    )


def formatar_escalar(valor: Valor) -> str:
    if valor is None:
        return "null"
    if isinstance(valor, bool):  # antes do int: bool é subclasse de int
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, list):
        raise ValueError("lista não é escalar")
    return json.dumps(valor, ensure_ascii=False) if _precisa_aspas(valor) else valor


def _formatar_entrada(chave: str, valor: Valor) -> List[str]:
    if isinstance(valor, list):
        if not valor:
            return [f"{chave}: []"]
        return [f"{chave}:"] + [f"  - {json.dumps(item, ensure_ascii=False)}" for item in valor]
    return [f"{chave}: {formatar_escalar(valor)}"]


def formatar_frontmatter(props: Dict[str, Valor]) -> List[str]:
    linhas = ["---"]
    for chave, valor in props.items():
        linhas.extend(_formatar_entrada(chave, valor))
    return linhas + ["---"]


def definir_propriedade(texto: str, chave: str, valor: Valor,
                        depois_de: Optional[str] = None) -> str:
    """
    Troca o valor de uma propriedade sem tocar no resto do arquivo: ordem das
    chaves, aspas das outras propriedades e corpo. Chave nova entra logo
    depois de `depois_de`, se ela existir; senão, no fim do frontmatter.
    """
    eol = _fim_de_linha(texto)
    linhas = _linhas(texto)
    faixa = _faixa(linhas)
    if faixa is None:
        raise ValueError("arquivo sem frontmatter")
    inicio, fim = faixa

    def achar(nome: str) -> int:
        for indice in range(inicio + 1, fim):
            if linhas[indice].startswith(f"{nome}:"):
                return indice
        return -1

    novas = _formatar_entrada(chave, valor)
    em = achar(chave)
    if em == -1:
        ancora = -1 if depois_de is None else achar(depois_de)
        inserir = fim if ancora == -1 else ancora + 1
        while ancora != -1 and inserir < fim and re.match(r"^\s+-", linhas[inserir]):
            inserir += 1
        linhas[inserir:inserir] = novas
    else:
        ate = em + 1
        while ate < fim and re.match(r"^\s+-", linhas[ate]):
            ate += 1
        linhas[em:ate] = novas
    return eol.join(linhas)


def acrescentar_historico(texto: str, entrada: str) -> str:
    """
    Acrescenta a entrada no fim da seção `## Histórico`, criando a seção no
    fim do arquivo se o card ainda não tiver uma.
    """
    eol = _fim_de_linha(texto)
    linhas = _linhas(re.sub(r"(\r?\n)+$", "", texto))
    bloco = _linhas(entrada)
    cabecalho = next((i for i, linha in enumerate(linhas) if _HISTORICO.match(linha)), -1)
    if cabecalho == -1:
        return eol.join(linhas + ["", "## Histórico", ""] + bloco + [""])
    seguinte = next(
        (i for i in range(cabecalho + 1, len(linhas)) if _TITULO_1_OU_2.match(linhas[i])),
        len(linhas),
    )
    inserir = seguinte
    while inserir > cabecalho + 1 and linhas[inserir - 1].strip() == "":
        inserir -= 1
    if inserir == cabecalho + 1:
        bloco = [""] + bloco
    linhas[inserir:inserir] = bloco
    return eol.join(linhas + [""])
