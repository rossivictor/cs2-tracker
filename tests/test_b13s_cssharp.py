#!/usr/bin/env python3
"""
Card B1.3s: CSSharp v1.0.378 (fix do CS2 v1.41.9.2), instalada à mão no
volume pelo papel servidor. Prende o pin do compose, o asset aprovado (o sem
runtime, com o sha256 do digest do GitHub) e a ordem da volta pelo snapshot
no runbook. Só leitura de arquivo versionado: nada de processo, rede ou Docker.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUNBOOK = RAIZ / "docs" / "runbooks" / "b1.3s-cssharp-1.0.378.md"
SHA_SEM_RUNTIME = "26cf779ec3c87c55f4e23496839c7cc1e2977952ae9795403c4a52253d76fc82"
SHA_COM_RUNTIME = "b7fcbd99619ab17e32b07a6af2bd5179d83e2c7a4c045e33cbd11e5492c87b7d"
URL = ("https://github.com/roflmuffin/CounterStrikeSharp/releases/download/v1.0.378/"
       "counterstrikesharp-linux-1.0.378.zip")


def _texto(caminho):
    return caminho.read_text(encoding="utf-8")


def _secao(texto, titulo):
    achado = re.search(rf"^#+ {re.escape(titulo)}[^\n]*\n(.*?)(?=^## |\Z)", texto, re.M | re.S)
    assert achado, f"seção '{titulo}' sumiu"
    return achado.group(1)


def test_compose_pina_o_par_com_a_cssharp_1_0_378():
    linhas = [x.strip() for x in _texto(RAIZ / "docker-compose.yml").splitlines()
              if "FIXED_VERSION=" in x and not x.strip().startswith("#")]
    assert linhas == ["- MMSOURCE_FIXED_VERSION=2.0.0.1469",
                      "- CSSHARP_FIXED_VERSION=v1.0.378",
                      "- MATCHZY_FIXED_VERSION=0.8.15"]


def test_runbook_baixa_so_o_asset_sem_runtime_e_confere_o_sha256():
    runbook = _texto(RUNBOOK)
    assert f"SHA_ESPERADO={SHA_SEM_RUNTIME}" in runbook
    assert "TAMANHO=4137186" in runbook
    assert "ASSET=counterstrikesharp-linux-1.0.378.zip" in runbook and URL in runbook
    assert 'curl -L --fail --proto \'=https\' -o "$ZIPDIR/$ASSET" "$URL"' in runbook
    assert '[ "$SHA_OBTIDO" = "$SHA_ESPERADO" ]' in runbook
    # O with-runtime só aparece como alternativa NÃO aprovada.
    assert runbook.count(SHA_COM_RUNTIME) == 1
    nao_aprovado = runbook.index("**Não aprovado:**")
    assert nao_aprovado < runbook.index(SHA_COM_RUNTIME) < nao_aprovado + 200
    assert "with-runtime-linux-1.0.378.zip" not in "".join(
        re.findall(r"```bash\n(.*?)```", runbook, re.S))


def test_runbook_volta_o_yaml_antes_do_volume_e_mantem_a_vanilla():
    runbook = _texto(RUNBOOK)
    caminho_a = _secao(runbook, "Caminho A")
    assert (caminho_a.index("switch --detach jogavel-") < caminho_a.index("J restaurar --de")
            < caminho_a.index("J voltar --tag"))
    comandos = "".join(re.findall(r"```bash\n(.*?)```", runbook, re.S))
    assert "vanilla off" not in comandos and "jogavel.py soak" not in comandos
    assert "J vanilla status" in comandos
    assert "versoes-conhecidas.md" not in comandos


def _comandos(texto):
    return "".join(re.findall(r"```bash\n(.*?)```", texto, re.S))


def _funcao(comandos, nome):
    achado = re.search(rf"^{nome}\(\) \{{(.*?)^\}}", comandos, re.M | re.S)
    assert achado, f"função {nome} sumiu"
    return achado.group(1)


def test_unzip_exclui_o_shared_com_destino_antes_do_zip():
    # Janela de 25/10: shared/ é 1000:1000 (APIs dos plugins de bot) e o zip
    # só põe ali um README; o unzip não pode tocar nele.
    comandos = _comandos(_texto(RUNBOOK))
    linha = next(x for x in comandos.splitlines() if x.strip().startswith("-o -q "))
    assert linha.strip().startswith(
        "-o -q -d /d/game/csgo \"/in/$ASSET\" -x 'addons/counterstrikesharp/shared/*';")
    assert "-Z1" in comandos and "-x \"$EXCLUI\"" in comandos
    assert "EXCLUI='addons/counterstrikesharp/shared/*'" in comandos


def test_donos_e_inventario_poda_o_shared_e_o_registra_a_parte():
    comandos = _comandos(_texto(RUNBOOK))
    donos = _funcao(comandos, "donos")
    assert "-path 'game/csgo/addons/counterstrikesharp/shared' -prune -o" in donos
    assert "*/plugins" in donos and "*/dotnet" in donos
    inventario = _funcao(comandos, "inventario")
    assert "-path game/csgo/addons/counterstrikesharp/shared -prune -o -exec stat" in inventario
    assert 'echo "== donos de shared/ (intocado)"' in inventario
    assert inventario.index("== donos de shared/") < inventario.index('echo "== ls $p"')
    assert ('diff <(secao_shared "$BK/configs-antes.txt") <(secao_shared "$BK/configs-instalado.txt")'
            in comandos)


def test_sha256_confere_so_o_que_se_instala_e_as_contagens_batem():
    runbook = _texto(RUNBOOK)
    comandos = _comandos(runbook)
    assert "-c --quiet /bk/zip-membros-instalar.sha256" in comandos
    assert "-c --quiet /bk/zip-membros.sha256" not in comandos
    assert ("grep -v '  addons/counterstrikesharp/shared/' \"$BK/zip-membros.sha256\" > "
            "\"$BK/zip-membros-instalar.sha256\"") in comandos
    assert "ENTRADAS=82; ARQUIVOS=65" in comandos
    assert "ENTRADAS_INSTALAR=80; ARQUIVOS_INSTALAR=64" in comandos
    assert "**82 entradas / 65\n  arquivos**; a extração, **80 entradas / 64 arquivos**" in runbook


def test_container_parado_na_abertura_nao_e_ligado_nem_consultado():
    comandos = _comandos(_texto(RUNBOOK))
    for linha in comandos.splitlines():
        if "docker start" in linha:
            assert linha.strip().startswith('if [ "$ESTADO_ABERTURA" = running ]; then docker start')
    passo1 = _secao(_texto(RUNBOOK), "1. Estado")
    assert passo1.index('if [ "$ESTADO_ABERTURA" = running ]') < passo1.index('rcon "$c"')
    assert "GC Connection established for server version" in passo1


def test_estado_vigente_dos_docs_diz_v1_0_378():
    readme = _texto(RAIZ / "README.md")
    assert "| `v1.0.378` | runtime .NET pros plugins" in readme
    boot = _texto(RAIZ / "docs" / "runbooks" / "servidor-boot-saudavel.md")
    assert "`[CSSHARP SETUP] Version v1.0.378 ...`" in boot
    assert "(b1.3s-cssharp-1.0.378.md)" in _texto(RAIZ / "docs" / "runbooks" / "README.md")
