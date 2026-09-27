"""
Testes do vault do board (card H1.4): o modelo versionado em
tools/board/modelo/ e o `iniciar`, que cria o vault a partir dele sem
sobrescrever nada.

Tudo em tmp_path: o vault real (docs/board-cs2 do checkout principal) nunca é
criado, lido nem escrito. A .venv não tem PyYAML (e nada se instala nela),
então o Board.base passa por um leitor de um subconjunto estrito de YAML, que
recusa o que não conhece.
"""
import io
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from tools.board import cli, vault  # noqa: E402
from tools.board.frontmatter import ler_frontmatter  # noqa: E402
from tools.board.modelo import (  # noqa: E402
    CAMADAS,
    EXECUTORES,
    NOTAS_DO_VAULT,
    STATUS,
    VERIFICACOES,
    carregar,
)

ARQUIVOS = [".obsidian/community-plugins.json", ".obsidian/core-plugins.json",
            "Board.base", "README.md"]
# Cores que o Better Kanban Bases View 0.7.1 aceita (main.js do plugin no vault do kalendas).
CORES_DO_PLUGIN = {"gray", "red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink"}


# ---------------------------------------------------------------------------
# leitor de YAML restrito: mapas e listas em bloco, escalares como texto
# ---------------------------------------------------------------------------

_INDICADOR = re.compile(r"^([\[\]{}!&*|>%@`#,]|[?:-](\s|$))")
_CHAVE = re.compile(r"""^("[^"]*"|'[^']*'|[^\s"'#\[\]{}!&*|>%@`,?:-][^:]*?):(?:\s+(.*))?$""")


def _escalar(bruto, n):
    if bruto.startswith('"'):
        return json.loads(bruto)
    if bruto.startswith("'"):
        miolo = bruto[1:-1]
        if len(bruto) < 2 or not bruto.endswith("'") or "'" in miolo.replace("''", ""):
            raise ValueError(f"linha {n}: aspas simples mal fechadas")
        return miolo.replace("''", "'")
    if _INDICADOR.match(bruto) or ": " in bruto or " #" in bruto or bruto.endswith(":"):
        raise ValueError(f"linha {n}: escalar simples ambíguo: {bruto!r}")
    return bruto


def ler_yaml_restrito(texto):
    linhas = []
    for n, bruta in enumerate(texto.split("\n"), 1):
        if "\t" in bruta:
            raise ValueError(f"linha {n}: tab")
        if bruta.strip() and not bruta.lstrip().startswith("#"):
            linhas.append([n, len(bruta) - len(bruta.lstrip(" ")), bruta.strip()])
    pos = 0

    def item(i):
        return i < len(linhas) and (linhas[i][2] == "-" or linhas[i][2].startswith("- "))

    def mapa(recuo):
        nonlocal pos
        resultado = {}
        while pos < len(linhas) and linhas[pos][1] == recuo and not item(pos):
            n, _, conteudo = linhas[pos]
            par = _CHAVE.match(conteudo)
            if not par:
                raise ValueError(f"linha {n}: não é chave: valor")
            chave, valor = _escalar(par.group(1), n), par.group(2)
            if chave in resultado:
                raise ValueError(f"linha {n}: chave repetida {chave}")
            pos += 1
            if valor is not None:
                resultado[chave] = _escalar(valor, n)
            elif pos < len(linhas) and (linhas[pos][1] > recuo
                                        or linhas[pos][1] == recuo and item(pos)):
                recuo_filho = linhas[pos][1]
                resultado[chave] = lista(recuo_filho) if item(pos) else mapa(recuo_filho)
            else:
                resultado[chave] = None
        if pos < len(linhas) and linhas[pos][1] > recuo:
            raise ValueError(f"linha {linhas[pos][0]}: recuo inesperado")
        return resultado

    def lista(recuo):
        nonlocal pos
        resultado = []
        while pos < len(linhas) and linhas[pos][1] == recuo and item(pos):
            n, _, conteudo = linhas[pos]
            resto = conteudo[1:].lstrip(" ")
            if not resto:
                raise ValueError(f"linha {n}: item vazio")
            if _CHAVE.match(resto):  # "- chave: valor" abre um mapa dentro do item
                linhas[pos] = [n, recuo + len(conteudo) - len(resto), resto]
                resultado.append(mapa(linhas[pos][1]))
            else:
                pos += 1
                resultado.append(_escalar(resto, n))
        return resultado

    documento = mapa(0)
    if pos != len(linhas):
        raise ValueError(f"linha {linhas[pos][0]}: sobrou texto")
    return documento


@pytest.mark.parametrize("texto", [
    "a: 1\na: 2\n", "a:\n\t- x\n", "a: {b: 1}\n", "a: x: y\n", "a: 'x'y'\n",
    "a: 1\n  b: 2\n", "a: &ancora 1\n",
])
def test_leitor_restrito_recusa_chave_repetida_tab_fluxo_ambiguidade_e_ancora(texto):
    with pytest.raises(ValueError):
        ler_yaml_restrito(texto)


def test_leitor_restrito_le_lista_de_mapas_com_chave_vazia_e_lista_sem_recuo():
    texto = "v:\n  - a: 1\n    b:\n  - a: '2'\n    c:\n    - x\n    - \"y: z\"\n"
    assert ler_yaml_restrito(texto) == {"v": [{"a": "1", "b": None},
                                              {"a": "2", "c": ["x", "y: z"]}]}


# ---------------------------------------------------------------------------
# o modelo
# ---------------------------------------------------------------------------

def _base():
    return ler_yaml_restrito(vault.texto_do_modelo("Board.base"))


def test_modelo_tem_board_base_readme_e_obsidian_minimo_sem_types_json_nem_py():
    assert vault.arquivos_do_modelo() == ARQUIVOS
    # Sem .py (e sem __init__.py) na pasta, tools.board.modelo continua sendo o modelo.py.
    import tools.board.modelo as modulo
    assert Path(modulo.__file__).name == "modelo.py"


def test_board_base_tem_uma_visao_esteira_kanban_por_status_na_ordem_do_board():
    base = _base()
    assert base["filters"] == {"and": ['file.ext == "md"', 'file.hasProperty("Status")']}
    [esteira] = base["views"]
    assert esteira["type"] == "kanban" and esteira["name"] == "Esteira"
    assert esteira["groupBy"] == {"property": "Status", "direction": "ASC"}
    assert esteira["kanbanState"]["columnOrders"]["note.Status"] == list(STATUS)
    cores = esteira["kanbanState"]["columnSettings"]["note.Status"]
    assert list(cores) == list(STATUS)
    assert {c["color"] for c in cores.values()} <= CORES_DO_PLUGIN
    assert esteira["sort"] == [{"property": "Reprovada", "direction": "DESC"},
                               {"property": "Ordem", "direction": "ASC"}]
    assert esteira["order"][0] == "file.name"
    assert [p for p in esteira["order"] if not p.startswith(("file.", "formula."))] == [
        "ID", "Verificação", "Executor", "Camada"]


@pytest.mark.parametrize("formula, propriedade, valores", [
    ("status_valido", "note.Status", STATUS),
    ("verificacao_valida", 'note["Verificação"]', VERIFICACOES),
    ("executor_valido", "note.Executor", EXECUTORES),
    ("camada_valida", "note.Camada", CAMADAS),
])
def test_formulas_do_board_base_conferem_as_mesmas_listas_do_cli(formula, propriedade, valores):
    formulas = _base()["formulas"]
    lista, contem = re.fullmatch(r"(\[.*\])\.contains\((.*)\)", formulas[formula]).groups()
    assert json.loads(lista) == list(valores)
    assert contem == propriedade
    assert f"formula.{formula}" in formulas["fora_da_lista"]


def test_board_base_conta_deps_pendentes_e_toda_formula_usada_existe():
    base = _base()
    pendentes = base["formulas"]["deps_pendentes"]
    assert 'note["Depende de"]' in pendentes and 'Status != "Concluída"' in pendentes
    usadas = {p for p in base["views"][0]["order"] if p.startswith("formula.")}
    usadas |= set(base["properties"])
    usadas |= set(re.findall(r"formula\.\w+", " ".join(base["formulas"].values())))
    assert {u.split(".", 1)[1] for u in usadas} <= set(base["formulas"])


def test_obsidian_do_modelo_liga_bases_e_lista_so_o_better_kanban_bases_view():
    core = json.loads(vault.texto_do_modelo(".obsidian/core-plugins.json"))
    assert core["bases"] is True and core["sync"] is False
    comunidade = json.loads(vault.texto_do_modelo(".obsidian/community-plugins.json"))
    assert comunidade == ["bases-kanban-view-ttvl"]


def test_readme_do_vault_nao_e_card_e_explica_o_cli():
    readme = vault.texto_do_modelo("README.md")
    assert ler_frontmatter(readme) is None and "README.md" in NOTAS_DO_VAULT
    assert "C:/Users/Victor/Projetos/cs2-tracker/.venv/Scripts/python.exe -m tools.board" in readme
    assert "iniciar" in readme and "validar" in readme


# ---------------------------------------------------------------------------
# iniciar
# ---------------------------------------------------------------------------

def rodar(*argv):
    out, err = [], []
    codigo = cli.main(list(argv), log=out.append, erro=err.append, preflight=lambda: 0)
    return SimpleNamespace(codigo=codigo, out="\n".join(out), err="\n".join(err))


def fotografia(pasta):
    return {c.relative_to(pasta).as_posix(): (c.read_bytes(), c.stat().st_mtime_ns)
            for c in sorted(pasta.rglob("*")) if c.is_file()}


def test_iniciar_cria_o_vault_do_modelo_em_lf_e_nada_fora_da_pasta(tmp_path):
    (tmp_path / "vizinho.txt").write_text("fica", encoding="utf-8")
    antes = fotografia(tmp_path)
    destino = tmp_path / "board-cs2"
    resultado = rodar("iniciar", f"--board={destino}")
    assert resultado.codigo == 0, resultado.err
    assert "(pasta nova)" in resultado.out and "4 criado(s) · 0 igual(is)" in resultado.out
    assert "Better Kanban Bases View" in resultado.out
    for relativo in ARQUIVOS:
        dados = (destino / relativo).read_bytes()
        assert b"\r\n" not in dados and dados.decode("utf-8") == vault.texto_do_modelo(relativo)
    depois = fotografia(tmp_path)
    assert {k: v for k, v in depois.items() if not k.startswith("board-cs2/")} == antes


def test_iniciar_de_novo_nao_grava_nada_nem_com_crlf_ou_bom_e_sai_0(tmp_path):
    destino = tmp_path / "board-cs2"
    assert rodar("iniciar", f"--board={destino}").codigo == 0
    readme = destino / "README.md"
    readme.write_bytes(b"\xef\xbb\xbf" + readme.read_bytes().replace(b"\n", b"\r\n"))
    antes = fotografia(destino)
    resultado = rodar("iniciar", f"--board={destino}")
    assert resultado.codigo == 0 and resultado.err == ""
    assert "0 criado(s) · 4 igual(is) · 0 diferente(s) · 0 conflito(s)" in resultado.out
    assert "Próximo passo" not in resultado.out
    assert fotografia(destino) == antes


def test_iniciar_nao_sobrescreve_mostra_o_diff_e_so_o_board_base_sai_1(tmp_path):
    destino = tmp_path / "board-cs2"
    rodar("iniciar", f"--board={destino}")
    base = destino / "Board.base"
    meu = base.read_text(encoding="utf-8").replace("color: cyan", "color: pink")
    base.write_text(meu, encoding="utf-8")
    comunidade = destino / ".obsidian" / "community-plugins.json"
    comunidade.write_text('[\n  "bases-kanban-view-ttvl",\n  "outro"\n]', encoding="utf-8")
    (destino / "README.md").unlink()
    resultado = rodar("iniciar", f"--board={destino}")
    assert resultado.codigo == 1
    assert "ERRO · Board.base · diferente do modelo: mantido, nada sobrescrito" in resultado.err
    assert "-            color: pink" in resultado.err
    assert "+            color: cyan" in resultado.err
    aviso = "aviso · .obsidian/community-plugins.json · diferente do modelo: mantido"
    assert aviso in resultado.err
    assert base.read_text(encoding="utf-8") == meu
    assert '"outro"' in comunidade.read_text(encoding="utf-8")
    assert "criado · README.md" in resultado.out  # o que falta nasce mesmo assim
    comunidade.unlink()
    base.unlink()
    assert rodar("iniciar", f"--board={destino}").codigo == 0  # sem o seu, adota o modelo


def test_iniciar_seco_nao_grava_nada_nem_cria_a_pasta(tmp_path):
    destino = tmp_path / "board-cs2"
    resultado = rodar("iniciar", f"--board={destino}", "--seco")
    assert resultado.codigo == 0
    assert "criaria · Board.base" in resultado.out and "(seco: nada gravado)" in resultado.out
    assert not destino.exists()
    destino.mkdir()
    (destino / "README.md").write_text("meu", encoding="utf-8")
    resultado = rodar("iniciar", f"--board={destino}", "--seco")
    assert "3 a criar · 0 igual(is) · 1 diferente(s)" in resultado.out
    assert [c.name for c in destino.iterdir()] == ["README.md"]


@pytest.mark.parametrize("preparar, mensagem", [
    (lambda d: (d / "Board.base").mkdir(), "ERRO · Board.base · existe e não é arquivo"),
    (lambda d: (d / ".obsidian").write_text("x", encoding="utf-8"),
     "ERRO · .obsidian/community-plugins.json · .obsidian existe e não é pasta"),
])
def test_iniciar_recusa_conflito_de_tipo_sem_gravar_nesse_caminho(tmp_path, preparar, mensagem):
    destino = tmp_path / "board-cs2"
    destino.mkdir()
    preparar(destino)
    resultado = rodar("iniciar", f"--board={destino}")
    assert resultado.codigo == 1 and mensagem in resultado.err


def test_iniciar_recusa_pasta_mae_inexistente_e_arquivo_no_lugar_da_pasta(tmp_path):
    resultado = rodar("iniciar", f"--board={tmp_path / 'a' / 'b' / 'board-cs2'}")
    assert resultado.codigo == 1 and "a pasta-mãe" in resultado.err
    assert not (tmp_path / "a").exists()
    arquivo = tmp_path / "board-cs2"
    arquivo.write_text("x", encoding="utf-8")
    resultado = rodar("iniciar", f"--board={arquivo}")
    assert resultado.codigo == 1 and "existe e não é pasta" in resultado.err
    assert arquivo.read_text(encoding="utf-8") == "x"


def test_iniciar_recusa_caminho_que_sai_do_vault_por_link(tmp_path):
    destino, fora = tmp_path / "board-cs2", tmp_path / "fora"
    destino.mkdir()
    fora.mkdir()
    try:
        os.symlink(fora, destino / ".obsidian", target_is_directory=True)
    except (OSError, NotImplementedError):
        try:  # no Windows sem modo de desenvolvedor: junção, que não pede privilégio
            import _winapi
            _winapi.CreateJunction(str(fora), str(destino / ".obsidian"))
        except (ImportError, AttributeError, OSError):
            pytest.skip("sem link simbólico nem junção nesta máquina")
    resultado = rodar("iniciar", f"--board={destino}")
    assert resultado.codigo == 1 and "sai da pasta do vault" in resultado.err
    assert list(fora.iterdir()) == []


def test_iniciar_interrompido_diz_o_que_criou_e_nao_deixa_arquivo_pela_metade(
        tmp_path, monkeypatch):
    destino = tmp_path / "board-cs2"
    abrir = open

    class DiscoCheio(io.BytesIO):
        def write(self, _):
            raise OSError("disco cheio")

    def abrir_com_falha(caminho, modo):
        arquivo = abrir(caminho, modo)
        if Path(caminho).name != "Board.base":
            return arquivo
        arquivo.close()  # nasceu vazio pelo "x"; quem falha é a escrita
        return DiscoCheio()

    monkeypatch.setattr(vault, "open", abrir_com_falha, raising=False)
    resultado = rodar("iniciar", f"--board={destino}")
    assert resultado.codigo == 1 and "disco cheio" in resultado.err
    assert ("Já criados: .obsidian/community-plugins.json, .obsidian/core-plugins.json"
            in resultado.err)
    assert not (destino / "Board.base").exists()
    monkeypatch.undo()
    assert rodar("iniciar", f"--board={destino}").codigo == 0  # a próxima rodada completa
    assert (destino / "Board.base").is_file()


def test_iniciar_sem_board_usa_o_padrao_e_so_aceita_seco(tmp_path, monkeypatch):
    nao_existe = rodar("validar", f"--board={tmp_path / 'board-cs2'}")
    assert nao_existe.codigo == 1 and "crie o vault com o iniciar" in nao_existe.err
    monkeypatch.setattr(cli, "BOARD_PADRAO", tmp_path / "board-cs2")
    assert rodar("iniciar").codigo == 0
    assert (tmp_path / "board-cs2" / "Board.base").is_file()
    resultado = rodar("iniciar", "--papel=PM")
    assert resultado.codigo == 1 and "opção desconhecida --papel para iniciar" in resultado.err
    monkeypatch.chdir(tmp_path)  # --board= vazio seria a pasta atual
    resultado = rodar("iniciar", "--board=")
    assert resultado.codigo == 1 and "--board veio vazio" in resultado.err
    assert not (tmp_path / "Board.base").exists()


# ---------------------------------------------------------------------------
# o CLI num vault de verdade: Board.base, README.md e .obsidian/ não são card
# ---------------------------------------------------------------------------

def test_cli_opera_o_vault_iniciado_ignora_o_que_nao_e_card_e_o_iniciar_nao_toca_card(
        tmp_path):
    destino = tmp_path / "board-cs2"
    assert rodar("iniciar", f"--board={destino}").codigo == 0
    # Nota do vault com cara de card e .md dentro de .obsidian/ também ficam de fora.
    (destino / "README.md").write_text("---\nStatus: Backlog\n---\n", encoding="utf-8")
    plugin = destino / ".obsidian" / "plugins" / "x"
    plugin.mkdir(parents=True)
    (plugin / "README.md").write_text("---\nStatus: Backlog\n---\n", encoding="utf-8")
    spec = tmp_path / "spec.json"
    comum = {"camada": "Infra/Harness", "verificacao": "Offline", "caminho_de_jogo": False}
    spec.write_text(json.dumps([
        {**comum, "ordem": 1, "titulo": "Vault do board", "card": "H1.4",
         "executor": "Agente", "corpo": "**Problema:** criar o vault."},
        {**comum, "ordem": 2, "titulo": "Abrir o vault", "card": "H1.5", "executor": "Humano",
         "depende_de": ["H1.4"], "corpo": "**Problema:** abrir o vault."},
    ]), encoding="utf-8")
    assert rodar("criar", f"--spec={spec}", f"--board={destino}").codigo == 0
    assert [c.nome for c in carregar(destino).cartoes] == ["1 - Vault do board",
                                                           "2 - Abrir o vault"]
    validar = rodar("validar", f"--board={destino}")
    assert validar.codigo == 0 and "2 cards · 0 erro(s) · 0 aviso(s)" in validar.out
    fila = rodar("fila", f"--board={destino}")
    assert "1 · H1.4" in fila.out and "H1.5" not in fila.out and fila.err == ""
    assert rodar("mover", "--card=H1.4", "--status=Concluída", f"--board={destino}").codigo == 0
    reclassificado = rodar("reclassificar", "--concluido=H1.4", f"--board={destino}")
    assert "Bloqueada → Pronta para começar" in reclassificado.out
    assert reclassificado.err == ""

    cards = {c: v for c, v in fotografia(destino).items() if c[0].isdigit()}
    de_novo = rodar("iniciar", f"--board={destino}")
    assert de_novo.codigo == 0 and "(2 card(s), intocados)" in de_novo.out
    assert "aviso · README.md" in de_novo.err  # o README mexido fica, com aviso
    assert {c: v for c, v in fotografia(destino).items() if c[0].isdigit()} == cards
