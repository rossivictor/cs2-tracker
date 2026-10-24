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


def test_estado_vigente_dos_docs_diz_v1_0_378():
    readme = _texto(RAIZ / "README.md")
    assert "| `v1.0.378` | runtime .NET pros plugins" in readme
    boot = _texto(RAIZ / "docs" / "runbooks" / "servidor-boot-saudavel.md")
    assert "`[CSSHARP SETUP] Version v1.0.378 ...`" in boot
    assert "(b1.3s-cssharp-1.0.378.md)" in _texto(RAIZ / "docs" / "runbooks" / "README.md")
