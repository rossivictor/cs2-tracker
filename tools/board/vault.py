"""
Vault do board (card H1.4): o `iniciar` cria o `docs/board-cs2/` a partir do
modelo versionado em `tools/board/modelo/` (Board.base, README.md e
.obsidian/). O vault fica fora do git (Q21=A); o que se versiona é o modelo e
este comando.

Nunca sobrescreve. O que falta é criado com abertura exclusiva ("x"), que
falha se o arquivo aparecer no meio. O que já existe fica como está: igual ao
modelo, passa; diferente, sai com o diff. Só o `Board.base` diferente é
recusa (sai 1), porque a Esteira é o contrato do board; a config em
`.obsidian/` o próprio Obsidian regrava, e só gera aviso. Nada é escrito fora
da pasta de destino: a pasta-mãe tem de existir, e caminho que sai dela (link
ou junção) é conflito. Card não é criado nem tocado.

A pasta `modelo/` não tem `__init__.py` de propósito: sem ele, o
`tools.board.modelo` continua sendo o `modelo.py`, porque o import prefere o
arquivo à pasta sem `__init__`.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .modelo import ErroBoard

MODELO = Path(__file__).resolve().parent / "modelo"
BASE = "Board.base"


@dataclass
class Passo:
    relativo: str  # caminho dentro do vault, com "/"
    acao: str  # "criar", "igual", "diverge" ou "conflito"
    motivo: str = ""
    diff: List[str] = field(default_factory=list)

    @property
    def recusa(self) -> bool:
        return self.acao == "conflito" or (self.acao == "diverge" and self.relativo == BASE)


def arquivos_do_modelo(modelo: Path = MODELO) -> List[str]:
    return sorted(c.relative_to(modelo).as_posix() for c in modelo.rglob("*") if c.is_file())


def texto_do_modelo(relativo: str, modelo: Path = MODELO) -> str:
    return _normalizar((modelo / relativo).read_bytes())


def _normalizar(dados: bytes) -> str:
    """Sem BOM e com LF: com autocrlf, o checkout traz o modelo em CRLF."""
    return dados.decode("utf-8-sig").replace("\r\n", "\n")


def _pastas_no_caminho(destino: Path, relativo: str) -> List[Path]:
    partes = relativo.split("/")[:-1]
    return [destino.joinpath(*partes[:fim]) for fim in range(1, len(partes) + 1)]


def _dentro(raiz: Path, caminho: Path) -> bool:
    try:
        caminho.resolve().relative_to(raiz)
    except ValueError:
        return False
    return True


def planejar(destino: Path, modelo: Path = MODELO) -> List[Passo]:
    """O que o `iniciar` faria em `destino`, arquivo por arquivo, sem gravar."""
    if destino.exists() and not destino.is_dir():
        raise ErroBoard(f"{destino.as_posix()} existe e não é pasta")
    if not destino.exists() and not destino.parent.is_dir():
        raise ErroBoard(f"a pasta-mãe {destino.parent.as_posix()} não existe: o iniciar só "
                        "cria a pasta do vault, nada acima dela")
    raiz = destino.resolve()
    passos: List[Passo] = []
    for relativo in arquivos_do_modelo(modelo):
        alvo = destino / relativo
        no_caminho = [p for p in _pastas_no_caminho(destino, relativo)
                      if p.exists() and not p.is_dir()]
        if no_caminho:
            nome = no_caminho[0].relative_to(destino).as_posix()
            passos.append(Passo(relativo, "conflito", f"{nome} existe e não é pasta"))
        elif not _dentro(raiz, alvo):
            passos.append(Passo(relativo, "conflito",
                                "o caminho sai da pasta do vault (link ou junção)"))
        elif not alvo.exists() and not alvo.is_symlink():
            passos.append(Passo(relativo, "criar"))
        elif not alvo.is_file():
            passos.append(Passo(relativo, "conflito", "existe e não é arquivo"))
        else:
            passos.append(_comparar(relativo, alvo, texto_do_modelo(relativo, modelo)))
    return passos


def _comparar(relativo: str, alvo: Path, esperado: str) -> Passo:
    try:
        atual = _normalizar(alvo.read_bytes())
    except UnicodeDecodeError:
        return Passo(relativo, "diverge", "não é UTF-8")
    if atual == esperado:
        return Passo(relativo, "igual")
    diff = difflib.unified_diff(atual.splitlines(), esperado.splitlines(),
                                f"vault/{relativo}", f"modelo/{relativo}", lineterm="")
    return Passo(relativo, "diverge", "diferente do modelo", list(diff))


def aplicar(destino: Path, passos: List[Passo], modelo: Path = MODELO) -> List[str]:
    """Cria os arquivos que o plano manda criar e devolve quais criou."""
    criados: List[str] = []
    try:
        if not destino.exists():
            destino.mkdir()  # sem parents: nada acima da pasta do vault
        for passo in passos:
            if passo.acao != "criar":
                continue
            for pasta in _pastas_no_caminho(destino, passo.relativo):
                if not pasta.exists():
                    pasta.mkdir()
            alvo = destino / passo.relativo
            dados = texto_do_modelo(passo.relativo, modelo).encode("utf-8")
            arquivo = open(alvo, "xb")  # "x": se o arquivo aparecer no meio, falha
            try:
                with arquivo:  # a escrita de verdade pode falhar só no close
                    arquivo.write(dados)
            except OSError:
                try:
                    alvo.unlink()  # nasceu agora, pelo "x": é nosso
                except OSError:
                    pass
                raise
            criados.append(passo.relativo)
    except OSError as caught:
        ja = ", ".join(criados) if criados else "nenhum"
        raise ErroBoard(f"iniciar interrompido, nada sobrescrito: {caught}. "
                        f"Já criados: {ja}") from None
    return criados
