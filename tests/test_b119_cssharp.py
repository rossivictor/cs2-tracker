#!/usr/bin/env python3
"""
Card B1.19: CSSharp v1.0.380 (fix do CS2 v1.41.9.7, build 2000943), instalada à
mão no volume pelo papel servidor. Prende o pin do compose (que veio do teste do
B1.3s), a tabela G5 do asset sem runtime e a ordem da janela: vanilla on com
smoke de changelevel antes, vanilla off só depois das conferências, e a volta
com o YAML antes do volume. Só leitura de arquivo versionado: nada de processo,
rede ou Docker.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUNBOOK = RAIZ / "docs" / "runbooks" / "b1.19-cssharp-1.0.380.md"
# Gabaritos escritos à mão a partir do digest do GitHub e do download de 12/11.
SHA_SEM_RUNTIME = "47dad50c0448027fab6e28d3b82ddceca93365e3a616377d9b4a166064b808c5"
SHA_COM_RUNTIME = "f0653332a517c9edbaf8d6bfeb2ffec5aa730638ebd5e568d9753fa1063ba68e"
SHA_SNAPSHOT_12_11 = "40dd0b0e993cc0e549774ffc8d02aa0cb9a2b67b49f0782f5743b59bd4fe05f8"
URL = ("https://github.com/roflmuffin/CounterStrikeSharp/releases/download/v1.0.380/"
       "counterstrikesharp-linux-1.0.380.zip")


def _texto(caminho):
    return caminho.read_text(encoding="utf-8")


def _comandos(texto):
    return "".join(re.findall(r"```bash\n(.*?)```", texto, re.S))


def _secao(texto, titulo):
    achado = re.search(rf"^#+ {re.escape(titulo)}[^\n]*\n(.*?)(?=^#+ |\Z)", texto, re.M | re.S)
    assert achado, f"seção '{titulo}' sumiu"
    return achado.group(1)


def test_compose_pina_o_par_com_a_cssharp_1_0_380():
    compose = _texto(RAIZ / "docker-compose.yml")
    linhas = [x.strip() for x in compose.splitlines()
              if "FIXED_VERSION=" in x and not x.strip().startswith("#")]
    assert linhas == ["- MMSOURCE_FIXED_VERSION=2.0.0.1469",
                      "- CSSHARP_FIXED_VERSION=v1.0.380",
                      "- MATCHZY_FIXED_VERSION=0.8.15"]
    assert "1469 com 1.0.375 a 1.0.380" in compose
    assert "[[ADR-0009]] e [[b1.19-cssharp-1.0.380]]" in compose


def test_runbook_traz_a_tabela_g5_e_baixa_so_o_sem_runtime():
    runbook = _texto(RUNBOOK)
    comandos = _comandos(runbook)
    assert f"SHA_ESPERADO={SHA_SEM_RUNTIME}" in comandos
    assert "TAMANHO=4142158" in comandos
    assert "ASSET=counterstrikesharp-linux-1.0.380.zip" in comandos and URL in runbook
    assert "ENTRADAS=82; ARQUIVOS=65" in comandos
    assert "ENTRADAS_INSTALAR=80; ARQUIVOS_INSTALAR=64" in comandos
    assert 'curl -L --fail --proto \'=https\' -o "$ZIPDIR/$ASSET" "$URL"' in comandos
    assert '[ "$SHA_OBTIDO" = "$SHA_ESPERADO" ]' in comandos
    assert runbook.count(SHA_COM_RUNTIME) == 1
    nao_aprovado = runbook.index("**Não aprovado:**")
    assert nao_aprovado < runbook.index(SHA_COM_RUNTIME) < nao_aprovado + 200
    assert "with-runtime" not in comandos
    # O zip se baixa de novo nesta janela: nada de laço que reaproveite pasta anterior.
    assert "b1.3s*/download" not in comandos and "ANT=" not in comandos


def test_versao_do_volume_e_lida_antes_do_sed():
    comandos = _comandos(_texto(RUNBOOK))
    leitura = comandos.index("VER_ANTES=$(docker run")
    exige = comandos.index('[ "$VER_ANTES" = v1.0.378 ]')
    troca = comandos.index('sed -i "s/^v1\\.0\\.378\\$/v1.0.380/"')
    assert leitura < exige < troca
    assert "DONO=$(docker run" in comandos and comandos.index("DONO=$(docker run") < troca


def test_vanilla_off_so_depois_do_smoke_e_das_conferencias():
    runbook = _texto(RUNBOOK)
    comandos = _comandos(runbook)
    assert comandos.count("J vanilla off") == 1
    off = comandos.index("J vanilla off")
    assert comandos.index('rcon "changelevel de_inferno"') < off
    assert comandos.index("conferir_botai_2000930.py") < off
    assert comandos.index("tools/conferir_plugins_bot.py") < off
    assert "--gamedata \"$BK/gamedata-1.0.380.json\"" in comandos
    assert "SHA_LIB=acc5c6c332e032c4bb2e063b267f870027e19590952570f249a0e0e06d65fc75" in comandos
    # O RESULTADO offline do dev fica registrado, inclusive a contraprova da 1.0.378.
    conferencia = _secao(runbook, "Conferências offline na 2000943")
    assert conferencia.count("**`RESULTADO: OK`.**") == 2
    assert "28/28" in conferencia and "ClientPrint OK" in conferencia
    assert "ClientPrint (2 casamentos)" in conferencia and "RESULTADO: DIVERGE" in conferencia


def test_rollback_volta_o_yaml_antes_do_volume_e_avisa_que_nao_e_jogavel():
    runbook = _texto(RUNBOOK)
    rollback = _secao(runbook, "Rollback")
    assert "não um jogo jogável" in rollback
    assert (rollback.index("switch --detach jogavel-") < rollback.index("J restaurar --de")
            < rollback.index("J voltar --tag"))
    assert "volume-addons-0928.tgz" in rollback and SHA_SNAPSHOT_12_11 in rollback
    assert "versoes-conhecidas.md" not in _comandos(runbook)


def test_indice_de_runbooks_lista_o_b1_19():
    assert "(b1.19-cssharp-1.0.380.md)" in _texto(RAIZ / "docs" / "runbooks" / "README.md")
