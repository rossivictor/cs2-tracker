#!/usr/bin/env python3
"""
Plugin de captura 0.4.1 sem truncar o órfão (card P1.10).

O plugin é C# e não roda aqui: a máquina não tem dotnet, e o build é do job
`plugin` do CI e do papel servidor, em janela. O teste lê o fonte
(docker/plugins-src/Cs2TrackerEvents/Cs2TrackerEventsPlugin.cs) e prova três
coisas:

1. a regra do plugin é a do start_match (P1.1) e do contrato do JSONL, §7:
   os mesmos três tipos e a mesma exceção da morte de pós-jogo (P1.1d);
2. Load e OnMapStart passam pelo PreservarOrfao ANTES do truncamento;
3. a regra, montada com as constantes tiradas do fonte, dá o gabarito escrito
   à mão sobre a cauda real (T1.3), os dois órfãos falsos reais (83 e 87) e
   as partidas 44 e 59.

O fonte é só lido; nada de docker/events-live/, processo ou rede.
"""
import json
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import start_match  # noqa: E402

FONTE = RAIZ / "docker" / "plugins-src" / "Cs2TrackerEvents" / "Cs2TrackerEventsPlugin.cs"
CAPTURA = RAIZ / "tests" / "fixtures" / "captura"
CAUDA_REAL = CAPTURA / "current.jsonl"
CAUDA_REAL_2 = RAIZ / "tests" / "fixtures" / "logs" / "eventos" / "current.jsonl"
FALSO_83 = CAPTURA / "orfao_falso_83.jsonl"
FALSO_87 = CAPTURA / "orfao_falso_87.jsonl"
PARTIDA_44 = CAPTURA / "events_44_map0.jsonl"  # começa com BOM
PARTIDA_59 = CAPTURA / "events_59_map0.jsonl"


@pytest.fixture(scope="module")
def fonte() -> str:
    return FONTE.read_text(encoding="utf-8")


def _corpo(fonte: str, assinatura: str) -> str:
    """O corpo do método que começa em `assinatura`, por contagem de chaves."""
    inicio = fonte.index(assinatura)
    abre = fonte.index("{", inicio)
    nivel = 0
    for i in range(abre, len(fonte)):
        if fonte[i] == "{":
            nivel += 1
        elif fonte[i] == "}":
            nivel -= 1
            if nivel == 0:
                return fonte[abre:i + 1]
    raise AssertionError(f"corpo de {assinatura} sem fim")


def _tipos_do_plugin(fonte: str) -> list:
    achou = re.search(r"string\[\]\s+EventosDePartida\s*=\s*\{([^}]*)\}", fonte)
    assert achou, "EventosDePartida não está no plugin"
    return re.findall(r'"([^"]+)"', achou.group(1))


def _arma_do_pos_jogo(fonte: str) -> str:
    corpo = _corpo(fonte, "internal static bool MorteDePosJogo(")
    achou = re.search(r'Texto\(evento, "weapon"\) != "([^"]+)"', corpo)
    assert achou, corpo
    return achou.group(1)


# ------------------------------------------------- a regra é a do start_match

def test_os_tipos_do_plugin_sao_os_tres_do_criterio_e_os_do_start_match(fonte):
    tipos = _tipos_do_plugin(fonte)
    assert sorted(tipos) == ["player_death", "player_hurt", "round_start"]
    assert set(tipos) == start_match.EVENTOS_DE_PARTIDA


def test_morte_de_pos_jogo_do_plugin_tem_a_regra_do_p1_1d(fonte):
    corpo = _corpo(fonte, "internal static bool MorteDePosJogo(")
    assert _arma_do_pos_jogo(fonte) == "world"
    assert 'Texto(evento, "type") != "player_death"' in corpo
    assert 'var atacante = Texto(evento, "attacker_steamid");' in corpo
    # Atacante = vítima e não vazio (o bot sai com steamid null).
    assert ('!string.IsNullOrEmpty(atacante) && atacante == Texto(evento, "victim_steamid")'
            in corpo)
    # E a morte de pós-jogo é o que se desconta do tipo de partida.
    leitura = _corpo(fonte, "internal static bool TemEventoDePartida(")
    assert "EventosDePartida.Contains(tipo) && !MorteDePosJogo(evento)" in leitura


# ---------------------------------------- Load e OnMapStart, antes do truncar

def test_load_e_onmapstart_preservam_antes_de_truncar(fonte):
    load = _corpo(fonte, "public override void Load(")
    assert "RegisterListener<Listeners.OnMapStart>(OnMapStart);" in load
    assert load.rstrip("}").rstrip().endswith("ResetForNewMap();")
    assert "private void OnMapStart(string mapName) => ResetForNewMap();" in fonte

    reset = _corpo(fonte, "private void ResetForNewMap(")
    preserva = reset.index("PreservarOrfao(_eventsPath);")
    trunca = reset.index('File.WriteAllText(_eventsPath, "");')
    # Drena e fecha o writer, preserva, e só então trunca.
    assert reset.index("DrenaFila();") < reset.index("CloseWriter();") < preserva < trunca
    assert reset.count("File.WriteAllText(") == 1


def test_o_orfao_tem_o_nome_do_start_match(fonte):
    nome = _corpo(fonte, "internal static string NomeDoOrfao(")
    assert "agoraUtc.ToString(\"yyyyMMdd'T'HHmmss'Z'\", CultureInfo.InvariantCulture)" in nome
    assert '$"orphan_{carimbo}.jsonl"' in nome
    assert '$"orphan_{carimbo}-{n}.jsonl"' in nome  # nunca sobrescreve
    preserva = _corpo(fonte, "private static void PreservarOrfao(")
    assert "File.Move(current, destino);" in preserva
    assert "File.Copy(current, destino);" in preserva


def test_versao_do_plugin_e_a_0_4_1(fonte):
    assert re.findall(r'ModuleVersion => "([^"]+)"', fonte) == ["0.4.1"]


# ------------------------------------ a regra do fonte sobre os arquivos reais

def _regra_do_plugin(fonte: str):
    """TemEventoDePartida com as constantes lidas do fonte: o filtro barato
    (a linha cita um dos tipos), o parse e a exceção da morte de pós-jogo."""
    tipos = _tipos_do_plugin(fonte)
    arma = _arma_do_pos_jogo(fonte)

    def pos_jogo(evento: dict) -> bool:
        atacante = evento.get("attacker_steamid")
        return (evento.get("type") == "player_death" and evento.get("weapon") == arma
                and isinstance(atacante, str) and atacante != ""
                and atacante == evento.get("victim_steamid"))

    def tem_partida(conteudo: bytes) -> bool:
        texto = conteudo.decode("utf-8", errors="replace").removeprefix("﻿")
        for linha in texto.splitlines():
            if not any(t in linha for t in tipos):
                continue
            try:
                evento = json.loads(linha)
            except ValueError:
                continue
            if isinstance(evento, dict) and evento.get("type") in tipos and not pos_jogo(evento):
                return True
        return False

    return tem_partida


def _primeira_linha(caminho: Path, tipo: str, world: bool = False) -> bytes:
    for linha in caminho.read_bytes().removeprefix(b"\xef\xbb\xbf").splitlines(keepends=True):
        if f'"type":"{tipo}"'.encode() in linha and (world or b'"weapon":"world"' not in linha):
            return linha
    raise AssertionError(f"{tipo} não está em {caminho.name}")


# Gabarito à mão: True = orphan_<utc>, False = cauda truncada.
@pytest.mark.parametrize("arquivo, orfao", [
    (CAUDA_REAL, False),     # 44 snapshots, 1 round_stats, 1 round_officially_ended
    (CAUDA_REAL_2, False),   # a cópia do T1.3 em logs/eventos
    (FALSO_83, False),       # cauda + morte de pós-jogo pelo world (P1.1d)
    (FALSO_87, False),
    (PARTIDA_44, True),      # partida inteira, com BOM
    (PARTIDA_59, True),
], ids=["cauda_t13", "cauda_logs", "falso_83", "falso_87", "partida_44", "partida_59"])
def test_regra_do_plugin_nos_arquivos_reais(fonte, arquivo, orfao):
    assert _regra_do_plugin(fonte)(arquivo.read_bytes()) is orfao


@pytest.mark.parametrize("extra, orfao", [
    (lambda: _primeira_linha(PARTIDA_44, "round_start"), True),
    (lambda: _primeira_linha(PARTIDA_44, "player_death"), True),
    (lambda: _primeira_linha(PARTIDA_44, "player_hurt"), True),
    (lambda: _primeira_linha(PARTIDA_44, "round_end"), False),
    (lambda: _primeira_linha(PARTIDA_44, "bomb_planted"), False),
    (lambda: _primeira_linha(FALSO_83, "player_death", world=True), False),
    (lambda: (_primeira_linha(PARTIDA_44, "round_start")
              + _primeira_linha(FALSO_83, "player_death", world=True)), True),
    (lambda: b'{"type":"round_start","round_num":3', False),  # linha cortada por crash
], ids=["round_start", "player_death", "player_hurt", "round_end", "bomba",
        "pos_jogo", "pos_jogo_com_round_start", "linha_cortada"])
def test_cauda_real_mais_um_evento(fonte, extra, orfao):
    conteudo = CAUDA_REAL.read_bytes() + extra()
    assert _regra_do_plugin(fonte)(conteudo) is orfao


def test_regra_do_plugin_concorda_com_o_start_match(fonte, tmp_path):
    # Nos arquivos reais, o plugin e o start_match dão a mesma resposta: os
    # dois nunca brigam pelo mesmo current.jsonl.
    regra = _regra_do_plugin(fonte)
    arquivos = (CAUDA_REAL, CAUDA_REAL_2, FALSO_83, FALSO_87, PARTIDA_44, PARTIDA_59)
    for n, arquivo in enumerate(arquivos):
        pasta = tmp_path / str(n)
        pasta.mkdir()
        (pasta / "current.jsonl").write_bytes(arquivo.read_bytes())
        do_start_match = start_match.preservar_orfao(pasta, log=lambda _: None) is not None
        assert regra(arquivo.read_bytes()) is do_start_match, arquivo.name
